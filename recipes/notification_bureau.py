#!/usr/bin/env python3
"""Doubler la carte par une vraie notification du systeme.

    butbutbut --on-goal 'python3 /chemin/vers/recipes/notification_bureau.py'

A regler : rien.

Systemes : Linux (notify-send, du paquet libnotify), macOS (osascript, fourni),
    Windows (PowerShell, fourni). Ailleurs, la recette le dit et s'arrete.

Pourquoi doubler la carte de butbutbut, qui fait deja le travail ? Parce
qu'elle s'efface au bout de quelques secondes et ne laisse rien derriere elle.
Une notification du systeme, si : elle s'empile dans le centre de
notifications, et le but rate pendant qu'on etait a la cuisine s'y retrouve.
C'est aussi le seul moyen de voir passer un but quand butbutbut tourne en
`--no-overlay`, ou quand un jeu en plein ecran mange la carte.

Le texte ne passe **jamais** par la ligne de commande construite ici : chaque
systeme va le relire dans l'environnement (PowerShell) ou le recoit en
argument (osascript, notify-send). Un club nomme `"; rm -rf ~` ne casse donc
rien - c'est la meme promesse que celle du crochet lui-meme.
"""

import os
import subprocess
import sys

# Sous Windows, sans ca, une console noire clignote a l'ecran a chaque but.
CREATE_NO_WINDOW = 0x08000000

# De quoi laisser le ballon vivre ses huit secondes ci-dessous, sans jamais
# approcher les trente du crochet.
TIMEOUT = 20.0

# Le ballon de notification de Windows, ecrit en PowerShell parce qu'aucun
# module n'est a installer pour l'avoir - BurntToast et consorts sont des
# dependances, et il n'y en a pas ici. Le script relit BUT_TEXT et BUT_TEAM
# lui-meme : ce qui vient du reseau reste une valeur, jamais du code.
#
# Le `Start-Sleep` n'est pas une politesse : le ballon meurt avec le processus
# qui l'affiche. Huit secondes, parce qu'un fil du crochet reste pris pendant
# ce temps-la et que butbutbut n'en tient que huit a la fois.
POWERSHELL = r"""
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$title = 'BUT !'
if ($env:BUT_TYPE -eq 'cancelled') { $title = 'But refuse par la VAR' }
elseif ($env:BUT_TEAM) { $title = "BUT ! $($env:BUT_TEAM)" }
$icon = New-Object System.Windows.Forms.NotifyIcon
$icon.Icon = [System.Drawing.SystemIcons]::Information
$icon.BalloonTipTitle = $title
$icon.BalloonTipText = $env:BUT_TEXT
$icon.Visible = $true
$icon.ShowBalloonTip(8000)
Start-Sleep -Seconds 8
$icon.Dispose()
"""


def value(name, default=""):
    """Le detail du but, tel que le crochet l'a pose dans l'environnement."""
    return os.environ.get(name, "") or default


def title():
    """Une ligne de titre courte : les centres de notifications tronquent."""
    if value("BUT_TYPE") == "cancelled":
        return "But refuse par la VAR"
    team = value("BUT_TEAM")
    return "BUT ! " + team if team else "BUT !"


def body():
    return value("BUT_TEXT") or "{} {} {}".format(
        value("BUT_HOME", "?"), value("BUT_SCORE", "?"), value("BUT_AWAY", "?"))


def command(platform, head, text):
    """La commande a lancer, en liste : rien n'est recolle dans un shell."""
    if platform.startswith("linux"):
        return ["notify-send", "--app-name=butbutbut", head, text]
    if platform == "darwin":
        # La forme `on run argv` evite d'ecrire le texte dans le script
        # AppleScript, ou une apostrophe suffirait a tout casser.
        script = ('on run argv\n'
                  'display notification (item 1 of argv)'
                  ' with title (item 2 of argv)\n'
                  'end run')
        return ["osascript", "-e", script, text, head]
    if platform == "win32":
        return ["powershell", "-NoProfile", "-NonInteractive",
                "-ExecutionPolicy", "Bypass", "-Command", POWERSHELL]
    return None


def main():
    head, text = title(), body()
    argv = command(sys.platform, head, text)
    if argv is None:
        print("notification : {} n'est pas gere par cette recette"
              .format(sys.platform))
        return 1
    extra = {}
    if sys.platform == "win32":
        extra["creationflags"] = CREATE_NO_WINDOW
    try:
        done = subprocess.run(argv, timeout=TIMEOUT, stdin=subprocess.DEVNULL,
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL, **extra)
    except FileNotFoundError:
        print("notification : {} est introuvable".format(argv[0]))
        return 1
    except subprocess.TimeoutExpired:
        print("notification : {} ne rend pas la main".format(argv[0]))
        return 1
    except Exception as error:
        print("notification : {} ({})".format(argv[0], error))
        return 1
    if done.returncode:
        # notify-send sans session graphique, osascript sans autorisation :
        # le programme est la, mais rien ne s'est affiche. Le dire une fois
        # vaut mieux que de croire la notification partie tous les dimanches.
        print("notification : {} a rendu {}".format(argv[0], done.returncode))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
