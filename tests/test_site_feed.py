import json
import shutil
import threading
import unittest
import urllib.error
import urllib.request
import uuid
from http.server import ThreadingHTTPServer
from pathlib import Path

from butbutbut import companion, espn, leagues, site_feed, state
from helpers import event, goal_detail, payload


def source(*events, logo=None):
    data = payload(*events)
    header = {"name": "Ligue 1", "abbreviation": "L1", "slug": "fra.1"}
    if logo is not None:
        header["logos"] = [{"href": logo}]
    data["leagues"] = [header]
    data["season"] = {"year": 2026}
    return data


class SiteFeedCase(unittest.TestCase):
    def setUp(self):
        self.root = Path.cwd() / ".test-site-feed" / uuid.uuid4().hex
        self.root.mkdir(parents=True)
        self.store = site_feed.Store(self.root / "feed.sqlite3")
        self.league = leagues.League("fra.1", "Ligue 1", "LIGUE 1", "#fff")

    def tearDown(self):
        shutil.rmtree(str(self.root), ignore_errors=True)
        try:
            self.root.parent.rmdir()
        except OSError:
            pass

    def matches(self, *events, logo=None):
        return espn.parse(source(*events, logo=logo), self.league)


class TestContract(SiteFeedCase):
    def test_all_football_excludes_other_sports(self):
        selected = leagues.resolve("all-football")
        self.assertEqual(selected, list(leagues.FOOTBALL))
        self.assertTrue(all(item.sport is leagues.sports.SOCCER for item in selected))

    def test_contract_version_and_empty_response(self):
        feed = self.store.feed(followed=[self.league])
        self.assertEqual(feed["schema_version"], 1)
        self.assertTrue(feed["producer"].startswith("butbutbut/"))
        self.assertEqual(feed["matches"], [])
        self.assertIsNone(feed["next_cursor"])
        self.assertEqual(feed["competitions"][0]["external_id"], "fra.1")

    def test_logo_is_read_from_metadata_and_never_guessed(self):
        match = self.matches(event(), logo="https://a.espncdn.com/ligue1.png")[0]
        self.assertEqual(site_feed.normalize_match(match)["competition"]["logo_url"],
                         "https://a.espncdn.com/ligue1.png")
        without = self.matches(event())[0]
        self.assertIsNone(
            site_feed.normalize_match(without)["competition"]["logo_url"])

    def test_a_match_is_fully_normalized(self):
        raw = event(
            match_id="401", state="post", home_score=2, away_score=1,
            status_name="STATUS_FULL_TIME", home_logo="https://img/home.png",
            details=(goal_detail("H401", "45+2'", "J. Test", index=1),),
            home_stats={"totalShots": "12"}, away_stats={"totalShots": "7"},
            venue_country="France")
        raw["season"] = {"displayName": "2026-27"}
        raw["competitions"][0]["details"][0]["id"] = "espn-event-9"
        raw["competitions"][0]["venue"]["fullName"] = "Stade de test"
        raw["competitions"][0]["competitors"][0]["team"]["slug"] = "angers"
        row = site_feed.normalize_match(self.matches(raw)[0])
        self.assertEqual(row["external_id"], "401")
        self.assertEqual(row["status"], "finished")
        self.assertEqual(row["starts_at"], "2026-09-06T15:15:00Z")
        self.assertEqual(row["season"], "2026-27")
        self.assertEqual(row["venue"], "Stade de test")
        self.assertEqual(row["home_team"]["external_id"], "H401")
        self.assertEqual(row["home_team"]["slug"], "angers")
        self.assertEqual(row["home_team"]["crest_url"], "https://img/home.png")
        self.assertEqual(row["events"][0]["minute"], 45)
        self.assertEqual(row["events"][0]["added_time"], 2)
        self.assertEqual(row["events"][0]["team_external_id"], "H401")
        self.assertEqual(row["events"][0]["external_id"], "espn-event-9")
        self.assertEqual(row["home_statistics"]["totalShots"], 12.0)


class TestPagination(SiteFeedCase):
    def setUp(self):
        super().setUp()
        matches = self.matches(
            event(match_id="2", date="2026-09-02T10:00Z"),
            event(match_id="1", date="2026-09-02T10:00Z"),
            event(match_id="3", date="2026-09-03T10:00Z"),
            event(match_id="4", date="2026-09-04T10:00Z"))
        self.store.upsert([self.league], matches)

    def test_pages_have_no_duplicate_or_omission(self):
        first = self.store.feed({"limit": "2"})
        second = self.store.feed({"limit": "2", "cursor": first["next_cursor"]})
        ids = [row["external_id"] for row in first["matches"] + second["matches"]]
        self.assertEqual(ids, ["1", "2", "3", "4"])
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIsNone(second["next_cursor"])

    def test_cursor_cannot_be_reused_with_other_filters(self):
        first = self.store.feed({"limit": "1", "from": "2026-09-01"})
        with self.assertRaises(site_feed.InvalidQuery):
            self.store.feed({"limit": "1", "from": "2026-09-02",
                             "cursor": first["next_cursor"]})

    def test_invalid_cursor_and_limits_are_rejected(self):
        for params in ({"cursor": "broken"}, {"limit": "0"},
                       {"limit": str(site_feed.MAX_LIMIT + 1)},
                       {"from": "demain"}):
            with self.subTest(params=params), self.assertRaises(site_feed.InvalidQuery):
                self.store.feed(params)

    def test_date_bounds_are_inclusive_for_calendar_days(self):
        feed = self.store.feed({"from": "2026-09-02", "to": "2026-09-03"})
        self.assertEqual([row["external_id"] for row in feed["matches"]],
                         ["1", "2", "3"])


class TestBackfill(SiteFeedCase):
    def test_one_league_error_does_not_erase_the_other(self):
        other = leagues.League("eng.1", "Premier League", "PREMIER", "#fff")

        def opener(url, _timeout):
            if "/eng.1/" in url:
                raise espn.SourceError("panne anglaise")
            return json.dumps(source(event(match_id="ok"))).encode("utf-8")

        worker = site_feed.Backfill(
            self.root / "feed.sqlite3", self.root / "raw", opener=opener,
            request_delay=0, sleeper=lambda _seconds: None)
        result = worker.run([self.league, other], "2026-09-01", "2026-09-30")
        self.assertEqual(result["completed"], 1)
        self.assertEqual(len(result["errors"]), 1)
        feed = self.store.feed()
        self.assertEqual([row["external_id"] for row in feed["matches"]], ["ok"])
        self.assertEqual(feed["errors"][0]["competition_external_id"], "eng.1")

    def test_dry_run_does_not_create_storage_or_call_network(self):
        worker = site_feed.Backfill(
            self.root / "never.sqlite3", self.root / "raw",
            opener=lambda *_args: self.fail("network used"))
        result = worker.run([self.league], "2026-01-01", "2026-02-28",
                            dry_run=True)
        self.assertEqual(result["planned"], 2)
        self.assertFalse((self.root / "never.sqlite3").exists())

    def test_partial_month_is_resumable_without_omission(self):
        calls = []
        data = source(
            event(match_id="early", date="2026-09-02T10:00Z"),
            event(match_id="inside", date="2026-09-16T10:00Z"))

        def opener(url, _timeout):
            calls.append(url)
            return json.dumps(data).encode("utf-8")

        worker = site_feed.Backfill(
            self.root / "feed.sqlite3", self.root / "raw", opener=opener,
            request_delay=0, sleeper=lambda _seconds: None)
        worker.run([self.league], "2026-09-15", "2026-09-20")
        self.assertEqual([row["external_id"] for row in self.store.feed()["matches"]],
                         ["inside"])
        worker.run([self.league], "2026-09-01", "2026-09-30")
        self.assertEqual([row["external_id"] for row in self.store.feed()["matches"]],
                         ["early", "inside"])
        # Le second lot normalise le cache brut du mois sans nouvelle requete.
        self.assertEqual(len(calls), 1)


class TestHttp(SiteFeedCase):
    def setUp(self):
        super().setUp()
        self.state_path = self.root / "state.json"
        self.control_path = self.root / "control.json"
        state.write(self.state_path, {"version": 2, "goals_today": 3,
                                      "private_preference": "never expose"})
        self.server = ThreadingHTTPServer(
            ("127.0.0.1", 0),
            companion.handler(self.state_path, self.control_path,
                              feed_path=self.root / "feed.sqlite3",
                              followed=[self.league]))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)
        super().tearDown()

    def get(self, path):
        url = "http://127.0.0.1:{}{}".format(self.server.server_address[1], path)
        with urllib.request.urlopen(url, timeout=2) as response:
            return response.status, response.headers, json.load(response)

    def test_site_feed_is_utf8_and_whitelists_state(self):
        status, headers, body = self.get("/api/v1/site-feed")
        self.assertEqual(status, 200)
        self.assertEqual(headers.get_content_charset(), "utf-8")
        self.assertEqual(body["state"]["goals_today"], 3)
        self.assertNotIn("private_preference", json.dumps(body))

    def test_api_state_is_unchanged(self):
        _status, _headers, body = self.get("/api/state")
        self.assertEqual(body["version"], 2)
        self.assertEqual(body["private_preference"], "never expose")

    def test_bad_feed_query_is_a_400(self):
        url = "http://127.0.0.1:{}/api/v1/site-feed?limit=0".format(
            self.server.server_address[1])
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(url, timeout=2)
        self.assertEqual(caught.exception.code, 400)
        caught.exception.close()


if __name__ == "__main__":
    unittest.main()
