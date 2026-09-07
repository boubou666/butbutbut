import unittest

from butbutbut import espn, i18n, leagues, sports

from helpers import event, goal_detail, payload


def setUpModule():
    # describe() est traduit depuis la 1.6.0 : sans cet epinglage ces tests
    # suivraient la langue de la machine et echoueraient sur la CI, qui est en
    # anglais. Meme raison que dans test_cli, test_watcher et test_overlay.
    i18n.use("fr")

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


class TestDesignates(unittest.TestCase):
    """Le pendant sans effet de bord de find(), pour les noms de fichiers son."""

    def test_a_code_a_name_or_an_alias_all_designate_the_league(self):
        for token in ("fra.1", "l1", "ligue1", "Ligue 1", "france"):
            found = leagues.designates(token)
            self.assertIsNotNone(found, token)
            self.assertEqual(found.slug, "fra.1", token)

    def test_a_word_that_is_not_a_competition_gives_nothing(self):
        for token in ("om", "corne", "contre", ""):
            self.assertIsNone(leagues.designates(token), token)

    def test_an_unknown_espn_code_is_not_opened_on_the_way(self):
        # find() ouvrirait la competition ; ici on ne fait que repondre.
        slug = "gre.2"
        self.assertNotIn(slug, leagues.BY_SLUG)
        self.assertIsNone(leagues.designates(slug))
        self.assertNotIn(slug, leagues.BY_SLUG)


# ------------------------------------------------------- football feminin ----

def words_of(league) -> set:
    """Tout ce qui, tape a --leagues, doit designer cette competition-la.

    matches_token() accepte quatre choses en plus des alias : le code, la
    reference prefixee du sport, le nom et l'etiquette. Un test des seuls
    alias laisserait donc passer une collision sur un nom.
    """
    return ({league.slug, league.ref, league.name.lower(), league.label.lower()}
            | set(league.aliases))


def mirror_slugs(slug) -> list:
    """Les codes masculins du catalogue que ce code feminin reflete.

    La source marque le feminin d'un `w`, tantot segment a part ("eng.w.1"),
    tantot colle au segment suivant ("uefa.wchampions", "fifa.wworldq.uefa").
    On retire l'un ou l'autre et on garde ce que le catalogue reconnait :
    aucune table ecrite a la main, donc rien a oublier le jour ou une entree
    s'ajoute.
    """
    parts = slug.split(".")
    candidates = []
    for index, part in enumerate(parts):
        rest = parts[index + 1:]
        if part == "w":
            candidates.append(".".join(parts[:index] + rest))
        elif len(part) > 1 and part.startswith("w"):
            candidates.append(".".join(parts[:index] + [part[1:]] + rest))
    return [code for code in candidates if code in leagues.BY_SLUG]


class TestWomenCatalogue(unittest.TestCase):
    """Le miroir feminin du catalogue : voir l'en-tete de leagues.py."""

    def test_they_are_football_like_the_others(self):
        self.assertTrue(leagues.WOMEN)
        for league in leagues.WOMEN:
            self.assertIs(league.sport, sports.SOCCER, league.slug)
            self.assertFalse(league.provisional, league.slug)
            self.assertRegex(league.accent, r"^#[0-9a-f]{6}$", league.slug)
            self.assertEqual(league.label, league.label.upper(), league.slug)
            self.assertEqual(league.ref, league.slug, league.slug)

    def test_football_is_the_two_catalogues_side_by_side(self):
        self.assertEqual(list(leagues.FOOTBALL),
                         list(leagues.CATALOGUE) + list(leagues.WOMEN))
        for league in leagues.WOMEN:
            self.assertIs(leagues.BY_SLUG[league.slug], league)

    def test_no_word_designates_two_competitions(self):
        """Deux a deux, sur tout le catalogue : aucun mot ne peut hesiter.

        C'est le seul controle qui vaille pour une convention d'alias. Une
        liste ecrite a la main dirait ce qu'on a pense a verifier ; celui-ci
        dit ce qui est vrai, y compris pour les entrees ecrites demain.
        """
        seen = {}
        for league in leagues.FULL_CATALOGUE:
            for word in words_of(league):
                self.assertNotIn(
                    word, seen,
                    "{!r} designe a la fois {} et {}".format(
                        word, seen.get(word), league.slug))
                seen[word] = league.slug

    def test_no_keyword_is_shadowed_by_a_competition(self):
        # _expand() lit les mots-cles AVANT le catalogue : un alias qui
        # s'appellerait "feminines" ne serait jamais atteint.
        words = set()
        for league in leagues.FULL_CATALOGUE:
            words |= words_of(league)
        for keyword in (leagues._ALL + leagues._EVERYTHING
                        + leagues._BIG_FIVE + leagues._WOMEN):
            self.assertNotIn(keyword, words, keyword)

    def test_every_colour_is_its_own(self):
        # Une couleur partagee ferait deux competitions identiques sur la
        # carte, la seule chose qui les distingue etant l'en-tete.
        accents = [league.accent for league in leagues.FULL_CATALOGUE]
        self.assertEqual(len(accents), len(set(accents)))

    def test_the_mens_word_plus_an_f_opens_the_womens_competition(self):
        """La convention, verifiee sur les paires que la source elle-meme relie.

        Deux exigences, et la seconde compte autant que la premiere : au moins
        un mot masculin suffixe d'un `f` ouvre la competition feminine, et
        aucun n'ouvre autre chose. Sans elle, "plf" pourrait un jour designer
        une competition sans rapport, et la regle ne serait plus une regle.
        """
        pairs = 0
        for woman in leagues.WOMEN:
            for slug in mirror_slugs(woman.slug):
                pairs += 1
                man = leagues.BY_SLUG[slug]
                derived = [alias + "f" for alias in man.aliases]
                opened = [word for word in derived
                          if leagues.designates(word) is woman]
                self.assertTrue(
                    opened,
                    "{} ne repond a aucun alias de {} suffixe d'un f".format(
                        woman.slug, slug))
                for word in derived:
                    found = leagues.designates(word)
                    self.assertIn(found, (None, woman),
                                  "{!r} designe {}".format(word, found))
        # Le garde-fou du garde-fou : si la derivation cessait de trouver quoi
        # que ce soit, le test passerait sans rien avoir verifie.
        self.assertGreaterEqual(pairs, 9)

    def test_every_womens_competition_answers_to_an_f(self):
        for league in leagues.WOMEN:
            self.assertTrue([a for a in league.aliases if a.endswith("f")],
                            league.slug)

    def test_the_source_publishes_no_italian_or_german_equivalent(self):
        # Ce n'est pas un oubli : `ita.w.1` et `ger.w.1` n'existent pas chez
        # la source, alors que la Serie A et la Bundesliga sont au catalogue.
        # Le jour ou ils apparaitront, ce test dira de les ajouter.
        for slug in ("ita.w.1", "ger.w.1"):
            self.assertNotIn(slug, leagues.BY_SLUG)


class TestWomenSelection(unittest.TestCase):
    def test_the_aliases_resolve(self):
        for token, slug in (("wsl", "eng.w.1"), ("plf", "eng.w.1"),
                            ("ligaf", "esp.w.1"), ("l1f", "fra.w.1"),
                            ("d1f", "fra.w.1"), ("nwsl", "usa.nwsl"),
                            ("uclf", "uefa.wchampions"),
                            ("uwcl", "uefa.wchampions"),
                            ("c1f", "uefa.wchampions"),
                            ("uelf", "uefa.w.europa"),
                            ("nationsf", "uefa.w.nations"),
                            ("cdmf", "fifa.wwc"),
                            ("qualifsf", "fifa.wworldq.uefa"),
                            ("facupf", "eng.w.fa"),
                            ("leaguecupf", "eng.w.league_cup"),
                            ("reina", "esp.copa_de_la_reina"),
                            ("concacaff", "concacaf.w.champions_cup")):
            self.assertEqual([l.slug for l in leagues.resolve(token)], [slug],
                             token)

    def test_the_mens_words_have_not_moved(self):
        # Le vrai piege du chantier : "l1" doit rester la Ligue 1, "liga"
        # LaLiga, "ucl" la C1 masculine. Un mot qui change de sens selon la
        # competition suivie ne se rattrape jamais.
        for token, slug in (("l1", "fra.1"), ("liga", "esp.1"),
                            ("pl", "eng.1"), ("ucl", "uefa.champions"),
                            ("cdm", "fifa.world"), ("facup", "eng.fa"),
                            ("copa", "esp.copa_del_rey"), ("mls", "usa.1"),
                            ("concacaf", "concacaf.champions")):
            self.assertEqual([l.slug for l in leagues.resolve(token)], [slug],
                             token)

    def test_the_keyword_takes_them_all(self):
        for token in ("feminines", "feminin", "footf", "women", "womens"):
            self.assertEqual(leagues.resolve(token), list(leagues.WOMEN), token)

    def test_all_stays_the_mens_catalogue(self):
        """L'arbitrage : `all` ne bouge pas d'une competition.

        Une mise a jour ne change pas ce qu'on suit - c'est deja la raison
        pour laquelle `all` ne prend pas le hockey.
        """
        for token in ("all", "tout", "foot"):
            chosen = leagues.resolve(token)
            self.assertEqual(chosen, list(leagues.CATALOGUE), token)
            for league in leagues.WOMEN:
                self.assertNotIn(league, chosen, token)

    def test_all_sports_takes_them_like_the_rest(self):
        chosen = leagues.resolve("all-sports")
        self.assertEqual(chosen, list(leagues.FULL_CATALOGUE))
        for league in leagues.WOMEN:
            self.assertIn(league, chosen)

    def test_they_mix_with_the_mens_catalogue(self):
        chosen = leagues.resolve("l1,l1f,ucl,uclf")
        self.assertEqual([l.slug for l in chosen],
                         ["fra.1", "fra.w.1", "uefa.champions",
                          "uefa.wchampions"])

    def test_exclusion_works_on_the_group(self):
        chosen = leagues.resolve("all-sports", exclude="feminines")
        self.assertEqual(chosen, list(leagues.CATALOGUE)
                         + list(leagues.OTHER_SPORTS))

    def test_describe_names_the_group(self):
        self.assertEqual(leagues.describe(leagues.resolve("feminines")),
                         "tout le football feminin ({} competitions)".format(
                             len(leagues.WOMEN)))

    def test_the_keyword_is_a_competition_word_for_table(self):
        # --table trie ses jetons en "competition" et "equipe" : sans ca,
        # `--table feminines` chercherait un club de ce nom.
        for token in ("feminines", "footf", "wsl", "l1f"):
            self.assertTrue(leagues.names_a_league(token), token)

    def test_a_sound_file_may_be_named_after_them(self):
        # designates() est ce que lit `--sound-for wsl=corne.wav` et ce que
        # lit un fichier `wsl.mp3` : il ne s'interesse pas a ce que `all`
        # emporte, seulement a ce qui est du football.
        self.assertIs(leagues.designates("wsl"), leagues.BY_SLUG["eng.w.1"])
        self.assertIs(leagues.designates("uclf"),
                      leagues.BY_SLUG["uefa.wchampions"])
        self.assertIsNone(leagues.designates("wslf"))


class TestWomenPayload(unittest.TestCase):
    """La source les publie comme les autres : charge utile figee, ici.

    Relevee sur `soccer/eng.w.1` - meme forme, memes cles, memes drapeaux
    qu'un match de Premier League. C'est tout le fond du chantier : il n'y
    avait rien a ecrire du cote de la lecture.
    """

    PAYLOAD = payload(event(
        match_id="1", home="Arsenal", away="Chelsea",
        home_score=2, away_score=1, state="in", detail="67'", clock="67'",
        details=[goal_detail("H1", minute="12'", scorer="A. Russo"),
                 goal_detail("A1", minute="40'", scorer="S. Kaneryd", index=1),
                 goal_detail("H1", minute="66'", scorer="B. Mead",
                             penalty=True, index=2)]))

    def test_a_womens_match_reads_like_any_other(self):
        league = leagues.BY_SLUG["eng.w.1"]
        matches = espn.parse(self.PAYLOAD, league)
        self.assertEqual(len(matches), 1)

        match = matches[0]
        self.assertEqual((match.home, match.away), ("Arsenal", "Chelsea"))
        self.assertEqual((match.home_score, match.away_score), (2, 1))
        self.assertEqual([play.scorer for play in match.plays],
                         ["A. Russo", "S. Kaneryd", "B. Mead"])
        self.assertTrue(match.plays[2].penalty)

    def test_the_card_says_which_competition(self):
        # Une equipe feminine porte le nom de son club masculin (voir
        # teams.py) : l'en-tete de la carte est ce qui separe les deux, et
        # c'est pour ca qu'elle porte un F.
        self.assertEqual(leagues.BY_SLUG["eng.w.1"].label, "WSL")
        self.assertEqual(leagues.BY_SLUG["fra.w.1"].label, "PREMIERE LIGUE F")
        self.assertEqual(leagues.BY_SLUG["fra.1"].label, "LIGUE 1")

    def test_a_catalogued_womens_league_never_renames_itself(self):
        league = leagues.BY_SLUG["fra.w.1"]
        raw = payload(event())
        raw["leagues"] = [{"name": "French Premiere Ligue",
                           "abbreviation": "Premiere Ligue"}]
        espn.parse(raw, league)
        self.assertEqual(league.name, "Premiere Ligue F")
        self.assertEqual(league.label, "PREMIERE LIGUE F")


if __name__ == "__main__":
    unittest.main()
