import unittest

from butbutbut import screens


class TestPlacement(unittest.TestCase):
    def setUp(self):
        self.monitor = screens.Monitor(0, 0, 1920, 1080, primary=True)

    def test_bottom_right_keeps_the_margin(self):
        x, y = self.monitor.place(400, 120, "bottom-right", margin=24)
        self.assertEqual((x, y), (1920 - 400 - 24, 1080 - 120 - 24))

    def test_every_corner(self):
        self.assertEqual(self.monitor.place(400, 120, "top-left", margin=24), (24, 24))
        self.assertEqual(self.monitor.place(400, 120, "top-right", margin=24),
                         (1496, 24))
        self.assertEqual(self.monitor.place(400, 120, "bottom-left", margin=24),
                         (24, 936))
        self.assertEqual(self.monitor.place(400, 120, "center"), (760, 480))

    def test_second_monitor_offset_is_respected(self):
        second = screens.Monitor(1920, 0, 1920, 1080)
        x, _y = second.place(400, 120, "bottom-right", margin=24)
        self.assertEqual(x, 1920 + 1920 - 400 - 24)

    def test_a_card_wider_than_the_screen_stays_on_it(self):
        small = screens.Monitor(0, 0, 300, 200)
        self.assertEqual(small.place(400, 120, "bottom-right"), (0, 56))

    def test_unknown_corner_falls_back_to_bottom_right(self):
        self.assertEqual(self.monitor.place(400, 120, "nulle-part", margin=24),
                         self.monitor.place(400, 120, "bottom-right", margin=24))


class TestSelection(unittest.TestCase):
    def setUp(self):
        self.found = [
            screens.Monitor(0, 0, 1920, 1080, name="a"),
            screens.Monitor(1920, 0, 2560, 1440, primary=True, name="b"),
        ]

    def test_default_is_the_primary_screen(self):
        self.assertEqual(screens.pick(self.found, None).name, "b")
        self.assertEqual(screens.pick(self.found, "primary").name, "b")

    def test_index_selection_and_clamping(self):
        self.assertEqual(screens.pick(self.found, 0).name, "a")
        self.assertEqual(screens.pick(self.found, "1").name, "b")
        self.assertEqual(screens.pick(self.found, 99).name, "b")

    def test_nonsense_preference_falls_back(self):
        self.assertEqual(screens.pick(self.found, "gauche").name, "a")

    def test_empty_list_still_gives_a_screen(self):
        self.assertIsInstance(screens.pick([], None), screens.Monitor)

    def test_monitors_is_never_empty(self):
        found = screens.monitors()
        self.assertTrue(found)
        for monitor in found:
            self.assertGreater(monitor.width, 0)
            self.assertGreater(monitor.height, 0)

    def test_describe(self):
        self.assertIn("2 ecrans", screens.describe(self.found))
        self.assertIn("1 ecran", screens.describe(self.found[:1]))


if __name__ == "__main__":
    unittest.main()
