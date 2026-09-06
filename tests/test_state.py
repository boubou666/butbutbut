import json
import os
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from butbutbut import espn, leagues, state, watcher

from helpers import bump, event, goal_detail, opener_for, payload

LIGUE1 = leagues.BY_SLUG["fra.1"]


def matches_from(*events):
    return espn.parse(payload(*events), LIGUE1)


def goal_event(match, kind=watcher.GOAL):
    return watcher.Event(kind=kind, match=match, side="home", team=match.home,
                         opponent=match.away, home_score=match.home_score,
                         away_score=match.away_score, delta=1, play=None)


class TestWriteAndRead(unittest.TestCase):
    def test_round_trip(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "etat.json"
            self.assertTrue(state.write(path, {"version": 1, "goals_today": 2}))
            self.assertEqual(state.read(path)["goals_today"], 2)

    def test_missing_file_reads_as_none(self):
        with TemporaryDirectory() as tmp:
            self.assertIsNone(state.read(Path(tmp) / "jamais-ecrit.json"))

    def test_truncated_file_reads_as_none(self):
        # Le cas que l'ecriture atomique evite, mais qu'un antivirus ou un
        # arret brutal peut quand meme produire : --status ne doit pas exploser.
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "etat.json"
            path.write_text('{"version": 1, "matches": [{"home": "Ang',
                            encoding="utf-8")
            self.assertIsNone(state.read(path))

    def test_a_json_that_is_not_an_object_reads_as_none(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "etat.json"
            path.write_text("[1, 2, 3]", encoding="utf-8")
            self.assertIsNone(state.read(path))

    def test_write_leaves_no_temporary_behind(self):
        with TemporaryDirectory() as tmp:
            state.write(Path(tmp) / "etat.json", {"a": 1})
            self.assertEqual(sorted(os.listdir(tmp)), ["etat.json"])

    def test_write_replaces_the_previous_content_whole(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "etat.json"
            state.write(path, {"goals_today": 1, "long": "x" * 5000})
            state.write(path, {"goals_today": 2})
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data, {"goals_today": 2})

    def test_an_impossible_path_is_swallowed(self):
        # Dossier de donnees en lecture seule, disque plein : l'etat se perd,
        # le daemon continue. C'est tout l'interet du False rendu ici.
        with TemporaryDirectory() as tmp:
            barrier = Path(tmp) / "fichier"
            barrier.write_text("pas un dossier", encoding="utf-8")
            self.assertFalse(state.write(barrier / "etat.json", {"a": 1}))

    def test_unserialisable_payload_is_swallowed(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "etat.json"
            self.assertFalse(state.write(path, {"objet": object()}))
            self.assertFalse(path.exists())
            self.assertEqual(os.listdir(tmp), [])

    def test_clear_never_complains(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "etat.json"
            state.write(path, {"a": 1})
            state.clear(path)
            self.assertFalse(path.exists())
            state.clear(path)          # deja parti : silence


class TestFreshness(unittest.TestCase):
    def test_age_counts_from_the_last_write(self):
        data = {"updated_at": 1000.0}
        self.assertEqual(state.age(data, now=1030.0), 30.0)

    def test_age_of_an_undatable_state(self):
        self.assertIsNone(state.age(None))
        self.assertIsNone(state.age({}))
        self.assertIsNone(state.age({"updated_at": "hier"}))

    def test_a_live_match_shortens_the_patience(self):
        live = {"interval": 25, "idle_interval": 300, "matches": [{"home": "A"}]}
        idle = {"interval": 25, "idle_interval": 300, "matches": []}
        self.assertLess(state.stale_after(live), state.stale_after(idle))
        self.assertEqual(state.stale_after(idle), 900.0)

    def test_stale_when_the_daemon_stopped_polling(self):
        data = {"updated_at": 1000.0, "interval": 25, "idle_interval": 300,
                "matches": [{"home": "A"}]}
        self.assertFalse(state.is_stale(data, now=1060.0))
        self.assertTrue(state.is_stale(data, now=1600.0))

    def test_no_state_at_all_counts_as_stale(self):
        self.assertTrue(state.is_stale(None))

    def test_describe_age_stays_readable(self):
        self.assertEqual(state.describe_age(12), "il y a 12 s")
        self.assertEqual(state.describe_age(600), "il y a 10 min")
        self.assertEqual(state.describe_age(7800), "il y a 2 h 10")
        self.assertEqual(state.describe_age(None), "date inconnue")


class TestReporter(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.path = Path(self.tmp.name) / "etat.json"
        self.reporter = state.Reporter(self.path, leagues=[LIGUE1],
                                       interval=25, idle_interval=300)

    def tearDown(self):
        self.tmp.cleanup()

    def test_snapshot_keeps_the_live_matches_and_their_scores(self):
        matches = matches_from(
            event(match_id="1", state="in", home_score=1, away_score=0),
            event(match_id="2", home="Lyon", away="Lille", state="pre",
                  clock="", detail="17:00"))
        self.reporter.update(matches)

        data = state.read(self.path)
        self.assertEqual(data["total_matches"], 2)
        self.assertEqual(len(data["matches"]), 1)
        row = data["matches"][0]
        self.assertEqual(row["home"], "Angers")
        self.assertEqual(row["home_score"], 1)
        self.assertEqual(row["away_score"], 0)
        self.assertEqual(row["league"], "Ligue 1")
        self.assertEqual(data["leagues"], ["Ligue 1"])
        self.assertEqual(data["pid"], os.getpid())
        self.assertEqual(data["interval"], 25)
        self.assertLess(abs(data["updated_at"] - time.time()), 30)

    def test_only_real_goals_are_counted(self):
        match = matches_from(event(state="in", home_score=1))[0]
        self.reporter.update([match], [
            goal_event(match),
            goal_event(match, kind=watcher.CANCELLED),
            goal_event(match, kind=watcher.KICKOFF),
            goal_event(match),
        ])
        self.assertEqual(state.read(self.path)["goals_today"], 2)

    def test_the_counter_survives_between_two_polls(self):
        match = matches_from(event(state="in", home_score=1))[0]
        self.reporter.update([match], [goal_event(match)])
        self.reporter.update([match])
        self.assertEqual(state.read(self.path)["goals_today"], 1)

    def test_the_counter_restarts_at_midnight(self):
        match = matches_from(event(state="in", home_score=1))[0]
        self.reporter.update([match], [goal_event(match)])
        self.reporter.day = "1998-07-12"     # comme si on avait passe minuit
        self.reporter.update([match], [goal_event(match)])

        data = state.read(self.path)
        self.assertEqual(data["goals_today"], 1)
        self.assertEqual(data["day"], state.today())

    def test_a_failed_write_does_not_raise(self):
        broken = state.Reporter(Path(self.tmp.name) / "absent" / "x" / "\0")
        self.assertFalse(broken.update([]))

    def test_the_watcher_feeds_the_reporter(self):
        # Le chemin complet : un but detecte par le watcher se retrouve dans
        # le fichier d'etat, sans que personne ne recompte a la main.
        source = {"payload": payload(event(state="in", home_score=1))}
        guard = watcher.Watcher([LIGUE1], opener=opener_for(source))
        guard.prime()
        source["payload"] = bump(source["payload"], "away",
                                 details=(goal_detail("A1", "58'", "A. K."),))
        events = guard.refresh(LIGUE1)
        self.reporter.update(guard.all_matches(), events)

        data = state.read(self.path)
        self.assertEqual(data["goals_today"], 1)
        self.assertEqual(data["matches"][0]["away_score"], 1)


if __name__ == "__main__":
    unittest.main()
