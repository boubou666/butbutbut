"""Catalogue it : le francais en cle, la traduction en valeur.

Une entree absente rend le francais. Les {accolades} sont des trous a valeur :
elles doivent se retrouver a l'identique dans la traduction, sinon le texte
sortira sans sa donnee.

Les etiquettes de --status forment une colonne : le deux-points tombe au meme
caractere qu'en francais, quitte a abreger (suoni pers., gol di oggi,
anti-spoiler, suono per). Une etiquette qui remplit ses douze signes le colle,
comme le francais le fait deja ('competizioni:').

'anti-spoiler' plutot que 'senza spoiler' : le second fait treize signes et
decalait la colonne d'un cran. Le mot est porte partout ou la phrase parle du
mode, pour que le fichier ne dise pas la meme chose de deux facons.

L'italien n'ecrit pas ici 'e' accent grave : en ASCII il se confondrait avec
'e' = et. Les phrases qui le demandaient sont tournees autrement.

tests/test_i18n.py verifie tout cela phrase par phrase, et refuse une phrase
nouvelle qui ne serait ni traduite ici ni declaree laissee en francais.
"""

MESSAGES = {
    'tirs au but': 'calci di rigore',
    'Exemples :':
        'Esempi:',
    "\n{} match(s), '>' = en cours.":
        "\n{} partite, '>' = in corso.",
    "'?' = sans spoiler : {} match(s) masque(s). Le journal, lui, a tout : "
    'butbutbut --today.':
        "'?' = anti-spoiler: {} partite nascoste. Il registro invece ha "
        'tutto: butbutbut --today.',
    '  releve      : {}':
        '  rilevamento : {}',
    '  buts du jour: {}  (le detail : butbutbut --today)':
        '  gol di oggi : {}  (dettaglio: butbutbut --today)',

    # --- --next --------------------------------------------------------------
    # Une competition qui n'a pas repondu ne fait pas echouer la commande :
    # elle se signale en fin de liste, et le calendrier se dit incomplet.
    'butbutbut : prochains matchs - {}, {} jour(s)':
        'butbutbut : prossime partite - {}, {} giorni',
    '\n{} match(s) a venir dans {} competition(s), sur {} jour(s).':
        '\n{} partite in arrivo in {} competizioni, su {} giorni.',
    "\nAucune competition n'a repondu : rien a annoncer.":
        '\nNessuna competizione ha risposto: niente da annunciare.',
    '  ({} injoignable : {})': '  ({} irraggiungibile: {})',
    '  (le calendrier ci-dessus est donc incomplet ; les autres competitions '
    'ont repondu)':
        '  (il calendario qui sopra resta quindi incompleto ; le altre '
        'competizioni hanno risposto)',

    # --- --table -------------------------------------------------------------
    # Le classement d'une competition, pas un palmares de buteurs : les deux
    # mots se separent dans les langues qui les distinguent.
    'butbutbut : classement - {}': 'butbutbut : classifica - {}',
    "\nAucune competition n'a repondu : rien a classer.":
        '\nNessuna competizione ha risposto: niente da classificare.',
    "  (une coupe se joue en tableau ; hors saison, la source n'a rien a "
    'servir)':
        '  (una coppa si gioca a eliminazione ; fuori stagione, la fonte non '
        'ha nulla da servire)',
    '  (le classement ci-dessus est donc incomplet ; les autres competitions '
    'ont repondu)':
        '  (la classifica qui sopra resta quindi incompleta ; le altre '
        'competizioni hanno risposto)',

    # --- la fenetre lue dans le journal --------------------------------------
    # Nommee en tete de --today, --stats, --top-scorers et --export : la meme
    # phrase sert aux quatre, d'ou sa place avant elles.
    'date illisible : {!r}. Format attendu : AAAA-MM-JJ, par exemple --since '
    '{}':
        'data illeggibile: {!r}. Formato atteso: AAAA-MM-GG, per esempio '
        '--since {}',
    'depuis le debut du journal': "dall'inizio del registro",
    'le {}': 'il {}',
    'du {} au {}': 'dal {} al {}',

    'butbutbut : buts signales le {:%d/%m/%Y}':
        'butbutbut : gol segnalati il {:%d/%m/%Y}',
    'butbutbut : buts signales {}': 'butbutbut : gol segnalati {}',
    "\n  (journal vide : aucun but n'y a encore ete ecrit)":
        '\n  (registro vuoto: nessun gol scritto finora)',
    '\n  (aucun but dans le journal)': '\n  (nessun gol nel registro)',
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
    "  son nomme   : {} paire(s), le plus precis l'emporte":
        '  suono per   : {} coppie, vince la piu precisa',

    # Ce que les deux lignes 'son' de --status affichent a droite : quand un
    # son a soi se declenche, d'apres son nom de fichier ou --sound-for.
    'quand une equipe suivie encaisse':
        'quando una squadra seguita subisce un gol',
    '  (jamais : aucune equipe suivie, voir --teams)':
        '  (mai: nessuna squadra seguita, vedi --teams)',
    'les buts de {}': 'i gol di {}',
    '  (competition non suivie)': '  (competizione non seguita)',
    'tirage general': 'sorteggio generale',
    'et {} autre(s)': 'e altri {}',
    'quand cette equipe marque': 'quando questa squadra segna',

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
    '  butbutbut --leagues all                (tout le catalogue de football)':
        '  butbutbut --leagues all                (tutto il catalogo del '
        'calcio)',
    '  butbutbut --leagues nhl,top14          (hockey et rugby, a la demande)':
        '  butbutbut --leagues nhl,top14          (hockey e rugby, a '
        'richiesta)',
    '  butbutbut --leagues rugby              (tout le rugby du catalogue)':
        '  butbutbut --leagues rugby              (tutto il rugby del '
        'catalogo)',
    '  butbutbut --leagues all-sports         (vraiment tout)':
        '  butbutbut --leagues all-sports         (davvero tutto)',
    '  butbutbut --leagues feminines          (tout le football feminin)':
        '  butbutbut --leagues feminines          (tutto il calcio femminile)',
    '  butbutbut --leagues l1f,wsl,uclf       (le meme, au feminin : un f a la fin)':
        '  butbutbut --leagues l1f,wsl,uclf       (lo stesso, al femminile: una f finale)',
    "  butbutbut --leagues por.1              (n'importe quel code ESPN)":
        '  butbutbut --leagues por.1              (un codice ESPN qualsiasi)',
    '  butbutbut --leagues hockey:nhl         (... y compris dans un autre '
    'sport)':
        '  butbutbut --leagues hockey:nhl         (... anche in un altro '
        'sport)',
    'butbutbut : {} ecran(s) detecte(s)':
        'butbutbut : {} schermi rilevati',
    "\nPar defaut la carte s'affiche en bas a droite de l'ecran principal.":
        '\nDi base la scheda compare in basso a destra sullo schermo '
        'principale.',
    'La deplacer :  butbutbut --screen 1 --position top-right':
        'Per spostarla:  butbutbut --screen 1 --position top-right',

    # --- les demonstrations : --test, --speak, --test-hook -------------------
    # Ce que --test-hook montre a l'ecran est une colonne comme celle de
    # --status : le ' : ' y tombe au meme index.
    'butbutbut : voix - {}': 'butbutbut : voce - {}',
    'butbutbut : demo epinglee - [{}] {}':
        'butbutbut : demo fissata - [{}] {}',
    'butbutbut : aucune commande a essayer. Passe --on-goal "...", ou pose la '
    'cle on_goal dans le fichier de configuration.':
        'butbutbut : nessun comando da provare. Passa --on-goal "...", o '
        'metti la chiave on_goal nel file di configurazione.',
    'butbutbut : but fabrique, la commande recevra':
        'butbutbut : gol di prova, il comando ricevera',
    '\n  commande    : {}': '\n  comando     : {}',
    '  resultat    : tuee apres {:.0f}s, elle ne rendait pas la main':
        '  risultato   : terminato a forza dopo {:.0f}s, non restituiva il '
        'controllo',
    '  resultat    : impossible de la lancer ({})':
        '  risultato   : impossibile lanciarlo ({})',
    '  resultat    : code de sortie {}': '  risultato   : codice di uscita {}',
    '  sortie      :': '  output      :',

    'butbutbut {} - mise a jour':
        'butbutbut {} - aggiornamento',
    "butbutbut : aucune equipe ne correspond a {} dans {}. Voir 'butbutbut "
    "--list-teams'.":
        "butbutbut : nessuna squadra corrisponde a {} in {}. Vedi 'butbutbut "
        "--list-teams'.",
    "butbutbut : aucune competition ne correspond au prefixe de {}. Voir "
    "'butbutbut --list'.":
        "butbutbut : nessuna competizione corrisponde al prefisso di {}. Vedi "
        "'butbutbut --list'.",
    "butbutbut : {} vise une competition qui n'est pas suivie : ajoute-la a "
    "--leagues, ou retire le prefixe.":
        "butbutbut : {} punta a una competizione non seguita: aggiungila a "
        "--leagues, oppure togli il prefisso.",
    '{} - {} equipe(s)':
        '{} - {} squadre',
    "'*' = suivie, '-' = exclue.":
        "'*' = seguita, '-' = esclusa.",
    "'?' = suivie sans spoiler : journal seulement, ni carte ni son.":
        "'?' = seguita anti-spoiler: solo registro, niente scheda e niente "
        'suono.',
    '                etat laisse par un daemon qui ne tourne plus':
        '                stato lasciato da un daemon ormai spento',
    '  en cours    : inconnu (le dernier releve est trop vieux)':
        '  in corso    : sconosciuto (ultimo rilevamento troppo vecchio)',
    '  en cours    : {}':
        '  in corso    : {}',
    "\n  (aucun but pour l'instant)":
        '\n  (nessun gol per ora)',
    '\n  (aucun but sur cette periode)': '\n  (nessun gol in questo periodo)',
    '\nJournal : {}':
        '\nRegistro: {}',
    "'-' = but retire par la VAR ({}).":
        "'-' = gol annullato dal VAR ({}).",
    '\n{} but(s) signale(s), {} jour(s), {} competition(s).':
        '\n{} gol segnalati, {} giorni, {} competizioni.',
    '{} = but retire par la VAR ({}) : {} but(s) confirme(s).':
        '{} = gol annullato dal VAR ({}): {} gol confermati.',
    '  equipes     : {}':
        '  squadre     : {}',
    '  epinglee    : {}': '  fissata     : {}',
    '{} (etat inconnu : voir la ligne releve)':
        '{} (stato ignoto: vedi la riga rilevamento)',
    '{} (aucun match en cours)':
        '{} (nessuna partita in corso)',
    '  sans spoiler: {}  (journal seulement : ni carte, ni son)':
        '  anti-spoiler: {}  (solo registro: niente scheda, niente suono)',
    '  silence     : {}': '  silenzio    : {}',
    '  competitions: {}':
        '  competizioni: {}',
    '  sports      : {}': '  sport       : {}',
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
    'affiche les prochains matchs puis quitte. Sans rien : les {} prochains '
    "jours des competitions suivies. '--next om' cible une equipe, '--next "
    "14' allonge la fenetre ({} au plus)":
        'mostra le prossime partite poi esce. Senza nulla: i prossimi {} '
        "giorni delle competizioni seguite. '--next om' punta a una squadra, "
        "'--next 14' allunga la finestra ({} al massimo)",
    'COMPETITION|EQUIPE': 'COMPETIZIONE|SQUADRA',
    'affiche le classement puis quitte. Sans rien : les competitions suivies. '
    "'--table l1' cible une competition, '--table om' surligne une equipe "
    'dans la sienne, et les deux se combinent':
        'mostra la classifica poi esce. Senza nulla: le competizioni seguite. '
        "'--table l1' punta a una competizione, '--table om' evidenzia una "
        'squadra nella sua, e le due si combinano',
    "affiche l'etat (daemon, dernier releve, matchs en cours, son, ecrans, "
    'connexion)':
        'mostra lo stato (daemon, ultimo rilevamento, partite in corso, '
        'suono, schermi, connessione)',
    "recapitule les buts signales aujourd'hui":
        'riepiloga i gol segnalati oggi',
    "recapitule les buts des {} derniers jours (aujourd'hui compris)":
        'riepiloga i gol degli ultimi {} giorni (oggi compreso)',
    'recapitule les buts des {} derniers jours':
        'riepiloga i gol degli ultimi {} giorni',
    'recapitule les buts depuis ce jour, au format AAAA-MM-JJ. Ex : --since '
    "2026-09-01. L'emporte sur --week et --month.":
        'riepiloga i gol da questo giorno, nel formato AAAA-MM-GG. Es: '
        '--since 2026-09-01. Prevale su --week e --month.',
    'classe les buteurs vus passer, buts annules par la VAR deduits. Sur tout '
    'le journal, ou sur la fenetre de --week, --month ou --since':
        'classifica i marcatori visti passare, dedotti i gol annullati dal '
        'VAR. Su tutto il registro, o sulla finestra di --week, --month o '
        '--since',
    'les formes cachees dans le journal : les buts par minute de match '
    '(histogramme), par competition, les soirees les plus prolifiques. Meme '
    'fenetre et memes filtres que --top-scorers':
        'le forme nascoste nel registro: i gol per minuto di gioco '
        '(istogramma), per competizione, le serate piu prolifiche. Stessa '
        'finestra e stessi filtri di --top-scorers',
    'ecrit les buts du journal en donnees sur la sortie standard, pour un '
    'tableur ou un script. Memes fenetres et memes filtres que --stats. Ex : '
    'butbutbut --export csv --month > buts.csv':
        'scrive i gol del registro come dati sullo standard output, per un '
        'foglio di calcolo o uno script. Stesse finestre e stessi filtri di '
        '--stats. Es: butbutbut --export csv --month > buts.csv',
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
    'FICHIER': 'FILE',
    'surveille normalement, et ecrit en plus chaque reponse brute de la '
    "source dans FICHIER (JSON Lines ; un nom en .gz est compresse). C'est ce "
    'que --replay rejoue.':
        'sorveglia normalmente, e scrive in piu ogni risposta grezza della '
        'fonte in FILE (JSON Lines ; un nome in .gz viene compresso). '
        '--replay riproduce proprio questo.',
    'rejoue un enregistrement : memes cartes, meme son, meme journal, sans '
    "reseau. Ni le journal ni l'etat du vrai daemon ne sont touches.":
        'riproduce una registrazione: stesse schede, stesso suono, stesso '
        'registro, senza rete. Il registro e lo stato del daemon vero restano '
        'intatti.',
    'avec --replay : divise les ecarts de temps par N (defaut 1 ; 60 = une '
    'heure de match en une minute)':
        'con --replay: divide gli scarti di tempo per N (di base 1 ; 60 = '
        "un'ora di partita in un minuto)",
    'fichier de configuration a lire (defaut : {} dans le dossier de '
    "donnees, voir 'butbutbut --paths')":
        'file di configurazione da leggere (di base: {} nella cartella dati, '
        "vedi 'butbutbut --paths')",
    "ecrit un fichier de configuration d'exemple, commente, puis quitte "
    "(n'ecrase rien)":
        'scrive un file di configurazione di esempio, commentato, poi esce '
        '(non sovrascrive nulla)',
    'competitions a ne pas suivre, meme syntaxe. Ex : --exclude liga,seriea':
        'competizioni da non seguire, stessa sintassi. Es: --exclude '
        'liga,seriea',
    'liste les competitions surveillables et leurs noms':
        'elenca le competizioni sorvegliabili e i loro nomi',
    'ne signaler que les matchs de ces equipes, separees par des virgules. '
    "Un match compte des qu'une des deux equipes y est, et un mot prefixe ne "
    'vaut que dans sa competition. Ex : --teams om,psg ou --teams '
    'ligue2:sochaux':
        'segnala solo le partite di queste squadre, separate da virgole. Una '
        'partita conta se compare una delle due squadre, e una parola con '
        'prefisso vale solo nella sua competizione. Es: --teams om,psg o '
        '--teams ligue2:sochaux',
    'ne rien signaler des matchs de ces equipes, prefixe compris '
    '(ligue2:metz)':
        'non segnalare nulla delle partite di queste squadre, prefisso '
        'compreso (ligue2:metz)',
    "garde a l'ecran une carte qui suit les matchs de cette equipe : elle "
    "apparait au coup d'envoi, se met a jour a chaque releve et s'en va "
    'quelques minutes apres la fin. Une seule equipe, et jamais de son. Ex : '
    '--pin om':
        'tiene sullo schermo una scheda che segue le partite di questa '
        "squadra: compare al fischio d'inizio, si aggiorna a ogni rilevamento "
        'e se ne va qualche minuto dopo la fine. Una sola squadra, e mai il '
        'suono. Es: --pin om',
    'matchs regardes en differe : aucune carte ni aucun son pour ces equipes, '
    "quel que soit l'evenement. Le journal, lui, garde tout (butbutbut "
    '--today). Ex : --spoiler-free om':
        'partite guardate in differita: nessuna scheda e nessun suono per '
        "queste squadre, qualunque sia l'evento. Il registro invece tiene "
        'tutto (butbutbut --today). Es: --spoiler-free om',
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
    'PLAGE': 'FASCIA',
    "plage horaire ou rien ne s'affiche et rien ne sonne, au format {} (ex : "
    '{}). Le but tombe quand meme dans le journal, et --today le retrouve. '
    "L'heure est celle de la machine, la plage peut enjamber minuit.":
        'fascia oraria in cui non compare nulla e non suona nulla, nel '
        'formato {} (es: {}). Il gol finisce comunque nel registro, e --today '
        "lo ritrova. Si usa l'ora della macchina, e la fascia puo scavalcare "
        'la mezzanotte.',
    "se taire aussi quand le systeme signale qu'on presente : mode "
    "presentation, ecran duplique ou 'ne pas deranger'. Windows uniquement ; "
    "un partage de fenetre Teams/Zoom n'est pas detectable, voir README":
        'tace anche quando il sistema segnala che si sta presentando: '
        "modalita presentazione, schermo duplicato o 'non disturbare'. Solo "
        'Windows ; la condivisione di una finestra Teams/Zoom resta non '
        'rilevabile, vedi README',
    'signale aussi les cartons rouges, par une carte discrete et sans son':
        'segnala anche i cartellini rossi, con una scheda discreta e senza '
        'suono',
    "annonce le match ce nombre de minutes avant le coup d'envoi, une seule "
    'fois et sans son (0 = desactive, defaut)':
        'annuncia la partita questo numero di minuti prima del fischio '
        "d'inizio, una sola volta e senza suono (0 = disattivato, di base)",
    'au reveil apres une veille, resume en une carte muette les buts tombes '
    "pendant l'absence (par defaut le reveil reste silencieux)":
        'al risveglio dopo una sospensione, riassume in una scheda muta i gol '
        "caduti durante l'assenza (di base il risveglio resta silenzioso)",
    'COMMANDE': 'COMANDO',
    'commande a lancer a chaque but, avec le detail du but dans des variables '
    "d'environnement BUT_* (voir --test-hook et le README)":
        'comando da lanciare a ogni gol, con il dettaglio del gol in '
        "variabili d'ambiente BUT_* (vedi --test-hook e il README)",
    'essaie la commande de --on-goal sur un but fabrique, et montre ce '
    "qu'elle rend":
        'prova il comando di --on-goal su un gol di prova, e mostra cosa '
        'restituisce',
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
    'dit le but a voix haute, en plus du son (ou a sa place avec --no-sound). '
    "La phrase est celle des cartes, dans leur langue. 'butbutbut --test "
    "--speak' l'essaie tout de suite.":
        'dice il gol ad alta voce, oltre al suono (o al suo posto con '
        '--no-sound). Usa la frase delle schede, nella loro lingua. '
        "'butbutbut --test --speak' la prova subito.",
    'volume de la corne synthetisee, 0.0 a 1.0':
        'volume della tromba sintetizzata, da 0.0 a 1.0',
    'PAIRES': 'COPPIE',
    'un son a soi pour une equipe ou une competition, sous forme de paires '
    'nom=chemin separees par des virgules. Les noms sont ceux de --teams et '
    "de --leagues, et l'equipe l'emporte sur sa competition. Un chemin fautif "
    'est refuse au demarrage. Ex : --sound-for om=~/sons/om.wav':
        'un suono tutto tuo per una squadra o una competizione, sotto forma '
        'di coppie nome=percorso separate da virgole. I nomi sono quelli di '
        '--teams e di --leagues, e la squadra vince sulla sua competizione. '
        "Un percorso sbagliato viene rifiutato all'avvio. Es: --sound-for "
        'om=~/sons/om.wav',
    'regenere la corne synthetisee':
        'rigenera la tromba sintetizzata',
    "n'ecrit que dans le journal":
        'scrive solo nel registro',
    "butbutbut : --pin ne prend qu'une equipe ({!r} en annonce plusieurs) : "
    "il n'y a jamais qu'une carte epinglee.":
        'butbutbut : --pin prende una sola squadra ({!r} ne annuncia '
        'diverse): la scheda fissata resta sempre una sola.',
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
    '  rattrapage  : {}': '  recupero    : {}',
    'actif (une carte de resume au reveil, sans son)':
        'attivo (una scheda di riepilogo al risveglio, senza suono)',
    'inactif (le reveil reste silencieux, voir --catch-up)':
        'inattivo (il risveglio resta silenzioso, vedi --catch-up)',
    '  affichage   : tkinter MANQUANT (voir README)':
        '  grafica     : tkinter ASSENTE (vedi README)',
    'ECHEC ({})':
        'FALLITO ({})',
    "butbutbut : impossible d'arreter {} : {}":
        'butbutbut : impossibile fermare {}: {}',
    'Un but tombe en Ligue 1, Premier League, LaLiga, Serie A ou Bundesliga : '
    "le son part et le score s'affiche a l'ecran. Le hockey et le rugby sont "
    'dans le catalogue, a la demande (voir --list).':
        'Un gol in Ligue 1, Premier League, LaLiga, Serie A o Bundesliga: '
        'parte il suono e il punteggio compare sullo schermo. Hockey e rugby '
        'sono nel catalogo, a richiesta (vedi --list).',
    'butbutbut : dossier de donnees inutilisable : {}':
        'butbutbut : cartella dati inutilizzabile: {}',
    'injoignable ({})':
        'irraggiungibile ({})',

    # --- la prose du parseur -------------------------------------------------
    # Les metavariables du --help. SECONDI se retrouve dans l'aide de
    # --retry-fullscreen, plus haut : les deux doivent dire le meme mot.
    'CHEMIN':
        'PERCORSO',
    'LISTE':
        'ELENCO',
    'DATE':
        'DATA',
    'EQUIPE':
        'SQUADRA',
    'EQUIPE|JOURS':
        'SQUADRA|GIORNI',
    'competitions suivies, separees par des virgules (defaut : les 5 grands '
    "championnats de football). Ex : --leagues l1,pl,ucl ; 'all' pour tout le "
    "catalogue de football, 'hockey' ou 'rugby' pour un autre sport entier, "
    "'all-sports' pour tout ; un code ESPN marche aussi (por.1, hockey:nhl)":
        'competizioni seguite, separate da virgole (di base: i 5 grandi '
        "campionati di calcio). Es: --leagues l1,pl,ucl ; 'all' per tutto il "
        "catalogo del calcio, 'hockey' o 'rugby' per un altro sport intero, "
        "'all-sports' per tutto ; anche un codice ESPN va bene (por.1, "
        'hockey:nhl)',
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
    '  crochet     : {}': '  hook        : {}',
    '{}  (essai : --test-hook)': '{}  (prova: --test-hook)',
    'aucun (voir --on-goal)': 'nessuno (vedi --on-goal)',
    '  voix        : {}': '  voce        : {}',
    '  son         : {} fichier(s), le nom dit quand ils jouent':
        '  suono       : {} file, il nome dice quando suonano',
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
    'tout le football feminin ({} competitions)':
        'tutto il calcio femminile ({} competizioni)',
    # "tout le {} ({} competitions)" n'a pas d'entree : le trou y recoit le nom
    # du sport, que sports.py garde en francais pour le journal. La traduire
    # ferait une phrase a moitie italienne ; celle-ci, non.
    'tous les sports ({} competitions)':
        'tutti gli sport ({} competizioni)',
    '{} et {} autres':
        '{} e altre {}',
    'Les 5 grands (defaut)':
        'I 5 grandi (di base)',
    'Aussi disponibles':
        'Anche disponibili',
    'Hockey sur glace (a demander)':
        'Hockey su ghiaccio (a richiesta)',
    'Rugby a XV (a demander)':
        'Rugby a XV (a richiesta)',
    'Football feminin (a demander)':
        'Calcio femminile (a richiesta)',

    # --- --top-scorers -------------------------------------------------------
    # Les buts repris par la VAR sont deduits : le compte affiche n'est pas
    # celui des lignes du journal, et la note le dit.
    'butbutbut : buteurs vus passer {}':
        'butbutbut : marcatori visti passare {}',
    "\n  (aucun buteur connu : la source n'avait pas encore publie l'action)":
        '\n  (nessun marcatore noto: la fonte non aveva ancora pubblicato '
        "l'azione)",
    '  ... et {} autre(s) buteur(s) plus bas au classement.':
        '  ... e altri {} marcatori piu in basso in classifica.',
    '\n{} buteur(s) pour {} but(s) confirme(s) sur {} signale(s).':
        '\n{} marcatori per {} gol confermati su {} segnalati.',
    '{} but(s) retire(s) par la VAR, deduit(s) du classement.':
        '{} gol annullati dal VAR, dedotti dalla classifica.',
    '{} annulation(s) sans but a retirer dans cette fenetre (le but est tombe '
    'avant).':
        '{} annullamenti senza gol da togliere in questa finestra (il gol era '
        'arrivato prima).',
    '{} but(s) sans buteur connu, hors classement.':
        '{} gol senza marcatore noto, fuori classifica.',

    # --- --stats -------------------------------------------------------------
    # Les gabarits d'alignement ({:<16} {:>4}) portent la colonne : ils
    # doivent se retrouver a l'identique, largeur comprise.
    'butbutbut : ce que le journal raconte {}':
        'butbutbut : cosa racconta il registro {}',
    '\n  (aucun but debout dans cette fenetre : {} signale(s), {} repris par '
    'la VAR)':
        '\n  (nessun gol valido in questa finestra: {} segnalati, {} '
        'annullati dal VAR)',
    '\nPar minute de match': '\nPer minuto di gioco',
    '  (aucune minute de jeu lisible dans cette fenetre)':
        '  (nessun minuto di gioco leggibile in questa finestra)',
    '\nPar competition': '\nPer competizione',
    '  ... et {} autre(s) competition(s) plus bas.':
        '  ... e altre {} competizioni piu in basso.',
    '\nLes soirees les plus prolifiques': '\nLe serate piu prolifiche',
    '  {:<16} {:>4} but(s)': '  {:<16} {:>4} gol',
    '  ... et {} autre(s) soiree(s) a {} but(s).':
        '  ... e altre {} serate da {} gol.',
    '\nNature des buts': '\nNatura dei gol',
    '\n{} but(s) confirme(s) sur {} signale(s), dans {} competition(s).':
        '\n{} gol confermati su {} segnalati, in {} competizioni.',
    '{} match(s) avec au moins un but signale, {:.1f} but(s) par match.':
        '{} partite con almeno un gol segnalato, {:.1f} gol a partita.',
    'Un 0-0 ne laisse aucune trace dans le journal, ni dans cette moyenne.':
        'Uno 0-0 non lascia traccia nel registro, e nemmeno in questa media.',
    '{} but(s) retire(s) par la VAR, deduit(s) de tout ce qui precede.':
        '{} gol annullati dal VAR, dedotti da tutto quanto precede.',
    '{} but(s) dans le temps additionnel, comptes dans la tranche de leur '
    'minute.':
        '{} gol nel recupero, contati nella fascia del loro minuto.',
    '{} but(s) sans minute de jeu lisible, hors histogramme.':
        '{} gol senza minuto di gioco leggibile, fuori istogramma.',

    # --- --export ------------------------------------------------------------
    # Seules les notes vont sur la sortie d'erreur et se traduisent ; les
    # donnees elles-memes gardent leurs en-tetes anglais, non traduits.
    'butbutbut : export {} {}': 'butbutbut : esportazione {} {}',
    '{} ligne(s) : {} but(s) signale(s) dont {} debout, {} annulation(s).':
        '{} righe: {} gol segnalati di cui {} validi, {} annullamenti.',
    "Le champ 'standing' dit lesquels la VAR a repris.":
        "Il campo 'standing' dice quali il VAR ha annullato.",
    'Journal : {}': 'Registro: {}',
    'butbutbut : export interrompu : {}':
        'butbutbut : esportazione interrotta: {}',

    'butbutbut : competitions surveillables\n':
        'butbutbut : competizioni sorvegliabili\n',

    # --- les matchs de --scores ----------------------------------------------
    '  (aucun match au programme)':
        '  (nessuna partita in programma)',
    '  (aucun match de ces equipes)':
        '  (nessuna partita di queste squadre)',
    'sans spoiler': 'anti-spoiler',
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
