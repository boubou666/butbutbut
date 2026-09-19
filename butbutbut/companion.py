"""Ecran compagnon HTTP local, sans dependance ni ressource distante."""

from __future__ import annotations

import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import souvenir, state, streaming

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
*{box-sizing:border-box}body{margin:0;background:#070b14;color:#f8fafc;font:16px/1.45 system-ui,sans-serif}main{max-width:980px;margin:auto;padding:32px 18px 80px}header{display:flex;justify-content:space-between;align-items:center;gap:16px;margin-bottom:28px}.controls{display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end}h1{margin:0;font-size:clamp(1.6rem,5vw,3rem);letter-spacing:-.04em}.live{color:#fbca3e}.status{color:#94a3b8}.panel{background:#111827;border:1px solid #273449;border-radius:22px;padding:20px;margin:16px 0}.match,.event,.story{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:14px;padding:14px 0;border-top:1px solid #263149}.panel>:nth-child(2){border-top:0}.home{text-align:right}.score{font-size:1.55rem;font-weight:800;font-variant-numeric:tabular-nums}.meta{grid-column:1/-1;text-align:center;color:#94a3b8;font-size:.85rem}.event{grid-template-columns:90px 1fr auto}.event .home{text-align:left}.context{color:#fbca3e;text-transform:uppercase;font-size:.75rem;letter-spacing:.1em}.story{grid-template-columns:1fr auto 1fr}.muted{color:#94a3b8}button,select{border:0;border-radius:999px;padding:11px 16px;font:inherit}select{background:#1f2937;color:#f8fafc}button{background:#fbca3e;color:#111827;font-weight:800;cursor:pointer}button:disabled{opacity:.45;cursor:not-allowed}.hidden{display:none}.empty{color:#64748b;padding:12px 0}a{color:#fbca3e}footer{margin-top:30px;color:#64748b;font-size:.8rem}</style></head><body><main><header><div><h1>butbutbut <span class="live">●</span></h1><div id="status" class="status">Connexion…</div></div><div class="controls"><select id="kickoff" class="hidden"></select><button id="sync">Je vois le coup d’envoi</button></div></header><section id="delay" class="panel hidden"></section><section class="panel"><h2>En direct</h2><div id="matches"></div></section><section class="panel"><h2>Dernières alertes</h2><div id="events"></div></section><section class="panel"><h2>Souvenirs</h2><div id="stories"></div></section><footer>Tout reste sur cette machine. Aucune police, image ou bibliothèque distante n’est chargée par cette page.</footer></main><script>
const $=id=>document.getElementById(id), esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function empty(text){return `<div class="empty">${esc(text)}</div>`}function match(m){return `<div class="match"><span class="home">${esc(m.home)}</span><span class="score">${esc(m.home_score)}–${esc(m.away_score)}</span><span>${esc(m.away)}</span><span class="meta">${esc(m.league)} · ${esc(m.clock)}</span></div>`}function event(e){return `<div class="event"><span class="context">${esc(e.context_label||e.title)}</span><span class="home">${esc(e.score_line)}<br><span class="muted">${esc(e.detail)}</span></span><span>${esc(e.minute)}</span></div>`}function story(s){return `<div class="story"><span class="home">${esc(s.home)}</span><span class="score">${esc(s.home_score)}–${esc(s.away_score)}</span><span>${esc(s.away)}</span><span class="meta">${esc(s.league)} · ${esc(s.goals?.length||0)} action(s) de score</span></div>`}
async function refresh(){try{const r=await fetch('/api/state',{cache:'no-store'}),d=await r.json(),delay=Number(d.stream_delay||0),ks=d.recent_kickoffs||[];$('status').textContent=d.updated_text?`Dernier relevé : ${d.updated_text}`:'Daemon arrêté ou état indisponible';$('sync').disabled=!ks.length;$('kickoff').classList.toggle('hidden',ks.length<2);$('kickoff').innerHTML=ks.slice().reverse().map(k=>`<option value="${esc(k.id)}">${esc(k.home)} – ${esc(k.away)}</option>`).join('');if(delay>0){$('delay').classList.remove('hidden');$('delay').innerHTML=`Flux synchronisé avec ${Math.round(delay)} s de retard. Les scores bruts sont masqués ici.`;$('matches').innerHTML=empty('Le fil synchronisé apparaît dans les alertes ci-dessous.')}else{$('delay').classList.add('hidden');$('matches').innerHTML=(d.matches||[]).map(match).join('')||empty('Aucun match en cours.')} $('events').innerHTML=(d.recent_events||[]).slice().reverse().map(event).join('')||empty('Aucune alerte récente.');$('stories').innerHTML=(d.souvenirs||[]).slice().reverse().map(story).join('')||empty('Aucun match terminé depuis l’installation.')}catch(e){$('status').textContent='Compagnon indisponible';}}$('sync').onclick=async()=>{const id=$('kickoff').value||'';const r=await fetch('/api/sync?match='+encodeURIComponent(id),{method:'POST'}),d=await r.json();alert(d.message||d.error);refresh()};refresh();setInterval(refresh,2000);
</script></body></html>"""


def handler(state_path, control_path, stories_path=None):
    state_path, control_path = Path(state_path), Path(control_path)
    stories_path = Path(stories_path) if stories_path else None

    class Handler(BaseHTTPRequestHandler):
        def _json(self, payload, status=200):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/api/state":
                data = state.read(state_path) or {}
                if stories_path is not None:
                    data["souvenirs"] = souvenir.read(stories_path)[-10:]
                return self._json(data)
            if self.path not in ("/", "/index.html"):
                return self._json({"error": "introuvable"}, 404)
            body = PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

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


def serve(state_path, control_path, bind="", on_ready=None, stories_path=None):
    host, port = parse_bind(bind)
    server = ThreadingHTTPServer(
        (host, port), handler(state_path, control_path, stories_path))
    if on_ready:
        on_ready(host, server.server_address[1])
    try:
        server.serve_forever(poll_interval=0.5)
    finally:
        server.server_close()
