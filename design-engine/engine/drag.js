/** Mode-free range gesture. Coordinates and units remain the renderer's responsibility. */
export function bindRangeDrag(element,{hit,onRange,onClear,onPan,onPinch,enabled=()=>true,axis='x'}) {
 let drag=null,multi=null,suppressUntil=0;
 const oldTouch=element.style?.touchAction;
 if(element.style)element.style.touchAction='pan-y';
 const stop=e=>{e.preventDefault();e.stopPropagation();};
 const point=e=>{const r=element.getBoundingClientRect();return [e.clientX-r.left,e.clientY-r.top];};
 function down(e){
  if(!enabled()||multi||e.button>0||e.altKey||e.target?.closest?.('button,summary,input,select'))return;
  const p=point(e),index=hit(p);if(index==null)return;
  drag={id:e.pointerId,x:e.clientX,y:e.clientY,start:index,last:index,active:false,type:e.pointerType};
 }
 function move(e){
  if(!drag||multi||e.pointerId!==drag.id)return;
  const dx=e.clientX-drag.x,dy=e.clientY-drag.y;
  if(!drag.active){if(drag.type==='touch'&&Math.abs(dy)>Math.abs(dx)&&Math.abs(dy)>7){drag=null;return;}if(Math.abs(axis==='y'?dy:dx)<7)return;drag.active=true;try{element.setPointerCapture?.(e.pointerId);}catch{}}
  stop(e);const index=hit(point(e),true);if(index==null)return;drag.last=index;onRange(drag.start,index);
 }
 function up(e){if(!drag||e.pointerId!==drag.id)return;if(drag.active){stop(e);onRange(drag.start,drag.last);suppressUntil=Date.now()+450;}try{element.releasePointerCapture?.(e.pointerId);}catch{}drag=null;}
 function cancel(){drag=null;}
 function click(e){if(Date.now()<suppressUntil){stop(e);e.stopImmediatePropagation?.();return;}if(enabled()&&!e.altKey&&hit(point(e))!=null)onClear();}
 const fingers=e=>{const [a,b]=e.touches;return {x:(a.clientX+b.clientX)/2,distance:Math.hypot(a.clientX-b.clientX,a.clientY-b.clientY)};};
 function touchStart(e){if(e.touches.length!==2||!enabled())return;stop(e);drag=null;multi=fingers(e);suppressUntil=Date.now()+450;}
 function touchMove(e){if(!multi||e.touches.length!==2)return;stop(e);e.stopImmediatePropagation?.();const next=fingers(e),r=element.getBoundingClientRect();if(multi.distance>0&&next.distance>0)onPinch?.(multi.distance/next.distance,(next.x-r.left)/r.width);onPan?.((next.x-multi.x)/r.width);multi=next;suppressUntil=Date.now()+450;}
 function touchEnd(e){if(multi){suppressUntil=Date.now()+450;drag=null;}if(e.touches.length<2)multi=null;}
 const handlers={pointerdown:down,pointermove:move,pointerup:up,pointercancel:cancel,click,touchstart:touchStart,touchmove:touchMove,touchend:touchEnd,touchcancel:touchEnd};
 for(const [name,fn] of Object.entries(handlers))element.addEventListener(name,fn,{capture:true,passive:false});
 return ()=>{for(const [name,fn] of Object.entries(handlers))element.removeEventListener(name,fn,true);if(element.style)element.style.touchAction=oldTouch??'';drag=null;multi=null;};
}

export function rangeSeries(spec){return spec.kind==='fan'?[{name:'관측',data:spec.observed},{name:'중앙 추정',data:spec.center}]:spec.series??[];}

export function rangeValues(spec,range,legend={}){
 if(!range)return [];
 return rangeSeries(spec).filter(s=>legend[s.name]!==false).map(s=>{
  const a=s.data[range.startIndex],b=s.data[range.endIndex],valid=Number.isFinite(a)&&Number.isFinite(b),measure=s.measure??spec.measure??(spec.unit==='%'?'pp':'relative');
  const difference=valid?b-a:null;
  return {name:s.name,start:a,end:b,difference,change:!valid?null:measure==='relative'?(a>0?(b/a-1)*100:null):measure==='pp'&&spec.unit==='확률'?difference*100:difference,unit:measure==='relative'?'%':measure==='pp'?'%p':spec.unit??'',measure};
 });
}
