import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';
const source=readFileSync(new URL('../shared/design/v3/boot.js',import.meta.url),'utf8');
function run({search='',saved,blocked=false,project='news'}={}){
 const entries=new Map(saved===undefined?[]:[['quant-research-theme',saved]]),root={dataset:{theme:'light',quantDesignProject:project},style:{}},window={};
 const storage={getItem:k=>{if(blocked)throw Error('blocked');return entries.get(k)},setItem:(k,v)=>{if(blocked)throw Error('blocked');entries.set(k,v)}};
 vm.runInNewContext(source,{document:{documentElement:root},window,localStorage:storage,location:{search},URLSearchParams});return{root,entries,window};
}
test('fresh pages ignore legacy light markup and start dark',()=>{for(const project of ['news','factor','alpha-house','investment-journal']){const r=run({project});assert.equal(r.root.dataset.theme,'dark');assert.equal(r.root.style.colorScheme,'dark')}});
test('explicit light and dark preferences survive navigation and reload',()=>{for(const saved of ['light','dark']){const r=run({saved});assert.equal(r.root.dataset.theme,saved);assert.equal(r.entries.get('research-news-theme'),saved)}});
test('valid URL overrides a saved choice; invalid values never reset the choice',()=>{assert.equal(run({search:'?theme=light',saved:'dark'}).root.dataset.theme,'light');assert.equal(run({search:'?theme=invalid',saved:'dark'}).root.dataset.theme,'dark');assert.equal(run({saved:'unknown'}).root.dataset.theme,'dark')});
test('storage denial still permits dark default and explicit light',()=>{assert.equal(run({blocked:true}).root.dataset.theme,'dark');assert.equal(run({blocked:true,search:'?theme=light'}).root.dataset.theme,'light')});
test('late native defaults are reconciled before displaying the common shell',()=>{const r=run();r.root.dataset.theme='light';r.window.QuantDesignTheme.apply();assert.equal(r.root.dataset.theme,'dark')});
