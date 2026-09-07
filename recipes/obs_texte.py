#!/usr/bin/env python3
"""Afficher le dernier but dans un bandeau, pour OBS ou une barre d'etat.

    butbutbut --on-goal 'python3 /chemin/vers/recipes/obs_texte.py'

A regler : rien. Facultatif : BUTBUTBUT_OBS_FICHIER (le fichier a ecrire, par
    defaut but-en-cours.txt dans ton dossier personnel) et
    BUTBUTBUT_OBS_SECONDES (duree d'affichage, 12 par defaut, 25 au plus).

Systemes : tous. Python 3.8+, bibliotheque standard seule.

Dans OBS : Sources > + > Texte (GDI+ ou FreeType) > "Lire depuis un fichier",
et on pointe ce fichier. Une barre d'etat (i3blocks, waybar, tmux) le lit
aussi bien avec un `cat` toutes les deux secondes.

Le fichier **redevient vide** apres la duree d'affichage : un bandeau qui garde
le but de 21h07 jusqu'a la fin du direct ment au spectateur. On ne l'efface
qu'a la condition d'y retrouver exactement ce qu'on y avait ecrit - sinon,
c'est qu'un autre but est passe entre-temps et c'est a lui d'avoir le bandeau.

A savoir : le fil du crochet reste occupe pendant toute la duree d'affichage,
et butbutbut n'en tient que huit a la fois.
"""

import os
import sys
import time

DEFAULT_SECONDS = 12.0
MAX_SECONDS = 25.0          # le crochet tue la commande a 30 secondes


def value(name, default=""):
    """Le detail du but, tel que le crochet l'a pose dans l'environnement."""
    return os.environ.get(name, "") or default


def target():
    raw = os.environ.get("BUTBUTBUT_OBS_FICHIER", "").strip()
    if raw:
        return os.path.expanduser(raw)
    return os.path.join(os.path.expanduser("~"), "but-en-cours.txt")


def seconds():
    try:
        wanted = float(os.environ.get("BUTBUTBUT_OBS_SECONDES", "") or
                       DEFAULT_SECONDS)
    except ValueError:
        wanted = DEFAULT_SECONDS
    return max(0.0, min(MAX_SECONDS, wanted))


def banner():
    """La ligne du bandeau : courte, un bandeau n'a pas la place d'un roman."""
    head = "VAR" if value("BUT_TYPE") == "cancelled" else "BUT"
    line = "{} : {} {} {}".format(
        head, value("BUT_HOME", "?"), value("BUT_SCORE", "?"),
        value("BUT_AWAY", "?"))
    scorer = value("BUT_SCORER")
    minute = value("BUT_MINUTE")
    if scorer:
        line += " - " + scorer
    if minute:
        line += " (" + minute + ")"
    return line


def write(path, text):
    """Ecrit a cote puis renomme, pour qu'OBS ne lise jamais un demi-bandeau.

    Sous Windows, le renommage echoue si OBS tient le fichier ouvert au meme
    instant : on ecrit alors dedans directement. Un bandeau lu a moitie une
    fois sur mille vaut mieux qu'un bandeau qui ne s'affiche pas.
    """
    temporary = path + ".tmp"
    try:
        with open(temporary, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(temporary, path)
    except OSError:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)


def read(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()
    except OSError:
        return ""


def main(sleep=time.sleep):
    # L'attente est injectable : c'est la seule facon d'eprouver ce qui se
    # passe quand un deuxieme but tombe pendant l'affichage, sans faire durer
    # un test douze secondes.
    path = target()
    line = banner() + "\n"
    try:
        write(path, line)
        sleep(seconds())
        if read(path) == line:
            # Personne n'a marque depuis : le bandeau nous appartient encore.
            write(path, "")
    except OSError as error:
        print("obs : ecriture impossible ({})".format(error))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
