"""Cartes souvenir persistantes, fabriquees a la fin d'un match."""

from __future__ import annotations

import html
import base64
import json
import os
import re
import time
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from . import teams, themes

MAX_STORIES = 50


def _play_row(play, match, home_score, away_score) -> dict:
    side = match.side_of(play.team_id)
    return {
        "side": side or "",
        "team": match.home if side == "home" else match.away,
        "scorer": play.scorer or play.prefix(),
        "minute": play.minute or "",
        "kind": play.kind_key,
        "home_score": home_score,
        "away_score": away_score,
    }


def from_match(match, created_at=None) -> dict:
    """Une histoire autonome a partir de la photo finale publiee par ESPN."""
    home_score = away_score = 0
    goals = []
    for play in match.plays:
        side = match.side_of(play.team_id)
        if side == "home":
            home_score += int(play.points or 0)
        elif side == "away":
            away_score += int(play.points or 0)
        goals.append(_play_row(play, match, home_score, away_score))
    created_at = time.time() if created_at is None else float(created_at)
    return {
        "id": str(match.id),
        "created_at": created_at,
        "created_text": datetime.fromtimestamp(created_at).isoformat(timespec="seconds"),
        "league": match.league.name,
        "league_label": match.league.label,
        "sport": match.sport.code,
        "home": match.home,
        "away": match.away,
        "home_score": match.home_score,
        "away_score": match.away_score,
        "home_logo": match.home_logo,
        "away_logo": match.away_logo,
        "home_color": match.home_color,
        "away_color": match.away_color,
        "venue_country": getattr(match, "venue_country", ""),
        "motif": themes.match_motif(match),
        "club_theme_id": (match.away_id if match.winner == "away"
                          else match.home_id),
        "goals": goals,
    }


def read(path) -> list:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return []
    return data if isinstance(data, list) else []


def write(path, stories) -> bool:
    path = Path(path)
    tmp = path.with_name("{}.{}.tmp".format(path.name, os.getpid()))
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tmp.open("w", encoding="utf-8") as handle:
            json.dump(list(stories)[-MAX_STORIES:], handle, ensure_ascii=False,
                      indent=1)
        os.replace(str(tmp), str(path))
        return True
    except Exception:
        try:
            tmp.unlink()
        except Exception:
            pass
        return False


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.stories = read(path)

    def add(self, story) -> bool:
        self.stories = [row for row in self.stories
                        if str(row.get("id")) != str(story.get("id"))]
        self.stories.append(dict(story))
        self.stories = self.stories[-MAX_STORIES:]
        return write(self.path, self.stories)

    def latest(self, query=""):
        needle = teams.normalize(query)
        for story in reversed(self.stories):
            names = " ".join((str(story.get("home", "")),
                              str(story.get("away", "")),
                              str(story.get("league", ""))))
            if not needle or needle in teams.normalize(names):
                return story
        return None


def filename(story) -> str:
    base = "{}-{}-{}".format(story.get("created_text", "match")[:10],
                             story.get("home", "home"),
                             story.get("away", "away"))
    slug = re.sub(r"[^a-z0-9]+", "-", teams.normalize(base)).strip("-")
    return (slug or "match") + ".html"


@lru_cache(maxsize=512)
def _image_data(path) -> str:
    """Une image embarquee en data URI pour que le souvenir reste autonome."""
    try:
        encoded = base64.b64encode(Path(path).read_bytes()).decode("ascii")
    except Exception:
        return ""
    return "data:image/png;base64," + encoded


def _atlas_data() -> str:
    return _image_data(str(themes.ATLAS))


def render(story) -> str:
    """Une carte HTML autonome : aucun CDN, police ou script distant."""
    esc = lambda value: html.escape(str(value or ""))
    rows = []
    for goal in story.get("goals", []):
        score = "{}–{}".format(goal.get("home_score", ""),
                               goal.get("away_score", ""))
        rows.append(
            '<li class="goal {side}"><span class="minute">{minute}</span>'
            '<span class="scorer">{scorer}</span><span class="score">{score}</span></li>'
            .format(side=esc(goal.get("side")), minute=esc(goal.get("minute")),
                    scorer=esc(goal.get("scorer")), score=esc(score)))
    if not rows:
        rows.append('<li class="empty">Aucun marqueur publie par la source</li>')
    home = esc(story.get("home"))
    away = esc(story.get("away"))
    motif = str(story.get("motif") or "stadium")
    club = themes.club_asset(story.get("club_theme_id"))
    if club:
        position_x, position_y = 50, 50
        background_size = "contain"
        artwork = _image_data(str(club))
    else:
        position_x, position_y = themes.css_position(motif)
        background_size = "500% 400%"
        artwork = _atlas_data()
    return """<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{home} {hs}–{as_} {away}</title><style>
:root{{--home:#{hc};--away:#{ac}}}*{{box-sizing:border-box}}body{{margin:0;min-height:100vh;display:grid;place-items:center;background:#070b14;color:#f8fafc;font:16px/1.4 system-ui,sans-serif;padding:24px}}.card{{position:relative;width:min(680px,100%);background:linear-gradient(145deg,#141b2d,#0d1220);border:1px solid #2b3650;border-radius:28px;overflow:hidden;box-shadow:0 30px 80px #0009}}.postcard{{position:absolute;z-index:0;right:-24px;top:4px;width:260px;aspect-ratio:1;background-image:url('{artwork}');background-size:{background_size};background-position:{px}% {py}%;background-repeat:no-repeat;opacity:.52;pointer-events:none}}.bar,header,ol,footer{{position:relative;z-index:1}}.bar{{height:7px;background:linear-gradient(90deg,var(--home),var(--away))}}header{{padding:30px 32px 22px;text-align:center}}.league{{color:#94a3b8;text-transform:uppercase;letter-spacing:.16em;font-size:.75rem}}h1{{display:grid;grid-template-columns:1fr auto 1fr;gap:18px;align-items:center;margin:22px 0 0;font-size:clamp(1.1rem,4vw,2rem)}}h1 span:first-child{{text-align:right}}h1 span:last-child{{text-align:left}}strong{{font-size:clamp(2.5rem,10vw,5rem);letter-spacing:-.08em}}ol{{list-style:none;margin:0;padding:0 32px 30px}}li{{display:grid;grid-template-columns:70px 1fr 70px;gap:12px;padding:12px 0;border-top:1px solid #263149}}.minute{{color:#94a3b8}}.score{{font-variant-numeric:tabular-nums;text-align:right;font-weight:700}}.away .scorer{{text-align:right}}.empty{{display:block;text-align:center;color:#94a3b8}}footer{{padding:16px 32px;background:#0a0f1b;color:#64748b;font-size:.8rem;text-align:center}}
</style></head><body><article class="card"><div class="postcard" aria-hidden="true"></div><div class="bar"></div><header><div class="league">{league}</div><h1><span>{home}</span><strong>{hs}–{as_}</strong><span>{away}</span></h1></header><ol>{goals}</ol><footer>Souvenir créé localement par butbutbut</footer></article></body></html>""".format(
        home=home, away=away, hs=esc(story.get("home_score")),
        as_=esc(story.get("away_score")), league=esc(story.get("league")),
        hc=esc(story.get("home_color") or "64748b"),
        ac=esc(story.get("away_color") or "64748b"), goals="".join(rows),
        artwork=artwork, background_size=background_size,
        px=position_x, py=position_y)
