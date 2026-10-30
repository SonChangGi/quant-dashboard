(()=>{
'use strict';
if(window.__quantDesignV4?.state==='ready')return;
const root=document.documentElement,body=document.body,project=body.dataset.qdProject;
if(!document.querySelector('.qd-sidebar')||!document.querySelector('.qd-shell-inner'))return;
const read=(k,d)=>{try{return JSON.parse(localStorage.getItem(k))??d}catch{return d}},save=(k,v)=>{try{localStorage.setItem(k,JSON.stringify(v))}catch{}};
const icon=path=>`<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${path}</svg>`;
const glyphs={menu:icon('<rect x="3" y="4" width="18" height="16" rx="3"/><path d="M9 4v16"/>'),star:icon('<path d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2L12 17.3l-5.6 2.9 1.1-6.2L3 9.6l6.2-.9Z"/>'),chevron:icon('<path d="m8 10 4 4 4-4"/>'),close:icon('<path d="m6 6 12 12M6 18 18 6"/>'),view:icon('<path d="M4 6h16M4 12h16M4 18h16M8 3v6m8 0v6m-6 0v6"/>'),outline:icon('<path d="M8 6h12M8 12h12M8 18h12M4 6h.1M4 12h.1M4 18h.1"/>')};
function button(label,html,cls=''){const b=document.createElement('button');b.type='button';b.className=cls;b.setAttribute('aria-label',label);b.title=label;b.innerHTML=html;return b}
body.classList.add('qd-v04');
const side=document.querySelector('.qd-sidebar'),bar=document.querySelector('.qd-shell-inner');
const records=[...side.querySelectorAll('.qd-nav-group>a')].map(a=>({name:a.querySelector('span').textContent,url:a.href,icon:a.querySelector('svg').outerHTML,current:a.getAttribute('aria-current')==='page',node:a}));
const current=records.find(r=>r.current)||records[0];
const defaultFavorites=['대시보드','뉴스 브리핑','투자일지'];
const storedFavorites=read('quant-ui-v04-favorites',defaultFavorites);
let favorites=(Array.isArray(storedFavorites)?storedFavorites:defaultFavorites).filter(n=>records.some(r=>r.name===n));
root.dataset.viewDensity=read('quant-ui-v04-density','comfortable')==='compact'?'compact':'comfortable';
root.dataset.rail=read('quant-ui-v04-rail',false)?'collapsed':'expanded';
const collapse=button('사이드바 접기',glyphs.menu,'q4-icon q4-collapse');bar.prepend(collapse);
function syncRail(){const folded=root.dataset.rail==='collapsed';collapse.setAttribute('aria-label',folded?'사이드바 펼치기':'사이드바 접기');collapse.title=collapse.getAttribute('aria-label');collapse.setAttribute('aria-pressed',String(folded))}
collapse.onclick=()=>{root.dataset.rail=root.dataset.rail==='collapsed'?'expanded':'collapsed';save('quant-ui-v04-rail',root.dataset.rail==='collapsed');syncRail();dispatchEvent(new Event('resize'))};syncRail();
const picker=button('프로젝트 선택',`<span>${current.name}</span>${glyphs.chevron}`,'q4-picker');picker.setAttribute('aria-haspopup','dialog');document.querySelector('.qd-breadcrumb').replaceWith(picker);
const outline=button('이 페이지 목차',glyphs.outline,'q4-icon q4-outline');outline.setAttribute('aria-haspopup','dialog');
const view=button('보기 설정',glyphs.view,'q4-icon q4-view');view.setAttribute('aria-haspopup','dialog');bar.insertBefore(outline,document.getElementById('qd-theme'));bar.insertBefore(view,document.getElementById('qd-theme'));
const footer=side.querySelector('.qd-side-footer');footer.replaceChildren();const version=document.createElement('small');version.textContent='Quant Research · v0.4';footer.append(version);
let opener;
function dialog(title,cls){const d=document.createElement('dialog');d.className='q4-dialog '+cls;d.setAttribute('aria-label',title);const head=document.createElement('div');head.className='q4-dialog-head';const h=document.createElement('h2');h.textContent=title;const close=button(title+' 닫기',glyphs.close,'q4-icon');close.onclick=()=>d.close();head.append(h,close);d.append(head);body.append(d);d.addEventListener('click',e=>{if(e.target===d)d.close()});d.addEventListener('close',()=>opener?.focus({preventScroll:true}));return d}
function show(d,b){if(body.classList.contains('qd-focus-open')||document.querySelector('dialog[open]'))return;opener=b;d.showModal()}
const projects=dialog('프로젝트','q4-projects');const projectList=document.createElement('div');projectList.className='q4-project-grid';projects.append(projectList);
const favGroup=document.createElement('div');favGroup.className='qd-nav-group q4-favorites';side.querySelector('nav').prepend(favGroup);
function renderFavorites(){favGroup.replaceChildren();const h=document.createElement('p');h.textContent='즐겨찾기';favGroup.append(h);for(const r of records){r.node.title=r.name;const yes=favorites.includes(r.name);r.node.hidden=yes; if(yes){const a=r.node.cloneNode(true);a.hidden=false;favGroup.append(a)}}favGroup.hidden=!favorites.length;
 for(const group of side.querySelectorAll('.qd-nav-group:not(.q4-favorites)'))group.hidden=![...group.querySelectorAll('a')].some(a=>!a.hidden);
 projectList.replaceChildren();for(const r of records){const row=document.createElement('div');row.className='q4-project-row';const a=document.createElement('a');a.href=r.url;a.innerHTML=r.icon;const span=document.createElement('span');span.textContent=r.name;a.append(span);if(r.current)a.setAttribute('aria-current','page');const star=button(r.name+' 즐겨찾기',glyphs.star,'q4-star');star.setAttribute('aria-pressed',String(favorites.includes(r.name)));star.onclick=()=>{const removing=favorites.includes(r.name);favorites=removing?favorites.filter(n=>n!==r.name):[...favorites,r.name];save('quant-ui-v04-favorites',favorites);renderFavorites();projectList.querySelectorAll('.q4-star')[records.indexOf(r)]?.focus()};row.append(a,star);projectList.append(row)}
}
renderFavorites();picker.onclick=()=>{renderFavorites();show(projects,picker)};
const settings=dialog('보기 설정','q4-settings');const densityLabel=document.createElement('p');densityLabel.textContent='화면 밀도';settings.append(densityLabel);const densities=document.createElement('div');densities.className='q4-density-options';settings.append(densities);
for(const [id,name,desc]of [['comfortable','여유롭게','카드와 표를 편하게 읽기'],['compact','촘촘하게','한 화면에 더 많은 정보']]){const b=button(name,`<strong>${name}</strong><span>${desc}</span>`);b.dataset.density=id;b.onclick=()=>{root.dataset.viewDensity=id;save('quant-ui-v04-density',id);syncDensity();dispatchEvent(new Event('resize'))};densities.append(b)}
function syncDensity(){for(const b of densities.children)b.setAttribute('aria-pressed',String(b.dataset.density===root.dataset.viewDensity))}syncDensity();const shortcuts=document.createElement('p');shortcuts.className='q4-shortcuts';shortcuts.textContent='⌘ K 빠른 이동 · Esc 닫기';settings.append(shortcuts);view.onclick=()=>show(settings,view);
const contents=dialog('이 페이지 목차','q4-contents');const contentList=document.createElement('div');contentList.className='q4-content-list';contents.append(contentList);
function goTo(target){const prev=target.getAttribute('tabindex');target.setAttribute('tabindex','-1');target.focus({preventScroll:true});target.scrollIntoView({block:'start',behavior:'instant'});target.addEventListener('blur',()=>prev===null?target.removeAttribute('tabindex'):target.setAttribute('tabindex',prev),{once:true})}
outline.onclick=()=>{contentList.replaceChildren();const used=new Set();for(const h of document.querySelectorAll('main h2,main h3,.dashboard-shell h2,.library h2')){if(!h.getClientRects().length||h.closest('dialog'))continue;const name=h.textContent.trim().replace(/\s+/g,' ');if(!name||used.has(name))continue;used.add(name);const b=button(name,'');b.textContent=name;b.onclick=()=>{contents.close();requestAnimationFrame(()=>goTo(h))};contentList.append(b)}if(!contentList.childElementCount){const p=document.createElement('p');p.textContent='현재 화면에 추가 섹션이 없습니다.';contentList.append(p)}show(contents,outline)};
if(project==='quant-dashboard'){
 const index=document.querySelector('.section-index');index.classList.add('q4-original-index');const filters=document.createElement('nav');filters.className='section q4-hub-views';filters.setAttribute('aria-label','대시보드 보기');const options=[['all','전체',null],['market','시장',['fearngreed','regime']],['strategy','전략 · ETF',['momentum','etf']],['semiconductors','반도체',['dram','sox']]];
 let active=new URLSearchParams(location.search).get('view')||'all';if(!options.some(o=>o[0]===active))active='all';
 const apply=()=>{const allowed=options.find(o=>o[0]===active)[2];for(const e of document.querySelectorAll('#summary-grid>article[data-project-id]'))e.hidden=!!allowed&&!allowed.includes(e.dataset.projectId);for(const h of document.querySelectorAll('#summary-grid>.summary-group-heading')){let n=h.nextElementSibling,visible=false;while(n&&!n.matches('.summary-group-heading')){if(!n.hidden)visible=true;n=n.nextElementSibling}h.hidden=!visible}document.querySelector('.news-section').hidden=active!=='all';for(const b of filters.querySelectorAll('button[data-view]'))b.setAttribute('aria-pressed',String(b.dataset.view===active));};
 for(const [id,name]of options){const b=button(name,'');b.textContent=name;b.dataset.view=id;b.onclick=()=>{active=id;apply();const u=new URL(location.href);id==='all'?u.searchParams.delete('view'):u.searchParams.set('view',id);history.replaceState(null,'',u);dispatchEvent(new Event('resize'))};filters.append(b)}const data=document.createElement('a');data.href='#operations';data.textContent='데이터 상태';data.onclick=()=>{const details=document.querySelector('#operations details');if(details)details.open=true};filters.append(data);index.before(filters);new MutationObserver(apply).observe(document.getElementById('summary-grid'),{childList:true});apply();
}
window.__quantDesignV4={version:'0.4.0',state:'ready',project};
})();
