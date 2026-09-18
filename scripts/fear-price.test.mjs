import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const context = vm.createContext({ console, URL });
vm.runInContext(readFileSync('assets/app.js', 'utf8'), context);
const api = context.__QUANT_DASHBOARD_TESTS__;
const clone = (value) => JSON.parse(JSON.stringify(value));
const normalized = (value) => JSON.parse(JSON.stringify(value));
const freeze = (value) => {
  if (value && typeof value === 'object') {
    Object.values(value).forEach(freeze);
    Object.freeze(value);
  }
  return value;
};

function fixture() {
  const summary = {
    schemaVersion: 1, contract: 'quant-research-summary', projectId: 'fearngreed',
    methodologyVersion: 'fear-flow-v5', generatedAt: '2026-06-21T12:00:00Z',
    dataAsOf: '2026-06-21', status: { state: 'degraded' },
    primaryEntities: [{ id: 'KOSPI', name: 'KOSPI', signalState: 'greed', sentimentPercentile: 90 }],
  };
  const points = Array.from({ length: 21 }, (_, index) => ({
    date: `2026-06-${String(index + 1).padStart(2, '0')}`,
    return1d: (index - 10) / 1000, rawFlowTrillion: (index - 10) / 10,
    role: index === 20 ? 'current' : 'training', state: 'extreme_greed',
  }));
  const fit = { model: 'raw', fitMethod: 'ols', alpha: .4, beta: -50, trainingCount: 20,
    observed: 1, expected: -.1, residual: 1.1, state: 'extreme_greed', percentile: 100 };
  const dashboard = {
    schemaVersion: 1, methodologyVersion: summary.methodologyVersion,
    dataAsOf: summary.dataAsOf, generatedAt: summary.generatedAt, status: summary.status,
    scatterByModel: { raw: points },
    scatterMetaByModel: { raw: {
      model: 'raw', unit: 'krw_trillion', window: 20, trainingCount: 20, currentCount: 1, pointCount: 21,
      roles: { training: 'rolling_window', current: 'out_of_sample_observation' },
      stateBoundaries: {
        method: 'empirical_cdf_transition_order_statistic', fitScope: 'current_fit_on_prior_window', trainingCount: 20,
        comparators: {
          extremeFear: 'residual < extremeFearUpper', fear: 'extremeFearUpper <= residual < fearUpper',
          neutral: 'fearUpper <= residual < greedLower', greed: 'greedLower <= residual < extremeGreedLower',
          extremeGreed: 'residual >= extremeGreedLower',
        },
        percentileCuts: { extremeFearUpper: 5, fearUpper: 20, greedLower: 80, extremeGreedLower: 95 },
        // Training residuals are independently known: -.4 + 150 * return1d.
        residualOffsets: { extremeFearUpper: -1.75, fearUpper: -1.3, greedLower: .35, extremeGreedLower: .8 },
      },
    } },
    regression: { raw: fit }, models: { raw: fit },
  };
  let close = 6000;
  const history = {
    schemaVersion: 1, methodologyVersion: summary.methodologyVersion,
    dataAsOf: summary.dataAsOf, generatedAt: summary.generatedAt, fixture: false,
    numericPrecisionDigits: 8, seriesEncoding: 'columnar-v1',
    seriesColumns: ['date', 'kospiClose', 'return1d', 'rawFlowTrillion'],
    seriesRows: [ ['2026-05-31', close, null, null], ...points.map((point) => {
      close *= 1 + point.return1d;
      return [point.date, Number(close.toFixed(8)), point.return1d, point.rawFlowTrillion];
    }) ],
  };
  return { summary, dashboard, history, scatter: api.parseFearScatter(dashboard, summary) };
}

function rejectsHistory(edit) {
  const input = fixture();
  edit(input.history);
  assert.throws(() => api.parseFearPrices(input.history, input.summary, input.scatter));
}

test('price join preserves index-point units, raw observations and date order without mutating sources', () => {
  const input = fixture();
  const before = JSON.stringify(input);
  freeze(input);
  const result = api.parseFearPrices(input.history, input.summary, input.scatter);
  assert.equal(result.length, 21);
  assert.equal(result[0].date, '2026-06-01');
  assert.equal(result[0].close, 5940, 'KOSPI close is index points, without currency scaling');
  assert.equal(result[0].rawFlowTrillion, -1, 'raw flow remains in trillion KRW');
  assert.equal(result[0].return1d, -.01, 'returns remain fractions in the data model');
  assert.equal(result.at(-1).close, input.history.seriesRows.at(-1)[1]);
  for (let index = 0; index < result.length; index += 1) {
    const { close, ...observation } = result[index];
    assert.deepEqual(normalized(observation), normalized(input.scatter.points[index]));
    assert.equal(close, input.history.seriesRows[index + 1][1]);
  }
  assert.equal(JSON.stringify(input), before);
});

test('price source must belong to the same real publication and declared precision', () => {
  for (const edit of [
    (h) => { h.schemaVersion = 2; },
    (h) => { h.generatedAt = '2026-06-22T12:00:00Z'; },
    (h) => { h.dataAsOf = '2026-06-20'; },
    (h) => { h.methodologyVersion = 'another-method'; },
    (h) => { h.fixture = true; },
    (h) => { h.numericPrecisionDigits = 6; },
    (h) => { h.seriesEncoding = 'unknown'; },
  ]) rejectsHistory(edit);
});

test('ambiguous columns, malformed rows, duplicate dates and missing selected days are rejected', () => {
  for (const edit of [
    (h) => { h.seriesColumns.push('kospiClose'); h.seriesRows.forEach((r) => r.push(r[1])); },
    (h) => { h.seriesColumns[1] = 'price'; },
    (h) => { h.seriesRows[5].pop(); },
    (h) => { h.seriesRows[5].push(0); },
    (h) => { h.seriesRows[5][0] = h.seriesRows[4][0]; },
    (h) => { h.seriesRows[0][0] = '2026-02-30'; },
    (h) => { [h.seriesRows[2], h.seriesRows[3]] = [h.seriesRows[3], h.seriesRows[2]]; },
    (h) => { h.seriesRows.splice(5, 1); },
    (h) => { h.seriesRows.at(-1)[0] = '2026-06-22'; },
  ]) rejectsHistory(edit);
});

test('selected prices and raw input fields must be finite numeric values', () => {
  for (const invalid of [null, 0, -10, '5940', NaN, Infinity]) {
    rejectsHistory((h) => { h.seriesRows[1][1] = invalid; });
  }
  for (const column of [2, 3]) {
    for (const invalid of [null, '0', NaN, Infinity]) {
      rejectsHistory((h) => { h.seriesRows[1][column] = invalid; });
    }
  }
});

test('eight-decimal history rounding is accepted without replacing the original scatter values', () => {
  const { history, summary, scatter } = fixture();
  history.seriesRows[1][2] += 4.9e-9;
  history.seriesRows[1][3] -= 4.9e-9;
  const result = api.parseFearPrices(history, summary, scatter);
  assert.equal(result[0].return1d, -.01);
  assert.equal(result[0].rawFlowTrillion, -1);
  assert.equal(result[0].close, 5940);
  rejectsHistory((h) => { h.seriesRows[1][2] += 1e-6; });
  rejectsHistory((h) => { h.seriesRows[1][3] += 1e-6; });
});

test('a plausible positive price with the wrong daily change is rejected using the preceding close', () => {
  rejectsHistory((h) => { h.seriesRows[1][1] += 10; });
  rejectsHistory((h) => { h.seriesRows[0][1] += 10; });
});

test('both plots classify from the current raw fit, independently of historical and robust states', () => {
  const { scatter } = fixture();
  assert.equal(scatter.points[0].state, 'extreme_greed', 'the fixture deliberately disagrees with the current fit');
  assert.equal(api.fearPointState(scatter, scatter.points[0]), 'extreme_fear');
  assert.equal(api.fearPointState(scatter, scatter.points[10]), 'neutral');
  assert.equal(api.fearPointState(scatter, scatter.points.at(-1)), 'extreme_greed');
  const before = JSON.stringify(scatter);
  freeze(scatter);
  api.fearPointState(scatter, scatter.points[0]);
  assert.equal(JSON.stringify(scatter), before);
  assert.equal(api.fearPointState({ ...scatter, boundaries: null }, scatter.points[0]), null);
});

test('published residual boundary equality follows inclusive transitions despite rounding', () => {
  const { scatter } = fixture();
  const checks = [
    ['extremeFearUpper', 'extreme_fear', 'fear'],
    ['fearUpper', 'fear', 'neutral'],
    ['greedLower', 'neutral', 'greed'],
    ['extremeGreedLower', 'greed', 'extreme_greed'],
  ];
  for (const [key, below, atOrAbove] of checks) {
    const boundary = scatter.boundaries[key];
    const row = (delta) => ({ date: '2026-06-01', return1d: .01,
      rawFlowTrillion: scatter.alpha + scatter.beta * .01 + boundary + delta,
      state: 'neutral', role: 'training' });
    assert.equal(api.fearPointState(scatter, row(-1e-6)), below, `${key}: genuinely below`);
    assert.equal(api.fearPointState(scatter, row(-2e-9)), atOrAbove, `${key}: rounded equality from below`);
    assert.equal(api.fearPointState(scatter, row(0)), atOrAbove, `${key}: exact equality`);
    assert.equal(api.fearPointState(scatter, row(2e-9)), atOrAbove, `${key}: rounded equality from above`);
    assert.equal(api.fearPointState(scatter, row(1e-6)), atOrAbove, `${key}: genuinely above`);
  }
});

test('price failures preserve a valid scatter and the original project summary', () => {
  const { summary, dashboard, history } = fixture();
  const good = api.parseFearPanel({ summary, dashboard, history });
  assert.equal(good.scatter.pricePoints.length, 21);
  assert.equal(good.priceError, undefined);
  history.generatedAt = '2026-06-22T12:00:00Z';
  const bad = api.parseFearPanel({ summary, dashboard, history });
  assert.equal(bad.entityPresent, true);
  assert.equal(bad.current.sentimentPercentile, 90);
  assert.equal(bad.scatter.points.length, 21);
  assert.ok(!bad.scatter.pricePoints?.length);
  assert.equal(typeof bad.priceError, 'string');
  assert.ok(bad.priceError.length > 0);
  assert.equal(bad.scatterError, undefined);
  assert.equal(api.visibleHealthLabel({ mode: 'live', summary: bad }), '차트 확인 필요');
});

test('price geometry retains every matched date within the mobile and desktop plot', () => {
  const { history, summary, scatter } = fixture();
  const points = api.parseFearPrices(history, summary, scatter);
  const before = JSON.stringify(points);
  freeze(points);
  for (const width of [300, 390, 640]) {
    const geometry = api.fearPriceGeometry(points, width);
    assert.equal(geometry.points.length, points.length);
    assert.ok(geometry.yTicks.length >= 2);
    assert.ok(geometry.dateTicks.length >= 2);
    for (let index = 0; index < geometry.points.length; index += 1) {
      const point = geometry.points[index];
      assert.equal(point.row.date, points[index].date);
      assert.equal(point.y, geometry.y(points[index].close));
      assert.ok(point.x >= geometry.p.l && point.x <= geometry.w - geometry.p.r);
      assert.ok(point.y >= geometry.p.t && point.y <= geometry.h - geometry.p.b);
      if (index) assert.ok(point.x > geometry.points[index - 1].x);
    }
    assert.ok(geometry.yTicks.every((value) => Number.isFinite(value) && value > 1000));
  }
  assert.equal(JSON.stringify(points), before);
});
