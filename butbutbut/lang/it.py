"""Catalogue it : le francais en cle, la traduction en valeur.

Une entree absente rend le francais. Les {accolades} sont des trous a valeur :
elles doivent se retrouver a l'identique dans la traduction, sinon le texte
sortira sans sa donnee.

Les etiquettes de --status forment une colonne : le ' : ' tombe au meme
index qu'en francais, quitte a abreger (suoni pers., gol di oggi).
"""

MESSAGES = {
    'Exemples :':
        'Esempi:',
    "\n{} match(s), '>' = en cours.":
        "\n{} partite, '>' = in corso.",
    '  releve      : {}':
        '  rilevamento : {}',
    '  buts du jour: {}  (le detail : butbutbut --today)':
        '  gol di oggi : {}  (dettaglio: butbutbut --today)',
    'butbutbut : buts signales le {:%d/%m/%Y}':
        'butbutbut : gol segnalati il {:%d/%m/%Y}',
    '\n{} but(s) dans {} competition(s).':
        '\n{} gol in {} competizioni.',
    '  langue      : {}':
        '  lingua      : {}',
    '  suivi       : {}':
        '  seguite     : {}',
    '  source      : ESPN scoreboard (public, sans cle)':
        '  fonte       : ESPN scoreboard (pubblico, senza chiave)',
    '  cadence     : {}s en direct / {}s au repos':
        '  cadenza     : {}s in diretta / {}s a riposo',
    '  donnees     : {}':
        '  dati        : {}',
    '  sons perso  : {}  ({} fichier(s))':
        '  suoni pers. : {}  ({} file)',
    '  ecussons    : {}':
        '  stemmi      : {}',
    # 'su' + 'lo schermo' donnerait 'su lo schermo' : la preposition
    # articulee ('sullo') est portee par la valeur, pas par le gabarit.
    '  ecrans      : {} -> carte en {} sur {}':
        '  schermi     : {} -> scheda in {} {}',
    '  plein ecran : {}':
        '  fullscreen  : {}',
    '  journal     : {}':
        '  registro    : {}',
    '\nExemples :':
        '\nEsempi:',
    '  butbutbut --exclude liga,seriea        (les 5 grands moins deux)':
        '  butbutbut --exclude liga,seriea        (i 5 grandi campionati '
        'meno due)',
    '  butbutbut --leagues all                (tout le catalogue)':
        '  butbutbut --leagues all                (tutto il catalogo)',
    "  butbutbut --leagues por.1              (n'importe quel code ESPN)":
        '  butbutbut --leagues por.1              (un codice ESPN qualsiasi)',
    'butbutbut : {} ecran(s) detecte(s)':
        'butbutbut : {} schermi rilevati',
    "\nPar defaut la carte s'affiche en bas a droite de l'ecran principal.":
        '\nDi base la scheda compare in basso a destra sullo schermo '
        'principale.',
    'La deplacer :  butbutbut --screen 1 --position top-right':
        'Per spostarla:  butbutbut --screen 1 --position top-right',
    'butbutbut {} - mise a jour':
        'butbutbut {} - aggiornamento',
    "butbutbut : aucune equipe ne correspond a {} dans {}. Voir 'butbutbut "
    "--list-teams'.":
        "butbutbut : nessuna squadra corrisponde a {} in {}. Vedi 'butbutbut "
        "--list-teams'.",
    '{} - {} equipe(s)':
        '{} - {} squadre',
    "'*' = suivie, '-' = exclue.":
        "'*' = seguita, '-' = esclusa.",
    '                etat laisse par un daemon qui ne tourne plus':
        '                stato lasciato da un daemon ormai spento',
    '  en cours    : inconnu (le dernier releve est trop vieux)':
        '  in corso    : sconosciuto (ultimo rilevamento troppo vecchio)',
    '  en cours    : {}':
        '  in corso    : {}',
    "\n  (aucun but pour l'instant)":
        '\n  (nessun gol per ora)',
    '\nJournal : {}':
        '\nRegistro: {}',
    "'-' = but retire par la VAR ({}).":
        "'-' = gol annullato dal VAR ({}).",
    '  equipes     : {}':
        '  squadre     : {}',
    '  competitions: {}':
        '  competizioni: {}',
    '  son         : {}{}':
        '  suono       : {}{}',
    '  son         : {} ({})':
        '  suono       : {} ({})',
    '  lecteur     : winsound + MCI (integres)':
        '  lettore     : winsound + MCI (integrati)',
    '  lecteur     : {}':
        '  lettore     : {}',
    '  affichage   : tkinter OK':
        '  grafica     : tkinter OK',
    'OK ({} : {} match(s))':
        'OK ({}: {} partite)',
    'butbutbut : daemon {} arrete.':
        'butbutbut : daemon {} fermato.',
    'affiche N cartes de demonstration puis quitte (defaut 1 ; --test 3 '
    "montre l'empilement)":
        'mostra N schede di prova poi esce (di base 1 ; --test 3 le mostra '
        'impilate)',
    'affiche les matchs du jour dans le terminal puis quitte':
        'mostra le partite di oggi nel terminale poi esce',
    "affiche l'etat (daemon, dernier releve, matchs en cours, son, ecrans, "
    'connexion)':
        'mostra lo stato (daemon, ultimo rilevamento, partite in corso, '
        'suono, schermi, connessione)',
    "recapitule les buts signales aujourd'hui":
        'riepiloga i gol segnalati oggi',
    'arrete le daemon en cours':
        'ferma il daemon in esecuzione',
    'affiche les chemins utilises':
        'mostra i percorsi usati',
    'liste les ecrans detectes':
        'elenca gli schermi rilevati',
    "met a jour butbutbut depuis GitHub et rejoue l'installeur":
        "aggiorna butbutbut da GitHub e rilancia l'installer",
    'dit si une version plus recente existe, sans rien installer':
        'dice se esiste una versione nuova, senza installare nulla',
    'avec --update ou --check-update : viser la pointe de la branche '
    'principale au lieu de la derniere release':
        'con --update o --check-update: puntare alla testa del ramo '
        "principale invece che all'ultima release",
    'fichier de configuration a lire (defaut : {} dans le dossier de '
    "donnees, voir 'butbutbut --paths')":
        'file di configurazione da leggere (di base: {} nella cartella dati, '
        "vedi 'butbutbut --paths')",
    "ecrit un fichier de configuration d'exemple, commente, puis quitte "
    "(n'ecrase rien)":
        'scrive un file di configurazione di esempio, commentato, poi esce '
        '(non sovrascrive nulla)',
    'competitions suivies, separees par des virgules (defaut : les 5 grands '
    "championnats). Ex : --leagues l1,pl,ucl ; 'all' pour tout le catalogue "
    '; un code ESPN marche aussi (por.1)':
        'competizioni seguite, separate da virgole (di base: i 5 grandi '
        "campionati). Es: --leagues l1,pl,ucl ; 'all' per tutto il catalogo "
        '; funziona anche un codice ESPN (por.1)',
    'competitions a ne pas suivre, meme syntaxe. Ex : --exclude liga,seriea':
        'competizioni da non seguire, stessa sintassi. Es: --exclude '
        'liga,seriea',
    'liste les competitions surveillables et leurs noms':
        'elenca le competizioni sorvegliabili e i loro nomi',
    'ne signaler que les matchs de ces equipes, separees par des virgules. '
    "Un match compte des qu'une des deux equipes y est. Ex : --teams om,psg":
        'segnala solo le partite di queste squadre, separate da virgole. Una '
        'partita conta se compare una delle due squadre. Es: --teams om,psg',
    'ne rien signaler des matchs de ces equipes':
        'non segnalare nulla delle partite di queste squadre',
    'liste les equipes des competitions suivies':
        'elenca le squadre delle competizioni seguite',
    'secondes entre deux releves quand un match est en cours (defaut {})':
        'secondi tra due rilevamenti con una partita in corso (di base {})',
    "secondes entre deux releves quand il n'y a rien a suivre (defaut {})":
        'secondi tra due rilevamenti senza nulla da seguire (di base {})',
    "duree d'affichage de la carte (defaut : la duree du son, au moins {})":
        'durata di visualizzazione della scheda (di base: la durata del '
        'suono, almeno {})',
    "coin ou les cartes s'empilent : bottom-right (defaut), bottom-left, "
    'top-right, top-left, center':
        'angolo in cui si impilano le schede: bottom-right (di base), '
        'bottom-left, top-right, top-left, center',
    "ecran d'affichage : 'primary' (defaut) ou un index (0, 1, 2...). Voir "
    "'butbutbut --screens'.":
        "schermo su cui mostrare le schede: 'primary' (di base) o un indice "
        "(0, 1, 2...). Vedi 'butbutbut --screens'.",
    'taille de la carte (1.0 par defaut, 1.5 = plus grande)':
        'dimensione della scheda (1.0 di base, 1.5 = ingrandita)',
    'opacite, 0.0 a 1.0':
        'opacita, da 0.0 a 1.0',
    'pas de carte : seulement le son et le journal':
        'niente scheda: solo il suono e il registro',
    "pas de carte au coup d'envoi, a la mi-temps, a la reprise ni a la fin "
    'du match (les buts, si)':
        "niente scheda al fischio d'inizio, all'intervallo, alla ripresa e a "
        'fine partita (i gol restano)',
    "quand une application en plein ecran masque l'ecran, repasser la carte "
    "des que l'ecran se libere, pendant SECONDES au plus (defaut {:.0f} ; "
    'Windows uniquement, voir README)':
        "quando un'applicazione a schermo intero copre lo schermo, rimettere "
        'la scheda appena lo schermo si libera, per SECONDI al massimo (di '
        'base {:.0f} ; solo Windows, vedi README)',
    'signale aussi les cartons rouges, par une carte discrete et sans son':
        'segnala anche i cartellini rossi, con una scheda discreta e senza '
        'suono',
    "annonce le match ce nombre de minutes avant le coup d'envoi, une seule "
    'fois et sans son (0 = desactive, defaut)':
        'annuncia la partita questo numero di minuti prima del fischio '
        "d'inizio, una sola volta e senza suono (0 = disattivato, di base)",
    'langue des cartes : fr, en, es, it, de (defaut : celle du systeme, '
    'francais a defaut). Le journal, lui, reste toujours en francais.':
        'lingua delle schede: fr, en, es, it, de (di base: quella del '
        'sistema, francese come ripiego). Il registro resta in francese.',
    "pas d'ecusson sur les cartes, et rien de telecharge (les couleurs des "
    'clubs restent)':
        'niente stemmi sulle schede, e nessun download (i colori dei club '
        'restano)',
    'mode muet':
        'silenzioso',
    'volume de la corne synthetisee, 0.0 a 1.0':
        'volume della tromba sintetizzata, da 0.0 a 1.0',
    'regenere la corne synthetisee':
        'rigenera la tromba sintetizzata',
    "n'ecrit que dans le journal":
        'scrive solo nel registro',
    'butbutbut : position inconnue : {} (voir --help)':
        'butbutbut : posizione sconosciuta: {} (vedi --help)',
    'butbutbut : corne regeneree -> {}':
        'butbutbut : tromba rigenerata -> {}',
    '  (la source ne publie pas de liste pour cette competition)':
        '  (la fonte non pubblica un elenco per questa competizione)',
    '                (!) plus rien depuis, alors que la cadence est de {}s : '
    'daemon bloque ou source injoignable ?':
        '                (!) nulla da allora, con una cadenza di {}s: daemon '
        'bloccato o fonte irraggiungibile?',
    'actif (pid {})':
        'attivo (pid {})',
    'arrete':
        'fermo',
    'desactives (--no-logos)':
        'disattivati (--no-logos)',
    '{}  ({} en cache)':
        '{}  ({} in cache)',
    "l'ecran principal":
        'sullo schermo principale',
    'ecran {}':
        'sullo schermo {}',
    '  affichage   : tkinter MANQUANT (voir README)':
        '  grafica     : tkinter ASSENTE (vedi README)',
    'ECHEC ({})':
        'FALLITO ({})',
    "butbutbut : impossible d'arreter {} : {}":
        'butbutbut : impossibile fermare {}: {}',
    'butbutbut : dossier de donnees inutilisable : {}':
        'butbutbut : cartella dati inutilizzabile: {}',
    'injoignable ({})':
        'irraggiungibile ({})',

    # --- la prose du parseur -------------------------------------------------
    'Un but tombe en Ligue 1, Premier League, LaLiga, Serie A ou Bundesliga : '
    "le son part et le score s'affiche a l'ecran.":
        'Un gol in Ligue 1, Premier League, LaLiga, Serie A o Bundesliga: '
        'parte il suono e il punteggio compare sullo schermo.',
    # Les metavariables du --help. SECONDI se retrouve dans l'aide de
    # --retry-fullscreen, plus haut : les deux doivent dire le meme mot.
    'CHEMIN':
        'PERCORSO',
    'LISTE':
        'ELENCO',
    'COIN':
        'ANGOLO',
    'CHOIX':
        'SCELTA',
    'SECONDES':
        'SECONDI',
    'MINUTES':
        'MINUTI',
    'CODE':
        'CODICE',

    # --- les valeurs de --status ---------------------------------------------
    # 'Connexion' fait 9 signes, 'Connessione' en fait 11 : les deux espaces
    # de bourrage disparaissent et le ' : ' ne bouge pas d'un cran.
    '\n  Connexion   : ':
        '\n  Connessione : ',
    "aucun pour l'instant":
        'nessuno per ora',
    "aucun (le daemon efface son etat en s'arretant)":
        'nessuno (il daemon cancella il suo stato quando si ferma)',
    '{} match(s)':
        '{} partite',
    ' sur {} au programme':
        ' su {} in programma',
    '  (absent, voir --write-config)':
        '  (assente, vedi --write-config)',
    ' (+{} autre(s), tirage au hasard)':
        ' (+{} altri, scelto a sorte)',
    'fourni':
        'incluso',
    'corne synthetisee':
        'tromba sintetizzata',
    'detecte (la carte masquee est notee au journal)':
        'rilevato (la scheda coperta viene notata nel registro)',
    'non detectable sur cette plateforme':
        'non rilevabile su questa piattaforma',
    'AUCUN (installe mpv/ffmpeg/pipewire/alsa-utils)':
        'NESSUNO (installa mpv/ffmpeg/pipewire/alsa-utils)',
    'butbutbut : aucun daemon en cours.':
        'butbutbut : nessun daemon in esecuzione.',

    # --- l'age du dernier releve ---------------------------------------------
    # L'italien met le 'fa' apres la duree la ou le francais met 'il y a'
    # devant : le trou a valeur change de place, jamais de rang.
    'date inconnue':
        'data sconosciuta',
    'il y a {} s':
        '{} s fa',
    'il y a {} min':
        '{} min fa',
    'il y a {} h {:02d}':
        '{} h {:02d} fa',

    # --- les ecrans ----------------------------------------------------------
    '1 ecran ({}x{})':
        '1 schermo ({}x{})',
    '{} ecrans [{}]':
        '{} schermi [{}]',
    '  (principal)':
        '  (principale)',

    # --- les competitions ----------------------------------------------------
    'les 5 grands championnats':
        'i 5 grandi campionati',
    'tout le catalogue ({} competitions)':
        'tutto il catalogo ({} competizioni)',
    '{} et {} autres':
        '{} e altre {}',
    'Les 5 grands (defaut)':
        'I 5 grandi (di base)',
    'Aussi disponibles':
        'Anche disponibili',
    'butbutbut : competitions surveillables\n':
        'butbutbut : competizioni sorvegliabili\n',

    # --- les matchs de --scores ----------------------------------------------
    '  (aucun match au programme)':
        '  (nessuna partita in programma)',
    '  (aucun match de ces equipes)':
        '  (nessuna partita di queste squadre)',
    'en cours':
        'in corso',
    'termine':
        'finita',
    'a venir':
        'da giocare',
    'imminent':
        'imminente',
    'dans {} min':
        'tra {} min',
    'francais': 'francese',
    'anglais': 'inglese',
    'espagnol': 'spagnolo',
    'italien': 'italiano',
    'allemand': 'tedesco',
    'aucune competition selectionnee.':
        'nessuna competizione selezionata.',
    'plus aucune competition a surveiller apres exclusion.':
        'non resta nessuna competizione da seguire dopo le esclusioni.',
    'butbutbut : impossible de verifier les equipes (source injoignable), on continue sans verification.':
        'butbutbut : impossibile verificare le squadre (fonte irraggiungibile), si continua senza verifica.',
}
