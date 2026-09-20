import io
import shutil
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

from butbutbut import chronicle, cli, journal


def entry(day, clock, text):
    return journal.parse_line("{} {}  {}".format(day, clock, text))


DAY = "2026-09-19"
NICE = ("BUT [Ligue 1] Nice 1 - 0 Lens pour Nice - "
        "But de G. Laborde (12')")
ARSENAL = ("BUT [Premier League] Arsenal 1 - 0 Chelsea pour Arsenal - "
           "But de M. Odegaard (30')")


class TestNight(unittest.TestCase):
    def test_the_latest_evening_is_selected_and_crosses_midnight(self):
        rows = [entry(DAY, "23:58:00", NICE),
                entry("2026-09-20", "00:02:00", ARSENAL)]
        self.assertEqual(chronicle.evenings(rows), [DAY])
        page = chronicle.render_night(rows)
        self.assertIn("La Nuit", page)
        self.assertIn("G. Laborde", page)
        self.assertIn("M. Odegaard", page)
        self.assertIn("2</strong><span>buts confirmés", page)

    def test_var_removes_the_goal_from_the_timeline(self):
        rows = [entry(DAY, "20:00:00", NICE), entry(
            DAY, "20:01:00", "BUT ANNULE [Ligue 1] Nice 0 - 0 Lens "
                                "pour Nice - Score corrige (13')")]
        page = chronicle.render_night(rows, DAY)
        self.assertNotIn("G. Laborde", page)
        self.assertIn("0</strong><span>buts confirmés", page)

    def test_user_text_is_escaped_and_the_page_is_autonomous(self):
        row = entry(DAY, "20:00:00", "BUT [Ligue 1] A &lt; B 1 - 0 Lens "
                                      "pour A &lt; B - But de X (1')")
        page = chronicle.render_night([row], DAY)
        self.assertNotIn("https://", page)
        self.assertNotIn("<script", page)


class TestConstellation(unittest.TestCase):
    def test_one_confirmed_goal_makes_one_star(self):
        rows = [entry(DAY, "20:00:00", NICE),
                entry(DAY, "20:05:00", ARSENAL)]
        page = chronicle.render_constellation(rows)
        self.assertEqual(page.count("<circle "), 2)
        self.assertIn("12&#x27;", page)
        self.assertIn("30&#x27;", page)
        self.assertIn("Ligue 1", page)
        self.assertIn("Premier League", page)

    def test_an_unknown_minute_is_owned_up_to(self):
        row = entry(DAY, "20:00:00", "BUT [NHL] Boston 1 - 0 Toronto pour "
                                      "Boston - But de X (12:34)")
        page = chronicle.render_constellation([row])
        self.assertIn("minute inconnue", page)


class TestChronicleCli(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).parent / ".chronicle-tests" / self._testMethodName
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True)
        patcher = mock.patch.object(cli, "data_dir", return_value=root)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        self.paths = cli.paths()
        self.paths["log"].parent.mkdir(parents=True, exist_ok=True)

    def write(self, *rows):
        self.paths["log"].write_text("\n".join(rows) + "\n", encoding="utf-8")

    def run_cli(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_night_writes_the_latest_evening(self):
        today = datetime.now().strftime("%Y-%m-%d")
        self.write("{} 20:00:00  {}".format(today, NICE))
        target = self.paths["data"] / "nuit.html"
        code, printed, errors = self.run_cli(
            ["--night", "--chronicle-output", str(target)])
        self.assertEqual((code, errors), (0, ""))
        self.assertTrue(target.exists())
        self.assertIn("Nuit des buts", printed)

    def test_constellation_obeys_the_period(self):
        today = datetime.now().strftime("%Y-%m-%d")
        old = (datetime.now() - timedelta(days=40)).strftime("%Y-%m-%d")
        self.write("{} 20:00:00  {}".format(old, ARSENAL),
                   "{} 20:00:00  {}".format(today, NICE))
        target = self.paths["data"] / "stars.html"
        code, _printed, errors = self.run_cli(
            ["--constellation", "--week", "--chronicle-output", str(target)])
        self.assertEqual((code, errors), (0, ""))
        page = target.read_text(encoding="utf-8")
        self.assertIn("G. Laborde", page)
        self.assertNotIn("M. Odegaard", page)

    def test_empty_journal_is_explained(self):
        code, _printed, errors = self.run_cli(["--night"])
        self.assertEqual(code, 1)
        self.assertIn("aucun but", errors)

    def test_output_without_a_story_command_is_refused(self):
        code, _printed, errors = self.run_cli(
            ["--chronicle-output", "somewhere.html"])
        self.assertEqual(code, 2)
        self.assertIn("ne sert qu'avec", errors)


if __name__ == "__main__":
    unittest.main()
