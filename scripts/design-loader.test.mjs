import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';
const source=readFileSync(new URL('../shared/navigation/v1/nav.js',import.meta.url),'utf8').split('/* Shared presentation layer.')[1];
const loader='/* Shared presentation layer.'+source;
async function run({path='/',host='sonchanggi.github.io',project,fail=false,early=false,modern=false,earlyState="loading"}={}){
 const nodes=[],root={dataset:{}},window={dispatchEvent(){}},footer={textContent:'Quant Research · v0.4'};
 if(early)window.QuantFirstPaint={styleReady:true,state:earlyState,project,base:'https://sonchanggi.github.io/quant-dashboard/shared/design/startup/1.2.0/',fail(reason){this.state='fallback';this.reason=reason}};
 const document={readyState:'complete',currentScript:{src:'https://sonchanggi.github.io/quant-dashboard/shared/navigation/v1/nav.js'},documentElement:root,querySelector:s=>s==='link[data-quant-first-paint-css]'&&modern?{}:s==='.qd-side-footer small'?footer:s==='[data-quant-project]'&&project?{dataset:{quantProject:project}}:null,createElement:tag=>({tag,remove(){this.removed=true}}),head:{append(node){nodes.push(node);queueMicrotask(()=>(fail)?node.onerror?.():node.onload?.())}}};
 vm.runInNewContext(loader,{document,window,location:{pathname:path,hostname:host},URL,CustomEvent:class{},Promise});
 await new Promise(r=>setTimeout(r,10));return{nodes,window,root,footer};
}
test('all ten projects use only their prepared runtime',async()=>{
 for(const project of ['quant-dashboard','factor','regime','fearNgreed','etf-tracking','dram-price','sox','news','alpha-house','investment-journal']){
  const r=await run({project,early:true});assert.equal(r.nodes.length,1);assert.equal(r.nodes[0].tag,'script');assert(String(r.nodes[0].src).endsWith('/startup/1.2.0/runtime.js'));assert.equal(r.window.__quantDesignV3.state,'loading');
 }
});
test('missing startup never falls back to a retired dynamic design',async()=>{
 for(const project of ['hub','momentum','factor','regime','fearngreed','fear-greed','dram','sox','etf','news','observatory','investment-journal']){
  const r=await run({project});assert.equal(r.nodes.length,0);assert.equal(r.window.__quantDesignV3.state,'error');assert.equal(r.window.__quantDesignUnified,undefined);
 }
});
test('native host routing remains available without historical bundle requests',async()=>{
 for(const host of ['alpha-house.changgi-son.chatgpt.site','invest.changgi-son.chatgpt.site'])for(const path of ['/','/login','/accounts/example']){
  const r=await run({host,path});assert.equal(r.nodes.length,0);assert.equal(r.window.__quantDesignV3.project,host.startsWith('invest.')?'investment-journal':'alpha-house');
 }
});
test('unrelated pages are left untouched',async()=>{const r=await run({path:'/unknown/'});assert.equal(r.window.__quantDesignV3,undefined);assert.equal(r.nodes.length,0)});
test('runtime network failure restores the native fallback',async()=>{const r=await run({project:'factor',early:true,fail:true});assert.equal(r.window.QuantFirstPaint.state,'fallback');assert.equal(r.window.QuantFirstPaint.reason,'runtime-network');assert.equal(r.window.__quantDesignV3.state,'error')});
test('late navigation cannot revive a timed-out design',async()=>{const r=await run({project:'factor',early:true,earlyState:'fallback',modern:true});assert.equal(r.nodes.length,0);assert.equal(r.window.__quantDesignV3.state,'error')});
test('missing modern startup makes no additional presentation requests',async()=>{const r=await run({project:'factor',modern:true});assert.equal(r.nodes.length,0);assert.equal(r.window.__quantDesignV3.state,'error')});
test('shell keeps all existing projects and includes journal once in the market group',()=>{
 const shell=readFileSync(new URL('../shared/design/releases/0.5.0/foundation/shell.js',import.meta.url),'utf8');
 const projects=vm.runInNewContext(shell.match(/const projects=(\[.*?\]);/)[1]);
 assert.deepEqual(Array.from(projects,row=>row[0]),['quant-dashboard','factor','fearNgreed','regime','dram-price','sox','etf-tracking','news','investment-journal','alpha-house']);
 const groups=[...shell.matchAll(/groupItems\((\[.*?\])\)/g)].flatMap(match=>Array.from(vm.runInNewContext(match[1])));
 assert.equal(groups.length,9);assert.equal(new Set(groups).size,9);
 assert.deepEqual([...groups].sort(),Array.from(projects.slice(1),row=>row[0]).sort());
 assert(shell.includes("'https://invest.changgi-son.chatgpt.site/'"));
});

test('production v0.4 assets exclude local routing and preserve native data ownership',()=>{
 for(const name of ['v04.js','v04.css','v04-finance.css','v04-editorial.css']){
  const asset=readFileSync(new URL('../shared/design/releases/0.5.0/foundation/'+name,import.meta.url),'utf8');
  assert(!/QuantPreview|127\.0\.0\.1|localhost|design=baseline|quant-preview-|로컬 미리보기/.test(asset),name);
  assert(!/\bfetch\s*\(|XMLHttpRequest|serviceWorker/.test(asset),name);
 }
});

