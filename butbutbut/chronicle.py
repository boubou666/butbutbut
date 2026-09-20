"""Recits HTML autonomes construits a partir du journal de buts.

Deux echelles, une seule matiere :

* la Nuit des buts raconte une soiree comme un multiplex termine ;
* la Constellation pose toute une periode sur une carte, un point par but.

Le journal est volontairement la seule source. Ces pages restent donc
disponibles daemon arrete, ne font aucun appel reseau et ne promettent rien que
butbutbut n'ait effectivement vu passer.
"""

from __future__ import annotations

import hashlib
import html
from datetime import datetime

from . import journal


def _esc(value) -> str:
    return html.escape(str(value or ""))


def _stamp(entry):
    try:
        return datetime.strptime("{} {}".format(entry.day, entry.time),
                                 "%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return None


def _color(label: str) -> str:
    """Une couleur stable par competition, lisible sur le fond sombre."""
    digest = hashlib.sha1(str(label).encode("utf-8")).digest()
    hue = int.from_bytes(digest[:2], "big") % 360
    return "hsl({}, 72%, 62%)".format(hue)


def _base(title: str, eyebrow: str, body: str, extra_css: str = "") -> str:
    return """<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{title}</title><style>
:root{{--ink:#f8fafc;--muted:#94a3b8;--gold:#fbca3e;--panel:#101827;--line:#273449}}
*{{box-sizing:border-box}}body{{margin:0;min-height:100vh;background:radial-gradient(circle at 75% -10%,#25324b 0,transparent 38%),#070b14;color:var(--ink);font:16px/1.45 system-ui,sans-serif}}main{{width:min(1120px,100%);margin:auto;padding:48px 22px 80px}}.eyebrow{{color:var(--gold);text-transform:uppercase;letter-spacing:.18em;font-size:.75rem;font-weight:800}}h1{{font-size:clamp(2.4rem,7vw,5.4rem);line-height:.92;letter-spacing:-.065em;margin:.22em 0 .35em}}.lede{{max-width:720px;color:var(--muted);font-size:1.05rem}}.panel{{background:linear-gradient(145deg,#131c2e,#0c1220);border:1px solid var(--line);border-radius:24px;box-shadow:0 24px 70px #0007}}.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin:32px 0}}.kpi{{padding:18px}}.kpi strong{{display:block;font-size:2rem;letter-spacing:-.05em}}.kpi span,footer{{color:var(--muted)}}footer{{margin-top:34px;font-size:.78rem;text-align:center}}{extra_css}
</style></head><body><main><div class="eyebrow">{eyebrow}</div>{body}<footer>Créé localement par butbutbut · aucune ressource distante</footer></main></body></html>""".format(
        title=_esc(title), eyebrow=_esc(eyebrow), body=body,
        extra_css=extra_css)


def evenings(entries) -> list:
    """Les soirees presentes, de la plus recente a la plus ancienne."""
    return sorted({journal.evening_of(entry) for entry in entries}, reverse=True)


def _night_entries(entries, day="") -> tuple:
    available = evenings(entries)
    selected = day or (available[0] if available else "")
    return selected, [entry for entry in entries
                      if journal.evening_of(entry) == selected]


def _match_groups(entries) -> list:
    order, grouped = [], {}
    for entry in entries:
        key = entry.match
        if key not in grouped:
            order.append(key)
            grouped[key] = []
        grouped[key].append(entry)
    return [(key, grouped[key]) for key in order]


def _lead_changes(entries) -> int:
    leader = 0
    changes = 0
    for entry in entries:
        current = ((entry.home_score > entry.away_score)
                   - (entry.home_score < entry.away_score))
        if current and leader and current != leader:
            changes += 1
        if current:
            leader = current
    return changes


def _rush(entries, seconds=120) -> int:
    stamps = sorted(stamp for stamp in (_stamp(row) for row in entries)
                    if stamp is not None)
    best = left = 0
    for right, stamp in enumerate(stamps):
        while (stamp - stamps[left]).total_seconds() > seconds:
            left += 1
        best = max(best, right - left + 1)
    return best


def render_night(entries, day="") -> str:
    """La chronique autonome d'une soiree (6 h a 6 h)."""
    selected, raw = _night_entries(list(entries), day)
    kept, orphans = journal.settle(raw)
    matches = _match_groups(raw)
    leagues = len({entry.league for entry in kept})
    changes = sum(_lead_changes(rows) for _key, rows in matches)
    rush = _rush(kept)

    cards = []
    for (league, home, away), rows in matches:
        last = rows[-1]
        goals, _ = journal.settle(rows)
        timeline = []
        for goal in goals:
            who = goal.scorer or goal.detail or goal.team
            timeline.append(
                '<li><time>{}</time><span>{}</span><b>{}–{}</b></li>'.format(
                    _esc(goal.minute or goal.time), _esc(who),
                    goal.home_score, goal.away_score))
        cards.append(
            '<article class="match panel" style="--club:{}"><div class="league">{}</div>'
            '<h2><span>{}</span><strong>{}–{}</strong><span>{}</span></h2>'
            '<ol>{}</ol></article>'.format(
                _color(league), _esc(league), _esc(home), last.home_score,
                last.away_score, _esc(away), "".join(timeline)))

    scorer_rows = journal.scoreboard(raw).rows[:5]
    podium = "".join('<li><b>{}</b><span>{} · {} but{}</span></li>'.format(
        _esc(name), _esc(clubs), count, "s" if count != 1 else "")
        for name, count, clubs in scorer_rows)
    if not podium:
        podium = '<li class="empty">Aucun buteur publié par la source</li>'

    title = "La Nuit des buts"
    date = _esc(selected or "aucune soirée")
    body = """<h1>La Nuit<br>des buts</h1><p class="lede">La soirée du {date}, reconstruite depuis les alertes réellement reçues.</p>
<section class="kpis"><div class="kpi panel"><strong>{goals}</strong><span>buts confirmés</span></div><div class="kpi panel"><strong>{matches}</strong><span>matchs animés</span></div><div class="kpi panel"><strong>{leagues}</strong><span>compétitions</span></div><div class="kpi panel"><strong>{rush}</strong><span>buts en 2 minutes</span></div><div class="kpi panel"><strong>{changes}</strong><span>changements de leader</span></div></section>
<div class="grid">{cards}</div><section class="podium panel"><div><div class="eyebrow">Les visages de la nuit</div><h3>Les buteurs</h3></div><ol>{podium}</ol></section>{note}""".format(
        date=date, goals=len(kept), matches=len(matches), leagues=leagues,
        rush=rush, changes=changes, cards="".join(cards), podium=podium,
        note=('<p class="note">{} annulation(s) sans but correspondant dans cette fenêtre.</p>'.format(orphans)
              if orphans else ""))
    css = """.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,430px),1fr));gap:18px}.match{padding:22px;border-top:5px solid var(--club)}.league{color:var(--club);text-transform:uppercase;letter-spacing:.12em;font-size:.72rem;font-weight:800}.match h2{display:grid;grid-template-columns:1fr auto 1fr;gap:14px;align-items:center;font-size:1rem}.match h2 span:first-child{text-align:right}.match h2 strong{font-size:2.35rem}.match ol,.podium ol{list-style:none;margin:0;padding:0}.match li{display:grid;grid-template-columns:62px 1fr auto;gap:10px;padding:9px 0;border-top:1px solid var(--line)}time{color:var(--muted)}.podium{margin-top:18px;padding:24px;display:grid;grid-template-columns:minmax(180px,.7fr) 1fr;gap:24px}.podium h3{font-size:2rem;margin:.25em 0}.podium li{display:flex;justify-content:space-between;gap:12px;padding:8px 0;border-top:1px solid var(--line)}.podium li span,.note{color:var(--muted)}@media(max-width:620px){.podium{grid-template-columns:1fr}}"""
    return _base(title, "Chronique de soirée", body, css)


def _minute(entry) -> int:
    clock = entry.clock
    if clock is None:
        return 0
    return max(0, min(120, clock[0] + clock[1]))


def render_constellation(entries, label="depuis le début du journal") -> str:
    """Une carte SVG de la periode, un point par but confirme."""
    raw = list(entries)
    kept, orphans = journal.settle(raw)
    days = sorted({journal.evening_of(entry) for entry in kept})
    leagues = sorted({entry.league for entry in kept})
    width = 1000
    left, right, top, row_h = 105, 28, 42, 44
    plot_w = width - left - right
    height = max(180, top + max(1, len(days)) * row_h + 48)
    day_y = {day: top + index * row_h + row_h / 2
             for index, day in enumerate(days)}

    grid = []
    for minute in range(0, 121, 15):
        x = left + (minute / 120.0) * plot_w
        grid.append('<line x1="{x:.1f}" y1="24" x2="{x:.1f}" y2="{bottom}"/>'
                    '<text x="{x:.1f}" y="18">{minute}′</text>'.format(
                        x=x, bottom=height - 30, minute=minute))
    for day in days:
        y = day_y[day]
        grid.append('<line x1="{}" y1="{:.1f}" x2="{}" y2="{:.1f}"/>'.format(
            left, y, width - right, y))
        grid.append('<text class="day" x="{}" y="{:.1f}">{}</text>'.format(
            left - 12, y + 4, _esc(day[5:])))

    points = []
    for index, entry in enumerate(kept):
        minute = _minute(entry)
        x = left + (minute / 120.0) * plot_w
        y = day_y.get(journal.evening_of(entry), top + row_h / 2)
        # Les buts simultanes restent distincts au lieu de se recouvrir.
        y += ((index % 3) - 1) * 5
        when = (entry.minute if entry.clock is not None
                else "minute inconnue ({})".format(entry.minute or "?"))
        title = "{} · {} · {} · {}".format(
            when, entry.score_line(),
            entry.scorer or entry.detail, entry.league)
        points.append('<circle cx="{:.1f}" cy="{:.1f}" r="6" fill="{}">'
                      '<title>{}</title></circle>'.format(
                          x, y, _color(entry.league), _esc(title)))

    legend = "".join('<span><i style="background:{}"></i>{}</span>'.format(
        _color(league), _esc(league)) for league in leagues)
    svg = ('<svg class="sky" viewBox="0 0 {} {}" role="img" '
           'aria-label="Un point par but, rangé par soirée et minute de jeu">'
           '<g class="grid">{}</g><g class="stars">{}</g></svg>').format(
               width, height, "".join(grid), "".join(points))
    body = """<h1>La constellation<br>de la saison</h1><p class="lede">{label}. Chaque étoile est un but confirmé ; sa position raconte quand il est tombé.</p>
<section class="kpis"><div class="kpi panel"><strong>{goals}</strong><span>étoiles</span></div><div class="kpi panel"><strong>{days}</strong><span>soirées</span></div><div class="kpi panel"><strong>{leagues}</strong><span>compétitions</span></div></section><section class="chart panel">{svg}<div class="legend">{legend}</div></section>{note}""".format(
        label=_esc(label), goals=len(kept), days=len(days), leagues=len(leagues),
        svg=svg, legend=legend,
        note=('<p class="note">{} annulation(s) n’ont pas pu être rattachées à une étoile.</p>'.format(orphans)
              if orphans else ""))
    css = """.chart{padding:16px;overflow-x:auto}.sky{display:block;min-width:760px;width:100%;height:auto}.grid line{stroke:#263149;stroke-width:1}.grid text{fill:#64748b;font-size:12px;text-anchor:middle}.grid .day{text-anchor:end;fill:#94a3b8}.stars circle{stroke:#fff9;stroke-width:1;filter:drop-shadow(0 0 5px currentColor)}.legend{display:flex;gap:14px;flex-wrap:wrap;padding:16px 10px 6px;color:var(--muted);font-size:.82rem}.legend span{display:flex;align-items:center;gap:7px}.legend i{width:9px;height:9px;border-radius:50%;box-shadow:0 0 8px currentColor}.note{color:var(--muted)}"""
    return _base("La Constellation de la saison", "Atlas du journal", body, css)
