import unittest
from datetime import datetime, timezone

from butbutbut import espn, leagues

from helpers import event, goal_detail, opener_for, payload

LIGUE1 = leagues.BY_SLUG["fra.1"]


class TestParse(unittest.TestCase):
    def test_reads_teams_scores_and_state(self):
        matches = espn.parse(payload(event(home_score=1, away_score=2)), LIGUE1)
        self.assertEqual(len(matches), 1)
        match = matches[0]
        self.assertEqual(match.home, "Angers")
        self.assertEqual(match.away, "Stade Rennais")
        self.assertEqual((match.home_score, match.away_score), (1, 2))
        self.assertTrue(match.live)
        self.assertFalse(match.finished)
        self.assertEqual(match.score_line(), "Angers 1 - 2 Stade Rennais")
        self.assertIs(match.league, LIGUE1)

    def test_long_names_fall_back_to_short_name(self):
        matches = espn.parse(
            payload(event(home="Borussia Monchengladbach")), LIGUE1)
        self.assertEqual(matches[0].home, "Boruss")

    def test_missing_score_is_zero_not_a_crash(self):
        raw = payload(event())
        raw["events"][0]["competitions"][0]["competitors"][0].pop("score")
        self.assertEqual(espn.parse(raw, LIGUE1)[0].home_score, 0)

    def test_broken_events_are_skipped_not_fatal(self):
        raw = payload({"id": "x"}, event(match_id="7"), "pas un dict")
        matches = espn.parse(raw, LIGUE1)
        self.assertEqual([m.id for m in matches], ["7"])

    def test_event_without_two_sides_is_skipped(self):
        raw = payload(event())
        raw["events"][0]["competitions"][0]["competitors"].pop()
        self.assertEqual(espn.parse(raw, LIGUE1), [])

    def test_kickoff_is_parsed_as_utc(self):
        matches = espn.parse(payload(event(date="2026-09-06T15:15Z")), LIGUE1)
        self.assertEqual(matches[0].start,
                         datetime(2026, 9, 6, 15, 15, tzinfo=timezone.utc))

    def test_unreadable_kickoff_gives_none(self):
        matches = espn.parse(payload(event(date="bientot")), LIGUE1)
        self.assertIsNone(matches[0].start)
        self.assertIsNone(matches[0].seconds_until_kickoff())

    def test_seconds_until_kickoff(self):
        matches = espn.parse(payload(event(date="2026-09-06T15:15Z")), LIGUE1)
        now = datetime(2026, 9, 6, 15, 0, tzinfo=timezone.utc)
        self.assertAlmostEqual(matches[0].seconds_until_kickoff(now), 900.0)


class TestPlays(unittest.TestCase):
    def test_scoring_plays_are_collected_with_scorer(self):
        details = (goal_detail("H1", "35'", "C. Arcus"),
                   {"type": {"text": "Yellow Card"}, "scoringPlay": False})
        match = espn.parse(payload(event(details=details)), LIGUE1)[0]
        self.assertEqual(len(match.plays), 1)
        play = match.plays[0]
        self.assertEqual(play.scorer, "C. Arcus")
        self.assertEqual(play.minute, "35'")
        self.assertEqual(play.summary(), "But de C. Arcus (35')")
        self.assertEqual(play.prefix(), "But")

    def test_own_goal_and_penalty_wording(self):
        details = (goal_detail("H1", "17'", "J. Lefort", own_goal=True, index=1),
                   goal_detail("A1", "58'", "A. Kalimuendo", penalty=True, index=2))
        match = espn.parse(payload(event(details=details)), LIGUE1)[0]
        self.assertEqual(match.plays[0].summary(),
                         "But contre son camp de J. Lefort (17')")
        self.assertEqual(match.plays[1].summary(),
                         "Penalty de A. Kalimuendo (58')")

    def test_plays_are_filtered_by_team(self):
        details = (goal_detail("H1", index=1), goal_detail("A1", index=2))
        match = espn.parse(payload(event(details=details)), LIGUE1)[0]
        self.assertEqual(len(match.plays_for("H1")), 1)
        self.assertEqual(len(match.plays_for("A1")), 1)

    def test_play_without_athlete_still_parses(self):
        detail = goal_detail("H1")
        detail.pop("athletesInvolved")
        match = espn.parse(payload(event(details=(detail,))), LIGUE1)[0]
        self.assertEqual(match.plays[0].scorer, "")
        self.assertEqual(match.plays[0].summary(), "But (35')")

    def test_keys_are_stable_across_two_reads(self):
        raw = payload(event(details=(goal_detail("H1"),)))
        first = espn.parse(raw, LIGUE1)[0]
        second = espn.parse(raw, LIGUE1)[0]
        self.assertEqual([p.key for p in first.plays],
                         [p.key for p in second.plays])


class TestFetch(unittest.TestCase):
    def test_fetch_goes_through_the_opener(self):
        state = {"payload": payload(event())}
        matches = espn.scoreboard(LIGUE1, opener=opener_for(state))
        self.assertEqual(matches[0].home, "Angers")

    def test_network_failure_becomes_source_error(self):
        def broken(_url, _timeout):
            raise OSError("pas de reseau")

        with self.assertRaises(espn.SourceError):
            espn.fetch("fra.1", opener=broken)

    def test_garbage_json_becomes_source_error(self):
        with self.assertRaises(espn.SourceError):
            espn.fetch("fra.1", opener=lambda *_: b"<html>oups</html>")

    def test_non_dict_json_becomes_source_error(self):
        with self.assertRaises(espn.SourceError):
            espn.fetch("fra.1", opener=lambda *_: b"[1, 2, 3]")


if __name__ == "__main__":
    unittest.main()
