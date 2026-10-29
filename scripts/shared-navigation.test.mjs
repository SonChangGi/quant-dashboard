import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createRequire} from 'node:module';
import {execFileSync} from 'node:child_process';
const require=createRequire(import.meta.url);
const api=require('../shared/navigation/v1/nav.js');
const source=JSON.parse(fs.readFileSync(new URL('../shared/navigation/v1/menu.json',import.meta.url),'utf8'));
test('all generated navigation fallbacks match the central source',()=>{
 assert.deepEqual(api.fallbackMenu,source);
 assert.deepEqual(source.projects.map(project=>project.id),['factor','dram','etf','sox','fear-greed','regime','news','investment-journal','observatory']);
 assert.equal(source.projects.find(p=>p.id==='factor').url,'https://sonchanggi.github.io/factor/');
 assert(!source.projects.some(p=>p.id==='best-factor'||p.id==='spo'));
 assert(!JSON.stringify(api.fallbackMenu).includes('/SPO/'));
 execFileSync(process.execPath,['scripts/sync-navigation.mjs','--check']);
});
test('rejects duplicate ids, unsafe URLs, retired links and invalid labels before replacing a menu',()=>{
 for(const mutate of [m=>m.projects.push(m.projects[0]),m=>m.projects[0].url='javascript:alert(1)',m=>m.projects[0].url='https://example.com/track/',m=>m.projects[0].url='https://sonchanggi.github.io/best-factor/',m=>m.projects[0].label='<img>',m=>m.projects[0].id='best-factor',m=>m.brand.url='https://sonchanggi.github.io/another/']){
  const changed=structuredClone(source);mutate(changed);assert.throws(()=>api.validateMenu(changed));
 }
 assert.deepEqual(api.fallbackMenu,source);
});
test('loads new central menu data without reinterpreting calculation ids',async()=>{
 const changed=structuredClone(source);changed.projects[0].label='Fear & Greed Flow';let options;
 const loaded=await api.loadMenu(async(url,request)=>{assert.equal(url,api.menuUrl);options=request;return {ok:true,text:async()=>JSON.stringify(changed)};});
 assert.equal(loaded.projects[0].label,'Fear & Greed Flow');assert.equal(options.credentials,'omit');assert.equal(options.cache,'no-cache');
 assert.equal(api.getLinks(loaded,'momentum').find(p=>p.current).id,'factor');
});
test('a stalled transport or response body has a bounded deadline',async()=>{
 await assert.rejects(api.loadMenu(()=>new Promise(()=>{}),10),/timeout/);
 await assert.rejects(api.loadMenu(async()=>({ok:true,text:()=>new Promise(()=>{})}),10),/timeout/);
 await assert.rejects(api.loadMenu(async()=>({ok:true,text:async()=>JSON.stringify({})})),/schema/);
 assert.deepEqual(api.fallbackMenu,source);
});

test('future projects follow the latest project while Alpha House remains last',()=>{
 const changed=structuredClone(source);
 changed.projects.splice(-1,0,{id:'next-project',label:'Next project',url:'https://sonchanggi.github.io/next-project/'});
 const links=api.getLinks(api.validateMenu(changed),'next-project');
 assert.deepEqual(links.slice(-3).map(project=>project.id),['investment-journal','next-project','observatory']);
 assert.equal(links.find(project=>project.current).id,'next-project');
});

test('investment journal keeps its authenticated site URL and rejects credentials or token queries',()=>{
 const journal=api.getLinks(source,'investment-journal').find(project=>project.current);
 assert.equal(journal.url,'https://invest.changgi-son.chatgpt.site/');
 for(const url of ['https://user:secret@invest.changgi-son.chatgpt.site/','https://invest.changgi-son.chatgpt.site/?token=secret','https://invest.changgi-son.chatgpt.site.evil.example/']){
  const changed=structuredClone(source);changed.projects.find(project=>project.id==='investment-journal').url=url;assert.throws(()=>api.validateMenu(changed));
 }
});
