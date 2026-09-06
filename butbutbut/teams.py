"""Filtrer par equipe : ne se faire alerter que pour les clubs qu'on suit.

    butbutbut --teams om,psg
    butbutbut --teams "real madrid,barcelona" --leagues liga,ucl
    butbutbut --exclude-teams psg

Un match est retenu des que **l'une des deux equipes** correspond : si tu suis
l'OM, tu veux aussi savoir quand l'OM encaisse.

La reconnaissance des noms doit encaisser ce que les gens tapent vraiment :

  - les accents          : "malaga" trouve "Malaga", "atletico" trouve
                           "Atletico Madrid" ;
  - les abreviations      : ESPN en fournit une par club (PSG, RMA, MAN...) ;
  - les surnoms francais  : "om", "ol", "asse", "losc"... qu'ESPN ne connait
                           pas, d'ou la petite table ci-dessous ;
  - les noms partiels     : "marseille" trouve "Marseille", "manchester"
                           trouve les deux Manchester (c'est voulu, et
                           `--list-teams` montre ce qu'un mot attrape).
"""

from __future__ import annotations

import re
import unicodedata

# Surnoms courants qu'ESPN n'expose pas. La valeur est ce qu'on cherche
# ensuite dans les noms officiels, donc "om" revient a taper "marseille".
ALIASES = {
    # France
    "om": "marseille",
    "ol": "lyon",
    "asse": "saint etienne",
    "losc": "lille",
    "ogcn": "nice",
    "asm": "monaco",
    "srfc": "rennes",
    "mhsc": "montpellier",
    "fcn": "nantes",
    "tfc": "toulouse",
    "asnl": "nancy",
    # Angleterre
    "manu": "manchester united",
    "mufc": "manchester united",
    "mcfc": "manchester city",
    "lfc": "liverpool",
    "cfc": "chelsea",
    # Espagne, Italie, Allemagne
    "barca": "barcelona",
    "atleti": "atletico",
    "juve": "juventus",
    "bvb": "dortmund",
    "gladbach": "monchengladbach",
}

# En dessous, un mot n'est cherche qu'a l'identique : "bar" ne doit pas
# attraper "Barcelona" par hasard, alors que l'abreviation BAR, si.
PARTIAL_MIN = 4


def normalize(text) -> str:
    """Minuscules, sans accents, sans ponctuation ni espaces."""
    decomposed = unicodedata.normalize("NFKD", str(text or ""))
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return "".join(c for c in stripped.lower() if c.isalnum())


def expand(token: str) -> str:
    """Remplace un surnom par le nom a chercher."""
    return ALIASES.get(normalize(token), token)


def words(name) -> list:
    """Les mots d'un nom, normalises un par un."""
    parts = re.split(r"[\s./'`-]+", str(name or ""))
    return [normalize(part) for part in parts if normalize(part)]


def _hit(token: str, names) -> bool:
    """Vrai si `token` (deja normalise) designe l'une de ces ecritures.

    Le mot doit coller au nom entier ou au DEBUT d'un de ses mots. Sans cette
    contrainte de frontiere, "real" attrapait aussi "Villarreal", ou "real"
    n'est qu'un morceau de mot.
    """
    for name in names:
        if not name:
            continue
        flat = normalize(name)
        if token == flat:
            return True
        if len(token) >= PARTIAL_MIN and flat.startswith(token):
            return True
        for word in words(name):
            if token == word:
                return True
            if len(token) >= PARTIAL_MIN and word.startswith(token):
                return True
    return False


class Filter:
    """Les equipes suivies, et celles dont on ne veut rien savoir."""

    def __init__(self, wanted=None, excluded=None):
        self.wanted_tokens = _tokens(wanted)
        self.excluded_tokens = _tokens(excluded)
        self.wanted = [normalize(expand(t)) for t in self.wanted_tokens]
        self.excluded = [normalize(expand(t)) for t in self.excluded_tokens]
        # Vide de partout : pas de filtre du tout, tout passe.
        self.active = bool(self.wanted or self.excluded)

    def team_matches(self, names) -> bool:
        return any(_hit(token, names) for token in self.wanted)

    def team_excluded(self, names) -> bool:
        return any(_hit(token, names) for token in self.excluded)

    def matches(self, match) -> bool:
        """Ce match interesse-t-il ?

        Il suffit qu'une des deux equipes soit suivie ; il suffit qu'une des
        deux soit exclue pour que le match saute.
        """
        if not self.active:
            return True

        home = getattr(match, "home_names", (match.home,))
        away = getattr(match, "away_names", (match.away,))

        if self.excluded and (self.team_excluded(home) or self.team_excluded(away)):
            return False
        if not self.wanted:
            return True
        return self.team_matches(home) or self.team_matches(away)

    def resolve(self, catalogue) -> tuple:
        """Confronte les mots demandes a un catalogue d'equipes.

        `catalogue` : liste de tuples de noms (un tuple par equipe), telle que
        la rend espn.team_names. Renvoie ({mot: [noms trouves]}, [mots orphelins]).
        """
        found = {}
        orphans = []
        for raw, token in zip(self.wanted_tokens + self.excluded_tokens,
                              self.wanted + self.excluded):
            hits = [names[0] for names in catalogue if _hit(token, names)]
            if hits:
                found[raw] = sorted(set(hits))
            else:
                orphans.append(raw)
        return found, orphans

    def describe(self) -> str:
        parts = []
        if self.wanted_tokens:
            parts.append("equipes suivies : " + ", ".join(self.wanted_tokens))
        if self.excluded_tokens:
            parts.append("equipes exclues : " + ", ".join(self.excluded_tokens))
        return " | ".join(parts) if parts else "toutes les equipes"

    def __repr__(self):
        return "<Filter {}>".format(self.describe())


def _tokens(value) -> list:
    if value is None:
        return []
    if isinstance(value, str):
        value = value.replace(";", ",").split(",")
    return [str(token).strip() for token in value if str(token).strip()]
