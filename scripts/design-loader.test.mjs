import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';
const source=readFileSync(new URL('../shared/navigation/v1/nav.js',import.meta.url),'utf8').split('/* Shared presentation layer.')[1];
const loader='/* Shared presentation layer.'+source;
async function run({path='/',host='sonchanggi.github.io',project,fail=false}={}){
 const nodes=[],root={dataset:{}},window={dispatchEvent(){}};
 const document={readyState:'complete',currentScript:{src:'https://sonchanggi.github.io/quant-dashboard/shared/navigation/v1/nav.js'},documentElement:root,querySelector:s=>s==='[data-quant-project]'&&project?{dataset:{quantProject:project}}:null,createElement:tag=>({tag,remove(){this.removed=true}}),head:{append(node){nodes.push(node);queueMicrotask(()=>fail?node.onerror?.():node.onload?.())}}};
 vm.runInNewContext(loader,{document,window,location:{pathname:path,hostname:host},URL,CustomEvent:class{},Promise});
 await new Promise(r=>setTimeout(r,10));return{nodes,window,root};
}
test('every current project and legacy alias resolves to its production design',async()=>{
 const cases={hub:'quant-dashboard',momentum:'factor',factor:'factor',regime:'regime',fearngreed:'fearNgreed','fear-greed':'fearNgreed',dram:'dram-price',sox:'sox',etf:'etf-tracking',news:'news',observatory:'alpha-house','investment-journal':'investment-journal'};
 for(const [project,expected] of Object.entries(cases)){const r=await run({project});assert.equal(r.window.__quantDesignV3.project,expected);assert.equal(r.window.__quantDesignV3.state,'ready');assert(r.nodes.filter(n=>n.tag==='link').every(n=>n.media==='all'));assert(r.nodes.every(n=>String(n.href||n.src).startsWith('https://sonchanggi.github.io/quant-dashboard/shared/design/v3/')))}
});
test('Alpha House host resolves at root and nested pages without nav dataset',async()=>{for(const path of ['/','/projects/example']){const r=await run({path,host:'alpha-house.changgi-son.chatgpt.site'});assert.equal(r.window.__quantDesignV3.project,'alpha-house')}});
test('failed styles leave the original navigation visible without adding a shell',async()=>{const r=await run({project:'news',fail:true});assert.equal(r.window.__quantDesignV3.state,'error');assert(r.nodes.filter(n=>n.tag==='link').every(n=>n.removed));assert(!r.nodes.some(n=>String(n.src).endsWith('/shell.js')))});
test('unrelated pages are left untouched',async()=>{const r=await run({path:'/unknown/'});assert.equal(r.window.__quantDesignV3,undefined);assert.equal(r.nodes.length,0)});

test('investment journal host always resolves its design on login and nested pages',async()=>{
 for(const path of ['/','/login','/accounts/example','/transactions/2026']){
  const r=await run({path,host:'invest.changgi-son.chatgpt.site'});
  assert.equal(r.window.__quantDesignV3.project,'investment-journal');assert.equal(r.window.__quantDesignV3.state,'ready');
  assert(r.nodes.some(node=>String(node.href).endsWith('/investment-journal.css')));
  assert(!r.nodes.some(node=>String(node.href).endsWith('/alpha.css')));
 }
});
test('shell keeps all existing projects and includes journal once in the market group',()=>{
 const shell=readFileSync(new URL('../shared/design/v3/shell.js',import.meta.url),'utf8');
 const projects=vm.runInNewContext(shell.match(/const projects=(\[.*?\]);/)[1]);
 assert.deepEqual(Array.from(projects,row=>row[0]),['quant-dashboard','factor','fearNgreed','regime','dram-price','sox','etf-tracking','news','investment-journal','alpha-house']);
 const groups=[...shell.matchAll(/groupItems\((\[.*?\])\)/g)].flatMap(match=>Array.from(vm.runInNewContext(match[1])));
 assert.equal(groups.length,9);assert.equal(new Set(groups).size,9);
 assert.deepEqual([...groups].sort(),Array.from(projects.slice(1),row=>row[0]).sort());
 assert(shell.includes("'https://invest.changgi-son.chatgpt.site/'"));
});
