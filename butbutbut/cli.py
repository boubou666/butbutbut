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
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from . import (__version__, config, crests, espn, fullscreen, i18n,
               journal, leagues, replay, screens, sound, state, teams, watcher)
# La prose de la ligne de commande : le francais est la cle, voir lang/.
from .i18n import tr

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


# Les chemins detournes le temps d'un rejeu. Vide en temps normal : voir
# sandbox_paths(), juste en dessous.
_REDIRECTED = {}

REPLAY_DIRNAME = "replay"


def paths() -> dict:
    root = data_dir()
    found = {
        "data": root,
        "sound": root / "sound",
        "logos": root / "logos",
        "wav": root / "but.wav",
        "log": root / "butbutbut.log",
        "pid": root / "butbutbut.pid",
        "config": root / config.FILENAME,
        "state": root / "butbutbut.json",
    }
    found.update(_REDIRECTED)
    return found


@contextmanager
def sandbox_paths(root):
    """Detourne le journal, l'etat et le pid vers `root`, le temps d'un bloc.

    C'est l'isolation du rejeu, et elle se prend ici plutot qu'a chaque appel.
    Un rejeu traverse expres les memes chemins qu'un vrai samedi soir : il
    ecrit donc un journal, publie un fichier d'etat et poserait un fichier pid.
    Or un match d'il y a trois semaines rejoue ce matin n'a rien a faire dans
    `--today`, un etat de rejeu ferait croire a `--status` que le daemon suit
    des matchs qui sont finis depuis longtemps, et le fichier pid ferait
    croire au vrai daemon qu'une instance tourne deja - ou l'inverse.

    Detourner les trois d'un bloc, a la racine, evite de trainer un chemin en
    parametre dans dix fonctions et surtout d'en oublier une : tout ce qui
    passe par paths() est isole, y compris le code qu'on ecrira demain.

    Ce qui n'est PAS detourne : le son et le cache d'ecussons. Ce sont des
    caches partages, en lecture pour l'essentiel, et les redetourner
    obligerait chaque rejeu a retelecharger tous les ecussons - alors qu'un
    rejeu est justement cense se passer de reseau.
    """
    global _REDIRECTED

    root = Path(root)
    try:
        root.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    previous = _REDIRECTED
    _REDIRECTED = {
        "log": root / "butbutbut.log",
        "pid": root / "butbutbut.pid",
        "state": root / "butbutbut.json",
    }
    try:
        yield paths()
    finally:
        _REDIRECTED = previous


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
        print(tr("butbutbut : impossible de verifier les equipes (source "
                 "injoignable), on continue sans verification."),
              file=sys.stderr)
        return 0

    found, orphans = chosen.resolve(catalogue)
    for token in sorted(found):
        clubs = found[token]
        extra = "" if len(clubs) == 1 else "  ({} clubs)".format(len(clubs))
        print(tr("  {:<16} -> {}{}", token, ", ".join(clubs), extra))
    if orphans:
        print(tr("butbutbut : aucune equipe ne correspond a {} dans {}. "
              "Voir 'butbutbut --list-teams'.", 
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
        print(tr("{} - {} equipe(s)", league.name, len(catalogue)))
        if not catalogue:
            print(tr("  (la source ne publie pas de liste pour cette competition)"))
            continue
        for names in catalogue:
            mark = " "
            if chosen is not None:
                if chosen.team_excluded(names):
                    mark = "-"
                elif chosen.team_matches(names):
                    mark = "*"
            print(tr("  {} {:<30} {}", mark, names[0], names[-1]))
        time.sleep(0.15)

    print()
    if chosen is not None:
        print(tr("'*' = suivie, '-' = exclue."))
    print(tr("Exemples :"))
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

    recorder = None
    if args.record:
        try:
            recorder = replay.Recorder(
                args.record, leagues=selection,
                on_log=lambda message: log(message, quiet=args.quiet)).start()
        except Exception as exc:
            # Un chemin impossible se dit maintenant, pas dans trois heures
            # quand on ira chercher le fichier.
            log("enregistrement impossible ({}) : {}".format(args.record, exc),
                quiet=args.quiet)
            release_pid_file()
            return 2

    guard = watcher.Watcher(
        selection,
        interval=args.interval,
        idle_interval=args.idle_interval,
        opener=recorder.opener if recorder is not None else None,
        on_log=lambda message: log(message, quiet=args.quiet),
        teams=chosen_teams,
        red_cards=args.red_cards,
        before_kickoff=args.before_kickoff * 60.0,
    )

    if recorder is not None:
        log("enregistrement des releves bruts -> {}".format(recorder.path),
            quiet=args.quiet)

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
        if recorder is not None:
            recorder.close()
            log(recorder.summary(), quiet=args.quiet)
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

        # `and pending.empty()` : un but depose dans la file juste apres que la
        # boucle ci-dessus l'a trouvee vide, et juste avant que le fil de
        # surveillance s'arrete, se perdait sinon. Le fil ne depose plus rien
        # une fois `stopping` leve, donc la file est bien vide pour de bon.
        if stopping.is_set() and pending.empty():
            stack.stop()

    stack.every(overlay.PUMP_MS, drain)
    stack.run()


def do_replay(args) -> int:
    """Rejoue un enregistrement : memes cartes, meme son, meme journal.

    Tout ce qui suit est le do_daemon() d'un soir de match, a trois choses
    pres, et chacune est le sujet meme de la commande :

      - la source est un fichier au lieu du reseau (l'`opener` du Player) ;
      - le temps avance a `--speed` fois la vitesse reelle (la `Pace`, qui
        tient lieu d'evenement d'arret aux boucles de surveillance) ;
      - le journal, l'etat et le pid vont dans un bac a sable (sandbox_paths).

    Le watcher, la detection des buts, les cartes, le son et les lignes de
    journal, eux, sont exactement ceux du direct. C'est voulu : un rejeu qui
    prendrait un raccourci ne prouverait rien.
    """
    from . import overlay

    try:
        recording = replay.Recording.load(args.replay)
    except replay.RecordingError as exc:
        print("butbutbut : " + str(exc), file=sys.stderr)
        return 2

    selection = recording.leagues()
    if not selection:
        print("butbutbut : {} ne nomme aucune competition reconnaissable."
              .format(args.replay), file=sys.stderr)
        return 2

    player = replay.Player(recording)

    with sandbox_paths(data_dir() / REPLAY_DIRNAME) as p:
        # La derniere carte a droit au meme temps d'antenne que les autres :
        # sans ce sursis, elle s'effacerait a l'instant ou elle s'affiche.
        pace = replay.Pace(player, speed=args.speed,
                           linger=resolve_sound(args)[1])

        def request_stop(_signum, _frame):
            pace.set()

        # Rendus a la fin, contrairement au daemon : celui-la ne rend jamais
        # la main, un rejeu si, et il laisserait un Ctrl-C casse derriere lui.
        restore = {}
        for name in ("SIGTERM", "SIGINT"):
            try:
                number = getattr(signal, name)
                restore[number] = signal.signal(number, request_stop)
            except Exception:
                pass

        log("rejeu de {} - {} - x{:g}".format(
            recording.path, recording.describe(), args.speed), quiet=args.quiet)
        log("journal, etat et pid du rejeu isoles dans {}".format(
            p["log"].parent), quiet=args.quiet)

        guard = watcher.Watcher(
            selection,
            interval=args.interval,
            idle_interval=args.idle_interval,
            opener=player.opener,
            monotonic=player.monotonic,
            clock=player.wall,
            on_log=lambda message: log(message, quiet=args.quiet),
            teams=team_filter(args),
            red_cards=args.red_cards,
            before_kickoff=args.before_kickoff * 60.0,
        )
        # Meme premier passage muet que le daemon, et sur les memes releves :
        # c'est ce qui fait que le rejeu produit la meme suite d'evenements.
        guard.prime(pause=0.0, now=player.monotonic())

        reporter = state.Reporter(p["state"], leagues=selection,
                                  interval=args.interval,
                                  idle_interval=args.idle_interval)
        reporter.update(guard.all_matches())

        stack = None
        if not args.no_overlay:
            try:
                stack = overlay.Stack(
                    screen=args.screen, position=args.position,
                    opacity=args.opacity, scale=args.scale,
                    retry_fullscreen=args.retry_fullscreen,
                    on_log=lambda message: log(message, quiet=args.quiet)).open()
            except overlay.TkinterMissing as exc:
                log(str(exc), quiet=args.quiet)
                log("pas de carte : on rejoue au son et au journal",
                    quiet=args.quiet)

        crest = crest_cache(args)
        try:
            if stack is None:
                _watch_headless(guard, args, pace, reporter)
            else:
                _watch_with_cards(guard, args, pace, stack, reporter, crest)
        except KeyboardInterrupt:
            log("rejeu interrompu.", quiet=args.quiet)
        finally:
            pace.set()
            if stack is not None:
                stack.close()
            crest.join(2.0)
            sound.stop_all()
            state.clear(p["state"])
            for number, handler in restore.items():
                try:
                    signal.signal(number, handler)
                except Exception:
                    pass
            log("rejeu termine : {} releve(s) servi(s) sur {}, {} parcourues."
                .format(player.served, len(recording.records),
                        replay.human_time(player.elapsed)), quiet=args.quiet)
    return 0


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
        print(tr("butbutbut : demo - [{}] {} - {}", 
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
                     on_log=lambda message: print(tr("butbutbut : {}", message)))
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
            print(tr("{:<16} {}", league.name,
                     tr("injoignable ({})", exc)))
            continue

        if chosen is not None:
            matches = [match for match in matches if chosen.matches(match)]

        print(tr("\n{}", league.name))
        if not matches:
            print(tr("  (aucun match au programme)")
                  if chosen is None else tr("  (aucun match de ces equipes)"))
            continue

        for match in matches:
            total += 1
            # 'note' et non 'state' : le module state est importe ici.
            if match.live:
                mark, note = ">", match.detail or match.clock or tr("en cours")
            elif match.finished:
                mark, note = " ", match.detail or tr("termine")
            else:
                mark, note = " ", _kickoff_text(match, now)
            print(tr("  {} {:>22} {} - {} {:<22} {}", 
                mark, match.home, match.home_score, match.away_score,
                match.away, note))
            for play in match.plays:
                side = match.home if play.team_id == match.home_id else match.away
                print(tr("      {:<22} {}", side, play.summary()))

    print(tr("\n{} match(s), '>' = en cours.", total))
    return 0


def _kickoff_text(match, now) -> str:
    remaining = match.seconds_until_kickoff(now)
    if remaining is None:
        return match.detail or tr("a venir")
    if remaining < 0:
        return match.detail or tr("imminent")
    if remaining < 3600:
        return tr("dans {} min", int(remaining // 60))
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
        print(tr("  releve      : {}", 
            tr("aucun pour l'instant") if pid
            else tr("aucun (le daemon efface son etat en s'arretant)")))
        return

    stale = state.is_stale(data)
    line = state.describe_age(state.age(data))
    stamp = data.get("updated_text")
    if stamp:
        line += "  ({})".format(stamp)
    print(tr("  releve      : {}", line))
    if not pid:
        print(tr("                etat laisse par un daemon qui ne tourne plus"))
    elif stale:
        print(tr("                (!) plus rien depuis, alors que la cadence est "
              "de {}s : daemon bloque ou source injoignable ?", 
                  _announced_cadence(data)))

    if stale:
        # Un etat perime decrit un match fini depuis longtemps : annoncer une
        # mi-temps d'hier soir serait pire que de ne rien annoncer.
        print(tr("  en cours    : inconnu (le dernier releve est trop vieux)"))
    else:
        matches = [row for row in (data.get("matches") or [])
                   if isinstance(row, dict)]
        summary = tr("{} match(s)", len(matches))
        if isinstance(data.get("total_matches"), int):
            summary += tr(" sur {} au programme", data["total_matches"])
        print(tr("  en cours    : {}", summary))
        for row in matches:
            print("                [{}] {} {} - {} {}  {}".format(
                row.get("league", "?"), row.get("home", "?"),
                row.get("home_score", "?"), row.get("away_score", "?"),
                row.get("away", "?"), row.get("clock", "")).rstrip())

    goals = data.get("goals_today", 0) if data.get("day") == state.today() else 0
    print(tr("  buts du jour: {}  (le detail : butbutbut --today)", goals))


def _announced_cadence(data):
    key = "interval" if data.get("matches") else "idle_interval"
    return data.get(key, "?")


def do_today(args) -> int:
    """Le recapitulatif de la journee, relu dans le journal."""
    p = paths()
    entries = journal.goals(p["log"])

    print(tr("butbutbut : buts signales le {:%d/%m/%Y}", datetime.now()))
    if not entries:
        print(tr("\n  (aucun but pour l'instant)"))
        print(tr("\nJournal : {}", p["log"]))
        return 0

    scored = 0
    cancelled = 0
    grouped = journal.by_league(entries)
    for league, rows in grouped:
        print(tr("\n{}", league))
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

    print(tr("\n{} but(s) dans {} competition(s).", scored, len(grouped)))
    if cancelled:
        print(tr("'-' = but retire par la VAR ({}).", cancelled))
    return 0


def do_status(args) -> int:
    p = paths()
    pid = running_pid()
    selection = leagues.resolve(args.leagues, args.exclude)

    print(tr("butbutbut {}", __version__))
    print(tr("  daemon      : {}",
             tr("actif (pid {})", pid) if pid else tr("arrete")))
    _print_activity(pid)
    chosen = team_filter(args)
    if chosen is not None:
        print(tr("  equipes     : {}", chosen.describe()))
    print(tr("  langue      : {}", i18n.describe()))
    summary = leagues.describe(selection)
    names = ", ".join(league.name for league in selection)
    print(tr("  suivi       : {}", summary))
    if names != summary and len(selection) <= 10:
        print(tr("  competitions: {}", names))
    followed = leagues.sports_of(selection)
    if len(followed) > 1:
        # Une ligne de plus seulement quand il y a de quoi se tromper : suivre
        # du foot et du hockey en meme temps, ca se dit.
        print(tr("  sports      : {}",
                 ", ".join(sport.name for sport in followed)))
    print(tr("  source      : ESPN scoreboard (public, sans cle)"))
    print(tr("  cadence     : {}s en direct / {}s au repos", 
        args.interval, args.idle_interval))
    print(tr("  donnees     : {}", p["data"]))
    settings = Path(getattr(args, "config", None) or p["config"])
    print(tr("  config      : {}{}", 
        settings,
        "" if settings.exists() else tr("  (absent, voir --write-config)")))

    sounds = sound.custom_sounds(p["sound"])
    if sounds:
        extra = (tr(" (+{} autre(s), tirage au hasard)", len(sounds) - 1)
                 if len(sounds) > 1 else "")
        print(tr("  son         : {}{}", sounds[0].name, extra))
    else:
        chosen = sound.pick_sound(p["wav"], p["sound"])
        origin = (tr("fourni") if chosen == sound.BUNDLED_SOUND
                  else tr("corne synthetisee"))
        print(tr("  son         : {} ({})", chosen.name, origin))
    print(tr("  sons perso  : {}  ({} fichier(s))", p["sound"], len(sounds)))

    cached = crest_cache(args).cached()
    print(tr("  ecussons    : {}",
             tr("desactives (--no-logos)") if args.no_logos
             else tr("{}  ({} en cache)", p["logos"], len(cached))))

    found = screens.monitors()
    print(tr("  ecrans      : {} -> carte en {} sur {}",
             screens.describe(found), args.position,
             tr("l'ecran principal") if args.screen is None
             else tr("ecran {}", args.screen)))
    print(tr("  plein ecran : {}", 
        tr("detecte (la carte masquee est notee au journal)")
        if fullscreen.supported()
        else tr("non detectable sur cette plateforme")))
    print(tr("  journal     : {}", p["log"]))

    if sys.platform == "win32":
        print(tr("  lecteur     : winsound + MCI (integres)"))
    else:
        player = sound.find_player()
        print(tr("  lecteur     : {}", 
            player[0] if player
            else tr("AUCUN (installe mpv/ffmpeg/pipewire/alsa-utils)")))
    try:
        import tkinter  # noqa: F401

        print(tr("  affichage   : tkinter OK"))
    except Exception:
        print(tr("  affichage   : tkinter MANQUANT (voir README)"))

    print(tr("\n  Connexion   : "), end="", flush=True)
    try:
        matches = espn.scoreboard(selection[0])
        print(tr("OK ({} : {} match(s))", selection[0].name, len(matches)))
    except espn.SourceError as exc:
        print(tr("ECHEC ({})", exc))
        return 1
    return 0


def do_list(args) -> int:
    """Le catalogue des competitions, tous sports confondus."""
    print(tr("butbutbut : competitions surveillables\n"))
    for title, name, slug, alias in leagues.catalogue_lines(all_sports=True):
        if title is not None:
            print(tr("{}:", title))
            continue
        print(tr("  {:<30} {:<24} {}", name, slug, alias))

    print(tr("\nExemples :"))
    print("  butbutbut --leagues l1,ucl,ligue2")
    print(tr("  butbutbut --exclude liga,seriea        (les 5 grands moins deux)"))
    print(tr("  butbutbut --leagues all                (tout le catalogue de football)"))
    print(tr("  butbutbut --leagues nhl,top14          (hockey et rugby, a la demande)"))
    print(tr("  butbutbut --leagues rugby              (tout le rugby du catalogue)"))
    print(tr("  butbutbut --leagues all-sports         (vraiment tout)"))
    print(tr("  butbutbut --leagues por.1              (n'importe quel code ESPN)"))
    print(tr("  butbutbut --leagues hockey:nhl         (... y compris dans un autre sport)"))
    return 0


def do_screens(args) -> int:
    found = screens.monitors()
    print(tr("butbutbut : {} ecran(s) detecte(s)", len(found)))
    for index, monitor in enumerate(found):
        tag = tr("  (principal)") if monitor.primary else ""
        print(tr("  {}  {:<16} {}x{} a +{}+{}{}", 
            index, monitor.name, monitor.width, monitor.height,
            monitor.x, monitor.y, tag))
    print(tr("\nPar defaut la carte s'affiche en bas a droite de l'ecran principal."))
    print(tr("La deplacer :  butbutbut --screen 1 --position top-right"))
    return 0


def do_paths(args) -> int:
    for key, value in paths().items():
        print(tr("{:6} {}", key, value))
    return 0


def do_check_update(args) -> int:
    from . import update

    print(tr("butbutbut {}", __version__))
    return update.check(dev=args.dev)


def do_update(args) -> int:
    from . import update

    print(tr("butbutbut {} - mise a jour", __version__))
    try:
        return update.update(dev=args.dev)
    except update.UpdateError as exc:
        # Le message dit quoi faire a la main : une pile d'appels par-dessus
        # ne renseignerait personne.
        print(tr("butbutbut : {}", exc), file=sys.stderr)
        return 1


def do_stop(args) -> int:
    pid = running_pid()
    if not pid:
        print(tr("butbutbut : aucun daemon en cours."))
        return 1
    try:
        if sys.platform == "win32":
            os.system("taskkill /PID {} /F >NUL 2>&1".format(pid))
        else:
            os.kill(pid, signal.SIGTERM)
        print(tr("butbutbut : daemon {} arrete.", pid))
        release_pid_file()
        # Sous Windows le daemon est tue net : son finally ne tourne pas, et
        # personne d'autre ne viendrait ramasser son etat.
        state.clear(paths()["state"])
        return 0
    except Exception as exc:
        print(tr("butbutbut : impossible d'arreter {} : {}", pid, exc))
        return 1


# ---------------------------------------------------------------- parse ------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="butbutbut",
        description=tr("Un but tombe en Ligue 1, Premier League, LaLiga, Serie A "
                       "ou Bundesliga : le son part et le score s'affiche a "
                       "l'ecran. Le hockey et le rugby sont dans le catalogue, "
                       "a la demande (voir --list)."),
    )
    parser.add_argument("--version", action="version",
                        version="butbutbut {}".format(__version__))

    parser.add_argument("--test", nargs="?", type=int, const=1, default=0,
                        metavar="N",
                        help=tr("affiche N cartes de demonstration puis quitte "
                             "(defaut 1 ; --test 3 montre l'empilement)"))
    parser.add_argument("--scores", action="store_true",
                        help=tr("affiche les matchs du jour dans le terminal puis quitte"))
    parser.add_argument("--status", action="store_true",
                        help=tr("affiche l'etat (daemon, dernier releve, matchs "
                             "en cours, son, ecrans, connexion)"))
    parser.add_argument("--today", action="store_true",
                        help=tr("recapitule les buts signales aujourd'hui"))
    parser.add_argument("--stop", action="store_true", help=tr("arrete le daemon en cours"))
    parser.add_argument("--paths", action="store_true", help=tr("affiche les chemins utilises"))
    parser.add_argument("--screens", action="store_true", help=tr("liste les ecrans detectes"))
    parser.add_argument("--update", action="store_true",
                        help=tr("met a jour butbutbut depuis GitHub et rejoue l'installeur"))
    parser.add_argument("--check-update", action="store_true",
                        dest="check_update",
                        help=tr("dit si une version plus recente existe, sans rien installer"))
    parser.add_argument("--dev", action="store_true",
                        help=tr("avec --update ou --check-update : viser la pointe "
                             "de la branche principale au lieu de la derniere release"))

    parser.add_argument("--record", default=None, metavar=tr("FICHIER"),
                        help=tr("surveille normalement, et ecrit en plus chaque "
                             "reponse brute de la source dans FICHIER (JSON "
                             "Lines ; un nom en .gz est compresse). C'est ce "
                             "que --replay rejoue."))
    parser.add_argument("--replay", default=None, metavar=tr("FICHIER"),
                        help=tr("rejoue un enregistrement : memes cartes, meme "
                             "son, meme journal, sans reseau. Ni le journal ni "
                             "l'etat du vrai daemon ne sont touches."))
    parser.add_argument("--speed", type=float, default=replay.DEFAULT_SPEED,
                        metavar=tr("N"),
                        help=tr("avec --replay : divise les ecarts de temps par "
                             "N (defaut 1 ; 60 = une heure de match en une "
                             "minute)"))

    parser.add_argument("--config", default=None, metavar=tr("CHEMIN"),
                        help=tr("fichier de configuration a lire (defaut : {} dans "
                             "le dossier de donnees, voir 'butbutbut --paths')"
                        , config.FILENAME))
    parser.add_argument("--write-config", action="store_true", dest="write_config",
                        help=tr("ecrit un fichier de configuration d'exemple, "
                             "commente, puis quitte (n'ecrase rien)"))

    parser.add_argument("--leagues", default=None, metavar=tr("LISTE"),
                        help=tr("competitions suivies, separees par des virgules "
                             "(defaut : les 5 grands championnats de football). "
                             "Ex : --leagues l1,pl,ucl ; 'all' pour tout le "
                             "catalogue de football, 'hockey' ou 'rugby' pour "
                             "un autre sport entier, 'all-sports' pour tout ; "
                             "un code ESPN marche aussi (por.1, hockey:nhl)"))
    parser.add_argument("--exclude", default=None, metavar=tr("LISTE"),
                        help=tr("competitions a ne pas suivre, meme syntaxe. Ex : "
                             "--exclude liga,seriea"))
    parser.add_argument("--list", action="store_true", dest="list_leagues",
                        help=tr("liste les competitions surveillables et leurs noms"))
    parser.add_argument("--teams", default=None, metavar=tr("LISTE"),
                        help=tr("ne signaler que les matchs de ces equipes, "
                             "separees par des virgules. Un match compte des "
                             "qu'une des deux equipes y est. Ex : --teams om,psg"))
    parser.add_argument("--exclude-teams", default=None, metavar=tr("LISTE"),
                        dest="exclude_teams",
                        help=tr("ne rien signaler des matchs de ces equipes"))
    parser.add_argument("--list-teams", action="store_true", dest="list_teams",
                        help=tr("liste les equipes des competitions suivies"))
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL,
                        help=tr("secondes entre deux releves quand un match est en "
                             "cours (defaut {})", DEFAULT_INTERVAL))
    parser.add_argument("--idle-interval", type=int, default=DEFAULT_IDLE_INTERVAL,
                        dest="idle_interval",
                        help=tr("secondes entre deux releves quand il n'y a rien a "
                             "suivre (defaut {})", DEFAULT_IDLE_INTERVAL))

    parser.add_argument("--duration", type=float, default=None,
                        help=tr("duree d'affichage de la carte (defaut : la duree "
                             "du son, au moins {})", DEFAULT_DURATION))
    parser.add_argument("--position", default=DEFAULT_POSITION, metavar=tr("COIN"),
                        help=tr("coin ou les cartes s'empilent : bottom-right "
                             "(defaut), bottom-left, top-right, top-left, center"))
    parser.add_argument("--screen", default=None, metavar=tr("CHOIX"),
                        help=tr("ecran d'affichage : 'primary' (defaut) ou un index "
                             "(0, 1, 2...). Voir 'butbutbut --screens'."))
    parser.add_argument("--scale", type=float, default=1.0,
                        help=tr("taille de la carte (1.0 par defaut, 1.5 = plus grande)"))
    parser.add_argument("--opacity", type=float, default=1.0, help=tr("opacite, 0.0 a 1.0"))
    parser.add_argument("--no-overlay", action="store_true", dest="no_overlay",
                        help=tr("pas de carte : seulement le son et le journal"))
    parser.add_argument("--no-phase-cards", action="store_true",
                        dest="no_phase_cards",
                        help=tr("pas de carte au coup d'envoi, a la mi-temps, a la "
                             "reprise ni a la fin du match (les buts, si)"))
    parser.add_argument("--retry-fullscreen", nargs="?", type=float,
                        const=RETRY_FULLSCREEN, default=0.0, metavar=tr("SECONDES"),
                        dest="retry_fullscreen",
                        help=tr("quand une application en plein ecran masque "
                             "l'ecran, repasser la carte des que l'ecran se "
                             "libere, pendant SECONDES au plus (defaut {:.0f} ; "
                             "Windows uniquement, voir README)", 
                                 RETRY_FULLSCREEN))
    parser.add_argument("--red-cards", action="store_true", dest="red_cards",
                        help=tr("signale aussi les cartons rouges, par une carte "
                             "discrete et sans son"))
    parser.add_argument("--before-kickoff", type=int, default=0,
                        dest="before_kickoff", metavar=tr("MINUTES"),
                        help=tr("annonce le match ce nombre de minutes avant le "
                             "coup d'envoi, une seule fois et sans son "
                             "(0 = desactive, defaut)"))
    parser.add_argument("--lang", default=None, metavar=tr("CODE"),
                        help=tr("langue des cartes : fr, en, es, it, de (defaut : "
                             "celle du systeme, francais a defaut). Le journal, "
                             "lui, reste toujours en francais."))
    parser.add_argument("--no-logos", action="store_true", dest="no_logos",
                        help=tr("pas d'ecusson sur les cartes, et rien de "
                             "telecharge (les couleurs des clubs restent)"))
    parser.add_argument("--no-sound", action="store_true", dest="no_sound",
                        help=tr("mode muet"))
    parser.add_argument("--volume", type=float, default=DEFAULT_VOLUME,
                        help=tr("volume de la corne synthetisee, 0.0 a 1.0"))
    parser.add_argument("--regen-sound", action="store_true", dest="regen_sound",
                        help=tr("regenere la corne synthetisee"))
    parser.add_argument("--quiet", action="store_true", help=tr("n'ecrit que dans le journal"))
    return parser


def main(argv=None) -> int:
    chosen = config.path_from(argv, paths()["config"])

    # La langue en tout premier : les aides d'argparse sont traduites a la
    # construction du parseur, donc avant que l'analyse ne livre --lang. C'est
    # le seul moment ou --help peut encore sortir dans la bonne langue.
    try:
        i18n.use(config.lang_from(argv, chosen))
    except i18n.UnknownLanguage as exc:
        # Langue inconnue : le francais est tout ce qui est sur, ici.
        print("butbutbut : {}".format(exc), file=sys.stderr)
        return 2

    parser = build_parser()

    # Le fichier alimente les defauts du parseur avant l'analyse : la ligne de
    # commande, analysee ensuite, l'emporte donc toujours. Voir config.apply().
    for warning in config.apply(parser, chosen).warnings:
        print(tr("butbutbut : {}", warning), file=sys.stderr)

    args = parser.parse_args(argv)
    args.config = chosen        # le chemin retenu, pour --status et --write-config

    if args.write_config:
        # Un parseur neuf : le fichier d'exemple annonce les vrais defauts du
        # programme, pas ceux qu'un fichier deja present vient d'installer.
        written, message = config.write_example(chosen, build_parser())
        print(tr("butbutbut : {}", message),
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
    if args.record and args.replay:
        print("butbutbut : --record enregistre le direct, --replay rejoue un "
              "enregistrement : les deux ensemble n'ont pas de sens.",
              file=sys.stderr)
        return 2
    if args.speed <= 0:
        print("butbutbut : --speed attend un nombre strictement positif "
              "(1 = temps reel, 60 = soixante fois plus vite).", file=sys.stderr)
        return 2
    if args.position.strip().lower() not in screens.CORNERS:
        print(tr("butbutbut : position inconnue : {} (voir --help)", args.position),
              file=sys.stderr)
        return 2


    try:
        leagues.resolve(args.leagues, args.exclude)
    except leagues.SelectionError as exc:
        print(tr("butbutbut : {}", exc), file=sys.stderr)
        return 2

    p = paths()
    try:
        p["data"].mkdir(parents=True, exist_ok=True)
        p["sound"].mkdir(parents=True, exist_ok=True)
        p["logos"].mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        print(tr("butbutbut : dossier de donnees inutilisable : {}", exc),
              file=sys.stderr)

    if args.regen_sound:
        sound.ensure_wav(p["wav"], args.volume, force=True)
        print(tr("butbutbut : corne regeneree -> {}", p["wav"]))

    if args.list_leagues:
        return do_list(args)
    if args.list_teams:
        return do_list_teams(args)
    # La verification des equipes interroge la source : un rejeu, qui est
    # justement cense se passer de reseau, s'en passe aussi.
    if (args.teams or args.exclude_teams) and not args.replay:
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
    if args.replay:
        return do_replay(args)

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
