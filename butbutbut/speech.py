"""La voix : dire le but a voix haute, pour qui ne regarde pas l'ecran.

Tout le reste du programme suppose qu'on regarde. Le son dit qu'il s'est passe
quelque chose, la carte dit quoi - mais elle ne dit rien a qui travaille dans
une autre fenetre, sur un autre bureau, ou ne voit pas l'ecran du tout. Une
phrase dite a voix haute porte le score et le buteur sans qu'on leve les yeux.
C'est du confort, et accessoirement de l'accessibilite.

La phrase n'est pas fabriquee ici : c'est celle du crochet (`hook.phrase_of`,
la variable `BUT_TEXT`), et elle suit la **langue des cartes**, pas celle du
journal - on parle a qui regarde l'ecran, pas a qui relira `--today` demain
matin. Ecrire ici une seconde formulation aurait garanti qu'un jour les deux ne
disent plus la meme chose.

Trois systemes, trois programmes, zero dependance :

  - **Windows** : PowerShell et `System.Speech.Synthesis`, present depuis
    toujours et sans rien a installer. Le texte part par une **variable
    d'environnement**, jamais recolle dans le script - meme raison qu'au
    crochet : le jour ou la source annoncera un club nomme `'; rm -rf ~`, ce
    sera un nom d'equipe et rien d'autre ;
  - **macOS** : `say`, livre avec le systeme. Il n'a pas d'option de langue :
    c'est la voix reglee dans les preferences qui parle, quelle que soit celle
    des cartes. `say -v '?'` les enumere ;
  - **Linux** : `spd-say` (speech-dispatcher), puis `espeak-ng`, puis `espeak`,
    le premier qui existe. Aucun n'est la partout, d'ou l'ordre : `spd-say`
    passe par le bureau et sa voix reglee, les deux autres parlent tout seuls.

Ce qui ne doit jamais arriver, et n'arrive pas :

  - **le daemon ne meurt pas** : programme absent, voix non installee, commande
    qui rend 1, commande qui ne rend jamais la main - une ligne de journal, et
    la vie continue. Une ligne **une seule fois** : un daemon qui tourne six
    heures ecrirait autant de lignes que de buts pour une panne qui ne changera
    plus, et noierait justement les buts ;
  - **le daemon n'attend pas** : la parole vit dans un fil a elle, et surtout
    pas dans celui qui affiche les cartes (tkinter n'aime pas qu'on le fasse
    attendre, et une carte en retard se voit).

Deux buts coup sur coup ne se parlent pas dessus : les phrases font la queue et
sortent l'une apres l'autre. Deux buts du meme releve, c'est souvent deux
matchs differents - en jeter un laisserait croire a un score qui n'existe plus.
La file est bornee a BACKLOG : au-dela, c'est la plus **ancienne en attente**
qui saute, parce qu'un soir de folie on veut savoir ou on en est, pas ecouter
le quart d'heure precedent.

Et la voix arrive apres la corne (AFTER_SOUND) : parler pendant le jingle rend
les deux inaudibles.
"""

from __future__ import annotations

import collections
import os
import shutil
import subprocess
import sys
import threading
import time

from . import i18n

DEFAULT_TIMEOUT = 30.0      # secondes avant de tuer une voix qui s'eternise
BACKLOG = 4                 # phrases en attente au plus (voir en tete)
AFTER_SOUND = 2.5           # la corne synthetisee dure 2,10 s
MAX_DELAY = 15.0            # au-dela, un but annonce n'est plus une nouvelle
OUTPUT_LIMIT = 120          # signes de sortie repris dans le journal

# Sous Windows, sans ca, une console noire clignote a l'ecran a chaque but.
CREATE_NO_WINDOW = 0x08000000

# Ce que le texte traverse sous Windows. Voir le pourquoi en tete de module.
ENV_TEXT = "BUTBUTBUT_SPEAK"
ENV_CULTURE = "BUTBUTBUT_SPEAK_CULTURE"

# La culture demandee a System.Speech pour chacune des cinq langues des cartes.
# Le pays n'y est qu'un pretexte : la selection se fait sur la langue, et une
# voix britannique repond aussi bien qu'une americaine pour "en".
CULTURES = {"fr": "fr-FR", "en": "en-US", "es": "es-ES", "it": "it-IT",
            "de": "de-DE"}

# Le script PowerShell, en une ligne et **sans un seul guillemet double** :
# c'est ce qui rend son passage par la ligne de commande sans surprise, quelle
# que soit la facon dont Windows recolle les arguments.
#
# SelectVoiceByHints est enveloppe : une machine sans voix pour la langue
# demandee ne doit pas se taire, elle doit parler avec celle qu'elle a. Et
# aucune machine n'a les cinq langues installees.
SCRIPT = (
    "$ErrorActionPreference = 'Stop';"
    " Add-Type -AssemblyName System.Speech;"
    " $voice = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
    " try { $voice.SelectVoiceByHints(0, 0, 0,"
    " [System.Globalization.CultureInfo]::GetCultureInfo($env:"
    + ENV_CULTURE + ")) } catch { };"
    " $voice.Speak($env:" + ENV_TEXT + ");"
    " $voice.Dispose()"
)

# PowerShell 5, celui de tous les Windows, avant PowerShell 7 : le premier
# porte System.Speech sans rien installer.
WINDOWS_SHELLS = ("powershell", "pwsh")

MACOS_VOICE = "say"

# Les synthetiseurs Linux, dans l'ordre de preference, et le drapeau par lequel
# chacun accepte une langue - ce n'est pas le meme d'un programme a l'autre.
# `-w` fait attendre spd-say la fin de la phrase : sans lui il rend la main
# aussitot, et notre file d'attente ne servirait plus a rien.
LINUX_VOICES = (
    ("spd-say", ("-w", "-l")),
    ("espeak-ng", ("-v",)),
    ("espeak", ("-v",)),
)


class Timeout(RuntimeError):
    """Le synthetiseur ne rendait pas la main : on l'a tue."""


# ------------------------------------------------------------- la commande ---

def find(platform=None, which=None):
    """(nom connu, chemin) du programme qui sait parler ici, ou None.

    Le nom est celui de nos tables, pas celui du fichier trouve : c'est lui qui
    dit ensuite comment construire la commande, et il ne depend donc pas de la
    facon dont la machine a nomme son binaire.
    """
    system = platform or sys.platform
    lookup = which or shutil.which

    if system == "win32":
        for name in WINDOWS_SHELLS:
            found = lookup(name)
            if found:
                return (name, found)
        return None

    if system == "darwin":
        found = lookup(MACOS_VOICE)
        return (MACOS_VOICE, found) if found else None

    for name, _flags in LINUX_VOICES:
        found = lookup(name)
        if found:
            return (name, found)
    return None


def _argument(text) -> str:
    """Le texte tel qu'il peut partir en argument, sans passer pour une option.

    Un nom d'equipe ne commence pas par un tiret, et la phrase commence par son
    titre - mais la source ecrit ce qu'elle veut, et une espace de plus coute
    moins cher qu'un `-v` interprete par `espeak` un soir de match.
    """
    value = str(text)
    return " " + value if value.startswith("-") else value


def command_for(text, lang=None, platform=None, which=None):
    """(commande, variables d'environnement) pour dire `text`, ou None.

    None veut dire qu'aucun programme de cette machine ne sait parler : c'est
    un cas normal sous Linux, ou rien n'est installe par defaut.

    L'environnement rendu est vide partout sauf sous Windows, ou il porte le
    texte : c'est la seule facon de ne pas le recoller dans un script.
    """
    found = find(platform=platform, which=which)
    if found is None:
        return None
    name, binary = found
    code = i18n.normalize(lang) or i18n.language()

    if name in WINDOWS_SHELLS:
        return ([binary, "-NoProfile", "-NonInteractive", "-Command", SCRIPT],
                {ENV_TEXT: str(text),
                 ENV_CULTURE: CULTURES.get(code, CULTURES[i18n.FALLBACK])})

    if name == MACOS_VOICE:
        # Pas de langue : `say` n'a pas d'option pour ca, il n'a que des noms
        # de voix, qui ne sont les memes sur aucune machine.
        return ([binary, _argument(text)], {})

    flags = dict(LINUX_VOICES)[name]
    return ([binary] + list(flags) + [code, _argument(text)], {})


def merge(values) -> dict:
    """Nos variables posees sur l'environnement du daemon.

    On repart de celui-ci et non d'un environnement vide : PowerShell sans
    SystemRoot, ou `espeak` sans HOME ni les variables du serveur de son, ne
    diraient rien du tout.
    """
    env = dict(os.environ)
    env.update({key: str(value) for key, value in values.items()})
    return env


def run_command(command, env, timeout):
    """Lance le synthetiseur et attend sa fin. Rend (code de sortie, sortie).

    `shell=False`, contrairement au crochet : ici la commande est la notre, et
    le seul morceau qui vienne du reseau est le texte a dire. Il reste donc une
    valeur - un argument, ou une variable d'environnement - et jamais un
    fragment de ligne de shell.
    """
    extra = {}
    if sys.platform == "win32":
        extra["creationflags"] = CREATE_NO_WINDOW
    process = subprocess.Popen(
        command, env=env,
        # Sans DEVNULL, `espeak` sans texte lirait son entree standard et
        # attendrait le delai plutot que de rendre la main.
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **extra)
    try:
        output, _ = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
        raise Timeout(timeout)
    return process.returncode, (output or b"").decode("utf-8", "replace").strip()


def _first_line(output) -> str:
    lines = (output or "").strip().splitlines()
    return lines[0][:OUTPUT_LIMIT] if lines else ""


# ------------------------------------------------------------- la voix -------

class Voice:
    """La voix de --speak : elle dit les buts, un par un, dans un fil a elle.

    Sans l'option, l'objet existe quand meme et ne fait rien : le reste du
    programme n'a donc jamais a se demander si la voix est armee.
    """

    def __init__(self, enabled=True, lang=None, on_log=None,
                 timeout=DEFAULT_TIMEOUT, spawn=None, platform=None,
                 which=None, backlog=BACKLOG, pause=None):
        self.enabled = bool(enabled)
        self.lang = lang
        self.on_log = on_log or (lambda message: None)
        self.timeout = float(timeout)
        # Injectables : un test n'a aucune raison de lancer un vrai
        # synthetiseur, ni de connaitre la plateforme sur laquelle il tourne.
        self.spawn = spawn or run_command
        self.platform = platform
        self.which = which
        self._pending = collections.deque(maxlen=max(1, int(backlog)))
        self._wake = threading.Condition()
        self._stop = threading.Event()   # arret net, file d'attente comprise
        self._closing = False            # on finit la file, puis on s'arrete
        # Egalement injectable : sans quoi le test du decalage d'apres-corne
        # attendrait vraiment deux secondes et demie.
        self._pause = pause or self._stop.wait
        self._thread = None
        self._said = set()          # les pannes deja notees, une fois chacune

    def __bool__(self) -> bool:
        return self.enabled

    def describe(self) -> str:
        """Ce qu'on en dit a --status, en une ligne."""
        found = find(platform=self.platform, which=self.which)
        if found is None:
            return ("aucun programme de synthese vocale ici (installe "
                    "speech-dispatcher ou espeak-ng)")
        name = found[0]
        how = ("PowerShell (System.Speech)" if name in WINDOWS_SHELLS
               else name)
        if not self.enabled:
            return "inactive (voir --speak) - {} parlerait".format(how)
        return "{}, dans la langue des cartes".format(how)

    def say(self, text, after: float = 0.0) -> None:
        """Depose la phrase et rend la main tout de suite.

        `after` retarde la phrase du temps qu'il faut a la corne pour finir. Le
        retard est compte depuis MAINTENANT et pas depuis le moment ou le fil
        la prendra : une phrase qui a deja attendu son tour derriere une autre
        n'a plus rien a attendre.
        """
        if not self.enabled or self._closing or self._stop.is_set():
            return
        phrase = str(text or "").strip()
        if not phrase:
            return
        self._start()
        with self._wake:
            # maxlen jette la plus ancienne en attente. Voir en tete de module.
            self._pending.append(
                (time.monotonic() + max(0.0, min(float(after), MAX_DELAY)),
                 phrase))
            self._wake.notify()

    def close(self, timeout: float = 0.0) -> None:
        """Ne plus rien dire. Sans delai, tout de suite ; sinon, apres la fin.

        Les deux appelants ne veulent pas la meme chose. Le daemon qu'on arrete
        n'a plus rien a raconter : `close()` sans delai jette la file. La demo
        de `--test --speak`, elle, n'a qu'une phrase a faire entendre et n'a
        pas d'autre moment pour ca : `close(2.0)` la laisse finir.

        Le sous-processus deja lance, lui, n'est jamais tue - meme choix que
        pour le jingle (voir sound.release) : couper un mot au milieu a l'arret
        du daemon ressemblerait a un plantage.
        """
        thread = self._thread
        if timeout > 0 and thread is not None:
            self._closing = True
            with self._wake:
                self._wake.notify_all()
            thread.join(timeout)
        self._stop.set()
        with self._wake:
            self._pending.clear()
            self._wake.notify_all()

    # ------------------------------------------------------------ interne ----

    def _start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._closing = False
        self._thread = threading.Thread(target=self._work,
                                        name="butbutbut-speak", daemon=True)
        self._thread.start()

    def _work(self) -> None:
        """Le fil de la voix : une phrase a la fois, jamais deux ensemble."""
        while True:
            with self._wake:
                while (not self._pending and not self._stop.is_set()
                       and not self._closing):
                    self._wake.wait(1.0)
                if self._stop.is_set() or not self._pending:
                    return      # arret net, ou plus rien a dire avant l'arret
                deadline, phrase = self._pending.popleft()
            waiting = deadline - time.monotonic()
            if waiting > 0:
                self._pause(waiting)
                if self._stop.is_set():
                    return
            try:
                self._speak(phrase)
            except Exception as exc:
                # Le fil de la voix ne meurt pas : demain il y aura un autre
                # but, et peut-etre que ca remarchera.
                self._once("inattendu", "voix : {}".format(exc))

    def _speak(self, phrase) -> None:
        found = command_for(phrase, self.lang, platform=self.platform,
                            which=self.which)
        if found is None:
            self._once("absent", "voix : aucun programme de synthese vocale "
                                 "sur cette machine, les buts restent muets "
                                 "(voir le README)")
            return
        command, values = found
        try:
            code, output = self.spawn(command, merge(values), self.timeout)
        except Timeout:
            self._once("delai", "voix : {} tue apres {:.0f}s (il ne rendait "
                                "pas la main)".format(command[0], self.timeout))
        except Exception as exc:
            self._once("lancement", "voix : impossible de lancer {} ({})"
                                    .format(command[0], exc))
        else:
            if code:
                first = _first_line(output)
                self._once("code", "voix : {} a rendu {}{}".format(
                    command[0], code, " - " + first if first else ""))

    def _once(self, key, message) -> None:
        """La meme panne ne s'ecrit qu'une fois. Voir en tete de module."""
        if key in self._said:
            return
        self._said.add(key)
        try:
            self.on_log(message)
        except Exception:
            pass
