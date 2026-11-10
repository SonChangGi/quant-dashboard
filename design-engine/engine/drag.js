import {bindTouchChart, navigateChartWindow} from './touch.js?v=043';

/** Mouse range selection and touch inspection share the renderer's coordinates. */
export function bindRangeDrag(element, {hit, onInspect, onRange, onClear, onNavigate, rangeReadout, enabled = () => true, axis = 'x', touch = true}) {
  let drag = null;
  let suppressClick = false;
  const point = e => {
    const bounds = element.getBoundingClientRect();
    return [e.clientX - bounds.left, e.clientY - bounds.top];
  };
  const stop = e => {e.preventDefault(); e.stopImmediatePropagation();};
  const touchCleanup = touch ? bindTouchChart(element, {hit, inspect: onInspect, compare: onRange, clear: onClear, navigate: onNavigate, rangeReadout, enabled, axis}) : null;
  function down(e) {
    if (e.pointerType === 'touch') return;
    suppressClick = false;
    if (!enabled() || e.button !== 0 || e.altKey || e.target?.closest?.('button,summary,input,select,a')) return;
    const start = hit(point(e));
    if (start != null) drag = {id: e.pointerId, x: e.clientX, y: e.clientY, start, active: false};
  }
  function move(e) {
    if (!drag || e.pointerId !== drag.id) return;
    if (!drag.active) {
      if (Math.abs(axis === 'y' ? e.clientY - drag.y : e.clientX - drag.x) < 7) return;
      drag.active = true;
      try { element.setPointerCapture?.(e.pointerId); } catch {}
    }
    stop(e);
    const index = hit(point(e), true);
    if (index != null) onRange(drag.start, index);
  }
  function end(e) {
    if (!drag || e.pointerId !== drag.id) return;
    if (drag.active) {
      suppressClick = true;
      stop(e);
    }
    drag = null;
  }
  function click(e) {
    if (suppressClick) {
      suppressClick = false;
      stop(e);
      return;
    }
    if (enabled() && !e.altKey && hit(point(e)) != null) onClear();
  }
  const handlers = {pointerdown: down, pointermove: move, pointerup: end, pointercancel: end, click};
  for (const [type, handler] of Object.entries(handlers)) element.addEventListener(type, handler, true);
  return () => {
    touchCleanup?.();
    for (const [type, handler] of Object.entries(handlers)) element.removeEventListener(type, handler, true);
    drag = null;
  };
}

export {navigateChartWindow};

export function rangeSeries(spec){return spec.kind==='fan'?[{name:'관측',data:spec.observed},{name:'중앙 추정',data:spec.center}]:spec.series??[];}

export function rangeValues(spec,range,legend={}){
 if(!range)return [];
 return rangeSeries(spec).filter(s=>legend[s.name]!==false).map(s=>{
  const a=s.data[range.startIndex],b=s.data[range.endIndex],valid=Number.isFinite(a)&&Number.isFinite(b),measure=s.measure??spec.measure??(spec.unit==='%'?'pp':'relative');
  const difference=valid?b-a:null;
  return {name:s.name,start:a,end:b,difference,change:!valid?null:measure==='relative'?(a>0?(b/a-1)*100:null):measure==='pp'&&spec.unit==='확률'?difference*100:difference,unit:measure==='relative'?'%':measure==='pp'?'%p':spec.unit??'',measure};
 });
}
