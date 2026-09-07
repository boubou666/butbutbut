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


# Un journal a cheval sur deux mois, avec ce qu'il faut de VAR : deux buts de
# la meme equipe dans le meme match, par deux buteurs differents, puis une
# annulation. Seul le dernier des deux doit sauter.
SPAN = """\
2026-08-30 20:05:00  BUT [Ligue 1] Nice 1 - 0 Lens pour Nice - But de G. Laborde (12')
2026-08-31 18:00:00  demarrage (pid 12) - les 5 championnats
2026-08-31 20:10:00  BUT [Ligue 1] Angers 1 - 0 Stade Rennais pour Angers - But de C. Arcus (20')
2026-08-31 20:15:00  BUT ANNULE [Ligue 1] Angers 0 - 0 Stade Rennais pour Angers - Score corrige (21')
2026-09-01 19:00:00  BUT [Premier League] Arsenal 1 - 0 Chelsea pour Arsenal - But de M. Odegaard (30')
2026-09-01 19:30:00  BUT [Premier League] Arsenal 2 - 0 Chelsea pour Arsenal - But de B. Saka (55')
2026-09-01 19:40:00  BUT ANNULE [Premier League] Arsenal 1 - 0 Chelsea pour Arsenal - Score corrige (56')
2026-09-02 21:00:00  BUT [Bundesliga] Bayer 04 Leverkusen 1 - 1 Bayern pour Bayer 04 Leverkusen - But de P. Schick (77')
"""


class TestWindows(unittest.TestCase):
    """La meme lecture, parametree par une fenetre de dates."""

    def read(self, since=None, until=None, content=SPAN):
        with TemporaryDirectory() as tmp:
            return journal.goals_between(log_file(tmp, content), since, until)

    def test_a_window_takes_its_two_bounds(self):
        found = self.read("2026-08-31", "2026-09-01")
        self.assertEqual([e.scorer for e in found],
                         ["C. Arcus", "", "M. Odegaard", "B. Saka", ""])

    def test_a_window_crosses_the_end_of_a_month(self):
        # Le filtre compare des chaines : "2026-09-01" doit tomber dans une
        # fenetre ouverte le 31 aout, ce qu'un filtre par prefixe raterait.
        found = self.read("2026-08-31", "2026-09-02")
        self.assertEqual(sorted({e.day for e in found}),
                         ["2026-08-31", "2026-09-01", "2026-09-02"])

    def test_a_window_open_on_both_sides_is_the_whole_journal(self):
        self.assertEqual(len(self.read()), 7)

    def test_a_window_open_on_one_side_only(self):
        self.assertEqual(len(self.read(since="2026-09-01")), 4)
        self.assertEqual(len(self.read(until="2026-08-30")), 1)

    def test_a_window_before_the_journal_is_empty(self):
        self.assertEqual(self.read("1998-07-01", "1998-07-12"), [])

    def test_a_day_is_a_window_of_one_day(self):
        with TemporaryDirectory() as tmp:
            path = log_file(tmp, SPAN)
            self.assertEqual([e.time for e in journal.goals(path, "2026-09-01")],
                             [e.time for e in journal.goals_between(
                                 path, "2026-09-01", "2026-09-01")])

    def test_an_empty_journal_gives_nothing(self):
        self.assertEqual(self.read(content=""), [])

    def test_a_missing_journal_gives_nothing(self):
        with TemporaryDirectory() as tmp:
            self.assertEqual(journal.goals_between(Path(tmp) / "jamais.log"), [])

    def test_lines_from_another_version_are_skipped_without_a_word(self):
        # Ce que le journal peut contenir d'une version passee ou future : on
        # n'en lit rien, et surtout on ne perd pas les lignes d'a cote.
        content = SPAN + "\n".join((
            "2026-09-02 21:05:00  BUT {Bundesliga} Bayern 1 - 2 Leverkusen",
            "2026-09-02 21:06:00  BUT [Bundesliga] Bayern deux - un Leverkusen",
            "2026-09-02 21:07:00  GOAL [Bundesliga] Bayern 1 - 2 Leverkusen pour Bayern",
            "02/09/2026 21:08  BUT [Bundesliga] Bayern 1 - 2 Leverkusen pour Bayern",
            "\x00\x01 pas du texte",
            "",
        ))
        self.assertEqual(len(self.read(content=content)), 7)

    def test_days_come_grouped_in_the_order_of_the_journal(self):
        grouped = journal.by_day(self.read())
        self.assertEqual([day for day, _ in grouped],
                         ["2026-08-30", "2026-08-31", "2026-09-01",
                          "2026-09-02"])
        self.assertEqual(len(grouped[2][1]), 3)


class TestVideoAssistant(unittest.TestCase):
    """Ce que la VAR retire doit vraiment disparaitre des comptes."""

    def entries(self, content=SPAN):
        with TemporaryDirectory() as tmp:
            return journal.goals_between(log_file(tmp, content))

    def test_an_annulment_takes_back_the_last_goal_of_that_team(self):
        kept, orphans = journal.settle(self.entries())
        self.assertEqual([e.scorer for e in kept],
                         ["G. Laborde", "M. Odegaard", "P. Schick"])
        self.assertEqual(orphans, 0)

    def test_an_annulment_does_not_touch_the_other_team(self):
        content = "\n".join((
            "2026-09-01 19:00:00  BUT [Ligue 1] Angers 1 - 0 Rennes pour "
            "Angers - But de C. Arcus (30')",
            "2026-09-01 19:20:00  BUT [Ligue 1] Angers 1 - 1 Rennes pour "
            "Rennes - But de A. Kalimuendo (44')",
            "2026-09-01 19:25:00  BUT ANNULE [Ligue 1] Angers 1 - 0 Rennes "
            "pour Rennes - Score corrige (45')",
        )) + "\n"
        kept, _orphans = journal.settle(self.entries(content))
        self.assertEqual([e.scorer for e in kept], ["C. Arcus"])

    def test_a_goal_and_its_annulment_in_the_same_window_cancel_out(self):
        with TemporaryDirectory() as tmp:
            found = journal.goals_between(log_file(tmp, SPAN), "2026-08-31",
                                          "2026-08-31")
        kept, orphans = journal.settle(found)
        self.assertEqual(len(found), 2)
        self.assertEqual(kept, [])
        self.assertEqual(orphans, 0)

    def test_an_annulment_without_its_goal_is_counted_apart(self):
        # La fenetre s'ouvre apres le but : on ne deduit pas un but au hasard,
        # on compte l'annulation a part.
        content = ("2026-09-01 00:05:00  BUT ANNULE [Ligue 1] Angers 1 - 0 "
                   "Rennes pour Rennes - Score corrige (90+4')\n")
        kept, orphans = journal.settle(self.entries(content))
        self.assertEqual(kept, [])
        self.assertEqual(orphans, 1)

        board = journal.scoreboard(self.entries(content))
        self.assertEqual((board.rows, board.confirmed, board.orphans),
                         ([], 0, 1))

    def test_the_ranking_does_not_keep_a_goal_taken_back(self):
        board = journal.scoreboard(self.entries())
        self.assertEqual(board.rows, [
            ("G. Laborde", 1, "Nice"),
            ("M. Odegaard", 1, "Arsenal"),
            ("P. Schick", 1, "Bayer 04 Leverkusen"),
        ])
        # B. Saka a marque, la VAR est passee : il n'est nulle part.
        self.assertNotIn("B. Saka", [name for name, _, _ in board.rows])
        self.assertEqual((board.signalled, board.confirmed, board.cancelled),
                         (5, 3, 2))

    def test_the_ranking_counts_and_orders(self):
        content = "\n".join(
            "2026-09-0{} 19:0{}:00  BUT [Ligue 1] Nice {} - 0 Lens pour Nice "
            "- But de {} (1{}')".format(day, day, day, scorer, day)
            for day, scorer in ((1, "G. Laborde"), (2, "G. Laborde"),
                                (3, "T. Boga"), (4, "E. Guessand"))) + "\n"
        board = journal.scoreboard(self.entries(content))
        self.assertEqual([(name, count) for name, count, _ in board.rows],
                         [("G. Laborde", 2), ("E. Guessand", 1), ("T. Boga", 1)])

    def test_a_goal_without_a_scorer_counts_without_being_attributed(self):
        content = "\n".join((
            "2026-09-01 19:00:00  BUT [Ligue 1] Nice 1 - 0 Lens pour Nice",
            "2026-09-01 19:10:00  BUT [Ligue 1] Nice 2 - 0 Lens pour Nice - "
            "But de G. Laborde (22')",
        )) + "\n"
        board = journal.scoreboard(self.entries(content))
        self.assertEqual(board.rows, [("G. Laborde", 1, "Nice")])
        self.assertEqual((board.confirmed, board.unknown), (2, 1))

    def test_an_empty_window_gives_an_empty_ranking(self):
        board = journal.scoreboard([])
        self.assertEqual(board.rows, [])
        self.assertEqual((board.signalled, board.confirmed, board.cancelled,
                          board.unknown, board.orphans), (0, 0, 0, 0, 0))


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
