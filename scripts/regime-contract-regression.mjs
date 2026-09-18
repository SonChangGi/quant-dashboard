import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const root = new URL('../', import.meta.url);
const fixture = JSON.parse(readFileSync(new URL('fixtures/regime-v5-public.json', import.meta.url), 'utf8'));
const context = vm.createContext({ console, URL });
vm.runInContext(readFileSync(new URL('assets/app.js', root), 'utf8'), context, { filename: 'assets/app.js' });
const api = context.__QUANT_DASHBOARD_TESTS__;
const adapter = api.PANEL_ADAPTERS.regime;
const plain = (value) => JSON.parse(JSON.stringify(value));
const clone = (value) => structuredClone(value);
const hash = (bytes) => createHash('sha256').update(bytes).digest('hex');

// Keep the public-record projection independent of the production parser.
const pick = (value, keys) => Object.fromEntries(keys.filter((key) => Object.hasOwn(value, key)).map((key) => [key, value[key]]));
function compactPayload(payload, week = [...payload.weekly].sort((a, b) => a.date.localeCompare(b.date)).at(-1)) {
  return {
    meta: pick(payload.meta, ['mode', 'result_version', 'generated_at', 'generation_id', 'data_as_of', 'status']),
    sources: payload.sources.map((source) => pick(source, ['id', 'license_class'])),
    weekly: [{
      date: week.date,
      current: week.current,
      next_week: pick(week.next_week, ['state', 'probabilities', 'confidence', 'date']),
      transition_probability: week.transition_probability,
      transition_risk: Object.fromEntries(['1w', '4w', '13w'].map((horizon) => [horizon,
        pick(week.transition_risk[horizon], ['probability', 'target_end'])])),
    }],
  };
}

function legacyPayload(version, mode = 'live') {
  return {
    meta: { mode, result_version: `weekly-regime-result-${version}`, generated_at: '2026-08-08T00:00:00Z', data_as_of: '2026-08-07T20:00:00Z', status: 'ok' },
    sources: mode === 'live' ? [
      { id: 'alpha_vantage', license_class: 'private_noncommercial' },
      { id: 'alfred', license_class: 'user_confirmed_ml_storage_derived' },
    ] : [
      { id: 'synthetic_market_fixture', license_class: 'synthetic_fixture' },
      { id: 'synthetic_macro_fixture', license_class: 'synthetic_fixture' },
    ],
    weekly: [{
      date: '2026-08-07',
      current: { state: 'risk_on', probabilities: { risk_on: .6, transition: .3, risk_off: .1 }, confidence: .6 },
      next_week: { state: 'transition', probabilities: { risk_on: .3, transition: .6, risk_off: .1 }, confidence: .6, date: '2026-08-14' },
      transition_probability: .7,
      transition_risk: {
        '1w': { probability: .7, target_end: '2026-08-14' },
        '4w': { probability: .8, target_end: '2026-09-04' },
        '13w': { probability: .9, target_end: '2026-11-06' },
      },
    }],
  };
}

test('compact fixture records immutable full/core source identities and exact v5 fields', () => {
  assert.equal(fixture.provenance.snapshots.full.url, 'https://sonchanggi.github.io/regime/data/regime-results.json');
  assert.equal(fixture.provenance.snapshots.core.url, 'https://sonchanggi.github.io/regime/data/regime-core.json');
  assert.equal(fixture.core.source_payload_sha256, fixture.provenance.snapshots.full.sha256);
  for (const snapshot of Object.values(fixture.provenance.snapshots)) assert.match(snapshot.sha256, /^[a-f0-9]{64}$/);
  assert.ok(readFileSync(new URL('fixtures/regime-v5-public.json', import.meta.url)).length < 12000);
  assert.deepEqual(fixture.full, fixture.core.payload);
  assert.equal(fixture.full.weekly[0].current.primary_membership, .56947738);
  assert.equal(fixture.full.weekly[0].next_week.confidence, .80730902);
  assert.equal(fixture.full.weekly[0].current.probabilities, undefined);
});

test('actual v5 full and core/2 projections produce identical summaries without mutation', () => {
  const before = JSON.stringify(fixture);
  const raw = plain(api.parseRegime(fixture.full));
  const core = plain(api.parseRegime(fixture.core));
  assert.deepEqual(core, raw);
  assert.equal(raw.publicPayloadValid, true);
  assert.equal(raw.dataAsOf, '2026-09-04');
  assert.equal(raw.nextDate, '2026-09-11');
  assert.equal(raw.resultVersion, 'weekly-regime-result-v5');
  assert.equal(raw.currentConfidence, .56947738);
  assert.equal(raw.currentMeasureLabel, '소속도');
  assert.equal(raw.nextConfidence, .80730902);
  assert.equal(raw.meta.sourceCount, 3);
  assert.equal(raw.meta.statusState, 'degraded');
  assert.equal(JSON.stringify(fixture), before);
  for (const payload of [fixture.full, fixture.core]) {
    const parsed = api.parsePanelSafely(adapter, { summary: payload });
    assert.equal(parsed.ok, true);
    assert.equal(parsed.error, null);
    assert.equal(adapter.hasUsableData(parsed.data), true);
    const { trend, trendError, ...originalSummary } = plain(parsed.data);
    assert.deepEqual(originalSummary, raw);
  }
});

test('core/1 uses the same v5 summary contract', () => {
  const core = clone(fixture.core);
  core.schema_version = 'regime-dashboard-core/1';
  delete core.history_sidecars;
  assert.deepEqual(plain(api.parseRegime(core)), plain(api.parseRegime(fixture.full)));
});

test('hysteresis-selected v5 current state need not have the largest membership', () => {
  const current = fixture.historical.weekly[0].current;
  assert.equal(current.state, 'risk_off');
  assert.equal(current.primary_membership, .39901948);
  assert.equal(current.memberships.transition, .5485768);
  const parsed = api.parseRegime(fixture.historical);
  assert.equal(parsed.currentState, 'risk_off');
  assert.equal(parsed.currentConfidence, current.primary_membership);
  assert.equal(parsed.dataAsOf, '2023-03-03');
});

for (const version of ['v3', 'v4']) {
  for (const mode of ['demo', 'live']) {
    test(`${version} ${mode} probability-based current state remains supported`, () => {
      const parsed = api.parsePanelSafely(adapter, { summary: legacyPayload(version, mode) });
      assert.equal(parsed.ok, true);
      assert.equal(parsed.data.currentConfidence, .6);
      assert.equal(parsed.data.currentMeasureLabel, '확률');
      assert.equal(parsed.data.transitionRisk13w, .9);
      assert.equal(parsed.data.meta.sourceCount, 2);
      assert.equal(parsed.data.meta.statusState, mode === 'demo' ? 'demo' : 'ok');
    });
  }
}

test('source ordering is immaterial but its exact identities and licenses are preserved', () => {
  const reordered = clone(fixture.full);
  reordered.sources.reverse();
  assert.deepEqual(plain(api.parseRegime(reordered)), plain(api.parseRegime(fixture.full)));
});

test('panel adapter starts from the public core and enriches verified history', () => {
  assert.deepEqual(plain(adapter.sourceUrls), { summary: fixture.provenance.snapshots.core.url });
  assert.equal(adapter.primarySourceKey, 'summary');
  assert.equal(typeof adapter.enrichSources, 'function');
});

test('v5 chart labels, watchlist and briefing identify current membership separately from next probability', () => {
  const summary = api.parseRegime(fixture.full);
  const measure = api.parseRegimeTrend(fixture.full).currentMeasureLabel;
  const watchlist = api.entitySummaryLine('regime', summary.entities[0]);
  const briefing = api.briefingItemForRecord({ project: { id: 'regime' }, summary });
  const forecastMarker = `${summary.nextDate} 예측`;
  assert.ok(watchlist.includes(forecastMarker));
  assert.ok(briefing.title.includes(forecastMarker));
  for (const text of [measure, watchlist.split(forecastMarker)[0], briefing.title.split(forecastMarker)[0]]) {
    assert.match(text, /소속도/);
    assert.doesNotMatch(text, /확률/);
  }
  assert.match(watchlist.split(forecastMarker)[1], /확률/);
  assert.match(briefing.title.split(forecastMarker)[1], /확률/);
  assert.equal(api.parseRegimeTrend(fixture.full).rows.at(-1).nextDate, '2026-09-11');
  assert.equal(api.parseRegimeTrend(legacyPayload('v4')).currentMeasureLabel, '확률');
});

const rawFailures = [
  ['unknown result version', (p) => { p.meta.result_version = 'weekly-regime-result-v6'; }],
  ['missing provider', (p) => { p.sources.pop(); }],
  ['duplicate provider', (p) => { p.sources[2] = clone(p.sources[0]); }],
  ['unrecognized provider', (p) => { p.sources[2].id = 'other_provider'; }],
  ['extra provider', (p) => { p.sources.push({ id: 'other_provider', license_class: 'public' }); }],
  ...['alpha_vantage', 'alfred', 'frb_h10'].map((id) => [`altered ${id} license`, (p) => { p.sources.find((source) => source.id === id).license_class = 'synthetic_fixture'; }]),
  ['missing sources', (p) => { delete p.sources; }],
  ['unrecognized mode', (p) => { p.meta.mode = 'unknown'; }],
  ['legacy current shape in v5', (p) => { p.weekly[0].current = clone(legacyPayload('v4').weekly[0].current); }],
  ['missing membership', (p) => { delete p.weekly[0].current.memberships.risk_off; }],
  ['extra membership', (p) => { p.weekly[0].current.memberships.unknown = 0; }],
  ['membership string', (p) => { p.weekly[0].current.memberships.risk_on = '.56947738'; }],
  ['membership outside range', (p) => { p.weekly[0].current.memberships.risk_on = -1; }],
  ['membership sum', (p) => { p.weekly[0].current.memberships.risk_on = .5; }],
  ['primary membership mismatch', (p) => { p.weekly[0].current.primary_membership = .5; }],
  ['current state mismatch', (p) => { p.weekly[0].current.state = 'transition'; }],
  ['unknown current membership method', (p) => { p.weekly[0].current.method = 'posterior_probability'; }],
  ['next state is not probability maximum', (p) => { p.weekly[0].next_week.state = 'transition'; p.weekly[0].next_week.confidence = p.weekly[0].next_week.probabilities.transition; }],
  ['next confidence mismatch', (p) => { p.weekly[0].next_week.confidence = .5; }],
  ['next probability sum', (p) => { p.weekly[0].next_week.probabilities.risk_on = .5; }],
  ['nonfinite next probability', (p) => { p.weekly[0].next_week.probabilities.risk_on = NaN; }],
  ['next probability outside range', (p) => { p.weekly[0].next_week.probabilities.risk_off = -.1; }],
  ['empty weekly', (p) => { p.weekly = []; }],
  ['invalid observation date', (p) => { p.weekly[0].date = '2026-02-30'; }],
  ['missing generated timestamp', (p) => { delete p.meta.generated_at; }],
  ['observation cutoff mismatch', (p) => { p.meta.data_as_of = '2026-08-28T20:00:00Z'; }],
  ['non-forward next date', (p) => { p.weekly[0].next_week.date = p.weekly[0].date; }],
  ['next date skips a week', (p) => { p.weekly[0].next_week.date = '2026-09-18'; p.weekly[0].transition_risk['1w'].target_end = '2026-09-18'; }],
  ['one-week target mismatch', (p) => { p.weekly[0].transition_risk['1w'].target_end = '2026-09-18'; }],
  ['four-week target is only three weeks ahead', (p) => { p.weekly[0].transition_risk['4w'].target_end = '2026-09-25'; }],
  ['thirteen-week target is only twelve weeks ahead', (p) => { p.weekly[0].transition_risk['13w'].target_end = '2026-11-27'; }],
  ['nonmonotone departure risks', (p) => { p.weekly[0].transition_risk['13w'].probability = .2; }],
  ['inconsistent departure probability', (p) => { p.weekly[0].transition_probability = .25; }],
  ['inconsistent one-week risk', (p) => { p.weekly[0].transition_risk['1w'].probability = .25; }],
];

const coreFailures = [
  ['unknown envelope version', (p) => { p.schema_version = 'regime-dashboard-core/3'; }],
  ['unknown envelope identity', (p) => { p.schema_version = 'other-envelope/1'; }],
  ['missing envelope version', (p) => { delete p.schema_version; }],
  ['missing nested payload', (p) => { delete p.payload; }],
  ['nested payload is not an object', (p) => { p.payload = []; }],
  ['missing generation', (p) => { delete p.generation_id; }],
  ['empty generation', (p) => { p.generation_id = ''; p.payload.meta.generation_id = ''; }],
  ['blank generation', (p) => { p.generation_id = ' '; p.payload.meta.generation_id = ' '; }],
  ['generation mismatch', (p) => { p.generation_id = 'other-generation'; }],
  ['missing payload generation', (p) => { delete p.payload.meta.generation_id; }],
  ['missing source hash', (p) => { delete p.source_payload_sha256; }],
  ['uppercase source hash', (p) => { p.source_payload_sha256 = p.source_payload_sha256.toUpperCase(); }],
  ['short source hash', (p) => { p.source_payload_sha256 = 'a'.repeat(63); }],
  ['long source hash', (p) => { p.source_payload_sha256 = 'a'.repeat(65); }],
  ['nonhex source hash', (p) => { p.source_payload_sha256 = 'g'.repeat(64); }],
  ...['v3', 'v4'].map((version) => [`non-v5 ${version} in core`, (p) => { p.payload = legacyPayload(version); p.payload.meta.generation_id = p.generation_id; }]),
];

for (const [kind, initial, failures] of [['raw v5', fixture.full, rawFailures], ['core', fixture.core, coreFailures]]) {
  for (const [label, mutate] of failures) {
    test(`${kind} rejects ${label} instead of claiming usable data`, () => {
      const value = clone(initial);
      mutate(value);
      assert.throws(() => api.parseRegime(value));
      const parsed = api.parsePanelSafely(adapter, { summary: value });
      assert.equal(parsed.ok, false);
      assert.equal(parsed.data, null);
      assert.match(parsed.error, /Payload parse failed/);
    });
  }
}

for (const version of ['v3', 'v4']) {
  test(`${version} cannot acquire a v5 provider or an altered legacy license`, () => {
    const extra = legacyPayload(version);
    extra.sources.push(clone(fixture.full.sources[2]));
    assert.throws(() => api.parseRegime(extra));
    const altered = legacyPayload(version);
    altered.sources[1].license_class = 'public_domain';
    assert.throws(() => api.parseRegime(altered));
  });
}

// Optional local evidence replay: CI uses only the 7 KB checked-in projection.
const fullPath = process.env.REGIME_PUBLIC_FULL_PATH;
const corePath = process.env.REGIME_PUBLIC_CORE_PATH;
test('immutable original full/core files yield the exact compact-fixture summaries', {
  skip: !fullPath && !corePath ? 'Set REGIME_PUBLIC_FULL_PATH and REGIME_PUBLIC_CORE_PATH to replay the frozen originals.' : false,
}, () => {
  assert.ok(fullPath && corePath, 'Both original paths are required');
  const before = { full: readFileSync(fullPath), core: readFileSync(corePath) };
  const documents = Object.fromEntries(Object.entries(before).map(([key, raw]) => [key, JSON.parse(raw)]));
  for (const [key, raw] of Object.entries(before)) {
    assert.equal(hash(raw), fixture.provenance.snapshots[key].sha256);
    assert.equal(raw.length, fixture.provenance.snapshots[key].bytes);
  }
  assert.deepEqual(compactPayload(documents.full), fixture.full);
  assert.deepEqual({ ...documents.core, payload: compactPayload(documents.core.payload) }, fixture.core);
  const full = plain(api.parseRegime(documents.full));
  const core = plain(api.parseRegime(documents.core));
  assert.deepEqual(full, core);
  assert.deepEqual(full, plain(api.parseRegime(fixture.full)));
  assert.equal(hash(readFileSync(fullPath)), hash(before.full));
  assert.equal(hash(readFileSync(corePath)), hash(before.core));
});
