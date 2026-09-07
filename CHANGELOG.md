# Changelog

Toutes les evolutions notables de butbutbut sont consignees ici.

Le format suit [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/),
et le projet respecte le [versionnage semantique](https://semver.org/lang/fr/).

## [Non publie]

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
