import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from butbutbut import cli, config


def write(path, text):
    Path(path).write_text(text, encoding="utf-8")
    return Path(path)


class ConfigCase(unittest.TestCase):
    """Chaque test a son dossier : jamais le vrai fichier de l'utilisateur."""

    def setUp(self):
        box = tempfile.TemporaryDirectory()
        self.addCleanup(box.cleanup)
        self.dir = Path(box.name)
        self.path = self.dir / config.FILENAME

    def read(self, text):
        write(self.path, text)
        return config.read(self.path)


class TestReading(ConfigCase):
    def test_a_missing_file_is_silent(self):
        outcome = config.read(self.dir / "nulle-part.conf")
        self.assertFalse(outcome.found)
        self.assertEqual(outcome.values, {})
        self.assertEqual(outcome.warnings, [])

    def test_values_are_converted_to_the_type_of_the_option(self):
        outcome = self.read("[butbutbut]\n"
                            "leagues = l1,ucl\n"
                            "interval = 40\n"
                            "duration = 8.5\n"
                            "position = top-left\n"
                            "no_sound = oui\n")
        self.assertEqual(outcome.warnings, [])
        self.assertEqual(outcome.values, {
            "leagues": "l1,ucl", "interval": 40, "duration": 8.5,
            "position": "top-left", "no_sound": True})

    def test_keys_may_be_written_like_the_long_options(self):
        # "idle-interval" est le reflexe de celui qui vient de la ligne de
        # commande, et la casse ne devrait jamais etre un piege.
        outcome = self.read("[butbutbut]\nIdle-Interval = 90\nEXCLUDE = liga\n")
        self.assertEqual(outcome.warnings, [])
        self.assertEqual(outcome.values, {"idle_interval": 90, "exclude": "liga"})

    def test_an_empty_key_is_an_absent_key(self):
        outcome = self.read("[butbutbut]\nteams =\nleagues = l1\n")
        self.assertEqual(outcome.warnings, [])
        self.assertEqual(outcome.values, {"leagues": "l1"})

    def test_booleans_speak_both_languages(self):
        for text, expected in (("oui", True), ("true", True), ("1", True),
                               ("ON", True), ("non", False), ("false", False),
                               ("0", False), ("off", False)):
            outcome = self.read("[butbutbut]\nquiet = {}\n".format(text))
            self.assertEqual(outcome.values["quiet"], expected, text)
            self.assertEqual(outcome.warnings, [])

    def test_a_decimal_comma_is_accepted(self):
        outcome = self.read("[butbutbut]\nvolume = 0,8\n")
        self.assertEqual(outcome.values["volume"], 0.8)
        self.assertEqual(outcome.warnings, [])

    def test_an_unknown_key_is_reported_but_not_fatal(self):
        outcome = self.read("[butbutbut]\nchampionnat = l1\ninterval = 30\n")
        self.assertEqual(outcome.values, {"interval": 30})
        self.assertEqual(len(outcome.warnings), 1)
        self.assertIn("championnat", outcome.warnings[0])

    def test_a_text_where_a_number_belongs_is_reported(self):
        outcome = self.read("[butbutbut]\ninterval = beaucoup\nquiet = oui\n")
        self.assertNotIn("interval", outcome.values)
        self.assertEqual(outcome.values, {"quiet": True})
        self.assertEqual(len(outcome.warnings), 1)
        self.assertIn("entier", outcome.warnings[0])

    def test_an_impossible_position_is_reported(self):
        outcome = self.read("[butbutbut]\nposition = milieu-gauche\n")
        self.assertEqual(outcome.values, {})
        self.assertIn("coin inconnu", outcome.warnings[0])

    def test_a_word_that_is_neither_yes_nor_no_is_reported(self):
        outcome = self.read("[butbutbut]\nno_overlay = peut-etre\n")
        self.assertEqual(outcome.values, {})
        self.assertIn("no_overlay", outcome.warnings[0])

    def test_an_unknown_league_drops_the_selection_without_stopping(self):
        outcome = self.read("[butbutbut]\n"
                            "leagues = championnat-de-mars\nquiet = oui\n")
        self.assertEqual(outcome.values, {"quiet": True})
        self.assertIn("championnat-de-mars", outcome.warnings[0])

    def test_excluding_everything_drops_the_selection_without_stopping(self):
        outcome = self.read("[butbutbut]\nleagues = l1\nexclude = l1\n")
        self.assertEqual(outcome.values, {})
        self.assertEqual(len(outcome.warnings), 1)

    def test_a_malformed_file_is_ignored_with_a_warning(self):
        outcome = self.read("ceci n'est pas un fichier ini\n[[[\n")
        self.assertTrue(outcome.found)
        self.assertEqual(outcome.values, {})
        self.assertEqual(len(outcome.warnings), 1)
        self.assertIn(str(self.path), outcome.warnings[0])
        # Le message tient sur une ligne : le journal en depend.
        self.assertNotIn("\n", outcome.warnings[0])

    def test_a_file_without_our_section_is_ignored_with_a_warning(self):
        outcome = self.read("[autre]\nleagues = l1\n")
        self.assertEqual(outcome.values, {})
        self.assertIn("[butbutbut]", outcome.warnings[0])

    def test_an_unreadable_file_is_ignored_with_a_warning(self):
        # Un dossier a la place du fichier : illisible sur tous les systemes.
        folder = self.dir / "dossier.conf"
        folder.mkdir()
        outcome = config.read(folder)
        self.assertEqual(outcome.values, {})
        self.assertEqual(len(outcome.warnings), 1)
        self.assertIn("illisible", outcome.warnings[0])

    def test_bytes_that_are_not_utf8_are_ignored_with_a_warning(self):
        self.path.write_bytes(b"[butbutbut]\nteams = \xff\xfe\n")
        outcome = config.read(self.path)
        self.assertEqual(outcome.values, {})
        self.assertIn("illisible", outcome.warnings[0])


class TestPrecedence(ConfigCase):
    """Ligne de commande > fichier > defauts."""

    def parse(self, text, argv):
        write(self.path, text)
        parser = cli.build_parser()
        outcome = config.apply(parser, self.path)
        return parser.parse_args(argv), outcome

    def test_defaults_win_when_there_is_no_file(self):
        parser = cli.build_parser()
        config.apply(parser, self.dir / "absent.conf")
        args = parser.parse_args([])
        self.assertEqual(args.interval, cli.DEFAULT_INTERVAL)
        self.assertEqual(args.position, cli.DEFAULT_POSITION)
        self.assertIsNone(args.leagues)

    def test_the_file_wins_over_the_defaults(self):
        args, outcome = self.parse(
            "[butbutbut]\nleagues = l1,ucl\ninterval = 40\nquiet = oui\n", [])
        self.assertEqual(outcome.warnings, [])
        self.assertEqual(args.leagues, "l1,ucl")
        self.assertEqual(args.interval, 40)
        self.assertTrue(args.quiet)

    def test_the_command_line_wins_over_the_file(self):
        args, _ = self.parse(
            "[butbutbut]\nleagues = l1,ucl\ninterval = 40\n",
            ["--leagues", "pl", "--interval", "10"])
        self.assertEqual(args.leagues, "pl")
        self.assertEqual(args.interval, 10)

    def test_the_command_line_wins_even_when_it_types_the_default(self):
        """Le piege : --interval 25 vaut le defaut, et doit gagner quand meme.

        Compare les valeurs apres coup ne suffirait pas a le voir ; c'est
        justement pourquoi le fichier passe par set_defaults() avant l'analyse.
        """
        args, _ = self.parse(
            "[butbutbut]\ninterval = 40\nposition = top-left\n",
            ["--interval", str(cli.DEFAULT_INTERVAL),
             "--position", cli.DEFAULT_POSITION])
        self.assertEqual(args.interval, cli.DEFAULT_INTERVAL)
        self.assertEqual(args.position, cli.DEFAULT_POSITION)

    def test_a_key_the_file_does_not_set_keeps_its_default(self):
        args, _ = self.parse("[butbutbut]\ninterval = 40\n", [])
        self.assertEqual(args.idle_interval, cli.DEFAULT_IDLE_INTERVAL)
        self.assertEqual(args.volume, cli.DEFAULT_VOLUME)

    def test_a_broken_file_leaves_every_default_in_place(self):
        args, outcome = self.parse("pas du tout un fichier ini\n[[[", [])
        self.assertTrue(outcome.warnings)
        self.assertEqual(args.interval, cli.DEFAULT_INTERVAL)
        self.assertEqual(args.position, cli.DEFAULT_POSITION)
        self.assertIsNone(args.leagues)


class TestChosenPath(ConfigCase):
    def test_config_designates_another_file(self):
        other = self.dir / "ailleurs.conf"
        self.assertEqual(config.path_from(["--config", str(other)], self.path),
                         other)

    def test_without_config_the_data_dir_file_is_used(self):
        self.assertEqual(config.path_from(["--leagues", "l1"], self.path),
                         self.path)

    def test_a_config_without_a_value_falls_back_without_crashing(self):
        # Le vrai parseur dira l'erreur ; le mini-parseur ne doit pas mourir.
        self.assertEqual(config.path_from(["--config"], self.path), self.path)

    def test_the_data_dir_holds_the_config_file(self):
        self.assertEqual(cli.paths()["config"].name, config.FILENAME)
        self.assertEqual(cli.paths()["config"].parent, cli.paths()["data"])


class TestExampleFile(ConfigCase):
    def setUp(self):
        super().setUp()
        self.parser = cli.build_parser()
        self.text = config.example(self.parser)

    def test_every_key_is_documented_and_commented_out(self):
        self.assertIn("[butbutbut]", self.text)
        for option in config.OPTIONS:
            self.assertIn("# {} = ".format(option.name), self.text)
            self.assertNotIn("\n{} = ".format(option.name), self.text)

    def test_every_key_exists_in_the_parser(self):
        """Le fichier ne doit jamais proposer une option que le programme ignore."""
        known = vars(self.parser.parse_args([]))
        for option in config.OPTIONS:
            self.assertIn(option.name, known)

    def test_defaults_are_written_in_plain_words(self):
        self.assertIn("# defaut : les 5 grands championnats", self.text)
        self.assertIn("# defaut : {}".format(cli.DEFAULT_INTERVAL), self.text)
        self.assertIn("# defaut : non", self.text)

    def test_the_file_is_ascii_only(self):
        self.text.encode("ascii")

    def test_uncommenting_everything_gives_a_valid_file(self):
        lines = []
        for line in self.text.splitlines():
            body = line[2:] if line.startswith("# ") else line
            name = body.split("=")[0].strip()
            lines.append(body if line.startswith("# ") and name in config.BY_NAME
                         else line)
        outcome = self.read("\n".join(lines) + "\n")

        self.assertEqual(outcome.warnings, [])
        self.assertEqual(sorted(outcome.values), sorted(config.BY_NAME))
        self.assertIsInstance(outcome.values["interval"], int)
        self.assertIsInstance(outcome.values["opacity"], float)
        self.assertIsInstance(outcome.values["no_sound"], bool)

    def test_writing_creates_the_file_and_its_parent_dir(self):
        target = self.dir / "creux" / "butbutbut.conf"
        written, message = config.write_example(target, self.parser)
        self.assertTrue(written, message)
        self.assertEqual(target.read_text(encoding="utf-8"), self.text)

    def test_an_existing_file_is_never_overwritten_in_silence(self):
        write(self.path, "[butbutbut]\nleagues = l1\n")
        written, message = config.write_example(self.path, self.parser)
        self.assertFalse(written)
        self.assertIn("existe deja", message)
        self.assertIn("leagues = l1", self.path.read_text(encoding="utf-8"))


class TestMainWiring(ConfigCase):
    """Ce que main() fait vraiment du fichier."""

    def run_main(self, argv):
        seen = {}

        def capture(args):
            seen["args"] = args
            return 0

        err, out = io.StringIO(), io.StringIO()
        with mock.patch.object(cli, "do_paths", capture):
            with redirect_stderr(err), redirect_stdout(out):
                code = cli.main(list(argv) + ["--paths"])
        return seen.get("args"), code, err.getvalue(), out.getvalue()

    def test_the_file_reaches_the_commands(self):
        write(self.path, "[butbutbut]\nleagues = l1,ucl\nscale = 1.4\n")
        args, code, err, _out = self.run_main(["--config", str(self.path)])
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertEqual(args.leagues, "l1,ucl")
        self.assertEqual(args.scale, 1.4)
        self.assertEqual(args.config, self.path)

    def test_the_command_line_still_wins_inside_main(self):
        write(self.path, "[butbutbut]\nleagues = l1,ucl\n")
        args, _code, _err, _out = self.run_main(
            ["--config", str(self.path), "--leagues", "pl"])
        self.assertEqual(args.leagues, "pl")

    def test_a_broken_file_warns_on_stderr_and_starts_anyway(self):
        write(self.path, "n'importe quoi\n[[[\n")
        args, code, err, _out = self.run_main(["--config", str(self.path)])
        self.assertEqual(code, 0)
        self.assertIn("butbutbut :", err)
        self.assertIsNone(args.leagues)

    def test_an_unknown_key_warns_on_stderr_and_starts_anyway(self):
        write(self.path, "[butbutbut]\nchampionnat = l1\nscale = 2\n")
        args, code, err, _out = self.run_main(["--config", str(self.path)])
        self.assertEqual(code, 0)
        self.assertIn("championnat", err)
        self.assertEqual(args.scale, 2.0)

    def test_write_config_writes_then_refuses_to_overwrite(self):
        target = self.dir / "neuf.conf"
        argv = ["--config", str(target), "--write-config"]

        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            self.assertEqual(cli.main(argv), 0)
        self.assertTrue(target.exists())
        self.assertIn("[butbutbut]", target.read_text(encoding="utf-8"))
        self.assertIn(str(target), out.getvalue())

        stamp = target.read_text(encoding="utf-8")
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            self.assertEqual(cli.main(argv), 1)
        self.assertIn("existe deja", err.getvalue())
        self.assertEqual(target.read_text(encoding="utf-8"), stamp)

    def test_the_example_announces_the_defaults_of_the_parser_it_is_given(self):
        """D'ou le parseur neuf dans main() : sinon l'exemple recopierait le
        fichier deja charge au lieu d'annoncer les defauts du programme."""
        parser = cli.build_parser()
        write(self.path, "[butbutbut]\ninterval = 40\n")
        config.apply(parser, self.path)

        self.assertIn("# defaut : 40", config.example(parser))
        self.assertIn("# defaut : {}".format(cli.DEFAULT_INTERVAL),
                      config.example(cli.build_parser()))


class TestNoOptionIsForgotten(unittest.TestCase):
    """Le fichier doit suivre la ligne de commande, sinon il ment.

    Ecrit apres avoir constate qu'une option ajoutee au parseur n'atterrissait
    pas dans le fichier : `--write-config` proposait alors un fichier complet
    ou quatre reglages etaient tout simplement absents.
    """

    # Ce qui n'a aucun sens dans un fichier : les commandes ponctuelles, et le
    # chemin du fichier lui-meme.
    ACTIONS = {
        "test", "scores", "status", "stop", "paths", "screens", "today",
        "list_leagues", "list_teams", "regen_sound", "write_config", "config",
        "update", "check_update", "dev",
    }

    def test_every_lasting_option_has_its_key(self):
        parser = cli.build_parser()
        lasting = {action.dest for action in parser._actions
                   if action.dest not in ("help", "version")} - self.ACTIONS
        known = {option.name for option in config.OPTIONS}
        self.assertEqual(sorted(lasting - known), [],
                         "options absentes du fichier de configuration")

    def test_no_key_without_its_option(self):
        parser = cli.build_parser()
        dests = {action.dest for action in parser._actions}
        for option in config.OPTIONS:
            self.assertIn(option.name, dests, option.name)


if __name__ == "__main__":
    unittest.main()
