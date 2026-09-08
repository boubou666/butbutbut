"""La mise en page des cartes, figee en plans ASCII de reference.

    python tools/plans.py

C'est la commande - la seule - qui regenere `tests/plans/*.txt` apres un
changement voulu de mise en page. Le diff de la PR montre alors le deplacement
en clair : une ligne de tableau qui passe de 235 a 237, un ecusson qui glisse
d'une colonne dans le dessin.

Ce que ces tests ajoutent aux autres tests de `test_overlay.py` : ceux-la
verifient des invariants ponctuels - le score est centre, un carton ne mord pas
sur un nom - et laissaient donc passer sans broncher un decalage de deux
pixels. Ceux-ci comparent la carte entiere a ce qui est range dans le depot.

Le mecanisme, et surtout ce qui le rend identique sur les trois systemes et les
cinq versions de Python de la CI, est explique dans `tests/blueprint.py`.
"""

import os
import unittest

import blueprint

from butbutbut import overlay


class TestPlansMatchTheirReference(unittest.TestCase):
    """Le coeur : ce que le code dessine aujourd'hui contre le depot."""

    maxDiff = None

    def test_each_card_matches_its_plan(self):
        for name, _scale, _note, _card in blueprint.SCENARIOS:
            with self.subTest(plan=name):
                self.assertEqual(
                    blueprint.render(name), blueprint.stored(name),
                    "le plan '{}' a change : relire le diff, puis "
                    "`python tools/plans.py` si le changement est voulu"
                    .format(name))

    def test_no_reference_is_left_behind(self):
        """Un scenario renomme laisse un fichier orphelin, jamais relu."""
        stored = sorted(name[:-4] for name in os.listdir(blueprint.PLANS)
                        if name.endswith(".txt"))
        self.assertEqual(stored,
                         sorted(name for name, _s, _n, _c in blueprint.SCENARIOS))

    def test_the_command_would_rewrite_nothing(self):
        """`python tools/plans.py` sur un depot propre ne changerait rien."""
        self.assertEqual(blueprint.write_all(dry_run=True), [])


class TestPlansStayReadable(unittest.TestCase):
    """Une reference illisible finit supprimee : autant la tenir."""

    def test_the_references_are_pure_ascii(self):
        for name, _scale, _note, _card in blueprint.SCENARIOS:
            with self.subTest(plan=name):
                text = blueprint.stored(name)
                self.assertEqual(text.encode("ascii").decode("ascii"), text)

    def test_a_plan_shows_where_everything_is(self):
        """Le nom, le score, l'ecusson et le carton se lisent dans le plan."""
        text = blueprint.stored("cartons-rouges")
        for expected in ("Angers", "Stade Rennais", "score dom.", "separateur",
                         "ecusson dom.", "ecusson ext.", "carton", "filet"):
            self.assertIn(expected, text)
        # Le dessin, lui, se lit sans le tableau : le carton y est un R.
        drawing = text.split("boite")[0]
        self.assertIn("RRR", drawing)
        self.assertIn("Stade Rennais", drawing)

    def test_every_scenario_says_why_it_is_there(self):
        for name, _scale, note, _card in blueprint.SCENARIOS:
            with self.subTest(plan=name):
                self.assertTrue(note.strip())
                self.assertTrue(blueprint.stored(name).startswith("# " + note))

    def test_a_plan_is_stable_from_one_run_to_the_next(self):
        """Sans quoi la commande de regeneration ferait du bruit a chaque fois."""
        for name, _scale, _note, _card in blueprint.SCENARIOS:
            with self.subTest(plan=name):
                self.assertEqual(blueprint.render(name), blueprint.render(name))


class TestTwoPixelsAreEnough(unittest.TestCase):
    """La promesse du chantier : deux pixels cassent un test.

    Sans ces tests-la, rien ne prouverait que les references servent a quelque
    chose - une reference qu'aucun decalage ne fait bouger est un fichier mort.
    """

    def shifted(self, name, **constants):
        """Le plan de `name` avec quelques constantes de `overlay` deplacees."""
        before = {key: getattr(overlay, key) for key in constants}
        try:
            for key, value in constants.items():
                setattr(overlay, key, value)
            return blueprint.render(name)
        finally:
            for key, value in before.items():
                setattr(overlay, key, value)

    def test_two_pixels_of_margin_break_the_plan(self):
        moved = self.shifted("but-football", PAD_X=overlay.PAD_X + 2)
        self.assertNotEqual(moved, blueprint.stored("but-football"))

    def test_two_pixels_between_a_name_and_the_score_break_the_plan(self):
        moved = self.shifted("cartons-rouges", GAP=overlay.GAP + 2)
        self.assertNotEqual(moved, blueprint.stored("cartons-rouges"))

    def test_two_pixels_of_height_break_the_plan(self):
        moved = self.shifted("fin-de-match", PAD_Y=overlay.PAD_Y + 2)
        self.assertNotEqual(moved, blueprint.stored("fin-de-match"))

    def test_two_pixels_between_a_crest_and_its_name_break_the_plan(self):
        moved = self.shifted("but-football", LOGO_GAP=overlay.LOGO_GAP + 2)
        self.assertNotEqual(moved, blueprint.stored("but-football"))

    def test_the_shift_reads_in_the_diff(self):
        """Et il se lit : deux pixels de plus, ce sont deux nombres de plus."""
        moved = self.shifted("but-football", PAD_X=overlay.PAD_X + 2).splitlines()
        before = blueprint.stored("but-football").splitlines()
        rows = [(old, new) for old, new in zip(before, moved) if old != new]
        titles = [(old, new) for old, new in rows if '"BUT !"' in old]
        self.assertEqual(len(titles), 1)
        old, new = titles[0]
        self.assertIn("29", old.split('"')[0])
        self.assertIn("31", new.split('"')[0])

    def test_the_constants_are_put_back(self):
        """Le garde-fou du garde-fou : ces tests ne doivent rien laisser."""
        self.assertEqual((overlay.PAD_X, overlay.PAD_Y, overlay.GAP,
                          overlay.LOGO_GAP), (22, 16, 26, 10))


class TestPlansDoNotDependOnTheMachine(unittest.TestCase):
    """Le point dur : le meme plan sur Ubuntu, Windows, macOS et cinq Python."""

    def test_no_system_font_is_ever_measured(self):
        """Les polices du plan sont fausses, donc identiques partout."""
        sheet = blueprint.fonts()
        self.assertEqual(sorted(sheet), sorted(blueprint.METRICS))
        for name, font in sheet.items():
            self.assertEqual(font.measure("abcd"), 4 * font.width)
            self.assertEqual(font.metrics("linespace"), font.line)

    def test_the_scale_shrinks_and_grows_the_whole_sheet(self):
        small, large = blueprint.fonts(0.5), blueprint.fonts(2.0)
        for name in blueprint.METRICS:
            self.assertLess(small[name].width, large[name].width)
            self.assertLess(small[name].line, large[name].line)

    def test_a_font_never_shrinks_to_nothing(self):
        """Un plancher, comme dans overlay._fonts : sinon plus rien ne se mesure."""
        for font in blueprint.fonts(0.01).values():
            self.assertGreaterEqual(font.width, 3)
            self.assertGreaterEqual(font.line, 6)

    def test_no_coordinate_is_written_as_a_raw_float(self):
        """Un dixieme de pixel au plus : le reste serait du bruit de machine."""
        for name, _scale, _note, _card in blueprint.SCENARIOS:
            table = blueprint.stored(name).split("contenu\n", 1)[1]
            for line in table.splitlines()[1:]:
                # Un nom de boite peut porter une espace ("score dom.") : ce
                # sont les colonnes qui decoupent le tableau, pas les blancs.
                for word in line[14:42].split():
                    if "." in word:
                        with self.subTest(plan=name, value=word):
                            self.assertTrue(word.replace(".", "", 1).isdigit())
                            self.assertEqual(len(word.split(".")[1]), 1)

    def test_the_references_carry_no_windows_line_ending(self):
        """La CI relit sous Linux ce qu'on regenere parfois sous Windows."""
        for name, _scale, _note, _card in blueprint.SCENARIOS:
            with self.subTest(plan=name):
                with open(blueprint.path(name), "rb") as handle:
                    self.assertNotIn(b"\r", handle.read())


class TestPlansCoverTheCards(unittest.TestCase):
    """Une forme de carte non couverte est une forme qui derivera en silence."""

    def names(self):
        return [name for name, _s, _n, _c in blueprint.SCENARIOS]

    def test_every_shape_of_card_has_a_plan(self):
        for expected in ("but-football", "carte-epinglee", "fin-de-match",
                         "rugby-essai", "cartons-rouges", "noms-tronques"):
            self.assertIn(expected, self.names())

    def test_at_least_two_scales_are_frozen(self):
        scales = set(scale for _n, scale, _no, _c in blueprint.SCENARIOS)
        self.assertGreaterEqual(len(scales), 3)
        self.assertLess(min(scales), 1.0)
        self.assertGreater(max(scales), 1.0)

    def test_the_pinned_card_has_no_third_line(self):
        table = blueprint.stored("carte-epinglee").split("contenu\n", 1)[1]
        self.assertNotIn("detail", table)
        self.assertIn("detail", blueprint.stored("but-football")
                      .split("contenu\n", 1)[1])

    def test_the_fulltime_card_lists_the_scorers(self):
        text = blueprint.stored("fin-de-match")
        self.assertIn("ligne 1", text)
        self.assertIn("ligne 2", text)

    def test_the_stake_costs_the_prematch_card_no_height(self):
        """Tout l'arbitrage du chantier, en un test.

        L'avant-match est deja la carte la plus haute du programme : l'enjeu y
        entre par le coin que la minute laisse vide, pas par une ligne de plus.
        Quatre cartes empilees valent un mur de 612 pixels dans les deux cas.
        """
        def height(name):
            head = blueprint.stored(name).split("\n")[2]
            return head.split(" x ")[1].split(" px")[0]

        self.assertEqual(height("avant-match-aller"), height("avant-match"))

        # Et le compte a rebours reste la troisieme ligne : la carte porte son
        # "detail" au-dessus de ses deux lignes de forme, l'enjeu au-dessus de
        # tout, dans l'en-tete.
        table = blueprint.stored("avant-match-aller").split("contenu\n", 1)[1]
        rows = [line.split()[0] for line in table.strip().split("\n")]
        self.assertLess(rows.index("minute"), rows.index("detail"))
        self.assertLess(rows.index("detail"), rows.index("ligne"))

    def test_the_long_names_are_shortened(self):
        self.assertIn("...", blueprint.stored("noms-tronques"))

    def test_the_scale_really_changes_the_card(self):
        small = blueprint.stored("echelle-075")
        large = blueprint.stored("echelle-160")
        self.assertNotEqual(small, large)
        self.assertIn("echelle 0.75", small)
        self.assertIn("echelle 1.60", large)


if __name__ == "__main__":
    unittest.main()
