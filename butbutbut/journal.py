"""Relecture du journal : de quoi recapituler une journee de buts.

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
lignes de demarrage, les erreurs reseau et tout ce qu'on y ajoutera demain.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from . import watcher

# Les en-tetes que log_line() peut poser devant un but. "BUT ANNULE" avant
# "BUT" : l'alternance s'arrete au premier motif qui colle.
HEADS = (
    ("BUT ANNULE", watcher.CANCELLED),
    ("BUT", watcher.GOAL),
)

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


def goals(path, day=None) -> list:
    """Les buts d'une journee, dans l'ordre du journal.

    `day` au format 2026-09-06 ; par defaut aujourd'hui. Un journal absent
    n'est pas une erreur : c'est une journee sans but de plus.
    """
    day = day or "{:%Y-%m-%d}".format(datetime.now())
    found = []
    try:
        with Path(path).open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                # Le filtre sur la date avant le parseur : un journal de
                # plusieurs mois se lit alors sans travail inutile.
                if not line.startswith(day):
                    continue
                entry = parse_line(line)
                if entry is not None:
                    found.append(entry)
    except Exception:
        return found
    return found


def by_league(entries) -> list:
    """[(competition, [buts])], dans l'ordre du premier but de la journee."""
    order = []
    grouped = {}
    for entry in entries:
        if entry.league not in grouped:
            grouped[entry.league] = []
            order.append(entry.league)
        grouped[entry.league].append(entry)
    return [(name, grouped[name]) for name in order]
