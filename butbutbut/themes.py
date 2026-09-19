"""Themes territoriaux des clubs, avec le pays du stade comme repli.

Une carte de but appartient d'abord au club qui marque : son identifiant ESPN
designe une illustration locale embarquee. Les cartes sans camp explicite
prennent le recevant et les souvenirs le vainqueur. Cette regle reste nette
quand les deux equipes viennent de pays differents.

Un club encore inconnu retombe sur le pays du stade, puis sur celui du
championnat ou le globe international. Tous les motifs gardent la meme encre,
le meme grain et le meme cadrage : changer de territoire change le sujet, pas
la direction artistique.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path


# ImageGen ajoute un bloc de provenance ``caBX`` a son PNG original. Les
# navigateurs l'ignorent, mais Tk 8.6 le prenait pour une autre image et
# annoncait 355 x 355 au lieu de 1402 x 1122. Cette copie est le meme dessin,
# simplement reencode en PNG RGBA standard pour rester lisible partout.
ATLAS = Path(__file__).resolve().parent / "assets" / "country-postcards-v2.png"
CLUBS = ATLAS.parent / "clubs"


# Position dans l'atlas 5 x 4, lu de gauche a droite puis de haut en bas.
MOTIFS = {
    "france": 0,
    "england": 1,
    "spain": 2,
    "italy": 3,
    "germany": 4,
    "portugal": 5,
    "netherlands": 6,
    "belgium": 7,
    "turkey": 8,
    "united-states": 9,
    "mexico": 10,
    "argentina": 11,
    "brazil": 12,
    "saudi-arabia": 13,
    "japan": 14,
    "scotland": 15,
    "canada": 16,
    "international": 17,
    "stadium": 18,
    "celebration": 19,
}


# Les noms de pays suivent la langue demandee a ESPN. On les ramene d'abord a
# l'ASCII ; cette table couvre les cinq langues de butbutbut et les deux formes
# anglaises les plus frequentes de l'API.
_ALIASES = {
    "france": "france", "francia": "france", "franca": "france",
    "england": "england", "angleterre": "england",
    "inglaterra": "england", "inghilterra": "england",
    "spain": "spain", "espagne": "spain", "espana": "spain",
    "spanien": "spain", "spagna": "spain", "espanha": "spain",
    "italy": "italy", "italie": "italy", "italia": "italy",
    "italien": "italy",
    "germany": "germany", "allemagne": "germany",
    "alemania": "germany", "deutschland": "germany",
    "germania": "germany",
    "portugal": "portugal", "portogallo": "portugal",
    "netherlands": "netherlands", "the netherlands": "netherlands",
    "pays bas": "netherlands", "paises bajos": "netherlands",
    "paises baixos": "netherlands", "niederlande": "netherlands",
    "paesi bassi": "netherlands", "holland": "netherlands",
    "belgium": "belgium", "belgique": "belgium", "belgica": "belgium",
    "belgien": "belgium", "belgio": "belgium",
    "turkey": "turkey", "turkiye": "turkey", "turquie": "turkey",
    "turquia": "turkey", "turkei": "turkey", "turchia": "turkey",
    "united states": "united-states", "united states of america": "united-states",
    "usa": "united-states", "us": "united-states",
    "etats unis": "united-states", "estados unidos": "united-states",
    "vereinigte staaten": "united-states", "stati uniti": "united-states",
    "mexico": "mexico", "mexique": "mexico", "messico": "mexico",
    "argentina": "argentina", "argentine": "argentina",
    "argentinien": "argentina",
    "brazil": "brazil", "bresil": "brazil", "brasil": "brazil",
    "brasilien": "brazil", "brasile": "brazil",
    "saudi arabia": "saudi-arabia", "arabie saoudite": "saudi-arabia",
    "arabia saudita": "saudi-arabia", "saudi arabien": "saudi-arabia",
    "japan": "japan", "japon": "japan", "giappone": "japan",
    "japao": "japan",
    "scotland": "scotland", "ecosse": "scotland", "escocia": "scotland",
    "schottland": "scotland", "scozia": "scotland",
    "canada": "canada",
}


# Repli des competitions nationales quand l'adresse du stade manque.
_LEAGUE_COUNTRY = {
    "fra": "france", "eng": "england", "esp": "spain", "ita": "italy",
    "ger": "germany", "por": "portugal", "ned": "netherlands",
    "bel": "belgium", "tur": "turkey", "usa": "united-states",
    "mex": "mexico", "arg": "argentina", "bra": "brazil",
    "ksa": "saudi-arabia", "jpn": "japan", "sco": "scotland",
}

_INTERNATIONAL = ("uefa.", "fifa.", "conmebol.", "concacaf.")


def _plain(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def country_motif(country: str) -> str:
    """Cle du motif connu pour un nom de pays localise, ou chaine vide."""
    return _ALIASES.get(_plain(country), "")


def match_motif(match) -> str:
    """Motif honnete d'un match : stade, championnat, puis voyage neutre."""
    venue_country = getattr(match, "venue_country", "")
    found = country_motif(venue_country)
    if found:
        return found

    slug = str(getattr(getattr(match, "league", None), "slug", "") or "").lower()
    # Un pays est bien annonce mais n'a pas encore son dessin : le stade
    # generique est plus honnete que le pays de la competition (un match de
    # championnat peut etre delocalise a l'etranger).
    if str(venue_country or "").strip():
        return "stadium"
    prefix = slug.partition(".")[0].lower()
    if not slug.startswith(_INTERNATIONAL) and prefix in _LEAGUE_COUNTRY:
        return _LEAGUE_COUNTRY[prefix]
    return "international" if slug.startswith(_INTERNATIONAL) else "stadium"


def league_motif(league) -> str:
    """Motif d'une carte de demonstration, qui n'a pas encore de stade."""
    slug = str(getattr(league, "slug", "") or "").lower()
    prefix = slug.partition(".")[0].lower()
    if not slug.startswith(_INTERNATIONAL) and prefix in _LEAGUE_COUNTRY:
        return _LEAGUE_COUNTRY[prefix]
    return "international" if slug.startswith(_INTERNATIONAL) else "stadium"


def atlas_box(motif: str, width: int, height: int) -> tuple:
    """Rectangle entier d'un motif dans l'atlas, sans pixels perdus aux bords."""
    index = MOTIFS.get(motif, MOTIFS["stadium"])
    column, row = index % 5, index // 5
    return (round(column * width / 5), round(row * height / 4),
            round((column + 1) * width / 5), round((row + 1) * height / 4))


def css_position(motif: str) -> tuple:
    """Position CSS (%) du meme motif quand l'atlas sert de background."""
    index = MOTIFS.get(motif, MOTIFS["stadium"])
    column, row = index % 5, index // 5
    # background-position mesure l'espace restant, pas la largeur de l'image :
    # cinq colonnes donnent donc 0, 25, 50, 75, 100 %.
    return (column * 25, row * (100 / 3.0))


def club_asset(team_id: str):
    """PNG territorial d'un club, ou None tant que l'asset n'existe pas.

    L'identifiant ESPN est plus stable que le nom : une traduction, un accent
    ou un changement de sponsor ne doit pas decrocher l'image du club.
    """
    team_id = str(team_id or "").strip()
    if not team_id or not team_id.isdigit():
        return None
    path = CLUBS / (team_id + ".png")
    return path if path.is_file() else None
