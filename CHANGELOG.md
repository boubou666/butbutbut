# Changelog

Toutes les evolutions notables de butbutbut sont consignees ici.

Le format suit [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/),
et le projet respecte le [versionnage semantique](https://semver.org/lang/fr/).

## [Non publie]

### Ajoute

- **Un crochet a chaque but** : `--on-goal "commande"` lance la commande de son
  choix quand un but tombe, avec tout le detail du but dans des variables
  d'environnement `BUT_*` (`BUT_TEXT` porte la phrase toute faite). Plutot que
  d'ecrire dans butbutbut les dix integrations que dix personnes voudraient -
  guirlande connectee, webhook Discord, domotique, compteur perso - il donne de
  quoi les ecrire soi-meme.
- `--test-hook` lance la commande sur un but fabrique et montre ce qu'elle
  recoit, ce qu'elle rend et son code de sortie. Regler un crochet en guettant
  un vrai but aurait ete une mise au point d'une demi-journee, avec un daemon
  qui se tait justement quand tout va bien.
- La cle `on_goal` du fichier de configuration, et une ligne `crochet` dans
  `--status`.

### Interne

- **Les donnees du but passent par l'environnement, jamais par la commande.**
  Un nom d'equipe n'est donc jamais recolle dans une ligne de shell : le jour
  ou la source annoncera un club nomme `; rm -rf ~`, il ne se passera rien.
  C'est aussi ce qui rend `shell=True` acceptable, et donc ce qui permet
  d'ecrire sa commande avec les tubes et les guillemets dont on a l'habitude.
- La commande part dans un fil a part et personne ne guette sa fin : un script
  lent ne retarde ni la carte, ni le releve suivant. Elle est tuee au bout de
  30 s, et huit au plus tournent en meme temps. Un echec est une ligne de
  journal ; une reussite ne dit rien, un crochet qui part a chaque but n'ayant
  pas a remplir le journal.
- Le crochet part **depuis le fil de surveillance**, a cote du journal, et non
  depuis la boucle d'affichage : il decrit un but, pas une carte, et doit donc
  partir aussi en `--no-overlay` et quand l'affichage echoue.
- Il part aussi sur un but **retire par la VAR**, `BUT_TYPE` valant alors
  `cancelled` : annoncer un but puis se taire quand il est refuse, ce serait
  mentir a ce qu'on alimente. Les temps forts, les expulsions et les annonces
  d'avant match, eux, ne declenchent rien.
- 502 -> **523 tests**.



### Ajoute

- **Des sons par contexte, decides par le nom du fichier.** Le dossier `sound`
  ne se contente plus d'un tirage au hasard : `om.mp3` ne sort que quand l'OM
  marque, `fra.1.mp3` (ou `l1.mp3`) que pour un but de Ligue 1, et surtout
  `contre.mp3` quand une equipe suivie avec `--teams` **encaisse**. Suivre un
  club, c'est enfin entendre la difference entre "on a marque" et "on a pris".
- Les noms acceptes sont ceux qu'on tape deja ailleurs : les surnoms et
  abreviations de `--teams` (`om`, `barca`, `manu`, `olm`...) et les codes ou
  alias de `--list` (`fra.1`, `l1`, `ligue1`, `ucl`). Le mot pour "encaisse"
  s'ecrit aussi `encaisse`, `against` ou `conceded`.
- Plusieurs fichiers pour la meme chose se distinguent par un suffixe apres
  `-`, `_`, un espace ou un point (`om-1.mp3`, `om-2.mp3`) : le tirage au
  hasard reste, mais entre eux seulement.
- `butbutbut --status` deroule le dossier et dit, fichier par fichier, ce que
  butbutbut a compris de son nom - y compris qu'un `contre.mp3` ne servira
  jamais sans `--teams`, ou qu'un son vise une competition non suivie.

### Change

- La priorite va du plus etroit au plus large - equipe, `contre`, competition,
  fond sonore - pour qu'une intention precise ne soit jamais recouverte par une
  plus large, et un etage vide passe la main au suivant. Un dossier sans nom
  reconnaissable se comporte donc exactement comme avant.
- Le son est desormais choisi **par but** et non par releve : deux buts du meme
  tour peuvent venir de deux equipes, donc de deux fichiers.



### Ajoute

- **Le mode sans spoiler** : `--spoiler-free EQUIPES` (et la cle
  `spoiler_free`). Pour les matchs de ces equipes, plus rien n'arrive a l'ecran
  ni au haut-parleur - ni but, ni but annule, ni temps fort, ni carton rouge, ni
  annonce d'avant match. Un « COUP D'ENVOI » dit que le direct est parti, un
  « FIN DU MATCH » que tout est joue : ca spoile autant qu'un but, donc tous les
  evenements se taisent. C'est le reglage du match regarde en differe, ou la
  carte annoncait le but avant qu'on ne le voie.
- Le journal, lui, garde tout : c'est le coeur du reglage. On ne coupe que
  l'ecran et le son, et `butbutbut --today` raconte le match une fois qu'on l'a
  vu. D'ou un evenement *marque* (`Event.spoiler_free`) et non filtre, la ou
  `--exclude-teams` fait disparaitre le match jusque dans le journal.
- Les noms se tapent avec la meme souplesse que `--teams` (`om`, `barca`,
  `manu`, les noms sans accents, les debuts de mots) et un mot qui ne designe
  aucune equipe est refuse au demarrage. La faute de frappe est plus sournoise
  ici qu'ailleurs : elle ne rend pas le daemon muet, elle le laisse spoiler le
  match qu'on voulait proteger.
- `--status` rappelle le reglage, et `--list-teams` marque d'un `?` les equipes
  concernees.

### Change

- `--scores` montre les matchs sans spoiler, mais avec leur score masque :
  `Marseille ? - ? Paris FC   sans spoiler`. Les faire disparaitre aurait ete
  pire que de tout montrer - on ne saurait plus si le match a lieu, ni a quelle
  heure, et c'est justement le jour ou on le regarde qu'on ouvre `--scores`.
  Rien de ce qui permettrait de reconstituer le score ne s'affiche : ni les
  buteurs, ni l'etat du match, pour qu'un match termine ressemble a un match en
  cours. `--status` masque de la meme facon le score des matchs en cours.
- L'ordre de decision des trois filtres par equipe est fixe et teste :
  `--exclude-teams` fait disparaitre le match, puis `--teams`, puis
  `--spoiler-free` qui le laisse vivre en silence. Suivre l'OM **et** le mettre
  en sans-spoiler est donc un usage normal : je veux le journal, pas l'alerte.

### Interne

- 701 -> **743 tests**.



### Ajoute

- **`--catch-up` : rattraper ce qui s'est passe pendant la veille.** Au reveil,
  au lieu de se taire, butbutbut affiche UNE carte de resume - les matchs qui
  ont bouge, leur score avant et apres, et les buteurs. La photo d'avant le
  trou n'est plus jetee : elle est confrontee a celle du reveil, et comme la
  source publie le tableau des actions avec des cles stables, on sait
  exactement quels buts on n'a jamais vus.
- La cle `catch_up` du fichier de configuration, et une ligne « rattrapage »
  dans `--status` qui rappelle lequel des deux comportements est arme.

### Change

- Rien par defaut : l'option est **eteinte**, le silence au reveil reste le
  comportement livre. C'est celui qui ne raconte jamais rien de faux, et
  changer d'avis pour tout le monde en montant de version serait une surprise.

### Interne

- Les arbitrages de la carte de resume, tous pris contre le reflexe de tout
  dire : **une seule** carte et non une par but (rejouer trois cartes avec des
  minutes perimees est exactement ce que le silence evitait) ; **aucun son**
  (on n'annonce pas au klaxon un but vieux d'une heure) ; **pas de carte du
  tout** quand personne n'a marque, le journal notant quand meme le rattrapage
  pour que « aucune carte » et « le rattrapage n'a pas tourne » restent
  distinguables ; le filtre `--teams` respecte ; et un match commence et fini
  pendant la veille laisse de cote, meme regle que pour la carte de fin de
  match - on n'en a rien suivi.
- La troncature de la carte n'est pas reecrite : la liste des matchs passe par
  `extra_parts()` et se fait couper en hauteur et en largeur par le mecanisme
  qui coupe deja la liste des buteurs de la fin de match.
- Le resume attend que **toutes** les competitions suivies aient ete
  rephotographiees. Sous Linux `time.monotonic()` gele pendant la veille : les
  echeances ne retombent pas au meme releve, et un resume a trous vaudrait
  moins que rien.
- Deux sommeils d'affilee avant que le resume ait pu sortir gardent la photo la
  plus ancienne, pas la plus recente : c'est elle qui dit tout ce qu'on a
  manque.



### Ajoute

- **La carte epinglee** : `butbutbut --pin om`. Tant qu'un match de l'equipe
  demandee est en cours, une carte **reste a l'ecran** et se met a jour a
  chaque releve (le score et la minute), au lieu de n'apparaitre qu'aux buts.
  butbutbut passe ainsi de l'alerte au tableau de bord : la carte vit sur le
  second ecran pendant qu'on travaille.
- La cle `pin` du fichier de configuration, et une ligne `epinglee` dans
  `butbutbut --status` qui dit ce que le daemon suit vraiment.
  `butbutbut --test --pin om` en montre une, sans quoi personne ne pourrait la
  regler.

### Details qui ont demande un arbitrage

- **Ou elle vit** : ancree au coin choisi, la pile des cartes fugaces demarrant
  apres elle. Cinq buts d'affilee ne peuvent donc pas la pousser dehors (le
  plafond de cinq ne compte que les fugaces), et aucune carte de but ne peut se
  poser dessus (toutes les places sont calculees ensemble). Elle perd le coin,
  qui est la meilleure place : c'est le prix d'etre la en permanence.
- **Son cycle de vie** : elle apparait au coup d'envoi, ou tout de suite si le
  match est deja en cours au demarrage - lancer le daemon a la mi-temps doit
  donner la carte. Elle disparait cinq minutes apres la fin du match : elle ne
  passe pas la nuit a l'ecran. Un match qui disparait du tableau de bord est
  traite comme un match fini, avec le meme delai : mieux vaut une carte qui
  s'attarde qu'une carte qui clignote.
- **Un mot pour plusieurs clubs** (`--pin real` en attrape trois) est accepte,
  le nommage etant celui de `--teams` ; mais il n'y a **jamais qu'une carte**.
  Elle suit le match commence en premier et n'en change pas tant qu'il dure -
  une carte qui sauterait d'un match a l'autre serait illisible - puis passe au
  suivant. `--pin om,psg`, en revanche, est refuse au demarrage : accepter la
  liste reviendrait a n'en suivre silencieusement qu'une des deux.
- **Elle ne fait aucun bruit**, et aucune equipe n'y passe en couleur de club :
  le son reste la marque du but, et la couleur veut dire « elle vient de
  marquer », jamais « elle mene ».



### Ajoute

- **Enregistrer un vrai match, et le rejouer.** `butbutbut --record
  match.jsonl --leagues l1` surveille normalement et met en plus chaque reponse
  brute de la source sur le disque ; `butbutbut --replay match.jsonl` la
  ressort, cartes et sons compris, sans reseau, en respectant les ecarts de
  temps entre releves. `--speed 60` fait passer une heure de match en une
  minute. De quoi mettre au point l'affichage sans attendre un samedi soir,
  reproduire un bug ("chez moi la carte deborde sur ce match-la") et fabriquer
  les captures du README - `--test` ne montrait que des cartes figees.
- Le format du fichier est du **JSON Lines** documente : un en-tete portant un
  numero de format, puis une ligne par releve avec son horodatage et le code de
  la competition. Une ligne illisible - la derniere d'une session tuee en plein
  match - est comptee et ignoree, le reste se rejoue. Un fichier ecrit par une
  version future dit clairement pourquoi il ne passe pas, au lieu de partir de
  travers.
- Un nom de fichier en `.gz` est compresse a l'ecriture et decompresse a la
  lecture, des deux cotes : du JSON d'API se comprime autour de vingt fois, et
  une soiree de Ligue 1 pese sinon des dizaines de mega-octets.

### Change

- Le rejeu ne court-circuite pas la surveillance : il remplace la **source**
  (l'`opener` injectable de `espn.fetch`) et laisse le watcher, la detection des
  buts, les cartes, le son et le journal faire exactement ce qu'ils font un
  samedi soir. Un rejeu qui prendrait un raccourci ne testerait que lui-meme.
  C'est ce que verifie le test central : un match joue en direct contre une
  source simulee, enregistre, puis rejoue, doit rendre la meme suite
  d'evenements, a la ligne de journal pres.
- Le journal, le fichier d'etat et le fichier pid d'un rejeu sont detournes d'un
  bloc vers un sous-dossier `replay/` du dossier de donnees. Un match d'il y a
  trois semaines rejoue ce matin n'a rien a faire dans `--today`, et un rejeu ne
  reclame pas le fichier pid de l'instance unique : on peut donc rejouer un
  match pendant que le vrai daemon tourne. Le detournement se prend a la racine,
  dans `paths()`, pour qu'aucun appelant ne puisse l'oublier.
- Une reponse identique a la precedente n'est plus reecrite : la ligne se resume
  a son horodatage et a un marqueur `repeat`. L'heure du releve est gardee -
  c'est elle qui porte la cadence, et la perdre changerait le rythme du rejeu.

### Corrige

- La derniere carte pouvait ne jamais s'afficher : un but depose dans la file
  juste apres que la boucle d'affichage l'a trouvee vide, et juste avant que le
  fil de surveillance s'arrete, partait avec la fenetre. Invisible au quotidien
  (le daemon s'arrete quand on le lui demande, pas au dernier but), mais un
  rejeu s'arrete de lui-meme sur le dernier releve : le "FIN DU MATCH" manquait
  une fois sur cinq.

### Interne

- `espn.download()` sort du corps de `espn.fetch()` : il n'y a plus qu'un seul
  endroit ou le reseau est touche, et c'est ce que l'enregistrement enrobe.
- Le `Watcher` accepte une horloge monotone injectable, a cote de l'horloge
  murale qu'il avait deja. C'est ce qui permet a un rejeu d'accelerer le temps
  sans qu'une seule ligne des deux boucles de surveillance ne change : elles
  continuent d'appeler `tick()` et `plan_wait()`, et l'attente qu'on leur passe
  avance l'horloge de l'enregistrement.
- 573 -> **627 tests**.



### Ajoute

- **Le hockey sur glace et le rugby a XV**, a la demande. Le tableau de bord
  d'ESPN a la meme forme pour tous les sports, seul le premier segment de
  l'URL change : `soccer/fra.1`, `hockey/nhl`, `rugby/180659`. Dix
  competitions de plus, verifiees une par une contre la source - la NHL, et
  neuf competitions de rugby (Tournoi des Six Nations, Top 14, Premiership,
  URC, Champions Cup, Rugby Championship, Super Rugby, Coupe du monde, matchs
  internationaux).
- Trois nouvelles facons de choisir : `--leagues hockey` ou `--leagues rugby`
  prend un sport entier, `--leagues foot` le football seul, et
  `--leagues all-sports` (ou `tous-sports`) prend vraiment tout.
- **Le vocabulaire des cartes suit le sport, dans les cinq langues.** Un essai
  s'annonce `ESSAI !` et vaut cinq points, une transformation `TRANSFORMATION`,
  une penalite `PENALITE`, un drop `DROP` ; le hockey garde `BUT !` - un but de
  hockey est un but - mais commence par une `MISE AU JEU` et souffle a la
  `FIN DU TIERS-TEMPS`, n'ayant pas de mi-temps mais deux pauses entre trois
  tiers-temps. Une carte de rugby dont l'action n'est pas encore publiee
  annonce `POINTS !` et dit de combien : `+5 points`.
- L'echappatoire vise maintenant un autre sport : `--leagues hockey:nhl`,
  `--leagues rugby:270565`, `--leagues hockey/mens-college-hockey`. Sans
  prefixe, c'est toujours du football.
- `butbutbut --list` affiche les autres sports dans leurs propres groupes, et
  `--status` ajoute une ligne `sports` quand on en suit plusieurs.
- Un sport ecarte expres explique pourquoi plutot que de repondre "inconnu" :
  `--leagues basketball:nba` renvoie qu'un panier toutes les trente secondes
  ferait de butbutbut une alarme et non une notification.

### Change

- **`--leagues all` reste tout le catalogue de football**, et n'interroge donc
  pas la NHL. Quelqu'un qui tapait `all` pour suivre les coupes nationales ne
  doit pas se retrouver, apres une simple mise a jour, avec des cartes de
  hockey a deux heures du matin : une mise a jour ne change pas ce qu'on suit.
  C'est `all-sports` qui prend tout.
- Une action porte desormais elle-meme sa cle de vocabulaire et sa valeur en
  points : le reste du programme n'a plus jamais a se demander de quel sport
  vient la carte qu'il ecrit.
- Quand plusieurs actions tombent entre deux releves, c'est la plus chere qui
  est annoncee et non la derniere : un essai transforme (sept points d'un coup)
  affiche `ESSAI !`, pas `TRANSFORMATION`.

### Corrige

- `--today` relit maintenant les buts contre son camp et les buts sur penalty,
  que leur en-tete de journal (`BUT CONTRE SON CAMP`, `BUT SUR PENALTY`)
  faisait passer a travers le filet depuis toujours.


## [1.6.0] - 2026-09-07

### Ajoute

- **La ligne de commande parle elle aussi les cinq langues.** `--help`,
  `--status`, `--scores`, `--screens`, `--list` et `--today` suivent la langue
  retenue, cartes comprises. Les *valeurs* aussi, pas seulement les etiquettes
  devant : `last poll : il y a 12 s` ne se lit plus a moitie en francais.
- La description du parseur, les metavariables (`CHEMIN`, `LISTE`, `COIN`...)
  et les noms de langue affiches par `--status` sont traduits.

### Change

- **La langue est desormais reglee avant la construction du parseur.** Les
  textes d'aide d'argparse sont traduits au moment ou on les lui donne : les
  fixer apres l'analyse laissait `--help` en francais quoi qu'on demande, et
  seule la variable `BUTBUTBUT_LANG` fonctionnait. `--lang de --help` sort
  maintenant en allemand.
- L'aide de `--lang` ne promet plus que "cette aide reste en francais" :
  c'est precisement ce qui a change. Le journal, lui, reste francais.

### Corrige

- Les tests de `--status` epinglent la langue par l'environnement. Ils
  lancaient la ligne de commande sans `--lang` tout en affirmant des libelles
  francais : ils passaient sur une machine francaise et auraient echoue sur
  l'integration continue, dont les machines sont anglaises.

## [1.5.0] - 2026-09-07

### Ajoute

- **Les cartes parlent la langue de la machine** : francais, anglais, espagnol,
  italien, allemand - les cinq langues des cinq grands championnats - et le
  francais quand ce n'est aucune des cinq. Un but en Bundesliga s'affiche
  `TOR!` / `Tor von F. Rieder` sur une machine allemande.
- Le nom des competitions suit quand il se traduit : la Ligue des champions
  devient CHAMPIONS LEAGUE, la Coupe du monde WELTMEISTERSCHAFT. Celles dont
  le nom est un nom propre sont laissees tranquilles - Bundesliga, Serie A,
  Coupe de France s'ecrivent pareil partout.
- `--lang de`, la cle `lang` du fichier de configuration, ou la variable
  d'environnement `BUTBUTBUT_LANG`. `--status` affiche la langue retenue, et une
  langue inconnue est refusee au demarrage avec la liste de celles qu'on parle.
- **Le README existe en anglais** ([README.en.md](README.en.md)), avec un
  renvoi croise en tete des deux versions.

### Change

- **Le journal reste en francais, quelle que soit la langue des cartes.** Il
  voisine la ligne de commande, qui n'est pas traduite, et surtout `--today` le
  relit : un fichier ecrit avant un changement de langue resterait sinon a
  moitie illisible pour le relecteur. Une carte peut donc afficher `TOR!`
  pendant que le journal note `BUT`.
- Le compte a rebours d'avant match est fige en secondes et non en texte : fige
  en francais, il n'aurait pu etre rendu ni dans la langue de la carte ni dans
  celle du journal, qui n'en veulent pas la meme.
- Sous Windows, l'API systeme passe avant les variables `LANG` : un shell comme
  Git Bash pose `LANG=en_US` quoi qu'il arrive, ce qui rendait la detection
  aveugle a la langue reelle de la machine.

### Corrige

- Le paragraphe du journal apparaissait deux fois dans le README, chaque moitie
  venant d'une PR differente fusionnee le meme jour. Repere par la relecture
  pour la traduction anglaise.

### Interne

- La langue par defaut dependant de la machine, les trois modules de tests qui
  affirment une formulation epinglent la leur. Sans ca la suite passait sur une
  machine francaise et echouait sur la CI, dont les machines sont anglaises :
  elle tourne desormais a l'identique en fr, en, es, it et de.
- 459 -> **498 tests**.

## [1.4.0] - 2026-09-06

Premiere contribution exterieure au projet, par
[@Arzaroth](https://github.com/Arzaroth) : la mise a jour sans reinstaller.

### Ajoute

- **Mise a jour automatique**, sur le modele de
  [doot](https://github.com/boubou666/doot) : `butbutbut --update` recupere la
  derniere version, rejoue l'installeur et relance le daemon ;
  `butbutbut --check-update` se contente de dire si une version plus recente
  existe.
- L'installeur depose une fiche `install.json` dans le dossier de donnees :
  d'ou vient le code, quel commit, et **avec quelles options**. `--update` la
  relit, donc une mise a jour rejoue les memes competitions, le meme coin et la
  meme cadence - qui suivait `l1,pl,ucl` ne se retrouve pas ramene aux cinq
  grands championnats, ni le daemon relance sans sa selection.
- C'est la **derniere release** qui est installee, depliee depuis son archive.
  Le depot clone n'est pas touche dans ce mode : l'amener sur l'etiquette
  demanderait de le laisser en HEAD detachee, et il appartient a son
  proprietaire. `--dev` vise la pointe de la branche principale, et la le clone
  sert s'il est encore la (`git pull --ff-only`), l'archive de `main` prenant
  le relais sinon. Cette seconde voie ne demande ni git ni le clone d'origine :
  une installation dont le dossier a ete efface se met a jour quand meme.
- `--check-update` et `--update` visent enfin la meme chose : des versions par
  defaut, des commits avec `--dev`. La premiere mouture annoncait une release
  et installait la pointe de `main`.
- `--update` refuse d'ecraser une installation qui ne vient pas des scripts et
  renvoie vers l'outil qui la gere : `pipx upgrade butbutbut`,
  `pip install --upgrade butbutbut`, ou le gestionnaire de paquets de la
  distribution.

### Corrige

- **La publication PyPI ne pouvait pas se declencher.** Elle vivait dans un
  workflow separe ecoutant `release: published`, or Actions refuse qu'un
  evenement produit par le `GITHUB_TOKEN` declenche un autre workflow : une
  release creee par `github-actions[bot]` ne reveille personne. Constate en
  poussant `v1.3.0`, ou le workflow `pypi` n'a meme pas eu de run. La
  publication est desormais le second job de `release.yml`, declenche par le
  push du tag - un evenement humain, qui declenche bien. Les deux jobs vivent
  dans `pypi.yml`, et `release.yml` disparait : un publisher de confiance PyPI
  autorise UN nom de fichier de workflow, et c'est celui-la qui est declare
  cote pypi.org. Le declenchement manuel du meme workflow sert de rattrapage.
  Le README ne promet plus un automatisme qui n'existait pas.
- L'installeur arrete le daemon avant de remplacer le code. Il continuait
  jusque-la sur des fichiers effaces, et ne reprenait le nouveau code qu'a la
  session suivante.
- Une mise a jour interrompue rend le daemon. Le redemarrage vit desormais
  dans un `finally` : un telechargement coupe ou un installeur en echec
  laissait sinon la surveillance eteinte jusqu'a la session suivante, sans que
  personne s'en apercoive.
- `--update` explique ce qui a echoue au lieu d'imprimer une pile d'appels.
- **L'installeur n'ecrase plus le fichier de configuration.** Il posait ses
  valeurs par defaut en arguments du service de demarrage (`--position`,
  `--interval`), et la ligne de commande l'emportant toujours sur le fichier,
  ces deux reglages de `butbutbut.conf` etaient ignores en silence. Il ne pose
  desormais que les options qu'on lui passe, `--quiet` excepte. Le bug touchait
  deja `./install.sh` rejoue a la main, avant meme l'arrivee de `--update`.

## [1.3.0] - 2026-09-06

Sept chantiers menes en parallele, chacun dans sa branche, fusionnes ensemble.

### Ajoute

- **Ecussons et couleurs des clubs sur la carte** : l'equipe qui marque prend
  la couleur de son club, le filet vertical garde celle de la competition. La
  couleur n'est retenue que si elle se lit sur le fond sombre (luminance WCAG,
  seuil 3.5) ; sinon on descend sur la couleur secondaire, puis sur celle du
  championnat - le noir sur noir du Paris FC finit ainsi en jaune Ligue 1. Les
  ecussons viennent d'un cache disque et ne sont **jamais** attendus : une
  carte sans ecusson s'affiche tout de suite et le telechargement se fait en
  fond pour la prochaine fois. `--no-logos`.
- **Fichier de configuration** (`butbutbut --write-config`) : plus besoin de
  relancer l'installeur pour changer de championnat. La ligne de commande garde
  toujours la priorite, y compris quand elle retape une valeur par defaut.
- **Cartons rouges** (`--red-cards`), **annonce d'avant-match**
  (`--before-kickoff N`, une seule fois par match) et **carte de fin de match
  avec les buteurs**. Aucune des trois ne fait de bruit : seul un but declenche
  le son.
- **Fichier d'etat et `--today`** : `--status` dit maintenant quand a eu lieu
  le dernier releve, quels matchs sont en cours et combien de buts sont tombes
  aujourd'hui, avec un avertissement quand le releve est trop vieux pour la
  cadence annoncee. `--today` recapitule la journee en relisant le journal, la
  seule trace qui survive a un redemarrage.
- **Publication PyPI** en Trusted Publishing, dans un workflow separe et inerte
  tant que le proprietaire du depot ne l'a pas arme (voir README).

### Corrige

- **Plus de fausses cartes en sortant de veille.** Apres une suspension, la
  source avait des heures d'avance sur notre derniere photo : le daemon criait
  un but avec un ecart de trois et une minute perimee. Un trou d'horloge remet
  desormais les competitions a l'etat "jamais photographie", ce qui reutilise le
  chemin silencieux du premier releve. La detection compare le temps reellement
  ecoule a l'attente annoncee, et non `time.monotonic()` a `time.time()` : la
  semantique de monotonic vis-a-vis de la veille differe entre Windows et Linux,
  ce detecteur-la aurait ete faux d'un cote.
- **Une carte masquee par une application en plein ecran est signalee.** Une
  fenetre `topmost` passe derriere un jeu ou un lecteur en plein ecran
  exclusif : le but etait rate en silence. Detecte sous Windows, note au
  journal, et `--retry-fullscreen` repasse la carte des que l'ecran se libere.
- Les liens relatifs du README auraient tous ete morts sur la fiche PyPI, et le
  sdist embarquait les tests sans `tests/helpers.py` : ils ne demarraient meme
  pas.
- Le fichier de configuration ignorait quatre options ajoutees en parallele par
  d'autres branches. Un test verifie desormais que toute option durable du
  parseur a sa cle.

### Interne

- 179 -> **403 tests**, toujours sans reseau ni ecran.


## [1.2.0] - 2026-09-06

### Ajoute

- **Filtre par equipe** : `--teams om,psg` ne signale que les matchs de ces
  clubs, `--exclude-teams psg` ne signale que les autres. Un match compte des
  qu'une des deux equipes y est, buts et cartes de deroulement comprises, et
  `--scores` s'y plie aussi.
- La reconnaissance des noms encaisse le nom complet, le nom court,
  l'abreviation de la source, les accents (`malaga` trouve Malaga), un debut de
  mot a partir de quatre lettres, et une table de surnoms usuels (`om`, `ol`,
  `asse`, `losc`, `manu`, `barca`, `juve`, `bvb`...). Un mot ne mord qu'au
  debut d'un mot du nom : `real` designe Madrid, Sociedad et Betis, mais pas
  Villarreal.
- Un mot qui ne designe aucune equipe est refuse au demarrage, avec la liste
  des competitions ou il a ete cherche - plutot qu'un daemon muet pour
  toujours.
- `--list-teams` liste les equipes des competitions suivies et marque celles
  que le filtre attrape (`*` suivie, `-` exclue).
- Une banniere en tete du README : deux supporters ahuris qui pointent cinq
  ecrans affichant tous un but. Dessinee en vectoriel
  ([docs/banniere.svg](docs/banniere.svg), genere par
  [docs/banniere.py](docs/banniere.py)), aux couleurs des cartes, et
  rasterisee en PNG pour l'affichage sur GitHub.

## [1.1.1] - 2026-09-06

### Corrige

- **`--status`, `--scores` et `--test` plantaient en 1.1.0** avec un
  `NameError`. En retirant la fonction devenue inutile qui deduisait les coups
  d'envoi, le decoupage a emporte les quatre fonctions voisines, dont
  `do_status`. La surveillance et les cartes, elles, n'etaient pas touchees :
  seuls ces trois commandes l'etaient. **Passer directement de 1.0.x a 1.1.1.**
- Un test verifie desormais que chaque commande appelee par `main()` existe
  bel et bien, et chaque commande est executee au moins une fois avec la source
  simulee. La suite passait sur la 1.1.0 cassee parce qu'aucun test n'entrait
  dans ces commandes : c'est cette lacune qui est comblee.

## [1.1.0] - 2026-09-06

### Ajoute

- Cartes de deroulement du match : **coup d'envoi**, **mi-temps**, **reprise**
  et **fin du match**. Volontairement plus sobres qu'un but (titre gris, pas de
  troisieme ligne, aucune equipe mise en avant) et surtout **sans aucun son** :
  seul un but declenche la corne. La phase est lue dans `status.type.name` de
  la source (`STATUS_HALFTIME`, `STATUS_SECOND_HALF`, `STATUS_FULL_TIME`...),
  et la mi-temps des prolongations compte comme une mi-temps.
- `--no-phase-cards` pour n'avoir que les buts a l'ecran. Le journal continue
  d'enregistrer ces moments.
- Un match jamais vu en cours ne declenche pas de carte de fin, et un match
  reporte ou abandonne reste muet.
- Badges CI, release, Python et licence dans le README, plus une capture de
  trois cartes empilees.

### Corrige

- **Le nom de l'equipe pouvait sortir de la carte par la gauche.** Le score est
  centre dans la carte, mais la largeur reservee aux noms suivait la somme des
  deux : des que l'un etait bien plus long que l'autre, il debordait
  (`Eintracht Frankfurt 1 - 4 FC Augsburg`). La place reservee est desormais la
  meme de chaque cote, ce qui rend le debordement impossible par construction ;
  des noms a rallonge sont raccourcis avec des points de suspension plutot que
  de sortir du cadre.
- Un but annule ne declenchait plus de son que dans la documentation : le
  daemon le jouait quand meme. Seul un vrai but fait du bruit.

### Change

- Les lignes de journal « coup d'envoi » et « fin du match », qui etaient
  deduites d'une comparaison de listes dans la boucle, viennent maintenant des
  memes evenements que les cartes. Un seul chemin, une seule verite.

## [1.0.1] - 2026-09-06

### Corrige

- `install.ps1` : la verification de connexion a la source echouait sur
  Windows. PowerShell mange les guillemets doubles internes en passant a un
  exe natif, et `2>$null` sur une commande native emballe la sortie d'erreur
  dans un `ErrorRecord` qui, avec `ErrorActionPreference = Stop`, faisait
  echouer l'installation entiere. L'URL passe desormais par `argv` et les
  appels a python passent par un helper qui neutralise les deux pieges.
- `install.sh` et `uninstall.sh` : `[ test ] && variable=1` sous `set -e`
  faisait sortir le script quand le test etait faux (aucune option passee).
  Remplace par des `if`.
- `uninstall.sh --help` desinstallait au lieu d'afficher l'aide : les
  arguments sont maintenant analyses.
- Le test `play_async` sur un fichier absent verifiait la mauvaise chose : le
  contrat est de ne jamais lever, pas de rendre `None`. Il echouait sur macOS,
  ou `afplay` est bien lance et echoue de son cote.

## [1.0.0] - 2026-09-06

Premiere version.

### Ajoute

- Surveillance en fond des cinq grands championnats europeens : Ligue 1,
  Premier League, LaLiga, Serie A, Bundesliga.
- Carte de score a l'ecran a chaque but : championnat, minute,
  `Equipe A score - score Equipe B`, et le buteur. L'equipe qui vient de
  marquer et son chiffre prennent la couleur du championnat, le nom du buteur
  ressort en clair.
- Les cartes s'empilent depuis le coin choisi (`bottom-right` par defaut) : la
  derniere arrivee est collee au coin, les precedentes remontent, et quand
  l'une s'efface les autres reprennent sa place. Cinq cartes visibles au plus.
- Son a chaque but : le mp3 fourni, un fichier perso depose dans le dossier
  `sound`, ou une corne de stade synthetisee en dernier recours. Un seul coup
  de corne quand plusieurs buts remontent dans le meme releve.
- Catalogue de 36 competitions, toutes verifiees contre la source : coupes
  d'Europe (`ucl`, `uel`, `uecl`, supercoupe), selections (Coupe du monde,
  Ligue des nations, qualifications), deuxiemes divisions (Ligue 2,
  Championship, Serie B, 2. Bundesliga, LaLiga 2), autres championnats
  europeens (Portugal, Eredivisie, Belgique, Super Lig, Ecosse), coupes
  nationales (Coupe de France, FA Cup, Carabao, Copa del Rey, Coppa Italia,
  DFB-Pokal) et hors d'Europe (MLS, Liga MX, Bresil, Argentine, Saudi,
  J.League, Libertadores, Concacaf).
- `--leagues` pour choisir, `--exclude` pour retirer, `--list` pour voir le
  catalogue et ses alias. Les mots-cles `all` et `big5` sont acceptes.
- N'importe quel code ESPN passe a la volee (`--leagues gre.1`) : la
  competition prend le nom que la source annonce au premier releve.
- Detection : un score qui monte est un but. Les actions de la source ne
  servent qu'a habiller la carte (buteur, minute, csc, penalty), jamais a
  detecter, car elles arrivent parfois quelques secondes plus tard.
- Le premier releve est silencieux : lancer le daemon en pleine journee de
  championnat ne rejoue pas les buts deja marques.
- Un score qui descend (but refuse par la VAR) affiche une carte orange
  `BUT ANNULE`, sans son.
- Cadence adaptative et independante par competition : 25 s quand un match est
  en cours, 60 s a l'approche d'un coup d'envoi, 5 min au repos. Les releves
  sont decales les uns des autres pour ne pas tirer trente-six requetes en
  rafale.
- Attente doublee a chaque echec reseau (plafond 5 min), reprise notee dans le
  journal.
- `--scores` pour les matchs du jour dans le terminal, `--status` pour l'etat
  complet (daemon, son, ecrans, connexion), `--test N` pour voir des cartes
  s'empiler, `--stop`, `--paths`, `--screens`.
- Multi-ecrans : les ecrans sont enumeres via l'API systeme
  (`EnumDisplayMonitors`, `xrandr --listmonitors`, CoreGraphics), pas via
  tkinter, pour qu'une carte ne se retrouve jamais a cheval sur deux dalles.
- Fenetres sans bordure, toujours au-dessus, qui ne volent jamais le focus ;
  fond transparent et clics traversants sous Windows.
- Instance unique via fichier pid, journal horodate, `--quiet` pour n'ecrire
  que dans le journal.
- Installation par plateforme : `install.sh` (systemd utilisateur, LaunchAgent
  macOS, autostart `.desktop`), `install.ps1` (raccourci de demarrage, PATH
  utilisateur, sans droits admin), PKGBUILD Arch.
- 113 tests, sans reseau ni ecran : la source est simulee, la geometrie de
  l'empilement est testee sans tkinter.

[Non publie]: https://github.com/boubou666/butbutbut/compare/v1.6.0...HEAD
[1.6.0]: https://github.com/boubou666/butbutbut/compare/v1.5.0...v1.6.0
[1.5.0]: https://github.com/boubou666/butbutbut/compare/v1.4.0...v1.5.0
[1.4.0]: https://github.com/boubou666/butbutbut/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/boubou666/butbutbut/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/boubou666/butbutbut/compare/v1.1.1...v1.2.0
[1.1.1]: https://github.com/boubou666/butbutbut/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/boubou666/butbutbut/compare/v1.0.1...v1.1.0
[1.0.1]: https://github.com/boubou666/butbutbut/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/boubou666/butbutbut/releases/tag/v1.0.0
