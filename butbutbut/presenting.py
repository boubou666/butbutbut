"""Quelqu'un d'autre regarde-t-il cet ecran ? Ce que le systeme veut bien dire.

Une carte "BUT" au milieu d'une visio partagee, c'est le bug qu'on ne decouvre
qu'une fois, et devant temoins. La question posee ici n'est donc pas celle de
fullscreen.py ("la carte sera-t-elle visible ?") mais son exact contraire :
"est-ce qu'elle serait vue par trop de monde ?".

Ce qui est detectable, et ce qui ne l'est pas
---------------------------------------------

Windows expose `SHQueryUserNotificationState` (shell32, Vista et au-dela) :
c'est l'API par laquelle Windows repond lui-meme a "est-ce le moment d'afficher
une notification ?". On lui pose donc notre question telle quelle, et on retient
deux de ses reponses :

  - QUNS_PRESENTATION_MODE : mode presentation, celui des parametres de
    presentation de Windows, qu'un videoprojecteur branche declenche ;
  - QUNS_QUIET_TIME : assistant de concentration, autrement dit "ne pas
    deranger". Windows l'allume de lui-meme quand l'ecran est DUPLIQUE - un
    videoprojecteur, une salle de reunion - et c'est aussi ce qu'on allume a la
    main avant une visio.

Ce qui n'est PAS detecte, et il faut le dire plutot que de le laisser croire :
un partage de fenetre ou d'ecran depuis Teams, Zoom ou Meet. Windows n'expose
rien qui le dise, et la seule facon d'y arriver serait de guetter le nom de
classe de la barre flottante de chaque application de visio
("ZPToolBarParentWnd" et compagnie). Cette heuristique-la tombe a la premiere
mise a jour de l'application, et se declenche de travers entre-temps : ne rien
detecter et le dire vaut mieux que detecter parfois, au hasard.

Ce qu'on laisse expres de cote
------------------------------

Les etats de plein ecran (QUNS_BUSY, QUNS_RUNNING_D3D_FULL_SCREEN, QUNS_APP)
ne comptent pas : un jeu en plein ecran n'est pas un partage d'ecran, personne
d'autre ne le regarde, et il a deja son traitement dans fullscreen.py - lequel
laisse partir le son et sait repasser la carte plus tard. Les retenir ici
rendrait butbutbut muet pendant un match joue en plein ecran, c'est-a-dire
exactement quand il sert a quelque chose.

QUNS_NOT_PRESENT (session verrouillee, ecran de veille) ne compte pas non plus,
pour la raison symetrique : une carte que personne ne voit ne derange personne,
et le son est justement ce qu'on veut entendre depuis la cuisine.

Hors de Windows, rien. macOS allume un point orange quand l'ecran est capture
mais ne le dit a aucune API publique ; sous Wayland le partage passe par
xdg-desktop-portal, qui ne repond qu'a celui qui a demande le partage ; X11 ne
sait meme pas qu'un partage existe. `state()` y rend None, et la carte part
comme avant.
"""

from __future__ import annotations

import sys

# Les valeurs de QUERY_USER_NOTIFICATION_STATE, dans l'ordre de l'entete Win32.
NOT_PRESENT = 1
BUSY = 2
D3D_FULL_SCREEN = 3
PRESENTATION_MODE = 4
ACCEPTS_NOTIFICATIONS = 5
QUIET_TIME = 6
APP_FULL_SCREEN = 7

# La raison part au journal, qui reste francais quelle que soit la langue des
# cartes : elle s'ecrit donc ici, en clair, et pas via i18n.
REASONS = {
    PRESENTATION_MODE: "mode presentation",
    QUIET_TIME: "ne pas deranger (assistant de concentration, ecran duplique)",
}


# ------------------------------------------------------------- decision ------

def reason_for(state):
    """La raison de se taire pour cet etat, ou None si l'on peut parler.

    C'est toute la decision, et elle ne depend ni de Windows ni de ctypes :
    c'est ici qu'on peut la verifier. Un etat inconnu - une version de Windows
    qui en ajouterait un - laisse parler : le doute profite au but.
    """
    try:
        return REASONS.get(int(state))
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------- API --------

def supported() -> bool:
    """Vrai la ou la question a une reponse. Windows seulement."""
    return sys.platform == "win32"


def state():
    """L'etat annonce par le systeme, ou None quand on ne sait pas.

    None couvre les deux ignorances, qui ne se ressemblent pas : la plateforme
    qui ne sait pas repondre, et l'appel qui a echoue. Elles menent au meme
    endroit - la carte part - mais l'appelant ne le dit au journal qu'une fois,
    et pas dans les memes termes.
    """
    if not supported():
        return None
    try:
        import ctypes

        # L'etat sort par le pointeur, la fonction ne rend qu'un HRESULT : un
        # code non nul veut dire que rien n'a ete ecrit, surtout pas qu'on est
        # libre de parler. D'ou le None plutot que la valeur laissee a zero.
        found = ctypes.c_int(0)
        code = ctypes.windll.shell32.SHQueryUserNotificationState(
            ctypes.byref(found))
        if code != 0:
            return None
        return int(found.value)
    except Exception:
        return None


def reason():
    """La raison de se taire en ce moment, ou None. Ne leve jamais."""
    return reason_for(state())
