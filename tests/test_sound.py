import sys
import unittest
from unittest import mock
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
            path = sound.write_wav(Path(tmp) / "horn.wav", level=0.4)
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


class TestParseAssignments(unittest.TestCase):
    """La lecture de --sound-for, partagee avec le fichier de configuration."""

    def test_a_pair_gives_a_word_and_a_path(self):
        [one] = sound.parse_assignments("om=cri.wav")
        self.assertEqual(one.token, "om")
        self.assertEqual(one.path, Path("cri.wav"))

    def test_several_pairs_at_once(self):
        found = sound.parse_assignments("om=cri.wav,ucl=corne.mp3")
        self.assertEqual([one.token for one in found], ["om", "ucl"])

    def test_a_line_break_separates_too(self):
        # C'est ainsi qu'une valeur du fichier de configuration s'ecrit sur
        # plusieurs lignes.
        found = sound.parse_assignments("om=cri.wav\nucl=corne.mp3")
        self.assertEqual([one.token for one in found], ["om", "ucl"])

    def test_a_comma_inside_a_path_is_not_a_separator(self):
        # Rien n'interdit la virgule dans un nom de dossier : elle ne coupe
        # que devant une nouvelle paire.
        found = sound.parse_assignments("om=sons, vol. 2/om.wav;ucl=corne.mp3")
        self.assertEqual([(one.token, one.path.name) for one in found],
                         [("om", "om.wav"), ("ucl", "corne.mp3")])
        self.assertIn("sons, vol. 2", str(found[0].path))

    def test_spaces_and_a_trailing_comma_are_forgiven(self):
        found = sound.parse_assignments("  om = cri.wav ,  ")
        self.assertEqual([(one.token, one.path.name) for one in found],
                         [("om", "cri.wav")])

    def test_nothing_at_all_is_not_an_error(self):
        self.assertEqual(sound.parse_assignments(None), [])
        self.assertEqual(sound.parse_assignments(""), [])
        self.assertEqual(sound.parse_assignments("  ,  "), [])

    def test_a_word_without_its_path_is_refused_by_name(self):
        with self.assertRaises(sound.Invalid) as caught:
            sound.parse_assignments("om")
        self.assertIn("om", str(caught.exception))

    def test_a_path_without_its_word_is_refused_too(self):
        with self.assertRaises(sound.Invalid):
            sound.parse_assignments("=cri.wav")

    def test_the_home_shortcut_is_expanded(self):
        # Personne ne developpe le `~` du fichier de configuration : le shell
        # n'est pas passe par la.
        [one] = sound.parse_assignments("om=~/sons/om.wav")
        self.assertNotIn("~", str(one.path))
        self.assertTrue(str(one.path).endswith("om.wav"))


class TestUnusable(unittest.TestCase):
    """Ce qu'un chemin fautif rend : une phrase, pas un booleen."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)

    def test_a_readable_sound_says_nothing(self):
        path = self.folder / "cri.wav"
        path.write_bytes(b"x")
        self.assertIsNone(sound.unusable(path))

    def test_a_missing_file_is_named_as_such(self):
        self.assertIn("introuvable", sound.unusable(self.folder / "nulle.wav"))

    def test_a_folder_is_not_a_sound(self):
        self.assertIn("dossier", sound.unusable(self.folder))

    def test_a_format_nobody_can_play_is_refused(self):
        path = self.folder / "cri.txt"
        path.write_bytes(b"x")
        self.assertIn("format", sound.unusable(path))

    def test_check_assignments_names_every_faulty_pair(self):
        good = self.folder / "cri.wav"
        good.write_bytes(b"x")
        problems = sound.check_assignments([
            sound.Assignment("om", good),
            sound.Assignment("psg", self.folder / "nulle.wav"),
            sound.Assignment("ucl", self.folder / "note.txt"),
        ])
        self.assertEqual(len(problems), 2)
        self.assertIn("psg", problems[0])
        self.assertIn("ucl", problems[1])

    def test_all_is_well_gives_an_empty_list(self):
        path = self.folder / "cri.wav"
        path.write_bytes(b"x")
        self.assertEqual(sound.check_assignments(
            [sound.Assignment("om", path)]), [])


class TestNamedSoundsAreArmed(unittest.TestCase):
    """Un son nomme joue aux memes etages qu'un nom de fichier, et les couvre."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)

    def pair(self, token, name):
        """Une paire dont le fichier existe pour de bon."""
        path = self.folder / name
        path.write_bytes(b"x")
        return sound.Assignment(token, path)

    def armed(self, pool, context, assigned, on_missing=None):
        return names(sound.armed_sounds(pool, context, assigned, on_missing))

    def test_a_named_team_plays_only_when_it_scores(self):
        cri = [self.pair("om", "cri.wav")]
        self.assertEqual(self.armed(files("corne.mp3"), scoring(), cri),
                         ["cri.wav"])
        self.assertEqual(
            self.armed(files("corne.mp3"), scoring(marseille=False), cri),
            ["corne.mp3"])

    def test_a_full_name_names_the_team_too(self):
        self.assertEqual(
            self.armed([], scoring(), [self.pair("marseille", "cri.wav")]),
            ["cri.wav"])

    def test_a_named_league_plays_for_that_league_only(self):
        corne = [self.pair("l1", "corne.wav")]
        self.assertEqual(self.armed([], scoring(), corne), ["corne.wav"])
        other = scoring(league=leagues.BY_SLUG["eng.1"])
        self.assertEqual(self.armed([], other, corne), [])

    def test_the_team_beats_its_own_competition(self):
        # L'arbitrage documente : le plus precis gagne.
        both = [self.pair("l1", "corne.wav"), self.pair("om", "cri.wav")]
        self.assertEqual(self.armed([], scoring(), both), ["cri.wav"])
        # Un but de Paris dans la meme competition : l'etage equipe est vide,
        # celui de la competition prend la main.
        self.assertEqual(self.armed([], scoring(marseille=False), both),
                         ["corne.wav"])

    def test_what_is_named_covers_what_was_guessed_at_the_same_tier(self):
        pool = files("om.mp3", "corne.mp3")
        self.assertEqual(self.armed(pool, scoring(), [self.pair("om", "cri.wav")]),
                         ["cri.wav"])

    def test_a_named_sound_never_becomes_background_noise(self):
        # `psg` ne joue pas dans ce but-la : son cri se tait, et le fond
        # sonore du dossier reste ce qu'il etait.
        pool = files("corne.mp3")
        self.assertEqual(
            self.armed(pool, scoring(), [self.pair("psg", "cri.wav")]),
            ["corne.mp3"])

    def test_the_team_that_concedes_stays_quiet(self):
        self.assertEqual(
            self.armed([], scoring(), [self.pair("psg", "cri.wav")]), [])

    def test_the_conceded_word_works_when_named(self):
        aie = [self.pair("contre", "aie.wav")]
        self.assertEqual(self.armed([], scoring(conceded=True), aie),
                         ["aie.wav"])
        self.assertEqual(self.armed([], scoring(), aie), [])

    def test_two_sounds_for_the_same_word_are_both_drawn(self):
        both = [self.pair("om", "cri-1.wav"), self.pair("om", "cri-2.wav")]
        self.assertEqual(sorted(self.armed([], scoring(), both)),
                         ["cri-1.wav", "cri-2.wav"])

    def test_without_a_goal_nothing_named_comes_out(self):
        # --test et les cartes muettes : rien a comparer, tirage d'avant.
        pool = files("corne.mp3")
        self.assertEqual(self.armed(pool, None, [self.pair("om", "cri.wav")]),
                         ["corne.mp3"])

    def test_every_tier_is_reachable_by_a_named_sound(self):
        ranked = sound.named_by_tier(
            [self.pair("om", "cri.wav"), self.pair("contre", "aie.wav"),
             self.pair("l1", "corne.wav"), self.pair("psg", "eux.wav")],
            scoring(conceded=True))
        self.assertEqual(names(ranked[sound.TIER_TEAM]), ["cri.wav"])
        self.assertEqual(names(ranked[sound.TIER_CONCEDED]), ["aie.wav"])
        self.assertEqual(names(ranked[sound.TIER_LEAGUE]), ["corne.wav"])
        # Il n'y a pas d'etage general pour un son nomme, et l'equipe qui
        # encaisse n'arme rien du tout.
        self.assertEqual(ranked[sound.TIER_GENERAL], [])


class TestNamedSoundThatVanishes(unittest.TestCase):
    """La cle USB debranchee : on degrade, on note, on ne se tait pas."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.noted = []

    def note(self, assignment, problem):
        self.noted.append((assignment.token, problem))

    def gone(self, token="om", name="cri.wav"):
        return sound.Assignment(token, self.folder / name)

    def test_the_folder_takes_over_and_the_loss_is_noted(self):
        chosen = sound.armed_sounds(files("om.mp3"), scoring(), [self.gone()],
                                    self.note)
        self.assertEqual(names(chosen), ["om.mp3"])
        self.assertEqual(self.noted[0][0], "om")
        self.assertIn("introuvable", self.noted[0][1])

    def test_an_empty_tier_hands_over_like_any_other(self):
        chosen = sound.armed_sounds(files("corne.mp3"), scoring(),
                                    [self.gone()], self.note)
        self.assertEqual(names(chosen), ["corne.mp3"])

    def test_a_sound_named_for_someone_else_is_never_looked_for(self):
        # Un cri nomme pour une equipe qui ne joue pas ce soir n'a pas a etre
        # cherche sur le disque, ni a remplir le journal a chaque but.
        sound.armed_sounds(files("corne.mp3"), scoring(),
                           [self.gone("lens")], self.note)
        self.assertEqual(self.noted, [])

    def test_pick_sound_falls_back_all_the_way_down(self):
        empty = self.folder / "sound"
        empty.mkdir()
        chosen = sound.pick_sound(self.folder / "but.wav", empty,
                                  context=scoring(), assigned=[self.gone()],
                                  on_missing=self.note)
        self.assertNotEqual(chosen.name, "cri.wav")
        self.assertTrue(chosen.is_file())
        self.assertEqual(len(self.noted), 1)

    def test_pick_sound_plays_the_named_one_while_it_is_there(self):
        empty = self.folder / "sound"
        empty.mkdir()
        cri = self.folder / "cri.wav"
        cri.write_bytes(b"x")
        chosen = sound.pick_sound(self.folder / "but.wav", empty,
                                  context=scoring(),
                                  assigned=[sound.Assignment("om", cri)])
        self.assertEqual(chosen, cri)
        self.assertEqual(self.noted, [])


class TestReadVolume(unittest.TestCase):
    """L'echelle est 0 a 100, et l'ancienne doit continuer a vouloir dire ca."""

    def test_the_scale_runs_to_a_hundred(self):
        self.assertEqual(sound.read_volume("0"), 0)
        self.assertEqual(sound.read_volume("70"), 70)
        self.assertEqual(sound.read_volume(100), 100)

    def test_the_old_scale_is_still_understood(self):
        # Des fichiers de configuration ecrits il y a des mois portent ces
        # valeurs-la : les relire de travers ferait sursauter au premier but.
        self.assertEqual(sound.read_volume("0.55"), 55)
        self.assertEqual(sound.read_volume("1"), 100)

    def test_a_percent_sign_settles_the_doubt(self):
        # La seule facon d'ecrire un pour cent, puisque 1 tout court appartient
        # a l'ancienne echelle.
        self.assertEqual(sound.read_volume("1%"), 1)
        self.assertEqual(sound.read_volume("50 %"), 50)

    def test_a_decimal_comma_is_accepted(self):
        self.assertEqual(sound.read_volume(",5"), 50)

    def test_what_is_not_a_volume_says_so(self):
        for wrong in ("", "fort", "-1", "101", "nan", "inf", True):
            with self.assertRaises(sound.Invalid, msg=repr(wrong)):
                sound.read_volume(wrong)

    def test_the_complaint_names_the_scale(self):
        with self.assertRaises(sound.Invalid) as caught:
            sound.read_volume("200")
        self.assertIn("100", str(caught.exception))
        self.assertIn("200", str(caught.exception))


class TestVolumeAtPlayback(unittest.TestCase):
    """Le volume se regle a la lecture : c'est ce qui le fait valoir partout."""

    def players(self, *available):
        """shutil.which qui ne connait que ces binaires-la."""
        return lambda binary: "/usr/bin/" + binary if binary in available else None

    def linux(self, *available):
        return mock.patch.multiple(
            sound, sys=mock.Mock(platform="linux"),
            shutil=mock.Mock(which=self.players(*available)))

    def test_full_volume_leaves_the_command_untouched(self):
        # Une option de reglage est un pari sur la version installee du
        # lecteur. Personne ne doit le prendre pour rien.
        with self.linux("mpv"):
            self.assertEqual(sound.find_player(Path("but.mp3")),
                             list(sound.LINUX_PLAYERS[0][1]))

    def test_each_player_gets_its_own_dialect(self):
        for binary, expected in (("mpv", "--volume=50"),
                                 ("ffplay", "50"),
                                 ("play", "0.5"),
                                 ("cvlc", "0.5"),
                                 ("paplay", "--volume=32768")):
            with self.linux(binary):
                name = "but.mp3" if binary != "paplay" else "but.wav"
                command = sound.find_player(Path(name), 50)
                self.assertEqual(command[0], binary)
                self.assertIn(expected, command, binary)

    def test_a_player_without_a_knob_still_plays(self):
        # aplay n'a pas de reglage. Un but fort vaut mieux qu'un but perdu
        # parce qu'on lui aurait invente une option.
        with self.linux("aplay"):
            command = sound.find_player(Path("but.wav"), 10)
            self.assertEqual(command, list(sound.LINUX_PLAYERS[-1][1]))
            self.assertFalse(sound.tunable(command))

    def test_status_can_tell_who_knows_how(self):
        self.assertTrue(sound.tunable(["mpv", "--really-quiet"]))
        self.assertTrue(sound.tunable(["afplay"]))
        self.assertFalse(sound.tunable(["aplay", "-q"]))
        self.assertFalse(sound.tunable(None))

    def test_zero_plays_nothing_at_all(self):
        # Le contrat de --volume 0 : pas un lecteur lance pour rien.
        with mock.patch.object(sound, "find_player") as finder:
            self.assertIsNone(sound.play_async(sound.BUNDLED_SOUND, 0))
            finder.assert_not_called()


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
