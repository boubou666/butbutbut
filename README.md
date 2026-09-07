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
butbutbut --speak             # ... et dit le but a voix haute, en plus du son
butbutbut --test              # une carte de demonstration
butbutbut --test 3            # trois cartes, pour voir l'empilement
butbutbut --scores            # les matchs du jour dans le terminal
butbutbut --next              # les prochains matchs, groupes par jour
butbutbut --table             # le classement des competitions suivies
butbutbut --table om          # ... celui de l'OM, sa ligne surlignee
butbutbut --list              # les competitions surveillables
butbutbut --list-teams        # les equipes des competitions suivies
butbutbut --status            # daemon, dernier releve, matchs en cours, son, ecrans
butbutbut --today             # les buts signales aujourd'hui
butbutbut --week              # les 7 derniers jours
butbutbut --month             # les 30 derniers jours
butbutbut --since 2026-09-01  # depuis cette date
butbutbut --top-scorers       # le classement des buteurs vus passer
butbutbut --stats             # les formes cachees dans le journal
butbutbut --export csv        # le journal en donnees, pour un tableur
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
butbutbut --leagues l1f,wsl               # le football feminin
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

### Le football feminin

butbutbut suit **14 competitions feminines**, servies par le meme endroit et
sous la meme forme que les autres : un but de Liga F se lit exactement comme
un but de LaLiga, buteur, minute, csc et penalty compris. Leur absence
jusqu'ici n'etait pas un arbitrage, c'etait un angle mort.

```bash
butbutbut --leagues l1f,wsl            # Premiere Ligue et Women's Super League
butbutbut --leagues uclf               # la Ligue des champions feminine
butbutbut --leagues feminines          # les 14 d'un coup
butbutbut --leagues l1,l1f             # les deux Ligue 1, ensemble
```

| Famille | Noms acceptes |
| --- | --- |
| Championnats | `wsl`/`plf`, `ligaf`, `l1f`/`d1f`, `eredivisief`, `nwsl` |
| Coupes d'Europe | `uclf`/`c1f`/`uwcl`, `uelf`/`europaf` |
| Selections | `cdmf`/`mondialf`, `nationsf`, `qualifsf` |
| Coupes nationales | `facupf`, `leaguecupf`, `reina` |
| Hors d'Europe | `concacaff` |

#### La regle des alias : un `f` a la fin

**Le mot masculin, plus un `f`.** `l1` donne `l1f`, `pl` donne `plf`, `liga`
donne `ligaf`, `ucl` donne `uclf`, `cdm` donne `cdmf`, `facup` donne `facupf`.
Il n'y a rien d'autre a retenir, et c'est le seul point de ce chantier qui
demandait vraiment un arbitrage.

Ce qu'il fallait eviter, c'est **un mot qui change de sens selon ce qu'on
suit**. `psg` designe deja une equipe, `l1` la Ligue 1 : le jour ou `l1`
voudrait dire « les deux Ligue 1 », plus personne ne saurait ce que fait son
propre fichier de configuration - et surtout pas six mois plus tard. Ici,
aucun mot deja pris ne bouge. `l1`, c'est la Ligue 1, hier comme demain.

Le `f` n'est pas venu de nulle part : c'est le marqueur que tout le monde
ecrit deja, des grilles de programmes (« France F ») jusqu'au nom officiel de
la premiere division espagnole, qui s'appelle **Liga F**. Une competition qui
porte un nom a elle repond en plus a ce nom-la - `wsl`, `nwsl`, `uwcl`,
`reina` -, et c'est souvent celui qu'on tape en premier.

L'etiquette de la carte suit la meme regle, et pour la meme raison. La
premiere division francaise feminine s'appelle officiellement « Premiere
Ligue » ; affichee telle quelle, a deux heures du matin, elle se lit
« Premier League ». La carte annonce donc **PREMIERE LIGUE F**.

#### Ce que `--leagues all` ne prend pas

**`all` reste le catalogue masculin**, et c'est le meme arbitrage que pour le
hockey, mot pour mot : quelqu'un qui tapait `--leagues all` hier ne doit pas
se retrouver, apres une simple mise a jour, avec des cartes de matchs qu'il
n'a jamais demandes. Une mise a jour ne change pas ce qu'on suit. Et `all`,
c'est deja 36 endpoints ; y verser le reste en ferait 60 sans que ce soit un
choix.

Elles se demandent donc, d'un seul mot :

```bash
butbutbut --leagues all              # 36 competitions, les memes qu'avant
butbutbut --leagues feminines        # les 14 feminines (ou footf, women)
butbutbut --leagues all,feminines    # les 50
butbutbut --leagues all-sports       # vraiment tout, autres sports compris
```

`all-sports` les emporte, comme il emporte le hockey et le rugby : c'est ce
qu'il promet, et personne ne le tape par distraction.

#### Ce que la source publie, et ce qu'elle ne publie pas

Le catalogue feminin est **le miroir du masculin** : y entre la competition
feminine dont l'homologue masculin est deja la. Cette regle fait tout le tri,
et elle explique les absences sans avoir a les justifier une par une - il n'y
a pas d'Euro feminin ici parce qu'il n'y a pas d'Euro tout court, et la W Gold
Cup attendra la Gold Cup. Elles existent bien chez la source, elles ont ete
verifiees, et l'echappatoire les ouvre quand meme :

```bash
butbutbut --leagues uefa.weuro            # l'Euro feminin
butbutbut --leagues fifa.w.olympics       # le tournoi olympique
butbutbut --leagues aus.w.1,can.w.nsl     # A-League Women, Northern Super League
```

Deux trous, en revanche, ne viennent pas de nous : **l'Italie et l'Allemagne
n'ont pas d'equivalent feminin chez la source**. `ita.w.1` et `ger.w.1`
repondent 400, alors que la Serie A et la Bundesliga sont au catalogue depuis
le premier jour. On ne suit pas ce qui n'est pas publie.

Et rien ici ne dira quand elles apparaitront : la suite de tests ne touche
jamais au reseau, et le test qui garde ces deux slugs garde le CATALOGUE - il
empeche qu'on les inscrive sans les avoir essayes, ce qui donnerait une
competition injoignable a chaque releve. C'est donc un geste manuel qui
repond, et il tient en une ligne :

```bash
butbutbut --scores --leagues ita.w.1
```

`--scores`, `--next` et `--table` marchent dessus comme partout ailleurs. Le
classement, lui, a une notion de colonnes par sport (voir « Les colonnes
suivent le sport ») : une competition feminine est du football, elle compte
donc les matchs nuls comme la Ligue 1 - verifie, pas suppose.

#### Une equipe feminine porte le nom de son club

La source ecrit « Paris Saint-Germain » dans `fra.w.1` comme dans `fra.1`,
« Arsenal » dans la WSL comme en Premier League. Le rapprochement des noms
travaillant sur les libelles, `--teams psg` attrape donc **les deux equipes du
club** des qu'on suit les deux competitions.

C'est la bonne reponse, et non un defaut a corriger : quelqu'un qui suit le
PSG suit le PSG. Rien dans le nom ne permettrait d'ailleurs de trancher, et
vouloir le faire demanderait une liste d'equipes feminines ecrite a la main,
qui vieillirait mal. Ce qui separe les deux cartes, c'est la competition, et
c'est l'en-tete qui l'annonce. Quand on ne veut qu'une des deux, `--leagues`
suffit deja : suivre `l1f` seul ne fait pas apparaitre les buts des hommes.

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

**`--leagues all` reste le catalogue masculin de football**, exactement ce
qu'il designait avant. Deux raisons, et la premiere suffit :

- **personne n'a demande la NHL.** Quelqu'un qui tapait `--leagues all` pour
  suivre les coupes nationales ne doit pas se retrouver, apres une simple mise
  a jour, avec des cartes de hockey a deux heures du matin. Une mise a jour ne
  change pas ce qu'on suit ;
- `all`, c'est deja 36 endpoints. Y verser le reste en ferait 60 sans que ce
  soit un choix.

C'est le meme raisonnement qui tient le football feminin hors de `all` (voir
« Le football feminin ») : la regle ne porte pas sur le sport, elle porte sur
la promesse faite au mot.

Pour vraiment tout : `--leagues all-sports` (ou `tous-sports`). Et
`--leagues foot` designe le catalogue masculin de football, comme `all`.

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
| Classement (`--table`) | oui | oui, par conference | oui, points de bonus compris |

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

### Ne pas deranger

Il y a deux moments ou une carte tombe mal, et aucun des deux ne depend du
match : **la nuit**, et **quand quelqu'un d'autre regarde ton ecran**. Une carte
« BUT » au milieu d'une visio partagee, c'est le bug qu'on ne decouvre qu'une
fois, et devant temoins.

```bash
butbutbut --quiet-hours 23:00-08:00      # rien entre 23 h et 8 h
butbutbut --quiet-while-presenting       # rien pendant une presentation
```

Pendant le silence, **rien a l'ecran et rien au haut-parleur** : ni but, ni but
annule, ni temps fort, ni carton rouge, ni annonce d'avant match. La carte
epinglee s'en va aussi - un tableau de bord allume toute la nuit est exactement
ce dont on se plaint - et elle revient d'elle-meme au premier releve qui suit.

**Le journal, lui, garde tout**, exactement comme en mode sans spoiler. C'est
tout le contrat : on ne coupe que l'alerte, jamais la trace. Le lendemain matin,
`butbutbut --today` raconte la nuit comme n'importe quel autre soir :

```
butbutbut : buts signales le 07/09/2026

MLS
    02:14:31  LA Galaxy 1 - 0 Seattle          But de R. Puig (58')
```

#### La plage horaire

`--quiet-hours 23:00-08:00` se lit sur **l'horloge de la machine**, pas en UTC :
la plage veut dire ce qu'elle veut dire pour celui qui l'ecrit, ou qu'il soit et
quel que soit le fuseau des matchs suivis. Elle peut **enjamber minuit**, ce qui
est meme le cas courant : personne ne dort de 9 h a 17 h.

Le **debut est inclus, la fin exclue** : a 23:00 pile on se tait, a 08:00 pile on
parle. Il faut trancher quelque part, et c'est ainsi qu'on lit un horaire - « de
23 h a 8 h » ne compte pas 8 h.

Les quatre formes que les gens tapent vraiment sont acceptees, et ramenees a une
seule : `23:00-08:00`, `23h00-08h00`, `23h-8h` et `23-8` disent la meme chose.
Une plage illisible, elle, est refusee tout de suite, en nommant le format
attendu :

```
$ butbutbut --quiet-hours "de 23h a 8h"
butbutbut : plage horaire illisible : 'de 23h a 8h' (attendu HH:MM-HH:MM, par exemple 23:00-08:00)
```

Une plage qui commence et finit a la meme heure (`08:00-08:00`) est refusee
aussi : elle veut dire « tout le temps » ou « jamais » selon la personne a qui on
demande, et ce n'est pas a butbutbut de choisir a sa place.

Sur la ligne de commande, c'est fatal (code 2) : celui qui tape est devant son
terminal. **Dans le fichier de configuration**, la meme faute est signalee sur la
sortie d'erreur et la cle est simplement ignoree - le daemon est souvent lance au
demarrage de la machine, sans personne pour lire l'erreur, et un daemon qui
refuse de demarrer coute plus cher qu'une plage horaire perdue.

#### Le partage d'ecran : ce qui est detecte, et ce qui ne l'est pas

`--quiet-while-presenting` pose la question au systeme plutot que de la deviner.
Sous Windows, `SHQueryUserNotificationState` est exactement l'API par laquelle
Windows repond lui-meme a « est-ce le moment d'afficher une notification ? » : on
lui pose donc la question telle quelle, et on retient deux de ses reponses.

| Situation | Detectee ? |
| --- | --- |
| Mode presentation Windows (videoprojecteur branche, parametres de presentation) | oui |
| Ecran **duplique** vers un projecteur ou une salle de reunion | oui, via l'assistant de concentration que Windows allume alors tout seul |
| « Ne pas deranger » / assistant de concentration active a la main | oui |
| Partage de **fenetre ou d'ecran** depuis Teams, Zoom ou Meet | **non** |
| macOS, X11, Wayland | **non**, rien du tout |

**Le partage depuis une application de visio n'est pas detectable, et il vaut
mieux le dire que de le laisser croire.** Windows n'expose rien qui le signale.
La seule facon d'y arriver serait de guetter le nom de classe de la barre
flottante de chaque application (`ZPToolBarParentWnd` et compagnie) : cette
heuristique-la tombe a la premiere mise a jour de Zoom, et se declenche de
travers entre-temps. Ne rien detecter et l'ecrire ici vaut mieux que detecter
parfois, au hasard.

En pratique, le geste qui marche est donc : **allumer « ne pas deranger » avant
la visio**. Windows le fait deja pour tout le reste du systeme, et butbutbut le
suit. C'est aussi ce que Windows allume tout seul quand l'ecran est duplique, le
cas de la salle de reunion et du videoprojecteur.

Hors de Windows, il n'y a rien a suivre : macOS allume un point orange quand
l'ecran est capture mais ne le dit a aucune API publique, le partage sous Wayland
passe par un portail qui ne repond qu'a celui qui a demande le partage, et X11 ne
sait meme pas qu'un partage existe. L'option y est refusee avec un avertissement,
comme `--retry-fullscreen`.

Une detection qui echoue **laisse passer la carte** - on retombe sur le
comportement d'avant l'option - et le journal le note **une fois**, pas a chaque
releve : un daemon tourne des heures, et une detection cassee qui ecrirait une
ligne toutes les 25 secondes rendrait le journal illisible le jour ou on en
aurait justement besoin.

#### Le crochet, lui, part quand meme

`--on-goal` continue de se declencher pendant le silence, contrairement au mode
sans spoiler qui le coupe. Ce n'est pas un oubli : le silence protege **cet
ecran** et **ce haut-parleur**, alors qu'une commande qui allume une guirlande,
pousse une notification sur un telephone ou ecrit dans un tableur n'a aucune
raison de se taire parce que la machine, elle, dort. Sans cela, `--quiet-hours`
reviendrait a arreter le daemon. `--spoiler-free`, lui, coupe tout, et pour une
raison differente : la, c'est le resultat qu'on ne veut pas connaitre, ou qu'il
arrive.

#### `--status` dit quand butbutbut se tait, et pourquoi

C'est la premiere chose qu'on va verifier en croyant a une panne, donc la ligne
est toujours la, meme quand rien ne fait taire :

```
  silence     : plage 23:00-08:00 - en veille jusqu'a 08:00
  silence     : plage 23:00-08:00 - rien en ce moment
  silence     : presentation ou ecran duplique - mode presentation
  silence     : aucun (voir --quiet-hours)
```

Le journal dit la meme chose, et **seulement quand ca change** :

```
2026-09-06 23:00:14  silence : en veille jusqu'a 08:00
2026-09-07 08:00:22  fin du silence : les cartes et le son repassent
```

#### Les trois fois ou butbutbut se demande « est-ce le moment ? »

Ce sont trois formes d'une meme question, et elles se cumulent - d'ou un seul
point de decision dans le code (`butbutbut/silence.py`) plutot que trois branches
eparpillees. Elles ne rendent pas le meme verdict, et c'est voulu :

| Question | Reglage | Verdict |
| --- | --- | --- |
| Quelle heure est-il ? | `--quiet-hours` | rien a l'ecran, rien au son |
| Quelqu'un regarde-t-il cet ecran ? | `--quiet-while-presenting` | rien a l'ecran, rien au son |
| La carte serait-elle seulement visible ? | `--retry-fullscreen` | la carte part **quand meme**, et peut repasser plus tard |

Le sens du doute change avec la question. Se tromper sur le plein ecran ferait
manquer un but pour rien, donc la carte passe ; se tromper a 2 h du matin ou
pendant une presentation coute bien plus cher, donc on se tait. Et un jeu en
plein ecran n'est jamais compte comme une presentation : personne d'autre ne le
regarde, et rendre butbutbut muet pendant un match joue en plein ecran reviendrait
a le couper exactement quand il sert.

**Le silence ne concerne que le daemon.** `--test` et `--replay` affichent leurs
cartes a 3 h du matin comme a midi : ce sont des commandes qu'on vient de taper,
et les taire ressemblerait a une panne.

Les deux reglages ont leur cle de configuration :

```ini
[butbutbut]
quiet_hours = 23:00-08:00
quiet_while_presenting = oui
```

### Les prochains matchs

`--scores` dit ce qui se joue aujourd'hui. `--next` repond a la question
d'apres : **c'est quand, le prochain match ?**

```bash
butbutbut --next              # les prochains matchs des competitions suivies
butbutbut --next om           # ... de cette equipe
butbutbut --next 14           # ... sur les 14 prochains jours
butbutbut --next om,psg,3     # les deux a la fois, dans n'importe quel ordre
```

```
butbutbut : prochains matchs - Ligue 1, Ligue des champions, 7 jour(s)

mardi 08/09 (demain)
  Ligue des champions
      18:45             Club Brugge - Aston Villa            dans 40 h
      21:00       Borussia Dortmund - Villarreal             dans 42 h
      21:00             Real Madrid - Internazionale         dans 42 h

vendredi 11/09
  Ligue 1
      20:45           Stade Rennais - Marseille              dans 4 j

samedi 12/09
  Ligue 1
      17:15              Strasbourg - AS Monaco              dans 5 j
      20:45                Paris FC - Lyon                   dans 5 j

6 match(s) a venir dans 2 competition(s), sur 7 jour(s).
```

Groupe **par jour puis par competition**, a l'**heure locale de la machine** :
la source ne parle qu'en UTC, ou un match du samedi 21 h a Marseille est ecrit
le dimanche a 1 h du matin. La derniere colonne dit dans combien de temps -
l'heure repond *quand*, elle repond *dans combien de temps*, et ca evite de
compter les jours sur ses doigts.

**Sept jours par defaut**, parce que c'est la maille du calendrier : un club
joue une fois par semaine, deux quand il a une coupe. Sept jours contiennent
donc toujours le prochain match de qui que ce soit, sans deverser un mois
d'affiches pour repondre a une question qui tient en une ligne. `--next 30` est
le maximum : au-dela la source elle-meme n'a plus rien a dire, les calendriers
n'etant publies qu'a quelques semaines.

La fenetre se compte en **jours entiers** et non en tranches de 24 h :
`--next 1`, c'est le reste de la journee ; `--next 7`, aujourd'hui et les six
jours suivants. Une fenetre qui se refermerait au milieu d'une soiree couperait
une affiche en deux sans que personne comprenne pourquoi.

Le nom d'equipe est celui que `--teams` accepte deja - `om`, `barca`, `manu`,
les noms sans accents, un debut de mot : c'est le meme code. Il s'ajoute a
`--teams` s'il y en a un.

Rien au programme n'affiche pas un tableau vide mais une phrase, qui redit ce
qui a ete cherche, ou, et sur combien de temps :

```
Rien au programme dans les 7 prochains jours pour om dans Ligue 1.
```

C'est aussi la que se voit une faute de frappe : `--next` ne confronte pas le
mot au catalogue des clubs comme le fait `--teams`, verification qui couterait
une requete de plus par competition sur une commande qu'on lance en passant.

**Une requete par competition**, pas une par jour : le tableau de bord accepte
un intervalle de dates, donc toute la fenetre tient dans un seul appel. Les
competitions sont interrogees les unes apres les autres, espacees comme au
demarrage du daemon - avec `--leagues all` ce sont 36 requetes, et une rafale
finit par se faire jeter. **Si l'une echoue, les autres continuent** : le
calendrier sort quand meme, avec ce qui manque dit en toutes lettres.

```
9 match(s) a venir dans 1 competition(s), sur 7 jour(s).
  (Bundesliga injoignable : HTTP 500 sur ger.1)
  (le calendrier ci-dessus est donc incomplet ; les autres competitions ont repondu)
```

Quand aucune ne repond, la commande le dit et sort en erreur plutot que de
laisser croire a un week-end sans football.

### Le classement

`--scores` dit ce qui se joue, `--next` ce qui arrive, `--top-scorers` ce qu'on
a vu passer. Restait la seule question qu'un supporter pose sans regarder de
match : **ils sont ou, au classement ?**

```bash
butbutbut --table             # le classement des competitions suivies
butbutbut --table l1          # ... d'une competition
butbutbut --table om          # ... de la competition de cette equipe, sa ligne surlignee
butbutbut --table l1,om       # les deux a la fois, dans n'importe quel ordre
```

```
butbutbut : classement - Ligue 1

Ligue 1 (2026-27)
   #  Equipe                     J     G     N     P  Diff   Pts
   1  AS Monaco                  3     3     0     0    +4     9
   2  Paris FC                   3     2     1     0    +4     7
   3  Lyon                       3     2     1     0    +4     7
   ...
> 10  Marseille                  3     1     0     2    +1     3
   ...
  18  AJ Auxerre                 3     0     0     3    -7     0
```

(La ligne surlignee est celle de `--table om`.)

Le mot qui suit `--table` est lu comme une **competition** si le catalogue le
reconnait, comme une **equipe** sinon. Ce sont exactement les noms de
`--leagues` et de `--teams` : `l1`, `nhl`, `top14` d'un cote, `om`, `barca`,
`manu` de l'autre. Aucun club ne s'appelle `big5`.

Un pays, si. `france` est le raccourci de la Ligue 1 autant que le nom d'une
selection : la competition l'emporte, donc `--table france` sort la Ligue 1, et
`--table france --leagues 6nations` aussi - le mot donne a `--table` passe avant
`--leagues`, sans le dire. Meme sort pour `angleterre`, `espagne`, `italie`,
`allemagne`, `portugal`, `ecosse`, `bresil`, `argentine`, `mexique`, `japon` et
`usa`. Pour un classement de selections, nommer la competition repond mieux de
toute facon : `--table 6nations` montre la ligne de la France au milieu de
celles qui lui donnent son sens.

Une equipe nommee ne montre pas sa seule ligne : un rang tout seul ne veut rien
dire, c'est le classement de sa competition qui repond a la question. Elle est
surlignee d'un chevron, le meme signe que `--scores` emploie pour "en cours" -
pas une couleur, parce qu'un terminal peut etre en noir sur blanc ou redirige
dans un fichier.

`--exclude-teams` n'a **aucun effet** ici, et c'est voulu : on ne retire pas une
equipe d'un classement. Les rangs se comptent les uns par rapport aux autres, et
une ligne manquante ferait un tableau qui ment. Taire un match, oui ; trouer un
classement, non.

#### Les colonnes suivent le sport

Le rugby et le hockey n'ont pas la meme notion de classement que le football, et
les colonnes le disent :

| Sport    | Colonnes                          | Ce qui change |
|----------|-----------------------------------|---------------|
| Football | `J G N P Diff Pts`                | le socle |
| Hockey   | `J G P DP Diff Pts`               | pas de match nul, mais les **defaites en prolongation** |
| Rugby    | `J G N P Bon Diff Pts`            | les **points de bonus** |

Un match de hockey se decide toujours, en prolongation ou aux tirs au but :
afficher une colonne "N" de zeros serait inventer une statistique. En revanche
une defaite en prolongation rapporte un point, et sans la colonne `DP` le total
de la ligne ne se retrouve pas. Au rugby, ce sont les points de bonus qui font
passer une equipe devant une autre a nombre de victoires egal. **Rien n'est
fabrique** : chaque colonne vient d'une statistique que la source publie, et une
statistique absente donne un tiret, jamais un zero.

Le tableau tient dans **80 colonnes**, meme au rugby qui en compte le plus. Un
tableau qui se replie sur deux lignes ne se lit plus du tout.

#### Ce qui vient de la source, et ce qu'on n'invente pas

Le classement a son propre endpoint chez ESPN, lu avec le meme client, les memes
en-tetes et la meme politesse que les scores :

```
https://site.api.espn.com/apis/v2/sports/<sport>/<slug>/standings
```

C'est bien `apis/v2` et non `apis/site/v2` comme le tableau de bord : la
deuxieme adresse repond 200 avec un objet vide, ce qui ressemble a une
intersaison alors que c'est juste la mauvaise porte.

**Le rang n'est jamais calcule.** Le depart entre deux equipes a egalite se joue
sur des regles propres a chaque competition - difference de buts ici,
confrontations directes la, essais marques ailleurs - et les refaire finirait
par mentir un jour, sur une competition qu'on ne regarde pas. On affiche le rang
qu'ESPN publie (`rank` au football et au rugby, `playoffSeed` au hockey, qui n'a
pas de `rank` du tout).

Le **tri**, lui, est necessaire, et c'est une surprise de la source : un
championnat arrive deja trie, mais un groupe de Coupe du monde arrive dans le
desordre et la conference Ouest de la NHL commence a sa 4e tete de serie. On
range donc les lignes par le rang publie ; quand la source n'en publie aucun, on
garde son ordre et on numerote.

**Un bloc, ou plusieurs.** La source met toujours une *liste* de blocs, meme
quand il n'y en a qu'un : un championnat en a un, la NHL deux (ses conferences),
une Coupe du monde douze (ses groupes). Le nom du bloc n'est ecrit que s'il y en
a plusieurs - sur un championnat, la source appelle son unique bloc "French
Ligue 1 2026-27", ce qui ne ferait que repeter la ligne du dessus.

```
butbutbut : classement - NHL

NHL (2025-26)
  Eastern Conference
   #  Equipe                     J     G     P    DP  Diff   Pts
   1  Carolina Hurricanes       82    53    22     7   +56   113
   ...
  Western Conference
   #  Equipe                     J     G     P    DP  Diff   Pts
   1  Colorado Avalanche        82    55    16    11   +99   121
   ...
```

#### Quand il n'y a rien a classer

Une coupe se joue en tableau, pas en classement, et entre deux saisons la source
n'a rien a servir. Dans les deux cas la reponse est une phrase, pas un tableau
vide - qui ressemblerait trop a une panne - et elle nomme l'endroit exact ou on
est alle voir :

```
butbutbut : classement - Coupe de France

Aucun classement a afficher pour Coupe de France.
  (Coupe de France : aucun classement publie sous soccer/fra.coupe_de_france)
  (une coupe se joue en tableau ; hors saison, la source n'a rien a servir)
```

Une equipe qu'on ne trouve nulle part obtient le meme traitement, et c'est la
que se voit une faute de frappe : comme `--next`, `--table` ne confronte pas le
mot au catalogue des clubs, verification qui couterait une requete de plus par
competition sur une commande qu'on lance en passant.

```
Aucune ligne pour zzzclub dans les classements de Ligue 1.
```

**Une requete par competition**, les unes apres les autres et espacees, comme
`--next` et comme le demarrage du daemon. **Si l'une echoue, les autres
continuent** ; quand aucune ne repond, la commande le dit et sort en erreur.

```
  (Bundesliga injoignable : HTTP 500 sur ger.1)
  (le classement ci-dessus est donc incomplet ; les autres competitions ont repondu)
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

#### Nommer le son soi-meme : `--sound-for`

Renommer un fichier suppose de le copier dans le dossier `sound`, et d'accepter
que butbutbut devine ce que `om` veut dire. Quand le cri du club est deja
quelque part sur le disque - ou quand le nom du fichier sert a autre chose -
la paire se dit directement :

```bash
butbutbut --sound-for om=~/sons/allez-om.wav
butbutbut --sound-for om=~/sons/om.wav,ucl=~/sons/hymne.mp3
butbutbut --teams om --sound-for om=~/sons/om.wav,contre=~/sons/aie.wav
```

A gauche, les memes mots que partout ailleurs : ceux de `--teams` pour un club
(`om`, `barca`, `manu`, `marseille`, un debut de nom), ceux de `--leagues` pour
une competition (`l1`, `ucl`, `nhl`, un code ESPN), et `contre` pour un but
encaisse par une equipe suivie. A droite, un chemin - `~` compris.

**Qui gagne quand un but coche les deux ?** L'equipe. Un but de l'OM en Ligue
des champions, avec `om=` et `ucl=` nommes tous les deux, sort le son de l'OM :
c'est le plus precis qui parle, exactement comme pour les noms de fichiers. Ce
sont d'ailleurs les **memes quatre etages** - l'equipe, `contre`, la
competition, le fond sonore - et non un second mecanisme pose a cote. La seule
difference : `--sound-for` n'a pas d'etage general. Un son nomme vise quelqu'un,
il ne devient jamais le bruit de fond des autres buts.

**Et si le dossier dit deja quelque chose ?** A etage egal, ce qui est nomme
couvre ce qui est devine : avec `om.mp3` dans le dossier *et*
`--sound-for om=~/sons/om.wav`, c'est le second qui sort. Celui qui a ecrit la
paire vient de dire lequel il voulait.

**Un chemin fautif se dit au demarrage**, pas au premier but trois heures plus
tard - c'est la meme logique qu'un nom d'equipe mal orthographie :

```
$ butbutbut --sound-for om=~/sons/om.wav
butbutbut : le son de om : fichier introuvable (/home/moi/sons/om.wav)
$ butbutbut --sound-for marseile=~/sons/om.wav
butbutbut : aucune equipe ne correspond a 'marseile' dans Ligue 1. [...]
```

Le fichier doit exister, etre lisible, et porter une extension que butbutbut
sait jouer (wav, mp3, ogg, opus, flac, m4a, aac). Toutes les paires fautives
sont dites d'un coup : corriger trois chemins en relancant trois fois n'amuse
personne.

Une fois parti, en revanche, le daemon ne s'arrete plus pour si peu. Un fichier
qui **disparait en cours de route** - cle USB debranchee, dossier renomme - fait
retomber le but sur le son d'en dessous (le dossier, puis le son fourni), et
laisse une ligne au journal :

```
2026-09-07 21:14:03  son nomme pour om indisponible (fichier introuvable) :
/media/cle/om.wav -- le son par defaut prend le relais
```

`--volume` et `--no-sound` gardent leur portee : le mode muet coupe aussi les
sons nommes, et `--volume` continue de ne regler que la corne synthetisee - un
fichier a soi se regle dans son propre editeur, comme ceux du dossier `sound`.

```bash
butbutbut --status            # ce que chaque paire arme, et ce qui cloche
```

```
  son nomme   : 3 paire(s), le plus precis l'emporte
                om -> om.wav           quand cette equipe marque
                contre -> aie.wav      quand une equipe suivie encaisse
                ucl -> hymne.mp3       les buts de Ligue des champions
```

Et c'est bien `--status` qui le dit, meme quand ca cloche : un chemin fautif est
refuse au demarrage de toutes les commandes **sauf celle-la**. Sortir en erreur
devant la seule commande a qui on pose justement la question reviendrait a
refuser d'y repondre ; elle affiche donc la paire en cause, avec ce qu'elle a -
`om -> om.wav  quand cette equipe marque  (fichier introuvable)`. C'est le cas
qui compte, parce que le demarrage remonte parfois a des semaines et qu'un
disque externe se debranche.

Dans le fichier de configuration, tout tient dans une seule cle - separee par
des virgules, ou une paire par ligne quand la liste s'allonge :

```ini
[butbutbut]
teams = om
sound_for =
    om=~/sons/om.wav
    contre=~/sons/aie.wav
    ucl=~/sons/hymne.mp3
```

Une virgule ne coupe que devant une nouvelle paire : un chemin qui en contient
une (`om=~/sons, vol. 2/om.wav`) reste lisible tel quel.

```bash
butbutbut --no-sound          # muet
butbutbut --no-overlay        # juste le son et le journal, pas de carte
butbutbut --no-logos          # pas d'ecusson sur les cartes
butbutbut --duration 8        # garder la carte 8 s (defaut : la duree du son)
```

### La voix

Tout ce qui precede suppose qu'on regarde l'ecran. Le son dit qu'il s'est passe
quelque chose, la carte dit quoi - mais elle ne dit rien a qui travaille dans
une autre fenetre, sur un autre bureau, ou ne voit pas l'ecran du tout. Une
phrase dite a voix haute porte le score et le buteur sans qu'on leve les yeux.

```bash
butbutbut --speak                    # le son, puis la phrase
butbutbut --speak --no-sound         # la voix seule, sans corne
butbutbut --test --speak             # l'essayer tout de suite, sans attendre un but
```

La phrase est **celle du crochet** - la variable `BUT_TEXT` de `--on-goal`,
mot pour mot :

```
BUT ! [Ligue 1] Angers 1 - 2 Stade Rennais - But de A. Kalimuendo (58')
```

Il n'y en a qu'une dans le programme, expres : deux formulations auraient fini
par ne plus dire la meme chose. Elle suit la **langue des cartes** (`--lang`),
pas celle du journal - on parle a qui regarde l'ecran, pas a qui relira
`--today` demain matin.

**Rien a installer, nulle part** - c'est la meme regle que pour le reste :

| Systeme | Ce qui parle | A installer |
| --- | --- | --- |
| Windows | PowerShell et `System.Speech` | rien |
| macOS | `say` | rien |
| Linux | `spd-say`, sinon `espeak-ng`, sinon `espeak` | `speech-dispatcher` ou `espeak-ng` |

`butbutbut --status` dit lequel parlerait ici, avant meme qu'on ait pose
l'option :

```
  voix        : inactive (voir --speak) - PowerShell (System.Speech) parlerait
```

C'est la reponse qui compte, parce qu'elle arrive avant d'avoir rien installe :
une machine ou rien ne parle le dit la, et pas au premier but. L'option posee,
la meme ligne change de temps :

```
  voix        : PowerShell (System.Speech), dans la langue des cartes
```

**Un mot sur les voix installees.** Windows choisit une voix de la langue des
cartes quand la machine en a une, et garde la sienne sinon : une machine
anglaise lira du francais avec un accent anglais plutot que de se taire.
`spd-say` et `espeak` recoivent la langue en clair. `say`, lui, n'a pas
d'option de langue - c'est la voix reglee dans les Reglages qui parle, quelle
qu'elle soit ; `say -v '?'` les enumere.

**Deux buts coup sur coup ?** Les phrases **font la queue** et sortent l'une
apres l'autre. C'etait le choix a faire, et il se defend : deux buts du meme
releve, c'est le plus souvent deux matchs differents, et jeter le second
laisserait croire a un score qui n'existe plus. Parler par-dessus, lui, rend
les deux inaudibles. La file est bornee a quatre phrases, et au-dela c'est la
plus **ancienne en attente** qui saute : un soir de folie, on veut savoir ou on
en est, pas ecouter le quart d'heure precedent.

La voix attend aussi que la corne ait fini avant de parler - deux secondes et
demie - pour la meme raison.

**Ce qui la fait taire.** Exactement ce qui fait taire le haut-parleur, parce
qu'elle en est un :

- `--quiet-hours` et `--quiet-while-presenting` : la nuit et pendant une
  presentation, on ne parle pas plus qu'on n'affiche (voir
  [Ne pas deranger](#ne-pas-deranger)) ;
- `--spoiler-free` : ce qui n'est pas montre ne se dit pas non plus, sinon
  l'option ne protegerait plus rien ;
- le journal, lui, garde tout dans les deux cas, et `--today` le raconte.

**Ce qui ne peut pas arriver.** Aucune panne de voix ne touche le daemon :
programme absent, voix non installee, commande qui rend 1, commande qui ne rend
jamais la main (elle est tuee au bout de 30 s). Une ligne au journal, **une
seule** - un samedi entier ecrirait sinon autant de lignes que de buts pour une
panne qui ne changera plus - et le match continue. La parole vit dans un fil a
elle : ni la carte, ni le releve suivant ne l'attendent.

> `--speak` ne parle pas pendant un `--replay`. Une soiree rejouee a
> `--speed 60` reduit une mi-temps a trente secondes : la voix parlerait encore
> du premier but que le match serait fini.

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

Un soir de coupe, cette meme carte porte en plus le verdict de la seance de
tirs au but - `Tirs au but 3 - 5 : Stade de Reims` - parce qu'un `1 - 1` ne dit
pas qui se qualifie. Voir [Les tirs au but](#les-tirs-au-but).

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
sound_for = om=~/sons/om.wav, ucl=~/sons/hymne.mp3
volume = 0.55
no_sound = non
speak = non
no_overlay = non
no_phase_cards = non
catch_up = non
quiet = non

# Ne pas deranger : la nuit, et quand on presente
quiet_hours = 23:00-08:00
quiet_while_presenting = non
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

**Des recettes qui marchent deja.** Une porte de sortie ne sert a rien si
personne ne sait ce qu'il y a derriere : personne n'ecrira son webhook Discord
a partir d'un `notify-send`. Le dossier
[`recipes/`](https://github.com/boubou666/butbutbut/tree/main/recipes) contient
donc huit commandes completes, a copier et a tailler - un webhook Discord, un
webhook Slack, un evenement Home Assistant a qui l'automatisation de la maison
repond, une ampoule WiZ qui vire au vert le temps du but puis retrouve
exactement l'etat qu'elle avait, un compteur de buts en JSON qui suit meme les
annulations de la VAR, une vraie notification du systeme qui reste dans le
centre de notifications, un bandeau texte pour OBS ou une barre d'etat, et un
gabarit shell pour ne reagir qu'aux buts qu'on veut.

```bash
butbutbut --on-goal 'python3 ~/butbutbut/recipes/discord_webhook.py'
```

Zero dependance la aussi : rien que la bibliotheque standard de Python, ou le
shell de la machine. Pas de `curl` suppose present, pas de `jq`. Un secret -
URL de webhook, jeton - se lit dans une variable d'environnement et ne passe
**jamais** par la ligne de commande, qui se lit dans `ps` et que
`butbutbut --status` reaffiche. Le mode d'emploi, les reglages de chacune et ou
poser le secret selon le systeme sont dans
[`recipes/README.md`](https://github.com/boubou666/butbutbut/blob/main/recipes/README.md).

Ces recettes voyagent avec le code source, et pas dans le paquet installe par
`pipx` : butbutbut ne les lance jamais lui-meme, c'est toi qui le fais. Un test
du depot compare les variables `BUT_*` qu'elles lisent a celles que le crochet
publie vraiment - une recette ne peut pas pourrir en silence en promettant un
detail qui n'existe pas.

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
qui est arme. Un match mis en `--spoiler-free`, lui, ne lance rien : le
crochet est une alerte de plus, et le mode sans spoiler les coupe toutes -
autrement une guirlande ou un webhook raconterait le but que l'ecran et le
haut-parleur viennent justement de taire.

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

**Toutes** les commandes suivent, y compris les valeurs qu'elles affichent -
`il y a 12 s` devient `vor 12 s`, pas seulement l'etiquette devant : l'aide,
`--status`, `--scores`, `--next`, `--table`, `--screens`, `--list`,
`--list-teams`, `--today`, `--week`, `--month`, `--since`, `--top-scorers`,
`--stats`, `--export` et `--test-hook`.

Les colonnes tiennent dans les cinq langues, et c'est cette contrainte-la qui
decide de la traduction d'une etiquette de `--status` : le deux-points tombe au
meme caractere partout, quitte a abreger (`rattrapage` devient `catch-up`,
`recuperacion`, `recupero`, `Nachholen`).

Les en-tetes du classement de `--table` suivent la meme regle, et pour la meme
raison qu'elles etaient un probleme : `G`, `N`, `P` sont les initiales de
gagne, nul et perdu, et ne veulent rien dire pour qui lit la page en anglais.
Elles deviennent `W D L`, `G E P`, `V N P`, `S U N` - chacune tenant dans une
colonne de six signes, ce qu'un test verifie langue par langue plutot que de
s'en remettre a l'oeil.

**Ce qui reste en francais** :

- **le journal, et par choix.** `--today` le relit, et un fichier ecrit avant
  un changement de langue resterait sinon a moitie illisible pour le
  relecteur. Une carte peut donc afficher `TOR!` pendant que le journal note
  `BUT` - et une ligne citee par `--today` reste dans la langue ou elle a ete
  ecrite ;
- **les dates.** Les jours de la semaine (`lundi`, `mar.`), `(aujourd'hui)` et
  `(demain)`, le compte a rebours de `--next` (`dans 3 h`) sont ecrits en dur
  dans `cli.py` et ne passent pas par le catalogue ;
- **les valeurs de `--status` qui vont aussi au journal.** Trois familles, et
  une seule raison pour les trois : la meme phrase sert a l'ecran ET a une
  ligne de journal, qui reste francaise. Les lignes `silence` et `voix`
  (`silence.describe()`, `speech.describe()`), la ligne `equipes`
  (`teams.Filter.describe()`, que le daemon note aussi au demarrage), et le
  detail d'un son nomme qu'on ne peut pas jouer (`sound.unusable()`, que le
  journal reprend quand un fichier disparait en cours de soiree). Les
  etiquettes, elles, sont traduites ;
- **le fichier de configuration commente** qu'ecrit `--write-config`, et les
  six messages qui refusent un argument impossible : les quatre du demarrage
  (`--speed 0`, `--record` avec `--replay`, `--retry-fullscreen` et
  `--quiet-while-presenting` hors de Windows) et les deux du rejeu (un
  enregistrement illisible, un enregistrement qui ne nomme aucune competition
  reconnaissable) ;
- **le nom des sports dans une phrase a trou.** `tout le {} (N competitions)`
  recoit le nom du sport, que `sports.py` garde en francais pour le journal :
  la traduire ferait une phrase a moitie traduite. Les titres du catalogue,
  eux, sont traduits (`Ice hockey (on request)`, `Eishockey (auf Wunsch)`).

Une phrase qu'un catalogue ne porte pas retombe sur le francais plutot que de
disparaitre : une traduction incomplete laisse le programme utilisable. C'est
ce qui a permis a sept commandes d'etre livrees en francais dans les cinq
langues sans que rien ne casse - et sans que personne ne le voie. Un test
compare maintenant, langue par langue, les phrases que le code donne a traduire
a celles que les catalogues portent : ce qui reste en francais y est nomme une
par une, avec sa raison.

Ce garde-fou a une portee exacte, et elle vaut la peine d'etre dite : il ne
voit que ce qui **passe par `tr()`**. Une phrase ecrite en dur, qui n'est
jamais donnee a traduire, lui est invisible - c'est le cas des trois familles
ci-dessus et des jours de la semaine. Il empeche la dette de revenir par la
porte qu'elle avait empruntee sept fois ; il ne remplace pas de regarder
l'ecran dans les cinq langues.

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

Sans rien de plus, l'endpoint ne sert que **la journee en cours** : assez pour
guetter les buts, pas pour dire quand tombe le prochain match. Il accepte pour
ca un parametre `dates`, un jour (`?dates=20260908`) ou un intervalle
(`?dates=20260908-20260915`), bornes comprises. C'est ce dernier qui permet a
`--next` de couvrir une semaine entiere en une seule requete par competition,
la ou un jour a la fois en couterait sept.

Le meme hote publie deux autres endpoints, lus avec le meme client et les memes
en-tetes : `.../teams`, qui sert a valider ce qu'on tape dans `--teams`, et le
classement de `--table`, dont l'adresse n'a pas tout a fait la meme forme.

```
https://site.api.espn.com/apis/v2/sports/<sport>/<code>/standings
```

`apis/v2`, et non `apis/site/v2` comme le tableau de bord : la seconde adresse
existe pourtant, et repond 200 avec un objet vide - une intersaison en apparence,
une mauvaise porte en realite. La difference est notee dans le code pour ne pas
avoir a la redecouvrir.

Tout ce qu'on sait de cette source - les parametres qu'elle accepte, la forme
exacte de ses reponses, ses en-tetes, ses codes d'erreur, ses pieges, et les
218 competitions de football qu'elle expose - est reuni dans
[docs/api-espn.md](docs/api-espn.md) : le contrat qu'on s'ecrit a soi-meme,
puisque le fournisseur n'en ecrit pas. Chaque ligne y a ete verifiee contre la
vraie source, et le document donne les commandes pour tout refaire.

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

### Les tirs au but

Une seance de tirs au but est le seul moment ou la source dit "but" onze fois
sans que personne ne marque. Tout depend donc d'une question, et d'une seule :
**est-ce que le score publie bouge pendant la seance ?** La reponse a ete allee
chercher sur des matchs a elimination directe deja joues, et elle est **non**.

| Seance | Ce que la source publie |
| --- | --- |
| Chelsea - Liverpool, finale de la FA Cup, 14 mai 2022 | score `0 - 0`, `shootoutScore` 5 et 6, onze tirs, statut `STATUS_FINAL_PEN`, detail `FT-Pens` |
| Angers - Reims, Coupe de France, 25 fevrier 2025 | score `1 - 1`, **aucun `shootoutScore`**, huit tirs horodates de 91' a 99', meme statut |
| Argentine - France, finale de la Coupe du monde, 18 decembre 2022 | score `3 - 3`, `shootoutScore` 4 et 2, six tirs, meme statut |
| Atletico - Real Madrid, Ligue des champions, 12 mars 2025 | score `1 - 0`, `shootoutScore` 2 et 4, six tirs, meme statut |

Le score reste celui de la fin du temps reglementaire, et la seance est publiee
**a cote**. Donc **pas de soir de coupe a dix cornes** : la detection ne
regarde que le score, le score ne bouge pas, rien ne se declenche. Le bug qu'on
redoutait n'existe pas, et c'est la premiere chose que ce chantier a etablie.

Il y a en revanche le manque inverse, et il est double.

**Un tir au but se presentait comme un but.** Chaque tir reussi est publie dans
le meme tableau que les buts, avec le meme drapeau :

```json
{"type": {"text": "Penalty - Scored"}, "scoreValue": 1, "scoringPlay": true,
 "penaltyKick": true, "shootout": true, "clock": {"displayValue": "120'"}}
```

Ce tableau-la est celui qui habille les cartes et que `--scores` recopie. Une
finale de FA Cup terminee 0-0 sortait donc une carte `FIN DU MATCH` annoncant
`Chelsea 0 - 0 Liverpool` suivie de **onze buteurs**. Les tirs sont maintenant
mis de cote des la lecture : le drapeau `shootout` est le seul qui les
distingue d'un vrai but, et c'est le seul auquel on puisse se fier puisque le
score, lui, les dement.

**Une seance ne disait pas qui se qualifiait.** `FIN DU MATCH / Angers 1 - 1
Stade de Reims` est exact et rate l'essentiel. La troisieme ligne le dit
maintenant, et le vainqueur y est mis en valeur comme un buteur l'est ailleurs :

```
FIN DU MATCH
Angers 1 - 1 Stade de Reims
Tirs au but 3 - 5 : Stade de Reims
Angers : B. Dieng 90'+5'
Stade de Reims : K. Nakamura 79'
```

Le total vient de `shootoutScore` quand la source le donne. Il manque environ
une fois sur dix - la Coupe de France du 25 fevrier 2025 ne le portait pas,
sans rien qui la distingue des autres soirs - et on compte alors les tirs
reussis, ce qui donne le meme nombre partout ou les deux etaient la. Le nom du
vainqueur, lui, vient du drapeau `winner` : c'est la seule chose de la reponse
qui sache dire qui continue sur un 1-1. Sans lui, la carte se contente de
`Tirs au but` - elle n'invente pas un qualifie.

La carte reste **muette**, comme toutes les fins de match : un verdict s'ecrit,
il ne se corne pas.

Le **hockey** n'a jamais eu ce probleme, et pour une raison de reglement : sa
fusillade **donne un but au vainqueur**, dans le score du match. Vegas 4-3
Chicago le 3 decembre 2025, statut `STATUS_FINAL` et detail `Final/SO` - le
score bouge donc pour de vrai, une fois, au bon moment, et butbutbut annonce ce
but comme les autres. C'est correct : la NHL aussi l'appelle le but vainqueur.
La carte de fin de match ajoute seulement `Vainqueur aux tirs au but : Vegas
Golden Knights`, parce qu'un 4-3 qui n'a pas eu lieu dans le temps
reglementaire merite d'etre explique. Noter au passage que le hockey ne le dit
pas au meme endroit : son statut reste `STATUS_FINAL`, seul le detail change.

Le **rugby a XV** n'a aucun marqueur : le reglement prevoit bien un concours de
coups de pied, il n'a jamais servi dans un match professionnel, et guetter une
chaine qu'ESPN n'a jamais eu a ecrire serait guetter une invention.

**Ce qui reste ouvert.** Tout ceci est etabli sur des seances **terminees**. Ce
que la source publie pendant les quelques minutes que dure la seance - un
statut `STATUS_SHOOTOUT` ? un score qui monterait puis reviendrait ? - n'a pas
pu etre observe : il aurait fallu etre devant un match a elimination directe au
bon moment. Le score final etant celui du temps reglementaire dans les quatre
competitions relevees, il n'y a pas de raison de croire qu'il bouge entre-temps
- mais c'est une deduction, pas une observation, et elle est ecrite ici pour
que le jour ou quelqu'un verra une carte de trop, il sache ou regarder.

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

Et les releves sont **compresses**. La source sait servir du gzip, encore
faut-il le demander : personne ne le fait a votre place, `urllib` n'annonce
rien tout seul. Le tableau de bord de la Ligue 1 tombe de 33 832 a 4 145
octets, et un tour complet de `--leagues all` de **1 355 ko a 148 ko** - neuf
fois moins. Sur une soiree de deux heures a suivre les 36 competitions, c'est
400 Mo qui deviennent 44 Mo : de quoi laisser le programme tourner sur un
partage de connexion sans y penser. Rien a installer, `gzip` est dans la
bibliotheque standard, et une reponse non compressee continue de passer telle
quelle.

C'est la seule economie disponible, et ce n'est pas faute d'avoir cherche
l'autre : la source n'envoie **ni `ETag` ni `Last-Modified`**, il n'y a donc
rien a poser dans une requete conditionnelle qui aurait evite les releves
inchanges.

### Le canari

Cette source n'est documentee nulle part, et personne ne nous previendra le
jour ou `penaltyKick` sera renomme ou `athletesInvolved` deplace. Rien ne
casserait : la lecture est defensive, donc le daemon continuerait de tourner -
il cesserait simplement d'annoncer les penaltys. Une panne muette, la pire
espece. Et les 523 tests n'y verraient rien : c'est eux qui fabriquent la
reponse d'ESPN.

D'ou un canari, qu'on peut lancer a la main :

```bash
python tools/canari.py
python tools/canari.py --leagues fra.1,ger.1 --dates 20250517
```

Il interroge la source pour de vrai, puis verifie que chaque cle lue par
`butbutbut/espn.py` est encore la, et du bon type. Il va meme repasser la
reponse a `espn.parse()`, le code que le daemon execute : des cles presentes
qui ne produisent plus ni match, ni but, ni buteur seraient une derive tout
aussi grave.

Une cle peut aussi rester en place et **changer de forme**, ce qui ne se voit
nulle part ailleurs. Le canari relit donc la minute des buts avec le lecteur du
journal, celui dont sort l'histogramme de `--stats` : une horloge que plus
personne ne sait lire vaut une ligne rouge. Le football seul est tenu a cette
regle - `12:34`, l'horloge d'un match de hockey, n'est pas une minute de jeu.

Le rapport donne une ligne par cle :

```
  ok           competitor.team.color                        couleur hex     6/6
  ok           detail.penaltyKick                           booleen         16/16
  MANQUE       detail.athletesInvolved[0].shortName         texte non vide  0/16
```

Trois verdicts, et c'est la nuance qui compte :

| Verdict | Ce que ca dit |
| --- | --- |
| `ok` | la cle est la, avec la bonne tete |
| `MANQUE` / `TYPE` | elle a disparu ou change de forme - sortie non nulle |
| `non verifie` | rien de cette espece ne s'est presente (aucun but ce jour-la) : ce n'est pas un echec |

Un mardi de juillet, le tableau du jour peut etre vide : le canari ne crie pas
au loup pour ca. Il redemande alors les quatre derniers mois d'un coup
(`?dates=AAAAMMJJ-AAAAMMJJ`), de quoi retomber sur des matchs joues - et donc
sur des buts a inspecter - en toute saison.

Il tourne aussi tout seul une fois par jour
([`canari.yml`](.github/workflows/canari.yml)), et **jamais sur un push ni une
pull request** : la CI ordinaire doit rester hors reseau et deterministe, sans
quoi une panne d'ESPN repeindrait en rouge des changements qui n'y sont pour
rien - et on apprendrait vite a ignorer le rouge. Un canari rouge, lui, ouvre
une issue avec son rapport.

**Et quand il vire au rouge ?** Le rapport nomme la cle, ce qui etait attendu,
et combien de fois elle manquait. Tout ce qui la lit vit dans
`butbutbut/espn.py` (`parse()`, `_parse_details()`, les `team_*()`). Reste a
decider : la source l'a renommee (on suit), deplacee (on va la chercher
ailleurs), ou supprimee (on retire la fonctionnalite plutot que d'afficher du
vide). Le changement se repercute ensuite dans les charges utiles fabriquees
par `tests/helpers.py`, sans quoi la suite hors reseau continuerait de valider
un monde qui n'existe plus.

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

**Elle ne sort personne de son plein ecran, en revanche.** Une carte n'est
jamais activee et n'a pas de bouton dans la barre des taches
(`WS_EX_NOACTIVATE` et `WS_EX_TOOLWINDOW`, poses **avant** le premier
affichage). Sans eux, Windows donnerait le premier plan a la carte a l'instant
ou elle apparait ; et s'il refuse le vol, il fait clignoter son bouton a la
place - un bouton qui clignote fait remonter la barre des taches par-dessus le
jeu, et le plein ecran est perdu pour un but. L'ordre compte autant que les
styles : poses apres l'affichage, ils arrivent une fois le mal fait.

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

C'est la premiere des trois fois ou butbutbut se demande "est-ce le moment ?" -
les deux autres sont l'heure qu'il est et le regard des autres, et elles n'ont
pas le meme verdict : voir [Ne pas deranger](#ne-pas-deranger).

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

## Plus loin que le jour meme

Le meme analyseur, avec une fenetre plus large :

```bash
butbutbut --week                 # les 7 derniers jours, aujourd'hui compris
butbutbut --month                # les 30 derniers jours
butbutbut --since 2026-09-01     # depuis cette date (AAAA-MM-JJ)
```

`--since` l'emporte sur `--week` et `--month`. Une date illisible est refusee
tout de suite, avec le format attendu :

```
butbutbut : date illisible : 'hier'. Format attendu : AAAA-MM-JJ, par exemple --since 2026-09-01
```

### Quelques jours : le detail

```
butbutbut : buts signales du sam. 05/09/2026 au lun. 07/09/2026

sam. 05/09/2026
    Ligue 1          Nice 1 - 0 Lens                     G. Laborde 12'
    Ligue 1          Nice 1 - 1 Lens                     F. Thauvin 44'
    Ligue 1          Nice 2 - 1 Lens                     G. Laborde 62'
    Premier League   Arsenal 1 - 0 Tottenham             M. Odegaard 21'
    Premier League   Arsenal 2 - 0 Tottenham             B. Saka 47'
  - Premier League   Arsenal 1 - 0 Tottenham             Score corrige 48'
    Premier League   Arsenal 2 - 0 Tottenham             K. Havertz 77'
    Bundesliga       Bayer 04 Leverkusen 1 - 0 Dortmund  P. Schick 29'
    Bundesliga       Bayer 04 Leverkusen 2 - 0 Dortmund  F. Wirtz 73'

dim. 06/09/2026
    Ligue 1          Marseille 1 - 0 Nantes              M. Greenwood 17'
    Ligue 1          Marseille 2 - 0 Nantes              A. Rabiot 59'
    Ligue 1          Lille 1 - 0 Auxerre                 J. David 38'
    LaLiga           Barcelone 1 - 0 Valence             R. Lewandowski 26'
    LaLiga           Barcelone 2 - 0 Valence             Lamine Yamal 64'
    Serie A          Inter 1 - 0 Roma                    L. Martinez 82'

lun. 07/09/2026
    Ligue 1          Angers 1 - 0 Stade Rennais          C. Arcus 61'
    Ligue 1          Angers 1 - 1 Stade Rennais          A. Kalimuendo 79'

16 but(s) signale(s), 3 jour(s), 5 competition(s).
'-' = but retire par la VAR (1) : 15 but(s) confirme(s).
```

Au-dela d'un jour, le jour devient le seul titre et la competition passe en
colonne : grouper par jour **et** par competition poserait un en-tete toutes
les deux lignes. L'heure de detection cede la place a la minute du match, plus
parlante une fois la soiree passee.

### Un mois : une ligne par jour

Trente jours de Ligue 1, ce sont trois cents buts : le detail ne tiendrait pas
sur un ecran. La densite se decide donc sur ce qu'il y a a montrer, pas sur la
fenetre demandee - tant que la liste tient sur un ecran elle est donnee, au-dela
chaque journee se resume a sa ligne :

```
butbutbut : buts signales du dim. 09/08/2026 au lun. 07/09/2026

  sam. 29/08   9 but(s)          Premier League 4, Ligue 1 3, LaLiga 2
  dim. 30/08   9 but(s)          Ligue 1 4, Serie A 3, Bundesliga 2
  mar. 01/09   2 but(s)          Premier League 2
  mer. 02/09   2 but(s)  -1 VAR  Ligue 1 2
  sam. 05/09   8 but(s)  -1 VAR  Ligue 1 3, Premier League 3, Bundesliga 2
  dim. 06/09   6 but(s)          Ligue 1 3, LaLiga 2, Serie A 1
  lun. 07/09   2 but(s)          Ligue 1 2

38 but(s) signale(s), 7 jour(s), 5 competition(s).
'-N VAR' = but retire par la VAR (2) : 36 but(s) confirme(s).
```

Une fenetre plus courte rend le detail, et `--top-scorers` rend les noms.

---

## Le classement des buteurs

```bash
butbutbut --top-scorers               # tout le journal
butbutbut --top-scorers --week        # sur les 7 derniers jours
butbutbut --top-scorers --teams om    # seulement les matchs de l'OM
```

```
butbutbut : buteurs vus passer depuis le debut du journal

    1  G. Laborde                  3  Nice
    2  F. Thauvin                  2  Lens
    2  H. Lepaul                   2  Angers
    2  K. Havertz                  2  Arsenal
    2  L. Martinez                 2  Inter
    2  M. Greenwood                2  Marseille
    2  M. Odegaard                 2  Arsenal
    2  P. Schick                   2  Bayer 04 Leverkusen
    9  A. Kalimuendo               1  Stade Rennais
    9  A. Rabiot                   1  Marseille
    9  B. Saka                     1  Arsenal
    9  C. Arcus                    1  Angers
    9  C. Gakpo                    1  Liverpool
    9  C. Palmer                   1  Chelsea
    9  D. Zapata                   1  Torino
    9  E. Guessand                 1  Nice
    9  F. Wirtz                    1  Bayer 04 Leverkusen
    9  H. Kane                     1  Bayern
    9  J. Bellingham               1  Real Madrid
    9  J. David                    1  Lille
  ... et 7 autre(s) buteur(s) plus bas au classement.

27 buteur(s) pour 36 but(s) confirme(s) sur 38 signale(s).
2 but(s) retire(s) par la VAR, deduit(s) du classement.
```

Sans fenetre, c'est **tout le journal** : un classement n'a d'interet
qu'accumule. A egalite le rang est partage, et le classement se combine a une
fenetre comme au filtre par equipe (`--teams`, `--exclude-teams`), qui vaut
aussi pour `--today`, `--week`, `--month` et `--since`.

**Un but refuse par la VAR ne reste a personne.** Le journal ne dit pas quel
but une annulation efface - la ligne `BUT ANNULE` ne porte ni buteur ni minute
du but d'origine, seulement le score revenu en arriere. Le rattachement est
donc positionnel, comme le fait l'arbitre video : une annulation retire le
dernier but encore debout de la meme equipe dans le meme match. Une annulation
dont le but est tombe avant l'ouverture de la fenetre n'est deduite de
personne, et le pied de sortie le dit plutot que de voler un but au hasard.

Enfin, la source publie ses actions avec quelques secondes de retard : un but
detecte avant elle est ecrit sans buteur, et le restera. Ces buts-la comptent
dans le total, jamais dans le classement, et le pied de sortie les annonce.

---

## Les formes du journal

Le journal accumule des mois de buts. `--today`, `--week`, `--month`, `--since`
et `--top-scorers` les relisent, mais tous les cinq rendent une **liste** : un
but, une ligne, dans l'ordre ou ils sont tombes. Or un tas de buts a des formes
qu'aucune liste ne montre. Est-ce qu'on marque vraiment plus en fin de match ?
Quelle competition remplit le journal ? Quelle a ete la meilleure soiree de
l'ete ? `--stats` regarde les memes lignes en tas.

```bash
butbutbut --stats                     # tout le journal
butbutbut --stats --week              # sur les 7 derniers jours
butbutbut --stats --since 2026-08-09  # depuis cette date
butbutbut --stats --teams om          # seulement les matchs de l'OM
```

```
butbutbut : ce que le journal raconte du dim. 09/08/2026 au lun. 07/09/2026

Par minute de match
    1-10  #######                                 6   4%
   11-20  #####                                   4   3%
   21-30  ##############                         12   8%
   31-40  ######################                 18  13%
   41-50  #########################              21  15%
   51-60  ###################                    16  11%
   61-70  ##############                         12   8%
   71-80  #############################          24  17%
   81-90  ####################################   30  21%

Par competition
  Ligue 1              ####################################   43  30%
  Premier League       ################################       38  27%
  LaLiga               ######################                 26  18%
  Bundesliga           ##################                     22  15%
  Serie A              #######                                 8   6%
  Ligue des champions  #####                                   6   4%

Les soirees les plus prolifiques
  mer. 19/08/2026    15 but(s)
  ven. 21/08/2026    14 but(s)
  mer. 12/08/2026    12 but(s)

Nature des buts
  But                       113  79%
  But contre son camp        11   8%
  Penalty                    19  13%

143 but(s) confirme(s) sur 144 signale(s), dans 6 competition(s).
53 match(s) avec au moins un but signale, 2.7 but(s) par match.
Un 0-0 ne laisse aucune trace dans le journal, ni dans cette moyenne.
1 but(s) retire(s) par la VAR, deduit(s) de tout ce qui precede.
17 but(s) dans le temps additionnel, comptes dans la tranche de leur minute.
```

**Des tranches de dix minutes**, parce que c'est la maille ou le football se
raconte : "juste avant la mi-temps", "dans le dernier quart d'heure". A la
minute pres il faudrait quatre-vingt-dix lignes pour ne montrer que du bruit.
Un but a `90+3'` reste un but de la 90e et va dans la tranche `81-90` : le
sortir ailleurs aplatirait justement la bosse qu'on vient voir. Et
l'histogramme couvre toujours les quatre-vingt-dix minutes, meme quand la
fenetre n'a que trois buts a la 12e : une tranche vide est une forme elle
aussi, et s'arreter au dernier but l'effacerait. Une prolongation, elle,
allonge le cadre jusqu'a la 120e.

**Une soiree n'est pas un jour de calendrier.** Le journal change de jour a
minuit, une soiree de football non : un coup d'envoi a 21h qui part en
prolongation, une affiche sud-americaine, un match de NHL vu depuis l'Europe.
Le but de 23h50 et celui de 00h12 sont de la meme soiree, et compter par date
en ferait deux demi-soirees dont aucune n'a existe. Six heures du matin coupe
la nuit. **Trois soirees sont nommees**, et les ex aequo de la troisieme sont
comptees en une ligne de plus - `... et 17 autre(s) soiree(s) a 6 but(s).` Les
nommer toutes chasserait le reste de la sortie hors de l'ecran un soir de
multiplex ; s'arreter a trois sans compter les autres laisserait croire a un
podium qui n'existe pas.

**Un but refuse par la VAR ne compte nulle part**, exactement comme dans
[le classement des buteurs](#le-classement-des-buteurs) : le rattachement
positionnel est le meme code, pas un second. Ni dans l'histogramme, ni dans la
competition, ni dans la soiree. Les annulations dont le but est tombe avant
l'ouverture de la fenetre sont annoncees a part.

**La nature d'un but sort de l'en-tete de sa ligne**, la seule chose qui la
porte : `BUT SUR PENALTY`, `BUT CONTRE SON CAMP`, `ESSAI`, `PENALITE`, `DROP`.
Quand la source publie l'action trop tard, le but est ecrit `BUT` et compte
comme tel : cette part est un plancher, pas un total exact. Une seule nature
dans la fenetre n'a pas droit a son tableau - "143 buts sur 143 sont des buts"
n'apprend rien.

**Et ce qui n'est pas la n'y est pas par honnetete.** Le journal n'ecrit que ce
qui bouge : un 0-0 n'y laisse pas une ligne, donc `--stats` ne connait aucun
match sans but, et sa moyenne est celle des matchs **ou un but est tombe** -
mecaniquement plus haute que celle d'une saison, ce que le pied de sortie dit
en toutes lettres. Le passeur, le pied, la distance, la possession : la source
ne les publie pas, personne ne peut donc les compter ici. Une minute que le
journal n'ecrit pas comme une minute de jeu - l'horloge d'un match de hockey,
un libelle de phase, une ligne d'une version qu'on ne sait plus lire - reste
hors de l'histogramme, et le pied de sortie la compte plutot que de la faire
entrer de travers.

**Le calcul se fait hors reseau** : tout est deja dans le fichier. Une reserve,
la meme que pour `--top-scorers` : nommer une equipe fait d'abord verifier ce
nom aupres du catalogue, et cette verification-la, elle, demande le reseau.
C'est voulu - `--stats --teams om` qui rendrait une page vide sur une faute de
frappe serait pire que muet - et une source injoignable le dit puis laisse
passer. Sans `--teams` ni `--exclude-teams`, rien ne sort de la machine.

Un journal absent, vide, ou dont aucune ligne ne tombe dans la fenetre le dit
en toutes lettres, comme `--today`.

---

## Le journal en donnees

`--on-goal` couvre l'amont : au moment ou le but tombe, on declenche ce qu'on
veut. Rien ne couvrait l'aval. Des mois de buts dorment dans le journal, et
tout ce qui les en sortait jusqu'ici etait **mis en page pour un oeil humain** :
colonnes alignees, barres de pourcentage, rangs partages, totaux en toutes
lettres. Un tableur, un carnet de notes, un graphe : tout cela demande des
donnees.

```bash
butbutbut --export csv > buts.csv         # tout le journal, dans un tableur
butbutbut --export json --month           # les 30 derniers jours, en JSON
butbutbut --export csv --since 2026-08-09 # depuis cette date
butbutbut --export json --teams om        # seulement les matchs de l'OM
```

Memes fenetres et memes filtres que `--stats` et `--top-scorers` : `--week`,
`--month`, `--since`, `--teams`, `--exclude-teams`. Sans fenetre, c'est **tout
le journal**. Et c'est la meme et unique lecture (`journal.goals_between`) que
tous les autres recapitulatifs : un second analyseur finirait par ne plus
compter comme le premier, et un export qui contredit `--stats` sur le meme
journal ne vaudrait rien.

```
timestamp,evening,kind,nature,standing,league,home,away,home_score,away_score,team,scorer,minute,stoppage,clock,detail
2026-09-06T18:43:27,2026-09-06,goal,goal,true,Premier League,Arsenal,Chelsea,2,1,Arsenal,M. Odegaard,50,0,50',But de M. Odegaard
2026-09-06T20:12:44,2026-09-06,goal,penalty,true,Ligue 1,"Nice, OGC",Lens,1,0,"Nice, OGC",G. Laborde,90,3,90+3',Penalty de G. Laborde
2026-09-06T21:04:10,2026-09-06,goal,goal,false,Bundesliga,Bayer 04 Leverkusen,Bayern,1,0,Bayer 04 Leverkusen,P. Schick,12,0,12',But de P. Schick
2026-09-06T21:05:58,2026-09-06,cancellation,cancelled,false,Bundesliga,Bayer 04 Leverkusen,Bayern,0,0,Bayer 04 Leverkusen,,13,0,13',Score corrige
```

```json
[
  {
    "timestamp": "2026-09-06T18:43:27",
    "evening": "2026-09-06",
    "kind": "goal",
    "nature": "goal",
    "standing": true,
    "league": "Premier League",
    "home": "Arsenal",
    "away": "Chelsea",
    "home_score": 2,
    "away_score": 1,
    "team": "Arsenal",
    "scorer": "M. Odegaard",
    "minute": 50,
    "stoppage": 0,
    "clock": "50'",
    "detail": "But de M. Odegaard"
  }
]
```

### Les champs

| Champ | Ce qu'il porte |
| --- | --- |
| `timestamp` | Le moment ou butbutbut a vu le but, en ISO 8601 : `2026-09-06T18:43:27` |
| `evening` | La soiree du but, qui n'est pas toujours son jour (voir plus bas) |
| `kind` | `goal` ou `cancellation` : la forme de la ligne du journal |
| `nature` | `goal`, `own_goal`, `penalty`, `try`, `conversion`, `penalty_goal`, `drop_goal`, `points`, et `cancelled` / `points_cancelled` pour ce que la VAR a retire |
| `standing` | Le but tient-il encore, une fois la VAR passee ? |
| `league` | La competition, telle que le journal l'a ecrite |
| `home`, `away` | Le recevant et le visiteur |
| `home_score`, `away_score` | Le score **apres** cette ligne |
| `team` | L'equipe qui marque, ou celle dont le score est revenu en arriere |
| `scorer` | Le buteur. Vide quand la source n'avait pas encore publie l'action |
| `minute` | La minute de jeu, en nombre. Vide quand elle n'est pas lisible |
| `stoppage` | Le temps additionnel, en nombre. Vide quand la minute ne l'est pas |
| `clock` | La minute telle qu'ecrite : `90+3'`, ou l'horloge d'un match de hockey |
| `detail` | La phrase du journal : `But de M. Odegaard`, `Score corrige` |

**Rien de plus, parce qu'il n'y a rien de plus.** Ces champs sortent tous de ce
que le journal porte vraiment ; aucun n'est complete aupres de la source au
moment de l'export. Le passeur, le pied, la distance, le nom complet du buteur :
personne ne les a jamais ecrits dans ce fichier, et une colonne toujours vide
serait une promesse tenue par personne.

**Les noms de colonnes sont en anglais et ne se traduisent pas**, alors que
toute la prose du programme, elle, se traduit. Un en-tete de colonne n'est pas
une phrase, c'est un contrat : un tableur ouvert sur une machine anglaise et un
script lance sur une machine francaise doivent lire le meme fichier, et une
colonne qui changerait de nom avec la langue casserait le second a chaque
voyage. Le contenu, lui, reste ce que le journal a ecrit - donc en francais.

**Les dates et les heures sortent en ISO 8601**, jamais dans la mise en page du
journal : c'est la seule forme qu'une machine relit sans qu'on lui explique.
Sans fuseau horaire, en revanche : le journal ecrit l'heure de la machine et ne
dit pas laquelle, et coller un `Z` ou un decalage inventerait une precision que
personne n'a. `evening` est la **soiree** du but et non son jour de calendrier -
le but de 00h12 appartient a la soiree de la veille, exactement comme dans
[`--stats`](#les-formes-du-journal).

**La minute de jeu sort en trois champs** parce qu'elle repond a trois
questions : `minute` pour ranger un but dans un histogramme, `stoppage` pour
savoir s'il est tombe dans le temps additionnel, et `clock` pour ne pas jeter ce
que le journal a ecrit quand ce n'etait pas une minute de football. L'horloge
d'un match de hockey (`12:07`) n'est lisible ni comme un nombre ni comme rien :
`minute` et `stoppage` restent vides, `clock` la garde intacte.

### Ce que l'export dit de la VAR

**Toutes les lignes sortent, buts et annulations, et chacune porte
`standing`.** C'est l'arbitrage central de cette commande, et il se joue en deux
temps parce que la question est double.

Taire les annulations mentirait : la ligne `BUT ANNULE` a bien existe, elle a
son horodatage, et c'est elle qui explique pourquoi un score recule. Un export
qui l'efface rend un journal que personne n'a vecu.

Les melanger aux buts mentirait tout autant : un but repris par la VAR n'est pas
un but, et un tableur qui compterait ses lignes trouverait un total que ni
`--stats` ni `--top-scorers` ne rendent. D'ou `standing`, pose sur chaque
ligne : garder les lignes ou il vaut `true` donne **exactement** les buts que le
reste du programme compte, en une ligne de filtre.

Le rattachement est celui de `--top-scorers`, repris tel quel et pas recrit a
cote : une annulation retire le dernier but encore debout de la meme equipe dans
le meme match. Une annulation dont le but est tombe avant l'ouverture de la
fenetre n'est deduite de personne, et la sortie d'erreur le dit.

### Le CSV, et le JSON

Le CSV a **un en-tete, une seule forme de ligne, et la virgule pour
separateur**. La virgule plutot que le point-virgule qu'attend un tableur
francais : ce fichier est fait pour etre relu par un programme, et la virgule
est ce que tous supposent par defaut. Le point-virgule ne plairait qu'a une
locale, celle du lecteur, que le fichier ne peut pas connaitre au moment ou on
l'ecrit ; un tableur qui n'en veut pas le demande a l'import, un script a qui on
donne du point-virgule ne demande rien et lit tout de travers.

Une virgule, un guillemet ou un accent dans un nom d'equipe ne sont pas des cas
rares a plaindre - `Nice, OGC` est cite dans l'exemple plus haut. C'est le
travail du module `csv` de la bibliotheque standard, qui protege la case comme
il faut et que `csv.reader` rend intacte : **rien n'est echappe a la main ici**,
exactement pour cette raison. Le fichier est en **UTF-8** quoi qu'en dise la
console - une console Windows annonce volontiers du cp1252, et l'export
mourrait sur le premier accent s'il la croyait - et ses lignes se terminent par
un simple `\n`, parce que cette sortie part dans un tuyau aussi souvent que dans
un fichier.

Le JSON est **un seul grand tableau**, un objet par but, et non du JSON par
lignes. `--record` fait l'inverse, et pour une bonne raison : c'est un flux sans
fin, ecrit pendant qu'un match se joue, et une coupure au milieu doit laisser
tout ce qui precede lisible. L'export est exactement le contraire - une reponse
finie a une question posee - et l'arbitrage se retourne avec lui. Une fenetre du
journal tient en memoire sans y penser, donc `json.load(open(...))` en une ligne
suffit, ce que le JSON par lignes interdit. Et un fichier coupe en route ne
parse plus, ce qui est justement ce qu'on veut : en JSON par lignes il parserait
encore, en silence, avec les derniers buts en moins. Mieux vaut un export qui
refuse de s'ouvrir qu'un export qui ment de trois lignes.

### Deux sorties, et une seule porte les donnees

**Les donnees vont sur la sortie standard, et rien d'autre n'y va.** La fenetre
couverte, les totaux, les avertissements, le chemin du journal, la confirmation
des noms passes a `--teams` : tout part sur la **sortie d'erreur**. Une phrase
au milieu d'un CSV le rend illisible, et `butbutbut --export csv > buts.csv`
doit rendre un fichier, pas un fichier plus un commentaire. Dans un terminal,
les deux se melent et on lit tout ; des qu'on redirige, chacun va ou il doit.

```
$ butbutbut --export csv --week > buts.csv
butbutbut : export csv du dim. 31/08/2026 au dim. 07/09/2026
38 ligne(s) : 36 but(s) signale(s) dont 35 debout, 2 annulation(s).
Le champ 'standing' dit lesquels la VAR a repris.
Journal : /home/moi/.local/share/butbutbut/butbutbut.log
```

**Un journal absent, vide, ou une fenetre sans le moindre but restent des
reponses valides** : un tableau JSON vide, un CSV reduit a son en-tete, et
l'explication a cote. Un consommateur ne doit jamais avoir a distinguer "rien"
de "casse" - c'est exactement le genre de difference qui fait planter un script
un dimanche soir. Un tuyau referme en cours de route (`--export csv | head`) ne
remonte pas non plus : il se dit sur la sortie d'erreur, et la commande s'en va.

**L'export se fait hors reseau** : tout est deja dans le fichier. La meme
reserve que `--stats` et `--top-scorers`, et c'est la seule : nommer une equipe
fait d'abord verifier ce nom aupres du catalogue, et cette verification-la
demande le reseau. Sans `--teams` ni `--exclude-teams`, rien ne sort de la
machine.

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

**1313 tests**, sans reseau ni ecran : la source est simulee par un `opener`, le
cache d'ecussons par un `fetcher`, l'horloge par un `FakeClock`, et la geometrie
des cartes (empilement, debordement, troncature, place des ecussons) est
verifiee avec une police factice, donc sans tkinter. Le choix de couleur, lui,
est une fonction pure : son invariant est teste sur toutes les paires d'un jeu
de couleurs reelles - ce qui sort est toujours lisible, ou c'est la couleur de
la competition. L'enregistrement, lui, est verifie par un aller-retour complet :
un match joue en direct contre une source simulee, mis en boite, puis rejoue -
et les deux doivent rendre exactement la meme suite d'evenements.

Un seul programme du depot parle vraiment a ESPN, et il n'est pas dans cette
suite : c'est [le canari](#le-canari), `python tools/canari.py`.

### Ou elle tourne

L'[integration continue](https://github.com/boubou666/butbutbut/actions/workflows/ci.yml)
la rejoue sur Linux, Windows et macOS, en **Python 3.9, 3.12, 3.13 et 3.14**,
plus la **3.8** sous Linux seul. Ce sont les deux bouts qui comptent : la 3.8
tient le plancher annonce dans les prerequis, et la 3.14 est celle sur laquelle
le depot s'ecrit tous les jours - longtemps la seule a n'avoir jamais ete
essayee, ce qui est exactement la mauvaise a oublier. Les versions du milieu
(3.10, 3.11) sont tenues sans etre essayees : c'est un pari assume, ce qui
casse d'une version a l'autre casse rarement au milieu seul. Et le plancher ne
passe que sous Linux, parce qu'on lui demande de prouver que le code se lit
encore en 3.8, pas que les trois systemes divergent a cette version-la plutot
qu'aux autres.

Ce plancher, `3.8`, est ecrit a seize endroits. Neuf se nomment un par un :
`requires-python`, les deux badges, les deux listes de prerequis, et les quatre
garde-fous des installeurs - la comparaison qui refuse, et la phrase qui
l'explique. Les sept autres sont les en-tetes de `recipes/`, et ceux-la ne se
nomment pas : ils se **decouvrent**, sans quoi la recette ecrite demain
echapperait au controle - ce qui est precisement le defaut qu'on repare ici.

Le plafond, lui, n'est ecrit nulle part : il se deduit des classifiers du
paquet et de la matrice. Un test du depot les confronte tous, parce que c'est
exactement ainsi que la 3.14 avait pu manquer - rien ne reliait ces fichiers
entre eux, et tout restait vert.

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
