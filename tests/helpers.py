"""Fabrique de charges utiles ESPN, pour les tests."""

import copy
import json
import struct
import zlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from butbutbut import cli


# --- La machine de qui lance les tests n'est pas un decor --------------------

def isolate_data_dir(test):
    """Detourne le dossier de donnees vers un temporaire. Rend `cli.paths()`.

    A appeler dans le setUp de TOUT test qui traverse `cli.main()` ou
    `cli.paths()`. Sans lui, le test lit le dossier de donnees de la machine
    qui le lance, donc le VRAI fichier de configuration de qui developpe - et
    `config.apply()` en verse le contenu dans les defauts du parseur avant que
    la ligne de commande ne soit analysee.

    Ce n'est pas une precaution de principe : sur une machine ou butbutbut est
    installe et configure, vingt-cinq tests tombaient pour cette seule raison.
    `--table` suivait la Ligue 2 et ne surveillait qu'un club, parce que le
    fichier le demande, la ou le test n'avait demande ni l'une ni l'autre. Et
    la CI restait verte, ses machines n'ayant aucun fichier : le pire des cas,
    un test qui ne casse que chez celui qui se sert du programme.

    Le detournement passe par `cli.data_dir`, une fonction et non une
    constante, et c'est la seule porte - la configuration, le journal, l'etat,
    le pid, le son et les ecussons en descendent tous. Isoler la racine les
    isole donc tous, y compris ce qui s'ajoutera demain.

    Le nettoyage est pose sur le test (`addCleanup`) : il a lieu meme quand le
    test echoue, et il n'y a pas de tearDown a oublier.
    """
    tmp = TemporaryDirectory()
    patcher = mock.patch.object(cli, "data_dir", return_value=Path(tmp.name))
    patcher.start()
    test.addCleanup(patcher.stop)
    test.addCleanup(tmp.cleanup)
    return cli.paths()


def goal_detail(team_id, minute="35'", scorer="C. Arcus", own_goal=False,
                penalty=False, index=0):
    return {
        "type": {"id": "70", "text": "Own Goal" if own_goal else "Goal"},
        "clock": {"value": 60.0 * index, "displayValue": minute},
        "team": {"id": team_id},
        "scoreValue": 1,
        "scoringPlay": True,
        "ownGoal": own_goal,
        "penaltyKick": penalty,
        "shootout": False,
        "athletesInvolved": [{"id": "9" + str(index), "shortName": scorer}],
    }


def red_card_detail(team_id, minute="62'", player="J. Lefort", index=0):
    """Un carton rouge : meme tableau `details` qu'un but, autre drapeau."""
    return {
        "type": {"id": "94", "text": "Red Card"},
        "clock": {"value": 60.0 * index, "displayValue": minute},
        "team": {"id": team_id},
        "scoringPlay": False,
        "yellowCard": False,
        "redCard": True,
        "athletesInvolved": [{"id": "7" + str(index), "shortName": player}],
    }


def in_minutes(minutes) -> str:
    """Une date ISO a N minutes d'ici : pour les annonces d'avant-match."""
    when = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    return when.strftime("%Y-%m-%dT%H:%M:%SZ")


def at_local_hour(days_ahead, hour, minute=0) -> str:
    """Une date ISO UTC pour un coup d'envoi a l'heure LOCALE voulue.

    in_minutes() suffit pour un compte a rebours, pas pour verifier un
    regroupement par jour : "dans 120 min" tombe la veille ou le lendemain
    selon l'heure a laquelle la suite est lancee. Ici le jour local est choisi,
    donc le test dit la meme chose a 9 h et a 23 h, sous tous les fuseaux.
    """
    local = (datetime.now().replace(hour=hour, minute=minute, second=0,
                                    microsecond=0)
             + timedelta(days=days_ahead))
    # Un datetime naif est lu comme une heure locale par astimezone().
    return local.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def team(name, color="", alternate="", logo=""):
    """Un competiteur, tel que la source le decrit.

    `name` peut etre une chaine (on derive alors un nom court et une
    abreviation plausibles) ou un tuple (nom complet, nom court, abreviation)
    quand un test a besoin des vraies ecritures - "PSG" par exemple.

    Les couleurs et l'ecusson ne sont poses que s'ils sont demandes : la source
    les omet aussi, et le code doit tenir sans.
    """
    if isinstance(name, (tuple, list)):
        display, short, abbr = (list(name) + [None, None])[:3]
    else:
        display, short, abbr = name, name, name[:3].upper()
    entry = {"displayName": display, "shortDisplayName": short or display,
             "abbreviation": abbr or display[:3].upper()}
    if color:
        entry["color"] = color
    if alternate:
        entry["alternateColor"] = alternate
    if logo:
        entry["logo"] = logo
    return entry


def _standing(form, record) -> dict:
    """La forme et le bilan d'un camp, absents quand on ne les demande pas.

    Absents, et non vides : c'est ce que la source fait au hockey, et c'est ce
    que la grande majorite des tests doit voir - sans quoi ils passeraient tous
    par un chemin que le hockey ne prend jamais.
    """
    extra = {}
    if form:
        extra["form"] = form
    if record:
        extra["records"] = [{"name": "All Splits", "type": "total",
                             "summary": record, "abbreviation": "Total"}]
    return extra


def event(match_id="1", home="Angers", away="Stade Rennais", home_score=0,
          away_score=0, state="in", detail="35'", clock="35'",
          date="2026-09-06T15:15Z", details=(), status_name="",
          home_colors=(), away_colors=(), home_logo="", away_logo="",
          home_form="", away_form="", home_record="", away_record=""):
    return {
        "id": match_id,
        "competitions": [{
            "id": match_id,
            "date": date,
            "competitors": [
                dict({"homeAway": "home", "score": str(home_score),
                      "team": dict(team(home, *home_colors, logo=home_logo),
                                   id="H" + match_id)},
                     **_standing(home_form, home_record)),
                dict({"homeAway": "away", "score": str(away_score),
                      "team": dict(team(away, *away_colors, logo=away_logo),
                                   id="A" + match_id)},
                     **_standing(away_form, away_record)),
            ],
            "status": {"displayClock": clock,
                       "type": {"state": state, "shortDetail": detail,
                                "name": status_name}},
            "details": list(details),
        }],
    }


# --- Les autres sports -------------------------------------------------------
# Ce que la vraie source publie ailleurs qu'au football, releve sur
# `hockey/nhl` et sur les competitions de `rugby/<numero>`. Les differences
# sont exactement celles que espn.py doit encaisser, et elles sont reproduites
# ici telles quelles - c'est tout l'interet de ces fabriques.

# Rugby : `type.id` porte la nature de l'action, et il n'y a AUCUN drapeau -
# ni scoringPlay, ni redCard, ni scoreValue.
RUGBY_TYPE_IDS = {
    "try": "1",
    "conversion": "2",
    "penalty goal": "3",
    "drop goal": "4",
    "yellow card": "5",
    "red card": "6",
    "player substituted": "7",
    "substitute on": "8",
    "start of first half": "9",
    "end of first half": "10",
    "start of second half": "11",
    "end of second half": "12",
    "drop goal-missed": "37",
}


def rugby_detail(team_id, kind="try", minute="8'", player="L. Carter", index=0):
    """Une action de rugby, dans la forme exacte de la source.

    Aucun drapeau : c'est `type.id` qui dit s'il s'agit d'un essai, d'une
    transformation ou d'un remplacement. Lue avec le lecteur du football, une
    telle action ne serait tout simplement pas vue.
    """
    detail = {
        "type": {"id": RUGBY_TYPE_IDS.get(kind, "0"), "text": kind},
        "clock": {"value": 60.0 * index, "displayValue": minute},
        "team": {"id": team_id},
    }
    if player:
        detail["athletesInvolved"] = [{
            "id": "3" + str(index),
            "fullName": player,
            "displayName": player,
            "shortName": player,
            "position": "FH",
            "links": [],
        }]
    return detail


def hockey_event(match_id="1", home="Boston Bruins", away="Montreal Canadiens",
                 home_score=0, away_score=0, state="in",
                 detail="2nd Period - 12:07", clock="12:07", period=2,
                 date="2026-09-19T23:00Z", status_name="STATUS_IN_PROGRESS"):
    """Un match de hockey tel que la source le publie.

    Deux ecarts avec le football, et ils sont volontaires :

      - **aucune cle `details`**. La source n'en publie pas pour le hockey, ni
        pendant le match ni apres : pas de tableau d'actions, donc jamais de
        buteur. La fabrique ne peut pas en offrir un que la source n'a pas ;
      - le score est un **entier**, pas une chaine, et l'equipe n'a qu'une
        seule couleur.

    `period` remplace la mi-temps : 1, 2, 3, puis 4 (prolongation) et 5 (tirs
    au but).
    """
    def side(name, where, score, team_id, color):
        return {"homeAway": where, "score": score,
                "team": {"id": team_id, "displayName": name,
                         "shortDisplayName": name.split()[-1],
                         "abbreviation": name[:3].upper(), "color": color}}

    return {
        "id": match_id,
        "competitions": [{
            "id": match_id,
            "date": date,
            "competitors": [
                side(home, "home", home_score, "H" + match_id, "231f20"),
                side(away, "away", away_score, "A" + match_id, "c41230"),
            ],
            "status": {"clock": 727.0, "displayClock": clock, "period": period,
                       "type": {"state": state, "name": status_name,
                                "shortDetail": detail, "detail": detail}},
        }],
    }


def payload(*events):
    return {"events": list(events)}


# --- Le resume d'un match ----------------------------------------------------
# L'autre porte, celle que seul le hockey pousse : `/summary?event=<id>`. Ce
# que la vraie source y met, releve sur un match de NHL - 302 actions dont 14
# buts, et les buteurs que le tableau de bord n'a jamais eus.

def hockey_play(team_id="H1", minute="0:29", period=1, scorer="M. Sasson",
                assists=("F. Hronek", "Z. Buium"), index=0, type_id="505",
                text="Goal"):
    """Un but tel que `plays[]` le publie : un type, une equipe, des roles.

    Rien ici ne ressemble a `details` : pas de `athletesInvolved`, pas de
    `ownGoal`, pas de minute de jeu. Un tableau `participants` ou chaque entree
    porte son role, et une horloge qui repart a zero a chaque tiers-temps.
    """
    people = []
    if scorer:
        people.append({"type": "scorer",
                       "athlete": {"id": "S" + str(index), "shortName": scorer},
                       "ytdGoals": 12})
    for rank, name in enumerate(assists):
        people.append({"type": "assister",
                       "athlete": {"id": "A{}{}".format(index, rank),
                                   "shortName": name},
                       "ytdAssists": 35})
    return {
        "type": {"id": type_id, "text": text},
        "text": "{} {} ({})".format(scorer or "?", text, index + 1),
        "scoringPlay": True,
        "scoreValue": 1,
        "period": {"number": period, "displayValue": "{}st".format(period)},
        "clock": {"displayValue": minute},
        "team": {"id": team_id},
        "participants": people,
    }


def hockey_noise(team_id="H1", index=0):
    """Une action qui n'est pas un but : le gros du resume, et rien pour nous.

    Sur les 302 actions d'un match, 288 sont de cette espece. Les melanger aux
    buts dans les tests est le seul moyen de verifier que le tri tient.
    """
    return {
        "type": {"id": "506", "text": "Shot"},
        "scoringPlay": False,
        "period": {"number": 1, "displayValue": "1st"},
        "clock": {"displayValue": "4:1{}".format(index)},
        "team": {"id": team_id},
        "participants": [{"type": "shooter",
                          "athlete": {"id": "X", "shortName": "P. Kane"}}],
    }


def hockey_summary(*plays):
    """Le resume d'un match, reduit a ce que butbutbut y lit.

    La vraie reponse porte aussi `boxscore`, `rosters`, `leaders`, `odds`,
    `videos`, `news` et `standings` - 450 ko en tout. On n'en reproduit rien :
    le programme ne lit que `plays[]`, et une fabrique qui recopierait le reste
    donnerait a croire qu'on s'en sert.
    """
    return {"plays": list(plays)}


# --- Les classements ---------------------------------------------------------
# Le classement a un endpoint et une forme a lui, releves sur la vraie source :
# un objet, un tableau `children` de blocs (un championnat en a un, la NHL deux,
# une Coupe du monde douze), et dans chaque bloc des `entries` faites d'une
# equipe et d'une liste plate de statistiques.

def standing_entry(name, team_id="1", note="", **stats):
    """Une ligne de classement : une equipe et ses statistiques.

    Les statistiques se passent par leur `type` ESPN - gamesplayed, wins,
    pointdifferential, rank - parce que c'est sous ce nom que les colonnes de
    sports.py vont les chercher. La source les nomme deux fois, `type` et
    `name` ; on pose les deux, comme elle.
    """
    return {
        "team": {"id": team_id, "displayName": name,
                 "shortDisplayName": name.split()[-1],
                 "abbreviation": name[:3].upper()},
        "note": {"description": note} if note else {},
        "stats": [{"name": key, "type": key, "displayValue": str(value)}
                  for key, value in stats.items()],
    }


def standings_payload(*groups, **kwargs):
    """La reponse du classement. `groups` : des (nom du bloc, [lignes]).

    Sans aucun bloc, c'est la reponse d'une coupe hors saison : la source rend
    alors un objet complet, mais sans le moindre `children`.
    """
    name = kwargs.pop("name", "French Ligue 1")
    season = kwargs.pop("season", "2026-27 French Ligue 1")
    answer = {"name": name, "abbreviation": name,
              "season": {"year": 2026, "displayName": season}}
    if groups:
        answer["children"] = [
            {"name": group_name, "abbreviation": season,
             "standings": {"name": "overall", "seasonDisplayName": season,
                           "entries": list(entries)}}
            for group_name, entries in groups]
    return answer


def opener_for(state):
    """Un opener() pour espn.fetch, qui sert state['payload'] a chaque appel."""
    def opener(_url, _timeout):
        return json.dumps(state["payload"]).encode("utf-8")
    return opener


def bump(source, side="away", by=1, details=()):
    """Copie la charge utile en ajoutant `by` point(s) a un cote.

    `by` vaut 1 au football et au hockey, 5 pour un essai, 3 pour une penalite.
    Le tableau d'actions n'est cree que s'il y a quelque chose a y mettre : le
    hockey n'en a pas du tout, et lui en inventer un mentirait sur la source.
    """
    after = copy.deepcopy(source)
    competition = after["events"][0]["competitions"][0]
    for competitor in competition["competitors"]:
        if competitor["homeAway"] == side:
            competitor["score"] = str(int(competitor["score"]) + by)
    if details:
        competition.setdefault("details", []).extend(details)
    return after


class FakeClock:
    """Une horloge murale qu'on avance a la main.

    Un test ne peut pas endormir la machine : on simule le saut de temps que
    la veille ou l'hibernation laisse derriere elle.
    """

    def __init__(self, start=1600000000.0):
        self.now = float(start)

    def __call__(self):
        return self.now

    def jump(self, seconds):
        self.now += float(seconds)
def png_bytes(width=8, height=8):
    """Un vrai PNG, fabrique ici plutot que range en binaire dans le depot.

    Le cache d'ecussons refuse ce qui n'a pas la signature d'un PNG : il faut
    donc de quoi lui donner l'un et l'autre.
    """
    def chunk(tag, data):
        body = tag + data
        return (struct.pack(">I", len(data)) + body
                + struct.pack(">I", zlib.crc32(body) & 0xffffffff))

    rows = b"".join(b"\x00" + b"\xff\x00\x00" * width for _ in range(height))
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(rows))
            + chunk(b"IEND", b""))


class FakeFont:
    """Une police mesurable sans tkinter : largeur fixe par caractere.

    Suffit a tester la geometrie des cartes sur une machine sans ecran.
    """

    def __init__(self, width=8, line=16):
        self.width = width
        self.line = line

    def measure(self, text):
        return len(text) * self.width

    def metrics(self, _what="linespace"):
        return self.line


def fake_fonts(**widths):
    base = {"label": 7, "title": 9, "team": 11, "score": 15,
            "detail": 8, "scorer": 9}
    base.update(widths)
    return {name: FakeFont(width) for name, width in base.items()}
