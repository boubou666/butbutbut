"""La carte epinglee, cycle de vie compris, sans reseau ni ecran.

Tout ce module tient sur des `espn.Match` fabriques a la main : `Pin` ne
connait ni tkinter ni la source, il ne fait que decider quel match on suit.
"""

import unittest

from butbutbut import espn, leagues, pinned

from helpers import event, payload

LIGUE1 = leagues.BY_SLUG["fra.1"]


def matches(*events):
    """Des Match, tels que le tableau de bord les donnerait."""
    return espn.parse(payload(*events), LIGUE1)


def live(home="Angers", away="Stade Rennais", **kwargs):
    kwargs.setdefault("state", "in")
    return event(home=home, away=away, **kwargs)


class TestNothingAsked(unittest.TestCase):
    """Sans --pin, ce module ne doit rien faire du tout."""

    def test_an_empty_pin_is_inactive(self):
        for token in (None, "", "   "):
            pin = pinned.Pin(token)
            self.assertFalse(pin.active)
            self.assertIsNone(pin.update(matches(live())))
        self.assertEqual(pinned.Pin(None).describe(), "aucune carte epinglee")


class TestAppearing(unittest.TestCase):
    def test_a_live_match_is_pinned_right_away(self):
        """Demarrer le daemon a la mi-temps doit donner la carte tout de suite."""
        follow = pinned.Pin("angers").update(matches(live()))
        self.assertIsNotNone(follow)
        self.assertFalse(follow.ended)
        self.assertEqual(follow.match.home, "Angers")

    def test_the_away_team_counts_too(self):
        follow = pinned.Pin("rennai").update(matches(live()))
        self.assertIsNotNone(follow)
        self.assertEqual(follow.match.away, "Stade Rennais")

    def test_a_match_that_has_not_started_pins_nothing(self):
        pin = pinned.Pin("angers")
        self.assertIsNone(pin.update(matches(live(state="pre", clock="0'"))))

        # ... et la carte arrive au coup d'envoi, au releve suivant.
        follow = pin.update(matches(live(clock="1'")))
        self.assertIsNotNone(follow)
        self.assertFalse(follow.ended)

    def test_another_teams_match_is_ignored(self):
        pin = pinned.Pin("om")
        self.assertIsNone(pin.update(matches(live())))
        self.assertFalse(pin.match_id)

    def test_a_finished_match_is_never_adopted(self):
        """Lancer le daemon apres le match ne doit pas ressortir une carte."""
        pin = pinned.Pin("angers")
        self.assertIsNone(pin.update(matches(live(state="post", detail="FT"))))


class TestFollowing(unittest.TestCase):
    """La carte suit le match : le score et la minute changent, elle reste."""

    def setUp(self):
        self.pin = pinned.Pin("angers")

    def test_the_score_and_the_minute_are_refreshed(self):
        self.pin.update(matches(live(home_score=0, clock="12'")))
        follow = self.pin.update(matches(live(home_score=2, clock="61'")))
        self.assertEqual(follow.match.home_score, 2)
        self.assertEqual(follow.match.clock, "61'")
        self.assertFalse(follow.ended)

    def test_it_stays_on_the_same_match(self):
        first = self.pin.update(matches(live()))
        second = self.pin.update(matches(live()))
        self.assertEqual(first.match.id, second.match.id)

    def test_halftime_is_not_the_end(self):
        self.pin.update(matches(live()))
        follow = self.pin.update(
            matches(live(status_name="STATUS_HALFTIME", clock="45'")))
        self.assertFalse(follow.ended)

    def test_it_describes_what_it_follows(self):
        self.pin.update(matches(live(home_score=1)))
        self.assertEqual(self.pin.describe(),
                         "carte epinglee sur angers : [Ligue 1] Angers 1 - 0 "
                         "Stade Rennais")

    def test_a_pin_that_follows_nothing_says_so(self):
        self.assertEqual(pinned.Pin("angers").describe(),
                         "carte epinglee sur angers (aucun match en cours)")


class TestDisappearing(unittest.TestCase):
    """Elle ne doit pas rester la toute la nuit."""

    def setUp(self):
        self.pin = pinned.Pin("angers", linger=300.0)
        self.pin.update(matches(live()), now=1000.0)

    def final(self, **kwargs):
        return matches(live(state="post", clock="90'+4'", detail="FT", **kwargs))

    def test_the_final_whistle_keeps_the_card_a_moment(self):
        follow = self.pin.update(self.final(home_score=2), now=1000.0)
        self.assertIsNotNone(follow)
        self.assertTrue(follow.ended)
        self.assertEqual(follow.match.home_score, 2)

    def test_the_card_goes_after_the_grace_delay(self):
        self.pin.update(self.final(), now=1000.0)
        self.assertIsNotNone(self.pin.update(self.final(), now=1299.0))
        self.assertIsNone(self.pin.update(self.final(), now=1301.0))
        # ... et elle ne revient pas au releve suivant.
        self.assertIsNone(self.pin.update(self.final(), now=1400.0))

    def test_the_delay_starts_at_the_final_whistle_not_at_kickoff(self):
        # Un match suivi pendant deux heures ne doit pas disparaitre au sifflet.
        follow = self.pin.update(self.final(), now=8000.0)
        self.assertTrue(follow.ended)
        self.assertIsNotNone(self.pin.update(self.final(), now=8200.0))

    def test_a_match_that_vanishes_from_the_scoreboard_is_treated_as_over(self):
        """Reponse tronquee ou changement de journee : pas de clignotement."""
        follow = self.pin.update(matches(), now=1000.0)
        self.assertIsNotNone(follow)
        self.assertTrue(follow.ended)
        self.assertEqual(follow.match.home, "Angers")
        self.assertIsNone(self.pin.update(matches(), now=1400.0))

    def test_a_match_that_comes_back_is_followed_again(self):
        self.pin.update(matches(), now=1000.0)
        follow = self.pin.update(matches(live(clock="70'")), now=1100.0)
        self.assertFalse(follow.ended)
        # Le compte a rebours est remis a zero : le match a repris.
        self.assertIsNone(self.pin.ended_at)
        self.assertIsNotNone(self.pin.update(matches(live()), now=2000.0))


class TestSeveralClubsForOneWord(unittest.TestCase):
    """'real' attrape trois clubs : il n'y a quand meme qu'une carte."""

    def three_reals(self, **kwargs):
        return matches(
            live("Real Sociedad", "Getafe", match_id="2",
                 date="2026-09-06T19:00Z", **kwargs),
            live("Real Madrid", "Betis", match_id="1",
                 date="2026-09-06T17:00Z", **kwargs))

    def test_only_one_card_and_it_is_the_earliest_kickoff(self):
        follow = pinned.Pin("real").update(self.three_reals())
        self.assertEqual(follow.match.home, "Real Madrid")

    def test_it_does_not_hop_from_one_match_to_the_other(self):
        """Une carte qui changerait de match a chaque releve serait illisible."""
        pin = pinned.Pin("real")
        pin.update(self.three_reals())
        for _ in range(5):
            self.assertEqual(pin.update(self.three_reals()).match.home,
                             "Real Madrid")

    def test_the_next_match_takes_the_place_once_the_first_is_gone(self):
        pin = pinned.Pin("real", linger=60.0)
        pin.update(self.three_reals(), now=0.0)

        over = matches(
            live("Real Sociedad", "Getafe", match_id="2",
                 date="2026-09-06T19:00Z"),
            live("Real Madrid", "Betis", match_id="1",
                 date="2026-09-06T17:00Z", state="post", detail="FT"))

        self.assertTrue(pin.update(over, now=10.0).ended)
        follow = pin.update(over, now=100.0)
        self.assertFalse(follow.ended)
        self.assertEqual(follow.match.home, "Real Sociedad")

    def test_a_match_without_a_date_comes_last(self):
        # On ne sait pas quand il a commence : il ne peut pas se dire premier.
        undated = matches(live("Real Betis", "Cadix", match_id="3", date=""),
                          live("Real Madrid", "Getafe", match_id="4",
                               date="2026-09-06T20:00Z"))
        self.assertEqual(pinned.Pin("real").update(undated).match.home,
                         "Real Madrid")


class TestTheJournal(unittest.TestCase):
    def test_the_journal_notes_the_start_and_the_end(self):
        seen = []
        pin = pinned.Pin("angers", linger=10.0, on_log=seen.append)
        pin.update(matches(live(home_score=1)), now=0.0)
        pin.update(matches(live(home_score=1, state="post")), now=0.0)
        pin.update(matches(live(home_score=1, state="post")), now=100.0)

        self.assertEqual(len(seen), 2)
        self.assertIn("carte epinglee sur [Ligue 1] Angers 1 - 0", seen[0])
        self.assertIn("retiree", seen[1])

    def test_nothing_is_logged_at_every_refresh(self):
        seen = []
        pin = pinned.Pin("angers", on_log=seen.append)
        for _ in range(5):
            pin.update(matches(live()))
        self.assertEqual(len(seen), 1)

    def test_a_broken_journal_never_stops_the_daemon(self):
        def broken(_message):
            raise RuntimeError("journal casse")

        pin = pinned.Pin("angers", on_log=broken)
        self.assertIsNotNone(pin.update(matches(live())))


if __name__ == "__main__":
    unittest.main()
