"""Enumeration des ecrans, pour poser la carte de score au bon endroit.

tkinter ne sait pas decrire une configuration multi-ecrans : `winfo_screenwidth()`
renvoie l'ecran principal (Windows, macOS) ou tout le bureau virtuel d'un bloc
(X11), ce qui collerait la carte a cheval entre deux dalles. On interroge donc
le systeme :

  - Windows : EnumDisplayMonitors + GetMonitorInfoW (zone de travail, hors barre
    des taches)
  - Linux   : `xrandr --listmonitors`
  - macOS   : CoreGraphics (CGGetActiveDisplayList + CGDisplayBounds)

Chaque methode retombe proprement sur un ecran unique si elle echoue.
"""

from __future__ import annotations

import re
import subprocess
import sys

from .i18n import tr

# Coins possibles pour la carte, et la marge qu'on garde avec le bord.
CORNERS = ("bottom-right", "bottom-left", "top-right", "top-left", "center")
MARGIN = 24


class Monitor:
    """Un ecran : position et taille en pixels, dans le bureau virtuel."""

    __slots__ = ("x", "y", "width", "height", "primary", "name")

    def __init__(self, x, y, width, height, primary=False, name=""):
        self.x = int(x)
        self.y = int(y)
        self.width = int(width)
        self.height = int(height)
        self.primary = bool(primary)
        self.name = name or "ecran"

    def place(self, width: int, height: int, corner: str = "bottom-right",
              margin: int = MARGIN):
        """Coordonnees ou poser une fenetre width x height sur cet ecran."""
        corner = (corner or "bottom-right").strip().lower()

        if corner == "center":
            return (self.x + (self.width - width) // 2,
                    self.y + (self.height - height) // 2)

        left = corner.endswith("left")
        top = corner.startswith("top")

        x = self.x + margin if left else self.x + self.width - width - margin
        y = self.y + margin if top else self.y + self.height - height - margin

        # On ne sort jamais de l'ecran, meme si la carte est plus large que lui.
        x = max(self.x, min(x, self.x + max(0, self.width - width)))
        y = max(self.y, min(y, self.y + max(0, self.height - height)))
        return (x, y)

    def __repr__(self):
        flag = "*" if self.primary else " "
        return "<Monitor {}{} {}x{}+{}+{}>".format(
            flag, self.name, self.width, self.height, self.x, self.y)


# ------------------------------------------------------------- Windows -------

def _windows_monitors() -> list:
    import ctypes
    from ctypes import wintypes

    class RECT(ctypes.Structure):
        _fields_ = [
            ("left", ctypes.c_long),
            ("top", ctypes.c_long),
            ("right", ctypes.c_long),
            ("bottom", ctypes.c_long),
        ]

    class MONITORINFOEXW(ctypes.Structure):
        _fields_ = [
            ("cbSize", ctypes.c_ulong),
            ("rcMonitor", RECT),
            ("rcWork", RECT),
            ("dwFlags", ctypes.c_ulong),
            ("szDevice", ctypes.c_wchar * 32),
        ]

    MONITORINFOF_PRIMARY = 0x00000001
    user32 = ctypes.windll.user32
    found = []

    callback_type = ctypes.WINFUNCTYPE(
        ctypes.c_int,
        ctypes.c_void_p,               # HMONITOR
        ctypes.c_void_p,               # HDC
        ctypes.POINTER(RECT),          # LPRECT
        ctypes.c_ssize_t,              # LPARAM
    )

    def callback(handle, _hdc, _rect, _param):
        info = MONITORINFOEXW()
        info.cbSize = ctypes.sizeof(MONITORINFOEXW)
        if user32.GetMonitorInfoW(ctypes.c_void_p(handle), ctypes.byref(info)):
            # rcWork exclut la barre des taches : la carte ne se cache pas dessous
            work = info.rcWork
            found.append(
                Monitor(
                    work.left,
                    work.top,
                    work.right - work.left,
                    work.bottom - work.top,
                    primary=bool(info.dwFlags & MONITORINFOF_PRIMARY),
                    name=info.szDevice,
                )
            )
        return 1

    user32.EnumDisplayMonitors(
        wintypes.HDC(), None, callback_type(callback), ctypes.c_ssize_t(0)
    )
    return found


# --------------------------------------------------------------- Linux -------

_XRANDR_LINE = re.compile(
    r"^\s*(?P<index>\d+):\s+\+(?P<primary>\*?)(?P<name>\S+)\s+"
    r"(?P<width>\d+)/\d+x(?P<height>\d+)/\d+\+(?P<x>-?\d+)\+(?P<y>-?\d+)"
)


def _linux_monitors() -> list:
    try:
        out = subprocess.run(
            ["xrandr", "--listmonitors"],
            capture_output=True, text=True, timeout=4,
        )
    except Exception:
        return []
    if out.returncode != 0:
        return []

    found = []
    for line in out.stdout.splitlines():
        match = _XRANDR_LINE.match(line)
        if not match:
            continue
        found.append(
            Monitor(
                match.group("x"),
                match.group("y"),
                match.group("width"),
                match.group("height"),
                primary=bool(match.group("primary")),
                name=match.group("name"),
            )
        )
    return found


# --------------------------------------------------------------- macOS -------

def _macos_monitors() -> list:
    import ctypes
    import ctypes.util

    class CGPoint(ctypes.Structure):
        _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]

    class CGSize(ctypes.Structure):
        _fields_ = [("width", ctypes.c_double), ("height", ctypes.c_double)]

    class CGRect(ctypes.Structure):
        _fields_ = [("origin", CGPoint), ("size", CGSize)]

    path = ctypes.util.find_library("CoreGraphics")
    if not path:
        return []
    core = ctypes.cdll.LoadLibrary(path)

    max_displays = 16
    displays = (ctypes.c_uint32 * max_displays)()
    count = ctypes.c_uint32(0)
    if core.CGGetActiveDisplayList(max_displays, displays, ctypes.byref(count)) != 0:
        return []

    core.CGDisplayBounds.restype = CGRect
    core.CGDisplayBounds.argtypes = [ctypes.c_uint32]
    core.CGMainDisplayID.restype = ctypes.c_uint32

    main_id = core.CGMainDisplayID()
    found = []
    for i in range(count.value):
        display_id = displays[i]
        bounds = core.CGDisplayBounds(display_id)
        found.append(
            Monitor(
                bounds.origin.x,
                bounds.origin.y,
                bounds.size.width,
                bounds.size.height,
                primary=(display_id == main_id),
                name="display-{}".format(display_id),
            )
        )
    return found


# ---------------------------------------------------------------- API --------

def monitors(fallback_width: int = 1920, fallback_height: int = 1080) -> list:
    """Tous les ecrans. Jamais vide : au pire un seul, aux dimensions donnees."""
    detect = {
        "win32": _windows_monitors,
        "darwin": _macos_monitors,
    }.get(sys.platform, _linux_monitors)

    try:
        found = detect()
    except Exception:
        found = []

    found = [m for m in found if m.width > 0 and m.height > 0]
    if not found:
        found = [Monitor(0, 0, fallback_width, fallback_height, primary=True, name="ecran")]
    return found


def pick(found: list, preference=None) -> Monitor:
    """Choisit un ecran.

    preference : None / "primary" -> l'ecran principal ; un entier (ou sa forme
    texte) -> l'ecran de cet index, borne a la liste.
    """
    if not found:
        return Monitor(0, 0, 1920, 1080, primary=True)

    if preference in (None, "", "primary", "main", "principal"):
        for monitor in found:
            if monitor.primary:
                return monitor
        return found[0]

    try:
        index = int(preference)
    except (TypeError, ValueError):
        return found[0]
    return found[max(0, min(index, len(found) - 1))]


def describe(found: list) -> str:
    if len(found) == 1:
        monitor = found[0]
        return tr("1 ecran ({}x{})", monitor.width, monitor.height)
    parts = ", ".join(
        "{}:{} {}x{}{}".format(i, m.name, m.width, m.height, "*" if m.primary else "")
        for i, m in enumerate(found)
    )
    return tr("{} ecrans [{}]", len(found), parts)
