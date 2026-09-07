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
from datetime import datetime, timedelta
from pathlib import Path

from . import i18n, watcher

# Les cles de titre que log_line() peut poser devant un score qui bouge, et le
# mot court qui les nomme quand il en existe un. Le journal est toujours ecrit
# en francais, mais on prend les libelles dans le catalogue plutot qu'en dur :
# une reformulation ne doit pas rendre muet `--today` sans que rien ne le dise.
#
# Le rugby en apporte quatre (essai, transformation, penalite, drop) et le
# hockey aucune : un but de hockey se dit "but", comme au football.
#
# L'en-tete est la SEULE chose qui dise la nature d'un but : la ligne ne porte
# pas de drapeau "penalty" ou "csc", elle porte "BUT SUR PENALTY". C'est donc
# de lui que `survey()` tire la part des penaltys et des csc, et c'est pour ca
# que l'analyseur retient la cle qui a mordu au lieu de la jeter.
_NATURES = (
    ("title_goal", "goal"),
    ("title_own_goal", "own_goal"),
    ("title_penalty", "penalty"),
    # "POINTS !" est le titre generique du rugby : aucune action ne le porte,
    # donc le catalogue n'a pas de mot court a lui opposer.
    ("title_points", ""),
    ("title_try", "try"),
    ("title_conversion", "conversion"),
    ("title_penalty_goal", "penalty_goal"),
    ("title_drop_goal", "drop_goal"),
)
_GOAL_KEYS = tuple(key for key, _short in _NATURES)
_CANCELLED_KEYS = ("title_cancelled", "title_points_cancelled")
_SHORT_KEYS = dict(_NATURES)


def _heads() -> tuple:
    """Les en-tetes reconnus, du plus long au plus court.

    L'ordre compte peu - le motif exige un " [" derriere l'en-tete, donc "BUT"
    ne mord pas sur "BUT ANNULE [" - mais le garder decroissant met le lecteur
    a l'abri d'un futur libelle qui serait prefixe d'un autre.
    """
    found = []
    seen = set()
    for keys, kind in ((_CANCELLED_KEYS, watcher.CANCELLED),
                       (_GOAL_KEYS, watcher.GOAL)):
        for key in keys:
            head = i18n.text(key, lang=i18n.FALLBACK).rstrip(" !")
            if head and (head, kind) not in seen:
                seen.add((head, kind))
                found.append((head, kind, key))
    return tuple(sorted(found, key=lambda row: -len(row[0])))


HEADS = _heads()


def label_of(key) -> str:
    """Le nom lisible d'une nature de but : "But", "Penalty", "Essai".

    Le titre de carte ("BUT SUR PENALTY !") crie : il est fait pour etre lu de
    l'autre bout de la piece. Dans une colonne de tableau on prend donc le mot
    court du catalogue, et a defaut le titre calme.
    """
    short = _SHORT_KEYS.get(key)
    if short:
        return i18n.text(short, lang=i18n.FALLBACK)
    return i18n.text(key, lang=i18n.FALLBACK).rstrip(" !").capitalize()


_STAMP = re.compile(r"^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2})\s\s+(.+)$")
_SCORE = re.compile(r"^(?P<home>.+?) (?P<home_score>\d+) - (?P<away_score>\d+) "
                    r"(?P<away>.+)$")
# La minute de jeu telle que le journal l'ecrit : 50', 90+3', ou 45 tout sec.
# Tout le reste - l'horloge d'un match de hockey (12:34), un libelle de phase,
# une ligne d'une version dont on ne connait plus la forme - n'est pas une
# minute de jeu : mieux vaut l'avouer que la faire entrer de travers dans un
# histogramme dont c'est justement la precision qui fait tout l'interet.
_MINUTE = re.compile(r"^(\d{1,3})\s*(?:\+\s*(\d{1,3}))?\s*'?$")


class Entry:
    """Un but relu dans le journal."""

    __slots__ = ("day", "time", "kind", "league", "home", "away", "home_score",
                 "away_score", "team", "detail", "minute", "key")

    def __init__(self, day, time, kind, league, home, away, home_score,
                 away_score, team, detail, minute, key=""):
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
        self.key = key                # title_penalty, title_own_goal...

    @property
    def goal(self) -> bool:
        return self.kind == watcher.GOAL

    @property
    def match(self) -> tuple:
        """De quel match vient ce but : (competition, recevant, visiteur).

        La competition en fait partie : deux equipes se croisent en
        championnat et en coupe, et ce ne sont pas les memes matchs.
        """
        return (self.league, self.home, self.away)

    @property
    def clock(self):
        """(minute, temps additionnel) du but, ou None si ce n'est pas lisible.

        Voir _MINUTE : le journal n'ecrit pas que des minutes de football.
        """
        found = _MINUTE.match(self.minute.strip())
        if found is None:
            return None
        return int(found.group(1)), int(found.group(2) or 0)

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

    for head, kind, key in HEADS:
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
                 team=team.strip(), detail=detail.strip(),
                 minute=minute.strip(), key=key)


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


# La soiree commence a 6h du matin. Un but tombe avant appartient a la veille :
# voir evening_of(), qui explique pourquoi.
EVENING_HOUR = 6
# L'histogramme des minutes : des tranches de dix, et jamais moins que les
# quatre-vingt-dix minutes d'un match. Une tranche vide dit quelque chose -
# "aucun but dans le dernier quart d'heure" est une forme, exactement comme un
# baton qui deborde - et s'arreter au dernier but l'effacerait.
MINUTE_SLICE = 10
MINUTE_FLOOR = 90


def evening_of(entry) -> str:
    """La soiree d'un but : son jour, sauf quand il tombe apres minuit.

    Le journal change de jour a minuit, une soiree de football non. Un coup
    d'envoi a 21h qui part en prolongation, une affiche sud-americaine, un
    match de NHL vu depuis l'Europe : le but de 00h12 et celui de 23h50
    appartiennent a la meme soiree, et compter par jour de calendrier en
    ferait deux demi-soirees dont aucune n'a existe.

    Six heures du matin coupe la nuit : aucun match ne commence a 5h, et
    personne ne parle du but de 00h40 comme du match du lendemain. Un
    horodatage illisible garde son jour tel quel plutot que de disparaitre.
    """
    try:
        hour = int(entry.time[:2])
    except (TypeError, ValueError, IndexError):
        return entry.day
    if hour >= EVENING_HOUR:
        return entry.day
    try:
        moment = datetime.strptime(entry.day, "%Y-%m-%d")
    except (TypeError, ValueError):
        return entry.day
    return "{:%Y-%m-%d}".format(moment - timedelta(days=1))


class Survey:
    """Les formes qu'une fenetre du journal cache : de quoi nourrir --stats.

    Tout est compte sur les buts que la VAR a laisses debout (settle()) : un
    but efface ne doit pas gonfler un histogramme plus qu'il ne gonfle un
    classement de buteurs. Les lignes d'annulation, elles, restent comptees a
    part, et servent aussi a savoir qu'un match a bien ete suivi.
    """

    __slots__ = ("signalled", "confirmed", "cancelled", "orphans", "buckets",
                 "timed", "untimed", "added", "leagues", "evenings", "natures",
                 "matches")

    def __init__(self, signalled, confirmed, cancelled, orphans, buckets,
                 timed, untimed, added, leagues, evenings, natures, matches):
        self.signalled = signalled  # lignes "BUT", annulations non comprises
        self.confirmed = confirmed  # ce qu'il en reste une fois la VAR passee
        self.cancelled = cancelled  # lignes "BUT ANNULE" de la fenetre
        self.orphans = orphans      # annulations sans but a retirer
        self.buckets = buckets      # [(premiere minute, derniere, buts)]
        self.timed = timed          # buts dont la minute etait lisible
        self.untimed = untimed      # ... et ceux dont elle ne l'etait pas
        self.added = added          # buts dans le temps additionnel
        self.leagues = leagues      # [(competition, buts)], du plus fourni
        self.evenings = evenings    # [(soiree, buts)], de la plus prolifique
        self.natures = natures      # [(cle de titre, buts)], ordre du catalogue
        self.matches = matches      # matchs ou quelque chose a ete signale

    @property
    def per_match(self) -> float:
        """Buts confirmes par match. 0.0 quand rien n'a ete vu.

        A lire pour ce que c'est : la moyenne des matchs OU UN BUT EST TOMBE.
        Un 0-0 ne laisse aucune ligne dans le journal, donc aucune trace ici,
        et cette moyenne est mecaniquement plus haute que celle d'une saison.
        C'est le prix d'un journal qui n'ecrit que ce qui bouge, et il vaut
        mieux le dire que publier un chiffre qu'on croirait comparable.
        """
        return (self.confirmed / float(self.matches)) if self.matches else 0.0

    def __repr__(self):
        return "<Survey {} but(s) {} match(s)>".format(self.confirmed,
                                                       self.matches)


def _slices(minutes) -> list:
    """Les tranches de dix minutes couvrant `minutes`. [(debut, fin, buts)].

    La minute 10 va dans la tranche 1-10 et la 11 dans la suivante : on compte
    comme un commentateur, pas comme une machine. La minute 0 - un but signale
    avant que l'horloge ne parte - rejoint la premiere tranche, faute de mieux.
    """
    top = max([MINUTE_FLOOR] + list(minutes))
    count = (top + MINUTE_SLICE - 1) // MINUTE_SLICE
    tally = [0] * count
    for minute in minutes:
        tally[max(0, minute - 1) // MINUTE_SLICE] += 1
    return [(index * MINUTE_SLICE + 1, (index + 1) * MINUTE_SLICE, tally[index])
            for index in range(count)]


def _ranked(tally) -> list:
    """[(valeur, compte)] du plus fourni au moins fourni, puis alphabetique.

    L'ordre alphabetique a egalite, comme pour le classement des buteurs : le
    meme journal doit rendre deux fois la meme liste, ce qu'aucun dictionnaire
    ne promet.
    """
    return sorted(tally.items(), key=lambda row: (-row[1], row[0]))


def survey(entries) -> Survey:
    """Ce que la fenetre a de remarquable, une fois la VAR passee.

    Un seul parcours des entrees pour tout : les minutes, les competitions,
    les soirees, la nature des buts. Rien ici ne retourne au journal, et rien
    ne demande le reseau - tout etait deja dans le fichier.
    """
    kept, orphans = settle(entries)
    cancelled = sum(1 for entry in entries if not entry.goal)

    minutes = []
    untimed = 0
    added = 0
    leagues = {}
    evenings = {}
    natures = {}
    for entry in kept:
        clock = entry.clock
        if clock is None:
            untimed += 1
        else:
            minutes.append(clock[0])
            if clock[1]:
                added += 1
        leagues[entry.league] = leagues.get(entry.league, 0) + 1
        evening = evening_of(entry)
        evenings[evening] = evenings.get(evening, 0) + 1
        natures[entry.key] = natures.get(entry.key, 0) + 1

    # Le match compte des qu'une ligne le concerne, but confirme ou annulation :
    # une annulation prouve qu'on regardait ce match-la, meme si le score est
    # revenu ou il etait. La soiree entre dans la cle pour qu'un match a cheval
    # sur minuit n'en fasse pas deux, et pour que deux confrontations des memes
    # equipes a des dates differentes n'en fassent pas qu'une.
    matches = {(evening_of(entry),) + entry.match for entry in entries}

    return Survey(
        signalled=len(entries) - cancelled, confirmed=len(kept),
        cancelled=cancelled, orphans=orphans, buckets=_slices(minutes),
        timed=len(minutes), untimed=untimed, added=added,
        leagues=_ranked(leagues), evenings=_ranked(evenings),
        # L'ordre du catalogue, pas celui des comptes : "But" avant "Penalty"
        # avant "But contre son camp" se lit comme une phrase, et ne bouge pas
        # d'une fenetre a l'autre.
        natures=[(key, natures[key]) for key in _GOAL_KEYS if natures.get(key)],
        matches=len(matches))
