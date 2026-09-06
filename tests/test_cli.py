import unittest
from pathlib import Path

from butbutbut import cli


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
        self.assertFalse(args.quiet)

    def test_flags(self):
        args = self.parser.parse_args(
            ["--leagues", "l1,pl", "--exclude", "pl",
             "--interval", "10", "--idle-interval", "120",
             "--position", "top-left", "--screen", "1", "--duration", "8",
             "--no-sound", "--no-overlay", "--quiet"])
        self.assertEqual(args.leagues, "l1,pl")
        self.assertEqual(args.exclude, "pl")
        self.assertEqual(args.interval, 10)
        self.assertEqual(args.idle_interval, 120)
        self.assertEqual(args.position, "top-left")
        self.assertEqual(args.screen, "1")
        self.assertEqual(args.duration, 8.0)
        self.assertTrue(args.no_sound and args.no_overlay and args.quiet)


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
