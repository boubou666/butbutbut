import unittest
from datetime import datetime, timezone
from types import SimpleNamespace

from butbutbut import ical


def match(match_id="401", home="Marseille", away="Lyon", sport="soccer"):
    return SimpleNamespace(
        id=match_id,
        start=datetime(2026, 10, 3, 19, 5, tzinfo=timezone.utc),
        home=home,
        away=away,
        venue="Stade; test, annexe",
        league=SimpleNamespace(name="Ligue 1"),
        sport=SimpleNamespace(code=sport),
        group_name="",
        round_name="8e journée",
    )


class TestCalendar(unittest.TestCase):
    def render(self, *matches):
        return ical.render(
            matches, name="Mes matchs",
            generated_at=datetime(2026, 9, 22, 12, 0, tzinfo=timezone.utc))

    def test_a_match_has_a_stable_identity_and_utc_kickoff(self):
        page = self.render(match())
        self.assertIn("BEGIN:VCALENDAR\r\n", page)
        self.assertIn("UID:401@butbutbut.local\r\n", page)
        self.assertIn("DTSTART:20261003T190500Z\r\n", page)
        self.assertIn("SUMMARY:Marseille – Lyon\r\n", page)
        self.assertIn("DURATION:PT2H\r\n", page)
        self.assertTrue(page.endswith("END:VCALENDAR\r\n"))

    def test_text_values_are_escaped(self):
        page = self.render(match(home="A, B", away="C; D"))
        self.assertIn("SUMMARY:A\\, B – C\\; D", page)
        self.assertIn("LOCATION:Stade\\; test\\, annexe", page)

    def test_long_utf8_lines_are_folded_without_exceeding_75_bytes(self):
        page = self.render(match(home="Olympique " + "é" * 70))
        self.assertTrue(any(line.startswith(" ") for line in page.split("\r\n")))
        self.assertTrue(all(len(line.encode("utf-8")) <= 75
                            for line in page.split("\r\n")))

    def test_each_sport_gets_a_realistic_reserved_window(self):
        self.assertIn("DURATION:PT2H30M", self.render(match(sport="rugby")))
        self.assertIn("DURATION:PT3H", self.render(match(sport="hockey")))

    def test_an_empty_calendar_is_still_importable(self):
        page = self.render()
        self.assertNotIn("BEGIN:VEVENT", page)
        self.assertIn("X-WR-CALNAME:Mes matchs", page)


if __name__ == "__main__":
    unittest.main()
