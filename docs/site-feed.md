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

Parametres optionnels :

- `from` et `to` : date `YYYY-MM-DD` ou date/heure ISO 8601. Une date de fin
  couvre toute la journee indiquee ;
- `limit` : 100 par defaut, de 1 a 500 ;
- `cursor` : valeur opaque rendue dans `next_cursor`.

L'ordre est strictement `(starts_at, external_id)`. La pagination utilise cette
cle et non un decalage : elle ne charge pas tout l'historique en memoire. Un
curseur est lie a ses filtres `from` et `to` ; le reutiliser avec d'autres
bornes rend HTTP 400. A la derniere page, `next_cursor` vaut `null`.

Les identifiants de competition, de match et d'equipe sont ceux recus d'ESPN.
Un evenement sans identifiant ESPN propre recoit une cle stable dans son match,
faite des champs ESPN qui le decrivent. Les dates de match sont en UTC et les
statuts sont limites a `scheduled`, `live`, `finished`, `postponed` et
`cancelled`.

`competition.logo_url` et `team.crest_url` viennent uniquement des metadonnees
effectivement recues. Aucune URL de logo n'est construite a partir d'un
identifiant suppose ; la valeur reste `null` quand la source ne publie rien.
La meme representation normalisee de la competition est incluse dans chaque
match.

## Backfill explicite et reprenable

Le daemon ne lance jamais un backfill massif au demarrage. La commande dediee
travaille mois par mois, limite les requetes, reessaie les erreurs transitoires,
met les reponses brutes compressees en cache et valide chaque lot dans SQLite.
Les reponses brutes et les objets normalises restent dans deux stockages
separes. Relancer exactement la meme commande saute les lots termines et relit
le cache si un lot doit etre repris.

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
