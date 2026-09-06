import unittest

from butbutbut import espn, leagues

from helpers import event, payload


class TestCatalogue(unittest.TestCase):
    def test_the_five_big_ones_are_the_default(self):
        self.assertEqual(
            [l.slug for l in leagues.LEAGUES],
            ["fra.1", "eng.1", "esp.1", "ita.1", "ger.1"],
        )
        self.assertEqual(leagues.resolve(None), list(leagues.LEAGUES))
        self.assertEqual(leagues.resolve(""), list(leagues.LEAGUES))

    def test_catalogue_holds_the_five_plus_the_extras(self):
        self.assertEqual(len(leagues.CATALOGUE),
                         len(leagues.LEAGUES) + len(leagues.EXTRA))
        for league in leagues.CATALOGUE:
            self.assertIs(leagues.BY_SLUG[league.slug], league)

    def test_no_duplicate_slug_or_alias_in_the_catalogue(self):
        slugs = [l.slug for l in leagues.CATALOGUE]
        self.assertEqual(len(slugs), len(set(slugs)))

        seen = {}
        for league in leagues.CATALOGUE:
            for alias in league.aliases:
                self.assertNotIn(alias, seen,
                                 "alias {!r} partage par {} et {}".format(
                                     alias, seen.get(alias), league.slug))
                seen[alias] = league.slug

    def test_every_competition_is_presentable(self):
        for league in leagues.CATALOGUE:
            self.assertRegex(league.accent, r"^#[0-9a-f]{6}$")
            self.assertEqual(league.label, league.label.upper())
            self.assertFalse(league.provisional)

    def test_catalogue_lines_are_grouped(self):
        lines = leagues.catalogue_lines()
        titles = [title for title, _n, _s, _a in lines if title]
        self.assertEqual(len(titles), 2)
        rows = [row for row in lines if row[0] is None]
        self.assertEqual(len(rows), len(leagues.CATALOGUE))


class TestSelection(unittest.TestCase):
    def test_aliases(self):
        for token, slug in (("l1", "fra.1"), ("ligue1", "fra.1"),
                            ("pl", "eng.1"), ("premier league", "eng.1"),
                            ("liga", "esp.1"), ("LaLiga", "esp.1"),
                            ("seriea", "ita.1"), ("serie a", "ita.1"),
                            ("bundesliga", "ger.1"), ("de", "ger.1"),
                            ("ucl", "uefa.champions"), ("c1", "uefa.champions"),
                            ("ligue2", "fra.2"), ("l2", "fra.2"),
                            ("championship", "eng.2"), ("mls", "usa.1"),
                            ("cdm", "fifa.world"), ("facup", "eng.fa")):
            self.assertEqual([l.slug for l in leagues.resolve(token)], [slug], token)

    def test_comma_separated_list_keeps_command_line_order(self):
        chosen = leagues.resolve("bundesliga,l1,ucl")
        self.assertEqual([l.slug for l in chosen],
                         ["ger.1", "fra.1", "uefa.champions"])

    def test_duplicates_are_collapsed(self):
        self.assertEqual(len(leagues.resolve("l1,ligue1,fra.1")), 1)

    def test_all_means_the_whole_catalogue(self):
        self.assertEqual(leagues.resolve("all"), list(leagues.CATALOGUE))
        self.assertEqual(leagues.resolve("tout"), list(leagues.CATALOGUE))

    def test_big5_keyword(self):
        self.assertEqual(leagues.resolve("big5"), list(leagues.LEAGUES))

    def test_unknown_name_is_reported_with_help(self):
        with self.assertRaises(leagues.UnknownLeague) as caught:
            leagues.resolve("champions-du-monde")
        self.assertIn("--list", str(caught.exception))

    def test_describe(self):
        self.assertEqual(leagues.describe(leagues.resolve(None)),
                         "les 5 grands championnats")
        self.assertEqual(leagues.describe(leagues.resolve("l1")), "Ligue 1")
        self.assertIn("catalogue", leagues.describe(leagues.resolve("all")))
        self.assertIn("autres", leagues.describe(leagues.resolve(
            "l1,pl,liga,seriea,bundesliga,ucl,uel,ligue2")))


class TestExclusion(unittest.TestCase):
    def test_exclude_trims_the_default_five(self):
        chosen = leagues.resolve(None, exclude="liga,seriea")
        self.assertEqual([l.slug for l in chosen], ["fra.1", "eng.1", "ger.1"])

    def test_exclude_works_on_an_explicit_selection(self):
        chosen = leagues.resolve("all", exclude="mls,ligue2")
        slugs = [l.slug for l in chosen]
        self.assertNotIn("usa.1", slugs)
        self.assertNotIn("fra.2", slugs)
        self.assertIn("fra.1", slugs)

    def test_excluding_something_not_selected_changes_nothing(self):
        self.assertEqual(leagues.resolve("l1", exclude="mls"),
                         leagues.resolve("l1"))

    def test_excluding_everything_is_an_error(self):
        with self.assertRaises(leagues.NoLeagueLeft):
            leagues.resolve("l1,pl", exclude="l1,pl")

    def test_unknown_exclusion_is_reported(self):
        with self.assertRaises(leagues.UnknownLeague):
            leagues.resolve(None, exclude="nimportequoi")

    def test_selection_errors_share_a_base_class(self):
        self.assertTrue(issubclass(leagues.UnknownLeague, leagues.SelectionError))
        self.assertTrue(issubclass(leagues.NoLeagueLeft, leagues.SelectionError))


class TestAdHocCompetition(unittest.TestCase):
    """N'importe quel code ESPN doit passer, meme hors catalogue."""

    def test_a_raw_espn_slug_is_accepted(self):
        chosen = leagues.resolve("gre.1")
        self.assertEqual(len(chosen), 1)
        self.assertEqual(chosen[0].slug, "gre.1")
        self.assertTrue(chosen[0].provisional)

    def test_the_same_slug_gives_the_same_object(self):
        first = leagues.resolve("den.1")[0]
        second = leagues.resolve("den.1")[0]
        self.assertIs(first, second)

    def test_something_that_is_not_a_slug_is_refused(self):
        for token in ("ligue 42", "pl1", "!!", "fra."):
            with self.assertRaises(leagues.UnknownLeague, msg=token):
                leagues.resolve(token)

    def test_the_real_name_arrives_with_the_first_payload(self):
        league = leagues.resolve("nor.1")[0]
        self.assertTrue(league.provisional)

        raw = payload(event())
        raw["leagues"] = [{"name": "Norwegian Eliteserien",
                           "abbreviation": "Eliteserien"}]
        espn.parse(raw, league)

        self.assertEqual(league.name, "Norwegian Eliteserien")
        self.assertEqual(league.label, "ELITESERIEN")
        self.assertFalse(league.provisional)

    def test_a_catalogued_league_never_renames_itself(self):
        league = leagues.BY_SLUG["fra.1"]
        raw = payload(event())
        raw["leagues"] = [{"name": "French Ligue 1", "abbreviation": "Ligue 1"}]
        espn.parse(raw, league)
        self.assertEqual(league.name, "Ligue 1")
        self.assertEqual(league.label, "LIGUE 1")


if __name__ == "__main__":
    unittest.main()
