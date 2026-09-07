# L'API d'ESPN, telle qu'on l'a relevee

Tout butbutbut tient sur une seule source : le tableau de bord public d'ESPN.
Elle est gratuite, sans cle, sans inscription - et **sans contrat**. Personne
n'en publie la forme, personne ne previendra le jour ou un champ changera de
nom. Le code la lit donc de facon defensive, `tools/canari.py` la surveille
tous les jours, et ce fichier est le troisieme etage de la meme precaution :
**le contrat qu'on s'ecrit a soi-meme**, puisque le fournisseur n'en ecrit
pas.

Chaque chiffre ci-dessous a ete releve contre la vraie source, en production,
le **7 septembre 2026**. Rien n'est ici de memoire ni d'apres un billet de
blog : ce qui n'a pas pu etre observe est marque comme tel. L'annexe D donne
les commandes pour tout refaire.

> **Avertissement.** Aucune de ces adresses n'est documentee ni garantie par
> ESPN. Elles peuvent disparaitre du jour au lendemain, et l'usage qu'on en
> fait ici est celui d'un client de bureau qui releve quelques competitions
> toutes les vingt secondes. Ce n'est pas une invitation a en faire un
> service.

## Sommaire

- [1. Les hotes](#1-les-hotes)
- [2. Ce qui vaut pour toutes les requetes](#2-ce-qui-vaut-pour-toutes-les-requetes)
- [3. Le tableau de bord](#3-le-tableau-de-bord)
- [4. Les equipes](#4-les-equipes)
- [5. Le classement](#5-le-classement)
- [6. Le catalogue des competitions](#6-le-catalogue-des-competitions)
- [7. Le resume d'un match](#7-le-resume-dun-match)
- [8. L'API core](#8-lapi-core)
- [9. Les images](#9-les-images)
- [10. Ce que butbutbut lit vraiment](#10-ce-que-butbutbut-lit-vraiment)
- [11. Les pieges](#11-les-pieges)
- [12. Ce qu'on pourrait en tirer](#12-ce-quon-pourrait-en-tirer)
- [Annexe A - les actions du football](#annexe-a---les-actions-du-football)
- [Annexe B - les actions du rugby et du hockey](#annexe-b---les-actions-du-rugby-et-du-hockey)
- [Annexe C - les codes de competition](#annexe-c---les-codes-de-competition)
- [Annexe D - reverifier ce document](#annexe-d---reverifier-ce-document)

---

## 1. Les hotes

Quatre noms de domaine, et ils ne servent pas a la meme chose.

| Hote | Ce qu'il sert | Ce qu'on en lit |
| --- | --- | --- |
| `site.api.espn.com` | l'API du site : tableau de bord, equipes, classement, resume de match | **tout ce que butbutbut utilise** |
| `sports.core.api.espn.com` | l'API interne, hyperliee (`$ref`) et paginee | rien, mais elle repond a tout |
| `a.espncdn.com` | les images : ecussons, logos de competition, portraits | les ecussons |
| `site.web.api.espn.com` | le meme service, plus quelques vues du site web | rien : il sert deja tout ce qui precede |

Les deux premieres publient les memes matchs sous deux formes tres
differentes : `site.api` sert un gros objet complet en une requete, `core`
sert un graphe de references a suivre une par une. Pour un client qui releve
un score toutes les vingt secondes, la premiere gagne sans discussion - c'est
le sens de tout ce qui suit.

`site.web.api` merite une phrase, parce qu'on pourrait croire a une porte de
plus : c'est le meme service que `site.api`, aux memes chemins et a l'octet
pres (33 832 sur les deux pour la Ligue 1). Il ajoute une vue a lui,
`/apis/v2/scoreboard/header?sport=soccer&league=fra.1`, qui rend les memes
matchs en 37 ko, n'accepte **qu'une** competition a la fois et n'apporte donc
rien. Ses chemins `common/v3` (`/statistics`, `/leaders`), eux, rendent 404.

---

## 2. Ce qui vaut pour toutes les requetes

### La forme des URL

```
https://site.api.espn.com/apis/site/v2/sports/<sport>/<competition>/<ressource>
```

`<sport>` est le seul segment qui change d'un sport a l'autre : `soccer`,
`hockey`, `rugby`. `<competition>` est le code ESPN - un nom pointe au
football (`fra.1`), un mot au hockey (`nhl`), un **numero** au rugby
(`270559`). La forme de la reponse, elle, est presque la meme partout, et
c'est ce presque qui occupe la section 3.

Tout est en `GET`, tout rend du JSON UTF-8, rien ne demande de cle, aucun
quota n'est annonce. Douze requetes lancees coup sur coup en 0,9 s ont toutes
rendu 200 : il n'y a pas de limite visible a l'echelle d'un client de bureau.
Ce n'est pas une raison pour marteler - le daemon releve toutes les vingt
secondes, et la source elle-meme se declare cachable une a soixante secondes.

### Les en-tetes qu'on envoie

Ceux de `espn.headers()`, et il y en a un qui n'est pas decoratif :

```
User-Agent: butbutbut/1.9.0 (+https://github.com/boubou666/butbutbut)
Accept: application/json
Accept-Language: fr,en;q=0.8
Cache-Control: no-cache
```

### Le `User-Agent` est filtre, et c'est un piege

Devant l'API se tient un Akamai qui refuse certains clients. Le refus est un
**403 en HTML** (`Server: AkamaiGHost`, `<TITLE>Access Denied</TITLE>`), pas
un JSON d'erreur : un lecteur qui attend du JSON verra une reponse illisible
plutot qu'un refus. Releve sur la meme URL, a la suite :

| `User-Agent` | Reponse |
| --- | --- |
| `butbutbut/1.9.0 (+https://github.com/boubou666/butbutbut)` | **200** |
| `Python-urllib/3.14` (le defaut de la stdlib) | 200 |
| `curl/8.0` | 200 |
| `butbutbut/1.9.0` (le meme, sans l'URL) | **403** |
| `butbutbut`, `foo/1.0`, `x` | 403 |
| `Mozilla/5.0` | 403 |
| une chaine Chrome complete et credible | 403 |

Le filtre n'est donc pas "un vrai navigateur passe" - c'est plutot l'inverse :
**se faire passer pour un navigateur est exactement ce qui fait refuser**. Un
agent qui se nomme et donne un moyen de le joindre passe. C'est la raison pour
laquelle l'en-tete du projet porte l'URL du depot, et c'est une ligne a ne pas
raccourcir en croyant faire propre.

### La compression, elle, est gratuite

L'API repond `Vary: Accept-Encoding` et honore `Accept-Encoding: gzip`. Sur le
tableau de bord de la Ligue 1 : **33 832 octets sans, 4 145 avec**, soit huit
fois moins ; sur un tour complet de `--leagues all`, 1 355 ko contre 148 ko.
Rien a decoder a la main, `gzip.decompress` suffit. **butbutbut le demande
depuis la 1.10.0** : c'est ce releve qui a decide de la question, faute de
pouvoir faire mieux (voir juste en dessous).

### Le cache, et ce qu'il n'y a pas

| En-tete | Valeur observee |
| --- | --- |
| `Cache-Control` | `max-age=1` a `max-age=10` sur le tableau de bord, `max-age=63` sur `/teams`, `max-age=900` sur l'API core |
| `ETag` | **absent** |
| `Last-Modified` | **absent** |
| `Vary` | `Accept-Encoding` |
| `Access-Control-Allow-Origin` | `*` |

L'absence des deux du milieu tranche une question qui revenait : **les
requetes conditionnelles sont impossibles**. Sans `ETag` ni `Last-Modified`,
il n'y a rien a poser dans un `If-None-Match` ou un `If-Modified-Since`, et
les deux essais rendent bien un 200 complet. On ne peut donc pas economiser
les 36 requetes par tour de `--leagues all` de cette facon-la ; on peut, en
revanche, les alleger de huit dixiemes avec gzip.

### Les erreurs

| Code | Quand | Corps |
| --- | --- | --- |
| 400 | competition inconnue, sport inconnu, `dates` mal forme | `{"code":400,"message":"Failed to get events endpoint."}` |
| 400 | classement d'une competition inconnue | `{"code":400,"message":"Unable to retrieve any standings information for zzz.9"}` |
| 400 | equipe inconnue | `{"code":400,"message":"Failed to get league teams summary"}` |
| 404 | match inconnu sur `/summary` | `{"code":404,"message":"Error invoking GET: ...pvt/v2/..."}` |
| 403 | `User-Agent` filtre | du **HTML**, pas du JSON |

A noter : une competition inconnue rend **400 et non 404**, et le message ne
distingue pas "ce code n'existe pas" de "cette adresse est mal formee". Le 404
du resume, lui, laisse fuir l'adresse interne (`sports.core.api.espn.pvt`), ce
qui dit assez que ces messages ne sont ecrits pour personne.

Une competition connue mais sans match du jour rend, elle, **200 avec
`"events": []`** : une intersaison n'est pas une erreur, et le code ne doit pas
la traiter comme telle.

### `lang` et `region` : deux tiers de deception

Les endpoints acceptent `?lang=xx&region=yy`. La question valait d'etre posee -
si la source savait traduire, `i18n.py` en porterait moins. Releve sur
`soccer/ger.1` :

| Parametres | Nom de competition | Etat du match |
| --- | --- | --- |
| (aucun) | German Bundesliga | Full Time |
| `lang=es&region=es` | **Bundesliga** | **Tiempo Completo** |
| `lang=pt&region=br` | **Bundesliga** | **Final da Partida** |
| `lang=nl&region=nl` | Bundesliga | Full Time |
| `lang=fr&region=fr` | German Bundesliga | Full Time |
| `lang=it&region=it`, `lang=de&region=de`, `lang=ar&region=ae` | German Bundesliga | Full Time |
| `lang=zz&region=zz` | German Bundesliga | Full Time |

Trois lecons. **L'espagnol et le portugais sont vraiment traduits** - noms de
competition et libelles d'etat. **Le francais ne l'est pas**, pas plus que
l'allemand ou l'italien : demander `lang=fr` ne coute rien et ne rapporte
rien. Et **les noms d'equipes ne bougent jamais**, dans aucune langue, ce qui
otait de toute facon l'interet principal : c'est sur les libelles d'equipe que
travaille `teams.py`, et ils seraient restes a traduire.

Un `lang` inconnu n'est pas une erreur : il est ignore.

---

## 3. Le tableau de bord

```
https://site.api.espn.com/apis/site/v2/sports/<sport>/<competition>/scoreboard
```

C'est l'endpoint qui fait tourner le programme : un appel par competition et
par tour de boucle, et tout ce qui s'affiche sur une carte en sort.

### Les parametres

Verifie sur `soccer/eng.1`, le 7 septembre 2026 :

| Parametre | Effet | Verifie |
| --- | --- | --- |
| `dates=AAAAMMJJ` | ce jour-la | `?dates=20260906` -> 2 matchs |
| `dates=AAAAMMJJ-AAAAMMJJ` | l'intervalle, **bornes comprises** | `?dates=20260901-20260930` -> 30 matchs |
| `dates=AAAAMM` | le mois entier | `?dates=202609` -> 30 matchs |
| `dates=AAAA` | l'annee de saison entiere | `?dates=2026` -> 100 matchs (voir `limit`) |
| `limit=N` | le nombre maximum de matchs rendus | **defaut 100** |
| `lang`, `region` | voir plus haut | espagnol et portugais seulement |
| `season`, `seasontype`, `week` | **sans effet** au football | `?week=3` rend 0 match, `?season=2025` rend la journee en cours |

Sans `dates`, l'endpoint ne sert que **la journee en cours**. C'est assez pour
guetter les buts, pas pour dire quand tombe le prochain match : c'est
l'intervalle qui permet a `--next` de couvrir une semaine en une requete par
competition la ou un jour a la fois en couterait sept.

**Le `limit` par defaut est un piege silencieux.** `?dates=2026` sur la
Premier League rend 100 matchs sans le dire ; le meme appel avec `&limit=500`
en rend 374, et un intervalle explicite (`?dates=20260801-20270601&limit=1000`)
rend les 380 du calendrier - l'annee de saison ne couvre pas exactement le
meme domaine. Rien dans la reponse ne signale la troncature : pas de `next`,
pas de compteur total. Un client qui balaie large doit poser `limit`
lui-meme.

### La forme generale

```json
{
  "leagues": [ { "id": "710", "name": "French Ligue 1", "abbreviation": "Ligue 1",
                 "slug": "fra.1", "season": {}, "logos": [], "calendar": [] } ],
  "season": { "type": 1, "year": 2026 },
  "day": { "date": "2026-09-06" },
  "events": [],
  "provider": {}
}
```

`leagues[0]` porte le nom officiel de la competition : c'est de la que
`--leagues gre.1` tire son vrai nom des le premier releve
(`League.adopt_name`). `leagues[0].calendar` est la liste des journees de la
saison, en dates ISO - de quoi savoir a l'avance quels jours valent une
requete.

### Un match : `events[]`

| Champ | Exemple | Remarque |
| --- | --- | --- |
| `id` | `"401876467"` | l'identifiant du match, stable |
| `uid` | `"s:600~l:710~e:401876467"` | sport, competition, match |
| `date` | `"2026-09-06T13:00Z"` | UTC, **parfois sans les secondes** |
| `name` | `"Strasbourg at Troyes"` | toujours en anglais |
| `shortName` | `"STR @ TRY"` | |
| `competitions` | `[ ... ]` | **une seule** en pratique |
| `status`, `venue`, `links` | | repetes ou completes dans `competitions[0]` |

Le detail vit dans `competitions[0]`, jamais ailleurs : `competitors`,
`details`, `status`, `odds`, `broadcasts`, `attendance`, `notes`. Le code lit
`competitions[0]` et retombe sur l'evenement pour la date et l'etat, parce que
les deux niveaux ne se remplissent pas toujours ensemble.

### L'etat : `competitions[0].status`

```json
{ "clock": 5400.0, "displayClock": "90'+6'", "period": 2,
  "type": { "id": "28", "name": "STATUS_FULL_TIME", "state": "post",
            "completed": true, "description": "Full Time",
            "detail": "FT", "shortDetail": "FT" } }
```

`state` ne prend que trois valeurs - `pre`, `in`, `post` - et c'est le socle de
`espn.phase_of()`. Le detail est dans `type.name`, et il n'est pas le meme d'un
sport a l'autre. Releve sur environ 6 800 matchs :

| Sport | `type.id` | `type.name` | `state` | `description` |
| --- | --- | --- | --- | --- |
| football | 1 | `STATUS_SCHEDULED` | `pre` | Scheduled |
| football | 28 | `STATUS_FULL_TIME` | `post` | Full Time |
| football | 45 | `STATUS_FINAL_AET` | `post` | Final Score - After Extra Time |
| football | 47 | `STATUS_FINAL_PEN` | `post` | Final Score - After Penalties |
| football | 6 | `STATUS_POSTPONED` | `post` | Postponed |
| football | 8 | `STATUS_SUSPENDED` | `post` | Suspended |
| football | 27 | `STATUS_ABANDONED` | `post` | Abandoned |
| hockey | 3 | `STATUS_FINAL` | `post` | Final |
| hockey | 6 | `STATUS_POSTPONED` | `post` | Postponed |
| rugby | 0 | `STATUS_TBD` | `pre` | TBD |
| rugby | 1 | `STATUS_SCHEDULED` | `pre` | Scheduled |
| rugby | 3 | `STATUS_FINAL` | `post` | FT |

Deux choses sautent aux yeux. **Le football et les deux autres ne nomment pas
la fin de la meme facon** (`STATUS_FULL_TIME` contre `STATUS_FINAL`), d'ou la
lecture par `state` plutot que par nom. Et **un match reporte, suspendu ou
abandonne est annonce `post`**, comme un match termine : sans le nom, le
programme afficherait une carte de fin de match pour une rencontre qui n'a
jamais commence. C'est tout l'objet de la liste `_STOPPED` de `espn.py`.

Les etats **en cours de jeu n'ont pas pu etre observes** au moment du releve :
les 218 competitions de football ont ete balayees, pas un match ne se jouait.
Les noms que le code reconnait viennent de releves anterieurs, et la liste est
volontairement large parce qu'un nom inconnu laisse simplement le match "en
cours" - donc aucune carte, jamais une carte fausse : `STATUS_FIRST_HALF`,
`STATUS_HALFTIME`, `STATUS_SECOND_HALF`, `STATUS_EXTRA_TIME_HALFTIME`,
`STATUS_SHOOTOUT`, `STATUS_IN_PROGRESS`, `STATUS_INTERMISSION`,
`STATUS_END_PERIOD`, `STATUS_END_OF_PERIOD`.

`displayClock` porte la minute de jeu telle qu'on l'affiche : `"67'"`,
`"90'+6'"` au football - apostrophe des **deux** cotes du plus - et `"12:34"`
au hockey. Deux formes qui ne se lisent pas avec le meme lecteur.

### Les deux equipes : `competitors[]`

Toujours deux entrees, distinguees par `homeAway` (`"home"` / `"away"`), et
**pas necessairement dans cet ordre** : c'est le champ qui fait foi, pas la
position.

| Champ | Exemple | Remarque |
| --- | --- | --- |
| `homeAway` | `"home"` | le seul moyen sur de savoir qui recoit |
| `score` | `"2"` | une **chaine**, pas un entier |
| `winner` | `false` | absent avant la fin |
| `form` | `"LWDLW"` | les cinq derniers matchs, football seulement |
| `records` | `[{"summary": "1-1-1"}]` | |
| `statistics` | possession, tirs, corners... | football seulement, et jamais avant le coup d'envoi |
| `team` | l'objet ci-dessous | |

L'equipe elle-meme :

| Champ | Exemple | Remarque |
| --- | --- | --- |
| `id` | `"170"` | l'identifiant ESPN, stable |
| `displayName` | `"Troyes"` | le nom lisible |
| `shortDisplayName`, `name`, `location`, `abbreviation` | `"TRY"` | quatre ecritures de plus |
| `color`, `alternateColor` | `"0000bf"` | **sans le diese**, et parfois absents |
| `logo` | `.../teamlogos/soccer/500/170.png` | au hockey : `.../nhl/500/scoreboard/col.png` |
| `logos` | tableau `{href, rel}` | quand `logo` manque |

Le football donne `alternateColor`, le hockey non ; la couleur est parfois une
chaine vide. Rien la-dedans n'est garanti, et `crests.py` sait retomber sur la
couleur de la competition.

### Les actions : `competitions[0].details`

C'est ici que les trois sports divergent vraiment, et c'est la seule vraie
difference de lecture du projet.

**Le football** publie une entree par action marquante, portee par des
**drapeaux** :

```json
{ "type": { "id": "98", "text": "Penalty - Scored" },
  "clock": { "value": 5133.0, "displayValue": "86'" },
  "team": { "id": "6851" },
  "scoreValue": 1,
  "scoringPlay": true, "redCard": false, "yellowCard": false,
  "penaltyKick": true, "ownGoal": false, "shootout": false,
  "athletesInvolved": [ { "id": "271137", "shortName": "L. Sinayoko",
                          "displayName": "Lassine Sinayoko", "jersey": "9",
                          "headshot": "...", "team": { "id": "6851" } } ] }
```

Les drapeaux s'excluent, sauf `penaltyKick` et `shootout` qui accompagnent un
`scoringPlay`. Un tir au but de seance se reconnait a `shootout: true` - et il
porte le `type.id` **104** la ou un penalty de jeu porte le **98**. La table
complete des `type.id` est en
[annexe A](#annexe-a---les-actions-du-football).

**Le rugby** publie le meme tableau, **sans un seul drapeau** :

```json
{ "type": { "id": "1", "text": "try" },
  "clock": { "value": 434.0, "displayValue": "8'" },
  "team": { "id": "25986" },
  "athletesInvolved": [ { "id": "296203", "shortName": "G. Villiere",
                          "position": "W" } ] }
```

Ni `scoringPlay`, ni `scoreValue`, ni `ownGoal` : **quatre cles en tout**, et
c'est `type.id` qui dit ce qui s'est passe. Lu avec le lecteur du football, un
match de rugby n'aurait aucune action du tout - c'est exactement pour ca que
`_rugby_details()` existe. Table en
[annexe B](#annexe-b---les-actions-du-rugby-et-du-hockey).

**Le hockey ne publie rien.** Sur 798 matchs termines releves, `details` est
absent a chaque fois - pas vide : absent. On a le score, l'horloge et la
periode, jamais le buteur. La carte le dit en ne disant rien. (Les buteurs du
hockey existent pourtant ailleurs : voir la section 7.)

---

## 4. Les equipes

```
https://site.api.espn.com/apis/site/v2/sports/<sport>/<competition>/teams
https://site.api.espn.com/apis/site/v2/sports/<sport>/<competition>/teams/<id>
```

Sert a valider ce qu'on tape dans `--teams` et a repondre a `--list-teams`. La
reponse est enfouie de trois niveaux, et c'est le seul endpoint du lot a
l'etre :

```
sports[0].leagues[0].teams[].team
```

L'objet `team` est celui du tableau de bord, avec `logos` en plus. Quelques
comptes releves : `fra.1` 18, `eng.1` 20, `nhl` 32, `rugby/270559` 14,
`uefa.champions` 36, `eng.fa` **124** - une coupe ouverte aux divisions
inferieures rend bien tout son monde. `?limit=` n'y change rien : la liste est
complete d'office.

Une competition qui ne repond pas rend une liste vide plutot qu'une erreur :
on ne bloque pas le demarrage pour un catalogue d'equipes.

---

## 5. Le classement

```
https://site.api.espn.com/apis/v2/sports/<sport>/<competition>/standings
```

**`apis/v2`, et non `apis/site/v2`.** La mauvaise adresse existe pourtant et
repond 200 - avec un objet quasi vide (`{"fullViewLink": ...}`), ce qui
ressemble a une intersaison alors que c'est juste la mauvaise porte. C'est la
faute qu'on ne veut pas refaire, et elle est notee dans le code a l'endroit ou
elle se commet.

### La forme

```json
{ "id": "710", "name": "French Ligue 1", "abbreviation": "FRA.1",
  "season": { "year": 2026, "displayName": "2026-27 French Ligue 1" },
  "seasons": [],
  "children": [
    { "name": "French Ligue 1 2026-27",
      "standings": { "seasonDisplayName": "2026-27 French Ligue 1 Standings",
                     "entries": [] } } ] }
```

`children` est **toujours une liste**, meme a un seul element, et c'est ce qui
permet de traiter un championnat et une phase de poules avec le meme code :

| Competition | `children` |
| --- | --- |
| `soccer/fra.1` | 1 (le championnat) |
| `hockey/nhl` | 2 (les conferences Est et Ouest) |
| `soccer/fifa.world` | 12 (les groupes) |
| `soccer/eng.fa` | **0** (une coupe n'a pas de classement) |

Une ligne, `children[].standings.entries[]` :

```json
{ "team": { "id": "160", "displayName": "Paris Saint-Germain" },
  "note": { "color": "#81D6AC", "description": "Champions League", "rank": 1 },
  "stats": [ { "name": "gamesPlayed", "type": "gamesplayed",
               "displayName": "Games Played", "abbreviation": "GP",
               "value": 3.0, "displayValue": "3" } ] }
```

Trois choses a savoir sur `stats`.

**C'est une liste plate, pas un objet** : il faut l'indexer soi-meme. Chaque
statistique porte **deux noms** - `type` en minuscules (`"gamesplayed"`) et
`name` en camel (`"gamesPlayed"`) - et les deux ne concordent pas d'un sport a
l'autre. Le rugby compte ses victoires sous `gamesWon`, le football sous
`wins` : c'est pour ca que `_stats_of()` range sous les deux.

**`displayValue` porte le signe, `value` non** : une difference de buts de +4
arrive en `4.0` d'un cote et `"+4"` de l'autre. C'est la chaine qu'on affiche.

**Le rang n'est pas toujours la.** Le football et le rugby publient `rank`, le
hockey n'a que `playoffSeed`. Et l'ordre de la liste ne remplace pas le rang :
un championnat arrive trie, mais un groupe de Coupe du monde arrive dans le
desordre et une conference NHL commence a sa quatrieme tete de serie.

Les statistiques disponibles, par sport (releve) :

| Sport | `stats[].name` |
| --- | --- |
| football | `gamesPlayed`, `wins`, `ties`, `losses`, `points`, `pointsFor`, `pointsAgainst`, `pointDifferential`, `ppg`, `rank`, `rankChange`, `deductions`, `advanced`, `overall` |
| hockey | `gamesPlayed`, `wins`, `losses`, `otLosses`, `overtimeLosses`, `overtimeWins`, `regWins`, `regLosses`, `shootoutWins`, `shootoutLosses`, `points`, `pointsFor`, `pointsAgainst`, `pointDifferential`, `playoffSeed`, `streak`, `clincher`, `gamesBehind`, `Home`, `Road`, `Last Ten Games`, `vs. Div.` |
| rugby | `gamesPlayed`, `gamesWon`, `gamesDrawn`, `gamesLost`, `points`, `pointsFor`, `pointsAgainst`, `pointsDifference`, `bonusPoints`, `bonusPointsTry`, `bonusPointsLosing`, `triesFor`, `triesAgainst`, `triesDifference`, `rank`, `playoffSeed`, `streak`, `winPercent` |

Trois sports, trois facons de compter : le hockey n'a pas de match nul mais
compte les defaites en prolongation, le rugby ajoute ses points de bonus et
ses essais, le football n'a ni l'un ni l'autre. Fabriquer une colonne de nuls
pour le hockey serait inventer un zero.

`note` habille la ligne d'une zone de qualification et de sa couleur
(`"Champions League"`, `"Relegation"`). De quoi peindre un tableau ; on ne le
lit pas dans un terminal de 80 colonnes.

### Les parametres

| Parametre | Effet |
| --- | --- |
| `season=AAAA` | le classement d'une saison passee - `?season=2025` repond |
| `level=N` | la profondeur des groupes ; `level=1` rend un objet **sans `children`** |

La liste des saisons disponibles est dans la reponse elle-meme, sous
`seasons[]`, chacune avec ses `types[].hasStandings` : de quoi savoir ce qu'on
peut demander avant de le demander.

---

## 6. Le catalogue des competitions

Deux facons de savoir ce qui existe.

```
https://site.api.espn.com/apis/site/v2/leagues/dropdown?sport=soccer&limit=1000
```

Rend la liste complete des competitions d'un sport, avec pour chacune son
`slug`, son `name`, ses `logos` et - precieux - **`hasStandings`**. Au moment
du releve : **218** competitions de football, **19** de rugby, **6** de hockey.
La liste entiere est en
[annexe C](#annexe-c---les-codes-de-competition).

```
https://sports.core.api.espn.com/v2/sports
```

Rend les 17 sports d'ESPN : `australian-football`, `baseball`, `basketball`,
`cricket`, `field-hockey`, `football`, `golf`, `hockey`, `lacrosse`, `mma`,
`racing`, `rugby`, `rugby-league`, `soccer`, `tennis`, `volleyball`,
`water-polo`.

butbutbut n'en ouvre que trois, et le README dit pourquoi : ce n'est pas une
limite technique, c'est le modele du programme. Un panier toutes les trente
secondes ne se notifie pas.

---

## 7. Le resume d'un match

```
https://site.api.espn.com/apis/site/v2/sports/<sport>/<competition>/summary?event=<id>
```

Une requete par match, et une reponse lourde : `boxscore`, `rosters`,
`leaders`, `odds`, `videos`, `news`, `standings`, `commentary`... 430 ko pour
un match de football, 450 ko pour un match de NHL. Un client qui suit 36
competitions ne peut pas se payer ca par match et par tour - butbutbut ne
l'appelle donc **qu'apres un but de hockey, et que pour le match concerne**,
soit quelques fois par soiree. C'est le seul endroit ou il pousse cette porte,
et c'est parce qu'il y a dedans **ce que le tableau de bord ne donne pas**.

Au football, `keyEvents[]` (28 entrees sur le match releve) reprend les actions
du tableau de bord et y ajoute les temps forts - coup d'envoi, mi-temps,
remplacements - avec un `type.type` lisible (`"kickoff"`). Et `commentary[]`
(127 entrees) est le fil minute par minute.

**Au hockey, `plays[]` porte les buteurs que le tableau de bord n'a pas.** Sur
un match releve, 302 actions dont 14 buts, chacun ainsi :

```json
{ "type": { "id": "505", "text": "Goal" },
  "text": "Max Sasson Goal (12) Snap Shot, assists: Filip Hronek (35), Zeev Buium (19)",
  "scoringPlay": true, "scoreValue": 1,
  "period": { "number": 1, "displayValue": "1st" },
  "clock": { "displayValue": "0:29" },
  "team": { "id": "22" },
  "participants": [
    { "type": "scorer",   "athlete": { "id": "4996099", "shortName": "M. Sasson" }, "ytdGoals": 12 },
    { "type": "assister", "athlete": { "id": "4063607", "shortName": "F. Hronek" }, "ytdAssists": 35 } ] }
```

Donc : "le hockey n'a pas de buteur" est vrai **du tableau de bord**, et faux
de la source entiere. Ce qui manquait n'etait pas la donnee, c'etait un budget
reseau ; il tient dans une requete par but. Voir la section 12.

Trois choses a savoir avant de lire `plays[]` :

- **le role est dans `participants[].type`**, pas dans l'ordre du tableau. Un
  but nomme jusqu'a trois joueurs, et le premier de la liste n'est pas
  necessairement le buteur ;
- **l'horloge repart a zero a chaque tiers-temps.** `clock.displayValue` seul
  ne situe rien : il faut `period.number` avec. `period.displayValue`, lui, est
  en anglais ("1st", "OT") et ne se pose donc pas tel quel sur une carte ;
- **la fusillade n'y est pas.** Le but vainqueur figure au score du match sans
  qu'aucune action ne lui corresponde : un lecteur qui compte les buts publies
  en trouvera un de moins que le tableau de bord.

---

## 8. L'API core

```
https://sports.core.api.espn.com/v2/sports/<sport>/leagues/<competition>/...
```

L'API interne, et elle repond a a peu pres tout : `/seasons/2026/teams`,
`/events`, `/events/<id>`, `/events/<id>/competitions/<id>/plays`, `/groups`,
`/rankings`, `/notes`. Deux traits qui la distinguent :

- **elle est hyperliee** : une liste ne contient pas les objets mais des
  `{"$ref": "http://..."}` a suivre un par un. Compter 18 requetes pour les
  18 clubs d'une Ligue 1 ;
- **elle est paginee** : `count`, `pageIndex`, `pageSize`, `pageCount`,
  `items`, avec `?limit=` et `?page=`.

Elle se cache mieux (`max-age=900, stale-while-revalidate=7200`) mais coute
plus cher a l'usage : les 302 actions du match de NHL ci-dessus pesent 663 ko
ici contre 450 ko par `/summary`. Pour un client de bureau, `site.api` reste la
bonne porte ; `core` sert quand on cherche quelque chose que le tableau de bord
ne publie pas.

Detail utile pour deviner une adresse : les messages d'erreur de `site.api`
laissent parfois fuir l'appel `core` correspondant, hote interne compris.

---

## 9. Les images

Tout est sur `a.espncdn.com`, en PNG, sans authentification. Les URL arrivent
normalement dans la charge utile (`team.logo`, `athlete.headshot`) ; les motifs
ci-dessous ne servent qu'a fabriquer une URL a partir d'un identifiant, ce que
fait `espn.logo_url()` pour les cartes de demonstration.

| Motif | Exemple | Verifie |
| --- | --- | --- |
| `/i/teamlogos/soccer/500/<id>.png` | `.../soccer/500/170.png` | 200, 500x500 |
| `/i/teamlogos/soccer/500-dark/<id>.png` | | 200, variante sombre |
| `/i/teamlogos/nhl/500/<id>.png` | `.../nhl/500/1.png` | 200 - **le numero marche** |
| `/i/teamlogos/nhl/500/<abbrev>.png` | `.../nhl/500/bos.png` | 200, autre rendition |
| `/i/teamlogos/nhl/500/scoreboard/<abbrev>.png` | | c'est celle que sert la charge utile |
| `/i/teamlogos/rugby/teams/500/<id>.png` | `.../500/25986.png` | 200 |
| `/i/leaguelogos/soccer/500/<id>.png` | `.../500/9.png` | 200 |
| `/i/headshots/<sport>/players/full/<id>.png` | | 200 **quand le joueur en a un** |
| n'importe quoi d'inconnu | | 404 franc |

Le hockey merite une precision : le code range ses ecussons sous le numero
d'equipe, et une note du depot doutait que ce soit la bonne cle. Verification
faite, **les deux formes existent** et rendent bien le bon club -
`nhl/500/1.png` est Boston, `nhl/500/22.png` est Vancouver - simplement ce
n'est pas la meme image que celle du tableau de bord, qui passe par
`scoreboard/<abbrev>`. Tous les portraits, en revanche, n'existent pas : un
joueur sans photo rend 404, et la charge utile omet alors le champ.

**Le redimensionneur.** ESPN sert aussi les images par un combineur qui
redimensionne cote serveur :

```
https://a.espncdn.com/combiner/i?img=/i/teamlogos/soccer/500/170.png&h=80&w=80
```

Le meme ecusson pese **44,7 ko en 500x500 et 6,0 ko en 80x80** - et la carte ne
l'affiche jamais plus grand que quelques dizaines de pixels. `&scale=crop`
recadre.

C'est ce que `crests.py` demande desormais : la taille suit `--scale` sur une
echelle de trois barreaux (64, 128, 256), et au-dela c'est l'original qui
repart. Un chemin qui n'existe pas rend **404 franc** a travers le combineur
aussi - il n'y a pas d'image de remplacement a distinguer d'une vraie.

---

## 10. Ce que butbutbut lit vraiment

De tout ce qui precede, le programme ne lit qu'une poignee de champs. Les
voici, avec l'endroit qui les lit - c'est aussi la liste que surveille
`tools/canari.py`.

| Champ ESPN | Lu par | Sert a |
| --- | --- | --- |
| `events[].id` | `espn.parse` | l'identite d'un match |
| `events[].competitions[0]` | `espn.parse` | tout le reste |
| `competitors[].homeAway` | `espn.parse` | qui recoit |
| `competitors[].score` | `espn.parse` | **le score, donc le but** |
| `competitors[].team.displayName` / `shortDisplayName` | `_team_name` | le nom sur la carte |
| `competitors[].team.name` / `location` / `abbreviation` | `team_names` | le rapprochement de `--teams` |
| `competitors[].team.color` / `alternateColor` | `team_colors` | la couleur du club |
| `competitors[].team.logo` / `logos[].href` | `team_logo` | l'ecusson |
| `status.type.state` | `phase_of` | en cours, a venir, termine |
| `status.type.name` | `phase_of` | mi-temps, report, abandon |
| `status.type.shortDetail` / `detail` / `description` | `espn.parse` | la ligne d'etat |
| `status.displayClock` | `espn.parse` | la minute de jeu |
| `competitions[0].date` | `_parse_date` | l'heure du coup d'envoi |
| `details[].type.id` / `text` | `_soccer_details`, `_rugby_details` | la nature de l'action |
| `details[].scoringPlay` / `redCard` / `ownGoal` / `penaltyKick` / `shootout` | `_soccer_details` | l'habillage de la carte |
| `details[].clock.displayValue` | `_detail_common` | la minute du but |
| `details[].athletesInvolved[0].shortName` | `_detail_common` | le buteur |
| `leagues[0].name` / `abbreviation` | `espn.parse` | le nom d'une competition ouverte a la volee |
| `children[].standings.entries[].stats[]` | `_stats_of` | le classement |
| `plays[].type.id` / `text` | `summary_goals` | reconnaitre un but au hockey |
| `plays[].team.id` | `summary_goals` | de quel camp vient le but |
| `plays[].clock.displayValue` / `period.number` | `_summary_minute` | quand |
| `plays[].participants[].type` | `_summary_participants` | buteur ou passeur |
| `plays[].participants[].athlete.shortName` | `_summary_participants` | **le nom** |

Les cinq dernieres lignes ne viennent pas du tableau de bord mais du resume
d'un match (section 7), et ne sont lues que pour le hockey, qu'apres un but, et
que pour le match qui vient de l'encaisser.

Et surtout, ce qu'il **ne** lit pas : le score n'est jamais deduit des actions.
Un score qui monte est un but, meme si `details` n'a pas encore rattrape -
c'est ce qui fait que le hockey, qui ne publie aucune action, est suivi aussi
bien que le reste.

---

## 11. Les pieges

Ceux qui ont deja coute quelque chose, ou qui le couteraient.

1. **`apis/v2` pour le classement, `apis/site/v2` pour le reste.** La mauvaise
   adresse repond 200 avec un objet vide : une panne muette.
2. **`limit` vaut 100 par defaut** sur le tableau de bord, et la troncature ne
   se signale nulle part.
3. **Une competition inconnue rend 400, pas 404**, et une intersaison rend 200
   avec `events: []`. Ne pas confondre les deux.
4. **Le `User-Agent` peut faire refuser la requete**, en HTML, par Akamai. Un
   403 n'est pas une competition qui n'existe pas.
5. **`score` est une chaine.**
6. **Les couleurs n'ont pas de diese** et sont parfois vides.
7. **`details` n'existe pas au hockey** - les buteurs y vivent dans le resume
   du match, sous `plays[]` - et n'a **aucun drapeau** au rugby.
8. **`athletesInvolved` peut etre vide** : un but sans buteur publie est normal
   pendant quelques secondes.
9. **La date arrive parfois sans les secondes** (`2026-09-06T18:45Z`), ce qui
   fait echouer un `strptime` trop strict.
10. **La minute des arrets de jeu s'ecrit `90'+6'`**, apostrophe des deux cotes
    du plus. Un lecteur qui n'accepte que `90+6'` jette la moitie des buts de
    fin de match sans rien casser - c'est arrive.
11. **L'ordre de `children[].standings.entries` ne vaut pas classement**, et le
    hockey n'a pas de `rank` du tout.
12. **Pas d'`ETag`, pas de `Last-Modified`** : les requetes conditionnelles
    sont hors de portee.

---

## 12. Ce qu'on pourrait en tirer

Quatre pistes que ce releve ouvre, avec leur arbitrage. Chacune dit ou elle en
est.

**Demander gzip - fait.** Huit fois moins d'octets sur le fil, pour une ligne
dans `headers()`, une decompression dans `download()` et zero dependance
(`gzip` est dans la stdlib). C'etait la seule economie de trafic disponible,
puisque les requetes conditionnelles ne le sont pas ; elle est en place depuis
la 1.10.0. Le piege d'implementation valait le detour : on reconnait un flux
compresse a ses **deux premiers octets** et non a l'en-tete
`Content-Encoding`, parce qu'un proxy qui decompresse en chemin ne pense pas
toujours a retirer l'en-tete - et parce qu'une reponse en clair traverse alors
le meme chemin sans cas particulier.

**Les buteurs du hockey - fait.** Ils vivent dans `/summary?event=<id>`, sous
`plays[].participants[].type == "scorer"`, et le cout etait le probleme : 450
ko par match. La regle retenue est celle qu'annoncait ce paragraphe - on
n'appelle le resume **qu'apres un but detecte** et **que pour le match
concerne**, soit six a sept fois par match et par soiree, jamais a chaque tour
de boucle. La carte de hockey a donc son buteur et ses passeurs.

Deux arbitrages ont ete tranches en chemin, et ils valent d'etre notes ici :

- **la carte attend, mais pas longtemps.** Le resume est la seule requete du
  programme qui se glisse entre un but detecte et la carte qui l'annonce : elle
  a donc son propre plafond, 1,5 s au lieu des 8 s d'un tableau de bord. Passe
  ce delai, la carte sort sans nom. Le fil de fond de `crests.py` ne convenait
  pas : un ecusson arrive en retard sert la carte suivante, le nom du buteur du
  1-0 n'habillera jamais que la carte du 1-0 ;
- **le nom se choisit par le rang, pas par la fraicheur.** Le resume est lu au
  moment du but, et l'on y prend le n-ieme but de l'equipe qui vient de passer
  a n - et seulement si le resume en compte exactement autant que le tableau de
  bord. Un resume en retard d'un releve, ou une fusillade dont le but vainqueur
  n'est publie nulle part, donnent alors une carte sans nom plutot qu'une carte
  qui affiche le buteur precedent.

**Le combineur d'images - fait.** `combiner/i?img=...&h=64&w=64` divise par
sept le poids d'un ecusson, que `crests.py` telechargeait en 500x500 pour
l'afficher tout petit : cinq ecussons mesures passent de 185 031 a 25 071
octets. La reserve - c'est une URL qu'on fabrique, la ou le projet prefere
celle que la source annonce - est levee et non contournee. On ne fabrique que
ce qu'on sait manipuler, un chemin d'image d'`espncdn.com` et rien d'autre
(`crests.combiner_url`), et `crests.Cache.fetch_now` essaie l'URL fabriquee
d'abord, l'annonce ensuite : un 404, un corps vide, une reponse qui n'est pas
un PNG exploitable ne coutent qu'une requete perdue. Le cache est du coup
indexe par (URL annoncee, taille), pour que le repli range son image la ou la
carte ira la chercher.

**Les noms traduits.** Repondu, et c'est non : l'espagnol et le portugais seuls
sont servis, le francais ne l'est pas, et **les noms d'equipes ne sont jamais
traduits** dans aucune langue. `i18n.py` garde donc son travail, et `teams.py`
son rapprochement sur les libelles anglais.

---

## Annexe A - les actions du football

Releve sur 7 competitions et 3 periodes, soit environ 3 300 actions. `type.id`
est stable, `type.text` est en anglais.

| `type.id` | `type.text` | `scoreValue` | Drapeau | Occurrences |
| --- | --- | --- | --- | --- |
| 70 | Goal | 1 | `scoringPlay` | 981 |
| 137 | Goal - Header | 1 | `scoringPlay` | 190 |
| 173 | Goal - Volley | 1 | `scoringPlay` | 76 |
| 138 | Goal - Free-kick | 1 | `scoringPlay` | 18 |
| 98 | Penalty - Scored | 1 | `scoringPlay` + `penaltyKick` | 87 |
| 104 | Penalty - Scored | 1 | `scoringPlay` + `penaltyKick` + **`shootout`** | 7 |
| 97 | Own Goal | 1 | `scoringPlay` + `ownGoal` | 47 |
| 93 | Red Card | 0 | `redCard` | 93 |
| 94 | Yellow Card | 0 | `yellowCard` | 1817 |

Le code ne lit **pas** ces numeros au football : il lit les drapeaux, qui sont
plus surs - une variante de but inedite reste un but. Les numeros sont ici pour
comprendre, et pour reconnaitre un tir au but de seance - **104** - d'un
penalty de jeu - **98** - autrement que par le drapeau `shootout`.

Un carton jaune n'est jamais signale : ce n'est pas un evenement de score, et
la carte serait du bruit.

---

## Annexe B - les actions du rugby et du hockey

### Rugby : `competitions[0].details`

Releve sur 5 competitions, 339 matchs, 17 957 actions. **Aucun drapeau** :
`type.id` est la seule information, et le nombre de points ne vient pas de la
source - c'est le code qui le connait.

| `type.id` | `type.text` | Points | Lu par butbutbut | Occurrences |
| --- | --- | --- | --- | --- |
| 1 | try | 5 | oui | 2585 |
| 2 | conversion | 2 | oui | 1923 |
| 3 | penalty goal | 3 | oui | 601 |
| 4 | drop goal | 3 | oui | 11 |
| 5 | yellow card | 0 | **non** | 442 |
| 6 | red card | 0 | oui | 42 |
| 7 | player substituted | 0 | non | 6183 |
| 8 | substitute on | 0 | non | 6167 |
| 37 | drop goal-missed | 0 | non | 3 |

Le carton jaune est ecarte expres : au rugby c'est une exclusion temporaire de
dix minutes, pas une expulsion, et le confondre avec un carton rouge donnerait
une carte qui ment. `drop goal-missed` rappelle pourquoi la table de secours
par libelle est en correspondance **exacte** et non par prefixe.

### Hockey : rien dans le tableau de bord

`details` est absent sur les 798 matchs termines releves. Les actions existent
dans `/summary?event=<id>` sous `plays[]`, avec ces types :

| `type.id` | `type.text` |
| --- | --- |
| 505 | Goal |
| 506 | Shot |
| 507 | Missed |
| 508 | Blocked |
| 502 | Face Off |
| 503 | Hit |
| 516 | Stoppage |
| 518 / 519 | Period Start / Period End |
| 1401 / 1402 | Takeaway / Giveaway |
| 31, 49, 55... | les penalites, une par infraction |

**Seul le 505 est lu**, et il l'est deux fois : par son numero, et par son
libelle "Goal" en secours - la meme precaution qu'au rugby, ou les numeros ont
deja bouge. Les 288 autres actions d'un match ne sont pas ignorees par
economie, elles n'habillent aucune carte : un tir bloque ne fait pas de bruit.

---

## Annexe C - les codes de competition

Les codes servis par `leagues/dropdown` au 7 septembre 2026. La colonne
"classement" reprend `hasStandings` : une competition a `non` rendra un
`children` vide sur `/standings`.

Le catalogue de butbutbut est un sous-ensemble de cette liste ; n'importe quel
autre code s'ouvre a la volee (`--leagues gre.1`,
`--leagues hockey:mens-college-hockey`).

### Hockey (6)

| slug | nom | classement |
| --- | --- | --- |
| `hockey-world-cup` | World Cup of Hockey | non |
| `mens-college-hockey` | NCAA Men's Ice Hockey | non |
| `nhl` | National Hockey League | oui |
| `olympics-mens-ice-hockey` | Men's Ice Hockey | non |
| `olympics-womens-ice-hockey` | Women's Ice Hockey | non |
| `womens-college-hockey` | NCAA Women's Hockey | non |

### Rugby (19)

| slug | nom | classement |
| --- | --- | --- |
| `164205` | Rugby World Cup | oui |
| `17567` | Nations Championship | oui |
| `180659` | Six Nations | oui |
| `2009` | URBA Primera A | non |
| `242041` | Super Rugby Pacific | oui |
| `244293` | The Rugby Championship | oui |
| `267979` | Gallagher Prem | oui |
| `268565` | British and Irish Lions Tour | non |
| `270557` | United Rugby Championship | oui |
| `270559` | French Top 14 | non |
| `270563` | Mitre 10 Cup | oui |
| `271937` | European Rugby Champions Cup | oui |
| `272073` | European Rugby Challenge Cup | non |
| `282` | Olympic Men's 7s | oui |
| `283` | Olympic Women's Rugby Sevens | oui |
| `289234` | International Test Match | oui |
| `289237` | Women's Rugby World Cup | oui |
| `289262` | Major League Rugby | non |
| `289279` | URBA Top 14 | oui |

### Football (218)

| slug | nom | classement |
| --- | --- | --- |
| `afc.asian.cup` | AFC Asian Cup | oui |
| `afc.champions` | AFC Champions League Elite | oui |
| `afc.champions_qual` | AFC Champions League Elite Qualifying | non |
| `afc.cup` | AFC Champions League Two | oui |
| `afc.cup_qual` | AFC Champions League Two Qualifying | non |
| `afc.cupq` | AFC Asian Cup Qualifiers | oui |
| `afc.saff.championship` | SAFF Championship | oui |
| `afc.w.asian.cup` | AFC Women's Asian Cup | oui |
| `aff.championship` | ASEAN Championship | oui |
| `arg.1` | Argentine Liga Profesional de Futbol | oui |
| `arg.2` | Argentine Nacional B | oui |
| `arg.3` | Argentine Primera B | oui |
| `arg.copa` | Copa Argentina | non |
| `arg.copa_de_la_superliga` | Argentine Copa de la Superliga | oui |
| `arg.supercopa` | Argentine Supercopa | non |
| `arg.supercopa.internacional` | Argentine Supercopa Internacional | non |
| `arg.trofeo_de_la_campeones` | Argentine Trofeo de Campeones | non |
| `aus.1` | Australian A-League Men | oui |
| `aus.w.1` | Australian A-League Women | oui |
| `aut.1` | Austrian Bundesliga | oui |
| `bel.1` | Belgian Pro League | oui |
| `bel.promotion.relegation` | Belgian Pro League Promotion/Relegation Playoffs | non |
| `bol.1` | Bolivian Liga Profesional | oui |
| `bol.copa` | Copa Bolivia | oui |
| `bol.ply.rel` | Bolivian Liga Profesional Promotion/Relegation Playoffs | non |
| `bra.1` | Brazilian Serie A | oui |
| `bra.2` | Brazilian Serie B | oui |
| `bra.camp.carioca` | Brazilian Campeonato Carioca | oui |
| `bra.camp.gaucho` | Brazilian Campeonato Gaucho | oui |
| `bra.camp.mineiro` | Brazilian Campeonato Mineiro | oui |
| `bra.camp.paulista` | Brazilian Campeonato Paulista | oui |
| `bra.copa_do_brazil` | Copa do Brasil | non |
| `bra.supercopa_do_brazil` | Brazilian Supercopa Rei | non |
| `caf.champions` | CAF Champions League | oui |
| `caf.championship` | African Nations Championship | oui |
| `caf.confed` | CAF Confederation Cup | oui |
| `caf.cosafa` | COSAFA Cup | oui |
| `caf.nations` | Africa Cup of Nations | oui |
| `caf.nations_qual` | Africa Cup of Nations Qualifying | oui |
| `caf.w.nations` | Women's Africa Cup of Nations | oui |
| `campeones.cup` | Campeones Cup | non |
| `can.w.nsl` | Northern Super League | oui |
| `chi.1` | Chilean Primera Division | oui |
| `chi.1.promotion.relegation` | Chilean Primera Division Promotion/Relegation Playoffs | non |
| `chi.copa_chi` | Copa Chile | oui |
| `chi.super_cup` | Chilean Supercopa | non |
| `chn.1` | Chinese Super League | oui |
| `chn.1.promotion.relegation` | Chinese Super League Promotion/Relegation Playoffs | non |
| `club.friendly` | Club Friendly | non |
| `col.1` | Colombian Primera A | oui |
| `col.copa` | Copa Colombia | oui |
| `col.superliga` | Colombian Superliga | non |
| `concacaf.central.american.cup` | Concacaf Central American Cup | oui |
| `concacaf.champions` | Concacaf Champions Cup | non |
| `concacaf.champions_cup` | CONCACAF Champions Cup | non |
| `concacaf.confederations_playoff` | Concacaf Cup | non |
| `concacaf.gold` | Concacaf Gold Cup | oui |
| `concacaf.gold_qual` | Concacaf Gold Cup Qualifying | non |
| `concacaf.leagues.cup` | Leagues Cup | oui |
| `concacaf.nations.league` | Concacaf Nations League | oui |
| `concacaf.u23` | CONCACAF U23 Tournament | oui |
| `concacaf.w.champions_cup` | Concacaf W Champions Cup | oui |
| `concacaf.w.gold` | Concacaf W Gold Cup | oui |
| `concacaf.womens.championship` | Concacaf W Championship | non |
| `conmebol.america` | Copa America | oui |
| `conmebol.america.femenina` | Copa America Femenina | oui |
| `conmebol.libertadores` | CONMEBOL Libertadores | oui |
| `conmebol.recopa` | CONMEBOL Recopa | non |
| `conmebol.sudamericana` | CONMEBOL Sudamericana | oui |
| `crc.1` | Costa Rican Primera Division | oui |
| `den.1` | Danish Superliga | oui |
| `ecu.1` | LigaPro Ecuador | oui |
| `eng.1` | English Premier League | oui |
| `eng.2` | English League Championship | oui |
| `eng.3` | English League One | oui |
| `eng.4` | English League Two | oui |
| `eng.5` | English National League | oui |
| `eng.charity` | English FA Community Shield | non |
| `eng.fa` | English FA Cup | non |
| `eng.fa_qual` | English FA Cup Qualifying | non |
| `eng.league_cup` | English Carabao Cup | non |
| `eng.trophy` | English EFL Trophy | oui |
| `eng.w.1` | English Women's Super League | oui |
| `eng.w.fa` | English Women's FA Cup | non |
| `eng.w.league_cup` | English Women's League Cup | oui |
| `eng.w.promotion.relegation` | English Women's Super League Promotion/Relegation Playoff | non |
| `esp.1` | Spanish LALIGA | oui |
| `esp.2` | Spanish LALIGA 2 | oui |
| `esp.copa_de_la_reina` | Spanish Copa de la Reina | non |
| `esp.copa_del_rey` | Spanish Copa del Rey | non |
| `esp.joan_gamper` | Trofeo Joan Gamper | non |
| `esp.super_cup` | Spanish Supercopa | non |
| `esp.w.1` | Spanish Liga F | oui |
| `fifa.concacaf.olympicsq` | Men's Olympic Qualifying Playoff | oui |
| `fifa.conmebol.olympicsq` | CONMEBOL Pre-Olympic Tournament | oui |
| `fifa.cwc` | FIFA Club World Cup | oui |
| `fifa.friendly` | International Friendly | non |
| `fifa.friendly.w` | Women's International Friendly | non |
| `fifa.friendly_u21` | Under-21 International Friendly | non |
| `fifa.intercontinental.cup` | Intercontinental Cup (India) | oui |
| `fifa.intercontinental_cup` | FIFA Intercontinental Cup | non |
| `fifa.olympics` | Men's Olympic Soccer Tournament | oui |
| `fifa.shebelieves` | SheBelieves Cup | oui |
| `fifa.w.champions_cup` | FIFA Women's Champions Cup | non |
| `fifa.w.concacaf.olympicsq` | Concacaf Women's Olympic Qualifying | oui |
| `fifa.w.olympics` | Women's Olympic Soccer Tournament | oui |
| `fifa.wcq.ply` | FIFA World Cup Qualifying - Playoff Tournament | non |
| `fifa.world` | FIFA World Cup | oui |
| `fifa.world.u17` | FIFA Under-17 World Cup | oui |
| `fifa.world.u20` | FIFA Under-20 World Cup | oui |
| `fifa.worldq.afc` | FIFA World Cup Qualifying - AFC | oui |
| `fifa.worldq.caf` | FIFA World Cup Qualifying - CAF | oui |
| `fifa.worldq.concacaf` | FIFA World Cup Qualifying - Concacaf | oui |
| `fifa.worldq.conmebol` | FIFA World Cup Qualifying - CONMEBOL | oui |
| `fifa.worldq.ofc` | FIFA World Cup Qualifying - OFC | oui |
| `fifa.worldq.uefa` | FIFA World Cup Qualifying - UEFA | oui |
| `fifa.wwc` | FIFA Women's World Cup | oui |
| `fifa.wwcq.ply` | FIFA Women's World Cup Qualifying - Playoff Tournament | non |
| `fifa.wworld.u17` | FIFA Under-17 Women's World Cup | oui |
| `fifa.wworldq.uefa` | FIFA Women's World Cup Qualifying - UEFA | oui |
| `fra.1` | French Ligue 1 | oui |
| `fra.1.promotion.relegation` | French Ligue 1 Promotion/Relegation Playoffs | non |
| `fra.2` | French Ligue 2 | oui |
| `fra.coupe_de_france` | Coupe de France | non |
| `fra.super_cup` | French Trophee des Champions | non |
| `fra.w.1` | French Premiere Ligue | oui |
| `friendly.emirates_cup` | Emirates Cup | non |
| `ger.1` | German Bundesliga | oui |
| `ger.2` | German 2. Bundesliga | oui |
| `ger.2.promotion.relegation` | German Bundesliga 2. Promotion/Relegation Playoffs | non |
| `ger.dfb_pokal` | German Cup | non |
| `ger.playoff.relegation` | German Bundesliga Promotion/Relegation Playoff | non |
| `ger.super_cup` | German Supercup | non |
| `global.arnold.clark_cup` | Arnold Clark Cup | oui |
| `global.club_challenge` | CONMEBOL-UEFA Club Challenge | non |
| `global.finalissima` | CONMEBOL-UEFA Cup of Champions | non |
| `global.gulf_cup` | Arabian Gulf Cup | oui |
| `global.pinatar_cup` | Pinatar Cup | oui |
| `global.u20.intercontinental_cup` | CONMEBOL-UEFA U20 Intercontinental Cup | non |
| `global.w.finalissima` | CONMEBOL-UEFA Women's Cup of Champions | non |
| `gre.1` | Greek Super League | oui |
| `gua.1` | Guatemalan Liga Nacional | oui |
| `hon.1` | Honduran Liga Nacional | oui |
| `ind.1` | Indian Super League | oui |
| `ita.1` | Italian Serie A | oui |
| `ita.2` | Italian Serie B | oui |
| `ita.coppa_italia` | Coppa Italia | non |
| `ita.super_cup` | Italian Supercoppa | non |
| `jpn.1` | Japanese J.League | oui |
| `jpn.world_challenge` | Japanese J.League World Challenge | non |
| `ksa.1` | Saudi Pro League | oui |
| `ksa.kings.cup` | Saudi King's Cup | non |
| `mex.1` | Mexican Liga BBVA MX | oui |
| `mex.2` | Mexican Liga de Expansion MX | oui |
| `mex.campeon` | Mexican Campeon de Campeones | non |
| `ned.1` | Dutch Eredivisie | oui |
| `ned.2` | Dutch Keuken Kampioen Divisie | oui |
| `ned.3.promotion.relegation` | Dutch Tweede Divisie Promotion/Relegation Playoffs | non |
| `ned.cup` | Dutch KNVB Beker | non |
| `ned.playoff.relegation` | Dutch Eredivisie Promotion/Relegation Playoffs | non |
| `ned.supercup` | Dutch Johan Cruyff Shield | non |
| `ned.w.1` | Dutch Vrouwen Eredivisie | oui |
| `ned.w.knvb_cup` | Dutch KNVB Beker Vrouwen | non |
| `nonfifa` | Non-FIFA Friendly | non |
| `nor.1` | Norwegian Eliteserien | oui |
| `nor.1.promotion.relegation` | Norwegian Eliteserien Promotion/Relegation Playoffs | non |
| `par.1` | Paraguayan Primera Division | oui |
| `par.1.supercopa` | Paraguayan Supercopa | non |
| `per.1` | Peruvian Liga 1 | oui |
| `por.1` | Portuguese Primeira Liga | oui |
| `por.1.promotion.relegation` | Portuguese Primeira Liga Promotion/Relegation Playoffs | non |
| `por.taca.portugal` | Taca de Portugal | non |
| `rsa.1` | South African Premiership | oui |
| `rus.1` | Russian Premier League | oui |
| `rus.1.promotion.relegation` | Russian Premier League Relegation/Promotion Playoffs | non |
| `sco.1` | Scottish Premiership | oui |
| `sco.1.promotion.relegation` | Scottish Premiership Promotion/Relegation Playoffs | non |
| `sco.2` | Scottish Championship | oui |
| `sco.2.promotion.relegation` | Scottish Championship Promotion/Relegation Playoffs | non |
| `sco.challenge` | Scottish League Challenge Cup | oui |
| `sco.cis` | Scottish League Cup | oui |
| `sco.tennents` | Scottish Cup | non |
| `sco.tennents_qual` | Scottish Cup Qualifying | non |
| `slv.1` | Salvadoran Primera Division | oui |
| `swe.1` | Swedish Allsvenskan | oui |
| `swe.1.promotion.relegation` | Swedish Allsvenskan Promotion/Relegation Playoffs | non |
| `tur.1` | Turkish Super Lig | oui |
| `uefa.champions` | UEFA Champions League | oui |
| `uefa.champions_qual` | UEFA Champions League Qualifying | non |
| `uefa.euro` | UEFA European Championship | oui |
| `uefa.euro.u19` | UEFA European Under-19 Championship | oui |
| `uefa.euro_u21` | UEFA European Under-21 Championship | oui |
| `uefa.euro_u21_qual` | UEFA European Under-21 Championship Qualifying | oui |
| `uefa.europa` | UEFA Europa League | oui |
| `uefa.europa.conf` | UEFA Conference League | oui |
| `uefa.europa.conf_qual` | UEFA Conference League Qualifying | non |
| `uefa.europa_qual` | UEFA Europa League Qualifying | non |
| `uefa.euroq` | UEFA European Championship Qualifying | oui |
| `uefa.nations` | UEFA Nations League | oui |
| `uefa.super_cup` | UEFA Super Cup | non |
| `uefa.w.europa` | UEFA Women's Europa Cup | non |
| `uefa.w.nations` | UEFA Women's Nations League | oui |
| `uefa.wchampions` | UEFA Women's Champions League | oui |
| `uefa.wchampions_qual` | UEFA Women's Champions League Qualifying | non |
| `uefa.weuro` | UEFA Women's European Championship | oui |
| `uru.1` | Liga AUF Uruguaya | oui |
| `uru.2` | Segunda Division de Uruguay | oui |
| `usa.1` | MLS | oui |
| `usa.ncaa.m.1` | NCAA Men's Soccer | non |
| `usa.ncaa.w.1` | NCAA Women's Soccer | non |
| `usa.nwsl` | NWSL | oui |
| `usa.nwsl.cup` | NWSL Challenge Cup | non |
| `usa.open` | U.S. Open Cup | non |
| `usa.usl.1` | USL Championship | oui |
| `usa.usl.l1` | USL League One | oui |
| `usa.usl.l1.cup` | USL Cup | oui |
| `usa.w.usl.1` | USL Super League | oui |
| `ven.1` | Venezuelan Primera Division | oui |

---

## Annexe D - reverifier ce document

Rien de tout ce qui precede n'est garanti : c'est un releve, pas un contrat.
Voici de quoi le refaire, avec la seule bibliotheque standard.

Le tableau de bord, brut :

```bash
curl -s -H 'User-Agent: butbutbut/1.9.0 (+https://github.com/boubou666/butbutbut)' \
  'https://site.api.espn.com/apis/site/v2/sports/soccer/fra.1/scoreboard' | head -c 400
```

Les en-tetes, pour la question du cache et de l'`ETag` :

```bash
curl -sI -H 'User-Agent: butbutbut/1.9.0 (+https://github.com/boubou666/butbutbut)' \
  'https://site.api.espn.com/apis/site/v2/sports/soccer/fra.1/scoreboard'
```

Les actions d'un sport, comptees par type - c'est ainsi qu'ont ete faites les
annexes A et B :

```bash
python - <<'EOF'
import collections, json, urllib.request
UA = "butbutbut/1.9.0 (+https://github.com/boubou666/butbutbut)"
url = ("https://site.api.espn.com/apis/site/v2/sports/rugby/270559"
       "/scoreboard?dates=20260201-20260401&limit=500")
page = urllib.request.urlopen(
    urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30)
data = json.load(page)
seen = collections.Counter()
for event in data.get("events") or []:
    for competition in event.get("competitions") or []:
        for detail in competition.get("details") or []:
            kind = detail.get("type") or {}
            seen[(kind.get("id"), kind.get("text"))] += 1
for key, count in seen.most_common():
    print(key, count)
EOF
```

Le catalogue des competitions d'un sport, qui a produit l'annexe C :

```bash
python - <<'EOF'
import json, urllib.request
UA = "butbutbut/1.9.0 (+https://github.com/boubou666/butbutbut)"
url = "https://site.api.espn.com/apis/site/v2/leagues/dropdown?sport=soccer&limit=1000"
page = urllib.request.urlopen(
    urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30)
for league in json.load(page)["leagues"]:
    print(league["slug"], "|", league["name"], "|", league.get("hasStandings"))
EOF
```

Et surtout, le programme qui fait ce travail tous les jours sans qu'on le lui
demande :

```bash
python tools/canari.py
```

Le canari interroge la vraie source et verifie que **chaque cle lue par
`butbutbut/espn.py` est encore la, et du bon type**. C'est lui qui attrapera
une derive avant ce document, parce qu'il tourne dans la CI quotidienne
(`.github/workflows/canari.yml`) et que ce fichier, lui, ne tourne pas. En cas
de desaccord entre les deux, **c'est le canari qui a raison** : il vient de
parler a la source, ce document date du 7 septembre 2026.
