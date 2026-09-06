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

from . import (__version__, config, crests, espn, fullscreen, journal,
               leagues, screens, sound, state, teams, watcher)

DEFAULT_INTERVAL = 25          # secondes, quand un match est en cours
DEFAULT_IDLE_INTERVAL = 300    # secondes, quand il n'y a rien a suivre
DEFAULT_DURATION = 6.0         # duree d'affichage minimale de la carte
PHASE_DURATION = 5.0           # coup d'envoi, mi-temps, reprise, fin : sans son
DEFAULT_VOLUME = 0.55
DEFAULT_POSITION = "bottom-right"
RETRY_FULLSCREEN = 120.0       # duree d'attente par defaut de --retry-fullscreen


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
        "logos": root / "logos",
        "wav": root / "but.wav",
        "log": root / "butbutbut.log",
        "pid": root / "butbutbut.pid",
        "config": root / config.FILENAME,
        "state": root / "butbutbut.json",
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


def crest_cache(args, on_log=None):
    """Le cache d'ecussons, ou un cache eteint avec --no-logos.

    Toujours un objet, jamais None : c'est lui qui decide de ne rien faire,
    l'appelant n'a pas a s'en soucier a chaque but.
    """
    return crests.Cache(paths()["logos"], enabled=not args.no_logos,
                        on_log=on_log or (lambda message: None))


def team_filter(args):
    """Le filtre par equipe, ou None s'il n'y a rien a filtrer."""
    chosen = teams.Filter(args.teams, args.exclude_teams)
    return chosen if chosen.active else None


def check_teams(args, selection) -> int:
    """Confronte --teams / --exclude-teams au catalogue des competitions.

    Un mot qui ne designe aucune equipe est une faute de frappe : mieux vaut
    le dire tout de suite que de laisser le daemon rester muet pour toujours.
    """
    chosen = team_filter(args)
    if chosen is None:
        return 0

    catalogue = []
    for league in selection:
        catalogue.extend(espn.catalogue(league))
        time.sleep(0.15)

    if not catalogue:
        print("butbutbut : impossible de verifier les equipes (source "
              "injoignable), on continue sans verification.", file=sys.stderr)
        return 0

    found, orphans = chosen.resolve(catalogue)
    for token in sorted(found):
        clubs = found[token]
        extra = "" if len(clubs) == 1 else "  ({} clubs)".format(len(clubs))
        print("  {:<16} -> {}{}".format(token, ", ".join(clubs), extra))
    if orphans:
        print("butbutbut : aucune equipe ne correspond a {} dans {}. "
              "Voir 'butbutbut --list-teams'.".format(
                  ", ".join(repr(o) for o in orphans),
                  leagues.describe(selection)), file=sys.stderr)
        return 2
    return 0


def do_list_teams(args) -> int:
    """Les equipes des competitions suivies, avec ce que le filtre attrape."""
    selection = leagues.resolve(args.leagues, args.exclude)
    chosen = team_filter(args)

    for league in selection:
        catalogue = espn.catalogue(league)
        print()
        print("{} - {} equipe(s)".format(league.name, len(catalogue)))
        if not catalogue:
            print("  (la source ne publie pas de liste pour cette competition)")
            continue
        for names in catalogue:
            mark = " "
            if chosen is not None:
                if chosen.team_excluded(names):
                    mark = "-"
                elif chosen.team_matches(names):
                    mark = "*"
            print("  {} {:<30} {}".format(mark, names[0], names[-1]))
        time.sleep(0.15)

    print()
    if chosen is not None:
        print("'*' = suivie, '-' = exclue.")
    print("Exemples :")
    print("  butbutbut --teams om,psg")
    print("  butbutbut --teams \"real madrid\" --leagues liga,ucl")
    print("  butbutbut --exclude-teams psg")
    return 0


# --------------------------------------------------------------- actions -----

def do_daemon(args) -> int:
    from . import overlay

    selection = leagues.resolve(args.leagues, args.exclude)

    if not claim_pid_file():
        log("une instance tourne deja (pid {}), sortie.".format(running_pid()),
            quiet=args.quiet)
        return 1

    chosen_teams = team_filter(args)
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
        teams=chosen_teams,
        red_cards=args.red_cards,
        before_kickoff=args.before_kickoff * 60.0,
    )

    log("demarrage (pid {}) - {} - releve toutes les {}s en direct, {}s au repos"
        .format(os.getpid(), leagues.describe(selection), args.interval,
                args.idle_interval), quiet=args.quiet)
    if chosen_teams is not None:
        log(chosen_teams.describe(), quiet=args.quiet)
    if args.red_cards:
        log("cartons rouges signales", quiet=args.quiet)
    if args.before_kickoff:
        log("annonce du coup d'envoi {} min avant".format(args.before_kickoff),
            quiet=args.quiet)
    log("pour tout arreter : butbutbut --stop", quiet=args.quiet)

    guard.prime()
    log(_startup_summary(guard), quiet=args.quiet)

    # L'etat est publie des le premier releve : sinon un --status lance dans la
    # foulee du demarrage annoncerait un daemon sans aucune activite.
    reporter = state.Reporter(paths()["state"], leagues=selection,
                              interval=args.interval,
                              idle_interval=args.idle_interval)
    reporter.update(guard.all_matches())

    stack = None
    if not args.no_overlay:
        try:
            stack = overlay.Stack(
                screen=args.screen, position=args.position, opacity=args.opacity,
                scale=args.scale, retry_fullscreen=args.retry_fullscreen,
                on_log=lambda message: log(message, quiet=args.quiet)).open()
            log("cartes empilees en {} de {}".format(
                args.position,
                "l'ecran principal" if args.screen is None
                else "l'ecran {}".format(args.screen)), quiet=args.quiet)
        except overlay.TkinterMissing as exc:
            log(str(exc), quiet=args.quiet)
            log("pas de carte : on continue au son et au journal", quiet=args.quiet)

    crest = crest_cache(args, on_log=lambda message: log(message, quiet=args.quiet))

    try:
        if stack is None:
            _watch_headless(guard, args, stopping, reporter)
        else:
            _watch_with_cards(guard, args, stopping, stack, reporter, crest)
    except KeyboardInterrupt:
        log("arret demande.", quiet=args.quiet)
    finally:
        stopping.set()
        if stack is not None:
            stack.close()
        crest.join(2.0)
        sound.stop_all()
        release_pid_file()
        # L'etat s'en va avec le pid : garde, il ferait croire a des matchs en
        # cours des heures apres l'arret. Le journal, lui, reste.
        state.clear(paths()["state"])
        log("arret.", quiet=args.quiet)
    return 0


def _watch_headless(guard, args, stopping, reporter) -> None:
    """Sans carte : un seul fil, le son et le journal."""
    while not stopping.is_set():
        media = None
        events = guard.tick()
        reporter.update(guard.all_matches(), events)
        for event in events:
            log(event.log_line(), quiet=args.quiet)
            if not event.goal:
                continue            # but annule et phases de match : muets
            if media is None:
                media = resolve_sound(args)
            play_goal_sound(media[0])

        # plan_wait() et pas next_delay() : le watcher retient ce qu'on s'est
        # engage a attendre, et voit ainsi au tick suivant qu'on a dormi.
        stopping.wait(guard.plan_wait())


def _watch_with_cards(guard, args, stopping, stack, reporter, crest=None) -> None:
    """Avec cartes : tkinter garde le fil principal, la surveillance a le sien.

    tkinter n'aime pas etre touche depuis un autre fil : le fil de surveillance
    ne fait que du reseau et du journal, puis depose ses buts dans une file que
    la boucle tkinter vide toutes les PUMP_MS millisecondes.
    """
    from . import overlay

    pending = queue.Queue()

    def poll():
        while not stopping.is_set():
            try:
                events = guard.tick()
                reporter.update(guard.all_matches(), events)
                for event in events:
                    log(event.log_line(), quiet=args.quiet)
                    pending.put(event)
            except Exception as exc:
                log("erreur de surveillance : {}".format(exc), quiet=args.quiet)
            stopping.wait(guard.plan_wait())

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
                if event.sober:
                    if event.phase and args.no_phase_cards:
                        continue    # le journal garde la trace, pas l'ecran
                    # Temps forts, expulsion, avant-match : carte seule, pas de
                    # son. La duree ne depend donc pas de celle du jingle.
                    stack.push(overlay.Card.from_event(event, crest),
                               duration=args.duration or PHASE_DURATION)
                    continue

                if media is None:
                    media = resolve_sound(args)
                stack.push(overlay.Card.from_event(event, crest), duration=media[1])
                if event.goal:
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


def do_test(args) -> int:
    from . import overlay

    selection = leagues.resolve(args.leagues, args.exclude)
    count = max(1, int(args.test))
    # Les ecussons qui manquent partent se telecharger : le prochain --test les
    # aura. Celui-ci s'affiche sans attendre, exactement comme un vrai but.
    crest = crest_cache(args)
    cards = [overlay.Card.demo(selection[i % len(selection)], crest)
             for i in range(count)]

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
                     opacity=args.opacity, scale=args.scale,
                     retry_fullscreen=args.retry_fullscreen,
                     on_log=lambda message: print("butbutbut : {}".format(message)))
    except overlay.TkinterMissing as exc:
        print(str(exc), file=sys.stderr)
        return 4
    finally:
        # On laisse finir les ecussons partis en fond : sinon la demo,
        # toujours tuee juste apres, ne les aurait jamais.
        crest.join(3.0)
    return 0


def do_scores(args) -> int:
    selection = leagues.resolve(args.leagues, args.exclude)
    chosen = team_filter(args)
    now = datetime.now(timezone.utc)
    total = 0

    for league in selection:
        try:
            matches = espn.scoreboard(league)
        except espn.SourceError as exc:
            print("{:<16} {}".format(league.name, "injoignable ({})".format(exc)))
            continue

        if chosen is not None:
            matches = [match for match in matches if chosen.matches(match)]

        print("\n{}".format(league.name))
        if not matches:
            print("  (aucun match au programme)"
                  if chosen is None else "  (aucun match de ces equipes)")
            continue

        for match in matches:
            total += 1
            # 'note' et non 'state' : le module state est importe ici.
            if match.live:
                mark, note = ">", match.detail or match.clock or "en cours"
            elif match.finished:
                mark, note = " ", match.detail or "termine"
            else:
                mark, note = " ", _kickoff_text(match, now)
            print("  {} {:>22} {} - {} {:<22} {}".format(
                mark, match.home, match.home_score, match.away_score,
                match.away, note))
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


def _print_activity(pid) -> None:
    """L'activite du daemon, relue dans le fichier d'etat.

    Le fichier pid dit qu'un processus existe, jamais qu'il travaille : sans
    ces lignes, un daemon bloque sur une requete est indistinguable d'un daemon
    qui suit trois matchs.
    """
    data = state.read(paths()["state"])
    if data is None:
        print("  releve      : {}".format(
            "aucun pour l'instant" if pid
            else "aucun (le daemon efface son etat en s'arretant)"))
        return

    stale = state.is_stale(data)
    line = state.describe_age(state.age(data))
    stamp = data.get("updated_text")
    if stamp:
        line += "  ({})".format(stamp)
    print("  releve      : {}".format(line))
    if not pid:
        print("                etat laisse par un daemon qui ne tourne plus")
    elif stale:
        print("                (!) plus rien depuis, alors que la cadence est "
              "de {}s : daemon bloque ou source injoignable ?".format(
                  _announced_cadence(data)))

    if stale:
        # Un etat perime decrit un match fini depuis longtemps : annoncer une
        # mi-temps d'hier soir serait pire que de ne rien annoncer.
        print("  en cours    : inconnu (le dernier releve est trop vieux)")
    else:
        matches = [row for row in (data.get("matches") or [])
                   if isinstance(row, dict)]
        summary = "{} match(s)".format(len(matches))
        if isinstance(data.get("total_matches"), int):
            summary += " sur {} au programme".format(data["total_matches"])
        print("  en cours    : {}".format(summary))
        for row in matches:
            print("                [{}] {} {} - {} {}  {}".format(
                row.get("league", "?"), row.get("home", "?"),
                row.get("home_score", "?"), row.get("away_score", "?"),
                row.get("away", "?"), row.get("clock", "")).rstrip())

    goals = data.get("goals_today", 0) if data.get("day") == state.today() else 0
    print("  buts du jour: {}  (le detail : butbutbut --today)".format(goals))


def _announced_cadence(data):
    key = "interval" if data.get("matches") else "idle_interval"
    return data.get(key, "?")


def do_today(args) -> int:
    """Le recapitulatif de la journee, relu dans le journal."""
    p = paths()
    entries = journal.goals(p["log"])

    print("butbutbut : buts signales le {:%d/%m/%Y}".format(datetime.now()))
    if not entries:
        print("\n  (aucun but pour l'instant)")
        print("\nJournal : {}".format(p["log"]))
        return 0

    scored = 0
    cancelled = 0
    grouped = journal.by_league(entries)
    for league, rows in grouped:
        print("\n{}".format(league))
        for entry in rows:
            if entry.goal:
                scored += 1
            else:
                cancelled += 1
            detail = " ".join(part for part in (
                entry.detail,
                "({})".format(entry.minute) if entry.minute else "") if part)
            print("  {} {}  {:<34} {}".format(
                " " if entry.goal else "-", entry.time,
                entry.score_line(), detail).rstrip())

    print("\n{} but(s) dans {} competition(s).".format(scored, len(grouped)))
    if cancelled:
        print("'-' = but retire par la VAR ({}).".format(cancelled))
    return 0


def do_status(args) -> int:
    p = paths()
    pid = running_pid()
    selection = leagues.resolve(args.leagues, args.exclude)

    print("butbutbut {}".format(__version__))
    print("  daemon      : {}".format(
        "actif (pid {})".format(pid) if pid else "arrete"))
    _print_activity(pid)
    chosen = team_filter(args)
    if chosen is not None:
        print("  equipes     : {}".format(chosen.describe()))
    summary = leagues.describe(selection)
    names = ", ".join(league.name for league in selection)
    print("  suivi       : {}".format(summary))
    if names != summary and len(selection) <= 10:
        print("  competitions: {}".format(names))
    print("  source      : ESPN scoreboard (public, sans cle)")
    print("  cadence     : {}s en direct / {}s au repos".format(
        args.interval, args.idle_interval))
    print("  donnees     : {}".format(p["data"]))
    settings = Path(getattr(args, "config", None) or p["config"])
    print("  config      : {}{}".format(
        settings, "" if settings.exists() else "  (absent, voir --write-config)"))

    sounds = sound.custom_sounds(p["sound"])
    if sounds:
        extra = " (+{} autre(s), tirage au hasard)".format(len(sounds) - 1) if len(sounds) > 1 else ""
        print("  son         : {}{}".format(sounds[0].name, extra))
    else:
        chosen = sound.pick_sound(p["wav"], p["sound"])
        origin = "fourni" if chosen == sound.BUNDLED_SOUND else "corne synthetisee"
        print("  son         : {} ({})".format(chosen.name, origin))
    print("  sons perso  : {}  ({} fichier(s))".format(p["sound"], len(sounds)))

    cached = crest_cache(args).cached()
    print("  ecussons    : {}".format(
        "desactives (--no-logos)" if args.no_logos
        else "{}  ({} en cache)".format(p["logos"], len(cached))))

    found = screens.monitors()
    print("  ecrans      : {} -> carte en {} sur {}".format(
        screens.describe(found), args.position,
        "l'ecran principal" if args.screen is None else "ecran {}".format(args.screen)))
    print("  plein ecran : {}".format(
        "detecte (la carte masquee est notee au journal)"
        if fullscreen.supported()
        else "non detectable sur cette plateforme"))
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


def do_check_update(args) -> int:
    from . import update

    print("butbutbut {}".format(__version__))
    return update.check()


def do_update(args) -> int:
    from . import update

    print("butbutbut {} - mise a jour".format(__version__))
    return update.update()


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
        # Sous Windows le daemon est tue net : son finally ne tourne pas, et
        # personne d'autre ne viendrait ramasser son etat.
        state.clear(paths()["state"])
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
                        help="affiche l'etat (daemon, dernier releve, matchs "
                             "en cours, son, ecrans, connexion)")
    parser.add_argument("--today", action="store_true",
                        help="recapitule les buts signales aujourd'hui")
    parser.add_argument("--stop", action="store_true", help="arrete le daemon en cours")
    parser.add_argument("--paths", action="store_true", help="affiche les chemins utilises")
    parser.add_argument("--screens", action="store_true", help="liste les ecrans detectes")
    parser.add_argument("--update", action="store_true",
                        help="met a jour butbutbut depuis GitHub et rejoue l'installeur")
    parser.add_argument("--check-update", action="store_true",
                        dest="check_update",
                        help="dit si une version plus recente existe, sans rien installer")

    parser.add_argument("--config", default=None, metavar="CHEMIN",
                        help="fichier de configuration a lire (defaut : {} dans "
                             "le dossier de donnees, voir 'butbutbut --paths')"
                        .format(config.FILENAME))
    parser.add_argument("--write-config", action="store_true", dest="write_config",
                        help="ecrit un fichier de configuration d'exemple, "
                             "commente, puis quitte (n'ecrase rien)")

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
    parser.add_argument("--teams", default=None, metavar="LISTE",
                        help="ne signaler que les matchs de ces equipes, "
                             "separees par des virgules. Un match compte des "
                             "qu'une des deux equipes y est. Ex : --teams om,psg")
    parser.add_argument("--exclude-teams", default=None, metavar="LISTE",
                        dest="exclude_teams",
                        help="ne rien signaler des matchs de ces equipes")
    parser.add_argument("--list-teams", action="store_true", dest="list_teams",
                        help="liste les equipes des competitions suivies")
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
    parser.add_argument("--no-phase-cards", action="store_true",
                        dest="no_phase_cards",
                        help="pas de carte au coup d'envoi, a la mi-temps, a la "
                             "reprise ni a la fin du match (les buts, si)")
    parser.add_argument("--retry-fullscreen", nargs="?", type=float,
                        const=RETRY_FULLSCREEN, default=0.0, metavar="SECONDES",
                        dest="retry_fullscreen",
                        help="quand une application en plein ecran masque "
                             "l'ecran, repasser la carte des que l'ecran se "
                             "libere, pendant SECONDES au plus (defaut {:.0f} ; "
                             "Windows uniquement, voir README)".format(
                                 RETRY_FULLSCREEN))
    parser.add_argument("--red-cards", action="store_true", dest="red_cards",
                        help="signale aussi les cartons rouges, par une carte "
                             "discrete et sans son")
    parser.add_argument("--before-kickoff", type=int, default=0,
                        dest="before_kickoff", metavar="MINUTES",
                        help="annonce le match ce nombre de minutes avant le "
                             "coup d'envoi, une seule fois et sans son "
                             "(0 = desactive, defaut)")
    parser.add_argument("--no-logos", action="store_true", dest="no_logos",
                        help="pas d'ecusson sur les cartes, et rien de "
                             "telecharge (les couleurs des clubs restent)")
    parser.add_argument("--no-sound", action="store_true", dest="no_sound",
                        help="mode muet")
    parser.add_argument("--volume", type=float, default=DEFAULT_VOLUME,
                        help="volume de la corne synthetisee, 0.0 a 1.0")
    parser.add_argument("--regen-sound", action="store_true", dest="regen_sound",
                        help="regenere la corne synthetisee")
    parser.add_argument("--quiet", action="store_true", help="n'ecrit que dans le journal")
    return parser


def main(argv=None) -> int:
    parser = build_parser()

    # Le fichier alimente les defauts du parseur avant l'analyse : la ligne de
    # commande, analysee ensuite, l'emporte donc toujours. Voir config.apply().
    chosen = config.path_from(argv, paths()["config"])
    for warning in config.apply(parser, chosen).warnings:
        print("butbutbut : {}".format(warning), file=sys.stderr)

    args = parser.parse_args(argv)
    args.config = chosen        # le chemin retenu, pour --status et --write-config

    if args.write_config:
        # Un parseur neuf : le fichier d'exemple annonce les vrais defauts du
        # programme, pas ceux qu'un fichier deja present vient d'installer.
        written, message = config.write_example(chosen, build_parser())
        print("butbutbut : {}".format(message),
              file=sys.stdout if written else sys.stderr)
        return 0 if written else 1

    args.interval = max(5, args.interval)
    args.idle_interval = max(args.interval, args.idle_interval)
    args.retry_fullscreen = max(0.0, args.retry_fullscreen or 0.0)
    if args.retry_fullscreen and not fullscreen.supported():
        # Mieux vaut le dire que laisser croire a un filet de securite.
        print("butbutbut : --retry-fullscreen ne sert que sous Windows, "
              "le plein ecran n'y est pas detectable ailleurs.", file=sys.stderr)
        args.retry_fullscreen = 0.0
    args.before_kickoff = max(0, args.before_kickoff)
    if args.position.strip().lower() not in screens.CORNERS:
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
        p["logos"].mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        print("butbutbut : dossier de donnees inutilisable : {}".format(exc),
              file=sys.stderr)

    if args.regen_sound:
        sound.ensure_wav(p["wav"], args.volume, force=True)
        print("butbutbut : corne regeneree -> {}".format(p["wav"]))

    if args.list_leagues:
        return do_list(args)
    if args.list_teams:
        return do_list_teams(args)
    if args.teams or args.exclude_teams:
        failed = check_teams(args, leagues.resolve(args.leagues, args.exclude))
        if failed:
            return failed

    if args.screens:
        return do_screens(args)
    if args.paths:
        return do_paths(args)
    if args.check_update:
        return do_check_update(args)
    if args.update:
        return do_update(args)
    if args.stop:
        return do_stop(args)
    if args.status:
        return do_status(args)
    if args.today:
        return do_today(args)
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
