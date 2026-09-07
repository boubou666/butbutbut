"""Les sports que butbutbut sait suivre, et pourquoi ceux-la seulement.

Le tableau de bord d'ESPN a la meme forme pour tous les sports : seul le
premier segment de l'URL change.

    https://site.api.espn.com/apis/site/v2/sports/<sport>/<ligue>/scoreboard

Ouvrir le catalogue est donc gratuit du cote du reseau. Ce n'est pas gratuit du
cote de l'utilisateur : butbutbut n'est pas un tableau de scores, c'est un
programme qui fait du bruit et pose une carte devant ce qu'on etait en train de
faire. Le modele tient en une phrase - **un score qui monte, c'est un
evenement qui merite un son** - et un sport n'entre ici que s'il tient dans
cette phrase.


Les trois retenus
-----------------

**Le football** reste le sport par defaut, et rien ne change pour lui : un but
toutes les quarante-cinq minutes environ, chacun raconte quelque chose, et la
source publie le buteur, la minute, le csc et le penalty.

**Le hockey sur glace** colle au modele : six a sept buts par match, soit un
toutes les dix minutes, chacun renverse ou confirme quelque chose. Reserve :
le **tableau de bord** ne publie aucun tableau d'actions pour le hockey -
verifie contre `hockey/nhl`, sur des matchs joues comme sur des matchs a venir,
le `details` de la competition est toujours absent. Ses buteurs vivent
ailleurs, dans le resume du match (`/summary?event=<id>`, `plays[]`), qui pese
450 ko : c'est le drapeau `summary_plays` ci-dessous, et il ne se paye qu'apres
un but, pour le seul match qui vient d'en encaisser un. Quand ce resume ne
repond pas, la carte redevient ce qu'elle a toujours ete - un score et une
minute, sans troisieme ligne. Mieux vaut une carte honnete qu'un nom invente.

**Le rugby a XV** colle aussi, mais autrement : cinq a huit actions de points
par match, et surtout des actions qui ne se valent pas. Un essai n'est pas une
transformation, et le score monte de 5, de 3 ou de 2 selon ce qui vient de se
passer. C'est justement ce qui rend le sport interessant ici : le `delta` porte
une information que le football n'a jamais eue. La source publie un tableau
d'actions complet (essai, transformation, penalite, drop, carton rouge) avec le
joueur et la minute.


Celui qu'on laisse dehors : le basket
-------------------------------------

Un match NBA, c'est environ 220 points, soit un panier toutes les vingt a
trente secondes. Une carte et une corne de stade a ce rythme ne sont plus une
notification, c'est une alarme incendie : au bout de dix minutes on coupe le
son, et au bout de vingt on desinstalle. Rendre le basket supportable
demanderait de changer le modele, pas d'ajouter une ligne au catalogue - il
faudrait ne signaler que ce qui compte (un 3-points decisif, un ecart qui
bascule, les deux dernieres minutes d'un match serre), donc juger de
l'importance d'une action, donc lire autre chose que le score. C'est un autre
programme. `--leagues basketball:nba` est refuse, avec cette raison en clair.

Le meme raisonnement ecarte le handball (60 buts par match) et le tennis (un
point toutes les trente secondes, et un score qui n'est pas un entier qui
monte). Le football americain et le baseball tomberaient dans la bonne cadence
mais pas dans le bon modele : un touchdown vaut 6 points puis 1 de plus une
minute apres, et un score qui monte de 6 puis de 1 ferait deux cartes pour une
seule action.


Ce qu'un sport porte
--------------------

Le strict necessaire pour que le reste du programme n'ait jamais a demander
"est-ce que c'est du foot ?" :

  - `code` : le segment d'URL, et rien d'autre ;
  - `plays` : comment lire le tableau d'actions, parce que les trois sports ne
    le publient pas pareil (voir espn.py) ;
  - `breaks` : ce qu'ESPN ecrit dans `status.type.name` pendant une pause. Le
    hockey n'a pas de mi-temps, il a deux pauses entre trois tiers-temps ;
  - `shootout` : ce qu'ESPN ecrit quand le match s'est decide aux tirs au but.
    Un sport qui n'y va jamais - le rugby - ne met rien ici ;
  - `titles` : les libelles de carte qui changent de mot d'un sport a l'autre.
    Un sport qui n'a rien a redire ne met rien ici, et retombe sur le
    vocabulaire du football ;
  - `unit_score` : vrai quand un score ne monte que de 1. Faux au rugby, ou la
    carte doit dire de combien de points le score a bouge ;
  - `red_cards` : vrai quand le sport expulse a la carte rouge. Le hockey ne
    le fait pas - il a des penalites, pas des expulsions - et le tableau de
    bord ne publie de toute facon aucune action pour lui ;
  - `summary_plays` : vrai quand les buteurs de ce sport ne sont pas dans le
    tableau de bord mais dans le resume du match, qu'il faut donc aller
    chercher a part. Le drapeau existe pour que personne ne paye cette requete
    sans en avoir besoin : le football a deja ses buteurs sous la main, il ne
    doit pas depenser 450 ko pour les relire ;
  - `table` : les colonnes du classement, parce qu'un classement de hockey et
    un classement de football ne comptent pas les memes choses.

Ce module ne connait ni les competitions ni les cartes : il ne fait que dire
comment un sport se comporte. Le catalogue vit dans leagues.py.
"""

from __future__ import annotations

# Comment se lit le tableau `details` d'une competition. Les trois sports ne
# le remplissent pas de la meme facon, et c'est la seule vraie difference de
# lecture entre eux.
PLAYS_FLAGS = "flags"    # football : des drapeaux (scoringPlay, redCard)
PLAYS_TYPES = "types"    # rugby : un type numerote (1 = essai, 2 = transf.)
PLAYS_NONE = "none"      # hockey : le tableau de bord ne publie rien du tout


# Comment un match qui s'est decide aux tirs au but se reconnait dans la
# reponse. Releve sur des seances reelles, pas deduit : voir le README, section
# "Les tirs au but".
#
# Au **football**, la seance a son propre etat de fin : `status.type.name` vaut
# STATUS_FINAL_PEN et `shortDetail` "FT-Pens" (FA Cup 2022, Coupe de France
# 2025, Coupe du monde 2022, Ligue des champions 2025 - la meme chose partout).
# Au **hockey**, l'etat reste STATUS_FINAL et c'est le detail qui le dit :
# "Final/SO". Chercher dans les deux chaines a la fois coute une concatenation
# et evite d'avoir a se rappeler laquelle porte l'information.
SHOOTOUT_SOCCER = ("FINAL_PEN", "FT-PENS")
SHOOTOUT_HOCKEY = ("FINAL/SO",)


# Les colonnes du classement, sport par sport : ce que la source publie
# vraiment, et rien de plus. Les trois sports ne comptent pas les memes
# choses - le hockey ignore le match nul mais compte les defaites en
# prolongation, le rugby ajoute ses points de bonus, le football n'a ni l'un
# ni l'autre. Fabriquer une colonne "N" pour le hockey reviendrait a inventer
# un zero qui ne veut rien dire, et une colonne de bonus au football afficherait
# du vide sur dix-huit lignes.
#
# Chaque colonne est un (en-tete, cles acceptees). Plusieurs cles, parce que la
# source appelle la difference de points "pointdifferential" au football et au
# hockey mais "pointsdifference" au rugby : les accepter toutes des maintenant
# coute une ligne et evite une colonne vide le jour ou l'un des deux noms
# gagne. Une cle qu'on ne trouve pas donne un tiret, jamais une erreur.

TABLE_SOCCER = (
    ("table_played", ("gamesplayed",)),
    ("table_won", ("wins", "gameswon")),
    ("table_drawn", ("ties", "gamesdrawn")),
    ("table_lost", ("losses", "gameslost")),
    ("table_diff", ("pointdifferential", "pointsdifference")),
    ("table_points", ("points",)),
)

# Le hockey n'a pas de match nul : un match se decide toujours, en prolongation
# ou aux tirs au but. La colonne qui compte est donc "DP", les defaites en
# prolongation, qui rapportent un point la ou une defaite seche n'en rapporte
# aucun - sans elle, le total de points de la ligne ne se retrouve pas.
TABLE_HOCKEY = (
    ("table_played", ("gamesplayed",)),
    ("table_won", ("wins", "gameswon")),
    ("table_lost", ("losses", "gameslost")),
    ("table_otl", ("otlosses", "overtimelosses")),
    ("table_diff", ("pointdifferential", "pointsdifference")),
    ("table_points", ("points",)),
)

# Le rugby ajoute les points de bonus : quatre essais ou une defaite de moins
# de huit points en rapportent un, et c'est ce qui fait qu'une equipe passe
# devant une autre a nombre de victoires egal. Un classement de rugby sans la
# colonne "Bon" ne s'explique pas.
TABLE_RUGBY = (
    ("table_played", ("gamesplayed",)),
    ("table_won", ("wins", "gameswon")),
    ("table_drawn", ("ties", "gamesdrawn")),
    ("table_lost", ("losses", "gameslost")),
    ("table_bonus", ("bonuspoints",)),
    ("table_diff", ("pointdifferential", "pointsdifference")),
    ("table_points", ("points",)),
)


class Sport:
    """Un sport d'ESPN : son segment d'URL et ses quelques particularites."""

    __slots__ = ("code", "name", "aliases", "plays", "breaks", "shootout",
                 "unit_score", "red_cards", "summary_plays", "logo_pattern",
                 "table", "_titles")

    def __init__(self, code, name, aliases=(), plays=PLAYS_FLAGS, breaks=(),
                 shootout=(), unit_score=True, logo_pattern="", titles=None,
                 table=TABLE_SOCCER, red_cards=True, summary_plays=False):
        self.code = code                  # "soccer", "hockey", "rugby"
        self.name = name                  # "football", en francais, pour le journal
        self.aliases = tuple(aliases)     # ce qu'on peut taper a --leagues
        self.plays = plays
        # Marqueurs supplementaires de pause dans status.type.name. Le controle
        # generique (HALFTIME) reste actif partout : ceci ne fait qu'ajouter.
        self.breaks = tuple(breaks)
        # Les marqueurs de seance de tirs au but, cherches en majuscules dans
        # le nom d'etat ET dans le detail court. Vide = ce sport n'en connait
        # pas, et aucune carte ne parlera jamais de tirs au but chez lui.
        self.shootout = tuple(shootout)
        self.unit_score = bool(unit_score)
        # Faux quand le sport ne connait pas l'expulsion : la carte n'a alors
        # aucun carton a compter, et un compteur a zero qui ne bougera jamais
        # vaut moins que rien du tout.
        self.red_cards = bool(red_cards)
        # Vrai quand il faut aller lire le resume du match pour connaitre les
        # buteurs. Faux par defaut, et ce defaut est le bon : le resume pese
        # 450 ko, un sport qui publie deja ses actions dans le tableau de bord
        # n'a aucune raison de les payer une seconde fois.
        self.summary_plays = bool(summary_plays)
        # De quoi reconstruire l'URL d'un ecusson a partir du seul numero
        # d'equipe. Ne sert qu'aux cartes de demonstration : partout ailleurs
        # l'URL vient de la source. Le hockey range ses ecussons sous
        # l'abreviation du club et non sous son numero - "bos", pas "18".
        self.logo_pattern = logo_pattern
        # Les colonnes du classement. Le football sert de socle ici aussi : un
        # sport qui n'a rien de particulier a compter herite des siennes.
        self.table = tuple(table)
        self._titles = dict(titles or {})

    def title_key(self, key: str) -> str:
        """La cle de libelle a utiliser pour ce sport.

        Un sport qui n'a pas d'avis rend la cle telle quelle : le vocabulaire
        du football sert de socle, et chaque sport ne redit que ce qui differe.
        """
        return self._titles.get(key, key)

    @property
    def overrides(self) -> dict:
        """Les libelles que ce sport reformule. Lecture seule, pour les tests."""
        return dict(self._titles)

    def matches_token(self, token: str) -> bool:
        token = token.strip().lower()
        return token == self.code or token in self.aliases

    def __repr__(self):
        return "<Sport {}>".format(self.code)


# --- Le football : le defaut absolu, et le socle de vocabulaire --------------

SOCCER = Sport(
    "soccer", "football",
    aliases=("foot", "football", "soccer"),
    plays=PLAYS_FLAGS,
    shootout=SHOOTOUT_SOCCER,
    logo_pattern="https://a.espncdn.com/i/teamlogos/soccer/500/{id}.png",
)

# --- Le hockey sur glace ----------------------------------------------------
# Aucun tableau d'actions dans le tableau de bord : le score et l'horloge, c'est
# tout ce qu'un releve ordinaire en tire. Et trois
# tiers-temps la ou le football a deux mi-temps, d'ou un vocabulaire de pause
# a lui. Les noms exacts qu'ESPN pose pendant une pause n'ont pas pu etre
# observes (aucun match en cours au moment de l'ecriture) : la liste est donc
# large, et le repli est le silence. Un nom non reconnu laisse simplement le
# match "en cours", donc aucune carte - jamais une carte fausse.

HOCKEY = Sport(
    "hockey", "hockey sur glace",
    aliases=("hockey", "glace", "icehockey"),
    plays=PLAYS_NONE,
    # ... mais le resume du match, lui, porte les buteurs et leurs passeurs.
    # Le seul sport des trois dans ce cas : c'est ce drapeau qui autorise la
    # requete supplementaire, et lui seul.
    summary_plays=True,
    breaks=("INTERMISSION", "END_PERIOD", "END_OF_PERIOD"),
    # La fusillade du hockey ne se lit pas comme celle du football : elle
    # donne un but au vainqueur, dans le score du match. Le marqueur ne sert
    # donc qu'a EXPLIQUER un 4-3 qui n'a pas eu lieu dans le temps reglemen-
    # taire, jamais a mettre des tirs de cote - il n'y en a pas a mettre, le
    # resume ne publie pas la fusillade tir par tir.
    shootout=SHOOTOUT_HOCKEY,
    # Pas de carton rouge au hockey : une faute y coute deux minutes sur le
    # banc des penalites, et l'exclusion de match ne se dit pas par un carton.
    red_cards=False,
    logo_pattern="https://a.espncdn.com/i/teamlogos/nhl/500/{id}.png",
    table=TABLE_HOCKEY,
    titles={
        "title_kickoff": "title_faceoff",
        "title_halftime": "title_period_break",
        "title_restart": "title_period_restart",
        "title_fulltime": "title_game_over",
    },
)

# --- Le rugby a XV ----------------------------------------------------------
# Le seul des trois ou le score ne monte pas de 1 : un essai vaut 5 points, un
# drop et une penalite 3, une transformation 2. Le titre de la carte vient donc
# de l'action et non du sport, et quand l'action n'est pas encore publiee la
# carte annonce des "points", pas un "but".
#
# Aucun marqueur de tirs au but : le reglement en prevoit bien un (le concours
# de coups de pied), il n'a jamais servi dans un match professionnel, et
# guetter une chaine qu'ESPN n'a jamais eu a ecrire serait guetter une
# invention.

RUGBY = Sport(
    "rugby", "rugby a XV",
    aliases=("rugby", "xv", "rugbyxv"),
    plays=PLAYS_TYPES,
    unit_score=False,
    logo_pattern="https://a.espncdn.com/i/teamlogos/rugby/teams/500/{id}.png",
    table=TABLE_RUGBY,
    titles={
        "title_goal": "title_points",
        "title_cancelled": "title_points_cancelled",
    },
)

SPORTS = (SOCCER, HOCKEY, RUGBY)
BY_CODE = {sport.code: sport for sport in SPORTS}
DEFAULT = SOCCER

# Les sports qu'on refuse expres, avec la raison. Une erreur qui explique vaut
# mieux qu'une erreur qui liste : quelqu'un qui tape "basketball:nba" a une
# idee en tete, autant y repondre.
DECLINED = {
    "basketball": "un panier toutes les trente secondes : une carte et une "
                  "corne a ce rythme ne notifient plus rien, elles alertent. "
                  "Voir le README, section 'Les sports'.",
    "basket": "voir 'basketball'.",
    "nba": "voir 'basketball'.",
    "handball": "soixante buts par match : meme probleme que le basket.",
    "tennis": "le score n'y est pas un entier qui monte (15, 30, 40, jeu).",
}


def find(token: str):
    """Le sport designe par `token`, ou None."""
    lowered = (token or "").strip().lower()
    for sport in SPORTS:
        if sport.matches_token(lowered):
            return sport
    return None


def declined(token: str) -> str:
    """La raison pour laquelle ce sport est ecarte, ou une chaine vide."""
    return DECLINED.get((token or "").strip().lower(), "")


def describe() -> str:
    """Les sports ouverts, pour un message d'aide."""
    return ", ".join(sport.code for sport in SPORTS)
