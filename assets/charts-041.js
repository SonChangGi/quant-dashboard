/* 0.4.2 direct-range renderer. Inputs are the application's already-validated rows. */
(() => {
'use strict';
if (!globalThis.echarts) return;
const live=new Map(),fmt=n=>Number.isFinite(n)?new Intl.NumberFormat('ko-KR',{maximumFractionDigits:2}).format(n):'—';
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function theme(host){const s=getComputedStyle(host),get=(k,v)=>s.getPropertyValue(k).trim()||v;return {text:get('--qe-text','#edf3f2'),muted:get('--qe-muted','#a6b4b6'),border:get('--qe-border','#364247'),surface:get('--qe-raised','#20282c'),colors:Array.from({length:6},(_,i)=>get('--chart-'+(i+1),['#71adff','#6dd5a4','#f18fa0','#dfb269','#b8a1e9','#65ccd2'][i]))};}
function mount(host, config){
 if(!host||!host.isConnected)return;
 host.dataset.chartEngine='echarts-042';
 const prior=live.get(host);let saved=prior?.chart.getOption();prior?.touchCleanup?.();prior?.chart.dispose();prior?.ro.disconnect();host.replaceChildren();
 host.classList.add('qe-plot041');host.style.minWidth='0';host.style.overflow='visible';host.onpointermove=null;host.onpointerleave=null;host.onclick=null;host.onkeydown=null;
 const plot=document.createElement('div');plot.className='qe-canvas041';plot.style.height=(config.height||320)+'px';plot.style.width='100%';plot.tabIndex=0;plot.setAttribute('role','img');plot.setAttribute('aria-label',config.title);host.append(plot);

 const reset=document.createElement('button');reset.type='button';reset.textContent='전체 기간';reset.dataset.quantResetView='';reset.hidden=true;host.append(reset);
 const range=document.createElement('output');range.className='qe-range041';range.dataset.quantChartReadout='';range.hidden=true;host.append(range);
 const chart=echarts.init(plot,null,{renderer:'svg'}),t=theme(host);
 const resolveColor=v=>typeof v==='string'&&/^var\(--/.test(v)?getComputedStyle(host).getPropertyValue(v.slice(4,-1)).trim()||t.muted:v;
 const resolveTree=v=>Array.isArray(v)?v.map(resolveTree):v&&typeof v==='object'?Object.fromEntries(Object.entries(v).map(([k,x])=>[k,resolveTree(x)])):resolveColor(v);
 let option=resolveTree(config.option(t));option.animation=false;option.backgroundColor='transparent';option.textStyle={fontFamily:'Pretendard, sans-serif',color:t.text};option.tooltip={confine:true,renderMode:'richText',backgroundColor:t.surface,borderColor:t.border,textStyle:{color:t.text,fontSize:12},...option.tooltip};
 if(saved?.dataZoom&&option.dataZoom)option.dataZoom=option.dataZoom.map((z,i)=>({...z,start:saved.dataZoom[i]?.start??0,end:saved.dataZoom[i]?.end??100}));
 if(saved?.legend?.[0]?.selected&&option.legend)option.legend.selected=saved.legend[0].selected;
 chart.setOption(option);
 const zoomState=()=>{reset.hidden=!(chart.getOption().dataZoom||[]).some(z=>z.start>0||z.end<100);};chart.on('datazoom',zoomState);zoomState();reset.onclick=()=>{chart.dispatchAction({type:'dataZoom',start:0,end:100});};
 let selected=config.selectedIndex??(config.dates?.length-1||0),anchor=null;
 const select=i=>{selected=Math.max(0,Math.min((config.dates?.length||1)-1,i));config.onSelect?.(selected);if(!chart.isDisposed())chart.dispatchAction({type:'showTip',seriesIndex:0,dataIndex:selected});};
 plot.addEventListener('keydown',e=>{const n=config.dates?.length;if(!n)return;const move={ArrowLeft:selected-1,ArrowUp:selected-1,ArrowRight:selected+1,ArrowDown:selected+1,Home:0,End:n-1};if(e.key==='Escape'){clearRange();e.preventDefault();e.stopImmediatePropagation();chart.dispatchAction({type:'hideTip'});return;}if(!(e.key in move))return;e.preventDefault();e.stopImmediatePropagation();if(e.shiftKey&&anchor===null)anchor=selected;select(move[e.key]);if(e.shiftKey&&config.rangeSeries?.length)showRange(anchor,selected);},true);
 chart.on('click',p=>{if(Number.isInteger(p.dataIndex)){config.onSelect?.(p.data?.index??p.dataIndex);selected=p.dataIndex;}});
 chart.on('updateAxisPointer',e=>{const i=e.axesInfo?.[0]?.value;if(Number.isInteger(i)){selected=i;config.onSelect?.(i);}});
 let selection=null, selectedRows=null;
 const shade=document.createElement('div');shade.className='qe-selection042';plot.append(shade);
 const source=document.createElement('details');source.className='qe-options041';source.innerHTML='<summary>데이터 표</summary>';host.append(source);
 function renderSource(){if(!source.open)return;let table=source.querySelector('table');if(!table){table=document.createElement('table');table.innerHTML='<thead><tr>'+config.columns.map(c=>'<th scope="col">'+esc(c)+'</th>').join('')+'</tr></thead><tbody></tbody>';source.append(table);}table.tBodies[0].innerHTML=(config.rows||[]).map((row,i)=>selectedRows&&!selectedRows.has(i)?'':'<tr>'+row.map(v=>'<td>'+esc(v==null?'—':typeof v==='number'?fmt(v):v)+'</td>').join('')+'</tr>').join('');}
 source.addEventListener('toggle',renderSource);
 function clearRange(){if(selection)chart.setOption({tooltip:{showContent:true}});selection=null;selectedRows=null;anchor=null;range.hidden=true;shade.replaceChildren();renderSource();}
 function drawRange(){shade.replaceChildren();if(!selection||chart.isDisposed())return;const rects=chart.getModel().getComponent('grid',0).coordinateSystem.getRect();if(selection.kind==='line'){for(let i=0;i<chart.getOption().grid.length;i++){const r=chart.getModel().getComponent('grid',i).coordinateSystem.getRect();const left=Math.max(r.x,chart.convertToPixel({xAxisIndex:i},selection.lo)),right=Math.min(r.x+r.width,chart.convertToPixel({xAxisIndex:i},selection.hi));if(right>=left)box(left,r.y,Math.max(1,right-left),r.height);}}else{const p=chart.convertToPixel({gridIndex:0},[selection.x0,selection.y1]),q=chart.convertToPixel({gridIndex:0},[selection.x1,selection.y0]);box(p[0],p[1],q[0]-p[0],q[1]-p[1]);}}
 function box(x,y,w,h){const e=document.createElement('div');Object.assign(e.style,{left:x+'px',top:y+'px',width:w+'px',height:h+'px'});shade.append(e);}
 function showRange(a,b){if(!selection){chart.setOption({tooltip:{showContent:false}});chart.dispatchAction({type:'hideTip'});}const lo=Math.max(0,Math.min(a,b)),hi=Math.min(config.dates.length-1,Math.max(a,b));selection={kind:'line',lo,hi};selectedRows=new Set(Array.from({length:hi-lo+1},(_,i)=>lo+i));range.hidden=false;const visible=chart.getOption().legend?.[0]?.selected||{};const parts=(config.rangeSeries||[]).filter(s=>visible[s.name]!==false).map(s=>{const first=s.data[lo],last=s.data[hi],valid=Number.isFinite(first)&&Number.isFinite(last),delta=valid?last-first:null,relative=valid&&first>0?(last/first-1)*100:null;const change=s.measure==='relative'?(relative===null?'Δ '+fmt(delta)+(s.pointUnit||'')+' · 변화율 —':fmt(relative)+'%'):fmt(delta)+(s.unit||'');return '<div>'+esc(s.rangeLabel||s.name)+' <b>'+fmt(first)+(s.pointUnit||'')+' → '+fmt(last)+(s.pointUnit||'')+'</b> · '+esc(change)+'</div>';});range.innerHTML='<strong>'+esc(config.dates[lo]+'–'+config.dates[hi])+'</strong>'+parts.join('');drawRange();renderSource();}
 function showArea(a,b){const p=chart.convertFromPixel({gridIndex:0},a),q=chart.convertFromPixel({gridIndex:0},b);selection={kind:'area',x0:Math.min(p[0],q[0]),x1:Math.max(p[0],q[0]),y0:Math.min(p[1],q[1]),y1:Math.max(p[1],q[1])};const rows=(config.points||[]).filter((r,i)=>{const hit=r.x>=selection.x0&&r.x<=selection.x1&&r.y>=selection.y0&&r.y<=selection.y1;return hit;});selectedRows=new Set((config.points||[]).flatMap((r,i)=>rows.includes(r)?[i]:[]));range.hidden=false;range.textContent=rows.length+'개 선택 · '+config.xLabel+' '+fmt(selection.x0)+'–'+fmt(selection.x1)+' · '+config.yLabel+' '+fmt(selection.y0)+'–'+fmt(selection.y1);drawRange();renderSource();}
 chart.on('datazoom',drawRange);chart.on('legendselectchanged',()=>{if(selection?.kind==='line')showRange(selection.lo,selection.hi);});
 let drag=null,suppressClick=false;
 const local=e=>{const r=plot.getBoundingClientRect();return[e.clientX-r.left,e.clientY-r.top];};
 const inside=p=>chart.getOption().grid.some((_,i)=>chart.containPixel({gridIndex:i},p));
 const index=p=>Math.max(0,Math.min(config.dates.length-1,Math.round(chart.convertFromPixel({xAxisIndex:0},p[0]))));
 const clamp=p=>{const r=chart.getModel().getComponent('grid',0).coordinateSystem.getRect();return[Math.max(r.x,Math.min(r.x+r.width,p[0])),Math.max(r.y,Math.min(r.y+r.height,p[1]))];};
 const seriesMode=Boolean(config.rangeSeries?.length);
 const touchCleanup=globalThis.QuantTouchChart?.bindTouchChart(plot,{
   hit:(p,clamped)=>clamped||inside(p)?(seriesMode?index(p):clamp(p)):null,
   inspect:(value)=>{if(seriesMode){select(value);return;}const [x,y]=value;const i=nearestPoint(x,y);if(i>=0){config.onSelect?.(config.points[i].index??i);chart.dispatchAction({type:'showTip',seriesIndex:0,dataIndex:i});}},
   compare:(a,b)=>seriesMode?showRange(a,b):showArea(a,b),
   clear:clearRange,rangeReadout:()=>range,
   navigate:(a,b)=>globalThis.QuantTouchChart.navigateECharts(chart,a,b,.2)
 });
 function nearestPoint(x,y){
   let best=24,index=-1;
   for(let i=0;i<config.points.length;i++){const point=config.points[i];const p=chart.convertToPixel({gridIndex:0},[point.x,point.y]);const distance=Math.hypot(x-p[0],y-p[1]);if(distance<best){best=distance;index=i;}}
   return index;
 }
 plot.style.touchAction='pan-y';
 plot.addEventListener('pointerdown',e=>{if(e.pointerType==='touch'||e.button!==0)return;suppressClick=false;const p=local(e);if(!inside(p)||e.altKey)return;anchor=null;drag={id:e.pointerId,start:p,active:false};},true);
 plot.addEventListener('pointermove',e=>{if(!drag||drag.id!==e.pointerId)return;const p=local(e),dx=p[0]-drag.start[0],dy=p[1]-drag.start[1];if(!drag.active){if(Math.hypot(dx,dy)<6)return;drag.active=true;chart.dispatchAction({type:'hideTip'});try{plot.setPointerCapture?.(e.pointerId);}catch{}}e.preventDefault();e.stopImmediatePropagation();if(seriesMode)showRange(index(drag.start),index(p));else showArea(clamp(drag.start),clamp(p));},true);
 const release=e=>{if(drag?.id===e.pointerId){suppressClick=drag.active;drag=null;}};plot.addEventListener('pointerup',release,true);plot.addEventListener('pointercancel',release,true);
 plot.addEventListener('click',e=>{if(suppressClick){suppressClick=false;e.preventDefault();e.stopImmediatePropagation();return;}if(inside(local(e)))clearRange();},true);
 plot.addEventListener('dblclick',()=>reset.click());
 plot.addEventListener('keydown',e=>{if(e.key==='0'){reset.click();e.preventDefault();}},true);
 const ro=new ResizeObserver(()=>{chart.resize();drawRange();});ro.observe(plot);live.set(host,{chart,ro,config,touchCleanup});
 return chart;
}
function axis(t,unit=''){return {type:'value',scale:true,name:unit,nameLocation:'end',nameGap:15,nameTextStyle:{color:t.muted},axisLabel:{color:t.muted,fontSize:11,formatter:fmt},splitNumber:4,splitLine:{lineStyle:{color:t.border,type:'dashed'}},axisLine:{show:false}};}
function lines(host,c){const dates=c.dates,panels=c.panels||[{title:c.title,unit:c.unit,series:c.series}],plotLeft=panels.some(p=>p.axis?.axisLabel?.formatter)?86:panels.length>1?56:48;return mount(host,{...c,dates,height:c.height||Math.max(245,panels.length*215+30),columns:['날짜',...panels.flatMap(p=>p.series.map(s=>(panels.length>1?p.title+' · ':'')+s.name+(p.unit?' ('+p.unit+')':'')))],rows:dates.map((d,i)=>[d,...panels.flatMap(p=>p.series.map(s=>s.data[i]))]),rangeSeries:panels.flatMap(p=>p.series.map(s=>({...s,pointUnit:p.unit||c.unit||'',rangeLabel:panels.length>1?s.name+' '+p.title:s.name}))).filter(s=>s.range!==false),option:t=>({legend:{show:c.legend!==false,type:'scroll',top:0,textStyle:{color:t.muted},pageIconColor:t.text},grid:panels.map((p,i)=>({left:plotLeft,right:20,top:55+i*215,bottom:undefined,height:155,containLabel:false})),title:panels.map((p,i)=>({text:p.title+(p.unit?' · '+p.unit:''),left:12,top:30+i*215,textStyle:{fontSize:12,color:t.muted,fontWeight:500}})),xAxis:panels.map((p,i)=>({type:'category',gridIndex:i,data:dates,boundaryGap:false,axisTick:{show:false},axisLabel:{show:i===panels.length-1,color:t.muted,fontSize:11,hideOverlap:true,showMinLabel:true,showMaxLabel:true,alignMinLabel:'left',alignMaxLabel:'right',formatter:v=>v.slice(2,10)},axisLine:{lineStyle:{color:t.border}}})),yAxis:panels.map((p,i)=>({...axis(t),gridIndex:i,...p.axis})),tooltip:{trigger:'axis',axisPointer:{type:'line'},valueFormatter:fmt},axisPointer:{link:[{xAxisIndex:'all'}]},dataZoom:[{type:'inside',xAxisIndex:panels.map((_,i)=>i),filterMode:'none',preventDefaultMouseMove:false,moveOnMouseMove:'alt',moveOnMouseWheel:false}],brush:{xAxisIndex:0,brushMode:'single',toolbox:[]},toolbox:{show:false},series:panels.flatMap((p,i)=>p.series.map((s,j)=>({name:s.name,type:'line',xAxisIndex:i,yAxisIndex:i,data:s.data,showSymbol:false,connectNulls:false,smooth:false,lineStyle:{width:2.4,type:s.dashed?'dashed':'solid',color:s.color||t.colors[j%6]},itemStyle:{color:s.color||t.colors[j%6]},emphasis:{focus:'series'},...s.extra})))})});}
function scatter(host,c){return mount(host,{...c,columns:c.columns||['대상',c.xLabel,c.yLabel],rows:c.points.map(p=>[p.name,p.x,p.y]),option:t=>({dataZoom:[{type:'inside',xAxisIndex:0,filterMode:'none',moveOnMouseMove:'alt',moveOnMouseWheel:false,preventDefaultMouseMove:false},{type:'inside',yAxisIndex:0,filterMode:'none',moveOnMouseMove:'alt',moveOnMouseWheel:false,preventDefaultMouseMove:false}],grid:{left:12,right:24,top:42,bottom:50,containLabel:true},xAxis:{...axis(t,c.xLabel),nameLocation:'middle',nameGap:28,...c.xAxis},yAxis:{...axis(t,c.yLabel),...c.yAxis},tooltip:{trigger:'item',formatter:p=>p.data.name+'\n'+c.xLabel+' '+fmt(p.value[0])+'\n'+c.yLabel+' '+fmt(p.value[1])},series:[{type:'scatter',data:c.points.map((p,i)=>({name:p.name,label:{show:p.showLabel},value:[p.x,p.y],index:p.index??i,symbol:p.symbol||'circle',itemStyle:{color:p.hollow?t.surface:p.color||t.colors[0],borderColor:p.color||t.colors[0],borderWidth:p.current?2:1},symbolSize:p.current?11:6})),emphasis:{focus:'self'},...c.series},...(c.extra?.(t)||[])]})});}
function categories(host,rows){
 const plot=host.querySelector('.factor-holdings'),items=[...plot.children],output=document.createElement('output');output.className='qe-range041';output.hidden=true;output.dataset.quantChartReadout='';host.append(output);plot.tabIndex=0;plot.style.touchAction='pan-y';let gesture=null,blocked=false,cursor=0,anchor=0;
 const clear=()=>{output.hidden=true;items.forEach(e=>e.removeAttribute('data-range-selected'));};
 const show=(a,b)=>{const lo=Math.min(a,b),hi=Math.max(a,b),chosen=rows.slice(lo,hi+1),valid=chosen.filter(r=>Number.isFinite(r.weight));output.hidden=false;output.textContent=chosen.length+'개 · '+chosen.map(r=>r.symbol).join(', ')+' · 모델 비중 합계 '+(valid.length===chosen.length?fmt(valid.reduce((n,r)=>n+r.weight,0)*100)+'%':'—');items.forEach((e,i)=>e.dataset.rangeSelected=String(i>=lo&&i<=hi));};
 const at=y=>{let i=items.findIndex(e=>y<e.getBoundingClientRect().bottom);return i<0?items.length-1:i;};
 globalThis.QuantTouchChart?.bindTouchChart(plot,{
   axis:'y',hit:([,y])=>at(y+plot.getBoundingClientRect().top),
   inspect:i=>show(i,i),compare:show,clear,rangeReadout:()=>output
 });

 plot.addEventListener('pointerdown',e=>{if(e.button===0&&e.pointerType!=='touch')gesture={id:e.pointerId,x:e.clientX,y:e.clientY,index:at(e.clientY),touch:e.pointerType==='touch',active:false};});
 plot.addEventListener('pointermove',e=>{if(!gesture||gesture.id!==e.pointerId)return;const dx=e.clientX-gesture.x,dy=e.clientY-gesture.y;if(!gesture.active){if(Math.hypot(dx,dy)<6)return;if(gesture.touch&&Math.abs(dy)>Math.abs(dx)){gesture=null;return;}gesture.active=true;try{plot.setPointerCapture(e.pointerId)}catch{}}e.preventDefault();show(gesture.index,at(e.clientY));});
 plot.addEventListener('pointerup',()=>{blocked=!!gesture?.active;gesture=null;});plot.addEventListener('pointercancel',()=>{gesture=null;});plot.addEventListener('click',()=>{if(blocked){blocked=false;return;}clear();});
 plot.addEventListener('keydown',e=>{if(e.key==='Escape'){clear();e.preventDefault();return;}if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Home','End'].includes(e.key))return;e.preventDefault();if(!e.shiftKey)anchor=cursor;cursor=e.key==='Home'?0:e.key==='End'?items.length-1:Math.max(0,Math.min(items.length-1,cursor+(['ArrowLeft','ArrowUp'].includes(e.key)?-1:1)));show(e.shiftKey?anchor:cursor,cursor);});
}
new MutationObserver(()=>{for(const [el,v] of live)if(!el.isConnected){v.touchCleanup?.();v.chart.dispose();v.ro.disconnect();live.delete(el);}}).observe(document.body,{childList:true,subtree:true});
new MutationObserver(()=>{for(const [host,v] of [...live])mount(host,v.config);}).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});
globalThis.HubCharts041={lines,scatter,categories};
})();
