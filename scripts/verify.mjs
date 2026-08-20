import { readFileSync, statSync } from 'node:fs';

const files = {
  html: readFileSync('index.html', 'utf8'),
  css: readFileSync('assets/styles.css', 'utf8'),
  sharedNav: readFileSync('assets/shared-nav.css', 'utf8'),
  app: readFileSync('assets/app.js', 'utf8'),
  readme: readFileSync('README.md', 'utf8'),
  design: readFileSync('DESIGN.md', 'utf8'),
  webDesign: readFileSync('docs/web-design.md', 'utf8'),
  commonDesign: readFileSync('docs/common-design-v1.md', 'utf8'),
  commonDesignPrompt: readFileSync('docs/common-design-v1-rollout-prompt.md', 'utf8'),
  platformArchitecture: readFileSync('docs/platform-architecture-v1.md', 'utf8'),
  controlAudit: readFileSync('docs/control-audit-2026-07-24.md', 'utf8'),
  packageJson: readFileSync('package.json', 'utf8'),
  liveSmoke: readFileSync('scripts/live-contract-smoke.mjs', 'utf8'),
  publicHealthPolicy: readFileSync('scripts/public-health-policy.mjs', 'utf8'),
  publicHealthIncident: readFileSync('scripts/public-health-incident.mjs', 'utf8'),
  publicHealthGate: readFileSync('scripts/public-health-gate.mjs', 'utf8'),
  platformFoundationWorkflow: readFileSync('.github/workflows/platform-foundation.yml', 'utf8'),
  publicHealthWorkflow: readFileSync('.github/workflows/public-data-health.yml', 'utf8'),
  pagesWorkflow: readFileSync('.github/workflows/pages.yml', 'utf8'),
};

const checks = [];
const assert = (condition, label) => checks.push({ label, ok: Boolean(condition) });
const contains = (file, needle) => file.includes(needle);

for (const path of ['index.html', 'assets/styles.css', 'assets/shared-nav.css', 'assets/app.js', 'DESIGN.md', 'docs/web-design.md', 'docs/common-design-v1.md', 'docs/common-design-v1-rollout-prompt.md', 'docs/platform-architecture-v1.md', 'docs/control-audit-2026-07-24.md', 'scripts/verify.mjs', 'scripts/regression.mjs', 'scripts/static-smoke.mjs', 'scripts/live-contract-smoke.mjs', 'scripts/public-health-policy.mjs', 'scripts/public-health-incident.mjs', 'scripts/public-health-incident.test.mjs', 'scripts/public-health-gate.mjs', 'scripts/public-health-gate.test.mjs', '.github/workflows/platform-foundation.yml', '.github/workflows/public-data-health.yml', '.github/workflows/pages.yml', 'platform/vercel.json', 'package.json']) {
  assert(statSync(path).isFile(), `${path} exists`);
}

const projectUrls = [
  'https://sonchanggi.github.io/fearNgreed/',
  'https://sonchanggi.github.io/momentum-factor-lab/',
  'https://sonchanggi.github.io/dram-price/',
  'https://sonchanggi.github.io/best-factor/',
  'https://sonchanggi.github.io/etf-tracking/',
  'https://sonchanggi.github.io/sox/',
  'https://sonchanggi.github.io/regime/',
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
  'https://sonchanggi.github.io/regime/data/regime-results.json',
];
for (const url of dataUrls) {
  assert(contains(files.app, url), `public data endpoint present: ${url}`);
}

assert(contains(files.app, 'const PROJECTS = ['), 'project registry exists');
assert(contains(files.app, "id: 'regime'"), 'Regime project registry entry exists');
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
assert(contains(files.html, 'class="skip-link"') && contains(files.html, 'id="main-content"'), 'keyboard users can skip the shared navigation');
assert(
  contains(files.html, 'quant-shared-nav')
    && contains(files.html, 'assets/shared-nav.css')
    && contains(files.sharedNav, 'position: fixed !important')
    && contains(files.sharedNav, '--quant-shared-nav-height: 101px'),
  'shared navigation stays fixed and reserves desktop/mobile document space',
);
assert(
  contains(files.html, 'site-nav-inner quant-shared-nav__inner')
    && contains(files.html, 'id="hub-status-coverage"')
    && contains(files.html, 'id="hub-status-date"')
    && contains(files.html, 'id="hub-status-attention"'),
  'compact shared navigation and results-first Hub status strip exist',
);
assert(
  contains(files.html, '<details class="operations-panel">')
    && contains(files.html, '데이터 · 출처 · 운영 상세')
    && !contains(files.html, 'id="hero-actions"')
    && !contains(files.html, 'id="project-grid"')
    && !contains(files.html, 'roadmap-section'),
  'repeated navigation and explanatory sections are consolidated into one closed operations disclosure',
);
assert(
  contains(files.css, '.site-nav-inner')
    && contains(files.css, 'min-height: 58px')
    && contains(files.css, 'font-size: 15px')
    && contains(files.css, 'line-height: 1.55')
    && contains(files.css, '.skip-link'),
  'shared navigation, typography density, and keyboard entry styles are present',
);
assert(contains(files.app, 'createLinkPanelShell') && contains(files.app, 'renderHubStatus'), 'result-card registry and dynamic Hub status rendering exist');
assert(
  contains(files.html, 'name="quant-supabase-url" content=""')
    && contains(files.html, 'name="quant-supabase-publishable-key" content=""'),
  'optional Supabase metadata connection is disabled by default',
);
assert(contains(files.app, 'FALLBACK_SNAPSHOT'), 'fallback snapshot exists');
assert(contains(files.app, 'getJsonBestEffort'), 'best-effort fetch helper exists');
assert(
  contains(files.app, 'getPublishedSnapshotMetadata')
    && contains(files.app, 'published_project_snapshots')
    && contains(files.app, 'metadataMismatch'),
  'Hub reads optional published metadata while preserving Pages JSON fallback',
);
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
assert(contains(files.app, 'renderDramSourceChart') && contains(files.app, 'data-dram-scale="indexed"'), 'DRAM chart offers a display-only indexed comparison while preserving USD view');
assert(contains(files.app, 'pointerPreview: true') && contains(files.app, 'dram-selection-guide'), 'DRAM chart coordinates pointer, keyboard, and single-date selection feedback');
assert(!contains(files.app, 'dram-value-layer') && !contains(files.app, 'dram-value-label'), 'DRAM chart does not overlay every observation value on the plot');
assert(contains(files.app, 'TrendForce daily'), 'DRAM chart prioritizes saved TrendForce daily prices');
assert(contains(files.app, 'D램 가격'), 'Korean D램 price label exists');
assert(contains(files.app, 'isValidChartPoint'), 'DRAM chart validates date/value points');
assert(contains(files.app, 'parseBestFactor'), 'best factor parser exists');
assert(contains(files.app, 'parseEtfTracking'), 'ETF Tracking parser exists');
assert(contains(files.app, 'parseSox'), 'SOX summary parser exists');
assert(contains(files.app, 'renderSox'), 'SOX dashboard panel renderer exists');
assert(contains(files.app, 'SOX 구성종목 · Momentum Top 5'), 'SOX central summary panel copy exists');
assert(contains(files.app, 'parseRegime') && contains(files.app, 'renderRegime'), 'Regime public-result parser and summary panel renderer exist');
assert(contains(files.app, "['demo', 'live'].includes(meta.mode)") && contains(files.app, "synthetic_fixture") && contains(files.app, "private_noncommercial") && contains(files.app, "user_confirmed_ml_storage_derived"), 'Regime adapter validates demo and exact live-derived source contracts');
assert(contains(files.app, 'PROJECT_EXPECTED_FRESHNESS_DAYS') && contains(files.app, 'expectedFreshnessDays'), 'every panel has a project-level freshness fallback');
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
assert(
  contains(files.app, 'bindChartKeyboardFrames')
    && contains(files.app, 'class="etf-mini-plot" tabindex="0"')
    && contains(files.app, 'class="dram-chart-frame" tabindex="0"')
    && contains(files.app, 'chart-keyboard-readout')
    && contains(files.app, "navigationLabel: '날짜/제품'"),
  'ETF and DRAM charts use one focusable frame with arrow-key exploration and an external exact-value readout',
);
assert(
  !/class="etf-data-point"[^>]*tabindex=/.test(files.app)
    && !/class="dram-series"[^>]*tabindex=/.test(files.app),
  'SVG data points and series do not create excessive keyboard tab stops',
);
assert(contains(files.css, '.etf-detail-grid'), 'ETF Tracking detail grid CSS exists');
assert(contains(files.css, '.etf-top10-list'), 'ETF Tracking TOP10 list CSS exists');
assert(contains(files.css, '.dram-scale-control') && contains(files.css, '.dram-legend-button'), 'DRAM display controls and series buttons use dashboard-native styles');
assert(!contains(files.css, '.dram-value-layer') && !contains(files.css, '.dram-value-label'), 'DRAM CSS contains no all-point value-label reveal behavior');
assert(
  contains(files.css, '.panel--momentum :is(th, td):nth-child(3)')
    && contains(files.css, '.panel--sox :is(th, td):nth-child(6)')
    && !contains(files.css, 'th:not(:first-child)'),
  'table alignment is project-aware so numeric cells align right without moving ticker or status text',
);
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
  contains(files.readme, 'docs/platform-architecture-v1.md')
    && contains(files.readme, 'docs/control-audit-2026-07-24.md')
    && contains(files.platformArchitecture, 'Do not force every project through FastAPI')
    && contains(files.controlAudit, 'Analysis controls'),
  'README links the audited frontend/backend boundary and implementation architecture',
);
assert(contains(files.readme, 'Momentum Factor, Best Factor') && contains(files.readme, '여섯 기준 프로젝트'), 'README names the complete six-site design reference suite');
assert(
  [
    'https://sonchanggi.github.io/dram-price/',
    'https://sonchanggi.github.io/fearNgreed/',
    'https://sonchanggi.github.io/etf-tracking/',
    'https://sonchanggi.github.io/sox/',
    'https://sonchanggi.github.io/momentum-factor-lab/',
    'https://sonchanggi.github.io/best-factor/',
  ].every((url) => contains(files.webDesign, url)),
  'web design prompt fixes the six-site reference suite',
);
assert(contains(files.webDesign, '버전: `2.2.1`'), 'web design prompt version is pinned');
assert(contains(files.webDesign, '## 1. 절대 보호 경계') && contains(files.webDesign, '계산·normalization·selection·aggregation 함수는 동결'), 'web design prompt protects analysis and result behavior');
assert(contains(files.webDesign, '### 1.4 입력의 네 종류를 먼저 선언한다') && ['`display`', '`result_selector`', '`analysis`', '`operation`'].every((kind) => contains(files.webDesign, kind)), 'web design prompt classifies every visible control before implementation');
assert(contains(files.webDesign, '### 1.5 현재 6개 사이트의 입력 기준선') && contains(files.webDesign, 'command 생성만으로 완료 처리하지 않는다'), 'web design prompt records the audited six-site input baseline');
assert(contains(files.webDesign, '### 1.6 입력 → 권위 분석 engine → 결과 계약') && contains(files.webDesign, 'config_hash') && contains(files.webDesign, 'artifact URL·SHA-256'), 'web design prompt requires an end-to-end input and artifact identity contract');
assert(contains(files.webDesign, '실제 bytes를 가져와 byte size와 SHA-256을 검증') && contains(files.webDesign, 'envelope 자기 비교는 금지'), 'web design prompt requires actual artifact-byte verification');
assert(contains(files.webDesign, 'worker의 실제 최대 실행 시간') && contains(files.webDesign, '내구 저장소에서 재조회'), 'web design prompt covers long-running durable analysis');
assert(contains(files.webDesign, '### 1.7 입력 민감도와 결정성 테스트') && contains(files.webDesign, '결정적 A/B fixture') && contains(files.webDesign, '단순 mock 호출 횟수만으로'), 'web design prompt requires black-box input sensitivity evidence');
assert(contains(files.webDesign, '### 1.8 백엔드·프런트엔드 분리 경계') && contains(files.webDesign, '정적 JSON snapshot은 삭제하지 않고'), 'web design prompt separates delivery responsibilities without replacing validated snapshots');
assert(contains(files.webDesign, 'applied_config') && contains(files.webDesign, 'draft_config') && contains(files.webDesign, 'requested_inputs') && contains(files.webDesign, 'effective_inputs'), 'web design prompt prevents draft and silently-fallbacked inputs from masquerading as applied results');
assert(contains(files.webDesign, 'effective_config_hash') && contains(files.webDesign, 'config_hash == effective_config_hash'), 'web design prompt binds requested and fallback-effective configurations separately');
assert(contains(files.webDesign, 'packages/') && contains(files.webDesign, 'data-client/') && contains(files.webDesign, '프로젝트별 view-model'), 'web design prompt defines reusable frontend boundaries without centralizing project calculations');
assert(contains(files.webDesign, '## 13. 기존 페이지 개선 절차') && contains(files.webDesign, '## 14. 신규 프로젝트 구현 절차') && contains(files.webDesign, 'local preview'), 'web design prompt covers existing and new project workflows');
assert(contains(files.webDesign, '## 4. 9개 공통 메뉴') && contains(files.webDesign, 'aria-current="page"') && contains(files.webDesign, 'Quant Research Hub'), 'web design prompt fixes the shared navigation contract');
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
assert(contains(files.commonDesign, 'Hub → Fear & Greed → Momentum → DRAM') && contains(files.commonDesign, 'SOX → Regime'), 'common design v1 fixes the project navigation order');
assert(contains(files.commonDesign, 'skip link') && contains(files.commonDesign, '12px'), 'common design v1 fixes keyboard entry and legible dense labels');
assert(contains(files.commonDesign, '프로젝트별 plan-goal'), 'common design v1 requires project-by-project rollout');
assert(contains(files.commonDesign, 'plot 영역 밖') && contains(files.commonDesign, 'absolute overlay'), 'common design v1 keeps exact-value readouts away from plotted marks');
assert(contains(files.commonDesign, '구현 설명') && contains(files.commonDesign, 'actionExplanation'), 'common design v1 removes implementation narration and repeated row explanations');
assert(contains(files.commonDesign, '버전: `1.2.0`') && contains(files.commonDesign, '공통 타이포그래피와 세로 밀도'), 'common design v1.2 fixes the shared typography and density reference');
assert(contains(files.commonDesign, '`15px`, `line-height: 1.55`') && contains(files.commonDesign, '`800` 이상'), 'common design v1.2 fixes the shared type scale and weight hierarchy');
assert(contains(files.commonDesign, '작은 disclaimer') && contains(files.commonDesign, '기본 닫힘 `운영 상세`'), 'common design v1.2 does not exempt fine print from copy reduction');
assert(contains(files.commonDesign, '8개 항목') && contains(files.commonDesign, '완료된 일부 프로젝트나 현재 프로젝트와 Hub만'), 'common design v1.2 requires the complete shared navigation');
assert(contains(files.commonDesign, '승인된 기존 색 토큰·primary·의미색') && contains(files.commonDesign, 'type·series·axis·legend·column·order를 보존'), 'common design v1.2 preserves project-specific visuals and analytical surfaces');
assert(contains(files.commonDesign, '역사적 적용 사례의 도메인 차이(비규범)') && contains(files.commonDesign, '비규범 파일럿 근거'), 'common design v1.2 keeps pilot projects as evidence rather than normative templates');
assert(contains(files.readme, 'docs/common-design-v1-rollout-prompt.md') && contains(files.design, 'docs/common-design-v1-rollout-prompt.md'), 'README and DESIGN link the rollout prompt');
assert(contains(files.commonDesignPrompt, '프로젝트별 plan-goal') && contains(files.commonDesignPrompt, 'Python 수집·분석·전략') && contains(files.commonDesignPrompt, '공개 JSON schema') && contains(files.commonDesignPrompt, 'workflow·GitHub Pages URL'), 'rollout prompt preserves project-by-project analysis, data, and deployment boundaries');
assert(contains(files.commonDesignPrompt, 'plot 밖의 고정 행') && contains(files.commonDesignPrompt, '구현 설명') && contains(files.commonDesignPrompt, 'bounding box'), 'rollout prompt requires copy reduction and chart collision QA');
assert(contains(files.commonDesignPrompt, 'Quant Research 공통 디자인 v1.2') && contains(files.commonDesignPrompt, '공통 타이포그래피와 밀도') && contains(files.commonDesignPrompt, '통일성의 범위'), 'rollout prompt applies the shared visual reference');
assert(contains(files.commonDesignPrompt, '`15px / 1.55`') && contains(files.commonDesignPrompt, '`800` 이상'), 'rollout prompt carries the compact type and weight rules');
assert(contains(files.commonDesignPrompt, 'Hub → Fear & Greed → Momentum → DRAM') && contains(files.commonDesignPrompt, '정확히 8개'), 'rollout prompt requires the full registry-driven top navigation');
assert(contains(files.commonDesignPrompt, 'sticky shell 약 `58px`') && contains(files.commonDesignPrompt, '메뉴 글자 `12px / 650`'), 'rollout prompt carries the compact shared navigation density');
assert(contains(files.commonDesignPrompt, '`데이터 · 출처 · 운영 상세`'), 'rollout prompt consolidates secondary copy in one named closed details section');
assert(contains(files.commonDesignPrompt, '기존 차트 유형·패널·축·범례·계열') && contains(files.commonDesignPrompt, '기존 색 토큰'), 'rollout prompt preserves project-specific charts, tables, and colors');
assert(contains(files.commonDesignPrompt, '공통 디자인만을 이유로 새 기능') && contains(files.commonDesignPrompt, '수정 전 대상 화면의 computed'), 'rollout prompt preserves existing chart capabilities and records a before baseline');
assert(contains(readFileSync('scripts/regression.mjs', 'utf8'), 'malformed momentum payload resolves to fallback mode'), 'malformed payload regression exists');
assert(contains(readFileSync('scripts/regression.mjs', 'utf8'), 'null/non-object entries resolve to fallback'), 'null-entry payload regression exists');
assert(contains(readFileSync('scripts/static-smoke.mjs', 'utf8'), 'static server smoke'), 'static server smoke exists');
assert(contains(files.packageJson, '"test:live"'), 'package exposes optional live contract smoke');
assert(contains(files.packageJson, '"test:publish"') && contains(files.packageJson, 'npm run test:live'), 'package exposes publish gate with live contract smoke');
assert(contains(files.liveSmoke, 'MAX_PAYLOAD_BYTES') && contains(files.liveSmoke, 'MAX_GENERATION_AGE_DAYS'), 'live contract smoke checks payload size and freshness');
assert(contains(files.liveSmoke, "'transport'") && contains(files.liveSmoke, "'contract'") && contains(files.liveSmoke, "'freshness'"), 'live health report distinguishes transient transport from hard contract and freshness failures');
assert(contains(files.publicHealthWorkflow, 'cron: "15 5 * * 2-6"') && contains(files.publicHealthWorkflow, 'workflow_run:'), 'public health runs on schedule and after the main platform workflow');
assert(contains(files.publicHealthWorkflow, 'public-data-incident-state') && contains(files.publicHealthWorkflow, '--incident-changed'), 'scheduled public health deduplicates an unchanged hard incident');
assert(contains(files.publicHealthWorkflow, 'scripts/public-health-gate.mjs') && contains(files.publicHealthGate, "finding.category === 'contract' || finding.category === 'observability'") && contains(files.publicHealthGate, "'data_health_warning'"), 'Hub health fails only web-breaking contract or observability regressions while retaining data-health evidence');
assert(contains(files.publicHealthWorkflow, 'Fail only public contract or broad observability regressions') && contains(files.publicHealthWorkflow, 'HEALTH_EXIT" == "2"'), 'scheduled monitor keeps transient and stale data findings non-notifying');
assert(contains(files.publicHealthIncident, 'normalizeIncidentMessage') && contains(files.publicHealthIncident, 'quant-dashboard-public-health-incident'), 'public health incident identity normalizes moving age values');
assert(
  contains(files.publicHealthPolicy, 'TRANSPORT_HARD_FAILURE_PROJECT_THRESHOLD = 2')
    && contains(files.publicHealthPolicy, 'operationalFindingsFor')
    && contains(files.publicHealthPolicy, 'degraded reasons'),
  'public health policy reports operational degradation and escalates broad transport loss',
);
assert(
  files.platformFoundationWorkflow.split('".github/workflows/public-data-health.yml"').length - 1 === 2,
  'public health workflow changes trigger Platform Foundation on pull requests and main pushes',
);
assert(
  files.platformFoundationWorkflow.split('".github/workflows/pages.yml"').length - 1 === 2,
  'Pages workflow changes trigger Platform Foundation on pull requests and main pushes',
);
assert(contains(files.pagesWorkflow, 'workflows: ["Platform Foundation"]') && contains(files.pagesWorkflow, "workflow_run.event == 'push'") && contains(files.pagesWorkflow, 'conclusion == \'success\''), 'Pages deploys only after successful main-push Platform Foundation validation');
assert(contains(files.publicHealthWorkflow, "workflow_run.event == 'push'"), 'privileged workflow_run health checks reject pull-request revisions');
assert(contains(files.pagesWorkflow, 'Refuse a superseded Hub artifact') && contains(files.pagesWorkflow, 'EXPECTED_SOURCE_SHA'), 'Pages refuses a superseded Hub artifact');
assert(contains(files.pagesWorkflow, 'Require Actions-owned Pages configuration') && contains(files.pagesWorkflow, 'build_type') && contains(files.pagesWorkflow, 'workflow'), 'Pages refuses to race the legacy branch publisher');
assert(contains(files.pagesWorkflow, 'Build an allowlisted Pages artifact') && contains(files.pagesWorkflow, 'Verify public Hub bytes'), 'Pages publishes an allowlisted artifact and verifies public bytes');
assert(contains(files.pagesWorkflow, 'public-site-health:') && contains(files.pagesWorkflow, 'Fail only when the existing public Hub is unusable'), 'automatic Pages failures are notification-gated by live Hub usability');
assert(!contains(files.pagesWorkflow, 'actions/checkout@v') && !contains(files.pagesWorkflow, 'actions/deploy-pages@v'), 'Pages workflow pins third-party Actions by commit SHA');
assert(contains(files.liveSmoke, 'validateAdapterContract'), 'live contract smoke rejects incompatible contract versions');
assert(contains(files.liveSmoke, 'REQUIRED_PROJECT_COUNT = 7'), 'live contract smoke requires all seven active public summary panels');
assert(
  files.liveSmoke.indexOf('class PublicFetchError') >= 0
    && files.liveSmoke.indexOf('class PublicFetchError') < files.liveSmoke.indexOf('for (const project of panelProjects)'),
  'live contract smoke initializes its typed fetch error before the top-level network loop',
);
assert(!contains(files.app, '../momentum-factor-lab') && !contains(files.app, '../dram-price') && !contains(files.app, '../best-factor') && !contains(files.app, '../etf-tracking') && !contains(files.app, '../sox'), 'no sibling local source paths referenced');

const failed = checks.filter((check) => !check.ok);
for (const check of checks) {
  console.log(`${check.ok ? 'PASS' : 'FAIL'} ${check.label}`);
}

if (failed.length) {
  console.error(`\n${failed.length} verification check(s) failed.`);
  process.exit(1);
}

console.log(`\n${checks.length} verification checks passed.`);
