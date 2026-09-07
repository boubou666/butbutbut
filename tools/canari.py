#!/usr/bin/env python3
"""Le canari : la source a-t-elle change de forme sous nos pieds ?

    python tools/canari.py

Tout butbutbut repose sur une API publique mais **non documentee**, le tableau
de bord d'ESPN. Personne ne nous previendra le jour ou `penaltyKick` sera
renomme, ou `athletesInvolved` deplace : le daemon, lui, est ecrit de facon
defensive, donc il ne plantera pas - il se contentera de ne plus jamais
annoncer un penalty. Une panne muette, la pire espece.

Les tests de `tests/` simulent la source par un `opener` : parfaits pour la
logique, aveugles a ce genre de derive puisque c'est nous qui fabriquons la
charge utile. D'ou ce programme, le seul du depot qui parle vraiment au reseau,
et qui n'est donc **jamais** lance par la CI ordinaire (voir
`.github/workflows/canari.yml`, quotidien, et `ci.yml`, hors reseau).

Ce qu'il fait : il interroge quelques competitions pour de vrai, et verifie que
chaque cle lue par `butbutbut/espn.py` est encore la, et du bon type. Puis il
repasse la charge utile a `espn.parse()` lui-meme : des cles presentes qui ne
produisent plus de matchs seraient une derive tout aussi grave.

Deux niveaux d'exigence, parce que la source ne remplit pas tout a tout moment :

  - **requis** : la cle doit etre sur *chaque* objet de son espece. Un match
    sans `homeAway` ou sans `score` n'existe pas ;
  - **au moins une fois** : la cle ne vit que dans certains contextes (la
    couleur d'un club, un `ownGoal`). Elle doit apparaitre au moins une fois
    parmi tout ce qu'on a inspecte ; si le contexte lui-meme ne s'est jamais
    presente (aucun but ce jour-la), la cle est declaree **non verifiee** et ce
    n'est pas un echec.

Un mardi de juillet, le tableau du jour peut etre vide : le canari ne crie pas
au loup pour ca. Il redemande alors les quatre derniers mois d'un coup
(`?dates=AAAAMMJJ-AAAAMMJJ`), de quoi retomber sur des matchs joues et donc sur
des buts a inspecter, en toute saison.

Codes de sortie : 0 tout va bien, 1 une cle manque ou a change de type, 2 la
source est injoignable. Le rapport complet est imprime dans tous les cas : on
veut la liste des degats, pas seulement le premier.
"""

import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

# Le canari vit dans tools/ mais lit le vrai code : c'est tout l'interet.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from butbutbut import __version__, crests, espn, leagues, sports  # noqa: E402

SCOREBOARD_URL = espn.SCOREBOARD_URL
TEAMS_URL = espn.TEAMS_URL
USER_AGENT = espn.USER_AGENT

# fra.1 et eng.1 sont les deux plus suivies ; esp.1 fait un troisieme avis, et
# les trois ne jouent pas toujours les memes jours - de quoi trouver des buts.
DEFAULT_SLUGS = ("fra.1", "eng.1", "esp.1")

# Le filet de rattrapage quand le tableau du jour est vide. Quatre mois : entre
# la fin d'une saison (fin mai) et le debut de la suivante (mi-aout), c'est
# toujours assez long pour attraper des matchs joues.
LOOKBACK_DAYS = 120

TIMEOUT = 20.0
ATTEMPTS = 2          # une panne d'une seconde ne doit pas allumer le rouge


# ------------------------------------------------------------- typage --------
# La cle est l'etiquette imprimee dans le rapport : elle dit a un lecteur
# presse ce qui etait attendu.

def _text(value):
    return isinstance(value, str)


def _full_text(value):
    return isinstance(value, str) and value.strip() != ""


def _identifier(value):
    """Un identifiant ESPN : espn.py le passe a str(), donc un nombre convient."""
    return isinstance(value, (str, int)) and str(value).strip() != ""


def _integer(value):
    """Ce que `espn._int()` saura lire : "3", 3, mais pas "trois"."""
    try:
        int(str(value).strip())
    except (TypeError, ValueError):
        return False
    return True


CHECKS = {
    "liste": lambda v: isinstance(v, list),
    "liste non vide": lambda v: isinstance(v, list) and len(v) > 0,
    "objet": lambda v: isinstance(v, dict),
    "texte": _text,
    "texte non vide": _full_text,
    "identifiant": _identifier,
    "entier": _integer,
    "booleen": lambda v: isinstance(v, bool),
    "pre/in/post": lambda v: v in (espn.PRE, espn.LIVE, espn.POST),
    "home/away": lambda v: v in ("home", "away"),
    "date ISO": lambda v: espn._parse_date(v) is not None,
    "couleur hex": lambda v: crests.normalize(v) is not None,
    "url http": lambda v: (isinstance(v, str)
                           and v.lower().startswith(("http://", "https://"))),
}

REQUIRED = "requis"
SAMPLED = "au moins une fois"


# --------------------------------------------------------------- specs -------
# Chaque table decrit un objet de la reponse : (chemin, exigence, type
# attendu). Le chemin peut etre pointe ("status.type.state") ; il est lu
# exactement comme espn.py le lit.

PAYLOAD_KEYS = (
    ("events", REQUIRED, "liste"),
)

# En-tete de competition : espn.parse() y prend le nom d'une competition
# ouverte a la volee (League.adopt_name).
HEADER_KEYS = (
    ("name", SAMPLED, "texte non vide"),
    ("abbreviation", SAMPLED, "texte non vide"),
)

EVENT_KEYS = (
    ("id", REQUIRED, "identifiant"),
    ("competitions", REQUIRED, "liste non vide"),
    ("date", SAMPLED, "date ISO"),          # repli quand competition.date manque
)

COMPETITION_KEYS = (
    ("id", SAMPLED, "identifiant"),         # repli quand event.id manque
    ("date", REQUIRED, "date ISO"),
    ("competitors", REQUIRED, "liste non vide"),
    ("status", REQUIRED, "objet"),
    ("status.displayClock", REQUIRED, "texte"),
    ("status.type", REQUIRED, "objet"),
    ("status.type.state", REQUIRED, "pre/in/post"),
    ("status.type.name", REQUIRED, "texte non vide"),
    ("status.type.shortDetail", REQUIRED, "texte non vide"),
    ("details", SAMPLED, "liste"),          # absent tant que rien n'est arrive
)

COMPETITOR_KEYS = (
    ("homeAway", REQUIRED, "home/away"),
    ("score", REQUIRED, "entier"),
    ("team", REQUIRED, "objet"),
)

TEAM_KEYS = (
    ("id", REQUIRED, "identifiant"),
    ("displayName", REQUIRED, "texte non vide"),
    ("shortDisplayName", REQUIRED, "texte non vide"),
    ("abbreviation", REQUIRED, "texte non vide"),
    ("name", SAMPLED, "texte non vide"),
    ("location", SAMPLED, "texte non vide"),
    ("color", SAMPLED, "couleur hex"),
    ("alternateColor", SAMPLED, "couleur hex"),
    ("logo", SAMPLED, "url http"),
)

# Sur *toutes* les actions : ce sont ces deux drapeaux qui trient les buts des
# expulsions. Les perdre, c'est ne plus rien afficher du tout.
DETAIL_FLAGS = (
    ("scoringPlay", REQUIRED, "booleen"),
    ("redCard", REQUIRED, "booleen"),
)

# Sur les seules actions qui nous interessent (un but ou une expulsion).
DETAIL_KEYS = (
    ("type.text", REQUIRED, "texte non vide"),
    ("clock.displayValue", REQUIRED, "texte non vide"),
    ("team.id", REQUIRED, "identifiant"),
    ("ownGoal", REQUIRED, "booleen"),
    ("penaltyKick", REQUIRED, "booleen"),
    ("shootout", REQUIRED, "booleen"),
    # Pas REQUIRED : la source laisse parfois une action sans joueur nomme
    # (une sur deux cents un dimanche de LaLiga). espn.py le lit deja
    # defensivement - la carte sort alors sans buteur - donc crier au loup
    # la-dessus tous les matins, ce serait apprendre a ignorer le rouge.
    # Ce qu'on surveille vraiment, c'est que la cle n'ait pas disparu.
    ("athletesInvolved", SAMPLED, "liste"),
)

ATHLETE_KEYS = (
    ("id", SAMPLED, "identifiant"),
    ("shortName", REQUIRED, "texte non vide"),
    ("displayName", SAMPLED, "texte non vide"),   # repli quand shortName manque
)

# L'autre endpoint : la liste des equipes, qui valide ce qu'on tape dans
# --teams. Vide, il ferait refuser tous les noms au demarrage.
TEAMS_PAYLOAD_KEYS = (
    ("sports", REQUIRED, "liste non vide"),
    ("sports.0.leagues", REQUIRED, "liste non vide"),
    ("sports.0.leagues.0.teams", REQUIRED, "liste non vide"),
)

CATALOGUE_ENTRY_KEYS = (
    ("team", REQUIRED, "objet"),
    ("team.displayName", REQUIRED, "texte non vide"),
    ("team.shortDisplayName", REQUIRED, "texte non vide"),
    ("team.abbreviation", REQUIRED, "texte non vide"),
)

# Le programme de la visite, dans l'ordre du rapport. Il sert aussi a annoncer
# d'avance toutes les cles surveillees : une cle qu'aucun objet n'a permis de
# regarder doit sortir "non verifiee", et pas disparaitre du rapport.
PLAN = (
    ("payload", PAYLOAD_KEYS),
    ("leagues[0]", HEADER_KEYS),
    ("event", EVENT_KEYS),
    ("competition", COMPETITION_KEYS),
    ("competitor", COMPETITOR_KEYS),
    ("competitor.team", TEAM_KEYS),
    ("detail", DETAIL_FLAGS),
    ("detail", DETAIL_KEYS),
    ("detail.athletesInvolved[0]", ATHLETE_KEYS),
    ("equipes", TEAMS_PAYLOAD_KEYS),
    ("equipes.teams[]", CATALOGUE_ENTRY_KEYS),
)


def dig(obj, path):
    """Descend un chemin pointe. Rend (trouve, valeur).

    "trouve" est faux des qu'un maillon manque : c'est exactement ce que
    `.get()` en cascade produit dans espn.py, une valeur absente.
    """
    current = obj
    for key in path.split("."):
        if isinstance(current, list):
            try:
                index = int(key)
            except ValueError:
                return False, None
            if index >= len(current):
                return False, None
            current = current[index]
            continue
        if not isinstance(current, dict) or key not in current:
            return False, None
        current = current[key]
    return True, current


# -------------------------------------------------------------- rapport ------

class Ledger:
    """Le carnet du canari : une ligne par cle surveillee.

    On ne peut pas juger une cle sur un seul objet - la source remplit ce
    qu'elle veut quand elle veut. On compte donc, pour chaque cle, combien de
    fois elle etait la, combien de fois elle manquait, et combien de fois elle
    portait autre chose que ce qu'on attend. Le verdict tombe a la fin.
    """

    def __init__(self, plan=PLAN):
        self.order = []
        self.entries = {}
        self.anomalies = []
        for scope, spec in plan:
            for path, level, expected in spec:
                self.declare(scope + "." + path, level, expected)

    def declare(self, path, level, expected):
        """Inscrit une cle au programme, avant meme de l'avoir cherchee."""
        if path not in self.entries:
            self.entries[path] = {"level": level, "expected": expected,
                                  "seen": 0, "missing": 0, "bad": 0,
                                  "sample": ""}
            self.order.append(path)

    def note(self, path, level, expected, present, value=None):
        """Une observation de plus pour `path`, sur un objet de son espece."""
        self.declare(path, level, expected)
        entry = self.entries[path]
        if not present:
            entry["missing"] += 1
            return
        entry["seen"] += 1
        if not CHECKS[expected](value):
            entry["bad"] += 1
            if not entry["sample"]:
                entry["sample"] = repr(value)[:40]

    def check(self, scope, obj, spec):
        """Confronte un objet a la table de cles qui le decrit."""
        for path, level, expected in spec:
            found, value = dig(obj, path)
            self.note(scope + "." + path, level, expected, found, value)

    def anomaly(self, message):
        """Ce qui n'entre dans aucune case : un evenement qui n'est pas un objet."""
        if message not in self.anomalies:
            self.anomalies.append(message)

    def verdict(self, path):
        """ok / MANQUE / TYPE / non verifie, pour une cle."""
        entry = self.entries[path]
        if entry["bad"]:
            return "TYPE"
        if not entry["seen"] and not entry["missing"]:
            # Aucun objet de cette espece ne s'est presente : la cle n'est pas
            # absente, elle n'a simplement pas pu etre regardee.
            return "non verifie"
        if entry["level"] == REQUIRED:
            return "MANQUE" if entry["missing"] else "ok"
        return "ok" if entry["seen"] else "MANQUE"

    def failures(self):
        """Les cles qui ne vont pas, plus les anomalies de structure."""
        broken = [path for path in self.order
                  if self.verdict(path) in ("MANQUE", "TYPE")]
        return broken + list(self.anomalies)

    def unverified(self):
        return [path for path in self.order
                if self.verdict(path) == "non verifie"]

    def lines(self):
        """Le rapport, une ligne par cle, dans l'ordre de la lecture."""
        out = []
        for path in self.order:
            entry = self.entries[path]
            verdict = self.verdict(path)
            total = entry["seen"] + entry["missing"]
            counts = "{}/{}".format(entry["seen"], total)
            line = "  {:<12} {:<44} {:<15} {}".format(
                verdict, path, entry["expected"], counts)
            if entry["bad"]:
                line += "  ({} du mauvais type, ex. {})".format(
                    entry["bad"], entry["sample"])
            out.append(line)
        for message in self.anomalies:
            out.append("  {:<12} {}".format("ANOMALIE", message))
        return out


# --------------------------------------------------------------- lecture -----

def inspect_scoreboard(payload, ledger):
    """Passe un tableau de bord au peigne fin. Rend le decompte de ce qu'on a vu.

    Les compteurs servent a deux choses : dire au lecteur sur quoi le verdict
    s'appuie, et savoir s'il faut aller chercher un jour ou l'on a joue.
    """
    tally = {"events": 0, "usable": 0, "goals": 0, "red_cards": 0}

    ledger.check("payload", payload, PAYLOAD_KEYS)

    header = payload.get("leagues") or []
    if header and isinstance(header[0], dict):
        ledger.check("leagues[0]", header[0], HEADER_KEYS)

    for event in payload.get("events") or []:
        if not isinstance(event, dict):
            ledger.anomaly("un element de events n'est pas un objet")
            continue
        tally["events"] += 1
        ledger.check("event", event, EVENT_KEYS)

        competitions = event.get("competitions") or []
        if not competitions or not isinstance(competitions[0], dict):
            ledger.anomaly("un match sans competitions[0] exploitable")
            continue
        competition = competitions[0]
        ledger.check("competition", competition, COMPETITION_KEYS)

        sides = {}
        for competitor in competition.get("competitors") or []:
            if not isinstance(competitor, dict):
                ledger.anomaly("un element de competitors n'est pas un objet")
                continue
            ledger.check("competitor", competitor, COMPETITOR_KEYS)
            team = competitor.get("team")
            if isinstance(team, dict):
                ledger.check("competitor.team", team, TEAM_KEYS)
            sides[competitor.get("homeAway")] = competitor
        if "home" in sides and "away" in sides:
            tally["usable"] += 1
        else:
            ledger.anomaly("un match sans cote home et cote away")

        for detail in competition.get("details") or []:
            if not isinstance(detail, dict):
                ledger.anomaly("un element de details n'est pas un objet")
                continue
            ledger.check("detail", detail, DETAIL_FLAGS)
            scoring = bool(detail.get("scoringPlay"))
            red = bool(detail.get("redCard"))
            if not scoring and not red:
                continue          # un carton jaune : espn.py n'en lit rien
            if scoring:
                tally["goals"] += 1
            else:
                tally["red_cards"] += 1
            ledger.check("detail", detail, DETAIL_KEYS)

            athletes = detail.get("athletesInvolved") or []
            if athletes and isinstance(athletes[0], dict):
                ledger.check("detail.athletesInvolved[0]", athletes[0],
                             ATHLETE_KEYS)
    return tally


def inspect_teams(payload, ledger):
    """L'endpoint des equipes, celui qui valide --teams."""
    ledger.check("equipes", payload, TEAMS_PAYLOAD_KEYS)
    found, entries = dig(payload, "sports.0.leagues.0.teams")
    if not found or not isinstance(entries, list):
        return 0
    for entry in entries:
        if not isinstance(entry, dict):
            ledger.anomaly("un element de teams n'est pas un objet")
            continue
        ledger.check("equipes.teams[]", entry, CATALOGUE_ENTRY_KEYS)
    return len(entries)


def cross_check(payload, slug, tally, ledger):
    """Le vrai code de lecture rend-il encore des matchs, des buts, un buteur ?

    Une cle peut etre la et ne plus rien produire (une valeur qui change de
    forme, un tableau qui se vide). On repasse donc la charge utile a
    `espn.parse()`, le code que le daemon execute vraiment, et on compare avec
    ce qu'on vient de compter a la main.
    """
    league = leagues.find(slug)
    if league is None:
        return []          # un code que le catalogue refuse : pas son proces
    problems = []
    try:
        matches = espn.parse(payload, league)
    except Exception as exc:
        return ["espn.parse() a leve {} : {}".format(type(exc).__name__, exc)]

    if len(matches) != tally["usable"]:
        problems.append(
            "espn.parse() rend {} match(s) pour {} exploitable(s) dans la "
            "reponse".format(len(matches), tally["usable"]))

    goals = sum(len(match.plays) for match in matches)
    if goals != tally["goals"]:
        problems.append(
            "espn.parse() rend {} but(s) la ou la reponse en compte {}"
            .format(goals, tally["goals"]))

    reds = sum(len(match.red_cards) for match in matches)
    if reds != tally["red_cards"]:
        problems.append(
            "espn.parse() rend {} expulsion(s) la ou la reponse en compte {}"
            .format(reds, tally["red_cards"]))

    if tally["goals"] and not any(play.scorer for match in matches
                                  for play in match.plays):
        problems.append("aucun buteur nomme sur {} but(s) : le nom du buteur "
                        "ne remonte plus".format(tally["goals"]))

    if matches and not any(match.home and match.away for match in matches):
        problems.append("aucun match ne porte le nom de ses deux equipes")

    return problems


# --------------------------------------------------------------- reseau ------

def http_opener(url, timeout):
    """L'appel reel. Les tests passent leur propre callable a la place."""
    request = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Cache-Control": "no-cache",
    })
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def fetch_json(url, opener, timeout=TIMEOUT, attempts=ATTEMPTS):
    """Une reponse JSON, ou une SourceError. Deux essais avant de crier."""
    last = None
    for _ in range(attempts):
        try:
            raw = opener(url, timeout)
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8", "replace")
            payload = json.loads(raw)
        except Exception as exc:
            last = exc
            continue
        if not isinstance(payload, dict):
            last = ValueError("la reponse n'est pas un objet JSON")
            continue
        return payload
    raise espn.SourceError("{} : {}".format(url, last))


def lookback_range(today=None, days=LOOKBACK_DAYS):
    """Le parametre `dates` d'un rattrapage : "AAAAMMJJ-AAAAMMJJ".

    ESPN accepte un intervalle, ce qui evite de deviner un jour de match : on
    demande les quatre derniers mois d'un coup et on y trouve forcement des
    matchs joues, ete compris.
    """
    today = today or datetime.now(timezone.utc).date()
    start = today - timedelta(days=days)
    return "{}-{}".format(start.strftime("%Y%m%d"), today.strftime("%Y%m%d"))


def split_sport(slug):
    """(sport, code) a partir de ce qu'on tape : "fra.1" ou "hockey:nhl".

    Meme ecriture que --leagues, ou le football est sous-entendu. Le canari ne
    surveille par defaut que le football : les autres sports lisent le meme
    tableau de bord, mais pas le meme tableau d'actions, et leurs cles
    meriteront leur propre inventaire.
    """
    if ":" in str(slug):
        code, _, rest = str(slug).partition(":")
        sport = sports.find(code)
        if sport is not None:
            return sport, rest
    return sports.DEFAULT, str(slug)


def scoreboard_url(slug, dates=""):
    sport, code = split_sport(slug)
    url = SCOREBOARD_URL.format(sport=sport.code, slug=code)
    return url + "?dates=" + dates if dates else url


def teams_url(slug):
    sport, code = split_sport(slug)
    return TEAMS_URL.format(sport=sport.code, slug=code)


# --------------------------------------------------------------- passage -----

VERT, ROUGE, INJOIGNABLE = "vert", "rouge", "injoignable"


def check_league(slug, opener=None, dates="", timeout=TIMEOUT, out=None):
    """Le canari sur une competition. Rend (verdict, ledger).

    Le premier appel est celui que le daemon fait vraiment, sans `dates` : on
    verifie d'abord ce que butbutbut lit tous les jours. S'il n'en sort aucun
    but a inspecter, on redemande les derniers mois - sans quoi un mardi de
    juillet ne verifierait rien du tout.
    """
    out = out or sys.stdout
    opener = opener or http_opener
    ledger = Ledger()
    problems = []

    print("--- {} {}".format(slug, "-" * (66 - len(slug))), file=out)

    try:
        first = fetch_json(scoreboard_url(slug, dates), opener, timeout)
    except espn.SourceError as exc:
        print("  INJOIGNABLE  {}\n".format(exc), file=out)
        return INJOIGNABLE, ledger

    tally = inspect_scoreboard(first, ledger)
    problems.extend(cross_check(first, slug, tally, ledger))
    print("  releve {:<14} {} match(s), {} but(s), {} expulsion(s)".format(
        dates or "le jour meme", tally["events"], tally["goals"],
        tally["red_cards"]), file=out)

    # Rien a se mettre sous la dent : on va chercher un jour ou l'on a joue.
    if not dates and not tally["goals"]:
        window = lookback_range()
        try:
            second = fetch_json(scoreboard_url(slug, window), opener, timeout)
        except espn.SourceError as exc:
            print("  INJOIGNABLE  {}\n".format(exc), file=out)
            return INJOIGNABLE, ledger
        extra = inspect_scoreboard(second, ledger)
        problems.extend(cross_check(second, slug, extra, ledger))
        print("  rattrapage {:<10} {} match(s), {} but(s), {} expulsion(s)"
              .format(window, extra["events"], extra["goals"],
                      extra["red_cards"]), file=out)
        for key in tally:
            tally[key] += extra[key]

    if not tally["events"]:
        print("  aucun match a inspecter : rien n'est verifie ici, et ce n'est"
              " pas un echec.", file=out)

    try:
        teams = fetch_json(teams_url(slug), opener, timeout)
    except espn.SourceError as exc:
        print("  INJOIGNABLE  {}\n".format(exc), file=out)
        return INJOIGNABLE, ledger
    count = inspect_teams(teams, ledger)
    print("  catalogue      {} equipe(s)".format(count), file=out)

    for line in ledger.lines():
        print(line, file=out)
    for problem in problems:
        print("  {:<12} {}".format("PARSE", problem), file=out)

    broken = ledger.failures()
    skipped = ledger.unverified()
    print("  bilan : {} cle(s) surveillee(s), {} en defaut, {} non verifiee(s)"
          .format(len(ledger.order), len(broken), len(skipped)), file=out)
    print("", file=out)
    return (ROUGE if (broken or problems) else VERT), ledger


def run(slugs=DEFAULT_SLUGS, opener=None, dates="", timeout=TIMEOUT, out=None):
    """Le canari sur plusieurs competitions. Rend le code de sortie."""
    out = out or sys.stdout
    print("canari butbutbut {} - la forme du tableau de bord ESPN"
          .format(__version__), file=out)
    print(SCOREBOARD_URL.format(sport="<sport>", slug="<code>"), file=out)
    print("", file=out)

    verdicts = {}
    skipped = {}
    for slug in slugs:
        verdicts[slug], ledger = check_league(slug, opener=opener, dates=dates,
                                              timeout=timeout, out=out)
        skipped[slug] = len(ledger.unverified())

    broken = [slug for slug, verdict in verdicts.items() if verdict == ROUGE]
    if broken:
        print("ROUGE : la source a bouge sur {}. Le detail est ci-dessus ; ce "
              "qui lit ces cles vit dans butbutbut/espn.py."
              .format(", ".join(broken)), file=out)
        return 1

    mute = [slug for slug, verdict in verdicts.items()
            if verdict == INJOIGNABLE]
    if mute:
        print("SOURCE INJOIGNABLE ({}) : rien n'a pu etre verifie. Une panne "
              "passagere se rattrape en relancant.".format(", ".join(mute)),
              file=out)
        return 2

    print("VERT : toutes les cles lues par butbutbut/espn.py sont a leur "
          "place.", file=out)
    blind = [slug for slug in slugs if skipped.get(slug)]
    if blind:
        print("       ({} : des cles n'ont pas pu etre regardees, faute de "
              "match ou d'action a inspecter - ce n'est pas un echec.)"
              .format(", ".join(blind)), file=out)
    return 0


def main(argv=None, opener=None, out=None):
    parser = argparse.ArgumentParser(
        prog="canari",
        description="Verifie que le tableau de bord d'ESPN a toujours la forme "
                    "que butbutbut/espn.py attend.")
    parser.add_argument("--leagues", default=",".join(DEFAULT_SLUGS),
                        help="codes ESPN a interroger (defaut : {})"
                             .format(",".join(DEFAULT_SLUGS)))
    parser.add_argument("--dates", default="",
                        help="viser une date ou un intervalle : 20250517, "
                             "20250501-20250517")
    parser.add_argument("--timeout", type=float, default=TIMEOUT,
                        help="delai reseau, en secondes")
    args = parser.parse_args(argv)

    slugs = [slug.strip() for slug in args.leagues.split(",") if slug.strip()]
    return run(slugs=slugs, opener=opener, dates=args.dates.strip(),
               timeout=args.timeout, out=out)


if __name__ == "__main__":
    sys.exit(main())
