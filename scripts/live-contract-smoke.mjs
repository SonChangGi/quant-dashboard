import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import vm from 'node:vm';
import {
  operationalFindingsFor,
  transportEscalation,
} from './public-health-policy.mjs';

const MAX_PAYLOAD_BYTES = 8_000_000;
const MAX_GENERATION_AGE_DAYS = 21;
const REQUIRED_PROJECT_COUNT = 8;
const reportPath = argumentValue('--report');

const sandbox = { console };
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(readFileSync('assets/app.js', 'utf8'), sandbox, { filename: 'assets/app.js' });

const api = sandbox.__QUANT_DASHBOARD_TESTS__;
if (!api) throw new Error('Dashboard test API was not exported.');

const { PROJECTS, PANEL_ADAPTERS } = api;
const panelProjects = PROJECTS.filter(
  (project) => project.panelAdapter && PANEL_ADAPTERS[project.panelAdapter],
);
const results = [];
const findings = [];

if (panelProjects.length !== REQUIRED_PROJECT_COUNT) {
  addFinding('hub', 'contract', 'hard', `Expected ${REQUIRED_PROJECT_COUNT} panel projects, found ${panelProjects.length}.`);
}

for (const project of panelProjects) {
  const adapter = PANEL_ADAPTERS[project.panelAdapter];
  let entries;
  try {
    entries = await Promise.all(
      Object.entries(adapter.sourceUrls).map(async ([sourceKey, url]) => [
        sourceKey,
        await fetchJson(url),
      ]),
    );
  } catch (error) {
    const category = error instanceof PublicFetchError ? error.category : 'transport';
    addFinding(project.id, category, category === 'transport' ? 'transient' : 'hard', error.message);
    results.push(resultRow(project.id, {
      state: category === 'transport' ? 'transient' : 'hard',
      sources: 0,
    }));
    continue;
  }

  const projectFindingStart = findings.length;
  const payloadBytes = entries.reduce((sum, [, result]) => sum + result.bytes, 0);
  const dataSources = Object.fromEntries(
    entries.map(([sourceKey, result]) => [sourceKey, result.data]),
  );
  const contractError = api.validateAdapterContract(adapter, dataSources);
  if (contractError) {
    addFinding(project.id, 'contract', 'hard', contractError);
    results.push(resultRow(project.id, {
      state: 'contract',
      payloadBytes,
      sources: entries.length,
    }));
    continue;
  }

  let summary;
  try {
    summary = adapter.parse(dataSources);
  } catch (error) {
    addFinding(
      project.id,
      'contract',
      'hard',
      `Payload parse failed: ${error instanceof Error ? error.message : String(error)}`,
    );
    results.push(resultRow(project.id, {
      state: 'contract',
      payloadBytes,
      sources: entries.length,
    }));
    continue;
  }

  const usable = adapter.hasUsableData(summary);
  const record = {
    project,
    summary,
    mode: 'live',
    generatedAt: summary?.generatedAt || '',
    dataAsOf: api.summaryDataAsOf(summary),
    payloadBytes,
    sourceCount: entries.length,
  };
  const generatedAgeDays = ageDays(summary?.generatedAt);
  const freshnessSource = api.recordFreshnessDate(record);
  const freshnessAgeDays = ageDays(freshnessSource);
  const expectedFreshnessDays = api.expectedFreshnessDays(record);
  const staleBySource = api.isRecordStale(record);

  check(project.id, usable, 'contract', `${project.id} live payload is not usable`);
  check(project.id, payloadBytes > 0, 'contract', `${project.id} payload byte count is missing`);
  check(
    project.id,
    payloadBytes <= MAX_PAYLOAD_BYTES,
    'contract',
    `${project.id} payload exceeds ${MAX_PAYLOAD_BYTES.toLocaleString('en-US')} bytes`,
  );
  check(
    project.id,
    generatedAgeDays !== null,
    'contract',
    `${project.id} generatedAt is missing or invalid`,
  );
  check(
    project.id,
    expectedFreshnessDays !== null,
    'contract',
    `${project.id} has no expected freshness policy`,
  );

  check(
    project.id,
    freshnessAgeDays !== null,
    'contract',
    `${project.id} has no parseable data freshness source`,
  );
  if (
    summary?.meta?.dataAsOf
    || summary?.meta?.minDataAsOf
    || summary?.dataAsOf
    || summary?.dataEndDate
  ) {
    check(
      project.id,
      freshnessSource !== summary?.generatedAt,
      'contract',
      `${project.id} freshness source incorrectly used generatedAt`,
    );
  }
  if (freshnessAgeDays !== null && expectedFreshnessDays !== null) {
    check(
      project.id,
      freshnessAgeDays <= expectedFreshnessDays || staleBySource,
      'contract',
      `${project.id} stale data is not detected by Hub health logic`,
    );
    if (freshnessAgeDays > expectedFreshnessDays) {
      addFinding(
        project.id,
        'freshness',
        'hard',
        `${project.id} data is ${freshnessAgeDays.toFixed(1)} days old; expected <= ${expectedFreshnessDays} days`,
      );
    }
  }
  if (generatedAgeDays !== null && generatedAgeDays > MAX_GENERATION_AGE_DAYS) {
    addFinding(
      project.id,
      'freshness',
      'hard',
      `${project.id} generation is ${generatedAgeDays.toFixed(1)} days old`,
    );
  }

  operationalFindingsFor(project.id, summary).forEach((finding) => findings.push(finding));

  const projectFindings = findings.slice(projectFindingStart);
  results.push(resultRow(project.id, {
    state: projectFindings.some((finding) => finding.severity === 'hard')
      ? 'hard'
      : projectFindings.some((finding) => finding.category === 'operation')
        ? 'degraded'
        : projectFindings.length
          ? 'transient'
        : 'ok',
    generatedAt: summary?.generatedAt || 'n/a',
    freshnessSource: freshnessSource || 'n/a',
    staleBySource,
    payloadBytes,
    sources: entries.length,
    rows: rowCountFor(project.id, summary),
  }));
}

const transientTransportProjects = findings
  .filter((finding) => finding.category === 'transport' && finding.severity === 'transient')
  .map((finding) => finding.project);
const broadTransportFailure = transportEscalation(
  transientTransportProjects,
  panelProjects.length,
);
if (broadTransportFailure) {
  findings.push(broadTransportFailure);
  const affectedProjects = new Set(broadTransportFailure.affectedProjects);
  results
    .filter((result) => affectedProjects.has(result.project))
    .forEach((result) => {
      result.state = 'hard';
    });
}

const hardFindings = findings.filter((finding) => finding.severity === 'hard');
const transientFindings = findings.filter((finding) => finding.severity === 'transient');
const report = {
  schemaVersion: 1,
  contract: 'quant-dashboard-public-health',
  generatedAt: new Date().toISOString(),
  state: hardFindings.length ? 'failed' : transientFindings.length ? 'degraded' : 'healthy',
  counts: {
    projectCount: panelProjects.length,
    healthyProjectCount: results.filter((result) => result.state === 'ok').length,
    hardFindingCount: hardFindings.length,
    transientFindingCount: transientFindings.length,
  },
  findings,
  projects: results,
};

if (reportPath) {
  const target = resolve(reportPath);
  mkdirSync(dirname(target), { recursive: true });
  writeFileSync(target, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
}

console.table(results.map((result) => ({
  project: result.project,
  state: result.state,
  generatedAt: result.generatedAt,
  freshnessSource: result.freshnessSource,
  staleBySource: result.staleBySource,
  sources: result.sources,
  rows: result.rows,
  payloadKB: Math.round(result.payloadBytes / 1024),
})));
for (const finding of findings) {
  const prefix = finding.severity === 'hard' ? 'ERROR' : 'WARN';
  console.error(`${prefix} [${finding.category}] ${finding.project}: ${finding.message}`);
}
console.log(
  `Public health ${report.state}: ${report.counts.healthyProjectCount}/${report.counts.projectCount} healthy, `
  + `${hardFindings.length} hard, ${transientFindings.length} transient.`,
);

if (hardFindings.length) process.exitCode = 1;
else if (transientFindings.length) process.exitCode = 2;

async function fetchJson(url) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 12_000);
  try {
    const response = await fetch(url, { signal: controller.signal, cache: 'no-store' });
    if (!response.ok) {
      const category = response.status === 429 || response.status >= 500
        ? 'transport'
        : 'contract';
      throw new PublicFetchError(category, `${url} returned HTTP ${response.status}`);
    }
    const text = await response.text();
    const bytes = Buffer.byteLength(text, 'utf8');
    try {
      return { url, bytes, data: JSON.parse(text) };
    } catch {
      throw new PublicFetchError('contract', `${url} returned invalid JSON`);
    }
  } catch (error) {
    if (error instanceof PublicFetchError) throw error;
    throw new PublicFetchError(
      'transport',
      `${url} fetch failed: ${error instanceof Error ? error.message : String(error)}`,
    );
  } finally {
    clearTimeout(timeout);
  }
}

function check(project, condition, category, message) {
  if (!condition) addFinding(project, category, 'hard', message);
}

function addFinding(project, category, severity, message) {
  findings.push({ project, category, severity, message });
}

function resultRow(project, values = {}) {
  return {
    project,
    state: values.state || 'unknown',
    generatedAt: values.generatedAt || 'n/a',
    freshnessSource: values.freshnessSource || 'n/a',
    staleBySource: Boolean(values.staleBySource),
    payloadBytes: values.payloadBytes || 0,
    sources: values.sources || 0,
    rows: values.rows || 0,
  };
}

function rowCountFor(projectId, summary) {
  if (projectId === 'dram') return summary?.series?.length || summary?.entities?.length || 0;
  return summary?.rows?.length || summary?.entities?.length || 0;
}

function ageDays(value) {
  const timestamp = Date.parse(value || '');
  if (!Number.isFinite(timestamp)) return null;
  return (Date.now() - timestamp) / (24 * 60 * 60 * 1000);
}

function argumentValue(name) {
  const index = process.argv.indexOf(name);
  return index >= 0 ? process.argv[index + 1] || '' : '';
}

class PublicFetchError extends Error {
  constructor(category, message) {
    super(message);
    this.name = 'PublicFetchError';
    this.category = category;
  }
}
