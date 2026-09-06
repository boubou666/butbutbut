"""La surveillance : comparer deux photos du tableau de bord, en tirer les buts.

Principe : a chaque passage on relit le tableau de bord d'un championnat et on
compare les scores a ceux du passage precedent. Un score qui monte = un but.
La liste des actions d'ESPN sert ensuite a habiller la notification (buteur,
minute, csc, penalty) ; elle arrive parfois avec quelques secondes de retard,
c'est pour ca qu'elle ne sert jamais a *detecter* le but, seulement a le
decrire.

Deux garde-fous :
  - le premier passage sur un championnat ne declenche rien : il photographie
    l'existant, sinon lancer le daemon en pleine journee de championnat ferait
    hurler tous les buts deja marques ;
  - un score qui *descend* (but refuse par la VAR) est signale sans son.

La cadence s'adapte : rapide quand un match est en cours, lente quand il n'y a
rien a regarder. Chaque championnat a son propre rythme, donc on n'interroge
pas la Bundesliga toutes les 25 s un mardi soir de Ligue 1.
"""

from __future__ import annotations

import time

from . import espn

DEFAULT_INTERVAL = 25.0        # un match est en cours
DEFAULT_IDLE_INTERVAL = 300.0  # rien en cours dans ce championnat
KICKOFF_INTERVAL = 60.0        # coup d'envoi imminent
KICKOFF_WINDOW = 1200.0        # "imminent" = dans moins de 20 min
MAX_BACKOFF = 300.0            # plafond d'attente apres une erreur reseau
SPREAD = 1.5                   # decalage entre deux competitions, en secondes
FORGET_AFTER = 12 * 3600.0     # on oublie un match vu il y a plus de 12 h

GOAL = "goal"
CANCELLED = "cancelled"


class Event:
    """Ce qui vient de se passer : un but, ou un but retire par la VAR."""

    __slots__ = ("kind", "match", "side", "team", "opponent", "home_score",
                 "away_score", "delta", "play", "at")

    def __init__(self, kind, match, side, team, opponent, home_score,
                 away_score, delta, play, at=None):
        self.kind = kind
        self.match = match
        self.side = side              # "home" ou "away"
        self.team = team              # equipe concernee
        self.opponent = opponent
        self.home_score = home_score
        self.away_score = away_score
        self.delta = delta            # +1, +2 (doublon rattrape), -1...
        self.play = play              # espn.Play ou None
        self.at = at or time.time()

    @property
    def league(self):
        return self.match.league

    @property
    def goal(self) -> bool:
        return self.kind == GOAL

    @property
    def title(self) -> str:
        if self.kind == CANCELLED:
            return "BUT ANNULE"
        if self.play is not None and self.play.own_goal:
            return "BUT CONTRE SON CAMP"
        if self.play is not None and self.play.penalty:
            return "BUT SUR PENALTY"
        return "BUT !"

    @property
    def minute(self) -> str:
        """La minute du but, sinon l'horloge du match."""
        if self.play is not None and self.play.minute:
            return self.play.minute
        return self.match.clock or self.match.detail or ""

    @property
    def score_line(self) -> str:
        return "{} {} - {} {}".format(self.match.home, self.home_score,
                                      self.away_score, self.match.away)

    def detail_parts(self) -> list:
        """La troisieme ligne, en morceaux : (texte, mis_en_valeur).

        Le nom du buteur est le seul morceau mis en valeur : c'est l'info qu'on
        veut lire en premier apres le score.
        """
        if self.kind == CANCELLED:
            return [("Score corrige", False)]

        play = self.play
        if play is None:
            minute = self.minute
            return [("Minute " + minute, False)] if minute else []

        # La minute n'est pas repetee ici : l'en-tete de la carte la porte deja.
        if play.scorer:
            return [(play.prefix() + " de ", False), (play.scorer, True)]
        return [(play.prefix(), False)]

    def detail_line(self) -> str:
        """La meme ligne, d'un bloc : journal, tests, mode --no-overlay."""
        return "".join(text for text, _ in self.detail_parts())

    def log_line(self) -> str:
        head = "BUT" if self.goal else "ANNULE"
        parts = ["{} [{}] {}".format(head, self.league.name, self.score_line)]
        if self.team:
            parts.append("pour " + self.team)
        detail = self.detail_line()
        if detail:
            parts.append("- " + detail)
        if self.minute:
            parts.append("(" + self.minute + ")")
        return " ".join(parts)

    def __repr__(self):
        return "<Event {} {}>".format(self.kind, self.score_line)


class _Snapshot:
    """Ce qu'on retient d'un match entre deux passages."""

    __slots__ = ("home_score", "away_score", "seen_plays", "last_seen")

    def __init__(self, home_score, away_score, seen_plays, last_seen):
        self.home_score = home_score
        self.away_score = away_score
        self.seen_plays = seen_plays
        self.last_seen = last_seen


class Watcher:
    """Interroge les championnats a leur rythme et renvoie les buts."""

    def __init__(self, leagues, interval=DEFAULT_INTERVAL,
                 idle_interval=DEFAULT_IDLE_INTERVAL,
                 kickoff_window=KICKOFF_WINDOW, timeout=espn.DEFAULT_TIMEOUT,
                 opener=None, on_log=None):
        self.leagues = list(leagues)
        self.interval = max(5.0, float(interval))
        self.idle_interval = max(self.interval, float(idle_interval))
        self.kickoff_window = float(kickoff_window)
        self.timeout = float(timeout)
        self.opener = opener
        self.on_log = on_log or (lambda message: None)

        self.matches = {}          # slug -> list[Match] du dernier passage
        self._snapshots = {}       # match_id -> _Snapshot
        self._due = {league.slug: 0.0 for league in self.leagues}
        self._failures = {league.slug: 0 for league in self.leagues}
        self._primed = set()       # championnats deja photographies une fois

    # ------------------------------------------------------------ cadence ---

    def due_leagues(self, now=None) -> list:
        now = now if now is not None else time.monotonic()
        return [l for l in self.leagues if self._due.get(l.slug, 0.0) <= now]

    def next_delay(self, now=None) -> float:
        """Secondes a attendre avant le prochain passage, bornees."""
        now = now if now is not None else time.monotonic()
        if not self.leagues:
            return self.idle_interval
        soonest = min(self._due.get(l.slug, 0.0) for l in self.leagues)
        return max(1.0, min(60.0, soonest - now))

    def _cadence(self, matches) -> float:
        """Rythme de ce championnat, d'apres ce qu'il a au programme."""
        if any(match.live for match in matches):
            return self.interval

        soonest = None
        for match in matches:
            remaining = match.seconds_until_kickoff()
            if remaining is None or remaining < -7200:
                continue
            if soonest is None or remaining < soonest:
                soonest = remaining

        if soonest is not None and soonest <= self.kickoff_window:
            return min(KICKOFF_INTERVAL, self.idle_interval)
        return self.idle_interval

    def live_matches(self) -> list:
        found = []
        for league in self.leagues:
            found.extend(m for m in self.matches.get(league.slug, []) if m.live)
        return found

    def all_matches(self) -> list:
        found = []
        for league in self.leagues:
            found.extend(self.matches.get(league.slug, []))
        return found

    # -------------------------------------------------------------- lecture -

    def refresh(self, league, now=None) -> list:
        """Relit un championnat et renvoie les evenements qui en decoulent."""
        now = now if now is not None else time.monotonic()
        try:
            matches = espn.scoreboard(league, timeout=self.timeout, opener=self.opener)
        except espn.SourceError as exc:
            self._failures[league.slug] = self._failures.get(league.slug, 0) + 1
            failures = self._failures[league.slug]
            wait = min(MAX_BACKOFF, self.interval * (2 ** min(failures, 4)))
            self._due[league.slug] = now + wait
            if failures in (1, 5) or failures % 20 == 0:
                self.on_log("{} injoignable ({}) - nouvel essai dans {:.0f}s"
                            .format(league.name, exc, wait))
            return []

        if self._failures.get(league.slug):
            self.on_log(league.name + " de nouveau joignable")
        self._failures[league.slug] = 0

        self.matches[league.slug] = matches
        self._due[league.slug] = now + self._cadence(matches)

        primed = league.slug in self._primed
        self._primed.add(league.slug)

        events = []
        for match in matches:
            events.extend(self._diff(match, alert=primed))
        self._forget_old()
        return events

    def tick(self, now=None) -> list:
        """Passe sur tous les championnats dont l'heure est venue."""
        now = now if now is not None else time.monotonic()
        events = []
        for league in self.due_leagues(now):
            events.extend(self.refresh(league, now=now))
        return events

    def prime(self, pause: float = 0.2) -> None:
        """Premier passage sur tout : photographie l'existant, sans alerte.

        Les appels sont espaces, et les prochains releves decales les uns des
        autres : avec tout le catalogue, trente-six requetes tirees en rafale
        finissent par se faire jeter par la source.
        """
        total = len(self.leagues)
        for index, league in enumerate(self.leagues):
            self.refresh(league)
            self._due[league.slug] += index * SPREAD
            if pause and index + 1 < total:
                time.sleep(pause)

    # --------------------------------------------------------------- diff ---

    def _diff(self, match, alert=True) -> list:
        """Compare un match a sa photo precedente."""
        stamp = time.time()
        previous = self._snapshots.get(match.id)
        keys = {play.key for play in match.plays}

        if previous is None:
            self._snapshots[match.id] = _Snapshot(
                match.home_score, match.away_score, keys, stamp)
            return []

        events = []
        pairs = (
            ("home", match.home_id, match.home, match.away,
             previous.home_score, match.home_score),
            ("away", match.away_id, match.away, match.home,
             previous.away_score, match.away_score),
        )

        for side, team_id, team, opponent, before, after in pairs:
            if after == before:
                continue
            delta = after - before
            play = self._pick_play(match, team_id, previous.seen_plays) if delta > 0 else None
            events.append(Event(
                kind=GOAL if delta > 0 else CANCELLED,
                match=match,
                side=side,
                team=team,
                opponent=opponent,
                home_score=match.home_score,
                away_score=match.away_score,
                delta=delta,
                play=play,
            ))

        previous.home_score = match.home_score
        previous.away_score = match.away_score
        previous.seen_plays = keys
        previous.last_seen = stamp

        return events if alert else []

    @staticmethod
    def _pick_play(match, team_id, seen_keys):
        """La derniere action de cette equipe qu'on n'avait pas encore vue."""
        fresh = [p for p in match.plays_for(team_id) if p.key not in seen_keys]
        if fresh:
            return fresh[-1]
        known = match.plays_for(team_id)
        return known[-1] if known else None

    def _forget_old(self) -> None:
        limit = time.time() - FORGET_AFTER
        stale = [key for key, snap in self._snapshots.items() if snap.last_seen < limit]
        for key in stale:
            del self._snapshots[key]
