import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const MAX_PAYLOAD_BYTES = 8_000_000;
const MAX_STALENESS_DAYS = 21;
const REQUIRED_PROJECT_COUNT = 6;

const sandbox = { console };
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(readFileSync('assets/app.js', 'utf8'), sandbox, { filename: 'assets/app.js' });

const api = sandbox.__QUANT_DASHBOARD_TESTS__;
if (!api) throw new Error('Dashboard test API was not exported.');

const { PROJECTS, PANEL_ADAPTERS } = api;
const panelProjects = PROJECTS.filter((project) => project.panelAdapter && PANEL_ADAPTERS[project.panelAdapter]);
const results = [];

if (panelProjects.length !== REQUIRED_PROJECT_COUNT) {
  throw new Error(`Expected ${REQUIRED_PROJECT_COUNT} panel projects, found ${panelProjects.length}.`);
}

for (const project of panelProjects) {
  const adapter = PANEL_ADAPTERS[project.panelAdapter];
  const entries = await Promise.all(
    Object.entries(adapter.sourceUrls).map(async ([sourceKey, url]) => [sourceKey, await fetchJson(url)])
  );
  const payloadBytes = entries.reduce((sum, [, result]) => sum + result.bytes, 0);
  const dataSources = Object.fromEntries(entries.map(([sourceKey, result]) => [sourceKey, result.data]));
  const contractError = api.validateAdapterContract(adapter, dataSources);
  assert(!contractError, `${project.id} contract is compatible: ${contractError || 'ok'}`);
  const summary = adapter.parse(dataSources);
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
  const generatedFreshness = freshnessDays(summary?.generatedAt);
  const freshnessSource = api.recordFreshnessDate(record);
  const freshness = freshnessDays(freshnessSource);
  const expectedFreshnessDays = finiteNumber(summary?.meta?.expectedFreshnessDays);
  const staleBySource = api.isRecordStale(record);

  assert(usable, `${project.id} live payload is usable`);
  assert(payloadBytes > 0, `${project.id} payload byte count is known`);
  assert(payloadBytes <= MAX_PAYLOAD_BYTES, `${project.id} payload is under ${MAX_PAYLOAD_BYTES.toLocaleString('en-US')} bytes`);
  assert(generatedFreshness !== null, `${project.id} payload exposes a parseable generatedAt timestamp`);
  if (expectedFreshnessDays !== null) {
    assert(freshness !== null, `${project.id} payload exposes a parseable data freshness source`);
    if ((summary?.meta?.dataAsOf || summary?.dataAsOf || summary?.dataEndDate) && freshnessSource === summary?.generatedAt) {
      throw new Error(`${project.id} freshness source did not prefer dataAsOf/dataEndDate over generatedAt`);
    }
    if (freshness > expectedFreshnessDays) {
      assert(staleBySource, `${project.id} dataAsOf staleness is detected by dashboard health logic`);
    } else {
      assert(!staleBySource, `${project.id} fresh dataAsOf is not mislabeled stale`);
    }
  } else {
    assert(generatedFreshness <= MAX_STALENESS_DAYS, `${project.id} generatedAt is fresh within ${MAX_STALENESS_DAYS} days`);
  }
  if (project.id === 'valuation') {
    assert((summary.tickerCount || 0) >= 10, 'valuation covers at least 10 tickers');
    assert((summary.sectors || []).length >= 3, 'valuation covers at least 3 sectors/themes');
  }

  results.push({
    project: project.id,
    generatedAt: summary?.generatedAt || 'n/a',
    freshnessSource: freshnessSource || 'n/a',
    staleBySource,
    payloadBytes,
    sources: entries.length,
    rows: rowCountFor(project.id, summary),
  });
}

console.table(results.map((result) => ({
  project: result.project,
  generatedAt: result.generatedAt,
  freshnessSource: result.freshnessSource,
  staleBySource: result.staleBySource,
  sources: result.sources,
  rows: result.rows,
  payloadKB: Math.round(result.payloadBytes / 1024),
})));
console.log(`Live contract smoke passed for ${results.length} public dashboard payloads.`);

async function fetchJson(url) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 12_000);
  try {
    const response = await fetch(url, { signal: controller.signal, cache: 'no-store' });
    if (!response.ok) throw new Error(`${url} returned HTTP ${response.status}`);
    const text = await response.text();
    const bytes = Buffer.byteLength(text, 'utf8');
    return { url, bytes, data: JSON.parse(text) };
  } finally {
    clearTimeout(timeout);
  }
}

function rowCountFor(projectId, summary) {
  if (projectId === 'dram') return summary?.series?.length || summary?.entities?.length || 0;
  if (projectId === 'valuation') return summary?.tickerCount || summary?.rows?.length || 0;
  return summary?.rows?.length || summary?.entities?.length || 0;
}

function freshnessDays(value) {
  const timestamp = Date.parse(value || '');
  if (!Number.isFinite(timestamp)) return null;
  return (Date.now() - timestamp) / (24 * 60 * 60 * 1000);
}

function finiteNumber(value) {
  if (value === null || value === undefined || value === '') return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}
