import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const context = vm.createContext({console, URL});
vm.runInContext(fs.readFileSync('assets/app.js', 'utf8'), context);
const api = context.__QUANT_DASHBOARD_TESTS__;

test('DRAM product labels preserve generation, Gb, speed, organisation and eTT distinctions', () => {
  const names = ['DDR4 16Gb (2Gx8) 3200', 'DDR4 8Gb (1Gx8) 3200', 'DDR5 16Gb (2Gx8) 4800/5600', 'DDR5 16Gb (2Gx8) eTT', 'DDR3 4Gb 512Mx8 1600/1866', 'DDR4 16Gb (2Gx8) eTT'];
  const labels = names.map(name => api.dramProductLabel(`${name} · TrendForce daily`));
  assert.equal(new Set(labels.map(label => label.name + label.spec)).size, 6);
  assert.equal(labels[2].name, 'DDR5 16Gb');
  assert.equal(labels[2].spec, '4800/5600 · 2G×8');
  assert.equal(labels[4].spec, '1600/1866 · 512M×8');
  assert.equal(labels[5].spec, 'eTT · 2G×8');
  assert.equal(labels[0].full, `${names[0]} · TrendForce daily`);
  for (const name of ['DDR4 16GB RDIMM 3200', 'New product / contract']) assert.equal(api.dramProductLabel(name).name, name);
});

test('SOX relative scores remain 0–1 and missing values never become zero marks', () => {
  for (const value of [null, undefined, NaN, -0.1, 1.1, '0.5']) assert.equal(api.soxScore(value), null);
  assert.equal(api.soxScore(0), 0);
  assert.equal(api.soxScore(1), 1);
  const rows = [{rank:1,ticker:'AAA',priceMomentum:null,earningsMomentum:.8,score:.7}, {rank:2,ticker:'BBB',priceMomentum:0,earningsMomentum:1,score:.6}];
  const snapshot = JSON.stringify(rows), geometry = api.soxQuadrantGeometry(rows, 800, 'BBB');
  assert.equal(geometry.points.length, 1);
  assert.equal(geometry.points[0].ticker, 'BBB');
  assert.equal(geometry.points[0].x, geometry.bounds.left);
  assert.equal(geometry.points[0].y, geometry.bounds.top);
  assert.equal(JSON.stringify(rows), snapshot);
});

test('ETF shared scale includes every fund and current Top10 history, independent of display limit', () => {
  const rows = [{chartSeries:[{points:[{date:'2026-09-01',value:.08},{date:'2026-09-03',value:null}]}]}, {chartSeries:[{points:[{date:'2026-09-02',value:.13},{date:'2026-09-04',value:.12}]}]}];
  const domain = api.etfComparisonDomain(rows);
  assert.equal(domain.minDate, Date.parse('2026-09-01'));
  assert.equal(domain.maxDate, Date.parse('2026-09-04'));
  assert.equal(domain.yTicks[0], 0);
  assert.ok(domain.yTicks.at(-1) >= .13);
  const empty = api.etfComparisonDomain([]);
  assert.equal(empty.minDate, null);
  assert.equal(empty.maxDate, null);
});

test('ETF display controls retain missing history as gaps, exact dates and all series on Top10', () => {
  const row = {name:'Fund',chartSeries:Array.from({length:10}, (_, i) => ({rank:i+1,label:`S${i}`,points:[{date:'2026-09-01',value:.05+i/100},{date:'2026-09-02',value:null},{date:'2026-09-03',value:.06+i/100}]}))};
  const before = JSON.stringify(row), domain = api.etfComparisonDomain([row]);
  const compact = api.renderEtfMiniChart(row, {width:250,limit:5,domain});
  const all = api.renderEtfMiniChart(row, {width:400,limit:10,domain});
  assert.equal((compact.match(/class="etf-mini-series /g) || []).length, 5);
  assert.match(compact, /현재 상위 5종목 편입비중 추이/);
  assert.match(all, /현재 상위 10종목 편입비중 추이/);
  assert.equal((all.match(/class="etf-mini-series /g) || []).length, 10);
  assert.equal((all.match(/class="etf-mini-line"/g) || []).length, 20);
  assert.equal((all.match(/class="etf-data-point"/g) || []).length, 20);
  assert.ok(!all.includes('data-date="2026-09-02"'));
  assert.ok(compact.includes(`data-y-max="${domain.yTicks.at(-1)}"`));
  assert.equal(JSON.stringify(row), before);
});

test('DRAM uses source averages without synthesizing prices from highs and lows', () => {
  const seriesFor = (values) => api.parseDram({observations: [{
    source: 'trendforce', kind: 'spot', cadence: 'daily',
    product_id: 'ddr4', product_name: 'DDR4 16Gb (2Gx8) 3200',
    date: '2026-09-21', values,
  }]}, {series: []}, {}).series;
  for (const values of [{high: 80, low: 40}, {session_high: 80}, {average: 0}, {average: -1}, {session_average: NaN}]) {
    assert.equal(seriesFor(values).length, 0);
  }
  assert.equal(seriesFor({session_average: 55.433, average: 999})[0].points[0][1], 55.433);
  assert.equal(seriesFor({average: 45})[0].points[0][1], 45);
});
