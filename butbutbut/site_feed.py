"""Flux HTTP versionne pour les consommateurs locaux de butbutbut.

Le stockage SQLite ne contient que les objets normalises exposes par le
contrat. Les reponses ESPN brutes du backfill vivent a part, dans RawCache.
La route HTTP ne touche jamais au reseau et lit une page a la fois.
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
import os
import queue
import re
import sqlite3
import threading
import time
import unicodedata
import urllib.parse
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from . import __version__, espn, sports

SCHEMA_VERSION = 1
PRODUCER = "butbutbut/{}".format(__version__)
DEFAULT_LIMIT = 100
MAX_LIMIT = 500
DEFAULT_REQUEST_DELAY = 1.5
MAX_RETRIES = 3

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_MINUTE = re.compile(r"^(\d+)(?:\+(\d+))?")
_WINDOWS_PATH = re.compile(r"[A-Za-z]:[\\/][^\s,;]+")
_UNC_PATH = re.compile(r"\\\\[^\s,;]+")
_POSIX_PATH = re.compile(r"(?<![:\w])/(?:[^\s,;]+)")

COUNTRY_CODES = {
    "arg": "AR", "aus": "AU", "bel": "BE", "bra": "BR", "chi": "CL",
    "chn": "CN", "col": "CO", "den": "DK", "eng": "GB", "esp": "ES",
    "fra": "FR", "ger": "DE", "ita": "IT", "jpn": "JP", "mex": "MX",
    "ned": "NL", "nor": "NO", "por": "PT", "sco": "GB", "sui": "CH",
    "swe": "SE", "tur": "TR", "usa": "US",
}


class InvalidQuery(ValueError):
    """Parametres du contrat invalides."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z")


def slugify(value) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _http_url(value):
    text = str(value or "").strip()
    return text if text.lower().startswith(("http://", "https://")) else None


def _safe_error_message(value):
    """Message observable, borne et sans chemin local."""
    text = _WINDOWS_PATH.sub("[chemin local]", str(value or ""))
    text = _UNC_PATH.sub("[chemin local]", text)
    text = _POSIX_PATH.sub("[chemin local]", text).strip()
    return text[:300] or "erreur de source"


def _country_code(league):
    given = str(getattr(league, "country_code", "") or "").upper()
    if len(given) == 2:
        return given
    if len(given) == 3:
        # ESPN emploie parfois FRA/ENG. Le prefixe catalogue est plus fiable
        # pour produire l'ISO alpha-2 attendu par les consommateurs.
        mapped = COUNTRY_CODES.get(given.lower())
        if mapped:
            return mapped
    return COUNTRY_CODES.get(str(league.slug).partition(".")[0].lower())


def normalize_competition(league) -> dict:
    return {
        "external_id": str(league.slug),
        "name": str(league.name),
        "slug": slugify(league.name) or str(league.slug),
        "country_code": _country_code(league),
        # Jamais de repli vers /leaguelogos/<id> : seule la metadonnee recue
        # dans payload.leagues[].logo(s) est autorisee ici.
        "logo_url": _http_url(getattr(league, "logo_url", "")),
    }


def _team(match, side) -> dict:
    names = tuple(getattr(match, side + "_names", ()) or ())
    name = names[0] if names else getattr(match, side)
    return {
        "external_id": str(getattr(match, side + "_id")),
        "name": str(name),
        "short_name": str(getattr(match, side + "_short", "") or name),
        "slug": (str(getattr(match, side + "_slug", "") or "").strip()
                 or slugify(name)),
        "crest_url": _http_url(getattr(match, side + "_logo", "")),
    }


def normalize_status(match) -> str:
    name = "{} {}".format(match.status_name, match.detail).upper()
    if any(word in name for word in ("POSTPON", "DELAYED", "RESCHEDULED",
                                     "SUSPEND")):
        return "postponed"
    if any(word in name for word in ("CANCEL", "ABANDON", "FORFEIT")):
        return "cancelled"
    if match.state == espn.POST:
        return "finished"
    if match.state == espn.LIVE:
        return "live"
    return "scheduled"


def _minute(value):
    found = _MINUTE.match(str(value or "").strip())
    if found is None:
        return None, None
    return int(found.group(1)), (int(found.group(2)) if found.group(2) else None)


def _event(play, sequence) -> dict:
    minute, added = _minute(play.minute)
    return {
        "external_id": str(play.key),
        "kind": str(play.kind_key or "event"),
        "minute": minute,
        "added_time": added,
        "sequence": sequence,
        "team_external_id": str(play.team_id) if play.team_id else None,
        "player_name": str(play.scorer) if play.scorer else None,
        "details": {
            "label": str(play.kind or ""),
            "own_goal": bool(play.own_goal),
            "penalty": bool(play.penalty),
            "shootout": bool(play.shootout),
            "red_card": bool(play.red_card),
        },
    }


def normalize_match(match) -> dict:
    if match.start is None:
        starts_at = None
    else:
        starts_at = match.start.astimezone(timezone.utc).isoformat(
            timespec="seconds").replace("+00:00", "Z")
    plays = list(match.plays) + list(match.red_cards) + list(match.shootout)
    plays.sort(key=lambda play: (getattr(play, "sequence", 0), str(play.key)))
    return {
        "external_id": str(match.id),
        "competition": normalize_competition(match.league),
        "home_team": _team(match, "home"),
        "away_team": _team(match, "away"),
        "starts_at": starts_at,
        "status": normalize_status(match),
        "clock": str(match.clock or match.detail or "") or None,
        "season": str(getattr(match, "season", "") or "") or None,
        "home_score": int(match.home_score),
        "away_score": int(match.away_score),
        "venue": str(getattr(match, "venue", "") or "") or None,
        "events": [_event(play, getattr(play, "sequence", index))
                   for index, play in enumerate(plays)],
        "home_statistics": dict(match.home_stats),
        "away_statistics": dict(match.away_stats),
    }


def _parse_bound(value, upper=False):
    if value in (None, ""):
        return None
    text = str(value).strip()
    try:
        if _DATE.fullmatch(text):
            parsed = datetime.combine(date.fromisoformat(text), datetime.min.time(),
                                      tzinfo=timezone.utc)
            if upper:
                parsed += timedelta(days=1)
        else:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            parsed = parsed.astimezone(timezone.utc)
    except (TypeError, ValueError) as exc:
        raise InvalidQuery("date ISO 8601 invalide : {!r}".format(text)) from exc
    return parsed.isoformat(timespec="seconds").replace("+00:00", "Z")


def _fingerprint(first, last):
    return hashlib.sha256(json.dumps([first, last], separators=(",", ":"))
                          .encode("utf-8")).hexdigest()[:20]


def _cursor_encode(first, last, starts_at, external_id):
    data = {"v": 1, "f": _fingerprint(first, last),
            "after": [starts_at, external_id]}
    body = json.dumps(data, separators=(",", ":"), sort_keys=True).encode("utf-8")
    envelope = hashlib.sha256(body).hexdigest()[:16].encode("ascii") + b"." + body
    return base64.urlsafe_b64encode(envelope).rstrip(b"=").decode("ascii")


def _cursor_decode(value, first, last):
    try:
        raw = str(value).encode("ascii")
        envelope = base64.urlsafe_b64decode(raw + b"=" * (-len(raw) % 4))
        digest, body = envelope.split(b".", 1)
        if digest.decode("ascii") != hashlib.sha256(body).hexdigest()[:16]:
            raise ValueError
        data = json.loads(body.decode("utf-8"))
        after = data["after"]
        if (data.get("v") != 1 or data.get("f") != _fingerprint(first, last)
                or not isinstance(after, list) or len(after) != 2
                or not all(isinstance(item, str) for item in after)):
            raise ValueError
        return after[0], after[1]
    except Exception as exc:
        raise InvalidQuery("cursor invalide ou incompatible avec les filtres") from exc


class Query:
    def __init__(self, params=None):
        params = params or {}

        def one(name):
            value = params.get(name)
            if isinstance(value, (list, tuple)):
                if len(value) > 1:
                    raise InvalidQuery("parametre repete : {}".format(name))
                return value[0] if value else None
            return value

        unknown = set(params) - {"from", "to", "cursor", "limit"}
        if unknown:
            raise InvalidQuery("parametre inconnu : {}".format(sorted(unknown)[0]))
        self.first = _parse_bound(one("from"))
        self.last = _parse_bound(one("to"), upper=True)
        if self.first and self.last and self.first >= self.last:
            raise InvalidQuery("from doit preceder to")
        raw_limit = one("limit")
        try:
            self.limit = DEFAULT_LIMIT if raw_limit in (None, "") else int(raw_limit)
        except (TypeError, ValueError) as exc:
            raise InvalidQuery("limit doit etre un entier") from exc
        if not 1 <= self.limit <= MAX_LIMIT:
            raise InvalidQuery("limit doit etre compris entre 1 et {}".format(MAX_LIMIT))
        raw_cursor = one("cursor")
        self.after = (_cursor_decode(raw_cursor, self.first, self.last)
                      if raw_cursor else None)


class Store:
    """Base normalisee, avec pagination par cle plutot que OFFSET."""

    def __init__(self, path):
        self.path = Path(path)

    def _connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(str(self.path), timeout=5.0)
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA busy_timeout=5000")
        db.executescript("""
            CREATE TABLE IF NOT EXISTS competitions (
                external_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS matches (
                external_id TEXT PRIMARY KEY,
                competition_id TEXT NOT NULL,
                starts_at TEXT NOT NULL,
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS matches_order
                ON matches(starts_at, external_id);
            CREATE TABLE IF NOT EXISTS backfill_periods (
                competition_id TEXT NOT NULL,
                period TEXT NOT NULL,
                status TEXT NOT NULL,
                message TEXT,
                updated_at TEXT NOT NULL,
                PRIMARY KEY(competition_id, period)
            );
        """)
        return db

    def upsert(self, leagues=(), matches=()):
        stamp = utc_now()
        competitions = {item.slug: normalize_competition(item) for item in leagues}
        normalized = []
        for match in matches:
            row = normalize_match(match)
            if row["starts_at"] is None:
                continue
            competitions[row["competition"]["external_id"]] = row["competition"]
            normalized.append(row)
        with closing(self._connect()) as db, db:
            for key, value in competitions.items():
                if value.get("logo_url") is not None:
                    continue
                previous = db.execute(
                    "SELECT payload FROM competitions WHERE external_id=?", (key,)
                ).fetchone()
                if previous:
                    try:
                        value["logo_url"] = json.loads(previous[0]).get("logo_url")
                    except (TypeError, ValueError):
                        pass
            for row in normalized:
                row["competition"] = competitions[
                    row["competition"]["external_id"]]
            db.executemany(
                "INSERT INTO competitions VALUES (?, ?, ?) "
                "ON CONFLICT(external_id) DO UPDATE SET payload=excluded.payload, "
                "updated_at=excluded.updated_at",
                [(key, json.dumps(value, ensure_ascii=False, separators=(",", ":")), stamp)
                 for key, value in competitions.items()])
            db.executemany(
                "INSERT INTO matches VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(external_id) DO UPDATE SET "
                "competition_id=excluded.competition_id, starts_at=excluded.starts_at, "
                "payload=excluded.payload, updated_at=excluded.updated_at",
                [(row["external_id"], row["competition"]["external_id"],
                  row["starts_at"],
                  json.dumps(row, ensure_ascii=False, separators=(",", ":")), stamp)
                 for row in normalized])

    def mark_period(self, competition_id, period, status, message=""):
        with closing(self._connect()) as db, db:
            db.execute(
                "INSERT INTO backfill_periods VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(competition_id, period) DO UPDATE SET "
                "status=excluded.status, message=excluded.message, "
                "updated_at=excluded.updated_at",
                (competition_id, period, status, str(message or ""), utc_now()))

    def period_done(self, competition_id, period):
        with closing(self._connect()) as db, db:
            row = db.execute(
                "SELECT status FROM backfill_periods WHERE competition_id=? AND period=?",
                (competition_id, period)).fetchone()
        return bool(row and row[0] == "ok")

    def feed(self, params=None, followed=(), current_state=None):
        query = Query(params)
        where, values = ["1=1"], []
        followed = list(followed)
        followed_ids = [str(league.slug) for league in followed]
        if followed_ids:
            where.append("competition_id IN ({})".format(
                ",".join("?" for _item in followed_ids)))
            values.extend(followed_ids)
        if query.first:
            where.append("starts_at >= ?")
            values.append(query.first)
        if query.last:
            where.append("starts_at < ?")
            values.append(query.last)
        if query.after:
            where.append("(starts_at > ? OR (starts_at = ? AND external_id > ?))")
            values.extend((query.after[0], query.after[0], query.after[1]))
        sql = ("SELECT starts_at, external_id, payload FROM matches WHERE "
               + " AND ".join(where)
               + " ORDER BY starts_at, external_id LIMIT ?")
        values.append(query.limit + 1)

        with closing(self._connect()) as db, db:
            rows = db.execute(sql, values).fetchall()
            stored_competitions = [json.loads(row[0]) for row in db.execute(
                "SELECT payload FROM competitions ORDER BY external_id")]
            errors = [{"competition_external_id": row[0], "period": row[1],
                       "message": _safe_error_message(row[2]),
                       "observed_at": row[3]}
                      for row in db.execute(
                          "SELECT competition_id, period, message, updated_at "
                          "FROM backfill_periods WHERE status='error' "
                          "ORDER BY updated_at DESC LIMIT 50")]
            if followed_ids:
                errors = [error for error in errors
                          if error["competition_external_id"] in followed_ids]

        page_rows, more = rows[:query.limit], len(rows) > query.limit
        matches = [json.loads(row[2]) for row in page_rows]
        by_id = {item["external_id"]: item for item in stored_competitions}
        if followed_ids:
            by_id = {key: value for key, value in by_id.items()
                     if key in set(followed_ids)}
        for league in followed:
            current = normalize_competition(league)
            old = by_id.get(current["external_id"])
            # Un catalogue sans metadata ne doit pas effacer un logo deja lu.
            if old and current["logo_url"] is None:
                current["logo_url"] = old.get("logo_url")
            by_id[current["external_id"]] = current
        competitions = [by_id[key] for key in sorted(by_id)]
        for match in matches:
            competition_id = match.get("competition", {}).get("external_id")
            if competition_id in by_id:
                match["competition"] = by_id[competition_id]

        next_cursor = None
        if more and page_rows:
            last = page_rows[-1]
            next_cursor = _cursor_encode(query.first, query.last, last[0], last[1])

        raw_state = current_state or {}
        public_state = {
            "available": bool(raw_state),
            "updated_at": raw_state.get("updated_at"),
            "started_at": raw_state.get("started_at"),
            "goals_today": raw_state.get("goals_today", 0),
            "total_matches": raw_state.get("total_matches", 0),
        }
        return {
            "schema_version": SCHEMA_VERSION,
            "producer": PRODUCER,
            "generated_at": utc_now(),
            "competitions": competitions,
            "matches": matches,
            "next_cursor": next_cursor,
            "state": public_state,
            "errors": errors,
        }


class AsyncWriter:
    """Ecrit hors de la boucle de surveillance et regroupe les instantanes."""

    def __init__(self, path, leagues=(), on_log=None):
        self.store = Store(path)
        self.leagues = tuple(leagues)
        self.on_log = on_log or (lambda _message: None)
        self.queue = queue.Queue(maxsize=8)
        self.thread = threading.Thread(target=self._run, name="site-feed-writer",
                                       daemon=True)
        self.thread.start()

    def submit(self, matches):
        item = list(matches)
        try:
            self.queue.put_nowait(item)
        except queue.Full:
            # Le prochain releve porte un etat complet : jeter l'ancien est
            # plus juste que bloquer le watcher derriere le disque.
            try:
                self.queue.get_nowait()
                self.queue.task_done()
                self.queue.put_nowait(item)
            except queue.Empty:
                pass

    def _run(self):
        while True:
            item = self.queue.get()
            try:
                if item is None:
                    return
                self.store.upsert(leagues=self.leagues, matches=item)
            except Exception as exc:
                self.on_log("site-feed : ecriture impossible ({})".format(exc))
            finally:
                self.queue.task_done()

    def close(self, timeout=2.0):
        try:
            self.queue.put_nowait(None)
        except queue.Full:
            try:
                self.queue.get_nowait()
                self.queue.task_done()
                self.queue.put_nowait(None)
            except queue.Empty:
                return
        self.thread.join(timeout)


class RawCache:
    def __init__(self, root):
        self.root = Path(root)

    def path_for(self, league, period):
        sport = getattr(league, "sport", None) or sports.DEFAULT
        safe_slug = re.sub(r"[^a-zA-Z0-9_.-]+", "_", str(league.slug))
        return self.root / sport.code / safe_slug / (str(period) + ".json.gz")

    def read(self, league, period):
        path = self.path_for(league, period)
        try:
            with gzip.open(str(path), "rt", encoding="utf-8") as handle:
                payload = json.load(handle)
            return payload if isinstance(payload, dict) else None
        except Exception:
            return None

    def write(self, league, period, payload):
        path = self.path_for(league, period)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name("{}.{}.tmp".format(path.name, os.getpid()))
        try:
            with gzip.open(str(tmp), "wt", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
            os.replace(str(tmp), str(path))
        finally:
            try:
                tmp.unlink()
            except OSError:
                pass


def _months(first, last):
    cursor = first.replace(day=1)
    final = last.replace(day=1)
    while cursor <= final:
        yield cursor.strftime("%Y%m")
        cursor = ((cursor.replace(day=28) + timedelta(days=4)).replace(day=1))


def _period_checkpoint(period, first, last):
    month_start = date(int(period[:4]), int(period[4:]), 1)
    next_month = ((month_start.replace(day=28) + timedelta(days=4)).replace(day=1))
    month_last = next_month - timedelta(days=1)
    scope_first, scope_last = max(first, month_start), min(last, month_last)
    if scope_first == month_start and scope_last == month_last:
        return period
    return "{}:{}:{}".format(period, scope_first.isoformat(), scope_last.isoformat())


def season_range(value):
    text = str(value or "").strip()
    found = re.fullmatch(r"(\d{4})(?:[-/](\d{2}|\d{4}))?", text)
    if found is None:
        raise InvalidQuery("saison invalide : {!r}".format(text))
    first_year = int(found.group(1))
    if found.group(2) is None:
        return date(first_year, 1, 1), date(first_year, 12, 31)
    raw_last = found.group(2)
    last_year = int(raw_last) if len(raw_last) == 4 else (first_year // 100 * 100 + int(raw_last))
    if last_year != first_year + 1:
        raise InvalidQuery("une saison doit couvrir deux annees consecutives")
    return date(first_year, 7, 1), date(last_year, 6, 30)


class Backfill:
    """Backfill mensuel, cache, reprenable et isole par competition."""

    def __init__(self, store_path, raw_root, opener=None, request_delay=DEFAULT_REQUEST_DELAY,
                 timeout=espn.DEFAULT_TIMEOUT, sleeper=time.sleep, on_progress=None):
        self.store = Store(store_path)
        self.cache = RawCache(raw_root)
        self.opener = opener
        self.request_delay = max(0.0, float(request_delay))
        self.timeout = timeout
        self.sleeper = sleeper
        self.on_progress = on_progress or (lambda _message: None)

    def _fetch(self, league, period):
        cached = self.cache.read(league, period)
        if cached is not None:
            return cached, True
        sport = getattr(league, "sport", None) or sports.DEFAULT
        url = espn.SCOREBOARD_URL.format(sport=sport.code, slug=league.slug)
        url += "?" + urllib.parse.urlencode({"dates": period, "limit": 1000})
        last = None
        for attempt in range(MAX_RETRIES):
            try:
                if self.opener is None:
                    raw = espn.download(url, self.timeout, label=league.ref)
                else:
                    raw = self.opener(url, self.timeout)
                if isinstance(raw, bytes):
                    raw = espn.uncompress(raw, league.ref).decode("utf-8", "replace")
                payload = json.loads(raw) if isinstance(raw, str) else raw
                if not isinstance(payload, dict):
                    raise espn.SourceError("reponse inattendue pour " + league.ref)
                self.cache.write(league, period, payload)
                return payload, False
            except Exception as exc:
                last = exc
                if attempt + 1 < MAX_RETRIES:
                    self.sleeper(min(4.0, 2.0 ** attempt))
        if isinstance(last, espn.SourceError):
            raise last
        raise espn.SourceError(type(last).__name__)

    def run(self, leagues, first, last, dry_run=False):
        first, last = first if isinstance(first, date) else date.fromisoformat(first), \
            last if isinstance(last, date) else date.fromisoformat(last)
        if first > last:
            raise InvalidQuery("la borne de debut doit preceder la borne de fin")
        periods = list(_months(first, last))
        leagues = list(leagues)
        result = {"planned": len(periods) * len(leagues), "completed": 0,
                  "cached": 0, "skipped": 0, "errors": []}
        if dry_run:
            for league in leagues:
                for period in periods:
                    self.on_progress("{} {} (dry-run)".format(league.ref, period))
            return result

        network_request = False
        for league in leagues:
            for period in periods:
                checkpoint = _period_checkpoint(period, first, last)
                if self.store.period_done(league.slug, checkpoint):
                    result["skipped"] += 1
                    continue
                if network_request and self.request_delay:
                    self.sleeper(self.request_delay)
                try:
                    payload, cached = self._fetch(league, period)
                    network_request = network_request or not cached
                    parsed = espn.parse(payload, league)
                    parsed = [match for match in parsed
                              if match.start is not None
                              and first <= match.start.date() <= last]
                    self.store.upsert([league], parsed)
                    self.store.mark_period(league.slug, checkpoint, "ok")
                    result["completed"] += 1
                    result["cached"] += int(cached)
                    self.on_progress("{} {} : {} match(s){}".format(
                        league.ref, period, len(parsed), " (cache)" if cached else ""))
                except Exception as exc:
                    message = _safe_error_message(
                        exc if isinstance(exc, espn.SourceError)
                        else type(exc).__name__)
                    self.store.mark_period(league.slug, checkpoint, "error", message)
                    error = {"competition_external_id": league.slug,
                             "period": checkpoint, "message": message}
                    result["errors"].append(error)
                    self.on_progress("{} {} : erreur : {}".format(
                        league.ref, period, message))
        return result
