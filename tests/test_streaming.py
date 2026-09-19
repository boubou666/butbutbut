import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from butbutbut import streaming


class TestDelay(unittest.TestCase):
    def event(self, at):
        return SimpleNamespace(at=at)

    def test_an_event_waits_for_the_stream(self):
        delay = streaming.Delay(30, now=100)
        event = self.event(100)
        self.assertEqual(delay.push([event], now=120), [])
        self.assertEqual(delay.next_wait(60, now=120), 10)
        self.assertEqual(delay.ready(now=130), [event])

    def test_a_live_command_redates_what_is_waiting(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "control.json"
            delay = streaming.Delay(30, path, now=100)
            event = self.event(100)
            delay.push([event], now=101)
            streaming.request(path, 5, now=102)
            self.assertTrue(delay.poll())
            self.assertEqual(delay.seconds, 5)
            self.assertEqual(delay.ready(now=105), [event])

    def test_a_command_left_by_an_old_daemon_is_ignored(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "control.json"
            streaming.request(path, 90, now=50)
            delay = streaming.Delay(0, path, now=100)
            self.assertFalse(delay.poll())
            self.assertEqual(delay.seconds, 0)


class TestCalibration(unittest.TestCase):
    def test_the_visible_kickoff_measures_the_delay(self):
        self.assertEqual(streaming.delay_from_kickoff(
            {"last_kickoff_at": 100}, now=187), 87)

    def test_a_missing_kickoff_is_refused(self):
        with self.assertRaises(streaming.Invalid):
            streaming.delay_from_kickoff({}, now=time.time())

    def test_a_match_can_be_selected_in_a_multiplex(self):
        state = {
            "last_kickoff_at": 120,
            "recent_kickoffs": [
                {"id": "1", "at": 100, "match": "Marseille 0 - 0 Lyon"},
                {"id": "2", "at": 120, "match": "Paris 0 - 0 Lille"},
            ],
        }
        self.assertEqual(streaming.delay_from_kickoff(
            state, now=190, match="marseille"), 90)


if __name__ == "__main__":
    unittest.main()
