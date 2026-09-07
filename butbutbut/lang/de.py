"""Catalogue de : le francais en cle, la traduction en valeur.

Une entree absente rend le francais. Les {accolades} sont des trous a valeur :
elles doivent se retrouver a l'identique dans la traduction, sinon le texte
sortira sans sa donnee.

Les gabarits purs ('{:6} {}', 'butbutbut {}'...) n'ont pas d'entree : il n'y
a rien a y traduire, et le francais les rend deja tels quels.
"""

MESSAGES = {
    'Exemples :': 'Beispiele:',
    "\n{} match(s), '>' = en cours.": "\n{} Spiel(e), '>' = live.",
    '  releve      : {}': '  Abfrage     : {}',
    '  buts du jour: {}  (le detail : butbutbut --today)':
        '  Tore heute  : {}  (Details: butbutbut --today)',
    'butbutbut : buts signales le {:%d/%m/%Y}':
        'butbutbut : Tore am {:%d/%m/%Y}',
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
    '  ecussons    : {}': '  Wappen      : {}',
    '  ecrans      : {} -> carte en {} sur {}':
        '  Monitore    : {} -> Karte in {} auf {}',
    '  plein ecran : {}': '  Vollbild    : {}',
    '  journal     : {}': '  Logdatei    : {}',
    '\nExemples :': '\nBeispiele:',
    '  butbutbut --exclude liga,seriea        (les 5 grands moins deux)':
        '  butbutbut --exclude liga,seriea        (die 5 Topligen minus zwei)',
    '  butbutbut --leagues all                (tout le catalogue)':
        '  butbutbut --leagues all                (der ganze Katalog)',
    "  butbutbut --leagues por.1              (n'importe quel code ESPN)":
        '  butbutbut --leagues por.1              (jeder ESPN-Code)',
    'butbutbut : {} ecran(s) detecte(s)': 'butbutbut : {} Monitor(e) erkannt',
    "\nPar defaut la carte s'affiche en bas a droite de l'ecran principal.":
        '\nOhne Angabe erscheint die Karte unten rechts auf dem Hauptmonitor.',
    'La deplacer :  butbutbut --screen 1 --position top-right':
        'Verschieben:   butbutbut --screen 1 --position top-right',
    'butbutbut {} - mise a jour': 'butbutbut {} - Update',
    ("butbutbut : aucune equipe ne correspond a {} dans {}. Voir 'butbutbut "
     "--list-teams'."):
        ("butbutbut : {} passt zu keinem Team in {}. Siehe 'butbutbut "
         "--list-teams'."),
    '{} - {} equipe(s)': '{} - {} Team(s)',
    "'*' = suivie, '-' = exclue.": "'*' = verfolgt, '-' = ausgeschlossen.",
    'butbutbut : demo - [{}] {} - {}': 'butbutbut : Demo - [{}] {} - {}',
    '                etat laisse par un daemon qui ne tourne plus':
        '                Zustand eines Daemons, der nicht mehr aktiv ist',
    '  en cours    : inconnu (le dernier releve est trop vieux)':
        '  Live        : unbekannt (die letzte Abfrage ist zu alt)',
    '  en cours    : {}': '  Live        : {}',
    "\n  (aucun but pour l'instant)": '\n  (noch keine Tore)',
    '\nJournal : {}': '\nLogdatei : {}',
    "'-' = but retire par la VAR ({}).": "'-' = Tor vom VAR aberkannt ({}).",
    '  equipes     : {}': '  Teams       : {}',
    '  competitions: {}': '  Wettbewerbe : {}',
    '  son         : {}{}': '  Ton         : {}{}',
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
    ("affiche l'etat (daemon, dernier releve, matchs en cours, son, ecrans, "
     'connexion)'):
        ('zeigt den Zustand (Daemon, letzte Abfrage, laufende Spiele, Ton, '
         'Monitore, Verbindung)'),
    "recapitule les buts signales aujourd'hui":
        'fasst die heute gemeldeten Tore zusammen',
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
    ('fichier de configuration a lire (defaut : {} dans le dossier de '
     "donnees, voir 'butbutbut --paths')"):
        ('zu lesende Konfigurationsdatei (Standard : {} im Datenordner, '
         "siehe 'butbutbut --paths')"),
    ("ecrit un fichier de configuration d'exemple, commente, puis quitte "
     "(n'ecrase rien)"):
        ('schreibt eine kommentierte Beispiel-Konfiguration und beendet sich '
         '(eine vorhandene Datei bleibt)'),
    ('competitions suivies, separees par des virgules (defaut : les 5 grands '
     "championnats). Ex : --leagues l1,pl,ucl ; 'all' pour tout le catalogue "
     '; un code ESPN marche aussi (por.1)'):
        ('verfolgte Wettbewerbe, mit Komma getrennt (Standard : die 5 '
         "Topligen). Bsp : --leagues l1,pl,ucl ; 'all' nimmt den ganzen "
         'Katalog ; ein ESPN-Code geht auch (por.1)'),
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
    ("quand une application en plein ecran masque l'ecran, repasser la carte "
     "des que l'ecran se libere, pendant SECONDES au plus (defaut {:.0f} ; "
     'Windows uniquement, voir README)'):
        ('wenn eine Vollbild-Anwendung den Bildschirm verdeckt, die Karte '
         'erneut zeigen, sobald er wieder frei ist, maximal SECONDES lang '
         '(Standard {:.0f} ; nur Windows, siehe README)'),
    'signale aussi les cartons rouges, par une carte discrete et sans son':
        'meldet auch Rote Karten, mit einer dezenten Einblendung und ohne Ton',
    ("annonce le match ce nombre de minutes avant le coup d'envoi, une seule "
     'fois et sans son (0 = desactive, defaut)'):
        ('meldet das Spiel so viele Minuten vor dem Anpfiff, einmalig und '
         'ohne Ton (0 = aus, Standard)'),
    ('langue des cartes : fr, en, es, it, de (defaut : celle du systeme, '
     'francais a defaut). Le journal, lui, reste toujours en francais.'):
        ('Sprache der Karten : fr, en, es, it, de (Standard : die des '
         'Systems, sonst Franzoesisch). Die Logdatei bleibt franzoesisch.'),
    ("pas d'ecusson sur les cartes, et rien de telecharge (les couleurs des "
     'clubs restent)'):
        ('kein Wappen auf den Karten, und nichts wird geladen (die '
         'Vereinsfarben bleiben)'),
    'mode muet': 'stumm',
    'volume de la corne synthetisee, 0.0 a 1.0':
        'Pegel der erzeugten Fanfare, 0.0 bis 1.0',
    'regenere la corne synthetisee': 'erzeugt die Fanfare neu',
    "n'ecrit que dans le journal": 'schreibt nur in die Logdatei',
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
    'fourni': 'mitgeliefert',
    'corne synthetisee': 'erzeugte Fanfare',
    # 'ausgelost' evite le 'zufaellig' qui demanderait un trema.
    ' (+{} autre(s), tirage au hasard)': ' (+{} weitere, eine wird ausgelost)',
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

    # --- les ecrans ----------------------------------------------------------
    '1 ecran ({}x{})': '1 Monitor ({}x{})',
    '{} ecrans [{}]': '{} Monitore [{}]',
    '  (principal)': '  (Hauptmonitor)',

    # --- le catalogue de competitions ---------------------------------------
    'les 5 grands championnats': 'die 5 Topligen',
    'tout le catalogue ({} competitions)':
        'der ganze Katalog ({} Wettbewerbe)',
    '{} et {} autres': '{} und {} weitere',
    'Les 5 grands (defaut)': 'Die 5 Topligen (Standard)',
    # 'Ausserdem verfuegbar' demanderait deux tremas et un eszett.
    'Aussi disponibles': 'Weitere Wettbewerbe',
    'butbutbut : competitions surveillables\n':
        'butbutbut : verfolgbare Wettbewerbe\n',
    'butbutbut : aucun daemon en cours.': 'butbutbut : kein Daemon aktiv.',

    # --- l'en-tete de --help -------------------------------------------------
    # Le verbe francais ('tombe') n'a pas d'equivalent sans trema ('faellt') :
    # la phrase allemande se passe donc de verbe pour son sujet.
    ('Un but tombe en Ligue 1, Premier League, LaLiga, Serie A ou Bundesliga '
     ": le son part et le score s'affiche a l'ecran."):
        ('Ein Tor in Ligue 1, Premier League, LaLiga, Serie A oder Bundesliga '
         ': der Ton geht los und der Spielstand erscheint auf dem '
         'Bildschirm.'),

    # --- les metavariables de --help ----------------------------------------
    # CODE et LISTE s'ecrivent pareil en allemand : pas d'entree.
    'CHEMIN': 'PFAD',
    'COIN': 'ECKE',
    'CHOIX': 'AUSWAHL',
    'SECONDES': 'SEKUNDEN',
    'MINUTES': 'MINUTEN',
}
