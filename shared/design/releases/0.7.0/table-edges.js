/* Read-only scroll cues. Native table layout, sorting and scroll remain owners. */
(()=>{'use strict';
const entries=new Map();let pending=false;
function sync(entry){
 const {wrap,host,left,right}=entry,r=wrap.getBoundingClientRect(),h=host.getBoundingClientRect();
 const visible=wrap.getClientRects().length&&innerWidth<=600&&wrap.scrollWidth>wrap.clientWidth+1;
 for(const edge of [left,right]){edge.style.top=`${r.top-h.top+host.scrollTop-host.clientTop+wrap.clientTop}px`;edge.style.height=`${wrap.clientHeight}px`;}
 left.style.left=`${r.left-h.left+host.scrollLeft-host.clientLeft+wrap.clientLeft}px`;
 right.style.left=`${r.left-h.left+host.scrollLeft-host.clientLeft+wrap.clientLeft+wrap.clientWidth-16}px`;
 left.hidden=!visible||wrap.scrollLeft<=1;right.hidden=!visible||wrap.scrollLeft+wrap.clientWidth>=wrap.scrollWidth-1;
 wrap.dataset.qpScrollEdges=visible?`${left.hidden?'':'left'} ${right.hidden?'':'right'}`.trim():'none';
}
function scan(){pending=false;
 for(const [wrap,e] of entries){if(!wrap.isConnected){e.observer.disconnect();e.left.remove();e.right.remove();entries.delete(wrap)}else sync(e)}
 for(const table of document.querySelectorAll('table:not([role=grid]):not(.calendar-grid)')){
  let wrap=table.parentElement;
  while(wrap&&wrap!==document.body&&!/(auto|scroll)/.test(getComputedStyle(wrap).overflowX))wrap=wrap.parentElement;
  if(!wrap||wrap===document.body||entries.has(wrap)||wrap.scrollWidth<=wrap.clientWidth+1)continue;
  const host=wrap.parentElement;if(!host||host.matches('table,tbody,tr'))continue;
  if(getComputedStyle(host).position==='static')host.style.position='relative';
  const left=document.createElement('span'),right=document.createElement('span');
  left.className='qp-table-edge qp-table-edge-left';right.className='qp-table-edge qp-table-edge-right';
  for(const edge of [left,right]){edge.setAttribute('aria-hidden','true');edge.hidden=true;host.append(edge)}
  const entry={wrap,host,left,right,observer:new ResizeObserver(()=>sync(entry))};entries.set(wrap,entry);
  entry.observer.observe(wrap);entry.observer.observe(table);wrap.addEventListener('scroll',()=>sync(entry),{passive:true});sync(entry);
 }
}
function schedule(){if(!pending){pending=true;requestAnimationFrame(scan)}}
function start(){scan();new MutationObserver(schedule).observe(document.body,{childList:true,subtree:true});addEventListener('resize',schedule,{passive:true})}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
