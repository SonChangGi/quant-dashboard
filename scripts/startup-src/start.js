/* Early presentation only. Native application data and hydration retain ownership. */
(()=>{
'use strict';
if(window.QuantFirstPaint)return;
const root=document.documentElement,script=document.currentScript;
const project=script?.dataset.quantDesignProject;
const projects=['quant-dashboard','factor','dram-price','etf-tracking','sox','fearNgreed','regime','news','investment-journal','alpha-house'];
const sheet=document.querySelector('link[data-quant-first-paint-css]');
if(!projects.includes(project)||!sheet?.sheet||typeof CSSScopeRule==='undefined')return;
const valid=t=>t==='light'||t==='dark';
let saved;try{saved=localStorage.getItem('quant-research-theme')}catch{}
const requested=new URLSearchParams(location.search).get('theme');
const theme=valid(requested)?requested:valid(saved)?saved:'dark';
const read=(key,fallback)=>{try{return JSON.parse(localStorage.getItem(key))??fallback}catch{return fallback}};
root.dataset.quantDesignProject=project;root.dataset.unifiedDesign='0.5.0';root.dataset.quantStartup='1.0.0';root.dataset.quantPaint='loading';
root.dataset.viewDensity=read('quant-ui-v04-density','comfortable')==='compact'?'compact':'comfortable';
root.dataset.rail=read('quant-ui-v04-rail',false)?'collapsed':'expanded';
function applyTheme(){root.dataset.theme=theme;root.style.colorScheme=theme;try{localStorage.setItem('quant-research-theme',theme)}catch{}}
applyTheme();
let body,added=[],previousProject;
const bodyObserver=new MutationObserver(prepareBody);
function prepareBody(){
 if(body||!document.body)return;
 body=document.body;previousProject=body.dataset.qdProject;
 added=['qd-v03','qd-v04',project==='quant-dashboard'?'qd-hub':'qd-project'].filter(c=>!body.classList.contains(c));
 body.classList.add(...added);body.dataset.qdProject=project;bodyObserver.disconnect();
}
bodyObserver.observe(root,{childList:true});prepareBody();
const themeObserver=new MutationObserver(()=>{if(root.dataset.theme!==theme)applyTheme()});
themeObserver.observe(root,{attributes:true,attributeFilter:['data-theme']});
const api=window.QuantFirstPaint={version:'1.0.0',uiVersion:'0.5.0',project,styleReady:true,state:'loading',base:new URL('.',script.src).href,finish,fail};
let timer=setTimeout(()=>fail('timeout'),4000);
function stop(){clearTimeout(timer);themeObserver.disconnect();bodyObserver.disconnect()}
function finish(){if(api.state!=='loading')return;stop();api.state='ready';root.dataset.quantPaint='ready'}
function fail(reason){
 if(api.state!=='loading')return;stop();api.state='fallback';api.reason=reason;api.styleReady=false;
 if(window.__quantDesignV3)window.__quantDesignV3.state='error';
 document.querySelectorAll('.qd-shell,.qd-sidebar,.qd-command,.q4-dialog').forEach(node=>node.remove());
 delete root.dataset.quantStartup;delete root.dataset.unifiedDesign;root.dataset.quantPaint='fallback';
 if(body){body.classList.remove(...added);if(previousProject===undefined)delete body.dataset.qdProject;else body.dataset.qdProject=previousProject}
}
})();
