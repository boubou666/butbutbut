"""Catalogue es : le francais en cle, la traduction en valeur.

Une entree absente rend le francais. Les {accolades} sont des trous a valeur :
elles doivent se retrouver a l'identique dans la traduction, sinon le texte
sortira sans sa donnee.

Deux contraintes ont guide le choix des mots :

  - les etiquettes de --status forment une colonne. Le " : " doit tomber au
    meme index qu'en francais : les libelles espagnols trop longs sont abreges
    ("competic.", "p. completa") plutot que de decaler leur ligne ;
  - le depot est en ASCII pur. Les tournures evitent les diacritiques quand
    elles le peuvent ("escala" et non "tamano"), et les accents restants
    tombent, comme le francais du projet le fait deja.

Les libelles ne suffisent pas : ce que --status, --scores et --list affichent
dans leurs colonnes est une valeur, pas un gabarit. "il y a 12 s", "en cours",
"les 5 grands championnats" viennent de state, espn et leagues, et se
traduisent ici comme le reste, sans quoi une ligne espagnole finirait sur un
mot francais.

Les phrases que l'espagnol laisse identiques - le nom du programme,
"(principal)", les etiquettes deja espagnoles ("config", "daemon"), les
gabarits purement typographiques ("{:<16} {}", "\\n{}") - sont absentes d'ici :
elles rendent le francais, c'est-a-dire elles-memes.

tests/test_i18n.py verifie tout cela phrase par phrase, et refuse une phrase
nouvelle qui ne serait ni traduite ici ni declaree laissee en francais.
"""

MESSAGES = {
    "tirs au but": "tanda de penaltis",
    # ---------------------------------------------------------- --status ----
    "actif (pid {})": "activo (pid {})",
    "arrete": "detenido",
    "  releve      : {}": "  sondeo      : {}",
    "aucun pour l'instant": "todavia ninguno",
    "aucun (le daemon efface son etat en s'arretant)":
        "ninguno (el daemon borra su estado al detenerse)",
    "date inconnue": "fecha desconocida",
    "il y a {} s": "hace {} s",
    "il y a {} min": "hace {} min",
    "il y a {} h {:02d}": "hace {} h {:02d}",
    "                etat laisse par un daemon qui ne tourne plus":
        "                estado dejado por un daemon que ya no corre",
    "                (!) plus rien depuis, alors que la cadence est de {}s : "
    "daemon bloque ou source injoignable ?":
        "                (!) nada nuevo desde entonces, y la cadencia es de "
        "{}s: daemon bloqueado o fuente inaccesible?",
    "  en cours    : inconnu (le dernier releve est trop vieux)":
        "  en juego    : desconocido (el ultimo sondeo es demasiado viejo)",
    "  en cours    : {}": "  en juego    : {}",
    "{} match(s)": "{} partido(s)",
    " sur {} au programme": " de {} programados",
    "  buts du jour: {}  (le detail : butbutbut --today)":
        "  goles de hoy: {}  (el detalle: butbutbut --today)",
    "  equipes     : {}": "  equipos     : {}",
    "  epinglee    : {}": "  fijada      : {}",
    "{} (etat inconnu : voir la ligne releve)":
        "{} (estado desconocido: ver la linea sondeo)",
    "{} (aucun match en cours)":
        "{} (ningun partido en curso)",
    "  sans spoiler: {}  (journal seulement : ni carte, ni son)":
        "  sin spoiler : {}  (solo el registro: ni tarjeta, ni sonido)",
    "  silence     : {}": "  silencio    : {}",
    "  langue      : {}": "  idioma      : {}",
    "  suivi       : {}": "  siguiendo   : {}",
    "  competitions: {}": "  competic.   : {}",
    "  sports      : {}": "  deportes    : {}",
    "les 5 grands championnats": "las 5 grandes ligas",
    "tout le catalogue ({} competitions)":
        "todo el catalogo ({} competiciones)",
    "tout le football feminin ({} competitions)":
        "todo el futbol femenino ({} competiciones)",
    # "tout le {} ({} competitions)" n'a pas d'entree : le trou y recoit le nom
    # du sport, que sports.py garde en francais pour le journal. La traduire
    # ferait une phrase a moitie espagnole ; celle-ci, non.
    "tous les sports ({} competitions)": "todos los deportes ({} competiciones)",
    "{} et {} autres": "{} y {} mas",
    "  source      : ESPN scoreboard (public, sans cle)":
        "  fuente      : ESPN scoreboard (publico, sin clave)",
    "  cadence     : {}s en direct / {}s au repos":
        "  cadencia    : {}s en directo / {}s en reposo",
    "  donnees     : {}": "  datos       : {}",
    "  (absent, voir --write-config)": "  (ausente, ver --write-config)",
    "  crochet     : {}": "  gancho      : {}",
    "{}  (essai : --test-hook)": "{}  (prueba: --test-hook)",
    "aucun (voir --on-goal)": "ninguno (ver --on-goal)",
    "  voix        : {}": "  voz         : {}",
    "  son         : {} fichier(s), le nom dit quand ils jouent":
        "  sonido      : {} fichero(s), el nombre dice cuando suenan",
    "  son         : {} ({})": "  sonido      : {} ({})",
    "fourni": "incluido",
    "corne synthetisee": "bocina sintetizada",
    "  sons perso  : {}  ({} fichier(s))":
        "  mis sonidos : {}  ({} fichero(s))",
    "  son nomme   : {} paire(s), le plus precis l'emporte":
        "  s. nombrado : {} par(es), gana el mas preciso",

    # Ce que les deux lignes 'son' de --status affichent a droite : quand un
    # son a soi se declenche, d'apres son nom de fichier ou --sound-for.
    "quand une equipe suivie encaisse": "cuando un equipo seguido encaja",
    "  (jamais : aucune equipe suivie, voir --teams)":
        "  (nunca: ningun equipo seguido, ver --teams)",
    "les buts de {}": "los goles de {}",
    "  (competition non suivie)": "  (competicion no seguida)",
    "tirage general": "sorteo general",
    "et {} autre(s)": "y {} mas",
    "quand cette equipe marque": "cuando este equipo marca",

    "  ecussons    : {}": "  escudos     : {}",
    "desactives (--no-logos)": "desactivados (--no-logos)",
    "  ecrans      : {} -> carte en {} sur {}":
        "  pantallas   : {} -> tarjeta en {} en {}",
    "1 ecran ({}x{})": "1 pantalla ({}x{})",
    "{} ecrans [{}]": "{} pantallas [{}]",
    "l'ecran principal": "la pantalla principal",
    "ecran {}": "pantalla {}",
    "  rattrapage  : {}": "  recuperacion: {}",
    "actif (une carte de resume au reveil, sans son)":
        "activo (una tarjeta de resumen al despertar, sin sonido)",
    "inactif (le reveil reste silencieux, voir --catch-up)":
        "inactivo (el despertar sigue en silencio, ver --catch-up)",
    "  plein ecran : {}": "  p. completa : {}",
    "detecte (la carte masquee est notee au journal)":
        "detectado (la tarjeta tapada se anota en el registro)",
    "non detectable sur cette plateforme": "no detectable en esta plataforma",
    "  journal     : {}": "  registro    : {}",
    "  lecteur     : winsound + MCI (integres)":
        "  reproductor : winsound + MCI (integrados)",
    "  lecteur     : {}": "  reproductor : {}",
    "AUCUN (installe mpv/ffmpeg/pipewire/alsa-utils)":
        "NINGUNO (instala mpv/ffmpeg/pipewire/alsa-utils)",
    "  affichage   : tkinter OK": "  interfaz    : tkinter OK",
    "  affichage   : tkinter MANQUANT (voir README)":
        "  interfaz    : tkinter AUSENTE (ver README)",
    "\n  Connexion   : ": "\n  Conexion    : ",
    "OK ({} : {} match(s))": "OK ({} : {} partido(s))",
    "ECHEC ({})": "FALLO ({})",

    # ---------------------------------------------------------- --scores ----
    "injoignable ({})": "inaccesible ({})",
    "  (aucun match au programme)": "  (ningun partido programado)",
    "  (aucun match de ces equipes)": "  (ningun partido de estos equipos)",
    "sans spoiler": "sin spoiler",
    "en cours": "en juego",
    "termine": "finalizado",
    "a venir": "por jugar",
    "imminent": "inminente",
    "dans {} min": "en {} min",
    "\n{} match(s), '>' = en cours.": "\n{} partido(s), '>' = en juego.",
    "'?' = sans spoiler : {} match(s) masque(s). Le journal, lui, a tout : "
    "butbutbut --today.":
        "'?' = sin spoiler: {} partido(s) tapado(s). El registro, en cambio, "
        "lo tiene todo: butbutbut --today.",

    # ------------------------------------------------------------ --next ----
    # Une competition qui n'a pas repondu ne fait pas echouer la commande :
    # elle se signale en fin de liste, et le calendrier se dit incomplet.
    "butbutbut : prochains matchs - {}, {} jour(s)":
        "butbutbut : proximos partidos - {}, {} dia(s)",
    "\n{} match(s) a venir dans {} competition(s), sur {} jour(s).":
        "\n{} partido(s) por jugar en {} competicion(es), en {} dia(s).",
    "\nAucune competition n'a repondu : rien a annoncer.":
        "\nNinguna competicion ha respondido: nada que anunciar.",
    "  ({} injoignable : {})": "  ({} inaccesible: {})",
    "  (le calendrier ci-dessus est donc incomplet ; les autres competitions "
    "ont repondu)":
        "  (el calendario de arriba esta por tanto incompleto; las demas "
        "competiciones si han respondido)",

    # ----------------------------------------------------------- --table ----
    # Le classement d'une competition, pas un palmares de buteurs : les deux
    # mots se separent dans les langues qui les distinguent.
    "butbutbut : classement - {}": "butbutbut : clasificacion - {}",
    "\nAucune competition n'a repondu : rien a classer.":
        "\nNinguna competicion ha respondido: nada que clasificar.",
    "  (une coupe se joue en tableau ; hors saison, la source n'a rien a "
    "servir)":
        "  (una copa se juega por eliminatorias; fuera de temporada, la "
        "fuente no tiene nada que servir)",
    "  (le classement ci-dessus est donc incomplet ; les autres competitions "
    "ont repondu)":
        "  (la clasificacion de arriba esta por tanto incompleta; las demas "
        "competiciones si han respondido)",

    # ------------------------------------ la fenetre lue dans le journal ----
    # Nommee en tete de --today, --stats, --top-scorers et --export : la meme
    # phrase sert aux quatre, d'ou sa place avant elles.
    "date illisible : {!r}. Format attendu : AAAA-MM-JJ, par exemple --since "
    "{}":
        "fecha ilegible: {!r}. Formato esperado: AAAA-MM-DD, por ejemplo "
        "--since {}",
    "depuis le debut du journal": "desde el principio del registro",
    "le {}": "el {}",
    "du {} au {}": "del {} al {}",

    # ----------------------------------------------------------- --today ----
    "butbutbut : buts signales le {:%d/%m/%Y}":
        "butbutbut : goles avisados el {:%d/%m/%Y}",
    "butbutbut : buts signales {}": "butbutbut : goles avisados {}",
    "\n  (journal vide : aucun but n'y a encore ete ecrit)":
        "\n  (registro vacio: todavia no se ha escrito ningun gol)",
    "\n  (aucun but dans le journal)": "\n  (ningun gol en el registro)",
    "\n  (aucun but pour l'instant)": "\n  (todavia no hay goles)",
    "\n  (aucun but sur cette periode)": "\n  (ningun gol en este periodo)",
    "\nJournal : {}": "\nRegistro : {}",
    "\n{} but(s) dans {} competition(s).":
        "\n{} gol(es) en {} competicion(es).",
    "'-' = but retire par la VAR ({}).": "'-' = gol anulado por el VAR ({}).",
    "\n{} but(s) signale(s), {} jour(s), {} competition(s).":
        "\n{} gol(es) avisado(s), {} dia(s), {} competicion(es).",
    "{} = but retire par la VAR ({}) : {} but(s) confirme(s).":
        "{} = gol anulado por el VAR ({}): {} gol(es) confirmado(s).",

    # ------------------------------------------------------ --list-teams ----
    "butbutbut : aucune equipe ne correspond a {} dans {}. "
    "Voir 'butbutbut --list-teams'.":
        "butbutbut : ningun equipo coincide con {} en {}. "
        "Ver 'butbutbut --list-teams'.",
    "butbutbut : aucune competition ne correspond au prefixe de {}. "
    "Voir 'butbutbut --list'.":
        "butbutbut : ninguna competicion coincide con el prefijo de {}. "
        "Ver 'butbutbut --list'.",
    "butbutbut : {} vise une competition qui n'est pas suivie : "
    "ajoute-la a --leagues, ou retire le prefixe.":
        "butbutbut : {} apunta a una competicion que no se sigue: "
        "anadela a --leagues, o quita el prefijo.",
    "{} - {} equipe(s)": "{} - {} equipo(s)",
    "  (la source ne publie pas de liste pour cette competition)":
        "  (la fuente no publica lista para esta competicion)",
    "'*' = suivie, '-' = exclue.": "'*' = seguido, '-' = excluido.",
    "'?' = suivie sans spoiler : journal seulement, ni carte ni son.":
        "'?' = seguido sin spoiler: solo el registro, ni tarjeta ni sonido.",
    "Exemples :": "Ejemplos:",

    # ----------------------------------------------------- --top-scorers ----
    # Les buts repris par la VAR sont deduits : le compte affiche n'est pas
    # celui des lignes du journal, et la note le dit.
    "butbutbut : buteurs vus passer {}":
        "butbutbut : goleadores vistos pasar {}",
    "\n  (aucun buteur connu : la source n'avait pas encore publie l'action)":
        "\n  (ningun goleador conocido: la fuente todavia no habia publicado "
        "la jugada)",
    "  ... et {} autre(s) buteur(s) plus bas au classement.":
        "  ... y {} goleador(es) mas abajo en la clasificacion.",
    "\n{} buteur(s) pour {} but(s) confirme(s) sur {} signale(s).":
        "\n{} goleador(es) para {} gol(es) confirmado(s) de {} avisado(s).",
    "{} but(s) retire(s) par la VAR, deduit(s) du classement.":
        "{} gol(es) anulado(s) por el VAR, descontado(s) de la clasificacion.",
    "{} annulation(s) sans but a retirer dans cette fenetre (le but est tombe "
    "avant).":
        "{} anulacion(es) sin gol que quitar en esta ventana (el gol cayo "
        "antes).",
    "{} but(s) sans buteur connu, hors classement.":
        "{} gol(es) sin goleador conocido, fuera de la clasificacion.",

    # ----------------------------------------------------------- --stats ----
    # Les gabarits d'alignement ({:<16} {:>4}) portent la colonne : ils
    # doivent se retrouver a l'identique, largeur comprise.
    "butbutbut : ce que le journal raconte {}":
        "butbutbut : lo que cuenta el registro {}",
    "\n  (aucun but debout dans cette fenetre : {} signale(s), {} repris par "
    "la VAR)":
        "\n  (ningun gol en pie en esta ventana: {} avisado(s), {} anulado(s) "
        "por el VAR)",
    "\nPar minute de match": "\nPor minuto de partido",
    "  (aucune minute de jeu lisible dans cette fenetre)":
        "  (ningun minuto de juego legible en esta ventana)",
    "\nPar competition": "\nPor competicion",
    "  ... et {} autre(s) competition(s) plus bas.":
        "  ... y {} competicion(es) mas abajo.",
    "\nLes soirees les plus prolifiques": "\nLas noches mas goleadoras",
    "  {:<16} {:>4} but(s)": "  {:<16} {:>4} gol(es)",
    "  ... et {} autre(s) soiree(s) a {} but(s).":
        "  ... y {} noche(s) mas con {} gol(es).",
    "\nNature des buts": "\nTipo de goles",
    "\n{} but(s) confirme(s) sur {} signale(s), dans {} competition(s).":
        "\n{} gol(es) confirmado(s) de {} avisado(s), en {} competicion(es).",
    "{} match(s) avec au moins un but signale, {:.1f} but(s) par match.":
        "{} partido(s) con al menos un gol avisado, {:.1f} gol(es) por "
        "partido.",
    "Un 0-0 ne laisse aucune trace dans le journal, ni dans cette moyenne.":
        "Un 0-0 no deja rastro en el registro, ni en esta media.",
    "{} but(s) retire(s) par la VAR, deduit(s) de tout ce qui precede.":
        "{} gol(es) anulado(s) por el VAR, descontado(s) de todo lo anterior.",
    "{} but(s) dans le temps additionnel, comptes dans la tranche de leur "
    "minute.":
        "{} gol(es) en el tiempo de descuento, contados en el tramo de su "
        "minuto.",
    "{} but(s) sans minute de jeu lisible, hors histogramme.":
        "{} gol(es) sin minuto de juego legible, fuera del histograma.",

    # ---------------------------------------------------------- --export ----
    # Seules les notes vont sur la sortie d'erreur et se traduisent ; les
    # donnees elles-memes gardent leurs en-tetes anglais, non traduits.
    "butbutbut : export {} {}": "butbutbut : exportacion {} {}",
    "{} ligne(s) : {} but(s) signale(s) dont {} debout, {} annulation(s).":
        "{} linea(s): {} gol(es) avisado(s), de los que {} en pie, {} "
        "anulacion(es).",
    "Le champ 'standing' dit lesquels la VAR a repris.":
        "El campo 'standing' dice cuales ha anulado el VAR.",
    "Journal : {}": "Registro : {}",
    "butbutbut : export interrompu : {}":
        "butbutbut : exportacion interrumpida : {}",

    # ------------------------------------------------------------ --list ----
    "butbutbut : competitions surveillables\n":
        "butbutbut : competiciones vigilables\n",
    "Les 5 grands (defaut)": "Las 5 grandes (por defecto)",
    "Aussi disponibles": "Tambien disponibles",
    "Hockey sur glace (a demander)": "Hockey sobre hielo (a peticion)",
    "Rugby a XV (a demander)": "Rugby XV (a peticion)",
    "Football feminin (a demander)":
        "Futbol femenino (a peticion)",
    "\nExemples :": "\nEjemplos:",
    "  butbutbut --exclude liga,seriea        (les 5 grands moins deux)":
        "  butbutbut --exclude liga,seriea        (las 5 grandes menos dos)",
    "  butbutbut --leagues all                (tout le catalogue de football)":
        "  butbutbut --leagues all                (todo el catalogo de futbol)",
    "  butbutbut --leagues nhl,top14          (hockey et rugby, a la demande)":
        "  butbutbut --leagues nhl,top14          (hockey y rugby, a peticion)",
    "  butbutbut --leagues rugby              (tout le rugby du catalogue)":
        "  butbutbut --leagues rugby              (todo el rugby del catalogo)",
    "  butbutbut --leagues all-sports         (vraiment tout)":
        "  butbutbut --leagues all-sports         (absolutamente todo)",
    "  butbutbut --leagues feminines          (tout le football feminin)":
        "  butbutbut --leagues feminines          (todo el futbol femenino)",
    "  butbutbut --leagues l1f,wsl,uclf       (le meme, au feminin : un f a la fin)":
        "  butbutbut --leagues l1f,wsl,uclf       (lo mismo, en femenino: una f al final)",
    "  butbutbut --leagues por.1              (n'importe quel code ESPN)":
        "  butbutbut --leagues por.1              (cualquier codigo ESPN)",
    "  butbutbut --leagues hockey:nhl         (... y compris dans un autre "
    "sport)":
        "  butbutbut --leagues hockey:nhl         (... incluso en otro "
        "deporte)",

    # --------------------------------------------------------- --screens ----
    "butbutbut : {} ecran(s) detecte(s)":
        "butbutbut : {} pantalla(s) detectada(s)",
    "  {}  {:<16} {}x{} a +{}+{}{}": "  {}  {:<16} {}x{} en +{}+{}{}",
    "\nPar defaut la carte s'affiche en bas a droite de l'ecran principal.":
        "\nPor defecto la tarjeta sale abajo a la derecha de la pantalla "
        "principal.",
    "La deplacer :  butbutbut --screen 1 --position top-right":
        "Para moverla:  butbutbut --screen 1 --position top-right",

    # ----------------- les demonstrations : --test, --speak, --test-hook ----
    # Ce que --test-hook montre a l'ecran est une colonne comme celle de
    # --status : le ' : ' y tombe au meme index.
    "butbutbut : voix - {}": "butbutbut : voz - {}",
    "butbutbut : demo epinglee - [{}] {}": "butbutbut : demo fijada - [{}] {}",
    'butbutbut : aucune commande a essayer. Passe --on-goal "...", ou pose la '
    "cle on_goal dans le fichier de configuration.":
        'butbutbut : ningun comando que probar. Pasa --on-goal "...", o pon '
        "la clave on_goal en el fichero de configuracion.",
    "butbutbut : but fabrique, la commande recevra":
        "butbutbut : gol inventado, el comando recibira",
    "\n  commande    : {}": "\n  comando     : {}",
    "  resultat    : tuee apres {:.0f}s, elle ne rendait pas la main":
        "  resultado   : matada tras {:.0f}s, no devolvia el control",
    "  resultat    : impossible de la lancer ({})":
        "  resultado   : imposible lanzarla ({})",
    "  resultat    : code de sortie {}": "  resultado   : codigo de salida {}",
    "  sortie      :": "  salida      :",

    # ---------------------------------------------------------- --update ----
    "butbutbut {} - mise a jour": "butbutbut {} - actualizacion",

    # ------------------------------------------------------------ --stop ----
    "butbutbut : aucun daemon en cours.": "butbutbut : ningun daemon en curso.",
    "butbutbut : daemon {} arrete.": "butbutbut : daemon {} detenido.",
    "butbutbut : impossible d'arreter {} : {}":
        "butbutbut : imposible detener {} : {}",
    "Un but tombe en Ligue 1, Premier League, LaLiga, Serie A ou Bundesliga : "
    "le son part et le score s'affiche a l'ecran. Le hockey et le rugby sont "
    "dans le catalogue, a la demande (voir --list).":
        "Cae un gol en la Ligue 1, la Premier League, LaLiga, la Serie A o la "
        "Bundesliga: suena la bocina y el marcador sale en pantalla. El "
        "hockey y el rugby estan en el catalogo, a peticion (ver --list).",

    # ----------------------------------------------------------- erreurs ----
    "butbutbut : position inconnue : {} (voir --help)":
        "butbutbut : posicion desconocida : {} (ver --help)",
    "butbutbut : dossier de donnees inutilisable : {}":
        "butbutbut : carpeta de datos inutilizable : {}",
    "butbutbut : corne regeneree -> {}": "butbutbut : bocina regenerada -> {}",

    # -------------------------------------------------------------- aide ----

    # Les metavariables : ce que --help montre a la place de la valeur.
    "CHEMIN": "RUTA",
    "LISTE": "LISTA",
    "DATE": "FECHA",
    "EQUIPE": "EQUIPO",
    "EQUIPE|JOURS": "EQUIPO|DIAS",
    "competitions suivies, separees par des virgules (defaut : les 5 grands "
    "championnats de football). Ex : --leagues l1,pl,ucl ; 'all' pour tout le "
    "catalogue de football, 'hockey' ou 'rugby' pour un autre sport entier, "
    "'all-sports' pour tout ; un code ESPN marche aussi (por.1, hockey:nhl)":
        "competiciones seguidas, separadas por comas (por defecto: las 5 "
        "grandes ligas de futbol). Ej: --leagues l1,pl,ucl; 'all' para todo "
        "el catalogo de futbol, 'hockey' o 'rugby' para otro deporte entero, "
        "'all-sports' para todo; un codigo ESPN tambien vale (por.1, "
        "hockey:nhl)",
    "COIN": "ESQUINA",
    "CHOIX": "OPCION",
    "SECONDES": "SEGUNDOS",
    "MINUTES": "MINUTOS",
    "CODE": "CODIGO",

    "affiche N cartes de demonstration puis quitte "
    "(defaut 1 ; --test 3 montre l'empilement)":
        "muestra N tarjetas de demostracion y sale "
        "(por defecto 1; --test 3 muestra el apilado)",
    "affiche les matchs du jour dans le terminal puis quitte":
        "muestra los partidos del dia en el terminal y sale",
    "affiche les prochains matchs puis quitte. Sans rien : les {} prochains "
    "jours des competitions suivies. '--next om' cible une equipe, '--next "
    "14' allonge la fenetre ({} au plus)":
        "muestra los proximos partidos y sale. Sin nada: los {} proximos dias "
        "de las competiciones seguidas. '--next om' apunta a un equipo, "
        "'--next 14' alarga la ventana ({} como mucho)",
    "COMPETITION|EQUIPE": "COMPETICION|EQUIPO",
    "affiche le classement puis quitte. Sans rien : les competitions suivies. "
    "'--table l1' cible une competition, '--table om' surligne une equipe "
    "dans la sienne, et les deux se combinent":
        "muestra la clasificacion y sale. Sin nada: las competiciones "
        "seguidas. '--table l1' apunta a una competicion, '--table om' "
        "resalta un equipo en la suya, y las dos cosas se combinan",
    "affiche l'etat (daemon, dernier releve, matchs en cours, son, ecrans, "
    "connexion)":
        "muestra el estado (daemon, ultimo sondeo, partidos en juego, sonido, "
        "pantallas, conexion)",
    "recapitule les buts signales aujourd'hui": "resume los goles avisados hoy",
    "recapitule les buts des {} derniers jours (aujourd'hui compris)":
        "resume los goles de los ultimos {} dias (hoy incluido)",
    "recapitule les buts des {} derniers jours":
        "resume los goles de los ultimos {} dias",
    "recapitule les buts depuis ce jour, au format AAAA-MM-JJ. Ex : --since "
    "2026-09-01. L'emporte sur --week et --month.":
        "resume los goles desde ese dia, en formato AAAA-MM-DD. Ej: --since "
        "2026-09-01. Manda sobre --week y --month.",
    "classe les buteurs vus passer, buts annules par la VAR deduits. Sur tout "
    "le journal, ou sur la fenetre de --week, --month ou --since":
        "clasifica los goleadores vistos pasar, descontados los goles "
        "anulados por el VAR. Sobre todo el registro, o sobre la ventana de "
        "--week, --month o --since",
    "les formes cachees dans le journal : les buts par minute de match "
    "(histogramme), par competition, les soirees les plus prolifiques. Meme "
    "fenetre et memes filtres que --top-scorers":
        "las formas escondidas en el registro: los goles por minuto de "
        "partido (histograma), por competicion, las noches mas goleadoras. "
        "Misma ventana y mismos filtros que --top-scorers",
    "ecrit les buts du journal en donnees sur la sortie standard, pour un "
    "tableur ou un script. Memes fenetres et memes filtres que --stats. Ex : "
    "butbutbut --export csv --month > buts.csv":
        "escribe los goles del registro como datos en la salida estandar, "
        "para una hoja de calculo o un script. Mismas ventanas y mismos "
        "filtros que --stats. Ej: butbutbut --export csv --month > goles.csv",
    "arrete le daemon en cours": "detiene el daemon en curso",
    "affiche les chemins utilises": "muestra las rutas usadas",
    "liste les ecrans detectes": "lista las pantallas detectadas",
    "met a jour butbutbut depuis GitHub et rejoue l'installeur":
        "actualiza butbutbut desde GitHub y relanza el instalador",
    "dit si une version plus recente existe, sans rien installer":
        "dice si existe una version mas reciente, sin instalar nada",
    "avec --update ou --check-update : viser la pointe de la branche "
    "principale au lieu de la derniere release":
        "con --update o --check-update: apuntar a la punta de la rama "
        "principal en vez de a la ultima release",
    "FICHIER": "FICHERO",
    "surveille normalement, et ecrit en plus chaque reponse brute de la "
    "source dans FICHIER (JSON Lines ; un nom en .gz est compresse). C'est ce "
    "que --replay rejoue.":
        "vigila con normalidad, y ademas escribe cada respuesta en bruto de "
        "la fuente en FICHERO (JSON Lines; un nombre en .gz se comprime). Es "
        "lo que --replay vuelve a pasar.",
    "rejoue un enregistrement : memes cartes, meme son, meme journal, sans "
    "reseau. Ni le journal ni l'etat du vrai daemon ne sont touches.":
        "vuelve a pasar una grabacion: mismas tarjetas, mismo sonido, mismo "
        "registro, sin red. Ni el registro ni el estado del daemon de verdad "
        "se tocan.",
    "avec --replay : divise les ecarts de temps par N (defaut 1 ; 60 = une "
    "heure de match en une minute)":
        "con --replay: divide los intervalos de tiempo por N (por defecto 1; "
        "60 = una hora de partido en un minuto)",
    "fichier de configuration a lire (defaut : {} dans le dossier de donnees, "
    "voir 'butbutbut --paths')":
        "fichero de configuracion a leer (por defecto: {} en la carpeta de "
        "datos, ver 'butbutbut --paths')",
    "ecrit un fichier de configuration d'exemple, commente, puis quitte "
    "(n'ecrase rien)":
        "escribe un fichero de configuracion de ejemplo, comentado, y sale "
        "(no sobrescribe nada)",
    "competitions a ne pas suivre, meme syntaxe. Ex : --exclude liga,seriea":
        "competiciones que no seguir, misma sintaxis. "
        "Ej: --exclude liga,seriea",
    "liste les competitions surveillables et leurs noms":
        "lista las competiciones vigilables y sus nombres",
    "ne signaler que les matchs de ces equipes, separees par des virgules. "
    "Un match compte des qu'une des deux equipes y est, et un mot prefixe ne "
    "vaut que dans sa competition. Ex : --teams om,psg ou --teams "
    "ligue2:sochaux":
        "avisar solo de los partidos de estos equipos, separados por comas. "
        "Un partido cuenta en cuanto juega uno de los dos, y una palabra con "
        "prefijo solo vale en su competicion. Ej: --teams om,psg o --teams "
        "ligue2:sochaux",
    "ne rien signaler des matchs de ces equipes, prefixe compris "
    "(ligue2:metz)":
        "no avisar de los partidos de estos equipos, con prefijo incluido "
        "(ligue2:metz)",
    "garde a l'ecran une carte qui suit les matchs de cette equipe : elle "
    "apparait au coup d'envoi, se met a jour a chaque releve et s'en va "
    "quelques minutes apres la fin. Une seule equipe, et jamais de son. Ex : "
    "--pin om":
        "deja en pantalla una tarjeta que sigue los partidos de este equipo: "
        "aparece al comienzo, se actualiza en cada sondeo y se va unos "
        "minutos despues del final. Un solo equipo, y nunca sonido. Ej: --pin "
        "om",
    "matchs regardes en differe : aucune carte ni aucun son pour ces equipes, "
    "quel que soit l'evenement. Le journal, lui, garde tout (butbutbut "
    "--today). Ex : --spoiler-free om":
        "partidos vistos en diferido: ninguna tarjeta ni ningun sonido para "
        "estos equipos, pase lo que pase. El registro lo guarda todo "
        "(butbutbut --today). Ej: --spoiler-free om",
    "liste les equipes des competitions suivies":
        "lista los equipos de las competiciones seguidas",
    "secondes entre deux releves quand un match est en cours (defaut {})":
        "segundos entre dos sondeos cuando hay un partido en juego "
        "(por defecto {})",
    "secondes entre deux releves quand il n'y a rien a suivre (defaut {})":
        "segundos entre dos sondeos cuando no hay nada que seguir "
        "(por defecto {})",
    "duree d'affichage de la carte (defaut : la duree du son, au moins {})":
        "tiempo que la tarjeta sigue en pantalla (por defecto: lo que dura el "
        "sonido, al menos {})",
    "coin ou les cartes s'empilent : bottom-right (defaut), bottom-left, "
    "top-right, top-left, center":
        "esquina donde se apilan las tarjetas: bottom-right (por defecto), "
        "bottom-left, top-right, top-left, center",
    "ecran d'affichage : 'primary' (defaut) ou un index (0, 1, 2...). "
    "Voir 'butbutbut --screens'.":
        "pantalla de salida: 'primary' (por defecto) o un indice (0, 1, 2...). "
        "Ver 'butbutbut --screens'.",
    "taille de la carte (1.0 par defaut, 1.5 = plus grande)":
        "escala de la tarjeta (1.0 por defecto, 1.5 = mas grande)",
    "opacite, 0.0 a 1.0": "opacidad, 0.0 a 1.0",
    "pas de carte : seulement le son et le journal":
        "sin tarjeta: solo el sonido y el registro",
    "pas de carte au coup d'envoi, a la mi-temps, a la reprise ni a la fin du "
    "match (les buts, si)":
        "sin tarjeta en el comienzo, el descanso, la reanudacion ni el final "
        "del partido (los goles, si)",
    "quand une application en plein ecran masque l'ecran, repasser la carte "
    "des que l'ecran se libere, pendant SECONDES au plus (defaut {:.0f} ; "
    "Windows uniquement, voir README)":
        "cuando una aplicacion a pantalla completa tapa la pantalla, repetir "
        "la tarjeta en cuanto se libere, durante SEGUNDOS como mucho "
        "(por defecto {:.0f}; solo Windows, ver README)",
    "PLAGE": "FRANJA",
    "plage horaire ou rien ne s'affiche et rien ne sonne, au format {} (ex : "
    "{}). Le but tombe quand meme dans le journal, et --today le retrouve. "
    "L'heure est celle de la machine, la plage peut enjamber minuit.":
        "franja horaria en la que nada sale ni suena, en formato {} (ej: {}). "
        "El gol cae igualmente en el registro, y --today lo encuentra. La "
        "hora es la de la maquina, y la franja puede cruzar la medianoche.",
    "se taire aussi quand le systeme signale qu'on presente : mode "
    "presentation, ecran duplique ou 'ne pas deranger'. Windows uniquement ; "
    "un partage de fenetre Teams/Zoom n'est pas detectable, voir README":
        "callarse tambien cuando el sistema avisa de que se esta presentando: "
        "modo presentacion, pantalla duplicada o 'no molestar'. Solo Windows; "
        "compartir una ventana en Teams/Zoom no es detectable, ver README",
    "signale aussi les cartons rouges, par une carte discrete et sans son":
        "avisa tambien de las tarjetas rojas, con una tarjeta discreta y sin "
        "sonido",
    "annonce le match ce nombre de minutes avant le coup d'envoi, une seule "
    "fois et sans son (0 = desactive, defaut)":
        "anuncia el partido estos minutos antes del comienzo, una sola vez y "
        "sin sonido (0 = desactivado, por defecto)",
    "au reveil apres une veille, resume en une carte muette les buts tombes "
    "pendant l'absence (par defaut le reveil reste silencieux)":
        "al despertar tras una suspension, resume en una tarjeta muda los "
        "goles caidos durante la ausencia (por defecto el despertar sigue en "
        "silencio)",
    "COMMANDE": "COMANDO",
    "commande a lancer a chaque but, avec le detail du but dans des variables "
    "d'environnement BUT_* (voir --test-hook et le README)":
        "comando que lanzar en cada gol, con el detalle del gol en variables "
        "de entorno BUT_* (ver --test-hook y el README)",
    "essaie la commande de --on-goal sur un but fabrique, et montre ce "
    "qu'elle rend":
        "prueba el comando de --on-goal con un gol inventado, y muestra lo "
        "que devuelve",
    "langue des cartes : fr, en, es, it, de (defaut : celle du systeme, "
    "francais a defaut). Le journal, lui, reste toujours en francais.":
        "idioma de las tarjetas: fr, en, es, it, de (por defecto: el del "
        "sistema, frances si no se sabe). El registro sigue en frances.",
    "pas d'ecusson sur les cartes, et rien de telecharge (les couleurs des "
    "clubs restent)":
        "sin escudo en las tarjetas, y sin descargar nada (los colores de los "
        "clubes se quedan)",
    "mode muet": "modo silencio",
    "dit le but a voix haute, en plus du son (ou a sa place avec --no-sound). "
    "La phrase est celle des cartes, dans leur langue. 'butbutbut --test "
    "--speak' l'essaie tout de suite.":
        "dice el gol en voz alta, ademas del sonido (o en su lugar con "
        "--no-sound). La frase es la de las tarjetas, en su idioma. "
        "'butbutbut --test --speak' lo prueba al momento.",
    "volume de la corne synthetisee, 0.0 a 1.0":
        "volumen de la bocina sintetizada, 0.0 a 1.0",
    "PAIRES": "PARES",
    "un son a soi pour une equipe ou une competition, sous forme de paires "
    "nom=chemin separees par des virgules. Les noms sont ceux de --teams et "
    "de --leagues, et l'equipe l'emporte sur sa competition. Un chemin fautif "
    "est refuse au demarrage. Ex : --sound-for om=~/sons/om.wav":
        "un sonido propio para un equipo o una competicion, en forma de pares "
        "nombre=ruta separados por comas. Los nombres son los de --teams y "
        "--leagues, y el equipo manda sobre su competicion. Una ruta erronea "
        "se rechaza al arrancar. Ej: --sound-for om=~/sonidos/om.wav",
    "regenere la corne synthetisee": "regenera la bocina sintetizada",
    "n'ecrit que dans le journal": "solo escribe en el registro",
    "butbutbut : --pin ne prend qu'une equipe ({!r} en annonce plusieurs) : "
    "il n'y a jamais qu'une carte epinglee.":
        "butbutbut : --pin solo acepta un equipo ({!r} anuncia varios) : "
        "nunca hay mas de una tarjeta fijada.",
    'francais': 'frances',
    'anglais': 'ingles',
    'espagnol': 'castellano',
    'italien': 'italiano',
    'allemand': 'aleman',
    'aucune competition selectionnee.':
        'no hay ninguna competicion seleccionada.',
    'plus aucune competition a surveiller apres exclusion.':
        'no queda ninguna competicion que seguir tras las exclusiones.',
    'butbutbut : impossible de verifier les equipes (source injoignable), on continue sans verification.':
        'butbutbut : no se pueden comprobar los equipos (fuente inaccesible), se continua sin comprobar.',
}
