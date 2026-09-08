"""Les cartes ecrites dans le terminal, quand il n'y a pas d'ecran ou les poser.

Un serveur sans X, une session SSH, un tmux, un conteneur : `overlay.py` n'y a
aucune fenetre a ouvrir, et jusqu'ici un but n'y laissait qu'une ligne de
journal. `--no-overlay` existait deja, mais il coupe l'affichage, il ne le
remplace pas.

    +----------------------------------------------------------------------------+
    | BUT !  LIGUE 1                                                         35' |
    |                      Angers  1 - 2  Stade Rennais                          |
    | But de C. Arcus                                                            |
    +----------------------------------------------------------------------------+

Pourquoi ce module n'est pas `tests/blueprint.py` deplace ici
--------------------------------------------------------------

Le depot sait deja rendre une carte en ASCII : `tests/blueprint.py` transcrit
`overlay._draw` dans une grille de caracteres, et c'est ce qui produit
`tests/plans/*.txt`. La reutiliser ici etait la premiere idee, et elle a ete
essayee avant d'etre ecartee, en la faisant tourner sur les cartes du depot.

Elle ne marche pas, et pour une raison de fond : un plan est une transcription
d'une geometrie en **pixels**, a raison d'un caractere pour huit pixels. Le
ramener a la taille d'un terminal revient a rendre la grille plus grossiere, et
une grille plus grossiere fait entrer les traces les uns dans les autres. Voici
ce que donne le plan de la carte de fin de match dans une hauteur de terminal :

    |##-FIN DU MATCH--LIGUE ---------------------90'+4'-+|
    |## Angers :M. Lopez 12'  -   2   Stade Rennais     ||

"LIGUE 1" a perdu son chiffre sous le bord de la carte, et la ligne des
buteurs est passee par-dessus le score. C'est normal : `blueprint` est fait
pour qu'un decalage de deux pixels saute aux yeux dans un diff de PR, pas pour
mettre du texte en page. Le rendre lisible en terminal reviendrait a lui
demander le contraire de ce pour quoi il a ete ecrit, et les plans figes en
paieraient le prix.

Ce module pose donc les memes elements dans la meme geometrie - le score au
centre, la place des noms reservee a l'identique des deux cotes, les cartons
contre le chiffre de leur equipe, le nom trop long qui cede - mais il la calcule
en **caracteres**. Ce qui reste unique, et c'est le seul partage qui compte,
c'est la source : la meme `overlay.Card`, fabriquee par le meme
`Card.from_event`. Aucun contenu n'est refabrique ici, rien n'est retraduit, et
une carte qui change de forme change des deux cotes a la fois.

Le garde-fou contre la derive est dans `tests/test_terminal.py` : il rend en
terminal les **memes cartes figees** que les plans de `blueprint.SCENARIOS`, et
verifie que chacune y porte encore son titre, ses deux equipes, son score et
son detail. Une forme de carte ajoutee aux plans arrive donc ici toute seule, et
un element qui disparaitrait d'un cote ferait tomber un test de l'autre.

Ce qu'une carte de terminal ne montre pas
------------------------------------------

Les ecussons : un terminal n'affiche pas d'image, et les remplacer par un sigle
ferait dire au dessin quelque chose que la carte ne dit pas.

Les couleurs. Tout le choix de couleur du programme repose sur une certitude :
le fond de la carte vaut `overlay.CARD_BG`, et `crests.pick_accent` ne garde la
couleur d'un club que si elle se lit sur CE fond-la. Un terminal n'a pas de fond
connu - il peut etre blanc, noir, ou n'importe quoi - donc la question que
`pick_accent` sait trancher n'a plus de reponse ici. Ecrire quand meme une
couleur reviendrait a parier sur le theme de quelqu'un d'autre, et un nom de
club illisible est pire qu'un nom de club en noir et blanc. La question de
NO_COLOR, du tty et des consoles Windows ne se pose donc pas encore : il n'y a
aucun code d'echappement a degrader.

Ou ca s'ecrit
--------------

Sur la **sortie d'erreur**, comme tout ce qui n'est pas une donnee (voir la
section "Deux sorties, et une seule porte les donnees" du README). En daemon, la
sortie standard porte les lignes de journal : ce sont elles qu'on redirige vers
un fichier et qu'on passe a un `grep`. Une carte de six lignes plantee au milieu
serait exactement la phrase au milieu du CSV que cette regle interdit. Dans un
terminal les deux flux se melent et on lit tout ; des qu'on redirige, chacun va
ou il doit.
"""

from __future__ import annotations

import shutil
import sys

# Largeur de confort et plafond, comme les MIN_WIDTH / MAX_WIDTH en pixels de
# `overlay._layout` : une carte plus etroite ne sait plus rien montrer, et une
# carte qui prendrait toute la largeur d'un terminal de 200 colonnes eparpille
# le score et le nom si loin l'un de l'autre qu'on ne les lit plus ensemble.
MIN_WIDTH = 30
MAX_WIDTH = 78

# Le cadre. Trois signes ASCII, pas de semi-graphique Unicode : le depot est en
# ASCII pur, et une console Windows sur sa page de code d'origine ne dessinerait
# de toute facon pas les caracteres de boite.
CORNER = "+"
EDGE_H = "-"
EDGE_V = "|"

# Un carton rouge, faute de rouge. Deux signes plutot qu'un, pour qu'on compte
# les expulsions d'un coup d'oeil sans avoir a lire un chiffre - la raison meme
# pour laquelle la carte de l'ecran dessine un rectangle au lieu d'ecrire "1".
RED = "[]"

GAP = 2                  # espaces entre un nom d'equipe et le score
RED_NAME_GAP = 1         # espace entre les cartons et le nom de leur equipe
HEAD_GAP = 2             # espaces entre le titre et le nom de la competition
ELLIPSIS = "..."


# ------------------------------------------------------------- largeur -------

def columns(stream=None) -> int:
    """La largeur a donner a une carte ecrite dans `stream`.

    Une sortie qui n'est pas un terminal n'a pas de largeur : sa "taille" serait
    celle d'une console qui n'est pas la, ou celle heritee d'une variable
    COLUMNS qui traine. On rend alors une largeur fixe, ce qui a l'avantage de
    rendre un fichier redirige identique d'une machine a l'autre.

    Ne leve jamais : un flux exotique - un test qui capture, un service sans
    console - rend la largeur fixe et la carte s'ecrit quand meme.
    """
    stream = sys.stderr if stream is None else stream
    try:
        if not stream.isatty():
            return MAX_WIDTH
    except Exception:
        return MAX_WIDTH
    try:
        found = shutil.get_terminal_size((MAX_WIDTH + 2, 24)).columns
    except Exception:
        return MAX_WIDTH
    # Deux colonnes de marge : une carte collee au bord droit se fait couper par
    # le retour a la ligne des que le terminal compte un caractere de moins que
    # ce qu'il annonce, ce qui arrive.
    return max(MIN_WIDTH, min(MAX_WIDTH, int(found) - 2))


# ------------------------------------------------------------ decoupe --------

def shorten(text: str, limit: int) -> str:
    """Raccourcit `text` avec des points de suspension pour tenir en `limit`.

    La transposition en caracteres de `overlay._fit`, meme regle comprise : on
    rend au moins un caractere plutot qu'une chaine vide, parce qu'un nom
    d'equipe reduit a rien laisse un score qui ne dit plus qui joue.
    """
    text = text or ""
    if len(text) <= limit:
        return text
    trimmed = text[:max(0, limit - len(ELLIPSIS))].rstrip()
    return (trimmed + ELLIPSIS) if trimmed else text[:1]


def _join(parts, limit: int) -> str:
    """Assemble une ligne en morceaux, coupee sur `limit` caracteres.

    Comme `overlay._fit_parts` : les morceaux entiers passent tant qu'ils
    rentrent, celui qui deborde est coupe, et la suite est abandonnee - une
    liste de buteurs qui grandit ne pousse jamais de texte hors de la carte.

    Le drapeau de mise en valeur des morceaux ("le buteur ressort en clair") est
    ignore : il ne se dit qu'en couleur, et ce module n'en met pas.
    """
    line = ""
    for text, _strong in parts:
        room = limit - len(line)
        if len(text) <= room:
            line += text
            continue
        short = shorten(text, room)
        if len(short) <= room:
            line += short
        break
    return line


# -------------------------------------------------------------- dessin -------

def _header(card, inner: int) -> str:
    """Ligne 1 : le titre, la competition, et la minute a droite."""
    minute = card.minute or ""
    head = card.title or ""
    if card.league:
        head = (head + " " * HEAD_GAP + card.league) if head else card.league
    # La minute garde sa place quoi qu'il arrive : c'est le seul element de la
    # carte qui dit ou en est le match, et un titre a rallonge n'a pas a
    # l'effacer. C'est donc lui qui cede, comme le nom d'equipe cede au score.
    # Elle est collee au bord droit, la ou la carte de l'ecran l'ancre aussi.
    room = inner - len(minute)
    return shorten(head, room - 1 if minute else room).ljust(room) + minute


def _score(card, inner: int) -> str:
    """Ligne 2 : les deux equipes, leurs cartons, et le score au centre.

    La place des noms est reservee a l'identique des deux cotes, et celle des
    cartons sur le camp le plus sanctionne : c'est ce qui garde le score au
    centre de la carte, exactement comme `overlay._layout` le fait en pixels.
    Une reserve par camp deplacerait le score a chaque expulsion.
    """
    score = "{} - {}".format(card.home_score, card.away_score)
    reds = max(card.home_reds, card.away_reds)
    red_slot = (len(RED) * reds + RED_NAME_GAP) if reds else 0

    half = (inner - len(score)) // 2 - GAP
    room = max(1, half - red_slot)

    # Les cartons sont colles au score et non au nom : un camp qui en a un et
    # l'autre deux les gardent ainsi alignes sur la meme colonne.
    line = (shorten(card.home, room).rjust(room)
            + (RED * card.home_reds).rjust(red_slot)
            + " " * GAP + score + " " * GAP
            + (RED * card.away_reds).ljust(red_slot)
            + shorten(card.away, room).ljust(room))
    # Filet de securite : sur une carte reduite au minimum et deux camps
    # expulses, la reserve des cartons peut manger toute la place des noms. La
    # carte reste alors dans ses bords, quitte a couper - jamais l'inverse.
    return line[:inner]


def render(card, width: int = MAX_WIDTH) -> list:
    """Les lignes de la carte, cadre compris. Toutes de la meme longueur."""
    width = max(MIN_WIDTH, int(width))
    inner = width - 4                    # "| " a gauche, " |" a droite
    edge = CORNER + EDGE_H * (width - 2) + CORNER

    body = [_header(card, inner), _score(card, inner)]
    if card.parts:
        body.append(_join(card.parts, inner))
    for line in card.extra:
        if line:
            body.append(_join(line, inner))

    return ([edge]
            + ["{} {} {}".format(EDGE_V, text.ljust(inner), EDGE_V)
               for text in body]
            + [edge])


def draw(card, width: int = MAX_WIDTH) -> str:
    """La carte entiere, prete a etre ecrite."""
    return "\n".join(render(card, width))


# -------------------------------------------------------------- sortie -------

class Writer:
    """Le porte-plume des cartes : il tient le flux et sa largeur.

    Une instance vit aussi longtemps que le daemon, et relit la largeur du
    terminal a chaque carte : une fenetre redimensionnee en cours de soiree ne
    doit pas laisser des cartes trop larges jusqu'au prochain redemarrage.
    """

    def __init__(self, stream=None, width=None):
        self.stream = sys.stderr if stream is None else stream
        # Une largeur imposee sert aux tests et a un terminal qui ment ; sans
        # elle, on redemande a chaque carte.
        self.fixed = int(width) if width else None

    def width(self) -> int:
        return self.fixed or columns(self.stream)

    def show(self, card) -> bool:
        """Ecrit la carte. Rend vrai si elle est partie, faux sinon.

        N'echoue jamais bruyamment : un tuyau referme, une console fermee sous
        les pieds d'un service, un flux deja detruit a l'arret ne doivent pas
        tuer un daemon dont le travail - le journal, le son, le crochet - est
        deja fait ailleurs.
        """
        try:
            self.stream.write(draw(card, self.width()) + "\n")
            self.stream.flush()
            return True
        except Exception:
            return False
