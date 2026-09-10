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

Le programme de la visite depend du sport, parce que les trois ne publient pas
la meme chose. Le football et le rugby ont leur tableau d'actions dans le
tableau de bord ; le hockey n'en a pas du tout - lui reclamer `details` serait
guetter une cle dont on sait qu'elle n'existe pas - et va chercher ses buteurs
dans le resume d'un match, dont les cles sont donc surveillees pour lui seul.
Un resume par competition et par passage : c'est 450 ko, et la question posee
ici se repond sur un match aussi bien que sur trente.

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

from butbutbut import (__version__, crests, espn, journal, leagues,  # noqa: E402
                       sports)

SCOREBOARD_URL = espn.SCOREBOARD_URL
TEAMS_URL = espn.TEAMS_URL
SUMMARY_URL = espn.SUMMARY_URL

# fra.1 et eng.1 sont les deux plus suivies ; esp.1 fait un troisieme avis, et
# les trois ne jouent pas toujours les memes jours - de quoi trouver des buts.
# hockey:nhl s'y ajoute pour une raison a lui : c'est le seul sport dont les
# buteurs viennent du resume d'un match, et une cle de `plays[]` qui bougerait
# rendrait la carte de hockey muette sans que rien ne casse.
DEFAULT_SLUGS = ("fra.1", "eng.1", "esp.1", "hockey:nhl")

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


def _number(value):
    """Ce que `espn._stat_value()` saura lire : "51.5", "7", mais pas "".

    Le canari lit avec les yeux du programme, jamais avec les siens : si un
    jour la source ecrit ses statistiques autrement, c'est cette fonction-la
    qui doit dire non, parce que c'est elle que la carte croira.
    """
    return espn._stat_value(value) is not None


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
    "nombre": _number,
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
    # REQUIRED alors que la note elle-meme est presque toujours vide : c'est le
    # TABLEAU qui est sur chaque match (9 601 releves, pas une exception), et
    # c'est justement ce qu'on veut voir bouger. Une note qui n'arriverait plus
    # jamais ne casse rien ; `notes` devenue une chaine se decouperait lettre
    # par lettre chez un lecteur moins prudent que le notre.
    ("notes", REQUIRED, "liste"),
)

# Les statistiques d'un camp, pour les seuls sports qui en affichent une sur
# leur carte de fin de match. Les noms ne sont pas ecrits ici mais demandes au
# sport (`Sport.team_stats`) : deux listes finiraient par diverger, et c'est
# celle de sports.py que la carte croit.
#
# SAMPLED et non REQUIRED, parce que la source ne remplit ce bloc qu'apres le
# coup d'envoi : sur un match a venir le tableau est VIDE - present, mais vide.
# Un mardi de juillet, le canari dira donc "non verifie", ce qui est la verite.
COMPETITOR_STATS_KEYS = (
    ("statistics", SAMPLED, "liste"),
)


def stats_keys(sport):
    return tuple((name, SAMPLED, "nombre") for name in sport.team_stats)


def stats_bag(competitor) -> dict:
    """{nom: displayValue} pour un camp, tel qu'espn.team_stats() le lit.

    Aplatir le tableau avant de le confronter aux cles surveillees, c'est
    poser la seule question qui vaille : "possessionPct est-il toujours la ?".
    Un tableau de neuf objets tous bien formes ne repond pas a celle-la - ils
    pourraient tous avoir ete renommes.
    """
    bag = {}
    for entry in competitor.get("statistics") or []:
        if isinstance(entry, dict) and entry.get("name") is not None:
            bag.setdefault(entry["name"], entry.get("displayValue"))
    return bag


# `details` a sa table a lui, et pas par gout du rangement : au hockey la cle
# est absente de tous les matchs, tout le temps. Declaree avec les autres, elle
# ferait rougir le canari tous les matins sur `hockey:nhl` pour un fait connu
# et documente. Elle n'est donc surveillee que chez les sports qui la lisent.
COMPETITION_DETAILS_KEYS = (
    ("details", SAMPLED, "liste"),          # absent tant que rien n'est arrive
)

COMPETITOR_KEYS = (
    ("homeAway", REQUIRED, "home/away"),
    ("score", REQUIRED, "entier"),
    ("team", REQUIRED, "objet"),
)

# Ni `winner` ni `shootoutScore` ne figurent ici, et ce n'est pas un oubli. Un
# competiteur sur trois est un match a venir : il n'a legitimement ni l'un ni
# l'autre, et une cle surveillee qui manque sur les deux tiers des objets ferait
# rougir le canari un mardi de juillet. Ce qui les concerne est verifie plus
# bas, sur les seuls matchs ou la question se pose - voir cross_check().

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


# Ce qu'un sport ne publie pas du tout sur ses equipes. Le hockey n'a jamais de
# couleur secondaire ; le rugby n'a ni couleur secondaire ni ville. Une cle
# absente PARTOUT dans un sport n'est pas une cle disparue, c'est une cle qui
# n'a jamais existe la : la reclamer allumerait le rouge tous les matins, et un
# rouge permanent est un rouge qu'on apprend a ne plus lire.
TEAM_KEYS_ABSENT = {
    "hockey": ("alternateColor",),
    "rugby": ("location", "alternateColor"),
}


def team_keys(sport):
    """Les cles d'une equipe que ce sport publie vraiment.

    Le football les donne toutes, les autres non, alors que le reste de l'objet
    d'equipe garde la meme forme. Ce qu'on renonce a surveiller sur un sport,
    espn.py le lit deja par `.get()` : son absence n'y coute rien.
    """
    absent = TEAM_KEYS_ABSENT.get(sport.code, ())
    return tuple(key for key in TEAM_KEYS if key[0] not in absent)

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

# Le rugby publie le meme tableau `details` que le football, mais pas un seul
# drapeau : la nature de l'action se lit dans `type.id` ("1" = essai), et c'est
# ainsi qu'espn.py la lit (`_rugby_details()`). Lui reclamer `scoringPlay`,
# c'est guetter une cle qui n'a jamais existe chez lui ; et un essai n'a pas
# plus d'`ownGoal` que de `penaltyKick`, ces deux-la sont du football.
RUGBY_DETAIL_KEYS = (
    ("type.id", REQUIRED, "identifiant"),
    ("type.text", REQUIRED, "texte non vide"),
    ("clock.displayValue", REQUIRED, "texte non vide"),
    ("team.id", REQUIRED, "identifiant"),
    ("athletesInvolved", SAMPLED, "liste"),
)


def soccer_kind(detail):
    """(point, expulsion, tir au but) d'une action, lue par ses drapeaux."""
    scoring = bool(detail.get("scoringPlay"))
    red = bool(detail.get("redCard"))
    return scoring, red and not scoring, bool(detail.get("shootout"))


def rugby_kind(detail):
    """La meme chose, lue par le type de l'action - comme espn.py la lit.

    Les tables viennent d'espn.py et n'en sont pas recopiees : ce qui compte
    ici est que le canari inspecte exactement les actions que le daemon
    retient. Le jour ou ESPN renumeroterait ses types, les deux se tromperaient
    ensemble sans qu'une seule cle ne manque - c'est justement pour cela que
    cross_check() surveille a part une journee entiere restee sans action.
    """
    kind = detail.get("type") or {}
    type_id = str(kind.get("id") or "").strip()
    text = str(kind.get("text") or "").strip().lower()
    scored = (espn.RUGBY_SCORES.get(type_id)
              or espn.RUGBY_SCORES_BY_TEXT.get(text))
    red = type_id in espn.RUGBY_RED_CARD or text == "red card"
    # Le rugby ne se departage jamais aux tirs au but (voir sports.py) : le
    # troisieme drapeau est faux par construction, pas par oubli.
    return bool(scored), bool(red and not scored), False


def detail_plan(sport):
    """(drapeaux exiges, cles d'une action retenue, tri) pour ce sport.

    Deux sources, deux grammaires. Trier autrement qu'espn.py, ce serait
    inspecter les mauvaises actions - ou, pour le rugby, aucune.
    """
    if sport.plays == sports.PLAYS_TYPES:
        return (), RUGBY_DETAIL_KEYS, rugby_kind
    return DETAIL_FLAGS, DETAIL_KEYS, soccer_kind

# L'autre endpoint : la liste des equipes, qui valide ce qu'on tape dans
# --teams. Vide, il ferait refuser tous les noms au demarrage.
TEAMS_PAYLOAD_KEYS = (
    ("sports", REQUIRED, "liste non vide"),
    ("sports.0.leagues", REQUIRED, "liste non vide"),
    ("sports.0.leagues.0.teams", REQUIRED, "liste non vide"),
)

# Le resume d'un match : la seule autre porte que butbutbut pousse, et il ne la
# pousse qu'apres un but, pour les sports qui n'ont pas de buteur dans leur
# tableau de bord (voir sports.Sport.summary_plays).
SUMMARY_PAYLOAD_KEYS = (
    ("plays", REQUIRED, "liste non vide"),
)

# Sur *toutes* les actions du resume : c'est le type qui trie les 14 buts des
# 302 actions d'un match. Le perdre, c'est ne plus jamais nommer un buteur.
PLAY_TYPE_KEYS = (
    ("type.id", REQUIRED, "identifiant"),
    ("type.text", REQUIRED, "texte non vide"),
)

# Sur les seules actions qui nous interessent : les buts.
GOAL_PLAY_KEYS = (
    ("team.id", REQUIRED, "identifiant"),
    ("clock.displayValue", REQUIRED, "texte non vide"),
    ("period.number", REQUIRED, "entier"),
    ("scoringPlay", SAMPLED, "booleen"),
    ("participants", REQUIRED, "liste non vide"),
)

# Le buteur et ses passeurs. `type` porte le role ("scorer", "assister") et
# c'est lui qui distingue les deux : sans role, espn.py refuse expres de
# deviner, et la carte ressort sans nom.
PARTICIPANT_KEYS = (
    ("type", REQUIRED, "texte non vide"),
    ("athlete", REQUIRED, "objet"),
    ("athlete.id", SAMPLED, "identifiant"),
    ("athlete.shortName", REQUIRED, "texte non vide"),
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
BOARD_PLAN = (
    ("payload", PAYLOAD_KEYS),
    ("leagues[0]", HEADER_KEYS),
    ("event", EVENT_KEYS),
    ("competition", COMPETITION_KEYS),
    ("competitor", COMPETITOR_KEYS),
    ("competitor.team", TEAM_KEYS),
)

# Le tableau d'actions, pour les sports qui en ont un.
DETAILS_PLAN = (
    ("competition", COMPETITION_DETAILS_KEYS),
    ("detail", DETAIL_FLAGS),
    ("detail", DETAIL_KEYS),
    ("detail.athletesInvolved[0]", ATHLETE_KEYS),
)

# Le meme, pour un sport qui trie ses actions par type. Annoncer les drapeaux
# du football ici ferait sortir deux cles "MANQUE" sur chaque ligne de rugby.
RUGBY_DETAILS_PLAN = (
    ("competition", COMPETITION_DETAILS_KEYS),
    ("detail", RUGBY_DETAIL_KEYS),
    ("detail.athletesInvolved[0]", ATHLETE_KEYS),
)


def details_plan(sport):
    """Le programme du tableau d'actions de ce sport."""
    if sport.plays == sports.PLAYS_TYPES:
        return RUGBY_DETAILS_PLAN
    return DETAILS_PLAN

CATALOGUE_PLAN = (
    ("equipes", TEAMS_PAYLOAD_KEYS),
    ("equipes.teams[]", CATALOGUE_ENTRY_KEYS),
)

# Le programme du football, qui reste le defaut : tout, dans l'ordre du rapport.
PLAN = BOARD_PLAN + DETAILS_PLAN + CATALOGUE_PLAN

# Le programme du resume, ajoute au precedent pour les seuls sports qui vont
# y chercher leurs buteurs. Le declarer partout ferait sortir dix cles "non
# verifiees" sur chaque ligne de football, tous les matins, pour un endpoint
# que le football n'appelle jamais - et une colonne de gris qu'on finit par ne
# plus lire est pire qu'une colonne absente.
SUMMARY_PLAN = (
    ("resume", SUMMARY_PAYLOAD_KEYS),
    ("resume.plays[]", PLAY_TYPE_KEYS),
    ("resume.but", GOAL_PLAY_KEYS),
    ("resume.but.participants[]", PARTICIPANT_KEYS),
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

def inspect_scoreboard(payload, ledger, sport=None):
    """Passe un tableau de bord au peigne fin. Rend le decompte de ce qu'on a vu.

    Les compteurs servent a deux choses : dire au lecteur sur quoi le verdict
    s'appuie, et savoir s'il faut aller chercher un jour ou l'on a joue.

    `sport` decide de ce qu'on regarde. Un sport sans tableau d'actions n'en a
    pas un vide, il n'en a pas du tout : lui reclamer `details` reviendrait a
    surveiller une cle dont on sait qu'elle n'existe pas, et a passer au rouge
    tous les matins pour rien.
    """
    sport = sport or sports.DEFAULT
    team_spec = team_keys(sport)
    reads_details = sport.plays != sports.PLAYS_NONE
    flags_spec, detail_spec, kind_of = detail_plan(sport)
    # Meme regle pour les statistiques : un sport qui n'en affiche aucune ne se
    # fait pas reclamer un champ qu'il remplit avec de tout autres nombres.
    stats_spec = stats_keys(sport)
    reads_stats = bool(stats_spec)
    tally = {"events": 0, "usable": 0, "goals": 0, "red_cards": 0,
             "shootout": 0}

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
        if reads_details:
            ledger.check("competition", competition, COMPETITION_DETAILS_KEYS)

        sides = {}
        for competitor in competition.get("competitors") or []:
            if not isinstance(competitor, dict):
                ledger.anomaly("un element de competitors n'est pas un objet")
                continue
            ledger.check("competitor", competitor, COMPETITOR_KEYS)
            if reads_stats:
                ledger.check("competitor", competitor, COMPETITOR_STATS_KEYS)
                bag = stats_bag(competitor)
                # Le bloc est vide avant le coup d'envoi, et un tableau vide
                # n'est pas une cle disparue : on ne juge que ce qui est
                # rempli, sinon un mardi de juillet passerait au rouge.
                if bag:
                    ledger.check("competitor.statistics", bag, stats_spec)
            team = competitor.get("team")
            if isinstance(team, dict):
                ledger.check("competitor.team", team, team_spec)
            sides[competitor.get("homeAway")] = competitor
        if "home" in sides and "away" in sides:
            tally["usable"] += 1
        else:
            ledger.anomaly("un match sans cote home et cote away")

        for detail in (competition.get("details") or []) if reads_details else ():
            if not isinstance(detail, dict):
                ledger.anomaly("un element de details n'est pas un objet")
                continue
            if flags_spec:
                ledger.check("detail", detail, flags_spec)
            scoring, red, shootout = kind_of(detail)
            if not scoring and not red:
                continue          # un carton jaune : espn.py n'en lit rien
            # Un tir au but est compte a part, comme espn.py le range a part :
            # il porte `scoringPlay` sans faire monter le score du match. Le
            # confondre avec un but ferait rougir le canari a chaque soiree de
            # coupe, pour un comportement voulu.
            if shootout:
                tally["shootout"] += 1
            elif scoring:
                tally["goals"] += 1
            else:
                tally["red_cards"] += 1
            ledger.check("detail", detail, detail_spec)

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


def scored_event(payload):
    """L'identifiant d'un match du tableau de bord qui a des buts, ou "".

    Un resume ne se demande que si l'on sait qu'il y a quelque chose dedans :
    inspecter le 0-0 d'un match a venir declarerait `plays` vide et
    `participants` absent, c'est-a-dire du rouge pour une reponse parfaitement
    normale.
    """
    for event in payload.get("events") or []:
        if not isinstance(event, dict):
            continue
        competitions = event.get("competitions") or []
        if not competitions or not isinstance(competitions[0], dict):
            continue
        total = 0
        for competitor in competitions[0].get("competitors") or []:
            if isinstance(competitor, dict):
                total += espn._int(competitor.get("score"))
        if total:
            identifier = str(event.get("id") or "").strip()
            if identifier:
                return identifier
    return ""


def inspect_summary(payload, ledger):
    """Le resume d'un match au peigne fin : d'ou viennent les buteurs du hockey."""
    tally = {"plays": 0, "goals": 0, "scorers": 0, "assists": 0}

    ledger.check("resume", payload, SUMMARY_PAYLOAD_KEYS)

    for play in payload.get("plays") or []:
        if not isinstance(play, dict):
            ledger.anomaly("un element de plays n'est pas un objet")
            continue
        tally["plays"] += 1
        ledger.check("resume.plays[]", play, PLAY_TYPE_KEYS)

        kind = play.get("type") or {}
        type_id = str((kind.get("id") if isinstance(kind, dict) else "") or "")
        text = str((kind.get("text") if isinstance(kind, dict) else "") or "")
        if (type_id.strip() not in espn.GOAL_PLAY_TYPES
                and text.strip().lower() != espn.GOAL_PLAY_TEXT):
            continue
        tally["goals"] += 1
        ledger.check("resume.but", play, GOAL_PLAY_KEYS)

        for participant in play.get("participants") or []:
            if not isinstance(participant, dict):
                ledger.anomaly("un element de participants n'est pas un objet")
                continue
            ledger.check("resume.but.participants[]", participant,
                         PARTICIPANT_KEYS)
            role = str(participant.get("type") or "").strip().lower()
            if role == espn.ROLE_SCORER:
                tally["scorers"] += 1
            elif role == espn.ROLE_ASSISTER:
                tally["assists"] += 1
    return tally


def summary_cross_check(payload, tally, ledger):
    """Le lecteur du programme retrouve-t-il encore les buts comptes a la main ?

    Meme raison que cross_check() : des cles presentes qui ne produisent plus
    un seul buteur seraient une derive aussi grave qu'une cle disparue, et elle
    ne se verrait nulle part ailleurs - la carte de hockey sortirait sans nom,
    comme avant, sans que rien ne casse.
    """
    problems = []
    goals = espn.summary_goals(payload)
    if len(goals) != tally["goals"]:
        problems.append("espn.summary_goals() rend {} but(s) la ou le resume "
                        "en compte {}".format(len(goals), tally["goals"]))
    # Le resume a ete demande pour un match dont le score avait bouge : n'y
    # trouver aucun but, c'est que le type d'action a change de nom ET de
    # numero. Le comptage a la main ne le verrait pas - il lit les memes deux
    # constantes que le programme - mais cette invariante-la, si.
    if tally["plays"] and not tally["goals"]:
        problems.append("{} action(s) dans le resume d'un match qui a marque, "
                        "et pas un seul but reconnu".format(tally["plays"]))
    if tally["goals"] and not any(goal.scorer for goal in goals):
        problems.append("aucun buteur nomme sur {} but(s) : la carte de hockey "
                        "redeviendrait muette".format(tally["goals"]))
    if tally["assists"] and not any(goal.assists for goal in goals):
        problems.append("aucun passeur lu alors que le resume en publie {}"
                        .format(tally["assists"]))
    return problems


def kicks_note(tally) -> str:
    """", 12 tir(s) au but" quand il y en a eu, une chaine vide sinon.

    Une seance est rare : l'annoncer a zero sur toutes les lignes du rapport
    ferait du bruit tous les jours pour un fait de quelques soirs par an.
    """
    if not tally.get("shootout"):
        return ""
    return ", {} tir(s) au but".format(tally["shootout"])


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

    kicks = sum(len(match.shootout) for match in matches)
    if kicks != tally["shootout"]:
        problems.append(
            "espn.parse() rend {} tir(s) au but la ou la reponse en compte {}"
            .format(kicks, tally["shootout"]))

    # Le drapeau `winner` ne se surveille que la : c'est le seul endroit ou la
    # reponse doit l'avoir. Sans lui, une carte de fin de match de coupe se
    # contente de dire "Tirs au but" - vrai, mais elle ne nomme plus celui qui
    # se qualifie, et c'est justement ce qu'on etait venu chercher.
    orphans = [match for match in matches
               if match.on_penalties and not match.winner]
    if orphans:
        problems.append(
            "{} match(s) decide(s) aux tirs au but sans drapeau winner : le "
            "vainqueur ne remonte plus".format(len(orphans)))

    if tally["goals"] and not any(play.scorer for match in matches
                                  for play in match.plays):
        problems.append("aucun buteur nomme sur {} but(s) : le nom du buteur "
                        "ne remonte plus".format(tally["goals"]))

    if matches and not any(match.home and match.away for match in matches):
        problems.append("aucun match ne porte le nom de ses deux equipes")

    # La derive qu'aucune cle ne trahirait : le rugby ne trie pas ses actions
    # par drapeau mais par numero de type, et un renumerotage laisserait toutes
    # les cles en place pour ne plus produire une seule action - le canari
    # comme espn.py lisant la meme table, ils se tromperaient ensemble. Le
    # tableau des scores, lui, continuerait d'afficher des points : c'est par
    # lui qu'on le saurait. Un match fini sans action publiee arrive ; toute
    # une journee de matchs finis avec des points au tableau, non.
    if league.sport.plays != sports.PLAYS_NONE:
        played = [match for match in matches
                  if match.state == espn.POST
                  and (match.home_score or 0) + (match.away_score or 0) > 0]
        if played and not any(match.plays for match in played):
            problems.append(
                "{} match(s) termine(s) avec des points au tableau et pas une "
                "seule action : le tri des actions ne reconnait plus rien"
                .format(len(played)))

    # La minute n'est pas qu'un ornement : c'est elle qui fait l'histogramme de
    # --stats. Une cle peut rester en place et changer de FORME - c'est arrive,
    # la source ecrivait 90'+9' quand le lecteur n'acceptait que 90+3', et les
    # buts des arrets de jeu ont cesse de compter sans que rien ne rougisse.
    # Le football seul : l'horloge d'un match de hockey (12:34) n'est pas une
    # minute de jeu et n'a pas a se lire comme telle.
    if league.sport is sports.SOCCER:
        written = [play.minute for match in matches for play in match.plays
                   if play.minute]
        if written and not any(journal.minute_of(one) for one in written):
            problems.append(
                "aucune des {} minute(s) de but n'est lisible (ex. {}) : la "
                "forme de l'horloge a change".format(
                    len(written), ", ".join(sorted(set(written))[:3])))

    return problems


# --------------------------------------------------------------- reseau ------

def http_opener(url, timeout):
    """L'appel reel. Les tests passent leur propre callable a la place.

    Les en-tetes sont ceux du daemon, pris chez lui (`espn.headers()`) et non
    recopies : le canari est cense voir ce que voit le programme, pas ce qu'un
    autre client verrait. C'est vrai depuis que la requete demande du gzip -
    une source qui compresserait mal ne casserait que le daemon, et le canari
    l'aurait annonce vert.
    """
    request = urllib.request.Request(url, headers=espn.headers())
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return espn.uncompress(response.read(), url)


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

    Meme ecriture que --leagues, ou le football est sous-entendu. Le sport
    decide de ce qu'on va regarder : les trois lisent le meme tableau de bord,
    mais seul le hockey va chercher ses buteurs dans le resume d'un match, et
    lui seul se voit donc ajouter les cles de `plays[]` a son programme.
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


def summary_url(slug, event_id):
    sport, code = split_sport(slug)
    return "{}?event={}".format(
        SUMMARY_URL.format(sport=sport.code, slug=code), event_id)


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
    sport, _ = split_sport(slug)
    plan = tuple(
        (scope, team_keys(sport) if scope == "competitor.team" else spec)
        for scope, spec in BOARD_PLAN)
    if sport.plays != sports.PLAYS_NONE:
        plan += details_plan(sport)
    if sport.team_stats:
        plan += (("competitor", COMPETITOR_STATS_KEYS),
                 ("competitor.statistics", stats_keys(sport)))
    if sport.summary_plays:
        plan += SUMMARY_PLAN
    ledger = Ledger(plan=plan + CATALOGUE_PLAN)
    problems = []

    print("--- {} {}".format(slug, "-" * (66 - len(slug))), file=out)

    try:
        first = fetch_json(scoreboard_url(slug, dates), opener, timeout)
    except espn.SourceError as exc:
        print("  INJOIGNABLE  {}\n".format(exc), file=out)
        return INJOIGNABLE, ledger

    boards = [first]
    tally = inspect_scoreboard(first, ledger, sport)
    problems.extend(cross_check(first, slug, tally, ledger))
    print("  releve {:<14} {} match(s), {} but(s), {} expulsion(s){}".format(
        dates or "le jour meme", tally["events"], tally["goals"],
        tally["red_cards"], kicks_note(tally)), file=out)

    # Rien a se mettre sous la dent : on va chercher un jour ou l'on a joue.
    # "Rien" ne veut pas dire la meme chose selon le sport. Au football, c'est
    # l'absence de but dans `details`. Au hockey, qui n'en publie jamais, ce
    # critere serait vrai tous les soirs et le canari repartirait chercher
    # quatre mois de NHL a chaque passage : ce qu'on cherche la, c'est un match
    # dont le score a bouge, le seul dont le resume aura des buts dedans.
    empty = (not scored_event(first) if sport.summary_plays
             else not tally["goals"])
    if not dates and empty:
        window = lookback_range()
        try:
            second = fetch_json(scoreboard_url(slug, window), opener, timeout)
        except espn.SourceError as exc:
            print("  INJOIGNABLE  {}\n".format(exc), file=out)
            return INJOIGNABLE, ledger
        boards.append(second)
        extra = inspect_scoreboard(second, ledger, sport)
        problems.extend(cross_check(second, slug, extra, ledger))
        print("  rattrapage {:<10} {} match(s), {} but(s), {} expulsion(s){}"
              .format(window, extra["events"], extra["goals"],
                      extra["red_cards"], kicks_note(extra)), file=out)
        for key in tally:
            tally[key] += extra[key]

    if not tally["events"]:
        print("  aucun match a inspecter : rien n'est verifie ici, et ce n'est"
              " pas un echec.", file=out)

    # Le resume d'un match, et un seul : c'est 450 ko, et la question posee ici
    # - "les cles de plays[] sont-elles encore la ?" - se repond aussi bien sur
    # un match que sur trente.
    if sport.summary_plays:
        event_id = ""
        for board in boards:
            event_id = scored_event(board)
            if event_id:
                break
        if not event_id:
            print("  resume         aucun match avec but : rien a inspecter",
                  file=out)
        else:
            try:
                digest = fetch_json(summary_url(slug, event_id), opener, timeout)
            except espn.SourceError as exc:
                print("  INJOIGNABLE  {}\n".format(exc), file=out)
                return INJOIGNABLE, ledger
            found = inspect_summary(digest, ledger)
            problems.extend(summary_cross_check(digest, found, ledger))
            print("  resume         match {}, {} action(s), {} but(s), "
                  "{} buteur(s), {} passe(s)"
                  .format(event_id, found["plays"], found["goals"],
                          found["scorers"], found["assists"]), file=out)

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
