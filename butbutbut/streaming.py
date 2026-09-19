"""Synchronisation des alertes avec un flux video en retard.

Le direct de la source reste le temps de reference : le journal y est ecrit
sans attendre. Cette file ne retarde que ce qui alerte une personne (carte,
son, voix et crochet). Elle est volontairement ignorante de tkinter et du
reseau ; les deux boucles de surveillance lui donnent des ``Event`` et
reprennent ceux dont l'heure est venue.

Le recalage en cours de match passe par un petit fichier de commande atomique.
La GUI, la commande ``--sync-stream`` et l'ecran compagnon vivent dans des
processus differents du daemon : ce fichier est leur plus petit denominateur
commun, comme le fichier d'etat l'est deja pour ``--status``.
"""

from __future__ import annotations

import heapq
import json
import os
import time
import uuid
from pathlib import Path


MAX_DELAY = 3600.0


class Invalid(ValueError):
    pass


def normalize_delay(value) -> float:
    """Un retard en secondes, borne a une heure et jamais negatif."""
    try:
        delay = float(value or 0.0)
    except (TypeError, ValueError):
        raise Invalid("le retard du streaming doit etre un nombre de secondes")
    if delay < 0:
        raise Invalid("le retard du streaming ne peut pas etre negatif")
    if delay > MAX_DELAY:
        raise Invalid("le retard du streaming est limite a une heure")
    return delay


def _read(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def request(path, delay, now=None) -> dict:
    """Demande au daemon d'appliquer ``delay`` sans modifier sa config."""
    delay = normalize_delay(delay)
    now = time.time() if now is None else float(now)
    payload = {"token": uuid.uuid4().hex, "delay": delay,
               "requested_at": now}
    path = Path(path)
    tmp = path.with_name("{}.{}.tmp".format(path.name, os.getpid()))
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tmp.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False)
        os.replace(str(tmp), str(path))
    finally:
        try:
            tmp.unlink()
        except Exception:
            pass
    return payload


def delay_from_kickoff(state, now=None, match="") -> float:
    """Calcule le retard au clic « je vois le coup d'envoi maintenant »."""
    kickoff = None
    query = str(match or "").strip().casefold()
    if query:
        rows = list((state or {}).get("recent_kickoffs") or [])
        found = [row for row in rows
                 if query == str(row.get("id", "")).casefold()
                 or query in str(row.get("match", "")).casefold()]
        if not found:
            raise Invalid("aucun coup d'envoi recent ne correspond a {!r}"
                          .format(match))
        kickoff = found[-1].get("at")
    try:
        kickoff = float(kickoff if kickoff is not None
                         else (state or {}).get("last_kickoff_at"))
    except (TypeError, ValueError):
        raise Invalid("aucun coup d'envoi recent n'a ete detecte")
    now = time.time() if now is None else float(now)
    delay = now - kickoff
    if delay < 0 or delay > MAX_DELAY:
        raise Invalid("le dernier coup d'envoi detecte est trop ancien")
    return delay


class Delay:
    """File stable d'evenements, reprogrammable pendant le match."""

    def __init__(self, seconds=0.0, control_path=None, on_change=None,
                 now=None):
        self.seconds = normalize_delay(seconds)
        self.control_path = Path(control_path) if control_path else None
        self.on_change = on_change or (lambda _seconds: None)
        self.started_at = time.time() if now is None else float(now)
        self._queue = []
        self._sequence = 0
        current = _read(self.control_path) if self.control_path else None
        self._token = (current or {}).get("token", "")

    @property
    def active(self) -> bool:
        return self.seconds > 0

    def poll(self) -> bool:
        """Prend une nouvelle commande, une seule fois, et redate la file."""
        if self.control_path is None:
            return False
        data = _read(self.control_path)
        if not data or data.get("token") == self._token:
            return False
        self._token = str(data.get("token") or "")
        try:
            requested = float(data.get("requested_at"))
            delay = normalize_delay(data.get("delay"))
        except (TypeError, ValueError, Invalid):
            return False
        # Une commande abandonnee par un daemon precedent ne doit pas changer
        # le suivant au demarrage.
        if requested < self.started_at:
            return False
        self.seconds = delay
        self._queue = [(event.at + delay, sequence, event)
                       for _due, sequence, event in self._queue]
        heapq.heapify(self._queue)
        self.on_change(delay)
        return True

    def push(self, events, now=None) -> list:
        """Ajoute des evenements et rend tous ceux dont l'heure est venue."""
        self.poll()
        for event in events:
            self._sequence += 1
            heapq.heappush(self._queue,
                           (float(event.at) + self.seconds,
                            self._sequence, event))
        return self.ready(now=now)

    def ready(self, now=None) -> list:
        now = time.time() if now is None else float(now)
        found = []
        while self._queue and self._queue[0][0] <= now:
            found.append(heapq.heappop(self._queue)[2])
        return found

    def next_wait(self, default, now=None) -> float:
        """Le prochain releve ou la prochaine alerte, le premier des deux."""
        wait = max(0.0, float(default))
        if not self._queue:
            return wait
        now = time.time() if now is None else float(now)
        return min(wait, max(0.0, self._queue[0][0] - now))
