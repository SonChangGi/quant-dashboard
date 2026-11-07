/* Frozen presentation for seven already approved News archive documents only. */
/* Shared presentation layer. Keep the navigation v1 contract above unchanged. */
(function(){
'use strict';
if(typeof document==='undefined'||typeof window==='undefined'||window.__quantDesignV3)return;
const script=document.currentScript;
const archivedPaths=["/news/previews/68c794e1b8e10af7fc7db83b/index.html", "/news/previews/410dc673f197f26f5beec057/index.html", "/news/weekend/2026-09-14/index.html", "/news/weekend/2026-09-28/index.html", "/news/weekend/2026-09-21/index.html", "/news/weekend/2026-09-21/revisions/5082e05d8c3d02b49d19d181/index.html", "/news/weekend/2026-09-28/revisions/469163ed5963470ca7f21f6f/index.html"];
const localArchiveHost=['127.0.0.1','localhost'].includes(location.hostname);
let archivePath=location.pathname.endsWith('/')?location.pathname+'index.html':location.pathname;
if(localArchiveHost&&!archivePath.startsWith('/news/'))archivePath='/news'+archivePath;
if((location.hostname!=='sonchanggi.github.io'&&!localArchiveHost)||!archivedPaths.includes(archivePath)||window.QuantFirstPaint||document.querySelector('link[data-quant-first-paint-css]'))return;
const aliases={momentum:'factor',hub:'quant-dashboard',fearngreed:'fearNgreed','fear-greed':'fearNgreed',dram:'dram-price',etf:'etf-tracking',observatory:'alpha-house'};
const styles={
'quant-dashboard':[],factor:['factor-regime.css'],regime:['factor-regime.css'],fearNgreed:['fear-etf.css','fear-etf-v03.css'],'etf-tracking':['fear-etf.css','fear-etf-v03.css'],'dram-price':['dram-sox.css'],sox:['dram-sox.css'],news:['news.css','news-v03.css'],'alpha-house':['alpha.css'],'investment-journal':['investment-journal.css']};
function begin(){
 const nav=document.querySelector('[data-quant-project]');
 const hostedProjects={'alpha-house.changgi-son.chatgpt.site':'alpha-house','research-observatory-changgi.changgi-son.chatgpt.site':'alpha-house','invest.changgi-son.chatgpt.site':'investment-journal'};
 const raw=document.documentElement.dataset.quantDesignProject||hostedProjects[location.hostname]||nav?.dataset.quantProject||location.pathname.split('/')[1];
 const project=aliases[raw]||raw||(location.hostname.endsWith('.chatgpt.site')?'alpha-house':'');
 if(!Object.hasOwn(styles,project))return;
 window.__quantDesignV3={version:'0.4.0',project,state:'loading'};
 document.documentElement.dataset.quantDesignProject=project;
 const releaseBase=new URL('../releases/0.5.0/',script.src);
 const base=new URL('foundation/',releaseBase);
 const early=window.QuantFirstPaint;
 if(early?.styleReady&&early.state==='loading'&&early.project===project){
  const runtime=document.createElement('script');runtime.src=new URL('runtime.js',early.base);
  runtime.onerror=()=>{window.__quantDesignV3.state='error';early.fail('runtime-network')};
  document.head.append(runtime);return;
 }
 // A pinned modern page must never downgrade after timeout or stylesheet failure.
 if(early||document.querySelector('link[data-quant-first-paint-css]')){
  if(early?.state==='loading')early.fail('startup-contract');
  window.__quantDesignV3.state='error';return;
 }
 const css=['design-system.css',...styles[project].filter(n=>!n.includes('v03')),'v03.css',...styles[project].filter(n=>n.includes('v03')),'focus.css','v04.css',...(['factor','regime','fearNgreed','etf-tracking','dram-price','sox'].includes(project)?['v04-finance.css']:['news','investment-journal','alpha-house'].includes(project)?['v04-editorial.css']:[])];
 const links=css.map(name=>{const link=document.createElement('link');link.rel='stylesheet';link.href=new URL(name,base);link.media='not all';document.head.append(link);return link});
 const ready=Promise.all(links.map(link=>new Promise((resolve,reject)=>{link.onload=resolve;link.onerror=reject})));
 const load=name=>new Promise((resolve,reject)=>{const el=document.createElement('script');el.src=new URL(name,base);el.onload=resolve;el.onerror=reject;document.head.append(el)});
 async function unified(){
  window.__quantDesignUnified={version:'0.5.0',foundation:'0.4.0',project,state:'loading'};
  const styles=['common.css','adapters/finance.css','adapters/editorial.css','adapters/hub.css'];
  const extensionLinks=styles.map(name=>{const link=document.createElement('link');link.rel='stylesheet';link.href=new URL(name,releaseBase);link.media='not all';return link});
  try{
   await Promise.all(extensionLinks.map(link=>new Promise((resolve,reject)=>{link.onload=resolve;link.onerror=reject;document.head.append(link)})));
   extensionLinks.forEach(link=>link.media='all');
   document.documentElement.dataset.unifiedDesign='0.5.0';
   for(const name of ['polish.js','adapters/finance.js','adapters/editorial.js'])await new Promise((resolve,reject)=>{const el=document.createElement('script');el.src=new URL(name,releaseBase);el.onload=resolve;el.onerror=reject;document.head.append(el)});
   window.__quantDesignUnified.state='ready';
   const footer=document.querySelector('.qd-side-footer small');
   if(footer)footer.textContent='Quant Research · v'+window.__quantDesignUnified.version;
   window.dispatchEvent(new CustomEvent('quant-design-unified-ready',{detail:{project,version:'0.5.0'}}));
  }catch{extensionLinks.forEach(link=>link.remove());delete document.documentElement.dataset.unifiedDesign;window.__quantDesignUnified.state='error'}
 }

 Promise.all([ready,load('boot.js')]).then(async()=>{window.QuantDesignTheme?.apply();await load('shell.js');links.forEach(l=>l.media='all');await load('focus.js');if(project==='news')await load('news-v03.js');await load('v04.js');window.__quantDesignV3.state='ready';window.dispatchEvent(new CustomEvent('quant-design-ready',{detail:{project,version:'0.4.0'}}));await unified()}).catch(()=>{window.__quantDesignV3.state='error';if(!document.querySelector('.qd-shell'))links.forEach(l=>l.remove())});
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',begin,{once:true});else begin();
})();
