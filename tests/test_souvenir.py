import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from butbutbut import espn, leagues, souvenir
from helpers import event, goal_detail, payload


class TestStory(unittest.TestCase):
    def match(self):
        details = [
            goal_detail("H1", "12'", "A. Un", index=1),
            goal_detail("A1", "48'", "B. Deux", index=2),
            goal_detail("H1", "90+2'", "C. Trois", index=3),
        ]
        return espn.parse(payload(event(home="Angers", away="Rennes",
                                        home_score=2, away_score=1,
                                        state="post", detail="FT",
                                        details=details,
                                        home_stats={"possessionPct": "54.5",
                                                    "totalShots": "14",
                                                    "shotsOnTarget": "6",
                                                    "wonCorners": "5"},
                                        away_stats={"possessionPct": "45.5",
                                                    "totalShots": "9",
                                                    "shotsOnTarget": "3",
                                                    "wonCorners": "2"},
                                        venue_country="France")),
                          leagues.BY_SLUG["fra.1"])[0]

    def test_the_timeline_rebuilds_the_score(self):
        story = souvenir.from_match(self.match(), created_at=100)
        self.assertEqual(story["home_score"], 2)
        self.assertEqual(story["away_score"], 1)
        self.assertEqual([(g["home_score"], g["away_score"])
                          for g in story["goals"]], [(1, 0), (1, 1), (2, 1)])
        self.assertEqual(story["venue_country"], "France")
        self.assertEqual(story["motif"], "france")
        self.assertEqual(story["home_stats"]["totalShots"], 14.0)
        self.assertEqual(story["away_stats"]["wonCorners"], 2.0)

    def test_the_html_is_autonomous_and_escaped(self):
        story = souvenir.from_match(self.match(), created_at=100)
        story["home"] = "A < B"
        page = souvenir.render(story)
        self.assertIn("A &lt; B", page)
        self.assertNotIn("https://", page)
        self.assertIn("data:image/png;base64,", page)
        self.assertIn('class="postcard"', page)
        self.assertIn("Enregistrer en PNG", page)
        self.assertIn("canvas.toBlob", page)
        self.assertIn("01 JANVIER 1970 · FRANCE", page)
        self.assertIn("mask-image:radial-gradient", page)
        self.assertIn(".home .scorer", page)
        self.assertIn(".away .scorer", page)
        self.assertIn("Possession", page)
        self.assertIn("Tirs cadrés", page)
        self.assertIn("Corners", page)

    def test_a_known_club_replaces_the_country_atlas(self):
        match = self.match()
        match.home_id = "176"
        story = souvenir.from_match(match, created_at=100)
        page = souvenir.render(story)
        self.assertEqual(story["club_theme_id"], "176")
        self.assertIn("background-size:contain", page)

    def test_the_store_replaces_the_same_match(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "stories.json"
            store = souvenir.Store(path)
            first = souvenir.from_match(self.match(), created_at=100)
            store.add(first)
            second = dict(first, home_score=3)
            store.add(second)
            self.assertEqual(len(souvenir.read(path)), 1)
            self.assertEqual(store.latest("angers")["home_score"], 3)

    def test_the_store_enriches_a_legacy_story_from_the_current_board(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "stories.json"
            match = self.match()
            story = souvenir.from_match(match, created_at=100)
            story["home_stats"] = {"wonCorners": 5.0}
            story.pop("away_stats")
            match.home_stats = {"totalShots": 14.0}
            store = souvenir.Store(path)
            store.add(story)

            self.assertTrue(store.enrich([match]))
            saved = souvenir.read(path)[0]
            self.assertEqual(saved["home_stats"]["totalShots"], 14.0)
            self.assertEqual(saved["home_stats"]["wonCorners"], 5.0)
            self.assertEqual(saved["away_stats"]["wonCorners"], 2.0)
            self.assertFalse(store.enrich([match]))


class TestContexts(unittest.TestCase):
    def test_score_contexts_do_not_guess_the_future(self):
        from butbutbut import watcher
        self.assertEqual(watcher.context_of("home", 1, 0, 1), watcher.OPENING)
        self.assertEqual(watcher.context_of("away", 1, 1, 1), watcher.EQUALIZER)
        self.assertEqual(watcher.context_of("home", 2, 1, 1), watcher.GO_AHEAD)
        self.assertEqual(watcher.context_of("home", 3, 1, 1),
                         watcher.EXTENDS_LEAD)
        self.assertEqual(watcher.context_of("away", 3, 2, 1),
                         watcher.CLOSES_GAP)


if __name__ == "__main__":
    unittest.main()
