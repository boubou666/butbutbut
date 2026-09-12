![Two stunned supporters point at five screens all showing a goal](https://raw.githubusercontent.com/boubou666/butbutbut/main/docs/banniere.png)

*This project is also documented in [French](README.md).*

# butbutbut

[![ci](https://github.com/boubou666/butbutbut/actions/workflows/ci.yml/badge.svg)](https://github.com/boubou666/butbutbut/actions/workflows/ci.yml)
[![release](https://img.shields.io/github/v/release/boubou666/butbutbut)](https://github.com/boubou666/butbutbut/releases)
[![python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![pypi](https://img.shields.io/pypi/v/butbutbut)](https://pypi.org/project/butbutbut/)
[![licence](https://img.shields.io/badge/licence-MIT-green)](https://github.com/boubou666/butbutbut/blob/main/LICENSE)

A goal in **Ligue 1**, the **Premier League**, **LaLiga**, **Serie A** or the
**Bundesliga**: the sound fires, and a card appears in the bottom-right corner
of your screen with the score and the scorer.

![Three cards stacked in the bottom-right corner of the screen](https://raw.githubusercontent.com/boubou666/butbutbut/main/docs/cartes.png)

Every team wears its **crest**, the team that has just scored and its number
switch to their **club colour**, the vertical stripe keeps the competition's
own, and the scorer's name stands out in white. Two goals at the same time
don't tread on each other: the cards stack up from the corner. The key moments
of a match (kick-off, half-time, restart, full-time) get a quieter card of
their own, with no sound: that's the third one above.

**Ice hockey** and **rugby union** are in the catalogue too, on request:
`butbutbut --leagues nhl,top14`. Football stays the absolute default, nothing
invites itself. See [Sports](#sports).

Like [doot](https://github.com/boubou666/doot): **zero dependencies**, nothing
but the Python standard library, and it runs on Windows, macOS and Linux.

---

## Installation

### With pipx, without cloning (every system)

```bash
pipx install butbutbut
butbutbut
```

`pip install --user butbutbut` does the same thing. Both commands, `butbutbut`
and `but`, land in your PATH, and the sound ships inside the package: zero
dependencies, nothing else to download.

What pipx does not do, on the other hand: **start automatically** when you log
in. For that, use the scripts below.

> This method will only work from the first version pushed to PyPI onwards.
> The repository is ready; one step remains on the pypi.org side:
> [Publishing to PyPI](#publishing-to-pypi).

### Linux (Arch, Debian/Ubuntu, Fedora, openSUSE...) and macOS

```bash
git clone https://github.com/boubou666/butbutbut
cd butbutbut
./install.sh
```

Options: `--no-autostart`, `--leagues l1,pl`, `--position top-right`,
`--interval 25`.

The script installs the command into `~/.local/bin`, then enables automatic
start at login: a **systemd user unit** on Linux, a **LaunchAgent** on macOS,
an autostart `.desktop` entry as a last resort.

### Windows 10/11

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

Options: `-NoAutostart`, `-Leagues "l1,pl"`, `-Position top-right`,
`-Interval 25`. No admin rights needed: everything goes into
`%LOCALAPPDATA%\Programs\butbutbut` and a shortcut is dropped into the Startup
folder.

### Arch Linux (native package)

```bash
cd packaging && makepkg -si
systemctl --user reenable butbutbut.service
systemctl --user restart butbutbut.service
```

### Without installing anything

```bash
python -m butbutbut --test 3
```

---

## Usage

```bash
butbutbut                     # watch in the background (the default)
butbutbut --speak             # ... and say the goal out loud, on top of the sound
butbutbut --test              # one demo card
butbutbut --test 3            # three cards, to see them stack
butbutbut --scores            # today's fixtures in the terminal
butbutbut --next              # the fixtures to come, grouped by day
butbutbut --table             # the table of the competitions you follow
butbutbut --table om          # ... Marseille's, with their row highlighted
butbutbut --list              # the competitions you can watch
butbutbut --list-teams        # the teams in the competitions you follow
butbutbut --status            # daemon, last poll, matches in play, sound, screens
butbutbut --today             # the goals reported today
butbutbut --week              # the last 7 days
butbutbut --month             # the last 30 days
butbutbut --since 2026-09-01  # since that date
butbutbut --top-scorers       # the ranking of the scorers seen going by
butbutbut --stats             # the shapes hidden in the log
butbutbut --export csv        # the log as data, for a spreadsheet
butbutbut --record m.jsonl    # watch, and box up the raw polls as well
butbutbut --replay m.jsonl    # replay a recording, cards and sounds included
butbutbut --stop              # stop the daemon
butbutbut --check-update      # is there a newer version?
butbutbut --update            # fetch, reinstall, restart the daemon
butbutbut --update --dev      # same, but the tip of the main branch
butbutbut --test-hook         # try the --on-goal command out
butbutbut --paths             # where the data and the log live
butbutbut --write-config      # write an example configuration file
butbutbut --screens           # the screens detected
```

The command also answers to `but`, for short.

### Choosing the competitions

By default: the big five leagues. `--leagues` picks some, `--exclude` drops
some:

```bash
butbutbut --leagues l1,pl                 # only these two
butbutbut --exclude liga,seriea           # the big 5 minus two
butbutbut --leagues l1,ligue2,ucl,cdf     # Ligue 1 + Ligue 2 + UCL + Coupe de France
butbutbut --leagues all                   # the whole football catalogue
butbutbut --leagues big5                  # the big 5, explicitly
butbutbut --leagues l1f,wsl               # women's football
butbutbut --leagues nhl,top14             # and outside football
butbutbut --leagues all-sports            # really everything
```

The catalogue goes well beyond the big five: **36 football competitions**
checked against the source, among them

| Family | Examples (accepted names) |
| --- | --- |
| European cups | `ucl`/`c1`, `uel`/`europa`, `uecl`/`conference`, `supercoupe` |
| National teams | `cdm`/`mondial`, `nations`, `qualifs` |
| Second tiers | `ligue2`/`l2`, `championship`, `serieb`, `bundesliga2`, `liga2` |
| Europe | `portugal`, `eredivisie`, `belgique`, `superlig`, `ecosse` |
| Domestic cups | `cdf`/`coupedefrance`, `facup`, `carabao`, `copa`, `coppa`, `dfb` |
| Outside Europe | `mls`, `ligamx`, `bresil`, `argentine`, `saudi`, `jleague`, `libertadores` |

`butbutbut --list` prints the full catalogue with the aliases.

**And a competition that isn't in it?** Pass its ESPN code straight through,
it will be followed all the same:

```bash
butbutbut --leagues gre.1        # Greek Super League
butbutbut --leagues aus.1,den.1  # A-League, Danish Superliga
```

The name shown on the card is then whatever the source announces, picked up on
the first poll (`gre.1` becomes "GREEK SUPER LEAGUE").

> A word of warning all the same: `--leagues all` means 36 endpoints to poll.
> The adaptive polling rate does most of the work (a competition with no
> fixture is only re-read every 5 minutes), but do stay reasonable.

### Women's football

butbutbut follows **14 women's competitions**, served from the same place and
in the same shape as the rest: a Liga F goal reads exactly like a LaLiga goal,
scorer, minute, own goal and penalty included. Their absence until now was not
a judgement call, it was a blind spot.

```bash
butbutbut --leagues l1f,wsl            # Premiere Ligue and the Women's Super League
butbutbut --leagues uclf               # the Women's Champions League
butbutbut --leagues feminines          # all 14 at once
butbutbut --leagues l1,l1f             # both Ligue 1s, together
```

| Family | Accepted names |
| --- | --- |
| Leagues | `wsl`/`plf`, `ligaf`, `l1f`/`d1f`, `eredivisief`, `nwsl` |
| European cups | `uclf`/`c1f`/`uwcl`, `uelf`/`europaf` |
| National teams | `cdmf`/`mondialf`, `nationsf`, `qualifsf` |
| Domestic cups | `facupf`, `leaguecupf`, `reina` |
| Outside Europe | `concacaff` |

#### The alias rule: an `f` at the end

**The men's word, plus an `f`.** `l1` gives `l1f`, `pl` gives `plf`, `liga`
gives `ligaf`, `ucl` gives `uclf`, `cdm` gives `cdmf`, `facup` gives `facupf`.
There is nothing else to remember, and it is the one point of this piece of
work that really called for a decision.

What had to be avoided is **a word that changes meaning depending on what you
follow**. `psg` already names a team, `l1` names Ligue 1: the day `l1` came to
mean "both Ligue 1s", nobody would know what their own configuration file
does - least of all six months later. Here, no word already taken moves. `l1`
is Ligue 1, today and tomorrow.

The `f` did not come out of nowhere: it is the marker everyone already writes,
from TV listings ("France F") to the official name of the Spanish top flight,
which is called **Liga F**. A competition with a name of its own answers to
that name as well - `wsl`, `nwsl`, `uwcl`, `reina` - and that is usually the
one you type first.

The card label follows the same rule, for the same reason. The French women's
top flight is officially called "Premiere Ligue"; shown as such, at two in the
morning, it reads as "Premier League". So the card says **PREMIERE LIGUE F**.

#### What `--leagues all` does not take

**`all` is still the men's catalogue**, and it is the same judgement call as
for hockey, word for word: someone who typed `--leagues all` yesterday must
not find themselves, after a mere update, with cards for matches they never
asked for. An update does not change what you follow. And `all` is already 36
endpoints; pouring the rest into it would make 60 without that being a choice.

So they are asked for, in a single word:

```bash
butbutbut --leagues all              # 36 competitions, the same as before
butbutbut --leagues feminines        # the 14 women's ones (or footf, women)
butbutbut --leagues all,feminines    # the 50
butbutbut --leagues all-sports       # really everything, other sports included
```

`all-sports` takes them, just as it takes hockey and rugby: that is what it
promises, and nobody types it by accident.

#### What the source publishes, and what it does not

The women's catalogue is **the mirror of the men's one**: a women's
competition gets in when its men's counterpart is already there. That rule
does all the sorting, and it explains the absences without having to justify
them one by one - there is no women's Euro here because there is no Euro at
all, and the W Gold Cup will wait for the Gold Cup. They do exist at the
source, they were checked, and the escape hatch opens them anyway:

```bash
butbutbut --leagues uefa.weuro            # the Women's Euro
butbutbut --leagues fifa.w.olympics       # the Olympic tournament
butbutbut --leagues aus.w.1,can.w.nsl     # A-League Women, Northern Super League
```

Two gaps, however, are not ours: **Italy and Germany have no women's
equivalent at the source**. `ita.w.1` and `ger.w.1` answer 400, while Serie A
and the Bundesliga have been in the catalogue since day one. We do not follow
what is not published.

And nothing here will tell you when they show up: the test suite never touches
the network, and the test guarding those two slugs guards the CATALOGUE - it
stops anyone from adding them untried, which would give an unreachable
competition on every poll. So it is a manual check that answers, and it fits on
one line:

```bash
butbutbut --scores --leagues ita.w.1
```

`--scores`, `--next` and `--table` work on them like anywhere else. The table
does have a per-sport notion of columns (see "The columns follow the sport"):
a women's competition is football, so it counts draws just like Ligue 1 -
checked, not assumed.

#### A women's team carries its club's name

The source writes "Paris Saint-Germain" in `fra.w.1` just as in `fra.1`,
"Arsenal" in the WSL just as in the Premier League. Since name matching works
on the labels, `--teams psg` therefore catches **both of the club's teams** as
soon as you follow both competitions.

That is the right answer rather than a defect: someone who follows PSG follows
PSG. Nothing in the name would allow a distinction anyway, and wanting one
would mean a hand-written list of women's teams, which would age badly. What
separates the two cards is the competition, and the header is what announces
it. When you only want one of the two, `--leagues` is already enough:
following `l1f` alone does not bring up the men's goals.

---

## Sports

butbutbut also follows **ice hockey** and **rugby union**. Neither invites
itself: football stays the absolute default, and plain `butbutbut` still
follows the big five leagues and nothing else.

```bash
butbutbut --leagues nhl                 # the NHL
butbutbut --leagues top14,6nations      # Top 14 and the Six Nations
butbutbut --leagues l1,nhl              # both at once
butbutbut --leagues hockey              # every hockey competition in the catalogue
butbutbut --leagues rugby               # every rugby competition in the catalogue
```

| Sport | Competitions (accepted names) |
| --- | --- |
| Ice hockey | `nhl`/`lnh` |
| Rugby union | `6nations`/`tournoi`, `top14`, `prem`, `urc`, `champions-cup`, `trc`, `superrugby`, `rwc`, `testmatch` |

### What `all` means

**`--leagues all` is still the men's football catalogue**, exactly what it
meant before. Two reasons, and the first one is enough:

- **nobody asked for the NHL.** Someone who typed `--leagues all` to follow
  domestic cups must not find themselves, after a mere update, with hockey
  cards at two in the morning. An update does not change what you follow;
- `all` is already 36 endpoints. Pouring the rest into it would make 60
  without that being a choice.

The same reasoning keeps women's football out of `all` (see "Women's
football"): the rule is not about the sport, it is about the promise made to
the word.

For really everything: `--leagues all-sports` (or `tous-sports`). And
`--leagues foot` means the men's football catalogue, just like `all`.

### Why these sports, and not basketball

butbutbut's model fits in one sentence: **a score going up is an event worth a
sound**. A sport only gets in if it fits that sentence.

| Sport | Rhythm | Verdict |
| --- | --- | --- |
| Football | a goal every ~45 min | the default |
| Ice hockey | a goal every ~10 min | perfect fit |
| Rugby union | 5 to 8 scoring actions a match, and they are not equal | perfect fit |
| Basketball | **a basket every 20 to 30 s** | declined |

A card and a stadium horn at the rhythm of an NBA game (some 220 points) are
no longer a notification, they are a fire alarm: after ten minutes you mute the
sound, after twenty you uninstall. Making basketball bearable would mean
**changing the model**, not adding a line to the catalogue: it would have to
report only what matters - a decisive three-pointer, a lead that flips, the
last two minutes of a close game - hence judge how important an action is,
hence read something other than the score. That is a different program.
`--leagues basketball:nba` is therefore refused, with that reason spelled out.

The same reasoning declines handball (60 goals a match) and tennis (a score
that is not an integer going up). American football and baseball would land in
the right rhythm but not in the right model: a touchdown is worth 6 points and
then 1 more a minute later, and a score going up by 6 then by 1 would make two
cards for a single action.

### The wording follows the sport

A hockey goal is not a rugby try, and a try is worth five points: the title,
the scorer line and the delta follow the sport, in all five languages.

```
TRY!   TOP 14                                                 63'
Stade Toulousain      19 - 14      Stade Francais
Try by A. Dupont
```

| | Football | Hockey | Rugby |
| --- | --- | --- | --- |
| A score going up | `GOAL!` | `GOAL!` | `TRY!`, `CONVERSION`, `PENALTY GOAL`, `DROP GOAL` |
| Start of play | `KICK-OFF` | `PUCK DROP` | `KICK-OFF` |
| Break | `HALF-TIME` | `END OF PERIOD` | `HALF-TIME` |
| Score corrected | `GOAL DISALLOWED` | `GOAL DISALLOWED` | `POINTS REMOVED` |

A hockey goal **is** a goal: hockey only rewords what genuinely differs, namely
its breaks - it has no half-time, it has two breaks between three periods.
Rugby keeps football's wording for the run of play (it does have two halves)
and only brings its own scoring actions.

### What each sport actually publishes

All three were checked against the source, endpoint by endpoint. They do not
say the same things, and butbutbut never pretends otherwise.

| | Football | Hockey | Rugby |
| --- | --- | --- | --- |
| Score, clock, phase | yes | yes | yes |
| Crest, club colours | yes | yes | yes (a single colour) |
| Event list | yes | **no** (see below) | yes, but with no flags |
| Scorer, minute of the action | yes | yes, via the match summary | yes |
| Assists | no | **yes** | no |
| Statistics on the full-time card | yes | no (see below) | no |
| Red cards (`--red-cards`) | yes | not applicable | yes |
| Table (`--table`) | yes | yes, per conference | yes, bonus points included |

**Hockey publishes no event list in the scoreboard** - not during the game,
not after it. Its scorers live elsewhere, in the match summary, a **450 kB**
response that no client following 36 competitions can ask for every round of
the loop. So it is asked for **after a goal, and only for the match
concerned**: six or seven times per match, never every twenty-five seconds. The
hockey card gains its scorer, and its two assists on a line of their own.

This is the one request in the program that slips between a detected goal and
the card announcing it, so it gets its own ceiling: **1.5 s**, where a
scoreboard is allowed eight. Past that - or if the summary does not answer, or
names nobody - the card goes out as before, with the score and the minute, and
the log says why. Better an honest card than an invented name; and better the
previous scorer nowhere than on the next goal's card, so the name shown is that
of the nth goal of the team that has just reached n, and only if the summary
counts exactly as many as the scoreboard.

The end-of-match card lists both sides' scorers, as in football, on one
condition: that the list explains the score exactly. A summary missed during
the match therefore leaves a silent end card rather than a list with holes.

**Rugby publishes everything, but without a single flag**: where football marks
a goal with `scoringPlay` and a sending-off with `redCard`, rugby only gives a
`type.id` (1 try, 2 conversion, 3 penalty goal, 4 drop goal, 6 red card). Read
with football's reader, a rugby match would have no events at all - which is
why it has its own.

**All three publish team statistics, and not remotely the same ones.**
Football gives nine per side, always the same, among them the possession and
the shots on target that end up on the
[full-time card](#the-key-moments-of-a-match). Hockey gives six, two of which
are **season** totals mixed in with the match numbers: "551 goals" beside a
3-2 means nothing. Rugby gives 193 in the Six Nations and **none** in the Top
14, the Premiership, the URC or Super Rugby - a line that would only say
something in one competition out of five would be a lottery. So both keep
quiet, and that is a choice, not an oversight.

And **whatever does not apply switches itself off**: `--red-cards` on hockey
does not crash, it simply finds nothing to report, the source publishing no
sanctions. Rugby's yellow card is deliberately ignored: it is a ten-minute
temporary exclusion, not a sending-off.

### An ESPN code in another sport

The escape hatch works everywhere. With no prefix it is football - that is what
`--leagues gre.1` has always meant, and it does not change. To aim at another
sport, prefix it with the sport's name:

```bash
butbutbut --leagues gre.1                        # football (implied)
butbutbut --leagues hockey:mens-college-hockey   # college hockey
butbutbut --leagues rugby:270565                 # a rugby competition outside the catalogue
butbutbut --leagues hockey/nhl                   # the URL's "/" works too
```

The competition takes the name the source announces on the first poll, just
like in football.

### Following only certain teams

```bash
butbutbut --teams om,psg                    # these two clubs and nothing else
butbutbut --teams "real madrid" --leagues liga,ucl
butbutbut --exclude-teams psg               # everything except PSG
```

A match counts **as soon as either of the two teams** is in it: following OM
also means wanting to know when OM concedes. The filter applies to goals just
as it does to the key-moment cards, and to `--scores` as well. Both of these
options **make a match disappear**; to follow one without having it told to you,
see [spoiler-free mode](#spoiler-free-mode) just below.

The accepted names cope with what people actually type:

| You type | What it finds |
| --- | --- |
| `marseille`, `olm` | the full name, the source's abbreviation |
| `om`, `ol`, `asse`, `losc`, `manu`, `barca`, `juve`, `bvb` | the usual nicknames |
| `malaga`, `atletico`, `alaves` | accented names, without the accents |
| `barce`, `rennai` | the start of a word (from 4 letters up) |
| `real` | **three** clubs: Madrid, Sociedad, Betis - but not Villarreal |
| `manchester` | both Manchesters |

A word only bites at the **start of a word** in the name: `real` will not go
digging for Villar**real**. Below four letters you have to hit it exactly
(`bar` is Barcelona's abbreviation).

A word that matches no team is rejected at startup, together with the list of
competitions it was looked for in: a typo should not turn into a daemon that
stays silent for three weeks. `butbutbut --list-teams --teams om` also shows
what each word catches (`*` followed, `-` excluded).

#### One club inside a single competition

```bash
butbutbut --leagues big5,ligue2 --teams ligue2:sochaux
```

Adding a second division for **one club only** did not work: the team list
applies to every followed competition at once, so `--teams sochaux` silenced the
big five in the same breath. A word **prefixed with a competition** only
applies - and above all only restricts - inside that one:

| You write | What you get |
| --- | --- |
| `--teams sochaux` | nothing anywhere any more, except Sochaux |
| `--teams ligue2:sochaux` | the followed leagues carry on whole, and Ligue 2 narrows down to Sochaux |
| `--teams om,ligue2:sochaux` | OM everywhere, plus Sochaux in Ligue 2 |
| `--exclude-teams ligue2:metz` | Metz disappears from Ligue 2, and from nowhere else |

The prefix is written **the way `--leagues` is**: `l1:`, `ligue2:`, an ESPN code
(`por.1:`), a whole group (`feminines:lyon`), and `/` works too. For another
sport the competition keeps its own prefix and the club comes after:
`hockey:nhl:rangers` - the cut is made at the last colon. `--pin` and
`--spoiler-free` accept the same notation.

Three mistakes are rejected at startup, the first two **without a single
request**, because each of them would leave the word inert without ever saying
so:

- a prefix that names no competition: `ligu2:sochaux`;
- a prefix that names one that is not followed: `ligue2:sochaux` without
  `ligue2` in `--leagues`;
- a club that is absent from the competition it was given: `ligue2:om`, checked
  against the Ligue 2 catalogue alone rather than against every competition
  lumped together.

### Spoiler-free mode

There is one moment where butbutbut turns against you: you are watching the
match on a delay - a stream, a replay, ninety seconds behind the live feed - and
the card announces the goal before you get to see it. For that match, you need
to be able to tell it to keep quiet.

```bash
butbutbut --spoiler-free om                  # I am watching OM on a delay
butbutbut --teams om,psg --spoiler-free om   # alert me for PSG, not for OM
```

For a match covered by the list, **nothing reaches the screen or the speakers**:
no goal, no disallowed goal, no key moment, no red card, no kick-off warning. A
"KICK-OFF" would say the live feed has started, a "FULL TIME" that it is all
over: that spoils just as much as a goal, so **every** event goes quiet, without
exception.

**The journal, on the other hand, keeps everything.** That is the whole point of
the setting: only the screen and the sound are cut. Once you have watched the
match, `butbutbut --today` tells it like any other evening:

```
butbutbut : buts signales le 06/09/2026

Ligue 1
    18:51:10  Marseille 1 - 0 Paris FC        But de A. Kalimuendo (61')
    19:14:02  Marseille 1 - 1 Paris FC        But de M. Kebbal (77')
```

Names are typed with the same flexibility as `--teams` (`om`, `barca`, `manu`,
unaccented names, the start of a word), and a word that matches no team is
rejected at startup. A typo is even more treacherous here than elsewhere: it
does not make the daemon silent, it lets it spoil the very match you wanted to
protect. `butbutbut --list-teams --spoiler-free om` marks what the word catches
with a `?`.

**`--scores` masks the score** instead of hiding the match:

```
Ligue 1
  ?              Marseille ? - ? Paris FC               sans spoiler
  >                   Lens 2 - 0 Lille                  35'

2 match(s), '>' = en cours.
'?' = sans spoiler : 1 match(s) masque(s). Le journal, lui, a tout : butbutbut --today.
```

Dropping the line would have been worse than showing everything: you would no
longer know whether the match is on, nor at what time - and the day you watch it
is exactly the day you open `--scores`. So nothing that would let you rebuild
the score is shown - neither the scorers nor the state of the match: a finished
match looks like one in progress, otherwise a plain "termine" at the 80th minute
would be enough to tell you it is done. `butbutbut --status` masks the score of
live matches the same way, and recalls the setting:

```
  equipes     : equipes suivies : om, psg
  sans spoiler: om  (journal seulement : ni carte, ni son)
```

**Alongside `--teams` and `--exclude-teams`**, the three lists live together,
and the order of decision is always the same:

| Order | Setting | What it does to a match it covers |
| --- | --- | --- |
| 1 | `--exclude-teams` | the match does not exist: no card, no sound, no journal |
| 2 | `--teams` | outside the list, the match does not exist either |
| 3 | `--spoiler-free` | the match stays and fills the journal; screen and sound go quiet |

The first two silence a match, the third only silences the alert. Following OM
**and** putting it in spoiler-free mode is therefore not a contradiction, it is
the normal use: I want the journal, not the alert.

The setting has its own configuration key, so you do not have to retype it next
Saturday:

```ini
[butbutbut]
teams = om
spoiler_free = om
```

### Do not disturb

There are two moments when a card lands badly, and neither depends on the match:
**at night**, and **when someone else is looking at your screen**. A "GOAL" card
in the middle of a shared video call is the kind of bug you only discover once,
and in front of witnesses.

```bash
butbutbut --quiet-hours 23:00-08:00      # nothing between 11 pm and 8 am
butbutbut --quiet-while-presenting       # nothing while presenting
```

While it is quiet, **nothing on screen and nothing through the speakers**: no
goal, no cancelled goal, no key moment, no red card, no pre-match announcement.
The pinned card goes away too - a dashboard lit up all night is exactly what
people complain about - and it comes back by itself on the first poll after the
window.

**The journal keeps everything**, exactly as in spoiler-free mode. That is the
whole contract: only the alert is cut, never the trace. The next morning,
`butbutbut --today` tells the night like any other evening:

```
butbutbut : buts signales le 07/09/2026

MLS
    02:14:31  LA Galaxy 1 - 0 Seattle          But de R. Puig (58')
```

#### The time range

`--quiet-hours 23:00-08:00` is read against **the machine's clock**, not UTC: the
range means what it means to whoever writes it, wherever they are and whatever
time zone the followed matches are played in. It may **wrap around midnight**,
which is in fact the common case: nobody sleeps from 9 am to 5 pm.

The **start is included, the end excluded**: at 23:00 sharp it goes quiet, at
08:00 sharp it speaks again. A line has to be drawn somewhere, and that is how a
timetable reads - "from 11 pm to 8 am" does not include 8 am.

The four forms people actually type are accepted, and reduced to a single one:
`23:00-08:00`, `23h00-08h00`, `23h-8h` and `23-8` all say the same thing. An
unreadable range, on the other hand, is refused right away, naming the expected
format:

```
$ butbutbut --quiet-hours "de 23h a 8h"
butbutbut : plage horaire illisible : 'de 23h a 8h' (attendu HH:MM-HH:MM, par exemple 23:00-08:00)
```

A range that starts and ends at the same time (`08:00-08:00`) is refused as well:
it means "always" or "never" depending on who you ask, and it is not butbutbut's
place to choose for them.

On the command line this is fatal (exit code 2): whoever types it is sitting in
front of their terminal. **In the configuration file**, the same mistake is
reported on standard error and the key is simply ignored - the daemon is often
launched when the machine boots, with nobody there to read the error, and a
daemon that refuses to start costs more than a lost time range.

#### Screen sharing: what is detected, and what is not

`--quiet-while-presenting` asks the system rather than guessing. On Windows,
`SHQueryUserNotificationState` is precisely the API through which Windows itself
answers "is this a good moment to show a notification?": we ask it that very
question, and keep two of its answers.

| Situation | Detected? |
| --- | --- |
| Windows presentation mode (projector plugged in, presentation settings) | yes |
| Screen **duplicated** to a projector or a meeting room | yes, through the Focus Assist that Windows then turns on by itself |
| "Do not disturb" / Focus Assist turned on by hand | yes |
| **Window or screen share** from Teams, Zoom or Meet | **no** |
| macOS, X11, Wayland | **no**, nothing at all |

**Sharing from a conferencing app is not detectable, and it is better to say so
than to let it be assumed.** Windows exposes nothing that reports it. The only
way there would be to watch for the window class name of each application's
floating toolbar (`ZPToolBarParentWnd` and friends): that heuristic breaks at
Zoom's next update, and misfires in the meantime. Detecting nothing and writing
it down here beats detecting sometimes, at random.

In practice, the gesture that works is therefore: **turn "do not disturb" on
before the call**. Windows already honours it for the rest of the system, and
butbutbut follows. It is also what Windows turns on by itself when the display is
duplicated, which is the meeting-room and projector case.

Outside Windows there is nothing to follow: macOS lights an orange dot while the
screen is being captured but tells no public API about it, sharing under Wayland
goes through a portal that only answers the client which requested the share, and
X11 does not even know that sharing exists. The option is refused there with a
warning, like `--retry-fullscreen`.

A detection that fails **lets the card through** - back to the behaviour from
before the option - and the journal notes it **once**, not on every poll: a daemon
runs for hours, and a broken detection writing a line every 25 seconds would make
the journal unreadable on the very day you needed it.

#### The hook still fires

`--on-goal` keeps firing while it is quiet, unlike spoiler-free mode which cuts
it. This is not an oversight: the silence protects **this screen** and **these
speakers**, whereas a command that lights a garland, pushes a notification to a
phone or writes into a spreadsheet has no reason to go quiet because the machine
is asleep. Without that, `--quiet-hours` would amount to stopping the daemon.
`--spoiler-free` does cut everything, and for a different reason: there, it is the
result you do not want to know, whenever it arrives.

#### `--status` says when butbutbut goes quiet, and why

That is the first thing anyone checks when they suspect a breakdown, so the line
is always there, even when nothing silences anything:

```
  silence     : plage 23:00-08:00 - en veille jusqu'a 08:00
  silence     : plage 23:00-08:00 - rien en ce moment
  silence     : presentation ou ecran duplique - mode presentation
  silence     : aucun (voir --quiet-hours)
```

The journal says the same thing, and **only when it changes**:

```
2026-09-06 23:00:14  silence : en veille jusqu'a 08:00
2026-09-07 08:00:22  fin du silence : les cartes et le son repassent
```

#### The three times butbutbut asks itself "is this the moment?"

They are three shapes of a single question, and they stack - hence a single
decision point in the code (`butbutbut/silence.py`) rather than three branches
scattered around. They do not return the same verdict, and that is deliberate:

| Question | Setting | Verdict |
| --- | --- | --- |
| What time is it? | `--quiet-hours` | nothing on screen, nothing through the speakers |
| Is someone else looking at this screen? | `--quiet-while-presenting` | nothing on screen, nothing through the speakers |
| Would the card even be visible? | `--retry-fullscreen` | the card goes out **anyway**, and may come back later |

The benefit of the doubt changes with the question. Getting full-screen detection
wrong would make you miss a goal for nothing, so the card goes out; getting it
wrong at 2 am or in the middle of a presentation costs far more, so it stays
quiet. And a full-screen game never counts as a presentation: nobody else is
watching it, and going mute during a match played full-screen would mean cutting
butbutbut out exactly when it earns its keep.

**The silence only concerns the daemon.** `--test` and `--replay` show their
cards at 3 am just as they do at noon: those are commands you have just typed,
and silencing them would look like a breakdown.

Both settings have their configuration key:

```ini
[butbutbut]
quiet_hours = 23:00-08:00
quiet_while_presenting = oui
```

### The fixtures to come

`--scores` says what is being played today. `--next` answers the question that
comes right after: **when is the next match?**

```bash
butbutbut --next              # the fixtures to come in the competitions you follow
butbutbut --next om           # ... for that team
butbutbut --next 14           # ... over the next 14 days
butbutbut --next om,psg,3     # both at once, in any order
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

Grouped **by day, then by competition**, in the **machine's local time**: the
source only speaks UTC, where a Saturday 9 pm match in Marseille is written
down as Sunday 1 am. The last column says how long there is to wait - the time
answers *when*, that column answers *in how long*, and it saves counting days
on your fingers.

**Seven days by default**, because that is the grain of the calendar: a club
plays once a week, twice when it has a cup tie. Seven days therefore always
contain anybody's next match, without dumping a month of fixtures to answer a
question that fits on one line. `--next 30` is the ceiling: beyond that the
source itself has nothing left to say, calendars only being published a few
weeks ahead.

The window counts **whole days**, not 24-hour slices: `--next 1` is the rest of
today, `--next 7` is today plus the six days after it. A window closing in the
middle of an evening would cut a fixture list in half for no reason anybody
could see.

The team name is the one `--teams` already accepts - `om`, `barca`, `manu`,
accented names without their accents, the start of a word: it is the same code.
It adds to `--teams` when there is one.

Nothing scheduled prints a sentence rather than an empty table, one that
repeats what was looked for, where, and over how long:

```
Rien au programme dans les 7 prochains jours pour om dans Ligue 1.
```

That is also where a typo shows up: `--next` does not check the word against
the club catalogue the way `--teams` does, a check that would cost one more
request per competition on a command you fire off in passing.

**One request per competition**, not one per day: the dashboard accepts a date
range, so the whole window fits in a single call. Competitions are polled one
after the other, spaced out just as they are when the daemon starts - with
`--leagues all` that is 36 requests, and a burst ends up being turned away.
**If one fails, the others carry on**: the calendar comes out anyway, with what
is missing spelled out.

```
9 match(s) a venir dans 1 competition(s), sur 7 jour(s).
  (Bundesliga injoignable : HTTP 500 sur ger.1)
  (le calendrier ci-dessus est donc incomplet ; les autres competitions ont repondu)
```

When none of them answers, the command says so and exits with an error rather
than letting you believe in a weekend without football.

> The terminal output itself is in French, like `--scores` and `--status`: only
> the cards follow the machine's language.

### The table

`--scores` says what is being played, `--next` what is coming, `--top-scorers`
what we have seen go by. What was left is the one question a supporter asks
without watching a match at all: **where are they in the table?**

```bash
butbutbut --table             # the table of the competitions you follow
butbutbut --table l1          # ... of one competition
butbutbut --table om          # ... of that team's competition, their row highlighted
butbutbut --table l1,om       # both at once, in any order
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

(The highlighted row is the one `--table om` was after.)

The word after `--table` is read as a **competition** if the catalogue
recognises it, and as a **team** otherwise. These are exactly the names
`--leagues` and `--teams` already accept: `l1`, `nhl`, `top14` on one side,
`om`, `barca`, `manu` on the other. No club is called `big5`.

A country is another matter. `france` is shorthand for Ligue 1 as much as it is
the name of a national side: the competition wins, so `--table france` prints
Ligue 1 - and so does `--table france --leagues 6nations`, the word given to
`--table` quietly taking precedence over `--leagues`. The same goes for
`angleterre`, `espagne`, `italie`, `allemagne`, `portugal`, `ecosse`, `bresil`,
`argentine`, `mexique`, `japon` and `usa`. For a table of national sides,
naming the competition answers better anyway: `--table 6nations` shows France's
row among the ones that give it meaning.

Naming a team does not show that team's row alone: a rank on its own means
nothing, it is the table of their competition that answers the question. Their
row is marked with a chevron, the same sign `--scores` uses for "live" - not a
colour, because a terminal may be black on white, or redirected into a file.

`--exclude-teams` has **no effect** here, and that is deliberate: you do not
take a team out of a table. Ranks are counted relative to one another, and a
missing row would make a table that lies. Silencing a match, yes; punching a
hole in a table, no.

#### The columns follow the sport

Rugby and hockey do not have football's notion of a table, and the columns say
so:

| Sport | Columns | What changes |
|-------|---------|--------------|
| Football | `J G N P Diff Pts` | the baseline |
| Hockey | `J G P DP Diff Pts` | no draws, but **overtime losses** |
| Rugby | `J G N P Bon Diff Pts` | **bonus points** |

A hockey game is always decided, in overtime or in a shootout: showing an "N"
column full of zeroes would be inventing a statistic. An overtime loss, on the
other hand, is worth a point, and without the `DP` column the row's total does
not add up. In rugby it is the bonus points that put one team ahead of another
on equal wins. **Nothing is fabricated**: every column comes from a statistic
the source publishes, and a missing statistic shows a dash, never a zero.

The table fits in **80 columns**, even in rugby which has the most of them. A
table that wraps onto two lines cannot be read at all.

(The column headers are French abbreviations - J for games played, G for wins,
N for draws, P for losses - like the rest of the terminal output.)

#### What comes from the source, and what we do not invent

The table has its own ESPN endpoint, read with the same client, the same headers
and the same politeness as the scores:

```
https://site.api.espn.com/apis/v2/sports/<sport>/<slug>/standings
```

That is `apis/v2` and not `apis/site/v2` like the scoreboard: the second address
answers 200 with an empty object, which looks like an off-season when it is
merely the wrong door.

**The rank is never computed.** Separating two teams on equal points follows
rules specific to each competition - goal difference here, head-to-head there,
tries scored elsewhere - and redoing that would end up lying one day, about a
competition nobody was watching. We show the rank ESPN publishes (`rank` in
football and rugby, `playoffSeed` in hockey, which has no `rank` at all).

The **ordering**, on the other hand, is necessary, and it is a surprise from the
source: a league table arrives already sorted, but a World Cup group arrives
shuffled and the NHL's Western Conference starts at its 4th seed. So the rows
are ordered by the published rank; when the source publishes none, we keep its
order and number the rows.

**One block, or several.** The source always puts a *list* of blocks, even when
there is only one: a league has one, the NHL two (its conferences), a World Cup
twelve (its groups). The block's name is only printed when there is more than
one - for a league, the source calls its single block "French Ligue 1 2026-27",
which would only repeat the line above.

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

#### When there is nothing to rank

A cup is played as a bracket, not as a table, and between two seasons the source
has nothing to serve. In both cases the answer is a sentence, not an empty table
- which would look too much like a breakdown - and it names the exact place we
went looking:

```
butbutbut : classement - Coupe de France

Aucun classement a afficher pour Coupe de France.
  (Coupe de France : aucun classement publie sous soccer/fra.coupe_de_france)
  (une coupe se joue en tableau ; hors saison, la source n'a rien a servir)
```

A team found nowhere gets the same treatment, and that is where a typo shows up:
like `--next`, `--table` does not check the word against the club catalogue, a
check that would cost one more request per competition on a command you fire off
in passing.

```
Aucune ligne pour zzzclub dans les classements de Ligue 1.
```

**One request per competition**, one after another and spaced out, like `--next`
and like the daemon's start-up. **If one fails, the others carry on**; when none
of them answers, the command says so and exits with an error.

```
  (Bundesliga injoignable : HTTP 500 sur ger.1)
  (le classement ci-dessus est donc incomplet ; les autres competitions ont repondu)
```

### Placing the cards

```bash
butbutbut --position bottom-right     # default
butbutbut --position top-left
butbutbut --screen 1                  # on the second screen
butbutbut --scale 1.4                 # bigger cards
butbutbut --opacity 0.9
```

The cards stack from the corner you choose: the latest one sits against the
corner, the earlier ones move up (or down, from a top corner). Past five
visible cards, the oldest one gives up its place. One card is the exception,
[the pinned card](#the-pinned-card): it holds the corner permanently, the stack
starts after it, and it does not count towards the five.

### No screen: the cards written in the terminal

A machine with no graphical server, an SSH session, a tmux, a container: there
is no window to open, and until now a goal left nothing there but a line of log.
`--no-overlay` already existed, but it **cuts** the display, it does not replace
it.

```bash
butbutbut --terminal
```

The same card, the same elements, the same geometry - the score in the middle,
the names on either side, the scorer underneath - but in characters:

```
+----------------------------------------------------------------------------+
| GOAL!  LIGUE 1                                                         35' |
|                           Angers  0 - 1  Stade Rennais                     |
| Goal by A. Kalimuendo                                                      |
+----------------------------------------------------------------------------+
```

Every card goes through it, not just the goals: kick-off, half-time, the
restart, full-time with its list of scorers, the sending-off, the pre-match
announcement. A red card is drawn here too rather than written: `[]` per card,
against the figure of the team that took it.

**It starts in two ways.** `--terminal` asks for it, and then no window is even
attempted - which is what you want over SSH towards a machine that does have a
screen, or from a tmux. Without the option, butbutbut first tries to open a
window and **switches over on its own** the day it cannot: tkinter missing,
`DISPLAY` empty. That fallback is not silent, it says so:

```
2026-09-08 23:37:33  aucune fenetre possible : les cartes s'ecrivent dans le terminal (sortie d'erreur), le journal garde la sortie standard
```

It is automatic because it takes nothing away from anybody: at that point the
card was already lost, and an option you would have had to read beforehand would
only have saved those who read it. `--no-overlay` keeps its exact meaning - no
card, anywhere - and wins over `--terminal` when both are given.

**One exception, when nobody is reading.** The argument above assumes a human
in front of the terminal. Started by the autostart, butbutbut has none: the
cards would go to the system log for the whole session, while the screen would
only stay empty until the session publishes `DISPLAY`. In that precise case -
no screen, and standard error is not a terminal - the daemon exits with 5
instead of falling back, and the supervisor restarts it thirty seconds later
with the complete environment:

```
2026-09-12 17:10:31  aucun affichage joignable : ni DISPLAY ni WAYLAND_DISPLAY. Sortie en 5, pour etre relance quand la session les aura publies.
```

The arbiter is standard error rather than standard output, because that is
where those cards are written: `butbutbut --terminal > evening.log` therefore
keeps its fallback. `--terminal` and `--no-overlay` are never concerned, they
ask for no screen at all.

> By the way: a session with no `DISPLAY` used to **take the daemon down**
> before the version that introduced this fallback. `tkinter` imported fine, `Tk()` raised a `TclError`
> nothing caught, and butbutbut died at startup on the very machine where it
> would have been useful. It now degrades, as it does everywhere else.

**Sound, voice, hook and log do not move.** This mode replaces a window and
nothing else: `--speak` speaks, `--on-goal` fires, the log file fills up
identically, and `--no-phase-cards`, `--spoiler-free` and `--quiet-hours` apply
exactly the same. `--quiet`, on the other hand, wins: it says "write to the log
only", and a card is writing in the terminal.

**Two outputs, the same rule as everywhere else.** The log goes to standard
output, the card to standard error - that is the rule of [Two outputs, and only
one carries the data](#two-outputs-and-only-one-carries-the-data), applied as
is: the card is formatting, the log line is the data. In a terminal the two mix
and you read everything; as soon as you redirect, each goes where it belongs.

```bash
butbutbut --terminal > evening.log    # the file only gets the log
butbutbut --terminal | grep 'BUT'     # ... and a filter works as before
```

**The width follows the terminal**, between 30 and 78 columns, read again for
every card - so a window resized mid-evening is followed. An output that is not
a terminal (a file, a pipe) has no width: the card then takes the maximum width,
which has the merit of producing the same file from one machine to the next.
Whatever does not fit gives way, exactly as on the on-screen card - the names
first, the list of scorers next, never the score:

```
+--------------------------------------------+
| GOAL!  BUNDESLIGA                      35' |
| Borussia... [][]  1 - 2  []   Eintrach...  |
| Goal by C. Arcus                           |
+--------------------------------------------+
```

**What a terminal card does not show**, and why:

- **the crests**: a terminal displays no image, and an abbreviation in their
  place would make the drawing say something the card does not;
- **the colours**, and that is a choice, not an oversight. The whole colour
  decision of the program rests on one certainty: the card background is the
  blue-black of `overlay.py`, and [a club's
  colour](#club-crests-and-colours) is only kept when it reads against it. A
  terminal has no known background - it may be white - so the question
  `crests.pick_accent` knows how to settle no longer has an answer, and we do
  not bet on somebody else's theme. An unreadable club name would be worse than
  a club name in black and white. Nothing writes an escape code, so there is
  nothing to degrade for `NO_COLOR`, for a Windows console or for a pipe;
- **the pinned card**: it is worth having because it *stays* on screen, and a
  terminal only scrolls. `--pin` keeps following its match - the "pinned" line
  of `--status` still tells the truth - but no pinned card is written.

**You can look at it without waiting for a Saturday night.** `butbutbut --test
--terminal` shows the sample card, and `--replay` replays a whole evening,
terminal cards included: see [Recording a real match, and replaying
it](#recording-a-real-match-and-replaying-it).

### Club crests and colours

For every team, the source publishes the URL of its crest and its two colours.
The card uses that in two ways.

**The crest**, next to its team's name. tkinter reads the PNG on its own, so
still zero dependencies: no Pillow. But **a card never waits on the network** -
a goal has to be on screen within the second. Crests are therefore served from
a disk cache, and a crest that is still unknown goes off to download in the
background: the card of the moment shows without it, the one for the next goal
will have it. Room is reserved for it as soon as either of the two teams has
one, so that the score stays centred in the same place from one goal to the
next.

| System | Cache |
| --- | --- |
| Windows | `%LOCALAPPDATA%\butbutbut\logos` |
| macOS | `~/Library/Application Support/butbutbut/logos` |
| Linux | `~/.local/share/butbutbut/logos` |

A crest that does not exist, a corrupt PNG, a read-only folder: the card shows
without an image, and that's that. The folder can be wiped at any time, it
will fill up again.

What gets downloaded is downloaded **at the size the card will show it**. The
source publishes its crests at 500x500 and serves the very same file resized
server-side: a crest goes from 37 kB to 5 kB, seven times less, and it looks
sharper - tkinter only shrinks by integer ratios, and halving a 64x64 beats
dividing a 500x500 by fifteen. The size asked for follows `--scale`, and past a
projection-sized card the original comes back instead.

That URL is the only one butbutbut **builds** instead of reading it from the
answer, so it is treated as a preference and nothing more. It is not even built
for an address of an unexpected shape, and if it does not return a usable PNG -
404, empty body, anything that is not an image - the URL the source announces
is used instead, right away. Nothing shows on the card. Crests downloaded by
earlier versions were filed under their URL alone: they are no longer looked
up, and their replacements arrive as the goals come in.

**The club colour**, for the team that scores and for its number. Careful,
though: these colours are chosen for a white background, and the card's
background is almost black. Troyes' navy blue (`0000bf`) is unreadable on it,
and Paris FC's black (`000000`) simply ceases to exist. So butbutbut measures
the **contrast** (WCAG relative luminance) and walks down three rungs for as
long as it cannot read anything:

| Rung | Example |
| --- | --- |
| the club colour, if it stands out | Bayern `dc052d`, Arsenal `e20520` -> kept |
| its secondary colour, otherwise | Chelsea `144992` -> white, Barcelona `990000` -> `fce38a` |
| the competition's, as a last resort | Paris FC `000000` / `000000` -> the yellow of Ligue 1 |

The vertical stripe, on the other hand, never moves: it always says which
competition you are in. `butbutbut --test 5` walks the colour through all
three rungs, with five real teams.

```bash
butbutbut --no-logos          # no crest, nothing downloaded
```

Club colours stay with `--no-logos`: they arrive with the scores, they cost no
request at all.

### Sound

The bundled mp3 plays on every goal. To replace it, drop a file into the
`sound` folder (`butbutbut --paths` gives the path):

| System | Folder |
| --- | --- |
| Windows | `%LOCALAPPDATA%\butbutbut\sound` |
| macOS | `~/Library/Application Support/butbutbut/sound` |
| Linux | `~/.local/share/butbutbut/sound` |

Formats: wav, mp3, ogg, opus, flac, m4a, aac. Several files? One is drawn at
random on every goal. No need to restart the daemon: the folder is re-read
every time.

#### One sound per context, decided by the file name

The **name** of the file says when it plays. Nothing to configure: renaming is
enough.

| File name | When it plays |
| --- | --- |
| `contre.mp3`, `against.mp3` | when a **followed** team (`--teams`) **concedes** |
| `om.mp3`, `barca.mp3`, `marseille.mp3`, `olm.mp3` | when **that team scores** |
| `fra.1.mp3`, `l1.mp3`, `ligue1.mp3`, `ucl.mp3` | only for a goal in **that competition** |
| `corne.mp3`, anything else | the background pool, drawn at random as before |

Team names are the ones `--teams` accepts (nicknames, abbreviations, accents
dropped) and competition names the ones `--list` lists (ESPN code or alias).
The conceding word also spells `encaisse` or `conceded`.

**Several files for the same thing?** A suffix after `-`, `_`, a space or a dot
is enough: `om-1.mp3`, `om-2.mp3`, `contre 2.ogg`. One of them is drawn at
random, as before.

**Which one wins when several could play**: the order runs from the narrowest
to the widest, so that a precise intent is never buried under a broader one.

| | Tier | What it can claim |
| --- | --- | --- |
| 1 | the team that scores | the goals of a single club |
| 2 | `contre` | every goal conceded by the followed clubs |
| 3 | the competition | a whole competition |
| 4 | the background pool | everything |

An empty tier hands over to the next one: a folder holding only `contre.mp3`
and `corne.mp3` plays `corne.mp3` the rest of the time. That is what makes an
**OM - PSG** worth listening to: with those two files and `--teams om`, a goal
for OM sounds different from a goal against, without looking at the screen.

```bash
butbutbut --status            # what butbutbut made of each file
```

```
  son         : 4 fichier(s), le nom dit quand ils jouent
                contre.mp3             quand une equipe suivie encaisse
                corne.mp3              tirage general
                fra.1.mp3              les buts de Ligue 1
                om.mp3                 quand cette equipe marque
```

> One caveat: to keep a team file out of the *other* matches, butbutbut has to
> know that the word names a club - which it does for the usual nicknames
> (`om`, `ol`, `barca`, `manu`, `juve`, `bvb`...) and for anything passed to
> `--teams`. Any other name (`angers.mp3`) does play for Angers when Angers
> scores, but joins the background pool elsewhere: there is no offline team
> catalogue to settle it. `--teams angers` removes the ambiguity, and
> `--status` then files it under the right tier.

#### Naming the sound yourself: `--sound-for`

Renaming a file means copying it into the `sound` folder, and accepting that
butbutbut guesses what `om` stands for. When the club's chant already lives
somewhere on the disk - or when the file name is needed for something else -
the pair can simply be spelled out:

```bash
butbutbut --sound-for om=~/sounds/allez-om.wav
butbutbut --sound-for om=~/sounds/om.wav,ucl=~/sounds/anthem.mp3
butbutbut --teams om --sound-for om=~/sounds/om.wav,contre=~/sounds/ouch.wav
```

On the left, the very same words as everywhere else: those of `--teams` for a
club (`om`, `barca`, `manu`, `marseille`, the start of a name), those of
`--leagues` for a competition (`l1`, `ucl`, `nhl`, an ESPN code), and `contre`
for a goal conceded by a followed team. On the right, a path - `~` included.

**Which one wins when a goal ticks both boxes?** The team. A goal for OM in the
Champions League, with both `om=` and `ucl=` named, plays the OM sound: the
most precise one speaks, exactly as with file names. These are in fact the
**same four tiers** - the team, `contre`, the competition, the background pool -
and not a second mechanism bolted on the side. The one difference:
`--sound-for` has no general tier. A named sound aims at someone; it never
becomes the background noise of every other goal.

**And if the folder already says something?** At equal tier, what is named
covers what is guessed: with `om.mp3` in the folder *and*
`--sound-for om=~/sounds/om.wav`, the latter plays. Whoever wrote the pair has
just said which one they meant.

**A wrong path is reported at startup**, not at the first goal three hours
later - the same logic as a misspelled team name:

```
$ butbutbut --sound-for om=~/sounds/om.wav
butbutbut : le son de om : fichier introuvable (/home/me/sounds/om.wav)
$ butbutbut --sound-for marseile=~/sounds/om.wav
butbutbut : aucune equipe ne correspond a 'marseile' dans Ligue 1. [...]
```

The file must exist, be readable, and carry an extension butbutbut knows how to
play (wav, mp3, ogg, opus, flac, m4a, aac). Every faulty pair is reported at
once: fixing three paths across three restarts is nobody's idea of fun.

Once started, though, the daemon no longer stops for that. A file that
**vanishes along the way** - USB stick unplugged, folder renamed - makes the
goal fall back to the sound below it (the folder, then the bundled sound) and
leaves a line in the log:

```
2026-09-07 21:14:03  son nomme pour om indisponible (fichier introuvable) :
/media/usb/om.wav -- le son par defaut prend le relais
```

`--volume` and `--no-sound` keep their reach: silent mode also cuts the named
sounds, and `--volume` applies to them like to every other.

```bash
butbutbut --status            # what each pair arms, and what is wrong with it
```

```
  son nomme   : 3 paire(s), le plus precis l'emporte
                om -> om.wav           quand cette equipe marque
                contre -> aie.wav      quand une equipe suivie encaisse
                ucl -> hymne.mp3       les buts de Ligue des champions
```

And `--status` does say so even when something is wrong: a faulty path is
refused at startup by every command **except that one**. Erroring out in front
of the only command you asked the question of would amount to refusing to
answer; it prints the offending pair instead, with what it has -
`om -> om.wav  quand cette equipe marque  (fichier introuvable)`. That is the
case that matters, because startup was sometimes weeks ago and external drives
get unplugged.

In the configuration file everything fits in a single key - comma-separated, or
one pair per line once the list grows:

```ini
[butbutbut]
teams = om
sound_for =
    om=~/sounds/om.wav
    contre=~/sounds/ouch.wav
    ucl=~/sounds/anthem.mp3
```

A comma only splits in front of a new pair: a path that contains one
(`om=~/sounds, vol. 2/om.wav`) stays readable as it is.

```bash
butbutbut --no-sound          # silent
butbutbut --no-overlay        # just the sound and the log, no card
butbutbut --terminal          # the card written in the terminal, no window
butbutbut --no-logos          # no crest on the cards
butbutbut --duration 8        # keep the card for 8 s (default: the length of the sound)
```

### The volume

```bash
butbutbut --volume 40         # 0 muted, 100 loudest
```

The setting applies to **every** sound - the bundled horn, an mp3 dropped in
the folder, a sound named by `--sound-for` - because it is applied at playback
rather than to the file. `--volume 0` amounts to `--no-sound`, and leaves
`--speak` talking: turning the goals down has never meant silencing the
announcement.

`butbutbut --status` shows the level in force, and warns when the installed
player cannot follow it. Only one is in that case, `aplay`: it has no knob, and
the goal will come out loud - and the wav no longer has that problem at all,
since it goes through the native output, which applies the gain to the samples.
Installing `mpv` or `ffmpeg` is enough to give it
back.

`--volume` long counted from 0.0 to 1.0. Those values are still understood -
`0.55` means 55, `1` means the maximum - so a configuration file written before
does not change meaning. Only a true 1% has to be written `1%`.


### The voice

Everything above assumes you are looking at the screen. The sound says
something happened, the card says what - but it says nothing to someone working
in another window, on another desktop, or who cannot see the screen at all. A
sentence spoken out loud carries the score and the scorer without you having to
look up.

```bash
butbutbut --speak                    # the sound, then the sentence
butbutbut --speak --no-sound         # the voice alone, no horn
butbutbut --test --speak             # try it right now, without waiting for a goal
```

The sentence is **the hook's sentence** - the `BUT_TEXT` variable of
`--on-goal`, word for word:

```
BUT ! [Ligue 1] Angers 1 - 2 Stade Rennais - But de A. Kalimuendo (58')
```

There is only one in the program, deliberately: two wordings would eventually
have stopped saying the same thing. It follows the **language of the cards**
(`--lang`), not that of the log - you are speaking to whoever is watching the
screen, not to whoever will read `--today` tomorrow morning.

**Nothing to install, anywhere** - the same rule as everywhere else here:

| System | What speaks | To install |
| --- | --- | --- |
| Windows | PowerShell and `System.Speech` | nothing |
| macOS | `say` | nothing |
| Linux | `spd-say`, else `espeak-ng`, else `espeak` | `speech-dispatcher` or `espeak-ng` |

`butbutbut --status` says which one would speak here, before you have even set
the option:

```
  voix        : inactive (voir --speak) - PowerShell (System.Speech) parlerait
```

That is the answer that matters, because it comes before you have installed
anything: a machine where nothing can speak says so there, not at the first
goal. With the option set, the same line changes tense:

```
  voix        : PowerShell (System.Speech), dans la langue des cartes
```

**A word about installed voices.** Windows picks a voice in the language of the
cards when the machine has one, and keeps its own otherwise: an English machine
will read French with an English accent rather than fall silent. `spd-say` and
`espeak` are handed the language directly. `say`, for its part, has no language
option - the voice set in System Settings is the one that speaks, whichever it
is; `say -v '?'` lists them.

**Two goals back to back?** The sentences **queue up** and come out one after
the other. That was the call to make, and it holds: two goals in the same poll
are most often two different matches, and dropping the second would leave you
believing a score that no longer exists. Talking over it, meanwhile, makes both
unintelligible. The queue is capped at four sentences, and beyond that it is
the **oldest one waiting** that goes: on a wild night you want to know where
things stand, not to listen to the previous quarter of an hour.

The voice also waits for the horn to finish before speaking - two and a half
seconds - for the same reason.

**What silences it.** Exactly what silences the speaker, because it is one:

- `--quiet-hours` and `--quiet-while-presenting`: at night and during a
  presentation, we no more speak than we display (see
  [Do not disturb](#do-not-disturb));
- `--spoiler-free`: what is not shown is not said either, otherwise the option
  would no longer protect anything;
- the log, for its part, keeps everything in both cases, and `--today` tells
  the story.

**What cannot happen.** No failure of the voice touches the daemon: missing
program, voice not installed, command returning 1, command that never returns
(it is killed after 30 s). One line in the log, **one only** - a whole Saturday
would otherwise write as many lines as there were goals for a fault that will
not change - and the match goes on. Speech lives in a thread of its own:
neither the card nor the next poll waits for it.

> `--speak` does not talk during a `--replay`. An evening replayed at
> `--speed 60` squeezes a half into thirty seconds: the voice would still be on
> the first goal when the match ended.

### The key moments of a match

Beyond goals, a card marks **kick-off**, **half-time**, the **restart** and
**full-time**. They are deliberately plainer: the title is grey instead of the
league's colour, no team is singled out, and above all **they make no noise at
all**. Only a goal fires the sound.

```bash
butbutbut --no-phase-cards    # only goals on screen
```

The log, for its part, keeps a trace of these moments even with that option on.

The **kick-off** card says what both clubs did before: their form over the last
five matches, most recent first, then their record for the season.

```
COUP D'ENVOI   LIGUE 1                                             1'
Marseille           0 - 0              Paris FC
Marseille : PPGGG  1G 0N 2P
Paris FC : GGNGP  2G 1N 0P
```

The letters are the ones from the table - in French `G` won, `N` drawn, `P`
lost - and they follow the language of the cards, just like the `--table`
columns: the form and the standings must not say the same thing two different
ways. So Marseille come off three straight wins followed by two defeats, the
last of which is their latest match.

Both pieces of information travel in the **same response as the score**: they
do not cost one extra request, they were simply being thrown away. A side the
source says nothing about gets no line, and the card then goes back to being
exactly what it was - which is the whole of hockey, whose scoreboard publishes
neither form nor record. Rugby has its form but not its record.

The [pre-match card](#the-pre-match-announcement) says the same thing, under its
countdown. Those two are the only ones that look backwards, and that is
deliberate: they are the only two where the match has nothing to say about
itself. From half-time on, what has just happened is more interesting than what
happened last month.

The **full-time** card goes a little further: it lists each side's scorers
under the score, because a bare `1 - 2` does not say who scored, and that is
precisely the question when you haven't watched the match.

The cards speak the language of the machine, French among five (see [Language](#language)); the log stays in French.

```
FIN DU MATCH   LIGUE 1                                        90'+4'
Angers              1 - 2              Stade Rennais
Angers : M. Lopez 12'
Stade Rennais : A. Kalimuendo 58', L. Blas 77'
Possession 39% - 61%  Tirs cadres 4 - 9
```

A side that hasn't scored gets no line, an own goal is marked `(csc)` and a
penalty `(sp)`. The card gains one line per scoring side, but never a pixel
more than its maximum width: a list that runs too long is cut off with an
ellipsis rather than allowed to overflow.

The last line **explains** the score instead of repeating it: `1 - 2` has
already been said, `39% - 61%, 4 shots on target to 9` tells the match. It
comes after the scorers because "who scored" is the question you ask on
arriving at the card, and "how" only afterwards. It is **the only card** that
carries it, for the same reason the form is on the kick-off card: it is the
only one where the match has nothing new left to say. A goal card has eight
seconds to announce a scorer, and at half-time the match is not over.

Two statistics, not four, and the choice is not a matter of taste: across
1,764 finished matches, the winner had more **shots on target** than the loser
69% of the time, more **shots** 57%, and more **corners** 45% - that is, less
often than a coin toss. **Possession** predicts nothing at all (50%), and that
is exactly what keeps it: it does not say who won, it says how, and a 2-1 won
with 39% of the ball tells you something. The survey is in
[docs/api-espn.en.md](docs/api-espn.en.md), section 3.

Like the form and the record, those numbers arrive in **the same response as
the score**: they do not cost one extra request. And as everywhere else, we
keep quiet rather than approximate: if only one side publishes a statistic,
the whole pair is thrown away - `39%` on its own would let you guess `61%`,
which could be anything. An all-zero block (the source does publish some, on
genuinely finished matches too) is not shown either, and a shots-on-target
count lower than the same side's goals is dropped: the card carries the score
right above, it is not going to contradict itself. When nothing is left, the
card is exactly the one from before.

Football only: hockey and rugby fill the same field with entirely different
numbers - goalkeeper saves and season totals for one, 193 statistics in the
Six Nations and none at all in the Top 14 for the other. Their full-time card
does not move by a pixel.

On a cup night the same card also carries the shootout verdict - `Tirs au but
3 - 5 : Stade de Reims` - because a `1 - 1` does not say who goes through. See
[Penalty shootouts](#penalty-shootouts).

On Windows and macOS playback is built in (MCI, `afplay`). On Linux you need a
the **wav goes out natively**: butbutbut talks to `libpulse-simple` through
ctypes, with `libasound` as a second resort, and therefore needs no binary at
all to play the **synthesised stadium horn** it generates itself. PipeWire has
no path of its own, it serves the PulseAudio interface.

The mp3 keeps an external player (`mpv`, `ffmpeg`, `sox`, `vlc`): Python's
standard library has no audio decoder. Without one of them, butbutbut falls
back on the synthesised horn rather than on silence.

### The configuration file

So you don't have to retype the same options every time - or re-run the
installer just to change league - butbutbut reads a file at startup:

```bash
butbutbut --write-config      # write a commented example (never overwrites anything)
butbutbut --paths             # where it lives: the "config" line
```

| System | File |
| --- | --- |
| Windows | `%LOCALAPPDATA%\butbutbut\butbutbut.conf` |
| macOS | `~/Library/Application Support/butbutbut/butbutbut.conf` |
| Linux | `~/.local/share/butbutbut/butbutbut.conf` |

A single section, `[butbutbut]`, and keys named after the long options without
the dashes. Everything is optional:

```ini
[butbutbut]
# What we follow
leagues = l1,ucl,cdf
exclude = seriea
teams = om,psg
exclude_teams = psg
spoiler_free = om

# One club inside a single competition: the rest carries on whole.
# leagues = big5,ligue2
# teams = ligue2:sochaux

# The card that stays on screen for the duration of the match (one team)
pin = om

# Where and how it shows up
position = top-right
screen = 1
duration = 8
scale = 1.2
opacity = 0.95

# Polling rate, in seconds
interval = 25
idle_interval = 300

# Sound and discretion (oui/non, true/false, 1/0)
sound_for = om=~/sounds/om.wav, ucl=~/sounds/anthem.mp3
volume = 70
no_sound = non
speak = non
no_overlay = non
terminal = non
no_phase_cards = non
catch_up = non
quiet = non

# Do not disturb: at night, and while presenting
quiet_hours = 23:00-08:00
quiet_while_presenting = non
```

**The command line always keeps the last word**: `command line > file >
defaults`. With the file above, `butbutbut --leagues pl` follows the Premier
League just this once, without changing anything in the file.

```bash
butbutbut --config ~/perso/but.conf     # read another file
butbutbut --config ~/perso/but.conf --write-config
```

The file is **only read at startup**: after a change, restart the daemon
(`butbutbut --stop`, then `butbutbut`). `butbutbut --status` reminds you which
file is in use, and whether it exists.

None of this ever stops butbutbut from starting: a missing file is the normal,
silent case, and a file that is unreadable, malformed, or carrying an unknown
key or an impossible value (`interval = lots`, `position = middle`) is
reported on standard error - the offending key is ignored, the rest applies.

### Red cards

```bash
butbutbut --red-cards
```

On request, a sending-off gets a card of its own. It is **detected** like a
goal - the source publishes it in the same table of events, with a stable key,
so it comes out only once and a sending-off already shown when the daemon
starts is never replayed - but it is **displayed** like a key moment: grey
title, no team in colour (that would make it look like good news), and **no
sound**.

```
CARTON ROUGE   LIGUE 1                                           62'
Angers              1 - 2              Stade Rennais
Stade Rennais : J. Lefort
```

It does not depend on `--no-phase-cards`: switching off a match's key moments
must not switch off what you have explicitly asked for. `--red-cards` turns it
on, and nothing else turns it off.

#### One red rectangle per sending-off, on every card

A sending-off card comes and goes; the team stays down to ten until the final
whistle. So every card of that match says it, not only the one for the card
itself: **one red rectangle per sending-off**, set against the score of the
team that took it.

```
BUT !   PREMIER LEAGUE                                            74'
Arsenal  []  1 - 2  Chelsea
But de C. Palmer
```

That is what explains the goal that follows. A 1-2 with eleven against ten does
not read like an ordinary 1-2, and until now that fact only lived in a card
seen for six seconds, twenty minutes earlier.

Three details, all for the same reason: the card must not move just because the
match falls apart.

- **Room is reserved on both sides**, sized on the more punished team. The
  score stays in the middle of the card, where the eye looks for it; reserving
  per side would slide it at every sending-off.
- **The rectangles line up on the score**, not on the name: two cards on one
  side and one on the other still fall in the same column, each against the
  digit it concerns.
- **They do not depend on `--red-cards`.** The option opens a card for the
  sending-off, with its title and the player's name; the rectangles are there
  without asking. They cost no request: sendings-off arrive in the same table
  of events as the goals.

They follow `--scale` like the rest of the row, and are drawn on the pinned
card as on any other. A sport that has no sending-off never shows one:
**hockey** punishes with two minutes in the box, not with a card (and the
source publishes no events at all for it anyway). **Rugby** does - but its
yellow card is a ten-minute temporary exclusion, and is not counted.

```bash
butbutbut --test --leagues eng.1     # a demo card shows one
```

### The pre-match announcement

```bash
butbutbut --before-kickoff 5     # 5 minutes before, once (0 = off)
```

A quiet card a few minutes before kick-off, with the countdown, and no sound.
**One per match only**: the window stays open across several polls in a row,
and the card does not come back at each of them. A match running late (the
time has passed, nothing has started) fires nothing: announcing a match that
should already have kicked off would be a lie.

```
LE MATCH VA COMMENCER   LIGUE 1
Angers              0 - 0              Stade Rennais
Coup d'envoi dans 5 min
Angers : PPGGG  1G 0N 2P
Stade Rennais : GGNGP  2G 1N 0P
```

The countdown stays on the third line - it is what the card exists for - and
the form of both sides goes underneath, as at
[kick-off](#the-key-moments-of-a-match). It is the tallest card in the
programme, and the only one whose height depends on what the source publishes:
a match it says nothing about gives back the three lines from before.

**Which leg of a cup tie this is shows up in the corner**, where every other
card puts the minute of play:

```
LE MATCH VA COMMENCER   LIGUE DES CHAMPIONS            Match aller
Real Madrid         0 - 0                    Benfica
Coup d'envoi dans 5 min
Real Madrid : GGNGG  3G 1N 0P
Benfica : GPGGN  2G 1N 1P
```

Nothing has started, so that corner is free: the stake goes in without costing
the tallest card in the programme one more line. It is also everything the
source publishes about a match's stake - **there is no matchday there**, no
round either, and not a single league says anything at all (see
[docs/api-espn.en.md](docs/api-espn.en.md), section 3). What else it writes is
in English and most often a result: a label the programme cannot say back in
all five languages is dropped, never shown verbatim.

Like the red card, this card has its own switch and does not depend on
`--no-phase-cards`. Set to more than a quarter of an hour ahead, it also
speeds up the polling rate so that the time you asked for is actually met.

The **team filter** applies to these three cards just as it does to goals:
with `--teams om`, only OM's sendings-off, announcements and full-time cards
come through.

### The pinned card

```bash
butbutbut --pin om        # while OM are playing, a card stays on screen
```

Every card above is fleeting: it shows up on an event, it leaves a few seconds
later. This one does the opposite. It appears at kick-off, **refreshes at every
poll** - the score and the clock - and leaves a while after the final whistle.
That is what turns butbutbut from an alert into a **dashboard**: the card lives
on your second screen while you work.

```
LIVE   PREMIER LEAGUE                                            61'
Arsenal                2 - 1                Chelsea
```

Two lines, not three: it does not tell you what just happened, it tells you
where the match stands. No team turns to its club colour either - everywhere
else that colour means "they have just scored", and reusing it for "they are
ahead" would be a category error stretched over ninety minutes. And it **never
makes a sound**: the sound stays the mark of a goal. A goal still rings and
still gets its own card, next to this one.

**Where it lives.** It is **anchored to the corner you chose**, and the stack
of fleeting cards starts right after it. Two deliberate consequences: five
goals in a row cannot push it out, because the five-card ceiling only counts
the fleeting ones; and it cannot hide a goal card, because every position is
computed together, its own first. It gives up the corner, which is the best
spot - that is the price of being there permanently: your eye knows where to
look, a goal should not have to wait.

**Its life cycle.** It appears at kick-off, or straight away if a match is
already under way when the daemon starts: starting it at half-time should give
you the card, not make you wait for the next match. It follows the match to the
end, then stays **five minutes** past the final whistle - long enough to catch
the score on your way back from the kitchen - and disappears. It does not spend
the night on screen. A match that vanishes from the scoreboard (a new matchday,
a truncated response) is treated as a finished one, with the same delay: a card
that lingers beats a card that flickers.

**One team, one card.** `--pin om,psg` is refused at startup: there is never
more than one pinned card, and accepting the list would silently follow only
one of the two. A word that catches **several clubs** is allowed, though -
`--pin real` is Madrid, Sociedad and Betis - because the naming is the one from
`--teams`, and refusing here what we accept there would make no sense. In that
case the card follows **the match that kicked off first**, and does not change
while it lasts: a card hopping from one match to another at every poll would be
unreadable. When it ends, the card moves on to another one still in play.

The naming is exactly that of `--teams` (`om`, `barca`, `manu`, unaccented
names, the start of a word), and a word that names no team is **refused at
startup**, just like `--teams`: a silent `--pin marseile` would be a card that
never arrives, with no way to know why.

`--pin` is not a filter: it adds a card, it hides none. To be alerted only
about that team, `--teams` is the option, and the two combine:
`butbutbut --teams om --pin om`.

```bash
butbutbut --test --pin om     # a demo pinned card
butbutbut --status            # the "epinglee" line says what it follows
```

```
  epinglee    : om -> [Ligue 1] Marseille 1 - 0 Paris FC  34'
```

The log records the card arriving and leaving, and nothing in between: one line
per poll for ninety minutes would teach nobody anything.
### Running a command on every goal

```bash
butbutbut --on-goal 'curl -s -X POST -d "$BUT_TEXT" https://example/hook'
```

Rather than building into butbutbut the ten integrations ten people would want
- a smart light strip, a Discord webhook, home automation, a personal counter -
`--on-goal` hands you what you need to write them yourself. The program knows
nothing about what it runs, and that is the point.

The details of the goal arrive in **environment variables**, never pasted into
the command: `$BUT_TEXT` under a shell, `%BUT_TEXT%` under cmd.

| Variable | Example | |
| --- | --- | --- |
| `BUT_TEXT` | `GOAL! [Ligue 1] Marseille 2 - 1 Paris FC - Goal by M. Greenwood (67')` | the ready-made sentence |
| `BUT_TYPE` | `goal` | `goal`, or `cancelled` when VAR takes it back |
| `BUT_LEAGUE`, `BUT_LEAGUE_CODE` | `Ligue 1`, `fra.1` | the competition, and its ESPN code |
| `BUT_HOME`, `BUT_AWAY` | `Marseille`, `Paris FC` | both teams |
| `BUT_HOME_SCORE`, `BUT_AWAY_SCORE`, `BUT_SCORE` | `2`, `1`, `2 - 1` | the score after the goal |
| `BUT_TEAM`, `BUT_OPPONENT`, `BUT_SIDE` | `Marseille`, `Paris FC`, `home` | who has just scored |
| `BUT_SCORER`, `BUT_MINUTE` | `M. Greenwood`, `67'` | empty until the source publishes them |
| `BUT_OWN_GOAL`, `BUT_PENALTY` | `0`, `0` | `1` or `0` |
| `BUT_DELTA` | `1` | `-1` when the goal is taken back, `2` when a missed one is caught up |

These names are a **contract**: they go and live in scripts that are not in
this repository, so they will not change. They are in English, unlike the rest
of the project, because a script gets shared across the five languages of the
cards.

**Tuning the command without waiting for a goal:**

```bash
butbutbut --test-hook
```

The command runs against a made-up goal, right away, and butbutbut shows the
variables it receives, its output and its exit code. Without this, getting a
hook right would mean waiting for the next goal with a daemon that stays
silent when everything works.

```
butbutbut : but fabrique, la commande recevra
  BUT_AWAY           Paris FC
  BUT_HOME           Marseille
  BUT_SCORER         M. Greenwood
  ...
  commande    : notify-send "Goal!" "$BUT_TEXT"
  resultat    : code de sortie 0
```

A few commands that work as they are:

```bash
butbutbut --on-goal 'notify-send "Goal!" "$BUT_TEXT"'
butbutbut --on-goal 'echo "$(date +%H:%M) $BUT_TEXT" >> ~/my-goals.txt'
butbutbut --on-goal 'test "$BUT_TYPE" = goal && mpv ~/sounds/airhorn.mp3'
```

**Recipes that already work.** A way out is of no use if nobody knows what lies
behind it: nobody will write their Discord webhook starting from a
`notify-send`. So the
[`recipes/`](https://github.com/boubou666/butbutbut/tree/main/recipes) folder
holds eight complete commands, to copy and to trim — a Discord webhook, a Slack
webhook, a Home Assistant event your home automation answers, a WiZ bulb that
turns green for the length of the goal then goes back to exactly the state it
was in, a JSON goal counter that follows VAR cancellations too, a real system
notification that stays in the notification centre, a text banner for OBS or a
status bar, and a shell template to react only to the goals you care about.

```bash
butbutbut --on-goal 'python3 ~/butbutbut/recipes/discord_webhook.py'
```

Zero dependencies there as well: nothing but the Python standard library, or
the machine's shell. No `curl` assumed to be there, no `jq`. A secret — webhook
URL, token — is read from an environment variable and **never** travels through
the command line, which shows up in `ps` and which `butbutbut --status` prints
back. The instructions, each recipe's settings and where to put the secret on
each system are in
[`recipes/README.md`](https://github.com/boubou666/butbutbut/blob/main/recipes/README.md)
(in French, like the rest of that folder).

Those recipes travel with the source code, and not inside the package `pipx`
installs: butbutbut never runs them itself, you do. A test in the repository
compares the `BUT_*` variables they read with the ones the hook really
publishes — a recipe cannot rot silently by promising a detail that does not
exist.

**What the hook promises:**

- **The data travels through the environment, never through the command.** A
  team name is therefore never pasted into a shell line: the day the source
  announces a club called `; rm -rf ~`, nothing will happen.
- **A goal never waits for the command.** It runs in its own thread and nobody
  watches for its end: a slow script delays neither the card nor the next
  poll. Past 30 seconds, it is killed.
- **It cannot bring butbutbut down.** Command not found, non-zero exit code, a
  script that never returns: one line in the log, and life goes on. Success,
  on the other hand, says nothing - a hook that fires on every goal has no
  business filling the log.

The hook fires on a goal **and on VAR taking it back**: announcing a goal and
then staying quiet when it is disallowed would lie to whatever you feed.
`BUT_TYPE` tells the two apart in one word. The key moments of a match,
sendings-off and pre-match announcements trigger nothing: the option promises
a goal.

The team filter applies as it does elsewhere: with `--teams om`, only OM's
goals run the command. The `on_goal` key of the configuration file does the
same without retyping the option, and `butbutbut --status` recalls what is
armed. A match set to `--spoiler-free` runs nothing: the hook is one
more alert, and spoiler-free mode cuts them all - otherwise a light strip or a
webhook would tell you the goal the screen and the speaker just went quiet
about.

### Language

The cards **and the command line** speak the language of the machine, among the
five of the big-five leagues - French, English, Spanish, Italian, German -
falling back to French when it is none of them.

```bash
butbutbut --lang de       # force German
butbutbut --lang de --help   # the help too
butbutbut --status        # the "language" line says which one was picked
```

```
TOR!   BUNDESLIGA                                              89'
Eintracht Frankfurt      1 - 4      FC Augsburg
Tor von F. Rieder
```

Competition names follow: the Champions League becomes CHAMPIONS LEAGUE, the
World Cup WELTMEISTERSCHAFT. The ones whose name is a proper noun are left
alone - the Bundesliga, Serie A or the Coupe de France are spelled the same
everywhere.

**Every** command follows, down to the values they print - `il y a 12 s`
becomes `vor 12 s`, not just the label in front of it: the help, `--status`,
`--scores`, `--next`, `--table`, `--screens`, `--list`, `--list-teams`,
`--today`, `--week`, `--month`, `--since`, `--top-scorers`, `--stats`,
`--export` and `--test-hook`.

The columns hold in all five languages. That constraint is what decides how a
`--status` label is translated: the colon lands on the same character
everywhere, abbreviating where it must (`rattrapage` becomes `catch-up`,
`recuperacion`, `recupero`, `Nachholen`).


The `--table` column headings follow the same rule, and for the very reason
they were a problem: `G`, `N`, `P` are the initials of gagne, nul and perdu,
and mean nothing to an English reader. They become `W D L`, `G E P`, `V N P`,
`S U N` - each fitting a six-character column, which a test checks language by
language rather than trusting the eye.

**What stays in French**:

- **the log, and by choice.** `--today` reads it back, and a file written
  before a language change would otherwise be half unreadable to the parser.
  So a card can read `TOR!` while the log records `BUT` - and a line quoted
  back by `--today` stays in the language it was written in;
- **dates.** Weekday names (`lundi`, `mar.`), `(aujourd'hui)` and `(demain)`,
  and the `--next` countdown (`dans 3 h`) are hard-coded in `cli.py` and never
  reach the catalogue;
- **the `--status` values that also go to the log.** Three families, one
  reason for all three: the same sentence serves the screen AND a log line,
  which stays French. The `silence` and `voice` lines
  (`silence.describe()`, `speech.describe()`), the `equipes` line
  (`teams.Filter.describe()`, which the daemon also writes at startup), and
  the detail of a named sound it cannot play (`sound.unusable()`, which the
  log repeats when a file vanishes mid-evening). The labels themselves are
  translated;
- **the commented configuration file** written by `--write-config`, and the
  six messages that reject an impossible argument: the four at startup
  (`--speed 0`, `--record` together with `--replay`, `--retry-fullscreen` and
  `--quiet-while-presenting` off Windows) and the two in replay (an unreadable
  recording, a recording that names no recognisable competition);
- **the sport name inside one templated phrase.** `tout le {} (N competitions)`
  gets the name of the sport, which `sports.py` keeps in French for the log:
  translating the frame would produce a half-translated sentence. The catalogue
  headings themselves are translated (`Ice hockey (on request)`, `Eishockey
  (auf Wunsch)`).

A phrase a catalogue does not carry falls back to French rather than
disappearing: an unfinished translation leaves the program usable. That is what
let seven commands ship in French across all five languages without anything
breaking - and without anyone noticing. A test now compares, language by
language, the phrases the code hands over for translation against what the
catalogues carry: whatever stays in French is named there one by one, with its
reason.

That guard has an exact reach, and it is worth stating: it only sees what goes
**through `tr()`**. A hard-coded sentence, never handed over for translation,
is invisible to it - which is the case for the three families above and for
weekday names. It stops the debt from coming back through the door it used
seven times; it does not replace looking at the screen in all five languages.

Precedence, strongest first:

| | |
| --- | --- |
| 1 | `--lang de`, or the `lang` key in the configuration file |
| 2 | the `BUTBUTBUT_LANG` environment variable |
| 3 | the language of the system |
| 4 | French |

On Windows the system API comes before `LANG` and friends: a shell like Git
Bash sets `LANG=en_US` whatever happens, which would make detection blind to
the real language of the machine. And Windows can answer two different
languages - the one of its interface and the one of the regional settings. The
first one wins, following Microsoft's own convention for interface text; if your
machine shows English menus while you want it in French, `lang = fr` in the
configuration file settles it.

---

## Where the scores come from

**A single source, the same one for every competition**: ESPN's public
scoreboard, one endpoint per competition.

```
https://site.api.espn.com/apis/site/v2/sports/<sport>/<code>/scoreboard
```

| League | Code |
| --- | --- |
| Ligue 1 | `soccer/fra.1` |
| Premier League | `soccer/eng.1` |
| LaLiga | `soccer/esp.1` |
| Serie A | `soccer/ita.1` |
| Bundesliga | `soccer/ger.1` |

That is also what makes the catalogue extensible: Ligue 2 is `fra.2`, the
Champions League `uefa.champions`, the Coupe de France `fra.coupe_de_france`...
same response format, same reading code.

The **first segment is the sport**, and it is the only thing that changes
outside football: `hockey/nhl`, `rugby/180659`. Rugby is keyed by a number
rather than a word; every one of them was checked against the source, one by
one. See [Sports](#sports) for what each one actually publishes.

Why this source: no API key, no sign-up, no quota to keep an eye on, it is
updated live, and it gives the **scorer**, the **minute**, **own goals**,
**penalties**, each club's **crest** and its **colours**. It is a public but
undocumented API: everything is read defensively, and a key that disappears
does not kill the daemon.

Left alone, the endpoint only serves **the current day**: enough to watch for
goals, not enough to say when the next match falls. For that it accepts a
`dates` parameter, either one day (`?dates=20260908`) or a range
(`?dates=20260908-20260915`), both ends included. That range is what lets
`--next` cover a whole week in a single request per competition, where one day
at a time would cost seven.

The same host publishes two more endpoints, read with the same client and the
same headers: `.../teams`, which validates what you type into `--teams`, and the
table behind `--table`, whose address does not quite have the same shape.

```
https://site.api.espn.com/apis/v2/sports/<sport>/<code>/standings
```

`apis/v2`, not `apis/site/v2` like the scoreboard: the second address does
exist, and answers 200 with an empty object - an off-season by appearance, the
wrong door in reality. The difference is noted in the code so it does not have
to be rediscovered.

Everything we know about this source - the parameters it accepts, the exact
shape of its responses, its headers, its error codes, its traps, and the 218
football competitions it exposes - is gathered in
[docs/api-espn.en.md](docs/api-espn.en.md): the contract we write for
ourselves, since the provider writes none. Every line of it was checked
against the real source, and the document gives the commands to redo all of
it.

### How a goal is detected

On every poll, each match's score is compared with the one from the previous
poll. **A score that goes up is a goal.** ESPN's list of events only serves to
dress the card (scorer, minute, own goal, penalty): it sometimes arrives a few
seconds after the score, and the goal must not wait for the scorer's name.

That is exactly why the other sports cost the detection nothing: a score going
up is a score going up, whether it gains 1 in football and hockey or 5 in
rugby. Hockey, which publishes no events in the scoreboard, is therefore
followed just as well as the rest - it is afterwards, and for it alone, that a
match summary goes looking for the scorer's name (see "What each sport really
publishes").

Two safeguards:

- **the first poll fires nothing.** It photographs what is already there.
  Otherwise, starting the daemon on a Sunday at 5 pm would replay every goal
  already scored;
- **a score that goes down** (a goal ruled out by VAR) shows an orange
  `BUT ANNULE` card - goal disallowed - with no sound.

### Penalty shootouts

A shootout is the one moment where the source says "goal" eleven times without
anyone scoring. Everything therefore hangs on a single question: **does the
published score move during the shootout?** The answer was fetched from real
knockout matches already played, and it is **no**.

| Shootout | What the source publishes |
| --- | --- |
| Chelsea - Liverpool, FA Cup final, 14 May 2022 | score `0 - 0`, `shootoutScore` 5 and 6, eleven kicks, status `STATUS_FINAL_PEN`, detail `FT-Pens` |
| Angers - Reims, Coupe de France, 25 February 2025 | score `1 - 1`, **no `shootoutScore` at all**, eight kicks timed 91' to 99', same status |
| Argentina - France, World Cup final, 18 December 2022 | score `3 - 3`, `shootoutScore` 4 and 2, six kicks, same status |
| Atletico - Real Madrid, Champions League, 12 March 2025 | score `1 - 0`, `shootoutScore` 2 and 4, six kicks, same status |

The score stays the one from the end of normal time, and the shootout is
published **alongside** it. So there is **no cup night with ten air horns**:
detection only watches the score, the score does not move, nothing fires. The
bug we feared does not exist, and establishing that was the first half of this
work.

The opposite gap did exist, though, twice over.

**A shootout kick looked like a goal.** Every converted kick is published in
the same array as the goals, carrying the same flag:

```json
{"type": {"text": "Penalty - Scored"}, "scoreValue": 1, "scoringPlay": true,
 "penaltyKick": true, "shootout": true, "clock": {"displayValue": "120'"}}
```

That array is the one that dresses the cards and that `--scores` copies out. An
FA Cup final that ended 0-0 therefore produced a `FIN DU MATCH` card reading
`Chelsea 0 - 0 Liverpool` followed by **eleven scorers**. Kicks are now set
aside at read time: the `shootout` flag is the only thing that tells them apart
from a real goal, and it is the only thing worth trusting, since the score
itself contradicts them.

**A shootout did not say who went through.** `FIN DU MATCH / Angers 1 - 1 Stade
de Reims` is accurate and misses the point. The third line now says it, with
the winner highlighted the way a scorer is elsewhere:

```
FIN DU MATCH
Angers 1 - 1 Stade de Reims
Tirs au but 3 - 5 : Stade de Reims
Angers : B. Dieng 90'+5'
Stade de Reims : K. Nakamura 79'
```

The tally comes from `shootoutScore` when the source gives it. It is missing
about one time in ten - the Coupe de France night of 25 February 2025 did not
carry it, with nothing else setting it apart - and the converted kicks are
counted instead, which yields the same number everywhere both were available.
The winner's name comes from the `winner` flag: it is the only thing in the
response that can say who goes on from a 1-1. Without it the card just says
`Tirs au but` - it does not invent a qualifier.

The card stays **silent**, like every full-time card: a verdict is written, not
sounded.

**Hockey** never had this problem, for a reason that comes from the rulebook: a
shootout there **awards a goal to the winner**, inside the match score. Vegas
4-3 Chicago on 3 December 2025, status `STATUS_FINAL` and detail `Final/SO` -
the score really does move, once, at the right moment, and butbutbut announces
that goal like any other. Which is correct: the NHL calls it the game-winning
goal too. The full-time card only adds `Vainqueur aux tirs au but : Vegas
Golden Knights`, because a 4-3 that did not happen in regulation deserves an
explanation. Note in passing that hockey does not say it in the same place: its
status stays `STATUS_FINAL`, only the detail changes.

**Rugby union** carries no marker at all: the laws do provide for a kicking
competition, it has never been used in a professional match, and watching for a
string ESPN has never had to write would be watching for an invention.

**What is left open.** All of this is established on **finished** shootouts.
What the source publishes during the few minutes a shootout lasts - a
`STATUS_SHOOTOUT` status? a score that would go up and come back down? - could
not be observed: it would have taken sitting in front of a knockout tie at
exactly the right moment. Since the final score is the end-of-normal-time score
in all four competitions sampled, there is no reason to think it moves in
between - but that is a deduction, not an observation, and it is written down
here so that the day someone sees one card too many, they know where to look.

### Waking from sleep

If the machine sleeps, hibernates, or the process is frozen for the length of
a half, the scoreboard has run hours ahead of the last photograph: comparing
against it as it stands would put out a `BUT` card with a delta of 3 and a
stale minute, or even a `COUP D'ENVOI` for a match that has already finished.

Before every poll, the daemon compares the wall-clock time that has actually
elapsed with the time it meant to wait. Beyond **two minutes of lateness**
(enough to let a loaded machine, or a poll dragged out by the 8 s HTTP
timeout, pass without a murmur), it concludes that it has jumped through time.
Two behaviours from there, depending on what you asked for.

#### By default: silence

It **re-photographs every score**, exactly as on the first poll, and notes it
in the log:

```
2026-09-06 21:14:07  trou de 47 min dans le temps (veille, hibernation ou processus gele) - on rephotographie les scores sans rien annoncer
```

Watching then resumes as normal, and the next goal is announced as usual. The
goals that went in during the sleep, however, are lost: that is the price of
not talking nonsense.

#### With `--catch-up`: one summary card

```bash
butbutbut --catch-up
```

The photograph taken before the gap is no longer thrown away: it is set aside,
then compared with the one taken on waking. Because the source publishes each
match's table of events with **stable keys**, we know exactly which goals we
never saw - and therefore what can be told without making anything up.

```
PENDANT TON ABSENCE   LIGUE 1                                     47 min
Angers              0 - 2              Stade Rennais
avant 0 - 0 : A. Kalimuendo 58', L. Blas 77'
Lens 1 - 0 Lille (avant 0 - 0) : F. Sotoca 23'
```

What that card does **not** do matters as much as what it says:

- **one card**, never one per goal. Replaying three cards with stale minutes on
  them is precisely what the silence was avoiding;
- **no sound.** An hour-old goal does not get the horn. It is a discreet card,
  like half-time or a red card - and like them it has its own switch:
  `--no-phase-cards` does not turn it off;
- **nothing to say, no card at all.** If nobody scored during the sleep the
  screen stays empty; the log still records the catch-up;
- the **team filter** applies: with `--teams om`, only Marseille's matches show
  up on it;
- a match that **started and finished during the sleep** is left out too: we
  followed none of it, the same rule as for the full-time card.

The first match concerned takes the score line, the others get one line each
below it. A whole night of World Cup fixtures will not make the card overflow:
it is cut in height as well as in width, by the very mechanism that already
trims the list of scorers on the full-time card. The log keeps everything:

```
2026-09-06 21:14:07  trou de 47 min dans le temps (veille, hibernation ou processus gele) - on rephotographie les scores, et on resume ce qu'on a manque
2026-09-06 21:14:09  rattrapage : 2 match(s) ont bouge pendant les 47 min d'absence
2026-09-06 21:14:09  PENDANT TON ABSENCE [Ligue 1] Angers 0 - 2 Stade Rennais - avant 0 - 0 : A. Kalimuendo 58', L. Blas 77' - Lens 1 - 0 Lille (avant 0 - 0) : F. Sotoca 23' (47 min)
```

`butbutbut --status` shows which of the two behaviours is armed on its
"rattrapage" line, and the `catch_up` key in the configuration file turns it on
without retyping the option.

The measurement is taken on the wall clock and not on `time.monotonic()`: on
Linux, monotonic is frozen during sleep and would therefore see no gap at all,
whereas on Windows it carries on ticking. That is also why the summary waits
until **every** competition being followed has been re-photographed: their due
times do not all come round on the same poll, and a summary with holes in it
would be worth less than nothing.

### Polling rate

Each league has its own rhythm, so as not to hammer the source:

| Situation | Poll |
| --- | --- |
| a match in play | every 25 s (`--interval`) |
| kick-off in under 20 min | every 60 s |
| nothing on the schedule | every 5 min (`--idle-interval`) |

On a Tuesday evening with no Bundesliga, the Bundesliga is polled every five
minutes. If the network drops, the wait doubles on every failure (capped at
5 min) and the recovery is noted in the log.

And the polls are **compressed**. The source can serve gzip, but it has to be
asked: nobody does it for you, `urllib` advertises nothing on its own. The
Ligue 1 scoreboard drops from 33,832 to 4,145 bytes, and a full round of
`--leagues all` from **1,355 kB to 148 kB** - nine times less. Over a
two-hour evening following all 36 competitions, 400 MB become 44 MB: enough to
leave the program running on a phone hotspot without thinking about it.
Nothing to install, `gzip` is in the standard library, and an uncompressed
answer still goes through untouched.

It is the only saving available, and not for want of looking for the other
one: the source sends **no `ETag` and no `Last-Modified`**, so there is
nothing to put in a conditional request that would have skipped the unchanged
polls.

### The canary

That source is documented nowhere, and nobody will warn us the day
`penaltyKick` gets renamed or `athletesInvolved` moved. Nothing would break:
the reading is defensive, so the daemon would keep running - it would simply
stop announcing penalties ever again. A silent failure, the worst kind. And
the 523 tests would see nothing of it: they are the ones fabricating ESPN's
reply.

Hence a canary, which you can run by hand:

```bash
python tools/canari.py
python tools/canari.py --leagues fra.1,ger.1 --dates 20250517
```

It queries the source for real, then checks that every key read by
`butbutbut/espn.py` is still there, and of the right type. It even hands the
reply back to `espn.parse()`, the very code the daemon runs: keys that are
present but no longer yield a match, a goal or a scorer would be just as
serious a drift.

What it looks at depends on the sport, because the three do not publish the
same things. Football and rugby have their event list in the scoreboard;
hockey has none at all, and demanding `details` from it would mean watching
every morning for a key we know does not exist. Since its scorers live in the
match summary, `hockey:nhl` is one of the competitions queried by default and
the `plays[]` keys - the type of the play, each participant's role, the
player's name - are watched for it alone. One summary per competition per run:
it is 450 kB, and the question answers itself on one match as well as thirty.

Rugby does have that list, but not that grammar: its plays carry no flag at
all - what a play is reads from `type.id`, "1" for a try - and its teams have
neither town nor secondary colour. Demanding `scoringPlay` or `alternateColor`
there would mean watching for keys ESPN has never published for that sport: red
every morning, hence a red you learn to stop reading. In exchange, one drift
belongs to rugby alone: were those numbers to change, not a single key would be
missing and not a single play would be recognised any more. The scoreboard is
what would tell - a day of finished matches, points on the board and not one
play: red line.

A key can also stay in place and **change shape**, which shows up nowhere else.
So the canary re-reads goal minutes with the log's own reader, the one behind
the `--stats` histogram: a clock nobody can read any more earns a red line.
Football alone is held to that rule - `12:34`, an ice hockey clock, is not a
minute of play.

The report gives one line per key:

```
  ok           competitor.team.color                        couleur hex     6/6
  ok           detail.penaltyKick                           booleen         16/16
  MANQUE       detail.athletesInvolved[0].shortName         texte non vide  0/16
```

Three verdicts, and the nuance is the whole point:

| Verdict | What it means |
| --- | --- |
| `ok` | the key is there, with the right shape |
| `MANQUE` / `TYPE` | it is gone, or changed shape - non-zero exit code |
| `non verifie` | nothing of that kind showed up (no goal that day): this is not a failure |

On a Tuesday in July the day's board can be empty: the canary does not cry
wolf over that. It then asks again for the last four months in one go
(`?dates=YYYYMMDD-YYYYMMDD`), enough to land on matches that were actually
played - and therefore on goals to inspect - in any season.

It also runs on its own once a day
([`canari.yml`](.github/workflows/canari.yml)), and **never on a push or a
pull request**: the ordinary CI must stay offline and deterministic, otherwise
an ESPN outage would paint changes red that have nothing to do with it - and
we would soon learn to ignore red. A red canary, for its part, opens an issue
carrying its report.

**And when it does turn red?** The report names the key, what was expected,
and how many times it was missing. Everything that reads it lives in
`butbutbut/espn.py` (`parse()`, `_parse_details()`, the `team_*()`). Then it
is a decision: the source renamed it (follow), moved it (go and fetch it
elsewhere), or dropped it (remove the feature rather than display a blank).
The change then has to reach the payloads fabricated by `tests/helpers.py`,
otherwise the offline suite would keep validating a world that no longer
exists.

---

## What happens on screen

- **a borderless window, always on top**, which never steals focus;
- **crests** read from the disk cache, never from the network: each card keeps
  a reference to its images, otherwise tkinter forgets them and they vanish
  from the screen;
- **Windows**: a genuinely transparent background (rounded corners) and a
  *click-through* window: clicks pass straight through, you can carry on
  playing;
- **macOS**: a borderless window, absent from the Dock;
- **Linux**: a *splash*-type window, laid on top;
- **multi-screen**: the screens are enumerated through the system API
  (`EnumDisplayMonitors`, `xrandr --listmonitors`, CoreGraphics), not through
  tkinter, so that a card never ends up straddling two displays.

The display lives in the main thread (tkinter insists on it), the network
watching in a thread of its own: a slow request never freezes a card on
screen.

### When an app is full-screen

A card is an *always-on-top* window, but a game or a video player running
**full-screen** goes in front of it: the goal then falls into the void. Before
every card, butbutbut therefore looks at whether the foreground window covers
the whole of the target display (`GetForegroundWindow` + `GetWindowRect`
compared with the monitor's `rcMonitor` - the entire display, not the work
area - and the absence of `WS_CAPTION` / `WS_THICKFRAME`, which tells a
full-screen window apart from one that is merely maximised). The card goes out
anyway, since the detection can get it wrong, but the log keeps a trace of the
goal you probably missed:

```
2026-09-06 21:07:02  BUT [Ligue 1] Marseille 2 - 1 Paris FC pour Marseille - But de M. Greenwood (67')
2026-09-06 21:07:02  une application en plein ecran occupe \\.\DISPLAY1 : la carte y est probablement invisible
```

The sound, for its part, fires as usual.

**It never pulls anyone out of full screen, though.** A card is never
activated and has no taskbar button (`WS_EX_NOACTIVATE` and
`WS_EX_TOOLWINDOW`, set **before** it is first shown). Without them Windows
would hand the card the foreground the moment it appears; and when it refuses
the steal, it flashes the card's taskbar button instead - a flashing button
brings the taskbar back over the game, and full screen is lost over a goal.
The order matters as much as the styles: set after the window is shown, they
arrive once the damage is done.

```bash
butbutbut --retry-fullscreen        # show the card again later (120 s at most)
butbutbut --retry-fullscreen 300    # ... for 5 minutes
```

With this option, the hidden card stays in the queue and **comes back as soon
as the screen frees up** (game quit, full-screen exited); if the screen is
still taken when the delay runs out, the card is dropped, again with a line in
the log.

A Windows system notification was ruled out: Windows holds toasts back
precisely while an application is full-screen, so the promise would have been
kept exactly when it was of no use.

> **Windows only.** X11, Wayland and macOS give no reliable, portable answer
> to the question "is a full-screen window occupying this display?". Rather
> than a heuristic that gets it wrong, butbutbut detects nothing there: cards
> show as before, with no extra log line, and `--retry-fullscreen` is refused
> with a warning.

This is the first of the three times butbutbut asks itself "is this the
moment?" - the other two are what time it is and who else is watching, and they
do not return the same verdict: see [Do not disturb](#do-not-disturb).

---

## Recording a real match, and replaying it

`butbutbut --test` shows made-up cards: pretty, but frozen. The real sequence -
kick-off, goal, red card, half-time, a goal ruled out by VAR, full-time - only
happens on a Saturday night. `--record` puts it in a box, `--replay` takes it
back out as many times as you like.

```bash
butbutbut --record match.jsonl --leagues l1    # while the match is on
butbutbut --replay match.jsonl                 # later, in real time
butbutbut --replay match.jsonl --speed 60      # an hour of football in a minute
```

It does three things at once:

- **it sorts out the display** without waiting for the next Saturday: the card
  that overflows, the missing crest, the unreadable colour all get fixed by
  replaying the same match ten times in a row;
- **it reproduces a bug**: "the card overflows on that match here" becomes a
  file of a few megabytes you attach to the ticket, and the person on the other
  end sees exactly the same thing;
- **it makes the screenshots and GIFs** in this README, with real names, real
  scores and a real sequence.

### `--record`: sitting between the program and the source

`--record` changes nothing about the watch: the daemon runs normally, shows its
cards, plays its sound and writes its log. It **also** writes every raw ESPN
response to disk, with its timestamp and the competition code. All the usual
options still apply:

```bash
butbutbut --record psg-om.jsonl --leagues l1 --teams psg,om --red-cards
```

There is a good reason to pass `--leagues`: see below, what it weighs.

### `--replay`: the same evening, with no network

The replay does not read the file looking for goals. It **replaces the source**
and lets the rest of the program do its job: comparing scores, the silent first
poll, the scorer picked from the plays, the polling rate that adapts, the cards,
the sound, the log lines - it all goes through the same paths as a real Saturday
night. That is the only way a replay proves anything: a replay that took a
shortcut would only ever test itself.

`--speed` divides the gaps between two polls. `--speed 1` (the default) replays
in real time, `--speed 60` fits an hour of football into a minute. The
competitions replayed are **the ones in the file**, not the ones in `--leagues`:
a Ligue 1 recording replays as Ligue 1, whatever you type.

```
2026-09-07 21:04:11  rejeu de match.jsonl - 288 releve(s) - Ligue 1 - 1 h 52 - enregistre le 2026-09-06 20:41:03 - x60
2026-09-07 21:04:13  COUP D'ENVOI [Ligue 1] Angers 0 - 0 Stade Rennais (3')
2026-09-07 21:04:22  BUT [Ligue 1] Angers 1 - 0 Stade Rennais pour Angers - But de B. Saka (12')
2026-09-07 21:05:06  FIN DU MATCH [Ligue 1] Angers 1 - 0 Stade Rennais - Angers : B. Saka 12' (FT)
```

(The log stays in French whatever the language of the cards - see
[Card language](#card-language).)

Red cards and the pre-match announcement stay opt-in on replay just as they are
live: `--replay match.jsonl --red-cards` brings them out even if the recording
was made without.

### The file format

**JSON Lines**: one line = one complete JSON object. Two properties follow, and
they are exactly the ones we were after - it reads with the naked eye, and a
session killed mid-match leaves a file where only the last line is rubbish.

The first line is a header, the following ones are the polls:

```json
{"kind":"butbutbut-record","format":1,"version":"1.5.0","recorded_at":1757270481.4,"recorded_text":"2026-09-06 20:41:21","leagues":["fra.1"]}
{"at":1757270481.6,"slug":"fra.1","payload":{"events":[...]}}
{"at":1757270506.7,"slug":"fra.1","repeat":true}
```

| key | what it is |
| --- | --- |
| `format` | the number of the **format**, not of the program |
| `at` | the time of the poll: it is the gap between two `at` that `--speed` divides |
| `slug` | the ESPN code of the competition (one file can carry several) |
| `payload` | the ESPN response, as it came, with nothing removed |
| `repeat` | response identical to the previous one for that competition (see below) |

**An older file stays replayable**, which is what `format` is for: a reader
accepts any number lower than or equal to its own. A file written by a future
version says plainly why it will not play, instead of going off the rails:

```
butbutbut : match.jsonl est enregistre au format 2, et cette version de
butbutbut ne lit que le format 1 : mets butbutbut a jour (butbutbut --update).
```

An unreadable line - the last one of a session killed halfway - is counted and
ignored, and the rest replays. So is an unknown key: that is what allows a field
to be added tomorrow without changing the format number.

Since every line stands on its own, a recording can be cut with the tools of the
system. Keeping the header and the twenty polls around the goal:

```bash
(head -1 match.jsonl; sed -n '120,140p' match.jsonl) > the-goal.jsonl
butbutbut --replay the-goal.jsonl --speed 10
```

### What a replay does not touch

A replay **pollutes neither `--today`, nor `--status`, nor the running daemon**.
The log, the state file and the pid file are redirected in one go to a `replay/`
subfolder of the data directory, for the duration of the replay:

```
~/.local/share/butbutbut/replay/butbutbut.log      <- the replay's log
```

The redirection happens at the root, in `paths()`, rather than in every
function: everything that goes through it is isolated, including the code
written tomorrow. In practice: a match from three weeks ago replayed this
morning does not show up in `butbutbut --today`, `--status` keeps describing the
real daemon, and **a match can be replayed while the daemon is running** - the
replay does not claim the single-instance pid file.

What is *not* redirected: the sound and the crest cache. Those are shared
caches, and isolating them would force every replay to download every crest
again - when a replay is precisely meant to do without the network. That is in
fact the only network access a replay can still trigger, when a crest is missing
from the cache; `--no-logos` closes that one too.

### What it weighs

An ESPN scoreboard is **60 to 200 kB of JSON**, depending on how many matches
are on. At 25 s per poll, two hours of a full round make about 290 polls, so
**20 to 60 MB per competition**. A whole evening recorded across the big five
would comfortably pass 100 MB: `--record` is there to keep *one* match, and
`--leagues l1` is not a stylistic precaution.

Two things bring that back to a sane size:

- **a response identical to the previous one is not written again.** The line
  boils down to its timestamp and the `repeat` marker: sixty-odd bytes instead
  of two hundred thousand. The time of the poll is kept - it is what carries the
  polling rate, and losing it would change the rhythm of the replay. During a
  live match it gains nothing (the match clock moves on every poll, so the
  response does too), but a competition at rest - which is most of an evening -
  comes down to one line every five minutes;
- **gzip**, when the file name ends in `.gz`. Compressed on write, decompressed
  on read, without being asked. API JSON compresses about twenty times over: the
  40 MB of a match fit in 2 MB, and the file is still readable with `zcat`.

A hockey evening adds **450 kB per goal** to that: the match summary the
program reads to get the scorer goes through the same `opener`, so it is
recorded like everything else. It has a key of its own -
`hockey:nhl@401809123` rather than `hockey:nhl` - without which it would join
the scoreboard's queue and the replay would hand a summary to something asking
for scores. A recording made before this feature carries none: the replay then
asks for a summary the file does not have, the card goes out with no scorer and
the log says so. Nothing breaks, you just lose the names.

```bash
butbutbut --record match.jsonl.gz --leagues l1
butbutbut --replay match.jsonl.gz --speed 60
```

On reading, the recording is loaded into memory in one go: that is on purpose, a
replay is a development tool, it runs in front of someone watching their screen.

### Making a screenshot or a GIF

1. **Record** a match, one single competition, while it is being played:

   ```bash
   butbutbut --record match.jsonl.gz --leagues l1 --red-cards
   ```

2. **Find the interesting passage.** The file is text, `grep -c` counts the
   polls and `sed -n` slices a range out (see above). A goal fits in three or
   four polls.

3. **Replay** it big, in the middle of the screen, and fast enough that the
   screen recorder does not have to run for ten minutes:

   ```bash
   butbutbut --replay the-goal.jsonl.gz --speed 30 --scale 1.6 \
             --position center --red-cards
   ```

4. **Capture** with the tool of the system: `Win`+`Alt`+`R` (Xbox Game Bar) or
   [ScreenToGif](https://www.screentogif.com/) on Windows, `Cmd`+`Shift`+`5` on
   macOS, [Peek](https://github.com/phw/peek) or `ffmpeg -f x11grab` on Linux.

The replay follows the polling rate the watcher computes, just like live: a
recording made with `--interval 25` replays at the same rhythm. Replayed with
rates other than the ones it was recorded with, it never skips a poll, but it
may take a little longer than the original match - `--interval` and
`--idle-interval` tighten it up.

---

## Knowing whether the watch is really running

A daemon that is alive but stuck looks just like a daemon that works: the pid
file says that a process exists, never that it is working. So on **every
poll** the daemon writes a small state file next to the pid file
(`butbutbut.json`, see `butbutbut --paths`): the poll's timestamp, the matches
in play and their scores, the day's goal counter, the competitions followed,
the pid.

The pid file itself carries two lines: the process number, and the date the
system created it. A number alone does not say who it stands for. Systems
recycle them, and on Windows a number can even answer long after the program
died - the process object outlives it as long as a handle stays open
somewhere. A daemon killed outright by a session ending was enough to block
every later one (`une instance tourne deja`) without a single goal being
announced, and `butbutbut --stop` could aim at a stranger. The creation date
settles it: two processes can share a number, never the instant they were
born.

`butbutbut --status` reads it back:

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

If nothing has come in for a long while, `--status` says so instead of
pretending:

```
  releve      : il y a 20 min  (2026-09-06 18:32:44)
                (!) plus rien depuis, alors que la cadence est de 25s : daemon bloque ou source injoignable ?
  en cours    : inconnu (le dernier releve est trop vieux)
```

The threshold follows the advertised polling rate: a few minutes when a match
is in play, wider at rest. The file is written in one go (a temporary file,
then `os.replace()`), so `--status` never reads a JSON cut in half; and if the
disk is full or the folder read-only, the write is abandoned in silence:
losing the state has never killed a daemon in the middle of a match. The file
disappears when the daemon stops.

---

## The day's round-up

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

The goals are read back **from the log**, not from the state file: the log
survives a reboot, a crash and the daemon being stopped, so `--today` still
answers the next morning, machine switched off in between. Whatever the log
cannot read is ignored without a fuss.

---

## Further back than today

The same parser, with a wider window:

```bash
butbutbut --week                 # the last 7 days, today included
butbutbut --month                # the last 30 days
butbutbut --since 2026-09-01     # since that date (YYYY-MM-DD)
```

`--since` wins over `--week` and `--month`. A date that isn't one is refused
straight away, with the expected format (these commands are not in the
translation catalogues yet, so they answer in French, like the log they read):

```
butbutbut : date illisible : 'hier'. Format attendu : AAAA-MM-JJ, par exemple --since 2026-09-01
```

### A few days: the detail

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

Beyond a single day, the day becomes the only heading and the competition
moves into a column: grouping by day **and** by competition would put a title
every other line. The detection time gives way to the minute of the match,
which says more once the evening is over.

### A month: one line a day

Thirty days of Ligue 1 are three hundred goals: the detail would not fit on a
screen. The density is therefore decided on what there is to show, not on the
window asked for - as long as the list fits on a screen it is given, beyond
that each day comes down to its own line:

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

A shorter window gives the detail back, and `--top-scorers` gives the names.

---

## The scorers' ranking

```bash
butbutbut --top-scorers               # the whole log
butbutbut --top-scorers --week        # over the last 7 days
butbutbut --top-scorers --teams om    # only Marseille's matches
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

Without a window, it is the **whole log**: a ranking is only worth something
once it has piled up. Ties share their place, and the ranking combines with a
window as well as with the team filter (`--teams`, `--exclude-teams`), which
also applies to `--today`, `--week`, `--month` and `--since`.

**A goal the VAR took back stays with nobody.** The log does not say which goal
an annulment erases - the `BUT ANNULE` line carries neither the scorer nor the
minute of the original goal, only the score gone backwards. The match is
therefore positional, exactly as the video referee does it: an annulment takes
back the last goal still standing for that team in that match. An annulment
whose goal fell before the window opened is deducted from nobody, and the
footer says so rather than stealing a goal from someone at random.

Finally, the source publishes its plays a few seconds late: a goal detected
before it is written without a scorer, and stays that way. Those goals count in
the total, never in the ranking, and the footer announces them.

---

## The shapes of the log

The log piles up months of goals. `--today`, `--week`, `--month`, `--since` and
`--top-scorers` all read them back, but all five return a **list**: one goal,
one line, in the order they fell. Yet a pile of goals has shapes no list ever
shows. Are more goals really scored late in a match? Which competition fills
the log? Which was the best evening of the summer? `--stats` looks at the very
same lines, in a pile.

```bash
butbutbut --stats                     # the whole log
butbutbut --stats --week              # over the last 7 days
butbutbut --stats --since 2026-08-09  # since that date
butbutbut --stats --teams om          # only the matches of OM
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

**Ten-minute slices**, because that is the grain football is told in: "right
before half-time", "in the last quarter of an hour". To the minute it would
take ninety lines to show nothing but noise. A goal at `90+3'` stays a goal of
the 90th and goes into the `81-90` slice: putting it elsewhere would flatten
the very bump one comes to see. And the histogram always covers the full ninety
minutes, even when the window holds three goals in the 12th: an empty slice is
a shape too, and stopping at the last goal would erase it. Extra time, in turn,
stretches the frame up to the 120th.

**An evening is not a calendar day.** The log turns the page at midnight, a
football evening does not: a 9 p.m. kick-off that goes to extra time, a South
American fixture, an NHL game watched from Europe. The goal at 11:50 p.m. and
the one at 12:12 a.m. belong to the same evening, and counting by date would
make two half-evenings, neither of which existed. Six in the morning cuts the
night. **Three evenings are named**, and any ties with the third are counted on
one more line - `... et 17 autre(s) soiree(s) a 6 but(s).` Naming them all would
push the rest of the output off the screen on a multiplex night; stopping at
three without counting the others would suggest a podium that does not exist.

**A goal the VAR turned down counts nowhere**, exactly as in
[the scorers' ranking](#the-scorers-ranking): the positional matching is the
same code, not a second one. Not in the histogram, not in the competition, not
in the evening. Annulments whose goal fell before the window opened are
reported separately.

**The nature of a goal comes from the head of its line**, the only thing that
carries it: `BUT SUR PENALTY`, `BUT CONTRE SON CAMP`, `ESSAI`, `PENALITE`,
`DROP`. When the source publishes the play too late, the goal is written `BUT`
and counts as one: that share is a floor, not an exact total. A single nature
in the window gets no table - "143 goals out of 143 are goals" teaches nobody
anything.

**And what is missing is missing out of honesty.** The log only writes what
moves: a 0-0 leaves no line at all, so `--stats` knows of no goalless match,
and its average is that of the matches **where a goal fell** - mechanically
higher than a season's, which the footer spells out. The assist, the foot, the
distance, possession: the source does not publish them, so nobody can count
them here. A minute the log does not write as a minute of play - an ice hockey
clock, a phase label, a line from a version we can no longer read - stays out
of the histogram, and the footer counts it rather than forcing it in sideways.

**The arithmetic happens offline**: it is all already in the file. One caveat,
the same one `--top-scorers` carries: naming a team first checks that name
against the catalogue, and that check does need the network. It is deliberate -
`--stats --teams om` returning an empty page over a typo would be worse than
silent - and an unreachable source says so, then lets the command through.
Without `--teams` or `--exclude-teams`, nothing leaves the machine.

A missing log, an empty one, or one where no line falls inside the window says
so in plain words, just like `--today`.

---

## The log as data

`--on-goal` covers the upstream side: the moment the goal drops, you can fire
off whatever you like. Nothing covered the downstream side. Months of goals lie
asleep in the log, and everything that got them out until now was **laid out for
a human eye**: aligned columns, percentage bars, shared ranks, totals spelled
out in words. A spreadsheet, a notebook, a graph: all of those want data.

```bash
butbutbut --export csv > buts.csv         # the whole log, into a spreadsheet
butbutbut --export json --month           # the last 30 days, as JSON
butbutbut --export csv --since 2026-08-09 # since that date
butbutbut --export json --teams om        # only Marseille's matches
```

Same windows and same filters as `--stats` and `--top-scorers`: `--week`,
`--month`, `--since`, `--teams`, `--exclude-teams`. With no window, it is **the
whole log**. And it is the same single read (`journal.goals_between`) as every
other round-up: a second parser would end up counting differently from the
first, and an export that contradicts `--stats` on the same log would be worth
nothing.

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

### The fields

| Field | What it carries |
| --- | --- |
| `timestamp` | When butbutbut saw the goal, in ISO 8601: `2026-09-06T18:43:27` |
| `evening` | The goal's evening, which is not always its day (see below) |
| `kind` | `goal` or `cancellation`: the shape of the log line |
| `nature` | `goal`, `own_goal`, `penalty`, `try`, `conversion`, `penalty_goal`, `drop_goal`, `points`, plus `cancelled` / `points_cancelled` for what the VAR took back |
| `standing` | Is the goal still standing, once the VAR has been through? |
| `league` | The competition, as the log wrote it |
| `home`, `away` | Home and away sides |
| `home_score`, `away_score` | The score **after** this line |
| `team` | The team that scored, or the one whose score went back |
| `scorer` | The scorer. Empty when the source had not published the play yet |
| `minute` | The minute of play, as a number. Empty when it is not readable |
| `stoppage` | Stoppage time, as a number. Empty when the minute is not readable |
| `clock` | The minute as written: `90+3'`, or an ice hockey clock |
| `detail` | The log's own sentence: `But de M. Odegaard`, `Score corrige` |

**Nothing more, because there is nothing more.** Every one of these fields comes
out of what the log really carries; none of them is filled in from the source at
export time. The assist, the foot, the distance, the scorer's full name: nobody
ever wrote those into this file, and a column that is always empty is a promise
kept by no one.

**The column names are in English and are never translated**, while all the
program's prose is. A column header is not a sentence, it is a contract: a
spreadsheet opened on an English machine and a script run on a French one must
read the same file, and a column that changed its name with the language would
break the second one on every trip. The contents, on the other hand, stay
exactly as the log wrote them - so, in French.

**Dates and times come out in ISO 8601**, never in the log's own layout: that is
the only shape a machine reads back without being told how. With no timezone,
though: the log writes the machine's own clock and does not say which one, and
bolting on a `Z` or an offset would invent a precision nobody has. `evening` is
the goal's **evening**, not its calendar day - the goal at 00:12 belongs to the
evening before, exactly as in [`--stats`](#the-shapes-of-the-log).

**The minute of play comes out as three fields** because it answers three
questions: `minute` to drop a goal into a histogram, `stoppage` to know whether
it fell in added time, and `clock` so as not to throw away what the log wrote
when it was not a football minute at all. An ice hockey clock (`12:07`) is
readable neither as a number nor as nothing: `minute` and `stoppage` stay empty,
`clock` keeps it intact.

### What the export says about the VAR

**Every line comes out, goals and cancellations alike, and each one carries
`standing`.** That is this command's central trade-off, and it is settled in two
moves because the question is a double one.

Saying nothing about cancellations would be a lie: the `BUT ANNULE` line really
did happen, it has its own timestamp, and it is what explains a score going
backwards. An export that erases it hands back a log nobody lived through.

Mixing them in with the goals would be just as much of a lie: a goal the VAR
took back is not a goal, and a spreadsheet counting those lines would find a
total neither `--stats` nor `--top-scorers` reports. Hence `standing`, on every
line: keeping the lines where it is `true` gives **exactly** the goals the rest
of the program counts, in a one-line filter.

The matching is `--top-scorers`' own, reused as is rather than rewritten
alongside: a cancellation removes the last goal still standing for the same team
in the same match. A cancellation whose goal fell before the window opened is
deducted from nobody, and the error output says so.

### The CSV, and the JSON

The CSV has **a header, a single line shape, and the comma as its separator**.
The comma rather than the semicolon a French spreadsheet expects: this file is
made to be read back by a program, and the comma is what all of them assume by
default. The semicolon would only please one locale, the reader's, which the
file cannot know at the time it is written; a spreadsheet that does not want a
comma asks at import time, whereas a script handed semicolons asks nothing and
reads everything crooked.

A comma, a quote or an accent in a team name is not some rare case to be pitied
- `Nice, OGC` is right there in the sample above. That is the standard library's
`csv` module's job: it quotes the cell as needed and `csv.reader` hands it back
intact, so **nothing is escaped by hand here**, for exactly that reason. The
file is **UTF-8** whatever the console claims - a Windows console happily
announces cp1252, and the export would die on the first accent if it believed it
- and its lines end with a plain `\n`, because this output goes down a pipe as
often as into a file.

The JSON is **one single big array**, one object per goal, and not JSON Lines.
`--record` does the opposite, and for a good reason: it is an endless stream,
written while a match is being played, and a cut in the middle must leave
everything before it readable. The export is the exact opposite - a finished
answer to a question that was asked - and the trade-off turns over with it. A
window of the log fits in memory without a second thought, so
`json.load(open(...))` in one line is enough, which JSON Lines rules out. And a
file cut short no longer parses, which is precisely what we want: as JSON Lines
it would still parse, silently, with the last goals missing. Better an export
that refuses to open than an export that lies by three lines.

### Two outputs, and only one carries the data

**The data goes to standard output, and nothing else goes there.** The window
covered, the totals, the warnings, the path to the log, the confirmation of the
names passed to `--teams`: all of it goes to **standard error**. A sentence in
the middle of a CSV makes it unreadable, and `butbutbut --export csv >
buts.csv` must produce a file, not a file plus a comment. In a terminal the two
mingle and you read everything; the moment you redirect, each goes where it
belongs.

```
$ butbutbut --export csv --week > buts.csv
butbutbut : export csv du dim. 31/08/2026 au dim. 07/09/2026
38 ligne(s) : 36 but(s) signale(s) dont 35 debout, 2 annulation(s).
Le champ 'standing' dit lesquels la VAR a repris.
Journal : /home/moi/.local/share/butbutbut/butbutbut.log
```

**A missing log, an empty one, or a window without a single goal are still valid
answers**: an empty JSON array, a CSV cut down to its header, and the
explanation next door. A consumer must never have to tell "nothing" from
"broken" - that is exactly the kind of difference that crashes a script on a
Sunday evening. A pipe closed halfway through (`--export csv | head`) does not
blow up either: it is reported on the error output, and the command leaves.

**The export happens offline**: it is all already in the file. The same caveat
as `--stats` and `--top-scorers`, and it is the only one: naming a team first
checks that name against the catalogue, and that check does need the network.
Without `--teams` or `--exclude-teams`, nothing leaves the machine.

---

## Log

```
2026-09-06 18:41:21  demarrage (pid 3752) - les 5 championnats - releve toutes les 25s en direct, 300s au repos
2026-09-06 18:41:21  15 match(s) au programme, 6 en cours, 3 a venir
2026-09-06 18:43:27  BUT [Premier League] Arsenal 2 - 1 Chelsea pour Arsenal - But de M. Odegaard (50')
2026-09-06 18:51:04  CARTON ROUGE [Premier League] Arsenal 2 - 1 Chelsea pour Chelsea - Chelsea : M. Caicedo (58')
2026-09-06 19:24:10  FIN DU MATCH [Premier League] Arsenal 2 - 1 Chelsea - Arsenal : B. Saka 12', M. Odegaard 50' ; Chelsea : C. Palmer 74' (FT)
```

Path: `butbutbut --paths`. The daemon also writes kick-offs, half-times,
full-time whistles, sendings-off and pre-match announcements there - even the
ones whose card went unnoticed on screen. That trace is what
`butbutbut --today` reads back.

---

## Requirements

- **Python 3.8+**
- **tkinter** (a system package on Linux: `tk`, `python3-tk`,
  `python3-tkinter` depending on the distribution; `brew install python-tk` on
  macOS)
- **an audio player** on Linux, for the mp3 only (`mpv`, `ffmpeg`, `sox`,
  `vlc`): the wav goes out natively, with no binary at all
- an internet connection

`butbutbut --status` checks all of that in one go, connection to the source
included.

---

## Updating

Once installed, butbutbut updates itself, on all three systems:

```bash
butbutbut --check-update    # says whether a newer version exists
butbutbut --update          # fetch, reinstall, restart the daemon
```

`--update` reads back the record left by the installer (`install.json`, in the
data folder) to find out **which options it was installed with**, then replays
the installer with the same settings. An update will not drag you back to the
big five leagues if you were following `l1,pl,ucl`. The daemon is stopped for
the duration of the operation and restarts behind it, on the same selection.
If the update fails along the way, the daemon starts again anyway, on the old
code.

It is the **latest release** that gets installed, downloaded from GitHub and
unpacked into a temporary folder. Your cloned repository, if you have kept
one, is left untouched: bringing it onto the tag would mean leaving it on a
detached HEAD, and it belongs to you.

### The bleeding edge, with `--dev`

```bash
butbutbut --check-update --dev    # where has the main branch got to?
butbutbut --update --dev          # go there
```

Here the cloned repository is used if it is still around (`git pull
--ff-only`), and the archive of `main` takes over if it isn't. That second
route needs neither git nor the original clone, so an installation whose
folder you have since deleted updates all the same.

Both commands aim at the same thing in each mode: releases by default, commits
with `--dev`. So `--check-update` cannot announce one release to you and
`--update` then install a different one.

### The configuration file stays in charge

The installer puts into the startup service only the options **you** gave it.
`./install.sh --leagues l1,pl,ucl` puts down `--leagues`, and nothing else.
The default values are not spelled out as arguments; otherwise they would
override the same key in `butbutbut.conf`, the command line always beating the
file.

Put another way: a bare `./install.sh` leaves the configuration file in charge
of everything, and `--update` respects that choice since it replays the same
options. The one exception is `--quiet`, always set, a session daemon writing
to an output that does not exist.

Your sounds, your configuration file and your log are left untouched: they
live in the data folder, and the installer only replaces the code.

If butbutbut did not come from the install scripts, `--update` refuses and
points you at the tool that manages it, rather than overwriting files that are
not its own:

| Installed by | Update |
| --- | --- |
| `install.sh` / `install.ps1` | `butbutbut --update` |
| `pipx install butbutbut` | `pipx upgrade butbutbut` |
| `pip install --user butbutbut` | `pip install --upgrade butbutbut` |
| Arch's `PKGBUILD`, a distribution package | `pacman -Syu`, `apt upgrade`... |

---

## Uninstalling

```bash
./uninstall.sh              # or --purge to wipe your own sounds too
```

```powershell
powershell -ExecutionPolicy Bypass -File .\uninstall.ps1    # or -Purge
```

---

## Tests

```bash
PYTHONPATH=".:tests" python -m unittest discover -s tests
```

**1645 tests**, with no network and no screen: the source is simulated by an
`opener`, the crest cache by a `fetcher`, the clock by a `FakeClock`, and the
geometry of the cards (stacking, overflow, truncation, the room left for
crests) is checked with a dummy font, hence without tkinter. Colour selection,
for its part, is a pure function: its invariant is tested over every pair from
a set of real colours - what comes out is always readable, or it is the
competition's colour. Recording, for its part, is checked by a full round trip:
a match played live against a simulated source, boxed up, then replayed - and
the two must produce exactly the same sequence of events.

No machine either: a test never reads the data directory of whoever runs it.
`helpers.isolate_data_dir()` redirects it to a temporary one, and it is the
configuration that makes this necessary - `config.apply()` pours the file into
the parser's defaults before the command line is parsed, so a developer
following Ligue 2 saw it turn up in tests that had never asked for it. CI never
saw a thing, its machines having no file: the worst kind of failure, one that
breaks only for the person actually using the program.

One single program in the repository really talks to ESPN, and it is not in
this suite: [the canary](#the-canary), `python tools/canari.py`.

### The blueprint of a card

`overlay.py` draws every card in the program, and its layout was held together
by nothing but spot assertions: the score stays centred, a red card bites
neither into the name nor into the score. Each one is right, none of them says
what the card looks like, and a two-pixel shift slipped between them without a
single test blinking.

So eleven cards are frozen as **ASCII blueprints** under `tests/plans/`: the
goal card, the pinned card, the pre-match card (twice: with and without the
stake in the corner, so that the identical height reads in plain sight),
kick-off, full time, a rugby card, a card with red cards on both sides, names
long enough to be truncated, and the goal card at two other `--scale` values.
Every blueprint carries a drawing and a table.

```
     0         80        160       240       320       400       480
  0 |+------------------------------------------------------------------+|
 16 |##  BUT !  LIGUE 1                                            35'  ||
 40 |##           oooo                                            oooo  ||
 56 |##           oooo Angers     1  -    2    Stade Rennais      oooo  ||
 80 |##  But de C. Arcus                                                ||
104 |+------------------------------------------------------------------+|

boite              x0     y0     x1     y1  contenu
------------------------------------------  ------------------------------
titre              29     16     74     31  "BUT !"
equipe dom.       143   46.5    209   66.5  "Angers"
score dom.        235     43    250     70  "1"
```

The drawing says where the score is, where the name is, where the crests (`o`),
the red cards (`R`) and the competition's stripe (`#`) are; the table gives the
same boxes to the pixel. Two more pixels of margin, and the title's row goes
from 29 to 31: the shift **reads** in the pull request's diff instead of having
to be guessed behind a number that changed. A reference image would have done
the same job, in binary, unreadable in review and dependent on the font
installed on the machine.

The blueprint goes through the drawing (`_draw`) and not only through the
layout (`_layout`): what is frozen is therefore what really reaches the screen,
drawing order included.

And it is **identical** across the three systems and the five Python versions
of the CI - otherwise it would only ever turn the CI red. The fonts are fake
and fixed (one width per character, one line height), not tkinter's, which do
not measure the same thing on an Ubuntu runner and on a Windows one; and the
scenarios' cards are written in `tests/blueprint.py` rather than built by
`Card.from_event`, because a blueprint freezes a geometry and has no business
breaking the day a translation changes.

After a deliberate layout change, **one** command regenerates the ten
blueprints:

```bash
python tools/plans.py
```

It is a `tools/` script and not an option of the program, for the same reason
as [the canary](#the-canary): those blueprints only serve the repository, and
`butbutbut --help` has no business carrying, for life, a line that speaks only
to the tests.

**The terminal mode does not go through it.** The question came up - the
repository already knew how to draw a card in ASCII, why do it twice? - and the
answer is that a blueprint transcribes a geometry **in pixels**, at one
character per eight pixels. Brought down to the size of a terminal, it makes the
strokes run into each other: "LIGUE 1" loses its digit under the edge of the
card, and the line of scorers walks over the score. That is normal, `blueprint`
is built so a two-pixel shift leaps out of a diff, not to lay out text. [The
terminal card](#no-screen-the-cards-written-in-the-terminal) therefore computes
its geometry in characters, and what stays unique is the source: the same
`overlay.Card`, built by the same `Card.from_event`. The guard against drift is
that `tests/test_terminal.py` renders **the very same frozen cards** as the
blueprints - so a shape of card added here arrives there on its own.

### Where it runs

[Continuous integration](https://github.com/boubou666/butbutbut/actions/workflows/ci.yml)
replays it on Linux, Windows and macOS, on **Python 3.9, 3.12, 3.13 and
3.14**, plus **3.8** on Linux alone. It is the two ends that matter: 3.8 holds
the floor announced in the requirements, and 3.14 is the one the repository is
written on every day - for a long while the only one never tried, which is
exactly the wrong one to forget. The versions in between (3.10, 3.11) are
supported without being tried: a deliberate bet, since what breaks from one
version to the next rarely breaks in the middle alone. And the floor only runs
on Linux, because what it is asked to prove is that the code still reads in
3.8, not that the three systems diverge at that version rather than the
others.

That floor, `3.8`, is written in sixteen places. Nine are named one by one:
`requires-python`, both badges, both requirement lists, and the installers'
four guards - the comparison that refuses, and the sentence that explains it.
The other seven are the headers under `recipes/`, and those are not named: they
are **discovered**, otherwise tomorrow's recipe would slip past the check -
which is precisely the flaw being repaired here.

The ceiling is written nowhere: it is deduced from the package classifiers and
from the matrix. A test in the repository confronts them all, because that is
exactly how 3.14 came to be missed - nothing tied those files together, and
everything stayed green.

---

## Versions

Changes are recorded in
[CHANGELOG.md](https://github.com/boubou666/butbutbut/blob/main/CHANGELOG.md),
in the [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) format. Every
version carries a `vX.Y.Z` tag and an automatically built
[release](https://github.com/boubou666/butbutbut/releases), with the package
attached.

### Publishing to PyPI

Publishing is the second job in
[`pypi.yml`](https://github.com/boubou666/butbutbut/blob/main/.github/workflows/pypi.yml):
it sets off with the tag, right after the release, and sends to PyPI
**exactly** the wheel and the sdist attached to it. Through **Trusted
Publishing**: PyPI trusts the workflow itself via an OIDC token, so there is
**no API token to store** in the repository.

The workflow is **inert by default**. As long as the steps below have not been
carried out, the job is skipped: pushing a tag goes on producing the GitHub
release as before, with no red failure. Only the repository owner can carry
out these steps, and only once:

1. **Have an account on [pypi.org](https://pypi.org/)**, with two-factor
   authentication enabled (it is mandatory in order to publish).

2. **Declare the trusted publisher.** The `butbutbut` project does not exist
   on PyPI yet, so you have to go through a *pending publisher*. In the
   account menu, `Publishing`, then `Add a new pending publisher`, `GitHub`
   tab. Fill in exactly:

   | Field | Value |
   | --- | --- |
   | PyPI Project Name | `butbutbut` |
   | Owner | `boubou666` |
   | Repository name | `butbutbut` |
   | Workflow name | `pypi.yml` |
   | Environment name | `pypi` |

   Careful: a *pending publisher* does not reserve the name, it only
   authorises the workflow to create it. Best not to let too much time drag on
   between this step and the first publication.

3. **Create the GitHub environment.** Repository, `Settings`, `Environments`,
   `New environment`, named **`pypi`** - the same word as in step 2. That is
   also the place to add, if you want one, a manual approval before every push
   to PyPI.

4. **Arm the publication.** Repository, `Settings`, `Secrets and variables`,
   `Actions`, `Variables` tab, `New repository variable`: name
   **`PYPI_PUBLISH`**, value **`true`**. That is the switch; without it the
   job stays skipped.

5. **Push a tag**, as usual:

   ```bash
   git tag -a v1.2.1 -m "1.2.1" && git push --tags
   ```

   `pypi.yml` checks the tag, builds the package, creates the release, then
   its second job sends that same package to PyPI. The *pending publisher*
   then becomes an ordinary publisher, and the project exists.

To catch up on a push without creating a new tag: `Actions` tab, workflow
**release et publication**, `Run workflow`, giving the tag you want. That is
the way out when publishing has been skipped - the variable not yet armed at
tag time, a PyPI outage, a rejected token. Same file, therefore same
publisher: nothing more to declare at PyPI.

> **Why a single workflow, and why that name.** Publishing first lived in a
> separate file listening on `release: published`. That could never work:
> Actions refuses to let an event produced by the `GITHUB_TOKEN` trigger
> another workflow, so as to avoid loops - a release created by
> `github-actions[bot]` wakes nobody. Observed while pushing `v1.3.0`, where
> that trigger did not produce a single run. The tag push, on the other hand,
> comes from a human. Hence one file with two jobs. And it is called
> `pypi.yml` because a trusted publisher authorises **one** file name: the one
> declared in step 2, and the job that exchanges the OIDC token has to live in
> it.

## License

MIT.
