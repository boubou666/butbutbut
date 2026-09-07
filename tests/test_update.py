"""Mise a jour d'une installation existante.

Rien ici ne touche au reseau ni ne lance d'installeur : ce qui est verifie,
c'est la fiche d'installation, le choix de la voie de mise a jour, les options
rejouees et les refus. Le telechargement reel est remplace la ou il apparait.
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from butbutbut import cli, update

# La racine du depot : tests/ en est le voisin direct.
RACINE = Path(__file__).resolve().parent.parent


class UpdateTestCase(unittest.TestCase):
    """Isole le dossier de donnees, donc la fiche."""

    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        root = Path(self._dir.name)
        self.paths = {
            "data": root,
            "sound": root / "sound",
            "wav": root / "but.wav",
            "log": root / "butbutbut.log",
            "pid": root / "butbutbut.pid",
            "config": root / "butbutbut.conf",
            "state": root / "butbutbut.json",
        }
        patch = mock.patch.object(cli, "paths", lambda: self.paths)
        patch.start()
        self.addCleanup(patch.stop)
        self.root = root

    def tearDown(self):
        self._dir.cleanup()


class Fiche(UpdateTestCase):
    """La fiche laissee par l'installeur."""

    def test_absente_rend_un_dictionnaire_vide(self):
        self.assertEqual(update.read_record(), {})

    def test_aller_retour(self):
        donnees = {"source": "/chemin", "commit": "abc123", "leagues": "l1,pl",
                   "position": "top-left", "interval": 30, "autostart": True}
        update.write_record(donnees)
        self.assertEqual(update.read_record(), donnees)

    def test_fiche_illisible_ne_plante_pas(self):
        update.record_path().write_text("{ pas du json", encoding="utf-8")
        self.assertEqual(update.read_record(), {})

    def test_fiche_avec_BOM(self):
        """install.ps1 passe par PowerShell 5.1, qui ecrit l'UTF-8 avec un BOM.

        json.loads refuse ce caractere invisible : lue en utf-8 strict, la
        fiche reviendrait vide et --check-update annoncerait un commit inconnu
        sur une installation pourtant parfaitement enregistree.
        """
        contenu = json.dumps({"commit": "f" * 40, "interval": 25})
        update.record_path().write_bytes(b"\xef\xbb\xbf" + contenu.encode("utf-8"))
        self.assertEqual(update.read_record().get("commit"), "f" * 40)
        self.assertEqual(update.local_sha(), "f" * 40)

    def test_commit_lu_dans_la_fiche(self):
        update.write_record({"commit": "0123456789abcdef"})
        self.assertEqual(update.local_sha(), "0123456789abcdef")

    def test_sans_commit_ni_source(self):
        update.write_record({"interval": 25})
        self.assertIsNone(update.local_sha())

    def test_ecrite_en_utf8_lisible(self):
        update.write_record({"source": "/home/utilisateur/depot"})
        contenu = json.loads(update.record_path().read_text(encoding="utf-8"))
        self.assertEqual(contenu["source"], "/home/utilisateur/depot")

    def test_ecrite_dans_le_dossier_de_donnees(self):
        self.assertEqual(update.record_path().parent, self.root)


class Comparaison(UpdateTestCase):
    """`--check-update`, sans reseau. Des versions par defaut, des commits en dev."""

    def test_a_jour(self):
        update.write_record({"version": "1.3.0"})
        with mock.patch.object(update, "latest_release", lambda: "1.3.0"):
            self.assertEqual(update.check(verbose=lambda *a: None), 0)

    def test_en_retard(self):
        update.write_record({"version": "1.3.0"})
        with mock.patch.object(update, "latest_release", lambda: "1.4.0"):
            self.assertEqual(update.check(verbose=lambda *a: None), 1)

    def test_reseau_injoignable(self):
        update.write_record({"version": "1.3.0"})
        with mock.patch.object(update, "latest_release", lambda: None):
            self.assertEqual(update.check(verbose=lambda *a: None), 2)

    def test_sans_fiche_on_compare_la_version_du_paquet(self):
        from butbutbut import __version__

        with mock.patch.object(update, "latest_release", lambda: __version__):
            self.assertEqual(update.check(verbose=lambda *a: None), 0)

    def test_le_commit_n_est_pas_consulte_par_defaut(self):
        """C'est une release qui sera installee : comparer un commit ferait
        annoncer une chose et en installer une autre."""
        update.write_record({"version": "1.3.0", "commit": "a" * 40})
        appels = []
        with mock.patch.object(update, "latest_release", lambda: "1.3.0"), \
             mock.patch.object(update, "remote_sha",
                               lambda: appels.append(1) or "b" * 40):
            self.assertEqual(update.check(verbose=lambda *a: None), 0)
        self.assertEqual(appels, [], "le commit ne devrait pas etre interroge")

    def test_dev_a_jour(self):
        update.write_record({"commit": "a" * 40})
        with mock.patch.object(update, "remote_sha", lambda: "a" * 40):
            self.assertEqual(update.check(verbose=lambda *a: None, dev=True), 0)

    def test_dev_en_retard(self):
        update.write_record({"commit": "a" * 40})
        with mock.patch.object(update, "remote_sha", lambda: "b" * 40):
            self.assertEqual(update.check(verbose=lambda *a: None, dev=True), 1)

    def test_dev_reseau_injoignable(self):
        update.write_record({"commit": "a" * 40})
        with mock.patch.object(update, "remote_sha", lambda: None):
            self.assertEqual(update.check(verbose=lambda *a: None, dev=True), 2)

    def test_dev_sans_commit_connu_ne_compare_rien(self):
        """Installe depuis une release, il n'y a pas de commit a comparer.
        On le dit, plutot que d'annoncer un retard invente."""
        update.write_record({"version": "1.3.0"})
        with mock.patch.object(update, "remote_sha", lambda: "b" * 40):
            self.assertEqual(update.check(verbose=lambda *a: None, dev=True), 2)

    def test_release_injoignable(self):
        with mock.patch.object(update, "_api", lambda url: None):
            self.assertIsNone(update.latest_release())
            self.assertIsNone(update.latest_tag())


class ChoixDeLaVoie(UpdateTestCase):
    """Par defaut la derniere release ; le depot clone n'est vu qu'en --dev."""

    def _telechargements(self):
        vus = []

        def faux(destination, url=update.ARCHIVE_MAIN):
            vus.append(url)
            return destination / "butbutbut-x"

        return vus, faux

    def test_par_defaut_on_prend_l_etiquette_de_la_derniere_release(self):
        vus, faux = self._telechargements()
        with mock.patch.object(update, "latest_tag", lambda: "v1.3.0"), \
             mock.patch.object(update, "download_source", faux):
            _source, voie = update.refresh_source({}, self.root,
                                                  verbose=lambda *a: None)
        self.assertEqual(vus, [update.ARCHIVE_TAG.format("v1.3.0")])
        self.assertIn("1.3.0", voie)

    def test_par_defaut_le_depot_clone_n_est_pas_touche(self):
        """Le point du mode par defaut : l'amener sur l'etiquette le laisserait
        en HEAD detachee, et il appartient a son proprietaire."""
        depot = self.root / "clone"
        (depot / ".git").mkdir(parents=True)
        vus, faux = self._telechargements()
        appels_git = []
        with mock.patch.object(update, "latest_tag", lambda: "v1.3.0"), \
             mock.patch.object(update, "download_source", faux), \
             mock.patch.object(update.shutil, "which", lambda n: "/usr/bin/git"), \
             mock.patch.object(update.subprocess, "run",
                               lambda *a, **k: appels_git.append(a)):
            source, voie = update.refresh_source({"source": str(depot)}, self.root,
                                                 verbose=lambda *a: None)
        self.assertEqual(appels_git, [], "git a ete appele en mode release")
        self.assertNotEqual(source, depot)
        self.assertEqual(len(vus), 1)

    def test_sans_release_publiee_on_refuse_plutot_que_de_prendre_main(self):
        with mock.patch.object(update, "latest_tag", lambda: None):
            with self.assertRaises(update.UpdateError) as leve:
                update.refresh_source({}, self.root, verbose=lambda *a: None)
        self.assertIn("--dev", str(leve.exception))

    def test_dev_sans_source_on_telecharge_main(self):
        vus, faux = self._telechargements()
        with mock.patch.object(update, "download_source", faux):
            _source, voie = update.refresh_source({}, self.root,
                                                  verbose=lambda *a: None, dev=True)
        self.assertEqual(vus, [update.ARCHIVE_MAIN])
        self.assertIn("main", voie)

    def test_dev_source_sans_git_on_telecharge(self):
        depot = self.root / "clone_sans_git"
        depot.mkdir()
        vus, faux = self._telechargements()
        with mock.patch.object(update, "download_source", faux):
            _source, voie = update.refresh_source({"source": str(depot)}, self.root,
                                                  verbose=lambda *a: None, dev=True)
        self.assertEqual(vus, [update.ARCHIVE_MAIN])

    def test_dev_source_git_on_tire(self):
        depot = self.root / "clone"
        (depot / ".git").mkdir(parents=True)
        faux = mock.Mock(returncode=0, stdout="", stderr="")
        with mock.patch.object(update.shutil, "which", lambda n: "/usr/bin/git"), \
             mock.patch.object(update.subprocess, "run", return_value=faux):
            source, voie = update.refresh_source({"source": str(depot)}, self.root,
                                                 verbose=lambda *a: None, dev=True)
        self.assertEqual(voie, "git pull")
        self.assertEqual(source, depot)

    def test_dev_git_en_echec_bascule_sur_l_archive(self):
        depot = self.root / "clone"
        (depot / ".git").mkdir(parents=True)
        faux = mock.Mock(returncode=1, stdout="", stderr="divergence")
        vus, telecharge = self._telechargements()
        with mock.patch.object(update.shutil, "which", lambda n: "/usr/bin/git"), \
             mock.patch.object(update.subprocess, "run", return_value=faux), \
             mock.patch.object(update, "download_source", telecharge):
            _source, voie = update.refresh_source({"source": str(depot)}, self.root,
                                                  verbose=lambda *a: None, dev=True)
        self.assertEqual(vus, [update.ARCHIVE_MAIN])


class Version(UpdateTestCase):
    """La version installee, et celle du code qu'on vient de recuperer."""

    def test_la_fiche_prime_sur_le_paquet(self):
        update.write_record({"version": "9.9.9"})
        self.assertEqual(update.local_version(), "9.9.9")

    def test_sans_fiche_on_prend_celle_du_paquet(self):
        from butbutbut import __version__

        self.assertEqual(update.local_version(), __version__)

    def test_lue_dans_le_code_recupere(self):
        source = self.root / "src"
        (source / "butbutbut").mkdir(parents=True)
        (source / "butbutbut" / "__init__.py").write_text(
            '"""doc."""\n\n__version__ = "4.5.6"\n__all__ = ["__version__"]\n',
            encoding="utf-8")
        self.assertEqual(update.source_version(source), "4.5.6")

    def test_source_sans_version_ne_plante_pas(self):
        source = self.root / "vide"
        source.mkdir()
        self.assertIsNone(update.source_version(source))

    def test_etiquette_et_version_viennent_de_la_meme_release(self):
        with mock.patch.object(update, "_api", lambda url: {"tag_name": "v1.2.3"}):
            self.assertEqual(update.latest_tag(), "v1.2.3")
            self.assertEqual(update.latest_release(), "1.2.3")


class Installeur(UpdateTestCase):
    """La commande construite pour rejouer l'installeur."""

    def commande_pour(self, fiche):
        source = self.root / "src"
        source.mkdir(exist_ok=True)
        script = "install.ps1" if sys.platform == "win32" else "install.sh"
        (source / script).write_text("#", encoding="utf-8")

        vues = []
        faux = mock.Mock(returncode=0, stdout="", stderr="")

        def espion(commande, **kwargs):
            vues.append(commande)
            return faux

        with mock.patch.object(update.subprocess, "run", espion):
            update.run_installer(source, fiche, verbose=lambda *a: None)
        return vues[0]

    def test_les_competitions_sont_reprises(self):
        """Le coeur de l'affaire : une mise a jour ne doit pas reinstaller les
        cinq grands championnats chez qui suivait `l1,pl,ucl`."""
        commande = self.commande_pour({"leagues": "l1,pl,ucl"})
        self.assertIn("l1,pl,ucl", commande)

    def test_les_reglages_d_affichage_sont_repris(self):
        commande = self.commande_pour({"position": "top-left", "interval": 40})
        self.assertIn("top-left", commande)
        self.assertIn("40", commande)

    def test_sans_competitions_pas_de_drapeau(self):
        """Fiche sans championnats : l'installeur garde son defaut."""
        commande = self.commande_pour({"leagues": ""})
        for interdit in ("--leagues", "-Leagues"):
            self.assertNotIn(interdit, commande)

    def test_fiche_vide_ne_pose_aucun_reglage(self):
        """Le coeur du correctif : un defaut materialise en argument ecraserait
        la meme cle du fichier de configuration."""
        commande = self.commande_pour({})
        for interdit in ("--position", "--interval", "--leagues",
                         "-Position", "-Interval", "-Leagues"):
            self.assertNotIn(interdit, commande)

    def test_un_interval_nul_compte_comme_absent(self):
        """install.ps1 note 0 quand -Interval n'a pas ete passe."""
        commande = self.commande_pour({"interval": 0})
        for interdit in ("--interval", "-Interval"):
            self.assertNotIn(interdit, commande)

    def test_sans_autostart(self):
        commande = self.commande_pour({"autostart": False})
        attendu = "-NoAutostart" if sys.platform == "win32" else "--no-autostart"
        self.assertIn(attendu, commande)

    def test_avec_autostart_pas_de_drapeau(self):
        commande = self.commande_pour({"autostart": True})
        for interdit in ("-NoAutostart", "--no-autostart"):
            self.assertNotIn(interdit, commande)

    def test_installeur_manquant(self):
        source = self.root / "vide"
        source.mkdir()
        with self.assertRaises(update.UpdateError):
            update.run_installer(source, {}, verbose=lambda *a: None)

    def test_echec_de_l_installeur_remonte(self):
        source = self.root / "src2"
        source.mkdir()
        script = "install.ps1" if sys.platform == "win32" else "install.sh"
        (source / script).write_text("#", encoding="utf-8")
        faux = mock.Mock(returncode=1, stdout="", stderr="ca a casse")
        with mock.patch.object(update.subprocess, "run", return_value=faux):
            with self.assertRaises(update.UpdateError):
                update.run_installer(source, {}, verbose=lambda *a: None)


class ArgumentsDuDaemon(UpdateTestCase):
    """Le daemon relance apres coup suit la meme selection qu'avant."""

    def test_les_competitions_survivent_a_la_relance(self):
        arguments = update.daemon_args({"leagues": "l1,pl,ucl", "position": "top-left",
                                        "interval": 40})
        self.assertEqual(arguments, ["--leagues", "l1,pl,ucl", "--position",
                                     "top-left", "--interval", "40", "--quiet"])

    def test_fiche_vide_ne_pose_que_quiet(self):
        """--quiet est la seule exception : un daemon de session ecrit sur une
        sortie qui n'existe pas."""
        self.assertEqual(update.daemon_args({}), ["--quiet"])

    def test_seuls_les_reglages_passes_sont_poses(self):
        self.assertEqual(update.daemon_args({"position": "top-left"}),
                         ["--position", "top-left", "--quiet"])


class FicheRectifiee(UpdateTestCase):
    """Ce que `update()` remet dans la fiche que l'installeur vient d'ecrire."""

    def _source(self, version="1.4.0"):
        source = self.root / "src"
        (source / "butbutbut").mkdir(parents=True, exist_ok=True)
        (source / "butbutbut" / "__init__.py").write_text(
            '__version__ = "{}"\n'.format(version), encoding="utf-8")
        return source

    def _mise_a_jour(self, fiche, durable, commit_distant="c" * 40, dev=False):
        update.write_record(fiche)
        source = self._source()
        with mock.patch.object(update, "managed_elsewhere", lambda: None), \
             mock.patch.object(update, "daemon_pid", lambda: None), \
             mock.patch.object(update, "refresh_source",
                               lambda f, t, verbose, d=False: (source, "la release v1.4.0")), \
             mock.patch.object(update, "run_installer", lambda *a, **k: None), \
             mock.patch.object(update, "git_sha",
                               lambda d: commit_distant if durable else None), \
             mock.patch.object(update, "remote_sha", lambda: commit_distant):
            self.assertEqual(update.update(verbose=lambda *a: None, dev=dev), 0)
        return update.read_record()

    def test_la_version_installee_est_notee(self):
        """C'est elle que --check-update comparera desormais."""
        fiche = self._mise_a_jour({"version": "1.3.0"}, durable=False)
        self.assertEqual(fiche["version"], "1.4.0")

    def test_le_chemin_temporaire_n_est_pas_conserve(self):
        """Sans depot durable, la source pointerait un dossier deja efface."""
        fiche = self._mise_a_jour({"source": "/tmp/parti"}, durable=False)
        self.assertEqual(fiche["source"], "")

    def test_l_archive_d_une_release_n_a_pas_de_commit(self):
        """Elle n'a pas de .git : garder l'ancien commit ferait mentir
        --check-update --dev sur ce qui est reellement en place."""
        fiche = self._mise_a_jour({"commit": "0" * 40}, durable=False,
                                  commit_distant=None)
        self.assertEqual(fiche["commit"], "")

    def test_le_depot_garde_ce_que_l_installeur_a_note(self):
        fiche = self._mise_a_jour({"commit": "d" * 40, "source": "/depot"},
                                  durable=True, dev=True)
        self.assertEqual(fiche["commit"], "d" * 40)
        self.assertEqual(fiche["source"], "/depot")


class DaemonRendu(UpdateTestCase):
    """Le daemon arrete pour la mise a jour doit repartir, meme en echec.

    Sans le `finally`, un installeur qui rendait un code non nul laissait la
    surveillance eteinte jusqu'a la session suivante - et c'est justement le
    moment ou personne ne regarde son terminal.
    """

    def _mise_a_jour(self, installeur):
        relances = []
        source = self.root / "src"
        source.mkdir(exist_ok=True)
        with mock.patch.object(update, "managed_elsewhere", lambda: None), \
             mock.patch.object(update, "daemon_pid", lambda: 4242), \
             mock.patch.object(update, "stop_daemon", lambda: True), \
             mock.patch.object(update, "start_daemon",
                               lambda f: relances.append(f) or True), \
             mock.patch.object(update, "refresh_source",
                               lambda f, t, verbose, d=False: (source, "l'archive de main")), \
             mock.patch.object(update, "run_installer", installeur), \
             mock.patch.object(update, "git_sha", lambda d: None), \
             mock.patch.object(update, "remote_sha", lambda: "c" * 40):
            return relances, update.update(verbose=lambda *a: None)

    def test_relance_apres_une_mise_a_jour_reussie(self):
        relances, code = self._mise_a_jour(lambda *a, **k: None)
        self.assertEqual(code, 0)
        self.assertEqual(len(relances), 1)

    def test_la_relance_a_lieu_avant_que_l_erreur_ne_remonte(self):
        relances = []
        source = self.root / "src"
        source.mkdir(exist_ok=True)

        def casse(*a, **k):
            raise update.UpdateError("telechargement impossible")

        with mock.patch.object(update, "managed_elsewhere", lambda: None), \
             mock.patch.object(update, "daemon_pid", lambda: 4242), \
             mock.patch.object(update, "stop_daemon", lambda: True), \
             mock.patch.object(update, "start_daemon",
                               lambda f: relances.append(f) or True), \
             mock.patch.object(update, "refresh_source",
                               lambda f, t, verbose, d=False: (source, "l'archive de main")), \
             mock.patch.object(update, "run_installer", casse):
            with self.assertRaises(update.UpdateError):
                update.update(verbose=lambda *a: None)
        self.assertEqual(len(relances), 1, "le daemon n'a pas ete rendu")

    def test_un_daemon_arrete_avant_ne_repart_pas_tout_seul(self):
        """On rend l'etat d'avant, on ne demarre pas ce qui ne tournait pas."""
        relances = []
        source = self.root / "src"
        source.mkdir(exist_ok=True)
        with mock.patch.object(update, "managed_elsewhere", lambda: None), \
             mock.patch.object(update, "daemon_pid", lambda: None), \
             mock.patch.object(update, "start_daemon",
                               lambda f: relances.append(f) or True), \
             mock.patch.object(update, "refresh_source",
                               lambda f, t, verbose, d=False: (source, "l'archive de main")), \
             mock.patch.object(update, "run_installer", lambda *a, **k: None), \
             mock.patch.object(update, "git_sha", lambda d: None), \
             mock.patch.object(update, "remote_sha", lambda: "c" * 40):
            update.update(verbose=lambda *a: None)
        self.assertEqual(relances, [])


class ArchiveSurveillee(UpdateTestCase):
    """Ce qu'on accepte de deplier."""

    def _zip(self, noms):
        import zipfile

        chemin = self.root / "archive.zip"
        with zipfile.ZipFile(chemin, "w") as zip_:
            for nom in noms:
                zip_.writestr(nom, "x")
        return zipfile.ZipFile(chemin)

    def test_une_archive_normale_passe(self):
        with self._zip(["butbutbut-main/README.md",
                        "butbutbut-main/butbutbut/cli.py"]) as zip_:
            update.check_members(zip_, self.root)      # ne leve pas

    def test_un_membre_qui_remonte_est_refuse(self):
        with self._zip(["butbutbut-main/ok.py", "../../.bashrc"]) as zip_:
            with self.assertRaises(update.UpdateError):
                update.check_members(zip_, self.root)

    def test_un_membre_absolu_est_refuse(self):
        with self._zip(["/etc/cron.d/piege"]) as zip_:
            with self.assertRaises(update.UpdateError):
                update.check_members(zip_, self.root)


class InstallationSysteme(UpdateTestCase):
    """Une installation qu'on ne gere pas ne doit pas etre ecrasee."""

    def test_refus_si_paquet_systeme(self):
        with mock.patch.object(update, "managed_elsewhere", lambda: "pacman"):
            self.assertEqual(update.update(verbose=lambda *a: None), 3)

    def test_pipx_est_reconnu(self):
        chemin = "/home/x/.local/share/pipx/venvs/butbutbut/lib/python3.12/" \
                 "site-packages/butbutbut/update.py"
        with mock.patch.object(update, "__file__", chemin):
            self.assertIn("pipx", update.managed_elsewhere() or "")

    def test_pip_est_reconnu(self):
        chemin = "/home/x/.local/lib/python3.12/site-packages/butbutbut/update.py"
        with mock.patch.object(update, "__file__", chemin):
            self.assertIn("pip", update.managed_elsewhere() or "")

    def test_le_depot_et_le_dossier_de_donnees_sont_acceptes(self):
        """Les deux installations que --update a le droit de rejouer."""
        for chemin in ("/home/x/repos/butbutbut/butbutbut/update.py",
                       "/home/x/.local/share/butbutbut/app/butbutbut/update.py"):
            with mock.patch.object(update, "__file__", chemin):
                self.assertIsNone(update.managed_elsewhere(), chemin)


class TestLesTroisNumerosSeSuivent(unittest.TestCase):
    """Le numero de version est ecrit a trois endroits : ils doivent s'accorder.

    Ecrit apres les avoir trouves separes - le programme annoncait 1.6.0, le
    paquet se serait construit en 1.5.0, et le PKGBUILD d'Arch aussi. Rien ne
    le signalait : chacun est juste tout seul, et faux avec les deux autres.
    `butbutbut/__init__.py` fait foi, c'est lui que le programme lit.
    """

    def numero(self, chemin, motif):
        texte = (RACINE / chemin).read_text(encoding="utf-8")
        trouve = re.search(motif, texte, re.M)
        self.assertIsNotNone(trouve, chemin)
        return trouve.group(1)

    def test_pyproject_suit_le_paquet(self):
        from butbutbut import __version__

        self.assertEqual(
            self.numero("pyproject.toml", r'^version = "([^"]+)"'),
            __version__)

    def test_le_pkgbuild_suit_le_paquet(self):
        from butbutbut import __version__

        self.assertEqual(self.numero("packaging/PKGBUILD", r"^pkgver=(.+)$"),
                         __version__)

    def test_le_changelog_ouvre_la_version_courante(self):
        """Une version publiee sans son entree de CHANGELOG n'existe pas."""
        from butbutbut import __version__

        texte = (RACINE / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("## [{}] - ".format(__version__), texte)


class TestLIntervalleDePythonEstLeMemePartout(unittest.TestCase):
    """L'intervalle de versions supportees est ecrit a neuf endroits.

    Le plancher est dit en toutes lettres : `requires-python`, le badge et les
    prerequis des deux README, et les deux installeurs qui refusent un
    interpreteur trop vieux. Le plafond, lui, n'est ecrit nulle part - il se
    deduit des classifiers et de la matrice de CI. Rien ne relie ces endroits,
    et c'est ainsi que la 3.14 a pu devenir la version de tous les jours sans
    jamais etre essayee : la matrice s'arretait a la 3.13, les classifiers
    aussi, et tout restait vert. Une matrice qui ne dit plus la verite est pire
    qu'une matrice absente, parce qu'elle rassure.
    """

    # Chaque motif rend le chiffre mineur du plancher. Deux par fichier la ou
    # le plancher y est ecrit deux fois : une prose qui vieillit a cote d'une
    # comparaison qui, elle, marche encore est le mensonge le plus courant.
    PLANCHERS = (
        ("pyproject.toml", r'^requires-python = ">=3\.(\d+)"'),
        ("README.md", r"badge/python-3\.(\d+)%2B"),
        ("README.md", r"\*\*Python 3\.(\d+)\+\*\*"),
        ("README.en.md", r"badge/python-3\.(\d+)%2B"),
        ("README.en.md", r"\*\*Python 3\.(\d+)\+\*\*"),
        ("install.sh", r"sys\.version_info >= \(3, (\d+)\)"),
        ("install.sh", r"Python 3\.(\d+)\+ est introuvable"),
        ("install.ps1", r"\[version\]'3\.(\d+)'"),
        ("install.ps1", r"Python 3\.(\d+)\+ est introuvable"),
    )

    def texte(self, chemin):
        return (RACINE / chemin).read_text(encoding="utf-8")

    def couple(self, version):
        """"3.14" -> (3, 14) : se compare comme un numero, pas comme un mot.

        En chaines, "3.14" passe avant "3.9" - de quoi croire que la matrice
        plafonne a la 3.9 juste au moment ou on lui demande son plus haut.
        """
        return tuple(int(morceau) for morceau in version.split("."))

    def matrice(self):
        """Les versions que la CI essaye, celle de l'`include` comprise.

        Seules les versions entre guillemets comptent : les commentaires du
        fichier en citent aussi, au fil de la phrase, et ce ne sont pas des
        cases de la matrice.
        """
        bloc = self.texte(".github/workflows/ci.yml")
        bloc = bloc.split("matrix:", 1)[1].split("steps:", 1)[0]
        return {self.couple(trouve)
                for trouve in re.findall(r'"(3\.\d+)"', bloc)}

    def classifiers(self):
        """Les versions que le paquet annonce a PyPI."""
        return {self.couple(trouve) for trouve in re.findall(
            r'"Programming Language :: Python :: (3\.\d+)"',
            self.texte("pyproject.toml"))}

    def test_le_plancher_est_le_meme_partout(self):
        trouves = {}
        for chemin, motif in self.PLANCHERS:
            marque = re.search(motif, self.texte(chemin), re.M)
            self.assertIsNotNone(marque, "{} : {}".format(chemin, motif))
            trouves["{} ({})".format(chemin, motif)] = (3, int(marque.group(1)))
        self.assertEqual(len(set(trouves.values())), 1, trouves)

    def test_la_ci_essaye_le_plancher_annonce(self):
        """Promettre un plancher sans jamais l'essayer, c'est le perdre."""
        plancher = re.search(r'^requires-python = ">=(3\.\d+)"',
                             self.texte("pyproject.toml"), re.M)
        self.assertIsNotNone(plancher)
        self.assertEqual(min(self.matrice()), self.couple(plancher.group(1)))

    def test_la_ci_essaye_la_derniere_version_annoncee(self):
        """Le classifier le plus haut est une promesse, pas un souhait.

        C'est ce test qui aurait parle plus tot : le depot s'ecrivait en 3.14
        et n'annoncait rien au-dela de la 3.13.
        """
        self.assertEqual(max(self.classifiers()), max(self.matrice()))

    def test_chaque_version_essayee_est_annoncee(self):
        """L'inverse n'est pas vrai : on annonce plus large qu'on n'essaye.

        Les versions du milieu (3.10, 3.11) sont tenues sans etre essayees -
        c'est un pari assume. Essayer une version sans l'annoncer, en revanche,
        ne serait qu'un oubli.
        """
        self.assertEqual(sorted(self.matrice() - self.classifiers()), [])


if __name__ == "__main__":
    unittest.main()
