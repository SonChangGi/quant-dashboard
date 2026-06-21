import { readFileSync, statSync } from 'node:fs';

const files = {
  html: readFileSync('index.html', 'utf8'),
  css: readFileSync('assets/styles.css', 'utf8'),
  app: readFileSync('assets/app.js', 'utf8'),
  readme: readFileSync('README.md', 'utf8'),
  packageJson: readFileSync('package.json', 'utf8'),
  liveSmoke: readFileSync('scripts/live-contract-smoke.mjs', 'utf8'),
};

const checks = [];
const assert = (condition, label) => checks.push({ label, ok: Boolean(condition) });
const contains = (file, needle) => file.includes(needle);

for (const path of ['index.html', 'assets/styles.css', 'assets/app.js', 'scripts/verify.mjs', 'scripts/regression.mjs', 'scripts/static-smoke.mjs', 'scripts/live-contract-smoke.mjs', 'package.json']) {
  assert(statSync(path).isFile(), `${path} exists`);
}

const projectUrls = [
  'https://sonchanggi.github.io/momentum-factor-lab/',
  'https://sonchanggi.github.io/dram-price/',
  'https://sonchanggi.github.io/best-factor/',
  'https://sonchanggi.github.io/etf-tracking/',
  'https://sonchanggi.github.io/valuation/',
];
for (const url of projectUrls) {
  assert(contains(files.html, url) || contains(files.app, url), `project URL present: ${url}`);
}

const dataUrls = [
  'https://sonchanggi.github.io/momentum-factor-lab/data/summary.json',
  'https://sonchanggi.github.io/dram-price/data/summary.json',
  'https://sonchanggi.github.io/dram-price/data/prices.json',
  'https://sonchanggi.github.io/dram-price/data/series.json',
  'https://sonchanggi.github.io/dram-price/data/status.json',
  'https://sonchanggi.github.io/best-factor/data/summary.json',
  'https://sonchanggi.github.io/etf-tracking/data/summary.json',
  'https://sonchanggi.github.io/etf-tracking/data/dashboard.json',
  'https://sonchanggi.github.io/etf-tracking/data/history.json',
  'https://sonchanggi.github.io/valuation/data/summary.json',
];
for (const url of dataUrls) {
  assert(contains(files.app, url), `public data endpoint present: ${url}`);
}

assert(contains(files.app, 'const PROJECTS = ['), 'project registry exists');
assert(contains(files.app, 'PANEL_ADAPTERS'), 'panel adapter manifest exists');
assert(contains(files.app, 'quant-research-summary'), 'common summary contract is validated');
assert(contains(files.app, 'summaryEntities'), 'common summary entities feed dossier search');
assert(contains(files.app, 'renderDashboardPanels'), 'manifest-driven dashboard panel renderer exists');
assert(contains(files.app, 'loadProjectPanel'), 'shared panel loader exists');
assert(contains(files.html, 'id="top-nav"'), 'dynamic top navigation mount exists');
assert(contains(files.html, 'id="summary-grid"'), 'dynamic dashboard mount exists');
assert(contains(files.html, 'id="research-briefing"'), 'research briefing mount exists');
assert(contains(files.html, 'id="watchlist-input"'), 'watchlist input exists');
assert(contains(files.html, 'id="data-health"'), 'data health mount exists');
assert(contains(files.app, 'FALLBACK_SNAPSHOT'), 'fallback snapshot exists');
assert(contains(files.app, 'getJsonBestEffort'), 'best-effort fetch helper exists');
assert(contains(files.app, 'textByteLength'), 'payload byte counter helper exists');
assert(contains(files.app, 'resolveLoadState'), 'schema/empty-data load state resolver exists');
assert(contains(files.app, 'parsePanelSafely'), 'parser exception fallback guard exists');
assert(contains(files.app, 'validateAdapterContract'), 'versioned public JSON contract validator exists');
assert(contains(files.app, 'expectedVersion') && contains(files.app, 'schemaVersion') && contains(files.app, 'quant-research-summary'), 'public data contract versions are explicit');
assert(contains(files.app, 'asRecords'), 'external arrays are filtered to records');
assert(contains(files.app, 'parseMomentum'), 'momentum parser exists');
assert(contains(files.app, 'latest_output_rows'), 'momentum latest output optional field is handled');
assert(contains(files.app, 'deriveMomentumDisplayWeights'), 'momentum research-only weights are normalized for display');
assert(contains(files.app, '리서치 신호 정규화 비중'), 'momentum normalized weight source is explicit');
assert(contains(files.app, 'parseDram'), 'DRAM parser exists');
assert(contains(files.app, 'renderDramChart'), 'DRAM SVG chart renderer exists');
assert(contains(files.app, 'TrendForce daily'), 'DRAM chart prioritizes saved TrendForce daily prices');
assert(contains(files.app, 'D램 가격'), 'Korean D램 price label exists');
assert(contains(files.app, 'isValidChartPoint'), 'DRAM chart validates date/value points');
assert(contains(files.app, 'parseBestFactor'), 'best factor parser exists');
assert(contains(files.app, 'parseEtfTracking'), 'ETF Tracking parser exists');
assert(contains(files.app, 'parseValuation'), 'Valuation parser exists');
assert(contains(files.app, 'ETF별 TOP10 비중'), 'ETF Tracking detail panel label exists');
assert(contains(files.app, '최근 1개월 비중 변화'), 'ETF Tracking chart copy names the one-month history window');
assert(contains(files.app, 'enrichEtfTrackingSources'), 'ETF Tracking adapter loads per-ETF history sources');
assert(contains(files.app, 'compactEtfHistoryPayload'), 'ETF Tracking history is compacted to recent window');
assert(contains(files.app, 'Range') && contains(files.app, 'compactEtfHistoryTailText'), 'ETF Tracking history uses ranged tail reads before full-file fallback');
assert(contains(files.app, 'appendEtfHistoryStatus'), 'ETF Tracking status reports per-ETF history load coverage');
assert(contains(files.app, 'renderEtfDetailCards'), 'ETF Tracking TOP10 detail renderer exists');
assert(contains(files.app, 'renderEtfMiniChart'), 'ETF Tracking mini chart renderer exists');
assert(contains(files.css, '.etf-detail-grid'), 'ETF Tracking detail grid CSS exists');
assert(contains(files.css, '.etf-top10-list'), 'ETF Tracking TOP10 list CSS exists');
assert(contains(files.app, 'latest_holdings'), 'best factor holdings optional field is handled');
assert(contains(files.app, 'formatFreshness'), 'freshness formatter exists');
assert(contains(files.app, 'renderResearchBriefing'), 'research briefing renderer exists');
assert(contains(files.app, 'renderDataHealth'), 'data health renderer exists');
assert(contains(files.app, 'watchlistMatchesForToken'), 'watchlist matcher exists');
assert(contains(files.app, 'health-link'), 'data health links automation/manual update workflows');
assert(contains(files.app, 'entitySummaryLine'), 'watchlist dossier uses entity-level summary lines');
assert(contains(files.app, '업데이트 시각 알 수 없음'), 'freshness fallback text exists');
assert(contains(files.app, "panelDomId(project, 'status')"), 'manifest-generated freshness/status hooks exist');
assert(contains(files.app, 'status-line'), 'panel status line renderer exists');
assert(contains(files.html, '투자, 세무, 법률 또는 매매 조언이 아닙니다'), 'research disclaimer exists');
assert(contains(files.readme, '다른 프로젝트의 로컬 소스 코드를 직접 import하지 않습니다'), 'README isolation note exists');
assert(contains(files.readme, 'summary.json'), 'README documents summary contract endpoint');
assert(contains(readFileSync('scripts/regression.mjs', 'utf8'), 'malformed momentum payload resolves to fallback mode'), 'malformed payload regression exists');
assert(contains(readFileSync('scripts/regression.mjs', 'utf8'), 'null/non-object entries resolve to fallback'), 'null-entry payload regression exists');
assert(contains(readFileSync('scripts/static-smoke.mjs', 'utf8'), 'static server smoke'), 'static server smoke exists');
assert(contains(files.packageJson, '"test:live"'), 'package exposes optional live contract smoke');
assert(contains(files.liveSmoke, 'MAX_PAYLOAD_BYTES') && contains(files.liveSmoke, 'MAX_STALENESS_DAYS'), 'live contract smoke checks payload size and freshness');
assert(contains(files.liveSmoke, 'validateAdapterContract'), 'live contract smoke rejects incompatible contract versions');
assert(!contains(files.app, '../momentum-factor-lab') && !contains(files.app, '../dram-price') && !contains(files.app, '../best-factor') && !contains(files.app, '../etf-tracking') && !contains(files.app, '../valuation'), 'no sibling local source paths referenced');

const failed = checks.filter((check) => !check.ok);
for (const check of checks) {
  console.log(`${check.ok ? 'PASS' : 'FAIL'} ${check.label}`);
}

if (failed.length) {
  console.error(`\n${failed.length} verification check(s) failed.`);
  process.exit(1);
}

console.log(`\n${checks.length} verification checks passed.`);
