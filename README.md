![Deux supporters ahuris pointent du doigt cinq ecrans qui affichent tous un but](https://raw.githubusercontent.com/boubou666/butbutbut/main/docs/banniere.png)

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
butbutbut --leagues all                   # tout le catalogue
butbutbut --leagues big5                  # les 5 grands, explicitement
```

Le catalogue va bien au-dela des cinq grands : **36 competitions** verifiees
contre la source, dont

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

---

## D'ou viennent les scores

**Une seule source, la meme pour toutes les competitions** : le tableau de bord
public d'ESPN, un endpoint par competition.

```
https://site.api.espn.com/apis/site/v2/sports/soccer/<code>/scoreboard
```

| Championnat | Code |
| --- | --- |
| Ligue 1 | `fra.1` |
| Premier League | `eng.1` |
| LaLiga | `esp.1` |
| Serie A | `ita.1` |
| Bundesliga | `ger.1` |

C'est aussi ce qui rend le catalogue extensible : Ligue 2 c'est `fra.2`, la
Ligue des champions `uefa.champions`, la Coupe de France
`fra.coupe_de_france`... meme format de reponse, meme code de lecture.

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

Chemin : `butbutbut --paths`. Le daemon ecrit aussi les coups d'envoi, les fins
de match, les expulsions et les annonces d'avant match - meme celles dont la
carte est coupee a l'ecran.
Chemin : `butbutbut --paths`. Le daemon ecrit aussi les coups d'envoi et les
fins de match. C'est cette trace que `butbutbut --today` relit.

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

**218 tests**, sans reseau ni ecran : la source est simulee par un `opener`, et
**225 tests**, sans reseau ni ecran : la source est simulee par un `opener`, et
**222 tests**, sans reseau ni ecran : la source est simulee par un `opener`, et
la geometrie des cartes (empilement, debordement, troncature) est verifiee avec
une police factice, donc sans tkinter.
**238 tests**, sans reseau ni ecran : la source est simulee par un `opener`, le
cache d'ecussons par un `fetcher`, et la geometrie des cartes (empilement,
debordement, troncature, place des ecussons) est verifiee avec une police
factice, donc sans tkinter. Le choix de couleur, lui, est une fonction pure :
son invariant est teste sur toutes les paires d'un jeu de couleurs reelles - ce
qui sort est toujours lisible, ou c'est la couleur de la competition.

---

## Versions

Les evolutions sont consignees dans
[CHANGELOG.md](https://github.com/boubou666/butbutbut/blob/main/CHANGELOG.md),
au format [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/). Chaque
version porte un tag `vX.Y.Z` et une
[release](https://github.com/boubou666/butbutbut/releases) construite
automatiquement, avec le paquet en piece jointe.

### Publication sur PyPI

Le workflow
[`pypi.yml`](https://github.com/boubou666/butbutbut/blob/main/.github/workflows/pypi.yml)
envoie sur PyPI les paquets attaches a une release GitHub, en **Trusted
Publishing** : PyPI fait confiance au workflow lui-meme via un jeton OIDC, il
n'y a donc **aucun jeton d'API a stocker** dans le depot.

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

   `release.yml` construit le paquet et cree la release ; `pypi.yml` prend le
   relais et envoie ce meme paquet sur PyPI. Le *pending publisher* devient
   alors un publisher normal, et le projet existe.

Pour rejouer un envoi sans creer de tag : onglet `Actions`, workflow **pypi**,
`Run workflow`, en donnant le tag d'une release deja publiee.

## Licence

MIT.
