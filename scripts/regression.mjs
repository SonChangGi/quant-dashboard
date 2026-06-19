import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const source = readFileSync('assets/app.js', 'utf8');
const context = vm.createContext({ console });
vm.runInContext(source, context, { filename: 'assets/app.js' });
const api = context.__QUANT_DASHBOARD_TESTS__;

const checks = [];
const assert = (condition, label) => checks.push({ ok: Boolean(condition), label });
const fallbackFor = (parsed, hasUsableData, reason) => api.resolveLoadState({ ok: true, data: {} }, hasUsableData, reason);

assert(api, 'test API exposed without browser DOM');

const malformedMomentum = api.parseMomentum({ runs: [{ summary: { selected_factor: 'schema_drift' }, latest_output_rows: [] }], latest_run_index: 0 });
const momentumState = fallbackFor(malformedMomentum, malformedMomentum.rows.length > 0, 'Momentum payload did not contain usable top rows.');
assert(momentumState.mode === 'fallback', 'HTTP 200 malformed momentum payload resolves to fallback mode');
assert(/Momentum payload/.test(momentumState.error), 'Momentum fallback keeps explicit schema reason');

const malformedDram = api.parseDram({ observations: [{ product_name: 'Bad DRAM', date: 'not-a-date', values: { average: 1.23 } }] }, { series: [] }, { generated_at: '2026-06-10T00:00:00Z' });
const dramState = fallbackFor(malformedDram, malformedDram.series.length > 0, 'DRAM payload did not contain usable dated price points.');
assert(dramState.mode === 'fallback', 'HTTP 200 malformed DRAM payload resolves to fallback mode');
assert(api.normalizeChartSeries([{ name: 'bad', points: [['not-a-date', 1.2], ['2026-06-10', Number.NaN]] }]).length === 0, 'DRAM chart drops invalid dates and invalid numeric values');
assert(api.isValidChartPoint('2026-06-10', 1.2), 'DRAM chart accepts valid dated numeric point');

const malformedBest = api.parseBestFactor({ summary: { best_factor: 'schema_drift' }, latest_holdings: [] });
const bestState = fallbackFor(malformedBest, malformedBest.rows.length > 0, 'Best Factor payload did not contain usable holdings.');
assert(bestState.mode === 'fallback', 'HTTP 200 malformed Best Factor payload resolves to fallback mode');
assert(/Best Factor payload/.test(bestState.error), 'Best Factor fallback keeps explicit schema reason');

const malformedEtf = api.parseEtfTracking({ generatedAt: '2026-06-17T00:00:00Z', etfs: [{ id: 'bad', latest: { top10: [] } }] });
const etfState = fallbackFor(malformedEtf, malformedEtf.rows.length > 0, 'ETF Tracking payload did not contain usable ETF rows.');
assert(etfState.mode === 'fallback', 'HTTP 200 malformed ETF Tracking payload resolves to fallback mode');
assert(/ETF Tracking payload/.test(etfState.error), 'ETF Tracking fallback keeps explicit schema reason');

const malformedValuation = api.parseValuation({ generatedAt: '2026-06-19T00:00:00Z', tickers: [null, { name: 'No ticker' }] });
const valuationState = fallbackFor(malformedValuation, malformedValuation.rows.length > 0, 'Valuation payload did not contain usable ticker rows.');
assert(valuationState.mode === 'fallback', 'HTTP 200 malformed Valuation payload resolves to fallback mode');
assert(/Valuation payload/.test(valuationState.error), 'Valuation fallback keeps explicit schema reason');

const validMomentum = api.parseMomentum({ runs: [{ summary: { selected_factor: 'mom_valid', data_as_of: '2026-06-10' }, latest_output_rows: [{ rank: 1, symbol: 'AAA', score: 2, proposed_weight: 0.2, weight: 0.1 }] }], latest_run_index: 0 });
assert(validMomentum.rows.length === 1 && validMomentum.factor === 'mom_valid', 'recorded valid Momentum fixture produces top row');

const validDram = api.parseDram({ observations: [{ product_name: 'DDR5 Fixture', date: '2026-06-10', values: { average: 42 } }] }, { series: [{ product_name: 'DDR5 Fixture', representative: true }] }, { generated_at: '2026-06-10T00:00:00Z' });
assert(validDram.series.length === 1 && validDram.series[0].points.length === 1, 'recorded valid DRAM fixture produces chart series');

const validBest = api.parseBestFactor({ summary: { best_factor: 'quality', data_end_date: '2026-06-10' }, latest_holdings: [{ factor: 'quality', ticker: 'BBB', score: 1, weight: 0.3, rebalance_date: '2026-06-01' }] });
assert(validBest.rows.length === 1 && validBest.factor === 'quality', 'recorded valid Best Factor fixture produces holding row');

const validEtf = api.parseEtfTracking({
  generatedAt: '2026-06-17T00:00:00Z',
  etfs: [{
    shortName: 'ETF Fixture',
    code: '0000',
    availableEndDate: '2026-06-17',
    metrics: { signalCount: 1, entryExitSignalCount: 1, returnCoverage: 1 },
    history: [
      { date: '2026-06-16', holdings: [{ rank: 1, ticker: 'AAA', name: 'Alpha', weightPercent: 5.5 }, { rank: 2, ticker: 'BBB', name: 'Beta', weightPercent: 4 }] },
      { date: '2026-06-17', holdings: [{ rank: 1, ticker: 'AAA', name: 'Alpha', weightPercent: 6.5 }, { rank: 2, ticker: 'BBB', name: 'Beta', weightPercent: 4.5 }] },
    ],
    latest: {
      date: '2026-06-17',
      sourceStatus: 'live',
      top10: [
        { rank: 1, ticker: 'AAA', name: 'Alpha', weightPercent: 6.5 },
        { rank: 2, ticker: 'BBB', name: 'Beta', weightPercent: 4.5 },
      ],
    },
  }],
});
assert(validEtf.rows.length === 1 && validEtf.rows[0].topWeight === 0.065, 'recorded valid ETF Tracking fixture produces ETF row');
assert(validEtf.rows[0].top10.length === 2 && validEtf.rows[0].top10Weight === 0.11, 'recorded valid ETF Tracking fixture preserves top10 list and total weight');
assert(validEtf.rows[0].chartSeries.length === 2 && validEtf.rows[0].chartSeries[0].points.length === 2, 'recorded valid ETF Tracking fixture builds mini chart series');

const validValuation = api.parseValuation({
  generatedAt: '2026-06-19T00:00:00Z',
  modelPolicy: { decisionOwner: '사용자' },
  methodologyReferences: [{ key: 'dcf' }],
  tickers: [
    { ticker: 'AAA', name: 'Alpha', sectorLabel: '기술', themeTags: ['AI'], price: 100, dcfPerShare: 120, qualityStatus: '충분' },
    { ticker: 'BBB', name: 'Beta', sectorLabel: '금융', themeTags: ['Bank'], price: 50, dcfPerShare: 40, qualityStatus: '일부 누락' },
  ],
});
assert(validValuation.rows.length === 2 && validValuation.rows[0].ticker === 'AAA', 'recorded valid Valuation fixture produces DCF gap sorted rows');
assert(validValuation.tickerCount === 2 && validValuation.sectors.includes('기술'), 'recorded valid Valuation fixture preserves coverage metadata');

assert(Object.keys(api.PANEL_ADAPTERS).length === 5, 'panel adapter manifest has five current adapters');


const nullEntryMomentum = api.parseMomentum({ runs: [{ summary: { selected_factor: 'null_drift' }, latest_output_rows: [null, 'bad'], holdings: [null] }], latest_run_index: 0 });
const nullMomentumState = fallbackFor(nullEntryMomentum, nullEntryMomentum.rows.length > 0, 'Momentum payload did not contain usable top rows.');
assert(nullMomentumState.mode === 'fallback', 'Momentum null/non-object entries resolve to fallback without throwing');

const nullEntryDram = api.parseDram({ observations: [null, 'bad', { product_name: 'Bad date', date: 'not-a-date', values: { average: 1 } }] }, { series: [null] }, {});
const nullDramState = fallbackFor(nullEntryDram, nullEntryDram.series.length > 0, 'DRAM payload did not contain usable dated price points.');
assert(nullDramState.mode === 'fallback', 'DRAM null/non-object entries resolve to fallback without throwing');

const nullEntryBest = api.parseBestFactor({ summary: { best_factor: 'null_drift' }, rankings: [null], latest_holdings: [null, 'bad'] });
const nullBestState = fallbackFor(nullEntryBest, nullEntryBest.rows.length > 0, 'Best Factor payload did not contain usable holdings.');
assert(nullBestState.mode === 'fallback', 'Best Factor null/non-object entries resolve to fallback without throwing');

const nullEntryEtf = api.parseEtfTracking({ etfs: [null, 'bad', { latest: { top10: [null] } }] });
const nullEtfState = fallbackFor(nullEntryEtf, nullEntryEtf.rows.length > 0, 'ETF Tracking payload did not contain usable ETF rows.');
assert(nullEtfState.mode === 'fallback', 'ETF Tracking null/non-object entries resolve to fallback without throwing');

const nullEntryValuation = api.parseValuation({ tickers: [null, 'bad', { ticker: 'CCC', themeTags: [null, 'Cloud'], price: 'bad' }] });
assert(nullEntryValuation.rows.length === 1 && nullEntryValuation.rows[0].ticker === 'CCC', 'Valuation null/non-object entries resolve without throwing');

const throwingAdapter = { parse: () => { throw new Error('fixture boom'); } };
const safeParse = api.parsePanelSafely(throwingAdapter, {});
assert(safeParse.ok === false && /Payload parse failed/.test(safeParse.error), 'panel parser exceptions convert to explicit fallback reason');
const contractMismatch = api.validateAdapterContract(api.PANEL_ADAPTERS.valuation, { valuation: { schemaVersion: 999, tickers: [], modelPolicy: {}, methodologyReferences: [] } });
assert(/expected 1/.test(contractMismatch), 'contract version mismatch is rejected before parsing');


class ElementStub {
  constructor(tagName) {
    this.tagName = tagName;
    this.children = [];
    this.attributes = {};
    this.className = '';
    this.id = '';
    this.href = '';
    this.textContent = '';
    this._innerHTML = '';
  }
  replaceChildren(...children) { this.children = children; }
  appendChild(child) { this.children.push(child); return child; }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  get innerHTML() { return this._innerHTML; }
  set innerHTML(value) { this._innerHTML = String(value); }
}
const domTargets = {
  '#top-nav': new ElementStub('nav'),
  '#hero-actions': new ElementStub('div'),
  '#project-grid': new ElementStub('div'),
  '#summary-grid': new ElementStub('div'),
  '#etf-details': new ElementStub('div'),
  '#research-briefing': new ElementStub('div'),
  '#data-health': new ElementStub('div'),
  '#watchlist-results': new ElementStub('div'),
};
context.Node = ElementStub;
context.document = {
  querySelector: (selector) => domTargets[selector] || null,
  createElement: (tagName) => new ElementStub(tagName),
  addEventListener: () => {},
};
api.renderProjectNavigation();
api.renderDashboardPanels();
assert(domTargets['#top-nav'].children.length === 5, 'manifest renderer creates top navigation links');
assert(domTargets['#hero-actions'].children.length === 5, 'manifest renderer creates hero action links');
assert(domTargets['#summary-grid'].children.length === 5, 'manifest renderer creates five dashboard panel shells');
assert(domTargets['#summary-grid'].children.every((child) => /원본 열기/.test(child.innerHTML)), 'dashboard panel shells preserve original page links');
assert(domTargets['#summary-grid'].children.some((child) => /panel-detail/.test(child.innerHTML)), 'ETF panel shell includes detail mount for TOP10 cards');
api.renderEtfDetailCards('#etf-details', validEtf.rows);
assert(/etf-detail-card/.test(domTargets['#etf-details'].innerHTML), 'ETF detail renderer creates per-ETF card markup');
assert(/AAA/.test(domTargets['#etf-details'].innerHTML) && /BBB/.test(domTargets['#etf-details'].innerHTML), 'ETF detail renderer includes TOP10 holdings');
assert(/TOP10 비중 변화 미니 그래프/.test(domTargets['#etf-details'].innerHTML), 'ETF detail renderer includes mini chart markup');

const records = [
  { project: api.PROJECTS.find((project) => project.id === 'valuation'), summary: validValuation, mode: 'live', generatedAt: validValuation.generatedAt, payloadBytes: 12000, sourceCount: 1 },
  { project: api.PROJECTS.find((project) => project.id === 'etf'), summary: validEtf, mode: 'live', generatedAt: validEtf.generatedAt, payloadBytes: 90000, sourceCount: 1 },
];
api.renderResearchBriefing(records);
api.renderDataHealth(records);
assert(/Valuation/.test(domTargets['#research-briefing'].innerHTML), 'research briefing renders valuation item');
assert(/live/.test(domTargets['#data-health'].innerHTML), 'data health renders live state');
assert(api.watchlistMatchesForToken(records, 'AAA').length >= 2, 'watchlist matcher connects valuation and ETF ticker exposure');
assert(api.parseWatchlistTokens('NVDA, AMD DRAM').join('|') === 'NVDA|AMD|DRAM', 'watchlist token parser handles commas and spaces');

const failed = checks.filter((check) => !check.ok);
for (const check of checks) console.log(`${check.ok ? 'PASS' : 'FAIL'} ${check.label}`);
if (failed.length) {
  console.error(`\n${failed.length} regression check(s) failed.`);
  process.exit(1);
}
console.log(`\n${checks.length} regression checks passed.`);
