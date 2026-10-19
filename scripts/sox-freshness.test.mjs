import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const context = vm.createContext({ console, URL });
vm.runInContext(fs.readFileSync('assets/app.js', 'utf8'), context);
const api = context.__QUANT_DASHBOARD_TESTS__;
const time = (value) => Date.parse(value);
const record = (dataAsOf, generatedAt = '2026-10-16T22:00:00Z') => ({
  project: { id: 'sox' },
  mode: 'live',
  generatedAt,
  summary: {
    dataAsOf,
    generatedAt,
    meta: { statusState: 'ok', expectedFreshnessDays: 3 },
  },
});

// Fixed producer-contract examples: the new session becomes due at 06:30 KST,
// including after daylight-saving and early closes. These are not wall-clock tests.
test('SOX keeps Friday current through the weekend and Monday until the next collection cutoff', () => {
  for (const now of ['2026-10-18T12:00:00Z', '2026-10-19T12:00:00Z', '2026-10-19T21:29:59Z']) {
    assert.equal(api.latestExpectedSoxSession(time(now)), '2026-10-16', now);
    const current = record('2026-10-16');
    assert.equal(api.soxFreshnessAssessment(current, time(now)).state, 'current', now);
    assert.equal(api.isRecordStale(current, time(now)), false, now);
    assert.equal(api.healthLabel(current, time(now)), '정상', now);
  }
  const cutoff = time('2026-10-19T21:30:00Z');
  assert.equal(api.latestExpectedSoxSession(cutoff), '2026-10-19');
  const previous = record('2026-10-16');
  assert.equal(api.soxFreshnessAssessment(previous, cutoff).state, 'stale');
  assert.equal(api.isRecordStale(previous, cutoff), true);
  assert.equal(api.healthLabel(previous, cutoff), '갱신 지연');
  assert.equal(api.soxFreshnessAssessment(record('2026-10-19', '2026-10-19T21:30:00Z'), cutoff).state, 'current');
});

test('SOX session calendar handles market holidays and special closures without removing early-close sessions', () => {
  const examples = [
    ['2026-07-03', false], // Observed Independence Day.
    ['2026-07-02', true],
    ['2026-04-03', false], // Good Friday.
    ['2026-06-19', false], // Juneteenth.
    ['2021-06-18', true], // The exchange did not yet observe Juneteenth.
    ['2026-11-26', false], // Thanksgiving.
    ['2026-11-27', true], // Early close is still a trading session.
    ['2026-12-25', false],
    ['2026-10-17', false],
    ['2026-10-18', false],
    ['2021-12-31', true], // Saturday New Year does not close the previous Friday.
    ['2023-01-02', false], // Sunday New Year is observed on Monday.
    ['2025-01-09', false], // National day of mourning.
  ];
  for (const [day, expected] of examples) assert.equal(api.isUsEquitySession(day), expected, day);
});

test('SOX waits for the first post-holiday session cutoff instead of counting calendar days', () => {
  const before = time('2026-07-06T21:29:59Z');
  const after = time('2026-07-06T21:30:00Z');
  const thursday = record('2026-07-02', '2026-07-02T22:00:00Z');
  assert.equal(api.latestExpectedSoxSession(before), '2026-07-02');
  assert.equal(api.soxFreshnessAssessment(thursday, before).state, 'current');
  assert.equal(api.isRecordStale(thursday, before), false);
  assert.equal(api.latestExpectedSoxSession(after), '2026-07-06');
  assert.equal(api.soxFreshnessAssessment(thursday, after).state, 'stale');
  assert.equal(api.soxFreshnessAssessment(record('2026-07-06', '2026-07-06T21:30:00Z'), after).state, 'current');
  for (const [now, expected] of [
    ['2026-04-04T04:31:00Z', '2026-04-02'],
    ['2026-06-19T21:30:00Z', '2026-06-18'],
    ['2025-01-10T00:00:00Z', '2025-01-08'],
    ['2022-01-01T00:00:00Z', '2021-12-31'],
  ]) assert.equal(api.latestExpectedSoxSession(time(now)), expected, now);
});

test('SOX uses the same 06:30 KST readiness boundary across DST and early closes', () => {
  const examples = [
    ['2026-03-09T20:30:00Z', '2026-03-06'], // After the DST close, before the collection window.
    ['2026-03-09T21:29:59Z', '2026-03-06'],
    ['2026-03-09T21:30:00Z', '2026-03-09'],
    ['2026-11-02T21:15:00Z', '2026-10-30'], // After the standard-time close.
    ['2026-11-02T21:30:00Z', '2026-11-02'],
    ['2026-11-27T20:00:00Z', '2026-11-25'], // Friday early close after Thanksgiving.
    ['2026-11-27T21:30:00Z', '2026-11-27'],
  ];
  for (const [now, expected] of examples) assert.equal(api.latestExpectedSoxSession(time(now)), expected, now);
});

test('SOX reports a missed midweek session even with a newly generated snapshot', () => {
  const now = time('2026-10-21T12:00:00Z');
  const old = record('2026-10-19', '2026-10-21T11:00:00Z');
  const result = api.soxFreshnessAssessment(old, now);
  assert.equal(result.expectedSession, '2026-10-20');
  assert.equal(result.dataAsOf, '2026-10-19');
  assert.equal(result.state, 'stale');
  assert.ok(result.reason);
  assert.equal(api.isRecordStale(old, now), true);
  assert.equal(api.healthLabel(old, now), '갱신 지연');
  assert.equal(api.soxFreshnessAssessment(record('2026-10-20', '2026-10-20T22:00:00Z'), now).state, 'current');
});

test('SOX requires valid observation dates and never substitutes a fresh generation timestamp', () => {
  const now = time('2026-10-20T12:00:00Z');
  for (const value of [undefined, null, '', 'not-a-date', '2026-02-30', '2026-10-17', '2026-10-18', '2026-10-20']) {
    const invalid = record(value, '2026-10-20T11:00:00Z');
    const result = api.soxFreshnessAssessment(invalid, now);
    assert.equal(result.state, 'invalid', String(value));
    assert.ok(result.reason, String(value));
    assert.equal(api.isRecordStale(invalid, now), true, String(value));
    assert.equal(api.healthLabel(invalid, now), '기준일 확인 필요', String(value));
  }
  for (const value of ['', 'not-a-date', '2026-02-30']) assert.equal(api.isUsEquitySession(value), false, value);
});

test('SOX generation must exist, not be future, and satisfy the observation-specific production cutoff', () => {
  const now = time('2026-10-20T12:00:00Z');
  for (const generatedAt of ['', null, 'not-a-date', '2026-10-20T12:00:01Z']) {
    const invalid = record('2026-10-19', generatedAt);
    assert.equal(api.soxFreshnessAssessment(invalid, now).state, 'invalid', String(generatedAt));
    assert.equal(api.isRecordStale(invalid, now), true);
  }
  const missing = record('2026-10-19');
  delete missing.generatedAt;
  delete missing.summary.generatedAt;
  assert.equal(api.soxFreshnessAssessment(missing, now).state, 'invalid');
  const before = record('2026-10-19', '2026-10-19T21:29:59Z');
  assert.equal(api.soxFreshnessAssessment(before, now).state, 'stale');
  for (const generatedAt of ['2026-10-19T21:30:00Z', '2026-10-20T06:30:00+09:00']) {
    assert.equal(api.soxFreshnessAssessment(record('2026-10-19', generatedAt), now).state, 'current', generatedAt);
  }
});

test('SOX cannot bypass its session policy by increasing the legacy day allowance', () => {
  const now = time('2026-10-21T12:00:00Z');
  const old = record('2026-10-19', '2026-10-21T11:00:00Z');
  old.summary.meta.expectedFreshnessDays = 999;
  assert.equal(api.isRecordStale(old, now), true);
  const holiday = record('2026-07-02', '2026-07-02T22:00:00Z');
  holiday.summary.meta.expectedFreshnessDays = 0;
  assert.equal(api.isRecordStale(holiday, time('2026-07-06T12:00:00Z')), false);
});

test('other projects retain their existing elapsed-day freshness policies', () => {
  const other = record('2026-10-16', '2026-10-20T12:00:00Z');
  other.project.id = 'dram';
  assert.equal(api.isRecordStale(other, time('2026-10-19T00:00:00Z')), false);
  assert.equal(api.isRecordStale(other, time('2026-10-19T00:00:01Z')), true);
  other.summary.meta.expectedFreshnessDays = 10;
  other.project.id = 'regime';
  assert.equal(api.isRecordStale(other, time('2026-10-21T12:00:00Z')), false);
});

test('SOX rejects impossible timestamp dates instead of Date.parse normalization', () => {
  const now = time('2026-03-03T12:00:00Z');
  for (const generatedAt of ['2026-02-30T22:00:00Z', '2026-03-02T24:00:00Z', '2026-03-03T07:00:00']) {
    const result = api.soxFreshnessAssessment(record('2026-03-02', generatedAt), now);
    assert.equal(result.state, 'invalid', generatedAt);
    assert.equal(result.reason, 'invalid_generation');
  }
  assert.equal(api.soxFreshnessAssessment(record('2026-03-02', '2026-03-03T07:00:00+09:00'), now).state, 'current');
});
