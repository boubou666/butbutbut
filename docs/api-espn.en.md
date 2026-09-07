# ESPN's API, as we surveyed it

The whole of butbutbut rests on a single source: ESPN's public scoreboard.
It is free, no key, no sign-up - and **no contract**. Nobody publishes its
shape, nobody will warn us the day a field is renamed. So the code reads it
defensively, `tools/canari.py` watches it every day, and this file is the
third floor of the same precaution: **the contract we write for ourselves**,
since the provider writes none.

Every figure below was surveyed against the real source, in production, on
**7 September 2026**. Nothing here comes from memory or from a blog post: what
could not be observed is marked as such. Appendix D gives the commands to redo
all of it.

> **Warning.** None of these addresses is documented or guaranteed by ESPN.
> They can vanish overnight, and the use made of them here is that of a
> desktop client polling a few competitions every twenty seconds. This is not
> an invitation to build a service on them.

## Contents

- [1. The hosts](#1-the-hosts)
- [2. What holds for every request](#2-what-holds-for-every-request)
- [3. The scoreboard](#3-the-scoreboard)
- [4. Teams](#4-teams)
- [5. Standings](#5-standings)
- [6. The competition catalogue](#6-the-competition-catalogue)
- [7. A match summary](#7-a-match-summary)
- [8. The core API](#8-the-core-api)
- [9. Images](#9-images)
- [10. What butbutbut actually reads](#10-what-butbutbut-actually-reads)
- [11. The traps](#11-the-traps)
- [12. What could be done with this](#12-what-could-be-done-with-this)
- [Appendix A - football plays](#appendix-a---football-plays)
- [Appendix B - rugby and hockey plays](#appendix-b---rugby-and-hockey-plays)
- [Appendix C - competition codes](#appendix-c---competition-codes)
- [Appendix D - re-checking this document](#appendix-d---re-checking-this-document)

---

## 1. The hosts

Four domain names, and they do not serve the same purpose.

| Host | What it serves | What we read from it |
| --- | --- | --- |
| `site.api.espn.com` | the site API: scoreboard, teams, standings, match summary | **everything butbutbut uses** |
| `sports.core.api.espn.com` | the internal API, hyperlinked (`$ref`) and paginated | nothing, but it answers everything |
| `a.espncdn.com` | images: crests, competition logos, headshots | the crests |
| `site.web.api.espn.com` | the same service, plus a few website views | nothing: it already serves everything above |

The first two publish the same matches in two very different shapes:
`site.api` serves one large complete object per request, `core` serves a graph
of references to be followed one by one. For a client polling a score every
twenty seconds the first wins without argument - which is the point of
everything that follows.

`site.web.api` deserves a sentence, because it looks like one more door: it is
the same service as `site.api`, on the same paths and to the byte (33,832 on
both for Ligue 1). It adds a view of its own,
`/apis/v2/scoreboard/header?sport=soccer&league=fra.1`, which returns the same
matches in 37 kB, accepts **one** competition at a time and therefore brings
nothing. Its `common/v3` paths (`/statistics`, `/leaders`) return 404.

---

## 2. What holds for every request

### The shape of the URLs

```
https://site.api.espn.com/apis/site/v2/sports/<sport>/<competition>/<resource>
```

`<sport>` is the only segment that changes from one sport to another:
`soccer`, `hockey`, `rugby`. `<competition>` is the ESPN code - a dotted name
in football (`fra.1`), a word in hockey (`nhl`), a **number** in rugby
(`270559`). The shape of the response, on the other hand, is almost the same
everywhere, and that "almost" is the whole of section 3.

Everything is `GET`, everything returns UTF-8 JSON, nothing asks for a key, no
quota is announced. Twelve requests fired back to back in 0.9 s all returned
200: there is no visible limit at the scale of a desktop client. That is no
reason to hammer it - the daemon polls every twenty seconds, and the source
itself declares one to sixty seconds of cacheability.

### The headers we send

Those of `espn.headers()`, and one of them is not decoration:

```
User-Agent: butbutbut/1.9.0 (+https://github.com/boubou666/butbutbut)
Accept: application/json
Accept-Language: fr,en;q=0.8
Cache-Control: no-cache
```

### The `User-Agent` is filtered, and that is a trap

An Akamai stands in front of the API and refuses some clients. The refusal is
a **403 in HTML** (`Server: AkamaiGHost`, `<TITLE>Access Denied</TITLE>`), not
an error JSON: a reader expecting JSON sees an unreadable response rather than
a refusal. Surveyed on the same URL, back to back:

| `User-Agent` | Response |
| --- | --- |
| `butbutbut/1.9.0 (+https://github.com/boubou666/butbutbut)` | **200** |
| `Python-urllib/3.14` (the stdlib default) | 200 |
| `curl/8.0` | 200 |
| `butbutbut/1.9.0` (the same one, without the URL) | **403** |
| `butbutbut`, `foo/1.0`, `x` | 403 |
| `Mozilla/5.0` | 403 |
| a complete, credible Chrome string | 403 |

So the filter is not "a real browser gets through" - rather the opposite:
**pretending to be a browser is exactly what gets you refused**. An agent that
names itself and gives a way to reach it gets through. That is why the
project's header carries the repository URL, and it is a line not to shorten
in the name of tidiness.

### Compression, on the other hand, is free

The API answers `Vary: Accept-Encoding` and honours `Accept-Encoding: gzip`.
On the Ligue 1 scoreboard: **33,832 bytes without, 4,145 with**, eight times
less; over a full round of `--leagues all`, 1,355 kB against 148 kB. Nothing to
decode by hand, `gzip.decompress` is enough. **butbutbut has asked for it since
1.10.0**: this survey is what settled the question, for want of anything better
(see just below).

### The cache, and what is missing from it

| Header | Observed value |
| --- | --- |
| `Cache-Control` | `max-age=1` to `max-age=10` on the scoreboard, `max-age=63` on `/teams`, `max-age=900` on the core API |
| `ETag` | **absent** |
| `Last-Modified` | **absent** |
| `Vary` | `Accept-Encoding` |
| `Access-Control-Allow-Origin` | `*` |

The absence of the middle two settles a question that kept coming back:
**conditional requests are impossible**. With no `ETag` and no
`Last-Modified` there is nothing to put in an `If-None-Match` or an
`If-Modified-Since`, and both attempts do return a full 200. So the 36
requests per round of `--leagues all` cannot be saved that way; they can,
however, be made eight tenths lighter with gzip.

### Errors

| Code | When | Body |
| --- | --- | --- |
| 400 | unknown competition, unknown sport, malformed `dates` | `{"code":400,"message":"Failed to get events endpoint."}` |
| 400 | standings of an unknown competition | `{"code":400,"message":"Unable to retrieve any standings information for zzz.9"}` |
| 400 | unknown team | `{"code":400,"message":"Failed to get league teams summary"}` |
| 404 | unknown match on `/summary` | `{"code":404,"message":"Error invoking GET: ...pvt/v2/..."}` |
| 403 | filtered `User-Agent` | **HTML**, not JSON |

Note that an unknown competition returns **400 and not 404**, and the message
does not distinguish "this code does not exist" from "this address is
malformed". The summary's 404 leaks the internal address
(`sports.core.api.espn.pvt`), which says enough about who these messages were
written for.

A known competition with no match today returns **200 with `"events": []`**:
an off-season is not an error, and the code must not treat it as one.

### `lang` and `region`: two thirds disappointment

The endpoints accept `?lang=xx&region=yy`. The question was worth asking - if
the source could translate, `i18n.py` would carry less. Surveyed on
`soccer/ger.1`:

| Parameters | Competition name | Match state |
| --- | --- | --- |
| (none) | German Bundesliga | Full Time |
| `lang=es&region=es` | **Bundesliga** | **Tiempo Completo** |
| `lang=pt&region=br` | **Bundesliga** | **Final da Partida** |
| `lang=nl&region=nl` | Bundesliga | Full Time |
| `lang=fr&region=fr` | German Bundesliga | Full Time |
| `lang=it&region=it`, `lang=de&region=de`, `lang=ar&region=ae` | German Bundesliga | Full Time |
| `lang=zz&region=zz` | German Bundesliga | Full Time |

Three lessons. **Spanish and Portuguese really are translated** - competition
names and status labels. **French is not**, no more than German or Italian:
asking for `lang=fr` costs nothing and returns nothing. And **team names never
move**, in any language, which removed the main interest anyway: `teams.py`
works on the team labels, and they would have stayed untranslated.

An unknown `lang` is not an error: it is ignored.

---

## 3. The scoreboard

```
https://site.api.espn.com/apis/site/v2/sports/<sport>/<competition>/scoreboard
```

This is the endpoint that runs the program: one call per competition per
round of the loop, and everything shown on a card comes out of it.

### The parameters

Checked on `soccer/eng.1`, on 7 September 2026:

| Parameter | Effect | Checked |
| --- | --- | --- |
| `dates=YYYYMMDD` | that day | `?dates=20260906` -> 2 matches |
| `dates=YYYYMMDD-YYYYMMDD` | the interval, **both bounds included** | `?dates=20260901-20260930` -> 30 matches |
| `dates=YYYYMM` | the whole month | `?dates=202609` -> 30 matches |
| `dates=YYYY` | the whole season year | `?dates=2026` -> 100 matches (see `limit`) |
| `limit=N` | the maximum number of matches returned | **defaults to 100** |
| `lang`, `region` | see above | Spanish and Portuguese only |
| `season`, `seasontype`, `week` | **no effect** in football | `?week=3` returns 0 matches, `?season=2025` returns today |

Without `dates` the endpoint only serves **the current day**. That is enough
to watch for goals, not to say when the next match falls: it is the interval
that lets `--next` cover a week in one request per competition where a day at
a time would cost seven.

**The default `limit` is a silent trap.** `?dates=2026` on the Premier League
returns 100 matches without saying so; the same call with `&limit=500` returns
374, and an explicit interval (`?dates=20260801-20270601&limit=1000`) returns
the 380 of the fixture list - the season year does not cover exactly the same
range. Nothing in the response signals the truncation: no `next`, no total. A
client sweeping wide has to set `limit` itself.

### The general shape

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

`leagues[0]` carries the official name of the competition: that is where
`--leagues gre.1` gets its real name on the very first poll
(`League.adopt_name`). `leagues[0].calendar` is the list of the season's
matchdays as ISO dates - enough to know in advance which days are worth a
request.

### One match: `events[]`

| Field | Example | Note |
| --- | --- | --- |
| `id` | `"401876467"` | the match identifier, stable |
| `uid` | `"s:600~l:710~e:401876467"` | sport, competition, match |
| `date` | `"2026-09-06T13:00Z"` | UTC, **sometimes without seconds** |
| `name` | `"Strasbourg at Troyes"` | always in English |
| `shortName` | `"STR @ TRY"` | |
| `competitions` | `[ ... ]` | **only one** in practice |
| `status`, `venue`, `links` | | repeated or completed inside `competitions[0]` |

The detail lives in `competitions[0]`, never anywhere else: `competitors`,
`details`, `status`, `odds`, `broadcasts`, `attendance`, `notes`. The code
reads `competitions[0]` and falls back to the event for the date and the
state, because the two levels are not always filled together.

### The state: `competitions[0].status`

```json
{ "clock": 5400.0, "displayClock": "90'+6'", "period": 2,
  "type": { "id": "28", "name": "STATUS_FULL_TIME", "state": "post",
            "completed": true, "description": "Full Time",
            "detail": "FT", "shortDetail": "FT" } }
```

`state` only takes three values - `pre`, `in`, `post` - and it is the base of
`espn.phase_of()`. The detail sits in `type.name`, and it is not the same from
one sport to the next. Surveyed over about 6,800 matches:

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

Two things stand out. **Football and the other two do not name the end the
same way** (`STATUS_FULL_TIME` against `STATUS_FINAL`), hence reading `state`
rather than the name. And **a postponed, suspended or abandoned match is
announced as `post`**, like a finished one: without the name the program would
show a full-time card for a match that never kicked off. That is the whole
point of the `_STOPPED` list in `espn.py`.

The **in-play states could not be observed** at survey time: all 218 football
competitions were swept, not one match was being played. The names the code
recognises come from earlier surveys, and the list is deliberately wide
because an unknown name simply leaves the match "in progress" - so no card,
never a false card: `STATUS_FIRST_HALF`, `STATUS_HALFTIME`,
`STATUS_SECOND_HALF`, `STATUS_EXTRA_TIME_HALFTIME`, `STATUS_SHOOTOUT`,
`STATUS_IN_PROGRESS`, `STATUS_INTERMISSION`, `STATUS_END_PERIOD`,
`STATUS_END_OF_PERIOD`.

`displayClock` carries the minute of play as it is displayed: `"67'"`,
`"90'+6'"` in football - an apostrophe on **both** sides of the plus - and
`"12:34"` in hockey. Two shapes that do not read with the same reader.

### The two teams: `competitors[]`

Always two entries, told apart by `homeAway` (`"home"` / `"away"`), and **not
necessarily in that order**: the field is what counts, not the position.

| Field | Example | Note |
| --- | --- | --- |
| `homeAway` | `"home"` | the only safe way to know who is at home |
| `score` | `"2"` | a **string**, not an integer |
| `winner` | `false` | absent before the end |
| `form` | `"LWDLW"` | last five matches, football only |
| `records` | `[{"summary": "1-1-1"}]` | |
| `statistics` | possession, shots, corners... | football only, and never before kick-off |
| `team` | the object below | |

The team itself:

| Field | Example | Note |
| --- | --- | --- |
| `id` | `"170"` | the ESPN identifier, stable |
| `displayName` | `"Troyes"` | the readable name |
| `shortDisplayName`, `name`, `location`, `abbreviation` | `"TRY"` | four more spellings |
| `color`, `alternateColor` | `"0000bf"` | **no hash sign**, and sometimes absent |
| `logo` | `.../teamlogos/soccer/500/170.png` | in hockey: `.../nhl/500/scoreboard/col.png` |
| `logos` | array of `{href, rel}` | when `logo` is missing |

Football gives `alternateColor`, hockey does not; the colour is sometimes an
empty string. Nothing in there is guaranteed, and `crests.py` knows how to
fall back on the competition colour.

### The plays: `competitions[0].details`

This is where the three sports really diverge, and it is the project's only
genuine difference in reading.

**Football** publishes one entry per notable play, carried by **flags**:

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

The flags are mutually exclusive, except `penaltyKick` and `shootout` which
accompany a `scoringPlay`. A shoot-out kick is recognised by
`shootout: true` - and it carries `type.id` **104** where a penalty in open
play carries **98**. The full `type.id` table is in
[appendix A](#appendix-a---football-plays).

**Rugby** publishes the same array, **without a single flag**:

```json
{ "type": { "id": "1", "text": "try" },
  "clock": { "value": 434.0, "displayValue": "8'" },
  "team": { "id": "25986" },
  "athletesInvolved": [ { "id": "296203", "shortName": "G. Villiere",
                          "position": "W" } ] }
```

No `scoringPlay`, no `scoreValue`, no `ownGoal`: **four keys in total**, and
it is `type.id` that says what happened. Read with the football reader, a
rugby match would have no plays at all - which is exactly why
`_rugby_details()` exists. Table in
[appendix B](#appendix-b---rugby-and-hockey-plays).

**Hockey publishes nothing.** Over 798 finished matches surveyed, `details` is
absent every time - not empty: absent. We get the score, the clock and the
period, never the scorer. The card says so by saying nothing. (Hockey scorers
do exist elsewhere, though: see section 7.)

---

## 4. Teams

```
https://site.api.espn.com/apis/site/v2/sports/<sport>/<competition>/teams
https://site.api.espn.com/apis/site/v2/sports/<sport>/<competition>/teams/<id>
```

Used to validate what is typed into `--teams` and to answer `--list-teams`.
The response is buried three levels deep, and it is the only endpoint of the
set that is:

```
sports[0].leagues[0].teams[].team
```

The `team` object is the scoreboard one, plus `logos`. A few surveyed counts:
`fra.1` 18, `eng.1` 20, `nhl` 32, `rugby/270559` 14, `uefa.champions` 36,
`eng.fa` **124** - a cup open to the lower divisions does return everyone.
`?limit=` changes nothing: the list is complete by default.

A competition that does not answer returns an empty list rather than an
error: we do not block startup over a team catalogue.

---

## 5. Standings

```
https://site.api.espn.com/apis/v2/sports/<sport>/<competition>/standings
```

**`apis/v2`, not `apis/site/v2`.** The wrong address does exist and answers
200 - with a nearly empty object (`{"fullViewLink": ...}`), which looks like
an off-season when it is merely the wrong door. That is the mistake we do not
want to make twice, and it is noted in the code exactly where it is made.

### The shape

```json
{ "id": "710", "name": "French Ligue 1", "abbreviation": "FRA.1",
  "season": { "year": 2026, "displayName": "2026-27 French Ligue 1" },
  "seasons": [],
  "children": [
    { "name": "French Ligue 1 2026-27",
      "standings": { "seasonDisplayName": "2026-27 French Ligue 1 Standings",
                     "entries": [] } } ] }
```

`children` is **always a list**, even with a single element, and that is what
allows a league and a group stage to be handled by the same code:

| Competition | `children` |
| --- | --- |
| `soccer/fra.1` | 1 (the league) |
| `hockey/nhl` | 2 (the Eastern and Western conferences) |
| `soccer/fifa.world` | 12 (the groups) |
| `soccer/eng.fa` | **0** (a cup has no table) |

One row, `children[].standings.entries[]`:

```json
{ "team": { "id": "160", "displayName": "Paris Saint-Germain" },
  "note": { "color": "#81D6AC", "description": "Champions League", "rank": 1 },
  "stats": [ { "name": "gamesPlayed", "type": "gamesplayed",
               "displayName": "Games Played", "abbreviation": "GP",
               "value": 3.0, "displayValue": "3" } ] }
```

Three things to know about `stats`.

**It is a flat list, not an object**: you index it yourself. Each statistic
carries **two names** - `type` in lower case (`"gamesplayed"`) and `name` in
camel case (`"gamesPlayed"`) - and the two do not agree across sports. Rugby
counts its wins under `gamesWon`, football under `wins`: that is why
`_stats_of()` files them under both.

**`displayValue` carries the sign, `value` does not**: a goal difference of +4
arrives as `4.0` on one side and `"+4"` on the other. The string is what gets
displayed.

**The rank is not always there.** Football and rugby publish `rank`, hockey
only has `playoffSeed`. And the order of the list does not stand in for the
rank: a league arrives sorted, but a World Cup group arrives shuffled and an
NHL conference starts at its fourth seed.

The statistics available, by sport (surveyed):

| Sport | `stats[].name` |
| --- | --- |
| football | `gamesPlayed`, `wins`, `ties`, `losses`, `points`, `pointsFor`, `pointsAgainst`, `pointDifferential`, `ppg`, `rank`, `rankChange`, `deductions`, `advanced`, `overall` |
| hockey | `gamesPlayed`, `wins`, `losses`, `otLosses`, `overtimeLosses`, `overtimeWins`, `regWins`, `regLosses`, `shootoutWins`, `shootoutLosses`, `points`, `pointsFor`, `pointsAgainst`, `pointDifferential`, `playoffSeed`, `streak`, `clincher`, `gamesBehind`, `Home`, `Road`, `Last Ten Games`, `vs. Div.` |
| rugby | `gamesPlayed`, `gamesWon`, `gamesDrawn`, `gamesLost`, `points`, `pointsFor`, `pointsAgainst`, `pointsDifference`, `bonusPoints`, `bonusPointsTry`, `bonusPointsLosing`, `triesFor`, `triesAgainst`, `triesDifference`, `rank`, `playoffSeed`, `streak`, `winPercent` |

Three sports, three ways of counting: hockey has no draw but counts overtime
losses, rugby adds its bonus points and its tries, football has neither.
Manufacturing a draws column for hockey would be inventing a zero.

`note` dresses the row with a qualification zone and its colour
(`"Champions League"`, `"Relegation"`). Enough to paint a table; we do not
read it in an 80-column terminal.

### The parameters

| Parameter | Effect |
| --- | --- |
| `season=YYYY` | the table of a past season - `?season=2025` answers |
| `level=N` | group depth; `level=1` returns an object **with no `children`** |

The list of available seasons is in the response itself, under `seasons[]`,
each with its `types[].hasStandings`: enough to know what can be asked before
asking it.

---

## 6. The competition catalogue

Two ways of knowing what exists.

```
https://site.api.espn.com/apis/site/v2/leagues/dropdown?sport=soccer&limit=1000
```

Returns the complete list of a sport's competitions, each with its `slug`,
`name`, `logos` and - valuable - **`hasStandings`**. At survey time: **218**
football competitions, **19** rugby, **6** hockey. The full list is in
[appendix C](#appendix-c---competition-codes).

```
https://sports.core.api.espn.com/v2/sports
```

Returns ESPN's 17 sports: `australian-football`, `baseball`, `basketball`,
`cricket`, `field-hockey`, `football`, `golf`, `hockey`, `lacrosse`, `mma`,
`racing`, `rugby`, `rugby-league`, `soccer`, `tennis`, `volleyball`,
`water-polo`.

butbutbut opens only three of them, and the README says why: it is not a
technical limit, it is the program's model. A basket every thirty seconds is
not a notification.

---

## 7. A match summary

```
https://site.api.espn.com/apis/site/v2/sports/<sport>/<competition>/summary?event=<id>
```

One request per match, and a heavy response: `boxscore`, `rosters`, `leaders`,
`odds`, `videos`, `news`, `standings`, `commentary`... 430 kB for a football
match, 450 kB for an NHL one. butbutbut never calls it - a client following 36
competitions cannot afford that per match per round. But it is worth knowing
what is inside, because it holds **what the scoreboard does not give**.

In football, `keyEvents[]` (28 entries on the surveyed match) repeats the
scoreboard plays and adds the milestones - kick-off, half-time, substitutions
- with a readable `type.type` (`"kickoff"`). And `commentary[]` (127 entries)
is the minute-by-minute feed.

**In hockey, `plays[]` carries the scorers the scoreboard does not have.** On
one surveyed match, 302 plays of which 14 goals, each like this:

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

So: "hockey has no scorer" is true **of the scoreboard**, and false of the
source as a whole. What is missing is not the data, it is a network budget.
See section 12.

---

## 8. The core API

```
https://sports.core.api.espn.com/v2/sports/<sport>/leagues/<competition>/...
```

The internal API, and it answers just about everything:
`/seasons/2026/teams`, `/events`, `/events/<id>`,
`/events/<id>/competitions/<id>/plays`, `/groups`, `/rankings`, `/notes`. Two
traits set it apart:

- **it is hyperlinked**: a list does not contain the objects but
  `{"$ref": "http://..."}` entries to be followed one by one. Count 18
  requests for the 18 clubs of a Ligue 1;
- **it is paginated**: `count`, `pageIndex`, `pageSize`, `pageCount`, `items`,
  with `?limit=` and `?page=`.

It caches better (`max-age=900, stale-while-revalidate=7200`) but costs more
in use: the 302 plays of the NHL match above weigh 663 kB here against 450 kB
through `/summary`. For a desktop client `site.api` remains the right door;
`core` is for when you are after something the scoreboard does not publish.

A useful detail for guessing an address: `site.api` error messages sometimes
leak the matching `core` call, internal host included.

---

## 9. Images

Everything is on `a.espncdn.com`, as PNG, without authentication. The URLs
normally arrive in the payload (`team.logo`, `athlete.headshot`); the patterns
below only serve to build a URL from an identifier, which is what
`espn.logo_url()` does for the demonstration cards.

| Pattern | Example | Checked |
| --- | --- | --- |
| `/i/teamlogos/soccer/500/<id>.png` | `.../soccer/500/170.png` | 200, 500x500 |
| `/i/teamlogos/soccer/500-dark/<id>.png` | | 200, dark variant |
| `/i/teamlogos/nhl/500/<id>.png` | `.../nhl/500/1.png` | 200 - **the number works** |
| `/i/teamlogos/nhl/500/<abbrev>.png` | `.../nhl/500/bos.png` | 200, another rendition |
| `/i/teamlogos/nhl/500/scoreboard/<abbrev>.png` | | this is the one the payload serves |
| `/i/teamlogos/rugby/teams/500/<id>.png` | `.../500/25986.png` | 200 |
| `/i/leaguelogos/soccer/500/<id>.png` | `.../500/9.png` | 200 |
| `/i/headshots/<sport>/players/full/<id>.png` | | 200 **when the player has one** |
| anything unknown | | a clean 404 |

Hockey deserves a note: the code files its crests under the team number, and a
comment in the repository doubted that was the right key. Checked, **both
forms exist** and do return the right club - `nhl/500/1.png` is Boston,
`nhl/500/22.png` is Vancouver - it simply is not the same image as the
scoreboard's, which goes through `scoreboard/<abbrev>`. Headshots, on the
other hand, do not all exist: a player without a photo returns 404, and the
payload then omits the field.

**The resizer.** ESPN also serves images through a combiner that resizes
server-side:

```
https://a.espncdn.com/combiner/i?img=/i/teamlogos/soccer/500/170.png&h=80&w=80
```

The same crest weighs **44.7 kB at 500x500 and 6.0 kB at 80x80** - and the
card never shows it larger than a few dozen pixels. `&scale=crop` crops.

---

## 10. What butbutbut actually reads

Out of everything above, the program reads only a handful of fields. Here they
are, with the place that reads them - it is also the list `tools/canari.py`
watches.

| ESPN field | Read by | Used for |
| --- | --- | --- |
| `events[].id` | `espn.parse` | the identity of a match |
| `events[].competitions[0]` | `espn.parse` | everything else |
| `competitors[].homeAway` | `espn.parse` | who is at home |
| `competitors[].score` | `espn.parse` | **the score, hence the goal** |
| `competitors[].team.displayName` / `shortDisplayName` | `_team_name` | the name on the card |
| `competitors[].team.name` / `location` / `abbreviation` | `team_names` | matching `--teams` |
| `competitors[].team.color` / `alternateColor` | `team_colors` | the club colour |
| `competitors[].team.logo` / `logos[].href` | `team_logo` | the crest |
| `status.type.state` | `phase_of` | live, upcoming, finished |
| `status.type.name` | `phase_of` | half-time, postponement, abandonment |
| `status.type.shortDetail` / `detail` / `description` | `espn.parse` | the status line |
| `status.displayClock` | `espn.parse` | the minute of play |
| `competitions[0].date` | `_parse_date` | the kick-off time |
| `details[].type.id` / `text` | `_soccer_details`, `_rugby_details` | the nature of the play |
| `details[].scoringPlay` / `redCard` / `ownGoal` / `penaltyKick` / `shootout` | `_soccer_details` | dressing the card |
| `details[].clock.displayValue` | `_detail_common` | the minute of the goal |
| `details[].athletesInvolved[0].shortName` | `_detail_common` | the scorer |
| `leagues[0].name` / `abbreviation` | `espn.parse` | the name of a competition opened on the fly |
| `children[].standings.entries[].stats[]` | `_stats_of` | the table |

And above all, what it does **not** read: the score is never derived from the
plays. A score that goes up is a goal, even if `details` has not caught up -
which is what makes hockey, publishing no plays at all, followed just as well
as the rest.

---

## 11. The traps

The ones that have already cost something, or that would.

1. **`apis/v2` for standings, `apis/site/v2` for the rest.** The wrong address
   answers 200 with an empty object: a silent failure.
2. **`limit` defaults to 100** on the scoreboard, and the truncation is
   signalled nowhere.
3. **An unknown competition returns 400, not 404**, and an off-season returns
   200 with `events: []`. Do not confuse the two.
4. **The `User-Agent` can get the request refused**, in HTML, by Akamai. A 403
   is not a competition that does not exist.
5. **`score` is a string.**
6. **Colours have no hash sign** and are sometimes empty.
7. **`details` does not exist in hockey** and has **no flags at all** in
   rugby.
8. **`athletesInvolved` can be empty**: a goal with no published scorer is
   normal for a few seconds.
9. **The date sometimes arrives without seconds** (`2026-09-06T18:45Z`), which
   breaks a too-strict `strptime`.
10. **Stoppage-time minutes are written `90'+6'`**, an apostrophe on both
    sides of the plus. A reader that only accepts `90+6'` throws away half the
    late goals without breaking anything - it happened.
11. **The order of `children[].standings.entries` is not the ranking**, and
    hockey has no `rank` at all.
12. **No `ETag`, no `Last-Modified`**: conditional requests are out of reach.

---

## 12. What could be done with this

Four leads this survey opens, with their trade-off. The first one has already
shipped; the other three are waiting.

**Ask for gzip - done.** Eight times fewer bytes on the wire, for one line in
`headers()`, a decompression in `download()` and zero dependencies (`gzip` is
in the stdlib). It was the only traffic saving available, since conditional
requests are not; it has been in place since 1.10.0. The implementation trap
was worth the detour: a compressed stream is recognised by its **first two
bytes** and not by the `Content-Encoding` header, because a proxy that
decompresses on the way does not always think to remove the header - and
because a clear answer then goes down the same path with no special case.

**Hockey scorers.** They exist, in `/summary?event=<id>`, under
`plays[].participants[].type == "scorer"`. The cost is the problem: 450 kB per
match. A workable lead would be to call it **only after a goal is detected**
and **only for that match** - a few times an evening, not every round of the
loop. The hockey card would gain its scorer's name, and even the assists.

**The image combiner.** `combiner/i?img=...&h=80&w=80` divides a crest's
weight by seven, where `crests.py` downloads it at 500x500 today to display it
tiny. Reservation: it is a URL we build, where the project prefers the one the
source announces.

**Translated names.** Answered, and the answer is no: only Spanish and
Portuguese are served, French is not, and **team names are never translated**
in any language. So `i18n.py` keeps its job, and `teams.py` keeps matching on
the English labels.

---

## Appendix A - football plays

Surveyed over 7 competitions and 3 periods, about 3,300 plays. `type.id` is
stable, `type.text` is in English.

| `type.id` | `type.text` | `scoreValue` | Flag | Occurrences |
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

The code does **not** read those numbers in football: it reads the flags,
which are safer - an unheard-of goal variant is still a goal. The numbers are
here to understand, and to tell a shoot-out kick - **104** - from a penalty in
open play - **98** - by something other than the `shootout` flag.

A yellow card is never signalled: it is not a scoring event, and the card
would be noise.

---

## Appendix B - rugby and hockey plays

### Rugby: `competitions[0].details`

Surveyed over 5 competitions, 339 matches, 17,957 plays. **No flags at all**:
`type.id` is the only information, and the number of points does not come from
the source - the code knows it.

| `type.id` | `type.text` | Points | Read by butbutbut | Occurrences |
| --- | --- | --- | --- | --- |
| 1 | try | 5 | yes | 2585 |
| 2 | conversion | 2 | yes | 1923 |
| 3 | penalty goal | 3 | yes | 601 |
| 4 | drop goal | 3 | yes | 11 |
| 5 | yellow card | 0 | **no** | 442 |
| 6 | red card | 0 | yes | 42 |
| 7 | player substituted | 0 | no | 6183 |
| 8 | substitute on | 0 | no | 6167 |
| 37 | drop goal-missed | 0 | no | 3 |

The yellow card is left out on purpose: in rugby it is a ten-minute temporary
exclusion, not a sending-off, and confusing it with a red card would produce a
card that lies. `drop goal-missed` is a reminder of why the fallback table by
label matches **exactly** and not by prefix.

### Hockey: nothing in the scoreboard

`details` is absent on all 798 finished matches surveyed. The plays do exist
in `/summary?event=<id>` under `plays[]`, with these types:

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
| 31, 49, 55... | the penalties, one per offence |

---

## Appendix C - competition codes

The codes served by `leagues/dropdown` on 7 September 2026. The "standings"
column repeats `hasStandings`: a competition marked `no` will return an empty
`children` on `/standings`.

butbutbut's catalogue is a subset of this list; any other code opens on the
fly (`--leagues gre.1`, `--leagues hockey:mens-college-hockey`).

### Hockey (6)

| slug | name | standings |
| --- | --- | --- |
| `hockey-world-cup` | World Cup of Hockey | no |
| `mens-college-hockey` | NCAA Men's Ice Hockey | no |
| `nhl` | National Hockey League | yes |
| `olympics-mens-ice-hockey` | Men's Ice Hockey | no |
| `olympics-womens-ice-hockey` | Women's Ice Hockey | no |
| `womens-college-hockey` | NCAA Women's Hockey | no |

### Rugby (19)

| slug | name | standings |
| --- | --- | --- |
| `164205` | Rugby World Cup | yes |
| `17567` | Nations Championship | yes |
| `180659` | Six Nations | yes |
| `2009` | URBA Primera A | no |
| `242041` | Super Rugby Pacific | yes |
| `244293` | The Rugby Championship | yes |
| `267979` | Gallagher Prem | yes |
| `268565` | British and Irish Lions Tour | no |
| `270557` | United Rugby Championship | yes |
| `270559` | French Top 14 | no |
| `270563` | Mitre 10 Cup | yes |
| `271937` | European Rugby Champions Cup | yes |
| `272073` | European Rugby Challenge Cup | no |
| `282` | Olympic Men's 7s | yes |
| `283` | Olympic Women's Rugby Sevens | yes |
| `289234` | International Test Match | yes |
| `289237` | Women's Rugby World Cup | yes |
| `289262` | Major League Rugby | no |
| `289279` | URBA Top 14 | yes |

### Football (218)

| slug | name | standings |
| --- | --- | --- |
| `afc.asian.cup` | AFC Asian Cup | yes |
| `afc.champions` | AFC Champions League Elite | yes |
| `afc.champions_qual` | AFC Champions League Elite Qualifying | no |
| `afc.cup` | AFC Champions League Two | yes |
| `afc.cup_qual` | AFC Champions League Two Qualifying | no |
| `afc.cupq` | AFC Asian Cup Qualifiers | yes |
| `afc.saff.championship` | SAFF Championship | yes |
| `afc.w.asian.cup` | AFC Women's Asian Cup | yes |
| `aff.championship` | ASEAN Championship | yes |
| `arg.1` | Argentine Liga Profesional de Futbol | yes |
| `arg.2` | Argentine Nacional B | yes |
| `arg.3` | Argentine Primera B | yes |
| `arg.copa` | Copa Argentina | no |
| `arg.copa_de_la_superliga` | Argentine Copa de la Superliga | yes |
| `arg.supercopa` | Argentine Supercopa | no |
| `arg.supercopa.internacional` | Argentine Supercopa Internacional | no |
| `arg.trofeo_de_la_campeones` | Argentine Trofeo de Campeones | no |
| `aus.1` | Australian A-League Men | yes |
| `aus.w.1` | Australian A-League Women | yes |
| `aut.1` | Austrian Bundesliga | yes |
| `bel.1` | Belgian Pro League | yes |
| `bel.promotion.relegation` | Belgian Pro League Promotion/Relegation Playoffs | no |
| `bol.1` | Bolivian Liga Profesional | yes |
| `bol.copa` | Copa Bolivia | yes |
| `bol.ply.rel` | Bolivian Liga Profesional Promotion/Relegation Playoffs | no |
| `bra.1` | Brazilian Serie A | yes |
| `bra.2` | Brazilian Serie B | yes |
| `bra.camp.carioca` | Brazilian Campeonato Carioca | yes |
| `bra.camp.gaucho` | Brazilian Campeonato Gaucho | yes |
| `bra.camp.mineiro` | Brazilian Campeonato Mineiro | yes |
| `bra.camp.paulista` | Brazilian Campeonato Paulista | yes |
| `bra.copa_do_brazil` | Copa do Brasil | no |
| `bra.supercopa_do_brazil` | Brazilian Supercopa Rei | no |
| `caf.champions` | CAF Champions League | yes |
| `caf.championship` | African Nations Championship | yes |
| `caf.confed` | CAF Confederation Cup | yes |
| `caf.cosafa` | COSAFA Cup | yes |
| `caf.nations` | Africa Cup of Nations | yes |
| `caf.nations_qual` | Africa Cup of Nations Qualifying | yes |
| `caf.w.nations` | Women's Africa Cup of Nations | yes |
| `campeones.cup` | Campeones Cup | no |
| `can.w.nsl` | Northern Super League | yes |
| `chi.1` | Chilean Primera Division | yes |
| `chi.1.promotion.relegation` | Chilean Primera Division Promotion/Relegation Playoffs | no |
| `chi.copa_chi` | Copa Chile | yes |
| `chi.super_cup` | Chilean Supercopa | no |
| `chn.1` | Chinese Super League | yes |
| `chn.1.promotion.relegation` | Chinese Super League Promotion/Relegation Playoffs | no |
| `club.friendly` | Club Friendly | no |
| `col.1` | Colombian Primera A | yes |
| `col.copa` | Copa Colombia | yes |
| `col.superliga` | Colombian Superliga | no |
| `concacaf.central.american.cup` | Concacaf Central American Cup | yes |
| `concacaf.champions` | Concacaf Champions Cup | no |
| `concacaf.champions_cup` | CONCACAF Champions Cup | no |
| `concacaf.confederations_playoff` | Concacaf Cup | no |
| `concacaf.gold` | Concacaf Gold Cup | yes |
| `concacaf.gold_qual` | Concacaf Gold Cup Qualifying | no |
| `concacaf.leagues.cup` | Leagues Cup | yes |
| `concacaf.nations.league` | Concacaf Nations League | yes |
| `concacaf.u23` | CONCACAF U23 Tournament | yes |
| `concacaf.w.champions_cup` | Concacaf W Champions Cup | yes |
| `concacaf.w.gold` | Concacaf W Gold Cup | yes |
| `concacaf.womens.championship` | Concacaf W Championship | no |
| `conmebol.america` | Copa America | yes |
| `conmebol.america.femenina` | Copa America Femenina | yes |
| `conmebol.libertadores` | CONMEBOL Libertadores | yes |
| `conmebol.recopa` | CONMEBOL Recopa | no |
| `conmebol.sudamericana` | CONMEBOL Sudamericana | yes |
| `crc.1` | Costa Rican Primera Division | yes |
| `den.1` | Danish Superliga | yes |
| `ecu.1` | LigaPro Ecuador | yes |
| `eng.1` | English Premier League | yes |
| `eng.2` | English League Championship | yes |
| `eng.3` | English League One | yes |
| `eng.4` | English League Two | yes |
| `eng.5` | English National League | yes |
| `eng.charity` | English FA Community Shield | no |
| `eng.fa` | English FA Cup | no |
| `eng.fa_qual` | English FA Cup Qualifying | no |
| `eng.league_cup` | English Carabao Cup | no |
| `eng.trophy` | English EFL Trophy | yes |
| `eng.w.1` | English Women's Super League | yes |
| `eng.w.fa` | English Women's FA Cup | no |
| `eng.w.league_cup` | English Women's League Cup | yes |
| `eng.w.promotion.relegation` | English Women's Super League Promotion/Relegation Playoff | no |
| `esp.1` | Spanish LALIGA | yes |
| `esp.2` | Spanish LALIGA 2 | yes |
| `esp.copa_de_la_reina` | Spanish Copa de la Reina | no |
| `esp.copa_del_rey` | Spanish Copa del Rey | no |
| `esp.joan_gamper` | Trofeo Joan Gamper | no |
| `esp.super_cup` | Spanish Supercopa | no |
| `esp.w.1` | Spanish Liga F | yes |
| `fifa.concacaf.olympicsq` | Men's Olympic Qualifying Playoff | yes |
| `fifa.conmebol.olympicsq` | CONMEBOL Pre-Olympic Tournament | yes |
| `fifa.cwc` | FIFA Club World Cup | yes |
| `fifa.friendly` | International Friendly | no |
| `fifa.friendly.w` | Women's International Friendly | no |
| `fifa.friendly_u21` | Under-21 International Friendly | no |
| `fifa.intercontinental.cup` | Intercontinental Cup (India) | yes |
| `fifa.intercontinental_cup` | FIFA Intercontinental Cup | no |
| `fifa.olympics` | Men's Olympic Soccer Tournament | yes |
| `fifa.shebelieves` | SheBelieves Cup | yes |
| `fifa.w.champions_cup` | FIFA Women's Champions Cup | no |
| `fifa.w.concacaf.olympicsq` | Concacaf Women's Olympic Qualifying | yes |
| `fifa.w.olympics` | Women's Olympic Soccer Tournament | yes |
| `fifa.wcq.ply` | FIFA World Cup Qualifying - Playoff Tournament | no |
| `fifa.world` | FIFA World Cup | yes |
| `fifa.world.u17` | FIFA Under-17 World Cup | yes |
| `fifa.world.u20` | FIFA Under-20 World Cup | yes |
| `fifa.worldq.afc` | FIFA World Cup Qualifying - AFC | yes |
| `fifa.worldq.caf` | FIFA World Cup Qualifying - CAF | yes |
| `fifa.worldq.concacaf` | FIFA World Cup Qualifying - Concacaf | yes |
| `fifa.worldq.conmebol` | FIFA World Cup Qualifying - CONMEBOL | yes |
| `fifa.worldq.ofc` | FIFA World Cup Qualifying - OFC | yes |
| `fifa.worldq.uefa` | FIFA World Cup Qualifying - UEFA | yes |
| `fifa.wwc` | FIFA Women's World Cup | yes |
| `fifa.wwcq.ply` | FIFA Women's World Cup Qualifying - Playoff Tournament | no |
| `fifa.wworld.u17` | FIFA Under-17 Women's World Cup | yes |
| `fifa.wworldq.uefa` | FIFA Women's World Cup Qualifying - UEFA | yes |
| `fra.1` | French Ligue 1 | yes |
| `fra.1.promotion.relegation` | French Ligue 1 Promotion/Relegation Playoffs | no |
| `fra.2` | French Ligue 2 | yes |
| `fra.coupe_de_france` | Coupe de France | no |
| `fra.super_cup` | French Trophee des Champions | no |
| `fra.w.1` | French Premiere Ligue | yes |
| `friendly.emirates_cup` | Emirates Cup | no |
| `ger.1` | German Bundesliga | yes |
| `ger.2` | German 2. Bundesliga | yes |
| `ger.2.promotion.relegation` | German Bundesliga 2. Promotion/Relegation Playoffs | no |
| `ger.dfb_pokal` | German Cup | no |
| `ger.playoff.relegation` | German Bundesliga Promotion/Relegation Playoff | no |
| `ger.super_cup` | German Supercup | no |
| `global.arnold.clark_cup` | Arnold Clark Cup | yes |
| `global.club_challenge` | CONMEBOL-UEFA Club Challenge | no |
| `global.finalissima` | CONMEBOL-UEFA Cup of Champions | no |
| `global.gulf_cup` | Arabian Gulf Cup | yes |
| `global.pinatar_cup` | Pinatar Cup | yes |
| `global.u20.intercontinental_cup` | CONMEBOL-UEFA U20 Intercontinental Cup | no |
| `global.w.finalissima` | CONMEBOL-UEFA Women's Cup of Champions | no |
| `gre.1` | Greek Super League | yes |
| `gua.1` | Guatemalan Liga Nacional | yes |
| `hon.1` | Honduran Liga Nacional | yes |
| `ind.1` | Indian Super League | yes |
| `ita.1` | Italian Serie A | yes |
| `ita.2` | Italian Serie B | yes |
| `ita.coppa_italia` | Coppa Italia | no |
| `ita.super_cup` | Italian Supercoppa | no |
| `jpn.1` | Japanese J.League | yes |
| `jpn.world_challenge` | Japanese J.League World Challenge | no |
| `ksa.1` | Saudi Pro League | yes |
| `ksa.kings.cup` | Saudi King's Cup | no |
| `mex.1` | Mexican Liga BBVA MX | yes |
| `mex.2` | Mexican Liga de Expansion MX | yes |
| `mex.campeon` | Mexican Campeon de Campeones | no |
| `ned.1` | Dutch Eredivisie | yes |
| `ned.2` | Dutch Keuken Kampioen Divisie | yes |
| `ned.3.promotion.relegation` | Dutch Tweede Divisie Promotion/Relegation Playoffs | no |
| `ned.cup` | Dutch KNVB Beker | no |
| `ned.playoff.relegation` | Dutch Eredivisie Promotion/Relegation Playoffs | no |
| `ned.supercup` | Dutch Johan Cruyff Shield | no |
| `ned.w.1` | Dutch Vrouwen Eredivisie | yes |
| `ned.w.knvb_cup` | Dutch KNVB Beker Vrouwen | no |
| `nonfifa` | Non-FIFA Friendly | no |
| `nor.1` | Norwegian Eliteserien | yes |
| `nor.1.promotion.relegation` | Norwegian Eliteserien Promotion/Relegation Playoffs | no |
| `par.1` | Paraguayan Primera Division | yes |
| `par.1.supercopa` | Paraguayan Supercopa | no |
| `per.1` | Peruvian Liga 1 | yes |
| `por.1` | Portuguese Primeira Liga | yes |
| `por.1.promotion.relegation` | Portuguese Primeira Liga Promotion/Relegation Playoffs | no |
| `por.taca.portugal` | Taca de Portugal | no |
| `rsa.1` | South African Premiership | yes |
| `rus.1` | Russian Premier League | yes |
| `rus.1.promotion.relegation` | Russian Premier League Relegation/Promotion Playoffs | no |
| `sco.1` | Scottish Premiership | yes |
| `sco.1.promotion.relegation` | Scottish Premiership Promotion/Relegation Playoffs | no |
| `sco.2` | Scottish Championship | yes |
| `sco.2.promotion.relegation` | Scottish Championship Promotion/Relegation Playoffs | no |
| `sco.challenge` | Scottish League Challenge Cup | yes |
| `sco.cis` | Scottish League Cup | yes |
| `sco.tennents` | Scottish Cup | no |
| `sco.tennents_qual` | Scottish Cup Qualifying | no |
| `slv.1` | Salvadoran Primera Division | yes |
| `swe.1` | Swedish Allsvenskan | yes |
| `swe.1.promotion.relegation` | Swedish Allsvenskan Promotion/Relegation Playoffs | no |
| `tur.1` | Turkish Super Lig | yes |
| `uefa.champions` | UEFA Champions League | yes |
| `uefa.champions_qual` | UEFA Champions League Qualifying | no |
| `uefa.euro` | UEFA European Championship | yes |
| `uefa.euro.u19` | UEFA European Under-19 Championship | yes |
| `uefa.euro_u21` | UEFA European Under-21 Championship | yes |
| `uefa.euro_u21_qual` | UEFA European Under-21 Championship Qualifying | yes |
| `uefa.europa` | UEFA Europa League | yes |
| `uefa.europa.conf` | UEFA Conference League | yes |
| `uefa.europa.conf_qual` | UEFA Conference League Qualifying | no |
| `uefa.europa_qual` | UEFA Europa League Qualifying | no |
| `uefa.euroq` | UEFA European Championship Qualifying | yes |
| `uefa.nations` | UEFA Nations League | yes |
| `uefa.super_cup` | UEFA Super Cup | no |
| `uefa.w.europa` | UEFA Women's Europa Cup | no |
| `uefa.w.nations` | UEFA Women's Nations League | yes |
| `uefa.wchampions` | UEFA Women's Champions League | yes |
| `uefa.wchampions_qual` | UEFA Women's Champions League Qualifying | no |
| `uefa.weuro` | UEFA Women's European Championship | yes |
| `uru.1` | Liga AUF Uruguaya | yes |
| `uru.2` | Segunda Division de Uruguay | yes |
| `usa.1` | MLS | yes |
| `usa.ncaa.m.1` | NCAA Men's Soccer | no |
| `usa.ncaa.w.1` | NCAA Women's Soccer | no |
| `usa.nwsl` | NWSL | yes |
| `usa.nwsl.cup` | NWSL Challenge Cup | no |
| `usa.open` | U.S. Open Cup | no |
| `usa.usl.1` | USL Championship | yes |
| `usa.usl.l1` | USL League One | yes |
| `usa.usl.l1.cup` | USL Cup | yes |
| `usa.w.usl.1` | USL Super League | yes |
| `ven.1` | Venezuelan Primera Division | yes |

---

## Appendix D - re-checking this document

None of the above is guaranteed: it is a survey, not a contract. Here is what
it takes to redo it, with the standard library only.

The scoreboard, raw:

```bash
curl -s -H 'User-Agent: butbutbut/1.9.0 (+https://github.com/boubou666/butbutbut)' \
  'https://site.api.espn.com/apis/site/v2/sports/soccer/fra.1/scoreboard' | head -c 400
```

The headers, for the cache and `ETag` question:

```bash
curl -sI -H 'User-Agent: butbutbut/1.9.0 (+https://github.com/boubou666/butbutbut)' \
  'https://site.api.espn.com/apis/site/v2/sports/soccer/fra.1/scoreboard'
```

A sport's plays, counted by type - this is how appendices A and B were made:

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

A sport's competition catalogue, which produced appendix C:

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

And above all, the program that does this work every day without being asked:

```bash
python tools/canari.py
```

The canary queries the real source and checks that **every key read by
`butbutbut/espn.py` is still there, and of the right type**. It is the one
that will catch a drift before this document does, because it runs in the
daily CI (`.github/workflows/canari.yml`) while this file does not. Should the
two disagree, **the canary is right**: it has just spoken to the source, this
document dates from 7 September 2026.
