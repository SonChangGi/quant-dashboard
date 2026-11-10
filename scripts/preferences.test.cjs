const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const source=fs.readFileSync('shared/preferences/1.0.1/preferences.js','utf8');
const {KEY,clean,merge,value,projectId,migrate,capsule}=require('../shared/preferences/1.0.1/preferences.js');
const field=(key,v,at=10,by='a')=>({v:1,fields:{[key]:{value:v,at,by}}});
test('stable project IDs accept only the ten trusted projects',()=>{
 assert.equal(projectId('https://sonchanggi.github.io/factor/?x=1'),'factor');
 assert.equal(projectId('https://invest.changgi-son.chatgpt.site/'),'investment-journal');
 for(const u of ['https://sonchanggi.github.io.evil.test/factor/','https://sonchanggi.github.io/unknown/','javascript:alert(1)','http://sonchanggi.github.io/factor/'])assert.equal(projectId(u),null);
});
test('legacy names and empty favorites migrate without resetting them',()=>{
 const data={'quant-ui-v04-favorites':'["Factor","SOX"]','quant-ui-v04-rail':'true'};
 const s=migrate(k=>data[k]??null,'legacy');assert(value(s,'favorite:factor'));assert(!value(s,'favorite:news'));assert(value(s,'rail'));
 const empty=migrate(k=>k==='quant-ui-v04-favorites'?'[]':null,'legacy');assert(!value(empty,'favorite:news'));
});
test('separate legacy lists preserve favorites then explicit removal wins',()=>{
 const a=migrate(k=>k==='quant-ui-v04-favorites'?'["Factor"]':null,'a');
 const b=migrate(k=>k==='quant-ui-v04-favorites'?'["SOX"]':null,'b');
 const both=merge(a,b);assert(value(both,'favorite:factor'));assert(value(both,'favorite:sox'));
 assert(!value(merge(both,field('favorite:sox',false,20)),'favorite:sox'));
});
test('per-field merge retains independent edits and ignores stale changes',()=>{
 const s=merge(field('rail',true,20),field('density','compact',21));
 const r=merge(s,field('rail',false,10));assert(value(r,'rail'));assert.equal(value(r,'density'),'compact');
 assert.deepEqual(merge(field('rail',true,10,'z'),field('rail',false,10,'a')),field('rail',true,10,'z'));
});
test('incoming data rejects unsupported settings and forged clocks',()=>{
 const s=clean({v:1,fields:{...field('theme','light').fields,...field('token','secret').fields,...field('rail','yes').fields,...field('density','compact',Date.now()+999999).fields}});
 assert.deepEqual(Object.keys(s.fields),['theme']);
 assert.deepEqual(clean({v:2,fields:{}}),{v:1,fields:{}});
 assert.equal(capsule('x'.repeat(6001)),null);assert.equal(capsule('bad'),null);
});
function browser(origin,shared=new Map(),hash=''){
 const docEvents={},events={},root={dataset:{},style:{}},location=new URL(origin+hash);
 const document={documentElement:root,readyState:'loading',body:{},addEventListener:(k,f,options)=>{(docEvents[k]??=[]).push({f,capture:options===true})},querySelector:()=>null,querySelectorAll:()=>[]};
 const context={document,location,URL,localStorage:{getItem:k=>shared.get(k)??null,setItem:(k,v)=>shared.set(k,v)},history:{state:null,replaceState(_a,_b,u){context.location=new URL(u)}},crypto:{randomUUID:()=>origin},structuredClone,atob,btoa,console,Event,Date,Math,queueMicrotask,dispatchEvent(){},MutationObserver:class{observe(){}},addEventListener:(k,f)=>events[k]=f};
 context.window=context;vm.runInNewContext(source,context);
 return {context,events,docEvents,shared,api:context.QuantPreferences};
}
test('same-origin storage and focus reconcile without reload',()=>{
 const shared=new Map(),a=browser('https://sonchanggi.github.io/factor/',shared),b=browser('https://sonchanggi.github.io/news/',shared);
 a.api.set('favorite:factor',true);b.events.storage({key:KEY});assert(value(b.api.get(),'favorite:factor'));
 b.api.set('rail',true);a.events.focus();assert(value(a.api.get(),'rail'));
 b.api.set('favorite:factor',false);a.events.storage({key:KEY});assert(!value(a.api.get(),'favorite:factor'));
});
test('cross-origin capsule restores before first paint and retains original anchor',()=>{
 const a=browser('https://sonchanggi.github.io/factor/');a.api.set('favorite:factor',true);a.api.set('density','compact');
 const payload=btoa(JSON.stringify({...a.api.get(),anchor:'#positions'}));
 const b=browser('https://invest.changgi-son.chatgpt.site/',new Map(),'#qp='+payload);
 assert.equal(b.context.location.hash,'#positions');assert.equal(b.shared.get('quant-ui-v04-density'),'"compact"');assert(value(b.api.get(),'favorite:factor'));
 assert(!b.context.location.href.includes('qp='));
});
test('blocked storage leaves usable in-memory preferences',()=>{
 const b=browser('https://sonchanggi.github.io/news/');b.context.localStorage.setItem=()=>{throw Error('blocked')};b.api.set('rail',true);assert(value(b.api.get(),'rail'));
});
test('native picker reopening cannot redraw stale favorites',()=>{
 const b=browser('https://sonchanggi.github.io/quant-dashboard/');
 const group={children:[],replaceChildren(...nodes){this.children=nodes},append(n){this.children.push(n)}};
 const factor={href:'https://sonchanggi.github.io/factor/',hidden:false,cloneNode(){return {href:this.href,hidden:this.hidden}}};
 const doc=b.context.document;doc.createElement=()=>({});
 doc.querySelector=s=>s==='.q4-favorites'?group:null;
 doc.querySelectorAll=s=>s==='.qd-nav-group:not(.q4-favorites)>a'?[factor]:[];
 b.events['quant-design-ready']();b.api.set('favorite:factor',true);
 assert.equal(group.children.length,2);
 // The existing shell's picker onclick redraws from its initial favorites.
 group.replaceChildren({textContent:'즐겨찾기'});factor.hidden=false;
 for(const {f,capture} of b.docEvents.click)if(!capture)f({target:{closest:s=>s==='.q4-picker'?{}:null}});
 assert.equal(group.children.length,2);assert.equal(factor.hidden,true);
});
