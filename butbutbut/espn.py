"""Source des scores : le tableau de bord public d'ESPN.

    https://site.api.espn.com/apis/site/v2/sports/<sport>/<slug>/scoreboard

Pourquoi celle-la : pas de cle d'API, pas d'inscription, elle couvre les cinq
championnats, elle est mise a jour en direct et elle donne meme le buteur et la
minute. C'est une API publique mais non documentee : tout est lu de facon
defensive (une cle qui disparait ne doit pas tuer le daemon).

Le premier segment est le sport, et c'est la seule chose qui change d'un sport
a l'autre dans l'URL : `soccer/fra.1`, `hockey/nhl`, `rugby/180659`. La forme
de la reponse, elle, est presque la meme partout - presque, et c'est tout le
sujet de `_parse_details` :

  - le **football** publie ses actions dans `competitions[].details`, chacune
    portee par des drapeaux (`scoringPlay`, `redCard`, `ownGoal`...) ;
  - le **rugby** publie le meme tableau, mais **sans aucun drapeau** : c'est
    `type.id` qui dit ce qui s'est passe (1 essai, 2 transformation, 3
    penalite, 4 drop, 6 carton rouge). Lu avec le lecteur du football, un match
    de rugby n'aurait aucune action du tout ;
  - le **hockey** ne publie **rien** : `details` est absent, sur un match a
    venir comme sur un match termine. On a le score, l'horloge et la periode.

Le meme hote publie un second endpoint, le classement, sous une adresse qui
n'a pas tout a fait la meme forme (voir STANDINGS_URL, plus bas). Il est lu
avec le meme client et les memes en-tetes : c'est tout l'interet d'avoir un
seul endroit ou le reseau est touche.

Rien d'autre que la stdlib : urllib + json.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from . import __version__, i18n, crests, sports

SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/{sport}/{slug}/scoreboard"
TEAMS_URL = "https://site.api.espn.com/apis/site/v2/sports/{sport}/{slug}/teams"
# Le classement, et c'est bien `apis/v2` et non `apis/site/v2` comme les deux
# au-dessus : verifie contre la source, la forme `site/v2/.../standings` repond
# 200 avec un objet vide `{}`, ce qui ressemblerait a une intersaison alors que
# c'est juste la mauvaise adresse. Une faute qu'on n'a pas envie de refaire.
STANDINGS_URL = "https://site.api.espn.com/apis/v2/sports/{sport}/{slug}/standings"

USER_AGENT = "butbutbut/{} (+https://github.com/boubou666/butbutbut)".format(__version__)
DEFAULT_TIMEOUT = 8.0

# Le tableau de bord accepte un parametre `dates` : un jour (AAAAMMJJ) ou un
# intervalle (AAAAMMJJ-AAAAMMJJ), bornes comprises. Sans lui, il ne sert que la
# journee en cours - assez pour surveiller les buts, pas pour dire quand tombe
# le prochain match.
DAY_FORMAT = "%Y%m%d"

# Etats renvoyes par ESPN.
PRE, LIVE, POST = "pre", "in", "post"

# Phases d'un match. ESPN les nomme dans status.type.name : STATUS_SCHEDULED,
# STATUS_FIRST_HALF, STATUS_HALFTIME, STATUS_SECOND_HALF, STATUS_FULL_TIME...
SCHEDULED = "scheduled"
PLAYING = "playing"
HALFTIME = "halftime"
FINAL = "final"
UNKNOWN = "unknown"      # reporte, abandonne, suspendu : on ne signale rien

# Un match dans un de ces etats n'est pas "a venir" : il ne se joue pas du tout.
_STOPPED = ("POSTPONED", "CANCELED", "CANCELLED", "ABANDONED", "SUSPENDED",
            "DELAYED", "RESCHEDULED", "FORFEIT")

# Au-dela, on prefere le nom court : "Borussia Monchengladbach" tient mal.
NAME_LIMIT = 20


def phase_of(state: str, status_name: str, sport=None) -> str:
    """La phase du match, a partir de l'etat et du nom d'etat d'ESPN.

    La mi-temps des prolongations compte comme une mi-temps : le nom contient
    HALFTIME dans les deux cas.

    HALFTIME est ici le nom generique de la *pause*, pas celui de la mi-temps
    du football : le hockey n'a pas de mi-temps, il a deux pauses entre trois
    tiers-temps, et c'est le sport qui apporte les marqueurs supplementaires a
    reconnaitre (voir sports.py). Le mot qui s'affiche sur la carte, lui, suit
    le sport - "MI-TEMPS" ici, "FIN DU TIERS-TEMPS" la.
    """
    name = (status_name or "").upper()
    extra = sport.breaks if sport is not None else ()

    if "HALFTIME" in name or "HALF_TIME" in name:
        return HALFTIME
    if any(marker in name for marker in extra):
        return HALFTIME
    if any(word in name for word in _STOPPED):
        return UNKNOWN
    if state == LIVE:
        return PLAYING
    if state == POST:
        return FINAL
    if state == PRE:
        return SCHEDULED
    return UNKNOWN


class SourceError(RuntimeError):
    """Le tableau de bord n'a pas pu etre lu (reseau, HTTP, JSON casse)."""


# ---------------------------------------------------------------- modele -----

# La preposition ne se deduit pas du nom : "But" -> "But de ", mais
# "Carton rouge" -> "Carton rouge pour ", et l'allemand ne met rien du tout
# apres "Rote Karte". Tout ce qui n'est pas ici prend simplement "<cle>_by".
_BY_KEYS = {"red_card": "red_card_for"}

# Le titre de carte propre a une action. Un but ordinaire n'est pas la : son
# titre depend du sport (BUT ! au football et au hockey, POINTS ! au rugby),
# c'est donc le sport qui le donne, pas l'action.
_TITLE_KEYS = {
    "own_goal": "title_own_goal",
    "penalty": "title_penalty",
    "red_card": "title_red_card",
    "try": "title_try",
    "conversion": "title_conversion",
    "penalty_goal": "title_penalty_goal",
    "drop_goal": "title_drop_goal",
}

# La forme courte, entre parentheses, quand la carte de fin de match aligne
# plusieurs buteurs : "J. Lefort (csc) 17'", "L. Carter (essai) 8'".
_SHORT_KEYS = {
    "own_goal": "own_goal_short",
    "penalty": "penalty_short",
    "try": "try_short",
    "conversion": "conversion_short",
    "penalty_goal": "penalty_goal_short",
    "drop_goal": "drop_goal_short",
}


class Play:
    """Une action marquante d'un match : de quoi habiller une carte.

    Un but, un essai, une transformation, une expulsion. L'action porte
    elle-meme sa cle de vocabulaire (`kind_key`) et ce qu'elle vaut au score
    (`points`) : le reste du programme n'a alors plus jamais a se demander de
    quel sport vient la carte qu'il est en train d'ecrire.

    Les drapeaux `own_goal` / `penalty` / `red_card` restent la : ils viennent
    de la source pour le football, et c'est eux qui donnent la cle par defaut.
    """

    __slots__ = ("key", "team_id", "minute", "kind", "scorer", "own_goal",
                 "penalty", "shootout", "red_card", "kind_key", "points")

    def __init__(self, key, team_id, minute, kind, scorer, own_goal, penalty,
                 shootout, red_card=False, kind_key="", points=None):
        self.key = key
        self.team_id = team_id
        self.minute = minute          # 35' ou vide
        self.kind = kind              # Goal, Own Goal, try, penalty goal...
        self.scorer = scorer          # C. Arcus, ou vide
        self.own_goal = own_goal
        self.penalty = penalty
        self.shootout = shootout
        self.red_card = red_card
        # La cle de vocabulaire. Deduite des drapeaux du football quand elle
        # n'est pas donnee : un appelant qui construit un Play a l'ancienne
        # (les tests, par exemple) obtient exactement le meme resultat qu'avant.
        self.kind_key = kind_key or self._default_key()
        # Ce que l'action ajoute au score : 1 partout sauf au rugby, 0 pour une
        # expulsion. Sert a choisir l'action la plus parlante quand plusieurs
        # tombent entre deux releves.
        self.points = points if points is not None else (0 if red_card else 1)

    def _default_key(self) -> str:
        if self.red_card:
            return "red_card"
        if self.own_goal:
            return "own_goal"
        if self.penalty:
            return "penalty"
        return "goal"

    @property
    def title_key(self) -> str:
        """La cle du titre de carte, ou "" si c'est au sport de le dire."""
        return _TITLE_KEYS.get(self.kind_key, "")

    def prefix(self, lang=None) -> str:
        """La nature de l'action, sans le joueur, dans la langue demandee."""
        return i18n.text(self.kind_key, lang=lang)

    def prefix_for(self, lang=None) -> str:
        """La meme chose, suivie de sa preposition : "But de ", "Tor von ".

        On ne colle pas une preposition derriere prefix() : d'une langue a
        l'autre elle change, et l'allemand n'en met pas du tout apres une
        carte de carton rouge.
        """
        return i18n.text(_BY_KEYS.get(self.kind_key, self.kind_key + "_by"),
                         lang=lang)

    def short_mark(self, lang=None) -> str:
        """La mention entre parentheses : "csc", "sp", "essai". Vide si aucune.

        Un but ordinaire n'en a pas : le preciser sur une carte de football
        n'apprendrait rien a personne.
        """
        key = _SHORT_KEYS.get(self.kind_key)
        return i18n.text(key, lang=lang) if key else ""

    def summary(self, lang=None) -> str:
        """Une ligne : But de C. Arcus (35'), Tor von H. Kane (35')."""
        base = ((self.prefix_for(lang=lang) + self.scorer) if self.scorer
                else self.prefix(lang=lang))
        if self.minute:
            base += " (" + self.minute + ")"
        return base

    def __repr__(self):
        return "<Play {} {} {}>".format(self.minute, self.kind, self.scorer)


class Match:
    """Un match tel que le tableau de bord le decrit a l'instant T."""

    __slots__ = ("id", "league", "home", "away", "home_id", "away_id",
                 "home_names", "away_names", "home_score", "away_score",
                 "state", "status_name", "detail", "clock", "start", "plays",
                 "red_cards", "home_logo", "away_logo", "home_color",
                 "away_color", "home_alt", "away_alt")

    def __init__(self, id, league, home, away, home_id, away_id, home_score,
                 away_score, state, detail, clock, start, plays,
                 status_name="", home_names=(), away_names=(), red_cards=(),
                 home_logo="", away_logo="", home_color="", away_color="",
                 home_alt="", away_alt=""):
        self.id = id
        self.league = league
        self.home = home
        self.away = away
        self.home_id = home_id
        self.away_id = away_id
        # Tous les noms connus de chaque equipe : nom complet, nom court,
        # abreviation. C'est ce que le filtre par equipe interroge.
        self.home_names = tuple(home_names) or (home,)
        self.away_names = tuple(away_names) or (away,)
        self.home_score = home_score
        self.away_score = away_score
        self.state = state
        self.status_name = status_name  # STATUS_SECOND_HALF, STATUS_FULL_TIME...
        self.detail = detail          # FT, 45+2', Sun 6 Sep at 17:00...
        self.clock = clock            # la minute, quand le match est en cours
        self.start = start            # datetime UTC, ou None
        self.plays = plays            # list[Play] : les buts, et rien d'autre
        # Les expulsions sont tenues a part : `plays` habille les buts, et un
        # carton rouge n'a jamais decrit un but.
        self.red_cards = list(red_cards)
        # L'habillage du club : l'URL de son ecusson et ses deux couleurs, en
        # #rrggbb. Vides quand la source ne les donne pas.
        self.home_logo = home_logo
        self.away_logo = away_logo
        self.home_color = home_color
        self.away_color = away_color
        self.home_alt = home_alt
        self.away_alt = away_alt

    @property
    def sport(self):
        """Le sport de la competition. Le football quand rien ne le dit."""
        return getattr(self.league, "sport", None) or sports.DEFAULT

    @property
    def phase(self) -> str:
        """scheduled / playing / halftime / final / unknown."""
        return phase_of(self.state, self.status_name, self.sport)

    @property
    def live(self) -> bool:
        return self.state == LIVE

    @property
    def finished(self) -> bool:
        return self.state == POST

    def score_line(self) -> str:
        return "{} {} - {} {}".format(self.home, self.home_score,
                                      self.away_score, self.away)

    def seconds_until_kickoff(self, now=None) -> float | None:
        if self.start is None:
            return None
        now = now or datetime.now(timezone.utc)
        return (self.start - now).total_seconds()

    def plays_for(self, team_id) -> list:
        return [play for play in self.plays if play.team_id == team_id]

    def side_of(self, team_id) -> str:
        """"home", "away", ou "" quand la source ne nomme pas l'equipe."""
        if team_id and team_id == self.home_id:
            return "home"
        if team_id and team_id == self.away_id:
            return "away"
        return ""

    def __repr__(self):
        return "<Match {} {} [{}]>".format(self.league.slug, self.score_line(), self.state)


# ---------------------------------------------------------------- reseau -----

def headers() -> dict:
    """Les en-tetes de toutes nos requetes, en un seul endroit."""
    return {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Accept-Language": "fr,en;q=0.8",
        "Cache-Control": "no-cache",
    }


def download(url: str, timeout: float = DEFAULT_TIMEOUT, label: str = "") -> bytes:
    """La requete brute vers la source, sans rien interpreter.

    Sortie du corps de fetch() pour qu'il existe un seul endroit ou le reseau
    est touche : c'est ce qu'appelle `replay.Recorder` quand il se pose entre
    le programme et la source. `label` n'est la que pour le message d'erreur -
    le code du championnat parle mieux qu'une URL de cent caracteres.
    """
    label = label or url
    request = urllib.request.Request(url, headers=headers())
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        raise SourceError("HTTP {} sur {}".format(exc.code, label)) from exc
    except Exception as exc:          # URLError, socket.timeout, ssl...
        raise SourceError("{} sur {} : {}".format(
            type(exc).__name__, label, exc)) from exc


def day_code(moment) -> str:
    """Un jour dans la forme attendue par `dates` : AAAAMMJJ."""
    return moment.strftime(DAY_FORMAT)


def date_span(first, last=None) -> str:
    """La valeur du parametre `dates` : un jour, ou un intervalle.

    Verifie contre la source : `?dates=20260906` rend le programme de ce
    jour-la, `?dates=20260906-20260919` celui de toute la periode, les deux
    bornes comprises. C'est ce qui permet a `--next` de couvrir une semaine
    entiere en **une** requete par competition la ou un jour a la fois en
    couterait sept.
    """
    start = day_code(first)
    if last is None:
        return start
    end = day_code(last)
    # Un intervalle d'un seul jour n'apporte rien : autant poser la forme
    # courte, celle qu'on lit dans les journaux et dans les tests.
    return start if end == start else "{}-{}".format(start, end)


def _read_json(url: str, timeout: float, opener, label: str) -> dict:
    """Une requete + un decodage, la seule facon d'aller chercher du JSON ici.

    Sortie du corps de fetch() le jour ou le classement a eu besoin exactement
    du meme chemin : memes en-tetes, meme delai, meme facon de traduire une
    panne en SourceError. Deux facons d'appeler ESPN auraient fini par diverger
    - l'une avec l'en-tete de politesse, l'autre sans.
    """
    if opener is not None:
        try:
            raw = opener(url, timeout)
        except SourceError:
            raise
        except Exception as exc:
            raise SourceError(str(exc)) from exc
    else:
        raw = download(url, timeout, label=label)

    try:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", "replace")
        payload = json.loads(raw)
    except Exception as exc:
        raise SourceError("reponse illisible pour {} : {}".format(label, exc)) from exc

    if not isinstance(payload, dict):
        raise SourceError("reponse inattendue pour " + label)
    return payload


def fetch(slug: str, timeout: float = DEFAULT_TIMEOUT, opener=None,
          sport=None, dates=None) -> dict:
    """Recupere le tableau de bord brut d'une competition.

    `sport` : un sports.Sport, ou None pour le football. Il n'y a rien d'autre
    a passer : le sport n'est qu'un segment d'URL a ce niveau-la.

    `dates` (voir date_span) demande une autre periode que la journee
    en cours.

    `opener` sert aux tests et a l'enregistrement : n'importe quel
    callable(url, timeout) -> bytes.
    """
    url = SCOREBOARD_URL.format(sport=(sport or sports.DEFAULT).code,
                                slug=slug)
    if dates:
        url += "?" + urllib.parse.urlencode({"dates": dates})
    return _read_json(url, timeout, opener, slug)


# ---------------------------------------------------------------- parsing ----

def _int(value, default=0) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _team_name(competitor) -> str:
    """Nom lisible : le nom complet, ou le nom court s'il est trop long."""
    team = competitor.get("team") or {}
    full = (team.get("displayName") or "").strip()
    short = (team.get("shortDisplayName") or "").strip()
    if full and len(full) <= NAME_LIMIT:
        return full
    return short or full or (team.get("abbreviation") or "?")


def team_names(competitor) -> tuple:
    """Tous les noms d'une equipe, du plus lisible au plus court."""
    team = competitor.get("team") or {}
    names = (team.get("displayName"), team.get("shortDisplayName"),
             team.get("name"), team.get("location"), team.get("abbreviation"))
    return tuple(str(name).strip() for name in names if name)


def team_colors(competitor) -> tuple:
    """(couleur, couleur secondaire) d'une equipe, en "#rrggbb".

    ESPN les ecrit sans le diese ("0000bf"), et pas toujours : une chaine vide
    signale simplement qu'on ne sait pas.
    """
    team = competitor.get("team") or {}
    return (crests.normalize(team.get("color")) or "",
            crests.normalize(team.get("alternateColor")) or "")


def team_logo(competitor) -> str:
    """URL du PNG de l'ecusson, ou une chaine vide.

    Seul http(s) est accepte : ce qui sortira de la est telecharge sans qu'on
    le regarde de plus pres.
    """
    team = competitor.get("team") or {}
    url = team.get("logo")
    if not url:
        for entry in team.get("logos") or []:
            if isinstance(entry, dict) and entry.get("href"):
                url = entry["href"]
                break
    url = str(url or "").strip()
    return url if url.lower().startswith(("http://", "https://")) else ""


def logo_url(team_id, sport=None) -> str:
    """L'ecusson d'une equipe a partir de son seul identifiant ESPN.

    Ne sert qu'aux cartes de demonstration : partout ailleurs l'URL arrive avec
    les scores. C'est heureux, parce que le rangement change d'un sport a
    l'autre - le hockey classe ses ecussons sous l'abreviation du club ("bos")
    et non sous son numero, et un sport sans modele connu rend une chaine vide
    plutot qu'une URL inventee.
    """
    pattern = (sport or sports.DEFAULT).logo_pattern
    return pattern.format(id=team_id) if pattern else ""


def _parse_date(value) -> datetime | None:
    """Date ISO d'ESPN, souvent 2026-09-06T18:45Z. Renvoie un datetime UTC."""
    if not value:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    parsers = (
        lambda t: datetime.fromisoformat(t),
        lambda t: datetime.strptime(t, "%Y-%m-%dT%H:%M%z"),
        lambda t: datetime.strptime(t, "%Y-%m-%dT%H:%M:%S%z"),
    )
    for parser in parsers:
        try:
            parsed = parser(text)
        except Exception:
            continue
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    return None


def _detail_common(detail) -> tuple:
    """(minute, id d'equipe, nom du joueur, id du joueur) d'une action.

    L'enveloppe est la meme pour les trois sports - une horloge, une equipe,
    un joueur ; c'est ce qu'elle contient qui change, et c'est ce que les deux
    lecteurs ci-dessous savent lire chacun a sa facon.
    """
    clock = (detail.get("clock") or {}).get("displayValue") or ""
    team_id = str(((detail.get("team") or {}).get("id") or "")).strip()

    athletes = detail.get("athletesInvolved") or []
    scorer = ""
    athlete_id = ""
    if athletes and isinstance(athletes[0], dict):
        scorer = (athletes[0].get("shortName")
                  or athletes[0].get("displayName") or "").strip()
        athlete_id = str(athletes[0].get("id") or "")
    return str(clock).strip(), team_id, scorer, athlete_id


def _soccer_details(competition) -> tuple:
    """(buts, cartons rouges) d'un match de football.

    Les deux vivent dans le meme tableau `details` : un but porte
    `scoringPlay`, une expulsion porte `redCard`. Ils sont separes ici parce
    qu'ils ne servent pas a la meme chose (un but est habille par un buteur,
    une expulsion se signale pour elle-meme).
    """
    goals = []
    red_cards = []
    for index, detail in enumerate(competition.get("details") or []):
        if not isinstance(detail, dict):
            continue
        scoring = bool(detail.get("scoringPlay"))
        red = bool(detail.get("redCard"))
        if not scoring and not red:
            continue

        kind = ((detail.get("type") or {}).get("text")
                or ("Goal" if scoring else "Red Card")).strip()
        clock, team_id, scorer, athlete_id = _detail_common(detail)

        # Cle stable : la meme action relue dix fois garde la meme identite.
        key = "|".join((team_id, str(clock), kind, athlete_id, str(index)))

        play = Play(
            key=key,
            team_id=team_id,
            minute=clock,
            kind=kind,
            scorer=scorer,
            own_goal=bool(detail.get("ownGoal")),
            penalty=bool(detail.get("penaltyKick")),
            shootout=bool(detail.get("shootout")),
            red_card=red and not scoring,
        )
        # Un but reste un but, meme si la source colle les deux drapeaux.
        (goals if scoring else red_cards).append(play)
    return goals, red_cards


# Ce que le rugby publie, releve sur la vraie source (Top 14, Six Nations,
# URC, Premiership, Super Rugby, Rugby Championship, Coupe du monde) :
# 1 essai, 2 transformation, 3 penalite, 4 drop, 5 carton jaune, 6 carton
# rouge, 7/8 remplacements, 9 a 12 les bornes de mi-temps, 37 drop manque.
# Aucun drapeau nulle part : `type.id` est la seule information.
RUGBY_SCORES = {
    "1": ("try", 5),
    "2": ("conversion", 2),
    "3": ("penalty_goal", 3),
    "4": ("drop_goal", 3),
}
# Le meme tableau par le libelle, au cas ou les numeros bougeraient un jour.
# La correspondance est exacte et non par prefixe : "drop goal-missed" ne doit
# surtout pas passer pour un drop reussi.
RUGBY_SCORES_BY_TEXT = {
    "try": ("try", 5),
    "conversion": ("conversion", 2),
    "penalty goal": ("penalty_goal", 3),
    "drop goal": ("drop_goal", 3),
}
RUGBY_RED_CARD = ("6",)

# Le carton jaune (type 5) n'est pas signale : au rugby c'est une exclusion
# temporaire de dix minutes, pas une expulsion. Le confondre avec un carton
# rouge donnerait une carte qui ment.


def _rugby_details(competition) -> tuple:
    """(actions de points, cartons rouges) d'un match de rugby.

    Meme tableau `details` qu'au football, mais sans le moindre drapeau : la
    nature de l'action se lit dans `type.id`, et son nom dans `type.text`. Une
    action inconnue (remplacement, borne de mi-temps, drop manque) est ignoree
    en silence, comme au football.
    """
    scores = []
    red_cards = []
    for index, detail in enumerate(competition.get("details") or []):
        if not isinstance(detail, dict):
            continue
        kind_type = detail.get("type") or {}
        type_id = str(kind_type.get("id") or "").strip()
        text = str(kind_type.get("text") or "").strip()

        scored = RUGBY_SCORES.get(type_id) or RUGBY_SCORES_BY_TEXT.get(text.lower())
        red = type_id in RUGBY_RED_CARD or text.lower() == "red card"
        if scored is None and not red:
            continue

        clock, team_id, scorer, athlete_id = _detail_common(detail)
        kind_key, points = scored if scored else ("red_card", 0)
        key = "|".join((team_id, clock, text or kind_key, athlete_id, str(index)))

        play = Play(
            key=key,
            team_id=team_id,
            minute=clock,
            kind=text or kind_key,
            scorer=scorer,
            own_goal=False,
            penalty=False,
            shootout=False,
            red_card=bool(red and scored is None),
            kind_key=kind_key,
            points=points,
        )
        (red_cards if scored is None else scores).append(play)
    return scores, red_cards


def _parse_details(competition, sport=None) -> tuple:
    """(actions de score, cartons rouges) du match, selon le sport.

    Le hockey passe par la branche vide : la source ne publie pas de tableau
    d'actions pour lui, et inventer un buteur serait pire que de n'en afficher
    aucun.
    """
    sport = sport or sports.DEFAULT
    if sport.plays == sports.PLAYS_TYPES:
        return _rugby_details(competition)
    if sport.plays == sports.PLAYS_NONE:
        return [], []
    return _soccer_details(competition)


def parse(payload: dict, league) -> list:
    """Transforme un tableau de bord ESPN en liste de Match.

    Tout evenement mal forme est ignore plutot que de faire echouer le lot.
    """
    sport = getattr(league, "sport", None) or sports.DEFAULT

    # Une competition ouverte a la volee (un code ESPN passe a --leagues) prend
    # ici le nom que la source annonce.
    if getattr(league, "provisional", False):
        header = (payload.get("leagues") or [{}])[0]
        if isinstance(header, dict):
            league.adopt_name(header.get("name"), header.get("abbreviation"))

    matches = []
    for event in payload.get("events") or []:
        if not isinstance(event, dict):
            continue
        competitions = event.get("competitions") or []
        if not competitions or not isinstance(competitions[0], dict):
            continue
        competition = competitions[0]

        home = away = None
        for competitor in competition.get("competitors") or []:
            if not isinstance(competitor, dict):
                continue
            if competitor.get("homeAway") == "home":
                home = competitor
            elif competitor.get("homeAway") == "away":
                away = competitor
        if home is None or away is None:
            continue

        status = competition.get("status") or event.get("status") or {}
        status_type = status.get("type") or {}
        state = (status_type.get("state") or "").strip().lower() or PRE
        status_name = str(status_type.get("name") or "").strip()
        detail = (status_type.get("shortDetail")
                  or status_type.get("detail")
                  or status_type.get("description") or "").strip()
        clock = str(status.get("displayClock") or "").strip()

        match_id = str(event.get("id") or competition.get("id") or "").strip()
        if not match_id:
            continue

        goals, red_cards = _parse_details(competition, sport)
        home_color, home_alt = team_colors(home)
        away_color, away_alt = team_colors(away)

        matches.append(Match(
            id=match_id,
            league=league,
            home=_team_name(home),
            away=_team_name(away),
            home_id=str((home.get("team") or {}).get("id") or "H"),
            away_id=str((away.get("team") or {}).get("id") or "A"),
            home_names=team_names(home),
            away_names=team_names(away),
            home_score=_int(home.get("score")),
            away_score=_int(away.get("score")),
            state=state,
            status_name=status_name,
            detail=detail,
            clock=clock,
            start=_parse_date(competition.get("date") or event.get("date")),
            plays=goals,
            red_cards=red_cards,
            home_logo=team_logo(home),
            away_logo=team_logo(away),
            home_color=home_color,
            away_color=away_color,
            home_alt=home_alt,
            away_alt=away_alt,
        ))
    return matches


def scoreboard(league, timeout: float = DEFAULT_TIMEOUT, opener=None,
               dates=None) -> list:
    """fetch + parse, pour une competition, quel que soit son sport."""
    sport = getattr(league, "sport", None) or sports.DEFAULT
    return parse(fetch(league.slug, timeout=timeout, opener=opener,
                       sport=sport, dates=dates), league)


def catalogue(league, timeout: float = DEFAULT_TIMEOUT, opener=None) -> list:
    """Toutes les equipes d'une competition : une liste de tuples de noms.

    Sert a valider ce que l'utilisateur a tape dans --teams, et a repondre a
    --list-teams. Une competition qui ne repond pas (certaines coupes) rend
    une liste vide plutot qu'une erreur : on ne bloque pas pour ca.
    """
    sport = getattr(league, "sport", None) or sports.DEFAULT
    url = TEAMS_URL.format(sport=sport.code, slug=league.slug)
    try:
        if opener is not None:
            raw = opener(url, timeout)
        else:
            raw = download(url, timeout, label=league.slug)
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", "replace")
        payload = json.loads(raw)
    except Exception:
        return []

    try:
        groups = (payload.get("sports") or [{}])[0].get("leagues") or [{}]
        entries = groups[0].get("teams") or []
    except Exception:
        return []

    found = []
    for entry in entries:
        if isinstance(entry, dict):
            names = team_names(entry)
            if names:
                found.append(names)
    return found


# ------------------------------------------------------------- classement ----
# Le classement ne vient pas du tableau de bord mais d'un endpoint a lui, et sa
# forme est celle-ci, relevee sur les trois sports :
#
#   { "name": "French Ligue 1",
#     "children": [ { "name": "...", "standings": { "entries": [...] } } ] }
#
# `children` est la vraie particularite : c'est toujours une LISTE de blocs,
# meme quand il n'y en a qu'un. Un championnat en a un, la NHL en a deux (ses
# conferences), une Coupe du monde en a douze (ses groupes). Les traiter tous
# de la meme facon evite d'ecrire un cas "championnat" et un cas "poules".
#
# Une equipe y est decrite par `team` - le meme objet que sur le tableau de
# bord, d'ou la reutilisation de _team_name et team_names - et par `stats`, une
# liste plate de statistiques nommees. Plate et non ordonnee : on l'indexe, et
# c'est le sport qui dit ensuite quelles colonnes il compte (voir sports.py).

# La saison, telle qu'ESPN l'ecrit : "2026-27 French Ligue 1", "2025-26",
# "2026". Seule la partie annees nous interesse - le reste repete le nom de la
# competition, qu'on vient d'afficher, et en anglais par-dessus le marche.
SEASON_YEARS = re.compile(r"^\s*(\d{4}(?:\s*[-/]\s*\d{2,4})?)")

# Le rang, tel que la source le nomme : `rank` au football et au rugby,
# `playoffSeed` au hockey, qui n'a pas de `rank` du tout. C'est la seule
# position qu'on affiche - voir _parse_group pour pourquoi on ne la calcule
# jamais soi-meme.
RANK_KEYS = ("rank", "playoffseed")


class Row:
    """La ligne d'une equipe dans un classement.

    `stats` est un dictionnaire de chaines deja pretes a afficher : la source
    donne pour chaque statistique une valeur numerique **et** son ecriture
    ("+4" et non "4.0" pour une difference de buts). On garde l'ecriture, parce
    que c'est elle qui porte le signe.

    La ligne ne retient que ce qui s'affiche ou se cherche. La source dit aussi
    la zone de qualification ("Champions League", "Relegation") et sa couleur :
    de quoi habiller un tableau, pas un terminal de 80 colonnes ou chaque signe
    est deja pris. On ne le lit donc pas - le jour ou une carte en aura besoin,
    il sera temps.
    """

    __slots__ = ("rank", "team", "names", "stats")

    def __init__(self, rank, team, names=(), stats=None):
        self.rank = rank              # le rang affiche, 1 pour le premier
        self.team = team              # nom lisible
        self.names = tuple(names) or (team,)   # toutes les ecritures connues
        self.stats = dict(stats or {})

    def cell(self, keys) -> str:
        """La valeur de la premiere de ces cles, ou un tiret.

        Un tiret et non un zero : une statistique absente n'est pas une
        statistique nulle, et une colonne de zeros ferait croire a un
        championnat qui n'aurait jamais commence.
        """
        for key in keys:
            value = self.stats.get(key)
            if value not in (None, ""):
                return value
        return "-"

    def __repr__(self):
        return "<Row {} {}>".format(self.rank, self.team)


class Group:
    """Un bloc de classement : un championnat, une poule, une conference."""

    __slots__ = ("name", "rows")

    def __init__(self, name, rows=()):
        self.name = name
        self.rows = list(rows)

    def __repr__(self):
        return "<Group {} ({})>".format(self.name, len(self.rows))


class Table:
    """Le classement d'une competition, tel que la source le publie."""

    __slots__ = ("league", "season", "groups")

    def __init__(self, league, season="", groups=()):
        self.league = league
        self.season = season          # "2026-27", ou vide
        self.groups = list(groups)

    @property
    def sport(self):
        return getattr(self.league, "sport", None) or sports.DEFAULT

    @property
    def empty(self) -> bool:
        """Vrai quand il n'y a pas une seule ligne a montrer.

        Une coupe rend un objet complet mais sans `children` du tout, et un
        tournoi entre deux editions rend un `children` sans `entries` : les
        deux se ressemblent assez pour ne meriter qu'une seule reponse.
        """
        return not any(group.rows for group in self.groups)

    def __repr__(self):
        return "<Table {} ({})>".format(self.league.slug, len(self.groups))


def season_label(value) -> str:
    """La saison en quelques signes : "2026-27" plutot que sa phrase entiere."""
    found = SEASON_YEARS.match(str(value or ""))
    return found.group(1).replace(" ", "") if found else ""


def _stats_of(entry) -> dict:
    """Les statistiques d'une ligne, indexees par tous leurs noms.

    ESPN nomme chaque statistique deux fois - `type` ("gamesplayed") et `name`
    ("gamesPlayed") - et les deux ne concordent pas toujours d'un sport a
    l'autre : le rugby compte ses victoires sous `gamesWon`, le football sous
    `wins`. On range sous les deux, en minuscules : la colonne retrouve alors
    sa valeur quel que soit le nom qui a survecu.
    """
    found = {}
    for stat in entry.get("stats") or []:
        if not isinstance(stat, dict):
            continue
        value = stat.get("displayValue")
        if value in (None, ""):
            continue
        for key in (stat.get("type"), stat.get("name")):
            key = str(key or "").strip().lower()
            if key and key not in found:
                found[key] = str(value).strip()
    return found


def _rank_of(stats) -> int | None:
    """Le rang publie par la source, ou None quand elle n'en publie pas."""
    for key in RANK_KEYS:
        found = _int(stats.get(key), 0)
        if found > 0:
            return found
    return None


def _parse_group(child) -> Group:
    """Un bloc de `children` : son nom et ses lignes, rangees par leur rang.

    On affiche le rang que la source publie, et on ne le calcule jamais : le
    depart entre deux equipes a egalite se joue sur des regles propres a chaque
    competition (difference de buts, confrontations directes, essais marques),
    et les refaire ici finirait par mentir un jour, sur une competition qu'on
    n'aura pas regardee.

    Le tri, lui, est necessaire, et c'est une surprise de la source : un
    championnat arrive bien trie, mais un groupe de Coupe du monde arrive dans
    le desordre et la conference Ouest de la NHL commence a sa 4e tete de
    serie. L'ordre de la liste ne veut donc rien dire ; le rang, si. Quand la
    source n'en donne aucun, on garde son ordre et on numerote les lignes -
    c'est tout ce qu'on peut faire d'honnete.
    """
    standings_of = child.get("standings") or {}
    name = str(child.get("name") or child.get("shortName") or "").strip()

    rows = []
    ranked = True
    for position, entry in enumerate(standings_of.get("entries") or [], start=1):
        if not isinstance(entry, dict):
            continue
        team = entry.get("team")
        if not isinstance(team, dict):
            continue
        wrapper = {"team": team}
        stats = _stats_of(entry)
        rank = _rank_of(stats)
        if rank is None:
            ranked = False
            rank = position
        rows.append(Row(
            rank=rank,
            team=_team_name(wrapper),
            names=team_names(wrapper),
            stats=stats,
        ))

    if ranked:
        rows.sort(key=lambda row: row.rank)
    return Group(name, rows)


def parse_standings(payload: dict, league) -> Table:
    """Transforme la reponse du classement en Table. Ne leve jamais.

    Une competition ouverte a la volee prend ici le nom que la source annonce,
    exactement comme sur le tableau de bord : `--table gre.1` doit pouvoir
    s'afficher sous son vrai nom des la premiere requete.
    """
    if getattr(league, "provisional", False):
        league.adopt_name(payload.get("name"), payload.get("abbreviation"))

    children = payload.get("children")
    children = children if isinstance(children, list) else []

    season = ""
    groups = []
    for child in children:
        if not isinstance(child, dict):
            continue
        groups.append(_parse_group(child))
        if not season:
            season = season_label(
                (child.get("standings") or {}).get("seasonDisplayName"))

    if not season:
        # Le repli : la saison en cours d'apres l'en-tete. Elle peut differer
        # de celle du classement servi - en intersaison, la source rend encore
        # celui de la saison passee - d'ou l'ordre : le classement d'abord,
        # l'en-tete seulement s'il n'a rien dit.
        season = season_label((payload.get("season") or {}).get("displayName"))
    return Table(league, season=season, groups=groups)


def standings(league, timeout: float = DEFAULT_TIMEOUT, opener=None) -> Table:
    """Le classement d'une competition, quel que soit son sport."""
    sport = getattr(league, "sport", None) or sports.DEFAULT
    url = STANDINGS_URL.format(sport=sport.code, slug=league.slug)
    return parse_standings(_read_json(url, timeout, opener, league.slug),
                           league)
