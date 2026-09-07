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
#
# Le vocabulaire du football sert de socle a tous les sports : un but de hockey
# se dit "but", et le hockey ne redit donc que ce qui differe (la mise au jeu,
# les tiers-temps). Le rugby, lui, apporte les siennes - essai, transformation,
# penalite, drop - parce qu'aucune ne se dit "but". Voir sports.py : c'est le
# sport qui aiguille vers la bonne cle, jamais l'appelant.
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
        "title_faceoff": "MISE AU JEU",
        "title_period_break": "FIN DU TIERS-TEMPS",
        "title_period_restart": "REPRISE",
        "title_game_over": "FIN DU MATCH",
        "title_points": "POINTS !",
        "title_points_cancelled": "POINTS RETIRES",
        "title_try": "ESSAI !",
        "title_conversion": "TRANSFORMATION",
        "title_penalty_goal": "PENALITE",
        "title_drop_goal": "DROP",
        "title_pinned": "EN DIRECT",
        "title_catchup": "PENDANT TON ABSENCE",
        "goal": "But",
        "penalty": "Penalty",
        "own_goal": "But contre son camp",
        "red_card": "Carton rouge",
        "try": "Essai",
        "conversion": "Transformation",
        "penalty_goal": "Penalite",
        "drop_goal": "Drop",
        "goal_by": "But de ",
        "penalty_by": "Penalty de ",
        "own_goal_by": "But contre son camp de ",
        "red_card_for": "Carton rouge pour ",
        "try_by": "Essai de ",
        "conversion_by": "Transformation de ",
        "penalty_goal_by": "Penalite de ",
        "drop_goal_by": "Drop de ",
        "cancelled": "Score corrige",
        "minute": "Minute {minute}",
        "points_added": "+{points} points",
        "own_goal_short": "csc",
        "penalty_short": "sp",
        "try_short": "essai",
        "conversion_short": "transf.",
        "penalty_goal_short": "pen.",
        "drop_goal_short": "drop",
        "kickoff_soon": "Coup d'envoi dans moins d'une minute",
        "kickoff_in": "Coup d'envoi dans {minutes} min",
        "catchup_before": "avant {score}",
        "catchup_gap": "{minutes} min",
        "league_ucl": "LIGUE DES CHAMPIONS",
        "league_uel": "LIGUE EUROPA",
        "league_uecl": "LIGUE CONFERENCE",
        "league_usc": "SUPERCOUPE UEFA",
        "league_nations": "LIGUE DES NATIONS",
        "league_wc": "COUPE DU MONDE",
        "league_wcq": "QUALIF. CDM",
        "league_wucl": "LIGUE DES CHAMPIONS F",
        "league_wuel": "COUPE EUROPA F",
        "league_wnations": "LIGUE DES NATIONS F",
        "league_wwc": "COUPE DU MONDE F",
        "league_wwcq": "QUALIF. CDM F",
        "league_six_nations": "TOURNOI DES SIX NATIONS",
        "league_rwc": "COUPE DU MONDE DE RUGBY",
        "league_test_match": "MATCH INTERNATIONAL",
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
        "title_faceoff": "PUCK DROP",
        "title_period_break": "END OF PERIOD",
        "title_period_restart": "NEXT PERIOD",
        "title_game_over": "FINAL",
        "title_points": "POINTS!",
        "title_points_cancelled": "POINTS REMOVED",
        "title_try": "TRY!",
        "title_conversion": "CONVERSION",
        "title_penalty_goal": "PENALTY GOAL",
        "title_drop_goal": "DROP GOAL",
        "title_pinned": "LIVE",
        "title_catchup": "WHILE YOU WERE AWAY",
        "goal": "Goal",
        "penalty": "Penalty",
        "own_goal": "Own goal",
        "red_card": "Red card",
        "try": "Try",
        "conversion": "Conversion",
        "penalty_goal": "Penalty goal",
        "drop_goal": "Drop goal",
        "goal_by": "Goal by ",
        "penalty_by": "Penalty by ",
        "own_goal_by": "Own goal by ",
        "red_card_for": "Red card for ",
        "try_by": "Try by ",
        "conversion_by": "Conversion by ",
        "penalty_goal_by": "Penalty goal by ",
        "drop_goal_by": "Drop goal by ",
        "cancelled": "Score corrected",
        "minute": "Minute {minute}",
        "points_added": "+{points} points",
        "own_goal_short": "og",
        "penalty_short": "pen",
        "try_short": "try",
        "conversion_short": "conv.",
        "penalty_goal_short": "pen.",
        "drop_goal_short": "drop",
        "kickoff_soon": "Kick-off in under a minute",
        "kickoff_in": "Kick-off in {minutes} min",
        "catchup_before": "was {score}",
        "catchup_gap": "{minutes} min",
        "league_ucl": "CHAMPIONS LEAGUE",
        "league_uel": "EUROPA LEAGUE",
        "league_uecl": "CONFERENCE LEAGUE",
        "league_usc": "UEFA SUPER CUP",
        "league_nations": "NATIONS LEAGUE",
        "league_wc": "WORLD CUP",
        "league_wcq": "WC QUALIFYING",
        "league_wucl": "WOMEN'S CHAMPIONS LEAGUE",
        "league_wuel": "WOMEN'S EUROPA CUP",
        "league_wnations": "WOMEN'S NATIONS LEAGUE",
        "league_wwc": "WOMEN'S WORLD CUP",
        "league_wwcq": "WWC QUALIFYING",
        "league_six_nations": "SIX NATIONS",
        "league_rwc": "RUGBY WORLD CUP",
        "league_test_match": "TEST MATCH",
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
        "title_faceoff": "COMIENZA EL PARTIDO",
        "title_period_break": "FIN DEL PERIODO",
        "title_period_restart": "SIGUIENTE PERIODO",
        "title_game_over": "FINAL DEL PARTIDO",
        "title_points": "PUNTOS!",
        "title_points_cancelled": "PUNTOS ANULADOS",
        "title_try": "ENSAYO!",
        "title_conversion": "CONVERSION",
        "title_penalty_goal": "GOLPE DE CASTIGO",
        "title_drop_goal": "DROP",
        "title_pinned": "EN DIRECTO",
        "title_catchup": "MIENTRAS NO ESTABAS",
        "goal": "Gol",
        "penalty": "Penalti",
        "own_goal": "Gol en propia",
        "red_card": "Tarjeta roja",
        "try": "Ensayo",
        "conversion": "Conversion",
        "penalty_goal": "Golpe de castigo",
        "drop_goal": "Drop",
        "goal_by": "Gol de ",
        "penalty_by": "Penalti de ",
        "own_goal_by": "Gol en propia de ",
        "red_card_for": "Tarjeta roja para ",
        "try_by": "Ensayo de ",
        "conversion_by": "Conversion de ",
        "penalty_goal_by": "Golpe de castigo de ",
        "drop_goal_by": "Drop de ",
        "cancelled": "Marcador corregido",
        "minute": "Minuto {minute}",
        "points_added": "+{points} puntos",
        "own_goal_short": "pp",
        "penalty_short": "pen",
        "try_short": "ensayo",
        "conversion_short": "conv.",
        "penalty_goal_short": "castigo",
        "drop_goal_short": "drop",
        "kickoff_soon": "Comienza en menos de un minuto",
        "kickoff_in": "Comienza en {minutes} min",
        "catchup_before": "antes {score}",
        "catchup_gap": "{minutes} min",
        "league_ucl": "LIGA DE CAMPEONES",
        "league_uel": "EUROPA LEAGUE",
        "league_uecl": "CONFERENCE LEAGUE",
        "league_usc": "SUPERCOPA DE EUROPA",
        "league_nations": "LIGA DE NACIONES",
        "league_wc": "COPA DEL MUNDO",
        "league_wcq": "CLASIF. MUNDIAL",
        "league_wucl": "LIGA DE CAMPEONES F",
        "league_wuel": "EUROPA CUP F",
        "league_wnations": "LIGA DE NACIONES F",
        "league_wwc": "COPA DEL MUNDO F",
        "league_wwcq": "CLASIF. MUNDIAL F",
        "league_six_nations": "SEIS NACIONES",
        "league_rwc": "MUNDIAL DE RUGBY",
        "league_test_match": "TEST MATCH",
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
        "title_faceoff": "INIZIO PARTITA",
        "title_period_break": "FINE DEL PERIODO",
        "title_period_restart": "SI RIPARTE",
        "title_game_over": "FINE PARTITA",
        "title_points": "PUNTI!",
        "title_points_cancelled": "PUNTI ANNULLATI",
        "title_try": "META!",
        "title_conversion": "TRASFORMAZIONE",
        "title_penalty_goal": "CALCIO DI PUNIZIONE",
        "title_drop_goal": "DROP",
        "title_pinned": "IN DIRETTA",
        "title_catchup": "MENTRE ERI VIA",
        "goal": "Gol",
        "penalty": "Rigore",
        "own_goal": "Autogol",
        "red_card": "Cartellino rosso",
        "try": "Meta",
        "conversion": "Trasformazione",
        "penalty_goal": "Calcio di punizione",
        "drop_goal": "Drop",
        "goal_by": "Gol di ",
        "penalty_by": "Rigore di ",
        "own_goal_by": "Autogol di ",
        "red_card_for": "Cartellino rosso per ",
        "try_by": "Meta di ",
        "conversion_by": "Trasformazione di ",
        "penalty_goal_by": "Calcio di punizione di ",
        "drop_goal_by": "Drop di ",
        "cancelled": "Punteggio corretto",
        "minute": "Minuto {minute}",
        "points_added": "+{points} punti",
        "own_goal_short": "aut",
        "penalty_short": "rig",
        "try_short": "meta",
        "conversion_short": "trasf.",
        "penalty_goal_short": "pun.",
        "drop_goal_short": "drop",
        "kickoff_soon": "Inizio tra meno di un minuto",
        "kickoff_in": "Inizio tra {minutes} min",
        "catchup_before": "prima {score}",
        "catchup_gap": "{minutes} min",
        "league_ucl": "CHAMPIONS LEAGUE",
        "league_uel": "EUROPA LEAGUE",
        "league_uecl": "CONFERENCE LEAGUE",
        "league_usc": "SUPERCOPPA UEFA",
        "league_nations": "NATIONS LEAGUE",
        "league_wc": "MONDIALI",
        "league_wcq": "QUALIF. MONDIALI",
        "league_wucl": "CHAMPIONS LEAGUE F",
        "league_wuel": "EUROPA CUP F",
        "league_wnations": "NATIONS LEAGUE F",
        "league_wwc": "MONDIALI F",
        "league_wwcq": "QUALIF. MONDIALI F",
        "league_six_nations": "SEI NAZIONI",
        "league_rwc": "COPPA DEL MONDO DI RUGBY",
        "league_test_match": "TEST MATCH",
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
        "title_faceoff": "ANSPIEL",
        "title_period_break": "DRITTELPAUSE",
        "title_period_restart": "ES GEHT WEITER",
        "title_game_over": "SPIELENDE",
        "title_points": "PUNKTE!",
        "title_points_cancelled": "PUNKTE ABERKANNT",
        "title_try": "VERSUCH!",
        "title_conversion": "ERHOEHUNG",
        "title_penalty_goal": "STRAFTRITT",
        "title_drop_goal": "DROPKICK",
        "title_pinned": "LIVE",
        "title_catchup": "IN DEINER ABWESENHEIT",
        "goal": "Tor",
        "penalty": "Elfmeter",
        "own_goal": "Eigentor",
        "red_card": "Rote Karte",
        "try": "Versuch",
        "conversion": "Erhoehung",
        "penalty_goal": "Straftritt",
        "drop_goal": "Dropkick",
        "goal_by": "Tor von ",
        "penalty_by": "Elfmeter von ",
        "own_goal_by": "Eigentor von ",
        "red_card_for": "Rote Karte: ",
        "try_by": "Versuch von ",
        "conversion_by": "Erhoehung von ",
        "penalty_goal_by": "Straftritt von ",
        "drop_goal_by": "Dropkick von ",
        "cancelled": "Spielstand korrigiert",
        "minute": "Minute {minute}",
        "points_added": "+{points} Punkte",
        "own_goal_short": "ET",
        "penalty_short": "E",
        "try_short": "V",
        "conversion_short": "Erh.",
        "penalty_goal_short": "Straf.",
        "drop_goal_short": "Drop",
        "kickoff_soon": "Anpfiff in weniger als einer Minute",
        "kickoff_in": "Anpfiff in {minutes} min",
        "catchup_before": "vorher {score}",
        "catchup_gap": "{minutes} min",
        "league_ucl": "CHAMPIONS LEAGUE",
        "league_uel": "EUROPA LEAGUE",
        "league_uecl": "CONFERENCE LEAGUE",
        "league_usc": "UEFA SUPERCUP",
        "league_nations": "NATIONS LEAGUE",
        "league_wc": "WELTMEISTERSCHAFT",
        "league_wcq": "WM-QUALIFIKATION",
        "league_wucl": "CHAMPIONS LEAGUE F",
        "league_wuel": "EUROPA CUP F",
        "league_wnations": "NATIONS LEAGUE F",
        "league_wwc": "FRAUEN-WM",
        "league_wwcq": "FRAUEN-WM-QUALI",
        "league_six_nations": "SIX NATIONS",
        "league_rwc": "RUGBY-WM",
        "league_test_match": "TESTSPIEL",
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
    """Le code de langue et son nom, ex. "en (anglais)" ou "en (English)".

    Le nom passe par tr() comme le reste de la ligne de commande : afficher
    "en (anglais)" dans une interface anglaise serait cocasse.
    """
    code = language()
    return "{} ({})".format(code, _name(code))


def _name(code) -> str:
    """Le nom d'une langue, traduit.

    Les cinq appels sont ecrits en toutes lettres, et pas tr(NAMES[code]) :
    l'extracteur qui garde les catalogues propres ne lit que des constantes,
    et une cle qu'il ne voit pas, il la declare morte. Un detour qui se paie
    en repetition, mais qui garde le garde-fou utile.
    """
    noms = {
        "fr": tr("francais"),
        "en": tr("anglais"),
        "es": tr("espagnol"),
        "it": tr("italien"),
        "de": tr("allemand"),
    }
    return noms.get(code, code)


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
