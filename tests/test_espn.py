import gzip
import json
import unittest
import unittest.mock
from datetime import datetime, timezone

from butbutbut import espn, i18n, leagues, sports

from helpers import (event, goal_detail, hockey_noise, hockey_play,
                     hockey_summary, opener_for, payload, red_card_detail)

LIGUE1 = leagues.BY_SLUG["fra.1"]
NHL = leagues.BY_SLUG["nhl"]


def setUpModule():
    # Ces tests affirment des formulations francaises. Sans cet epinglage ils
    # passeraient sur une machine francaise et echoueraient sur la CI, dont les
    # machines sont anglaises.
    i18n.use("fr")

class TestParse(unittest.TestCase):
    def test_reads_teams_scores_and_state(self):
        matches = espn.parse(payload(event(home_score=1, away_score=2)), LIGUE1)
        self.assertEqual(len(matches), 1)
        match = matches[0]
        self.assertEqual(match.home, "Angers")
        self.assertEqual(match.away, "Stade Rennais")
        self.assertEqual((match.home_score, match.away_score), (1, 2))
        self.assertTrue(match.live)
        self.assertFalse(match.finished)
        self.assertEqual(match.score_line(), "Angers 1 - 2 Stade Rennais")
        self.assertIs(match.league, LIGUE1)

    def test_long_names_fall_back_to_short_name(self):
        matches = espn.parse(payload(event(
            home=("Borussia Monchengladbach", "M'gladbach", "BMG"))), LIGUE1)
        self.assertEqual(matches[0].home, "M'gladbach")

    def test_every_writing_of_a_team_is_kept(self):
        # C'est ce que le filtre par equipe interroge.
        matches = espn.parse(payload(event(
            home=("Paris Saint-Germain", "PSG", "PSG"))), LIGUE1)
        self.assertIn("Paris Saint-Germain", matches[0].home_names)
        self.assertIn("PSG", matches[0].home_names)

    def test_missing_score_is_zero_not_a_crash(self):
        raw = payload(event())
        raw["events"][0]["competitions"][0]["competitors"][0].pop("score")
        self.assertEqual(espn.parse(raw, LIGUE1)[0].home_score, 0)

    def test_broken_events_are_skipped_not_fatal(self):
        raw = payload({"id": "x"}, event(match_id="7"), "pas un dict")
        matches = espn.parse(raw, LIGUE1)
        self.assertEqual([m.id for m in matches], ["7"])

    def test_event_without_two_sides_is_skipped(self):
        raw = payload(event())
        raw["events"][0]["competitions"][0]["competitors"].pop()
        self.assertEqual(espn.parse(raw, LIGUE1), [])

    def test_kickoff_is_parsed_as_utc(self):
        matches = espn.parse(payload(event(date="2026-09-06T15:15Z")), LIGUE1)
        self.assertEqual(matches[0].start,
                         datetime(2026, 9, 6, 15, 15, tzinfo=timezone.utc))

    def test_unreadable_kickoff_gives_none(self):
        matches = espn.parse(payload(event(date="bientot")), LIGUE1)
        self.assertIsNone(matches[0].start)
        self.assertIsNone(matches[0].seconds_until_kickoff())

    def test_seconds_until_kickoff(self):
        matches = espn.parse(payload(event(date="2026-09-06T15:15Z")), LIGUE1)
        now = datetime(2026, 9, 6, 15, 0, tzinfo=timezone.utc)
        self.assertAlmostEqual(matches[0].seconds_until_kickoff(now), 900.0)


class TestTeamLook(unittest.TestCase):
    """Ecusson et couleurs : ESPN les publie, on les lit comme le reste."""

    def parse(self, **kwargs):
        return espn.parse(payload(event(**kwargs)), LIGUE1)[0]

    def test_colours_are_normalised_from_the_espn_writing(self):
        match = self.parse(home_colors=("0000BF", "fafafc"),
                           away_colors=("ef2f24", "FFFFFF"))
        self.assertEqual((match.home_color, match.home_alt),
                         ("#0000bf", "#fafafc"))
        self.assertEqual((match.away_color, match.away_alt),
                         ("#ef2f24", "#ffffff"))

    def test_the_logo_url_is_kept_as_is(self):
        url = "https://a.espncdn.com/i/teamlogos/soccer/500/170.png"
        self.assertEqual(self.parse(home_logo=url).home_logo, url)

    def test_a_team_without_colours_or_logo_is_not_a_problem(self):
        match = self.parse()
        self.assertEqual((match.home_color, match.home_alt), ("", ""))
        self.assertEqual((match.home_logo, match.away_logo), ("", ""))

    def test_a_broken_colour_is_dropped_rather_than_passed_on(self):
        match = self.parse(home_colors=("transparent", "0a4"))
        self.assertEqual((match.home_color, match.home_alt), ("", "#00aa44"))

    def test_only_http_logos_are_accepted(self):
        for url in ("ftp://ailleurs/1.png", "javascript:alert(1)",
                    "/i/teamlogos/1.png", "   "):
            self.assertEqual(self.parse(home_logo=url).home_logo, "", url)

    def test_the_logos_list_is_the_fallback(self):
        raw = payload(event())
        team = raw["events"][0]["competitions"][0]["competitors"][0]["team"]
        team["logos"] = [{"href": "https://exemple/ecusson.png"}]
        self.assertEqual(espn.parse(raw, LIGUE1)[0].home_logo,
                         "https://exemple/ecusson.png")

    def test_a_logo_can_be_rebuilt_from_the_team_number(self):
        self.assertEqual(espn.logo_url("170"),
                         "https://a.espncdn.com/i/teamlogos/soccer/500/170.png")


class TestFormAndRecord(unittest.TestCase):
    """La forme et le bilan : deja dans le tableau de bord, longtemps jetes."""

    def parse(self, **kwargs):
        return espn.parse(payload(event(**kwargs)), LIGUE1)[0]

    def test_the_form_is_read_as_the_source_writes_it(self):
        match = self.parse(home_form="LLWWW", away_form="WWDWL")
        self.assertEqual((match.home_form, match.away_form), ("LLWWW", "WWDWL"))

    def test_a_lowercase_form_is_still_a_form(self):
        self.assertEqual(self.parse(home_form="llwww").home_form, "LLWWW")

    def test_an_unknown_letter_drops_the_whole_string(self):
        # Quatre resultats sur cinq, sans le dire, seraient un mensonge par
        # omission : la carte prefere se taire.
        self.assertEqual(self.parse(home_form="LLW?W").home_form, "")

    def test_no_form_at_all_is_not_a_problem(self):
        # Le hockey : la source ne publie ni l'un ni l'autre.
        match = self.parse()
        self.assertEqual((match.home_form, match.home_record), ("", ""))

    def test_the_record_is_read_as_the_source_writes_it(self):
        self.assertEqual(self.parse(home_record="1-0-2").home_record, "1-0-2")

    def test_a_record_that_is_a_form_in_disguise_is_dropped(self):
        # Le rugby republie sa forme sous `records`. La carte l'afficherait
        # deux fois de suite.
        self.assertEqual(self.parse(home_record="LWWWW").home_record, "")

    def test_zero_everywhere_is_not_a_record(self):
        # La phase de groupes d'une coupe d'Europe repond "0-0-0" des juillet.
        self.assertEqual(self.parse(home_record="0-0-0").home_record, "")

    def test_a_two_number_record_is_dropped(self):
        # "2-1" ne dit pas si le second nombre compte les nuls ou les
        # defaites. Un bilan qu'on ne sait pas lire ne s'affiche pas.
        self.assertEqual(self.parse(home_record="2-1").home_record, "")

    def test_the_season_total_wins_over_the_home_and_away_splits(self):
        raw = payload(event())
        competitor = raw["events"][0]["competitions"][0]["competitors"][0]
        competitor["records"] = [
            {"name": "Home", "type": "home", "summary": "1-0-0"},
            {"name": "All Splits", "type": "total", "summary": "1-0-2"},
        ]
        self.assertEqual(espn.parse(raw, LIGUE1)[0].home_record, "1-0-2")


class TestPlays(unittest.TestCase):
    def test_scoring_plays_are_collected_with_scorer(self):
        details = (goal_detail("H1", "35'", "C. Arcus"),
                   {"type": {"text": "Yellow Card"}, "scoringPlay": False})
        match = espn.parse(payload(event(details=details)), LIGUE1)[0]
        self.assertEqual(len(match.plays), 1)
        play = match.plays[0]
        self.assertEqual(play.scorer, "C. Arcus")
        self.assertEqual(play.minute, "35'")
        self.assertEqual(play.summary(), "But de C. Arcus (35')")
        self.assertEqual(play.prefix(), "But")

    def test_own_goal_and_penalty_wording(self):
        details = (goal_detail("H1", "17'", "J. Lefort", own_goal=True, index=1),
                   goal_detail("A1", "58'", "A. Kalimuendo", penalty=True, index=2))
        match = espn.parse(payload(event(details=details)), LIGUE1)[0]
        self.assertEqual(match.plays[0].summary(),
                         "But contre son camp de J. Lefort (17')")
        self.assertEqual(match.plays[1].summary(),
                         "Penalty de A. Kalimuendo (58')")

    def test_plays_are_filtered_by_team(self):
        details = (goal_detail("H1", index=1), goal_detail("A1", index=2))
        match = espn.parse(payload(event(details=details)), LIGUE1)[0]
        self.assertEqual(len(match.plays_for("H1")), 1)
        self.assertEqual(len(match.plays_for("A1")), 1)

    def test_play_without_athlete_still_parses(self):
        detail = goal_detail("H1")
        detail.pop("athletesInvolved")
        match = espn.parse(payload(event(details=(detail,))), LIGUE1)[0]
        self.assertEqual(match.plays[0].scorer, "")
        self.assertEqual(match.plays[0].summary(), "But (35')")

    def test_keys_are_stable_across_two_reads(self):
        raw = payload(event(details=(goal_detail("H1"),)))
        first = espn.parse(raw, LIGUE1)[0]
        second = espn.parse(raw, LIGUE1)[0]
        self.assertEqual([p.key for p in first.plays],
                         [p.key for p in second.plays])


class TestRedCards(unittest.TestCase):
    """Les expulsions vivent dans le meme tableau `details` que les buts."""

    def test_red_cards_are_kept_apart_from_the_goals(self):
        details = (goal_detail("H1", "35'", "C. Arcus", index=1),
                   red_card_detail("A1", "62'", "J. Lefort", index=2),
                   {"type": {"text": "Yellow Card"}, "scoringPlay": False})
        match = espn.parse(payload(event(details=details)), LIGUE1)[0]

        self.assertEqual([p.scorer for p in match.plays], ["C. Arcus"])
        self.assertEqual([p.scorer for p in match.red_cards], ["J. Lefort"])
        card = match.red_cards[0]
        self.assertTrue(card.red_card)
        self.assertEqual(card.minute, "62'")
        self.assertEqual(card.prefix(), "Carton rouge")
        self.assertEqual(card.summary(), "Carton rouge pour J. Lefort (62')")

    def test_a_match_without_expulsion_has_an_empty_list(self):
        match = espn.parse(payload(event(details=(goal_detail("H1"),))), LIGUE1)[0]
        self.assertEqual(match.red_cards, [])

    def test_keys_are_stable_across_two_reads(self):
        raw = payload(event(details=(goal_detail("H1", index=1),
                                     red_card_detail("A1", index=2))))
        first = espn.parse(raw, LIGUE1)[0]
        second = espn.parse(raw, LIGUE1)[0]
        self.assertEqual([p.key for p in first.red_cards],
                         [p.key for p in second.red_cards])
        # Un but et une expulsion de la meme equipe ne partagent pas de cle.
        self.assertNotEqual(first.plays[0].key, first.red_cards[0].key)

    def test_the_tally_counts_each_camp_apart(self):
        """Ce que la carte dessine : un compte par camp, pas un total."""
        match = espn.parse(payload(event(details=(
            red_card_detail("H1", "12'", "M. Sylla", index=1),
            red_card_detail("A1", "62'", "J. Lefort", index=2),
            red_card_detail("A1", "80'", "P. Gueye", index=3),
        ))), LIGUE1)[0]
        self.assertEqual(match.red_card_tally(), (1, 2))

    def test_a_match_without_expulsion_counts_zero_on_both_sides(self):
        match = espn.parse(payload(event(details=(goal_detail("H1"),))), LIGUE1)[0]
        self.assertEqual(match.red_card_tally(), (0, 0))

    def test_an_expulsion_without_a_team_is_counted_nowhere(self):
        """Mieux vaut ne rien dire que de faire jouer a dix la mauvaise equipe."""
        match = espn.parse(payload(event(
            details=(red_card_detail("", "62'", "J. Lefort"),))), LIGUE1)[0]
        self.assertEqual(len(match.red_cards), 1)
        self.assertEqual(match.red_card_tally(), (0, 0))

    def test_a_sport_without_red_cards_never_counts_one(self):
        """Le garde-fou est le drapeau du sport, pas la chance d'un tableau vide.

        Le match est lu au football - donc avec ses expulsions - puis rattache
        a une competition de hockey. Le compte tombe a zero parce que le sport
        n'expulse pas, et non parce que la source s'est tue : c'est ce qui
        protege le jour ou elle publierait pour le hockey un tableau d'actions
        qu'elle n'a jamais publie.
        """
        match = espn.parse(payload(event(
            details=(red_card_detail("H1"),))), LIGUE1)[0]
        self.assertEqual(match.red_card_tally(), (1, 0))
        match.league = NHL
        self.assertEqual(match.red_card_tally(), (0, 0))

    def test_the_side_of_a_red_card_is_found_from_its_team(self):
        match = espn.parse(payload(event(
            details=(red_card_detail("A1"),))), LIGUE1)[0]
        self.assertEqual(match.side_of(match.red_cards[0].team_id), "away")
        self.assertEqual(match.side_of("H1"), "home")
        self.assertEqual(match.side_of(""), "")


class TestPhase(unittest.TestCase):
    """La phase du match, lue dans status.type.name."""

    def test_the_states_espn_actually_returns(self):
        for state, name, expected in (
                ("pre", "STATUS_SCHEDULED", espn.SCHEDULED),
                ("in", "STATUS_FIRST_HALF", espn.PLAYING),
                ("in", "STATUS_HALFTIME", espn.HALFTIME),
                ("in", "STATUS_SECOND_HALF", espn.PLAYING),
                ("post", "STATUS_FULL_TIME", espn.FINAL)):
            self.assertEqual(espn.phase_of(state, name), expected, name)

    def test_extra_time_halftime_counts_as_halftime(self):
        self.assertEqual(espn.phase_of("in", "STATUS_EXTRA_TIME_HALFTIME"),
                         espn.HALFTIME)

    def test_shootout_is_still_playing(self):
        self.assertEqual(espn.phase_of("in", "STATUS_SHOOTOUT"), espn.PLAYING)

    def test_a_match_that_is_not_happening_is_unknown(self):
        for name in ("STATUS_POSTPONED", "STATUS_CANCELED", "STATUS_ABANDONED",
                     "STATUS_DELAYED", "STATUS_SUSPENDED"):
            self.assertEqual(espn.phase_of("pre", name), espn.UNKNOWN, name)

    def test_missing_status_name_falls_back_on_the_state(self):
        self.assertEqual(espn.phase_of("in", ""), espn.PLAYING)
        self.assertEqual(espn.phase_of("pre", None), espn.SCHEDULED)
        self.assertEqual(espn.phase_of("post", ""), espn.FINAL)
        self.assertEqual(espn.phase_of("n'importe quoi", ""), espn.UNKNOWN)

    def test_the_match_carries_its_phase(self):
        match = espn.parse(payload(event(
            state="in", status_name="STATUS_HALFTIME")), LIGUE1)[0]
        self.assertEqual(match.status_name, "STATUS_HALFTIME")
        self.assertEqual(match.phase, espn.HALFTIME)
        self.assertTrue(match.live)      # la mi-temps, c'est toujours "in"


class TestFetch(unittest.TestCase):
    def test_fetch_goes_through_the_opener(self):
        state = {"payload": payload(event())}
        matches = espn.scoreboard(LIGUE1, opener=opener_for(state))
        self.assertEqual(matches[0].home, "Angers")

    def test_network_failure_becomes_source_error(self):
        def broken(_url, _timeout):
            raise OSError("pas de reseau")

        with self.assertRaises(espn.SourceError):
            espn.fetch("fra.1", opener=broken)

    def test_garbage_json_becomes_source_error(self):
        with self.assertRaises(espn.SourceError):
            espn.fetch("fra.1", opener=lambda *_: b"<html>oups</html>")

    def test_non_dict_json_becomes_source_error(self):
        with self.assertRaises(espn.SourceError):
            espn.fetch("fra.1", opener=lambda *_: b"[1, 2, 3]")


class TestCompression(unittest.TestCase):
    """La compression : huit fois moins d'octets, et rien d'autre qui bouge.

    Ces tests sont les seuls du fichier a passer par `urlopen` plutot que par
    un opener : c'est justement le morceau qu'un opener remplace, donc le seul
    qu'aucun autre test ne regarde. Le reseau, lui, n'est pas touche - c'est un
    faux `urlopen` qui rend les octets qu'on lui donne.
    """

    def urlopen_giving(self, body):
        """Un faux `urlopen` qui rend ce corps-la."""
        class Response:
            def read(_self):
                return body

            def __enter__(_self):
                return _self

            def __exit__(_self, *_ignored):
                return False

        return lambda _request, timeout=None: Response()

    def download_of(self, body, label="fra.1"):
        with unittest.mock.patch.object(espn.urllib.request, "urlopen",
                                        self.urlopen_giving(body)):
            return espn.download("https://exemple.invalid/scoreboard", label=label)

    def test_the_request_asks_for_it(self):
        # Personne ne le demande a notre place : urllib n'annonce rien tout seul.
        self.assertEqual(espn.headers()["Accept-Encoding"], "gzip")

    def test_a_compressed_answer_comes_back_in_clear(self):
        page = json.dumps(payload(event())).encode("utf-8")
        self.assertEqual(self.download_of(gzip.compress(page)), page)

    def test_a_clear_answer_passes_through_untouched(self):
        # Le jour ou la source cesserait de compresser, ou un proxy qui
        # decompresse en chemin : rien ne doit changer pour autant.
        page = b'{"events": []}'
        self.assertEqual(self.download_of(page), page)

    def test_an_empty_answer_is_not_a_crash(self):
        self.assertEqual(self.download_of(b""), b"")

    def test_a_truncated_stream_names_the_competition(self):
        broken = gzip.compress(b'{"events": []}')[:10]
        with self.assertRaises(espn.SourceError) as caught:
            self.download_of(broken)
        # Le message doit dire ou ca casse, et que c'est la compression : relu
        # comme du JSON, un flux tronque donnerait "reponse illisible", ce qui
        # est vrai et n'aide personne.
        self.assertIn("fra.1", str(caught.exception))
        self.assertIn("compressee", str(caught.exception))

    def test_the_whole_read_goes_through_it(self):
        page = json.dumps(payload(event())).encode("utf-8")
        with unittest.mock.patch.object(espn.urllib.request, "urlopen",
                                        self.urlopen_giving(gzip.compress(page))):
            matches = espn.scoreboard(LIGUE1)
        self.assertEqual(matches[0].home, "Angers")

    def test_an_opener_is_left_alone(self):
        # Les tests et le rejeu passent par la, et rendent du JSON en clair :
        # le contrat de `espn.download()` ne change pas d'un caractere.
        state = {"payload": payload(event())}
        matches = espn.scoreboard(LIGUE1, opener=opener_for(state))
        self.assertEqual(matches[0].home, "Angers")

    def test_what_is_not_bytes_is_not_touched(self):
        self.assertEqual(espn.uncompress('{"events": []}'), '{"events": []}')


class TestDates(unittest.TestCase):
    """Le parametre `dates`, sur lequel repose --next."""

    def test_a_single_day_is_written_plainly(self):
        day = datetime(2026, 9, 6, tzinfo=timezone.utc)
        self.assertEqual(espn.day_code(day), "20260906")
        self.assertEqual(espn.date_span(day), "20260906")
        # Les deux bornes egales : pas d'intervalle inutile.
        self.assertEqual(espn.date_span(day, day), "20260906")

    def test_a_window_becomes_an_interval(self):
        first = datetime(2026, 9, 6, tzinfo=timezone.utc)
        last = datetime(2026, 9, 13, tzinfo=timezone.utc)
        self.assertEqual(espn.date_span(first, last), "20260906-20260913")

    def test_the_url_carries_the_window(self):
        seen = []

        def opener(url, _timeout):
            seen.append(url)
            return b'{"events": []}'

        espn.fetch("fra.1", opener=opener, dates="20260906-20260913")
        self.assertEqual(len(seen), 1)
        self.assertTrue(seen[0].startswith(
            espn.SCOREBOARD_URL.format(sport=sports.DEFAULT.code, slug="fra.1")), seen[0])
        self.assertIn("dates=20260906-20260913", seen[0])

    def test_without_dates_the_url_does_not_change(self):
        seen = []

        def opener(url, _timeout):
            seen.append(url)
            return b'{"events": []}'

        espn.fetch("fra.1", opener=opener)
        self.assertEqual(seen, [espn.SCOREBOARD_URL.format(sport=sports.DEFAULT.code, slug="fra.1")])

    def test_scoreboard_passes_the_window_along(self):
        seen = []

        def opener(url, _timeout):
            seen.append(url)
            return b'{"events": []}'

        espn.scoreboard(LIGUE1, opener=opener, dates="20260906-20260913")
        self.assertIn("dates=20260906-20260913", seen[0])


class TestTheMatchSummary(unittest.TestCase):
    """L'autre porte : 450 ko, et les buteurs que le tableau de bord n'a pas."""

    def test_the_url_names_the_sport_the_competition_and_the_match(self):
        seen = []

        def opener(url, _timeout):
            seen.append(url)
            return b'{"plays": []}'

        espn.summary(NHL, "401809123", opener=opener)
        self.assertEqual(
            seen,
            ["https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/"
             "summary?event=401809123"])

    def test_it_goes_through_the_same_read_as_everything_else(self):
        # Meme chemin, donc memes en-tetes et meme traduction des pannes : une
        # seconde facon d'appeler ESPN aurait fini par diverger de la premiere.
        def opener(_url, _timeout):
            raise OSError("le reseau est parti")

        with self.assertRaises(espn.SourceError):
            espn.summary(NHL, "1", opener=opener)

    def test_its_deadline_is_shorter_than_a_scoreboard(self):
        """Une carte attend derriere cet appel : il ne peut pas durer huit secondes."""
        seen = []

        def opener(_url, timeout):
            seen.append(timeout)
            return b'{"plays": []}'

        espn.summary(NHL, "1", opener=opener)
        self.assertEqual(seen, [espn.SUMMARY_TIMEOUT])
        self.assertLess(espn.SUMMARY_TIMEOUT, espn.DEFAULT_TIMEOUT)

    def test_only_the_goals_are_kept(self):
        goals = espn.summary_goals(hockey_summary(
            hockey_noise(index=0),
            hockey_play(team_id="H1", index=0),
            hockey_noise(index=1),
            hockey_play(team_id="A1", index=1, scorer="C. Makar", assists=()),
        ))
        self.assertEqual([play.team_id for play in goals], ["H1", "A1"])
        self.assertEqual([play.scorer for play in goals],
                         ["M. Sasson", "C. Makar"])

    def test_a_goal_recognised_by_its_label_when_the_number_moves(self):
        # Comme au rugby : deux lectures pour la meme chose, et le canari
        # signale celle qui a bouge.
        goals = espn.summary_goals(hockey_summary(
            hockey_play(type_id="9999", text="Goal")))
        self.assertEqual(len(goals), 1)

    def test_the_scorer_and_the_assists_come_from_their_role(self):
        goal = espn.summary_goals(hockey_summary(hockey_play()))[0]
        self.assertEqual(goal.scorer, "M. Sasson")
        self.assertEqual(goal.assists, ("F. Hronek", "Z. Buium"))
        self.assertEqual(goal.kind_key, "goal")
        self.assertEqual(goal.points, 1)

    def test_without_the_role_nobody_is_named_rather_than_someone_wrong(self):
        """Un but nomme jusqu'a trois joueurs : le premier venu n'est pas le buteur."""
        play = hockey_play()
        for participant in play["participants"]:
            participant["type"] = ""
        goal = espn.summary_goals(hockey_summary(play))[0]
        self.assertEqual(goal.scorer, "")
        self.assertEqual(goal.assists, ())

    def test_the_period_travels_with_the_clock(self):
        # L'horloge du hockey repart a zero trois fois : "0:29" seul ne dit pas
        # de quel tiers-temps on parle. Le numero se lit dans les cinq langues,
        # le "1st" d'ESPN non.
        goal = espn.summary_goals(hockey_summary(
            hockey_play(minute="12:07", period=2)))[0]
        self.assertEqual(goal.minute, "P2 12:07")

    def test_a_clock_without_a_period_keeps_the_clock(self):
        play = hockey_play()
        play.pop("period")
        self.assertEqual(espn.summary_goals(hockey_summary(play))[0].minute,
                         "0:29")

    def test_a_summary_without_plays_is_not_a_crash(self):
        for broken in ({}, {"plays": None}, {"plays": []}, {"plays": ["x"]}):
            self.assertEqual(espn.summary_goals(broken), [])

    def test_keys_stay_stable_across_two_reads(self):
        first = espn.summary_goals(hockey_summary(hockey_play(), hockey_play(index=1)))
        second = espn.summary_goals(hockey_summary(hockey_play(), hockey_play(index=1)))
        self.assertEqual([play.key for play in first],
                         [play.key for play in second])
        self.assertEqual(len(set(play.key for play in first)), 2)


class TestWhichGoalIsBeingAnnounced(unittest.TestCase):
    """Le buteur se choisit par le rang, jamais par "le dernier publie"."""

    def goals(self, *teams):
        return [espn.summary_goals(hockey_summary(
            hockey_play(team_id=team, index=index)))[0]
            for index, team in enumerate(teams)]

    def test_the_nth_goal_of_the_team_that_just_scored(self):
        goals = self.goals("H1", "A1", "H1")
        self.assertIs(espn.summary_scorer(goals, "H1", 2), goals[2])
        self.assertIs(espn.summary_scorer(goals, "A1", 1), goals[1])

    def test_two_goals_in_one_poll_still_announce_the_last_one(self):
        """Un releve saute : le score passe de 0 a 2, la carte nomme le 2-0."""
        goals = self.goals("H1", "H1")
        self.assertIs(espn.summary_scorer(goals, "H1", 2), goals[1])

    def test_a_summary_running_late_names_nobody(self):
        """Deux buts au tableau de bord, un seul publie : pas de nom, jamais le mauvais."""
        goals = self.goals("H1")
        self.assertIsNone(espn.summary_scorer(goals, "H1", 2))

    def test_a_summary_running_ahead_names_nobody_either(self):
        goals = self.goals("H1", "H1")
        self.assertIsNone(espn.summary_scorer(goals, "H1", 1))

    def test_a_team_the_summary_never_names(self):
        goals = self.goals("H1")
        self.assertIsNone(espn.summary_scorer(goals, "AUTRE", 1))
        self.assertIsNone(espn.summary_scorer(goals, "", 1))

    def test_nothing_to_announce_on_an_empty_list(self):
        self.assertIsNone(espn.summary_scorer([], "H1", 1))
        self.assertIsNone(espn.summary_scorer(self.goals("H1"), "H1", 0))


if __name__ == "__main__":
    unittest.main()
