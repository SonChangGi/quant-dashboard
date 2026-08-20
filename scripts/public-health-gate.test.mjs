import assert from 'node:assert/strict';
import test from 'node:test';

import { decideHealthGate } from './public-health-gate.mjs';

const hard = (category) => ({ project: 'example', category, severity: 'hard', message: 'failure' });
const report = (findings = []) => ({
  schemaVersion: 1,
  contract: 'quant-dashboard-public-health',
  findings,
});

test('freshness failures are recorded without failing a usable public site', () => {
  assert.deepEqual(decideHealthGate({
    report: report([hard('freshness')]),
    healthExit: 1,
    eventName: 'workflow_run',
    incidentChanged: true,
  }), { fail: false, reason: 'data_health_warning' });
  assert.deepEqual(decideHealthGate({
    report: report([hard('freshness')]),
    healthExit: 1,
    eventName: 'schedule',
    incidentChanged: true,
  }), { fail: false, reason: 'data_health_warning' });
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

test('scheduled monitor fails once only for a new web-breaking incident', () => {
  assert.equal(decideHealthGate({
    report: report([hard('contract')]),
    healthExit: 1,
    eventName: 'schedule',
    incidentChanged: true,
  }).fail, true);
  assert.deepEqual(decideHealthGate({
    report: report([hard('contract')]),
    healthExit: 1,
    eventName: 'schedule',
    incidentChanged: false,
  }), { fail: false, reason: 'unchanged_web_incident' });
  assert.equal(decideHealthGate({
    report: report([hard('observability')]),
    healthExit: 1,
    eventName: 'schedule',
    incidentChanged: null,
  }).fail, true);
});

test('manual hard checks fail and transient-only checks pass', () => {
  assert.deepEqual(decideHealthGate({
    report: report([hard('freshness')]),
    healthExit: 1,
    eventName: 'workflow_dispatch',
    incidentChanged: false,
  }), { fail: false, reason: 'data_health_warning' });
  assert.equal(decideHealthGate({
    report: report([hard('contract')]),
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

test('unexpected monitor exit stays visible without producing a page-failure signal', () => {
  assert.deepEqual(decideHealthGate({
    report: report(),
    healthExit: 17,
    eventName: 'schedule',
    incidentChanged: false,
  }), { fail: false, reason: 'monitor_internal_error' });
});

test('invalid reports stay non-notifying when no web breakage was proved', () => {
  assert.deepEqual(decideHealthGate({
    report: {},
    healthExit: 0,
    eventName: 'schedule',
    incidentChanged: false,
  }), { fail: false, reason: 'monitor_internal_error' });
});
