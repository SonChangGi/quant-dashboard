import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

export function decideHealthGate({ report = {}, healthExit, eventName, incidentChanged }) {
  const exitCode = String(healthExit ?? '');
  const reportValid = report?.schemaVersion === 1
    && report?.contract === 'quant-dashboard-public-health'
    && Array.isArray(report?.findings);
  if (!reportValid) {
    return { fail: true, reason: 'invalid_health_report' };
  }
  const hardFindings = report.findings.filter((finding) => finding?.severity === 'hard');
  if ((exitCode === '0' || exitCode === '2') && hardFindings.length) {
    return { fail: true, reason: 'report_exit_mismatch' };
  }
  if (exitCode === '1' && !hardFindings.length) {
    return { fail: true, reason: 'report_exit_mismatch' };
  }
  if (exitCode === '0' || exitCode === '2') {
    return { fail: false, reason: exitCode === '2' ? 'transient_findings' : 'healthy' };
  }
  if (exitCode !== '1') {
    return { fail: true, reason: 'monitor_failed' };
  }

  if (eventName === 'workflow_run') {
    const blocking = hardFindings.filter((finding) => (
      finding.category === 'contract' || finding.category === 'observability'
    ));
    if (!blocking.length) {
      return { fail: false, reason: 'upstream_freshness_notified_elsewhere' };
    }
  }
  if (eventName === 'schedule' && incidentChanged === false) {
    return { fail: false, reason: 'unchanged_scheduled_incident' };
  }
  return { fail: true, reason: 'hard_regression' };
}

function argumentValue(name) {
  const index = process.argv.indexOf(name);
  return index >= 0 ? process.argv[index + 1] : '';
}

function main() {
  const reportPath = argumentValue('--report');
  const incidentChangedRaw = argumentValue('--incident-changed');
  const report = reportPath && existsSync(reportPath)
    ? JSON.parse(readFileSync(reportPath, 'utf8'))
    : {};
  const decision = decideHealthGate({
    report,
    healthExit: argumentValue('--health-exit'),
    eventName: argumentValue('--event-name'),
    incidentChanged: incidentChangedRaw === 'true'
      ? true
      : incidentChangedRaw === 'false'
        ? false
        : null,
  });
  console.log(JSON.stringify(decision));
  if (decision.fail) process.exitCode = 1;
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  main();
}
