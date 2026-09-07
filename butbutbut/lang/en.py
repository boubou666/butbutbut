"""Catalogue en : le francais en cle, la traduction en valeur.

Une entree absente rend le francais. Les {accolades} sont des trous a valeur :
elles doivent se retrouver a l'identique dans la traduction, sinon le texte
sortira sans sa donnee.
"""

MESSAGES = {
    # ------------------------------------------------------------ --status --
    # Les etiquettes forment une colonne : le " : " doit rester au meme index
    # que dans le francais, sinon --status part de travers.
    "butbutbut {}": "butbutbut {}",
    "  daemon      : {}": "  daemon      : {}",
    "actif (pid {})": "running (pid {})",
    "arrete": "stopped",
    "  releve      : {}": "  last poll   : {}",
    "                etat laisse par un daemon qui ne tourne plus":
        "                state left by a daemon that is no longer running",
    "                (!) plus rien depuis, alors que la cadence est de {}s : "
    "daemon bloque ou source injoignable ?":
        "                (!) nothing since, though the polling interval is "
        "{}s : daemon stuck or source unreachable?",
    "  en cours    : inconnu (le dernier releve est trop vieux)":
        "  live        : unknown (the last poll is too old)",
    "  en cours    : {}": "  live        : {}",
    "  buts du jour: {}  (le detail : butbutbut --today)":
        "  goals today : {}  (details: butbutbut --today)",
    "  equipes     : {}": "  teams       : {}",
    "  langue      : {}": "  language    : {}",
    "  suivi       : {}": "  watching    : {}",
    "  competitions: {}": "  leagues     : {}",
    "  source      : ESPN scoreboard (public, sans cle)":
        "  source      : ESPN scoreboard (public, no key)",
    "  cadence     : {}s en direct / {}s au repos":
        "  polling     : {}s live / {}s idle",
    "  donnees     : {}": "  data        : {}",
    "  config      : {}{}": "  config      : {}{}",
    "  son         : {}{}": "  sound       : {}{}",
    "  son         : {} ({})": "  sound       : {} ({})",
    "  sons perso  : {}  ({} fichier(s))":
        "  own sounds  : {}  ({} file(s))",
    "  ecussons    : {}": "  crests      : {}",
    "desactives (--no-logos)": "off (--no-logos)",
    "{}  ({} en cache)": "{}  ({} cached)",
    "  ecrans      : {} -> carte en {} sur {}":
        "  screens     : {} -> card at {} on {}",
    "l'ecran principal": "the primary screen",
    "ecran {}": "screen {}",
    "  plein ecran : {}": "  fullscreen  : {}",
    "  journal     : {}": "  log         : {}",
    "  lecteur     : winsound + MCI (integres)":
        "  player      : winsound + MCI (built in)",
    "  lecteur     : {}": "  player      : {}",
    "  affichage   : tkinter OK": "  display     : tkinter OK",
    "  affichage   : tkinter MANQUANT (voir README)":
        "  display     : tkinter MISSING (see README)",
    "OK ({} : {} match(s))": "OK ({}: {} match(es))",
    "ECHEC ({})": "FAILED ({})",

    # ------------------------------------------------------------ --scores --
    "\n{}": "\n{}",
    "{:<16} {}": "{:<16} {}",
    "injoignable ({})": "unreachable ({})",
    "  {} {:>22} {} - {} {:<22} {}": "  {} {:>22} {} - {} {:<22} {}",
    "      {:<22} {}": "      {:<22} {}",
    "\n{} match(s), '>' = en cours.": "\n{} match(es), '>' = live.",

    # ------------------------------------------------------------- --today --
    "butbutbut : buts signales le {:%d/%m/%Y}":
        "butbutbut : goals reported on {:%d/%m/%Y}",
    "\n  (aucun but pour l'instant)": "\n  (no goals yet)",
    "\nJournal : {}": "\nLog: {}",
    "\n{} but(s) dans {} competition(s).": "\n{} goal(s) in {} league(s).",
    "'-' = but retire par la VAR ({}).": "'-' = goal ruled out by VAR ({}).",

    # -------------------------------------------------------------- --list --
    "{}:": "{}:",
    "  {:<30} {:<24} {}": "  {:<30} {:<24} {}",
    "\nExemples :": "\nExamples:",
    "  butbutbut --exclude liga,seriea        (les 5 grands moins deux)":
        "  butbutbut --exclude liga,seriea        (the big five minus two)",
    "  butbutbut --leagues all                (tout le catalogue)":
        "  butbutbut --leagues all                (the whole catalogue)",
    "  butbutbut --leagues por.1              (n'importe quel code ESPN)":
        "  butbutbut --leagues por.1              (any ESPN code)",

    # -------------------------------------------------------- --list-teams --
    "{} - {} equipe(s)": "{} - {} team(s)",
    "  (la source ne publie pas de liste pour cette competition)":
        "  (the source publishes no list for this league)",
    "  {} {:<30} {}": "  {} {:<30} {}",
    "'*' = suivie, '-' = exclue.": "'*' = followed, '-' = excluded.",
    "Exemples :": "Examples:",
    "  {:<16} -> {}{}": "  {:<16} -> {}{}",
    "butbutbut : aucune equipe ne correspond a {} dans {}. "
    "Voir 'butbutbut --list-teams'.":
        "butbutbut : no team matches {} in {}. "
        "See 'butbutbut --list-teams'.",

    # ----------------------------------------------------------- --screens --
    "butbutbut : {} ecran(s) detecte(s)": "butbutbut : {} screen(s) detected",
    "  {}  {:<16} {}x{} a +{}+{}{}": "  {}  {:<16} {}x{} at +{}+{}{}",
    "\nPar defaut la carte s'affiche en bas a droite de l'ecran principal.":
        "\nBy default the card appears at the bottom right of the primary "
        "screen.",
    "La deplacer :  butbutbut --screen 1 --position top-right":
        "To move it:  butbutbut --screen 1 --position top-right",

    # ------------------------------------------- --paths, --test, --update --
    "{:6} {}": "{:6} {}",
    "butbutbut : demo - [{}] {} - {}": "butbutbut : demo - [{}] {} - {}",
    "butbutbut {} - mise a jour": "butbutbut {} - update",
    "butbutbut : daemon {} arrete.": "butbutbut : daemon {} stopped.",
    "butbutbut : impossible d'arreter {} : {}":
        "butbutbut : cannot stop {} : {}",

    # ----------------------------------------------------------- messages --
    "butbutbut : {}": "butbutbut : {}",
    "butbutbut : position inconnue : {} (voir --help)":
        "butbutbut : unknown position: {} (see --help)",
    "butbutbut : dossier de donnees inutilisable : {}":
        "butbutbut : unusable data directory: {}",
    "butbutbut : corne regeneree -> {}":
        "butbutbut : horn regenerated -> {}",

    # -------------------------------------------------------------- --help --
    "affiche N cartes de demonstration puis quitte (defaut 1 ; --test 3 "
    "montre l'empilement)":
        "show N demonstration cards, then quit (default 1 ; --test 3 shows "
        "them stacking)",
    "affiche les matchs du jour dans le terminal puis quitte":
        "show today's matches in the terminal, then quit",
    "affiche l'etat (daemon, dernier releve, matchs en cours, son, ecrans, "
    "connexion)":
        "show the current state (daemon, last poll, live matches, sound, "
        "screens, connection)",
    "recapitule les buts signales aujourd'hui":
        "sum up the goals reported today",
    "arrete le daemon en cours": "stop the running daemon",
    "affiche les chemins utilises": "show the paths in use",
    "liste les ecrans detectes": "list the detected screens",
    "met a jour butbutbut depuis GitHub et rejoue l'installeur":
        "update butbutbut from GitHub and run the installer again",
    "dit si une version plus recente existe, sans rien installer":
        "say whether a newer version exists, without installing anything",
    "avec --update ou --check-update : viser la pointe de la branche "
    "principale au lieu de la derniere release":
        "with --update or --check-update: aim at the tip of the main branch "
        "instead of the latest release",
    "fichier de configuration a lire (defaut : {} dans le dossier de donnees, "
    "voir 'butbutbut --paths')":
        "configuration file to read (default: {} in the data directory, see "
        "'butbutbut --paths')",
    "ecrit un fichier de configuration d'exemple, commente, puis quitte "
    "(n'ecrase rien)":
        "write a commented example configuration file, then quit (never "
        "overwrites anything)",
    "competitions suivies, separees par des virgules (defaut : les 5 grands "
    "championnats). Ex : --leagues l1,pl,ucl ; 'all' pour tout le catalogue ; "
    "un code ESPN marche aussi (por.1)":
        "leagues to follow, comma separated (default: the big five leagues). "
        "E.g. --leagues l1,pl,ucl ; 'all' for the whole catalogue ; an ESPN "
        "code works too (por.1)",
    "competitions a ne pas suivre, meme syntaxe. Ex : --exclude liga,seriea":
        "leagues not to follow, same syntax. E.g. --exclude liga,seriea",
    "liste les competitions surveillables et leurs noms":
        "list the leagues that can be watched, with their names",
    "ne signaler que les matchs de ces equipes, separees par des virgules. "
    "Un match compte des qu'une des deux equipes y est. Ex : --teams om,psg":
        "only report matches involving these teams, comma separated. A match "
        "counts as soon as either side is in the list. E.g. --teams om,psg",
    "ne rien signaler des matchs de ces equipes":
        "report nothing from matches involving these teams",
    "liste les equipes des competitions suivies":
        "list the teams of the leagues being followed",
    "secondes entre deux releves quand un match est en cours (defaut {})":
        "seconds between two polls while a match is live (default {})",
    "secondes entre deux releves quand il n'y a rien a suivre (defaut {})":
        "seconds between two polls when there is nothing to follow "
        "(default {})",
    "duree d'affichage de la carte (defaut : la duree du son, au moins {})":
        "how long the card stays up (default: the length of the sound, at "
        "least {})",
    "coin ou les cartes s'empilent : bottom-right (defaut), bottom-left, "
    "top-right, top-left, center":
        "corner where the cards stack: bottom-right (default), bottom-left, "
        "top-right, top-left, center",
    "ecran d'affichage : 'primary' (defaut) ou un index (0, 1, 2...). "
    "Voir 'butbutbut --screens'.":
        "screen to display on: 'primary' (default) or an index (0, 1, 2...). "
        "See 'butbutbut --screens'.",
    "taille de la carte (1.0 par defaut, 1.5 = plus grande)":
        "card size (1.0 by default, 1.5 = bigger)",
    "opacite, 0.0 a 1.0": "opacity, 0.0 to 1.0",
    "pas de carte : seulement le son et le journal":
        "no card: sound and log only",
    "pas de carte au coup d'envoi, a la mi-temps, a la reprise ni a la fin du "
    "match (les buts, si)":
        "no card at kick-off, half-time, the restart or full-time (goals "
        "still get one)",
    "quand une application en plein ecran masque l'ecran, repasser la carte "
    "des que l'ecran se libere, pendant SECONDES au plus (defaut {:.0f} ; "
    "Windows uniquement, voir README)":
        "when a fullscreen application hides the screen, show the card again "
        "as soon as the screen is free, for SECONDES at most (default "
        "{:.0f} ; Windows only, see README)",
    "signale aussi les cartons rouges, par une carte discrete et sans son":
        "report red cards too, with a discreet card and no sound",
    "annonce le match ce nombre de minutes avant le coup d'envoi, une seule "
    "fois et sans son (0 = desactive, defaut)":
        "announce the match this many minutes before kick-off, once only and "
        "without sound (0 = off, default)",
    "langue des cartes : fr, en, es, it, de (defaut : celle du systeme, "
    "francais a defaut). Le journal, lui, reste toujours en francais.":
        "card language: fr, en, es, it, de (default: the system language, "
        "French otherwise). The log stays in French.",
    "pas d'ecusson sur les cartes, et rien de telecharge (les couleurs des "
    "clubs restent)":
        "no crests on the cards, and nothing downloaded (club colours stay)",
    "mode muet": "mute",
    "volume de la corne synthetisee, 0.0 a 1.0":
        "volume of the synthesised horn, 0.0 to 1.0",
    "regenere la corne synthetisee": "regenerate the synthesised horn",
    "n'ecrit que dans le journal": "write to the log only",
}
