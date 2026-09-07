import os
import unittest
from unittest import mock

import pathlib

from butbutbut import (cli, espn, i18n, journal, lang, leagues, overlay,
                       watcher)

from helpers import bump, event, goal_detail, opener_for, payload

LIGUE1 = leagues.BY_SLUG["fra.1"]


class TestCatalogues(unittest.TestCase):
    """Le test qui compte : aucune langue ne doit avoir de trou."""

    def test_les_cinq_langues_sont_la(self):
        self.assertEqual(i18n.LANGUAGES, ("fr", "en", "es", "it", "de"))
        self.assertEqual(i18n.FALLBACK, "fr")
        self.assertEqual(sorted(i18n.MESSAGES), sorted(i18n.LANGUAGES))

    def test_aucune_cle_ne_manque_nulle_part(self):
        reference = set(i18n.MESSAGES[i18n.FALLBACK])
        for lang in i18n.LANGUAGES:
            manquantes = reference - set(i18n.MESSAGES[lang])
            self.assertEqual(sorted(manquantes), [],
                             "cles absentes du catalogue {}".format(lang))
            en_trop = set(i18n.MESSAGES[lang]) - reference
            self.assertEqual(sorted(en_trop), [],
                             "cles en trop dans le catalogue {}".format(lang))

    def test_aucun_libelle_vide(self):
        for lang in i18n.LANGUAGES:
            for cle, valeur in i18n.MESSAGES[lang].items():
                self.assertTrue(valeur.strip(), "{}/{}".format(lang, cle))

    def test_les_libelles_a_trous_gardent_leur_trou(self):
        # "minute" et "kickoff_in" prennent une valeur : la perdre dans une
        # traduction donnerait un texte fige, sans le chiffre.
        for lang in i18n.LANGUAGES:
            self.assertIn("{minute}", i18n.MESSAGES[lang]["minute"])
            self.assertIn("{minutes}", i18n.MESSAGES[lang]["kickoff_in"])

    def test_les_catalogues_restent_en_ascii(self):
        # Comme le reste du projet : les formulations sont choisies pour ne pas
        # avoir besoin de diacritiques, plutot que d'en afficher a moitie.
        for lang in i18n.LANGUAGES:
            for cle, valeur in i18n.MESSAGES[lang].items():
                self.assertEqual(valeur, valeur.encode("ascii", "replace").decode(),
                                 "{}/{} n'est pas en ascii".format(lang, cle))

    def test_chaque_langue_dit_le_but_a_sa_facon(self):
        titres = {lang: i18n.MESSAGES[lang]["title_goal"] for lang in i18n.LANGUAGES}
        self.assertEqual(titres["fr"], "BUT !")
        self.assertEqual(titres["de"], "TOR!")
        # Deux langues peuvent coincider (GOL! en espagnol et en italien), mais
        # pas les cinq : ce serait le signe d'un catalogue copie sans traduire.
        self.assertGreater(len(set(titres.values())), 3)


class TestNormalisation(unittest.TestCase):
    def test_les_formes_habituelles(self):
        for valeur, attendu in (("fr", "fr"), ("FR", "fr"), ("fr_FR", "fr"),
                                ("fr-FR", "fr"), ("fr_FR.UTF-8", "fr"),
                                ("de_DE.utf8", "de"), ("  es  ", "es"),
                                ("it_IT", "it"), ("en_GB", "en")):
            self.assertEqual(i18n.normalize(valeur), attendu, valeur)

    def test_les_noms_que_windows_rend_parfois(self):
        for valeur, attendu in (("French_France", "fr"), ("German_Germany", "de"),
                                ("Spanish_Spain", "es"), ("Italian_Italy", "it"),
                                ("English_United States", "en")):
            self.assertEqual(i18n.normalize(valeur), attendu, valeur)

    def test_ce_qui_ne_veut_rien_dire_rend_vide(self):
        for valeur in ("", None, "C", "POSIX", "klingon", "zz", "42"):
            self.assertEqual(i18n.normalize(valeur), "", repr(valeur))

    def test_une_langue_hors_des_cinq_rend_vide(self):
        # Le neerlandais n'est pas traduit : a l'appelant de decider du repli,
        # pas a normalize de faire semblant.
        self.assertEqual(i18n.normalize("nl_NL"), "")


class TestChoix(unittest.TestCase):
    def setUp(self):
        self.avant = i18n.language()

    def tearDown(self):
        i18n.use(self.avant)

    def test_use_fixe_la_langue(self):
        self.assertEqual(i18n.use("de"), "de")
        self.assertEqual(i18n.language(), "de")

    def test_use_accepte_les_formes_longues(self):
        self.assertEqual(i18n.use("es_ES.UTF-8"), "es")

    def test_use_refuse_une_langue_inconnue(self):
        with self.assertRaises(i18n.UnknownLanguage) as capte:
            i18n.use("klingon")
        # Le message doit lister ce qu'on parle, sinon il ne sert a rien.
        for lang in i18n.LANGUAGES:
            self.assertIn(lang, str(capte.exception))

    def test_use_sans_argument_reprend_le_systeme(self):
        with mock.patch.object(i18n, "detect", return_value="it"):
            self.assertEqual(i18n.use(None), "it")

    def test_describe_nomme_la_langue(self):
        i18n.use("de")
        self.assertIn("de", i18n.describe())
        self.assertIn("allemand", i18n.describe())


class TestDetection(unittest.TestCase):
    def setUp(self):
        self.avant = i18n.language()

    def tearDown(self):
        i18n.use(self.avant)

    def test_la_variable_dediee_prime_sur_tout(self):
        with mock.patch.dict(os.environ, {i18n.ENV: "it", "LANG": "de_DE"}):
            with mock.patch.object(i18n, "_from_windows", return_value="en"):
                self.assertEqual(i18n.detect(), "it")

    def test_une_variable_dediee_absurde_est_ignoree(self):
        # On ne veut pas qu'une faute de frappe dans l'environnement fasse
        # tomber le daemon : elle est ignoree, la detection continue.
        #
        # La plateforme est imposee : hors Windows, _from_windows n'est meme pas
        # consultee, et un test qui la surchargeait passait ici pour echouer sur
        # la CI - c'est exactement ce qui s'est produit.
        with mock.patch.object(i18n.sys, "platform", "linux"):
            with mock.patch.dict(os.environ,
                                 {i18n.ENV: "klingon", "LANG": "es_ES.UTF-8"},
                                 clear=True):
                self.assertEqual(i18n.detect(), "es")

    def test_sous_windows_le_systeme_passe_avant_LANG(self):
        # Git Bash pose LANG=en_US quoi qu'il arrive : le suivre rendrait la
        # detection aveugle a la langue reelle de la machine.
        with mock.patch.object(i18n.sys, "platform", "win32"):
            with mock.patch.dict(os.environ, {"LANG": "en_US.UTF-8"}, clear=True):
                with mock.patch.object(i18n, "_from_windows", return_value="fr"):
                    self.assertEqual(i18n.detect(), "fr")

    def test_hors_windows_ce_sont_les_variables_qui_parlent(self):
        with mock.patch.object(i18n.sys, "platform", "linux"):
            with mock.patch.dict(os.environ, {"LANG": "de_DE.UTF-8"}, clear=True):
                self.assertEqual(i18n.detect(), "de")

    def test_le_francais_en_dernier_recours(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch.object(i18n, "_from_windows", return_value=None):
                with mock.patch.object(i18n, "_from_locale", return_value=None):
                    self.assertEqual(i18n.detect(), i18n.FALLBACK)

    def test_les_variables_posix_servent_quand_le_systeme_se_tait(self):
        with mock.patch.dict(os.environ, {"LANG": "it_IT.UTF-8"}, clear=True):
            with mock.patch.object(i18n, "_from_windows", return_value=None):
                self.assertEqual(i18n.detect(), "it")


class TestTexte(unittest.TestCase):
    def setUp(self):
        self.avant = i18n.language()

    def tearDown(self):
        i18n.use(self.avant)

    def test_le_libelle_suit_la_langue_courante(self):
        i18n.use("de")
        self.assertEqual(i18n.text("title_goal"), "TOR!")
        i18n.use("es")
        self.assertEqual(i18n.text("title_goal"), "GOL!")

    def test_la_langue_demandee_ne_change_pas_la_courante(self):
        # C'est ce qui permet au journal de rester francais pendant que les
        # cartes parlent allemand, sans etat global a basculer entre deux fils.
        i18n.use("de")
        self.assertEqual(i18n.text("title_goal", lang="fr"), "BUT !")
        self.assertEqual(i18n.language(), "de")
        self.assertEqual(i18n.text("title_goal"), "TOR!")

    def test_les_valeurs_sont_posees(self):
        i18n.use("en")
        self.assertEqual(i18n.text("minute", minute="35'"), "Minute 35'")
        self.assertEqual(i18n.text("kickoff_in", minutes=5), "Kick-off in 5 min")

    def test_une_cle_inconnue_rend_la_cle(self):
        # Une carte de but ne doit jamais tomber parce qu'il manque une
        # traduction.
        self.assertEqual(i18n.text("cle_qui_n_existe_pas"), "cle_qui_n_existe_pas")

    def test_une_cle_absente_d_un_catalogue_retombe_sur_le_francais(self):
        i18n.use("de")
        with mock.patch.dict(i18n.MESSAGES["de"], clear=False) as _:
            del i18n.MESSAGES["de"]["title_goal"]
            try:
                self.assertEqual(i18n.text("title_goal"), "BUT !")
            finally:
                i18n.MESSAGES["de"]["title_goal"] = "TOR!"

    def test_une_valeur_manquante_ne_leve_pas(self):
        # Mieux vaut un libelle a trou qu'une carte perdue.
        self.assertEqual(i18n.text("minute"), i18n.MESSAGES[i18n.language()]["minute"])

    def test_all_texts_donne_les_cinq_formulations(self):
        titres = i18n.all_texts("title_cancelled")
        self.assertIn("BUT ANNULE", titres)
        self.assertIn("TOR ABERKANNT", titres)
        self.assertEqual(len(titres), len(set(titres)))


def _un_but(lang, **kwargs):
    """Un evenement de but, cartes rendues dans `lang`."""
    state = {"payload": payload(event(home_score=1, away_score=1))}
    guard = watcher.Watcher([LIGUE1], opener=opener_for(state))
    guard.prime()
    state["payload"] = bump(state["payload"], "away", **kwargs)
    i18n.use(lang)
    return guard.refresh(LIGUE1)[0]


class TestLesCartesParlentLaLangue(unittest.TestCase):
    def setUp(self):
        self.avant = i18n.language()

    def tearDown(self):
        i18n.use(self.avant)

    def test_le_titre_d_un_but(self):
        attendus = {"fr": "BUT !", "en": "GOAL!", "es": "GOL!", "it": "GOL!",
                    "de": "TOR!"}
        for lang, attendu in attendus.items():
            self.assertEqual(_un_but(lang).title, attendu, lang)

    def test_le_buteur(self):
        details = (goal_detail("A1", "58'", "A. Kalimuendo", index=3),)
        attendus = {
            "fr": "But de A. Kalimuendo",
            "en": "Goal by A. Kalimuendo",
            "es": "Gol de A. Kalimuendo",
            "it": "Gol di A. Kalimuendo",
            "de": "Tor von A. Kalimuendo",
        }
        for lang, attendu in attendus.items():
            self.assertEqual(_un_but(lang, details=details).detail_line(),
                             attendu, lang)

    def test_le_csc_et_le_penalty(self):
        csc = (goal_detail("A1", "17'", "J. Lefort", own_goal=True, index=4),)
        for lang, titre in (("fr", "BUT CONTRE SON CAMP"), ("de", "EIGENTOR"),
                            ("it", "AUTOGOL"), ("es", "GOL EN PROPIA")):
            self.assertEqual(_un_but(lang, details=csc).title, titre, lang)

    def test_un_but_annule(self):
        for lang, attendu in (("fr", "Score corrige"), ("en", "Score corrected"),
                              ("de", "Spielstand korrigiert")):
            evenement = _un_but(lang, by=-1)
            self.assertEqual(evenement.detail_line(), attendu, lang)

    def test_la_carte_reprend_la_traduction(self):
        i18n.use("de")
        carte = overlay.Card.from_event(_un_but("de"))
        self.assertEqual(carte.title, "TOR!")

    def test_la_carte_de_demonstration_aussi(self):
        i18n.use("it")
        self.assertEqual(overlay.Card.demo().title, "GOL!")
        self.assertTrue(overlay.Card.demo().detail.startswith("Gol di "))


class TestLeJournalResteEnFrancais(unittest.TestCase):
    """Le journal voisine la ligne de commande, et --today le relit."""

    def setUp(self):
        self.avant = i18n.language()

    def tearDown(self):
        i18n.use(self.avant)

    def test_la_ligne_de_journal_ne_suit_pas_la_langue(self):
        details = (goal_detail("A1", "58'", "A. Kalimuendo", index=5),)
        allemand = _un_but("de", details=details)
        self.assertEqual(allemand.title, "TOR!")          # la carte, oui
        ligne = allemand.log_line()
        self.assertTrue(ligne.startswith("BUT "), ligne)  # le journal, non
        self.assertIn("But de A. Kalimuendo", ligne)
        self.assertNotIn("Tor von", ligne)

    def test_un_journal_ecrit_en_allemand_reste_relisible(self):
        # Le format ne bouge pas avec la langue : --today marche toujours.
        details = (goal_detail("A1", "58'", "A. Kalimuendo", index=6),)
        ligne = _un_but("de", details=details).log_line()
        entree = journal.parse_line("2026-09-06 21:14:07  " + ligne)
        self.assertIsNotNone(entree)
        self.assertEqual(entree.kind, watcher.GOAL)
        self.assertEqual(entree.scorer, "A. Kalimuendo")

    def test_le_titre_est_toujours_disponible_en_francais(self):
        i18n.use("es")
        self.assertEqual(watcher.title_of(watcher.FULLTIME, lang="fr"),
                         "FIN DU MATCH")
        self.assertEqual(watcher.title_of(watcher.FULLTIME), "FINAL DEL PARTIDO")


class TestPlay(unittest.TestCase):
    def setUp(self):
        self.avant = i18n.language()

    def tearDown(self):
        i18n.use(self.avant)

    def test_le_prefixe_et_sa_preposition(self):
        play = espn.Play("k", "1", "35'", "Goal", "C. Arcus", False, False, False)
        i18n.use("de")
        self.assertEqual(play.prefix(), "Tor")
        self.assertEqual(play.prefix_for(), "Tor von ")
        self.assertEqual(play.summary(), "Tor von C. Arcus (35')")
        # Et la langue demandee explicitement l'emporte.
        self.assertEqual(play.prefix(lang="it"), "Gol")

    def test_le_carton_rouge_a_sa_propre_preposition(self):
        rouge = espn.Play("k", "1", "62'", "Red Card", "J. Lefort", False, False,
                          False, red_card=True)
        i18n.use("de")
        # L'allemand ne met pas de preposition ici : "Rote Karte: X".
        self.assertEqual(rouge.summary(), "Rote Karte: J. Lefort (62')")
        i18n.use("fr")
        self.assertEqual(rouge.summary(), "Carton rouge pour J. Lefort (62')")


class TestLaProseDeLaLigneDeCommande(unittest.TestCase):
    """Le francais sert de cle : les catalogues doivent lui coller."""

    def phrases(self):
        """Les phrases que le programme passe a tr(), extraites du code.

        Tout le paquet, et pas seulement cli.py : --status affiche aussi ce que
        lui rendent state, screens et leagues, et ces trois-la traduisent leurs
        valeurs eux-memes.
        """
        import ast

        trouvees = []
        dossier = pathlib.Path(cli.__file__).parent
        for fichier in sorted(dossier.glob("*.py")):
            source = fichier.read_text(encoding="utf-8")
            for noeud in ast.walk(ast.parse(source)):
                if (isinstance(noeud, ast.Call)
                        and getattr(noeud.func, "id", None) == "tr"
                        and noeud.args
                        and isinstance(noeud.args[0], ast.Constant)
                        and isinstance(noeud.args[0].value, str)):
                    trouvees.append(noeud.args[0].value)
        return trouvees

    def test_il_y_a_de_la_prose_a_traduire(self):
        # Garde-fou : si quelqu'un defait l'extraction, ce test le dit.
        self.assertGreater(len(set(self.phrases())), 80)

    def test_aucune_traduction_orpheline(self):
        """Une cle qui ne correspond a aucune phrase du code est morte.

        Elle vient d'une phrase reformulee depuis : la traduction ne sortira
        jamais, et personne ne s'en apercevra.
        """
        connues = set(self.phrases()) | set(i18n.MESSAGES[i18n.FALLBACK])
        for code, catalogue in lang.CATALOGUES.items():
            orphelines = sorted(set(catalogue) - connues)
            self.assertEqual(orphelines, [],
                             "cles mortes dans le catalogue {}".format(code))

    def test_les_trous_a_valeur_sont_preserves(self):
        """Une traduction qui perd une accolade perd sa donnee."""
        import re

        trous = re.compile(r"\{[^}]*\}")
        for code, catalogue in lang.CATALOGUES.items():
            for francais, traduit in catalogue.items():
                self.assertEqual(len(trous.findall(traduit)),
                                 len(trous.findall(francais)),
                                 "{} : {!r}".format(code, francais))

    def test_les_colonnes_de_status_restent_alignees(self):
        """Les etiquettes de --status forment une colonne : elle doit tenir.

        Le gabarit entier est traduit, alignement compris. Une traduction plus
        longue que le francais decalerait sa ligne, et --status deviendrait
        illisible dans cette langue.
        """
        gabarits = [p for p in self.phrases()
                    if p.startswith("  ") and " : " in p[:20]]
        self.assertGreater(len(gabarits), 8)

        for code, catalogue in lang.CATALOGUES.items():
            for francais in gabarits:
                traduit = catalogue.get(francais)
                if traduit is None:
                    continue
                self.assertEqual(traduit.index(" : "), francais.index(" : "),
                                 "{} : la colonne bouge sur {!r}".format(
                                     code, francais))


if __name__ == "__main__":
    unittest.main()
