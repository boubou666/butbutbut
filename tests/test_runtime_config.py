import json
import unittest
from unittest import mock

from butbutbut import cli, leagues, runtime_config, watcher

from helpers import FakeClock, bump, event, opener_for, payload


LIGUE1 = leagues.BY_SLUG["fra.1"]


class Response:
    def __init__(self, value):
        self.body = json.dumps(value).encode("utf-8")

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def document(revision="one", matches=None, poll=5, grace=45,
             version="1.0"):
    return {
        "schema_version": version,
        "revision": revision,
        "catalog_scope": "all-football",
        "poll_after_seconds": poll,
        "grace_period_seconds": grace,
        "live_matches": list(matches or []),
    }


def match(match_id="401234567", selected_by=1, competition="fra.1"):
    return {
        "external_id": match_id,
        "competition_external_id": competition,
        "starts_at": "2026-09-21T19:00:00Z",
        "selected_by": selected_by,
    }


class Sequence:
    def __init__(self, *answers):
        self.answers = list(answers)
        self.requests = []

    def __call__(self, request, timeout=None):
        self.requests.append((request, timeout))
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return Response(answer)


class TestRuntimeClient(unittest.TestCase):
    def client(self, opener, **kwargs):
        self.logs = []
        return runtime_config.Client(
            "http://localhost:8000/", "top-secret", opener=opener,
            clock=kwargs.pop("clock", FakeClock(0)), on_log=self.logs.append,
            **kwargs)

    def test_addition_is_immediate_and_header_is_sent(self):
        source = Sequence(document(matches=[match()]))
        client = self.client(source)
        self.assertEqual(client.refresh(force=True), {"401234567": "fra.1"})
        request, _timeout = source.requests[0]
        self.assertEqual(request.full_url,
                         "http://localhost:8000" + runtime_config.PATH)
        self.assertEqual(request.get_header("X-butbutbut-api-key"), "top-secret")

    def test_duplicate_users_make_one_match(self):
        client = self.client(Sequence(document(matches=[
            match(selected_by=1), match(selected_by=10), match(selected_by=99),
        ])))
        self.assertEqual(client.refresh(force=True), {"401234567": "fra.1"})

    def test_unchanged_revision_does_not_emit_an_update(self):
        same = document(matches=[match()])
        client = self.client(Sequence(same, same))
        self.assertIsNotNone(client.refresh(now=0, force=True))
        self.assertIsNone(client.refresh(now=5, force=True))

    def test_removal_waits_for_grace_then_expires(self):
        source = Sequence(
            document("one", [match()], grace=45),
            document("two", [], grace=45),
            document("two", [], grace=45),
        )
        client = self.client(source)
        client.refresh(now=0, force=True)
        self.assertEqual(client.refresh(now=5, force=True),
                         {"401234567": "fra.1"})
        self.assertIsNone(client.refresh(now=49, force=False))
        self.assertEqual(client.refresh(now=50, force=True), {})

    def test_return_during_grace_cancels_removal(self):
        source = Sequence(document("one", [match()]), document("two", []),
                          document("three", [match()]))
        client = self.client(source)
        client.refresh(now=0, force=True)
        client.refresh(now=5, force=True)
        self.assertEqual(client.refresh(now=20, force=True),
                         {"401234567": "fra.1"})
        self.assertIsNone(client.refresh(now=60))

    def test_empty_response_is_a_valid_empty_selection(self):
        client = self.client(Sequence(document(matches=[])))
        self.assertEqual(client.refresh(force=True), {})
        self.assertEqual(client.active_matches, {})

    def test_unavailable_site_keeps_then_expires_last_valid_config(self):
        source = Sequence(document(matches=[match()]), OSError("offline"),
                          OSError("still offline"))
        client = self.client(source, max_stale=30)
        client.refresh(now=0, force=True)
        self.assertIsNone(client.refresh(now=5, force=True))
        self.assertEqual(client.active_matches, {"401234567": "fra.1"})
        self.assertEqual(client.refresh(now=30, force=True), {})
        self.assertEqual(client.active_matches, {})
        self.assertTrue(any("expiree" in line for line in self.logs))

    def test_same_revision_is_reapplied_after_stale_expiration(self):
        current = document(matches=[match()])
        source = Sequence(current, OSError("offline"), current)
        client = self.client(source, max_stale=30)
        client.refresh(now=0, force=True)
        self.assertEqual(client.refresh(now=30, force=True), {})
        self.assertEqual(client.refresh(now=35, force=True),
                         {"401234567": "fra.1"})

    def test_failures_apply_an_exponential_backoff(self):
        client = self.client(Sequence(OSError("a"), OSError("b")))
        client.refresh(now=0, force=True)
        first = client.next_delay(now=0)
        client.refresh(now=first, force=True)
        self.assertGreater(client.next_delay(now=first), first)

    def test_incompatible_major_is_ignored(self):
        source = Sequence(document("one", [match()]),
                          document("two", [], version="2.0"))
        client = self.client(source)
        client.refresh(now=0, force=True)
        self.assertIsNone(client.refresh(now=5, force=True))
        self.assertEqual(client.active_matches, {"401234567": "fra.1"})
        self.assertTrue(any("incompatible" in line for line in self.logs))

    def test_api_key_never_appears_in_logs(self):
        client = self.client(Sequence(OSError("top-secret")))
        client.refresh(force=True)
        self.assertNotIn("top-secret", "\n".join(self.logs))


class TestRuntimeWatcher(unittest.TestCase):
    def setUp(self):
        self.state = {"payload": payload(event(match_id="401234567", state="in"),
                                         event(match_id="other", state="in"))}

    def test_only_selected_match_generates_events(self):
        guard = watcher.Watcher(
            [LIGUE1], opener=opener_for(self.state),
            selected_matches={"401234567": "fra.1"})
        guard.prime(pause=0)
        changed = bump(self.state["payload"], "home")
        # bump() touche le premier match, qui est bien le match selectionne.
        self.state["payload"] = changed
        self.assertEqual(len(guard.refresh(LIGUE1)), 1)
        self.assertEqual([item.id for item in guard.all_matches()], ["401234567"])
        self.assertEqual(len(guard.catalog_matches()), 2)

    def test_new_selection_wakes_its_competition_immediately(self):
        guard = watcher.Watcher([LIGUE1], opener=opener_for(self.state),
                                selected_matches={}, monotonic=lambda: 10,
                                catalog_interval=3600)
        guard.refresh(LIGUE1, now=0)
        self.assertEqual(guard._due["fra.1"], 3600)
        self.assertTrue(guard.set_selected_matches(
            {"401234567": "fra.1"}, now=10))
        self.assertEqual(guard._due["fra.1"], 10)

    def test_removal_returns_competition_to_catalog_cadence(self):
        guard = watcher.Watcher(
            [LIGUE1], opener=opener_for(self.state), interval=20,
            selected_matches={"401234567": "fra.1"}, catalog_interval=3600)
        guard.refresh(LIGUE1, now=0)
        self.assertEqual(guard._due["fra.1"], 20)
        guard.set_selected_matches({}, now=7)
        self.assertEqual(guard._due["fra.1"], 3607)

    def test_selected_adhoc_football_competition_is_opened(self):
        guard = watcher.Watcher([LIGUE1], opener=opener_for(self.state),
                                selected_matches={})
        guard.set_selected_matches({"42": "gre.1"}, now=7)
        self.assertIn("gre.1", {league.ref for league in guard.leagues})
        self.assertEqual(guard._due["gre.1"], 7)

    def test_catalog_failure_does_not_accelerate_catalog_polling(self):
        def broken(*_args, **_kwargs):
            raise OSError("offline")

        guard = watcher.Watcher([LIGUE1], opener=broken,
                                selected_matches={}, catalog_interval=3600)
        guard.refresh(LIGUE1, now=0)
        self.assertEqual(guard._due["fra.1"], 3600)

    def test_autonomous_mode_still_watches_every_match(self):
        guard = watcher.Watcher([LIGUE1], opener=opener_for(self.state))
        guard.prime(pause=0)
        self.assertEqual({item.id for item in guard.all_matches()},
                         {"401234567", "other"})
        self.state["payload"] = bump(self.state["payload"], "home")
        self.assertEqual(len(guard.refresh(LIGUE1)), 1)

    def test_site_feed_receives_catalog_while_status_receives_selection(self):
        writer = mock.Mock()
        guard = mock.Mock(**{"catalog_matches.return_value": ["all"]})
        submit = cli._site_feed_submitter(writer, guard, runtime=mock.Mock())
        submit(["selected"])
        writer.submit.assert_called_once_with(["all"])

    def test_autonomous_site_feed_keeps_the_existing_path(self):
        writer = mock.Mock()
        submit = cli._site_feed_submitter(writer, mock.Mock(), runtime=None)
        submit(["all"])
        writer.submit.assert_called_once_with(["all"])


if __name__ == "__main__":
    unittest.main()
