import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const context = vm.createContext({ console, URL });
vm.runInContext(readFileSync('assets/app.js', 'utf8'), context);
const api = context.__QUANT_DASHBOARD_TESTS__;
const clone = (value) => JSON.parse(JSON.stringify(value));
const week = (date, state = 'risk_on') => {
  const day = (n) => new Date(Date.parse(date) + n * 7 * 86400000).toISOString().slice(0, 10);
  const values = { risk_on: .6, transition: .35, risk_off: .05 };
  return { date, current: { state, memberships: values, primary_membership: values[state], membership_entropy: .3, method: 'risk_score_anchor_membership' },
    next_week: { date: day(1), state: 'risk_on', probabilities: { risk_on: .7, transition: .2, risk_off: .1 }, confidence: .7, entropy: .73 },
    transition_probability: .3, transition_risk: Object.fromEntries([[1,.3],[4,.6],[13,.9]].map(([n,p])=>[`${n}w`,{probability:p,target_end:day(n)}])) };
};
const past = [week('2026-08-14','transition'),week('2026-08-21','risk_off')];
const recent = [week('2026-09-04'),week('2026-09-11')];
const history = { schema_version:'regime-dashboard-history/1', generation_id:'test-generation', source_payload_sha256:'a'.repeat(64), weekly:past };
const body = JSON.stringify(history);
const descriptor = { path:'regime-history-000.json', start:past[0].date, end:past.at(-1).date, row_count:past.length, sha256:createHash('sha256').update(body).digest('hex') };
const core = { schema_version:'regime-dashboard-core/2', generation_id:history.generation_id, source_payload_sha256:history.source_payload_sha256, history_sidecars:[descriptor],
  payload:{meta:{mode:'demo',result_version:'weekly-regime-result-v5',generation_id:history.generation_id,generated_at:'2026-09-12T12:00:00Z',data_as_of:'2026-09-11',status:'ok'},
    sources:[{id:'synthetic_test',license_class:'synthetic_fixture'}],weekly:recent} };
const sources = {summary:core,regimeHistory:{[descriptor.path]:history}};

test('trend preserves membership, forecast probability, hysteresis state and forecast entropy',()=>{
  const trend=api.parseRegimePanel(sources).trend;
  assert.equal(trend.rows.length,4);
  assert.equal(trend.currentMeasureLabel,'소속도');
  assert.equal(trend.rows[0].currentState,'transition');
  assert.equal(trend.rows[0].memberships.risk_on,.6);
  assert.equal(trend.rows[0].probabilities.risk_on,.7);
  assert.equal(trend.rows[0].entropy,.73);
});

test('actual t+1 uses target date, never next array row or predicted state',()=>{
  const {rows}=api.parseRegimeTrend(core,sources.regimeHistory);
  assert.equal(rows[0].actualState,'risk_off');
  assert.equal(rows[1].actualState,null,'missing Aug28 must not borrow Sep04');
  assert.equal(rows[2].actualState,'risk_on');
  assert.equal(rows.at(-1).actualState,null,'future result remains pending');
});

test('history fetch uses publisher SHA and exact generation identity',async()=>{
  let calls=0;
  const result=await api.enrichRegimeSources({summary:core},async(url,timeout,sha)=>{
    calls++;assert.equal(url,'https://sonchanggi.github.io/regime/data/regime-history-000.json');
    assert.equal(sha,createHash('sha256').update(body).digest('hex'));assert.ok(timeout>0);
    return {ok:true,data:clone(history),bytes:body.length};
  });
  assert.equal(calls,1);assert.equal(result.dataSources.regimeHistoryError,'');
  assert.equal(api.parseRegimePanel(result.dataSources).trend.rows.length,4);
});

test('wrong generation, source hash, bounds and counts reject sidecar history',()=>{
  for (const edit of [h=>h.generation_id='old',h=>h.source_payload_sha256='b'.repeat(64),h=>h.schema_version='unknown',h=>h.weekly.pop(),h=>h.weekly.reverse()]) {
    const h=clone(history);edit(h);assert.throws(()=>api.validateRegimeHistory(h,core,descriptor));
  }
});

test('untrusted history paths and hash failures do not replace the usable summary',async()=>{
  const p=clone(core);p.history_sidecars[0].path='../other.json';
  let calls=0;
  const enriched=await api.enrichPanelSources(api.PANEL_ADAPTERS.regime,{summary:p},async()=>{calls++;return {ok:true};});
  assert.equal(calls,0);assert.equal(api.parseRegimePanel(enriched.dataSources).trend,null);
  const failed=await api.enrichRegimeSources({summary:core},async()=>({ok:false,error:'Published JSON SHA-256 mismatch.'}));
  const summary=api.parseRegimePanel(failed.dataSources);
  assert.equal(summary.publicPayloadValid,true);assert.equal(summary.currentConfidence,.6);
  assert.equal(summary.trend,null);assert.match(summary.trendError,/SHA-256/);
  assert.equal(api.visibleHealthLabel({mode:'live',summary}),'차트 확인 필요');
});

test('malformed older observations fail the chart while retaining the current summary',()=>{
  for(const edit of [p=>p.weekly[0].current.memberships.risk_off=null,p=>p.weekly[0].next_week.date='2026-08-28',p=>p.weekly[0].next_week.entropy=2,p=>p.weekly[1].date=p.weekly[0].date]){
    const h=clone(history);edit(h);const summary=api.parseRegimePanel({summary:core,regimeHistory:{[descriptor.path]:h}});
    assert.equal(summary.publicPayloadValid,true);assert.equal(summary.trend,null);assert.ok(summary.trendError);
  }
});

test('core and history overlap cannot silently overwrite observations',()=>{
  const p=clone(core);p.payload.weekly.unshift(past[1]);
  assert.throws(()=>api.parseRegimeTrend(p,sources.regimeHistory),/duplicate|overlap/);
});

test('period filters select 26, 52, 104 or all observations without changing the endpoint',()=>{
  const row=api.parseRegimeTrend(core,sources.regimeHistory).rows.at(-1);
  const rows=Array.from({length:150},(_,i)=>({...row,date:new Date(Date.parse('2023-01-06')+i*7*86400000).toISOString().slice(0,10)}));
  for(const [window,count] of [[26,26],[52,52],[104,104],['all',150]]){
    const selected=api.windowedRegimeRows({rows},window);
    assert.equal(selected.length,count);assert.equal(selected.at(-1).date,rows.at(-1).date);
    assert.equal(selected[0].date,rows[150-count].date);
  }
  assert.equal(rows.length,150);
});

test('chart uses common percent scales, time distances and separate authoritative backgrounds',()=>{
  const rows=api.parseRegimeTrend(core,sources.regimeHistory).rows;
  for(const width of [280,334,580,900]){
    const g=api.regimeTrendGeometry(rows,width);
    assert.equal(g.y(1,g.observedTop),g.observedTop);
    assert.equal(g.y(0,g.forecastTop),g.forecastTop+g.panelHeight);
    assert.ok(Math.abs((g.x(2)-g.x(1))/(g.x(1)-g.x(0))-2)<1e-10);
    assert.equal(g.panels[0].bands[0].state,'transition');
    assert.equal(g.panels[1].bands[0].state,'risk_on');
    assert.ok(g.panels[0].bands[1].right<g.panels[0].bands[2].left,'missing week remains unshaded');
    for(const panel of g.panels)for(const {x,y} of panel.series.flatMap(s=>s.points)){
      assert.ok(x>=g.left&&x<=g.right);assert.ok(y>=panel.top&&y<=panel.top+g.panelHeight);
    }
  }
});

test('nearby endpoint values have distinct label positions at every viewport',()=>{
  const row=clone(api.parseRegimeTrend(core,sources.regimeHistory).rows.at(-1));
  row.memberships={risk_on:.334,transition:.333,risk_off:.333};
  for(const width of [280,334,580]){
    const g=api.regimeTrendGeometry([row],width),labels=g.panels[0].endpoints;
    for(let i=1;i<labels.length;i++)assert.ok(labels[i].labelY-labels[i-1].labelY>=18);
  }
});

test('unavailable chart clears the previous graph instead of showing old observations',()=>{
  const target={innerHTML:'<svg>old</svg>'};context.document={querySelector:()=>target};
  api.renderRegimeTrend(null,{id:'regime'});
  assert.ok(!target.innerHTML.includes('<svg>'));assert.match(target.innerHTML,/불러올 수 없습니다/);
  delete context.document;
});
