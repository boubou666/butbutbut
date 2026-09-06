"""Fabrique de charges utiles ESPN, pour les tests."""

import copy
import json


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


def event(match_id="1", home="Angers", away="Stade Rennais", home_score=0,
          away_score=0, state="in", detail="35'", clock="35'",
          date="2026-09-06T15:15Z", details=(), status_name=""):
    return {
        "id": match_id,
        "competitions": [{
            "id": match_id,
            "date": date,
            "competitors": [
                {"homeAway": "home", "score": str(home_score),
                 "team": {"id": "H" + match_id, "displayName": home,
                          "shortDisplayName": home[:6], "abbreviation": "HOM"}},
                {"homeAway": "away", "score": str(away_score),
                 "team": {"id": "A" + match_id, "displayName": away,
                          "shortDisplayName": away[:6], "abbreviation": "AWA"}},
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
