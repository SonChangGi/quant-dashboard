import test from 'node:test';
import assert from 'node:assert/strict';
import { validateSpec, createEngine, themes, CHART_KINDS } from '../engine/index.js';

function freezeTree(value) {
  if (value && typeof value === 'object') {
    Object.values(value).forEach(freezeTree);
    Object.freeze(value);
  }
  return value;
}
const table = freezeTree({
  kind:'table', title:'관측 비교', columns:[
    {key:'name',label:'종목',type:'text'}, {key:'value',label:'관측',type:'number'}
  ], rows:[{id:'a',name:'A',value:0},{id:'b',name:'B',value:null}]
});
const waterfall = {
  kind:'waterfall',title:'순기여도',initial:100,verifyTotals:true,
  rows:[{name:'가격 기여',value:20},{name:'비용',value:-3},{name:'종료',type:'total',value:117}]
};

test('core accepts immutable table evidence and never coerces missing observations into zero',()=>{
  const before=structuredClone(table);
  assert.equal(validateSpec(table),table);
  assert.deepEqual(table,before);
  assert.equal(table.rows[1].value,null);
});

test('row identity rejects duplicates, including numeric and string DOM collisions',()=>{
  for(const ids of [['a','a'],[1,'1'],[null,'b'],[undefined,'b']]){
    assert.throws(()=>validateSpec({...table,rows:ids.map((id,i)=>({id,name:`N${i}`,value:i}))}),/id/);
  }
  assert.equal(validateSpec({...table,rows:[]}).rows.length,0,'empty is a valid observable state');
});

test('column keys are unique and an invalid candidate does not mutate last valid evidence',()=>{
  const before=structuredClone(table);
  const invalid={...table,columns:[table.columns[0],{...table.columns[1],key:'name'}]};
  assert.throws(()=>validateSpec(invalid),/key/);
  assert.deepEqual(table,before);
  assert.equal(invalid.columns[1].key,'name','validation must not silently repair the candidate');
});

test('core rejects absent titles and dispatches chart validation before mount allocation',()=>{
  for(const title of [undefined,'','  ',3])assert.throws(()=>validateSpec({...table,title}),/title/);
  assert.throws(()=>validateSpec({title:'Unknown',kind:'unknown'}),/unknown kind/);
  assert.throws(()=>validateSpec({title:'길이 불일치',kind:'line',x:['a','b'],series:[{name:'A',data:[1]}]}),/length/);
  assert.throws(()=>createEngine(null),/root/);
});

test('verified waterfall rejects mismatched totals and preserves all signed contributions',()=>{
  const input=freezeTree(structuredClone(waterfall));
  const before=structuredClone(input);
  assert.equal(validateSpec(input),input);
  assert.deepEqual(input,before);
  assert.throws(()=>validateSpec({...waterfall,rows:[...waterfall.rows.slice(0,2),{name:'종료',type:'total',value:118}]}),/합계/);
  assert.equal(validateSpec({...waterfall,verifyTotals:false,rows:[...waterfall.rows.slice(0,2),{name:'별도 잔액',type:'total',value:118}]}).rows[2].value,118);
});

test('waterfall verification handles negative opening balances, zero crossings and intermediate totals',()=>{
  const spec={kind:'waterfall',title:'교차',initial:-20,verifyTotals:true,rows:[
    {name:'하락',value:-5},{name:'회복',value:40},{name:'중간',type:'total',value:15},
    {name:'후속 비용',value:-3},{name:'종료',type:'total',value:12}
  ]};
  assert.equal(validateSpec(spec),spec);
  assert.throws(()=>validateSpec({...spec,rows:[...spec.rows.slice(0,-1),{name:'종료',type:'total',value:15}]}),/합계/);
});

test('waterfall arithmetic tolerates binary roundoff while rejecting non-finite evidence',()=>{
  assert.doesNotThrow(()=>validateSpec({kind:'waterfall',title:'반올림',verifyTotals:true,rows:[
    {name:'A',value:.1},{name:'B',value:.2},{name:'합계',type:'total',value:.3}
  ]}));
  for(const value of [NaN,Infinity,-Infinity])assert.throws(()=>validateSpec({...waterfall,rows:[{name:'A',value}]}),/finite/);
});

test('theme contract exposes the same role tokens in dark and light and recognized chart kinds are unique',()=>{
  const expected=['bg','surface','raised','text','muted','border','grid','accent','positive','negative','palette'];
  for(const theme of Object.values(themes)){
    assert.deepEqual(Object.keys(theme),expected);
    for(const key of expected.filter(x=>x!=='palette'))assert.match(theme[key],/^#[0-9a-f]{6}$/i);
    assert.ok(theme.palette.length>=4);
  }
  assert.equal(new Set(CHART_KINDS).size,CHART_KINDS.length);
});

import { JSDOM } from 'jsdom';
function environment(echarts) {
  const dom=new JSDOM('<main id="root"><p id="retained">User-owned content</p><div id="host"></div></main><div id="outside"></div>');
  const doc=dom.window.document, root=doc.querySelector('#root'), host=doc.querySelector('#host');
  return {dom,doc,root,host,engine:createEngine(root,{echarts})};
}
function fakeEcharts({failRender=false}={}) {
  const instances=new Map();
  return {instances,init(element){let option,disposed=false;const chart={setOption(next){if(failRender)throw new Error('render failed');option=next;},getOption(){return option;},on(){},dispatchAction(){},resize(){},dispose(){disposed=true;},get disposed(){return disposed;}};instances.set(element,chart);return chart;},getInstanceByDom(element){return instances.get(element);}};
}
const line={kind:'line',title:'비교',x:['a','b'],series:[{name:'A',data:[1,2]}]};

test('table validation rejects missing column contracts and invalid row identities',()=>{
  for(const column of [{label:'A',type:'text'},{key:' ',label:'A',type:'text'},{key:'a',label:'',type:'text'},{key:'a',label:'A',type:'unsupported'}])assert.throws(()=>validateSpec({...table,columns:[column]}),TypeError);
  for(const id of ['', ' ', {}, NaN, Infinity])assert.throws(()=>validateSpec({...table,rows:[{id}]}),/id/);
});
test('waterfall explicit initial matches opening total; implicit opening total is valid',()=>{
  const spec={kind:'waterfall',title:'초기 잔액',verifyTotals:true,rows:[{name:'시작',type:'total',value:50},{name:'상승',value:2},{name:'끝',type:'total',value:52}]};
  assert.doesNotThrow(()=>validateSpec(spec));assert.doesNotThrow(()=>validateSpec({...spec,initial:50}));assert.throws(()=>validateSpec({...spec,initial:100}),/합계/);
});
test('invalid update preserves visible DOM, state and prior data',()=>{
  const e=environment(), handle=e.engine.mount(e.host,table),before=handle.element.outerHTML,state=handle.getState();
  assert.throws(()=>handle.update({...table,rows:[table.rows[0],table.rows[0]]}),/id/);
  assert.equal(handle.element.outerHTML,before);assert.deepEqual(handle.getState(),state);
  assert.throws(()=>handle.update(line),/kind/);assert.equal(handle.element.outerHTML,before);
  e.engine.destroy();e.dom.window.close();
});
test('update snapshots caller data against later mutation and theme rerender',()=>{
  const charts=fakeEcharts(),e=environment(charts),handle=e.engine.mount(e.host,line);
  const next=structuredClone(line);next.series[0].data=[3,4];handle.update(next);next.series[0].data[0]=999;next.title='outside mutation';
  e.engine.setTheme('light');assert.deepEqual([...charts.instances.values()][0].getOption().series[0].data,[3,4]);
  assert.equal(handle.element.querySelector('h2').textContent,'비교');assert.equal(handle.element.querySelector('.qe-raw-table td').textContent,'3');
  e.engine.destroy();e.dom.window.close();
});
test('external hosts and failed renderer initialization leave no mounted frame',()=>{
  const e=environment();assert.throws(()=>e.engine.mount(e.doc.querySelector('#outside'),table),/root/);
  assert.throws(()=>e.engine.mount(e.host,line),/ECharts/);assert.equal(e.host.children.length,0);assert.equal(e.doc.querySelector('#outside').children.length,0);
  e.engine.destroy();e.dom.window.close();
  const charts=fakeEcharts({failRender:true}),f=environment(charts);
  assert.throws(()=>f.engine.mount(f.host,line),/render failed/);assert.equal(f.host.children.length,0);assert.ok([...charts.instances.values()][0].disposed);
  f.engine.destroy();f.dom.window.close();
});
test('destroy removes only owned frames, invalidates handles and is idempotent',()=>{
  const e=environment(),handle=e.engine.mount(e.host,table),retained=e.doc.querySelector('#retained');
  e.engine.destroy();e.engine.destroy();handle.destroy();assert.equal(e.doc.querySelector('#retained'),retained);assert.equal(e.doc.querySelector('#host'),e.host);assert.equal(e.host.children.length,0);
  assert.throws(()=>handle.update(table),/destroy/);assert.throws(()=>e.engine.mount(e.host,table),/destroy/);assert.throws(()=>e.engine.setTheme('light'),/destroy/);e.dom.window.close();
});
test('status update preserves retry behavior and rejects invalid transition atomically',()=>{
  const e=environment();let retries=0;const status={kind:'status',title:'자료',state:'loading'},handle=e.engine.mount(e.host,status,{onRetry(){retries++;}});
  assert.equal(handle.element.querySelector('.qe-status').getAttribute('aria-busy'),'true');handle.update({...status,state:'error'});
  handle.element.querySelector('.qe-status button').click();assert.equal(retries,1);assert.equal(handle.element.querySelector('.qe-status').getAttribute('role'),'alert');
  assert.throws(()=>handle.update({...status,state:'success'}),/state/);assert.deepEqual(handle.getState(),{state:'error'});
  handle.update({...status,state:'empty'});assert.equal(handle.element.querySelector('.qe-status button'),null);e.engine.destroy();e.dom.window.close();
});
test('independent engines keep theme scopes and owned mounts isolated',()=>{
  const e=environment(),secondRoot=e.doc.querySelector('#outside'),second=createEngine(secondRoot,{theme:'light'});
  e.engine.mount(e.host,table);second.mount(secondRoot,table);
  assert.equal(secondRoot.dataset.qeTheme,'light');assert.equal(e.host.closest('[data-qe-theme]').dataset.qeTheme,'dark');
  e.engine.setTheme('light');second.setTheme('dark');assert.equal(e.host.closest('[data-qe-theme]').dataset.qeTheme,'light');assert.equal(secondRoot.dataset.qeTheme,'dark');
  e.engine.destroy();assert.equal(secondRoot.querySelectorAll('.qe-frame').length,1);second.destroy();e.dom.window.close();
});

test('direct chart interaction exposes reset only after zoom and keeps source data optional',()=>{
 const e=environment(fakeEcharts());
 const v=e.engine.mount(e.host,{...line,x:['a','b','c'],series:[{name:'A',data:[100,110.00000000000001,null]}]});
 assert.equal(e.host.querySelector('.qe-observation-steps'),null);
 assert.equal(e.host.querySelector('.qe-chart-help'),null);
 const reset=[...e.host.querySelectorAll('button')].find(b=>b.textContent==='전체 기간');
 assert.equal(reset.hidden,true);v.renderer.setZoom(20,70);assert.equal(reset.hidden,false);
 v.renderer.setLegend('A',false);reset.click();assert.equal(reset.hidden,true);assert.equal(v.getState().legend.A,false);
 v.renderer.setLegend('A',true);v.renderer.select(1);assert.equal(e.host.querySelector('.qe-readout').textContent,'bA 110');
 v.renderer.select(null);assert.equal(e.host.querySelector('.qe-readout').textContent,'');
 const data=e.host.querySelector('.qe-data');
 assert.equal(e.host.querySelector('.qe-chart-menu'),null);
 assert.equal(data.open,false);data.querySelector('summary').click();assert.equal(data.open,true);
 assert.equal(e.host.querySelector('.qe-spec-source').open,false);
 e.engine.destroy();e.dom.window.close();
});

test('every time-series has immediate range output without a mode button or consumer',()=>{
 const e=environment(fakeEcharts());const v=e.engine.mount(e.host,{...line,x:['a','b','c'],series:[{name:'A',data:[100,110,120]}]});
 assert.equal([...e.host.querySelectorAll('button')].some(b=>b.textContent==='구간 선택'),false);
 v.renderer.setRange(2,0);assert.match(e.host.querySelector('.qe-range-readout').textContent,/a → c.*100 → 120.*20%/);
 v.renderer.setRange(null,null);assert.equal(e.host.querySelector('.qe-range-readout').hidden,true);
 e.engine.destroy();e.dom.window.close();
});
