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


def line(text, day=DAY, clock="20:00:00"):
    """Une ligne de journal fabriquee, deja analysee."""
    entry = journal.parse_line("{} {}  {}".format(day, clock, text))
    assert entry is not None, text
    return entry


def goal(minute="20'", league="Ligue 1", home="Angers", away="Stade Rennais",
         team=None, scorer="C. Arcus", head="BUT", day=DAY, clock="20:00:00"):
    """Un but a la carte, pour eprouver survey() sans ecrire un journal entier."""
    team = home if team is None else team
    text = "{} [{}] {} 1 - 0 {} pour {} - But de {}".format(
        head, league, home, away, team, scorer)
    if minute:
        text += " ({})".format(minute)
    return line(text, day=day, clock=clock)


def cancel(league="Ligue 1", home="Angers", away="Stade Rennais", team=None,
           day=DAY, clock="20:05:00"):
    team = home if team is None else team
    return line("BUT ANNULE [{}] {} 0 - 0 {} pour {} - Score corrige".format(
        league, home, away, team), day=day, clock=clock)


class TestNatureOfAGoal(unittest.TestCase):
    """Le journal ne dit la nature d'un but que dans l'en-tete de sa ligne."""

    def test_the_head_of_the_line_is_kept(self):
        self.assertEqual(goal(head="BUT").key, "title_goal")
        self.assertEqual(goal(head="BUT SUR PENALTY").key, "title_penalty")
        self.assertEqual(goal(head="BUT CONTRE SON CAMP").key,
                         "title_own_goal")
        self.assertEqual(cancel().key, "title_cancelled")

    def test_the_rugby_heads_are_read_too(self):
        self.assertEqual(goal(head="ESSAI").key, "title_try")
        self.assertEqual(goal(head="PENALITE").key, "title_penalty_goal")
        self.assertEqual(goal(head="DROP").key, "title_drop_goal")

    def test_a_nature_is_named_with_a_word_not_a_shout(self):
        # Le titre de carte crie ("BUT SUR PENALTY !") : dans un tableau on
        # veut le mot du catalogue.
        self.assertEqual(journal.label_of("title_goal"), "But")
        self.assertEqual(journal.label_of("title_penalty"), "Penalty")
        self.assertEqual(journal.label_of("title_own_goal"),
                         "But contre son camp")
        # "POINTS !" n'a pas de mot court : on retombe sur le titre, calme.
        self.assertEqual(journal.label_of("title_points"), "Points")


class TestMinuteOfAGoal(unittest.TestCase):
    def test_a_plain_minute_is_read(self):
        self.assertEqual(goal(minute="50'").clock, (50, 0))
        self.assertEqual(goal(minute="7'").clock, (7, 0))

    def test_added_time_keeps_its_base_minute(self):
        self.assertEqual(goal(minute="90+3'").clock, (90, 3))
        self.assertEqual(goal(minute="45+2'").clock, (45, 2))

    def test_the_form_the_source_really_writes_is_read_too(self):
        # La forme d'ESPN porte une apostrophe des les deux cotes du plus. Elle
        # n'etait lue par personne, et un but dans les arrets de jeu - celui
        # qu'on retient - ne comptait donc nulle part.
        self.assertEqual(goal(minute="90'+9'").clock, (90, 9))
        self.assertEqual(goal(minute="45'+2'").clock, (45, 2))
        self.assertEqual(goal(minute="90'+11'").clock, (90, 11))

    def test_what_is_not_a_minute_of_play_is_not_read_as_one(self):
        # L'horloge d'un match de hockey, un libelle de phase, un but sans
        # minute du tout : rien de tout cela n'est une minute de jeu.
        self.assertIsNone(goal(minute="12:34").clock)
        self.assertIsNone(goal(minute="Mi-temps").clock)
        self.assertIsNone(goal(minute="").clock)
        self.assertIsNone(goal(minute="FT").clock)
        # Une apostrophe de trop reste illisible : elargir la forme acceptee
        # ne doit pas revenir a tout accepter.
        self.assertIsNone(goal(minute="90''").clock)
        self.assertIsNone(goal(minute="+3'").clock)


class TestEvenings(unittest.TestCase):
    """Une soiree n'est pas un jour de calendrier."""

    def test_a_goal_after_midnight_belongs_to_the_night_before(self):
        self.assertEqual(journal.evening_of(
            goal(day="2026-09-07", clock="00:12:00")), "2026-09-06")
        self.assertEqual(journal.evening_of(
            goal(day="2026-09-06", clock="23:50:00")), "2026-09-06")

    def test_the_morning_belongs_to_its_own_day(self):
        # 6h du matin coupe la nuit : un match d'apres est celui du jour meme.
        self.assertEqual(journal.evening_of(
            goal(day="2026-09-07", clock="06:00:00")), "2026-09-07")
        self.assertEqual(journal.evening_of(
            goal(day="2026-09-07", clock="13:30:00")), "2026-09-07")

    def test_a_match_across_midnight_is_one_evening_not_two(self):
        found = journal.survey([
            goal(day="2026-09-06", clock="23:50:00", minute="88'"),
            goal(day="2026-09-07", clock="00:12:00", minute="90+4'"),
        ])
        self.assertEqual(found.evenings, [("2026-09-06", 2)])
        self.assertEqual(found.matches, 1)

    def test_an_unreadable_stamp_keeps_its_day(self):
        entry = goal()
        entry.time = "??"
        self.assertEqual(journal.evening_of(entry), DAY)


class TestSurvey(unittest.TestCase):
    def test_an_empty_window_says_nothing_and_divides_by_nothing(self):
        found = journal.survey([])
        self.assertEqual(found.confirmed, 0)
        self.assertEqual(found.matches, 0)
        self.assertEqual(found.per_match, 0.0)
        self.assertEqual(found.leagues, [])
        self.assertEqual(found.evenings, [])
        self.assertEqual(found.natures, [])
        # L'histogramme garde son cadre : quatre-vingt-dix minutes, a zero.
        self.assertEqual(len(found.buckets), 9)
        self.assertEqual({count for _low, _high, count in found.buckets}, {0})

    def test_goals_fall_in_the_slice_a_commentator_would_name(self):
        found = journal.survey([goal(minute="1'"), goal(minute="10'"),
                                goal(minute="11'"), goal(minute="90'")])
        counts = {(low, high): count for low, high, count in found.buckets}
        self.assertEqual(counts[(1, 10)], 2)
        self.assertEqual(counts[(11, 20)], 1)
        self.assertEqual(counts[(81, 90)], 1)
        self.assertEqual(found.timed, 4)

    def test_the_histogram_always_covers_a_whole_match(self):
        """Une tranche vide est une forme : "aucun but en fin de match"."""
        found = journal.survey([goal(minute="12'")])
        self.assertEqual(found.buckets[0][:2], (1, 10))
        self.assertEqual(found.buckets[-1][:2], (81, 90))

    def test_extra_time_stretches_the_histogram(self):
        found = journal.survey([goal(minute="112'")])
        self.assertEqual(found.buckets[-1], (111, 120, 1))

    def test_added_time_stays_in_the_minute_it_belongs_to(self):
        found = journal.survey([goal(minute="90+3'")])
        counts = {(low, high): count for low, high, count in found.buckets}
        self.assertEqual(counts[(81, 90)], 1)
        self.assertEqual(found.added, 1)

    def test_a_goal_without_a_readable_minute_is_set_aside(self):
        found = journal.survey([goal(minute="50'"), goal(minute="Mi-temps")])
        self.assertEqual(found.timed, 1)
        self.assertEqual(found.untimed, 1)
        self.assertEqual(found.confirmed, 2)

    def test_the_var_takes_its_goal_out_of_every_count(self):
        found = journal.survey([
            goal(minute="50'"),
            goal(minute="70'", scorer="H. Lepaul"),
            cancel(),
        ])
        self.assertEqual(found.confirmed, 1)
        self.assertEqual(found.signalled, 2)
        self.assertEqual(found.cancelled, 1)
        self.assertEqual(found.timed, 1)
        counts = {(low, high): count for low, high, count in found.buckets}
        self.assertEqual(counts[(61, 70)], 0)       # le dernier but est parti
        self.assertEqual(counts[(41, 50)], 1)
        self.assertEqual(found.leagues, [("Ligue 1", 1)])

    def test_a_cancellation_without_a_goal_to_remove_is_counted_apart(self):
        found = journal.survey([cancel()])
        self.assertEqual(found.orphans, 1)
        self.assertEqual(found.confirmed, 0)
        self.assertEqual(found.cancelled, 1)
        # Le match a bien ete suivi : une annulation le prouve.
        self.assertEqual(found.matches, 1)

    def test_leagues_are_ranked_and_ties_are_alphabetical(self):
        found = journal.survey([
            goal(league="Ligue 1"),
            goal(league="Serie A", home="Inter", away="Torino"),
            goal(league="LaLiga", home="Girona", away="Real Madrid"),
            goal(league="Serie A", home="Inter", away="Torino",
                 clock="20:10:00"),
        ])
        self.assertEqual(found.leagues,
                         [("Serie A", 2), ("LaLiga", 1), ("Ligue 1", 1)])

    def test_evenings_are_ranked_and_ties_are_chronological(self):
        found = journal.survey([
            goal(day="2026-09-05"),
            goal(day="2026-09-06", home="Nice", away="Lens"),
            goal(day="2026-09-04", home="Lille", away="Brest"),
        ])
        self.assertEqual(found.evenings, [("2026-09-04", 1),
                                          ("2026-09-05", 1),
                                          ("2026-09-06", 1)])

    def test_the_best_evening_comes_first(self):
        found = journal.survey([
            goal(day="2026-09-05"),
            goal(day="2026-09-06", home="Nice", away="Lens"),
            goal(day="2026-09-06", home="Nice", away="Lens",
                 clock="20:30:00"),
        ])
        self.assertEqual(found.evenings[0], ("2026-09-06", 2))

    def test_the_same_fixture_on_two_evenings_makes_two_matches(self):
        found = journal.survey([goal(day="2026-09-05"),
                                goal(day="2026-09-30")])
        self.assertEqual(found.matches, 2)
        self.assertAlmostEqual(found.per_match, 1.0)

    def test_the_same_teams_in_two_competitions_make_two_matches(self):
        found = journal.survey([goal(league="Ligue 1"),
                                goal(league="Coupe de France",
                                     clock="20:30:00")])
        self.assertEqual(found.matches, 2)

    def test_natures_follow_the_catalogue_not_the_counts(self):
        found = journal.survey([
            goal(head="BUT CONTRE SON CAMP"),
            goal(head="BUT CONTRE SON CAMP", clock="20:10:00"),
            goal(head="BUT", clock="20:20:00"),
            goal(head="BUT SUR PENALTY", clock="20:30:00"),
        ])
        self.assertEqual(found.natures, [("title_goal", 1),
                                         ("title_own_goal", 2),
                                         ("title_penalty", 1)])

    def test_a_line_no_version_can_read_never_reaches_the_survey(self):
        """Le parseur la laisse tomber : survey() ne la voit jamais passer."""
        with TemporaryDirectory() as tmp:
            path = log_file(tmp, LOG + (
                "2026-09-06 21:00:00  BUUUT {Ligue 1} Angers <-> Rennes\n"))
            found = journal.survey(journal.goals(path, DAY))
        self.assertEqual(found.signalled, 3)
        self.assertEqual(found.confirmed, 2)    # la VAR en a repris un
        self.assertEqual(found.cancelled, 1)


if __name__ == "__main__":
    unittest.main()
