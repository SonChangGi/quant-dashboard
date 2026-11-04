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
