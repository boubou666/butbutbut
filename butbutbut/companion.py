"""Ecran compagnon HTTP local, sans dependance ni ressource distante."""

from __future__ import annotations

import json
import sqlite3
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import site_feed, souvenir, state, streaming

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


class Invalid(ValueError):
    pass


def parse_bind(value):
    text = str(value or "").strip()
    host, port = DEFAULT_HOST, DEFAULT_PORT
    if text:
        if ":" in text:
            host, raw_port = text.rsplit(":", 1)
            host = host.strip() or DEFAULT_HOST
        else:
            raw_port = text
        try:
            port = int(raw_port)
        except ValueError:
            raise Invalid("adresse compagnon illisible : {!r}".format(text))
    if not 1 <= port <= 65535:
        raise Invalid("le port compagnon doit etre compris entre 1 et 65535")
    return host, port


PAGE = r"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>butbutbut — compagnon</title><style>
*{box-sizing:border-box}body{margin:0;background:#070b14;color:#f8fafc;font:16px/1.45 system-ui,sans-serif}main{max-width:980px;margin:auto;padding:32px 18px 80px}header{display:flex;justify-content:space-between;align-items:center;gap:16px;margin-bottom:28px}.controls,.story-actions{display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end}h1{margin:0;font-size:clamp(1.6rem,5vw,3rem);letter-spacing:-.04em}.live{color:#fbca3e}.status{color:#94a3b8}.panel{background:#111827;border:1px solid #273449;border-radius:22px;padding:20px;margin:16px 0}.match,.event,.story{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:14px;padding:14px 0;border-top:1px solid #263149}.panel>:nth-child(2){border-top:0}.match-link{color:inherit;text-decoration:none;border-radius:12px}.match-link:hover{background:#172033}.home{text-align:right}.score{font-size:1.55rem;font-weight:800;font-variant-numeric:tabular-nums}.meta{grid-column:1/-1;text-align:center;color:#94a3b8;font-size:.85rem}.event{grid-template-columns:90px 1fr auto}.event .home{text-align:left}.context{color:#fbca3e;text-transform:uppercase;font-size:.75rem;letter-spacing:.1em}.story{grid-template-columns:1fr auto 1fr}.story-actions{grid-column:1/-1;justify-self:center}.story-link{border:1px solid #39475f;border-radius:999px;padding:6px 12px;text-decoration:none;font-size:.76rem;font-weight:750}.story-link:hover{background:#1f2937}.muted{color:#94a3b8}button,select{border:0;border-radius:999px;padding:11px 16px;font:inherit}select{background:#1f2937;color:#f8fafc}button{background:#fbca3e;color:#111827;font-weight:800;cursor:pointer}button:disabled{opacity:.45;cursor:not-allowed}.hidden{display:none}.empty{color:#64748b;padding:12px 0}a{color:#fbca3e}footer{margin-top:30px;color:#64748b;font-size:.8rem}</style></head><body><main><header><div><h1>butbutbut <span class="live">●</span></h1><div id="status" class="status">Connexion…</div></div><div class="controls"><select id="kickoff" class="hidden"></select><button id="sync">Je vois le coup d’envoi</button></div></header><section id="delay" class="panel hidden"></section><section class="panel"><h2>En direct</h2><div id="matches"></div></section><section class="panel"><h2>Dernières alertes</h2><div id="events"></div></section><section class="panel"><h2>Souvenirs</h2><div id="stories"></div></section><footer>Tout reste sur cette machine. Aucune police, image ou bibliothèque distante n’est chargée par cette page.</footer></main><script>
const $=id=>document.getElementById(id), esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function empty(text){return `<div class="empty">${esc(text)}</div>`}function match(m){return `<a class="match match-link" href="/match?id=${encodeURIComponent(m.id)}"><span class="home">${esc(m.home)}</span><span class="score">${esc(m.home_score)}–${esc(m.away_score)}</span><span>${esc(m.away)}</span><span class="meta">${esc(m.league)} · ${esc(m.clock)} · Ouvrir le Match Center</span></a>`}function event(e){const body=`<span class="context">${esc(e.context_label||e.title)}</span><span class="home">${esc(e.score_line)}<br><span class="muted">${esc(e.detail)}</span></span><span>${esc(e.minute)}</span>`;return e.match_id?`<a class="event match-link" href="/match?id=${encodeURIComponent(e.match_id)}">${body}</a>`:`<div class="event">${body}</div>`}function story(s){return `<div class="story"><span class="home">${esc(s.home)}</span><span class="score">${esc(s.home_score)}–${esc(s.away_score)}</span><span>${esc(s.away)}</span><span class="meta">${esc(s.league)} · ${esc(s.goals?.length||0)} action(s) de score</span><span class="story-actions"><a class="story-link" href="/match?id=${encodeURIComponent(s.id)}">Match Center</a><a class="story-link" href="/souvenir?id=${encodeURIComponent(s.id)}" target="_blank" rel="noopener">Ouvrir et enregistrer la carte</a></span></div>`}
async function refresh(){try{const r=await fetch('/api/state',{cache:'no-store'}),d=await r.json(),delay=Number(d.stream_delay||0),ks=d.recent_kickoffs||[];$('status').textContent=d.updated_text?`Dernier relevé : ${d.updated_text}`:'Daemon arrêté ou état indisponible';$('sync').disabled=!ks.length;$('kickoff').classList.toggle('hidden',ks.length<2);$('kickoff').innerHTML=ks.slice().reverse().map(k=>`<option value="${esc(k.id)}">${esc(k.home)} – ${esc(k.away)}</option>`).join('');if(delay>0){$('delay').classList.remove('hidden');$('delay').innerHTML=`Flux synchronisé avec ${Math.round(delay)} s de retard. Les scores bruts sont masqués ici.`;$('matches').innerHTML=empty('Le fil synchronisé apparaît dans les alertes ci-dessous.')}else{$('delay').classList.add('hidden');$('matches').innerHTML=(d.matches||[]).map(match).join('')||empty('Aucun match en cours.')} $('events').innerHTML=(d.recent_events||[]).slice().reverse().map(event).join('')||empty('Aucune alerte récente.');$('stories').innerHTML=(d.souvenirs||[]).slice().reverse().map(story).join('')||empty('Aucun match terminé depuis l’installation.')}catch(e){$('status').textContent='Compagnon indisponible';}}$('sync').onclick=async()=>{const id=$('kickoff').value||'';const r=await fetch('/api/sync?match='+encodeURIComponent(id),{method:'POST'}),d=await r.json();alert(d.message||d.error);refresh()};refresh();setInterval(refresh,2000);
</script></body></html>"""


MATCH_PAGE = r"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>butbutbut — Match Center</title><style>
*{box-sizing:border-box}body{margin:0;background:#070b14;color:#f8fafc;font:16px/1.45 system-ui,sans-serif}main{max-width:900px;margin:auto;padding:28px 18px 80px}a{color:#fbca3e;text-decoration:none}.back{display:inline-block;margin-bottom:24px}.card{background:#111827;border:1px solid #273449;border-radius:24px;padding:clamp(18px,4vw,32px);margin:16px 0}.eyebrow{color:#fbca3e;text-transform:uppercase;letter-spacing:.12em;font-size:.76rem;font-weight:800;text-align:center}.muted{color:#94a3b8}.center{text-align:center}.teams{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:clamp(12px,4vw,38px);margin:28px 0}.team{font-size:clamp(1.05rem,4vw,1.6rem);font-weight:750;color:inherit}.team-link{color:inherit}.home{text-align:right}.score{font-size:clamp(2rem,8vw,4.6rem);line-height:1;font-weight:900;letter-spacing:-.05em;font-variant-numeric:tabular-nums}.status{display:inline-block;background:#263149;border-radius:999px;padding:6px 12px;font-size:.78rem;font-weight:800}.status.live{background:#7f1d1d;color:#fecaca}.notice{border-color:#a16207;background:#241b09}.notice h1{margin-top:0}.section-title{margin:0 0 16px}.timeline{list-style:none;margin:0;padding:0}.timeline li{display:grid;grid-template-columns:54px 1fr;gap:14px;padding:13px 0;border-top:1px solid #263149}.timeline li:first-child{border-top:0}.minute{font-weight:850;color:#fbca3e;font-variant-numeric:tabular-nums}.event-label{font-weight:750}.tag{color:#94a3b8;font-size:.82rem}.stats-row{display:grid;grid-template-columns:48px 1fr 48px;align-items:center;gap:12px;margin:15px 0}.stats-row strong:first-child{text-align:right}.stat-label{text-align:center;color:#cbd5e1;font-size:.82rem}.meter{height:7px;border-radius:99px;background:#334155;margin-top:6px;overflow:hidden}.meter span{display:block;height:100%;background:#fbca3e}.empty{color:#64748b}.hidden{display:none}@media(max-width:540px){.teams{gap:10px}.team{font-size:1rem}.card{border-radius:18px}.stats-row{grid-template-columns:40px 1fr 40px}}</style></head><body><main><a class="back" href="/">← Retour au compagnon</a><div id="app" class="card center"><span class="muted">Chargement du match…</span></div><footer class="center muted">Données conservées sur cette machine, sans ressource distante.</footer></main><script>
const app=document.getElementById('app'),esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const labels={scheduled:'À venir',live:'En direct',finished:'Terminé',postponed:'Reporté',cancelled:'Annulé'},statLabels={possessionPct:'Possession',totalShots:'Tirs',shotsOnTarget:'Tirs cadrés',wonCorners:'Corners'},decision={penalties:'Après tirs au but',extra_time:'Après prolongation'};
function dateLabel(value){if(!value)return'';const d=new Date(value);return Number.isNaN(d.getTime())?'':d.toLocaleString('fr-FR',{dateStyle:'long',timeStyle:'short'})}
function stage(m){return [m.edition_name,m.group_name,m.round_name,m.leg_number?`Match ${m.leg_number}`:''].filter(Boolean).join(' · ')}
function teamLink(t,cls='team-link'){return t.external_id?`<a class="${cls}" href="/team?id=${encodeURIComponent(t.external_id)}">${esc(t.name)}</a>`:`<span class="${cls}">${esc(t.name)}</span>`}
function minute(e){if(e.minute==null)return'—';return `${e.minute}${e.added_time?`+${e.added_time}`:''}′`}
function eventLabel(e){const d=e.details||{},bits=[d.label||e.kind||'Action'];if(e.player_name)bits.push(e.player_name);if(d.own_goal)bits.push('contre son camp');if(d.penalty)bits.push('penalty');return bits.map(esc).join(' · ')}
function timeline(m){if(!(m.events||[]).length)return'<p class="empty">Aucune action détaillée publiée pour ce match.</p>';return `<ol class="timeline">${m.events.map(e=>{const side=e.team_external_id===m.home_team.external_id?m.home_team.short_name:e.team_external_id===m.away_team.external_id?m.away_team.short_name:'';return `<li><span class="minute">${minute(e)}</span><span><span class="event-label">${eventLabel(e)}</span>${side?`<br><span class="tag">${esc(side)}</span>`:''}</span></li>`}).join('')}</ol>`}
function stats(m){const h=m.home_statistics||{},a=m.away_statistics||{},keys=Object.keys(statLabels).filter(k=>Number.isFinite(Number(h[k]))&&Number.isFinite(Number(a[k])));if(!keys.length)return'<p class="empty">Aucune statistique comparative publiée.</p>';return keys.map(k=>{const hv=Number(h[k]),av=Number(a[k]),total=Math.max(0,hv)+Math.max(0,av),pct=total?Math.max(0,Math.min(100,hv/total*100)):50,format=v=>k==='possessionPct'?`${Math.round(v)} %`:String(v);return `<div class="stats-row"><strong>${esc(format(hv))}</strong><div><div class="stat-label">${esc(statLabels[k])}</div><div class="meter"><span style="width:${pct.toFixed(1)}%"></span></div></div><strong>${esc(format(av))}</strong></div>`}).join('')}
function render(data){const m=data.match,c=m.competition||{},home=m.home_team||{},away=m.away_team||{},competition=c.external_id?`<a class="eyebrow" href="/competition?id=${encodeURIComponent(c.external_id)}">${esc(c.name||'Compétition')}</a>`:`<div class="eyebrow">${esc(c.name||'Match')}</div>`,duel=home.external_id&&away.external_id?`<p><a href="/head-to-head?team=${encodeURIComponent(home.external_id)}&opponent=${encodeURIComponent(away.external_id)}">Voir le face-à-face</a></p>`:'';if(data.spoiler_free){app.className='card notice center';app.innerHTML=`${competition}<h1>Direct synchronisé</h1><p>${teamLink(home)} – ${teamLink(away)}</p><p class="muted">Le score, la minute, les actions et les statistiques restent masqués jusqu’à leur livraison selon le retard de ton streaming.</p>${duel}`;return}const scheduled=m.status==='scheduled',score=scheduled?'—':`${m.home_score}–${m.away_score}`,meta=[dateLabel(m.starts_at),m.venue,stage(m),decision[m.decided_by]].filter(Boolean).map(esc).join(' · ');app.className='';app.innerHTML=`<section class="card">${competition}<div class="teams">${teamLink(home,'team home')}<div class="score">${esc(score)}</div>${teamLink(away,'team')}</div><div class="center"><span class="status ${m.status==='live'?'live':''}">${esc(labels[m.status]||m.status)}${m.clock?` · ${esc(m.clock)}`:''}</span><p class="muted">${meta}</p>${duel}</div></section><section class="card"><h2 class="section-title">Chronologie</h2>${timeline(m)}</section><section class="card"><h2 class="section-title">Statistiques</h2>${stats(m)}</section>`}
async function load(){const id=new URLSearchParams(location.search).get('id')||'';if(!id){app.innerHTML='<h1>Match introuvable</h1><p class="muted">Aucun identifiant n’a été fourni.</p>';return}try{const r=await fetch('/api/v1/match?id='+encodeURIComponent(id),{cache:'no-store'}),d=await r.json();if(!r.ok)throw new Error(d.error||'Match indisponible');render(d)}catch(e){app.innerHTML=`<h1>Match indisponible</h1><p class="muted">${esc(e.message)}</p>`}}load();setInterval(load,2000);
</script></body></html>"""


COMPETITION_PAGE = r"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>butbutbut — Compétition</title><style>
*{box-sizing:border-box}body{margin:0;background:#070b14;color:#f8fafc;font:16px/1.45 system-ui,sans-serif}main{max-width:1040px;margin:auto;padding:28px 18px 80px}a{color:#fbca3e;text-decoration:none}.back{display:inline-block;margin-bottom:24px}.card{background:#111827;border:1px solid #273449;border-radius:22px;padding:clamp(17px,3vw,28px);margin:16px 0}header{display:flex;align-items:end;justify-content:space-between;gap:18px;flex-wrap:wrap}h1{margin:0;font-size:clamp(2rem,6vw,4rem);letter-spacing:-.05em}h2{margin:0 0 16px}.muted{color:#94a3b8}.eyebrow{color:#fbca3e;text-transform:uppercase;letter-spacing:.12em;font-size:.76rem;font-weight:800}select{background:#1f2937;color:#f8fafc;border:1px solid #39475f;border-radius:999px;padding:10px 15px;font:inherit}.groups{display:grid;grid-template-columns:repeat(auto-fit,minmax(310px,1fr));gap:16px}.group{overflow:auto}.group h3,.round h3{margin:0 0 12px}table{width:100%;border-collapse:collapse;font-size:.88rem}th,td{padding:8px 6px;border-top:1px solid #263149;text-align:right;font-variant-numeric:tabular-nums}th:first-child,td:first-child{text-align:left}.rank{color:#fbca3e;font-weight:800}.round{margin-top:24px}.match{display:grid;grid-template-columns:105px 1fr auto 1fr;gap:12px;align-items:center;color:inherit;padding:12px 4px;border-top:1px solid #263149}.match:hover{background:#172033}.home{text-align:right}.score{font-weight:850;font-variant-numeric:tabular-nums}.date{color:#94a3b8;font-size:.8rem}.live{color:#fca5a5}.empty{color:#64748b}@media(max-width:620px){.match{grid-template-columns:1fr auto 1fr}.date{grid-column:1/-1}.groups{grid-template-columns:1fr}}</style></head><body><main><a class="back" href="/">← Retour au compagnon</a><div id="app" class="card"><span class="muted">Chargement de la compétition…</span></div></main><script>
const app=document.getElementById('app'),esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),labels={scheduled:'À venir',live:'En direct',finished:'Terminé',postponed:'Reporté',cancelled:'Annulé'};
function val(v){return v==null?'—':esc(v)}function dateLabel(v){if(!v)return'';const d=new Date(v);return Number.isNaN(d.getTime())?'':d.toLocaleString('fr-FR',{dateStyle:'short',timeStyle:'short'})}
function tables(rows){if(!rows.length)return'<p class="empty">Aucun classement officiel publié pour cette édition.</p>';return `<div class="groups">${rows.map(g=>`<section class="card group"><h3>${esc(g.group_name||g.phase_name||'Classement')}</h3><table><thead><tr><th>Équipe</th><th>J</th><th>G</th><th>N</th><th>P</th><th>+/-</th><th>Pts</th></tr></thead><tbody>${(g.rows||[]).map(r=>`<tr><td><span class="rank">${val(r.rank)}</span> ${esc(r.team_name)}</td><td>${val(r.played)}</td><td>${val(r.won)}</td><td>${val(r.drawn)}</td><td>${val(r.lost)}</td><td>${val(r.goal_difference)}</td><td><strong>${val(r.points)}</strong></td></tr>`).join('')}</tbody></table></section>`).join('')}</div>`}
function matchRow(m){const h=m.home_team||{},a=m.away_team||{},scheduled=m.status==='scheduled',score=m.spoiler_free?'Masqué':scheduled?'–':`${m.home_score}–${m.away_score}`,status=m.spoiler_free?'Direct synchronisé':labels[m.status]||m.status,match=`/match?id=${encodeURIComponent(m.external_id)}`;return `<div class="match"><a class="date" href="${match}">${esc(dateLabel(m.starts_at))}<br>${esc(status)}</a><a class="home" href="/team?id=${encodeURIComponent(h.external_id)}">${esc(h.short_name||h.name)}</a><a class="score ${m.status==='live'?'live':''}" href="${match}">${esc(score)}</a><a href="/team?id=${encodeURIComponent(a.external_id)}">${esc(a.short_name||a.name)}</a></div>`}
function fixtures(matches){if(!matches.length)return'<p class="empty">Aucune rencontre enregistrée pour cette édition.</p>';const groups=[];for(const m of matches){const parts=[m.phase_name,m.group_name,m.round_name].filter(Boolean),label=[...new Set(parts)].join(' · ')||'Rencontres';let group=groups.find(g=>g.label===label);if(!group){group={label,matches:[]};groups.push(group)}group.matches.push(m)}return groups.map(g=>`<section class="round"><h3>${esc(g.label)}</h3>${g.matches.map(matchRow).join('')}</section>`).join('')}
function render(d){const c=d.competition||{},e=d.edition||{},options=(d.editions||[]).map(x=>`<option value="${esc(x.external_id)}" ${x.external_id===e.external_id?'selected':''}>${esc(x.name)} · ${x.match_count} match(s)</option>`).join('');app.className='';app.innerHTML=`<section class="card"><header><div><div class="eyebrow">Compétition</div><h1>${esc(c.name||'Compétition')}</h1><p class="muted">${esc(e.name||'Aucune édition')}</p></div>${options?`<label>Édition<br><select id="edition">${options}</select></label>`:''}</header></section><section><h2>Classements</h2>${tables(d.standings||[])}</section><section class="card"><h2>Rencontres</h2>${fixtures(d.matches||[])}</section>`;const select=document.getElementById('edition');if(select)select.onchange=()=>{const url=new URL(location.href);url.searchParams.set('edition',select.value);history.replaceState(null,'',url);load()}}
async function load(){const p=new URLSearchParams(location.search),id=p.get('id')||'',edition=p.get('edition');if(!id){app.innerHTML='<h1>Compétition introuvable</h1>';return}let url='/api/v1/competition?id='+encodeURIComponent(id);if(edition!==null)url+='&edition='+encodeURIComponent(edition);try{const r=await fetch(url,{cache:'no-store'}),d=await r.json();if(!r.ok)throw new Error(d.error||'Compétition indisponible');render(d)}catch(e){app.innerHTML=`<h1>Compétition indisponible</h1><p class="muted">${esc(e.message)}</p>`}}load();setInterval(load,10000);
</script></body></html>"""


TEAM_PAGE = r"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>butbutbut — Équipe</title><style>
*{box-sizing:border-box}body{margin:0;background:#070b14;color:#f8fafc;font:16px/1.45 system-ui,sans-serif}main{max-width:920px;margin:auto;padding:28px 18px 80px}a{color:#fbca3e;text-decoration:none}.back{display:inline-block;margin-bottom:24px}.card{background:#111827;border:1px solid #273449;border-radius:22px;padding:clamp(17px,3vw,28px);margin:16px 0}header{display:flex;align-items:center;gap:20px;flex-wrap:wrap}h1{margin:0;font-size:clamp(2rem,7vw,4.5rem);letter-spacing:-.05em}.badge{display:grid;place-items:center;width:72px;height:72px;border-radius:22px;background:#fbca3e;color:#111827;font-size:1.35rem;font-weight:950}.eyebrow{color:#fbca3e;text-transform:uppercase;letter-spacing:.12em;font-size:.76rem;font-weight:800}.muted{color:#94a3b8}.record{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-top:24px}.stat{background:#172033;border-radius:14px;padding:12px;text-align:center}.stat strong{display:block;font-size:1.35rem}.stat span{color:#94a3b8;font-size:.74rem}.form,.competitions{display:flex;gap:8px;flex-wrap:wrap;margin-top:18px}.pill,.competition{display:inline-grid;place-items:center;min-width:34px;height:34px;border-radius:999px;font-weight:850}.pill.W{background:#166534}.pill.D{background:#475569}.pill.L{background:#991b1b}.competition{border:1px solid #39475f;padding:0 12px;color:#f8fafc;font-size:.8rem}.match{display:grid;grid-template-columns:112px 1fr auto 1fr;gap:12px;align-items:center;padding:13px 4px;border-top:1px solid #263149}.match:first-of-type{border-top:0}.home{text-align:right}.score{font-weight:850;font-variant-numeric:tabular-nums;color:#f8fafc}.date{color:#94a3b8;font-size:.8rem}.live{color:#fca5a5}.team{color:inherit}.empty{color:#64748b}@media(max-width:600px){.record{grid-template-columns:repeat(3,1fr)}.match{grid-template-columns:1fr auto 1fr}.date{grid-column:1/-1}.badge{width:54px;height:54px;border-radius:16px}}</style></head><body><main><a class="back" href="/">← Retour au compagnon</a><div id="app" class="card"><span class="muted">Chargement de l’équipe…</span></div></main><script>
const app=document.getElementById('app'),esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),labels={scheduled:'À venir',live:'En direct',finished:'Terminé',postponed:'Reporté',cancelled:'Annulé'};
function dateLabel(v){if(!v)return'';const d=new Date(v);return Number.isNaN(d.getTime())?'':d.toLocaleString('fr-FR',{dateStyle:'medium',timeStyle:'short'})}
function matchRow(m,id){const h=m.home_team||{},a=m.away_team||{},scheduled=m.status==='scheduled',score=m.spoiler_free?'Masqué':scheduled?'–':`${m.home_score}–${m.away_score}`,status=m.spoiler_free?'Direct synchronisé':labels[m.status]||m.status,url=`/match?id=${encodeURIComponent(m.external_id)}`,team=t=>t.external_id===id?`<strong>${esc(t.short_name||t.name)}</strong>`:`<a class="team" href="/team?id=${encodeURIComponent(t.external_id)}">${esc(t.short_name||t.name)}</a>`;return `<div class="match"><a class="date" href="${url}">${esc(dateLabel(m.starts_at))}<br>${esc((m.competition||{}).name||'')} · ${esc(status)}</a><span class="home">${team(h)}</span><a class="score ${m.status==='live'?'live':''}" href="${url}">${esc(score)}</a><span>${team(a)}</span></div>`}
function section(title,rows,id,empty){return `<section class="card"><h2>${esc(title)}</h2>${rows.length?rows.map(m=>matchRow(m,id)).join(''):`<p class="empty">${esc(empty)}</p>`}</section>`}
function render(d){const t=d.team||{},r=d.record||{},matches=d.matches||[],live=matches.filter(m=>m.status==='live'),upcoming=matches.filter(m=>['scheduled','postponed'].includes(m.status)),results=matches.filter(m=>['finished','cancelled'].includes(m.status)).slice(-20).reverse(),initials=(t.short_name||t.name||'?').split(/\s+/).map(x=>x[0]).join('').slice(0,3).toUpperCase();app.className='';app.innerHTML=`<section class="card"><header><span class="badge">${esc(initials)}</span><div><div class="eyebrow">Équipe</div><h1>${esc(t.name||'Équipe')}</h1></div></header><div class="record"><div class="stat"><strong>${r.played||0}</strong><span>matchs</span></div><div class="stat"><strong>${r.won||0}</strong><span>victoires</span></div><div class="stat"><strong>${r.drawn||0}</strong><span>nuls</span></div><div class="stat"><strong>${r.lost||0}</strong><span>défaites</span></div><div class="stat"><strong>${r.goals_for||0}–${r.goals_against||0}</strong><span>buts</span></div></div>${(d.form||[]).length?`<div class="form"><span class="muted">Forme</span>${d.form.map(x=>`<span class="pill ${esc(x)}">${esc(x)}</span>`).join('')}</div>`:''}<div class="competitions">${(d.competitions||[]).map(c=>`<a class="competition" href="/competition?id=${encodeURIComponent(c.external_id)}">${esc(c.name)}</a>`).join('')}</div></section>${live.length?section('En direct',live,t.external_id,''):''}${section('À venir',upcoming,t.external_id,'Aucun match à venir enregistré.')}${section('Derniers résultats',results,t.external_id,'Aucun résultat enregistré.')}`}
async function load(){const id=new URLSearchParams(location.search).get('id')||'';if(!id){app.innerHTML='<h1>Équipe introuvable</h1>';return}try{const r=await fetch('/api/v1/team?id='+encodeURIComponent(id),{cache:'no-store'}),d=await r.json();if(!r.ok)throw new Error(d.error||'Équipe indisponible');render(d)}catch(e){app.innerHTML=`<h1>Équipe indisponible</h1><p class="muted">${esc(e.message)}</p>`}}load();setInterval(load,10000);
</script></body></html>"""


HEAD_TO_HEAD_PAGE = r"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>butbutbut — Face-à-face</title><style>
*{box-sizing:border-box}body{margin:0;background:#070b14;color:#f8fafc;font:16px/1.45 system-ui,sans-serif}main{max-width:920px;margin:auto;padding:28px 18px 80px}a{color:#fbca3e;text-decoration:none}.back{display:inline-block;margin-bottom:24px}.card{background:#111827;border:1px solid #273449;border-radius:22px;padding:clamp(17px,3vw,28px);margin:16px 0}.eyebrow{color:#fbca3e;text-transform:uppercase;letter-spacing:.12em;font-size:.76rem;font-weight:800;text-align:center}.versus{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:18px;margin:24px 0;text-align:center}.team{color:#f8fafc;font-size:clamp(1.2rem,5vw,2.4rem);font-weight:900}.vs{color:#64748b;font-weight:900}.record{display:grid;grid-template-columns:1fr 1fr 1fr;gap:9px}.stat{background:#172033;border-radius:14px;padding:14px;text-align:center}.stat strong{display:block;font-size:1.55rem}.stat span,.muted{color:#94a3b8;font-size:.8rem}.competitions{display:flex;justify-content:center;gap:8px;flex-wrap:wrap;margin-top:18px}.competition{border:1px solid #39475f;border-radius:999px;padding:7px 12px;color:#f8fafc;font-size:.8rem}.match{display:grid;grid-template-columns:112px 1fr auto 1fr;gap:12px;align-items:center;padding:13px 4px;border-top:1px solid #263149}.match:first-of-type{border-top:0}.home{text-align:right}.score{font-weight:850;font-variant-numeric:tabular-nums;color:#f8fafc}.date{color:#94a3b8;font-size:.8rem}.live{color:#fca5a5}.empty{color:#64748b}@media(max-width:600px){.match{grid-template-columns:1fr auto 1fr}.date{grid-column:1/-1}.record{gap:6px}.stat{padding:10px 5px}}</style></head><body><main><a class="back" href="/">← Retour au compagnon</a><div id="app" class="card"><span class="muted">Chargement du face-à-face…</span></div></main><script>
const app=document.getElementById('app'),esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),labels={scheduled:'À venir',live:'En direct',finished:'Terminé',postponed:'Reporté',cancelled:'Annulé'};
function dateLabel(v){if(!v)return'';const d=new Date(v);return Number.isNaN(d.getTime())?'':d.toLocaleString('fr-FR',{dateStyle:'medium',timeStyle:'short'})}
function matchRow(m){const h=m.home_team||{},a=m.away_team||{},scheduled=m.status==='scheduled',score=m.spoiler_free?'Masqué':scheduled?'–':`${m.home_score}–${m.away_score}`,status=m.spoiler_free?'Direct synchronisé':labels[m.status]||m.status,url=`/match?id=${encodeURIComponent(m.external_id)}`;return `<div class="match"><a class="date" href="${url}">${esc(dateLabel(m.starts_at))}<br>${esc((m.competition||{}).name||'')} · ${esc(status)}</a><a class="home" href="/team?id=${encodeURIComponent(h.external_id)}">${esc(h.short_name||h.name)}</a><a class="score ${m.status==='live'?'live':''}" href="${url}">${esc(score)}</a><a href="/team?id=${encodeURIComponent(a.external_id)}">${esc(a.short_name||a.name)}</a></div>`}
function render(d){const a=d.first_team||{},b=d.second_team||{},r=d.record||{},rows=(d.matches||[]).slice(-12).reverse();app.className='';app.innerHTML=`<section class="card"><div class="eyebrow">Face-à-face</div><div class="versus"><a class="team" href="/team?id=${encodeURIComponent(a.external_id)}">${esc(a.name||'Équipe')}</a><span class="vs">VS</span><a class="team" href="/team?id=${encodeURIComponent(b.external_id)}">${esc(b.name||'Équipe')}</a></div><div class="record"><div class="stat"><strong>${r.first_wins||0}</strong><span>victoires ${esc(a.short_name||a.name||'')}</span></div><div class="stat"><strong>${r.draws||0}</strong><span>nuls</span></div><div class="stat"><strong>${r.second_wins||0}</strong><span>victoires ${esc(b.short_name||b.name||'')}</span></div></div><p class="muted" style="text-align:center">${r.played||0} match(s) terminé(s) · ${r.first_goals||0}–${r.second_goals||0} buts</p><div class="competitions">${(d.competitions||[]).map(c=>`<a class="competition" href="/competition?id=${encodeURIComponent(c.external_id)}">${esc(c.name)}</a>`).join('')}</div></section><section class="card"><h2>Confrontations</h2>${rows.length?rows.map(matchRow).join(''):'<p class="empty">Aucune confrontation enregistrée.</p>'}</section>`}
async function load(){const p=new URLSearchParams(location.search),team=p.get('team')||'',opponent=p.get('opponent')||'';if(!team||!opponent){app.innerHTML='<h1>Face-à-face introuvable</h1>';return}try{const r=await fetch(`/api/v1/head-to-head?team=${encodeURIComponent(team)}&opponent=${encodeURIComponent(opponent)}`,{cache:'no-store'}),d=await r.json();if(!r.ok)throw new Error(d.error||'Face-à-face indisponible');render(d)}catch(e){app.innerHTML=`<h1>Face-à-face indisponible</h1><p class="muted">${esc(e.message)}</p>`}}load();setInterval(load,10000);
</script></body></html>"""


def match_center_payload(match, current_state=None):
    """Forme publique d'un Match Center, avec masque du direct synchronise."""
    snapshot = current_state or {}
    try:
        delayed = float(snapshot.get("stream_delay") or 0) > 0
    except (TypeError, ValueError):
        delayed = False
    redacted = delayed and match.get("status") == "live"
    if redacted:
        visible = {key: match.get(key) for key in (
            "external_id", "competition", "home_team", "away_team",
            "starts_at", "status",
        )}
    else:
        visible = match
    return {
        "schema_version": site_feed.SCHEMA_VERSION,
        "generated_at": site_feed.utc_now(),
        "spoiler_free": redacted,
        "match": visible,
    }


def competition_center_payload(detail, current_state=None):
    """Vue d'une edition, dont chaque direct respecte le retard du flux."""
    payload = dict(detail)
    matches = []
    for match in detail.get("matches", ()):
        public = match_center_payload(match, current_state=current_state)
        row = dict(public["match"])
        row["spoiler_free"] = public["spoiler_free"]
        matches.append(row)
    payload["matches"] = matches
    payload["schema_version"] = site_feed.SCHEMA_VERSION
    payload["generated_at"] = site_feed.utc_now()
    return payload


def team_center_payload(detail, current_state=None):
    """Vue d'une equipe dont les directs respectent le retard du flux."""
    payload = dict(detail)
    matches = []
    for match in detail.get("matches", ()):
        public = match_center_payload(match, current_state=current_state)
        row = dict(public["match"])
        row["spoiler_free"] = public["spoiler_free"]
        matches.append(row)
    payload["matches"] = matches
    payload["schema_version"] = site_feed.SCHEMA_VERSION
    payload["generated_at"] = site_feed.utc_now()
    return payload


def head_to_head_payload(detail, current_state=None):
    """Face-a-face local avec le meme masque live que les autres vues."""
    payload = dict(detail)
    matches = []
    for match in detail.get("matches", ()):
        public = match_center_payload(match, current_state=current_state)
        row = dict(public["match"])
        row["spoiler_free"] = public["spoiler_free"]
        matches.append(row)
    payload["matches"] = matches
    payload["schema_version"] = site_feed.SCHEMA_VERSION
    payload["generated_at"] = site_feed.utc_now()
    return payload


def handler(state_path, control_path, stories_path=None, feed_path=None,
            followed=()):
    state_path, control_path = Path(state_path), Path(control_path)
    stories_path = Path(stories_path) if stories_path else None
    feed_path = Path(feed_path) if feed_path else state_path.with_name("site-feed.sqlite3")

    class Handler(BaseHTTPRequestHandler):
        def _json(self, payload, status=200):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _html(self, page, status=200):
            body = page.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path == "/api/state":
                data = state.read(state_path) or {}
                if stories_path is not None:
                    data["souvenirs"] = souvenir.read(stories_path)[-10:]
                return self._json(data)
            if parsed.path == "/api/v1/competition":
                params = parse_qs(parsed.query, keep_blank_values=True)
                unknown = set(params) - {"id", "edition"}
                chosen = params.get("id") or []
                editions = params.get("edition")
                if (unknown or len(chosen) != 1 or not chosen[0].strip()
                        or editions is not None and len(editions) != 1):
                    return self._json(
                        {"error": "identifiant de competition invalide"}, 400)
                try:
                    detail = site_feed.Store(feed_path).competition_detail(
                        chosen[0], edition_id=(editions[0] if editions else None))
                except site_feed.NotFound as exc:
                    return self._json({"error": str(exc)}, 404)
                except (OSError, sqlite3.Error, TypeError, ValueError):
                    return self._json(
                        {"error": "explorateur de competition indisponible"}, 503)
                if detail is None:
                    return self._json({"error": "competition introuvable"}, 404)
                return self._json(competition_center_payload(
                    detail, current_state=state.read(state_path)))
            if parsed.path == "/api/v1/team":
                params = parse_qs(parsed.query, keep_blank_values=True)
                unknown = set(params) - {"id"}
                chosen = params.get("id") or []
                if unknown or len(chosen) != 1 or not chosen[0].strip():
                    return self._json(
                        {"error": "identifiant d'equipe invalide"}, 400)
                try:
                    detail = site_feed.Store(feed_path).team_detail(chosen[0])
                except (OSError, sqlite3.Error, TypeError, ValueError):
                    return self._json(
                        {"error": "explorateur d'equipe indisponible"}, 503)
                if detail is None:
                    return self._json({"error": "equipe introuvable"}, 404)
                return self._json(team_center_payload(
                    detail, current_state=state.read(state_path)))
            if parsed.path == "/api/v1/head-to-head":
                params = parse_qs(parsed.query, keep_blank_values=True)
                unknown = set(params) - {"team", "opponent"}
                teams = params.get("team") or []
                opponents = params.get("opponent") or []
                invalid = (unknown or len(teams) != 1 or len(opponents) != 1
                           or not teams[0].strip() or not opponents[0].strip()
                           or teams[0].strip() == opponents[0].strip())
                if invalid:
                    return self._json(
                        {"error": "equipes du face-a-face invalides"}, 400)
                try:
                    detail = site_feed.Store(feed_path).head_to_head(
                        teams[0], opponents[0])
                except (OSError, sqlite3.Error, TypeError, ValueError):
                    return self._json(
                        {"error": "face-a-face indisponible"}, 503)
                if detail is None:
                    return self._json(
                        {"error": "face-a-face introuvable"}, 404)
                return self._json(head_to_head_payload(
                    detail, current_state=state.read(state_path)))
            if parsed.path == "/api/v1/match":
                params = parse_qs(parsed.query, keep_blank_values=True)
                unknown = set(params) - {"id"}
                chosen = params.get("id") or []
                if unknown or len(chosen) != 1 or not chosen[0].strip():
                    return self._json({"error": "identifiant de match invalide"}, 400)
                try:
                    match = site_feed.Store(feed_path).get_match(chosen[0])
                except (OSError, sqlite3.Error, TypeError, ValueError):
                    return self._json({"error": "Match Center indisponible"}, 503)
                if match is None:
                    return self._json({"error": "match introuvable"}, 404)
                return self._json(match_center_payload(
                    match, current_state=state.read(state_path)))
            if parsed.path == "/api/v1/site-feed":
                try:
                    params = parse_qs(parsed.query, keep_blank_values=True)
                    payload = site_feed.Store(feed_path).feed(
                        params, followed=followed,
                        current_state=state.read(state_path))
                except site_feed.InvalidQuery as exc:
                    return self._json({"error": str(exc)}, 400)
                except (OSError, sqlite3.Error, TypeError, ValueError):
                    return self._json({"error": "site-feed indisponible"}, 503)
                return self._json(payload)
            if parsed.path == "/souvenir":
                chosen = (parse_qs(parsed.query).get("id") or [""])[0]
                stories = souvenir.read(stories_path) if stories_path else []
                story = next((row for row in reversed(stories)
                              if str(row.get("id")) == chosen), None)
                if story is None:
                    return self._json({"error": "souvenir introuvable"}, 404)
                return self._html(souvenir.render(story))
            if parsed.path == "/match":
                return self._html(MATCH_PAGE)
            if parsed.path == "/competition":
                return self._html(COMPETITION_PAGE)
            if parsed.path == "/team":
                return self._html(TEAM_PAGE)
            if parsed.path == "/head-to-head":
                return self._html(HEAD_TO_HEAD_PAGE)
            if parsed.path not in ("/", "/index.html"):
                return self._json({"error": "introuvable"}, 404)
            return self._html(PAGE)

        def do_POST(self):
            parsed = urlparse(self.path)
            if parsed.path != "/api/sync":
                return self._json({"error": "introuvable"}, 404)
            data = state.read(state_path) or {}
            try:
                chosen = (parse_qs(parsed.query).get("match") or [""])[0]
                delay = streaming.delay_from_kickoff(data, match=chosen)
                streaming.request(control_path, delay)
            except (streaming.Invalid, OSError) as exc:
                return self._json({"error": str(exc)}, 409)
            return self._json({"delay": delay,
                               "message": "Retard mesure : {:.0f} s".format(delay)})

        def log_message(self, _format, *_args):
            return

    return Handler


def serve(state_path, control_path, bind="", on_ready=None, stories_path=None,
          feed_path=None, followed=()):
    host, port = parse_bind(bind)
    server = ThreadingHTTPServer(
        (host, port), handler(state_path, control_path, stories_path,
                              feed_path=feed_path, followed=followed))
    if on_ready:
        on_ready(host, server.server_address[1])
    try:
        server.serve_forever(poll_interval=0.5)
    finally:
        server.server_close()
