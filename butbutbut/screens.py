"""ButButBut's monitor policy on top of :mod:`desktop_overlay`.

The shared package owns operating-system enumeration and geometry. This module
keeps the score card's primary-screen default, French status text, and legacy
corner-placement method.
"""

from __future__ import annotations

from desktop_overlay import geometry as _geometry
from desktop_overlay.monitors import enumerate_monitors

from .i18n import tr

CORNERS = _geometry.CORNERS
MARGIN = 24


class Monitor(_geometry.Monitor):
    """A shared monitor rectangle with the score card's placement method."""

    def __init__(self, x, y, width, height, primary=False, name=""):
        super().__init__(
            x, y, width, height, primary=primary, name=name or "ecran"
        )

    def place(self, width: int, height: int, corner: str = "bottom-right",
              margin: int = MARGIN):
        return self.corner_position(
            width, height, corner=corner, margin=margin
        )


def _local(monitor: _geometry.Monitor) -> Monitor:
    if isinstance(monitor, Monitor):
        return monitor
    return Monitor(
        monitor.x,
        monitor.y,
        monitor.width,
        monitor.height,
        primary=monitor.primary,
        name=monitor.name,
    )


def monitors(fallback_width: int = 1920,
             fallback_height: int = 1080) -> list[Monitor]:
    """Return every active screen, with one fallback when detection fails."""
    return [
        _local(monitor)
        for monitor in enumerate_monitors(fallback_width, fallback_height)
    ]


def pick(found: list[Monitor], preference=None) -> Monitor:
    """Choose a monitor using ButButBut's primary-screen default policy."""
    if found and preference not in (None, "", "primary", "main", "principal"):
        try:
            int(preference)
        except (TypeError, ValueError):
            return found[0]
    return _local(
        _geometry.pick_monitor(found, preference, default="primary")
    )


def describe(found: list[Monitor]) -> str:
    if len(found) == 1:
        monitor = found[0]
        return tr("1 ecran ({}x{})", monitor.width, monitor.height)
    parts = ", ".join(
        "{}:{} {}x{}{}".format(
            index,
            monitor.name,
            monitor.width,
            monitor.height,
            "*" if monitor.primary else "",
        )
        for index, monitor in enumerate(found)
    )
    return tr("{} ecrans [{}]", len(found), parts)