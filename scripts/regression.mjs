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


const validMomentum = api.parseMomentum({ runs: [{ summary: { selected_factor: 'mom_valid', data_as_of: '2026-06-10' }, latest_output_rows: [{ rank: 1, symbol: 'AAA', score: 2, proposed_weight: 0.2, weight: 0.1 }] }], latest_run_index: 0 });
assert(validMomentum.rows.length === 1 && validMomentum.factor === 'mom_valid', 'recorded valid Momentum fixture produces top row');

const validDram = api.parseDram({ observations: [{ product_name: 'DDR5 Fixture', date: '2026-06-10', values: { average: 42 } }] }, { series: [{ product_name: 'DDR5 Fixture', representative: true }] }, { generated_at: '2026-06-10T00:00:00Z' });
assert(validDram.series.length === 1 && validDram.series[0].points.length === 1, 'recorded valid DRAM fixture produces chart series');

const validBest = api.parseBestFactor({ summary: { best_factor: 'quality', data_end_date: '2026-06-10' }, latest_holdings: [{ factor: 'quality', ticker: 'BBB', score: 1, weight: 0.3, rebalance_date: '2026-06-01' }] });
assert(validBest.rows.length === 1 && validBest.factor === 'quality', 'recorded valid Best Factor fixture produces holding row');

assert(Object.keys(api.PANEL_ADAPTERS).length === 3, 'panel adapter manifest has three current adapters');


const nullEntryMomentum = api.parseMomentum({ runs: [{ summary: { selected_factor: 'null_drift' }, latest_output_rows: [null, 'bad'], holdings: [null] }], latest_run_index: 0 });
const nullMomentumState = fallbackFor(nullEntryMomentum, nullEntryMomentum.rows.length > 0, 'Momentum payload did not contain usable top rows.');
assert(nullMomentumState.mode === 'fallback', 'Momentum null/non-object entries resolve to fallback without throwing');

const nullEntryDram = api.parseDram({ observations: [null, 'bad', { product_name: 'Bad date', date: 'not-a-date', values: { average: 1 } }] }, { series: [null] }, {});
const nullDramState = fallbackFor(nullEntryDram, nullEntryDram.series.length > 0, 'DRAM payload did not contain usable dated price points.');
assert(nullDramState.mode === 'fallback', 'DRAM null/non-object entries resolve to fallback without throwing');

const nullEntryBest = api.parseBestFactor({ summary: { best_factor: 'null_drift' }, rankings: [null], latest_holdings: [null, 'bad'] });
const nullBestState = fallbackFor(nullEntryBest, nullEntryBest.rows.length > 0, 'Best Factor payload did not contain usable holdings.');
assert(nullBestState.mode === 'fallback', 'Best Factor null/non-object entries resolve to fallback without throwing');

const throwingAdapter = { parse: () => { throw new Error('fixture boom'); } };
const safeParse = api.parsePanelSafely(throwingAdapter, {});
assert(safeParse.ok === false && /Payload parse failed/.test(safeParse.error), 'panel parser exceptions convert to explicit fallback reason');


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
};
context.Node = ElementStub;
context.document = {
  querySelector: (selector) => domTargets[selector] || null,
  createElement: (tagName) => new ElementStub(tagName),
  addEventListener: () => {},
};
api.renderProjectNavigation();
api.renderDashboardPanels();
assert(domTargets['#top-nav'].children.length === 3, 'manifest renderer creates top navigation links');
assert(domTargets['#hero-actions'].children.length === 3, 'manifest renderer creates hero action links');
assert(domTargets['#summary-grid'].children.length === 3, 'manifest renderer creates three dashboard panel shells');
assert(domTargets['#summary-grid'].children.every((child) => /원본 열기/.test(child.innerHTML)), 'dashboard panel shells preserve original page links');

const failed = checks.filter((check) => !check.ok);
for (const check of checks) console.log(`${check.ok ? 'PASS' : 'FAIL'} ${check.label}`);
if (failed.length) {
  console.error(`\n${failed.length} regression check(s) failed.`);
  process.exit(1);
}
console.log(`\n${checks.length} regression checks passed.`);
