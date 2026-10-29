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
 const cases={hub:'quant-dashboard',momentum:'factor',factor:'factor',regime:'regime',fearngreed:'fearNgreed','fear-greed':'fearNgreed',dram:'dram-price',sox:'sox',etf:'etf-tracking',news:'news',observatory:'alpha-house'};
 for(const [project,expected] of Object.entries(cases)){const r=await run({project});assert.equal(r.window.__quantDesignV3.project,expected);assert.equal(r.window.__quantDesignV3.state,'ready');assert(r.nodes.filter(n=>n.tag==='link').every(n=>n.media==='all'));assert(r.nodes.every(n=>String(n.href||n.src).startsWith('https://sonchanggi.github.io/quant-dashboard/shared/design/v3/')))}
});
test('Alpha House host resolves at root and nested pages without nav dataset',async()=>{for(const path of ['/','/projects/example']){const r=await run({path,host:'alpha-house.changgi-son.chatgpt.site'});assert.equal(r.window.__quantDesignV3.project,'alpha-house')}});
test('failed styles leave the original navigation visible without adding a shell',async()=>{const r=await run({project:'news',fail:true});assert.equal(r.window.__quantDesignV3.state,'error');assert(r.nodes.every(n=>n.tag==='link'&&n.removed))});
test('unrelated pages are left untouched',async()=>{const r=await run({path:'/unknown/'});assert.equal(r.window.__quantDesignV3,undefined);assert.equal(r.nodes.length,0)});
