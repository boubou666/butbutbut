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

_FRENCH_MONTHS = (
    "JANVIER", "FÉVRIER", "MARS", "AVRIL", "MAI", "JUIN",
    "JUILLET", "AOÛT", "SEPTEMBRE", "OCTOBRE", "NOVEMBRE", "DÉCEMBRE",
)

_STORY_STATS = (
    ("possessionPct", "Possession", True),
    ("totalShots", "Tirs", False),
    ("shotsOnTarget", "Tirs cadrés", False),
    ("wonCorners", "Corners", False),
)


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
        "home_stats": dict(match.home_stats),
        "away_stats": dict(match.away_stats),
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


def _story_date(story) -> str:
    """Une date éditoriale stable, sans dépendre de la locale du système."""
    value = str(story.get("created_text") or "")
    try:
        stamp = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        try:
            stamp = datetime.fromtimestamp(float(story.get("created_at")))
        except (TypeError, ValueError, OSError):
            return "MATCH TERMINÉ"
    return "{:02d} {} {}".format(
        stamp.day, _FRENCH_MONTHS[stamp.month - 1], stamp.year)


def _story_stats(story) -> str:
    """Les paires réellement publiées, comparées sans rien inventer."""
    home_stats = story.get("home_stats")
    away_stats = story.get("away_stats")
    if not isinstance(home_stats, dict) or not isinstance(away_stats, dict):
        return ""
    rows = []
    for name, label, percent in _STORY_STATS:
        try:
            home = float(home_stats.get(name))
            away = float(away_stats.get(name))
        except (TypeError, ValueError):
            continue
        if not (0 <= home <= 1e6 and 0 <= away <= 1e6):
            continue
        total = home + away
        share = 50.0 if not total else 100.0 * home / total
        template = "{:.0f}%" if percent else "{:g}"
        rows.append(
            '<li class="stat-row"><strong>{home}</strong><span>'
            '<small>{label}</small><i style="--home-share:{share:.1f}%" '
            'aria-hidden="true"></i></span><strong>{away}</strong></li>'
            .format(home=template.format(home), away=template.format(away),
                    label=label, share=share))
    if not rows:
        return ""
    return ('<section class="match-stats" aria-label="Statistiques du match">'
            '<div class="stats-heading"><span>Domicile</span><strong>Les chiffres</strong>'
            '<span>Extérieur</span></div><ul>{}</ul></section>'.format("".join(rows)))


def render(story) -> str:
    """Une carte HTML autonome : aucun CDN, police ou script distant."""
    esc = lambda value: html.escape(str(value or ""))
    rows = []
    for goal in story.get("goals", []):
        score = "{}–{}".format(goal.get("home_score", ""),
                               goal.get("away_score", ""))
        rows.append(
            '<li class="goal {side}"><span class="minute">{minute}</span>'
            '<span class="pulse" aria-hidden="true"></span>'
            '<span class="scorer"><strong>{scorer}</strong><small>{team}</small></span>'
            '<span class="step-score">{score}</span></li>'
            .format(side=esc(goal.get("side")), minute=esc(goal.get("minute")),
                    scorer=esc(goal.get("scorer")), team=esc(goal.get("team")),
                    score=esc(score)))
    if not rows:
        rows.append('<li class="empty">Aucun buteur publié par la source</li>')
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
    location = esc(story.get("venue_country"))
    date = esc(_story_date(story))
    meta = date + (" · " + location.upper() if location else "")
    download_name = esc(filename(story).rsplit(".", 1)[0] + ".png")
    stats_html = _story_stats(story)
    return """<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{home} {hs}–{as_} {away}</title><style>
.goal>*{{grid-row:1}}
.match-stats{{position:relative;z-index:1;margin:0 38px 18px;padding:13px 18px 15px;border:1px solid #d8d0c2;border-radius:14px;background:#f8f5eddd}}.stats-heading{{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;margin-bottom:9px;color:#8b8274;font-size:.55rem;font-weight:800;letter-spacing:.14em;text-transform:uppercase}}.stats-heading strong{{color:var(--ink);font-size:.6rem;letter-spacing:.18em}}.stats-heading span:last-child{{text-align:right}}.match-stats ul{{list-style:none;margin:0;padding:0}}.stat-row{{display:grid;grid-template-columns:45px minmax(0,1fr) 45px;align-items:center;gap:12px;min-height:32px}}.stat-row>strong{{font-size:.78rem;font-variant-numeric:tabular-nums}}.stat-row>strong:last-child{{text-align:right}}.stat-row span{{display:grid;gap:4px;text-align:center}}.stat-row small{{color:var(--muted);font-size:.61rem}}.stat-row i{{height:4px;border-radius:999px;background:linear-gradient(90deg,var(--home) 0 var(--home-share),var(--away) var(--home-share) 100%)}}@media(max-width:600px){{.match-stats{{margin:0 23px 16px;padding:12px}}.stat-row{{grid-template-columns:38px minmax(0,1fr) 38px;gap:8px}}}}
:root{{--home:#{hc};--away:#{ac};--paper:#f3efe5;--ink:#111827;--muted:#6b7280}}*{{box-sizing:border-box}}body{{margin:0;min-height:100vh;display:grid;place-items:center;background:#080d16;color:var(--ink);font:16px/1.35 Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;padding:28px}}.page{{display:grid;width:min(760px,100%);gap:18px;justify-items:center}}.ticket{{--notch-y:209px;position:relative;width:100%;min-height:500px;background:var(--paper);border-radius:24px;overflow:hidden;filter:drop-shadow(0 24px 35px #0009);-webkit-mask-image:radial-gradient(circle at 0 var(--notch-y),transparent 0 15px,#000 15.5px),radial-gradient(circle at 100% var(--notch-y),transparent 0 15px,#000 15.5px);-webkit-mask-composite:source-in;-webkit-mask-repeat:no-repeat;mask-image:radial-gradient(circle at 0 var(--notch-y),transparent 0 15px,#000 15.5px),radial-gradient(circle at 100% var(--notch-y),transparent 0 15px,#000 15.5px);mask-composite:intersect;mask-repeat:no-repeat}}.accent{{height:8px;background:linear-gradient(90deg,var(--home) 0 49.6%,#f3efe5 49.6% 50.4%,var(--away) 50.4%)}}.postcard{{position:absolute;z-index:0;right:-54px;bottom:-38px;width:390px;aspect-ratio:1;background-image:url('{artwork}');background-size:{background_size};background-position:{px}% {py}%;background-repeat:no-repeat;opacity:.13;filter:saturate(.7) contrast(1.15);pointer-events:none}}.masthead,.scoreboard,.divider,.timeline,.signature{{position:relative;z-index:1}}.masthead{{display:flex;justify-content:space-between;align-items:center;padding:25px 38px 10px;color:var(--muted);font-size:.68rem;font-weight:750;letter-spacing:.18em;text-transform:uppercase}}.competition{{color:var(--ink)}}.scoreboard{{display:grid;grid-template-columns:minmax(0,1fr) 180px minmax(0,1fr);align-items:center;gap:18px;padding:14px 38px 48px}}.team{{min-width:0}}.team.home{{text-align:right}}.team.away{{text-align:left}}.team-label{{display:block;margin-bottom:7px;color:var(--muted);font-size:.61rem;font-weight:800;letter-spacing:.16em;text-transform:uppercase}}h1{{margin:0;font-size:clamp(1.15rem,3.4vw,2rem);line-height:1.08;letter-spacing:-.035em;text-wrap:balance}}.result{{position:relative;display:grid;grid-template-columns:1fr 22px 1fr;align-items:center;text-align:center;font-family:"Arial Black",Impact,ui-sans-serif,sans-serif;font-size:clamp(3.5rem,11vw,6.2rem);line-height:.85;letter-spacing:-.09em;font-variant-numeric:tabular-nums}}.result i{{color:#9ca3af;font-family:ui-serif,Georgia,serif;font-size:2rem;font-style:normal;font-weight:400;letter-spacing:0}}.result em{{position:absolute;left:50%;bottom:-29px;transform:translateX(-50%);padding:5px 10px;border-radius:999px;background:var(--ink);color:var(--paper);font-family:ui-sans-serif,system-ui,sans-serif;font-size:.58rem;font-style:normal;font-weight:800;letter-spacing:.16em;white-space:nowrap}}.divider{{display:flex;align-items:center;gap:16px;margin:0 38px;color:#8b8274;font-size:.6rem;font-weight:800;letter-spacing:.18em;text-transform:uppercase}}.divider:before,.divider:after{{content:"";height:1px;flex:1;background:#d4ccbe}}.timeline{{list-style:none;margin:0;padding:13px 38px 16px}}.goal{{display:grid;grid-template-columns:minmax(0,1fr) 10px 48px 58px 48px 10px minmax(0,1fr);align-items:center;gap:10px;min-height:58px;border-bottom:1px solid #ddd6c9}}.goal:last-child{{border-bottom:0}}.minute{{color:var(--ink);font-family:ui-serif,Georgia,serif;font-size:1.05rem;font-weight:700;font-variant-numeric:tabular-nums}}.pulse{{width:9px;height:9px;border:2px solid var(--paper);border-radius:50%;background:var(--home);box-shadow:0 0 0 1px var(--home)}}.home .scorer{{grid-column:1;align-items:flex-end;text-align:right}}.home .pulse{{grid-column:2}}.home .minute{{grid-column:3;text-align:right}}.away .minute{{grid-column:5;text-align:left}}.away .pulse{{grid-column:6;background:var(--away);box-shadow:0 0 0 1px var(--away)}}.away .scorer{{grid-column:7;align-items:flex-start;text-align:left}}.scorer{{display:flex;flex-direction:column;min-width:0}}.scorer strong{{overflow:hidden;font-size:.92rem;letter-spacing:-.01em;text-overflow:ellipsis;white-space:nowrap}}.scorer small{{color:var(--muted);font-size:.66rem}}.step-score{{grid-column:4;justify-self:center;padding:5px 8px;border:1px solid #d2cabc;border-radius:7px;background:#f8f5ed;font-size:.78rem;font-weight:800;font-variant-numeric:tabular-nums}}.empty{{padding:25px;text-align:center;color:var(--muted);font-size:.82rem}}.signature{{display:flex;justify-content:space-between;align-items:center;padding:13px 38px 17px;border-top:1px dashed #c9c0b0;color:#857b6b;font-size:.59rem;font-weight:750;letter-spacing:.15em;text-transform:uppercase}}.signature strong{{color:var(--ink);font-size:.68rem;letter-spacing:.22em}}.actions{{display:flex;align-items:center;gap:12px;color:#91a0b7;font-size:.78rem}}button{{display:inline-flex;align-items:center;gap:9px;border:1px solid #344158;border-radius:999px;background:#111827;color:#f8fafc;padding:11px 17px;font:inherit;font-weight:750;cursor:pointer;box-shadow:0 10px 28px #0005}}button:hover{{background:#192235;border-color:#506078}}button:focus-visible{{outline:3px solid #f3efe5;outline-offset:3px}}button:disabled{{cursor:wait;opacity:.6}}@media(max-width:600px){{body{{padding:14px}}.ticket{{--notch-y:196px}}.masthead{{align-items:flex-start;gap:12px;padding:21px 23px 8px}}.match-meta{{max-width:55%;text-align:right}}.scoreboard{{grid-template-columns:1fr 116px 1fr;gap:9px;padding:15px 23px 45px}}h1{{font-size:clamp(.95rem,5vw,1.35rem)}}.result{{font-size:clamp(3rem,18vw,4.4rem)}}.divider{{margin:0 23px}}.timeline{{padding:13px 23px}}.goal{{grid-template-columns:minmax(0,1fr) 8px 34px 50px 34px 8px minmax(0,1fr);gap:5px}}.scorer strong{{font-size:.8rem}}.scorer small{{font-size:.58rem}}.signature{{padding:13px 23px 16px}}.actions{{flex-direction:column}}}}
</style></head><body><main class="page"><article class="ticket" id="card"><div class="accent"></div><div class="postcard" aria-hidden="true"></div><header class="masthead"><span class="competition">{league}</span><span class="match-meta">{meta}</span></header><section class="scoreboard" aria-label="Score final"><div class="team home"><span class="team-label">Domicile</span><h1>{home}</h1></div><div class="result"><span>{hs}</span><i>—</i><span>{as_}</span><em>Score final</em></div><div class="team away"><span class="team-label">Extérieur</span><h1>{away}</h1></div></section><div class="divider"><span>Le fil du match</span></div><ol class="timeline">{goals}</ol>{stats}<footer class="signature"><strong>butbutbut</strong><span>Un match. Une trace.</span></footer></article><div class="actions"><button id="save" type="button" aria-describedby="save-status"><span aria-hidden="true">↓</span> Enregistrer en PNG</button><span id="save-status" role="status">Prête à partager</span></div></main><script>
const button=document.getElementById('save'),status=document.getElementById('save-status');
button.addEventListener('click',async()=>{{button.disabled=true;status.textContent='Création de l’image…';try{{if(document.fonts)await document.fonts.ready;const card=document.getElementById('card'),box=card.getBoundingClientRect(),copy=card.cloneNode(true),styles=document.querySelector('style').textContent;copy.style.width=box.width+'px';copy.style.height=box.height+'px';const content=new XMLSerializer().serializeToString(copy),svg=`<svg xmlns="http://www.w3.org/2000/svg" width="${{box.width}}" height="${{box.height}}"><foreignObject width="100%" height="100%"><div xmlns="http://www.w3.org/1999/xhtml"><style>${{styles}}</style>${{content}}</div></foreignObject></svg>`,url=URL.createObjectURL(new Blob([svg],{{type:'image/svg+xml;charset=utf-8'}})),image=new Image();await new Promise((resolve,reject)=>{{image.onload=resolve;image.onerror=reject;image.src=url}});const scale=2,canvas=document.createElement('canvas');canvas.width=Math.round(box.width*scale);canvas.height=Math.round(box.height*scale);canvas.getContext('2d').drawImage(image,0,0,canvas.width,canvas.height);URL.revokeObjectURL(url);const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/png'));if(!blob)throw new Error('export');const link=document.createElement('a');link.download='{download_name}';link.href=URL.createObjectURL(blob);link.click();setTimeout(()=>URL.revokeObjectURL(link.href),1000);status.textContent='Image enregistrée';}}catch(error){{status.textContent='Export impossible dans ce navigateur';}}finally{{button.disabled=false;}}}});
</script></body></html>""".format(
        home=home, away=away, hs=esc(story.get("home_score")),
        as_=esc(story.get("away_score")), league=esc(story.get("league")),
        hc=esc(story.get("home_color") or "64748b"),
        ac=esc(story.get("away_color") or "64748b"), goals="".join(rows),
        artwork=artwork, background_size=background_size,
        px=position_x, py=position_y, meta=meta,
        download_name=download_name, stats=stats_html)
