"""La detection du plein ecran, testee sans ecran et sans ctypes.

Les rectangles utilises ici sont ceux releves sur une machine Windows 10 a deux
dalles 1920x1080 : c'est le cas reel qui a motive le correctif.
"""

import unittest
from unittest import mock

from butbutbut import fullscreen, screens

# Releves sur la machine de test.
DALLE = (0, 0, 1920, 1080)              # rcMonitor
TRAVAIL = (0, 0, 1920, 1040)            # rcWork, ce que renvoie screens.py
PLEIN_ECRAN = (0, 0, 1920, 1080)
MAXIMISEE = (-8, -8, 1928, 1048)        # bordures invisibles comprises

CAP = fullscreen.WS_CAPTION
THICK = fullscreen.WS_THICKFRAME
SANS_DECO = 0x96000008                  # style d'une fenetre plein ecran relevee
AVEC_DECO = 0x15C70000                  # style d'une fenetre maximisee relevee


class TestCoversScreen(unittest.TestCase):
    def test_a_fullscreen_window_covers_the_whole_panel(self):
        self.assertTrue(
            fullscreen.covers_screen(PLEIN_ECRAN, DALLE, SANS_DECO))

    def test_a_maximised_window_does_not(self):
        # Elle deborde sur les cotes mais s'arrete au-dessus de la barre des
        # taches : la carte reste visible dessus.
        self.assertFalse(
            fullscreen.covers_screen(MAXIMISEE, DALLE, AVEC_DECO))

    def test_a_maximised_window_is_refused_on_its_styles_alone(self):
        # Barre des taches masquee automatiquement : la fenetre maximisee couvre
        # alors toute la dalle. Seuls ses styles la distinguent encore.
        cachee = (-8, -8, 1928, 1088)
        self.assertTrue(fullscreen.covers_screen(cachee, DALLE))
        self.assertFalse(fullscreen.covers_screen(cachee, DALLE, AVEC_DECO))
        for style in (CAP, THICK, CAP | THICK):
            self.assertFalse(fullscreen.covers_screen(PLEIN_ECRAN, DALLE, style))

    def test_the_work_area_is_not_the_panel(self):
        # Le piege : mesuree contre la zone de travail, une fenetre maximisee
        # passe pour du plein ecran. D'ou le rcMonitor.
        self.assertTrue(fullscreen.covers_screen(MAXIMISEE, TRAVAIL))

    def test_a_window_that_leaves_a_strip_uncovered(self):
        for window in ((0, 0, 1920, 1000),      # bas libre
                       (0, 100, 1920, 1080),    # haut libre
                       (200, 0, 1920, 1080),    # gauche libre
                       (0, 0, 1700, 1080)):     # droite libre
            self.assertFalse(fullscreen.covers_screen(window, DALLE, SANS_DECO),
                             "{} ne couvre pas la dalle".format(window))

    def test_a_few_pixels_of_jeu_are_tolerated(self):
        short = (0, 0, 1920, 1080 - fullscreen.EDGE_TOLERANCE)
        self.assertTrue(fullscreen.covers_screen(short, DALLE, SANS_DECO))
        shorter = (0, 0, 1920, 1080 - fullscreen.EDGE_TOLERANCE - 1)
        self.assertFalse(fullscreen.covers_screen(shorter, DALLE, SANS_DECO))

    def test_tolerance_can_be_tightened(self):
        self.assertFalse(
            fullscreen.covers_screen((0, 0, 1920, 1078), DALLE, SANS_DECO,
                                     tolerance=0))

    def test_a_fullscreen_window_on_the_other_panel_does_not_count(self):
        second = (1920, 0, 3840, 1080)
        self.assertTrue(fullscreen.covers_screen(second, second, SANS_DECO))
        self.assertFalse(fullscreen.covers_screen(second, DALLE, SANS_DECO))

    def test_a_window_larger_than_the_panel_still_covers_it(self):
        self.assertTrue(
            fullscreen.covers_screen((-100, -100, 4000, 2000), DALLE, SANS_DECO))

    def test_empty_or_broken_rectangles_are_never_fullscreen(self):
        for window in ((0, 0, 0, 0), (10, 10, 5, 5), None, (1, 2, 3),
                       ("a", "b", "c", "d")):
            self.assertFalse(fullscreen.covers_screen(window, DALLE, SANS_DECO))
        self.assertFalse(fullscreen.covers_screen(PLEIN_ECRAN, (0, 0, 0, 0),
                                                  SANS_DECO))
        self.assertFalse(fullscreen.covers_screen(PLEIN_ECRAN, None, SANS_DECO))

    def test_an_unknown_style_falls_back_to_geometry(self):
        self.assertTrue(fullscreen.covers_screen(PLEIN_ECRAN, DALLE))
        self.assertTrue(fullscreen.covers_screen(PLEIN_ECRAN, DALLE, 0))


class TestShellWindows(unittest.TestCase):
    """Le bureau couvre l'ecran et n'a pas de decoration : ce n'est pas un jeu."""

    def test_desktop_geometry_would_pass_without_the_guard(self):
        bureau = (0, 0, 3840, 1080)     # Progman, releve sur la machine de test
        self.assertTrue(fullscreen.covers_screen(bureau, DALLE, 0x800000C0))
        self.assertTrue(fullscreen.is_shell_class("Progman"))
        self.assertTrue(fullscreen.is_shell_class("WorkerW"))

    def test_ordinary_classes_are_not_the_shell(self):
        for name in ("Chrome_WidgetWin_1", "TkTopLevel", "", None):
            self.assertFalse(fullscreen.is_shell_class(name))


class TestMonitorRect(unittest.TestCase):
    def test_rect_of_a_monitor(self):
        monitor = screens.Monitor(1920, 0, 1920, 1040)
        self.assertEqual(fullscreen.monitor_rect(monitor), (1920, 0, 3840, 1040))


class TestCovers(unittest.TestCase):
    """L'entree impure : elle ne doit jamais lever, ni mentir hors de Windows."""

    def setUp(self):
        self.monitor = screens.Monitor(0, 0, 1920, 1040, primary=True)

    def test_nothing_is_detected_outside_windows(self):
        for platform in ("linux", "darwin", "freebsd"):
            with mock.patch.object(fullscreen.sys, "platform", platform):
                self.assertFalse(fullscreen.supported())
                self.assertFalse(fullscreen.covers(self.monitor))

    def test_a_broken_win32_call_never_raises(self):
        with mock.patch.object(fullscreen.sys, "platform", "win32"), \
                mock.patch.object(fullscreen, "_foreground_window",
                                  side_effect=OSError("boom")):
            self.assertFalse(fullscreen.covers(self.monitor))

    def test_no_foreground_window_is_not_fullscreen(self):
        with mock.patch.object(fullscreen.sys, "platform", "win32"), \
                mock.patch.object(fullscreen, "_foreground_window",
                                  return_value=None):
            self.assertFalse(fullscreen.covers(self.monitor))

    def test_a_fullscreen_foreground_window_is_reported(self):
        with mock.patch.object(fullscreen.sys, "platform", "win32"), \
                mock.patch.object(fullscreen, "_screen_rect", return_value=DALLE), \
                mock.patch.object(fullscreen, "_foreground_window",
                                  return_value=(PLEIN_ECRAN, SANS_DECO)):
            self.assertTrue(fullscreen.covers(self.monitor))

    def test_a_maximised_foreground_window_is_not(self):
        with mock.patch.object(fullscreen.sys, "platform", "win32"), \
                mock.patch.object(fullscreen, "_screen_rect", return_value=DALLE), \
                mock.patch.object(fullscreen, "_foreground_window",
                                  return_value=(MAXIMISEE, AVEC_DECO)):
            self.assertFalse(fullscreen.covers(self.monitor))

    def test_the_screen_rect_falls_back_to_the_work_area(self):
        # Si Windows ne repond pas, on compare a ce qu'on sait deja de l'ecran.
        with mock.patch.object(fullscreen, "_user32", side_effect=OSError):
            self.assertEqual(fullscreen._screen_rect(self.monitor),
                             (0, 0, 1920, 1040))


if __name__ == "__main__":
    unittest.main()
