"""Ne pas deranger : la plage horaire, la presentation, et le verdict unique.

Ni reseau ni ecran ici, et surtout pas l'horloge de la machine : chaque test
qui parle d'une heure la fournit lui-meme, sinon la suite dirait autre chose
selon qu'elle tourne a 9 h ou a 2 h du matin. La detection de presentation,
elle, est remplacee par ce qu'on veut lui faire dire - la vraie ne repond que
sous Windows, et la CI n'y tourne pas forcement.
"""

import unittest
from datetime import datetime
from unittest import mock

from butbutbut import presenting, silence


def at(hour, minute=0) -> datetime:
    """Un moment de la journee. Le jour choisi n'a aucune importance."""
    return datetime(2026, 9, 6, hour, minute)


class TestReadingAWindow(unittest.TestCase):
    def test_a_plain_window_is_read(self):
        window = silence.parse("23:00-08:00")
        self.assertEqual((window.start, window.end), (23 * 60, 8 * 60))
        self.assertEqual(window.describe(), "23:00-08:00")

    def test_the_forms_people_actually_type_are_accepted(self):
        for text in ("23:00-08:00", "23h00-08h00", "23h-8h", "23-8",
                     " 23:00 - 8:00 ", "23.00-08.00"):
            self.assertEqual(silence.normalize(text), "23:00-08:00", text)

    def test_nothing_written_is_no_window_at_all(self):
        for text in (None, "", "   "):
            self.assertIsNone(silence.parse(text))
            self.assertEqual(silence.normalize(text), "")

    def test_an_unreadable_window_says_the_expected_format(self):
        for text in ("n'importe quoi", "23:00", "23:00-08:00-09:00",
                     "de 23h a 8h", "-", "23:00-"):
            with self.assertRaises(silence.Invalid) as raised:
                silence.parse(text)
            self.assertIn(silence.FORMAT, str(raised.exception), text)
            self.assertIn(silence.EXAMPLE, str(raised.exception), text)

    def test_an_impossible_hour_is_refused(self):
        for text in ("25:00-08:00", "23:70-08:00", "23:00-24:00"):
            with self.assertRaises(silence.Invalid):
                silence.parse(text)

    def test_a_window_that_starts_where_it_ends_is_refused(self):
        """"08:00-08:00" veut dire tout le temps, ou jamais : on ne devine pas."""
        with self.assertRaises(silence.Invalid) as raised:
            silence.parse("08:00-08:00")
        self.assertIn("vide", str(raised.exception))


class TestWhenAWindowCovers(unittest.TestCase):
    def test_a_daytime_window(self):
        window = silence.parse("09:00-17:00")
        self.assertFalse(window.wraps)
        self.assertTrue(window.covers(at(12)))
        self.assertFalse(window.covers(at(8, 59)))
        self.assertFalse(window.covers(at(22)))

    def test_a_window_across_midnight(self):
        """Le cas courant : personne ne dort de 9 h a 17 h."""
        window = silence.parse("23:00-08:00")
        self.assertTrue(window.wraps)
        for moment in (at(23), at(23, 30), at(0), at(2), at(7, 59)):
            self.assertTrue(window.covers(moment), moment)
        for moment in (at(8), at(12), at(22, 59)):
            self.assertFalse(window.covers(moment), moment)

    def test_the_bounds_are_start_included_end_excluded(self):
        window = silence.parse("23:00-08:00")
        self.assertTrue(window.covers(at(23, 0)))       # 23:00 pile : on se tait
        self.assertFalse(window.covers(at(8, 0)))       # 08:00 pile : on parle
        self.assertTrue(window.covers(at(7, 59)))
        self.assertFalse(window.covers(at(22, 59)))

    def test_midnight_is_a_bound_like_another(self):
        window = silence.parse("00:00-06:00")
        self.assertFalse(window.wraps)
        self.assertTrue(window.covers(at(0, 0)))
        self.assertFalse(window.covers(at(6, 0)))

    def test_a_window_may_also_be_asked_in_minutes(self):
        window = silence.parse("23:00-08:00")
        self.assertTrue(window.covers(23 * 60))
        self.assertFalse(window.covers(8 * 60))


class TestTheVerdict(unittest.TestCase):
    def test_nothing_armed_never_hushes(self):
        hush = silence.Silence()
        self.assertFalse(hush.armed)
        self.assertIsNone(hush.reason(at(3)))
        self.assertIn("aucun", hush.describe())

    def test_inside_the_window_it_says_until_when(self):
        hush = silence.Silence("23:00-08:00")
        self.assertTrue(hush.armed)
        found = hush.reason(at(2))
        self.assertIsNotNone(found)
        self.assertIn("08:00", found)

    def test_outside_the_window_it_says_nothing(self):
        self.assertIsNone(silence.Silence("23:00-08:00").reason(at(14)))

    def test_the_clock_of_the_machine_is_used_when_no_moment_is_given(self):
        hush = silence.Silence("23:00-08:00", clock=lambda: at(2))
        self.assertIsNotNone(hush.reason())
        self.assertIsNone(
            silence.Silence("23:00-08:00", clock=lambda: at(14)).reason())

    def test_only_the_changes_reach_the_journal(self):
        """Un daemon qui repete "en veille" tous les releves noierait ses buts."""
        lines = []
        hush = silence.Silence("23:00-08:00", on_log=lines.append)
        for _ in range(4):
            hush.reason(at(2))
        self.assertEqual(len(lines), 1)
        self.assertIn("silence", lines[0])

        for _ in range(4):
            hush.reason(at(9))
        self.assertEqual(len(lines), 2)
        self.assertIn("fin du silence", lines[1])

    def test_a_quiet_start_writes_nothing(self):
        lines = []
        silence.Silence("23:00-08:00", on_log=lines.append).reason(at(14))
        self.assertEqual(lines, [])

    def test_describe_says_the_window_and_the_moment(self):
        hush = silence.Silence("23:00-08:00", clock=lambda: at(2))
        text = hush.describe()
        self.assertIn("23:00-08:00", text)
        self.assertIn("08:00", text)
        self.assertIn("rien en ce moment",
                      silence.Silence("23:00-08:00",
                                      clock=lambda: at(14)).describe())

    def test_describe_does_not_write_to_the_journal(self):
        """--status pose la question sans etre le daemon : il ne raconte rien."""
        lines = []
        silence.Silence("23:00-08:00", on_log=lines.append,
                        clock=lambda: at(2)).describe()
        self.assertEqual(lines, [])


class TestWhilePresenting(unittest.TestCase):
    def state(self, value):
        return mock.patch.object(presenting, "state", return_value=value)

    def test_a_presentation_hushes(self):
        hush = silence.Silence(while_presenting=True)
        with self.state(presenting.PRESENTATION_MODE):
            self.assertEqual(hush.reason(), "mode presentation")

    def test_do_not_disturb_hushes_too(self):
        hush = silence.Silence(while_presenting=True)
        with self.state(presenting.QUIET_TIME):
            self.assertIn("ne pas deranger", hush.reason())

    def test_an_ordinary_desktop_does_not(self):
        hush = silence.Silence(while_presenting=True)
        with self.state(presenting.ACCEPTS_NOTIFICATIONS):
            self.assertIsNone(hush.reason())

    def test_a_fullscreen_game_is_not_a_presentation(self):
        """Sinon butbutbut deviendrait muet pendant un match joue en plein
        ecran, c'est-a-dire exactement quand il sert. C'est --retry-fullscreen
        qui s'occupe de ce cas-la, et le son, lui, part."""
        hush = silence.Silence(while_presenting=True)
        for value in (presenting.BUSY, presenting.D3D_FULL_SCREEN,
                      presenting.APP_FULL_SCREEN, presenting.NOT_PRESENT):
            with self.state(value):
                self.assertIsNone(hush.reason(), value)

    def test_the_option_off_never_asks(self):
        hush = silence.Silence()
        with mock.patch.object(presenting, "state") as asked:
            self.assertIsNone(hush.reason())
        asked.assert_not_called()

    def test_the_window_wins_before_anything_is_asked(self):
        """Il est 2 h : inutile de deranger Windows pour savoir quoi faire."""
        hush = silence.Silence("23:00-08:00", while_presenting=True)
        with mock.patch.object(presenting, "state") as asked:
            self.assertIsNotNone(hush.reason(at(2)))
        asked.assert_not_called()

    def test_a_detection_that_fails_lets_the_card_through(self):
        lines = []
        hush = silence.Silence(while_presenting=True, on_log=lines.append)
        with self.state(None):
            for _ in range(5):
                self.assertIsNone(hush.reason())
        # Une ligne, pas une par releve : un daemon tourne des heures.
        self.assertEqual(len(lines), 1)
        self.assertIn("comme d'habitude", lines[0])


class TestWhatTheSystemSays(unittest.TestCase):
    """La decision de presenting.py, sans Windows : c'est une table."""

    def test_the_two_states_that_mean_do_not_disturb(self):
        self.assertEqual(presenting.reason_for(presenting.PRESENTATION_MODE),
                         "mode presentation")
        self.assertIn("ne pas deranger",
                      presenting.reason_for(presenting.QUIET_TIME))

    def test_everything_else_lets_the_card_through(self):
        for value in (presenting.NOT_PRESENT, presenting.BUSY,
                      presenting.D3D_FULL_SCREEN,
                      presenting.ACCEPTS_NOTIFICATIONS,
                      presenting.APP_FULL_SCREEN):
            self.assertIsNone(presenting.reason_for(value), value)

    def test_an_unknown_or_absent_state_lets_the_card_through(self):
        """Une version de Windows qui ajouterait un etat ne doit rien casser."""
        for value in (None, 0, 99, "presentation", object()):
            self.assertIsNone(presenting.reason_for(value), value)

    def test_asking_never_raises_anywhere(self):
        # Sur une machine sans Windows, state() rend None sans rien tenter.
        self.assertIn(presenting.state(), list(presenting.REASONS) + [
            presenting.NOT_PRESENT, presenting.BUSY,
            presenting.D3D_FULL_SCREEN, presenting.ACCEPTS_NOTIFICATIONS,
            presenting.APP_FULL_SCREEN, None])

    def test_a_broken_call_is_an_absent_answer(self):
        with mock.patch.object(presenting, "supported", return_value=True):
            with mock.patch("ctypes.windll", create=True) as windll:
                windll.shell32.SHQueryUserNotificationState.side_effect = OSError
                self.assertIsNone(presenting.state())


if __name__ == "__main__":
    unittest.main()
