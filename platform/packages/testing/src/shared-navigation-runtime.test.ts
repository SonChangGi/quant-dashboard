// @vitest-environment jsdom
import {expect,it,afterEach,vi} from 'vitest';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
interface TestDom {window: Window & typeof globalThis}
const {JSDOM} = createRequire(resolve(process.cwd(),"package.json"))('jsdom') as {JSDOM: new (html: string, options: {url:string;runScripts:string}) => TestDom};
import {resolve} from 'node:path';
const source=readFileSync(resolve(process.cwd(),'../shared/navigation/v1/nav.js'),'utf8');
const menu=JSON.parse(readFileSync(resolve(process.cwd(),'../shared/navigation/v1/menu.json'),'utf8'));
const doms:TestDom[]=[];
afterEach(()=>{for(const dom of doms.splice(0))dom.window.close();vi.restoreAllMocks();});
function create(fetcher?:unknown){const dom=new JSDOM('<nav class="quant-shared-nav" data-quant-project="etf"><a class="quant-shared-nav__brand" href="/">Hub</a><div class="quant-shared-nav__links"><a href="https://sonchanggi.github.io/best-factor/">Best Factor</a></div><button id="theme">Theme</button></nav>',{url:'https://sonchanggi.github.io/etf-tracking/',runScripts:'outside-only'});doms.push(dom);Object.assign(dom.window,{fetch:fetcher});dom.window.eval(source);return dom;}
it('replaces links atomically while preserving theme element, handler and ETF controls',async()=>{
 const changed=structuredClone(menu);changed.projects[0].label='Central update';
 const dom=create(async()=>({ok:true,text:async()=>JSON.stringify(changed)}));
 const d=dom.window.document,button=d.querySelector('#theme')!;let clicks=0;button.addEventListener('click',()=>clicks++);
 await new Promise(resolve=>dom.window.setTimeout(resolve,10));
 expect(d.querySelector('.quant-shared-nav__links')!.textContent).toContain('Central update');
 expect(d.querySelector('.quant-shared-nav__links')!.textContent).not.toContain('Best Factor');
 expect(d.querySelectorAll('.quant-shared-nav__links a')).toHaveLength(menu.projects.length);
 expect(d.querySelectorAll('[data-control-id="project_navigation"]')).toHaveLength(menu.projects.length);
 expect(d.querySelector('[aria-current="page"]')!.textContent).toBe('ETF');
 expect(d.querySelector('#theme')).toBe(button);(button as HTMLButtonElement).click();expect(clicks).toBe(1);
 // A legacy renderer cannot reintroduce its retired menu later.
 d.querySelector('.quant-shared-nav__links')!.innerHTML='<a>Best Factor</a>';
 await new Promise(resolve=>dom.window.setTimeout(resolve,5));
 expect(d.querySelector('.quant-shared-nav__links')!.textContent).not.toContain('Best Factor');
});
it('keeps a usable fallback on malformed response and never edits a React-owned rail',async()=>{
 const dom=create(async()=>({ok:true,text:async()=>JSON.stringify({schemaVersion:'bad'})}));
 const d=dom.window.document;
 await new Promise(resolve=>dom.window.setTimeout(resolve,10));
 expect(d.querySelectorAll('.quant-shared-nav__links a')).toHaveLength(menu.projects.length);
 expect(d.querySelector('.quant-shared-nav__links')!.textContent).toContain('Factor');
 const nav=d.createElement('nav');nav.className='quant-shared-nav';nav.dataset.quantNavigationManaged='react';nav.innerHTML='<div class="quant-shared-nav__links"><a>React state</a></div>';d.body.append(nav);
 await new Promise(resolve=>dom.window.setTimeout(resolve,5));expect(nav.textContent).toBe('React state');
});
