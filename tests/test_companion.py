import unittest

from butbutbut import companion


class TestBind(unittest.TestCase):
    def test_the_default_is_local_only(self):
        self.assertEqual(companion.parse_bind(""), ("127.0.0.1", 8765))

    def test_a_port_stays_local(self):
        self.assertEqual(companion.parse_bind("9000"), ("127.0.0.1", 9000))

    def test_lan_access_must_be_explicit(self):
        self.assertEqual(companion.parse_bind("0.0.0.0:9000"),
                         ("0.0.0.0", 9000))

    def test_an_invalid_port_is_refused(self):
        with self.assertRaises(companion.Invalid):
            companion.parse_bind("70000")


class TestPage(unittest.TestCase):
    def test_the_page_has_no_remote_resource(self):
        for page in (companion.PAGE, companion.MATCH_PAGE,
                     companion.COMPETITION_PAGE, companion.TEAM_PAGE,
                     companion.HEAD_TO_HEAD_PAGE):
            self.assertNotIn("https://", page)
            self.assertNotIn("http://", page)
        self.assertIn("/api/state", companion.PAGE)
        self.assertIn("/api/sync", companion.PAGE)
        self.assertIn("/souvenir?id=", companion.PAGE)
        self.assertIn("/match?id=", companion.PAGE)
        self.assertIn("/api/v1/match?id=", companion.MATCH_PAGE)
        self.assertIn("/competition?id=", companion.MATCH_PAGE)
        self.assertIn("/api/v1/competition?id=", companion.COMPETITION_PAGE)
        self.assertIn("/team?id=", companion.MATCH_PAGE)
        self.assertIn("/team?id=", companion.COMPETITION_PAGE)
        self.assertIn("/api/v1/team?id=", companion.TEAM_PAGE)
        self.assertIn("/head-to-head?team=", companion.MATCH_PAGE)
        self.assertIn("/api/v1/head-to-head?team=",
                      companion.HEAD_TO_HEAD_PAGE)
        self.assertIn("Ouvrir et enregistrer la carte", companion.PAGE)

    def test_a_stream_delay_redacts_a_live_match(self):
        match = {
            "external_id": "401", "status": "live", "clock": "67'",
            "home_score": 2, "away_score": 1, "events": [{"kind": "goal"}],
            "competition": {"name": "Ligue 1"},
            "home_team": {"name": "Angers"}, "away_team": {"name": "Lille"},
        }
        payload = companion.match_center_payload(
            match, {"stream_delay": 90})
        self.assertTrue(payload["spoiler_free"])
        self.assertNotIn("home_score", payload["match"])
        self.assertNotIn("clock", payload["match"])
        self.assertNotIn("events", payload["match"])
        self.assertEqual(payload["match"]["home_team"]["name"], "Angers")

    def test_a_match_is_complete_without_a_stream_delay(self):
        match = {"external_id": "401", "status": "live", "home_score": 2}
        payload = companion.match_center_payload(match, {"stream_delay": 0})
        self.assertFalse(payload["spoiler_free"])
        self.assertIs(payload["match"], match)

    def test_a_competition_redacts_only_its_live_matches(self):
        detail = {"competition": {"name": "Ligue 1"}, "matches": [
            {"external_id": "live", "status": "live", "home_score": 2},
            {"external_id": "done", "status": "finished", "home_score": 1},
        ]}
        payload = companion.competition_center_payload(
            detail, {"stream_delay": 90})
        self.assertTrue(payload["matches"][0]["spoiler_free"])
        self.assertNotIn("home_score", payload["matches"][0])
        self.assertFalse(payload["matches"][1]["spoiler_free"])
        self.assertEqual(payload["matches"][1]["home_score"], 1)

    def test_a_team_redacts_only_its_live_matches(self):
        detail = {"team": {"name": "Angers"}, "record": {"played": 4},
                  "matches": [
                      {"external_id": "live", "status": "live",
                       "home_score": 2},
                      {"external_id": "done", "status": "finished",
                       "home_score": 1},
                  ]}
        payload = companion.team_center_payload(
            detail, {"stream_delay": 90})
        self.assertTrue(payload["matches"][0]["spoiler_free"])
        self.assertNotIn("home_score", payload["matches"][0])
        self.assertEqual(payload["record"]["played"], 4)
        self.assertEqual(payload["matches"][1]["home_score"], 1)

    def test_a_head_to_head_redacts_only_its_live_matches(self):
        detail = {"first_team": {"name": "Angers"},
                  "second_team": {"name": "Lille"},
                  "record": {"played": 8}, "matches": [
                      {"external_id": "live", "status": "live",
                       "home_score": 2},
                      {"external_id": "done", "status": "finished",
                       "home_score": 1},
                  ]}
        payload = companion.head_to_head_payload(
            detail, {"stream_delay": 90})
        self.assertTrue(payload["matches"][0]["spoiler_free"])
        self.assertNotIn("home_score", payload["matches"][0])
        self.assertEqual(payload["record"]["played"], 8)
        self.assertEqual(payload["matches"][1]["home_score"], 1)


if __name__ == "__main__":
    unittest.main()
