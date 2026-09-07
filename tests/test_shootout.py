"""Les tirs au but, et ce que la source publie vraiment pendant une seance.

Tout ce fichier repose sur une observation, et une seule, faite sur des seances
reelles telechargees depuis le tableau de bord d'ESPN :

    **le score publie ne bouge pas pendant une seance de tirs au but.**

Verifie sur quatre competitions, en demandant a la source les journees deja
jouees (`espn.fetch(slug, dates=...)`) :

  - Chelsea 0-0 Liverpool, finale de la FA Cup, 14 mai 2022 (`eng.fa`) :
    score 0-0, `shootoutScore` 5 et 6, onze tirs publies, tous a 120' ;
  - Angers 1-1 Stade de Reims, Coupe de France, 25 fevrier 2025
    (`fra.coupe_de_france`) : score 1-1, **aucun `shootoutScore`**, huit tirs
    publies avec une horloge qui continue d'avancer (91' a 99') ;
  - Argentine 3-3 France, finale de la Coupe du monde 2022 (`fifa.world`) :
    score 3-3, `shootoutScore` 4 et 2, six tirs publies ;
  - Real Madrid et PSG, huitiemes de la Ligue des champions, mars 2025
    (`uefa.champions`) : meme forme.

Les deux premieres sont figees ici, parce qu'elles se completent : l'une porte
le total que la source donne, l'autre ne le porte pas et oblige a compter les
tirs ; l'une n'a aucun but de match, l'autre en a deux et des cartons jaunes a
ignorer. Elles sont recopiees telles que la source les sert, drapeaux compris -
une charge utile simplifiee ne prouverait plus rien du comportement reel.

Le hockey est la troisieme piece : sa fusillade ne se lit pas pareil du tout.
Elle donne un but au vainqueur, dans le score du match, et la source ne publie
aucune action pour elle. Vegas 4-3 Chicago, 3 decembre 2025 (`nhl`).
"""

import copy
import io
import unittest
from contextlib import redirect_stdout
from unittest import mock

from butbutbut import cli, espn, i18n, leagues, sports, watcher

from helpers import FakeClock, opener_for

COUPE = leagues.BY_SLUG["fra.coupe_de_france"]
FA_CUP = leagues.BY_SLUG["eng.fa"]
NHL = leagues.BY_SLUG["nhl"]


def setUpModule():
    # Ces tests affirment des formulations francaises. Sans cet epinglage ils
    # passeraient sur une machine francaise et echoueraient sur la CI, dont les
    # machines sont anglaises.
    i18n.use("fr")


# --- Les charges utiles, telles que la source les sert -----------------------

def _team(team_id, display, short, abbr, color, alternate):
    return {"id": team_id, "displayName": display, "shortDisplayName": short,
            "name": short, "location": display, "abbreviation": abbr,
            "color": color, "alternateColor": alternate,
            "logo": "https://a.espncdn.com/i/teamlogos/soccer/500/"
                    + team_id + ".png"}


def _kick(team_id, minute, seconds, athlete_id, scorer):
    """Un tir au but reussi, dans la forme exacte de la source.

    A noter, et c'est tout le sujet : `scoringPlay` est **vrai** et
    `scoreValue` vaut 1, alors que le score du match ne bougera pas d'un
    dixieme. Le seul drapeau qui distingue ce tir d'un vrai but est `shootout`.
    """
    return {
        "type": {"id": "104", "text": "Penalty - Scored"},
        "clock": {"value": float(seconds), "displayValue": minute},
        "team": {"id": team_id},
        "scoreValue": 1,
        "scoringPlay": True,
        "redCard": False,
        "yellowCard": False,
        "penaltyKick": True,
        "ownGoal": False,
        "shootout": True,
        "athletesInvolved": [{"id": athlete_id, "shortName": scorer,
                              "displayName": scorer, "fullName": scorer,
                              "team": {"id": team_id}}],
    }


def _goal(team_id, type_id, text, minute, seconds, athlete_id, scorer):
    return {
        "type": {"id": type_id, "text": text},
        "clock": {"value": float(seconds), "displayValue": minute},
        "team": {"id": team_id},
        "scoreValue": 1,
        "scoringPlay": True,
        "redCard": False,
        "yellowCard": False,
        "penaltyKick": False,
        "ownGoal": False,
        "shootout": False,
        "athletesInvolved": [{"id": athlete_id, "shortName": scorer,
                              "displayName": scorer, "fullName": scorer,
                              "team": {"id": team_id}}],
    }


def _yellow(team_id, minute, seconds, athlete_id, player):
    """Un carton jaune. La source en met partout, y compris pendant la seance."""
    return {
        "type": {"id": "94", "text": "Yellow Card"},
        "clock": {"value": float(seconds), "displayValue": minute},
        "team": {"id": team_id},
        "scoreValue": 0,
        "scoringPlay": False,
        "redCard": False,
        "yellowCard": True,
        "penaltyKick": False,
        "ownGoal": False,
        "shootout": False,
        "athletesInvolved": [{"id": athlete_id, "shortName": player,
                              "displayName": player, "fullName": player,
                              "team": {"id": team_id}}],
    }


# Angers 1-1 Stade de Reims, Coupe de France, 25 fevrier 2025. Reims passe.
# La source ne donne PAS de `shootoutScore` sur ce match-la : le total ne peut
# venir que du decompte des tirs reussis, cinq contre trois.
_ANGERS = _team("7868", "Angers", "Angers", "ANG", "1a1a1a", "ffffff")
_REIMS = _team("3243", "Stade de Reims", "Reims", "REIM", "ef2f24", "0000bf")

REIMS_KICKS = (
    _kick("3243", "91'", 5407.0, "265953", "K. Nakamura"),
    _kick("7868", "93'", 5523.0, "313889", "B. Dieng"),
    _kick("3243", "93'", 5569.0, "361468", "Gabriel Moscardo"),
    _kick("3243", "95'", 5676.0, "371471", "N. Sangui"),
    _kick("7868", "96'", 5720.0, "201198", "Z. Ferhat"),
    _kick("3243", "97'", 5776.0, "219350", "J. Ito"),
    _kick("7868", "98'", 5826.0, "357154", "L. Raolisoa"),
    _kick("3243", "99'", 5891.0, "329483", "O. Diakite"),
)

REIMS_MATCH = (
    _yellow("3243", "38'", 2250.0, "345470", "M. Gbane"),
    _yellow("7868", "45'", 2692.0, "196164", "J. Aholou"),
    _goal("3243", "137", "Goal - Header", "79'", 4703.0, "265953",
          "K. Nakamura"),
    _yellow("7868", "90'+3'", 5400.0, "201198", "Z. Ferhat"),
    _goal("7868", "173", "Goal - Volley", "90'+5'", 5400.0, "313889",
          "B. Dieng"),
)


def coupe_de_france(kicks=REIMS_KICKS, state="post",
                    status_name="STATUS_FINAL_PEN", detail="FT-Pens",
                    clock="96'", winner=True):
    """Angers - Reims, tel que la source le publie apres la seance.

    `winner=False` retire le drapeau du vainqueur : c'est la seule cle sur
    laquelle repose le nom affiche, on verifie donc aussi qu'elle peut manquer.
    """
    def side(team, where, won):
        entry = {"id": team["id"], "uid": "s:600~t:" + team["id"],
                 "type": "team", "order": 0 if where == "home" else 1,
                 "homeAway": where, "score": "1", "team": copy.deepcopy(team)}
        if winner:
            entry["winner"] = won
            entry["advance"] = won
        return entry

    return {"events": [{
        "id": "732292",
        "date": "2025-02-25T20:00Z",
        "competitions": [{
            "id": "732292",
            "date": "2025-02-25T20:00Z",
            "competitors": [side(_ANGERS, "home", False),
                            side(_REIMS, "away", True)],
            "status": {"clock": 5760.0, "displayClock": clock, "period": 5,
                       "type": {"id": "47", "name": status_name,
                                "state": state, "completed": state == "post",
                                "description": "Final Score - After Penalties",
                                "detail": detail, "shortDetail": detail}},
            "details": list(REIMS_MATCH) + list(kicks),
        }],
    }]}


# Chelsea 0-0 Liverpool, finale de la FA Cup, 14 mai 2022. Liverpool gagne 6-5.
# Onze tirs, tous horodates 120' - la seance suit une prolongation, l'horloge
# du match s'y est arretee. Et la source donne cette fois `shootoutScore`.
_CHELSEA = _team("363", "Chelsea", "Chelsea", "CHE", "144992", "FFFFFF")
_LIVERPOOL = _team("364", "Liverpool", "Liverpool", "LIV", "d11317", "FFFFFF")

FA_CUP_KICKS = (
    _kick("363", "120'", 7200.0, "146127", "M. Alonso"),
    _kick("363", "120'", 7200.0, "189007", "R. James"),
    _kick("363", "120'", 7200.0, "152469", "R. Barkley"),
    _kick("363", "120'", 7200.0, "165778", "Jorginho"),
    _kick("363", "120'", 7200.0, "176733", "H. Ziyech"),
    _kick("364", "120'", 7200.0, "26843", "J. Milner"),
    _kick("364", "120'", 7200.0, "135293", "T. Alcantara"),
    _kick("364", "120'", 7200.0, "147234", "R. Firmino"),
    _kick("364", "120'", 7200.0, "223532", "T. Alexander-Arnold"),
    _kick("364", "120'", 7200.0, "208133", "D. Jota"),
    _kick("364", "120'", 7200.0, "226177", "K. Tsimikas"),
)


def fa_cup_final(state="post", status_name="STATUS_FINAL_PEN",
                 detail="FT-Pens"):
    def side(team, where, tally, won):
        return {"id": team["id"], "uid": "s:600~t:" + team["id"],
                "type": "team", "order": 0 if where == "home" else 1,
                "homeAway": where, "score": "0", "winner": won,
                "shootoutScore": tally, "team": copy.deepcopy(team)}

    return {"events": [{
        "id": "634288",
        "date": "2022-05-14T15:45Z",
        "competitions": [{
            "id": "634288",
            "date": "2022-05-14T15:45Z",
            "competitors": [side(_CHELSEA, "home", 5, False),
                            side(_LIVERPOOL, "away", 6, True)],
            "status": {"clock": 7200.0, "displayClock": "120'", "period": 5,
                       "type": {"id": "47", "name": status_name,
                                "state": state, "completed": state == "post",
                                "description": "Final Score - After Penalties",
                                "detail": detail, "shortDetail": detail}},
            "details": [_yellow("363", "77'", 4609.0, "189007", "R. James")]
                       + list(FA_CUP_KICKS),
        }],
    }]}


# Vegas 4-3 Chicago, NHL, 3 decembre 2025. La fusillade du hockey ne ressemble
# a rien de ce qui precede : l'etat reste STATUS_FINAL, seul le detail dit
# "Final/SO", il n'y a AUCUN tableau d'actions, et le but vainqueur est deja
# compte dans le 4-3. C'est pour ca que le hockey n'a jamais eu de bug ici :
# son score bouge, donc butbutbut annonce une fois, au bon moment.

def nhl_shootout(state="post", status_name="STATUS_FINAL",
                 detail="Final/SO"):
    def side(team_id, name, where, score, color, won):
        return {"id": team_id, "homeAway": where, "score": score,
                "winner": won,
                "team": {"id": team_id, "displayName": name,
                         "shortDisplayName": name.split()[-1],
                         "abbreviation": name[:3].upper(), "color": color}}

    return {"events": [{
        "id": "401802770",
        "date": "2025-12-03T03:00Z",
        "competitions": [{
            "id": "401802770",
            "date": "2025-12-03T03:00Z",
            "competitors": [
                side("37", "Vegas Golden Knights", "home", 4, "344043", True),
                side("4", "Chicago Blackhawks", "away", 3, "e31937", False)],
            "status": {"clock": 0.0, "displayClock": "0:00", "period": 5,
                       "type": {"id": "3", "name": status_name,
                                "state": state, "completed": state == "post",
                                "description": "Final", "detail": detail,
                                "shortDetail": detail, "altDetail": "SO"}},
        }],
    }]}


# --- Ce que la source dit, et ce qu'on en tire -------------------------------

class TestTheSourceItself(unittest.TestCase):
    """Le fait brut, celui dont depend tout le reste du chantier."""

    def test_the_score_does_not_move_during_a_shootout(self):
        # Huit tirs publies, cinq reussis d'un cote, trois de l'autre, et le
        # score du match reste 1-1. C'est l'observation qui dit qu'il n'y a
        # pas de corne a couper : la detection ne verra jamais rien passer.
        match = espn.parse(coupe_de_france(), COUPE)[0]
        self.assertEqual((match.home_score, match.away_score), (1, 1))
        self.assertEqual(len(match.shootout), 8)

    def test_a_kick_carries_the_flags_of_a_goal(self):
        # Pourquoi le tri ne peut pas se faire sur scoringPlay : un tir en
        # porte un, comme un but.
        kick = REIMS_KICKS[0]
        self.assertTrue(kick["scoringPlay"])
        self.assertEqual(kick["scoreValue"], 1)
        self.assertTrue(kick["shootout"])

    def test_kicks_are_not_goals(self):
        match = espn.parse(coupe_de_france(), COUPE)[0]
        self.assertEqual([play.scorer for play in match.plays],
                         ["K. Nakamura", "B. Dieng"])

    def test_a_shootout_without_a_single_goal_leaves_no_play_at_all(self):
        match = espn.parse(fa_cup_final(), FA_CUP)[0]
        self.assertEqual(match.plays, [])
        self.assertEqual(len(match.shootout), 11)
        self.assertEqual((match.home_score, match.away_score), (0, 0))

    def test_yellow_cards_are_still_ignored(self):
        match = espn.parse(coupe_de_france(), COUPE)[0]
        self.assertEqual(match.red_cards, [])


class TestTheTally(unittest.TestCase):
    def test_the_source_total_is_used_when_it_is_there(self):
        match = espn.parse(fa_cup_final(), FA_CUP)[0]
        self.assertEqual((match.home_shootout, match.away_shootout), (5, 6))
        self.assertEqual(match.shootout_line(), "5 - 6")

    def test_kicks_are_counted_when_the_total_is_missing(self):
        # Coupe de France 2025 : pas de shootoutScore dans la reponse. Compter
        # les tirs reussis donne 3-5, ce que la seance a vraiment donne.
        match = espn.parse(coupe_de_france(), COUPE)[0]
        self.assertEqual((match.home_shootout, match.away_shootout), (3, 5))
        self.assertEqual(match.shootout_line(), "3 - 5")

    def test_the_winner_comes_from_the_source(self):
        match = espn.parse(coupe_de_france(), COUPE)[0]
        self.assertEqual(match.winner, "away")
        self.assertEqual(match.winner_name, "Stade de Reims")

    def test_no_winner_flag_is_survivable(self):
        match = espn.parse(coupe_de_france(winner=False), COUPE)[0]
        self.assertEqual(match.winner_name, "")
        self.assertTrue(match.on_penalties)

    def test_a_match_without_a_shootout_has_no_line(self):
        raw = coupe_de_france(kicks=(), status_name="STATUS_FULL_TIME",
                              detail="FT")
        match = espn.parse(raw, COUPE)[0]
        self.assertEqual(match.shootout_line(), "")
        self.assertFalse(match.on_penalties)


class TestWhoWentToPenalties(unittest.TestCase):
    def test_the_final_pen_status_is_recognised(self):
        match = espn.parse(coupe_de_france(), COUPE)[0]
        self.assertTrue(match.on_penalties)

    def test_a_match_still_being_played_never_claims_a_verdict(self):
        # Pendant la seance, le match est encore "in" : il n'y a pas de
        # verdict a annoncer, et la carte qui le porte n'est pas encore due.
        running = coupe_de_france(state="in", status_name="STATUS_SHOOTOUT",
                                  detail="Pens")
        match = espn.parse(running, COUPE)[0]
        self.assertFalse(match.on_penalties)
        self.assertEqual(match.phase, espn.PLAYING)

    def test_hockey_says_it_in_the_detail_and_not_in_the_status(self):
        match = espn.parse(nhl_shootout(), NHL)[0]
        self.assertEqual(match.status_name, "STATUS_FINAL")
        self.assertTrue(match.on_penalties)
        # Aucun tir publie, donc aucun total a afficher : le 4-3 porte deja le
        # but vainqueur.
        self.assertEqual(match.shootout_line(), "")
        self.assertEqual(match.winner_name, "Vegas Golden Knights")

    def test_an_ordinary_hockey_final_is_not_a_shootout(self):
        match = espn.parse(nhl_shootout(detail="Final"), NHL)[0]
        self.assertFalse(match.on_penalties)

    def test_overtime_is_not_a_shootout_either(self):
        match = espn.parse(nhl_shootout(detail="Final/OT"), NHL)[0]
        self.assertFalse(match.on_penalties)

    def test_rugby_never_goes_to_penalties(self):
        self.assertEqual(sports.RUGBY.shootout, ())


# --- Ce que ca donne a l'ecran -----------------------------------------------

class TestNothingHappensDuringTheShootout(unittest.TestCase):
    """Le coeur du chantier : une seance ne s'annonce pas comme dix buts."""

    def test_eight_kicks_land_without_a_single_card(self):
        before = coupe_de_france(kicks=(), state="in",
                                 status_name="STATUS_SECOND_HALF",
                                 detail="90'+5'", clock="90'+5'")
        state = {"payload": before}
        guard = watcher.Watcher([COUPE], opener=opener_for(state))
        guard.prime(pause=0)

        # Les tirs arrivent, un par un, sans que le score bouge.
        for count in range(1, len(REIMS_KICKS) + 1):
            state["payload"] = coupe_de_france(
                kicks=REIMS_KICKS[:count], state="in",
                status_name="STATUS_SHOOTOUT", detail="Pens", clock="90'+5'")
            self.assertEqual(guard.refresh(COUPE), [], "tir " + str(count))

    def test_the_end_of_the_shootout_gives_one_card_and_it_is_the_full_time(self):
        before = coupe_de_france(kicks=REIMS_KICKS, state="in",
                                 status_name="STATUS_SHOOTOUT", detail="Pens")
        state = {"payload": before}
        guard = watcher.Watcher([COUPE], opener=opener_for(state))
        guard.prime(pause=0)

        state["payload"] = coupe_de_france()
        events = guard.refresh(COUPE)
        self.assertEqual([one.kind for one in events], [watcher.FULLTIME])


class TestTheFullTimeCard(unittest.TestCase):
    def card(self, maker=coupe_de_france, league=COUPE,
             status="STATUS_FINAL_PEN", detail="FT-Pens", **kwargs):
        """La carte de fin de match, prise juste apres la seance.

        Le releve d'avant montre le match encore en cours : c'est la bascule
        qui fabrique la carte, et sans elle il n'y aurait rien a lire.
        """
        state = {"payload": maker(state="in", status_name="STATUS_SHOOTOUT",
                                  detail="Pens", **kwargs)}
        guard = watcher.Watcher([league], opener=opener_for(state))
        guard.prime(pause=0)
        state["payload"] = maker(status_name=status, detail=detail, **kwargs)
        return guard.refresh(league)[0]

    def test_it_names_the_qualifier(self):
        card = self.card()
        self.assertEqual(card.title, "FIN DU MATCH")
        self.assertEqual(card.score_line, "Angers 1 - 1 Stade de Reims")
        self.assertEqual(card.detail_line(),
                         "Tirs au but 3 - 5 : Stade de Reims")

    def test_the_qualifier_is_the_highlighted_part(self):
        # Meme regle que le buteur sur une carte de but : ce qu'on cherche des
        # yeux est ce qui est mis en valeur.
        parts = self.card().detail_parts()
        self.assertEqual(parts[-1], ("Stade de Reims", True))

    def test_the_scorers_listed_are_the_scorers_of_the_match(self):
        # Sans le tri, cette carte alignerait huit tireurs sous un 1-1.
        self.assertEqual(self.card().extra_lines(),
                         ["Angers : B. Dieng 90'+5'",
                          "Stade de Reims : K. Nakamura 79'"])

    def test_a_goalless_shootout_lists_nobody(self):
        card = self.card(maker=fa_cup_final, league=FA_CUP)
        self.assertEqual(card.extra_lines(), [])
        self.assertEqual(card.detail_line(), "Tirs au but 5 - 6 : Liverpool")

    def test_without_a_tally_the_card_still_names_the_winner(self):
        card = self.card(maker=nhl_shootout, league=NHL,
                         status="STATUS_FINAL", detail="Final/SO")
        self.assertEqual(card.detail_line(),
                         "Vainqueur aux tirs au but : Vegas Golden Knights")

    def test_without_a_winner_the_card_says_only_what_it_knows(self):
        card = self.card(winner=False)
        self.assertEqual(card.detail_line(), "Tirs au but")

    def test_an_ordinary_full_time_card_is_unchanged(self):
        card = self.card(kicks=(), status="STATUS_FULL_TIME", detail="FT")
        self.assertEqual(card.detail_line(), "")

    def test_the_card_stays_silent(self):
        # Une fin de match ne sonne pas, seance ou pas : le verdict s'ecrit,
        # il ne se corne pas.
        self.assertTrue(self.card().sober)

    def test_the_journal_keeps_the_verdict_in_french(self):
        line = self.card().log_line()
        self.assertIn("Tirs au but 3 - 5 : Stade de Reims", line)
        self.assertIn("Angers 1 - 1 Stade de Reims", line)

    def test_the_card_follows_the_language(self):
        i18n.use("en")
        try:
            self.assertEqual(self.card().detail_line(),
                             "Shootout 3 - 5: Stade de Reims")
        finally:
            i18n.use("fr")

    def test_the_journal_stays_french_whatever_the_cards_say(self):
        i18n.use("en")
        try:
            self.assertIn("Tirs au but 3 - 5 : Stade de Reims",
                          self.card().log_line())
        finally:
            i18n.use("fr")


class TestTheOtherReaders(unittest.TestCase):
    """Tout ce qui lit `plays` profite du tri, sans une ligne de plus."""

    def test_the_catch_up_card_does_not_replay_the_shootout(self):
        # Une machine qui dort pendant la seance : au reveil le score n'a pas
        # bouge, il n'y a donc rien a rattraper - et surtout pas huit tirs.
        state = {"payload": coupe_de_france(
            kicks=(), state="in", status_name="STATUS_SECOND_HALF",
            detail="90'+5'")}
        clock = FakeClock()
        logged = []
        guard = watcher.Watcher([COUPE], opener=opener_for(state),
                                catch_up=True, clock=clock,
                                on_log=logged.append)
        guard.refresh(COUPE, now=0.0)
        guard.plan_wait(now=25.0)
        clock.jump(40 * 60)

        state["payload"] = coupe_de_france()
        self.assertEqual(guard.tick(now=25.0), [])
        self.assertTrue(any("personne n'a marque" in line for line in logged),
                        logged)

    def test_scores_says_who_goes_through(self):
        # Sans cette ligne, une soiree de Coupe de France s'affiche en matchs
        # nuls et ne dit pas qui joue le tour suivant.
        matches = espn.parse(coupe_de_france(), COUPE)
        buffer = io.StringIO()
        with mock.patch.object(espn, "scoreboard", return_value=matches):
            with redirect_stdout(buffer):
                cli.main(["--scores", "--leagues", "cdf"])
        printed = buffer.getvalue()
        self.assertIn("Angers", printed)
        self.assertIn("1 - 1", printed)
        self.assertIn("tirs au but", printed)
        self.assertIn("Stade de Reims (3 - 5)", printed)

    def test_scores_does_not_list_the_kickers_as_scorers(self):
        matches = espn.parse(fa_cup_final(), FA_CUP)
        buffer = io.StringIO()
        with mock.patch.object(espn, "scoreboard", return_value=matches):
            with redirect_stdout(buffer):
                cli.main(["--scores", "--leagues", "facup"])
        printed = buffer.getvalue()
        self.assertNotIn("Jorginho", printed)
        self.assertIn("Liverpool (5 - 6)", printed)


if __name__ == "__main__":
    unittest.main()
