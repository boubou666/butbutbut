"""Ne pas deranger : le seul endroit qui repond "est-ce le moment ?".

Trois choses peuvent rendre une carte importune, et ce sont trois formes de la
meme question :

  - **l'heure** : personne ne veut d'une carte a 2 h du matin (`--quiet-hours`) ;
  - **le regard des autres** : l'ecran est duplique, on presente
    (`--quiet-while-presenting`, voir presenting.py) ;
  - **ce qui est deja affiche** : un jeu en plein ecran masque la carte
    (voir fullscreen.py).

Les deux premieres se posent ici, et rendent le meme verdict : rien a l'ecran,
rien au haut-parleur. La troisieme est restee dans overlay.Stack.push() parce
que sa reponse, elle, est differente - la carte part quand meme, quitte a
repasser plus tard (`--retry-fullscreen`). C'est le sens du doute qui change :
une detection de plein ecran qui se trompe ferait manquer un but pour rien,
alors qu'a 2 h du matin, ou pendant une presentation, se tromper dans l'autre
sens coute bien plus cher.

**Le journal, lui, ne depend jamais de la reponse.** C'est tout le contrat : le
but tombe dans le journal comme n'importe quel autre soir, et
`butbutbut --today` le raconte au reveil. On ne coupe que l'alerte, comme le
mode sans spoiler (teams.py) - a une difference pres, tranchee dans cli.py : le
crochet `--on-goal` continue de partir. Le silence protege CET ecran et CE
haut-parleur ; une commande qui allume une guirlande ou pousse une notification
sur un telephone n'a aucune raison de se taire parce que la machine, elle, dort.

La plage se lit sur l'horloge de la machine, jamais en UTC : "23:00-08:00" veut
dire ce qu'il veut dire pour celui qui l'ecrit, ou qu'il soit. Elle peut
enjamber minuit - c'est meme le cas courant - et sa borne de debut est incluse,
celle de fin exclue : a 23:00 pile on se tait, a 08:00 pile on parle. Il faut
trancher quelque part, et c'est ainsi qu'on lit un horaire ("de 23 h a 8 h" ne
compte pas 8 h).
"""

from __future__ import annotations

import re
from datetime import datetime

from . import presenting

DAY = 24 * 60
FORMAT = "HH:MM-HH:MM"
EXAMPLE = "23:00-08:00"

# "23:00", "23h00", "23h" et "23" designent tous la meme heure, et c'est ce que
# les gens tapent vraiment. Aucune de ces formes n'est ambigue, donc aucune
# raison d'en refuser une pour la beaute du format.
_MOMENT = re.compile(r"^(\d{1,2})\s*(?:[:h.]\s*(\d{1,2}))?\s*h?$")


class Invalid(ValueError):
    """La plage ecrite ne veut rien dire."""


# ------------------------------------------------------------- lecture -------

def clock(minutes) -> str:
    """Des minutes depuis minuit, ecrites comme une horloge : 480 -> "08:00"."""
    total = int(minutes) % DAY
    return "{:02d}:{:02d}".format(total // 60, total % 60)


def minutes_of(moment) -> int:
    """Le moment de la journee, en minutes depuis minuit.

    Accepte un datetime (le cas normal) ou deja des minutes (les tests, et le
    code qui a fait le calcul lui-meme).
    """
    if isinstance(moment, datetime):
        return moment.hour * 60 + moment.minute
    return int(moment) % DAY


def _moment(text) -> int:
    found = _MOMENT.match(str(text).strip().lower())
    if found is None:
        raise Invalid("heure illisible : {!r} (attendu {}, par exemple {})"
                      .format(str(text).strip(), FORMAT, EXAMPLE))
    hour = int(found.group(1))
    minute = int(found.group(2) or 0)
    if hour > 23 or minute > 59:
        raise Invalid("heure impossible : {!r} (attendu {}, par exemple {})"
                      .format(str(text).strip(), FORMAT, EXAMPLE))
    return hour * 60 + minute


def parse(text):
    """Lit "23:00-08:00" et rend une plage, ou None si le texte est vide.

    Leve Invalid en nommant le format attendu : une plage horaire mal ecrite se
    corrige en deux secondes quand on sait a quoi elle devrait ressembler, et
    en dix minutes quand le message dit seulement "valeur invalide".
    """
    raw = str(text or "").strip()
    if not raw:
        return None

    parts = raw.split("-")
    if len(parts) != 2:
        raise Invalid("plage horaire illisible : {!r} (attendu {}, par exemple "
                      "{})".format(raw, FORMAT, EXAMPLE))

    start, end = _moment(parts[0]), _moment(parts[1])
    if start == end:
        # Ni "tout le temps" ni "jamais" ne se devinent : les deux lectures se
        # defendent, donc aucune ne peut etre choisie a la place de quelqu'un.
        raise Invalid("plage horaire vide : {!r} commence et finit a la meme "
                      "heure (attendu {}, par exemple {})".format(
                          raw, FORMAT, EXAMPLE))
    return Hours(start, end)


def normalize(text) -> str:
    """La plage telle qu'on la reecrit : "23h-8h" devient "23:00-08:00".

    Le texte normalise est ce qu'on garde du debut a la fin - dans `args`, dans
    le fichier de configuration relu, dans `--status`. Un seul format affiche
    evite d'avoir a se demander si "23h" et "23:00" sont bien la meme chose.
    """
    window = parse(text)
    return window.describe() if window is not None else ""


class Hours:
    """Une plage horaire de la journee, en minutes depuis minuit."""

    __slots__ = ("start", "end")

    def __init__(self, start, end):
        self.start = int(start) % DAY
        self.end = int(end) % DAY

    @property
    def wraps(self) -> bool:
        """Vrai si la plage enjambe minuit - c'est-a-dire le cas courant."""
        return self.end < self.start

    def covers(self, moment) -> bool:
        """Vrai si `moment` tombe dans la plage. Debut inclus, fin exclue."""
        value = minutes_of(moment)
        if self.wraps:
            return value >= self.start or value < self.end
        return self.start <= value < self.end

    def ends_at(self) -> str:
        return clock(self.end)

    def describe(self) -> str:
        return "{}-{}".format(clock(self.start), clock(self.end))

    def __repr__(self):
        return "<Hours {}>".format(self.describe())


# ------------------------------------------------------------- verdict -------

class Silence:
    """Le verdict, et le seul objet qui le rende.

    `reason()` donne la raison de se taire, en francais et prete a partir au
    journal, ou None quand on peut parler. Elle ne leve jamais : une detection
    qui echoue laisse passer la carte, comme partout ailleurs ici.
    """

    __slots__ = ("hours", "while_presenting", "on_log", "_clock", "_said",
                 "_blind")

    def __init__(self, hours=None, while_presenting=False, on_log=None,
                 clock=None):
        self.hours = hours if isinstance(hours, Hours) else parse(hours)
        self.while_presenting = bool(while_presenting)
        self.on_log = on_log
        # L'horloge est injectable : sans ca, un test de plage horaire ne
        # dirait pas la meme chose selon l'heure a laquelle la suite tourne.
        self._clock = clock or datetime.now
        self._said = None       # la derniere raison journalisee
        self._blind = False     # detection muette : on le dit une fois

    @property
    def armed(self) -> bool:
        """Vrai si quelque chose peut faire taire les cartes."""
        return self.hours is not None or self.while_presenting

    def reason(self, now=None):
        """La raison de se taire en ce moment, ou None.

        Journalise les changements d'etat, et eux seuls : un daemon qui repete
        "en veille" toutes les 25 secondes noierait ses buts, et un silence
        jamais explique passerait pour une panne.
        """
        found = self.verdict(now)
        if found != self._said:
            self._log("silence : {}".format(found) if found else
                      "fin du silence : les cartes et le son repassent")
            self._said = found
        return found

    def verdict(self, now=None):
        """Le meme calcul, sans rien ecrire au journal : pour --status."""
        if self.hours is not None:
            moment = now if now is not None else self._clock()
            if self.hours.covers(moment):
                return "en veille jusqu'a {}".format(self.hours.ends_at())
        if self.while_presenting:
            found = presenting.state()
            if found is None:
                self._blind_once()
                return None
            return presenting.reason_for(found)
        return None

    def describe(self) -> str:
        """Ce qu'on en dit a `--status` et au journal, en une ligne."""
        parts = []
        if self.hours is not None:
            parts.append("plage {}".format(self.hours.describe()))
        if self.while_presenting:
            parts.append("presentation ou ecran duplique"
                         if presenting.supported() else
                         "presentation (non detectable sur cette plateforme)")
        if not parts:
            return "aucun (voir --quiet-hours)"
        parts.append(self.verdict() or "rien en ce moment")
        return " - ".join(parts)

    # ------------------------------------------------------------ interne ----

    def _blind_once(self) -> None:
        """La detection n'a pas repondu : une ligne, pas une par releve.

        Un daemon tourne des heures ; une detection cassee ecrirait autant de
        lignes que de releves et rendrait le journal illisible le jour ou on en
        aurait justement besoin.
        """
        if self._blind:
            return
        self._blind = True
        self._log("presentation non detectable sur cette plateforme : les "
                  "cartes passent comme d'habitude" if not presenting.supported()
                  else "le systeme n'a pas repondu sur l'etat de presentation :"
                       " les cartes passent comme d'habitude")

    def _log(self, message: str) -> None:
        if self.on_log is None:
            return
        try:
            self.on_log(message)
        except Exception:
            pass
