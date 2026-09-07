"""Enregistrer un vrai match, et le rejouer.

`butbutbut --test` montre des cartes fabriquees : jolies, mais figees. Pour
mettre au point l'affichage, reproduire un bug ("chez moi la carte deborde sur
ce match-la") ou fabriquer les captures du README, il faut un vrai
enchainement - coup d'envoi, but, mi-temps, expulsion, VAR, fin de match - et
il ne tombe qu'un samedi soir.

    butbutbut --record match.jsonl --leagues l1    # pendant le match
    butbutbut --replay match.jsonl                 # plus tard, autant de fois
    butbutbut --replay match.jsonl --speed 60      # une heure en une minute

Deux pieces, posees de part et d'autre du meme point d'accroche : l'`opener`
injectable de `espn.fetch()`.

  - `Recorder` se glisse entre le programme et le reseau. Il demande la source,
    ecrit la reponse brute sur le disque avec son horodatage, puis rend la
    reponse a l'appelant. Le daemon ne sait pas qu'il est enregistre et
    continue de tourner normalement.
  - `Player` fait l'inverse : il sert les reponses du fichier, dans l'ordre et
    a l'heure dite, sans toucher au reseau.

Ce qu'il y a entre les deux - le watcher, la detection des buts, les cartes, le
son, le journal - ne change pas d'une ligne. C'est la seule facon qu'un rejeu
prouve quelque chose : un rejeu qui passerait a cote du watcher ne testerait
que lui-meme.

Le temps, lui, est virtualise. `Timeline` porte l'heure de l'enregistrement,
`Pace` l'avance. Cette derniere presente l'interface de `threading.Event`
(`is_set`, `set`, `wait`) parce que c'est exactement par la que les deux
boucles de surveillance de cli.py dorment : leur passer une `Pace` a la place
de l'evenement d'arret suffit a accelerer le temps sans toucher a une seule de
leurs lignes.


Le format du fichier
--------------------

Du JSON Lines : une ligne = un objet JSON complet, termine par un saut de
ligne. Aucune ligne ne depend de la suivante, ce qui donne les deux proprietes
qu'on cherchait - ca se lit a l'oeil nu (`head -1 match.jsonl` passe dans
`python -m json.tool`), et une session tuee en plein milieu laisse un fichier
dont seule la derniere ligne est a jeter.

La premiere ligne est un en-tete :

    {"kind": "butbutbut-record", "format": 1, "version": "1.5.0",
     "recorded_at": 1757270481.4, "recorded_text": "2026-09-07 20:41:21",
     "leagues": ["fra.1"]}

`format` est le numero du *format*, pas celui du programme : c'est lui qui dit
si un fichier enregistre par une version anterieure reste rejouable. Un lecteur
accepte tout format inferieur ou egal au sien, et refuse un format superieur en
disant pourquoi ("enregistre au format 2, cette version ne lit que le format
1"). Un fichier sans en-tete lisible est refuse de la meme facon plutot que
devine : mieux vaut un refus clair qu'un rejeu qui part de travers.

Viennent ensuite les releves, un par appel a la source :

    {"at": 1757270481.6, "slug": "fra.1", "payload": {... ESPN, tel quel ...}}
    {"at": 1757270506.7, "slug": "fra.1", "repeat": true}

`at` est l'heure du releve (`time.time()`, en secondes) : c'est l'ecart entre
deux `at` successifs que le rejeu respecte, divise par `--speed`. `slug` est le
code ESPN de la competition, ce qui permet a un meme fichier de porter
plusieurs championnats melanges : ils repartent chacun dans leur file.

`repeat` remplace une charge utile identique, octet pour octet, a la precedente
du meme championnat - voir plus bas.

Un lecteur ignore ce qu'il ne comprend pas : une ligne illisible (la derniere
d'une session tuee), une ligne sans `slug`, un `repeat` qui ne suit aucune
charge utile connue pour son championnat. Il les compte et le dit, mais il
rejoue le reste. Une cle inconnue d'une version future est ignoree de la meme
facon : c'est ce qui permet d'ajouter un champ sans changer le numero de
format.

Ce que ca implique pour `repeat` : il designe la derniere charge utile *lue*,
pas une ligne precise. Une troncature n'entame jamais que la fin du fichier -
c'est la que le processus a ete tue - donc la question ne se pose que pour un
fichier trafique a la main, et un `repeat` en tete de fichier, qui ne suit
rien, est abandonne.


Ce que ca pese
--------------

Un tableau de bord ESPN fait 60 a 200 ko de JSON selon le nombre de matchs a
l'affiche. A 25 s par releve, deux heures de multiplex font environ 290
releves, soit **20 a 60 Mo par competition suivie**. Une soiree complete de
Ligue 1 enregistree en meme temps que les quatre autres grands championnats
depasserait tranquillement les 100 Mo : `--record` sert a garder *un* match,
pas un week-end, et `--leagues l1` n'est pas une precaution de style.

Deux choses ramenent ca a une taille raisonnable :

  - **le marqueur `repeat`.** Une reponse identique a la precedente n'est pas
    reecrite : la ligne se resume a son horodatage, une soixantaine d'octets au
    lieu de deux cent mille. L'heure du releve, elle, est conservee - c'est
    elle qui porte la cadence, et la perdre changerait le rythme du rejeu.
    Pendant un match en cours ca ne gagne rien (l'horloge du match bouge a
    chaque releve, donc la reponse aussi), mais un championnat au repos, qui
    est l'essentiel d'une soiree, se resume alors a une ligne toutes les cinq
    minutes.
  - **gzip.** Un chemin qui finit par `.gz` est compresse a l'ecriture et
    decompresse a la lecture, des deux cotes, sans rien demander. Du JSON
    d'API se comprime autour de 20 fois : les 40 Mo d'un match tiennent dans
    2 Mo, et le fichier reste lisible avec `zcat`.

A la lecture, l'enregistrement est charge en memoire d'un bloc. C'est assume :
un rejeu est un outil de mise au point, il tourne sur la machine de quelqu'un
qui regarde son ecran, pas sur un serveur.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import time
from collections import deque
from datetime import datetime
from pathlib import Path

from . import __version__, espn, leagues as catalogue, sports

# Le numero du format du fichier. A n'incrementer que si une version future
# cesse de pouvoir lire ce qu'on ecrit ici : ajouter une cle n'est pas un
# changement de format, les lecteurs ignorent ce qu'ils ne connaissent pas.
FORMAT = 1

# La signature de l'en-tete. Elle sert a refuser tout de suite un fichier qui
# n'a rien a voir (un .json, un .log) plutot qu'a le lire a moitie.
KIND = "butbutbut-record"

DEFAULT_SPEED = 1.0

# De combien on depasse l'heure d'un releve pour etre sur de le servir : les
# flottants ne tombent pas juste, et un releve manque decalerait tout le rejeu.
EPSILON = 0.001

# Passe ce silence apres le dernier releve, le rejeu se considere fini meme
# s'il restait des lignes qu'aucun championnat suivi ne reclame.
TAIL = 600.0


class RecordingError(RuntimeError):
    """Le fichier ne peut pas etre rejoue, et on dit pourquoi."""


# ------------------------------------------------------------- outillage -----

# La ressource qui n'est pas un tableau de bord : le resume d'un match, que le
# hockey va lire apres un but pour y prendre le buteur. Elle vit sous la meme
# competition que le tableau de bord, au meme hote, aux deux premiers segments
# pres - d'ou la marque ci-dessous.
SUMMARY_RESOURCE = "summary"
SUMMARY_MARK = "@"


def slug_of(url) -> str:
    """La cle du releve, extraite de l'URL qui l'a demande.

    Le `Recorder` ne voit passer que des URL : c'est ce que l'`opener` recoit.
    Depuis que le catalogue s'ouvre aux autres sports, deux competitions
    peuvent porter le meme code ESPN : la cle est donc celle de `League.ref` -
    "fra.1" au football, ou le sport est sous-entendu, "hockey:nhl" ailleurs.
    Sans quoi un enregistrement pris en `--leagues all-sports` servirait la
    NHL a qui demande la Ligue 1.

    Le resume d'un match prend la meme cle **suivie du numero du match** :
    "hockey:nhl@401809123". Les deux URL ne different que par leur troisieme
    segment ; sans cette marque, les 450 ko de `plays[]` d'un match iraient
    s'ajouter a la file du tableau de bord de la NHL, et le rejeu servirait un
    resume a un watcher qui demandait des scores. Deux ressources, deux files.
    """
    parts = str(url).split("/sports/")
    if len(parts) < 2:
        return ""
    segments = [part for part in parts[1].split("/") if part]
    if len(segments) < 2:
        return ""
    sport = segments[0].split("?")[0].strip()
    slug = segments[1].split("?")[0].strip()
    if not sport or not slug:
        return ""
    key = slug if sport == sports.DEFAULT.code else sport + ":" + slug
    mark = _summary_mark(segments)
    return key + mark if mark else key


def _summary_mark(segments) -> str:
    """"@401809123" quand l'URL vise un resume de match, "" sinon.

    Un resume sans numero de match n'existe pas dans la vraie source, mais il
    garde quand meme sa marque : une cle qui retomberait sur celle du tableau
    de bord melangerait les deux files, ce qui est exactement ce qu'on evite
    ici.
    """
    if len(segments) < 3:
        return ""
    resource, _, query = segments[2].partition("?")
    if resource.strip() != SUMMARY_RESOURCE:
        return ""
    for field in query.split("&"):
        name, _, value = field.partition("=")
        if name.strip() == "event" and value.strip():
            return SUMMARY_MARK + value.strip()
    return SUMMARY_MARK


def _is_gzip(path) -> bool:
    return str(path).lower().endswith(".gz")


def _open_text(path, mode):
    """Ouvre le fichier en texte utf-8, compresse ou non selon son extension.

    newline="\\n" partout : un enregistrement fait sous Windows doit se rejouer
    sous Linux, et une ligne JSON qui traine un \\r n'est plus du JSON Lines.
    """
    if _is_gzip(path):
        return gzip.open(str(path), mode + "t", encoding="utf-8", newline="\n")
    return open(str(path), mode, encoding="utf-8", newline="\n")


def human_size(count) -> str:
    """41 ko, 4.1 Mo : de quoi juger un fichier d'un coup d'oeil."""
    value = float(count)
    for unit in ("o", "ko", "Mo", "Go"):
        if value < 1024.0 or unit == "Go":
            return ("{:.0f} {}" if value >= 100 or unit == "o"
                    else "{:.1f} {}").format(value, unit)
        value /= 1024.0
    return "{:.0f} Go".format(value)


def human_time(seconds) -> str:
    """1 h 52, 3 min 20 s : la duree d'un enregistrement, en clair."""
    total = int(max(0.0, float(seconds)))
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return "{} h {:02d}".format(hours, minutes)
    if minutes:
        return "{} min {:02d} s".format(minutes, secs)
    return "{} s".format(secs)


# ---------------------------------------------------------- enregistrement ---

class Recorder:
    """Se pose entre le programme et la source, et note tout ce qui passe.

    Son `opener` a la signature attendue par `espn.fetch()` : c'est le seul
    point de contact avec le reste du programme. Il appelle la source (le
    reseau, ou l'`opener` qu'on lui a donne), ecrit la reponse, et la rend.

    Rien de ce qui se passe ici ne doit interrompre la surveillance : un disque
    plein pendant un match couterait des buts. Une ecriture qui echoue est donc
    signalee une fois au journal, et l'enregistrement s'arrete tout seul.
    """

    def __init__(self, path, opener=None, clock=None, leagues=(), dedupe=True,
                 on_log=None):
        self.path = Path(path)
        # L'opener sous-jacent : None = le reseau. Les tests s'en servent pour
        # enregistrer une source simulee.
        self._source = opener
        self.clock = clock or time.time
        self.dedupe = bool(dedupe)
        self.on_log = on_log or (lambda message: None)
        self.leagues = [getattr(league, "ref", str(league)) for league in leagues]

        self.polls = 0        # releves ecrits, marqueurs compris
        self.repeats = 0      # ... dont reponses identiques a la precedente
        self.bytes = 0        # octets ecrits (avant compression)
        self.broken = False   # l'ecriture a lache, on n'ecrit plus rien

        self._handle = None
        self._marks = {}      # slug -> empreinte de la derniere reponse ecrite

    # ------------------------------------------------------------ cycle de vie

    def start(self) -> "Recorder":
        """Ouvre le fichier et pose l'en-tete. Leve si le chemin est mauvais.

        C'est le seul moment ou une erreur remonte : un chemin impossible se
        dit au demarrage, pas trois heures plus tard quand on cherche le
        fichier.

        Le fichier est ouvert en ajout : reprendre un enregistrement apres un
        redemarrage le prolonge au lieu de l'effacer. Le second en-tete que ca
        pose est ignore a la lecture, expres pour ce cas.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = _open_text(self.path, "a")
        stamp = self.clock()
        self._write({
            "kind": KIND,
            "format": FORMAT,
            "version": __version__,
            "recorded_at": round(stamp, 3),
            "recorded_text": "{:%Y-%m-%d %H:%M:%S}".format(
                datetime.fromtimestamp(stamp)),
            "leagues": list(self.leagues),
        })
        return self

    def close(self) -> None:
        if self._handle is not None:
            try:
                self._handle.close()
            except Exception:
                pass
            self._handle = None

    def summary(self) -> str:
        """Ce qu'on a enregistre, pour le journal a l'arret."""
        parts = ["{} releve(s)".format(self.polls)]
        if self.repeats:
            parts.append("dont {} inchange(s)".format(self.repeats))
        parts.append(human_size(self.bytes))
        if _is_gzip(self.path):
            try:
                parts.append("{} sur le disque".format(
                    human_size(self.path.stat().st_size)))
            except Exception:
                pass
        return "enregistrement : {} -> {}".format(", ".join(parts), self.path)

    # ---------------------------------------------------------------- opener --

    def opener(self, url, timeout=espn.DEFAULT_TIMEOUT):
        """L'opener a donner au watcher. Meme contrat que espn.download()."""
        raw = (self._source or espn.download)(url, timeout)
        self.note(slug_of(url), raw)
        return raw

    def note(self, slug, raw) -> None:
        """Ecrit un releve. Ne leve jamais : la surveillance passe avant."""
        if self._handle is None or self.broken:
            return
        try:
            self._note(slug, raw)
        except Exception as exc:
            self.broken = True
            self.on_log("enregistrement interrompu ({}) : {}".format(self.path, exc))
            self.close()

    def _note(self, slug, raw) -> None:
        line = {"at": round(self.clock(), 3), "slug": slug}

        # L'empreinte plutot que la reponse entiere : comparer 16 octets coute
        # moins cher que d'en garder 200 000 par championnat suivi.
        data = raw if isinstance(raw, bytes) else str(raw).encode("utf-8")
        mark = hashlib.blake2b(data, digest_size=16).digest()
        if self.dedupe and self._marks.get(slug) == mark:
            line["repeat"] = True
            self.repeats += 1
        else:
            line["payload"] = json.loads(data.decode("utf-8", "replace"))
            self._marks[slug] = mark

        self._write(line)
        self.polls += 1

    def _write(self, entry) -> None:
        text = json.dumps(entry, ensure_ascii=False,
                          separators=(",", ":")) + "\n"
        self._handle.write(text)
        # A chaque ligne : une session tuee en plein match ne doit perdre que
        # la ligne en cours, pas le tampon des dix dernieres minutes.
        self._handle.flush()
        self.bytes += len(text.encode("utf-8"))


# ---------------------------------------------------------------- lecture ----

class Record:
    """Un releve relu : quand, quelle competition, et la reponse brute."""

    __slots__ = ("at", "slug", "text")

    def __init__(self, at, slug, text):
        self.at = at            # time.time() au moment du releve
        self.slug = slug        # code ESPN
        self.text = text        # la reponse, telle qu'elle sera reservie

    def __repr__(self):
        return "<Record {} {}>".format(self.slug, self.at)


class Recording:
    """Un fichier d'enregistrement, relu et verifie."""

    __slots__ = ("path", "format", "version", "recorded_at", "recorded_text",
                 "slugs", "records", "skipped", "repeats")

    def __init__(self, path, header, records, skipped=0, repeats=0):
        self.path = Path(path)
        self.format = header.get("format", FORMAT)
        self.version = str(header.get("version") or "?")
        self.recorded_at = header.get("recorded_at")
        self.recorded_text = str(header.get("recorded_text") or "")
        self.records = records
        self.skipped = skipped      # lignes illisibles ou orphelines
        self.repeats = repeats      # lignes 'repeat' resolues
        # L'ordre d'apparition, pas l'ordre alphabetique : un fichier a deux
        # championnats garde celui de la ligne de commande d'origine.
        seen = []
        for record in records:
            if record.slug not in seen:
                seen.append(record.slug)
        self.slugs = tuple(seen)

    # ---------------------------------------------------------------- lecture

    @classmethod
    def load(cls, path) -> "Recording":
        """Relit un fichier. Leve RecordingError s'il n'est pas rejouable."""
        path = Path(path)
        try:
            handle = _open_text(path, "r")
        except FileNotFoundError:
            raise RecordingError("enregistrement introuvable : {}".format(path))
        except OSError as exc:
            raise RecordingError("enregistrement illisible ({}) : {}".format(path, exc))

        header = None
        records = []
        skipped = 0
        repeats = 0
        latest = {}         # slug -> derniere charge utile lue, pour 'repeat'

        try:
            with handle:
                for line in cls._lines(handle):
                    entry = cls._decode(line)
                    if entry is None:
                        skipped += 1
                        continue
                    if header is None:
                        header = cls._header(entry, path)
                        continue
                    if entry.get("kind") == KIND:
                        # Un second en-tete : le daemon a repris son
                        # enregistrement dans le meme fichier. Ce n'est pas une
                        # ligne perdue, on ne la compte pas comme telle.
                        continue
                    record, orphan = cls._record(entry, latest)
                    if record is None:
                        skipped += 1
                        continue
                    if orphan:
                        repeats += 1
                    records.append(record)
        except (OSError, EOFError, gzip.BadGzipFile) as exc:
            # Un .gz coupe net leve ici : ce qui a ete lu reste bon, on garde.
            if header is None:
                raise RecordingError(
                    "enregistrement illisible ({}) : {}".format(path, exc))

        if header is None:
            raise RecordingError(
                "{} n'est pas un enregistrement butbutbut (en-tete absent ou "
                "illisible).".format(path))
        if not records:
            raise RecordingError(
                "{} ne contient aucun releve rejouable.".format(path))

        records.sort(key=lambda record: record.at)
        return cls(path, header, records, skipped=skipped, repeats=repeats)

    @staticmethod
    def _lines(handle):
        """Les lignes du fichier, une a une, sans jamais tout charger."""
        for line in handle:
            line = line.strip()
            if line:
                yield line

    @staticmethod
    def _decode(line):
        """La ligne en objet, ou None si elle est a jeter.

        C'est ici que la robustesse a la troncature se joue : une ligne coupee
        au milieu ne se decode pas, et une ligne qui n'est pas un objet JSON
        (un tableau, un nombre) n'a rien a faire dans un enregistrement.
        """
        try:
            entry = json.loads(line)
        except ValueError:
            return None
        return entry if isinstance(entry, dict) else None

    @staticmethod
    def _header(entry, path):
        """Verifie l'en-tete, ou leve en disant ce qui cloche."""
        if entry.get("kind") != KIND:
            raise RecordingError(
                "{} n'est pas un enregistrement butbutbut (la premiere ligne "
                "n'annonce pas {!r}).".format(path, KIND))
        try:
            version = int(entry.get("format", 0))
        except (TypeError, ValueError):
            version = 0
        if version > FORMAT:
            raise RecordingError(
                "{} est enregistre au format {}, et cette version de butbutbut "
                "ne lit que le format {} : mets butbutbut a jour "
                "(butbutbut --update).".format(path, version, FORMAT))
        if version < 1:
            raise RecordingError(
                "{} annonce un numero de format inattendu ({!r}).".format(
                    path, entry.get("format")))
        return entry

    @staticmethod
    def _record(entry, latest):
        """(Record, orphelin) pour une ligne de releve, ou (None, False).

        Un `repeat` reprend la derniere charge utile lue pour son championnat.
        Quand il n'y en a aucune - un fichier qui commencerait par un marqueur -
        le releve est abandonne : mieux vaut un releve de moins qu'un score
        invente.
        """
        slug = str(entry.get("slug") or "").strip()
        if not slug:
            return None, False
        try:
            at = float(entry.get("at"))
        except (TypeError, ValueError):
            return None, False

        if entry.get("repeat"):
            text = latest.get(slug)
            if text is None:
                return None, False
            return Record(at, slug, text), True

        payload = entry.get("payload")
        if not isinstance(payload, dict):
            return None, False
        text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        latest[slug] = text
        return Record(at, slug, text), False

    # ------------------------------------------------------------- lecture ---

    @property
    def span(self) -> float:
        """Duree couverte par l'enregistrement, en secondes."""
        return self.records[-1].at - self.records[0].at

    def leagues(self) -> list:
        """Les competitions du fichier, resolues dans le catalogue.

        Un code inconnu du catalogue est ouvert a la volee, exactement comme
        `--leagues por.1` : la source lui donnera son nom au premier releve
        rejoue.
        """
        found = []
        for slug in self.slugs:
            league = catalogue.find(slug)
            if league is not None and league not in found:
                found.append(league)
        return found

    def describe(self) -> str:
        parts = ["{} releve(s)".format(len(self.records))]
        names = [league.name for league in self.leagues()]
        if names:
            parts.append(", ".join(names))
        parts.append(human_time(self.span))
        if self.recorded_text:
            parts.append("enregistre le " + self.recorded_text)
        line = " - ".join(parts)
        if self.skipped:
            line += " ({} ligne(s) illisible(s), ignoree(s))".format(self.skipped)
        return line


# ----------------------------------------------------------------- rejeu -----

class Timeline:
    """Le temps du rejeu : celui de l'enregistrement, avance a la main.

    Deux aiguilles, comme dans le vrai programme : une horloge murale (celle
    qui sert au watcher a reperer les trous de veille) et une horloge
    monotone (celle qui sert a la cadence). Les deux avancent ensemble, ce qui
    evite qu'un rejeu accelere ressemble a une sortie d'hibernation.
    """

    __slots__ = ("start", "offset")

    def __init__(self, start=0.0):
        self.start = float(start)
        self.offset = 0.0

    def monotonic(self) -> float:
        return self.offset

    def wall(self) -> float:
        return self.start + self.offset

    def advance(self, seconds) -> None:
        self.offset += max(0.0, float(seconds))


class Player:
    """Sert les releves d'un enregistrement, dans l'ordre et a l'heure dite.

    Son `opener` a le meme contrat que celui du `Recorder`, ce qui suffit a
    remplacer le reseau : le watcher demande un championnat, il recoit ce que
    la source avait repondu ce soir-la.

    Deux regles, qui font toute la fidelite du rejeu :

      - un releve n'est jamais saute. Chaque appel rend au plus un releve, le
        plus ancien pas encore servi dont l'heure est passee. Un watcher qui
        interrogerait moins souvent que l'enregistrement prendrait du retard,
        mais verrait quand meme tous les evenements ;
      - un appel avant l'heure du prochain releve rend le precedent, a
        l'identique. C'est ce que la vraie source aurait fait : interroger deux
        fois de suite un tableau de bord qui n'a pas bouge rend deux fois la
        meme chose, et le watcher n'en tire aucun evenement.
    """

    def __init__(self, recording):
        self.recording = recording
        self.timeline = Timeline(recording.records[0].at)
        self.polls = 0
        self.served = 0

        self._queues = {}
        for record in recording.records:
            self._queues.setdefault(record.slug, deque()).append(record)
        self._pending = len(recording.records)
        self._last = {}      # slug -> derniere reponse servie
        self._end = recording.records[-1].at

    # ------------------------------------------------------------- horloges --

    def monotonic(self) -> float:
        return self.timeline.monotonic()

    def wall(self) -> float:
        return self.timeline.wall()

    def advance(self, seconds) -> None:
        self.timeline.advance(seconds)

    @property
    def elapsed(self) -> float:
        """Temps de match ecoule depuis le debut du rejeu, en secondes."""
        return self.timeline.offset

    # --------------------------------------------------------------- source --

    def opener(self, url, timeout=None):
        """L'opener a donner au watcher : aucun reseau, jamais."""
        slug = slug_of(url)
        self.polls += 1
        now = self.wall()

        queue = self._queues.get(slug)
        while queue and queue[0].at <= now:
            record = queue.popleft()
            self._pending -= 1
            self._last[slug] = record.text
            self.served += 1
            return record.text

        previous = self._last.get(slug)
        if previous is None:
            # Le watcher reclame un championnat que le fichier ne porte pas,
            # ou le reclame avant son premier releve. Une erreur de source est
            # exactement ce que le vrai programme sait deja encaisser.
            raise espn.SourceError(
                "aucun releve enregistre pour {} a cet instant".format(slug or "?"))
        return previous

    # -------------------------------------------------------------- cadence --

    def next_at(self):
        """L'heure du prochain releve en attente, ou None s'il n'en reste pas."""
        times = [queue[0].at for queue in self._queues.values() if queue]
        return min(times) if times else None

    @property
    def pending(self) -> int:
        return self._pending

    def exhausted(self) -> bool:
        """Vrai quand il n'y a plus rien a rejouer.

        Le garde-fou du bas : un fichier peut porter des releves qu'aucun
        championnat suivi ne viendra chercher (une competition retiree de la
        selection). Passe TAIL secondes de silence apres le dernier releve, on
        arrete plutot que de tourner pour toujours.
        """
        if self._pending <= 0:
            return True
        return self.wall() > self._end + TAIL


class Pace:
    """L'attente du rejeu : elle avance le temps au lieu de le subir.

    Elle porte l'interface de `threading.Event` - `is_set()`, `set()`,
    `wait()` - parce que c'est exactement par la que les boucles de
    surveillance de cli.py dorment : `stopping.wait(guard.plan_wait())`. En
    leur passant une Pace a la place de l'evenement d'arret, le rejeu accelere
    le temps sans qu'une seule ligne de ces boucles ne change, et il traverse
    donc les memes chemins qu'un vrai samedi soir.

    Ce qu'elle fait a chaque attente : avancer l'horloge du rejeu de ce que la
    boucle s'apprete a dormir, puis dormir vraiment ce meme delai divise par
    `speed`. Une exception : quand le prochain releve tombe avant la fin du
    delai demande, elle s'arrete a son heure. Sans ca, un enregistrement dont
    les releves ne tombent pas pile sur la cadence prendrait un retard qui
    grandirait a chaque tour.
    """

    def __init__(self, player, speed=DEFAULT_SPEED, sleeper=None, linger=0.0):
        self.player = player
        self.speed = max(0.001, float(speed))
        self.sleeper = sleeper or time.sleep
        # Le temps laisse a la derniere carte avant de fermer la fenetre :
        # sans lui, le dernier but du match disparaitrait a l'instant meme ou
        # il s'affiche.
        self.linger = max(0.0, float(linger))
        self.steps = 0
        self._stopped = False

    # ---------------------------------------------------- interface d'Event --

    def is_set(self) -> bool:
        return self._stopped

    def set(self) -> None:
        self._stopped = True

    def clear(self) -> None:
        self._stopped = False

    def wait(self, timeout=None) -> bool:
        if self._stopped:
            return True

        if self.player.exhausted():
            if self.linger:
                self.sleeper(self.linger)
            self._stopped = True
            return True

        step = max(0.0, float(timeout or 0.0))
        upcoming = self.player.next_at()
        if upcoming is not None:
            remaining = upcoming - self.player.wall()
            if 0.0 < remaining < step:
                step = remaining + EPSILON

        self.player.advance(step)
        self.steps += 1
        if step:
            self.sleeper(step / self.speed)
        return self._stopped
