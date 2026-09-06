"""Les competitions surveillees.

Par defaut : les cinq grands championnats. Mais la source (le tableau de bord
d'ESPN) en expose bien d'autres, et tout ce qu'elle sert a la meme forme : un
catalogue suffit donc a les ouvrir.

    butbutbut --leagues l1,ligue2,ucl      # choix explicite
    butbutbut --exclude liga,seriea        # les 5 moins deux
    butbutbut --leagues all                # tout le catalogue
    butbutbut --leagues por.1              # n'importe quel code ESPN

Chaque competition porte son code ESPN (`slug`), son nom d'affichage, son
etiquette de carte et sa couleur. Les alias servent a la ligne de commande.
"""

from __future__ import annotations

import re

from . import i18n

# Un code ESPN ressemble a "fra.1", "uefa.champions", "fra.coupe_de_france".
SLUG_SHAPE = re.compile(r"^[a-z]{2,8}(?:\.[a-z0-9_]+)+$")

# Couleur des competitions ouvertes a la volee, hors catalogue.
NEUTRAL_ACCENT = "#7cc0ff"


class League:
    """Une competition : identite ESPN + habillage de la carte."""

    __slots__ = ("slug", "name", "_label", "accent", "aliases", "provisional",
                 "key")

    def __init__(self, slug, name, label, accent, aliases=(), provisional=False,
                 key=""):
        self.slug = slug              # code ESPN, ex. "fra.1"
        self.name = name              # "Ligue 1"
        self._label = label           # "LIGUE 1", pour l'en-tete de la carte
        # Cle de traduction, pour les competitions dont le nom se traduit. La
        # Bundesliga ou la Coupe de France s'ecrivent pareil partout ; la Ligue
        # des champions, non.
        self.key = key
        self.accent = accent          # couleur de la competition sur la carte
        self.aliases = tuple(aliases)
        # Vrai pour une competition ouverte a la volee : on ne connait pas
        # encore son vrai nom, la source nous le dira au premier releve.
        self.provisional = provisional

    @property
    def label(self) -> str:
        """L'etiquette de la carte, dans la langue courante."""
        return i18n.text(self.key) if self.key else self._label

    def matches_token(self, token: str) -> bool:
        token = token.strip().lower()
        return (token in (self.slug, self.name.lower(), self.label.lower())
                or token in self.aliases)

    def adopt_name(self, name, abbreviation=None) -> None:
        """Prend le nom que la source annonce (competitions hors catalogue)."""
        if not self.provisional or not name:
            return
        self.name = str(name).strip()
        self._label = str(abbreviation or name).strip().upper()
        self.provisional = False

    def __repr__(self):
        return "<League {} {}>".format(self.slug, self.name)


# --- Les cinq grands : ce que butbutbut suit sans rien demander --------------

LEAGUES = (
    League("fra.1", "Ligue 1", "LIGUE 1", "#f2e34c",
           ("l1", "ligue1", "ligue-1", "fra", "france", "fr")),
    League("eng.1", "Premier League", "PREMIER LEAGUE", "#00ff87",
           ("pl", "epl", "premier", "premierleague", "eng", "angleterre")),
    League("esp.1", "LaLiga", "LA LIGA", "#ff6b5e",
           ("liga", "laliga", "la-liga", "esp", "espagne", "es")),
    League("ita.1", "Serie A", "SERIE A", "#5ab7ff",
           ("seriea", "serie-a", "ita", "italie", "it")),
    League("ger.1", "Bundesliga", "BUNDESLIGA", "#ff5c5c",
           ("bl", "bundes", "bundesliga", "ger", "allemagne", "de")),
)

# --- Le reste du catalogue : a demander explicitement ------------------------
# Tous ces codes ont ete verifies contre la source.

EXTRA = (
    # Coupes d'Europe
    League("uefa.champions", "Ligue des champions", "LIGUE DES CHAMPIONS", "#4c6ef5",
           ("ucl", "ldc", "c1", "champions", "championsleague"),
           key="league_ucl"),
    League("uefa.europa", "Ligue Europa", "LIGUE EUROPA", "#ff922b",
           ("uel", "europa", "c3", "europaleague"),
           key="league_uel"),
    League("uefa.europa.conf", "Ligue Conference", "LIGUE CONFERENCE", "#51cf66",
           ("uecl", "conference", "conf", "c4"),
           key="league_uecl"),
    League("uefa.super_cup", "Supercoupe d'Europe", "SUPERCOUPE UEFA", "#845ef7",
           ("supercoupe", "uefasupercup"),
           key="league_usc"),
    # Selections
    League("uefa.nations", "Ligue des nations", "LIGUE DES NATIONS", "#22b8cf",
           ("nations", "ldn", "nationsleague"),
           key="league_nations"),
    League("fifa.world", "Coupe du monde", "COUPE DU MONDE", "#fcc419",
           ("cdm", "mondial", "worldcup", "wc"),
           key="league_wc"),
    League("fifa.worldq.uefa", "Qualif. Coupe du monde (UEFA)", "QUALIF. CDM", "#a9b4c4",
           ("qualifs", "wcq", "eliminatoires"),
           key="league_wcq"),
    # Deuxiemes divisions
    League("fra.2", "Ligue 2", "LIGUE 2", "#c0b32a",
           ("l2", "ligue2", "ligue-2", "fra2")),
    League("eng.2", "Championship", "CHAMPIONSHIP", "#2f9e6a",
           ("championship", "efl", "eng2")),
    League("esp.2", "LaLiga 2", "LA LIGA 2", "#c9564b",
           ("liga2", "laliga2", "esp2")),
    League("ita.2", "Serie B", "SERIE B", "#3f8fc4",
           ("serieb", "serie-b", "ita2")),
    League("ger.2", "2. Bundesliga", "2. BUNDESLIGA", "#c74848",
           ("bundesliga2", "bl2", "ger2")),
    # Autres championnats europeens
    League("por.1", "Primeira Liga", "PRIMEIRA LIGA", "#38d9a9",
           ("portugal", "primeira", "por", "pt")),
    League("ned.1", "Eredivisie", "EREDIVISIE", "#ff8c42",
           ("eredivisie", "ned", "paysbas", "nl")),
    League("bel.1", "Pro League", "PRO LEAGUE", "#e8a33d",
           ("belgique", "jupiler", "bel", "be")),
    League("tur.1", "Super Lig", "SUPER LIG", "#e64980",
           ("superlig", "turquie", "tur", "tr")),
    League("sco.1", "Scottish Premiership", "SCOTTISH PREM", "#748ffc",
           ("ecosse", "premiership", "sco")),
    # Coupes nationales
    League("fra.coupe_de_france", "Coupe de France", "COUPE DE FRANCE", "#4dabf7",
           ("cdf", "coupedefrance", "coupe")),
    League("eng.fa", "FA Cup", "FA CUP", "#69db7c",
           ("facup", "fa")),
    League("eng.league_cup", "Carabao Cup", "CARABAO CUP", "#4dd4ac",
           ("carabao", "leaguecup", "eflcup")),
    League("esp.copa_del_rey", "Copa del Rey", "COPA DEL REY", "#ff8787",
           ("copa", "copadelrey")),
    League("ita.coppa_italia", "Coppa Italia", "COPPA ITALIA", "#74c0fc",
           ("coppa", "coppaitalia")),
    League("ger.dfb_pokal", "Coupe d'Allemagne", "DFB-POKAL", "#ffa8a8",
           ("dfb", "dfbpokal", "pokal")),
    # Hors d'Europe
    League("usa.1", "MLS", "MLS", "#20c997", ("mls", "usa", "etatsunis")),
    League("mex.1", "Liga MX", "LIGA MX", "#94d82d", ("ligamx", "mex", "mexique")),
    League("bra.1", "Brasileirao", "BRASILEIRAO", "#ffd43b",
           ("bra", "bresil", "brasileirao", "brasil")),
    League("arg.1", "Liga Profesional", "LIGA PROFESIONAL", "#66d9e8",
           ("arg", "argentine", "lpf")),
    League("ksa.1", "Saudi Pro League", "SAUDI PRO LEAGUE", "#37b24d",
           ("saudi", "ksa", "arabie")),
    League("jpn.1", "J.League", "J.LEAGUE", "#f783ac", ("jleague", "jpn", "japon")),
    League("conmebol.libertadores", "Copa Libertadores", "LIBERTADORES", "#fab005",
           ("libertadores", "copalibertadores")),
    League("concacaf.champions", "Concacaf Champions Cup", "CONCACAF CC", "#63e6be",
           ("concacaf", "ccc")),
)

CATALOGUE = LEAGUES + EXTRA

BY_SLUG = {league.slug: league for league in CATALOGUE}
DEFAULT_SLUGS = tuple(league.slug for league in LEAGUES)

# Mots-cles de la ligne de commande.
_ALL = ("all", "tout", "tous", "toutes", "*")
_BIG_FIVE = ("big5", "top5", "les5", "5", "grands")


class SelectionError(ValueError):
    """La selection de competitions demandee n'est pas exploitable."""


class UnknownLeague(SelectionError):
    """Le nom passe a --leagues / --exclude ne correspond a rien."""


class NoLeagueLeft(SelectionError):
    """Tout a ete exclu : il ne reste rien a surveiller."""


def _tokens(value) -> list:
    if value is None:
        return []
    if isinstance(value, str):
        value = value.replace(";", ",").split(",")
    return [str(token).strip() for token in value if str(token).strip()]


def find(token: str):
    """La competition designee par `token`, ou None.

    Un code ESPN inconnu du catalogue est accepte tel quel : la competition est
    creee a la volee et prendra son vrai nom au premier releve.
    """
    lowered = token.strip().lower()
    for league in CATALOGUE:
        if league.matches_token(lowered):
            return league

    if SLUG_SHAPE.match(lowered):
        adhoc = League(lowered, lowered, lowered.upper(), NEUTRAL_ACCENT,
                       provisional=True)
        BY_SLUG.setdefault(lowered, adhoc)
        return BY_SLUG[lowered]
    return None


def _expand(value, default=()) -> list:
    tokens = _tokens(value)
    if not tokens:
        return list(default)

    found = []
    for token in tokens:
        lowered = token.lower()
        if lowered in _ALL:
            found.extend(l for l in CATALOGUE if l not in found)
            continue
        if lowered in _BIG_FIVE:
            found.extend(l for l in LEAGUES if l not in found)
            continue

        league = find(token)
        if league is None:
            raise UnknownLeague(
                "competition inconnue : {!r}. Voir 'butbutbut --list' pour les "
                "noms acceptes ; un code ESPN (por.1, uefa.champions) marche "
                "aussi.".format(token))
        if league not in found:
            found.append(league)
    return found


def resolve(tokens=None, exclude=None) -> list:
    """Les competitions a surveiller.

    `tokens` : None ou vide -> les cinq grands. `exclude` retire ensuite ce
    qu'on ne veut pas. L'ordre du catalogue est conserve pour les mots-cles,
    celui de la ligne de commande pour un choix explicite.
    """
    selection = _expand(tokens, default=LEAGUES)
    blocked = {league.slug for league in _expand(exclude, default=())}

    kept = [league for league in selection if league.slug not in blocked]
    if not kept:
        if blocked:
            raise NoLeagueLeft(
                "plus aucune competition a surveiller apres exclusion.")
        raise NoLeagueLeft("aucune competition selectionnee.")
    return kept


def describe(selection) -> str:
    if list(selection) == list(LEAGUES):
        return "les 5 grands championnats"
    if list(selection) == list(CATALOGUE):
        return "tout le catalogue ({} competitions)".format(len(CATALOGUE))
    names = [league.name for league in selection]
    if len(names) > 6:
        return "{} et {} autres".format(", ".join(names[:6]), len(names) - 6)
    return ", ".join(names)


def catalogue_lines() -> list:
    """Le catalogue, pretes a afficher : (groupe, nom, code, alias)."""
    rows = [("Les 5 grands (defaut)", LEAGUES), ("Aussi disponibles", EXTRA)]
    lines = []
    for title, group in rows:
        lines.append((title, None, None, None))
        for league in group:
            alias = ", ".join(league.aliases[:3])
            lines.append((None, league.name, league.slug, alias))
    return lines
