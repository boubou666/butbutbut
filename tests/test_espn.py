import unittest
from datetime import datetime, timezone

from butbutbut import espn, leagues

from helpers import event, goal_detail, opener_for, payload, red_card_detail

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
        matches = espn.parse(payload(event(
            home=("Borussia Monchengladbach", "M'gladbach", "BMG"))), LIGUE1)
        self.assertEqual(matches[0].home, "M'gladbach")

    def test_every_writing_of_a_team_is_kept(self):
        # C'est ce que le filtre par equipe interroge.
        matches = espn.parse(payload(event(
            home=("Paris Saint-Germain", "PSG", "PSG"))), LIGUE1)
        self.assertIn("Paris Saint-Germain", matches[0].home_names)
        self.assertIn("PSG", matches[0].home_names)

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


class TestTeamLook(unittest.TestCase):
    """Ecusson et couleurs : ESPN les publie, on les lit comme le reste."""

    def parse(self, **kwargs):
        return espn.parse(payload(event(**kwargs)), LIGUE1)[0]

    def test_colours_are_normalised_from_the_espn_writing(self):
        match = self.parse(home_colors=("0000BF", "fafafc"),
                           away_colors=("ef2f24", "FFFFFF"))
        self.assertEqual((match.home_color, match.home_alt),
                         ("#0000bf", "#fafafc"))
        self.assertEqual((match.away_color, match.away_alt),
                         ("#ef2f24", "#ffffff"))

    def test_the_logo_url_is_kept_as_is(self):
        url = "https://a.espncdn.com/i/teamlogos/soccer/500/170.png"
        self.assertEqual(self.parse(home_logo=url).home_logo, url)

    def test_a_team_without_colours_or_logo_is_not_a_problem(self):
        match = self.parse()
        self.assertEqual((match.home_color, match.home_alt), ("", ""))
        self.assertEqual((match.home_logo, match.away_logo), ("", ""))

    def test_a_broken_colour_is_dropped_rather_than_passed_on(self):
        match = self.parse(home_colors=("transparent", "0a4"))
        self.assertEqual((match.home_color, match.home_alt), ("", "#00aa44"))

    def test_only_http_logos_are_accepted(self):
        for url in ("ftp://ailleurs/1.png", "javascript:alert(1)",
                    "/i/teamlogos/1.png", "   "):
            self.assertEqual(self.parse(home_logo=url).home_logo, "", url)

    def test_the_logos_list_is_the_fallback(self):
        raw = payload(event())
        team = raw["events"][0]["competitions"][0]["competitors"][0]["team"]
        team["logos"] = [{"href": "https://exemple/ecusson.png"}]
        self.assertEqual(espn.parse(raw, LIGUE1)[0].home_logo,
                         "https://exemple/ecusson.png")

    def test_a_logo_can_be_rebuilt_from_the_team_number(self):
        self.assertEqual(espn.logo_url("170"),
                         "https://a.espncdn.com/i/teamlogos/soccer/500/170.png")


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


class TestRedCards(unittest.TestCase):
    """Les expulsions vivent dans le meme tableau `details` que les buts."""

    def test_red_cards_are_kept_apart_from_the_goals(self):
        details = (goal_detail("H1", "35'", "C. Arcus", index=1),
                   red_card_detail("A1", "62'", "J. Lefort", index=2),
                   {"type": {"text": "Yellow Card"}, "scoringPlay": False})
        match = espn.parse(payload(event(details=details)), LIGUE1)[0]

        self.assertEqual([p.scorer for p in match.plays], ["C. Arcus"])
        self.assertEqual([p.scorer for p in match.red_cards], ["J. Lefort"])
        card = match.red_cards[0]
        self.assertTrue(card.red_card)
        self.assertEqual(card.minute, "62'")
        self.assertEqual(card.prefix(), "Carton rouge")
        self.assertEqual(card.summary(), "Carton rouge pour J. Lefort (62')")

    def test_a_match_without_expulsion_has_an_empty_list(self):
        match = espn.parse(payload(event(details=(goal_detail("H1"),))), LIGUE1)[0]
        self.assertEqual(match.red_cards, [])

    def test_keys_are_stable_across_two_reads(self):
        raw = payload(event(details=(goal_detail("H1", index=1),
                                     red_card_detail("A1", index=2))))
        first = espn.parse(raw, LIGUE1)[0]
        second = espn.parse(raw, LIGUE1)[0]
        self.assertEqual([p.key for p in first.red_cards],
                         [p.key for p in second.red_cards])
        # Un but et une expulsion de la meme equipe ne partagent pas de cle.
        self.assertNotEqual(first.plays[0].key, first.red_cards[0].key)

    def test_the_side_of_a_red_card_is_found_from_its_team(self):
        match = espn.parse(payload(event(
            details=(red_card_detail("A1"),))), LIGUE1)[0]
        self.assertEqual(match.side_of(match.red_cards[0].team_id), "away")
        self.assertEqual(match.side_of("H1"), "home")
        self.assertEqual(match.side_of(""), "")


class TestPhase(unittest.TestCase):
    """La phase du match, lue dans status.type.name."""

    def test_the_states_espn_actually_returns(self):
        for state, name, expected in (
                ("pre", "STATUS_SCHEDULED", espn.SCHEDULED),
                ("in", "STATUS_FIRST_HALF", espn.PLAYING),
                ("in", "STATUS_HALFTIME", espn.HALFTIME),
                ("in", "STATUS_SECOND_HALF", espn.PLAYING),
                ("post", "STATUS_FULL_TIME", espn.FINAL)):
            self.assertEqual(espn.phase_of(state, name), expected, name)

    def test_extra_time_halftime_counts_as_halftime(self):
        self.assertEqual(espn.phase_of("in", "STATUS_EXTRA_TIME_HALFTIME"),
                         espn.HALFTIME)

    def test_shootout_is_still_playing(self):
        self.assertEqual(espn.phase_of("in", "STATUS_SHOOTOUT"), espn.PLAYING)

    def test_a_match_that_is_not_happening_is_unknown(self):
        for name in ("STATUS_POSTPONED", "STATUS_CANCELED", "STATUS_ABANDONED",
                     "STATUS_DELAYED", "STATUS_SUSPENDED"):
            self.assertEqual(espn.phase_of("pre", name), espn.UNKNOWN, name)

    def test_missing_status_name_falls_back_on_the_state(self):
        self.assertEqual(espn.phase_of("in", ""), espn.PLAYING)
        self.assertEqual(espn.phase_of("pre", None), espn.SCHEDULED)
        self.assertEqual(espn.phase_of("post", ""), espn.FINAL)
        self.assertEqual(espn.phase_of("n'importe quoi", ""), espn.UNKNOWN)

    def test_the_match_carries_its_phase(self):
        match = espn.parse(payload(event(
            state="in", status_name="STATUS_HALFTIME")), LIGUE1)[0]
        self.assertEqual(match.status_name, "STATUS_HALFTIME")
        self.assertEqual(match.phase, espn.HALFTIME)
        self.assertTrue(match.live)      # la mi-temps, c'est toujours "in"


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
