"""La surveillance : comparer deux photos du tableau de bord, en tirer les buts.

Principe : a chaque passage on relit le tableau de bord d'un championnat et on
compare les scores a ceux du passage precedent. Un score qui monte = un but.
La liste des actions d'ESPN sert ensuite a habiller la notification (buteur,
minute, csc, penalty) ; elle arrive parfois avec quelques secondes de retard,
c'est pour ca qu'elle ne sert jamais a *detecter* le but, seulement a le
decrire.

Trois garde-fous :
  - le premier passage sur un championnat ne declenche rien : il photographie
    l'existant, sinon lancer le daemon en pleine journee de championnat ferait
    hurler tous les buts deja marques ;
  - un score qui *descend* (but refuse par la VAR) est signale sans son ;
  - un trou dans le temps (veille, hibernation, processus gele) remet tous les
    championnats a l'etat "jamais photographie" : au reveil la source a des
    heures d'avance sur nous, la comparer a notre derniere photo n'a plus de
    sens.

Autour du but viennent des evenements plus discrets, tous muets : les temps
forts du match (coup d'envoi, mi-temps, reprise, fin), les expulsions et
l'annonce d'un coup d'envoi imminent. Les deux derniers sont a la demande.

La cadence s'adapte : rapide quand un match est en cours, lente quand il n'y a
rien a regarder. Chaque championnat a son propre rythme, donc on n'interroge
pas la Bundesliga toutes les 25 s un mardi soir de Ligue 1.

Tout ceci vaut pour les trois sports ouverts (voir sports.py), sans une ligne
de plus : la detection ne regarde que le score, et un score qui monte est un
score qui monte, qu'il gagne 1 au football et au hockey ou 5 au rugby. Ce qui
change d'un sport a l'autre, ce sont les mots - le titre de la carte et le
texte du buteur -, et ils sont demandes au sport, jamais decides ici. Un sport
qui ne publie aucune action (le hockey) ou qui n'a pas de mi-temps (le hockey
encore) se contente donc de moins de cartes ; rien ne s'y desactive a la main.
"""

from __future__ import annotations

import time

from . import espn, i18n, sports

DEFAULT_INTERVAL = 25.0        # un match est en cours
DEFAULT_IDLE_INTERVAL = 300.0  # rien en cours dans ce championnat
KICKOFF_INTERVAL = 60.0        # coup d'envoi imminent
KICKOFF_WINDOW = 1200.0        # "imminent" = dans moins de 20 min
MAX_BACKOFF = 300.0            # plafond d'attente apres une erreur reseau
SPREAD = 1.5                   # decalage entre deux competitions, en secondes
FORGET_AFTER = 12 * 3600.0     # on oublie un match vu il y a plus de 12 h
GAP_GRACE = 120.0              # retard tolere avant de crier a la suspension

GOAL = "goal"
CANCELLED = "cancelled"
KICKOFF = "kickoff"
HALFTIME = "halftime"
RESTART = "restart"
FULLTIME = "fulltime"
RED_CARD = "red_card"
PREMATCH = "prematch"

# Les cartes de deroulement du match : meme carte, mais jamais de son.
PHASES = (KICKOFF, HALFTIME, RESTART, FULLTIME)

# Les cartes au ton discret : titre gris, aucune equipe mise en avant, et
# surtout aucun son. Seul un but fait du bruit, c'est ce qui le distingue.
# L'expulsion et l'avant-match rejoignent les phases sur ce point, mais pas
# sur --no-phase-cards : chacune a son propre interrupteur, et couper les
# temps forts ne doit pas couper ce qu'on a explicitement demande.
SOBER = PHASES + (RED_CARD, PREMATCH)

# Une cle de traduction par sorte d'evenement : la formulation vit dans
# i18n.py, pas ici.
TITLE_KEYS = {
    GOAL: "title_goal",
    CANCELLED: "title_cancelled",
    KICKOFF: "title_kickoff",
    HALFTIME: "title_halftime",
    RESTART: "title_restart",
    FULLTIME: "title_fulltime",
    RED_CARD: "title_red_card",
    PREMATCH: "title_prematch",
}


def title_of(kind, play=None, lang=None, sport=None) -> str:
    """Le titre d'une carte, dans la langue demandee (courante par defaut).

    Deux niveaux, et dans cet ordre :

      - l'action, quand elle sait se nommer. Un csc, un penalty, un essai, une
        transformation ne s'annoncent pas comme un but ordinaire, et ce n'est
        pas le sport qui le dit, c'est l'action elle-meme ;
      - le sport, sinon. Un score qui monte sans action pour l'expliquer se dit
        "BUT !" au football et au hockey, "POINTS !" au rugby ; et une pause se
        dit "MI-TEMPS" ici, "FIN DU TIERS-TEMPS" la.

    Un sport qui n'a rien de particulier a dire retombe sur le vocabulaire du
    football : c'est le socle, et c'est pour ca que rien n'a bouge pour lui.
    """
    sport = sport or sports.DEFAULT
    if kind == GOAL and play is not None and play.title_key:
        return i18n.text(play.title_key, lang=lang)
    key = TITLE_KEYS.get(kind)
    return i18n.text(sport.title_key(key), lang=lang) if key else kind.upper()

# Ce qui declenche une carte de phase : (phase precedente, phase actuelle).
# Un match jamais vu en cours ne declenche pas de "fin du match" : on n'a rien
# suivi, autant se taire.
TRANSITIONS = {
    (espn.SCHEDULED, espn.PLAYING): KICKOFF,
    (espn.UNKNOWN, espn.PLAYING): KICKOFF,      # match retarde qui part enfin
    (espn.PLAYING, espn.HALFTIME): HALFTIME,
    (espn.HALFTIME, espn.PLAYING): RESTART,
    (espn.PLAYING, espn.FINAL): FULLTIME,
    (espn.HALFTIME, espn.FINAL): FULLTIME,
}


def _scorer_text(play, lang=None) -> str:
    """Un buteur en quelques signes : Kalimuendo 58', Lefort (csc) 17'.

    Volontairement plus court que Play.summary() : la carte de fin de match en
    aligne plusieurs sur une ligne, "But de " repete trois fois mangerait la
    place des noms. La mention entre parentheses vient de l'action - "csc" et
    "sp" au football, "essai" et "transf." au rugby, rien pour un but simple.
    """
    who = play.scorer or play.prefix(lang=lang)
    mark = play.short_mark(lang=lang)
    if mark:
        who += " (" + mark + ")"
    return (who + " " + play.minute) if play.minute else who


def _countdown(seconds: float, lang=None) -> str:
    """Le compte a rebours d'avant match, arrondi a la minute superieure."""
    minutes = int(seconds // 60) + 1
    if minutes <= 1:
        return i18n.text("kickoff_soon", lang=lang)
    return i18n.text("kickoff_in", lang=lang, minutes=minutes)


class Event:
    """Ce qui vient de se passer : un but, une expulsion, un temps fort."""

    __slots__ = ("kind", "match", "side", "team", "opponent", "home_score",
                 "away_score", "delta", "play", "at", "countdown")

    def __init__(self, kind, match, side, team, opponent, home_score,
                 away_score, delta, play, at=None, countdown=None):
        self.kind = kind
        self.match = match
        self.side = side              # "home" ou "away"
        self.team = team              # equipe concernee
        self.opponent = opponent
        self.home_score = home_score
        self.away_score = away_score
        self.delta = delta            # +1, +2 (doublon rattrape), -1...
        self.play = play              # espn.Play ou None
        self.at = at or time.time()
        # Le compte a rebours est fige en SECONDES au moment de l'evenement,
        # pas en texte : recalcule a l'affichage il vieillirait, mais fige en
        # francais il ne pourrait plus etre rendu dans une autre langue - la
        # carte et le journal n'en veulent pas la meme.
        self.countdown = countdown

    @property
    def league(self):
        return self.match.league

    @property
    def sport(self):
        return self.match.sport

    @property
    def goal(self) -> bool:
        return self.kind == GOAL

    @property
    def phase(self) -> bool:
        """Vrai pour une carte de deroulement (coup d'envoi, mi-temps...)."""
        return self.kind in PHASES

    @property
    def sober(self) -> bool:
        """Vrai pour une carte discrete : titre gris, et jamais de son."""
        return self.kind in SOBER

    @property
    def title(self) -> str:
        return title_of(self.kind, self.play, sport=self.sport)

    @property
    def minute(self) -> str:
        """La minute du but, sinon l'horloge du match."""
        if self.kind == PREMATCH:
            # Rien n'a commence : l'horloge d'un match a venir ne dit rien, et
            # la date complete que la source y met deborde de l'en-tete.
            return ""
        if self.play is not None and self.play.minute:
            return self.play.minute
        return self.match.clock or self.match.detail or ""

    @property
    def score_line(self) -> str:
        return "{} {} - {} {}".format(self.match.home, self.home_score,
                                      self.away_score, self.match.away)

    @property
    def colors(self) -> tuple:
        """(couleur, couleur secondaire) du club concerne, ou ("", "").

        Une carte de deroulement ne designe aucune equipe : elle n'a donc pas
        de couleur de club a prendre.
        """
        if self.side == "home":
            return (self.match.home_color, self.match.home_alt)
        if self.side == "away":
            return (self.match.away_color, self.match.away_alt)
        return ("", "")

    def detail_parts(self, lang=None) -> list:
        """La troisieme ligne, en morceaux : (texte, mis_en_valeur).

        Le nom du buteur est le seul morceau mis en valeur : c'est l'info qu'on
        veut lire en premier apres le score.
        """
        if self.kind == CANCELLED:
            return [(i18n.text("cancelled", lang=lang), False)]
        if self.kind == PREMATCH:
            if self.countdown is None:
                return []
            return [(_countdown(self.countdown, lang=lang), False)]
        if self.kind == RED_CARD:
            # L'equipe se lit ici plutot que dans la couleur du score : voir
            # une equipe passer en couleur, sur cette carte, ressemblerait a
            # une bonne nouvelle.
            if self.play is not None and self.play.scorer:
                return [(self.team + " : ", False), (self.play.scorer, True)]
            return [(self.team, False)] if self.team else []
        if self.phase:
            # Le titre dit tout : pas de troisieme ligne, la carte est plus
            # basse et se distingue d'un but au premier coup d'oeil.
            return []

        play = self.play
        if play is None:
            # Rien pour habiller le score. Au rugby, le seul fait qu'il ait
            # bouge de 5 dit deja qu'un essai vient d'etre marque : le delta
            # est une information, la ou au football il n'en serait pas une
            # (un but vaut un but). Le hockey, lui, n'a jamais d'action a
            # afficher - la source n'en publie pas - et retombe sur la minute.
            if not self.sport.unit_score and self.delta > 0:
                return [(i18n.text("points_added", lang=lang,
                                   points=self.delta), False)]
            minute = self.minute
            if not minute:
                return []
            return [(i18n.text("minute", lang=lang, minute=minute), False)]

        # La minute n'est pas repetee ici : l'en-tete de la carte la porte deja.
        if play.scorer:
            return [(play.prefix_for(lang=lang), False), (play.scorer, True)]
        return [(play.prefix(lang=lang), False)]

    def detail_line(self, lang=None) -> str:
        """La meme ligne, d'un bloc : journal, tests, mode --no-overlay."""
        return "".join(t for t, _ in self.detail_parts(lang=lang))

    def extra_parts(self, lang=None) -> list:
        """Les lignes supplementaires de la carte, en morceaux.

        Seule la fin du match en a : le score seul ne dit pas qui a marque,
        alors que c'est la premiere chose qu'on cherche quand on n'a pas vu le
        match. Un camp sans but n'a pas de ligne du tout.
        """
        if self.kind != FULLTIME:
            return []

        match = self.match
        lines = []
        for team, team_id in ((match.home, match.home_id),
                              (match.away, match.away_id)):
            scorers = [_scorer_text(play, lang=lang)
                       for play in match.plays_for(team_id)]
            if scorers:
                lines.append([(team + " : ", False), (", ".join(scorers), True)])
        return lines

    def extra_lines(self, lang=None) -> list:
        """Les memes lignes, chacune d'un bloc : journal et tests."""
        return ["".join(t for t, _ in line) for line in self.extra_parts(lang=lang)]

    def log_line(self) -> str:
        """La ligne du journal, toujours en francais.

        Deux raisons de ne pas la traduire : elle voisine la ligne de commande,
        qui parle francais, et `--today` la relit. Un fichier ecrit avant un
        changement de langue resterait sinon a moitie illisible pour le
        relecteur.
        """
        head = title_of(self.kind, self.play, lang=i18n.FALLBACK,
                        sport=self.sport).rstrip(" !")
        parts = ["{} [{}] {}".format(head, self.league.name, self.score_line)]
        if self.team:
            parts.append("pour " + self.team)
        detail = self.detail_line(lang=i18n.FALLBACK)
        if detail:
            parts.append("- " + detail)
        extra = self.extra_lines(lang=i18n.FALLBACK)
        if extra:
            parts.append("- " + " ; ".join(extra))
        if self.minute:
            parts.append("(" + self.minute + ")")
        return " ".join(parts)

    def __repr__(self):
        return "<Event {} {}>".format(self.kind, self.score_line)


class _Snapshot:
    """Ce qu'on retient d'un match entre deux passages."""

    __slots__ = ("home_score", "away_score", "phase", "seen_plays",
                 "seen_cards", "announced", "last_seen")

    def __init__(self, home_score, away_score, phase, seen_plays, last_seen,
                 seen_cards=None):
        self.home_score = home_score
        self.away_score = away_score
        self.phase = phase
        self.seen_plays = seen_plays
        self.seen_cards = seen_cards or set()
        # L'avant-match n'est annonce qu'une fois : la fenetre reste ouverte
        # pendant plusieurs releves, sans ce drapeau la carte reviendrait
        # toutes les minutes jusqu'au coup d'envoi.
        self.announced = False
        self.last_seen = last_seen


class Watcher:
    """Interroge les championnats a leur rythme et renvoie les buts."""

    def __init__(self, leagues, interval=DEFAULT_INTERVAL,
                 idle_interval=DEFAULT_IDLE_INTERVAL,
                 kickoff_window=KICKOFF_WINDOW, timeout=espn.DEFAULT_TIMEOUT,
                 opener=None, on_log=None, teams=None, clock=None,
                 red_cards=False, before_kickoff=0.0):
        self.leagues = list(leagues)
        # Filtre par equipe (teams.Filter) ou None : on continue de suivre tous
        # les matchs, mais on ne signale que ceux qui concernent ces clubs.
        self.teams = teams
        # Les deux options a la demande : une expulsion et une annonce d'avant
        # match n'interessent pas tout le monde, elles ne s'invitent pas.
        self.red_cards = bool(red_cards)
        self.before_kickoff = max(0.0, float(before_kickoff))   # en secondes
        self.interval = max(5.0, float(interval))
        self.idle_interval = max(self.interval, float(idle_interval))
        self.kickoff_window = float(kickoff_window)
        self.timeout = float(timeout)
        self.opener = opener
        self.on_log = on_log or (lambda message: None)
        # L'horloge murale, surchargeable : elle sert a reperer les trous, et
        # les tests ne peuvent pas endormir la machine pour de vrai.
        self.clock = clock or time.time

        # Les competitions sont indexees par leur `ref` et non par leur `slug` :
        # deux sports pourraient un jour partager un code ESPN, et leurs matchs
        # se melangeraient dans ces trois dictionnaires. Au football, `ref` vaut
        # le `slug` - rien n'a bouge de ce cote.
        self.matches = {}          # ref -> list[Match] du dernier passage
        self._snapshots = {}       # match_id -> _Snapshot
        self._due = {league.ref: 0.0 for league in self.leagues}
        self._failures = {league.ref: 0 for league in self.leagues}
        self._primed = set()       # championnats deja photographies une fois
        self._planned = 0.0        # attente annoncee a la boucle de surveillance
        self._planned_at = None    # ... et l'heure a laquelle on l'a annoncee

    # ------------------------------------------------------------ cadence ---

    def due_leagues(self, now=None) -> list:
        now = now if now is not None else time.monotonic()
        return [l for l in self.leagues if self._due.get(l.ref, 0.0) <= now]

    def next_delay(self, now=None) -> float:
        """Secondes a attendre avant le prochain passage, bornees."""
        now = now if now is not None else time.monotonic()
        if not self.leagues:
            return self.idle_interval
        soonest = min(self._due.get(l.ref, 0.0) for l in self.leagues)
        return max(1.0, min(60.0, soonest - now))

    def plan_wait(self, now=None) -> float:
        """Le meme delai, mais note : c'est ce qu'on s'engage a attendre.

        La boucle de surveillance appelle ceci plutot que next_delay() juste
        avant de dormir. Le prochain tick() confrontera cette promesse au
        temps reellement ecoule ; l'ecart, c'est le trou.
        """
        delay = self.next_delay(now=now)
        self._planned = delay
        self._planned_at = self.clock()
        return delay

    def _gap(self) -> float:
        """Le temps d'horloge perdu depuis la derniere promesse, 0.0 sinon.

        On mesure avec l'horloge murale et non time.monotonic() : sous Linux
        monotonic est gelee pendant la veille, elle ne verrait donc aucun
        trou, alors que sous Windows elle continue d'avancer. Un reglage NTP
        peut la faire sauter, mais le prix d'un faux positif se limite a une
        re-photographie muette.
        """
        if self._planned_at is None:
            return 0.0
        elapsed = self.clock() - self._planned_at
        # GAP_GRACE laisse largement passer une machine chargee ou un releve
        # traine par le timeout HTTP : un vrai reveil de veille se compte en
        # minutes, jamais en secondes.
        if elapsed <= self._planned + GAP_GRACE:
            return 0.0
        return elapsed

    def _cadence(self, matches) -> float:
        """Rythme de ce championnat, d'apres ce qu'il a au programme."""
        if any(match.live for match in matches):
            return self.interval

        soonest = None
        for match in matches:
            remaining = match.seconds_until_kickoff()
            if remaining is None or remaining < -7200:
                continue
            if soonest is None or remaining < soonest:
                soonest = remaining

        # Une annonce d'avant match reglee sur une heure n'aurait aucun sens si
        # on ne relevait le championnat que toutes les cinq minutes.
        window = max(self.kickoff_window, self.before_kickoff)
        if soonest is not None and soonest <= window:
            return min(KICKOFF_INTERVAL, self.idle_interval)
        return self.idle_interval

    def live_matches(self) -> list:
        found = []
        for league in self.leagues:
            found.extend(m for m in self.matches.get(league.ref, []) if m.live)
        return found

    def all_matches(self) -> list:
        found = []
        for league in self.leagues:
            found.extend(self.matches.get(league.ref, []))
        return found

    # -------------------------------------------------------------- lecture -

    def refresh(self, league, now=None) -> list:
        """Relit un championnat et renvoie les evenements qui en decoulent."""
        now = now if now is not None else time.monotonic()
        try:
            matches = espn.scoreboard(league, timeout=self.timeout, opener=self.opener)
        except espn.SourceError as exc:
            self._failures[league.ref] = self._failures.get(league.ref, 0) + 1
            failures = self._failures[league.ref]
            wait = min(MAX_BACKOFF, self.interval * (2 ** min(failures, 4)))
            self._due[league.ref] = now + wait
            if failures in (1, 5) or failures % 20 == 0:
                self.on_log("{} injoignable ({}) - nouvel essai dans {:.0f}s"
                            .format(league.name, exc, wait))
            return []

        if self._failures.get(league.ref):
            self.on_log(league.name + " de nouveau joignable")
        self._failures[league.ref] = 0

        self.matches[league.ref] = matches
        self._due[league.ref] = now + self._cadence(matches)

        primed = league.ref in self._primed
        self._primed.add(league.ref)

        events = []
        for match in matches:
            events.extend(self._diff(match, alert=primed))
        self._forget_old()
        return events

    def tick(self, now=None) -> list:
        """Passe sur tous les championnats dont l'heure est venue."""
        now = now if now is not None else time.monotonic()
        self._check_gap()
        events = []
        for league in self.due_leagues(now):
            events.extend(self.refresh(league, now=now))
        return events

    def _check_gap(self) -> float:
        """Si on a saute dans le temps, tout redevient a photographier.

        Sans ca, un 0-0 releve avant la veille compare a un 3-1 lu au reveil
        sortirait une carte "BUT" de delta 3 avec une minute perimee, voire un
        "COUP D'ENVOI" pour un match deja fini. Le silence du premier releve
        est exactement le bon comportement : on le rejoue.
        """
        gap = self._gap()
        if not gap:
            return 0.0
        self.on_log("trou de {:.0f} min dans le temps (veille, hibernation ou "
                    "processus gele) - on rephotographie les scores sans rien "
                    "annoncer".format(gap / 60.0))
        self._primed.clear()
        self._planned_at = None
        return gap

    def prime(self, pause: float = 0.2) -> None:
        """Premier passage sur tout : photographie l'existant, sans alerte.

        Les appels sont espaces, et les prochains releves decales les uns des
        autres : avec tout le catalogue, trente-six requetes tirees en rafale
        finissent par se faire jeter par la source.
        """
        total = len(self.leagues)
        for index, league in enumerate(self.leagues):
            self.refresh(league)
            self._due[league.ref] += index * SPREAD
            if pause and index + 1 < total:
                time.sleep(pause)

    # --------------------------------------------------------------- diff ---

    def _diff(self, match, alert=True) -> list:
        """Compare un match a sa photo precedente."""
        stamp = time.time()
        previous = self._snapshots.get(match.id)
        keys = {play.key for play in match.plays}
        card_keys = {play.key for play in match.red_cards}

        if previous is None:
            # Premier coup d'oeil sur ce match : on photographie, on se tait.
            self._snapshots[match.id] = _Snapshot(
                match.home_score, match.away_score, match.phase, keys, stamp,
                seen_cards=card_keys)
            return []

        events = []
        pairs = (
            ("home", match.home_id, match.home, match.away,
             previous.home_score, match.home_score),
            ("away", match.away_id, match.away, match.home,
             previous.away_score, match.away_score),
        )

        for side, team_id, team, opponent, before, after in pairs:
            if after == before:
                continue
            delta = after - before
            play = self._pick_play(match, team_id, previous.seen_plays) if delta > 0 else None
            events.append(Event(
                kind=GOAL if delta > 0 else CANCELLED,
                match=match,
                side=side,
                team=team,
                opponent=opponent,
                home_score=match.home_score,
                away_score=match.away_score,
                delta=delta,
                play=play,
            ))

        # Une expulsion se detecte comme un but : une action qu'on n'avait pas
        # encore vue. La cle est stable, donc elle ne ressort jamais deux fois.
        if self.red_cards:
            sides = {"home": (match.home, match.away),
                     "away": (match.away, match.home)}
            for play in match.red_cards:
                if play.key in previous.seen_cards:
                    continue
                side = match.side_of(play.team_id)
                team, opponent = sides.get(side, ("", ""))
                events.append(Event(
                    kind=RED_CARD,
                    match=match,
                    side=side or None,
                    team=team,
                    opponent=opponent,
                    home_score=match.home_score,
                    away_score=match.away_score,
                    delta=0,
                    play=play,
                ))

        # Deroulement du match : coup d'envoi, mi-temps, reprise, fin.
        kind = TRANSITIONS.get((previous.phase, match.phase))
        if kind is not None:
            events.append(Event(
                kind=kind,
                match=match,
                side=None,
                team="",
                opponent="",
                home_score=match.home_score,
                away_score=match.away_score,
                delta=0,
                play=None,
            ))

        # Le match va commencer : une seule fois, meme si la fenetre reste
        # ouverte pendant plusieurs releves.
        remaining = self._prematch_countdown(match, previous)
        if remaining is not None:
            previous.announced = True
            events.append(Event(
                kind=PREMATCH,
                match=match,
                side=None,
                team="",
                opponent="",
                home_score=match.home_score,
                away_score=match.away_score,
                delta=0,
                play=None,
                countdown=remaining,
            ))

        # La photo est mise a jour avant tout filtrage : un evenement tu par le
        # filtre par equipe, ou par le premier releve, reste un evenement vu.
        previous.home_score = match.home_score
        previous.away_score = match.away_score
        previous.phase = match.phase
        previous.seen_plays = keys
        previous.seen_cards = card_keys
        previous.last_seen = stamp

        if not alert:
            return []
        if self.teams is not None and not self.teams.matches(match):
            return []
        return events

    def _prematch_countdown(self, match, previous):
        """Secondes restantes s'il faut annoncer ce match, sinon None."""
        if not self.before_kickoff or previous.announced:
            return None
        if match.phase != espn.SCHEDULED:
            return None
        remaining = match.seconds_until_kickoff()
        # Une heure de coup d'envoi deja passee alors que le match n'a pas
        # demarre, c'est un retard : annoncer "ca va commencer" serait faux.
        if remaining is None or remaining <= 0 or remaining > self.before_kickoff:
            return None
        return remaining

    @staticmethod
    def _pick_play(match, team_id, seen_keys):
        """L'action qui explique le mieux le score, parmi celles qu'on n'a pas vues.

        Au football, toutes les actions valent 1 : c'est donc la derniere, et
        rien n'a change. Au rugby, un essai et sa transformation peuvent tomber
        dans le meme releve - le score passe de 14 a 21 d'un coup. Annoncer
        "TRANSFORMATION" parce que c'est la derniere de la liste serait annoncer
        le detail et taire l'evenement : on garde la plus chere, et la plus
        recente a valeur egale (d'ou le parcours a l'envers).
        """
        fresh = [p for p in match.plays_for(team_id) if p.key not in seen_keys]
        if fresh:
            return max(reversed(fresh), key=lambda play: play.points)
        known = match.plays_for(team_id)
        return known[-1] if known else None

    def _forget_old(self) -> None:
        limit = time.time() - FORGET_AFTER
        stale = [key for key, snap in self._snapshots.items() if snap.last_seen < limit]
        for key in stale:
            del self._snapshots[key]
