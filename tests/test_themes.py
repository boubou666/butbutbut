import unittest
import struct
import json

from butbutbut import themes
from butbutbut.leagues import BY_SLUG


class Match:
    def __init__(self, country="", slug="fra.1"):
        self.venue_country = country
        self.league = BY_SLUG[slug]


class TestCountryNames(unittest.TestCase):
    def test_the_five_ui_languages_reach_the_same_drawing(self):
        for name in ("Espagne", "España", "Spanien", "Spagna", "Espanha"):
            self.assertEqual(themes.country_motif(name), "spain")

    def test_accents_and_punctuation_do_not_matter(self):
        self.assertEqual(themes.country_motif("États-Unis"), "united-states")

    def test_an_unknown_country_is_not_invented(self):
        self.assertEqual(themes.country_motif("Atlantide"), "")


class TestMatchTheme(unittest.TestCase):
    def test_the_stadium_country_wins_even_in_a_foreign_league(self):
        self.assertEqual(themes.match_motif(Match("Italia", "uefa.champions")),
                         "italy")

    def test_a_domestic_league_is_the_reliable_fallback(self):
        self.assertEqual(themes.match_motif(Match("", "ger.1")), "germany")

    def test_an_international_match_without_a_venue_gets_the_globe(self):
        self.assertEqual(themes.match_motif(Match("", "uefa.champions")),
                         "international")

    def test_an_announced_but_unknown_host_is_not_replaced_by_the_league(self):
        self.assertEqual(themes.match_motif(Match("Wales", "eng.1")),
                         "stadium")

    def test_the_demo_uses_the_same_rule(self):
        self.assertEqual(themes.league_motif(BY_SLUG["fra.1"]), "france")


class TestAtlas(unittest.TestCase):
    def test_the_bundled_png_is_the_tk_compatible_copy(self):
        data = themes.ATLAS.read_bytes()
        self.assertEqual(struct.unpack(">II", data[16:24]), (1402, 1122))
        self.assertNotIn(b"caBX", data)

    def test_the_twenty_cells_cover_the_whole_atlas(self):
        boxes = {themes.atlas_box(name, 1384, 1120)
                 for name in themes.MOTIFS}
        self.assertEqual(len(boxes), 20)
        self.assertIn((0, 0, 277, 280), boxes)
        self.assertIn((1107, 840, 1384, 1120), boxes)


class TestClubAssets(unittest.TestCase):
    def test_an_existing_club_is_addressed_by_espn_id(self):
        path = themes.club_asset("176")
        self.assertIsNotNone(path)
        self.assertEqual(path.name, "176.png")

    def test_an_unknown_or_malformed_id_uses_the_country_fallback(self):
        self.assertIsNone(themes.club_asset("999999999"))
        self.assertIsNone(themes.club_asset("../176"))

    def test_the_complete_current_collection_is_bundled(self):
        manifest = themes.ATLAS.parent / "club-themes.json"
        rows = json.loads(manifest.read_text(encoding="utf-8"))
        self.assertEqual(len(rows), 384)
        self.assertEqual(sum(bool(row["women"]) for row in rows), 68)
        for row in rows:
            path = themes.club_asset(row["id"])
            self.assertIsNotNone(path, row["name"])
            with path.open("rb") as stream:
                header = stream.read(26)
            self.assertEqual(header[:8], b"\x89PNG\r\n\x1a\n")
            self.assertEqual(struct.unpack(">II", header[16:24]), (512, 512))
            self.assertIn(header[25], (3, 6))  # PNG indexe ou RGBA


if __name__ == "__main__":
    unittest.main()
