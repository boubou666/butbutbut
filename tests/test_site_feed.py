import json
import shutil
import sqlite3
import threading
import unittest
import urllib.error
import urllib.request
import uuid
from contextlib import closing
from http.server import ThreadingHTTPServer
from pathlib import Path

from butbutbut import companion, espn, leagues, site_feed, state
from helpers import event, goal_detail, in_minutes, payload


FIXTURES = Path(__file__).with_name("fixtures")


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

    def test_one_match_can_be_read_directly_with_fresh_competition_metadata(self):
        match = self.matches(event(match_id="401"))[0]
        self.store.upsert([self.league], [match])
        self.assertEqual(self.store.get_match("401")["external_id"], "401")
        self.assertEqual(
            self.store.get_match("401")["competition"]["name"], "Ligue 1")
        self.assertIsNone(self.store.get_match("missing"))

    def test_search_finds_teams_and_competitions_without_accents(self):
        self.store.upsert([self.league], self.matches(event(
            match_id="401", home="Saint-Étienne", away="Paris FC")))
        teams = self.store.search("etienne")
        self.assertEqual(teams[0]["external_id"], "H401")
        self.assertEqual(teams[0]["type"], "team")
        competitions = self.store.search("ligue")
        self.assertEqual(competitions[0]["external_id"], "fra.1")
        self.assertEqual(competitions[0]["type"], "competition")
        self.assertEqual(len(self.store.search("i", limit=1)), 0)

    def test_favorites_join_teams_and_competitions_without_duplicates(self):
        matches = self.matches(
            event(match_id="401", state="pre", status_name="STATUS_SCHEDULED",
                  date=in_minutes(60)),
            event(match_id="402", state="in", status_name="STATUS_IN_PROGRESS"),
            event(match_id="403", state="post", status_name="STATUS_FULL_TIME"),
            event(match_id="404", state="pre", status_name="STATUS_SCHEDULED"))
        self.store.upsert([self.league], matches)
        selected = self.store.favorite_matches(
            team_ids=["H401"], competition_ids=["fra.1"])
        self.assertEqual(
            [item["external_id"] for item in selected], ["402", "401"])
        self.assertEqual(self.store.favorite_matches(), [])

    def test_absent_structure_is_null_not_invented(self):
        row = site_feed.normalize_match(self.matches(event())[0])
        for key in ("edition_external_id", "edition_name", "phase_kind",
                    "phase_external_id", "phase_name", "phase_order",
                    "group_external_id", "group_name", "group_order",
                    "round_external_id", "round_name", "round_order",
                    "tie_external_id", "leg_number", "bracket_slot",
                    "next_match_external_id", "winner_team_external_id",
                    "decided_by"):
            self.assertIsNone(row[key], key)

    def test_decision_method_uses_only_explicit_final_statuses(self):
        regular = site_feed.normalize_match(self.matches(event(
            state="post", status_name="STATUS_FULL_TIME", detail="FT"))[0])
        extra = site_feed.normalize_match(self.matches(event(
            state="post", status_name="STATUS_FINAL_AET", detail="AET"))[0])
        self.assertEqual(regular["decided_by"], "regular_time")
        self.assertEqual(extra["decided_by"], "extra_time")

    def test_a_regular_season_is_a_league_phase(self):
        raw = event()
        raw["season"] = {"year": 2026, "type": 8001,
                         "slug": "regular-season"}
        structure = espn.parse_competition_structure({
            "year": 2026,
            "displayName": "2026-27 Ligue 1",
            "types": {"items": [{
                "id": "1", "type": 8001, "name": "Regular Season",
                "slug": "regular-season", "hasStandings": True,
            }]},
        })
        match = espn.parse(source(raw), self.league, structure=structure)[0]
        row = site_feed.normalize_match(match)
        self.assertEqual(row["phase_kind"], "league")
        self.assertEqual(row["phase_name"], "Regular Season")


class TestOfficialCompetitionStructure(SiteFeedCase):
    def setUp(self):
        super().setUp()
        with (FIXTURES / "site_feed_groups_knockout.json").open(
                encoding="utf-8") as handle:
            self.fixture = json.load(handle)
        self.league = leagues.League(
            "test.cup", "Test Cup", "TEST CUP", "#fff")

    def normalized_feed(self):
        structure = espn.parse_competition_structure(
            self.fixture["season"], self.fixture["tournament"],
            self.fixture["core_events"].values(), self.fixture["standings"])
        matches = espn.parse(self.fixture["scoreboard"], self.league,
                             structure=structure)
        table = espn.parse_standings(
            self.fixture["standings"], self.league, structure=structure)
        self.store.upsert([self.league], matches, [table])
        return self.store.feed(followed=[self.league])

    def test_groups_then_knockout_are_joined_without_parsing_free_text(self):
        feed = self.normalized_feed()
        group, round_of_16, quarterfinal = feed["matches"]
        self.assertEqual(
            (group["edition_external_id"], group["edition_name"]),
            ("2026", "2026 Test Cup"))
        self.assertEqual(
            (group["phase_kind"], group["phase_external_id"],
             group["phase_name"], group["phase_order"]),
            ("group", "9001", "Group Stage", 1))
        self.assertEqual(
            (group["group_external_id"], group["group_name"],
             group["group_order"]),
            ("group-a", "Group A", 1))
        self.assertEqual(group["decided_by"], "regular_time")
        self.assertEqual(
            (round_of_16["phase_kind"], round_of_16["round_external_id"],
             round_of_16["round_name"], round_of_16["round_order"]),
            ("knockout", "round-r16", "Round of 16", 1))
        self.assertEqual(
            (round_of_16["tie_external_id"], round_of_16["leg_number"],
             round_of_16["bracket_slot"],
             round_of_16["next_match_external_id"]),
            ("tie-1", 1, 2, "qf-1"))
        self.assertEqual(round_of_16["winner_team_external_id"], "alpha")
        self.assertEqual(round_of_16["decided_by"], "penalties")
        self.assertIsNone(quarterfinal["winner_team_external_id"])
        self.assertIsNone(quarterfinal["decided_by"])

    def test_official_group_table_exposes_only_published_values(self):
        table = self.normalized_feed()["standings"][0]
        self.assertEqual(
            (table["edition_external_id"], table["phase_external_id"],
             table["group_external_id"], table["group_order"]),
            ("2026", "9001", "group-a", 1))
        alpha, beta = table["rows"]
        self.assertEqual(alpha, {
            "team_external_id": "alpha", "team_name": "Alpha",
            "played": 3, "won": 2, "drawn": 1, "lost": 0,
            "goals_for": 5, "goals_against": 2, "goal_difference": 3,
            "points": 6, "rank": 1, "penalties": 1,
        })
        self.assertIsNone(beta["penalties"])

    def test_one_competition_exposes_its_editions_matches_and_tables(self):
        self.normalized_feed()
        detail = self.store.competition_detail("test.cup")
        self.assertEqual(detail["competition"]["name"], "Test Cup")
        self.assertEqual(detail["edition"]["external_id"], "2026")
        self.assertEqual(detail["edition"]["match_count"], 3)
        self.assertEqual(
            [row["external_id"] for row in detail["matches"]],
            ["group-1", "r16-1", "qf-1"])
        self.assertEqual(len(detail["standings"]), 1)
        with self.assertRaises(site_feed.NotFound):
            self.store.competition_detail("test.cup", edition_id="1900")

    def test_one_team_exposes_its_record_form_and_matches(self):
        self.normalized_feed()
        detail = self.store.team_detail("alpha")
        self.assertEqual(detail["team"]["name"], "Alpha")
        self.assertEqual(detail["record"], {
            "played": 2, "won": 1, "drawn": 1, "lost": 0,
            "goals_for": 3, "goals_against": 3,
        })
        self.assertEqual(detail["form"], ["D", "W"])
        self.assertEqual(
            [row["external_id"] for row in detail["matches"]],
            ["group-1", "r16-1", "qf-1"])
        self.assertEqual(
            [row["external_id"] for row in detail["competitions"]],
            ["test.cup"])
        self.assertIsNone(self.store.team_detail("missing"))

    def test_a_penalty_shootout_uses_the_official_winner_in_team_form(self):
        self.normalized_feed()
        detail = self.store.team_detail("gamma")
        self.assertEqual(detail["record"]["lost"], 1)
        self.assertEqual(detail["record"]["drawn"], 0)
        self.assertEqual(detail["form"], ["L"])

    def test_head_to_head_uses_the_official_winner_and_requested_order(self):
        self.normalized_feed()
        detail = self.store.head_to_head("gamma", "alpha")
        self.assertEqual(detail["first_team"]["name"], "Gamma")
        self.assertEqual(detail["second_team"]["name"], "Alpha")
        self.assertEqual(detail["record"], {
            "played": 1, "first_wins": 0, "draws": 0,
            "second_wins": 1, "first_goals": 2, "second_goals": 2,
        })
        self.assertEqual(
            [row["external_id"] for row in detail["matches"]], ["r16-1"])
        self.assertIsNone(self.store.head_to_head("alpha", "missing"))
        self.assertIsNone(self.store.head_to_head("alpha", "alpha"))

    def test_a_live_score_update_does_not_erase_backfilled_structure(self):
        self.normalized_feed()
        live = espn.parse(self.fixture["scoreboard"], self.league)
        live[1].home_score = 3
        self.store.upsert([self.league], live)
        round_of_16 = self.store.feed(followed=[self.league])["matches"][1]
        self.assertEqual(round_of_16["home_score"], 3)
        self.assertEqual(round_of_16["round_external_id"], "round-r16")
        self.assertEqual(round_of_16["next_match_external_id"], "qf-1")

    def test_backfill_keeps_each_raw_response_outside_normalized_storage(self):
        def opener(url, _timeout):
            if "scoreboard" in url:
                answer = self.fixture["scoreboard"]
            elif "/standings" in url:
                answer = self.fixture["standings"]
            elif "/tournaments/" in url:
                answer = self.fixture["tournament"]
            elif "/events/" in url:
                event_id = url.split("/events/", 1)[1].split("?", 1)[0]
                answer = self.fixture["core_events"][event_id]
            else:
                answer = self.fixture["season"]
            return json.dumps(answer).encode("utf-8")

        worker = site_feed.Backfill(
            self.root / "feed.sqlite3", self.root / "raw", opener=opener,
            request_delay=0, sleeper=lambda _seconds: None)
        result = worker.run([self.league], "2026-06-01", "2026-06-30")
        self.assertEqual(result["errors"], [])
        self.assertEqual(len(self.store.feed()["standings"]), 1)
        raw = worker.cache.path_for(self.league, "202606")
        structure = worker.cache.path_for(self.league, "structure-2026")
        self.assertTrue(raw.exists())
        self.assertTrue(structure.exists())
        self.assertNotEqual(raw, structure)


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
    def test_a_legacy_match_table_is_indexed_by_edition_once(self):
        path = self.root / "legacy-matches.sqlite3"
        match = site_feed.normalize_match(
            self.matches(event(match_id="legacy"))[0])
        with closing(sqlite3.connect(str(path))) as db, db:
            db.execute("CREATE TABLE competitions (external_id TEXT PRIMARY KEY, "
                       "payload TEXT NOT NULL, updated_at TEXT NOT NULL)")
            db.execute("CREATE TABLE matches (external_id TEXT PRIMARY KEY, "
                       "competition_id TEXT NOT NULL, starts_at TEXT NOT NULL, "
                       "payload TEXT NOT NULL, updated_at TEXT NOT NULL)")
            db.execute("INSERT INTO competitions VALUES (?, ?, ?)", (
                "fra.1", json.dumps(match["competition"]), "2026-01-01T00:00:00Z"))
            db.execute("INSERT INTO matches VALUES (?, ?, ?, ?, ?)", (
                "legacy", "fra.1", match["starts_at"], json.dumps(match),
                "2026-01-01T00:00:00Z"))

        legacy = site_feed.Store(path)
        detail = legacy.competition_detail("fra.1")
        self.assertEqual(detail["matches"][0]["external_id"], "legacy")
        with closing(sqlite3.connect(str(path))) as db:
            edition_id, home_id, away_id = db.execute(
                "SELECT edition_id, home_team_id, away_team_id FROM matches "
                "WHERE external_id='legacy'"
            ).fetchone()
        self.assertEqual(edition_id, "2026")
        self.assertEqual((home_id, away_id), ("Hlegacy", "Alegacy"))
        self.assertEqual(
            legacy.search("angers")[0]["external_id"], "Hlegacy")

    def test_an_old_completed_period_is_renormalized_once(self):
        path = self.root / "legacy.sqlite3"
        with closing(sqlite3.connect(str(path))) as db, db:
            db.execute("CREATE TABLE backfill_periods ("
                       "competition_id TEXT NOT NULL, period TEXT NOT NULL, "
                       "status TEXT NOT NULL, message TEXT, updated_at TEXT NOT NULL, "
                       "PRIMARY KEY(competition_id, period))")
            db.execute("INSERT INTO backfill_periods VALUES "
                       "('fra.1', '202609', 'ok', '', '2026-09-30T00:00:00Z')")
        legacy = site_feed.Store(path)
        self.assertFalse(legacy.period_done("fra.1", "202609"))
        legacy.mark_period("fra.1", "202609", "ok")
        self.assertTrue(legacy.period_done("fra.1", "202609"))

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

    def test_local_search_has_a_dedicated_endpoint(self):
        self.store.upsert([self.league], self.matches(event(match_id="401")))
        status, _headers, body = self.get("/api/v1/search?q=angers&limit=5")
        self.assertEqual(status, 200)
        self.assertEqual(body["query"], "angers")
        self.assertEqual(body["results"][0]["external_id"], "H401")
        self.assertEqual(body["results"][0]["type"], "team")

    def test_local_search_rejects_bad_queries(self):
        for path in ("/api/v1/search", "/api/v1/search?q=a",
                     "/api/v1/search?q=angers&limit=0",
                     "/api/v1/search?q=angers&extra=1"):
            with self.subTest(path=path), self.assertRaises(
                    urllib.error.HTTPError) as caught:
                urllib.request.urlopen(
                    "http://127.0.0.1:{}{}".format(
                        self.server.server_address[1], path), timeout=2)
            self.assertEqual(caught.exception.code, 400)
            caught.exception.close()

    def test_favorites_have_a_spoiler_safe_endpoint(self):
        self.store.upsert([self.league], self.matches(event(
            match_id="401", state="in", home_score=2, away_score=1)))
        state.write(self.state_path, {"version": 2, "stream_delay": 90})
        status, _headers, body = self.get(
            "/api/v1/favorites?team=H401&competition=fra.1&limit=5")
        self.assertEqual(status, 200)
        self.assertEqual(body["matches"][0]["external_id"], "401")
        self.assertTrue(body["matches"][0]["spoiler_free"])
        self.assertNotIn("home_score", body["matches"][0])

    def test_favorites_calendar_is_downloadable(self):
        self.store.upsert([self.league], self.matches(event(
            match_id="401", state="pre", status_name="STATUS_SCHEDULED",
            date=in_minutes(60))))
        url = "http://127.0.0.1:{}/api/v1/favorites.ics?team=H401".format(
            self.server.server_address[1])
        with urllib.request.urlopen(url, timeout=2) as response:
            page = response.read().decode("utf-8")
            self.assertEqual(response.headers.get_content_type(),
                             "text/calendar")
            self.assertIn("butbutbut-favoris.ics",
                          response.headers["Content-Disposition"])
        self.assertIn("BEGIN:VCALENDAR\r\n", page)
        self.assertIn("UID:401@butbutbut.local\r\n", page)

    def test_favorites_reject_bad_queries(self):
        paths = ("/api/v1/favorites",
                 "/api/v1/favorites.ics",
                 "/api/v1/favorites?team=",
                 "/api/v1/favorites?team=H401&limit=0",
                 "/api/v1/favorites?team=H401&extra=1")
        for path in paths:
            with self.subTest(path=path), self.assertRaises(
                    urllib.error.HTTPError) as caught:
                urllib.request.urlopen(
                    "http://127.0.0.1:{}{}".format(
                        self.server.server_address[1], path), timeout=2)
            self.assertEqual(caught.exception.code, 400)
            caught.exception.close()

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

    def test_one_match_has_a_dedicated_endpoint(self):
        self.store.upsert([self.league], self.matches(event(
            match_id="401", state="in", home_score=2, away_score=1)))
        status, _headers, body = self.get("/api/v1/match?id=401")
        self.assertEqual(status, 200)
        self.assertEqual(body["match"]["external_id"], "401")
        self.assertEqual(body["match"]["home_score"], 2)
        self.assertFalse(body["spoiler_free"])

    def test_the_match_endpoint_rejects_missing_or_unknown_ids(self):
        for path, code in (("/api/v1/match", 400),
                           ("/api/v1/match?id=missing", 404)):
            with self.subTest(path=path), self.assertRaises(
                    urllib.error.HTTPError) as caught:
                urllib.request.urlopen(
                    "http://127.0.0.1:{}{}".format(
                        self.server.server_address[1], path), timeout=2)
            self.assertEqual(caught.exception.code, code)
            caught.exception.close()

    def test_one_competition_has_a_dedicated_endpoint(self):
        self.store.upsert([self.league], self.matches(event(match_id="401")))
        status, _headers, body = self.get(
            "/api/v1/competition?id=fra.1")
        self.assertEqual(status, 200)
        self.assertEqual(body["competition"]["external_id"], "fra.1")
        self.assertEqual(body["matches"][0]["external_id"], "401")
        self.assertEqual(body["edition"]["match_count"], 1)

    def test_one_team_has_a_dedicated_endpoint(self):
        self.store.upsert([self.league], self.matches(event(
            match_id="401", state="post", status_name="STATUS_FULL_TIME",
            home_score=2, away_score=1)))
        status, _headers, body = self.get("/api/v1/team?id=H401")
        self.assertEqual(status, 200)
        self.assertEqual(body["team"]["name"], "Angers")
        self.assertEqual(body["record"]["won"], 1)
        self.assertEqual(body["matches"][0]["external_id"], "401")

    def test_two_teams_have_a_head_to_head_endpoint(self):
        self.store.upsert([self.league], self.matches(event(
            match_id="401", state="post", status_name="STATUS_FULL_TIME",
            home_score=2, away_score=1)))
        status, _headers, body = self.get(
            "/api/v1/head-to-head?team=H401&opponent=A401")
        self.assertEqual(status, 200)
        self.assertEqual(body["first_team"]["name"], "Angers")
        self.assertEqual(body["second_team"]["name"], "Stade Rennais")
        self.assertEqual(body["record"]["first_wins"], 1)

    def test_head_to_head_rejects_invalid_or_unknown_pairs(self):
        for path, code in (("/api/v1/head-to-head?team=a&opponent=a", 400),
                           ("/api/v1/head-to-head?team=a&opponent=b", 404)):
            with self.subTest(path=path), self.assertRaises(
                    urllib.error.HTTPError) as caught:
                urllib.request.urlopen(
                    "http://127.0.0.1:{}{}".format(
                        self.server.server_address[1], path), timeout=2)
            self.assertEqual(caught.exception.code, code)
            caught.exception.close()

    def test_the_team_endpoint_rejects_missing_or_unknown_ids(self):
        for path, code in (("/api/v1/team", 400),
                           ("/api/v1/team?id=missing", 404)):
            with self.subTest(path=path), self.assertRaises(
                    urllib.error.HTTPError) as caught:
                urllib.request.urlopen(
                    "http://127.0.0.1:{}{}".format(
                        self.server.server_address[1], path), timeout=2)
            self.assertEqual(caught.exception.code, code)
            caught.exception.close()

    def test_the_competition_endpoint_rejects_an_unknown_edition(self):
        self.store.upsert([self.league], self.matches(event(match_id="401")))
        url = "http://127.0.0.1:{}/api/v1/competition?id=fra.1&edition=1900".format(
            self.server.server_address[1])
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(url, timeout=2)
        self.assertEqual(caught.exception.code, 404)
        caught.exception.close()


if __name__ == "__main__":
    unittest.main()
