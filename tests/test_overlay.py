"""La carte, testee sans tkinter : Card ne depend que de donnees."""

import unittest

from butbutbut import leagues, overlay, screens, watcher

from helpers import bump, event, goal_detail, opener_for, payload

LIGUE1 = leagues.BY_SLUG["fra.1"]


def one_goal(**bump_kwargs):
    state = {"payload": payload(event(home_score=1, away_score=1))}
    guard = watcher.Watcher([LIGUE1], opener=opener_for(state))
    guard.prime()
    state["payload"] = bump(state["payload"], **bump_kwargs)
    return guard.refresh(LIGUE1)[0]


class TestCard(unittest.TestCase):
    def test_card_carries_league_score_and_scorer(self):
        goal = one_goal(side="away",
                        details=(goal_detail("A1", "58'", "A. Kalimuendo", index=1),))
        card = overlay.Card.from_event(goal)

        self.assertEqual(card.title, "BUT !")
        self.assertEqual(card.league, "LIGUE 1")
        self.assertEqual(card.minute, "58'")
        self.assertEqual((card.home, card.away), ("Angers", "Stade Rennais"))
        self.assertEqual((card.home_score, card.away_score), (1, 2))
        self.assertEqual(card.side, "away")
        self.assertEqual(card.detail, "But de A. Kalimuendo")
        self.assertEqual(card.accent, LIGUE1.accent)
        self.assertEqual(card.text_line(), "Angers 1 - 2 Stade Rennais")

    def test_scorer_is_the_highlighted_part(self):
        goal = one_goal(side="home",
                        details=(goal_detail("H1", "12'", "H. Kane", index=2),))
        card = overlay.Card.from_event(goal)
        self.assertEqual([text for text, strong in card.parts if strong],
                         ["H. Kane"])

    def test_cancelled_goal_uses_the_warning_colour(self):
        goal = one_goal(side="home", by=-1)
        card = overlay.Card.from_event(goal)
        self.assertEqual(card.title, "BUT ANNULE")
        self.assertEqual(card.accent, overlay.CANCEL_ACCENT)
        self.assertTrue(card.muted_title)

    def test_demo_card_for_each_league(self):
        for league in leagues.LEAGUES:
            card = overlay.Card.demo(league)
            self.assertEqual(card.league, league.label)
            self.assertEqual(card.accent, league.accent)
            self.assertIn(card.side, ("home", "away"))
            self.assertTrue(card.detail.startswith("But de "))
            # Chaque demo met un buteur en valeur, comme un vrai but.
            self.assertEqual(len([t for t, strong in card.parts if strong]), 1)

    def test_card_without_details_has_no_empty_slot(self):
        card = overlay.Card.demo()
        self.assertTrue(card.parts)
        self.assertTrue(card.detail)


class TestStackPositions(unittest.TestCase):
    """L'empilement, teste sans tkinter : ce n'est que de la geometrie."""

    def setUp(self):
        self.monitor = screens.Monitor(0, 0, 1920, 1080, primary=True)
        self.sizes = [(400, 100), (400, 120), (360, 100)]

    def test_a_single_card_sits_in_the_corner(self):
        places = overlay.stack_positions(self.monitor, [(400, 100)], "bottom-right")
        self.assertEqual(places, [self.monitor.place(400, 100, "bottom-right")])

    def test_bottom_right_stack_grows_upwards_without_overlapping(self):
        places = overlay.stack_positions(self.monitor, self.sizes, "bottom-right")
        self.assertEqual(len(places), 3)

        # La plus recente est collee au coin, les autres remontent.
        corner_y = places[0][1]
        self.assertLess(places[1][1], corner_y)
        self.assertLess(places[2][1], places[1][1])

        # Aucune carte n'en recouvre une autre.
        for (below, (_x, y)), (width, height) in zip(
                enumerate(places[1:]), self.sizes[1:]):
            previous_top = places[below][1]
            self.assertLessEqual(y + height, previous_top)

    def test_gap_between_two_cards(self):
        places = overlay.stack_positions(self.monitor, self.sizes, "bottom-right",
                                         gap=10)
        self.assertEqual(places[0][1] - (places[1][1] + self.sizes[1][1]), 10)

    def test_top_left_stack_grows_downwards(self):
        places = overlay.stack_positions(self.monitor, self.sizes, "top-left")
        self.assertGreater(places[1][1], places[0][1])
        self.assertEqual({x for x, _y in places}, {screens.MARGIN})

    def test_cards_are_right_aligned_on_the_right_hand_corners(self):
        places = overlay.stack_positions(self.monitor, self.sizes, "bottom-right")
        for (x, _y), (width, _height) in zip(places, self.sizes):
            self.assertEqual(x + width, 1920 - screens.MARGIN)

    def test_stack_never_leaves_the_screen(self):
        small = screens.Monitor(0, 0, 800, 300)
        sizes = [(400, 100)] * 6
        for x, y in overlay.stack_positions(small, sizes, "bottom-right"):
            self.assertGreaterEqual(y, small.y)
            self.assertLessEqual(y + 100, small.y + small.height)

    def test_second_monitor_offset_is_kept(self):
        second = screens.Monitor(1920, 0, 1920, 1080)
        places = overlay.stack_positions(second, self.sizes, "bottom-right")
        for x, _y in places:
            self.assertGreaterEqual(x, 1920)


if __name__ == "__main__":
    unittest.main()
