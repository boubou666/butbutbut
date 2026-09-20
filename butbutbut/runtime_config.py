"""Configuration de surveillance fournie a chaud par le site butbutbut.

Ce module ne connait rien de l'implementation du site.  Il ne consomme que le
contrat HTTP versionne ``/internal/api/v1/daemon/runtime-config`` et rend au
watcher une table ``id de match -> id de competition``.
"""

from __future__ import annotations

import json
import math
import time
import urllib.error
import urllib.request
from datetime import datetime

from . import __version__


PATH = "/internal/api/v1/daemon/runtime-config"
SUPPORTED_MAJOR = 1
DEFAULT_TIMEOUT = 8.0
DEFAULT_MAX_STALE = 300.0
MAX_BACKOFF = 300.0
MIN_POLL = 1.0
USER_AGENT = "butbutbut/{} (+https://github.com/boubou666/butbutbut)".format(
    __version__)


class InvalidConfig(ValueError):
    """La reponse existe, mais ne respecte pas le contrat v1."""


class IncompatibleSchema(InvalidConfig):
    """La version majeure n'est pas comprise par ce daemon."""


def _number(value, name, minimum=0.0) -> float:
    if isinstance(value, bool):
        raise InvalidConfig("{} doit etre un nombre".format(name))
    try:
        answer = float(value)
    except (TypeError, ValueError):
        raise InvalidConfig("{} doit etre un nombre".format(name))
    if not math.isfinite(answer) or answer < minimum:
        raise InvalidConfig("{} doit etre superieur ou egal a {}".format(
            name, minimum))
    return answer


def parse(payload) -> dict:
    """Valide une reponse v1 et normalise les seuls champs utiles au daemon."""
    if not isinstance(payload, dict):
        raise InvalidConfig("la reponse doit etre un objet JSON")

    version = str(payload.get("schema_version") or "").strip()
    try:
        major = int(version.split(".", 1)[0])
    except (TypeError, ValueError):
        raise InvalidConfig("schema_version absent ou illisible")
    if major != SUPPORTED_MAJOR:
        raise IncompatibleSchema(
            "schema {} incompatible (version majeure acceptee : {})".format(
                version, SUPPORTED_MAJOR))

    revision = payload.get("revision")
    if not isinstance(revision, str) or not revision.strip():
        raise InvalidConfig("revision absente ou vide")
    if payload.get("catalog_scope") != "all-football":
        raise InvalidConfig("catalog_scope inconnu : {!r}".format(
            payload.get("catalog_scope")))

    poll_after = _number(payload.get("poll_after_seconds"),
                         "poll_after_seconds", MIN_POLL)
    grace = _number(payload.get("grace_period_seconds"),
                    "grace_period_seconds")
    raw_matches = payload.get("live_matches")
    if not isinstance(raw_matches, list):
        raise InvalidConfig("live_matches doit etre une liste")

    # L'id externe est la cle : selected_by ne change jamais le nombre de
    # watchers. En cas de doublon incoherent, la premiere occurrence gagne ;
    # elle suffit pour ne faire qu'une surveillance et ne suppose rien du site.
    matches = {}
    for index, item in enumerate(raw_matches):
        if not isinstance(item, dict):
            raise InvalidConfig("live_matches[{}] doit etre un objet".format(index))
        match_id = str(item.get("external_id") or "").strip()
        competition = str(item.get("competition_external_id") or "").strip()
        if not match_id or not competition:
            raise InvalidConfig(
                "live_matches[{}] requiert external_id et "
                "competition_external_id".format(index))
        starts_at = item.get("starts_at")
        if not isinstance(starts_at, str) or not starts_at.strip():
            raise InvalidConfig(
                "live_matches[{}].starts_at absent ou illisible".format(index))
        try:
            moment = datetime.fromisoformat(
                starts_at.strip().replace("Z", "+00:00"))
        except ValueError:
            raise InvalidConfig(
                "live_matches[{}].starts_at absent ou illisible".format(index))
        if moment.tzinfo is None:
            raise InvalidConfig(
                "live_matches[{}].starts_at doit porter un fuseau".format(index))
        selected_by = item.get("selected_by")
        if (isinstance(selected_by, bool) or not isinstance(selected_by, int)
                or selected_by < 0):
            raise InvalidConfig(
                "live_matches[{}].selected_by doit etre un entier positif"
                .format(index))
        matches.setdefault(match_id, competition)

    return {
        "revision": revision.strip(),
        "poll_after": poll_after,
        "grace": grace,
        "matches": matches,
    }


class Client:
    """Client cadence, tolerant aux pannes, avec retrait differe.

    ``refresh()`` rend la selection seulement lorsqu'elle a effectivement
    change. Une revision identique ne reconstruit donc rien dans le watcher.
    """

    def __init__(self, base_url, api_key, opener=None, timeout=DEFAULT_TIMEOUT,
                 max_stale=DEFAULT_MAX_STALE, clock=None, on_log=None):
        self.url = str(base_url or "").rstrip("/") + PATH
        self._api_key = str(api_key or "")
        self.opener = opener or urllib.request.urlopen
        self.timeout = float(timeout)
        self.max_stale = max(0.0, float(max_stale))
        self.clock = clock or time.monotonic
        self.on_log = on_log or (lambda message: None)

        self.revision = None
        self.poll_after = 5.0
        self.grace = 0.0
        self._wanted = {}
        self._active = {}
        self._retire_at = {}
        self._last_valid = None
        self._next_poll = 0.0
        self._failures = 0
        self._expired = False

    @property
    def active_matches(self) -> dict:
        return dict(self._active)

    def _request(self):
        request = urllib.request.Request(
            self.url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
                "X-ButButBut-API-Key": self._api_key,
            },
        )
        try:
            response = self.opener(request, timeout=self.timeout)
            if hasattr(response, "__enter__"):
                with response as opened:
                    body = opened.read()
            else:
                body = response.read()
            return json.loads(body.decode("utf-8"))
        except IncompatibleSchema:
            raise
        except Exception as exc:
            # La requete (et donc son en-tete secret) n'entre jamais dans le
            # message. On ne garde que la classe de panne et, pour HTTP, le
            # code public.
            if isinstance(exc, urllib.error.HTTPError):
                detail = "HTTP {}".format(exc.code)
            elif isinstance(exc, (json.JSONDecodeError, UnicodeError)):
                detail = "reponse JSON illisible"
            else:
                detail = type(exc).__name__
            raise InvalidConfig(detail) from exc

    def _expire_grace(self, now) -> bool:
        expired = [match_id for match_id, deadline in self._retire_at.items()
                   if deadline <= now]
        for match_id in expired:
            self._retire_at.pop(match_id, None)
            self._active.pop(match_id, None)
        return bool(expired)

    def _expire_stale(self, now) -> bool:
        if self._last_valid is None or self._expired:
            return False
        if now < self._last_valid + self.max_stale:
            return False
        changed = bool(self._active)
        self._wanted.clear()
        self._active.clear()
        self._retire_at.clear()
        self._expired = True
        self.on_log("configuration du site expiree : surveillance live arretee")
        return changed

    def _failure(self, now, message) -> None:
        self._failures += 1
        wait = min(MAX_BACKOFF,
                   max(MIN_POLL, self.poll_after) *
                   (2 ** min(self._failures - 1, 6)))
        self._next_poll = now + wait
        if self._failures in (1, 5) or self._failures % 20 == 0:
            safe = (str(message).replace(self._api_key, "***")
                    if self._api_key else str(message))
            self.on_log("configuration du site indisponible ({}) - nouvel "
                        "essai dans {:.0f}s".format(safe, wait))

    def refresh(self, now=None, force=False):
        """Interroge le site si necessaire ; rend ``dict`` si la cible change.

        Le retour ``None`` signifie que le watcher ne doit rien recalculer.
        Une panne conserve la derniere selection jusqu'a ``max_stale`` ; a
        l'expiration elle devient vide, jamais la selection autonome.
        """
        now = self.clock() if now is None else float(now)
        changed = self._expire_grace(now)
        changed = self._expire_stale(now) or changed
        if not force and now < self._next_poll:
            return self.active_matches if changed else None

        try:
            raw = self._request()
            update = parse(raw)
        except IncompatibleSchema as exc:
            self._failure(now, str(exc))
            return self.active_matches if changed else None
        except InvalidConfig as exc:
            self._failure(now, str(exc))
            return self.active_matches if changed else None

        was_failing = bool(self._failures)
        was_expired = self._expired
        self._failures = 0
        self._last_valid = now
        self._expired = False
        self._next_poll = now + self.poll_after
        if update["revision"] == self.revision and not was_expired:
            if was_failing:
                self.on_log("configuration du site de nouveau joignable")
            return self.active_matches if changed else None

        old_wanted = self._wanted
        wanted = update["matches"]
        grace = update["grace"]

        # Ajouts et retours pendant la grace : actifs immediatement.
        for match_id, competition in wanted.items():
            self._active[match_id] = competition
            self._retire_at.pop(match_id, None)
        # Retraits : l'ancienne competition reste la bonne jusqu'a l'echeance.
        for match_id in old_wanted.keys() - wanted.keys():
            self._retire_at[match_id] = now + grace

        self._wanted = dict(wanted)
        self.revision = update["revision"]
        self.poll_after = update["poll_after"]
        self.grace = grace
        self._next_poll = now + self.poll_after
        changed = self._expire_grace(now) or changed
        if was_failing:
            self.on_log("configuration du site de nouveau joignable")
        # Une nouvelle revision est un changement de configuration meme si sa
        # liste dedupliquee est identique : le watcher comparera sans dommage.
        return self.active_matches

    def next_delay(self, now=None) -> float:
        """Prochaine echeance HTTP, de grace ou d'expiration, bornee a 60 s."""
        now = self.clock() if now is None else float(now)
        deadlines = [self._next_poll]
        deadlines.extend(self._retire_at.values())
        if self._last_valid is not None and not self._expired:
            deadlines.append(self._last_valid + self.max_stale)
        return max(0.0, min(60.0, min(deadlines) - now))
