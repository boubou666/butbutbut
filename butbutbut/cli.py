"""Ligne de commande et boucle de fond de butbutbut."""

from __future__ import annotations

import argparse
import csv
import ctypes
import io
import json
import os
import queue
import signal
import sys
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import (__version__, config, crests, espn, fullscreen, hook, i18n,
               journal, leagues, pinned, presenting, replay, screens, silence,
               sound, speech, state, teams, watcher)
# La prose de la ligne de commande : le francais est la cle, voir lang/.
from .i18n import tr

DEFAULT_INTERVAL = 25          # secondes, quand un match est en cours
DEFAULT_IDLE_INTERVAL = 300    # secondes, quand il n'y a rien a suivre
DEFAULT_DURATION = 6.0         # duree d'affichage minimale de la carte
PHASE_DURATION = 5.0           # coup d'envoi, mi-temps, reprise, fin : sans son
CATCHUP_DURATION = 12.0        # le resume de sortie de veille : plusieurs lignes
DEFAULT_VOLUME = 0.55
DEFAULT_POSITION = "bottom-right"
RETRY_FULLSCREEN = 120.0       # duree d'attente par defaut de --retry-fullscreen
# Ce qu'on accorde au fil de surveillance pour finir sa phrase quand on s'en
# va. Plus que le delai d'un releve reseau (espn.DEFAULT_TIMEOUT) serait faire
# attendre l'arret pour un fil qu'on va de toute facon abandonner ; moins ne
# laisserait meme pas le temps d'ecrire le fichier d'etat.
WATCH_JOIN = 5.0

# Les recapitulatifs du journal (--today, --week, --month, --since).
WEEK_DAYS = 7                  # --week : aujourd'hui et les six jours d'avant
MONTH_DAYS = 30                # --month : idem, sur trente jours
# Le budget de lignes d'un recapitulatif detaille. Un terminal en fait 24 a 50 ;
# on vise le milieu, et au-dela le recapitulatif se resume a une ligne par jour
# plutot que de defiler hors de l'ecran.
SCREEN_LINES = 36
SCORERS_SHOWN = 20             # buteurs affiches par --top-scorers
LEAGUES_SHOWN = 3              # competitions nommees sur la ligne d'une journee
# --stats. La barre la plus longue fait 36 signes : avec le libelle, le compte
# et le pourcentage autour, la ligne la plus large tient dans 72 colonnes, donc
# dans les 80 d'un terminal qui n'a jamais ete redimensionne.
STATS_BAR = 36
STATS_LEAGUES = 8              # competitions detaillees par --stats
STATS_EVENINGS = 3             # soirees nommees par --stats
# Les jours de la semaine, abreges et sans accent, comme tout le reste du code.
# strftime() rendrait la langue du systeme : le journal, lui, parle francais.
WEEKDAYS = ("lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim.")
# --next : une semaine par defaut. C'est la maille du calendrier - un club joue
# une fois par semaine, deux quand il a une coupe - donc sept jours contiennent
# toujours le prochain match de qui que ce soit, sans deverser un mois
# d'affiches pour repondre a "c'est quand, le prochain ?".
DEFAULT_NEXT_DAYS = 7
# Au-dela, la source elle-meme n'a plus grand-chose a dire : les calendriers ne
# sont publies qu'a quelques semaines. Cette borne evite surtout de demander
# une annee entiere par megarde.
MAX_NEXT_DAYS = 30
# Meme espacement que Watcher.prime() : avec --leagues all ce sont 36 requetes,
# et une rafale finit par se faire jeter par la source.
NEXT_PAUSE = 0.2
# --table interroge les competitions les unes apres les autres, exactement pour
# la meme raison que --next : une rafale de requetes finit par se faire jeter.
TABLE_PAUSE = 0.2

# La largeur du classement, en signes. On vise 80 colonnes ecussons exclus -
# c'est le terminal le plus etroit qu'on croise encore, et un tableau qui se
# replie sur deux lignes ne se lit plus du tout. Le compte : 2 pour la marque
# de surlignage, 2 pour le rang, 2 de separation, le nom, puis une cellule par
# colonne du sport (sept au maximum, au rugby).
TABLE_NAME_WIDTH = 22
TABLE_CELL_WIDTH = 6

# Les jours de la semaine, ecrits ici plutot que tires de la locale : %A rend
# ce que la machine veut bien (parfois de l'anglais, parfois des accents), et
# l'affichage doit etre le meme partout.
WEEKDAYS_FULL = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi",
                 "dimanche")


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

def sound_clubs(args) -> list:
    """Les mots dont butbutbut sait qu'ils designent un club.

    Les surnoms usuels, plus tout ce que --teams et --exclude-teams ont recu.
    De quoi reconnaitre `psg.mp3` comme un son d'equipe meme un soir ou le PSG
    ne joue pas, et donc ne pas le verser dans le fond sonore des autres buts.
    """
    chosen = teams.Filter(args.teams, args.exclude_teams)
    return list(teams.ALIASES) + chosen.wanted_tokens + chosen.excluded_tokens


def sound_context(args, event):
    """Le contexte d'un but, pour que le nom des fichiers puisse parler.

    Rend None hors d'un but : une carte muette n'a pas de son a choisir, et
    --test n'a aucun match derriere lui.
    """
    if event is None or not event.goal:
        return None

    match = event.match
    if event.side == "away":
        scorer, beaten = match.away_names, match.home_names
    else:
        scorer, beaten = match.home_names, match.away_names

    # `contre` ne se declenche que pour une equipe SUIVIE : sans --teams, il
    # n'y a pas de camp, et tous les buts encaisses se valent.
    chosen = team_filter(args)
    conceded = bool(chosen is not None and chosen.wanted
                    and chosen.team_matches(beaten))
    return sound.Context(league=event.league, scorer_names=scorer,
                         beaten_names=beaten, conceded=conceded,
                         clubs=sound_clubs(args))


def sound_assignments(args) -> list:
    """Les paires de --sound-for, relues a chaque appel.

    Relues et non gardees : main() a deja refuse une paire fautive, et analyser
    trois mots coute moins cher qu'un etat de plus a trainer dans `args` - que
    les tests, `--status` et le daemon devraient tous penser a poser.

    Une paire qui ne veut rien dire rend une liste vide plutot que de lever :
    le demarrage l'a deja dite, et ce n'est pas au moment de jouer un son qu'on
    arrete tout.
    """
    try:
        return sound.parse_assignments(getattr(args, "sound_for", None))
    except sound.Invalid:
        return []


def sound_gone(args):
    """Que faire d'un son nomme qui s'est evapore : le noter, et continuer.

    Une cle USB debranchee ou un fichier renomme ne vaut pas le silence : le
    dossier, puis le son fourni, prennent le relais. Le journal, lui, garde de
    quoi comprendre pourquoi le cri du club n'est pas sorti ce soir-la.
    """
    def note(assignment, problem):
        log("son nomme pour {} indisponible ({}) : {} -- le son par defaut "
            "prend le relais".format(assignment.token, problem,
                                     assignment.path), quiet=args.quiet)
    return note


def resolve_sound(args, event=None):
    """(chemin du son, duree d'affichage). Relu a chaque but.

    Tu peux deposer un mp3 dans <data>/sound pendant que le daemon tourne : il
    le prendra au but suivant, sans redemarrage. `event` est ce qui permet au
    nom des fichiers - et aux paires de --sound-for - de designer une equipe,
    une competition ou un but encaisse ; il reste facultatif, faute de quoi
    --test et les cartes muettes n'auraient plus de son du tout.
    """
    p = paths()

    chosen = None
    if not args.no_sound:
        try:
            chosen = sound.pick_sound(p["wav"], p["sound"], args.volume,
                                      context=sound_context(args, event),
                                      assigned=sound_assignments(args),
                                      on_missing=sound_gone(args))
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


def speak_goal(voice, args, event) -> None:
    """Dit le but a voix haute, quand --speak est arme. Rend la main aussitot.

    La phrase part apres la corne (speech.AFTER_SOUND) : parler pendant le
    jingle rendrait les deux inaudibles. En mode muet il n'y a rien a attendre,
    et la voix devient la seule alerte.
    """
    if voice is None or not voice:
        return
    voice.say(hook.phrase_of(event),
              after=0.0 if args.no_sound else speech.AFTER_SOUND)


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


def checked_filter(args):
    """Les mots d'equipe a confronter au catalogue : ceux du filtre, et --pin.

    `--pin` n'est pas un filtre - il ne cache aucun but, il ajoute une carte -
    mais il nomme une equipe exactement de la meme facon, et une faute de
    frappe y merite le meme refus : un `--pin marseile` silencieux, ce serait
    une carte epinglee qui n'arrive jamais, sans qu'on sache pourquoi.
    """
    wanted = [token for token in (args.teams, getattr(args, "pin", None)) if token]
    chosen = teams.Filter(",".join(wanted), args.exclude_teams)
    return chosen if chosen.active else None


def spoiler_filter(args):
    """Le filtre sans spoiler, ou None si personne ne regarde en differe."""
    chosen = teams.SpoilerFilter(args.spoiler_free)
    return chosen if chosen.active else None


def sound_teams(args):
    """Les mots de --sound-for qui visent une equipe, en filtre verifiable.

    Une competition se reconnait hors ligne, une equipe non : elle passe donc
    par le meme catalogue que --teams, et une faute de frappe y merite le meme
    refus. Sans ca, `--sound-for marseile=cri.wav` serait un cri qui ne sort
    jamais, sans que rien ne le dise - la faute exacte que check_teams() a ete
    ecrite pour attraper.
    """
    tokens = [one.token for one in sound_assignments(args)
              if not sound.is_conceded_word(one.token)
              and leagues.designates(one.token) is None]
    chosen = teams.Filter(",".join(tokens))
    return chosen if chosen.active else None


def _team_filters(args) -> list:
    """Tous les filtres par equipe en vigueur, dans l'ordre de decision.

    Sert a la verification des mots au demarrage : les quatre listes puisent
    dans le meme vocabulaire, une faute de frappe y coute aussi cher.
    """
    return [f for f in (checked_filter(args), spoiler_filter(args),
                        sound_teams(args)) if f is not None]


def check_teams(args, selection, stream=None) -> int:
    """Confronte --teams / --exclude-teams / --pin / --spoiler-free au catalogue.

    Un mot qui ne designe aucune equipe est une faute de frappe : mieux vaut
    le dire tout de suite que de laisser le daemon rester muet pour toujours.
    Un mot fautif dans --spoiler-free est encore plus sournois : il ne rend pas
    le daemon muet, il le laisse spoiler le match qu'on voulait proteger. Les
    equipes nommees a --sound-for suivent le meme chemin.
    """
    chosen = _team_filters(args)
    if not chosen:
        return 0
    # `stream` : ou vont les lignes de confirmation. La sortie standard pour
    # tout le monde, sauf pour une commande dont la sortie standard est un
    # fichier de donnees (--export).
    stream = stream or sys.stdout

    catalogue = []
    for league in selection:
        catalogue.extend(espn.catalogue(league))
        time.sleep(0.15)

    if not catalogue:
        print(tr("butbutbut : impossible de verifier les equipes (source "
                 "injoignable), on continue sans verification."),
              file=sys.stderr)
        return 0

    found, orphans = {}, []
    for one in chosen:
        hits, missed = one.resolve(catalogue)
        found.update(hits)
        # Un meme mot peut figurer dans deux listes : il n'est signale qu'une
        # fois, sans quoi --teams om --spoiler-free omm sortirait deux lignes.
        orphans.extend(o for o in missed if o not in orphans)

    for token in sorted(found):
        clubs = found[token]
        extra = "" if len(clubs) == 1 else "  ({} clubs)".format(len(clubs))
        print(tr("  {:<16} -> {}{}", token, ", ".join(clubs), extra),
              file=stream)
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
    quiet_teams = spoiler_filter(args)

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
            # Le sans-spoiler passe apres l'exclusion (un match exclu n'existe
            # deja plus) mais devant le suivi : c'est la nuance qu'on est venu
            # verifier ici.
            if mark != "-" and quiet_teams is not None \
                    and quiet_teams.team_matches(names):
                mark = "?"
            print(tr("  {} {:<30} {}", mark, names[0], names[-1]))
        time.sleep(0.15)

    print()
    if chosen is not None:
        print(tr("'*' = suivie, '-' = exclue."))
    if quiet_teams is not None:
        print(tr("'?' = suivie sans spoiler : journal seulement, ni carte ni son."))
    print(tr("Exemples :"))
    print("  butbutbut --teams om,psg")
    print("  butbutbut --teams \"real madrid\" --leagues liga,ucl")
    print("  butbutbut --exclude-teams psg")
    print("  butbutbut --spoiler-free om")
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
    quiet_teams = spoiler_filter(args)
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
        spoiler_free=quiet_teams,
        red_cards=args.red_cards,
        before_kickoff=args.before_kickoff * 60.0,
        catch_up=args.catch_up,
    )

    if recorder is not None:
        log("enregistrement des releves bruts -> {}".format(recorder.path),
            quiet=args.quiet)
    # La carte epinglee vit a cote de la surveillance : le watcher raconte ce
    # qui vient d'arriver, elle montre ou en est un match. Inactive sans --pin.
    pin = pinned.Pin(args.pin, on_log=lambda message: log(message, quiet=args.quiet))

    log("demarrage (pid {}) - {} - releve toutes les {}s en direct, {}s au repos"
        .format(os.getpid(), leagues.describe(selection), args.interval,
                args.idle_interval), quiet=args.quiet)
    if chosen_teams is not None:
        log(chosen_teams.describe(), quiet=args.quiet)
    if quiet_teams is not None:
        log("sans spoiler : {} - le journal garde tout, l'ecran et le son se "
            "taisent".format(quiet_teams.describe()), quiet=args.quiet)
    if args.red_cards:
        log("cartons rouges signales", quiet=args.quiet)
    if args.before_kickoff:
        log("annonce du coup d'envoi {} min avant".format(args.before_kickoff),
            quiet=args.quiet)
    if pin.active:
        log("carte epinglee sur {} : elle reste a l'ecran tant qu'un match est "
            "en cours".format(args.pin), quiet=args.quiet)
    if args.catch_up:
        log("rattrapage de sortie de veille : une carte de resume, sans son",
            quiet=args.quiet)

    # Le seul point de decision du "est-ce le moment ?" : voir silence.py.
    hush = silence.Silence(args.quiet_hours,
                           while_presenting=args.quiet_while_presenting,
                           on_log=lambda message: log(message, quiet=args.quiet))
    if hush.armed:
        log("ne pas deranger : {}. Le journal garde tout, l'ecran et le son se "
            "taisent.".format(hush.describe()), quiet=args.quiet)

    on_goal = hook.Runner(args.on_goal,
                          on_log=lambda message: log(message, quiet=args.quiet))
    if on_goal:
        # La commande est notee au demarrage : un crochet muet qui reussit ne
        # laisse aucune trace ensuite, autant savoir ce qui a ete arme.
        log("crochet a chaque but : {}".format(on_goal.command), quiet=args.quiet)

    voice = speech.Voice(args.speak, lang=i18n.language(),
                         on_log=lambda message: log(message, quiet=args.quiet))
    if voice:
        # Ce qui parlera est dit au demarrage : une machine sans synthetiseur
        # se decouvrirait sinon au premier but, c'est-a-dire trop tard.
        log("annonce vocale : {}".format(voice.describe()), quiet=args.quiet)

    log("pour tout arreter : butbutbut --stop", quiet=args.quiet)

    guard.prime()
    log(_startup_summary(guard), quiet=args.quiet)

    # L'etat est publie des le premier releve : sinon un --status lance dans la
    # foulee du demarrage annoncerait un daemon sans aucune activite.
    reporter = state.Reporter(paths()["state"], leagues=selection,
                              interval=args.interval,
                              idle_interval=args.idle_interval, pin=args.pin)
    # Un match deja en cours au demarrage est epingle tout de suite : attendre
    # le coup d'envoi suivant priverait de carte celui qui lance le daemon a la
    # mi-temps, c'est-a-dire justement quand il en a envie.
    follow = pin.update(guard.all_matches())
    reporter.update(guard.all_matches(),
                    pinned=follow.match if follow is not None else None)

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
            _watch_headless(guard, args, stopping, reporter, pin,
                            on_goal=on_goal, hush=hush, voice=voice)
        else:
            _watch_with_cards(guard, args, stopping, stack, reporter, pin,
                              crest, on_goal=on_goal, hush=hush, voice=voice)
    except KeyboardInterrupt:
        log("arret demande.", quiet=args.quiet)
    finally:
        stopping.set()
        voice.close()
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


def _watch_headless(guard, args, stopping, reporter, pin,
                    on_goal=None, hush=None, voice=None) -> None:
    """Sans carte : un seul fil, le son et le journal.

    L'epinglage est quand meme suivi, faute d'ecran ou il s'afficherait :
    c'est lui qui alimente la ligne "epinglee" de `--status`, et il n'y a
    aucune raison qu'elle mente parce qu'on a coupe les cartes.
    """
    hush = hush if hush is not None else silence.Silence()
    while not stopping.is_set():
        events = guard.tick()
        # "Est-ce le moment ?" une fois par releve, pas une fois par but : la
        # reponse ne bougerait pas entre deux buts du meme tour, et la poser
        # deux fois ferait deux lignes de journal pour un seul changement.
        hushed = hush.reason()
        follow = pin.update(guard.all_matches())
        reporter.update(guard.all_matches(), events,
                        pinned=follow.match if follow is not None else None)
        for event in events:
            log(event.log_line(), quiet=args.quiet)
            if event.spoiler_free:
                continue            # match en differe : le journal, et rien d'autre
            # Le crochet part avec le journal, pas avec la carte : il decrit
            # un but, pas un affichage, et doit partir meme en --no-overlay.
            # Un match regarde en differe, en revanche, n'en declenche aucun :
            # le crochet est une alerte de plus, et --spoiler-free les coupe
            # toutes - d'ou le `continue` juste au-dessus. Le silence de
            # --quiet-hours, lui, le laisse passer : il protege cet ecran et ce
            # haut-parleur, pas un telephone a l'autre bout de la maison.
            if on_goal is not None:
                on_goal.fire(event)
            if not event.goal:
                continue            # but annule et phases de match : muets
            if hushed:
                continue            # nuit, ou presentation : le journal a deja tout
            # La voix avant le son : elle part dans son propre fil et n'attend
            # personne, alors que resolve_sound() relit le dossier et peut
            # mesurer un fichier. Elle attendra la corne d'elle-meme.
            speak_goal(voice, args, event)
            # Un son par but, et pas un par releve : deux buts du meme tour
            # peuvent venir de deux equipes, donc de deux fichiers.
            play_goal_sound(resolve_sound(args, event)[0])

        # plan_wait() et pas next_delay() : le watcher retient ce qu'on s'est
        # engage a attendre, et voit ainsi au tick suivant qu'on a dormi.
        stopping.wait(guard.plan_wait())


def _watch_with_cards(guard, args, stopping, stack, reporter, pin,
                      crest=None, on_goal=None, hush=None, voice=None) -> None:
    """Avec cartes : tkinter garde le fil principal, la surveillance a le sien.

    tkinter n'aime pas etre touche depuis un autre fil : le fil de surveillance
    ne fait que du reseau et du journal, puis depose ses buts dans une file que
    la boucle tkinter vide toutes les PUMP_MS millisecondes.

    La carte epinglee suit le meme chemin, dans sa propre file : le verdict de
    chaque releve y est depose, et seul le DERNIER est applique. Un releve en
    retard ne doit pas repeindre un score perime par-dessus le bon.
    """
    from . import overlay

    hush = hush if hush is not None else silence.Silence()
    pending = queue.Queue()
    pinning = queue.Queue()

    def poll():
        while not stopping.is_set():
            try:
                events = guard.tick()
                hushed = hush.reason()
                follow = pin.update(guard.all_matches())
                reporter.update(guard.all_matches(), events,
                                pinned=follow.match if follow is not None else None)
                if pin.active:
                    # "AUCUNE carte" vaut aussi pour l'epinglee : un tableau de
                    # bord allume toute la nuit est exactement ce dont on se
                    # plaint. Elle revient d'elle-meme au premier releve d'apres
                    # le silence, puisque chaque tour repose la question.
                    pinning.put(None if hushed else follow)
                for event in events:
                    log(event.log_line(), quiet=args.quiet)
                    # Depuis le fil de surveillance, et non depuis drain() :
                    # le crochet ne doit rien devoir a tkinter, et il part
                    # meme quand l'affichage de la carte echoue. Un match
                    # regarde en differe, lui, n'en declenche aucun : le
                    # crochet est une alerte de plus, et --spoiler-free les
                    # coupe toutes. Le journal, lui, a deja sa ligne.
                    if event.spoiler_free:
                        continue
                    if on_goal is not None:
                        on_goal.fire(event)
                    if hushed:
                        continue    # rien ne monte a tkinter : ni carte, ni son
                    # La voix part d'ici et pas de drain(), pour la meme raison
                    # que le crochet : elle ne doit rien devoir a tkinter, et
                    # une carte qui n'arrive pas a s'afficher ne doit pas
                    # rendre le but muet. Elle a son fil, elle ne retient
                    # personne.
                    if event.goal:
                        speak_goal(voice, args, event)
                    pending.put(event)
            except Exception as exc:
                log("erreur de surveillance : {}".format(exc), quiet=args.quiet)
            stopping.wait(guard.plan_wait())

    thread = threading.Thread(target=poll, name="butbutbut-watch", daemon=True)
    thread.start()

    def drain_pin():
        """Le dernier verdict d'epinglage, s'il en est arrive un."""
        follow = None
        fresh = False
        while True:
            try:
                follow = pinning.get_nowait()
                fresh = True
            except queue.Empty:
                break
        if not fresh:
            return
        try:
            if follow is None:
                stack.unpin()
            else:
                stack.pin(overlay.Card.pinned(follow.match, ended=follow.ended,
                                              crest=crest))
        except Exception as exc:
            # Une carte qui reste des heures a l'ecran finira par tomber sur un
            # ecran debranche ou un gestionnaire de fenetres de mauvaise humeur.
            log("echec de la carte epinglee : {}".format(exc), quiet=args.quiet)

    def drain():
        # L'epinglee d'abord : sa taille decide de la place des fugaces, donc
        # un but arrive dans le meme tour se pose du premier coup au bon
        # endroit, au lieu d'etre deplace juste apres.
        drain_pin()
        # Le son sans contexte n'est resolu qu'une fois : il ne sert qu'a la
        # duree des cartes muettes, alors qu'un but choisit son fichier.
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
                    # Temps forts, expulsion, avant-match, rattrapage : carte
                    # seule, pas de son. La duree ne depend donc pas de celle
                    # du jingle - et le resume de veille, qui a plusieurs
                    # lignes a lire, reste un peu plus longtemps.
                    default = (CATCHUP_DURATION if event.kind == watcher.CATCHUP
                               else PHASE_DURATION)
                    stack.push(overlay.Card.from_event(event, crest),
                               duration=args.duration or default)
                    continue

                if event.goal:
                    chosen = resolve_sound(args, event)
                else:
                    if media is None:
                        media = resolve_sound(args)
                    chosen = media
                stack.push(overlay.Card.from_event(event, crest), duration=chosen[1])
                if event.goal:
                    play_goal_sound(chosen[0])
            except Exception as exc:
                log("echec de l'affichage : {}".format(exc), quiet=args.quiet)

        # `and pending.empty()` : un but depose dans la file juste apres que la
        # boucle ci-dessus l'a trouvee vide, et juste avant que le fil de
        # surveillance s'arrete, se perdait sinon. Le fil ne depose plus rien
        # une fois `stopping` leve, donc la file est bien vide pour de bon.
        if stopping.is_set() and pending.empty():
            stack.stop()

    stack.every(overlay.PUMP_MS, drain)
    try:
        stack.run()
    finally:
        # La boucle tkinter rendue, le fil de surveillance peut etre en plein
        # reporter.update(), c'est-a-dire en train d'ecrire le fichier d'etat.
        # Rendre la main sans l'attendre laisse la suite - l'effacement de cet
        # etat, la fin du processus - passer par-dessus une ecriture en cours,
        # et un fil demon n'y change rien : il est tue net, au milieu de sa
        # phrase. On leve donc `stopping` (sa longue attente se reveille la) et
        # on lui laisse le temps de sortir de lui-meme.
        stopping.set()
        thread.join(WATCH_JOIN)
        if thread.is_alive():
            # Il tient un releve reseau qui ne repond pas. On ne retient pas
            # l'arret pour lui - c'est un fil demon, le processus s'en va -
            # mais on le dit, parce qu'un etat a moitie ecrit se lira ailleurs.
            log("le fil de surveillance n'a pas rendu la main en {:.0f}s"
                .format(WATCH_JOIN), quiet=args.quiet)


def do_replay(args) -> int:
    """Rejoue un enregistrement : memes cartes, meme son, meme journal.

    Tout ce qui suit est le do_daemon() d'un soir de match, a quatre choses
    pres - les trois premieres sont le sujet meme de la commande :

      - la source est un fichier au lieu du reseau (l'`opener` du Player) ;
      - le temps avance a `--speed` fois la vitesse reelle (la `Pace`, qui
        tient lieu d'evenement d'arret aux boucles de surveillance) ;
      - le journal, l'etat et le pid vont dans un bac a sable (sandbox_paths) ;
      - aucun `hush` n'est passe aux boucles de surveillance : `--quiet-hours`
        et `--quiet-while-presenting` restent sans effet en rejeu. Un rejeu est
        une commande qu'on vient de taper ; la taire parce qu'il est 3 h
        ressemblerait a une panne ;
      - aucune voix non plus : `--speak` ne parle pas en rejeu. Une soiree
        rejouee a `--speed 60` reduit une mi-temps a trente secondes, ou une
        phrase de trois secondes par but ne raconterait plus rien - elle
        parlerait encore du premier but que le match serait fini. Le crochet se
        tait ici pour une raison voisine.

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
        # Le rejeu emprunte les memes chemins que le direct, carte epinglee
        # comprise : c'est justement la qu'on la regle sans attendre un match.
        pin = pinned.Pin(args.pin,
                         on_log=lambda message: log(message, quiet=args.quiet))
        try:
            if stack is None:
                _watch_headless(guard, args, pace, reporter, pin)
            else:
                _watch_with_cards(guard, args, pace, stack, reporter, pin, crest)
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


def speak_demo(args, card):
    """Fait dire la carte de demo par --test --speak. Rend la voix, a fermer.

    La phrase est celle du crochet, montee sur les morceaux de la carte plutot
    que sur un evenement : la demo n'en a pas, et elle merite quand meme la
    phrase que le daemon dira le soir venu.
    """
    voice = speech.Voice(args.speak, lang=i18n.language(),
                         on_log=lambda message: print(tr("butbutbut : {}",
                                                         message)))
    if voice:
        print(tr("butbutbut : voix - {}", voice.describe()))
        voice.say(hook.phrase(card.title, card.league, card.text_line(),
                              card.detail, card.minute),
                  after=0.0 if args.no_sound else speech.AFTER_SOUND)
    return voice


def do_test(args) -> int:
    from . import overlay

    selection = leagues.resolve(args.leagues, args.exclude)
    count = max(1, int(args.test))
    # Les ecussons qui manquent partent se telecharger : le prochain --test les
    # aura. Celui-ci s'affiche sans attendre, exactement comme un vrai but.
    crest = crest_cache(args)
    cards = [overlay.Card.demo(selection[i % len(selection)], crest)
             for i in range(count)]

    # Avec --pin, la demo montre aussi la carte epinglee : c'est la seule facon
    # d'en regler la taille, le coin et l'ecran sans attendre un vrai match.
    # L'equipe demandee n'y change rien - la demo n'a pas de reseau, elle
    # affiche le match d'exemple du championnat.
    anchor = overlay.Card.demo_pinned(selection[0], crest) if args.pin else None

    for card in cards:
        print(tr("butbutbut : demo - [{}] {} - {}",
            card.league, card.text_line(), card.detail))
    if anchor is not None:
        print(tr("butbutbut : demo epinglee - [{}] {}",
                 anchor.league, anchor.text_line()))

    path, duration = resolve_sound(args)

    # Sans ca, regler --speak voudrait dire attendre un vrai but pour savoir
    # si la machine parle - la meme demi-journee de mise au point que
    # --test-hook a supprimee pour le crochet.
    voice = speak_demo(args, cards[0])

    if args.no_overlay:
        handle = play_goal_sound(path)
        time.sleep(min(duration, 5.0))
        sound.release(handle)
        voice.close(2.0)
        return 0

    try:
        overlay.show(cards, duration=duration, sound_path=path,
                     screen=args.screen, position=args.position,
                     opacity=args.opacity, scale=args.scale,
                     retry_fullscreen=args.retry_fullscreen,
                     pinned=anchor,
                     on_log=lambda message: print(tr("butbutbut : {}", message)))
    except overlay.TkinterMissing as exc:
        print(str(exc), file=sys.stderr)
        return 4
    finally:
        # On laisse finir les ecussons partis en fond : sinon la demo,
        # toujours tuee juste apres, ne les aurait jamais.
        crest.join(3.0)
        voice.close(2.0)
    return 0


def do_test_hook(args) -> int:
    """Lance la commande de --on-goal sur un but fabrique, et rend compte.

    C'est le seul endroit ou on l'attend : regler un crochet en guettant un
    vrai but serait une mise au point d'une demi-journee. On montre donc les
    variables, la sortie et le code de retour, la ou le daemon se tait.
    """
    if not args.on_goal:
        print(tr("butbutbut : aucune commande a essayer. Passe --on-goal "
                 "\"...\", ou pose la cle on_goal dans le fichier de "
                 "configuration."), file=sys.stderr)
        return 2

    values = hook.demo()
    print(tr("butbutbut : but fabrique, la commande recevra"))
    for key in sorted(values):
        print("  {:<18} {}".format(key, values[key]))
    print(tr("\n  commande    : {}", args.on_goal))

    runner = hook.Runner(args.on_goal)
    try:
        code, output = runner.call(values)
    except hook.Timeout:
        print(tr("  resultat    : tuee apres {:.0f}s, elle ne rendait pas la main",
                 runner.timeout), file=sys.stderr)
        return 1
    except Exception as exc:
        print(tr("  resultat    : impossible de la lancer ({})", exc),
              file=sys.stderr)
        return 1

    print(tr("  resultat    : code de sortie {}", code))
    if output:
        print(tr("  sortie      :"))
        for line in output.splitlines():
            print("    " + line)
    if code:
        # Le daemon, lui, se contenterait d'une ligne de journal : ici on est
        # devant son terminal, autant que le shell le sache aussi.
        return 1
    return 0


def do_scores(args) -> int:
    """Les matchs du jour. Un match en differe apparait, son score est masque.

    Trois reponses etaient possibles pour --spoiler-free ici, et deux sont
    mauvaises. Tout afficher trahirait le seul reglage qu'on est venu chercher.
    Faire disparaitre le match serait pire encore : on ne saurait plus s'il a
    lieu, a quelle heure, ni meme si le mot tape designe bien ce club-la - et
    c'est justement le jour ou l'on regarde ce match qu'on ouvre --scores.

    Reste le compromis : la ligne existe, le score devient "? - ?", et rien de
    ce qui pourrait le reconstituer ne s'affiche - ni les buteurs, ni l'etat du
    match. Un match termine ressemble ainsi a un match en cours, sinon un
    simple "termine" a la 80e minute suffirait a dire que c'est plie.
    """
    selection = leagues.resolve(args.leagues, args.exclude)
    chosen = team_filter(args)
    quiet_teams = spoiler_filter(args)
    now = datetime.now(timezone.utc)
    total = 0
    masked = 0

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
            hidden = quiet_teams is not None and quiet_teams.covers(match)
            home_score, away_score = match.home_score, match.away_score
            # 'note' et non 'state' : le module state est importe ici.
            if hidden:
                masked += 1
                mark, note = "?", tr("sans spoiler")
                home_score = away_score = "?"
            elif match.live:
                mark, note = ">", match.detail or match.clock or tr("en cours")
            elif match.finished:
                mark, note = " ", match.detail or tr("termine")
            else:
                mark, note = " ", _kickoff_text(match, now)
            print(tr("  {} {:>22} {} - {} {:<22} {}",
                mark, match.home, home_score, away_score,
                match.away, note))
            if hidden:
                continue        # les buteurs reconstitueraient le score
            for play in match.plays:
                side = match.home if play.team_id == match.home_id else match.away
                print(tr("      {:<22} {}", side, play.summary()))

    print(tr("\n{} match(s), '>' = en cours.", total))
    if masked:
        print(tr("'?' = sans spoiler : {} match(s) masque(s). "
                 "Le journal, lui, a tout : butbutbut --today.", masked))
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


# ------------------------------------------------------- prochains matchs ----

def _next_request(value) -> tuple:
    """Ce que --next a recu : (jours, equipes).

    Une valeur faite de chiffres est une fenetre, tout le reste est un nom
    d'equipe. Aucun club ne s'appelle "7" et personne n'ecrit une duree en
    lettres : l'ambiguite ne se produit pas. La liste est acceptee pour pouvoir
    tout dire d'un coup - `--next om,psg,3`.
    """
    days = DEFAULT_NEXT_DAYS
    wanted = []
    for token in str(value or "").replace(";", ",").split(","):
        token = token.strip()
        if not token:
            continue
        if token.isdigit():
            days = max(1, min(MAX_NEXT_DAYS, int(token)))
        else:
            wanted.append(token)
    return days, ",".join(wanted)


def _next_filter(args, wanted):
    """Le filtre par equipe de --next : celui de --teams, plus ce qui suit --next.

    Le nom donne a --next n'est pas confronte au catalogue comme le fait
    --teams : la verification coute une requete par competition, ce qui
    doublerait le cout d'une commande ponctuelle. Une faute de frappe se voit
    autrement, dans la phrase du calendrier vide, qui repete le mot cherche.
    """
    both = ",".join(part for part in (args.teams, wanted) if part)
    chosen = teams.Filter(both, args.exclude_teams)
    return chosen if chosen.active else None


def next_matches(matches, now, days, today=None) -> list:
    """Ceux de ces matchs qui restent a jouer dans la fenetre demandee.

    Un match commence n'est plus un prochain match : `--scores` est la pour ce
    qui se joue. Un match dont l'heure est passee sans que rien ne demarre
    (retard, report) ne repond pas non plus a la question posee.

    La borne haute est la fin du dernier jour **local** de la fenetre, et non
    "dans N fois 24 h" : une fenetre qui se refermerait au milieu d'une soiree
    couperait une affiche en deux sans que personne comprenne pourquoi.
    """
    today = today or datetime.now().date()
    last_day = today + timedelta(days=max(1, days) - 1)

    kept = []
    for match in matches:
        if match.start is None or match.live or match.finished:
            continue
        if match.start <= now:
            continue
        if match.start.astimezone().date() > last_day:
            continue
        kept.append(match)
    kept.sort(key=lambda match: (match.start, match.league.name, match.home))
    return kept


def group_by_day(matches) -> list:
    """[(jour, [(competition, [matchs])])], dans l'ordre chronologique.

    Le regroupement se fait sur le jour **local** et non sur celui d'UTC : un
    match du samedi 21 h a Marseille se joue le samedi, pas le dimanche a 1 h
    du matin comme la source l'ecrit.
    """
    order = []
    days = {}
    for match in matches:
        day = match.start.astimezone().date()
        if day not in days:
            days[day] = []
            order.append(day)
        rows = days[day]
        for name, group in rows:
            if name == match.league.name:
                group.append(match)
                break
        else:
            rows.append((match.league.name, [match]))
    return [(day, days[day]) for day in order]


def _day_title(day, today) -> str:
    """"mardi 08/09", et le mot du jour quand il y en a un.

    Le calendrier ecrit les jours en toutes lettres, la ou le recapitulatif du
    journal les abrege : on lit une affiche, on parcourt un releve.
    """
    line = "{} {:%d/%m}".format(WEEKDAYS_FULL[day.weekday()], day)
    elapsed = (day - today).days
    if elapsed == 0:
        return line + " (aujourd'hui)"
    if elapsed == 1:
        return line + " (demain)"
    return line


def _delay_text(seconds) -> str:
    """Le temps qui reste avant le coup d'envoi, en une poignee de signes.

    L'heure du match dit *quand*, cette colonne dit *dans combien de temps* :
    c'est la vraie reponse a la question, et elle evite de compter les jours
    sur ses doigts.
    """
    if seconds < 3600:
        return "dans {} min".format(max(1, int(seconds // 60)))
    if seconds < 48 * 3600:
        return "dans {} h".format(int(seconds // 3600))
    return "dans {} j".format(int(seconds // 86400))


def _nothing_text(days, chosen, selection) -> str:
    """La phrase du calendrier vide.

    Un tableau sans ligne laisse croire a une panne. Il faut dire ce qui a ete
    cherche, ou, et sur combien de temps : c'est aussi ce qui rend visible une
    faute de frappe dans le nom d'equipe.
    """
    where = leagues.describe(selection)
    if chosen is not None and chosen.wanted_tokens:
        where = "{} dans {}".format(", ".join(chosen.wanted_tokens), where)
    if days == 1:
        return "Rien au programme aujourd'hui pour {}.".format(where)
    return "Rien au programme dans les {} prochains jours pour {}.".format(
        days, where)


def do_next(args) -> int:
    """Les prochains matchs, groupes par jour puis par competition."""
    selection = leagues.resolve(args.leagues, args.exclude)
    days, wanted = _next_request(args.next)
    chosen = _next_filter(args, wanted)

    now = datetime.now(timezone.utc)
    today = datetime.now().date()
    # La fenetre demandee a la source est elargie d'un jour de chaque cote :
    # `dates` compte les jours dans le fuseau d'ESPN, pas dans le notre, et un
    # match de 21 h en France peut y tomber la veille ou le lendemain. Le tri
    # fin est fait ici, sur les vraies heures de coup d'envoi.
    span = espn.date_span(today - timedelta(days=1),
                          today + timedelta(days=days))

    found = []
    unreachable = []
    total = len(selection)
    for index, league in enumerate(selection):
        try:
            matches = espn.scoreboard(league, dates=span)
        except espn.SourceError as exc:
            # Une competition muette n'emporte pas les autres : mieux vaut un
            # calendrier incomplet, et dit comme tel, qu'une erreur a la place
            # de tout ce qui a bien repondu.
            unreachable.append((league, exc))
            matches = []
        if chosen is not None:
            matches = [match for match in matches if chosen.matches(match)]
        found.extend(next_matches(matches, now, days, today=today))
        if index + 1 < total:
            time.sleep(NEXT_PAUSE)

    found.sort(key=lambda match: (match.start, match.league.name, match.home))
    grouped = group_by_day(found)

    print(tr("butbutbut : prochains matchs - {}, {} jour(s)",
             leagues.describe(selection), days))
    if chosen is not None:
        print(tr("  {}", chosen.describe()))

    for day, rows in grouped:
        print(tr("\n{}", _day_title(day, today)))
        for name, matches in rows:
            print(tr("  {}", name))
            for match in matches:
                print("      {:%H:%M}  {:>22} - {:<22} {}".format(
                    match.start.astimezone(), match.home, match.away,
                    _delay_text(match.seconds_until_kickoff(now))).rstrip())

    if found:
        print(tr("\n{} match(s) a venir dans {} competition(s), sur {} jour(s).",
                 len(found), len({m.league.name for m in found}), days))
    elif len(unreachable) == total:
        print(tr("\nAucune competition n'a repondu : rien a annoncer."))
    else:
        print(tr("\n{}", _nothing_text(days, chosen, selection)))

    for league, exc in unreachable:
        print(tr("  ({} injoignable : {})", league.name, exc))
    if unreachable and len(unreachable) < total:
        print(tr("  (le calendrier ci-dessus est donc incomplet ; les autres "
                 "competitions ont repondu)"))
    return 1 if unreachable and len(unreachable) == total else 0


# ------------------------------------------------------------- classement ----
# --scores dit ce qui se joue, --next ce qui arrive, --top-scorers ce qu'on a vu
# passer. Restait "ils sont ou, au classement ?", la seule question qu'un
# supporter pose sans regarder de match.
#
# Ce qui a ete arbitre ici :
#
#   - les colonnes viennent du sport et de nulle part ailleurs (sports.py). Un
#     classement de hockey n'a pas de colonne de matchs nuls parce que le
#     hockey n'a pas de match nul, pas parce qu'on aurait oublie de la remplir ;
#   - on ne calcule aucun rang : les regles de depart a egalite changent d'une
#     competition a l'autre, et les refaire, c'est se tromper un jour de
#     printemps sur une competition qu'on ne regarde pas. Le rang affiche est
#     celui que la source publie (voir espn._parse_group) ;
#   - une competition sans classement (une coupe, une intersaison) le dit en
#     toutes lettres, avec l'endroit ou on est alle voir. Un tableau vide
#     ressemble trop a une panne.


def _table_request(value) -> tuple:
    """Ce que --table a recu : (competitions, equipes).

    Un jeton que le catalogue reconnait est une competition, tout le reste est
    une equipe. C'est la meme ruse que --next, qui distingue les jours des
    equipes en regardant si le mot est un nombre : ici la question posee au
    catalogue est aussi tranchee, et aucun club ne s'appelle "l1" ni "big5".
    """
    picked = []
    wanted = []
    for token in str(value or "").replace(";", ",").split(","):
        token = token.strip()
        if not token:
            continue
        (picked if leagues.names_a_league(token) else wanted).append(token)
    return ",".join(picked), ",".join(wanted)


def _table_filter(args, wanted):
    """Les equipes a surligner : --teams, plus ce qui suit --table.

    --exclude-teams n'entre pas ici, et c'est volontaire : on ne retire pas une
    equipe d'un classement. Le classement est un tout, les rangs se comptent
    les uns par rapport aux autres, et une ligne manquante ferait un tableau
    qui ment. Taire un match, oui ; trouer un classement, non.

    Comme pour --next, le mot n'est pas confronte au catalogue des equipes :
    ca couterait une requete par competition. Une faute de frappe se voit
    ailleurs, dans la phrase finale qui repete le mot cherche.
    """
    both = ",".join(part for part in (args.teams, wanted) if part)
    chosen = teams.Filter(both)
    return chosen if chosen.active else None


def _table_name(name) -> str:
    """Le nom du club, coupe a la largeur de sa colonne.

    espn.py rend deja le nom court quand le nom complet depasse ; il reste les
    clubs dont le nom court lui-meme deborde, et la colonne qui glisse d'un
    caractere derange plus que le mot ampute.
    """
    name = str(name or "")
    return name if len(name) <= TABLE_NAME_WIDTH else name[:TABLE_NAME_WIDTH]


def table_header(sport) -> str:
    """La ligne d'en-tete du classement, colonnes du sport comprises."""
    cells = "".join("{:>{}}".format(title, TABLE_CELL_WIDTH)
                    for title, _keys in sport.table)
    return "  {:>2}  {:<{}}{}".format("#", "Equipe", TABLE_NAME_WIDTH,
                                      cells).rstrip()


def table_row(row, sport, marked=False) -> str:
    """Une ligne de classement. `marked` la surligne d'un chevron.

    Un chevron et pas une couleur : le terminal de quelqu'un peut etre en noir
    sur blanc, sur fond clair, ou redirige dans un fichier. C'est deja le signe
    que --scores emploie pour "en cours", et il ne coute rien a personne.
    """
    cells = "".join("{:>{}}".format(row.cell(keys), TABLE_CELL_WIDTH)
                    for _title, keys in sport.table)
    return "{} {:>2}  {:<{}}{}".format(
        ">" if marked else " ", row.rank, _table_name(row.team),
        TABLE_NAME_WIDTH, cells).rstrip()


def table_groups(table, chosen) -> list:
    """Les blocs a montrer : tous, ou seulement ceux ou l'equipe figure.

    "--table om" ne demande pas la Ligue 1, il demande la ligne de l'OM - et le
    classement de sa competition avec, sans quoi un rang tout seul ne veut rien
    dire. On garde donc le bloc entier des qu'une de ses lignes repond.
    """
    if chosen is None:
        return [group for group in table.groups if group.rows]
    return [group for group in table.groups
            if any(chosen.team_matches(row.names) for row in group.rows)]


def _no_table_text(league) -> str:
    """La ligne d'une competition sans classement.

    Elle nomme l'endroit exact ou on est alle voir : c'est ce qui distingue
    "cette coupe n'a pas de classement" de "butbutbut s'est trompe d'adresse",
    et c'est la seule chose qu'on puisse dire honnetement des deux.
    """
    return "{} : aucun classement publie sous {}/{}".format(
        league.name, league.sport.code, league.slug)


def do_table(args) -> int:
    """Le classement des competitions surveillees."""
    picked, wanted = _table_request(args.table)
    try:
        selection = leagues.resolve(picked or args.leagues, args.exclude)
    except leagues.SelectionError as exc:
        # Les competitions de --table ne passent pas par le controle de main() :
        # elles arrivent dans un autre argument, elles se verifient ici.
        print(tr("butbutbut : {}", exc), file=sys.stderr)
        return 2
    chosen = _table_filter(args, wanted)

    print(tr("butbutbut : classement - {}", leagues.describe(selection)))
    if chosen is not None:
        print(tr("  {}", chosen.describe()))

    shown = 0
    silent = []
    unreachable = []
    total = len(selection)
    for index, league in enumerate(selection):
        # La pause se prend AVANT la requete plutot qu'apres : elle vaut alors
        # pour toutes les sorties de boucle, y compris celle d'une competition
        # injoignable, sans avoir a la repeter a chaque branche.
        if index:
            time.sleep(TABLE_PAUSE)
        try:
            table = espn.standings(league)
        except espn.SourceError as exc:
            # Une competition muette n'emporte pas les autres, exactement comme
            # pour --next : un classement partiel, et dit comme tel, vaut mieux
            # qu'une erreur a la place de tout ce qui a bien repondu.
            unreachable.append((league, exc))
            continue

        groups = table_groups(table, chosen)
        if groups:
            shown += 1
            _print_table(table, groups, chosen)
        elif table.empty:
            # Rien a montrer, et deux raisons possibles : la source n'a pas de
            # classement (on le dit), ou l'equipe cherchee n'est pas de cette
            # competition-la (on se tait, elle est peut-etre dans la suivante).
            silent.append(league)

    if not shown:
        if len(unreachable) == total:
            print(tr("\nAucune competition n'a repondu : rien a classer."))
        else:
            print(tr("\n{}", _nothing_ranked_text(chosen, selection)))
    for league in silent:
        print(tr("  ({})", _no_table_text(league)))
    if silent:
        # La raison, une seule fois : elle est la meme pour toutes, et la
        # repeter sur trente-six lignes de coupes noierait le classement.
        print(tr("  (une coupe se joue en tableau ; hors saison, la source "
                 "n'a rien a servir)"))
    for league, exc in unreachable:
        print(tr("  ({} injoignable : {})", league.name, exc))
    if unreachable and len(unreachable) < total:
        print(tr("  (le classement ci-dessus est donc incomplet ; les autres "
                 "competitions ont repondu)"))
    return 1 if unreachable and len(unreachable) == total else 0


def _print_table(table, groups, chosen) -> None:
    """Un classement : son titre, ses blocs, ses lignes."""
    season = " ({})".format(table.season) if table.season else ""
    print(tr("\n{}{}", table.league.name, season))
    for group in groups:
        # Le nom du bloc n'est ecrit que s'il y en a plusieurs : sur un
        # championnat, la source appelle son unique bloc "French Ligue 1
        # 2026-27", ce qui ne fait que repeter la ligne du dessus.
        if len(table.groups) > 1 and group.name:
            print(tr("  {}", group.name))
        print(table_header(table.sport))
        for row in group.rows:
            marked = chosen is not None and chosen.team_matches(row.names)
            print(table_row(row, table.sport, marked=marked))


def _nothing_ranked_text(chosen, selection) -> str:
    """La phrase du classement vide : ce qui a ete cherche, et ou.

    Meme raison que pour --next : un ecran sans tableau laisse croire a une
    panne, et c'est la que se voit une faute de frappe dans le nom d'equipe.
    """
    where = leagues.describe(selection)
    if chosen is not None and chosen.wanted_tokens:
        return "Aucune ligne pour {} dans les classements de {}.".format(
            ", ".join(chosen.wanted_tokens), where)
    return "Aucun classement a afficher pour {}.".format(where)


def _print_activity(pid, quiet_teams=None) -> None:
    """L'activite du daemon, relue dans le fichier d'etat.

    Le fichier pid dit qu'un processus existe, jamais qu'il travaille : sans
    ces lignes, un daemon bloque sur une requete est indistinguable d'un daemon
    qui suit trois matchs.

    `quiet_teams` masque le score des matchs regardes en differe, comme le fait
    --scores : une ligne "en cours" en dit autant qu'une carte.
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
            home, away = row.get("home", "?"), row.get("away", "?")
            home_score = row.get("home_score", "?")
            away_score = row.get("away_score", "?")
            clock = row.get("clock", "")
            if quiet_teams is not None and quiet_teams.covers_names((home,),
                                                                    (away,)):
                home_score = away_score = "?"
                clock = "(sans spoiler)"
            print("                [{}] {} {} - {} {}  {}".format(
                row.get("league", "?"), home, home_score, away_score,
                away, clock).rstrip())

    goals = data.get("goals_today", 0) if data.get("day") == state.today() else 0
    print(tr("  buts du jour: {}  (le detail : butbutbut --today)", goals))


def pin_summary(token) -> str:
    """La ligne "epinglee" de --status : le mot demande, et ce qu'il suit.

    Le mot vient de la ligne de commande ou du fichier de configuration ; le
    match, lui, vient du fichier d'etat, donc du daemon qui tourne vraiment.
    Les deux peuvent diverger - daemon lance avec d'autres options, fichier
    modifie depuis - et c'est justement ce qu'on veut voir.
    """
    data = state.read(paths()["state"])
    if not data or state.is_stale(data):
        return "{} (etat inconnu : voir la ligne releve)".format(token)
    row = data.get("pinned")
    if not isinstance(row, dict):
        return "{} (aucun match en cours)".format(token)
    return "{} -> [{}] {} {} - {} {}  {}".format(
        token, row.get("league", "?"), row.get("home", "?"),
        row.get("home_score", "?"), row.get("away_score", "?"),
        row.get("away", "?"), row.get("clock", "")).rstrip()
SOUNDS_SHOWN = 12       # au-dela, --status resume plutot que de derouler


def _sound_arming(sounds, args, selection=()) -> list:
    """Ce que chaque fichier du dossier `sound` arme, d'apres son seul nom.

    C'est la reponse a la question que se pose qui vient d'y deposer un
    fichier : est-ce que butbutbut a compris ce nom-la ? On repond donc avant
    le prochain but, sans match sous la main - d'ou les limites de
    sound.declared() : un nom de club inconnu de --teams passe pour du fond
    sonore, et jouera pourtant pour son equipe.
    """
    clubs = sound_clubs(args)
    followed = team_filter(args)
    watched = bool(followed is not None and followed.wanted)
    slugs = {league.slug for league in selection}

    rows = []
    for path in sounds[:SOUNDS_SHOWN]:
        tier, target = sound.declared(path, clubs=clubs)
        if tier == sound.TIER_CONCEDED:
            label = tr("quand une equipe suivie encaisse")
            if not watched:
                label += tr("  (jamais : aucune equipe suivie, voir --teams)")
        elif tier == sound.TIER_LEAGUE:
            label = tr("les buts de {}", target.name)
            if target.slug not in slugs:
                label += tr("  (competition non suivie)")
        elif tier == sound.TIER_TEAM:
            label = tr("quand cette equipe marque")
        else:
            label = tr("tirage general")
        rows.append((path.name, label))

    if len(sounds) > SOUNDS_SHOWN:
        rows.append(("...", tr("et {} autre(s)", len(sounds) - SOUNDS_SHOWN)))
    return rows


def _named_arming(assigned, args, selection=()) -> list:
    """Ce que chaque paire de --sound-for arme, et ce qui cloche s'il y a lieu.

    Plus sur que _sound_arming() : le mot a ete donne, il n'y a rien a deviner
    dans un nom de fichier. Le chemin, lui, est reverifie a chaque --status -
    le demarrage remonte parfois a des semaines, et un disque externe se
    debranche.
    """
    followed = team_filter(args)
    watched = bool(followed is not None and followed.wanted)
    slugs = {league.slug for league in selection}

    rows = []
    for one in assigned:
        target = leagues.designates(one.token)
        if sound.is_conceded_word(one.token):
            label = tr("quand une equipe suivie encaisse")
            if not watched:
                label += tr("  (jamais : aucune equipe suivie, voir --teams)")
        elif target is not None:
            label = tr("les buts de {}", target.name)
            if target.slug not in slugs:
                label += tr("  (competition non suivie)")
        else:
            label = tr("quand cette equipe marque")
        problem = sound.unusable(one.path)
        if problem is not None:
            label += tr("  ({})", problem)
        rows.append(("{} -> {}".format(one.token, one.path.name), label))
    return rows


def _announced_cadence(data):
    key = "interval" if data.get("matches") else "idle_interval"
    return data.get(key, "?")


def _day_of(moment) -> str:
    """Un instant, ecrit comme le journal l'ecrit."""
    return "{:%Y-%m-%d}".format(moment)


def _read_day(text) -> str:
    """Le jour derriere un --since, ou ValueError disant le format attendu."""
    try:
        return _day_of(datetime.strptime(str(text).strip(), "%Y-%m-%d"))
    except (ValueError, TypeError):
        raise ValueError(tr(
            "date illisible : {!r}. Format attendu : AAAA-MM-JJ, "
            "par exemple --since {}", text, _day_of(datetime.now())))


def _span_of(first, last) -> int:
    """Le nombre de jours de `first` a `last`, bornes comprises (au moins 1)."""
    start = datetime.strptime(first, "%Y-%m-%d")
    end = datetime.strptime(last, "%Y-%m-%d")
    return max(1, (end - start).days + 1)


class Window:
    """La periode d'un recapitulatif : deux jours du journal, bornes comprises.

    Les bornes sont des chaines AAAA-MM-JJ, la forme meme du journal : elles
    partent telles quelles dans journal.goals_between(), qui compare du texte.
    """

    __slots__ = ("first", "last", "span", "whole")

    def __init__(self, first=None, last=None, span=0, whole=False):
        self.first = first      # None : depuis la premiere ligne du journal
        self.last = last
        self.span = span        # jours couverts ; 0 quand la fenetre est tout
        self.whole = whole

    def describe(self) -> str:
        if self.whole:
            return tr("depuis le debut du journal")
        if self.span == 1:
            # Un seul jour : pas de jour de la semaine, c'est l'en-tete que
            # `--today` rend depuis toujours.
            return tr("le {}", _plain(self.first, "%d/%m/%Y"))
        return tr("du {} au {}", _stamp(self.first, "%d/%m/%Y"),
                  _stamp(self.last, "%d/%m/%Y"))


def window_of(args, whole_by_default: bool = False) -> Window:
    """La fenetre demandee par --today, --week, --month ou --since.

    `--since` l'emporte sur `--week` et `--month` : c'est la plus explicite des
    trois, et refuser la combinaison ferait une erreur de plus a expliquer.
    Sans aucune des quatre, la fenetre est la journee en cours - le
    comportement historique de `--today` - sauf pour le classement des
    buteurs, qui n'a d'interet qu'accumule et prend alors tout le journal.
    """
    last = _day_of(datetime.now())
    since = getattr(args, "since", None)
    if since is not None:
        # `is not None` et pas la simple verite : `--since ''` est une date
        # vide, donc une erreur a expliquer, pas une option absente.
        first = _read_day(since)            # leve ValueError si c'est illisible
        return Window(first, last, _span_of(first, last))
    if getattr(args, "month", False):
        span = MONTH_DAYS
    elif getattr(args, "week", False):
        span = WEEK_DAYS
    elif whole_by_default and not getattr(args, "today", False):
        return Window(whole=True)
    else:
        span = 1
    # Les 7 derniers jours, c'est aujourd'hui et les six d'avant : la journee
    # en cours compte, sinon --week ne dirait rien du match de ce soir.
    first = _day_of(datetime.now() - timedelta(days=span - 1))
    return Window(first, last, span)


def _window_goals(args, window) -> list:
    """Les buts de la fenetre, une seule lecture, filtre par equipe applique."""
    found = journal.goals_between(paths()["log"], window.first, window.last)
    chosen = team_filter(args)
    if chosen is None:
        return found
    # journal.Entry porte .home et .away : Filter.matches sait s'en contenter,
    # a defaut des noms alternatifs que seul un match de la source connait.
    return [entry for entry in found if chosen.matches(entry)]


def _header(window) -> str:
    """L'en-tete d'un recapitulatif.

    Une journee garde mot pour mot la phrase de `--today`, catalogues de
    traduction compris : c'est la meme commande, elle n'a pas a changer de
    formulation en passant par le chemin commun.
    """
    if window.span == 1 and not window.whole:
        return tr("butbutbut : buts signales le {:%d/%m/%Y}",
                  datetime.strptime(window.first, "%Y-%m-%d"))
    return tr("butbutbut : buts signales {}", window.describe())


def _empty_note(window, log_path) -> str:
    """La phrase d'une fenetre sans but : dire pourquoi, pas seulement quoi.

    Le retour a la ligne et les deux espaces font partie de la phrase, comme
    partout ici : c'est elle, entiere, qui sert de cle de traduction.
    """
    try:
        blank = not log_path.exists() or log_path.stat().st_size == 0
    except OSError:
        blank = False
    if blank:
        return tr("\n  (journal vide : aucun but n'y a encore ete ecrit)")
    if window.whole:
        return tr("\n  (aucun but dans le journal)")
    if window.span == 1:
        return tr("\n  (aucun but pour l'instant)")
    return tr("\n  (aucun but sur cette periode)")


def _plain(day, shape) -> str:
    """Un jour du journal, mis a l'endroit. Rendu tel quel s'il est illisible.

    Le journal est une source a demi sure : ses dates sortent d'une expression
    reguliere qui compte les chiffres sans verifier qu'ils font un calendrier.
    """
    try:
        return "{:{}}".format(datetime.strptime(day, "%Y-%m-%d"), shape)
    except (ValueError, TypeError):
        return str(day)


def _stamp(day, shape) -> str:
    """Le meme jour, precede de son jour de semaine.

    Sur plusieurs jours, c'est le jour de semaine qu'on cherche : personne ne
    retient la date du samedi de la semaine derniere, tout le monde retient
    qu'il y avait un match samedi.
    """
    try:
        moment = datetime.strptime(day, "%Y-%m-%d")
    except (ValueError, TypeError):
        return str(day)
    return "{} {:{}}".format(WEEKDAYS[moment.weekday()], moment, shape)


def _who(entry) -> str:
    """Le buteur et la minute du match, ou a defaut ce que le journal en dit."""
    parts = (entry.scorer or entry.detail, entry.minute)
    return " ".join(part for part in parts if part)


def do_recap(args) -> int:
    """Le recapitulatif des buts d'une fenetre de dates, relu dans le journal.

    Un seul chemin pour --today, --week, --month et --since : meme lecture,
    meme analyseur, seule la fenetre change. Ne restent propres a chacun que
    l'en-tete et la densite de l'affichage, qui se decident a l'arrivee.
    """
    try:
        window = window_of(args)
    except ValueError as exc:
        print(tr("butbutbut : {}", exc), file=sys.stderr)
        return 2

    p = paths()
    entries = _window_goals(args, window)

    print(_header(window))
    if not entries:
        print(_empty_note(window, p["log"]))
        print(tr("\nJournal : {}", p["log"]))
        return 0

    if window.span == 1:
        _print_one_day(entries)
    else:
        _print_many_days(entries)
    return 0


def _print_one_day(entries) -> None:
    """Une journee : groupee par competition, une ligne par but.

    La mise en forme historique de `--today`, et elle tient : une soiree c'est
    une poignee de buts, la competition en tete de bloc se lit mieux qu'une
    colonne repetee a chaque ligne, et l'heure de detection a encore un sens
    quand on rouvre le terminal le lendemain matin.
    """
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


def _print_many_days(entries) -> None:
    """Plusieurs jours : jour par jour, et d'autant plus serre qu'il y a a dire.

    Grouper par jour ET par competition, comme le fait une journee seule,
    poserait un titre toutes les deux lignes : illisible des la deuxieme
    semaine. Le jour reste donc le seul en-tete et la competition passe en
    colonne, alignee, l'oeil descendant une colonne au lieu de relire chaque
    ligne.

    Reste que le detail ne rentre pas toujours : trente jours de Ligue 1 font
    trois cents buts, et une semaine des cinq championnats guere moins. La
    densite se decide donc sur ce qu'il y a a montrer, pas sur la largeur de la
    fenetre demandee : tant que la liste tient sur un ecran on la donne, au-dela
    chaque journee se resume a sa ligne. Le detail reste a une fenetre plus
    courte, et les noms a --top-scorers.
    """
    days = journal.by_day(entries)
    # Deux lignes par jour (la respiration et le titre) plus une par but.
    detailed = 2 * len(days) + len(entries) <= SCREEN_LINES

    if not detailed:
        print()
    for day, rows in days:
        if detailed:
            print("\n" + _stamp(day, "%d/%m/%Y"))
            for entry in rows:
                # Colonnes fixes : competition, score, buteur. L'oeil descend
                # une colonne au lieu de relire chaque ligne, et le tout tient
                # dans 80 caracteres, y compris "Bayer 04 Leverkusen".
                print("  {} {:<15.15}  {:<34.34}  {}".format(
                    " " if entry.goal else "-", entry.league,
                    entry.score_line(), _who(entry)).rstrip())
        else:
            print(_day_line(day, rows))

    _print_total(entries, len(days), detailed)


def _day_line(day, rows) -> str:
    """Le resume d'une journee en une ligne : combien de buts, et dans quoi."""
    scored = sum(1 for entry in rows if entry.goal)
    cancelled = len(rows) - scored
    counts = [(name, sum(1 for entry in items if entry.goal))
              for name, items in journal.by_league(rows)]
    # La competition la plus fournie en tete : c'est celle qu'on cherche.
    counts.sort(key=lambda row: (-row[1], row[0]))
    counts = [row for row in counts if row[1]]
    # Trois competitions au plus, puis un compte : couper un nom en deux au
    # bout de la ligne serait moins lisible que d'annoncer ce qu'on ne dit pas.
    shown = ["{} {}".format(name, count)
             for name, count in counts[:LEAGUES_SHOWN]]
    if len(counts) > LEAGUES_SHOWN:
        shown.append("+{}".format(len(counts) - LEAGUES_SHOWN))
    return "  {:<11.11}{:>3} but(s)  {:<8}{:.46}".format(
        _stamp(day, "%d/%m"), scored,
        "-{} VAR".format(cancelled) if cancelled else "",
        ", ".join(shown)).rstrip()


def _print_total(entries, days, detailed) -> None:
    """Le pied de sortie : le total, et ce que la VAR a repris."""
    kept, _orphans = journal.settle(entries)
    cancelled = sum(1 for entry in entries if not entry.goal)
    print(tr("\n{} but(s) signale(s), {} jour(s), {} competition(s).",
             len(entries) - cancelled, days, len(journal.by_league(entries))))
    if cancelled:
        print(tr("{} = but retire par la VAR ({}) : {} but(s) confirme(s).",
                 "'-'" if detailed else "'-N VAR'", cancelled, len(kept)))


def do_top_scorers(args) -> int:
    """Le classement des buteurs vus passer, sur la fenetre demandee.

    Sans --week, --month ni --since, c'est tout le journal : un classement n'a
    d'interet qu'accumule, et le journal remonte a l'installation.
    """
    try:
        window = window_of(args, whole_by_default=True)
    except ValueError as exc:
        print(tr("butbutbut : {}", exc), file=sys.stderr)
        return 2

    p = paths()
    entries = _window_goals(args, window)
    board = journal.scoreboard(entries)

    print(tr("butbutbut : buteurs vus passer {}", window.describe()))
    if not board.rows:
        print(_empty_note(window, p["log"]) if not entries else tr(
            "\n  (aucun buteur connu : la source n'avait pas encore publie "
            "l'action)"))
        print(tr("\nJournal : {}", p["log"]))
        return 0

    print()
    rank = 0
    for place, (name, count, clubs) in enumerate(board.rows[:SCORERS_SHOWN], 1):
        # Rang partage a egalite : deux buteurs a 3 buts sont deuxiemes tous
        # les deux, et le suivant quatrieme.
        if place == 1 or count != board.rows[place - 2][1]:
            rank = place
        print("  {:>3}  {:<24.24}  {:>3}  {:.26}".format(
            rank, name, count, clubs).rstrip())

    hidden = len(board.rows) - SCORERS_SHOWN
    if hidden > 0:
        print(tr("  ... et {} autre(s) buteur(s) plus bas au classement.",
                 hidden))

    print(tr("\n{} buteur(s) pour {} but(s) confirme(s) sur {} signale(s).",
             len(board.rows), board.confirmed, board.signalled))
    if board.cancelled:
        print(tr("{} but(s) retire(s) par la VAR, deduit(s) du classement.",
                 board.cancelled))
    if board.orphans:
        print(tr("{} annulation(s) sans but a retirer dans cette fenetre "
                 "(le but est tombe avant).", board.orphans))
    if board.unknown:
        print(tr("{} but(s) sans buteur connu, hors classement.",
                 board.unknown))
    return 0


def _bar(count, top) -> str:
    """Un baton d'histogramme, a l'echelle du plus haut.

    Un signe au minimum des qu'il y a un but : arrondir a rien effacerait de
    l'histogramme la tranche ou il s'est passe quelque chose, ce qui est
    exactement ce qu'on vient y lire. Un '#' plutot qu'un caractere de
    remplissage : le journal, la carte et le terminal restent en ASCII pur, et
    une barre en unicode ressort en points d'interrogation sur la moitie des
    consoles Windows.
    """
    if count <= 0 or top <= 0:
        return ""
    return "#" * max(1, int(round(count * STATS_BAR / float(top))))


def _share(count, total) -> str:
    """La part d'un compte dans un total, arrondie au point de pourcentage."""
    if not total:
        return ""
    return "{:>3}%".format(int(round(100.0 * count / total)))


def do_stats(args) -> int:
    """Les formes que le journal cache : minutes, competitions, soirees.

    Rien de nouveau n'est lu ici. Ce sont les lignes de `--today` et de
    `--top-scorers`, la meme fenetre, le meme filtre par equipe - mais
    regardees en tas plutot qu'une par une, et un tas de buts a des formes
    qu'aucune liste ne montre. Sans fenetre c'est tout le journal, pour la
    meme raison qu'un classement de buteurs : une forme se voit sur la duree.

    Ce qui n'est pas ici manque parce que le journal ne le sait pas. Il n'ecrit
    que ce qui bouge : un 0-0 n'y laisse pas une ligne, et aucun compte de
    matchs sans but n'est donc possible. Le passeur, le pied, la distance : la
    source ne les publie pas. On mesure ce qui est ecrit, et on dit le reste.
    """
    try:
        window = window_of(args, whole_by_default=True)
    except ValueError as exc:
        print(tr("butbutbut : {}", exc), file=sys.stderr)
        return 2

    p = paths()
    entries = _window_goals(args, window)

    print(tr("butbutbut : ce que le journal raconte {}", window.describe()))
    if not entries:
        print(_empty_note(window, p["log"]))
        print(tr("\nJournal : {}", p["log"]))
        return 0

    found = journal.survey(entries)
    if not found.confirmed:
        # Tout ce qui suit compte des buts debout : sans un seul, chaque
        # tableau serait une colonne de zeros, et l'histogramme un cadre vide.
        print(tr("\n  (aucun but debout dans cette fenetre : {} signale(s), "
                 "{} repris par la VAR)", found.signalled, found.cancelled))
        print(tr("\nJournal : {}", p["log"]))
        return 0

    _print_minutes(found)
    _print_leagues(found)
    _print_evenings(found)
    _print_natures(found)
    _print_survey(found)
    print(tr("\nJournal : {}", p["log"]))
    return 0


def _print_minutes(found) -> None:
    """L'histogramme des minutes : la forme qu'on vient chercher en premier.

    Des tranches de dix minutes, parce que c'est la maille ou le football se
    raconte ("juste avant la mi-temps", "dans le dernier quart d'heure"), et
    parce qu'a la minute pres il faudrait quatre-vingt-dix lignes pour ne
    montrer que du bruit. Les buts du temps additionnel restent dans la tranche
    de leur minute : un but a 90+3' est un but de la 90e, et l'entasser
    ailleurs aplatirait justement la bosse qu'on cherche a voir.
    """
    print(tr("\nPar minute de match"))
    if not found.timed:
        print(tr("  (aucune minute de jeu lisible dans cette fenetre)"))
        return
    top = max(count for _low, _high, count in found.buckets)
    for low, high, count in found.buckets:
        print("  {:>3}-{:<3} {:<{}} {:>4} {:>4}".format(
            low, high, _bar(count, top), STATS_BAR, count,
            _share(count, found.timed)).rstrip())


def _print_leagues(found) -> None:
    """La repartition par competition, la plus fournie en tete."""
    print(tr("\nPar competition"))
    top = found.leagues[0][1]
    for name, count in found.leagues[:STATS_LEAGUES]:
        print("  {:<20.20} {:<{}} {:>4} {:>4}".format(
            name, _bar(count, top), STATS_BAR, count,
            _share(count, found.confirmed)).rstrip())
    hidden = len(found.leagues) - STATS_LEAGUES
    if hidden > 0:
        print(tr("  ... et {} autre(s) competition(s) plus bas.", hidden))


def _print_evenings(found) -> None:
    """Les soirees les plus prolifiques.

    Une soiree n'est pas un jour de calendrier : voir journal.evening_of(),
    qui rattache a la veille ce qui tombe apres minuit. A egalite on ne
    departage pas - annoncer une seule "meilleure soiree" quand trois se
    valent serait faux - on les annonce toutes, et le compte des ex aequo
    tient en une ligne quand ils sont trop nombreux pour la liste.
    """
    print(tr("\nLes soirees les plus prolifiques"))
    shown = found.evenings[:STATS_EVENINGS]
    for day, count in shown:
        print(tr("  {:<16} {:>4} but(s)", _stamp(day, "%d/%m/%Y"), count))
    tied = [row for row in found.evenings[len(shown):]
            if row[1] == shown[-1][1]]
    if tied:
        print(tr("  ... et {} autre(s) soiree(s) a {} but(s).",
                 len(tied), tied[0][1]))


def _print_natures(found) -> None:
    """La nature des buts : penaltys, csc, essais, ce que l'en-tete sait dire.

    C'est l'en-tete de la ligne qui porte la nature ("BUT SUR PENALTY"), et
    rien d'autre : quand la source publie l'action en retard, le but est ecrit
    "BUT" et compte comme tel. Cette part est donc un plancher, jamais un
    total exact, et le pied de sortie le rappelle.

    Une seule nature dans la fenetre ne merite pas un tableau : "36 buts sur
    36 sont des buts" n'apprend rien a personne.
    """
    if len(found.natures) < 2:
        return
    print(tr("\nNature des buts"))
    for key, count in found.natures:
        print("  {:<24.24} {:>4} {:>4}".format(
            journal.label_of(key), count,
            _share(count, found.confirmed)).rstrip())


def _print_survey(found) -> None:
    """Le pied de sortie : les totaux, et tout ce qu'ils ne disent pas."""
    print(tr("\n{} but(s) confirme(s) sur {} signale(s), dans "
             "{} competition(s).", found.confirmed, found.signalled,
             len(found.leagues)))
    print(tr("{} match(s) avec au moins un but signale, {:.1f} but(s) par "
             "match.", found.matches, found.per_match))
    print(tr("Un 0-0 ne laisse aucune trace dans le journal, ni dans cette "
             "moyenne."))
    if found.cancelled:
        print(tr("{} but(s) retire(s) par la VAR, deduit(s) de tout ce qui "
                 "precede.", found.cancelled))
    if found.orphans:
        print(tr("{} annulation(s) sans but a retirer dans cette fenetre "
                 "(le but est tombe avant).", found.orphans))
    if found.added:
        print(tr("{} but(s) dans le temps additionnel, comptes dans la "
                 "tranche de leur minute.", found.added))
    if found.untimed:
        print(tr("{} but(s) sans minute de jeu lisible, hors histogramme.",
                 found.untimed))


# ---------------------------------------------------------------- export -----

# Les champs de --export, dans l'ordre des colonnes du CSV et des cles du JSON.
#
# Ils sortent tous de ce que le journal porte VRAIMENT : rien ici ne se devine
# ni ne se complete aupres de la source. Les noms sont en anglais et ne passent
# PAS par le catalogue de traduction, contrairement a toute la prose du
# programme : un en-tete de colonne n'est pas une phrase, c'est un contrat. Un
# tableur ouvert sur une machine anglaise et un script lance sur une machine
# francaise doivent lire le meme fichier, et une colonne qui changerait de nom
# avec la langue casserait le second a chaque voyage.
EXPORT_FIELDS = (
    "timestamp",    # 2026-09-06T18:43:27, tel que le journal l'a ecrit
    "evening",      # la soiree du but, qui n'est pas toujours son jour
    "kind",         # goal | cancellation : la forme de la ligne du journal
    "nature",       # goal, own_goal, penalty, try, drop_goal, cancelled...
    "standing",     # le but tient-il encore, une fois la VAR passee ?
    "league",
    "home",
    "away",
    "home_score",
    "away_score",
    "team",         # l'equipe qui marque, ou celle dont le score est revenu
    "scorer",       # vide quand la source n'avait pas encore publie l'action
    "minute",       # la minute de jeu, en nombre ; nulle si illisible
    "stoppage",     # le temps additionnel, en nombre ; nul si illisible
    "clock",        # la minute telle qu'ecrite : "90+3'", ou l'horloge du hockey
    "detail",       # la phrase du journal : "But de M. Odegaard"
)

EXPORT_FORMATS = ("json", "csv")

# Le prefixe des cles de titre du catalogue. Retire, il laisse le mot qui
# nomme la nature d'un but ("title_own_goal" -> "own_goal") : stable d'une
# langue a l'autre, contrairement au libelle que journal.label_of() rend.
_TITLE_PREFIX = "title_"


def _mute_stdout() -> None:
    """Rebranche la sortie standard sur le trou noir, apres un tuyau referme.

    Sans quoi Python, en s'arretant, vide lui-meme sys.stdout - dans ce meme
    tuyau ferme - et imprime "Exception ignored while flushing sys.stdout"
    par-dessus le message qu'on venait d'ecrire proprement a cote. C'est la
    recette de la documentation Python pour un programme qui parle dans un
    tuyau : reouvrir le descripteur sur /dev/null (NUL sous Windows) avant de
    rendre la main.

    Tout echoue en silence ici, et c'est voulu : on est deja sur le chemin de
    sortie d'une erreur, et une sortie detournee en memoire - ce que fait
    n'importe quel test - n'a meme pas de descripteur a rebrancher.
    """
    try:
        target = sys.stdout.fileno()
    except Exception:
        return
    try:
        black_hole = os.open(os.devnull, os.O_WRONLY)
    except Exception:
        return
    try:
        os.dup2(black_hole, target)
    except Exception:
        pass
    finally:
        os.close(black_hole)


class _Utf8Writer:
    """Un objet-fichier texte qui pose ses octets en UTF-8 sur un flux binaire.

    Vingt lignes de moins auraient suffi avec io.TextIOWrapper, et c'est ce
    qu'on avait ecrit. Mais un TextIOWrapper ferme le flux qu'il habille en se
    detruisant : il faut donc le detacher, et son detach() commence par un
    flush. Sur un tuyau referme (`--export csv | head`) ce flush echoue, le
    detachement n'a jamais lieu, et le finaliseur vient fermer la sortie
    standard du programme en imprimant sa propre trace par-dessus le message
    qu'on venait d'ecrire proprement a cote.

    Un objet sans finaliseur et sans etat n'a pas ce probleme : le tuyau casse
    remonte de write(), la ou on l'attend et ou on sait quoi en dire.

    Le module csv et json.dump n'ont besoin que de write().
    """

    __slots__ = ("_raw",)

    def __init__(self, raw):
        self._raw = raw

    def write(self, text):
        return self._raw.write(text.encode("utf-8"))

    def flush(self):
        self._raw.flush()


@contextmanager
def _data_stream():
    """La sortie standard, garantie en UTF-8 et sans traduction de fin de ligne.

    Deux pieges, et ils ne se voient qu'a l'arrivee. Le premier est l'encodage :
    le journal est en UTF-8 et un nom d'equipe accentue s'y trouve, alors qu'une
    console Windows annonce volontiers du cp1252 - l'export mourrait sur
    "Bayer 04 Leverkusen" le jour ou il croise un accent. Le second est le
    retour a la ligne : en mode texte, Windows change chaque "\\n" en "\\r\\n",
    ce qui donnerait "\\r\\r\\n" aux lignes que le module csv termine deja
    lui-meme.

    On repasse donc par le flux d'octets quand il existe. Quand il n'existe pas
    - une sortie deja habillee en texte, ce que fait n'importe quelle
    redirection en memoire - on ecrit dedans tel quel : c'est l'appelant qui
    a choisi son encodage, ce n'est pas a nous de le defaire.
    """
    stream = sys.stdout
    raw = getattr(stream, "buffer", None)
    if raw is None:
        yield stream
        stream.flush()
        return
    yield _Utf8Writer(raw)
    raw.flush()


def _export_row(entry, standing: bool) -> dict:
    """Un but du journal, en donnees.

    La date et l'heure sortent en ISO 8601 parce que c'est la seule forme
    qu'une machine relit sans qu'on lui explique. Sans fuseau : le journal
    ecrit l'heure de la machine et ne dit pas laquelle, et coller un "Z" ou un
    decalage inventerait une precision que personne n'a.

    La minute de jeu sort en trois champs plutot qu'un, parce qu'elle repond a
    trois questions differentes : `minute` pour ranger un but dans un
    histogramme, `stoppage` pour savoir s'il est tombe dans le temps
    additionnel, et `clock` pour ne pas jeter ce que le journal a ecrit quand
    ce n'etait pas une minute de football - l'horloge d'un match de hockey n'est
    lisible ni comme un nombre ni comme rien.
    """
    clock = entry.clock
    key = entry.key
    return {
        "timestamp": "{}T{}".format(entry.day, entry.time),
        "evening": journal.evening_of(entry),
        "kind": "goal" if entry.goal else "cancellation",
        "nature": key[len(_TITLE_PREFIX):] if key.startswith(_TITLE_PREFIX)
                  else key,
        "standing": standing,
        "league": entry.league,
        "home": entry.home,
        "away": entry.away,
        "home_score": entry.home_score,
        "away_score": entry.away_score,
        "team": entry.team,
        "scorer": entry.scorer,
        # None et pas "" : le JSON a un `null` pour dire "on ne sait pas", et
        # une case de CSV vide dit la meme chose. Mettre un 0 la ferait entrer
        # tous les buts sans minute a la premiere minute de match.
        "minute": clock[0] if clock is not None else None,
        "stoppage": clock[1] if clock is not None else None,
        "clock": entry.minute,
        "detail": entry.detail,
    }


def _export_rows(entries) -> tuple:
    """([lignes], buts debout, annulations orphelines).

    Toutes les lignes de la fenetre sortent, buts ET annulations, et chacune
    porte en plus `standing`. C'est l'arbitrage central de l'export, et il se
    joue en deux temps parce que la question est double.

    Taire les annulations mentirait : la ligne "BUT ANNULE" a bien existe, elle
    a son horodatage, et c'est elle qui explique pourquoi un score recule. Un
    export qui l'efface rend un journal que personne n'a vecu.

    Les melanger aux buts mentirait tout autant : un but repris par la VAR
    n'est pas un but, et un tableur qui compterait ses lignes trouverait un
    total que ni `--stats` ni `--top-scorers` ne rendent. D'ou `standing`, pose
    sur chaque ligne : garder celles ou il est vrai donne exactement les buts
    que le reste du programme compte, en une ligne de filtre, sans avoir a
    rejouer le rattachement positionnel de son cote.

    Ce rattachement est justement celui de journal.settle(), repris tel quel :
    une annulation retire le dernier but encore debout de la meme equipe dans
    le meme match. Pas un second chemin a cote, sans quoi l'export finirait par
    ne plus dire la meme chose que le classement des buteurs.
    """
    kept, orphans = journal.settle(entries)
    # settle() rend les buts eux-memes et non leurs rangs : on repere donc les
    # objets. Chaque ligne relue donne une entree distincte, l'identite suffit.
    standing = {id(entry) for entry in kept}
    rows = [_export_row(entry, id(entry) in standing) for entry in entries]
    return rows, len(kept), orphans


def _write_json(handle, rows) -> None:
    """Un seul grand tableau, et non un objet par ligne.

    `--record` ecrit du JSON par lignes, et pour une bonne raison : c'est un
    flux sans fin, ecrit au fil de l'eau pendant qu'un match se joue, et une
    coupure au milieu doit laisser tout ce qui precede lisible. L'export est
    exactement l'inverse - une reponse finie a une question posee - et
    l'arbitrage se retourne avec lui :

      - une fenetre du journal tient en memoire sans y penser (des mois de buts
        font quelques milliers d'objets), donc `json.load(open(...))` en une
        ligne suffit, ce que le JSON par lignes interdit ;
      - un fichier coupe en route ne parse plus, et c'est ce qu'on veut : en
        JSON par lignes il parserait encore, en silence, avec les derniers buts
        en moins. Mieux vaut un export qui refuse de s'ouvrir qu'un export qui
        ment de trois lignes.

    `ensure_ascii=False` : le flux est en UTF-8 et l'annonce, un nom accentue
    n'a donc aucune raison de ressortir en `\\u00e9`. L'indentation, elle, est
    pour l'oeil : un export se regarde souvent une premiere fois a la main.
    """
    json.dump(rows, handle, ensure_ascii=False, indent=2)
    handle.write("\n")


def _csv_cell(value):
    """Une valeur, telle qu'une case de CSV peut la porter.

    Le CSV n'a qu'un type, le texte : `None` y devient une case vide et le
    booleen un mot. En minuscules, parce que c'est ce que lisent les
    bibliotheques de tableaux qui devinent les types - "True" de Python leur
    reste du texte.
    """
    if value is None:
        return ""
    if value is True:
        return "true"
    if value is False:
        return "false"
    return value


def _write_csv(handle, rows) -> None:
    """Un en-tete, puis une seule forme de ligne. Separateur : la virgule.

    La virgule plutot que le point-virgule, alors qu'un tableur francais
    attend le second : ce fichier est fait pour etre relu par un programme
    (`csv.reader`, un tableau de donnees, un tableur configure), et la virgule
    est ce que tous supposent par defaut. Le point-virgule ne plairait qu'a une
    locale, celle du lecteur, que le fichier ne peut pas connaitre au moment ou
    on l'ecrit. Un tableur qui n'en veut pas le demande a l'import ; un script
    a qui on donne du point-virgule, lui, ne demande rien et lit tout de
    travers.

    Une virgule, un guillemet ou un retour a la ligne dans un nom d'equipe ne
    sont pas un cas rare a plaindre : c'est le travail du module csv, qui
    protege la case comme il faut, et de csv.reader qui la rend intacte. Rien
    n'est echappe a la main ici, exactement pour cette raison.

    La fin de ligne est un simple "\\n" et non le "\\r\\n" que le module met par
    defaut : cette sortie part dans un tuyau aussi souvent que dans un fichier,
    et tout ce qui relit du CSV accepte les deux.
    """
    writer = csv.writer(handle, lineterminator="\n")
    writer.writerow(EXPORT_FIELDS)
    for row in rows:
        writer.writerow([_csv_cell(row[name]) for name in EXPORT_FIELDS])


def _export_note(shape, window, rows, confirmed, orphans, log_path) -> None:
    """Le compte rendu de l'export, sur la sortie d'erreur. Toujours.

    Rien de tout cela ne peut partir avec les donnees : une phrase au milieu
    d'un CSV le rend illisible, et un `> buts.json` doit rendre un fichier, pas
    un fichier plus un commentaire. Mais un export muet serait le seul chemin
    du journal qui ne dit rien - `--today`, `--stats` et le classement
    expliquent tous ce qu'ils viennent de compter. Ces lignes-la vont donc a
    cote, la ou elles restent visibles dans un terminal et invisibles dans un
    tuyau.
    """
    signalled = sum(1 for row in rows if row["kind"] == "goal")
    cancelled = len(rows) - signalled
    print(tr("butbutbut : export {} {}", shape, window.describe()),
          file=sys.stderr)
    if not rows:
        print(_empty_note(window, log_path).strip(), file=sys.stderr)
    else:
        print(tr("{} ligne(s) : {} but(s) signale(s) dont {} debout, "
                 "{} annulation(s).", len(rows), signalled, confirmed,
                 cancelled), file=sys.stderr)
        if signalled != confirmed:
            print(tr("Le champ 'standing' dit lesquels la VAR a repris."),
                  file=sys.stderr)
        if orphans:
            print(tr("{} annulation(s) sans but a retirer dans cette fenetre "
                     "(le but est tombe avant).", orphans), file=sys.stderr)
    print(tr("Journal : {}", log_path), file=sys.stderr)


def do_export(args) -> int:
    """Le journal en donnees, sur la sortie standard.

    `--on-goal` couvre l'amont : au moment du but, on peut declencher ce qu'on
    veut. Rien ne couvrait l'aval. Des mois de buts dorment dans le journal, et
    tout ce qui les en sortait jusqu'ici etait mis en page pour un oeil humain -
    colonnes alignees, barres de pourcentage, rangs partages. Un tableur, un
    carnet de notes, un graphe : tout cela demande des donnees.

    Meme fenetre et memes filtres que `--stats` et `--top-scorers`, et surtout
    la meme et unique lecture (journal.goals_between) : un deuxieme analyseur
    finirait par ne plus compter comme le premier, et un export qui contredit
    `--stats` sur le meme journal ne vaut rien.

    Les donnees vont sur la sortie standard et rien d'autre n'y va, pour que
    `butbutbut --export csv > buts.csv` rende un fichier valide meme le jour ou
    le journal est absent, ou la source injoignable, ou la fenetre vide. Un
    consommateur n'a pas a distinguer "rien" de "casse" : un tableau vide et un
    CSV reduit a son en-tete restent des reponses.
    """
    try:
        window = window_of(args, whole_by_default=True)
    except ValueError as exc:
        print(tr("butbutbut : {}", exc), file=sys.stderr)
        return 2

    p = paths()
    shape = (args.export or "").strip().lower()
    entries = _window_goals(args, window)
    rows, confirmed, orphans = _export_rows(entries)

    try:
        with _data_stream() as handle:
            if shape == "csv":
                _write_csv(handle, rows)
            else:
                _write_json(handle, rows)
    except Exception as exc:
        # Un tuyau referme en cours de route (`--export csv | head`), une
        # console qui refuse un octet : on le dit a cote et on s'en va. Une
        # trace d'erreur irait se coller a la fin des donnees deja ecrites.
        _mute_stdout()
        print(tr("butbutbut : export interrompu : {}", exc), file=sys.stderr)
        return 1

    _export_note(shape, window, rows, confirmed, orphans, p["log"])
    return 0


def do_status(args) -> int:
    p = paths()
    pid = running_pid()
    selection = leagues.resolve(args.leagues, args.exclude)

    print(tr("butbutbut {}", __version__))
    print(tr("  daemon      : {}",
             tr("actif (pid {})", pid) if pid else tr("arrete")))
    quiet_teams = spoiler_filter(args)
    _print_activity(pid, quiet_teams)
    chosen = team_filter(args)
    if chosen is not None:
        print(tr("  equipes     : {}", chosen.describe()))
    if args.pin:
        print(tr("  epinglee    : {}", pin_summary(args.pin)))
    if quiet_teams is not None:
        print(tr("  sans spoiler: {}  (journal seulement : ni carte, ni son)",
                 quiet_teams.describe()))
    # Haut de page, et toujours affichee, meme quand rien ne fait taire : un
    # silence sans explication est la premiere chose qu'on vient verifier en
    # croyant a une panne, et "aucun" repond aussi bien que "en veille".
    print(tr("  silence     : {}",
             silence.Silence(args.quiet_hours,
                             while_presenting=args.quiet_while_presenting
                             ).describe()))
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
    print(tr("  crochet     : {}",
             tr("{}  (essai : --test-hook)", args.on_goal) if args.on_goal
             else tr("aucun (voir --on-goal)")))
    # Toujours affichee, comme le silence : "qui parlerait ici" est la premiere
    # question de qui vient d'essayer --speak sans rien entendre.
    print(tr("  voix        : {}", speech.Voice(args.speak).describe()))

    sounds = sound.custom_sounds(p["sound"])
    if sounds:
        print(tr("  son         : {} fichier(s), le nom dit quand ils jouent",
                 len(sounds)))
        for name, label in _sound_arming(sounds, args, selection):
            print("                {:<22} {}".format(name, label))
    else:
        fallback = sound.pick_sound(p["wav"], p["sound"])
        origin = (tr("fourni") if fallback == sound.BUNDLED_SOUND
                  else tr("corne synthetisee"))
        print(tr("  son         : {} ({})", fallback.name, origin))
    print(tr("  sons perso  : {}  ({} fichier(s))", p["sound"], len(sounds)))

    named = sound_assignments(args)
    if named:
        print(tr("  son nomme   : {} paire(s), le plus precis l'emporte",
                 len(named)))
        for pair, label in _named_arming(named, args, selection):
            print("                {:<22} {}".format(pair, label))

    cached = crest_cache(args).cached()
    print(tr("  ecussons    : {}",
             tr("desactives (--no-logos)") if args.no_logos
             else tr("{}  ({} en cache)", p["logos"], len(cached))))

    found = screens.monitors()
    print(tr("  ecrans      : {} -> carte en {} sur {}",
             screens.describe(found), args.position,
             tr("l'ecran principal") if args.screen is None
             else tr("ecran {}", args.screen)))
    print(tr("  rattrapage  : {}",
             tr("actif (une carte de resume au reveil, sans son)")
             if args.catch_up
             else tr("inactif (le reveil reste silencieux, voir --catch-up)")))
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
                        metavar=tr("N"),
                        help=tr("affiche N cartes de demonstration puis quitte "
                             "(defaut 1 ; --test 3 montre l'empilement)"))
    parser.add_argument("--scores", action="store_true",
                        help=tr("affiche les matchs du jour dans le terminal puis quitte"))
    # nargs="?" avec un const vide : '--next' tout court doit se distinguer de
    # '--next' absent, sans quoi la commande ne serait jamais declenchee.
    parser.add_argument("--next", nargs="?", const="", default=None,
                        metavar=tr("EQUIPE|JOURS"),
                        help=tr("affiche les prochains matchs puis quitte. Sans "
                                "rien : les {} prochains jours des competitions "
                                "suivies. '--next om' cible une equipe, "
                                "'--next 14' allonge la fenetre ({} au plus)",
                                DEFAULT_NEXT_DAYS, MAX_NEXT_DAYS))
    # Meme const vide que --next, et pour la meme raison : '--table' tout court
    # doit se distinguer de '--table' absent.
    parser.add_argument("--table", nargs="?", const="", default=None,
                        metavar=tr("COMPETITION|EQUIPE"),
                        help=tr("affiche le classement puis quitte. Sans rien : "
                                "les competitions suivies. '--table l1' cible "
                                "une competition, '--table om' surligne une "
                                "equipe dans la sienne, et les deux se "
                                "combinent"))
    parser.add_argument("--status", action="store_true",
                        help=tr("affiche l'etat (daemon, dernier releve, matchs "
                             "en cours, son, ecrans, connexion)"))
    parser.add_argument("--today", action="store_true",
                        help=tr("recapitule les buts signales aujourd'hui"))
    parser.add_argument("--week", action="store_true",
                        help=tr("recapitule les buts des {} derniers jours "
                             "(aujourd'hui compris)", WEEK_DAYS))
    parser.add_argument("--month", action="store_true",
                        help=tr("recapitule les buts des {} derniers jours",
                                MONTH_DAYS))
    parser.add_argument("--since", default=None, metavar=tr("DATE"),
                        help=tr("recapitule les buts depuis ce jour, au format "
                             "AAAA-MM-JJ. Ex : --since 2026-09-01. "
                             "L'emporte sur --week et --month."))
    parser.add_argument("--top-scorers", action="store_true",
                        dest="top_scorers",
                        help=tr("classe les buteurs vus passer, buts annules "
                             "par la VAR deduits. Sur tout le journal, ou sur "
                             "la fenetre de --week, --month ou --since"))
    parser.add_argument("--stats", action="store_true",
                        help=tr("les formes cachees dans le journal : les buts "
                             "par minute de match (histogramme), par "
                             "competition, les soirees les plus prolifiques. "
                             "Meme fenetre et memes filtres que --top-scorers"))
    parser.add_argument("--export", default=None, choices=EXPORT_FORMATS,
                        metavar="json|csv",
                        help=tr("ecrit les buts du journal en donnees sur la "
                                "sortie standard, pour un tableur ou un "
                                "script. Memes fenetres et memes filtres que "
                                "--stats. Ex : butbutbut --export csv --month "
                                "> buts.csv"))
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
    parser.add_argument("--pin", default=None, metavar=tr("EQUIPE"),
                        help=tr("garde a l'ecran une carte qui suit les matchs "
                             "de cette equipe : elle apparait au coup d'envoi, "
                             "se met a jour a chaque releve et s'en va "
                             "quelques minutes apres la fin. Une seule equipe, "
                             "et jamais de son. Ex : --pin om"))
    parser.add_argument("--spoiler-free", default=None, metavar=tr("LISTE"),
                        dest="spoiler_free",
                        help=tr("matchs regardes en differe : aucune carte ni "
                             "aucun son pour ces equipes, quel que soit "
                             "l'evenement. Le journal, lui, garde tout "
                             "(butbutbut --today). Ex : --spoiler-free om"))
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
    parser.add_argument("--quiet-hours", default=None, dest="quiet_hours",
                        metavar=tr("PLAGE"),
                        help=tr("plage horaire ou rien ne s'affiche et rien ne "
                             "sonne, au format {} (ex : {}). Le but tombe quand "
                             "meme dans le journal, et --today le retrouve. "
                             "L'heure est celle de la machine, la plage peut "
                             "enjamber minuit.", silence.FORMAT, silence.EXAMPLE))
    parser.add_argument("--quiet-while-presenting", action="store_true",
                        dest="quiet_while_presenting",
                        help=tr("se taire aussi quand le systeme signale qu'on "
                             "presente : mode presentation, ecran duplique ou "
                             "'ne pas deranger'. Windows uniquement ; un "
                             "partage de fenetre Teams/Zoom n'est pas "
                             "detectable, voir README"))
    parser.add_argument("--red-cards", action="store_true", dest="red_cards",
                        help=tr("signale aussi les cartons rouges, par une carte "
                             "discrete et sans son"))
    parser.add_argument("--before-kickoff", type=int, default=0,
                        dest="before_kickoff", metavar=tr("MINUTES"),
                        help=tr("annonce le match ce nombre de minutes avant le "
                             "coup d'envoi, une seule fois et sans son "
                             "(0 = desactive, defaut)"))
    parser.add_argument("--catch-up", action="store_true", dest="catch_up",
                        help=tr("au reveil apres une veille, resume en une "
                             "carte muette les buts tombes pendant l'absence "
                             "(par defaut le reveil reste silencieux)"))
    parser.add_argument("--on-goal", default=None, dest="on_goal",
                        metavar=tr("COMMANDE"),
                        help=tr("commande a lancer a chaque but, avec le detail "
                             "du but dans des variables d'environnement BUT_* "
                             "(voir --test-hook et le README)"))
    parser.add_argument("--test-hook", action="store_true", dest="test_hook",
                        help=tr("essaie la commande de --on-goal sur un but "
                             "fabrique, et montre ce qu'elle rend"))
    parser.add_argument("--lang", default=None, metavar=tr("CODE"),
                        help=tr("langue des cartes : fr, en, es, it, de (defaut : "
                             "celle du systeme, francais a defaut). Le journal, "
                             "lui, reste toujours en francais."))
    parser.add_argument("--no-logos", action="store_true", dest="no_logos",
                        help=tr("pas d'ecusson sur les cartes, et rien de "
                             "telecharge (les couleurs des clubs restent)"))
    parser.add_argument("--no-sound", action="store_true", dest="no_sound",
                        help=tr("mode muet"))
    parser.add_argument("--speak", action="store_true", dest="speak",
                        help=tr("dit le but a voix haute, en plus du son (ou a "
                             "sa place avec --no-sound). La phrase est celle "
                             "des cartes, dans leur langue. 'butbutbut --test "
                             "--speak' l'essaie tout de suite."))
    parser.add_argument("--volume", type=float, default=DEFAULT_VOLUME,
                        help=tr("volume de la corne synthetisee, 0.0 a 1.0"))
    parser.add_argument("--sound-for", default=None, dest="sound_for",
                        metavar=tr("PAIRES"),
                        help=tr("un son a soi pour une equipe ou une "
                             "competition, sous forme de paires nom=chemin "
                             "separees par des virgules. Les noms sont ceux de "
                             "--teams et de --leagues, et l'equipe l'emporte "
                             "sur sa competition. Un chemin fautif est refuse "
                             "au demarrage. Ex : --sound-for om=~/sons/om.wav"))
    parser.add_argument("--regen-sound", action="store_true", dest="regen_sound",
                        help=tr("regenere la corne synthetisee"))
    parser.add_argument("--quiet", action="store_true", help=tr("n'ecrit que dans le journal"))
    return parser


def utf8_output() -> None:
    """Met la sortie standard en UTF-8, ou l'empeche au moins de casser.

    Sous Windows, une sortie redirigee - '> matchs.txt', un pipe, le journal
    d'un service - n'herite pas de l'UTF-8 de la console mais de la page de
    code ANSI, qui ne connait qu'un caractere sur mille. Un buteur nomme
    Zielinski, avec le vrai 'n' polonais, suffit alors a terminer la commande
    sur une UnicodeEncodeError au lieu du score. Tous les fichiers du projet
    sont deja ecrits en UTF-8 : la sortie fait desormais pareil.

    Une console reste sur sa page de code, elle : c'est elle qui saura ou non
    dessiner le caractere, et on ne gagne rien a lui envoyer autre chose. Elle
    herite seulement du remplacement, parce qu'un accent approximatif vaut
    mieux qu'une trace d'appels a la place des resultats.
    """
    for flux in (sys.stdout, sys.stderr):
        try:
            if flux.isatty():
                flux.reconfigure(errors="replace")
            else:
                flux.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            # Sortie capturee par un test, deja fermee, ou detournee vers autre
            # chose qu'un flux texte : il n'y a rien a reconfigurer, et rien de
            # grave non plus.
            pass


def main(argv=None) -> int:
    # Avant le moindre print : un message d'erreur aussi a le droit de
    # contenir le nom d'un club.
    utf8_output()

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
    # Une plage illisible est refusee ici, et nulle part ailleurs : le daemon
    # comme --status la relisent ensuite sans avoir a se demander si elle tient
    # debout. Le fichier de configuration, lui, l'ignore avec un avertissement
    # plutot que d'empecher un daemon lance au demarrage de la machine.
    try:
        args.quiet_hours = silence.normalize(args.quiet_hours)
    except silence.Invalid as exc:
        print(tr("butbutbut : {}", exc), file=sys.stderr)
        return 2
    if args.quiet_while_presenting and not presenting.supported():
        # Mieux vaut le dire que laisser croire a un filet de securite.
        print("butbutbut : --quiet-while-presenting ne sert que sous Windows, "
              "aucun autre systeme ne dit qu'une presentation est en cours.",
              file=sys.stderr)
        args.quiet_while_presenting = False
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

    # Une seule carte epinglee, donc un seul mot : une liste serait acceptee
    # par le filtre par equipe, et donnerait silencieusement une carte pour une
    # seule des equipes demandees. Mieux vaut le dire tout de suite. Un mot qui
    # attrape plusieurs clubs ('real'), lui, reste permis : voir pinned.py.
    args.pin = (args.pin or "").strip()
    if "," in args.pin or ";" in args.pin:
        print(tr("butbutbut : --pin ne prend qu'une equipe ({!r} en annonce "
                 "plusieurs) : il n'y a jamais qu'une carte epinglee.",
                 args.pin), file=sys.stderr)
        return 2

    if args.position.strip().lower() not in screens.CORNERS:
        print(tr("butbutbut : position inconnue : {} (voir --help)", args.position),
              file=sys.stderr)
        return 2

    # Un son nomme se verifie ici et maintenant, comme un nom d'equipe : un
    # chemin fautif qui ne se dirait qu'au premier but laisserait quelqu'un
    # attendre trois heures un cri qui ne viendra pas, et chercher du cote du
    # volume ou des haut-parleurs. Les paires sont lues au meme endroit, pour
    # que la ligne de commande et le fichier de configuration se trompent de la
    # meme facon et l'apprennent dans les memes termes.
    try:
        named = sound.parse_assignments(args.sound_for)
    except sound.Invalid as exc:
        print(tr("butbutbut : {}", exc), file=sys.stderr)
        return 2
    # --status echappe seul a ce refus : c'est la commande dont le travail est
    # justement de dire ce qui cloche. Refuser de la lancer reviendrait a nier
    # la reponse a la question qu'on vient de poser - et le chemin fautif est
    # de toute facon nomme, ligne par ligne, dans ce qu'elle affiche.
    problems = sound.check_assignments(named)
    if problems and not args.status:
        for message in problems:
            print(tr("butbutbut : {}", message), file=sys.stderr)
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
        # Meme regle que pour la confirmation des equipes plus bas : sous
        # --export, la sortie standard ne porte que des donnees. Cette ligne-la
        # n'y arriverait d'ailleurs meme pas dans l'ordre - l'export ecrit sous
        # la couche texte de sys.stdout, dont le tampon ne se vide qu'a la fin
        # du programme, donc elle se collerait DERRIERE les donnees.
        print(tr("butbutbut : corne regeneree -> {}", p["wav"]),
              file=sys.stderr if args.export else sys.stdout)

    if args.list_leagues:
        return do_list(args)
    if args.list_teams:
        return do_list_teams(args)
    if ((args.teams or args.exclude_teams or args.pin or args.spoiler_free
         or args.sound_for) and not args.replay):
        # --export n'ecrit que des donnees sur la sortie standard : la
        # confirmation des noms d'equipe est de la prose, elle part a cote
        # avec le reste, sans quoi le fichier produit commencerait par elle.
        failed = check_teams(args, leagues.resolve(args.leagues, args.exclude),
                             stream=sys.stderr if args.export else None)
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
    # Avant les recapitulatifs : --export dit COMMENT les buts sortent, les
    # fenetres ne disent que LESQUELS. `--export json --month` est un export,
    # pas un mois de listes.
    if args.export:
        return do_export(args)
    if args.top_scorers:
        return do_top_scorers(args)
    # Avant le recapitulatif : `--stats --week` demande les formes de la
    # semaine, pas la liste des buts de la semaine.
    if args.stats:
        return do_stats(args)
    if args.today or args.week or args.month or args.since is not None:
        return do_recap(args)
    if args.scores:
        return do_scores(args)
    if args.test_hook:
        return do_test_hook(args)
    if args.next is not None:
        return do_next(args)
    if args.table is not None:
        return do_table(args)
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
