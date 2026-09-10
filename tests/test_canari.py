"""Le canari lui-meme, sans reseau.

Le programme de `tools/canari.py` parle a ESPN pour de vrai ; ces tests-ci ne
parlent a personne. Ils lui servent des charges utiles fabriquees a la main :
une complete (il doit dire oui), les memes amputees d'une cle ou porteuses
d'une valeur du mauvais type (il doit dire non, et nommer la cle), et une sans
le moindre match (il ne doit pas crier au loup).
"""

import copy
import importlib.util
import io
import json
import os
import unittest

from helpers import (event, goal_detail, hockey_event, hockey_noise,
                     hockey_play, hockey_summary, payload, red_card_detail,
                     rugby_detail)

# Le canari vit dans tools/, hors du paquet : on le charge par son chemin,
# depuis celui de ce fichier, pour ne dependre d'aucun repertoire courant.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SPEC = importlib.util.spec_from_file_location(
    "canari", os.path.join(ROOT, "tools", "canari.py"))
canari = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(canari)


# Les neuf statistiques d'un camp, telles que la source les publie : trois
# cles par objet, pas une de plus, et des valeurs ecrites en toutes lettres.
# Le canari n'en surveille que deux, mais il doit les trouver au milieu des
# autres - c'est la seule facon de savoir si l'une a ete renommee.
STATISTICS = [
    {"name": "foulsCommitted", "displayValue": "16", "abbreviation": "FC"},
    {"name": "wonCorners", "displayValue": "7", "abbreviation": "CW"},
    {"name": "possessionPct", "displayValue": "60.1", "abbreviation": "PP"},
    {"name": "totalShots", "displayValue": "20", "abbreviation": "SHOT"},
    {"name": "shotsOnTarget", "displayValue": "7", "abbreviation": "SOG"},
    {"name": "totalGoals", "displayValue": "1", "abbreviation": "G"},
    {"name": "goalAssists", "displayValue": "1", "abbreviation": "A"},
    {"name": "shotAssists", "displayValue": "14", "abbreviation": "SHAST"},
    {"name": "appearances", "displayValue": "0", "abbreviation": "APP"},
]


def board(*events):
    """Une charge utile complete, telle que la source la sert vraiment.

    `helpers` fabrique le minimum que `espn.py` sait lire ; le canari, lui,
    surveille la forme entiere de la reponse - y compris des cles qui ne
    servent qu'en repli (`team.name`, `team.location`) et les drapeaux qui
    accompagnent toujours une action (`redCard` sur un but, `ownGoal` sur une
    expulsion). On les repose donc ici, comme ESPN les envoie.
    """
    raw = payload(*events)
    raw["leagues"] = [{"name": "French Ligue 1", "abbreviation": "FRA.1"}]
    for entry in raw["events"]:
        competition = entry["competitions"][0]
        entry.setdefault("date", competition["date"])
        started = competition["status"]["type"]["state"] != "pre"
        for competitor in competition["competitors"]:
            # Les statistiques du match, que la source ne remplit qu'une fois
            # le ballon parti : un match a venir garde son tableau vide, et le
            # canari dira "non verifie" plutot que "MANQUE". C'est la difference
            # entre une cle disparue et une cle qui n'a rien a dire encore.
            if started and not competitor.get("statistics"):
                competitor["statistics"] = list(STATISTICS)
            team = competitor["team"]
            team.setdefault("name", team["shortDisplayName"])
            team.setdefault("location", team["displayName"])
            team.setdefault("color", "1b458f")
            team.setdefault("alternateColor", "ffffff")
            team.setdefault(
                "logo", "https://a.espncdn.com/i/teamlogos/soccer/500/1.png")
        for detail in competition["details"]:
            for flag in ("scoringPlay", "redCard", "ownGoal", "penaltyKick",
                         "shootout"):
                detail.setdefault(flag, False)
            for athlete in detail.get("athletesInvolved") or []:
                athlete.setdefault("displayName", athlete.get("shortName"))
    return raw


def played(match_id="1"):
    """Un match joue, avec un but et une expulsion a inspecter."""
    return board(event(
        match_id=match_id, home_score=1, away_score=2, state="post",
        detail="FT", clock="90'", status_name="STATUS_FULL_TIME",
        details=[goal_detail("H" + match_id),
                 red_card_detail("A" + match_id)]))


def shootout_board(winner=True):
    """Un match de coupe decide aux tirs au but, comme la source le publie.

    Un tir au but porte `scoringPlay`, exactement comme un but, et seul le
    drapeau `shootout` l'en distingue - alors que le score du match, lui, ne
    bouge pas. Le canari doit donc les compter a part : sans ca il rougirait a
    chaque soiree de coupe, pour un comportement voulu.
    """
    def kick(team_id, player, index):
        one = goal_detail(team_id, "91'", player, penalty=True, index=index)
        one["shootout"] = True
        return one

    raw = board(event(
        home_score=1, away_score=1, state="post", detail="FT-Pens",
        clock="96'", status_name="STATUS_FINAL_PEN",
        details=[goal_detail("H1", "79'", "K. Nakamura"),
                 goal_detail("A1", "90'+5'", "B. Dieng", index=1),
                 kick("H1", "Z. Ferhat", 2),
                 kick("A1", "J. Ito", 3)]))
    if winner:
        for competitor in raw["events"][0]["competitions"][0]["competitors"]:
            competitor["winner"] = competitor["homeAway"] == "away"
    return raw


def catalogue(count=3):
    """L'autre endpoint : la liste des equipes, qui valide --teams."""
    return {"sports": [{"leagues": [{"teams": [
        {"team": {"id": str(index),
                  "displayName": "Club " + str(index),
                  "shortDisplayName": "Club" + str(index),
                  "abbreviation": "C" + str(index)}}
        for index in range(count)]}]}]}


def hockey_board(*events):
    """Un tableau de bord de hockey : le meme, sans le moindre `details`.

    C'est tout le sujet du sport ici - la cle n'est pas vide, elle est absente,
    et le canari ne doit pas la reclamer. Les competiteurs portent la meme
    parure que partout ailleurs, sauf `alternateColor`, que le hockey ne
    publie pas.
    """
    raw = payload(*(events or (hockey_event(home_score=2, away_score=1,
                                            state="post", detail="Final",
                                            status_name="STATUS_FINAL"),)))
    raw["leagues"] = [{"name": "National Hockey League", "abbreviation": "NHL"}]
    for entry in raw["events"]:
        competition = entry["competitions"][0]
        entry.setdefault("date", competition["date"])
        for competitor in competition["competitors"]:
            team = competitor["team"]
            team.setdefault("name", team["shortDisplayName"])
            team.setdefault("location", team["displayName"])
            team.setdefault(
                "logo", "https://a.espncdn.com/i/teamlogos/nhl/500/bos.png")
    return raw


def rugby_match(match_id="1"):
    """Un match de rugby joue : un essai transforme, une penalite, un change.

    Le remplacement n'est pas du decor. Il vaut deux actions sur trois dans un
    match, espn.py n'en lit rien, et le canari ne doit donc rien lui reclamer.
    """
    return event(
        match_id=match_id, home="Toulon", away="La Rochelle",
        home_score=7, away_score=3, state="post", detail="FT", clock="80'",
        status_name="STATUS_FULL_TIME",
        details=[rugby_detail("H" + match_id, "try", "8'", "L. Carter"),
                 rugby_detail("H" + match_id, "conversion", "9'", "M. Serin",
                              index=1),
                 rugby_detail("A" + match_id, "penalty goal", "24'",
                              "A. Hastoy", index=2),
                 rugby_detail("H" + match_id, "player substituted", "55'",
                              "T. Ollivon", index=3)])


def rugby_board(*events):
    """Un tableau de bord de rugby, tel que la source le sert vraiment.

    Deux differences avec celui du football, et ce sont elles qu'on teste : pas
    un seul drapeau sur les actions - la nature se lit dans `type.id` - et des
    equipes sans ville ni couleur secondaire. Ni `location` ni
    `alternateColor` ne sont donc reposes ici : les reclamer serait guetter des
    cles qu'ESPN n'a jamais publiees pour ce sport.
    """
    raw = payload(*(events or (rugby_match(),)))
    raw["leagues"] = [{"name": "French Top 14", "abbreviation": "TOP14"}]
    for entry in raw["events"]:
        competition = entry["competitions"][0]
        entry.setdefault("date", competition["date"])
        for competitor in competition["competitors"]:
            team = competitor["team"]
            team.setdefault("name", team["shortDisplayName"])
            team.setdefault("color", "b01c2e")
            team.setdefault(
                "logo",
                "https://a.espncdn.com/i/teamlogos/rugby/teams/500/1.png")
    return raw


def hockey_digest():
    """Le resume d'un match de hockey : deux buts pour l'un, un pour l'autre."""
    return hockey_summary(
        hockey_noise(),
        hockey_play(team_id="H1"),
        hockey_play(team_id="A1", index=1, scorer="C. Makar", assists=()),
        hockey_play(team_id="H1", index=2, period=3, scorer="J. Eichel"))


def opener_for(live=None, past=None, teams=None, seen=None, digest=None):
    """Un opener(url, timeout) qui sert la bonne charge utile selon l'URL."""
    def opener(url, _timeout):
        if seen is not None:
            seen.append(url)
        if url.endswith("/teams"):
            body = teams if teams is not None else catalogue()
        elif "/summary" in url:
            body = digest
        elif "dates=" in url:
            body = past
        else:
            body = live
        if body is None:
            raise IOError("rien de simule pour " + url)
        return json.dumps(body).encode("utf-8")
    return opener


def canary(live=None, past=None, teams=None, seen=None, digest=None,
           argv=("--leagues", "fra.1")):
    """Lance le canari et rend (code de sortie, rapport)."""
    out = io.StringIO()
    code = canari.main(list(argv),
                       opener=opener_for(live, past, teams, seen, digest),
                       out=out)
    return code, out.getvalue()


HOCKEY = ("--leagues", "hockey:nhl")
RUGBY = ("--leagues", "rugby:270559")


def without(source, *path):
    """La meme charge utile, amputee d'une cle. Le dernier mot est la cle."""
    copied = copy.deepcopy(source)
    node = copied
    for step in path[:-1]:
        node = node[step]
    node.pop(path[-1], None)
    return copied


class TestTheHockeySummary(unittest.TestCase):
    """Le hockey a un endpoint de plus, et donc des cles de plus a surveiller."""

    def run_it(self, digest=None, live=None, seen=None):
        return canary(live=live if live is not None else hockey_board(),
                      digest=hockey_digest() if digest is None else digest,
                      seen=seen, argv=HOCKEY)

    def test_a_complete_summary_is_green(self):
        code, report = self.run_it()
        self.assertEqual(code, 0, report)
        self.assertIn("3 but(s), 3 buteur(s)", report)
        self.assertIn("0 en defaut, 0 non verifiee(s)", report)

    def test_the_keys_of_plays_are_watched_by_name(self):
        _, report = self.run_it()
        for path in ("resume.plays[].type.id",
                     "resume.but.team.id",
                     "resume.but.period.number",
                     "resume.but.participants",
                     "resume.but.participants[].type",
                     "resume.but.participants[].athlete.shortName"):
            self.assertIn(path, report)

    def test_a_renamed_role_is_caught(self):
        digest = hockey_digest()
        for play in digest["plays"]:
            for participant in play.get("participants") or []:
                participant.pop("type", None)

        code, report = self.run_it(digest=digest)
        self.assertEqual(code, 1, report)
        self.assertIn("resume.but.participants[].type", report)
        # Et la lecture reelle le confirme : plus un seul nom sur les cartes.
        self.assertIn("aucun buteur nomme sur 3 but(s)", report)

    def test_a_participants_list_that_empties_is_caught(self):
        digest = hockey_digest()
        for play in digest["plays"]:
            play["participants"] = []

        code, report = self.run_it(digest=digest)
        self.assertEqual(code, 1, report)
        self.assertIn("resume.but.participants", report)

    def test_a_goal_type_that_changes_number_and_label_is_still_caught(self):
        """Le seul cas que le comptage a la main ne verrait pas tout seul.

        Le canari lit `505` et "Goal" dans espn.py : si les deux bougent
        ensemble, il compte zero but et le programme aussi, et les deux
        tombent d'accord sur du vide. L'invariante qui sauve la mise est
        ailleurs : ce resume-la est celui d'un match qui a marque.
        """
        digest = hockey_summary(hockey_noise(), hockey_noise(index=1))
        code, report = self.run_it(digest=digest)
        self.assertEqual(code, 1, report)
        self.assertIn("pas un seul but reconnu", report)

    def test_an_unreachable_summary_is_not_a_red_light(self):
        """Injoignable n'est pas casse : c'est le meme verdict que partout."""
        code, report = canary(live=hockey_board(), argv=HOCKEY)
        self.assertEqual(code, 2, report)
        self.assertIn("INJOIGNABLE", report)

    def test_no_summary_is_asked_when_nothing_has_been_scored(self):
        seen = []
        board = hockey_board(hockey_event(state="pre", detail="Fri 7:00 PM",
                                          status_name="STATUS_SCHEDULED"))
        code, report = canary(live=board, past=board, seen=seen, argv=HOCKEY)
        self.assertEqual(code, 0, report)
        self.assertIn("aucun match avec but", report)
        self.assertEqual([url for url in seen if "/summary" in url], [])

    def test_one_summary_and_one_only(self):
        """450 ko : la question se repond sur un match aussi bien que sur trente."""
        seen = []
        self.run_it(live=hockey_board(
            hockey_event(match_id="1", home_score=2, away_score=1),
            hockey_event(match_id="2", home_score=1, away_score=0)), seen=seen)
        self.assertEqual(len([url for url in seen if "/summary" in url]), 1)


class TestFootballPaysForNothingExtra(unittest.TestCase):
    def test_no_summary_key_is_declared_for_football(self):
        _, report = canary(live=played())
        self.assertNotIn("resume.", report)

    def test_and_no_summary_is_ever_fetched(self):
        seen = []
        canary(live=played(), seen=seen)
        self.assertEqual([url for url in seen if "/summary" in url], [])


class TestTheMissingDetailsOfHockey(unittest.TestCase):
    def test_hockey_does_not_require_a_secondary_colour(self):
        code, report = canary(live=hockey_board(), digest=hockey_digest(),
                              argv=HOCKEY)
        self.assertEqual(code, 0, report)
        self.assertNotIn("competitor.team.alternateColor", report)

    def test_a_sport_without_actions_is_not_asked_for_any(self):
        """`details` est absent de tous les matchs de hockey : ce n'est pas une panne."""
        code, report = canary(live=hockey_board(), digest=hockey_digest(),
                              argv=HOCKEY)
        self.assertEqual(code, 0, report)
        self.assertNotIn("competition.details", report)
        self.assertNotIn("detail.athletesInvolved", report)

    def test_football_still_watches_them(self):
        _, report = canary(live=played())
        self.assertIn("competition.details", report)
        self.assertIn("detail.athletesInvolved[0].shortName", report)


class TestTheOtherGrammarOfRugby(unittest.TestCase):
    """Le rugby a le meme tableau d'actions que le football, et pas sa grammaire.

    Un essai ne porte pas `scoringPlay` : il porte `type.id` = "1". Le canari
    qui reclamerait les drapeaux du football verrait quatre cles manquer sur
    chaque journee de Top 14 - un rouge quotidien pour une source qui n'a
    jamais rien promis de tel.
    """

    def test_a_complete_rugby_board_is_green(self):
        code, report = canary(live=rugby_board(), argv=RUGBY)
        self.assertEqual(code, 0, report)

    def test_the_flags_of_football_are_never_asked_of_rugby(self):
        _, report = canary(live=rugby_board(), argv=RUGBY)
        for flag in ("detail.scoringPlay", "detail.redCard", "detail.ownGoal",
                     "detail.penaltyKick", "detail.shootout"):
            self.assertNotIn(flag, report)

    def test_the_type_of_the_action_is_watched_instead(self):
        _, report = canary(live=rugby_board(), argv=RUGBY)
        self.assertIn("detail.type.id", report)
        self.assertIn("detail.type.text", report)

    def test_neither_town_nor_secondary_colour_is_asked_of_rugby(self):
        _, report = canary(live=rugby_board(), argv=RUGBY)
        self.assertNotIn("competitor.team.location", report)
        self.assertNotIn("competitor.team.alternateColor", report)

    def test_football_is_still_held_to_all_of_them(self):
        _, report = canary(live=played())
        self.assertIn("detail.scoringPlay", report)
        self.assertIn("competitor.team.alternateColor", report)
        self.assertIn("competitor.team.location", report)

    def test_a_try_that_loses_its_clock_is_caught(self):
        board = rugby_board()
        board["events"][0]["competitions"][0]["details"][0].pop("clock")
        code, report = canary(live=board, past=rugby_board(), argv=RUGBY)
        self.assertEqual(code, 1, report)
        self.assertIn("detail.clock.displayValue", report)

    def test_an_action_that_scores_nothing_is_not_inspected(self):
        """Le remplacement peut manquer ce qu'il veut : espn.py n'en lit rien."""
        board = rugby_board()
        board["events"][0]["competitions"][0]["details"][-1].pop("clock")
        code, report = canary(live=board, argv=RUGBY)
        self.assertEqual(code, 0, report)


class TestASilentRenumbering(unittest.TestCase):
    """Le piege propre au tri par type, et le seul filet qui le rattrape.

    Si ESPN renumerotait ses types, pas une cle ne manquerait : le canari et
    espn.py lisent la meme table et se tromperaient ensemble. Ce qui trahit la
    derive est ailleurs - une journee de matchs finis, des points au tableau,
    et pas une action reconnue.
    """

    def test_a_day_of_finished_matches_without_one_action_is_caught(self):
        board = rugby_board()
        for detail in board["events"][0]["competitions"][0]["details"]:
            detail["type"] = {"id": "77", "text": "score"}
        code, report = canary(live=board, past=board, argv=RUGBY)
        self.assertEqual(code, 1, report)
        self.assertIn("le tri des actions ne reconnait plus rien", report)

    def test_a_match_still_to_be_played_says_nothing(self):
        """0-0 avant le coup d'envoi : aucune action, et c'est bien normal."""
        board = rugby_board(event(
            home="Toulon", away="La Rochelle", state="pre",
            detail="Sat 12 Sep at 17:00", clock="0'",
            status_name="STATUS_SCHEDULED"))
        code, report = canary(live=board, past=board, argv=RUGBY)
        self.assertEqual(code, 0, report)


class TestHealthyPayload(unittest.TestCase):
    def test_a_complete_payload_is_green(self):
        code, report = canary(live=played())
        self.assertEqual(code, 0, report)
        self.assertIn("VERT", report)
        self.assertIn("0 en defaut, 0 non verifiee(s)", report)

    def test_the_report_names_every_watched_key(self):
        _, report = canary(live=played())
        for path in ("competitor.homeAway", "competitor.score",
                     "competitor.team.displayName", "competitor.team.color",
                     "competition.status.type.state", "detail.scoringPlay",
                     "detail.penaltyKick", "detail.ownGoal",
                     "detail.athletesInvolved[0].shortName",
                     "equipes.teams[].team.abbreviation"):
            self.assertIn(path, report)


class TestMissingKeys(unittest.TestCase):
    """Une cle qui disparait : c'est tout ce que le canari existe pour voir."""

    def amputate(self, *path):
        code, report = canary(live=without(played(), *path))
        self.assertEqual(code, 1, report)
        self.assertIn("MANQUE", report)
        return report

    def test_a_missing_side_is_caught(self):
        report = self.amputate("events", 0, "competitions", 0, "competitors",
                               0, "homeAway")
        self.assertIn("competitor.homeAway", report)

    def test_a_missing_penalty_flag_is_caught(self):
        report = self.amputate("events", 0, "competitions", 0, "details", 0,
                               "penaltyKick")
        self.assertIn("detail.penaltyKick", report)

    def test_a_missing_scorer_is_caught(self):
        """Pas par le compte de cles, mais par le second filet du canari.

        `athletesInvolved` est SAMPLED et non REQUIRED : la source laisse
        parfois une action sans joueur nomme, et crier au loup la-dessus tous
        les matins apprendrait a ignorer le rouge. C'est le re-passage dans
        espn.parse() qui rattrape la disparition - des cles presentes qui ne
        produisent plus rien, c'est exactement ce qu'il surveille.
        """
        code, report = canary(live=without(played(), "events", 0,
                                           "competitions", 0, "details", 0,
                                           "athletesInvolved"))
        self.assertEqual(code, 1, report)
        self.assertIn("aucun buteur nomme", report)

    def test_a_disappearing_notes_array_is_caught(self):
        # Le tableau est sur chaque match, meme vide. C'est lui qu'on surveille,
        # pas la note : une note qui n'arrive plus ne casse rien, un tableau
        # devenu autre chose se lirait de travers.
        report = self.amputate("events", 0, "competitions", 0, "notes")
        self.assertIn("competition.notes", report)

    def test_a_renamed_state_is_caught(self):
        report = self.amputate("events", 0, "competitions", 0, "status",
                               "type", "state")
        self.assertIn("competition.status.type.state", report)

    def test_a_missing_team_name_is_caught(self):
        report = self.amputate("events", 0, "competitions", 0, "competitors",
                               0, "team")
        self.assertIn("competitor.team", report)

    def test_an_emptied_team_catalogue_is_caught(self):
        # Vide, il ferait refuser tous les noms de --teams au demarrage.
        code, report = canary(live=played(), teams={"sports": []})
        self.assertEqual(code, 1, report)
        self.assertIn("equipes.sports", report)


class TestWrongTypes(unittest.TestCase):
    def test_a_score_that_is_not_a_number_is_caught(self):
        raw = played()
        competitor = raw["events"][0]["competitions"][0]["competitors"][0]
        competitor["score"] = "beaucoup"
        code, report = canary(live=raw)
        self.assertEqual(code, 1, report)
        self.assertIn("TYPE", report)
        self.assertIn("competitor.score", report)

    def test_a_flag_that_stops_being_a_boolean_is_caught(self):
        raw = played()
        raw["events"][0]["competitions"][0]["details"][0]["ownGoal"] = "oui"
        code, report = canary(live=raw)
        self.assertEqual(code, 1, report)
        self.assertIn("TYPE", report)
        self.assertIn("detail.ownGoal", report)


class TestShootout(unittest.TestCase):
    """Une soiree de coupe : deux buts, deux tirs au but, et rien de rouge."""

    def test_a_cup_night_is_green_and_counts_the_kicks_apart(self):
        code, report = canary(live=shootout_board())
        self.assertEqual(code, 0, report)
        self.assertIn("2 but(s)", report)
        self.assertIn("2 tir(s) au but", report)

    def test_an_ordinary_night_says_nothing_about_penalties(self):
        # Une mention "0 tir(s) au but" sur toutes les lignes du rapport ferait
        # du bruit tous les jours pour un fait de quelques soirs par an.
        _code, report = canary(live=played())
        self.assertNotIn("tir(s) au but", report)

    def test_a_shootout_that_names_no_winner_is_caught(self):
        # Le drapeau `winner` est la seule chose de la reponse qui dise qui se
        # qualifie sur un 1-1. Le perdre, c'est perdre la carte.
        code, report = canary(live=shootout_board(winner=False))
        self.assertEqual(code, 1, report)
        self.assertIn("sans drapeau winner", report)


class TestTheStatisticsAreWatchedByName(unittest.TestCase):
    """Renommer une statistique ne casse rien : c'est bien le probleme.

    La carte de fin de match perdrait sa ligne sans qu'un seul test ne
    bronche, puisque tous fabriquent eux-memes leur charge utile. C'est
    exactement le genre de panne muette pour lequel le canari existe.
    """

    def renamed(self, before, after):
        live = played()
        for competitor in live["events"][0]["competitions"][0]["competitors"]:
            for entry in competitor["statistics"]:
                if entry["name"] == before:
                    entry["name"] = after
        return live

    def test_a_renamed_statistic_is_caught(self):
        code, report = canary(live=self.renamed("possessionPct",
                                                "possessionPercent"))
        self.assertEqual(code, 1, report)
        self.assertIn("competitor.statistics.possessionPct", report)
        # Et l'autre, qui n'a pas bouge, reste verte : le rapport nomme le
        # degat, il ne rougit pas en bloc.
        for line in report.splitlines():
            if "competitor.statistics.shotsOnTarget" in line:
                self.assertIn("ok", line)
                break
        else:
            self.fail("shotsOnTarget absent du rapport")

    def test_a_value_that_stops_being_a_number_is_caught(self):
        live = played()
        for competitor in live["events"][0]["competitions"][0]["competitors"]:
            for entry in competitor["statistics"]:
                if entry["name"] == "shotsOnTarget":
                    entry["displayValue"] = "sept"
        code, report = canary(live=live)
        self.assertEqual(code, 1, report)
        self.assertIn("competitor.statistics.shotsOnTarget", report)

    def test_an_emptied_block_is_not_a_failure(self):
        # Un match a venir n'a rien a dire de lui-meme : la cle est la, le
        # tableau est vide, et ce n'est pas une disparition.
        live = played()
        for competitor in live["events"][0]["competitions"][0]["competitors"]:
            competitor["statistics"] = []
        code, report = canary(live=live)
        self.assertEqual(code, 0, report)
        self.assertIn("non verifie", report)

    def test_a_vanished_block_is_a_failure(self):
        live = played()
        for competitor in live["events"][0]["competitions"][0]["competitors"]:
            competitor.pop("statistics")
        code, report = canary(live=live)
        self.assertEqual(code, 1, report)
        self.assertIn("competitor.statistics", report)

    def test_hockey_is_never_asked_for_statistics(self):
        # Le hockey en publie, mais d'un tout autre genre, et sa carte n'en
        # affiche aucune : lui reclamer les noms du football ferait rougir le
        # canari tous les matins pour un fait connu.
        _, report = canary(live=hockey_board(), digest=hockey_digest(),
                           argv=HOCKEY)
        self.assertNotIn("statistics", report)


class TestNothingToCheck(unittest.TestCase):
    """Un mardi de juillet : rien a verifier n'est pas un echec."""

    def test_an_empty_board_is_not_a_failure(self):
        code, report = canary(live={"events": []}, past={"events": []})
        self.assertEqual(code, 0, report)
        self.assertIn("aucun match a inspecter", report)
        self.assertIn("non verifie", report)
        self.assertNotIn("MANQUE", report)

    def test_a_board_without_any_action_leaves_the_flags_unverified(self):
        # Des matchs a venir : aucun but, donc aucun drapeau a regarder.
        upcoming = board(event(state="pre", status_name="STATUS_SCHEDULED",
                               clock="0'", detail="Sun 6 Sep at 17:00"))
        code, report = canary(live=upcoming, past={"events": []})
        self.assertEqual(code, 0, report)
        for line in report.splitlines():
            if "detail.penaltyKick" in line:
                self.assertIn("non verifie", line)
                break
        else:
            self.fail("detail.penaltyKick absent du rapport")


class TestLookback(unittest.TestCase):
    def test_a_day_without_goals_sends_the_canary_into_the_past(self):
        seen = []
        code, report = canary(live={"events": []}, past=played(), seen=seen)
        self.assertEqual(code, 0, report)
        self.assertTrue(any("dates=" in url for url in seen), seen)
        # Le premier appel est celui du daemon : sans parametre de date.
        self.assertNotIn("dates=", seen[0])
        self.assertIn("rattrapage", report)
        self.assertIn("0 en defaut, 0 non verifiee(s)", report)

    def test_a_day_with_goals_asks_nothing_more(self):
        seen = []
        canary(live=played(), seen=seen)
        self.assertFalse([url for url in seen if "dates=" in url], seen)

    def test_an_explicit_date_is_honoured(self):
        seen = []
        canary(live=played(), seen=seen,
               argv=("--leagues", "fra.1", "--dates", "20250517"))
        self.assertIn("dates=20250517", seen[0])

    def test_the_lookback_window_is_an_espn_range(self):
        import datetime
        window = canari.lookback_range(datetime.date(2026, 9, 7), days=120)
        self.assertEqual(window, "20260510-20260907")


class TestUnreachableSource(unittest.TestCase):
    def test_a_silent_source_is_its_own_verdict(self):
        # Ni vert ni rouge : on n'a rien pu regarder, et ca se dit.
        code, report = canary()
        self.assertEqual(code, 2, report)
        self.assertIn("INJOIGNABLE", report)


class TestCrossCheck(unittest.TestCase):
    """Les cles peuvent etre la sans que le vrai code en tire quoi que ce soit."""

    def test_the_real_parser_is_run_on_what_was_fetched(self):
        raw = played()
        ledger = canari.Ledger()
        tally = canari.inspect_scoreboard(raw, ledger)
        self.assertEqual(tally["goals"], 1)
        self.assertEqual(tally["red_cards"], 1)
        self.assertEqual(canari.cross_check(raw, "fra.1", tally, ledger), [])

    def test_a_goal_without_a_scorer_is_reported(self):
        raw = played()
        for detail in raw["events"][0]["competitions"][0]["details"]:
            detail["athletesInvolved"] = []
        ledger = canari.Ledger()
        tally = canari.inspect_scoreboard(raw, ledger)
        problems = canari.cross_check(raw, "fra.1", tally, ledger)
        self.assertTrue(any("buteur" in problem for problem in problems),
                        problems)

    def test_the_form_the_source_really_writes_is_accepted(self):
        # 90'+9' est ce qu'ESPN ecrit vraiment. Le canari doit se taire dessus.
        raw = played()
        for detail in raw["events"][0]["competitions"][0]["details"]:
            detail["clock"]["displayValue"] = "90'+9'"
        ledger = canari.Ledger()
        tally = canari.inspect_scoreboard(raw, ledger)
        self.assertEqual(canari.cross_check(raw, "fra.1", tally, ledger), [])

    def test_a_clock_that_changes_shape_is_reported(self):
        # La cle est la, la valeur aussi, et plus personne ne sait la lire :
        # c'est exactement ce qui a fait taire le compteur des arrets de jeu.
        raw = played()
        for detail in raw["events"][0]["competitions"][0]["details"]:
            detail["clock"]["displayValue"] = "90:00"
        ledger = canari.Ledger()
        tally = canari.inspect_scoreboard(raw, ledger)
        problems = canari.cross_check(raw, "fra.1", tally, ledger)
        self.assertTrue(any("horloge" in problem for problem in problems),
                        problems)

    def test_a_hockey_clock_is_not_held_to_a_football_minute(self):
        # 12:34 est l'horloge normale d'un match de hockey : illisible comme
        # minute de jeu, et ce n'est pas une anomalie.
        raw = played()
        for detail in raw["events"][0]["competitions"][0]["details"]:
            detail["clock"]["displayValue"] = "12:34"
        ledger = canari.Ledger()
        tally = canari.inspect_scoreboard(raw, ledger)
        problems = canari.cross_check(raw, "nhl", tally, ledger)
        self.assertFalse(any("horloge" in problem for problem in problems),
                         problems)


class TestDig(unittest.TestCase):
    def test_it_walks_dotted_paths_and_indexes(self):
        source = {"sports": [{"leagues": [{"teams": [1, 2]}]}]}
        self.assertEqual(canari.dig(source, "sports.0.leagues.0.teams"),
                         (True, [1, 2]))

    def test_a_missing_link_is_not_a_crash(self):
        self.assertEqual(canari.dig({"a": {"b": 1}}, "a.c.d"), (False, None))
        self.assertEqual(canari.dig({"a": []}, "a.0"), (False, None))


if __name__ == "__main__":
    unittest.main()
