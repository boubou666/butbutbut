"""Catalogue de : le francais en cle, la traduction en valeur.

Une entree absente rend le francais. Les {accolades} sont des trous a valeur :
elles doivent se retrouver a l'identique dans la traduction, sinon le texte
sortira sans sa donnee.

Les gabarits purs ('{:6} {}', 'butbutbut {}'...) n'ont pas d'entree : il n'y
a rien a y traduire, et le francais les rend deja tels quels. CODE et LISTE
non plus : l'allemand les ecrit pareil.

Les etiquettes de --status forment une colonne : le deux-points tombe au meme
caractere qu'en francais, quitte a abreger (Stille, Hook, Stimme, Nachholen,
'Ton je Name'). 'Ohne Spoiler' fait ses douze signes tout juste.

Le fichier est en ASCII pur : on evite un mot quand il demande un trema
('anerkannt' plutot que 'bestaetigt'), et on ne translittere que la ou aucun
substitut n'existe (Torschuetzen, unvollstaendig).

tests/test_i18n.py verifie tout cela phrase par phrase, et refuse une phrase
nouvelle qui ne serait ni traduite ici ni declaree laissee en francais.
"""

MESSAGES = {
    'Exemples :': 'Beispiele:',
    "\n{} match(s), '>' = en cours.": "\n{} Spiel(e), '>' = live.",
    "'?' = sans spoiler : {} match(s) masque(s). Le journal, lui, a tout : "
    'butbutbut --today.':
        "'?' = ohne Spoiler : {} Spiel(e) verdeckt. Die Logdatei hat alles : "
        'butbutbut --today.',
    '  releve      : {}': '  Abfrage     : {}',
    '  buts du jour: {}  (le detail : butbutbut --today)':
        '  Tore heute  : {}  (Details: butbutbut --today)',

    # --- --next --------------------------------------------------------------
    # Une competition qui n'a pas repondu ne fait pas echouer la commande :
    # elle se signale en fin de liste, et le calendrier se dit incomplet.
    'butbutbut : prochains matchs - {}, {} jour(s)':
        'butbutbut : kommende Spiele - {}, {} Tag(e)',
    '\n{} match(s) a venir dans {} competition(s), sur {} jour(s).':
        '\n{} kommende(s) Spiel(e) in {} Wettbewerb(en), verteilt auf {} '
        'Tag(e).',
    "\nAucune competition n'a repondu : rien a annoncer.":
        '\nKein Wettbewerb hat geantwortet : nichts zu melden.',
    '  ({} injoignable : {})': '  ({} nicht erreichbar : {})',
    '  (le calendrier ci-dessus est donc incomplet ; les autres competitions '
    'ont repondu)':
        '  (der Spielplan oben ist also unvollstaendig ; die anderen '
        'Wettbewerbe haben geantwortet)',

    # --- --table -------------------------------------------------------------
    # Le classement d'une competition, pas un palmares de buteurs : les deux
    # mots se separent dans les langues qui les distinguent.
    'butbutbut : classement - {}': 'butbutbut : Tabelle - {}',
    "\nAucune competition n'a repondu : rien a classer.":
        '\nKein Wettbewerb hat geantwortet : nichts zu werten.',
    "  (une coupe se joue en tableau ; hors saison, la source n'a rien a "
    'servir)':
        '  (ein Pokal wird im Turnierbaum gespielt ; ausserhalb der Saison '
        'hat die Quelle nichts zu liefern)',
    '  (le classement ci-dessus est donc incomplet ; les autres competitions '
    'ont repondu)':
        '  (die Tabelle oben ist also unvollstaendig ; die anderen '
        'Wettbewerbe haben geantwortet)',

    # --- la fenetre lue dans le journal --------------------------------------
    # Nommee en tete de --today, --stats, --top-scorers et --export : la meme
    # phrase sert aux quatre, d'ou sa place avant elles.
    'date illisible : {!r}. Format attendu : AAAA-MM-JJ, par exemple --since '
    '{}':
        'unlesbares Datum : {!r}. Erwartetes Format : JJJJ-MM-TT, zum '
        'Beispiel --since {}',
    'depuis le debut du journal': 'seit dem ersten Eintrag',
    'le {}': 'am {}',
    'du {} au {}': 'vom {} bis {}',

    'butbutbut : buts signales le {:%d/%m/%Y}':
        'butbutbut : Tore am {:%d/%m/%Y}',
    'butbutbut : buts signales {}': 'butbutbut : gemeldete Tore {}',
    "\n  (journal vide : aucun but n'y a encore ete ecrit)":
        '\n  (Logdatei leer : es wurde noch kein Tor eingetragen)',
    '\n  (aucun but dans le journal)': '\n  (keine Tore in der Logdatei)',
    '\n{} but(s) dans {} competition(s).': '\n{} Tor(e) in {} Wettbewerb(en).',
    '  daemon      : {}': '  Daemon      : {}',
    '  langue      : {}': '  Sprache     : {}',
    '  suivi       : {}': '  Beobachtet  : {}',
    '  source      : ESPN scoreboard (public, sans cle)':
        '  Quelle      : ESPN Scoreboard (frei, ohne Key)',
    '  cadence     : {}s en direct / {}s au repos':
        '  Intervall   : {}s live / {}s im Leerlauf',
    '  donnees     : {}': '  Daten       : {}',
    '  config      : {}{}': '  Konfig      : {}{}',
    '  sons perso  : {}  ({} fichier(s))':
        '  Ton-Ordner  : {}  ({} Datei(en))',
    "  son nomme   : {} paire(s), le plus precis l'emporte":
        '  Ton je Name : {} Paar(e), das Genaueste gewinnt',

    # Ce que les deux lignes 'son' de --status affichent a droite : quand un
    # son a soi se declenche, d'apres son nom de fichier ou --sound-for.
    'quand une equipe suivie encaisse':
        'wenn ein verfolgtes Team ein Tor kassiert',
    '  (jamais : aucune equipe suivie, voir --teams)':
        '  (nie : kein Team verfolgt, siehe --teams)',
    'les buts de {}': 'die Tore von {}',
    '  (competition non suivie)': '  (Wettbewerb nicht verfolgt)',
    # 'ausgelost' evite le 'zufaellig' qui demanderait un trema.
    'tirage general': 'allgemein ausgelost',
    'et {} autre(s)': 'und {} weitere',
    'quand cette equipe marque': 'wenn dieses Team trifft',

    '  ecussons    : {}': '  Wappen      : {}',
    '  ecrans      : {} -> carte en {} sur {}':
        '  Monitore    : {} -> Karte in {} auf {}',
    '  plein ecran : {}': '  Vollbild    : {}',
    '  journal     : {}': '  Logdatei    : {}',
    '\nExemples :': '\nBeispiele:',
    '  butbutbut --exclude liga,seriea        (les 5 grands moins deux)':
        '  butbutbut --exclude liga,seriea        (die 5 Topligen minus zwei)',
    '  butbutbut --leagues all                (tout le catalogue de football)':
        '  butbutbut --leagues all                (der ganze Fussball-Katalog)',
    '  butbutbut --leagues nhl,top14          (hockey et rugby, a la demande)':
        '  butbutbut --leagues nhl,top14          (Eishockey und Rugby, auf '
        'Wunsch)',
    '  butbutbut --leagues rugby              (tout le rugby du catalogue)':
        '  butbutbut --leagues rugby              (das ganze Rugby im Katalog)',
    '  butbutbut --leagues all-sports         (vraiment tout)':
        '  butbutbut --leagues all-sports         (wirklich alles)',
    "  butbutbut --leagues por.1              (n'importe quel code ESPN)":
        '  butbutbut --leagues por.1              (jeder ESPN-Code)',
    '  butbutbut --leagues hockey:nhl         (... y compris dans un autre '
    'sport)':
        '  butbutbut --leagues hockey:nhl         (... auch in einer anderen '
        'Sportart)',
    'butbutbut : {} ecran(s) detecte(s)': 'butbutbut : {} Monitor(e) erkannt',
    "\nPar defaut la carte s'affiche en bas a droite de l'ecran principal.":
        '\nOhne Angabe erscheint die Karte unten rechts auf dem Hauptmonitor.',
    'La deplacer :  butbutbut --screen 1 --position top-right':
        'Verschieben:   butbutbut --screen 1 --position top-right',

    # --- les demonstrations : --test, --speak, --test-hook -------------------
    # Ce que --test-hook montre a l'ecran est une colonne comme celle de
    # --status : le ' : ' y tombe au meme index.
    'butbutbut : voix - {}': 'butbutbut : Stimme - {}',
    'butbutbut : demo epinglee - [{}] {}':
        'butbutbut : Demo angeheftet - [{}] {}',
    'butbutbut : aucune commande a essayer. Passe --on-goal "...", ou pose la '
    'cle on_goal dans le fichier de configuration.':
        'butbutbut : kein Befehl zum Ausprobieren. Gib --on-goal "..." mit, '
        'oder trage on_goal in die Konfigurationsdatei ein.',
    'butbutbut : but fabrique, la commande recevra':
        'butbutbut : erfundenes Tor, der Befehl bekommt',
    '\n  commande    : {}': '\n  Befehl      : {}',
    '  resultat    : tuee apres {:.0f}s, elle ne rendait pas la main':
        '  Ergebnis    : nach {:.0f}s abgebrochen, sie lief immer weiter',
    '  resultat    : impossible de la lancer ({})':
        '  Ergebnis    : Start fehlgeschlagen ({})',
    '  resultat    : code de sortie {}': '  Ergebnis    : Exit-Code {}',
    '  sortie      :': '  Ausgabe     :',

    'butbutbut {} - mise a jour': 'butbutbut {} - Update',
    ("butbutbut : aucune equipe ne correspond a {} dans {}. Voir 'butbutbut "
     "--list-teams'."):
        ("butbutbut : {} passt zu keinem Team in {}. Siehe 'butbutbut "
         "--list-teams'."),
    '{} - {} equipe(s)': '{} - {} Team(s)',
    "'*' = suivie, '-' = exclue.": "'*' = verfolgt, '-' = ausgeschlossen.",
    "'?' = suivie sans spoiler : journal seulement, ni carte ni son.":
        "'?' = verfolgt, ohne Spoiler : nur Logdatei, weder Karte noch Ton.",
    'butbutbut : demo - [{}] {} - {}': 'butbutbut : Demo - [{}] {} - {}',
    '                etat laisse par un daemon qui ne tourne plus':
        '                Zustand eines Daemons, der nicht mehr aktiv ist',
    '  en cours    : inconnu (le dernier releve est trop vieux)':
        '  Live        : unbekannt (die letzte Abfrage ist zu alt)',
    '  en cours    : {}': '  Live        : {}',
    "\n  (aucun but pour l'instant)": '\n  (noch keine Tore)',
    '\n  (aucun but sur cette periode)': '\n  (in diesem Zeitraum keine Tore)',
    '\nJournal : {}': '\nLogdatei : {}',
    "'-' = but retire par la VAR ({}).": "'-' = Tor vom VAR aberkannt ({}).",
    '\n{} but(s) signale(s), {} jour(s), {} competition(s).':
        '\n{} Tor(e) gemeldet, {} Tag(e), {} Wettbewerb(e).',
    '{} = but retire par la VAR ({}) : {} but(s) confirme(s).':
        '{} = Tor vom VAR aberkannt ({}) : {} anerkannte(s) Tor(e).',
    '  equipes     : {}': '  Teams       : {}',
    '  epinglee    : {}': '  Angeheftet  : {}',
    '  sans spoiler: {}  (journal seulement : ni carte, ni son)':
        '  Ohne Spoiler: {}  (nur Logdatei : weder Karte noch Ton)',
    '  silence     : {}': '  Stille      : {}',
    '  competitions: {}': '  Wettbewerbe : {}',
    '  sports      : {}': '  Sportarten  : {}',
    '  son         : {} ({})': '  Ton         : {} ({})',
    '  lecteur     : winsound + MCI (integres)':
        '  Player      : winsound + MCI (eingebaut)',
    '  lecteur     : {}': '  Player      : {}',
    '  affichage   : tkinter OK': '  Anzeige     : tkinter OK',
    'OK ({} : {} match(s))': 'OK ({} : {} Spiel(e))',
    '  {}  {:<16} {}x{} a +{}+{}{}': '  {}  {:<16} {}x{} bei +{}+{}{}',
    'butbutbut : daemon {} arrete.': 'butbutbut : Daemon {} gestoppt.',
    ('affiche N cartes de demonstration puis quitte (defaut 1 ; --test 3 '
     "montre l'empilement)"):
        ('zeigt N Demo-Karten und beendet sich (Standard 1 ; --test 3 zeigt '
         'den Stapel)'),
    'affiche les matchs du jour dans le terminal puis quitte':
        'zeigt die heutigen Spiele im Terminal und beendet sich',
    'affiche les prochains matchs puis quitte. Sans rien : les {} prochains '
    "jours des competitions suivies. '--next om' cible une equipe, '--next "
    "14' allonge la fenetre ({} au plus)":
        'zeigt die kommenden Spiele und beendet sich. Ohne Angabe : die '
        "kommenden {} Tage der verfolgten Wettbewerbe. '--next om' zielt auf "
        "ein Team, '--next 14' dehnt das Fenster aus (maximal {})",
    'COMPETITION|EQUIPE': 'WETTBEWERB|TEAM',
    'affiche le classement puis quitte. Sans rien : les competitions suivies. '
    "'--table l1' cible une competition, '--table om' surligne une equipe "
    'dans la sienne, et les deux se combinent':
        'zeigt die Tabelle und beendet sich. Ohne Angabe : die verfolgten '
        "Wettbewerbe. '--table l1' zielt auf einen Wettbewerb, '--table om' "
        'hebt ein Team in seinem eigenen Wettbewerb hervor, und beides geht '
        'zusammen',
    ("affiche l'etat (daemon, dernier releve, matchs en cours, son, ecrans, "
     'connexion)'):
        ('zeigt den Zustand (Daemon, letzte Abfrage, laufende Spiele, Ton, '
         'Monitore, Verbindung)'),
    "recapitule les buts signales aujourd'hui":
        'fasst die heute gemeldeten Tore zusammen',
    "recapitule les buts des {} derniers jours (aujourd'hui compris)":
        'fasst die Tore der letzten {} Tage zusammen (heute eingeschlossen)',
    'recapitule les buts des {} derniers jours':
        'fasst die Tore der letzten {} Tage zusammen',
    'recapitule les buts depuis ce jour, au format AAAA-MM-JJ. Ex : --since '
    "2026-09-01. L'emporte sur --week et --month.":
        'fasst die Tore ab diesem Tag zusammen, im Format JJJJ-MM-TT. Bsp : '
        '--since 2026-09-01. Hat Vorrang vor --week und --month.',
    'classe les buteurs vus passer, buts annules par la VAR deduits. Sur tout '
    'le journal, ou sur la fenetre de --week, --month ou --since':
        'wertet die gesehenen Torschuetzen, vom VAR aberkannte Tore '
        'abgezogen. In der ganzen Logdatei, oder im Fenster von --week, '
        '--month oder --since',
    'les formes cachees dans le journal : les buts par minute de match '
    '(histogramme), par competition, les soirees les plus prolifiques. Meme '
    'fenetre et memes filtres que --top-scorers':
        'die verborgenen Formen in der Logdatei : die Tore nach Spielminute '
        '(Histogramm), nach Wettbewerb, die torreichsten Abende. Gleiches '
        'Fenster und gleiche Filter wie --top-scorers',
    'ecrit les buts du journal en donnees sur la sortie standard, pour un '
    'tableur ou un script. Memes fenetres et memes filtres que --stats. Ex : '
    'butbutbut --export csv --month > buts.csv':
        'schreibt die Tore der Logdatei als Daten auf die Standardausgabe, '
        'zur Nutzung in einer Tabelle oder einem Skript. Gleiche Fenster und '
        'gleiche Filter wie --stats. Bsp : butbutbut --export csv --month > '
        'buts.csv',
    'arrete le daemon en cours': 'stoppt den laufenden Daemon',
    'affiche les chemins utilises': 'zeigt die verwendeten Pfade',
    'liste les ecrans detectes': 'listet die erkannten Monitore',
    "met a jour butbutbut depuis GitHub et rejoue l'installeur":
        'aktualisiert butbutbut von GitHub und startet den Installer neu',
    'dit si une version plus recente existe, sans rien installer':
        'sagt, ob eine neuere Version existiert, ohne etwas zu installieren',
    ('avec --update ou --check-update : viser la pointe de la branche '
     'principale au lieu de la derniere release'):
        ('mit --update oder --check-update : auf die Spitze des Hauptbranch '
         'zielen statt auf das letzte Release'),
    'FICHIER': 'DATEI',
    'surveille normalement, et ecrit en plus chaque reponse brute de la '
    "source dans FICHIER (JSON Lines ; un nom en .gz est compresse). C'est ce "
    'que --replay rejoue.':
        'beobachtet normal, und schreibt ausserdem jede rohe Antwort der '
        'Quelle in DATEI (JSON Lines ; ein Name mit .gz wird komprimiert). '
        'Genau das spielt --replay ab.',
    'rejoue un enregistrement : memes cartes, meme son, meme journal, sans '
    "reseau. Ni le journal ni l'etat du vrai daemon ne sont touches.":
        'spielt eine Aufzeichnung ab : gleiche Karten, gleicher Ton, gleiche '
        'Logdatei, ohne Netz. Weder die Logdatei noch der Zustand des echten '
        'Daemons werden angetastet.',
    'avec --replay : divise les ecarts de temps par N (defaut 1 ; 60 = une '
    'heure de match en une minute)':
        'mit --replay : teilt die Wartezeiten durch N (Standard 1 ; 60 = eine '
        'Stunde Spiel in einer Minute)',
    ('fichier de configuration a lire (defaut : {} dans le dossier de '
     "donnees, voir 'butbutbut --paths')"):
        ('zu lesende Konfigurationsdatei (Standard : {} im Datenordner, '
         "siehe 'butbutbut --paths')"),
    ("ecrit un fichier de configuration d'exemple, commente, puis quitte "
     "(n'ecrase rien)"):
        ('schreibt eine kommentierte Beispiel-Konfiguration und beendet sich '
         '(eine vorhandene Datei bleibt)'),
    'competitions suivies, separees par des virgules (defaut : les 5 grands '
    "championnats de football). Ex : --leagues l1,pl,ucl ; 'all' pour tout le "
    "catalogue de football, 'hockey' ou 'rugby' pour un autre sport entier, "
    "'all-sports' pour tout ; un code ESPN marche aussi (por.1, hockey:nhl)":
        'verfolgte Wettbewerbe, mit Komma getrennt (Standard : die 5 Topligen '
        "des Fussballs). Bsp : --leagues l1,pl,ucl ; 'all' nimmt den ganzen "
        "Fussball-Katalog, 'hockey' oder 'rugby' eine ganze andere Sportart, "
        "'all-sports' alles ; ein ESPN-Code geht auch (por.1, hockey:nhl)",
    'competitions a ne pas suivre, meme syntaxe. Ex : --exclude liga,seriea':
        ('Wettbewerbe, die nicht verfolgt werden, gleiche Syntax. Bsp : '
         '--exclude liga,seriea'),
    'liste les competitions surveillables et leurs noms':
        'listet die verfolgbaren Wettbewerbe und ihre Namen',
    ('ne signaler que les matchs de ces equipes, separees par des virgules. '
     "Un match compte des qu'une des deux equipes y est. Ex : --teams om,psg"):
        ('nur Spiele dieser Teams melden, mit Komma getrennt. Ein Spiel gilt '
         'schon, wenn eines der beiden Teams dabei ist. Bsp : --teams om,psg'),
    'ne rien signaler des matchs de ces equipes':
        'nichts aus Spielen dieser Teams melden',
    "garde a l'ecran une carte qui suit les matchs de cette equipe : elle "
    "apparait au coup d'envoi, se met a jour a chaque releve et s'en va "
    'quelques minutes apres la fin. Une seule equipe, et jamais de son. Ex : '
    '--pin om':
        'zeigt dauerhaft eine Karte, die den Spielen dieses Teams folgt : sie '
        'erscheint beim Anpfiff, wird bei jeder Abfrage aktualisiert und geht '
        'einige Minuten nach dem Ende. Nur ein Team, und nie mit Ton. Bsp : '
        '--pin om',
    'matchs regardes en differe : aucune carte ni aucun son pour ces equipes, '
    "quel que soit l'evenement. Le journal, lui, garde tout (butbutbut "
    '--today). Ex : --spoiler-free om':
        'zeitversetzt geschaute Spiele : keine Karte und kein Ton bei diesen '
        'Teams, egal bei welchem Ereignis. Die Logdatei hat weiter alles '
        '(butbutbut --today). Bsp : --spoiler-free om',
    'liste les equipes des competitions suivies':
        'listet die Teams der verfolgten Wettbewerbe',
    'secondes entre deux releves quand un match est en cours (defaut {})':
        ('Sekunden zwischen zwei Abfragen, solange ein Spiel live ist '
         '(Standard {})'),
    "secondes entre deux releves quand il n'y a rien a suivre (defaut {})":
        ('Sekunden zwischen zwei Abfragen, wenn es nichts zu verfolgen gibt '
         '(Standard {})'),
    "duree d'affichage de la carte (defaut : la duree du son, au moins {})":
        ('Anzeigedauer der Karte (Standard : die Dauer des Tons, mindestens '
         '{})'),
    ("coin ou les cartes s'empilent : bottom-right (defaut), bottom-left, "
     'top-right, top-left, center'):
        ('Ecke, in der sich die Karten stapeln : bottom-right (Standard), '
         'bottom-left, top-right, top-left, center'),
    ("ecran d'affichage : 'primary' (defaut) ou un index (0, 1, 2...). Voir "
     "'butbutbut --screens'."):
        ("Monitor der Anzeige : 'primary' (Standard) oder ein Index (0, 1, "
         "2...). Siehe 'butbutbut --screens'."),
    'taille de la carte (1.0 par defaut, 1.5 = plus grande)':
        'Kartenskalierung (Standard 1.0, 1.5 = 150 Prozent)',
    'opacite, 0.0 a 1.0': 'Deckkraft, 0.0 bis 1.0',
    'pas de carte : seulement le son et le journal':
        'keine Karte : nur Ton und Logdatei',
    ("pas de carte au coup d'envoi, a la mi-temps, a la reprise ni a la fin "
     'du match (les buts, si)'):
        ('keine Karte bei Anpfiff, Halbzeit, Wiederanpfiff und Abpfiff (Tore '
         'schon)'),
    # La phrase nomme la metavariable : SEKUNDEN, comme --help l'affiche.
    # Elle disait SECONDES, et renvoyait donc a un mot absent de la page.
    ("quand une application en plein ecran masque l'ecran, repasser la carte "
     "des que l'ecran se libere, pendant SECONDES au plus (defaut {:.0f} ; "
     'Windows uniquement, voir README)'):
        ('wenn eine Vollbild-Anwendung den Bildschirm verdeckt, die Karte '
         'erneut zeigen, sobald er wieder frei ist, maximal SEKUNDEN lang '
         '(Standard {:.0f} ; nur Windows, siehe README)'),
    'PLAGE': 'ZEITRAUM',
    "plage horaire ou rien ne s'affiche et rien ne sonne, au format {} (ex : "
    '{}). Le but tombe quand meme dans le journal, et --today le retrouve. '
    "L'heure est celle de la machine, la plage peut enjamber minuit.":
        'Zeitraum, in dem nichts erscheint und nichts klingt, im Format {} '
        '(Bsp : {}). Das Tor kommt trotzdem in die Logdatei, und --today '
        'findet es wieder. Die Uhrzeit ist die des Rechners, der Zeitraum '
        'kann Mitternacht einschliessen.',
    "se taire aussi quand le systeme signale qu'on presente : mode "
    "presentation, ecran duplique ou 'ne pas deranger'. Windows uniquement ; "
    "un partage de fenetre Teams/Zoom n'est pas detectable, voir README":
        'auch schweigen, wenn das System eine Praesentation meldet : '
        "Praesentationsmodus, geklonter Bildschirm oder 'Nicht stoeren'. Nur "
        'Windows ; ein geteiltes Teams/Zoom-Fenster ist nicht erkennbar, '
        'siehe README',
    'signale aussi les cartons rouges, par une carte discrete et sans son':
        'meldet auch Rote Karten, mit einer dezenten Einblendung und ohne Ton',
    ("annonce le match ce nombre de minutes avant le coup d'envoi, une seule "
     'fois et sans son (0 = desactive, defaut)'):
        ('meldet das Spiel so viele Minuten vor dem Anpfiff, einmalig und '
         'ohne Ton (0 = aus, Standard)'),
    'au reveil apres une veille, resume en une carte muette les buts tombes '
    "pendant l'absence (par defaut le reveil reste silencieux)":
        'beim Aufwachen aus dem Ruhezustand : eine stumme Karte fasst die '
        'Tore der Abwesenheit zusammen (ohne Angabe bleibt das Aufwachen '
        'still)',
    'COMMANDE': 'BEFEHL',
    'commande a lancer a chaque but, avec le detail du but dans des variables '
    "d'environnement BUT_* (voir --test-hook et le README)":
        'Befehl, der bei jedem Tor startet, mit den Einzelheiten des Tors in '
        'Umgebungsvariablen BUT_* (siehe --test-hook und README)',
    'essaie la commande de --on-goal sur un but fabrique, et montre ce '
    "qu'elle rend":
        'probiert den Befehl von --on-goal an einem erfundenen Tor aus, und '
        'zeigt, was er liefert',
    ('langue des cartes : fr, en, es, it, de (defaut : celle du systeme, '
     'francais a defaut). Le journal, lui, reste toujours en francais.'):
        ('Sprache der Karten : fr, en, es, it, de (Standard : die des '
         'Systems, sonst Franzoesisch). Die Logdatei bleibt franzoesisch.'),
    ("pas d'ecusson sur les cartes, et rien de telecharge (les couleurs des "
     'clubs restent)'):
        ('kein Wappen auf den Karten, und nichts wird geladen (die '
         'Vereinsfarben bleiben)'),
    'mode muet': 'stumm',
    'dit le but a voix haute, en plus du son (ou a sa place avec --no-sound). '
    "La phrase est celle des cartes, dans leur langue. 'butbutbut --test "
    "--speak' l'essaie tout de suite.":
        'sagt das Tor laut an, zusammen mit dem Ton (oder an seiner Stelle '
        'mit --no-sound). Es ist der Satz der Karten, in ihrer Sprache. '
        "'butbutbut --test --speak' probiert es sofort aus.",
    'volume de la corne synthetisee, 0.0 a 1.0':
        'Pegel der erzeugten Fanfare, 0.0 bis 1.0',
    'PAIRES': 'PAARE',
    'un son a soi pour une equipe ou une competition, sous forme de paires '
    'nom=chemin separees par des virgules. Les noms sont ceux de --teams et '
    "de --leagues, et l'equipe l'emporte sur sa competition. Un chemin fautif "
    'est refuse au demarrage. Ex : --sound-for om=~/sons/om.wav':
        'ein eigener Ton je Team oder Wettbewerb, als Paare name=pfad, mit '
        'Komma getrennt. Die Namen sind die von --teams und --leagues, und '
        'das Team gewinnt gegen seinen Wettbewerb. Ein falscher Pfad wird '
        'beim Start abgelehnt. Bsp : --sound-for om=~/sons/om.wav',
    'regenere la corne synthetisee': 'erzeugt die Fanfare neu',
    "n'ecrit que dans le journal": 'schreibt nur in die Logdatei',
    "butbutbut : --pin ne prend qu'une equipe ({!r} en annonce plusieurs) : "
    "il n'y a jamais qu'une carte epinglee.":
        'butbutbut : --pin nimmt nur ein Team ({!r} nennt mehrere) : es gibt '
        'immer nur eine angeheftete Karte.',
    'butbutbut : position inconnue : {} (voir --help)':
        'butbutbut : unbekannte Position : {} (siehe --help)',
    'butbutbut : corne regeneree -> {}':
        'butbutbut : Fanfare neu erzeugt -> {}',
    '  (la source ne publie pas de liste pour cette competition)':
        '  (die Quelle hat zu diesem Wettbewerb keine Liste)',
    ('                (!) plus rien depuis, alors que la cadence est de {}s : '
     'daemon bloque ou source injoignable ?'):
        ('                (!) seitdem nichts mehr, obwohl das Intervall {}s '
         'ist : Daemon blockiert oder Quelle nicht erreichbar ?'),
    'actif (pid {})': 'aktiv (pid {})',
    'arrete': 'gestoppt',
    'desactives (--no-logos)': 'deaktiviert (--no-logos)',
    '{}  ({} en cache)': '{}  ({} im Cache)',
    "l'ecran principal": 'dem Hauptmonitor',
    'ecran {}': 'Monitor {}',
    '  rattrapage  : {}': '  Nachholen   : {}',
    'actif (une carte de resume au reveil, sans son)':
        'aktiv (eine Zusammenfassung als Karte beim Aufwachen, ohne Ton)',
    'inactif (le reveil reste silencieux, voir --catch-up)':
        'inaktiv (das Aufwachen bleibt still, siehe --catch-up)',
    '  affichage   : tkinter MANQUANT (voir README)':
        '  Anzeige     : tkinter FEHLT (siehe README)',
    'ECHEC ({})': 'FEHLER ({})',
    "butbutbut : impossible d'arreter {} : {}":
        'butbutbut : Stoppen von {} fehlgeschlagen : {}',
    'butbutbut : dossier de donnees inutilisable : {}':
        'butbutbut : Datenordner nicht nutzbar : {}',
    'injoignable ({})': 'nicht erreichbar ({})',

    # --- les valeurs, et plus seulement les libelles -------------------------
    # Une ligne de --status traduite dont la valeur reste francaise se lit a
    # moitie : l'age du dernier releve, l'origine du son, l'etat du plein
    # ecran passent donc ici aussi.
    'il y a {} s': 'vor {} s',
    'il y a {} min': 'vor {} Min',
    'il y a {} h {:02d}': 'vor {} h {:02d}',
    'date inconnue': 'Zeitpunkt unbekannt',
    # Valeurs de la ligne 'Abfrage' : feminin en allemand, d'ou 'keine'.
    "aucun pour l'instant": 'noch keine',
    "aucun (le daemon efface son etat en s'arretant)":
        'keine (der Daemon entfernt seinen Zustand beim Stoppen)',
    '  (absent, voir --write-config)': '  (fehlt, siehe --write-config)',
    '  crochet     : {}': '  Hook        : {}',
    '{}  (essai : --test-hook)': '{}  (Probe : --test-hook)',
    'aucun (voir --on-goal)': 'keiner (siehe --on-goal)',
    '  voix        : {}': '  Stimme      : {}',
    '  son         : {} fichier(s), le nom dit quand ils jouent':
        '  Ton         : {} Datei(en), der Name sagt, wann sie spielen',
    'fourni': 'mitgeliefert',
    'corne synthetisee': 'erzeugte Fanfare',
    'AUCUN (installe mpv/ffmpeg/pipewire/alsa-utils)':
        'KEINER (mpv/ffmpeg/pipewire/alsa-utils installieren)',
    'detecte (la carte masquee est notee au journal)':
        'erkannt (eine verdeckte Karte kommt in die Logdatei)',
    'non detectable sur cette plateforme':
        'auf dieser Plattform nicht erkennbar',
    '{} match(s)': '{} Spiel(e)',
    ' sur {} au programme': ' von {} angesetzten',
    # 'Verbindung' fait un signe de plus que 'Connexion' : une espace de moins
    # avant le deux-points, et la colonne de --status ne bouge pas.
    '\n  Connexion   : ': '\n  Verbindung  : ',

    # --- l'etat des matchs, colonne de droite de --scores --------------------
    'en cours': 'live',
    'termine': 'beendet',
    'a venir': 'geplant',
    'imminent': 'gleich',
    'dans {} min': 'in {} Min',
    '  (aucun match au programme)': '  (keine Spiele angesetzt)',
    '  (aucun match de ces equipes)': '  (keine Spiele dieser Teams)',
    'sans spoiler': 'ohne Spoiler',

    # --- les ecrans ----------------------------------------------------------
    '1 ecran ({}x{})': '1 Monitor ({}x{})',
    '{} ecrans [{}]': '{} Monitore [{}]',
    '  (principal)': '  (Hauptmonitor)',

    # --- le catalogue de competitions ---------------------------------------
    'les 5 grands championnats': 'die 5 Topligen',
    'tout le catalogue ({} competitions)':
        'der ganze Katalog ({} Wettbewerbe)',
    # "tout le {} ({} competitions)" n'a pas d'entree : le trou y recoit le nom
    # du sport, que sports.py garde en francais pour le journal. La traduire
    # ferait une phrase a moitie allemande ; celle-ci, non.
    'tous les sports ({} competitions)': 'alle Sportarten ({} Wettbewerbe)',
    '{} et {} autres': '{} und {} weitere',
    'Les 5 grands (defaut)': 'Die 5 Topligen (Standard)',
    # 'Ausserdem verfuegbar' demanderait deux tremas et un eszett.
    'Aussi disponibles': 'Weitere Wettbewerbe',
    'Hockey sur glace (a demander)': 'Eishockey (auf Wunsch)',
    'Rugby a XV (a demander)': 'Rugby Union (auf Wunsch)',

    # --- --top-scorers -------------------------------------------------------
    # Les buts repris par la VAR sont deduits : le compte affiche n'est pas
    # celui des lignes du journal, et la note le dit.
    'butbutbut : buteurs vus passer {}':
        'butbutbut : gesehene Torschuetzen {}',
    "\n  (aucun buteur connu : la source n'avait pas encore publie l'action)":
        '\n  (kein Torschuetze bekannt : die Quelle hatte die Aktion noch '
        'nicht veroeffentlicht)',
    '  ... et {} autre(s) buteur(s) plus bas au classement.':
        '  ... und {} weitere(r) Torschuetze(n) weiter unten in der Wertung.',
    '\n{} buteur(s) pour {} but(s) confirme(s) sur {} signale(s).':
        '\n{} Torschuetze(n), {} anerkannte(s) Tor(e) von {} gemeldeten.',
    '{} but(s) retire(s) par la VAR, deduit(s) du classement.':
        '{} Tor(e) vom VAR aberkannt, aus der Wertung abgezogen.',
    '{} annulation(s) sans but a retirer dans cette fenetre (le but est tombe '
    'avant).':
        '{} Aberkennung(en) ohne passendes Tor in diesem Zeitraum (das Tor '
        'fiel davor).',
    '{} but(s) sans buteur connu, hors classement.':
        '{} Tor(e) ohne bekannten Torschuetzen, nicht in der Wertung.',

    # --- --stats -------------------------------------------------------------
    # Les gabarits d'alignement ({:<16} {:>4}) portent la colonne : ils
    # doivent se retrouver a l'identique, largeur comprise.
    'butbutbut : ce que le journal raconte {}':
        'butbutbut : was die Logdatei berichtet {}',
    '\n  (aucun but debout dans cette fenetre : {} signale(s), {} repris par '
    'la VAR)':
        '\n  (kein anerkanntes Tor in diesem Zeitraum : {} gemeldet, {} vom '
        'VAR aberkannt)',
    '\nPar minute de match': '\nNach Spielminute',
    '  (aucune minute de jeu lisible dans cette fenetre)':
        '  (keine lesbare Spielminute in diesem Zeitraum)',
    '\nPar competition': '\nNach Wettbewerb',
    '  ... et {} autre(s) competition(s) plus bas.':
        '  ... und {} weitere(r) Wettbewerb(e) weiter unten.',
    '\nLes soirees les plus prolifiques': '\nDie torreichsten Abende',
    '  {:<16} {:>4} but(s)': '  {:<16} {:>4} Tor(e)',
    '  ... et {} autre(s) soiree(s) a {} but(s).':
        '  ... und {} weitere(r) Abend(e) mit {} Tor(en).',
    '\nNature des buts': '\nArt der Tore',
    '\n{} but(s) confirme(s) sur {} signale(s), dans {} competition(s).':
        '\n{} anerkannte(s) Tor(e) von {} gemeldeten, in {} Wettbewerb(en).',
    '{} match(s) avec au moins un but signale, {:.1f} but(s) par match.':
        '{} Spiel(e) mit mindestens einem gemeldeten Tor, {:.1f} Tor(e) pro '
        'Spiel.',
    'Un 0-0 ne laisse aucune trace dans le journal, ni dans cette moyenne.':
        'Ein 0:0 steht nicht in der Logdatei, und damit auch nicht in diesem '
        'Schnitt.',
    '{} but(s) retire(s) par la VAR, deduit(s) de tout ce qui precede.':
        '{} Tor(e) vom VAR aberkannt, von allem oben abgezogen.',
    '{} but(s) dans le temps additionnel, comptes dans la tranche de leur '
    'minute.':
        '{} Tor(e) in der Nachspielzeit, in den Abschnitt ihrer Minute '
        'gerechnet.',
    '{} but(s) sans minute de jeu lisible, hors histogramme.':
        '{} Tor(e) ohne lesbare Spielminute, nicht im Histogramm.',

    # --- --export ------------------------------------------------------------
    # Seules les notes vont sur la sortie d'erreur et se traduisent ; les
    # donnees elles-memes gardent leurs en-tetes anglais, non traduits.
    'butbutbut : export {} {}': 'butbutbut : Export {} {}',
    '{} ligne(s) : {} but(s) signale(s) dont {} debout, {} annulation(s).':
        '{} Zeile(n) : {} gemeldete(s) Tor(e), davon {} anerkannt, {} '
        'Aberkennung(en).',
    "Le champ 'standing' dit lesquels la VAR a repris.":
        "Das Feld 'standing' sagt, welche der VAR aberkannt hat.",
    'Journal : {}': 'Logdatei : {}',
    'butbutbut : export interrompu : {}':
        'butbutbut : Export abgebrochen : {}',

    'butbutbut : competitions surveillables\n':
        'butbutbut : verfolgbare Wettbewerbe\n',
    'butbutbut : aucun daemon en cours.': 'butbutbut : kein Daemon aktiv.',

    # --- l'en-tete de --help -------------------------------------------------
    # Le verbe francais ('tombe') n'a pas d'equivalent sans trema ('faellt') :
    # la phrase allemande se passe donc de verbe pour son sujet.
    'Un but tombe en Ligue 1, Premier League, LaLiga, Serie A ou Bundesliga : '
    "le son part et le score s'affiche a l'ecran. Le hockey et le rugby sont "
    'dans le catalogue, a la demande (voir --list).':
        'Ein Tor in der Ligue 1, Premier League, LaLiga, Serie A oder '
        'Bundesliga : der Ton geht los und der Spielstand erscheint auf dem '
        'Bildschirm. Eishockey und Rugby stehen im Katalog, auf Wunsch (siehe '
        '--list).',

    # --- les metavariables de --help ----------------------------------------
    # CODE et LISTE s'ecrivent pareil en allemand : pas d'entree.
    'CHEMIN': 'PFAD',
    'DATE': 'DATUM',
    'EQUIPE': 'TEAM',
    'EQUIPE|JOURS': 'TEAM|TAGE',
    'COIN': 'ECKE',
    'CHOIX': 'AUSWAHL',
    'SECONDES': 'SEKUNDEN',
    'MINUTES': 'MINUTEN',
    'francais': 'Franzoesisch',
    'anglais': 'Englisch',
    'espagnol': 'Spanisch',
    'italien': 'Italienisch',
    'allemand': 'Deutsch',
    'aucune competition selectionnee.': 'kein Wettbewerb angegeben.',
    'plus aucune competition a surveiller apres exclusion.':
        'nach dem Ausschluss bleibt nichts zu beobachten.',
    'butbutbut : impossible de verifier les equipes (source injoignable), on continue sans verification.':
        'butbutbut : Teams lassen sich nicht kontrollieren (Quelle nicht erreichbar), es geht ohne Kontrolle weiter.',
}
