"""Les cartes de score : elles s'empilent dans un coin de l'ecran, puis s'effacent.

Trois lignes par carte, toujours les memes :

    BUT !   LIGUE 1                                            35'
    (o) Angers       1 - 2       Stade Rennais (o)
    But de C. Arcus

La fin du match en ajoute quelques-unes, une par camp qui a marque :

    FIN DU MATCH   LIGUE 1                                  90'+4'
    Angers        1 - 2        Stade Rennais
    Angers : M. Lopez 12'
    Stade Rennais : A. Kalimuendo 58', L. Blas 77'

Une equipe reduite a dix le dit sans un mot : un rectangle rouge par
expulsion, pose contre le chiffre de l'equipe qui l'a prise, sur toutes les
cartes et pas seulement sur celle de l'expulsion.

    BUT !   LIGUE 1                                            35'
    (o) Angers   [] 1 - 2   Stade Rennais (o)
    But de C. Arcus

L'equipe qui vient de marquer et son chiffre sont ecrits dans la couleur de son
club (voir crests.py : elle n'est prise que si elle se lit sur ce fond tres
sombre), le filet vertical garde celle de la competition et le nom du buteur
ressort en clair. On sait donc d'un coup d'oeil qui a marque, ou en est le
match et dans quel championnat il se joue. Chaque equipe porte son ecusson a
cote de son nom, quand il est deja en cache.

Deux cartes prennent plus d'air : l'avant-match et le coup d'envoi mettent les
illustrations territoriales des clubs face a face. Elles entrent depuis les
bords, se posent autour du VS ou du score, puis revelent la composition
complete. Un ecusson prend le relais si une illustration manque.

Deux buts coup sur coup ne se marchent pas dessus : chaque carte est une
fenetre a elle, et `Stack` les empile depuis le coin (la derniere arrivee est
collee au coin, les precedentes remontent). Quand l'une s'efface, les autres
reprennent sa place.

Une carte fait exception : la **carte epinglee** (`--pin om`, voir pinned.py).
Elle ne s'efface pas, elle suit un match du coup d'envoi au coup de sifflet
final. Elle est **ancree au coin**, et la pile des fugaces demarre juste apres
elle. Deux raisons a ce choix : la pile ne peut pas la pousser dehors, puisque
le plafond de cinq cartes ne compte que les fugaces ; et elle ne peut pas
masquer un but, puisque toutes les places sont calculees ensemble, la sienne
d'abord. Elle perd le coin, qui est la meilleure place, mais elle est la en
permanence : c'est a l'oeil de savoir ou la chercher, pas au but d'attendre.

Multiplateforme, comme doot :
  - Windows : fond reellement transparent (-transparentcolor), fenetres
    "click-through" qui ne volent jamais le focus (styles etendus Win32) ;
  - macOS   : fenetres sans bordure, absentes du Dock ;
  - Linux   : fenetres de type "splash", posees au-dessus, sans decoration.

Une carte reste une fenetre `topmost` : une application en plein ecran lui
passe devant. `fullscreen` sait le dire sous Windows ; la pile le note alors
dans le journal, et peut reproposer la carte plus tard (voir `push`). Passer
devant est une chose, sortir l'autre de son plein ecran en est une autre : une
carte n'active jamais rien et n'a pas de bouton dans la barre des taches, sous
peine de la faire remonter par-dessus le jeu (voir `desktop_overlay.window.prepare_window`).
"""

from __future__ import annotations

import math
import sys
import time

from desktop_overlay import window as overlay_window

from . import crests, fullscreen, i18n, leagues, screens, sound, sports, themes

TRANSPARENT_KEY = "#ff00fe"
CARD_BG = "#0d1017"
CARD_EDGE = "#232936"
TEXT = "#f3f5f9"
MUTED = "#8b95a7"
CANCEL_ACCENT = "#ffa63d"
RED_CARD = "#e5484d"
COUNTRY_ATLAS = themes.ATLAS

PAD_X = 22
PAD_Y = 16
BAR_WIDTH = 7
RADIUS = 14
GAP = 26                 # espace entre un nom d'equipe et le score
LINE_GAP = 12
EXTRA_GAP = 6            # espace entre deux lignes supplementaires
STACK_GAP = 10           # espace entre deux cartes empilees
MAX_EXTRA_LINES = 4      # au-dela, la carte serait plus haute qu'utile

LOGO_RATIO = 1.35        # cote de l'ecusson, en hauteurs de ligne d'equipe
LOGO_GAP = 10            # espace entre un ecusson et le nom de son equipe

# Le carton rouge est dessine, jamais ecrit : un rectangle se reconnait de
# loin et ne demande pas de police, la ou un "1 rouge" demanderait de lire.
# Ses proportions sont celles d'un vrai carton, et sa taille suit celle de la
# ligne d'equipe - donc --scale, sans avoir a s'en souvenir.
RED_RATIO = 0.56         # hauteur d'un carton, en hauteurs de ligne d'equipe
RED_ASPECT = 0.68        # largeur d'un carton, en hauteurs de carton
RED_GAP = 3              # espace entre deux cartons du meme camp
RED_NAME_GAP = 9         # espace entre les cartons et le nom de l'equipe

MIN_WIDTH = 420          # largeur de confort : les cartes empilees s'alignent
MAX_WIDTH = 720
MATCH_INTRO_MIN_WIDTH = 500
MOMENT_MIN_WIDTH = 500

FADE_IN = 0.22
FADE_OUT = 0.40
FADE_STEPS = 12
PUMP_MS = 120            # cadence des petites taches de la boucle tkinter

# L'avant-match et le coup d'envoi ont leur propre ouverture : les deux
# illustrations territoriales des clubs entrent face a face et se posent a
# leur place definitive. L'animation ne remplace jamais la carte : elle n'est
# qu'un calque identique pose par-dessus, et disparait sans saut au moindre
# probleme de Canvas.
DUEL_FRAME_MS = 20
DUEL_ENTER_FRAMES = 24
DUEL_HOLD_FRAMES = 22
DUEL_FRAMES = DUEL_ENTER_FRAMES + DUEL_HOLD_FRAMES
DUEL_MS = DUEL_FRAMES * DUEL_FRAME_MS

# But et carton rouge partagent le meme gabarit et la meme cadence. Leur geste
# reste different : un club pousse depuis son camp sur un but, tandis que le
# carton tombe d'un coup sec au milieu de la composition.
MOMENT_FRAME_MS = 20
MOMENT_ENTER_FRAMES = 24
MOMENT_HOLD_FRAMES = 24
MOMENT_FRAMES = MOMENT_ENTER_FRAMES + MOMENT_HOLD_FRAMES
MOMENT_MS = MOMENT_FRAMES * MOMENT_FRAME_MS
GOAL_CRY_PIXELS_PER_SECOND = 130

MAX_VISIBLE = 5          # au-dela, la plus ancienne carte cede sa place

RETRY_POLL_MS = 2000     # cadence a laquelle on regarde si le plein ecran a cesse

FONT_CANDIDATES = {
    "win32": ("Segoe UI", "Tahoma", "Arial"),
    "darwin": ("SF Pro Text", "Helvetica Neue", "Helvetica"),
}
LINUX_FONTS = ("Inter", "Cantarell", "DejaVu Sans", "Liberation Sans", "Noto Sans")


# Cartes de demonstration : de vraies equipes, avec leurs vraies couleurs et
# leurs vrais numeros ESPN, pour que `--test` montre exactement ce que donne un
# but. Chaque equipe : (nom, numero ESPN, couleur, couleur secondaire).
#
# `reds` - les expulsions (domicile, exterieur) - n'est pose que la ou il y en
# a : `--test` doit montrer le carton rouge une fois, pas sur les cinq cartes
# d'affilee, sans quoi il ne montre plus une expulsion mais une decoration.
#
# Le choix des buteurs n'est pas innocent : `--test 5` promene ainsi la couleur
# du club sur les trois etages de crests.pick_accent. Le Bayern (dc052d) garde
# sa couleur, Chelsea (144992) et Barcelone (990000) sont illisibles sur ce
# fond et passent a leur couleur secondaire, le Paris FC (000000, secondaire
# 000000 elle aussi) n'a rien de lisible et retombe sur le jaune de la Ligue 1.
DEMO = {
    "fra.1": {"home": ("Marseille", "176", "ffffff", "011F68"),
              "away": ("Paris FC", "6851", "000000", "000000"),
              "score": (2, 1), "side": "away",
              "scorer": "I. Kebbal", "minute": "67'"},
    "eng.1": {"home": ("Arsenal", "359", "e20520", "003399"),
              "away": ("Chelsea", "363", "144992", "ffffff"),
              "score": (1, 2), "side": "away", "reds": (1, 0),
              "scorer": "C. Palmer", "minute": "74'"},
    "esp.1": {"home": ("Real Madrid", "86", "ffffff", "1B4D3E"),
              "away": ("Barcelona", "83", "990000", "FCE38A"),
              "score": (3, 3), "side": "away",
              "scorer": "L. Yamal", "minute": "88'"},
    "ita.1": {"home": ("Inter Milan", "110", "00239c", "ffffff"),
              "away": ("Juventus", "111", "000000", "E8A2B0"),
              "score": (1, 0), "side": "home",
              "scorer": "M. Thuram", "minute": "23'"},
    "ger.1": {"home": ("Bayern Munich", "132", "dc052d", "1a1a1a"),
              "away": ("Dortmund", "124", "ffee00", "272726"),
              "score": (4, 2), "side": "home",
              "scorer": "H. Kane", "minute": "56'"},
}

# La meme chose pour les autres sports, ou l'exemple ne peut pas etre une
# equipe de football. Chacun apporte aussi son vocabulaire : une carte de
# demonstration de rugby qui annoncerait "BUT !" ne demontrerait rien.
#
# Les identifiants ne sont pas des numeros partout : le hockey range ses
# ecussons sous l'abreviation du club ("bos"), le rugby sous un numero. C'est
# `sport.logo_pattern` qui sait lequel (voir sports.py).
DEMO_BY_SPORT = {
    "hockey": {"home": ("Boston Bruins", "bos", "231f20", "fdb71a"),
               "away": ("Montreal Canadiens", "mtl", "c41230", "013a81"),
               "score": (3, 2), "side": "home",
               "scorer": "D. Pastrnak", "minute": "12:07",
               "title": "title_goal", "by": "goal_by"},
    "rugby": {"home": ("Stade Toulousain", "25922", "000000", ""),
              "away": ("Stade Francais", "25921", "cc0066", ""),
              "score": (19, 14), "side": "home", "reds": (0, 1),
              "scorer": "A. Dupont", "minute": "63'",
              "title": "title_try", "by": "try_by"},
}


class DisplayUnavailable(RuntimeError):
    """Aucune fenetre possible ici, quelle qu'en soit la raison.

    Les deux raisons ne se soignent pas pareil - il manque un paquet, ou il
    manque un serveur graphique - mais l'appelant, lui, en fait la meme chose :
    il ecrit ses cartes dans le terminal. D'ou ce parent commun, qui lui evite
    d'enumerer les pannes.
    """


class TkinterMissing(DisplayUnavailable):
    """tkinter absent : paquet systeme a installer."""


class NoDisplay(DisplayUnavailable):
    """tkinter est bien la, mais il n'a aucun affichage ou s'ouvrir.

    Le cas d'une session SSH, d'un tmux sans DISPLAY, d'un conteneur : l'import
    passe, `Tk()` non. Sans cette exception, l'erreur remontait en TclError
    brute jusqu'a main() et emportait le daemon - le seul chemin connu par
    lequel une machine sans ecran perdait butbutbut au demarrage.
    """


def _crest(cache, url):
    """Le chemin de l'ecusson deja en cache, ou None. Ne bloque jamais.

    Un cache casse (disque plein, dossier efface sous les pieds) n'a pas a
    empecher un but de s'afficher : on rend None et la carte se passe d'image.
    """
    if cache is None or not url:
        return None
    try:
        return cache.get(url)
    except Exception:
        return None


def _import_tk():
    try:
        return overlay_window.import_tk()
    except overlay_window.TkinterMissing as exc:
        raise TkinterMissing(
            "tkinter est introuvable. Installe-le :\n"
            "  Arch/Manjaro   : sudo pacman -S tk\n"
            "  Debian/Ubuntu  : sudo apt install python3-tk\n"
            "  Fedora         : sudo dnf install python3-tkinter\n"
            "  macOS (brew)   : brew install python-tk\n"
            "  Windows        : reinstalle Python en cochant 'tcl/tk'"
        ) from exc


# ----------------------------------------------------------------- carte -----

class Card:
    """Le contenu a afficher, independamment de tkinter."""

    __slots__ = ("title", "league", "minute", "home", "away", "home_score",
                 "away_score", "side", "parts", "accent", "title_color",
                 "extra", "team_accent", "home_logo", "away_logo",
                 "home_reds", "away_reds", "celebration", "motif",
                 "motif_path", "match_intro", "home_motif_path",
                 "away_motif_path", "moment", "focus_side")

    def __init__(self, title, league, minute, home, away, home_score, away_score,
                 side, detail, accent, title_color=None, extra=(),
                 team_accent=None, home_logo=None, away_logo=None,
                 home_reds=0, away_reds=0, celebration="", motif="",
                 motif_path=None, match_intro="", home_motif_path=None,
                 away_motif_path=None, moment="", focus_side=None):
        self.title = title              # "BUT !", "MI-TEMPS"...
        self.league = league            # "LIGUE 1"
        self.minute = minute            # "35'"
        self.home = home
        self.away = away
        self.home_score = home_score
        self.away_score = away_score
        self.side = side                # "home", "away" ou None
        self.parts = tuple(detail)      # [(texte, mis_en_valeur)] : le buteur
        # Les lignes qui suivent, decoupees pareil : les buteurs, a la fin du
        # match. Vide pour toutes les autres cartes.
        self.extra = tuple(tuple(line) for line in extra)
        self.accent = accent            # filet vertical, aux couleurs de la competition
        # Le titre : la couleur du championnat pour un but, gris pour une carte
        # de deroulement. Un but doit sauter aux yeux, une mi-temps non.
        self.title_color = title_color or accent
        # L'equipe qui marque : la couleur de son club, quand elle se lit sur
        # le fond de la carte. Le filet, lui, ne bouge pas : il dit toujours
        # dans quelle competition on est.
        self.team_accent = team_accent or accent
        # Chemins de PNG deja en cache, ou None : une carte n'attend jamais un
        # telechargement, elle se passe de l'ecusson qui n'est pas encore la.
        self.home_logo = home_logo
        self.away_logo = away_logo
        # Les expulsions de chaque camp, en nombre. Zero partout ou le sport
        # n'a pas de carton rouge, et zero par defaut : une carte fabriquee a
        # la main - un test, un appelant d'avant cette version - ne dessine
        # aucun carton et reste exactement la carte qu'elle etait.
        self.home_reds = int(home_reds or 0)
        self.away_reds = int(away_reds or 0)
        # Vide sur toutes les cartes sauf un vrai but de football. La chaine
        # est deja localisee au moment ou la carte est construite.
        self.celebration = str(celebration or "")
        # Une cle dans l'atlas de cartes postales. Vide reste accepte pour les
        # integrations et les anciennes cartes construites a la main.
        self.motif = str(motif or "")
        self.motif_path = motif_path
        # Le rituel d'avant-match et le generique final ouvrent sur un
        # face-a-face. Les chemins restent locaux et optionnels : une ligue
        # sans illustration garde la meme animation avec noms et ecussons.
        self.match_intro = str(match_intro or "")
        self.home_motif_path = home_motif_path
        self.away_motif_path = away_motif_path
        self.moment = str(moment or "")
        self.focus_side = focus_side if focus_side in ("home", "away") else None

    @property
    def detail(self) -> str:
        """La troisieme ligne d'un bloc, sans mise en forme."""
        return "".join(text for text, _ in self.parts)

    @classmethod
    def from_event(cls, event, crest=None):
        """Construit la carte a partir d'un evenement du watcher.

        `crest` : un crests.Cache, ou None pour une carte sans ecusson. Il
        n'est interroge que sur le disque - le reseau, si besoin, part derriere.
        """
        accent = event.league.accent
        title_color = accent
        team_accent = accent
        reds = event.match.red_card_tally()
        motif = themes.match_motif(event.match)
        themed_id = (event.match.away_id if event.side == "away"
                     else event.match.home_id)
        motif_path = themes.club_asset(themed_id)
        match_intro = (event.kind if event.kind in ("prematch", "kickoff",
                                                     "fulltime")
                       else "")

        if event.sober:
            # Temps forts, expulsion, avant-match : rien de tout ca ne doit
            # sauter aux yeux comme un but.
            title_color = MUTED
            if event.kind == "red_card":
                title_color = RED_CARD
        elif not event.goal:
            accent = title_color = team_accent = CANCEL_ACCENT   # but annule
        else:
            color, alternate = event.colors
            team_accent = crests.pick_accent(color, alternate, accent, CARD_BG)

        return cls(
            title=event.title,
            league=event.league.label,
            minute=event.minute,
            home=event.match.home,
            away=event.match.away,
            home_score=event.home_score,
            away_score=event.away_score,
            # Aucune equipe n'est mise en couleur sur une carte discrete : sur
            # un carton rouge, ca ressemblerait a une bonne nouvelle.
            side=None if event.sober else event.side,
            detail=event.detail_parts(),
            accent=accent,
            title_color=title_color,
            # Le contexte est une ligne de carte, pas une nouvelle nature de
            # but : le titre garde « BUT SUR PENALTY », le journal garde sa
            # grammaire stable, et « EGALISATION » vient juste en dessous.
            extra=event.context_parts() + event.extra_parts(),
            team_accent=team_accent,
            home_logo=_crest(crest, event.match.home_logo),
            away_logo=_crest(crest, event.match.away_logo),
            # Toutes les expulsions du match, pas seulement celle qui a
            # declenche la carte : une carte de but qui montre le carton pris
            # dix minutes plus tot explique le but.
            home_reds=reds[0],
            away_reds=reds[1],
            celebration=(leagues.goal_celebration(event.league)
                         if event.goal and event.sport is sports.SOCCER else ""),
            motif=motif,
            motif_path=motif_path,
            match_intro=match_intro,
            home_motif_path=(themes.club_asset(event.match.home_id)
                             if match_intro else None),
            away_motif_path=(themes.club_asset(event.match.away_id)
                             if match_intro else None),
            moment=event.kind,
            focus_side=event.side,
        )

    @classmethod
    def demo(cls, league=None, crest=None):
        """Une carte d'exemple, pour `butbutbut --test`."""
        from . import espn
        from .leagues import LEAGUES

        league = league or LEAGUES[0]
        sport = league.sport
        # Une competition de football sans exemple a elle emprunte celui de la
        # Ligue 1 ; un autre sport prend l'exemple de son sport, sans quoi une
        # carte de NHL montrerait Angers contre Rennes.
        sample = (DEMO.get(league.slug)
                  or DEMO_BY_SPORT.get(sport.code)
                  or DEMO["fra.1"])
        home, away = sample["home"], sample["away"]
        scoring = home if sample["side"] == "home" else away

        return cls(
            title=i18n.text(sample.get("title", "title_goal")),
            league=league.label,
            minute=sample["minute"],
            home=home[0],
            away=away[0],
            home_score=sample["score"][0],
            away_score=sample["score"][1],
            side=sample["side"],
            detail=[(i18n.text(sample.get("by", "goal_by")), False),
                    (sample["scorer"], True)],
            accent=league.accent,
            team_accent=crests.pick_accent(scoring[2], scoring[3],
                                           league.accent, CARD_BG),
            home_logo=_crest(crest, espn.logo_url(home[1], sport)),
            away_logo=_crest(crest, espn.logo_url(away[1], sport)),
            home_reds=sample.get("reds", (0, 0))[0],
            away_reds=sample.get("reds", (0, 0))[1],
            celebration=(leagues.goal_celebration(league)
                         if sport is sports.SOCCER else ""),
            motif=themes.league_motif(league),
            motif_path=themes.club_asset(scoring[1]),
            moment="goal",
            focus_side=sample["side"],
        )

    @classmethod
    def pinned(cls, match, ended=False, crest=None):
        """La carte epinglee d'un match, refaite a chaque releve.

        Elle part d'un `espn.Match` et non d'un evenement : elle ne raconte pas
        ce qui vient d'arriver, elle montre ou en est le match. D'ou une carte
        sans troisieme ligne - le score et la minute suffisent - et sans aucune
        equipe en couleur : partout ailleurs la couleur d'un club veut dire
        "c'est elle qui vient de marquer", la reutiliser pour dire "c'est elle
        qui mene" serait un contresens a l'echelle d'une soiree.

        Le ton est celui des temps forts (titre gris), qui est aussi la marque
        des cartes muettes : rien ici ne declenche de son.
        """
        league = match.league
        reds = match.red_card_tally()
        return cls(
            title=i18n.text("title_fulltime" if ended else "title_pinned"),
            league=league.label,
            minute=match.clock or match.detail or "",
            home=match.home,
            away=match.away,
            home_score=match.home_score,
            away_score=match.away_score,
            side=None,
            detail=[],
            accent=league.accent,
            title_color=MUTED,
            home_logo=_crest(crest, match.home_logo),
            away_logo=_crest(crest, match.away_logo),
            home_reds=reds[0],
            away_reds=reds[1],
            motif=themes.match_motif(match),
            motif_path=themes.club_asset(match.home_id),
        )

    @classmethod
    def demo_pinned(cls, league=None, crest=None):
        """Une carte epinglee d'exemple, pour `butbutbut --test --pin`.

        Sans elle, personne ne pourrait regler la taille, le coin ni l'ecran
        d'une carte qu'on n'obtient autrement qu'en attendant un vrai match.
        """
        from . import espn
        from .leagues import LEAGUES

        league = league or LEAGUES[0]
        sample = DEMO.get(league.slug, DEMO["fra.1"])
        home, away = sample["home"], sample["away"]

        return cls(
            title=i18n.text("title_pinned"),
            league=league.label,
            minute=sample["minute"],
            home=home[0],
            away=away[0],
            home_score=sample["score"][0],
            away_score=sample["score"][1],
            side=None,
            detail=[],
            accent=league.accent,
            title_color=MUTED,
            home_logo=_crest(crest, espn.logo_url(home[1])),
            away_logo=_crest(crest, espn.logo_url(away[1])),
            home_reds=sample.get("reds", (0, 0))[0],
            away_reds=sample.get("reds", (0, 0))[1],
            motif=themes.league_motif(league),
            motif_path=themes.club_asset(home[1]),
        )

    def text_line(self) -> str:
        return "{} {} - {} {}".format(self.home, self.home_score,
                                      self.away_score, self.away)


# ----------------------------------------------------------------- dessin ----

def _pick_font(tkfont, families_wanted, size, weight="normal"):
    families = set(tkfont.families())
    for name in families_wanted:
        if name in families:
            return tkfont.Font(family=name, size=size, weight=weight)
    return tkfont.Font(size=size, weight=weight)


def _team_points(scale) -> int:
    """Taille en points de la ligne d'equipe, la mesure dont tout depend.

    Elle vit dans sa propre fonction parce que `crest_size` doit la retrouver
    sans tkinter : deux ecritures du meme calcul auraient fini par diverger, et
    la divergence se serait vue en ecussons flous.
    """
    return max(10, int(16 * max(0.1, float(scale or 1.0))))


def _fonts(tkfont, scale: float):
    wanted = FONT_CANDIDATES.get(sys.platform, LINUX_FONTS)
    return {
        "label": _pick_font(tkfont, wanted, max(7, int(9 * scale)), "bold"),
        "title": _pick_font(tkfont, wanted, max(8, int(11 * scale)), "bold"),
        "team": _pick_font(tkfont, wanted, _team_points(scale), "bold"),
        "score": _pick_font(tkfont, wanted, max(12, int(22 * scale)), "bold"),
        "detail": _pick_font(tkfont, wanted, max(8, int(11 * scale)), "normal"),
        "scorer": _pick_font(tkfont, wanted, max(8, int(12 * scale)), "bold"),
    }


def _detail_font(fonts, strong):
    return fonts["scorer"] if strong else fonts["detail"]


def _logo_size(fonts) -> int:
    """Cote de l'ecusson : cale sur la ligne d'equipe, il suit donc --scale."""
    return int(fonts["team"].metrics("linespace") * LOGO_RATIO)


# Hauteur de ligne d'une police, en multiples de sa taille en points. Majoree
# expres : voir `crest_size`.
LINESPACE_RATIO = 1.8


def crest_size(scale: float = 1.0) -> int:
    """Le cote, en pixels, auquel une carte a `scale` affichera un ecusson.

    `_logo_size` mesure la vraie police, mais il lui faut une racine tkinter
    ouverte - or le cache d'ecussons doit connaitre la taille AVANT elle :
    --test telecharge ses ecussons avant meme qu'une fenetre existe. On refait
    donc le calcul a partir de --scale seul, en majorant la hauteur de ligne
    parce qu'une taille sous-estimee floute l'ecusson alors qu'une taille
    surestimee ne coute que des octets.

    Approcher suffit : `crests.fit_size` arrondit ensuite sur trois barreaux,
    et il faudrait se tromper du simple au double pour changer de barreau.
    """
    return int(_team_points(scale) * LINESPACE_RATIO * LOGO_RATIO)


def _red_size(fonts) -> tuple:
    """(largeur, hauteur) d'un carton rouge, calees sur la ligne d'equipe.

    Au moins 3 pixels de cote : sur une carte reduite a l'extreme, un carton
    d'un pixel disparaitrait dans le fond au lieu de dire qu'il manque un
    joueur.
    """
    height = max(3, int(fonts["team"].metrics("linespace") * RED_RATIO))
    return (max(3, int(height * RED_ASPECT)), height)


def _red_span(width: int, count: int) -> int:
    """La place que prennent `count` cartons cote a cote. Zero pour aucun."""
    return count * (width + RED_GAP) - RED_GAP if count else 0


def stack_positions(monitor, sizes, position="bottom-right", gap=STACK_GAP):
    """Ou poser chaque carte d'une pile, de la plus recente a la plus ancienne.

    `sizes` : [(largeur, hauteur)] dans l'ordre d'affichage, la premiere collee
    au coin. Depuis un coin du bas la pile monte, depuis le haut elle descend.
    """
    position = (position or "bottom-right").strip().lower()
    downwards = position.startswith("top") or position == "center"

    places = []
    offset = 0
    for width, height in sizes:
        x, y = monitor.place(width, height, position)
        y = y + offset if downwards else y - offset
        y = max(monitor.y, min(y, monitor.y + monitor.height - height))
        places.append((x, y))
        offset += height + gap
    return places


def layout_stack(monitor, pinned_size, sizes, position="bottom-right",
                 gap=STACK_GAP):
    """Ou poser la carte epinglee et chacune des cartes fugaces.

    Rend ((x, y) de l'epinglee ou None, [(x, y)] des fugaces). L'epinglee est
    simplement la premiere de la pile : elle prend le coin, les fugaces
    commencent apres elle. Une seule fonction pour les deux, sinon les deux
    calculs finiraient par diverger et une carte de but se poserait sur elle.

    `pinned_size` : (largeur, hauteur), ou None quand rien n'est epingle - et
    dans ce cas les fugaces retrouvent exactement les places d'avant.
    """
    sizes = list(sizes)
    if pinned_size is None:
        return None, stack_positions(monitor, sizes, position, gap)
    places = stack_positions(monitor, [tuple(pinned_size)] + sizes, position, gap)
    return places[0], places[1:]


def _rounded(canvas, x0, y0, x1, y1, radius, **options):
    """Rectangle a coins arrondis, avec les seuls outils du Canvas."""
    radius = max(0, min(radius, int((x1 - x0) / 2), int((y1 - y0) / 2)))
    points = [
        x0 + radius, y0, x1 - radius, y0, x1, y0, x1, y0 + radius,
        x1, y1 - radius, x1, y1, x1 - radius, y1, x0 + radius, y1,
        x0, y1, x0, y1 - radius, x0, y0 + radius, x0, y0,
    ]
    return canvas.create_polygon(points, smooth=True, **options)


def _crisp_rounded(canvas, x0, y0, x1, y1, radius, **options):
    """Petit rectangle arrondi aux segments droits, sans spline Tk."""
    x0, y0, x1, y1 = map(int, (x0, y0, x1, y1))
    radius = max(0, min(int(radius), (x1 - x0) // 2, (y1 - y0) // 2))
    points = []
    for cx, cy, start in (
            (x0 + radius, y0 + radius, 180),
            (x1 - radius, y0 + radius, 270),
            (x1 - radius, y1 - radius, 0),
            (x0 + radius, y1 - radius, 90)):
        for angle in range(start, start + 91, 15):
            radians = math.radians(angle)
            points.extend((round(cx + radius * math.cos(radians)),
                           round(cy + radius * math.sin(radians))))
    return canvas.create_polygon(tuple(points), smooth=False, **options)


def _fit(font, text: str, limit: float) -> str:
    """Raccourcit `text` avec des points de suspension pour tenir en `limit`."""
    if not text or font.measure(text) <= limit:
        return text
    trimmed = text
    while trimmed and font.measure(trimmed + "...") > limit:
        trimmed = trimmed[:-1]
    trimmed = trimmed.rstrip()
    return (trimmed + "...") if trimmed else text[:1]


def _fit_parts(fonts, parts, limit: float) -> list:
    """Raccourcit une ligne en morceaux pour qu'elle tienne dans `limit`.

    Les morceaux entiers sont gardes tant qu'ils rentrent, celui qui deborde
    est coupe, et la suite est abandonnee : une liste de buteurs qui grandit ne
    doit jamais pousser du texte hors de la carte.
    """
    fitted = []
    room = float(limit)
    for text, strong in parts:
        font = _detail_font(fonts, strong)
        width = font.measure(text)
        if width <= room:
            fitted.append((text, strong))
            room -= width
            continue
        shortened = _fit(font, text, room)
        # `_fit` rend au moins un caractere : s'il ne rentre toujours pas, ce
        # morceau saute plutot que de mordre sur le bord.
        if shortened and font.measure(shortened) <= room:
            fitted.append((shortened, strong))
        break
    return fitted


def _goal_band_height(fonts) -> int:
    """Hauteur du ruban de cri, adaptee a la police et non a la carte."""
    return max(44, fonts["score"].metrics("linespace") + 14)


def _moment_footer_height(fonts) -> int:
    """Hauteur necessaire aux noms d'equipes dans le pied de carte."""
    content_h = max(fonts["team"].metrics("linespace"),
                    fonts["label"].metrics("linespace"))
    return max(28, content_h + 10)


def _moment_min_height(fonts) -> int:
    """Gabarit qui garantit des boites de texte disjointes a toute echelle."""
    rows = (fonts["title"].metrics("linespace")
            + fonts["score"].metrics("linespace")
            + fonts["scorer"].metrics("linespace"))
    return (_goal_band_height(fonts) + rows + 4 * 10
            + _moment_footer_height(fonts))


def _layout(card: Card, fonts):
    """Mesure la carte : largeur, hauteur et abscisse de chaque morceau.

    Le score est centre dans la carte. La place reservee aux noms d'equipes est
    donc la MEME de chaque cote, sinon le nom le plus long sort de la carte :
    c'est exactement ce qui arrivait a "Eintracht Frankfurt 1 - 4 FC Augsburg",
    ou le nom de gauche depassait le bord.

    Les ecussons entrent dans cette reserve au lieu de la contourner : dans la
    demi-largeur reservee a chaque equipe, l'ecusson passe a l'exterieur du nom.
    Et il est reserve des qu'UNE des deux equipes en a un, sinon le score se
    decalerait selon les ecussons deja telecharges.
    """
    if card.match_intro:
        return _match_intro_layout(card, fonts)

    # Le score est decoupe en trois pour pouvoir colorer le seul chiffre qui
    # vient de bouger.
    score_parts = (str(card.home_score), " - ", str(card.away_score))
    score_widths = [fonts["score"].measure(part) for part in score_parts]
    score_w = sum(score_widths)

    margins = BAR_WIDTH + 2 * PAD_X
    home, away = card.home, card.away
    half = max(fonts["team"].measure(home), fonts["team"].measure(away))

    logo = _logo_size(fonts) if (card.home_logo or card.away_logo) else 0
    slot = (logo + LOGO_GAP) if logo else 0

    # Les cartons se rangent entre le nom et le score, du cote du chiffre de
    # leur equipe. Leur place est reservee des DEUX cotes, sur le camp le plus
    # sanctionne : le score reste ainsi au centre de la carte, alors qu'une
    # reserve par camp le decalerait a chaque expulsion.
    reds = max(card.home_reds, card.away_reds)
    red_w, red_h = _red_size(fonts) if reds else (0, 0)
    red_slot = (_red_span(red_w, reds) + RED_NAME_GAP) if reds else 0

    middle_w = 2 * (half + slot + red_slot) + 2 * GAP + score_w
    header_w = (fonts["title"].measure(card.title) + 18
                + fonts["label"].measure(card.league) + 18
                + fonts["label"].measure(card.minute))
    detail_w = sum(_detail_font(fonts, strong).measure(text)
                   for text, strong in card.parts)

    extra = [list(line) for line in card.extra[:MAX_EXTRA_LINES] if line]
    extra_w = max([sum(_detail_font(fonts, strong).measure(text)
                       for text, strong in line) for line in extra] or [0])

    content_w = max(middle_w, header_w, detail_w, extra_w)
    min_width = (MOMENT_MIN_WIDTH
                 if card.moment in ("goal", "red_card") else MIN_WIDTH)
    width = int(min(MAX_WIDTH, max(min_width, content_w + margins)))

    # Une liste de buteurs n'a pas de longueur maximale : elle est coupee sur
    # la largeur reelle de la carte, comme les noms d'equipes juste apres.
    extra = [_fit_parts(fonts, line, width - margins) for line in extra]
    extra = [line for line in extra if line]

    # Plafond atteint (des noms a rallonge) : on raccourcit plutot que de
    # deborder. La carte reste dans ses bords, quoi qu'on lui donne.
    room = max(20.0,
               (width - margins - score_w - 2 * GAP) / 2.0 - slot - red_slot)
    if half > room:
        home = _fit(fonts["team"], home, room)
        away = _fit(fonts["team"], away, room)

    center = BAR_WIDTH + (width - BAR_WIDTH) / 2.0
    score_left = center - score_w / 2.0

    # Les cartons sont colles au score, pas au nom : un camp qui en a un et
    # l'autre deux gardent ainsi leurs cartons alignes sur la meme colonne, et
    # chacun contre le chiffre qui le concerne.
    home_x = score_left - GAP - red_slot
    away_x = score_left + score_w + GAP + red_slot

    header_h = max(fonts["title"].metrics("linespace"), fonts["label"].metrics("linespace"))
    score_h = max(fonts["team"].metrics("linespace"),
                  fonts["score"].metrics("linespace"), logo, red_h)
    detail_h = max(fonts["detail"].metrics("linespace"),
                   fonts["scorer"].metrics("linespace")) if card.parts else 0

    extra_h = max(fonts["detail"].metrics("linespace"),
                  fonts["scorer"].metrics("linespace")) if extra else 0

    # Le bas du bloc de base : les lignes supplementaires se posent dessous.
    bottom = (PAD_Y + header_h + LINE_GAP + score_h
              + ((LINE_GAP - 2 + detail_h) if card.parts else 0))
    extra_y = [bottom + EXTRA_GAP + index * (EXTRA_GAP + extra_h) + extra_h / 2.0
               for index in range(len(extra))]

    natural_height = int(bottom + PAD_Y + len(extra) * (EXTRA_GAP + extra_h))
    # But et rouge gardent le meme cadre. Les quelques pixels en plus donnent
    # au cri une ligne superieure DANS la carte, sans recouvrir le score.
    body_height = (max(174, natural_height, _moment_min_height(fonts))
                   if card.moment in ("goal", "red_card")
                   else natural_height)
    body_shift = (body_height - natural_height) / 2.0
    moment_top = 0
    height = body_height

    return {
        "width": width,
        "height": height,
        "extra": extra,
        "extra_y": [y + body_shift for y in extra_y],
        "moment_top": moment_top,
        "body_height": body_height,
        "left": BAR_WIDTH + PAD_X,
        "right": width - PAD_X,
        "home": home,
        "away": away,
        "home_x": home_x,                            # ancre "e"
        "away_x": away_x,                            # ancre "w"
        "logo": logo,                                # cote de l'ecusson, 0 = aucun
        "moment_logo": (max(36, int(
            fonts["team"].metrics("linespace") * 2.0))
            if card.moment in ("goal", "red_card") and logo else logo),
        "home_logo_x": home_x - fonts["team"].measure(home) - LOGO_GAP,
        "away_logo_x": away_x + fonts["team"].measure(away) + LOGO_GAP,
        "red_w": red_w,                              # 0 = aucune expulsion
        "red_h": red_h,
        "home_reds_x": score_left - GAP - _red_span(red_w, card.home_reds),
        "away_reds_x": score_left + score_w + GAP,
        "score_x": score_left,
        "score_parts": score_parts,
        "score_widths": score_widths,
        "score_w": score_w,
        "header_y": body_shift + PAD_Y + header_h / 2.0,
        "score_y": (body_shift + PAD_Y + header_h + LINE_GAP
                    + score_h / 2.0),
        "detail_y": (body_shift + PAD_Y + header_h + LINE_GAP + score_h
                     + (LINE_GAP - 2) + detail_h / 2.0),
    }


def _match_intro_layout(card: Card, fonts):
    """Composition ample du rituel d'avant-match et du generique final."""
    header_h = max(fonts["title"].metrics("linespace"),
                   fonts["label"].metrics("linespace"))
    team_h = fonts["team"].metrics("linespace")
    detail_h = max(fonts["detail"].metrics("linespace"),
                   fonts["scorer"].metrics("linespace")) if card.parts else 0
    scene_size = max(92, int(team_h * 5.5))
    crest_size = max(30, int(team_h * 1.8))

    header_w = (fonts["title"].measure(card.title) + 24
                + fonts["label"].measure(card.league) + 18
                + fonts["label"].measure(card.minute))
    teams_w = 2 * max(fonts["team"].measure(card.home),
                      fonts["team"].measure(card.away)) + 150
    width = int(min(MAX_WIDTH, max(MATCH_INTRO_MIN_WIDTH,
                                   header_w + 2 * PAD_X + BAR_WIDTH,
                                   teams_w + 2 * PAD_X + BAR_WIDTH)))

    room = max(60.0, width * 0.34)
    home = _fit(fonts["team"], card.home, room)
    away = _fit(fonts["team"], card.away, room)
    extra = [list(line) for line in card.extra[:MAX_EXTRA_LINES] if line]
    extra = [_fit_parts(fonts, line, width - BAR_WIDTH - 2 * PAD_X)
             for line in extra]
    extra = [line for line in extra if line]
    parts = _fit_parts(fonts, list(card.parts),
                       width - BAR_WIDTH - 2 * PAD_X)
    extra_h = max(fonts["detail"].metrics("linespace"),
                  fonts["scorer"].metrics("linespace")) if extra else 0

    header_y = PAD_Y + header_h / 2.0
    scene_top = PAD_Y + header_h + LINE_GAP
    scene_y = scene_top + scene_size / 2.0
    team_y = scene_top + scene_size + 2 + team_h / 2.0
    detail_y = team_y + team_h / 2.0 + LINE_GAP + detail_h / 2.0
    bottom = (detail_y + detail_h / 2.0 if detail_h
              else team_y + team_h / 2.0)
    extra_y = [bottom + EXTRA_GAP + index * (EXTRA_GAP + extra_h)
               + extra_h / 2.0 for index in range(len(extra))]
    height = int(bottom + PAD_Y + len(extra) * (EXTRA_GAP + extra_h))

    return {
        "width": width,
        "height": height,
        "left": BAR_WIDTH + PAD_X,
        "right": width - PAD_X,
        "header_y": header_y,
        "scene_size": scene_size,
        "crest_size": crest_size,
        "fallback_logo": max(crest_size, int(scene_size * 0.62)),
        "badge_size": max(48, int(scene_size * 0.46)),
        "scene_y": scene_y,
        "home_scene_x": width * 0.24,
        "away_scene_x": width * 0.76,
        "home_crest_x": round(width * 0.24 - scene_size * 0.38),
        "away_crest_x": round(width * 0.76 + scene_size * 0.38),
        "crest_y": round(scene_y + scene_size * 0.24),
        "center_x": width / 2.0,
        "team_y": team_y,
        "home": home,
        "away": away,
        "detail_y": detail_y,
        "parts": parts,
        "extra": extra,
        "extra_y": extra_y,
        # Les ecussons prennent le relais si une illustration manque. Sur ces
        # deux cartes ils ont droit a une vraie presence, pas au petit format
        # de la ligne de score ordinaire.
        "logo": crest_size,
    }


def load_logos(tk, card: Card, box, master=None) -> dict:
    """Les ecussons de la carte, deja mis a la taille reservee par _layout.

    Rendus dans un dictionnaire que l'appelant doit GARDER : tkinter oublie une
    image que plus rien ne reference, et elle disparait de l'ecran. Avec des
    cartes empilees, chacune tient donc les siennes.
    """
    found = {}
    size = box.get("moment_logo", box.get("logo", 0))
    if not size:
        return found
    for key, path in (("home", card.home_logo), ("away", card.away_logo)):
        if path is None:
            continue
        image = crests.photo(tk, path, size, master=master)
        if image is not None:
            found[key] = image
    return found


def load_motif(tk, card: Card, box, master=None, atlas=None, cache=None) -> dict:
    """Decoupe le filigrane du pays dans l'atlas, sans Pillow ni reseau.

    Tk sait copier une zone d'un ``PhotoImage``. Le fichier reste donc unique
    dans le paquet — la garantie concrete que les vingt dessins partagent le
    meme traitement — et une carte ne garde en memoire que sa petite vignette.
    Une version ancienne de Tk ou un PNG illisible retire simplement le decor :
    le score, lui, doit toujours s'afficher.
    """
    if not card.motif and not card.motif_path:
        return {}
    try:
        if card.motif_path:
            source = tk.PhotoImage(file=str(card.motif_path), master=master)
            target = max(48, int(box.get("body_height", box["height"]) * 0.78))
            factor = max(1, int(math.ceil(source.height() / float(target))))
            key = ("club", str(card.motif_path), factor)
            sprite = (cache or {}).get(key)
            if sprite is None:
                sprite = source.subsample(factor, factor) if factor > 1 else source
                if cache is not None:
                    cache[key] = sprite
            return {"motif": sprite, "motif_source": source}

        atlas = atlas or tk.PhotoImage(file=str(COUNTRY_ATLAS), master=master)
        width, height = atlas.width(), atlas.height()
        x0, y0, x1, y1 = themes.atlas_box(card.motif, width, height)
        # Le motif occupe environ les trois quarts de la hauteur et reste un
        # filigrane, jamais une quatrieme ligne a lire.
        target = max(48, int(box.get("body_height", box["height"]) * 0.78))
        factor = max(1, int(math.ceil((y1 - y0) / float(target))))
        key = (card.motif, factor)
        sprite = (cache or {}).get(key)
        if sprite is None:
            sprite = tk.PhotoImage(width=x1 - x0, height=y1 - y0,
                                   master=master)
            sprite.tk.call(sprite, "copy", atlas, "-from", x0, y0, x1, y1,
                           "-to", 0, 0)
            if factor > 1:
                sprite = sprite.subsample(factor, factor)
            if cache is not None:
                cache[key] = sprite
        return {"motif": sprite, "motif_atlas": atlas}
    except Exception:
        return {}


def load_match_intro(tk, card: Card, box, master=None, cache=None) -> dict:
    """Charge les deux illustrations du face-a-face, sans aucun reseau.

    Les PNG de club sont volontairement plus grands que leur rendu dans une
    carte. Tk sait les reduire par facteur entier : c'est moins souple que
    Pillow, mais instantane, disponible partout et suffisant pour une intro
    qui ne dure qu'une seconde. Les ecussons deja charges restent le repli.
    """
    if not card.match_intro:
        return {}

    target = int(box.get(
        "scene_size",
        max(56, min(box["height"] * 0.82, box["width"] * 0.34))))
    found = {}
    for side, path in (("home", card.home_motif_path),
                       ("away", card.away_motif_path)):
        if path is None:
            continue
        try:
            source = tk.PhotoImage(file=str(path), master=master)
            factor = max(1, int(math.ceil(
                max(source.width(), source.height()) / float(target))))
            key = ("match-intro", str(path), factor)
            sprite = (cache or {}).get(key)
            if sprite is None:
                sprite = source.subsample(factor, factor) if factor > 1 else source
                if cache is not None:
                    cache[key] = sprite
            found[side + "_scene"] = sprite
            # Quand le facteur vaut un, le sprite EST la source. La reference
            # explicite rend aussi ce contrat evident pour les Tk plus anciens.
            found[side + "_scene_source"] = source
        except Exception:
            continue
    return found


def load_match_crests(tk, card: Card, box, scenes=None, master=None) -> dict:
    """Charge les ecussons en medaillon, ou en grand si le decor manque."""
    found = {}
    scenes = scenes or {}
    for side, path in (("home", card.home_logo), ("away", card.away_logo)):
        if path is None:
            continue
        has_scene = scenes.get(side + "_scene") is not None
        size = box["crest_size"] if has_scene else box["fallback_logo"]
        image = crests.photo(tk, path, size, master=master)
        if image is not None:
            found[side + "_crest" if has_scene else side] = image
    return found


def _draw_match_badge(canvas, card: Card, fonts, box, tags=None):
    """Le badge unique partage par l'intro et par la carte revelee."""
    tagged = {"tags": tags} if tags else {}
    cx, cy = box["center_x"], box["scene_y"]
    x0, y0, x1, y1 = _duel_badge_box(cx, cy, box["badge_size"])
    _crisp_rounded(canvas, x0, y0, x1, y1,
                   max(7, box["badge_size"] // 6),
                   fill=CARD_BG, outline=card.accent, **tagged)
    center_text = ("VS" if card.match_intro == "prematch" else
                   "{} - {}".format(card.home_score, card.away_score))
    canvas.create_text(cx, cy, text=center_text, fill=card.accent,
                       font=fonts["title"], anchor="center", **tagged)


def _draw_match_shell(canvas, card: Card, fonts, box, background, tags=None):
    """Fond, en-tete et badge communs aux deux temps de l'animation."""
    tagged = {"tags": tags} if tags else {}
    width, height = box["width"], box["height"]
    canvas.create_rectangle(0, 0, width, height,
                            fill=background, outline=background, **tagged)
    _rounded(canvas, 0, 0, width - 1, height - 1, RADIUS,
             fill=CARD_BG, outline=CARD_EDGE, **tagged)

    # Deux pans obliques donnent une direction au face-a-face sans ajouter une
    # couleur de club qui pourrait etre confondue avec celle d'un buteur.
    middle = box["center_x"]
    canvas.create_polygon(
        (10, RADIUS, middle - 20, RADIUS, middle - 58, height - RADIUS,
         10, height - RADIUS), fill="#111722", outline="", **tagged)
    canvas.create_polygon(
        (middle + 20, RADIUS, width - 10, RADIUS,
         width - 10, height - RADIUS, middle + 58, height - RADIUS),
        fill="#17131d", outline="", **tagged)
    canvas.create_rectangle(3, RADIUS // 2, 3 + BAR_WIDTH,
                            height - RADIUS // 2,
                            fill=card.accent, outline=card.accent, **tagged)

    title = canvas.create_text(
        box["left"], box["header_y"], text=card.title,
        fill=TEXT, font=fonts["title"], anchor="w", **tagged)
    title_end = canvas.bbox(title)[2]
    canvas.create_text(title_end + 14, box["header_y"], text=card.league,
                       fill=MUTED, font=fonts["label"], anchor="w", **tagged)
    if card.minute:
        canvas.create_text(box["right"], box["header_y"], text=card.minute,
                           fill=MUTED, font=fonts["label"], anchor="e",
                           **tagged)
    _draw_match_badge(canvas, card, fonts, box, tags=tags)


def _draw_match_intro_card(canvas, card: Card, fonts, box, background,
                           images=None):
    """Affiche finale des deux camps, apres leur entree animee."""
    _draw_match_shell(canvas, card, fonts, box, background)

    for side in ("home", "away"):
        scene = (images or {}).get(side + "_scene")
        image = scene or (images or {}).get(side)
        if image is not None:
            canvas.create_image(box[side + "_scene_x"], box["scene_y"],
                                image=image, anchor="center")
        crest = (images or {}).get(side + "_crest")
        if scene is not None and crest is not None:
            size = box["crest_size"] + 8
            x0, y0, x1, y1 = _duel_badge_box(
                box[side + "_crest_x"], box["crest_y"], size)
            canvas.create_oval(x0, y0, x1, y1,
                               fill=CARD_BG, outline=card.accent)
            canvas.create_image(box[side + "_crest_x"], box["crest_y"],
                                image=crest, anchor="center")
        canvas.create_text(box[side + "_scene_x"], box["team_y"],
                           text=box[side], fill=TEXT, font=fonts["team"],
                           anchor="center")

    detail_width = sum(_detail_font(fonts, strong).measure(text)
                       for text, strong in box["parts"])
    x = box["center_x"] - detail_width / 2.0
    for text, strong in box["parts"]:
        font = _detail_font(fonts, strong)
        canvas.create_text(
            x, box["detail_y"], text=text,
            fill=(TEXT if strong else card.accent), font=font, anchor="w")
        x += font.measure(text)

    for line, y in zip(box["extra"], box["extra_y"]):
        x = box["left"]
        for text, strong in line:
            font = _detail_font(fonts, strong)
            canvas.create_text(x, y, text=text,
                               fill=TEXT if strong else MUTED,
                               font=font, anchor="w")
            x += font.measure(text)


def _draw(canvas, card: Card, fonts, box, background, images=None):
    if card.match_intro:
        _draw_match_intro_card(canvas, card, fonts, box, background, images)
        return

    width, height = box["width"], box["height"]
    top = box.get("moment_top", 0)

    canvas.create_rectangle(0, 0, width, height, fill=background, outline=background)
    _rounded(canvas, 0, top, width - 1, height - 1, RADIUS,
             fill=CARD_BG, outline=CARD_EDGE)
    # Carte postale en filigrane : elle est posee avant tout le texte. Sa
    # palette sombre et or fait partie du PNG ; le score reste donc au-dessus
    # et garde exactement la meme hierarchie dans tous les pays.
    motif = (images or {}).get("motif")
    if motif is not None:
        canvas.create_image(width - 9, height - 3, image=motif, anchor="se")
    # Filet vertical aux couleurs du championnat, cale dans l'arrondi.
    canvas.create_rectangle(3, top + RADIUS // 2,
                            3 + BAR_WIDTH, height - RADIUS // 2,
                            fill=card.accent, outline=card.accent)

    # --- ligne 1 : BUT ! / championnat / minute
    title = canvas.create_text(box["left"], box["header_y"], text=card.title,
                               fill=card.title_color, font=fonts["title"], anchor="w")
    title_end = canvas.bbox(title)[2]
    canvas.create_text(title_end + 14, box["header_y"], text=card.league,
                       fill=MUTED, font=fonts["label"], anchor="w")
    if card.minute:
        canvas.create_text(box["right"], box["header_y"], text=card.minute,
                           fill=MUTED, font=fonts["label"], anchor="e")

    # --- ligne 2 : [ecusson] Equipe A  score - score  Equipe B [ecusson]
    # L'equipe qui vient de marquer et son chiffre passent a la couleur de son
    # club (crests.pick_accent l'a deja jugee lisible).
    home_color = card.team_accent if card.side == "home" else TEXT
    away_color = card.team_accent if card.side == "away" else TEXT

    for key, anchor in (("home", "e"), ("away", "w")):
        image = (images or {}).get(key)
        if image is not None:
            canvas.create_image(box[key + "_logo_x"], box["score_y"],
                                image=image, anchor=anchor)

    canvas.create_text(box["home_x"], box["score_y"], text=box["home"],
                       fill=home_color, font=fonts["team"], anchor="e")

    x = box["score_x"]
    for part, part_width, color in zip(box["score_parts"], box["score_widths"],
                                       (home_color, MUTED, away_color)):
        canvas.create_text(x, box["score_y"], text=part, fill=color,
                           font=fonts["score"], anchor="w")
        x += part_width

    canvas.create_text(box["away_x"], box["score_y"], text=box["away"],
                       fill=away_color, font=fonts["team"], anchor="w")

    # Les expulsions : un rectangle rouge par carton, contre le chiffre de
    # l'equipe qui l'a pris. Rouge plein, quelle que soit la carte - c'est la
    # seule couleur de la carte qui ne veut jamais dire autre chose.
    for count, x0 in ((card.home_reds, box["home_reds_x"]),
                      (card.away_reds, box["away_reds_x"])):
        top = box["score_y"] - box["red_h"] / 2.0
        for index in range(count):
            x = x0 + index * (box["red_w"] + RED_GAP)
            canvas.create_rectangle(x, top, x + box["red_w"], top + box["red_h"],
                                    fill=RED_CARD, outline=RED_CARD)

    # --- ligne 3 : le buteur, seul morceau en clair
    x = box["left"]
    for text, strong in card.parts:
        font = _detail_font(fonts, strong)
        canvas.create_text(x, box["detail_y"], text=text,
                           fill=TEXT if strong else MUTED, font=font, anchor="w")
        x += font.measure(text)

    # --- lignes suivantes : les buteurs, a la fin du match
    for line, y in zip(box["extra"], box["extra_y"]):
        x = box["left"]
        for text, strong in line:
            font = _detail_font(fonts, strong)
            canvas.create_text(x, y, text=text,
                               fill=TEXT if strong else MUTED, font=font,
                               anchor="w")
            x += font.measure(text)


# ------------------------------------------------------------------ pile -----

def _smoothstep(frame: int, entering: int) -> float:
    """Progression a vitesse nulle aux deux extremites."""
    progress = max(0.0, min(float(frame) / float(entering), 1.0))
    return progress * progress * (3.0 - 2.0 * progress)


def _moment_x(frame: int, width: float, side: str) -> float:
    """Fait entrer l'illustration du club jusqu'a son quart de carte."""
    left = side == "home"
    outside = -float(width) * 0.18 if left else float(width) * 1.18
    target = float(width) * (0.22 if left else 0.78)
    eased = _smoothstep(min(frame, MOMENT_ENTER_FRAMES), MOMENT_ENTER_FRAMES)
    return outside + (target - outside) * eased


def _red_card_y(frame: int, height: float) -> float:
    """Fait tomber le carton au centre sans rebond ni demi-pixel."""
    start = -float(height) * 0.28
    target = float(height) * 0.55
    eased = _smoothstep(min(frame, MOMENT_ENTER_FRAMES), MOMENT_ENTER_FRAMES)
    return round(start + (target - start) * eased)


def _goal_cry_x(frame: int, width: float, text_width: float,
                total_frames: int = MOMENT_FRAMES) -> float:
    """Defilement regulier du cri, du debut a la fin de la carte."""
    start = float(width) + float(text_width) / 2.0 + PAD_X
    end = -float(text_width) / 2.0 - PAD_X
    total_frames = max(1, int(total_frames))
    progress = max(0.0, min(float(frame) / total_frames, 1.0))
    return start + (end - start) * progress


def _stretch_goal_cry(text: str, font, target_width: float) -> str:
    """Allonge la plus longue voyelle repetee jusqu'a la largeur voulue."""
    text = str(text or "")
    if not text or font.measure(text) >= target_width:
        return text

    best_start = best_end = 0
    run_start = 0
    for index in range(1, len(text) + 1):
        if index < len(text) and text[index] == text[run_start]:
            continue
        if index - run_start > best_end - best_start:
            best_start, best_end = run_start, index
        run_start = index

    letter = text[best_start:best_start + 1] or "O"
    letter_width = max(1, font.measure(letter))
    missing = max(0, int(math.ceil(
        (float(target_width) - font.measure(text)) / letter_width)))
    return text[:best_end] + letter * missing + text[best_end:]


def _moment_footer_box(fonts, top: float, body_height: float) -> tuple:
    """Bandeau inferieur commun : haut, centre et hauteur."""
    height = _moment_footer_height(fonts)
    footer_top = top + body_height - height
    return footer_top, footer_top + height / 2.0, height


def _moment_team_line(card: Card, font, limit: float) -> str:
    """Les deux equipes sur une ligne, raccourcies ensemble si necessaire."""
    return _fit(font, "{}  ·  {}".format(card.home, card.away), limit)


def _goal_text_rows(fonts, top: float, body_height: float) -> dict:
    """Place les quatre lignes du but sans jamais laisser leurs boites se croiser."""
    title_h = fonts["title"].metrics("linespace")
    score_h = fonts["score"].metrics("linespace")
    player_h = fonts["scorer"].metrics("linespace")
    footer_top, _footer_y, _footer_h = _moment_footer_box(
        fonts, top, body_height)
    gap = 10
    player_y = footer_top - gap - player_h / 2.0
    score_y = (player_y - player_h / 2.0 - gap
               - score_h / 2.0)

    title_floor = top + _goal_band_height(fonts) + gap + title_h / 2.0
    title_ceiling = score_y - score_h / 2.0 - gap - title_h / 2.0
    title_y = max(title_floor,
                  min(top + body_height * 0.40, title_ceiling))
    return {
        "title": title_y,
        "score": score_y,
        "player": player_y,
        "footer_top": footer_top,
    }


def _duel_x(frame: int, width: float, side: str) -> float:
    """Abscisse d'un camp pendant l'ouverture avant-match.

    Les deux camps entrent depuis leur bord et se posent exactement la ou la
    carte finale les gardera. La symetrie est calculee ici plutot que dans le
    Canvas afin de rester exacte a toutes les tailles de carte.
    """
    frame = max(0, min(int(frame), DUEL_FRAMES))
    left = side == "home"
    outside = -float(width) * 0.18 if left else float(width) * 1.18
    target = float(width) * (0.24 if left else 0.76)

    if frame <= DUEL_ENTER_FRAMES:
        # Smoothstep part et arrive a vitesse nulle. L'ancien ease-out cubic
        # avalait 16 % du trajet des la premiere image : ce grand saut, suivi
        # de pas minuscules, donnait exactement l'impression de saccade.
        eased = _smoothstep(frame, DUEL_ENTER_FRAMES)
        return outside + (target - outside) * eased

    return target


def _duel_badge_box(center_x: float, center_y: float,
                    size: float = 48.0) -> tuple:
    """Boite carree entiere : aucun demi-pixel ne tord son contour."""
    side = max(4, int(round(size)))
    x0 = int(round(float(center_x) - side / 2.0))
    y0 = int(round(float(center_y) - side / 2.0))
    return x0, y0, x0 + side, y0 + side


class _Panel:
    """Une carte a l'ecran : sa fenetre, son canvas, sa taille.

    Le contenu passe par `_render`, appelable plusieurs fois sur la meme
    fenetre : c'est ce qui permet a la carte epinglee de changer de score sans
    disparaitre puis revenir. Une fenetre recreee a chaque releve clignoterait,
    reprendrait le dessus des autres et coincerait les ecussons.
    """

    def __init__(self, stack, card: Card):
        tk = stack.tk
        self.stack = stack
        self.card = None
        self.box = None
        self.width = 0
        self.height = 0
        self.images = {}

        self.window = tk.Toplevel(stack.root)
        self.background = overlay_window.prepare_window(
            self.window,
            transparent_key=TRANSPARENT_KEY,
            fallback_background=CARD_BG,
        )
        self.canvas = tk.Canvas(self.window, bg=self.background,
                                highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)


        self._render(card)

    def _render(self, card: Card) -> None:
        """(Re)mesure et (re)dessine la carte dans la fenetre deja ouverte."""
        self.card = card
        self.box = _layout(card, self.stack.fonts)
        self.width = self.box["width"]
        self.height = self.box["height"]

        # Les images vivent aussi longtemps que la carte : sans cette
        # reference, tkinter les ramasse et les ecussons disparaissent.
        motif_cache = getattr(self.stack, "_motif_cache", None)
        if card.match_intro:
            self.images = load_match_intro(
                self.stack.tk, card, self.box, master=self.window,
                cache=motif_cache)
            self.images.update(load_match_crests(
                self.stack.tk, card, self.box, scenes=self.images,
                master=self.window))
            decor = {}
        else:
            self.images = load_logos(self.stack.tk, card, self.box,
                                     master=self.window)
            decor = load_motif(
                self.stack.tk, card, self.box, master=self.window,
                atlas=getattr(self.stack, "_country_atlas", None),
                cache=motif_cache)
        if decor.get("motif_atlas") is not None:
            self.stack._country_atlas = decor["motif_atlas"]
        self.images.update(decor)

        self.canvas.delete("all")
        self.canvas.configure(width=self.width, height=self.height)
        _draw(self.canvas, card, self.stack.fonts, self.box, self.background,
              self.images)

    def move(self, x: int, y: int) -> None:
        try:
            overlay_window.move_window(self.window, self.width, self.height, x, y)
        except Exception:
            pass

    def reveal(self) -> None:
        """Fait apparaitre la fenetre, en fondu, et la laisse la."""
        try:
            overlay_window.show_window(self.window)
        except Exception:
            return
        self._fade(self.stack.opacity, FADE_STEPS,
                   max(10, int(FADE_IN * 1000 / FADE_STEPS)), lambda: None)

    # -- interne

    def _after(self, ms, callback):
        try:
            self.window.after(ms, callback)
        except Exception:
            pass

    def _fade(self, target, remaining, step, done):
        if not self.window.winfo_exists():
            return
        try:
            current = float(self.window.wm_attributes("-alpha"))
        except Exception:
            current = target
            remaining = 0
        if remaining <= 0:
            try:
                self.window.wm_attributes("-alpha", target)
            except Exception:
                pass
            done()
            return
        try:
            self.window.wm_attributes("-alpha", current + (target - current) / remaining)
        except Exception:
            pass
        self._after(step, lambda: self._fade(target, remaining - 1, step, done))


class _Toast(_Panel):
    """Une carte fugace : elle s'efface toute seule au bout de sa duree."""

    def __init__(self, stack, card: Card, duration: float):
        _Panel.__init__(self, stack, card)
        self.duration = max(1.0, float(duration))
        self.closing = False

    def _moment_frame(self, art, card_shapes, cry, frame, total_frames,
                      done) -> None:
        """Anime le club concerne et, pour une expulsion, le carton."""
        if not self.window.winfo_exists():
            return
        if frame >= total_frames:
            # Le cri a fini sa traversee hors champ. Seul ce calque mobile
            # disparait ; toute la composition posee reste la carte finale.
            try:
                self.canvas.delete("goal_cry")
            except Exception:
                pass
            # Cette composition EST la carte finale. La retirer ici revelait
            # brutalement l'ancien dessin place dessous : meme contenu, mais
            # toute la geometrie sautait d'un coup. On la laisse donc posee
            # jusqu'au fondu de sortie, exactement comme les camps du duel.
            done()
            return

        side = self.card.focus_side or "home"
        x = _moment_x(frame, self.width, side)
        top = self.box.get("moment_top", 0)
        body_height = self.box.get("body_height", self.height - top)
        footer_top, _footer_y, _footer_h = _moment_footer_box(
            self.stack.fonts, top, body_height)
        content_top = (top + _goal_band_height(self.stack.fonts)
                       if self.card.moment == "goal" and self.card.celebration
                       else top + RADIUS)
        art_y = (content_top + footer_top) / 2.0
        try:
            for item, x_offset, y_offset, half in art:
                item_x, item_y = x + x_offset, art_y + y_offset
                if half:
                    self.canvas.coords(
                        item, item_x - half, item_y - half,
                        item_x + half, item_y + half)
                else:
                    self.canvas.coords(item, item_x, item_y)

            card_y = top + _red_card_y(frame, body_height)
            card_x = self.width / 2.0
            for item, x0, y0, x1, y1 in card_shapes:
                self.canvas.coords(item, card_x + x0, card_y + y0,
                                   card_x + x1, card_y + y1)
            if cry is not None:
                item, text_width = cry
                self.canvas.coords(
                    item,
                    _goal_cry_x(
                        frame, self.width, text_width, total_frames),
                    top + _goal_band_height(self.stack.fonts) / 2.0,
                )
        except Exception:
            try:
                self.canvas.delete("moment_intro")
            except Exception:
                pass
            done()
            return
        self._after(
            MOMENT_FRAME_MS,
            lambda: self._moment_frame(
                art, card_shapes, cry, frame + 1, total_frames, done),
        )

    def _moment_shell(self, color) -> None:
        """Fond commun aux buts et aux rouges : meme taille, meme structure."""
        width, height = self.width, self.height
        top = self.box.get("moment_top", 0)
        body_height = self.box.get("body_height", height - top)
        # Sur un but, la diagonale commence sous le bandeau du cri. Texte et
        # fond gardent ainsi le meme contraste pendant toute la traversee ; la
        # couleur du club ne passe plus sur elle-meme au milieu d'une lettre.
        panel_top = (top + _goal_band_height(self.stack.fonts)
                     if self.card.moment == "goal" and self.card.celebration
                     else top + RADIUS)
        side = self.card.focus_side or "home"
        self.canvas.create_rectangle(
            0, 0, width, height, fill=self.background,
            outline=self.background, tags="moment_intro")
        _rounded(self.canvas, 0, top, width - 1, height - 1,
                 RADIUS, fill=CARD_BG, outline=CARD_EDGE,
                 tags="moment_intro")
        if side == "home":
            panel = (9, panel_top, width * 0.46, panel_top,
                     width * 0.34, height - RADIUS, 9, height - RADIUS)
            slash = (width * 0.45, panel_top,
                     width * 0.48, panel_top,
                     width * 0.36, height - RADIUS,
                     width * 0.33, height - RADIUS)
        else:
            panel = (width * 0.54, panel_top,
                     width - 9, panel_top,
                     width - 9, height - RADIUS,
                     width * 0.66, height - RADIUS)
            slash = (width * 0.52, panel_top,
                     width * 0.55, panel_top,
                     width * 0.67, height - RADIUS,
                     width * 0.64, height - RADIUS)
        self.canvas.create_polygon(panel, fill="#131925", outline="",
                                   tags="moment_intro")
        self.canvas.create_polygon(slash, fill=color, outline="",
                                   tags="moment_intro")
        self.canvas.create_rectangle(
            3, top + RADIUS // 2, 3 + BAR_WIDTH, height - RADIUS // 2,
            fill=self.card.accent, outline=self.card.accent,
            tags="moment_intro")

    def _moment_art(self) -> list:
        """Dessine illustration et ecusson au point de depart de leur entree."""
        side = self.card.focus_side or "home"
        start_x = _moment_x(0, self.width, side)
        top = self.box.get("moment_top", 0)
        body_height = self.box.get("body_height", self.height - top)
        footer_top, _footer_y, _footer_h = _moment_footer_box(
            self.stack.fonts, top, body_height)
        content_top = (top + _goal_band_height(self.stack.fonts)
                       if self.card.moment == "goal" and self.card.celebration
                       else top + RADIUS)
        art_y = (content_top + footer_top) / 2.0
        items = []
        scene = self.images.get("motif")
        if scene is not None:
            items.append((self.canvas.create_image(
                start_x, art_y, image=scene, anchor="center",
                tags="moment_intro"), 0, 0, 0))

        crest = self.images.get(side)
        if crest is not None:
            direction = 1 if side == "home" else -1
            crest_x = direction * self.width * 0.105
            half = (self.box.get("moment_logo",
                                 self.box.get("logo", 24)) + 12) / 2.0
            crest_center = min(
                art_y + (footer_top - content_top) * 0.14,
                footer_top - half - 6)
            crest_y = crest_center - art_y
            items.append((self.canvas.create_oval(
                0, 0, 0, 0, fill=CARD_BG, outline=self.card.accent,
                width=3, tags="moment_intro"), crest_x, crest_y, half))
            items.append((self.canvas.create_image(
                0, 0, image=crest, anchor="center", tags="moment_intro"),
                crest_x, crest_y, 0))
        return items

    def _moment_footer(self) -> None:
        """Pose competition, deux equipes et minute sur un pied opaque."""
        top = self.box.get("moment_top", 0)
        body_height = self.box.get("body_height", self.height - top)
        footer_top, footer_y, _footer_h = _moment_footer_box(
            self.stack.fonts, top, body_height)

        # Deux rectangles epousent le bas arrondi sans demander de clipping :
        # toute la largeur au-dessus des coins, puis seulement leur tangente.
        self.canvas.create_rectangle(
            0, footer_top, self.width, self.height - RADIUS,
            fill=CARD_BG, outline="", tags="moment_intro")
        self.canvas.create_rectangle(
            RADIUS, self.height - RADIUS,
            self.width - RADIUS, self.height,
            fill=CARD_BG, outline="", tags="moment_intro")
        self.canvas.create_rectangle(
            PAD_X, footer_top, self.width - PAD_X, footer_top + 1,
            fill=CARD_EDGE, outline="", tags="moment_intro")

        label = self.stack.fonts["label"]
        team = self.stack.fonts["team"]
        league_w = label.measure(self.card.league)
        minute_w = label.measure(self.card.minute)
        left_edge = BAR_WIDTH + PAD_X
        names_left = left_edge + league_w + 14
        names_right = self.width - PAD_X - minute_w - 14
        names_room = max(50.0, names_right - names_left)
        names = _moment_team_line(self.card, team, names_room)

        self.canvas.create_text(
            left_edge, footer_y, text=self.card.league,
            fill=MUTED, font=label, anchor="w", tags="moment_intro")
        self.canvas.create_text(
            (names_left + names_right) / 2.0, footer_y, text=names,
            fill=TEXT, font=team, anchor="center", tags="moment_intro")
        if self.card.minute:
            self.canvas.create_text(
                self.width - PAD_X, footer_y, text=self.card.minute,
                fill=MUTED, font=label, anchor="e", tags="moment_intro")

        # Le pied opaque masque aussi l'illustration ; le filet, lui, doit
        # rester continu jusqu'au dernier pixel de la carte.
        self.canvas.create_rectangle(
            3, top + RADIUS // 2,
            3 + BAR_WIDTH, self.height - RADIUS // 2,
            fill=self.card.accent, outline=self.card.accent,
            tags="moment_intro")

    def _moment_intro(self, done, red=False, total_frames=MOMENT_FRAMES) -> None:
        """Compose l'ouverture visuelle d'un but ou d'un carton rouge."""
        try:
            color = RED_CARD if red else self.card.team_accent
            self._moment_shell(color)
            side = self.card.focus_side or "home"
            top = self.box.get("moment_top", 0)
            body_height = self.box.get("body_height", self.height - top)
            text_x = self.width * (0.71 if side == "home" else 0.29)
            text_room = self.width * 0.38
            cry = None
            if not red and self.card.celebration:
                cry_font = self.stack.fonts["score"]
                seconds = total_frames * MOMENT_FRAME_MS / 1000.0
                target_width = (self.width
                                + seconds * GOAL_CRY_PIXELS_PER_SECOND)
                cry_text = _stretch_goal_cry(
                    self.card.celebration, cry_font, target_width)
                cry_width = cry_font.measure(cry_text)
                cry = (self.canvas.create_text(
                    _goal_cry_x(
                        0, self.width, cry_width, total_frames),
                    top + _goal_band_height(self.stack.fonts) / 2.0,
                    text=cry_text, fill=color,
                    font=cry_font, anchor="center",
                    tags=("moment_intro", "goal_cry")), cry_width)
                self.canvas.create_rectangle(
                    PAD_X, top + _goal_band_height(self.stack.fonts),
                    self.width - PAD_X,
                    top + _goal_band_height(self.stack.fonts) + 1,
                    fill=CARD_EDGE, outline="", tags="moment_intro")
                # Le Canvas ne sait pas clipper un texte dans une sous-zone.
                # Ce cache remet donc la marge gauche au premier plan : le
                # ruban nait APRES le filet de competition, jamais dessus.
                band_bottom = top + _goal_band_height(self.stack.fonts)
                self.canvas.create_rectangle(
                    0, top + RADIUS, BAR_WIDTH + PAD_X, band_bottom,
                    fill=CARD_BG, outline="", tags="moment_intro")
                self.canvas.create_rectangle(
                    3, top + RADIUS // 2,
                    3 + BAR_WIDTH, self.height - RADIUS // 2,
                    fill=self.card.accent, outline=self.card.accent,
                    tags="moment_intro")
            title = _fit(self.stack.fonts["title"], self.card.title, text_room)
            player = "".join(text for text, strong in self.card.parts if strong)
            player = player or self.card.detail
            player = _fit(self.stack.fonts["scorer"], player, text_room)
            goal_rows = (None if red else _goal_text_rows(
                self.stack.fonts, top, body_height))

            self.canvas.create_text(
                text_x, (top + body_height * 0.25 if red
                         else goal_rows["title"]),
                text=title,
                fill=color, font=self.stack.fonts["title"], anchor="center",
                tags="moment_intro")
            if red:
                team = self.card.home if side == "home" else self.card.away
                team = _fit(self.stack.fonts["team"], team, text_room)
                self.canvas.create_text(
                    text_x, top + body_height * 0.48, text=team,
                    fill=TEXT, font=self.stack.fonts["team"], anchor="center",
                    tags="moment_intro")
            else:
                self.canvas.create_text(
                    text_x, goal_rows["score"],
                    text="{} - {}".format(
                        self.card.home_score, self.card.away_score),
                    fill=TEXT, font=self.stack.fonts["score"], anchor="center",
                    tags="moment_intro")
            if player:
                self.canvas.create_text(
                    text_x, (top + body_height * 0.68 if red
                             else goal_rows["player"]), text=player,
                    fill=TEXT, font=self.stack.fonts["scorer"], anchor="center",
                    tags="moment_intro")

            art = self._moment_art()
            card_shapes = []
            if red:
                card_h = min(52, max(38, int(body_height * 0.42)))
                card_w = max(24, int(card_h * RED_ASPECT))
                half_w, half_h = card_w / 2.0, card_h / 2.0
                y = top + _red_card_y(0, body_height)
                card_shapes.append((self.canvas.create_rectangle(
                    self.width / 2.0 - half_w + 3, y - half_h + 4,
                    self.width / 2.0 + half_w + 3, y + half_h + 4,
                    fill="#07090d", outline="", tags="moment_intro"),
                    -half_w + 3, -half_h + 4, half_w + 3, half_h + 4))
                card_shapes.append((self.canvas.create_rectangle(
                    self.width / 2.0 - half_w, y - half_h,
                    self.width / 2.0 + half_w, y + half_h,
                    fill=RED_CARD, outline="#ff6b70", width=2,
                    tags="moment_intro"),
                    -half_w, -half_h, half_w, half_h))
            self._moment_footer()
        except Exception:
            done()
            return
        self._moment_frame(art, card_shapes, cry, 0, total_frames, done)

    def _match_intro_frame(self, items, frame, done) -> None:
        """Anime les deux territoires en miroir, puis rend la vraie carte."""
        if not self.window.winfo_exists():
            return
        if frame >= DUEL_FRAMES:
            try:
                self.canvas.delete("match_intro")
            except Exception:
                pass
            done()
            return

        y = self.box["scene_y"]
        try:
            for side in ("home", "away"):
                x = _duel_x(frame, self.width, side)
                for item, x_offset, y_offset, half in items[side]:
                    item_x, item_y = x + x_offset, y + y_offset
                    if half:
                        self.canvas.coords(
                            item, item_x - half, item_y - half,
                            item_x + half, item_y + half)
                    else:
                        self.canvas.coords(item, item_x, item_y)

        except Exception:
            try:
                self.canvas.delete("match_intro")
            except Exception:
                pass
            done()
            return

        self._after(
            DUEL_FRAME_MS,
            lambda: self._match_intro_frame(items, frame + 1, done),
        )

    def _match_intro(self, done) -> None:
        """Pose une affiche animee des deux camps par-dessus la carte."""
        try:
            _draw_match_shell(
                self.canvas, self.card, self.stack.fonts, self.box,
                self.background, tags="match_intro")

            y = self.box["scene_y"]
            camps = {"home": [], "away": []}
            for side in ("home", "away"):
                scene = self.images.get(side + "_scene")
                image = scene or self.images.get(side)
                if image is not None:
                    camps[side].append((self.canvas.create_image(
                        _duel_x(0, self.width, side), y,
                        image=image, anchor="center", tags="match_intro"),
                        0, 0, 0))
                crest = self.images.get(side + "_crest")
                if scene is not None and crest is not None:
                    crest_x = (self.box[side + "_crest_x"]
                               - self.box[side + "_scene_x"])
                    crest_y = self.box["crest_y"] - self.box["scene_y"]
                    half = (self.box["crest_size"] + 8) / 2.0
                    camps[side].append((self.canvas.create_oval(
                        0, 0, 0, 0, fill=CARD_BG,
                        outline=self.card.accent, tags="match_intro"),
                        crest_x, crest_y, half))
                    camps[side].append((self.canvas.create_image(
                        0, 0, image=crest, anchor="center",
                        tags="match_intro"), crest_x, crest_y, 0))
                camps[side].append((self.canvas.create_text(
                    _duel_x(0, self.width, side), self.box["team_y"],
                    text=self.box[side], fill=TEXT,
                    font=self.stack.fonts["team"], anchor="center",
                    tags="match_intro"),
                    0, self.box["team_y"] - y, 0))
        except Exception:
            done()
            return

        self._match_intro_frame(camps, 0, done)

    def start(self) -> None:
        try:
            overlay_window.show_window(self.window)
        except Exception:
            return

        hold_ms = max(200, int((self.duration - FADE_IN - FADE_OUT) * 1000))
        fade_step = max(10, int(FADE_IN * 1000 / FADE_STEPS))
        if self.card.moment == "goal" or self.card.celebration:
            # Le fondu ouvre sur le club buteur, son ecusson et le nouveau
            # score. Le cri est etire pour defiler pendant toute la lecture.
            self._fade(self.stack.opacity, FADE_STEPS, fade_step, lambda: None)
            cry_ms = max(MOMENT_MS, int((self.duration - FADE_OUT) * 1000))
            cry_frames = max(
                MOMENT_FRAMES,
                int(math.ceil(cry_ms / float(MOMENT_FRAME_MS))))
            self._moment_intro(
                self.close, red=False, total_frames=cry_frames)
        elif self.card.moment == "red_card":
            self._fade(self.stack.opacity, FADE_STEPS, fade_step, lambda: None)
            self._moment_intro(
                lambda: self._after(hold_ms, self.close), red=True)
        elif self.card.match_intro:
            # Meme contrat que la celebration : l'intro s'ajoute au temps de
            # lecture, elle ne le mange pas. Le compte a rebours comme les
            # buteurs du generique restent donc aussi lisibles qu'avant.
            self._fade(self.stack.opacity, FADE_STEPS, fade_step, lambda: None)
            self._match_intro(lambda: self._after(hold_ms, self.close))
        else:
            self._fade(self.stack.opacity, FADE_STEPS, fade_step,
                       lambda: self._after(hold_ms, self.close))
        # Filet de securite : si le gestionnaire de fenetres avale les
        # animations, la carte disparait quand meme.
        intro_ms = (MOMENT_MS
                    if self.card.moment == "red_card"
                    else DUEL_MS if self.card.match_intro else 0)
        self._after(int(self.duration * 1000) + intro_ms + 3000, self.destroy)

    def close(self) -> None:
        if self.closing:
            return
        self.closing = True
        self._fade(0.0, FADE_STEPS, max(10, int(FADE_OUT * 1000 / FADE_STEPS)),
                   self.destroy)

    def destroy(self) -> None:
        self.stack._remove(self)


class _Pinned(_Panel):
    """La carte epinglee : elle apparait une fois, et se contente de changer.

    Pas de duree, pas de fondu de sortie : c'est la pile qui la retire, quand
    le match qu'elle suit a fini de vivre (voir pinned.py).
    """

    def start(self) -> None:
        self.reveal()

    def update(self, card: Card) -> None:
        """Nouveau score, nouvelle minute : on redessine, la fenetre reste."""
        self._render(card)

    def destroy(self) -> None:
        try:
            self.window.destroy()
        except Exception:
            pass


class Stack:
    """La pile de cartes : une racine tkinter, N fenetres empilees dans un coin.

    La derniere carte arrivee est collee au coin, les precedentes remontent
    (ou descendent, si le coin choisi est en haut). Quand une carte s'efface,
    les autres reprennent sa place.

    La carte epinglee, elle, est tenue a part : elle occupe le coin en
    permanence et la pile des fugaces commence apres elle. Elle n'entre pas
    dans le compte de `max_visible` - cinq buts d'affilee ne doivent pas
    pousser dehors un tableau de bord qu'on a demande expres - et `len(stack)`
    ne compte que les fugaces.
    """

    def __init__(self, screen=None, position="bottom-right", opacity=1.0,
                 scale=1.0, max_visible=MAX_VISIBLE, retry_fullscreen=0.0,
                 on_log=None):
        self.screen = screen
        self.position = (position or "bottom-right").strip().lower()
        self.opacity = max(0.05, min(1.0, float(opacity)))
        self.scale = float(scale)
        self.max_visible = max(1, int(max_visible))
        # Secondes pendant lesquelles une carte masquee par une application en
        # plein ecran attend son tour. 0 : elle ne repasse pas.
        self.retry_fullscreen = max(0.0, float(retry_fullscreen or 0.0))
        self.on_log = on_log

        self.tk = None
        self.root = None
        self.fonts = None
        self._toasts = []      # du plus recent (au coin) au plus ancien
        self._pinned = None    # la carte epinglee, ou None : elle tient le coin
        self._pending = 0      # cartes programmees mais pas encore affichees
        self._monitor = None
        # Un atlas par racine Tk, puis une petite vignette par pays/taille. La
        # carte epinglee se redessine souvent : elle ne relit jamais le PNG.
        self._country_atlas = None
        self._motif_cache = {}

    # ------------------------------------------------------------- cycle ----

    def open(self) -> "Stack":
        """Cree la racine tkinter. Leve DisplayUnavailable s'il n'y a pas d'ecran."""
        if self.root is not None:
            return self
        tk, tkfont = _import_tk()
        self.tk = tk
        try:
            self.root = tk.Tk()
        except Exception as exc:
            raise NoDisplay(
                "aucun affichage graphique ou ouvrir une carte ({}). Sous "
                "Linux, c'est ce que dit une session sans DISPLAY : un SSH, un "
                "tmux, un conteneur.".format(exc)) from exc
        self.root.withdraw()
        self.fonts = _fonts(tkfont, self.scale)
        self.refresh_monitor()
        return self

    def refresh_monitor(self):
        """(Re)lit la configuration des ecrans : elle peut changer en cours de route."""
        self._monitor = screens.pick(screens.monitors(), self.screen)
        return self._monitor

    def close(self) -> None:
        for toast in list(self._toasts):
            try:
                toast.window.destroy()
            except Exception:
                pass
        self._toasts = []
        self.unpin()
        if self.root is not None:
            try:
                self.root.destroy()
            except Exception:
                pass
            self.root = None
            self._country_atlas = None
            self._motif_cache = {}

    def stop(self) -> None:
        """Fait rendre la main a run()."""
        if self.root is not None:
            try:
                self.root.quit()
            except Exception:
                pass

    def run(self) -> None:
        """Boucle tkinter. Rend la main sur stop()."""
        self.open()
        self.root.mainloop()

    def run_until_idle(self, check_ms: int = PUMP_MS) -> None:
        """Boucle jusqu'a ce que la pile soit vide (utilise par --test)."""
        self.open()

        def check():
            if not self._toasts and self._pending == 0:
                self.stop()
                return
            self.root.after(check_ms, check)

        self.root.after(check_ms, check)
        self.root.mainloop()

    def every(self, ms: int, callback) -> None:
        """Rappelle `callback` toutes les `ms` millisecondes dans la boucle tkinter.

        C'est par la que la boucle de surveillance, qui vit dans un autre fil,
        fait remonter ses buts : tkinter n'aime pas etre touche ailleurs que
        dans son propre fil.
        """
        self.open()

        def tick():
            try:
                callback()
            finally:
                if self.root is not None:
                    try:
                        self.root.after(ms, tick)
                    except Exception:
                        pass

        self.root.after(ms, tick)

    # ------------------------------------------------------------ cartes ----

    def push(self, card: Card, duration: float = 6.0) -> None:
        """Ajoute une carte au coin, en decalant celles deja affichees.

        Si une application en plein ecran occupe l'ecran vise, la carte partira
        quand meme - la detection peut se tromper, et une carte peut-etre
        visible vaut mieux qu'un but retenu pour rien - mais le journal garde
        la trace du but probablement manque, et l'option de repli le remet en
        file d'attente jusqu'a ce que l'ecran se libere.
        """
        self.open()

        if self.hidden_by_fullscreen():
            self._log("une application en plein ecran occupe {} : la carte y est"
                      " probablement invisible".format(self._screen_name()))
            if self.retry_fullscreen > 0:
                self._retry_later(card, duration,
                                  time.monotonic() + self.retry_fullscreen)

        self._show(card, duration)

    def hidden_by_fullscreen(self) -> bool:
        """Vrai si une fenetre plein ecran masque l'ecran ou va la carte.

        Toujours faux hors de Windows : voir `fullscreen`. Ne leve jamais et ne
        coute qu'une poignee d'appels Win32 (0,1 ms mesuree), donc le cas
        normal ne perd rien.
        """
        monitor = self._monitor or self.refresh_monitor()
        return fullscreen.covers(monitor)

    def _screen_name(self) -> str:
        monitor = self._monitor or self.refresh_monitor()
        return monitor.name

    def _log(self, message: str) -> None:
        if self.on_log is None:
            return
        try:
            self.on_log(message)
        except Exception:
            pass

    def _retry_later(self, card: Card, duration: float, deadline: float) -> None:
        """Represente la carte des que l'ecran se libere, jusqu'a `deadline`.

        La carte compte comme "en attente" : `run_until_idle` ne rend donc pas
        la main avant que la question soit tranchee, dans un sens ou l'autre.
        """
        self._pending += 1

        def again():
            if self.root is None:
                return
            if not self.hidden_by_fullscreen():
                self._pending -= 1
                self._log("l'ecran s'est libere : la carte repasse")
                try:
                    self._show(card, duration)
                except Exception as exc:
                    # Personne n'attend cet appel : sans ce filet, l'echec
                    # partirait dans la sortie d'erreur de tkinter.
                    self._log("carte non reaffichee : {}".format(exc))
                return
            if time.monotonic() >= deadline:
                self._pending -= 1
                self._log("toujours en plein ecran apres {:.0f}s : carte"
                          " abandonnee".format(self.retry_fullscreen))
                return
            self.root.after(RETRY_POLL_MS, again)

        self.root.after(RETRY_POLL_MS, again)

    def _show(self, card: Card, duration: float) -> None:
        """Cree la fenetre de la carte et la fait apparaitre."""
        self.open()

        # Trop de cartes : la plus ancienne s'en va tout de suite.
        while len(self._toasts) >= self.max_visible:
            self._toasts[-1].destroy()

        toast = _Toast(self, card, duration)
        self._toasts.insert(0, toast)
        self._reposition()
        toast.start()

    def push_later(self, delay_ms: int, card: Card, duration: float = 6.0) -> None:
        """Programme une carte : sert a montrer l'empilement (`--test 3`)."""
        self.open()
        self._pending += 1

        def fire():
            self._pending -= 1
            self.push(card, duration)

        self.root.after(max(0, int(delay_ms)), fire)

    # ---------------------------------------------------- carte epinglee ----

    def pin(self, card: Card) -> None:
        """Pose la carte epinglee, ou met a jour celle qui est deja la.

        Appelee a chaque releve tant que le match dure : la premiere fois elle
        ouvre la fenetre, ensuite elle ne fait que redessiner dedans. La pile
        est repositionnee dans les deux cas, la carte pouvant changer de taille
        (un score a deux chiffres, une minute plus longue).
        """
        self.open()
        if self._pinned is None:
            self._pinned = _Pinned(self, card)
            self._reposition()
            self._pinned.start()
            return
        self._pinned.update(card)
        self._reposition()

    def unpin(self) -> None:
        """Retire la carte epinglee, s'il y en a une. La pile se retasse."""
        if self._pinned is None:
            return
        pinned, self._pinned = self._pinned, None
        pinned.destroy()
        self._reposition()

    @property
    def pinned(self):
        """La carte epinglee affichee, ou None. Sert aux tests et au journal."""
        return self._pinned.card if self._pinned is not None else None

    def _remove(self, toast) -> None:
        try:
            toast.window.destroy()
        except Exception:
            pass
        if toast in self._toasts:
            self._toasts.remove(toast)
        self._reposition()

    def _reposition(self) -> None:
        """Recalcule la place de chaque carte depuis le coin choisi.

        L'epinglee et les fugaces sont calculees d'un seul coup : c'est la
        garantie qu'une carte de but ne se pose jamais dessus.
        """
        monitor = self._monitor or self.refresh_monitor()
        sizes = [(toast.width, toast.height) for toast in self._toasts]
        anchor, places = layout_stack(
            monitor,
            (self._pinned.width, self._pinned.height) if self._pinned else None,
            sizes, self.position)
        if anchor is not None:
            self._pinned.move(*anchor)
        for toast, (x, y) in zip(self._toasts, places):
            toast.move(x, y)

    def __len__(self):
        return len(self._toasts)


# -------------------------------------------------------------- raccourcis ---

def show(cards, duration: float = 6.0, sound_path=None, screen=None,
         position="bottom-right", opacity: float = 1.0, scale: float = 1.0,
         stagger: float = 0.9, retry_fullscreen: float = 0.0, on_log=None,
         pinned=None, volume: float = sound.MAX_VOLUME) -> None:
    """Affiche une ou plusieurs cartes, et rend la main quand tout est efface.

    Bloquant : pratique pour `--test`. Le daemon, lui, garde une Stack ouverte
    et pousse ses cartes au fil des buts.

    `pinned` : une carte epinglee a poser au coin le temps de la demonstration.
    Elle ne retient pas la main - `run_until_idle` ne compte que les fugaces -
    et s'en va avec la pile : sinon `--test --pin` ne rendrait jamais la main.
    """
    if isinstance(cards, Card):
        cards = [cards]

    stack = Stack(screen=screen, position=position, opacity=opacity, scale=scale,
                  retry_fullscreen=retry_fullscreen, on_log=on_log)
    stack.open()
    try:
        if pinned is not None:
            stack.pin(pinned)
        for index, card in enumerate(cards):
            stack.push_later(int(index * stagger * 1000), card, duration)
        handle = sound.play_async(sound_path, volume) if sound_path else None
        try:
            stack.run_until_idle()
        finally:
            sound.release(handle)
    finally:
        stack.close()
