"""Le crochet de --on-goal : ce qu'il passe, quand il part, et quand il se tait.

Rien ici ne lance de vrai processus, sauf le dernier cas : `Runner.spawn` est
injectable exactement pour ca. Le seul test qui execute vraiment quelque chose
lance l'interpreteur courant sur un script ecrit a la volee, ce qui marche
aussi bien sous cmd que sous sh.
"""

import os
import subprocess
import sys
import threading
import unittest
from tempfile import TemporaryDirectory
from pathlib import Path

from butbutbut import espn, hook, i18n, leagues, watcher

from helpers import bump, event, goal_detail, opener_for, payload

LIGUE1 = leagues.BY_SLUG["fra.1"]


def setUpModule():
    # Ces tests affirment des formulations francaises (le titre de la carte se
    # retrouve dans BUT_TEXT). Sans cet epinglage ils passeraient sur une
    # machine francaise et echoueraient sur la CI, dont les machines sont
    # anglaises.
    i18n.use("fr")


def _watcher(home=1, away=1, state_name="in"):
    source = {"payload": payload(event(home_score=home, away_score=away,
                                       state=state_name))}
    guard = watcher.Watcher([LIGUE1], opener=opener_for(source))
    guard.prime()
    return guard, source


def a_goal():
    """Un vrai evenement de but, sorti du watcher et pas fabrique a la main."""
    guard, source = _watcher()
    source["payload"] = bump(
        source["payload"], "away",
        details=(goal_detail("A1", "58'", "A. Kalimuendo", index=3),))
    return guard.refresh(LIGUE1)[0]


def a_cancelled_goal():
    guard, source = _watcher(home=1, away=2)
    source["payload"] = bump(source["payload"], "away", by=-1)
    return guard.refresh(LIGUE1)[0]


def a_kickoff():
    guard, source = _watcher(home=0, away=0, state_name="pre")
    source["payload"] = payload(event(home_score=0, away_score=0, state="in"))
    return guard.refresh(LIGUE1)[0]


class Recorder:
    """Un `spawn` qui note ce qu'on lui demande, au lieu de le lancer."""

    def __init__(self, code=0, output="", raises=None):
        self.calls = []
        self.code = code
        self.output = output
        self.raises = raises

    def __call__(self, command, env, timeout):
        self.calls.append((command, env, timeout))
        if self.raises is not None:
            raise self.raises
        return self.code, self.output


def run_and_wait(runner, event_):
    """fire() rend la main tout de suite : un test, lui, doit attendre."""
    thread = runner.fire(event_)
    if thread is not None:
        thread.join(5.0)
    return thread


class TestEnvironment(unittest.TestCase):
    def test_a_goal_describes_itself_completely(self):
        values = hook.environment(a_goal())
        self.assertEqual(values["BUT_TYPE"], "goal")
        self.assertEqual(values["BUT_LEAGUE"], "Ligue 1")
        self.assertEqual(values["BUT_LEAGUE_CODE"], "fra.1")
        self.assertEqual(values["BUT_HOME"], "Angers")
        self.assertEqual(values["BUT_AWAY"], "Stade Rennais")
        self.assertEqual(values["BUT_HOME_SCORE"], "1")
        self.assertEqual(values["BUT_AWAY_SCORE"], "2")
        self.assertEqual(values["BUT_SCORE"], "1 - 2")
        self.assertEqual(values["BUT_TEAM"], "Stade Rennais")
        self.assertEqual(values["BUT_OPPONENT"], "Angers")
        self.assertEqual(values["BUT_SIDE"], "away")
        self.assertEqual(values["BUT_SCORER"], "A. Kalimuendo")
        self.assertEqual(values["BUT_MINUTE"], "58'")
        self.assertEqual(values["BUT_OWN_GOAL"], "0")
        self.assertEqual(values["BUT_PENALTY"], "0")
        self.assertEqual(values["BUT_DELTA"], "1")

    def test_text_is_the_ready_made_sentence(self):
        # C'est la variable que 90 % des scripts utiliseront seule.
        values = hook.environment(a_goal())
        self.assertEqual(
            values["BUT_TEXT"],
            "BUT ! [Ligue 1] Angers 1 - 2 Stade Rennais"
            " - But de A. Kalimuendo (58')")

    def test_everything_is_a_string(self):
        # Un environnement n'accepte que des chaines : un entier ou un None qui
        # passerait ici ferait tomber le lancement, pas la valeur.
        for value in hook.environment(a_goal()).values():
            self.assertIsInstance(value, str)

    def test_a_goal_without_a_scorer_still_works(self):
        # Le tableau des actions arrive parfois quelques secondes apres le
        # score : le crochet ne doit pas attendre le nom du buteur.
        guard, source = _watcher()
        source["payload"] = bump(source["payload"], "away")
        values = hook.environment(guard.refresh(LIGUE1)[0])
        self.assertEqual(values["BUT_SCORER"], "")
        self.assertEqual(values["BUT_TEAM"], "Stade Rennais")

    def test_a_cancelled_goal_says_so(self):
        values = hook.environment(a_cancelled_goal())
        self.assertEqual(values["BUT_TYPE"], "cancelled")
        self.assertEqual(values["BUT_DELTA"], "-1")

    def test_an_own_goal_and_a_penalty_are_flagged(self):
        guard, source = _watcher()
        source["payload"] = bump(
            source["payload"], "away",
            details=(goal_detail("A1", "58'", "J. Lefort", penalty=True,
                                 index=3),))
        values = hook.environment(guard.refresh(LIGUE1)[0])
        self.assertEqual(values["BUT_PENALTY"], "1")
        self.assertEqual(values["BUT_OWN_GOAL"], "0")

    def test_the_demo_matches_the_real_thing(self):
        # Le seul garde-fou contre une demo qui derive : --test-hook doit
        # montrer exactement les variables qu'un vrai but posera.
        self.assertEqual(set(hook.demo()), set(hook.environment(a_goal())))
        for value in hook.demo().values():
            self.assertIsInstance(value, str)

    def test_merge_keeps_the_environment_of_the_daemon(self):
        # Sans PATH ni HOME, la moitie des commandes ne marcheraient pas.
        merged = hook.merge({"BUT_TEAM": "Marseille"})
        self.assertEqual(merged["BUT_TEAM"], "Marseille")
        for key in os.environ:
            self.assertIn(key, merged)


class TestWhatFires(unittest.TestCase):
    def test_a_goal_fires_the_command(self):
        spy = Recorder()
        runner = hook.Runner("peu importe", spawn=spy)
        run_and_wait(runner, a_goal())
        self.assertEqual(len(spy.calls), 1)
        command, env, _timeout = spy.calls[0]
        self.assertEqual(command, "peu importe")
        self.assertEqual(env["BUT_SCORER"], "A. Kalimuendo")

    def test_a_cancelled_goal_fires_it_too(self):
        # Annoncer un but puis se taire quand la VAR le refuse, ce serait
        # mentir a ce qu'on alimente. BUT_TYPE laisse filtrer qui veut.
        spy = Recorder()
        runner = hook.Runner("peu importe", spawn=spy)
        run_and_wait(runner, a_cancelled_goal())
        self.assertEqual(len(spy.calls), 1)
        self.assertEqual(spy.calls[0][1]["BUT_TYPE"], "cancelled")

    def test_a_phase_card_fires_nothing(self):
        # L'option promet un but : un coup d'envoi n'en est pas un.
        spy = Recorder()
        runner = hook.Runner("peu importe", spawn=spy)
        self.assertIsNone(run_and_wait(runner, a_kickoff()))
        self.assertEqual(spy.calls, [])

    def test_without_a_command_nothing_happens(self):
        runner = hook.Runner(None, spawn=Recorder())
        self.assertFalse(runner)
        self.assertIsNone(run_and_wait(runner, a_goal()))

    def test_blank_spaces_are_not_a_command(self):
        self.assertFalse(hook.Runner("   "))

    def test_too_many_at_once_are_refused(self):
        # Un script qui ne rend jamais la main ne doit pas finir par tenir un
        # fil par but de la journee.
        released = threading.Event()
        started = threading.Semaphore(0)

        def slow(_command, _env, _timeout):
            started.release()
            released.wait(5.0)
            return 0, ""

        notes = []
        runner = hook.Runner("lent", spawn=slow, on_log=notes.append)
        goal = a_goal()
        threads = [runner.fire(goal) for _ in range(hook.MAX_INFLIGHT)]
        for _ in range(hook.MAX_INFLIGHT):
            started.acquire(timeout=5.0)

        self.assertIsNone(runner.fire(goal))
        self.assertTrue(any("deja en cours" in note for note in notes))

        released.set()
        for thread in threads:
            thread.join(5.0)
        # La place se libere : le but suivant repart normalement.
        self.assertIsNotNone(run_and_wait(runner, goal))


class TestFailuresAreOnlyNoted(unittest.TestCase):
    def test_a_silent_success_says_nothing(self):
        notes = []
        runner = hook.Runner("ok", spawn=Recorder(0, "tout va bien"),
                             on_log=notes.append)
        run_and_wait(runner, a_goal())
        self.assertEqual(notes, [])

    def test_a_non_zero_exit_is_noted_with_its_first_line(self):
        notes = []
        runner = hook.Runner("ko", spawn=Recorder(3, "curl: (7) refuse\nsuite"),
                             on_log=notes.append)
        run_and_wait(runner, a_goal())
        self.assertEqual(len(notes), 1)
        self.assertIn("3", notes[0])
        self.assertIn("curl: (7) refuse", notes[0])
        self.assertNotIn("suite", notes[0])

    def test_a_command_that_never_returns_is_killed_and_noted(self):
        notes = []
        runner = hook.Runner("bloque", on_log=notes.append,
                             spawn=Recorder(raises=hook.Timeout(30.0)))
        run_and_wait(runner, a_goal())
        self.assertEqual(len(notes), 1)
        self.assertIn("tuee", notes[0])

    def test_a_command_that_cannot_be_launched_is_noted(self):
        notes = []
        runner = hook.Runner("n_importe_quoi", on_log=notes.append,
                             spawn=Recorder(raises=OSError("introuvable")))
        run_and_wait(runner, a_goal())
        self.assertEqual(len(notes), 1)
        self.assertIn("introuvable", notes[0])

    def test_a_failure_never_escapes_the_thread(self):
        # Le contrat du module : le crochet ne peut pas tuer le daemon.
        runner = hook.Runner("ko", spawn=Recorder(raises=RuntimeError("boum")))
        thread = run_and_wait(runner, a_goal())
        self.assertFalse(thread.is_alive())


class TestForReal(unittest.TestCase):
    """Le seul test qui lance vraiment un processus, bout en bout."""

    def test_the_command_receives_the_variables(self):
        with TemporaryDirectory() as folder:
            script = Path(folder) / "crochet.py"
            output = Path(folder) / "vu.txt"
            script.write_text(
                "import os, sys\n"
                "open(sys.argv[1], 'w', encoding='utf-8').write("
                "os.environ['BUT_TEXT'])\n",
                encoding="utf-8")
            # Les guillemets tiennent aussi bien sous sh que sous cmd, et le
            # chemin de l'interpreteur peut contenir des espaces.
            command = '"{}" "{}" "{}"'.format(sys.executable, script, output)

            runner = hook.Runner(command)
            code, _text = runner.call(hook.demo())

            self.assertEqual(code, 0)
            self.assertEqual(output.read_text(encoding="utf-8"),
                             hook.demo()["BUT_TEXT"])

    def test_a_failing_command_gives_back_its_code(self):
        command = '"{}" -c "raise SystemExit(4)"'.format(sys.executable)
        code, _text = hook.Runner(command).call(hook.demo())
        self.assertEqual(code, 4)


if __name__ == "__main__":
    unittest.main()
