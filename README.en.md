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
butbutbut --list              # the competitions you can watch
butbutbut --list-teams        # the teams in the competitions you follow
butbutbut --status            # daemon, last poll, matches in play, sound, screens
butbutbut --today             # the goals reported today
butbutbut --stop              # stop the daemon
butbutbut --check-update      # is there a newer version?
butbutbut --update            # fetch, reinstall, restart the daemon
butbutbut --update --dev      # same, but the tip of the main branch
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
as it does to the key-moment cards, and to `--scores` as well.

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
visible cards, the oldest one gives up its place.

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
quiet = non
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
timeout, pass without a murmur), it concludes that it has jumped through time:
it **re-photographs every score in silence**, exactly as on the first poll,
and notes it in the log:

```
2026-09-06 21:14:07  trou de 47 min dans le temps (veille, hibernation ou processus gele) - on rephotographie les scores sans rien annoncer
```

Watching then resumes as normal, and the next goal is announced as usual. The
goals that went in during the sleep, however, are lost: that is the price of
not talking nonsense.

The measurement is taken on the wall clock and not on `time.monotonic()`: on
Linux, monotonic is frozen during sleep and would therefore see no gap at all,
whereas on Windows it carries on ticking.

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

**573 tests**, with no network and no screen: the source is simulated by an
`opener`, the crest cache by a `fetcher`, the clock by a `FakeClock`, and the
geometry of the cards (stacking, overflow, truncation, the room left for
crests) is checked with a dummy font, hence without tkinter. Colour selection,
for its part, is a pure function: its invariant is tested over every pair from
a set of real colours - what comes out is always readable, or it is the
competition's colour.

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
