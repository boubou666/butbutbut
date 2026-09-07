import io
import json
import os
import re
import threading
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from butbutbut import (cli, espn, hook, i18n, leagues, pinned, sound,
                       state, watcher)

from helpers import at_local_hour, event, goal_detail, in_minutes, payload


_LANGUE = {}


def setUpModule():
    # Ces tests lancent cli.main() sans --lang et affirment des libelles
    # francais. Sans cela la langue vient de la detection : ils passeraient sur
    # une machine francaise et echoueraient sur la CI, dont les machines sont
    # anglaises. On passe par la variable d'environnement plutot que par
    # i18n.use(), parce que main() refixe la langue a chaque appel.
    _LANGUE["avant"] = os.environ.get(i18n.ENV)
    os.environ[i18n.ENV] = "fr"
    i18n.use("fr")


def tearDownModule():
    if _LANGUE["avant"] is None:
        os.environ.pop(i18n.ENV, None)
    else:
        os.environ[i18n.ENV] = _LANGUE["avant"]

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
        # Les nouvelles cartes ne s'invitent pas : il faut les demander.
        self.assertFalse(args.red_cards)
        # Le silence au reveil reste le comportement livre.
        self.assertFalse(args.catch_up)
        self.assertEqual(args.before_kickoff, 0)
        self.assertFalse(args.quiet)
        self.assertEqual(args.retry_fullscreen, 0.0)

    def test_retry_fullscreen_is_opt_in(self):
        # Sans valeur : la duree par defaut. Avec : celle qu'on donne.
        self.assertEqual(
            self.parser.parse_args(["--retry-fullscreen"]).retry_fullscreen,
            cli.RETRY_FULLSCREEN)
        self.assertEqual(
            self.parser.parse_args(["--retry-fullscreen", "45"]).retry_fullscreen,
            45.0)

    def test_the_new_cards_are_opt_in(self):
        args = self.parser.parse_args(["--red-cards", "--before-kickoff", "5",
                                       "--catch-up"])
        self.assertTrue(args.red_cards)
        self.assertEqual(args.before_kickoff, 5)
        self.assertTrue(args.catch_up)


    def test_a_negative_countdown_is_read_as_disabled(self):
        with mock.patch.object(cli, "do_daemon", return_value=0) as daemon:
            cli.main(["--before-kickoff", "-3", "--leagues", "l1"])
        self.assertEqual(daemon.call_args[0][0].before_kickoff, 0)

    def test_flags(self):
        args = self.parser.parse_args(
            ["--leagues", "l1,pl", "--exclude", "pl",
             "--interval", "10", "--idle-interval", "120",
             "--position", "top-left", "--screen", "1", "--duration", "8",
             "--no-sound", "--no-overlay", "--no-phase-cards", "--red-cards",
             "--before-kickoff", "10", "--quiet"])
        self.assertEqual(args.leagues, "l1,pl")
        self.assertEqual(args.exclude, "pl")
        self.assertEqual(args.interval, 10)
        self.assertEqual(args.idle_interval, 120)
        self.assertEqual(args.position, "top-left")
        self.assertEqual(args.screen, "1")
        self.assertEqual(args.duration, 8.0)
        self.assertTrue(args.no_sound and args.no_overlay and args.quiet)
        self.assertTrue(args.no_phase_cards)
        self.assertTrue(args.red_cards)
        self.assertEqual(args.before_kickoff, 10)

    def test_the_three_team_lists_cohabit(self):
        args = self.parser.parse_args(
            ["--teams", "om,psg", "--exclude-teams", "psg",
             "--spoiler-free", "om"])
        self.assertEqual(args.teams, "om,psg")
        self.assertEqual(args.exclude_teams, "psg")
        self.assertEqual(args.spoiler_free, "om")
        self.assertEqual(cli.spoiler_filter(args).wanted_tokens, ["om"])

    def test_spoiler_free_is_off_by_default(self):
        args = self.parser.parse_args([])
        self.assertIsNone(args.spoiler_free)
        self.assertIsNone(cli.spoiler_filter(args))


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
        self.assertEqual(set(paths),
                         {"data", "sound", "logos", "wav", "log", "pid",
                          "config", "state"})
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
class TestCrestCache(unittest.TestCase):
    def test_the_cache_lives_in_the_data_dir(self):
        args = cli.build_parser().parse_args([])
        cache = cli.crest_cache(args)
        self.assertTrue(cache.enabled)
        self.assertEqual(cache.directory, cli.paths()["logos"])

    def test_no_logos_switches_the_cache_off(self):
        args = cli.build_parser().parse_args(["--no-logos"])
        self.assertTrue(args.no_logos)
        cache = cli.crest_cache(args)
        self.assertFalse(cache.enabled)
        # Eteint, il ne rend rien et ne demande rien au reseau.
        self.assertIsNone(cache.get("https://exemple/1.png"))
        self.assertFalse(cache.prefetch("https://exemple/1.png"))


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


class TestActivity(unittest.TestCase):
    """--status et --today, sur un dossier de donnees fabrique."""

    LOG = "\n".join((
        "2026-09-05 22:10:04  BUT [Ligue 1] Nice 1 - 0 Lens pour Nice - "
        "But de G. Laborde (12')",
        "{day} 18:43:27  BUT [Premier League] Arsenal 2 - 1 Chelsea pour "
        "Arsenal - But de M. Odegaard (50')",
        "{day} 18:51:10  BUT [Ligue 1] Angers 1 - 0 Stade Rennais pour "
        "Angers - Penalty de C. Arcus (61')",
        "{day} 18:52:44  BUT ANNULE [Ligue 1] Angers 0 - 0 Stade Rennais "
        "pour Angers - Score corrige (62')",
    ))

    def setUp(self):
        self.tmp = TemporaryDirectory()
        root = Path(self.tmp.name)
        patcher = mock.patch.object(cli, "data_dir", return_value=root)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)
        self.paths = cli.paths()

    def run_cli(self, argv):
        matches = espn.parse(payload(event(state="in", home_score=1)),
                             leagues.BY_SLUG["fra.1"])
        buffer = io.StringIO()
        with mock.patch.object(espn, "scoreboard", return_value=matches):
            with redirect_stdout(buffer):
                code = cli.main(argv + ["--leagues", "l1"])
        return code, buffer.getvalue()

    def write_state(self, **extra):
        data = {
            "version": 1, "pid": os.getpid(), "updated_at": time.time(),
            "updated_text": "2026-09-06 18:52:44", "day": state.today(),
            "goals_today": 3, "interval": 25, "idle_interval": 300,
            "leagues": ["Ligue 1"], "total_matches": 4,
            "matches": [{"league": "Premier League", "home": "Arsenal",
                         "away": "Chelsea", "home_score": 2, "away_score": 1,
                         "clock": "50'"}],
        }
        data.update(extra)
        self.paths["state"].parent.mkdir(parents=True, exist_ok=True)
        self.paths["state"].write_text(json.dumps(data), encoding="utf-8")

    def pretend_the_daemon_runs(self):
        self.paths["pid"].parent.mkdir(parents=True, exist_ok=True)
        self.paths["pid"].write_text(str(os.getpid()))

    # ------------------------------------------------------------ status ---

    def test_status_shows_the_last_poll_and_the_live_matches(self):
        self.pretend_the_daemon_runs()
        self.write_state()
        code, printed = self.run_cli(["--status"])
        self.assertEqual(code, 0)
        self.assertIn("il y a", printed)
        self.assertIn("Arsenal 2 - 1 Chelsea", printed)
        self.assertIn("1 match(s) sur 4 au programme", printed)
        self.assertIn("buts du jour: 3", printed)

    def test_status_says_when_there_is_no_state_yet(self):
        code, printed = self.run_cli(["--status"])
        self.assertEqual(code, 0)
        self.assertIn("releve", printed)
        self.assertNotIn("Traceback", printed)

    def test_status_survives_a_truncated_state_file(self):
        self.pretend_the_daemon_runs()
        self.paths["state"].parent.mkdir(parents=True, exist_ok=True)
        self.paths["state"].write_text('{"matches": [{"home": "Ars',
                                       encoding="utf-8")
        code, printed = self.run_cli(["--status"])
        self.assertEqual(code, 0)
        self.assertIn("releve", printed)

    def test_status_warns_when_the_daemon_stopped_polling(self):
        # Le signal qui manquait : un daemon vivant mais muet depuis 20 min
        # alors qu'un match est en cours.
        self.pretend_the_daemon_runs()
        self.write_state(updated_at=time.time() - 1200)
        _code, printed = self.run_cli(["--status"])
        self.assertIn("(!)", printed)
        # L'etat est perime : ses matchs ne sont plus affiches comme en cours.
        self.assertNotIn("Arsenal 2 - 1 Chelsea", printed)

    def test_status_ignores_a_goal_counter_from_another_day(self):
        self.pretend_the_daemon_runs()
        self.write_state(day="1998-07-12")
        _code, printed = self.run_cli(["--status"])
        self.assertIn("buts du jour: 0", printed)

    # ------------------------------------------------------------- today ---

    def test_today_recaps_the_goals_by_competition(self):
        self.paths["log"].parent.mkdir(parents=True, exist_ok=True)
        self.paths["log"].write_text(self.LOG.format(day=state.today()),
                                     encoding="utf-8")
        code, printed = self.run_cli(["--today"])
        self.assertEqual(code, 0)
        self.assertIn("Premier League", printed)
        self.assertIn("18:43:27", printed)
        self.assertIn("Arsenal 2 - 1 Chelsea", printed)
        self.assertIn("But de M. Odegaard (50')", printed)
        self.assertIn("Penalty de C. Arcus (61')", printed)
        self.assertIn("2 but(s) dans 2 competition(s)", printed)
        # Le but annule est montre, mais ne compte pas.
        self.assertIn("Score corrige", printed)
        # Hier n'est pas aujourd'hui.
        self.assertNotIn("G. Laborde", printed)

    def test_today_without_a_journal(self):
        code, printed = self.run_cli(["--today"])
        self.assertEqual(code, 0)
        self.assertIn("aucun but", printed)

    def test_today_is_reachable_from_main(self):
        self.assertIn("--today", cli.build_parser().format_help())


def days_ago(count) -> str:
    """Un jour du journal, compte a rebours depuis aujourd'hui."""
    return "{:%Y-%m-%d}".format(datetime.now() - timedelta(days=count))


def end_of_last_month() -> str:
    """Le dernier jour du mois precedent, quel que soit le jour du test.

    Une bascule de mois ne s'ecrit pas en dur : le test tournerait juste onze
    mois sur douze.
    """
    midnight = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    return "{:%Y-%m-%d}".format(midnight.replace(day=1) - timedelta(days=1))


class TestRecaps(unittest.TestCase):
    """--week, --month, --since et --top-scorers, sur des journaux fabriques."""

    NICE = "BUT [Ligue 1] Nice 1 - 0 Lens pour Nice - But de G. Laborde (12')"
    ARSENAL = ("BUT [Premier League] Arsenal 1 - 0 Chelsea pour Arsenal - "
               "But de M. Odegaard (30')")
    GIRONA = ("BUT [LaLiga] Girona 0 - 1 Real Madrid pour Real Madrid - "
              "But de K. Mbappe (50')")

    def setUp(self):
        self.tmp = TemporaryDirectory()
        patcher = mock.patch.object(cli, "data_dir",
                                    return_value=Path(self.tmp.name))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)
        self.paths = cli.paths()

    def write_log(self, *rows):
        """Ecrit un journal a partir de (jour, heure, texte)."""
        lines = ["{} {}  {}".format(day, clock, text)
                 for day, clock, text in rows]
        self.paths["log"].parent.mkdir(parents=True, exist_ok=True)
        self.paths["log"].write_text("\n".join(lines) + "\n", encoding="utf-8")

    def run_cli(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(argv)
        return code, out.getvalue(), err.getvalue()

    # ------------------------------------------------------------ fenetres --

    def test_week_covers_the_last_seven_days_and_no_more(self):
        self.write_log(
            (days_ago(10), "20:00:00", self.GIRONA),
            (days_ago(3), "20:00:00", self.ARSENAL),
            (days_ago(0), "20:00:00", self.NICE),
        )
        code, printed, _err = self.run_cli(["--week"])
        self.assertEqual(code, 0)
        self.assertIn("M. Odegaard", printed)
        self.assertIn("G. Laborde", printed)
        self.assertNotIn("K. Mbappe", printed)      # dix jours, c'est trop vieux
        self.assertIn("2 but(s) signale(s), 2 jour(s), 2 competition(s).",
                      printed)

    def test_month_reaches_where_the_week_stops(self):
        self.write_log(
            (days_ago(20), "20:00:00", self.GIRONA),
            (days_ago(40), "20:00:00", self.ARSENAL),
        )
        _code, week, _err = self.run_cli(["--week"])
        self.assertNotIn("K. Mbappe", week)
        _code, month, _err = self.run_cli(["--month"])
        self.assertIn("K. Mbappe", month)
        self.assertNotIn("M. Odegaard", month)      # quarante jours, non plus

    def test_since_crosses_the_end_of_a_month(self):
        # Le filtre compare des chaines : le 1er du mois doit tomber dans une
        # fenetre ouverte le dernier jour du mois d'avant.
        opening = end_of_last_month()
        self.write_log(
            (opening, "20:00:00", self.NICE),
            (days_ago(0), "20:00:00", self.ARSENAL),
        )
        code, printed, _err = self.run_cli(["--since", opening])
        self.assertEqual(code, 0)
        self.assertIn("G. Laborde", printed)
        self.assertIn("M. Odegaard", printed)
        self.assertIn("2 but(s) signale(s), 2 jour(s), 2 competition(s).",
                      printed)

    def test_since_wins_over_week(self):
        self.write_log((days_ago(20), "20:00:00", self.GIRONA))
        _code, printed, _err = self.run_cli(
            ["--since", days_ago(30), "--week"])
        self.assertIn("K. Mbappe", printed)

    def test_a_date_that_is_not_one_is_refused_with_the_expected_format(self):
        for wrong in ("hier", "01/09/2026", "2026-02-30", ""):
            code, printed, errors = self.run_cli(["--since", wrong])
            self.assertEqual(code, 2, wrong)
            self.assertIn("AAAA-MM-JJ", errors, wrong)
            self.assertEqual(printed, "", wrong)

    def test_today_still_reads_a_single_day(self):
        self.write_log(
            (days_ago(1), "20:00:00", self.GIRONA),
            (days_ago(0), "20:00:00", self.NICE),
        )
        _code, printed, _err = self.run_cli(["--today"])
        self.assertIn("butbutbut : buts signales le {:%d/%m/%Y}".format(
            datetime.now()), printed)
        self.assertIn("1 but(s) dans 1 competition(s).", printed)
        self.assertNotIn("K. Mbappe", printed)

    # ---------------------------------------------------------- affichage ---

    def test_a_short_period_keeps_the_detail_of_every_goal(self):
        self.write_log(
            (days_ago(2), "20:00:00", self.NICE),
            (days_ago(0), "21:00:00", self.ARSENAL),
        )
        _code, printed, _err = self.run_cli(["--week"])
        self.assertIn("Nice 1 - 0 Lens", printed)
        self.assertIn("G. Laborde 12'", printed)     # buteur et minute du match
        self.assertIn("Premier League", printed)

    def test_a_long_period_falls_back_to_one_line_a_day(self):
        # Douze journees de quatre buts : le detail ne tiendrait pas sur un
        # ecran, chaque jour se resume alors a sa ligne.
        rows = []
        for back in range(12, 0, -1):
            for goal in range(4):
                rows.append((days_ago(back), "2{}:00:00".format(goal),
                             self.NICE))
        self.write_log(*rows)
        _code, printed, _err = self.run_cli(["--month"])
        self.assertIn("4 but(s)", printed)           # la ligne d'une journee
        self.assertIn("Ligue 1 4", printed)
        self.assertNotIn("G. Laborde", printed)      # le detail a saute
        self.assertIn("48 but(s) signale(s), 12 jour(s), 1 competition(s).",
                      printed)

    def test_no_line_runs_off_the_screen(self):
        rows = []
        for back in range(12, 0, -1):
            rows.append((days_ago(back), "20:00:00",
                         "BUT [Bundesliga] Bayer 04 Leverkusen 1 - 1 Bayern "
                         "pour Bayer 04 Leverkusen - But de P. Schick (77')"))
            rows.append((days_ago(back), "21:00:00", self.ARSENAL))
        self.write_log(*rows)
        for argv in (["--week"], ["--month"], ["--top-scorers"]):
            _code, printed, _err = self.run_cli(argv)
            longest = max(len(line) for line in printed.splitlines())
            self.assertLessEqual(longest, 80, argv)

    # ------------------------------------------------------- journal vide ---

    def test_a_missing_journal_says_so_plainly(self):
        code, printed, _err = self.run_cli(["--week"])
        self.assertEqual(code, 0)
        self.assertIn("journal vide", printed)
        self.assertIn(str(self.paths["log"]), printed)

    def test_an_empty_journal_says_so_plainly(self):
        self.paths["log"].parent.mkdir(parents=True, exist_ok=True)
        self.paths["log"].write_text("", encoding="utf-8")
        code, printed, _err = self.run_cli(["--top-scorers"])
        self.assertEqual(code, 0)
        self.assertIn("journal vide", printed)

    def test_a_period_without_a_goal_is_not_an_empty_journal(self):
        self.write_log((days_ago(40), "20:00:00", self.NICE))
        _code, printed, _err = self.run_cli(["--week"])
        self.assertIn("aucun but sur cette periode", printed)

    def test_lines_the_parser_cannot_read_are_ignored_without_a_word(self):
        self.write_log(
            (days_ago(1), "18:00:00", "demarrage (pid 3752) - les 5 champ"),
            (days_ago(1), "18:02:00", "COUP D'ENVOI [Ligue 1] Nice 0 - 0 Lens"),
            (days_ago(1), "18:04:00", "Bundesliga injoignable (timeout)"),
            (days_ago(1), "18:06:00", "BUT [Ligue 1] Nice - Lens pour Nice"),
            (days_ago(1), "18:08:00", "BUT {Ligue 1} Nice 1 - 0 Lens"),
            (days_ago(0), "20:00:00", self.NICE),
        )
        code, printed, errors = self.run_cli(["--week"])
        self.assertEqual(code, 0)
        self.assertEqual(errors, "")
        self.assertIn("1 but(s) signale(s), 1 jour(s), 1 competition(s).",
                      printed)

    # ---------------------------------------------------------- classement --

    def test_top_scorers_does_not_keep_a_goal_the_var_took_back(self):
        self.write_log(
            (days_ago(2), "20:00:00", self.ARSENAL),
            (days_ago(2), "20:30:00", "BUT [Premier League] Arsenal 2 - 0 "
                                      "Chelsea pour Arsenal - But de B. Saka (55')"),
            (days_ago(2), "20:32:00", "BUT ANNULE [Premier League] Arsenal 1 - "
                                      "0 Chelsea pour Arsenal - Score corrige (56')"),
            (days_ago(1), "20:00:00", self.ARSENAL),
        )
        code, printed, _err = self.run_cli(["--top-scorers"])
        self.assertEqual(code, 0)
        self.assertIn("M. Odegaard", printed)
        self.assertNotIn("B. Saka", printed)         # son but a ete refuse
        self.assertIn("1 buteur(s) pour 2 but(s) confirme(s) sur 3 signale(s).",
                      printed)
        self.assertIn("1 but(s) retire(s) par la VAR", printed)

    def test_top_scorers_ranks_and_shares_the_places(self):
        self.write_log(
            (days_ago(3), "20:00:00", self.NICE),
            (days_ago(2), "20:00:00", self.NICE),
            (days_ago(1), "20:00:00", self.ARSENAL),
            (days_ago(0), "20:00:00", self.GIRONA),
        )
        _code, printed, _err = self.run_cli(["--top-scorers"])
        rows = [line for line in printed.splitlines() if "  " in line
                and any(name in line for name in ("Laborde", "Odegaard",
                                                  "Mbappe"))]
        self.assertEqual(len(rows), 3)
        self.assertIn("G. Laborde", rows[0])
        self.assertIn("Nice", rows[0])
        # Deux buteurs a un but : deuxiemes tous les deux.
        self.assertTrue(rows[1].strip().startswith("2"), rows[1])
        self.assertTrue(rows[2].strip().startswith("2"), rows[2])

    def test_top_scorers_takes_the_whole_journal_by_default(self):
        self.write_log(
            (days_ago(40), "20:00:00", self.GIRONA),
            (days_ago(0), "20:00:00", self.NICE),
        )
        _code, whole, _err = self.run_cli(["--top-scorers"])
        self.assertIn("depuis le debut du journal", whole)
        self.assertIn("K. Mbappe", whole)
        _code, week, _err = self.run_cli(["--top-scorers", "--week"])
        self.assertNotIn("K. Mbappe", week)
        self.assertIn("G. Laborde", week)

    def test_top_scorers_obeys_the_team_filter(self):
        self.write_log(
            (days_ago(1), "20:00:00", self.NICE),
            (days_ago(0), "20:00:00", self.ARSENAL),
        )
        catalogue = [("Nice",), ("Lens",), ("Arsenal",), ("Chelsea",)]
        with mock.patch.object(espn, "catalogue", return_value=catalogue):
            with mock.patch.object(time, "sleep"):
                _code, printed, _err = self.run_cli(
                    ["--top-scorers", "--teams", "nice"])
        self.assertIn("G. Laborde", printed)
        self.assertNotIn("M. Odegaard", printed)

    def test_a_goal_without_a_scorer_is_counted_but_not_attributed(self):
        self.write_log(
            (days_ago(0), "20:00:00", "BUT [Ligue 1] Nice 1 - 0 Lens pour Nice"),
            (days_ago(0), "20:10:00", self.NICE),
        )
        _code, printed, _err = self.run_cli(["--top-scorers"])
        self.assertIn("1 buteur(s) pour 2 but(s) confirme(s)", printed)
        self.assertIn("1 but(s) sans buteur connu", printed)

    def test_the_new_commands_are_reachable_from_main(self):
        help_text = cli.build_parser().format_help()
        for option in ("--week", "--month", "--since", "--top-scorers"):
            self.assertIn(option, help_text)


class OneShot:
    """Un watcher qui rend un but au premier passage, puis plus rien."""

    def __init__(self, matches, events, stopping):
        self.matches = matches
        self.events = events
        self.stopping = stopping
        self.passes = 0

    def tick(self):
        self.passes += 1
        if self.passes > 1:
            self.stopping.set()
            return []
        return self.events

    def all_matches(self):
        return self.matches

    def next_delay(self):
        return 0.0

    def plan_wait(self):
        # Les boucles de surveillance annoncent leur attente au watcher, qui
        # s'en sert pour reperer les trous (veille, processus gele). La
        # doublure doit donc porter la meme methode que le vrai.
        self.planned = True
        return self.next_delay()


class FakeStack:
    """Une pile de cartes sans tkinter : elle retient ce qu'on lui pousse."""

    def __init__(self, state_path, guard=None):
        self.state_path = state_path
        # Le watcher, pour savoir quand son passage est fini. Voir run().
        self.guard = guard
        self.cards = []
        # La carte epinglee est tenue a part, comme dans la vraie pile : elle
        # ne s'empile pas, elle se remplace.
        self.pinned = []
        self.unpinned = 0
        self.drain = None
        self.stopping = None

    def every(self, _ms, callback):
        self.drain = callback

    def run(self):
        """Attend la fin du passage du fil, puis vide la file une fois.

        Surtout pas "attendre le premier etat publie" : la boucle ecrit
        l'etat AVANT de deposer ses evenements dans la file, et vider entre
        les deux rendait zero carte une fois sur cent - un echec sur une
        seule machine de la CI, jamais en local. La boucle annonce son
        attente (plan_wait) une fois tout depose : c'est ce moment-la qu'on
        guette.
        """
        deadline = time.time() + 10
        while time.time() < deadline and not (
                getattr(self.guard, "planned", False)
                if self.guard is not None else self.state_path.exists()):
            time.sleep(0.01)
        self.stopping.set()
        self.drain()

    def push(self, card, duration=None):
        self.cards.append(card)

    def pin(self, card):
        self.pinned.append(card)

    def unpin(self):
        self.unpinned += 1

    def stop(self):
        pass


class TestBothWatchLoopsFeedTheState(unittest.TestCase):
    """Les deux chemins de surveillance publient le meme etat.

    Ecrit parce que le chemin avec cartes est le seul qu'on utilise vraiment :
    l'oublier reviendrait a n'avoir un --status utile qu'en --no-overlay.
    """

    def setUp(self):
        self.tmp = TemporaryDirectory()
        patcher = mock.patch.object(cli, "data_dir",
                                    return_value=Path(self.tmp.name))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)
        self.paths = cli.paths()
        self.paths["data"].mkdir(parents=True, exist_ok=True)
        self.args = cli.build_parser().parse_args(["--quiet", "--no-sound"])

    def guard_with_one_goal(self, stopping):
        matches = espn.parse(payload(event(state="in", home_score=1)),
                             leagues.BY_SLUG["fra.1"])
        goal = watcher.Event(kind=watcher.GOAL, match=matches[0], side="home",
                             team=matches[0].home, opponent=matches[0].away,
                             home_score=1, away_score=0, delta=1, play=None)
        return OneShot(matches, [goal], stopping)

    def reporter(self):
        return state.Reporter(self.paths["state"],
                              leagues=[leagues.BY_SLUG["fra.1"]],
                              interval=25, idle_interval=300)

    def test_headless_loop_publishes_the_state(self):
        stopping = threading.Event()
        guard = self.guard_with_one_goal(stopping)
        cli._watch_headless(guard, self.args, stopping, self.reporter(),
                            pinned.Pin(""))

        data = state.read(self.paths["state"])
        self.assertEqual(data["goals_today"], 1)
        self.assertEqual(data["matches"][0]["home"], "Angers")

    def test_card_loop_publishes_the_state_too(self):
        stopping = threading.Event()
        guard = self.guard_with_one_goal(stopping)
        stack = FakeStack(self.paths["state"], guard)
        stack.stopping = stopping
        cli._watch_with_cards(guard, self.args, stopping, stack,
                              self.reporter(), pinned.Pin(""))

        data = state.read(self.paths["state"])
        self.assertEqual(data["goals_today"], 1)
        self.assertEqual(data["matches"][0]["home"], "Angers")
        self.assertEqual(len(stack.cards), 1)

    def test_without_pin_nothing_is_pinned_anywhere(self):
        stopping = threading.Event()
        guard = self.guard_with_one_goal(stopping)
        stack = FakeStack(self.paths["state"], guard)
        stack.stopping = stopping
        cli._watch_with_cards(guard, self.args, stopping, stack,
                              self.reporter(), pinned.Pin(""))

        self.assertEqual(stack.pinned, [])
        self.assertEqual(stack.unpinned, 0)
        self.assertIsNone(state.read(self.paths["state"])["pinned"])

    def test_the_card_loop_pins_the_followed_match(self):
        stopping = threading.Event()
        guard = self.guard_with_one_goal(stopping)
        stack = FakeStack(self.paths["state"], guard)
        stack.stopping = stopping
        cli._watch_with_cards(guard, self.args, stopping, stack,
                              self.reporter(), pinned.Pin("angers"))

        self.assertEqual(len(stack.pinned), 1)
        card = stack.pinned[0]
        self.assertEqual((card.home, card.away), ("Angers", "Stade Rennais"))
        self.assertEqual((card.home_score, card.away_score), (1, 0))
        # Et l'etat le publie, pour --status.
        row = state.read(self.paths["state"])["pinned"]
        self.assertEqual(row["home"], "Angers")

    def test_the_headless_loop_still_publishes_the_pinned_match(self):
        """Sans ecran, la ligne "epinglee" de --status ne doit pas mentir."""
        stopping = threading.Event()
        guard = self.guard_with_one_goal(stopping)
        cli._watch_headless(guard, self.args, stopping, self.reporter(),
                            pinned.Pin("angers"))

        row = state.read(self.paths["state"])["pinned"]
        self.assertEqual(row["home"], "Angers")
        self.assertEqual(row["home_score"], 1)

    def catch_up_event(self, stopping):
        """Le resume de sortie de veille, tel que le watcher le rendrait."""
        matches = espn.parse(payload(event(state="in", home_score=2)),
                             leagues.BY_SLUG["fra.1"])
        summary = watcher.Event(
            kind=watcher.CATCHUP, match=matches[0], side=None, team="",
            opponent="", home_score=2, away_score=0, delta=0, play=None,
            changes=[watcher.Change(matches[0], 0, 0, matches[0].plays)],
            gap=40 * 60.0)
        return OneShot(matches, [summary], stopping)

    def test_the_catch_up_card_is_shown_without_a_sound(self):
        # Le point de l'option : une carte au reveil, et surtout pas la corne
        # pour un but vieux d'une heure.
        stopping = threading.Event()
        guard = self.catch_up_event(stopping)
        stack = FakeStack(self.paths["state"], guard)
        stack.stopping = stopping
        with mock.patch.object(cli, "play_goal_sound") as horn:
            cli._watch_with_cards(guard, self.args, stopping, stack,
                                  self.reporter(), pinned.Pin(""))

        self.assertEqual(len(stack.cards), 1)
        # La duree du trou plutot qu'une minute de jeu : c'est bien le resume.
        # Elle s'ecrit pareil dans les cinq langues, le test tient donc sur une
        # machine anglaise comme celles de la CI.
        self.assertEqual(stack.cards[0].minute, "40 min")
        horn.assert_not_called()


class TestPinOption(unittest.TestCase):
    """--pin : une equipe, une carte, et un mot verifie comme --teams."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        patcher = mock.patch.object(cli, "data_dir",
                                    return_value=Path(self.tmp.name))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)
        self.paths = cli.paths()
        self.paths["data"].mkdir(parents=True, exist_ok=True)

    def test_it_is_opt_in(self):
        parser = cli.build_parser()
        self.assertIsNone(parser.parse_args([]).pin)
        self.assertEqual(parser.parse_args(["--pin", "om"]).pin, "om")

    def test_a_list_of_teams_is_refused(self):
        # Il n'y a jamais qu'une carte epinglee : accepter la liste
        # reviendrait a n'en suivre silencieusement qu'une seule.
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            self.assertEqual(cli.main(["--pin", "om,psg"]), 2)

    def test_a_word_that_names_nothing_is_refused_at_startup(self):
        with mock.patch.object(espn, "catalogue",
                               return_value=[("Marseille", "OM", "MAR")]):
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                self.assertEqual(cli.main(["--pin", "marseile", "--leagues", "l1"]), 2)

    def test_a_word_that_names_a_team_goes_through(self):
        with mock.patch.object(espn, "catalogue",
                               return_value=[("Marseille", "OM", "MAR")]), \
                mock.patch.object(cli, "do_daemon", return_value=0) as daemon:
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                self.assertEqual(cli.main(["--pin", " om ", "--leagues", "l1"]), 0)
        self.assertEqual(daemon.call_args[0][0].pin, "om")

    def test_the_demo_can_show_one(self):
        """Sans --test, personne ne pourrait regler cette carte-la."""
        with mock.patch.object(espn, "catalogue",
                               return_value=[("Marseille", "OM", "MAR")]):
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                code = cli.main(["--test", "--pin", "om", "--leagues", "l1",
                                 "--no-overlay", "--no-sound", "--duration", "0.1"])
        self.assertEqual(code, 0)
        self.assertIn("demo epinglee", buffer.getvalue())

    def state_with(self, **extra):
        payload_ = state.Reporter(self.paths["state"], interval=25,
                                  idle_interval=300, pin="om").snapshot()
        payload_.update(extra)
        state.write(self.paths["state"], payload_)

    def test_status_says_what_is_pinned(self):
        row = {"league": "Ligue 1", "home": "Marseille", "away": "Paris FC",
               "home_score": 1, "away_score": 0, "clock": "34'"}
        self.state_with(pinned=row)
        summary = cli.pin_summary("om")
        self.assertIn("om ->", summary)
        self.assertIn("[Ligue 1] Marseille 1 - 0 Paris FC", summary)
        self.assertIn("34'", summary)

    def test_status_says_when_nothing_is_pinned(self):
        self.state_with(pinned=None)
        self.assertEqual(cli.pin_summary("om"), "om (aucun match en cours)")

    def test_status_does_not_invent_a_match_from_a_stale_state(self):
        # Un etat perime decrirait un match fini depuis des heures.
        self.assertIn("etat inconnu", cli.pin_summary("om"))
        self.state_with(updated_at=0.0,
                        pinned={"league": "Ligue 1", "home": "Marseille"})
        self.assertIn("etat inconnu", cli.pin_summary("om"))

    def test_the_status_line_shows_up(self):
        self.state_with(pinned=None)
        matches = espn.parse(payload(event(state="in")), leagues.BY_SLUG["fra.1"])
        with mock.patch.object(espn, "scoreboard", return_value=matches), \
                mock.patch.object(espn, "catalogue",
                                  return_value=[("Marseille", "OM", "MAR")]):
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                cli.main(["--status", "--pin", "om", "--leagues", "l1"])
        self.assertIn("epinglee", buffer.getvalue())


class TestSpoilerFreeLoops(unittest.TestCase):
    """Un but en differe : une ligne de journal, et strictement rien d'autre.

    Les deux chemins de surveillance sont verifies, pour la meme raison que
    l'etat : oublier celui des cartes reviendrait a ne rien avoir corrige.
    """

    def setUp(self):
        self.tmp = TemporaryDirectory()
        patcher = mock.patch.object(cli, "data_dir",
                                    return_value=Path(self.tmp.name))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)
        self.paths = cli.paths()
        self.paths["data"].mkdir(parents=True, exist_ok=True)
        self.args = cli.build_parser().parse_args(["--quiet"])

    def guard_with_one_goal(self, stopping, spoiler_free):
        matches = espn.parse(payload(event(state="in", home_score=1)),
                             leagues.BY_SLUG["fra.1"])
        goal = watcher.Event(kind=watcher.GOAL, match=matches[0], side="home",
                             team=matches[0].home, opponent=matches[0].away,
                             home_score=1, away_score=0, delta=1, play=None,
                             spoiler_free=spoiler_free)
        return OneShot(matches, [goal], stopping)

    def reporter(self):
        return state.Reporter(self.paths["state"],
                              leagues=[leagues.BY_SLUG["fra.1"]],
                              interval=25, idle_interval=300)

    def run_headless(self, spoiler_free):
        stopping = threading.Event()
        guard = self.guard_with_one_goal(stopping, spoiler_free)
        with mock.patch.object(cli, "play_goal_sound") as horn:
            with mock.patch.object(cli, "log") as journal:
                cli._watch_headless(guard, self.args, stopping,
                                    self.reporter(), pinned.Pin(""))
        return horn, journal

    def run_with_cards(self, spoiler_free):
        stopping = threading.Event()
        guard = self.guard_with_one_goal(stopping, spoiler_free)
        stack = FakeStack(self.paths["state"], guard)
        stack.stopping = stopping
        with mock.patch.object(cli, "play_goal_sound") as horn:
            with mock.patch.object(cli, "log") as journal:
                cli._watch_with_cards(guard, self.args, stopping, stack,
                                      self.reporter(), pinned.Pin(""))
        return stack, horn, journal

    def test_the_hook_does_not_fire_on_a_match_watched_late(self):
        """Le crochet est une alerte de plus : --spoiler-free les coupe toutes.

        Sans ca, une guirlande ou un webhook raconterait le but que l'ecran et
        le haut-parleur viennent justement de taire.
        """
        stopping = threading.Event()
        guard = self.guard_with_one_goal(stopping, True)
        fired = []
        runner = hook.Runner("peu importe",
                             spawn=lambda *a: fired.append(a) or (0, ""))
        cli._watch_headless(guard, self.args, stopping, self.reporter(),
                            pinned.Pin(""), on_goal=runner)
        self.assertEqual(fired, [])

    def test_the_hook_still_fires_on_an_ordinary_goal(self):
        stopping = threading.Event()
        guard = self.guard_with_one_goal(stopping, False)
        fired = []
        runner = hook.Runner("peu importe",
                             spawn=lambda *a: fired.append(a) or (0, ""))
        thread = None
        original = runner.fire

        def watched(event):
            nonlocal thread
            thread = original(event)
            return thread

        runner.fire = watched
        cli._watch_headless(guard, self.args, stopping, self.reporter(),
                            pinned.Pin(""), on_goal=runner)
        if thread is not None:
            thread.join(5.0)
        self.assertEqual(len(fired), 1)

    def test_headless_loop_stays_silent(self):
        horn, journal = self.run_headless(True)
        horn.assert_not_called()
        self.assertIn("BUT", " ".join(str(c) for c in journal.call_args_list))

    def test_headless_loop_still_sounds_an_ordinary_goal(self):
        horn, _journal = self.run_headless(False)
        self.assertTrue(horn.called)

    def test_card_loop_shows_and_sounds_nothing(self):
        stack, horn, journal = self.run_with_cards(True)
        self.assertEqual(stack.cards, [])
        horn.assert_not_called()
        self.assertIn("BUT", " ".join(str(c) for c in journal.call_args_list))

    def test_card_loop_still_shows_an_ordinary_goal(self):
        stack, horn, _journal = self.run_with_cards(False)
        self.assertEqual(len(stack.cards), 1)
        self.assertTrue(horn.called)

    def test_the_state_is_published_either_way(self):
        # Le daemon continue de suivre le match : --status doit le voir.
        self.run_with_cards(True)
        data = state.read(self.paths["state"])
        self.assertEqual(data["matches"][0]["home"], "Angers")


class TestSpoilerFreeCommands(unittest.TestCase):
    """--scores, --status et la verification des mots au demarrage."""

    CATALOGUE = [("Angers", "Angers", "SCO"),
                 ("Stade Rennais", "Rennes", "REN")]

    def setUp(self):
        self.tmp = TemporaryDirectory()
        patcher = mock.patch.object(cli, "data_dir",
                                    return_value=Path(self.tmp.name))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)
        self.paths = cli.paths()

    def run_cli(self, argv):
        matches = espn.parse(
            payload(event(state="in", home_score=1,
                          details=[goal_detail("H1", "35'", "C. Arcus")])),
            leagues.BY_SLUG["fra.1"])
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(espn, "scoreboard", return_value=matches):
            with mock.patch.object(espn, "catalogue", return_value=self.CATALOGUE):
                with redirect_stdout(out), redirect_stderr(err):
                    code = cli.main(argv + ["--leagues", "l1"])
        return code, out.getvalue(), err.getvalue()

    # ------------------------------------------------------------ scores ---

    def test_scores_masks_the_score_but_keeps_the_match(self):
        code, printed, _err = self.run_cli(["--scores", "--spoiler-free", "angers"])
        self.assertEqual(code, 0)
        self.assertIn("Angers", printed)
        self.assertIn("Stade Rennais", printed)
        self.assertIn("? - ?", printed)
        self.assertIn("sans spoiler", printed)

    def test_scores_hides_what_would_rebuild_the_score(self):
        _code, printed, _err = self.run_cli(["--scores", "--spoiler-free", "angers"])
        self.assertNotIn("C. Arcus", printed)
        self.assertNotIn("1 - 0", printed)

    def test_scores_without_the_option_says_everything(self):
        _code, printed, _err = self.run_cli(["--scores"])
        self.assertIn("1 - 0", printed)
        self.assertIn("C. Arcus", printed)
        self.assertNotIn("sans spoiler", printed)

    def test_scores_only_masks_the_match_concerned(self):
        # L'autre match du jour garde son score : on ne coupe pas tout.
        matches = espn.parse(payload(event(state="in", home_score=1),
                                     event(match_id="2", home="Lens",
                                           away="Lille", home_score=2,
                                           state="in")),
                             leagues.BY_SLUG["fra.1"])
        buffer = io.StringIO()
        with mock.patch.object(espn, "scoreboard", return_value=matches):
            with mock.patch.object(espn, "catalogue", return_value=self.CATALOGUE):
                with redirect_stdout(buffer):
                    cli.main(["--scores", "--leagues", "l1",
                              "--spoiler-free", "angers"])
        printed = buffer.getvalue()
        self.assertIn("? - ?", printed)
        self.assertIn("2 - 0", printed)

    # ------------------------------------------------------------ status ---

    def write_state(self, home="Angers", away="Stade Rennais"):
        data = {
            "version": 1, "pid": os.getpid(), "updated_at": time.time(),
            "updated_text": "2026-09-06 18:52:44", "day": state.today(),
            "goals_today": 1, "interval": 25, "idle_interval": 300,
            "leagues": ["Ligue 1"], "total_matches": 1,
            "matches": [{"league": "Ligue 1", "home": home, "away": away,
                         "home_score": 1, "away_score": 0, "clock": "35'"}],
        }
        self.paths["state"].parent.mkdir(parents=True, exist_ok=True)
        self.paths["state"].write_text(json.dumps(data), encoding="utf-8")
        self.paths["pid"].write_text(str(os.getpid()))

    def test_status_announces_the_setting(self):
        code, printed, _err = self.run_cli(
            ["--status", "--spoiler-free", "angers,rennes"])
        self.assertEqual(code, 0)
        self.assertIn("sans spoiler: angers, rennes", printed)

    def test_status_says_nothing_without_the_option(self):
        _code, printed, _err = self.run_cli(["--status"])
        self.assertNotIn("sans spoiler", printed)

    def test_status_masks_the_score_of_a_match_in_progress(self):
        # Une ligne "en cours" en dit autant qu'une carte.
        self.write_state()
        _code, printed, _err = self.run_cli(["--status", "--spoiler-free", "angers"])
        self.assertIn("Angers ? - ? Stade Rennais", printed)
        self.assertNotIn("Angers 1 - 0", printed)

    def test_status_leaves_the_other_matches_alone(self):
        self.write_state(home="Lens", away="Lille")
        _code, printed, _err = self.run_cli(["--status", "--spoiler-free", "angers"])
        self.assertIn("Lens 1 - 0 Lille", printed)

    # ------------------------------------------------------ verification ---

    def test_a_word_that_designates_nothing_is_refused_at_startup(self):
        # Comme --teams : une faute de frappe ici laisserait spoiler le match
        # qu'on voulait justement proteger.
        code, _printed, err = self.run_cli(["--status", "--spoiler-free", "marseile"])
        self.assertEqual(code, 2)
        self.assertIn("marseile", err)

    def test_a_known_word_passes(self):
        code, _printed, _err = self.run_cli(["--status", "--spoiler-free", "angers"])
        self.assertEqual(code, 0)

    def test_a_word_shared_by_two_lists_is_only_reported_once(self):
        _code, _printed, err = self.run_cli(
            ["--status", "--teams", "marseile", "--spoiler-free", "marseile"])
        self.assertEqual(err.count("marseile"), 1)


class TestContextualSound(unittest.TestCase):
    """Le pont entre un but et le nom des fichiers du dossier `sound`."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        patcher = mock.patch.object(cli, "data_dir",
                                    return_value=Path(self.tmp.name))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)
        self.folder = cli.paths()["sound"]
        self.folder.mkdir(parents=True)

    def drop(self, *names):
        for name in names:
            (self.folder / name).write_bytes(b"x")

    def args(self, *extra):
        # --duration fige la duree : sans lui, chaque appel irait mesurer un
        # faux mp3 de trois octets.
        return cli.build_parser().parse_args(
            ["--quiet", "--duration", "1"] + list(extra))

    def goal(self, side="home", kind=watcher.GOAL):
        matches = espn.parse(
            payload(event(home="Marseille",
                          away=("Paris Saint-Germain", "Paris SG", "PSG"),
                          state="in", home_score=1)),
            leagues.BY_SLUG["fra.1"])
        match = matches[0]
        home = side == "home"
        return watcher.Event(kind=kind, match=match, side=side,
                             team=match.home if home else match.away,
                             opponent=match.away if home else match.home,
                             home_score=1, away_score=0, delta=1, play=None)

    def chosen(self, args, event_=None):
        path, _duration = cli.resolve_sound(args, event_)
        return path.name

    def test_a_team_file_plays_only_when_that_team_scores(self):
        self.drop("om.mp3", "corne.mp3")
        args = self.args()
        self.assertEqual(self.chosen(args, self.goal("home")), "om.mp3")
        self.assertEqual(self.chosen(args, self.goal("away")), "corne.mp3")

    def test_a_followed_team_conceding_gets_the_conceded_file(self):
        self.drop("contre.mp3", "corne.mp3")
        args = self.args("--teams", "om")
        # Le PSG marque : l'OM, qu'on suit, vient de prendre un but.
        self.assertEqual(self.chosen(args, self.goal("away")), "contre.mp3")
        self.assertEqual(self.chosen(args, self.goal("home")), "corne.mp3")

    def test_without_teams_nobody_concedes_at_home(self):
        self.drop("contre.mp3", "corne.mp3")
        self.assertEqual(self.chosen(self.args(), self.goal("away")),
                         "corne.mp3")

    def test_the_league_file_takes_over_when_no_team_is_named(self):
        self.drop("l1.mp3", "corne.mp3")
        self.assertEqual(self.chosen(self.args(), self.goal("home")), "l1.mp3")

    def test_no_event_keeps_the_old_draw(self):
        # --test, et les cartes muettes : tout le dossier reste candidat.
        self.drop("om.mp3")
        self.assertEqual(self.chosen(self.args()), "om.mp3")

    def test_a_silent_card_has_no_context(self):
        args = self.args()
        self.assertIsNone(cli.sound_context(args, None))
        self.assertIsNone(cli.sound_context(args, self.goal(kind=watcher.KICKOFF)))

    def test_the_context_knows_who_scored_and_who_took_it(self):
        context = cli.sound_context(self.args("--teams", "om"),
                                    self.goal("away"))
        self.assertTrue(context.names_scorer("psg"))
        self.assertTrue(context.names_beaten("om"))
        self.assertTrue(context.conceded)
        self.assertTrue(context.names_league("l1"))

    def test_status_says_what_each_file_arms(self):
        self.drop("contre.mp3", "l1.mp3", "om.mp3", "corne.mp3")
        rows = dict(cli._sound_arming(sound.custom_sounds(self.folder),
                                      self.args("--teams", "om"),
                                      [leagues.BY_SLUG["fra.1"]]))
        self.assertIn("encaisse", rows["contre.mp3"])
        self.assertIn("Ligue 1", rows["l1.mp3"])
        self.assertIn("marque", rows["om.mp3"])
        self.assertIn("general", rows["corne.mp3"])

    def test_status_warns_that_conceded_needs_a_followed_team(self):
        self.drop("contre.mp3")
        rows = dict(cli._sound_arming(sound.custom_sounds(self.folder),
                                      self.args(), [leagues.BY_SLUG["fra.1"]]))
        self.assertIn("--teams", rows["contre.mp3"])

    def test_status_flags_a_sound_for_a_league_nobody_watches(self):
        self.drop("pl.mp3")
        rows = dict(cli._sound_arming(sound.custom_sounds(self.folder),
                                      self.args(), [leagues.BY_SLUG["fra.1"]]))
        self.assertIn("non suivie", rows["pl.mp3"])


def fixtures(*rows, **kwargs):
    """Des matchs a venir, tels que la source les decrit.

    `rows` : des (identifiant, domicile, exterieur, date ISO). L'etat est "pre"
    partout - un prochain match n'a par definition pas commence.
    """
    slug = kwargs.pop("slug", "fra.1")
    events = [event(match_id=str(match_id), home=home, away=away, state="pre",
                    detail="a venir", clock="", date=when)
              for match_id, home, away, when in rows]
    return espn.parse(payload(*events), leagues.BY_SLUG[slug])


def run_next(argv, answers, pause=0.0):
    """Lance --next sur des reponses fabriquees, et rend (code, sortie).

    `answers` : slug -> liste de matchs, ou une exception a lever pour ce
    slug-la. La pause entre deux competitions est neutralisee par defaut :
    c'est la cadence qui est testee ailleurs, pas ici.
    """
    def scoreboard(league, **_kwargs):
        answer = answers[league.slug]
        if isinstance(answer, Exception):
            raise answer
        return answer

    buffer = io.StringIO()
    with mock.patch.object(cli, "NEXT_PAUSE", pause):
        with mock.patch.object(espn, "scoreboard", side_effect=scoreboard):
            with redirect_stdout(buffer):
                code = cli.main(argv)
    return code, buffer.getvalue()


class TestNextRequest(unittest.TestCase):
    """Ce que --next accepte : rien, une equipe, un nombre de jours."""

    def test_nothing_asks_for_the_default_window(self):
        self.assertEqual(cli._next_request(""), (cli.DEFAULT_NEXT_DAYS, ""))

    def test_a_word_is_a_team(self):
        self.assertEqual(cli._next_request("om"), (cli.DEFAULT_NEXT_DAYS, "om"))

    def test_a_number_is_a_window(self):
        self.assertEqual(cli._next_request("3"), (3, ""))

    def test_both_can_be_said_at_once(self):
        self.assertEqual(cli._next_request("om,psg,3"), (3, "om,psg"))

    def test_the_window_is_bounded(self):
        self.assertEqual(cli._next_request("0"), (1, ""))
        self.assertEqual(cli._next_request("999"), (cli.MAX_NEXT_DAYS, ""))


class TestNextWindow(unittest.TestCase):
    """La fenetre de jours, et ce qui n'est pas un prochain match."""

    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.today = datetime.now().date()

    def keep(self, matches, days):
        return cli.next_matches(matches, self.now, days, today=self.today)

    def test_a_match_beyond_the_window_is_left_out(self):
        matches = fixtures(("1", "Angers", "Rennes", at_local_hour(3, 21)))
        self.assertEqual(len(self.keep(matches, 7)), 1)
        # Le dernier jour de --next 1, c'est aujourd'hui : dans trois jours,
        # c'est dehors.
        self.assertEqual(self.keep(matches, 1), [])

    def test_the_window_counts_whole_local_days(self):
        # A la fin du 7e jour, tard : dedans quand meme. Une fenetre qui se
        # fermerait "dans 7 fois 24 h" couperait la soiree en deux.
        matches = fixtures(("1", "Angers", "Rennes", at_local_hour(6, 23, 45)))
        self.assertEqual(len(self.keep(matches, 7)), 1)
        self.assertEqual(self.keep(matches, 6), [])

    def test_a_match_already_under_way_is_not_a_next_match(self):
        live = espn.parse(payload(event(state="in", date=in_minutes(-30))),
                          leagues.BY_SLUG["fra.1"])
        self.assertEqual(self.keep(live, 7), [])

    def test_a_kickoff_already_passed_is_not_announced(self):
        # L'heure est passee mais rien n'a demarre (retard, report) : ce n'est
        # pas une reponse a "c'est quand, le prochain ?".
        late = fixtures(("1", "Angers", "Rennes", in_minutes(-30)))
        self.assertEqual(self.keep(late, 7), [])

    def test_a_match_without_a_date_is_left_out(self):
        undated = fixtures(("1", "Angers", "Rennes", ""))
        self.assertEqual(self.keep(undated, 7), [])

    def test_matches_come_out_in_kickoff_order(self):
        matches = fixtures(("1", "Angers", "Rennes", at_local_hour(2, 21)),
                           ("2", "Lyon", "Nice", at_local_hour(1, 17)))
        kept = self.keep(matches, 7)
        self.assertEqual([match.home for match in kept], ["Lyon", "Angers"])


class TestNextGrouping(unittest.TestCase):
    """Le regroupement par jour puis par competition."""

    def test_one_group_per_day_in_chronological_order(self):
        matches = cli.next_matches(
            fixtures(("1", "Angers", "Rennes", at_local_hour(1, 21)),
                     ("2", "Lyon", "Nice", at_local_hour(3, 17))),
            datetime.now(timezone.utc), 7)
        grouped = cli.group_by_day(matches)
        self.assertEqual(len(grouped), 2)
        self.assertLess(grouped[0][0], grouped[1][0])

    def test_a_day_holds_one_row_per_competition(self):
        matches = cli.next_matches(
            fixtures(("1", "Angers", "Rennes", at_local_hour(1, 21)))
            + fixtures(("2", "Arsenal", "Chelsea", at_local_hour(1, 18)),
                       slug="eng.1"),
            datetime.now(timezone.utc), 7)
        grouped = cli.group_by_day(matches)
        self.assertEqual(len(grouped), 1)
        rows = grouped[0][1]
        # L'ordre des competitions suit le premier match de chacune.
        self.assertEqual([name for name, _ in rows],
                         ["Premier League", "Ligue 1"])
        self.assertEqual([len(group) for _, group in rows], [1, 1])


class TestNextFormatting(unittest.TestCase):
    """Les petits textes de l'affichage, pris un par un."""

    def test_the_day_title_names_today_and_tomorrow(self):
        today = date(2026, 9, 7)          # un lundi
        self.assertEqual(cli._day_title(today, today),
                         "lundi 07/09 (aujourd'hui)")
        self.assertEqual(cli._day_title(today + timedelta(days=1), today),
                         "mardi 08/09 (demain)")
        self.assertEqual(cli._day_title(today + timedelta(days=5), today),
                         "samedi 12/09")

    def test_the_countdown_changes_unit_with_the_distance(self):
        self.assertEqual(cli._delay_text(35 * 60), "dans 35 min")
        self.assertEqual(cli._delay_text(3 * 3600), "dans 3 h")
        self.assertEqual(cli._delay_text(5 * 86400), "dans 5 j")
        # Jamais "dans 0 min" : un match imminent reste a venir.
        self.assertEqual(cli._delay_text(20), "dans 1 min")


class TestNextCommand(unittest.TestCase):
    """--next de bout en bout, sans reseau."""

    def test_it_groups_by_day_then_by_competition(self):
        code, printed = run_next(
            ["--next", "--leagues", "l1,pl"],
            {"fra.1": fixtures(("1", "Angers", "Rennes", at_local_hour(1, 21))),
             "eng.1": fixtures(("2", "Arsenal", "Chelsea", at_local_hour(1, 18)),
                               slug="eng.1")})
        self.assertEqual(code, 0)
        self.assertIn("Ligue 1", printed)
        self.assertIn("Premier League", printed)
        self.assertIn("Angers", printed)
        self.assertIn("Chelsea", printed)
        # Heure locale, pas celle de la source.
        self.assertIn("21:00", printed)
        self.assertIn("18:00", printed)
        self.assertIn("2 match(s) a venir dans 2 competition(s), sur 7 jour(s).",
                      printed)
        # Un seul jour : un seul en-tete.
        self.assertEqual(printed.count("(demain)"), 1)

    def test_a_team_can_be_named_right_after_next(self):
        code, printed = run_next(
            ["--next", "om", "--leagues", "l1"],
            {"fra.1": fixtures(
                ("1", "Marseille", "Paris FC", at_local_hour(1, 21)),
                ("2", "Lyon", "Nice", at_local_hour(2, 17)))})
        self.assertEqual(code, 0)
        self.assertIn("Marseille", printed)
        self.assertNotIn("Lyon", printed)

    def test_a_number_right_after_next_is_the_window(self):
        answers = {"fra.1": fixtures(
            ("1", "Angers", "Rennes", at_local_hour(1, 21)),
            ("2", "Lyon", "Nice", at_local_hour(5, 17)))}

        code, printed = run_next(["--next", "2", "--leagues", "l1"], answers)
        self.assertEqual(code, 0)
        self.assertIn("Angers", printed)
        self.assertNotIn("Lyon", printed)
        self.assertIn("sur 2 jour(s)", printed)

        _, wider = run_next(["--next", "7", "--leagues", "l1"], answers)
        self.assertIn("Lyon", wider)

    def test_an_empty_calendar_is_a_sentence_not_a_table(self):
        code, printed = run_next(["--next", "om", "--leagues", "l1"],
                                 {"fra.1": []})
        self.assertEqual(code, 0)
        self.assertIn("Rien au programme dans les 7 prochains jours", printed)
        # Le mot cherche est repete : c'est la qu'une faute de frappe se voit.
        self.assertIn("om", printed)

    def test_one_unreachable_competition_does_not_stop_the_others(self):
        code, printed = run_next(
            ["--next", "--leagues", "l1,pl"],
            {"fra.1": fixtures(("1", "Angers", "Rennes", at_local_hour(1, 21))),
             "eng.1": espn.SourceError("HTTP 500")})
        self.assertEqual(code, 0)
        self.assertIn("Angers", printed)
        self.assertIn("Premier League injoignable : HTTP 500", printed)
        self.assertIn("incomplet", printed)

    def test_everything_unreachable_is_an_error(self):
        code, printed = run_next(["--next", "--leagues", "l1"],
                                 {"fra.1": espn.SourceError("pas de reseau")})
        self.assertEqual(code, 1)
        self.assertIn("Aucune competition n'a repondu", printed)

    def test_the_whole_window_is_asked_in_one_request_per_competition(self):
        seen = []

        def scoreboard(league, **kwargs):
            seen.append((league.slug, kwargs.get("dates")))
            return []

        with mock.patch.object(cli, "NEXT_PAUSE", 0.0):
            with mock.patch.object(espn, "scoreboard", side_effect=scoreboard):
                with redirect_stdout(io.StringIO()):
                    cli.main(["--next", "7", "--leagues", "l1,pl"])

        self.assertEqual([slug for slug, _ in seen], ["fra.1", "eng.1"])
        for _, dates in seen:
            self.assertRegex(dates, r"^\d{8}-\d{8}$")
        # La fenetre est elargie d'un jour de chaque cote : `dates` compte les
        # jours dans le fuseau de la source, pas dans le notre.
        first, last = seen[0][1].split("-")
        today = datetime.now().date()
        self.assertEqual(first, espn.day_code(today - timedelta(days=1)))
        self.assertEqual(last, espn.day_code(today + timedelta(days=7)))

    def test_the_requests_are_spaced_out(self):
        # Avec --leagues all ce sont 36 requetes : une rafale se ferait jeter.
        with mock.patch.object(cli.time, "sleep") as sleeping:
            with mock.patch.object(espn, "scoreboard", return_value=[]):
                with redirect_stdout(io.StringIO()):
                    cli.main(["--next", "--leagues", "l1,pl,liga"])
        self.assertEqual(sleeping.call_count, 2)
        for call in sleeping.call_args_list:
            self.assertEqual(call[0][0], cli.NEXT_PAUSE)


if __name__ == "__main__":
    unittest.main()
