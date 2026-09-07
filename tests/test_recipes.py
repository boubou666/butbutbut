"""Les recettes de recipes/ : elles compilent, elles sont listees, elles ne
mentent pas sur les variables du crochet.

Ces fichiers-la ne sont importes par personne : rien dans butbutbut ne les
appelle, c'est l'utilisateur qui les lance. Sans tests, ils pourriraient en
silence - une variable `BUT_` renommee, une recette ajoutee et jamais listee,
un accent glisse dans un depot qui n'en veut pas. Le test qui compte est celui
qui compare **chaque nom `BUT_` ecrit dans ce dossier** a ce que `hook.py`
publie vraiment : c'est lui qui empechera une recette de promettre un detail
que le crochet ne donne pas.

Rien ici ne parle au reseau, n'allume d'ampoule ni n'ecrit hors d'un dossier
temporaire : les recettes sont chargees comme des modules (leur garde
`__main__` les empeche de s'executer), et seules leurs fonctions pures et leurs
sorties d'erreur sont eprouvees.
"""

import importlib.util
import os
import re
import sys
import unittest
import unittest.mock
from tempfile import TemporaryDirectory

from butbutbut import hook, leagues, watcher

from helpers import bump, event, goal_detail, opener_for, payload

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECIPES = os.path.join(ROOT, "recipes")

# Le prefixe seul ("BUT_") et les noms composes ("BUTBUTBUT_HA_URL") ne sont
# pas des variables du crochet : la garde de gauche les ecarte.
BUT_NAME = re.compile(r"(?<![A-Z0-9_])BUT_[A-Z][A-Z0-9_]*")
SETTING_NAME = re.compile(r"BUTBUTBUT_[A-Z][A-Z0-9_]*")


def recipe_files():
    """Les recettes, README exclu. Triees, pour un echec toujours lisible."""
    return sorted(name for name in os.listdir(RECIPES)
                  if name != "README.md" and not name.startswith(".")
                  and os.path.isfile(os.path.join(RECIPES, name)))


def read(name):
    with open(os.path.join(RECIPES, name), "r", encoding="utf-8") as handle:
        return handle.read()


def load(name):
    """Une recette chargee comme un module, sans passer par son `main`.

    Le `.pyc` est refuse au passage : un dossier qu'on donne a copier n'a pas a
    se remplir de `__pycache__` parce que la suite de tests est passee.
    """
    spec = importlib.util.spec_from_file_location(
        "recette_" + name.replace(".", "_"), os.path.join(RECIPES, name))
    module = importlib.util.module_from_spec(spec)
    keep = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = keep
    return module


def published():
    """Les variables que le crochet pose vraiment, prises a la source.

    On ne se contente pas de `hook.demo()` : l'environnement d'un vrai but,
    sorti du watcher, est ce que les recettes liront le dimanche soir.
    """
    ligue1 = leagues.BY_SLUG["fra.1"]
    source = {"payload": payload(event(home_score=1, away_score=1))}
    guard = watcher.Watcher([ligue1], opener=opener_for(source))
    guard.prime()
    source["payload"] = bump(
        source["payload"], "away",
        details=(goal_detail("A1", "58'", "A. Kalimuendo", index=3),))
    goal = guard.refresh(ligue1)[0]
    return set(hook.environment(goal)) | set(hook.demo())


class TestRecipesExist(unittest.TestCase):

    def test_le_dossier_a_des_recettes_et_un_readme(self):
        self.assertTrue(os.path.isdir(RECIPES))
        self.assertTrue(os.path.isfile(os.path.join(RECIPES, "README.md")))
        # Cinq recettes, c'est le seuil en dessous duquel le dossier
        # redeviendrait l'exemple unique qu'il remplace.
        self.assertGreaterEqual(len(recipe_files()), 5)

    def test_chaque_recette_est_du_python_ou_du_shell(self):
        for name in recipe_files():
            self.assertTrue(name.endswith((".py", ".sh", ".ps1")),
                            "extension inattendue : " + name)

    def test_chaque_recette_est_en_ascii_pur(self):
        # Comme tout le depot : un accent traverse mal les consoles Windows.
        for name in recipe_files():
            with self.subTest(recette=name):
                read(name).encode("ascii")

    def test_chaque_recette_a_un_en_tete_complet(self):
        # Une recette sans "A regler" et sans "Systemes" est inutilisable : on
        # ne sait ni ce qu'elle demande, ni ou elle tourne.
        for name in recipe_files():
            with self.subTest(recette=name):
                head = read(name)[:2000]
                self.assertIn("A regler", head)
                self.assertIn("Systemes", head)

    def test_chaque_recette_python_a_une_garde_main(self):
        # Sans elle, charger la recette pour la tester la lancerait.
        for name in recipe_files():
            if name.endswith(".py"):
                with self.subTest(recette=name):
                    self.assertIn('if __name__ == "__main__":', read(name))


class TestRecipesLoad(unittest.TestCase):
    """Elles compilent, elles se chargent, et rien ne part au chargement."""

    def test_chaque_recette_python_compile(self):
        for name in recipe_files():
            if name.endswith(".py"):
                with self.subTest(recette=name):
                    compile(read(name), name, "exec")

    def test_chaque_recette_python_se_charge_sans_environnement(self):
        # Une recette qui lirait sa configuration au chargement plutot que dans
        # son `main` echouerait ici, et c'est bien le but : le crochet ne
        # garantit qu'une chose, c'est qu'il lance le fichier.
        for name in recipe_files():
            if name.endswith(".py"):
                with self.subTest(recette=name):
                    with unittest.mock.patch.dict(os.environ, {}, clear=True):
                        module = load(name)
                    self.assertTrue(callable(getattr(module, "main", None)),
                                    name + " n'expose pas main()")


class TestRecipesReadme(unittest.TestCase):

    def setUp(self):
        self.readme = read("README.md")

    def test_chaque_recette_est_listee(self):
        for name in recipe_files():
            with self.subTest(recette=name):
                self.assertIn(name, self.readme)

    def test_le_readme_ne_liste_que_des_recettes_qui_existent(self):
        # Les liens du tableau : `[`nom`](nom)`. Une recette renommee sans
        # toucher au README laisserait un lien mort.
        linked = set(re.findall(r"\]\(([A-Za-z0-9_.-]+\.(?:py|sh|ps1))\)",
                                self.readme))
        self.assertTrue(linked)
        self.assertEqual(linked - set(recipe_files()), set())

    def test_chaque_reglage_est_documente(self):
        """Un BUTBUTBUT_* lu par une recette et absent du README est un piege.

        Le lecteur ne devinera pas le nom d'une variable d'environnement.
        """
        for name in recipe_files():
            for setting in sorted(set(SETTING_NAME.findall(read(name)))):
                with self.subTest(recette=name, reglage=setting):
                    self.assertIn(setting, self.readme)


class TestRecipesUseRealVariables(unittest.TestCase):
    """Le test qui empeche ce dossier de pourrir."""

    def test_aucune_recette_n_invente_de_variable(self):
        known = published()
        for name in recipe_files() + ["README.md"]:
            for found in sorted(set(BUT_NAME.findall(read(name)))):
                with self.subTest(recette=name, variable=found):
                    self.assertIn(found, known)

    def test_les_recettes_lisent_vraiment_le_crochet(self):
        # Un dossier ou plus aucune recette ne nommerait une variable BUT_
        # rendrait le test precedent vrai et vide.
        used = set()
        for name in recipe_files():
            used |= set(BUT_NAME.findall(read(name)))
        self.assertIn("BUT_TEXT", used)
        self.assertIn("BUT_TYPE", used)

    def test_le_readme_du_dossier_renvoie_au_contrat(self):
        self.assertIn("hook.py", read("README.md"))


class TestRecipesAreQuietWithoutSecrets(unittest.TestCase):
    """Sans secret, une recette reseau se plaint en une ligne et sort avec 1.

    Le journal ne garde que la premiere ligne, et seulement 120 signes : une
    recette qui repondrait par une trace d'exception n'y laisserait rien
    d'utile. Aucun de ces appels ne touche au reseau - ils s'arretent avant.
    """

    def check(self, name, named):
        """Lance la recette sans rien dans l'environnement, et lit sa plainte.

        Le `print` de la recette est detourne plutot que la sortie du processus
        entier : la suite reste silencieuse, meme quand elle eprouve des echecs.
        """
        module = load(name)
        lines = []
        with unittest.mock.patch.dict(os.environ, {}, clear=True),                 unittest.mock.patch.object(module, "print", lines.append,
                                           create=True):
            code = module.main()
        self.assertEqual(code, 1)
        self.assertEqual(len(lines), 1)
        self.assertLessEqual(len(lines[0]), hook.OUTPUT_LIMIT)
        self.assertIn(named, lines[0])

    def test_discord_sans_son_webhook(self):
        self.check("discord_webhook.py", "BUTBUTBUT_DISCORD_WEBHOOK")

    def test_slack_sans_son_webhook(self):
        self.check("slack_webhook.py", "BUTBUTBUT_SLACK_WEBHOOK")

    def test_home_assistant_sans_jeton(self):
        self.check("home_assistant.py", "BUTBUTBUT_HA_URL")

    def test_ampoule_sans_adresse(self):
        self.check("ampoule_wiz.py", "BUTBUTBUT_WIZ_HOST")


class TestDiscordPayload(unittest.TestCase):

    def setUp(self):
        self.module = load("discord_webhook.py")

    def payload(self, **changes):
        values = dict(hook.demo())
        values.update(changes)
        with unittest.mock.patch.dict(os.environ, values, clear=True):
            return self.module.payload()

    def test_un_but_donne_une_carte_verte(self):
        body = self.payload()
        embed = body["embeds"][0]
        self.assertEqual(embed["title"], "BUT !")
        self.assertIn("Marseille 2 - 1 Paris FC", embed["description"])
        self.assertEqual(embed["color"], self.module.COLOR_GOAL)

    def test_un_but_retire_par_la_var_donne_une_carte_rouge(self):
        embed = self.payload(BUT_TYPE="cancelled")["embeds"][0]
        self.assertEqual(embed["color"], self.module.COLOR_CANCELLED)
        self.assertIn("VAR", embed["title"])

    def test_le_buteur_et_sa_minute_sont_dans_un_champ(self):
        fields = self.payload()["embeds"][0]["fields"]
        self.assertIn("M. Greenwood - 67'",
                      [field["value"] for field in fields])

    def test_sans_buteur_le_champ_disparait(self):
        # La source ne publie pas toujours l'action : un champ "But de :" vide
        # ferait croire a un bug de la recette.
        fields = self.payload(BUT_SCORER="", BUT_MINUTE="")["embeds"][0]["fields"]
        self.assertEqual(len(fields), 1)

    def test_un_penalty_se_voit(self):
        fields = self.payload(BUT_PENALTY="1")["embeds"][0]["fields"]
        self.assertIn("(penalty)", " ".join(field["value"] for field in fields))


class TestSlackPayload(unittest.TestCase):

    def setUp(self):
        self.module = load("slack_webhook.py")

    def body(self, **changes):
        values = dict(hook.demo())
        values.update(changes)
        with unittest.mock.patch.dict(os.environ, values, clear=True):
            return self.module.payload()

    def test_la_phrase_toute_faite_part_telle_quelle(self):
        self.assertIn("BUT ! [Ligue 1] Marseille 2 - 1 Paris FC",
                      self.body()["text"])

    def test_un_but_retire_change_l_emoji(self):
        self.assertIn(":no_entry_sign:", self.body(BUT_TYPE="cancelled")["text"])

    def test_le_balisage_de_slack_est_neutralise(self):
        # Un club nomme "Foot & Co" ne doit pas ressortir en "Foot &amp; Co".
        self.assertEqual(self.module.escape("A & <B>"), "A &amp; &lt;B&gt;")


class TestCompteur(unittest.TestCase):

    def setUp(self):
        self.module = load("compteur.py")

    def count(self, data, **changes):
        values = dict(hook.demo())
        values.update(changes)
        with unittest.mock.patch.dict(os.environ, values, clear=True):
            return self.module.updated(data, self.module.delta())

    def test_un_but_ajoute_un(self):
        data = self.count({})
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["par_equipe"]["Marseille"], 1)
        self.assertEqual(data["par_competition"]["Ligue 1"], 1)

    def test_un_but_retire_par_la_var_enleve_un(self):
        data = self.count({"total": 3, "par_equipe": {"Marseille": 2},
                           "par_competition": {"Ligue 1": 3}},
                          BUT_TYPE="cancelled", BUT_DELTA="-1")
        self.assertEqual(data["total"], 2)
        self.assertEqual(data["par_equipe"]["Marseille"], 1)

    def test_un_doublon_rattrape_compte_double(self):
        # BUT_DELTA vaut 2 quand un but rate au releve precedent est rattrape.
        self.assertEqual(self.count({}, BUT_DELTA="2")["total"], 2)

    def test_un_compteur_ne_descend_pas_sous_zero(self):
        # Une annulation lue apres un redemarrage, sans le but qui va avec.
        data = self.count({}, BUT_TYPE="cancelled", BUT_DELTA="-1")
        self.assertEqual(data["total"], 0)
        self.assertEqual(data["par_equipe"]["Marseille"], 0)

    def test_une_annulation_ne_touche_pas_au_dernier_but(self):
        data = self.count({"dernier": {"texte": "un but"}},
                          BUT_TYPE="cancelled", BUT_DELTA="-1")
        self.assertEqual(data["dernier"]["texte"], "un but")

    def test_un_delta_illisible_vaut_un_but(self):
        with unittest.mock.patch.dict(os.environ, {"BUT_DELTA": "beaucoup"},
                                      clear=True):
            self.assertEqual(self.module.delta(), 1)

    def test_un_fichier_illisible_repart_de_zero(self):
        # Plutot que de refuser le but : un compteur perdu se reconstitue,
        # un but perdu non.
        with TemporaryDirectory() as folder:
            path = os.path.join(folder, "compteur.json")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("{ ceci n'est pas du json")
            self.assertEqual(self.module.load(path), {})

    def test_l_aller_retour_par_le_fichier(self):
        with TemporaryDirectory() as folder:
            path = os.path.join(folder, "compteur.json")
            self.module.save(path, self.count({}))
            self.assertEqual(self.module.load(path)["total"], 1)

    def test_un_verrou_deja_pris_ne_bloque_pas_indefiniment(self):
        # Attendre sans fin tiendrait un des huit fils du crochet jusqu'a ce
        # que butbutbut le tue : mieux vaut un but non compte.
        with TemporaryDirectory() as folder:
            lock = os.path.join(folder, "compteur.json.lock")
            open(lock, "w").close()
            waited = []
            taken = self.module.take_lock(lock, patience=0.0,
                                          sleep=waited.append)
            self.assertFalse(taken)
            self.assertEqual(waited, [])

    def test_un_verrou_qui_se_libere_finit_par_se_prendre(self):
        # Le cas normal d'un multiplex : le but d'a cote avait pris le fichier,
        # il le rend, et celui-ci se compte quand meme.
        with TemporaryDirectory() as folder:
            lock = os.path.join(folder, "compteur.json.lock")
            open(lock, "w").close()
            taken = self.module.take_lock(
                lock, patience=5.0, sleep=lambda _delay: os.unlink(lock))
            self.assertTrue(taken)

    def test_un_verrou_libre_se_prend(self):
        with TemporaryDirectory() as folder:
            lock = os.path.join(folder, "compteur.json.lock")
            self.assertTrue(self.module.take_lock(lock))
            self.assertTrue(os.path.exists(lock))


class TestObsTexte(unittest.TestCase):

    def setUp(self):
        self.module = load("obs_texte.py")

    def banner(self, **changes):
        values = dict(hook.demo())
        values.update(changes)
        with unittest.mock.patch.dict(os.environ, values, clear=True):
            return self.module.banner()

    def test_le_bandeau_tient_sur_une_ligne(self):
        line = self.banner()
        self.assertNotIn("\n", line)
        self.assertIn("BUT : Marseille 2 - 1 Paris FC", line)
        self.assertIn("M. Greenwood", line)

    def test_un_but_retire_se_signale(self):
        self.assertTrue(self.banner(BUT_TYPE="cancelled").startswith("VAR"))

    def test_la_duree_est_bornee_par_le_delai_du_crochet(self):
        module = self.module
        with unittest.mock.patch.dict(os.environ,
                                      {"BUTBUTBUT_OBS_SECONDES": "600"},
                                      clear=True):
            self.assertLessEqual(module.seconds(), module.MAX_SECONDS)
        self.assertLess(module.MAX_SECONDS, hook.DEFAULT_TIMEOUT)

    def test_une_duree_illisible_ne_fait_pas_tomber_la_recette(self):
        module = self.module
        with unittest.mock.patch.dict(os.environ,
                                      {"BUTBUTBUT_OBS_SECONDES": "longtemps"},
                                      clear=True):
            self.assertEqual(module.seconds(), module.DEFAULT_SECONDS)

    def test_le_bandeau_s_efface_apres_coup(self):
        module = self.module
        with TemporaryDirectory() as folder:
            path = os.path.join(folder, "bandeau.txt")
            values = dict(hook.demo())
            values["BUTBUTBUT_OBS_FICHIER"] = path
            shown = []
            with unittest.mock.patch.dict(os.environ, values, clear=True):
                code = module.main(sleep=lambda _delay:
                                   shown.append(module.read(path)))
            self.assertEqual(code, 0)
            self.assertIn("Marseille 2 - 1 Paris FC", shown[0])
            self.assertEqual(module.read(path), "")

    def test_un_but_plus_recent_garde_le_bandeau(self):
        # Le deuxieme but a ecrit pendant qu'on attendait : ce n'est plus a
        # nous d'effacer, sinon le bandeau clignoterait a chaque doublon.
        module = self.module
        with TemporaryDirectory() as folder:
            path = os.path.join(folder, "bandeau.txt")
            values = dict(hook.demo())
            values["BUTBUTBUT_OBS_FICHIER"] = path
            with unittest.mock.patch.dict(os.environ, values, clear=True):
                module.main(sleep=lambda _delay:
                            module.write(path, "BUT : un autre\n"))
            self.assertEqual(module.read(path), "BUT : un autre\n")


class TestAmpouleWiz(unittest.TestCase):

    def setUp(self):
        self.module = load("ampoule_wiz.py")

    def color(self, **changes):
        with unittest.mock.patch.dict(os.environ, changes, clear=True):
            return self.module.color()

    def test_un_but_est_vert_par_defaut(self):
        self.assertEqual(self.color(), self.module.DEFAULT_COLOR)

    def test_un_but_retire_est_rouge_quoi_qu_on_regle(self):
        # Le rouge dit "ce but n'est plus la" : une couleur choisie ne doit pas
        # rendre les deux evenements indiscernables.
        self.assertEqual(self.color(BUT_TYPE="cancelled",
                                    BUTBUTBUT_WIZ_COLOR="0,0,255"),
                         self.module.CANCELLED_COLOR)

    def test_une_couleur_choisie_est_reprise(self):
        self.assertEqual(self.color(BUTBUTBUT_WIZ_COLOR="10, 20, 30"),
                         (10, 20, 30))

    def test_une_couleur_illisible_retombe_sur_le_defaut(self):
        self.assertEqual(self.color(BUTBUTBUT_WIZ_COLOR="bleu"),
                         self.module.DEFAULT_COLOR)
        self.assertEqual(self.color(BUTBUTBUT_WIZ_COLOR="1,2"),
                         self.module.DEFAULT_COLOR)

    def test_une_couleur_hors_bornes_est_ramenee_dans_l_octet(self):
        self.assertEqual(self.color(BUTBUTBUT_WIZ_COLOR="900,-5,10"),
                         (255, 0, 10))

    def test_la_duree_reste_sous_le_delai_du_crochet(self):
        with unittest.mock.patch.dict(os.environ,
                                      {"BUTBUTBUT_WIZ_SECONDS": "3600"},
                                      clear=True):
            self.assertLessEqual(self.module.seconds(), self.module.MAX_SECONDS)
        self.assertLess(self.module.MAX_SECONDS, hook.DEFAULT_TIMEOUT)

    def run_main(self, folder, replies, host="10.0.0.9"):
        """Un but complet, sans reseau, sans attente et sans vrai verrou.

        `replies` est ce que l'ampoule repond a chaque trame : None quand elle
        se tait. Rend (code de sortie, trames envoyees, lignes imprimees).
        """
        sent, lines, answers = [], [], list(replies)

        def send(_host, message, wait_for_reply=True):
            sent.append(message)
            return answers.pop(0) if answers else None

        lock = os.path.join(folder, "wiz.lock")
        values = {"BUTBUTBUT_WIZ_HOST": host}
        with unittest.mock.patch.dict(os.environ, values, clear=True), \
                unittest.mock.patch.object(self.module, "send", send), \
                unittest.mock.patch.object(self.module, "lock_path",
                                           lambda: lock), \
                unittest.mock.patch.object(self.module, "print", lines.append,
                                           create=True):
            code = self.module.main(sleep=lambda _delay: None)
        return code, sent, lines

    def test_l_ampoule_retrouve_exactement_l_etat_qu_elle_avait(self):
        # C'est toute la recette : un salon rendu comme on l'a trouve. Le
        # `sceneId` et le `temp` reviennent avec, sinon une ampoule reglee en
        # blanc chaud finirait la soiree en couleur.
        before = {"state": True, "dimming": 40, "temp": 2700, "sceneId": 12,
                  "rssi": -55}
        with TemporaryDirectory() as folder:
            code, sent, lines = self.run_main(
                folder, [{"result": before}])
        self.assertEqual(code, 0)
        self.assertEqual(lines, [])                 # une reussite se tait
        self.assertEqual([trame["method"] for trame in sent],
                         ["getPilot", "setPilot", "setPilot"])
        self.assertEqual(sent[1]["params"]["g"], self.module.DEFAULT_COLOR[1])
        self.assertEqual(sent[2]["params"],
                         {"state": True, "dimming": 40, "temp": 2700,
                          "sceneId": 12})

    def test_une_ampoule_muette_n_est_pas_touchee(self):
        """Ne pas savoir ou la remettre est une raison de n'y pas toucher."""
        with TemporaryDirectory() as folder:
            code, sent, lines = self.run_main(folder, [None])
        self.assertEqual(code, 1)
        self.assertEqual(len(sent), 1)              # le getPilot, et rien apres
        self.assertIn("10.0.0.9", lines[0])

    def test_une_reponse_biscornue_vaut_un_silence(self):
        # L'ampoule a repondu, mais pas ce qu'on attendait : on ne devine pas.
        with TemporaryDirectory() as folder:
            code, sent, _ = self.run_main(folder, [{"result": "voila"}])
        self.assertEqual(code, 1)
        self.assertEqual(len(sent), 1)

    def test_un_deuxieme_but_repeint_sans_toucher_a_l_etat_garde(self):
        # Le premier but tient le verrou : le deuxieme ne doit ni relire ni
        # remettre, sinon le vert de l'eclat deviendrait l'etat "normal".
        with TemporaryDirectory() as folder:
            lock = os.path.join(folder, "wiz.lock")
            open(lock, "w").close()
            sent = []
            values = {"BUTBUTBUT_WIZ_HOST": "10.0.0.9"}
            with unittest.mock.patch.dict(os.environ, values, clear=True), \
                    unittest.mock.patch.object(
                        self.module, "send",
                        lambda _host, message, **kw: sent.append(message)), \
                    unittest.mock.patch.object(self.module, "lock_path",
                                               lambda: lock):
                code = self.module.main(sleep=lambda _delay: None)
            self.assertEqual(code, 0)
            self.assertEqual([trame["method"] for trame in sent], ["setPilot"])
            self.assertTrue(os.path.exists(lock))   # il ne l'a pas libere

    def test_un_verrou_deja_pris_se_reconnait(self):
        with TemporaryDirectory() as folder:
            lock = os.path.join(folder, "wiz.lock")
            self.assertTrue(self.module.take_lock(lock))
            self.assertFalse(self.module.take_lock(lock))

    def test_un_verrou_oublie_finit_par_se_liberer(self):
        # Une recette tuee en plein eclat laisse son verrou : sans peremption,
        # l'ampoule ne clignoterait plus jamais.
        with TemporaryDirectory() as folder:
            lock = os.path.join(folder, "wiz.lock")
            self.assertTrue(self.module.take_lock(lock))
            old = os.path.getmtime(lock) - self.module.STALE_LOCK - 10
            os.utime(lock, (old, old))
            self.assertTrue(self.module.take_lock(lock))


class TestNotificationBureau(unittest.TestCase):

    def setUp(self):
        self.module = load("notification_bureau.py")

    def test_chaque_systeme_a_sa_commande(self):
        for platform, program in (("linux", "notify-send"),
                                  ("linux2", "notify-send"),
                                  ("darwin", "osascript"),
                                  ("win32", "powershell")):
            with self.subTest(systeme=platform):
                argv = self.module.command(platform, "titre", "texte")
                self.assertEqual(argv[0], program)

    def test_un_systeme_inconnu_ne_lance_rien(self):
        self.assertIsNone(self.module.command("aix7", "titre", "texte"))

    def test_le_texte_passe_en_argument_jamais_dans_un_script(self):
        """Un nom d'equipe ne doit jamais devenir du code.

        C'est la promesse du crochet lui-meme ; une recette qui recollerait le
        texte dans un `-e` d'osascript la reprendrait a son compte.
        """
        piege = '"; do shell script "rm -rf ~'
        argv = self.module.command("darwin", "titre", piege)
        self.assertIn(piege, argv)
        script = argv[argv.index("-e") + 1]
        self.assertNotIn(piege, script)

    def test_le_titre_nomme_l_equipe(self):
        with unittest.mock.patch.dict(os.environ, hook.demo(), clear=True):
            self.assertEqual(self.module.title(), "BUT ! Marseille")

    def test_le_titre_dit_la_var(self):
        values = dict(hook.demo(), BUT_TYPE="cancelled")
        with unittest.mock.patch.dict(os.environ, values, clear=True):
            self.assertIn("VAR", self.module.title())

    def test_le_corps_retombe_sur_le_score_sans_phrase_toute_faite(self):
        values = dict(hook.demo(), BUT_TEXT="")
        with unittest.mock.patch.dict(os.environ, values, clear=True):
            self.assertEqual(self.module.body(), "Marseille 2 - 1 Paris FC")


class TestFiltreShell(unittest.TestCase):
    """Le gabarit shell : on ne lance pas /bin/sh, on lit ce qu'il dit.

    La CI tourne aussi sous Windows, ou il n'y a pas de shell POSIX : ce qui se
    verifie ici, c'est que le gabarit reste un gabarit - des variables du
    crochet correctement citees, et une sortie silencieuse.
    """

    def setUp(self):
        self.text = read("filtre.sh")

    def test_chaque_variable_est_entre_guillemets(self):
        # Sans guillemets, "Paris FC" arriverait au test en deux mots.
        for match in re.finditer(r'\$\{BUT_[A-Z_]+[^}]*\}', self.text):
            start = match.start()
            with self.subTest(bout=match.group(0)):
                self.assertEqual(self.text[start - 1], '"')

    def test_le_gabarit_sort_sans_bruit(self):
        # Un but ecarte n'est pas un echec : sortir avec autre chose que 0
        # remplirait le journal a chaque but des autres equipes.
        self.assertIn("exit 0", self.text)
        self.assertNotIn("exit 1", self.text)

    def test_le_gabarit_passe_la_main_avec_l_environnement(self):
        # `exec` plutot qu'un appel : la recette suivante herite des variables
        # du crochet sans qu'on ait rien a lui repasser.
        self.assertIn("exec ", self.text)


class TestPackagingSaysTheTruth(unittest.TestCase):
    """Le dossier voyage avec les sources, et pas dans le paquet installe.

    Un a-peu-pres ici se paie a l'installation : une recette introuvable apres
    un `pipx install`, ou un paquet qui embarque du code que butbutbut ne lance
    jamais.
    """

    def read_root(self, name):
        with open(os.path.join(ROOT, name), "r", encoding="utf-8") as handle:
            return handle.read()

    def test_le_sdist_emporte_les_recettes(self):
        self.assertIn("recursive-include recipes", self.read_root("MANIFEST.in"))

    def test_le_paquet_installe_ne_les_emporte_pas(self):
        # recipes/ n'est pas un paquet Python et n'a rien a faire dans le
        # wheel : personne dans butbutbut ne l'importe.
        pyproject = self.read_root("pyproject.toml")
        self.assertIn('packages = ["butbutbut"]', pyproject)
        self.assertNotIn("recipes", pyproject.split("[tool.setuptools]")[1])

    def test_le_readme_du_dossier_le_dit(self):
        self.assertIn("pipx", read("README.md"))


if __name__ == "__main__":
    unittest.main()
