"""La langue des cartes : celle du systeme, avec le francais en dernier recours.

Cinq langues, celles des cinq grands championnats : francais, anglais,
espagnol, italien, allemand. Une competition suivie hors de ces cinq pays
s'affiche dans la langue du systeme quand elle en fait partie, en francais
sinon - ce n'est pas la langue du match qui compte, c'est celle de qui regarde.

L'ordre de decision :

  1. `--lang de`, ou la cle `lang` du fichier de configuration ;
  2. la variable d'environnement `BUTBUTBUT_LANG` ;
  3. la langue du systeme ;
  4. le francais.

Ce qui est traduit : les cartes, et les lignes de journal qui les decrivent.
La ligne de commande (aide, `--status`, `--scores`) reste en francais.

Attention en ecrivant des tests : la langue par defaut depend de la machine.
Un test qui affirme une formulation doit epingler la sienne avec `use("fr")`,
sinon il passera ici et echouera sur une machine anglaise.
"""

from __future__ import annotations

import os
import sys

FALLBACK = "fr"
LANGUAGES = ("fr", "en", "es", "it", "de")

# Le nom de chaque langue, pour `--status` et les messages d'erreur.
NAMES = {
    "fr": "francais",
    "en": "anglais",
    "es": "espagnol",
    "it": "italien",
    "de": "allemand",
}

ENV = "BUTBUTBUT_LANG"

# Les cles portent le sens, pas la formulation : `goal_by` est "But de " en
# francais et "Tor von " en allemand, ou la preposition n'a rien a voir. C'est
# pour ca qu'on ne compose pas `prefix + " de "` : dans plusieurs langues la
# preposition depend de ce qui precede.
MESSAGES = {
    "fr": {
        "title_goal": "BUT !",
        "title_own_goal": "BUT CONTRE SON CAMP",
        "title_penalty": "BUT SUR PENALTY",
        "title_cancelled": "BUT ANNULE",
        "title_kickoff": "COUP D'ENVOI",
        "title_halftime": "MI-TEMPS",
        "title_restart": "REPRISE",
        "title_fulltime": "FIN DU MATCH",
        "title_red_card": "CARTON ROUGE",
        "title_prematch": "LE MATCH VA COMMENCER",
        "goal": "But",
        "penalty": "Penalty",
        "own_goal": "But contre son camp",
        "red_card": "Carton rouge",
        "goal_by": "But de ",
        "penalty_by": "Penalty de ",
        "own_goal_by": "But contre son camp de ",
        "red_card_for": "Carton rouge pour ",
        "cancelled": "Score corrige",
        "minute": "Minute {minute}",
        "own_goal_short": "csc",
        "penalty_short": "sp",
        "kickoff_soon": "Coup d'envoi dans moins d'une minute",
        "kickoff_in": "Coup d'envoi dans {minutes} min",
        "league_ucl": "LIGUE DES CHAMPIONS",
        "league_uel": "LIGUE EUROPA",
        "league_uecl": "LIGUE CONFERENCE",
        "league_usc": "SUPERCOUPE UEFA",
        "league_nations": "LIGUE DES NATIONS",
        "league_wc": "COUPE DU MONDE",
        "league_wcq": "QUALIF. CDM",
    },
    "en": {
        "title_goal": "GOAL!",
        "title_own_goal": "OWN GOAL",
        "title_penalty": "PENALTY GOAL",
        "title_cancelled": "GOAL DISALLOWED",
        "title_kickoff": "KICK-OFF",
        "title_halftime": "HALF-TIME",
        "title_restart": "SECOND HALF",
        "title_fulltime": "FULL-TIME",
        "title_red_card": "RED CARD",
        "title_prematch": "KICKING OFF SOON",
        "goal": "Goal",
        "penalty": "Penalty",
        "own_goal": "Own goal",
        "red_card": "Red card",
        "goal_by": "Goal by ",
        "penalty_by": "Penalty by ",
        "own_goal_by": "Own goal by ",
        "red_card_for": "Red card for ",
        "cancelled": "Score corrected",
        "minute": "Minute {minute}",
        "own_goal_short": "og",
        "penalty_short": "pen",
        "kickoff_soon": "Kick-off in under a minute",
        "kickoff_in": "Kick-off in {minutes} min",
        "league_ucl": "CHAMPIONS LEAGUE",
        "league_uel": "EUROPA LEAGUE",
        "league_uecl": "CONFERENCE LEAGUE",
        "league_usc": "UEFA SUPER CUP",
        "league_nations": "NATIONS LEAGUE",
        "league_wc": "WORLD CUP",
        "league_wcq": "WC QUALIFYING",
    },
    "es": {
        "title_goal": "GOL!",
        "title_own_goal": "GOL EN PROPIA",
        "title_penalty": "GOL DE PENALTI",
        "title_cancelled": "GOL ANULADO",
        "title_kickoff": "COMIENZA EL PARTIDO",
        "title_halftime": "DESCANSO",
        "title_restart": "SEGUNDA PARTE",
        "title_fulltime": "FINAL DEL PARTIDO",
        "title_red_card": "TARJETA ROJA",
        "title_prematch": "EL PARTIDO VA A EMPEZAR",
        "goal": "Gol",
        "penalty": "Penalti",
        "own_goal": "Gol en propia",
        "red_card": "Tarjeta roja",
        "goal_by": "Gol de ",
        "penalty_by": "Penalti de ",
        "own_goal_by": "Gol en propia de ",
        "red_card_for": "Tarjeta roja para ",
        "cancelled": "Marcador corregido",
        "minute": "Minuto {minute}",
        "own_goal_short": "pp",
        "penalty_short": "pen",
        "kickoff_soon": "Comienza en menos de un minuto",
        "kickoff_in": "Comienza en {minutes} min",
        "league_ucl": "LIGA DE CAMPEONES",
        "league_uel": "EUROPA LEAGUE",
        "league_uecl": "CONFERENCE LEAGUE",
        "league_usc": "SUPERCOPA DE EUROPA",
        "league_nations": "LIGA DE NACIONES",
        "league_wc": "COPA DEL MUNDO",
        "league_wcq": "CLASIF. MUNDIAL",
    },
    "it": {
        "title_goal": "GOL!",
        "title_own_goal": "AUTOGOL",
        "title_penalty": "GOL SU RIGORE",
        "title_cancelled": "GOL ANNULLATO",
        "title_kickoff": "FISCHIO D'INIZIO",
        "title_halftime": "INTERVALLO",
        "title_restart": "SECONDO TEMPO",
        "title_fulltime": "FINE PARTITA",
        "title_red_card": "CARTELLINO ROSSO",
        "title_prematch": "LA PARTITA STA PER INIZIARE",
        "goal": "Gol",
        "penalty": "Rigore",
        "own_goal": "Autogol",
        "red_card": "Cartellino rosso",
        "goal_by": "Gol di ",
        "penalty_by": "Rigore di ",
        "own_goal_by": "Autogol di ",
        "red_card_for": "Cartellino rosso per ",
        "cancelled": "Punteggio corretto",
        "minute": "Minuto {minute}",
        "own_goal_short": "aut",
        "penalty_short": "rig",
        "kickoff_soon": "Inizio tra meno di un minuto",
        "kickoff_in": "Inizio tra {minutes} min",
        "league_ucl": "CHAMPIONS LEAGUE",
        "league_uel": "EUROPA LEAGUE",
        "league_uecl": "CONFERENCE LEAGUE",
        "league_usc": "SUPERCOPPA UEFA",
        "league_nations": "NATIONS LEAGUE",
        "league_wc": "MONDIALI",
        "league_wcq": "QUALIF. MONDIALI",
    },
    "de": {
        "title_goal": "TOR!",
        "title_own_goal": "EIGENTOR",
        "title_penalty": "ELFMETERTOR",
        "title_cancelled": "TOR ABERKANNT",
        "title_kickoff": "ANPFIFF",
        "title_halftime": "HALBZEIT",
        "title_restart": "ZWEITE HALBZEIT",
        "title_fulltime": "ABPFIFF",
        "title_red_card": "ROTE KARTE",
        "title_prematch": "DAS SPIEL BEGINNT BALD",
        "goal": "Tor",
        "penalty": "Elfmeter",
        "own_goal": "Eigentor",
        "red_card": "Rote Karte",
        "goal_by": "Tor von ",
        "penalty_by": "Elfmeter von ",
        "own_goal_by": "Eigentor von ",
        "red_card_for": "Rote Karte: ",
        "cancelled": "Spielstand korrigiert",
        "minute": "Minute {minute}",
        "own_goal_short": "ET",
        "penalty_short": "E",
        "kickoff_soon": "Anpfiff in weniger als einer Minute",
        "kickoff_in": "Anpfiff in {minutes} min",
        "league_ucl": "CHAMPIONS LEAGUE",
        "league_uel": "EUROPA LEAGUE",
        "league_uecl": "CONFERENCE LEAGUE",
        "league_usc": "UEFA SUPERCUP",
        "league_nations": "NATIONS LEAGUE",
        "league_wc": "WELTMEISTERSCHAFT",
        "league_wcq": "WM-QUALIFIKATION",
    },
}


class UnknownLanguage(ValueError):
    """La langue demandee n'est pas parmi les cinq."""


_active = None


# ------------------------------------------------------------- detection -----

def _from_environment():
    """La langue posee dans l'environnement, ou None.

    `BUTBUTBUT_LANG` d'abord, puis les variables POSIX habituelles. On lit
    aussi ces dernieres sous Windows : quelqu'un qui les pose sait ce qu'il
    fait, et c'est le seul levier dans un terminal.
    """
    for name in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        value = os.environ.get(name)
        if value:
            code = normalize(value)
            if code:
                return code
    return None


def _explicit():
    """La langue posee expres dans BUTBUTBUT_LANG, ou None."""
    return normalize(os.environ.get(ENV)) or None


def _from_windows():
    """La langue de Windows, via l'API systeme.

    Deux reponses possibles, et elles ne concordent pas toujours : l'interface (souvent
    l'anglais, c'est la langue de l'ISO installe) et le reglage utilisateur
    (celui que la personne a choisi pour ses formats). On suit la convention de
    Microsoft, qui destine la premiere aux textes d'interface, et on garde la
    seconde en second choix quand l'interface n'est pas des cinq.

    Cette API passe avant LANG et compagnie : sous Windows, un shell comme Git
    Bash pose LANG=en_US quoi qu'il arrive, ce qui rendrait la detection
    aveugle a la langue reelle de la machine.
    """
    try:
        import ctypes
        import locale

        noyau = ctypes.windll.kernel32
        for appel in ("GetUserDefaultUILanguage", "GetUserDefaultLangID"):
            code = normalize(locale.windows_locale.get(getattr(noyau, appel)()))
            if code:
                return code
    except Exception:
        return None
    return None


def _from_locale():
    """Le reglage regional du processus, en dernier ressort.

    On evite locale.getdefaultlocale(), deprecie depuis 3.11.
    """
    try:
        import locale

        current = locale.getlocale(locale.LC_MESSAGES if hasattr(locale, "LC_MESSAGES")
                                   else locale.LC_CTYPE)[0]
        return normalize(current)
    except Exception:
        return None


def normalize(value) -> str:
    """Ramene "fr_FR.UTF-8", "de-DE", "French_France" a un code connu.

    Rend une chaine vide quand la langue n'est pas des cinq : c'est a
    l'appelant de decider du repli, pas a cette fonction de mentir.
    """
    if not value:
        return ""
    text_ = str(value).strip().lower()
    if not text_ or text_ in ("c", "posix"):
        return ""

    # "fr_FR.UTF-8" -> "fr", "de-DE" -> "de"
    code = text_.replace("-", "_").split(".")[0].split("_")[0].strip()
    if code in LANGUAGES:
        return code

    # Windows sait aussi repondre "French_France" sur un locale non traduit.
    for lang, mots in (("fr", ("french", "francais")), ("en", ("english",)),
                       ("es", ("spanish", "espanol", "castellano")),
                       ("it", ("italian", "italiano")),
                       ("de", ("german", "deutsch"))):
        if any(text_.startswith(mot) for mot in mots):
            return lang
    return ""


def detect() -> str:
    """La langue a utiliser sans consigne explicite."""
    sources = [_explicit]
    if sys.platform == "win32":
        sources.append(_from_windows)
    sources += [_from_environment, _from_locale]

    for source in sources:
        code = source()
        if code:
            return code
    return FALLBACK


# ---------------------------------------------------------------- choix ------

def use(lang=None) -> str:
    """Fixe la langue courante. Sans argument, celle du systeme.

    Leve UnknownLanguage si on demande une langue qu'on ne parle pas : mieux
    vaut le dire au demarrage que d'afficher des cartes francaises a quelqu'un
    qui a explicitement demande autre chose.
    """
    global _active

    if lang is None:
        _active = detect()
        return _active

    code = normalize(lang)
    if not code:
        raise UnknownLanguage(
            "langue inconnue : {!r} (connues : {})".format(
                lang, ", ".join(LANGUAGES)))
    _active = code
    return _active


def language() -> str:
    """La langue courante, detectee au premier appel."""
    if _active is None:
        use(None)
    return _active


def describe() -> str:
    code = language()
    return "{} ({})".format(code, NAMES.get(code, code))


# ---------------------------------------------------------------- texte ------

def text(key: str, lang=None, **valeurs) -> str:
    """Le libelle `key`, dans `lang` ou dans la langue courante.

    Une cle absente d'un catalogue retombe sur le francais, et une cle inconnue
    partout rend la cle elle-meme : une carte de but ne doit jamais tomber
    parce qu'il manque une traduction.

    `lang` est explicite plutot que pose dans un etat global le temps d'un
    bloc : le daemon rend ses cartes dans un fil et ecrit son journal dans un
    autre, et une langue basculee globalement contaminerait l'autre fil.
    """
    catalogue = MESSAGES.get(lang or language()) or {}
    modele = catalogue.get(key)
    if modele is None:
        modele = MESSAGES[FALLBACK].get(key, key)
    if not valeurs:
        return modele
    try:
        return modele.format(**valeurs)
    except Exception:
        return modele


def tr(francais: str, *positions, lang=None, **valeurs) -> str:
    """La prose de la ligne de commande, dont le francais est la cle.

    Voir lang/__init__.py pour la raison de ce second mecanisme. Une phrase
    absente du catalogue rend le francais : la ligne de commande reste lisible
    meme a moitie traduite, ce qui vaut mieux qu'un texte manquant.

    Les valeurs se passent comme a str.format(), nommees ou non ; `lang` est
    donc reserve aux mots-cles, sans quoi une valeur positionnelle irait s'y
    perdre - c'est arrive.
    """
    code = lang or language()
    if code == FALLBACK:
        traduit = francais
    else:
        from . import lang as catalogues

        traduit = catalogues.CATALOGUES.get(code, {}).get(francais, francais)
    if not positions and not valeurs:
        return traduit
    try:
        return traduit.format(*positions, **valeurs)
    except Exception:
        # Une accolade perdue dans une traduction ne doit pas faire tomber la
        # commande : on retombe sur le francais, qui a ses trous au complet.
        try:
            return francais.format(*positions, **valeurs)
        except Exception:
            return francais


def all_texts(key: str) -> list:
    """Le libelle dans les cinq langues, sans doublon.

    Sert au relecteur de journal : un fichier peut avoir ete ecrit avant un
    changement de langue, et `--today` doit le relire quand meme.
    """
    vus = []
    for lang in LANGUAGES:
        valeur = MESSAGES[lang].get(key)
        if valeur and valeur not in vus:
            vus.append(valeur)
    return vus
