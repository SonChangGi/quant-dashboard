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
