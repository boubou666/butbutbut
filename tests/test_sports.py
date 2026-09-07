"""Sortir du football : catalogue, URL, lecture d'un autre sport.

Le fil rouge de ce fichier est le meme que celui de la PR : ouvrir le
catalogue sans que le football perde quoi que ce soit. Chaque bloc a donc son
pendant "et le football, lui, ne bouge pas".
"""

import unittest

from butbutbut import cli, espn, i18n, journal, leagues, overlay, sports, watcher

from helpers import (bump, event, goal_detail, hockey_event, opener_for,
                     payload, rugby_detail)

LIGUE1 = leagues.BY_SLUG["fra.1"]
NHL = leagues.BY_SLUG["nhl"]
TOP14 = leagues.BY_SLUG["270559"]


def setUpModule():
    # Ces tests affirment des formulations francaises : sans cet epinglage ils
    # passeraient ici et echoueraient sur une CI anglaise.
    i18n.use("fr")


# ------------------------------------------------------------------ sports ---

class TestSports(unittest.TestCase):
    def test_the_three_sports_and_their_url_segment(self):
        self.assertEqual([sport.code for sport in sports.SPORTS],
                         ["soccer", "hockey", "rugby"])
        self.assertIs(sports.DEFAULT, sports.SOCCER)

    def test_a_sport_is_found_by_its_code_or_an_alias(self):
        for token, sport in (("soccer", sports.SOCCER), ("foot", sports.SOCCER),
                             ("football", sports.SOCCER),
                             ("hockey", sports.HOCKEY), ("glace", sports.HOCKEY),
                             ("rugby", sports.RUGBY), ("xv", sports.RUGBY),
                             ("RUGBY", sports.RUGBY)):
            self.assertIs(sports.find(token), sport, token)
        self.assertIsNone(sports.find("curling"))

    def test_football_is_the_vocabulary_floor(self):
        # Le football ne redit rien : c'est lui, le socle.
        self.assertEqual(sports.SOCCER.overrides, {})
        self.assertEqual(sports.SOCCER.title_key("title_goal"), "title_goal")

    def test_hockey_renames_only_what_differs(self):
        # Un but de hockey est un but ; ce sont ses pauses qui n'en sont pas.
        self.assertEqual(sports.HOCKEY.title_key("title_goal"), "title_goal")
        self.assertEqual(sports.HOCKEY.title_key("title_halftime"),
                         "title_period_break")

    def test_rugby_has_no_goals_at_all(self):
        self.assertEqual(sports.RUGBY.title_key("title_goal"), "title_points")
        self.assertFalse(sports.RUGBY.unit_score)
        self.assertTrue(sports.SOCCER.unit_score)
        self.assertTrue(sports.HOCKEY.unit_score)

    def test_only_the_sports_that_send_off_carry_red_cards(self):
        # Le hockey punit par deux minutes de banc, pas par un carton : la
        # carte n'a rien a compter chez lui.
        self.assertTrue(sports.SOCCER.red_cards)
        self.assertTrue(sports.RUGBY.red_cards)
        self.assertFalse(sports.HOCKEY.red_cards)

    def test_the_declined_sports_say_why(self):
        for token in ("basketball", "basket", "nba"):
            self.assertTrue(sports.declined(token), token)
        self.assertIn("trente secondes", sports.declined("basketball"))
        self.assertEqual(sports.declined("hockey"), "")


# --------------------------------------------------------------- catalogue ---

class TestCatalogue(unittest.TestCase):
    def test_the_football_catalogue_is_untouched(self):
        for league in leagues.CATALOGUE:
            self.assertIs(league.sport, sports.SOCCER, league.slug)

    def test_the_other_sports_live_beside_it(self):
        # Tout le football d'abord - masculin puis feminin -, les autres
        # sports ensuite : c'est l'ordre de --list, et celui de all-sports.
        self.assertEqual(list(leagues.FULL_CATALOGUE),
                         list(leagues.FOOTBALL) + list(leagues.OTHER_SPORTS))
        self.assertTrue(leagues.HOCKEY_LEAGUES)
        self.assertTrue(leagues.RUGBY_LEAGUES)
        for league in leagues.HOCKEY_LEAGUES:
            self.assertIs(league.sport, sports.HOCKEY)
        for league in leagues.RUGBY_LEAGUES:
            self.assertIs(league.sport, sports.RUGBY)

    def test_everything_is_presentable_in_every_sport(self):
        for league in leagues.FULL_CATALOGUE:
            self.assertRegex(league.accent, r"^#[0-9a-f]{6}$", league.slug)
            self.assertEqual(league.label, league.label.upper(), league.slug)
            self.assertFalse(league.provisional, league.slug)
            self.assertTrue(league.name.strip(), league.slug)

    def test_no_duplicate_reference_or_alias_across_sports(self):
        refs = [league.ref for league in leagues.FULL_CATALOGUE]
        self.assertEqual(len(refs), len(set(refs)))
        # Les cles internes du watcher sont les `slug` par `ref` ; deux sports
        # qui partageraient un code ESPN doivent rester distinguables.
        slugs = [league.slug for league in leagues.FULL_CATALOGUE]
        self.assertEqual(len(slugs), len(set(slugs)))

        seen = {}
        for league in leagues.FULL_CATALOGUE:
            for alias in league.aliases:
                self.assertNotIn(alias, seen,
                                 "alias {!r} partage par {} et {}".format(
                                     alias, seen.get(alias), league.ref))
                seen[alias] = league.ref

    def test_no_alias_shadows_a_sport_keyword(self):
        """Un alias qui s'appellerait "rugby" volerait le mot-cle du sport."""
        reserved = set()
        for sport in sports.SPORTS:
            reserved.add(sport.code)
            reserved.update(sport.aliases)
        for league in leagues.FULL_CATALOGUE:
            for alias in league.aliases:
                self.assertNotIn(alias, reserved, league.ref)

    def test_the_reference_is_what_one_would_type(self):
        self.assertEqual(LIGUE1.ref, "fra.1")          # le foot est sous-entendu
        self.assertEqual(NHL.ref, "hockey:nhl")
        self.assertEqual(TOP14.ref, "rugby:270559")

    def test_a_translated_competition_name_follows_the_language(self):
        six = leagues.BY_SLUG["180659"]
        i18n.use("fr")
        self.assertEqual(six.label, "TOURNOI DES SIX NATIONS")
        i18n.use("it")
        self.assertEqual(six.label, "SEI NAZIONI")
        i18n.use("fr")


# --------------------------------------------------------------- selection ---

class TestSelection(unittest.TestCase):
    def test_the_default_is_still_football_and_nothing_else(self):
        chosen = leagues.resolve(None)
        self.assertEqual(chosen, list(leagues.LEAGUES))
        for league in chosen:
            self.assertIs(league.sport, sports.SOCCER)

    def test_all_stays_inside_football(self):
        """Le point le plus important du lot : `all` n'a pas change de sens."""
        chosen = leagues.resolve("all")
        self.assertEqual(chosen, list(leagues.CATALOGUE))
        self.assertNotIn(NHL, chosen)
        for league in chosen:
            self.assertIs(league.sport, sports.SOCCER)

    def test_all_sports_takes_everything(self):
        for token in ("all-sports", "tous-sports", "everything"):
            self.assertEqual(leagues.resolve(token),
                             list(leagues.FULL_CATALOGUE), token)

    def test_a_sport_name_takes_that_sport_whole(self):
        self.assertEqual(leagues.resolve("hockey"), list(leagues.HOCKEY_LEAGUES))
        self.assertEqual(leagues.resolve("rugby"), list(leagues.RUGBY_LEAGUES))
        self.assertEqual(leagues.resolve("foot"), list(leagues.CATALOGUE))

    def test_competitions_of_two_sports_mix_freely(self):
        chosen = leagues.resolve("l1,nhl,top14")
        self.assertEqual([l.ref for l in chosen],
                         ["fra.1", "hockey:nhl", "rugby:270559"])
        self.assertEqual([s.code for s in leagues.sports_of(chosen)],
                         ["soccer", "hockey", "rugby"])

    def test_aliases_of_the_new_competitions(self):
        for token, ref in (("nhl", "hockey:nhl"), ("lnh", "hockey:nhl"),
                           ("top14", "rugby:270559"), ("t14", "rugby:270559"),
                           ("6nations", "rugby:180659"),
                           ("tournoi", "rugby:180659"),
                           ("urc", "rugby:270557"), ("rwc", "rugby:164205"),
                           ("270559", "rugby:270559")):
            self.assertEqual([l.ref for l in leagues.resolve(token)], [ref], token)

    def test_exclusion_works_across_sports(self):
        chosen = leagues.resolve("all-sports", exclude="hockey")
        self.assertNotIn(NHL, chosen)
        self.assertIn(TOP14, chosen)
        self.assertIn(LIGUE1, chosen)

    def test_describe_names_the_whole_of_a_sport(self):
        self.assertEqual(leagues.describe(leagues.resolve(None)),
                         "les 5 grands championnats")
        self.assertIn("catalogue", leagues.describe(leagues.resolve("all")))
        self.assertIn("tous les sports",
                      leagues.describe(leagues.resolve("all-sports")))
        self.assertIn("rugby", leagues.describe(leagues.resolve("rugby")))

    def test_the_listing_shows_football_alone_unless_asked(self):
        football = leagues.catalogue_lines()
        self.assertEqual(len([t for t, _n, _s, _a in football if t]), 2)
        self.assertEqual(len([r for r in football if r[0] is None]),
                         len(leagues.CATALOGUE))

        everything = leagues.catalogue_lines(everything=True)
        self.assertEqual(len([t for t, _n, _s, _a in everything if t]), 5)
        self.assertEqual(len([r for r in everything if r[0] is None]),
                         len(leagues.FULL_CATALOGUE))


class TestAdHocAcrossSports(unittest.TestCase):
    """L'echappatoire : un code ESPN inconnu, dans n'importe quel sport."""

    def test_a_bare_slug_is_still_football(self):
        chosen = leagues.resolve("gre.1")[0]
        self.assertEqual(chosen.slug, "gre.1")
        self.assertIs(chosen.sport, sports.SOCCER)
        self.assertTrue(chosen.provisional)

    def test_a_prefixed_slug_aims_at_another_sport(self):
        for token, code, slug in (
                ("hockey:mens-college-hockey", "hockey", "mens-college-hockey"),
                ("hockey/mens-college-hockey", "hockey", "mens-college-hockey"),
                ("rugby:270565", "rugby", "270565")):
            chosen = leagues.resolve(token)[0]
            self.assertEqual(chosen.sport.code, code, token)
            self.assertEqual(chosen.slug, slug, token)
            self.assertTrue(chosen.provisional, token)

    def test_the_same_prefixed_slug_gives_the_same_object(self):
        self.assertIs(leagues.resolve("rugby:270566")[0],
                      leagues.resolve("rugby:270566")[0])

    def test_a_prefixed_slug_that_is_catalogued_is_not_reinvented(self):
        self.assertIs(leagues.resolve("hockey:nhl")[0], NHL)

    def test_an_unknown_sport_is_refused_with_the_list(self):
        with self.assertRaises(leagues.UnknownLeague) as caught:
            leagues.resolve("curling:1")
        for sport in sports.SPORTS:
            self.assertIn(sport.code, str(caught.exception))

    def test_a_declined_sport_says_why_rather_than_just_no(self):
        for token in ("basketball", "basketball:nba"):
            with self.assertRaises(leagues.DeclinedSport) as caught:
                leagues.resolve(token)
            self.assertIn("trente secondes", str(caught.exception), token)
        self.assertTrue(issubclass(leagues.DeclinedSport, leagues.SelectionError))

    def test_the_real_name_still_arrives_with_the_first_payload(self):
        league = leagues.resolve("hockey:collegiale")[0]
        raw = payload(hockey_event())
        raw["leagues"] = [{"name": "NCAA Men's Ice Hockey", "abbreviation": "NCAAH"}]
        espn.parse(raw, league)
        self.assertEqual(league.name, "NCAA Men's Ice Hockey")
        self.assertEqual(league.label, "NCAAH")


# --------------------------------------------------------------------- URL ---

class TestUrls(unittest.TestCase):
    """Le sport est un segment d'URL, et c'est tout ce qu'il est ici."""

    def urls_for(self, league):
        seen = []

        def opener(url, _timeout):
            seen.append(url)
            return b'{"events": []}'

        espn.scoreboard(league, opener=opener)
        espn.catalogue(league, opener=opener)
        return seen

    def test_football_urls_have_not_moved(self):
        self.assertEqual(self.urls_for(LIGUE1), [
            "https://site.api.espn.com/apis/site/v2/sports/soccer/fra.1/scoreboard",
            "https://site.api.espn.com/apis/site/v2/sports/soccer/fra.1/teams",
        ])

    def test_the_other_sports_change_only_the_first_segment(self):
        self.assertEqual(self.urls_for(NHL), [
            "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard",
            "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/teams",
        ])
        self.assertEqual(self.urls_for(TOP14), [
            "https://site.api.espn.com/apis/site/v2/sports/rugby/270559/scoreboard",
            "https://site.api.espn.com/apis/site/v2/sports/rugby/270559/teams",
        ])

    def test_fetch_without_a_sport_is_football(self):
        seen = []

        def opener(url, _timeout):
            seen.append(url)
            return b"{}"

        espn.fetch("fra.1", opener=opener)
        espn.fetch("nhl", opener=opener, sport=sports.HOCKEY)
        self.assertIn("/soccer/fra.1/", seen[0])
        self.assertIn("/hockey/nhl/", seen[1])

    def test_the_demo_logo_follows_the_sport(self):
        self.assertEqual(espn.logo_url("170"),
                         "https://a.espncdn.com/i/teamlogos/soccer/500/170.png")
        self.assertEqual(espn.logo_url("bos", sports.HOCKEY),
                         "https://a.espncdn.com/i/teamlogos/nhl/500/bos.png")
        self.assertEqual(espn.logo_url("25922", sports.RUGBY),
                         "https://a.espncdn.com/i/teamlogos/rugby/teams/500/25922.png")


# ------------------------------------------------------------------ hockey ---

class TestHockeyPayload(unittest.TestCase):
    """Ce que la source publie vraiment pour le hockey : le score, et rien de plus."""

    def parse(self, **kwargs):
        return espn.parse(payload(hockey_event(**kwargs)), NHL)[0]

    def test_scores_are_read_even_written_as_integers(self):
        match = self.parse(home_score=3, away_score=2)
        self.assertEqual((match.home_score, match.away_score), (3, 2))
        self.assertEqual(match.score_line(),
                         "Boston Bruins 3 - 2 Montreal Canadiens")
        self.assertTrue(match.live)

    def test_no_action_is_published_so_none_is_invented(self):
        match = self.parse()
        self.assertEqual(match.plays, [])
        self.assertEqual(match.red_cards, [])

    def test_a_clock_and_a_period_instead_of_a_minute(self):
        match = self.parse(clock="12:07", period=2)
        self.assertEqual(match.clock, "12:07")
        self.assertEqual(match.phase, espn.PLAYING)

    def test_the_intermission_is_a_break_not_a_halftime(self):
        for name in ("STATUS_END_PERIOD", "STATUS_INTERMISSION",
                     "STATUS_END_OF_PERIOD"):
            self.assertEqual(
                espn.phase_of("in", name, sports.HOCKEY), espn.HALFTIME, name)
            # Le meme nom ne dit rien au football : chaque sport n'ajoute que
            # ses propres marqueurs.
            self.assertEqual(
                espn.phase_of("in", name, sports.SOCCER), espn.PLAYING, name)

    def test_an_unknown_break_name_is_silence_never_a_wrong_card(self):
        # Le repli est le match en cours : aucune carte, plutot qu'une fausse.
        self.assertEqual(espn.phase_of("in", "STATUS_ENTRACTE", sports.HOCKEY),
                         espn.PLAYING)

    def test_final_in_overtime_is_still_final(self):
        match = self.parse(state="post", status_name="STATUS_FINAL",
                           detail="Final/OT", period=4)
        self.assertEqual(match.phase, espn.FINAL)
        self.assertTrue(match.finished)

    def test_a_goal_is_a_goal_in_every_language(self):
        source = {"payload": payload(hockey_event(home_score=1, away_score=1))}
        guard = watcher.Watcher([NHL], opener=opener_for(source))
        guard.prime()
        source["payload"] = bump(source["payload"], "home")
        goal = guard.refresh(NHL)[0]

        self.assertEqual(goal.kind, watcher.GOAL)
        self.assertEqual(goal.delta, 1)
        self.assertEqual(goal.title, "BUT !")
        self.assertEqual(watcher.title_of(watcher.GOAL, lang="de",
                                          sport=sports.HOCKEY), "TOR!")
        # Pas d'action publiee : la carte se rabat sur la minute, sans inventer
        # de buteur.
        self.assertIsNone(goal.play)
        self.assertEqual(goal.detail_line(), "Minute 12:07")

    def test_the_break_and_the_end_speak_hockey(self):
        for lang, pause, fin, debut in (
                ("fr", "FIN DU TIERS-TEMPS", "FIN DU MATCH", "MISE AU JEU"),
                ("en", "END OF PERIOD", "FINAL", "PUCK DROP"),
                ("de", "DRITTELPAUSE", "SPIELENDE", "ANSPIEL")):
            self.assertEqual(watcher.title_of(watcher.HALFTIME, lang=lang,
                                              sport=sports.HOCKEY), pause, lang)
            self.assertEqual(watcher.title_of(watcher.FULLTIME, lang=lang,
                                              sport=sports.HOCKEY), fin, lang)
            self.assertEqual(watcher.title_of(watcher.KICKOFF, lang=lang,
                                              sport=sports.HOCKEY), debut, lang)

    def test_red_cards_switch_themselves_off(self):
        """Il n'y a pas de carton rouge au hockey : rien a desactiver a la main."""
        source = {"payload": payload(hockey_event(home_score=1))}
        guard = watcher.Watcher([NHL], opener=opener_for(source), red_cards=True)
        guard.prime()
        source["payload"] = bump(source["payload"], "home")
        events = guard.refresh(NHL)
        self.assertEqual([e.kind for e in events], [watcher.GOAL])


# ------------------------------------------------------------------- rugby ---

class TestRugbyPayload(unittest.TestCase):
    """Le rugby publie tout, mais sans un seul drapeau."""

    def parse(self, details):
        raw = payload(event(details=details, home_score=19, away_score=14))
        return espn.parse(raw, TOP14)[0]

    def test_the_scoring_actions_and_what_they_are_worth(self):
        match = self.parse((
            rugby_detail("H1", "try", "8'", "L. Carter", index=1),
            rugby_detail("H1", "conversion", "9'", "T. Ramos", index=2),
            rugby_detail("A1", "penalty goal", "11'", "T. Edmed", index=3),
            rugby_detail("A1", "drop goal", "45'", "D. Willemse", index=4),
        ))
        self.assertEqual([(p.kind_key, p.points) for p in match.plays],
                         [("try", 5), ("conversion", 2),
                          ("penalty_goal", 3), ("drop_goal", 3)])
        self.assertEqual([p.summary() for p in match.plays], [
            "Essai de L. Carter (8')",
            "Transformation de T. Ramos (9')",
            "Penalite de T. Edmed (11')",
            "Drop de D. Willemse (45')",
        ])

    def test_what_is_not_a_score_is_ignored(self):
        match = self.parse((
            rugby_detail("H1", "player substituted", "15'", "W. Skelton", index=1),
            rugby_detail("H1", "substitute on", "15'", "J. van Tonder", index=2),
            rugby_detail("H1", "start of first half", "1'", "", index=3),
            rugby_detail("H1", "end of second half", "81'", "", index=4),
            rugby_detail("A1", "yellow card", "22'", "E. Dumortier", index=5),
            rugby_detail("A1", "drop goal-missed", "19'", "G. Prisciantelli",
                         index=6),
        ))
        self.assertEqual(match.plays, [])
        # Le carton jaune est une exclusion temporaire : ce n'est pas une
        # expulsion, et le confondre donnerait une carte qui ment.
        self.assertEqual(match.red_cards, [])

    def test_the_red_card_is_the_one_card_that_counts(self):
        match = self.parse((
            rugby_detail("H1", "try", "8'", "L. Carter", index=1),
            rugby_detail("A1", "red card", "72'", "T. Latu", index=2),
        ))
        self.assertEqual([p.scorer for p in match.plays], ["L. Carter"])
        self.assertEqual([p.scorer for p in match.red_cards], ["T. Latu"])
        card = match.red_cards[0]
        self.assertTrue(card.red_card)
        self.assertEqual(card.points, 0)
        self.assertEqual(card.summary(), "Carton rouge pour T. Latu (72')")
        # Et il se compte du bon cote : c'est ce que la carte dessine.
        self.assertEqual(match.red_card_tally(), (0, 1))

    def test_keys_stay_stable_across_two_reads(self):
        details = (rugby_detail("H1", "try", index=1),
                   rugby_detail("H1", "conversion", index=2))
        first, second = self.parse(details), self.parse(details)
        self.assertEqual([p.key for p in first.plays],
                         [p.key for p in second.plays])
        self.assertNotEqual(first.plays[0].key, first.plays[1].key)

    def test_a_try_moves_the_score_by_five_and_says_so(self):
        source = {"payload": payload(event(home_score=14, away_score=14))}
        guard = watcher.Watcher([TOP14], opener=opener_for(source))
        guard.prime()
        source["payload"] = bump(
            source["payload"], "home", by=5,
            details=(rugby_detail("H1", "try", "63'", "A. Dupont", index=1),))
        essai = guard.refresh(TOP14)[0]

        self.assertEqual(essai.kind, watcher.GOAL)
        self.assertEqual(essai.delta, 5)
        self.assertEqual(essai.title, "ESSAI !")
        self.assertEqual(essai.detail_line(), "Essai de A. Dupont")
        self.assertEqual(essai.score_line, "Angers 19 - 14 Stade Rennais")

    def test_a_try_and_its_conversion_in_one_reading_announce_the_try(self):
        """Sept points d'un coup : c'est l'essai l'evenement, pas la transformation."""
        source = {"payload": payload(event(home_score=0, away_score=0))}
        guard = watcher.Watcher([TOP14], opener=opener_for(source))
        guard.prime()
        source["payload"] = bump(
            source["payload"], "home", by=7,
            details=(rugby_detail("H1", "try", "8'", "L. Carter", index=1),
                     rugby_detail("H1", "conversion", "9'", "T. Ramos", index=2)))
        essai = guard.refresh(TOP14)[0]

        self.assertEqual(essai.delta, 7)
        self.assertEqual(essai.title, "ESSAI !")
        self.assertEqual(essai.play.scorer, "L. Carter")

    def test_points_without_an_action_still_say_how_many(self):
        source = {"payload": payload(event(home_score=0, away_score=0))}
        guard = watcher.Watcher([TOP14], opener=opener_for(source))
        guard.prime()
        source["payload"] = bump(source["payload"], "away", by=3)
        points = guard.refresh(TOP14)[0]

        self.assertIsNone(points.play)
        self.assertEqual(points.title, "POINTS !")
        self.assertEqual(points.detail_line(), "+3 points")
        for lang, attendu in (("en", "+3 points"), ("es", "+3 puntos"),
                              ("it", "+3 punti"), ("de", "+3 Punkte")):
            self.assertEqual(points.detail_parts(lang=lang)[0][0], attendu, lang)

    def test_the_titles_hold_up_in_the_five_languages(self):
        for lang, essai, transf, points in (
                ("fr", "ESSAI !", "TRANSFORMATION", "POINTS !"),
                ("en", "TRY!", "CONVERSION", "POINTS!"),
                ("es", "ENSAYO!", "CONVERSION", "PUNTOS!"),
                ("it", "META!", "TRASFORMAZIONE", "PUNTI!"),
                ("de", "VERSUCH!", "ERHOEHUNG", "PUNKTE!")):
            match = self.parse((
                rugby_detail("H1", "try", index=1),
                rugby_detail("H1", "conversion", index=2)))
            self.assertEqual(watcher.title_of(watcher.GOAL, match.plays[0],
                                              lang=lang), essai, lang)
            self.assertEqual(watcher.title_of(watcher.GOAL, match.plays[1],
                                              lang=lang), transf, lang)
            self.assertEqual(watcher.title_of(watcher.GOAL, lang=lang,
                                              sport=sports.RUGBY), points, lang)

    def test_removed_points_are_not_a_disallowed_goal(self):
        source = {"payload": payload(event(home_score=0, away_score=7))}
        guard = watcher.Watcher([TOP14], opener=opener_for(source))
        guard.prime()
        source["payload"] = bump(source["payload"], "away", by=-7)
        retire = guard.refresh(TOP14)[0]
        self.assertEqual(retire.kind, watcher.CANCELLED)
        self.assertEqual(retire.title, "POINTS RETIRES")
        self.assertEqual(retire.detail_line(), "Score corrige")

    def test_the_full_time_card_lists_what_each_action_was(self):
        source = {"payload": payload(event(
            home_score=7, away_score=3, state="in",
            status_name="STATUS_SECOND_HALF",
            details=(rugby_detail("H1", "try", "8'", "L. Carter", index=1),
                     rugby_detail("H1", "conversion", "9'", "T. Ramos", index=2),
                     rugby_detail("A1", "penalty goal", "11'", "T. Edmed",
                                  index=3))))}
        guard = watcher.Watcher([TOP14], opener=opener_for(source))
        guard.prime()
        source["payload"] = bump(source["payload"], "home", by=0)
        source["payload"]["events"][0]["competitions"][0]["status"]["type"] = {
            "state": "post", "name": "STATUS_FULL_TIME", "shortDetail": "FT"}
        fin = guard.refresh(TOP14)[0]

        self.assertEqual(fin.kind, watcher.FULLTIME)
        self.assertEqual(fin.extra_lines(), [
            "Angers : L. Carter (essai) 8', T. Ramos (transf.) 9'",
            "Stade Rennais : T. Edmed (pen.) 11'",
        ])

    def test_rugby_keeps_the_football_phase_words(self):
        # Le rugby a bien deux mi-temps : rien a redire de ce cote.
        self.assertEqual(watcher.title_of(watcher.HALFTIME, lang="fr",
                                          sport=sports.RUGBY), "MI-TEMPS")
        self.assertEqual(watcher.title_of(watcher.KICKOFF, lang="fr",
                                          sport=sports.RUGBY), "COUP D'ENVOI")


# ----------------------------------------------------- le foot ne perd rien --

class TestFootballIsUntouched(unittest.TestCase):
    """La non-regression, dite explicitement plutot que deduite."""

    def one_goal(self, details=(), by=1):
        source = {"payload": payload(event(home_score=1, away_score=0))}
        guard = watcher.Watcher([LIGUE1], opener=opener_for(source))
        guard.prime()
        source["payload"] = bump(source["payload"], "away", by=by,
                                 details=details)
        return guard.refresh(LIGUE1)[0]

    def test_a_goal_is_still_a_goal(self):
        goal = self.one_goal(
            details=(goal_detail("A1", "58'", "A. Kalimuendo", index=3),))
        self.assertEqual(goal.title, "BUT !")
        self.assertEqual(goal.delta, 1)
        self.assertEqual(goal.detail_line(), "But de A. Kalimuendo")
        self.assertEqual(goal.play.points, 1)
        self.assertEqual(goal.play.kind_key, "goal")

    def test_own_goals_and_penalties_keep_their_wording(self):
        own = self.one_goal(
            details=(goal_detail("A1", "17'", "J. Lefort", own_goal=True,
                                 index=4),))
        self.assertEqual(own.title, "BUT CONTRE SON CAMP")
        self.assertEqual(own.detail_line(), "But contre son camp de J. Lefort")

        penalty = self.one_goal(
            details=(goal_detail("A1", "61'", "C. Arcus", penalty=True, index=5),))
        self.assertEqual(penalty.title, "BUT SUR PENALTY")
        self.assertEqual(penalty.play.points, 1)

    def test_a_goal_without_an_action_still_shows_the_minute(self):
        # Le football n'a pas de "+1 points" : ce serait dire ce que tout le
        # monde sait deja.
        goal = self.one_goal()
        self.assertIsNone(goal.play)
        self.assertEqual(goal.detail_line(), "Minute 35'")

    def test_a_play_built_the_old_way_behaves_the_old_way(self):
        play = espn.Play("k", "1", "35'", "Goal", "C. Arcus", False, False, False)
        self.assertEqual(play.kind_key, "goal")
        self.assertEqual(play.points, 1)
        self.assertEqual(play.summary(), "But de C. Arcus (35')")
        self.assertEqual(play.short_mark(), "")

        card = espn.Play("k", "1", "62'", "Red Card", "J. Lefort", False, False,
                         False, red_card=True)
        self.assertEqual(card.kind_key, "red_card")
        self.assertEqual(card.points, 0)
        self.assertEqual(card.prefix_for(), "Carton rouge pour ")

    def test_the_football_phases_have_not_moved(self):
        for state, name, expected in (
                ("pre", "STATUS_SCHEDULED", espn.SCHEDULED),
                ("in", "STATUS_FIRST_HALF", espn.PLAYING),
                ("in", "STATUS_HALFTIME", espn.HALFTIME),
                ("post", "STATUS_FULL_TIME", espn.FINAL)):
            self.assertEqual(espn.phase_of(state, name), expected, name)
            self.assertEqual(espn.phase_of(state, name, sports.SOCCER),
                             expected, name)


# ---------------------------------------------------------------- journal ----

class TestJournalReadsEverySport(unittest.TestCase):
    """`--today` relit le journal : il doit y reconnaitre les autres sports."""

    def entry_for(self, line):
        return journal.parse_line("2026-09-06 21:14:07  " + line)

    def test_a_hockey_goal_reads_like_a_football_goal(self):
        entry = self.entry_for(
            "BUT [NHL] Boston Bruins 3 - 2 Montreal Canadiens pour Boston "
            "Bruins (12:07)")
        self.assertEqual(entry.kind, watcher.GOAL)
        self.assertEqual(entry.league, "NHL")
        self.assertEqual(entry.minute, "12:07")

    def test_the_rugby_headings_are_recognised(self):
        for head in ("ESSAI", "TRANSFORMATION", "PENALITE", "DROP", "POINTS"):
            entry = self.entry_for(
                head + " [Top 14] La Rochelle 30 - 27 Stade Toulousain pour "
                "La Rochelle - Essai de A. Dupont (63')")
            self.assertIsNotNone(entry, head)
            self.assertEqual(entry.kind, watcher.GOAL, head)
            self.assertEqual(entry.scorer, "A. Dupont", head)

        retire = self.entry_for(
            "POINTS RETIRES [Top 14] La Rochelle 25 - 27 Stade Toulousain pour "
            "La Rochelle - Score corrige (64')")
        self.assertEqual(retire.kind, watcher.CANCELLED)

    def test_the_football_headings_that_used_to_slip_through(self):
        """Un csc et un penalty s'annoncent autrement que "BUT", et le
        relecteur ne les reconnaissait pas : ils manquaient a `--today`.
        """
        for head, detail in (("BUT CONTRE SON CAMP", "But contre son camp de J. Lefort"),
                             ("BUT SUR PENALTY", "Penalty de C. Arcus")):
            entry = self.entry_for(
                "{} [Ligue 1] Angers 1 - 0 Stade Rennais pour Angers - {} "
                "(17')".format(head, detail))
            self.assertIsNotNone(entry, head)
            self.assertEqual(entry.kind, watcher.GOAL, head)
            self.assertTrue(entry.scorer, head)

    def test_what_the_watcher_writes_is_what_the_parser_reads(self):
        # Le vrai contrat, refait pour le rugby : la ligne sort de log_line().
        source = {"payload": payload(event(home_score=14, away_score=14))}
        guard = watcher.Watcher([TOP14], opener=opener_for(source))
        guard.prime()
        source["payload"] = bump(
            source["payload"], "home", by=5,
            details=(rugby_detail("H1", "try", "63'", "A. Dupont", index=7),))
        essai = guard.refresh(TOP14)[0]

        entry = self.entry_for(essai.log_line())
        self.assertIsNotNone(entry, essai.log_line())
        self.assertEqual(entry.kind, watcher.GOAL)
        self.assertEqual(entry.league, "Top 14")
        self.assertEqual(entry.scorer, "A. Dupont")
        self.assertEqual(entry.minute, "63'")

    def test_the_journal_stays_in_french_whatever_the_cards_say(self):
        i18n.use("de")
        try:
            source = {"payload": payload(event(home_score=0, away_score=0))}
            guard = watcher.Watcher([TOP14], opener=opener_for(source))
            guard.prime()
            source["payload"] = bump(
                source["payload"], "home", by=5,
                details=(rugby_detail("H1", "try", "63'", "A. Dupont", index=8),))
            essai = guard.refresh(TOP14)[0]
            self.assertEqual(essai.title, "VERSUCH!")
            self.assertTrue(essai.log_line().startswith("ESSAI ["),
                            essai.log_line())
        finally:
            i18n.use("fr")


# ----------------------------------------------------------------- cartes ----

class TestDemoCards(unittest.TestCase):
    def test_each_sport_shows_its_own_teams_and_its_own_words(self):
        hockey = overlay.Card.demo(NHL)
        self.assertEqual(hockey.league, "NHL")
        self.assertEqual(hockey.title, "BUT !")
        self.assertIn("Bruins", hockey.home)
        self.assertTrue(hockey.detail.startswith("But de "))

        rugby = overlay.Card.demo(TOP14)
        self.assertEqual(rugby.league, "TOP 14")
        self.assertEqual(rugby.title, "ESSAI !")
        self.assertTrue(rugby.detail.startswith("Essai de "))
        self.assertEqual(rugby.accent, TOP14.accent)

    def test_every_catalogued_competition_has_a_demo_card(self):
        for league in leagues.FULL_CATALOGUE:
            card = overlay.Card.demo(league)
            self.assertEqual(card.league, league.label, league.ref)
            self.assertTrue(card.title.strip(), league.ref)
            self.assertTrue(card.detail.strip(), league.ref)


# ------------------------------------------------------------ vocabulaire ---

class TestVocabulary(unittest.TestCase):
    """Le catalogue de mots doit tenir dans les cinq langues, sans trou."""

    def test_every_override_points_at_a_real_key(self):
        reference = i18n.MESSAGES[i18n.FALLBACK]
        for sport in sports.SPORTS:
            for generic, replacement in sport.overrides.items():
                self.assertIn(generic, reference, sport.code)
                self.assertIn(replacement, reference,
                              "{} renvoie sur une cle inexistante".format(sport.code))

    def test_points_added_keeps_its_hole(self):
        # Sans {points}, la carte de rugby dirait "+ points".
        for lang in i18n.LANGUAGES:
            self.assertIn("{points}", i18n.MESSAGES[lang]["points_added"], lang)

    def test_every_action_has_its_word_its_preposition_and_its_short_form(self):
        for key in ("goal", "penalty", "own_goal", "try", "conversion",
                    "penalty_goal", "drop_goal"):
            for lang in i18n.LANGUAGES:
                catalogue = i18n.MESSAGES[lang]
                self.assertIn(key, catalogue, "{}/{}".format(lang, key))
                preposition = catalogue.get(key + "_by", "")
                self.assertTrue(preposition.endswith(" "),
                                "{}/{}_by ne finit pas par une espace".format(lang, key))

    def test_the_rugby_words_are_really_translated(self):
        # Deux langues peuvent coincider, pas les cinq : ce serait le signe
        # d'un catalogue copie sans traduire.
        for key in ("title_try", "title_conversion", "title_points"):
            valeurs = {i18n.MESSAGES[lang][key] for lang in i18n.LANGUAGES}
            self.assertGreater(len(valeurs), 2, key)


# ------------------------------------------------------------ ligne de cmd ---

class TestCommandLine(unittest.TestCase):
    def setUp(self):
        # cli.main() rappelle i18n.use() avec ce que dit le fichier de
        # configuration de la machine : sur un poste francais il repose le
        # francais, sur la CI il pose l'anglais. Sans ce rangement, la langue
        # partirait avec lui et les classes suivantes affirmeraient des
        # libelles francais dans la langue du hasard.
        self.addCleanup(i18n.use, "fr")

    def test_the_listing_shows_the_other_sports(self):
        import io
        import contextlib

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(cli.main(["--list"]), 0)
        text = out.getvalue()
        self.assertIn("NHL", text)
        self.assertIn("Top 14", text)
        self.assertIn("Ligue 1", text)
        self.assertIn("all-sports", text)

    def test_a_declined_sport_leaves_with_an_explanation(self):
        import io
        import contextlib

        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(cli.main(["--leagues", "basketball:nba"]), 2)
        self.assertIn("trente secondes", err.getvalue())


if __name__ == "__main__":
    unittest.main()
