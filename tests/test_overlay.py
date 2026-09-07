"""La carte, testee sans tkinter : Card ne depend que de donnees."""

import unittest
from unittest import mock

from butbutbut import espn, fullscreen, i18n, leagues, overlay, screens, watcher
from butbutbut import crests, espn, leagues, overlay, screens, watcher

from helpers import (bump, event, fake_fonts, goal_detail, in_minutes,
                     opener_for, payload, red_card_detail)

LIGUE1 = leagues.BY_SLUG["fra.1"]

# Un chemin d'ecusson n'a pas besoin d'exister pour que _layout lui reserve sa
# place : la geometrie se calcule avant que tkinter n'ouvre quoi que ce soit.
CREST = "ecusson.png"


def one_goal(event_kwargs=None, **bump_kwargs):
    state = {"payload": payload(event(home_score=1, away_score=1,
                                      **(event_kwargs or {})))}
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
def one_catchup(count=2, scorer="F. Sotoca"):
    """Le resume de sortie de veille : `count` matchs ont bouge pendant le trou."""
    changes = []
    for index in range(1, count + 1):
        board = payload(event(
            match_id=str(index), home="Equipe {}".format(index),
            away="Adversaire {}".format(index), state="in", home_score=1,
            details=(goal_detail("H" + str(index), "23'", scorer, index=index),)))
        match = espn.parse(board, LIGUE1)[0]
        changes.append(watcher.Change(match, 0, 0, match.plays))

    head = changes[0].match
    return watcher.Event(kind=watcher.CATCHUP, match=head, side=None, team="",
                         opponent="", home_score=head.home_score,
                         away_score=head.away_score, delta=0, play=None,
                         changes=changes, gap=40 * 60.0)


def goal_card(side="home", crest=None, **event_kwargs):
    """La carte d'un but marque par `side`, avec l'habillage demande."""
    return overlay.Card.from_event(
        one_goal(event_kwargs=event_kwargs, side=side), crest)


def _card(home="Angers", away="Stade Rennais", home_logo=None, away_logo=None,
          home_score=1, away_score=2):
    return overlay.Card(
        title="BUT !", league="LIGUE 1", minute="35'",
        home=home, away=away, home_score=home_score, away_score=away_score,
        side="home", detail=[("But de ", False), ("C. Arcus", True)],
        accent="#f2e34c", home_logo=home_logo, away_logo=away_logo)


def one_phase(first, second):
    """L'evenement produit par le passage d'un etat de match a un autre."""
    state = {"payload": payload(event(**first))}
    guard = watcher.Watcher([LIGUE1], opener=opener_for(state))
    guard.prime()
    state["payload"] = payload(event(**second))
    return guard.refresh(LIGUE1)[0]


def setUpModule():
    # Ces tests affirment des formulations francaises. Sans cet epinglage ils
    # passeraient sur une machine francaise et echoueraient sur la CI, dont les
    # machines sont anglaises.
    i18n.use("fr")

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


class TestCatchUpCard(unittest.TestCase):
    """Le resume de sortie de veille : une carte discrete, une ligne par match.

    Elle ne rejoue pas la troncature de la fin de match, elle la reutilise :
    c'est `_layout` qui coupe, en hauteur comme en largeur.
    """

    def test_it_looks_like_a_key_moment_not_like_a_goal(self):
        card = overlay.Card.from_event(one_catchup())
        self.assertEqual(card.title, "PENDANT TON ABSENCE")
        self.assertEqual(card.title_color, overlay.MUTED)
        self.assertEqual(card.accent, LIGUE1.accent)
        # Aucune equipe en couleur : personne ne vient de marquer a l'instant.
        self.assertIsNone(card.side)
        self.assertEqual(card.minute, "40 min")

    def test_the_first_match_is_on_the_score_line_and_the_others_below(self):
        card = overlay.Card.from_event(one_catchup(count=3))
        self.assertEqual((card.home, card.away), ("Equipe 1", "Adversaire 1"))
        self.assertEqual(card.detail, "avant 0 - 0 : F. Sotoca 23'")
        self.assertEqual(["".join(t for t, _ in line) for line in card.extra], [
            "Equipe 2 1 - 0 Adversaire 2 (avant 0 - 0) : F. Sotoca 23'",
            "Equipe 3 1 - 0 Adversaire 3 (avant 0 - 0) : F. Sotoca 23'",
        ])

    def test_a_long_night_is_capped_like_a_long_list_of_scorers(self):
        card = overlay.Card.from_event(one_catchup(count=12))
        box = overlay._layout(card, fake_fonts())
        self.assertEqual(len(box["extra"]), overlay.MAX_EXTRA_LINES)

    def test_a_line_too_wide_is_cut_with_an_ellipsis(self):
        card = overlay.Card.from_event(
            one_catchup(count=2, scorer="Un Nom Vraiment Interminable " * 4))
        box = overlay._layout(card, fake_fonts())
        self.assertTrue(box["extra"][0][-1][0].endswith("..."))
class TestTeamColourOnTheCard(unittest.TestCase):
    """L'equipe qui marque prend sa couleur, le filet garde celle du championnat."""

    def test_a_readable_club_colour_wins_over_the_league(self):
        card = goal_card("home", away_colors=("dc052d", "1a1a1a"),
                         home_colors=("dc052d", "1a1a1a"))
        self.assertEqual(card.team_accent, "#dc052d")
        self.assertEqual(card.accent, LIGUE1.accent)      # le filet ne bouge pas

    def test_an_unreadable_club_colour_takes_the_alternate(self):
        # Troyes : 0000bf sur le fond de la carte, c'est du noir sur du noir.
        card = goal_card("away", away_colors=("0000bf", "fafafc"))
        self.assertEqual(card.team_accent, "#fafafc")

    def test_two_unreadable_colours_keep_the_league_colour(self):
        card = goal_card("away", away_colors=("000000", "000000"))
        self.assertEqual(card.team_accent, LIGUE1.accent)

    def test_a_club_without_colours_keeps_the_league_colour(self):
        self.assertEqual(goal_card("home").team_accent, LIGUE1.accent)

    def test_the_colour_taken_is_the_one_of_the_scoring_side(self):
        card = goal_card("away", home_colors=("dc052d", "dc052d"),
                         away_colors=("ffee00", "ffee00"))
        self.assertEqual(card.team_accent, "#ffee00")

    def test_a_cancelled_goal_ignores_the_club_colour(self):
        card = overlay.Card.from_event(
            one_goal(event_kwargs={"home_colors": ("dc052d", "dc052d")},
                     side="home", by=-1))
        self.assertEqual(card.team_accent, overlay.CANCEL_ACCENT)
        self.assertEqual(card.accent, overlay.CANCEL_ACCENT)

    def test_a_phase_card_has_no_club_colour(self):
        card = overlay.Card.from_event(
            one_phase({"state": "in"}, {"state": "post"}))
        self.assertEqual(card.team_accent, LIGUE1.accent)

    def test_the_colour_shown_is_always_readable_or_the_league_one(self):
        for color, alternate in (("0000bf", "fafafc"), ("000000", "000000"),
                                 ("144992", "ffffff"), ("ffee00", "272726"),
                                 ("", ""), ("bidon", "pareil")):
            card = goal_card("home", home_colors=(color, alternate))
            self.assertTrue(
                card.team_accent == LIGUE1.accent
                or crests.readable(card.team_accent, overlay.CARD_BG),
                (color, alternate, card.team_accent))


class TestCrestsOnTheCard(unittest.TestCase):
    """L'ecusson vient du cache, jamais du reseau."""

    def test_without_a_cache_a_card_has_no_crest(self):
        card = goal_card("home", home_logo="https://exemple/1.png")
        self.assertIsNone(card.home_logo)
        self.assertIsNone(card.away_logo)

    def test_a_cached_crest_lands_on_the_card(self):
        cache = _FakeCache({"https://exemple/1.png": CREST})
        card = goal_card("home", crest=cache,
                         home_logo="https://exemple/1.png",
                         away_logo="https://exemple/2.png")
        self.assertEqual(card.home_logo, CREST)
        self.assertIsNone(card.away_logo)      # pas encore telecharge
        self.assertEqual(cache.asked, ["https://exemple/1.png",
                                       "https://exemple/2.png"])

    def test_a_match_without_logos_asks_nothing(self):
        cache = _FakeCache({})
        goal_card("home", crest=cache)
        self.assertEqual(cache.asked, [])

    def test_a_cache_that_breaks_does_not_break_the_card(self):
        card = goal_card("home", crest=_BrokenCache(),
                         home_logo="https://exemple/1.png")
        self.assertIsNone(card.home_logo)
        self.assertEqual(card.home, "Angers")   # la carte est intacte

    def test_a_demo_card_asks_for_both_crests(self):
        cache = _FakeCache({})
        overlay.Card.demo(LIGUE1, cache)
        self.assertEqual(len(cache.asked), 2)
        for url in cache.asked:
            self.assertTrue(url.startswith("https://"), url)
            self.assertTrue(url.endswith(".png"), url)


class _FakeCache:
    """Un cache d'ecussons sans disque ni reseau : il sait juste qui a demande quoi."""

    def __init__(self, known):
        self.known = known
        self.asked = []

    def get(self, url):
        self.asked.append(url)
        return self.known.get(url)


class _BrokenCache:
    """Le disque a disparu sous les pieds du daemon."""

    def get(self, url):
        raise OSError("plus de disque")


class _FakeImage:
    """Ce que tkinter rend d'un PNG : une taille, un zoom, un sous-echantillonnage."""

    def __init__(self, size=500):
        self.size = size
        self.factors = []

    def width(self):
        return self.size

    def height(self):
        return self.size

    def zoom(self, x, _y):
        self.factors.append(("zoom", x))
        self.size *= x
        return self

    def subsample(self, x, _y):
        self.factors.append(("subsample", x))
        self.size //= x
        return self


class _FakeTk:
    """Le module tkinter, reduit a ce dont crests.photo a besoin."""

    def __init__(self, size=500, broken=False):
        self.size = size
        self.broken = broken
        self.opened = []

    def PhotoImage(self, file=None, master=None):    # noqa: N802 - nom tkinter
        self.opened.append(file)
        if self.broken:
            raise RuntimeError("couldn't recognize data in image file")
        return _FakeImage(self.size)


class TestCrestImages(unittest.TestCase):
    """Le chargement des images, avec un tkinter factice : la CI n'a pas d'ecran."""

    def box(self, card):
        return overlay._layout(card, fake_fonts())

    def test_each_crest_is_loaded_and_kept(self):
        card = _card(home_logo=CREST, away_logo=CREST)
        box = self.box(card)
        tk = _FakeTk()
        images = overlay.load_logos(tk, card, box)
        # La reference est ce qui compte : sans elle, tkinter oublie l'image
        # et l'ecusson disparait de la carte affichee.
        self.assertEqual(sorted(images), ["away", "home"])
        self.assertEqual(len(tk.opened), 2)
        for image in images.values():
            self.assertLessEqual(image.size, box["logo"])

    def test_a_card_without_crest_loads_nothing(self):
        card = _card()
        tk = _FakeTk()
        self.assertEqual(overlay.load_logos(tk, card, self.box(card)), {})
        self.assertEqual(tk.opened, [])

    def test_only_the_side_that_has_one(self):
        card = _card(away_logo=CREST)
        images = overlay.load_logos(_FakeTk(), card, self.box(card))
        self.assertEqual(list(images), ["away"])

    def test_a_corrupted_png_gives_no_image_and_no_error(self):
        card = _card(home_logo=CREST, away_logo=CREST)
        images = overlay.load_logos(_FakeTk(broken=True), card, self.box(card))
        self.assertEqual(images, {})


def check_inside(case, card, fonts=None):
    """Verifie que rien de la carte ne sort de la carte. Rend la mise en page.

    Partage par les deux classes ci-dessous : les ecussons doivent respecter
    exactement les memes bornes que les noms d'equipes.
    """
    fonts = fonts or fake_fonts()
    box = overlay._layout(card, fonts)
    left = overlay.BAR_WIDTH + overlay.PAD_X
    right = box["width"] - overlay.PAD_X

    home_left = box["home_x"] - fonts["team"].measure(box["home"])
    away_right = box["away_x"] + fonts["team"].measure(box["away"])

    case.assertGreaterEqual(round(home_left, 3), left,
                            "le nom de gauche sort de la carte")
    case.assertLessEqual(round(away_right, 3), right,
                         "le nom de droite sort de la carte")
    # Les noms ne mordent pas sur le score.
    case.assertLessEqual(box["home_x"], box["score_x"])
    case.assertGreaterEqual(box["away_x"], box["score_x"] + box["score_w"])

    # Les ecussons non plus : ils tiennent dans la carte, a l'exterieur des
    # noms, sans jamais mordre dessus.
    size = box["logo"]
    if size and card.home_logo:
        case.assertGreaterEqual(round(box["home_logo_x"] - size, 3), left,
                                "l'ecusson de gauche sort de la carte")
        case.assertLessEqual(round(box["home_logo_x"], 3), round(home_left, 3))
    if size and card.away_logo:
        case.assertLessEqual(round(box["away_logo_x"] + size, 3), right,
                             "l'ecusson de droite sort de la carte")
        case.assertGreaterEqual(round(box["away_logo_x"], 3), round(away_right, 3))
    return box


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
        return check_inside(self, card, fonts)

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


class TestCrestGeometry(unittest.TestCase):
    """Les ecussons entrent dans la reserve de _layout sans la casser."""

    def check(self, card, fonts=None):
        return check_inside(self, card, fonts)

    def test_a_card_with_crests_stays_inside(self):
        for home, away in ((CREST, CREST), (CREST, None), (None, CREST)):
            self.check(_card(home_logo=home, away_logo=away))

    def test_long_names_and_crests_together(self):
        for home, away in (("Eintracht Frankfurt", "FC Augsburg"),
                           ("A", "Borussia Monchengladbach"),
                           ("Club Athletique et Sportif de la Vallee du Rhone",
                            "Association Sportive des Amis Reunis du Nord")):
            box = self.check(_card(home, away, CREST, CREST))
            self.assertLessEqual(box["width"], overlay.MAX_WIDTH)

    def test_crests_widen_the_card(self):
        without = overlay._layout(_card(), fake_fonts())
        with_crests = overlay._layout(_card(home_logo=CREST, away_logo=CREST),
                                      fake_fonts())
        self.assertGreater(with_crests["width"], without["width"])
        self.assertEqual(with_crests["logo"], overlay._logo_size(fake_fonts()))
        self.assertEqual(without["logo"], 0)

    def test_the_place_is_reserved_on_both_sides_even_with_one_crest(self):
        """Sinon le score se decalerait selon les ecussons deja telecharges."""
        both = overlay._layout(_card(home_logo=CREST, away_logo=CREST),
                               fake_fonts())
        only_home = overlay._layout(_card(home_logo=CREST), fake_fonts())
        self.assertEqual(only_home["width"], both["width"])
        self.assertEqual(only_home["score_x"], both["score_x"])
        self.assertEqual(only_home["home_x"], both["home_x"])

    def test_the_row_makes_room_for_a_tall_crest(self):
        fonts = fake_fonts()
        short = overlay._layout(_card(), fonts)
        tall = overlay._layout(_card(home_logo=CREST, away_logo=CREST), fonts)
        self.assertGreaterEqual(tall["height"], short["height"])
        # L'ecusson tient dans la carte, en hauteur aussi.
        size = tall["logo"]
        self.assertGreaterEqual(tall["score_y"] - size / 2.0, 0)
        self.assertLessEqual(tall["score_y"] + size / 2.0, tall["height"])

    def test_a_crest_never_lands_on_the_score(self):
        box = overlay._layout(_card(home_logo=CREST, away_logo=CREST,
                                    home_score=19, away_score=17), fake_fonts())
        self.assertLess(box["home_logo_x"], box["score_x"])
        self.assertGreater(box["away_logo_x"], box["score_x"] + box["score_w"])


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


class _FakeCanvas:
    """Le canvas de tkinter, reduit a ce que _draw lui demande."""

    def __init__(self, *_args, **_kwargs):
        pass

    def pack(self, **_kwargs):
        pass

    def delete(self, *_args):
        pass

    def configure(self, **_kwargs):
        pass

    def bbox(self, *_args):
        return (0, 0, 10, 10)

    def __getattr__(self, _name):
        # create_text, create_rectangle, create_image... : le dessin ne nous
        # interesse pas ici, seul l'ordre des appels a la fenetre compte.
        return lambda *args, **kwargs: 1


class _FakeWindow:
    """Une fenetre qui note ce qu'on lui fait, dans l'ordre."""

    def __init__(self, log):
        self.log = log
        self.alpha = 0.0

    def withdraw(self):
        self.log.append("withdraw")

    def overrideredirect(self, _flag):
        self.log.append("overrideredirect")

    def wm_attributes(self, name, *value):
        if not value:
            return self.alpha
        if name == "-alpha":
            self.alpha = float(value[0])
        return None

    def deiconify(self):
        self.log.append("deiconify")

    def geometry(self, _spec):
        pass

    def config(self, **_kwargs):
        pass

    def after(self, _ms, _callback):
        # Les rappels ne partent pas : la carte reste au moment ou on l'a vue.
        return "timer"

    def winfo_exists(self):
        return True

    def winfo_id(self):
        return 1

    def update_idletasks(self):
        pass

    def destroy(self):
        self.log.append("destroy")


class _FakeStack:
    """De la pile, _Panel ne lit que ces trois choses."""

    def __init__(self, log):
        self.log = log
        self.opacity = 1.0
        self.fonts = fake_fonts()
        self.root = None
        self.tk = self

    def Toplevel(self, _root):                       # noqa: N802 - nom tkinter
        return _FakeWindow(self.log)

    def Canvas(self, *args, **kwargs):               # noqa: N802 - nom tkinter
        return _FakeCanvas(*args, **kwargs)

    def PhotoImage(self, **_kwargs):                 # noqa: N802 - nom tkinter
        return None


class TestACardNeverStealsTheScreen(unittest.TestCase):
    """Les styles Win32 se posent avant l'affichage, jamais apres.

    C'est tout ce qui separe une carte discrete d'une carte qui sort un jeu de
    son plein ecran : Windows tranche l'activation quand la fenetre apparait.
    Poses apres `deiconify`, WS_EX_NOACTIVATE et WS_EX_TOOLWINDOW arrivent une
    fois le premier plan reclame et le bouton de barre des taches cree.
    """

    def setUp(self):
        self.log = []
        self.stack = _FakeStack(self.log)
        self.card = overlay.Card.demo(LIGUE1, None)
        patch = mock.patch.object(overlay, "_make_click_through",
                                  lambda _window: self.log.append("styles"))
        patch.start()
        self.addCleanup(patch.stop)

    def test_they_are_set_while_the_window_is_still_hidden(self):
        overlay._Panel(self.stack, self.card)
        self.assertIn("styles", self.log)
        self.assertNotIn("deiconify", self.log)
        self.assertLess(self.log.index("withdraw"), self.log.index("styles"))

    def test_a_goal_card_shows_itself_only_afterwards(self):
        toast = overlay._Toast(self.stack, self.card, 6.0)
        toast.start()
        self.assertLess(self.log.index("styles"), self.log.index("deiconify"))

    def test_the_pinned_card_too(self):
        panel = overlay._Panel(self.stack, self.card)
        panel.reveal()
        self.assertLess(self.log.index("styles"), self.log.index("deiconify"))

    def test_once_is_enough(self):
        # Les styles tiennent jusqu'a la fin de la fenetre : les reposer a
        # chaque affichage ne ferait que masquer l'ordre qui compte.
        toast = overlay._Toast(self.stack, self.card, 6.0)
        toast.start()
        self.assertEqual(self.log.count("styles"), 1)


def one_match(**kwargs):
    """Un Match, tel que le tableau de bord le donnerait."""
    kwargs.setdefault("state", "in")
    return espn.parse(payload(event(**kwargs)), LIGUE1)[0]


class TestPinnedCard(unittest.TestCase):
    """La carte epinglee : elle montre ou en est le match, pas ce qui arrive."""

    def test_it_carries_the_score_and_the_minute(self):
        card = overlay.Card.pinned(
            one_match(home_score=1, away_score=2, clock="61'"))
        self.assertEqual(card.title, "EN DIRECT")
        self.assertEqual(card.league, "LIGUE 1")
        self.assertEqual(card.minute, "61'")
        self.assertEqual((card.home_score, card.away_score), (1, 2))
        self.assertEqual(card.text_line(), "Angers 1 - 2 Stade Rennais")

    def test_it_is_as_quiet_as_a_phase_card(self):
        # Le titre gris est la marque des cartes muettes : rien ici ne joue de
        # son, et aucune equipe n'est mise en couleur - la couleur d'un club
        # veut dire "elle vient de marquer", pas "elle mene".
        card = overlay.Card.pinned(one_match(home_score=3))
        self.assertEqual(card.title_color, overlay.MUTED)
        self.assertEqual(card.accent, LIGUE1.accent)
        self.assertEqual(card.team_accent, LIGUE1.accent)
        self.assertIsNone(card.side)
        self.assertEqual(card.parts, ())
        self.assertEqual(card.extra, ())

    def test_the_final_whistle_changes_the_title(self):
        card = overlay.Card.pinned(
            one_match(state="post", clock="90'+4'", detail="FT"), ended=True)
        self.assertEqual(card.title, "FIN DU MATCH")
        self.assertEqual(card.minute, "90'+4'")

    def test_a_match_without_a_clock_falls_back_on_the_detail(self):
        card = overlay.Card.pinned(one_match(clock="", detail="HT"))
        self.assertEqual(card.minute, "HT")

    def test_the_crests_come_from_the_cache_only(self):
        cache = _FakeCache({"https://exemple/1.png": CREST})
        card = overlay.Card.pinned(
            one_match(home_logo="https://exemple/1.png",
                      away_logo="https://exemple/2.png"), crest=cache)
        self.assertEqual(card.home_logo, CREST)
        self.assertIsNone(card.away_logo)      # pas encore telecharge

    def test_a_broken_cache_does_not_break_the_card(self):
        card = overlay.Card.pinned(
            one_match(home_logo="https://exemple/1.png"), crest=_BrokenCache())
        self.assertIsNone(card.home_logo)
        self.assertEqual(card.home, "Angers")

    def test_it_is_shorter_than_a_goal_card(self):
        fonts = fake_fonts()
        pinned_box = overlay._layout(overlay.Card.pinned(one_match()), fonts)
        goal = overlay._layout(overlay.Card.demo(), fonts)
        self.assertLess(pinned_box["height"], goal["height"])
        check_inside(self, overlay.Card.pinned(one_match()))

    def test_the_demo_card_shows_the_same_thing(self):
        """Sans --test, personne ne pourrait regler cette carte-la."""
        for league in leagues.LEAGUES:
            card = overlay.Card.demo_pinned(league)
            self.assertEqual(card.title, "EN DIRECT")
            self.assertEqual(card.league, league.label)
            self.assertIsNone(card.side)
            self.assertEqual(card.parts, ())
            check_inside(self, card)


class TestPinnedAndTheStackTogether(unittest.TestCase):
    """Ou vit la carte epinglee par rapport a la pile des fugaces."""

    def setUp(self):
        self.monitor = screens.Monitor(0, 0, 1920, 1080, primary=True)
        self.pinned = (400, 90)
        self.sizes = [(400, 100), (400, 120), (360, 100)]

    def test_without_a_pinned_card_nothing_changes(self):
        anchor, places = overlay.layout_stack(self.monitor, None, self.sizes,
                                              "bottom-right")
        self.assertIsNone(anchor)
        self.assertEqual(places, overlay.stack_positions(
            self.monitor, self.sizes, "bottom-right"))

    def test_the_pinned_card_takes_the_corner(self):
        anchor, _places = overlay.layout_stack(self.monitor, self.pinned,
                                               self.sizes, "bottom-right")
        self.assertEqual(anchor,
                         self.monitor.place(400, 90, "bottom-right"))

    def test_the_ephemeral_stack_starts_after_it(self):
        anchor, places = overlay.layout_stack(self.monitor, self.pinned,
                                              self.sizes, "bottom-right")
        # Une carte de but ne se pose jamais sur l'epinglee : elle commence
        # au-dessus, l'espace habituel en plus.
        self.assertEqual(places[0][1] + self.sizes[0][1] + overlay.STACK_GAP,
                         anchor[1])
        for (below, (_x, y)), (_width, height) in zip(
                enumerate(places[1:]), self.sizes[1:]):
            self.assertLessEqual(y + height, places[below][1])

    def test_five_goals_never_push_it_out(self):
        """Le plafond de cinq cartes ne compte que les fugaces."""
        alone, _ = overlay.layout_stack(self.monitor, self.pinned, [],
                                        "bottom-right")
        crowded, places = overlay.layout_stack(
            self.monitor, self.pinned, [(400, 100)] * overlay.MAX_VISIBLE,
            "bottom-right")
        self.assertEqual(alone, crowded)
        self.assertEqual(len(places), overlay.MAX_VISIBLE)

    def test_it_works_from_every_corner(self):
        for corner in screens.CORNERS:
            anchor, places = overlay.layout_stack(self.monitor, self.pinned,
                                                  self.sizes, corner)
            self.assertEqual(anchor, self.monitor.place(400, 90, corner))
            for (x, y), (width, height) in zip(places, self.sizes):
                self.assertGreaterEqual(x, self.monitor.x)
                self.assertGreaterEqual(y, self.monitor.y)
                self.assertLessEqual(y + height, self.monitor.y + self.monitor.height)

    def test_an_empty_stack_leaves_nothing_but_the_pinned_card(self):
        anchor, places = overlay.layout_stack(self.monitor, self.pinned, [])
        self.assertIsNotNone(anchor)
        self.assertEqual(places, [])


class TestStackKnowsItsPinnedCard(unittest.TestCase):
    """Ce qu'on peut verifier de la pile sans ouvrir la moindre fenetre."""

    def test_a_fresh_stack_has_none(self):
        stack = overlay.Stack()
        self.assertIsNone(stack.pinned)
        self.assertEqual(len(stack), 0)

    def test_unpinning_nothing_is_harmless(self):
        # Le daemon appelle unpin() a chaque releve sans carte epinglee : ca ne
        # doit ni ouvrir tkinter ni se plaindre.
        stack = overlay.Stack()
        stack.unpin()
        self.assertIsNone(stack.root)


if __name__ == "__main__":
    unittest.main()
