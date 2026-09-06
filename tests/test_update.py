"""Mise a jour d'une installation existante.

Rien ici ne touche au reseau ni ne lance d'installeur : ce qui est verifie,
c'est la fiche d'installation, le choix de la voie de mise a jour, les options
rejouees et les refus. Le telechargement reel est remplace la ou il apparait.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from butbutbut import cli, update


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
    """`--check-update`, sans reseau."""

    def test_a_jour(self):
        update.write_record({"commit": "a" * 40})
        with mock.patch.object(update, "remote_sha", lambda: "a" * 40):
            self.assertEqual(update.check(verbose=lambda *a: None), 0)

    def test_en_retard(self):
        update.write_record({"commit": "a" * 40})
        with mock.patch.object(update, "remote_sha", lambda: "b" * 40):
            self.assertEqual(update.check(verbose=lambda *a: None), 1)

    def test_reseau_injoignable(self):
        update.write_record({"commit": "a" * 40})
        with mock.patch.object(update, "remote_sha", lambda: None):
            self.assertEqual(update.check(verbose=lambda *a: None), 2)

    def test_commit_inconnu_compare_les_versions(self):
        """Installe depuis une release : pas de commit, mais un numero.

        Sans ce recours, --check-update ne repondrait rien d'utile a qui a
        installe depuis une release ou depuis PyPI, faute de depot git.
        """
        from butbutbut import __version__

        with mock.patch.object(update, "latest_release", lambda: __version__):
            self.assertEqual(update.check(verbose=lambda *a: None), 0)

    def test_version_en_retard(self):
        with mock.patch.object(update, "latest_release", lambda: "99.0.0"):
            self.assertEqual(update.check(verbose=lambda *a: None), 1)

    def test_aucune_release_publiee(self):
        with mock.patch.object(update, "latest_release", lambda: None):
            self.assertEqual(update.check(verbose=lambda *a: None), 2)

    def test_le_commit_prime_sur_la_version(self):
        """Avec un commit connu, on compare les commits, c'est plus precis."""
        update.write_record({"commit": "a" * 40})
        appels = []
        with mock.patch.object(update, "remote_sha", lambda: "a" * 40), \
             mock.patch.object(update, "latest_release",
                               lambda: appels.append(1) or "0.0.1"):
            self.assertEqual(update.check(verbose=lambda *a: None), 0)
        self.assertEqual(appels, [], "la version ne devrait pas etre interrogee")

    def test_etiquette_sans_v(self):
        """tag_name vaut vX.Y.Z, la comparaison porte sur X.Y.Z."""
        with mock.patch.object(update, "_api", lambda url: {"tag_name": "v1.2.3"}):
            self.assertEqual(update.latest_release(), "1.2.3")

    def test_release_injoignable(self):
        with mock.patch.object(update, "_api", lambda url: None):
            self.assertIsNone(update.latest_release())


class ChoixDeLaVoie(UpdateTestCase):
    """Depot git s'il est la, archive sinon."""

    def test_sans_source_on_telecharge(self):
        appels = []

        def faux_telechargement(destination):
            appels.append(destination)
            return destination / "butbutbut-main"

        with mock.patch.object(update, "download_source", faux_telechargement):
            _source, voie = update.refresh_source({}, self.root, verbose=lambda *a: None)
        self.assertEqual(voie, "archive")
        self.assertEqual(len(appels), 1)

    def test_source_sans_git_on_telecharge(self):
        depot = self.root / "clone_sans_git"
        depot.mkdir()
        with mock.patch.object(update, "download_source",
                               lambda d: d / "butbutbut-main"):
            _source, voie = update.refresh_source({"source": str(depot)}, self.root,
                                                  verbose=lambda *a: None)
        self.assertEqual(voie, "archive")

    def test_source_git_on_tire(self):
        depot = self.root / "clone"
        (depot / ".git").mkdir(parents=True)
        faux = mock.Mock(returncode=0, stdout="", stderr="")
        with mock.patch.object(update.shutil, "which", lambda n: "/usr/bin/git"), \
             mock.patch.object(update.subprocess, "run", return_value=faux):
            source, voie = update.refresh_source({"source": str(depot)}, self.root,
                                                 verbose=lambda *a: None)
        self.assertEqual(voie, "git pull")
        self.assertEqual(source, depot)

    def test_git_en_echec_bascule_sur_l_archive(self):
        depot = self.root / "clone"
        (depot / ".git").mkdir(parents=True)
        faux = mock.Mock(returncode=1, stdout="", stderr="divergence")
        with mock.patch.object(update.shutil, "which", lambda n: "/usr/bin/git"), \
             mock.patch.object(update.subprocess, "run", return_value=faux), \
             mock.patch.object(update, "download_source",
                               lambda d: d / "butbutbut-main"):
            _source, voie = update.refresh_source({"source": str(depot)}, self.root,
                                                  verbose=lambda *a: None)
        self.assertEqual(voie, "archive")


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

    def test_fiche_vide_reprend_les_defauts(self):
        commande = self.commande_pour({})
        self.assertIn(cli.DEFAULT_POSITION, commande)
        self.assertIn(str(cli.DEFAULT_INTERVAL), commande)

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

    def test_fiche_vide_reprend_les_defauts(self):
        arguments = update.daemon_args({})
        self.assertNotIn("--leagues", arguments)
        self.assertIn(cli.DEFAULT_POSITION, arguments)
        self.assertIn("--quiet", arguments)


class FicheRectifiee(UpdateTestCase):
    """Ce que `update()` remet dans la fiche que l'installeur vient d'ecrire."""

    def _mise_a_jour(self, fiche, source_durable, apres):
        update.write_record(fiche)
        source = self.root / "src"
        source.mkdir(exist_ok=True)
        with mock.patch.object(update, "managed_elsewhere", lambda: None), \
             mock.patch.object(update, "daemon_pid", lambda: None), \
             mock.patch.object(update, "refresh_source",
                               lambda f, t, verbose: (source, "archive")), \
             mock.patch.object(update, "run_installer", lambda *a, **k: None), \
             mock.patch.object(update, "git_sha",
                               lambda d: apres if source_durable else None), \
             mock.patch.object(update, "remote_sha", lambda: apres):
            self.assertEqual(update.update(verbose=lambda *a: None), 0)
        return update.read_record()

    def test_le_chemin_temporaire_n_est_pas_conserve(self):
        """Sans depot durable, la source pointerait un dossier deja efface."""
        fiche = self._mise_a_jour({"source": "/tmp/parti"}, False, "c" * 40)
        self.assertEqual(fiche["source"], "")

    def test_l_archive_impose_son_commit(self):
        """Par l'archive, l'installeur n'a aucun commit a noter : c'est celui
        qu'on vient de deplier qui decrit le code en place, meme si la fiche en
        portait deja un autre - sinon --check-update reste bloque dessus."""
        fiche = self._mise_a_jour({"commit": "0" * 40}, False, "c" * 40)
        self.assertEqual(fiche["commit"], "c" * 40)

    def test_le_depot_garde_ce_que_l_installeur_a_note(self):
        fiche = self._mise_a_jour({"commit": "d" * 40, "source": "/depot"},
                                  True, "c" * 40)
        self.assertEqual(fiche["commit"], "d" * 40)
        self.assertEqual(fiche["source"], "/depot")


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


if __name__ == "__main__":
    unittest.main()
