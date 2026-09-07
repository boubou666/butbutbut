"""Relecture du journal : de quoi recapituler une journee, ou un mois, de buts.

Pourquoi relire du texte plutot que tenir la liste dans le fichier d'etat :

  - le journal est la seule trace durable. Le fichier d'etat est une photo du
    daemon en cours, jetable par construction (on l'efface, on n'a rien perdu
    d'important) ; le journal, lui, survit a un redemarrage, a un plantage, a
    une mise a jour, et il contient deja tous les buts depuis l'installation ;
  - `--today` doit repondre meme quand plus rien ne tourne. On regarde le
    recapitulatif de la soiree le lendemain matin, daemon arrete ;
  - le format n'est pas celui d'un tiers : ces lignes sortent de
    `Event.log_line()`, c'est-a-dire de nous. Le parseur est donc teste contre
    la fonction qui les ecrit, et le cout du texte se limite a ce module.

Ce qui n'est pas parsable est ignore sans bruit : le journal contient aussi les
lignes de demarrage, les erreurs reseau et tout ce qu'on y ajoutera demain. Et
il a pu tourner sur plusieurs versions du programme : une ligne d'un format
qu'on ne connait plus est une ligne de moins, jamais une erreur.

Une seule lecture, parametree par une fenetre de dates (`goals_between`), sert
tous les recapitulatifs : la journee, la semaine, le mois, et le classement des
buteurs. Les jours sont des chaines AAAA-MM-JJ d'un bout a l'autre, jamais des
dates : c'est la forme du journal, elle se compare telle quelle (le tri
alphabetique d'une date ISO est son tri chronologique), et le filtre tombe donc
avant l'analyseur, ligne par ligne.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from . import i18n, watcher

# Les cles de titre que log_line() peut poser devant un score qui bouge. Le
# journal est toujours ecrit en francais, mais on prend les libelles dans le
# catalogue plutot qu'en dur : une reformulation ne doit pas rendre muet
# `--today` sans que rien ne le dise.
#
# Le rugby en apporte quatre (essai, transformation, penalite, drop) et le
# hockey aucune : un but de hockey se dit "but", comme au football.
_GOAL_KEYS = ("title_goal", "title_own_goal", "title_penalty", "title_points",
              "title_try", "title_conversion", "title_penalty_goal",
              "title_drop_goal")
_CANCELLED_KEYS = ("title_cancelled", "title_points_cancelled")


def _heads() -> tuple:
    """Les en-tetes reconnus, du plus long au plus court.

    L'ordre compte peu - le motif exige un " [" derriere l'en-tete, donc "BUT"
    ne mord pas sur "BUT ANNULE [" - mais le garder decroissant met le lecteur
    a l'abri d'un futur libelle qui serait prefixe d'un autre.
    """
    found = []
    for keys, kind in ((_CANCELLED_KEYS, watcher.CANCELLED),
                       (_GOAL_KEYS, watcher.GOAL)):
        for key in keys:
            head = i18n.text(key, lang=i18n.FALLBACK).rstrip(" !")
            if head and (head, kind) not in found:
                found.append((head, kind))
    return tuple(sorted(found, key=lambda row: -len(row[0])))


HEADS = _heads()

_STAMP = re.compile(r"^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2})\s\s+(.+)$")
_SCORE = re.compile(r"^(?P<home>.+?) (?P<home_score>\d+) - (?P<away_score>\d+) "
                    r"(?P<away>.+)$")


class Entry:
    """Un but relu dans le journal."""

    __slots__ = ("day", "time", "kind", "league", "home", "away", "home_score",
                 "away_score", "team", "detail", "minute")

    def __init__(self, day, time, kind, league, home, away, home_score,
                 away_score, team, detail, minute):
        self.day = day                # 2026-09-06
        self.time = time              # 18:43:27
        self.kind = kind              # watcher.GOAL ou watcher.CANCELLED
        self.league = league
        self.home = home
        self.away = away
        self.home_score = home_score
        self.away_score = away_score
        self.team = team              # equipe qui marque
        self.detail = detail          # "But de M. Odegaard", "Score corrige"
        self.minute = minute          # 50', ou vide

    @property
    def goal(self) -> bool:
        return self.kind == watcher.GOAL

    @property
    def scorer(self) -> str:
        """Le buteur, quand le journal le connait.

        La source publie ses actions avec quelques secondes de retard : un but
        detecte avant elle est journalise sans buteur, et le restera.
        """
        head, sep, name = self.detail.partition(" de ")
        return name.strip() if sep and head else ""

    def score_line(self) -> str:
        return "{} {} - {} {}".format(self.home, self.home_score,
                                      self.away_score, self.away)

    def __repr__(self):
        return "<Entry {} {} {}>".format(self.time, self.kind, self.score_line())


def parse_line(line: str):
    """Un but a partir d'une ligne de journal, ou None si ce n'en est pas une."""
    stamp = _STAMP.match(line.strip())
    if stamp is None:
        return None
    day, clock, body = stamp.group(1), stamp.group(2), stamp.group(3)

    for head, kind in HEADS:
        if body.startswith(head + " ["):
            body = body[len(head) + 1:]
            break
    else:
        return None

    if not body.startswith("["):
        return None
    end = body.find("] ")
    if end < 0:
        return None
    league, rest = body[1:end], body[end + 2:]

    # " pour <equipe>" separe le score du reste : c'est le seul repere sur
    # lequel s'appuyer, un nom d'equipe pouvant contenir a peu pres n'importe
    # quoi ("Bayer 04 Leverkusen" fait deja mentir la lecture des chiffres).
    score, sep, tail = rest.partition(" pour ")
    if not sep:
        score, tail = rest, ""

    found = _SCORE.match(score)
    if found is None:
        return None

    minute = ""
    if tail.endswith(")"):
        cut = tail.rfind(" (")
        if cut > 0:
            minute, tail = tail[cut + 2:-1], tail[:cut]

    team, _sep, detail = tail.partition(" - ")

    return Entry(day=day, time=clock, kind=kind, league=league,
                 home=found.group("home"), away=found.group("away"),
                 home_score=int(found.group("home_score")),
                 away_score=int(found.group("away_score")),
                 team=team.strip(), detail=detail.strip(), minute=minute.strip())


def goals_between(path, since=None, until=None) -> list:
    """Les buts d'une fenetre de dates, dans l'ordre du journal.

    `since` et `until` sont des jours AAAA-MM-JJ, bornes comprises ; None
    ouvre le cote correspondant, et les deux a None rendent tout le journal.
    La comparaison est celle de deux chaines : voir l'en-tete du module.

    Un journal absent, vide, illisible ou coupe en route n'est pas une erreur :
    c'est une fenetre sans but de plus. Rendre ce qu'on a deja lu vaut mieux
    qu'une trace d'erreur pour une commande dont tout l'interet est de repondre
    quand plus rien ne tourne.
    """
    found = []
    try:
        with Path(path).open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                # Le filtre sur la date avant le parseur : un journal de
                # plusieurs mois se lit alors sans travail inutile. Une ligne
                # sans horodatage (la suite d'un bloc, par exemple) commence
                # par une espace, donc tombe avant toute borne.
                day = line[:10]
                if since is not None and day < since:
                    continue
                if until is not None and day > until:
                    continue
                entry = parse_line(line)
                if entry is not None:
                    found.append(entry)
    except Exception:
        return found
    return found


def goals(path, day=None) -> list:
    """Les buts d'une journee, dans l'ordre du journal.

    `day` au format 2026-09-06 ; par defaut aujourd'hui. Une journee n'est
    qu'une fenetre d'un jour : tout le travail est dans goals_between().
    """
    day = day or "{:%Y-%m-%d}".format(datetime.now())
    return goals_between(path, day, day)


def _group(entries, key) -> list:
    """[(valeur, [buts])], dans l'ordre d'apparition de chaque valeur."""
    order = []
    grouped = {}
    for entry in entries:
        value = key(entry)
        if value not in grouped:
            grouped[value] = []
            order.append(value)
        grouped[value].append(entry)
    return [(value, grouped[value]) for value in order]


def by_league(entries) -> list:
    """[(competition, [buts])], dans l'ordre du premier but de la fenetre."""
    return _group(entries, lambda entry: entry.league)


def by_day(entries) -> list:
    """[(jour, [buts])], du plus ancien au plus recent.

    C'est l'ordre du journal, qui est ecrit au fil de l'eau : rien a trier.
    """
    return _group(entries, lambda entry: entry.day)


def settle(entries) -> tuple:
    """Les buts que la VAR a laisses debout. Rend ([buts], annulations orphelines).

    Le journal ne dit pas QUEL but une annulation efface : la ligne
    "BUT ANNULE" ne porte ni buteur ni minute du but d'origine, seulement le
    score revenu en arriere (voir watcher.Event.log_line, qui n'a pas plus a
    ecrire : la source annonce une baisse de score, pas l'action retiree). Le
    rattachement ne peut donc etre que positionnel : une annulation retire le
    dernier but encore debout de la meme equipe dans le meme match. C'est
    exactement ce que fait l'arbitre video, et une pile par (competition,
    match, equipe) suffit a le rejouer.

    Les annulations orphelines sont celles qui ne trouvent aucun but a
    retirer : le but est tombe avant le debut de la fenetre, ou sa ligne etait
    illisible. On les compte a part plutot que de deduire un but au hasard -
    un classement des buteurs qui vole un but a quelqu'un est pire qu'un
    classement qui avoue son trou.
    """
    standing = {}       # (competition, match, equipe) -> pile d'index de buts
    live = set()
    orphans = 0
    for index, entry in enumerate(entries):
        key = (entry.league, entry.home, entry.away, entry.team)
        if entry.goal:
            standing.setdefault(key, []).append(index)
            live.add(index)
            continue
        stack = standing.get(key)
        if stack:
            live.discard(stack.pop())
        else:
            orphans += 1
    # sorted() : l'ordre du journal, que le passage par un ensemble a perdu.
    return [entries[index] for index in sorted(live)], orphans


class Board:
    """Le classement des buteurs d'une fenetre du journal."""

    __slots__ = ("rows", "signalled", "confirmed", "cancelled", "unknown",
                 "orphans")

    def __init__(self, rows, signalled, confirmed, cancelled, unknown,
                 orphans):
        self.rows = rows            # [(buteur, buts, equipes)], du haut vers le bas
        self.signalled = signalled  # buts vus passer, annulations non comprises
        self.confirmed = confirmed  # ce qu'il en reste une fois la VAR passee
        self.cancelled = cancelled  # lignes "BUT ANNULE" de la fenetre
        self.unknown = unknown      # buts confirmes dont le buteur manque
        self.orphans = orphans      # annulations sans but a retirer

    def __repr__(self):
        return "<Board {} buteur(s) {} but(s)>".format(len(self.rows),
                                                       self.confirmed)


def scoreboard(entries) -> Board:
    """Le classement des buteurs, buts annules deduits.

    Un buteur ne garde pas un but que la VAR a refuse : c'est tout l'interet
    de passer par settle() plutot que de compter les lignes "BUT".

    Le journal ne connait pas toujours le buteur - la source publie ses actions
    avec quelques secondes de retard, et un but detecte avant elle est ecrit
    sans nom, definitivement. Ces buts-la sont comptes a part et jamais
    attribues : mieux vaut un classement qui dit ce qui lui manque.
    """
    kept, orphans = settle(entries)
    tally = {}
    clubs = {}
    unknown = 0
    for entry in kept:
        name = entry.scorer
        if not name:
            unknown += 1
            continue
        tally[name] = tally.get(name, 0) + 1
        seen = clubs.setdefault(name, [])
        # Un buteur peut changer de club en cours de journal, et marquer pour
        # son club puis pour sa selection.
        if entry.team and entry.team not in seen:
            seen.append(entry.team)
    # A egalite, l'ordre alphabetique : le meme journal doit rendre deux fois
    # le meme classement, et l'ordre d'un dictionnaire ne le promet pas.
    rows = [(name, tally[name], "/".join(clubs[name]))
            for name in sorted(tally, key=lambda name: (-tally[name], name))]
    cancelled = sum(1 for entry in entries if not entry.goal)
    return Board(rows=rows, signalled=len(entries) - cancelled,
                 confirmed=len(kept), cancelled=cancelled, unknown=unknown,
                 orphans=orphans)
