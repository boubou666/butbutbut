import sys
import unittest
import wave
from pathlib import Path
from tempfile import TemporaryDirectory

from butbutbut import leagues, sound

MARSEILLE = ("Marseille", "Marseille", "OLM")
PARIS = ("Paris Saint-Germain", "Paris SG", "PSG")
L1 = leagues.BY_SLUG["fra.1"]


def files(*names) -> list:
    """Des chemins de sons, sans rien ecrire sur le disque.

    Le classement ne regarde que le nom : un test qui ecrirait de vrais
    fichiers ne prouverait rien de plus et serait plus lent.
    """
    return [Path("/sound") / name for name in names]


def names(paths) -> list:
    return [path.name for path in paths]


def scoring(marseille=True, conceded=False, clubs=(), league=L1):
    """Un contexte de but : Marseille - Paris, l'un ou l'autre marque."""
    scorer, beaten = (MARSEILLE, PARIS) if marseille else (PARIS, MARSEILLE)
    return sound.Context(league=league, scorer_names=scorer,
                         beaten_names=beaten, conceded=conceded, clubs=clubs)


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


class TestNameCandidates(unittest.TestCase):
    def test_the_whole_name_comes_first(self):
        self.assertEqual(sound.name_candidates("om.mp3")[0], "om")
        self.assertEqual(sound.name_candidates("fra.1.mp3")[0], "fra.1")

    def test_a_variant_suffix_is_trimmed(self):
        self.assertIn("om", sound.name_candidates("om-2.mp3"))
        self.assertIn("om", sound.name_candidates("om_2.wav"))
        self.assertIn("om", sound.name_candidates("om 2.ogg"))
        self.assertIn("fra.1", sound.name_candidates("fra.1-b.mp3"))

    def test_a_long_name_is_tried_whole_before_being_cut(self):
        # Sinon "saint-etienne" ne designerait plus que "saint".
        self.assertEqual(sound.name_candidates("saint-etienne.mp3")[0],
                         "saint-etienne")


class TestArmedSounds(unittest.TestCase):
    """Le choix du fichier : fonction pure, aucun son n'est joue ici."""

    def test_without_context_the_whole_folder_is_candidate(self):
        pool = files("om.mp3", "l1.mp3", "corne.mp3")
        self.assertEqual(sound.armed_sounds(pool), pool)

    def test_the_team_that_scores_wins_every_other_tier(self):
        pool = files("om.mp3", "contre.mp3", "l1.mp3", "corne.mp3")
        chosen = sound.armed_sounds(pool, scoring(conceded=True))
        self.assertEqual(names(chosen), ["om.mp3"])

    def test_full_name_and_abbreviation_designate_the_team_too(self):
        for name in ("marseille.mp3", "olm.mp3", "Marseille.MP3"):
            chosen = sound.armed_sounds(files(name, "corne.mp3"), scoring())
            self.assertEqual(names(chosen), [name], name)

    def test_a_followed_team_conceding_gets_its_own_sound(self):
        pool = files("contre.mp3", "l1.mp3", "corne.mp3")
        chosen = sound.armed_sounds(pool, scoring(marseille=False, conceded=True))
        self.assertEqual(names(chosen), ["contre.mp3"])

    def test_the_same_folder_sounds_different_on_both_sides(self):
        # C'est tout l'interet : entendre la difference entre "on a marque" et
        # "on a pris" sans regarder l'ecran.
        pool = files("om.mp3", "contre.mp3")
        self.assertEqual(names(sound.armed_sounds(pool, scoring(conceded=True))),
                         ["om.mp3"])
        self.assertEqual(
            names(sound.armed_sounds(pool, scoring(marseille=False, conceded=True))),
            ["contre.mp3"])

    def test_conceded_stays_silent_without_a_followed_team(self):
        # Sans --teams personne n'encaisse "chez nous" : le mot ne s'arme pas.
        pool = files("contre.mp3", "corne.mp3")
        chosen = sound.armed_sounds(pool, scoring(marseille=False))
        self.assertEqual(names(chosen), ["corne.mp3"])

    def test_every_written_form_of_the_conceded_word_is_accepted(self):
        for name in ("contre.mp3", "encaisse.mp3", "against.mp3", "conceded.mp3"):
            chosen = sound.armed_sounds(files(name, "corne.mp3"),
                                        scoring(conceded=True))
            self.assertEqual(names(chosen), [name], name)

    def test_the_league_is_named_by_its_code_or_any_alias(self):
        for name in ("fra.1.mp3", "l1.mp3", "ligue1.mp3", "france.wav"):
            chosen = sound.armed_sounds(files(name, "corne.mp3"), scoring())
            self.assertEqual(names(chosen), [name], name)

    def test_another_league_never_plays_and_never_joins_the_draw(self):
        pool = files("pl.mp3", "seriea.mp3", "corne.mp3")
        chosen = sound.armed_sounds(pool, scoring())
        self.assertEqual(names(chosen), ["corne.mp3"])

    def test_the_team_that_concedes_stays_quiet(self):
        # psg.mp3 dit "quand le PSG marque", pas "quand il prend un but".
        pool = files("psg.mp3", "corne.mp3")
        chosen = sound.armed_sounds(pool, scoring())
        self.assertEqual(names(chosen), ["corne.mp3"])

    def test_a_club_from_elsewhere_is_not_background_noise(self):
        # barca est un surnom connu : le fichier vise Barcelone, il n'a rien a
        # faire dans le tirage general d'un Marseille - Paris.
        pool = files("barca.mp3", "corne.mp3")
        chosen = sound.armed_sounds(pool, scoring())
        self.assertEqual(names(chosen), ["corne.mp3"])

    def test_a_club_named_to_teams_is_known_even_when_it_does_not_play(self):
        pool = files("angers.mp3", "corne.mp3")
        self.assertEqual(names(sound.armed_sounds(pool, scoring())),
                         ["angers.mp3", "corne.mp3"])
        chosen = sound.armed_sounds(pool, scoring(clubs=["angers"]))
        self.assertEqual(names(chosen), ["corne.mp3"])

    def test_an_empty_tier_hands_over_to_the_next_one(self):
        pool = files("contre.mp3", "l1.mp3", "corne.mp3")
        # Personne n'encaisse chez nous : l'etage "contre" est vide, la
        # competition prend la main.
        self.assertEqual(names(sound.armed_sounds(pool, scoring())), ["l1.mp3"])

    def test_several_files_of_one_tier_are_all_candidates(self):
        pool = files("om-1.mp3", "om-2.mp3", "om.mp3", "corne.mp3")
        chosen = sound.armed_sounds(pool, scoring())
        self.assertEqual(names(chosen), ["om-1.mp3", "om-2.mp3", "om.mp3"])

    def test_a_folder_that_says_nothing_about_this_goal_is_empty(self):
        # Rien d'arme : pick_sound() retombera sur le son fourni.
        pool = files("pl.mp3", "barca.mp3")
        self.assertEqual(sound.armed_sounds(pool, scoring()), [])

    def test_every_tier_is_reachable(self):
        pool = files("om.mp3", "contre.mp3", "l1.mp3", "corne.mp3")
        ranked = sound.sounds_by_tier(pool, scoring(conceded=True))
        self.assertEqual(names(ranked[sound.TIER_TEAM]), ["om.mp3"])
        self.assertEqual(names(ranked[sound.TIER_CONCEDED]), ["contre.mp3"])
        self.assertEqual(names(ranked[sound.TIER_LEAGUE]), ["l1.mp3"])
        self.assertEqual(names(ranked[sound.TIER_GENERAL]), ["corne.mp3"])

    def test_the_order_of_the_tiers_is_the_documented_one(self):
        self.assertEqual(sound.TIERS, (sound.TIER_TEAM, sound.TIER_CONCEDED,
                                       sound.TIER_LEAGUE, sound.TIER_GENERAL))


class TestDeclared(unittest.TestCase):
    """Ce que --status annonce, sans match sous la main."""

    def test_each_recognised_name_gives_its_tier(self):
        self.assertEqual(sound.declared("contre.mp3")[0], sound.TIER_CONCEDED)
        self.assertEqual(sound.declared("corne.mp3")[0], sound.TIER_GENERAL)
        tier, target = sound.declared("l1.mp3")
        self.assertEqual((tier, target.slug), (sound.TIER_LEAGUE, "fra.1"))

    def test_a_nickname_is_read_as_a_team(self):
        self.assertEqual(sound.declared("om-2.mp3")[0], sound.TIER_TEAM)
        self.assertEqual(sound.declared("psg.mp3", clubs=["psg"])[0],
                         sound.TIER_TEAM)

    def test_an_unknown_club_looks_generic_until_it_scores(self):
        # La limite assumee : sans catalogue d'equipes hors ligne, --status ne
        # peut pas deviner qu'"angers" est un club.
        self.assertEqual(sound.declared("angers.mp3")[0], sound.TIER_GENERAL)


class TestPickWithContext(unittest.TestCase):
    def test_the_context_narrows_what_pick_sound_draws_from(self):
        with TemporaryDirectory() as tmp:
            folder = Path(tmp) / "sound"
            folder.mkdir()
            for name in ("om.mp3", "corne.mp3"):
                (folder / name).write_bytes(b"x")
            chosen = sound.pick_sound(Path(tmp) / "but.wav", folder,
                                      context=scoring())
            self.assertEqual(chosen.name, "om.mp3")

    def test_nothing_armed_falls_back_to_the_bundled_sound(self):
        with TemporaryDirectory() as tmp:
            folder = Path(tmp) / "sound"
            folder.mkdir()
            (folder / "pl.mp3").write_bytes(b"x")
            chosen = sound.pick_sound(Path(tmp) / "but.wav", folder,
                                      context=scoring())
            self.assertNotEqual(chosen.name, "pl.mp3")


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
