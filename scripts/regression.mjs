import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const source = readFileSync('assets/app.js', 'utf8');
const context = vm.createContext({ console, URL });
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

const malformedSox = api.parseSox({ schemaVersion: 1, contract: 'quant-research-summary', projectId: 'sox', status: 'ok', primaryEntities: [null, { metrics: { score: 0.2 } }] });
const soxState = fallbackFor(malformedSox, malformedSox.rows.length > 0, 'SOX summary did not contain usable constituents.');
assert(soxState.mode === 'fallback', 'HTTP 200 malformed SOX summary resolves to fallback mode');
assert(/SOX summary/.test(soxState.error), 'SOX fallback keeps explicit schema reason');

const validMomentum = api.parseMomentum({ runs: [{ summary: { selected_factor: 'mom_valid', data_as_of: '2026-06-10' }, latest_output_rows: [{ rank: 1, symbol: 'AAA', score: 2, proposed_weight: 0.2, weight: 0.1 }] }], latest_run_index: 0 });
assert(validMomentum.rows.length === 1 && validMomentum.factor === 'mom_valid', 'recorded valid Momentum fixture produces top row');

const selectedVsBestMomentumSummary = {
  schemaVersion: 1,
  contract: 'quant-research-summary',
  projectId: 'momentum',
  generatedAt: '2026-06-18T00:00:00Z',
  dataAsOf: '2026-06-18',
  status: { state: 'ok', label: 'Research signals (not tradable)' },
  highlights: [{ label: 'Selected factor', value: 'selected_mom' }],
  primaryEntities: [{ symbol: 'SEL', metrics: { rank: 1, signal: 9, displayWeight: 0, finalWeight: 0 } }],
  limitations: ['fixture limitation'],
};
const selectedVsBestMomentum = api.parseMomentum(selectedVsBestMomentumSummary, {
  generated_at_utc: '2026-06-18T00:05:00Z',
  latest_run_index: 0,
  runs: [{
    generated_at_utc: '2026-06-18T00:05:00Z',
    summary: { selected_factor: 'selected_mom', data_as_of: '2026-06-18', recommendation_output_label: 'Research signals (not tradable)' },
    factor_leaders: [{ date: '2026-06-18', window: '1Y', window_label: '최근 1년', best_factor: 'best_mom', selected_factor: 'selected_mom' }],
    latest_output_rows: [{ rank: 1, symbol: 'SEL', score: 9, proposed_weight: 0.9, weight: 0.9 }],
    holdings: [
      { date: '2026-06-18', window: '1Y', factor: 'best_mom', rank: 1, symbol: 'BST', score: 4, default_weight: 0.4, weight: 0.4 },
      { date: '2026-06-18', window: '6M', factor: 'best_mom', rank: 1, symbol: 'DUP', score: 3, default_weight: 0.3, weight: 0.3 },
      { date: '2026-06-18', window: '1Y', factor: 'selected_mom', rank: 1, symbol: 'SEL', score: 9, default_weight: 0.9, weight: 0.9 },
    ],
  }],
});
assert(selectedVsBestMomentum.factor === 'best_mom' && selectedVsBestMomentum.rows[0].symbol === 'BST', 'Momentum summary uses best factor dashboard holdings instead of selected-factor rows');
assert(!selectedVsBestMomentum.rows.some((row) => row.symbol === 'SEL' || row.symbol === 'DUP') && /best momentum factor/.test(selectedVsBestMomentum.status), 'Momentum best-factor rows respect the leader window and keep status evidence');
const missingBestDetailMomentum = api.parseMomentum(selectedVsBestMomentumSummary, null);
assert(missingBestDetailMomentum.bestFactorUnavailable && missingBestDetailMomentum.rows.length === 0, 'Momentum missing dashboard detail becomes explicit unavailable state instead of selected-factor rows');
assert(!/selected_mom/.test(`${missingBestDetailMomentum.factor} ${missingBestDetailMomentum.status}`) && /best factor로 표시하지 않음/.test(missingBestDetailMomentum.status), 'Momentum missing dashboard detail does not label selected factor as best');
const weakBestDetailMomentum = api.parseMomentum(selectedVsBestMomentumSummary, {
  runs: [{ summary: { selected_factor: 'selected_mom', data_as_of: '2026-06-18' }, latest_output_rows: [] }],
  latest_run_index: 0,
});
assert(weakBestDetailMomentum.bestFactorUnavailable && weakBestDetailMomentum.rows.length === 0, 'Momentum weak dashboard detail does not mask usable summary as best-factor output');
assert(!/selected_mom/.test(`${weakBestDetailMomentum.factor} ${weakBestDetailMomentum.status}`), 'Momentum weak dashboard detail does not label selected factor as best');
const leaderWithoutHoldingsMomentum = api.parseMomentum(selectedVsBestMomentumSummary, {
  runs: [{
    summary: { selected_factor: 'selected_mom', data_as_of: '2026-06-18' },
    factor_leaders: [{ date: '2026-06-18', window: '1Y', best_factor: 'best_mom', selected_factor: 'selected_mom' }],
    latest_output_rows: [{ rank: 1, symbol: 'SEL', score: 9, proposed_weight: 0.9, weight: 0.9 }],
    holdings: [],
  }],
  latest_run_index: 0,
});
assert(leaderWithoutHoldingsMomentum.bestFactorUnavailable && leaderWithoutHoldingsMomentum.factor === 'best_mom', 'Momentum best leader without matching holdings becomes unavailable instead of rendering selected latest rows');
assert(!leaderWithoutHoldingsMomentum.rows.some((row) => row.symbol === 'SEL'), 'Momentum best leader without holdings never displays selected-factor latest output rows');
const noLeaderLatestRowsMomentum = api.parseMomentum(selectedVsBestMomentumSummary, {
  runs: [{
    summary: { selected_factor: 'selected_mom', data_as_of: '2026-06-18' },
    latest_output_rows: [{ rank: 1, symbol: 'SEL', score: 9, proposed_weight: 0.9, weight: 0.9 }],
  }],
  latest_run_index: 0,
});
assert(noLeaderLatestRowsMomentum.bestFactorUnavailable && noLeaderLatestRowsMomentum.factor === 'best factor 확인 필요', 'Momentum dashboard without best leader never treats selected latest rows as best-factor output');
assert(!noLeaderLatestRowsMomentum.rows.some((row) => row.symbol === 'SEL') && !/selected_mom/.test(`${noLeaderLatestRowsMomentum.factor} ${noLeaderLatestRowsMomentum.status}`), 'Momentum dashboard without best leader does not display or label selected-factor data');

const researchOnlyMomentum = api.parseMomentum({
  schemaVersion: 1,
  contract: 'quant-research-summary',
  projectId: 'momentum',
  generatedAt: '2026-06-18T00:00:00Z',
  dataAsOf: '2026-06-18',
  status: { label: 'Research signals (not tradable)' },
  highlights: [{ label: 'Selected factor', value: 'mom_9_1' }],
  primaryEntities: [
    { symbol: 'AAA', metrics: { rank: 1, signal: 3, displayWeight: 0, finalWeight: 0 } },
    { symbol: 'BBB', metrics: { rank: 2, signal: 1, displayWeight: 0, finalWeight: 0 } },
  ],
});
const researchWeightTotal = researchOnlyMomentum.rows.reduce((sum, row) => sum + row.finalWeight, 0);
assert(researchOnlyMomentum.rows[0].displayWeight === 0.75 && researchOnlyMomentum.rows[0].finalWeight === 0.75, 'Momentum research-only zero weights are replaced with signal-normalized dashboard weights');
assert(Math.abs(researchWeightTotal - 1) < 1e-9 && /정규화/.test(researchOnlyMomentum.status), 'Momentum normalized weights sum to one and keep source status explicit');

const validDram = api.parseDram({ observations: [{ product_name: 'DDR5 Fixture', date: '2026-06-10', values: { average: 42 } }] }, { series: [{ product_name: 'DDR5 Fixture', representative: true }] }, { generated_at: '2026-06-10T00:00:00Z' });
assert(validDram.series.length === 1 && validDram.series[0].points.length === 1, 'recorded valid DRAM fixture produces chart series');

const trendforceDram = api.parseDram({
  generated_at: '2026-06-18T00:00:00Z',
  observations: [
    { source: 'memorymarket', cadence: 'weekly', product_id: 'mm-ddr4', product_name: 'MemoryMarket Weekly', date: '2026-06-10', values: { average: 30 } },
    { source: 'memorymarket', cadence: 'weekly', product_id: 'mm-ddr4', product_name: 'MemoryMarket Weekly', date: '2026-06-17', values: { average: 31 } },
    { source: 'trendforce', cadence: 'daily', product_id: 'tf-ddr5', product_name: 'DDR5 Daily', date: '2026-06-17', values: { session_average: 44 } },
    { source: 'trendforce', cadence: 'daily', product_id: 'tf-ddr5', product_name: 'DDR5 Daily', date: '2026-06-18', values: { session_average: 45 } },
  ],
}, { series: [{ source: 'trendforce', cadences: ['daily'], product_id: 'tf-ddr5', product_name: 'DDR5 Daily', representative: true }] }, { generated_at: '2026-06-18T00:00:00Z' });
assert(trendforceDram.series.length === 1 && /TrendForce daily/.test(trendforceDram.series[0].name), 'DRAM parser prioritizes saved TrendForce daily price series over weekly proxies');
assert(trendforceDram.series[0].points.length === 2 && trendforceDram.observationCount === 2, 'DRAM chart uses daily TrendForce observations and counts selected points');
const dramAxisTicks = api.buildDramAxisTicks(4.4543, 5.1234, 5);
assert(dramAxisTicks.length >= 3 && dramAxisTicks.every((tick) => Number.isInteger(tick)), 'DRAM chart y-axis ticks are clean integers for fractional prices');

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
const etfAxisTicks = api.buildEtfPercentAxisTicks(0.044543, 0.0461, 5);
assert(etfAxisTicks.length >= 4 && etfAxisTicks.at(-1) - etfAxisTicks[0] >= 0.04, 'ETF mini chart y-axis expands narrow weight ranges for readability');
assert(etfAxisTicks.every((tick) => Math.abs((tick * 100) - Math.round(tick * 100)) < 1e-9), 'ETF mini chart y-axis uses whole-percent tick labels');
const etfMiniMarkup = api.renderEtfMiniChart(validEtf.rows[0]);
const etfGridYPositions = [...etfMiniMarkup.matchAll(/<line x1="58" x2="658" y1="([0-9.]+)" y2="\1" stroke="#d9e2f1"/g)].map((match) => Number(match[1]));
assert((etfMiniMarkup.match(/stroke="#d9e2f1"/g) || []).length >= 4 && /최근 1개월 비중\(%\)/.test(etfMiniMarkup), 'ETF mini chart renders a taller multi-tick percent axis');
assert(Math.max(...etfGridYPositions) - Math.min(...etfGridYPositions) > 120, 'ETF mini chart percent axis uses the expanded vertical plotting area');

const etfHistoryPayload = api.compactEtfHistoryPayload({
  id: 'etf-fixture',
  latest: { date: '2026-06-30', top10: [{ rank: 1, ticker: 'AAA', weight: 0.1 }] },
  history: Array.from({ length: 47 }, (_, index) => {
    const date = new Date(Date.UTC(2026, 4, 15 + index)).toISOString().slice(0, 10);
    return { date, holdings: [{ rank: 1, ticker: 'AAA', weight: 0.01 + index / 1000 }] };
  }),
}, 31);
assert(etfHistoryPayload.history.every((row) => row.date >= '2026-05-31'), 'ETF compact history keeps only the recent one-month window');

const etfTailPayload = api.compactEtfHistoryTailText([
  '{"message":"partial ranged payload starts inside an older object"}',
  '{"date":"2026-05-30","sourceStatus":"live","queryDate":"2026-05-30","holdings":[{"rank":1,"ticker":"AAA","weight":0.11}]}',
  ',{"date":"2026-06-17","sourceStatus":"live","queryDate":"2026-06-17","holdings":[{"rank":1,"ticker":"AAA","weight":0.12}]}',
  ',{"date":"2026-06-30","sourceStatus":"live","queryDate":"2026-06-30","holdings":[{"rank":1,"ticker":"AAA","weight":0.13}]}]}',
].join(''), { id: 'tail-fixture', shortName: 'Tail ETF', historyCount: 3, availableEndDate: '2026-06-30' }, 31);
assert(etfTailPayload.history.length === 2 && etfTailPayload.history[0].date === '2026-06-17', 'ETF ranged history tail parser extracts complete recent one-month snapshots');

const validEtfWithExternalHistory = api.parseEtfTracking({
  generatedAt: '2026-06-30T00:00:00Z',
  etfs: [{
    id: 'etf-fixture',
    shortName: 'ETF Fixture',
    code: '0000',
    latest: {
      date: '2026-06-30',
      sourceStatus: 'live',
      top10: [{ rank: 1, ticker: 'AAA', name: 'Alpha', weight: 0.21 }],
    },
  }],
}, null, { 'etf-fixture': etfHistoryPayload }, { requested: 1, loaded: 1, failed: 0 });
assert(validEtfWithExternalHistory.rows[0].chartSeries[0].points.length === etfHistoryPayload.history.length, 'ETF parser uses external per-ETF month history for mini charts');
assert(validEtfWithExternalHistory.status.includes('최근 1개월 history 1/1개 로드'), 'ETF parser status reports per-ETF month-history load coverage');
const failedEtfHistoryStatus = api.appendEtfHistoryStatus('ETF fixture status', { requested: 2, loaded: 0, failed: 2, error: 'fixture boom' });
assert(failedEtfHistoryStatus.includes('history 로드 실패') && failedEtfHistoryStatus.includes('fixture boom'), 'ETF history failure status preserves error evidence');
const enrichmentFailure = api.etfHistoryEnrichmentFailure({ etfHistoryManifest: { etfs: [{ id: 'one' }, { id: 'two' }] } }, 'fixture boom');
assert(enrichmentFailure.dataSources.etfHistoryStatus.requested === 2 && enrichmentFailure.dataSources.etfHistoryStatus.failed === 2, 'ETF history enrichment exceptions become visible status counts');
const genericEnrichmentFailure = await api.enrichPanelSources({ enrichSources: async () => { throw new Error('generic boom'); } }, {}, async () => ({}));
assert(genericEnrichmentFailure.fetchResults.enrichment.error.includes('generic boom'), 'generic enrichment exceptions preserve fetch evidence');
assert(api.resolveEtfHistoryUrl('data/history/etf-fixture.json') === 'https://sonchanggi.github.io/etf-tracking/data/history/etf-fixture.json', 'ETF history URL resolver allows same-site per-ETF history JSON');
assert(api.resolveEtfHistoryUrl('https://evil.example/history.json') === '', 'ETF history URL resolver rejects off-site history URLs');

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

const validSox = api.parseSox({
  schemaVersion: 1,
  contract: 'quant-research-summary',
  projectId: 'sox',
  projectName: 'SOX Fixture',
  generatedAt: '2026-06-29T00:00:00Z',
  dataAsOf: '2026-06-26',
  status: 'ok',
  primaryEntities: [
    { id: 'BBB', label: 'BBB', name: 'Beta Semi', metrics: { score: 0.5, weight: 0.2, priceMomentum: 0.4, earningsMomentum: 0.6 }, status: '중립/혼재' },
    { id: 'AAA', label: 'AAA', name: 'Alpha Semi', metrics: { score: 0.9, weight: 0.1, priceMomentum: 0.8, earningsMomentum: 1.0 }, status: '가격·실적 동반 강세' },
  ],
});
assert(validSox.rows.length === 2 && validSox.rows[0].ticker === 'AAA', 'recorded valid SOX fixture sorts summary rows by combined score');
assert(validSox.topWeight.ticker === 'BBB' && validSox.entities.some((entity) => entity.symbol === 'AAA'), 'SOX parser preserves top proxy weight and dossier entities');

const validRiskScore = api.parseRiskScore({
  schemaVersion: 1,
  contract: 'quant-research-summary',
  projectId: 'risk-score',
  generatedAt: '2026-06-30T00:00:00Z',
  dataAsOf: '2026-06-26',
  status: 'Confirmed Red',
  coverage: { entityCount: 1 },
  primaryEntities: [{ id: 'sox-top-risk', symbol: 'NASDAQSOX', metrics: { latestClose: 13203.57, oneDayReturn: -0.01, ohScore: 0, rfScore: 5, topRiskScore: 5, confirmedTopRisk: true, vixClose: 17.2 } }],
  limitations: ['fixture limitation'],
  automation: { cadence: 'daily-after-market-close' },
  riskScore: { current: { date: '2026-06-26', close: 13203.57, oneDayReturn: -0.01, vixClose: 17.2, ohScore: 0, rfScore: 5, topRiskScore: 5, confirmation: true, regime: 'Rebound Failure', actionLabel: 'Confirmed Red', actionLevel: 'confirmed-red', actionText: 'fixture action' } },
});
assert(validRiskScore.current.topRiskScore === 5 && validRiskScore.current.confirmedTopRisk, 'recorded valid Risk Score fixture produces current top-risk row');
assert(validRiskScore.rows.some((row) => row.label === 'RF Score' && /5/.test(row.value)), 'Risk Score parser exposes OH/RF summary rows');

assert(Object.keys(api.PANEL_ADAPTERS).length === 7, 'panel adapter manifest has seven current adapters including Risk Score');
const riskScoreAdapter = api.PANEL_ADAPTERS.riskScore;
assert(Boolean(riskScoreAdapter?.sourceUrls?.summary?.includes('/quant-dashboard/risk-score/data/risk-score/risk_score_summary.json')), 'Risk Score adapter exposes public summary source URL');
assert(typeof riskScoreAdapter?.parse === 'function', 'Risk Score adapter exposes parser function');
assert(typeof riskScoreAdapter?.render === 'function', 'Risk Score adapter exposes renderer function');
assert(typeof riskScoreAdapter?.fallback === 'function', 'Risk Score adapter exposes fallback function');
assert(typeof riskScoreAdapter?.hasUsableData === 'function' && riskScoreAdapter.hasUsableData(validRiskScore), 'Risk Score adapter has usable-data predicate for parsed summary');
assert(riskScoreAdapter.fallback().current.topRiskScore === 5, 'Risk Score adapter fallback returns current score snapshot');
const incompleteRiskScore = api.parseRiskScore({
  schemaVersion: 1,
  contract: 'quant-research-summary',
  projectId: 'risk-score',
  generatedAt: '2026-06-30T00:00:00Z',
  dataAsOf: '2026-06-26',
  status: 'schema drift',
  primaryEntities: [{ id: 'sox-top-risk', symbol: 'NASDAQSOX', metrics: {} }],
  riskScore: { current: { date: '2026-06-26' } },
});
assert(!riskScoreAdapter.hasUsableData(incompleteRiskScore), 'Risk Score adapter rejects incomplete score metrics as unusable data');
const incompleteRiskState = fallbackFor(incompleteRiskScore, riskScoreAdapter.hasUsableData(incompleteRiskScore), 'Risk Score summary did not contain usable current score metrics.');
assert(incompleteRiskState.mode === 'fallback' && /Risk Score summary/.test(incompleteRiskState.error), 'Risk Score incomplete payload resolves to explicit fallback mode');

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

const nullEntrySox = api.parseSox({ schemaVersion: 1, contract: 'quant-research-summary', projectId: 'sox', status: 'ok', primaryEntities: [null, 'bad', { id: 'DDD', metrics: { score: 0.1 } }] });
assert(nullEntrySox.rows.length === 1 && nullEntrySox.rows[0].ticker === 'DDD', 'SOX null/non-object entries resolve without throwing');

const throwingAdapter = { parse: () => { throw new Error('fixture boom'); } };
const safeParse = api.parsePanelSafely(throwingAdapter, {});
assert(safeParse.ok === false && /Payload parse failed/.test(safeParse.error), 'panel parser exceptions convert to explicit fallback reason');
const contractMismatch = api.validateAdapterContract(api.PANEL_ADAPTERS.valuation, { summary: { schemaVersion: 999, contract: 'quant-research-summary', projectId: 'valuation', status: {}, primaryEntities: [] } });
assert(/expected 1/.test(contractMismatch), 'contract version mismatch is rejected before parsing');

const summaryFixture = {
  schemaVersion: 1,
  contract: 'quant-research-summary',
  projectId: 'valuation',
  projectName: 'Valuation Fixture',
  generatedAt: '2026-06-19T00:00:00Z',
  dataAsOf: '2026-06-18',
  status: { state: 'ok', label: 'fixture', cadence: 'manual', expectedFreshnessDays: 14 },
  coverage: { entityCount: 1, sectors: ['기술'] },
  primaryEntities: [{
    symbol: 'NVDA',
    name: 'NVIDIA',
    label: 'NVDA · 기술',
    sectorLabel: '기술',
    themes: ['AI', 'Semiconductors'],
    metrics: { price: 100, dcfPerShare: 120, qualityStatus: '충분', priceAsOf: '2026-06-18' },
    warnings: ['상대가치 비교군 확인 필요'],
  }],
  limitations: ['모형은 판단 주체가 아니라 계산 보조 도구입니다.'],
  automation: { workflowUrl: 'https://github.com/SonChangGi/valuation/actions/workflows/data-refresh.yml' },
};
assert(api.isResearchSummary(summaryFixture, 'valuation'), 'summary fixture satisfies common contract helper');

assert(api.safeAutomationUrl('https://github.com/SonChangGi/valuation/actions/workflows/data-refresh.yml').startsWith('https://github.com/'), 'automation URL allowlist accepts GitHub HTTPS links');
assert(api.safeAutomationUrl('javascript:alert(1)') === '', 'automation URL allowlist rejects javascript scheme');
assert(api.safeAutomationUrl('https://evil.example/actions') === '', 'automation URL allowlist rejects unexpected hosts');
const parsedSummaryValuation = api.parseValuation(summaryFixture);
assert(parsedSummaryValuation.rows.length === 1 && parsedSummaryValuation.rows[0].ticker === 'NVDA', 'Valuation summary contract parses into panel rows');
const dossierMatches = api.watchlistMatchesForToken([
  { project: { id: 'valuation', shortName: 'Valuation' }, summary: parsedSummaryValuation },
], 'AI');
assert(dossierMatches.length === 1 && /비교군/.test(dossierMatches[0].limit), 'watchlist dossier uses summary entities and limitation text without duplicate legacy rows');

const etfEntityDossier = api.watchlistMatchesForToken([
  { project: api.PROJECTS.find((project) => project.id === 'etf'), summary: { meta: { statusState: 'ok' }, entities: [
    { symbol: 'AAA', label: 'AAA · ETF One', metrics: { etf: 'ETF One', weight: 0.1, date: '2026-06-18' }, warnings: ['ETF One warning'] },
    { symbol: 'AAA', label: 'AAA · ETF Two', metrics: { etf: 'ETF Two', weight: 0.2, date: '2026-06-18' }, warnings: ['ETF Two warning'] },
  ] } },
], 'AAA');
assert(etfEntityDossier.length === 2, 'ETF dossier identity preserves same ticker across ETF contexts');


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
assert(domTargets['#top-nav'].children.length === 8, 'manifest renderer creates top navigation links including SOX, Risk Score, and Port');
assert(domTargets['#hero-actions'].children.length === 8, 'manifest renderer creates hero action links including SOX, Risk Score, and Port');
assert(domTargets['#summary-grid'].children.length === 7, 'manifest renderer creates seven dashboard panel shells including SOX and Risk Score');
assert(domTargets['#summary-grid'].children.every((child) => /원본 열기/.test(child.innerHTML)), 'dashboard panel shells preserve original page links');
assert(domTargets['#summary-grid'].children.some((child) => /panel-detail/.test(child.innerHTML)), 'ETF panel shell includes detail mount for TOP10 cards');
assert(domTargets['#summary-grid'].children.some((child) => /SOX 구성종목/.test(child.innerHTML)), 'SOX panel shell appears in the central summary grid');
api.renderEtfDetailCards('#etf-details', validEtf.rows);
assert(/etf-detail-card/.test(domTargets['#etf-details'].innerHTML), 'ETF detail renderer creates per-ETF card markup');
assert(/AAA/.test(domTargets['#etf-details'].innerHTML) && /BBB/.test(domTargets['#etf-details'].innerHTML), 'ETF detail renderer includes TOP10 holdings');
assert(/TOP10 비중 변화 미니 그래프/.test(domTargets['#etf-details'].innerHTML), 'ETF detail renderer includes mini chart markup');


const staleByDataAsOfRecord = {
  project: api.PROJECTS.find((project) => project.id === 'best'),
  summary: {
    generatedAt: new Date().toISOString(),
    dataEndDate: '2000-01-01',
    meta: { dataAsOf: '2000-01-01', expectedFreshnessDays: 7 },
    rows: [],
  },
  mode: 'live',
  generatedAt: new Date().toISOString(),
};
assert(api.recordFreshnessDate(staleByDataAsOfRecord) === '2000-01-01', 'data health freshness source prefers dataAsOf/dataEndDate over generatedAt');
assert(api.isRecordStale(staleByDataAsOfRecord), 'data health marks a stale dataAsOf as stale even when generatedAt is fresh');
assert(/기준일/.test(api.recordFreshnessText(staleByDataAsOfRecord)), 'data health text names the data 기준일 used for staleness');

const records = [
  { project: api.PROJECTS.find((project) => project.id === 'momentum'), summary: selectedVsBestMomentum, mode: 'live', generatedAt: selectedVsBestMomentum.generatedAt, payloadBytes: 13000, sourceCount: 2 },
  { project: api.PROJECTS.find((project) => project.id === 'sox'), summary: validSox, mode: 'live', generatedAt: validSox.generatedAt, payloadBytes: 6000, sourceCount: 1 },
  { project: api.PROJECTS.find((project) => project.id === 'valuation'), summary: validValuation, mode: 'live', generatedAt: validValuation.generatedAt, payloadBytes: 12000, sourceCount: 1 },
  { project: api.PROJECTS.find((project) => project.id === 'etf'), summary: validEtf, mode: 'live', generatedAt: validEtf.generatedAt, payloadBytes: 90000, sourceCount: 1 },
];
api.renderResearchBriefing(records);
api.renderDataHealth(records);
assert(/Valuation/.test(domTargets['#research-briefing'].innerHTML), 'research briefing renders valuation item');
assert(/SOX/.test(domTargets['#research-briefing'].innerHTML) && /AAA/.test(domTargets['#research-briefing'].innerHTML), 'research briefing renders SOX central summary item');
assert(/best_mom/.test(domTargets['#research-briefing'].innerHTML) && !/selected_mom/.test(domTargets['#research-briefing'].innerHTML), 'research briefing renders Momentum from best factor rather than selected factor');
assert(/live/.test(domTargets['#data-health'].innerHTML), 'data health renders live state');
assert(/Portfolio snapshot/.test(domTargets['#data-health'].innerHTML), 'data health renders portfolio freshness snapshot');
const mixedFreshness = api.portfolioFreshnessSummary([
  { project: { shortName: 'A' }, summary: { dataAsOf: '2026-06-22' }, generatedAt: '2026-06-23T00:00:00Z' },
  { project: { shortName: 'B' }, summary: { dataAsOf: '2026-06-23' }, generatedAt: '2026-06-23T00:00:00Z' },
]);
assert(mixedFreshness.mixed && mixedFreshness.label.includes('혼합 기준일'), 'portfolio freshness snapshot flags mixed project dates');
assert(api.watchlistMatchesForToken(records, 'AAA').length >= 3, 'watchlist matcher connects valuation, ETF, and SOX ticker exposure');
assert(api.parseWatchlistTokens('NVDA, AMD DRAM').join('|') === 'NVDA|AMD|DRAM', 'watchlist token parser handles commas and spaces');

const failed = checks.filter((check) => !check.ok);
for (const check of checks) console.log(`${check.ok ? 'PASS' : 'FAIL'} ${check.label}`);
if (failed.length) {
  console.error(`\n${failed.length} regression check(s) failed.`);
  process.exit(1);
}
console.log(`\n${checks.length} regression checks passed.`);
