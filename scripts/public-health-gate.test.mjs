import assert from 'node:assert/strict';
import test from 'node:test';

import { decideHealthGate } from './public-health-gate.mjs';

const hard = (category) => ({ project: 'example', category, severity: 'hard', message: 'failure' });
const report = (findings = []) => ({
  schemaVersion: 1,
  contract: 'quant-dashboard-public-health',
  findings,
});

test('Hub code pushes do not repeat an upstream freshness failure', () => {
  assert.deepEqual(decideHealthGate({
    report: report([hard('freshness')]),
    healthExit: 1,
    eventName: 'workflow_run',
    incidentChanged: true,
  }), { fail: false, reason: 'upstream_freshness_notified_elsewhere' });
});

test('Hub code pushes still fail contract and observability regressions', () => {
  for (const category of ['contract', 'observability']) {
    assert.equal(decideHealthGate({
      report: report([hard(category)]),
      healthExit: 1,
      eventName: 'workflow_run',
      incidentChanged: true,
    }).fail, true);
  }
});

test('scheduled monitor fails once for a new incident and softens an unchanged incident', () => {
  assert.equal(decideHealthGate({
    report: report([hard('freshness')]),
    healthExit: 1,
    eventName: 'schedule',
    incidentChanged: true,
  }).fail, true);
  assert.deepEqual(decideHealthGate({
    report: report([hard('freshness')]),
    healthExit: 1,
    eventName: 'schedule',
    incidentChanged: false,
  }), { fail: false, reason: 'unchanged_scheduled_incident' });
  assert.equal(decideHealthGate({
    report: report([hard('freshness')]),
    healthExit: 1,
    eventName: 'schedule',
    incidentChanged: null,
  }).fail, true);
});

test('manual hard checks fail and transient-only checks pass', () => {
  assert.equal(decideHealthGate({
    report: report([hard('freshness')]),
    healthExit: 1,
    eventName: 'workflow_dispatch',
    incidentChanged: false,
  }).fail, true);
  assert.equal(decideHealthGate({
    report: report(),
    healthExit: 2,
    eventName: 'schedule',
    incidentChanged: false,
  }).fail, false);
});

test('unexpected monitor exit fails closed', () => {
  assert.deepEqual(decideHealthGate({
    report: report(),
    healthExit: 17,
    eventName: 'schedule',
    incidentChanged: false,
  }), { fail: true, reason: 'monitor_failed' });
});

test('invalid reports and report-exit mismatches fail closed', () => {
  assert.deepEqual(decideHealthGate({
    report: {},
    healthExit: 0,
    eventName: 'schedule',
    incidentChanged: false,
  }), { fail: true, reason: 'invalid_health_report' });
  assert.deepEqual(decideHealthGate({
    report: report([hard('freshness')]),
    healthExit: 0,
    eventName: 'schedule',
    incidentChanged: false,
  }), { fail: true, reason: 'report_exit_mismatch' });
  assert.deepEqual(decideHealthGate({
    report: report(),
    healthExit: 1,
    eventName: 'schedule',
    incidentChanged: false,
  }), { fail: true, reason: 'report_exit_mismatch' });
});
