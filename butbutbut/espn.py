"""Source des scores : le tableau de bord public d'ESPN.

    https://site.api.espn.com/apis/site/v2/sports/soccer/<slug>/scoreboard

Pourquoi celle-la : pas de cle d'API, pas d'inscription, elle couvre les cinq
championnats, elle est mise a jour en direct et elle donne meme le buteur et la
minute. C'est une API publique mais non documentee : tout est lu de facon
defensive (une cle qui disparait ne doit pas tuer le daemon).

Rien d'autre que la stdlib : urllib + json.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime, timezone

SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/scoreboard"

USER_AGENT = "butbutbut/1.0 (+https://github.com/boubou666/butbutbut)"
DEFAULT_TIMEOUT = 8.0

# Etats renvoyes par ESPN.
PRE, LIVE, POST = "pre", "in", "post"

# Au-dela, on prefere le nom court : "Borussia Monchengladbach" tient mal.
NAME_LIMIT = 20


class SourceError(RuntimeError):
    """Le tableau de bord n'a pas pu etre lu (reseau, HTTP, JSON casse)."""


# ---------------------------------------------------------------- modele -----

class Play:
    """Une action marquante d'un match (ici : un but)."""

    __slots__ = ("key", "team_id", "minute", "kind", "scorer", "own_goal",
                 "penalty", "shootout")

    def __init__(self, key, team_id, minute, kind, scorer, own_goal, penalty, shootout):
        self.key = key
        self.team_id = team_id
        self.minute = minute          # 35' ou vide
        self.kind = kind              # Goal, Own Goal, Penalty - Scored...
        self.scorer = scorer          # C. Arcus, ou vide
        self.own_goal = own_goal
        self.penalty = penalty
        self.shootout = shootout

    def prefix(self) -> str:
        """La nature du but, sans le buteur : But, Penalty, But contre son camp."""
        if self.own_goal:
            return "But contre son camp"
        if self.penalty:
            return "Penalty"
        return "But"

    def summary(self) -> str:
        """Une ligne en francais : But de C. Arcus (35')."""
        base = self.prefix()
        if self.scorer:
            base += " de " + self.scorer
        if self.minute:
            base += " (" + self.minute + ")"
        return base

    def __repr__(self):
        return "<Play {} {} {}>".format(self.minute, self.kind, self.scorer)


class Match:
    """Un match tel que le tableau de bord le decrit a l'instant T."""

    __slots__ = ("id", "league", "home", "away", "home_id", "away_id",
                 "home_score", "away_score", "state", "detail", "clock",
                 "start", "plays")

    def __init__(self, id, league, home, away, home_id, away_id, home_score,
                 away_score, state, detail, clock, start, plays):
        self.id = id
        self.league = league
        self.home = home
        self.away = away
        self.home_id = home_id
        self.away_id = away_id
        self.home_score = home_score
        self.away_score = away_score
        self.state = state
        self.detail = detail          # FT, 45+2', Sun 6 Sep at 17:00...
        self.clock = clock            # la minute, quand le match est en cours
        self.start = start            # datetime UTC, ou None
        self.plays = plays            # list[Play]

    @property
    def live(self) -> bool:
        return self.state == LIVE

    @property
    def finished(self) -> bool:
        return self.state == POST

    def score_line(self) -> str:
        return "{} {} - {} {}".format(self.home, self.home_score,
                                      self.away_score, self.away)

    def seconds_until_kickoff(self, now=None) -> float | None:
        if self.start is None:
            return None
        now = now or datetime.now(timezone.utc)
        return (self.start - now).total_seconds()

    def plays_for(self, team_id) -> list:
        return [play for play in self.plays if play.team_id == team_id]

    def __repr__(self):
        return "<Match {} {} [{}]>".format(self.league.slug, self.score_line(), self.state)


# ---------------------------------------------------------------- reseau -----

def fetch(slug: str, timeout: float = DEFAULT_TIMEOUT, opener=None) -> dict:
    """Recupere le tableau de bord brut d'un championnat.

    `opener` sert aux tests : n'importe quel callable(url, timeout) -> bytes.
    """
    url = SCOREBOARD_URL.format(slug=slug)

    if opener is not None:
        try:
            raw = opener(url, timeout)
        except Exception as exc:
            raise SourceError(str(exc)) from exc
    else:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
                "Accept-Language": "fr,en;q=0.8",
                "Cache-Control": "no-cache",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            raise SourceError("HTTP {} sur {}".format(exc.code, slug)) from exc
        except Exception as exc:      # URLError, socket.timeout, ssl...
            raise SourceError("{} sur {} : {}".format(type(exc).__name__, slug, exc)) from exc

    try:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", "replace")
        payload = json.loads(raw)
    except Exception as exc:
        raise SourceError("reponse illisible pour {} : {}".format(slug, exc)) from exc

    if not isinstance(payload, dict):
        raise SourceError("reponse inattendue pour " + slug)
    return payload


# ---------------------------------------------------------------- parsing ----

def _int(value, default=0) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _team_name(competitor) -> str:
    """Nom lisible : le nom complet, ou le nom court s'il est trop long."""
    team = competitor.get("team") or {}
    full = (team.get("displayName") or "").strip()
    short = (team.get("shortDisplayName") or "").strip()
    if full and len(full) <= NAME_LIMIT:
        return full
    return short or full or (team.get("abbreviation") or "?")


def _parse_date(value) -> datetime | None:
    """Date ISO d'ESPN, souvent 2026-09-06T18:45Z. Renvoie un datetime UTC."""
    if not value:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    parsers = (
        lambda t: datetime.fromisoformat(t),
        lambda t: datetime.strptime(t, "%Y-%m-%dT%H:%M%z"),
        lambda t: datetime.strptime(t, "%Y-%m-%dT%H:%M:%S%z"),
    )
    for parser in parsers:
        try:
            parsed = parser(text)
        except Exception:
            continue
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    return None


def _parse_plays(competition) -> list:
    """Les buts inscrits dans le match, dans l'ordre ou ESPN les donne."""
    plays = []
    for index, detail in enumerate(competition.get("details") or []):
        if not isinstance(detail, dict) or not detail.get("scoringPlay"):
            continue

        kind = ((detail.get("type") or {}).get("text") or "Goal").strip()
        clock = (detail.get("clock") or {}).get("displayValue") or ""
        team_id = str(((detail.get("team") or {}).get("id") or "")).strip()

        athletes = detail.get("athletesInvolved") or []
        scorer = ""
        athlete_id = ""
        if athletes and isinstance(athletes[0], dict):
            scorer = (athletes[0].get("shortName")
                      or athletes[0].get("displayName") or "").strip()
            athlete_id = str(athletes[0].get("id") or "")

        # Cle stable : le meme but relu dix fois garde la meme identite.
        key = "|".join((team_id, str(clock), kind, athlete_id, str(index)))

        plays.append(Play(
            key=key,
            team_id=team_id,
            minute=str(clock).strip(),
            kind=kind,
            scorer=scorer,
            own_goal=bool(detail.get("ownGoal")),
            penalty=bool(detail.get("penaltyKick")),
            shootout=bool(detail.get("shootout")),
        ))
    return plays


def parse(payload: dict, league) -> list:
    """Transforme un tableau de bord ESPN en liste de Match.

    Tout evenement mal forme est ignore plutot que de faire echouer le lot.
    """
    # Une competition ouverte a la volee (un code ESPN passe a --leagues) prend
    # ici le nom que la source annonce.
    if getattr(league, "provisional", False):
        header = (payload.get("leagues") or [{}])[0]
        if isinstance(header, dict):
            league.adopt_name(header.get("name"), header.get("abbreviation"))

    matches = []
    for event in payload.get("events") or []:
        if not isinstance(event, dict):
            continue
        competitions = event.get("competitions") or []
        if not competitions or not isinstance(competitions[0], dict):
            continue
        competition = competitions[0]

        home = away = None
        for competitor in competition.get("competitors") or []:
            if not isinstance(competitor, dict):
                continue
            if competitor.get("homeAway") == "home":
                home = competitor
            elif competitor.get("homeAway") == "away":
                away = competitor
        if home is None or away is None:
            continue

        status = competition.get("status") or event.get("status") or {}
        status_type = status.get("type") or {}
        state = (status_type.get("state") or "").strip().lower() or PRE
        detail = (status_type.get("shortDetail")
                  or status_type.get("detail")
                  or status_type.get("description") or "").strip()
        clock = str(status.get("displayClock") or "").strip()

        match_id = str(event.get("id") or competition.get("id") or "").strip()
        if not match_id:
            continue

        matches.append(Match(
            id=match_id,
            league=league,
            home=_team_name(home),
            away=_team_name(away),
            home_id=str((home.get("team") or {}).get("id") or "H"),
            away_id=str((away.get("team") or {}).get("id") or "A"),
            home_score=_int(home.get("score")),
            away_score=_int(away.get("score")),
            state=state,
            detail=detail,
            clock=clock,
            start=_parse_date(competition.get("date") or event.get("date")),
            plays=_parse_plays(competition),
        ))
    return matches


def scoreboard(league, timeout: float = DEFAULT_TIMEOUT, opener=None) -> list:
    """fetch + parse, pour un championnat."""
    return parse(fetch(league.slug, timeout=timeout, opener=opener), league)
