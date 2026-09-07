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
systemctl --user enable --now butbutbut.service
```

### Without installing anything

```bash
python -m butbutbut --test 3
```

---

## Usage

```bash
butbutbut                     # watch in the background (the default)
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

**`--leagues all` is still the whole football catalogue**, exactly what it
meant before. Two reasons, and the first one is enough:

- **nobody asked for the NHL.** Someone who typed `--leagues all` to follow
  domestic cups must not find themselves, after a mere update, with hockey
  cards at two in the morning. An update does not change what you follow;
- `all` is already 36 endpoints. Pouring the other sports into it would make
  46 without that being a choice.

For really everything: `--leagues all-sports` (or `tous-sports`). And
`--leagues foot` means football alone, just like `all`.

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
| Event list | yes | **no** | yes, but with no flags |
| Scorer, minute of the action | yes | **no** | yes |
| Red cards (`--red-cards`) | yes | not applicable | yes |
| Table (`--table`) | yes | yes, per conference | yes, bonus points included |

**Hockey publishes no event list at all** - not during the game, not after it.
You get the score, the clock and the period; never the scorer. The card says so
by saying nothing: it shows the score and the minute, with no third line.
Better an honest card than an invented name.

**Rugby publishes everything, but without a single flag**: where football marks
a goal with `scoringPlay` and a sending-off with `redCard`, rugby only gives a
`type.id` (1 try, 2 conversion, 3 penalty goal, 4 drop goal, 6 red card). Read
with football's reader, a rugby match would have no events at all - which is
why it has its own.

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

```bash
butbutbut --no-sound          # silent
butbutbut --no-overlay        # just the sound and the log, no card
butbutbut --no-logos          # no crest on the cards
butbutbut --duration 8        # keep the card for 8 s (default: the length of the sound)
```

### The key moments of a match

Beyond goals, a card marks **kick-off**, **half-time**, the **restart** and
**full-time**. They are deliberately plainer: the title is grey instead of the
league's colour, no team is singled out, and above all **they make no noise at
all**. Only a goal fires the sound.

```bash
butbutbut --no-phase-cards    # only goals on screen
```

The log, for its part, keeps a trace of these moments even with that option on.

The **full-time** card goes a little further: it lists each side's scorers
under the score, because a bare `1 - 2` does not say who scored, and that is
precisely the question when you haven't watched the match.

The cards speak the language of the machine, French among five (see [Language](#language)); the log stays in French.

```
FIN DU MATCH   LIGUE 1                                        90'+4'
Angers              1 - 2              Stade Rennais
Angers : M. Lopez 12'
Stade Rennais : A. Kalimuendo 58', L. Blas 77'
```

A side that hasn't scored gets no line, an own goal is marked `(csc)` and a
penalty `(sp)`. The card gains one line per scoring side, but never a pixel
more than its maximum width: a list that runs too long is cut off with an
ellipsis rather than allowed to overflow.

On Windows and macOS playback is built in (MCI, `afplay`). On Linux you need a
player: `mpv` or `ffmpeg` for the mp3; with only `aplay`/`paplay`, butbutbut
falls back on a **synthesised stadium horn** in wav, generated by the program
itself.

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
volume = 0.55
no_sound = non
no_overlay = non
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
```

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

The help, `--status`, `--scores`, `--screens`, `--list` and `--today` follow,
down to the values they print - `il y a 12 s` becomes `vor 12 s`, not just the
label in front of it.

**What stays in French**: the log, and **by choice**. `--today` reads it back,
and a file written before a language change would otherwise be half unreadable
to the parser. So a card can read `TOR!` while the log records `BUT`.

A phrase a catalogue does not carry falls back to French rather than
disappearing: an unfinished translation leaves the program usable.

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

### How a goal is detected

On every poll, each match's score is compared with the one from the previous
poll. **A score that goes up is a goal.** ESPN's list of events only serves to
dress the card (scorer, minute, own goal, penalty): it sometimes arrives a few
seconds after the score, and the goal must not wait for the scorer's name.

That is exactly why the other sports cost the detection nothing: a score going
up is a score going up, whether it gains 1 in football and hockey or 5 in
rugby. Hockey, which publishes no events at all, is therefore followed just as
well as the rest - it simply has cards with no scorer's name.

Two safeguards:

- **the first poll fires nothing.** It photographs what is already there.
  Otherwise, starting the daemon on a Sunday at 5 pm would replay every goal
  already scored;
- **a score that goes down** (a goal ruled out by VAR) shows an orange
  `BUT ANNULE` card - goal disallowed - with no sound.

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
- **an audio player**, on Linux only (`mpv`, `ffmpeg`, `sox`, `vlc`, or
  pipewire/pulse/alsa for the wav fallback)
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

**1034 tests**, with no network and no screen: the source is simulated by an
`opener`, the crest cache by a `fetcher`, the clock by a `FakeClock`, and the
geometry of the cards (stacking, overflow, truncation, the room left for
crests) is checked with a dummy font, hence without tkinter. Colour selection,
for its part, is a pure function: its invariant is tested over every pair from
a set of real colours - what comes out is always readable, or it is the
competition's colour. Recording, for its part, is checked by a full round trip:
a match played live against a simulated source, boxed up, then replayed - and
the two must produce exactly the same sequence of events.

One single program in the repository really talks to ESPN, and it is not in
this suite: [the canary](#the-canary), `python tools/canari.py`.

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
