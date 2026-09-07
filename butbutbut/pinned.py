"""La carte epinglee : un match reste a l'ecran tant qu'il se joue.

    butbutbut --pin om

Toutes les autres cartes sont fugaces : elles arrivent sur un evenement, elles
s'en vont quelques secondes plus tard. Celle-ci fait l'inverse - elle se pose au
coup d'envoi, se met a jour a chaque releve (le score et la minute), et s'en va
un moment apres le coup de sifflet final. C'est ce qui fait passer butbutbut de
l'alerte au tableau de bord : la carte vit sur le second ecran pendant qu'on
travaille, et le score du match qu'on suit est la sans rien avoir a ouvrir.

Ce module ne connait ni tkinter ni les cartes : il ne fait que decider **quel
match on suit, et jusqu'a quand**. L'affichage lit ce verdict (`Follow`) et en
fabrique une carte. C'est ce qui permet de tester tout le cycle de vie sans
ecran.

Les arbitrages, tous discutables mais tous tenus :

  - **une seule carte epinglee**, meme si le mot demande attrape plusieurs
    clubs (`--pin real` en attrape trois : Madrid, Sociedad, Betis). Deux matchs
    de la meme equipe en meme temps n'existent pas, mais deux matchs de deux
    Real, si. Plusieurs cartes epinglees repousseraient d'autant la pile des
    buts hors du coin, et un tableau de bord qui prend un quart d'ecran n'est
    plus un tableau de bord. On suit donc **le match commence en premier**, et
    on n'en change pas tant qu'il dure : une carte qui sauterait d'un match a
    l'autre au gre des releves serait illisible. Quand il finit, la carte passe
    au suivant s'il en reste un en cours ;
  - **elle apparait des qu'un match est en cours**, pas seulement au coup
    d'envoi : demarrer le daemon a la mi-temps doit donner la carte tout de
    suite, sinon il faudrait attendre le match suivant ;
  - **elle ne passe pas la nuit a l'ecran**. Le match fini, elle reste `LINGER`
    secondes - le temps de voir le score final en revenant de la cuisine - puis
    elle disparait. Sans ce delai, un daemon lance le samedi afficherait encore
    dimanche matin un match termine depuis douze heures ;
  - **un match qui disparait du tableau de bord** (changement de journee,
    reponse tronquee) est traite comme un match fini : on garde la derniere
    photo et on laisse courir le meme delai, plutot que de faire clignoter la
    carte au premier releve bancal ;
  - **elle ne fait jamais de bruit** : le son reste la marque du but. Rien ici
    ne joue quoi que ce soit, et la carte est fabriquee dans le ton discret des
    temps forts.

Le nommage de l'equipe passe par `teams.Filter`, comme `--teams` : `om`,
`barca`, `manu`, les noms sans accents et les debuts de mots marchent pareil, et
un mot qui ne designe rien est refuse au demarrage par la ligne de commande.
"""

from __future__ import annotations

import time

from . import teams

# Secondes pendant lesquelles la carte survit a la fin du match. Cinq minutes :
# assez pour lire le score final en revenant, trop peu pour tenir la nuit.
LINGER = 300.0


class Follow:
    """Le match suivi a cet instant, et l'etat dans lequel on le montre."""

    __slots__ = ("match", "ended")

    def __init__(self, match, ended=False):
        self.match = match
        # Le match est fini : la carte le dit et vit ses dernieres minutes.
        self.ended = bool(ended)

    def __repr__(self):
        return "<Follow {} {}>".format(
            "termine" if self.ended else "en cours", self.match.score_line())


class Pin:
    """Le match epingle : lequel, et jusqu'a quand.

    Un seul objet pour toute la vie du daemon : c'est lui qui retient le match
    en cours de suivi d'un releve a l'autre, et l'heure du coup de sifflet
    final.
    """

    __slots__ = ("token", "filter", "linger", "on_log", "match_id", "last",
                 "ended_at")

    def __init__(self, token, linger=LINGER, on_log=None):
        self.token = str(token or "").strip()
        # Un filtre a un seul mot : `matches()` regarde les deux equipes, donc
        # epingler l'OM marche que l'OM recoive ou se deplace.
        self.filter = teams.Filter(self.token) if self.token else None
        self.linger = max(0.0, float(linger))
        self.on_log = on_log
        self.match_id = None      # le match suivi, d'un releve a l'autre
        self.last = None          # sa derniere photo connue
        self.ended_at = None      # quand il s'est termine, pour le compte a rebours

    @property
    def active(self) -> bool:
        """Vrai si un mot a ete demande : sinon tout ce module ne fait rien."""
        return self.filter is not None and self.filter.active

    def update(self, matches, now=None):
        """Le verdict de ce releve : un `Follow`, ou None (pas de carte).

        Appelee a chaque releve, meme quand rien n'a bouge : c'est aussi ce qui
        fait expirer la carte d'un match fini.
        """
        if not self.active:
            return None
        now = time.monotonic() if now is None else float(now)

        candidates = [match for match in matches if self.filter.matches(match)]

        if self.match_id is not None:
            following = self._followed(candidates)
            verdict = self._still_showing(following, now)
            if verdict is not None:
                return verdict
            # Le delai de grace est ecoule : la place se libere, et un autre
            # match de la selection peut la prendre des ce releve.
            self._release()

        chosen = self._pick(candidates)
        if chosen is None:
            return None
        self.match_id = chosen.id
        self.last = chosen
        self.ended_at = None
        self._log("carte epinglee sur [{}] {}".format(
            chosen.league.name, chosen.score_line()))
        return Follow(chosen, ended=False)

    def describe(self) -> str:
        """Ce que `--status` et le journal disent de l'epinglage."""
        if not self.active:
            return "aucune carte epinglee"
        if self.last is None:
            return "carte epinglee sur {} (aucun match en cours)".format(self.token)
        return "carte epinglee sur {} : [{}] {}".format(
            self.token, self.last.league.name, self.last.score_line())

    # ------------------------------------------------------------ interne ----

    def _followed(self, candidates):
        """La photo du match suivi dans ce releve, ou None s'il n'y est plus."""
        for match in candidates:
            if match.id == self.match_id:
                return match
        return None

    def _still_showing(self, following, now):
        """Faut-il garder le match suivi ? Rend le `Follow`, ou None.

        Un match absent du releve est traite comme un match fini : on montre sa
        derniere photo pendant le meme delai de grace. Une reponse tronquee ou
        un changement de journee ne doit pas faire disparaitre la carte d'un
        match qui se joue peut-etre encore.
        """
        if following is not None:
            self.last = following
            if following.live:
                self.ended_at = None
                return Follow(following, ended=False)

        if self.ended_at is None:
            self.ended_at = now
        if now - self.ended_at > self.linger:
            return None
        return Follow(self.last, ended=True)

    def _pick(self, candidates):
        """Le match a epingler parmi ceux qui se jouent, ou None.

        Trie par heure de coup d'envoi puis par identifiant : deux releves
        successifs ne doivent jamais choisir differemment sur les memes
        donnees, sans quoi la carte changerait de match toute seule.
        """
        live = [match for match in candidates if match.live]
        if not live:
            return None
        return sorted(live, key=_order)[0]

    def _release(self) -> None:
        if self.last is not None:
            self._log("carte epinglee retiree ([{}] {})".format(
                self.last.league.name, self.last.score_line()))
        self.match_id = None
        self.last = None
        self.ended_at = None

    def _log(self, message: str) -> None:
        """Le journal, s'il y en a un, et jamais au prix du daemon."""
        if self.on_log is None:
            return
        try:
            self.on_log(message)
        except Exception:
            pass

    def __repr__(self):
        return "<Pin {!r} {}>".format(self.token, self.match_id or "-")


def _order(match):
    """Clef de tri : l'heure de coup d'envoi d'abord, l'identifiant ensuite.

    Un match sans date passe apres ceux qui en ont une : on ne sait pas quand
    il a commence, il ne peut donc pas revendiquer d'etre le premier.
    """
    start = match.start
    stamp = (0, start.timestamp()) if start is not None else (1, 0.0)
    return (stamp, str(match.id))
