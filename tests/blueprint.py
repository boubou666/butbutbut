"""Le plan d'une carte : sa geometrie figee en ASCII, lisible et diffable.

`overlay.py` dessine toutes les cartes du programme, et jusqu'ici sa mise en
page n'etait tenue que par des assertions ponctuelles, ecrites une par une au
fil des nouveautes : "le carton ne mord pas sur le nom", "le score reste
centre". Chacune est juste, aucune ne dit a quoi ressemble la carte, et un
decalage de deux pixels passait entre elles sans qu'un seul test bronche.

Ce module rend donc une carte en **texte**, range en fichier de reference dans
`tests/plans/`. Un decalage se voit alors deux fois : dans le tableau des
boites, au pixel pres, et dans le dessin, qui dit ou est le score, ou est le
nom, ou sont les ecussons et les cartons. La revue de PR lit le decalage au
lieu d'un nombre qui change.

Pas d'image de reference : un PNG est binaire, illisible en revue, et il
dependrait de la police installee sur la machine.

Le plan passe par `_draw` et non seulement par `_layout` : ce qui est fige est
donc ce qui arrive vraiment a l'ecran, ordre de dessin compris, et non une
seconde mise en page qui pourrait deriver de la premiere. `_Pen` est un canvas
qui note au lieu de peindre.

Trois precautions rendent le plan identique sur les trois systemes et les cinq
versions de Python de la CI - c'est tout l'interet de la chose, un plan qui
bouge d'un runner a l'autre ne serait qu'une nuisance :

  - les polices sont **fausses et fixes** (`FakeFont`, deja utilise par
    `test_overlay.py` pour tester sans ecran) : un caractere large de N pixels,
    un interligne constant. Les metriques de tkinter, elles, different d'un
    Ubuntu a un Windows ;
  - les cartes des scenarios sont **ecrites ici**, pas fabriquees par
    `Card.from_event` ni par `Card.demo` : le plan fige de la geometrie, il n'a
    pas a casser le jour ou un libelle de competition ou une traduction change ;
  - les coordonnees sont arrondies au dixieme de pixel avant d'etre ecrites,
    donc jamais un flottant en toutes lettres.

Regenerer les references :

    python tools/plans.py
"""

import io
import math
import os

from helpers import FakeFont

from butbutbut import overlay

HERE = os.path.dirname(os.path.abspath(__file__))
PLANS = os.path.join(HERE, "plans")

# Largeur d'un caractere et interligne de chaque police, en pixels, a --scale 1.
# Les valeurs sont inventees : ce qu'on demande a ce jeu, ce n'est pas de
# ressembler a Segoe UI, c'est de rendre le meme nombre partout et de garder
# entre les six polices les proportions qui font la carte - un score plus haut
# qu'un nom d'equipe, une etiquette plus basse qu'un titre.
METRICS = {
    "label": (7, 12),
    "title": (9, 15),
    "team": (11, 20),
    "score": (15, 27),
    "detail": (8, 14),
    "scorer": (9, 15),
}

# Le dessin regarde la carte a travers une grille grossiere : une colonne pour
# six pixels, une ligne pour huit. Assez fin pour qu'un nom se lise a sa place,
# assez grossier pour qu'une carte de 420 pixels tienne dans la largeur d'un
# diff. La precision au pixel, elle, est dans le tableau des boites.
CELL_W = 8
CELL_H = 8

# Les glyphes du dessin. Chacun doit se distinguer d'une lettre de texte : on
# doit voir d'un coup d'oeil ce qui est un ecusson et ce qui est un nom.
BORDER = "+"
EDGE_H = "-"
EDGE_V = "|"
BAR = "#"
LOGO = "o"
RED = "R"


def fonts(scale=1.0):
    """Les six polices de la carte, mesurables sans tkinter, a `scale`.

    Meme regle que `overlay._fonts` : la taille suit l'echelle et bute sur un
    plancher, sans quoi une carte a --scale 0.2 n'aurait plus de police du tout.
    """
    return {name: FakeFont(max(3, int(width * scale)), max(6, int(line * scale)))
            for name, (width, line) in METRICS.items()}


class _Logo:
    """Un ecusson deja mis a la taille, sans PhotoImage ni tkinter."""

    def __init__(self, size):
        self.size = size


class _Pen:
    """Un canvas qui note ce qu'on lui demande de dessiner, au lieu de peindre.

    Il n'implemente que les quatre appels de `_draw`, plus `bbox` dont `_draw`
    se sert pour poser le nom du championnat derriere le titre.
    """

    def __init__(self):
        self.items = []

    def _add(self, kind, bounds, **extra):
        extra["kind"] = kind
        extra["bounds"] = bounds
        self.items.append(extra)
        return len(self.items) - 1

    def create_rectangle(self, x0, y0, x1, y1, fill=None, outline=None):
        return self._add("rect", (x0, y0, x1, y1), fill=fill)

    def create_polygon(self, points, smooth=False, fill=None, outline=None):
        xs = points[0::2]
        ys = points[1::2]
        return self._add("frame", (min(xs), min(ys), max(xs), max(ys)), fill=fill)

    def create_text(self, x, y, text="", fill=None, font=None, anchor="w"):
        width = font.measure(text)
        line = font.metrics("linespace")
        x0 = x - width if anchor == "e" else x
        return self._add("text", (x0, y - line / 2.0, x0 + width, y + line / 2.0),
                         text=text, font=font, anchor=anchor)

    def create_image(self, x, y, image=None, anchor="w"):
        size = image.size
        x0 = x - size if anchor == "e" else x
        return self._add("logo", (x0, y - size / 2.0, x0 + size, y + size / 2.0),
                         anchor=anchor)

    def bbox(self, item):
        return tuple(self.items[item]["bounds"])


def _named(pen, card, box, sheet):
    """Donne un nom francais a chaque trace, pour la colonne de gauche.

    Les noms disent ce que le trace EST, et rien de plus : ils ne se
    numerotent pas. Deux cartons ou deux morceaux de la meme ligne portent donc
    le meme nom, et ce sont leurs coordonnees et leur contenu qui les separent
    - une numerotation se serait decalee tout entiere a la premiere expulsion
    de plus, pour un diff illisible.
    """
    roles = {id(font): name for name, font in sheet.items()}
    heights = [box["detail_y"]] + list(box["extra_y"])
    scores = ("score dom.", "separateur", "score ext.")
    scored = 0
    named = []

    for item in pen.items:
        kind = item["kind"]
        if kind == "frame":
            name = "carte"
        elif kind == "rect" and item["fill"] == overlay.RED_CARD:
            name = "carton"
        elif kind == "rect" and item["fill"] == card.accent:
            name = "filet"
        elif kind == "rect":
            # Le rectangle de fond, exactement aux dimensions de la carte : il
            # ne dit rien que la ligne "carte" ne dise deja.
            continue
        elif kind == "logo":
            name = "ecusson dom." if item["anchor"] == "e" else "ecusson ext."
        else:
            role = roles.get(id(item["font"]), "?")
            middle = (item["bounds"][1] + item["bounds"][3]) / 2.0
            if role == "title":
                name = "titre"
            elif role == "label":
                name = "competition" if item["anchor"] == "w" else "minute"
            elif role == "team":
                name = "equipe dom." if item["anchor"] == "e" else "equipe ext."
            elif role == "score":
                name = scores[min(scored, 2)]
                scored += 1
            else:
                # Le buteur et les lignes de fin de match partagent leurs deux
                # polices : c'est la hauteur qui les separe.
                rank = min(range(len(heights)),
                           key=lambda i: abs(middle - heights[i]))
                name = "detail" if rank == 0 else "ligne {}".format(rank)
        named.append((name, item))
    return named


def _px(value):
    """Un pixel, ecrit court : entier quand il l'est, un dixieme sinon."""
    rounded = round(float(value), 1)
    if rounded == int(rounded):
        return str(int(rounded))
    return "{:.1f}".format(rounded)


def _grid(named, width, height):
    """Le dessin : chaque trace pose ses caracteres dans une grille grossiere."""
    # La grille tient exactement le dernier pixel de la carte, qui est
    # `width - 1` : la dimensionner sur `width` laisserait une colonne et une
    # ligne vides au bout, ou le bord de la carte n'ira jamais.
    cols = max(1, int(math.ceil((int(width) - 1) / float(CELL_W))))
    rows = max(1, int(math.ceil((int(height) - 1) / float(CELL_H))))
    cells = [[" "] * cols for _ in range(rows)]

    def put(row, col, char):
        if 0 <= row < rows and 0 <= col < cols:
            cells[row][col] = char

    def span(bounds):
        # Le coin haut-gauche tombe sur la colonne la plus proche, le coin
        # bas-droit sur la derniere colonne que la boite touche : arrondir les
        # deux au plus proche mangerait le bord droit de la carte, et un texte
        # y perdrait sa derniere lettre pour un demi-pixel.
        x0, y0, x1, y1 = bounds
        c0, r0 = int(x0 / CELL_W + 0.5), int(y0 / CELL_H + 0.5)
        return (c0, r0,
                max(c0, int(math.ceil(x1 / float(CELL_W))) - 1),
                max(r0, int(math.ceil(y1 / float(CELL_H))) - 1))

    for name, item in named:
        c0, r0, c1, r1 = span(item["bounds"])
        if item["kind"] == "frame":
            for col in range(c0, c1 + 1):
                put(r0, col, EDGE_H)
                put(r1, col, EDGE_H)
            for row in range(r0, r1 + 1):
                put(row, c0, EDGE_V)
                put(row, c1, EDGE_V)
            for row, col in ((r0, c0), (r0, c1), (r1, c0), (r1, c1)):
                put(row, col, BORDER)
        elif item["kind"] in ("rect", "logo"):
            char = BAR if name.startswith("filet") else (
                LOGO if item["kind"] == "logo" else RED)
            for row in range(r0, r1 + 1):
                for col in range(c0, c1 + 1):
                    put(row, col, char)
        else:
            # Le texte est ecrit tel quel, a partir de sa colonne de depart et
            # sur sa ligne du milieu : c'est ce qui rend le dessin lisible.
            row = int((item["bounds"][1] + item["bounds"][3]) / 2.0 // CELL_H)
            for offset, char in enumerate(item["text"]):
                if c0 + offset > c1:
                    break
                put(row, c0 + offset, char)

    return cells


def _ruler(cols, indent):
    """La reglette du haut : l'abscisse en pixels, toutes les dix colonnes."""
    marks = [" "] * (cols + 6)
    for col in range(0, cols, 10):
        for offset, char in enumerate(str(col * CELL_W)):
            marks[col + offset] = char
    return (" " * indent + "".join(marks)).rstrip()


def plan(card, scale=1.0, note=""):
    """Rend le plan ASCII d'une carte, tel qu'il est range dans `tests/plans/`."""
    sheet = fonts(scale)
    box = overlay._layout(card, sheet)
    images = {}
    if box["logo"]:
        for key, path in (("home", card.home_logo), ("away", card.away_logo)):
            if path is not None:
                images[key] = _Logo(box["logo"])

    pen = _Pen()
    overlay._draw(pen, card, sheet, box, overlay.CARD_BG, images)
    named = _named(pen, card, box, sheet)

    lines = []
    if note:
        lines.append("# " + note)
    lines.append("# echelle {:.2f} - police (largeur/interligne) {}".format(
        scale, "  ".join("{} {}/{}".format(name, sheet[name].width,
                                           sheet[name].line)
                         for name in sorted(sheet))))
    lines.append("# carte {} x {} px - grille {} x {} px par caractere".format(
        box["width"], box["height"], CELL_W, CELL_H))
    lines.append("")

    cells = _grid(named, box["width"], box["height"])
    lines.append(_ruler(len(cells[0]), 5))
    for index, row in enumerate(cells):
        lines.append("{:>3} |{}|".format(index * CELL_H, "".join(row)).rstrip())
    lines.append("")

    head = ("{:<14}{:>7}{:>7}{:>7}{:>7}  {}"
            .format("boite", "x0", "y0", "x1", "y1", "contenu"))
    lines.append(head)
    lines.append("-" * 42 + "  " + "-" * 30)
    for name, item in named:
        x0, y0, x1, y1 = item["bounds"]
        content = '"{}"'.format(item["text"]) if item["kind"] == "text" else ""
        lines.append("{:<14}{:>7}{:>7}{:>7}{:>7}  {}".format(
            name, _px(x0), _px(y0), _px(x1), _px(y1), content).rstrip())
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------- scenarios -----

# Les cartes sont ecrites ici plutot que fabriquees par `Card.from_event` : le
# plan fige une geometrie, pas un libelle. Le contenu reste celui des vraies
# cartes - c'est lui qui donne leur largeur aux boites - mais il ne bougera pas
# le jour ou une traduction ou un nom de competition change.

CREST = "ecusson.png"


def _goal(**kwargs):
    base = dict(title="BUT !", league="LIGUE 1", minute="35'",
                home="Angers", away="Stade Rennais",
                home_score=1, away_score=2, side="home",
                detail=[("But de ", False), ("C. Arcus", True)],
                accent="#f2e34c")
    base.update(kwargs)
    return overlay.Card(**base)


def _scenarios():
    """Les cartes figees, et pourquoi chacune est la.

    Une par forme de carte du programme, plus celles ou la mise en page a deja
    casse : des noms trop longs, des cartons des deux cotes, une echelle qui
    n'est pas 1.
    """
    return [
        ("but-football", 1.0,
         "La carte de but : trois lignes, deux ecussons, un buteur.",
         _goal(home_logo=CREST, away_logo=CREST)),

        ("carte-epinglee", 1.0,
         "La carte epinglee : ni buteur ni couleur d'equipe, elle ne dit que"
         " l'etat du match.",
         overlay.Card(title="EN COURS", league="LIGUE 1", minute="67'",
                      home="Angers", away="Stade Rennais",
                      home_score=1, away_score=2, side=None, detail=[],
                      accent="#f2e34c", title_color=overlay.MUTED,
                      home_logo=CREST, away_logo=CREST)),

        ("fin-de-match", 1.0,
         "Le sifflet final : une ligne de buteurs par camp, sous le score.",
         overlay.Card(title="FIN DU MATCH", league="LIGUE 1", minute="90'+4'",
                      home="Angers", away="Stade Rennais",
                      home_score=1, away_score=2, side=None, detail=[],
                      accent="#f2e34c", title_color=overlay.MUTED,
                      extra=[[("Angers : ", False), ("M. Lopez 12'", True)],
                             [("Stade Rennais : ", False),
                              ("A. Kalimuendo 58', L. Blas 77'", True)]])),

        ("rugby-essai", 1.0,
         "Le rugby : un essai vaut cinq points, et le detail de la carte le"
         " dit - une ligne plus longue qu'un but de football.",
         overlay.Card(title="ESSAI !", league="TOP 14", minute="63'",
                      home="Stade Toulousain", away="Stade Francais",
                      home_score=19, away_score=14, side="home",
                      detail=[("Essai de ", False), ("A. Dupont", True),
                              (" (+5)", False)],
                      accent="#1f7a3d", home_logo=CREST, away_logo=CREST)),

        ("cartons-rouges", 1.0,
         "Deux expulsions d'un cote, une de l'autre : la place est reservee"
         " des deux cotes, sur le camp le plus sanctionne, et le score reste"
         " au centre de la carte.",
         _goal(home_reds=2, away_reds=1, home_logo=CREST, away_logo=CREST)),

        ("noms-tronques", 1.0,
         "Des noms a rallonge, des cartons et des ecussons : la carte bute sur"
         " son plafond de largeur et ce sont les noms qui cedent.",
         _goal(home="Borussia Monchengladbach", away="Eintracht Frankfurt",
               home_reds=2, away_reds=1, home_logo=CREST, away_logo=CREST)),

        ("echelle-075", 0.75,
         "La meme carte de but a --scale 0.75 : elle garde sa largeur de"
         " confort (MIN_WIDTH) et perd de la hauteur.",
         _goal(home_logo=CREST, away_logo=CREST)),

        ("echelle-160", 1.6,
         "La meme carte de but a --scale 1.6 : tout grandit ensemble, y"
         " compris les ecussons et les cartons.",
         _goal(home_reds=1, home_logo=CREST, away_logo=CREST)),
    ]


SCENARIOS = _scenarios()


def path(name):
    return os.path.join(PLANS, name + ".txt")


def render(name):
    """Le plan attendu pour le scenario `name`, calcule maintenant."""
    for scenario, scale, note, card in SCENARIOS:
        if scenario == name:
            return plan(card, scale, note)
    raise KeyError(name)


def stored(name):
    """Le plan de reference, tel qu'il est range dans le depot."""
    with io.open(path(name), "r", encoding="ascii", newline="\n") as handle:
        return handle.read()


def write_all(dry_run=False):
    """Reecrit tous les plans de reference. Rend la liste des noms changes.

    `dry_run` ne fait que comparer. C'est ce que les tests appellent : un test
    qui reecrirait la reference qu'il est cense controler la reparerait en
    silence, et ne serait plus un test du tout.
    """
    if not dry_run and not os.path.isdir(PLANS):
        os.makedirs(PLANS)
    changed = []
    for name, scale, note, card in SCENARIOS:
        text = plan(card, scale, note)
        try:
            before = stored(name)
        except (IOError, OSError):
            before = None
        if before != text:
            changed.append(name)
        if dry_run:
            continue
        # newline="\n" est explicite : sans lui, une regeneration sous Windows
        # rangerait des fins de ligne CRLF dans un fichier que la CI relit sous
        # Linux, et tous les plans seraient rouges d'un coup.
        with io.open(path(name), "w", encoding="ascii", newline="\n") as handle:
            handle.write(text)
    return changed
