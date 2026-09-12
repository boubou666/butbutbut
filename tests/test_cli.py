import csv
import io
import json
import os
import re
import subprocess
import sys
import threading
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from butbutbut import (cli, espn, hook, i18n, journal, leagues, pinned,
                       presenting, silence, sound, speech, state, teams,
                       watcher)

from helpers import (at_local_hour, event, goal_detail, in_minutes,
                     isolate_data_dir, payload)


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
        # build_parser() seul ne lit rien, mais les tests de cette classe
        # passent par main(), qui verse le fichier de configuration dans les
        # defauts avant d'analyser argv.
        isolate_data_dir(self)
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
        # Le silence ne s'invite pas non plus : sans plage, rien ne se tait.
        self.assertIsNone(args.quiet_hours)
        self.assertFalse(args.quiet_while_presenting)

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


    def test_the_volume_runs_from_zero_to_a_hundred(self):
        self.assertEqual(self.parser.parse_args([]).volume, cli.DEFAULT_VOLUME)
        self.assertEqual(self.parser.parse_args(["--volume", "70"]).volume, 70)
        # L'ancienne echelle, celle des fichiers deja ecrits.
        self.assertEqual(self.parser.parse_args(["--volume", "0.55"]).volume, 55)

    def test_an_impossible_volume_is_refused_with_the_scale(self):
        with mock.patch("sys.stderr", new_callable=io.StringIO) as err:
            with self.assertRaises(SystemExit):
                self.parser.parse_args(["--volume", "200"])
        self.assertIn("100", err.getvalue())

    def test_a_volume_of_zero_is_the_silent_mode(self):
        # Sans ca, butbutbut irait choisir un son, en mesurerait la duree et le
        # tendrait a un lecteur pour qu'il ne le joue pas - et la carte
        # attendrait a l'ecran la fin d'un silence.
        with mock.patch.object(cli, "do_daemon", return_value=0) as daemon:
            cli.main(["--volume", "0", "--leagues", "l1"])
        self.assertTrue(daemon.call_args[0][0].no_sound)

    def test_a_volume_above_zero_leaves_the_sound_on(self):
        with mock.patch.object(cli, "do_daemon", return_value=0) as daemon:
            cli.main(["--volume", "1%", "--leagues", "l1"])
        self.assertFalse(daemon.call_args[0][0].no_sound)

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

    def test_an_unreadable_quiet_range_is_refused(self):
        """Devant son terminal, on veut savoir tout de suite qu'on s'est trompe."""
        err = io.StringIO()
        with redirect_stderr(err):
            self.assertEqual(cli.main(["--quiet-hours", "de 23h a 8h"]), 2)
        self.assertIn(silence.FORMAT, err.getvalue())

    def test_a_readable_quiet_range_is_rewritten_once_for_all(self):
        parser = cli.build_parser()
        self.assertEqual(parser.parse_args(["--quiet-hours", "23h-8h"]).quiet_hours,
                         "23h-8h")
        # main() normalise : le reste du programme ne voit qu'une seule forme.
        seen = {}

        def capture(args):
            seen["args"] = args
            return 0

        with mock.patch.object(cli, "do_paths", capture):
            with redirect_stdout(io.StringIO()):
                cli.main(["--quiet-hours", "23h-8h", "--paths"])
        self.assertEqual(seen["args"].quiet_hours, "23:00-08:00")

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

    def setUp(self):
        self.paths = isolate_data_dir(self)

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

    def test_the_wanted_size_travels_from_scale_to_the_cache(self):
        # overlay sait quel cote un ecusson occupera, crests sait quoi en
        # demander a ESPN : c'est crest_cache qui les met en rapport. Un
        # ecusson pris en 64 et montre a 160 pixels serait floue.
        url = "https://a.espncdn.com/i/teamlogos/soccer/500/170.png"
        small = cli.crest_cache(cli.build_parser().parse_args([]))
        big = cli.crest_cache(cli.build_parser().parse_args(["--scale", "4"]))
        self.assertEqual(small.size, 64)
        self.assertGreater(big.size, small.size)
        self.assertNotEqual(small.path_for(url), big.path_for(url))
        self.assertIn("&h=64&w=64", small.candidates(url)[0])

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
    """Le fichier pid, et la seule question qui compte : est-ce bien NOUS ?"""

    def setUp(self):
        self.paths = isolate_data_dir(self)

    def write(self, *lines):
        self.paths["pid"].parent.mkdir(parents=True, exist_ok=True)
        self.paths["pid"].write_text("\n".join(lines) + "\n")

    def test_dead_pid_is_not_considered_running(self):
        self.assertFalse(cli._process_alive(-1))
        self.assertFalse(cli._process_alive(0))

    def test_our_own_pid_is_alive(self):
        self.assertTrue(cli._process_alive(os.getpid()))

    @unittest.skipUnless(sys.platform == "win32",
                         "un objet processus ne survit au programme que la")
    def test_a_process_that_died_but_whose_handle_survives_is_dead(self):
        """Le vrai bug : un daemon tue net qui repond present pendant des heures.

        Windows garde l'objet processus tant qu'un handle reste ouvert
        quelque part - ici le notre, comme celui du lanceur d'un daemon tue par
        une fin de session. Le numero repond alors a OpenProcess sans que rien
        ne tourne, et butbutbut refusait de repartir sur "une instance tourne
        deja". On garde donc le handle expres pendant qu'on tue l'enfant.
        """
        import ctypes

        child = subprocess.Popen([sys.executable, "-c", "import time"
                                  "; time.sleep(60)"])
        SYNCHRONIZE = 0x00100000
        kept = ctypes.windll.kernel32.OpenProcess(SYNCHRONIZE, False, child.pid)
        self.addCleanup(ctypes.windll.kernel32.CloseHandle, kept)
        child.terminate()
        child.wait(timeout=10)
        self.assertFalse(cli._process_alive(child.pid))

    def test_a_living_process_answers_yes(self):
        child = subprocess.Popen([sys.executable, "-c", "import time"
                                  "; time.sleep(60)"])
        self.addCleanup(child.wait)
        self.addCleanup(child.terminate)
        self.assertTrue(cli._process_alive(child.pid))

    def test_the_stamp_of_a_process_does_not_move(self):
        """Deux lectures du meme processus donnent la meme empreinte."""
        stamp = cli._process_stamp(os.getpid())
        if not stamp:
            self.skipTest("ce systeme ne publie pas la date de creation")
        self.assertEqual(stamp, cli._process_stamp(os.getpid()))

    def test_a_process_that_is_gone_has_no_stamp(self):
        self.assertEqual(cli._process_stamp(-1), "")

    def test_a_hair_of_drift_is_still_the_same_process(self):
        """Linux recalcule l'heure de demarrage a chaque lecture, a la seconde."""
        self.assertTrue(cli._same_stamp("1788938197.844", "1788938198.200"))
        self.assertFalse(cli._same_stamp("1788938197.844", "1788938497.844"))

    def test_a_stamp_that_is_not_a_number_is_compared_as_it_is(self):
        """macOS ne rend qu'un texte : `Tue Sep  9 09:16:37 2026`."""
        self.assertTrue(cli._same_stamp("Tue Sep  9 09:16:37 2026",
                                        "Tue Sep  9 09:16:37 2026"))
        self.assertFalse(cli._same_stamp("Tue Sep  9 09:16:37 2026",
                                         "Tue Sep  9 09:16:38 2026"))

    def test_claiming_writes_the_pid_and_its_stamp(self):
        self.assertTrue(cli.claim_pid_file())
        written = self.paths["pid"].read_text().splitlines()
        self.assertEqual(written[0], str(os.getpid()))
        self.assertEqual(written[1], cli._process_stamp(os.getpid()))

    def test_a_recycled_pid_is_not_our_daemon(self):
        """Le cas reel : le daemon est mort, un inconnu porte son numero.

        Notre propre pid, donc bien vivant, avec l'empreinte d'un autre. Sans
        cette comparaison butbutbut refuserait de demarrer - et `--stop`
        tuerait le processus qui a herite du numero.
        """
        if not cli._process_stamp(os.getpid()):
            self.skipTest("ce systeme ne publie pas la date de creation")
        self.write(str(os.getpid()), "une-autre-vie")
        self.assertIsNone(cli.running_pid())
        self.assertTrue(cli.claim_pid_file())

    def test_the_same_process_is_still_recognised(self):
        self.write(str(os.getpid()), cli._process_stamp(os.getpid()))
        self.assertEqual(cli.running_pid(), os.getpid())

    def test_a_file_without_a_stamp_keeps_the_benefit_of_the_doubt(self):
        """Celui qu'ecrivait la 1.13 : une ligne, et un daemon peut-etre vivant."""
        self.write(str(os.getpid()))
        self.assertEqual(cli.running_pid(), os.getpid())

    def test_a_pid_file_left_by_a_dead_daemon_stops_nothing(self):
        self.write("999999", "peu importe")
        self.assertIsNone(cli.running_pid())
        self.assertTrue(cli.claim_pid_file())

    def test_an_unreadable_pid_file_is_no_daemon(self):
        self.write("ce n'est pas un nombre")
        self.assertIsNone(cli.running_pid())


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
        self.paths = isolate_data_dir(self)

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
        self.paths = isolate_data_dir(self)

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
        for option in ("--week", "--month", "--since", "--top-scorers",
                       "--stats"):
            self.assertIn(option, help_text)


class TestStats(unittest.TestCase):
    """--stats : les formes du journal, sur des journaux fabriques."""

    def setUp(self):
        self.paths = isolate_data_dir(self)

    def write_log(self, *rows):
        lines = ["{} {}  {}".format(day, clock, text)
                 for day, clock, text in rows]
        self.paths["log"].parent.mkdir(parents=True, exist_ok=True)
        self.paths["log"].write_text("\n".join(lines) + "\n", encoding="utf-8")

    def run_cli(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(argv)
        return code, out.getvalue(), err.getvalue()

    @staticmethod
    def goal(minute, league="Ligue 1", home="Angers", away="Stade Rennais",
             scorer="C. Arcus", head="BUT"):
        return "{} [{}] {} 1 - 0 {} pour {} - But de {} ({}')".format(
            head, league, home, away, home, scorer, minute)

    # -------------------------------------------------------- histogramme --

    def test_the_histogram_shows_the_shape_of_a_match(self):
        self.write_log(
            (days_ago(1), "20:00:00", self.goal(88)),
            (days_ago(1), "20:05:00", self.goal(89, home="Nice", away="Lens")),
            (days_ago(1), "20:10:00", self.goal(12, home="Lille",
                                                away="Brest")),
        )
        code, printed, _err = self.run_cli(["--stats"])
        self.assertEqual(code, 0)
        self.assertIn("Par minute de match", printed)
        rows = {text.split()[0]: text for text in printed.splitlines()
                if text.startswith("  ") and "-" in text.split()[0]}
        self.assertIn("81-90", rows)
        self.assertIn("11-20", rows)
        # La bosse de fin de match est la plus haute barre.
        self.assertGreater(rows["81-90"].count("#"), rows["11-20"].count("#"))
        # Une tranche vide reste affichee : c'est une forme, elle aussi.
        self.assertIn("31-40", rows)
        self.assertEqual(rows["31-40"].count("#"), 0)

    def test_a_lonely_goal_still_gets_a_bar(self):
        """Arrondir a rien effacerait la minute qu'on vient justement lire."""
        self.write_log(
            (days_ago(1), "20:00:00", self.goal(5)),
            *[(days_ago(1), "20:{:02d}:00".format(index),
               self.goal(85, home="Nice", away="Lens"))
              for index in range(1, 30)])
        _code, printed, _err = self.run_cli(["--stats"])
        row = [text for text in printed.splitlines()
               if text.strip().startswith("1-10")][0]
        self.assertIn("#", row)

    def test_an_unreadable_minute_is_owned_up_to(self):
        self.write_log(
            (days_ago(1), "20:00:00", self.goal(50)),
            (days_ago(1), "20:05:00", "BUT [Ligue 1] Nice 1 - 0 Lens pour "
                                      "Nice - But de G. Laborde (Mi-temps)"),
        )
        _code, printed, _err = self.run_cli(["--stats"])
        self.assertIn("1 but(s) sans minute de jeu lisible", printed)

    def test_added_time_is_counted_and_said(self):
        self.write_log(
            (days_ago(1), "20:00:00", "BUT [Ligue 1] Angers 1 - 0 Stade "
                                      "Rennais pour Angers - But de C. Arcus "
                                      "(90+4')"),
        )
        _code, printed, _err = self.run_cli(["--stats"])
        self.assertIn("1 but(s) dans le temps additionnel", printed)
        row = [text for text in printed.splitlines()
               if text.strip().startswith("81-90")][0]
        self.assertIn("#", row)                 # un but a la 90e reste a la 90e

    # ------------------------------------------------ competitions, nature --

    def test_competitions_are_ranked(self):
        self.write_log(
            (days_ago(1), "20:00:00", self.goal(10)),
            (days_ago(1), "20:05:00", self.goal(20, home="Nice", away="Lens")),
            (days_ago(1), "20:10:00", self.goal(30, league="LaLiga",
                                                home="Girona",
                                                away="Real Madrid")),
        )
        _code, printed, _err = self.run_cli(["--stats"])
        lines = printed.splitlines()
        first = lines.index("Par competition")
        self.assertIn("Ligue 1", lines[first + 1])
        self.assertIn("LaLiga", lines[first + 2])

    def test_penalties_and_own_goals_are_told_apart(self):
        self.write_log(
            (days_ago(1), "20:00:00", self.goal(10)),
            (days_ago(1), "20:05:00", self.goal(20, head="BUT SUR PENALTY")),
            (days_ago(1), "20:10:00", self.goal(30,
                                                head="BUT CONTRE SON CAMP")),
        )
        _code, printed, _err = self.run_cli(["--stats"])
        self.assertIn("Nature des buts", printed)
        self.assertIn("Penalty", printed)
        self.assertIn("But contre son camp", printed)

    def test_one_nature_alone_does_not_deserve_a_table(self):
        self.write_log((days_ago(1), "20:00:00", self.goal(10)))
        _code, printed, _err = self.run_cli(["--stats"])
        self.assertNotIn("Nature des buts", printed)

    # -------------------------------------------------------------- soirees --

    def test_the_best_evening_comes_first(self):
        self.write_log(
            (days_ago(3), "20:00:00", self.goal(10)),
            (days_ago(2), "20:00:00", self.goal(10, home="Nice", away="Lens")),
            (days_ago(2), "20:05:00", self.goal(20, home="Nice", away="Lens")),
            (days_ago(2), "20:10:00", self.goal(30, home="Nice", away="Lens")),
        )
        _code, printed, _err = self.run_cli(["--stats"])
        lines = printed.splitlines()
        first = lines.index("Les soirees les plus prolifiques")
        self.assertIn("3 but(s)", lines[first + 1])
        self.assertIn("1 but(s)", lines[first + 2])

    def test_a_match_across_midnight_stays_one_evening(self):
        self.write_log(
            (days_ago(2), "23:50:00", self.goal(88)),
            (days_ago(1), "00:12:00", self.goal(90)),
        )
        _code, printed, _err = self.run_cli(["--stats"])
        lines = printed.splitlines()
        first = lines.index("Les soirees les plus prolifiques")
        self.assertIn("2 but(s)", lines[first + 1])
        # Une seule soiree, donc une seule ligne avant la suivante.
        self.assertFalse(lines[first + 2].strip())
        self.assertIn("1 match(s) avec au moins un but", printed)

    def test_evenings_tied_at_the_top_are_all_named(self):
        """Annoncer une seule meilleure soiree quand quatre se valent
        serait faux : on les nomme, puis on compte celles qui debordent."""
        self.write_log(*[
            (days_ago(index), "20:00:00", self.goal(10))
            for index in range(1, 5)])
        _code, printed, _err = self.run_cli(["--stats"])
        lines = printed.splitlines()
        first = lines.index("Les soirees les plus prolifiques")
        self.assertEqual(len([text for text in lines[first + 1:first + 4]
                              if "1 but(s)" in text]), 3)
        self.assertIn("... et 1 autre(s) soiree(s) a 1 but(s).", printed)

    # ------------------------------------------------- fenetres et filtres --

    def test_stats_takes_the_whole_journal_by_default(self):
        self.write_log(
            (days_ago(40), "20:00:00", self.goal(10, league="LaLiga",
                                                 home="Girona",
                                                 away="Real Madrid")),
            (days_ago(0), "20:00:00", self.goal(20)),
        )
        _code, whole, _err = self.run_cli(["--stats"])
        self.assertIn("depuis le debut du journal", whole)
        self.assertIn("LaLiga", whole)
        _code, week, _err = self.run_cli(["--stats", "--week"])
        self.assertNotIn("LaLiga", week)
        self.assertIn("Ligue 1", week)

    def test_stats_obeys_the_team_filter(self):
        self.write_log(
            (days_ago(1), "20:00:00", self.goal(10, home="Nice", away="Lens")),
            (days_ago(0), "20:00:00", self.goal(20, league="Premier League",
                                                home="Arsenal",
                                                away="Chelsea")),
        )
        catalogue = [("Nice",), ("Lens",), ("Arsenal",), ("Chelsea",)]
        with mock.patch.object(espn, "catalogue", return_value=catalogue):
            with mock.patch.object(time, "sleep"):
                _code, printed, _err = self.run_cli(
                    ["--stats", "--teams", "nice"])
        self.assertIn("Ligue 1", printed)
        self.assertNotIn("Premier League", printed)

    def test_an_unreadable_since_is_an_error_not_a_traceback(self):
        code, _printed, err = self.run_cli(["--stats", "--since", "hier"])
        self.assertEqual(code, 2)
        self.assertIn("date illisible", err)

    # ------------------------------------------------------- les cas vides --

    def test_a_missing_journal_says_so(self):
        code, printed, _err = self.run_cli(["--stats"])
        self.assertEqual(code, 0)
        self.assertIn("aucun but", printed)
        self.assertIn(str(self.paths["log"]), printed)

    def test_an_empty_journal_says_so(self):
        self.paths["log"].parent.mkdir(parents=True, exist_ok=True)
        self.paths["log"].write_text("", encoding="utf-8")
        code, printed, _err = self.run_cli(["--stats"])
        self.assertEqual(code, 0)
        self.assertIn("journal vide", printed)

    def test_a_window_without_a_single_goal_says_so(self):
        self.write_log((days_ago(40), "20:00:00", self.goal(10)))
        code, printed, _err = self.run_cli(["--stats", "--week"])
        self.assertEqual(code, 0)
        self.assertIn("aucun but sur cette periode", printed)
        self.assertNotIn("Par minute de match", printed)

    def test_a_window_where_the_var_took_everything_back_says_so(self):
        self.write_log(
            (days_ago(1), "20:00:00", self.goal(10)),
            (days_ago(1), "20:02:00", "BUT ANNULE [Ligue 1] Angers 0 - 0 "
                                      "Stade Rennais pour Angers - Score "
                                      "corrige (11')"),
        )
        code, printed, _err = self.run_cli(["--stats"])
        self.assertEqual(code, 0)
        self.assertIn("aucun but debout dans cette fenetre", printed)
        self.assertNotIn("Par minute de match", printed)

    def test_a_cancellation_without_its_goal_is_owned_up_to(self):
        self.write_log(
            (days_ago(1), "20:00:00", "BUT ANNULE [Ligue 1] Angers 0 - 0 "
                                      "Stade Rennais pour Angers - Score "
                                      "corrige (11')"),
            (days_ago(1), "20:30:00", self.goal(40, home="Nice", away="Lens")),
        )
        _code, printed, _err = self.run_cli(["--stats"])
        self.assertIn("1 annulation(s) sans but a retirer", printed)

    def test_every_line_fits_in_eighty_columns(self):
        """Un histogramme qui deborde du terminal ne se lit plus."""
        self.write_log(*[
            (days_ago(1), "20:{:02d}:00".format(index),
             self.goal(85, league="Championnat national de tres loin",
                       home="Bayer 04 Leverkusen", away="Bayern"))
            for index in range(0, 40)])
        _code, printed, _err = self.run_cli(["--stats"])
        # Le chemin du journal fait la longueur qu'il fait : c'est la seule
        # ligne dont on ne decide pas la largeur.
        long_lines = [text for text in printed.splitlines()
                      if len(text) > 80 and str(self.paths["log"]) not in text]
        self.assertEqual(long_lines, [])


class ConsoleStdout:
    """Une sortie standard comme en a un vrai terminal : du texte sur des octets.

    Une redirection en memoire (io.StringIO) ne suffit pas a tester l'export :
    elle n'a pas de flux d'octets, donc elle ne peut ni mal encoder un accent
    ni doubler un retour a la ligne - c'est-a-dire aucun des deux pieges que
    --export doit desamorcer. Celle-ci annonce du cp1252, l'encodage qu'une
    console Windows revendique par defaut et sur lequel un nom d'equipe
    accentue casserait si l'export ecrivait naivement du texte.
    """

    def __init__(self):
        self.buffer = io.BytesIO()
        self.encoding = "cp1252"

    def write(self, text):
        self.buffer.write(text.encode(self.encoding))
        return len(text)

    def flush(self):
        pass


class _ClosedPipe(io.BytesIO):
    """Un flux d'octets qui se referme apres les premiers octets."""

    def __init__(self, allowed=1):
        io.BytesIO.__init__(self)
        self.allowed = allowed

    def write(self, data):
        if self.allowed <= 0:
            raise OSError(32, "Broken pipe")
        self.allowed -= 1
        return io.BytesIO.write(self, data)


class BrokenPipeStdout(ConsoleStdout):
    """La meme sortie, dont le tuyau se referme au milieu : `--export | head`.

    Le piege de ce cas-la n'est pas l'erreur elle-meme mais ce qui arrive
    APRES : un flux mal referme imprime sa propre trace par-dessus le message
    qu'on venait d'ecrire proprement a cote, et emporte la sortie standard du
    programme avec lui.
    """

    def __init__(self, allowed=1):
        ConsoleStdout.__init__(self)
        self.buffer = _ClosedPipe(allowed)


class TestExport(unittest.TestCase):
    """--export json|csv : le journal en donnees, sur des journaux fabriques."""

    # Un accent, une virgule et un guillemet dans le meme journal : les trois
    # choses qui font mentir un export ecrit a la main. Ils sont ecrits en
    # echappement parce que les sources du depot sont en ASCII pur, mais le
    # journal, lui, les recoit en UTF-8 comme le vrai.
    NICE = "Nice, OGC"                      # une virgule dans un nom d'equipe
    LENS = 'Le "RC" Lens'                   # un guillemet dans un autre
    ALAVES = "Alav\u00e9s"                 # un accent, dans un troisieme

    def setUp(self):
        self.paths = isolate_data_dir(self)

    def write_log(self, *rows):
        lines = ["{} {}  {}".format(day, clock, text)
                 for day, clock, text in rows]
        self.paths["log"].parent.mkdir(parents=True, exist_ok=True)
        self.paths["log"].write_text("\n".join(lines) + "\n", encoding="utf-8")

    def run_cli(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(argv)
        return code, out.getvalue(), err.getvalue()

    @staticmethod
    def goal(league="Ligue 1", home="Angers", away="Stade Rennais",
             home_score=1, away_score=0, team=None, scorer="C. Arcus",
             minute="35'", head="BUT"):
        return "{} [{}] {} {} - {} {} pour {} - But de {} ({})".format(
            head, league, home, home_score, away_score, away,
            team or home, scorer, minute)

    def export(self, *argv):
        """Rend (donnees relues, prose de la sortie d'erreur)."""
        shape = argv[argv.index("--export") + 1]
        code, printed, errors = self.run_cli(list(argv))
        self.assertEqual(code, 0, errors)
        if shape == "json":
            return json.loads(printed), errors
        rows = list(csv.reader(io.StringIO(printed)))
        return rows, errors

    # ------------------------------------------------ ce que ca sait ecrire --

    def test_json_is_read_back_by_the_json_module(self):
        self.write_log(
            (days_ago(1), "20:00:00", self.goal()),
            (days_ago(0), "21:00:00", self.goal(league="LaLiga",
                                                home=self.ALAVES,
                                                away="Osasuna",
                                                scorer="M. Diaz")),
        )
        rows, _errors = self.export("--export", "json")
        self.assertEqual(len(rows), 2)
        self.assertEqual([row["scorer"] for row in rows],
                         ["C. Arcus", "M. Diaz"])
        self.assertEqual(rows[1]["league"], "LaLiga")
        self.assertEqual(rows[1]["home"], self.ALAVES)
        # Les cles sont exactement celles annoncees, dans le meme ordre : un
        # consommateur qui les lit une fois doit pouvoir s'y fier.
        for row in rows:
            self.assertEqual(list(row), list(cli.EXPORT_FIELDS))

    def test_csv_is_read_back_by_the_csv_module(self):
        self.write_log((days_ago(0), "20:00:00", self.goal()))
        rows, _errors = self.export("--export", "csv")
        self.assertEqual(rows[0], list(cli.EXPORT_FIELDS))
        self.assertEqual(len(rows), 2)
        # Une seule forme de ligne : autant de cases que d'en-tetes, toujours.
        for row in rows:
            self.assertEqual(len(row), len(cli.EXPORT_FIELDS))
        row = dict(zip(rows[0], rows[1]))
        self.assertEqual(row["home"], "Angers")
        self.assertEqual(row["home_score"], "1")
        self.assertEqual(row["scorer"], "C. Arcus")

    def test_a_comma_and_a_quote_in_a_name_survive_the_round_trip(self):
        """Un nom d'equipe n'a aucune raison de respecter la grammaire du CSV."""
        self.write_log((days_ago(0), "20:00:00",
                        self.goal(home=self.NICE, away=self.LENS)))
        rows, _errors = self.export("--export", "csv")
        row = dict(zip(rows[0], rows[1]))
        self.assertEqual(row["home"], self.NICE)
        self.assertEqual(row["away"], self.LENS)
        self.assertEqual(row["team"], self.NICE)
        rows, _errors = self.export("--export", "json")
        self.assertEqual(rows[0]["home"], self.NICE)
        self.assertEqual(rows[0]["away"], self.LENS)

    def test_an_accent_comes_out_in_utf8_whatever_the_console_says(self):
        """Le journal est en UTF-8 ; une console Windows annonce du cp1252."""
        self.write_log((days_ago(0), "20:00:00",
                        self.goal(home=self.ALAVES, away="Osasuna")))
        for shape in ("json", "csv"):
            console = ConsoleStdout()
            with mock.patch.object(sys, "stdout", console):
                with redirect_stderr(io.StringIO()):
                    code = cli.main(["--export", shape])
            self.assertEqual(code, 0, shape)
            written = console.buffer.getvalue()
            self.assertIn(self.ALAVES.encode("utf-8"), written, shape)
            # Et le flux reste ouvert : l'export ne ferme pas la sortie du
            # programme derriere lui.
            self.assertFalse(console.buffer.closed, shape)
            text = written.decode("utf-8")
            if shape == "json":
                self.assertEqual(json.loads(text)[0]["home"], self.ALAVES)
            else:
                # Aucune ligne doublee par le mode texte de Windows.
                self.assertNotIn("\r", text)
                back = list(csv.reader(io.StringIO(text)))
                self.assertEqual(len(back), 2, back)
                self.assertEqual(dict(zip(back[0], back[1]))["home"],
                                 self.ALAVES)

    # ----------------------------------------------------- dates et minutes --

    def test_dates_and_times_come_out_in_iso_8601(self):
        self.write_log((days_ago(0), "20:04:09", self.goal()))
        rows, _errors = self.export("--export", "json")
        self.assertEqual(rows[0]["timestamp"],
                         "{}T20:04:09".format(days_ago(0)))
        self.assertEqual(rows[0]["evening"], days_ago(0))

    def test_a_goal_after_midnight_belongs_to_the_evening_before(self):
        """La meme soiree que --stats, pas le jour du calendrier."""
        self.write_log((days_ago(0), "00:12:00", self.goal()))
        rows, _errors = self.export("--export", "json")
        self.assertEqual(rows[0]["evening"], days_ago(1))

    def test_the_minute_comes_out_as_a_number_and_keeps_what_was_written(self):
        self.write_log(
            (days_ago(0), "20:00:00", self.goal(minute="90+3'")),
            (days_ago(0), "20:10:00", self.goal(minute="Mi-temps",
                                                home="Nice", away="Lens")),
        )
        rows, _errors = self.export("--export", "json")
        self.assertEqual((rows[0]["minute"], rows[0]["stoppage"]), (90, 3))
        self.assertEqual(rows[0]["clock"], "90+3'")
        # Une minute que le journal n'ecrit pas comme une minute de jeu ne
        # devient pas un zero : elle devient un trou, et le texte reste.
        self.assertIsNone(rows[1]["minute"])
        self.assertIsNone(rows[1]["stoppage"])
        self.assertEqual(rows[1]["clock"], "Mi-temps")

    def test_an_unknown_number_is_an_empty_cell_in_csv(self):
        self.write_log((days_ago(0), "20:00:00", self.goal(minute="Mi-temps")))
        rows, _errors = self.export("--export", "csv")
        row = dict(zip(rows[0], rows[1]))
        self.assertEqual(row["minute"], "")
        self.assertEqual(row["stoppage"], "")

    # ------------------------------------------------------------- la VAR ---

    def test_a_goal_the_var_took_back_does_not_come_out_as_a_goal(self):
        self.write_log(
            (days_ago(0), "20:00:00", self.goal(scorer="M. Odegaard")),
            (days_ago(0), "20:02:00", self.goal(home_score=2,
                                                scorer="B. Saka")),
            (days_ago(0), "20:04:00", "BUT ANNULE [Ligue 1] Angers 1 - 0 "
                                      "Stade Rennais pour Angers - Score "
                                      "corrige (41')"),
        )
        rows, _errors = self.export("--export", "json")
        # Trois lignes de journal, trois lignes d'export : l'annulation a bien
        # eu lieu, la taire rendrait un journal que personne n'a vecu.
        self.assertEqual(len(rows), 3)
        self.assertEqual([row["kind"] for row in rows],
                         ["goal", "goal", "cancellation"])
        # Mais le but repris n'est plus debout, et l'annulation non plus.
        self.assertEqual([row["standing"] for row in rows],
                         [True, False, False])
        # Garder les lignes debout rend exactement ce que compte le classement.
        standing = [row for row in rows if row["standing"]]
        self.assertEqual([row["scorer"] for row in standing], ["M. Odegaard"])

    def test_the_standing_goals_are_the_ones_the_scoreboard_counts(self):
        """Un seul rattachement positionnel dans le programme, pas deux."""
        self.write_log(
            (days_ago(2), "20:00:00", self.goal(scorer="M. Odegaard")),
            (days_ago(2), "20:02:00", self.goal(home_score=2,
                                                scorer="B. Saka")),
            (days_ago(1), "20:04:00", "BUT ANNULE [Ligue 1] Angers 1 - 0 "
                                      "Stade Rennais pour Angers - Score "
                                      "corrige (41')"),
            (days_ago(0), "21:00:00", self.goal(league="LaLiga", home="Girona",
                                                away="Real Madrid",
                                                scorer="K. Mbappe")),
        )
        rows, _errors = self.export("--export", "json")
        standing = sum(1 for row in rows if row["standing"])
        entries = journal.goals_between(self.paths["log"])
        self.assertEqual(standing, journal.scoreboard(entries).confirmed)

    def test_a_cancellation_says_which_goal_kind_it_was(self):
        self.write_log(
            (days_ago(0), "20:00:00", self.goal(head="BUT SUR PENALTY")),
            (days_ago(0), "20:04:00", "BUT ANNULE [Ligue 1] Angers 0 - 0 "
                                      "Stade Rennais pour Angers - Score "
                                      "corrige (41')"),
        )
        rows, _errors = self.export("--export", "json")
        self.assertEqual([row["nature"] for row in rows],
                         ["penalty", "cancelled"])

    def test_an_orphan_cancellation_is_owned_up_to_on_the_error_output(self):
        self.write_log((days_ago(0), "20:04:00",
                        "BUT ANNULE [Ligue 1] Angers 0 - 0 Stade Rennais "
                        "pour Angers - Score corrige (41')"))
        _rows, errors = self.export("--export", "json")
        self.assertIn("1 annulation(s) sans but a retirer", errors)

    # ------------------------------------------- fenetres, filtres, reseau ---

    def test_the_window_is_the_one_of_stats_and_top_scorers(self):
        self.write_log(
            (days_ago(40), "20:00:00", self.goal(scorer="K. Mbappe")),
            (days_ago(0), "20:00:00", self.goal(scorer="C. Arcus")),
        )
        whole, errors = self.export("--export", "json")
        self.assertEqual(len(whole), 2)
        self.assertIn("depuis le debut du journal", errors)
        week, _errors = self.export("--export", "json", "--week")
        self.assertEqual([row["scorer"] for row in week], ["C. Arcus"])
        since, _errors = self.export("--export", "json", "--since",
                                     days_ago(50))
        self.assertEqual(len(since), 2)

    def test_the_team_filter_applies_and_stays_off_the_data(self):
        """--teams verifie les noms aupres de la source : c'est de la prose."""
        self.write_log(
            (days_ago(0), "20:00:00", self.goal(home="Nice", away="Lens")),
            (days_ago(0), "21:00:00", self.goal(home="Angers",
                                                away="Stade Rennais")),
        )
        catalogue = [("Nice",), ("Lens",), ("Angers",), ("Stade Rennais",)]
        with mock.patch.object(espn, "catalogue", return_value=catalogue):
            with mock.patch.object(time, "sleep"):
                code, printed, errors = self.run_cli(
                    ["--export", "json", "--teams", "nice"])
        self.assertEqual(code, 0)
        rows = json.loads(printed)          # rien d'autre n'est arrive la
        self.assertEqual([row["home"] for row in rows], ["Nice"])
        # La confirmation du mot d'equipe est partie a cote, avec le reste.
        self.assertIn("nice", errors)
        self.assertIn("Nice", errors)

    def test_excluding_a_team_leaves_it_out(self):
        self.write_log(
            (days_ago(0), "20:00:00", self.goal(home="Nice", away="Lens")),
            (days_ago(0), "21:00:00", self.goal(home="Angers",
                                                away="Stade Rennais")),
        )
        catalogue = [("Nice",), ("Lens",), ("Angers",), ("Stade Rennais",)]
        with mock.patch.object(espn, "catalogue", return_value=catalogue):
            with mock.patch.object(time, "sleep"):
                code, printed, _errors = self.run_cli(
                    ["--export", "json", "--exclude-teams", "nice"])
        self.assertEqual(code, 0)
        self.assertEqual([row["home"] for row in json.loads(printed)],
                         ["Angers"])

    def test_nothing_leaves_the_machine_without_a_team_word(self):
        """Sans --teams, l'export ne touche que le fichier. Comme --stats."""
        self.write_log((days_ago(0), "20:00:00", self.goal()))

        def refuse(*_args, **_kwargs):
            raise AssertionError("l'export a demande le reseau")

        with mock.patch.object(espn, "fetch", refuse):
            with mock.patch.object(espn, "catalogue", refuse):
                rows, _errors = self.export("--export", "json")
        self.assertEqual(len(rows), 1)

    def test_the_only_other_talker_moves_aside_too(self):
        """--regen-sound est la seule autre option qui ecrit sur stdout.

        Elle se declenche avant l'export dans main(), et sa ligne se serait
        collee aux donnees - derriere elles, meme, l'export ecrivant sous la
        couche texte de sys.stdout dont le tampon ne se vide qu'a la fin.
        """
        self.write_log((days_ago(0), "20:00:00", self.goal()))
        with mock.patch.object(sound, "ensure_wav", lambda *a, **k: None):
            code, printed, errors = self.run_cli(
                ["--export", "json", "--regen-sound"])
        self.assertEqual(code, 0)
        self.assertNotIn("corne regeneree", printed)
        self.assertIn("corne regeneree", errors)
        self.assertEqual(len(json.loads(printed)), 1)

    # ------------------------------------------------- rien, mais pas casse --

    def test_a_missing_journal_still_gives_valid_data(self):
        for shape, expected in (("json", "[]"), ("csv", None)):
            code, printed, errors = self.run_cli(["--export", shape])
            self.assertEqual(code, 0, shape)
            self.assertIn("journal vide", errors, shape)
            self.assertIn(str(self.paths["log"]), errors, shape)
            if expected is not None:
                self.assertEqual(json.loads(printed), [])
            else:
                # Un CSV reduit a son en-tete reste un CSV.
                self.assertEqual(list(csv.reader(io.StringIO(printed))),
                                 [list(cli.EXPORT_FIELDS)])

    def test_an_empty_journal_still_gives_valid_data(self):
        self.paths["log"].parent.mkdir(parents=True, exist_ok=True)
        self.paths["log"].write_text("", encoding="utf-8")
        rows, errors = self.export("--export", "json")
        self.assertEqual(rows, [])
        self.assertIn("journal vide", errors)

    def test_a_window_without_a_goal_still_gives_valid_data(self):
        self.write_log((days_ago(40), "20:00:00", self.goal()))
        rows, errors = self.export("--export", "csv", "--week")
        self.assertEqual(rows, [list(cli.EXPORT_FIELDS)])
        self.assertIn("aucun but sur cette periode", errors)

    def test_lines_the_parser_cannot_read_never_reach_the_data(self):
        self.write_log(
            (days_ago(0), "18:00:00", "demarrage (pid 3752) - les 5 champ"),
            (days_ago(0), "18:04:00", "Bundesliga injoignable (timeout)"),
            (days_ago(0), "18:06:00", "COUP D'ENVOI [Ligue 1] Nice 0 - 0 Lens"),
            (days_ago(0), "20:00:00", self.goal()),
        )
        rows, _errors = self.export("--export", "json")
        self.assertEqual(len(rows), 1)

    # ---------------------------------------------------- deux sorties ------

    def test_the_standard_output_carries_data_and_nothing_else(self):
        """C'est toute la promesse : `--export csv > buts.csv` rend un CSV."""
        self.write_log(
            (days_ago(0), "20:00:00", self.goal()),
            (days_ago(0), "20:04:00", "BUT ANNULE [Ligue 1] Angers 0 - 0 "
                                      "Stade Rennais pour Angers - Score "
                                      "corrige (41')"),
        )
        for shape in ("json", "csv"):
            code, printed, errors = self.run_cli(["--export", shape])
            self.assertEqual(code, 0, shape)
            self.assertNotIn("butbutbut :", printed, shape)
            self.assertNotIn(str(self.paths["log"]), printed, shape)
            # Et la prose est bien quelque part : ailleurs, pas nulle part.
            self.assertIn("butbutbut : export {}".format(shape), errors)
            self.assertIn("2 ligne(s)", errors)
            self.assertIn("Journal :", errors)

    def test_a_date_that_is_not_one_leaves_the_data_output_untouched(self):
        code, printed, errors = self.run_cli(["--export", "json",
                                              "--since", "hier"])
        self.assertEqual(code, 2)
        self.assertEqual(printed, "")
        self.assertIn("AAAA-MM-JJ", errors)

    def test_a_closed_pipe_is_said_beside_and_not_raised(self):
        """`--export csv | head` referme le tuyau : rien ne doit remonter."""
        self.write_log((days_ago(0), "20:00:00", self.goal()))

        def broken(*_args, **_kwargs):
            raise OSError(32, "Broken pipe")

        with mock.patch.object(cli, "_write_json", broken):
            code, _printed, errors = self.run_cli(["--export", "json"])
        self.assertEqual(code, 1)
        self.assertIn("export interrompu", errors)

    def test_a_closed_pipe_goes_through_the_real_byte_stream(self):
        """Le meme cas, mais par le vrai flux d'octets.

        Le test ci-dessus remplace _write_json : il n'atteint jamais le flux,
        donc il ne peut pas voir ce que celui-ci laisse derriere lui. Vert et
        aveugle, autrement dit. Celui-ci emprunte le chemin d'un vrai tuyau.
        """
        self.write_log((days_ago(0), "20:00:00", self.goal()))
        for shape in ("json", "csv"):
            console = BrokenPipeStdout()
            errors = io.StringIO()
            with mock.patch.object(sys, "stdout", console):
                with redirect_stderr(errors):
                    code = cli.main(["--export", shape])
            self.assertEqual(code, 1, shape)
            self.assertIn("export interrompu", errors.getvalue(), shape)
            # Les premiers octets sont bien passes par le flux avant la
            # coupure : c'est ce qui distingue ce test du precedent, qui
            # n'atteignait jamais le flux.
            self.assertTrue(console.buffer.getvalue(), shape)
        # Ce qu'aucun test en memoire ne peut voir, faute d'interprete qui
        # s'arrete : la trace que Python imprimait ensuite par-dessus le
        # message ci-dessus. Elle se verifie dans un vrai tuyau, a la main
        # (`--export csv | head`), et c'est dit dans les deux README.

    # ------------------------------------------------------------ la ligne --

    def test_only_the_two_formats_are_accepted(self):
        for wrong in ("xml", "JSON!", ""):
            with self.assertRaises(SystemExit):
                with redirect_stderr(io.StringIO()):
                    cli.build_parser().parse_args(["--export", wrong])

    def test_export_is_reachable_and_documented(self):
        help_text = cli.build_parser().format_help()
        self.assertIn("--export", help_text)
        self.assertIsNone(cli.build_parser().parse_args([]).export)



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


class SlowReporter:
    """Un rapporteur d'etat qui prend son temps, et le dit pendant qu'il ecrit.

    L'ecriture du fichier d'etat est le seul geste du fil de surveillance qui
    dure : c'est celui qu'on abandonnait en cours de route. En vrai il tient
    quelques millisecondes, assez pour que la course ne se voie qu'une fois
    sur deux et seulement sous Windows. On l'etire ici pour qu'elle soit
    certaine a chaque passage.
    """

    def __init__(self, real, delay=0.3):
        self.real = real
        self.delay = delay
        self.updates = 0
        self.writing = False

    def update(self, *args, **kwargs):
        self.updates += 1
        self.writing = True
        try:
            time.sleep(self.delay)
            return self.real.update(*args, **kwargs)
        finally:
            self.writing = False


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
        self.paths = isolate_data_dir(self)
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

    def test_the_watch_thread_is_awaited_before_the_loop_returns(self):
        """On ne rend pas la main pendant que le fil ecrit encore l'etat.

        Le fil de surveillance est le seul a appeler reporter.update(). La
        boucle rendait la main sans l'attendre : ce qui suit - l'effacement de
        l'etat, la fin du processus - passait alors par-dessus une ecriture en
        cours. Ca se voyait sous Windows a deux endroits, tous deux au hasard :
        un fichier d'etat relu vide, et un dossier temporaire qu'on ne pouvait
        plus effacer parce qu'il restait ouvert.
        """
        stopping = threading.Event()
        guard = self.guard_with_one_goal(stopping)
        stack = FakeStack(self.paths["state"], guard)
        stack.stopping = stopping
        reporter = SlowReporter(self.reporter())
        cli._watch_with_cards(guard, self.args, stopping, stack, reporter,
                              pinned.Pin(""))

        self.assertFalse(reporter.writing, "le fil ecrivait encore")
        # Et ce qu'il a ecrit est complet, pas un fichier a moitie pose.
        data = state.read(self.paths["state"])
        self.assertIsNotNone(data)
        self.assertEqual(data["goals_today"], 1)

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
        self.paths = isolate_data_dir(self)
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
        self.paths = isolate_data_dir(self)
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


class TestQuietHoursLoops(unittest.TestCase):
    """--quiet-hours : rien a l'ecran, rien au haut-parleur, tout au journal.

    C'est le meme contrat que le mode sans spoiler, pour une autre raison : la
    nuit plutot que le differe. D'ou les memes verifications - et une de plus,
    parce que le crochet, lui, continue de partir.
    """

    def setUp(self):
        self.paths = isolate_data_dir(self)
        self.paths["data"].mkdir(parents=True, exist_ok=True)
        self.args = cli.build_parser().parse_args(["--quiet"])

    def hush(self, hour):
        """Le verdict d'une nuit, a l'heure qu'on veut : jamais celle de la CI."""
        return silence.Silence("23:00-08:00",
                               clock=lambda: datetime(2026, 9, 6, hour, 0))

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

    def run_headless(self, hour, pin=""):
        stopping = threading.Event()
        guard = self.guard_with_one_goal(stopping)
        with mock.patch.object(cli, "play_goal_sound") as horn:
            with mock.patch.object(cli, "log") as journal:
                cli._watch_headless(guard, self.args, stopping,
                                    self.reporter(), pinned.Pin(pin),
                                    hush=self.hush(hour))
        return horn, journal

    def run_with_cards(self, hour, pin=""):
        stopping = threading.Event()
        guard = self.guard_with_one_goal(stopping)
        stack = FakeStack(self.paths["state"], guard)
        stack.stopping = stopping
        with mock.patch.object(cli, "play_goal_sound") as horn:
            with mock.patch.object(cli, "log") as journal:
                cli._watch_with_cards(guard, self.args, stopping, stack,
                                      self.reporter(), pinned.Pin(pin),
                                      hush=self.hush(hour))
        return stack, horn, journal

    # ------------------------------------------------------ pendant la nuit --

    def test_the_headless_loop_stays_silent_at_two_in_the_morning(self):
        horn, journal = self.run_headless(2)
        horn.assert_not_called()
        self.assertIn("BUT", " ".join(str(c) for c in journal.call_args_list))

    def test_the_card_loop_shows_and_sounds_nothing_at_two_in_the_morning(self):
        stack, horn, journal = self.run_with_cards(2)
        self.assertEqual(stack.cards, [])
        horn.assert_not_called()
        self.assertIn("BUT", " ".join(str(c) for c in journal.call_args_list))

    def test_the_goal_still_reaches_the_journal_file(self):
        """Le coeur du reglage : --today doit le retrouver au reveil."""
        stopping = threading.Event()
        guard = self.guard_with_one_goal(stopping)
        stack = FakeStack(self.paths["state"], guard)
        stack.stopping = stopping
        cli._watch_with_cards(guard, self.args, stopping, stack,
                              self.reporter(), pinned.Pin(""),
                              hush=self.hush(2))

        written = self.paths["log"].read_text(encoding="utf-8")
        self.assertIn("BUT", written)
        self.assertIn("Angers", written)
        self.assertEqual(stack.cards, [])

    def test_the_pinned_card_goes_away_for_the_night_too(self):
        """Aucune carte vaut aussi pour celle qui reste allumee en permanence."""
        stack, _horn, _journal = self.run_with_cards(2, pin="angers")
        self.assertEqual(stack.pinned, [])
        self.assertEqual(stack.unpinned, 1)
        # Le daemon suit toujours le match : --status ne doit pas mentir.
        self.assertEqual(state.read(self.paths["state"])["pinned"]["home"],
                         "Angers")

    def test_the_hook_still_fires_during_the_night(self):
        """Le silence protege cet ecran et ce haut-parleur, pas un telephone.

        C'est la difference avec --spoiler-free, qui coupe tout : la nuit, on
        veut justement que la commande qui pousse une notification ailleurs
        parte, sinon le reglage reviendrait a arreter le daemon.
        """
        stopping = threading.Event()
        guard = self.guard_with_one_goal(stopping)
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
                            pinned.Pin(""), on_goal=runner, hush=self.hush(2))
        if thread is not None:
            thread.join(5.0)
        self.assertEqual(len(fired), 1)

    # ------------------------------------------------------ hors de la nuit --

    def test_the_headless_loop_sounds_the_goal_at_two_in_the_afternoon(self):
        horn, _journal = self.run_headless(14)
        self.assertTrue(horn.called)

    def test_the_card_loop_shows_the_goal_at_two_in_the_afternoon(self):
        stack, horn, _journal = self.run_with_cards(14)
        self.assertEqual(len(stack.cards), 1)
        self.assertTrue(horn.called)

    def test_the_pinned_card_is_back_outside_the_window(self):
        stack, _horn, _journal = self.run_with_cards(14, pin="angers")
        self.assertEqual(len(stack.pinned), 1)
        self.assertEqual(stack.unpinned, 0)

    # --------------------------------------------------------- degradation --

    def test_a_detection_that_fails_lets_the_card_through(self):
        """La presentation indetectable ramene au comportement d'avant."""
        stopping = threading.Event()
        guard = self.guard_with_one_goal(stopping)
        stack = FakeStack(self.paths["state"], guard)
        stack.stopping = stopping
        lines = []
        hush = silence.Silence(while_presenting=True, on_log=lines.append)
        with mock.patch.object(presenting, "state", return_value=None):
            with mock.patch.object(cli, "play_goal_sound") as horn:
                cli._watch_with_cards(guard, self.args, stopping, stack,
                                      self.reporter(), pinned.Pin(""),
                                      hush=hush)
        self.assertEqual(len(stack.cards), 1)
        self.assertTrue(horn.called)
        self.assertEqual(len(lines), 1)

    def test_a_loop_without_a_verdict_behaves_exactly_as_before(self):
        """Les deux boucles se passent d'un Silence : le rejeu n'en a pas."""
        stopping = threading.Event()
        guard = self.guard_with_one_goal(stopping)
        stack = FakeStack(self.paths["state"], guard)
        stack.stopping = stopping
        with mock.patch.object(cli, "play_goal_sound") as horn:
            cli._watch_with_cards(guard, self.args, stopping, stack,
                                  self.reporter(), pinned.Pin(""))
        self.assertEqual(len(stack.cards), 1)
        self.assertTrue(horn.called)


class TestTheVoiceInTheLoops(unittest.TestCase):
    """--speak : ce que la voix dit, quand elle se tait, et ce qu'elle encaisse.

    La voix suit exactement les regles du haut-parleur, parce qu'elle en est
    un : elle se tait la nuit et pendant une presentation, elle se tait sur un
    match regarde en differe, et une panne de synthetiseur ne doit pas plus
    remonter dans la boucle de surveillance qu'une carte son absente.

    Aucun synthetiseur n'est lance : `Voice.spawn` est injecte, comme ailleurs.
    """

    def setUp(self):
        self.paths = isolate_data_dir(self)
        self.paths["data"].mkdir(parents=True, exist_ok=True)
        self.args = cli.build_parser().parse_args(["--quiet", "--no-sound",
                                                   "--speak"])
        self.said = []

    def voice(self, raises=None):
        def spawn(command, env, timeout):
            self.said.append(command[-1])
            if raises is not None:
                raise raises
            return 0, ""

        found = speech.Voice(True, lang="fr", spawn=spawn, platform="linux",
                             which=lambda name: "/usr/bin/spd-say",
                             on_log=lambda message: None)
        self.addCleanup(found.close, 2.0)
        return found

    def hush(self, hour):
        return silence.Silence("23:00-08:00",
                               clock=lambda: datetime(2026, 9, 6, hour, 0))

    def guard_with_one_goal(self, stopping, spoiler_free=False):
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

    def run_headless(self, voice, hush=None, spoiler_free=False):
        stopping = threading.Event()
        guard = self.guard_with_one_goal(stopping, spoiler_free)
        cli._watch_headless(guard, self.args, stopping, self.reporter(),
                            pinned.Pin(""), hush=hush, voice=voice)
        return stopping

    def run_with_cards(self, voice, hush=None, spoiler_free=False):
        stopping = threading.Event()
        guard = self.guard_with_one_goal(stopping, spoiler_free)
        stack = FakeStack(self.paths["state"], guard)
        stack.stopping = stopping
        cli._watch_with_cards(guard, self.args, stopping, stack,
                              self.reporter(), pinned.Pin(""), voice=voice,
                              hush=hush)
        return stack

    def spoken(self, count=1, timeout=5.0):
        limit = time.monotonic() + timeout
        while len(self.said) < count and time.monotonic() < limit:
            time.sleep(0.005)
        return self.said

    # ------------------------------------------------------- un but ordinaire

    def test_the_headless_loop_says_the_goal(self):
        self.run_headless(self.voice())
        said = self.spoken()
        self.assertEqual(len(said), 1)
        # La phrase est celle du crochet, pas une deuxieme ecrite pour la voix.
        self.assertIn("BUT !", said[0])
        self.assertIn("Angers 1 - 0 Stade Rennais", said[0])

    def test_the_card_loop_says_the_goal_too(self):
        stack = self.run_with_cards(self.voice())
        self.assertEqual(len(stack.cards), 1)
        self.assertEqual(len(self.spoken()), 1)

    # ------------------------------------------------------------- le silence

    def test_nothing_is_said_at_two_in_the_morning(self):
        """Le silence de 1.8.0 vaut pour la voix : c'est un haut-parleur."""
        self.run_headless(self.voice(), hush=self.hush(2))
        time.sleep(0.1)
        self.assertEqual(self.said, [])
        # Et le journal, lui, garde tout : c'est tout le contrat.
        self.assertIn("BUT", self.paths["log"].read_text(encoding="utf-8"))

    def test_nothing_is_said_at_two_in_the_morning_with_cards_either(self):
        stack = self.run_with_cards(self.voice(), hush=self.hush(2))
        time.sleep(0.1)
        self.assertEqual(self.said, [])
        self.assertEqual(stack.cards, [])

    def test_the_goal_is_said_again_outside_the_window(self):
        self.run_headless(self.voice(), hush=self.hush(14))
        self.assertEqual(len(self.spoken()), 1)

    def test_nothing_is_said_while_presenting(self):
        hush = silence.Silence(while_presenting=True)
        with mock.patch.object(presenting, "state",
                               return_value=presenting.PRESENTATION_MODE):
            self.run_with_cards(self.voice(), hush=hush)
        time.sleep(0.1)
        self.assertEqual(self.said, [])

    # -------------------------------------------------------- le sans-spoiler

    def test_a_match_watched_late_is_never_spoken(self):
        """Ce qui n'est pas montre ne se dit pas non plus : c'est le point."""
        self.run_headless(self.voice(), spoiler_free=True)
        time.sleep(0.1)
        self.assertEqual(self.said, [])
        self.assertIn("BUT", self.paths["log"].read_text(encoding="utf-8"))

    def test_a_match_watched_late_is_never_spoken_with_cards_either(self):
        stack = self.run_with_cards(self.voice(), spoiler_free=True)
        time.sleep(0.1)
        self.assertEqual(self.said, [])
        self.assertEqual(stack.cards, [])

    # ------------------------------------------------------------ degradation

    def test_a_broken_voice_never_reaches_the_watch_loop(self):
        """Une panne de synthetiseur ne coute ni la carte, ni le journal."""
        stack = self.run_with_cards(self.voice(raises=OSError("pas de son")))
        self.assertEqual(len(stack.cards), 1)
        self.assertIn("BUT", self.paths["log"].read_text(encoding="utf-8"))

    def test_a_loop_without_a_voice_behaves_exactly_as_before(self):
        """Le rejeu n'en passe aucune : les deux boucles s'en passent."""
        stopping = threading.Event()
        guard = self.guard_with_one_goal(stopping)
        cli._watch_headless(guard, self.args, stopping, self.reporter(),
                            pinned.Pin(""))
        self.assertEqual(self.said, [])

    def test_an_unarmed_voice_says_nothing_of_an_ordinary_goal(self):
        muette = speech.Voice(False, spawn=lambda *a: self.said.append(a))
        self.run_headless(muette)
        time.sleep(0.1)
        self.assertEqual(self.said, [])


class TestSpoilerFreeCommands(unittest.TestCase):
    """--scores, --status et la verification des mots au demarrage."""

    CATALOGUE = [("Angers", "Angers", "SCO"),
                 ("Stade Rennais", "Rennes", "REN")]

    def setUp(self):
        self.paths = isolate_data_dir(self)

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

    def test_scores_says_which_competition_a_womens_match_belongs_to(self):
        # Arsenal joue dans les deux : sans l'en-tete de competition, les deux
        # lignes seraient indiscernables.
        matches = espn.parse(
            payload(event(match_id="1", home="Arsenal", away="Chelsea",
                          state="in", home_score=1,
                          details=[goal_detail("H1", "35'", "B. Mead")])),
            leagues.BY_SLUG["eng.w.1"])
        buffer = io.StringIO()
        with mock.patch.object(espn, "scoreboard", return_value=matches):
            with mock.patch.object(espn, "catalogue", return_value=self.CATALOGUE):
                with redirect_stdout(buffer):
                    code = cli.main(["--scores", "--leagues", "wsl"])
        printed = buffer.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("Women's Super League", printed)
        self.assertIn("1 - 0", printed)
        self.assertIn("B. Mead", printed)

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
        self.folder = isolate_data_dir(self)["sound"]
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


class TestNamedSound(unittest.TestCase):
    """`--sound-for om=cri.wav` : le mot est donne, et le chemin verifie tot."""

    def setUp(self):
        self.folder = isolate_data_dir(self)["sound"]
        self.folder.mkdir(parents=True)
        self.mine = cli.paths()["data"] / "cris"
        self.mine.mkdir()

    def cri(self, name="cri.wav") -> Path:
        path = self.mine / name
        path.write_bytes(b"x")
        return path

    def args(self, *extra):
        return cli.build_parser().parse_args(
            ["--quiet", "--duration", "1"] + list(extra))

    def goal(self, side="home"):
        matches = espn.parse(
            payload(event(home="Marseille",
                          away=("Paris Saint-Germain", "Paris SG", "PSG"),
                          state="in", home_score=1)),
            leagues.BY_SLUG["fra.1"])
        match = matches[0]
        home = side == "home"
        return watcher.Event(kind=watcher.GOAL, match=match, side=side,
                             team=match.home if home else match.away,
                             opponent=match.away if home else match.home,
                             home_score=1, away_score=0, delta=1, play=None)

    def run_cli(self, argv, catalogue=(("Marseille", "OM", "MAR"),)):
        """main() sans reseau : catalogue et scoreboard sont fabriques."""
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(espn, "catalogue", return_value=list(catalogue)), \
                mock.patch.object(espn, "scoreboard", return_value=[]), \
                mock.patch.object(cli, "do_daemon", return_value=0):
            with redirect_stdout(out), redirect_stderr(err):
                code = cli.main(argv)
        return code, out.getvalue(), err.getvalue()

    # --- ce qui se dit au demarrage ------------------------------------------

    def test_a_missing_file_is_refused_before_the_first_goal(self):
        code, _out, err = self.run_cli(
            ["--sound-for", "om=" + str(self.mine / "absent.wav"),
             "--leagues", "l1"])
        self.assertEqual(code, 2)
        self.assertIn("introuvable", err)
        self.assertIn("om", err)

    def test_a_format_nobody_can_play_is_refused_too(self):
        note = self.mine / "cri.txt"
        note.write_bytes(b"x")
        code, _out, err = self.run_cli(
            ["--sound-for", "om=" + str(note), "--leagues", "l1"])
        self.assertEqual(code, 2)
        self.assertIn("format", err)

    def test_something_that_is_not_a_pair_is_refused(self):
        code, _out, err = self.run_cli(["--sound-for", "om", "--leagues", "l1"])
        self.assertEqual(code, 2)
        self.assertIn("nom=chemin", err)

    def test_a_misspelled_team_is_refused_like_anywhere_else(self):
        # Un cri nomme pour "marseile" ne sortirait jamais, et rien ne le
        # dirait : c'est exactement ce que check_teams() attrape ailleurs.
        code, _out, err = self.run_cli(
            ["--sound-for", "marseile=" + str(self.cri()), "--leagues", "l1"])
        self.assertEqual(code, 2)
        self.assertIn("marseile", err)

    def test_a_competition_is_not_looked_for_in_the_team_catalogue(self):
        code, _out, err = self.run_cli(
            ["--sound-for", "ucl=" + str(self.cri()), "--leagues", "l1"])
        self.assertEqual(code, 0, err)

    def test_a_good_pair_lets_the_daemon_start(self):
        code, _out, err = self.run_cli(
            ["--sound-for", "om=" + str(self.cri()), "--leagues", "l1"])
        self.assertEqual(code, 0, err)

    # --- ce qui sort au but --------------------------------------------------

    def chosen(self, args, event_=None):
        path, _duration = cli.resolve_sound(args, event_)
        return path.name

    def test_the_named_sound_plays_for_that_team_only(self):
        (self.folder / "corne.mp3").write_bytes(b"x")
        args = self.args("--sound-for", "om=" + str(self.cri()))
        self.assertEqual(self.chosen(args, self.goal("home")), "cri.wav")
        self.assertEqual(self.chosen(args, self.goal("away")), "corne.mp3")

    def test_the_team_wins_over_its_own_competition(self):
        args = self.args("--sound-for", "l1={},om={}".format(
            self.cri("l1.wav"), self.cri("cri.wav")))
        self.assertEqual(self.chosen(args, self.goal("home")), "cri.wav")
        self.assertEqual(self.chosen(args, self.goal("away")), "l1.wav")

    def test_what_is_named_covers_the_file_that_was_guessed(self):
        (self.folder / "om.mp3").write_bytes(b"x")
        args = self.args("--sound-for", "om=" + str(self.cri()))
        self.assertEqual(self.chosen(args, self.goal("home")), "cri.wav")

    def test_the_folder_keeps_the_goals_nobody_named(self):
        (self.folder / "corne.mp3").write_bytes(b"x")
        args = self.args("--sound-for", "psg=" + str(self.cri()))
        self.assertEqual(self.chosen(args, self.goal("home")), "corne.mp3")

    def test_no_sound_still_means_no_sound(self):
        args = self.args("--no-sound", "--sound-for",
                         "om=" + str(self.cri()))
        self.assertIsNone(cli.resolve_sound(args, self.goal("home"))[0])

    def test_a_sound_that_vanishes_degrades_and_lands_in_the_journal(self):
        (self.folder / "corne.mp3").write_bytes(b"x")
        cri = self.cri()
        args = self.args("--sound-for", "om=" + str(cri))
        cri.unlink()                      # la cle USB vient d'etre debranchee
        self.assertEqual(self.chosen(args, self.goal("home")), "corne.mp3")
        written = cli.paths()["log"].read_text(encoding="utf-8")
        self.assertIn("son nomme pour om", written)
        self.assertIn("introuvable", written)

    # --- ce que --status en dit ----------------------------------------------

    def test_status_says_what_each_pair_arms(self):
        args = self.args("--teams", "om", "--sound-for",
                         "om={},ucl={},contre={}".format(
                             self.cri("cri.wav"), self.cri("hymne.wav"),
                             self.cri("aie.wav")))
        rows = dict(cli._named_arming(cli.sound_assignments(args), args,
                                      [leagues.BY_SLUG["fra.1"]]))
        self.assertIn("marque", rows["om -> cri.wav"])
        self.assertIn("non suivie", rows["ucl -> hymne.wav"])
        self.assertIn("encaisse", rows["contre -> aie.wav"])

    def test_status_says_when_a_named_file_is_gone(self):
        cri = self.cri()
        args = self.args("--sound-for", "om=" + str(cri))
        cri.unlink()
        rows = dict(cli._named_arming(cli.sound_assignments(args), args))
        self.assertIn("introuvable", rows["om -> cri.wav"])

    def test_status_is_not_refused_when_a_named_file_is_gone(self):
        # Le meme cas, mais par la vraie ligne de commande : le refus au
        # demarrage vaut pour tout le monde SAUF --status, sans quoi la seule
        # commande capable de repondre "voila ce qui cloche" sortirait en 2
        # avant d'avoir rien affiche. Le test ci-dessus, lui, appelle
        # _named_arming() en direct : il ne verrait pas ce refus-la.
        cri = self.cri()
        cri.unlink()
        code, printed, complained = self.run_cli(
            ["--status", "--sound-for", "om=" + str(cri), "--leagues", "l1"])
        self.assertEqual(code, 0)
        self.assertIn("om -> cri.wav", printed)
        self.assertIn("introuvable", printed)
        self.assertNotIn("introuvable", complained)


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

    def setUp(self):
        isolate_data_dir(self)

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

    def test_it_reads_a_womens_competition_like_any_other(self):
        # Meme endpoint, meme lecture : ce qui se verifie ici, c'est que la
        # competition arrive bien jusqu'au bout de la commande, en-tete
        # compris - et que les deux Arsenal ne se melangent pas.
        code, printed = run_next(
            ["--next", "--leagues", "l1f,wsl"],
            {"fra.w.1": fixtures(("1", "Paris FC", "OL Lyonnes",
                                  at_local_hour(1, 21)), slug="fra.w.1"),
             "eng.w.1": fixtures(("2", "Arsenal", "Chelsea",
                                  at_local_hour(1, 18)), slug="eng.w.1")})
        self.assertEqual(code, 0)
        self.assertIn("Premiere Ligue F", printed)
        self.assertIn("Women's Super League", printed)
        self.assertIn("OL Lyonnes", printed)
        self.assertIn("2 match(s) a venir dans 2 competition(s), sur 7 jour(s).",
                      printed)

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


class Cp1252(io.TextIOWrapper):
    """Une sortie sur la page de code ANSI de Windows, terminal ou non."""

    def __init__(self, tty):
        io.TextIOWrapper.__init__(self, io.BytesIO(), encoding="cp1252")
        self._tty = tty

    def isatty(self):
        return self._tty


class TestUtf8Output(unittest.TestCase):
    # Un buteur dont le nom sort de la page de code ANSI : le 'n' polonais de
    # Zielinski. C'est lui qui terminait '--scores > matchs.txt' sur une
    # UnicodeEncodeError au lieu du score.
    BUTEUR = "P. Zieli\u0144ski"

    def test_a_redirected_output_switches_to_utf8(self):
        flux = Cp1252(tty=False)
        with mock.patch.object(cli.sys, "stdout", flux):
            cli.utf8_output()
        self.assertEqual(flux.encoding, "utf-8")
        flux.write(self.BUTEUR)
        flux.flush()
        self.assertEqual(flux.buffer.getvalue().decode("utf-8"), self.BUTEUR)

    def test_a_console_keeps_its_code_page_but_stops_crashing(self):
        # La console sait ce qu'elle sait dessiner : on ne lui impose pas
        # l'UTF-8, on lui retire seulement le droit de lever une exception.
        flux = Cp1252(tty=True)
        with mock.patch.object(cli.sys, "stdout", flux):
            cli.utf8_output()
        self.assertEqual(flux.encoding, "cp1252")
        flux.write(self.BUTEUR)      # ne leve plus UnicodeEncodeError
        flux.flush()
        self.assertEqual(flux.buffer.getvalue(), b"P. Zieli?ski")

    def test_stderr_is_reconfigured_too(self):
        # Un message d'erreur peut nommer un club autant qu'une carte.
        flux = Cp1252(tty=False)
        with mock.patch.object(cli.sys, "stderr", flux):
            cli.utf8_output()
        self.assertEqual(flux.encoding, "utf-8")

    def test_a_captured_output_is_left_alone(self):
        # Sous pytest, ou ici meme, sys.stdout n'a pas de reconfigure().
        with mock.patch.object(cli.sys, "stdout", io.StringIO()):
            cli.utf8_output()   # ne leve pas

    def test_a_closed_output_is_left_alone(self):
        flux = Cp1252(tty=False)
        flux.close()
        with mock.patch.object(cli.sys, "stdout", flux):
            cli.utf8_output()   # ne leve pas


class TestScopeChecking(unittest.TestCase):
    """Un prefixe de competition se verifie sans reseau, donc avant tout.

    Les deux fautes valent un refus au demarrage parce qu'elles ont le meme
    effet : le mot ne s'applique jamais, et rien ne le dit.
    """

    def check(self, wanted, selection):
        erreur = io.StringIO()
        with redirect_stderr(erreur):
            code = cli.check_scopes([teams.Filter(wanted=wanted)], selection)
        return code, erreur.getvalue()

    def test_a_known_prefix_of_a_followed_competition_passes(self):
        code, sortie = self.check("ligue2:sochaux",
                                  leagues.resolve("big5,ligue2"))
        self.assertEqual(code, 0)
        self.assertEqual(sortie, "")

    def test_a_prefix_that_names_no_competition_is_refused(self):
        code, sortie = self.check("ligu2:sochaux", leagues.resolve("big5"))
        self.assertEqual(code, 2)
        self.assertIn("ligu2:sochaux", sortie)

    def test_a_prefix_outside_the_selection_is_refused(self):
        # Ligue 2 existe, mais elle n'est pas suivie : ce mot ne servirait
        # jamais, et le daemon resterait muet sur Sochaux sans rien dire.
        code, sortie = self.check("ligue2:sochaux", leagues.resolve("big5"))
        self.assertEqual(code, 2)
        self.assertIn("--leagues", sortie)

    def test_words_without_prefix_are_none_of_its_business(self):
        code, sortie = self.check("om,psg", leagues.resolve("big5"))
        self.assertEqual(code, 0)
        self.assertEqual(sortie, "")

    def test_an_unfound_bounded_word_only_names_its_own_competition(self):
        # 'ligue2:om' n'a ete cherche qu'en Ligue 2 : lui reprocher les cinq
        # grands championnats enverrait corriger la mauvaise chose.
        selection = leagues.resolve("big5,ligue2")
        groupes = cli.orphan_groups(["ligue2:om"], selection)
        self.assertEqual(groupes, [("'ligue2:om'", "Ligue 2")])

    def test_free_words_keep_the_whole_selection_in_one_message(self):
        selection = leagues.resolve("l1,ligue2")
        groupes = cli.orphan_groups(["marseile", "ligue2:om"], selection)
        self.assertEqual(groupes[0], ("'marseile'", leagues.describe(selection)))
        self.assertEqual(groupes[1], ("'ligue2:om'", "Ligue 2"))


if __name__ == "__main__":
    unittest.main()


class TestAucunAffichage(unittest.TestCase):
    """Le daemon sort au lieu de tourner aveugle jusqu'a la deconnexion.

    L'environnement d'un processus ne change plus une fois qu'il tourne :
    demarre avant que la session ne publie DISPLAY, le daemon ne le verrait
    jamais apparaitre. Sortir en erreur laisse le superviseur le relancer avec
    l'environnement complet.
    """

    def setUp(self):
        self.paths = isolate_data_dir(self)

    def sans(self, *noms):
        propre = {k: v for k, v in os.environ.items() if k not in noms}
        return mock.patch.dict(os.environ, propre, clear=True)

    def avec(self, **variables):
        return mock.patch.dict(os.environ, variables, clear=False)

    def args(self, *argv):
        return cli.build_parser().parse_args(list(argv))

    def boucle_interdite(self):
        """Fait echouer le test si le daemon depasse le garde.

        Sans ce garde-fou, un correctif retire laisserait le test partir dans
        la vraie boucle de surveillance : il interrogerait le reseau et
        dormirait, donc se bloquerait au lieu d'echouer, ce qui ne previendrait
        personne.
        """
        def refus():
            raise AssertionError("le daemon est alle au-dela du garde")

        return mock.patch.object(cli, "claim_pid_file", refus)

    def test_ni_x11_ni_wayland(self):
        with mock.patch.object(cli.sys, "platform", "linux"), \
                self.sans("DISPLAY", "WAYLAND_DISPLAY"):
            self.assertTrue(cli.sans_affichage())

    def test_x11_suffit(self):
        with mock.patch.object(cli.sys, "platform", "linux"), \
                self.sans("WAYLAND_DISPLAY"), self.avec(DISPLAY=":0"):
            self.assertFalse(cli.sans_affichage())

    def test_wayland_suffit(self):
        with mock.patch.object(cli.sys, "platform", "linux"), \
                self.sans("DISPLAY"), self.avec(WAYLAND_DISPLAY="wayland-0"):
            self.assertFalse(cli.sans_affichage())

    def test_windows_et_macos_dessinent_sans_ces_variables(self):
        for plateforme in ("win32", "darwin"):
            with self.subTest(plateforme=plateforme):
                with mock.patch.object(cli.sys, "platform", plateforme), \
                        self.sans("DISPLAY", "WAYLAND_DISPLAY"):
                    self.assertFalse(cli.sans_affichage())

    def test_le_daemon_sort_en_5(self):
        with mock.patch.object(cli, "sans_affichage", lambda: True), \
                self.boucle_interdite():
            code = cli.do_daemon(self.args("--quiet"))
        self.assertEqual(code, 5)

    def test_le_daemon_ne_laisse_pas_de_fichier_pid(self):
        """Sortir avant de reclamer le pid : sinon la relance se croirait en
        double et sortirait en 1, cette fois pour de bon."""
        with mock.patch.object(cli, "sans_affichage", lambda: True), \
                self.boucle_interdite():
            cli.do_daemon(self.args("--quiet"))
        self.assertFalse(self.paths["pid"].exists())

    def test_le_journal_dit_pourquoi_meme_en_quiet(self):
        """L'unite tourne avec --quiet : sans le journal, le refus serait muet."""
        with mock.patch.object(cli, "sans_affichage", lambda: True), \
                self.boucle_interdite():
            cli.do_daemon(self.args("--quiet"))
        journal = self.paths["log"].read_text(encoding="utf-8")
        self.assertIn("aucun affichage joignable", journal)

    def test_no_overlay_n_a_pas_besoin_d_ecran(self):
        """Sans carte, il reste le son, la voix et le journal : refuser de
        demarrer priverait de tout ca pour une fenetre qu'on ne veut pas."""
        self.assertFalse(cli.besoin_d_affichage(self.args("--no-overlay")))

    def test_terminal_n_a_pas_besoin_d_ecran(self):
        self.assertFalse(cli.besoin_d_affichage(self.args("--terminal")))

    def test_le_mode_normal_en_a_besoin(self):
        self.assertTrue(cli.besoin_d_affichage(self.args()))

    def test_no_overlay_demarre_sans_affichage(self):
        """La regression que le garde pourrait introduire : un daemon muet et
        aveugle par choix ne doit pas etre refuse."""
        atteint = []

        def marqueur():
            atteint.append(True)
            return False        # coupe court, le garde a bien laisse passer

        with mock.patch.object(cli, "sans_affichage", lambda: True), \
                mock.patch.object(cli, "claim_pid_file", marqueur):
            code = cli.do_daemon(self.args("--no-overlay", "--quiet"))
        self.assertEqual(atteint, [True], "le garde a refuse a tort")
        self.assertEqual(code, 1)
