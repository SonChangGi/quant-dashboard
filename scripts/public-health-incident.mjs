import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

export function normalizeIncidentMessage(value) {
  return String(value || '')
    .replace(/\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z\b/g, '#datetime')
    .replace(/\b\d{4}-\d{2}-\d{2}\b/g, '#date')
    .replace(/\b\d+(?:\.\d+)?(?=\s+days?\s+old\b)/gi, '#')
    .replace(/(?<=\bstale\s+for\s+)\d+(?:\.\d+)?(?=\s+days?\b)/gi, '#')
    .replace(/\s+/g, ' ')
    .trim();
}

export function incidentIdentity(report) {
  const findings = Array.isArray(report?.findings) ? report.findings : [];
  return findings
    .filter((finding) => finding?.severity === 'hard')
    .map((finding) => ({
      project: String(finding.project || 'unknown'),
      category: String(finding.category || 'unknown'),
      message: normalizeIncidentMessage(finding.message),
      affectedProjects: Array.isArray(finding.affectedProjects)
        ? [...new Set(finding.affectedProjects.map(String))].sort()
        : [],
    }))
    .sort((left, right) => (
      left.project.localeCompare(right.project)
      || left.category.localeCompare(right.category)
      || left.message.localeCompare(right.message)
    ));
}

export function incidentState(report, previous = null) {
  const identity = incidentIdentity(report);
  const fingerprint = identity.length
    ? createHash('sha256').update(JSON.stringify(identity)).digest('hex')
    : '';
  const previousFingerprint = previous?.schemaVersion === 1
    && previous?.contract === 'quant-dashboard-public-health-incident'
    && typeof previous?.fingerprint === 'string'
    ? previous.fingerprint
    : '';
  return {
    schemaVersion: 1,
    contract: 'quant-dashboard-public-health-incident',
    generatedAt: new Date().toISOString(),
    fingerprint,
    previousFingerprint,
    changed: fingerprint !== previousFingerprint,
    hardFindingCount: identity.length,
    identity,
  };
}

function argumentValue(name) {
  const index = process.argv.indexOf(name);
  return index >= 0 ? process.argv[index + 1] : '';
}

function readJson(path, { optional = false } = {}) {
  if (!path || !existsSync(path)) {
    if (optional) return null;
    throw new Error(`Missing required JSON file: ${path || '(empty path)'}`);
  }
  return JSON.parse(readFileSync(path, 'utf8'));
}

function appendGithubOutputs(path, state) {
  if (!path) return;
  const lines = [
    `fingerprint=${state.fingerprint}`,
    `previous_fingerprint=${state.previousFingerprint}`,
    `changed=${state.changed ? 'true' : 'false'}`,
    `has_hard=${state.hardFindingCount ? 'true' : 'false'}`,
    `hard_count=${state.hardFindingCount}`,
  ];
  writeFileSync(path, `${lines.join('\n')}\n`, { flag: 'a' });
}

function main() {
  const reportPath = argumentValue('--report');
  const previousPath = argumentValue('--previous');
  const outputPath = argumentValue('--output');
  const githubOutputPath = argumentValue('--github-output');
  if (!reportPath || !outputPath) {
    throw new Error('Usage: public-health-incident --report FILE --output FILE [--previous FILE]');
  }
  const state = incidentState(
    readJson(resolve(reportPath)),
    readJson(previousPath ? resolve(previousPath) : '', { optional: true }),
  );
  const resolvedOutput = resolve(outputPath);
  mkdirSync(dirname(resolvedOutput), { recursive: true });
  writeFileSync(resolvedOutput, `${JSON.stringify(state, null, 2)}\n`);
  appendGithubOutputs(githubOutputPath, state);
  console.log(JSON.stringify({
    fingerprint: state.fingerprint || null,
    previousFingerprint: state.previousFingerprint || null,
    changed: state.changed,
    hardFindingCount: state.hardFindingCount,
  }));
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  main();
}
