"""--table : le classement, de la charge utile ESPN a la ligne affichee.

Aucun reseau nulle part. Les charges utiles sont figees dans le fichier, dans
la forme relevee sur la vraie source - un championnat, une NHL a deux
conferences, un tournoi de rugby, une coupe hors saison.
"""

import io
import os
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

from butbutbut import cli, espn, i18n, leagues, sports

from helpers import standing_entry, standings_payload

LIGUE1 = leagues.BY_SLUG["fra.1"]
NHL = leagues.BY_SLUG["nhl"]
SIX_NATIONS = leagues.BY_SLUG["180659"]
WSL = leagues.BY_SLUG["eng.w.1"]

_LANGUE = {}


def setUpModule():
    # Ces tests affirment des formulations francaises. Sans cet epinglage ils
    # passeraient sur une machine francaise et echoueraient sur la CI, dont les
    # machines sont anglaises.
    _LANGUE["avant"] = os.environ.get(i18n.ENV)
    os.environ[i18n.ENV] = "fr"
    i18n.use("fr")


def tearDownModule():
    if _LANGUE["avant"] is None:
        os.environ.pop(i18n.ENV, None)
    else:
        os.environ[i18n.ENV] = _LANGUE["avant"]


def soccer_row(name, rank, played=3, wins=1, ties=1, losses=1, diff="+2",
               points=4, note=""):
    return standing_entry(name, team_id=name[:3].upper(), note=note,
                          rank=rank, gamesplayed=played, wins=wins, ties=ties,
                          losses=losses, pointdifferential=diff, points=points)


def hockey_row(name, seed, played=82, wins=50, losses=25, otl=7, diff="+40",
               points=107):
    """Une ligne de NHL : pas de `rank`, pas de match nul, un `playoffSeed`."""
    return standing_entry(name, team_id=name[:3].upper(), playoffseed=seed,
                          gamesplayed=played, wins=wins, losses=losses,
                          otlosses=otl, pointdifferential=diff, points=points)


def rugby_row(name, rank, played=5, won=4, drawn=0, lost=1, bonus=5,
              diff="+81", points=21):
    return standing_entry(name, team_id=name[:3].upper(), rank=rank,
                          gamesplayed=played, gameswon=won, gamesdrawn=drawn,
                          gameslost=lost, bonuspoints=bonus,
                          pointsdifference=diff, points=points)


LIGUE1_PAYLOAD = standings_payload(
    ("French Ligue 1 2026-27", [
        soccer_row("AS Monaco", 1, wins=3, ties=0, losses=0, diff="+4",
                   points=9, note="Champions League"),
        soccer_row("Marseille", 10, wins=1, ties=0, losses=2, diff="+1",
                   points=3),
        soccer_row("AJ Auxerre", 18, wins=0, ties=0, losses=3, diff="-7",
                   points=0, note="Relegation"),
    ]))

NHL_PAYLOAD = standings_payload(
    ("Eastern Conference", [hockey_row("Carolina Hurricanes", 1)]),
    ("Western Conference", [
        # Dans le desordre, comme la vraie source : la 1re tete de serie
        # arrive derniere.
        hockey_row("Dallas Stars", 2, points=112),
        hockey_row("Colorado Avalanche", 1, points=121),
    ]),
    name="National Hockey League", season="2025-26")

SIX_NATIONS_PAYLOAD = standings_payload(
    ("Six Nations", [rugby_row("France", 1), rugby_row("Wales", 6, won=1,
                                                       lost=4, bonus=2,
                                                       diff="-82", points=6)]),
    name="Six Nations", season="2026")

# Le football feminin : meme endpoint, memes cles, memes colonnes. C'est ce
# qu'il fallait verifier plutot que supposer, --table ayant une notion de
# classement par sport - et le sport, ici, est bien le football.
WSL_PAYLOAD = standings_payload(
    ("2026-27 English Women's Super League", [
        soccer_row("Chelsea", 1, wins=3, ties=0, losses=0, diff="+8",
                   points=9, note="Champions League"),
        soccer_row("Arsenal", 2, wins=2, ties=1, losses=0, diff="+5",
                   points=7),
    ]),
    name="English Women's Super League",
    season="2026-27 English Women's Super League")


def run_table(argv, answers, pause=0.0):
    """Lance --table sur des reponses fabriquees, et rend (code, sortie).

    `answers` : slug -> charge utile ESPN, ou une exception a lever pour ce
    slug-la. La pause entre deux competitions est neutralisee par defaut :
    c'est la cadence qui est testee ailleurs, pas ici.
    """
    def standings(league, **_kwargs):
        answer = answers[league.slug]
        if isinstance(answer, Exception):
            raise answer
        return espn.parse_standings(answer, league)

    buffer = io.StringIO()
    with mock.patch.object(cli, "TABLE_PAUSE", pause):
        with mock.patch.object(espn, "standings", side_effect=standings):
            with redirect_stderr(buffer):
                with redirect_stdout(buffer):
                    code = cli.main(argv)
    return code, buffer.getvalue()


class TestStandingsParsing(unittest.TestCase):
    """Ce que espn.parse_standings tire d'une charge utile complete."""

    def test_a_championship_has_one_group(self):
        table = espn.parse_standings(LIGUE1_PAYLOAD, LIGUE1)
        self.assertEqual(len(table.groups), 1)
        self.assertEqual([row.team for row in table.groups[0].rows],
                         ["AS Monaco", "Marseille", "AJ Auxerre"])
        self.assertFalse(table.empty)

    def test_the_season_is_reduced_to_its_years(self):
        # La source ecrit "2026-27 French Ligue 1" : le nom de la competition
        # vient d'etre affiche, et en anglais par-dessus le marche.
        table = espn.parse_standings(LIGUE1_PAYLOAD, LIGUE1)
        self.assertEqual(table.season, "2026-27")

    def test_the_displayed_writing_is_kept_not_the_number(self):
        # "+4" et non "4.0" : c'est l'ecriture qui porte le signe.
        row = espn.parse_standings(LIGUE1_PAYLOAD, LIGUE1).groups[0].rows[0]
        self.assertEqual(row.cell(("pointdifferential",)), "+4")
        self.assertEqual(row.rank, 1)

    def test_every_writing_of_a_team_is_kept(self):
        # C'est ce que le surlignage interroge.
        row = espn.parse_standings(LIGUE1_PAYLOAD, LIGUE1).groups[0].rows[1]
        self.assertIn("Marseille", row.names)

    def test_conferences_are_two_groups(self):
        table = espn.parse_standings(NHL_PAYLOAD, NHL)
        self.assertEqual([group.name for group in table.groups],
                         ["Eastern Conference", "Western Conference"])

    def test_the_published_rank_orders_the_rows(self):
        # La conference Ouest arrive dans le desordre chez ESPN : l'ordre de la
        # liste ne veut rien dire, le rang si.
        west = espn.parse_standings(NHL_PAYLOAD, NHL).groups[1]
        self.assertEqual([row.team for row in west.rows],
                         ["Colorado Avalanche", "Dallas Stars"])

    def test_the_hockey_rank_is_its_playoff_seed(self):
        # Le hockey ne publie aucun `rank` : c'est `playoffSeed` qui fait foi.
        west = espn.parse_standings(NHL_PAYLOAD, NHL).groups[1]
        self.assertEqual([row.rank for row in west.rows], [1, 2])

    def test_without_any_rank_the_rows_are_simply_numbered(self):
        nameless = standings_payload(("Poule", [
            standing_entry("Alpha", gamesplayed=1),
            standing_entry("Beta", gamesplayed=1),
        ]))
        rows = espn.parse_standings(nameless, LIGUE1).groups[0].rows
        self.assertEqual([(row.rank, row.team) for row in rows],
                         [(1, "Alpha"), (2, "Beta")])


class TestStandingsDegraded(unittest.TestCase):
    """Les charges utiles amputees. Rien ne doit lever."""

    def test_a_cup_out_of_season_has_no_children_at_all(self):
        table = espn.parse_standings(standings_payload(
            name="Coupe de France", season="2025-26 Coupe de France"), LIGUE1)
        self.assertTrue(table.empty)
        self.assertEqual(table.groups, [])
        # La saison retombe sur l'en-tete quand aucun bloc ne la dit.
        self.assertEqual(table.season, "2025-26")

    def test_a_group_without_entries_is_empty_too(self):
        # Ce que rend un tournoi entre deux editions : le bloc existe, les
        # lignes non.
        table = espn.parse_standings(standings_payload(("Tournoi", [])),
                                     LIGUE1)
        self.assertTrue(table.empty)

    def test_an_answer_without_anything_known_does_not_raise(self):
        table = espn.parse_standings({}, LIGUE1)
        self.assertTrue(table.empty)
        self.assertEqual(table.season, "")

    def test_a_missing_column_shows_a_dash_not_a_zero(self):
        # Un zero ferait croire a un championnat qui n'a jamais commence.
        thin = standings_payload(("Poule", [standing_entry("Alpha", rank=1)]))
        row = espn.parse_standings(thin, LIGUE1).groups[0].rows[0]
        self.assertEqual(row.cell(("points",)), "-")

    def test_a_broken_entry_does_not_take_the_others_with_it(self):
        broken = standings_payload(("Poule", [
            "pas un objet",
            {"stats": []},                       # sans equipe
            standing_entry("Alpha", rank=1),
        ]))
        rows = espn.parse_standings(broken, LIGUE1).groups[0].rows
        self.assertEqual([row.team for row in rows], ["Alpha"])

    def test_an_ad_hoc_competition_takes_the_name_the_source_gives(self):
        league = leagues.find("gre.1")
        self.assertTrue(league.provisional)
        espn.parse_standings(standings_payload(
            ("Poule", [standing_entry("Alpha", rank=1)]),
            name="Greek Super League"), league)
        self.assertEqual(league.name, "Greek Super League")


class TestStandingsRequest(unittest.TestCase):
    """L'adresse interrogee, et le client qui l'interroge."""

    def test_the_url_carries_the_sport_and_the_slug(self):
        seen = []

        def opener(url, _timeout):
            seen.append(url)
            return b"{}"

        espn.standings(LIGUE1, opener=opener)
        espn.standings(NHL, opener=opener)
        self.assertEqual(seen, [
            "https://site.api.espn.com/apis/v2/sports/soccer/fra.1/standings",
            "https://site.api.espn.com/apis/v2/sports/hockey/nhl/standings",
        ])

    def test_a_broken_answer_is_a_source_error(self):
        def opener(_url, _timeout):
            return b"<html>pas du json</html>"

        with self.assertRaises(espn.SourceError):
            espn.standings(LIGUE1, opener=opener)


class TestTableColumns(unittest.TestCase):
    """Les colonnes viennent du sport, et de nulle part ailleurs."""

    def headers(self, sport):
        return [title for title, _keys in sport.table]

    def test_football_counts_draws(self):
        self.assertEqual(self.headers(sports.SOCCER),
                         ["J", "G", "N", "P", "Diff", "Pts"])

    def test_hockey_has_no_draw_but_overtime_losses(self):
        # Un match de hockey se decide toujours : la colonne "N" n'existe pas,
        # et sans "DP" le total de points de la ligne ne se retrouve pas.
        headers = self.headers(sports.HOCKEY)
        self.assertNotIn("N", headers)
        self.assertIn("DP", headers)

    def test_rugby_carries_its_bonus_points(self):
        self.assertIn("Bon", self.headers(sports.RUGBY))
        self.assertNotIn("Bon", self.headers(sports.SOCCER))

    def test_a_womens_competition_counts_like_any_football(self):
        # Les colonnes viennent du sport, et une competition feminine EST du
        # football : rien a declarer, mais ca se verifie plutot que ca ne se
        # suppose - c'est le seul endroit du programme ou le classement
        # change de forme d'un sport a l'autre.
        self.assertIs(WSL.sport, sports.SOCCER)
        self.assertEqual(self.headers(WSL.sport), self.headers(LIGUE1.sport))


class TestTableFormatting(unittest.TestCase):
    """La geometrie du tableau : un terminal de 80 colonnes, ecussons exclus."""

    def rows_of(self, payload, league):
        return espn.parse_standings(payload, league).groups[0].rows

    def test_no_line_goes_past_eighty_columns(self):
        cases = ((sports.SOCCER, self.rows_of(LIGUE1_PAYLOAD, LIGUE1)),
                 (sports.HOCKEY, self.rows_of(NHL_PAYLOAD, NHL)),
                 (sports.RUGBY, self.rows_of(SIX_NATIONS_PAYLOAD,
                                             SIX_NATIONS)))
        for sport, rows in cases:
            self.assertLessEqual(len(cli.table_header(sport)), 80, sport.code)
            for row in rows:
                line = cli.table_row(row, sport, marked=True)
                self.assertLessEqual(len(line), 80, sport.code)

    def test_a_very_long_name_is_cut_rather_than_pushing_the_columns(self):
        long_name = standing_entry("Borussia Verein fuer Leibesuebungen",
                                   rank=1, points=9)
        row = espn.parse_standings(standings_payload(("Poule", [long_name])),
                                   LIGUE1).groups[0].rows[0]
        line = cli.table_row(row, sports.SOCCER)
        self.assertLessEqual(len(line), 80)
        # La colonne des points reste a sa place, celle de l'en-tete.
        self.assertEqual(len(line), len(cli.table_header(sports.SOCCER)))

    def test_the_marked_row_wears_a_chevron(self):
        row = self.rows_of(LIGUE1_PAYLOAD, LIGUE1)[1]
        self.assertTrue(cli.table_row(row, sports.SOCCER, marked=True)
                        .startswith(">"))
        self.assertFalse(cli.table_row(row, sports.SOCCER)
                         .startswith(">"))

    def test_the_columns_line_up_with_their_headers(self):
        header = cli.table_header(sports.SOCCER)
        line = cli.table_row(self.rows_of(LIGUE1_PAYLOAD, LIGUE1)[0],
                             sports.SOCCER)
        self.assertEqual(header.index("Pts") + len("Pts"),
                         len(line.rstrip()))


class TestTableRequest(unittest.TestCase):
    """Ce que --table accepte : une competition, une equipe, les deux."""

    def test_nothing_asks_for_the_watched_competitions(self):
        self.assertEqual(cli._table_request(""), ("", ""))

    def test_a_known_name_is_a_competition(self):
        self.assertEqual(cli._table_request("l1"), ("l1", ""))
        self.assertEqual(cli._table_request("nhl"), ("nhl", ""))
        self.assertEqual(cli._table_request("top14"), ("top14", ""))

    def test_an_unknown_word_is_a_team(self):
        self.assertEqual(cli._table_request("om"), ("", "om"))

    def test_both_can_be_said_at_once(self):
        self.assertEqual(cli._table_request("om,l1"), ("l1", "om"))

    def test_asking_the_question_opens_no_competition(self):
        # names_a_league() repond sans inscrire : une equipe mal orthographiee
        # ne doit pas ouvrir un slug fantome.
        before = dict(leagues._ADHOC)
        cli._table_request("zzz.9")
        self.assertEqual(set(leagues._ADHOC), set(before))


class TestTableCommand(unittest.TestCase):
    """--table de bout en bout, sans reseau."""

    def test_it_prints_the_table_of_the_named_competition(self):
        code, printed = run_table(["--table", "l1"],
                                  {"fra.1": LIGUE1_PAYLOAD})
        self.assertEqual(code, 0)
        self.assertIn("Ligue 1 (2026-27)", printed)
        self.assertIn("AS Monaco", printed)
        self.assertIn("AJ Auxerre", printed)
        self.assertIn("Pts", printed)

    def test_naming_a_team_keeps_only_its_competition(self):
        code, printed = run_table(
            ["--table", "om", "--leagues", "l1,pl"],
            {"fra.1": LIGUE1_PAYLOAD, "eng.1": standings_payload(
                ("Premier League", [soccer_row("Arsenal", 1)]),
                name="English Premier League")})
        self.assertEqual(code, 0)
        self.assertIn("Ligue 1", printed)
        self.assertNotIn("Arsenal", printed)
        # Le classement entier, pas la seule ligne cherchee : un rang tout seul
        # ne veut rien dire.
        self.assertIn("AS Monaco", printed)

    def test_the_named_team_is_the_only_one_marked(self):
        _code, printed = run_table(["--table", "om,l1"],
                                   {"fra.1": LIGUE1_PAYLOAD})
        marked = [line for line in printed.splitlines()
                  if line.startswith(">")]
        self.assertEqual(len(marked), 1)
        self.assertIn("Marseille", marked[0])

    def test_a_competition_and_a_team_combine(self):
        code, printed = run_table(["--table", "l1,om", "--leagues", "pl"],
                                  {"fra.1": LIGUE1_PAYLOAD})
        # La competition nommee l'emporte sur --leagues : c'est celle-la qu'on
        # est venu chercher.
        self.assertEqual(code, 0)
        self.assertIn("Ligue 1", printed)
        self.assertIn("> 10  Marseille", printed)

    def test_each_conference_gets_its_own_block(self):
        code, printed = run_table(["--table", "nhl"], {"nhl": NHL_PAYLOAD})
        self.assertEqual(code, 0)
        self.assertIn("Eastern Conference", printed)
        self.assertIn("Western Conference", printed)
        self.assertIn("DP", printed)          # les colonnes du hockey

    def test_a_single_block_is_not_named(self):
        # La source appelle l'unique bloc d'un championnat "French Ligue 1
        # 2026-27" : le repeter sous "Ligue 1 (2026-27)" n'apprend rien.
        _code, printed = run_table(["--table", "l1"],
                                   {"fra.1": LIGUE1_PAYLOAD})
        self.assertNotIn("French Ligue 1", printed)

    def test_it_prints_the_table_of_a_womens_competition(self):
        code, printed = run_table(["--table", "wsl"], {"eng.w.1": WSL_PAYLOAD})
        self.assertEqual(code, 0)
        self.assertIn("Women's Super League (2026-27)", printed)
        self.assertIn("Chelsea", printed)
        self.assertIn("N", printed)               # les colonnes du football
        self.assertNotIn("Bon", printed)

    def test_the_womens_keyword_asks_for_the_whole_group(self):
        # `--table feminines` doit lire un mot de competition, pas chercher un
        # club de ce nom : c'est _table_request qui tranche, et le mot-cle
        # devait y entrer avec les autres.
        picked, wanted = cli._table_request("feminines")
        self.assertEqual((picked, wanted), ("feminines", ""))

    def test_rugby_shows_its_bonus_points(self):
        code, printed = run_table(["--table", "6nations"],
                                  {"180659": SIX_NATIONS_PAYLOAD})
        self.assertEqual(code, 0)
        self.assertIn("Bon", printed)
        self.assertIn("France", printed)

    def test_an_empty_table_says_what_was_looked_for_and_where(self):
        code, printed = run_table(["--table", "coupe"],
                                  {"fra.coupe_de_france": standings_payload(
                                      name="Coupe de France")})
        self.assertEqual(code, 0)
        self.assertIn("Aucun classement a afficher pour Coupe de France.",
                      printed)
        self.assertIn("soccer/fra.coupe_de_france", printed)
        self.assertIn("hors saison", printed)

    def test_a_team_found_nowhere_is_said_in_words(self):
        code, printed = run_table(["--table", "zzzclub", "--leagues", "l1"],
                                  {"fra.1": LIGUE1_PAYLOAD})
        self.assertEqual(code, 0)
        # Le mot cherche est repete : c'est la qu'une faute de frappe se voit.
        self.assertIn("zzzclub", printed)
        self.assertIn("Aucune ligne pour", printed)

    def test_one_unreachable_competition_does_not_stop_the_others(self):
        code, printed = run_table(
            ["--table", "l1,pl"],
            {"fra.1": LIGUE1_PAYLOAD,
             "eng.1": espn.SourceError("HTTP 500")})
        self.assertEqual(code, 0)
        self.assertIn("AS Monaco", printed)
        self.assertIn("Premier League injoignable : HTTP 500", printed)
        self.assertIn("incomplet", printed)

    def test_everything_unreachable_is_an_error(self):
        code, printed = run_table(["--table", "l1"],
                                  {"fra.1": espn.SourceError("pas de reseau")})
        self.assertEqual(code, 1)
        self.assertIn("Aucune competition n'a repondu", printed)

    def test_an_unknown_competition_is_refused_before_any_request(self):
        # Les competitions de --table n'arrivent pas par --leagues : elles ne
        # passent donc pas par le controle de main(), et se verifient dans
        # do_table. Sans quoi la faute serait avalee en silence.
        code, printed = run_table(["--table", "curling:1"], {})
        self.assertEqual(code, 2)
        self.assertIn("sport inconnu", printed)

    def test_the_requests_are_spaced_out(self):
        # Avec --leagues all ce sont 36 requetes : une rafale se ferait jeter.
        empty = standings_payload()
        with mock.patch.object(cli.time, "sleep") as sleeping:
            with mock.patch.object(
                    espn, "standings",
                    side_effect=lambda lg, **k: espn.parse_standings(empty, lg)):
                with redirect_stdout(io.StringIO()):
                    cli.main(["--table", "--leagues", "l1,pl,liga"])
        self.assertEqual(sleeping.call_count, 2)
        for call in sleeping.call_args_list:
            self.assertEqual(call[0][0], cli.TABLE_PAUSE)


if __name__ == "__main__":
    unittest.main()
