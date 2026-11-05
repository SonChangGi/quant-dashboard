import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
const release=new URL('../shared/design/releases/0.5.0/',import.meta.url);
const extension=new URL('../shared/design/releases/0.6.0/',import.meta.url);
const dest=new URL('../shared/design/startup/1.1.0/',import.meta.url);mkdirSync(dest,{recursive:true});
const css={
 'quant-dashboard':[],factor:['factor-regime.css'],regime:['factor-regime.css'],fearNgreed:['fear-etf.css','fear-etf-v03.css'],'etf-tracking':['fear-etf.css','fear-etf-v03.css'],'dram-price':['dram-sox.css'],sox:['dram-sox.css'],news:['news.css','news-v03.css'],'alpha-house':['alpha.css'],'investment-journal':['investment-journal.css']};
const finance=['factor','regime','fearNgreed','etf-tracking','dram-price','sox'];
const manifest={version:'1.1.0',uiVersion:'0.6.0',chartVersion:'1.2.0',foundation:'0.4.0',sources:{},files:{}};
const hash=s=>createHash('sha256').update(s).digest('hex');
function source(name){const s=readFileSync(new URL(name,release),'utf8');manifest.sources[name]=hash(s);return s}
function extra(name){const s=readFileSync(new URL(name,extension),'utf8');manifest.sources['release-0.6.0/'+name]=hash(s);return s}
function emit(name,text){if(process.argv.includes('--check')){if(readFileSync(new URL(name,dest),'utf8')!==text)throw new Error('Generated asset drift: '+name)}else writeFileSync(new URL(name,dest),text);manifest.files[name]=hash(text)}
for(const [project,domain] of Object.entries(css)){
 const names=['foundation/design-system.css',...domain.filter(n=>!n.includes('v03')).map(n=>'foundation/'+n),'foundation/v03.css',...domain.filter(n=>n.includes('v03')).map(n=>'foundation/'+n),'foundation/focus.css','foundation/v04.css',...(finance.includes(project)?['foundation/v04-finance.css']:['news','investment-journal','alpha-house'].includes(project)?['foundation/v04-editorial.css']:[]),'common.css','adapters/finance.css','adapters/editorial.css','adapters/hub.css'];
 let content=names.map(n=>'/* '+n+' */\n'+source(n)).join('\n')+'\n'+['common.css','dram.css','all-sites.css','quant-range.css'].map(extra).join('\n');
 const face=content.match(/@font-face\{[^}]+\}/)[0].replace("'./PretendardVariable.woff2'","'../../releases/0.5.0/foundation/PretendardVariable.woff2'");
 content=content.replace(/@font-face\{[^}]+\}/,'');
 content=content.replace(/:root/g,':scope').replace(/\bhtml(?=[\s.#\[:,{])/g,':scope');
 emit(project+'.css',`/* Generated from immutable foundation 0.5.0 and UI 0.6.0; source hashes in manifest.json. */\n${face}\n@scope (:root[data-quant-startup="1.1.0"]) {\n${content}\n}\nhtml[data-quant-startup][data-quant-paint="loading"] :is(.qd-shell,.qd-sidebar){visibility:hidden!important}\n`);
}
let runtime="/* Ordered, single-task presentation initialization from immutable sources. */\n(()=>{if(window.QuantFirstPaint?.state!=='loading')return;try{\n";
for(const name of ['foundation/boot.js','foundation/shell.js','foundation/focus.js','foundation/news-v03.js','foundation/v04.js','polish.js','adapters/finance.js','adapters/editorial.js']){
 const code=source(name);runtime+=(name==='foundation/news-v03.js'?"if(document.documentElement.dataset.quantDesignProject==='news'){\n"+code+'\n}':code)+'\n;\n';
}
runtime+=extra('tables.js')+'\n;\n'+extra('ui-copy.js')+'\n;\n';
runtime+=`if(window.__quantDesignV4?.state!=='ready')throw new Error('Shared shell initialization failed');
window.__quantDesignV3.state='ready';
window.__quantDesignUnified={version:'0.6.0',foundation:'0.4.0',project:document.documentElement.dataset.quantDesignProject,state:'ready'};
const footer=document.querySelector('.qd-side-footer small');if(footer)footer.textContent='Quant Research · v'+window.__quantDesignUnified.version;
window.QuantFirstPaint?.finish();
window.dispatchEvent(new CustomEvent('quant-design-ready',{detail:{project:window.__quantDesignUnified.project,version:'0.4.0'}}));
window.dispatchEvent(new CustomEvent('quant-design-unified-ready',{detail:{project:window.__quantDesignUnified.project,version:'0.6.0'}}));
}catch(error){if(window.__quantDesignV3)window.__quantDesignV3.state='error';window.QuantFirstPaint?.fail('runtime');throw error}})();\n`;
emit('runtime.js',runtime);emit('start.js',readFileSync(new URL('startup-src/start-1.1.js',import.meta.url),'utf8')+'\n;\n'+extra('quant-range.js'));
const manifestText=JSON.stringify(manifest,null,2)+'\n';if(process.argv.includes('--check')){if(readFileSync(new URL('manifest.json',dest),'utf8')!==manifestText)throw new Error('Manifest drift')}else writeFileSync(new URL('manifest.json',dest),manifestText);
console.log('Generated first-paint entry in '+fileURLToPath(dest));
