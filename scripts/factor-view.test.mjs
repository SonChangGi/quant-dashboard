import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const context = vm.createContext({console, URL});
vm.runInContext(fs.readFileSync('assets/app.js', 'utf8'), context);
const api = context.__QUANT_DASHBOARD_TESTS__;

test('displayed allocation sums signal-ranked holdings without replacing them with weight-ranked concentration', () => {
  const summary = { dataAsOf:'2026-09-17', concentration:{top5Weight:.9}, rows:[
    {rank:1,symbol:'AAA',signal:6,modelWeight:.05},
    {rank:2,symbol:'BBB',signal:5,modelWeight:.1},
  ] };
  const before = JSON.stringify(summary);
  const allocation = api.factorAllocation(summary, 'momentum');
  assert.ok(Math.abs(allocation.total - .15) < 1e-12);
  assert.equal(allocation.rows[0].symbol, 'AAA');
  assert.equal(allocation.rows[1].weight, .1);
  assert.equal(allocation.rows[0].value, 6);
  assert.equal(allocation.dateLabel, '2026-09-17');
  assert.equal(JSON.stringify(summary), before);
});

test('holdings dates remain separate from a later data date and each original rank is preserved', () => {
  const view = api.factorAllocation({dataEndDate:'2026-09-17',rows:[
    {rank:1,ticker:'AAA',score:500,weight:.3,date:'2026-08-31'},
    {rank:2,ticker:'BBB',score:300,weight:.17,date:'2026-08-31'},
  ]}, 'best');
  assert.equal(view.dateLabel, '2026-08-31');
  assert.equal(view.rows[0].rank, 1);
  assert.equal(view.rows[0].value, 500);
  view.rows[1].date = '2026-09-01';
  assert.equal(api.factorAllocation({rows:[{date:'2026-08-31'},{date:'2026-09-01'}]},'best').dateLabel, '종목별 상이');
});

test('missing, empty and invalid allocations cannot become measured zero exposure', () => {
  assert.equal(api.factorAllocation({rows:[]},'best').total, null);
  for(const weight of [null,undefined,NaN,'0.1',-.1,1.1]) {
    assert.equal(api.factorAllocation({rows:[{weight}]},'best').total, null);
  }
  assert.equal(api.factorAllocation({rows:[{weight:.6},{weight:.5}]},'best').total, null);
  assert.equal(api.factorAllocation({rows:[{weight:0}]},'best').total, 0);
});

test('both strategies use one untruncated weight scale independent of loading order', () => {
  const a = {rows:[{weight:.09}]}, b = {rows:[{weight:.3000796354}]}, c = {rows:[{weight:.61}]};
  assert.equal(api.factorWeightScale([a,b]), .4);
  assert.equal(api.factorWeightScale([b,a]), .4);
  assert.equal(api.factorWeightScale([a,c]), .7);
  assert.equal(api.factorWeightScale([{rows:[{weight:1}]}]), 1);
  assert.equal(api.factorWeightScale([{rows:[{weight:null},{weight:NaN}]}]), .4);
});

test('integrated holdings use a zero-based scale that fits observed weights without clipping', () => {
  assert.equal(api.integratedWeightScale({rows:[{weight:.0847},{weight:.0701}]}), .1);
  assert.equal(api.integratedWeightScale({rows:[{weight:.021}]}), .04);
  assert.equal(api.integratedWeightScale({rows:[]}), .1);
  for (const weight of [.1,.10001,.30001,.61,1]) assert(api.integratedWeightScale({rows:[{weight}]}) >= weight);
});

test('strategy and SPY rebase on their first common actual observation, retaining gaps and drawdowns', () => {
  const nav = [{date:'2020-01-01',value:1},{date:'2020-01-02',value:2},{date:'2020-01-03',value:null},{date:'2020-01-04',value:1.5},{date:'2020-01-05',value:3}];
  const comparisons = [{id:'SPY',nav:[{date:'2020-01-02',value:4},{date:'2020-01-03',value:5},{date:'2020-01-04',value:3}]}];
  const before=JSON.stringify([nav,comparisons]);
  const p=api.factorPerformanceData(nav,comparisons);
  assert.equal(p.rows[0].date,'2020-01-02');
  assert.deepEqual(Array.from(p.rows[0].values),[100,100]);
  assert.equal(p.rows[1].values[0],null);
  assert.equal(p.rows[1].values[1],125);
  assert.deepEqual(Array.from(p.rows[2].drawdowns),[-.25,-.4]);
  assert.equal(p.rows[3].values[1],null);
  assert.equal(JSON.stringify([nav,comparisons]),before);
  const g=api.factorPerformanceGeometry(p,580);
  assert(g.ceiling>=150);assert(g.ddFloor<=-.4);
  assert.equal(g.x(0),g.left);assert.equal(g.x(p.rows.length-1),g.right);
  assert.equal(api.factorPerformanceData(nav).benchmark,false);
  assert.equal(api.factorPerformanceData([],comparisons).rows.length,0);
});
