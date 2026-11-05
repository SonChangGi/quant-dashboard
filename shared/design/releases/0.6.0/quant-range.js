/* Source-data chart measurement. No network or data writes. */
(function(scope){'use strict';
const finite=v=>typeof v==='number'&&Number.isFinite(v);
function delta(a,b,measure='relative',scale=1){if(!finite(a)||!finite(b))return {value:null,unit:'missing'};if(measure==='pp')return {value:(b-a)*scale,unit:'%p'};if(measure==='relative'&&a>0)return {value:(b/a-1)*100,unit:'%'};return {value:(b-a)*scale,unit:'absolute'};}
function compute(c,start,end){
 if(c.kind==='scatter'){const pts=(c.scatter||[]).filter(p=>finite(p.x)&&finite(p.y)&&p.x>=Math.min(start.x,end.x)&&p.x<=Math.max(start.x,end.x)&&p.y>=Math.min(start.y,end.y)&&p.y<=Math.max(start.y,end.y));return {kind:'scatter',count:pts.length,points:pts,x:pts.length?[Math.min(...pts.map(p=>p.x)),Math.max(...pts.map(p=>p.x))]:null,y:pts.length?[Math.min(...pts.map(p=>p.y)),Math.max(...pts.map(p=>p.y))]:null};}
 const a=Math.min(start.index,end.index),b=Math.max(start.index,end.index),domain=c.domain||[];if(!domain[a]||!domain[b])return null;
 return {kind:c.kind||'timeseries',a,b,start:domain[a],end:domain[b],count:b-a+1,series:(c.series||[]).map(s=>{const points=new Map(s.points.map(p=>[p.key,p.value])),av=points.get(domain[a].key),bv=points.get(domain[b].key),values=domain.slice(a,b+1).map(d=>points.get(d.key)).filter(finite);return {...s,start:av,end:bv,delta:delta(av,bv,s.measure,s.scale??1),count:values.length,sum:s.aggregate==='sum'?values.reduce((x,y)=>x+y,0):null,min:values.length?Math.min(...values):null,max:values.length?Math.max(...values):null};})};
}
function pointResult(c,p){
 if(c.kind==='scatter'){const point=(c.scatter||[]).find(r=>String(r.id)===String(p.pointId));return point?{kind:'point',chartKind:'scatter',point,domain:{key:point.id,label:point.label||point.id},series:[]}:null}
 const d=c.domain?.[p.index];if(!d)return null;return {kind:'point',chartKind:c.kind||'timeseries',domain:d,index:p.index,series:(c.series||[]).map(series=>{const p=series.points.find(r=>r.key===d.key);return {...series,unit:series.pointUnit??series.unit,scale:series.pointScale??series.scale,value:p&&Object.hasOwn(p,'pointValue')?p.pointValue:p?.value}})};
}
function latestIndex(c,id){const series=(c.series||[]).find(s=>s.id===id)||c.series?.[0];if(!series)return null;const values=new Map(series.points.map(p=>[p.key,p.value]));for(let i=(c.domain?.length||0)-1;i>=0;i--)if(finite(values.get(c.domain[i].key)))return i;return null}
function identity(c){return JSON.stringify([c.kind,c.privacyHidden,(c.domain||[]).map(d=>d.key),(c.series||[]).map(s=>[s.id,s.unit,s.measure,s.scale,s.pointUnit,s.pointScale,s.points.map(p=>[p.key,p.value,p.pointValue])]),(c.scatter||[]).map(p=>[p.id,p.x,p.y])])}
const api={version:'1.2.0',delta,compute,pointResult,latestIndex,entries:new Map()};api.placeHud=function(bounds,size,origin,previous,pointer,dragging){const ix=Math.max(0,Math.min(6,(bounds.right-bounds.left-size.width)/2)),iy=Math.max(0,Math.min(6,(bounds.bottom-bounds.top-size.height)/2)),left=bounds.left+ix,right=Math.max(left,bounds.right-size.width-ix),top=bounds.top+iy,bottom=Math.max(top,bounds.bottom-size.height-iy);const corners={tl:{left,top},tr:{left:right,top},bl:{left,top:bottom},br:{left:right,top:bottom}};let corner=previous||(origin?(origin.y<(bounds.top+bounds.bottom)/2?'b':'t')+(origin.x<(bounds.left+bounds.right)/2?'r':'l'):'tl');const hit=(p,margin=0)=>pointer&&pointer.x>=p.left-margin&&pointer.x<=p.left+size.width+margin&&pointer.y>=p.top-margin&&pointer.y<=p.top+size.height+margin;if(dragging&&hit(corners[corner],8)){const opposite={tl:'br',tr:'bl',bl:'tr',br:'tl'}[corner];if(!hit(corners[opposite],20))corner=opposite}return {...corners[corner],corner}};scope.QuantRange=api;if(typeof module!=='undefined')module.exports=api;if(!scope.document)return;
const doc=scope.document,num=(v,precision=3)=>finite(v)?v.toLocaleString('ko-KR',{maximumFractionDigits:precision}):'—',digits=s=>s.precision??(/^(원|KRW)$/i.test(s.unit||'')?0:3);
api.register=function(c){
 if(!c?.element||typeof c.locate!=='function')return {destroy(){},clear(){},present(){},setSeries(){}};
 const previous=api.entries.get(c.id),saved=previous?.exportState?.();const restore=saved&&saved.identity===identity(c)&&c.retainSelection!==false?saved:null;previous?.destroy();
 const el=c.element,host=c.host||el.parentElement,abort=new AbortController();
 let drag=null,selection=null,pointSelection=null,computed=null,cursor=0,anchor=null,blockedClick=false,selectedSeries=c.primarySeries||null,corner=null,pointer=null,origin=null;
 const ui=doc.createElement('div');ui.className='qr-measure';ui.dataset.chartId=c.id;
 const toolbar=doc.createElement('div');toolbar.className='qr-toolbar';
 const label=doc.createElement('span');label.textContent='드래그 측정';label.title='Shift + ← → 구간 선택 · Esc 초기화';
 const touch=doc.createElement('button');touch.type='button';touch.textContent='터치 선택';touch.setAttribute('aria-pressed','false');
 const reset=doc.createElement('button');reset.type='button';reset.textContent='초기화';reset.disabled=true;
 const output=doc.createElement('div');output.className='qr-readout';output.setAttribute('role','status');output.setAttribute('aria-live','polite');
 toolbar.append(label,touch,reset);ui.append(toolbar,output);host.append(ui);
 const overlay=doc.createElement('div');overlay.className='qr-band';overlay.hidden=true;doc.body.append(overlay);
 const hud=doc.createElement('div');hud.className='qr-hud';hud.hidden=true;hud.dataset.chartId=c.id;hud.setAttribute('role','group');hud.setAttribute('aria-label','선택 구간 측정값');
 const hudTop=doc.createElement('div');hudTop.className='qr-hud-top';
 const seriesDot=doc.createElement('i');seriesDot.className='qr-series-dot';seriesDot.setAttribute('aria-hidden','true');
 const seriesName=doc.createElement('span');seriesName.className='qr-hud-name';
 const seriesSelect=doc.createElement('select');seriesSelect.className='qr-hud-select';seriesSelect.setAttribute('aria-label','측정 계열');
 const hudReset=doc.createElement('button');hudReset.className='qr-hud-reset';hudReset.type='button';hudReset.textContent='×';hudReset.setAttribute('aria-label','구간 선택 초기화');
 const major=doc.createElement('strong');major.className='qr-hud-value';
 const dates=doc.createElement('span');dates.className='qr-hud-dates';
 const endpoints=doc.createElement('span');endpoints.className='qr-hud-endpoints';
 hudTop.append(seriesDot,seriesName,seriesSelect,hudReset);hud.append(hudTop,major,dates,endpoints);doc.body.append(hud);
 let touchEnabled=false;
 touch.onclick=()=>{touchEnabled=!touchEnabled;touch.setAttribute('aria-pressed',String(touchEnabled));el.style.touchAction=touchEnabled?'none':'';c.onTouchMode?.(touchEnabled)};
 const originalTab=el.getAttribute('tabindex');if(originalTab===null)el.tabIndex=0;el.dataset.quantRange=c.id;
 const tip=c.kind==='scatter'?'드래그 또는 축 범위 입력 · Esc 초기화':(c.kind==='category'?'표시 순서대로 구간 선택':'드래그로 구간 선택')+' · Shift + ← → · Esc 초기화';output.textContent=tip;
 if(c.kind==='scatter'){
  const details=doc.createElement('details');details.className='qr-range-inputs';const summary=doc.createElement('summary');summary.textContent='범위 입력';details.append(summary);
  const inputs=[],form=doc.createElement('form');form.className='qr-scatter-inputs';
  for(const [axis,name,vals] of [['x',c.scatterAxes?.xLabel||'X',c.xDomain||[0,1]],['y',c.scatterAxes?.yLabel||'Y',c.yDomain||[0,1]]])for(let i=0;i<2;i++){
   const input=doc.createElement('input');input.type='number';input.step='any';input.value=Number(vals[i].toPrecision(8));input.setAttribute('aria-label',name+(i?' 끝':' 시작'));inputs.push(input);
   const field=doc.createElement('label');field.textContent=name+(i?' 끝':' 시작');field.append(input);form.append(field);
  }
  const apply=doc.createElement('button');apply.type='submit';apply.textContent='범위 적용';form.append(apply);
  form.onsubmit=e=>{e.preventDefault();const v=inputs.map(i=>i.value===''?NaN:Number(i.value));if(v.every(Number.isFinite)){corner=null;origin=null;paint({start:{x:v[0],y:v[2]},end:{x:v[1],y:v[3]}})}};
  details.append(form);ui.append(details);
 }
 function clear(){selection=null;pointSelection=null;computed=null;focusSeries(null,'clear');anchor=null;corner=null;origin=null;overlay.hidden=true;hud.hidden=true;ui.dataset.selected='false';reset.disabled=true;output.textContent=tip;c.onChange?.(null,null)}
 function requestReset(){clear();c.onReset?.();el.focus({preventScroll:true})}
 reset.onclick=requestReset;hudReset.onclick=requestReset;
 seriesSelect.onchange=()=>selectSeries(seriesSelect.value,{origin:'hud'});
 function focusSeries(id,origin){
  for(const mark of el.querySelectorAll('[data-qr-series-id]')){if(mark.hasAttribute('data-qr-hit'))continue;const index=mark.dataset.qrIndex===undefined?null:Number(mark.dataset.qrIndex),inCategory=c.kind!=='category'||index===null||(pointSelection?index===pointSelection.index:selection?index>=Math.min(selection.start.index,selection.end.index)&&index<=Math.max(selection.start.index,selection.end.index):true),active=id!==null&&mark.dataset.qrSeriesId===String(id)&&inCategory;mark.classList.toggle('qr-series-active',active);mark.classList.toggle('qr-series-muted',id!==null&&!active)}
  el.dataset.qrFocusedSeries=id??'';if(origin!=='refresh')c.onSeriesFocus?.(id,{origin});
 }
 function selectPoint(p){
  const id=p.seriesId??selectedSeries??c.series?.[0]?.id;let index=p.index;
  if(c.kind!=='scatter'&&!Number.isInteger(index))index=c.currentIndex?.()??(el.dataset.qrCurrentIndex!==undefined?Number(el.dataset.qrCurrentIndex):null)??pointSelection?.index??latestIndex(c,id);
  const point={mode:'point',seriesId:id,index,pointId:p.pointId,origin:p.origin||'line'};
  const result=pointResult(c,point);if(!result)return;
  selectedSeries=id;selection=null;pointSelection=point;corner=null;
  c.onSeriesRequest?.(id,{mode:'point',index,pointId:p.pointId,origin:point.origin});
  paintPoint(point,result);focusSeries(id??null,point.origin);
 }
 function selectSeries(id,options={}){
  if(!(c.series||computed?.series||[]).some(s=>String(s.id)===String(id)))return;
  selectedSeries=String(id);
  if(selection){c.onSeriesRequest?.(selectedSeries,{mode:'range',selection,origin:options.origin||'legend'});c.onSeriesChange?.(selectedSeries);paint(selection,computed);focusSeries(selectedSeries,options.origin||'legend')}
  else selectPoint({seriesId:selectedSeries,index:options.pointIndex,origin:options.origin||'legend'});
 }
 function paintPoint(point,result){
  selection=null;pointSelection=point;computed=result;reset.disabled=false;ui.dataset.selected='true';overlay.hidden=true;output.replaceChildren();
  const metric=result.series.find(s=>s.id===selectedSeries)||result.series[0];
  output.textContent=c.privacyHidden?`${result.domain.label} · 금액 숨김`:result.chartKind==='scatter'?`${result.domain.label} · ${c.scatterAxes?.xLabel||'X'} ${num(result.point.x)} · ${c.scatterAxes?.yLabel||'Y'} ${num(result.point.y)}`:`${result.domain.label} · ${metric?.label||''} ${num(finite(metric?.value)?metric.value*(metric.scale??1):null,metric?digits(metric):3)} ${metric?.unit||''}`;
  const {clip,focus}=visibleClip();renderHud(result,clip,focus);c.onPointChange?.(point,result);
 }
 function repaint(){if(selection)paint(selection,computed);else if(pointSelection)paintPoint(pointSelection,computed)}
 function clickAction(e){
  if(blockedClick){e.preventDefault();e.stopImmediatePropagation();return}
  if(e.target.closest?.('input,select,textarea,a,summary,[data-qr-native-control]'))return;
  if(e.target.closest?.('button')&&!e.target.closest?.('[data-qr-series-id],[data-qr-point-id],[data-qr-index]'))return;
  const tagged=e.target.closest?.('[data-qr-series-id],[data-qr-point-id],[data-qr-index]');
  if(tagged?.dataset.qrChartId&&tagged.dataset.qrSeriesId){selectSeries(tagged.dataset.qrSeriesId,{origin:'legend'});return}
  const hit=c.hitPoint?.(e)||null;
  const seriesId=c.hitSeries?c.hitSeries(e):(hit?.seriesId??tagged?.dataset.qrSeriesId);
  const pointId=hit?.pointId??tagged?.dataset.qrPointId;
  const index=hit?.index??(tagged?.dataset.qrIndex!==undefined?Number(tagged.dataset.qrIndex):c.locate(e)?.index);
  if(c.kind==='scatter'&&pointId!=null){selectPoint({pointId,origin:'line'});return}
  if(seriesId!=null){selectSeries(String(seriesId),{pointIndex:index,origin:'line'});return}
  const {clip}=visibleClip();if(e.clientX>=clip.left&&e.clientX<=clip.right&&e.clientY>=clip.top&&e.clientY<=clip.bottom){requestReset()}
 }
 function visibleClip(){
  const rect=el.getBoundingClientRect();let clip={left:rect.left,top:rect.top,right:rect.right,bottom:rect.bottom};
  let plot=c.plotRect?.();
  if(!plot&&c.project){const full=c.kind==='scatter'&&c.xDomain&&c.yDomain?{start:{x:c.xDomain[0],y:c.yDomain[0]},end:{x:c.xDomain[1],y:c.yDomain[1]}}:c.domain?.length>1?{start:{index:0},end:{index:c.domain.length-1}}:null;if(full)plot=c.project(full)}
  if(plot&&plot.width>0&&plot.height>0)clip={left:rect.left+plot.left,top:rect.top+plot.top,right:rect.left+plot.left+plot.width,bottom:rect.top+plot.top+plot.height};
  for(let parent=el.parentElement;parent&&parent!==doc.body;parent=parent.parentElement){const style=scope.getComputedStyle(parent),r=parent.getBoundingClientRect();if(/auto|scroll|hidden|clip/.test(style.overflowX)){clip.left=Math.max(clip.left,r.left);clip.right=Math.min(clip.right,r.right)}if(/auto|scroll|hidden|clip/.test(style.overflowY)){clip.top=Math.max(clip.top,r.top);clip.bottom=Math.min(clip.bottom,r.bottom)}}
  clip.left=Math.max(0,clip.left);clip.right=Math.min(scope.innerWidth,clip.right);clip.top=Math.max(0,clip.top);clip.bottom=Math.min(scope.innerHeight,clip.bottom);
  const focus=el.closest('.qd-focus-active,[role="dialog"],dialog');
  if(!focus)for(const header of doc.querySelectorAll('header,[role="banner"],.qd-shell')){const style=scope.getComputedStyle(header),r=header.getBoundingClientRect();if(/fixed|sticky/.test(style.position)&&r.top<Math.min(160,scope.innerHeight*.2)&&r.bottom>0&&r.left<clip.right&&r.right>clip.left)clip.top=Math.max(clip.top,r.bottom)}
  return {rect,clip,focus};
 }
 function renderHud(r,clip,focus){
  const portal=focus||doc.body;for(const node of [overlay,hud])if(node.parentElement!==portal)portal.append(node);hud.inert=false;
  const width=clip.right-clip.left,height=clip.bottom-clip.top;
  if(width<100||height<24){hud.hidden=true;return}
  const compact=height<130;hud.dataset.compact=String(compact);hud.dataset.micro=String(height<40);hud.dataset.dragging=String(!!drag?.moved);hud.dataset.privacy=String(!!c.privacyHidden);
  hud.setAttribute('aria-label',r.kind==='point'?'선택 관측값':'선택 구간 측정값');
  const series=r.series||[];
  if(!series.some(s=>s.id===selectedSeries))selectedSeries=series.find(s=>s.delta?.value!==null)?.id||series[0]?.id;
  const metric=series.find(s=>s.id===selectedSeries)||series[0];
  const options=series.map(s=>s.id+'\0'+s.label).join('\n');
  if(seriesSelect.dataset.options!==options){seriesSelect.replaceChildren(...series.map(s=>{const option=doc.createElement('option');option.value=s.id;option.textContent=s.label;return option}));seriesSelect.dataset.options=options}
  if(metric)seriesSelect.value=metric.id;
  seriesSelect.hidden=series.length<2;seriesName.hidden=series.length>1;seriesName.textContent=metric?.label||(r.kind==='scatter'?'산점도':'선택 구간');
  const mark=[...el.querySelectorAll('[data-qr-series-id]')].find(n=>n.dataset.qrSeriesId===metric?.id&&!n.hasAttribute('data-qr-hit'));const colored=mark&&(mark.matches('path,circle,line')?mark:mark.querySelector('path:not([data-qr-hit]):not([class*=hit]),circle'));const paintColor=metric?.color||(colored?scope.getComputedStyle(colored).stroke:null);seriesDot.style.background=paintColor||'var(--qd-muted,#87929a)';seriesDot.hidden=!paintColor;
  dates.textContent=r.kind==='point'?r.domain.label:r.kind==='scatter'?'선택한 점의 범위':r.start.label+' → '+r.end.label;
  major.dataset.direction='neutral';
  if(c.privacyHidden){major.textContent='••••';endpoints.textContent='금액 숨김'}
  else if(r.kind==='point'){if(r.chartKind==='scatter'){seriesName.textContent=r.domain.label;major.textContent=num(r.point.x);endpoints.textContent=(c.scatterAxes?.xLabel||'X')+' · '+(c.scatterAxes?.yLabel||'Y')+' '+num(r.point.y)}else{major.textContent=num(finite(metric?.value)?metric.value*(metric.scale??1):null,metric?digits(metric):3);const unit=doc.createElement('small');unit.className='qr-hud-unit';unit.textContent=' '+(metric?.unit||'');major.append(unit);endpoints.textContent=finite(metric?.value)?'':'해당 날짜 관측 없음'}}
  else if(r.kind==='scatter'){major.textContent=r.count+'개';endpoints.textContent=r.count?`${c.scatterAxes?.xLabel||'X'} ${num(r.x[0])}–${num(r.x[1])} · ${c.scatterAxes?.yLabel||'Y'} ${num(r.y[0])}–${num(r.y[1])}`:'선택된 점 없음'}
  else if(r.kind==='category'){
   major.textContent=metric?.sum!==null&&metric?.sum!==undefined?num(metric.sum*(metric.scale??1),digits(metric))+' '+(metric.unit||''):r.count+'개';
   endpoints.textContent=metric?`${metric.sum!==null?'합계 · ':''}범위 ${num(metric.min===null?null:metric.min*(metric.scale??1),digits(metric))}–${num(metric.max===null?null:metric.max*(metric.scale??1),digits(metric))} ${metric.unit||''}`:'';
  }else if(metric){
   const value=metric.delta.value,unit=metric.delta.unit==='absolute'?metric.unit||'':metric.delta.unit;
   major.textContent=value===null?'—':(value>0?'+':'')+num(value,unit==='%'||unit==='%p'?3:digits(metric))+' '+unit;
   major.dataset.direction=value===null||value===0?'neutral':value>0?'positive':'negative';
   endpoints.textContent=value===null?'끝점 관측 없음':`${num(finite(metric.start)?metric.start*(metric.scale??1):null,digits(metric))} → ${num(finite(metric.end)?metric.end*(metric.scale??1):null,digits(metric))} ${metric.unit||''}`;
  }else{major.textContent='—';endpoints.textContent='표시할 계열 없음'}
  const maxWidth=Math.max(100,width-12);hud.style.width=Math.min(compact?320:232,maxWidth)+'px';hud.style.maxHeight=height+'px';hud.style.zIndex=focus?'2147483002':'401';hud.hidden=false;
  const size={width:hud.offsetWidth,height:hud.offsetHeight};
  const placed=api.placeHud(clip,size,origin,corner,pointer,!!drag?.moved);corner=placed.corner;
  hud.style.left=placed.left+'px';hud.style.top=placed.top+'px';
 }
 function paint(s,provided){
  pointSelection=null;selection=s;const r=provided||compute(c,s.start,s.end);if(!r)return;computed=r;reset.disabled=false;ui.dataset.selected='true';output.replaceChildren();
  const heading=doc.createElement('strong');heading.textContent=r.kind==='scatter'?`${r.count}개 선택`:`${r.start.label} → ${r.end.label} · ${r.count}개 ${r.kind==='category'?'항목':'관측점'}`;output.append(heading);
  if(c.privacyHidden)output.append(doc.createTextNode(' · 금액 숨김'));
  else if(r.kind==='scatter'){const detail=doc.createElement('span');detail.textContent=r.count?`${c.scatterAxes?.xLabel||'X'} ${num(r.x[0])}–${num(r.x[1])} · ${c.scatterAxes?.yLabel||'Y'} ${num(r.y[0])}–${num(r.y[1])}`:'선택된 점 없음';output.append(detail)}
  else for(const s of r.series){const line=doc.createElement('span');if(r.kind==='category')line.textContent=`${s.label} · ${s.count}개 · ${num(s.min===null?null:s.min*(s.scale??1),digits(s))}–${num(s.max===null?null:s.max*(s.scale??1),digits(s))} ${s.unit||''}${s.sum!==null?' · 합계 '+num(s.sum*(s.scale??1),digits(s))+' '+(s.unit||''):''}`;else line.textContent=`${s.label} ${num(finite(s.start)?s.start*(s.scale??1):null,digits(s))} → ${num(finite(s.end)?s.end*(s.scale??1):null,digits(s))} ${s.unit||''} · ${s.delta.value===null?'끝점 관측 없음':(s.delta.value>0?'+':'')+num(s.delta.value,s.delta.unit==='absolute'?digits(s):3)+' '+(s.delta.unit==='absolute'?s.unit||'':s.delta.unit)}`;output.append(line)}
  const {rect,clip,focus}=visibleClip();
  if(c.project&&!c.privacyHidden&&c.band!==false){const box=c.project(s);if(box&&box.width>0&&box.height>0){const left=Math.max(clip.left,rect.left+box.left),top=Math.max(clip.top,rect.top+box.top),right=Math.min(clip.right,rect.left+box.left+box.width),bottom=Math.min(clip.bottom,rect.top+box.top+box.height);Object.assign(overlay.style,{left:left+'px',top:top+'px',width:Math.max(0,right-left)+'px',height:Math.max(0,bottom-top)+'px',zIndex:focus?'2147483001':'400',borderLeftWidth:rect.left+box.left<clip.left?'0':'1px',borderRightWidth:rect.left+box.left+box.width>clip.right?'0':'1px'});overlay.hidden=right<=left||bottom<=top}else overlay.hidden=true}else overlay.hidden=true;
  renderHud(r,clip,focus);c.onChange?.(s,r);
 }
 function listen(target,type,fn,options={}){target.addEventListener(type,fn,{...options,signal:abort.signal})}
 listen(el,'pointerdown',e=>{
  if(e.button!==0)return;
  pointer={x:e.clientX,y:e.clientY};origin=pointer;corner=null;
  if(c.interaction==='external'){drag={moved:false,id:e.pointerId,x:e.clientX,y:e.clientY};return}
  const point=c.locate(e);if(!point)return;drag={start:point,x:e.clientX,y:e.clientY,id:e.pointerId,previous:selection,previousPoint:pointSelection,allowRange:e.pointerType!=='touch'||touchEnabled,moved:false};
 },{capture:true});
 listen(scope,'pointermove',e=>{
  if(!drag||drag.id!==e.pointerId)return;pointer={x:e.clientX,y:e.clientY};
  if(c.interaction==='external'){if(Math.hypot(e.clientX-drag.x,e.clientY-drag.y)>=4)drag.moved=true;return}
  if(!drag.allowRange){if(Math.hypot(e.clientX-drag.x,e.clientY-drag.y)>=4)drag.moved=true;return}
  if(Math.hypot(e.clientX-drag.x,e.clientY-drag.y)<4&&!drag.moved)return;
  if(!drag.moved){try{el.setPointerCapture(e.pointerId)}catch{}}drag.moved=true;e.preventDefault();e.stopImmediatePropagation();const end=c.locate(e);if(end)paint({start:drag.start,end});
 },{capture:true});
 listen(scope,'pointerup',e=>{
  if(!drag||drag.id!==e.pointerId)return;
  if(drag.moved){blockedClick=true;setTimeout(()=>blockedClick=false,40);if(c.interaction!=='external'&&drag.allowRange){e.preventDefault();e.stopImmediatePropagation()}}
  drag=null;hud.dataset.dragging='false';repaint();
 },{capture:true});
 listen(scope,'pointercancel',()=>{if(!drag)return;const old=drag.previous,oldPoint=drag.previousPoint;drag=null;hud.dataset.dragging='false';blockedClick=true;setTimeout(()=>blockedClick=false,40);if(c.interaction!=='external'){if(old)paint(old);else if(oldPoint)paintPoint(oldPoint,pointResult(c,oldPoint));else clear()}},{capture:true});
 listen(el,'click',e=>{if(blockedClick){e.preventDefault();e.stopImmediatePropagation();return}if(c.interaction==='external')queueMicrotask(()=>clickAction(e));else clickAction(e)},{capture:true});
 listen(el,'keydown',e=>{if(e.key==='Escape'){requestReset();return}if(c.interaction==='external')return;if(!e.shiftKey||!['ArrowLeft','ArrowRight','Home','End'].includes(e.key)||c.kind==='scatter')return;e.preventDefault();e.stopImmediatePropagation();anchor??=cursor;cursor=e.key==='Home'?0:e.key==='End'?c.domain.length-1:Math.max(0,Math.min(c.domain.length-1,cursor+(e.key==='ArrowRight'?1:-1)));paint({start:{index:anchor},end:{index:cursor}})},{capture:true});
 for(const target of [ui,hud])listen(target,'keydown',e=>{if(e.key==='Escape'){e.preventDefault();requestReset();el.focus({preventScroll:true})}});
 listen(scope,'scroll',repaint,{capture:true});listen(scope,'resize',repaint);
 const handle={clear,config:c,selectSeries,selectPoint,getSelection(){return selection?{mode:'range',...selection,seriesId:selectedSeries}:pointSelection?{...pointSelection}:null},exportState(){return {identity:identity(c),selection,pointSelection,computed,selectedSeries}},refreshMarks(){if(c.nativeHit)return focusSeries((selection||pointSelection)?selectedSeries:null,'refresh');for(const path of el.querySelectorAll('path:not([data-qr-hit]):not([data-qr-hit-ready]):not(.qr-journal-hit):not([class*=series-hit])')){const owner=path.closest('[data-qr-series-id]');if(!owner||scope.getComputedStyle(path).fill!=='none')continue;path.dataset.qrHitReady='true';const hit=path.cloneNode(false);hit.removeAttribute('id');hit.removeAttribute('style');hit.setAttribute('class','qr-hit-path');for(const [k,v] of [['stroke','transparent'],['fill','none'],['opacity','0'],['stroke-width','16px'],['pointer-events','stroke'],['filter','none']])hit.style.setProperty(k,v,'important');hit.dataset.qrHit='true';hit.dataset.qrSeriesId=owner.dataset.qrSeriesId;hit.setAttribute('aria-hidden','true');hit.removeAttribute('tabindex');path.after(hit)}focusSeries((selection||pointSelection)?selectedSeries:null,'refresh')},present(s,result){if(result?.kind==='point')paintPoint(s,result);else paint(s,result)},setSeries(id){selectedSeries=id;repaint()},destroy(){abort.abort();ui.remove();overlay.remove();hud.remove();delete el.dataset.quantRange;if(originalTab===null)el.removeAttribute('tabindex');el.style.touchAction='';if(api.entries.get(c.id)===handle)api.entries.delete(c.id)}};
 api.entries.set(c.id,handle);if(restore){selectedSeries=restore.selectedSeries;if(restore.selection)paint(restore.selection,restore.computed);else if(restore.pointSelection)paintPoint(restore.pointSelection,pointResult(c,restore.pointSelection))}handle.refreshMarks();return handle;
};
/* Renderer-native SVG coordinates, including viewBox letterboxing and CSS scaling. */
function svgLocal(el,e){const m=el.getScreenCTM();if(!m)return null;const p=el.createSVGPoint();p.x=e.clientX;p.y=e.clientY;return p.matrixTransform(m.inverse())}
function svgBox(el,left,top,right,bottom){const m=el.getScreenCTM(),r=el.getBoundingClientRect();if(!m||!r.width||!r.height)return null;const a=el.createSVGPoint(),b=el.createSVGPoint();a.x=left;a.y=top;b.x=right;b.y=bottom;const p=a.matrixTransform(m),q=b.matrixTransform(m);return {left:Math.min(p.x,q.x)-r.left,top:Math.min(p.y,q.y)-r.top,width:Math.abs(p.x-q.x),height:Math.abs(p.y-q.y)}}
api.svg=function(c){const el=c.element;return api.register({...c,plotRect:()=>{const a=c.x(0,c.domain[0]),b=c.x(c.domain.length-1,c.domain.at(-1));return c.orientation==='vertical'?svgBox(el,c.plotLeft||0,Math.min(a,b),c.plotRight??el.viewBox.baseVal.width,Math.max(a,b)):svgBox(el,Math.min(a,b),c.plotTop||0,Math.max(a,b),(typeof c.plotBottom==='function'?c.plotBottom():c.plotBottom)??el.viewBox.baseVal.height)},locate:e=>{const p=svgLocal(el,e);if(!p)return null;const px=c.orientation==='vertical'?p.y:p.x;let index=0,best=Infinity;c.domain.forEach((d,i)=>{const dist=Math.abs(c.x(i,d)-px);if(dist<best){best=dist;index=i}});return {index}},project:s=>{const a=c.x(s.start.index,c.domain[s.start.index]),b=c.x(s.end.index,c.domain[s.end.index]);return c.orientation==='vertical'?svgBox(el,c.plotLeft||0,Math.min(a,b),c.plotRight??el.viewBox.baseVal.width,Math.max(a,b)):svgBox(el,Math.min(a,b),c.plotTop||0,Math.max(a,b),(typeof c.plotBottom==='function'?c.plotBottom():c.plotBottom)??el.viewBox.baseVal.height)}})};
api.scatterSvg=function(c){const el=c.element,b=c.bounds;const dx=p=>c.xDomain[0]+(p-b.left)/(b.right-b.left)*(c.xDomain[1]-c.xDomain[0]);const dy=p=>c.yDomain[1]-(p-b.top)/(b.bottom-b.top)*(c.yDomain[1]-c.yDomain[0]);const x=v=>b.left+(v-c.xDomain[0])/(c.xDomain[1]-c.xDomain[0])*(b.right-b.left);const y=v=>b.bottom-(v-c.yDomain[0])/(c.yDomain[1]-c.yDomain[0])*(b.bottom-b.top);return api.register({...c,kind:'scatter',hitPoint:c.hitPoint||((e)=>{let best=null,distance=Infinity;for(const point of c.scatter||[]){const box=svgBox(el,x(point.x),y(point.y),x(point.x),y(point.y));if(!box)continue;const r=el.getBoundingClientRect(),d=Math.hypot(e.clientX-r.left-box.left,e.clientY-r.top-box.top);if(d<distance&&d<=10){distance=d;best={pointId:point.id}}}return best}),plotRect:()=>svgBox(el,b.left,b.top,b.right,b.bottom),locate:e=>{const p=svgLocal(el,e);return p?{x:dx(p.x),y:dy(p.y)}:null},project:s=>svgBox(el,Math.min(x(s.start.x),x(s.end.x)),Math.min(y(s.start.y),y(s.end.y)),Math.max(x(s.start.x),x(s.end.x)),Math.max(y(s.start.y),y(s.end.y)))})};
api.categories=function(c){const el=c.element,getItems=()=>c.items||[...el.querySelectorAll(c.itemSelector)];getItems().forEach((item,i)=>{item.dataset.qrIndex=String(i);item.dataset.qrSeriesId||=c.series?.[0]?.id||''});return api.register({...c,kind:'category',locate:e=>{const items=getItems();let index=0,best=Infinity;items.forEach((item,i)=>{const r=item.getBoundingClientRect(),d=Math.abs((c.orientation==='horizontal'?e.clientX-(r.left+r.right)/2:e.clientY-(r.top+r.bottom)/2));if(d<best){best=d;index=i}});return {index}},project:s=>{const items=getItems(),a=items[Math.min(s.start.index,s.end.index)]?.getBoundingClientRect(),b=items[Math.max(s.start.index,s.end.index)]?.getBoundingClientRect(),r=el.getBoundingClientRect();return a&&b?{left:Math.min(a.left,b.left)-r.left,top:Math.min(a.top,b.top)-r.top,width:Math.max(a.right,b.right)-Math.min(a.left,b.left),height:Math.max(a.bottom,b.bottom)-Math.min(a.top,b.top)}:null}})};
doc.addEventListener('click',e=>{const mark=e.target.closest?.('[data-qr-chart-id][data-qr-series-id]');if(!mark||mark.closest('[data-quant-range]'))return;api.entries.get(mark.dataset.qrChartId)?.selectSeries(mark.dataset.qrSeriesId,{origin:'legend'})});
let unique=0;
function consume(){for(const h of api.entries.values())if(!h.config.element.isConnected)h.destroy();else h.refreshMarks?.();for(const el of doc.querySelectorAll('[data-qr-spec]:not([data-quant-range]):not([data-quant-range-error])')){try{const c={...JSON.parse(decodeURIComponent(el.dataset.qrSpec)),...el._quantRangeAdapter};if(api.entries.has(c.id))c.id+='-instance-'+(++unique);if(c.kind==='scatter')api.scatterSvg({...c,element:el});else if(c.itemSelector)api.categories({...c,element:el});else api.svg({...c,element:el,x:i=>c.xs[i]})}catch(error){el.dataset.quantRangeError=String(error)}}}
new MutationObserver(consume).observe(doc.documentElement,{childList:true,subtree:true});consume();
})(typeof window==='undefined'?globalThis:window);
