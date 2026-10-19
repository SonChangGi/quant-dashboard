import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
import { operationalFindingsFor } from './public-health-policy.mjs';

const context = vm.createContext({ console, URL });
vm.runInContext(readFileSync('assets/app.js', 'utf8'), context);
const api = context.__QUANT_DASHBOARD_TESTS__;
const fixture = JSON.parse(readFileSync('scripts/fixtures/fear-health-current.json', 'utf8'));
const fresh = () => structuredClone(fixture);
const assess = ({ summary, dashboard }) => api.fearHealthAssessment(summary, dashboard);
const rejectEdits = (edits) => {
  for (const [description, edit] of edits) {
    const data = fresh();
    edit(data);
    assert.equal(assess(data), null, description);
  }
};

test('published current Fear data retains all historical repairs as provenance, without mutating source status', () => {
  const data = fresh();
  const before = JSON.stringify(data);
  const result = assess(data);
  assert.equal(result.kind, 'provenance');
  assert.equal(result.label, '과거 보정 포함');
  assert.ok(result.detail.length > 0);
  assert.equal(data.summary.status.sourceFreshnessPassed, true);
  for (const check of Object.values(data.dashboard.crosschecks.etf)) {
    assert.equal(check.historyReconciliation.filledCount, 29);
    assert.equal(check.historyReconciliation.currentRunFilledCount, 0);
    assert.equal(check.historyReconciliation.unresolvedCount, 0);
  }
  assert.equal(JSON.stringify(data), before);
  assert.equal(data.summary.status.state, 'degraded');
});

test('verified authenticated fallback without repaired history has a distinct source label', () => {
  const data = fresh();
  const reasons = ['krx_open_api_target_session_lag', 'stock_crosscheck_authenticated_pykrx_fallback'];
  data.summary.status.degradedReasons = [...reasons];
  data.dashboard.status.degradedReasons = [...reasons];
  for (const check of Object.values(data.dashboard.crosschecks.etf)) {
    Object.assign(check.historyReconciliation, {
      source: 'yfinance_adjusted_checked_against_krx_calendar', filledCount: 0,
      inheritedFilledCount: 0, currentRunFilledCount: 0,
    });
  }
  assert.equal(assess(data).label, '대체 출처 확인');
});

test('mixed publications and unavailable source status cannot be downgraded to provenance', () => {
  rejectEdits([
    ['different observation', (d) => { d.dashboard.dataAsOf = '2026-10-16'; }],
    ['different generation', (d) => { d.dashboard.generatedAt = '2026-10-19T11:31:00Z'; }],
    ['missing generation', (d) => { delete d.dashboard.generatedAt; }],
    ['unavailable producer', (d) => { d.summary.status.state = 'unavailable'; }],
    ['unavailable dashboard', (d) => { d.dashboard.status.state = 'unavailable'; }],
  ]);
});

test('unknown, mismatched or absent reasons retain the ordinary warning path', () => {
  rejectEdits([
    ['unknown failure', (d) => { d.summary.status.degradedReasons.push('provider_request_failed'); d.dashboard.status.degradedReasons.push('provider_request_failed'); }],
    ['reason mismatch', (d) => { d.dashboard.status.degradedReasons.pop(); }],
    ['no reasons', (d) => { d.summary.status.degradedReasons = []; d.dashboard.status.degradedReasons = []; }],
    ['unknown repaired instrument', (d) => { d.summary.status.degradedReasons.push('adjusted_history_gap_reconciled_UNKNOWN'); d.dashboard.status.degradedReasons.push('adjusted_history_gap_reconciled_UNKNOWN'); }],
  ]);
});

test('core missingness, source coverage and stale-session failures remain warnings', () => {
  rejectEdits([
    ['quality not ok', (d) => { d.dashboard.quality.state = 'degraded'; }],
    ['quality issue', (d) => { d.dashboard.quality.issues.push('source_date_gaps'); }],
    ['date gap', (d) => { d.dashboard.quality.sourceGapCount = 1; }],
    ['incomplete source', (d) => { d.dashboard.quality.sourceCompleteness = 0.99; }],
    ['session coverage failed', (d) => { d.dashboard.quality.sourceSessionCoveragePassed = false; }],
    ['source freshness failed', (d) => { d.dashboard.quality.sourceFreshnessPassed = false; }],
    ['producer freshness failed', (d) => { d.summary.status.sourceFreshnessPassed = false; }],
    ['new expected date', (d) => { d.summary.status.expectedDataAsOf = '2026-10-20'; }],
    ['mismatched quality cutoff', (d) => { d.dashboard.quality.expectedAsOf = '2026-10-20'; }],
  ]);
});

test('every current KOSPI, ETF and stock crosscheck is required and must match its target session', () => {
  const paths = [['kospi'], ...Object.keys(fixture.dashboard.crosschecks.etf).map((t) => ['etf', t]), ...Object.keys(fixture.dashboard.crosschecks.stock).map((t) => ['stock', t])];
  for (const path of paths) {
    const locate = (d) => path.reduce((value, key) => value[key], d.dashboard.crosschecks);
    rejectEdits([
      [`${path} mismatch`, (d) => { locate(d).state = 'mismatch'; }],
      [`${path} stale`, (d) => { locate(d).secondaryLatestDate = '2026-10-16'; }],
      [`${path} discrepancy`, (d) => { locate(d).relativeDifference = 0.01; }],
    ]);
  }
  rejectEdits([
    ['missing stock evidence', (d) => { delete d.dashboard.crosschecks.stock['005930']; }],
    ['historical gating evidence absent', (d) => { delete d.dashboard.crosschecks.etf['069500'].historicalAnchorGatesPublication; }],
    ['historical gating evidence invalid', (d) => { d.dashboard.crosschecks.etf['069500'].historicalAnchorGatesPublication = 'false'; }],
    ['historical failure that gates publication', (d) => { d.dashboard.crosschecks.etf['069500'].historicalAnchorGatesPublication = true; }],
  ]);
});

test('unresolved or unproven historical repairs never receive a reassuring provenance label', () => {
  rejectEdits([
    ['missing reconciliation', (d) => { delete d.dashboard.crosschecks.etf['069500'].historyReconciliation; }],
    ['unavailable reconciliation', (d) => { d.dashboard.crosschecks.etf['069500'].historyReconciliation.state = 'unavailable'; }],
    ['unresolved row', (d) => { d.dashboard.crosschecks.etf['069500'].historyReconciliation.unresolvedCount = 1; }],
    ['missing row', (d) => { d.dashboard.crosschecks.etf['069500'].historyReconciliation.missingCount = 1; }],
    ['no fill evidence', (d) => { d.dashboard.crosschecks.etf['069500'].historyReconciliation.filledCount = 0; }],
    ['unknown fill provenance', (d) => { d.dashboard.crosschecks.etf['069500'].historyReconciliation.source = 'unknown'; }],
  ]);
});

test('fallback classification requires the authenticated KRX source identity', () => {
  rejectEdits([
    ['source absent', (d) => { d.summary.sources = []; }],
    ['fallback unconfirmed', (d) => { d.summary.sources.find((s) => s.id === 'krx').mode = 'unknown'; }],
  ]);
});

test('current data with historical repair limitations still has a warning tone, never a clean bill of health', () => {
  const data = fresh();
  const result = assess(data);
  assert.equal(result.kind, 'provenance');
  const record = {
    project: { id: 'fearngreed' }, mode: 'live', dataAsOf: data.summary.dataAsOf,
    generatedAt: data.summary.generatedAt,
    summary: { dataAsOf: data.summary.dataAsOf, generatedAt: data.summary.generatedAt,
      meta: { statusState: 'degraded', expectedFreshnessDays: 3 }, healthAssessment: result },
  };
  assert.equal(api.healthTone(record, Date.parse('2026-10-19T12:00:00Z')), 'warn');
  assert.equal(api.healthLabel(record, Date.parse('2026-10-19T12:00:00Z')), '과거 보정 포함');
  assert.equal(api.healthLabel(record, Date.parse('2026-10-23T12:00:00Z')), '갱신 지연');
  record.summary.scatterError = 'fixture chart contract failed';
  assert.equal(api.healthLabel(record, Date.parse('2026-10-19T12:00:00Z')), '차트 확인 필요');
});


test('monitor keeps provenance as a warning with original reasons and rejects unknown or failed evidence', () => {
  const data = fresh();
  const summary = { meta: { statusState: 'degraded', degradedReasons: data.summary.status.degradedReasons },
    healthAssessment: assess(data) };
  const findings = operationalFindingsFor('fearngreed', summary);
  assert.equal(findings.length, 1);
  assert.equal(findings[0].category, 'provenance');
  assert.equal(findings[0].severity, 'transient');
  assert.equal(findings[0].upstreamState, 'degraded');
  assert.deepEqual(findings[0].upstreamReasons, data.summary.status.degradedReasons);
  for (const patch of [{ healthAssessment: null }, { scatterError: 'invalid scatter' }, { priceError: 'price mismatch' }]) {
    assert.ok(operationalFindingsFor('fearngreed', { ...summary, ...patch }).every((f) => f.category === 'operation'));
  }
  assert.ok(operationalFindingsFor('regime', summary).every((f) => f.category === 'operation'));
});
