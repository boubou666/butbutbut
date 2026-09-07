"""Le son du but : lecture multiplateforme, avec repli synthetise.

Ordre de priorite :
  1. un fichier depose dans <data_dir>/sound/  (`butbutbut --paths` donne le chemin)
  2. le son fourni avec butbutbut (butbutbut/assets/but.mp3)
  3. une corne de stade synthetisee ici meme, utilisee quand rien sur la
     machine ne sait lire le mp3 (Linux minimal sans mpv/ffmpeg/sox/vlc)

Formats acceptes : wav, mp3, ogg, opus, flac, m4a, aac.

Le **nom** des fichiers deposes parle : `om.mp3` ne sort que quand l'OM marque,
`fra.1.mp3` que pour un but de Ligue 1, `contre.mp3` quand une equipe suivie
encaisse. Le reste est le fond sonore, tire au hasard comme avant. Tout se
joue dans armed_sounds(), une fonction pure : le dossier est relu a chaque but,
et le classement se teste sans jouer une note.

`--sound-for om=cri.wav` dit la meme chose sans renommer ni deplacer quoi que
ce soit, et surtout sans deviner : le mot est donne, pas lu dans un nom de
fichier. Ces paires-la passent par les MEMES etages - une equipe l'emporte sur
sa competition parce qu'elle est plus precise - et couvrent le dossier a etage
egal, puisqu'elles ont ete ecrites noir sur blanc.
"""

from __future__ import annotations

import math
import random
import re
import shutil
import struct
import subprocess
import sys
import wave
from pathlib import Path

from . import leagues, teams

SAMPLE_RATE = 44100
TOTAL_SECONDS = 2.10

# Corne de stade : deux coups, le second tenu.
NOTES = (
    {"start": 0.00, "duration": 0.55, "freq": 233.08},   # si bemol 3
    {"start": 0.62, "duration": 1.35, "freq": 311.13},   # mi bemol 4
)

AUDIO_EXTENSIONS = (".wav", ".mp3", ".ogg", ".oga", ".opus", ".flac", ".m4a", ".aac")

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
BUNDLED_SOUND = ASSETS_DIR / "but.mp3"

# Lecteurs Linux/BSD, dans l'ordre de preference.
# "any" = gere aussi les formats compresses ; sinon wav uniquement.
LINUX_PLAYERS = (
    ("mpv", ["mpv", "--really-quiet", "--no-video"], "any"),
    ("ffplay", ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"], "any"),
    ("play", ["play", "-q"], "any"),                  # SoX
    ("cvlc", ["cvlc", "--play-and-exit", "--intf", "dummy"], "any"),
    ("pw-play", ["pw-play"], "wav"),                  # PipeWire
    ("paplay", ["paplay"], "wav"),                    # PulseAudio
    ("aplay", ["aplay", "-q"], "wav"),                # ALSA
)

MCI_ALIAS = "butsound"

# --- Les etages du choix par contexte ----------------------------------------

TIER_TEAM = "team"          # om.mp3 : cette equipe vient de marquer
TIER_CONCEDED = "conceded"  # contre.mp3 : une equipe suivie vient d'encaisser
TIER_LEAGUE = "league"      # fra.1.mp3, l1.mp3 : un but de cette competition
TIER_GENERAL = "general"    # tout le reste : le fond sonore

# L'ordre de priorite. Sa justification est dans armed_sounds().
TIERS = (TIER_TEAM, TIER_CONCEDED, TIER_LEAGUE, TIER_GENERAL)

# Le seul nom que butbutbut impose. Plusieurs ecritures, deux langues : autant
# qu'il se devine, personne ne va lire une table pour deposer un fichier.
CONCEDED_WORDS = ("contre", "encaisse", "against", "conceded")
_CONCEDED = frozenset(teams.normalize(word) for word in CONCEDED_WORDS)

# Ce qui separe un nom de sa variante : om-1.mp3 et om-2.mp3 arment le meme
# etage. Le point en fait partie pour que `fra.1-b.mp3` retombe sur `fra.1`.
VARIANT_SEPARATORS = "-_ ."


# ------------------------------------------------------------- synthese ------

def _render_samples(volume: float) -> list:
    count = int(SAMPLE_RATE * TOTAL_SECONDS)
    buffer = [0.0] * count
    two_pi = math.tau

    for note in NOTES:
        offset = int(note["start"] * SAMPLE_RATE)
        length = int(note["duration"] * SAMPLE_RATE)
        attack = int(0.030 * SAMPLE_RATE)
        release = int(0.180 * SAMPLE_RATE)

        for i in range(length):
            t = i / SAMPLE_RATE

            if i < attack:
                envelope = i / attack
            elif i > length - release:
                envelope = (length - i) / release
            else:
                envelope = 1.0

            # Une corne, c'est riche en harmoniques et legerement instable.
            drift = 1.0 + 0.0035 * math.sin(two_pi * 4.2 * t)
            phase = two_pi * note["freq"] * drift * t

            value = 0.0
            for harmonic in range(1, 11):
                value += math.sin(phase * harmonic) / harmonic

            index = offset + i
            if index < count:
                buffer[index] += (value / 2.6) * envelope

    for i in range(count):
        buffer[i] = math.tanh(buffer[i] * 1.6) * volume

    fade = int(0.02 * SAMPLE_RATE)  # evite le clic de fin
    for i in range(fade):
        buffer[count - 1 - i] *= i / fade

    return buffer


def write_wav(path: Path, volume: float = 0.55) -> Path:
    """Ecrit la corne synthetisee en WAV PCM 16 bits mono."""
    path.parent.mkdir(parents=True, exist_ok=True)
    samples = _render_samples(volume)
    frames = b"".join(
        struct.pack("<h", int(max(-1.0, min(1.0, s)) * 32000)) for s in samples
    )
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(SAMPLE_RATE)
        handle.writeframes(frames)
    return path


def ensure_wav(path: Path, volume: float = 0.55, force: bool = False) -> Path:
    if force or not path.exists() or path.stat().st_size == 0:
        write_wav(path, volume)
    return path


def custom_sounds(custom_dir: Path) -> list:
    """Les fichiers audio deposes par l'utilisateur, tries."""
    if not custom_dir.is_dir():
        return []
    return sorted(
        p for p in custom_dir.iterdir()
        if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS
    )


def bundled_sound() -> Path | None:
    """Le son livre avec butbutbut, ou None si le paquet n'en contient pas."""
    return BUNDLED_SOUND if BUNDLED_SOUND.is_file() else None


# ------------------------------------------------------ le nom qui parle -----

def name_candidates(path) -> list:
    """Le nom du fichier, puis ses prefixes, du plus long au plus court.

    Sans ca, deux sons pour la meme equipe seraient impossibles : `om-1.mp3`
    ne designe rien, alors que `om` designe Marseille. On rogne donc la
    variante de droite jusqu'a tomber sur un mot qui parle - ou sur rien, et
    le fichier rejoint le fond sonore.

    Les noms a rallonge ne sont pas casses pour autant : `saint-etienne`
    est essaye entier avant de perdre son `-etienne`.
    """
    stem = Path(path).stem.strip()
    found = []
    while stem:
        if stem not in found:
            found.append(stem)
        cut = max(stem.rfind(char) for char in VARIANT_SEPARATORS)
        if cut <= 0:
            break
        stem = stem[:cut].strip()
    return found


class Context:
    """Ce qu'un but dit de lui-meme au moment de choisir le son.

    Volontairement plat, et ignorant de watcher.Event : le module du son n'a
    pas a savoir comment un but est detecte, et une fonction de choix qui ne
    prend que des donnees se teste sans reseau, sans ecran et sans jouer une
    note. C'est cli.sound_context() qui fait le pont.
    """

    __slots__ = ("league", "scorer_names", "beaten_names", "conceded", "clubs")

    def __init__(self, league=None, scorer_names=(), beaten_names=(),
                 conceded=False, clubs=()):
        self.league = league                     # leagues.League, ou None
        # Toutes les ecritures connues des deux equipes (nom complet, nom
        # court, abreviation) : c'est ce qu'un nom de fichier doit accrocher.
        self.scorer_names = tuple(scorer_names)
        self.beaten_names = tuple(beaten_names)
        # Vrai quand c'est une equipe SUIVIE qui vient d'encaisser. Sans
        # --teams il n'y a personne a suivre, donc jamais de `contre.mp3`.
        self.conceded = bool(conceded)
        # Les mots dont on sait qu'ils designent un club meme s'il ne joue pas
        # ici : voir names_a_club().
        self.clubs = tuple(clubs)

    def names_scorer(self, name) -> bool:
        return teams.designates(name, self.scorer_names)

    def names_beaten(self, name) -> bool:
        return teams.designates(name, self.beaten_names)

    def names_league(self, name) -> bool:
        found = leagues.designates(name)
        return (found is not None and self.league is not None
                and found.slug == self.league.slug)

    def names_a_club(self, name) -> bool:
        """Vrai si ce mot designe un club, meme absent de ce match-ci.

        Sert a ne PAS verser `psg.mp3` dans le fond sonore pendant un
        Angers - Rennes : un nom de club arme un etage, il ne devient jamais
        le son par defaut de tous les autres buts.

        Hors du match en cours, butbutbut n'a pas de catalogue d'equipes sous
        la main - il faudrait le reseau. Le vocabulaire se limite donc aux
        surnoms usuels et a ce qui a ete passe a --teams ; c'est documente, et
        ca couvre le cas qui compte, celui de quelqu'un qui suit un club.
        """
        token = teams.normalize(teams.expand(name))
        if not token:
            return False
        if teams.normalize(name) in teams.ALIASES:
            return True
        return any(token == teams.normalize(teams.expand(club))
                   for club in self.clubs)


def is_conceded_word(token) -> bool:
    """Ce mot est-il celui du but encaisse (`contre`, `against`...) ?"""
    return teams.normalize(token) in _CONCEDED


def tier_of(path, context):
    """L'etage arme par ce nom de fichier pour ce but, ou None.

    None ne veut pas dire "general" : il veut dire "ce fichier parle d'autre
    chose" - une autre competition, l'equipe qui vient justement d'encaisser.
    Ces fichiers-la sont ecartes du tirage, pas verses dedans.
    """
    for name in name_candidates(path):
        if is_conceded_word(name):
            return TIER_CONCEDED if context.conceded else None
        if context.names_scorer(name):
            return TIER_TEAM
        if context.names_beaten(name):
            return None                  # elle vient d'encaisser : elle se tait
        found = leagues.designates(name)
        if found is not None:
            return TIER_LEAGUE if context.names_league(name) else None
        if context.names_a_club(name):
            return None                  # un club, mais pas un des deux ici
    return TIER_GENERAL


def sounds_by_tier(files, context) -> dict:
    """Les fichiers ranges par etage. Ceux qui visent ailleurs disparaissent."""
    pools = {tier: [] for tier in TIERS}
    for path in files:
        tier = tier_of(path, context)
        if tier is not None:
            pools[tier].append(path)
    return pools


# ------------------------------------------------------- les sons nommes ----

class Invalid(ValueError):
    """Une paire de --sound-for qui ne veut rien dire."""


# Ce qui separe deux paires : la virgule et le point-virgule comme partout
# ailleurs, et le retour a la ligne parce qu'une valeur du fichier de
# configuration peut s'ecrire sur plusieurs lignes.
#
# Un separateur ne coupe que s'il est SUIVI d'un `mot=`. Sans cela
# `om=Mes sons, vol. 2/om.wav` serait coupe en deux, et un chemin a virgule
# deviendrait impossible a ecrire - alors que rien, dans un systeme de
# fichiers, n'interdit la virgule.
PAIR_SPLIT = re.compile(r"[,;\n]\s*(?=[^=,;\n]+=)")


class Assignment:
    """Un son nomme a la main : le mot vise, et le fichier a jouer.

    Le mot n'est pas resolu ici. Une competition se reconnaitrait hors ligne,
    une equipe non - il faudrait le catalogue de la source - et surtout la
    reponse depend du but : `om` designe l'equipe qui marque dans un match, et
    personne dans le suivant. On garde donc le mot tel qu'il a ete tape, et
    c'est assignment_tier() qui tranche, but par but.
    """

    __slots__ = ("token", "path")

    def __init__(self, token, path):
        self.token = str(token).strip()
        # `~` est ce qu'on tape spontanement dans un fichier de configuration,
        # et rien ne l'y developpe : le shell n'est pas passe par la.
        self.path = Path(str(path).strip()).expanduser()

    def __repr__(self):
        return "<Assignment {}={}>".format(self.token, self.path)


def parse_assignments(value) -> list:
    """Lit "om=cri.wav,ucl=corne.mp3" et rend [Assignment, ...]. Leve Invalid.

    Le meme texte vient de deux endroits, la ligne de commande et une cle du
    fichier de configuration : d'ou une lecture unique, et une erreur qui se
    dit avec le mot fautif sous les yeux plutot qu'un "valeur invalide" sec.
    """
    if not value:
        return []
    text = value if isinstance(value, str) else "\n".join(
        str(part) for part in value)

    found = []
    for chunk in PAIR_SPLIT.split(text):
        # Une virgule de fin de ligne n'a coupe nulle part, faute de paire
        # derriere : elle arrive ici, collee au chemin.
        chunk = chunk.strip().strip(",;").strip()
        if not chunk:
            continue
        token, sign, path = chunk.partition("=")
        if not sign or not token.strip() or not path.strip():
            raise Invalid(
                "--sound-for attend des paires nom=chemin ({!r} n'en est pas "
                "une). Exemple : --sound-for om=cri.wav,ucl=corne.mp3".format(
                    chunk))
        found.append(Assignment(token, path))
    return found


def unusable(path):
    """Ce qui cloche avec ce fichier, ou None s'il est jouable.

    Rend la phrase plutot qu'un booleen : c'est elle qu'on affiche au demarrage
    et qu'on ecrit au journal, et "fichier introuvable" ne s'arbitre pas de la
    meme facon que "format inconnu" par celui qui lit.

    Le format se juge sur l'extension, comme partout ailleurs dans ce module :
    ouvrir le fichier pour de bon demanderait un decodeur qu'on n'a pas, et le
    lecteur du systeme, lui, se fie deja au nom.
    """
    path = Path(path)
    try:
        if path.is_dir():
            return "c'est un dossier, pas un fichier"
        if not path.is_file():
            return "fichier introuvable"
        if path.suffix.lower() not in AUDIO_EXTENSIONS:
            return "format que butbutbut ne sait pas jouer (au choix : {})".format(
                ", ".join(extension[1:] for extension in AUDIO_EXTENSIONS))
        with path.open("rb") as handle:
            handle.read(1)
    except (OSError, ValueError) as exc:
        # Droits refuses, chemin impossible sur ce systeme, disque parti :
        # tout cela se dit, et rien de tout cela ne doit lever ici.
        return "fichier illisible ({})".format(exc)
    return None


def check_assignments(assigned) -> list:
    """Ce qui cloche dans ces paires : une phrase par paire fautive.

    Une liste vide veut dire que tout est jouable. Toutes les paires sont
    regardees, pas seulement la premiere : corriger trois chemins un par un,
    en relancant a chaque fois, n'amuse personne.
    """
    problems = []
    for one in assigned:
        problem = unusable(one.path)
        if problem is not None:
            problems.append("le son de {} : {} ({})".format(
                one.token, problem, one.path))
    return problems


def assignment_tier(assignment, context):
    """L'etage arme par cette paire pour ce but, ou None.

    Le meme entonnoir que les noms de fichiers - l'equipe avant sa competition,
    parce qu'elle est plus precise - a un etage pres : il n'y a pas de general
    ici. Un son nomme vise quelqu'un ; un mot qui ne dit rien de CE but-la se
    tait plutot que de devenir le fond sonore de tous les autres.
    """
    name = assignment.token
    if is_conceded_word(name):
        return TIER_CONCEDED if context.conceded else None
    if context.names_scorer(name):
        return TIER_TEAM
    if context.names_beaten(name):
        return None                      # elle vient d'encaisser : elle se tait
    if context.names_league(name):
        return TIER_LEAGUE
    return None


def named_by_tier(assigned, context, on_missing=None) -> dict:
    """Les sons nommes ranges par etage, ceux qui ont disparu en moins.

    Le disque n'est consulte que pour les paires que CE but arme. Un son nomme
    pour une equipe qui ne joue pas ce soir n'a pas a etre cherche, et sa
    disparition n'a pas a remplir le journal d'une ligne par but tombe
    ailleurs. Le chemin a ete verifie au demarrage : s'il ne repond plus, c'est
    qu'une cle USB est partie ou qu'un fichier a ete renomme en cours de
    route - on le note, et l'etage repasse la main comme s'il etait vide.
    """
    pools = {tier: [] for tier in TIERS}
    for one in assigned:
        tier = assignment_tier(one, context)
        if tier is None:
            continue
        problem = unusable(one.path)
        if problem is not None:
            if on_missing is not None:
                on_missing(one, problem)
            continue
        pools[tier].append(one.path)
    return pools


def armed_sounds(files, context=None, assigned=(), on_missing=None) -> list:
    """Les fichiers a tirer au sort pour ce but : l'etage le plus precis servi.

    L'ordre est **equipe > contre > competition > general**, et il se lit comme
    un entonnoir : chaque etage peut reclamer plus de buts que le precedent.
    `om.mp3` ne parle que des buts de l'OM ; `contre.mp3` de tous les buts
    encaisses par les clubs suivis - avec `--teams om,psg,ol`, ca en fait
    beaucoup ; `fra.1.mp3` de toute une competition ; le fond sonore, de tout.
    Trier du plus etroit au plus large, c'est garantir qu'une intention precise
    n'est jamais recouverte par une plus large : qui depose `om.mp3` l'entend a
    chaque but de l'OM, meme s'il a aussi un son de Ligue 1.

    Deux consequences voulues. Un OM - PSG avec `om.mp3` et `contre.mp3` sonne
    differemment selon qui marque, et c'est exactement ce qu'on cherchait :
    entendre la difference entre "on a marque" et "on a pris". Et un etage vide
    passe la main au suivant plutot que de rendre le silence - un dossier qui
    n'a que `contre.mp3` et `corne.mp3` joue `corne.mp3` le reste du temps.

    Les paires de `--sound-for` entrent aux memes etages, et y couvrent ce que
    le dossier propose : a etage egal, ce qui a ete nomme l'emporte sur ce qui
    a ete devine dans un nom de fichier. C'est le seul arbitrage qui se defend
    devant quelqu'un qui a ecrit `--sound-for om=cri.wav` en ayant deja un
    `om.mp3` dans son dossier - il vient de dire lequel il voulait.

    Sans contexte (`--test`, une carte muette), rien ne change : tout le
    dossier est candidat, comme avant. Un son nomme, lui, ne sort pas : il
    designe une equipe ou une competition, et il n'y a la aucun but a qui les
    comparer.
    """
    files = list(files)
    if context is None:
        return files
    pools = sounds_by_tier(files, context)
    named = named_by_tier(assigned, context, on_missing)
    for tier in TIERS:
        if named[tier]:
            pools[tier] = named[tier]
    for tier in TIERS:
        if pools[tier]:
            return pools[tier]
    return []


def declared(path, clubs=()) -> tuple:
    """Ce qu'un nom de fichier annonce sans match sous la main : (etage, cible).

    Sert a `--status`, qui doit dire ce qui est arme avant le prochain but.
    Faute de match, l'etage equipe ne se reconnait qu'au vocabulaire de
    names_a_club() ; un nom de club inconnu passe donc pour du fond sonore, et
    n'en jouera pas moins pour son equipe le jour ou elle marque.
    """
    for name in name_candidates(path):
        if is_conceded_word(name):
            return (TIER_CONCEDED, None)
        found = leagues.designates(name)
        if found is not None:
            return (TIER_LEAGUE, found)
        if Context(clubs=clubs).names_a_club(name):
            return (TIER_TEAM, name)
    return (TIER_GENERAL, None)


def pick_sound(cache_wav: Path, custom_dir: Path, volume: float = 0.55,
               context=None, assigned=(), on_missing=None) -> Path:
    """Son a jouer : perso d'abord, puis celui fourni, puis la corne synthetisee.

    `context` (sound.Context) laisse le nom des fichiers designer une equipe,
    une competition ou un but encaisse ; sans lui, tirage au hasard dans tout
    le dossier, comme avant. `assigned` porte les paires de `--sound-for`, et
    `on_missing(assignment, probleme)` est appele pour celle dont le fichier
    s'est evapore depuis le demarrage - le son suivant prend le relais, il n'y
    a pas de raison de se taire pour autant.
    """
    customs = armed_sounds(custom_sounds(custom_dir), context, assigned,
                           on_missing)
    if customs:
        return random.choice(customs)

    default = bundled_sound()
    if default is not None and (sys.platform == "win32" or find_player(default)):
        return default

    return ensure_wav(cache_wav, volume)


# --------------------------------------------------------------- lecture -----

def _mci(command: str):
    """Envoie une commande MCI (Windows). Gere le mp3 et compagnie."""
    import ctypes

    buffer = ctypes.create_unicode_buffer(512)
    code = ctypes.windll.winmm.mciSendStringW(command, buffer, 511, 0)
    return code, buffer.value


def find_player(path: Path | None = None):
    """Commande de lecture adaptee au fichier, ou None.

    Windows n'en a pas besoin (winsound / MCI sont integres).
    """
    if sys.platform == "win32":
        return None
    if sys.platform == "darwin":
        return ["afplay"] if shutil.which("afplay") else None

    compressed = path is not None and path.suffix.lower() != ".wav"
    for binary, command, formats in LINUX_PLAYERS:
        if compressed and formats != "any":
            continue
        if shutil.which(binary):
            return command
    return None


def play_async(path: Path):
    """Lance le son sans bloquer. Silencieux si aucun lecteur n'est dispo."""
    path = Path(path)

    if sys.platform == "win32":
        if path.suffix.lower() == ".wav":
            try:
                import winsound

                winsound.PlaySound(
                    str(path),
                    winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT,
                )
                return "winsound"
            except Exception:
                return None
        # mp3, m4a, wma... : MCI sait faire, sans dependance externe
        try:
            _mci("close " + MCI_ALIAS)
            code, _ = _mci('open "{}" alias {}'.format(path, MCI_ALIAS))
            if code != 0:
                return None
            _mci("play " + MCI_ALIAS)
            return "mci"
        except Exception:
            return None

    command = find_player(path)
    if not command:
        return None
    try:
        return subprocess.Popen(
            command + [str(path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
        )
    except Exception:
        return None


def release(handle) -> None:
    """Libere les ressources SANS couper le son en cours.

    La carte peut disparaitre avant la fin du jingle : on le laisse aller au
    bout plutot que de le tronquer.
    """
    if handle == "mci":
        # MCI garde le fichier ouvert : on ne ferme qu'a la lecture suivante.
        return
    return


def stop_all() -> None:
    """Coupe net tout son en cours (arret du programme)."""
    if sys.platform == "win32":
        try:
            import winsound

            winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception:
            pass
        try:
            _mci("close " + MCI_ALIAS)
        except Exception:
            pass


# --------------------------------------------------------------- duree -------

def probe_duration(path: Path):
    """Duree du fichier en secondes, ou None si on ne sait pas la lire."""
    path = Path(path)

    if path.suffix.lower() == ".wav":
        try:
            with wave.open(str(path), "rb") as handle:
                rate = handle.getframerate()
                if rate:
                    return handle.getnframes() / float(rate)
        except Exception:
            return None
        return None

    if sys.platform == "win32":
        try:
            alias = MCI_ALIAS + "probe"
            _mci("close " + alias)
            code, _ = _mci('open "{}" alias {}'.format(path, alias))
            if code != 0:
                return None
            _mci("set {} time format milliseconds".format(alias))
            code, value = _mci("status {} length".format(alias))
            _mci("close " + alias)
            if code == 0 and value.strip().isdigit():
                return int(value.strip()) / 1000.0
        except Exception:
            return None
        return None

    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        try:
            out = subprocess.run(
                [ffprobe, "-v", "quiet", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
                capture_output=True, text=True, timeout=5,
            )
            return float(out.stdout.strip())
        except Exception:
            return None
    return None
