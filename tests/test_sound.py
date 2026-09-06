import sys
import unittest
import wave
from pathlib import Path
from tempfile import TemporaryDirectory

from butbutbut import sound


class TestSelection(unittest.TestCase):
    def test_custom_sounds_are_filtered_and_sorted(self):
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            for name in ("b.mp3", "a.wav", "notes.txt"):
                (folder / name).write_bytes(b"x")
            self.assertEqual([p.name for p in sound.custom_sounds(folder)],
                             ["a.wav", "b.mp3"])

    def test_missing_folder_gives_no_custom_sound(self):
        self.assertEqual(sound.custom_sounds(Path("nulle-part-du-tout")), [])

    def test_custom_sound_wins_over_the_bundled_one(self):
        with TemporaryDirectory() as tmp:
            folder = Path(tmp) / "sound"
            folder.mkdir()
            mine = folder / "corne.mp3"
            mine.write_bytes(b"x")
            chosen = sound.pick_sound(Path(tmp) / "but.wav", folder)
            self.assertEqual(chosen, mine)

    def test_bundled_sound_ships_with_the_package(self):
        self.assertIsNotNone(sound.bundled_sound())
        self.assertGreater(sound.BUNDLED_SOUND.stat().st_size, 1000)

    def test_fallback_is_a_playable_wav(self):
        with TemporaryDirectory() as tmp:
            path = sound.write_wav(Path(tmp) / "horn.wav", volume=0.4)
            with wave.open(str(path), "rb") as handle:
                self.assertEqual(handle.getnchannels(), 1)
                self.assertEqual(handle.getsampwidth(), 2)
                self.assertEqual(handle.getframerate(), sound.SAMPLE_RATE)
                self.assertGreater(handle.getnframes(), 0)
            self.assertAlmostEqual(sound.probe_duration(path),
                                   sound.TOTAL_SECONDS, places=1)

    def test_ensure_wav_only_writes_once(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "horn.wav"
            sound.ensure_wav(path, 0.4)
            stamp = path.stat().st_mtime_ns
            sound.ensure_wav(path, 0.4)
            self.assertEqual(path.stat().st_mtime_ns, stamp)
            sound.ensure_wav(path, 0.4, force=True)


class TestPlayers(unittest.TestCase):
    def test_windows_needs_no_external_player(self):
        if sys.platform != "win32":
            self.skipTest("Windows uniquement")
        self.assertIsNone(sound.find_player(Path("a.mp3")))

    def test_a_missing_file_never_raises(self):
        # Le contrat de play_async : ne jamais lever, quoi qu'on lui donne. Un
        # but ne doit pas faire tomber le daemon parce qu'un son a disparu.
        # Selon la plateforme il rend un handle (le lecteur externe echouera de
        # son cote, sans bruit) ou None si aucun lecteur n'est disponible.
        handle = sound.play_async(Path("nulle-part-du-tout.mp3"))
        sound.release(handle)

    def test_release_and_stop_are_safe_to_call(self):
        sound.release(None)
        sound.release("mci")
        sound.stop_all()

    def test_probe_duration_of_garbage_is_none(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "faux.wav"
            path.write_bytes(b"pas du son")
            self.assertIsNone(sound.probe_duration(path))


if __name__ == "__main__":
    unittest.main()
