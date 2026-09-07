"""Filtrer par equipe : ne se faire alerter que pour les clubs qu'on suit.

    butbutbut --teams om,psg
    butbutbut --teams "real madrid,barcelona" --leagues liga,ucl
    butbutbut --exclude-teams psg
    butbutbut --teams om --spoiler-free om
    butbutbut --teams ligue2:sochaux --leagues big5,ligue2

Un match est retenu des que **l'une des deux equipes** correspond : si tu suis
l'OM, tu veux aussi savoir quand l'OM encaisse.

Un mot peut se borner a une competition, et c'est toute la difference entre
"je ne veux plus que ce club" et "j'ajoute ce club" :

  - `--teams sochaux` ne laisse plus rien passer nulle part, sauf Sochaux. Les
    cinq grands championnats deviennent muets, ce qui n'est presque jamais ce
    qu'on voulait en ajoutant une deuxieme division ;
  - `--teams ligue2:sochaux` ne dit rien des autres competitions : elles
    continuent comme avant, et la Ligue 2 se reduit a Sochaux.

La regle tient en une phrase : **un mot sans prefixe vaut partout ; un mot
prefixe ne vaut, et surtout ne restreint, que sa competition**. Le prefixe
s'ecrit comme a `--leagues` - `ligue2:`, `l1:`, `hockey:nhl:` - et l'exclusion
se borne pareil (`--exclude-teams ligue2:metz`).

Trois listes cohabitent, et l'ordre de decision est toujours le meme :

  1. `--exclude-teams` : le match n'existe pas. Ni carte, ni son, ni journal.
  2. `--teams` : si la liste est remplie et que le match n'y est pas, meme
     chose, il n'existe pas.
  3. `--spoiler-free` : le match existe et continue de remplir le journal,
     mais rien ne va a l'ecran ni au haut-parleur.

Les deux premieres taisent un match ; la troisieme ne tait que l'alerte. Suivre
l'OM *et* le mettre en sans-spoiler est donc parfaitement coherent : c'est
exactement ce qu'on veut quand on regarde le match en differe et qu'on lira
`--today` une fois le direct rattrape.

La reconnaissance des noms doit encaisser ce que les gens tapent vraiment :

  - les accents          : "malaga" trouve "Malaga", "atletico" trouve
                           "Atletico Madrid" ;
  - les abreviations      : ESPN en fournit une par club (PSG, RMA, MAN...) ;
  - les surnoms francais  : "om", "ol", "asse", "losc"... qu'ESPN ne connait
                           pas, d'ou la petite table ci-dessous ;
  - les noms partiels     : "marseille" trouve "Marseille", "manchester"
                           trouve les deux Manchester (c'est voulu, et
                           `--list-teams` montre ce qu'un mot attrape).
"""

from __future__ import annotations

import re
import unicodedata

from . import leagues

# Surnoms courants qu'ESPN n'expose pas. La valeur est ce qu'on cherche
# ensuite dans les noms officiels, donc "om" revient a taper "marseille".
ALIASES = {
    # France
    "om": "marseille",
    "ol": "lyon",
    "asse": "saint etienne",
    "losc": "lille",
    "ogcn": "nice",
    "asm": "monaco",
    "srfc": "rennes",
    "mhsc": "montpellier",
    "fcn": "nantes",
    "tfc": "toulouse",
    "asnl": "nancy",
    # Angleterre
    "manu": "manchester united",
    "mufc": "manchester united",
    "mcfc": "manchester city",
    "lfc": "liverpool",
    "cfc": "chelsea",
    # Espagne, Italie, Allemagne
    "barca": "barcelona",
    "atleti": "atletico",
    "juve": "juventus",
    "bvb": "dortmund",
    "gladbach": "monchengladbach",
}

# En dessous, un mot n'est cherche qu'a l'identique : "bar" ne doit pas
# attraper "Barcelona" par hasard, alors que l'abreviation BAR, si.
PARTIAL_MIN = 4


def normalize(text) -> str:
    """Minuscules, sans accents, sans ponctuation ni espaces."""
    decomposed = unicodedata.normalize("NFKD", str(text or ""))
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return "".join(c for c in stripped.lower() if c.isalnum())


def expand(token: str) -> str:
    """Remplace un surnom par le nom a chercher."""
    return ALIASES.get(normalize(token), token)


def words(name) -> list:
    """Les mots d'un nom, normalises un par un."""
    parts = re.split(r"[\s./'`-]+", str(name or ""))
    return [normalize(part) for part in parts if normalize(part)]


def _hit(token: str, names) -> bool:
    """Vrai si `token` (deja normalise) designe l'une de ces ecritures.

    Le mot doit coller au nom entier ou au DEBUT d'un de ses mots. Sans cette
    contrainte de frontiere, "real" attrapait aussi "Villarreal", ou "real"
    n'est qu'un morceau de mot.
    """
    for name in names:
        if not name:
            continue
        flat = normalize(name)
        if token == flat:
            return True
        if len(token) >= PARTIAL_MIN and flat.startswith(token):
            return True
        for word in words(name):
            if token == word:
                return True
            if len(token) >= PARTIAL_MIN and word.startswith(token):
                return True
    return False


def designates(token, names) -> bool:
    """Vrai si ce mot designe l'une de ces equipes, surnoms compris.

    L'entree publique de _hit() : le choix du son par nom de fichier pose la
    meme question que le filtre, hors de tout Filter - `om.mp3` designe-t-il
    l'equipe qui vient de marquer ?
    """
    return _hit(normalize(expand(token)), names)


# Ce qui borne un mot d'equipe a une competition : "ligue2:sochaux". Ce sont
# exactement les separateurs de --leagues, ou "hockey:nhl" s'ecrit deja comme
# ca : une seule ponctuation a retenir pour les deux options.
SCOPE_SEPARATORS = ":/"


def split_scope(raw) -> tuple:
    """(mot de competition, mot d'equipe). La competition est vide sans prefixe.

    La coupe se fait au DERNIER separateur : "hockey:nhl:rangers" borne les
    Rangers a la NHL, la ou "hockey:rangers" les bornerait a tout le hockey.
    Couper au premier rendrait ces deux ecritures indistinguables, et il n'y a
    pas de nom de club a couper par accident - aucun n'a de deux-points.

    Un cote vide ("ligue2:", ":om") n'est pas un bornage mais une faute de
    frappe : le jeton repart entier comme nom d'equipe, ou il sera signale au
    demarrage comme n'importe quel mot qui ne designe aucun club.
    """
    raw = str(raw or "").strip()
    cut = max(raw.rfind(separator) for separator in SCOPE_SEPARATORS)
    if cut < 0:
        return "", raw
    scope, team = raw[:cut].strip(), raw[cut + 1:].strip()
    if not scope or not team:
        return "", raw
    return scope, team


def _scope_refs(scope: str) -> frozenset:
    """Les competitions que ce prefixe designe, lues comme --leagues les lit.

    D'ou un ensemble et non une competition : le prefixe accepte tout ce que
    `--leagues` accepte, donc aussi bien `ligue2` qu'un groupe entier
    (`feminines:lyon`). Un prefixe qui ne designe rien rend l'ensemble vide -
    le mot ne vaudra nulle part, et check_teams() le dira au demarrage plutot
    que de laisser le daemon muet.
    """
    try:
        return frozenset(league.ref for league in leagues.resolve(scope))
    except Exception:
        return frozenset()


def _ref_of(league) -> str:
    """La cle d'une competition, qu'on nous donne l'objet ou son etiquette.

    Le watcher tient un vrai objet League ; une ligne de journal relue n'a
    garde que l'etiquette de la carte ("LIGUE 2"), qui suffit a la retrouver.
    Rend une chaine vide quand on ne sait pas de quelle competition il s'agit.
    """
    ref = getattr(league, "ref", "")
    if ref:
        return ref
    found = leagues.designates(league) if league else None
    return found.ref if found is not None else ""


class Word:
    """Un mot d'equipe, parfois borne a une competition.

    `om` suit l'OM partout ; `ligue2:sochaux` suit Sochaux en Ligue 2 et **ne
    dit rien** des autres competitions. C'est cette moitie-la qui compte : un
    mot borne ne restreint que chez lui, donc ajouter un club n'a pas a faire
    taire ce qu'on suivait deja.
    """

    __slots__ = ("raw", "token", "needle", "scope")

    def __init__(self, raw):
        self.raw = str(raw or "").strip()
        scope, token = split_scope(self.raw)
        self.token = token                    # le club seul, sans le prefixe
        self.needle = normalize(expand(token))
        # None : aucun bornage, le mot vaut partout. Un ensemble vide : un
        # bornage dont on n'a pas su nommer la competition.
        self.scope = _scope_refs(scope) if scope else None

    def covers(self, league) -> bool:
        """Ce mot a-t-il son mot a dire sur cette competition ?"""
        if self.scope is None:
            return True
        ref = _ref_of(league)
        return bool(ref) and ref in self.scope

    def hits(self, names) -> bool:
        return _hit(self.needle, names)

    def __eq__(self, other):
        if not isinstance(other, Word):
            return NotImplemented
        return (self.raw, self.needle, self.scope) == (other.raw, other.needle,
                                                       other.scope)

    def __hash__(self):
        return hash((self.raw, self.needle, self.scope))

    def __repr__(self):
        return "<Word {}>".format(self.raw)


class Filter:
    """Les equipes suivies, et celles dont on ne veut rien savoir."""

    def __init__(self, wanted=None, excluded=None):
        self.wanted_tokens = _tokens(wanted)
        self.excluded_tokens = _tokens(excluded)
        self.wanted = [Word(t) for t in self.wanted_tokens]
        self.excluded = [Word(t) for t in self.excluded_tokens]
        # Vide de partout : pas de filtre du tout, tout passe.
        self.active = bool(self.wanted or self.excluded)

    @property
    def words(self) -> list:
        """Tous les mots, suivis et exclus : le vocabulaire du filtre."""
        return self.wanted + self.excluded

    def team_words(self) -> list:
        """Les clubs seuls, sans leur competition.

        Ce que le nom d'un fichier son peut porter : `sochaux.mp3` parle de
        Sochaux, pas de `ligue2:sochaux`, et un fichier ne saurait de toute
        facon pas nommer une competition ET un club.
        """
        seen = []
        for word in self.words:
            if word.token not in seen:
                seen.append(word.token)
        return seen

    def here(self, words, league) -> list:
        """Les mots qui ont leur mot a dire sur cette competition.

        Une competition qu'on n'a pas su nommer ne garde que les mots sans
        prefixe : c'est la seule reponse qui ne fasse pas disparaitre des
        matchs par accident.
        """
        return [word for word in words if word.covers(league)]

    def team_matches(self, names, league=None) -> bool:
        """Ce jeu de noms est-il suivi ? Dans cette competition, si elle est dite.

        Sans competition, la question posee n'est plus celle du filtre mais
        celle du vocabulaire - ce mot designe-t-il cette equipe ? - et tous les
        mots y repondent, prefixes compris. C'est ce qu'il faut au son (`om`
        parle de l'OM ou qu'il joue) et a un etat relu, qui ne sait plus de
        quelle competition il parle.
        """
        words = self.wanted if league is None else self.here(self.wanted, league)
        return any(word.hits(names) for word in words)

    def team_excluded(self, names, league=None) -> bool:
        words = (self.excluded if league is None
                 else self.here(self.excluded, league))
        return any(word.hits(names) for word in words)

    def bad_scopes(self) -> list:
        """Les mots dont le prefixe ne designe aucune competition."""
        return [word.raw for word in self.words
                if word.scope is not None and not word.scope]

    def outside(self, selection) -> list:
        """Les mots bornes a une competition qui n'est pas suivie.

        `--teams ligue2:sochaux` sans Ligue 2 dans `--leagues` ne ferait rien
        du tout, et ne le dirait pas : c'est le piege silencieux que la
        verification des noms existe pour attraper.
        """
        followed = {league.ref for league in selection}
        return [word.raw for word in self.words
                if word.scope and not (word.scope & followed)]

    def matches(self, match) -> bool:
        """Ce match interesse-t-il ?

        Il suffit qu'une des deux equipes soit suivie ; il suffit qu'une des
        deux soit exclue pour que le match saute. Un mot borne a une autre
        competition ne compte ni dans un sens ni dans l'autre : il ne parle pas
        de ce match-la.
        """
        if not self.active:
            return True

        home, away = sides_of(match)
        league = getattr(match, "league", None)
        excluded = self.here(self.excluded, league)
        wanted = self.here(self.wanted, league)

        if excluded and (any(word.hits(home) for word in excluded)
                         or any(word.hits(away) for word in excluded)):
            return False
        # Aucun mot suivi pour cette competition-ci : elle passe entiere. C'est
        # ce qui distingue `ligue2:sochaux` de `sochaux`, et rien d'autre.
        if not wanted:
            return True
        return (any(word.hits(home) for word in wanted)
                or any(word.hits(away) for word in wanted))

    def resolve(self, catalogue, by_league=None) -> tuple:
        """Confronte les mots demandes a un catalogue d'equipes.

        `catalogue` : liste de tuples de noms (un tuple par equipe), telle que
        la rend espn.team_names. Renvoie ({mot: [noms trouves]}, [mots orphelins]).

        `by_league` : les memes listes rangees par competition ({ref: noms}).
        Quand elle est fournie, un mot borne n'est confronte qu'au catalogue de
        SA competition - c'est la seule facon d'attraper `ligue2:om`, qui
        passerait sans encombre contre les equipes de toutes les competitions
        mises bout a bout.
        """
        found = {}
        orphans = []
        for word in self.words:
            here = catalogue
            if word.scope is not None and by_league is not None:
                here = [names for ref in sorted(word.scope)
                        for names in by_league.get(ref, ())]
            hits = [names[0] for names in here if word.hits(names)]
            if hits:
                found[word.raw] = sorted(set(hits))
            else:
                orphans.append(word.raw)
        return found, orphans

    def describe(self) -> str:
        parts = []
        if self.wanted_tokens:
            parts.append("equipes suivies : " + ", ".join(self.wanted_tokens))
        if self.excluded_tokens:
            parts.append("equipes exclues : " + ", ".join(self.excluded_tokens))
        return " | ".join(parts) if parts else "toutes les equipes"

    def __repr__(self):
        return "<Filter {}>".format(self.describe())


class SpoilerFilter(Filter):
    """Les matchs regardes en differe : le journal oui, l'ecran et le son non.

    C'est le seul reglage de butbutbut qui ne coupe pas la surveillance mais
    l'alerte. Un `Filter` ordinaire repond "ce match m'interesse-t-il ?" et
    fait disparaitre le reste ; celui-ci repond "dois-je me taire ?" et laisse
    tout le reste passer. D'ou une classe a part plutot qu'un troisieme jeu de
    mots dans `Filter` : les deux questions n'ont pas la meme reponse par
    defaut (rien de suivi = tout passe ; rien en sans-spoiler = rien a taire),
    et les melanger rendait `matches()` illisible.

    Il n'y a qu'une liste de mots, jamais d'exclusion : "ne me spoile pas, sauf
    ce club-la" n'a pas de sens - on ne demande pas le silence a moitie.
    """

    def __init__(self, teams=None):
        Filter.__init__(self, wanted=teams)

    def covers(self, match) -> bool:
        """Ce match est-il regarde en differe ?"""
        if not self.active:
            return False
        home, away = sides_of(match)
        league = getattr(match, "league", None)
        return (self.team_matches(home, league)
                or self.team_matches(away, league))

    def covers_names(self, home, away) -> bool:
        """La meme question, posee sur deux jeux de noms deja extraits.

        Le fichier d'etat relu par `--status` ne garde que le nom affiche de
        chaque equipe, pas l'objet match : il lui faut cette porte d'entree.
        """
        if not self.active:
            return False
        return self.team_matches(home) or self.team_matches(away)

    def describe(self) -> str:
        if not self.wanted_tokens:
            return "aucune"
        return ", ".join(self.wanted_tokens)


def sides_of(match) -> tuple:
    """(ecritures du domicile, ecritures de l'exterieur) d'un match.

    Toutes les ecritures connues, pas seulement celle qui est affichee : le
    filtre doit reconnaitre "PSG" comme "Paris Saint-Germain".
    """
    return (getattr(match, "home_names", (match.home,)),
            getattr(match, "away_names", (match.away,)))


def _tokens(value) -> list:
    if value is None:
        return []
    if isinstance(value, str):
        value = value.replace(";", ",").split(",")
    return [str(token).strip() for token in value if str(token).strip()]
