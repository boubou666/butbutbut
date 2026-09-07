"""Le crochet : une commande a soi, lancee a chaque but.

    butbutbut --on-goal 'curl -s -X POST -d "$BUT_TEXT" https://exemple/hook'

L'idee n'est pas d'ecrire dans butbutbut les dix integrations que dix personnes
voudraient - guirlande connectee, webhook Discord, domotique, compteur perso -
mais de leur donner de quoi les ecrire elles-memes. Le programme ne sait rien
de ce qu'il lance, et c'est le but.

Trois regles tiennent tout :

  - **les donnees du but passent par l'environnement, jamais par la commande.**
    Un nom d'equipe n'est donc jamais recolle dans une ligne de shell, et le
    jour ou la source annoncera un club nomme `; rm -rf ~`, il ne se passera
    rien. C'est aussi ce qui rend `shell=True` acceptable ici : la commande
    vient de l'utilisateur, seules les valeurs viennent du reseau, et elles
    restent des valeurs ;
  - **le but n'attend jamais la commande.** Elle part dans un fil a part et
    personne ne guette sa fin : un script lent ne doit retarder ni la carte
    suivante, ni le releve suivant ;
  - **elle ne peut pas faire echouer butbutbut.** Commande introuvable, code de
    sortie non nul, script qui ne rend jamais la main : une ligne de journal,
    et la vie continue. Une reussite, elle, ne dit rien du tout - un crochet
    qui part a chaque but n'a pas a remplir le journal.

Le crochet part sur un but **et sur son retrait par la VAR** : annoncer un but
puis se taire quand il est refuse, ce serait mentir a ce qu'on alimente.
`BUT_TYPE` distingue les deux en un mot, un script qui n'en veut qu'un le
filtre en une ligne. Les temps forts du match, les expulsions et les annonces
d'avant match, eux, ne declenchent rien : l'option promet un but.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading

from . import watcher

PREFIX = "BUT_"
DEFAULT_TIMEOUT = 30.0      # secondes avant de tuer une commande qui s'eternise
MAX_INFLIGHT = 8            # commandes simultanees, au-dela on refuse
OUTPUT_LIMIT = 120          # signes de sortie repris dans le journal

# Sous Windows, sans ca, une console noire clignote a l'ecran a chaque but.
CREATE_NO_WINDOW = 0x08000000

# Ce qui declenche la commande. Voir le pourquoi en tete de module.
FIRES_ON = (watcher.GOAL, watcher.CANCELLED)


class Timeout(RuntimeError):
    """La commande ne rendait pas la main : on l'a tuee."""


# ---------------------------------------------------------- environnement ----

def _flag(value) -> str:
    """Un booleen tel qu'un script le lit : "1" ou "0", jamais "True"."""
    return "1" if value else "0"


def phrase(title, league, score_line, detail="", minute="") -> str:
    """La phrase toute faite, dans la langue des cartes.

    C'est ce qu'on poste - ou ce qu'on dit a voix haute avec `--speak` - sans
    rien avoir a rassembler soi-meme :
    "BUT ! [Ligue 1] Marseille 2 - 1 Paris FC - But de M. Greenwood (67')".

    Elle prend ses morceaux plutot qu'un evenement parce qu'une carte de demo
    (`--test --speak`) n'en est pas un et merite pourtant la meme phrase : il
    n'y a **qu'une** formulation dans le programme, et c'est celle-ci.
    """
    line = "{} [{}] {}".format(title, league, score_line)
    if detail:
        line += " - " + detail
    if minute:
        line += " (" + minute + ")"
    return line


def phrase_of(event) -> str:
    """La meme phrase, pour un evenement du watcher."""
    return phrase(event.title, event.league.name, event.score_line,
                  event.detail_line(), event.minute)


def environment(event) -> dict:
    """Ce que la commande recevra : rien que des chaines, toutes en BUT_.

    C'est le **contrat public** du crochet : ces noms partent vivre dans des
    scripts qui ne sont pas dans ce depot, ils ne bougeront plus. Ils sont en
    anglais alors que le reste du programme parle francais, parce qu'un script
    se partage entre les cinq langues des cartes - contrairement au journal,
    qui reste francais parce que c'est `--today` qui le relit.
    """
    play = event.play
    return {
        PREFIX + "TYPE": event.kind,                        # goal | cancelled
        PREFIX + "LEAGUE": event.league.name,               # Ligue 1
        PREFIX + "LEAGUE_CODE": event.league.slug,          # fra.1
        PREFIX + "HOME": event.match.home,
        PREFIX + "AWAY": event.match.away,
        PREFIX + "HOME_SCORE": str(event.home_score),
        PREFIX + "AWAY_SCORE": str(event.away_score),
        PREFIX + "SCORE": "{} - {}".format(event.home_score, event.away_score),
        PREFIX + "TEAM": event.team or "",                  # l'equipe concernee
        PREFIX + "OPPONENT": event.opponent or "",
        PREFIX + "SIDE": event.side or "",                  # home | away
        PREFIX + "SCORER": (play.scorer if play else "") or "",
        PREFIX + "MINUTE": event.minute or "",
        PREFIX + "OWN_GOAL": _flag(play is not None and play.own_goal),
        PREFIX + "PENALTY": _flag(play is not None and play.penalty),
        PREFIX + "DELTA": str(event.delta),                 # +1, -1, +2...
        PREFIX + "TEXT": phrase_of(event),
    }


def demo() -> dict:
    """Le meme environnement, sur un but fabrique : pour `--test-hook`.

    Regler un crochet en attendant qu'un vrai but tombe serait une boucle de
    mise au point d'une demi-journee. Les cles sont epinglees par les tests
    contre celles d'`environment()`, elles ne peuvent pas se desynchroniser.
    """
    return {
        PREFIX + "TYPE": watcher.GOAL,
        PREFIX + "LEAGUE": "Ligue 1",
        PREFIX + "LEAGUE_CODE": "fra.1",
        PREFIX + "HOME": "Marseille",
        PREFIX + "AWAY": "Paris FC",
        PREFIX + "HOME_SCORE": "2",
        PREFIX + "AWAY_SCORE": "1",
        PREFIX + "SCORE": "2 - 1",
        PREFIX + "TEAM": "Marseille",
        PREFIX + "OPPONENT": "Paris FC",
        PREFIX + "SIDE": "home",
        PREFIX + "SCORER": "M. Greenwood",
        PREFIX + "MINUTE": "67'",
        PREFIX + "OWN_GOAL": "0",
        PREFIX + "PENALTY": "0",
        PREFIX + "DELTA": "1",
        PREFIX + "TEXT": "BUT ! [Ligue 1] Marseille 2 - 1 Paris FC"
                         " - But de M. Greenwood (67')",
    }


def merge(values) -> dict:
    """Nos variables posees sur l'environnement du daemon.

    On repart de celui-ci et non d'un environnement vide : sans PATH, HOME ni
    DISPLAY, la moitie des commandes qu'on voudrait ecrire ne marcheraient pas.
    """
    env = dict(os.environ)
    env.update({key: str(value) for key, value in values.items()})
    return env


# ------------------------------------------------------------- execution -----

def run_command(command, env, timeout):
    """Lance la commande et attend sa fin. Rend (code de sortie, sortie).

    Sortie et erreur sont melangees puis rendues d'un bloc : ca ne sert qu'a
    poser un mot dans le journal quand ca s'est mal passe, ou a montrer ce qui
    s'est dit sous `--test-hook`.
    """
    extra = {}
    if sys.platform == "win32":
        extra["creationflags"] = CREATE_NO_WINDOW
    process = subprocess.Popen(
        command, shell=True, env=env,
        # Sans DEVNULL, une commande qui lit son entree attendrait jusqu'au
        # delai plutot que de rendre la main tout de suite.
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


class Runner:
    """Le crochet de --on-goal : lance la commande sans faire attendre un but.

    Sans commande, l'objet existe quand meme et ne fait rien : le reste du
    programme n'a donc jamais a se demander si le crochet est arme.
    """

    def __init__(self, command, on_log=None, timeout=DEFAULT_TIMEOUT,
                 spawn=None):
        self.command = (command or "").strip()
        self.on_log = on_log or (lambda message: None)
        self.timeout = float(timeout)
        # Injectable : un test n'a aucune raison de lancer un vrai processus.
        self.spawn = spawn or run_command
        self._lock = threading.Lock()
        self._inflight = 0

    def __bool__(self) -> bool:
        return bool(self.command)

    def fire(self, event):
        """Depose le but chez la commande, et rend la main tout de suite.

        Renvoie le fil lance, ou None si rien n'est parti : pas de commande,
        evenement qui ne la concerne pas, ou trop de commandes deja en cours.
        """
        if not self.command or event.kind not in FIRES_ON:
            return None
        with self._lock:
            if self._inflight >= MAX_INFLIGHT:
                # Un script qui ne rend jamais la main ne doit pas finir par
                # tenir un fil par but de la journee.
                self.on_log("crochet : {} commandes deja en cours, celle de ce "
                            "but est abandonnee".format(self._inflight))
                return None
            self._inflight += 1
        thread = threading.Thread(target=self._work, args=(environment(event),),
                                  name="butbutbut-hook", daemon=True)
        thread.start()
        return thread

    def call(self, values):
        """Le meme lancement, mais attendu : `--test-hook` et les tests."""
        return self.spawn(self.command, merge(values), self.timeout)

    def _work(self, values) -> None:
        """Ce que fait le fil : lancer, puis se taire ou noter l'echec."""
        try:
            code, output = self.call(values)
        except Timeout:
            self.on_log("crochet : commande tuee apres {:.0f}s (elle ne rendait "
                        "pas la main)".format(self.timeout))
        except Exception as exc:
            self.on_log("crochet : impossible de lancer la commande ({})".format(exc))
        else:
            if code:
                first = _first_line(output)
                self.on_log("crochet : la commande a rendu {}{}".format(
                    code, " - " + first if first else ""))
        finally:
            with self._lock:
                self._inflight -= 1
