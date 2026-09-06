"""Ligne de commande et boucle de fond de butbutbut."""

from __future__ import annotations

import argparse
import ctypes
import os
import queue
import signal
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from . import __version__, espn, leagues, sound, watcher

DEFAULT_INTERVAL = 25          # secondes, quand un match est en cours
DEFAULT_IDLE_INTERVAL = 300    # secondes, quand il n'y a rien a suivre
DEFAULT_DURATION = 6.0         # duree d'affichage minimale de la carte
DEFAULT_VOLUME = 0.55
DEFAULT_POSITION = "bottom-right"


# --------------------------------------------------------------- chemins -----

def data_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")
        return Path(base) / "butbutbut"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "butbutbut"
    base = os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share")
    return Path(base) / "butbutbut"


def paths() -> dict:
    root = data_dir()
    return {
        "data": root,
        "sound": root / "sound",
        "wav": root / "but.wav",
        "log": root / "butbutbut.log",
        "pid": root / "butbutbut.pid",
    }


def log(message: str, quiet: bool = False) -> None:
    line = "{:%Y-%m-%d %H:%M:%S}  {}".format(datetime.now(), message)
    try:
        path = paths()["log"]
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except Exception:
        pass
    if not quiet:
        try:
            print(line, flush=True)
        except Exception:
            pass


# ------------------------------------------------------- instance unique -----

def _process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        SYNCHRONIZE = 0x00100000
        handle = ctypes.windll.kernel32.OpenProcess(SYNCHRONIZE, False, pid)
        if not handle:
            return False
        ctypes.windll.kernel32.CloseHandle(handle)
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def running_pid():
    pid_file = paths()["pid"]
    try:
        pid = int(pid_file.read_text().strip())
    except Exception:
        return None
    return pid if _process_alive(pid) else None


def claim_pid_file() -> bool:
    existing = running_pid()
    if existing and existing != os.getpid():
        return False
    pid_file = paths()["pid"]
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(str(os.getpid()))
    return True


def release_pid_file() -> None:
    try:
        paths()["pid"].unlink()
    except Exception:
        pass


# ---------------------------------------------------------------- media ------

def resolve_sound(args):
    """(chemin du son, duree d'affichage). Relu a chaque but.

    Tu peux deposer un mp3 dans <data>/sound pendant que le daemon tourne : il
    le prendra au but suivant, sans redemarrage.
    """
    p = paths()

    chosen = None
    if not args.no_sound:
        try:
            chosen = sound.pick_sound(p["wav"], p["sound"], args.volume)
        except Exception as exc:
            log("son indisponible : {}".format(exc), quiet=args.quiet)

    duration = args.duration
    if duration is None:
        duration = DEFAULT_DURATION
        if chosen is not None:
            length = sound.probe_duration(chosen)
            if length:
                duration = max(DEFAULT_DURATION, length + 0.6)
    return chosen, duration


_last_sound_at = 0.0


def play_goal_sound(path, min_gap: float = 2.0):
    """Joue le son, mais pas deux fois coup sur coup.

    Deux buts remontes par le meme releve arrivent a quelques millisecondes
    d'ecart : un seul coup de corne, et deux cartes empilees a l'ecran. Sans ce
    garde-fou, le second son couperait le premier.
    """
    global _last_sound_at

    if path is None:
        return None
    now = time.monotonic()
    if now - _last_sound_at < min_gap:
        return None
    _last_sound_at = now
    return sound.play_async(path)


# --------------------------------------------------------------- actions -----

def do_daemon(args) -> int:
    from . import overlay

    selection = leagues.resolve(args.leagues, args.exclude)

    if not claim_pid_file():
        log("une instance tourne deja (pid {}), sortie.".format(running_pid()),
            quiet=args.quiet)
        return 1

    stopping = threading.Event()

    def request_stop(_signum, _frame):
        stopping.set()

    for name in ("SIGTERM", "SIGINT"):
        try:
            signal.signal(getattr(signal, name), request_stop)
        except Exception:
            pass

    guard = watcher.Watcher(
        selection,
        interval=args.interval,
        idle_interval=args.idle_interval,
        on_log=lambda message: log(message, quiet=args.quiet),
    )

    log("demarrage (pid {}) - {} - releve toutes les {}s en direct, {}s au repos"
        .format(os.getpid(), leagues.describe(selection), args.interval,
                args.idle_interval), quiet=args.quiet)
    log("pour tout arreter : butbutbut --stop", quiet=args.quiet)

    guard.prime()
    log(_startup_summary(guard), quiet=args.quiet)

    stack = None
    if not args.no_overlay:
        try:
            stack = overlay.Stack(screen=args.screen, position=args.position,
                                  opacity=args.opacity, scale=args.scale).open()
            log("cartes empilees en {} de {}".format(
                args.position,
                "l'ecran principal" if args.screen is None
                else "l'ecran {}".format(args.screen)), quiet=args.quiet)
        except overlay.TkinterMissing as exc:
            log(str(exc), quiet=args.quiet)
            log("pas de carte : on continue au son et au journal", quiet=args.quiet)

    try:
        if stack is None:
            _watch_headless(guard, args, stopping)
        else:
            _watch_with_cards(guard, args, stopping, stack)
    except KeyboardInterrupt:
        log("arret demande.", quiet=args.quiet)
    finally:
        stopping.set()
        if stack is not None:
            stack.close()
        sound.stop_all()
        release_pid_file()
        log("arret.", quiet=args.quiet)
    return 0


def _watch_headless(guard, args, stopping) -> None:
    """Sans carte : un seul fil, le son et le journal."""
    live_ids = {m.id for m in guard.live_matches()}

    while not stopping.is_set():
        media = None
        for event in guard.tick():
            log(event.log_line(), quiet=args.quiet)
            if media is None:
                media = resolve_sound(args)
            play_goal_sound(media[0])

        live_ids = _log_kickoffs(guard, live_ids, args)
        stopping.wait(guard.next_delay())


def _watch_with_cards(guard, args, stopping, stack) -> None:
    """Avec cartes : tkinter garde le fil principal, la surveillance a le sien.

    tkinter n'aime pas etre touche depuis un autre fil : le fil de surveillance
    ne fait que du reseau et du journal, puis depose ses buts dans une file que
    la boucle tkinter vide toutes les PUMP_MS millisecondes.
    """
    from . import overlay

    pending = queue.Queue()

    def poll():
        live_ids = {m.id for m in guard.live_matches()}
        while not stopping.is_set():
            try:
                for event in guard.tick():
                    log(event.log_line(), quiet=args.quiet)
                    pending.put(event)
                live_ids = _log_kickoffs(guard, live_ids, args)
            except Exception as exc:
                log("erreur de surveillance : {}".format(exc), quiet=args.quiet)
            stopping.wait(guard.next_delay())

    thread = threading.Thread(target=poll, name="butbutbut-watch", daemon=True)
    thread.start()

    def drain():
        media = None
        while True:
            try:
                event = pending.get_nowait()
            except queue.Empty:
                break
            try:
                if media is None:
                    media = resolve_sound(args)
                stack.push(overlay.Card.from_event(event), duration=media[1])
                play_goal_sound(media[0])
            except Exception as exc:
                log("echec de l'affichage : {}".format(exc), quiet=args.quiet)

        if stopping.is_set():
            stack.stop()

    stack.every(overlay.PUMP_MS, drain)
    stack.run()


def _startup_summary(guard) -> str:
    matches = guard.all_matches()
    live = [m for m in matches if m.live]
    upcoming = [m for m in matches if m.state == espn.PRE]
    parts = ["{} match(s) au programme".format(len(matches))]
    if live:
        parts.append("{} en cours".format(len(live)))
    if upcoming:
        parts.append("{} a venir".format(len(upcoming)))
    line = ", ".join(parts)
    for match in live:
        line += "\n           en cours : [{}] {} ({})".format(
            match.league.name, match.score_line(), match.detail or match.clock)
    return line


def _log_kickoffs(guard, previous_ids, args):
    """Signale dans le journal les matchs qui commencent et ceux qui finissent."""
    current = guard.live_matches()
    current_ids = {m.id for m in current}

    for match in current:
        if match.id not in previous_ids:
            log("coup d'envoi [{}] {} - {}".format(
                match.league.name, match.home, match.away), quiet=args.quiet)

    for match in guard.all_matches():
        if match.id in previous_ids and match.id not in current_ids:
            log("fin du match [{}] {} ({})".format(
                match.league.name, match.score_line(), match.detail or "FT"),
                quiet=args.quiet)

    return current_ids


def do_test(args) -> int:
    from . import overlay

    selection = leagues.resolve(args.leagues, args.exclude)
    count = max(1, int(args.test))
    cards = [overlay.Card.demo(selection[i % len(selection)]) for i in range(count)]

    for card in cards:
        print("butbutbut : demo - [{}] {} - {}".format(
            card.league, card.text_line(), card.detail))

    path, duration = resolve_sound(args)

    if args.no_overlay:
        handle = play_goal_sound(path)
        time.sleep(min(duration, 5.0))
        sound.release(handle)
        return 0

    try:
        overlay.show(cards, duration=duration, sound_path=path,
                     screen=args.screen, position=args.position,
                     opacity=args.opacity, scale=args.scale)
    except overlay.TkinterMissing as exc:
        print(str(exc), file=sys.stderr)
        return 4
    return 0


def do_scores(args) -> int:
    selection = leagues.resolve(args.leagues, args.exclude)
    now = datetime.now(timezone.utc)
    total = 0

    for league in selection:
        try:
            matches = espn.scoreboard(league)
        except espn.SourceError as exc:
            print("{:<16} {}".format(league.name, "injoignable ({})".format(exc)))
            continue

        print("\n{}".format(league.name))
        if not matches:
            print("  (aucun match au programme)")
            continue

        for match in matches:
            total += 1
            if match.live:
                mark, state = ">", match.detail or match.clock or "en cours"
            elif match.finished:
                mark, state = " ", match.detail or "termine"
            else:
                mark, state = " ", _kickoff_text(match, now)
            print("  {} {:>22} {} - {} {:<22} {}".format(
                mark, match.home, match.home_score, match.away_score,
                match.away, state))
            for play in match.plays:
                side = match.home if play.team_id == match.home_id else match.away
                print("      {:<22} {}".format(side, play.summary()))

    print("\n{} match(s), '>' = en cours.".format(total))
    return 0


def _kickoff_text(match, now) -> str:
    remaining = match.seconds_until_kickoff(now)
    if remaining is None:
        return match.detail or "a venir"
    if remaining < 0:
        return match.detail or "imminent"
    if remaining < 3600:
        return "dans {} min".format(int(remaining // 60))
    local = match.start.astimezone()
    return "{:%d/%m %H:%M}".format(local)


def do_status(args) -> int:
    p = paths()
    pid = running_pid()
    selection = leagues.resolve(args.leagues, args.exclude)

    print("butbutbut {}".format(__version__))
    print("  daemon      : {}".format(
        "actif (pid {})".format(pid) if pid else "arrete"))
    summary = leagues.describe(selection)
    names = ", ".join(league.name for league in selection)
    print("  suivi       : {}".format(summary))
    if names != summary and len(selection) <= 10:
        print("  competitions: {}".format(names))
    print("  source      : ESPN scoreboard (public, sans cle)")
    print("  cadence     : {}s en direct / {}s au repos".format(
        args.interval, args.idle_interval))
    print("  donnees     : {}".format(p["data"]))

    sounds = sound.custom_sounds(p["sound"])
    if sounds:
        extra = " (+{} autre(s), tirage au hasard)".format(len(sounds) - 1) if len(sounds) > 1 else ""
        print("  son         : {}{}".format(sounds[0].name, extra))
    else:
        chosen = sound.pick_sound(p["wav"], p["sound"])
        origin = "fourni" if chosen == sound.BUNDLED_SOUND else "corne synthetisee"
        print("  son         : {} ({})".format(chosen.name, origin))
    print("  sons perso  : {}  ({} fichier(s))".format(p["sound"], len(sounds)))

    from . import screens

    found = screens.monitors()
    print("  ecrans      : {} -> carte en {} sur {}".format(
        screens.describe(found), args.position,
        "l'ecran principal" if args.screen is None else "ecran {}".format(args.screen)))
    print("  journal     : {}".format(p["log"]))

    if sys.platform == "win32":
        print("  lecteur     : winsound + MCI (integres)")
    else:
        player = sound.find_player()
        print("  lecteur     : {}".format(
            player[0] if player else "AUCUN (installe mpv/ffmpeg/pipewire/alsa-utils)"))
    try:
        import tkinter  # noqa: F401

        print("  affichage   : tkinter OK")
    except Exception:
        print("  affichage   : tkinter MANQUANT (voir README)")

    print("\n  Connexion   : ", end="", flush=True)
    try:
        matches = espn.scoreboard(selection[0])
        print("OK ({} : {} match(s))".format(selection[0].name, len(matches)))
    except espn.SourceError as exc:
        print("ECHEC ({})".format(exc))
        return 1
    return 0


def do_list(args) -> int:
    """Le catalogue des competitions, avec les noms acceptes."""
    print("butbutbut : competitions surveillables\n")
    for title, name, slug, alias in leagues.catalogue_lines():
        if title is not None:
            print("{}:".format(title))
            continue
        print("  {:<30} {:<24} {}".format(name, slug, alias))

    print("\nExemples :")
    print("  butbutbut --leagues l1,ucl,ligue2")
    print("  butbutbut --exclude liga,seriea        (les 5 grands moins deux)")
    print("  butbutbut --leagues all                (tout le catalogue)")
    print("  butbutbut --leagues por.1              (n'importe quel code ESPN)")
    return 0


def do_screens(args) -> int:
    from . import screens

    found = screens.monitors()
    print("butbutbut : {} ecran(s) detecte(s)".format(len(found)))
    for index, monitor in enumerate(found):
        tag = "  (principal)" if monitor.primary else ""
        print("  {}  {:<16} {}x{} a +{}+{}{}".format(
            index, monitor.name, monitor.width, monitor.height,
            monitor.x, monitor.y, tag))
    print("\nPar defaut la carte s'affiche en bas a droite de l'ecran principal.")
    print("La deplacer :  butbutbut --screen 1 --position top-right")
    return 0


def do_paths(args) -> int:
    for key, value in paths().items():
        print("{:6} {}".format(key, value))
    return 0


def do_stop(args) -> int:
    pid = running_pid()
    if not pid:
        print("butbutbut : aucun daemon en cours.")
        return 1
    try:
        if sys.platform == "win32":
            os.system("taskkill /PID {} /F >NUL 2>&1".format(pid))
        else:
            os.kill(pid, signal.SIGTERM)
        print("butbutbut : daemon {} arrete.".format(pid))
        release_pid_file()
        return 0
    except Exception as exc:
        print("butbutbut : impossible d'arreter {} : {}".format(pid, exc))
        return 1


# ---------------------------------------------------------------- parse ------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="butbutbut",
        description="Un but tombe en Ligue 1, Premier League, LaLiga, Serie A ou "
                    "Bundesliga : le son part et le score s'affiche a l'ecran.",
    )
    parser.add_argument("--version", action="version",
                        version="butbutbut {}".format(__version__))

    parser.add_argument("--test", nargs="?", type=int, const=1, default=0,
                        metavar="N",
                        help="affiche N cartes de demonstration puis quitte "
                             "(defaut 1 ; --test 3 montre l'empilement)")
    parser.add_argument("--scores", action="store_true",
                        help="affiche les matchs du jour dans le terminal puis quitte")
    parser.add_argument("--status", action="store_true",
                        help="affiche l'etat (daemon, son, ecrans, connexion)")
    parser.add_argument("--stop", action="store_true", help="arrete le daemon en cours")
    parser.add_argument("--paths", action="store_true", help="affiche les chemins utilises")
    parser.add_argument("--screens", action="store_true", help="liste les ecrans detectes")

    parser.add_argument("--leagues", default=None, metavar="LISTE",
                        help="competitions suivies, separees par des virgules "
                             "(defaut : les 5 grands championnats). Ex : "
                             "--leagues l1,pl,ucl ; 'all' pour tout le "
                             "catalogue ; un code ESPN marche aussi (por.1)")
    parser.add_argument("--exclude", default=None, metavar="LISTE",
                        help="competitions a ne pas suivre, meme syntaxe. Ex : "
                             "--exclude liga,seriea")
    parser.add_argument("--list", action="store_true", dest="list_leagues",
                        help="liste les competitions surveillables et leurs noms")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL,
                        help="secondes entre deux releves quand un match est en "
                             "cours (defaut {})".format(DEFAULT_INTERVAL))
    parser.add_argument("--idle-interval", type=int, default=DEFAULT_IDLE_INTERVAL,
                        dest="idle_interval",
                        help="secondes entre deux releves quand il n'y a rien a "
                             "suivre (defaut {})".format(DEFAULT_IDLE_INTERVAL))

    parser.add_argument("--duration", type=float, default=None,
                        help="duree d'affichage de la carte (defaut : la duree "
                             "du son, au moins {})".format(DEFAULT_DURATION))
    parser.add_argument("--position", default=DEFAULT_POSITION, metavar="COIN",
                        help="coin ou les cartes s'empilent : bottom-right "
                             "(defaut), bottom-left, top-right, top-left, center")
    parser.add_argument("--screen", default=None, metavar="CHOIX",
                        help="ecran d'affichage : 'primary' (defaut) ou un index "
                             "(0, 1, 2...). Voir 'butbutbut --screens'.")
    parser.add_argument("--scale", type=float, default=1.0,
                        help="taille de la carte (1.0 par defaut, 1.5 = plus grande)")
    parser.add_argument("--opacity", type=float, default=1.0, help="opacite, 0.0 a 1.0")
    parser.add_argument("--no-overlay", action="store_true", dest="no_overlay",
                        help="pas de carte : seulement le son et le journal")
    parser.add_argument("--no-sound", action="store_true", dest="no_sound",
                        help="mode muet")
    parser.add_argument("--volume", type=float, default=DEFAULT_VOLUME,
                        help="volume de la corne synthetisee, 0.0 a 1.0")
    parser.add_argument("--regen-sound", action="store_true", dest="regen_sound",
                        help="regenere la corne synthetisee")
    parser.add_argument("--quiet", action="store_true", help="n'ecrit que dans le journal")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    args.interval = max(5, args.interval)
    args.idle_interval = max(args.interval, args.idle_interval)
    if args.position.strip().lower() not in ("bottom-right", "bottom-left",
                                             "top-right", "top-left", "center"):
        print("butbutbut : position inconnue : {} (voir --help)".format(args.position),
              file=sys.stderr)
        return 2

    try:
        leagues.resolve(args.leagues, args.exclude)
    except leagues.SelectionError as exc:
        print("butbutbut : {}".format(exc), file=sys.stderr)
        return 2

    p = paths()
    try:
        p["data"].mkdir(parents=True, exist_ok=True)
        p["sound"].mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        print("butbutbut : dossier de donnees inutilisable : {}".format(exc),
              file=sys.stderr)

    if args.regen_sound:
        sound.ensure_wav(p["wav"], args.volume, force=True)
        print("butbutbut : corne regeneree -> {}".format(p["wav"]))

    if args.list_leagues:
        return do_list(args)
    if args.screens:
        return do_screens(args)
    if args.paths:
        return do_paths(args)
    if args.stop:
        return do_stop(args)
    if args.status:
        return do_status(args)
    if args.scores:
        return do_scores(args)
    if args.test:
        return do_test(args)

    try:
        return do_daemon(args)
    except Exception as exc:
        from .overlay import TkinterMissing

        if isinstance(exc, TkinterMissing):
            print(str(exc), file=sys.stderr)
            return 4
        raise


if __name__ == "__main__":
    raise SystemExit(main())
