import assert from 'node:assert/strict';
import test from 'node:test';

import {
  incidentIdentity,
  incidentState,
  normalizeIncidentMessage,
} from './public-health-incident.mjs';

test('age and date drift do not create a new incident identity', () => {
  assert.equal(
    normalizeIncidentMessage('port data is 13.3 days old on 2026-08-14; expected <= 5 days'),
    'port data is # days old on #date; expected <= 5 days',
  );
  const first = incidentState({
    findings: [{ project: 'port', category: 'freshness', severity: 'hard', message: 'port data is 13.3 days old' }],
  });
  const second = incidentState({
    findings: [{ project: 'port', category: 'freshness', severity: 'hard', message: 'port data is 14.3 days old' }],
  }, first);
  assert.equal(second.fingerprint, first.fingerprint);
  assert.equal(second.changed, false);
});

test('new hard category changes the incident fingerprint', () => {
  const first = incidentState({
    findings: [{ project: 'port', category: 'freshness', severity: 'hard', message: 'stale for 13 days' }],
  });
  const second = incidentState({
    findings: [{ project: 'port', category: 'contract', severity: 'hard', message: 'schema mismatch' }],
  }, first);
  assert.notEqual(second.fingerprint, first.fingerprint);
  assert.equal(second.changed, true);
});

test('transient findings do not enter the hard incident identity', () => {
  const report = {
    findings: [
      { project: 'fearngreed', category: 'operation', severity: 'transient', message: 'upstream degraded' },
      { project: 'port', category: 'freshness', severity: 'hard', message: 'stale' },
    ],
  };
  assert.deepEqual(incidentIdentity(report), [
    { project: 'port', category: 'freshness', message: 'stale', affectedProjects: [] },
  ]);
});

test('threshold and affected-project changes create a new incident identity', () => {
  const thresholdFive = incidentState({
    findings: [{ project: 'port', category: 'freshness', severity: 'hard', message: 'port data is 14 days old; expected <= 5 days' }],
  });
  const thresholdTen = incidentState({
    findings: [{ project: 'port', category: 'freshness', severity: 'hard', message: 'port data is 15 days old; expected <= 10 days' }],
  }, thresholdFive);
  assert.equal(thresholdTen.changed, true);

  const twoProjects = incidentState({
    findings: [{
      project: 'hub',
      category: 'observability',
      severity: 'hard',
      message: '2/8 public projects are unobservable; hard threshold is 2',
      affectedProjects: ['port', 'etf'],
    }],
  });
  const threeProjects = incidentState({
    findings: [{
      project: 'hub',
      category: 'observability',
      severity: 'hard',
      message: '3/8 public projects are unobservable; hard threshold is 2',
      affectedProjects: ['port', 'etf', 'fearngreed'],
    }],
  }, twoProjects);
  assert.equal(threeProjects.changed, true);
});

test('unknown previous-state contracts fail safe as a new incident', () => {
  const current = incidentState({
    findings: [{ project: 'port', category: 'freshness', severity: 'hard', message: 'stale' }],
  }, { schemaVersion: 99, contract: 'unknown', fingerprint: 'not-trusted' });
  assert.equal(current.previousFingerprint, '');
  assert.equal(current.changed, true);
});

test('resolution clears the fingerprint and is recorded as a change', () => {
  const previous = incidentState({
    findings: [{ project: 'port', category: 'freshness', severity: 'hard', message: 'stale' }],
  });
  const resolved = incidentState({ findings: [] }, previous);
  assert.equal(resolved.fingerprint, '');
  assert.equal(resolved.hardFindingCount, 0);
  assert.equal(resolved.changed, true);
});
