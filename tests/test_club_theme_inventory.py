"""Comparaison de l'inventaire de clubs, sans parler au reseau."""

from datetime import datetime, timezone
import importlib.util
import os
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SPEC = importlib.util.spec_from_file_location(
    "club_theme_inventory",
    os.path.join(ROOT, "tools", "club_theme_inventory.py"))
inventory = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(inventory)


def team(team_id, name, league="fra.1", league_name="Ligue 1"):
    return {
        "id": str(team_id), "name": name, "short_name": name,
        "slug": "team." + str(team_id), "league": league,
        "league_name": league_name, "country": "france", "women": False,
        "asset": "clubs/{}.png".format(team_id),
    }


class TestClubThemeUpdates(unittest.TestCase):
    def test_only_new_espn_ids_need_a_new_illustration(self):
        saved = [team(1, "Ancien nom"), team(2, "Club relegue")]
        current = [team(1, "Nouveau nom"), team(3, "Club promu")]
        added, removed = inventory.changes(saved, current)
        self.assertEqual([row["id"] for row in added], ["3"])
        self.assertEqual([row["id"] for row in removed], ["2"])

    def test_the_issue_body_contains_the_actionable_inventory(self):
        report = inventory.update_report(
            [team(1, "Club stable")],
            [team(1, "Club stable"), team(3, "Club promu")],
            datetime(2026, 9, 20, 8, 30, tzinfo=timezone.utc))
        self.assertIn("Nouvelles equipes a illustrer (1)", report)
        self.assertIn("Club promu", report)
        self.assertIn("`3`", report)
        self.assertIn("butbutbut/assets/clubs/3.png", report)
        self.assertIn("2026-09-20 08:30 UTC", report)

    def test_no_change_produces_an_explicit_empty_report(self):
        rows = [team(1, "Club stable")]
        report = inventory.update_report(rows, list(rows))
        self.assertIn("Nouvelles equipes a illustrer (0)", report)
        self.assertIn("_Aucune._", report)


if __name__ == "__main__":
    unittest.main()
