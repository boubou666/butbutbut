"""La voix de --speak : ce qu'elle lance, et tout ce qu'elle encaisse.

Rien ici ne fait parler une machine. `Voice.spawn` et `command_for(which=...)`
sont injectables exactement pour ca : la CI tourne sans carte son, sans
speech-dispatcher, et sur trois systemes dont deux ne sont pas celui du
developpeur. On verifie donc la commande CONSTRUITE, pas ce qu'elle produit.

La langue est epinglee : une phrase francaise sortirait autrement sur une
machine allemande, et la culture demandee a System.Speech en depend.
"""

import threading
import time
import unittest

from butbutbut import i18n, speech


def setUpModule():
    i18n.use("fr")


def which_for(*names):
    """Un `shutil.which` qui ne connait que les programmes qu'on lui nomme."""
    found = set(names)
    return lambda name: "/usr/bin/" + name if name in found else None


def windows_which(*names):
    """Le meme, mais avec des chemins qui ressemblent a ceux de Windows."""
    found = set(names)
    return lambda name: (
        "C:\\Windows\\System32\\{}.exe".format(name) if name in found else None)


class Recorder:
    """Un `spawn` qui note ce qu'on lui demande, au lieu de faire parler.

    `hold` retient le premier appel : c'est la seule facon de remplir la file
    d'attente pendant que la voix est occupee, donc de voir ce qu'elle jette.
    """

    def __init__(self, code=0, output="", raises=None, hold=None):
        self.calls = []
        self.code = code
        self.output = output
        self.raises = raises
        self.hold = hold
        self._lock = threading.Lock()

    def __call__(self, command, env, timeout):
        if self.hold is not None and not self.calls:
            with self._lock:
                self.calls.append((command, env, timeout))
            self.hold.wait(5.0)
        else:
            with self._lock:
                self.calls.append((command, env, timeout))
        if self.raises is not None:
            raise self.raises
        return self.code, self.output

    @property
    def spoken(self) -> list:
        """Les phrases dites, dans l'ordre : le dernier argument de chacune."""
        return [command[-1] for command, _env, _timeout in self.calls]


def until(condition, timeout=5.0) -> bool:
    """Attend qu'une condition soit vraie. La voix vit dans un fil a elle."""
    limit = time.monotonic() + timeout
    while time.monotonic() < limit:
        if condition():
            return True
        time.sleep(0.005)
    return condition()


def voice_for(recorder, names=("spd-say",), platform="linux", **extra):
    """Une voix branchee sur un faux systeme et un faux synthetiseur."""
    extra.setdefault("lang", "fr")
    extra.setdefault("pause", lambda seconds: None)
    return speech.Voice(True, spawn=recorder, platform=platform,
                        which=which_for(*names), **extra)


# ------------------------------------------------------------- la commande ---

class TestTheCommandPerPlatform(unittest.TestCase):
    def test_windows_speaks_through_powershell(self):
        command, env = speech.command_for(
            "BUT !", "fr", platform="win32",
            which=windows_which("powershell"))
        self.assertTrue(command[0].lower().endswith("powershell.exe"))
        self.assertIn("-NoProfile", command)
        self.assertIn("-Command", command)
        self.assertIn("System.Speech", command[-1])
        self.assertEqual(env[speech.ENV_TEXT], "BUT !")

    def test_windows_never_glues_the_text_into_the_script(self):
        """Le jour ou un club s'appellera "'; rm -rf ~", ce sera un nom.

        Meme regle qu'au crochet : les valeurs viennent du reseau, elles
        restent des valeurs. Ici elles passent par l'environnement.
        """
        vilain = "'; Remove-Item C:\\ -Recurse; '"
        command, env = speech.command_for(
            vilain, "fr", platform="win32", which=windows_which("powershell"))
        self.assertNotIn(vilain, " ".join(command))
        self.assertEqual(env[speech.ENV_TEXT], vilain)

    def test_windows_asks_for_the_culture_of_the_cards(self):
        for lang, culture in (("fr", "fr-FR"), ("de", "de-DE"),
                              ("es", "es-ES"), ("it", "it-IT"),
                              ("en", "en-US")):
            _command, env = speech.command_for(
                "BUT !", lang, platform="win32",
                which=windows_which("powershell"))
            self.assertEqual(env[speech.ENV_CULTURE], culture, lang)

    def test_windows_falls_back_to_powershell_7(self):
        command, _env = speech.command_for(
            "BUT !", "fr", platform="win32", which=windows_which("pwsh"))
        self.assertTrue(command[0].lower().endswith("pwsh.exe"))

    def test_macos_speaks_through_say(self):
        command, env = speech.command_for("BUT !", "fr", platform="darwin",
                                          which=which_for("say"))
        self.assertEqual(command, ["/usr/bin/say", "BUT !"])
        # `say` n'a pas d'option de langue : rien a inventer, donc rien de plus.
        self.assertEqual(env, {})

    def test_linux_prefers_speech_dispatcher(self):
        command, _env = speech.command_for(
            "BUT !", "fr", platform="linux",
            which=which_for("spd-say", "espeak-ng", "espeak"))
        self.assertEqual(command,
                         ["/usr/bin/spd-say", "-w", "-l", "fr", "BUT !"])

    def test_linux_falls_back_in_order(self):
        command, _env = speech.command_for(
            "BUT !", "fr", platform="linux",
            which=which_for("espeak-ng", "espeak"))
        self.assertEqual(command, ["/usr/bin/espeak-ng", "-v", "fr", "BUT !"])

        command, _env = speech.command_for("BUT !", "fr", platform="linux",
                                           which=which_for("espeak"))
        self.assertEqual(command, ["/usr/bin/espeak", "-v", "fr", "BUT !"])

    def test_the_language_of_the_cards_is_the_language_spoken(self):
        command, _env = speech.command_for("TOR!", "de", platform="linux",
                                           which=which_for("spd-say"))
        self.assertIn("de", command)

    def test_nothing_installed_is_no_command_at_all(self):
        self.assertIsNone(speech.command_for("BUT !", "fr", platform="linux",
                                             which=which_for()))
        self.assertIsNone(speech.find(platform="darwin", which=which_for()))
        self.assertIsNone(speech.find(platform="win32", which=which_for()))

    def test_a_text_that_starts_with_a_dash_is_not_read_as_an_option(self):
        """La source ecrit ce qu'elle veut ; espeak, lui, lit ses arguments."""
        command, _env = speech.command_for("-v fr et voila", "fr",
                                           platform="linux",
                                           which=which_for("espeak"))
        self.assertFalse(command[-1].startswith("-"))
        self.assertIn("-v fr et voila", command[-1])


class TestWhatItSaysOfItself(unittest.TestCase):
    def test_it_names_the_program_that_would_speak(self):
        voice = speech.Voice(True, platform="linux",
                             which=which_for("espeak-ng"))
        self.assertIn("espeak-ng", voice.describe())

    def test_it_says_when_nothing_can_speak(self):
        voice = speech.Voice(True, platform="linux", which=which_for())
        self.assertIn("aucun", voice.describe())

    def test_an_unarmed_voice_still_says_who_would_speak(self):
        """--status doit repondre avant qu'on ait pose l'option, pas apres."""
        voice = speech.Voice(False, platform="darwin", which=which_for("say"))
        self.assertIn("--speak", voice.describe())
        self.assertIn("say", voice.describe())


# ---------------------------------------------------------- ce qu'elle dit ---

class TestWhenItSpeaks(unittest.TestCase):
    def test_the_phrase_reaches_the_synthesizer(self):
        recorder = Recorder()
        voice = voice_for(recorder)
        self.addCleanup(voice.close, 2.0)
        voice.say("BUT ! [Ligue 1] Angers 1 - 2 Stade Rennais")
        self.assertTrue(until(lambda: recorder.calls))
        self.assertEqual(recorder.spoken,
                         ["BUT ! [Ligue 1] Angers 1 - 2 Stade Rennais"])

    def test_saying_gives_the_hand_back_at_once(self):
        """Le fil qui a trouve le but ne doit pas attendre la fin de la phrase."""
        started = threading.Event()
        release = threading.Event()

        def slow(command, env, timeout):
            started.set()
            release.wait(5.0)
            return 0, ""

        voice = voice_for(slow)
        self.addCleanup(voice.close, 2.0)
        voice.say("BUT !")
        self.assertTrue(started.wait(5.0))
        release.set()

    def test_a_voice_that_is_not_armed_never_launches_anything(self):
        recorder = Recorder()
        voice = speech.Voice(False, spawn=recorder, platform="linux",
                             which=which_for("spd-say"))
        voice.say("BUT !")
        time.sleep(0.05)
        self.assertEqual(recorder.calls, [])

    def test_an_empty_phrase_says_nothing(self):
        recorder = Recorder()
        voice = voice_for(recorder)
        self.addCleanup(voice.close, 2.0)
        for phrase in (None, "", "   "):
            voice.say(phrase)
        time.sleep(0.05)
        self.assertEqual(recorder.calls, [])

    def test_two_goals_in_a_row_do_not_talk_over_each_other(self):
        """Un match a rebondissements est le cas normal, pas l'exception."""
        recorder = Recorder()
        voice = voice_for(recorder)
        self.addCleanup(voice.close, 2.0)
        voice.say("premier but")
        voice.say("second but")
        self.assertTrue(until(lambda: len(recorder.calls) == 2))
        self.assertEqual(recorder.spoken, ["premier but", "second but"])

    def test_a_flurry_of_goals_drops_the_oldest_one_waiting(self):
        """La file est bornee : on veut savoir ou on en est, pas ou on en etait."""
        hold = threading.Event()
        recorder = Recorder(hold=hold)
        voice = voice_for(recorder, backlog=2)
        self.addCleanup(voice.close, 2.0)

        voice.say("but 1")
        self.assertTrue(until(lambda: recorder.calls))   # la voix est occupee
        for number in range(2, 6):
            voice.say("but {}".format(number))
        hold.set()

        self.assertTrue(until(lambda: len(recorder.calls) == 3))
        time.sleep(0.05)
        self.assertEqual(recorder.spoken, ["but 1", "but 4", "but 5"])


class TestWhenItWaitsForTheHorn(unittest.TestCase):
    def test_the_phrase_waits_for_the_sound_to_finish(self):
        waits = []
        recorder = Recorder()
        voice = voice_for(recorder, pause=waits.append)
        self.addCleanup(voice.close, 2.0)
        voice.say("BUT !", after=speech.AFTER_SOUND)
        self.assertTrue(until(lambda: recorder.calls))
        self.assertEqual(len(waits), 1)
        self.assertAlmostEqual(waits[0], speech.AFTER_SOUND, delta=0.5)

    def test_without_a_sound_there_is_nothing_to_wait_for(self):
        waits = []
        recorder = Recorder()
        voice = voice_for(recorder, pause=waits.append)
        self.addCleanup(voice.close, 2.0)
        voice.say("BUT !")
        self.assertTrue(until(lambda: recorder.calls))
        self.assertEqual(waits, [])

    def test_a_late_phrase_is_never_a_stale_phrase(self):
        """Un but annonce trois minutes apres n'est plus une nouvelle."""
        waits = []
        recorder = Recorder()
        voice = voice_for(recorder, pause=waits.append)
        self.addCleanup(voice.close, 2.0)
        voice.say("BUT !", after=600.0)
        self.assertTrue(until(lambda: recorder.calls))
        self.assertLessEqual(waits[0], speech.MAX_DELAY)


# ------------------------------------------------------------- degradation ---

class TestNothingKillsTheDaemon(unittest.TestCase):
    """Toutes les pannes possibles, et la meme reponse : une ligne, et on vit.

    Une ligne, et **une seule** : un daemon qui tourne un samedi entier
    ecrirait sinon autant de lignes que de buts pour une panne qui ne changera
    plus, et noierait justement les buts.
    """

    def voice(self, recorder, names=("spd-say",), lines=None):
        lines = [] if lines is None else lines
        found = voice_for(recorder, names=names, on_log=lines.append)
        self.addCleanup(found.close, 2.0)
        return found, lines

    def test_a_machine_without_a_synthesizer_says_so_once(self):
        recorder = Recorder()
        voice, lines = self.voice(recorder, names=())
        for _ in range(3):
            voice.say("BUT !")
        self.assertTrue(until(lambda: lines))
        time.sleep(0.05)
        self.assertEqual(len(lines), 1)
        self.assertIn("voix", lines[0])
        self.assertEqual(recorder.calls, [])

    def test_a_command_that_fails_is_noted_once(self):
        recorder = Recorder(code=1, output="cannot open audio device\nbis")
        voice, lines = self.voice(recorder)
        for _ in range(3):
            voice.say("BUT !")
        self.assertTrue(until(lambda: len(recorder.calls) == 3))
        time.sleep(0.05)
        self.assertEqual(len(lines), 1)
        self.assertIn("cannot open audio device", lines[0])
        # La seconde ligne de sortie ne monte pas au journal : une seule suffit
        # a dire ce qui cloche.
        self.assertNotIn("bis", lines[0])

    def test_a_command_that_never_returns_is_killed_and_noted_once(self):
        recorder = Recorder(raises=speech.Timeout(30.0))
        voice, lines = self.voice(recorder)
        for _ in range(2):
            voice.say("BUT !")
        self.assertTrue(until(lambda: lines))
        time.sleep(0.05)
        self.assertEqual(len(lines), 1)
        self.assertIn("spd-say", lines[0])

    def test_a_launch_that_explodes_is_noted_once(self):
        recorder = Recorder(raises=OSError("permission refusee"))
        voice, lines = self.voice(recorder)
        for _ in range(2):
            voice.say("BUT !")
        self.assertTrue(until(lambda: lines))
        time.sleep(0.05)
        self.assertEqual(len(lines), 1)
        self.assertIn("permission refusee", lines[0])

    def test_a_failure_never_comes_back_to_the_caller(self):
        """say() ne leve pas, quoi qu'il arrive derriere : c'est tout le point."""
        for boom in (OSError("rien"), RuntimeError("rien"),
                     speech.Timeout(1.0)):
            recorder = Recorder(raises=boom)
            voice, _lines = self.voice(recorder)
            voice.say("BUT !")
            time.sleep(0.05)

    def test_the_voice_keeps_going_after_a_failure(self):
        """Demain il y aura un autre but, et peut-etre que ca remarchera."""
        recorder = Recorder(code=1)
        voice, lines = self.voice(recorder)
        voice.say("but 1")
        self.assertTrue(until(lambda: recorder.calls))
        recorder.code = 0
        voice.say("but 2")
        self.assertTrue(until(lambda: len(recorder.calls) == 2))
        self.assertEqual(recorder.spoken, ["but 1", "but 2"])
        self.assertEqual(len(lines), 1)

    def test_a_journal_that_explodes_does_not_stop_the_voice(self):
        def broken(_message):
            raise RuntimeError("plus de place sur le disque")

        recorder = Recorder(code=1)
        voice = voice_for(recorder, on_log=broken)
        self.addCleanup(voice.close, 2.0)
        voice.say("but 1")
        self.assertTrue(until(lambda: recorder.calls))
        voice.say("but 2")
        self.assertTrue(until(lambda: len(recorder.calls) == 2))


class TestClosing(unittest.TestCase):
    """Deux fermetures, parce que les deux appelants ne veulent pas la meme.

    Le daemon qu'on arrete n'a plus rien a raconter ; `--test --speak`, lui,
    n'a qu'une phrase a faire entendre et n'a pas d'autre moment pour ca.
    """

    def test_closing_stops_the_thread(self):
        recorder = Recorder()
        voice = voice_for(recorder)
        voice.say("BUT !")
        self.assertTrue(until(lambda: recorder.calls))
        voice.close(2.0)
        self.assertFalse(voice._thread.is_alive())

    def test_closing_with_a_delay_lets_what_is_waiting_be_said(self):
        hold = threading.Event()
        recorder = Recorder(hold=hold)
        voice = voice_for(recorder)
        voice.say("but 1")
        self.assertTrue(until(lambda: recorder.calls))
        voice.say("but 2")
        hold.set()
        voice.close(5.0)
        self.assertEqual(recorder.spoken, ["but 1", "but 2"])

    def test_closing_without_a_delay_drops_what_was_waiting(self):
        """A l'arret du daemon, le but d'il y a dix secondes n'interesse plus."""
        hold = threading.Event()
        recorder = Recorder(hold=hold)
        voice = voice_for(recorder)
        voice.say("but 1")
        self.assertTrue(until(lambda: recorder.calls))
        voice.say("but 2")
        voice.close()
        hold.set()
        time.sleep(0.05)
        self.assertEqual(recorder.spoken, ["but 1"])

    def test_a_closed_voice_takes_no_more_phrases(self):
        recorder = Recorder()
        voice = voice_for(recorder)
        voice.close(2.0)
        voice.say("trop tard")
        time.sleep(0.05)
        self.assertEqual(recorder.calls, [])

    def test_closing_a_voice_that_never_spoke_is_harmless(self):
        speech.Voice(False).close(1.0)
        speech.Voice(True, platform="linux", which=which_for()).close(1.0)


if __name__ == "__main__":
    unittest.main()
