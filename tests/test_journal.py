import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from butbutbut import journal, leagues, watcher

from helpers import bump, event, goal_detail, opener_for, payload

LIGUE1 = leagues.BY_SLUG["fra.1"]

DAY = "2026-09-06"

# Un journal fabrique : des buts, du bruit autour, et un jour de moins.
LOG = """\
2026-09-05 22:10:04  BUT [Ligue 1] Nice 1 - 0 Lens pour Nice - But de G. Laborde (12')
2026-09-06 18:41:21  demarrage (pid 3752) - les 5 championnats - releve toutes les 25s
2026-09-06 18:41:21  15 match(s) au programme, 6 en cours, 3 a venir
2026-09-06 18:42:03  COUP D'ENVOI [Ligue 1] Angers 0 - 0 Stade Rennais (0')
2026-09-06 18:43:27  BUT [Premier League] Arsenal 2 - 1 Chelsea pour Arsenal - But de M. Odegaard (50')
2026-09-06 18:44:02  Bundesliga injoignable (timeout) - nouvel essai dans 50s
2026-09-06 18:51:10  BUT [Ligue 1] Angers 1 - 0 Stade Rennais pour Angers - Penalty de C. Arcus (61')
2026-09-06 18:52:44  BUT ANNULE [Ligue 1] Angers 0 - 0 Stade Rennais pour Angers - Score corrige (62')
2026-09-06 19:02:00  BUT [Bundesliga] Bayer 04 Leverkusen 1 - 1 Bayern pour Bayer 04 Leverkusen - But de P. Schick (77')
2026-09-06 19:30:00  FIN DU MATCH [Ligue 1] Angers 1 - 0 Stade Rennais (90+3')
"""


def log_file(tmp, content=LOG):
    path = Path(tmp) / "butbutbut.log"
    path.write_text(content, encoding="utf-8")
    return path


class TestParseLine(unittest.TestCase):
    def test_a_goal_is_read_back_whole(self):
        entry = journal.parse_line(
            "2026-09-06 18:43:27  BUT [Premier League] Arsenal 2 - 1 Chelsea "
            "pour Arsenal - But de M. Odegaard (50')")
        self.assertEqual(entry.day, "2026-09-06")
        self.assertEqual(entry.time, "18:43:27")
        self.assertEqual(entry.kind, watcher.GOAL)
        self.assertEqual(entry.league, "Premier League")
        self.assertEqual(entry.home, "Arsenal")
        self.assertEqual(entry.away, "Chelsea")
        self.assertEqual(entry.home_score, 2)
        self.assertEqual(entry.away_score, 1)
        self.assertEqual(entry.team, "Arsenal")
        self.assertEqual(entry.scorer, "M. Odegaard")
        self.assertEqual(entry.minute, "50'")
        self.assertEqual(entry.score_line(), "Arsenal 2 - 1 Chelsea")
        self.assertTrue(entry.goal)

    def test_a_team_name_with_digits_is_not_mistaken_for_the_score(self):
        entry = journal.parse_line(
            "2026-09-06 19:02:00  BUT [Bundesliga] Bayer 04 Leverkusen 1 - 1 "
            "Bayern pour Bayer 04 Leverkusen - But de P. Schick (77')")
        self.assertEqual(entry.home, "Bayer 04 Leverkusen")
        self.assertEqual(entry.away, "Bayern")
        self.assertEqual(entry.home_score, 1)

    def test_a_cancelled_goal_is_read_but_marked(self):
        entry = journal.parse_line(
            "2026-09-06 18:52:44  BUT ANNULE [Ligue 1] Angers 0 - 0 Stade "
            "Rennais pour Angers - Score corrige (62')")
        self.assertEqual(entry.kind, watcher.CANCELLED)
        self.assertFalse(entry.goal)
        self.assertEqual(entry.scorer, "")
        self.assertEqual(entry.detail, "Score corrige")

    def test_a_goal_without_scorer_is_still_a_goal(self):
        # La source publie ses actions en retard : le buteur manque parfois.
        entry = journal.parse_line(
            "2026-09-06 18:43:27  BUT [Ligue 1] Angers 1 - 0 Stade Rennais "
            "pour Angers")
        self.assertEqual(entry.team, "Angers")
        self.assertEqual(entry.scorer, "")
        self.assertEqual(entry.detail, "")
        self.assertEqual(entry.minute, "")

    def test_everything_that_is_not_a_goal_is_ignored(self):
        for line in ("2026-09-06 18:41:21  demarrage (pid 3752) - les 5 champ",
                     "2026-09-06 18:42:03  COUP D'ENVOI [Ligue 1] A 0 - 0 B (0')",
                     "2026-09-06 19:30:00  FIN DU MATCH [Ligue 1] A 1 - 0 B",
                     "2026-09-06 18:44:02  Bundesliga injoignable (timeout)",
                     "           en cours : [Ligue 1] Angers 0 - 0 Rennes",
                     "BUT [Ligue 1] Angers 1 - 0 Rennes pour Angers",
                     ""):
            self.assertIsNone(journal.parse_line(line), line)

    def test_what_the_watcher_writes_is_what_the_parser_reads(self):
        # Le vrai contrat : la ligne vient de Event.log_line(), pas d'un
        # fichier fabrique a la main. Si le format bouge, ce test tombe.
        source = {"payload": payload(event(state="in", home_score=1))}
        guard = watcher.Watcher([LIGUE1], opener=opener_for(source))
        guard.prime()
        source["payload"] = bump(
            source["payload"], "away",
            details=(goal_detail("A1", "58'", "A. Kalimuendo", index=3),))
        goal = guard.refresh(LIGUE1)[0]

        entry = journal.parse_line("2026-09-06 18:43:27  " + goal.log_line())
        self.assertEqual(entry.kind, watcher.GOAL)
        self.assertEqual(entry.league, "Ligue 1")
        self.assertEqual(entry.team, "Stade Rennais")
        self.assertEqual(entry.scorer, "A. Kalimuendo")
        self.assertEqual(entry.minute, "58'")
        self.assertEqual(entry.score_line(), goal.score_line)


class TestGoalsOfTheDay(unittest.TestCase):
    def test_only_the_day_asked_for(self):
        with TemporaryDirectory() as tmp:
            found = journal.goals(log_file(tmp), DAY)
        self.assertEqual([e.time for e in found],
                         ["18:43:27", "18:51:10", "18:52:44", "19:02:00"])

    def test_another_day_is_read_the_same_way(self):
        with TemporaryDirectory() as tmp:
            found = journal.goals(log_file(tmp), "2026-09-05")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].scorer, "G. Laborde")

    def test_a_day_without_a_single_goal(self):
        with TemporaryDirectory() as tmp:
            self.assertEqual(journal.goals(log_file(tmp), "1998-07-12"), [])

    def test_a_missing_journal_is_not_an_error(self):
        with TemporaryDirectory() as tmp:
            self.assertEqual(journal.goals(Path(tmp) / "jamais.log", DAY), [])

    def test_a_broken_line_does_not_lose_the_others(self):
        content = LOG.replace("Arsenal 2 - 1 Chelsea", "Arsenal - Chelsea")
        with TemporaryDirectory() as tmp:
            found = journal.goals(log_file(tmp, content), DAY)
        self.assertEqual(len(found), 3)

    def test_grouping_follows_the_order_of_the_first_goal(self):
        with TemporaryDirectory() as tmp:
            grouped = journal.by_league(journal.goals(log_file(tmp), DAY))
        self.assertEqual([name for name, _ in grouped],
                         ["Premier League", "Ligue 1", "Bundesliga"])
        self.assertEqual(len(grouped[1][1]), 2)


if __name__ == "__main__":
    unittest.main()
