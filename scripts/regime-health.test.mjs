import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import { operationalFindingsFor } from './public-health-policy.mjs';

const fixture = JSON.parse(readFileSync(new URL('fixtures/regime-health-current.json', import.meta.url), 'utf8'));
const priorFixture = JSON.parse(readFileSync(new URL('fixtures/regime-v5-public.json', import.meta.url), 'utf8'));
const context = vm.createContext({ console, URL });
vm.runInContext(readFileSync(new URL('../assets/app.js', import.meta.url), 'utf8'), context);
const api = context.__QUANT_DASHBOARD_TESTS__;
const plain = (value) => JSON.parse(JSON.stringify(value));
const clone = () => structuredClone(fixture.payload);
const assess = (payload) => api.regimeHealthAssessment(payload, payload.weekly.at(-1));
const now = Date.parse('2026-10-19T12:00:00Z');
const record = (summary) => ({ project: { id: 'regime' }, mode: 'live', generatedAt: summary.generatedAt, summary });

test('current Regime fixture retains public provenance and the actual diagnostic denominator', () => {
  assert.equal(fixture.provenance.url, 'https://sonchanggi.github.io/regime/data/regime-core.json');
  assert.match(fixture.provenance.sha256, /^[a-f0-9]{64}$/);
  assert.match(fixture.provenance.sourcePayloadSha256, /^[a-f0-9]{64}$/);
  assert.ok(Number.isFinite(Date.parse(fixture.provenance.retrievedAt)));
  assert.equal(fixture.payload.meta.generation_id, fixture.provenance.generationId);
  const diagnostic = fixture.payload.model.early_warning_health;
  assert.equal(diagnostic.evaluation_split, 'retrospective_diagnostic');
  assert.equal(diagnostic.event_count, 41);
  assert.equal(diagnostic.on_time_departure_count, 3);
  assert.ok(Math.abs(diagnostic.on_time_recall - 3 / 41) < 1e-8);
  assert.equal(fixture.payload.meta.status, 'degraded');
});

test('a current healthy source set with low transition recall is identified as model quality', () => {
  const payload = clone();
  const before = JSON.stringify(payload);
  const result = assess(payload);
  assert.equal(result.kind, 'model_quality');
  assert.equal(result.label, '조기경보 성능 주의');
  assert.match(result.detail, /41/);
  assert.match(result.detail, /3/);
  assert.match(result.detail, /7\.3%/);
  assert.equal(JSON.stringify(payload), before);
});

test('provenance notices do not create or remove the model diagnostic classification', () => {
  const payload = clone();
  const original = plain(assess(payload));
  payload.meta.warnings = [];
  assert.deepEqual(plain(assess(payload)), original);
  payload.meta.status = 'ok';
  payload.model.model_health = { status: 'ok', reasons: [] };
  payload.meta.warnings = structuredClone(fixture.payload.meta.warnings);
  assert.equal(assess(payload), null);
});

const nonModelOnlyCases = [
  ['provider failure', (p) => { p.sources[0].status = 'degraded'; }],
  ['provider issue', (p) => { p.sources[1].issues = ['missing_release']; }],
  ['provider evidence absent', (p) => { delete p.sources[0].status; }],
  ['no providers', (p) => { p.sources = []; }, false],
  ['unhealthy latest week', (p) => { p.weekly[0].health.status = 'degraded'; }],
  ['missing latest week health', (p) => { delete p.weekly[0].health; }],
  ['stale metadata', (p) => { p.meta.freshness.status = 'stale'; }],
  ['missing freshness evidence', (p) => { delete p.meta.freshness; }],
  ['blocked upstream', (p) => { p.meta.status = 'blocked'; }],
  ['unknown aggregate reason', (p) => { p.model.model_health.reasons.push('provider_degraded'); }],
  ['missing aggregate health', (p) => { delete p.model.model_health; }],
  ['probability quality warning', (p) => { p.model.probability_health.status = 'review_due'; }],
  ['holdout quality warning', (p) => { p.model.holdout_diagnostic.status = 'weak_generalization'; }],
  ['missing early-warning evidence', (p) => { delete p.model.early_warning_health; }],
  ['inconsistent early-warning state', (p) => { p.model.early_warning_health.status = 'ok'; }],
  ['inconsistent early-warning reason', (p) => { p.model.early_warning_health.reasons = ['unknown']; }],
  ['inconsistent recall', (p) => { p.model.early_warning_health.on_time_recall = 0.15; }],
  ['negative on-time count', (p) => { p.model.early_warning_health.on_time_departure_count = -1; }],
  ['fractional event count', (p) => { p.model.early_warning_health.event_count = 41.5; }],
  ['insufficient event count', (p) => {
    Object.assign(p.model.early_warning_health, { event_count: 5, on_time_departure_count: 0, on_time_recall: 0 });
  }],
  ['recall does not satisfy the warning threshold', (p) => {
    Object.assign(p.model.early_warning_health, { event_count: 20, on_time_departure_count: 4, on_time_recall: 0.20 });
  }],
];
for (const [name, change, parseable = true] of nonModelOnlyCases) {
  test(`Regime preserves the general warning for ${name}`, () => {
    const payload = clone();
    change(payload);
    assert.equal(assess(payload), null);
    if (!parseable) {
      assert.throws(() => api.parseRegime(payload), /sources/);
      return;
    }
    const parsed = api.parseRegime(payload);
    assert.notEqual(parsed.meta.statusState, 'ok');
    assert.notEqual(api.healthLabel(record(parsed), now), '조기경보 성능 주의');
  });
}

test('current public full and core records retain all displayed numerical results and the warning', () => {
  const payload = clone();
  const before = JSON.stringify(payload);
  const core = {
    schema_version: 'regime-dashboard-core/2',
    generation_id: fixture.provenance.generationId,
    source_payload_sha256: fixture.provenance.sourcePayloadSha256,
    payload,
  };
  const parsed = api.parseRegime(payload);
  assert.deepEqual(plain(api.parseRegime(core)), plain(parsed));
  assert.equal(parsed.dataAsOf, '2026-10-16');
  assert.equal(parsed.nextDate, '2026-10-23');
  assert.equal(parsed.currentState, 'transition');
  assert.equal(parsed.currentConfidence, .57230258);
  assert.equal(parsed.currentMeasureLabel, '소속도');
  assert.equal(parsed.nextState, 'transition');
  assert.equal(parsed.nextConfidence, .68287495);
  assert.equal(parsed.transitionRisk1w, .31712505);
  assert.equal(parsed.transitionRisk4w, .55877612);
  assert.equal(parsed.transitionRisk13w, .89832275);
  assert.equal(parsed.meta.statusState, 'degraded');
  assert.equal(api.healthLabel(record(parsed), now), '조기경보 성능 주의');
  assert.equal(JSON.stringify(payload), before);
});

test('legacy compact Regime records without diagnostic evidence retain their existing degraded state', () => {
  const before = JSON.stringify(priorFixture);
  assert.equal(assess(priorFixture.full), null);
  const parsed = api.parseRegime(priorFixture.full);
  assert.equal(parsed.meta.statusState, 'degraded');
  assert.equal(parsed.currentConfidence, .56947738);
  assert.equal(parsed.nextConfidence, .80730902);
  assert.equal(JSON.stringify(priorFixture), before);
});


test('monitor retains model-quality warning and does not swallow chart failures', () => {
  const parsed = api.parseRegime(clone());
  const findings = operationalFindingsFor('regime', parsed);
  assert.equal(findings.length, 1);
  assert.equal(findings[0].category, 'model_quality');
  assert.equal(findings[0].upstreamState, 'degraded');
  assert.deepEqual(plain(findings[0].upstreamReasons), ['low_transition_recall']);
  assert.ok(operationalFindingsFor('regime', { ...parsed, trendError: 'invalid history' }).every((f) => f.category === 'operation'));
});

test('blocked and error status override live-derived mode labels in UI and monitor', () => {
  for (const state of ['blocked', 'error']) {
    const payload = clone();
    payload.meta.status = state;
    const parsed = api.parseRegime(payload);
    assert.equal(api.healthLabel(record(parsed), now), '데이터 확인 필요');
    assert.equal(api.healthTone(record(parsed), now), 'warn');
    assert.ok(operationalFindingsFor('regime', parsed).some((f) => f.message.includes(state)));
  }
});
