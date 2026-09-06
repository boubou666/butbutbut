# Changelog

Toutes les evolutions notables de butbutbut sont consignees ici.

Le format suit [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/),
et le projet respecte le [versionnage semantique](https://semver.org/lang/fr/).

## [Non publie]

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

[Non publie]: https://github.com/boubou666/butbutbut/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/boubou666/butbutbut/compare/v1.1.1...v1.2.0
[1.1.1]: https://github.com/boubou666/butbutbut/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/boubou666/butbutbut/compare/v1.0.1...v1.1.0
[1.0.1]: https://github.com/boubou666/butbutbut/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/boubou666/butbutbut/releases/tag/v1.0.0
