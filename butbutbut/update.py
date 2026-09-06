"""Mise a jour d'une installation existante, sur les trois plateformes.

L'installeur laisse une fiche dans `<data_dir>/install.json` : d'ou le code
vient, quelle version, avec quelles options. `butbutbut --update` la relit pour
recuperer le code puis rejouer l'installeur avec les memes reglages.

Par defaut, c'est la **derniere release** qui est installee, et son archive est
depliee dans un dossier temporaire. Le depot clone, s'il en reste un, n'est pas
touche : l'amener sur l'etiquette demanderait de le laisser en HEAD detachee,
et il appartient a son proprietaire, pas a `--update`.

`--dev` vise la pointe de la branche principale. La, le depot clone sert quand
il est encore la (`git pull --ff-only`), et l'archive de `main` prend le relais
sinon - une installation dont le dossier a ete efface se met a jour quand meme.

`check()` et `update()` visent donc la meme chose dans chaque mode : des
versions par defaut, des commits avec `--dev`. Annoncer une release et en
installer une autre etait le defaut de la premiere mouture.

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
ARCHIVE_MAIN = "https://codeload.github.com/{}/zip/refs/heads/{}".format(DEPOT, BRANCHE)
ARCHIVE_TAG = "https://codeload.github.com/{}/zip/refs/tags/{{}}".format(DEPOT)
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


def local_version():
    """Version installee : celle notee par l'installeur, sinon celle du paquet."""
    from . import __version__

    return read_record().get("version") or __version__


def source_version(source: Path):
    """Version annoncee par le code qu'on vient de recuperer.

    Lue dans le fichier plutot que deduite de l'etiquette : c'est le code en
    place qui fait foi, pas le nom sous lequel on l'a telecharge.
    """
    fichier = Path(source) / "butbutbut" / "__init__.py"
    try:
        for ligne in fichier.read_text(encoding="utf-8").splitlines():
            if ligne.startswith("__version__"):
                return ligne.split("=", 1)[1].strip().strip("\"'") or None
    except Exception:
        return None
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


def latest_tag():
    """Etiquette de la derniere release, telle qu'elle est publiee (vX.Y.Z)."""
    donnees = _api(API_LATEST)
    if not donnees:
        return None
    return donnees.get("tag_name") or None


def latest_release():
    """Version de la derniere release, sans le v initial."""
    etiquette = latest_tag()
    return etiquette.lstrip("v") if etiquette else None


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


def download_source(destination: Path, url: str = ARCHIVE_MAIN) -> Path:
    """Telecharge et deplie une archive GitHub ; renvoie sa racine."""
    destination.mkdir(parents=True, exist_ok=True)
    archive = destination / "butbutbut.zip"
    requete = urllib.request.Request(url, headers={"User-Agent": AGENT})
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


def refresh_source(fiche: dict, travail: Path, verbose=print, dev: bool = False):
    """Rend une source a jour, et dit d'ou elle vient."""
    if not dev:
        etiquette = latest_tag()
        if not etiquette:
            raise UpdateError(
                "aucune release publiee, ou GitHub injoignable. "
                "`butbutbut --update --dev` prend la pointe de la branche "
                "principale.")
        verbose("  source      : release {} depuis GitHub".format(etiquette))
        # Le depot clone est volontairement ignore ici. L'amener sur
        # l'etiquette le laisserait en HEAD detachee, et c'est le dossier de
        # quelqu'un qui travaille peut-etre dedans.
        return (download_source(travail, ARCHIVE_TAG.format(etiquette)),
                "la release {}".format(etiquette))

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
    return download_source(travail, ARCHIVE_MAIN), "l'archive de {}".format(BRANCHE)


def _reglages(fiche: dict):
    """Les trois reglages de la fiche, vides quand ils n'ont pas ete passes."""
    interval = fiche.get("interval")
    return (
        str(fiche.get("leagues") or ""),
        str(fiche.get("position") or ""),
        "" if interval in (None, "", 0) else str(interval),
    )


def installer_args(fiche: dict) -> list:
    """Les options d'origine, retraduites pour l'installeur de la plateforme.

    Seules celles que l'installeur avait recues sont rejouees. Materialiser un
    defaut ici le reposerait dans le service de demarrage, ou il ecraserait la
    meme cle du fichier de configuration.
    """
    leagues, position, interval = _reglages(fiche)
    windows = sys.platform == "win32"

    arguments = []
    if leagues:
        arguments += ["-Leagues" if windows else "--leagues", leagues]
    if position:
        arguments += ["-Position" if windows else "--position", position]
    if interval:
        arguments += ["-Interval" if windows else "--interval", interval]
    if not fiche.get("autostart", True):
        arguments.append("-NoAutostart" if windows else "--no-autostart")
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
    """Les arguments du daemon, dans l'ordre ou l'installeur les pose.

    Meme regle que pour l'installeur, a une exception : --quiet est toujours
    pose. Un daemon de session ecrit sur une sortie qui n'existe pas, et le
    journal reste alimente de toute facon.
    """
    leagues, position, interval = _reglages(fiche)

    arguments = []
    if leagues:
        arguments += ["--leagues", leagues]
    if position:
        arguments += ["--position", position]
    if interval:
        arguments += ["--interval", interval]
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

def check(verbose=print, dev: bool = False) -> int:
    """Dit si une version plus recente existe.

    Par defaut on compare des versions, puisque c'est une release que
    `--update` installera. Avec `--dev` on compare des commits, puisque c'est
    la pointe de la branche qu'il ira chercher. Les deux commandes visent la
    meme chose dans chaque mode : annoncer une release et en installer une
    autre etait le defaut de la premiere mouture.
    """
    if dev:
        installe = local_sha()
        publie = remote_sha()
        if not installe:
            verbose("  installe    : commit inconnu (installation sans depot git)")
            verbose("  publie      : {}".format(publie[:8] if publie else "injoignable"))
            verbose("\nRien a comparer en mode dev. `butbutbut --check-update` "
                    "compare les versions publiees.")
            return 2
        verbose("  installe    : {} (commit)".format(installe[:8]))
        if publie is None:
            verbose("  publie      : injoignable (pas de reseau ?)")
            return 2
        verbose("  publie      : {}".format(publie[:8]))
        if installe == publie:
            verbose("\nbutbutbut est a jour sur la pointe de {}.".format(BRANCHE))
            return 0
        verbose("\nUne version plus recente existe : butbutbut --update --dev")
        return 1

    installee = local_version()
    publiee = latest_release()
    verbose("  installe    : {}".format(installee))
    if publiee is None:
        verbose("  publie      : injoignable (pas de reseau, ou aucune release)")
        return 2
    verbose("  publie      : {}".format(publiee))
    if installee == publiee:
        verbose("\nbutbutbut est a jour.")
        return 0
    verbose("\nUne version plus recente existe : butbutbut --update")
    return 1


def update(verbose=print, dev: bool = False) -> int:
    """Recupere le code, rejoue l'installeur, relance le daemon."""
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

    avant = local_sha() if dev else local_version()
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
            source, voie = refresh_source(fiche, Path(travail), verbose, dev)
            run_installer(source, fiche, verbose)
            durable = git_sha(source)
            apres_commit = durable or (remote_sha() if dev else None)
            apres_version = source_version(source)

        # L'installeur vient de reecrire la fiche, mais il ne sait pas tout.
        # Depliee d'une archive, la source n'a pas de .git : il y laisse un
        # commit vide et le chemin du dossier temporaire qu'on efface a
        # l'instant. On rectifie, sans quoi la fiche pointerait un chemin mort
        # et --check-update resterait muet jusqu'a la fin des temps.
        fraiche = read_record()
        if fraiche:
            if apres_version:
                fraiche["version"] = apres_version
            if durable:
                if apres_commit and not fraiche.get("commit"):
                    fraiche["commit"] = apres_commit
            else:
                fraiche["source"] = ""
                fraiche["commit"] = apres_commit or ""
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
    apres = apres_commit if dev else apres_version
    court = (lambda v: v[:8]) if dev else (lambda v: v)
    if avant and apres and avant == apres:
        verbose("Deja a jour ({}), reinstalle par acquit de conscience.".format(
            court(avant)))
    elif apres:
        verbose("Mis a jour : {} -> {} (via {}).".format(
            court(avant) if avant else "?", court(apres), voie))
    else:
        verbose("Reinstalle depuis {}.".format(voie))
    return 0
