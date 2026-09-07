import unittest

from butbutbut import espn, journal, leagues, teams, watcher

from helpers import bump, event, opener_for, payload

LIGUE1 = leagues.BY_SLUG["fra.1"]
LIGUE2 = leagues.BY_SLUG["fra.2"]

# Un catalogue reduit, ecrit comme la source le rend : (nom, court, abreviation).
CATALOGUE = [
    ("Marseille", "Marseille", "OLM"),
    ("Paris Saint-Germain", "PSG", "PSG"),
    ("Paris FC", "Paris FC", "PAR"),
    ("Lyon", "Lyon", "LYON"),
    ("Stade Rennais", "Rennes", "REN"),
    ("Real Madrid", "Real Madrid", "RMA"),
    ("Real Sociedad", "Real Sociedad", "RSO"),
    ("Real Betis", "Betis", "BET"),
    ("Villarreal", "Villarreal", "VIL"),
    ("Atletico Madrid", "Atletico", "ATM"),
    ("Manchester United", "Man United", "MAN"),
    ("Manchester City", "Man City", "MNC"),
    ("Barcelona", "Barcelona", "BAR"),
]


def hits(token):
    """Les clubs qu'un mot attrape dans le catalogue."""
    found, _orphans = teams.Filter(wanted=token).resolve(CATALOGUE)
    return sorted({club for clubs in found.values() for club in clubs})


class TestNormalisation(unittest.TestCase):
    def test_accents_and_punctuation_disappear(self):
        self.assertEqual(teams.normalize("Alaves"), "alaves")
        self.assertEqual(teams.normalize("Malaga"), "malaga")
        self.assertEqual(teams.normalize("Saint-Etienne"), "saintetienne")
        self.assertEqual(teams.normalize("Paris Saint-Germain"),
                         "parissaintgermain")
        self.assertEqual(teams.normalize("  BREST  "), "brest")

    def test_accented_source_names_are_reachable_unaccented(self):
        self.assertEqual(teams.normalize("Alavés"), "alaves")
        self.assertEqual(teams.normalize("Atlético Madrid"), "atleticomadrid")
        self.assertEqual(teams.normalize("Málaga"), "malaga")

    def test_words_are_split_on_spaces_and_dashes(self):
        self.assertEqual(teams.words("Paris Saint-Germain"),
                         ["paris", "saint", "germain"])
        self.assertEqual(teams.words("Man United"), ["man", "united"])

    def test_empty_stays_empty(self):
        self.assertEqual(teams.normalize(None), "")
        self.assertEqual(teams.words(None), [])


class TestMatching(unittest.TestCase):
    def test_full_name(self):
        self.assertEqual(hits("marseille"), ["Marseille"])

    def test_abbreviation(self):
        self.assertEqual(hits("olm"), ["Marseille"])
        self.assertEqual(hits("rma"), ["Real Madrid"])

    def test_short_name(self):
        self.assertEqual(hits("man united"), ["Manchester United"])

    def test_french_nicknames(self):
        self.assertEqual(hits("om"), ["Marseille"])
        self.assertEqual(hits("ol"), ["Lyon"])
        self.assertEqual(hits("srfc"), ["Stade Rennais"])

    def test_foreign_nicknames(self):
        self.assertEqual(hits("manu"), ["Manchester United"])
        self.assertEqual(hits("barca"), ["Barcelona"])
        self.assertEqual(hits("atleti"), ["Atletico Madrid"])

    def test_a_word_can_match_several_clubs_on_purpose(self):
        self.assertEqual(hits("real"),
                         ["Real Betis", "Real Madrid", "Real Sociedad"])
        self.assertEqual(hits("manchester"),
                         ["Manchester City", "Manchester United"])
        self.assertEqual(hits("paris"), ["Paris FC", "Paris Saint-Germain"])

    def test_a_word_inside_another_word_does_not_count(self):
        # Le bug a eviter : "real" attrapait "Villarreal".
        self.assertNotIn("Villarreal", hits("real"))
        self.assertEqual(hits("villarreal"), ["Villarreal"])

    def test_a_prefix_of_a_word_counts(self):
        self.assertEqual(hits("barce"), ["Barcelona"])
        self.assertEqual(hits("rennai"), ["Stade Rennais"])

    def test_short_tokens_only_match_exactly(self):
        # Sous 4 caracteres, un mot n'est cherche qu'a l'identique : "bar" est
        # l'abreviation de Barcelone, ce n'est pas un prefixe qui traine.
        self.assertEqual(hits("bar"), ["Barcelona"])
        self.assertEqual(hits("mnc"), ["Manchester City"])
        # Mais "man" est bien un mot entier des deux noms courts (Man United,
        # Man City) : les deux sortent, et c'est correct.
        self.assertEqual(hits("man"), ["Manchester City", "Manchester United"])

    def test_case_and_spacing_do_not_matter(self):
        self.assertEqual(hits("  MaRsEiLLe "), ["Marseille"])
        self.assertEqual(hits("PSG"), ["Paris Saint-Germain"])

    def test_unknown_word_finds_nothing(self):
        self.assertEqual(hits("marseile"), [])
        self.assertEqual(hits("nantes"), [])


class TestFilter(unittest.TestCase):
    PSG = ("Paris Saint-Germain", "PSG", "PSG")

    def match(self, home="Marseille", away="Lyon"):
        return espn.parse(payload(event(home=home, away=away)), LIGUE1)[0]

    def test_no_token_means_no_filter(self):
        empty = teams.Filter()
        self.assertFalse(empty.active)
        self.assertTrue(empty.matches(self.match()))

    def test_a_followed_team_at_home_or_away(self):
        followed = teams.Filter(wanted="om")
        self.assertTrue(followed.matches(self.match(home="Marseille")))
        self.assertTrue(followed.matches(self.match(home="Lyon", away="Marseille")))

    def test_a_match_without_the_followed_team_is_dropped(self):
        followed = teams.Filter(wanted="om")
        self.assertFalse(followed.matches(self.match(home="Lyon", away="Lens")))

    def test_several_followed_teams(self):
        followed = teams.Filter(wanted="om,psg")
        self.assertTrue(followed.matches(self.match(home=self.PSG)))
        self.assertTrue(followed.matches(self.match(home="Marseille")))
        self.assertFalse(followed.matches(self.match(home="Lens", away="Lille")))

    def test_exclusion_alone_lets_everything_else_through(self):
        blocked = teams.Filter(excluded="psg")
        self.assertTrue(blocked.active)
        self.assertTrue(blocked.matches(self.match(home="Marseille", away="Lyon")))
        self.assertFalse(blocked.matches(
            self.match(home=self.PSG, away="Lyon")))
        self.assertFalse(blocked.matches(
            self.match(home="Lyon", away=self.PSG)))

    def test_exclusion_wins_over_selection(self):
        both = teams.Filter(wanted="om,psg", excluded="psg")
        self.assertTrue(both.matches(self.match(home="Marseille")))
        self.assertFalse(both.matches(
            self.match(home="Marseille", away=self.PSG)))

    def test_the_abbreviation_of_the_match_is_enough(self):
        # Le nom affiche peut etre le nom court ; le filtre voit toutes les
        # ecritures, abreviation comprise.
        followed = teams.Filter(wanted="olm")
        self.assertTrue(followed.matches(
            self.match(home=("Marseille", "Marseille", "OLM"))))

    def test_resolve_reports_orphans(self):
        found, orphans = teams.Filter(wanted="om,nantes,psg").resolve(CATALOGUE)
        self.assertEqual(sorted(found), ["om", "psg"])
        self.assertEqual(orphans, ["nantes"])

    def test_resolve_covers_excluded_tokens_too(self):
        found, orphans = teams.Filter(wanted="om", excluded="nantes").resolve(
            CATALOGUE)
        self.assertIn("om", found)
        self.assertEqual(orphans, ["nantes"])

    def test_describe(self):
        self.assertEqual(teams.Filter().describe(), "toutes les equipes")
        self.assertIn("om", teams.Filter(wanted="om").describe())
        self.assertIn("exclues", teams.Filter(excluded="psg").describe())

    def test_a_list_works_as_well_as_a_string(self):
        self.assertEqual(teams.Filter(wanted=["om", "psg"]).wanted,
                         teams.Filter(wanted="om,psg").wanted)


class TestSpoilerFilter(unittest.TestCase):
    """Le mode sans spoiler : la meme souplesse de nommage, l'autre reponse."""

    PSG = ("Paris Saint-Germain", "PSG", "PSG")

    def match(self, home="Marseille", away="Lyon"):
        return espn.parse(payload(event(home=home, away=away)), LIGUE1)[0]

    def test_no_token_covers_nothing(self):
        # Le defaut inverse de celui de Filter : rien de demande, rien a taire.
        empty = teams.SpoilerFilter()
        self.assertFalse(empty.active)
        self.assertFalse(empty.covers(self.match()))

    def test_a_match_of_the_team_at_home_or_away(self):
        quiet = teams.SpoilerFilter("om")
        self.assertTrue(quiet.covers(self.match(home="Marseille")))
        self.assertTrue(quiet.covers(self.match(home="Lyon", away="Marseille")))

    def test_another_match_is_not_covered(self):
        quiet = teams.SpoilerFilter("om")
        self.assertFalse(quiet.covers(self.match(home="Lens", away="Lille")))

    def test_the_naming_flexibility_of_teams_is_reused(self):
        for token, home in (("om", "Marseille"), ("barca", "Barcelona"),
                            ("manu", "Manchester United"),
                            ("atletico", "Atletico Madrid"),
                            ("rennai", "Stade Rennais")):
            self.assertTrue(teams.SpoilerFilter(token).covers(
                self.match(home=home)), token)

    def test_the_abbreviation_is_enough(self):
        self.assertTrue(teams.SpoilerFilter("psg").covers(
            self.match(home=self.PSG, away="Lyon")))

    def test_several_teams(self):
        quiet = teams.SpoilerFilter("om,psg")
        self.assertTrue(quiet.covers(self.match(home=self.PSG, away="Lens")))
        self.assertTrue(quiet.covers(self.match(home="Marseille")))
        self.assertFalse(quiet.covers(self.match(home="Lens", away="Lille")))

    def test_plain_names_are_enough(self):
        # Le fichier d'etat relu par --status ne garde que le nom affiche.
        quiet = teams.SpoilerFilter("om")
        self.assertTrue(quiet.covers_names(("Marseille",), ("Lyon",)))
        self.assertTrue(quiet.covers_names(("Lyon",), ("Marseille",)))
        self.assertFalse(quiet.covers_names(("Lens",), ("Lille",)))
        self.assertFalse(teams.SpoilerFilter().covers_names(("Marseille",),
                                                            ("Lyon",)))

    def test_a_list_works_as_well_as_a_string(self):
        self.assertEqual(teams.SpoilerFilter(["om", "psg"]).wanted,
                         teams.SpoilerFilter("om,psg").wanted)

    def test_resolve_reports_orphans_like_the_other_filter(self):
        found, orphans = teams.SpoilerFilter("om,marseile").resolve(CATALOGUE)
        self.assertEqual(sorted(found), ["om"])
        self.assertEqual(orphans, ["marseile"])

    def test_describe(self):
        self.assertEqual(teams.SpoilerFilter().describe(), "aucune")
        self.assertEqual(teams.SpoilerFilter("om,psg").describe(), "om, psg")


class TestWatcherFiltering(unittest.TestCase):
    """Le filtre doit couper les evenements, pas la surveillance."""

    def goals(self, wanted=None, excluded=None, home="Marseille", away="Lyon"):
        state = {"payload": payload(event(home=home, away=away))}
        guard = watcher.Watcher(
            [LIGUE1], opener=opener_for(state),
            teams=teams.Filter(wanted, excluded) if (wanted or excluded) else None)
        guard.prime()
        state["payload"] = bump(state["payload"], "home")
        return guard.refresh(LIGUE1)

    def test_without_filter_every_goal_comes_through(self):
        self.assertEqual(len(self.goals()), 1)

    def test_a_goal_of_a_followed_team(self):
        self.assertEqual(len(self.goals(wanted="om")), 1)

    def test_a_goal_against_a_followed_team_counts_too(self):
        # Suivre l'OM, c'est aussi vouloir savoir quand l'OM encaisse.
        events = self.goals(wanted="om", home="Lyon", away="Marseille")
        self.assertEqual(len(events), 1)

    def test_a_goal_elsewhere_is_ignored(self):
        self.assertEqual(self.goals(wanted="om", home="Lens", away="Lille"), [])

    def test_an_excluded_team_is_ignored(self):
        self.assertEqual(self.goals(excluded="om"), [])

    def test_phase_cards_follow_the_filter(self):
        for home, away, expected in (("Marseille", "Lyon", 1),
                                     ("Lens", "Lille", 0)):
            state = {"payload": payload(event(home=home, away=away, state="pre"))}
            guard = watcher.Watcher([LIGUE1], opener=opener_for(state),
                                    teams=teams.Filter(wanted="om"))
            guard.prime()
            state["payload"] = payload(event(home=home, away=away, state="in"))
            self.assertEqual(len(guard.refresh(LIGUE1)), expected, home)

    def test_filtered_matches_are_still_followed(self):
        # On continue de lire tous les matchs : seul l'affichage est filtre.
        state = {"payload": payload(event(home="Lens", away="Lille"))}
        guard = watcher.Watcher([LIGUE1], opener=opener_for(state),
                                teams=teams.Filter(wanted="om"))
        guard.prime()
        self.assertEqual(len(guard.all_matches()), 1)


class TestDesignates(unittest.TestCase):
    """L'entree publique dont se sert le choix du son par nom de fichier."""

    def test_a_nickname_designates_its_club(self):
        self.assertTrue(teams.designates("om", ("Marseille", "OLM")))
        self.assertTrue(teams.designates("barca", ("Barcelona", "BAR")))

    def test_the_abbreviation_and_the_start_of_a_word_work_too(self):
        self.assertTrue(teams.designates("olm", ("Marseille", "OLM")))
        self.assertTrue(teams.designates("rennai", ("Stade Rennais", "REN")))

    def test_another_club_is_not_designated(self):
        self.assertFalse(teams.designates("psg", ("Marseille", "OLM")))
        self.assertFalse(teams.designates("corne", ("Marseille", "OLM")))


class TestWomensTeams(unittest.TestCase):
    """Une equipe feminine porte le nom de son club, et c'est voulu.

    La source ecrit "Paris Saint-Germain" dans `fra.w.1` comme dans `fra.1`,
    "Arsenal" dans la WSL comme en Premier League : releve, pas suppose. Le
    rapprochement travaillant sur les libelles, `--teams psg` attrape donc les
    deux equipes du club des qu'on suit les deux competitions.

    C'est la bonne reponse, et non un defaut a corriger : quelqu'un qui suit
    le PSG suit le PSG. Rien dans le nom ne permettrait d'ailleurs de trancher
    - il faudrait un catalogue d'equipes feminines ecrit a la main, qui
    vieillirait mal. Ce qui separe les deux cartes, c'est la competition, et
    c'est ce que l'en-tete annonce (LIGUE 1 contre PREMIERE LIGUE F).

    Et quand on ne veut qu'une des deux, `--leagues` suffit deja : suivre
    `l1f` seul ne fait pas apparaitre les buts des hommes.
    """

    WOMEN = [
        ("Paris Saint-Germain", "Paris Saint-Germain", "PSG"),
        ("Paris FC", "Paris FC", "PFC"),
        ("OL Lyonnes", "OL Lyonnes", "OLL"),
        ("Montpellier", "Montpellier", "MTP"),
    ]

    def test_a_club_word_catches_the_womens_team_too(self):
        found, orphans = teams.Filter(wanted="psg").resolve(self.WOMEN)
        self.assertEqual(orphans, [])
        self.assertEqual(found["psg"], ["Paris Saint-Germain"])

    def test_a_nickname_written_for_the_mens_club_still_lands(self):
        # "ol" est le surnom de Lyon dans teams.ALIASES : il vise "lyon", que
        # l'equipe feminine n'ecrit plus depuis qu'elle s'appelle OL Lyonnes.
        # Le prefixe de mot la rattrape quand meme, par "ol" exactement.
        found, _orphans = teams.Filter(wanted="lyonnes").resolve(self.WOMEN)
        self.assertEqual(found["lyonnes"], ["OL Lyonnes"])

    def test_the_filter_does_not_confuse_two_clubs_of_the_same_city(self):
        found, _orphans = teams.Filter(wanted="paris fc").resolve(self.WOMEN)
        self.assertEqual(found["paris fc"], ["Paris FC"])


class TestScopedWords(unittest.TestCase):
    """Une equipe bornee a une competition : `--teams ligue2:sochaux`.

    Le cas qui a amene l'ecriture : suivre les cinq grands championnats ET
    Sochaux en Ligue 2. Sans bornage, `--teams sochaux` faisait taire les cinq
    autres - ajouter un club revenait a tout perdre.
    """

    LIGUE2_TEAMS = [
        ("Sochaux", "Sochaux", "SOC"),
        ("Grenoble", "Grenoble", "GRE"),
        ("Metz", "Metz", "METZ"),
    ]

    def match(self, home="Sochaux", away="Grenoble", league=None):
        return espn.parse(payload(event(home=home, away=away)),
                          league or LIGUE2)[0]

    def test_the_prefix_is_cut_at_the_last_separator(self):
        self.assertEqual(teams.split_scope("ligue2:sochaux"),
                         ("ligue2", "sochaux"))
        self.assertEqual(teams.split_scope("hockey:nhl:rangers"),
                         ("hockey:nhl", "rangers"))
        self.assertEqual(teams.split_scope("om"), ("", "om"))

    def test_a_half_written_prefix_stays_a_team_word(self):
        # Ni "ligue2:" ni ":om" ne bornent quoi que ce soit : le jeton repart
        # entier, et sera signale comme un club introuvable.
        self.assertEqual(teams.split_scope("ligue2:"), ("", "ligue2:"))
        self.assertEqual(teams.split_scope(":om"), ("", ":om"))

    def test_a_word_carries_the_competitions_of_its_prefix(self):
        word = teams.Word("ligue2:sochaux")
        self.assertEqual(word.token, "sochaux")
        self.assertEqual(word.scope, frozenset({"fra.2"}))
        # Sans prefixe, aucun bornage - et surtout pas un ensemble vide, qui
        # voudrait dire "borne a rien du tout".
        self.assertIsNone(teams.Word("om").scope)

    def test_the_bounded_competition_keeps_only_that_club(self):
        followed = teams.Filter(wanted="ligue2:sochaux")
        self.assertTrue(followed.matches(self.match(home="Sochaux")))
        self.assertTrue(followed.matches(self.match(home="Grenoble",
                                                    away="Sochaux")))
        self.assertFalse(followed.matches(self.match(home="Grenoble",
                                                     away="Metz")))

    def test_the_other_competitions_are_left_alone(self):
        """Le coeur du sujet : un mot borne ne restreint que chez lui."""
        followed = teams.Filter(wanted="ligue2:sochaux")
        self.assertTrue(followed.matches(
            self.match(home="Lens", away="Lille", league=LIGUE1)))

    def test_a_word_without_prefix_still_rules_everywhere(self):
        followed = teams.Filter(wanted="om,ligue2:sochaux")
        self.assertTrue(followed.matches(
            self.match(home="Marseille", away="Lille", league=LIGUE1)))
        # La Ligue 1 est desormais restreinte a l'OM, elle, parce qu'un mot
        # sans prefixe la vise aussi.
        self.assertFalse(followed.matches(
            self.match(home="Lens", away="Lille", league=LIGUE1)))
        self.assertTrue(followed.matches(self.match(home="Sochaux")))

    def test_an_exclusion_can_be_bounded_too(self):
        blocked = teams.Filter(excluded="ligue2:metz")
        self.assertFalse(blocked.matches(self.match(home="Metz",
                                                    away="Sochaux")))
        # Le meme club en Ligue 1 n'a rien demande a personne.
        self.assertTrue(blocked.matches(
            self.match(home="Metz", away="Lille", league=LIGUE1)))

    def test_a_journal_line_is_bounded_by_its_label(self):
        """Une ligne relue n'a garde que l'etiquette de la carte."""
        followed = teams.Filter(wanted="ligue2:sochaux")
        entry = journal.Entry(day="2026-09-06", time="18:43:27",
                              kind=watcher.GOAL, league="LIGUE 2",
                              home="Sochaux", away="Grenoble",
                              home_score=1, away_score=0, team="Sochaux",
                              detail="But de M. Kalulu", minute="12'")
        self.assertTrue(followed.matches(entry))
        entry.home, entry.away, entry.team = "Metz", "Grenoble", "Metz"
        self.assertFalse(followed.matches(entry))

    def test_an_unknown_competition_only_keeps_the_free_words(self):
        # Rien ne dit de quelle competition il s'agit : le mot borne se tait
        # plutot que de faire disparaitre le match.
        followed = teams.Filter(wanted="ligue2:sochaux")

        class Unknown:
            home, away, league = "Sochaux", "Grenoble", ""
        self.assertTrue(followed.matches(Unknown()))

    def test_the_club_word_travels_without_its_prefix(self):
        # C'est lui que porte un fichier son : sochaux.mp3, pas ligue2.mp3.
        chosen = teams.Filter(wanted="ligue2:sochaux,om", excluded="ligue2:metz")
        self.assertEqual(chosen.team_words(), ["sochaux", "om", "metz"])

    def test_a_bounded_word_is_checked_in_its_own_competition(self):
        by_league = {"fra.1": CATALOGUE, "fra.2": self.LIGUE2_TEAMS}
        flat = CATALOGUE + self.LIGUE2_TEAMS

        found, orphans = teams.Filter(wanted="ligue2:sochaux").resolve(
            flat, by_league)
        self.assertEqual(orphans, [])
        self.assertEqual(found["ligue2:sochaux"], ["Sochaux"])

        # L'OM existe, mais pas en Ligue 2 : sans le catalogue par competition,
        # ce mot passerait pour bon et ne servirait jamais a rien.
        _found, orphans = teams.Filter(wanted="ligue2:om").resolve(
            flat, by_league)
        self.assertEqual(orphans, ["ligue2:om"])

    def test_a_prefix_that_names_nothing_is_reported(self):
        self.assertEqual(teams.Filter(wanted="ligu2:sochaux").bad_scopes(),
                         ["ligu2:sochaux"])
        self.assertEqual(teams.Filter(wanted="ligue2:sochaux").bad_scopes(), [])

    def test_a_prefix_outside_the_selection_is_reported(self):
        chosen = teams.Filter(wanted="ligue2:sochaux,om")
        self.assertEqual(chosen.outside([LIGUE1]), ["ligue2:sochaux"])
        self.assertEqual(chosen.outside([LIGUE1, LIGUE2]), [])

    def test_listing_marks_the_club_only_in_its_competition(self):
        chosen = teams.Filter(wanted="ligue2:sochaux")
        names = ("Sochaux", "Sochaux", "SOC")
        self.assertTrue(chosen.team_matches(names, LIGUE2))
        self.assertFalse(chosen.team_matches(names, LIGUE1))
        # Sans competition, la question redevient celle du vocabulaire : ce mot
        # designe-t-il ce club ? Oui, et c'est ce dont le son a besoin.
        self.assertTrue(chosen.team_matches(names))


if __name__ == "__main__":
    unittest.main()
