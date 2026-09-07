"""Le canari lui-meme, sans reseau.

Le programme de `tools/canari.py` parle a ESPN pour de vrai ; ces tests-ci ne
parlent a personne. Ils lui servent des charges utiles fabriquees a la main :
une complete (il doit dire oui), les memes amputees d'une cle ou porteuses
d'une valeur du mauvais type (il doit dire non, et nommer la cle), et une sans
le moindre match (il ne doit pas crier au loup).
"""

import copy
import importlib.util
import io
import json
import os
import unittest

from helpers import event, goal_detail, payload, red_card_detail

# Le canari vit dans tools/, hors du paquet : on le charge par son chemin,
# depuis celui de ce fichier, pour ne dependre d'aucun repertoire courant.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SPEC = importlib.util.spec_from_file_location(
    "canari", os.path.join(ROOT, "tools", "canari.py"))
canari = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(canari)


def board(*events):
    """Une charge utile complete, telle que la source la sert vraiment.

    `helpers` fabrique le minimum que `espn.py` sait lire ; le canari, lui,
    surveille la forme entiere de la reponse - y compris des cles qui ne
    servent qu'en repli (`team.name`, `team.location`) et les drapeaux qui
    accompagnent toujours une action (`redCard` sur un but, `ownGoal` sur une
    expulsion). On les repose donc ici, comme ESPN les envoie.
    """
    raw = payload(*events)
    raw["leagues"] = [{"name": "French Ligue 1", "abbreviation": "FRA.1"}]
    for entry in raw["events"]:
        competition = entry["competitions"][0]
        entry.setdefault("date", competition["date"])
        for competitor in competition["competitors"]:
            team = competitor["team"]
            team.setdefault("name", team["shortDisplayName"])
            team.setdefault("location", team["displayName"])
            team.setdefault("color", "1b458f")
            team.setdefault("alternateColor", "ffffff")
            team.setdefault(
                "logo", "https://a.espncdn.com/i/teamlogos/soccer/500/1.png")
        for detail in competition["details"]:
            for flag in ("scoringPlay", "redCard", "ownGoal", "penaltyKick",
                         "shootout"):
                detail.setdefault(flag, False)
            for athlete in detail.get("athletesInvolved") or []:
                athlete.setdefault("displayName", athlete.get("shortName"))
    return raw


def played(match_id="1"):
    """Un match joue, avec un but et une expulsion a inspecter."""
    return board(event(
        match_id=match_id, home_score=1, away_score=2, state="post",
        detail="FT", clock="90'", status_name="STATUS_FULL_TIME",
        details=[goal_detail("H" + match_id),
                 red_card_detail("A" + match_id)]))


def catalogue(count=3):
    """L'autre endpoint : la liste des equipes, qui valide --teams."""
    return {"sports": [{"leagues": [{"teams": [
        {"team": {"id": str(index),
                  "displayName": "Club " + str(index),
                  "shortDisplayName": "Club" + str(index),
                  "abbreviation": "C" + str(index)}}
        for index in range(count)]}]}]}


def opener_for(live=None, past=None, teams=None, seen=None):
    """Un opener(url, timeout) qui sert la bonne charge utile selon l'URL."""
    def opener(url, _timeout):
        if seen is not None:
            seen.append(url)
        if url.endswith("/teams"):
            body = teams if teams is not None else catalogue()
        elif "dates=" in url:
            body = past
        else:
            body = live
        if body is None:
            raise IOError("rien de simule pour " + url)
        return json.dumps(body).encode("utf-8")
    return opener


def canary(live=None, past=None, teams=None, seen=None, argv=("--leagues",
                                                              "fra.1")):
    """Lance le canari et rend (code de sortie, rapport)."""
    out = io.StringIO()
    code = canari.main(list(argv), opener=opener_for(live, past, teams, seen),
                       out=out)
    return code, out.getvalue()


def without(source, *path):
    """La meme charge utile, amputee d'une cle. Le dernier mot est la cle."""
    copied = copy.deepcopy(source)
    node = copied
    for step in path[:-1]:
        node = node[step]
    node.pop(path[-1], None)
    return copied


class TestHealthyPayload(unittest.TestCase):
    def test_a_complete_payload_is_green(self):
        code, report = canary(live=played())
        self.assertEqual(code, 0, report)
        self.assertIn("VERT", report)
        self.assertIn("0 en defaut, 0 non verifiee(s)", report)

    def test_the_report_names_every_watched_key(self):
        _, report = canary(live=played())
        for path in ("competitor.homeAway", "competitor.score",
                     "competitor.team.displayName", "competitor.team.color",
                     "competition.status.type.state", "detail.scoringPlay",
                     "detail.penaltyKick", "detail.ownGoal",
                     "detail.athletesInvolved[0].shortName",
                     "equipes.teams[].team.abbreviation"):
            self.assertIn(path, report)


class TestMissingKeys(unittest.TestCase):
    """Une cle qui disparait : c'est tout ce que le canari existe pour voir."""

    def amputate(self, *path):
        code, report = canary(live=without(played(), *path))
        self.assertEqual(code, 1, report)
        self.assertIn("MANQUE", report)
        return report

    def test_a_missing_side_is_caught(self):
        report = self.amputate("events", 0, "competitions", 0, "competitors",
                               0, "homeAway")
        self.assertIn("competitor.homeAway", report)

    def test_a_missing_penalty_flag_is_caught(self):
        report = self.amputate("events", 0, "competitions", 0, "details", 0,
                               "penaltyKick")
        self.assertIn("detail.penaltyKick", report)

    def test_a_missing_scorer_is_caught(self):
        """Pas par le compte de cles, mais par le second filet du canari.

        `athletesInvolved` est SAMPLED et non REQUIRED : la source laisse
        parfois une action sans joueur nomme, et crier au loup la-dessus tous
        les matins apprendrait a ignorer le rouge. C'est le re-passage dans
        espn.parse() qui rattrape la disparition - des cles presentes qui ne
        produisent plus rien, c'est exactement ce qu'il surveille.
        """
        code, report = canary(live=without(played(), "events", 0,
                                           "competitions", 0, "details", 0,
                                           "athletesInvolved"))
        self.assertEqual(code, 1, report)
        self.assertIn("aucun buteur nomme", report)

    def test_a_renamed_state_is_caught(self):
        report = self.amputate("events", 0, "competitions", 0, "status",
                               "type", "state")
        self.assertIn("competition.status.type.state", report)

    def test_a_missing_team_name_is_caught(self):
        report = self.amputate("events", 0, "competitions", 0, "competitors",
                               0, "team")
        self.assertIn("competitor.team", report)

    def test_an_emptied_team_catalogue_is_caught(self):
        # Vide, il ferait refuser tous les noms de --teams au demarrage.
        code, report = canary(live=played(), teams={"sports": []})
        self.assertEqual(code, 1, report)
        self.assertIn("equipes.sports", report)


class TestWrongTypes(unittest.TestCase):
    def test_a_score_that_is_not_a_number_is_caught(self):
        raw = played()
        competitor = raw["events"][0]["competitions"][0]["competitors"][0]
        competitor["score"] = "beaucoup"
        code, report = canary(live=raw)
        self.assertEqual(code, 1, report)
        self.assertIn("TYPE", report)
        self.assertIn("competitor.score", report)

    def test_a_flag_that_stops_being_a_boolean_is_caught(self):
        raw = played()
        raw["events"][0]["competitions"][0]["details"][0]["ownGoal"] = "oui"
        code, report = canary(live=raw)
        self.assertEqual(code, 1, report)
        self.assertIn("TYPE", report)
        self.assertIn("detail.ownGoal", report)


class TestNothingToCheck(unittest.TestCase):
    """Un mardi de juillet : rien a verifier n'est pas un echec."""

    def test_an_empty_board_is_not_a_failure(self):
        code, report = canary(live={"events": []}, past={"events": []})
        self.assertEqual(code, 0, report)
        self.assertIn("aucun match a inspecter", report)
        self.assertIn("non verifie", report)
        self.assertNotIn("MANQUE", report)

    def test_a_board_without_any_action_leaves_the_flags_unverified(self):
        # Des matchs a venir : aucun but, donc aucun drapeau a regarder.
        upcoming = board(event(state="pre", status_name="STATUS_SCHEDULED",
                               clock="0'", detail="Sun 6 Sep at 17:00"))
        code, report = canary(live=upcoming, past={"events": []})
        self.assertEqual(code, 0, report)
        for line in report.splitlines():
            if "detail.penaltyKick" in line:
                self.assertIn("non verifie", line)
                break
        else:
            self.fail("detail.penaltyKick absent du rapport")


class TestLookback(unittest.TestCase):
    def test_a_day_without_goals_sends_the_canary_into_the_past(self):
        seen = []
        code, report = canary(live={"events": []}, past=played(), seen=seen)
        self.assertEqual(code, 0, report)
        self.assertTrue(any("dates=" in url for url in seen), seen)
        # Le premier appel est celui du daemon : sans parametre de date.
        self.assertNotIn("dates=", seen[0])
        self.assertIn("rattrapage", report)
        self.assertIn("0 en defaut, 0 non verifiee(s)", report)

    def test_a_day_with_goals_asks_nothing_more(self):
        seen = []
        canary(live=played(), seen=seen)
        self.assertFalse([url for url in seen if "dates=" in url], seen)

    def test_an_explicit_date_is_honoured(self):
        seen = []
        canary(live=played(), seen=seen,
               argv=("--leagues", "fra.1", "--dates", "20250517"))
        self.assertIn("dates=20250517", seen[0])

    def test_the_lookback_window_is_an_espn_range(self):
        import datetime
        window = canari.lookback_range(datetime.date(2026, 9, 7), days=120)
        self.assertEqual(window, "20260510-20260907")


class TestUnreachableSource(unittest.TestCase):
    def test_a_silent_source_is_its_own_verdict(self):
        # Ni vert ni rouge : on n'a rien pu regarder, et ca se dit.
        code, report = canary()
        self.assertEqual(code, 2, report)
        self.assertIn("INJOIGNABLE", report)


class TestCrossCheck(unittest.TestCase):
    """Les cles peuvent etre la sans que le vrai code en tire quoi que ce soit."""

    def test_the_real_parser_is_run_on_what_was_fetched(self):
        raw = played()
        ledger = canari.Ledger()
        tally = canari.inspect_scoreboard(raw, ledger)
        self.assertEqual(tally["goals"], 1)
        self.assertEqual(tally["red_cards"], 1)
        self.assertEqual(canari.cross_check(raw, "fra.1", tally, ledger), [])

    def test_a_goal_without_a_scorer_is_reported(self):
        raw = played()
        for detail in raw["events"][0]["competitions"][0]["details"]:
            detail["athletesInvolved"] = []
        ledger = canari.Ledger()
        tally = canari.inspect_scoreboard(raw, ledger)
        problems = canari.cross_check(raw, "fra.1", tally, ledger)
        self.assertTrue(any("buteur" in problem for problem in problems),
                        problems)

    def test_the_form_the_source_really_writes_is_accepted(self):
        # 90'+9' est ce qu'ESPN ecrit vraiment. Le canari doit se taire dessus.
        raw = played()
        for detail in raw["events"][0]["competitions"][0]["details"]:
            detail["clock"]["displayValue"] = "90'+9'"
        ledger = canari.Ledger()
        tally = canari.inspect_scoreboard(raw, ledger)
        self.assertEqual(canari.cross_check(raw, "fra.1", tally, ledger), [])

    def test_a_clock_that_changes_shape_is_reported(self):
        # La cle est la, la valeur aussi, et plus personne ne sait la lire :
        # c'est exactement ce qui a fait taire le compteur des arrets de jeu.
        raw = played()
        for detail in raw["events"][0]["competitions"][0]["details"]:
            detail["clock"]["displayValue"] = "90:00"
        ledger = canari.Ledger()
        tally = canari.inspect_scoreboard(raw, ledger)
        problems = canari.cross_check(raw, "fra.1", tally, ledger)
        self.assertTrue(any("horloge" in problem for problem in problems),
                        problems)

    def test_a_hockey_clock_is_not_held_to_a_football_minute(self):
        # 12:34 est l'horloge normale d'un match de hockey : illisible comme
        # minute de jeu, et ce n'est pas une anomalie.
        raw = played()
        for detail in raw["events"][0]["competitions"][0]["details"]:
            detail["clock"]["displayValue"] = "12:34"
        ledger = canari.Ledger()
        tally = canari.inspect_scoreboard(raw, ledger)
        problems = canari.cross_check(raw, "nhl", tally, ledger)
        self.assertFalse(any("horloge" in problem for problem in problems),
                         problems)


class TestDig(unittest.TestCase):
    def test_it_walks_dotted_paths_and_indexes(self):
        source = {"sports": [{"leagues": [{"teams": [1, 2]}]}]}
        self.assertEqual(canari.dig(source, "sports.0.leagues.0.teams"),
                         (True, [1, 2]))

    def test_a_missing_link_is_not_a_crash(self):
        self.assertEqual(canari.dig({"a": {"b": 1}}, "a.c.d"), (False, None))
        self.assertEqual(canari.dig({"a": []}, "a.0"), (False, None))


if __name__ == "__main__":
    unittest.main()
