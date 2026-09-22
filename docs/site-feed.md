# Flux local versionne pour un site

Le compagnon HTTP expose `GET /api/v1/site-feed`. Cette route est independante
de tout site consommateur : elle lit uniquement le stockage local du daemon,
ne fait aucun appel reseau et ne pousse aucune donnee vers un service tiers.
`/api/state`, `/api/sync` et les comportements de surveillance restent
inchanges.

Demarrer le serveur :

```bash
butbutbut --serve
curl 'http://127.0.0.1:8765/api/v1/site-feed?from=2026-08-01&limit=100'
```

L'ecoute reste limitee a `127.0.0.1` par defaut. Il n'y a pas
d'authentification : ne pas exposer ce port a Internet.

## Contrat v1

La reponse est du JSON UTF-8. Elle contient toujours :

```json
{
  "schema_version": 1,
  "producer": "butbutbut/1.24.0",
  "generated_at": "2026-09-20T20:00:00Z",
  "competitions": [],
  "matches": [],
  "standings": [],
  "next_cursor": null,
  "state": {
    "available": true,
    "updated_at": 1789934400.0,
    "started_at": 1789930000.0,
    "goals_today": 3,
    "total_matches": 18
  },
  "errors": []
}
```

`state` est une liste blanche volontairement courte. Aucun secret, cookie,
preference utilisateur ni chemin local n'est expose. `errors` rend visibles
les erreurs de backfill d'une competition sans retirer les donnees des autres.

### Recherche locale

Le compagnon indexe les equipes rencontrees et les competitions connues :

```bash
curl 'http://127.0.0.1:8765/api/v1/search?q=saint+etienne&limit=12'
```

`q` contient au moins deux caracteres et `limit` est optionnel, de 1 a 20.
Chaque resultat porte `type: team` ou `type: competition` ainsi que l'objet
normalise correspondant. La recherche ignore casse, accents et ponctuation,
reste entierement locale et ne consulte pas la source sportive. L'index equipe
est actualise avec les matchs et reconstruit une fois depuis les objets deja
stockes lors de l'ouverture d'une ancienne base.

Dans le compagnon, l'etoile d'un resultat l'ajoute a **Mes favoris**. La liste
est conservee dans le stockage local du navigateur : elle ne modifie ni la
configuration du daemon, ni la base SQLite, et ne quitte jamais la machine.
L'Explorer montre aussi les huit dernieres fiches Match Center, equipe ou
competition consultees. Cette liste locale ne conserve que type, identifiant
et nom (jamais un score), ignore les entrees invalides et se synchronise entre
onglets. Une etoile permet de suivre une equipe ou competition depuis cette
liste. `/` focalise la recherche ; Echap l'efface.
Le navigateur envoie uniquement leurs identifiants a la route locale
`GET /api/v1/favorites?team=...&competition=...&limit=12`. La reponse deduplique
les directs et matchs a venir, place les directs en premier et masque leur
score lorsque le retard streaming est actif. Vingt favoris et vingt matchs par
reponse constituent les bornes maximales.
Le bloc **A suivre** demande maintenant `limit=20`, regroupe les rencontres
par direct ou date locale et les filtre dans le navigateur. Le filtre visuel
ne change ni la requete du calendrier ni les regles anti-spoiler.
Un selecteur permet aussi de voir seulement les rencontres d'un favori lorsque
plusieurs sont enregistres. Il lance une requete locale separee avec ce seul
identifiant et `limit=20`, afin qu'un favori absent des vingt premiers matchs
globaux reste consultable. Le flux global continue a alimenter les alertes et
le calendrier ; le choix affiche ne les limite pas.
Le navigateur retient le favori et le filtre Tous / En direct / A venir dans
son stockage local, et revient a Tous mes favoris si la selection a disparu.
Un encart annonce le prochain coup d'envoi programme dans la vue courante,
sans consulter une autre source et sans afficher de score. Le lien secondaire
**Calendrier de ce favori .ics** applique uniquement son identifiant a la
route iCalendar ; le calendrier global reste inchange.
L'Explorer peut exporter cette selection en `butbutbut-favoris.json`, puis
importer ce fichier dans un autre navigateur. Le JSON versionne contient
`version: 1` et une liste `favorites` (type, identifiant et nom) ; l'import
valide le fichier, ignore les doublons et ajoute les entrees absentes sans
retirer les favoris deja presents. Aucun fichier n'est envoye au serveur.
Les fiches equipe et competition lisent et modifient la meme cle de stockage
local que l'Explorer ; les onglets ouverts reagissent aussi aux changements de
cette cle via l'evenement `storage`. Aucun appel d'ecriture n'est adresse au
daemon.
Le Match Center affiche aussi des boutons de favori pour ses deux equipes et
sa competition. Ils restent utilisables dans la vue de direct synchronise,
sans reveler le score masque.

La variante `GET /api/v1/favorites.ics` accepte les memes parametres `team` et
`competition`. Elle renvoie les rencontres programmees au format iCalendar,
avec `Content-Type: text/calendar` et une piece jointe
`butbutbut-favoris.ics`. Les directs, reports sans nouvel horaire et dates
invalides ne sont pas ajoutes au calendrier.

Le bouton **Activer les alertes** s'appuie sur l'API Notification du navigateur.
L'autorisation et le choix restent propres a ce navigateur ; aucun abonnement
n'est cree cote serveur. Tant que la page reste ouverte, deux releves successifs
du flux favori permettent de signaler un passage en direct ou un changement de
score. Le premier releve initialise seulement la comparaison, et un match
`spoiler_free` ne produit aucune notification.

Parametres optionnels :

- `from` et `to` : date `YYYY-MM-DD` ou date/heure ISO 8601. Une date de fin
  couvre toute la journee indiquee ;
- `limit` : 100 par defaut, de 1 a 500 ;
- `cursor` : valeur opaque rendue dans `next_cursor`.

L'ordre est strictement `(starts_at, external_id)`. La pagination utilise cette
cle et non un decalage : elle ne charge pas tout l'historique en memoire. Un
curseur est lie a ses filtres `from` et `to` ; le reutiliser avec d'autres
bornes rend HTTP 400. A la derniere page, `next_cursor` vaut `null`.

### Fiche d'un match

Le compagnon expose aussi la lecture directe d'un match deja present dans le
stockage, sans parcourir les pages du flux :

```bash
curl 'http://127.0.0.1:8765/api/v1/match?id=401'
```

La reponse contient `schema_version`, `generated_at`, `spoiler_free` et
`match`. L'objet `match` reprend exactement la representation normalisee du
flux, avec la metadonnee de competition la plus recente. Un identifiant absent
rend HTTP 404 et un parametre absent ou ambigu rend HTTP 400.

Quand le retard de streaming est actif et que le match est en direct,
`spoiler_free` vaut `true`. La fiche ne publie alors que l'identifiant, la
competition, les deux equipes, l'heure de debut et le statut : score, minute,
actions et statistiques restent volontairement masques.

### Fiche d'une competition

L'explorateur local lit une edition complete avec ses matchs et ses
classements :

```bash
curl 'http://127.0.0.1:8765/api/v1/competition?id=fifa.world&edition=2022'
```

`edition` est optionnel ; sans lui, l'edition qui porte le match le plus recent
est choisie. La reponse contient `competition`, l'`edition` selectionnee, la
liste `editions`, les `matches` chronologiques et les `standings` officiels de
cette edition. Un identifiant de competition ou d'edition inconnu rend HTTP
404. L'index local `(competition, edition, date)` evite de parcourir tout
l'historique a chaque ouverture.

Pendant une synchronisation de streaming, chaque match en direct de cette
fiche porte `spoiler_free: true` et perd, comme le Match Center, score brut,
minute, actions et statistiques. Les matchs termines et a venir restent
inchanges.

### Fiche d'une equipe

La route equipe rassemble son historique local dans toutes les competitions :

```bash
curl 'http://127.0.0.1:8765/api/v1/team?id=176'
```

La reponse contient `team`, les `competitions` rencontrees, le bilan `record`,
la `form` des cinq derniers matchs termines et les `matches` chronologiques.
Le bilan compte uniquement les rencontres terminees et utilise le vainqueur
officiel lorsqu'un score reste egal apres une seance de tirs au but. Un
identifiant inconnu rend HTTP 404.

Deux index locaux, un par camp, evitent de parcourir l'historique complet. Ils
sont alimentes a chaque releve et reconstruits automatiquement lors de la
premiere ouverture d'une ancienne base. Les matchs en direct y respectent le
meme champ `spoiler_free` et le meme masquage que les autres vues detaillees.

### Face-a-face

Deux equipes deja rencontrees peuvent etre comparees sans requete distante :

```bash
curl 'http://127.0.0.1:8765/api/v1/head-to-head?team=176&opponent=160'
```

La reponse conserve l'ordre demande dans `first_team` et `second_team`, puis
fournit leurs `competitions`, leur `record` commun et les `matches`
chronologiques. Le bilan compte victoires, nuls et buts de chaque camp sur les
seuls matchs termines. Il utilise `winner_team_external_id` pour ne pas lire
une victoire aux tirs au but comme un nul. Deux identifiants identiques rendent
HTTP 400 ; une paire sans rencontre connue rend HTTP 404. Le masque du direct
est identique a celui des fiches match, competition et equipe.

Les champs historiques `external_id` des competitions, matchs et equipes sont
conserves sans changement. Les nouveaux identifiants de structure sont des
chaines opaques : un consommateur ne doit dependre ni de leur forme, ni d'une
URL, ni d'un nom de table du fournisseur. Ils restent stables dans leur edition
et la jointure se fait toujours par egalite stricte. Un evenement sans
identifiant propre recoit une cle stable dans son match, faite des champs source
qui le decrivent. Les dates de match sont en UTC et les statuts sont limites a
`scheduled`, `live`, `finished`, `postponed` et `cancelled`.

`competition.logo_url` et `team.crest_url` viennent uniquement des metadonnees
effectivement recues. Aucune URL de logo n'est construite a partir d'un
identifiant suppose ; la valeur reste `null` quand la source ne publie rien.
La meme representation normalisee de la competition est incluse dans chaque
match.

### Structure officielle des competitions

Chaque objet de `matches` conserve tous ses champs precedents et ajoute les
champs suivants. Une donnee que les ressources officielles ne publient pas vaut
`null` ; le feed ne deduit jamais un tour d'une date ou d'un texte libre.

- edition : `edition_external_id`, `edition_name` ;
- phase : `phase_kind` (`league`, `group` ou `knockout`),
  `phase_external_id`, `phase_name`, `phase_order` ;
- groupe : `group_external_id`, `group_name`, `group_order` ;
- tour : `round_external_id`, `round_name`, `round_order` ;
- tableau : `tie_external_id`, `leg_number`, `bracket_slot`,
  `next_match_external_id` ;
- resultat : `winner_team_external_id` et `decided_by` (`regular_time`,
  `extra_time` ou `penalties`).

`phase_order`, `group_order` et `round_order` sont des rangs commences a 1 dans
l'ordre officiel recu. `next_match_external_id` designe bien un match du feed,
pas un numero de case du tableau. `winner_team_external_id` reprend l'identifiant
de l'une des deux equipes du match.

`standings` contient un objet par groupe officiellement classe :

```json
{
  "competition_external_id": "fifa.world",
  "edition_external_id": "2022",
  "edition_name": "2022 FIFA World Cup",
  "phase_external_id": "10953",
  "phase_name": "Group Stage",
  "phase_order": 1,
  "group_external_id": "1",
  "group_name": "Group A",
  "group_order": 1,
  "rows": [{
    "team_external_id": "449",
    "team_name": "Netherlands",
    "played": 3,
    "won": 2,
    "drawn": 1,
    "lost": 0,
    "goals_for": 5,
    "goals_against": 1,
    "goal_difference": 4,
    "points": 7,
    "rank": 1,
    "penalties": 0
  }]
}
```

Toutes les valeurs d'une ligne, rang et penalites compris, proviennent du
classement officiel. Elles valent `null` si la colonne manque ; aucun total,
rang ni departage n'est recalcule localement. Cet ajout est retrocompatible et
ne change pas `schema_version: 1` ni le chemin `/api/v1/site-feed`.

## Backfill explicite et reprenable

Le daemon ne lance jamais un backfill massif au demarrage. La commande dediee
travaille mois par mois, limite les requetes, reessaie les erreurs transitoires,
met chaque reponse brute compressee en cache (scoreboard, edition, tournoi,
evenements de tableau et classement) puis valide les objets normalises dans
SQLite. Les reponses brutes et les objets normalises restent dans deux
stockages separes. Relancer exactement la meme commande saute les lots termines
et relit le cache si un lot doit etre repris.

Verifier le plan sans reseau ni ecriture :

```bash
butbutbut --site-feed-backfill --site-feed-season 2025-2026 \
  --leagues all-football --site-feed-dry-run
```

Backfiller toutes les competitions de football supportees, saison par saison :

```bash
butbutbut --site-feed-backfill --site-feed-season 2023-2024 --leagues all-football
butbutbut --site-feed-backfill --site-feed-season 2024-2025 --leagues all-football
butbutbut --site-feed-backfill --site-feed-season 2025-2026 --leagues all-football
```

`all-football` inclut explicitement les catalogues masculin et feminin, sans
activer le hockey ni le rugby. Une saison `2025-2026` couvre du 1er juillet au
30 juin ; une saison `2025` couvre l'annee civile.

Une plage arbitraire est aussi possible :

```bash
butbutbut --site-feed-backfill --site-feed-from 2026-01-01 \
  --site-feed-to 2026-06-30 --leagues l1,ucl
```

ESPN ne fournit pas de premiere date fiable commune. « Depuis le debut » exige
donc une borne explicite, choisie et conservable dans le script d'exploitation :

```bash
butbutbut --site-feed-backfill --site-feed-from beginning \
  --site-feed-earliest 1992-07-01 --site-feed-to 2026-09-20 \
  --leagues all-football
```

Le delai entre requetes vaut 1,5 seconde et se regle avec
`--site-feed-request-delay`. Une panne reste associee a sa competition et a son
mois, apparait dans `errors`, et n'invalide pas les autres competitions.

## Donnees et droits

Les logos, marques et donnees ESPN peuvent etre soumis a des conditions
d'utilisation. Leur disponibilite technique dans une reponse ne constitue pas
une autorisation de redistribution. Il appartient au consommateur du flux de
verifier les droits applicables avant toute publication.
