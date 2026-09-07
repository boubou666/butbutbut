"""Catalogue en : le francais en cle, la traduction en valeur.

Une entree absente rend le francais. Les {accolades} sont des trous a valeur :
elles doivent se retrouver a l'identique dans la traduction, sinon le texte
sortira sans sa donnee.

Deux familles de phrases n'ont pas d'entree ici, et c'est voulu :

  - les gabarits purement typographiques ("{:6} {}", "{:<16} {}") n'ont pas un
    mot a traduire ;
  - les phrases que l'anglais laisse telles quelles - le nom du programme, les
    metavariables CODE, DATE et MINUTES, les lignes "daemon", "silence" et
    "sports" - rendraient le francais, c'est-a-dire elles-memes.

Les etiquettes de --status forment une colonne : le deux-points doit rester au
meme caractere qu'en francais, quitte a abreger (last poll, own sounds,
catch-up, named sound). Une etiquette qui remplit ses douze signes le colle,
comme le francais le fait deja ("goals today:").

tests/test_i18n.py verifie tout cela phrase par phrase, et refuse une phrase
nouvelle qui ne serait ni traduite ici ni declaree laissee en francais.
"""

MESSAGES = {
    "tirs au but": "penalty shootout",
    # ------------------------------------------------------------ --status --
    "actif (pid {})": "running (pid {})",
    "arrete": "stopped",
    "  releve      : {}": "  last poll   : {}",
    "aucun pour l'instant": "none yet",
    "aucun (le daemon efface son etat en s'arretant)":
        "none (the daemon clears its state when it stops)",
    "date inconnue": "unknown date",
    "il y a {} s": "{} s ago",
    "il y a {} min": "{} min ago",
    "il y a {} h {:02d}": "{} h {:02d} ago",
    "                etat laisse par un daemon qui ne tourne plus":
        "                state left by a daemon that is no longer running",
    "                (!) plus rien depuis, alors que la cadence est de {}s : "
    "daemon bloque ou source injoignable ?":
        "                (!) nothing since, though the polling interval is "
        "{}s : daemon stuck or source unreachable?",
    "  en cours    : inconnu (le dernier releve est trop vieux)":
        "  live        : unknown (the last poll is too old)",
    "  en cours    : {}": "  live        : {}",
    "{} match(s)": "{} match(es)",
    " sur {} au programme": " of {} scheduled",
    "  buts du jour: {}  (le detail : butbutbut --today)":
        "  goals today : {}  (details: butbutbut --today)",
    "  equipes     : {}": "  teams       : {}",
    "  epinglee    : {}": "  pinned      : {}",
    "{} (etat inconnu : voir la ligne releve)":
        "{} (state unknown: see the last poll line)",
    "{} (aucun match en cours)":
        "{} (no match under way)",
    "  sans spoiler: {}  (journal seulement : ni carte, ni son)":
        "  spoiler-free: {}  (log only: no card, no sound)",
    "  langue      : {}": "  language    : {}",
    "  suivi       : {}": "  watching    : {}",
    "  competitions: {}": "  leagues     : {}",
    "  source      : ESPN scoreboard (public, sans cle)":
        "  source      : ESPN scoreboard (public, no key)",
    "  cadence     : {}s en direct / {}s au repos":
        "  polling     : {}s live / {}s idle",
    "  donnees     : {}": "  data        : {}",
    "  (absent, voir --write-config)": "  (missing, see --write-config)",
    "  crochet     : {}": "  hook        : {}",
    "{}  (essai : --test-hook)": "{}  (try it: --test-hook)",
    "aucun (voir --on-goal)": "none (see --on-goal)",
    "  voix        : {}": "  voice       : {}",
    "  son         : {} fichier(s), le nom dit quand ils jouent":
        "  sound       : {} file(s), the name says when they play",
    "  son         : {} ({})": "  sound       : {} ({})",
    "fourni": "bundled",
    "corne synthetisee": "synthesised horn",
    "  sons perso  : {}  ({} fichier(s))":
        "  own sounds  : {}  ({} file(s))",
    "  son nomme   : {} paire(s), le plus precis l'emporte":
        "  named sound : {} pair(s), the most specific wins",

    # Ce que les deux lignes 'son' de --status affichent a droite : quand un
    # son a soi se declenche, d'apres son nom de fichier ou --sound-for.
    "quand une equipe suivie encaisse": "when a followed team concedes",
    "  (jamais : aucune equipe suivie, voir --teams)":
        "  (never: no team followed, see --teams)",
    "les buts de {}": "goals in {}",
    "  (competition non suivie)": "  (league not followed)",
    "tirage general": "general pool",
    "et {} autre(s)": "and {} more",
    "quand cette equipe marque": "when this team scores",

    "  ecussons    : {}": "  crests      : {}",
    "desactives (--no-logos)": "off (--no-logos)",
    "{}  ({} en cache)": "{}  ({} cached)",
    "  ecrans      : {} -> carte en {} sur {}":
        "  screens     : {} -> card at {} on {}",
    "1 ecran ({}x{})": "1 screen ({}x{})",
    "{} ecrans [{}]": "{} screens [{}]",
    "l'ecran principal": "the primary screen",
    "ecran {}": "screen {}",
    "  rattrapage  : {}": "  catch-up    : {}",
    "actif (une carte de resume au reveil, sans son)":
        "on (a summary card on wake-up, without sound)",
    "inactif (le reveil reste silencieux, voir --catch-up)":
        "off (the wake-up stays silent, see --catch-up)",
    "  plein ecran : {}": "  fullscreen  : {}",
    "detecte (la carte masquee est notee au journal)":
        "detected (a hidden card is noted in the log)",
    "non detectable sur cette plateforme": "not detectable on this platform",
    "  journal     : {}": "  log         : {}",
    "  lecteur     : winsound + MCI (integres)":
        "  player      : winsound + MCI (built in)",
    "  lecteur     : {}": "  player      : {}",
    "AUCUN (installe mpv/ffmpeg/pipewire/alsa-utils)":
        "NONE (install mpv/ffmpeg/pipewire/alsa-utils)",
    "  affichage   : tkinter OK": "  display     : tkinter OK",
    "  affichage   : tkinter MANQUANT (voir README)":
        "  display     : tkinter MISSING (see README)",
    "\n  Connexion   : ": "\n  Connection  : ",
    "OK ({} : {} match(s))": "OK ({}: {} match(es))",
    "ECHEC ({})": "FAILED ({})",

    # ----------------------------------------------------- le suivi decrit --
    # Rendu par leagues.describe(), affiche sur la ligne "suivi" de --status.
    "les 5 grands championnats": "the big five leagues",
    "tout le catalogue ({} competitions)": "the whole catalogue ({} leagues)",
    "tout le football feminin ({} competitions)":
        "all of women's football ({} leagues)",
    # "tout le {} ({} competitions)" n'a pas d'entree : le trou y recoit le nom
    # du sport, que sports.py garde en francais pour le journal. La traduire
    # ferait une phrase a moitie anglaise ; celle-ci, non.
    "tous les sports ({} competitions)": "every sport ({} leagues)",
    "{} et {} autres": "{} and {} others",

    # ------------------------------------------------------------ --scores --
    "injoignable ({})": "unreachable ({})",
    "  (aucun match au programme)": "  (no match scheduled)",
    "  (aucun match de ces equipes)": "  (no match for these teams)",
    "sans spoiler": "spoiler-free",
    # L'etat du match, en bout de ligne, quand la source ne dit rien de mieux.
    "en cours": "live",
    "termine": "finished",
    "a venir": "upcoming",
    "imminent": "kicking off",
    "dans {} min": "in {} min",
    "\n{} match(s), '>' = en cours.": "\n{} match(es), '>' = live.",
    "'?' = sans spoiler : {} match(s) masque(s). Le journal, lui, a tout : "
    "butbutbut --today.":
        "'?' = spoiler-free: {} match(es) hidden. The log has it all: "
        "butbutbut --today.",

    # -------------------------------------------------------------- --next --
    # Une competition qui n'a pas repondu ne fait pas echouer la commande :
    # elle se signale en fin de liste, et le calendrier se dit incomplet.
    "butbutbut : prochains matchs - {}, {} jour(s)":
        "butbutbut : coming matches - {}, {} day(s)",
    "\n{} match(s) a venir dans {} competition(s), sur {} jour(s).":
        "\n{} match(es) coming up in {} league(s), over {} day(s).",
    "\nAucune competition n'a repondu : rien a annoncer.":
        "\nNot one league answered: nothing to announce.",
    "  ({} injoignable : {})": "  ({} unreachable: {})",
    "  (le calendrier ci-dessus est donc incomplet ; les autres competitions "
    "ont repondu)":
        "  (the schedule above is therefore incomplete ; the other leagues "
        "did answer)",

    # ------------------------------------------------------------- --table --
    # Le classement d'une competition, pas un palmares de buteurs : les deux
    # mots se separent dans les langues qui les distinguent.
    "butbutbut : classement - {}": "butbutbut : table - {}",
    "\nAucune competition n'a repondu : rien a classer.":
        "\nNot one league answered: nothing to rank.",
    "  (une coupe se joue en tableau ; hors saison, la source n'a rien a "
    "servir)":
        "  (a cup is played as a bracket ; out of season, the source has "
        "nothing to serve)",
    "  (le classement ci-dessus est donc incomplet ; les autres competitions "
    "ont repondu)":
        "  (the table above is therefore incomplete ; the other leagues did "
        "answer)",

    # -------------------------------------- la fenetre lue dans le journal --
    # Nommee en tete de --today, --stats, --top-scorers et --export : la meme
    # phrase sert aux quatre, d'ou sa place avant elles.
    "date illisible : {!r}. Format attendu : AAAA-MM-JJ, par exemple --since "
    "{}":
        "unreadable date: {!r}. Expected format: YYYY-MM-DD, for example "
        "--since {}",
    "depuis le debut du journal": "since the log begins",
    "le {}": "on {}",
    "du {} au {}": "from {} to {}",

    # ------------------------------------------------------------- --today --
    "butbutbut : buts signales le {:%d/%m/%Y}":
        "butbutbut : goals reported on {:%d/%m/%Y}",
    "butbutbut : buts signales {}": "butbutbut : goals reported {}",
    "\n  (journal vide : aucun but n'y a encore ete ecrit)":
        "\n  (empty log: not one goal has been written to it yet)",
    "\n  (aucun but dans le journal)": "\n  (no goals in the log)",
    "\n  (aucun but pour l'instant)": "\n  (no goals yet)",
    "\n  (aucun but sur cette periode)": "\n  (no goals over that period)",
    "\nJournal : {}": "\nLog: {}",
    "\n{} but(s) dans {} competition(s).": "\n{} goal(s) in {} league(s).",
    "'-' = but retire par la VAR ({}).": "'-' = goal ruled out by VAR ({}).",
    "\n{} but(s) signale(s), {} jour(s), {} competition(s).":
        "\n{} goal(s) reported, {} day(s), {} league(s).",
    "{} = but retire par la VAR ({}) : {} but(s) confirme(s).":
        "{} = goal ruled out by VAR ({}): {} goal(s) confirmed.",

    # ------------------------------------------------------- --top-scorers --
    # Les buts repris par la VAR sont deduits : le compte affiche n'est pas
    # celui des lignes du journal, et la note le dit.
    "butbutbut : buteurs vus passer {}": "butbutbut : scorers seen {}",
    "\n  (aucun buteur connu : la source n'avait pas encore publie l'action)":
        "\n  (no scorer known: the source had not published the play yet)",
    "  ... et {} autre(s) buteur(s) plus bas au classement.":
        "  ... and {} more scorer(s) further down the ranking.",
    "\n{} buteur(s) pour {} but(s) confirme(s) sur {} signale(s).":
        "\n{} scorer(s) for {} goal(s) confirmed out of {} reported.",
    "{} but(s) retire(s) par la VAR, deduit(s) du classement.":
        "{} goal(s) ruled out by VAR, taken off the ranking.",
    "{} annulation(s) sans but a retirer dans cette fenetre (le but est tombe "
    "avant).":
        "{} cancellation(s) with no goal to take off in this window (the goal "
        "fell earlier).",
    "{} but(s) sans buteur connu, hors classement.":
        "{} goal(s) with no known scorer, out of the ranking.",

    # ------------------------------------------------------------- --stats --
    # Les gabarits d'alignement ({:<16} {:>4}) portent la colonne : ils
    # doivent se retrouver a l'identique, largeur comprise.
    "butbutbut : ce que le journal raconte {}":
        "butbutbut : what the log has to say {}",
    "\n  (aucun but debout dans cette fenetre : {} signale(s), {} repris par "
    "la VAR)":
        "\n  (not one goal left standing in this window: {} reported, {} "
        "ruled out by VAR)",
    "\nPar minute de match": "\nBy match minute",
    "  (aucune minute de jeu lisible dans cette fenetre)":
        "  (no readable match minute in this window)",
    "\nPar competition": "\nBy league",
    "  ... et {} autre(s) competition(s) plus bas.":
        "  ... and {} more league(s) further down.",
    "\nLes soirees les plus prolifiques": "\nThe highest-scoring evenings",
    "  {:<16} {:>4} but(s)": "  {:<16} {:>4} goal(s)",
    "  ... et {} autre(s) soiree(s) a {} but(s).":
        "  ... and {} more evening(s) with {} goal(s).",
    "\nNature des buts": "\nKinds of goal",
    "\n{} but(s) confirme(s) sur {} signale(s), dans {} competition(s).":
        "\n{} goal(s) confirmed out of {} reported, in {} league(s).",
    "{} match(s) avec au moins un but signale, {:.1f} but(s) par match.":
        "{} match(es) with at least one goal reported, {:.1f} goal(s) per "
        "match.",
    "Un 0-0 ne laisse aucune trace dans le journal, ni dans cette moyenne.":
        "A 0-0 leaves no trace in the log, nor in that average.",
    "{} but(s) retire(s) par la VAR, deduit(s) de tout ce qui precede.":
        "{} goal(s) ruled out by VAR, taken off everything above.",
    "{} but(s) dans le temps additionnel, comptes dans la tranche de leur "
    "minute.":
        "{} goal(s) in stoppage time, counted in the band of their minute.",
    "{} but(s) sans minute de jeu lisible, hors histogramme.":
        "{} goal(s) with no readable match minute, out of the histogram.",

    # ------------------------------------------------------------ --export --
    # Seules les notes vont sur la sortie d'erreur et se traduisent ; les
    # donnees elles-memes gardent leurs en-tetes anglais, non traduits.
    "{} ligne(s) : {} but(s) signale(s) dont {} debout, {} annulation(s).":
        "{} row(s): {} goal(s) reported, {} of them standing, {} "
        "cancellation(s).",
    "Le champ 'standing' dit lesquels la VAR a repris.":
        "The 'standing' field says which ones VAR took back.",
    "Journal : {}": "Log: {}",
    "butbutbut : export interrompu : {}": "butbutbut : export cut short: {}",

    # -------------------------------------------------------------- --list --
    "butbutbut : competitions surveillables\n":
        "butbutbut : leagues that can be watched\n",
    "Les 5 grands (defaut)": "The big five (default)",
    "Aussi disponibles": "Also available",
    "Hockey sur glace (a demander)": "Ice hockey (on request)",
    "Rugby a XV (a demander)": "Rugby union (on request)",
    "Football feminin (a demander)":
        "Women's football (on request)",
    "\nExemples :": "\nExamples:",
    "  butbutbut --exclude liga,seriea        (les 5 grands moins deux)":
        "  butbutbut --exclude liga,seriea        (the big five minus two)",
    "  butbutbut --leagues all                (tout le catalogue de football)":
        "  butbutbut --leagues all                (the whole football "
        "catalogue)",
    "  butbutbut --leagues nhl,top14          (hockey et rugby, a la demande)":
        "  butbutbut --leagues nhl,top14          (hockey and rugby, on "
        "request)",
    "  butbutbut --leagues rugby              (tout le rugby du catalogue)":
        "  butbutbut --leagues rugby              (all the rugby in the "
        "catalogue)",
    "  butbutbut --leagues all-sports         (vraiment tout)":
        "  butbutbut --leagues all-sports         (really everything)",
    "  butbutbut --leagues feminines          (tout le football feminin)":
        "  butbutbut --leagues feminines          (all the women's football)",
    "  butbutbut --leagues l1f,wsl,uclf       (le meme, au feminin : un f a la fin)":
        "  butbutbut --leagues l1f,wsl,uclf       (the same, women's: an f at the end)",
    "  butbutbut --leagues por.1              (n'importe quel code ESPN)":
        "  butbutbut --leagues por.1              (any ESPN code)",
    "  butbutbut --leagues hockey:nhl         (... y compris dans un autre "
    "sport)":
        "  butbutbut --leagues hockey:nhl         (... including in another "
        "sport)",

    # -------------------------------------------------------- --list-teams --
    "{} - {} equipe(s)": "{} - {} team(s)",
    "  (la source ne publie pas de liste pour cette competition)":
        "  (the source publishes no list for this league)",
    "'*' = suivie, '-' = exclue.": "'*' = followed, '-' = excluded.",
    "'?' = suivie sans spoiler : journal seulement, ni carte ni son.":
        "'?' = followed spoiler-free: log only, no card and no sound.",
    "Exemples :": "Examples:",
    "butbutbut : aucune equipe ne correspond a {} dans {}. "
    "Voir 'butbutbut --list-teams'.":
        "butbutbut : no team matches {} in {}. "
        "See 'butbutbut --list-teams'.",
    "butbutbut : aucune competition ne correspond au prefixe de {}. "
    "Voir 'butbutbut --list'.":
        "butbutbut : no competition matches the prefix of {}. "
        "See 'butbutbut --list'.",
    "butbutbut : {} vise une competition qui n'est pas suivie : "
    "ajoute-la a --leagues, ou retire le prefixe.":
        "butbutbut : {} points at a competition that is not followed: "
        "add it to --leagues, or drop the prefix.",

    # ----------------------------------------------------------- --screens --
    "butbutbut : {} ecran(s) detecte(s)": "butbutbut : {} screen(s) detected",
    "  (principal)": "  (primary)",
    "  {}  {:<16} {}x{} a +{}+{}{}": "  {}  {:<16} {}x{} at +{}+{}{}",
    "\nPar defaut la carte s'affiche en bas a droite de l'ecran principal.":
        "\nBy default the card appears at the bottom right of the primary "
        "screen.",
    "La deplacer :  butbutbut --screen 1 --position top-right":
        "To move it:  butbutbut --screen 1 --position top-right",

    # ------------------- les demonstrations : --test, --speak, --test-hook --
    # Ce que --test-hook montre a l'ecran est une colonne comme celle de
    # --status : le ' : ' y tombe au meme index.
    "butbutbut : voix - {}": "butbutbut : voice - {}",
    "butbutbut : demo epinglee - [{}] {}": "butbutbut : pinned demo - [{}] {}",
    'butbutbut : aucune commande a essayer. Passe --on-goal "...", ou pose la '
    "cle on_goal dans le fichier de configuration.":
        'butbutbut : no command to try. Pass --on-goal "...", or put the '
        "on_goal key in the configuration file.",
    "butbutbut : but fabrique, la commande recevra":
        "butbutbut : made-up goal, the command will get",
    "\n  commande    : {}": "\n  command     : {}",
    "  resultat    : tuee apres {:.0f}s, elle ne rendait pas la main":
        "  result      : killed after {:.0f}s, it would not hand back control",
    "  resultat    : impossible de la lancer ({})":
        "  result      : could not run it ({})",
    "  resultat    : code de sortie {}": "  result      : exit code {}",
    "  sortie      :": "  output      :",

    # ------------------------------------------- --update, --stop, erreurs --
    "butbutbut {} - mise a jour": "butbutbut {} - update",
    "butbutbut : aucun daemon en cours.": "butbutbut : no daemon running.",
    "butbutbut : daemon {} arrete.": "butbutbut : daemon {} stopped.",
    "butbutbut : impossible d'arreter {} : {}":
        "butbutbut : cannot stop {} : {}",
    "Un but tombe en Ligue 1, Premier League, LaLiga, Serie A ou Bundesliga : "
    "le son part et le score s'affiche a l'ecran. Le hockey et le rugby sont "
    "dans le catalogue, a la demande (voir --list).":
        "A goal goes in in Ligue 1, the Premier League, LaLiga, Serie A or "
        "the Bundesliga: the sound fires and the score comes up on screen. "
        "Hockey and rugby are in the catalogue, on request (see --list).",
    "butbutbut : position inconnue : {} (voir --help)":
        "butbutbut : unknown position: {} (see --help)",
    "butbutbut : dossier de donnees inutilisable : {}":
        "butbutbut : unusable data directory: {}",
    "butbutbut : corne regeneree -> {}":
        "butbutbut : horn regenerated -> {}",

    # -------------------------------------------------------------- --help --

    # Les metavariables de l'aide. CODE et MINUTES s'ecrivent pareil.
    "CHEMIN": "PATH",
    "LISTE": "LIST",
    "EQUIPE": "TEAM",
    "EQUIPE|JOURS": "TEAM|DAYS",
    "competitions suivies, separees par des virgules (defaut : les 5 grands "
    "championnats de football). Ex : --leagues l1,pl,ucl ; 'all' pour tout le "
    "catalogue de football, 'hockey' ou 'rugby' pour un autre sport entier, "
    "'all-sports' pour tout ; un code ESPN marche aussi (por.1, hockey:nhl)":
        "leagues to follow, comma separated (default: the big five football "
        "leagues). E.g. --leagues l1,pl,ucl ; 'all' for the whole football "
        "catalogue, 'hockey' or 'rugby' for a whole other sport, 'all-sports' "
        "for everything ; an ESPN code works too (por.1, hockey:nhl)",
    "COIN": "CORNER",
    "CHOIX": "CHOICE",
    "SECONDES": "SECONDS",

    "affiche N cartes de demonstration puis quitte (defaut 1 ; --test 3 "
    "montre l'empilement)":
        "show N demonstration cards, then quit (default 1 ; --test 3 shows "
        "them stacking)",
    "affiche les matchs du jour dans le terminal puis quitte":
        "show today's matches in the terminal, then quit",
    "affiche les prochains matchs puis quitte. Sans rien : les {} prochains "
    "jours des competitions suivies. '--next om' cible une equipe, '--next "
    "14' allonge la fenetre ({} au plus)":
        "show the coming matches, then quit. With nothing: the next {} days "
        "of the leagues being followed. '--next om' aims at one team, '--next "
        "14' widens the window ({} at most)",
    "COMPETITION|EQUIPE": "LEAGUE|TEAM",
    "affiche le classement puis quitte. Sans rien : les competitions suivies. "
    "'--table l1' cible une competition, '--table om' surligne une equipe "
    "dans la sienne, et les deux se combinent":
        "show the table, then quit. With nothing: the leagues being followed. "
        "'--table l1' aims at one league, '--table om' highlights a team in "
        "its own, and the two combine",
    "affiche l'etat (daemon, dernier releve, matchs en cours, son, ecrans, "
    "connexion)":
        "show the current state (daemon, last poll, live matches, sound, "
        "screens, connection)",
    "recapitule les buts signales aujourd'hui":
        "sum up the goals reported today",
    "recapitule les buts des {} derniers jours (aujourd'hui compris)":
        "sum up the goals of the last {} days (today included)",
    "recapitule les buts des {} derniers jours":
        "sum up the goals of the last {} days",
    "recapitule les buts depuis ce jour, au format AAAA-MM-JJ. Ex : --since "
    "2026-09-01. L'emporte sur --week et --month.":
        "sum up the goals since that day, in YYYY-MM-DD form. E.g. --since "
        "2026-09-01. Wins over --week and --month.",
    "classe les buteurs vus passer, buts annules par la VAR deduits. Sur tout "
    "le journal, ou sur la fenetre de --week, --month ou --since":
        "rank the scorers seen, goals ruled out by VAR deducted. Over the "
        "whole log, or over the window of --week, --month or --since",
    "les formes cachees dans le journal : les buts par minute de match "
    "(histogramme), par competition, les soirees les plus prolifiques. Meme "
    "fenetre et memes filtres que --top-scorers":
        "the shapes hidden in the log: goals by match minute (histogram), by "
        "league, the highest-scoring evenings. Same window and same filters "
        "as --top-scorers",
    "ecrit les buts du journal en donnees sur la sortie standard, pour un "
    "tableur ou un script. Memes fenetres et memes filtres que --stats. Ex : "
    "butbutbut --export csv --month > buts.csv":
        "write the log's goals out as data on standard output, for a "
        "spreadsheet or a script. Same windows and same filters as --stats. "
        "E.g. butbutbut --export csv --month > goals.csv",
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
    "FICHIER": "FILE",
    "surveille normalement, et ecrit en plus chaque reponse brute de la "
    "source dans FICHIER (JSON Lines ; un nom en .gz est compresse). C'est ce "
    "que --replay rejoue.":
        "watch as usual, and also write every raw answer from the source into "
        "FILE (JSON Lines ; a .gz name is compressed). That is what --replay "
        "replays.",
    "rejoue un enregistrement : memes cartes, meme son, meme journal, sans "
    "reseau. Ni le journal ni l'etat du vrai daemon ne sont touches.":
        "replay a recording: same cards, same sound, same log, without the "
        "network. Neither the log nor the real daemon's state is touched.",
    "avec --replay : divise les ecarts de temps par N (defaut 1 ; 60 = une "
    "heure de match en une minute)":
        "with --replay: divide the time gaps by N (default 1 ; 60 = an hour "
        "of match in one minute)",
    "fichier de configuration a lire (defaut : {} dans le dossier de donnees, "
    "voir 'butbutbut --paths')":
        "configuration file to read (default: {} in the data directory, see "
        "'butbutbut --paths')",
    "ecrit un fichier de configuration d'exemple, commente, puis quitte "
    "(n'ecrase rien)":
        "write a commented example configuration file, then quit (never "
        "overwrites anything)",
    "competitions a ne pas suivre, meme syntaxe. Ex : --exclude liga,seriea":
        "leagues not to follow, same syntax. E.g. --exclude liga,seriea",
    "liste les competitions surveillables et leurs noms":
        "list the leagues that can be watched, with their names",
    "ne signaler que les matchs de ces equipes, separees par des virgules. "
    "Un match compte des qu'une des deux equipes y est, et un mot prefixe ne "
    "vaut que dans sa competition. Ex : --teams om,psg ou --teams "
    "ligue2:sochaux":
        "only report matches involving these teams, comma separated. A match "
        "counts as soon as either side is in the list, and a prefixed word "
        "only applies inside its competition. E.g. --teams om,psg or --teams "
        "ligue2:sochaux",
    "ne rien signaler des matchs de ces equipes, prefixe compris "
    "(ligue2:metz)":
        "report nothing from matches involving these teams, prefix included "
        "(ligue2:metz)",
    "garde a l'ecran une carte qui suit les matchs de cette equipe : elle "
    "apparait au coup d'envoi, se met a jour a chaque releve et s'en va "
    "quelques minutes apres la fin. Une seule equipe, et jamais de son. Ex : "
    "--pin om":
        "keep a card on screen that follows this team's matches: it appears "
        "at kick-off, updates at every poll and leaves a few minutes after "
        "the end. One team only, and never any sound. E.g. --pin om",
    "matchs regardes en differe : aucune carte ni aucun son pour ces equipes, "
    "quel que soit l'evenement. Le journal, lui, garde tout (butbutbut "
    "--today). Ex : --spoiler-free om":
        "matches watched later: no card and no sound for these teams, "
        "whatever happens. The log keeps everything (butbutbut --today). E.g. "
        "--spoiler-free om",
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
    # La phrase nomme la metavariable : elle doit la nommer comme --help
    # l'affiche desormais, SECONDS, sinon elle renvoie a un mot absent.
    "quand une application en plein ecran masque l'ecran, repasser la carte "
    "des que l'ecran se libere, pendant SECONDES au plus (defaut {:.0f} ; "
    "Windows uniquement, voir README)":
        "when a fullscreen application hides the screen, show the card again "
        "as soon as the screen is free, for SECONDS at most (default "
        "{:.0f} ; Windows only, see README)",
    "PLAGE": "RANGE",
    "plage horaire ou rien ne s'affiche et rien ne sonne, au format {} (ex : "
    "{}). Le but tombe quand meme dans le journal, et --today le retrouve. "
    "L'heure est celle de la machine, la plage peut enjamber minuit.":
        "time range where nothing is shown and nothing sounds, in the form {} "
        "(e.g. {}). The goal still lands in the log, and --today finds it "
        "again. The clock is the machine's, and the range may cross midnight.",
    "se taire aussi quand le systeme signale qu'on presente : mode "
    "presentation, ecran duplique ou 'ne pas deranger'. Windows uniquement ; "
    "un partage de fenetre Teams/Zoom n'est pas detectable, voir README":
        "stay quiet also when the system says you are presenting: "
        "presentation mode, duplicated screen or 'do not disturb'. Windows "
        "only ; a Teams/Zoom window share is not detectable, see README",
    "signale aussi les cartons rouges, par une carte discrete et sans son":
        "report red cards too, with a discreet card and no sound",
    "annonce le match ce nombre de minutes avant le coup d'envoi, une seule "
    "fois et sans son (0 = desactive, defaut)":
        "announce the match this many minutes before kick-off, once only and "
        "without sound (0 = off, default)",
    "au reveil apres une veille, resume en une carte muette les buts tombes "
    "pendant l'absence (par defaut le reveil reste silencieux)":
        "on waking from sleep, sum up in one silent card the goals scored "
        "while you were away (by default the wake-up stays silent)",
    "COMMANDE": "COMMAND",
    "commande a lancer a chaque but, avec le detail du but dans des variables "
    "d'environnement BUT_* (voir --test-hook et le README)":
        "command to run on every goal, with the goal's details in BUT_* "
        "environment variables (see --test-hook and the README)",
    "essaie la commande de --on-goal sur un but fabrique, et montre ce "
    "qu'elle rend":
        "try the --on-goal command on a made-up goal, and show what it gives "
        "back",
    "langue des cartes : fr, en, es, it, de (defaut : celle du systeme, "
    "francais a defaut). Le journal, lui, reste toujours en francais.":
        "card language: fr, en, es, it, de (default: the system language, "
        "French otherwise). The log stays in French.",
    "pas d'ecusson sur les cartes, et rien de telecharge (les couleurs des "
    "clubs restent)":
        "no crests on the cards, and nothing downloaded (club colours stay)",
    "mode muet": "mute",
    "dit le but a voix haute, en plus du son (ou a sa place avec --no-sound). "
    "La phrase est celle des cartes, dans leur langue. 'butbutbut --test "
    "--speak' l'essaie tout de suite.":
        "say the goal out loud, on top of the sound (or in its place with "
        "--no-sound). The sentence is the cards', in their language. "
        "'butbutbut --test --speak' tries it right away.",
    "volume de la corne synthetisee, 0.0 a 1.0":
        "volume of the synthesised horn, 0.0 to 1.0",
    "PAIRES": "PAIRS",
    "un son a soi pour une equipe ou une competition, sous forme de paires "
    "nom=chemin separees par des virgules. Les noms sont ceux de --teams et "
    "de --leagues, et l'equipe l'emporte sur sa competition. Un chemin fautif "
    "est refuse au demarrage. Ex : --sound-for om=~/sons/om.wav":
        "a sound of your own for a team or a league, as name=path pairs "
        "separated by commas. The names are those of --teams and of "
        "--leagues, and the team wins over its league. A wrong path is "
        "refused at start-up. E.g. --sound-for om=~/sounds/om.wav",
    "regenere la corne synthetisee": "regenerate the synthesised horn",
    "n'ecrit que dans le journal": "write to the log only",
    "butbutbut : --pin ne prend qu'une equipe ({!r} en annonce plusieurs) : "
    "il n'y a jamais qu'une carte epinglee.":
        "butbutbut : --pin takes only one team ({!r} names several): there is "
        "only ever one pinned card.",
    'francais': 'French',
    'anglais': 'English',
    'espagnol': 'Spanish',
    'italien': 'Italian',
    'allemand': 'German',
    'aucune competition selectionnee.': 'no competition selected.',
    'plus aucune competition a surveiller apres exclusion.':
        'nothing left to watch after the exclusions.',
    'butbutbut : impossible de verifier les equipes (source injoignable), on continue sans verification.':
        'butbutbut: cannot check the teams (source unreachable), carrying on without checking.',
}
