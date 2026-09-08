"""Les cartes ecrites dans le terminal : ce qu'elles montrent, et ce qu'elles
ne coupent pas.

Deux familles de tests, et la seconde compte autant que la premiere :

  - la carte elle-meme, figee ici en toutes lettres. Une carte de terminal EST
    du texte : sa reference n'a pas besoin d'un fichier a cote, l'assertion la
    porte, et un decalage se lit dans le diff de la PR comme un plan de
    `tests/plans/` ;
  - le fait que ce mode ne remplace QUE la fenetre. Le journal, le son, le
    crochet et la voix sont d'un autre etage, et un mode d'affichage qui les
    emporterait serait une regression silencieuse.

Le garde-fou contre la derive entre les deux dessinateurs de cartes est
`TestTheTerminalFollowsTheFrozenCards` : il rend en terminal les memes cartes
figees que les plans de `blueprint.SCENARIOS`. Une forme de carte ajoutee la-bas
arrive donc ici toute seule.
"""

import io
import threading
import unittest
from unittest import mock

import blueprint

from butbutbut import cli, config, espn, i18n, leagues, overlay, pinned
from butbutbut import state, terminal, watcher

from helpers import event, goal_detail, isolate_data_dir, payload

LIGUE1 = leagues.BY_SLUG["fra.1"]


def goal_card(**kwargs):
    """La carte de but des plans, avec ce qu'on veut y changer."""
    base = dict(title="BUT !", league="LIGUE 1", minute="35'",
                home="Angers", away="Stade Rennais",
                home_score=1, away_score=2, side="home",
                detail=[("But de ", False), ("C. Arcus", True)],
                accent="#f2e34c")
    base.update(kwargs)
    return overlay.Card(**base)


class FakeStream:
    """Une sortie qui note ce qu'on lui ecrit, et sait mentir sur son tty."""

    def __init__(self, tty=False, broken=False):
        self.chunks = []
        self.tty = tty
        self.broken = broken
        self.flushed = 0

    def isatty(self):
        if self.broken:
            raise ValueError("flux ferme")
        return self.tty

    def write(self, text):
        if self.broken:
            raise ValueError("flux ferme")
        self.chunks.append(text)
        return len(text)

    def flush(self):
        self.flushed += 1

    def text(self):
        return "".join(self.chunks)


class OneGoal:
    """Un watcher qui rend un evenement au premier passage, puis plus rien."""

    def __init__(self, matches, events, stopping):
        self.matches = matches
        self.events = events
        self.stopping = stopping
        self.passes = 0

    def tick(self):
        self.passes += 1
        if self.passes > 1:
            self.stopping.set()
            return []
        return self.events

    def all_matches(self):
        return self.matches

    def next_delay(self):
        return 0.0

    def plan_wait(self):
        return self.next_delay()


# ------------------------------------------------------------- la carte ------

class TestTheCardsOfTheProgram(unittest.TestCase):
    """Les formes de carte que le daemon pousse vraiment, figees en clair."""

    maxDiff = None

    def setUp(self):
        # La langue par defaut depend de la machine : les cartes de ces tests
        # portent des libelles francais, elles doivent le rester partout.
        self.addCleanup(i18n.use, i18n.language())
        i18n.use("fr")

    def test_a_goal(self):
        self.assertEqual(terminal.draw(goal_card()).splitlines(), [
            "+----------------------------------------------------------------------------+",
            "| BUT !  LIGUE 1                                                         35' |",
            "|                           Angers  1 - 2  Stade Rennais                     |",
            "| But de C. Arcus                                                            |",
            "+----------------------------------------------------------------------------+",
        ])

    def test_a_quiet_card_keeps_the_same_shape(self):
        """Un temps fort : meme carte, sans troisieme ligne ni couleur d'equipe.

        Sur l'ecran c'est le titre gris qui le dit. Le terminal n'a pas de gris,
        et c'est justement pour ca qu'il faut verifier que la carte reste
        lisible : il ne lui reste que le titre et le score.
        """
        card = overlay.Card(title="MI-TEMPS", league="LIGUE 1", minute="45'+2'",
                            home="Angers", away="Stade Rennais",
                            home_score=1, away_score=2, side=None, detail=[],
                            accent="#f2e34c", title_color=overlay.MUTED)
        self.assertEqual(terminal.draw(card).splitlines(), [
            "+----------------------------------------------------------------------------+",
            "| MI-TEMPS  LIGUE 1                                                   45'+2' |",
            "|                           Angers  1 - 2  Stade Rennais                     |",
            "+----------------------------------------------------------------------------+",
        ])

    def test_the_end_of_the_match_lists_the_scorers(self):
        card = overlay.Card(title="FIN DU MATCH", league="LIGUE 1",
                            minute="90'+4'", home="Angers", away="Stade Rennais",
                            home_score=1, away_score=2, side=None, detail=[],
                            accent="#f2e34c", title_color=overlay.MUTED,
                            extra=[[("Angers : ", False), ("M. Lopez 12'", True)],
                                   [("Stade Rennais : ", False),
                                    ("A. Kalimuendo 58', L. Blas 77'", True)]])
        self.assertEqual(terminal.draw(card).splitlines(), [
            "+----------------------------------------------------------------------------+",
            "| FIN DU MATCH  LIGUE 1                                               90'+4' |",
            "|                           Angers  1 - 2  Stade Rennais                     |",
            "| Angers : M. Lopez 12'                                                      |",
            "| Stade Rennais : A. Kalimuendo 58', L. Blas 77'                             |",
            "+----------------------------------------------------------------------------+",
        ])

    def test_a_red_card_is_drawn_and_never_written(self):
        """Deux expulsions d'un cote, une de l'autre : la meme reserve des deux.

        C'est la regle de `overlay._layout`, et elle vaut ici pour la meme
        raison : une reserve par camp deplacerait le score a chaque carton.
        """
        drawn = terminal.draw(goal_card(home_reds=2, away_reds=1)).splitlines()
        self.assertEqual(
            drawn[2],
            "|                      Angers [][]  1 - 2  []   Stade Rennais                |")

    def test_the_score_stays_in_the_middle(self):
        """Le score au centre, avec ou sans carton : c'est ce qu'on cherche."""
        for card in (goal_card(), goal_card(home_reds=3),
                     goal_card(home="Sochaux", away="Borussia Dortmund")):
            line = terminal.draw(card).splitlines()[2]
            middle = line.index(" 1 - 2 ") + len(" 1 - 2 ") / 2.0
            self.assertLess(abs(middle - len(line) / 2.0), 2.0, line)


class TestWhatDoesNotFit(unittest.TestCase):
    """Un nom trop long, un terminal trop etroit : la carte reste dans ses bords."""

    def test_a_name_too_long_is_shortened(self):
        drawn = terminal.draw(goal_card(home="Borussia Monchengladbach",
                                        away="Eintracht Frankfurt"), 46)
        self.assertIn("...", drawn)
        self.assertNotIn("Monchengladbach", drawn)

    def test_a_narrow_terminal_keeps_the_frame_square(self):
        for width in (30, 34, 52, 78):
            lines = terminal.render(goal_card(home_reds=2, away_reds=1), width)
            self.assertEqual(sorted(set(len(line) for line in lines)), [width],
                             "largeur {}".format(width))

    def test_a_terminal_narrower_than_the_floor_keeps_the_floor(self):
        """Une carte de 12 colonnes ne dirait plus rien : on garde le plancher.

        Meme choix que la largeur de confort de la carte de l'ecran
        (`overlay.MIN_WIDTH`) : mieux vaut une carte qui deborde d'un terminal
        minuscule qu'une carte ou le score a mange les deux equipes.
        """
        lines = terminal.render(goal_card(), 12)
        self.assertEqual(len(lines[0]), terminal.MIN_WIDTH)

    def test_a_long_list_of_scorers_is_cut_not_wrapped(self):
        card = goal_card(extra=[[("Angers : ", False),
                                 ("M. Lopez 12', J. Bamba 40', H. Belkebla 62'",
                                  True)]])
        lines = terminal.render(card, 40)
        self.assertEqual(sorted(set(len(line) for line in lines)), [40])
        self.assertIn("...", lines[-2])

    def test_every_card_is_pure_ascii(self):
        for _name, _scale, _note, card in blueprint.SCENARIOS:
            drawn = terminal.draw(card)
            self.assertEqual(drawn.encode("ascii").decode("ascii"), drawn)


class TestTheTerminalFollowsTheFrozenCards(unittest.TestCase):
    """Le garde-fou anti-derive : les cartes des plans, rendues en terminal.

    `blueprint.SCENARIOS` porte une carte par forme du programme - le but, la
    carte epinglee, l'avant-match, le coup d'envoi, la fin de match, le rugby,
    les cartons, les noms tronques. Les reprendre ici veut dire qu'une forme
    ajoutee aux plans est aussitot verifiee dans le terminal, au lieu d'y
    deriver sans que personne ne le voie.
    """

    def test_every_frozen_card_says_what_it_carries(self):
        for name, _scale, _note, card in blueprint.SCENARIOS:
            with self.subTest(carte=name):
                drawn = terminal.draw(card, 100)
                self.assertIn(card.title, drawn)
                self.assertIn(card.league, drawn)
                self.assertIn(card.home, drawn)
                self.assertIn(card.away, drawn)
                self.assertIn("{} - {}".format(card.home_score,
                                               card.away_score), drawn)
                if card.minute:
                    self.assertIn(card.minute, drawn)
                if card.detail:
                    self.assertIn(card.detail, drawn)

    def test_the_scale_of_the_window_means_nothing_here(self):
        """--scale agrandit des pixels, pas des caracteres : meme carte."""
        cards = {name: card for name, _s, _n, card in blueprint.SCENARIOS}
        self.assertEqual(terminal.draw(cards["echelle-075"]),
                         terminal.draw(cards["but-football"]))

    def test_a_card_never_raises_whatever_it_carries(self):
        for name, _scale, _note, card in blueprint.SCENARIOS:
            for width in (terminal.MIN_WIDTH, 40, terminal.MAX_WIDTH, 200):
                with self.subTest(carte=name, largeur=width):
                    self.assertTrue(terminal.draw(card, width))


# ------------------------------------------------------------- la sortie -----

class TestWhereTheCardGoes(unittest.TestCase):
    """La largeur, le tty, et le tuyau."""

    def test_a_stream_that_is_not_a_terminal_gets_a_fixed_width(self):
        """Un fichier ou un `grep` n'a pas de largeur : la carte n'en invente pas.

        Une largeur fixe rend en prime le meme fichier d'une machine a l'autre.
        """
        self.assertEqual(terminal.columns(FakeStream(tty=False)),
                         terminal.MAX_WIDTH)

    def test_a_terminal_gives_its_width_minus_a_margin(self):
        with mock.patch.object(terminal.shutil, "get_terminal_size",
                               return_value=mock.Mock(columns=60)):
            self.assertEqual(terminal.columns(FakeStream(tty=True)), 58)

    def test_a_very_wide_terminal_stops_at_the_ceiling(self):
        with mock.patch.object(terminal.shutil, "get_terminal_size",
                               return_value=mock.Mock(columns=400)):
            self.assertEqual(terminal.columns(FakeStream(tty=True)),
                             terminal.MAX_WIDTH)

    def test_a_stream_that_cannot_say_gets_the_fixed_width(self):
        self.assertEqual(terminal.columns(FakeStream(broken=True)),
                         terminal.MAX_WIDTH)

    def test_the_size_of_the_terminal_is_read_again_at_every_card(self):
        """Une fenetre redimensionnee en cours de soiree doit etre suivie."""
        writer = terminal.Writer(FakeStream(tty=True))
        sizes = [mock.Mock(columns=42), mock.Mock(columns=62)]
        with mock.patch.object(terminal.shutil, "get_terminal_size",
                               side_effect=sizes):
            self.assertEqual(writer.width(), 40)
            self.assertEqual(writer.width(), 60)

    def test_a_broken_pipe_never_raises(self):
        """Le daemon a deja fait son travail ailleurs : il ne meurt pas d'un tuyau."""
        writer = terminal.Writer(FakeStream(broken=True))
        self.assertFalse(writer.show(goal_card()))

    def test_a_card_that_goes_through_is_flushed(self):
        """Sans vidage, une carte resterait dans le tampon jusqu'au but suivant."""
        stream = FakeStream(tty=True)
        writer = terminal.Writer(stream, width=50)
        self.assertTrue(writer.show(goal_card()))
        self.assertEqual(stream.flushed, 1)
        self.assertTrue(stream.text().endswith("\n"))


# -------------------------------------------------------- le declenchement ---

class TestHowTheModeStarts(unittest.TestCase):
    """Sur demande, ou faute de fenetre. Jamais a la place d'une fenetre qui marche."""

    def setUp(self):
        self.paths = isolate_data_dir(self)
        self.paths["data"].mkdir(parents=True, exist_ok=True)

    def args(self, *extra):
        return cli.build_parser().parse_args(list(extra))

    def test_the_option_exists_and_is_off_by_default(self):
        self.assertFalse(self.args().terminal)
        self.assertTrue(self.args("--terminal").terminal)

    def test_the_option_lasts_in_the_configuration_file(self):
        """Une option durable sans cle de fichier ment a --write-config."""
        self.assertIn("terminal", {o.name for o in config.OPTIONS})

    def test_asking_for_it_opens_a_writer(self):
        with mock.patch.object(cli, "log"):
            self.assertIsNotNone(cli.terminal_cards(self.args("--terminal"),
                                                    "--terminal"))

    def test_quiet_wins_and_says_so(self):
        """--quiet dit "n'ecrire que dans le journal" : une carte est de l'ecriture."""
        with mock.patch.object(cli, "log") as journal:
            self.assertIsNone(cli.terminal_cards(self.args("--quiet"), "--terminal"))
        self.assertIn("quiet", " ".join(str(c) for c in journal.call_args_list))

    def test_a_missing_display_is_not_fatal_anymore(self):
        """tkinter present, mais aucun ecran ou s'ouvrir : le daemon survit.

        Sans cette conversion, la TclError de `Tk()` remontait brute jusqu'a
        main() et emportait le daemon d'une machine sans DISPLAY.
        """
        stack = overlay.Stack()
        fake = mock.Mock()
        fake.Tk.side_effect = RuntimeError("no display name and no $DISPLAY")
        with mock.patch.object(overlay, "_import_tk",
                               return_value=(fake, mock.Mock())):
            with self.assertRaises(overlay.DisplayUnavailable):
                stack.open()

    def test_the_missing_package_is_still_its_own_case(self):
        """Les deux pannes se soignent differemment : le message doit differer."""
        self.assertTrue(issubclass(overlay.TkinterMissing,
                                   overlay.DisplayUnavailable))
        self.assertTrue(issubclass(overlay.NoDisplay,
                                   overlay.DisplayUnavailable))

    def test_no_overlay_wins_over_terminal(self):
        """Celle qui coupe l'emporte : on ne montre pas ce qu'on a dit de cacher."""
        stopping = threading.Event()
        with mock.patch.object(cli, "_watch_headless") as loop:
            with mock.patch.object(cli, "log"):
                with mock.patch.object(cli, "terminal_cards") as maker:
                    self.daemon_up_to_the_loop(["--no-overlay", "--terminal"],
                                               stopping, loop)
        maker.assert_not_called()
        self.assertIsNone(loop.call_args.kwargs.get("printer"))

    def test_the_daemon_falls_back_when_no_window_can_open(self):
        stopping = threading.Event()
        with mock.patch.object(cli, "_watch_headless") as loop:
            with mock.patch.object(cli, "log"):
                with mock.patch.object(overlay.Stack, "open",
                                       side_effect=overlay.NoDisplay("rien")):
                    self.daemon_up_to_the_loop([], stopping, loop)
        self.assertIsInstance(loop.call_args.kwargs.get("printer"),
                              terminal.Writer)

    def daemon_up_to_the_loop(self, extra, stopping, loop):
        """Lance do_daemon jusqu'a la boucle, qui est doublee. Rend les args."""
        args = self.args("--leagues", "l1", *extra)
        empty = mock.Mock(**{"tick.return_value": [], "all_matches.return_value": [],
                             "plan_wait.return_value": 0.0,
                             "prime.return_value": None})
        with mock.patch.object(cli.watcher, "Watcher", return_value=empty):
            with mock.patch.object(cli, "check_teams", return_value=0):
                with mock.patch.object(cli, "claim_pid_file", return_value=True):
                    cli.do_daemon(args)
        return args


# ----------------------------------------------- ce que le mode ne coupe pas -

class TestTheModeReplacesOnlyTheWindow(unittest.TestCase):
    """Le son, le journal et le crochet sont d'un autre etage."""

    def setUp(self):
        self.paths = isolate_data_dir(self)
        self.paths["data"].mkdir(parents=True, exist_ok=True)
        # Les cartes de ces tests portent des libelles francais : la langue par
        # defaut, elle, est celle de la machine.
        self.addCleanup(i18n.use, i18n.language())
        i18n.use("fr")
        self.args = cli.build_parser().parse_args(["--terminal"])
        self.stream = FakeStream(tty=False)
        self.printer = terminal.Writer(self.stream, width=60)

    def reporter(self):
        return state.Reporter(self.paths["state"], leagues=[LIGUE1],
                              interval=25, idle_interval=300)

    def guard(self, stopping, kind=watcher.GOAL, home_score=1):
        matches = espn.parse(
            payload(event(state="in", home_score=home_score,
                          details=[goal_detail("1")])), LIGUE1)
        one = watcher.Event(kind=kind, match=matches[0], side="home",
                            team=matches[0].home, opponent=matches[0].away,
                            home_score=home_score, away_score=0, delta=1,
                            play=None)
        return OneGoal(matches, [one], stopping)

    def play(self, kind=watcher.GOAL, args=None, printer=True):
        stopping = threading.Event()
        guard = self.guard(stopping, kind)
        with mock.patch.object(cli, "play_goal_sound") as horn:
            with mock.patch.object(cli, "log") as journal:
                cli._watch_headless(guard, args or self.args, stopping,
                                    self.reporter(), pinned.Pin(""),
                                    printer=self.printer if printer else None)
        return horn, journal

    def test_a_goal_writes_its_card(self):
        self.play()
        self.assertIn("BUT", self.stream.text())
        self.assertIn("Angers", self.stream.text())

    def test_the_horn_still_sounds(self):
        horn, _journal = self.play()
        self.assertTrue(horn.called)

    def test_the_journal_still_gets_its_line(self):
        _horn, journal = self.play()
        self.assertIn("BUT", " ".join(str(c) for c in journal.call_args_list))

    def test_the_journal_stays_the_same_with_or_without_the_mode(self):
        """Le mode change l'affichage, pas la trace : les deux journaux collent."""
        _horn, with_cards = self.play()
        _horn2, without = self.play(printer=False)
        self.assertEqual([c.args for c in with_cards.call_args_list],
                         [c.args for c in without.call_args_list])

    def test_a_phase_gets_its_card_but_no_sound(self):
        horn, _journal = self.play(kind=watcher.FULLTIME)
        self.assertIn("FIN DU MATCH", self.stream.text())
        horn.assert_not_called()

    def test_no_phase_cards_still_silences_the_phases(self):
        args = cli.build_parser().parse_args(["--terminal", "--no-phase-cards"])
        self.play(kind=watcher.FULLTIME, args=args)
        self.assertEqual(self.stream.text(), "")

    def test_a_red_card_still_gets_its_card(self):
        """--no-phase-cards ne la couperait pas : elle a son propre interrupteur."""
        args = cli.build_parser().parse_args(["--terminal", "--no-phase-cards"])
        self.play(kind=watcher.RED_CARD, args=args)
        self.assertIn("CARTON ROUGE", self.stream.text())

    def test_a_match_watched_late_writes_nothing(self):
        """--spoiler-free coupe toutes les alertes, celle-ci comprise."""
        stopping = threading.Event()
        guard = self.guard(stopping)
        guard.events[0].spoiler_free = True
        with mock.patch.object(cli, "play_goal_sound"):
            with mock.patch.object(cli, "log"):
                cli._watch_headless(guard, self.args, stopping, self.reporter(),
                                    pinned.Pin(""), printer=self.printer)
        self.assertEqual(self.stream.text(), "")

    def test_a_card_that_fails_never_stops_the_loop(self):
        """Un terminal ferme sous les pieds d'un service ne doit rien emporter."""
        stopping = threading.Event()
        guard = self.guard(stopping)
        broken = terminal.Writer(FakeStream(broken=True))
        with mock.patch.object(cli, "play_goal_sound") as horn:
            with mock.patch.object(cli, "log"):
                cli._watch_headless(guard, self.args, stopping, self.reporter(),
                                    pinned.Pin(""), printer=broken)
        self.assertTrue(horn.called)


class TestTheDemonstration(unittest.TestCase):
    """`--test --terminal` doit montrer ce que le daemon montrera."""

    def setUp(self):
        self.paths = isolate_data_dir(self)
        self.paths["data"].mkdir(parents=True, exist_ok=True)
        self.addCleanup(i18n.use, i18n.language())
        i18n.use("fr")

    def run_test_command(self, *extra):
        args = cli.build_parser().parse_args(["--test", "--leagues", "l1",
                                              *extra])
        written = io.StringIO()
        with mock.patch.object(cli.sys, "stderr", written):
            with mock.patch.object(cli, "play_goal_sound"):
                with mock.patch.object(cli.time, "sleep"):
                    with mock.patch.object(cli.sys.stdout, "write"):
                        code = cli.do_test(args)
        return code, written.getvalue()

    def test_the_demo_writes_a_card(self):
        code, written = self.run_test_command("--terminal", "--no-sound")
        self.assertEqual(code, 0)
        self.assertIn("+---", written)
        self.assertIn(" - ", written)

    def test_the_demo_says_what_the_pinned_card_cannot_do(self):
        _code, written = self.run_test_command("--terminal", "--no-sound",
                                               "--pin", "om")
        self.assertIn("epinglee", written)


if __name__ == "__main__":
    unittest.main()
