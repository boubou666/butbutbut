import unittest

from butbutbut import espn, leagues, watcher

from helpers import bump, event, goal_detail, opener_for, payload

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


if __name__ == "__main__":
    unittest.main()
