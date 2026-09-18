import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = readFileSync('assets/app.js', 'utf8');
const context = vm.createContext({ console, URL });
vm.runInContext(source, context);
const api = context.__QUANT_DASHBOARD_TESTS__;
const clone = (value) => JSON.parse(JSON.stringify(value));
const summary = {
  schemaVersion: 1, contract: 'quant-research-summary', projectId: 'fearngreed', methodologyVersion: 'fear-flow-v5',
  generatedAt: '2026-06-21T12:00:00Z', dataAsOf: '2026-06-21', status: { state: 'degraded' },
  primaryEntities: [{ id: 'KOSPI', name: 'KOSPI', signalState: 'greed', sentimentPercentile: 90 }],
};
const points = Array.from({ length: 21 }, (_, index) => ({
  date: `2026-06-${String(index + 1).padStart(2, '0')}`,
  return1d: (index - 10) / 1000, rawFlowTrillion: (index - 10) / 10,
  role: index === 20 ? 'current' : 'training', state: 'neutral',
}));
const fit = { model: 'raw', fitMethod: 'ols', alpha: .4, beta: -50, trainingCount: 20,
  observed: 1, expected: -.1, residual: 1.1, state: 'neutral', percentile: 60 };
const dashboard = {
  schemaVersion: 1, methodologyVersion: summary.methodologyVersion, dataAsOf: summary.dataAsOf,
  generatedAt: summary.generatedAt, status: summary.status,
  scatterByModel: { raw: points },
  scatterMetaByModel: { raw: { model: 'raw', unit: 'krw_trillion', window: 20, trainingCount: 20,
    currentCount: 1, pointCount: 21, roles: { training: 'rolling_window', current: 'out_of_sample_observation' },
    stateBoundaries: {
      method: 'empirical_cdf_transition_order_statistic', fitScope: 'current_fit_on_prior_window', trainingCount: 20,
      comparators: { extremeFear: 'residual < extremeFearUpper', fear: 'extremeFearUpper <= residual < fearUpper', neutral: 'fearUpper <= residual < greedLower', greed: 'greedLower <= residual < extremeGreedLower', extremeGreed: 'residual >= extremeGreedLower' },
      percentileCuts: { extremeFearUpper: 5, fearUpper: 20, greedLower: 80, extremeGreedLower: 95 },
      // Independent order statistics: residual(i) = -1.9 + .15*i for i=0..19.
      residualOffsets: { extremeFearUpper: -1.75, fearUpper: -1.3, greedLower: .35, extremeGreedLower: .8 },
    } } },
  regression: { raw: fit }, models: { raw: fit },
};

test('published raw scatter preserves signed observations and its own model state', () => {
  const result = api.parseFearScatter(dashboard, summary);
  assert.equal(result.points.length, 21);
  assert.equal(result.trainingCount, 20);
  assert.equal(result.current.return1d, .01);
  assert.equal(result.current.rawFlowTrillion, 1);
  assert.equal(result.state, 'neutral', 'robust summary state is not used for the raw graph');
  assert.equal(result.points[0].rawFlowTrillion, -1);
});

test('mixed publication identity and unavailable inputs are rejected', () => {
  for (const change of [
    { dataAsOf: '2026-06-20' }, { generatedAt: '2026-06-22T12:00:00Z' },
    { methodologyVersion: 'unknown' }, { status: { state: 'unavailable' } }, { schemaVersion: 2 },
  ]) assert.throws(() => api.parseFearScatter({ ...dashboard, ...change }, summary));
  assert.throws(() => api.parseFearScatter({ ...dashboard, status: { state: 'unavailable' } }, { ...summary, status: { state: 'unavailable' } }));
});

test('raw units and fit must not silently become scaled shares or robust fits', () => {
  for (const edit of [
    (p) => { p.scatterMetaByModel.raw.unit = 'market_turnover_share'; },
    (p) => { p.regression.raw.fitMethod = 'huber'; },
    (p) => { p.models.raw.alpha += .1; },
    (p) => { p.models.raw.state = 'unavailable'; },
    (p) => { p.regression.raw.observed = 2; p.models.raw.observed = 2; },
  ]) { const p = clone(dashboard); edit(p); assert.throws(() => api.parseFearScatter(p, summary)); }
});

test('missing, duplicate, misdated or non-finite observations cannot create a chart', () => {
  for (const edit of [
    (p) => { p.scatterByModel.raw[0].return1d = null; },
    (p) => { p.scatterByModel.raw[0].rawFlowTrillion = '0'; },
    (p) => { p.scatterByModel.raw[0].date = '2026-02-30'; },
    (p) => { p.scatterByModel.raw[0].role = 'current'; },
    (p) => { p.scatterByModel.raw[1].date = p.scatterByModel.raw[0].date; },
    (p) => { p.scatterByModel.raw.at(-1).date = '2026-06-22'; },
    (p) => { p.scatterByModel.raw.reverse(); },
    (p) => { p.scatterMetaByModel.raw.trainingCount = 19; },
  ]) { const p = clone(dashboard); edit(p); assert.throws(() => api.parseFearScatter(p, summary)); }
});

test('background regions must match publisher residual order statistics', () => {
  const p = clone(dashboard);
  p.scatterMetaByModel.raw.stateBoundaries.residualOffsets.greedLower = .5;
  assert.throws(() => api.parseFearScatter(p, summary), /boundary mismatch/);
  const reversed = clone(dashboard);
  reversed.scatterMetaByModel.raw.stateBoundaries.comparators.extremeFear = 'residual > extremeFearUpper';
  assert.throws(() => api.parseFearScatter(reversed, summary), /comparator mismatch/);
  p.scatterMetaByModel.raw.stateBoundaries = null;
  assert.equal(api.parseFearScatter(p, summary).boundaries, null);
});

test('chart source failures stay separate from the existing summary contract', () => {
  const parsed = api.parseFearPanel({ summary, dashboard: null });
  assert.equal(parsed.entityPresent, true);
  assert.equal(parsed.current.sentimentPercentile, 90);
  assert.equal(parsed.scatter, null);
  assert.match(parsed.scatterError, /publication mismatch/);
  assert.equal(api.visibleHealthLabel({ mode: 'live', summary: parsed }), '차트 확인 필요');
});

test('plot keeps negative axes, all observations and regression bands inside the view at mobile and desktop widths', () => {
  const scatter = api.parseFearScatter(dashboard, summary);
  for (const width of [300, 340, 620]) {
    const g = api.fearScatterGeometry(scatter, width);
    assert.ok(g.xTicks.some((v) => v < 0) && g.yTicks.some((v) => v < 0));
    assert.ok(g.xTicks.includes(0) && g.yTicks.includes(0));
    assert.equal(g.points.length, 21);
    assert.equal(g.points.at(-1).x, g.x(1), 'one percent is plotted as 1, not .01');
    assert.equal(g.points.at(-1).y, g.y(1), 'one trillion KRW is plotted as 1');
    for (const point of g.points) {
      assert.ok(point.x >= g.p.l && point.x <= g.w - g.p.r);
      assert.ok(point.y >= g.p.t && point.y <= g.h - g.p.b);
    }
  }
});

test('unavailable refresh clears the previous scatter instead of retaining stale marks', () => {
  const target = { innerHTML: '<svg>old observations</svg>' };
  context.document = { querySelector: () => target };
  api.renderFearScatter(null, { id: 'fearngreed' });
  assert.ok(!target.innerHTML.includes('<svg>'));
  assert.match(target.innerHTML, /불러올 수 없습니다/);
});
