"""Le fichier de configuration : ses reglages sans retaper la ligne de commande.

Changer de championnat ou d'equipe suivie ne devrait pas obliger a relancer
l'installeur ni a bidouiller les arguments du raccourci de demarrage. Un
fichier pose a cote du journal (`butbutbut --paths`) suffit :

    [butbutbut]
    leagues = l1,ucl
    teams = om,psg
    position = top-right

Trois etages, dans cet ordre : **ligne de commande > fichier > defauts**. Le
fichier ne fait qu'alimenter les valeurs par defaut du parseur avant l'analyse
(`parser.set_defaults`), donc ce qui est tape a la main l'emporte toujours - y
compris quand ce qui est tape vaut justement le defaut, cas qu'argparse seul ne
saurait pas distinguer d'une option absente.

Rien ici n'est fatal. Un fichier absent est le cas normal et silencieux ; un
fichier illisible, mal forme, ou porteur d'une cle inconnue previent sur la
sortie d'erreur et laisse le programme demarrer sur ses defauts. Un daemon qui
refuse de se lancer coute plus cher qu'une option ignoree.

Le fichier est lu une seule fois, au demarrage : il faut relancer le daemon
pour qu'un changement s'applique. Toute la lecture tient dans `read()`, une
relecture a chaud n'aurait qu'a la rappeler.
"""

from __future__ import annotations

import argparse
import configparser
import textwrap
from pathlib import Path

from . import leagues, screens

SECTION = "butbutbut"
FILENAME = "butbutbut.conf"

COMMENT_WIDTH = 74      # largeur des commentaires du fichier d'exemple

# On accepte les deux langues : le fichier se lit aussi bien qu'il s'ecrit.
TRUE_WORDS = ("1", "true", "yes", "on", "oui", "vrai")
FALSE_WORDS = ("0", "false", "no", "off", "non", "faux")


class Invalid(ValueError):
    """La valeur ecrite ne veut rien dire pour la cle qui la porte."""


# ------------------------------------------------------------- lectures ------

def _text(value):
    return value.strip()


def _integer(value):
    try:
        return int(value.strip())
    except ValueError:
        raise Invalid("attend un nombre entier")


def _number(value):
    # La virgule decimale est ce qu'un clavier francais produit spontanement.
    try:
        return float(value.strip().replace(",", "."))
    except ValueError:
        raise Invalid("attend un nombre")


def _flag(value):
    lowered = value.strip().lower()
    if lowered in TRUE_WORDS:
        return True
    if lowered in FALSE_WORDS:
        return False
    raise Invalid("attend oui ou non (true/false, 1/0 marchent aussi)")


def _corner(value):
    corner = value.strip().lower()
    if corner not in screens.CORNERS:
        raise Invalid("coin inconnu, au choix : {}".format(
            ", ".join(screens.CORNERS)))
    return corner


class Option:
    """Une cle du fichier : comment on la lit, et ce qu'on en dit."""

    __slots__ = ("name", "read", "comment", "sample", "fallback")

    def __init__(self, name, read, comment, sample, fallback=""):
        self.name = name          # cle du fichier = dest argparse
        self.read = read          # texte -> valeur, leve Invalid
        self.comment = comment    # explication, pour le fichier d'exemple
        self.sample = sample      # valeur d'exemple, ecrite commentee
        # Ce qu'on affiche comme defaut quand le parseur repond None, qui ne
        # dit rien a personne ("defaut : les 5 grands" plutot que "defaut : None").
        self.fallback = fallback


# L'ordre est celui du fichier d'exemple : d'abord quoi suivre, puis ou et
# comment l'afficher. Les noms sont ceux des options longues, sans les tirets.
OPTIONS = (
    Option("leagues", _text,
           "Competitions suivies, separees par des virgules. 'big5' prend les "
           "cinq grands championnats, 'all' tout le catalogue, et un code ESPN "
           "(por.1) marche aussi. 'butbutbut --list' donne les noms acceptes.",
           "l1,pl,ucl", fallback="les 5 grands championnats"),
    Option("exclude", _text,
           "Competitions a retirer de la selection, meme syntaxe.",
           "liga,seriea", fallback="rien"),
    Option("teams", _text,
           "Ne signaler que les matchs de ces equipes, separees par des "
           "virgules. Un match compte des qu'une des deux equipes y est.",
           "om,psg", fallback="toutes les equipes"),
    Option("exclude_teams", _text,
           "Ne rien signaler des matchs de ces equipes.",
           "psg", fallback="aucune"),
    Option("pin", _text,
           "Garder a l'ecran une carte qui suit les matchs de cette equipe : "
           "elle apparait au coup d'envoi, se met a jour a chaque releve et "
           "s'en va quelques minutes apres la fin. Une seule equipe, et une "
           "seule carte epinglee.",
    Option("spoiler_free", _text,
           "Equipes regardees en differe : aucune carte ni aucun son pour "
           "leurs matchs, quel que soit l'evenement. Le journal garde tout, "
           "et 'butbutbut --today' le raconte une fois le match vu.",
           "om", fallback="aucune"),
    Option("position", _corner,
           "Coin ou les cartes s'empilent : {}.".format(
               ", ".join(screens.CORNERS)),
           "bottom-right"),
    Option("screen", _text,
           "Ecran d'affichage : 'primary' ou un index (0, 1, 2...). "
           "'butbutbut --screens' les enumere.",
           "1", fallback="l'ecran principal"),
    Option("interval", _integer,
           "Secondes entre deux releves quand un match est en cours. En "
           "dessous de 5, c'est 5.",
           "25"),
    Option("idle_interval", _integer,
           "Secondes entre deux releves quand il n'y a rien a suivre.",
           "300"),
    Option("duration", _number,
           "Secondes d'affichage d'une carte.",
           "8", fallback="la duree du son"),
    Option("scale", _number,
           "Taille des cartes : 1.5 pour les voir de loin.",
           "1.0"),
    Option("opacity", _number,
           "Opacite des cartes, de 0.0 a 1.0.",
           "1.0"),
    Option("volume", _number,
           "Volume de la corne synthetisee, de 0.0 a 1.0. Sans effet sur un "
           "son depose dans le dossier 'sound'.",
           "0.55"),
    Option("no_sound", _flag,
           "Mode muet : oui pour ne plus rien entendre.",
           "non"),
    Option("no_overlay", _flag,
           "Pas de carte du tout : oui pour ne garder que le son et le journal.",
           "non"),
    Option("no_phase_cards", _flag,
           "Pas de carte au coup d'envoi, a la mi-temps, a la reprise ni a la "
           "fin du match : oui pour ne voir que les buts.",
           "non"),
    Option("red_cards", _flag,
           "Signaler aussi les cartons rouges, par une carte discrete et sans "
           "son.",
           "non"),
    Option("before_kickoff", _integer,
           "Annoncer un match ce nombre de minutes avant le coup d'envoi, une "
           "seule fois et sans son. 0 desactive l'annonce.",
           "5", fallback="desactive"),
    Option("catch_up", _flag,
           "Au reveil apres une veille, resumer en UNE carte muette les buts "
           "tombes pendant l'absence. Non : le reveil reste silencieux, comme "
           "avant.",
           "oui"),
    Option("no_logos", _flag,
           "Pas d'ecusson sur les cartes, et rien de telecharge. Les couleurs "
           "des clubs, elles, restent.",
           "non"),
    Option("retry_fullscreen", _number,
           "Quand une application en plein ecran masque l'ecran, repasser la "
           "carte des que l'ecran se libere, pendant ce nombre de secondes au "
           "plus. 0 desactive. Windows uniquement.",
           "120", fallback="desactive"),
    Option("lang", _text,
           "Langue des cartes : fr, en, es, it, de. Par defaut celle du "
           "systeme, et le francais si elle n'est pas des cinq.",
           "de", fallback="la langue du systeme"),
    Option("quiet", _flag,
           "Silence dans le terminal : oui pour n'ecrire que dans le journal.",
           "non"),
)

BY_NAME = {option.name: option for option in OPTIONS}


# ------------------------------------------------------------- lecture -------

class Outcome:
    """Ce qu'une lecture a donne : les valeurs retenues, et ce qu'on a a redire."""

    __slots__ = ("path", "found", "values", "warnings")

    def __init__(self, path, found=False, values=None, warnings=None):
        self.path = Path(path)
        self.found = found        # le fichier existe, meme s'il etait illisible
        self.values = values if values is not None else {}
        self.warnings = warnings if warnings is not None else []


def read(path) -> Outcome:
    """Lit le fichier et rend ce qui en sort, sans jamais lever ni afficher."""
    outcome = Outcome(path)

    try:
        raw = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return outcome                  # le cas normal : pas de fichier, pas de bruit
    except (OSError, ValueError) as exc:
        # Dossier a la place d'un fichier, droits refuses, octets qui ne sont
        # pas de l'utf-8 : on le dit, on demarre quand meme.
        outcome.warnings.append(
            "fichier de configuration illisible ({}) : {}".format(path, exc))
        return outcome

    outcome.found = True

    # interpolation=None : un '%' dans un nom d'equipe n'est pas une syntaxe.
    reader = configparser.ConfigParser(interpolation=None)
    try:
        reader.read_string(raw, source=str(path))
    except configparser.Error as exc:
        outcome.warnings.append(
            "fichier de configuration ignore ({}) : {}".format(
                path, " ".join(str(exc).split())))
        return outcome

    if not reader.has_section(SECTION):
        outcome.warnings.append(
            "fichier de configuration sans section [{}] ({}) : rien n'a ete "
            "lu.".format(SECTION, path))
        return outcome

    for key, value in reader.items(SECTION):
        # Les tirets de la ligne de commande sont un reflexe : on les accepte.
        name = key.strip().lower().replace("-", "_")
        option = BY_NAME.get(name)
        if option is None:
            outcome.warnings.append(
                "cle inconnue dans {} : {!r} (ignoree).".format(path, key))
            continue
        if not value.strip():
            continue                    # une cle vide vaut une cle absente
        try:
            outcome.values[name] = option.read(value)
        except Invalid as exc:
            outcome.warnings.append("{} = {!r} dans {} : {} (cle ignoree).".format(
                key, value.strip(), path, exc))

    _check_leagues(outcome)
    return outcome


def _check_leagues(outcome) -> None:
    """Une competition inconnue dans le fichier ne doit pas tuer le demarrage.

    Sur la ligne de commande une faute de frappe rend 2 tout de suite : celui
    qui tape est devant son terminal. Le fichier, lui, est relu par un daemon
    lance au demarrage de la machine, souvent sans personne pour lire l'erreur.
    """
    picked = outcome.values.get("leagues")
    dropped = outcome.values.get("exclude")
    if picked is None and dropped is None:
        return
    try:
        leagues.resolve(picked, dropped)
    except leagues.SelectionError as exc:
        outcome.warnings.append(
            "leagues/exclude ignores dans {} : {}".format(outcome.path, exc))
        outcome.values.pop("leagues", None)
        outcome.values.pop("exclude", None)


def apply(parser, path) -> Outcome:
    """Verse le fichier dans les defauts du parseur, avant toute analyse.

    C'est tout le secret de la precedence : argparse ne sait pas dire une
    option absente d'une option passee a sa valeur par defaut, mais il sait
    qu'une option passee ecrase le defaut. On deplace donc le fichier du cote
    des defauts, et la ligne de commande gagne mecaniquement.
    """
    outcome = read(path)
    if outcome.values:
        parser.set_defaults(**outcome.values)
    return outcome


class _Silent(argparse.ArgumentParser):
    """Un parseur muet : le vrai, ensuite, dira proprement ce qui cloche."""

    def error(self, message):
        raise ValueError(message)


def path_from(argv, default) -> Path:
    """Le fichier a lire : --config s'il est passe, sinon celui du dossier.

    Il faut connaitre --config avant d'analyser le reste, puisque le reste
    depend de ce que le fichier propose : d'ou ce mini-parseur, qui ignore tout
    le reste de la ligne de commande.
    """
    pre = _Silent(add_help=False)
    pre.add_argument("--config", default=None)
    try:
        known, _rest = pre.parse_known_args(argv)
    except (ValueError, SystemExit):
        return Path(default)
    return Path(known.config) if known.config else Path(default)


def lang_from(argv, path):
    """La langue a appliquer avant meme de construire le parseur, ou None.

    Meme precedence que partout ailleurs -- la ligne de commande d'abord, le
    fichier ensuite -- mais lue en avance. Les textes d'aide sont traduits au
    moment ou argparse les recoit : les fixer apres l'analyse, quand --lang est
    enfin connu, laisserait --help en francais quoi qu'on demande.
    """
    pre = _Silent(add_help=False)
    pre.add_argument("--lang", default=None)
    try:
        known, _rest = pre.parse_known_args(argv)
    except (ValueError, SystemExit):
        known = None
    if known is not None and known.lang:
        return known.lang
    # Les avertissements de lecture ne sont pas emis ici : apply() relit le
    # fichier juste apres et les dira une fois, dans la bonne langue.
    return read(path).values.get("lang")

# ------------------------------------------------------------- ecriture ------

def _wrap(text) -> list:
    return ["# " + line for line in textwrap.wrap(
        text, COMMENT_WIDTH, break_on_hyphens=False, break_long_words=False)]


def _default_text(parser, option) -> str:
    """Le defaut tel qu'on l'annonce dans le fichier d'exemple."""
    value = parser.get_default(option.name)
    if value is True:
        return "oui"
    if value is False:
        return "non"
    if value is None or value == "":
        return option.fallback or "aucun"
    return str(value)


def example(parser) -> str:
    """Le fichier d'exemple : toutes les cles, expliquees et commentees."""
    lines = [
        "# Configuration de butbutbut.",
        "#",
        "# Toutes les cles sont commentees : enleve le '#' devant celles que tu",
        "# veux. Une cle absente garde sa valeur par defaut.",
        "#",
        "# Les arguments de la ligne de commande gardent la priorite sur ce",
        "# fichier. Il n'est lu qu'au demarrage : apres une modification,",
        "# relance le daemon (butbutbut --stop, puis butbutbut).",
        "",
        "[{}]".format(SECTION),
    ]
    for option in OPTIONS:
        lines.append("")
        lines.extend(_wrap(option.comment))
        lines.append("# defaut : {}".format(_default_text(parser, option)))
        lines.append("# {} = {}".format(option.name, option.sample))
    return "\n".join(lines) + "\n"


def write_example(path, parser, force: bool = False):
    """Ecrit le fichier d'exemple. Rend (ecrit ?, message a afficher).

    On n'ecrase jamais un fichier existant sans le dire : il contient les
    reglages de quelqu'un.
    """
    path = Path(path)
    if path.exists() and not force:
        return False, ("{} existe deja, rien n'a ete ecrit. Efface-le, ou "
                       "vise un autre chemin avec --config.".format(path))
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(example(parser), encoding="utf-8")
    except OSError as exc:
        return False, "impossible d'ecrire {} : {}".format(path, exc)
    return True, "fichier de configuration ecrit -> {}".format(path)
