"""Les competitions surveillees, tous sports confondus.

Par defaut : les cinq grands championnats de football, et rien d'autre. Mais
la source (le tableau de bord d'ESPN) en expose bien d'autres, et tout ce
qu'elle sert a la meme forme : un catalogue suffit donc a les ouvrir - y
compris hors du football, le sport n'etant qu'un segment d'URL de plus (voir
sports.py, qui dit lesquels et pourquoi).

    butbutbut --leagues l1,ligue2,ucl      # choix explicite
    butbutbut --exclude liga,seriea        # les 5 moins deux
    butbutbut --leagues all                # tout le catalogue de football
    butbutbut --leagues nhl,top14          # hockey et rugby, a la demande
    butbutbut --leagues rugby              # tout le rugby du catalogue
    butbutbut --leagues all-sports         # vraiment tout
    butbutbut --leagues por.1              # n'importe quel code ESPN
    butbutbut --leagues hockey:nhl         # ... y compris dans un autre sport


Ce que `all` veut dire
----------------------

`all` reste **tout le catalogue de football**, exactement ce qu'il designait
avant l'ouverture aux autres sports. Deux raisons, et la premiere suffit :

  - personne n'a demande la NHL. Quelqu'un qui tapait `--leagues all` pour
    suivre les coupes nationales ne doit pas se retrouver, apres une mise a
    jour, avec des cartes de hockey a deux heures du matin. Une mise a jour ne
    change pas ce qu'on suit ;
  - `all`, c'est deja 36 endpoints. Y verser les autres sports en ferait 46
    sans que ce soit un choix.

Les autres sports se demandent, donc : par competition (`nhl`, `top14`), par
sport entier (`hockey`, `rugby`, et `foot` pour le football seul), ou d'un bloc
avec `all-sports` / `tous-sports`, qui lui prend vraiment tout.


L'echappatoire
--------------

Un code ESPN inconnu du catalogue reste accepte tel quel : `--leagues gre.1`
suit la Super League grecque, et la competition prend son vrai nom au premier
releve. Sans prefixe, c'est du football - c'est ce que ca a toujours voulu
dire. Pour viser un autre sport, on prefixe : `hockey:mens-college-hockey`,
`rugby:270565`. Le separateur `/` marche aussi, parce que c'est celui de l'URL.

Chaque competition porte son sport, son code ESPN (`slug`), son nom
d'affichage, son etiquette de carte et sa couleur. Les alias servent a la ligne
de commande.
"""

from __future__ import annotations

import re

from . import i18n, sports
from .i18n import tr

# Un code ESPN de football ressemble a "fra.1", "uefa.champions",
# "fra.coupe_de_france". C'est la forme historique, et elle ne bouge pas : sans
# prefixe de sport, un jeton doit toujours ressembler a ca pour etre accepte.
SLUG_SHAPE = re.compile(r"^[a-z]{2,8}(?:\.[a-z0-9_]+)+$")

# Avec un prefixe de sport, la forme est bien plus libre : le hockey emploie
# des mots ("nhl", "mens-college-hockey") et le rugby des numeros ("270559").
# On ne verifie donc plus qu'une chose : que ca puisse tenir dans une URL.
ANY_SLUG_SHAPE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,40}$")

# Ce qui separe le sport de la competition dans un jeton : "hockey:nhl". Le
# "/" est accepte aussi, c'est celui de l'URL de la source.
SPORT_SEPARATORS = ":/"

# Couleur des competitions ouvertes a la volee, hors catalogue.
NEUTRAL_ACCENT = "#7cc0ff"


class League:
    """Une competition : identite ESPN + habillage de la carte."""

    __slots__ = ("slug", "name", "_label", "accent", "aliases", "provisional",
                 "key", "sport")

    def __init__(self, slug, name, label, accent, aliases=(), provisional=False,
                 key="", sport=None):
        self.slug = slug              # code ESPN, ex. "fra.1"
        self.name = name              # "Ligue 1"
        self._label = label           # "LIGUE 1", pour l'en-tete de la carte
        # Cle de traduction, pour les competitions dont le nom se traduit. La
        # Bundesliga ou la Coupe de France s'ecrivent pareil partout ; la Ligue
        # des champions, non.
        self.key = key
        self.accent = accent          # couleur de la competition sur la carte
        self.aliases = tuple(aliases)
        # Le sport, football par defaut : les trente-six competitions ecrites
        # avant l'ouverture n'ont pas eu a bouger d'un caractere.
        self.sport = sport or sports.DEFAULT
        # Vrai pour une competition ouverte a la volee : on ne connait pas
        # encore son vrai nom, la source nous le dira au premier releve.
        self.provisional = provisional

    @property
    def label(self) -> str:
        """L'etiquette de la carte, dans la langue courante."""
        return i18n.text(self.key) if self.key else self._label

    @property
    def ref(self) -> str:
        """La cle unique d'une competition, tous sports confondus.

        C'est aussi, exactement, ce qu'il faut taper pour la designer :
        "fra.1" au football, ou le sport est sous-entendu, "hockey:nhl"
        ailleurs. Deux sports pourraient un jour employer le meme code ESPN ;
        c'est cette chaine, et non le seul `slug`, qui sert de cle interne.
        """
        if self.sport is sports.DEFAULT:
            return self.slug
        return self.sport.code + ":" + self.slug

    def matches_token(self, token: str) -> bool:
        token = token.strip().lower()
        return (token in (self.slug, self.ref, self.name.lower(),
                          self.label.lower())
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

# --- Hockey sur glace : a demander -------------------------------------------
# La NHL, et elle seule. Les autres competitions que la source expose sous
# `hockey` (championnats universitaires americains, tournois olympiques) sont
# soit sans public ici, soit vivantes deux semaines tous les quatre ans :
# elles restent accessibles par l'echappatoire, `hockey:mens-college-hockey`.

HOCKEY_LEAGUES = (
    League("nhl", "NHL", "NHL", "#7fd4ff", ("lnh", "hockey-nhl"),
           sport=sports.HOCKEY),
)

# --- Rugby a XV : a demander -------------------------------------------------
# Le rugby d'ESPN se code par un numero et non par un mot : "270559" est le
# Top 14. Ils ont tous ete verifies contre la source, un par un, avec le nom
# qu'elle renvoie.

RUGBY_LEAGUES = (
    League("180659", "Tournoi des Six Nations", "SIX NATIONS", "#4dd2c0",
           ("6nations", "sixnations", "tournoi"),
           key="league_six_nations", sport=sports.RUGBY),
    League("270559", "Top 14", "TOP 14", "#e8543f",
           ("top14", "top-14", "t14"), sport=sports.RUGBY),
    League("267979", "Premiership Rugby", "PREMIERSHIP RUGBY", "#8ac926",
           ("prem", "gallagher", "premiership-rugby"), sport=sports.RUGBY),
    League("270557", "United Rugby Championship", "URC", "#b07cff",
           ("urc", "unitedrugby", "celtique"), sport=sports.RUGBY),
    League("271937", "Champions Cup", "CHAMPIONS CUP", "#3fa7ff",
           ("champions-cup", "championscup", "hcup"), sport=sports.RUGBY),
    League("244293", "The Rugby Championship", "RUGBY CHAMPIONSHIP", "#ffb703",
           ("rugbychampionship", "trc", "quatrenations"), sport=sports.RUGBY),
    League("242041", "Super Rugby Pacific", "SUPER RUGBY", "#2ec4b6",
           ("superrugby", "super-rugby", "srp"), sport=sports.RUGBY),
    League("164205", "Coupe du monde de rugby", "COUPE DU MONDE DE RUGBY",
           "#ffd166", ("rwc", "mondial-rugby", "cdmrugby"),
           key="league_rwc", sport=sports.RUGBY),
    League("289234", "Match international", "MATCH INTERNATIONAL", "#9aa7b8",
           ("testmatch", "internationaux", "tests"),
           key="league_test_match", sport=sports.RUGBY),
)

OTHER_SPORTS = HOCKEY_LEAGUES + RUGBY_LEAGUES

# Tout ce qui existe. `CATALOGUE` reste le catalogue de football, parce que
# c'est lui que designe `--leagues all` : voir l'en-tete du module.
FULL_CATALOGUE = CATALOGUE + OTHER_SPORTS

BY_SLUG = {league.slug: league for league in FULL_CATALOGUE}
DEFAULT_SLUGS = tuple(league.slug for league in LEAGUES)

# Les competitions d'un sport donne, dans l'ordre du catalogue.
BY_SPORT = {sports.SOCCER: CATALOGUE,
            sports.HOCKEY: HOCKEY_LEAGUES,
            sports.RUGBY: RUGBY_LEAGUES}

# Mots-cles de la ligne de commande. `_ALL` ne sort pas du football : voir
# l'en-tete du module pour la raison.
_ALL = ("all", "tout", "tous", "toutes", "*")
_EVERYTHING = ("all-sports", "allsports", "tous-sports", "toussports",
               "tout-sport", "everything", "**")
_BIG_FIVE = ("big5", "top5", "les5", "5", "grands")


class SelectionError(ValueError):
    """La selection de competitions demandee n'est pas exploitable."""


class UnknownLeague(SelectionError):
    """Le nom passe a --leagues / --exclude ne correspond a rien."""


class NoLeagueLeft(SelectionError):
    """Tout a ete exclu : il ne reste rien a surveiller."""


class DeclinedSport(SelectionError):
    """Le sport demande existe chez ESPN, mais butbutbut ne le suit pas."""


def _tokens(value) -> list:
    if value is None:
        return []
    if isinstance(value, str):
        value = value.replace(";", ",").split(",")
    return [str(token).strip() for token in value if str(token).strip()]


# Les competitions ouvertes a la volee, retenues d'un appel a l'autre : deux
# `--leagues gre.1` doivent designer le meme objet, sinon la competition
# reapprendrait son nom a chaque fois.
_ADHOC = {}


def _split_sport(token: str) -> tuple:
    """("hockey:nhl") -> (sports.HOCKEY, "nhl"). Sans prefixe : (None, jeton).

    Leve DeclinedSport pour un sport ecarte expres (le basket) et
    UnknownLeague pour un sport qui n'existe pas.
    """
    for separator in SPORT_SEPARATORS:
        head, found, tail = token.partition(separator)
        if not found:
            continue
        head, tail = head.strip(), tail.strip()
        sport = sports.find(head)
        if sport is not None:
            return sport, tail
        reason = sports.declined(head)
        if reason:
            raise DeclinedSport(
                "sport ecarte : {} - {}".format(head, reason))
        raise UnknownLeague(
            "sport inconnu : {!r} (connus : {}).".format(head, sports.describe()))
    return None, token


def _adhoc(sport, slug):
    """La competition hors catalogue, creee une fois puis retenue."""
    league = League(slug, slug, slug.upper(), NEUTRAL_ACCENT,
                    provisional=True, sport=sport)
    return _ADHOC.setdefault(league.ref, league)


def find(token: str):
    """La competition designee par `token`, ou None.

    Un code ESPN inconnu du catalogue est accepte tel quel : la competition est
    creee a la volee et prendra son vrai nom au premier releve. Sans prefixe de
    sport, c'est du football - c'est ce que `--leagues gre.1` a toujours voulu
    dire, et ca ne change pas.

    Rend None quand le jeton ne designe rien. Un prefixe de sport qui, lui, ne
    designe rien leve en revanche : "curling:1" est une faute qu'il vaut mieux
    nommer que traduire en "competition inconnue".
    """
    lowered = token.strip().lower()
    for league in FULL_CATALOGUE:
        if league.matches_token(lowered):
            return league

    sport, slug = _split_sport(lowered)
    if sport is not None:
        # Prefixe explicite : le catalogue a deja ete interroge plus haut sur
        # la forme complete, reste l'ouverture a la volee.
        return _adhoc(sport, slug) if ANY_SLUG_SHAPE.match(slug) else None

    if SLUG_SHAPE.match(lowered):
        return _adhoc(sports.DEFAULT, lowered)
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
        if lowered in _EVERYTHING:
            found.extend(l for l in FULL_CATALOGUE if l not in found)
            continue
        if lowered in _BIG_FIVE:
            found.extend(l for l in LEAGUES if l not in found)
            continue

        # Un sport entier : "hockey", "rugby", "foot". Teste avant le
        # catalogue, aucune competition ne portant ces noms.
        sport = sports.find(lowered)
        if sport is not None:
            found.extend(l for l in BY_SPORT.get(sport, ()) if l not in found)
            continue
        reason = sports.declined(lowered)
        if reason:
            raise DeclinedSport("sport ecarte : {} - {}".format(token, reason))

        league = find(token)
        if league is None:
            raise UnknownLeague(
                "competition inconnue : {!r}. Voir 'butbutbut --list' pour les "
                "noms acceptes ; un code ESPN (por.1, uefa.champions) marche "
                "aussi, et 'hockey:nhl' pour un autre sport.".format(token))
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
    # L'exclusion porte sur `ref` et non sur `slug` : deux sports pourraient un
    # jour employer le meme code ESPN, et exclure l'un ne doit pas retirer
    # l'autre.
    blocked = {league.ref for league in _expand(exclude, default=())}

    kept = [league for league in selection if league.ref not in blocked]
    if not kept:
        if blocked:
            raise NoLeagueLeft(
                tr("plus aucune competition a surveiller apres exclusion."))
        raise NoLeagueLeft(tr("aucune competition selectionnee."))
    return kept


def describe(selection) -> str:
    selection = list(selection)
    if selection == list(LEAGUES):
        return tr("les 5 grands championnats")
    if selection == list(CATALOGUE):
        return tr("tout le catalogue ({} competitions)", len(CATALOGUE))
    if selection == list(FULL_CATALOGUE):
        return tr("tous les sports ({} competitions)",
                      len(FULL_CATALOGUE))
    for sport, group in BY_SPORT.items():
        if sport is not sports.DEFAULT and selection == list(group):
            return tr("tout le {} ({} competitions)",
                          sport.name, len(group))
    names = [league.name for league in selection]
    if len(names) > 6:
        return tr("{} et {} autres", ", ".join(names[:6]), len(names) - 6)
    return ", ".join(names)


def sports_of(selection) -> list:
    """Les sports representes dans une selection, dans l'ordre de sports.py."""
    chosen = {league.sport for league in selection}
    return [sport for sport in sports.SPORTS if sport in chosen]


def catalogue_lines(all_sports=False) -> list:
    """Le catalogue, pret a afficher : (groupe, nom, code, alias).

    Sans argument, le catalogue de football : c'est celui que `--leagues all`
    designe, et celui que le reste du programme entend par "le catalogue".
    `all_sports=True` y ajoute les autres sports, dans leurs propres groupes -
    c'est ce que `butbutbut --list` affiche.
    """
    rows = [(tr("Les 5 grands (defaut)"), LEAGUES), (tr("Aussi disponibles"), EXTRA)]
    if all_sports:
        rows.append((tr("Hockey sur glace (a demander)"), HOCKEY_LEAGUES))
        rows.append((tr("Rugby a XV (a demander)"), RUGBY_LEAGUES))
    lines = []
    for title, group in rows:
        lines.append((title, None, None, None))
        for league in group:
            alias = ", ".join(league.aliases[:3])
            lines.append((None, league.name, league.slug, alias))
    return lines
