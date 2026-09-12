"""Sortie audio native.

La CI n'a ni carte son ni serveur audio, et tourne aussi sous macOS et Windows.
Rien ici ne joue : ce qui est verifie, c'est la preparation des echantillons, le
choix de la sortie, la reprise bornee d'ALSA, et le fait qu'une bibliotheque
absente se solde par un repli et non par une erreur.
"""

from __future__ import annotations

import array
import struct
import tempfile
import unittest
import wave
from pathlib import Path
from unittest import mock

from butbutbut import audio, sound


def _write(path: Path, channels: int, frames: list) -> Path:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(2)
        handle.setframerate(44100)
        flat = [v for f in frames for v in (f if isinstance(f, tuple) else (f,))]
        handle.writeframes(struct.pack("<%dh" % len(flat), *flat))
    return path


class AudioTestCase(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.root = Path(self._dir.name)

    def samples(self, pcm):
        values = array.array("h")
        values.frombytes(pcm)
        return values


class TestSamplePreparation(AudioTestCase):
    """La ou doot applique un panoramique, on applique le volume."""

    def test_full_volume_returns_the_file_untouched(self):
        """A fond, recopier les octets un par un ne changerait que le temps."""
        path = _write(self.root / "m.wav", 1, [10000, -7777, 7, -9])
        pcm, rate, channels = audio._pcm(path, sound.MAX_VOLUME)
        self.assertEqual(rate, 44100)
        self.assertEqual(channels, 1)
        with wave.open(str(path), "rb") as handle:
            self.assertEqual(pcm, handle.readframes(handle.getnframes()))

    def test_the_gain_is_applied_to_every_sample(self):
        path = _write(self.root / "m.wav", 1, [10000, -8000, 400])
        pcm, _rate, _channels = audio._pcm(path, 25.0)
        self.assertEqual(list(self.samples(pcm)), [2500, -2000, 100])

    def test_the_gain_rounds_instead_of_truncating(self):
        """Tirer vers zero ajouterait un demi-bit de biais par echantillon.

        7 et -9 sont choisis pour que l'arrondi et la troncature different :
        sans eux le test passerait avec les deux implementations.
        """
        path = _write(self.root / "m.wav", 1, [7, -9])
        pcm, _rate, _channels = audio._pcm(path, 50.0)
        self.assertEqual(list(self.samples(pcm)), [4, -4],
                         "attendu round(3.5) et round(-4.5), pas int()")

    def test_stereo_keeps_its_two_channels(self):
        """Sans panoramique, monter un mono en stereo ne ferait que doubler les
        octets a ecrire : chaque fichier garde ses canaux."""
        path = _write(self.root / "s.wav", 2, [(20000, 4000)] * 4)
        pcm, _rate, channels = audio._pcm(path, 50.0)
        self.assertEqual(channels, 2)
        self.assertEqual(list(self.samples(pcm))[:2], [10000, 2000])

    def test_mono_stays_mono(self):
        path = _write(self.root / "m.wav", 1, [10000] * 8)
        pcm, _rate, channels = audio._pcm(path, 50.0)
        self.assertEqual(channels, 1)
        self.assertEqual(len(self.samples(pcm)), 8)

    def test_zero_volume_silences_without_failing(self):
        path = _write(self.root / "m.wav", 1, [30000, -30000])
        pcm, _rate, _channels = audio._pcm(path, 0.0)
        self.assertEqual(list(self.samples(pcm)), [0, 0])

    def test_an_unsupported_width_returns_none(self):
        path = self.root / "8bits.wav"
        with wave.open(str(path), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(1)
            handle.setframerate(44100)
            handle.writeframes(b"\x80" * 16)
        self.assertIsNone(audio._pcm(path, sound.MAX_VOLUME))

    def test_an_unreadable_file_returns_none(self):
        path = self.root / "pas-un-wav.wav"
        path.write_bytes(b"ceci n'est pas un wav")
        self.assertIsNone(audio._pcm(path, sound.MAX_VOLUME))


class _FakeAlsa:
    """Le juste necessaire de libasound pour eprouver la reprise."""

    def __init__(self, rendus):
        self.rendus = list(rendus)
        self.prepares = 0

    def snd_pcm_writei(self, _pcm, _bloc, trames):
        if not self.rendus:
            return trames
        rendu = self.rendus.pop(0)
        return trames if rendu == "tout" else rendu

    def snd_pcm_prepare(self, _pcm):
        self.prepares += 1


class TestAlsaRecovery(AudioTestCase):
    """La reprise bornee, portee telle quelle depuis doot.

    Un underrun perpetuel, ou un zero rendu en boucle, ferait tourner le fil de
    lecture a vide indefiniment. Ce chemin n'est eprouve nulle part en vrai : le
    greffon ALSA de PipeWire repond a la place d'un ALSA nu.
    """

    def sortie(self, rendus, channels=1):
        out = audio._SortieAlsa.__new__(audio._SortieAlsa)
        out.lib = _FakeAlsa(rendus)
        out.pcm = None
        out.canaux = channels
        return out

    def bloc(self, frames, channels=1):
        return b"\x00" * (frames * 2 * channels)

    def test_a_complete_write_succeeds(self):
        out = self.sortie(["tout"])
        self.assertTrue(out.write(self.bloc(64)))

    def test_partial_writes_are_resumed(self):
        out = self.sortie([10, 20, "tout"])
        self.assertTrue(out.write(self.bloc(64)))

    def test_an_underrun_prepares_and_resumes(self):
        out = self.sortie([-audio.EPIPE, "tout"])
        self.assertTrue(out.write(self.bloc(64)))
        self.assertEqual(out.lib.prepares, 1)

    def test_a_real_error_gives_up_at_once(self):
        out = self.sortie([-5])
        self.assertFalse(out.write(self.bloc(64)))
        self.assertEqual(out.lib.prepares, 0)

    def test_a_perpetual_underrun_is_bounded(self):
        """Mieux vaut un son coupe qu'un coeur brule en silence."""
        out = self.sortie([-audio.EPIPE] * 500)
        self.assertFalse(out.write(self.bloc(64)))
        self.assertLessEqual(out.lib.prepares, audio.REPRISES_MAX + 1)

    def test_a_stream_of_zeroes_is_bounded_too(self):
        """Zero trame rendue n'est pas une erreur, mais n'avance pas non plus."""
        out = self.sortie([0] * 500)
        self.assertFalse(out.write(self.bloc(64)))

    def test_progress_resets_the_budget(self):
        """Des underruns espaces par du progres ne doivent pas cumuler."""
        rendus = []
        for _ in range(6):
            rendus += [-audio.EPIPE] * 4 + [8]
        rendus.append("tout")
        out = self.sortie(rendus)
        self.assertTrue(out.write(self.bloc(200)))

    def test_the_frame_size_follows_the_channel_count(self):
        """Un bloc stereo compte deux fois moins de trames que d'echantillons."""
        vues = []
        out = self.sortie([])
        out.canaux = 2
        out.lib.snd_pcm_writei = lambda _p, _b, trames: vues.append(trames) or trames
        out.write(self.bloc(32, channels=2))
        self.assertEqual(vues, [32])


class TestBackendChoice(AudioTestCase):
    """Une bibliotheque absente se solde par un repli, jamais par une erreur."""

    def sans_bibliotheques(self):
        return mock.patch.object(audio, "_SORTIES", ())

    def test_no_library_means_not_available(self):
        with self.sans_bibliotheques():
            self.assertFalse(audio.available())
            self.assertIsNone(audio.backend())

    def test_play_returns_none_without_an_output(self):
        path = _write(self.root / "m.wav", 1, [1000] * 8)
        with self.sans_bibliotheques():
            self.assertIsNone(audio.play(path, sound.MAX_VOLUME))

    def test_the_first_usable_output_wins(self):
        premier = mock.Mock(nom="premier", **{"bibliotheque.return_value": object()})
        second = mock.Mock(nom="second", **{"bibliotheque.return_value": object()})
        with mock.patch.object(audio, "_SORTIES", (premier, second)):
            self.assertEqual(audio.backend(), "premier")
            audio._ouvre(44100, 1)
        premier.assert_called_once_with(44100, 1)
        second.assert_not_called()

    def test_an_output_that_refuses_hands_over_to_the_next(self):
        premier = mock.Mock(**{"bibliotheque.return_value": object(),
                               "side_effect": OSError("pa_simple_new a echoue")})
        ouvert = object()
        second = mock.Mock(**{"bibliotheque.return_value": object(),
                              "return_value": ouvert})
        with mock.patch.object(audio, "_SORTIES", (premier, second)):
            self.assertIs(audio._ouvre(44100, 1), ouvert)

    def test_play_opens_the_output_with_the_file_channels(self):
        """Un mono ouvert en stereo sortirait a la mauvaise vitesse."""
        for channels, frames in ((1, [1000] * 8), (2, [(1000, 2000)] * 8)):
            with self.subTest(channels=channels):
                path = _write(self.root / ("c%d.wav" % channels), channels, frames)
                vus = []
                sortie = mock.Mock(**{"write.return_value": True})

                def ouvre(rate, canaux):
                    vus.append((rate, canaux))
                    return sortie

                with mock.patch.object(audio, "available", lambda: True), \
                        mock.patch.object(audio, "_ouvre", ouvre):
                    lecture = audio.play(path, sound.MAX_VOLUME)
                self.assertIsNotNone(lecture)
                lecture.join(5)
                self.assertEqual(vus, [(44100, channels)])

    def test_a_library_that_is_missing_is_skipped(self):
        absente = mock.Mock(**{"bibliotheque.return_value": None})
        ouvert = object()
        presente = mock.Mock(**{"bibliotheque.return_value": object(),
                                "return_value": ouvert})
        with mock.patch.object(audio, "_SORTIES", (absente, presente)):
            self.assertIs(audio._ouvre(44100, 1), ouvert)
        absente.assert_not_called()


class _WatchedSet(set):
    """Un ensemble qui refuse d'etre parcouru sans le verrou.

    Une course ne se reproduit pas a la demande : plutot que de la provoquer,
    on rend deterministe la faute qui la permet.
    """

    def __iter__(self):
        if not audio._verrou.locked():
            raise AssertionError("_en_cours parcouru sans tenir _verrou")
        return super().__iter__()


class TestConcurrentAccess(AudioTestCase):
    """`verse` retire du set depuis son fil pendant qu'on le parcourt."""

    def test_the_exit_wait_takes_the_lock_before_copying(self):
        lecture = mock.Mock()
        with mock.patch.object(audio, "_en_cours", _WatchedSet({lecture})):
            audio._laisse_finir(0.01)
        lecture.join.assert_called_once_with(0.01)

    def test_stop_all_takes_it_too(self):
        lecture = mock.Mock()
        with mock.patch.object(audio, "_en_cours", _WatchedSet({lecture})):
            audio.stop_all()
        lecture.stop.assert_called_once()

    def test_the_joins_happen_outside_the_lock(self):
        """Tenu pendant les join, le verrou bloquerait la lecture qui se
        termine sur son propre discard."""
        vu = []
        lecture = mock.Mock()
        lecture.join.side_effect = lambda _d: vu.append(audio._verrou.locked())
        with mock.patch.object(audio, "_en_cours", _WatchedSet({lecture})):
            audio._laisse_finir(0.01)
        self.assertEqual(vu, [False], "le verrou est encore tenu pendant le join")


class TestSoundPrefersTheNativeOutput(AudioTestCase):
    """Le cablage dans sound.play_async.

    La sortie native ne sert que la ou la stdlib ne joue rien. Windows garde
    winsound et MCI, qui sont integres, et sa branche rend avant d'arriver ici :
    ces tests declarent donc la plateforme dont ils parlent, au lieu de la
    supposer. Sans ca ils passaient sur Linux et tombaient sur la CI Windows.
    """

    def linux(self):
        return mock.patch.object(sound.sys, "platform", "linux")

    def test_a_wav_goes_native_when_it_answers(self):
        path = _write(self.root / "m.wav", 1, [1000] * 8)
        lecture = object()
        with self.linux(), \
                mock.patch.object(audio, "play", return_value=lecture) as native, \
                mock.patch.object(sound, "find_player") as externe:
            self.assertIs(sound.play_async(path, 60.0), lecture)
        native.assert_called_once()
        externe.assert_not_called()

    def test_windows_keeps_its_builtin_playback(self):
        """winsound et MCI sont dans la stdlib : rien a charger en ctypes."""
        path = _write(self.root / "m.wav", 1, [1000] * 8)
        with mock.patch.object(sound.sys, "platform", "win32"), \
                mock.patch.object(audio, "play") as native, \
                mock.patch.dict("sys.modules", {"winsound": mock.Mock()}):
            sound.play_async(path, sound.MAX_VOLUME)
        native.assert_not_called()

    def test_a_compressed_file_keeps_the_external_player(self):
        """Aucun decodeur mp3 dans la bibliotheque standard."""
        path = self.root / "but.mp3"
        path.write_bytes(b"\x00")
        with self.linux(), mock.patch.object(audio, "play") as native, \
                mock.patch.object(sound, "find_player", return_value=None):
            sound.play_async(path, 60.0)
        native.assert_not_called()

    def test_a_refused_wav_falls_back_to_the_player(self):
        """Rendre None n'est pas une erreur : c'est le repli attendu."""
        path = _write(self.root / "m.wav", 1, [1000] * 8)
        with self.linux(), mock.patch.object(audio, "play", return_value=None), \
                mock.patch.object(sound, "find_player", return_value=None) as externe:
            self.assertIsNone(sound.play_async(path, 60.0))
        externe.assert_called_once()

    def test_a_muted_volume_launches_nothing_at_all(self):
        path = _write(self.root / "m.wav", 1, [1000] * 8)
        with self.linux(), mock.patch.object(audio, "play") as native:
            self.assertIsNone(sound.play_async(path, sound.MUTE))
        native.assert_not_called()

    def test_plays_natively_only_for_wav(self):
        with mock.patch.object(sound, "native_backend", return_value="PulseAudio"):
            self.assertTrue(sound.plays_natively(Path("x.wav")))
            self.assertTrue(sound.plays_natively(Path("X.WAV")))
            self.assertFalse(sound.plays_natively(Path("x.mp3")))

    def test_plays_natively_is_false_without_a_backend(self):
        with mock.patch.object(sound, "native_backend", return_value=None):
            self.assertFalse(sound.plays_natively(Path("x.wav")))

    def test_stop_all_cuts_the_native_playbacks(self):
        with mock.patch.object(audio, "stop_all") as coupe:
            sound.stop_all()
        coupe.assert_called_once()


if __name__ == "__main__":
    unittest.main()
