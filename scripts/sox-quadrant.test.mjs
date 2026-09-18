import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const context = vm.createContext({console, URL});
vm.runInContext(fs.readFileSync('assets/app.js','utf8'), context);
const api = context.__QUANT_DASHBOARD_TESTS__;
const fixture = () => {
  const constituents = Array.from({length:6}, (_,i) => ({rank:i+1,ticker:`S${i}`,name:`Stock ${i}`,proxyWeight:(6-i)/21,scores:{priceMomentum:1-i*.15,earningsMomentum:.95-i*.1,combined:.975-i*.125,label:'original label'}}));
  const analysis = {schemaVersion:1,projectId:'sox',dataAsOf:'2026-09-17',generatedAt:'2026-09-18T03:54:20Z',status:{level:'ok'},index:{symbol:'SOX',constituentCount:6},constituents};
  const summary = {schemaVersion:1,contract:'quant-research-summary',projectId:'sox',dataAsOf:analysis.dataAsOf,generatedAt:analysis.generatedAt,status:{state:'ok'},coverage:{entityCount:6},primaryEntities:constituents.slice(0,5).map(r=>({id:r.ticker,symbol:r.ticker,name:r.name,metrics:{rank:r.rank,weight:r.proxyWeight,score:r.scores.combined,priceMomentum:r.scores.priceMomentum,earningsMomentum:r.scores.earningsMomentum}}))};
  return {summary,analysis};
};

test('SOX connects the complete same-publication universe without changing the Top5 summary', () => {
  const {summary,analysis} = fixture(), source = JSON.stringify({summary,analysis});
  const result = api.parseSoxPanel({summary,soxAnalysis:analysis});
  assert.equal(result.quadrant.count,6);
  assert.equal(result.quadrant.rows.length,6);
  assert.equal(result.quadrant.plottedCount,6);
  assert.equal(JSON.stringify(result.rows),JSON.stringify(api.parseSox(summary).rows));
  assert.equal(JSON.stringify({summary,analysis}),source);
  analysis.constituents.forEach((row,i)=>{
    assert.equal(result.quadrant.rows[i].priceMomentum,row.scores.priceMomentum);
    assert.equal(result.quadrant.rows[i].earningsMomentum,row.scores.earningsMomentum);
    assert.equal(result.quadrant.rows[i].weight,row.proxyWeight);
    assert.equal(result.quadrant.rows[i].status,row.scores.label);
  });
});

test('different publication, status, coverage, duplicate identities and changed leader values fail closed', () => {
  const changes = [
    a=>a.schemaVersion=2,a=>a.projectId='other',a=>a.index.symbol='OTHER',a=>a.dataAsOf='2026-09-16',
    a=>a.generatedAt='2026-09-18T03:55:20Z',a=>a.status.level='error',a=>a.status.level='degraded',
    a=>a.index.constituentCount=5,a=>a.constituents.pop(),a=>a.constituents[5].ticker='S0',
    a=>a.constituents[5].rank=1,a=>a.constituents[0].scores.priceMomentum=.8,
    a=>a.constituents[0].proxyWeight=.4,
  ];
  for (const change of changes) {
    const {summary,analysis}=fixture();change(analysis);
    const result=api.parseSoxPanel({summary,soxAnalysis:analysis});
    assert.equal(result.quadrant,null);
    assert.ok(result.quadrantError);
    assert.equal(result.rows.length,5);
  }
  const {summary}=fixture();
  assert.equal(api.parseSoxPanel({summary}).quadrant,null);
});

test('null scores remain missing, while zero is a real coordinate; invalid numeric values are rejected', () => {
  const {summary,analysis}=fixture();analysis.constituents[5].scores.earningsMomentum=null;
  const result=api.parseSoxQuadrant(summary,analysis);
  assert.equal(result.plottedCount,5);
  assert.equal(result.rows[5].earningsMomentum,null);
  const geometry=api.soxQuadrantGeometry(result.rows,900,'S0');
  assert.equal(geometry.points.length,5);
  analysis.constituents[5].scores.earningsMomentum=0;
  const zero=api.soxQuadrantGeometry(api.parseSoxQuadrant(summary,analysis).rows,900,'S0');
  assert.equal(zero.points.find(p=>p.ticker==='S5').y,zero.bounds.bottom);
  for(const invalid of [undefined,NaN,Infinity,-.01,1.01,'0.5']) {
    analysis.constituents[5].scores.earningsMomentum=invalid;
    assert.throws(()=>api.parseSoxQuadrant(summary,analysis));
  }
});

test('a missing proxy weight does not suppress valid price and earnings coordinates', () => {
  const {summary,analysis}=fixture();
  summary.status.state='degraded';analysis.status.level='degraded';
  summary.primaryEntities[0].metrics.weight=null;analysis.constituents[0].proxyWeight=null;
  const q=api.parseSoxQuadrant(summary,analysis);
  assert.equal(q.rows[0].weight,null);
  assert.equal(q.plottedCount,6);
  assert.equal(api.soxQuadrantGeometry(q.rows,900,'S0').points.length,6);
});

test('quadrant geometry never shifts underlying coordinates to avoid label collisions', () => {
  const rows=fixture().analysis.constituents.map(r=>({rank:r.rank,ticker:r.ticker,priceMomentum:.5,earningsMomentum:.5}));
  for(const width of [240,320,1000]) {
    const g=api.soxQuadrantGeometry(rows,width,'S5');
    assert.equal(g.points.length,6);
    for(const point of g.points) {assert.equal(point.x,g.centerX);assert.equal(point.y,g.centerY);}
    assert.ok(g.labels.some(l=>l.ticker==='S5'));
    for(const a of g.labels) {
      assert.ok(a.x>=g.bounds.left && a.x+a.width<=g.bounds.right);
      assert.ok(a.y>=g.bounds.top-20 && a.y+a.height<=g.bounds.bottom);
      for(const b of g.labels.filter(b=>b.ticker!==a.ticker)) assert.ok(a.x+a.width<=b.x || b.x+b.width<=a.x || a.y+a.height<=b.y || b.y+b.height<=a.y);
    }
  }
});

test('chart failure is visible in health without discarding valid summary rows', () => {
  const record={mode:'live',project:{id:'sox'},summary:{quadrantError:'publication mismatch',meta:{statusState:'ok'}}};
  assert.equal(api.visibleHealthLabel(record),'차트 확인 필요');
  assert.equal(api.healthTone(record),'warn');
});
