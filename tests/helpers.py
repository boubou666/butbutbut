"""Fabrique de charges utiles ESPN, pour les tests."""

import copy
import json
import struct
import zlib
from datetime import datetime, timedelta, timezone


def goal_detail(team_id, minute="35'", scorer="C. Arcus", own_goal=False,
                penalty=False, index=0):
    return {
        "type": {"id": "70", "text": "Own Goal" if own_goal else "Goal"},
        "clock": {"value": 60.0 * index, "displayValue": minute},
        "team": {"id": team_id},
        "scoreValue": 1,
        "scoringPlay": True,
        "ownGoal": own_goal,
        "penaltyKick": penalty,
        "shootout": False,
        "athletesInvolved": [{"id": "9" + str(index), "shortName": scorer}],
    }


def red_card_detail(team_id, minute="62'", player="J. Lefort", index=0):
    """Un carton rouge : meme tableau `details` qu'un but, autre drapeau."""
    return {
        "type": {"id": "94", "text": "Red Card"},
        "clock": {"value": 60.0 * index, "displayValue": minute},
        "team": {"id": team_id},
        "scoringPlay": False,
        "yellowCard": False,
        "redCard": True,
        "athletesInvolved": [{"id": "7" + str(index), "shortName": player}],
    }


def in_minutes(minutes) -> str:
    """Une date ISO a N minutes d'ici : pour les annonces d'avant-match."""
    when = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    return when.strftime("%Y-%m-%dT%H:%M:%SZ")


def team(name, color="", alternate="", logo=""):
    """Un competiteur, tel que la source le decrit.

    `name` peut etre une chaine (on derive alors un nom court et une
    abreviation plausibles) ou un tuple (nom complet, nom court, abreviation)
    quand un test a besoin des vraies ecritures - "PSG" par exemple.

    Les couleurs et l'ecusson ne sont poses que s'ils sont demandes : la source
    les omet aussi, et le code doit tenir sans.
    """
    if isinstance(name, (tuple, list)):
        display, short, abbr = (list(name) + [None, None])[:3]
    else:
        display, short, abbr = name, name, name[:3].upper()
    entry = {"displayName": display, "shortDisplayName": short or display,
             "abbreviation": abbr or display[:3].upper()}
    if color:
        entry["color"] = color
    if alternate:
        entry["alternateColor"] = alternate
    if logo:
        entry["logo"] = logo
    return entry


def event(match_id="1", home="Angers", away="Stade Rennais", home_score=0,
          away_score=0, state="in", detail="35'", clock="35'",
          date="2026-09-06T15:15Z", details=(), status_name="",
          home_colors=(), away_colors=(), home_logo="", away_logo=""):
    return {
        "id": match_id,
        "competitions": [{
            "id": match_id,
            "date": date,
            "competitors": [
                {"homeAway": "home", "score": str(home_score),
                 "team": dict(team(home, *home_colors, logo=home_logo),
                              id="H" + match_id)},
                {"homeAway": "away", "score": str(away_score),
                 "team": dict(team(away, *away_colors, logo=away_logo),
                              id="A" + match_id)},
            ],
            "status": {"displayClock": clock,
                       "type": {"state": state, "shortDetail": detail,
                                "name": status_name}},
            "details": list(details),
        }],
    }


def payload(*events):
    return {"events": list(events)}


def opener_for(state):
    """Un opener() pour espn.fetch, qui sert state['payload'] a chaque appel."""
    def opener(_url, _timeout):
        return json.dumps(state["payload"]).encode("utf-8")
    return opener


def bump(source, side="away", by=1, details=()):
    """Copie la charge utile en ajoutant `by` but(s) a un cote."""
    after = copy.deepcopy(source)
    competition = after["events"][0]["competitions"][0]
    for competitor in competition["competitors"]:
        if competitor["homeAway"] == side:
            competitor["score"] = str(int(competitor["score"]) + by)
    competition["details"].extend(details)
    return after


class FakeClock:
    """Une horloge murale qu'on avance a la main.

    Un test ne peut pas endormir la machine : on simule le saut de temps que
    la veille ou l'hibernation laisse derriere elle.
    """

    def __init__(self, start=1600000000.0):
        self.now = float(start)

    def __call__(self):
        return self.now

    def jump(self, seconds):
        self.now += float(seconds)
def png_bytes(width=8, height=8):
    """Un vrai PNG, fabrique ici plutot que range en binaire dans le depot.

    Le cache d'ecussons refuse ce qui n'a pas la signature d'un PNG : il faut
    donc de quoi lui donner l'un et l'autre.
    """
    def chunk(tag, data):
        body = tag + data
        return (struct.pack(">I", len(data)) + body
                + struct.pack(">I", zlib.crc32(body) & 0xffffffff))

    rows = b"".join(b"\x00" + b"\xff\x00\x00" * width for _ in range(height))
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(rows))
            + chunk(b"IEND", b""))


class FakeFont:
    """Une police mesurable sans tkinter : largeur fixe par caractere.

    Suffit a tester la geometrie des cartes sur une machine sans ecran.
    """

    def __init__(self, width=8, line=16):
        self.width = width
        self.line = line

    def measure(self, text):
        return len(text) * self.width

    def metrics(self, _what="linespace"):
        return self.line


def fake_fonts(**widths):
    base = {"label": 7, "title": 9, "team": 11, "score": 15,
            "detail": 8, "scorer": 9}
    base.update(widths)
    return {name: FakeFont(width) for name, width in base.items()}
