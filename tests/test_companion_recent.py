"""Local recent-view shortcuts and Explorer keyboard behaviour."""

import json
import shutil
import subprocess
import unittest

from butbutbut import companion


@unittest.skipUnless(shutil.which("node"), "Node.js unavailable")
class TestRecentViews(unittest.TestCase):
    def run_node(self, script):
        result = subprocess.run(
            ["node", "-e", script], capture_output=True, text=True,
            encoding="utf-8", timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_recent_views_are_validated_deduplicated_and_capped(self):
        harness = r"""
const assert=require('node:assert/strict');
const initial=[
  {type:'team',external_id:'alpha',name:'Alpha'},
  {type:'team',external_id:'alpha',name:'Duplicate'},
  {type:'match',external_id:'bad\nvalue',name:'Invalid'},
  ...Array.from({length:9},(_,i)=>({type:'match',external_id:String(i),name:`Match ${i}`})),
];
const values=new Map([['butbutbut:recent-views:v1',JSON.stringify(initial)]]);
let writes=0;
const localStorage={getItem(key){return values.get(key)||null},setItem(key,value){writes++;values.set(key,value)}};
"""
        assertions = r"""
assert.equal(readRecentViews().length,8);
assert.equal(readRecentViews()[0].name,'Alpha');
assert.equal(readRecentViews().some(row=>row.external_id==='bad\nvalue'),false);
rememberRecentView({type:'competition',external_id:'cup',name:'Coupe'});
assert.equal(readRecentViews()[0].name,'Coupe');
assert.equal(readRecentViews().length,8);
rememberRecentView({type:'match',external_id:'another',name:'Another'});
assert.equal(writes,1);
assert.equal(readRecentViews()[0].name,'Coupe');
"""
        self.run_node(harness + companion.RECENT_VIEWS_SCRIPT + assertions)

    def test_home_shortcuts_favorite_buttons_and_keyboard(self):
        harness = r"""
const assert=require('node:assert/strict');
const rows=[
  {type:'team',external_id:'alpha',name:'Alpha & <Friends>'},
  {type:'match',external_id:'m1',name:'Alpha – Beta'},
];
const values=new Map([['butbutbut:recent-views:v1',JSON.stringify(rows)]]);
const localStorage={getItem(key){return values.get(key)||null},setItem(key,value){values.set(key,value)}};
const elements={
  'recent-panel':{classList:{toggle(name,hidden){this.hidden=hidden}}},
  'recent-views':{innerHTML:''},
  search:{value:'old',addEventListener(name,handler){this[name]=handler},focus(){this.focused=true},blur(){this.focused=false}},
};
function $(id){return elements[id]}
function esc(value){return String(value).replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]))}
const favorites=[];
const favoriteKey='butbutbut:favorites:v1';
function isFavorite(row){return favorites.some(item=>item.external_id===row.external_id)}
let selected;
function toggleFavorite(row){selected=row}
function saveFavorites(){}
let searchTimer=0,searchSequence=0,searchRows=[1],searchRenders=0;
function renderSearch(){searchRenders++}
const storageHandlers=[],keyHandlers=[];
const window={addEventListener(name,handler){if(name==='storage')storageHandlers.push(handler)}};
const document={addEventListener(name,handler){if(name==='keydown')keyHandlers.push(handler)}};
"""
        assertions = r"""
assert.equal(elements['recent-panel'].classList.hidden,false);
const html=elements['recent-views'].innerHTML;
assert.match(html,/Alpha &amp; &lt;Friends&gt;/);
assert.match(html,/\/team\?id=alpha/);
assert.match(html,/\/match\?id=m1/);
assert.equal((html.match(/data-recent-favorite=/g)||[]).length,1);
elements['recent-views'].onclick({target:{closest(){return{dataset:{recentFavorite:encodeURIComponent(JSON.stringify(rows[0]))}}}}});
assert.deepEqual(selected,rows[0]);
let prevented=false;
keyHandlers[0]({key:'/',target:{closest(){return null}},preventDefault(){prevented=true}});
assert.equal(prevented,true);
assert.equal(elements.search.focused,true);
elements.search.focused=false;
keyHandlers[0]({key:'/',target:{closest(){return{}}},preventDefault(){throw Error('must not prevent')}});
assert.equal(elements.search.focused,false);
elements.search.keydown({key:'Escape'});
assert.equal(elements.search.value,'');
assert.equal(searchSequence,1);
assert.deepEqual(searchRows,[]);
assert.equal(searchRenders,1);
assert.equal(elements.search.focused,false);
"""
        self.run_node(harness + companion.RECENT_VIEWS_SCRIPT
                      + companion.RECENT_HOME_SCRIPT + assertions)

    def test_detail_wrappers_record_names_without_scores(self):
        scripts = (
            (companion.MATCH_RECENT_SCRIPT, {
                "match": {"external_id": "m1", "home_score": 4,
                          "away_score": 2, "home_team": {"name": "Alpha"},
                          "away_team": {"name": "Beta"}}},
             {"type": "match", "external_id": "m1",
              "name": "Alpha – Beta"}),
            (companion.TEAM_RECENT_SCRIPT,
             {"team": {"external_id": "alpha", "name": "Alpha"}},
             {"type": "team", "external_id": "alpha", "name": "Alpha"}),
            (companion.COMPETITION_RECENT_SCRIPT,
             {"competition": {"external_id": "cup", "name": "Coupe"}},
             {"type": "competition", "external_id": "cup", "name": "Coupe"}),
        )
        for script, payload, expected in scripts:
            with self.subTest(type=expected["type"]):
                harness = (
                    "const assert=require('node:assert/strict');"
                    "let captured;function render(){}"
                    "function rememberRecentView(row){captured=row;}"
                )
                assertions = ("render(" + json.dumps(payload)
                              + ");assert.deepEqual(captured,"
                              + json.dumps(expected, ensure_ascii=False)
                              + ");")
                self.run_node(harness + script + assertions)


if __name__ == "__main__":
    unittest.main()
