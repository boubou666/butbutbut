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

Les phrases que l'espagnol laisse identiques - le nom du programme, les
gabarits purement typographiques ("{:<16} {}", "\\n{}") - sont absentes d'ici :
elles rendent le francais, c'est-a-dire elles-memes.
"""

MESSAGES = {
    # ---------------------------------------------------------- --status ----
    "actif (pid {})": "activo (pid {})",
    "arrete": "detenido",
    "  releve      : {}": "  sondeo      : {}",
    "                etat laisse par un daemon qui ne tourne plus":
        "                estado dejado por un daemon que ya no corre",
    "                (!) plus rien depuis, alors que la cadence est de {}s : "
    "daemon bloque ou source injoignable ?":
        "                (!) nada nuevo desde entonces, y la cadencia es de "
        "{}s: daemon bloqueado o fuente inaccesible?",
    "  en cours    : inconnu (le dernier releve est trop vieux)":
        "  en juego    : desconocido (el ultimo sondeo es demasiado viejo)",
    "  en cours    : {}": "  en juego    : {}",
    "  buts du jour: {}  (le detail : butbutbut --today)":
        "  goles de hoy: {}  (el detalle: butbutbut --today)",
    "  equipes     : {}": "  equipos     : {}",
    "  langue      : {}": "  idioma      : {}",
    "  suivi       : {}": "  siguiendo   : {}",
    "  competitions: {}": "  competic.   : {}",
    "  source      : ESPN scoreboard (public, sans cle)":
        "  fuente      : ESPN scoreboard (publico, sin clave)",
    "  cadence     : {}s en direct / {}s au repos":
        "  cadencia    : {}s en directo / {}s en reposo",
    "  donnees     : {}": "  datos       : {}",
    "  son         : {}{}": "  sonido      : {}{}",
    "  son         : {} ({})": "  sonido      : {} ({})",
    "  sons perso  : {}  ({} fichier(s))":
        "  mis sonidos : {}  ({} fichero(s))",
    "  ecussons    : {}": "  escudos     : {}",
    "desactives (--no-logos)": "desactivados (--no-logos)",
    "  ecrans      : {} -> carte en {} sur {}":
        "  pantallas   : {} -> tarjeta en {} en {}",
    "l'ecran principal": "la pantalla principal",
    "ecran {}": "pantalla {}",
    "  plein ecran : {}": "  p. completa : {}",
    "  journal     : {}": "  registro    : {}",
    "  lecteur     : winsound + MCI (integres)":
        "  reproductor : winsound + MCI (integrados)",
    "  lecteur     : {}": "  reproductor : {}",
    "  affichage   : tkinter OK": "  interfaz    : tkinter OK",
    "  affichage   : tkinter MANQUANT (voir README)":
        "  interfaz    : tkinter AUSENTE (ver README)",
    "OK ({} : {} match(s))": "OK ({} : {} partido(s))",
    "ECHEC ({})": "FALLO ({})",

    # ---------------------------------------------------------- --scores ----
    "injoignable ({})": "inaccesible ({})",
    "\n{} match(s), '>' = en cours.": "\n{} partido(s), '>' = en juego.",

    # ----------------------------------------------------------- --today ----
    "butbutbut : buts signales le {:%d/%m/%Y}":
        "butbutbut : goles avisados el {:%d/%m/%Y}",
    "\n  (aucun but pour l'instant)": "\n  (todavia no hay goles)",
    "\nJournal : {}": "\nRegistro : {}",
    "\n{} but(s) dans {} competition(s).":
        "\n{} gol(es) en {} competicion(es).",
    "'-' = but retire par la VAR ({}).": "'-' = gol anulado por el VAR ({}).",

    # ------------------------------------------------------ --list-teams ----
    "butbutbut : aucune equipe ne correspond a {} dans {}. "
    "Voir 'butbutbut --list-teams'.":
        "butbutbut : ningun equipo coincide con {} en {}. "
        "Ver 'butbutbut --list-teams'.",
    "{} - {} equipe(s)": "{} - {} equipo(s)",
    "  (la source ne publie pas de liste pour cette competition)":
        "  (la fuente no publica lista para esta competicion)",
    "'*' = suivie, '-' = exclue.": "'*' = seguido, '-' = excluido.",
    "Exemples :": "Ejemplos:",

    # ------------------------------------------------------------ --list ----
    "\nExemples :": "\nEjemplos:",
    "  butbutbut --exclude liga,seriea        (les 5 grands moins deux)":
        "  butbutbut --exclude liga,seriea        (las 5 grandes menos dos)",
    "  butbutbut --leagues all                (tout le catalogue)":
        "  butbutbut --leagues all                (todo el catalogo)",
    "  butbutbut --leagues por.1              (n'importe quel code ESPN)":
        "  butbutbut --leagues por.1              (cualquier codigo ESPN)",

    # --------------------------------------------------------- --screens ----
    "butbutbut : {} ecran(s) detecte(s)":
        "butbutbut : {} pantalla(s) detectada(s)",
    "  {}  {:<16} {}x{} a +{}+{}{}": "  {}  {:<16} {}x{} en +{}+{}{}",
    "\nPar defaut la carte s'affiche en bas a droite de l'ecran principal.":
        "\nPor defecto la tarjeta sale abajo a la derecha de la pantalla "
        "principal.",
    "La deplacer :  butbutbut --screen 1 --position top-right":
        "Para moverla:  butbutbut --screen 1 --position top-right",

    # ---------------------------------------------------------- --update ----
    "butbutbut {} - mise a jour": "butbutbut {} - actualizacion",

    # ------------------------------------------------------------ --stop ----
    "butbutbut : daemon {} arrete.": "butbutbut : daemon {} detenido.",
    "butbutbut : impossible d'arreter {} : {}":
        "butbutbut : imposible detener {} : {}",

    # ----------------------------------------------------------- erreurs ----
    "butbutbut : position inconnue : {} (voir --help)":
        "butbutbut : posicion desconocida : {} (ver --help)",
    "butbutbut : dossier de donnees inutilisable : {}":
        "butbutbut : carpeta de datos inutilizable : {}",
    "butbutbut : corne regeneree -> {}": "butbutbut : bocina regenerada -> {}",

    # -------------------------------------------------------------- aide ----
    "affiche N cartes de demonstration puis quitte "
    "(defaut 1 ; --test 3 montre l'empilement)":
        "muestra N tarjetas de demostracion y sale "
        "(por defecto 1; --test 3 muestra el apilado)",
    "affiche les matchs du jour dans le terminal puis quitte":
        "muestra los partidos del dia en el terminal y sale",
    "affiche l'etat (daemon, dernier releve, matchs en cours, son, ecrans, "
    "connexion)":
        "muestra el estado (daemon, ultimo sondeo, partidos en juego, sonido, "
        "pantallas, conexion)",
    "recapitule les buts signales aujourd'hui": "resume los goles avisados hoy",
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
    "fichier de configuration a lire (defaut : {} dans le dossier de donnees, "
    "voir 'butbutbut --paths')":
        "fichero de configuracion a leer (por defecto: {} en la carpeta de "
        "datos, ver 'butbutbut --paths')",
    "ecrit un fichier de configuration d'exemple, commente, puis quitte "
    "(n'ecrase rien)":
        "escribe un fichero de configuracion de ejemplo, comentado, y sale "
        "(no sobrescribe nada)",
    "competitions suivies, separees par des virgules (defaut : les 5 grands "
    "championnats). Ex : --leagues l1,pl,ucl ; 'all' pour tout le catalogue ; "
    "un code ESPN marche aussi (por.1)":
        "competiciones seguidas, separadas por comas (por defecto: las 5 "
        "grandes ligas). Ej: --leagues l1,pl,ucl; 'all' para todo el catalogo; "
        "un codigo ESPN tambien vale (por.1)",
    "competitions a ne pas suivre, meme syntaxe. Ex : --exclude liga,seriea":
        "competiciones que no seguir, misma sintaxis. "
        "Ej: --exclude liga,seriea",
    "liste les competitions surveillables et leurs noms":
        "lista las competiciones vigilables y sus nombres",
    "ne signaler que les matchs de ces equipes, separees par des virgules. "
    "Un match compte des qu'une des deux equipes y est. Ex : --teams om,psg":
        "avisar solo de los partidos de estos equipos, separados por comas. "
        "Un partido cuenta en cuanto juega uno de los dos. Ej: --teams om,psg",
    "ne rien signaler des matchs de ces equipes":
        "no avisar de los partidos de estos equipos",
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
    "signale aussi les cartons rouges, par une carte discrete et sans son":
        "avisa tambien de las tarjetas rojas, con una tarjeta discreta y sin "
        "sonido",
    "annonce le match ce nombre de minutes avant le coup d'envoi, une seule "
    "fois et sans son (0 = desactive, defaut)":
        "anuncia el partido estos minutos antes del comienzo, una sola vez y "
        "sin sonido (0 = desactivado, por defecto)",
    "langue des cartes : fr, en, es, it, de (defaut : celle du systeme, "
    "francais a defaut). Le journal, lui, reste toujours en francais.":
        "idioma de las tarjetas: fr, en, es, it, de (por defecto: el del "
        "sistema, frances si no se sabe). El registro sigue en frances.",
    "pas d'ecusson sur les cartes, et rien de telecharge (les couleurs des "
    "clubs restent)":
        "sin escudo en las tarjetas, y sin descargar nada (los colores de los "
        "clubes se quedan)",
    "mode muet": "modo silencio",
    "volume de la corne synthetisee, 0.0 a 1.0":
        "volumen de la bocina sintetizada, 0.0 a 1.0",
    "regenere la corne synthetisee": "regenera la bocina sintetizada",
    "n'ecrit que dans le journal": "solo escribe en el registro",
}
