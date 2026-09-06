"""Le son du but : lecture multiplateforme, avec repli synthetise.

Ordre de priorite :
  1. un fichier depose dans <data_dir>/sound/  (`butbutbut --paths` donne le chemin)
  2. le son fourni avec butbutbut (butbutbut/assets/but.mp3)
  3. une corne de stade synthetisee ici meme, utilisee quand rien sur la
     machine ne sait lire le mp3 (Linux minimal sans mpv/ffmpeg/sox/vlc)

Formats acceptes : wav, mp3, ogg, opus, flac, m4a, aac.
"""

from __future__ import annotations

import math
import random
import shutil
import struct
import subprocess
import sys
import wave
from pathlib import Path

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


def pick_sound(cache_wav: Path, custom_dir: Path, volume: float = 0.55) -> Path:
    """Son a jouer : perso d'abord, puis celui fourni, puis la corne synthetisee."""
    customs = custom_sounds(custom_dir)
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
