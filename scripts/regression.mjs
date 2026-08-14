import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import {
  operationalFindingsFor,
  TRANSPORT_HARD_FAILURE_PROJECT_THRESHOLD,
  transportEscalation,
} from './public-health-policy.mjs';

const source = readFileSync('assets/app.js', 'utf8');
const context = vm.createContext({ console, URL });
vm.runInContext(source, context, { filename: 'assets/app.js' });
const api = context.__QUANT_DASHBOARD_TESTS__;

const checks = [];
const assert = (condition, label) => checks.push({ ok: Boolean(condition), label });
const fallbackFor = (parsed, hasUsableData, reason) => api.resolveLoadState({ ok: true, data: {} }, hasUsableData, reason);

assert(api, 'test API exposed without browser DOM');
const degradedOperationalFindings = operationalFindingsFor('port', {
  state: 'degraded',
  meta: {
    statusState: 'degraded',
    degradedReasons: ['provider_unavailable'],
  },
});
assert(
  degradedOperationalFindings.some((finding) => /upstream state is degraded/.test(finding.message))
    && degradedOperationalFindings.some((finding) => /provider_unavailable/.test(finding.message)),
  'public health reports degraded upstream state and provider reasons',
);
assert(
  transportEscalation(['port'], 8) === null,
  'one transient transport outage remains a soft observation warning',
);
const broadTransportFailure = transportEscalation(['port', 'etf'], 8);
assert(
  TRANSPORT_HARD_FAILURE_PROJECT_THRESHOLD === 2
    && broadTransportFailure?.severity === 'hard'
    && broadTransportFailure?.affectedProjects.length === 2,
  'two or more unobservable projects become a hard observability failure',
);
assert(
  api.PROJECTS.map((project) => project.shortName).join('|')
    === 'Fear & Greed|Momentum|DRAM|Best Factor|ETF|SOX|Port|Regime',
  'project manifest preserves the canonical navigation order after Hub',
);
assert(
  JSON.stringify(api.PLATFORM_PROJECT_IDS) === JSON.stringify({
    fearngreed: 'fear-greed',
    momentum: 'momentum',
    dram: 'dram',
    best: 'best-factor',
    etf: 'etf',
    sox: 'sox',
    port: 'port',
    regime: 'regime',
  }),
  'Hub maps public summary ids to canonical platform project identities',
);
assert(api.configuredSupabaseMetadata() === null, 'Supabase metadata lookup is disabled without explicit public configuration');
const metadataFetches = [];
context.document = {
  querySelector(selector) {
    if (selector === 'meta[name="quant-supabase-url"]') return { content: 'https://project.supabase.co/' };
    if (selector === 'meta[name="quant-supabase-publishable-key"]') return { content: 'sb_publishable_test_key' };
    return null;
  },
};
context.setTimeout = setTimeout;
context.clearTimeout = clearTimeout;
context.AbortController = AbortController;
const publishedMetadata = await api.getPublishedSnapshotMetadata('best-factor', 100, async (url, options) => {
  metadataFetches.push({ url, options });
  return {
    ok: true,
    async json() {
      return [{
        id: 'snapshot-1',
        project_id: 'best-factor',
        run_id: 'run-1',
        data_as_of: '2026-07-23',
        source: 'best-factor-live',
        source_hash: '1234567890abcdef',
        artifact_url: 'https://raw.githubusercontent.com/SonChangGi/best-factor/0123456789012345678901234567890123456789/docs/data/latest-results.json',
        artifact_sha256: 'a'.repeat(64),
        byte_size: 1024,
        contract_version: 'best-factor/latest-results/v1',
        created_at: '2026-07-24T01:00:00Z',
      }];
    },
  };
});
assert(publishedMetadata.ok && publishedMetadata.data.dataAsOf === '2026-07-23', 'Hub validates optional Supabase published snapshot metadata');
assert(
  metadataFetches.length === 1
    && metadataFetches[0].url.includes('/rest/v1/published_project_snapshots?')
    && metadataFetches[0].url.includes('project_id=eq.best-factor')
    && metadataFetches[0].options.headers.apikey === 'sb_publishable_test_key'
    && !Object.hasOwn(metadataFetches[0].options.headers, 'Authorization'),
  'Hub metadata lookup uses the public view and publishable key only',
);
delete context.document;
const momentumJcsRecordsVector = [
  { z: 1, a: '한글' },
  { nested: { b: 1, a: 2 }, a: true },
];
assert(
  api.momentumCanonicalKeyPartsJson(momentumJcsRecordsVector)
    === '[{"a":"한글","z":1},{"a":true,"nested":{"a":2,"b":1}}]',
  'Momentum provenance records use RFC 8785 key ordering while preserving array order',
);
assert(
  api.momentumCanonicalRecordsSha256(momentumJcsRecordsVector)
    === '1904f325c89a514ae58871fd97bab57cbfa9c4eabda2e2f688befa60f65282b4',
  'Momentum provenance records use the expected RFC 8785 JCS SHA-256 digest',
);

const malformedMomentum = api.parseMomentum({
  schemaVersion: 4,
  selectedFactor: 'schema_drift',
  compositeScore: 0.25,
  dataAsOf: '2026-06-10',
  weights: [],
});
const momentumState = fallbackFor(malformedMomentum, malformedMomentum.rows.length > 0, 'Momentum payload did not contain usable top rows.');
assert(momentumState.mode === 'fallback', 'HTTP 200 malformed momentum payload resolves to fallback mode');
assert(/Momentum payload/.test(momentumState.error), 'Momentum fallback keeps explicit schema reason');
const unavailableMomentumFallback = api.PANEL_ADAPTERS.momentum.fallback();
assert(
  unavailableMomentumFallback.unavailable === true
    && unavailableMomentumFallback.rows.length === 0
    && unavailableMomentumFallback.entities.length === 0
    && unavailableMomentumFallback.meta.holdingCount === 0,
  'Momentum fetch failure exposes unavailable state with zero holdings',
);
assert(
  unavailableMomentumFallback.generatedAt === ''
    && unavailableMomentumFallback.dataAsOf === ''
    && unavailableMomentumFallback.factor === '-'
    && unavailableMomentumFallback.selectedWeightingPolicy === '-'
    && unavailableMomentumFallback.compositeScore === null,
  'Momentum unavailable state carries no fallback date, factor, policy, score, or allocation snapshot',
);
assert(!api.PANEL_ADAPTERS.momentum.hasUsableData(unavailableMomentumFallback), 'Momentum unavailable state cannot be promoted to usable live holdings');

const validFearAndGreed = api.parseFearAndGreed({
  schemaVersion: 1,
  contract: 'quant-research-summary',
  projectId: 'fearngreed',
  generatedAt: '2026-07-16T00:00:00Z',
  dataAsOf: '2026-07-15',
  status: { state: 'ok', label: '중립', cadence: 'weekdays-after-20:30-KST', expectedFreshnessDays: 3, degradedReasons: [] },
  primaryEntities: [{ id: 'KOSPI', name: 'KOSPI', themes: ['Sentiment', 'Flow'], signalState: 'neutral', sentimentPercentile: 55, residualZ: 0.2, rollingR2: 0.7, disparity50: 101.2, position: 'cash', primaryProxy: '226490', modelQuality: 'ok', modelConfidence: 'high' }],
  limitations: ['사후적·탐색적 연구'],
});
const fearAdapter = api.PANEL_ADAPTERS.fearngreed;
assert(validFearAndGreed.current.sentimentPercentile === 55 && validFearAndGreed.current.position === 'cash', 'Fear & Greed parser preserves current percentile and model position');
assert(validFearAndGreed.entities[0].themes.includes('Flow') && validFearAndGreed.entities[0].sector === 'Korea', 'Fear & Greed entity feeds Korea Sentiment Flow dossier themes');
assert(fearAdapter.hasUsableData(validFearAndGreed), 'Fear & Greed adapter accepts a dated KOSPI summary');
const unavailableFear = fearAdapter.fallback();
assert(unavailableFear.unavailable === true && unavailableFear.rows.length === 0 && unavailableFear.dataAsOf === '', 'Fear & Greed fetch failure exposes unavailable without hardcoded market values');

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

const malformedSox = api.parseSox({ schemaVersion: 1, contract: 'quant-research-summary', projectId: 'sox', status: 'ok', primaryEntities: [null, { metrics: { score: 0.2 } }] });
const soxState = fallbackFor(malformedSox, malformedSox.rows.length > 0, 'SOX summary did not contain usable constituents.');
assert(soxState.mode === 'fallback', 'HTTP 200 malformed SOX summary resolves to fallback mode');
assert(/SOX summary/.test(soxState.error), 'SOX fallback keeps explicit schema reason');

const momentumDemoInputSha256 = { prices: 'c'.repeat(64) };
const momentumDemoMarketSnapshot = {
  sourceMode: 'demo',
  sourceLabel: 'deterministic demo fixture',
  provider: null,
  priceBasis: 'deterministic_adjusted_close_fixture',
  volumeBasis: 'deterministic_share_volume_fixture',
  rawCloseProxySymbolCount: 0,
  requestedThrough: '2026-06-18',
  dataAsOf: '2026-06-18',
  inputSha256: momentumDemoInputSha256,
  requestedCandidateCount: 50,
  providerReturnedCandidateCount: 50,
  analyzedSecurityCount: 50,
};
const momentumIdentityKeyParts = {
  identityVersion: 'momentum-result-identity-v1',
  canonicalJsonVersion: 'rfc8785-jcs-v1',
  inputs: { topN: 20, maxWeight: 0.6 },
  marketSnapshot: momentumDemoMarketSnapshot,
};
const momentumResultIdentity = {
  identityVersion: 'momentum-result-identity-v1',
  resultKey: api.momentumResultKeyForKeyParts(momentumIdentityKeyParts),
  keyParts: momentumIdentityKeyParts,
  canonicalKeyPartsJson: api.momentumCanonicalKeyPartsJson(momentumIdentityKeyParts),
};
const momentumResearchInputs = {
  version: 'research-inputs-v1',
  maxWeight: 0.6,
  selectionMinSharpe: 0,
  selectionMaxDrawdown: 0.6,
  selectionMaxAnnualizedCostDrag: 0.02,
  selectionMinEffectiveNames: 1,
  selectionMaxTargetHhi: 1,
  selectionMaxTargetWeight: 0.6,
  selectionMaxAbsSecurityDayContribution: 0.25,
  selectionMaxSecurityAbsoluteContributionShare: 0.35,
  selectionMaxLeaveOneSecurityCagrDelta: 0.25,
  selectionExtremeEventAction: 'exclude',
  selectionExtremeEventPenaltyPoints: 20,
};
const momentumConfig = {
  absolute_guardrail_version: 'absolute-factor-policy-v1',
  max_weight: 0.6,
  selection_min_sharpe: 0,
  selection_max_drawdown: 0.6,
  selection_max_annualized_cost_drag: 0.02,
  selection_min_effective_names: 1,
  selection_max_target_hhi: 1,
  selection_max_target_weight: 0.6,
  selection_max_abs_security_day_contribution: 0.25,
  selection_max_security_absolute_contribution_share: 0.35,
  selection_max_leave_one_security_cagr_delta: 0.25,
  selection_extreme_event_action: 'exclude',
  selection_extreme_event_penalty_points: 20,
};
const momentumPolicies = [
  'equal_weight',
  'capped_linear_rank',
  'capped_vol_adjusted_rank',
  'score_liquidity_rank',
];
const momentumIndependentFactors = [
  'selected_mom',
  ...Array.from({ length: 60 }, (_, index) => `independent_factor_${String(index + 1).padStart(2, '0')}`),
];
const momentumAliasDefinitions = [
  { factor: 'compatibility_alias_1', compatibility_alias_of: 'selected_mom', selection_eligible: false },
  { factor: 'compatibility_alias_2', compatibility_alias_of: 'independent_factor_01', selection_eligible: false },
  { factor: 'compatibility_alias_3', compatibility_alias_of: 'independent_factor_02', selection_eligible: false },
];
const momentumFactorDefinitions = [
  ...momentumIndependentFactors.map((factor) => ({
    factor,
    compatibility_alias_of: null,
    selection_eligible: true,
  })),
  ...momentumAliasDefinitions,
];
const momentumGridAccounting = {
  version: 1,
  independentFactorCount: 61,
  policyCount: 4,
  expectedIndependentPairCount: 244,
  evaluatedIndependentPairCount: 244,
  availableIndependentPairCount: 244,
  excludedIndependentPairCount: 0,
  missingIndependentPairCount: 0,
  diagnosticAliasFactorCount: 3,
  diagnosticAliasPairCount: 12,
  commonComparableFactorCount: 61,
  exclusionReasonCounts: {},
  invariant: 'availableIndependentPairCount + excludedIndependentPairCount = expectedIndependentPairCount',
};
const momentumFactorPolicyRanking = momentumFactorDefinitions.flatMap((definition) => (
  momentumPolicies.map((policyId) => {
    const selected = definition.factor === 'selected_mom' && policyId === 'capped_linear_rank';
    const alias = Boolean(definition.compatibility_alias_of);
    return {
      factor: definition.factor,
      policy_id: policyId,
      comparison_status: alias ? 'duplicate_alias' : 'available',
      selected,
      selection_status: alias ? 'data_excluded' : 'eligible',
      selection_eligible: !alias,
      standard_guardrail_pass: true,
      contribution_guardrail_pass: true,
      absolute_guardrail_pass: true,
      composite_score: selected ? 0.87 : 0.5,
      selection_score: alias ? null : (selected ? 0.87 : 0.5),
      min_target_effective_names: 1,
      median_target_effective_names: 999,
      current_target_effective_names: 1,
      max_target_hhi: 1,
      median_target_hhi: 0,
      current_target_hhi: 1,
      max_target_weight: 0.6,
      current_target_max_weight: 0.6,
      guardrail_historical_effective_names: true,
      guardrail_current_effective_names: true,
      guardrail_historical_target_hhi: true,
      guardrail_current_target_hhi: true,
      guardrail_historical_target_weight: true,
      guardrail_current_target_weight: true,
    };
  })
));
const momentumAbsoluteGuardrailRules = [
  ['minimum_sharpe', 'sharpe', '>=', 0, 'ratio'],
  ['maximum_drawdown_magnitude', 'max_drawdown', '>=', -0.6, 'fraction'],
  ['maximum_annualized_cost_drag', 'annualized_cost_drag', '<=', 0.02, 'fraction_per_year'],
  ['minimum_historical_target_effective_names', 'min_target_effective_names', '>=', 1, 'names'],
  ['minimum_current_target_effective_names', 'current_target_effective_names', '>=', 1, 'names'],
  ['maximum_historical_target_hhi', 'max_target_hhi', '<=', 1, 'fraction'],
  ['maximum_current_target_hhi', 'current_target_hhi', '<=', 1, 'fraction'],
  ['maximum_historical_target_weight', 'max_target_weight', '<=', 0.6, 'fraction'],
  ['maximum_current_target_weight', 'current_target_max_weight', '<=', 0.6, 'fraction'],
  ['maximum_security_day_contribution', 'max_abs_security_day_contribution', '<=', 0.25, 'portfolio_return_fraction'],
  ['maximum_security_absolute_contribution_share', 'max_security_absolute_contribution_share', '<=', 0.35, 'fraction'],
  ['maximum_leave_one_security_cagr_delta', 'max_abs_leave_one_security_cagr_delta', '<=', 0.25, 'cagr_fraction'],
].map(([id, metric, operator, threshold, unit]) => ({ id, metric, operator, threshold, unit }));
const momentumAbsoluteGuardrailProfile = {
  id: 'absolute-factor-policy-v1',
  version: 1,
  policyNeutral: true,
  rules: momentumAbsoluteGuardrailRules,
  requiredContracts: {
    completeExecutionCoverage: true,
    completePolicyInputs: true,
    contributionDiagnosticsComplete: true,
    currentTargetAvailable: true,
  },
  extremeEventAction: 'exclude',
  extremeEventPenaltyPoints: 20,
};
const concentrationForWeights = (weights, cashWeight) => {
  const values = weights.map((row) => row.weight);
  const investedWeight = values.reduce((sum, weight) => sum + weight, 0);
  const normalized = investedWeight > 0 ? values.map((weight) => weight / investedWeight) : [];
  const riskySleeveHhi = normalized.reduce((sum, weight) => sum + weight * weight, 0);
  const ordered = values.slice().sort((left, right) => right - left);
  return {
    investedWeight,
    cashWeight,
    riskySleeveHhi,
    effectiveNames: riskySleeveHhi > 0 ? 1 / riskySleeveHhi : 0,
    top1Weight: ordered.slice(0, 1).reduce((sum, weight) => sum + weight, 0),
    top5Weight: ordered.slice(0, 5).reduce((sum, weight) => sum + weight, 0),
    maxWeight: ordered[0] || 0,
  };
};
const momentumFixtureWeights = [
  { rank: 1, symbol: 'SEL', name: 'Selected Co', factorScore: 9, weight: 0.6 },
];
const momentumCurrentResearchTarget = {
  factor: 'selected_mom',
  asOf: '2026-06-18',
  signalDate: '2026-06-18',
  weightingPolicyId: 'capped_linear_rank',
  cashWeight: 0.4,
  eligibleSecurityCount: 40,
  weights: momentumFixtureWeights,
  concentration: concentrationForWeights(momentumFixtureWeights, 0.4),
};
const momentumSummaryV4 = {
  schemaVersion: 4,
  resultIdentity: momentumResultIdentity,
  resultKey: momentumResultIdentity.resultKey,
  generatedAt: '2026-06-18T00:00:00Z',
  dataAsOf: '2026-06-18',
  dataMode: 'demo',
  sourceLabel: 'deterministic demo fixture',
  universeSize: 50,
  eligibleSecurityCount: 40,
  factorCount: 64,
  gridAccounting: momentumGridAccounting,
  selectedFactor: 'selected_mom',
  selectedWeightingPolicy: 'capped_linear_rank',
  selectedReason: 'best joint factor-policy pair on the complete grid',
  compositeScore: 0.87,
  researchOnly: true,
  notInvestmentRecommendation: true,
  evidenceStatus: 'same_sample_descriptive',
  limitations: ['same-sample selection bias'],
  cashWeight: 0.4,
  maxWeight: 0.6,
  weights: momentumFixtureWeights,
};
const momentumDashboardV4 = {
  schemaVersion: 4,
  resultIdentity: momentumResultIdentity,
  resultKey: momentumResultIdentity.resultKey,
  generatedAtUtc: '2026-06-18T00:05:00Z',
  selectedFactor: 'selected_mom',
  selectedWeightingPolicy: 'capped_linear_rank',
  selectedReason: 'best joint factor-policy pair on the complete grid',
  researchScope: {
    researchOnly: true,
    notInvestmentRecommendation: true,
    evidenceStatus: 'same_sample_descriptive',
    limitations: ['same-sample selection bias'],
  },
  gridAccounting: momentumGridAccounting,
  factorDefinitions: momentumFactorDefinitions,
  factorPolicyRanking: momentumFactorPolicyRanking,
  researchInputs: momentumResearchInputs,
  selectionDecision: {
    guardrailProfile: momentumAbsoluteGuardrailProfile,
  },
  currentResearchTarget: momentumCurrentResearchTarget,
  factorPortfolios: {
    selected_mom: {
      factor: 'selected_mom',
      asOf: '2026-06-18',
      weightingPolicyId: 'capped_linear_rank',
      cashWeight: 0.4,
      weights: [{ rank: 1, symbol: 'SEL', name: 'Selected Co', factorScore: 9, weight: 0.6 }],
    },
  },
  data: {
    mode: 'demo',
    sourceLabel: 'deterministic demo fixture',
    provider: null,
    priceBasis: 'deterministic_adjusted_close_fixture',
    volumeBasis: 'deterministic_share_volume_fixture',
    rawCloseProxySymbolCount: 0,
    requestedThrough: '2026-06-18',
    asOf: '2026-06-18',
    inputSha256: momentumDemoInputSha256,
    requestedCandidateCount: 50,
    providerReturnedCandidateCount: 50,
    inputSecurityCount: 50,
    analyzedSecurityCount: 50,
    latestEligibleSecurityCount: 40,
    notes: ['fixture'],
  },
  config: momentumConfig,
  meta: {
    factorCount: 64,
    independentFactorCount: 61,
    aliasFactorCount: 3,
    policyCount: 4,
    policyFactorRunCount: 256,
  },
};
momentumSummaryV4.currentResearchTarget = momentumDashboardV4.currentResearchTarget;
const momentumV5Policy = 'score_liquidity_rank';
const momentumBestFactorPortfolioV5 = {
  ...momentumCurrentResearchTarget,
  weightingPolicyId: momentumV5Policy,
};
const momentumFactorRankingV5 = momentumFactorDefinitions.map((definition, index) => {
  const base = momentumFactorPolicyRanking.find((row) => (
    row.factor === definition.factor && row.policy_id === 'capped_linear_rank'
  ));
  const selected = definition.factor === 'selected_mom';
  return {
    ...base,
    policy_id: momentumV5Policy,
    selected,
    rank: selected ? 1 : (definition.compatibility_alias_of ? null : index + 2),
    selection_status: definition.compatibility_alias_of ? 'data_excluded' : 'eligible',
    selection_eligible: !definition.compatibility_alias_of,
  };
});
const momentumFactorAccountingV5 = {
  version: 2,
  independentFactorCount: 61,
  expectedIndependentFactorCount: 61,
  evaluatedIndependentFactorCount: 61,
  availableIndependentFactorCount: 61,
  excludedIndependentFactorCount: 0,
  missingIndependentFactorCount: 0,
  diagnosticAliasFactorCount: 3,
  commonComparableFactorCount: 61,
  exclusionReasonCounts: {},
};
const momentumDashboardV5 = {
  ...momentumDashboardV4,
  schemaVersion: 5,
  bestFactor: 'selected_mom',
  weightingPolicy: momentumV5Policy,
  bestFactorReason: 'same-input Python fixed-method factor selection',
  factorAccounting: momentumFactorAccountingV5,
  factorRanking: momentumFactorRankingV5,
  factorSelectionDecision: {
    guardrailProfile: { ...momentumAbsoluteGuardrailProfile, id: 'absolute-factor-v2' },
  },
  bestFactorPortfolio: momentumBestFactorPortfolioV5,
  bestFactorTransition: null,
  allocationMethod: { policyId: momentumV5Policy, fixed: true },
  config: { ...momentumDashboardV4.config, absolute_guardrail_version: 'absolute-factor-v2' },
  meta: {
    factorCount: 64,
    independentFactorCount: 61,
    aliasFactorCount: 3,
    portfolioCount: 64,
    factorRunCount: 64,
  },
};
const momentumSummaryV5 = {
  ...momentumSummaryV4,
  schemaVersion: 5,
  bestFactor: momentumSummaryV4.selectedFactor,
  weightingPolicy: momentumV5Policy,
  bestFactorReason: 'same-input Python fixed-method factor selection',
  factorAccounting: momentumFactorAccountingV5,
  bestFactorPortfolio: momentumBestFactorPortfolioV5,
  allocationMethod: {
    policyId: momentumV5Policy,
    fixed: true,
  },
};
assert(api.isMomentumSummaryV5(momentumSummaryV5), 'Momentum schema-v5 summary satisfies the fixed-method contract');
assert(api.isMomentumDashboardV5(momentumDashboardV5), 'Momentum schema-v5 dashboard satisfies the 64-factor fixed-method contract');
const momentumDashboardV5ResearchInputsV2 = {
  ...momentumDashboardV5,
  researchInputs: {
    ...momentumDashboardV5.researchInputs,
    version: 'research-inputs-v2',
  },
};
assert(
  api.isMomentumDashboardV5(momentumDashboardV5ResearchInputsV2),
  'Momentum schema-v5 dashboard accepts the current day-based research-inputs-v2 contract',
);
assert(
  !api.isMomentumDashboardV5({
    ...momentumDashboardV5,
    researchInputs: {
      ...momentumDashboardV5.researchInputs,
      version: 'research-inputs-v3',
    },
  }),
  'Momentum schema-v5 dashboard rejects unknown research-input contract versions',
);
const validMomentumV5 = api.parseMomentum(momentumSummaryV5, momentumDashboardV5);
assert(validMomentumV5.factor === 'selected_mom' && validMomentumV5.selectedWeightingPolicy === momentumV5Policy, 'Momentum schema-v5 parser keeps the Python best factor and fixed method aligned');
assert(validMomentumV5.weightSource === 'dashboard.bestFactorPortfolio.weights' && validMomentumV5.rows[0].symbol === 'SEL', 'Momentum schema-v5 parser reads bestFactorPortfolio without a browser-side proxy');
const momentumContractError = api.validateAdapterContract(
  api.PANEL_ADAPTERS.momentum,
  { summary: momentumSummaryV5, momentumDashboard: momentumDashboardV4 },
);
assert(!momentumContractError, 'Momentum adapter accepts schemaVersion 5 summary contract');
const oldMomentumContractError = api.validateAdapterContract(
  api.PANEL_ADAPTERS.momentum,
  { summary: { ...momentumSummaryV5, schemaVersion: 4 }, momentumDashboard: momentumDashboardV4 },
);
assert(/expected 5/.test(oldMomentumContractError), 'Momentum adapter rejects the retired summary schema version');
const { dataMode: omittedMomentumDataMode, ...momentumSummaryWithoutMode } = momentumSummaryV5;
const missingModeContractError = api.validateAdapterContract(
  api.PANEL_ADAPTERS.momentum,
  { summary: momentumSummaryWithoutMode, momentumDashboard: momentumDashboardV4 },
);
assert(omittedMomentumDataMode === 'demo' && /dataMode/.test(missingModeContractError), 'Momentum contract requires an explicit dataMode field');

const validMomentum = api.parseMomentum(momentumSummaryV4, momentumDashboardV4);
assert(validMomentum.factor === 'selected_mom' && validMomentum.compositeScore === 0.87, 'Momentum v4 reads selectedFactor and compositeScore directly');
assert(validMomentum.selectedWeightingPolicy === 'capped_linear_rank' && /joint factor-policy/.test(validMomentum.weightingPolicyReason), 'Momentum v4 reads the selected weighting policy and joint reason directly');
assert(validMomentum.rows.length === 1 && validMomentum.rows[0].symbol === 'SEL', 'Momentum v4 renders selected model holdings');
assert(validMomentum.rows[0].signal === 9 && validMomentum.rows[0].modelWeight === 0.6, 'Momentum v4 preserves Python factorScore and model weight');
assert(validMomentum.weightSource === 'dashboard.currentResearchTarget.weights', 'Momentum v4 uses dashboard current research target weights when detail is available');
assert(!('productionWeight' in validMomentum.rows[0]) && !('securityId' in validMomentum.rows[0]), 'Momentum v4 row model has no executable or PIT identity dependency');
assert(validMomentum.meta.limitations[0] === 'same-sample selection bias', 'Momentum v4 propagates research limitations');
assert(validMomentum.dataMode === 'demo' && validMomentum.dataModeLabel === '합성 데모', 'Momentum v4 preserves demo mode with an explicit Korean label');
assert(validMomentum.sourceLabel === 'deterministic demo fixture' && validMomentum.evidenceStatus === 'same_sample_descriptive', 'Momentum v4 preserves source and evidence status');
assert(validMomentum.meta.statusState === 'demo' && /합성 데모/.test(validMomentum.status), 'Momentum demo remains usable but carries a non-ok demo tone');
assert(/capped_linear_rank/.test(validMomentum.status) && /현금 40%/.test(validMomentum.status), 'Momentum status names the selected weighting policy and cash sleeve');
assert(validMomentum.rows.length === 1 && validMomentum.entities[0].warnings.some((warning) => /합성 데모/.test(warning)), 'Momentum demo warning does not hide selected holdings');

const summaryOnlyMomentum = api.parseMomentum(momentumSummaryV4);
assert(summaryOnlyMomentum.rows[0].modelWeight === 0.6 && summaryOnlyMomentum.weightSource === 'summary.weights' && summaryOnlyMomentum.dataMode === 'demo', 'Momentum v4 compact summary is independently usable with mode parity');
const dashboardOnlyMomentum = api.parseMomentum(momentumDashboardV4);
assert(dashboardOnlyMomentum.factor === 'selected_mom' && dashboardOnlyMomentum.rows[0].modelWeight === 0.6 && dashboardOnlyMomentum.dataMode === 'demo', 'Momentum v4 dashboard currentResearchTarget is independently usable with mode parity');

const localMomentumMarketSnapshot = {
  ...momentumDemoMarketSnapshot,
  sourceMode: 'local_file',
  sourceLabel: 'adjusted_prices.csv',
};
const localMomentumIdentityKeyParts = {
  ...momentumIdentityKeyParts,
  marketSnapshot: localMomentumMarketSnapshot,
};
const localMomentumResultIdentity = {
  identityVersion: 'momentum-result-identity-v1',
  resultKey: api.momentumResultKeyForKeyParts(localMomentumIdentityKeyParts),
  keyParts: localMomentumIdentityKeyParts,
  canonicalKeyPartsJson: api.momentumCanonicalKeyPartsJson(localMomentumIdentityKeyParts),
};
const localMomentumSummary = {
  ...momentumSummaryV4,
  resultIdentity: localMomentumResultIdentity,
  resultKey: localMomentumResultIdentity.resultKey,
  dataMode: 'local_file',
  sourceLabel: 'adjusted_prices.csv',
};
const localMomentumDashboard = {
  ...momentumDashboardV4,
  resultIdentity: localMomentumResultIdentity,
  resultKey: localMomentumResultIdentity.resultKey,
  data: {
    ...momentumDashboardV4.data,
    mode: 'local_file',
    sourceLabel: 'adjusted_prices.csv',
  },
};
const localMomentum = api.parseMomentum(localMomentumSummary, localMomentumDashboard);
assert(localMomentum.dataMode === 'local_file' && localMomentum.dataModeLabel === '로컬 연구 데이터', 'Momentum local_file mode uses the explicit local research-data label');
assert(localMomentum.meta.statusState === 'ok' && /adjusted_prices\.csv/.test(localMomentum.status), 'Momentum local research data keeps its source and normal data tone');

const liveMomentumAnalyzedSymbols = ['LIVE'];
const liveMomentumPriceSources = [
  { symbol: 'LIVE', price_source: 'fixture_adjusted_close' },
];
const liveMomentumSourceHealth = [
  { source: 'fixture_market_data', status: 'ok' },
];
const liveMomentumInputSha256 = {
  comparisonPrices: '0'.repeat(64),
  prices: '1'.repeat(64),
  volumes: '2'.repeat(64),
  dollarVolumes: '3'.repeat(64),
  rawCloses: '4'.repeat(64),
  requestedSymbols: '5'.repeat(64),
  returnedSymbols: '6'.repeat(64),
  universeRecords: '7'.repeat(64),
  priceSources: api.momentumCanonicalRecordsSha256(liveMomentumPriceSources),
  dataSources: api.momentumCanonicalRecordsSha256(liveMomentumSourceHealth),
};
const liveMomentumMarketSnapshot = {
  sourceMode: 'live_market',
  sourceLabel: 'Nasdaq screener + adjusted market prices',
  provider: 'fixture_market_data',
  priceBasis: 'provider_adjusted_close',
  volumeBasis: 'raw_close_x_raw_volume',
  rawCloseProxySymbolCount: 0,
  requestedThrough: '2026-07-10',
  dataAsOf: '2026-07-10',
  inputSha256: liveMomentumInputSha256,
  requestedCandidateCount: 2865,
  providerReturnedCandidateCount: 2857,
  analyzedSecurityCount: 1,
  candidateSymbolsSha256: api.momentumSha256Hex(
    api.momentumCanonicalKeyPartsJson(liveMomentumAnalyzedSymbols),
  ),
};
const liveMomentumIdentityKeyParts = {
  ...momentumIdentityKeyParts,
  inputs: { ...momentumIdentityKeyParts.inputs, maxWeight: 0.1 },
  marketSnapshot: liveMomentumMarketSnapshot,
};
const liveMomentumResultIdentity = {
  identityVersion: 'momentum-result-identity-v1',
  resultKey: api.momentumResultKeyForKeyParts(liveMomentumIdentityKeyParts),
  keyParts: liveMomentumIdentityKeyParts,
  canonicalKeyPartsJson: api.momentumCanonicalKeyPartsJson(liveMomentumIdentityKeyParts),
};
const liveMomentumWeights = [
  { rank: 1, symbol: 'LIVE', name: 'Live Co', factorScore: 2.5, weight: 0.1 },
];
const liveMomentumTarget = {
  ...momentumDashboardV4.currentResearchTarget,
  asOf: '2026-07-10',
  signalDate: '2026-07-10',
  weightingPolicyId: 'capped_vol_adjusted_rank',
  cashWeight: 0.9,
  eligibleSecurityCount: 2184,
  weights: liveMomentumWeights,
  concentration: concentrationForWeights(liveMomentumWeights, 0.9),
};
const liveMomentumSummary = {
  ...momentumSummaryV4,
  resultIdentity: liveMomentumResultIdentity,
  resultKey: liveMomentumResultIdentity.resultKey,
  currentResearchTarget: liveMomentumTarget,
  generatedAt: '2026-07-11T00:05:00Z',
  dataAsOf: '2026-07-10',
  dataMode: 'live_market',
  sourceLabel: 'Nasdaq screener + adjusted market prices',
  requestedCandidateCount: 2865,
  providerReturnedCandidateCount: 2857,
  universeSize: 2865,
  eligibleSecurityCount: 2184,
  selectedWeightingPolicy: 'capped_vol_adjusted_rank',
  selectedReason: 'highest eligible joint factor-policy selection score',
  evidenceStatus: 'same_sample_descriptive_actual_market',
  cashWeight: 0.9,
  maxWeight: 0.1,
  weights: liveMomentumWeights,
};
const liveMomentumDashboard = {
  ...momentumDashboardV4,
  resultIdentity: liveMomentumResultIdentity,
  resultKey: liveMomentumResultIdentity.resultKey,
  generatedAtUtc: '2026-07-11T00:05:00Z',
  selectedWeightingPolicy: 'capped_vol_adjusted_rank',
  selectedReason: 'highest eligible joint factor-policy selection score',
  researchScope: {
    ...momentumDashboardV4.researchScope,
    evidenceStatus: 'same_sample_descriptive_actual_market',
  },
  currentResearchTarget: liveMomentumTarget,
  factorPolicyRanking: momentumDashboardV4.factorPolicyRanking.map((row) => {
    const selected = row.factor === 'selected_mom'
      && row.policy_id === 'capped_vol_adjusted_rank';
    return {
      ...row,
      selected,
      composite_score: selected ? 0.87 : row.composite_score,
      selection_score: selected ? 0.87 : row.selection_score,
      current_target_max_weight: selected ? 0.1 : row.current_target_max_weight,
    };
  }),
  researchInputs: { ...momentumResearchInputs, maxWeight: 0.1 },
  data: {
    ...momentumDashboardV4.data,
    mode: 'live_market',
    sourceLabel: 'Nasdaq screener + adjusted market prices',
    provider: 'fixture_market_data',
    priceBasis: 'provider_adjusted_close',
    volumeBasis: 'raw_close_x_raw_volume',
    rawCloseProxySymbolCount: 0,
    requestedThrough: '2026-07-10',
    asOf: '2026-07-10',
    requestedCandidateCount: 2865,
    providerReturnedCandidateCount: 2857,
    inputSecurityCount: 2865,
    analyzedSecurityCount: 1,
    analyzedSymbols: liveMomentumAnalyzedSymbols,
    latestEligibleSecurityCount: 2184,
    inputSha256: liveMomentumInputSha256,
  },
  config: { ...momentumDashboardV4.config, max_weight: 0.1 },
  priceSources: liveMomentumPriceSources,
  sourceHealth: liveMomentumSourceHealth,
};
assert(api.isMomentumSummaryV4(liveMomentumSummary), 'Momentum live-market summary satisfies canonical schema v4');
assert(api.isMomentumDashboardV4(liveMomentumDashboard), 'Momentum live-market dashboard satisfies provenance, grid, and guardrail contracts');
const liveMomentum = api.parseMomentum(liveMomentumSummary, liveMomentumDashboard);
assert(liveMomentum.dataMode === 'live_market' && liveMomentum.dataModeLabel === '실제 시장 데이터', 'Momentum live_market mode uses the explicit Korean actual-market label');
assert(liveMomentum.evidenceStatus === 'same_sample_descriptive_actual_market' && liveMomentum.meta.statusState === 'ok', 'Momentum actual-market evidence status is recognized without degradation');
assert(liveMomentum.meta.requestedCandidateCount === 2865 && liveMomentum.meta.providerReturnedCandidateCount === 2857 && liveMomentum.meta.eligibleSecurityCount === 2184, 'Momentum live-market funnel preserves requested, provider-returned, and eligible counts');
assert(liveMomentum.rows[0].modelWeight === 0.1 && /capped_vol_adjusted_rank/.test(liveMomentum.status) && /현금 90%/.test(liveMomentum.status), 'Momentum live-market status preserves Python weight, selected policy, and cash');

const marketSnapshotFromMomentumData = (data) => ({
  sourceMode: data.mode,
  sourceLabel: data.sourceLabel,
  provider: data.provider,
  priceBasis: data.priceBasis,
  volumeBasis: data.volumeBasis,
  rawCloseProxySymbolCount: data.rawCloseProxySymbolCount,
  requestedThrough: data.requestedThrough,
  dataAsOf: data.asOf,
  inputSha256: data.inputSha256,
  requestedCandidateCount: data.requestedCandidateCount,
  providerReturnedCandidateCount: data.providerReturnedCandidateCount,
  analyzedSecurityCount: data.analyzedSecurityCount,
  candidateSymbolsSha256: api.momentumSha256Hex(
    api.momentumCanonicalKeyPartsJson(data.analyzedSymbols),
  ),
});
const rekeyMomentumDashboardForData = (dashboard, data, overrides = {}) => {
  const keyParts = {
    ...dashboard.resultIdentity.keyParts,
    marketSnapshot: marketSnapshotFromMomentumData(data),
  };
  const resultIdentity = {
    identityVersion: 'momentum-result-identity-v1',
    resultKey: api.momentumResultKeyForKeyParts(keyParts),
    keyParts,
    canonicalKeyPartsJson: api.momentumCanonicalKeyPartsJson(keyParts),
  };
  return {
    ...dashboard,
    ...overrides,
    data,
    resultIdentity,
    resultKey: resultIdentity.resultKey,
  };
};
const mutateSelectedMomentumRow = (dashboard, changes) => ({
  ...dashboard,
  factorPolicyRanking: dashboard.factorPolicyRanking.map((row) => (
    row.selected ? { ...row, ...changes } : row
  )),
});

const liveSummaryWithoutDashboard = api.parseMomentum(liveMomentumSummary);
assert(liveSummaryWithoutDashboard.unavailable === true && liveSummaryWithoutDashboard.rows.length === 0, 'Momentum live-market summary cannot bypass dashboard provenance validation');

const liveProvenanceMutations = [
  ['empty priceSources', { priceSources: [] }],
  ['empty sourceHealth', { sourceHealth: [] }],
  ['well-formed priceSources content without a matching canonical hash', {
    priceSources: [{ symbol: 'LIVE', price_source: 'fabricated_provider' }],
  }],
  ['well-formed sourceHealth content without a matching canonical hash', {
    sourceHealth: [{ source: 'fabricated_source', status: 'ok' }],
  }],
  ['case-insensitive duplicate price-source symbols', {
    priceSources: [
      ...liveMomentumDashboard.priceSources,
      { symbol: 'live', price_source: 'duplicate_fixture' },
    ],
  }],
  ['missing sourceHealth source', { sourceHealth: [{ source: '', status: 'ok' }] }],
  ['missing sourceHealth status', { sourceHealth: [{ source: 'fixture_market_data', status: '' }] }],
];
for (const [label, mutation] of liveProvenanceMutations) {
  const changed = { ...liveMomentumDashboard, ...mutation };
  assert(!api.isMomentumDashboardV4(changed), `Momentum live provenance rejects ${label}`);
}

const insufficientCoverageData = {
  ...liveMomentumDashboard.data,
  analyzedSecurityCount: 2,
  analyzedSymbols: ['LIVE', 'MISSING'],
};
const insufficientCoverageDashboard = rekeyMomentumDashboardForData(
  liveMomentumDashboard,
  insufficientCoverageData,
);
assert(!api.isMomentumDashboardV4(insufficientCoverageDashboard), 'Momentum priceSources must cover every analyzed security with unique symbols');

for (const hashField of Object.keys(liveMomentumInputSha256)) {
  const invalidHashData = {
    ...liveMomentumDashboard.data,
    inputSha256: {
      ...liveMomentumDashboard.data.inputSha256,
      [hashField]: 'NOT-A-LOWERCASE-SHA256',
    },
  };
  const invalidHashDashboard = rekeyMomentumDashboardForData(
    liveMomentumDashboard,
    invalidHashData,
  );
  assert(!api.isMomentumDashboardV4(invalidHashDashboard), `Momentum live provenance requires a lowercase 64-hex ${hashField} hash`);
}

for (const [label, inputSha256] of [
  ['missing hash key', Object.fromEntries(
    Object.entries(liveMomentumInputSha256).filter(([field]) => field !== 'rawCloses'),
  )],
  ['extra hash key', { ...liveMomentumInputSha256, unexpectedHash: 'a'.repeat(64) }],
]) {
  const changedData = { ...liveMomentumDashboard.data, inputSha256 };
  const changedDashboard = rekeyMomentumDashboardForData(liveMomentumDashboard, changedData);
  assert(!api.isMomentumDashboardV4(changedDashboard), `Momentum live inputSha256 rejects ${label}`);
}

const analyzedSymbolMutations = [
  ['empty analyzedSymbols', [], 0],
  ['blank analyzed symbol', ['LIVE', '  '], 2],
  ['case-insensitive duplicate analyzed symbols', ['LIVE', 'live'], 2],
];
for (const [label, analyzedSymbols, analyzedSecurityCount] of analyzedSymbolMutations) {
  const changedData = {
    ...liveMomentumDashboard.data,
    analyzedSymbols,
    analyzedSecurityCount,
  };
  const changedDashboard = rekeyMomentumDashboardForData(liveMomentumDashboard, changedData);
  assert(!api.isMomentumDashboardV4(changedDashboard), `Momentum live provenance rejects ${label}`);
}
const analyzedSymbolLengthMismatchData = {
  ...liveMomentumDashboard.data,
  analyzedSymbols: ['LIVE'],
  analyzedSecurityCount: 2,
};
assert(!api.isMomentumDashboardV4(
  rekeyMomentumDashboardForData(liveMomentumDashboard, analyzedSymbolLengthMismatchData),
), 'Momentum analyzedSymbols length must equal analyzedSecurityCount');

const twoAnalyzedSymbolPriceSources = [
  ...liveMomentumDashboard.priceSources,
  { symbol: 'ALT', price_source: 'fixture_adjusted_close' },
];
const twoAnalyzedSymbolsData = {
  ...liveMomentumDashboard.data,
  analyzedSecurityCount: 2,
  analyzedSymbols: ['LIVE', 'ALT'],
  inputSha256: {
    ...liveMomentumDashboard.data.inputSha256,
    priceSources: api.momentumCanonicalRecordsSha256(twoAnalyzedSymbolPriceSources),
  },
};
const twoAnalyzedSymbolsDashboard = rekeyMomentumDashboardForData(
  liveMomentumDashboard,
  twoAnalyzedSymbolsData,
  {
    priceSources: twoAnalyzedSymbolPriceSources,
  },
);
assert(api.isMomentumDashboardV4(twoAnalyzedSymbolsDashboard), 'Momentum analyzedSymbols supports an ordered, unique, fully covered candidate set');
const reorderedSymbolsData = {
  ...twoAnalyzedSymbolsData,
  analyzedSymbols: ['ALT', 'LIVE'],
};
const reorderedSymbolsSnapshot = {
  ...marketSnapshotFromMomentumData(reorderedSymbolsData),
  candidateSymbolsSha256: twoAnalyzedSymbolsDashboard.resultIdentity.keyParts.marketSnapshot
    .candidateSymbolsSha256,
};
const reorderedSymbolsKeyParts = {
  ...twoAnalyzedSymbolsDashboard.resultIdentity.keyParts,
  marketSnapshot: reorderedSymbolsSnapshot,
};
const reorderedSymbolsIdentity = {
  identityVersion: 'momentum-result-identity-v1',
  resultKey: api.momentumResultKeyForKeyParts(reorderedSymbolsKeyParts),
  keyParts: reorderedSymbolsKeyParts,
  canonicalKeyPartsJson: api.momentumCanonicalKeyPartsJson(reorderedSymbolsKeyParts),
};
const reorderedSymbolsDashboard = {
  ...twoAnalyzedSymbolsDashboard,
  data: reorderedSymbolsData,
  resultIdentity: reorderedSymbolsIdentity,
  resultKey: reorderedSymbolsIdentity.resultKey,
};
assert(!api.isMomentumDashboardV4(reorderedSymbolsDashboard), 'Momentum candidateSymbolsSha256 binds the exact analyzedSymbols order');

for (const field of ['priceBasis', 'volumeBasis', 'rawCloseProxySymbolCount']) {
  const changed = {
    ...liveMomentumDashboard,
    data: {
      ...liveMomentumDashboard.data,
      [field]: field === 'rawCloseProxySymbolCount' ? 1 : `mutated_${field}`,
    },
  };
  assert(!api.isMomentumDashboardV4(changed), `Momentum resultIdentity marketSnapshot binds data.${field}`);
}

assert(
  momentumDashboardV4.factorDefinitions.length === 64
    && momentumDashboardV4.factorPolicyRanking.length === 256
    && momentumDashboardV4.gridAccounting.independentFactorCount === 61
    && momentumDashboardV4.gridAccounting.diagnosticAliasFactorCount === 3
    && momentumDashboardV4.gridAccounting.expectedIndependentPairCount === 244
    && momentumDashboardV4.gridAccounting.diagnosticAliasPairCount === 12,
  'Momentum canonical consumer fixture preserves 64/61/3 factors and 244/12/256 pairs',
);
const missingFactorDefinitionDashboard = {
  ...momentumDashboardV4,
  factorDefinitions: momentumDashboardV4.factorDefinitions.slice(0, -1),
};
assert(!api.isMomentumDashboardV4(missingFactorDefinitionDashboard), 'Momentum canonical grid rejects a missing factor definition');
const missingGridPairDashboard = {
  ...momentumDashboardV4,
  factorPolicyRanking: momentumDashboardV4.factorPolicyRanking.slice(0, -1),
};
assert(!api.isMomentumDashboardV4(missingGridPairDashboard), 'Momentum canonical grid rejects a missing factor-policy pair');
const duplicateGridPairDashboard = {
  ...momentumDashboardV4,
  factorPolicyRanking: [
    ...momentumDashboardV4.factorPolicyRanking.slice(0, -1),
    { ...momentumDashboardV4.factorPolicyRanking[0], selected: false },
  ],
};
assert(!api.isMomentumDashboardV4(duplicateGridPairDashboard), 'Momentum canonical grid rejects duplicate factor-policy pairs');
const alteredGridAccountingDashboard = {
  ...momentumDashboardV4,
  gridAccounting: {
    ...momentumDashboardV4.gridAccounting,
    diagnosticAliasPairCount: 8,
  },
};
assert(!api.isMomentumDashboardV4(alteredGridAccountingDashboard), 'Momentum canonical grid rejects non-244/12/256 accounting');
const alteredAliasStatusDashboard = {
  ...momentumDashboardV4,
  factorPolicyRanking: momentumDashboardV4.factorPolicyRanking.map((row) => (
    row.factor === 'compatibility_alias_1' && row.policy_id === 'equal_weight'
      ? { ...row, comparison_status: 'available' }
      : row
  )),
};
assert(!api.isMomentumDashboardV4(alteredAliasStatusDashboard), 'Momentum canonical grid requires all 12 alias rows to remain duplicate_alias diagnostics');
assert(!api.isMomentumSummaryV4({
  ...momentumSummaryV4,
  gridAccounting: { ...momentumGridAccounting, independentFactorCount: 60 },
}), 'Momentum compact summary cannot advertise noncanonical grid accounting');

assert(api.isMomentumDashboardV4(momentumDashboardV4), 'Momentum concentration guardrails pass exactly at all six configured boundaries');
const medianDiagnosticDashboard = mutateSelectedMomentumRow(momentumDashboardV4, {
  median_target_effective_names: -100,
  median_target_hhi: 999,
});
assert(api.isMomentumDashboardV4(medianDiagnosticDashboard), 'Momentum target medians remain diagnostic-only and never drive concentration guardrails');
const concentrationMetricBreaches = {
  min_target_effective_names: 0.5,
  current_target_effective_names: 0.5,
  max_target_hhi: 1.1,
  current_target_hhi: 1.1,
  max_target_weight: 0.7,
  current_target_max_weight: 0.7,
};
for (const [metric, value] of Object.entries(concentrationMetricBreaches)) {
  assert(!api.isMomentumDashboardV4(
    mutateSelectedMomentumRow(momentumDashboardV4, { [metric]: value }),
  ), `Momentum selected-pair concentration metric ${metric} must match its canonical threshold/current target semantics`);
}
for (const flag of [
  'guardrail_historical_effective_names',
  'guardrail_current_effective_names',
  'guardrail_historical_target_hhi',
  'guardrail_current_target_hhi',
  'guardrail_historical_target_weight',
  'guardrail_current_target_weight',
]) {
  assert(!api.isMomentumDashboardV4(
    mutateSelectedMomentumRow(momentumDashboardV4, { [flag]: false }),
  ), `Momentum selected-pair guardrail boolean ${flag} must equal the recomputed threshold result`);
}
assert(!api.isMomentumDashboardV4(
  mutateSelectedMomentumRow(momentumDashboardV4, {
    min_target_effective_names: 0.5,
    guardrail_historical_effective_names: false,
  }),
), 'Momentum selected winner must pass all six concentration guardrails even when a failed flag matches its metric comparison');
for (const [field, value] of [
  ['comparison_status', 'insufficient_history'],
  ['selection_status', 'absolute_guardrail_excluded'],
  ['selection_eligible', false],
  ['standard_guardrail_pass', false],
  ['contribution_guardrail_pass', false],
  ['absolute_guardrail_pass', false],
  ['selection_score', null],
]) {
  assert(!api.isMomentumDashboardV4(
    mutateSelectedMomentumRow(momentumDashboardV4, { [field]: value }),
  ), `Momentum selected winner requires canonical ${field}`);
}

const unselectedPair = momentumDashboardV4.factorPolicyRanking.find((row) => (
  row.comparison_status === 'available' && row.selected !== true
));
const mutateUnselectedMomentumRow = (dashboard, changes) => ({
  ...dashboard,
  factorPolicyRanking: dashboard.factorPolicyRanking.map((row) => (
    row.factor === unselectedPair.factor && row.policy_id === unselectedPair.policy_id
      ? { ...row, ...changes }
      : row
  )),
});
for (const [metric, value] of Object.entries(concentrationMetricBreaches)) {
  assert(!api.isMomentumDashboardV4(
    mutateUnselectedMomentumRow(momentumDashboardV4, { [metric]: value }),
  ), `Momentum all-row concentration validation rejects a mismatched unselected ${metric}`);
}
for (const flag of [
  'guardrail_historical_effective_names',
  'guardrail_current_effective_names',
  'guardrail_historical_target_hhi',
  'guardrail_current_target_hhi',
  'guardrail_historical_target_weight',
  'guardrail_current_target_weight',
]) {
  assert(!api.isMomentumDashboardV4(
    mutateUnselectedMomentumRow(momentumDashboardV4, { [flag]: false }),
  ), `Momentum all-row concentration validation rejects a mismatched unselected ${flag}`);
}
const currentConcentrationMismatchDashboard = {
  ...momentumDashboardV4,
  currentResearchTarget: {
    ...momentumDashboardV4.currentResearchTarget,
    concentration: {
      ...momentumDashboardV4.currentResearchTarget.concentration,
      effectiveNames: 2,
    },
  },
};
assert(!api.isMomentumDashboardV4(currentConcentrationMismatchDashboard), 'Momentum currentResearchTarget concentration must be recomputed from canonical weights and cash');
const medianGuardrailProfileDashboard = {
  ...momentumDashboardV4,
  selectionDecision: {
    ...momentumDashboardV4.selectionDecision,
    guardrailProfile: {
      ...momentumDashboardV4.selectionDecision.guardrailProfile,
      rules: momentumDashboardV4.selectionDecision.guardrailProfile.rules.map((rule) => (
        rule.id === 'minimum_historical_target_effective_names'
          ? { ...rule, metric: 'median_target_effective_names' }
          : rule
      )),
    },
  },
};
assert(!api.isMomentumDashboardV4(medianGuardrailProfileDashboard), 'Momentum guardrail profile rejects median concentration metrics');

const dashboardWithGuardrailProfile = (guardrailProfile, overrides = {}) => ({
  ...momentumDashboardV4,
  ...overrides,
  selectionDecision: {
    ...momentumDashboardV4.selectionDecision,
    guardrailProfile,
  },
});
const exactProfileMutations = [
  ['missing rule', {
    ...momentumAbsoluteGuardrailProfile,
    rules: momentumAbsoluteGuardrailRules.slice(1),
  }],
  ['extra rule', {
    ...momentumAbsoluteGuardrailProfile,
    rules: [
      ...momentumAbsoluteGuardrailRules,
      { id: 'bogus', metric: 'bogus', operator: '<=', threshold: 1, unit: 'ratio' },
    ],
  }],
  ['reordered rules', {
    ...momentumAbsoluteGuardrailProfile,
    rules: [
      momentumAbsoluteGuardrailRules[1],
      momentumAbsoluteGuardrailRules[0],
      ...momentumAbsoluteGuardrailRules.slice(2),
    ],
  }],
];
for (const [label, guardrailProfile] of exactProfileMutations) {
  assert(!api.isMomentumDashboardV4(
    dashboardWithGuardrailProfile(guardrailProfile),
  ), `Momentum exact 12-rule guardrail profile rejects ${label}`);
}
for (const [field, value] of [
  ['id', 'legacy-guardrail-profile'],
  ['metric', 'median_target_effective_names'],
  ['operator', '<='],
  ['threshold', 999],
  ['unit', 'wrong_unit'],
]) {
  const rules = momentumAbsoluteGuardrailRules.map((rule, index) => (
    index === 0 ? { ...rule, [field]: value } : rule
  ));
  assert(!api.isMomentumDashboardV4(
    dashboardWithGuardrailProfile({ ...momentumAbsoluteGuardrailProfile, rules }),
  ), `Momentum exact 12-rule guardrail profile rejects a mutated rule ${field}`);
}
for (const [label, changes] of [
  ['profile id', { id: 'legacy-profile' }],
  ['profile version', { version: 2 }],
  ['policy neutrality', { policyNeutral: false }],
  ['extreme-event action', { extremeEventAction: 'penalize' }],
  ['extreme-event penalty', { extremeEventPenaltyPoints: 99 }],
  ['required contracts', {
    requiredContracts: {
      ...momentumAbsoluteGuardrailProfile.requiredContracts,
      currentTargetAvailable: false,
    },
  }],
  ['extra required contract', {
    requiredContracts: {
      ...momentumAbsoluteGuardrailProfile.requiredContracts,
      legacyContract: true,
    },
  }],
]) {
  assert(!api.isMomentumDashboardV4(
    dashboardWithGuardrailProfile({ ...momentumAbsoluteGuardrailProfile, ...changes }),
  ), `Momentum exact guardrail profile rejects mutated ${label}`);
}
assert(!api.isMomentumDashboardV4({
  ...momentumDashboardV4,
  researchInputs: { ...momentumResearchInputs, selectionMinSharpe: 999 },
}), 'Momentum guardrail profile thresholds remain derived from canonical research inputs');
assert(!api.isMomentumDashboardV4({
  ...momentumDashboardV4,
  config: { ...momentumConfig, selection_min_sharpe: 999 },
}), 'Momentum guardrail profile rejects research-input/config threshold drift');

const unsupportedModeMomentum = api.parseMomentum({
  ...momentumSummaryV4,
  dataMode: 'offline',
});
assert(unsupportedModeMomentum.rows.length === 0 && unsupportedModeMomentum.meta.statusState === 'unavailable', 'Momentum unsupported offline mode is rejected instead of being treated as local data');

const conflictingModeMomentum = api.parseMomentum(momentumSummaryV4, {
  ...localMomentumDashboard,
});
assert(conflictingModeMomentum.unavailable === true && conflictingModeMomentum.rows.length === 0, 'Momentum source mode and label conflicts fail closed because marketSnapshot binds both values');

const conflictingEvidenceMomentum = api.parseMomentum(momentumSummaryV4, {
  ...momentumDashboardV4,
  researchScope: {
    ...momentumDashboardV4.researchScope,
    evidenceStatus: 'conflicting_evidence',
  },
});
assert(conflictingEvidenceMomentum.rows[0].modelWeight === 0.6, 'Momentum non-identity evidence conflict does not hide selected holdings');
assert(conflictingEvidenceMomentum.meta.statusState === 'degraded' && conflictingEvidenceMomentum.meta.degradedReasons.some((reason) => reason.startsWith('evidence_status_mismatch:')), 'Momentum evidence conflict remains visible as a degraded reason');

const demoMomentumDossier = api.watchlistMatchesForToken([
  { project: api.PROJECTS.find((project) => project.id === 'momentum'), summary: validMomentum },
], 'SEL');
assert(demoMomentumDossier.length === 1 && /합성 데모/.test(demoMomentumDossier[0].detail) && /capped_linear_rank/.test(demoMomentumDossier[0].detail) && /현금 40%/.test(demoMomentumDossier[0].detail), 'Momentum watchlist preserves the data label, selected policy, and cash alongside selected holdings');

const resultKeyMismatchMomentum = api.parseMomentum(momentumSummaryV4, {
  ...momentumDashboardV4,
  resultIdentity: { ...momentumResultIdentity, resultKey: 'different-result-key' },
  resultKey: 'different-result-key',
});
assert(
  resultKeyMismatchMomentum.unavailable === true && resultKeyMismatchMomentum.rows.length === 0,
  'Momentum v4 summary/dashboard resultKey mismatch fails closed with zero holdings',
);

const identityKeyPartsMismatchMomentum = api.parseMomentum(momentumSummaryV4, {
  ...momentumDashboardV4,
  resultIdentity: {
    ...momentumResultIdentity,
    keyParts: {
      ...momentumResultIdentity.keyParts,
      marketSnapshot: {
        ...momentumResultIdentity.keyParts.marketSnapshot,
        dataAsOf: '2026-06-17',
      },
    },
  },
});
assert(
  identityKeyPartsMismatchMomentum.unavailable === true && identityKeyPartsMismatchMomentum.rows.length === 0,
  'Momentum v4 full resultIdentity mismatch fails closed even when resultKey text is unchanged',
);

const topLevelResultKeyMismatchMomentum = api.parseMomentum(momentumSummaryV4, {
  ...momentumDashboardV4,
  resultKey: 'stale-alias-result-key',
});
assert(
  topLevelResultKeyMismatchMomentum.unavailable === true && topLevelResultKeyMismatchMomentum.rows.length === 0,
  'Momentum v4 top-level resultKey must equal its nested resultIdentity resultKey',
);

const reorderedIdentityMomentum = api.parseMomentum(momentumSummaryV4, {
  ...momentumDashboardV4,
  resultIdentity: {
    keyParts: {
      marketSnapshot: {
        analyzedSecurityCount: 50,
        providerReturnedCandidateCount: 50,
        requestedCandidateCount: 50,
        inputSha256: { prices: 'c'.repeat(64) },
        dataAsOf: '2026-06-18',
        requestedThrough: '2026-06-18',
        rawCloseProxySymbolCount: 0,
        volumeBasis: 'deterministic_share_volume_fixture',
        priceBasis: 'deterministic_adjusted_close_fixture',
        provider: null,
        sourceLabel: 'deterministic demo fixture',
        sourceMode: 'demo',
      },
      inputs: { maxWeight: 0.6, topN: 20 },
      canonicalJsonVersion: 'rfc8785-jcs-v1',
      identityVersion: 'momentum-result-identity-v1',
    },
    resultKey: momentumResultIdentity.resultKey,
    identityVersion: 'momentum-result-identity-v1',
    canonicalKeyPartsJson: momentumResultIdentity.canonicalKeyPartsJson,
  },
});
assert(reorderedIdentityMomentum.rows.length === 1, 'Momentum v4 resultIdentity equality is structural and independent of JSON object key order');

const unsupportedIdentityMomentum = api.parseMomentum({
  ...momentumSummaryV4,
  resultIdentity: {
    ...momentumResultIdentity,
    identityVersion: 'unsupported-v999',
  },
}, {
  ...momentumDashboardV4,
  resultIdentity: {
    ...momentumResultIdentity,
    identityVersion: 'unsupported-v999',
  },
});
assert(unsupportedIdentityMomentum.unavailable === true && unsupportedIdentityMomentum.rows.length === 0, 'Momentum v4 unsupported result identity version fails closed');

const noncanonicalIdentity = {
  ...momentumResultIdentity,
  resultKey: 'f'.repeat(64),
};
const noncanonicalIdentityMomentum = api.parseMomentum({
  ...momentumSummaryV4,
  resultIdentity: noncanonicalIdentity,
  resultKey: noncanonicalIdentity.resultKey,
}, {
  ...momentumDashboardV4,
  resultIdentity: noncanonicalIdentity,
  resultKey: noncanonicalIdentity.resultKey,
});
assert(noncanonicalIdentityMomentum.unavailable === true && noncanonicalIdentityMomentum.rows.length === 0, 'Momentum v4 non-canonical resultKey fails closed even when both sources agree');

const paddedCanonicalJson = ` ${momentumResultIdentity.canonicalKeyPartsJson} `;
const paddedCanonicalIdentity = {
  ...momentumResultIdentity,
  canonicalKeyPartsJson: paddedCanonicalJson,
  resultKey: api.momentumSha256Hex(paddedCanonicalJson),
};
const paddedCanonicalIdentityMomentum = api.parseMomentum({
  ...momentumSummaryV4,
  resultIdentity: paddedCanonicalIdentity,
  resultKey: paddedCanonicalIdentity.resultKey,
}, {
  ...momentumDashboardV4,
  resultIdentity: paddedCanonicalIdentity,
  resultKey: paddedCanonicalIdentity.resultKey,
});
assert(paddedCanonicalIdentityMomentum.unavailable === true && paddedCanonicalIdentityMomentum.rows.length === 0, 'Momentum v4 rejects a self-consistent but non-JCS canonical transport');

const mismatchedMomentum = api.parseMomentum(momentumSummaryV4, {
  ...momentumDashboardV4,
  selectedFactor: 'other_mom',
});
assert(mismatchedMomentum.rows.length === 0, 'Momentum v4 selectedFactor mismatch fails closed instead of relabeling holdings');

const modelFactorMismatchMomentum = api.parseMomentum(momentumSummaryV4, {
  ...momentumDashboardV4,
  currentResearchTarget: { ...momentumDashboardV4.currentResearchTarget, factor: 'other_mom' },
});
assert(modelFactorMismatchMomentum.rows.length === 0, 'Momentum v4 currentResearchTarget factor mismatch fails closed');

const policyMismatchMomentum = api.parseMomentum(momentumSummaryV4, {
  ...momentumDashboardV4,
  selectedWeightingPolicy: 'equal_weight',
});
assert(policyMismatchMomentum.rows.length === 0, 'Momentum v4 summary/dashboard weighting-policy mismatch fails closed');

const modelPolicyMismatchMomentum = api.parseMomentum(momentumSummaryV4, {
  ...momentumDashboardV4,
  currentResearchTarget: { ...momentumDashboardV4.currentResearchTarget, weightingPolicyId: 'equal_weight' },
});
assert(modelPolicyMismatchMomentum.rows.length === 0, 'Momentum v4 currentResearchTarget weighting-policy mismatch fails closed');

const dashboardAsOfMismatchMomentum = api.parseMomentum(momentumSummaryV4, {
  ...momentumDashboardV4,
  data: { ...momentumDashboardV4.data, asOf: '2026-06-17' },
});
assert(dashboardAsOfMismatchMomentum.rows.length === 0, 'Momentum v4 summary/dashboard as-of mismatch fails closed');

const modelAsOfMismatchMomentum = api.parseMomentum(momentumSummaryV4, {
  ...momentumDashboardV4,
  currentResearchTarget: { ...momentumDashboardV4.currentResearchTarget, asOf: '2026-06-17' },
});
assert(modelAsOfMismatchMomentum.rows.length === 0, 'Momentum v4 currentResearchTarget as-of mismatch fails closed');

const modelSignalDateMismatchMomentum = api.parseMomentum(momentumSummaryV4, {
  ...momentumDashboardV4,
  currentResearchTarget: { ...momentumDashboardV4.currentResearchTarget, signalDate: '1999-12-31' },
});
assert(modelSignalDateMismatchMomentum.rows.length === 0, 'Momentum v4 stale currentResearchTarget signalDate fails closed against the canonical as-of date');

const caseOnlySummarySymbolMomentum = api.parseMomentum({
  ...momentumSummaryV4,
  weights: [{ ...momentumSummaryV4.weights[0], symbol: 'sel' }],
}, momentumDashboardV4);
assert(caseOnlySummarySymbolMomentum.rows[0].symbol === 'SEL', 'Momentum v4 cross-source symbol identity comparison is case-insensitive');

const changedSummarySymbolMomentum = api.parseMomentum({
  ...momentumSummaryV4,
  weights: [{ ...momentumSummaryV4.weights[0], symbol: 'OTHER' }],
}, momentumDashboardV4);
assert(changedSummarySymbolMomentum.rows.length === 0, 'Momentum v4 summary/dashboard holding-symbol mismatch fails closed');

const twoHoldingWeights = [
  { rank: 1, symbol: 'SEL', name: 'Selected Co', factorScore: 9, weight: 0.4 },
  { rank: 2, symbol: 'ALT', name: 'Alternate Co', factorScore: 7, weight: 0.2 },
];
const twoHoldingTarget = {
  ...momentumDashboardV4.currentResearchTarget,
  weights: twoHoldingWeights,
  concentration: concentrationForWeights(twoHoldingWeights, 0.4),
};
const twoHoldingSummary = {
  ...momentumSummaryV4,
  currentResearchTarget: twoHoldingTarget,
  weights: twoHoldingWeights,
};
const twoHoldingDashboard = {
  ...momentumDashboardV4,
  currentResearchTarget: twoHoldingTarget,
  factorPolicyRanking: momentumDashboardV4.factorPolicyRanking.map((row) => (
    row.selected
      ? {
        ...row,
        current_target_effective_names: twoHoldingTarget.concentration.effectiveNames,
        current_target_hhi: twoHoldingTarget.concentration.riskySleeveHhi,
        current_target_max_weight: twoHoldingTarget.concentration.maxWeight,
      }
      : row
  )),
};
const changedSummaryWeightMomentum = api.parseMomentum({
  ...twoHoldingSummary,
  weights: [
    { ...twoHoldingSummary.weights[0], weight: 0.3 },
    { ...twoHoldingSummary.weights[1], weight: 0.3 },
  ],
}, twoHoldingDashboard);
assert(changedSummaryWeightMomentum.rows.length === 0, 'Momentum v4 independently valid summary/dashboard holding-weight mismatch fails closed');

const changedSummaryCashMomentum = api.parseMomentum({
  ...twoHoldingSummary,
  cashWeight: 0.5,
  weights: [
    { ...twoHoldingSummary.weights[0], weight: 0.3 },
    { ...twoHoldingSummary.weights[1] },
  ],
}, twoHoldingDashboard);
assert(changedSummaryCashMomentum.rows.length === 0, 'Momentum v4 independently valid summary/dashboard cash mismatch fails closed');

const changedSummaryMaxWeightMomentum = api.parseMomentum({
  ...momentumSummaryV4,
  maxWeight: 0.7,
}, momentumDashboardV4);
assert(changedSummaryMaxWeightMomentum.rows.length === 0, 'Momentum v4 summary/dashboard max-weight contract mismatch fails closed');

const duplicateMomentum = api.parseMomentum({
  ...momentumSummaryV4,
  cashWeight: 0.4,
  weights: [
    { rank: 1, symbol: 'DUP', name: 'Duplicate One', factorScore: 3, weight: 0.3 },
    { rank: 2, symbol: 'dup', name: 'Duplicate Two', factorScore: 2, weight: 0.3 },
  ],
});
assert(duplicateMomentum.rows.length === 0, 'Momentum v4 duplicate symbols fail closed case-insensitively');

const cappedMomentum = api.parseMomentum({
  ...momentumSummaryV4,
  cashWeight: 0.3,
  weights: [{ rank: 1, symbol: 'CAP', name: 'Over Cap', factorScore: 3, weight: 0.7 }],
});
assert(cappedMomentum.rows.length === 0, 'Momentum v4 holding above maxWeight fails closed');

const badSumMomentum = api.parseMomentum({
  ...momentumSummaryV4,
  cashWeight: 0.3,
  weights: [{ rank: 1, symbol: 'SUM', name: 'Bad Sum', factorScore: 3, weight: 0.6 }],
});
assert(badSumMomentum.rows.length === 0, 'Momentum v4 weights plus cash not equal to one fail closed');

const negativeWeightMomentum = api.parseMomentum({
  ...momentumSummaryV4,
  cashWeight: 1.1,
  weights: [{ rank: 1, symbol: 'NEG', name: 'Negative', factorScore: 3, weight: -0.1 }],
});
assert(negativeWeightMomentum.rows.length === 0, 'Momentum v4 negative weights fail closed');

const nonfiniteWeightMomentum = api.parseMomentum({
  ...momentumSummaryV4,
  cashWeight: 0.4,
  weights: [{ rank: 1, symbol: 'NAN', name: 'Nonfinite', factorScore: 3, weight: Number.NaN }],
});
assert(nonfiniteWeightMomentum.rows.length === 0, 'Momentum v4 non-finite weights fail closed');

const zeroModelWeightMomentum = api.parseMomentum({
  ...momentumSummaryV4,
  cashWeight: 1,
  weights: [{ rank: 1, symbol: 'ZERO', name: 'Zero Co', factorScore: 3, weight: 0 }],
});
assert(zeroModelWeightMomentum.rows[0].modelWeight === 0, 'Momentum v4 explicit zero model weight is never signal-normalized');

const cashOnlyTarget = {
  ...momentumDashboardV4.currentResearchTarget,
  cashWeight: 1,
  weights: [],
  concentration: concentrationForWeights([], 1),
};
const cashOnlyMomentumSummary = {
  ...momentumSummaryV4,
  currentResearchTarget: cashOnlyTarget,
  cashWeight: 1,
  weights: [],
};
const cashOnlyMomentumDashboard = {
  ...momentumDashboardV4,
  currentResearchTarget: cashOnlyTarget,
  factorPolicyRanking: momentumDashboardV4.factorPolicyRanking.map((row) => (
    row.selected
      ? {
        ...row,
        current_target_effective_names: 0,
        current_target_hhi: 0,
        current_target_max_weight: 0,
        guardrail_current_effective_names: false,
      }
      : row
  )),
};
const cashOnlyMomentum = api.parseMomentum(cashOnlyMomentumSummary, cashOnlyMomentumDashboard);
assert(cashOnlyMomentum.unavailable === true && cashOnlyMomentum.rows.length === 0, 'Momentum v4 fails closed when a selected 100%-cash target breaches the current effective-names guardrail');
assert(!api.PANEL_ADAPTERS.momentum.hasUsableData(cashOnlyMomentum), 'Momentum panel cannot promote a selected target with a failed concentration guardrail');

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
const dramChartFixture = [
  { source: 'trendforce', name: 'High Price', points: [['2026-06-10', 60], ['2026-06-11', 66], ['2026-06-12', 72]] },
  { source: 'trendforce', name: 'Low Price', points: [['2026-06-10', 10], ['2026-06-11', 11], ['2026-06-12', 12]] },
];
const dramPriceMarkup = api.renderDramSourceChart('trendforce', dramChartFixture);
const dramIndexedMarkup = api.renderDramSourceChart('trendforce', dramChartFixture, 'indexed');
assert((dramPriceMarkup.match(/class="dram-series /g) || []).length === 2, 'DRAM price view preserves every input series');
assert((dramPriceMarkup.match(/class="dram-data-point/g) || []).length === 6, 'DRAM price view preserves every recorded point');
assert((dramPriceMarkup.match(/class="dram-legend-button"/g) || []).length === 2, 'DRAM legend exposes one selectable button per series');
assert((dramPriceMarkup.match(/data-keyboard-label=/g) || []).length === 6, 'DRAM points retain exact-value keyboard readout labels');
assert((dramPriceMarkup.match(/class="dram-chart-frame" tabindex="0"/g) || []).length === 1, 'DRAM chart keeps one keyboard entry point');
assert(!/dram-value-(?:layer|label)/.test(dramPriceMarkup), 'DRAM chart never renders the overlapping all-point value layer');
assert(dramPriceMarkup.indexOf('dram-chart-readout') < dramPriceMarkup.indexOf('dram-chart-frame'), 'DRAM exact-value readout stays outside and before the plot');
assert(/data-dram-scale-mode="price"/.test(dramPriceMarkup) && /data-dram-scale="price" aria-pressed="true"/.test(dramPriceMarkup), 'DRAM defaults to the original USD price axis');
assert(/data-dram-scale-mode="indexed"/.test(dramIndexedMarkup) && /상대 변화 · 첫 관측=100/.test(dramIndexedMarkup), 'DRAM indexed display mode clearly identifies its first-observation baseline');
assert(/72 USD · 시작=100 지수 120/.test(dramIndexedMarkup) && /12 USD · 시작=100 지수 120/.test(dramIndexedMarkup), 'DRAM indexed view keeps raw USD exact values alongside rebased display values');
assert((dramIndexedMarkup.match(/class="dram-data-point/g) || []).length === 6 && dramIndexedMarkup !== dramPriceMarkup, 'DRAM scale switching changes only presentation while retaining all points');

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
const etfGridYPositions = [...etfMiniMarkup.matchAll(/<line x1="76" x2="1088" y1="([0-9.]+)" y2="\1" stroke="#d9e2f1"/g)].map((match) => Number(match[1]));
assert((etfMiniMarkup.match(/stroke="#d9e2f1"/g) || []).length >= 4 && /최근 1개월 비중\(%\)/.test(etfMiniMarkup), 'ETF mini chart renders a taller multi-tick percent axis');
assert(Math.max(...etfGridYPositions) - Math.min(...etfGridYPositions) > 240, 'ETF mini chart percent axis uses the expanded vertical plotting area');
assert((etfMiniMarkup.match(/class="etf-data-point"/g) || []).length === 4, 'ETF mini chart renders every recorded daily point');
assert((etfMiniMarkup.match(/tabindex="0"/g) || []).length === 1 && /class="etf-mini-plot" tabindex="0"/.test(etfMiniMarkup), 'ETF mini chart uses one keyboard entry point on the chart frame');
assert(!/class="etf-data-point"[^>]*tabindex=/.test(etfMiniMarkup) && /etf-chart-readout/.test(etfMiniMarkup), 'ETF points leave the tab order while retaining an external exact-value readout');
assert((etfMiniMarkup.match(/class="legend-key"/g) || []).length === 2, 'ETF mini chart legend includes every TOP10 series');

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

const validPortPayload = {
  schemaVersion: 1,
  contract: 'quant-research-summary',
  projectId: 'port',
  generatedAt: '2026-07-28T06:13:36Z',
  dataAsOf: '2026-07-28',
  status: {
    state: 'degraded',
    label: '225개 가격 자산 · warnings 6',
    cadence: 'scheduled',
    expectedFreshnessDays: 5,
    warningCount: 6,
    criticalIssueCount: 0,
  },
  coverage: {
    assetCount: 225,
    historyAssetCount: 225,
    priceFallbackCount: 0,
    holdingsSourceCounts: { official: 3, live: 22, no_holdings: 17, proxy: 3 },
  },
  automation: { workflowUrl: 'https://github.com/SonChangGi/port/actions/workflows/update-data.yml' },
  primaryEntities: [{ symbol: 'SPY', name: 'SPY', metrics: { price: 739.09 } }],
  limitations: ['무료 공개 holdings는 지연될 수 있습니다.'],
};
const validPort = api.parsePort(validPortPayload);
assert(!api.validateAdapterContract(api.PANEL_ADAPTERS.port, { summary: validPortPayload }), 'Port adapter accepts its own public summary contract');
assert(api.PANEL_ADAPTERS.port.hasUsableData(validPort) && validPort.assetCount === 225 && validPort.warningCount === 6, 'Port adapter joins collection coverage into Hub health');
assert(api.briefingItemForRecord({ project: { id: 'port' }, summary: validPort }).detail.includes('가격 fallback 0개'), 'Port briefing exposes fallback and warning diagnostics');
const invalidPortHoldingsCounts = api.parsePort({
  ...validPortPayload,
  coverage: {
    ...validPortPayload.coverage,
    holdingsSourceCounts: { official: 3, live: -1 },
  },
});
assert(!invalidPortHoldingsCounts.contractValid, 'Port adapter rejects negative or non-integer holdings source counts');
const invalidPortState = api.parsePort({
  ...validPortPayload,
  status: {
    ...validPortPayload.status,
    state: 'mystery',
  },
});
assert(
  !invalidPortState.contractValid && !api.PANEL_ADAPTERS.port.hasUsableData(invalidPortState),
  'Port adapter rejects unsupported public status states',
);
const criticalPort = api.parsePort({
  ...validPortPayload,
  status: {
    ...validPortPayload.status,
    criticalIssueCount: 1,
  },
});
assert(
  !criticalPort.contractValid && !api.PANEL_ADAPTERS.port.hasUsableData(criticalPort),
  'Port adapter fails closed when critical collection issues are present',
);

const validRegimePayload = {
  meta: {
    mode: 'demo',
    result_version: 'weekly-regime-result-v4',
    generated_at: '2026-08-08T00:00:00Z',
    data_as_of: '2026-08-07T20:00:00Z',
  },
  sources: [
    { id: 'synthetic_market_fixture', license_class: 'synthetic_fixture' },
    { id: 'synthetic_macro_fixture', license_class: 'synthetic_fixture' },
  ],
  weekly: [{
    date: '2026-08-07',
    current: {
      state: 'risk_on',
      probabilities: { risk_on: 0.6, transition: 0.3, risk_off: 0.1 },
      confidence: 0.6,
    },
    next_week: {
      state: 'transition',
      probabilities: { risk_on: 0.3, transition: 0.6, risk_off: 0.1 },
      confidence: 0.6,
      date: '2026-08-14',
    },
    transition_probability: 0.7,
    transition_risk: {
      '1w': { probability: 0.7, target_end: '2026-08-14' },
      '4w': { probability: 0.8, target_end: '2026-09-04' },
      '13w': { probability: 0.9, target_end: '2026-11-06' },
    },
  }],
};
const validRegime = api.parseRegime(validRegimePayload);
assert(
  api.PANEL_ADAPTERS.regime.hasUsableData(validRegime)
    && validRegime.currentStateLabel === '위험 선호'
    && validRegime.nextStateLabel === '전환'
    && validRegime.transitionRisk13w === 0.9,
  'Regime adapter parses current, next-week, and 1/4/13-week probabilities from a synthetic demo',
);
assert(
  api.briefingItemForRecord({ project: { id: 'regime' }, summary: validRegime }).detail.includes('13주 90%'),
  'Regime briefing derives risk and date values from the public demo payload',
);
const validLiveRegimePayload = {
  ...validRegimePayload,
  meta: { ...validRegimePayload.meta, mode: 'live', status: 'degraded' },
  sources: [
    { id: 'alpha_vantage', license_class: 'private_noncommercial' },
    { id: 'alfred', license_class: 'user_confirmed_ml_storage_derived' },
  ],
};
const validLiveRegime = api.parsePanelSafely(api.PANEL_ADAPTERS.regime, {
  summary: validLiveRegimePayload,
});
assert(
  validLiveRegime.ok
    && validLiveRegime.data.publicPayloadValid
    && validLiveRegime.data.meta.dataModeLabel === 'Live 파생 결과'
    && validLiveRegime.data.meta.statusState === 'degraded',
  'Regime adapter accepts the exact personal noncommercial live-derived source contract',
);
const rejectedProviderRegime = api.parsePanelSafely(api.PANEL_ADAPTERS.regime, {
  summary: {
    ...validRegimePayload,
    sources: [{ id: 'alpha_vantage', license_class: 'private_noncommercial' }],
  },
});
assert(
  !rejectedProviderRegime.ok && /not synthetic/.test(rejectedProviderRegime.error),
  'Regime demo adapter rejects provider-derived source metadata',
);
const rejectedLicenseRegime = api.parsePanelSafely(api.PANEL_ADAPTERS.regime, {
  summary: {
    ...validRegimePayload,
    sources: [{ id: 'synthetic_market_fixture', license_class: 'private_noncommercial' }],
  },
});
assert(
  !rejectedLicenseRegime.ok && /not synthetic_fixture/.test(rejectedLicenseRegime.error),
  'Regime adapter requires synthetic_fixture licensing for every public source',
);
const rejectedLiveLicenseRegime = api.parsePanelSafely(api.PANEL_ADAPTERS.regime, {
  summary: {
    ...validLiveRegimePayload,
    sources: [
      { id: 'alpha_vantage', license_class: 'synthetic_fixture' },
      { id: 'alfred', license_class: 'user_confirmed_ml_storage_derived' },
    ],
  },
});
assert(
  !rejectedLiveLicenseRegime.ok && /invalid license_class/.test(rejectedLiveLicenseRegime.error),
  'Regime live adapter rejects a mismatched provider license contract',
);
const rejectedProbabilityRegime = api.parsePanelSafely(api.PANEL_ADAPTERS.regime, {
  summary: {
    ...validRegimePayload,
    weekly: [{
      ...validRegimePayload.weekly[0],
      current: {
        ...validRegimePayload.weekly[0].current,
        probabilities: { risk_on: 0.8, transition: 0.3, risk_off: 0.1 },
      },
    }],
  },
});
assert(
  !rejectedProbabilityRegime.ok && /sum to one/.test(rejectedProbabilityRegime.error),
  'Regime adapter rejects malformed three-state probability distributions',
);
const unavailableRegime = api.PANEL_ADAPTERS.regime.fallback();
assert(
  unavailableRegime.unavailable === true
    && unavailableRegime.dataAsOf === ''
    && unavailableRegime.currentConfidence === null
    && unavailableRegime.transitionRisk13w === null,
  'Regime unavailable fallback contains no hardcoded market state, probability, or date',
);

assert(Object.keys(api.PANEL_ADAPTERS).length === 8, 'panel adapter manifest has eight active public summary adapters including Regime');
assert(Object.keys(api.PANEL_ADAPTERS.port.sourceUrls).length === 1, 'Port adapter reads only its independent summary.json');
assert(Object.keys(api.PANEL_ADAPTERS.regime.sourceUrls).length === 1, 'Regime adapter reads only its public result JSON');

const nullEntryMomentum = api.parseMomentum({
  ...momentumSummaryV4,
  selectedFactor: 'null_drift',
  weights: [null, 'bad'],
});
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

const nullEntrySox = api.parseSox({ schemaVersion: 1, contract: 'quant-research-summary', projectId: 'sox', status: 'ok', primaryEntities: [null, 'bad', { id: 'DDD', metrics: { score: 0.1 } }] });
assert(nullEntrySox.rows.length === 1 && nullEntrySox.rows[0].ticker === 'DDD', 'SOX null/non-object entries resolve without throwing');

const throwingAdapter = { parse: () => { throw new Error('fixture boom'); } };
const safeParse = api.parsePanelSafely(throwingAdapter, {});
assert(safeParse.ok === false && /Payload parse failed/.test(safeParse.error), 'panel parser exceptions convert to explicit fallback reason');
const contractMismatch = api.validateAdapterContract(api.PANEL_ADAPTERS.sox, { summary: { schemaVersion: 999, contract: 'quant-research-summary', projectId: 'sox', status: {}, primaryEntities: [] } });
assert(/expected 1/.test(contractMismatch), 'contract version mismatch is rejected before parsing');

const summaryFixture = {
  schemaVersion: 1,
  contract: 'quant-research-summary',
  projectId: 'sox',
  projectName: 'SOX Fixture',
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
    metrics: { score: 0.8, weight: 0.1, priceMomentum: 0.7, earningsMomentum: 0.9 },
    warnings: ['구성종목 비중 출처 확인 필요'],
  }],
  limitations: ['프록시 비중은 공식 지수 비중과 다를 수 있습니다.'],
  automation: { workflowUrl: 'https://github.com/SonChangGi/sox/actions/workflows/update-sox-data.yml' },
};
assert(api.isResearchSummary(summaryFixture, 'sox'), 'summary fixture satisfies common contract helper');

assert(api.safeAutomationUrl('https://github.com/SonChangGi/sox/actions/workflows/update-sox-data.yml').startsWith('https://github.com/'), 'automation URL allowlist accepts GitHub HTTPS links');
assert(api.safeAutomationUrl('javascript:alert(1)') === '', 'automation URL allowlist rejects javascript scheme');
assert(api.safeAutomationUrl('https://evil.example/actions') === '', 'automation URL allowlist rejects unexpected hosts');
const parsedSummarySox = api.parseSox(summaryFixture);
assert(parsedSummarySox.rows.length === 1 && parsedSummarySox.rows[0].ticker === 'NVDA', 'SOX summary contract parses into panel rows');
const dossierMatches = api.watchlistMatchesForToken([
  { project: { id: 'sox', shortName: 'SOX' }, summary: parsedSummarySox },
], 'AI');
assert(dossierMatches.length === 1 && /비중 출처/.test(dossierMatches[0].limit), 'watchlist dossier uses summary entities and limitation text without duplicate legacy rows');

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
    this.dataset = {};
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
assert(domTargets['#top-nav'].children.length === 8, 'manifest renderer creates eight active project links including Regime');
assert(domTargets['#summary-grid'].children.length === 8, 'manifest renderer creates eight public summary panels');
assert(domTargets['#summary-grid'].children.every((child) => /열기/.test(child.innerHTML)), 'dashboard panel shells preserve project page links');
assert(domTargets['#summary-grid'].children.some((child) => /포트폴리오 데이터/.test(child.innerHTML)), 'Port public summary panel appears in the central grid');
assert(domTargets['#summary-grid'].children.some((child) => /panel-detail/.test(child.innerHTML)), 'ETF panel shell includes detail mount for TOP10 cards');
assert(domTargets['#summary-grid'].children.some((child) => /SOX 구성종목/.test(child.innerHTML)), 'SOX panel shell appears in the central summary grid');
assert(domTargets['#summary-grid'].children.some((child) => /현재 국면 · 다음 주 전망/.test(child.innerHTML)), 'Regime public result panel appears in the central summary grid');
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
assert(
  api.healthTone({ ...staleByDataAsOfRecord, metadataMismatch: true }) === 'warn'
    && api.healthLabel({ ...staleByDataAsOfRecord, metadataMismatch: true }) === '메타데이터 불일치',
  'data health fails closed when database metadata and the rendered summary date disagree',
);
const momentumFreshnessFallbackRecord = {
  project: api.PROJECTS.find((project) => project.id === 'momentum'),
  summary: { dataAsOf: '2000-01-01', meta: {} },
  mode: 'live',
};
assert(api.expectedFreshnessDays(momentumFreshnessFallbackRecord) === 5, 'Momentum receives a project-level freshness expectation when its custom contract omits one');
assert(api.isRecordStale(momentumFreshnessFallbackRecord), 'project-level freshness defaults close the Momentum stale-data blind spot');
const records = [
  { project: api.PROJECTS.find((project) => project.id === 'momentum'), summary: validMomentum, mode: 'live', generatedAt: validMomentum.generatedAt, payloadBytes: 13000, sourceCount: 2 },
  { project: api.PROJECTS.find((project) => project.id === 'sox'), summary: validSox, mode: 'live', generatedAt: validSox.generatedAt, payloadBytes: 6000, sourceCount: 1 },
  { project: api.PROJECTS.find((project) => project.id === 'etf'), summary: validEtf, mode: 'live', generatedAt: validEtf.generatedAt, payloadBytes: 90000, sourceCount: 1 },
];
api.renderResearchBriefing(records);
api.renderDataHealth(records);
assert(/SOX/.test(domTargets['#research-briefing'].innerHTML) && /AAA/.test(domTargets['#research-briefing'].innerHTML), 'research briefing renders SOX central summary item');
assert(/selected_mom/.test(domTargets['#research-briefing'].innerHTML) && /0\.87/.test(domTargets['#research-briefing'].innerHTML), 'research briefing renders the schema v4 selected Momentum factor and composite score');
assert(/합성 데모/.test(domTargets['#research-briefing'].innerHTML) && /briefing-item warning/.test(domTargets['#research-briefing'].innerHTML), 'research briefing labels demo evidence without hiding the Momentum result');
assert(/갱신 지연/.test(domTargets['#data-health'].innerHTML), 'data health renders localized stale state from project-level freshness defaults');
assert(/Momentum<\/strong>\s*<span>갱신 지연<\/span>/.test(domTargets['#data-health'].innerHTML) && /health-item warn/.test(domTargets['#data-health'].innerHTML), 'data health prioritizes stale Momentum data over its demo evidence label');
assert(/전체 기준일/.test(domTargets['#data-health'].innerHTML), 'data health renders localized portfolio freshness snapshot');
const mixedFreshness = api.portfolioFreshnessSummary([
  { project: { shortName: 'A' }, summary: { dataAsOf: '2026-06-22' }, generatedAt: '2026-06-23T00:00:00Z' },
  { project: { shortName: 'B' }, summary: { dataAsOf: '2026-06-23' }, generatedAt: '2026-06-23T00:00:00Z' },
]);
assert(mixedFreshness.mixed && mixedFreshness.label.includes('혼합 기준일'), 'portfolio freshness snapshot flags mixed project dates');
assert(api.watchlistMatchesForToken(records, 'AAA').length >= 2, 'watchlist matcher connects ETF and SOX ticker exposure');
assert(api.parseWatchlistTokens('NVDA, AMD DRAM').join('|') === 'NVDA|AMD|DRAM', 'watchlist token parser handles commas and spaces');

const failed = checks.filter((check) => !check.ok);
for (const check of checks) console.log(`${check.ok ? 'PASS' : 'FAIL'} ${check.label}`);
if (failed.length) {
  console.error(`\n${failed.length} regression check(s) failed.`);
  process.exit(1);
}
console.log(`\n${checks.length} regression checks passed.`);
