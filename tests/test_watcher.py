import unittest

from butbutbut import espn, i18n, leagues, teams, watcher

from helpers import (FakeClock, bump, event, goal_detail, in_minutes,
                     opener_for, payload, red_card_detail)

LIGUE1 = leagues.BY_SLUG["fra.1"]


def make_watcher(state, **kwargs):
    return watcher.Watcher([LIGUE1], opener=opener_for(state), **kwargs)


def setUpModule():
    # Ces tests affirment des formulations francaises. Sans cet epinglage ils
    # passeraient sur une machine francaise et echoueraient sur la CI, dont les
    # machines sont anglaises.
    i18n.use("fr")

class TestDetection(unittest.TestCase):
    def setUp(self):
        self.state = {"payload": payload(event(home_score=1, away_score=1))}
        self.guard = make_watcher(self.state)

    def test_first_pass_is_silent(self):
        # Sinon, lancer le daemon en pleine journee de championnat rejouerait
        # tous les buts deja marques.
        self.assertEqual(self.guard.refresh(LIGUE1), [])
        self.assertEqual(len(self.guard.matches["fra.1"]), 1)

    def test_second_pass_without_change_is_silent(self):
        self.guard.prime()
        self.assertEqual(self.guard.refresh(LIGUE1), [])

    def test_score_going_up_is_a_goal(self):
        self.guard.prime()
        self.state["payload"] = bump(self.state["payload"], "away")

        events = self.guard.refresh(LIGUE1)
        self.assertEqual(len(events), 1)
        goal = events[0]
        self.assertTrue(goal.goal)
        self.assertEqual(goal.side, "away")
        self.assertEqual(goal.team, "Stade Rennais")
        self.assertEqual(goal.opponent, "Angers")
        self.assertEqual(goal.score_line, "Angers 1 - 2 Stade Rennais")
        self.assertEqual(goal.title, "BUT !")
        self.assertIs(goal.league, LIGUE1)

    def test_goal_is_enriched_with_the_scorer(self):
        self.guard.prime()
        self.state["payload"] = bump(
            self.state["payload"], "away",
            details=(goal_detail("A1", "58'", "A. Kalimuendo", index=3),))

        goal = self.guard.refresh(LIGUE1)[0]
        self.assertEqual(goal.play.scorer, "A. Kalimuendo")
        self.assertEqual(goal.minute, "58'")
        self.assertEqual(goal.detail_line(), "But de A. Kalimuendo")
        self.assertEqual(goal.detail_parts(),
                         [("But de ", False), ("A. Kalimuendo", True)])

    def test_scorer_is_the_only_highlighted_part(self):
        self.guard.prime()
        self.state["payload"] = bump(
            self.state["payload"], "home",
            details=(goal_detail("H1", "12'", "H. Kane", index=4),))

        goal = self.guard.refresh(LIGUE1)[0]
        highlighted = [text for text, strong in goal.detail_parts() if strong]
        self.assertEqual(highlighted, ["H. Kane"])

    def test_penalty_and_own_goal_change_the_title(self):
        self.guard.prime()
        self.state["payload"] = bump(
            self.state["payload"], "home",
            details=(goal_detail("H1", "17'", "J. Lefort", own_goal=True, index=5),))
        self.assertEqual(self.guard.refresh(LIGUE1)[0].title,
                         "BUT CONTRE SON CAMP")

        self.state["payload"] = bump(
            self.state["payload"], "away",
            details=(goal_detail("A1", "58'", "K. Mbappe", penalty=True, index=6),))
        self.assertEqual(self.guard.refresh(LIGUE1)[0].title, "BUT SUR PENALTY")

    def test_goal_without_details_still_fires(self):
        # Les actions d'ESPN arrivent parfois apres le score : le but ne doit
        # pas attendre le nom du buteur.
        self.guard.prime()
        self.state["payload"] = bump(self.state["payload"], "home")

        goal = self.guard.refresh(LIGUE1)[0]
        self.assertIsNone(goal.play)
        self.assertEqual(goal.minute, "35'")
        self.assertEqual(goal.detail_line(), "Minute 35'")

    def test_two_goals_at_once_are_one_event_with_delta_two(self):
        self.guard.prime()
        self.state["payload"] = bump(self.state["payload"], "home", by=2)

        events = self.guard.refresh(LIGUE1)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].delta, 2)

    def test_both_teams_scoring_between_two_passes(self):
        self.guard.prime()
        raw = bump(self.state["payload"], "home")
        self.state["payload"] = bump(raw, "away")

        events = self.guard.refresh(LIGUE1)
        self.assertEqual(sorted(e.side for e in events), ["away", "home"])

    def test_score_going_down_is_a_cancelled_goal(self):
        self.guard.prime()
        self.state["payload"] = bump(self.state["payload"], "away", by=-1)

        events = self.guard.refresh(LIGUE1)
        self.assertEqual(len(events), 1)
        self.assertFalse(events[0].goal)
        self.assertEqual(events[0].title, "BUT ANNULE")
        self.assertEqual(events[0].detail_line(), "Score corrige")

    def test_a_new_match_is_baselined_not_replayed(self):
        self.guard.prime()
        self.state["payload"] = payload(
            event(home_score=1, away_score=1),
            event(match_id="2", home="Lens", away="Lille", home_score=3),
        )
        self.assertEqual(self.guard.refresh(LIGUE1), [])

    def test_log_line_carries_league_score_team_and_scorer(self):
        self.guard.prime()
        self.state["payload"] = bump(
            self.state["payload"], "away",
            details=(goal_detail("A1", "58'", "A. Kalimuendo", index=7),))

        line = self.guard.refresh(LIGUE1)[0].log_line()
        for piece in ("BUT", "Ligue 1", "Angers 1 - 2 Stade Rennais",
                      "Stade Rennais", "A. Kalimuendo", "58'"):
            self.assertIn(piece, line)


class TestMatchPhases(unittest.TestCase):
    """Coup d'envoi, mi-temps, reprise, fin : des cartes, jamais de son."""

    def transition(self, first, second):
        state = {"payload": payload(event(**first))}
        guard = make_watcher(state)
        guard.prime()
        state["payload"] = payload(event(**second))
        return guard.refresh(LIGUE1)

    def test_kickoff(self):
        events = self.transition({"state": "pre"}, {"state": "in"})
        self.assertEqual([e.kind for e in events], [watcher.KICKOFF])
        self.assertEqual(events[0].title, "COUP D'ENVOI")
        self.assertTrue(events[0].phase)
        self.assertFalse(events[0].goal)

    def test_the_kickoff_card_carries_the_form_of_both_sides(self):
        events = self.transition(
            {"state": "pre"},
            {"state": "in", "home_form": "LLWWW", "away_form": "WWDWL",
             "home_record": "1-0-2", "away_record": "2-1-0"})
        # "G", "N" et "P" sont les colonnes de --table : la forme et le
        # classement ne doivent pas dire la meme chose de deux facons.
        self.assertEqual(events[0].extra_lines(),
                         ["Angers : PPGGG  1G 0N 2P",
                          "Stade Rennais : GGNGP  2G 1N 0P"])

    def test_the_form_is_translated_like_the_table(self):
        events = self.transition({"state": "pre"},
                                 {"state": "in", "home_form": "LLWWW"})
        self.assertEqual(events[0].extra_lines(lang="de"), ["Angers : NNSSS"])

    def test_a_side_without_a_record_shows_its_form_alone(self):
        events = self.transition({"state": "pre"},
                                 {"state": "in", "home_form": "LLWWW"})
        self.assertEqual(events[0].extra_lines(), ["Angers : PPGGG"])

    def test_a_kickoff_the_source_says_nothing_about_is_the_card_of_before(self):
        # Le hockey, et tout match dont la source ne dit rien : la carte de
        # coup d'envoi reste ce qu'elle etait, titre et score.
        events = self.transition({"state": "pre"}, {"state": "in"})
        self.assertEqual(events[0].extra_lines(), [])
        self.assertEqual(events[0].detail_line(), "")

    def test_only_the_kickoff_looks_back(self):
        # A la mi-temps, ce qui vient de se passer est plus interessant que ce
        # qui s'est passe le mois dernier.
        for first, second in (({"state": "in"},
                               {"state": "in", "status_name": "STATUS_HALFTIME"}),
                              ({"state": "in"}, {"state": "post"})):
            events = self.transition(
                first, dict(second, home_form="LLWWW", home_record="1-0-2"))
            self.assertEqual(events[0].extra_lines(), [], events[0].kind)

    def test_the_journal_keeps_the_form_in_french(self):
        events = self.transition({"state": "pre"},
                                 {"state": "in", "home_form": "LLWWW",
                                  "home_record": "1-0-2"})
        self.assertIn("Angers : PPGGG  1G 0N 2P", events[0].log_line())

    def test_halftime(self):
        events = self.transition(
            {"state": "in"}, {"state": "in", "status_name": "STATUS_HALFTIME"})
        self.assertEqual([e.kind for e in events], [watcher.HALFTIME])
        self.assertEqual(events[0].title, "MI-TEMPS")

    def test_restart(self):
        events = self.transition(
            {"state": "in", "status_name": "STATUS_HALFTIME"},
            {"state": "in", "status_name": "STATUS_SECOND_HALF"})
        self.assertEqual([e.kind for e in events], [watcher.RESTART])
        self.assertEqual(events[0].title, "REPRISE")

    def test_fulltime(self):
        events = self.transition({"state": "in"}, {"state": "post"})
        self.assertEqual([e.kind for e in events], [watcher.FULLTIME])
        self.assertEqual(events[0].title, "FIN DU MATCH")

    def test_fulltime_straight_from_halftime(self):
        events = self.transition(
            {"state": "in", "status_name": "STATUS_HALFTIME"}, {"state": "post"})
        self.assertEqual([e.kind for e in events], [watcher.FULLTIME])

    def test_a_delayed_match_that_finally_starts(self):
        events = self.transition(
            {"state": "pre", "status_name": "STATUS_DELAYED"}, {"state": "in"})
        self.assertEqual([e.kind for e in events], [watcher.KICKOFF])

    def test_nothing_when_the_phase_does_not_move(self):
        self.assertEqual(self.transition({"state": "in"}, {"state": "in"}), [])
        self.assertEqual(self.transition({"state": "post"}, {"state": "post"}), [])

    def test_a_match_never_seen_live_says_nothing_at_full_time(self):
        # Le daemon dormait : on n'a rien suivi, autant se taire.
        self.assertEqual(self.transition({"state": "pre"}, {"state": "post"}), [])

    def test_a_postponed_match_is_silent(self):
        self.assertEqual(
            self.transition({"state": "pre"},
                            {"state": "pre", "status_name": "STATUS_POSTPONED"}),
            [])

    def test_first_sight_of_a_match_is_silent(self):
        state = {"payload": payload(event(state="in"))}
        guard = make_watcher(state)
        self.assertEqual(guard.refresh(LIGUE1), [])

    def test_a_phase_card_has_no_third_line_and_no_team(self):
        event_ = self.transition({"state": "in"}, {"state": "post"})[0]
        self.assertEqual(event_.detail_parts(), [])
        self.assertEqual(event_.detail_line(), "")
        self.assertIsNone(event_.side)
        self.assertEqual(event_.delta, 0)

    def test_a_goal_and_the_final_whistle_in_the_same_pass(self):
        state = {"payload": payload(event(state="in", home_score=0))}
        guard = make_watcher(state)
        guard.prime()
        state["payload"] = payload(event(state="post", home_score=1))

        events = guard.refresh(LIGUE1)
        # Le but d'abord, la fin ensuite : c'est l'ordre du match.
        self.assertEqual([e.kind for e in events],
                         [watcher.GOAL, watcher.FULLTIME])
        self.assertTrue(events[0].goal)
        self.assertFalse(events[1].goal)

    def test_log_lines_name_the_moment(self):
        for first, second, head in (({"state": "pre"}, {"state": "in"},
                                     "COUP D'ENVOI"),
                                    ({"state": "in"}, {"state": "post"},
                                     "FIN DU MATCH")):
            line = self.transition(first, second)[0].log_line()
            self.assertTrue(line.startswith(head), line)
            self.assertIn("Ligue 1", line)
            self.assertIn("Angers 0 - 0 Stade Rennais", line)


class TestOnlyAGoalMakesNoise(unittest.TestCase):
    """Le son ne part que sur `event.goal` : rien d'autre ne doit l'etre."""

    def test_no_sober_event_is_a_goal(self):
        match = espn.parse(payload(event()), LIGUE1)[0]
        for kind in watcher.SOBER:
            moment = watcher.Event(kind=kind, match=match, side=None, team="",
                                   opponent="", home_score=0, away_score=0,
                                   delta=0, play=None)
            self.assertFalse(moment.goal, kind)
            self.assertTrue(moment.sober, kind)

    def test_the_new_cards_do_not_hide_behind_no_phase_cards(self):
        # --no-phase-cards coupe les temps forts, pas ce qu'on a demande
        # explicitement avec --red-cards ou --before-kickoff.
        self.assertNotIn(watcher.RED_CARD, watcher.PHASES)
        self.assertNotIn(watcher.PREMATCH, watcher.PHASES)


class TestSpoilerFree(unittest.TestCase):
    """Le match regarde en differe : marque, jamais coupe.

    Toute la difference avec --exclude-teams tient la : l'evenement remonte
    complet, avec sa ligne de journal, et porte seulement un drapeau.
    """

    def guard(self, spoiler="om", wanted=None, excluded=None, home="Marseille",
              away="Lyon", red_cards=False, before_kickoff=0.0, **kwargs):
        self.state = {"payload": payload(event(home=home, away=away, **kwargs))}
        chosen = teams.Filter(wanted, excluded) if (wanted or excluded) else None
        guard = make_watcher(self.state, teams=chosen, red_cards=red_cards,
                             before_kickoff=before_kickoff,
                             spoiler_free=teams.SpoilerFilter(spoiler)
                             if spoiler else None)
        guard.prime()
        return guard

    def test_a_goal_comes_through_but_marked(self):
        guard = self.guard()
        self.state["payload"] = bump(self.state["payload"], "home")
        events = guard.refresh(LIGUE1)
        self.assertEqual(len(events), 1)
        self.assertTrue(events[0].goal)
        self.assertTrue(events[0].spoiler_free)

    def test_the_journal_line_is_intact(self):
        # Le coeur du reglage : on ne coupe que l'ecran et le son, --today
        # doit pouvoir raconter le match une fois qu'on l'a vu.
        guard = self.guard()
        self.state["payload"] = bump(
            self.state["payload"], "home",
            details=(goal_detail("H1", "58'", "A. Kalimuendo", index=3),))
        line = guard.refresh(LIGUE1)[0].log_line()
        self.assertIn("BUT", line)
        self.assertIn("Marseille 1 - 0 Lyon", line)
        self.assertIn("A. Kalimuendo", line)

    def test_another_match_is_not_marked(self):
        guard = self.guard(home="Lens", away="Lille")
        self.state["payload"] = bump(self.state["payload"], "home")
        events = guard.refresh(LIGUE1)
        self.assertEqual(len(events), 1)
        self.assertFalse(events[0].spoiler_free)

    def test_no_filter_marks_nothing(self):
        guard = self.guard(spoiler=None)
        self.state["payload"] = bump(self.state["payload"], "home")
        self.assertFalse(guard.refresh(LIGUE1)[0].spoiler_free)

    # ------------------------------------------------- tous les evenements --

    def test_a_cancelled_goal_is_marked_too(self):
        guard = self.guard(home_score=1)
        self.state["payload"] = bump(self.state["payload"], "home", by=-1)
        events = guard.refresh(LIGUE1)
        self.assertEqual([e.kind for e in events], [watcher.CANCELLED])
        self.assertTrue(events[0].spoiler_free)

    def test_every_phase_card_is_marked(self):
        # "COUP D'ENVOI" et "FIN DU MATCH" spoilent autant qu'un but : le
        # premier dit que le direct a demarre, le second que tout est joue.
        for first, second, kind in (
                ({"state": "pre"}, {"state": "in"}, watcher.KICKOFF),
                ({"state": "in"},
                 {"state": "in", "status_name": "STATUS_HALFTIME"},
                 watcher.HALFTIME),
                ({"state": "in", "status_name": "STATUS_HALFTIME"},
                 {"state": "in", "status_name": "STATUS_SECOND_HALF"},
                 watcher.RESTART),
                ({"state": "in"}, {"state": "post"}, watcher.FULLTIME)):
            guard = self.guard(**first)
            self.state["payload"] = payload(
                event(home="Marseille", away="Lyon", **second))
            events = guard.refresh(LIGUE1)
            self.assertEqual([e.kind for e in events], [kind])
            self.assertTrue(events[0].spoiler_free, kind)

    def test_a_red_card_is_marked(self):
        guard = self.guard(home_score=1, away_score=1, red_cards=True)
        self.state["payload"] = bump(
            self.state["payload"], "home", by=0,
            details=(red_card_detail("H1", "62'", "J. Lefort"),))
        events = guard.refresh(LIGUE1)
        self.assertEqual([e.kind for e in events], [watcher.RED_CARD])
        self.assertTrue(events[0].spoiler_free)

    def test_a_prematch_announcement_is_marked(self):
        guard = self.guard(state="pre", clock="0'", date=in_minutes(5),
                           before_kickoff=10 * 60.0)
        events = guard.refresh(LIGUE1)
        self.assertEqual([e.kind for e in events], [watcher.PREMATCH])
        self.assertTrue(events[0].spoiler_free)

    # ------------------------------------------- cohabitation des 3 filtres -

    def test_following_a_team_and_muting_it_is_a_sensible_pair(self):
        # L'usage reel : je veux le journal de l'OM, pas l'alerte.
        guard = self.guard(spoiler="om", wanted="om")
        self.state["payload"] = bump(self.state["payload"], "home")
        events = guard.refresh(LIGUE1)
        self.assertEqual(len(events), 1)
        self.assertTrue(events[0].spoiler_free)

    def test_a_match_outside_the_followed_teams_disappears_anyway(self):
        guard = self.guard(spoiler="om", wanted="om", home="Lens", away="Lille")
        self.state["payload"] = bump(self.state["payload"], "home")
        self.assertEqual(guard.refresh(LIGUE1), [])

    def test_exclusion_wins_over_the_spoiler_free_list(self):
        # Un match exclu n'existe pas : il n'a meme pas de ligne de journal.
        guard = self.guard(spoiler="om", excluded="om")
        self.state["payload"] = bump(self.state["payload"], "home")
        self.assertEqual(guard.refresh(LIGUE1), [])

    def test_a_followed_team_that_is_not_muted_keeps_its_alert(self):
        guard = self.guard(spoiler="om", wanted="om,ol", home="Lyon",
                           away="Lens")
        self.state["payload"] = bump(self.state["payload"], "home")
        events = guard.refresh(LIGUE1)
        self.assertEqual(len(events), 1)
        self.assertFalse(events[0].spoiler_free)

    def test_the_match_is_still_followed(self):
        guard = self.guard()
        self.assertEqual(len(guard.all_matches()), 1)


class TestRedCards(unittest.TestCase):
    """L'expulsion : detectee comme un but, affichee comme un temps fort."""

    def setUp(self):
        self.state = {"payload": payload(event(home_score=1, away_score=1))}

    def guard(self, **kwargs):
        guard = make_watcher(self.state, red_cards=True, **kwargs)
        guard.prime()
        return guard

    def send(self, guard, *details):
        self.state["payload"] = bump(self.state["payload"], "home", by=0,
                                     details=details)
        return guard.refresh(LIGUE1)

    def test_nothing_without_the_option(self):
        guard = make_watcher(self.state)
        guard.prime()
        self.assertEqual(self.send(guard, red_card_detail("H1")), [])

    def test_a_red_card_is_signalled_once_and_only_once(self):
        guard = self.guard()
        events = self.send(guard, red_card_detail("H1", "62'", "J. Lefort"))
        self.assertEqual([e.kind for e in events], [watcher.RED_CARD])

        # La cle est stable : la meme expulsion relue ne ressort pas.
        self.assertEqual(guard.refresh(LIGUE1), [])
        self.assertEqual(guard.refresh(LIGUE1), [])

    def test_a_red_card_already_there_at_the_first_pass_stays_quiet(self):
        # Demarrer le daemon a la 70e minute ne doit pas rejouer l'expulsion
        # de la 20e, exactement comme pour les buts.
        self.state["payload"] = payload(event(
            details=(red_card_detail("H1", "20'"),)))
        guard = self.guard()
        self.assertEqual(guard.refresh(LIGUE1), [])

    def test_the_card_names_the_team_and_the_player(self):
        guard = self.guard()
        expulsion = self.send(guard, red_card_detail("A1", "62'", "J. Lefort"))[0]
        self.assertEqual(expulsion.title, "CARTON ROUGE")
        self.assertEqual(expulsion.team, "Stade Rennais")
        self.assertEqual(expulsion.minute, "62'")
        self.assertEqual(expulsion.detail_line(), "Stade Rennais : J. Lefort")
        self.assertEqual([t for t, strong in expulsion.detail_parts() if strong],
                         ["J. Lefort"])

    def test_a_red_card_without_a_player_still_names_the_team(self):
        guard = self.guard()
        detail = red_card_detail("H1")
        detail["athletesInvolved"] = []
        expulsion = self.send(guard, detail)[0]
        self.assertEqual(expulsion.detail_line(), "Angers")

    def test_a_red_card_is_discreet_and_never_a_goal(self):
        guard = self.guard()
        expulsion = self.send(guard, red_card_detail("H1"))[0]
        self.assertFalse(expulsion.goal)
        self.assertFalse(expulsion.phase)     # --no-phase-cards ne la coupe pas
        self.assertTrue(expulsion.sober)      # donc : titre gris, aucun son
        self.assertEqual(expulsion.delta, 0)

    def test_the_team_filter_applies(self):
        guard = self.guard(teams=teams.Filter("lens"))
        self.assertEqual(self.send(guard, red_card_detail("H1")), [])

    def test_a_red_card_never_describes_a_goal(self):
        # Les deux vivent dans le meme tableau `details` : une expulsion ne
        # doit jamais finir en "But de ..." sur la carte du but suivant.
        guard = self.guard()
        self.state["payload"] = bump(
            self.state["payload"], "away",
            details=(red_card_detail("A1", "60'", "J. Lefort", index=1),
                     goal_detail("A1", "63'", "A. Kalimuendo", index=2)))

        events = guard.refresh(LIGUE1)
        self.assertEqual([e.kind for e in events],
                         [watcher.GOAL, watcher.RED_CARD])
        self.assertEqual(events[0].play.scorer, "A. Kalimuendo")
        self.assertEqual(events[0].detail_line(), "But de A. Kalimuendo")
        self.assertEqual(len(events[0].match.plays), 1)

    def test_log_line_names_the_expulsion(self):
        guard = self.guard()
        line = self.send(guard, red_card_detail("H1", "62'", "J. Lefort"))[0].log_line()
        for piece in ("CARTON ROUGE", "Ligue 1", "Angers", "J. Lefort", "62'"):
            self.assertIn(piece, line)


class TestPrematchCard(unittest.TestCase):
    """Le match va commencer : une carte, une seule, par match."""

    def setUp(self):
        self.state = {"payload": payload(event(
            state="pre", clock="0'", date=in_minutes(5)))}

    def guard(self, before_kickoff=10 * 60.0, **kwargs):
        guard = make_watcher(self.state, before_kickoff=before_kickoff, **kwargs)
        guard.prime()
        return guard

    def test_nothing_without_the_option(self):
        self.assertEqual(self.guard(before_kickoff=0).refresh(LIGUE1), [])

    def test_the_card_fires_once_inside_the_window(self):
        guard = self.guard()
        events = guard.refresh(LIGUE1)
        self.assertEqual([e.kind for e in events], [watcher.PREMATCH])
        self.assertEqual(events[0].title, "LE MATCH VA COMMENCER")

        # Le piege : la fenetre reste ouverte, les releves s'enchainent, et la
        # carte ne doit pas revenir a chacun d'eux.
        for _ in range(5):
            self.assertEqual(guard.refresh(LIGUE1), [])

    def test_the_first_pass_is_silent(self):
        # prime() photographie : meme dans la fenetre, rien ne sort.
        guard = make_watcher(self.state, before_kickoff=10 * 60.0)
        self.assertEqual(guard.refresh(LIGUE1), [])

    def test_a_match_too_far_away_says_nothing(self):
        self.state["payload"] = payload(event(state="pre", date=in_minutes(45)))
        self.assertEqual(self.guard().refresh(LIGUE1), [])

    def test_a_match_already_under_way_says_nothing(self):
        self.state["payload"] = payload(event(state="in", date=in_minutes(-20)))
        self.assertEqual(self.guard().refresh(LIGUE1), [])

    def test_a_kickoff_hour_already_passed_says_nothing(self):
        # Match en retard : "ca va commencer" serait faux.
        self.state["payload"] = payload(event(state="pre", date=in_minutes(-3)))
        self.assertEqual(self.guard().refresh(LIGUE1), [])

    def test_a_match_without_a_date_says_nothing(self):
        self.state["payload"] = payload(event(state="pre", date=""))
        self.assertEqual(self.guard().refresh(LIGUE1), [])

    def test_the_card_counts_down_and_shows_no_minute(self):
        announce = self.guard().refresh(LIGUE1)[0]
        self.assertEqual(announce.minute, "")     # rien n'a commence
        self.assertEqual(announce.detail_line(), "Coup d'envoi dans 5 min")
        self.assertTrue(announce.sober)
        self.assertFalse(announce.goal)
        self.assertFalse(announce.phase)          # son propre interrupteur

    def test_the_team_filter_applies(self):
        self.assertEqual(self.guard(teams=teams.Filter("lens")).refresh(LIGUE1), [])

    def test_the_announcement_does_not_replace_the_kickoff(self):
        guard = self.guard()
        self.assertEqual([e.kind for e in guard.refresh(LIGUE1)],
                         [watcher.PREMATCH])
        self.state["payload"] = payload(event(state="in", date=in_minutes(-1)))
        self.assertEqual([e.kind for e in guard.refresh(LIGUE1)],
                         [watcher.KICKOFF])

    def test_the_window_speeds_up_the_cadence(self):
        # Une annonce a 40 min n'a de sens que si on releve assez souvent.
        self.state["payload"] = payload(event(state="pre", date=in_minutes(35)))
        guard = make_watcher(self.state, interval=20, idle_interval=600,
                             before_kickoff=40 * 60.0)
        guard.refresh(LIGUE1, now=0.0)
        self.assertEqual(guard._due["fra.1"], watcher.KICKOFF_INTERVAL)


class TestFullTimeScorers(unittest.TestCase):
    """La fin du match liste les buteurs : le score seul ne dit pas qui."""

    def final(self, *details):
        """Le sifflet final d'un match qu'on suivait, deja mene 1-2."""
        state = {"payload": payload(event(
            state="in", home_score=1, away_score=2, details=details))}
        guard = make_watcher(state)
        guard.prime()
        state["payload"] = payload(event(
            state="post", clock="90'+4'", home_score=1, away_score=2,
            details=details))
        return guard.refresh(LIGUE1)[0]

    def test_each_camp_gets_its_line(self):
        end = self.final(goal_detail("H1", "12'", "M. Lopez", index=1),
                         goal_detail("A1", "58'", "A. Kalimuendo", index=2),
                         goal_detail("A1", "77'", "L. Blas", index=3))
        self.assertEqual(end.extra_lines(), [
            "Angers : M. Lopez 12'",
            "Stade Rennais : A. Kalimuendo 58', L. Blas 77'",
        ])

    def test_the_scorers_are_the_highlighted_part(self):
        end = self.final(goal_detail("H1", "12'", "M. Lopez", index=1))
        self.assertEqual([t for t, strong in end.extra_parts()[0] if strong],
                         ["M. Lopez 12'"])

    def test_a_camp_without_a_goal_has_no_line(self):
        end = self.final(goal_detail("A1", "58'", "A. Kalimuendo", index=1))
        self.assertEqual(end.extra_lines(), ["Stade Rennais : A. Kalimuendo 58'"])

    def test_a_goalless_match_has_no_extra_line(self):
        self.assertEqual(self.final().extra_lines(), [])

    def test_own_goals_and_penalties_are_marked(self):
        end = self.final(
            goal_detail("H1", "12'", "J. Lefort", own_goal=True, index=1),
            goal_detail("A1", "58'", "K. Mbappe", penalty=True, index=2))
        self.assertEqual(end.extra_lines(), [
            "Angers : J. Lefort (csc) 12'",
            "Stade Rennais : K. Mbappe (sp) 58'",
        ])

    def test_a_goal_without_a_scorer_falls_back_on_its_nature(self):
        detail = goal_detail("H1", "12'", "", index=1)
        detail["athletesInvolved"] = []
        self.assertEqual(self.final(detail).extra_lines(), ["Angers : But 12'"])

    def test_only_the_end_of_the_match_lists_the_scorers(self):
        state = {"payload": payload(event(state="in", home_score=0))}
        guard = make_watcher(state)
        guard.prime()
        state["payload"] = bump(state["payload"], "home",
                                details=(goal_detail("H1", "12'", "M. Lopez"),))
        goal = guard.refresh(LIGUE1)[0]
        self.assertEqual(goal.kind, watcher.GOAL)
        self.assertEqual(goal.extra_parts(), [])

    def test_log_line_carries_the_scorers(self):
        line = self.final(goal_detail("H1", "12'", "M. Lopez", index=1),
                          goal_detail("A1", "58'", "A. Kalimuendo", index=2)).log_line()
        self.assertTrue(line.startswith("FIN DU MATCH"), line)
        self.assertIn("Angers : M. Lopez 12'", line)
        self.assertIn("Stade Rennais : A. Kalimuendo 58'", line)


class TestCadence(unittest.TestCase):
    def test_live_match_gets_the_fast_cadence(self):
        state = {"payload": payload(event(state="in"))}
        guard = make_watcher(state, interval=20, idle_interval=600)
        guard.refresh(LIGUE1, now=0.0)
        self.assertEqual(guard._due["fra.1"], 20.0)

    def test_nothing_live_gets_the_slow_cadence(self):
        state = {"payload": payload(event(state="post", date="2000-01-01T12:00Z"))}
        guard = make_watcher(state, interval=20, idle_interval=600)
        guard.refresh(LIGUE1, now=0.0)
        self.assertEqual(guard._due["fra.1"], 600.0)

    def test_imminent_kickoff_speeds_things_up(self):
        from datetime import datetime, timedelta, timezone

        soon = datetime.now(timezone.utc) + timedelta(minutes=5)
        state = {"payload": payload(event(
            state="pre", date=soon.strftime("%Y-%m-%dT%H:%M:%SZ")))}
        guard = make_watcher(state, interval=20, idle_interval=600)
        guard.refresh(LIGUE1, now=0.0)
        self.assertEqual(guard._due["fra.1"], watcher.KICKOFF_INTERVAL)

    def test_due_leagues_and_next_delay(self):
        state = {"payload": payload(event(state="in"))}
        guard = make_watcher(state, interval=20)
        self.assertEqual(guard.due_leagues(now=0.0), [LIGUE1])
        guard.refresh(LIGUE1, now=0.0)
        self.assertEqual(guard.due_leagues(now=5.0), [])
        self.assertEqual(guard.next_delay(now=5.0), 15.0)

    def test_next_delay_is_clamped(self):
        state = {"payload": payload(event(state="post", date="2000-01-01T12:00Z"))}
        guard = make_watcher(state, interval=20, idle_interval=3600)
        guard.refresh(LIGUE1, now=0.0)
        self.assertEqual(guard.next_delay(now=0.0), 60.0)

    def test_prime_spreads_the_competitions_apart(self):
        # Sinon, avec tout le catalogue, tous les releves retomberaient a la
        # meme seconde et la source finirait par nous jeter.
        state = {"payload": payload(event(state="in"))}
        others = [leagues.BY_SLUG[slug] for slug in ("eng.1", "esp.1")]
        guard = watcher.Watcher([LIGUE1] + others, interval=20,
                                opener=opener_for(state))
        guard.prime(pause=0)

        due = [guard._due[l.slug] for l in guard.leagues]
        self.assertEqual(len(set(due)), 3)
        self.assertAlmostEqual(due[1] - due[0], watcher.SPREAD, places=1)

    def test_interval_has_a_floor(self):
        guard = watcher.Watcher([LIGUE1], interval=1, idle_interval=1)
        self.assertGreaterEqual(guard.interval, 5.0)
        self.assertGreaterEqual(guard.idle_interval, guard.interval)


class TestResilience(unittest.TestCase):
    def test_network_error_backs_off_and_keeps_going(self):
        def broken(_url, _timeout):
            raise OSError("pas de reseau")

        logged = []
        guard = watcher.Watcher([LIGUE1], interval=20, opener=broken,
                                on_log=logged.append)

        self.assertEqual(guard.refresh(LIGUE1, now=0.0), [])
        self.assertEqual(guard._due["fra.1"], 40.0)
        guard.refresh(LIGUE1, now=40.0)
        self.assertEqual(guard._due["fra.1"], 40.0 + 80.0)
        self.assertTrue(logged)

    def test_backoff_is_capped(self):
        guard = watcher.Watcher([LIGUE1], interval=60,
                                opener=lambda *_: (_ for _ in ()).throw(OSError("x")))
        for _ in range(10):
            guard.refresh(LIGUE1, now=0.0)
        self.assertLessEqual(guard._due["fra.1"], watcher.MAX_BACKOFF)

    def test_recovery_is_logged_and_state_survives(self):
        state = {"payload": payload(event(home_score=1))}
        failing = {"now": True}

        def flaky(url, timeout):
            if failing["now"]:
                raise OSError("pas de reseau")
            return opener_for(state)(url, timeout)

        logged = []
        guard = watcher.Watcher([LIGUE1], opener=flaky, on_log=logged.append)
        guard.refresh(LIGUE1, now=0.0)
        failing["now"] = False
        guard.refresh(LIGUE1, now=100.0)
        self.assertTrue(any("joignable" in message for message in logged))

        state["payload"] = bump(state["payload"], "home")
        self.assertEqual(len(guard.refresh(LIGUE1, now=200.0)), 1)

    def test_live_and_all_matches_views(self):
        state = {"payload": payload(
            event(state="in"), event(match_id="2", state="post"))}
        guard = make_watcher(state)
        guard.prime()
        self.assertEqual(len(guard.all_matches()), 2)
        self.assertEqual(len(guard.live_matches()), 1)

    def test_old_matches_are_forgotten(self):
        state = {"payload": payload(event())}
        guard = make_watcher(state)
        guard.prime()
        snapshot = next(iter(guard._snapshots.values()))
        snapshot.last_seen -= watcher.FORGET_AFTER + 60
        state["payload"] = payload(event(match_id="2"))
        guard.refresh(LIGUE1)
        self.assertNotIn("1", guard._snapshots)


class TestWakeFromSleep(unittest.TestCase):
    """Veille, hibernation, processus gele : au reveil on ne crie pas.

    Le scenario : 0-0 releve avant la veille, 3-1 au tableau de bord au
    reveil. Sans garde-fou le watcher sortirait une carte "BUT" de delta 3
    avec une minute perimee.
    """

    def setUp(self):
        self.clock = FakeClock()
        self.state = {"payload": payload(event(state="in"))}
        self.logged = []
        self.guard = make_watcher(self.state, interval=25, clock=self.clock,
                                  on_log=self.logged.append)
        self.guard.refresh(LIGUE1, now=0.0)   # la photo d'avant la veille

    def fall_asleep(self, seconds):
        """Promet une attente courte, puis fait sauter l'horloge murale."""
        self.guard.plan_wait(now=25.0)
        self.clock.jump(seconds)

    def test_a_time_jump_rephotographs_without_alerting(self):
        self.fall_asleep(40 * 60)
        self.state["payload"] = bump(self.state["payload"], "away", by=3)

        self.assertEqual(self.guard.tick(now=25.0), [])

    def test_the_gap_is_written_to_the_log(self):
        self.fall_asleep(40 * 60)
        self.guard.tick(now=25.0)
        self.assertTrue(any("trou" in line for line in self.logged), self.logged)

    def test_a_stale_phase_card_is_swallowed_too(self):
        # Sinon le reveil annoncerait "FIN DU MATCH" pour un match termine
        # depuis une heure, dont on n'a rien suivi.
        self.fall_asleep(90 * 60)
        self.state["payload"] = payload(event(state="post", home_score=2,
                                              away_score=1))
        self.assertEqual(self.guard.tick(now=25.0), [])

    def test_a_goal_after_the_rephotograph_is_announced(self):
        self.fall_asleep(40 * 60)
        self.state["payload"] = bump(self.state["payload"], "away", by=3)
        self.guard.tick(now=25.0)

        self.guard.plan_wait(now=50.0)
        self.clock.jump(25.0)
        self.state["payload"] = bump(self.state["payload"], "away")

        events = self.guard.tick(now=50.0)
        self.assertEqual([e.kind for e in events], [watcher.GOAL])
        self.assertEqual(events[0].delta, 1)
        self.assertEqual(events[0].score_line, "Angers 0 - 4 Stade Rennais")

    def test_a_normal_wait_never_takes_that_path(self):
        # Un releve traine par le timeout HTTP de 8 s n'est pas une veille.
        self.fall_asleep(1.0 + 8.0)
        self.state["payload"] = bump(self.state["payload"], "away")

        events = self.guard.tick(now=25.0)
        self.assertEqual([e.kind for e in events], [watcher.GOAL])
        self.assertEqual(self.logged, [])

    def test_the_grace_is_generous(self):
        self.fall_asleep(1.0 + watcher.GAP_GRACE)
        self.assertEqual(self.guard._gap(), 0.0)
        self.clock.jump(1.0)
        self.assertGreater(self.guard._gap(), 0.0)

    def test_nothing_promised_yet_is_not_a_gap(self):
        # Au demarrage la boucle n'a encore rien annonce : pas de trou imagine.
        self.clock.jump(3 * 3600)
        self.assertEqual(self.guard._gap(), 0.0)

    def test_a_clock_stepped_backwards_is_not_a_gap(self):
        self.fall_asleep(-3600)
        self.assertEqual(self.guard._gap(), 0.0)

    def test_plan_wait_returns_the_same_delay_as_next_delay(self):
        self.assertEqual(self.guard.plan_wait(now=10.0),
                         self.guard.next_delay(now=10.0))

    def test_the_catch_up_stays_off_unless_asked(self):
        # Le silence est le comportement livre : sans --catch-up, rien de la
        # machinerie de rattrapage ne doit se mettre en marche.
        self.fall_asleep(40 * 60)
        self.state["payload"] = bump(self.state["payload"], "away", by=2)
        self.assertEqual(self.guard.tick(now=25.0), [])
        self.assertIsNone(self.guard._missed)
        self.assertTrue(any("sans rien annoncer" in line
                            for line in self.logged), self.logged)


class TestCatchUp(unittest.TestCase):
    """--catch-up : au reveil, UNE carte muette dit ce qu'on a manque.

    Meme scenario que la veille tout court, mais la photo d'avant le trou n'est
    plus jetee : elle sert a nommer les matchs qui ont bouge, leur score
    d'avant et les buteurs, que la source publie avec des cles stables.
    """

    def setUp(self):
        self.clock = FakeClock()
        self.state = {"payload": self.board()}
        self.logged = []
        self.guard = self.watcher()

    def board(self, first=(0, 0), second=(0, 0), details=(), other_details=()):
        """Deux matchs en cours dans le meme championnat."""
        return payload(
            event(state="in", home_score=first[0], away_score=first[1],
                  details=details),
            event(match_id="2", home="Lens", away="Lille", state="in",
                  home_score=second[0], away_score=second[1],
                  details=other_details))

    def watcher(self, **kwargs):
        """Un watcher qui a deja photographie l'existant, avant la veille."""
        guard = make_watcher(self.state, interval=25, clock=self.clock,
                             catch_up=True, on_log=self.logged.append, **kwargs)
        guard.refresh(LIGUE1, now=0.0)
        return guard

    def fall_asleep(self, seconds=40 * 60):
        """Promet une attente courte, puis fait sauter l'horloge murale."""
        self.guard.plan_wait(now=25.0)
        self.clock.jump(seconds)

    def missed(self):
        """La veille, deux buts pour Rennes et un pour Lens, puis le reveil."""
        self.fall_asleep()
        self.state["payload"] = self.board(
            first=(0, 2), second=(1, 0),
            details=(goal_detail("A1", "58'", "A. Kalimuendo", index=1),
                     goal_detail("A1", "77'", "L. Blas", index=2)),
            other_details=(goal_detail("H2", "23'", "F. Sotoca", index=3),))
        return self.guard.tick(now=25.0)

    # ------------------------------------------------------------- la carte --

    def test_one_card_and_only_one(self):
        # Trois buts, deux matchs : rejouer une carte par but avec des minutes
        # perimees est exactement ce que le silence du reveil evitait.
        events = self.missed()
        self.assertEqual([e.kind for e in events], [watcher.CATCHUP])
        self.assertEqual(events[0].title, "PENDANT TON ABSENCE")

    def test_the_card_never_makes_a_sound(self):
        # Le son ne part que sur `event.goal` : on n'annonce pas au klaxon un
        # but vieux d'une heure.
        summary = self.missed()[0]
        self.assertFalse(summary.goal)
        self.assertTrue(summary.sober)
        self.assertFalse(summary.phase)   # --no-phase-cards ne la coupe pas
        self.assertEqual(summary.delta, 0)
        self.assertIsNone(summary.side)

    def test_the_card_names_the_matches_scores_and_scorers(self):
        summary = self.missed()
        summary = summary[0]
        self.assertEqual(summary.score_line, "Angers 0 - 2 Stade Rennais")
        self.assertEqual(summary.detail_line(),
                         "avant 0 - 0 : A. Kalimuendo 58', L. Blas 77'")
        self.assertEqual(summary.extra_lines(),
                         ["Lens 1 - 0 Lille (avant 0 - 0) : F. Sotoca 23'"])

    def test_the_scorers_are_the_highlighted_part(self):
        summary = self.missed()[0]
        self.assertEqual([t for t, strong in summary.detail_parts() if strong],
                         ["A. Kalimuendo 58', L. Blas 77'"])
        self.assertEqual([t for t, strong in summary.extra_parts()[0] if strong],
                         ["F. Sotoca 23'"])

    def test_the_header_carries_the_length_of_the_absence(self):
        # Aucune minute de jeu n'appartient a une carte qui couvre deux matchs.
        self.assertEqual(self.missed()[0].minute, "40 min")

    def test_a_goal_whose_action_is_unknown_still_counts(self):
        # La source publie ses actions avec du retard : un score qui a monte
        # sans action lisible reste un match qui a bouge.
        self.fall_asleep()
        self.state["payload"] = self.board(first=(0, 2))
        summary = self.guard.tick(now=25.0)[0]
        self.assertEqual(summary.detail_line(), "avant 0 - 0")
        self.assertEqual(summary.extra_lines(), [])

    def test_a_goal_already_seen_before_the_sleep_is_not_replayed(self):
        # La cle de l'action est stable : celle qu'on avait deja affichee ne
        # revient pas dans le resume.
        self.state["payload"] = self.board(
            first=(0, 1),
            details=(goal_detail("A1", "12'", "L. Blas", index=1),))
        self.guard = self.watcher()
        self.fall_asleep()
        self.state["payload"] = self.board(
            first=(0, 2),
            details=(goal_detail("A1", "12'", "L. Blas", index=1),
                     goal_detail("A1", "58'", "A. Kalimuendo", index=2)))
        summary = self.guard.tick(now=25.0)[0]
        self.assertEqual(summary.detail_line(),
                         "avant 0 - 1 : A. Kalimuendo 58'")

    def test_the_log_keeps_the_whole_list(self):
        line = self.missed()[0].log_line()
        for piece in ("PENDANT TON ABSENCE", "Ligue 1",
                      "Angers 0 - 2 Stade Rennais", "avant 0 - 0",
                      "A. Kalimuendo 58'", "Lens 1 - 0 Lille", "F. Sotoca 23'",
                      "(40 min)"):
            self.assertIn(piece, line)

    # ---------------------------------------------------------- rien a dire --

    def test_nothing_missed_means_no_card_at_all(self):
        self.fall_asleep()
        self.assertEqual(self.guard.tick(now=25.0), [])

    def test_the_catch_up_is_logged_even_without_a_card(self):
        # Sinon "aucune carte" et "le rattrapage n'a pas tourne" seraient
        # indistinguables dans le journal.
        self.fall_asleep()
        self.guard.tick(now=25.0)
        self.assertTrue(any("rattrapage" in line and "personne" in line
                            for line in self.logged), self.logged)

    def test_the_gap_itself_is_still_logged(self):
        self.missed()
        self.assertTrue(any("trou" in line for line in self.logged), self.logged)
        self.assertTrue(any("rattrapage" in line and "2 match(s)" in line
                            for line in self.logged), self.logged)

    def test_a_match_never_seen_before_the_gap_is_left_out(self):
        # Commence et fini pendant la veille : on n'a rien suivi, meme regle
        # que pour la carte de fin de match.
        self.fall_asleep()
        self.state["payload"] = payload(
            event(state="in", home_score=0, away_score=0),
            event(match_id="2", home="Lens", away="Lille", state="in"),
            event(match_id="3", home="Brest", away="Nantes", state="post",
                  home_score=2, away_score=1))
        self.assertEqual(self.guard.tick(now=25.0), [])

    # ------------------------------------------------------------- filtrage --

    def test_the_team_filter_applies(self):
        self.guard = self.watcher(teams=teams.Filter("lens"))
        summary = self.missed()[0]
        # Rennes a marque deux fois, mais on ne suit que Lens : c'est son match
        # qui prend la tete de la carte, et il y est seul.
        self.assertEqual(summary.score_line, "Lens 1 - 0 Lille")
        self.assertEqual(summary.detail_line(), "avant 0 - 0 : F. Sotoca 23'")
        self.assertEqual(summary.extra_lines(), [])

    def test_a_filter_that_matches_nothing_gives_no_card(self):
        self.guard = self.watcher(teams=teams.Filter("brest"))
        self.assertEqual(self.missed(), [])

    # ------------------------------------------------------------- cadence ---

    def test_watching_starts_again_normally_afterwards(self):
        self.missed()
        self.guard.plan_wait(now=50.0)
        self.clock.jump(25.0)
        self.state["payload"] = self.board(first=(0, 3), second=(1, 0))

        events = self.guard.tick(now=50.0)
        self.assertEqual([e.kind for e in events], [watcher.GOAL])
        self.assertEqual(events[0].delta, 1)

    def test_two_naps_in_a_row_are_summed_up_once(self):
        # La machine se rendort avant que le resume ait pu sortir : c'est la
        # photo la plus ancienne qui dit tout ce qu'on a manque.
        self.fall_asleep(20 * 60)
        self.guard._check_gap()
        self.state["payload"] = self.board(first=(0, 1))
        self.guard.plan_wait(now=25.0)
        self.clock.jump(20 * 60)
        self.state["payload"] = self.board(first=(0, 2))

        events = self.guard.tick(now=25.0)
        self.assertEqual([e.kind for e in events], [watcher.CATCHUP])
        self.assertEqual(events[0].detail_line(), "avant 0 - 0")
        self.assertEqual(events[0].minute, "40 min")

    def test_the_summary_waits_for_every_competition(self):
        """Un resume a trous vaudrait moins que rien.

        Sous Linux `time.monotonic()` gele pendant la veille : les echeances ne
        retombent donc pas toutes au meme releve.
        """
        premier = leagues.BY_SLUG["eng.1"]

        def opener(url, timeout):
            if premier.slug in url:
                return b'{"events": []}'
            return opener_for(self.state)(url, timeout)

        guard = watcher.Watcher([LIGUE1, premier], interval=25,
                                clock=self.clock, catch_up=True, opener=opener,
                                on_log=self.logged.append)
        guard.refresh(LIGUE1, now=0.0)
        guard.refresh(premier, now=0.0)
        guard.plan_wait(now=25.0)
        self.clock.jump(40 * 60)
        self.state["payload"] = self.board(first=(0, 2))

        # Seule la Ligue 1 est exigible : pas de resume tant que l'autre
        # championnat n'a pas ete rephotographie.
        self.assertEqual(guard.tick(now=25.0), [])
        guard._due[premier.slug] = 26.0
        self.assertEqual([e.kind for e in guard.tick(now=26.0)],
                         [watcher.CATCHUP])


if __name__ == "__main__":
    unittest.main()
