import unittest

from butbutbut import espn, leagues, watcher

from helpers import FakeClock, bump, event, goal_detail, opener_for, payload

LIGUE1 = leagues.BY_SLUG["fra.1"]


def make_watcher(state, **kwargs):
    return watcher.Watcher([LIGUE1], opener=opener_for(state), **kwargs)


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


if __name__ == "__main__":
    unittest.main()
