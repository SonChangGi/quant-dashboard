import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {buildOption,mountChart,formatChartNumber,CHART_KINDS} from '../engine/charts.js';

const fan={kind:'fan',title:'예측 구간',unit:'점',x:['2026-01-01','2026-02-01','2026-03-01','2026-04-01'],observed:[-2,1,null,null],center:[null,1,2,3],forecastStart:1,intervalKind:'prediction',method:'사전 계산 모의 분위수',intervals:[{level:.5,low:[null,0,1,2],high:[null,2,3,4]},{level:.9,low:[null,-1,-2,0],high:[null,3,6,7]}]};
const bullet={kind:'bullet',title:'실제와 목표',rows:[{name:'A',value:72,target:80,ranges:[50,75,100]},{name:'B',value:45,target:60,ranges:[40,65,100]}]};
const treemap={kind:'treemap',title:'계층',nodes:[{name:'반도체',children:[{name:'설계',value:30},{name:'장비',value:20}]},{name:'금융',value:40},{name:'미배분',value:0}]};
const line={kind:'line',title:'비교',x:['2026-01-01','2026-01-02','2026-01-03'],series:[{name:'A',data:[100,null,120]},{name:'SPY',data:[100,105,110]}],brush:true};
test('line gaps survive as null; no interpolation, immutable inputs, declared units',()=>{
  const before=JSON.stringify(line),option=buildOption({...line,unit:'%'});
  assert.equal(option.series[0].data[1],null);
  assert.equal(option.series[0].connectNulls,false);
  assert.equal(option.yAxis.name,'%');assert.equal(option.tooltip.valueFormatter(null),'미제공');
  assert.equal(option.grid.top,60);assert.equal(option.legend.top,0);
  assert.equal(JSON.stringify(line),before);assert.notEqual(option.series[0].data,line.series[0].data);
  assert.throws(()=>buildOption({...line,series:[{name:'A',data:[1,2]}]}),/length must match/);
  assert.throws(()=>buildOption({...line,series:[{name:'A',data:[1,NaN,3]}]}),/finite/);
});
test('heatmap keeps symmetric color scale and omits missing cells instead of inventing zeros',()=>{
  const o=buildOption({kind:'heatmap',x:['A','B'],y:['A','B'],values:[[0,0,.8],[1,0,-.2],[0,1,null],[1,1,.4]]});
  assert.equal(o.visualMap.min,-.8);assert.equal(o.visualMap.max,.8);assert.equal(o.series[0].data.length,3);
  assert.throws(()=>buildOption({kind:'heatmap',x:['A'],y:['A'],values:[[1,0,.2]]}),/coordinates/);
});
test('area always includes a zero baseline and brush never exposes a second unthemed toolbox',()=>{
  const positive=buildOption({kind:'area',x:['a','b'],series:[{name:'A',data:[20,40]}],brush:true});
  assert.equal(positive.yAxis.min,0);assert.equal(positive.yAxis.max,40);assert.equal(positive.yAxis.scale,false);
  assert.equal(positive.toolbox.show,false);
  const negative=buildOption({kind:'area',x:['a','b'],series:[{name:'A',data:[-40,-20]}]});
  assert.equal(negative.yAxis.min,-40);assert.equal(negative.yAxis.max,0);
  const mixed=buildOption({kind:'area',x:['a','b'],series:[{name:'A',data:[-20,40]}]});
  assert.equal(mixed.yAxis.min,-20);assert.equal(mixed.yAxis.max,40);
  const missing=buildOption({kind:'area',x:['a','b'],series:[{name:'A',data:[null,null]}]});
  assert.equal(missing.yAxis.min,0);assert.equal(missing.yAxis.max,1);
});
test('waterfall handles negative opening balances and crossing zero, totals reset running balance',()=>{
  const o=buildOption({kind:'waterfall',initial:-20,rows:[{name:'하락',value:-5},{name:'회복',value:40},{name:'합계',type:'total',value:15},{name:'비용',value:-3}]});
  assert.deepEqual(o.series[0].data,[[0,-20,-25,-5],[1,-25,15,40],[2,0,15,15],[3,15,12,-3]]);
  const s=o.series[0],data=s.data[1];
  const shape=s.renderItem({dataIndex:1},{value:i=>data[i],coord:([x,y])=>[x*100,100-y],size:()=>[100,0]}).shape;
  assert.equal(shape.y,85);assert.equal(shape.height,40);assert.ok(shape.width>0);
});
test('small multiples use one shared y extent, even with disjoint magnitudes and missing values',()=>{
  const o=buildOption({kind:'small-multiples',x:['a','b'],series:[{name:'small',data:[1,null]},{name:'large',data:[100,200]}]});
  assert.equal(o.yAxis[0].min,o.yAxis[1].min);assert.equal(o.yAxis[0].max,o.yAxis[1].max);
  assert.ok(o.yAxis[0].max>=200);assert.equal(o.series[0].data[1],null);
});
test('histogram uses explicit bin intervals and counts, rejects overlapping bins',()=>{
  const spec={kind:'histogram',bins:[{start:-2,end:0,count:3},{start:0,end:2,count:7}]};
  const o=buildOption(spec);assert.deepEqual(o.series[0].data,[[-2,0,3],[0,2,7]]);
  assert.equal(o.xAxis.min,-2);assert.equal(o.xAxis.max,2);
  assert.throws(()=>buildOption({...spec,bins:[spec.bins[0],{start:-1,end:1,count:4}]}),/non-overlapping/);
  assert.throws(()=>buildOption({kind:'histogram',bins:[{start:1,end:2,count:-1}]}),/nonnegative/);
  assert.throws(()=>buildOption({kind:'histogram',bins:[{start:0,end:1,count:3},{start:1,end:3,count:4}]}),/equal-width/);
});
test('calendar validates exact dates and range, never shifts date-only values through local timezone',()=>{
  const o=buildOption({kind:'calendar',range:'2024',values:[['2024-02-29',7],['2024-03-01',null]]});
  assert.deepEqual(o.series[0].data,[['2024-02-29',7]]);
  assert.throws(()=>buildOption({kind:'calendar',values:[['2025-02-29',7]]}),/valid calendar/);
  assert.throws(()=>buildOption({kind:'calendar',range:'2024',values:[['2025-01-01',7]]}),/outside range/);
});
test('range and boxplot reject impossible ordering rather than silently changing evidence',()=>{
  assert.throws(()=>buildOption({kind:'range',rows:[{name:'A',low:5,high:1}]}),/low/);
  assert.throws(()=>buildOption({kind:'range',rows:[{name:'A',low:1,high:5,value:8}]}),/outside/);
  assert.throws(()=>buildOption({kind:'boxplot',rows:[{name:'A',values:[1,4,3,5,6]}]}),/ordered/);
});
test('every declared chart species produces a renderable series and accessible description',()=>{
  const fixtures={fan,bullet,treemap,line,area:{...line,kind:'area'},bar:{rows:[{name:'A',value:2}]},diverging:{rows:[{name:'A',value:-2}]},slope:{rows:[{name:'A',start:1,end:2}]},dumbbell:{rows:[{name:'A',start:2,end:1}]},scatter:{points:[{name:'A',x:1,y:2}]},heatmap:{x:['A'],y:['A'],values:[[0,0,1]]},boxplot:{rows:[{name:'A',values:[1,2,3,4,5]}]},histogram:{bins:[{start:1,end:2,count:3}]},waterfall:{rows:[{name:'A',value:-2}]},range:{rows:[{name:'A',low:-2,high:3,value:1}]},'small-multiples':{...line,kind:'small-multiples'},calendar:{values:[['2026-01-01',3]]}};
  for(const kind of CHART_KINDS){const o=buildOption({...fixtures[kind],kind});assert.ok(o.series.length,kind);assert.ok(o.aria.label.description,kind);}
});
test('fan preserves signed nested intervals, explicit boundary, metadata and null gaps',()=>{
  const before=JSON.stringify(fan),o=buildOption(fan);
  assert.equal(o.series[0].name,'90% 예측구간');assert.equal(o.series[0].type,'custom');
  assert.deepEqual(o.series[0].data[0],[1,-1,3,2,-2,6]);
  assert.equal(o.series.at(-1).markLine.data[0].xAxis,'2026-02-01');assert.equal(o.series.at(-1).lineStyle.type,'dashed');
  assert.match(o.aria.label.description,/사전 계산 모의 분위수/);assert.equal(JSON.stringify(fan),before);
  assert.throws(()=>buildOption({...fan,method:''}),/method/);
  assert.throws(()=>buildOption({...fan,x:['2026-01-01','2026-03-01','2026-02-01','2026-04-01']}),/increasing/);
  assert.throws(()=>buildOption({...fan,observed:[-2,1,2,null]}),/boundary/);
  assert.throws(()=>buildOption({...fan,center:[1,1,2,3]}),/precede/);
  const crossing=structuredClone(fan);crossing.intervals[1].low[2]=1.5;
  assert.throws(()=>buildOption(crossing),/contain/);
  const asymmetric=structuredClone(fan);asymmetric.intervals[0].low[2]=null;
  assert.throws(()=>buildOption(asymmetric),/missing together/);
  const gap=structuredClone(fan);gap.center[2]=null;gap.intervals.forEach(b=>{b.low[2]=null;b.high[2]=null;});
  const g=buildOption(gap);assert.equal(g.series[0].data.length,0);assert.equal(g.series.at(-1).connectNulls,false);
});
test('fan bands use direct polygons across zero rather than stacking signed magnitudes',()=>{
  const o=buildOption(fan),s=o.series[0],d=s.data[0];
  const graphic=s.renderItem({dataIndex:0},{value:i=>d[i],coord:([x,y])=>[x*100,100-y]});
  assert.deepEqual(graphic.shape.points,[[100,101],[100,97],[200,94],[200,102]]);
  assert.match(o.tooltip.formatter([{axisValue:'2026-03-01'}]),/90% 예측구간 -2점 – 6점/);
});
test('bullet has a common zero axis, separate target mark and explicit bounded ranges',()=>{
  const o=buildOption(bullet);assert.equal(o.xAxis.min,0);assert.equal(o.xAxis.max,100);
  const s=o.series[0],d=s.data[0];const graphic=s.renderItem({dataIndex:0},{value:i=>d[i],coord:([x,y])=>[x*2,50+y*60],size:()=>[0,60]});
  assert.equal(graphic.children.length,5);assert.equal(graphic.children[3].shape.width,144);assert.equal(graphic.children[4].shape.x1,160);
  assert.throws(()=>buildOption({...bullet,rows:[{name:'A',value:72,target:110,ranges:[50,75,100]}]}),/range/);
  assert.throws(()=>buildOption({...bullet,rows:[{name:'A',value:72,target:80,ranges:[50,40,100]}]}),/increasing/);
});
test('treemap sums children without mutation and rejects ambiguous hierarchy',()=>{
  const before=JSON.stringify(treemap),o=buildOption(treemap);assert.equal(o.series[0].data[0].value,50);assert.equal(JSON.stringify(treemap),before);
  assert.equal(o.series[0].nodeClick,false);assert.match(o.tooltip.formatter({name:'금융',value:40}),/44.44%/);
  assert.throws(()=>buildOption({kind:'treemap',nodes:[{name:'A',value:-1}]}),/nonnegative/);
  assert.throws(()=>buildOption({kind:'treemap',nodes:[{name:'A',value:0}]}),/positive total/);
  assert.throws(()=>buildOption({kind:'treemap',nodes:[{name:'A',value:2,children:[{name:'B',value:1}]}]}),/sum/);
  const cyclic={name:'A'};cyclic.children=[cyclic];assert.throws(()=>buildOption({kind:'treemap',nodes:[cyclic]}),/acyclic/);
});
test('tiny observations are not rounded into zero; unknown and infinite values remain unavailable',()=>{
  assert.equal(formatChartNumber(.00042),'0.00042');assert.equal(formatChartNumber(1.234),'1.23');assert.equal(formatChartNumber(null),'미제공');assert.equal(formatChartNumber(Infinity),'미제공');
});

function mockMount(spec=line,events={}) {
  const attrs=new Map(),listeners=new Map(),handlers=new Map();let option,disposed=false;
  const element={getAttribute:k=>attrs.get(k)??null,setAttribute:(k,v)=>attrs.set(k,v),removeAttribute:k=>attrs.delete(k),addEventListener:(k,v)=>listeners.set(k,v),removeEventListener:k=>listeners.delete(k)};
  const actions=[];
  const chart={setOption:o=>{option=o;element.setAttribute('role','img');},getOption:()=>option,on:(k,v)=>handlers.set(k,v),dispatchAction:a=>actions.push(a),resize(){element.setAttribute('role','img');},dispose(){disposed=true;}};
  const selections=[],ranges=[];
  const api=mountChart(element,spec,{echarts:{init:()=>chart},onSelect:v=>selections.push(v),onRange:v=>ranges.push(v),...events});
  return {api,element,attrs,listeners,handlers,actions,selections,ranges,get option(){return option;},get disposed(){return disposed;}};
}
test('theme switch preserves exact selection, range, hidden legend and zoom',()=>{
  const m=mockMount();m.api.select(2);m.api.setRange(0,2);m.api.setLegend('SPY',false);m.api.setZoom(25,80);
  const before=m.api.getState();m.api.setTheme({text:'#111',muted:'#555',surface:'#fff'});
  assert.deepEqual(m.api.getState(),before);assert.equal(m.option.legend.selected.SPY,false);assert.equal(m.option.dataZoom[0].start,25);assert.equal(m.option.textStyle.color,'#111');
  assert.deepEqual(m.selections.at(-1),{index:2,x:'2026-01-03',series:[{name:'A',value:120}]});
  m.api.destroy();m.api.destroy();assert.ok(m.disposed);assert.equal(m.listeners.size,0);assert.equal(m.attrs.has('tabindex'),false);
});
test('keyboard cursor reports gaps; Shift range and Escape are separate from zoom',()=>{
  const m=mockMount();m.api.setZoom(20,90);
  const key=(key,shiftKey=false)=>m.listeners.get('keydown')({key,shiftKey,target:m.element,preventDefault(){}});
  key('ArrowRight');assert.equal(m.api.getState().cursor,1);assert.equal(m.selections.at(-1).series[0].value,null);
  key('ArrowRight',true);assert.equal(m.api.getState().range.startIndex,1);assert.equal(m.api.getState().range.endIndex,2);
  key('Escape');assert.equal(m.api.getState().range,null);assert.equal(m.api.getState().cursor,null);assert.deepEqual(m.api.getState().zoom,{start:20,end:90});
  m.api.setMode('zoom');assert.equal(m.option.dataZoom[0].zoomOnMouseWheel,true);
  m.api.setMode('select');assert.equal(m.option.dataZoom[0].zoomOnMouseWheel,true);
  m.api.resetView();assert.deepEqual(m.api.getState().zoom,{start:0,end:100});m.api.destroy();
});
test('invalid update leaves active chart intact; replacing x resets out-of-date selections',()=>{
  const m=mockMount();m.api.select(2);
  assert.throws(()=>m.api.update({...line,series:[{name:'A',data:[1]}]}));assert.equal(m.api.getState().cursor,2);
  m.api.update({...line,x:['a'],series:[{name:'A',data:[8]}]});assert.equal(m.api.getState().cursor,null);assert.equal(m.api.getState().range,null);m.api.destroy();
});
test('resetView restores every hidden series and keeps the keyboard host a group after ECharts ARIA writes',()=>{
  const m=mockMount({...line,series:line.series.map(s=>({...s,visible:false}))});
  assert.deepEqual(m.api.getState().hidden,['A','SPY']);
  assert.equal(m.attrs.get('role'),'group');
  m.api.select(2);m.api.setRange(0,2);m.api.setZoom(30,70);m.api.setMode('select');
  m.api.resetView();
  assert.deepEqual(m.api.getState(),{selectedIndex:null,cursor:null,range:null,legend:{A:true,SPY:true},hidden:[],zoom:{start:0,end:100},mode:'inspect'});
  assert.deepEqual(m.option.legend.selected,{A:true,SPY:true});
  assert.equal(m.attrs.get('role'),'group');
  assert.equal(m.option.aria.enabled,false);
  m.api.resize();assert.equal(m.attrs.get('role'),'group');
  m.api.setTheme({text:'#111'});assert.equal(m.attrs.get('role'),'group');m.api.destroy();
});
test('ResizeObserver redraw restores the interactive group and disconnects on destroy',()=>{
  const previous=globalThis.ResizeObserver;let resize,disconnected=false;
  globalThis.ResizeObserver=class{constructor(callback){resize=callback;}observe(){}disconnect(){disconnected=true;}};
  try{const m=mockMount();resize();assert.equal(m.attrs.get('role'),'group');m.api.destroy();assert.ok(disconnected);resize();assert.equal(m.attrs.has('role'),false);}finally{globalThis.ResizeObserver=previous;}
});
test('an initial renderer failure releases observer, listeners, host attributes and chart allocation',()=>{
  const previous=globalThis.ResizeObserver;let disconnected=false,disposeCount=0,resize;
  const attrs=new Map([['role','region'],['tabindex','-1'],['aria-label','Original host']]);
  const listeners=new Map(),events=new Map(),zrEvents=new Map();
  const element={getAttribute:k=>attrs.get(k)??null,setAttribute:(k,v)=>attrs.set(k,v),removeAttribute:k=>attrs.delete(k),addEventListener:(k,v)=>listeners.set(k,v),removeEventListener:k=>listeners.delete(k)};
  const originalError=new Error('initial SVG failure');
  const chart={getZr:()=>({on:(k,v)=>zrEvents.set(k,v),off:k=>zrEvents.delete(k)}),on:(k,v)=>events.set(k,v),off:k=>events.delete(k),setOption(){element.setAttribute('role','img');throw originalError;},resize(){throw new Error('disposed observer must not resize');},dispose(){disposeCount++;}};
  globalThis.ResizeObserver=class{constructor(callback){resize=callback;}observe(){}disconnect(){disconnected=true;}};
  try{
    assert.throws(()=>mountChart(element,line,{echarts:{init:()=>chart}}),error=>error===originalError);
    assert.ok(disconnected);assert.equal(disposeCount,1);assert.equal(listeners.size,0);assert.equal(events.size,0);assert.equal(zrEvents.size,0);
    assert.deepEqual(Object.fromEntries(attrs),{role:'region',tabindex:'-1','aria-label':'Original host'});
    resize();assert.equal(disposeCount,1);
  }finally{globalThis.ResizeObserver=previous;}
});
test('bundled ECharts renders all declared species to valid SVG, including custom geometry',()=>{
  const context={console,setTimeout,clearTimeout};
  vm.runInNewContext(fs.readFileSync(new URL('../vendor/echarts.min.js',import.meta.url),'utf8'),context);
  const fixtures=[fan,bullet,treemap,line,{...line,kind:'area'},{kind:'bar',rows:[{name:'A',value:2},{name:'B',value:null}]},{kind:'diverging',rows:[{name:'A',value:-2}]},{kind:'slope',rows:[{name:'A',start:1,end:2}]},{kind:'dumbbell',rows:[{name:'A',start:2,end:1}]},{kind:'scatter',points:[{name:'A',x:1,y:2}]},{kind:'heatmap',x:['A','B'],y:['A'],values:[[0,0,-1],[1,0,null]]},{kind:'boxplot',rows:[{name:'A',values:[1,2,3,4,5]}]},{kind:'histogram',bins:[{start:-2,end:0,count:3},{start:0,end:2,count:0}]},{kind:'waterfall',initial:-5,rows:[{name:'A',value:-2},{name:'B',value:9}]},{kind:'range',rows:[{name:'A',low:-2,high:3,value:1}]},{...line,kind:'small-multiples'},{kind:'calendar',range:'2026',values:[['2026-01-01',3],['2026-01-02',null]]}];
  for(const spec of fixtures){
    const chart=context.echarts.init(null,null,{renderer:'svg',ssr:true,width:800,height:420});
    try{chart.setOption(buildOption(spec));const svg=chart.renderToSVGString();assert.match(svg,/<svg/);assert.doesNotMatch(svg,/NaN|Infinity/,spec.kind);assert.ok(svg.length>500,spec.kind);}finally{chart.dispose();}
  }
});


test('default gestures need no mode switch, keyboard zoom is reversible without changing series',()=>{
 const m=mockMount();assert.equal(m.option.dataZoom.length,1);assert.equal(m.option.dataZoom[0].type,'inside');
 assert.equal(m.option.dataZoom[0].zoomOnMouseWheel,true);assert.equal(m.option.dataZoom[0].moveOnMouseMove,'alt');
 m.api.setLegend('SPY',false);m.api.select(2);
 const key=k=>m.listeners.get('keydown')({key:k,target:m.element,preventDefault(){}});
 key('+');assert.ok(m.api.getState().zoom.start>0);key('0');assert.deepEqual(m.api.getState().zoom,{start:0,end:100});
 assert.equal(m.api.getState().legend.SPY,false);assert.equal(m.api.getState().selectedIndex,2);m.api.destroy();
});


test('legend events expose isolated visibility while preserving zoom and pinned observation',()=>{
 let visible;const m=mockMount(line,{onLegendChange:v=>{visible=v;v.A=true;}});
 m.api.setZoom(20,80);m.api.select(2);m.handlers.get('legendselectchanged')({selected:{A:false,SPY:true}});
 assert.deepEqual(m.api.getState().zoom,{start:20,end:80});assert.equal(m.api.getState().selectedIndex,2);
 assert.equal(m.api.getState().legend.A,false);assert.equal(visible.SPY,true);m.api.destroy();
});

test('accessible chart name announces its title once and preserves semantic detail',()=>{
 const m=mockMount({...line,title:'Comparison',description:'Comparison. Same units and period.'});
 const label=m.attrs.get('aria-label');assert.equal(label.split('Comparison').length-1,1);assert.match(label,/Same units and period/);assert.match(label,/좌우 방향키/);m.api.destroy();
});
