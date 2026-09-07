import io
import json
import os
import re
import threading
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from butbutbut import cli, espn, i18n, leagues, pinned, state, watcher

from helpers import event, goal_detail, payload


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


if __name__ == "__main__":
    unittest.main()
