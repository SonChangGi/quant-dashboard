import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';
const code=readFileSync(new URL('../shared/design/startup/1.0.0/start.js',import.meta.url),'utf8');
function setup({search='',stored='dark',sheet=true,storageThrows=false,bodyNow=true}={}){
 const root={dataset:{},style:{}},classes=new Set(['native']),body={dataset:{},classList:{contains:v=>classes.has(v),add:(...v)=>v.forEach(c=>classes.add(c)),remove:(...v)=>v.forEach(c=>classes.delete(c))}};
 const observers=[],timers=[];const win={};
 const document={documentElement:root,currentScript:{dataset:{quantDesignProject:'factor'},src:'https://sonchanggi.github.io/quant-dashboard/shared/design/startup/1.0.0/start.js'},body:bodyNow?body:null,querySelector:()=>({sheet:sheet?{}:null}),querySelectorAll:()=>[]};
 const context={window:win,document,URL,URLSearchParams,CSSScopeRule:class{},location:{search},localStorage:{getItem:key=>{if(storageThrows)throw Error('denied');return key==='quant-research-theme'?stored:null},setItem(){}},MutationObserver:class{constructor(fn){this.fn=fn;observers.push(this)}observe(){}disconnect(){this.stopped=true}},setTimeout:fn=>{timers.push(fn);return timers.length},clearTimeout(){}};
 vm.runInNewContext(code,context);return {win,root,document,body,classes,observers,timers,context};
}
test('first body insertion gets final scopes before interaction initialization',()=>{const r=setup({bodyNow:false,search:'?theme=light',stored:'dark'});assert.equal(r.root.dataset.theme,'light');assert.equal(r.root.dataset.quantPaint,'loading');r.document.body=r.body;r.observers[0].fn();assert(r.classes.has('qd-v04'));assert.equal(r.body.dataset.qdProject,'factor');assert.equal(r.win.__quantDesignUnified,undefined);r.win.QuantFirstPaint.finish();assert.equal(r.root.dataset.quantPaint,'ready')});
test('storage unavailable retains a usable dark initial theme',()=>{const r=setup({storageThrows:true});assert.equal(r.root.dataset.theme,'dark');r.win.QuantFirstPaint.finish();assert(r.classes.has('native'))});
test('failed critical CSS leaves the native application untouched',()=>{const r=setup({sheet:false});assert.equal(r.win.QuantFirstPaint,undefined);assert.deepEqual([...r.classes],['native']);assert.equal(r.root.dataset.quantStartup,undefined)});
test('runtime failure restores native scope and exposes fallback without losing native classes',()=>{const r=setup();r.win.__quantDesignV3={state:'loading'};r.win.QuantFirstPaint.fail('runtime-network');assert.equal(r.root.dataset.quantStartup,undefined);assert.deepEqual([...r.classes],['native']);assert.equal(r.win.__quantDesignV3.state,'error');assert.equal(r.win.QuantFirstPaint.state,'fallback')});
test('late runtime cannot mutate a page after timeout fallback',()=>{const r=setup();r.timers[0]();const runtime=readFileSync(new URL('../shared/design/startup/1.0.0/runtime.js',import.meta.url),'utf8');vm.runInNewContext(runtime,r.context);assert.equal(r.win.QuantFirstPaint.state,'fallback');assert.deepEqual([...r.classes],['native'])});
