import io
import re
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from butbutbut import cli, espn, leagues

from helpers import event, payload


class TestParser(unittest.TestCase):
    def setUp(self):
        self.parser = cli.build_parser()

    def test_defaults(self):
        args = self.parser.parse_args([])
        self.assertIsNone(args.leagues)
        self.assertIsNone(args.exclude)
        self.assertFalse(args.list_leagues)
        self.assertEqual(args.test, 0)
        self.assertEqual(args.interval, cli.DEFAULT_INTERVAL)
        self.assertEqual(args.idle_interval, cli.DEFAULT_IDLE_INTERVAL)
        self.assertEqual(args.position, cli.DEFAULT_POSITION)
        self.assertIsNone(args.duration)
        self.assertFalse(args.no_sound)
        self.assertFalse(args.no_overlay)
        self.assertFalse(args.no_phase_cards)
        self.assertFalse(args.quiet)

    def test_flags(self):
        args = self.parser.parse_args(
            ["--leagues", "l1,pl", "--exclude", "pl",
             "--interval", "10", "--idle-interval", "120",
             "--position", "top-left", "--screen", "1", "--duration", "8",
             "--no-sound", "--no-overlay", "--no-phase-cards", "--quiet"])
        self.assertEqual(args.leagues, "l1,pl")
        self.assertEqual(args.exclude, "pl")
        self.assertEqual(args.interval, 10)
        self.assertEqual(args.idle_interval, 120)
        self.assertEqual(args.position, "top-left")
        self.assertEqual(args.screen, "1")
        self.assertEqual(args.duration, 8.0)
        self.assertTrue(args.no_sound and args.no_overlay and args.quiet)
        self.assertTrue(args.no_phase_cards)


class TestMainGuards(unittest.TestCase):
    def test_unknown_position_is_refused(self):
        self.assertEqual(cli.main(["--position", "milieu-gauche"]), 2)

    def test_unknown_league_is_refused(self):
        # Un nom qui n'existe pas : main() doit rendre 2 sans jamais demarrer
        # la surveillance.
        self.assertEqual(cli.main(["--leagues", "championnat-de-mars"]), 2)

    def test_excluding_everything_is_refused(self):
        self.assertEqual(cli.main(["--leagues", "l1", "--exclude", "l1"]), 2)

    def test_unknown_exclusion_is_refused(self):
        self.assertEqual(cli.main(["--exclude", "championnat-de-mars"]), 2)

    def test_list_command(self):
        self.assertEqual(cli.main(["--list"]), 0)

    def test_paths_command(self):
        self.assertEqual(cli.main(["--paths"]), 0)

    def test_screens_command(self):
        self.assertEqual(cli.main(["--screens"]), 0)


class TestEveryCommandIsReachable(unittest.TestCase):
    """main() ne doit jamais appeler une fonction qui n'existe pas.

    Ecrit apres avoir casse do_status, do_test, do_scores et _kickoff_text en
    supprimant une fonction voisine : la suite passait quand meme, parce que
    plus aucun test n'entrait dans ces commandes.
    """

    def test_all_dispatch_targets_exist(self):
        source = Path(cli.__file__).read_text(encoding="utf-8")
        body = source[source.index("def main("):]
        called = set(re.findall(r"return (do_\w+)\(args\)", body))
        self.assertGreaterEqual(len(called), 7, called)
        for name in sorted(called):
            self.assertTrue(callable(getattr(cli, name, None)),
                            "main() appelle {}(), absent du module".format(name))

    def test_every_command_runs_without_touching_the_network(self):
        matches = espn.parse(payload(event(state="in", home_score=1)),
                             leagues.BY_SLUG["fra.1"])
        commands = (["--status"], ["--scores"], ["--list"], ["--paths"],
                    ["--screens"],
                    ["--test", "--no-overlay", "--no-sound", "--duration", "1"])

        with mock.patch.object(espn, "scoreboard", return_value=matches):
            for argv in commands:
                buffer = io.StringIO()
                with redirect_stdout(buffer):
                    code = cli.main(argv + ["--leagues", "l1"])
                self.assertEqual(code, 0, argv)
                self.assertTrue(buffer.getvalue().strip(), argv)

    def test_scores_shows_the_match_and_its_scorers(self):
        matches = espn.parse(payload(event(state="in", home_score=1)),
                             leagues.BY_SLUG["fra.1"])
        buffer = io.StringIO()
        with mock.patch.object(espn, "scoreboard", return_value=matches):
            with redirect_stdout(buffer):
                cli.main(["--scores", "--leagues", "l1"])
        printed = buffer.getvalue()
        self.assertIn("Ligue 1", printed)
        self.assertIn("Angers", printed)
        self.assertIn("Stade Rennais", printed)

    def test_status_reports_the_source_being_unreachable(self):
        with mock.patch.object(espn, "scoreboard",
                               side_effect=espn.SourceError("pas de reseau")):
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                code = cli.main(["--status", "--leagues", "l1"])
        self.assertEqual(code, 1)
        self.assertIn("ECHEC", buffer.getvalue())


class TestPaths(unittest.TestCase):
    def test_all_paths_live_under_the_data_dir(self):
        paths = cli.paths()
        self.assertEqual(set(paths), {"data", "sound", "wav", "log", "pid"})
        root = paths["data"]
        for key, value in paths.items():
            self.assertIsInstance(value, Path)
            if key != "data":
                self.assertEqual(value.parent, root)

    def test_data_dir_is_platform_specific(self):
        self.assertIn("butbutbut", str(cli.data_dir()).lower())


class TestWatchLoops(unittest.TestCase):
    def test_both_loops_announce_their_wait(self):
        # Une boucle qui appellerait next_delay() dormirait sans rien promettre
        # au watcher : la sortie de veille repasserait inapercue.
        source = Path(cli.__file__).read_text(encoding="utf-8")
        self.assertEqual(source.count("stopping.wait(guard.plan_wait())"), 2)
        self.assertNotIn("guard.next_delay()", source)


class TestSoundResolution(unittest.TestCase):
    def test_no_sound_gives_no_path_and_the_default_duration(self):
        args = cli.build_parser().parse_args(["--no-sound"])
        path, duration = cli.resolve_sound(args)
        self.assertIsNone(path)
        self.assertEqual(duration, cli.DEFAULT_DURATION)

    def test_explicit_duration_is_kept(self):
        args = cli.build_parser().parse_args(["--duration", "12"])
        _path, duration = cli.resolve_sound(args)
        self.assertEqual(duration, 12.0)

    def test_card_stays_at_least_as_long_as_the_sound(self):
        args = cli.build_parser().parse_args([])
        _path, duration = cli.resolve_sound(args)
        self.assertGreaterEqual(duration, cli.DEFAULT_DURATION)


class TestPidFile(unittest.TestCase):
    def test_dead_pid_is_not_considered_running(self):
        self.assertFalse(cli._process_alive(-1))
        self.assertFalse(cli._process_alive(0))

    def test_our_own_pid_is_alive(self):
        import os

        self.assertTrue(cli._process_alive(os.getpid()))


if __name__ == "__main__":
    unittest.main()
