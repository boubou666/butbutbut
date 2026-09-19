"""Le fichier d'etat : ce que le daemon a vu a son dernier releve.

Pourquoi un fichier : `--status` tourne dans un autre processus que le daemon
et n'a aucun moyen de lui poser la question. Le daemon depose donc a chaque
releve une photo de ce qu'il voit (horodatage, matchs en cours, buts du jour)
et `--status` la relit. Sans ca, un daemon bloque sur un socket ressemble
exactement a un daemon qui marche : le fichier pid dit seulement qu'un
processus existe, jamais qu'il travaille.

Deux regles tiennent tout le module :

  - l'ecriture passe par un fichier temporaire puis `os.replace()`, qui est
    atomique. `--status` peut lire pile pendant une ecriture : sans ca il
    finirait par tomber sur un JSON coupe en deux, un jour, chez quelqu'un
    d'autre, et personne ne saurait le reproduire ;
  - aucune erreur ne sort d'ici. Disque plein, dossier en lecture seule,
    antivirus qui tient le fichier : un etat manquant est un desagrement, un
    daemon qui meurt pendant un match n'en est pas un. C'est la meme logique
    que `log()`.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path

from . import souvenir
from .i18n import tr

VERSION = 2
RECENT_EVENTS = 24

# On tolere trois releves manques avant de crier : la source repond parfois
# lentement, et le backoff de watcher.py peut deja avoir espace un passage.
STALE_MARGIN = 3.0
STALE_FLOOR = 90.0        # plancher, pour ne pas alarmer sur une cadence courte


# ------------------------------------------------------------- ecriture ------

def write(path, payload) -> bool:
    """Ecrit le JSON d'un seul bloc. Renvoie False si ca n'a pas marche.

    Le temporaire porte le pid dans son nom : deux processus qui ecriraient en
    meme temps (une instance qui demarre pendant qu'une autre s'arrete) ne se
    marchent pas dessus.
    """
    path = Path(path)
    tmp = path.with_name("{}.{}.tmp".format(path.name, os.getpid()))
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tmp.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=1,
                      sort_keys=True)
        os.replace(str(tmp), str(path))
        return True
    except Exception:
        try:
            tmp.unlink()
        except Exception:
            pass
        return False


def clear(path) -> None:
    """Efface le fichier d'etat, sans jamais se plaindre."""
    try:
        Path(path).unlink()
    except Exception:
        pass


# ------------------------------------------------------------- lecture -------

def read(path):
    """Le contenu du fichier d'etat, ou None : absent, illisible, tronque.

    Un fichier tronque est traite comme un fichier absent : c'est la seule
    reponse honnete, et l'appelant n'a de toute facon rien d'autre a en faire.
    """
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def age(data, now=None):
    """Secondes ecoulees depuis le dernier releve, ou None si indatable."""
    if not data:
        return None
    try:
        stamp = float(data.get("updated_at"))
    except (TypeError, ValueError):
        return None
    now = time.time() if now is None else now
    return max(0.0, now - stamp)


def stale_after(data) -> float:
    """Au-dela de ce delai, le silence du daemon devient suspect.

    Le seuil suit la cadence annoncee : 25 s entre deux releves quand un match
    est en cours, cinq minutes quand il n'y a rien a suivre. Comparer les deux
    au meme chronometre dirait n'importe quoi dans un sens ou dans l'autre.
    """
    base = None
    if data:
        key = "interval" if data.get("matches") else "idle_interval"
        try:
            base = float(data.get(key))
        except (TypeError, ValueError):
            base = None
    if not base or base <= 0:
        base = 300.0
    return max(STALE_FLOOR, base * STALE_MARGIN)


def is_stale(data, now=None) -> bool:
    seconds = age(data, now=now)
    if seconds is None:
        return True
    return seconds > stale_after(data)


def describe_age(seconds) -> str:
    """"il y a 12 s", "il y a 4 min", "il y a 2 h 10" - jamais un nombre nu."""
    if seconds is None:
        return tr("date inconnue")
    seconds = int(seconds)
    if seconds < 90:
        return tr("il y a {} s", seconds)
    if seconds < 5400:
        return tr("il y a {} min", seconds // 60)
    return tr("il y a {} h {:02d}", seconds // 3600, (seconds % 3600) // 60)


def today() -> str:
    return "{:%Y-%m-%d}".format(datetime.now())


# ------------------------------------------------------------- ecrivain ------

def _match_row(match) -> dict:
    return {
        "id": str(match.id),
        "league": match.league.name,
        "home": match.home,
        "away": match.away,
        "home_score": match.home_score,
        "away_score": match.away_score,
        "clock": match.clock or match.detail or "",
    }


def _event_row(event) -> dict:
    """La forme publique d'une alerte, pour l'ecran compagnon."""
    return {
        "at": event.at,
        "kind": event.kind,
        "title": event.title,
        "context": getattr(event, "context", ""),
        "context_label": event.context_label() if event.goal else "",
        "league": event.league.name,
        "home": event.match.home,
        "away": event.match.away,
        "home_score": event.home_score,
        "away_score": event.away_score,
        "score_line": event.score_line,
        "team": event.team,
        "detail": event.detail_line(),
        "minute": event.minute,
    }


class Reporter:
    """Tient le fichier d'etat a jour, releve apres releve.

    Les deux chemins de surveillance (avec et sans carte) partagent cet objet :
    ce qu'il faut retenir d'un releve est decide ici, une seule fois.
    """

    __slots__ = ("path", "leagues", "interval", "idle_interval", "started_at",
                 "goals", "day", "pin", "recent", "last_kickoff_at",
                 "last_kickoff_match", "recent_kickoffs", "stream_delay",
                 "stories")

    def __init__(self, path, leagues=(), interval=0, idle_interval=0, pin="",
                 stories_path=None, stream_delay=0.0):
        self.path = Path(path)
        self.leagues = [league.name for league in leagues]
        self.interval = interval
        self.idle_interval = idle_interval
        self.started_at = time.time()
        self.goals = 0
        self.day = today()
        # L'equipe epinglee, telle qu'elle a ete demandee : `--status` tourne
        # dans un autre processus et n'a que ce fichier pour savoir ce que le
        # daemon suit vraiment - le sien peut avoir ete lance avec d'autres
        # options, ou avant une modification du fichier de configuration.
        self.pin = str(pin or "")
        self.recent = []
        self.last_kickoff_at = None
        self.last_kickoff_match = ""
        self.recent_kickoffs = []
        self.stream_delay = float(stream_delay or 0.0)
        self.stories = souvenir.Store(stories_path) if stories_path else None

    def record(self, events=()) -> None:
        """Compte les buts du jour, buts annules et phases de match exclus."""
        for event in events:
            if getattr(event, "goal", False):
                self._roll()
                self.goals += 1
            if getattr(event, "kind", "") == "kickoff":
                self.last_kickoff_at = event.at
                self.last_kickoff_match = event.score_line
                self.recent_kickoffs.append({
                    "id": str(event.match.id),
                    "at": event.at,
                    "match": event.score_line,
                    "home": event.match.home,
                    "away": event.match.away,
                })
                self.recent_kickoffs = self.recent_kickoffs[-8:]
            if getattr(event, "kind", "") == "fulltime" and self.stories:
                self.stories.add(souvenir.from_match(event.match, event.at))

    def remember(self, events=()) -> None:
        """Garde les alertes effectivement livrees, jamais le direct brut."""
        for event in events:
            if not getattr(event, "spoiler_free", False):
                self.recent.append(_event_row(event))
        self.recent = self.recent[-RECENT_EVENTS:]

    def snapshot(self, matches=(), pinned=None) -> dict:
        matches = list(matches)
        live = [match for match in matches if match.live]
        self._roll()
        return {
            "pin": self.pin,
            # Le match epingle a l'instant, ou None : il peut etre termine (la
            # carte survit quelques minutes) et ne serait alors dans aucune des
            # lignes ci-dessous.
            "pinned": _match_row(pinned) if pinned is not None else None,
            "version": VERSION,
            "pid": os.getpid(),
            "updated_at": time.time(),
            "updated_text": "{:%Y-%m-%d %H:%M:%S}".format(datetime.now()),
            "started_at": self.started_at,
            "day": self.day,
            "goals_today": self.goals,
            "stream_delay": self.stream_delay,
            "last_kickoff_at": self.last_kickoff_at,
            "last_kickoff_match": self.last_kickoff_match,
            "recent_kickoffs": list(self.recent_kickoffs),
            "recent_events": list(self.recent),
            "souvenirs": (list(self.stories.stories[-10:])
                           if self.stories is not None else []),
            "interval": self.interval,
            "idle_interval": self.idle_interval,
            "leagues": list(self.leagues),
            "total_matches": len(matches),
            "matches": [_match_row(match) for match in live],
        }

    def update(self, matches=(), events=(), pinned=None, visible_events=None,
               stream_delay=None) -> bool:
        """Un releve vient de finir : compter, puis publier.

        ``events`` est le direct reel, pour le journal de bord et les totaux.
        ``visible_events`` est ce qui vient d'etre livre apres retard. Omis,
        il vaut ``events`` et preserve le contrat des anciens appelants.
        """
        self.record(events)
        self.remember(events if visible_events is None else visible_events)
        if stream_delay is not None:
            self.stream_delay = float(stream_delay)
        return write(self.path, self.snapshot(matches, pinned=pinned))

    def _roll(self) -> None:
        """Minuit : le compteur du jour repart de zero.

        Un daemon laisse tourner une semaine annoncerait sinon les buts de
        lundi un vendredi matin.
        """
        current = today()
        if current != self.day:
            self.day = current
            self.goals = 0
