import { readFileSync, statSync } from 'node:fs';

const files = {
  html: readFileSync('index.html', 'utf8'),
  css: readFileSync('assets/styles.css', 'utf8'),
  app: readFileSync('assets/app.js', 'utf8'),
  readme: readFileSync('README.md', 'utf8'),
  design: readFileSync('DESIGN.md', 'utf8'),
  webDesign: readFileSync('docs/web-design.md', 'utf8'),
  commonDesign: readFileSync('docs/common-design-v1.md', 'utf8'),
  commonDesignPrompt: readFileSync('docs/common-design-v1-rollout-prompt.md', 'utf8'),
  packageJson: readFileSync('package.json', 'utf8'),
  liveSmoke: readFileSync('scripts/live-contract-smoke.mjs', 'utf8'),
  riskSyncWorkflow: readFileSync('.github/workflows/sync-risk-score.yml', 'utf8'),
};

const checks = [];
const assert = (condition, label) => checks.push({ label, ok: Boolean(condition) });
const contains = (file, needle) => file.includes(needle);

for (const path of ['index.html', 'assets/styles.css', 'assets/app.js', 'DESIGN.md', 'docs/web-design.md', 'docs/common-design-v1.md', 'docs/common-design-v1-rollout-prompt.md', 'scripts/verify.mjs', 'scripts/regression.mjs', 'scripts/static-smoke.mjs', 'scripts/live-contract-smoke.mjs', '.github/workflows/sync-risk-score.yml', 'package.json']) {
  assert(statSync(path).isFile(), `${path} exists`);
}

const projectUrls = [
  'https://sonchanggi.github.io/fearNgreed/',
  'https://sonchanggi.github.io/momentum-factor-lab/',
  'https://sonchanggi.github.io/dram-price/',
  'https://sonchanggi.github.io/best-factor/',
  'https://sonchanggi.github.io/etf-tracking/',
  'https://sonchanggi.github.io/sox/',
  'https://sonchanggi.github.io/quant-dashboard/risk-score/',
  'https://sonchanggi.github.io/valuation/',
  'https://sonchanggi.github.io/port/',
  'https://sonchanggi.github.io/kelly/',
];
for (const url of projectUrls) {
  assert(contains(files.html, url) || contains(files.app, url), `project URL present: ${url}`);
}

const dataUrls = [
  'https://sonchanggi.github.io/fearNgreed/data/summary.json',
  'https://sonchanggi.github.io/momentum-factor-lab/data/summary.json',
  'https://sonchanggi.github.io/momentum-factor-lab/data/dashboard.json',
  'https://sonchanggi.github.io/dram-price/data/summary.json',
  'https://sonchanggi.github.io/dram-price/data/prices.json',
  'https://sonchanggi.github.io/dram-price/data/series.json',
  'https://sonchanggi.github.io/dram-price/data/status.json',
  'https://sonchanggi.github.io/best-factor/data/summary.json',
  'https://sonchanggi.github.io/etf-tracking/data/summary.json',
  'https://sonchanggi.github.io/etf-tracking/data/dashboard.json',
  'https://sonchanggi.github.io/etf-tracking/data/history.json',
  'https://sonchanggi.github.io/sox/data/summary.json',
  'https://sonchanggi.github.io/quant-dashboard/risk-score/data/risk-score/risk_score_summary.json',
  'https://sonchanggi.github.io/valuation/data/summary.json',
  'https://sonchanggi.github.io/kelly/data/summary.json',
];
for (const url of dataUrls) {
  assert(contains(files.app, url), `public data endpoint present: ${url}`);
}

assert(contains(files.app, 'const PROJECTS = ['), 'project registry exists');
assert(contains(files.app, "id: 'port'"), 'port project registry entry exists');
assert(contains(files.app, "id: 'kelly'"), 'Kelly project registry entry exists');
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
assert(contains(files.app, 'parseFearAndGreed'), 'Fear & Greed parser exists');
assert(contains(files.app, 'normalizeFearAndGreedUnavailable'), 'Fear & Greed uses unavailable rather than hardcoded market fallback');
assert(contains(files.app, "id: 'fearngreed'"), 'Fear & Greed project registry entry exists');
assert(contains(files.app, 'MOMENTUM_SUMMARY_CONTRACT') && contains(files.app, 'expectedVersion: 5'), 'momentum adapter requires schemaVersion 5 summary contract');
assert(contains(files.app, 'bestFactor') && contains(files.app, 'compositeScore'), 'momentum adapter reads Python best factor and composite score fields');
assert(contains(files.app, 'weightingPolicy') && contains(files.app, 'bestFactorReason'), 'momentum adapter reads the fixed weighting method and Python best-factor reason');
assert(contains(files.app, 'researchOnly') && contains(files.app, 'notInvestmentRecommendation'), 'momentum adapter requires research-only safety flags');
assert(contains(files.app, 'dataMode') && contains(files.app, 'sourceLabel') && contains(files.app, 'evidenceStatus'), 'momentum adapter preserves data mode, source, and evidence status');
assert(contains(files.app, '실제 시장 데이터') && contains(files.app, '합성 데모') && contains(files.app, '로컬 연구 데이터'), 'momentum consumer exposes explicit actual-market, demo, and local research-data labels');
assert(contains(files.app, 'same_sample_descriptive_actual_market'), 'momentum consumer recognizes actual-market descriptive evidence');
assert(contains(files.app, 'matchingMomentumContractValue') && contains(files.app, 'weightingPolicyId') && contains(files.app, 'currentTarget?.asOf') && contains(files.app, 'currentTarget?.signalDate'), 'momentum consumer fails closed on factor, policy, as-of, and signal-date parity conflicts');
assert(contains(files.app, 'matchingMomentumResultIdentity') && contains(files.app, 'validMomentumResultIdentity') && contains(files.app, 'resultIdentity.resultKey'), 'momentum consumer fails closed on full resultIdentity and resultKey parity conflicts');
assert(contains(files.app, 'MOMENTUM_RESULT_IDENTITY_VERSION') && contains(files.app, 'LOWERCASE_SHA256') && contains(files.app, 'canonicalKeyPartsJson') && contains(files.app, 'momentumSha256Hex'), 'momentum consumer requires the supported identity version and recomputes canonical lowercase SHA-256 result keys');
assert(contains(files.app, 'validMomentumMarketSnapshotParity') && contains(files.app, 'priceBasis') && contains(files.app, 'volumeBasis') && contains(files.app, 'rawCloseProxySymbolCount'), 'momentum consumer binds the hardened result identity market snapshot to dashboard data');
assert(contains(files.app, 'validMomentumLiveProvenance') && contains(files.app, 'priceSources') && contains(files.app, 'sourceHealth') && contains(files.app, 'MOMENTUM_LIVE_SNAPSHOT_HASH_FIELDS_V5') && contains(files.app, "'marketCaps'") && contains(files.app, "'marketCapSources'"), 'momentum consumer requires live provider provenance and the schema-v5 market-cap snapshot hashes');
assert(contains(files.app, 'momentumCanonicalRecordsSha256') && contains(files.app, 'hashes.priceSources !== momentumCanonicalRecordsSha256(priceSources)') && contains(files.app, 'hashes.dataSources !== momentumCanonicalRecordsSha256(sourceHealth)'), 'momentum consumer recomputes RFC 8785 JCS SHA-256 for live priceSources and sourceHealth records');
assert(contains(files.app, 'analyzedSymbols') && contains(files.app, 'candidateSymbolsSha256') && contains(files.app, 'momentumCanonicalKeyPartsJson(analyzedSymbols)'), 'momentum consumer binds the exact ordered analyzed-symbol universe to the result identity');
assert(contains(files.app, 'validMomentumFactorGridV5') && contains(files.app, 'factorCount: 64') && contains(files.app, 'independentFactorCount: 61') && contains(files.app, 'aliasFactorCount: 3') && contains(files.app, 'totalFactorRunCount: 64'), 'momentum consumer enforces the schema-v5 64/61/3 single-method factor grid');
assert(contains(files.app, 'MOMENTUM_ABSOLUTE_GUARDRAIL_RULES') && contains(files.app, 'expectedMomentumAbsoluteGuardrailProfile') && contains(files.app, 'validMomentumAbsoluteGuardrailProfile'), 'momentum consumer reconstructs the canonical full absolute guardrail profile');
assert(contains(files.app, 'MOMENTUM_REQUIRED_GUARDRAIL_CONTRACTS') && contains(files.app, 'extremeEventAction') && contains(files.app, 'extremeEventPenaltyPoints') && contains(files.app, 'momentumCanonicalKeyPartsJson(actual) === momentumCanonicalKeyPartsJson(expected)'), 'momentum consumer requires exact 12-rule metadata, required contracts, action, penalty, and ordered rule equality');
assert(contains(files.app, 'validMomentumConcentrationRows') && contains(files.app, 'payload.factorRanking ?? payload.factorPolicyRanking') && contains(files.app, 'guardrail_historical_effective_names') && contains(files.app, 'guardrail_current_target_weight'), 'momentum consumer recomputes six historical/current concentration flags for all 64 schema-v5 ranking rows');
assert(contains(files.app, 'validMomentumSelectedConcentrationContract') && contains(files.app, "selected.selection_status !== 'eligible'") && contains(files.app, 'selected.selection_eligible !== true') && contains(files.app, 'selected.absolute_guardrail_pass !== true') && contains(files.app, 'momentumFiniteNumber(selected.selection_score)') && contains(files.app, 'selected[rule.flag] !== true'), 'momentum consumer requires the selected winner, finite selection score, and all six concentration guards to pass');
assert(contains(files.app, 'matchingMomentumAllocations') && contains(files.app, 'summaryAllocation.cashWeight') && contains(files.app, 'summaryAllocation.maxWeight'), 'momentum consumer fails closed on summary/dashboard holding, cash, and max-weight parity conflicts');
assert(contains(files.app, 'bestFactorPortfolio') && contains(files.app, 'summaryTarget') && contains(files.app, 'dashboardTarget'), 'momentum consumer checks summary/dashboard Python bestFactorPortfolio parity');
assert(contains(files.app, 'validateMomentumAllocation') && contains(files.app, 'symbols.has(symbolKey)') && contains(files.app, 'Math.abs(totalWeight - 1)'), 'momentum consumer validates duplicate symbols and the weights-plus-cash contract');
assert(contains(files.app, 'row.modelWeight > maxWeight') && contains(files.app, 'row.modelWeight < 0'), 'momentum consumer rejects cap violations and negative weights');
assert(contains(files.app, 'appendMomentumContractConflict') && contains(files.app, "'data_mode'"), 'momentum consumer keeps supported metadata conflicts visible');
assert(contains(files.app, 'momentumDashboard') && contains(files.app, 'momentumRowsFromModelWeights'), 'momentum adapter loads schema-v5 model holdings');
assert(contains(files.app, 'dashboard.bestFactorPortfolio.weights') && contains(files.app, 'weightingPolicyId'), 'momentum dashboard parser consumes the Python best-factor portfolio');
assert(contains(files.app, '모델 비중'), 'momentum allocation column uses the model-weight label');
assert(!contains(files.app, 'latest_output_rows') && !contains(files.app, 'production_recommendation'), 'retired momentum output and production allocation fields are not consumed');
assert(!contains(files.app, 'deriveMomentumDisplayWeights') && !contains(files.app, 'securityId'), 'momentum consumer does not synthesize weights or require PIT identity fields');
assert(!contains(files.app, 'FALLBACK_SNAPSHOT.momentum'), 'momentum consumer never renders a hardcoded fallback snapshot');
assert(contains(files.app, 'parseDram'), 'DRAM parser exists');
assert(contains(files.app, 'renderDramChart'), 'DRAM SVG chart renderer exists');
assert(contains(files.app, 'buildDramAxisTicks'), 'DRAM chart uses clean integer y-axis ticks');
assert(contains(files.app, 'TrendForce daily'), 'DRAM chart prioritizes saved TrendForce daily prices');
assert(contains(files.app, 'D램 가격'), 'Korean D램 price label exists');
assert(contains(files.app, 'isValidChartPoint'), 'DRAM chart validates date/value points');
assert(contains(files.app, 'parseBestFactor'), 'best factor parser exists');
assert(contains(files.app, 'parseEtfTracking'), 'ETF Tracking parser exists');
assert(contains(files.app, 'parseSox'), 'SOX summary parser exists');
assert(contains(files.app, 'renderSox'), 'SOX dashboard panel renderer exists');
assert(contains(files.app, 'SOX 구성종목 · Momentum Top 5'), 'SOX central summary panel copy exists');
assert(contains(files.app, 'parseRiskScore'), 'Risk Score summary parser exists');
assert(contains(files.app, 'renderRiskScore'), 'Risk Score dashboard panel renderer exists');
assert(contains(files.app, "riskScore: {\n      sourceUrls") && contains(files.app, "parse: (sources) => parseRiskScore(sources.summary)") && contains(files.app, "fallback: normalizeRiskScoreFallback"), 'Risk Score adapter keeps source/parse/fallback contract');
assert(contains(files.app, 'SOX Top Risk · OH/RF/Confirmation'), 'Risk Score central summary panel copy exists');
assert(contains(files.app, "id: 'risk-score'"), 'Risk Score project registry entry exists');
assert(contains(files.app, 'parseValuation'), 'Valuation parser exists');
assert(contains(files.app, 'parseKelly') && contains(files.app, 'renderKelly'), 'Kelly parser and panel renderer exist');
assert(contains(files.app, 'normalizeKellyUnavailable'), 'Kelly fetch or contract failure stays unavailable without hardcoded calculation values');
assert(contains(files.app, "expectedProjectId: 'kelly'") && contains(files.app, 'KELLY_SUMMARY_CONTRACT'), 'Kelly adapter requires its own project identity and coverage contract');
assert(contains(files.app, "kelly: {\n      sourceUrls") && contains(files.app, "parse: (sources) => parseKelly(sources.summary)"), 'Kelly adapter reads only its public summary contract');
assert(contains(files.app, 'ETF별 TOP10 비중'), 'ETF Tracking detail panel label exists');
assert(contains(files.app, '최근 1개월 비중 변화'), 'ETF Tracking chart copy names the one-month history window');
assert(contains(files.app, 'enrichEtfTrackingSources'), 'ETF Tracking adapter loads per-ETF history sources');
assert(contains(files.app, 'compactEtfHistoryPayload'), 'ETF Tracking history is compacted to recent window');
assert(contains(files.app, 'Range') && contains(files.app, 'compactEtfHistoryTailText'), 'ETF Tracking history uses ranged tail reads before full-file fallback');
assert(contains(files.app, 'appendEtfHistoryStatus'), 'ETF Tracking status reports per-ETF history load coverage');
assert(contains(files.app, 'etfHistoryEnrichmentFailure'), 'ETF Tracking history enrichment failures stay visible');
assert(contains(files.app, 'renderEtfDetailCards'), 'ETF Tracking TOP10 detail renderer exists');
assert(contains(files.app, 'renderEtfMiniChart'), 'ETF Tracking mini chart renderer exists');
assert(contains(files.app, 'buildEtfPercentAxisTicks') && contains(files.app, '최근 1개월 비중(%)'), 'ETF mini chart exposes a readable percent y-axis');
assert(contains(files.css, '.etf-detail-grid'), 'ETF Tracking detail grid CSS exists');
assert(contains(files.css, '.etf-top10-list'), 'ETF Tracking TOP10 list CSS exists');
assert(contains(files.app, 'latest_holdings'), 'best factor holdings optional field is handled');
assert(contains(files.app, 'formatFreshness'), 'freshness formatter exists');
assert(contains(files.app, 'renderResearchBriefing'), 'research briefing renderer exists');
assert(contains(files.app, 'renderDataHealth'), 'data health renderer exists');
assert(contains(files.app, 'portfolioFreshnessSummary'), 'data health exposes cross-project freshness coherence');
assert(contains(files.app, 'watchlistMatchesForToken'), 'watchlist matcher exists');
assert(contains(files.app, 'health-link'), 'data health links automation/manual update workflows');
assert(contains(files.app, 'entitySummaryLine'), 'watchlist dossier uses entity-level summary lines');
assert(contains(files.app, '업데이트 시각 알 수 없음'), 'freshness fallback text exists');
assert(contains(files.app, "panelDomId(project, 'status')"), 'manifest-generated freshness/status hooks exist');
assert(contains(files.app, 'status-line'), 'panel status line renderer exists');
assert(contains(files.html, '투자, 세무, 법률 또는 매매 조언이 아닙니다'), 'research disclaimer exists');
assert(contains(files.readme, '다른 프로젝트의 로컬 소스 코드를 직접 import하지 않습니다'), 'README isolation note exists');
assert(contains(files.readme, 'summary.json'), 'README documents summary contract endpoint');
assert(contains(files.readme, 'docs/web-design.md') && contains(files.design, 'docs/web-design.md'), 'README and DESIGN link the canonical web design prompt');
assert(
  [
    'https://sonchanggi.github.io/dram-price/',
    'https://sonchanggi.github.io/fearNgreed/',
    'https://sonchanggi.github.io/etf-tracking/',
    'https://sonchanggi.github.io/sox/',
    'https://sonchanggi.github.io/momentum-factor-lab/',
  ].every((url) => contains(files.webDesign, url)),
  'web design prompt fixes the five-site reference suite',
);
assert(contains(files.webDesign, '## 1. 절대 보호 경계') && contains(files.webDesign, '계산·normalization·selection·aggregation 함수는 동결'), 'web design prompt protects analysis and result behavior');
assert(contains(files.webDesign, '## 13. 기존 페이지 개선 절차') && contains(files.webDesign, '## 14. 신규 프로젝트 구현 절차') && contains(files.webDesign, 'local preview'), 'web design prompt covers existing and new project workflows');
assert(contains(files.webDesign, '## 4. 11개 공통 메뉴') && contains(files.webDesign, 'aria-current="page"') && contains(files.webDesign, 'Quant Research Hub'), 'web design prompt fixes the shared navigation contract');
assert(contains(files.webDesign, '## 9. Table') && contains(files.webDesign, 'tabular') && contains(files.webDesign, '## 10. Chart') && contains(files.webDesign, 'plot 밖 정확값 readout'), 'web design prompt fixes table and chart contracts');
assert(contains(files.webDesign, 'multi-series comparison chart에만') && contains(files.webDesign, 'date-axis chart에만') && contains(files.webDesign, 'bar·quadrant'), 'web design prompt keeps chart interactions domain-conditional');
assert(contains(files.webDesign, 'TDS UI Kit') && contains(files.webDesign, '향후에도 Toss 자료에서 새 값을 직접 가져오지 않는다'), 'web design prompt records the Toss reference and reuse boundary');
assert(contains(files.readme, 'docs/common-design-v1.md'), 'README links the common design v1 contract');
assert(contains(files.design, 'docs/common-design-v1.md'), 'legacy design history links the v1 reference contract');
assert(contains(files.commonDesign, '결과 우선 정보 구조'), 'common design v1 fixes the result-first hierarchy');
assert(contains(files.commonDesign, '프레젠테이션 상태') && contains(files.commonDesign, '분석 상태'), 'common design v1 separates chart exploration from analysis state');
assert(contains(files.commonDesign, '데이터 기준일') && contains(files.commonDesign, '평가 종료일') && contains(files.commonDesign, '차트 선택일'), 'common design v1 names distinct date roles');
assert(contains(files.commonDesign, '390px') && contains(files.commonDesign, '44px'), 'common design v1 declares mobile containment and touch targets');
assert(contains(files.commonDesign, 'quant-research-theme') && contains(files.commonDesign, 'quant-dashboard-theme') && contains(files.commonDesign, 'quant-calm-theme') && contains(files.commonDesign, 'dram-price-theme'), 'common design v1 fixes canonical and legacy theme keys');
assert(contains(files.commonDesign, 'Hub → Fear & Greed → Momentum → DRAM') && contains(files.commonDesign, 'Kelly'), 'common design v1 fixes the project navigation order');
assert(contains(files.commonDesign, 'skip link') && contains(files.commonDesign, '12px'), 'common design v1 fixes keyboard entry and legible dense labels');
assert(contains(files.commonDesign, '프로젝트별 plan-goal'), 'common design v1 requires project-by-project rollout');
assert(contains(files.commonDesign, 'plot 영역 밖') && contains(files.commonDesign, 'absolute overlay'), 'common design v1 keeps exact-value readouts away from plotted marks');
assert(contains(files.commonDesign, '구현 설명') && contains(files.commonDesign, 'actionExplanation'), 'common design v1 removes implementation narration and repeated row explanations');
assert(contains(files.commonDesign, '버전: `1.2.0`') && contains(files.commonDesign, '공통 타이포그래피와 세로 밀도'), 'common design v1.2 fixes the shared typography and density reference');
assert(contains(files.commonDesign, '`15px`, `line-height: 1.55`') && contains(files.commonDesign, '`800` 이상'), 'common design v1.2 fixes the shared type scale and weight hierarchy');
assert(contains(files.commonDesign, '작은 disclaimer') && contains(files.commonDesign, '기본 닫힘 `운영 상세`'), 'common design v1.2 does not exempt fine print from copy reduction');
assert(contains(files.commonDesign, '11개 항목') && contains(files.commonDesign, '완료된 일부 프로젝트나 현재 프로젝트와 Hub만'), 'common design v1.2 requires the complete shared navigation');
assert(contains(files.commonDesign, '승인된 기존 색 토큰·primary·의미색') && contains(files.commonDesign, 'type·series·axis·legend·column·order를 보존'), 'common design v1.2 preserves project-specific visuals and analytical surfaces');
assert(contains(files.commonDesign, '역사적 적용 사례의 도메인 차이(비규범)') && contains(files.commonDesign, '비규범 파일럿 근거'), 'common design v1.2 keeps pilot projects as evidence rather than normative templates');
assert(contains(files.readme, 'docs/common-design-v1-rollout-prompt.md') && contains(files.design, 'docs/common-design-v1-rollout-prompt.md'), 'README and DESIGN link the rollout prompt');
assert(contains(files.commonDesignPrompt, '프로젝트별 plan-goal') && contains(files.commonDesignPrompt, 'Python 수집·분석·전략') && contains(files.commonDesignPrompt, '공개 JSON schema') && contains(files.commonDesignPrompt, 'workflow·GitHub Pages URL'), 'rollout prompt preserves project-by-project analysis, data, and deployment boundaries');
assert(contains(files.commonDesignPrompt, 'plot 밖의 고정 행') && contains(files.commonDesignPrompt, '구현 설명') && contains(files.commonDesignPrompt, 'bounding box'), 'rollout prompt requires copy reduction and chart collision QA');
assert(contains(files.commonDesignPrompt, 'Quant Research 공통 디자인 v1.2') && contains(files.commonDesignPrompt, '공통 타이포그래피와 밀도') && contains(files.commonDesignPrompt, '통일성의 범위'), 'rollout prompt applies the shared visual reference');
assert(contains(files.commonDesignPrompt, '`15px / 1.55`') && contains(files.commonDesignPrompt, '`800` 이상'), 'rollout prompt carries the compact type and weight rules');
assert(contains(files.commonDesignPrompt, 'Hub → Fear & Greed → Momentum → DRAM') && contains(files.commonDesignPrompt, '정확히 11개'), 'rollout prompt requires the full registry-driven top navigation');
assert(contains(files.commonDesignPrompt, 'sticky shell 약 `58px`') && contains(files.commonDesignPrompt, '메뉴 글자 `12px / 650`'), 'rollout prompt carries the compact shared navigation density');
assert(contains(files.commonDesignPrompt, '`데이터 · 출처 · 운영 상세`'), 'rollout prompt consolidates secondary copy in one named closed details section');
assert(contains(files.commonDesignPrompt, '기존 차트 유형·패널·축·범례·계열') && contains(files.commonDesignPrompt, '기존 색 토큰'), 'rollout prompt preserves project-specific charts, tables, and colors');
assert(contains(files.commonDesignPrompt, '공통 디자인만을 이유로 새 기능') && contains(files.commonDesignPrompt, '수정 전 대상 화면의 computed'), 'rollout prompt preserves existing chart capabilities and records a before baseline');
assert(contains(readFileSync('scripts/regression.mjs', 'utf8'), 'malformed momentum payload resolves to fallback mode'), 'malformed payload regression exists');
assert(contains(readFileSync('scripts/regression.mjs', 'utf8'), 'null/non-object entries resolve to fallback'), 'null-entry payload regression exists');
assert(contains(readFileSync('scripts/static-smoke.mjs', 'utf8'), 'static server smoke'), 'static server smoke exists');
assert(contains(files.packageJson, '"test:live"'), 'package exposes optional live contract smoke');
assert(contains(files.packageJson, '"test:publish"') && contains(files.packageJson, 'npm run test:live'), 'package exposes publish gate with live contract smoke');
assert(contains(files.liveSmoke, 'MAX_PAYLOAD_BYTES') && contains(files.liveSmoke, 'MAX_STALENESS_DAYS'), 'live contract smoke checks payload size and freshness');
assert(contains(files.liveSmoke, 'validateAdapterContract'), 'live contract smoke rejects incompatible contract versions');
assert(contains(files.liveSmoke, 'REQUIRED_PROJECT_COUNT = 9'), 'live contract smoke requires all nine public summary panels');
assert(!contains(files.app, '../momentum-factor-lab') && !contains(files.app, '../dram-price') && !contains(files.app, '../best-factor') && !contains(files.app, '../etf-tracking') && !contains(files.app, '../sox') && !contains(files.app, '../valuation') && !contains(files.app, '../risk-score') && !contains(files.app, '../kelly'), 'no sibling local source paths referenced');
assert(statSync('risk-score/index.html').isFile(), 'Risk Score deploy subtree index exists');
assert(statSync('risk-score/assets/app.js').isFile(), 'Risk Score deploy subtree app asset exists');
assert(statSync('risk-score/data/risk-score/risk_score_summary.json').isFile(), 'Risk Score deploy subtree summary JSON exists');
assert(contains(files.riskSyncWorkflow, 'repository: SonChangGi/risk-score') && contains(files.riskSyncWorkflow, 'path: .source/risk-score'), 'Risk Score mirror workflow checks out the canonical source explicitly');
assert(contains(files.riskSyncWorkflow, 'scripts/verify_data_freshness.py') && contains(files.riskSyncWorkflow, 'scripts/verify_quant_dashboard_sync.py'), 'Risk Score mirror workflow gates publication on source freshness and exact mirror verification');
assert(contains(files.riskSyncWorkflow, 'python3 .source/risk-score/scripts/sync_to_quant_dashboard.py') && contains(files.riskSyncWorkflow, 'npm test'), 'Risk Score mirror workflow builds through the source-owned script and verifies Quant Dashboard');
assert(contains(files.riskSyncWorkflow, 'verify-source:') && contains(files.riskSyncWorkflow, 'publish-mirror:') && contains(files.riskSyncWorkflow, 'needs: verify-source'), 'Risk Score mirror validation and publication use separate dependent jobs');
assert(contains(files.riskSyncWorkflow, 'permissions:\n  contents: read') && contains(files.riskSyncWorkflow, 'permissions:\n      contents: write'), 'Risk Score source validation is read-only and only publication receives write permission');
assert(contains(files.riskSyncWorkflow, 'actions/upload-artifact@') && contains(files.riskSyncWorkflow, 'actions/download-artifact@') && contains(files.riskSyncWorkflow, 'SHA256SUMS'), 'Risk Score mirror crosses the permission boundary as a checksummed artifact');
const actionPins = [...files.riskSyncWorkflow.matchAll(/^\s*uses:\s+([^@\s]+)@([^\s#]+)/gm)];
assert(actionPins.length > 0 && actionPins.every(([, , ref]) => /^[0-9a-f]{40}$/.test(ref)), 'all third-party workflow actions are pinned to full commit SHAs');
const publishJob = files.riskSyncWorkflow.split(/^  publish-mirror:\s*$/m)[1] || '';
assert(!contains(publishJob, '.source/risk-score/scripts/') && !contains(publishJob, 'repository: SonChangGi/risk-score'), 'write-enabled publication job does not execute or check out remote Risk Score source code');
assert(contains(files.riskSyncWorkflow, 'contents: write') && !contains(files.riskSyncWorkflow, 'QUANT_DASHBOARD_TOKEN'), 'Risk Score mirror publication uses the deploy repository token without a cross-repository secret');
assert(contains(files.riskSyncWorkflow, 'quant-dashboard-risk-score-sync') && contains(files.riskSyncWorkflow, 'cancel-in-progress: false'), 'Risk Score mirror workflow serializes scheduled retries');

const failed = checks.filter((check) => !check.ok);
for (const check of checks) {
  console.log(`${check.ok ? 'PASS' : 'FAIL'} ${check.label}`);
}

if (failed.length) {
  console.error(`\n${failed.length} verification check(s) failed.`);
  process.exit(1);
}

console.log(`\n${checks.length} verification checks passed.`);
