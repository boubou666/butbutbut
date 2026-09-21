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
    portee par des drapeaux (`scoringPlay`, `redCard`, `ownGoal`...). Le
    drapeau `shootout` en fait partie, et c'est le seul qui contredise le
    score : un tir au but est marque `scoringPlay` alors que le score du match
    ne bouge pas (voir _soccer_details) ;
  - le **rugby** publie le meme tableau, mais **sans aucun drapeau** : c'est
    `type.id` qui dit ce qui s'est passe (1 essai, 2 transformation, 3
    penalite, 4 drop, 6 carton rouge). Lu avec le lecteur du football, un match
    de rugby n'aurait aucune action du tout ;
  - le **hockey** ne publie **rien** : `details` est absent, sur un match a
    venir comme sur un match termine. On a le score, l'horloge et la periode.

Chaque camp porte aussi, dans la meme reponse, sa **forme** (`form`), son
**bilan** (`records`) et les **statistiques du match** (`statistics`). C'est ce
que les cartes de coup d'envoi et de fin de match affichent, et ca ne coute pas
un octet de plus : les trois cles sont deja dans le tableau de bord qu'on
telecharge a chaque tour, on les jetait. Le hockey se tait sur les deux
premieres ; sur la troisieme il parle, mais d'autre chose - voir
`sports.STATS_SOCCER`, qui dit quel sport publie quoi et ce qu'on en retient.

Le match lui-meme porte parfois une note (`notes`), et elle vaut surtout par ce
qu'elle n'est pas : ni le tour, ni la journee, ni rien qu'un championnat
publie. Voir match_note() pour ce qu'on en garde, et pourquoi si peu.

Le meme hote publie un second endpoint, le classement, sous une adresse qui
n'a pas tout a fait la meme forme (voir STANDINGS_URL, plus bas). Il est lu
avec le meme client et les memes en-tetes : c'est tout l'interet d'avoir un
seul endroit ou le reseau est touche.

Rien d'autre que la stdlib : urllib + json.
"""

from __future__ import annotations

import gzip
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
SEASON_URL = ("https://sports.core.api.espn.com/v2/sports/{sport}/leagues/"
              "{slug}/seasons/{year}")
# Le resume d'un match, et la seule adresse de ce fichier qu'on n'appelle pas a
# chaque tour : elle rend 450 ko. Voir summary() pour ce qui l'autorise.
SUMMARY_URL = "https://site.api.espn.com/apis/site/v2/sports/{sport}/{slug}/summary"

# Les lettres de la forme, telles que la source les ecrit : victoire, nul,
# defaite. Tout le reste est refuse (voir team_form).
FORM_LETTERS = "WDL"

# Un bilan, et rien d'autre : trois nombres separes par des tirets. C'est ce
# filtre qui distingue le "1-0-2" du football du "LWWWW" que le rugby publie
# au meme endroit (voir team_record).
RECORD = re.compile(r"^\d+-\d+-\d+$")

# Les seules notes de match qu'on sache redire dans les cinq langues, et donc
# les seules qui aient le droit de monter sur une carte.
#
# Le releve (9 601 matchs, voir docs/api-espn.md section 3) a repondu deux
# choses a la fois. `notes` n'est PAS le tour ni la journee : aucun
# championnat n'en publie une seule, et pas un match de rugby non plus. Et ce
# qu'elle contient est un texte libre, anglais, qui est le plus souvent un
# RESULTAT - "2nd Leg - Real Madrid advance 3-1 on aggregate", "Leeds United
# advance 4-2 on penalties". Une carte d'avant-match qui reprendrait ce texte
# tel quel raconterait la fin, et le ferait en anglais sur une carte
# espagnole.
#
# D'ou une table blanche et courte : ce qu'on reconnait, on le redit ; tout le
# reste se jette. Deux entrees seulement, parce que deux seulement ont ete
# observees - le depot ne suppose pas ce qu'il n'a pas vu.
NOTE_KEYS = {
    "1st leg": "note_first_leg",
    "2nd leg": "note_second_leg",
}

USER_AGENT = "butbutbut/{} (+https://github.com/boubou666/butbutbut)".format(__version__)
DEFAULT_TIMEOUT = 8.0

# Le delai du resume, et il est court expres. Un tableau de bord peut se
# permettre huit secondes : personne n'attend devant. Le resume, lui, est
# demande entre un but detecte et la carte qui l'annonce - c'est le seul
# endroit du programme ou une seconde de reseau se voit a l'ecran. 1,5 s est
# donc un plafond, pas une esperance : gzip ramene les 450 ko a une petite
# centaine de ko, et la reponse arrive d'ordinaire en trois fois moins. Passe
# ce delai on laisse tomber le nom, jamais la carte.
SUMMARY_TIMEOUT = 1.5

# Le tableau de bord accepte un parametre `dates` : un jour (AAAAMMJJ), un mois
# (AAAAMM) ou une annee (AAAA). Il acceptait aussi les intervalles jusqu'au
# 15 septembre 2026, puis s'est mis a leur repondre 400. `fetch()` garde cette
# interface pratique pour le reste du programme, mais la traduit desormais en
# un ou plusieurs mois et filtre localement les jours demandes.
DAY_FORMAT = "%Y%m%d"
DATE_RANGE = re.compile(r"^(\d{8})-(\d{8})$")

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
                 "penalty", "shootout", "red_card", "kind_key", "points",
                 "assists", "sequence")

    def __init__(self, key, team_id, minute, kind, scorer, own_goal, penalty,
                 shootout, red_card=False, kind_key="", points=None,
                 assists=(), sequence=0):
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
        # Les passeurs, quand la source les nomme - elle ne le fait qu'au
        # hockey, et seulement dans le resume du match. Vide partout ailleurs :
        # le football publie bien une passe decisive quelque part, mais pas
        # dans le tableau d'actions qu'on lit ici, et aller la chercher
        # couterait le meme demi-mega que le buteur du hockey pour un sport qui
        # a deja son nom.
        self.assists = tuple(assists)
        self.sequence = int(sequence or 0)

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
                 "red_cards", "shootout", "home_shootout", "away_shootout",
                 "winner", "home_logo", "away_logo", "home_color",
                 "away_color", "home_alt", "away_alt", "home_form",
                 "away_form", "home_record", "away_record", "note",
                 "home_stats", "away_stats", "venue_country", "venue",
                 "season", "home_short", "away_short", "home_slug",
                 "away_slug", "edition_external_id", "edition_name",
                 "phase_kind", "phase_external_id", "phase_name",
                 "phase_order", "group_external_id", "group_name",
                 "group_order", "round_external_id", "round_name",
                 "round_order", "tie_external_id", "leg_number",
                 "bracket_slot", "next_match_external_id")

    def __init__(self, id, league, home, away, home_id, away_id, home_score,
                 away_score, state, detail, clock, start, plays,
                 status_name="", home_names=(), away_names=(), red_cards=(),
                 shootout=(), home_shootout=0, away_shootout=0, winner="",
                 home_logo="", away_logo="", home_color="", away_color="",
                 home_alt="", away_alt="", home_form="", away_form="",
                 home_record="", away_record="", note="",
                 home_stats=None, away_stats=None, venue_country="", venue="",
                 season="", home_short="", away_short="", home_slug="",
                  away_slug="", edition_external_id="", edition_name="",
                  phase_kind="", phase_external_id="", phase_name="",
                  phase_order=None, group_external_id="", group_name="",
                  group_order=None, round_external_id="", round_name="",
                  round_order=None, tie_external_id="", leg_number=None,
                  bracket_slot=None, next_match_external_id=""):
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
        # Les tirs au but, tenus a part pour la meme raison, en plus fort : la
        # source les publie dans le meme tableau que les buts, avec le meme
        # `scoringPlay`, alors qu'ils ne changent PAS le score du match. Les
        # laisser dans `plays` ferait dire a une carte de fin de match "0 - 0"
        # suivi de onze buteurs. Voir _soccer_details().
        self.shootout = list(shootout)
        # Le resultat de la seance. Il vient de `shootoutScore` quand la source
        # le donne, du decompte des tirs reussis sinon : les deux se rejoignent
        # partout ou l'on a pu les comparer, et `shootoutScore` manque une fois
        # sur dix.
        self.home_shootout = int(home_shootout or 0)
        self.away_shootout = int(away_shootout or 0)
        # "home", "away" ou "" : le cote que la source declare vainqueur. Seul
        # ce drapeau sait dire qui se qualifie sur un 1-1.
        self.winner = winner
        # L'habillage du club : l'URL de son ecusson et ses deux couleurs, en
        # #rrggbb. Vides quand la source ne les donne pas.
        self.home_logo = home_logo
        self.away_logo = away_logo
        self.home_color = home_color
        self.away_color = away_color
        self.home_alt = home_alt
        self.away_alt = away_alt
        # La forme ("LLWWW") et le bilan ("1-0-2") de chaque club, vides quand
        # la source ne les publie pas - au hockey, et sur tout match qu'elle ne
        # rattache a aucune saison. Ce sont les seules valeurs du Match qui ne
        # parlent PAS de ce match-ci : elles disent ce que l'equipe a fait
        # avant, et c'est bien ce qu'on veut lire au coup d'envoi.
        self.home_form = home_form
        self.away_form = away_form
        self.home_record = home_record
        self.away_record = away_record
        # L'enjeu du match, quand la source en publie un qu'on sache redire :
        # une CLE i18n ("note_first_leg"), jamais le texte anglais de la
        # source. Vide partout ailleurs, c'est-a-dire presque partout - voir
        # match_note().
        self.note = note
        # Les statistiques du match lui-meme (possession, tirs cadres), vides
        # tant que rien n'a ete joue et partout ailleurs qu'au football. Elles
        # sont copiees plutot que rangees telles quelles : un dictionnaire par
        # defaut est partage par tous les matchs qui n'en ont pas, et un
        # dictionnaire partage finit toujours par etre modifie par quelqu'un.
        self.home_stats = dict(home_stats or {})
        self.away_stats = dict(away_stats or {})
        # Le pays du STADE, pas celui d'un club. C'est cette nuance qui rend
        # une finale internationale non ambigue et qui habille la carte sans
        # choisir arbitrairement un des deux camps.
        self.venue_country = str(venue_country or "").strip()
        self.venue = str(venue or "").strip()
        self.season = str(season or "").strip()
        self.home_short = str(home_short or home).strip()
        self.away_short = str(away_short or away).strip()
        self.home_slug = str(home_slug or "").strip()
        self.away_slug = str(away_slug or "").strip()
        # Structure officielle de la competition. Ces champs restent vides
        # quand la source ne les publie pas : aucun libelle ni identifiant de
        # tour n'est reconstruit depuis une date ou une note en prose.
        self.edition_external_id = str(edition_external_id or "").strip()
        self.edition_name = str(edition_name or "").strip()
        self.phase_kind = str(phase_kind or "").strip()
        self.phase_external_id = str(phase_external_id or "").strip()
        self.phase_name = str(phase_name or "").strip()
        self.phase_order = phase_order
        self.group_external_id = str(group_external_id or "").strip()
        self.group_name = str(group_name or "").strip()
        self.group_order = group_order
        self.round_external_id = str(round_external_id or "").strip()
        self.round_name = str(round_name or "").strip()
        self.round_order = round_order
        self.tie_external_id = str(tie_external_id or "").strip()
        self.leg_number = leg_number
        self.bracket_slot = bracket_slot
        self.next_match_external_id = str(next_match_external_id or "").strip()

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

    @property
    def on_penalties(self) -> bool:
        """Vrai quand la source dit que ce match s'est decide aux tirs au but.

        Un match en cours ne compte pas, meme pendant la seance : tant qu'il
        n'est pas fini il n'y a pas de verdict a annoncer, et la carte qui
        porte ce verdict est celle de la fin du match.

        Les marqueurs viennent du sport (voir sports.py) parce que la source ne
        les ecrit pas au meme endroit d'un sport a l'autre : le football pose
        un etat de fin a lui (STATUS_FINAL_PEN), le hockey garde STATUS_FINAL
        et ne le dit que dans le detail ("Final/SO").
        """
        if not self.finished:
            return False
        marks = self.sport.shootout
        if not marks:
            return False
        haystack = "{} {}".format(self.status_name, self.detail).upper()
        return any(mark in haystack for mark in marks)

    @property
    def winner_name(self) -> str:
        """Le nom de l'equipe declaree vainqueur, ou une chaine vide."""
        if self.winner == "home":
            return self.home
        if self.winner == "away":
            return self.away
        return ""

    def shootout_line(self) -> str:
        """Le score de la seance, "3 - 5", ou "" quand on ne le sait pas.

        Le hockey tombe toujours dans le "" : sa fusillade donne un but au
        vainqueur et se lit deja dans le score du match, la source ne publie ni
        tir ni total pour elle.
        """
        if not (self.home_shootout or self.away_shootout):
            return ""
        return "{} - {}".format(self.home_shootout, self.away_shootout)

    def seconds_until_kickoff(self, now=None) -> float | None:
        if self.start is None:
            return None
        now = now or datetime.now(timezone.utc)
        return (self.start - now).total_seconds()

    def plays_for(self, team_id) -> list:
        return [play for play in self.plays if play.team_id == team_id]

    def red_card_tally(self) -> tuple:
        """(domicile, exterieur) : les expulsions publiees jusqu'ici.

        Compte les actions deja lues, pas un etat que la source donnerait : il
        n'y a nulle part de "cette equipe joue a dix". Une expulsion dont on ne
        sait pas de quel camp elle vient n'est comptee nulle part - la mettre
        d'un cote au hasard ferait dire a la carte une chose fausse sur une
        equipe nommee, ce qui est pire que de n'en rien dire.

        Un sport sans carton rouge rend (0, 0) sans meme regarder : le hockey
        ne publie aucune action, et compter le vide est une facon de croire
        qu'on a compte.
        """
        if not self.sport.red_cards:
            return (0, 0)
        home = away = 0
        for play in self.red_cards:
            side = self.side_of(play.team_id)
            if side == "home":
                home += 1
            elif side == "away":
                away += 1
        return (home, away)

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
        # La source compresse si on le demande, et personne ne le demande a
        # notre place : urllib n'annonce rien tout seul. Mesure sur le tableau
        # de bord de la Ligue 1 : 33 832 octets sans, 4 145 avec. Huit fois
        # moins, sur 36 requetes par tour pour `--leagues all`, et c'est la
        # SEULE economie disponible - la source n'envoie ni ETag ni
        # Last-Modified, donc pas de requete conditionnelle possible.
        "Accept-Encoding": "gzip",
        "Accept-Language": "fr,en;q=0.8",
        "Cache-Control": "no-cache",
    }


# Les deux octets qui commencent un flux gzip. C'est eux qu'on regarde, et non
# l'en-tete `Content-Encoding` : un proxy qui decompresse en chemin ne pense
# pas toujours a retirer l'en-tete, et on se retrouverait a vouloir
# decompresser du JSON deja clair. L'inverse existe aussi. Les octets, eux, ne
# mentent pas.
GZIP_MAGIC = b"\x1f\x8b"


def uncompress(body, label: str = "") -> bytes:
    """Le corps d'une reponse, en clair, compresse ou non.

    Une reponse qui n'est pas du gzip ressort telle quelle : c'est le cas de
    tous les openers de test, qui rendent du JSON en clair, et ce doit rester
    le cas le jour ou la source cesserait de compresser.

    Une reponse annoncee gzip mais illisible, en revanche, est une panne
    franche et non une reponse vide - un corps tronque relu comme du JSON
    donnerait "reponse illisible", ce qui est vrai mais n'aide personne a
    comprendre ou ca casse.
    """
    if not isinstance(body, bytes) or not body.startswith(GZIP_MAGIC):
        return body
    try:
        return gzip.decompress(body)
    except Exception as exc:
        raise SourceError("reponse compressee illisible pour {} : {}".format(
            label or "la source", exc)) from exc


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
            body = response.read()
    except urllib.error.HTTPError as exc:
        raise SourceError("HTTP {} sur {}".format(exc.code, label)) from exc
    except Exception as exc:          # URLError, socket.timeout, ssl...
        raise SourceError("{} sur {} : {}".format(
            type(exc).__name__, label, exc)) from exc

    # Hors du `try` ci-dessus, expres : une decompression qui echoue n'est pas
    # une panne de reseau, et la faire passer pour telle enverrait chercher le
    # defaut du mauvais cote.
    return uncompress(body, label)


def day_code(moment) -> str:
    """Un jour dans la forme attendue par `dates` : AAAAMMJJ."""
    return moment.strftime(DAY_FORMAT)


def date_span(first, last=None) -> str:
    """La valeur du parametre `dates` : un jour, ou un intervalle.

    L'intervalle est une forme interne, lisible par les appelants. ESPN ne
    l'accepte plus directement : `fetch()` le traduit en mois complets, puis
    remet exactement les deux bornes ici demandees.
    """
    start = day_code(first)
    if last is None:
        return start
    end = day_code(last)
    # Un intervalle d'un seul jour n'apporte rien : autant poser la forme
    # courte, celle qu'on lit dans les journaux et dans les tests.
    return start if end == start else "{}-{}".format(start, end)


def _range_months(dates):
    """Les mois ESPN couvrant un intervalle, avec ses deux bornes.

    Rend None pour toute autre forme : un jour, un mois ou une valeur saisie
    par un appelant continue alors de voyager telle quelle jusqu'a la source.
    """
    found = DATE_RANGE.fullmatch(str(dates or ""))
    if found is None:
        return None
    try:
        first = datetime.strptime(found.group(1), DAY_FORMAT).date()
        last = datetime.strptime(found.group(2), DAY_FORMAT).date()
    except ValueError:
        return None
    if first > last:
        return None

    cursor = first.replace(day=1)
    final = last.replace(day=1)
    months = []
    while cursor <= final:
        months.append(cursor.strftime("%Y%m"))
        if cursor.month == 12:
            cursor = cursor.replace(year=cursor.year + 1, month=1)
        else:
            cursor = cursor.replace(month=cursor.month + 1)
    return found.group(1), found.group(2), tuple(months)


def _event_day(event):
    """Le jour AAAAMMJJ d'un evenement brut, s'il est lisible."""
    if not isinstance(event, dict):
        return ""
    stamps = [event.get("date")]
    competitions = event.get("competitions")
    if isinstance(competitions, list) and competitions:
        first = competitions[0]
        if isinstance(first, dict):
            stamps.append(first.get("date"))
    for stamp in stamps:
        if not isinstance(stamp, str):
            continue
        head = stamp[:10]
        if len(head) == 10 and head[4] == "-" and head[7] == "-":
            code = head.replace("-", "")
            if code.isdigit():
                return code
    return ""


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

    `dates` (voir date_span) demande une autre periode que la journee en
    cours. Un intervalle est lu par mois, parce que la source refuse desormais
    sa propre ancienne forme `AAAAMMJJ-AAAAMMJJ`.

    `opener` sert aux tests et a l'enregistrement : n'importe quel
    callable(url, timeout) -> bytes.
    """
    url = SCOREBOARD_URL.format(sport=(sport or sports.DEFAULT).code,
                                slug=slug)
    window = _range_months(dates)
    if window is None:
        if dates:
            url += "?" + urllib.parse.urlencode({"dates": dates})
        return _read_json(url, timeout, opener, slug)

    first, last, months = window
    pages = []
    for month in months:
        query = urllib.parse.urlencode({"dates": month, "limit": 1000})
        pages.append(_read_json(url + "?" + query, timeout, opener, slug))

    merged = dict(pages[0])
    events = []
    for page in pages:
        candidates = page.get("events")
        if not isinstance(candidates, list):
            continue
        for event in candidates:
            day = _event_day(event)
            # Une date absente ne doit pas faire disparaitre silencieusement
            # un match : les filtres metier de l'appelant restent le dernier
            # filet. Les dates lisibles, elles, rendent exactement l'ancien
            # contrat aux deux bornes comprises.
            if day and not first <= day <= last:
                continue
            events.append(event)
    merged["events"] = events
    return merged


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


def team_form(competitor) -> str:
    """Les derniers resultats d'une equipe, du plus recent au plus ancien.

    "LLWWW" se lit donc : defaite au dernier match, defaite avant, trois
    victoires avant ca. La source ne documente cet ordre nulle part ; il a ete
    verifie contre six matchs qui venaient de se terminer, dont la lettre de
    tete disait bien le resultat du jour.

    Une lettre inconnue fait jeter la chaine ENTIERE, pas la lettre : afficher
    quatre resultats sur cinq sans le dire serait pire que se taire.
    """
    form = str(competitor.get("form") or "").strip().upper()
    if not form or any(letter not in FORM_LETTERS for letter in form):
        return ""
    return form


def team_record(competitor) -> str:
    """Le bilan de la saison, "victoires-nuls-defaites", ou une chaine vide.

    Deux reponses justes n'ont rien a dire et sont ecartees ici :

      - le rugby republie sa forme sous `records` ("LWWWW" en guise de
        resume) la ou le football y met des chiffres. Sans le filtre, la carte
        afficherait la forme deux fois de suite ;
      - "0-0-0" n'est pas un bilan, c'est une competition qui n'a pas
        commence : la phase de groupes d'une coupe d'Europe le repond des
        juillet. Des chiffres justes qui ne disent rien.
    """
    entries = [entry for entry in competitor.get("records") or []
               if isinstance(entry, dict)]
    # `type == "total"` d'abord : la ou la source publie plusieurs bilans
    # (domicile, exterieur), c'est le seul qui parle de la saison entiere.
    entries.sort(key=lambda entry: entry.get("type") != "total")
    for entry in entries:
        summary = str(entry.get("summary") or "").strip()
        if RECORD.match(summary) and set(summary) - set("0-"):
            return summary
    return ""


def match_note(competition) -> str:
    """L'enjeu du match, en cle i18n ("note_first_leg"), ou une chaine vide.

    La source range ca sous `competitions[0].notes`, un tableau qui est la sur
    chaque match et vide sur 97 d'entre eux sur 100. Deux regles le lisent, et
    chacune existe pour une raison qu'un releve a mise au jour :

      - **on ne lit que la tete de la note**, jusqu'au premier " - ". Ce qui
        suit, quand il y a une suite, est le resultat de la confrontation :
        "2nd Leg - Arsenal advance 3-1 on aggregate". Couper la garantit qu'un
        resultat ne peut pas atteindre une carte, meme le jour ou la source en
        collera un sur un match a venir ;
      - **une tete inconnue se jette entierement**. Elle est en anglais et
        elle n'est pas traduite (l'espagnol et le portugais le sont, pas les
        cinq langues du programme) : la laisser passer mettrait "Kraft
        Hockeyville" en clair sur une carte allemande.

    Le tableau peut porter plusieurs notes ; on retient la premiere qu'on sait
    dire, et il n'y en a jamais eu deux.
    """
    notes = competition.get("notes")
    if not isinstance(notes, list):
        # La source la donne toujours en tableau. Si elle changeait d'avis, une
        # chaine ne serait pas decoupee lettre par lettre pour autant.
        return ""
    for note in notes:
        if not isinstance(note, dict):
            continue
        # `headline` et `text` portent le meme mot sur les 238 notes relevees ;
        # cinq d'entre elles n'avaient que `headline`, aucune que `text`.
        head = str(note.get("headline") or note.get("text") or "")
        key = NOTE_KEYS.get(head.split(" - ", 1)[0].strip().lower())
        if key:
            return key
    return ""


def _stat_value(raw):
    """Le nombre d'une statistique, ou None. "51.5" -> 51.5, "beaucoup" -> None.

    La source n'ecrit ses statistiques qu'en toutes lettres : un objet de
    `statistics[]` porte `name`, `abbreviation` et `displayValue`, et rien
    d'autre - pas de `value` numerique, sur les 96 588 objets releves. C'est
    donc une chaine qu'on lit, et il faut la lire prudemment.

    Le plafond n'est pas decoratif : `float()` avale "nan" et "inf" sans
    broncher, et les deux empoisonnent ensuite tout ce qu'ils touchent - une
    comparaison, un formatage, une carte. Un encadrement les arrete tous les
    deux d'un coup, NaN echouant meme la comparaison basse.
    """
    try:
        value = float(str(raw).strip())
    except (TypeError, ValueError):
        return None
    return value if 0.0 <= value <= 1e6 else None


def team_stats(competitor, sport=None) -> dict:
    """Les statistiques de match d'un camp, en nombres, ou un dictionnaire vide.

    Seuls les noms que le sport declare sont retenus (`Sport.team_stats`) : le
    football en publie neuf par camp ; les quatre valeurs utiles aux cartes
    sont conservees. Un sport qui ne declare rien - le hockey, le rugby - ne
    lit meme pas le champ.

    Une valeur illisible fait tomber SA statistique et elle seule : l'autre
    reste, et la carte sort. Le tri des paires, lui, se fait sur la carte, la
    ou l'on a les deux camps sous les yeux (voir watcher._stats_parts).
    """
    wanted = getattr(sport or sports.DEFAULT, "team_stats", ())
    if not wanted:
        return {}
    found = {}
    for entry in competitor.get("statistics") or []:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if name not in wanted or name in found:
            continue
        value = _stat_value(entry.get("displayValue"))
        if value is not None:
            found[name] = value
    return found


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


def competition_metadata(payload) -> tuple:
    """(logo_url, country_code) lu dans l'en-tete ESPN, sans URL inventee."""
    header = (payload.get("leagues") or [{}])[0]
    if not isinstance(header, dict):
        return "", ""
    url = header.get("logo")
    if not url:
        for entry in header.get("logos") or []:
            if isinstance(entry, dict) and entry.get("href"):
                url = entry["href"]
                break
    url = str(url or "").strip()
    if not url.lower().startswith(("http://", "https://")):
        url = ""

    country = header.get("country") or {}
    if isinstance(country, dict):
        country = (country.get("code") or country.get("abbreviation")
                   or country.get("isoCode") or "")
    country = str(country or "").strip().upper()
    # Un code pays publie par la source est court. Un libelle libre n'est pas
    # transforme ici : le contrat du feed fera son repli depuis le catalogue.
    if len(country) not in (2, 3):
        country = ""
    return url, country


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
    """(buts, cartons rouges, tirs au but) d'un match de football.

    Les trois vivent dans le meme tableau `details` : un but porte
    `scoringPlay`, une expulsion porte `redCard`, et un tir au but porte...
    `scoringPlay` lui aussi, plus `shootout`. Ils sont separes ici parce qu'ils
    ne servent pas a la meme chose (un but est habille par un buteur, une
    expulsion se signale pour elle-meme, une seance se resume a la fin).

    Le tri du troisieme est ce qui compte le plus, et il vient d'une
    observation : **un tir au but ne fait pas monter le score du match**.
    Verifie sur des seances reelles (FA Cup 2022, Coupe de France 2025, Coupe
    du monde 2022) - la source garde le score du temps reglementaire et publie
    la seance a cote. Un tir laisse dans `plays` serait un but que le score
    dement :
    onze buteurs sous un "0 - 0" sur la carte de fin de match, et onze lignes
    de buts dans `--scores`.
    """
    goals = []
    red_cards = []
    shootout = []
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
        key = str(detail.get("id") or "|".join(
            (team_id, str(clock), kind, athlete_id, str(index))))

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
            sequence=index,
        )
        if play.shootout:
            # Un tir au but est mis de cote meme quand la source le marque
            # aussi comme une expulsion : c'est le drapeau le plus precis qui
            # gagne, et il n'y a pas d'autre lecture possible d'un tir.
            shootout.append(play)
            continue
        # Un but reste un but, meme si la source colle les deux drapeaux.
        (goals if scoring else red_cards).append(play)
    return goals, red_cards, shootout


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
    """(actions de points, cartons rouges, tirs au but) d'un match de rugby.

    La troisieme liste est toujours vide, et le restera : le rugby a XV ne se
    departage pas aux tirs au but (voir sports.py). Elle est rendue quand meme
    pour que les deux lecteurs aient la meme forme.

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
        key = str(detail.get("id") or "|".join(
            (team_id, clock, text or kind_key, athlete_id, str(index))))

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
            sequence=index,
        )
        (red_cards if scored is None else scores).append(play)
    return scores, red_cards, []


def _parse_details(competition, sport=None) -> tuple:
    """(actions de score, cartons rouges, tirs au but) du match, selon le sport.

    Le hockey passe par la branche vide : la source ne publie pas de tableau
    d'actions pour lui, et inventer un buteur serait pire que de n'en afficher
    aucun. Sa fusillade ne fait pas exception - elle non plus n'a pas d'action
    publiee, seul le score du match la trahit.
    """
    sport = sport or sports.DEFAULT
    if sport.plays == sports.PLAYS_TYPES:
        return _rugby_details(competition)
    if sport.plays == sports.PLAYS_NONE:
        return [], [], []
    return _soccer_details(competition)


def _shootout_tally(competitor, kicks, team_id) -> int:
    """Les tirs au but reussis d'un cote : ce que la source dit, ou le compte.

    `shootoutScore` est la reponse la plus courte, mais elle manque : sur les
    dix seances relevees en Coupe de France 2025, neuf la portaient et une non,
    sans que rien d'autre ne distingue la dixieme. Compter les tirs reussis
    donne exactement le meme nombre partout ou les deux etaient la, et c'est
    donc le repli - il vaut mieux qu'un tiret.
    """
    given = competitor.get("shootoutScore")
    if given is not None:
        return _int(given)
    return sum(1 for kick in kicks if kick.team_id == team_id)


def _source_id(value) -> str:
    """Identifiant opaque publie par la source, jamais fabrique localement."""
    if isinstance(value, dict):
        value = (value.get("external_id") or value.get("externalId")
                 or value.get("id") or value.get("uid"))
    return str(value or "").strip()


def _positive_int(value):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _event_id_from_ref(value) -> str:
    if isinstance(value, dict):
        value = value.get("$ref") or value.get("href") or value.get("id")
    text = str(value or "").strip()
    found = re.search(r"/events/([^/?]+)", text)
    return found.group(1) if found else (text if "/" not in text else "")


def _phase_kind(item) -> str:
    """Categorie publique bornee du type de saison officiel."""
    if not isinstance(item, dict):
        return ""
    if item.get("hasGroups"):
        return "group"
    if item.get("hasStandings"):
        return "league"
    slug = str(item.get("slug") or "").lower()
    name = str(item.get("name") or "").lower()
    if "group" in slug or "group" in name:
        return "group"
    if any(word in (slug + " " + name) for word in (
            "round", "final", "playoff", "knockout", "cup")):
        return "knockout"
    return ""


def parse_competition_structure(season_payload, tournament_payload=None,
                                event_payloads=(), standings_payload=None) -> dict:
    """Normalise les liens officiels edition/phase/groupe/tableau.

    La sortie est volontairement independante des URL et des noms de champs
    ESPN. Elle peut etre jointe a un scoreboard sans jamais exposer les
    references hypermedia brutes dans le contrat public.
    """
    season_payload = season_payload if isinstance(season_payload, dict) else {}
    tournament_payload = (tournament_payload
                          if isinstance(tournament_payload, dict) else {})
    edition = {
        "external_id": _source_id(season_payload.get("year")),
        "name": str(season_payload.get("displayName") or "").strip(),
    }
    phases = {}
    raw_types = season_payload.get("types") or {}
    items = raw_types.get("items") if isinstance(raw_types, dict) else raw_types
    for order, item in enumerate(items or (), start=1):
        if not isinstance(item, dict):
            continue
        external_id = _source_id(item.get("type") or item.get("id"))
        if not external_id:
            continue
        normalized = {
            "external_id": external_id,
            "name": str(item.get("name") or item.get("displayName") or "").strip(),
            "order": order,
            "kind": _phase_kind(item),
            "source_id": _source_id(item.get("id")),
            "slug": str(item.get("slug") or "").strip(),
        }
        phases[external_id] = normalized
        if normalized["source_id"]:
            phases.setdefault(normalized["source_id"], normalized)

    groups = []
    standings_payload = (standings_payload
                         if isinstance(standings_payload, dict) else {})
    raw_groups = (standings_payload.get("children")
                  or season_payload.get("groups") or ())
    for order, group in enumerate(raw_groups, start=1):
        if not isinstance(group, dict):
            continue
        groups.append({
            "external_id": _source_id(group),
            "name": str(group.get("name") or group.get("displayName") or "").strip(),
            "order": order,
        })

    match_numbers = {}
    for event in event_payloads or ():
        if not isinstance(event, dict):
            continue
        event_id = _source_id(event.get("id"))
        competitions = event.get("competitions") or ()
        competition = competitions[0] if competitions and isinstance(
            competitions[0], dict) else {}
        number = _source_id(competition.get("matchNumber"))
        if event_id and number:
            match_numbers[number] = event_id

    tournament_groups = tournament_payload.get("groups") or ()
    all_event_ids = set()
    for group in tournament_groups:
        if not isinstance(group, dict):
            continue
        for matchup in group.get("matchups") or ():
            if not isinstance(matchup, dict):
                continue
            for event in matchup.get("events") or ():
                event_id = _event_id_from_ref(event)
                if event_id:
                    all_event_ids.add(event_id)

    events = {}
    for round_order, group in enumerate(tournament_groups, start=1):
        if not isinstance(group, dict):
            continue
        round_id = _source_id(group)
        round_name = str(group.get("displayName") or group.get("name") or "").strip()
        for matchup in group.get("matchups") or ():
            if not isinstance(matchup, dict):
                continue
            event_ids = [_event_id_from_ref(event)
                         for event in matchup.get("events") or ()]
            event_ids = [event_id for event_id in event_ids if event_id]
            advances = _source_id(matchup.get("winnerAdvancesTo"))
            next_match = match_numbers.get(advances)
            if next_match is None and advances in all_event_ids:
                next_match = advances
            for leg_number, event_id in enumerate(event_ids, start=1):
                events[event_id] = {
                    "round_external_id": round_id,
                    "round_name": round_name,
                    "round_order": round_order,
                    "tie_external_id": _source_id(matchup),
                    "leg_number": leg_number,
                    "bracket_slot": _positive_int(matchup.get("bracketLocation")),
                    "next_match_external_id": next_match or "",
                }
    return {"edition": edition, "phases": phases, "groups": groups,
            "events": events}


def _direct_hierarchy(event, competition) -> dict:
    season = event.get("season") or {}
    season = season if isinstance(season, dict) else {}
    phase = event.get("phase") or competition.get("phase") or {}
    phase = phase if isinstance(phase, dict) else {}
    phase_id = _source_id(phase) or _source_id(season.get("type"))
    phase_slug = str(phase.get("slug") or season.get("slug") or "").strip()
    phase_probe = dict(phase)
    if phase_slug:
        phase_probe.setdefault("slug", phase_slug)
    group = competition.get("group") or event.get("group") or {}
    group = group if isinstance(group, dict) else {}
    round_of = competition.get("round") or event.get("round") or {}
    round_of = round_of if isinstance(round_of, dict) else {}
    tie = competition.get("tie") or event.get("tie") or {}
    tie = tie if isinstance(tie, dict) else {}
    return {
        "edition_external_id": _source_id(season.get("year") or season.get("id")),
        "edition_name": str(season.get("displayName") or "").strip(),
        "phase_kind": _phase_kind(phase_probe),
        "phase_external_id": phase_id,
        "phase_name": str(phase.get("name") or phase.get("displayName") or "").strip(),
        "phase_order": _positive_int(phase.get("order")),
        "group_external_id": _source_id(group),
        "group_name": str(group.get("name") or group.get("displayName") or "").strip(),
        "group_order": _positive_int(group.get("order")),
        "round_external_id": _source_id(round_of),
        "round_name": str(round_of.get("name") or round_of.get("displayName") or "").strip(),
        "round_order": _positive_int(round_of.get("order")),
        "tie_external_id": _source_id(tie),
        "leg_number": _positive_int(competition.get("legNumber")
                                    or tie.get("legNumber")),
        "bracket_slot": _positive_int(competition.get("bracketSlot")
                                      or tie.get("bracketSlot")),
        "next_match_external_id": _source_id(
            competition.get("nextMatch") or tie.get("nextMatch")),
    }


def _event_hierarchy(event, competition, structure) -> dict:
    found = _direct_hierarchy(event, competition)
    structure = structure if isinstance(structure, dict) else {}
    edition = structure.get("edition") or {}
    found["edition_external_id"] = (found["edition_external_id"]
                                     or _source_id(edition))
    found["edition_name"] = found["edition_name"] or str(
        edition.get("name") or "").strip()
    phase = (structure.get("phases") or {}).get(found["phase_external_id"], {})
    if phase:
        found["phase_external_id"] = _source_id(phase)
        found["phase_name"] = found["phase_name"] or phase.get("name", "")
        found["phase_order"] = found["phase_order"] or phase.get("order")
        found["phase_kind"] = found["phase_kind"] or phase.get("kind", "")

    # Le scoreboard publie un altGameNote officiel ("..., Group A"). On ne le
    # parse pas librement : il ne sert qu'a joindre un nom de groupe exact deja
    # publie par la ressource de classement.
    if not found["group_external_id"] and found["phase_kind"] == "group":
        note = str(competition.get("altGameNote") or "").strip()
        candidates = [group for group in structure.get("groups") or ()
                      if group.get("name") and (note == group["name"]
                                                or note.endswith(", " + group["name"]))]
        if len(candidates) == 1:
            group = candidates[0]
            found["group_external_id"] = _source_id(group)
            found["group_name"] = group.get("name", "")
            found["group_order"] = group.get("order")

    for key, value in (structure.get("events") or {}).get(
            _source_id(event.get("id") or competition.get("id")), {}).items():
        if found.get(key) in (None, ""):
            found[key] = value
    return found


def parse(payload: dict, league, structure=None) -> list:
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
    logo, country = competition_metadata(payload)
    if hasattr(league, "adopt_metadata"):
        league.adopt_metadata(logo, country)

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

        goals, red_cards, kicks = _parse_details(competition, sport)
        home_color, home_alt = team_colors(home)
        away_color, away_alt = team_colors(away)

        # La competition est la copie la plus complete du stade. L'evenement
        # en porte parfois une seconde ; elle reste un repli utile si la
        # premiere disparait sur une competition encore inconnue.
        venue = competition.get("venue") or {}
        address = venue.get("address") if isinstance(venue, dict) else {}
        if not isinstance(address, dict):
            address = {}
        venue_country = address.get("country") or ""
        if not venue_country:
            event_venue = event.get("venue") or {}
            event_address = (event_venue.get("address")
                             if isinstance(event_venue, dict) else {})
            if isinstance(event_address, dict):
                venue_country = event_address.get("country") or ""
        # Le rugby range parfois "France" sous state, la ou le hockey range
        # une province courte comme "ON". Une valeur longue reste exploitable
        # par themes.country_motif ; une abreviation de province ne se fait pas
        # passer pour un pays.
        if not venue_country:
            venue_state = str(address.get("state") or "").strip()
            venue_country = venue_state if len(venue_state) > 2 else ""

        venue_name = str(venue.get("fullName") or venue.get("name") or "").strip()
        if not venue_name:
            event_venue = event.get("venue") or {}
            if isinstance(event_venue, dict):
                venue_name = str(event_venue.get("fullName")
                                 or event_venue.get("name") or "").strip()

        season_data = event.get("season") or payload.get("season") or {}
        if isinstance(season_data, dict):
            season = (season_data.get("displayName") or season_data.get("slug")
                      or season_data.get("year") or "")
        else:
            season = season_data

        home_team = home.get("team") or {}
        away_team = away.get("team") or {}
        hierarchy = _event_hierarchy(event, competition, structure)

        home_id = str((home.get("team") or {}).get("id") or "H")
        away_id = str((away.get("team") or {}).get("id") or "A")
        # Le vainqueur d'un match nul : sur un 1-1 de coupe, c'est la seule
        # chose de la reponse qui dise qui continue. La source pose le drapeau
        # sur les deux cotes ; on ne retient que celui qui est vrai.
        winner = ""
        if bool(home.get("winner")):
            winner = "home"
        elif bool(away.get("winner")):
            winner = "away"

        matches.append(Match(
            id=match_id,
            league=league,
            home=_team_name(home),
            away=_team_name(away),
            home_id=home_id,
            away_id=away_id,
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
            shootout=kicks,
            home_shootout=_shootout_tally(home, kicks, home_id),
            away_shootout=_shootout_tally(away, kicks, away_id),
            winner=winner,
            home_logo=team_logo(home),
            away_logo=team_logo(away),
            home_form=team_form(home),
            away_form=team_form(away),
            home_record=team_record(home),
            away_record=team_record(away),
            note=match_note(competition),
            home_stats=team_stats(home, sport),
            away_stats=team_stats(away, sport),
            home_color=home_color,
            away_color=away_color,
            home_alt=home_alt,
            away_alt=away_alt,
            venue_country=venue_country,
            venue=venue_name,
            season=season,
            home_short=(home_team.get("shortDisplayName")
                        or home_team.get("abbreviation") or ""),
            away_short=(away_team.get("shortDisplayName")
                        or away_team.get("abbreviation") or ""),
            home_slug=home_team.get("slug") or "",
            away_slug=away_team.get("slug") or "",
            **hierarchy
        ))
    return matches


def scoreboard(league, timeout: float = DEFAULT_TIMEOUT, opener=None,
               dates=None) -> list:
    """fetch + parse, pour une competition, quel que soit son sport."""
    sport = getattr(league, "sport", None) or sports.DEFAULT
    return parse(fetch(league.slug, timeout=timeout, opener=opener,
                       sport=sport, dates=dates), league)


# ------------------------------------------------------- resume d'un match ---
# Le hockey n'a pas de buteur dans le tableau de bord, il en a un dans le
# resume du match. Tout ce qui suit sert a l'y prendre, et rien d'autre : le
# resume n'est jamais lu pour lui-meme, ni pour un sport qui a deja ses actions.

# Ce qu'ESPN appelle un but dans `plays[]` : le numero, et le libelle en
# secours. Deux lectures pour la meme chose, comme au rugby - le jour ou les
# numeros bougent, le libelle sauve la carte, et le canari signale la derive.
GOAL_PLAY_TYPES = ("505",)
GOAL_PLAY_TEXT = "goal"

# Les roles publies sous `participants[].type`.
ROLE_SCORER = "scorer"
ROLE_ASSISTER = "assister"


def summary(league, event_id, timeout: float = SUMMARY_TIMEOUT,
            opener=None) -> dict:
    """Le resume brut d'UN match. 450 ko : a n'appeler qu'a bon escient.

    Passe par _read_json comme tout le reste - memes en-tetes, meme gzip, meme
    traduction des pannes en SourceError. Une seconde facon d'appeler ESPN
    aurait fini par diverger de la premiere, et c'est celle qui parle le moins
    souvent qui aurait derive sans qu'on le voie.

    L'appelant, lui, est tenu par sports.Sport.summary_plays : c'est ce drapeau
    qui dit quels sports en ont besoin, et watcher.py ne le demande qu'apres un
    but detecte, pour le seul match concerne.
    """
    sport = getattr(league, "sport", None) or sports.DEFAULT
    url = SUMMARY_URL.format(sport=sport.code, slug=league.slug)
    url += "?" + urllib.parse.urlencode({"event": str(event_id)})
    return _read_json(url, timeout, opener,
                      "{} / match {}".format(league.slug, event_id))


def _summary_minute(play) -> str:
    """"P2 12:07" : le tiers-temps en chiffre, l'horloge derriere.

    L'horloge seule ne suffit pas au hockey - elle repart a zero trois fois par
    match, et "0:29" ne dit pas de quel tiers-temps on parle. ESPN nomme bien
    la periode, mais en anglais ("1st", "OT") : la recopier ferait la seule
    ligne non traduite d'une carte allemande. Le numero, lui, se lit dans les
    cinq langues, et c'est pour ca qu'il est prefere au mot.
    """
    clock = str((play.get("clock") or {}).get("displayValue") or "").strip()
    if not clock:
        return ""
    try:
        return "P{} {}".format(int((play.get("period") or {}).get("number")),
                               clock)
    except (TypeError, ValueError):
        return clock


def _summary_participants(play) -> tuple:
    """(buteur, passeurs) d'une action de resume.

    Aucun repli sur "le premier participant" quand personne n'est marque
    `scorer` : un but de hockey nomme jusqu'a trois joueurs, et prendre le
    premier venu afficherait un passeur en gros a la place du buteur. Le jour
    ou ce role changerait de nom, la carte redeviendrait muette - ce que le
    canari verrait le lendemain matin, la ou un faux nom ne se voit jamais.
    """
    scorer = ""
    assists = []
    for part in play.get("participants") or []:
        if not isinstance(part, dict):
            continue
        athlete = part.get("athlete") or {}
        if not isinstance(athlete, dict):
            continue
        name = (athlete.get("shortName")
                or athlete.get("displayName") or "").strip()
        if not name:
            continue
        role = str(part.get("type") or "").strip().lower()
        if role == ROLE_SCORER and not scorer:
            scorer = name
        elif role == ROLE_ASSISTER:
            assists.append(name)
    return scorer, tuple(assists)


def summary_goals(payload: dict) -> list:
    """Les buts d'un resume, dans l'ordre ou la source les publie.

    Tout le reste de `plays[]` est jete : sur un match releve, 302 actions dont
    14 buts - les tirs, les mises au jeu et les penalites n'habillent aucune
    carte. Une action mal formee est ignoree comme ailleurs, elle ne fait pas
    echouer le lot.
    """
    goals = []
    for index, play in enumerate(payload.get("plays") or []):
        if not isinstance(play, dict):
            continue
        kind = play.get("type") or {}
        if not isinstance(kind, dict):
            continue
        type_id = str(kind.get("id") or "").strip()
        text = str(kind.get("text") or "").strip()
        if type_id not in GOAL_PLAY_TYPES and text.lower() != GOAL_PLAY_TEXT:
            continue

        team_id = str(((play.get("team") or {}).get("id") or "")).strip()
        minute = _summary_minute(play)
        scorer, assists = _summary_participants(play)
        goals.append(Play(
            key="|".join((team_id, minute, text or "Goal", str(index))),
            team_id=team_id,
            minute=minute,
            kind=text or "Goal",
            scorer=scorer,
            own_goal=False,
            penalty=False,
            shootout=False,
            assists=assists,
            sequence=index,
        ))
    return goals


def summary_scorer(goals, team_id, score: int):
    """Le but qui vient de porter cette equipe a `score`, ou None.

    On ne prend pas "le dernier but publie" mais le `score`-ieme, et seulement
    si le resume en compte exactement autant que le tableau de bord. C'est la
    seule facon de ne jamais coller le buteur precedent sur la carte du but
    suivant : un resume en retard d'un releve, une fusillade dont le but
    vainqueur n'est publie nulle part, une equipe que le resume ne nomme pas -
    les trois donnent le meme resultat, aucun nom, c'est-a-dire la carte de
    hockey d'avant ce chantier. Un nom faux, lui, ne se rattrape pas.
    """
    if score <= 0 or not team_id:
        return None
    mine = [goal for goal in goals if goal.team_id == team_id]
    return mine[-1] if len(mine) == score else None


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

    __slots__ = ("rank", "official_rank", "team", "team_id", "names",
                 "stats", "values")

    def __init__(self, rank, team, names=(), stats=None, team_id="",
                 official_rank=None, values=None):
        self.rank = rank              # le rang affiche, 1 pour le premier
        self.official_rank = official_rank
        self.team = team              # nom lisible
        self.team_id = str(team_id or "").strip()
        self.names = tuple(names) or (team,)   # toutes les ecritures connues
        self.stats = dict(stats or {})
        self.values = dict(values or {})

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

    __slots__ = ("name", "rows", "external_id", "order",
                 "phase_external_id", "phase_name", "phase_order")

    def __init__(self, name, rows=(), external_id="", order=None,
                 phase_external_id="", phase_name="", phase_order=None):
        self.name = name
        self.rows = list(rows)
        self.external_id = str(external_id or "").strip()
        self.order = order
        self.phase_external_id = str(phase_external_id or "").strip()
        self.phase_name = str(phase_name or "").strip()
        self.phase_order = phase_order

    def __repr__(self):
        return "<Group {} ({})>".format(self.name, len(self.rows))


class Table:
    """Le classement d'une competition, tel que la source le publie."""

    __slots__ = ("league", "season", "groups", "edition_external_id",
                 "edition_name")

    def __init__(self, league, season="", groups=(), edition_external_id="",
                 edition_name=""):
        self.league = league
        self.season = season          # "2026-27", ou vide
        self.groups = list(groups)
        self.edition_external_id = str(edition_external_id or "").strip()
        self.edition_name = str(edition_name or "").strip()

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


def _numeric_stats_of(entry) -> dict:
    """Valeurs officielles brutes, y compris une deduction egale a zero."""
    found = {}
    for stat in entry.get("stats") or []:
        if not isinstance(stat, dict):
            continue
        value = stat.get("value")
        if value is None:
            text = str(stat.get("displayValue") or "").strip()
            try:
                value = float(text)
            except ValueError:
                continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        number = int(number) if number.is_integer() else number
        for key in (stat.get("type"), stat.get("name")):
            key = str(key or "").strip().lower()
            if key and key not in found:
                found[key] = number
    return found


def _rank_of(stats) -> int | None:
    """Le rang publie par la source, ou None quand elle n'en publie pas."""
    for key in RANK_KEYS:
        found = _int(stats.get(key), 0)
        if found > 0:
            return found
    return None


def _parse_group(child, order=None, structure=None) -> Group:
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
        values = _numeric_stats_of(entry)
        official_rank = _rank_of(stats)
        if official_rank is None:
            official_rank = _positive_int(
                values.get("rank") or values.get("playoffseed"))
        rank = official_rank
        if official_rank is None:
            ranked = False
            rank = position
        rows.append(Row(
            rank=rank,
            official_rank=official_rank,
            team=_team_name(wrapper),
            team_id=_source_id(team),
            names=team_names(wrapper),
            stats=stats,
            values=values,
        ))

    if ranked:
        rows.sort(key=lambda row: row.rank)
    group_id = _source_id(child)
    phase_id = _source_id(standings_of.get("seasonType"))
    phase_name = ""
    phase_order = None
    phase = ((structure or {}).get("phases") or {}).get(phase_id, {})
    if phase:
        phase_id = _source_id(phase)
        phase_name = phase.get("name", "")
        phase_order = phase.get("order")
    return Group(name, rows, external_id=group_id, order=order,
                 phase_external_id=phase_id, phase_name=phase_name,
                 phase_order=phase_order)


def parse_standings(payload: dict, league, structure=None) -> Table:
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
    for order, child in enumerate(children, start=1):
        if not isinstance(child, dict):
            continue
        groups.append(_parse_group(child, order=order, structure=structure))
        if not season:
            season = season_label(
                (child.get("standings") or {}).get("seasonDisplayName"))

    if not season:
        # Le repli : la saison en cours d'apres l'en-tete. Elle peut differer
        # de celle du classement servi - en intersaison, la source rend encore
        # celui de la saison passee - d'ou l'ordre : le classement d'abord,
        # l'en-tete seulement s'il n'a rien dit.
        season = season_label((payload.get("season") or {}).get("displayName"))
    raw_season = payload.get("season") or {}
    raw_season = raw_season if isinstance(raw_season, dict) else {}
    edition = (structure or {}).get("edition") or {}
    edition_id = (_source_id(edition)
                  or _source_id(raw_season.get("year") or raw_season.get("id")))
    edition_name = (str(edition.get("name") or "").strip()
                    or str(raw_season.get("displayName") or "").strip())
    return Table(league, season=season, groups=groups,
                 edition_external_id=edition_id, edition_name=edition_name)


def standings(league, timeout: float = DEFAULT_TIMEOUT, opener=None) -> Table:
    """Le classement d'une competition, quel que soit son sport."""
    sport = getattr(league, "sport", None) or sports.DEFAULT
    url = STANDINGS_URL.format(sport=sport.code, slug=league.slug)
    return parse_standings(_read_json(url, timeout, opener, league.slug),
                           league)
