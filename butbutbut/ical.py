"""Calendrier iCalendar autonome des prochains matchs."""

from __future__ import annotations

from datetime import datetime, timezone

from . import __version__


def _escape(value) -> str:
    """Echappe une valeur TEXT selon RFC 5545, sans toucher a l'UTF-8."""
    return (str(value or "").replace("\\", "\\\\")
            .replace("\n", "\\n").replace("\r", "")
            .replace(";", "\\;").replace(",", "\\,"))


def _fold(line) -> list:
    """Plie une ligne a 75 octets, espace de continuation compris."""
    rows = []
    current = ""
    for character in line:
        candidate = current + character
        if current and len(candidate.encode("utf-8")) > 75:
            rows.append(current)
            current = " " + character
        else:
            current = candidate
    rows.append(current)
    return rows


def _utc_stamp(value) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _duration(match) -> str:
    sport = getattr(getattr(match, "sport", None), "code", "")
    if sport == "rugby":
        return "PT2H30M"
    if sport == "hockey":
        return "PT3H"
    return "PT2H"


def render(matches, name="butbutbut", generated_at=None) -> str:
    """Produit un calendrier publiable, triable et reinscriptible.

    Les identifiants de la source deviennent les UID : importer une nouvelle
    version du meme calendrier met donc a jour les rencontres au lieu de les
    dupliquer dans les clients qui savent rapprocher les UID.
    """
    generated_at = generated_at or datetime.now(timezone.utc)
    stamp = _utc_stamp(generated_at)
    lines = [
        "BEGIN:VCALENDAR",
        "PRODID:-//boubou666//butbutbut {}//FR".format(__version__),
        "VERSION:2.0",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:{}".format(_escape(name)),
        "X-WR-TIMEZONE:UTC",
    ]
    ordered = sorted(matches, key=lambda match: (
        match.start or datetime.max.replace(tzinfo=timezone.utc),
        str(match.id)))
    for match in ordered:
        if match.start is None:
            continue
        context = [match.league.name]
        for field in ("group_name", "round_name"):
            value = getattr(match, field, "")
            if value:
                context.append(str(value))
        lines.extend((
            "BEGIN:VEVENT",
            "UID:{}@butbutbut.local".format(_escape(match.id)),
            "DTSTAMP:{}".format(stamp),
            "DTSTART:{}".format(_utc_stamp(match.start)),
            "DURATION:{}".format(_duration(match)),
            "SUMMARY:{}".format(_escape(
                "{} – {}".format(match.home, match.away))),
            "DESCRIPTION:{}".format(_escape(" · ".join(context))),
            "CATEGORIES:{}".format(_escape(match.league.name)),
        ))
        venue = str(getattr(match, "venue", "") or "").strip()
        if venue:
            lines.append("LOCATION:{}".format(_escape(venue)))
        lines.extend(("STATUS:CONFIRMED", "TRANSP:TRANSPARENT", "END:VEVENT"))
    lines.append("END:VCALENDAR")
    return "\r\n".join(row for line in lines for row in _fold(line)) + "\r\n"
