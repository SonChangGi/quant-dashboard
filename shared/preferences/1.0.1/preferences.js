/* Quant preferences 1.0.1: browser-local state and trusted project-link handoff. */
(function(scope){
'use strict';
const KEY='quant-preferences-v1';
const projects=[['quant-dashboard','대시보드'],['investment-journal','투자일지'],['factor','Factor'],['fearNgreed','Fear & Greed'],['regime','Regime'],['etf-tracking','ETF'],['dram-price','DRAM'],['sox','SOX'],['news','뉴스 브리핑'],['alpha-house','Alpha House']];
const defaults={'theme':'dark','density':'comfortable','rail':false};
const defaultFavorites=['quant-dashboard','investment-journal','news'];
const legacy={theme:'quant-research-theme',density:'quant-ui-v04-density',rail:'quant-ui-v04-rail'};
const ids=projects.map(p=>p[0]);
function allowed(key,value){return key==='theme'?['dark','light'].includes(value):key==='density'?['comfortable','compact'].includes(value):key==='rail'||(key.startsWith('favorite:')&&ids.includes(key.slice(9)))?typeof value==='boolean':false}
function clean(input,now=Date.now()){
 const fields={};
 if(!input||input.v!==1||!input.fields||typeof input.fields!=='object')return {v:1,fields};
 for(const [key,row] of Object.entries(input.fields)){
  if(!row||!allowed(key,row.value)||!Number.isSafeInteger(row.at)||row.at<0||row.at>now+300000||typeof row.by!=='string'||row.by.length>80)continue;
  fields[key]={value:row.value,at:row.at,by:row.by};
 }
 return {v:1,fields};
}
function merge(a,b){
 const fields={...a.fields};
 for(const [key,row] of Object.entries(b.fields)){
  const old=fields[key];
  // On first migration preserve favorites from both sites; subsequent explicit removals win by revision.
  const legacyFavorite=old&&key.startsWith('favorite:')&&old.at===0&&row.at===0;
  if(!old||row.at>old.at||(row.at===old.at&&(legacyFavorite?row.value&&!old.value:row.by>old.by)))fields[key]=row;
 }
 return {v:1,fields};
}
function value(state,key){return state.fields[key]?.value??(key.startsWith('favorite:')?defaultFavorites.includes(key.slice(9)):defaults[key])}
function projectId(url){
 let u;try{u=new URL(url)}catch{return null}
 if(u.protocol!=='https:')return null;
 if(u.origin==='https://invest.changgi-son.chatgpt.site')return 'investment-journal';
 if(u.origin==='https://alpha-house.changgi-son.chatgpt.site')return 'alpha-house';
 if(u.origin==='https://sonchanggi.github.io'){const id=u.pathname.split('/')[1];if(ids.includes(id)&&!['investment-journal','alpha-house'].includes(id))return id}
 return null;
}
function migrate(get,origin){
 const fields={};
 for(const [key,name] of Object.entries(legacy)){
  let v=get(name);if(key!=='theme'){try{v=JSON.parse(v)}catch{continue}}
  if(allowed(key,v))fields[key]={value:v,at:0,by:origin};
 }
 let favorites;try{favorites=JSON.parse(get('quant-ui-v04-favorites'))}catch{}
 if(Array.isArray(favorites))for(const [id,name] of projects)fields['favorite:'+id]={value:favorites.includes(name),at:0,by:origin};
 return {v:1,fields};
}
function capsule(raw){
 if(raw.length>6000)return null;
 try{const data=JSON.parse(atob(raw.replace(/-/g,'+').replace(/_/g,'/')));if(typeof data.anchor!=='string'||data.anchor.length>2048||data.anchor&&data.anchor[0]!=='#')return null;return {state:clean(data),anchor:data.anchor}}catch{return null}
}
const core={KEY,projects,clean,merge,value,projectId,migrate,capsule};
if(typeof module!=='undefined'&&module.exports)module.exports=core;
if(!scope.document||scope.QuantPreferences)return;
const doc=scope.document,root=doc.documentElement;
const get=key=>{try{return localStorage.getItem(key)}catch{return null}};
const put=(key,v)=>{try{if(localStorage.getItem(key)!==v)localStorage.setItem(key,v)}catch{}};
const writer=scope.crypto?.randomUUID?.()||Math.random().toString(36).slice(2);
const parse=s=>{try{return clean(JSON.parse(s))}catch{return clean(null)}};
let state=get(KEY)?parse(get(KEY)):migrate(get,location.origin),mounted=false,records=[];
if(location.hash.startsWith('#qp=')){
 const incoming=capsule(location.hash.slice(4));
 if(incoming){state=merge(state,incoming.state);const u=new URL(location.href);u.hash=incoming.anchor;u.searchParams.set('theme',value(state,'theme'));history.replaceState(history.state,'',u)}
}
function persist(){
 put(KEY,JSON.stringify(state));
 for(const [key,name] of Object.entries(legacy))put(name,key==='theme'?value(state,key):JSON.stringify(value(state,key)));
 put('quant-ui-v04-favorites',JSON.stringify(projects.filter(([id])=>value(state,'favorite:'+id)).map(p=>p[1])));
}
// Restore before the existing first-paint/native scripts read their compatible keys.
persist();
function change(key,v){
 if(!allowed(key,v))return;
 const latest=parse(get(KEY));state=merge(state,latest);
 if(value(state,key)===v)return;
 const at=Math.max(Date.now(),...Object.values(state.fields).map(r=>r.at+1));
 state.fields[key]={value:v,at,by:writer};persist();render();
}
function readRemote(){const next=merge(state,parse(get(KEY)));if(JSON.stringify(next)!==JSON.stringify(state)){state=next;persist();render()}}
function linkUrl(raw){
 const u=new URL(raw,location.href);
 if(!projectId(u.href)||u.origin===location.origin||/\.(?:json|csv|pdf|zip|tgz)$/i.test(u.pathname))return null;
 let anchor=u.hash;
 if(anchor.startsWith('#qp=')){const old=capsule(anchor.slice(4));anchor=old?.anchor||''}
 const token=btoa(JSON.stringify({...state,anchor})).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
 u.hash='qp='+token;u.searchParams.set('theme',value(state,'theme'));return u.href;
}
function refreshLinks(){for(const a of doc.querySelectorAll('a[href]')){const href=linkUrl(a.href);if(href&&a.href!==href)a.href=href}}
function render(){
 if(!mounted)return;
 const rail=value(state,'rail'),density=value(state,'density'),theme=value(state,'theme');
 if(root.dataset.rail!==(rail?'collapsed':'expanded'))root.dataset.rail=rail?'collapsed':'expanded';
 if(root.dataset.viewDensity!==density)root.dataset.viewDensity=density;
 if(root.dataset.theme!==theme)root.dataset.theme=theme;
 const collapse=doc.querySelector('.q4-collapse');if(collapse){collapse.setAttribute('aria-pressed',String(rail));collapse.setAttribute('aria-label',rail?'사이드바 펼치기':'사이드바 접기');collapse.title=collapse.getAttribute('aria-label')}
 for(const b of doc.querySelectorAll('[data-density]'))b.setAttribute('aria-pressed',String(b.dataset.density===density));
 const group=doc.querySelector('.q4-favorites');
 if(group){
  const focus=doc.activeElement?.closest('.q4-favorites a');const focusId=focus&&projectId(focus.href);
  const heading=doc.createElement('p');heading.textContent='즐겨찾기';group.replaceChildren(heading);
  for(const record of records){const yes=value(state,'favorite:'+record.id);record.node.hidden=yes;if(yes){const a=record.node.cloneNode(true);a.hidden=false;group.append(a);if(focusId===record.id)a.focus({preventScroll:true})}}
  group.hidden=!records.some(r=>value(state,'favorite:'+r.id));
  for(const section of doc.querySelectorAll('.qd-nav-group:not(.q4-favorites)'))section.hidden=![...section.querySelectorAll('a')].some(a=>!a.hidden);
 }
 for(const row of doc.querySelectorAll('.q4-project-row')){const id=projectId(row.querySelector('a')?.href),star=row.querySelector('.q4-star');if(id&&star)star.setAttribute('aria-pressed',String(value(state,'favorite:'+id)))}
 refreshLinks();scope.dispatchEvent(new Event('resize'));
}
function mount(){
 if(mounted||!doc.querySelector('.q4-favorites'))return;
 records=[...doc.querySelectorAll('.qd-nav-group:not(.q4-favorites)>a')].map(node=>({node,id:projectId(node.href)})).filter(r=>r.id);
 if(!records.length)return;
 // Canonical order remains identical across all project pages.
 records.sort((a,b)=>ids.indexOf(a.id)-ids.indexOf(b.id));mounted=true;render();
 new MutationObserver(()=>{for(const [key,attr] of [['theme','theme'],['rail','rail'],['density','viewDensity']]){let v=root.dataset[attr];if(key==='rail')v=v==='collapsed';change(key,v)}}).observe(root,{attributes:true,attributeFilter:['data-theme','data-rail','data-view-density']});
 let queued=false;new MutationObserver(()=>{if(queued)return;queued=true;queueMicrotask(()=>{queued=false;refreshLinks()})}).observe(doc.body,{childList:true,subtree:true});
}
doc.addEventListener('click',event=>{
 const star=event.target.closest?.('.q4-star');
 if(star&&mounted){const id=projectId(star.closest('.q4-project-row')?.querySelector('a')?.href);if(id){event.preventDefault();event.stopImmediatePropagation();change('favorite:'+id,!value(state,'favorite:'+id));return}}
 // Capture fresh state at activation as well as decorating context-menu/new-tab links.
 const a=event.target.closest?.('a[href]');if(a){readRemote();const href=linkUrl(a.href);if(href)a.href=href}
},true);
// The pinned shell redraws its project picker from an old closure when reopened.
// Reconcile after that native handler, before the browser paints.
doc.addEventListener('click',event=>{if(mounted&&event.target.closest?.('.q4-picker')){readRemote();render()}});
scope.addEventListener('storage',event=>{if(event.key===KEY)readRemote()});
scope.addEventListener('pageshow',readRemote);scope.addEventListener('focus',readRemote);
doc.addEventListener('visibilitychange',()=>{if(doc.visibilityState==='visible')readRemote()});
scope.addEventListener('quant-design-ready',mount);
scope.addEventListener('quant-design-unified-ready',mount);
if(doc.readyState==='loading')doc.addEventListener('DOMContentLoaded',mount,{once:true});else mount();
scope.QuantPreferences={version:'1.0.1',get:()=>structuredClone(state),set:change};
})(typeof window==='undefined'?globalThis:window);
