"""Client-side agenda grouping and filter behavior."""

import json
import shutil
import subprocess
import unittest

from butbutbut import companion


@unittest.skipUnless(shutil.which("node"), "Node.js unavailable")
class TestFavoriteAgenda(unittest.TestCase):
    def test_groups_dates_and_filters_without_changing_the_source(self):
        harness = r"""
const assert = require('node:assert/strict');
const buttons = ['all','live','upcoming'].map(filter=>({
  dataset:{agendaFilter:filter},
  setAttribute(name,value){this[name]=value},
  textContent:'',
}));
const elements = {
  'favorite-agenda-filters':{querySelectorAll(){return buttons}},
  'favorite-agenda':{innerHTML:''},
  'favorite-next':{innerHTML:''},
  'favorite-agenda-selection':{dataset:{},innerHTML:'',value:'all'},
  'favorite-agenda-selection-label':{classList:{toggle(name,hidden){this.hidden=hidden}}},
  'favorite-selection-calendar':{href:'',classList:{toggle(name,hidden){this.hidden=hidden}},setAttribute(name,value){this[name]=value}},
};
function $(id){return elements[id]}
function esc(value){return String(value).replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]))}
function empty(message){return `<p>${message}</p>`}
function favoriteMatch(match){return `<a>${match.external_id}</a>`}
const savedViews=[];
const localStorage={setItem(key,value){savedViews.push([key,JSON.parse(value)])}};
const favoriteAgendaViewKey='butbutbut:favorite-agenda-view:v1';
let refreshCalls=0;
function refreshFavoriteMatches(){refreshCalls++}
const favorites=[
  {type:'team',external_id:'alpha:1',name:'Alpha'},
  {type:'competition',external_id:'cup',name:'Coupe'},
  {type:'team',external_id:'missing',name:'Sans match'},
];
function favoriteId(item){return `${item.type}:${item.external_id}`}
let favoriteAgendaMatches = [
  {external_id:'live',status:'live',competition:{external_id:'cup'},home_team:{external_id:'alpha:1'}},
  {external_id:'today',status:'scheduled',starts_at:'2026-09-22T12:00:00Z',competition:{external_id:'cup'},home_team:{name:'Club C'},away_team:{name:'Club D'}},
  {external_id:'tomorrow',status:'scheduled',starts_at:'2026-09-23T12:00:00Z',home_team:{external_id:'alpha:1',name:'<Alpha>'},away_team:{name:'Beta'}},
  {external_id:'postponed',status:'postponed'},
];
let favoriteAgendaFilter = 'all';
let favoriteAgendaSelection = 'all';
"""
        assertions = r"""
const now=new Date('2026-09-22T12:00:00Z');
assert.equal(favoriteAgendaGroup(favoriteAgendaMatches[0],now).label,'En direct');
assert.equal(favoriteAgendaGroup(favoriteAgendaMatches[1],now).label,'Aujourd’hui');
assert.equal(favoriteAgendaGroup(favoriteAgendaMatches[2],now).label,'Demain');
assert.equal(favoriteAgendaGroup(favoriteAgendaMatches[3],now).label,'Reportés');
assert.match(favoriteNextKickoffMarkup(favoriteAgendaMatches,new Date('2026-09-22T11:00:00Z')),/match\?id=today/);
assert.match(favoriteNextKickoffMarkup(favoriteAgendaMatches,new Date('2026-09-22T13:00:00Z')),/match\?id=tomorrow/);
assert.match(favoriteNextKickoffMarkup(favoriteAgendaMatches,new Date('2026-09-22T13:00:00Z')),/&lt;Alpha&gt;/);
assert.equal(favoriteNextKickoffMarkup(favoriteAgendaMatches,new Date('2026-09-24T12:00:00Z')),'');
renderFavoriteAgenda();
const all=elements['favorite-agenda'].innerHTML;
assert.ok(all.indexOf('En direct')<all.indexOf('Aujourd'));
assert.ok(all.indexOf('Aujourd')<all.indexOf('Demain'));
assert.ok(all.indexOf('Demain')<all.indexOf('Reportés'));
assert.equal(buttons[0].textContent,'Tous (4)');
assert.equal(buttons[1].textContent,'En direct (1)');
assert.equal(buttons[2].textContent,'À venir (3)');
assert.equal(elements['favorite-agenda-selection-label'].classList.hidden,false);
assert.match(elements['favorite-agenda-selection'].innerHTML,/Équipe · Alpha/);
assert.equal(elements['favorite-selection-calendar'].classList.hidden,true);
favoriteAgendaFilter='live';renderFavoriteAgenda();
assert.match(elements['favorite-agenda'].innerHTML,/<a>live<\/a>/);
assert.doesNotMatch(elements['favorite-agenda'].innerHTML,/<a>today<\/a>/);
assert.equal(buttons[1]['aria-pressed'],'true');
favoriteAgendaFilter='upcoming';renderFavoriteAgenda();
assert.doesNotMatch(elements['favorite-agenda'].innerHTML,/<a>live<\/a>/);
assert.match(elements['favorite-agenda'].innerHTML,/<a>postponed<\/a>/);
favoriteAgendaSelection='team:alpha:1';favoriteAgendaFilter='all';renderFavoriteAgenda();
assert.match(elements['favorite-agenda'].innerHTML,/<a>live<\/a>/);
assert.match(elements['favorite-agenda'].innerHTML,/<a>tomorrow<\/a>/);
assert.doesNotMatch(elements['favorite-agenda'].innerHTML,/<a>today<\/a>/);
assert.equal(buttons[0].textContent,'Tous (2)');
assert.equal(buttons[1].textContent,'En direct (1)');
assert.equal(elements['favorite-selection-calendar'].classList.hidden,false);
assert.match(elements['favorite-selection-calendar'].href,/limit=20&team=alpha%3A1$/);
favoriteAgendaFilter='upcoming';renderFavoriteAgenda();
assert.doesNotMatch(elements['favorite-agenda'].innerHTML,/<a>live<\/a>/);
assert.match(elements['favorite-agenda'].innerHTML,/<a>tomorrow<\/a>/);
favoriteAgendaSelection='competition:cup';favoriteAgendaFilter='all';renderFavoriteAgenda();
assert.match(elements['favorite-agenda'].innerHTML,/<a>today<\/a>/);
assert.doesNotMatch(elements['favorite-agenda'].innerHTML,/<a>tomorrow<\/a>/);
favoriteAgendaSelection='team:missing';renderFavoriteAgenda();
assert.equal(buttons[0].textContent,'Tous (0)');
assert.match(elements['favorite-agenda'].innerHTML,/Aucun match enregistré pour ce favori/);
favorites.pop();renderFavoriteAgenda();
assert.equal(favoriteAgendaSelection,'all');
favorites.pop();renderFavoriteAgenda();
assert.equal(elements['favorite-agenda-selection-label'].classList.hidden,true);
assert.equal(elements['favorite-selection-calendar'].classList.hidden,true);
assert.equal(elements['favorite-selection-calendar'].href,'#');
assert.deepEqual(savedViews.at(-1),[favoriteAgendaViewKey,{filter:'all',selection:'all'}]);
elements['favorite-agenda-filters'].onclick({target:{closest(){return buttons[1]}}});
assert.deepEqual(savedViews.at(-1),[favoriteAgendaViewKey,{filter:'live',selection:'all'}]);
elements['favorite-agenda-selection'].onchange({target:{value:'team:alpha:1'}});
assert.deepEqual(savedViews.at(-1),[favoriteAgendaViewKey,{filter:'live',selection:'team:alpha:1'}]);
assert.equal(elements['favorite-next'].innerHTML,'');
assert.equal(refreshCalls,1);
assert.equal(favoriteAgendaMatches.length,4);
"""
        result = subprocess.run(
            ["node", "-e", harness + companion.FAVORITE_AGENDA_SCRIPT
             + assertions], capture_output=True, text=True, encoding="utf-8",
            timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_selected_favorite_loads_its_own_feed_without_narrowing_alerts(self):
        page = companion.PAGE
        start = page.index("let favoriteSequence=0")
        end = page.index("$('favorite-alerts').onclick", start)
        harness = r"""
const assert=require('node:assert/strict');
const favorites=[
  {type:'team',external_id:'alpha',name:'Alpha'},
  {type:'competition',external_id:'cup',name:'Coupe'},
];
function favoriteId(item){return `${item.type}:${item.external_id}`}
const panel={classList:{add(){},remove(){}}};
const elements={
  'favorite-agenda-panel':panel,
  'favorite-agenda':{innerHTML:''},
  'favorite-calendar':{href:''},
};
function $(id){return elements[id]}
function empty(value){return value}
function syncFavoriteAgendaSelection(){}
const tracked=[],rendered=[],requests=[];
function trackFavoriteAlerts(rows){tracked.push(rows.map(row=>row.external_id))}
function renderFavoriteAgenda(){rendered.push({selection:favoriteAgendaSelection,ids:favoriteAgendaMatches.map(row=>row.external_id)})}
let delayTeam=false,resolveTeam,scopedStarted;
const teamStarted=new Promise(resolve=>scopedStarted=resolve);
function response(ids){return{ok:true,json:async()=>({matches:ids.map(external_id=>({external_id,spoiler_free:true}))})}}
async function fetch(url){
  requests.push(url);
  const query=new URL(url,'http://localhost').searchParams;
  if(query.has('team')&&query.has('competition'))return response(['global']);
  if(query.get('team')==='alpha'){
    if(delayTeam)return new Promise(resolve=>{resolveTeam=resolve;scopedStarted()});
    return response(['alpha-later']);
  }
  if(query.get('competition')==='cup')return response(['cup-later']);
  throw Error('Unexpected request: '+url);
}
"""
        assertions = r"""
async function main(){
  await refreshFavoriteMatches();
  assert.deepEqual(rendered.at(-1),{selection:'all',ids:['global']});
  assert.equal(requests.length,1);
  favoriteAgendaSelection='team:alpha';
  await refreshFavoriteMatches();
  assert.deepEqual(rendered.at(-1),{selection:'team:alpha',ids:['alpha-later']});
  assert.deepEqual(tracked,[['global'],['global']]);
  assert.match(elements['favorite-calendar'].href,/team=alpha&competition=cup/);
  assert.equal(requests.length,3);
  assert.match(requests.at(-1),/limit=20&team=alpha$/);
  delayTeam=true;
  const stale=refreshFavoriteMatches();
  await teamStarted;
  favoriteAgendaSelection='competition:cup';
  await refreshFavoriteMatches();
  resolveTeam(response(['obsolete']));
  await stale;
  assert.deepEqual(rendered.at(-1),{selection:'competition:cup',ids:['cup-later']});
  assert.deepEqual(favoriteAgendaMatches.map(row=>row.external_id),['cup-later']);
  assert.deepEqual(tracked.at(-1),['global']);
}
main().catch(error=>{console.error(error);process.exitCode=1});
"""
        result = subprocess.run(
            ["node", "-e", harness + page[start:end] + assertions],
            capture_output=True, text=True, encoding="utf-8", timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_saved_view_is_restored_only_when_valid(self):
        page = companion.PAGE
        start = page.index("const favoriteAgendaViewKey=")
        end = page.index("async function refreshFavoriteMatches", start)
        harness = r"""
const assert=require('node:assert/strict'),vm=require('node:vm');
function restored(saved){
  const context={localStorage:{getItem(){return saved}}};
  return JSON.parse(vm.runInNewContext(SOURCE+'\nJSON.stringify({filter:favoriteAgendaFilter,selection:favoriteAgendaSelection})',context));
}
assert.deepEqual(restored(JSON.stringify({filter:'upcoming',selection:'team:alpha'})),{filter:'upcoming',selection:'team:alpha'});
assert.deepEqual(restored(JSON.stringify({filter:'hidden',selection:'unknown'})),{filter:'all',selection:'all'});
assert.deepEqual(restored(JSON.stringify({filter:'live',selection:'team:'+('x'.repeat(251))})),{filter:'live',selection:'all'});
assert.deepEqual(restored('{bad json'),{filter:'all',selection:'all'});
"""
        source = page[start:end]
        result = subprocess.run(
            ["node", "-e", "const SOURCE=" + json.dumps(source)
             + ";\n" + harness], capture_output=True, text=True,
            encoding="utf-8", timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
