"""Detecte qu'une fenetre plein ecran masque l'ecran ou la carte doit s'afficher.

Une carte est une fenetre `topmost` : elle passe au-dessus des fenetres
ordinaires, mais pas au-dessus d'un jeu ou d'un lecteur video en plein ecran.
Le but tombe alors dans le vide, sans que rien ne le signale - c'est ce qu'une
capture d'ecran de test a montre : le processus tournait, la carte etait
poussee, l'ecran ne montrait que le jeu.

On regarde donc, juste avant d'afficher, si la fenetre au premier plan couvre
tout l'ecran vise. Deux indices, tous deux necessaires :

  - la geometrie : la fenetre couvre la dalle ENTIERE (rcMonitor), pas la seule
    zone de travail (rcWork) que renvoie screens.py. Une fenetre maximisee
    s'arrete au-dessus de la barre des taches ;
  - les styles : une fenetre qui garde sa barre de titre (WS_CAPTION) ou sa
    poignee de redimensionnement (WS_THICKFRAME) est au mieux maximisee. Le
    style seul ne suffit pas non plus : le bureau et l'hote de saisie Windows
    sont eux aussi sans decoration et grands comme l'ecran.

Mesure faite sur la machine de test (Windows 10, deux dalles 1920x1080, barre
des taches sur les deux) :

    fenetre maximisee   rect = (  -8,  -8, 1928, 1048)  cap=1 thick=1
    plein ecran         rect = (1920,   0, 3840, 1080)  cap=0 thick=0
    dalle (rcMonitor)   rect = (1920,   0, 3840, 1080)
    zone de travail     rect = (1920,   0, 3840, 1040)

Une fenetre maximisee deborde de 8 pixels sur les cotes (bordures de
redimensionnement invisibles) : la comparaison tolere donc un peu de jeu.

Hors de Windows, rien : X11, Wayland et macOS ne repondent pas a cette question
de facon fiable et portable, et une detection qui se trompe serait pire que pas
de detection du tout. `covers()` y renvoie toujours faux.
"""

from __future__ import annotations

import sys

# Une fenetre plein ecran ne tombe pas toujours au pixel pres sur la dalle :
# bordures invisibles d'un cote, arrondis de mise a l'echelle de l'autre.
EDGE_TOLERANCE = 8

WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000
DECORATIONS = WS_CAPTION | WS_THICKFRAME

# Le bureau couvre tout l'ecran et n'a aucune decoration : il passerait pour un
# jeu en plein ecran des que l'utilisateur clique sur "afficher le bureau".
SHELL_CLASSES = ("Progman", "WorkerW")


# ------------------------------------------------------------- decision ------

def covers_screen(window, screen, style=None, tolerance: int = EDGE_TOLERANCE) -> bool:
    """Vrai si `window` masque tout `screen`.

    Les deux rectangles sont des quadruplets (gauche, haut, droite, bas) en
    pixels du bureau virtuel ; `screen` est la dalle entiere, barre des taches
    comprise. `style` est le GWL_STYLE de la fenetre quand on le connait.

    C'est toute la decision, et elle ne depend ni d'un ecran ni de ctypes :
    c'est ici qu'on peut la verifier.
    """
    if style is not None and int(style) & DECORATIONS:
        return False

    try:
        left, top, right, bottom = (int(value) for value in window)
        edge_l, edge_t, edge_r, edge_b = (int(value) for value in screen)
    except (TypeError, ValueError):
        return False

    # Une fenetre reduite a rien, ou un ecran sans surface : rien a masquer.
    if right <= left or bottom <= top or edge_r <= edge_l or edge_b <= edge_t:
        return False

    tolerance = max(0, int(tolerance))
    return (left <= edge_l + tolerance
            and top <= edge_t + tolerance
            and right >= edge_r - tolerance
            and bottom >= edge_b - tolerance)


def is_shell_class(name) -> bool:
    """Vrai pour les fenetres du bureau, qu'on ne compte jamais comme plein ecran."""
    return bool(name) and str(name) in SHELL_CLASSES


def monitor_rect(monitor) -> tuple:
    """Le rectangle d'un screens.Monitor, tel qu'il le connait (zone de travail)."""
    return (monitor.x, monitor.y,
            monitor.x + monitor.width, monitor.y + monitor.height)


# ------------------------------------------------------------- Windows -------

def _user32():
    """user32 et les structures Win32 dont on a besoin.

    Les fonctions qui rendent un HANDLE sont declarees : sans restype, ctypes
    tronque la valeur a 32 bits, ce qui suffit aux HWND d'aujourd'hui mais
    n'est garanti nulle part.
    """
    import ctypes

    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

    class RECT(ctypes.Structure):
        _fields_ = [
            ("left", ctypes.c_long),
            ("top", ctypes.c_long),
            ("right", ctypes.c_long),
            ("bottom", ctypes.c_long),
        ]

    class MONITORINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", ctypes.c_ulong),
            ("rcMonitor", RECT),
            ("rcWork", RECT),
            ("dwFlags", ctypes.c_ulong),
        ]

    user32 = ctypes.windll.user32
    for name in ("GetForegroundWindow", "GetShellWindow"):
        getattr(user32, name).restype = ctypes.c_void_p
    user32.MonitorFromPoint.restype = ctypes.c_void_p
    user32.MonitorFromPoint.argtypes = [POINT, ctypes.c_ulong]
    return ctypes, user32, POINT, RECT, MONITORINFO


def _screen_rect(monitor) -> tuple:
    """La dalle entiere qui porte `monitor`, barre des taches comprise.

    screens.py renvoie la zone de travail : une fenetre maximisee la couvre
    entierement et passerait pour du plein ecran. On redemande donc a Windows
    le rcMonitor de la dalle qui contient le centre de cette zone.
    """
    fallback = monitor_rect(monitor)
    try:
        ctypes, user32, POINT, _RECT, MONITORINFO = _user32()

        MONITOR_DEFAULTTONEAREST = 2
        middle = POINT(int(monitor.x + monitor.width // 2),
                       int(monitor.y + monitor.height // 2))
        handle = user32.MonitorFromPoint(middle, MONITOR_DEFAULTTONEAREST)
        if not handle:
            return fallback

        info = MONITORINFO()
        info.cbSize = ctypes.sizeof(MONITORINFO)
        if not user32.GetMonitorInfoW(ctypes.c_void_p(handle), ctypes.byref(info)):
            return fallback
        area = info.rcMonitor
        return (area.left, area.top, area.right, area.bottom)
    except Exception:
        return fallback


def _foreground_window():
    """(rectangle, style) de la fenetre au premier plan, ou None.

    None des qu'il n'y a rien a comparer : pas de premier plan, fenetre reduite
    ou invisible, ou bureau.
    """
    ctypes, user32, _POINT, RECT, _MONITORINFO = _user32()

    hwnd = user32.GetForegroundWindow()
    if not hwnd or hwnd == user32.GetShellWindow():
        return None
    handle = ctypes.c_void_p(hwnd)
    if not user32.IsWindowVisible(handle) or user32.IsIconic(handle):
        return None

    name = ctypes.create_unicode_buffer(64)
    user32.GetClassNameW(handle, name, 64)
    if is_shell_class(name.value):
        return None

    area = RECT()
    if not user32.GetWindowRect(handle, ctypes.byref(area)):
        return None

    GWL_STYLE = -16
    style = user32.GetWindowLongW(handle, GWL_STYLE) & 0xFFFFFFFF
    return ((area.left, area.top, area.right, area.bottom), style)


# ---------------------------------------------------------------- API --------

def supported() -> bool:
    """Vrai la ou la detection existe. Windows seulement."""
    return sys.platform == "win32"


def covers(monitor) -> bool:
    """Vrai si une fenetre plein ecran occupe `monitor` en ce moment.

    Ne leve jamais et ne bloque jamais : un appel Win32 qui echoue rend faux,
    et une carte s'affiche comme avant. C'est le sens du doute ici - mieux vaut
    une carte peut-etre visible qu'une carte retenue pour rien.
    """
    if not supported():
        return False
    try:
        found = _foreground_window()
        if found is None:
            return False
        window, style = found
        return covers_screen(window, _screen_rect(monitor), style)
    except Exception:
        return False
