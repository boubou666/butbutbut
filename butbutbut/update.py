"""Mise a jour d'une installation existante, sur les trois plateformes.

L'installeur laisse une fiche dans `<data_dir>/install.json` : d'ou le code
vient, quel commit, avec quelles options. `butbutbut --update` la relit pour
rafraichir la source puis rejouer l'installeur avec les memes reglages - les
memes competitions, le meme coin, la meme cadence.

Deux facons de rafraichir la source, dans cet ordre :

  1. si le depot clone est toujours la, `git pull --ff-only` ;
  2. sinon, l'archive de la branche principale est telechargee depuis GitHub
     et depliee dans un dossier temporaire.

La seconde voie ne demande ni git ni le clone d'origine : une installation
faite il y a six mois, dont le dossier a ete efface depuis, se met a jour
quand meme.

Une installation qui ne vient pas des scripts - paquet de la distribution,
pipx, pip - n'est pas ecrasee : `--update` renvoie vers l'outil qui la gere.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from . import cli

DEPOT = "boubou666/butbutbut"
BRANCHE = "main"
ARCHIVE = "https://codeload.github.com/{}/zip/refs/heads/{}".format(DEPOT, BRANCHE)
API_HEAD = "https://api.github.com/repos/{}/commits/{}".format(DEPOT, BRANCHE)
API_LATEST = "https://api.github.com/repos/{}/releases/latest".format(DEPOT)
DELAI = 30
AGENT = "butbutbut-update"


class UpdateError(RuntimeError):
    """Mise a jour impossible : le message explique quoi faire a la main."""


# ---------------------------------------------------------------- fiche ------

def record_path() -> Path:
    # cli.paths() est appele ici et pas importe une fois pour toutes : lie a
    # l'import, la fonction ne serait plus remplacable, et les tests ecriraient
    # dans le vrai dossier de donnees au lieu de leur bac a sable.
    return cli.paths()["data"] / "install.json"


def read_record() -> dict:
    # utf-8-sig et pas utf-8 : PowerShell 5.1 ecrit l'UTF-8 avec un BOM, et
    # json.loads refuse ce caractere invisible en tete de fichier. La fiche
    # deposee par install.ps1 serait illisible, sans le moindre message.
    try:
        return json.loads(record_path().read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def write_record(data: dict) -> Path:
    chemin = record_path()
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return chemin


def local_sha():
    """Commit installe, d'apres la fiche puis d'apres le depot source."""
    fiche = read_record()
    if fiche.get("commit"):
        return fiche["commit"]
    source = fiche.get("source")
    if source:
        return git_sha(Path(source))
    return None


def git_sha(depot: Path):
    if not (depot / ".git").exists():
        return None
    try:
        out = subprocess.run(
            ["git", "-C", str(depot), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=15,
        )
        return out.stdout.strip() or None if out.returncode == 0 else None
    except Exception:
        return None


# ------------------------------------------------------------ installation ---

def managed_elsewhere():
    """Signale une installation qui ne nous appartient pas.

    Un paquet de la distribution, un environnement pipx ou un `pip install`
    ont chacun leur commande de mise a jour. Les ecraser avec l'installeur
    poserait un second butbutbut a cote du premier, et c'est le PATH qui
    trancherait lequel repond - un beau piege a diagnostiquer.
    """
    ici = str(Path(__file__).resolve())
    morceaux = Path(ici).parts

    if "pipx" in morceaux:
        return "pipx (pipx upgrade butbutbut)"
    if "site-packages" in morceaux or "dist-packages" in morceaux:
        return "pip (pip install --upgrade butbutbut)"
    for prefixe, outil in (
        ("/usr/lib", "ton gestionnaire de paquets (pacman -Syu, apt upgrade...)"),
        ("/usr/local/lib", "ton gestionnaire de paquets"),
        ("/opt", "ton gestionnaire de paquets"),
    ):
        if ici.startswith(prefixe):
            return outil
    return None


def _api(url: str):
    requete = urllib.request.Request(
        url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": AGENT},
    )
    try:
        with urllib.request.urlopen(requete, timeout=DELAI) as reponse:
            return json.loads(reponse.read().decode("utf-8"))
    except Exception:
        return None


def remote_sha():
    """Dernier commit publie, ou None si le reseau ne repond pas."""
    donnees = _api(API_HEAD)
    return donnees.get("sha") if donnees else None


def latest_release():
    """Version de la derniere release, sans le v initial.

    Sert aux installations faites depuis une release : elles n'ont pas de
    depot git, donc pas de commit a comparer, mais elles ont un numero de
    version.
    """
    donnees = _api(API_LATEST)
    if not donnees:
        return None
    etiquette = donnees.get("tag_name") or ""
    return etiquette.lstrip("v") or None


def check_members(zip_, destination: Path) -> None:
    """Refuse une archive qui pretendrait ecrire hors du dossier cible.

    zipfile deplie deja sans sortir de la destination : il retire les `..` et
    la barre initiale de chaque nom. On ne s'appuie pas dessus pour autant -
    c'est un detail d'implementation de CPython, non promis par la
    documentation, et `--update` exige que l'archive ne touche rien d'autre.
    """
    racine = Path(destination).resolve()
    for membre in zip_.namelist():
        cible = (racine / membre).resolve()
        if cible != racine and racine not in cible.parents:
            raise UpdateError(
                "archive telechargee suspecte : {!r} sort du dossier".format(membre))


def download_source(destination: Path) -> Path:
    """Telecharge et deplie l'archive de la branche ; renvoie sa racine."""
    destination.mkdir(parents=True, exist_ok=True)
    archive = destination / "butbutbut.zip"
    requete = urllib.request.Request(ARCHIVE, headers={"User-Agent": AGENT})
    try:
        with urllib.request.urlopen(requete, timeout=DELAI) as reponse:
            archive.write_bytes(reponse.read())
    except urllib.error.URLError as erreur:
        raise UpdateError("telechargement impossible : {}".format(erreur)) from erreur

    try:
        with zipfile.ZipFile(archive) as zip_:
            check_members(zip_, destination)
            zip_.extractall(destination)
    except zipfile.BadZipFile as erreur:
        raise UpdateError("archive telechargee illisible") from erreur

    racines = [p for p in destination.iterdir() if p.is_dir()]
    if not racines:
        raise UpdateError("archive telechargee vide")
    return racines[0]


def refresh_source(fiche: dict, travail: Path, verbose=print):
    """Rend une source a jour, et dit d'ou elle vient."""
    source = fiche.get("source")
    if source:
        depot = Path(source)
        if (depot / ".git").exists() and shutil.which("git"):
            verbose("  source      : {} (depot git)".format(depot))
            out = subprocess.run(
                ["git", "-C", str(depot), "pull", "--ff-only"],
                capture_output=True, text=True, timeout=120,
            )
            if out.returncode == 0:
                return depot, "git pull"
            verbose("  git pull a echoue ({}), on passe par l'archive".format(
                (out.stderr or "").strip().splitlines()[-1:]))

    verbose("  source      : archive {} depuis GitHub".format(BRANCHE))
    return download_source(travail), "archive"


def installer_args(fiche: dict) -> list:
    """Les options d'origine, retraduites pour l'installeur de la plateforme."""
    position = str(fiche.get("position") or cli.DEFAULT_POSITION)
    interval = str(fiche.get("interval") or cli.DEFAULT_INTERVAL)
    leagues = str(fiche.get("leagues") or "")
    autostart = fiche.get("autostart", True)

    if sys.platform == "win32":
        arguments = ["-Position", position, "-Interval", interval]
        if leagues:
            arguments += ["-Leagues", leagues]
        if not autostart:
            arguments.append("-NoAutostart")
        return arguments

    arguments = ["--position", position, "--interval", interval]
    if leagues:
        arguments += ["--leagues", leagues]
    if not autostart:
        arguments.append("--no-autostart")
    return arguments


def run_installer(source: Path, fiche: dict, verbose=print) -> None:
    """Rejoue l'installeur de la plateforme avec les options d'origine."""
    if sys.platform == "win32":
        script = source / "install.ps1"
        commande = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-File", str(script)] + installer_args(fiche)
    else:
        script = source / "install.sh"
        commande = ["bash", str(script)] + installer_args(fiche)

    if not script.is_file():
        raise UpdateError("installeur introuvable dans la source : {}".format(script))

    verbose("  installeur  : {}".format(script.name))
    out = subprocess.run(commande, capture_output=True, text=True, timeout=600)
    if out.returncode != 0:
        detail = (out.stderr or out.stdout).strip().splitlines()[-5:]
        raise UpdateError("l'installeur a echoue :\n    " + "\n    ".join(detail))


# ------------------------------------------------------------- daemon --------

def daemon_pid():
    return cli.running_pid()


def stop_daemon() -> bool:
    pid = daemon_pid()
    if not pid:
        return False
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/PID", str(pid), "/F"],
                           capture_output=True, timeout=30)
        else:
            import signal

            os.kill(pid, signal.SIGTERM)
        cli.release_pid_file()
        return True
    except Exception:
        return False


def daemon_args(fiche: dict) -> list:
    """Les arguments du daemon, dans l'ordre ou l'installeur les pose."""
    arguments = []
    leagues = str(fiche.get("leagues") or "")
    if leagues:
        arguments += ["--leagues", leagues]
    arguments += ["--position", str(fiche.get("position") or cli.DEFAULT_POSITION)]
    arguments += ["--interval", str(fiche.get("interval") or cli.DEFAULT_INTERVAL)]
    arguments.append("--quiet")
    return arguments


def start_daemon(fiche: dict) -> bool:
    """Relance le daemon en tache de fond, par le chemin de la plateforme."""
    try:
        if sys.platform == "win32":
            pythonw = fiche.get("pythonw") or sys.executable
            app = fiche.get("app_dir", "")
            env = {**os.environ}
            if app:
                env["PYTHONPATH"] = app + os.pathsep + env.get("PYTHONPATH", "")
            DETACHED = 0x00000008 | 0x08000000  # DETACHED_PROCESS | CREATE_NO_WINDOW
            subprocess.Popen(
                [pythonw, "-m", "butbutbut"] + daemon_args(fiche),
                cwd=app or None, env=env, creationflags=DETACHED,
                close_fds=True,
            )
            return True

        if shutil.which("systemctl"):
            out = subprocess.run(["systemctl", "--user", "restart", "butbutbut.service"],
                                 capture_output=True, timeout=60)
            if out.returncode == 0:
                return True

        lanceur = Path(fiche.get("bin_dir") or (Path.home() / ".local" / "bin"))
        lanceur = lanceur / "butbutbut"
        if lanceur.is_file():
            subprocess.Popen(
                [str(lanceur)] + daemon_args(fiche),
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL, start_new_session=True,
            )
            return True
    except Exception:
        return False
    return False


# ----------------------------------------------------------------- API -------

def check(verbose=print) -> int:
    """Dit si une version plus recente existe.

    Deux facons de comparer, selon ce qu'on sait de l'installation. Avec un
    depot git derriere, on compare les commits, c'est le plus precis. Installe
    depuis une release il n'y a pas de commit, mais il y a un numero de
    version : on le compare alors a celui de la derniere release.
    """
    from . import __version__

    installe = local_sha()

    if installe:
        publie = remote_sha()
        verbose("  installe    : {} (commit)".format(installe[:8]))
        if publie is None:
            verbose("  publie      : injoignable (pas de reseau ?)")
            return 2
        verbose("  publie      : {}".format(publie[:8]))
        if installe == publie:
            verbose("\nbutbutbut est a jour.")
            return 0
        verbose("\nUne version plus recente existe : butbutbut --update")
        return 1

    publiee = latest_release()
    verbose("  installe    : {} (version, pas de depot git)".format(__version__))
    if publiee is None:
        verbose("  publie      : injoignable (pas de reseau, ou aucune release)")
        return 2
    verbose("  publie      : {}".format(publiee))

    if __version__ == publiee:
        verbose("\nbutbutbut est a jour.")
        verbose("(compare de version a version : `butbutbut --update` ira quand "
                "meme chercher les derniers changements de la branche principale.)")
        return 0
    verbose("\nUne version plus recente existe : butbutbut --update")
    return 1


def update(verbose=print) -> int:
    """Rafraichit la source, rejoue l'installeur, relance le daemon."""
    gestionnaire = managed_elsewhere()
    if gestionnaire:
        verbose("butbutbut est installe par {}.".format(gestionnaire))
        verbose("Mets-le a jour par ce biais, pas avec --update.")
        return 3

    fiche = read_record()
    if not fiche:
        verbose("Aucune fiche d'installation : butbutbut n'a pas ete installe par")
        verbose("install.sh ou install.ps1, ou elle a ete effacee.")
        verbose("On tente quand meme depuis GitHub.\n")

    avant = local_sha()
    tournait = daemon_pid() is not None
    if tournait:
        verbose("  daemon      : arret le temps de la mise a jour")
        stop_daemon()

    # Le redemarrage est dans un finally : un telechargement coupe ou un
    # installeur qui rend 2 laissait sinon le daemon eteint pour de bon, et
    # personne ne s'en apercevait avant la session suivante - c'est-a-dire
    # pendant tous les matchs de la soiree.
    try:
        with tempfile.TemporaryDirectory(prefix="butbutbut-update-") as travail:
            source, voie = refresh_source(fiche, Path(travail), verbose)
            run_installer(source, fiche, verbose)
            apres = git_sha(source) or remote_sha()
            source_durable = source if git_sha(source) else None

        # L'installeur vient de reecrire la fiche. Par une archive il n'a pas
        # de commit a y mettre, et il y laisse le dossier temporaire qu'on
        # efface a l'instant : on rectifie, sans quoi la fiche pointerait un
        # chemin mort et --check-update resterait muet jusqu'a la fin des
        # temps. Par l'archive on ecrase le commit meme s'il y en avait un :
        # celui qu'on vient de deplier est le seul qui decrive le code en place.
        fraiche = read_record()
        if fraiche:
            if apres and (not source_durable or not fraiche.get("commit")):
                fraiche["commit"] = apres
            if not source_durable:
                fraiche["source"] = ""
            write_record(fraiche)
    finally:
        if tournait:
            verbose("  daemon      : redemarrage")
            # read_record() plutot que la fiche de depart : l'installeur a pu
            # la reecrire. En echec elle n'a pas bouge, et le daemon repart
            # comme avant.
            if not start_daemon(read_record() or fiche):
                verbose("  (relance automatique impossible, lance `butbutbut` toi-meme)")

    verbose("")
    if avant and apres and avant == apres:
        verbose("Deja a jour ({}), reinstalle par acquit de conscience.".format(
            avant[:8]))
    elif apres:
        verbose("Mis a jour : {} -> {} (via {}).".format(
            avant[:8] if avant else "?", apres[:8], voie))
    else:
        verbose("Reinstalle depuis la source ({}).".format(voie))
    return 0
