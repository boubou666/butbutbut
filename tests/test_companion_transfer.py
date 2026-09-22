"""Browser-side favourite backup contract, exercised without a browser."""

import shutil
import subprocess
import unittest

from butbutbut import companion


@unittest.skipUnless(shutil.which("node"), "Node.js unavailable")
class TestFavoriteTransfer(unittest.TestCase):
    def test_json_round_trip_and_rejected_imports(self):
        harness = r"""
const assert = require('node:assert/strict');
const elements = {
  'favorite-export': {},
  'favorite-import-file': {},
  'favorite-transfer-status': {textContent: ''},
};
function $(id){return elements[id]}
function favoriteId(row){return `${row.type}:${row.external_id}`}
const favoriteKey = 'butbutbut:favorites:v1';
let favorites = [{type:'team',external_id:'alpha',name:'Alpha'}];
let stored = '', saves = 0, renders = 0, refreshes = 0, download = null;
const localStorage = {setItem(_key,value){stored=value}};
function saveFavorites(){saves++}
function renderFavorites(){renders++}
function renderSearch(){}
function refreshFavoriteMatches(){refreshes++}
const listeners = {};
const window = {addEventListener(type,callback){listeners[type]=callback}};
const document = {
  body:{append(){}},
  createElement(){return {click(){download={name:this.download,href:this.href}},remove(){}}},
};
const URL = {createObjectURL(blob){URL.blob=blob;return 'blob:local'},revokeObjectURL(){}};
const setTimeout = () => 0;
"""
        assertions = r"""
async function run(){
  exportFavorites();
  assert.equal(download.name,'butbutbut-favoris.json');
  assert.deepEqual(JSON.parse(await URL.blob.text()),{
    version:1,favorites:[{
      type:'team',external_id:'alpha',name:'Alpha',short_name:'',country_code:''
    }]
  });
  const file = value => ({size:100,text:async()=>JSON.stringify(value)});
  await importFavorites(file({version:1,favorites:[
    {type:'team',external_id:'alpha',name:'Autre nom'},
    {type:'competition',external_id:'cup',name:'Coupe'},
    {type:'competition',external_id:'cup',name:'Doublon'},
  ]}));
  assert.equal(favorites.length,2);
  assert.equal(favorites[0].name,'Alpha');
  assert.equal(favorites[1].name,'Coupe');
  assert.equal(saves,1);
  assert.equal(JSON.parse(stored).length,2);
  await importFavorites(file({version:2,favorites:[]}));
  assert.equal(favorites.length,2);
  assert.match($('favorite-transfer-status').textContent,/Format/);
  await importFavorites(file({version:1,favorites:[
    {type:'team',external_id:'x',name:'Nom\nmalveillant'}
  ]}));
  assert.equal(favorites.length,2);
  assert.match($('favorite-transfer-status').textContent,/invalide/);
  await importFavorites({size:65537,text:async()=>''});
  assert.equal(favorites.length,2);
  assert.match($('favorite-transfer-status').textContent,/volumineux/);
  favorites = Array.from({length:20},(_,i)=>({
    type:'team',external_id:String(i),name:String(i)
  }));
  await importFavorites(file({version:1,favorites:[
    {type:'team',external_id:'extra',name:'Extra'}
  ]}));
  assert.equal(favorites.length,20);
  assert.match($('favorite-transfer-status').textContent,/20 favoris/);
  const savesBeforeSync=saves;
  listeners.storage({key:favoriteKey,newValue:JSON.stringify([
    {type:'team',external_id:'beta',name:'Beta'}
  ])});
  assert.equal(favorites.length,1);
  assert.equal(favorites[0].external_id,'beta');
  assert.equal(saves,savesBeforeSync);
  assert.equal(renders,1);
  assert.equal(refreshes,1);
}
run().catch(error=>{console.error(error);process.exitCode=1});
"""
        result = subprocess.run(
            ["node", "-e", harness + companion.FAVORITES_TRANSFER_SCRIPT
             + assertions], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
