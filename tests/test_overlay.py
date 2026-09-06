"""La carte, testee sans tkinter : Card ne depend que de donnees."""

import unittest
from unittest import mock

from butbutbut import fullscreen, leagues, overlay, screens, watcher

from helpers import (bump, event, fake_fonts, goal_detail, in_minutes,
                     opener_for, payload, red_card_detail)

LIGUE1 = leagues.BY_SLUG["fra.1"]


def one_goal(**bump_kwargs):
    state = {"payload": payload(event(home_score=1, away_score=1))}
    guard = watcher.Watcher([LIGUE1], opener=opener_for(state))
    guard.prime()
    state["payload"] = bump(state["payload"], **bump_kwargs)
    return guard.refresh(LIGUE1)[0]


def one_red_card(**card_kwargs):
    """L'evenement produit par une expulsion, option activee."""
    state = {"payload": payload(event(home_score=1, away_score=1))}
    guard = watcher.Watcher([LIGUE1], opener=opener_for(state), red_cards=True)
    guard.prime()
    state["payload"] = bump(state["payload"], "home", by=0,
                            details=(red_card_detail(**card_kwargs),))
    return guard.refresh(LIGUE1)[0]


def one_prematch():
    """L'evenement d'avant match, option activee."""
    state = {"payload": payload(event(state="pre", clock="0'",
                                      date=in_minutes(5)))}
    guard = watcher.Watcher([LIGUE1], opener=opener_for(state),
                            before_kickoff=10 * 60.0)
    guard.prime()
    return guard.refresh(LIGUE1)[0]


def one_fulltime(*details):
    """Le sifflet final d'un match suivi depuis la premiere periode."""
    state = {"payload": payload(event(state="in", home_score=1, away_score=2,
                                      details=details))}
    guard = watcher.Watcher([LIGUE1], opener=opener_for(state))
    guard.prime()
    state["payload"] = payload(event(state="post", clock="90'+4'", home_score=1,
                                     away_score=2, details=details))
    return guard.refresh(LIGUE1)[0]


def one_phase(first, second):
    """L'evenement produit par le passage d'un etat de match a un autre."""
    state = {"payload": payload(event(**first))}
    guard = watcher.Watcher([LIGUE1], opener=opener_for(state))
    guard.prime()
    state["payload"] = payload(event(**second))
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
        self.assertEqual(card.title_color, overlay.CANCEL_ACCENT)

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


class TestPhaseCards(unittest.TestCase):
    """Coup d'envoi, mi-temps, reprise, fin : meme carte, ton plus discret."""

    def test_kickoff(self):
        event = one_phase({"state": "pre", "clock": "0'"},
                          {"state": "in", "clock": "1'"})
        card = overlay.Card.from_event(event)
        self.assertEqual(card.title, "COUP D'ENVOI")
        self.assertEqual(card.minute, "1'")
        self.assertEqual((card.home_score, card.away_score), (0, 0))

    def test_halftime_restart_and_fulltime(self):
        for first, second, title in (
                ({"state": "in"}, {"state": "in", "status_name": "STATUS_HALFTIME"},
                 "MI-TEMPS"),
                ({"state": "in", "status_name": "STATUS_HALFTIME"}, {"state": "in"},
                 "REPRISE"),
                ({"state": "in"}, {"state": "post", "clock": "90'+4'"},
                 "FIN DU MATCH")):
            card = overlay.Card.from_event(one_phase(first, second))
            self.assertEqual(card.title, title)

    def test_a_phase_card_is_quieter_than_a_goal(self):
        card = overlay.Card.from_event(
            one_phase({"state": "in"}, {"state": "post"}))
        # Le titre est gris, mais le filet garde la couleur du championnat.
        self.assertEqual(card.title_color, overlay.MUTED)
        self.assertEqual(card.accent, LIGUE1.accent)
        # Aucune equipe mise en avant, et pas de troisieme ligne.
        self.assertIsNone(card.side)
        self.assertEqual(card.parts, ())
        self.assertEqual(card.detail, "")

    def test_a_phase_card_is_shorter_than_a_goal_card(self):
        fonts = fake_fonts()
        phase = overlay._layout(
            overlay.Card.from_event(one_phase({"state": "in"}, {"state": "post"})),
            fonts)
        goal = overlay._layout(overlay.Card.demo(), fonts)
        self.assertLess(phase["height"], goal["height"])


class TestRedCardAndPrematchCards(unittest.TestCase):
    """Deux cartes de plus, aussi discretes qu'un temps fort."""

    def test_a_red_card_is_as_quiet_as_a_phase_card(self):
        card = overlay.Card.from_event(one_red_card(team_id="A1"))
        self.assertEqual(card.title, "CARTON ROUGE")
        self.assertEqual(card.title_color, overlay.MUTED)
        self.assertEqual(card.accent, LIGUE1.accent)
        # Aucune equipe en couleur : la carte n'est pas une bonne nouvelle.
        self.assertIsNone(card.side)

    def test_a_red_card_names_the_team_and_the_player(self):
        card = overlay.Card.from_event(
            one_red_card(team_id="A1", minute="62'", player="J. Lefort"))
        self.assertEqual(card.detail, "Stade Rennais : J. Lefort")
        self.assertEqual([t for t, strong in card.parts if strong], ["J. Lefort"])
        self.assertEqual(card.minute, "62'")

    def test_the_prematch_card_counts_down(self):
        card = overlay.Card.from_event(one_prematch())
        self.assertEqual(card.title, "LE MATCH VA COMMENCER")
        self.assertEqual(card.title_color, overlay.MUTED)
        self.assertEqual(card.minute, "")
        self.assertEqual(card.detail, "Coup d'envoi dans 5 min")
        self.assertIsNone(card.side)

    def test_neither_carries_extra_lines(self):
        for card in (overlay.Card.from_event(one_red_card(team_id="H1")),
                     overlay.Card.from_event(one_prematch())):
            self.assertEqual(card.extra, ())


class TestFullTimeCard(unittest.TestCase):
    """La carte de fin de match liste les buteurs, sous le score."""

    def card(self, *details):
        return overlay.Card.from_event(one_fulltime(*details))

    def test_one_line_per_camp_that_scored(self):
        card = self.card(goal_detail("H1", "12'", "M. Lopez", index=1),
                         goal_detail("A1", "58'", "A. Kalimuendo", index=2),
                         goal_detail("A1", "77'", "L. Blas", index=3))
        box = overlay._layout(card, fake_fonts())
        self.assertEqual(["".join(t for t, _ in line) for line in box["extra"]],
                         ["Angers : M. Lopez 12'",
                          "Stade Rennais : A. Kalimuendo 58', L. Blas 77'"])

    def test_the_card_grows_with_its_scorers(self):
        fonts = fake_fonts()
        bare = overlay._layout(self.card(), fonts)
        listed = overlay._layout(
            self.card(goal_detail("H1", "12'", "M. Lopez", index=1)), fonts)
        self.assertEqual(bare["extra"], [])
        self.assertGreater(listed["height"], bare["height"])

    def test_a_goalless_final_stays_a_plain_phase_card(self):
        fonts = fake_fonts()
        box = overlay._layout(self.card(), fonts)
        goal = overlay._layout(overlay.Card.demo(), fonts)
        self.assertLess(box["height"], goal["height"])


class TestLayoutStaysInsideTheCard(unittest.TestCase):
    """Le bug du screenshot : "Eintracht Frankfurt" depassait a gauche."""

    def check(self, card, fonts=None):
        fonts = fonts or fake_fonts()
        box = overlay._layout(card, fonts)
        left = overlay.BAR_WIDTH + overlay.PAD_X
        right = box["width"] - overlay.PAD_X

        home_left = box["home_x"] - fonts["team"].measure(box["home"])
        away_right = box["away_x"] + fonts["team"].measure(box["away"])

        self.assertGreaterEqual(round(home_left, 3), left,
                                "le nom de gauche sort de la carte")
        self.assertLessEqual(round(away_right, 3), right,
                             "le nom de droite sort de la carte")
        # Les noms ne mordent pas sur le score.
        self.assertLessEqual(box["home_x"], box["score_x"])
        self.assertGreaterEqual(box["away_x"], box["score_x"] + box["score_w"])

        # Les lignes de buteurs non plus ne sortent pas de la carte.
        for line in box["extra"]:
            width = sum(overlay._detail_font(fonts, strong).measure(text)
                        for text, strong in line)
            self.assertLessEqual(round(left + width, 3), right,
                                 "une ligne de buteurs sort de la carte")
        return box

    def test_the_case_from_the_screenshot(self):
        box = self.check(overlay.Card(
            title="BUT !", league="BUNDESLIGA", minute="89'",
            home="Eintracht Frankfurt", away="FC Augsburg",
            home_score=1, away_score=4, side="away",
            detail=[("But de ", False), ("F. Rieder", True)],
            accent="#ff5c5c"))
        self.assertEqual(box["home"], "Eintracht Frankfurt")   # rien de tronque

    def test_both_sides_long_or_short(self):
        for home, away in (("Eintracht Frankfurt", "FC Augsburg"),
                           ("FC Augsburg", "Eintracht Frankfurt"),
                           ("Lens", "Lille"),
                           ("A", "Borussia Monchengladbach"),
                           ("Paris Saint-Germain", "Paris Saint-Germain")):
            self.check(overlay.Card(
                title="BUT !", league="LIGUE 1", minute="90'+5'",
                home=home, away=away, home_score=10, away_score=0,
                side="home", detail=[("But de ", False), ("X. Y", True)],
                accent="#f2e34c"))

    def test_absurd_names_are_shortened_not_overflowed(self):
        fonts = fake_fonts()
        box = self.check(overlay.Card(
            title="BUT !", league="LIGUE 1", minute="12'",
            home="Club Athletique et Sportif de la Vallee du Rhone Superieure",
            away="Association Sportive des Amis Reunis du Nord de la France",
            home_score=1, away_score=1, side="home",
            detail=[("But de ", False), ("X. Y", True)], accent="#f2e34c"), fonts)
        self.assertTrue(box["home"].endswith("..."))
        self.assertLessEqual(box["width"], overlay.MAX_WIDTH)

    def test_every_demo_card_fits(self):
        for league in leagues.LEAGUES:
            self.check(overlay.Card.demo(league))

    def test_a_long_list_of_scorers_is_trimmed(self):
        # Un 7-0 avec des noms a rallonge : la ligne est coupee, pas etalee.
        scorers = ", ".join("{}. Kalimuendo-Delacroix {}'".format(letter, 10 + i)
                            for i, letter in enumerate("ABCDEFG"))
        box = self.check(overlay.Card(
            title="FIN DU MATCH", league="LIGUE 1", minute="90'+4'",
            home="Angers", away="Stade Rennais", home_score=7, away_score=0,
            side=None, detail=[], accent="#f2e34c",
            extra=[[("Angers : ", False), (scorers, True)]]))
        self.assertLessEqual(box["width"], overlay.MAX_WIDTH)
        self.assertTrue(box["extra"][0][-1][0].endswith("..."))

    def test_the_number_of_extra_lines_is_capped(self):
        box = self.check(overlay.Card(
            title="FIN DU MATCH", league="LIGUE 1", minute="90'",
            home="Lens", away="Lille", home_score=1, away_score=1,
            side=None, detail=[], accent="#f2e34c",
            extra=[[("ligne {} ".format(i), False)] for i in range(12)]))
        self.assertEqual(len(box["extra"]), overlay.MAX_EXTRA_LINES)

    def test_an_unbreakable_scorer_line_is_dropped_not_overflowed(self):
        # Une police enorme : rien ne rentre, la ligne saute entierement.
        box = self.check(
            overlay.Card(
                title="FIN DU MATCH", league="LIGUE 1", minute="90'",
                home="Lens", away="Lille", home_score=1, away_score=0,
                side=None, detail=[], accent="#f2e34c",
                extra=[[("Lens : ", False), ("Un Nom Interminable 12'", True)]]),
            fake_fonts(detail=800, scorer=800))
        self.assertEqual(box["extra"], [])

    def test_a_wide_score_still_fits(self):
        self.check(overlay.Card(
            title="BUT !", league="LIGUE 1", minute="90'",
            home="Bayern Munich", away="Dinamo Zagreb",
            home_score=19, away_score=17, side="home",
            detail=[], accent="#f2e34c"))


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


class TestStackFullscreen(unittest.TestCase):
    """Le garde-fou plein ecran, sans ouvrir la moindre fenetre."""

    def test_the_option_is_off_by_default(self):
        self.assertEqual(overlay.Stack().retry_fullscreen, 0.0)
        self.assertEqual(overlay.Stack(retry_fullscreen=30).retry_fullscreen, 30.0)
        # Une duree negative ou absurde n'active rien.
        self.assertEqual(overlay.Stack(retry_fullscreen=-5).retry_fullscreen, 0.0)
        self.assertEqual(overlay.Stack(retry_fullscreen=None).retry_fullscreen, 0.0)

    def test_the_question_is_asked_about_the_chosen_screen(self):
        stack = overlay.Stack()
        with mock.patch.object(fullscreen, "covers", return_value=True) as asked:
            self.assertTrue(stack.hidden_by_fullscreen())
        self.assertEqual(asked.call_args[0][0], stack._monitor)

    def test_a_failing_detection_never_stops_a_card(self):
        # fullscreen.covers() avale deja tout ; on verifie qu'aucune exception
        # ne remonte jusqu'a l'affichage, meme si Win32 part en vrille.
        stack = overlay.Stack()
        with mock.patch.object(fullscreen, "_foreground_window",
                               side_effect=OSError("boom")), \
                mock.patch.object(fullscreen.sys, "platform", "win32"):
            self.assertFalse(stack.hidden_by_fullscreen())

    def test_the_journal_is_optional_and_a_broken_logger_is_harmless(self):
        overlay.Stack()._log("rien ne se passe")

        seen = []
        overlay.Stack(on_log=seen.append)._log("note")
        self.assertEqual(seen, ["note"])

        def broken(_message):
            raise RuntimeError("journal casse")

        overlay.Stack(on_log=broken)._log("note")


if __name__ == "__main__":
    unittest.main()
