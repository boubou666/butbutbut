"""Enregistrer un match, et le rejouer.

Ce qui est verifie ici, dans l'ordre : le format ecrit puis relu, ce qu'une
ligne tronquee devient, le respect des ecarts de temps (temps accelere, aucune
attente reelle) et - le test qui justifie tout le reste - le fait qu'un rejeu
rende exactement la meme suite d'evenements que le direct qu'il rejoue.
"""

import io
import json
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from butbutbut import (cli, espn, i18n, leagues, pinned, replay, sports,
                       state, watcher)

from helpers import FakeClock, event, goal_detail, payload, red_card_detail

LIGUE1 = leagues.BY_SLUG["fra.1"]
URL = espn.SCOREBOARD_URL.format(sport=sports.DEFAULT.code, slug="fra.1")


def setUpModule():
    # Le journal est toujours en francais, mais quelques assertions lisent des
    # titres de carte : on epingle la langue, comme les autres modules.
    i18n.use("fr")


def script():
    """Un match entier, releve par releve : ce qu'aurait servi la source.

    Coup d'envoi, but, expulsion, mi-temps, reprise, second but, but retire par
    la VAR, fin du match. C'est exactement l'enchainement qu'on ne peut pas
    fabriquer avec --test.
    """
    opener = goal_detail("H1", "12'", "B. Saka", index=1)
    card = red_card_detail("A1", "37'", "M. Caicedo", index=2)
    equalizer = goal_detail("A1", "58'", "A. Kalimuendo", index=3)

    def snapshot(home, away, state, status, clock, details):
        return payload(event(home_score=home, away_score=away, state=state,
                             status_name=status, clock=clock, detail=clock,
                             details=details))

    return [
        snapshot(0, 0, "pre", "STATUS_SCHEDULED", "", ()),
        snapshot(0, 0, "in", "STATUS_FIRST_HALF", "3'", ()),
        snapshot(1, 0, "in", "STATUS_FIRST_HALF", "12'", (opener,)),
        snapshot(1, 0, "in", "STATUS_FIRST_HALF", "37'", (opener, card)),
        snapshot(1, 0, "in", "STATUS_HALFTIME", "45'", (opener, card)),
        snapshot(1, 0, "in", "STATUS_SECOND_HALF", "47'", (opener, card)),
        snapshot(1, 1, "in", "STATUS_SECOND_HALF", "58'",
                 (opener, card, equalizer)),
        # La VAR reprend le but : le score redescend, la source retire l'action.
        snapshot(1, 0, "in", "STATUS_SECOND_HALF", "60'", (opener, card)),
        snapshot(1, 0, "post", "STATUS_FULL_TIME", "FT", (opener, card)),
    ]


def record_a_match(path, steps=None, step=25.0, dedupe=True):
    """Joue un match en direct en l'enregistrant. Rend (evenements, recorder).

    Le direct passe par un vrai Watcher, avec le Recorder pose sur son opener
    exactement comme le fait `butbutbut --record`.
    """
    steps = script() if steps is None else steps
    source = {"payload": steps[0]}
    clock = FakeClock()

    def opener(_url, _timeout):
        return json.dumps(source["payload"]).encode("utf-8")

    recorder = replay.Recorder(path, opener=opener, clock=clock,
                               leagues=[LIGUE1], dedupe=dedupe).start()
    guard = watcher.Watcher([LIGUE1], opener=recorder.opener,
                            monotonic=clock, clock=clock, red_cards=True)
    guard.prime(pause=0.0, now=clock())

    events = []
    for payload_ in steps[1:]:
        source["payload"] = payload_
        clock.jump(step)
        events.extend(guard.refresh(LIGUE1, now=clock()))
    recorder.close()
    return events, recorder


def replay_a_match(path, speed=1000.0, sleeper=None, interval=25.0,
                   idle_interval=300.0):
    """Rejoue un fichier par la boucle du daemon. Rend (evenements, pace).

    La boucle est celle de cli._watch_headless(), reduite a ce qui compte :
    tick(), plan_wait(), puis l'attente. C'est ce trio qu'un rejeu doit
    traverser pour prouver quelque chose.
    """
    recording = replay.Recording.load(path)
    player = replay.Player(recording)
    pace = replay.Pace(player, speed=speed,
                       sleeper=sleeper or (lambda _seconds: None))
    guard = watcher.Watcher(recording.leagues(), interval=interval,
                            idle_interval=idle_interval, opener=player.opener,
                            monotonic=player.monotonic, clock=player.wall,
                            red_cards=True)
    guard.prime(pause=0.0, now=player.monotonic())

    events = []
    for _ in range(10000):          # garde-fou : un rejeu ne boucle jamais
        if pace.is_set():
            break
        events.extend(guard.tick())
        pace.wait(guard.plan_wait())
    else:
        raise AssertionError("le rejeu ne s'arrete pas")
    return events, pace, player


class Sandbox(unittest.TestCase):
    """Un dossier temporaire, et le chemin d'un enregistrement dedans."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.path = self.dir / "match.jsonl"

    def lines(self, path=None):
        text = (path or self.path).read_text(encoding="utf-8")
        return [json.loads(line) for line in text.splitlines() if line.strip()]


# ---------------------------------------------------------------- format -----

class TestFormat(Sandbox):
    def test_the_file_starts_with_a_header_that_names_the_format(self):
        record_a_match(self.path)
        header = self.lines()[0]
        self.assertEqual(header["kind"], replay.KIND)
        self.assertEqual(header["format"], replay.FORMAT)
        self.assertEqual(header["leagues"], ["fra.1"])
        self.assertIn("recorded_text", header)

    def test_one_line_per_poll_with_its_time_and_its_league(self):
        record_a_match(self.path)
        rows = self.lines()[1:]
        self.assertEqual(len(rows), len(script()))
        for row in rows:
            self.assertEqual(row["slug"], "fra.1")
            self.assertIsInstance(row["at"], float)
        # Les ecarts sont ceux du direct : 25 s entre deux releves.
        self.assertAlmostEqual(rows[1]["at"] - rows[0]["at"], 25.0, places=3)

    def test_every_line_is_readable_on_its_own(self):
        # Du JSON Lines : chaque ligne se relit seule, sans la precedente.
        record_a_match(self.path)
        for line in self.path.read_text(encoding="utf-8").splitlines():
            self.assertIsInstance(json.loads(line), dict)

    def test_what_is_written_is_what_the_source_answered(self):
        record_a_match(self.path)
        first = self.lines()[1]["payload"]
        self.assertEqual(first, script()[0])

    def test_reading_it_back_gives_the_recording(self):
        record_a_match(self.path)
        recording = replay.Recording.load(self.path)
        self.assertEqual(recording.format, replay.FORMAT)
        self.assertEqual(recording.slugs, ("fra.1",))
        self.assertEqual(recording.leagues(), [LIGUE1])
        self.assertEqual(len(recording.records), len(script()))
        self.assertAlmostEqual(recording.span, 25.0 * (len(script()) - 1),
                               places=3)
        self.assertEqual(recording.skipped, 0)
        self.assertIn("Ligue 1", recording.describe())

    def test_a_gzip_name_is_compressed_on_both_sides(self):
        path = self.dir / "match.jsonl.gz"
        record_a_match(path)
        # Ce n'est plus du texte : c'est bien passe par gzip.
        self.assertEqual(path.read_bytes()[:2], b"\x1f\x8b")
        recording = replay.Recording.load(path)
        self.assertEqual(len(recording.records), len(script()))

    def test_a_recording_carries_several_leagues_in_one_file(self):
        clock = FakeClock()
        recorder = replay.Recorder(self.path, clock=clock).start()
        for slug in ("fra.1", "eng.1", "fra.1"):
            clock.jump(25.0)
            recorder.note(slug, json.dumps(payload(event())).encode("utf-8"))
        recorder.close()

        recording = replay.Recording.load(self.path)
        self.assertEqual(recording.slugs, ("fra.1", "eng.1"))
        self.assertEqual([l.slug for l in recording.leagues()],
                         ["fra.1", "eng.1"])


class TestSize(Sandbox):
    """Une soiree de Ligue 1 a 25 s par releve, ca fait beaucoup de JSON."""

    def repeat_the_same_answer(self, times, dedupe=True):
        clock = FakeClock()
        recorder = replay.Recorder(self.path, clock=clock,
                                   dedupe=dedupe).start()
        raw = json.dumps(payload(event())).encode("utf-8")
        for _ in range(times):
            clock.jump(25.0)
            recorder.note("fra.1", raw)
        recorder.close()
        return recorder

    def test_an_answer_identical_to_the_previous_one_is_not_rewritten(self):
        recorder = self.repeat_the_same_answer(5)
        self.assertEqual(recorder.polls, 5)
        self.assertEqual(recorder.repeats, 4)

        rows = self.lines()[1:]
        self.assertIn("payload", rows[0])
        for row in rows[1:]:
            self.assertTrue(row["repeat"])
            self.assertNotIn("payload", row)
        # Le marqueur ne pese presque rien face a la charge utile.
        self.assertLess(len(json.dumps(rows[1])), len(json.dumps(rows[0])) / 10)

    def test_the_marker_keeps_the_time_of_the_poll(self):
        # C'est l'heure qui porte la cadence : la perdre changerait le rythme.
        self.repeat_the_same_answer(4)
        rows = self.lines()[1:]
        self.assertAlmostEqual(rows[-1]["at"] - rows[0]["at"], 75.0, places=3)

    def test_a_marker_is_served_as_the_payload_it_stands_for(self):
        self.repeat_the_same_answer(4)
        recording = replay.Recording.load(self.path)
        self.assertEqual(len(recording.records), 4)
        self.assertEqual(recording.repeats, 3)
        served = {record.text for record in recording.records}
        self.assertEqual(len(served), 1)

    def test_deduplication_can_be_switched_off(self):
        recorder = self.repeat_the_same_answer(5, dedupe=False)
        self.assertEqual(recorder.repeats, 0)
        for row in self.lines()[1:]:
            self.assertIn("payload", row)

    def test_a_changing_answer_is_always_rewritten(self):
        # Pendant un match, l'horloge bouge a chaque releve : rien a gagner.
        _events, recorder = record_a_match(self.path)
        self.assertEqual(recorder.repeats, 0)
        self.assertGreater(recorder.bytes, 0)
        self.assertIn("releve(s)", recorder.summary())


# ------------------------------------------------------------ robustesse -----

class TestBrokenFiles(Sandbox):
    def truncate(self, keep_ratio=0.5):
        """Coupe la derniere ligne en plein milieu, comme un kill -9."""
        text = self.path.read_text(encoding="utf-8")
        lines = text.splitlines()
        last = lines[-1]
        lines[-1] = last[:int(len(last) * keep_ratio)]
        self.path.write_text("\n".join(lines), encoding="utf-8")

    def test_a_truncated_line_is_dropped_and_the_rest_is_replayable(self):
        record_a_match(self.path)
        total = len(replay.Recording.load(self.path).records)
        self.truncate()

        recording = replay.Recording.load(self.path)
        self.assertEqual(len(recording.records), total - 1)
        self.assertEqual(recording.skipped, 1)
        self.assertIn("illisible", recording.describe())

    def test_a_session_killed_mid_line_still_replays_its_events(self):
        live, _recorder = record_a_match(self.path)
        self.truncate(0.3)
        replayed, _pace, _player = replay_a_match(self.path)
        # Le dernier releve est perdu, donc la fin du match aussi. Tout ce qui
        # precede est intact : c'est exactement ce qu'on demande a du JSONL.
        self.assertEqual([e.log_line() for e in replayed],
                         [e.log_line() for e in live][:-1])

    def test_a_marker_that_stands_for_nothing_is_dropped(self):
        # Un marqueur designe la derniere charge utile lue. Quand il n'y en a
        # aucune, il ne designe rien : le rattacher a la competition d'a cote
        # inventerait un score.
        replay.Recorder(self.path).start().close()
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write('{"at": 1.0, "slug": "fra.1", "repeat": true}\n')
            handle.write(json.dumps({"at": 2.0, "slug": "fra.1",
                                     "payload": payload(event())}) + "\n")

        recording = replay.Recording.load(self.path)
        self.assertEqual(len(recording.records), 1)
        self.assertEqual(recording.skipped, 1)

    def test_a_file_without_a_header_is_refused_clearly(self):
        self.path.write_text('{"at": 1.0, "slug": "fra.1", "payload": {}}\n',
                             encoding="utf-8")
        with self.assertRaises(replay.RecordingError) as caught:
            replay.Recording.load(self.path)
        self.assertIn("butbutbut", str(caught.exception))

    def test_a_newer_format_says_what_to_do(self):
        # La raison d'etre du numero de format : un fichier ecrit demain doit
        # dire pourquoi il ne se rejoue pas, pas partir de travers.
        self.path.write_text(json.dumps({
            "kind": replay.KIND, "format": replay.FORMAT + 1,
        }) + '\n{"at": 1.0, "slug": "fra.1", "payload": {}}\n', encoding="utf-8")
        with self.assertRaises(replay.RecordingError) as caught:
            replay.Recording.load(self.path)
        message = str(caught.exception)
        self.assertIn("format {}".format(replay.FORMAT + 1), message)
        self.assertIn("--update", message)

    def test_an_older_format_stays_replayable(self):
        # L'inverse, et c'est la promesse : format <= le notre, on rejoue.
        record_a_match(self.path)
        rows = self.path.read_text(encoding="utf-8").splitlines()
        header = json.loads(rows[0])
        header["format"] = 1
        header.pop("recorded_text", None)      # une version qui ne l'ecrivait pas
        header["future_key"] = "on ignore ce qu'on ne connait pas"
        rows[0] = json.dumps(header)
        self.path.write_text("\n".join(rows) + "\n", encoding="utf-8")

        recording = replay.Recording.load(self.path)
        self.assertEqual(len(recording.records), len(script()))

    def test_an_empty_file_and_a_missing_file(self):
        self.path.write_text("", encoding="utf-8")
        with self.assertRaises(replay.RecordingError):
            replay.Recording.load(self.path)
        with self.assertRaises(replay.RecordingError) as caught:
            replay.Recording.load(self.dir / "jamais-vu.jsonl")
        self.assertIn("introuvable", str(caught.exception))

    def test_a_header_alone_has_nothing_to_replay(self):
        replay.Recorder(self.path).start().close()
        with self.assertRaises(replay.RecordingError) as caught:
            replay.Recording.load(self.path)
        self.assertIn("aucun releve", str(caught.exception))

    def test_a_recording_resumed_in_the_same_file_stays_readable(self):
        # Le daemon relance ecrit un second en-tete a la suite : ce n'est pas
        # une ligne perdue, et le rejeu enchaine les deux sessions.
        record_a_match(self.path)
        record_a_match(self.path)
        recording = replay.Recording.load(self.path)
        self.assertEqual(recording.skipped, 0)
        self.assertEqual(len(recording.records), 2 * len(script()))

    def test_a_line_without_a_league_is_ignored(self):
        record_a_match(self.path)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write('{"at": 1.0, "payload": {}}\n')
        self.assertEqual(replay.Recording.load(self.path).skipped, 1)

    def test_a_write_that_fails_does_not_stop_the_surveillance(self):
        # Disque plein en plein match : on perd l'enregistrement, pas les buts.
        recorder = replay.Recorder(self.path).start()
        recorder._handle.close()          # le fichier se ferme sous ses pieds
        said = []
        recorder.on_log = said.append
        recorder.note("fra.1", b"{}")
        self.assertTrue(recorder.broken)
        self.assertEqual(len(said), 1)
        # Et l'opener continue de rendre la reponse a l'appelant.
        self.assertEqual(recorder.opener.__self__, recorder)


# ---------------------------------------------------------- ecarts de temps --

class TestTiming(Sandbox):
    def measure(self, speed, **kwargs):
        slept = []
        _events, pace, player = replay_a_match(
            self.path, speed=speed, sleeper=slept.append, **kwargs)
        return player.elapsed, sum(slept), pace

    def test_the_gaps_are_the_recorded_ones_divided_by_the_speed(self):
        record_a_match(self.path)
        elapsed, slept, _pace = self.measure(1.0)
        self.assertAlmostEqual(slept, elapsed, places=6)

        fast_elapsed, fast_slept, _pace = self.measure(60.0)
        # Meme trajet, meme temps de match couvert : seule l'attente change.
        self.assertAlmostEqual(fast_elapsed, elapsed, places=6)
        self.assertAlmostEqual(fast_slept * 60.0, fast_elapsed, places=6)
        self.assertAlmostEqual(fast_slept, slept / 60.0, places=6)

    def test_the_whole_recording_is_covered(self):
        record_a_match(self.path)
        elapsed, _slept, _pace = self.measure(1000.0)
        self.assertGreaterEqual(elapsed, replay.Recording.load(self.path).span)

    def test_an_irregular_gap_is_kept(self):
        # Deux releves colles, puis cinq minutes de rien : le rejeu doit
        # traverser les cinq minutes, pas les lisser.
        steps = script()[:3]
        record_a_match(self.path, steps=steps, step=25.0)
        with self.path.open("a", encoding="utf-8") as handle:
            last = self.lines()[-1]
            handle.write(json.dumps({"at": last["at"] + 300.0,
                                     "slug": "fra.1", "repeat": True}) + "\n")

        elapsed, slept, _pace = self.measure(10.0)
        self.assertGreaterEqual(elapsed, 350.0)
        self.assertAlmostEqual(slept * 10.0, elapsed, places=6)

    def test_nothing_actually_waits_when_the_sleeper_is_stubbed(self):
        # Les tests accelerent le temps, ils ne l'attendent pas : la preuve,
        # c'est que la somme des attentes depasse largement leur duree.
        record_a_match(self.path)
        _elapsed, slept, _pace = self.measure(1.0)
        self.assertGreater(slept, 100.0)

    def test_the_pace_stops_at_the_next_poll_rather_than_overshooting(self):
        # Sinon un enregistrement dont les releves ne tombent pas pile sur la
        # cadence prendrait un retard qui grandirait a chaque tour.
        record_a_match(self.path)
        recording = replay.Recording.load(self.path)
        player = replay.Player(recording)
        pace = replay.Pace(player, sleeper=lambda _s: None)
        second = recording.records[1].at
        player.opener(URL)              # le premier releve, comme prime()

        pace.wait(3600.0)               # on demande une heure...
        self.assertLess(player.wall(), second + 1.0)   # ... on s'arrete au releve
        self.assertGreaterEqual(player.wall(), second)

    def test_the_last_card_gets_its_time_on_screen(self):
        record_a_match(self.path)
        recording = replay.Recording.load(self.path)
        player = replay.Player(recording)
        slept = []
        pace = replay.Pace(player, speed=1000.0, sleeper=slept.append,
                           linger=6.0)
        while player.pending:
            player.advance(3600.0)
            player.opener(URL)
        self.assertFalse(pace.is_set())
        pace.wait(0.0)
        self.assertTrue(pace.is_set())
        self.assertEqual(slept[-1], 6.0)   # le sursis n'est pas accelere

    def test_the_pace_answers_like_a_threading_event(self):
        # C'est par la que les boucles de cli.py dorment : meme interface, ou
        # le rejeu devrait s'ecrire une boucle a lui, qui ne prouverait rien.
        record_a_match(self.path)
        pace = replay.Pace(replay.Player(replay.Recording.load(self.path)),
                           sleeper=lambda _s: None)
        self.assertFalse(pace.is_set())
        pace.set()
        self.assertTrue(pace.wait(10.0))
        pace.clear()
        self.assertFalse(pace.is_set())


# -------------------------------------------------------------- fidelite ----

class TestTheReplayIsTheLiveRun(Sandbox):
    """Le test qui justifie tout le reste."""

    def test_the_replay_produces_the_very_same_events(self):
        live, _recorder = record_a_match(self.path)
        replayed, _pace, _player = replay_a_match(self.path)

        self.assertEqual([e.log_line() for e in replayed],
                         [e.log_line() for e in live])

    def test_the_recorded_match_really_has_everything_in_it(self):
        # Un rejeu identique a un direct vide ne prouverait rien.
        live, _recorder = record_a_match(self.path)
        kinds = [e.kind for e in live]
        self.assertEqual(kinds, [watcher.KICKOFF, watcher.GOAL,
                                 watcher.RED_CARD, watcher.HALFTIME,
                                 watcher.RESTART, watcher.GOAL,
                                 watcher.CANCELLED, watcher.FULLTIME])

    def test_the_replay_goes_through_the_watcher(self):
        # Les buts sont detectes par comparaison de scores, pas relus dans le
        # fichier : le premier releve reste donc muet, comme en direct.
        recording = replay.Recording.load(self.path) if self.path.exists() else None
        self.assertIsNone(recording)

        record_a_match(self.path)
        recording = replay.Recording.load(self.path)
        player = replay.Player(recording)
        guard = watcher.Watcher([LIGUE1], opener=player.opener,
                                monotonic=player.monotonic, clock=player.wall)
        self.assertEqual(guard.refresh(LIGUE1, now=player.monotonic()), [])
        self.assertEqual(len(guard.matches["fra.1"]), 1)

    def test_replaying_twice_gives_the_same_thing(self):
        record_a_match(self.path)
        first, _pace, _player = replay_a_match(self.path)
        second, _pace, _player = replay_a_match(self.path)
        self.assertEqual([e.log_line() for e in first],
                         [e.log_line() for e in second])

    def test_a_faster_replay_says_exactly_the_same_thing(self):
        record_a_match(self.path)
        slow, _pace, _player = replay_a_match(self.path, speed=1.0)
        fast, _pace, _player = replay_a_match(self.path, speed=600.0)
        self.assertEqual([e.log_line() for e in slow],
                         [e.log_line() for e in fast])

    def test_no_poll_is_ever_skipped(self):
        record_a_match(self.path)
        _events, _pace, player = replay_a_match(self.path)
        self.assertEqual(player.pending, 0)
        self.assertEqual(player.served, len(script()))

    def test_a_poll_before_the_next_record_gets_the_previous_answer(self):
        # Ce que la vraie source aurait fait : deux appels rapproches sur un
        # tableau de bord qui n'a pas bouge rendent deux fois la meme chose.
        record_a_match(self.path)
        player = replay.Player(replay.Recording.load(self.path))
        first = player.opener(URL)
        again = player.opener(URL)
        self.assertEqual(first, again)
        self.assertEqual(player.served, 1)

    def test_a_league_the_file_does_not_carry_is_a_source_error(self):
        record_a_match(self.path)
        player = replay.Player(replay.Recording.load(self.path))
        with self.assertRaises(espn.SourceError):
            player.opener(espn.SCOREBOARD_URL.format(sport=sports.DEFAULT.code, slug="eng.1"))


class TestUrls(unittest.TestCase):
    def test_the_league_is_read_back_from_the_url(self):
        self.assertEqual(replay.slug_of(URL), "fra.1")
        self.assertEqual(
            replay.slug_of(espn.TEAMS_URL.format(
                sport=sports.DEFAULT.code, slug="uefa.champions")),
            "uefa.champions")
        self.assertEqual(replay.slug_of("https://exemple.test/rien"), "")

    def test_another_sport_keeps_its_prefix(self):
        """Deux sports peuvent partager un code ESPN : la cle doit les separer."""
        self.assertEqual(
            replay.slug_of(espn.SCOREBOARD_URL.format(
                sport=sports.HOCKEY.code, slug="nhl")),
            "hockey:nhl")

    def test_a_match_summary_gets_a_key_of_its_own(self):
        """450 ko de plays[] n'ont rien a faire dans la file du tableau de bord."""
        board = espn.SCOREBOARD_URL.format(sport=sports.HOCKEY.code, slug="nhl")
        summary = espn.SUMMARY_URL.format(
            sport=sports.HOCKEY.code, slug="nhl") + "?event=401809123"

        self.assertEqual(replay.slug_of(summary), "hockey:nhl@401809123")
        self.assertNotEqual(replay.slug_of(summary), replay.slug_of(board))

    def test_two_matches_of_the_same_evening_do_not_share_a_key(self):
        base = espn.SUMMARY_URL.format(sport=sports.HOCKEY.code, slug="nhl")
        self.assertNotEqual(replay.slug_of(base + "?event=1"),
                            replay.slug_of(base + "?event=2"))

    def test_a_summary_without_a_match_number_still_stands_apart(self):
        base = espn.SUMMARY_URL.format(sport=sports.HOCKEY.code, slug="nhl")
        self.assertEqual(replay.slug_of(base), "hockey:nhl@")


class TestASummaryInARecording(Sandbox):
    """Enregistre a part, rejoue a part - et absent, il ne coute qu'un nom."""

    def test_the_recorder_keeps_the_two_answers_apart(self):
        board = espn.SCOREBOARD_URL.format(sport=sports.HOCKEY.code, slug="nhl")
        summary = espn.SUMMARY_URL.format(
            sport=sports.HOCKEY.code, slug="nhl") + "?event=7"

        def source(url, _timeout=None):
            return (b'{"plays": []}' if "/summary" in url
                    else b'{"events": []}')

        recorder = replay.Recorder(self.path, opener=source).start()
        recorder.opener(board)
        recorder.opener(summary)
        recorder.close()

        slugs = [record.slug
                 for record in replay.Recording.load(self.path).records]
        self.assertEqual(slugs, ["hockey:nhl", "hockey:nhl@7"])

    def test_an_old_recording_degrades_without_a_word(self):
        """Un fichier d'avant ce chantier ne porte aucun resume : c'est prevu."""
        board = espn.SCOREBOARD_URL.format(sport=sports.HOCKEY.code, slug="nhl")

        recorder = replay.Recorder(
            self.path, opener=lambda *_: b'{"events": []}').start()
        recorder.opener(board)
        recorder.close()

        player = replay.Player(replay.Recording.load(self.path))
        player.opener(board)
        with self.assertRaises(espn.SourceError):
            player.opener(espn.SUMMARY_URL.format(
                sport=sports.HOCKEY.code, slug="nhl") + "?event=7")


class TestReadableSizes(unittest.TestCase):
    def test_sizes(self):
        self.assertEqual(replay.human_size(12), "12 o")
        self.assertEqual(replay.human_size(2048), "2.0 ko")
        self.assertIn("Mo", replay.human_size(5 * 1024 * 1024))

    def test_durations(self):
        self.assertEqual(replay.human_time(45), "45 s")
        self.assertEqual(replay.human_time(200), "3 min 20 s")
        self.assertEqual(replay.human_time(6720), "1 h 52")


# -------------------------------------------------------------- isolation ---

class TestIsolation(Sandbox):
    """Un rejeu ne doit rien laisser dans les fichiers du vrai daemon."""

    def setUp(self):
        super().setUp()
        self.data = self.dir / "donnees"
        patcher = mock.patch.object(cli, "data_dir", return_value=self.data)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_the_sandbox_moves_the_journal_the_state_and_the_pid(self):
        real = cli.paths()
        with cli.sandbox_paths(self.data / "replay") as fake:
            for key in ("log", "state", "pid"):
                self.assertNotEqual(fake[key], real[key])
                self.assertEqual(fake[key].parent, self.data / "replay")
            # Le son et les ecussons restent partages : un rejeu ne doit pas
            # retelecharger tous les ecussons pour rien.
            for key in ("sound", "logos", "wav", "config"):
                self.assertEqual(fake[key], real[key])
            self.assertEqual(cli.paths()["log"], fake["log"])
        self.assertEqual(cli.paths(), real)

    def test_the_sandbox_is_put_back_even_when_the_block_explodes(self):
        real = cli.paths()
        with self.assertRaises(ZeroDivisionError):
            with cli.sandbox_paths(self.data / "replay"):
                1 / 0
        self.assertEqual(cli.paths(), real)

    def test_a_replay_writes_its_journal_beside_and_not_in_the_real_one(self):
        record_a_match(self.path)
        self.data.mkdir(parents=True, exist_ok=True)
        real_log = cli.paths()["log"]
        real_log.write_text("2026-09-05 22:10:04  demarrage\n", encoding="utf-8")

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = cli.main(["--replay", str(self.path), "--no-overlay",
                             "--no-sound", "--no-logos", "--duration", "0.01",
                             "--speed", "100000", "--red-cards"])
        self.assertEqual(code, 0)

        replayed = (self.data / "replay" / "butbutbut.log").read_text(encoding="utf-8")
        self.assertIn("BUT [Ligue 1]", replayed)
        self.assertIn("FIN DU MATCH", replayed)
        # Le journal du vrai daemon n'a pas bouge d'un octet, et son etat non
        # plus : --today et --status ignorent tout de ce rejeu.
        self.assertEqual(real_log.read_text(encoding="utf-8"),
                         "2026-09-05 22:10:04  demarrage\n")
        self.assertFalse(cli.paths()["state"].exists())
        self.assertFalse(cli.paths()["pid"].exists())

    def test_the_replay_cleans_up_its_own_state_file(self):
        record_a_match(self.path)
        self.data.mkdir(parents=True, exist_ok=True)
        with redirect_stdout(io.StringIO()):
            cli.main(["--replay", str(self.path), "--no-overlay", "--no-sound",
                      "--no-logos", "--duration", "0.01", "--speed", "100000"])
        self.assertFalse((self.data / "replay" / "butbutbut.json").exists())


class CardStack:
    """Une pile de cartes sans tkinter : elle retient ce qu'on lui pousse."""

    def __init__(self):
        self.cards = []
        self.drain = None
        self.stopped = False

    def every(self, _ms, callback):
        self.drain = callback

    def run(self):
        # La vraie pile vide la file toutes les PUMP_MS millisecondes : on
        # imite ce rythme plutot que de tourner a vide sur un coeur entier.
        while not self.stopped:
            self.drain()
            time.sleep(0.001)

    def push(self, card, duration=None):
        self.cards.append(card)

    def stop(self):
        self.stopped = True

    def close(self):
        pass


class TestTheCardLoopReplaysToo(Sandbox):
    """Le chemin avec cartes est celui qu'on utilise vraiment.

    C'est aussi celui ou la Pace tient lieu d'evenement d'arret a un fil de
    surveillance et a une boucle d'affichage a la fois : si elle ne portait pas
    exactement l'interface de threading.Event, ca se verrait ici.
    """

    def setUp(self):
        super().setUp()
        self.data = self.dir / "donnees"
        patcher = mock.patch.object(cli, "data_dir", return_value=self.data)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_every_event_becomes_a_card(self):
        live, _recorder = record_a_match(self.path)
        recording = replay.Recording.load(self.path)
        player = replay.Player(recording)
        pace = replay.Pace(player, speed=100000.0)

        args = cli.build_parser().parse_args(
            ["--quiet", "--no-sound", "--no-logos", "--duration", "0.01",
             "--red-cards"])
        stack = CardStack()
        with cli.sandbox_paths(self.data / "replay") as p:
            guard = watcher.Watcher(recording.leagues(), opener=player.opener,
                                    monotonic=player.monotonic,
                                    clock=player.wall, red_cards=True)
            guard.prime(pause=0.0, now=player.monotonic())
            reporter = state.Reporter(p["state"],
                                      leagues=recording.leagues())
            cli._watch_with_cards(guard, args, pace, stack, reporter,
                                  pinned.Pin(args.pin), cli.crest_cache(args))

        self.assertEqual(len(stack.cards), len(live))
        self.assertTrue(stack.stopped)
        self.assertEqual([card.title for card in stack.cards],
                         [event_.title for event_ in live])


# ------------------------------------------------------- ligne de commande ---

class TestCommandLine(unittest.TestCase):
    def setUp(self):
        self.parser = cli.build_parser()

    def test_defaults(self):
        args = self.parser.parse_args([])
        self.assertIsNone(args.record)
        self.assertIsNone(args.replay)
        self.assertEqual(args.speed, replay.DEFAULT_SPEED)

    def test_flags(self):
        args = self.parser.parse_args(
            ["--replay", "match.jsonl", "--speed", "60"])
        self.assertEqual(args.replay, "match.jsonl")
        self.assertEqual(args.speed, 60.0)

    def test_recording_and_replaying_at_once_is_refused(self):
        self.assertEqual(cli.main(["--record", "a.jsonl",
                                   "--replay", "b.jsonl"]), 2)

    def test_a_speed_of_zero_is_refused(self):
        self.assertEqual(cli.main(["--replay", "b.jsonl", "--speed", "0"]), 2)
        self.assertEqual(cli.main(["--replay", "b.jsonl", "--speed", "-3"]), 2)

    def test_an_unreadable_recording_is_refused_without_a_traceback(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "absent.jsonl"
            self.assertEqual(cli.main(["--replay", str(path)]), 2)

    def test_replay_is_reachable_from_main(self):
        help_text = self.parser.format_help()
        self.assertIn("--replay", help_text)
        self.assertIn("--record", help_text)
        self.assertIn("--speed", help_text)


if __name__ == "__main__":
    unittest.main()
