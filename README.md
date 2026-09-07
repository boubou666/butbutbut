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
butbutbut --record m.jsonl    # surveille, et met les releves bruts en boite
butbutbut --replay m.jsonl    # rejoue un enregistrement, cartes et sons compris
butbutbut --stop              # arrete le daemon
butbutbut --check-update      # une version plus recente existe-t-elle ?
butbutbut --update            # recupere, reinstalle, relance le daemon
butbutbut --update --dev      # idem, mais la pointe de la branche principale
butbutbut --test-hook         # essaie la commande de --on-goal
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
aux cartes de deroulement, et aussi a `--scores`. Ces deux options **font
disparaitre** un match ; pour le suivre sans se le faire raconter, voir [le mode
sans spoiler](#le-mode-sans-spoiler) juste en dessous.

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

### Le mode sans spoiler

Il y a un moment ou butbutbut se retourne contre toi : tu regardes le match en
differe - streaming, replay, quatre-vingt-dix secondes de retard sur le direct -
et la carte t'annonce le but avant que tu ne le voies. Ce match-la, il faut
pouvoir lui dire de se taire.

```bash
butbutbut --spoiler-free om                  # je regarde l'OM en differe
butbutbut --teams om,psg --spoiler-free om   # l'alerte pour le PSG, pas pour l'OM
```

Pour un match concerne, **rien n'arrive a l'ecran ni au haut-parleur** : ni but,
ni but annule, ni temps fort, ni carton rouge, ni annonce d'avant match. Un
« COUP D'ENVOI » dirait que le direct est parti, un « FIN DU MATCH » que tout
est joue : ca spoile autant qu'un but, donc **tous** les evenements se taisent,
sans exception.

**Le journal, lui, garde tout.** C'est le coeur du reglage : on ne coupe que
l'ecran et le son. Une fois le match vu, `butbutbut --today` le raconte comme
n'importe quel autre soir :

```
butbutbut : buts signales le 06/09/2026

Ligue 1
    18:51:10  Marseille 1 - 0 Paris FC        But de A. Kalimuendo (61')
    19:14:02  Marseille 1 - 1 Paris FC        But de M. Kebbal (77')
```

Les noms se tapent avec la meme souplesse que `--teams` (`om`, `barca`, `manu`,
les noms sans accents, les debuts de mots), et un mot qui ne designe aucune
equipe est refuse au demarrage. Une faute de frappe est meme plus sournoise ici
qu'ailleurs : elle ne rend pas le daemon muet, elle le laisse spoiler le match
qu'on voulait proteger. `butbutbut --list-teams --spoiler-free om` marque d'un
`?` ce que le mot attrape.

**`--scores` masque le score** plutot que de cacher le match :

```
Ligue 1
  ?              Marseille ? - ? Paris FC               sans spoiler
  >                   Lens 2 - 0 Lille                  35'

2 match(s), '>' = en cours.
'?' = sans spoiler : 1 match(s) masque(s). Le journal, lui, a tout : butbutbut --today.
```

Faire disparaitre la ligne aurait ete pire que de tout montrer : on ne saurait
plus si le match a lieu, ni a quelle heure, et c'est justement le jour ou on le
regarde qu'on ouvre `--scores`. Rien de ce qui permettrait de reconstituer le
score ne s'affiche donc - ni les buteurs, ni l'etat du match : un match termine
ressemble a un match en cours, sinon un simple « termine » a la 80e minute
suffirait a dire que c'est plie. `butbutbut --status` masque de la meme facon
le score des matchs en cours, et rappelle le reglage :

```
  equipes     : equipes suivies : om, psg
  sans spoiler: om  (journal seulement : ni carte, ni son)
```

**Avec `--teams` et `--exclude-teams`**, les trois listes cohabitent, et l'ordre
de decision est toujours le meme :

| Ordre | Reglage | Ce qu'il fait d'un match concerne |
| --- | --- | --- |
| 1 | `--exclude-teams` | le match n'existe pas : ni carte, ni son, ni journal |
| 2 | `--teams` | hors de la liste, le match n'existe pas non plus |
| 3 | `--spoiler-free` | le match reste et remplit le journal ; l'ecran et le son se taisent |

Les deux premieres taisent un match, la troisieme ne tait que l'alerte. Suivre
l'OM **et** le mettre en sans-spoiler n'est donc pas une contradiction, c'est
l'usage normal : je veux le journal, pas l'alerte.

Le reglage a sa cle de configuration, pour ne pas le retaper le samedi suivant :

```ini
[butbutbut]
teams = om
spoiler_free = om
```

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
de cinq cartes visibles, la plus ancienne cede sa place. Une carte fait
exception, [la carte epinglee](#la-carte-epinglee) : elle tient le coin en
permanence, la pile commence apres elle, et elle ne compte pas dans les cinq.

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

#### Un son par contexte, decide par le nom du fichier

Le **nom** du fichier dit quand il joue. Rien a configurer : renommer suffit.

| Nom du fichier | Quand il joue |
| --- | --- |
| `contre.mp3` | quand une equipe **suivie** (`--teams`) **encaisse** |
| `om.mp3`, `barca.mp3`, `marseille.mp3`, `olm.mp3` | quand **cette equipe marque** |
| `fra.1.mp3`, `l1.mp3`, `ligue1.mp3`, `ucl.mp3` | seulement pour un but de **cette competition** |
| `corne.mp3`, tout le reste | le fond sonore, tire au hasard comme avant |

Les noms d'equipe sont ceux de `--teams` (surnoms, abreviations, accents en
moins) et les noms de competition ceux de `--list` (code ESPN ou alias). Le
mot pour "encaisse" s'ecrit aussi `encaisse`, `against` ou `conceded`.

**Plusieurs fichiers pour la meme chose ?** Un suffixe apres `-`, `_`, un
espace ou un point suffit : `om-1.mp3`, `om-2.mp3`, `contre 2.ogg`. Le tirage
se fait au hasard entre eux, comme avant.

**Ce qui gagne quand plusieurs fichiers pourraient jouer** : l'ordre va du plus
etroit au plus large, pour qu'une intention precise ne soit jamais recouverte
par une plus large.

| | Etage | Ce qu'il peut reclamer |
| --- | --- | --- |
| 1 | l'equipe qui marque | les buts d'un seul club |
| 2 | `contre` | tous les buts encaisses par les clubs suivis |
| 3 | la competition | toute une competition |
| 4 | le fond sonore | tout |

Un etage vide passe la main au suivant : un dossier qui n'a que `contre.mp3` et
`corne.mp3` joue `corne.mp3` le reste du temps. C'est ce qui rend un
**OM - PSG** interessant : avec ces deux fichiers et `--teams om`, un but de
l'OM sonne autrement qu'un but encaisse, sans regarder l'ecran.

```bash
butbutbut --status            # ce que butbutbut a compris de chaque fichier
```

```
  son         : 4 fichier(s), le nom dit quand ils jouent
                contre.mp3             quand une equipe suivie encaisse
                corne.mp3              tirage general
                fra.1.mp3              les buts de Ligue 1
                om.mp3                 quand cette equipe marque
```

> Une precision : pour ecarter un fichier d'equipe des *autres* matchs,
> butbutbut doit savoir que ce mot designe un club - c'est le cas des surnoms
> usuels (`om`, `ol`, `barca`, `manu`, `juve`, `bvb`...) et de tout ce qui est
> passe a `--teams`. Un autre nom (`angers.mp3`) joue bien pour Angers quand
> Angers marque, mais rejoint le fond sonore ailleurs : il n'existe pas de
> catalogue d'equipes hors ligne pour trancher. `--teams angers` suffit a lever
> l'ambiguite, et `--status` le range alors au bon etage.

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
spoiler_free = om

# La carte qui reste a l'ecran pendant le match (une seule equipe)
pin = om

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
catch_up = non
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

### La carte epinglee

```bash
butbutbut --pin om        # tant que l'OM joue, une carte reste a l'ecran
```

Toutes les cartes ci-dessus sont fugaces : elles arrivent sur un evenement,
elles s'en vont quelques secondes plus tard. Celle-ci fait l'inverse. Elle se
pose au coup d'envoi, **se met a jour a chaque releve** - le score et la
minute - et s'en va un moment apres le coup de sifflet final. C'est ce qui fait
passer butbutbut de l'alerte au **tableau de bord** : la carte vit sur le
second ecran pendant qu'on travaille.

```
EN DIRECT   LIGUE 1                                              61'
Marseille              2 - 1              Paris FC
```

Deux lignes, pas trois : elle ne raconte pas ce qui vient d'arriver, elle dit
ou en est le match. Aucune equipe n'y passe en couleur non plus - partout
ailleurs la couleur d'un club veut dire « c'est elle qui vient de marquer », la
reutiliser pour dire « c'est elle qui mene » serait un contresens a l'echelle
d'une soiree. Et elle **ne fait jamais de bruit** : le son reste la marque du
but. Un but de l'OM sonne comme d'habitude et pose sa propre carte, a cote.

**Ou elle vit.** Elle est **ancree au coin choisi**, et la pile des cartes
fugaces demarre juste apres elle. Deux consequences voulues : cinq buts
d'affilee ne peuvent pas la pousser dehors, puisque le plafond de cinq cartes
ne compte que les fugaces ; et elle ne peut pas masquer une carte de but,
puisque toutes les places sont calculees ensemble, la sienne d'abord. Elle perd
le coin, qui est la meilleure place - c'est le prix d'etre la en permanence :
l'oeil sait ou la chercher, un but n'a pas a attendre.

**Son cycle de vie.** Elle apparait au coup d'envoi, ou tout de suite si le
match est deja en cours au demarrage du daemon : le lancer a la mi-temps doit
donner la carte, pas faire attendre le match suivant. Elle suit le match
jusqu'au bout, puis reste **cinq minutes** apres la fin - le temps de voir le
score final en revenant de la cuisine - et disparait. Elle ne passe pas la
nuit a l'ecran. Un match qui disparait du tableau de bord (changement de
journee, reponse tronquee) est traite comme un match fini, avec le meme delai :
mieux vaut une carte qui s'attarde qu'une carte qui clignote.

**Une seule equipe, et une seule carte.** `--pin om,psg` est refuse au
demarrage : il n'y a jamais qu'une carte epinglee, et accepter la liste
reviendrait a n'en suivre silencieusement qu'une des deux. Un mot qui attrape
**plusieurs clubs** est en revanche accepte - `--pin real`, c'est Madrid, la
Sociedad et le Betis - parce que le nommage est celui de `--teams` et qu'il
serait absurde d'y refuser ce qu'on accepte ailleurs. Dans ce cas la carte suit
**le match commence en premier**, et n'en change pas tant qu'il dure : une
carte qui sauterait d'un match a l'autre a chaque releve serait illisible.
Quand il finit, elle passe au suivant s'il en reste un en cours.

Le nommage est exactement celui de `--teams` (`om`, `barca`, `manu`, les noms
sans accents, les debuts de mots), et un mot qui ne designe aucune equipe est
**refuse au demarrage**, comme pour `--teams` : un `--pin marseile` silencieux,
ce serait une carte qui n'arrive jamais sans qu'on sache pourquoi.

`--pin` n'est pas un filtre : il ajoute une carte, il n'en cache aucune. Pour
n'etre alerte que de cette equipe-la, c'est `--teams` qu'il faut, et les deux se
combinent : `butbutbut --teams om --pin om`.

```bash
butbutbut --test --pin om     # une carte epinglee de demonstration
butbutbut --status            # la ligne "epinglee" dit ce qu'elle suit
```

```
  epinglee    : om -> [Ligue 1] Marseille 1 - 0 Paris FC  34'
```

Le journal note l'arrivee et le depart de la carte, et rien entre les deux :
une ligne par releve pendant quatre-vingt-dix minutes n'apprendrait rien a
personne.
### Lancer une commande a chaque but

```bash
butbutbut --on-goal 'curl -s -X POST -d "$BUT_TEXT" https://exemple/hook'
```

Plutot que d'ecrire dans butbutbut les dix integrations que dix personnes
voudraient - guirlande connectee, webhook Discord, domotique, compteur perso -
`--on-goal` donne de quoi les ecrire soi-meme. Le programme ne sait rien de ce
qu'il lance, et c'est le but.

Le detail du but arrive dans des **variables d'environnement**, jamais recolle
dans la commande : `$BUT_TEXT` sous un shell, `%BUT_TEXT%` sous cmd.

| Variable | Exemple | |
| --- | --- | --- |
| `BUT_TEXT` | `BUT ! [Ligue 1] Marseille 2 - 1 Paris FC - But de M. Greenwood (67')` | la phrase toute faite |
| `BUT_TYPE` | `goal` | `goal`, ou `cancelled` si la VAR retire le but |
| `BUT_LEAGUE`, `BUT_LEAGUE_CODE` | `Ligue 1`, `fra.1` | la competition, et son code ESPN |
| `BUT_HOME`, `BUT_AWAY` | `Marseille`, `Paris FC` | les deux equipes |
| `BUT_HOME_SCORE`, `BUT_AWAY_SCORE`, `BUT_SCORE` | `2`, `1`, `2 - 1` | le score apres le but |
| `BUT_TEAM`, `BUT_OPPONENT`, `BUT_SIDE` | `Marseille`, `Paris FC`, `home` | qui vient de marquer |
| `BUT_SCORER`, `BUT_MINUTE` | `M. Greenwood`, `67'` | vides tant que la source ne les publie pas |
| `BUT_OWN_GOAL`, `BUT_PENALTY` | `0`, `0` | `1` ou `0` |
| `BUT_DELTA` | `1` | `-1` quand le but est retire, `2` quand un doublon est rattrape |

Ces noms sont un **contrat** : ils partent vivre dans des scripts qui ne sont
pas dans ce depot, ils ne bougeront plus. Ils sont en anglais, contrairement au
reste, parce qu'un script se partage entre les cinq langues des cartes.

**Regler la commande sans attendre un but :**

```bash
butbutbut --test-hook
```

La commande part sur un but fabrique, tout de suite, et butbutbut montre les
variables qu'elle recoit, sa sortie et son code de retour. Sans ca, mettre au
point un crochet voudrait dire attendre le prochain but avec un daemon qui,
lui, se tait quand tout va bien.

```
butbutbut : but fabrique, la commande recevra
  BUT_AWAY           Paris FC
  BUT_HOME           Marseille
  BUT_SCORER         M. Greenwood
  ...
  commande    : notify-send "But !" "$BUT_TEXT"
  resultat    : code de sortie 0
```

Quelques commandes qui marchent telles quelles :

```bash
butbutbut --on-goal 'notify-send "But !" "$BUT_TEXT"'
butbutbut --on-goal 'echo "$(date +%H:%M) $BUT_TEXT" >> ~/mes-buts.txt'
butbutbut --on-goal 'test "$BUT_TYPE" = goal && mpv ~/sons/klaxon.mp3'
```

**Ce que le crochet promet :**

- **Les donnees passent par l'environnement, jamais par la commande.** Un nom
  d'equipe n'est donc jamais recolle dans une ligne de shell : le jour ou la
  source annoncera un club nomme `; rm -rf ~`, il ne se passera rien.
- **Un but n'attend jamais la commande.** Elle part dans un fil a part et
  personne ne guette sa fin : un script lent ne retarde ni la carte, ni le
  releve suivant. Au-dela de 30 secondes, elle est tuee.
- **Elle ne peut pas faire tomber butbutbut.** Commande introuvable, code de
  sortie non nul, script qui ne rend jamais la main : une ligne de journal, et
  la vie continue. Une reussite, elle, ne dit rien - un crochet qui part a
  chaque but n'a pas a remplir le journal.

Le crochet part sur un but **et sur son retrait par la VAR** : annoncer un but
puis se taire quand il est refuse, ce serait mentir a ce qu'on alimente.
`BUT_TYPE` distingue les deux en un mot. Les temps forts du match, les
expulsions et les annonces d'avant match, eux, ne declenchent rien : l'option
promet un but.

Le filtre par equipe s'applique comme au reste : avec `--teams om`, seuls les
buts de l'OM lancent la commande. La cle `on_goal` du fichier de configuration
fait la meme chose sans retaper l'option, et `butbutbut --status` rappelle ce
qui est arme.

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
le timeout HTTP de 8 s), il considere qu'il a saute dans le temps. Deux
comportements alors, selon ce qu'on lui a demande.

#### Par defaut : le silence

Il **rephotographie tous les scores**, exactement comme au premier releve, et
le note dans le journal :

```
2026-09-06 21:14:07  trou de 47 min dans le temps (veille, hibernation ou processus gele) - on rephotographie les scores sans rien annoncer
```

La surveillance reprend ensuite normalement, et le but suivant est annonce
comme d'habitude. Les buts tombes pendant la veille, eux, sont perdus : c'est
le prix a payer pour ne pas raconter n'importe quoi.

#### Avec `--catch-up` : une carte de resume

```bash
butbutbut --catch-up
```

La photo d'avant le trou n'est plus jetee : elle est mise de cote, puis
confrontee a celle du reveil. Comme la source publie le tableau des actions de
chaque match avec des **cles stables**, on sait exactement quels buts on n'a
jamais vus - et donc quoi raconter sans rien inventer.

```
PENDANT TON ABSENCE   LIGUE 1                                     47 min
Angers              0 - 2              Stade Rennais
avant 0 - 0 : A. Kalimuendo 58', L. Blas 77'
Lens 1 - 0 Lille (avant 0 - 0) : F. Sotoca 23'
```

Ce que cette carte **ne** fait **pas** compte autant que ce qu'elle dit :

- **une seule carte**, jamais une par but. Rejouer trois cartes avec des
  minutes perimees est exactement ce que le silence evitait ;
- **aucun son.** On n'annonce pas au klaxon un but vieux d'une heure. C'est
  une carte discrete, comme la mi-temps ou le carton rouge - et comme elles,
  elle a son propre interrupteur : `--no-phase-cards` ne la coupe pas ;
- **rien a dire, pas de carte du tout.** Si personne n'a marque pendant la
  veille, l'ecran reste vide ; le journal, lui, note quand meme le rattrapage ;
- le **filtre par equipe** s'applique : avec `--teams om`, seuls les matchs de
  l'OM y figurent ;
- un match **commence et fini pendant la veille** n'y figure pas non plus : on
  n'en a rien suivi, meme regle que pour la carte de fin de match.

Le premier match concerne occupe la ligne de score, les autres prennent une
ligne chacun en dessous. Une nuit entiere de Coupe du monde ne fait pas
deborder la carte pour autant : elle est coupee en hauteur comme en largeur,
par le meme mecanisme que la liste des buteurs de la carte de fin de match. Le
journal, lui, garde tout :

```
2026-09-06 21:14:07  trou de 47 min dans le temps (veille, hibernation ou processus gele) - on rephotographie les scores, et on resume ce qu'on a manque
2026-09-06 21:14:09  rattrapage : 2 match(s) ont bouge pendant les 47 min d'absence
2026-09-06 21:14:09  PENDANT TON ABSENCE [Ligue 1] Angers 0 - 2 Stade Rennais - avant 0 - 0 : A. Kalimuendo 58', L. Blas 77' - Lens 1 - 0 Lille (avant 0 - 0) : F. Sotoca 23' (47 min)
```

`butbutbut --status` rappelle sur sa ligne « rattrapage » lequel des deux
comportements est arme, et la cle `catch_up` du fichier de configuration
l'allume sans retaper l'option.

La mesure porte sur l'horloge murale et non sur `time.monotonic()` : sous
Linux, monotonic est gelee pendant la veille et ne verrait donc aucun trou,
alors que sous Windows elle continue d'avancer. C'est aussi pourquoi le resume
attend que **toutes** les competitions suivies aient ete rephotographiees :
leurs echeances ne retombent pas au meme releve, et un resume a trous vaudrait
moins que rien.

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

## Enregistrer un match, et le rejouer

`butbutbut --test` montre des cartes fabriquees : jolies, mais figees. Le vrai
enchainement - coup d'envoi, but, expulsion, mi-temps, but retire par la VAR,
fin du match - ne tombe qu'un samedi soir. `--record` le met en boite,
`--replay` le ressort autant de fois qu'on veut.

```bash
butbutbut --record match.jsonl --leagues l1    # pendant le match
butbutbut --replay match.jsonl                 # plus tard, en temps reel
butbutbut --replay match.jsonl --speed 60      # une heure de match en une minute
```

Ca sert a trois choses a la fois :

- **mettre au point l'affichage** sans attendre le prochain multiplex : la carte
  qui deborde, l'ecusson qui manque, la couleur illisible se corrigent en
  rejouant le meme match dix fois de suite ;
- **reproduire un bug** : "chez moi la carte deborde sur ce match-la" devient un
  fichier de quelques mega-octets qu'on joint au ticket, et la personne d'en
  face voit exactement la meme chose ;
- **fabriquer les captures et les GIF** de ce README, avec de vrais noms, de
  vrais scores et un vrai enchainement.

### `--record` : se poser entre le programme et la source

`--record` ne change rien a la surveillance : le daemon tourne normalement,
affiche ses cartes, joue son son et ecrit son journal. Il ecrit **en plus**
chaque reponse brute d'ESPN sur le disque, avec son horodatage et le code de la
competition. Toutes les options habituelles s'appliquent :

```bash
butbutbut --record psg-om.jsonl --leagues l1 --teams psg,om --red-cards
```

Il y a une bonne raison de mettre `--leagues` : voir plus bas, ce que ca pese.

### `--replay` : la meme soiree, sans reseau

Le rejeu ne relit pas le fichier pour en tirer des buts. Il **remplace la
source** et laisse le reste du programme faire son travail : la comparaison des
scores, le premier releve muet, le buteur pioche dans les actions, la cadence
qui s'adapte, les cartes, le son, les lignes de journal - tout passe par les
memes chemins qu'un vrai samedi soir. C'est la seule facon qu'un rejeu prouve
quelque chose : un rejeu qui prendrait un raccourci ne testerait que lui-meme.

`--speed` divise les ecarts de temps entre deux releves. `--speed 1` (le defaut)
rejoue en temps reel, `--speed 60` fait passer une heure de match en une minute.
Les competitions rejouees sont **celles du fichier**, pas celles de `--leagues` :
un enregistrement de Ligue 1 se rejoue en Ligue 1, quoi qu'on tape.

```
2026-09-07 21:04:11  rejeu de match.jsonl - 288 releve(s) - Ligue 1 - 1 h 52 - enregistre le 2026-09-06 20:41:03 - x60
2026-09-07 21:04:11  journal, etat et pid du rejeu isoles dans /home/toi/.local/share/butbutbut/replay
2026-09-07 21:04:13  COUP D'ENVOI [Ligue 1] Angers 0 - 0 Stade Rennais (3')
2026-09-07 21:04:22  BUT [Ligue 1] Angers 1 - 0 Stade Rennais pour Angers - But de B. Saka (12')
2026-09-07 21:04:35  CARTON ROUGE [Ligue 1] Angers 1 - 0 Stade Rennais pour Stade Rennais - Stade Rennais : M. Caicedo (37')
2026-09-07 21:05:06  FIN DU MATCH [Ligue 1] Angers 1 - 0 Stade Rennais - Angers : B. Saka 12' (FT)
2026-09-07 21:05:12  rejeu termine : 288 releve(s) servi(s) sur 288, 1 h 52 parcourues.
```

Les cartons rouges et l'annonce d'avant match restent a la demande au rejeu
comme en direct : `--replay match.jsonl --red-cards` les fait ressortir meme si
l'enregistrement a ete fait sans.

### Le format du fichier

Du **JSON Lines** : une ligne = un objet JSON complet. Deux proprietes en
decoulent, et ce sont exactement celles qu'on cherchait - ca se lit a l'oeil
nu, et une session tuee en plein match laisse un fichier dont seule la derniere
ligne est a jeter.

La premiere ligne est un en-tete, les suivantes sont les releves :

```json
{"kind":"butbutbut-record","format":1,"version":"1.5.0","recorded_at":1757270481.4,"recorded_text":"2026-09-06 20:41:21","leagues":["fra.1"]}
{"at":1757270481.6,"slug":"fra.1","payload":{"events":[...]}}
{"at":1757270506.7,"slug":"fra.1","repeat":true}
```

| cle | ce que c'est |
| --- | --- |
| `format` | le numero du **format**, pas celui du programme |
| `at` | l'heure du releve : c'est l'ecart entre deux `at` que `--speed` divise |
| `slug` | le code ESPN de la competition (un fichier peut en porter plusieurs) |
| `payload` | la reponse d'ESPN, telle quelle, sans rien retirer |
| `repeat` | reponse identique a la precedente du meme championnat (voir plus bas) |

**Un fichier plus vieux reste rejouable**, c'est la raison d'etre de `format` :
un lecteur accepte tout numero inferieur ou egal au sien. Un fichier ecrit par
une version future dit clairement pourquoi il ne passe pas, plutot que de partir
de travers :

```
butbutbut : match.jsonl est enregistre au format 2, et cette version de
butbutbut ne lit que le format 1 : mets butbutbut a jour (butbutbut --update).
```

Une ligne illisible - la derniere d'une session tuee au milieu - est comptee et
ignoree, et le reste se rejoue. Une cle inconnue l'est aussi : c'est ce qui
permet d'ajouter un champ demain sans changer le numero de format.

Comme chaque ligne se suffit, un enregistrement se decoupe avec les outils du
systeme. Garder l'en-tete et les vingt releves autour du but :

```bash
(head -1 match.jsonl; sed -n '120,140p' match.jsonl) > le-but.jsonl
butbutbut --replay le-but.jsonl --speed 10
```

### Ce qu'un rejeu ne touche pas

Un rejeu **ne pollue ni `--today`, ni `--status`, ni le daemon en cours**. Le
journal, le fichier d'etat et le fichier pid sont detournes d'un bloc vers un
sous-dossier `replay/` du dossier de donnees, le temps du rejeu :

```
~/.local/share/butbutbut/replay/butbutbut.log      <- le journal du rejeu
```

Le detournement se prend a la racine, dans `paths()`, plutot que dans chaque
fonction : tout ce qui passe par la est isole, y compris le code ecrit demain.
Consequences pratiques : un match d'il y a trois semaines rejoue ce matin
n'apparait pas dans `butbutbut --today`, `--status` continue de decrire le vrai
daemon, et **on peut rejouer un match pendant que le daemon tourne** - le rejeu
ne reclame pas le fichier pid de l'instance unique.

Ce qui n'est *pas* detourne : le son et le cache d'ecussons. Ce sont des caches
partages, et les isoler obligerait chaque rejeu a retelecharger tous les
ecussons - alors qu'un rejeu est justement cense se passer de reseau. C'est
d'ailleurs le seul acces reseau qu'un rejeu peut encore declencher, quand un
ecusson manque au cache ; `--no-logos` le ferme aussi.

### Ce que ca pese

Un tableau de bord ESPN fait **60 a 200 ko de JSON** selon le nombre de matchs a
l'affiche. A 25 s par releve, deux heures de multiplex font environ 290 releves,
soit **20 a 60 Mo par competition**. Une soiree complete enregistree sur les
cinq grands championnats depasserait tranquillement les 100 Mo : `--record` sert
a garder *un* match, et `--leagues l1` n'est pas une precaution de style.

Deux choses ramenent ca a une taille raisonnable :

- **une reponse identique a la precedente n'est pas reecrite.** La ligne se
  resume a son horodatage et au marqueur `repeat` : une soixantaine d'octets au
  lieu de deux cent mille. L'heure du releve, elle, est gardee - c'est elle qui
  porte la cadence, et la perdre changerait le rythme du rejeu. Pendant un match
  en cours ca ne gagne rien (l'horloge du match bouge a chaque releve, donc la
  reponse aussi), mais un championnat au repos - l'essentiel d'une soiree - se
  resume alors a une ligne toutes les cinq minutes ;
- **gzip**, quand le nom du fichier finit par `.gz`. Compression a l'ecriture,
  decompression a la lecture, sans rien demander. Du JSON d'API se comprime
  autour de vingt fois : les 40 Mo d'un match tiennent dans 2 Mo, et le fichier
  reste lisible avec `zcat`.

```bash
butbutbut --record match.jsonl.gz --leagues l1
butbutbut --replay match.jsonl.gz --speed 60
```

A la lecture, l'enregistrement est charge en memoire d'un bloc : c'est assume,
un rejeu est un outil de mise au point, il tourne devant quelqu'un qui regarde
son ecran.

### Fabriquer une capture ou un GIF

1. **Enregistrer** un match, une seule competition, pendant qu'il se joue :

   ```bash
   butbutbut --record match.jsonl.gz --leagues l1 --red-cards
   ```

2. **Reperer le passage** interessant. Le fichier est du texte, `grep -c` compte
   les releves et `sed -n` en decoupe une tranche (voir plus haut). Un but tient
   en trois ou quatre releves.

3. **Rejouer** en gros, au centre de l'ecran, et assez vite pour que
   l'enregistreur d'ecran n'ait pas a tourner dix minutes :

   ```bash
   butbutbut --replay le-but.jsonl.gz --speed 30 --scale 1.6 \
             --position center --red-cards
   ```

4. **Capturer** avec l'outil du systeme : `Win`+`Alt`+`R` (Xbox Game Bar) ou
   [ScreenToGif](https://www.screentogif.com/) sous Windows,
   `Cmd`+`Shift`+`5` sous macOS, [Peek](https://github.com/phw/peek) ou
   `ffmpeg -f x11grab` sous Linux.

Le rejeu suit la cadence que le watcher calcule, comme en direct : un
enregistrement fait avec `--interval 25` se rejoue au meme rythme. Rejoue avec
des cadences differentes de celles de l'enregistrement, il ne saute jamais un
releve, mais il peut mettre un peu plus longtemps que le match d'origine -
`--interval` et `--idle-interval` le resserrent.

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

**784 tests**, sans reseau ni ecran : la source est simulee par un `opener`, le
cache d'ecussons par un `fetcher`, l'horloge par un `FakeClock`, et la geometrie
des cartes (empilement, debordement, troncature, place des ecussons) est
verifiee avec une police factice, donc sans tkinter. Le choix de couleur, lui,
est une fonction pure : son invariant est teste sur toutes les paires d'un jeu
de couleurs reelles - ce qui sort est toujours lisible, ou c'est la couleur de
la competition. L'enregistrement, lui, est verifie par un aller-retour complet :
un match joue en direct contre une source simulee, mis en boite, puis rejoue -
et les deux doivent rendre exactement la meme suite d'evenements.

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
