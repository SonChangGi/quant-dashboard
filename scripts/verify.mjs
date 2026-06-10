import { readFileSync, statSync } from 'node:fs';

const files = {
  html: readFileSync('index.html', 'utf8'),
  css: readFileSync('assets/styles.css', 'utf8'),
  app: readFileSync('assets/app.js', 'utf8'),
  readme: readFileSync('README.md', 'utf8'),
};

const checks = [];
const assert = (condition, label) => checks.push({ label, ok: Boolean(condition) });
const contains = (file, needle) => file.includes(needle);

for (const path of ['index.html', 'assets/styles.css', 'assets/app.js', 'scripts/verify.mjs', 'scripts/regression.mjs', 'scripts/static-smoke.mjs', 'package.json']) {
  assert(statSync(path).isFile(), `${path} exists`);
}

const projectUrls = [
  'https://sonchanggi.github.io/momentum-factor-lab/',
  'https://sonchanggi.github.io/dram-price/',
  'https://sonchanggi.github.io/best-factor/',
];
for (const url of projectUrls) {
  assert(contains(files.html, url) || contains(files.app, url), `project URL present: ${url}`);
}

const dataUrls = [
  'https://sonchanggi.github.io/momentum-factor-lab/data/dashboard.json',
  'https://sonchanggi.github.io/dram-price/data/prices.json',
  'https://sonchanggi.github.io/dram-price/data/series.json',
  'https://sonchanggi.github.io/dram-price/data/status.json',
  'https://sonchanggi.github.io/best-factor/data/latest-results.json',
];
for (const url of dataUrls) {
  assert(contains(files.app, url), `public data endpoint present: ${url}`);
}

assert(contains(files.app, 'const PROJECTS = ['), 'project registry exists');
assert(contains(files.app, 'PANEL_ADAPTERS'), 'panel adapter manifest exists');
assert(contains(files.app, 'renderDashboardPanels'), 'manifest-driven dashboard panel renderer exists');
assert(contains(files.app, 'loadProjectPanel'), 'shared panel loader exists');
assert(contains(files.html, 'id="top-nav"'), 'dynamic top navigation mount exists');
assert(contains(files.html, 'id="summary-grid"'), 'dynamic dashboard mount exists');
assert(contains(files.app, 'FALLBACK_SNAPSHOT'), 'fallback snapshot exists');
assert(contains(files.app, 'getJsonBestEffort'), 'best-effort fetch helper exists');
assert(contains(files.app, 'resolveLoadState'), 'schema/empty-data load state resolver exists');
assert(contains(files.app, 'parsePanelSafely'), 'parser exception fallback guard exists');
assert(contains(files.app, 'asRecords'), 'external arrays are filtered to records');
assert(contains(files.app, 'parseMomentum'), 'momentum parser exists');
assert(contains(files.app, 'latest_output_rows'), 'momentum latest output optional field is handled');
assert(contains(files.app, 'parseDram'), 'DRAM parser exists');
assert(contains(files.app, 'renderDramChart'), 'DRAM SVG chart renderer exists');
assert(contains(files.app, 'D램 가격'), 'Korean D램 price label exists');
assert(contains(files.app, 'isValidChartPoint'), 'DRAM chart validates date/value points');
assert(contains(files.app, 'parseBestFactor'), 'best factor parser exists');
assert(contains(files.app, 'latest_holdings'), 'best factor holdings optional field is handled');
assert(contains(files.app, 'formatFreshness'), 'freshness formatter exists');
assert(contains(files.app, '업데이트 시각 알 수 없음'), 'freshness fallback text exists');
assert(contains(files.app, "panelDomId(project, 'status')"), 'manifest-generated freshness/status hooks exist');
assert(contains(files.app, 'status-line'), 'panel status line renderer exists');
assert(contains(files.html, '투자, 세무, 법률 또는 매매 조언이 아닙니다'), 'research disclaimer exists');
assert(contains(files.readme, '다른 프로젝트의 로컬 소스 코드를 수정하지 않습니다'), 'README isolation note exists');
assert(contains(readFileSync('scripts/regression.mjs', 'utf8'), 'malformed momentum payload resolves to fallback mode'), 'malformed payload regression exists');
assert(contains(readFileSync('scripts/regression.mjs', 'utf8'), 'null/non-object entries resolve to fallback'), 'null-entry payload regression exists');
assert(contains(readFileSync('scripts/static-smoke.mjs', 'utf8'), 'static server smoke'), 'static server smoke exists');
assert(!contains(files.app, '../momentum-factor-lab') && !contains(files.app, '../dram-price') && !contains(files.app, '../best-factor'), 'no sibling local source paths referenced');

const failed = checks.filter((check) => !check.ok);
for (const check of checks) {
  console.log(`${check.ok ? 'PASS' : 'FAIL'} ${check.label}`);
}

if (failed.length) {
  console.error(`\n${failed.length} verification check(s) failed.`);
  process.exit(1);
}

console.log(`\n${checks.length} verification checks passed.`);
