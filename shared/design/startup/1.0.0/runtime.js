/* Ordered, single-task presentation initialization from immutable sources. */
(()=>{if(window.QuantFirstPaint?.state!=='loading')return;try{
/* Shared theme preference wins over a page's legacy light/system default. */
(()=>{
 'use strict';
 const root=document.documentElement;
 const valid=value=>value==='light'||value==='dark';
 function apply(){
  let saved;try{saved=localStorage.getItem('quant-research-theme')}catch{}
  const requested=new URLSearchParams(location.search).get('theme');
  const theme=valid(requested)?requested:valid(saved)?saved:'dark';
  root.dataset.theme=theme;
  root.dataset.density=root.dataset.quantDesignProject==='news'?'spacious':'compact';
  root.style.colorScheme=theme;
  try{localStorage.setItem('quant-research-theme',theme);if(root.dataset.quantDesignProject==='news')localStorage.setItem('research-news-theme',theme)}catch{}
  return theme;
 }
 window.QuantDesignTheme=Object.freeze({apply});
 apply();
})();

;
(()=>{
'use strict';
const root=document.documentElement,project=root.dataset.quantDesignProject,hub=project==='quant-dashboard',library=location.pathname.startsWith('/news/library');
document.body.dataset.qdProject=project;document.body.classList.add(hub?'qd-hub':'qd-project','qd-v03');
const projects=[['quant-dashboard','대시보드','시장과 전략','grid'],['factor','Factor','팩터 전략','chart'],['fearNgreed','Fear & Greed','시장 심리','pulse'],['regime','Regime','시장 국면','layers'],['dram-price','DRAM','메모리 가격','chip'],['sox','SOX','반도체 지수','chart'],['etf-tracking','ETF','ETF 추적','pie'],['news','뉴스 브리핑','뉴스','news'],['investment-journal','투자일지','자산과 투자 기록','pie'],['alpha-house','Alpha House','작업 공간','house']];
const icons={grid:'<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',chart:'<path d="M4 4v16h17M7 15l4-5 4 2 5-7"/>',pulse:'<path d="M2 12h5l3-8 4 16 3-8h5"/>',layers:'<path d="m12 3 9 5-9 5-9-5 9-5Zm-9 9 9 5 9-5M3 16l9 5 9-5"/>',chip:'<rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 2v4m6-4v4M9 18v4m6-4v4M2 9h4m-4 6h4m12-6h4m-4 6h4"/>',pie:'<path d="M12 3v9h9A9 9 0 0 0 12 3Z"/><path d="M8 4a9 9 0 1 0 12 12"/>',news:'<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 7h8M8 11h8M8 15h3m3 0h2M8 18h8"/>',house:'<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V10Z"/><path d="M9 21v-8h6v8"/>',search:'<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',sun:'<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1 1m12 12 1 1M5 19l1-1M18 6l1-1"/>',moon:'<path d="M21 13A9 9 0 0 1 11 3 9 9 0 1 0 21 13Z"/>'};
const icon=(key)=>`<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[key]||icons.grid}</svg>`;
const label=library?'전체 브리핑':projects.find(p=>p[0]===project)?.[1]||'Quant';
const base=id=>id==='investment-journal'?'https://invest.changgi-son.chatgpt.site/':id==='alpha-house'?'https://alpha-house.changgi-son.chatgpt.site/':'https://sonchanggi.github.io/'+id+'/';
const url=id=>base(id)+'?theme='+root.dataset.theme;
const navItem=([id,name,,glyph])=>`<a href="${url(id)}" ${id===project?'aria-current="page"':''}>${icon(glyph)}<span>${name}</span>${id===project?'<i></i>':''}</a>`;
const groupItems=ids=>ids.map(id=>projects.find(project=>project[0]===id)).filter(Boolean).map(navItem).join('');
const shell=document.createElement('header');shell.className='qd-shell';shell.innerHTML=`<div class="qd-shell-inner"><a class="qd-brand" href="https://sonchanggi.github.io/quant-dashboard/"><span class="qd-logo" aria-hidden="true"><svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" focusable="false"><rect x="4" y="13" width="3.5" height="7" rx="1.2" opacity=".65"/><rect x="10.25" y="9" width="3.5" height="11" rx="1.2" opacity=".85"/><rect x="16.5" y="4" width="3.5" height="16" rx="1.2"/></svg></span>Quant</a><div class="qd-breadcrumb"><span>워크스페이스</span><span aria-hidden="true">/</span><strong>${label}</strong></div><nav class="qd-links" aria-label="공통 메뉴">${projects.map(navItem).join('')}</nav><button id="qd-search" type="button" aria-label="페이지와 섹션 찾기" aria-haspopup="dialog">${icon('search')}<span>페이지 · 섹션 찾기</span><kbd>⌘ K</kbd></button><button id="qd-theme" type="button"></button></div>`;
const side=document.createElement('aside');side.className='qd-sidebar';side.innerHTML=`<a class="qd-brand" href="https://sonchanggi.github.io/quant-dashboard/"><span class="qd-logo" aria-hidden="true"><svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" focusable="false"><rect x="4" y="13" width="3.5" height="7" rx="1.2" opacity=".65"/><rect x="10.25" y="9" width="3.5" height="11" rx="1.2" opacity=".85"/><rect x="16.5" y="4" width="3.5" height="16" rx="1.2"/></svg></span><span>Quant<small>RESEARCH WORKSPACE</small></span></a><nav aria-label="프로젝트"><div class="qd-nav-group">${navItem(projects[0])}</div><div class="qd-nav-group"><p>시장과 전략</p>${groupItems(['factor','fearNgreed','regime','etf-tracking','investment-journal'])}</div><div class="qd-nav-group"><p>반도체</p>${groupItems(['dram-price','sox'])}</div><div class="qd-nav-group"><p>뉴스와 작업</p>${groupItems(['news','alpha-house'])}</div></nav><div class="qd-side-footer"><small>Quant Research · v0.3.1</small></div>`;
document.body.prepend(shell);document.body.prepend(side);
const themeButton=document.getElementById('qd-theme');
function localize(a){const raw=a.getAttribute('href');if(!raw||raw.startsWith('#'))return;let u;try{u=new URL(raw,location.href)}catch{return}if(!['https:','http:'].includes(u.protocol))return;if(u.hostname==='research-observatory-changgi.changgi-son.chatgpt.site')u.hostname='alpha-house.changgi-son.chatgpt.site';const known=(u.hostname==='sonchanggi.github.io'&&projects.some(p=>p[0]===u.pathname.split('/')[1]))||['alpha-house.changgi-son.chatgpt.site','invest.changgi-son.chatgpt.site'].includes(u.hostname);if(known&&!/\.(json|csv|pdf|zip)$/i.test(u.pathname)){u.searchParams.set('theme',root.dataset.theme);a.setAttribute('href',u.href)}}
function sync(){const dark=root.dataset.theme==='dark';themeButton.innerHTML=icon(dark?'sun':'moon')+`<span class="qd-theme-label">${dark?'라이트':'다크'}</span>`;themeButton.setAttribute('aria-label',dark?'라이트 모드로 전환':'다크 모드로 전환');themeButton.setAttribute('aria-pressed',String(dark));try{localStorage.setItem('quant-research-theme',root.dataset.theme)}catch{}root.style.colorScheme=root.dataset.theme;const u=new URL(location.href);u.searchParams.set('theme',root.dataset.theme);history.replaceState(null,'',u);document.querySelectorAll('.qd-shell a,.qd-sidebar a').forEach(localize)}
themeButton.addEventListener('click',()=>{const native=document.getElementById('theme-toggle')||document.querySelector('.quant-shared-nav__theme'),before=root.dataset.theme;if(native)native.click();if(root.dataset.theme===before)root.dataset.theme=before==='dark'?'light':'dark';sync()});new MutationObserver(sync).observe(root,{attributes:true,attributeFilter:['data-theme']});
document.addEventListener('click',e=>{const a=e.target.closest?.('a[href]');if(a)localize(a)},true);
function refine(scope=document){scope.querySelectorAll?.('a[href]').forEach(localize);if(!hub)return;document.querySelectorAll('.panel-link').forEach(a=>{if(a.textContent.endsWith(' 열기'))a.textContent=a.textContent.replace(/ 열기$/,'')});const n=document.getElementById('news-report-link');if(n&&n.textContent!=='뉴스 전체')n.textContent='뉴스 전체'}
refine();new MutationObserver(records=>{for(const r of records)for(const node of r.addedNodes)if(node.nodeType===1&&!node.closest('.qd-command')){if(node.matches('a[href]'))localize(node);refine(node)}}).observe(document.body,{childList:true,subtree:true});
if(hub){const io=new IntersectionObserver(es=>{for(const e of es)if(e.isIntersecting)document.querySelectorAll('.section-index a').forEach(a=>a.classList.toggle('qd-active',a.hash==='#'+e.target.id))},{rootMargin:'-150px 0px -60% 0px'});['news','market','factors','semiconductors','holdings','operations'].forEach(id=>{const e=document.getElementById(id);if(e)io.observe(e)})}
const dialog=document.createElement('dialog');dialog.className='qd-command';dialog.setAttribute('aria-label','페이지와 섹션 빠른 이동');dialog.innerHTML=`<div class="qd-command-input">${icon('search')}<input id="qd-command-query" type="search" placeholder="페이지 · 섹션 검색" autocomplete="off" role="combobox" aria-controls="qd-command-results" aria-expanded="true" aria-autocomplete="list" aria-label="페이지 또는 섹션 검색"><button type="button" class="qd-command-close" aria-label="빠른 이동 닫기">Esc</button></div><div id="qd-command-results" role="listbox" aria-label="검색 결과"></div><p class="qd-command-status" role="status" aria-live="polite"></p><div class="qd-command-footer"><span>↑ ↓ 선택</span><span>↵ 이동</span><span>Esc 닫기</span></div>`;document.body.append(dialog);
const input=dialog.querySelector('input'),results=dialog.querySelector('#qd-command-results'),status=dialog.querySelector('[role=status]');let entries=[],shown=[],selected=0,opener;
function collect(){entries=projects.map(([id,name,desc,glyph])=>({name,desc:'프로젝트 · '+desc,href:url(id),glyph,terms:id+' '+name+' '+desc}));entries.push({name:'전체 브리핑',desc:'뉴스 · 날짜와 키워드 검색',href:base('news')+'library/?theme='+root.dataset.theme,glyph:'news',terms:'뉴스 브리핑 검색 archive library'});let index=0;for(const h of document.querySelectorAll('main h2,main h3,main h4,.dashboard-shell h2,.library h2')){if(!h.getClientRects().length||h.closest('.qd-command'))continue;const name=h.innerText.trim().replace(/\s+/g,' ');if(name.length<2)continue;const holder=h.closest('section[id],article[id]')||h;if(!holder.id){do{index++}while(document.getElementById('qd-section-'+index));holder.id='qd-section-'+index;}if(entries.some(x=>x.href==='#'+holder.id))continue;entries.push({name,desc:'이 페이지 · '+label,href:'#'+holder.id,glyph:project==='news'?'news':'chart',terms:name});if(index>90)break}}
function select(i){selected=i;const bs=[...results.querySelectorAll('[role=option]')];bs.forEach((b,n)=>b.setAttribute('aria-selected',String(n===i)));if(bs[i]){input.setAttribute('aria-activedescendant',bs[i].id);bs[i].scrollIntoView({block:'nearest'})}else input.removeAttribute('aria-activedescendant')}
function render(){const q=input.value.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);shown=entries.filter(e=>q.every(s=>e.terms.toLocaleLowerCase().includes(s))).slice(0,30);results.replaceChildren();shown.forEach((e,i)=>{const b=document.createElement('button');b.type='button';b.id='qd-command-option-'+i;b.setAttribute('role','option');b.tabIndex=-1;b.innerHTML=icon(e.glyph);const text=document.createElement('span'),title=document.createElement('strong'),sub=document.createElement('small');title.textContent=e.name;sub.textContent=e.desc;text.append(title,sub);b.append(text);const arrow=document.createElement('span');arrow.className='qd-command-arrow';arrow.textContent='↵';b.append(arrow);b.addEventListener('click',()=>go(i));results.append(b)});status.textContent=shown.length?shown.length+'개 결과':'일치하는 페이지나 섹션이 없습니다.';select(0)}
function close(){dialog.close();opener?.focus({preventScroll:true})}
function go(i){const e=shown[i];if(!e)return;close();if(e.href.startsWith('#')){const target=document.getElementById(e.href.slice(1));if(target){const old=target.getAttribute('tabindex');target.setAttribute('tabindex','-1');target.focus({preventScroll:true});requestAnimationFrame(()=>target.scrollIntoView({behavior:'instant',block:'start'}));target.addEventListener('blur',()=>{if(old===null)target.removeAttribute('tabindex');else target.setAttribute('tabindex',old)},{once:true})}}else location.assign(e.href)}
function open(){if(document.body.classList.contains('qd-focus-open')||document.querySelector('dialog[open]:not(.qd-command)'))return;if(dialog.open){close();return}opener=document.activeElement;collect();input.value='';render();dialog.showModal();input.focus()}
document.getElementById('qd-search').addEventListener('click',open);dialog.querySelector('.qd-command-close').addEventListener('click',close);dialog.addEventListener('cancel',e=>{e.preventDefault();close()});dialog.addEventListener('click',e=>{if(e.target===dialog)close()});input.addEventListener('input',render);input.addEventListener('keydown',e=>{if(e.isComposing)return;if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();if(shown.length)select((selected+(e.key==='ArrowDown'?1:-1)+shown.length)%shown.length)}if(e.key==='Enter'){e.preventDefault();go(selected)}});document.addEventListener('keydown',e=>{if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='k'){e.preventDefault();open()}});
sync();function centerNav(){const nav=shell.querySelector('.qd-links'),a=nav.querySelector('[aria-current=page]');if(a)nav.scrollLeft=Math.max(0,a.offsetLeft-nav.offsetLeft-(nav.clientWidth-a.clientWidth)/2)}requestAnimationFrame(centerNav);addEventListener('resize',centerNav);
})();

;
/* Expand existing chart panels without moving native/React nodes. */
(() => {
  'use strict';
  const path = document.documentElement.dataset.quantDesignProject;
  const specs = {
    'quant-dashboard': ['article.panel[data-project-id]', 'svg[role="img"]'],
    factor: ['.lab-panel', '.lab-chart'],
    fearNgreed: ['.card', '.chart svg'],
    regime: ['.card', '.svg-chart-wrap svg, #model-loss-chart svg'],
    'dram-price': ['.chart-panel', '.chart-viewport svg, .chart-facet svg'],
    sox: ['.panel', '.bar-chart .bar-row, .quadrant .quad-point'],
    'etf-tracking': ['.primary-chart-panel', '#weight-chart svg'],
    'investment-journal': ['.panel', '.recharts-wrapper']
  };
  if (!specs[path]) return;
  const [panels, charts] = specs[path];
  const controls = 'button:not([disabled]),a[href],input:not([disabled]),select:not([disabled]),textarea:not([disabled]),summary,[tabindex]:not([tabindex="-1"])';
  let active = null, scheduled = false;
  const visible = el => !!(el.getClientRects().length && getComputedStyle(el).visibility !== 'hidden' && !el.closest('[hidden],[inert]'));
  const restoreAttribute = (el, key, value) => value === null ? el.removeAttribute(key) : el.setAttribute(key, value);
  const resize = () => requestAnimationFrame(() => window.dispatchEvent(new Event('resize')));
  function makeButton(panel) {
    let button = [...panel.querySelectorAll('.qd-focus-button')].find(el => el.closest(panels) === panel);
    if (button) return button;
    button = document.createElement('button');
    button.type = 'button'; button.className = 'qd-focus-button';
    button.textContent = ''; button.title='차트 크게 보기'; button.setAttribute('aria-label', '차트 크게 보기');
    button.setAttribute('aria-haspopup', 'dialog');
    button.addEventListener('click', () => active?.panel === panel ? close() : open(panel, button));
    const heading = [...panel.children].find(el => el.matches('.panel-header,.card-head,.card-heading,.lab-section-heading,.section-heading') || (path==='investment-journal' && el.matches('.section-head')));
    if (heading) { heading.classList.add('qd-focus-heading'); heading.append(button); }
    else { const row = document.createElement('div'); row.className='qd-focus-tools'; row.append(button); panel.prepend(row); }
    return button;
  }
  function portals() {
    if (!active) return [];
    return [...active.panel.querySelectorAll('[aria-expanded="true"][aria-controls]')].flatMap(el => el.getAttribute('aria-controls').split(/\s+/).map(id => document.getElementById(id))).filter(Boolean);
  }
  function syncPortals() {
    for (const popup of portals()) {
      const wrapper = popup.closest('[data-radix-popper-content-wrapper]') || popup;
      if (!active.portals.has(wrapper)) {
        active.portals.set(wrapper, wrapper.inert);
        wrapper.inert = false; wrapper.classList.add('qd-focus-portal');
      }
    }
  }
  function open(panel, trigger) {
    if (active) close();
    const rect = panel.getBoundingClientRect(), style = getComputedStyle(panel);
    const placeholder = document.createElement('div'); placeholder.className='qd-focus-placeholder'; placeholder.setAttribute('aria-hidden','true');
    Object.assign(placeholder.style,{height:`${rect.height}px`,width:`${rect.width}px`,maxWidth:'100%',margin:style.margin,gridColumn:style.gridColumn,gridRow:style.gridRow});
    panel.before(placeholder);
    const backdrop = document.createElement('div'); backdrop.className='qd-focus-backdrop'; backdrop.setAttribute('aria-hidden','true'); backdrop.addEventListener('click',close); document.body.append(backdrop);
    active = {panel,trigger,placeholder,backdrop,inert:new Map(),ancestors:[],portals:new Map(),x:scrollX,y:scrollY,scrollTop:panel.scrollTop,attrs:{}};
    for (const key of ['role','aria-modal','aria-label','tabindex']) active.attrs[key]=panel.getAttribute(key);
    panel.setAttribute('role','dialog'); panel.setAttribute('aria-modal','true'); panel.setAttribute('aria-label',panel.querySelector('h2,h3,h4,h5')?.textContent.trim() || '차트 크게 보기'); panel.setAttribute('tabindex','-1');
    panel.classList.add('qd-focus-active'); document.body.classList.add('qd-focus-open');
    for (let branch=panel;branch && branch!==document.body;branch=branch.parentElement) {
      for (const sibling of branch.parentElement.children) {
        if (sibling===branch || sibling===backdrop || sibling===placeholder || ['SCRIPT','STYLE','LINK'].includes(sibling.tagName)) continue;
        active.inert.set(sibling,sibling.inert); sibling.inert=true;
      }
      if (branch!==panel) { branch.classList.add('qd-focus-ancestor'); active.ancestors.push(branch); }
    }
    trigger.textContent='닫기'; trigger.title='차트 크게 보기 닫기'; trigger.setAttribute('aria-label','차트 크게 보기 닫기'); trigger.setAttribute('aria-expanded','true');
    panel.scrollTop=0; trigger.focus({preventScroll:true}); resize();
  }
  function close() {
    if (!active) return;
    const state=active; active=null;
    for (const [el,inert] of state.inert) el.inert=inert;
    for (const [el,inert] of state.portals) {el.inert=inert;el.classList.remove('qd-focus-portal');}
    state.ancestors.forEach(el=>el.classList.remove('qd-focus-ancestor'));
    state.panel.classList.remove('qd-focus-active'); document.body.classList.remove('qd-focus-open');
    for (const [key,value] of Object.entries(state.attrs)) restoreAttribute(state.panel,key,value);
    state.placeholder.remove(); state.backdrop.remove(); state.panel.scrollTop=state.scrollTop;
    const button=state.trigger.isConnected?state.trigger:state.panel.querySelector('.qd-focus-button');
    if (button) {button.textContent='';button.title='차트 크게 보기';button.setAttribute('aria-label','차트 크게 보기');button.removeAttribute('aria-expanded');}
    window.scrollTo(state.x,state.y); if(button?.isConnected) button.focus({preventScroll:true}); resize();
  }
  document.addEventListener('keydown', event => {
    if (!active) return;
    const popup=portals().find(visible);
    // Native select/listbox Escape first dismisses that control, then the chart.
    if (event.key==='Escape' && !popup) {event.preventDefault();event.stopPropagation();close();return;}
    if (event.key!=='Tab') return;
    const items=[...active.panel.querySelectorAll(controls),...portals().flatMap(el=>[...el.querySelectorAll(controls)])].filter(visible);
    if(!items.length){event.preventDefault();active.panel.focus();return;}
    const index=items.indexOf(document.activeElement);
    if(event.shiftKey && index<=0){event.preventDefault();items.at(-1).focus();}
    else if(!event.shiftKey && (index===items.length-1 || index<0)){event.preventDefault();items[0].focus();}
  },true);
  document.addEventListener('focusin',event=>{
    if(active && !active.panel.contains(event.target) && !portals().some(el=>el.contains(event.target))) active.panel.querySelector('.qd-focus-button')?.focus({preventScroll:true});
  });
  function scan() {
    scheduled=false;
    if(active && !active.panel.isConnected) close();
    const candidates=[...document.querySelectorAll(panels)].filter(panel=>panel.querySelector(charts));
    for(const panel of candidates){
      // The closest chart-bearing panel owns the action; never add nested duplicate actions.
      if(candidates.some(other=>other!==panel && panel.contains(other))) continue;
      const button=makeButton(panel);
      if(active?.panel===panel){button.textContent='닫기';button.title='차트 크게 보기 닫기';button.setAttribute('aria-label','차트 크게 보기 닫기');button.setAttribute('aria-expanded','true');}
    }
    if(active) syncPortals();
  }
  const observer=new MutationObserver(records=>{
    if(!records.some(record=>[...record.addedNodes,...record.removedNodes].some(node=>node.nodeType===1 && !node.matches?.('.qd-focus-button,.qd-focus-tools,.qd-focus-placeholder,.qd-focus-backdrop')))) return;
    if(!scheduled){scheduled=true;requestAnimationFrame(scan);}
  });
  observer.observe(document.body,{childList:true,subtree:true}); scan();
})();

;
if(document.documentElement.dataset.quantDesignProject==='news'){
/* Local reading enhancement: retain the native article nodes and reader state. */
(() => {
  'use strict';
  if (!location.pathname.startsWith('/news/')) return;
  const library = document.querySelector('.library');
  const root = library || document.querySelector('main') || document.body;
  const selector = library ? '.card' : '.issue';
  let current = null;
  const dialog = document.createElement('dialog');
  dialog.className = 'nw3-reader';
  dialog.setAttribute('aria-label', '집중 읽기');
  const bar = document.createElement('div');
  bar.className = 'nw3-reader-bar';
  const label = document.createElement('span');
  label.textContent = '집중 읽기';
  const close = document.createElement('button');
  close.type = 'button';
  close.className = 'nw3-reader-close';
  close.textContent = '← 목록으로';
  bar.append(label, close);
  const content = document.createElement('div');
  content.className = 'nw3-reader-content';
  dialog.append(bar, content);
  root.append(dialog);

  function nativeControl(card) {
    return card.querySelector(library ? '.card-title' : '.issue-detail > summary');
  }
  function expanded(card) {
    return library ? card.classList.contains('open') : card.querySelector('.issue-detail').open;
  }
  function finish() {
    if (!current) return;
    const state = current;
    current = null;
    if (dialog.open) dialog.close();
    document.documentElement.classList.remove('nw3-reading');
    state.card.classList.remove('nw3-focused');
    if (state.placeholder.isConnected) {
      state.placeholder.replaceWith(state.card);
      if (!state.wasOpen && expanded(state.card)) nativeControl(state.card)?.click();
    } else {
      if (!state.wasOpen && expanded(state.card)) nativeControl(state.card)?.click();
      state.card.remove();
    }
    requestAnimationFrame(() => requestAnimationFrame(() => {
      window.scrollTo({top: state.scroll, behavior: 'instant'});
      const target = state.button.isConnected && !state.card.hidden ? state.button : document.querySelector(library ? '#query' : '#search');
      target?.focus({preventScroll:true});
    }));
  }
  function start(card, button) {
    if (current) return;
    const state = {card, button, wasOpen:expanded(card), scroll:window.scrollY, placeholder:document.createComment('news reader position')};
    current = state;
    if (!state.wasOpen) nativeControl(card)?.click();
    // Native daily reader first aligns the article. Move only after that frame.
    requestAnimationFrame(() => {
      if (current !== state || !card.isConnected) { if (current === state) finish(); return; }
      card.before(state.placeholder);
      content.append(card);
      card.classList.add('nw3-focused');
      document.documentElement.classList.add('nw3-reading');
      dialog.showModal();
      dialog.scrollTop = 0;
      close.focus({preventScroll:true});
    });
  }
  close.addEventListener('click', finish);
  dialog.addEventListener('cancel', event => {event.preventDefault(); finish();});
  dialog.addEventListener('close', () => {if (current) finish();});
  // Article backgrounds and titles normally collapse the native card. Keep them
  // readable in the dialog, while links, evidence details and save remain live.
  content.addEventListener('click', event => {
    const target = event.target;
    if (!(target instanceof Element)) return;
    if (target.closest('.card-title,.issue h3 a')) {event.preventDefault(); event.stopPropagation(); return;}
    if (!target.closest('a,button,input,select,textarea,label,summary,[role="button"]')) event.stopPropagation();
  }, true);
  function enhance() {
    root.querySelectorAll(selector).forEach(card => {
      if (card.querySelector('.nw3-read-button')) return;
      // Some archived editions contain the same provenance label twice in a row.
      // Only remove byte-identical neighboring labels from the rendered DOM.
      // Article bodies, source links and the stored edition stay untouched.
      card.querySelectorAll('.location').forEach(label => {
        let next = label.nextElementSibling;
        while (next?.matches('.location') && next.outerHTML === label.outerHTML) {
          const duplicate = next;
          next = duplicate.nextElementSibling;
          duplicate.remove();
        }
      });
      const button = document.createElement('button');
      button.className = 'nw3-read-button';
      button.type = 'button';
      button.textContent = '집중 읽기 ↗';
      button.setAttribute('aria-haspopup','dialog');
      button.setAttribute('aria-label', (card.querySelector('h3')?.textContent.trim() || '기사') + ' · 집중 읽기');
      button.addEventListener('click', event => {event.stopPropagation(); start(card, button);});
      card.append(button);
    });
  }
  enhance();
  const resultRoot = library ? document.getElementById('results') : root;
  if (resultRoot) new MutationObserver(() => {
    if (current && dialog.open && (!current.placeholder.isConnected || current.card.hidden)) finish();
    enhance();
  }).observe(resultRoot, {childList:true, subtree:true, attributes:true, attributeFilter:['hidden']});
})();

/* Weekly narrative navigation: presentation only, with native content ownership. */
(() => {
  'use strict';
  function enhanceWeekly() {
    if (document.body.dataset.qdProject !== 'news') return;
    const narrative = document.querySelector('.weekly-narrative');
    if (!narrative || narrative.dataset.nw4Reader) return;
    const stories = [...narrative.querySelectorAll('.narrative-story')].filter(story =>
      /^[A-Za-z0-9_-]+$/.test(story.id) && story.querySelector('h3'));
    const nativeNav = narrative.querySelector('.narrative-contents');
    if (!stories.length || !nativeNav) return;

    const aside = document.createElement('aside');
    aside.className = 'nw4-weekly-outline';
    aside.setAttribute('aria-label', '주간 이야기 탐색');
    const details = document.createElement('details');
    const summary = document.createElement('summary');
    summary.textContent = '이번 주 이야기';
    const count = document.createElement('span');
    count.className = 'nw4-outline-count';
    count.textContent = String(stories.length);
    summary.append(count);
    details.append(summary);
    const list = document.createElement('ol');
    const targets = [];
    const links = [];
    function linkTo(target, text, className) {
      const a = document.createElement('a');
      a.href = '#' + target.id;
      a.className = className;
      a.textContent = text;
      a.addEventListener('click', event => {
        const original = [...nativeNav.querySelectorAll('a')].find(link => link.hash === a.hash);
        if (original) {
          event.preventDefault();
          const reading = target.closest('.weekly-reading-details')
            || target.querySelector('.weekly-reading-details');
          if (reading && !reading.open) reading.querySelector('summary')?.click();
          original.click(); // Native archive/search/hash handlers remain authoritative.
        } else {
          const previous = target.getAttribute('tabindex');
          target.setAttribute('tabindex', '-1');
          target.focus({preventScroll: true});
          target.scrollIntoView({block: 'start', behavior: 'instant'});
          current();
          target.addEventListener('blur', () => previous === null
            ? target.removeAttribute('tabindex') : target.setAttribute('tabindex', previous), {once: true});
        }
        // Keep an explicit mobile disclosure usable while reading. Its state
        // is not saved and never changes the source article's reader state.
      });
      links.push(a);
      targets.push(target);
      return a;
    }
    stories.forEach(story => {
      const item = document.createElement('li');
      const heading = story.querySelector('h3').cloneNode(true);
      heading.querySelectorAll('.narrative-story-number').forEach(node => node.remove());
      const a = linkTo(story, heading.textContent.trim(), 'nw4-story-link');
      item.append(a);
      list.append(item);
    });
    details.append(list);
    const sections = document.createElement('nav');
    sections.className = 'nw4-outline-sections';
    sections.setAttribute('aria-label', '주간 브리핑 구간');
    [...nativeNav.querySelectorAll('a')].forEach(original => {
      if (!original.hash || original.hash === '#weekly-key-stories') return;
      const target = document.getElementById(original.hash.slice(1));
      if (target) sections.append(linkTo(target, original.textContent.trim(), 'nw4-section-link'));
    });
    details.append(sections);
    aside.append(details);
    narrative.prepend(aside);
    narrative.classList.add('nw4-weekly');
    narrative.dataset.nw4Reader = '1';

    const desktop = matchMedia('(min-width: 1180px)');
    const adapt = () => { details.open = desktop.matches; };
    adapt();
    if (desktop.addEventListener) desktop.addEventListener('change', adapt);
    let queued = false;
    const current = () => {
      queued = false;
      const rootStyle = getComputedStyle(document.documentElement);
      const offset = Math.max((parseFloat(rootStyle
        .getPropertyValue('--qd-header-height')) || 64) + 40,
      (parseFloat(rootStyle.scrollPaddingTop) || 0) + 24);
      // Heading elements inside a section have the same logical position as
      // their containing story/section. No URL or stored reading state changes.
      const positions = targets.map((target, index) => ({target, index,
        top: target.getBoundingClientRect().top})).filter(row => row.target.getClientRects().length);
      const past = positions.filter(row => row.top <= offset).sort((a, b) => b.top - a.top);
      const chosen = past[0] || positions.sort((a, b) => a.top - b.top)[0];
      links.forEach((link, index) => index === chosen?.index
        ? link.setAttribute('aria-current', 'location') : link.removeAttribute('aria-current'));
    };
    const queue = () => {if (!queued) {queued = true; requestAnimationFrame(current);}};
    window.addEventListener('scroll', queue, {passive: true});
    window.addEventListener('resize', queue, {passive: true});
    window.addEventListener('hashchange', queue);
    current();
  }
  if (window.__quantDesignV4?.state === 'ready') enhanceWeekly();
  else window.addEventListener('quant-design-ready', enhanceWeekly, {once: true});
})();

}
;
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

;
/* Presentation-only progressive enhancements. Native controls retain ownership. */
(() => {
  'use strict';
  function tables(scope=document) {
    for(const table of scope.querySelectorAll?.('table')||[]) {
      const parent=table.parentElement;
      if(!parent || !/(auto|scroll)/.test(getComputedStyle(parent).overflowX))continue;
      parent.classList.add('qu-scroll-table');
      if(parent.scrollWidth>parent.clientWidth+1 && !parent.hasAttribute('tabindex')) {
        parent.tabIndex=0;parent.setAttribute('role','region');
        parent.setAttribute('aria-label',(table.caption?.textContent||table.closest('section,article')?.querySelector('h2,h3,h4')?.textContent||'데이터 표').trim()+' 가로 스크롤');
      }
    }
  }
  tables();let pending=false;
  new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;tables();});}).observe(document.body,{childList:true,subtree:true});
  addEventListener('resize',()=>tables());
})();

;
/* Reviewed exact copy only; no calculation, request, input or chart mutation. */
(() => {
  'use strict';
  const rules = {
    'dram-price': [
      ['.page-footer>span', 'DRAM Price Lab · 개인 리서치용 공개 데이터 모니터', 'DRAM Price Lab'],
    ],
    'sox': [
      ['#methodology .method-grid>article', '운영 상세 개인 리서치용이며 투자 조언이 아닙니다. 데이터는 지연되거나 일부 누락될 수 있습니다.', ''],
    ],
    'etf-tracking': [
      ['#research-notice', '연구용 정적 스냅샷 · 잔차 신호는 실제 운용사 주문 확정이나 투자·매매 조언이 아닙니다.', ''],
      ['#decomposition-detail>summary small', '전일 대비 비중 변화의 전체 분석 행', ''],
    ],
  };
  const normalize = value => value.replace(/\s+/g, ' ').trim();
  function refine(scope) {
    const project = document.documentElement.dataset.quantDesignProject;
    for (const [selector, before, after] of rules[project] || []) {
      const nodes = [...(scope.matches?.(selector) ? [scope] : []), ...scope.querySelectorAll(selector)];
      for (const node of nodes) {
        if (normalize(node.textContent) !== before) continue;
        if (after) node.textContent = after;
        else node.remove();
      }
    }
  }
  function start() {
    refine(document);
    new MutationObserver(records => {
      for (const record of records) for (const node of record.addedNodes) {
        if (node.nodeType === 1) refine(node);
      }
    }).observe(document.body, {childList:true, subtree:true});
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, {once:true});
  else start();
  addEventListener('quant-design-ready', () => refine(document), {once:true});
})();

;
/* Exact UI copy edits only; never inspect article prose, financial output or failure messages. */
(() => {
  'use strict';
  const rules = {
    'investment-journal': [
      ['.section-head p','비교하고 싶은 지수를 선택하세요. 모두 해제하면 내 수익률만 표시합니다.',''],
      ['.auth-story-bottom','나만의 계정 · 기기 간 동기화 · 원본은 기기에서 분석',''],
      ['.demo-strip > span','가상 데이터 체험 중 · 실제 보유·시세가 아닙니다','예시 데이터'],
      ['.footer > span','시연용 가상 데이터','']
    ]
  };
  function apply() {
    const project = document.body?.dataset.qdProject;
    for (const [selector, before, after] of rules[project] || []) {
      for (const node of document.querySelectorAll(selector)) {
        if (node.textContent.trim() !== before || node.children.length) {
          if (!after) delete node.dataset.qdRedundantCopy;
          continue;
        }
        // Keep the React-owned node in place. Only this reviewed literal is changed.
        if (after) node.textContent = after;
        else node.dataset.qdRedundantCopy = 'true';
      }
    }
  }
  let scheduled = false;
  const observer = new MutationObserver(() => {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => {scheduled = false;apply();});
  });
  if (document.body) {apply();observer.observe(document.body,{subtree:true,childList:true,characterData:true});}
  else document.addEventListener('DOMContentLoaded',()=>{apply();observer.observe(document.body,{subtree:true,childList:true,characterData:true});},{once:true});
})();

;
if(window.__quantDesignV4?.state!=='ready')throw new Error('Shared shell initialization failed');
window.__quantDesignV3.state='ready';
window.__quantDesignUnified={version:'0.5.0',foundation:'0.4.0',project:document.documentElement.dataset.quantDesignProject,state:'ready'};
const footer=document.querySelector('.qd-side-footer small');if(footer)footer.textContent='Quant Research · v'+window.__quantDesignUnified.version;
window.QuantFirstPaint?.finish();
window.dispatchEvent(new CustomEvent('quant-design-ready',{detail:{project:window.__quantDesignUnified.project,version:'0.4.0'}}));
window.dispatchEvent(new CustomEvent('quant-design-unified-ready',{detail:{project:window.__quantDesignUnified.project,version:'0.5.0'}}));
}catch(error){window.__quantDesignV3.state='error';window.QuantFirstPaint?.fail('runtime');throw error}})();
