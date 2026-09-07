![Deux supporters ahuris pointent du doigt cinq ecrans qui affichent tous un but](https://raw.githubusercontent.com/boubou666/butbutbut/main/docs/banniere.png)

*Ce projet est aussi documente en [anglais](README.en.md).*

# butbutbut

[![ci](https://github.com/boubou666/butbutbut/actions/workflows/ci.yml/badge.svg)](https://github.com/boubou666/butbutbut/actions/workflows/ci.yml)
[![release](https://img.shields.io/github/v/release/boubou666/butbutbut)](https://github.com/boubou666/butbutbut/releases)
[![python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![pypi](https://img.shields.io/pypi/v/butbutbut)](https://pypi.org/project/butbutbut/)
[![licence](https://img.shields.io/badge/licence-MIT-green)](https://github.com/boubou666/butbutbut/blob/main/LICENSE)

Un but tombe en **Ligue 1**, **Premier League**, **LaLiga**, **Serie A** ou
**Bundesliga** : le son part, et une carte s'affiche en bas a droite de ton
ecran avec le score et le buteur.

![Trois cartes empilees en bas a droite de l'ecran](https://raw.githubusercontent.com/boubou666/butbutbut/main/docs/cartes.png)

Chaque equipe porte son **ecusson**, l'equipe qui vient de marquer et son
chiffre passent a la **couleur de son club**, le filet vertical garde celle de
la competition et le nom du buteur ressort en clair. Deux buts en meme temps ne
se marchent pas dessus : les cartes s'empilent depuis le coin. Les temps forts
du match (coup d'envoi, mi-temps, reprise, fin) ont droit a une carte plus
discrete, sans son : c'est la troisieme ci-dessus.

Le **hockey sur glace** et le **rugby a XV** sont dans le catalogue eux aussi,
a la demande : `butbutbut --leagues nhl,top14`. Le football reste le defaut
absolu, rien ne s'invite. Voir [Les sports](#les-sports).

Comme [doot](https://github.com/boubou666/doot) : **zero dependance**, rien que
la bibliotheque standard de Python, et ca tourne sur Windows, macOS et Linux.

---

## Installation

### Avec pipx, sans cloner (tous systemes)

```bash
pipx install butbutbut
butbutbut
```

`pip install --user butbutbut` fait la meme chose. Les deux commandes
`butbutbut` et `but` arrivent dans le PATH, et le son est embarque dans le
paquet : zero dependance, rien d'autre a telecharger.

Ce que pipx ne fait pas, en revanche : le **demarrage automatique** a
l'ouverture de session. Pour l'avoir, ce sont les scripts ci-dessous.

> Cette methode ne marchera qu'a partir de la premiere version envoyee sur
> PyPI. Le depot est pret, il reste une manipulation cote pypi.org :
> [Publication sur PyPI](#publication-sur-pypi).

### Linux (Arch, Debian/Ubuntu, Fedora, openSUSE...) et macOS

```bash
git clone https://github.com/boubou666/butbutbut
cd butbutbut
./install.sh
```

Options : `--no-autostart`, `--leagues l1,pl`, `--position top-right`,
`--interval 25`.

Le script installe la commande dans `~/.local/bin`, puis active le demarrage
automatique a l'ouverture de session : unite **systemd utilisateur** sous
Linux, **LaunchAgent** sous macOS, `.desktop` d'autostart en dernier recours.

### Windows 10/11

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

Options : `-NoAutostart`, `-Leagues "l1,pl"`, `-Position top-right`,
`-Interval 25`. Pas besoin de droits admin : tout va dans
`%LOCALAPPDATA%\Programs\butbutbut` et un raccourci est pose dans le dossier
Demarrage.

### Arch Linux (paquet natif)

```bash
cd packaging && makepkg -si
systemctl --user enable --now butbutbut.service
```

### Sans rien installer

```bash
python -m butbutbut --test 3
```

---

## Utilisation

```bash
butbutbut                     # surveille en fond (comportement par defaut)
butbutbut --test              # une carte de demonstration
butbutbut --test 3            # trois cartes, pour voir l'empilement
butbutbut --scores            # les matchs du jour dans le terminal
butbutbut --list              # les competitions surveillables
butbutbut --list-teams        # les equipes des competitions suivies
butbutbut --status            # daemon, dernier releve, matchs en cours, son, ecrans
butbutbut --today             # les buts signales aujourd'hui
butbutbut --stop              # arrete le daemon
butbutbut --check-update      # une version plus recente existe-t-elle ?
butbutbut --update            # recupere, reinstalle, relance le daemon
butbutbut --update --dev      # idem, mais la pointe de la branche principale
butbutbut --paths             # ou vivent les donnees et le journal
butbutbut --write-config      # ecrit un fichier de configuration d'exemple
butbutbut --screens           # les ecrans detectes
```

La commande s'appelle aussi `but`, en plus court.

### Choisir les competitions

Par defaut : les cinq grands championnats. `--leagues` en choisit,
`--exclude` en retire :

```bash
butbutbut --leagues l1,pl                 # seulement ces deux-la
butbutbut --exclude liga,seriea           # les 5 grands moins deux
butbutbut --leagues l1,ligue2,ucl,cdf     # Ligue 1 + Ligue 2 + C1 + Coupe de France
butbutbut --leagues all                   # tout le catalogue de football
butbutbut --leagues big5                  # les 5 grands, explicitement
butbutbut --leagues nhl,top14             # et hors du football
butbutbut --leagues all-sports            # vraiment tout
```

Le catalogue va bien au-dela des cinq grands : **36 competitions** de football
verifiees contre la source, dont

| Famille | Exemples (noms acceptes) |
| --- | --- |
| Coupes d'Europe | `ucl`/`c1`, `uel`/`europa`, `uecl`/`conference`, `supercoupe` |
| Selections | `cdm`/`mondial`, `nations`, `qualifs` |
| 2es divisions | `ligue2`/`l2`, `championship`, `serieb`, `bundesliga2`, `liga2` |
| Europe | `portugal`, `eredivisie`, `belgique`, `superlig`, `ecosse` |
| Coupes nationales | `cdf`/`coupedefrance`, `facup`, `carabao`, `copa`, `coppa`, `dfb` |
| Hors d'Europe | `mls`, `ligamx`, `bresil`, `argentine`, `saudi`, `jleague`, `libertadores` |

`butbutbut --list` affiche le catalogue complet avec les alias.

**Et une competition qui n'y est pas ?** Passe directement son code ESPN, il
sera suivi quand meme :

```bash
butbutbut --leagues gre.1        # Greek Super League
butbutbut --leagues aus.1,den.1  # A-League, Superliga danoise
```

Le nom affiche sur la carte est alors celui que la source annonce, recupere au
premier releve (`gre.1` devient « GREEK SUPER LEAGUE »).

> Attention quand meme : `--leagues all`, c'est 36 endpoints a interroger. La
> cadence adaptative fait le gros du travail (une competition sans match est
> relue toutes les 5 minutes seulement), mais reste raisonnable.

---

## Les sports

butbutbut suit aussi le **hockey sur glace** et le **rugby a XV**. Ni l'un ni
l'autre ne s'invite : le football reste le defaut absolu, et `butbutbut` tout
court continue de suivre les cinq grands championnats et rien d'autre.

```bash
butbutbut --leagues nhl                 # la NHL
butbutbut --leagues top14,6nations      # Top 14 et Tournoi
butbutbut --leagues l1,nhl              # les deux en meme temps
butbutbut --leagues hockey              # tout le hockey du catalogue
butbutbut --leagues rugby               # tout le rugby du catalogue
```

| Sport | Competitions (noms acceptes) |
| --- | --- |
| Hockey sur glace | `nhl`/`lnh` |
| Rugby a XV | `6nations`/`tournoi`, `top14`, `prem`, `urc`, `champions-cup`, `trc`, `superrugby`, `rwc`, `testmatch` |

### Ce que `all` veut dire

**`--leagues all` reste tout le catalogue de football**, exactement ce qu'il
designait avant. Deux raisons, et la premiere suffit :

- **personne n'a demande la NHL.** Quelqu'un qui tapait `--leagues all` pour
  suivre les coupes nationales ne doit pas se retrouver, apres une simple mise
  a jour, avec des cartes de hockey a deux heures du matin. Une mise a jour ne
  change pas ce qu'on suit ;
- `all`, c'est deja 36 endpoints. Y verser les autres sports en ferait 46 sans
  que ce soit un choix.

Pour vraiment tout : `--leagues all-sports` (ou `tous-sports`). Et
`--leagues foot` designe le football seul, comme `all`.

### Pourquoi ces sports-la, et pas le basket

Le modele de butbutbut tient en une phrase : **un score qui monte, c'est un
evenement qui merite un son**. Un sport n'entre ici que s'il tient dans cette
phrase.

| Sport | Rythme | Verdict |
| --- | --- | --- |
| Football | un but toutes les ~45 min | le defaut |
| Hockey sur glace | un but toutes les ~10 min | parfait |
| Rugby a XV | 5 a 8 actions de points par match, qui ne se valent pas | parfait |
| Basket | **un panier toutes les 20 a 30 s** | ecarte |

Une carte et une corne de stade au rythme d'un match NBA (environ 220 points)
ne sont plus une notification, c'est une alarme incendie : au bout de dix
minutes on coupe le son, au bout de vingt on desinstalle. Rendre le basket
supportable demanderait de **changer le modele**, pas d'ajouter une ligne au
catalogue : il faudrait ne signaler que ce qui compte - un 3-points decisif, un
ecart qui bascule, les deux dernieres minutes d'un match serre -, donc juger de
l'importance d'une action, donc lire autre chose que le score. C'est un autre
programme. `--leagues basketball:nba` est donc refuse, avec cette raison en
clair.

Le meme raisonnement ecarte le handball (60 buts par match) et le tennis (un
score qui n'est pas un entier qui monte). Le football americain et le baseball
tomberaient dans la bonne cadence mais pas dans le bon modele : un touchdown
vaut 6 points puis 1 de plus une minute apres, et un score qui monte de 6 puis
de 1 ferait deux cartes pour une seule action.

### Le vocabulaire suit le sport

Un but de hockey n'est pas un essai de rugby, et un essai vaut cinq points :
le titre, le texte du buteur et le delta suivent le sport, dans les cinq
langues.

```
ESSAI !   TOP 14                                              63'
Stade Toulousain      19 - 14      Stade Francais
Essai de A. Dupont
```

| | Football | Hockey | Rugby |
| --- | --- | --- | --- |
| Un score qui monte | `BUT !` | `BUT !` | `ESSAI !`, `TRANSFORMATION`, `PENALITE`, `DROP` |
| Debut du match | `COUP D'ENVOI` | `MISE AU JEU` | `COUP D'ENVOI` |
| Pause | `MI-TEMPS` | `FIN DU TIERS-TEMPS` | `MI-TEMPS` |
| Score corrige | `BUT ANNULE` | `BUT ANNULE` | `POINTS RETIRES` |

Un but de hockey **est** un but : le hockey ne reformule que ce qui differe
vraiment, c'est-a-dire ses pauses - il n'a pas de mi-temps, il a deux pauses
entre trois tiers-temps. Le rugby, lui, garde le vocabulaire du football pour
le deroulement du match (il a bien deux mi-temps) et n'apporte que ses actions.

### Ce que chaque sport publie vraiment

Les trois ont ete verifies contre la source, endpoint par endpoint. Ils ne
disent pas la meme chose, et butbutbut ne fait jamais semblant du contraire.

| | Football | Hockey | Rugby |
| --- | --- | --- | --- |
| Score, horloge, phase | oui | oui | oui |
| Ecusson, couleurs du club | oui | oui | oui (une seule couleur) |
| Tableau d'actions | oui | **non** | oui, mais sans drapeaux |
| Buteur, minute de l'action | oui | **non** | oui |
| Cartons rouges (`--red-cards`) | oui | sans objet | oui |

**Le hockey ne publie aucun tableau d'actions** - ni pendant le match, ni
apres. On a le score, l'horloge et la periode ; jamais le buteur. La carte le
dit en ne disant rien : elle affiche le score et la minute, sans troisieme
ligne. Mieux vaut une carte honnete qu'un nom invente.

**Le rugby publie tout, mais sans un seul drapeau** : la ou le football marque
un but par `scoringPlay` et une expulsion par `redCard`, le rugby ne donne
qu'un `type.id` (1 essai, 2 transformation, 3 penalite, 4 drop, 6 carton
rouge). Lu avec le lecteur du football, un match de rugby n'aurait aucune
action du tout - c'est pour ca qu'il a le sien.

Et **ce qui ne s'applique pas s'eteint tout seul** : `--red-cards` sur du
hockey ne plante pas, il ne trouve simplement rien a signaler, la source ne
publiant pas de sanctions. Le carton jaune du rugby, lui, est ignore expres :
c'est une exclusion temporaire de dix minutes, pas une expulsion.

### Un code ESPN dans un autre sport

L'echappatoire marche partout. Sans prefixe, c'est du football - c'est ce que
`--leagues gre.1` a toujours voulu dire, et ca ne change pas. Pour viser un
autre sport, on prefixe par son nom :

```bash
butbutbut --leagues gre.1                        # football (sous-entendu)
butbutbut --leagues hockey:mens-college-hockey   # hockey universitaire
butbutbut --leagues rugby:270565                 # une competition de rugby hors catalogue
butbutbut --leagues hockey/nhl                   # le "/" de l'URL marche aussi
```

La competition prend le nom que la source annonce au premier releve, comme au
football.

### Suivre seulement certaines equipes

```bash
butbutbut --teams om,psg                    # rien que ces deux clubs
butbutbut --teams "real madrid" --leagues liga,ucl
butbutbut --exclude-teams psg               # tout, sauf le PSG
```

Un match compte **des qu'une des deux equipes** y est : suivre l'OM, c'est
aussi vouloir savoir quand l'OM encaisse. Le filtre s'applique aux buts comme
aux cartes de deroulement, et aussi a `--scores`.

Les noms acceptes encaissent ce qu'on tape vraiment :

| On tape | Ce que ca trouve |
| --- | --- |
| `marseille`, `olm` | le nom complet, l'abreviation de la source |
| `om`, `ol`, `asse`, `losc`, `manu`, `barca`, `juve`, `bvb` | les surnoms usuels |
| `malaga`, `atletico`, `alaves` | les noms accentues, sans accent |
| `barce`, `rennai` | un debut de mot (a partir de 4 lettres) |
| `real` | **trois** clubs : Madrid, Sociedad, Betis - mais pas Villarreal |
| `manchester` | les deux Manchester |

Un mot ne mord qu'au **debut d'un mot** du nom : `real` ne va pas chercher
Villar**real**. En dessous de quatre lettres, il faut tomber juste (`bar` est
l'abreviation de Barcelone).

Un mot qui ne designe aucune equipe est refuse au demarrage, avec la liste des
competitions ou il a ete cherche : une faute de frappe ne se traduit pas par un
daemon muet pendant trois semaines. `butbutbut --list-teams --teams om` montre
d'ailleurs ce que chaque mot attrape (`*` suivie, `-` exclue).

### Placer les cartes

```bash
butbutbut --position bottom-right     # defaut
butbutbut --position top-left
butbutbut --screen 1                  # sur le second ecran
butbutbut --scale 1.4                 # cartes plus grandes
butbutbut --opacity 0.9
```

Les cartes s'empilent depuis le coin choisi : la derniere arrivee est collee au
coin, les precedentes remontent (ou descendent, depuis un coin du haut). Au-dela
de cinq cartes visibles, la plus ancienne cede sa place.

### Les ecussons et les couleurs des clubs

La source publie, pour chaque equipe, l'URL de son ecusson et ses deux
couleurs. La carte s'en sert de deux facons.

**L'ecusson**, a cote du nom de son equipe. tkinter lit le PNG tout seul, donc
toujours zero dependance : pas de Pillow. Mais **une carte n'attend jamais le
reseau** - un but doit etre a l'ecran dans la seconde. Les ecussons sont donc
servis depuis un cache disque, et un ecusson encore inconnu part se telecharger
en tache de fond : la carte du moment s'affiche sans lui, celle du prochain but
l'aura. La place lui est reservee des qu'une des deux equipes en a un, pour que
le score reste centre au meme endroit d'un but a l'autre.

| Systeme | Cache |
| --- | --- |
| Windows | `%LOCALAPPDATA%\butbutbut\logos` |
| macOS | `~/Library/Application Support/butbutbut/logos` |
| Linux | `~/.local/share/butbutbut/logos` |

Un ecusson qui n'existe pas, un PNG corrompu, un dossier en lecture seule : la
carte s'affiche sans image, et c'est tout. Le dossier peut etre efface a tout
moment, il se remplira de nouveau.

**La couleur du club**, pour l'equipe qui marque et son chiffre. Attention, ces
couleurs sont choisies pour un fond blanc, et le fond de la carte est presque
noir : le bleu marine de Troyes (`0000bf`) y est illisible, et le noir du Paris
FC (`000000`) n'existe carrement plus. butbutbut mesure donc le **contraste**
(luminance relative WCAG) et descend trois etages tant qu'il ne lit rien :

| Etage | Exemple |
| --- | --- |
| la couleur du club, si elle se detache | Bayern `dc052d`, Arsenal `e20520` -> gardee |
| sa couleur secondaire, sinon | Chelsea `144992` -> blanc, Barcelone `990000` -> `fce38a` |
| celle de la competition, en dernier | Paris FC `000000` / `000000` -> le jaune de la Ligue 1 |

Le filet vertical, lui, ne bouge jamais : il dit toujours dans quelle
competition on est. `butbutbut --test 5` promene la couleur sur les trois
etages, avec cinq vraies equipes.

```bash
butbutbut --no-logos          # pas d'ecusson, rien de telecharge
```

Les couleurs des clubs restent avec `--no-logos` : elles arrivent avec les
scores, elles ne coutent aucune requete.

### Le son

Le mp3 fourni est joue a chaque but. Pour le remplacer, depose un fichier dans
le dossier `sound` (`butbutbut --paths` donne le chemin) :

| Systeme | Dossier |
| --- | --- |
| Windows | `%LOCALAPPDATA%\butbutbut\sound` |
| macOS | `~/Library/Application Support/butbutbut/sound` |
| Linux | `~/.local/share/butbutbut/sound` |

Formats : wav, mp3, ogg, opus, flac, m4a, aac. Plusieurs fichiers ? Le tirage
est au hasard a chaque but. Pas besoin de redemarrer le daemon : le dossier est
relu a chaque fois.

```bash
butbutbut --no-sound          # muet
butbutbut --no-overlay        # juste le son et le journal, pas de carte
butbutbut --no-logos          # pas d'ecusson sur les cartes
butbutbut --duration 8        # garder la carte 8 s (defaut : la duree du son)
```

### Les temps forts du match

En plus des buts, une carte signale le **coup d'envoi**, la **mi-temps**, la
**reprise** et la **fin du match**. Elles sont volontairement plus sobres : le
titre est gris au lieu de la couleur du championnat, aucune equipe n'est mise
en avant, et surtout **elles ne font aucun bruit**. Seul un but declenche le
son.

```bash
butbutbut --no-phase-cards    # seulement les buts a l'ecran
```

Le journal, lui, garde la trace de ces moments meme avec cette option.

La carte de **fin de match** va un peu plus loin : elle liste les buteurs de
chaque camp sous le score, parce qu'un `1 - 2` tout seul ne dit pas qui a
marque, et que c'est justement la question quand on n'a pas vu le match.

```
FIN DU MATCH   LIGUE 1                                        90'+4'
Angers              1 - 2              Stade Rennais
Angers : M. Lopez 12'
Stade Rennais : A. Kalimuendo 58', L. Blas 77'
```

Un camp qui n'a pas marque n'a pas de ligne, un csc est note `(csc)` et un
penalty `(sp)`. La carte gagne une ligne par camp buteur, mais jamais un pixel
de plus que sa largeur maximale : une liste trop longue est coupee par des
points de suspension plutot que de deborder.

Sur Windows et macOS la lecture est integree (MCI, `afplay`). Sous Linux il faut
un lecteur : `mpv` ou `ffmpeg` pour le mp3 ; avec seulement `aplay`/`paplay`,
butbutbut retombe sur une **corne de stade synthetisee** en wav, generee par le
programme lui-meme.

### Le fichier de configuration

Pour ne pas retaper les memes options a chaque fois - ni relancer l'installeur
pour changer de championnat - butbutbut lit un fichier au demarrage :

```bash
butbutbut --write-config      # ecrit un exemple commente (n'ecrase jamais rien)
butbutbut --paths             # ou il se trouve : ligne "config"
```

| Systeme | Fichier |
| --- | --- |
| Windows | `%LOCALAPPDATA%\butbutbut\butbutbut.conf` |
| macOS | `~/Library/Application Support/butbutbut/butbutbut.conf` |
| Linux | `~/.local/share/butbutbut/butbutbut.conf` |

Une seule section, `[butbutbut]`, et des cles nommees comme les options
longues sans les tirets. Tout est facultatif :

```ini
[butbutbut]
# Ce qu'on suit
leagues = l1,ucl,cdf
exclude = seriea
teams = om,psg
exclude_teams = psg

# Ou et comment ca s'affiche
position = top-right
screen = 1
duration = 8
scale = 1.2
opacity = 0.95

# Cadence des releves, en secondes
interval = 25
idle_interval = 300

# Son et discretion (oui/non, true/false, 1/0)
volume = 0.55
no_sound = non
no_overlay = non
no_phase_cards = non
quiet = non
```

**La ligne de commande garde toujours la priorite** : `ligne de commande >
fichier > defauts`. Avec le fichier ci-dessus, `butbutbut --leagues pl` suit la
Premier League pour cette fois-la, sans rien changer au fichier.

```bash
butbutbut --config ~/perso/but.conf     # lire un autre fichier
butbutbut --config ~/perso/but.conf --write-config
```

Le fichier n'est **lu qu'au demarrage** : apres une modification, relance le
daemon (`butbutbut --stop`, puis `butbutbut`). `butbutbut --status` rappelle
quel fichier est utilise, et s'il existe.

Rien de tout cela n'empeche jamais butbutbut de demarrer : un fichier absent
est le cas normal et silencieux, et un fichier illisible, mal forme, ou
porteur d'une cle inconnue ou d'une valeur impossible (`interval = beaucoup`,
`position = milieu`) est signale sur la sortie d'erreur - la cle fautive est
ignoree, le reste s'applique.

### Les cartons rouges

```bash
butbutbut --red-cards
```

A la demande, une expulsion a droit a sa carte. Elle se **detecte** comme un
but - la source la publie dans le meme tableau d'actions, avec une cle stable,
donc elle ne sort qu'une fois et une expulsion deja affichee au demarrage du
daemon n'est jamais rejouee - mais elle **s'affiche** comme un temps fort :
titre gris, aucune equipe en couleur (ce serait lui donner l'air d'une bonne
nouvelle), et **aucun son**.

```
CARTON ROUGE   LIGUE 1                                           62'
Angers              1 - 2              Stade Rennais
Stade Rennais : J. Lefort
```

Elle ne depend pas de `--no-phase-cards` : couper les temps forts du match ne
doit pas couper ce qu'on a explicitement demande. C'est `--red-cards` qui
l'allume, et rien d'autre qui l'eteint.

### L'annonce d'avant match

```bash
butbutbut --before-kickoff 5     # 5 minutes avant, une fois (0 = desactive)
```

Une carte discrete quelques minutes avant le coup d'envoi, avec le compte a
rebours, et sans son. **Une seule par match** : la fenetre reste ouverte
plusieurs releves d'affilee, la carte ne revient pas a chacun d'eux. Un match en
retard (l'heure est passee, rien n'a commence) ne declenche rien : annoncer un
match qui aurait deja du debuter serait faux.

```
LE MATCH VA COMMENCER   LIGUE 1
Angers              0 - 0              Stade Rennais
Coup d'envoi dans 5 min
```

Comme le carton rouge, cette carte a son propre interrupteur et ne depend pas de
`--no-phase-cards`. Reglee plus tot qu'un quart d'heure, elle accelere aussi la
cadence des releves pour que l'heure demandee soit tenue.

Le **filtre par equipe** s'applique a ces trois cartes comme aux buts : avec
`--teams om`, seules les expulsions, annonces et fins de match de l'OM
remontent.

### La langue

Les cartes **et la ligne de commande** parlent la langue de la machine, parmi
les cinq des cinq grands championnats - francais, anglais, espagnol, italien,
allemand - et le francais quand ce n'est aucune des cinq.

```bash
butbutbut --lang de       # force l'allemand
butbutbut --lang de --help   # l'aide aussi
butbutbut --status        # la ligne "langue" dit ce qui a ete retenu
```

```
TOR!   BUNDESLIGA                                              89'
Eintracht Frankfurt      1 - 4      FC Augsburg
Tor von F. Rieder
```

Le nom des competitions suit : la Ligue des champions devient CHAMPIONS LEAGUE,
la Coupe du monde WELTMEISTERSCHAFT. Celles dont le nom est un nom propre n'y
touchent pas - la Bundesliga, la Serie A ou la Coupe de France s'ecrivent
pareil partout.

L'aide, `--status`, `--scores`, `--screens`, `--list` et `--today` suivent, y
compris les valeurs qu'ils affichent - `il y a 12 s` devient `vor 12 s`, pas
seulement l'etiquette devant.

**Ce qui reste en francais** : le journal, et **par choix**. `--today` le
relit, et un fichier ecrit avant un changement de langue resterait sinon a
moitie illisible pour le relecteur. Une carte peut donc afficher `TOR!` pendant
que le journal note `BUT`.

Une phrase qu'un catalogue ne porte pas retombe sur le francais plutot que de
disparaitre : une traduction incomplete laisse le programme utilisable.

L'ordre de decision, du plus fort au plus faible :

| | |
| --- | --- |
| 1 | `--lang de`, ou la cle `lang` du fichier de configuration |
| 2 | la variable d'environnement `BUTBUTBUT_LANG` |
| 3 | la langue du systeme |
| 4 | le francais |

Sous Windows, l'API systeme passe avant les variables `LANG` et compagnie :
un shell comme Git Bash pose `LANG=en_US` quoi qu'il arrive, ce qui rendrait la
detection aveugle a la langue reelle de la machine. Et Windows sait repondre
deux langues differentes - celle de son interface et celle des reglages
regionaux. C'est la premiere qui est retenue, suivant la convention de
Microsoft pour les textes d'interface ; si ta machine affiche des menus
anglais alors que tu la veux en francais, `lang = fr` dans le fichier de
configuration tranche.

---

## D'ou viennent les scores

**Une seule source, la meme pour toutes les competitions** : le tableau de bord
public d'ESPN, un endpoint par competition.

```
https://site.api.espn.com/apis/site/v2/sports/<sport>/<code>/scoreboard
```

| Championnat | Code |
| --- | --- |
| Ligue 1 | `soccer/fra.1` |
| Premier League | `soccer/eng.1` |
| LaLiga | `soccer/esp.1` |
| Serie A | `soccer/ita.1` |
| Bundesliga | `soccer/ger.1` |

C'est aussi ce qui rend le catalogue extensible : Ligue 2 c'est `fra.2`, la
Ligue des champions `uefa.champions`, la Coupe de France
`fra.coupe_de_france`... meme format de reponse, meme code de lecture.

Le **premier segment est le sport**, et c'est la seule chose qui change hors du
football : `hockey/nhl`, `rugby/180659`. Le rugby se code par un numero et non
par un mot ; ils ont tous ete verifies un par un contre la source. Voir
[Les sports](#les-sports) pour ce que chacun publie vraiment.

Pourquoi cette source : pas de cle d'API, pas d'inscription, pas de quota a
surveiller, elle est mise a jour en direct, et elle donne le **buteur**, la
**minute**, les **csc**, les **penaltys**, l'**ecusson** de chaque club et ses
**couleurs**. C'est une API publique mais non documentee : tout est lu de facon
defensive, une cle qui disparait ne tue pas le daemon.

### Comment un but est detecte

A chaque releve, le score de chaque match est compare a celui du releve
precedent. **Un score qui monte, c'est un but.** La liste des actions d'ESPN ne
sert qu'a habiller la carte (buteur, minute, csc, penalty) : elle arrive parfois
quelques secondes apres le score, et le but ne doit pas attendre le nom du
buteur.

C'est exactement pour cette raison que les autres sports n'ont rien coute a la
detection : un score qui monte est un score qui monte, qu'il gagne 1 au
football et au hockey ou 5 au rugby. Le hockey, qui ne publie aucune action,
est donc suivi aussi bien que le reste - il a simplement des cartes sans nom de
buteur.

Deux garde-fous :

- **le premier releve ne declenche rien.** Il photographie l'existant. Sinon,
  lancer le daemon un dimanche a 17 h rejouerait tous les buts deja marques ;
- **un score qui descend** (but refuse par la VAR) affiche une carte orange
  `BUT ANNULE`, sans son.

### Sortie de veille

Si la machine dort, hiberne, ou si le processus est gele pendant une mi-temps,
le tableau de bord a pris des heures d'avance sur la derniere photo : le
comparer telle quelle sortirait une carte `BUT` avec un delta de 3 et une
minute perimee, voire un `COUP D'ENVOI` pour un match deja termine.

Avant chaque releve, le daemon confronte le temps d'horloge reellement ecoule a
celui qu'il avait prevu d'attendre. Au-dela de **deux minutes de retard** (de
quoi laisser passer sans broncher une machine chargee ou un releve traine par
le timeout HTTP de 8 s), il considere qu'il a saute dans le temps :
il **rephotographie tous les scores en silence**, exactement comme au premier
releve, et le note dans le journal :

```
2026-09-06 21:14:07  trou de 47 min dans le temps (veille, hibernation ou processus gele) - on rephotographie les scores sans rien annoncer
```

La surveillance reprend ensuite normalement, et le but suivant est annonce
comme d'habitude. Les buts tombes pendant la veille, eux, sont perdus : c'est
le prix a payer pour ne pas raconter n'importe quoi.

La mesure porte sur l'horloge murale et non sur `time.monotonic()` : sous
Linux, monotonic est gelee pendant la veille et ne verrait donc aucun trou,
alors que sous Windows elle continue d'avancer.

### Cadence

Chaque championnat a son propre rythme, pour ne pas marteler la source :

| Situation | Releve |
| --- | --- |
| un match en cours | toutes les 25 s (`--interval`) |
| coup d'envoi dans moins de 20 min | toutes les 60 s |
| rien au programme | toutes les 5 min (`--idle-interval`) |

Un mardi soir sans Bundesliga, la Bundesliga est interrogee toutes les cinq
minutes. En cas de coupure reseau, l'attente double a chaque echec (plafond
5 min) et la reprise est notee dans le journal.

---

## Ce qui se passe a l'ecran

- **fenetre sans bordure, toujours au-dessus**, qui ne vole jamais le focus ;
- **ecussons** lus depuis le cache disque, jamais depuis le reseau : chaque
  carte garde une reference sur ses images, sinon tkinter les oublie et elles
  disparaissent de l'ecran ;
- **Windows** : fond reellement transparent (coins arrondis) et fenetre
  *click-through* : les clics passent au travers, tu peux continuer a jouer ;
- **macOS** : fenetre sans bordure, absente du Dock ;
- **Linux** : fenetre de type *splash*, posee au-dessus ;
- **multi-ecrans** : les ecrans sont enumeres via l'API systeme
  (`EnumDisplayMonitors`, `xrandr --listmonitors`, CoreGraphics), pas via
  tkinter, pour qu'une carte ne se retrouve jamais a cheval sur deux dalles.

L'affichage vit dans le fil principal (tkinter y tient), la surveillance reseau
dans un fil a part : une requete lente ne fige jamais une carte a l'ecran.

### Quand une appli est en plein ecran

Une carte est une fenetre *toujours au-dessus*, mais un jeu ou un lecteur video
en **plein ecran** lui passe devant : le but tombe alors dans le vide. Avant
chaque carte, butbutbut regarde donc si la fenetre au premier plan couvre toute
la dalle visee (`GetForegroundWindow` + `GetWindowRect` compares au `rcMonitor`
du moniteur - la dalle entiere, pas la zone de travail - et absence de
`WS_CAPTION` / `WS_THICKFRAME`, qui distingue un plein ecran d'une fenetre
simplement maximisee). La carte part quand meme, la detection pouvant se
tromper, mais le journal garde la trace du but probablement manque :

```
2026-09-06 21:07:02  BUT [Ligue 1] Marseille 2 - 1 Paris FC pour Marseille - But de M. Greenwood (67')
2026-09-06 21:07:02  une application en plein ecran occupe \\.\DISPLAY1 : la carte y est probablement invisible
```

Le son, lui, part comme d'habitude.

```bash
butbutbut --retry-fullscreen        # repasser la carte plus tard (120 s au plus)
butbutbut --retry-fullscreen 300    # ... pendant 5 minutes
```

Avec cette option, la carte masquee reste en file d'attente et **repasse des que
l'ecran se libere** (jeu quitte, sortie du plein ecran) ; si l'ecran est toujours
pris au bout du delai, elle est abandonnee, la aussi avec une ligne de journal.

Une notification systeme Windows a ete ecartee : Windows retient justement les
toasts pendant qu'une application est en plein ecran, la promesse aurait donc
ete tenue exactement quand elle ne servait a rien.

> **Windows uniquement.** X11, Wayland et macOS ne repondent pas de facon fiable
> et portable a la question "une fenetre plein ecran occupe-t-elle cet ecran ?".
> Plutot qu'une heuristique qui se trompe, butbutbut n'y detecte rien : les
> cartes s'affichent comme avant, sans ligne de journal supplementaire, et
> `--retry-fullscreen` y est refuse avec un avertissement.

---

## Savoir si la surveillance tourne vraiment

Un daemon vivant mais bloque ressemble a un daemon qui marche : le fichier pid
dit qu'un processus existe, jamais qu'il travaille. Le daemon ecrit donc, a
**chaque releve**, un petit fichier d'etat a cote du fichier pid
(`butbutbut.json`, voir `butbutbut --paths`) : horodatage du releve, matchs en
cours et leurs scores, compteur de buts du jour, competitions suivies, pid.

`butbutbut --status` le relit :

```
butbutbut 1.2.0
  daemon      : actif (pid 3752)
  releve      : il y a 12 s  (2026-09-06 18:52:44)
  en cours    : 2 match(s) sur 15 au programme
                [Premier League] Arsenal 2 - 1 Chelsea  50'
                [Ligue 1] Angers 1 - 0 Stade Rennais  61'
  buts du jour: 3  (le detail : butbutbut --today)
  ...
```

Si plus rien n'est arrive depuis longtemps, `--status` le dit au lieu de faire
semblant :

```
  releve      : il y a 20 min  (2026-09-06 18:32:44)
                (!) plus rien depuis, alors que la cadence est de 25s : daemon bloque ou source injoignable ?
  en cours    : inconnu (le dernier releve est trop vieux)
```

Le seuil suit la cadence annoncee : quelques minutes quand un match est en
cours, plus large au repos. Le fichier est ecrit d'un bloc (temporaire puis
`os.replace()`), donc `--status` ne lit jamais un JSON coupe en deux ; et si le
disque est plein ou le dossier en lecture seule, l'ecriture est abandonnee en
silence : perdre l'etat n'a jamais tue un daemon en plein match. Le fichier
disparait a l'arret du daemon.

---

## Le recapitulatif du jour

```bash
butbutbut --today
```

```
butbutbut : buts signales le 06/09/2026

Premier League
    18:43:27  Arsenal 2 - 1 Chelsea              But de M. Odegaard (50')

Ligue 1
    18:51:10  Angers 1 - 0 Stade Rennais         Penalty de C. Arcus (61')
  - 18:52:44  Angers 0 - 0 Stade Rennais         Score corrige (62')

Bundesliga
    19:02:00  Bayer 04 Leverkusen 1 - 1 Bayern   But de P. Schick (77')

3 but(s) dans 3 competition(s).
'-' = but retire par la VAR (1).
```

Les buts sont relus **dans le journal**, pas dans le fichier d'etat : le
journal survit a un redemarrage, a un plantage et a l'arret du daemon, donc
`--today` repond encore le lendemain matin, machine eteinte entre-temps. Ce que
le journal ne sait pas lire est ignore sans bruit.

---

## Journal

```
2026-09-06 18:41:21  demarrage (pid 3752) - les 5 championnats - releve toutes les 25s en direct, 300s au repos
2026-09-06 18:41:21  15 match(s) au programme, 6 en cours, 3 a venir
2026-09-06 18:43:27  BUT [Premier League] Arsenal 2 - 1 Chelsea pour Arsenal - But de M. Odegaard (50')
2026-09-06 18:51:04  CARTON ROUGE [Premier League] Arsenal 2 - 1 Chelsea pour Chelsea - Chelsea : M. Caicedo (58')
2026-09-06 19:24:10  FIN DU MATCH [Premier League] Arsenal 2 - 1 Chelsea - Arsenal : B. Saka 12', M. Odegaard 50' ; Chelsea : C. Palmer 74' (FT)
```

Chemin : `butbutbut --paths`. Le daemon y ecrit aussi les coups d'envoi, les
mi-temps, les fins de match, les expulsions et les annonces d'avant match -
meme celles dont la carte est passee inapercue a l'ecran. C'est cette trace que
`butbutbut --today` relit.

---

## Prerequis

- **Python 3.8+**
- **tkinter** (paquet systeme sous Linux : `tk`, `python3-tk`,
  `python3-tkinter` selon la distribution ; `brew install python-tk` sous macOS)
- **un lecteur audio** sous Linux uniquement (`mpv`, `ffmpeg`, `sox`, `vlc`,
  ou pipewire/pulse/alsa pour le repli wav)
- une connexion internet

`butbutbut --status` verifie tout ca d'un coup, connexion a la source comprise.

---

## Mettre a jour

Une fois installe, butbutbut se met a jour tout seul, sur les trois systemes :

```bash
butbutbut --check-update    # dit si une version plus recente existe
butbutbut --update          # recupere, reinstalle, relance le daemon
```

`--update` relit la fiche deposee par l'installeur (`install.json`, dans le
dossier de donnees) pour retrouver **avec quelles options il avait ete
installe**, puis rejoue l'installeur avec les memes reglages. Une mise a jour
ne te ramenera pas aux cinq grands championnats si tu suivais `l1,pl,ucl`. Le
daemon est arrete le temps de l'operation et redemarre derriere, sur la meme
selection. S'il echoue en route, le daemon repart quand meme, sur l'ancien
code.

C'est la **derniere release** qui est installee, telechargee depuis GitHub et
depliee dans un dossier temporaire. Ton depot clone, si tu en as garde un,
n'est pas touche : l'amener sur l'etiquette voudrait dire le laisser en HEAD
detachee, et il t'appartient.

### La pointe, avec `--dev`

```bash
butbutbut --check-update --dev    # ou en est la branche principale ?
butbutbut --update --dev          # y aller
```

La, le depot clone sert s'il est encore la (`git pull --ff-only`), et l'archive
de `main` prend le relais sinon. Cette seconde voie ne demande ni git ni le
clone d'origine, donc une installation dont tu as efface le dossier depuis se
met a jour quand meme.

Les deux commandes visent la meme chose dans chaque mode : des versions par
defaut, des commits avec `--dev`. `--check-update` ne peut donc pas t'annoncer
une release et `--update` t'en installer une autre.

### Le fichier de configuration reste maitre

L'installeur ne pose dans le service de demarrage que les options que **tu**
lui as passees. `./install.sh --leagues l1,pl,ucl` pose `--leagues`, et rien
d'autre. Les valeurs par defaut ne sont pas materialisees en arguments, sans
quoi elles ecraseraient la meme cle de `butbutbut.conf`, la ligne de commande
l'emportant toujours sur le fichier.

Autrement dit : `./install.sh` tout court laisse le fichier de configuration
maitre de tout, et `--update` respecte ce choix puisqu'il rejoue les memes
options. La seule exception est `--quiet`, toujours pose, un daemon de session
ecrivant sur une sortie qui n'existe pas.

Tes sons, ton fichier de configuration et ton journal ne sont pas touches :
ils vivent dans le dossier de donnees, l'installeur ne remplace que le code.

Si butbutbut ne vient pas des scripts d'installation, `--update` refuse et te
renvoie vers l'outil qui le gere plutot que d'ecraser des fichiers qui ne lui
appartiennent pas :

| Installe par | Mise a jour |
| --- | --- |
| `install.sh` / `install.ps1` | `butbutbut --update` |
| `pipx install butbutbut` | `pipx upgrade butbutbut` |
| `pip install --user butbutbut` | `pip install --upgrade butbutbut` |
| le `PKGBUILD` d'Arch, un paquet de la distribution | `pacman -Syu`, `apt upgrade`... |

---

## Desinstallation

```bash
./uninstall.sh              # ou --purge pour effacer aussi tes sons perso
```

```powershell
powershell -ExecutionPolicy Bypass -File .\uninstall.ps1    # ou -Purge
```

---

## Tests

```bash
PYTHONPATH=".:tests" python -m unittest discover -s tests
```

**573 tests**, sans reseau ni ecran : la source est simulee par un `opener`, le
cache d'ecussons par un `fetcher`, l'horloge par un `FakeClock`, et la geometrie
des cartes (empilement, debordement, troncature, place des ecussons) est
verifiee avec une police factice, donc sans tkinter. Le choix de couleur, lui,
est une fonction pure : son invariant est teste sur toutes les paires d'un jeu
de couleurs reelles - ce qui sort est toujours lisible, ou c'est la couleur de
la competition.

---

## Versions

Les evolutions sont consignees dans
[CHANGELOG.md](https://github.com/boubou666/butbutbut/blob/main/CHANGELOG.md),
au format [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/). Chaque
version porte un tag `vX.Y.Z` et une
[release](https://github.com/boubou666/butbutbut/releases) construite
automatiquement, avec le paquet en piece jointe.

### Publication sur PyPI

La publication est le second job de
[`pypi.yml`](https://github.com/boubou666/butbutbut/blob/main/.github/workflows/pypi.yml) :
il part avec le tag, juste apres la release, et envoie sur PyPI **exactement**
le wheel et le sdist attaches a celle-ci. En **Trusted Publishing** : PyPI fait
confiance au workflow lui-meme via un jeton OIDC, il n'y a donc **aucun jeton
d'API a stocker** dans le depot.

Le workflow est **inerte par defaut**. Tant que les etapes ci-dessous ne sont
pas faites, le job est saute : pousser un tag continue de produire la release
GitHub comme avant, sans echec rouge. Seul le proprietaire du depot peut faire
ces etapes, et une seule fois :

1. **Avoir un compte sur [pypi.org](https://pypi.org/)**, avec la double
   authentification activee (elle est obligatoire pour publier).

2. **Declarer le publisher de confiance.** Le projet `butbutbut` n'existe pas
   encore sur PyPI : il faut donc passer par un *pending publisher*. Dans le
   menu du compte, `Publishing`, puis `Add a new pending publisher`, onglet
   `GitHub`. Remplir exactement :

   | Champ | Valeur |
   | --- | --- |
   | PyPI Project Name | `butbutbut` |
   | Owner | `boubou666` |
   | Repository name | `butbutbut` |
   | Workflow name | `pypi.yml` |
   | Environment name | `pypi` |

   Attention : un *pending publisher* ne reserve pas le nom, il ne fait
   qu'autoriser le workflow a le creer. Mieux vaut ne pas trop laisser trainer
   entre cette etape et la premiere publication.

3. **Creer l'environnement GitHub.** Depot, `Settings`, `Environments`,
   `New environment`, nomme **`pypi`** - le meme mot qu'a l'etape 2. C'est
   aussi l'endroit ou ajouter, si on veut, une approbation manuelle avant
   chaque envoi sur PyPI.

4. **Armer la publication.** Depot, `Settings`, `Secrets and variables`,
   `Actions`, onglet `Variables`, `New repository variable` : nom
   **`PYPI_PUBLISH`**, valeur **`true`**. C'est l'interrupteur ; sans lui le
   job reste saute.

5. **Pousser un tag**, comme d'habitude :

   ```bash
   git tag -a v1.2.1 -m "1.2.1" && git push --tags
   ```

   `pypi.yml` verifie le tag, construit le paquet, cree la release, puis son
   second job envoie ce meme paquet sur PyPI. Le *pending publisher* devient
   alors un publisher normal, et le projet existe.

Pour rattraper un envoi sans creer de nouveau tag : onglet `Actions`, workflow
**release et publication**, `Run workflow`, en donnant le tag voulu. C'est la
porte de sortie quand la publication a ete sautee - variable pas encore armee
au moment du tag, panne de PyPI, jeton refuse. Meme fichier, donc meme
publisher : rien de plus a declarer chez PyPI.

> **Pourquoi un seul workflow, et pourquoi ce nom.** La publication a d'abord
> vecu dans un fichier separe ecoutant `release: published`. Ca ne pouvait pas
> marcher : Actions refuse qu'un evenement produit par le `GITHUB_TOKEN`
> declenche un autre workflow, pour eviter les boucles - une release creee par
> `github-actions[bot]` ne reveille personne. Constate en poussant `v1.3.0`, ou
> ce declencheur n'a pas produit un seul run. Le push du tag, lui, vient d'un
> humain. D'ou un seul fichier a deux jobs. Et il s'appelle `pypi.yml` parce
> qu'un publisher de confiance autorise **un** nom de fichier : c'est celui qui
> est declare a l'etape 2, et le job qui echange le jeton OIDC doit y vivre.

## Licence

MIT.
