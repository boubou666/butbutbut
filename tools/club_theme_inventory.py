"""Construit et controle le manifeste des illustrations territoriales.

La liste vient des endpoints ``/teams`` deja utilises par butbutbut. Elle est
donc reproductible a chaque changement de saison, au lieu d'enfouir 384 noms
dans le code. Les PNG, eux, restent indexes par l'identifiant ESPN stable.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from butbutbut import espn, leagues  # noqa: E402


MEN = (
    ("fra.1", "france"), ("eng.1", "england"),
    ("esp.1", "spain"), ("ita.1", "italy"),
    ("ger.1", "germany"), ("por.1", "portugal"),
    ("ned.1", "netherlands"), ("bel.1", "belgium"),
    ("tur.1", "turkey"), ("sco.1", "scotland"),
    ("usa.1", "united-states"), ("mex.1", "mexico"),
    ("bra.1", "brazil"), ("arg.1", "argentina"),
    ("ksa.1", "saudi-arabia"), ("jpn.1", "japan"),
)

WOMEN = (
    ("eng.w.1", "england"), ("esp.w.1", "spain"),
    ("fra.w.1", "france"), ("ned.w.1", "netherlands"),
    ("usa.nwsl", "united-states"),
)

MANIFEST = ROOT / "butbutbut" / "assets" / "club-themes.json"
ASSETS = ROOT / "butbutbut" / "assets" / "clubs"
UPDATE_EXIT = 3


def _entries(league, country, women=False):
    sport = league.sport
    url = espn.TEAMS_URL.format(sport=sport.code, slug=league.slug)
    raw = espn.download(url, timeout=espn.DEFAULT_TIMEOUT, label=league.slug)
    payload = json.loads(raw)
    rows = payload["sports"][0]["leagues"][0].get("teams") or []
    for row in rows:
        team = row.get("team") or row
        team_id = str(team.get("id") or "").strip()
        if not team_id:
            continue
        yield {
            "id": team_id,
            "name": str(team.get("displayName") or team.get("name") or "").strip(),
            "short_name": str(team.get("shortDisplayName") or "").strip(),
            "slug": str(team.get("slug") or "").strip(),
            "league": league.slug,
            "league_name": league.name,
            "country": country,
            "women": bool(women),
            "asset": "clubs/{}.png".format(team_id),
        }


def inventory():
    rows = []
    for women, catalogue in ((False, MEN), (True, WOMEN)):
        for slug, country in catalogue:
            rows.extend(_entries(leagues.BY_SLUG[slug], country, women))
    league_order = {slug: index for index, (slug, _country) in enumerate(MEN + WOMEN)}
    rows.sort(key=lambda row: (league_order[row["league"]], row["name"]))
    return rows


def write(rows, path=MANIFEST):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")


def audit(rows):
    missing = [row for row in rows if not (ASSETS / (row["id"] + ".png")).is_file()]
    print("{} clubs, {} images, {} manquantes".format(
        len(rows), len(rows) - len(missing), len(missing)))
    for row in missing:
        print("{}\t{}\t{}\t{}".format(
            row["id"], row["league"], row["country"], row["name"]))
    return 1 if missing else 0


def changes(saved, current):
    """Equipes entrees et sorties du perimetre, dans l'ordre du catalogue."""
    saved_ids = {row["id"] for row in saved}
    current_ids = {row["id"] for row in current}
    added = [row for row in current if row["id"] not in saved_ids]
    removed = [row for row in saved if row["id"] not in current_ids]
    return added, removed


def _cell(value):
    return str(value or "").replace("|", "\\|").replace("\n", " ")


def _team_table(rows):
    if not rows:
        return "_Aucune._"
    lines = [
        "| Championnat | Equipe | ESPN ID | Asset attendu |",
        "| --- | --- | ---: | --- |",
    ]
    for row in rows:
        lines.append("| {} | {} | `{}` | `{}` |".format(
            _cell(row.get("league_name") or row["league"]),
            _cell(row["name"]), _cell(row["id"]),
            _cell("butbutbut/assets/" + row["asset"])))
    return "\n".join(lines)


def update_report(saved, current, checked_at=None):
    """Rapport Markdown humain, utilisable tel quel comme corps d'issue."""
    added, removed = changes(saved, current)
    checked_at = checked_at or datetime.now(timezone.utc)
    return """# Inventaire des themes de clubs

Verification ESPN du {date} : **{current_count} equipes actuellement**, contre
**{saved_count} dans le manifeste**.

## Nouvelles equipes a illustrer ({added_count})

{added_table}

## Equipes sorties du perimetre ({removed_count})

{removed_table}

## Mise a jour

1. Creer une illustration par nouvelle equipe dans la DA bleu nuit et or.
2. La normaliser sous `butbutbut/assets/clubs/<ESPN ID>.png`.
3. Lancer `python tools/optimize_club_themes.py`.
4. Lancer `python tools/club_theme_inventory.py --refresh` pour accepter le
   nouvel inventaire, puis la suite de tests.

L'issue disparaitra au prochain passage une fois le manifeste actualise.
""".format(
        date=checked_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        current_count=len(current), saved_count=len(saved),
        added_count=len(added), removed_count=len(removed),
        added_table=_team_table(added), removed_table=_team_table(removed))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true",
                        help="relit ESPN et reecrit le manifeste")
    parser.add_argument("--json-missing", type=int, default=0,
                        help="rend en JSON les N prochains assets manquants")
    parser.add_argument("--check-updates", type=Path, metavar="RAPPORT",
                        help="compare ESPN au manifeste et ecrit un rapport Markdown")
    args = parser.parse_args()
    if args.check_updates:
        if not MANIFEST.is_file():
            parser.error("le manifeste de reference n'existe pas")
        saved = json.loads(MANIFEST.read_text(encoding="utf-8"))
        current = inventory()
        added, removed = changes(saved, current)
        args.check_updates.write_text(update_report(saved, current), encoding="utf-8")
        print("{} nouvelles, {} sorties ; rapport : {}".format(
            len(added), len(removed), args.check_updates))
        raise SystemExit(UPDATE_EXIT if added else 0)
    if args.refresh or not MANIFEST.is_file():
        rows = inventory()
        write(rows)
    else:
        rows = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if args.json_missing:
        missing = [row for row in rows
                   if not (ASSETS / (row["id"] + ".png")).is_file()]
        print(json.dumps(missing[:args.json_missing], ensure_ascii=False))
        return
    raise SystemExit(audit(rows))


if __name__ == "__main__":
    main()
