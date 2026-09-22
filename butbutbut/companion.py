"""Ecran compagnon HTTP local, sans dependance ni ressource distante."""

from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

from . import ical, site_feed, souvenir, state, streaming

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
*{box-sizing:border-box}body{margin:0;background:#070b14;color:#f8fafc;font:16px/1.45 system-ui,sans-serif}main{max-width:980px;margin:auto;padding:32px 18px 80px}header{display:flex;justify-content:space-between;align-items:center;gap:16px;margin-bottom:28px}.controls,.story-actions{display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end}h1{margin:0;font-size:clamp(1.6rem,5vw,3rem);letter-spacing:-.04em}.live{color:#fbca3e}.status{color:#94a3b8}.panel{background:#111827;border:1px solid #273449;border-radius:22px;padding:20px;margin:16px 0}.agenda-title{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}.agenda-actions{display:flex;gap:8px;align-items:center}.favorites-label{margin:0 0 8px;color:#94a3b8;font-size:.78rem;text-transform:uppercase;letter-spacing:.08em}.favorites{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px}.favorite{display:flex;align-items:center;border:1px solid #39475f;border-radius:999px;background:#172033}.favorite a{padding:7px 4px 7px 12px;color:#f8fafc;text-decoration:none}.favorite button{padding:7px 11px;background:transparent;color:#94a3b8}.searchbox input{width:100%;border:1px solid #39475f;border-radius:14px;padding:14px 16px;background:#0b1220;color:#f8fafc;font:inherit;outline:none}.searchbox input:focus{border-color:#fbca3e}.search-results{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:8px;margin-top:12px}.search-result{display:flex;align-items:center;gap:6px;border-radius:12px;background:#172033}.search-result:hover{background:#202b40}.search-link{display:flex;justify-content:space-between;align-items:center;gap:12px;min-width:0;flex:1;padding:12px;color:inherit;text-decoration:none}.search-link small{display:block;color:#94a3b8}.favorite-toggle{align-self:stretch;border-radius:0 12px 12px 0;padding:8px 14px;background:transparent;color:#fbca3e;font-size:1.2rem}.favorite-toggle:hover{background:#29344a}.search-type{color:#fbca3e;text-transform:uppercase;letter-spacing:.08em;font-size:.7rem;font-weight:850}.match,.event,.story{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:14px;padding:14px 0;border-top:1px solid #263149}.panel>:nth-child(2){border-top:0}.match-link{color:inherit;text-decoration:none;border-radius:12px}.match-link:hover{background:#172033}.home{text-align:right}.score{font-size:1.55rem;font-weight:800;font-variant-numeric:tabular-nums}.meta{grid-column:1/-1;text-align:center;color:#94a3b8;font-size:.85rem}.event{grid-template-columns:90px 1fr auto}.event .home{text-align:left}.context{color:#fbca3e;text-transform:uppercase;font-size:.75rem;letter-spacing:.1em}.story{grid-template-columns:1fr auto 1fr}.story-actions{grid-column:1/-1;justify-self:center}.story-link{border:1px solid #39475f;border-radius:999px;padding:6px 12px;text-decoration:none;font-size:.76rem;font-weight:750}.story-link:hover{background:#1f2937}.muted{color:#94a3b8}button,select{border:0;border-radius:999px;padding:11px 16px;font:inherit}select{background:#1f2937;color:#f8fafc}button{background:#fbca3e;color:#111827;font-weight:800;cursor:pointer}.agenda-actions button{border:1px solid #39475f;background:transparent;color:#fbca3e;padding:6px 12px;font-size:.76rem}.agenda-actions button[aria-pressed="true"]{background:#fbca3e;color:#111827}button:disabled{opacity:.45;cursor:not-allowed}.hidden{display:none}.empty{color:#64748b;padding:12px 0}a{color:#fbca3e}footer{margin-top:30px;color:#64748b;font-size:.8rem}@media(max-width:520px){.agenda-actions{width:100%}}</style></head><body><main><header><div><h1>butbutbut <span class="live">●</span></h1><div id="status" class="status">Connexion…</div></div><div class="controls"><select id="kickoff" class="hidden"></select><button id="sync">Je vois le coup d’envoi</button></div></header><section class="panel"><h2>Explorer</h2><div class="favorites-label">Mes favoris</div><div id="favorites" class="favorites"></div><div class="searchbox"><input id="search" type="search" autocomplete="off" placeholder="Une équipe ou une compétition…" aria-label="Rechercher une équipe ou une compétition"></div><div id="search-results" class="search-results"><div class="empty">Saisis au moins deux caractères.</div></div></section><section id="favorite-agenda-panel" class="panel hidden"><h2 class="agenda-title"><span>À suivre</span><span class="agenda-actions"><button id="favorite-alerts" type="button" aria-pressed="false">Activer les alertes</button><a id="favorite-calendar" class="story-link" href="#" download="butbutbut-favoris.ics" aria-label="Télécharger le calendrier des favoris">Calendrier .ics</a></span></h2><div id="favorite-agenda"></div></section><section id="delay" class="panel hidden"></section><section class="panel"><h2>En direct</h2><div id="matches"></div></section><section class="panel"><h2>Dernières alertes</h2><div id="events"></div></section><section class="panel"><h2>Souvenirs</h2><div id="stories"></div></section><footer>Tout reste sur cette machine. Aucune police, image ou bibliothèque distante n’est chargée par cette page.</footer></main><script>
const $=id=>document.getElementById(id), esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function empty(text){return `<div class="empty">${esc(text)}</div>`}function match(m){return `<a class="match match-link" href="/match?id=${encodeURIComponent(m.id)}"><span class="home">${esc(m.home)}</span><span class="score">${esc(m.home_score)}–${esc(m.away_score)}</span><span>${esc(m.away)}</span><span class="meta">${esc(m.league)} · ${esc(m.clock)} · Ouvrir le Match Center</span></a>`}function favoriteMatch(m){const h=m.home_team||{},a=m.away_team||{},waiting=['scheduled','postponed'].includes(m.status),score=m.spoiler_free?'Masqué':waiting?'–':`${m.home_score}–${m.away_score}`,labels={live:'En direct',scheduled:'À venir',postponed:'Reporté'},date=m.starts_at?new Date(m.starts_at).toLocaleString('fr-FR',{dateStyle:'medium',timeStyle:'short'}):'';return `<a class="match match-link" href="/match?id=${encodeURIComponent(m.external_id)}"><span class="home">${esc(h.short_name||h.name)}</span><span class="score">${esc(score)}</span><span>${esc(a.short_name||a.name)}</span><span class="meta">${esc((m.competition||{}).name||'')} · ${esc(labels[m.status]||m.status)}${date?' · '+esc(date):''}</span></a>`}function event(e){const body=`<span class="context">${esc(e.context_label||e.title)}</span><span class="home">${esc(e.score_line)}<br><span class="muted">${esc(e.detail)}</span></span><span>${esc(e.minute)}</span>`;return e.match_id?`<a class="event match-link" href="/match?id=${encodeURIComponent(e.match_id)}">${body}</a>`:`<div class="event">${body}</div>`}function story(s){return `<div class="story"><span class="home">${esc(s.home)}</span><span class="score">${esc(s.home_score)}–${esc(s.away_score)}</span><span>${esc(s.away)}</span><span class="meta">${esc(s.league)} · ${esc(s.goals?.length||0)} action(s) de score</span><span class="story-actions"><a class="story-link" href="/match?id=${encodeURIComponent(s.id)}">Match Center</a><a class="story-link" href="/souvenir?id=${encodeURIComponent(s.id)}" target="_blank" rel="noopener">Ouvrir et enregistrer la carte</a></span></div>`}
const favoriteKey='butbutbut:favorites:v1';let favorites=[],searchRows=[];try{const saved=JSON.parse(localStorage.getItem(favoriteKey)||'[]');if(Array.isArray(saved))favorites=saved.filter(x=>x&&['team','competition'].includes(x.type)&&x.external_id&&x.name).slice(0,20)}catch(_e){}function favoriteId(r){return `${r.type}:${r.external_id}`}function favoriteHref(r){return r.type==='team'?`/team?id=${encodeURIComponent(r.external_id)}`:`/competition?id=${encodeURIComponent(r.external_id)}`}function isFavorite(r){return favorites.some(x=>favoriteId(x)===favoriteId(r))}function saveFavorites(){try{localStorage.setItem(favoriteKey,JSON.stringify(favorites))}catch(_e){}renderFavorites();refreshFavoriteMatches()}function renderFavorites(){$('favorites').innerHTML=favorites.length?favorites.map(r=>`<span class="favorite"><a href="${favoriteHref(r)}">${esc(r.name)}</a><button type="button" data-favorite-remove="${esc(favoriteId(r))}" aria-label="Retirer ${esc(r.name)} des favoris">×</button></span>`).join(''):empty('Aucun favori pour le moment.')}function searchResult(r){const team=r.type==='team',detail=team?(r.short_name&&r.short_name!==r.name?r.short_name:'Fiche équipe'):(r.country_code||'Fiche compétition'),active=isFavorite(r),payload=encodeURIComponent(JSON.stringify({type:r.type,external_id:r.external_id,name:r.name,short_name:r.short_name||'',country_code:r.country_code||''}));return `<div class="search-result"><a class="search-link" href="${favoriteHref(r)}"><span><strong>${esc(r.name)}</strong><small>${esc(detail)}</small></span><span class="search-type">${team?'Équipe':'Compétition'}</span></a><button type="button" class="favorite-toggle" data-favorite="${payload}" aria-label="${active?'Retirer':'Ajouter'} ${esc(r.name)} ${active?'des':'aux'} favoris" aria-pressed="${active}">${active?'★':'☆'}</button></div>`}function renderSearch(){$('search-results').innerHTML=searchRows.length?searchRows.map(searchResult).join(''):empty($('search').value.trim().length<2?'Saisis au moins deux caractères.':'Aucun résultat local.')}function toggleFavorite(item){const id=favoriteId(item),index=favorites.findIndex(x=>favoriteId(x)===id);if(index<0&&favorites.length<20)favorites.push(item);else if(index>=0)favorites.splice(index,1);saveFavorites();renderSearch()}$('search-results').onclick=e=>{const button=e.target.closest('[data-favorite]');if(!button)return;toggleFavorite(JSON.parse(decodeURIComponent(button.dataset.favorite)))};$('favorites').onclick=e=>{const button=e.target.closest('[data-favorite-remove]');if(!button)return;favorites=favorites.filter(x=>favoriteId(x)!==button.dataset.favoriteRemove);saveFavorites();renderSearch()};
let searchTimer=0,searchSequence=0;$('search').oninput=()=>{clearTimeout(searchTimer);const q=$('search').value.trim(),sequence=++searchSequence;if(q.length<2){searchRows=[];renderSearch();return}searchTimer=setTimeout(async()=>{try{const r=await fetch('/api/v1/search?q='+encodeURIComponent(q),{cache:'no-store'}),d=await r.json();if(sequence!==searchSequence)return;if(!r.ok)throw new Error(d.error||'Recherche indisponible');searchRows=d.results||[];renderSearch()}catch(e){if(sequence===searchSequence){searchRows=[];$('search-results').innerHTML=empty(e.message)}}},180)};
const favoriteAlertKey='butbutbut:favorite-alerts:v1';let favoriteAlerts=false,favoriteAlertsReady=false,favoriteSnapshots=new Map();try{favoriteAlerts=localStorage.getItem(favoriteAlertKey)==='on'}catch(_e){}function syncFavoriteAlertButton(){const button=$('favorite-alerts'),supported='Notification'in window,granted=supported&&Notification.permission==='granted'&&favoriteAlerts,denied=supported&&Notification.permission==='denied';button.disabled=!supported||denied;button.setAttribute('aria-pressed',String(granted));button.textContent=!supported?'Alertes indisponibles':denied?'Alertes refusées':granted?'Alertes actives':'Activer les alertes'}async function toggleFavoriteAlerts(){if(!('Notification'in window))return;if(favoriteAlerts&&Notification.permission==='granted')favoriteAlerts=false;else{let permission=Notification.permission;if(permission==='default')permission=await Notification.requestPermission();favoriteAlerts=permission==='granted'}try{localStorage.setItem(favoriteAlertKey,favoriteAlerts?'on':'off')}catch(_e){}favoriteAlertsReady=false;syncFavoriteAlertButton()}function favoriteSnapshot(m){return{status:m.status,home_score:m.home_score,away_score:m.away_score,spoiler_free:Boolean(m.spoiler_free)}}function notifyFavorite(title,body,id){try{new Notification(title,{body,tag:`butbutbut-favorite-${id}`})}catch(_e){}}function trackFavoriteAlerts(matches){const next=new Map(matches.map(m=>[String(m.external_id),favoriteSnapshot(m)]));if(!favoriteAlerts||!('Notification'in window)||Notification.permission!=='granted'){favoriteSnapshots=next;favoriteAlertsReady=false;return}if(!favoriteAlertsReady){favoriteSnapshots=next;favoriteAlertsReady=true;return}for(const m of matches){const previous=favoriteSnapshots.get(String(m.external_id));if(!previous||m.spoiler_free||previous.spoiler_free)continue;const home=(m.home_team||{}).short_name||(m.home_team||{}).name||'Domicile',away=(m.away_team||{}).short_name||(m.away_team||{}).name||'Extérieur',competition=(m.competition||{}).name||'Match';if(previous.status!=='live'&&m.status==='live')notifyFavorite(`Coup d’envoi · ${home} – ${away}`,competition,m.external_id);else if(previous.status==='live'&&m.status==='live'&&m.home_score!=null&&m.away_score!=null&&(String(previous.home_score)!==String(m.home_score)||String(previous.away_score)!==String(m.away_score)))notifyFavorite(`Score mis à jour · ${home} – ${away}`,`${m.home_score}–${m.away_score} · ${competition}`,m.external_id)}favoriteSnapshots=next}
const favoriteAgendaViewKey='butbutbut:favorite-agenda-view:v1';
let favoriteSequence=0,favoriteAgendaMatches=[],favoriteAgendaFilter='all',favoriteAgendaSelection='all';
try{
  const view=JSON.parse(localStorage.getItem(favoriteAgendaViewKey)||'{}');
  if(view&&['all','live','upcoming'].includes(view.filter))favoriteAgendaFilter=view.filter;
  if(view&&typeof view.selection==='string'&&view.selection.length<=250&&
     (view.selection==='all'||view.selection.startsWith('team:')||view.selection.startsWith('competition:')))favoriteAgendaSelection=view.selection;
}catch(_e){}
async function refreshFavoriteMatches(){
  const sequence=++favoriteSequence,panel=$('favorite-agenda-panel');
  if(!favorites.length){panel.classList.add('hidden');if(favoriteAgendaSelection!=='all'){favoriteAgendaSelection='all';persistFavoriteAgendaView()}favoriteAgendaMatches=[];$('favorite-agenda').innerHTML='';$('favorite-next').innerHTML='';favoriteSnapshots.clear();favoriteAlertsReady=false;return}
  panel.classList.remove('hidden');
  syncFavoriteAgendaSelection();
  const params=new URLSearchParams({limit:'20'});
  for(const item of favorites)params.append(item.type,item.external_id);
  $('favorite-calendar').href='/api/v1/favorites.ics?'+params.toString();
  try{
    const response=await fetch('/api/v1/favorites?'+params.toString(),{cache:'no-store'}),data=await response.json();
    if(sequence!==favoriteSequence)return;
    if(!response.ok)throw new Error(data.error||'Fil favori indisponible');
    trackFavoriteAlerts(data.matches||[]);
    if(favoriteAgendaSelection==='all')favoriteAgendaMatches=data.matches||[];
    else{
      const item=favorites.find(row=>favoriteId(row)===favoriteAgendaSelection);
      if(!item)return;
      const scoped=new URLSearchParams({limit:'20'});scoped.append(item.type,item.external_id);
      const scopedResponse=await fetch('/api/v1/favorites?'+scoped.toString(),{cache:'no-store'}),scopedData=await scopedResponse.json();
      if(sequence!==favoriteSequence)return;
      if(!scopedResponse.ok)throw new Error(scopedData.error||'Fil favori indisponible');
      favoriteAgendaMatches=scopedData.matches||[];
    }
    renderFavoriteAgenda();
  }catch(error){if(sequence===favoriteSequence){$('favorite-agenda').innerHTML=empty(error.message);$('favorite-next').innerHTML=''}}
}
$('favorite-alerts').onclick=toggleFavoriteAlerts;syncFavoriteAlertButton();renderFavorites();refreshFavoriteMatches();
async function refresh(){try{const r=await fetch('/api/state',{cache:'no-store'}),d=await r.json(),delay=Number(d.stream_delay||0),ks=d.recent_kickoffs||[];$('status').textContent=d.updated_text?`Dernier relevé : ${d.updated_text}`:'Daemon arrêté ou état indisponible';$('sync').disabled=!ks.length;$('kickoff').classList.toggle('hidden',ks.length<2);$('kickoff').innerHTML=ks.slice().reverse().map(k=>`<option value="${esc(k.id)}">${esc(k.home)} – ${esc(k.away)}</option>`).join('');if(delay>0){$('delay').classList.remove('hidden');$('delay').innerHTML=`Flux synchronisé avec ${Math.round(delay)} s de retard. Les scores bruts sont masqués ici.`;$('matches').innerHTML=empty('Le fil synchronisé apparaît dans les alertes ci-dessous.')}else{$('delay').classList.add('hidden');$('matches').innerHTML=(d.matches||[]).map(match).join('')||empty('Aucun match en cours.')} $('events').innerHTML=(d.recent_events||[]).slice().reverse().map(event).join('')||empty('Aucune alerte récente.');$('stories').innerHTML=(d.souvenirs||[]).slice().reverse().map(story).join('')||empty('Aucun match terminé depuis l’installation.')}catch(e){$('status').textContent='Compagnon indisponible';}}$('sync').onclick=async()=>{const id=$('kickoff').value||'';const r=await fetch('/api/sync?match='+encodeURIComponent(id),{method:'POST'}),d=await r.json();alert(d.message||d.error);refresh()};refresh();setInterval(refresh,2000);setInterval(refreshFavoriteMatches,10000);
</script></body></html>"""

FAVORITES_TRANSFER_HTML = """<div class="favorite-transfer" aria-label="Sauvegarde des favoris"><button id="favorite-export" type="button">Exporter les favoris</button><input id="favorite-import-file" type="file" accept=".json,application/json"><label for="favorite-import-file">Importer des favoris</label><span id="favorite-transfer-status" role="status" aria-live="polite"></span></div>"""
FAVORITES_TRANSFER_CSS = """.favorite-transfer{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:0 0 16px}.favorite-transfer button,.favorite-transfer label{border:1px solid #39475f;border-radius:999px;background:#172033;color:#fbca3e;padding:7px 12px;font:inherit;font-size:.8rem;font-weight:750;cursor:pointer}.favorite-transfer button:hover,.favorite-transfer label:hover{background:#29344a}.favorite-transfer input{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}.favorite-transfer input:focus-visible+label{outline:2px solid #fbca3e;outline-offset:2px}.favorite-transfer #favorite-transfer-status:not(:empty){width:100%;color:#cbd5e1;font-size:.82rem}"""
FAVORITES_TRANSFER_SCRIPT = r"""
function decodeFavoriteBundle(text){
  let bundle;
  try{bundle=JSON.parse(text)}catch(_e){throw new Error('Fichier JSON illisible.')}
  if(!bundle||Array.isArray(bundle)||bundle.version!==1||!Array.isArray(bundle.favorites)||bundle.favorites.length>20)throw new Error('Format de favoris non reconnu.');
  const field=(value,optional=false)=>{if(optional&&value==null)return'';if(typeof value!=='string')throw new Error('Favori invalide.');const result=value.trim();if((!optional&&!result)||result.length>200||/[\x00-\x1f\x7f]/.test(result))throw new Error('Favori invalide.');return result};
  const rows=[],seen=new Set();
  for(const row of bundle.favorites){
    if(!row||Array.isArray(row)||!['team','competition'].includes(row.type))throw new Error('Favori invalide.');
    const item={type:row.type,external_id:field(row.external_id),name:field(row.name),short_name:field(row.short_name,true),country_code:field(row.country_code,true)};
    const key=favoriteId(item);if(!seen.has(key)){seen.add(key);rows.push(item)}
  }
  return rows;
}
function favoriteTransferStatus(message){$('favorite-transfer-status').textContent=message}
function exportFavorites(){
  if(!favorites.length){favoriteTransferStatus('Aucun favori à exporter.');return}
  const rows=favorites.map(({type,external_id,name,short_name='',country_code=''})=>({type,external_id,name,short_name,country_code}));
  const blob=new Blob([JSON.stringify({version:1,favorites:rows},null,2)+'\n'],{type:'application/json'});
  const url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download='butbutbut-favoris.json';document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
  favoriteTransferStatus(`${rows.length} favori(s) exporté(s).`);
}
async function importFavorites(file){
  if(!file)return;
  try{
    if(file.size>65536)throw new Error('Fichier trop volumineux (64 Ko maximum).');
    const rows=decodeFavoriteBundle(await file.text()),seen=new Set(favorites.map(favoriteId));
    const added=rows.filter(row=>!seen.has(favoriteId(row)));
    if(favorites.length+added.length>20)throw new Error('La sélection dépasserait 20 favoris.');
    if(!added.length){favoriteTransferStatus('Ces favoris sont déjà présents.');return}
    const merged=favorites.concat(added);
    try{localStorage.setItem(favoriteKey,JSON.stringify(merged))}catch(_e){throw new Error('Stockage local indisponible.')}
    favorites=merged;saveFavorites();renderSearch();favoriteTransferStatus(`${added.length} favori(s) importé(s).`);
  }catch(error){favoriteTransferStatus(error.message||'Import impossible.')}
}
$('favorite-export').onclick=exportFavorites;
$('favorite-import-file').onchange=event=>{const file=event.target.files?.[0];event.target.value='';importFavorites(file)};
window.addEventListener('storage',event=>{
  if(event.key!==favoriteKey)return;
  let rows;try{rows=JSON.parse(event.newValue||'[]')}catch(_e){return}
  if(!Array.isArray(rows))return;
  favorites=rows.filter(row=>row&&['team','competition'].includes(row.type)&&row.external_id&&row.name).slice(0,20);
  renderFavorites();renderSearch();refreshFavoriteMatches();
});
"""
PAGE = PAGE.replace("</style>", FAVORITES_TRANSFER_CSS + "</style>", 1)
PAGE = PAGE.replace('<div id="favorites" class="favorites"></div>',
                    '<div id="favorites" class="favorites"></div>'
                    + FAVORITES_TRANSFER_HTML, 1)
PAGE = PAGE.replace("</script></body></html>",
                    FAVORITES_TRANSFER_SCRIPT + "</script></body></html>", 1)

FAVORITE_AGENDA_HTML = """<div class="agenda-selection-row"><label id="favorite-agenda-selection-label" class="agenda-selection hidden" for="favorite-agenda-selection">Afficher le favori <select id="favorite-agenda-selection"><option value="all">Tous mes favoris</option></select></label><a id="favorite-selection-calendar" class="story-link agenda-selection-calendar hidden" href="#" download="butbutbut-favoris.ics">Calendrier de ce favori .ics</a></div><div id="favorite-next" class="agenda-next" role="status" aria-live="polite"></div><div id="favorite-agenda-filters" class="agenda-filters" role="group" aria-label="Filtrer les matchs favoris"><button type="button" data-agenda-filter="all" aria-pressed="true">Tous</button><button type="button" data-agenda-filter="live" aria-pressed="false">En direct</button><button type="button" data-agenda-filter="upcoming" aria-pressed="false">À venir</button></div>"""
FAVORITE_AGENDA_CSS = """.agenda-selection-row{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;margin:4px 0 12px}.agenda-selection{display:flex;align-items:center;gap:10px;flex-wrap:wrap;color:#94a3b8;font-size:.82rem}.agenda-selection.hidden,.agenda-selection-calendar.hidden{display:none}.agenda-selection select{max-width:100%;border:1px solid #39475f;padding:7px 11px;background:#172033;color:#f8fafc;font-size:.82rem}.agenda-selection-calendar{white-space:nowrap}.agenda-next{background:#172033;border:1px solid #39475f;border-radius:12px;padding:10px 12px;margin:0 0 12px;font-size:.82rem}.agenda-next:empty{display:none}.agenda-next strong{color:#fbca3e;margin-right:8px}.agenda-next a{color:#f8fafc;text-decoration:none}.agenda-next a:hover{text-decoration:underline}.agenda-filters{display:flex;gap:7px;flex-wrap:wrap;margin:4px 0 12px}.agenda-filters button{border:1px solid #39475f;background:#172033;color:#cbd5e1;padding:7px 11px;font-size:.78rem}.agenda-filters button[aria-pressed="true"]{background:#fbca3e;border-color:#fbca3e;color:#111827}.agenda-group{margin-top:16px}.agenda-group h3{margin:0;padding:8px 0;color:#fbca3e;font-size:.82rem;letter-spacing:.06em;text-transform:uppercase}.agenda-group .match:first-of-type{border-top:0}"""
FAVORITE_AGENDA_SCRIPT = r"""
function persistFavoriteAgendaView(){
  try{localStorage.setItem(favoriteAgendaViewKey,JSON.stringify({filter:favoriteAgendaFilter,selection:favoriteAgendaSelection}))}catch(_e){}
}
function favoriteAgendaIncludes(match,selection){
  if(selection==='all')return true;
  if(selection.startsWith('competition:'))return String((match.competition||{}).external_id||'')===selection.slice(12);
  if(selection.startsWith('team:'))return [match.home_team,match.away_team].some(team=>String((team||{}).external_id||'')===selection.slice(5));
  return false;
}
function syncFavoriteAgendaSelection(){
  const select=$('favorite-agenda-selection'),label=$('favorite-agenda-selection-label'),calendar=$('favorite-selection-calendar');
  const previous=favoriteAgendaSelection;
  if(favorites.length<2)favoriteAgendaSelection='all';
  if(favoriteAgendaSelection!=='all'&&!favorites.some(item=>favoriteId(item)===favoriteAgendaSelection))favoriteAgendaSelection='all';
  if(previous!==favoriteAgendaSelection)persistFavoriteAgendaView();
  const signature=JSON.stringify(favorites.map(item=>[favoriteId(item),item.name]));
  if(select.dataset.options!==signature){
    select.innerHTML='<option value="all">Tous mes favoris</option>'+favorites.map(item=>`<option value="${esc(favoriteId(item))}">${item.type==='team'?'Équipe':'Compétition'} · ${esc(item.name)}</option>`).join('');
    select.dataset.options=signature;
  }
  select.value=favoriteAgendaSelection;
  label.classList.toggle('hidden',favorites.length<2);
  const item=favorites.find(row=>favoriteId(row)===favoriteAgendaSelection);
  calendar.classList.toggle('hidden',!item);
  if(item){
    const params=new URLSearchParams({limit:'20'});params.append(item.type,item.external_id);
    calendar.href='/api/v1/favorites.ics?'+params.toString();
    calendar.setAttribute('aria-label',`Télécharger le calendrier de ${item.name}`);
  }else calendar.href='#';
}
function favoriteAgendaGroup(match,now=new Date()){
  if(match.status==='live')return{key:'live',label:'En direct',order:0,sort:0};
  if(match.status==='postponed')return{key:'postponed',label:'Reportés',order:2,sort:0};
  const start=new Date(match.starts_at||'');
  if(Number.isNaN(start.getTime()))return{key:'unknown',label:'Date à confirmer',order:3,sort:0};
  const stamp=date=>Date.UTC(date.getFullYear(),date.getMonth(),date.getDate());
  const day=stamp(start),distance=Math.round((day-stamp(now))/86400000);
  const key=`${start.getFullYear()}-${String(start.getMonth()+1).padStart(2,'0')}-${String(start.getDate()).padStart(2,'0')}`;
  const label=distance===0?"Aujourd’hui":distance===1?'Demain':start.toLocaleDateString('fr-FR',{weekday:'long',day:'numeric',month:'long'});
  return{key,label,order:1,sort:day};
}
function favoriteNextKickoffMarkup(matches,now=new Date()){
  const next=matches.filter(match=>match.status==='scheduled').map(match=>({match,start:new Date(match.starts_at||'')}))
    .filter(row=>Number.isFinite(row.start.getTime())&&row.start>=now)
    .sort((a,b)=>a.start-b.start)[0];
  if(!next)return'';
  const match=next.match,home=(match.home_team||{}),away=(match.away_team||{});
  const teams=`${home.short_name||home.name||'Domicile'} – ${away.short_name||away.name||'Extérieur'}`;
  const date=next.start.toLocaleString('fr-FR',{dateStyle:'medium',timeStyle:'short'});
  return `<strong>Prochain coup d’envoi</strong><a href="/match?id=${encodeURIComponent(match.external_id)}">${esc(teams)} · ${esc(date)}</a>`;
}
function renderFavoriteAgenda(){
  syncFavoriteAgendaSelection();
  const filters=$('favorite-agenda-filters'),matches=favoriteAgendaMatches.filter(match=>favoriteAgendaIncludes(match,favoriteAgendaSelection));
  const next=favoriteNextKickoffMarkup(matches);
  if($('favorite-next').innerHTML!==next)$('favorite-next').innerHTML=next;
  const live=matches.filter(match=>match.status==='live').length,upcoming=matches.length-live;
  const counts={all:matches.length,live,upcoming},labels={all:'Tous',live:'En direct',upcoming:'À venir'};
  for(const button of filters.querySelectorAll('[data-agenda-filter]')){
    const filter=button.dataset.agendaFilter;
    button.setAttribute('aria-pressed',String(filter===favoriteAgendaFilter));
    button.textContent=`${labels[filter]} (${counts[filter]})`;
  }
  const rows=matches.filter(match=>favoriteAgendaFilter==='all'||(favoriteAgendaFilter==='live'?match.status==='live':match.status!=='live'));
  if(!rows.length){$('favorite-agenda').innerHTML=empty(favoriteAgendaSelection!=='all'&&!matches.length?'Aucun match enregistré pour ce favori.':favoriteAgendaFilter==='live'?'Aucun favori en direct.':favoriteAgendaFilter==='upcoming'?'Aucun prochain match enregistré.':'Aucun direct ni prochain match enregistré.');return}
  const groups=new Map();
  for(const match of rows){const group=favoriteAgendaGroup(match);if(!groups.has(group.key))groups.set(group.key,{...group,matches:[]});groups.get(group.key).matches.push(match)}
  $('favorite-agenda').innerHTML=[...groups.values()].sort((a,b)=>a.order-b.order||a.sort-b.sort).map(group=>`<section class="agenda-group"><h3>${esc(group.label)}</h3>${group.matches.map(favoriteMatch).join('')}</section>`).join('');
}
$('favorite-agenda-filters').onclick=event=>{
  const button=event.target.closest('[data-agenda-filter]');if(!button)return;
  favoriteAgendaFilter=button.dataset.agendaFilter;persistFavoriteAgendaView();renderFavoriteAgenda();
};
$('favorite-agenda-selection').onchange=event=>{
  favoriteAgendaSelection=event.target.value;persistFavoriteAgendaView();
  $('favorite-agenda').innerHTML=empty('Chargement des matchs…');
  $('favorite-next').innerHTML='';
  refreshFavoriteMatches();
};
"""
PAGE = PAGE.replace("</style>", FAVORITE_AGENDA_CSS + "</style>", 1)
PAGE = PAGE.replace('<div id="favorite-agenda"></div>',
                    FAVORITE_AGENDA_HTML + '<div id="favorite-agenda"></div>', 1)
PAGE = PAGE.replace("</script></body></html>",
                    FAVORITE_AGENDA_SCRIPT + "</script></body></html>", 1)

RECENT_VIEWS_SCRIPT = r"""
const recentViewKey='butbutbut:recent-views:v1';
let recentViewRecorded=false;
function validRecentView(row){
  if(!row||!['match','team','competition'].includes(row.type))return null;
  if(typeof row.external_id!=='string'||typeof row.name!=='string')return null;
  const external_id=row.external_id.trim(),name=row.name.trim();
  if(!external_id||!name||external_id.length>200||name.length>200)return null;
  if(/[\x00-\x1f\x7f]/.test(external_id+name))return null;
  return{type:row.type,external_id,name};
}
function recentViewId(row){return `${row.type}:${row.external_id}`}
function readRecentViews(){
  try{
    const saved=JSON.parse(localStorage.getItem(recentViewKey)||'[]');
    if(!Array.isArray(saved))return[];
    const rows=[],seen=new Set();
    for(const candidate of saved){
      const row=validRecentView(candidate);if(!row)continue;
      const id=recentViewId(row);if(seen.has(id))continue;
      seen.add(id);rows.push(row);if(rows.length===8)break;
    }
    return rows;
  }catch(_e){return[]}
}
function rememberRecentView(candidate){
  if(recentViewRecorded)return;
  const row=validRecentView(candidate);if(!row)return;
  recentViewRecorded=true;
  const rows=readRecentViews();
  if(rows[0]&&recentViewId(rows[0])===recentViewId(row))return;
  try{localStorage.setItem(recentViewKey,JSON.stringify([row,...rows.filter(item=>recentViewId(item)!==recentViewId(row))].slice(0,8)))}catch(_e){}
}
"""
RECENT_HOME_HTML = """<div id="recent-panel" class="recent-panel hidden"><h3>Consultés récemment</h3><div id="recent-views" class="recent-views"></div></div>"""
RECENT_HOME_CSS = """.recent-panel{border-top:1px solid #263149;margin-top:20px;padding-top:18px}.recent-panel.hidden{display:none}.recent-panel h3{margin:0 0 10px;color:#cbd5e1;font-size:.88rem}.recent-views{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:8px}.recent-item{display:flex;align-items:stretch;min-width:0;border:1px solid #39475f;border-radius:12px;background:#172033}.recent-item a{flex:1;min-width:0;padding:10px 12px;color:#f8fafc;text-decoration:none}.recent-item a:hover{text-decoration:underline}.recent-item small{display:block;color:#94a3b8}.recent-item button{border-radius:0 12px 12px 0;padding:7px 12px;background:transparent;color:#fbca3e}.recent-item button:hover{background:#29344a}.recent-item button[aria-pressed="true"]{color:#fbca3e}"""
RECENT_HOME_SCRIPT = r"""
function recentViewHref(row){
  const path=row.type==='match'?'/match':row.type==='team'?'/team':'/competition';
  return `${path}?id=${encodeURIComponent(row.external_id)}`;
}
function renderRecentViews(){
  const rows=readRecentViews(),panel=$('recent-panel');
  panel.classList.toggle('hidden',!rows.length);
  const labels={match:'Match Center',team:'Équipe',competition:'Compétition'};
  $('recent-views').innerHTML=rows.map(row=>{
    const active=row.type!=='match'&&isFavorite(row),full=!active&&favorites.length>=20;
    const label=full?`20 favoris maximum pour ${row.name}`:`${active?'Retirer':'Ajouter'} ${row.name} ${active?'des':'aux'} favoris`;
    const button=row.type==='match'?'':`<button type="button" data-recent-favorite="${encodeURIComponent(JSON.stringify(row))}" aria-pressed="${active}" aria-label="${esc(label)}" ${full?'disabled':''}>${active?'★':'☆'}</button>`;
    return `<div class="recent-item"><a href="${recentViewHref(row)}"><strong>${esc(row.name)}</strong><small>${labels[row.type]}</small></a>${button}</div>`;
  }).join('');
}
const saveFavoritesWithoutRecent=saveFavorites;
saveFavorites=function(){saveFavoritesWithoutRecent();renderRecentViews()};
$('recent-views').onclick=event=>{
  const button=event.target.closest('[data-recent-favorite]');if(!button)return;
  toggleFavorite(JSON.parse(decodeURIComponent(button.dataset.recentFavorite)));
};
window.addEventListener('storage',event=>{if(event.key===recentViewKey||event.key===favoriteKey)renderRecentViews()});
document.addEventListener('keydown',event=>{
  if(event.key!=='/'||event.altKey||event.ctrlKey||event.metaKey||event.shiftKey)return;
  if(event.target?.closest('input,textarea,select,[contenteditable="true"]'))return;
  event.preventDefault();$('search').focus();
});
$('search').addEventListener('keydown',event=>{
  if(event.key!=='Escape')return;
  clearTimeout(searchTimer);searchSequence++;$('search').value='';searchRows=[];renderSearch();$('search').blur();
});
renderRecentViews();
"""
PAGE = PAGE.replace("</style>", RECENT_HOME_CSS + "</style>", 1)
PAGE = PAGE.replace('<div id="search-results" class="search-results"><div class="empty">Saisis au moins deux caractères.</div></div>',
                    '<div id="search-results" class="search-results"><div class="empty">Saisis au moins deux caractères.</div></div>' + RECENT_HOME_HTML, 1)
PAGE = PAGE.replace("</script></body></html>",
                    RECENT_VIEWS_SCRIPT + RECENT_HOME_SCRIPT
                    + "</script></body></html>", 1)


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

MATCH_FAVORITES_CSS = """.match-favorites{display:flex;justify-content:center;align-items:center;gap:8px;flex-wrap:wrap;border-top:1px solid #263149;padding-top:17px;margin-top:20px}.match-favorites-label{color:#94a3b8;font-size:.75rem;font-weight:800;letter-spacing:.08em;text-transform:uppercase;margin-right:4px}.match-favorites button{border:1px solid #39475f;border-radius:999px;background:#172033;color:#fbca3e;padding:7px 11px;font:inherit;font-size:.8rem;font-weight:750;cursor:pointer}.match-favorites button:hover{background:#29344a}.match-favorites button[aria-pressed="true"]{background:#fbca3e;color:#111827}.match-favorites button:disabled{opacity:.5;cursor:not-allowed}.match-favorites-status:not(:empty){width:100%;color:#fca5a5;font-size:.8rem}"""
MATCH_FAVORITES_SCRIPT = r"""
const matchFavoriteKey='butbutbut:favorites:v1';
let matchFavoriteItems=[];
function readMatchFavorites(){
  try{const rows=JSON.parse(localStorage.getItem(matchFavoriteKey)||'[]');return Array.isArray(rows)?rows.filter(row=>row&&['team','competition'].includes(row.type)&&row.external_id&&row.name).slice(0,20):[]}
  catch(_e){return[]}
}
function matchFavoriteId(item){return `${item.type}:${item.external_id}`}
function syncMatchFavoriteButtons(){
  const rows=readMatchFavorites(),selected=new Set(rows.map(matchFavoriteId));
  for(const button of app.querySelectorAll('[data-match-favorite]')){
    const item=matchFavoriteItems[Number(button.dataset.matchFavorite)],active=selected.has(matchFavoriteId(item)),full=!active&&rows.length>=20;
    button.disabled=full;button.setAttribute('aria-pressed',String(active));
    button.textContent=`${active?'★':'☆'} ${item.short_name||item.name}`;
    button.setAttribute('aria-label',full?`20 favoris maximum pour ${item.name}`:`${active?'Retirer':'Ajouter'} ${item.name} ${active?'des':'aux'} favoris`);
  }
}
function mountMatchFavorites(data){
  const match=data.match||{},competition=match.competition||{},home=match.home_team||{},away=match.away_team||{};
  const options=[
    {type:'team',external_id:home.external_id,name:home.name,short_name:home.short_name||''},
    {type:'team',external_id:away.external_id,name:away.name,short_name:away.short_name||''},
    {type:'competition',external_id:competition.external_id,name:competition.name},
  ];
  const seen=new Set();matchFavoriteItems=options.filter(item=>{const key=matchFavoriteId(item);if(!item.external_id||!item.name||seen.has(key))return false;seen.add(key);return true});
  if(!matchFavoriteItems.length)return;
  const card=app.querySelector('section.card')||app,holder=document.createElement('div');holder.className='match-favorites';
  const heading=document.createElement('span');heading.className='match-favorites-label';heading.textContent='Suivre';holder.append(heading);
  matchFavoriteItems.forEach((item,index)=>{const button=document.createElement('button');button.type='button';button.dataset.matchFavorite=String(index);button.dataset.favoriteKey=matchFavoriteId(item);holder.append(button)});
  const status=document.createElement('span');status.className='match-favorites-status';status.setAttribute('role','status');status.setAttribute('aria-live','polite');holder.append(status);card.append(holder);syncMatchFavoriteButtons();
}
const renderMatchWithoutFavorites=render;
render=function(data){
  const focused=document.activeElement?.dataset.favoriteKey;
  renderMatchWithoutFavorites(data);mountMatchFavorites(data);
  if(focused){const replacement=[...app.querySelectorAll('[data-favorite-key]')].find(button=>button.dataset.favoriteKey===focused);if(replacement)replacement.focus({preventScroll:true})}
};
app.addEventListener('click',event=>{
  const button=event.target.closest('[data-match-favorite]');if(!button||!app.contains(button))return;
  const item=matchFavoriteItems[Number(button.dataset.matchFavorite)];if(!item)return;
  const rows=readMatchFavorites(),key=matchFavoriteId(item),index=rows.findIndex(row=>matchFavoriteId(row)===key);
  if(index>=0)rows.splice(index,1);else if(rows.length<20)rows.push(item);else return;
  try{localStorage.setItem(matchFavoriteKey,JSON.stringify(rows))}
  catch(_e){const status=app.querySelector('.match-favorites-status');if(status)status.textContent='Favoris indisponibles dans ce navigateur.';return}
  syncMatchFavoriteButtons();
});
window.addEventListener('storage',event=>{if(event.key===matchFavoriteKey)syncMatchFavoriteButtons()});
"""
MATCH_PAGE = MATCH_PAGE.replace("</style>", MATCH_FAVORITES_CSS + "</style>", 1)
MATCH_PAGE = MATCH_PAGE.replace("async function load()",
                                MATCH_FAVORITES_SCRIPT + "async function load()", 1)
MATCH_RECENT_SCRIPT = r"""
const renderMatchBeforeRecent=render;
render=function(data){
  renderMatchBeforeRecent(data);
  const match=data.match||{},home=match.home_team||{},away=match.away_team||{};
  rememberRecentView({type:'match',external_id:match.external_id,
    name:`${home.short_name||home.name||'Domicile'} – ${away.short_name||away.name||'Extérieur'}`});
};
"""
MATCH_PAGE = MATCH_PAGE.replace("async function load()",
                                RECENT_VIEWS_SCRIPT + MATCH_RECENT_SCRIPT
                                + "async function load()", 1)


COMPETITION_PAGE = r"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>butbutbut — Compétition</title><style>
*{box-sizing:border-box}body{margin:0;background:#070b14;color:#f8fafc;font:16px/1.45 system-ui,sans-serif}main{max-width:1040px;margin:auto;padding:28px 18px 80px}a{color:#fbca3e;text-decoration:none}.back{display:inline-block;margin-bottom:24px}.card{background:#111827;border:1px solid #273449;border-radius:22px;padding:clamp(17px,3vw,28px);margin:16px 0}header{display:flex;align-items:end;justify-content:space-between;gap:18px;flex-wrap:wrap}.header-actions{display:flex;align-items:end;gap:10px;flex-wrap:wrap}.favorite-button{background:#fbca3e;color:#111827;border:0;border-radius:999px;padding:10px 15px;font:inherit;font-weight:800;cursor:pointer}.favorite-button[aria-pressed="true"]{background:#172033;color:#fbca3e;border:1px solid #39475f}.favorite-button:disabled{opacity:.55;cursor:not-allowed}h1{margin:0;font-size:clamp(2rem,6vw,4rem);letter-spacing:-.05em}h2{margin:0 0 16px}.muted{color:#94a3b8}.eyebrow{color:#fbca3e;text-transform:uppercase;letter-spacing:.12em;font-size:.76rem;font-weight:800}select{background:#1f2937;color:#f8fafc;border:1px solid #39475f;border-radius:999px;padding:10px 15px;font:inherit}.groups{display:grid;grid-template-columns:repeat(auto-fit,minmax(310px,1fr));gap:16px}.group{overflow:auto}.group h3,.round h3{margin:0 0 12px}table{width:100%;border-collapse:collapse;font-size:.88rem}th,td{padding:8px 6px;border-top:1px solid #263149;text-align:right;font-variant-numeric:tabular-nums}th:first-child,td:first-child{text-align:left}.rank{color:#fbca3e;font-weight:800}.round{margin-top:24px}.match{display:grid;grid-template-columns:105px 1fr auto 1fr;gap:12px;align-items:center;color:inherit;padding:12px 4px;border-top:1px solid #263149}.match:hover{background:#172033}.home{text-align:right}.score{font-weight:850;font-variant-numeric:tabular-nums}.date{color:#94a3b8;font-size:.8rem}.live{color:#fca5a5}.empty{color:#64748b}@media(max-width:620px){.match{grid-template-columns:1fr auto 1fr}.date{grid-column:1/-1}.groups{grid-template-columns:1fr}}</style></head><body><main><a class="back" href="/">← Retour au compagnon</a><div id="app" class="card"><span class="muted">Chargement de la compétition…</span></div></main><script>
const app=document.getElementById('app'),esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),labels={scheduled:'À venir',live:'En direct',finished:'Terminé',postponed:'Reporté',cancelled:'Annulé'};
const favoriteStorage='butbutbut:favorites:v1';function readFavorites(){try{const rows=JSON.parse(localStorage.getItem(favoriteStorage)||'[]');return Array.isArray(rows)?rows.filter(x=>x&&['team','competition'].includes(x.type)&&x.external_id&&x.name).slice(0,20):[]}catch(_e){return[]}}function bindFavorite(item){const button=document.getElementById('favorite');if(!button||!item.external_id)return;const id=`${item.type}:${item.external_id}`;let rows=readFavorites();function sync(){const active=rows.some(x=>`${x.type}:${x.external_id}`===id),full=!active&&rows.length>=20;button.disabled=full;button.setAttribute('aria-pressed',String(active));button.textContent=active?'★ Favori':full?'20 favoris maximum':'☆ Ajouter aux favoris';button.setAttribute('aria-label',active?`Retirer ${item.name} des favoris`:`Ajouter ${item.name} aux favoris`)}button.onclick=()=>{const index=rows.findIndex(x=>`${x.type}:${x.external_id}`===id);if(index>=0)rows.splice(index,1);else if(rows.length<20)rows.push(item);try{localStorage.setItem(favoriteStorage,JSON.stringify(rows))}catch(_e){}sync()};sync()}
function val(v){return v==null?'—':esc(v)}function dateLabel(v){if(!v)return'';const d=new Date(v);return Number.isNaN(d.getTime())?'':d.toLocaleString('fr-FR',{dateStyle:'short',timeStyle:'short'})}
function tables(rows){if(!rows.length)return'<p class="empty">Aucun classement officiel publié pour cette édition.</p>';return `<div class="groups">${rows.map(g=>`<section class="card group"><h3>${esc(g.group_name||g.phase_name||'Classement')}</h3><table><thead><tr><th>Équipe</th><th>J</th><th>G</th><th>N</th><th>P</th><th>+/-</th><th>Pts</th></tr></thead><tbody>${(g.rows||[]).map(r=>`<tr><td><span class="rank">${val(r.rank)}</span> ${esc(r.team_name)}</td><td>${val(r.played)}</td><td>${val(r.won)}</td><td>${val(r.drawn)}</td><td>${val(r.lost)}</td><td>${val(r.goal_difference)}</td><td><strong>${val(r.points)}</strong></td></tr>`).join('')}</tbody></table></section>`).join('')}</div>`}
function matchRow(m){const h=m.home_team||{},a=m.away_team||{},scheduled=m.status==='scheduled',score=m.spoiler_free?'Masqué':scheduled?'–':`${m.home_score}–${m.away_score}`,status=m.spoiler_free?'Direct synchronisé':labels[m.status]||m.status,match=`/match?id=${encodeURIComponent(m.external_id)}`;return `<div class="match"><a class="date" href="${match}">${esc(dateLabel(m.starts_at))}<br>${esc(status)}</a><a class="home" href="/team?id=${encodeURIComponent(h.external_id)}">${esc(h.short_name||h.name)}</a><a class="score ${m.status==='live'?'live':''}" href="${match}">${esc(score)}</a><a href="/team?id=${encodeURIComponent(a.external_id)}">${esc(a.short_name||a.name)}</a></div>`}
function fixtures(matches){if(!matches.length)return'<p class="empty">Aucune rencontre enregistrée pour cette édition.</p>';const groups=[];for(const m of matches){const parts=[m.phase_name,m.group_name,m.round_name].filter(Boolean),label=[...new Set(parts)].join(' · ')||'Rencontres';let group=groups.find(g=>g.label===label);if(!group){group={label,matches:[]};groups.push(group)}group.matches.push(m)}return groups.map(g=>`<section class="round"><h3>${esc(g.label)}</h3>${g.matches.map(matchRow).join('')}</section>`).join('')}
function render(d){const c=d.competition||{},e=d.edition||{},options=(d.editions||[]).map(x=>`<option value="${esc(x.external_id)}" ${x.external_id===e.external_id?'selected':''}>${esc(x.name)} · ${x.match_count} match(s)</option>`).join('');app.className='';app.innerHTML=`<section class="card"><header><div><div class="eyebrow">Compétition</div><h1>${esc(c.name||'Compétition')}</h1><p class="muted">${esc(e.name||'Aucune édition')}</p></div><div class="header-actions">${options?`<label>Édition<br><select id="edition">${options}</select></label>`:''}<button id="favorite" class="favorite-button" type="button">☆ Ajouter aux favoris</button></div></header></section><section><h2>Classements</h2>${tables(d.standings||[])}</section><section class="card"><h2>Rencontres</h2>${fixtures(d.matches||[])}</section>`;bindFavorite({type:'competition',external_id:c.external_id,name:c.name||'Compétition',country_code:c.country_code||''});const select=document.getElementById('edition');if(select)select.onchange=()=>{const url=new URL(location.href);url.searchParams.set('edition',select.value);history.replaceState(null,'',url);load()}}
async function load(){const p=new URLSearchParams(location.search),id=p.get('id')||'',edition=p.get('edition');if(!id){app.innerHTML='<h1>Compétition introuvable</h1>';return}let url='/api/v1/competition?id='+encodeURIComponent(id);if(edition!==null)url+='&edition='+encodeURIComponent(edition);try{const r=await fetch(url,{cache:'no-store'}),d=await r.json();if(!r.ok)throw new Error(d.error||'Compétition indisponible');render(d)}catch(e){app.innerHTML=`<h1>Compétition indisponible</h1><p class="muted">${esc(e.message)}</p>`}}load();setInterval(load,10000);
</script></body></html>"""


TEAM_PAGE = r"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>butbutbut — Équipe</title><style>
*{box-sizing:border-box}body{margin:0;background:#070b14;color:#f8fafc;font:16px/1.45 system-ui,sans-serif}main{max-width:920px;margin:auto;padding:28px 18px 80px}a{color:#fbca3e;text-decoration:none}.back{display:inline-block;margin-bottom:24px}.card{background:#111827;border:1px solid #273449;border-radius:22px;padding:clamp(17px,3vw,28px);margin:16px 0}header{display:flex;align-items:center;gap:20px;flex-wrap:wrap}h1{margin:0;font-size:clamp(2rem,7vw,4.5rem);letter-spacing:-.05em}.badge{display:grid;place-items:center;width:72px;height:72px;border-radius:22px;background:#fbca3e;color:#111827;font-size:1.35rem;font-weight:950}.favorite-button{margin-left:auto;background:#fbca3e;color:#111827;border:0;border-radius:999px;padding:10px 15px;font:inherit;font-weight:800;cursor:pointer}.favorite-button[aria-pressed="true"]{background:#172033;color:#fbca3e;border:1px solid #39475f}.favorite-button:disabled{opacity:.55;cursor:not-allowed}.eyebrow{color:#fbca3e;text-transform:uppercase;letter-spacing:.12em;font-size:.76rem;font-weight:800}.muted{color:#94a3b8}.record{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-top:24px}.stat{background:#172033;border-radius:14px;padding:12px;text-align:center}.stat strong{display:block;font-size:1.35rem}.stat span{color:#94a3b8;font-size:.74rem}.form,.competitions{display:flex;gap:8px;flex-wrap:wrap;margin-top:18px}.pill,.competition{display:inline-grid;place-items:center;min-width:34px;height:34px;border-radius:999px;font-weight:850}.pill.W{background:#166534}.pill.D{background:#475569}.pill.L{background:#991b1b}.competition{border:1px solid #39475f;padding:0 12px;color:#f8fafc;font-size:.8rem}.match{display:grid;grid-template-columns:112px 1fr auto 1fr;gap:12px;align-items:center;padding:13px 4px;border-top:1px solid #263149}.match:first-of-type{border-top:0}.home{text-align:right}.score{font-weight:850;font-variant-numeric:tabular-nums;color:#f8fafc}.date{color:#94a3b8;font-size:.8rem}.live{color:#fca5a5}.team{color:inherit}.empty{color:#64748b}@media(max-width:600px){.record{grid-template-columns:repeat(3,1fr)}.match{grid-template-columns:1fr auto 1fr}.date{grid-column:1/-1}.badge{width:54px;height:54px;border-radius:16px}.favorite-button{margin-left:0}}</style></head><body><main><a class="back" href="/">← Retour au compagnon</a><div id="app" class="card"><span class="muted">Chargement de l’équipe…</span></div></main><script>
const app=document.getElementById('app'),esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),labels={scheduled:'À venir',live:'En direct',finished:'Terminé',postponed:'Reporté',cancelled:'Annulé'};
const favoriteStorage='butbutbut:favorites:v1';function readFavorites(){try{const rows=JSON.parse(localStorage.getItem(favoriteStorage)||'[]');return Array.isArray(rows)?rows.filter(x=>x&&['team','competition'].includes(x.type)&&x.external_id&&x.name).slice(0,20):[]}catch(_e){return[]}}function bindFavorite(item){const button=document.getElementById('favorite');if(!button||!item.external_id)return;const id=`${item.type}:${item.external_id}`;let rows=readFavorites();function sync(){const active=rows.some(x=>`${x.type}:${x.external_id}`===id),full=!active&&rows.length>=20;button.disabled=full;button.setAttribute('aria-pressed',String(active));button.textContent=active?'★ Favori':full?'20 favoris maximum':'☆ Ajouter aux favoris';button.setAttribute('aria-label',active?`Retirer ${item.name} des favoris`:`Ajouter ${item.name} aux favoris`)}button.onclick=()=>{const index=rows.findIndex(x=>`${x.type}:${x.external_id}`===id);if(index>=0)rows.splice(index,1);else if(rows.length<20)rows.push(item);try{localStorage.setItem(favoriteStorage,JSON.stringify(rows))}catch(_e){}sync()};sync()}
function dateLabel(v){if(!v)return'';const d=new Date(v);return Number.isNaN(d.getTime())?'':d.toLocaleString('fr-FR',{dateStyle:'medium',timeStyle:'short'})}
function matchRow(m,id){const h=m.home_team||{},a=m.away_team||{},scheduled=m.status==='scheduled',score=m.spoiler_free?'Masqué':scheduled?'–':`${m.home_score}–${m.away_score}`,status=m.spoiler_free?'Direct synchronisé':labels[m.status]||m.status,url=`/match?id=${encodeURIComponent(m.external_id)}`,team=t=>t.external_id===id?`<strong>${esc(t.short_name||t.name)}</strong>`:`<a class="team" href="/team?id=${encodeURIComponent(t.external_id)}">${esc(t.short_name||t.name)}</a>`;return `<div class="match"><a class="date" href="${url}">${esc(dateLabel(m.starts_at))}<br>${esc((m.competition||{}).name||'')} · ${esc(status)}</a><span class="home">${team(h)}</span><a class="score ${m.status==='live'?'live':''}" href="${url}">${esc(score)}</a><span>${team(a)}</span></div>`}
function section(title,rows,id,empty){return `<section class="card"><h2>${esc(title)}</h2>${rows.length?rows.map(m=>matchRow(m,id)).join(''):`<p class="empty">${esc(empty)}</p>`}</section>`}
function render(d){const t=d.team||{},r=d.record||{},matches=d.matches||[],live=matches.filter(m=>m.status==='live'),upcoming=matches.filter(m=>['scheduled','postponed'].includes(m.status)),results=matches.filter(m=>['finished','cancelled'].includes(m.status)).slice(-20).reverse(),initials=(t.short_name||t.name||'?').split(/\s+/).map(x=>x[0]).join('').slice(0,3).toUpperCase();app.className='';app.innerHTML=`<section class="card"><header><span class="badge">${esc(initials)}</span><div><div class="eyebrow">Équipe</div><h1>${esc(t.name||'Équipe')}</h1></div><button id="favorite" class="favorite-button" type="button">☆ Ajouter aux favoris</button></header><div class="record"><div class="stat"><strong>${r.played||0}</strong><span>matchs</span></div><div class="stat"><strong>${r.won||0}</strong><span>victoires</span></div><div class="stat"><strong>${r.drawn||0}</strong><span>nuls</span></div><div class="stat"><strong>${r.lost||0}</strong><span>défaites</span></div><div class="stat"><strong>${r.goals_for||0}–${r.goals_against||0}</strong><span>buts</span></div></div>${(d.form||[]).length?`<div class="form"><span class="muted">Forme</span>${d.form.map(x=>`<span class="pill ${esc(x)}">${esc(x)}</span>`).join('')}</div>`:''}<div class="competitions">${(d.competitions||[]).map(c=>`<a class="competition" href="/competition?id=${encodeURIComponent(c.external_id)}">${esc(c.name)}</a>`).join('')}</div></section>${live.length?section('En direct',live,t.external_id,''):''}${section('À venir',upcoming,t.external_id,'Aucun match à venir enregistré.')}${section('Derniers résultats',results,t.external_id,'Aucun résultat enregistré.')}`;bindFavorite({type:'team',external_id:t.external_id,name:t.name||'Équipe',short_name:t.short_name||''})}
async function load(){const id=new URLSearchParams(location.search).get('id')||'';if(!id){app.innerHTML='<h1>Équipe introuvable</h1>';return}try{const r=await fetch('/api/v1/team?id='+encodeURIComponent(id),{cache:'no-store'}),d=await r.json();if(!r.ok)throw new Error(d.error||'Équipe indisponible');render(d)}catch(e){app.innerHTML=`<h1>Équipe indisponible</h1><p class="muted">${esc(e.message)}</p>`}}load();setInterval(load,10000);
</script></body></html>"""

DETAIL_FAVORITES_STORAGE_SCRIPT = r"""
window.addEventListener('storage',event=>{
  if(event.key!==favoriteStorage)return;
  const button=document.getElementById('favorite');if(button)button.disabled=true;
  load();
});
"""
COMPETITION_PAGE = COMPETITION_PAGE.replace(
    "</script></body></html>",
    DETAIL_FAVORITES_STORAGE_SCRIPT + "</script></body></html>", 1)
TEAM_PAGE = TEAM_PAGE.replace(
    "</script></body></html>",
    DETAIL_FAVORITES_STORAGE_SCRIPT + "</script></body></html>", 1)
COMPETITION_RECENT_SCRIPT = r"""
const renderCompetitionBeforeRecent=render;
render=function(data){
  renderCompetitionBeforeRecent(data);
  const competition=data.competition||{};
  rememberRecentView({type:'competition',external_id:competition.external_id,
    name:competition.name||'Compétition'});
};
"""
TEAM_RECENT_SCRIPT = r"""
const renderTeamBeforeRecent=render;
render=function(data){
  renderTeamBeforeRecent(data);
  const team=data.team||{};
  rememberRecentView({type:'team',external_id:team.external_id,
    name:team.name||'Équipe'});
};
"""
COMPETITION_PAGE = COMPETITION_PAGE.replace(
    "async function load()",
    RECENT_VIEWS_SCRIPT + COMPETITION_RECENT_SCRIPT + "async function load()", 1)
TEAM_PAGE = TEAM_PAGE.replace(
    "async function load()",
    RECENT_VIEWS_SCRIPT + TEAM_RECENT_SCRIPT + "async function load()", 1)


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


def favorite_matches_payload(matches, current_state=None):
    """Fil favori dont chaque direct respecte le retard du flux."""
    public = []
    for match in matches:
        visible = match_center_payload(match, current_state=current_state)
        row = dict(visible["match"])
        row["spoiler_free"] = visible["spoiler_free"]
        public.append(row)
    return {
        "schema_version": site_feed.SCHEMA_VERSION,
        "generated_at": site_feed.utc_now(),
        "matches": public,
    }


def favorite_calendar(matches):
    """Calendrier iCalendar des prochains matchs normalises favoris."""
    rows = []
    for match in matches:
        if match.get("status") != "scheduled" or not match.get("starts_at"):
            continue
        try:
            start = datetime.fromisoformat(
                match["starts_at"].replace("Z", "+00:00"))
        except (TypeError, ValueError):
            continue
        competition = match.get("competition") or {}
        home, away = match.get("home_team") or {}, match.get("away_team") or {}
        rows.append(SimpleNamespace(
            id=match.get("external_id"), start=start,
            home=home.get("name") or home.get("short_name") or "Equipe",
            away=away.get("name") or away.get("short_name") or "Equipe",
            venue=match.get("venue") or "",
            league=SimpleNamespace(name=competition.get("name") or "Match"),
            sport=SimpleNamespace(code=""),
            group_name=match.get("group_name") or "",
            round_name=match.get("round_name") or "",
        ))
    return ical.render(rows, name="butbutbut - Mes favoris")


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

        def _calendar(self, page):
            body = page.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/calendar; charset=utf-8")
            self.send_header("Content-Disposition",
                             'attachment; filename="butbutbut-favoris.ics"')
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        @staticmethod
        def _favorite_query(query, default_limit=12):
            params = parse_qs(query, keep_blank_values=True)
            unknown = set(params) - {"team", "competition", "limit"}
            teams = [item.strip() for item in params.get("team", ())]
            competitions = [item.strip() for item in params.get(
                "competition", ())]
            limits = params.get("limit")
            invalid = (unknown or not teams and not competitions
                       or any(not item or len(item) > 200
                              for item in teams + competitions)
                       or len(teams) + len(competitions) > 20
                       or limits is not None and len(limits) != 1)
            if invalid:
                raise ValueError("favoris invalides")
            try:
                limit = default_limit if limits is None else int(limits[0])
            except (TypeError, ValueError) as exc:
                raise ValueError("favoris invalides") from exc
            if not 1 <= limit <= 20:
                raise ValueError("favoris invalides")
            return teams, competitions, limit

        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path == "/api/state":
                data = state.read(state_path) or {}
                if stories_path is not None:
                    data["souvenirs"] = souvenir.read(stories_path)[-10:]
                return self._json(data)
            if parsed.path == "/api/v1/search":
                params = parse_qs(parsed.query, keep_blank_values=True)
                unknown = set(params) - {"q", "limit"}
                queries = params.get("q") or []
                limits = params.get("limit")
                if (unknown or len(queries) != 1
                        or len(queries[0].strip()) < 2
                        or limits is not None and len(limits) != 1):
                    return self._json({"error": "recherche invalide"}, 400)
                try:
                    limit = 12 if limits is None else int(limits[0])
                except (TypeError, ValueError):
                    return self._json({"error": "recherche invalide"}, 400)
                if not 1 <= limit <= 20:
                    return self._json({"error": "recherche invalide"}, 400)
                try:
                    results = site_feed.Store(feed_path).search(
                        queries[0], limit=limit)
                except (OSError, sqlite3.Error):
                    return self._json({"error": "recherche indisponible"}, 503)
                return self._json({
                    "schema_version": site_feed.SCHEMA_VERSION,
                    "generated_at": site_feed.utc_now(),
                    "query": queries[0].strip(),
                    "results": results,
                })
            if parsed.path in ("/api/v1/favorites", "/api/v1/favorites.ics"):
                try:
                    teams, competitions, limit = self._favorite_query(
                        parsed.query, default_limit=(
                            20 if parsed.path.endswith(".ics") else 12))
                except ValueError:
                    return self._json({"error": "favoris invalides"}, 400)
                try:
                    matches = site_feed.Store(feed_path).favorite_matches(
                        teams, competitions, limit=limit)
                except (OSError, sqlite3.Error, TypeError, ValueError):
                    return self._json({"error": "favoris indisponibles"}, 503)
                if parsed.path.endswith(".ics"):
                    return self._calendar(favorite_calendar(matches))
                return self._json(favorite_matches_payload(
                    matches, current_state=state.read(state_path)))
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
