(() => {
  'use strict';

  const SAFE_AUTOMATION_HOSTS = new Set(['github.com', 'www.github.com', 'sonchanggi.github.io']);
  const MOMENTUM_RESULT_IDENTITY_VERSION = 'momentum-result-identity-v1';
  const MOMENTUM_CANONICAL_JSON_VERSION = 'rfc8785-jcs-v1';
  const LOWERCASE_SHA256 = /^[0-9a-f]{64}$/;
  const MOMENTUM_FIXED_WEIGHTING_POLICY = 'score_liquidity_rank';
  const MOMENTUM_WEIGHTING_POLICIES = [
    'equal_weight',
    'capped_linear_rank',
    'capped_vol_adjusted_rank',
    'score_liquidity_rank',
  ];
  const MOMENTUM_LIVE_SNAPSHOT_HASH_FIELDS = [
    'comparisonPrices',
    'prices',
    'volumes',
    'dollarVolumes',
    'rawCloses',
    'requestedSymbols',
    'returnedSymbols',
    'universeRecords',
    'priceSources',
    'dataSources',
  ];
  const MOMENTUM_LIVE_SNAPSHOT_HASH_FIELDS_V5 = [
    ...MOMENTUM_LIVE_SNAPSHOT_HASH_FIELDS,
    'marketCaps',
    'marketCapSources',
  ];
  const MOMENTUM_CANONICAL_GRID = {
    factorCount: 64,
    independentFactorCount: 61,
    aliasFactorCount: 3,
    policyCount: 4,
    independentPairCount: 244,
    aliasPairCount: 12,
    totalPairCount: 256,
  };
  const MOMENTUM_V5_GRID = {
    factorCount: 64,
    independentFactorCount: 61,
    aliasFactorCount: 3,
    policyCount: 1,
    independentFactorRunCount: 61,
    aliasFactorRunCount: 3,
    totalFactorRunCount: 64,
  };
  const MOMENTUM_ABSOLUTE_GUARDRAIL_RULES = [
    {
      id: 'minimum_sharpe',
      metric: 'sharpe',
      operator: '>=',
      researchInput: 'selectionMinSharpe',
      config: 'selection_min_sharpe',
      unit: 'ratio',
    },
    {
      id: 'maximum_drawdown_magnitude',
      metric: 'max_drawdown',
      operator: '>=',
      researchInput: 'selectionMaxDrawdown',
      config: 'selection_max_drawdown',
      thresholdMultiplier: -1,
      unit: 'fraction',
    },
    {
      id: 'maximum_annualized_cost_drag',
      metric: 'annualized_cost_drag',
      operator: '<=',
      researchInput: 'selectionMaxAnnualizedCostDrag',
      config: 'selection_max_annualized_cost_drag',
      unit: 'fraction_per_year',
    },
    {
      id: 'minimum_historical_target_effective_names',
      metric: 'min_target_effective_names',
      flag: 'guardrail_historical_effective_names',
      researchInput: 'selectionMinEffectiveNames',
      config: 'selection_min_effective_names',
      operator: '>=',
      unit: 'names',
    },
    {
      id: 'minimum_current_target_effective_names',
      metric: 'current_target_effective_names',
      flag: 'guardrail_current_effective_names',
      researchInput: 'selectionMinEffectiveNames',
      config: 'selection_min_effective_names',
      operator: '>=',
      unit: 'names',
    },
    {
      id: 'maximum_historical_target_hhi',
      metric: 'max_target_hhi',
      flag: 'guardrail_historical_target_hhi',
      researchInput: 'selectionMaxTargetHhi',
      config: 'selection_max_target_hhi',
      operator: '<=',
      unit: 'fraction',
    },
    {
      id: 'maximum_current_target_hhi',
      metric: 'current_target_hhi',
      flag: 'guardrail_current_target_hhi',
      researchInput: 'selectionMaxTargetHhi',
      config: 'selection_max_target_hhi',
      operator: '<=',
      unit: 'fraction',
    },
    {
      id: 'maximum_historical_target_weight',
      metric: 'max_target_weight',
      flag: 'guardrail_historical_target_weight',
      researchInput: 'selectionMaxTargetWeight',
      config: 'selection_max_target_weight',
      operator: '<=',
      unit: 'fraction',
    },
    {
      id: 'maximum_current_target_weight',
      metric: 'current_target_max_weight',
      flag: 'guardrail_current_target_weight',
      researchInput: 'selectionMaxTargetWeight',
      config: 'selection_max_target_weight',
      operator: '<=',
      unit: 'fraction',
    },
    {
      id: 'maximum_security_day_contribution',
      metric: 'max_abs_security_day_contribution',
      operator: '<=',
      researchInput: 'selectionMaxAbsSecurityDayContribution',
      config: 'selection_max_abs_security_day_contribution',
      unit: 'portfolio_return_fraction',
    },
    {
      id: 'maximum_security_absolute_contribution_share',
      metric: 'max_security_absolute_contribution_share',
      operator: '<=',
      researchInput: 'selectionMaxSecurityAbsoluteContributionShare',
      config: 'selection_max_security_absolute_contribution_share',
      unit: 'fraction',
    },
    {
      id: 'maximum_leave_one_security_cagr_delta',
      metric: 'max_abs_leave_one_security_cagr_delta',
      operator: '<=',
      researchInput: 'selectionMaxLeaveOneSecurityCagrDelta',
      config: 'selection_max_leave_one_security_cagr_delta',
      unit: 'cagr_fraction',
    },
  ];
  const MOMENTUM_CONCENTRATION_GUARDRAILS = MOMENTUM_ABSOLUTE_GUARDRAIL_RULES
    .filter((rule) => Boolean(rule.flag));
  const MOMENTUM_REQUIRED_GUARDRAIL_CONTRACTS = {
    completeExecutionCoverage: true,
    completePolicyInputs: true,
    contributionDiagnosticsComplete: true,
    currentTargetAvailable: true,
  };

  const ENTITY_METRIC_RENDERERS = {
    etf: (metrics) => `${metrics.etf || 'ETF'} TOP10 비중 ${formatPercent(metrics.weight)} · 기준일 ${formatMaybeDate(metrics.date)}`,
    best: (metrics) => `팩터 ${metrics.factor || '-'} · 비중 ${formatPercent(metrics.weight)} · 점수 ${formatNumber(metrics.score)}`,
    momentum: (metrics) => `${metrics.dataModeLabel || '연구 데이터'} · 팩터 ${metrics.factor || '-'} · 정책 ${metrics.weightingPolicyId || '-'} · 현금 ${formatPercent(metrics.cashWeight)} · 신호 ${formatNumber(metrics.signal)} · 모델 비중 ${formatPercent(metrics.modelWeight)}`,
    dram: (metrics) => `${metrics.kind || '가격'} · ${formatMaybeDate(metrics.date)} · ${metrics.source || 'source N/A'}`,
    sox: (metrics) => `SOX proxy ${formatPercent(metrics.weight)} · 가격 ${formatNumber(metrics.priceMomentum)} · 실적 ${formatNumber(metrics.earningsMomentum)}`,
    fearngreed: (metrics) => `상태 ${metrics.signalState || '산출 불가'} · 백분위 ${formatNumber(metrics.sentimentPercentile)} · 잔차 z ${formatNumber(metrics.residualZ)} · 포지션 ${formatFearPosition(metrics.position)}`,
    regime: (metrics) => `현재 ${metrics.currentStateLabel || '-'} · ${metrics.currentMeasureLabel || '확률'} ${formatPercent(metrics.currentConfidence)} · ${formatMaybeDate(metrics.nextDate)} 예측 ${metrics.nextStateLabel || '-'} · 확률 ${formatPercent(metrics.nextConfidence)} · 1주 이탈 ${formatPercent(metrics.transitionRisk1w)}`,
  };

  const PROJECTS = [
    {
      id: 'fearngreed',
      shortName: 'Fear & Greed',
      title: 'Fear & Greed Flow Lab',
      description: 'KOSPI 대비 개인 순매수 잔차와 현재 전략 상태를 확인합니다.',
      url: 'https://sonchanggi.github.io/fearNgreed/',
      accent: 'FG',
      panelAdapter: 'fearngreed',
      panel: {
        eyebrow: 'KOSPI Flow Sentiment',
        title: '수익률 × 개인 순매수대금',
        contentType: 'scatter',
        metricLoading: 'Fear & Greed 공개 요약을 불러오는 중...',
      },
    },
    {
      id: 'momentum',
      shortName: 'Momentum',
      title: '모멘텀 팩터 랩',
      description: '선정 모멘텀 팩터와 현재 연구 포트폴리오를 확인합니다.',
      url: 'https://sonchanggi.github.io/momentum-factor-lab/',
      accent: 'MF',
      panelAdapter: 'momentum',
      panel: {
        eyebrow: 'Momentum Factor',
        title: '모멘텀 팩터',
        contentType: 'table',
        metricLoading: '모멘텀 데이터를 불러오는 중...',
        table: {
          caption: '동일 입력 Python 최고 모멘텀 팩터의 모델 포트폴리오 상위 종목',
          columns: ['순위', '종목', '신호', '모델 비중'],
          loadingText: '데이터를 불러오는 중...',
        },
      },
    },
    {
      id: 'dram',
      shortName: 'DRAM',
      title: 'D램(DRAM) 가격 랩',
      description: 'D램 현물가·고정가·주간 현물 프록시를 모니터링합니다.',
      url: 'https://sonchanggi.github.io/dram-price/',
      accent: 'DR',
      panelAdapter: 'dram',
      panel: {
        eyebrow: 'DRAM Price',
        title: 'DRAM 가격 추이',
        contentType: 'chart',
        metricLoading: 'D램 가격 데이터를 불러오는 중...',
        chartLabel: 'TrendForce 일별 저장 D램(DRAM) 가격 추이 그래프',
      },
    },
    {
      id: 'best',
      shortName: 'Best Factor',
      title: 'Best Factor Lab',
      description: '미국 주식 팩터 랭킹과 최신 편입 종목·비중을 확인합니다.',
      url: 'https://sonchanggi.github.io/best-factor/',
      accent: 'BF',
      panelAdapter: 'best',
      panel: {
        eyebrow: 'Best Factor',
        title: '베스트 팩터',
        contentType: 'table',
        metricLoading: '베스트 팩터 데이터를 불러오는 중...',
        table: {
          caption: '베스트 팩터 상위 5개 종목과 모델 비중',
          columns: ['순위', '종목', '점수', '모델 비중', '보유 기준일'],
          loadingText: '데이터를 불러오는 중...',
        },
      },
    },
    {
      id: 'etf',
      shortName: 'ETF',
      title: 'ETF TOP10 Tracking',
      description: '한국 상장 액티브 ETF 3종의 TOP10 비중과 편입·편출 신호를 추적합니다.',
      url: 'https://sonchanggi.github.io/etf-tracking/',
      accent: 'ETF',
      panelAdapter: 'etf',
      panel: {
        eyebrow: 'ETF Tracking',
        title: 'ETF별 TOP10 비중',
        contentType: 'table',
        metricLoading: 'ETF 추적 데이터를 불러오는 중...',
        detailSlot: true,
        table: {
          caption: 'ETF별 TOP10 합계와 특별 신호 요약',
          columns: ['ETF', '기준일', 'TOP10 합계', '신호', '종가 커버리지'],
          loadingText: 'ETF 데이터를 불러오는 중...',
        },
      },
    },
    {
      id: 'sox',
      shortName: 'SOX',
      title: 'SOX 반도체 지수 Cockpit',
      description: 'SOX 구성종목의 프록시 비중과 가격·실적 모멘텀을 비교합니다.',
      url: 'https://sonchanggi.github.io/sox/',
      accent: 'SX',
      panelAdapter: 'sox',
      panel: {
        eyebrow: 'SOX Semiconductor',
        title: 'SOX 구성종목 · 가격 vs 실적',
        contentType: 'table',
        metricLoading: 'SOX 데이터를 불러오는 중...',
        table: {
          caption: 'SOX proxy weight와 가격·실적 모멘텀 상위 종목',
          columns: ['순위', '종목', '종합', 'Proxy Wt', '가격/실적', '상태'],
          loadingText: 'SOX 요약 데이터를 불러오는 중...',
        },
      },
    },
    {
      id: 'regime',
      shortName: 'Regime',
      title: 'US Market Regime Lab',
      description: '미국 증시의 현재 국면과 다음 주 확률을 확인합니다.',
      url: 'https://sonchanggi.github.io/regime/',
      accent: 'RG',
      panelAdapter: 'regime',
      panel: {
        eyebrow: 'US Market Regime',
        title: '국면 추이',
        contentType: 'regime-trend',
        metricLoading: 'Regime 공개 요약을 불러오는 중...',
      },
    },
  ];
  const NAVIGATION_PROJECTS = [
    ...PROJECTS,
    { id: 'news', shortName: 'News', url: 'https://sonchanggi.github.io/news/' },
  ];
  const PLATFORM_PROJECT_IDS = {
    fearngreed: 'fear-greed',
    momentum: 'momentum',
    dram: 'dram',
    best: 'best-factor',
    etf: 'etf',
    sox: 'sox',
    regime: 'regime',
  };
  const PROJECT_EXPECTED_FRESHNESS_DAYS = Object.freeze({
    fearngreed: 5,
    momentum: 5,
    dram: 5,
    best: 5,
    etf: 5,
    sox: 5,
    regime: 10,
  });

  const REGIME_RESULT_VERSIONS = new Set(['weekly-regime-result-v3', 'weekly-regime-result-v4', 'weekly-regime-result-v5']);
  const REGIME_CORE_VERSIONS = new Set(['regime-dashboard-core/1', 'regime-dashboard-core/2']);
  const REGIME_STATES = Object.freeze(['risk_on', 'transition', 'risk_off']);
  const REGIME_LIVE_SOURCE_LICENSES = Object.freeze({
    alpha_vantage: 'private_noncommercial',
    alfred: 'user_confirmed_ml_storage_derived',
  });
  const REGIME_V5_LIVE_SOURCE_LICENSES = Object.freeze({
    ...REGIME_LIVE_SOURCE_LICENSES,
    frb_h10: 'federal_reserve_board_public_domain_citation_requested',
  });
  const REGIME_STATE_LABELS = Object.freeze({
    risk_on: '위험 선호',
    transition: '전환',
    risk_off: '위험 회피',
  });
  const SUMMARY_CONTRACT = { versionField: 'schemaVersion', expectedVersion: 1, requiredKeys: ['contract', 'projectId', 'status', 'primaryEntities'] };
  const MOMENTUM_SUMMARY_CONTRACT = {
    versionField: 'schemaVersion',
    expectedVersion: 5,
    requiredKeys: ['resultIdentity', 'bestFactor', 'weightingPolicy', 'bestFactorReason', 'factorAccounting', 'bestFactorPortfolio', 'allocationMethod', 'compositeScore', 'weights', 'cashWeight', 'maxWeight', 'dataAsOf', 'dataMode', 'sourceLabel', 'evidenceStatus', 'researchOnly', 'notInvestmentRecommendation'],
  };

  const PANEL_ADAPTERS = {
    fearngreed: {
      sourceUrls: {
        summary: 'https://sonchanggi.github.io/fearNgreed/data/summary.json',
        dashboard: 'https://sonchanggi.github.io/fearNgreed/data/dashboard.json',
        history: 'https://sonchanggi.github.io/fearNgreed/data/history.json',
      },
      primarySourceKey: 'summary',
      contracts: { summary: SUMMARY_CONTRACT },
      parse: (sources) => parseFearPanel(sources),
      hasUsableData: (summary) => Boolean(summary && summary.unavailable !== true && summary.entityPresent && summary.dataAsOf),
      fallback: normalizeFearAndGreedUnavailable,
      render: renderFearAndGreed,
      emptyReason: 'Fear & Greed summary did not contain a usable KOSPI entity.',
    },
    momentum: {
      sourceUrls: {
        summary: 'https://sonchanggi.github.io/momentum-factor-lab/data/summary.json',
        momentumDashboard: 'https://sonchanggi.github.io/momentum-factor-lab/data/dashboard.json',
      },
      primarySourceKey: 'summary',
      contracts: { summary: MOMENTUM_SUMMARY_CONTRACT },
      parse: (sources) => parseMomentum(sources.summary, sources.momentumDashboard),
      hasUsableData: (summary) => Boolean(
        summary
          && summary.unavailable !== true
          && Array.isArray(summary.rows)
          && finiteOrNull(summary.cashWeight) !== null,
      ),
      fallback: normalizeMomentumFallback,
      render: renderMomentum,
      emptyReason: 'Momentum summary did not contain usable top rows.',
    },
    dram: {
      sourceUrls: {
        summary: 'https://sonchanggi.github.io/dram-price/data/summary.json',
        dramPrices: 'https://sonchanggi.github.io/dram-price/data/prices.json',
        dramSeries: 'https://sonchanggi.github.io/dram-price/data/series.json',
        dramStatus: 'https://sonchanggi.github.io/dram-price/data/status.json',
      },
      primarySourceKey: 'summary',
      contracts: { summary: SUMMARY_CONTRACT },
      parse: (sources) => parseDram(sources.dramPrices, sources.dramSeries, sources.dramStatus, sources.summary),
      hasUsableData: (summary) => Boolean(summary?.series?.length || summary?.entities?.length),
      fallback: normalizeDramFallback,
      render: renderDram,
      emptyReason: 'DRAM summary/details did not contain usable price points.',
    },
    best: {
      sourceUrls: {
        summary: 'https://sonchanggi.github.io/best-factor/data/summary.json',
      },
      primarySourceKey: 'summary',
      contracts: { summary: SUMMARY_CONTRACT },
      parse: (sources) => parseBestFactor(sources.summary),
      hasUsableData: (summary) => Boolean(summary?.rows?.length),
      fallback: normalizeBestFallback,
      render: renderBestFactor,
      emptyReason: 'Best Factor summary did not contain usable holdings.',
    },
    etf: {
      sourceUrls: {
        summary: 'https://sonchanggi.github.io/etf-tracking/data/summary.json',
        etf: 'https://sonchanggi.github.io/etf-tracking/data/dashboard.json',
        etfHistoryManifest: 'https://sonchanggi.github.io/etf-tracking/data/history.json',
      },
      primarySourceKey: 'summary',
      contracts: { summary: SUMMARY_CONTRACT },
      enrichSources: enrichEtfTrackingSources,
      enrichmentFailure: etfHistoryEnrichmentFailure,
      parse: (sources) => parseEtfTracking(sources.etf, sources.summary, sources.etfHistories, sources.etfHistoryStatus),
      hasUsableData: (summary) => Boolean(summary?.rows?.length || summary?.entities?.length),
      fallback: normalizeEtfFallback,
      render: renderEtfTracking,
      emptyReason: 'ETF Tracking summary/details did not contain usable ETF rows.',
    },
    sox: {
      sourceUrls: {
        summary: 'https://sonchanggi.github.io/sox/data/summary.json',
        soxAnalysis: 'https://sonchanggi.github.io/sox/data/sox-analysis.json',
      },
      primarySourceKey: 'summary',
      contracts: { summary: SUMMARY_CONTRACT },
      parse: parseSoxPanel,
      hasUsableData: (summary) => Boolean(summary?.rows?.length),
      fallback: normalizeSoxFallback,
      render: renderSox,
      emptyReason: 'SOX summary did not contain usable constituents.',
    },
    regime: {
      sourceUrls: {
        summary: 'https://sonchanggi.github.io/regime/data/regime-core.json',
      },
      primarySourceKey: 'summary',
      parse: (sources) => parseRegimePanel(sources),
      enrichSources: enrichRegimeSources,
      enrichmentFailure: (sources, message) => ({ dataSources: { ...sources, regimeHistoryError: message }, fetchResults: { regimeHistory: { ok: false, error: message } } }),
      hasUsableData: (summary) => Boolean(summary?.publicPayloadValid && summary.unavailable !== true),
      fallback: normalizeRegimeUnavailable,
      render: renderRegime,
      emptyReason: 'Regime public payload did not satisfy the demo or live-derived contract.',
    },
  };

  const FALLBACK_SNAPSHOT = {
    dram: {
      generatedAt: '2026-06-10T14:09:17Z',
      status: '마지막 확인 스냅샷 표시 중',
      series: [
        {
          name: 'DDR4 16Gb 3200',
          points: [
            ['2025-12-09', 30.0], ['2026-01-06', 31.0], ['2026-02-03', 33.5],
            ['2026-03-03', 37.0], ['2026-04-07', 43.0], ['2026-05-05', 48.0], ['2026-06-02', 53.0],
          ],
        },
        {
          name: 'DDR5 16Gb Major',
          points: [
            ['2025-12-09', 39.0], ['2026-01-06', 41.0], ['2026-02-03', 43.0],
            ['2026-03-03', 47.0], ['2026-04-07', 50.0], ['2026-05-05', 54.0], ['2026-06-02', 58.0],
          ],
        },
      ],
    },
    best: {
      generatedAt: '2026-06-10T14:10:53Z',
      dataEndDate: '2026-06-10',
      factor: 'momentum_12_1',
      compositeScore: 0.9497823609,
      status: '마지막 확인 스냅샷 표시 중',
      rows: [
        { rank: 1, ticker: 'AMD', score: 1.986974867, weight: 0.3207175943, date: '2026-05-29' },
        { rank: 2, ticker: 'AMAT', score: 1.382066239, weight: 0.1907071998, date: '2026-05-29' },
        { rank: 3, ticker: 'CAT', score: 1.342891001, weight: 0.1822874356, date: '2026-05-29' },
        { rank: 4, ticker: 'GOOGL', score: 1.037325583, weight: 0.1166135822, date: '2026-05-29' },
        { rank: 5, ticker: 'GOOG', score: 1.010097312, weight: 0.1107615278, date: '2026-05-29' },
      ],
    },
    etf: {
      generatedAt: '2026-06-17T07:04:33Z',
      status: '마지막 확인 스냅샷 표시 중',
      rows: [{"name":"TIME 나스닥100","fullName":"TIME 미국나스닥100액티브","code":"426030","date":"2026-06-17","topName":"Micron Technology Inc","topTicker":"MU","topWeight":0.0673,"signalCount":2,"entryExitCount":2,"sourceStatus":"live","returnCoverage":0.9762047590481904,"top10":[{"rank":1,"ticker":"MU","codeRaw":"MU US EQUITY","name":"Micron Technology Inc","weight":0.0673},{"rank":2,"ticker":"SNDK","codeRaw":"SNDK US EQUITY","name":"Sandisk Corp","weight":0.0666},{"rank":3,"ticker":"INTC","codeRaw":"INTC US EQUITY","name":"Intel Corp","weight":0.0554},{"rank":4,"ticker":"ARM","codeRaw":"ARM US EQUITY","name":"ARM Holdings PLC","weight":0.053200000000000004},{"rank":5,"ticker":"NVDA","codeRaw":"NVDA US EQUITY","name":"NVIDIA Corp","weight":0.0467},{"rank":6,"ticker":"MRVL","codeRaw":"MRVL US EQUITY","name":"Marvell Technology Inc","weight":0.04019999999999999},{"rank":7,"ticker":"AMD","codeRaw":"AMD US EQUITY","name":"Advanced Micro Devices Inc","weight":0.0346},{"rank":8,"ticker":"DELL","codeRaw":"DELL US EQUITY","name":"Dell Technologies Inc","weight":0.0315},{"rank":9,"ticker":"CRDO","codeRaw":"CRDO US EQUITY","name":"Credo Technology Group Holding Ltd","weight":0.0302},{"rank":10,"ticker":"","codeRaw":"SPCX US EQUITY","name":"Space Exploration Technologies Corp","weight":0.0302}],"top10Weight":0.45589999999999997,"chartSeries":[{"rank":1,"label":"MU","points":[{"date":"2026-04-01","value":0.026600000000000002},{"date":"2026-04-14","value":0.0276},{"date":"2026-04-27","value":0.026099999999999998},{"date":"2026-05-12","value":0.0507},{"date":"2026-05-26","value":0.0475},{"date":"2026-06-09","value":0.0501},{"date":"2026-06-17","value":0.0673}]},{"rank":2,"label":"SNDK","points":[{"date":"2026-04-01","value":0.06860000000000001},{"date":"2026-04-14","value":0.0816},{"date":"2026-04-27","value":0.0567},{"date":"2026-05-12","value":0.0862},{"date":"2026-05-26","value":0.0512},{"date":"2026-06-09","value":0.0375},{"date":"2026-06-17","value":0.0666}]},{"rank":3,"label":"INTC","points":[{"date":"2026-04-01","value":0.020099999999999996},{"date":"2026-04-14","value":0.028300000000000002},{"date":"2026-04-27","value":0.044199999999999996},{"date":"2026-05-12","value":0.07400000000000001},{"date":"2026-05-26","value":0.0594},{"date":"2026-06-09","value":0.0416},{"date":"2026-06-17","value":0.0554}]},{"rank":4,"label":"ARM","points":[{"date":"2026-04-01","value":0.0385},{"date":"2026-04-14","value":0.0333},{"date":"2026-04-27","value":0.050499999999999996},{"date":"2026-05-12","value":0.0437},{"date":"2026-05-26","value":0.044199999999999996},{"date":"2026-06-09","value":0.0528},{"date":"2026-06-17","value":0.053200000000000004}]},{"rank":5,"label":"NVDA","points":[{"date":"2026-04-01","value":0.051100000000000007},{"date":"2026-04-14","value":0.04650000000000001},{"date":"2026-04-27","value":0.0676},{"date":"2026-05-12","value":0.0554},{"date":"2026-05-26","value":0.0851},{"date":"2026-06-09","value":0.0742},{"date":"2026-06-17","value":0.0467}]}]},{"name":"TIME 글로벌AI","fullName":"TIME 글로벌AI인공지능액티브","code":"456600","date":"2026-06-17","topName":"Kioxia Holdings Corp","topTicker":"285A.T","topWeight":0.0852,"signalCount":2,"entryExitCount":2,"sourceStatus":"live","returnCoverage":0.9604039596040396,"top10":[{"rank":1,"ticker":"285A.T","codeRaw":"285A JP EQUITY","name":"Kioxia Holdings Corp","weight":0.0852},{"rank":2,"ticker":"INTC","codeRaw":"INTC US EQUITY","name":"Intel Corp","weight":0.0722},{"rank":3,"ticker":"AMD","codeRaw":"AMD US EQUITY","name":"Advanced Micro Devices Inc","weight":0.0678},{"rank":4,"ticker":"STX","codeRaw":"STX US EQUITY","name":"Seagate Technology Holdings PLC","weight":0.0621},{"rank":5,"ticker":"WDC","codeRaw":"WDC US EQUITY","name":"Western Digital Corp","weight":0.052199999999999996},{"rank":6,"ticker":"ARM","codeRaw":"ARM US EQUITY","name":"ARM Holdings PLC","weight":0.0412},{"rank":7,"ticker":"","codeRaw":"NQU6 INDEX","name":"NASDAQ 100 E-MINI INDEX SEPT 2026","weight":0.038900000000000004},{"rank":8,"ticker":"SNDK","codeRaw":"SNDK US EQUITY","name":"Sandisk Corp","weight":0.037599999999999995},{"rank":9,"ticker":"SNOW","codeRaw":"SNOW US EQUITY","name":"Snowflake Inc","weight":0.037200000000000004},{"rank":10,"ticker":"NVDA","codeRaw":"NVDA US EQUITY","name":"NVIDIA Corp","weight":0.0332}],"top10Weight":0.5276,"chartSeries":[{"rank":1,"label":"285A.T","points":[{"date":"2026-05-15","value":0.0197},{"date":"2026-05-21","value":0.0209},{"date":"2026-05-28","value":0.0621},{"date":"2026-06-04","value":0.06559999999999999},{"date":"2026-06-10","value":0.07339999999999999},{"date":"2026-06-16","value":0.0806},{"date":"2026-06-17","value":0.0852}]},{"rank":2,"label":"INTC","points":[{"date":"2026-04-01","value":0.024},{"date":"2026-04-14","value":0.0526},{"date":"2026-04-27","value":0.0555},{"date":"2026-05-12","value":0.07980000000000001},{"date":"2026-05-26","value":0.0796},{"date":"2026-06-09","value":0.0621},{"date":"2026-06-17","value":0.0722}]},{"rank":3,"label":"AMD","points":[{"date":"2026-04-01","value":0.0199},{"date":"2026-04-14","value":0.018799999999999997},{"date":"2026-04-27","value":0.018600000000000002},{"date":"2026-05-12","value":0.0375},{"date":"2026-05-26","value":0.0463},{"date":"2026-06-09","value":0.0644},{"date":"2026-06-17","value":0.0678}]},{"rank":4,"label":"STX","points":[{"date":"2026-04-01","value":0.0412},{"date":"2026-04-14","value":0.0434},{"date":"2026-04-27","value":0.0358},{"date":"2026-05-12","value":0.057},{"date":"2026-05-26","value":0.058600000000000006},{"date":"2026-06-09","value":0.056600000000000004},{"date":"2026-06-17","value":0.0621}]},{"rank":5,"label":"WDC","points":[{"date":"2026-04-01","value":0.0461},{"date":"2026-04-14","value":0.04769999999999999},{"date":"2026-04-27","value":0.0452},{"date":"2026-05-12","value":0.045899999999999996},{"date":"2026-05-26","value":0.0461},{"date":"2026-06-09","value":0.0454},{"date":"2026-06-17","value":0.052199999999999996}]}]},{"name":"KoAct 나스닥성장","fullName":"KoAct 미국나스닥성장기업액티브","code":"2ETFQ1","date":"2026-06-17","topName":"Space Exploration Technologies Corp","topTicker":"SPCX US Equity","topWeight":0.09630000000000001,"signalCount":0,"entryExitCount":0,"sourceStatus":"live","returnCoverage":1.0,"top10":[{"rank":1,"ticker":"","codeRaw":"SPCX US Equity","name":"Space Exploration Technologies Corp","weight":0.09630000000000001},{"rank":2,"ticker":"AMD","codeRaw":"AMD US Equity","name":"ADVANCED MICRO DEVICES","weight":0.0745},{"rank":3,"ticker":"ARM","codeRaw":"ARM US Equity","name":"ARM Holdings PLC","weight":0.07339999999999999},{"rank":4,"ticker":"SNDK","codeRaw":"SNDK US Equity","name":"Sandisk Corp/DE","weight":0.0594},{"rank":5,"ticker":"INTC","codeRaw":"INTC US Equity","name":"INTEL Corp","weight":0.0557},{"rank":6,"ticker":"NVDA","codeRaw":"NVDA US Equity","name":"NVIDIA Corp","weight":0.049100000000000005},{"rank":7,"ticker":"GOOGL","codeRaw":"GOOGL US Equity","name":"ALPHABET INC-CL A","weight":0.047},{"rank":8,"ticker":"BE","codeRaw":"BE US Equity","name":"BLOOM ENERGY CORPORATION","weight":0.042},{"rank":9,"ticker":"MU","codeRaw":"MU US Equity","name":"MICRON TECH","weight":0.0405},{"rank":10,"ticker":"AMZN","codeRaw":"AMZN US Equity","name":"Amazon.com Inc","weight":0.0371}],"top10Weight":0.575,"chartSeries":[{"rank":1,"label":"SPCX US Equity","points":[{"date":"2026-06-16","value":0.0858},{"date":"2026-06-17","value":0.09630000000000001}]},{"rank":2,"label":"AMD","points":[{"date":"2026-06-08","value":0.0711},{"date":"2026-06-10","value":0.0757},{"date":"2026-06-12","value":0.0781},{"date":"2026-06-16","value":0.0742},{"date":"2026-06-17","value":0.0745}]},{"rank":3,"label":"ARM","points":[{"date":"2026-06-08","value":0.0698},{"date":"2026-06-10","value":0.0699},{"date":"2026-06-12","value":0.0694},{"date":"2026-06-16","value":0.0722},{"date":"2026-06-17","value":0.07339999999999999}]},{"rank":4,"label":"SNDK","points":[{"date":"2026-06-08","value":0.0637},{"date":"2026-06-10","value":0.0501},{"date":"2026-06-12","value":0.056100000000000004},{"date":"2026-06-16","value":0.059500000000000004},{"date":"2026-06-17","value":0.0594}]},{"rank":5,"label":"INTC","points":[{"date":"2026-06-08","value":0.0537},{"date":"2026-06-10","value":0.0545},{"date":"2026-06-12","value":0.0591},{"date":"2026-06-16","value":0.0579},{"date":"2026-06-17","value":0.0557}]}]}],
    },
    sox: {
      generatedAt: '2026-06-29T01:02:43Z',
      dataAsOf: '2026-06-26',
      status: '마지막 SOX 공개 summary 스냅샷 표시 중',
      rows: [
        { rank: 1, ticker: 'MU', name: 'Micron Technology', score: 0.9848, weight: 0.0858, priceMomentum: 0.9766, earningsMomentum: 0.9948, status: '가격·실적 동반 강세' },
        { rank: 2, ticker: 'ALAB', name: 'Astera Labs', score: 0.8286, weight: 0.0045, priceMomentum: 0.8717, earningsMomentum: 0.7759, status: '가격·실적 동반 강세' },
        { rank: 3, ticker: 'TER', name: 'Teradyne', score: 0.7722, weight: 0.0046, priceMomentum: 0.7255, earningsMomentum: 0.8293, status: '가격·실적 동반 강세' },
        { rank: 4, ticker: 'AMD', name: 'Advanced Micro Devices', score: 0.7447, weight: 0.0570, priceMomentum: 0.8207, earningsMomentum: 0.6517, status: '중립/혼재' },
        { rank: 5, ticker: 'CRDO', name: 'Credo Technology', score: 0.7339, weight: 0.0030, priceMomentum: 0.5910, earningsMomentum: 0.9086, status: '중립/혼재' },
      ],
      entities: [],
      meta: {
        statusState: 'fallback',
        statusLabel: 'SOX fallback snapshot',
        cadence: 'manual',
        expectedFreshnessDays: 14,
        limitations: ['SOX 공식 무료 비중이 없을 때는 시가총액 정규화 proxy weight를 사용합니다.'],
      },
    },
  };

  const COLORS = ['#7dd3fc', '#86efac', '#fb7185', '#fbbf24', '#c4b5fd', '#67e8f9'];
  const DRAM_DASHES = ['', '9 5', '3 4', '12 4 3 4', '2 5', '7 3 2 3'];
  const PANEL_RECORDS = new Map();
  const NEWS_ARCHIVE_URL = 'https://sonchanggi.github.io/news/archive.json';
  let newsState = { state: 'loading' };
  const ETF_HISTORY_WINDOW_DAYS = 31;
  const ETF_HISTORY_TAIL_BYTES = 2_400_000;
  let watchlistBound = false;
  const $ = (selector) => document.querySelector(selector);

  if (typeof document !== 'undefined') {
    document.addEventListener('DOMContentLoaded', () => {
      renderProjectNavigation();
      renderDashboardPanels();
      renderHubStatus([], getPanelProjects().length);
      loadDashboardPanels();
      loadNewsSummary();
    });
  }

  function renderProjectNavigation() {
    const topNav = $('#top-nav');

    if (topNav) {
      topNav.replaceChildren(...NAVIGATION_PROJECTS.map((project) => createProjectLink(project, project.shortName)));
    }
  }

  function createProjectLink(project, label) {
    const link = document.createElement('a');
    link.className = 'quant-shared-nav__link';
    link.href = project.url;
    link.textContent = label;
    link.setAttribute('data-project-id', project.id);
    return link;
  }

  function renderDashboardPanels() {
    const summaryGrid = $('#summary-grid');
    if (!summaryGrid) return;
    // Display groups only: the source registry, loaders and result identities stay unchanged.
    const groups = [
      { id: 'market', title: '시장 상태', label: '심리와 국면', projects: ['fearngreed', 'regime'] },
      { id: 'factors', title: '팩터 전략', label: '연구 결과와 모델 포트폴리오', projects: ['momentum', 'best'] },
      { id: 'semiconductors', title: '반도체', label: '메모리 가격과 SOX 구성종목', projects: ['dram', 'sox'] },
      { id: 'holdings', title: 'ETF 보유종목', label: 'TOP10 비중과 변화', projects: ['etf'] },
    ];
    const panels = groups.flatMap((group) => {
      const heading = document.createElement('div');
      heading.className = 'summary-group-heading';
      heading.id = group.id;
      heading.innerHTML = `<h3>${escapeHtml(group.title)}</h3>`;
      return [heading, ...group.projects.map((id) => {
        const project = PROJECTS.find((candidate) => candidate.id === id);
        return project.panelAdapter && project.panel && PANEL_ADAPTERS[project.panelAdapter]
          ? createPanelShell(project) : createLinkPanelShell(project);
      })];
    });
    summaryGrid.replaceChildren(...panels);
  }

  function parseNewsArchive(archive) {
    if (!isRecord(archive) || archive.schema_version !== 1 || archive.visibility !== 'public'
        || archive.base_path !== '/news/' || !Array.isArray(archive.entries)) throw new Error('News archive contract mismatch.');
    if (!archive.entries.length && !archive.latest_date) return null;
    const date = archive.latest_date;
    if (typeof date !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(date)
        || !Number.isFinite(Date.parse(date)) || new Date(date).toISOString().slice(0, 10) !== date) throw new Error('News publication date is invalid.');
    const matches = archive.entries.filter((entry) => entry?.date === date);
    if (matches.length !== 1) throw new Error('News latest publication is missing or duplicated.');
    const entry = matches[0];
    const report = new URL(entry.report_url, NEWS_ARCHIVE_URL);
    if (report.origin !== 'https://sonchanggi.github.io' || report.pathname !== `/news/daily/${date}/index.html`
        || report.username || report.password || report.search || report.hash
        || !LOWERCASE_SHA256.test(entry.sha256?.json || '')
        || typeof entry.generated_at !== 'string' || !Number.isFinite(Date.parse(entry.generated_at))
        || typeof entry.cutoff !== 'string' || !Number.isFinite(Date.parse(entry.cutoff))
        || typeof entry.mode !== 'string' || !entry.mode || typeof entry.status !== 'string' || !entry.status
        || !Number.isInteger(entry.issue_count) || entry.issue_count < 0) throw new Error('News publication identity is invalid.');
    return { ...entry, reportUrl: report.href, jsonUrl: new URL('briefing.json', report).href };
  }

  function parseNewsBriefing(entry, payload) {
    if (!isRecord(payload) || String(payload.schema_version) !== '1' || payload.publication?.visibility !== 'public'
        || payload.synthetic !== false || payload.report_date !== entry.date
        || payload.generated_at !== entry.generated_at || payload.cutoff !== entry.cutoff
        || payload.mode !== entry.mode || payload.status !== entry.status
        || !Array.isArray(payload.issues) || payload.issues.length !== entry.issue_count
        || !Array.isArray(payload.highlights)) throw new Error('News briefing does not match the publication.');
    if (payload.issues.some((issue) => !isRecord(issue) || typeof issue.title !== 'string' || !issue.title.trim()
        || !/^issue-[a-f0-9]{16}$/.test(issue.anchor || '') || !Array.isArray(issue.summary)
        || issue.summary.some((line) => typeof line !== 'string'))) throw new Error('News issue schema is invalid.');
    const anchors = new Set(payload.issues.map((issue) => issue.anchor));
    if (anchors.size !== payload.issues.length || payload.highlights.some((title) => typeof title !== 'string')) throw new Error('News issue identity is invalid.');
    // The publication owns selection and order. Do not re-rank headlines in the Hub.
    const selected = payload.highlights.length
      ? payload.highlights.map((title) => payload.issues.find((issue) => issue.title === title))
      : payload.issues;
    if (selected.some((issue) => !issue)) throw new Error('News highlight has no matching issue.');
    return {
      ...entry,
      headlines: selected.slice(0, 4).map((issue) => ({
        title: issue.title,
        summary: issue.evidence_expired ? '' : (issue.summary.find((line) => line.trim()) || ''),
        url: `${entry.reportUrl}#${issue.anchor}`,
      })),
      notes: [payload.notice, ...asArray(payload.coverage?.missing_sources).map((source) => `누락 출처: ${source}`)].filter(Boolean),
    };
  }

  async function loadNewsSummary(fetchJson = getJsonBestEffort) {
    newsState = { state: 'loading' };
    renderNewsSummary();
    try {
      const archive = await fetchJson(NEWS_ARCHIVE_URL);
      if (!archive.ok) throw new Error(archive.error || 'News archive unavailable.');
      const entry = parseNewsArchive(archive.data);
      if (!entry) newsState = { state: 'empty' };
      else {
        const briefing = await fetchJson(entry.jsonUrl, 8500, entry.sha256.json);
        if (!briefing.ok) throw new Error(briefing.error || 'News briefing unavailable.');
        newsState = { state: 'ready', summary: parseNewsBriefing(entry, briefing.data) };
      }
    } catch (error) {
      newsState = { state: 'error', error: error instanceof Error ? error.message : String(error) };
    }
    renderNewsSummary();
    return newsState;
  }

  function renderNewsSummary() {
    const target = $('#news-summary');
    const status = $('#news-status');
    const link = $('#news-report-link');
    const health = $('#news-health');
    if (!target || !status) return;
    const summary = newsState.summary;
    status.classList.toggle('warning', newsState.state === 'error');
    if (link) link.href = summary?.reportUrl || 'https://sonchanggi.github.io/news/';
    if (!summary) {
      const message = { loading: '발행 정보 확인 중', empty: '발행된 브리핑 없음', error: 'News 요약을 불러오지 못했습니다' }[newsState.state];
      status.textContent = message;
      target.innerHTML = newsState.state === 'loading' ? '<div class="skeleton-line">주요 뉴스를 불러오는 중...</div>' : '';
      if (health) health.innerHTML = `<article class="health-item ${newsState.state === 'error' ? 'warn' : ''}"><div><strong>News</strong><span>${escapeHtml(message)}</span></div>${newsState.error ? `<p>${escapeHtml(newsState.error)}</p>` : ''}<div class="source-links"><a href="${NEWS_ARCHIVE_URL}">발행 목록 JSON</a></div></article>`;
      return;
    }
    status.textContent = `발행일 ${summary.date} · ${summary.issue_count}개 이슈`;
    target.innerHTML = summary.headlines.length ? `<ol class="news-headlines">${summary.headlines.map((issue) => `<li><a href="${escapeAttribute(issue.url)}">${escapeHtml(issue.title)} <span aria-hidden="true">↗</span></a>${issue.summary ? `<p>${escapeHtml(issue.summary)}</p>` : ''}</li>`).join('')}</ol>` : '<p class="muted">선정된 이슈 없음</p>';
    if (health) health.innerHTML = `<article class="health-item ${summary.status === 'partial' ? 'warn' : 'ok'}"><div><strong>News</strong><span>${escapeHtml(summary.date)} · ${summary.issue_count}개 이슈</span></div><p>자료 마감 ${escapeHtml(formatFreshness(summary.cutoff))} · 생성 ${escapeHtml(formatFreshness(summary.generated_at))}</p><div class="source-links"><a href="${NEWS_ARCHIVE_URL}">발행 목록 JSON</a><a href="${escapeAttribute(summary.jsonUrl)}">브리핑 JSON</a></div></article>`;
  }

  function createPanelShell(project) {
    const panel = project.panel || {};
    const article = document.createElement('article');
    const contentType = panel.contentType || 'table';
    article.className = `panel panel-wide panel--${contentType} panel--${project.id}`;
    article.id = panelDomId(project, 'panel');
    article.dataset.projectId = project.id;
    article.setAttribute('aria-labelledby', panelDomId(project, 'title'));

    const content = contentType === 'regime-trend'
      ? `<div class="regime-trend-mount" id="${escapeAttribute(panelDomId(project, 'chart'))}"><div class="skeleton-line">국면 추이를 불러오는 중...</div></div>`
      : contentType === 'scatter'
      ? `<div class="fear-scatter-mount" id="${escapeAttribute(panelDomId(project, 'chart'))}"><div class="skeleton-line">차트를 불러오는 중...</div></div>`
      : contentType === 'chart'
      ? chartPanelMarkup(project)
      : contentType === 'metrics'
        ? metricsPanelMarkup(project)
        : tablePanelMarkup(project);
    if (contentType === 'metrics') article.className += ' metrics-only-panel';
    article.innerHTML = `
      <div class="panel-header">
        <div>
          <p class="eyebrow">${escapeHtml(panel.eyebrow || project.shortName)}</p>
          <h4 id="${escapeAttribute(panelDomId(project, 'title'))}">${escapeHtml(panel.title || project.title)}</h4>
        </div>
        <a class="panel-link" href="${escapeAttribute(project.url)}">${escapeHtml(project.shortName)} 열기</a>
      </div>
      <p class="status-line" id="${escapeAttribute(panelDomId(project, 'status'))}">업데이트 확인 중</p>
      ${content}
    `;
    return article;
  }

  function createLinkPanelShell(project) {
    const article = document.createElement('article');
    article.className = `panel panel-wide panel--link panel--${project.id}`;
    article.id = panelDomId(project, 'panel');
    article.dataset.projectId = project.id;
    article.setAttribute('aria-labelledby', panelDomId(project, 'title'));
    article.innerHTML = `
      <div class="project-link-card">
        <div class="project-link-identity">
          <span class="project-monogram" aria-hidden="true">${escapeHtml(project.accent)}</span>
          <div>
            <p class="eyebrow">${escapeHtml(project.shortName)}</p>
            <h3 id="${escapeAttribute(panelDomId(project, 'title'))}">${escapeHtml(project.title)}</h3>
          </div>
        </div>
        <p>${escapeHtml(project.description)}</p>
        <a class="panel-link" href="${escapeAttribute(project.url)}">${escapeHtml(project.shortName)} 열기</a>
      </div>
    `;
    return article;
  }

  function metricsPanelMarkup(project) {
    const panel = project.panel || {};
    return `
      <div class="metric-row" id="${escapeAttribute(panelDomId(project, 'metrics'))}" aria-live="polite">
        <div class="skeleton-line">${escapeHtml(panel.metricLoading || '데이터를 불러오는 중...')}</div>
      </div>
    `;
  }

  function tablePanelMarkup(project) {
    const panel = project.panel || {};
    const table = panel.table || { columns: [], caption: '', loadingText: '데이터를 불러오는 중...' };
    const columns = table.columns.map((label) => `<th scope="col">${escapeHtml(label)}</th>`).join('');
    const colspan = Math.max(table.columns.length, 1);
    if (['momentum', 'best'].includes(project.id)) return `
      <div class="factor-overview" id="${escapeAttribute(panelDomId(project, 'metrics'))}" aria-live="polite"><div class="skeleton-line">${escapeHtml(panel.metricLoading)}</div></div>
      <details class="factor-details">
        <summary>팩터 · 데이터 상세</summary>
        <dl class="factor-source-meta" id="${escapeAttribute(panelDomId(project, 'factor-meta'))}"></dl>
        <div class="table-wrap"><table><caption>${escapeHtml(table.caption)}</caption><thead><tr>${columns}</tr></thead><tbody id="${escapeAttribute(panelDomId(project, 'rows'))}"><tr><td colspan="${colspan}">${escapeHtml(table.loadingText)}</td></tr></tbody></table></div>
      </details>`;
    if (['sox', 'etf'].includes(project.id)) return `
      <div class="market-summary" id="${escapeAttribute(panelDomId(project, 'metrics'))}" aria-live="polite"><div class="skeleton-line">${escapeHtml(panel.metricLoading)}</div></div>
      <div class="panel-detail market-visual" id="${escapeAttribute(panelDomId(project, 'details'))}"></div>
      <details class="market-details"><summary>${project.id === 'sox' ? '종목별 점수 · 비중 상세' : 'ETF별 신호 · 데이터 상세'}</summary>
        <div class="table-wrap"><table><caption>${escapeHtml(table.caption)}</caption><thead><tr>${columns}</tr></thead><tbody id="${escapeAttribute(panelDomId(project, 'rows'))}"><tr><td colspan="${colspan}">${escapeHtml(table.loadingText)}</td></tr></tbody></table></div>
      </details>`;
    return `
      <div class="metric-row" id="${escapeAttribute(panelDomId(project, 'metrics'))}" aria-live="polite">
        <div class="skeleton-line">${escapeHtml(panel.metricLoading || '데이터를 불러오는 중...')}</div>
      </div>
      <div class="table-wrap">
        <table>
          <caption>${escapeHtml(table.caption || `${project.title} 요약`)}</caption>
          <thead><tr>${columns}</tr></thead>
          <tbody id="${escapeAttribute(panelDomId(project, 'rows'))}">
            <tr><td colspan="${colspan}">${escapeHtml(table.loadingText || '데이터를 불러오는 중...')}</td></tr>
          </tbody>
        </table>
      </div>
      ${panel.detailSlot ? `<div class="panel-detail" id="${escapeAttribute(panelDomId(project, 'details'))}"></div>` : ''}
    `;
  }

  function chartPanelMarkup(project) {
    const panel = project.panel || {};
    return `
      <div class="chart-toolbar" id="${escapeAttribute(panelDomId(project, 'metrics'))}" aria-live="polite">
        <span class="skeleton-line">${escapeHtml(panel.metricLoading || '차트 데이터를 불러오는 중...')}</span>
      </div>
      <div class="chart-card" id="${escapeAttribute(panelDomId(project, 'chart'))}" role="group" aria-label="${escapeAttribute(panel.chartLabel || `${project.title} 차트`)}"></div>
    `;
  }

  function getPanelProjects() {
    return PROJECTS.filter((project) => project.panelAdapter && project.panel && PANEL_ADAPTERS[project.panelAdapter]);
  }

  function panelDomId(project, slot) {
    return `${project.id}-${slot}`;
  }

  function panelSelector(project, slot) {
    return `#${panelDomId(project, slot)}`;
  }

  function projectById(id) {
    return PROJECTS.find((project) => project.id === id || project.panelAdapter === id) || null;
  }

  async function loadMomentumPanel() {
    return loadProjectPanel('momentum');
  }

  async function loadDramPanel() {
    return loadProjectPanel('dram');
  }

  async function loadBestPanel() {
    return loadProjectPanel('best');
  }

  async function loadEtfPanel() {
    return loadProjectPanel('etf');
  }

  async function loadDashboardPanels() {
    const projects = getPanelProjects();
    PANEL_RECORDS.clear();
    await Promise.all(projects.map(async (project) => {
      const record = await loadProjectPanel(project);
      if (!record) return;
      PANEL_RECORDS.set(record.project.id, record);
      const availableRecords = projects.map((item) => PANEL_RECORDS.get(item.id)).filter(Boolean);
      renderDataHealth(availableRecords);
      renderHubStatus(availableRecords, projects.length);
    }));
    const records = projects.map((project) => PANEL_RECORDS.get(project.id)).filter(Boolean);
    renderHubStatus(records, projects.length);
    return records;
  }

  async function loadProjectPanel(projectOrId) {
    const project = typeof projectOrId === 'string' ? projectById(projectOrId) : projectOrId;
    const adapter = project ? PANEL_ADAPTERS[project.panelAdapter] : null;
    if (!project || !adapter) return;

    const [publishedMetadata, entries] = await Promise.all([
      getPublishedSnapshotMetadata(PLATFORM_PROJECT_IDS[project.id] || project.id),
      Promise.all(Object.entries(adapter.sourceUrls).map(async ([sourceKey, url]) => [sourceKey, await getJsonBestEffort(url)])),
    ]);
    let fetchResults = Object.fromEntries(entries);
    let dataSources = Object.fromEntries(entries.map(([sourceKey, result]) => [sourceKey, result.ok ? result.data : null]));
    const enrichment = await enrichPanelSources(adapter, dataSources, getJsonBestEffort);
    dataSources = enrichment.dataSources;
    fetchResults = { ...fetchResults, ...enrichment.fetchResults };
    const primaryResult = fetchResults[adapter.primarySourceKey] || { ok: false, error: 'Missing primary source.' };
    const contractError = primaryResult.ok ? validateAdapterContract(adapter, dataSources) : null;
    const parseResult = primaryResult.ok && !contractError ? parsePanelSafely(adapter, dataSources) : { ok: false, data: null, error: contractError || primaryResult.error };
    const hasUsableData = parseResult.ok && adapter.hasUsableData(parseResult.data);
    const loadState = resolveLoadState(primaryResult, hasUsableData, parseResult.error || adapter.emptyReason);
    const summary = hasUsableData ? parseResult.data : adapter.fallback();
    const summaryAsOf = summaryDataAsOf(summary);
    const metadataMismatch = Boolean(
      publishedMetadata.ok
        && publishedMetadata.data?.dataAsOf
        && summaryAsOf
        && publishedMetadata.data.dataAsOf !== summaryAsOf,
    );
    adapter.render(summary, loadState.mode, loadState.error, project);
    const record = {
      project,
      adapterId: project.panelAdapter,
      summary,
      mode: loadState.mode,
      error: loadState.error,
      generatedAt: summary?.generatedAt || '',
      dataAsOf: summaryDataAsOf(summary),
      publishedMetadata: publishedMetadata.ok ? publishedMetadata.data : null,
      metadataMismatch,
      payloadBytes: Object.values(fetchResults).reduce((sum, result) => sum + numberOr(result.bytes, 0), 0),
      sourceCount: Object.keys(fetchResults).length,
    };
    renderPanelStatus(record);
    return record;
  }

  function validateAdapterContract(adapter, dataSources) {
    for (const [sourceKey, contract] of Object.entries(adapter.contracts || {})) {
      const payload = dataSources[sourceKey];
      if (!isRecord(payload)) return `${sourceKey} contract payload is missing or invalid.`;
      const version = payload[contract.versionField];
      if (String(version) !== String(contract.expectedVersion)) {
        return `${sourceKey} contract ${contract.versionField} expected ${contract.expectedVersion}, received ${version ?? 'missing'}.`;
      }
      for (const key of asArray(contract.requiredKeys)) {
        if (!(key in payload)) return `${sourceKey} contract missing required key: ${key}.`;
      }
      if (payload.contract && payload.contract !== 'quant-research-summary') {
        return `${sourceKey} contract expected quant-research-summary, received ${payload.contract}.`;
      }
      if (contract.expectedProjectId && payload.projectId !== contract.expectedProjectId) {
        return `${sourceKey} contract expected projectId ${contract.expectedProjectId}, received ${payload.projectId ?? 'missing'}.`;
      }
    }
    return null;
  }

  function parsePanelSafely(adapter, dataSources) {
    try {
      return { ok: true, data: adapter.parse(dataSources), error: null };
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      return { ok: false, data: null, error: `Payload parse failed: ${message}` };
    }
  }

  async function enrichPanelSources(adapter, dataSources, fetchJson) {
    if (typeof adapter.enrichSources !== 'function') return { dataSources, fetchResults: {} };
    try {
      const enriched = await adapter.enrichSources(dataSources, fetchJson);
      return {
        dataSources: isRecord(enriched?.dataSources) ? enriched.dataSources : dataSources,
        fetchResults: isRecord(enriched?.fetchResults) ? enriched.fetchResults : {},
      };
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      return adapter.enrichmentFailure
        ? adapter.enrichmentFailure(dataSources, message)
        : { dataSources, fetchResults: { enrichment: { ok: false, error: message } } };
    }
  }

  function resolveLoadState(fetchResult, hasUsableData, schemaReason) {
    if (fetchResult?.ok && hasUsableData) return { mode: 'live', error: null };
    if (fetchResult?.ok) return { mode: 'fallback', error: schemaReason || 'Payload schema did not contain usable data.' };
    return { mode: 'fallback', error: fetchResult?.error || 'Network or public JSON fetch failed.' };
  }

  async function getJsonBestEffort(url, timeoutMs = 8500, expectedSha256 = '') {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
    try {
      const response = await fetch(url, { signal: controller.signal, cache: 'no-store' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const text = await response.text();
      if (expectedSha256 && momentumSha256Hex(text) !== expectedSha256) throw new Error('Published JSON SHA-256 mismatch.');
      const headerBytes = finiteOrNull(response.headers.get('content-length'));
      const bytes = headerBytes ?? textByteLength(text);
      return { ok: true, data: JSON.parse(text), url, bytes };
    } catch (error) {
      return { ok: false, error: error instanceof Error ? error.message : String(error), url };
    } finally {
      window.clearTimeout(timeout);
    }
  }

  function configuredSupabaseMetadata() {
    const documentRef = globalThis.document;
    if (!documentRef || typeof documentRef.querySelector !== 'function') return null;
    const rawUrl = String(documentRef.querySelector('meta[name="quant-supabase-url"]')?.content || '').trim();
    const publishableKey = String(documentRef.querySelector('meta[name="quant-supabase-publishable-key"]')?.content || '').trim();
    if (!rawUrl || !publishableKey) return null;
    if (publishableKey.length > 4096 || /\s/.test(publishableKey)) return null;
    try {
      const url = new URL(rawUrl);
      const localhost = ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname);
      if (url.protocol !== 'https:' && !(localhost && url.protocol === 'http:')) return null;
      if (url.username || url.password || url.search || url.hash) return null;
      return { url: url.toString().replace(/\/+$/, ''), publishableKey };
    } catch (_) {
      return null;
    }
  }

  async function getPublishedSnapshotMetadata(projectId, timeoutMs = 4500, fetchImpl = null) {
    const config = configuredSupabaseMetadata();
    if (!config) return { ok: false, disabled: true, error: 'Supabase metadata is not configured.' };
    if (!/^[a-z0-9][a-z0-9-]{1,62}$/.test(String(projectId || ''))) {
      return { ok: false, disabled: false, error: 'Invalid platform project id.' };
    }
    const url = new URL(`${config.url}/rest/v1/published_project_snapshots`);
    url.searchParams.set(
      'select',
      'id,project_id,run_id,data_as_of,source,source_hash,artifact_url,artifact_sha256,byte_size,contract_version,created_at',
    );
    url.searchParams.set('project_id', `eq.${projectId}`);
    url.searchParams.set('order', 'data_as_of.desc,created_at.desc');
    url.searchParams.set('limit', '1');
    const controller = new AbortController();
    const timeout = globalThis.setTimeout(() => controller.abort(), timeoutMs);
    try {
      const request = fetchImpl || globalThis.fetch;
      if (typeof request !== 'function') throw new Error('Fetch is unavailable.');
      const response = await request(url.toString(), {
        signal: controller.signal,
        cache: 'no-store',
        headers: {
          Accept: 'application/json',
          apikey: config.publishableKey,
        },
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const rows = await response.json();
      const row = Array.isArray(rows) && isRecord(rows[0]) ? rows[0] : null;
      if (!row) return { ok: false, disabled: false, error: 'No published metadata row.' };
      if (row.project_id !== projectId) throw new Error('Supabase project id mismatch.');
      const artifactSha256 = String(row.artifact_sha256 || '').toLowerCase();
      const sourceHash = String(row.source_hash || '').toLowerCase();
      if (!/^[a-f0-9]{64}$/.test(artifactSha256)) throw new Error('Invalid artifact SHA-256.');
      if (!/^[a-f0-9]{8,128}$/.test(sourceHash)) throw new Error('Invalid source hash.');
      if (!/^\d{4}-\d{2}-\d{2}$/.test(String(row.data_as_of || ''))) throw new Error('Invalid data date.');
      return {
        ok: true,
        disabled: false,
        data: {
          projectId: row.project_id,
          runId: String(row.run_id || ''),
          dataAsOf: row.data_as_of,
          source: String(row.source || ''),
          sourceHash,
          artifactUrl: String(row.artifact_url || ''),
          artifactSha256,
          byteSize: numberOr(row.byte_size, 0),
          contractVersion: String(row.contract_version || ''),
          createdAt: String(row.created_at || ''),
        },
      };
    } catch (error) {
      return { ok: false, disabled: false, error: error instanceof Error ? error.message : String(error) };
    } finally {
      globalThis.clearTimeout(timeout);
    }
  }

  function isResearchSummary(payload, projectId = '') {
    return isRecord(payload)
      && payload.contract === 'quant-research-summary'
      && (!projectId || payload.projectId === projectId);
  }

  function summaryMeta(payload) {
    if (!isResearchSummary(payload)) return {};
    return {
      contract: payload.contract,
      projectId: payload.projectId,
      projectName: stringOr(payload.projectName, ''),
      generatedAt: stringOr(payload.generatedAt, ''),
      dataAsOf: stringOr(payload.dataAsOf, ''),
      statusState: stringOr(payload.status?.state, ''),
      statusLabel: stringOr(payload.status?.label, ''),
      cadence: stringOr(payload.status?.cadence, ''),
      expectedFreshnessDays: finiteOrNull(payload.status?.expectedFreshnessDays),
      degradedReasons: asArray(payload.status?.degradedReasons).map(String).filter(Boolean),
      limitations: asArray(payload.limitations).map(String).filter(Boolean),
      highlights: asRecords(payload.highlights),
      coverage: isRecord(payload.coverage) ? payload.coverage : {},
      automation: isRecord(payload.automation) ? payload.automation : {},
      sources: asRecords(payload.sources),
      payload: isRecord(payload.payload) ? payload.payload : {},
      detailUrl: stringOr(payload.detailUrl, ''),
      detailDataUrl: stringOr(payload.detailDataUrl, ''),
    };
  }

  function summaryEntities(payload) {
    return asRecords(payload?.primaryEntities).map((entity) => ({
      id: stringOr(entity.id, entity.entityKey, entity.symbol, entity.label, ''),
      symbol: stringOr(entity.symbol, ''),
      name: stringOr(entity.name, entity.symbol, ''),
      label: stringOr(entity.label, entity.symbol, entity.name, ''),
      sector: stringOr(entity.sector, ''),
      sectorLabel: stringOr(entity.sectorLabel, entity.sector, ''),
      themes: asArray(entity.themes).map(String).filter(Boolean),
      metrics: isRecord(entity.metrics) ? entity.metrics : {},
      signals: asArray(entity.signals).map(String).filter(Boolean),
      warnings: asArray(entity.warnings).map(String).filter(Boolean),
      status: stringOr(entity.status, ''),
      detailPath: stringOr(entity.detailPath, ''),
    }));
  }

  function highlightValue(meta, labelNeedle) {
    const lowerNeedle = String(labelNeedle || '').toLowerCase();
    const found = asRecords(meta.highlights).find((item) => String(item.label || '').toLowerCase().includes(lowerNeedle));
    return found?.value;
  }

  function firstLimitation(meta) {
    return asArray(meta.limitations).find(Boolean) || '원본 프로젝트의 방법론과 한계를 함께 확인하세요.';
  }

  function parseMomentum(payload, detailPayload = null) {
    const summaryV5 = isMomentumSummaryV5(payload) ? payload : null;
    const detailWasProvided = detailPayload !== null && detailPayload !== undefined;
    const dashboardV5 = isMomentumDashboardV5(detailPayload)
      ? detailPayload
      : (!summaryV5 && isMomentumDashboardV5(payload) ? payload : null);
    if (summaryV5 || dashboardV5) {
      if (detailWasProvided && !dashboardV5) {
        return momentumUnavailable(
          'Momentum dashboard resultIdentity/resultKey 또는 schemaVersion 5 계약이 유효하지 않아 보유 종목을 표시하지 않습니다.',
          'invalid_momentum_dashboard_contract',
        );
      }
      const parsedV5 = parseMomentumV5(summaryV5, dashboardV5);
      return parsedV5 || momentumUnavailable(
        'Momentum schemaVersion 5 summary/dashboard 계약을 확인할 수 없어 보유 종목을 표시하지 않습니다.',
        'unsupported_or_incomplete_momentum_contract',
      );
    }
    const summaryPayload = isMomentumSummaryV4(payload) ? payload : null;
    const dashboardPayload = isMomentumDashboardV4(detailPayload)
      ? detailPayload
      : (!summaryPayload && isMomentumDashboardV4(payload) ? payload : null);
    if (detailWasProvided && !dashboardPayload) {
      return momentumUnavailable(
        'Momentum dashboard resultIdentity/resultKey 또는 schemaVersion 4 계약이 유효하지 않아 보유 종목을 표시하지 않습니다.',
        'invalid_momentum_dashboard_contract',
      );
    }
    const parsed = parseMomentumV4(summaryPayload, dashboardPayload);
    return parsed || momentumUnavailable(
      'Momentum schemaVersion 4 summary/dashboard 계약을 확인할 수 없어 보유 종목을 표시하지 않습니다.',
      'unsupported_or_incomplete_momentum_contract',
    );
  }

  function momentumUnavailable(status, reason) {
    return {
      unavailable: true,
      factor: '-',
      selectedWeightingPolicy: '-',
      compositeScore: null,
      generatedAt: '',
      dataAsOf: '',
      dataMode: 'unsupported',
      dataModeLabel: '사용 불가',
      sourceLabel: '',
      evidenceStatus: '',
      outputLabel: '모델 포트폴리오',
      status,
      weightSource: '사용 가능한 Momentum 모델 비중 없음',
      rows: [],
      entities: [],
      meta: {
        schemaVersion: 5,
        statusState: 'unavailable',
        unavailable: true,
        holdingCount: 0,
        degradedReasons: [reason],
      },
    };
  }

  function validMomentumFactorAccountingV5(accounting) {
    if (!isRecord(accounting)) return false;
    const exactIntegers = {
      independentFactorCount: MOMENTUM_V5_GRID.independentFactorCount,
      expectedIndependentFactorCount: MOMENTUM_V5_GRID.independentFactorCount,
      evaluatedIndependentFactorCount: MOMENTUM_V5_GRID.independentFactorCount,
      missingIndependentFactorCount: 0,
      diagnosticAliasFactorCount: MOMENTUM_V5_GRID.aliasFactorCount,
    };
    if (Object.entries(exactIntegers).some(([field, expected]) => accounting[field] !== expected)) {
      return false;
    }
    const available = accounting.availableIndependentFactorCount;
    const excluded = accounting.excludedIndependentFactorCount;
    return Number.isInteger(available)
      && Number.isInteger(excluded)
      && available >= 0
      && excluded >= 0
      && available + excluded === MOMENTUM_V5_GRID.independentFactorCount
      && accounting.commonComparableFactorCount === available
      && isRecord(accounting.exclusionReasonCounts);
  }

  function isMomentumSummaryV5(payload) {
    return isRecord(payload)
      && Number(payload.schemaVersion) === 5
      && Boolean(validMomentumResultIdentity(payload))
      && Boolean(stringOr(payload.bestFactor, ''))
      && payload.weightingPolicy === MOMENTUM_FIXED_WEIGHTING_POLICY
      && Boolean(stringOr(payload.bestFactorReason, ''))
      && finiteOrNull(payload.compositeScore) !== null
      && payload.researchOnly === true
      && payload.notInvestmentRecommendation === true
      && typeof payload.dataMode === 'string'
      && typeof payload.sourceLabel === 'string'
      && typeof payload.evidenceStatus === 'string'
      && validMomentumFactorAccountingV5(payload.factorAccounting)
      && isRecord(payload.bestFactorPortfolio)
      && isRecord(payload.allocationMethod)
      && payload.allocationMethod.fixed === true
      && payload.allocationMethod.policyId === MOMENTUM_FIXED_WEIGHTING_POLICY
      && Array.isArray(payload.weights);
  }

  function isMomentumDashboardV5(payload) {
    return isRecord(payload)
      && Number(payload.schemaVersion) === 5
      && Boolean(validMomentumResultIdentity(payload))
      && Boolean(stringOr(payload.bestFactor, ''))
      && payload.weightingPolicy === MOMENTUM_FIXED_WEIGHTING_POLICY
      && Boolean(stringOr(payload.bestFactorReason, ''))
      && payload.researchScope?.researchOnly === true
      && payload.researchScope?.notInvestmentRecommendation === true
      && isRecord(payload.data)
      && isRecord(payload.researchScope)
      && isRecord(payload.bestFactorPortfolio)
      && isRecord(payload.allocationMethod)
      && payload.allocationMethod.fixed === true
      && payload.allocationMethod.policyId === MOMENTUM_FIXED_WEIGHTING_POLICY
      && Array.isArray(payload.factorRanking)
      && validMomentumMarketSnapshotParity(payload)
      && validMomentumLiveProvenance(payload)
      && validMomentumFactorGridV5(payload)
      && validMomentumAbsoluteGuardrailProfile(payload)
      && validMomentumConcentrationRows(payload)
      && validMomentumSelectedConcentrationContract(payload);
  }

  function isMomentumSummaryV4(payload) {
    return isRecord(payload)
      && Number(payload.schemaVersion) === 4
      && Boolean(validMomentumResultIdentity(payload))
      && Boolean(stringOr(payload.selectedFactor, ''))
      && Boolean(stringOr(payload.selectedWeightingPolicy, ''))
      && Boolean(stringOr(payload.selectedReason, ''))
      && finiteOrNull(payload.compositeScore) !== null
      && payload.researchOnly === true
      && payload.notInvestmentRecommendation === true
      && typeof payload.dataMode === 'string'
      && typeof payload.sourceLabel === 'string'
      && typeof payload.evidenceStatus === 'string'
      && validMomentumGridAccounting(payload.gridAccounting)
      && Array.isArray(payload.weights);
  }

  function isMomentumDashboardV4(payload) {
    return isRecord(payload)
      && Number(payload.schemaVersion) === 4
      && Boolean(validMomentumResultIdentity(payload))
      && Boolean(stringOr(payload.selectedFactor, ''))
      && Boolean(stringOr(payload.selectedWeightingPolicy, ''))
      && Boolean(stringOr(payload.selectedReason, ''))
      && payload.researchScope?.researchOnly === true
      && payload.researchScope?.notInvestmentRecommendation === true
      && isRecord(payload.data)
      && isRecord(payload.researchScope)
      && isRecord(payload.currentResearchTarget)
      && Array.isArray(payload.factorPolicyRanking)
      && validMomentumMarketSnapshotParity(payload)
      && validMomentumLiveProvenance(payload)
      && validMomentumFactorGrid(payload)
      && validMomentumAbsoluteGuardrailProfile(payload)
      && validMomentumConcentrationRows(payload)
      && validMomentumSelectedConcentrationContract(payload);
  }

  function momentumFiniteNumber(value) {
    return typeof value === 'number' && Number.isFinite(value);
  }

  function momentumCloseNumber(left, right) {
    if (!momentumFiniteNumber(left) || !momentumFiniteNumber(right)) return false;
    const scale = Math.max(1, Math.abs(left), Math.abs(right));
    return Math.abs(left - right) <= 1e-9 * scale;
  }

  function validMomentumGridAccounting(accounting) {
    if (!isRecord(accounting)) return false;
    const integerFields = {
      independentFactorCount: MOMENTUM_CANONICAL_GRID.independentFactorCount,
      policyCount: MOMENTUM_CANONICAL_GRID.policyCount,
      expectedIndependentPairCount: MOMENTUM_CANONICAL_GRID.independentPairCount,
      evaluatedIndependentPairCount: MOMENTUM_CANONICAL_GRID.independentPairCount,
      missingIndependentPairCount: 0,
      diagnosticAliasFactorCount: MOMENTUM_CANONICAL_GRID.aliasFactorCount,
      diagnosticAliasPairCount: MOMENTUM_CANONICAL_GRID.aliasPairCount,
    };
    if (Object.entries(integerFields).some(([field, expected]) => accounting[field] !== expected)) {
      return false;
    }
    const available = accounting.availableIndependentPairCount;
    const excluded = accounting.excludedIndependentPairCount;
    const common = accounting.commonComparableFactorCount;
    return Number.isInteger(available)
      && Number.isInteger(excluded)
      && available >= 0
      && excluded >= 0
      && available + excluded === MOMENTUM_CANONICAL_GRID.independentPairCount
      && Number.isInteger(common)
      && common >= 0
      && common <= MOMENTUM_CANONICAL_GRID.independentFactorCount;
  }

  function validMomentumMarketSnapshotParity(payload) {
    const data = payload.data;
    const marketSnapshot = payload.resultIdentity?.keyParts?.marketSnapshot;
    if (!isRecord(data) || !isRecord(marketSnapshot)) return false;
    const expected = {
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
    };
    if (
      !stringOr(expected.sourceMode, '').trim()
      || !stringOr(expected.sourceLabel, '').trim()
      || !stringOr(expected.priceBasis, '').trim()
      || !stringOr(expected.volumeBasis, '').trim()
      || !stringOr(expected.requestedThrough, '').trim()
      || !stringOr(expected.dataAsOf, '').trim()
      || !isRecord(expected.inputSha256)
      || !Number.isInteger(expected.rawCloseProxySymbolCount)
      || expected.rawCloseProxySymbolCount < 0
      || !Number.isInteger(expected.requestedCandidateCount)
      || !Number.isInteger(expected.providerReturnedCandidateCount)
      || !Number.isInteger(expected.analyzedSecurityCount)
    ) return false;
    return Object.entries(expected).every(([field, value]) => {
      if (isRecord(value)) {
        return JSON.stringify(canonicalMomentumIdentityValue(marketSnapshot[field]))
          === JSON.stringify(canonicalMomentumIdentityValue(value));
      }
      return marketSnapshot[field] === value;
    });
  }

  function validMomentumLiveProvenance(payload) {
    if (payload?.data?.mode !== 'live_market') return true;
    const priceSources = payload.priceSources;
    const sourceHealth = payload.sourceHealth;
    const hashes = payload.data?.inputSha256;
    const analyzedSecurityCount = payload.data?.analyzedSecurityCount;
    const analyzedSymbols = payload.data?.analyzedSymbols;
    const hashFields = Object.keys(isRecord(hashes) ? hashes : {}).sort();
    const expectedHashFields = (
      Number(payload.schemaVersion) === 5
        ? MOMENTUM_LIVE_SNAPSHOT_HASH_FIELDS_V5
        : MOMENTUM_LIVE_SNAPSHOT_HASH_FIELDS
    ).slice().sort();
    if (
      !Array.isArray(priceSources)
      || priceSources.length === 0
      || !Array.isArray(sourceHealth)
      || sourceHealth.length === 0
      || !isRecord(hashes)
      || JSON.stringify(hashFields) !== JSON.stringify(expectedHashFields)
      || expectedHashFields.some((field) => (
        !LOWERCASE_SHA256.test(stringOr(hashes[field], '').trim())
      ))
      || !Number.isInteger(analyzedSecurityCount)
      || analyzedSecurityCount < 1
      || !Array.isArray(analyzedSymbols)
      || analyzedSymbols.length !== analyzedSecurityCount
      || analyzedSymbols.some((symbol) => (
        typeof symbol !== 'string' || !symbol.trim()
      ))
    ) return false;

    const analyzedSymbolKeys = analyzedSymbols.map((symbol) => symbol.trim().toUpperCase());
    if (new Set(analyzedSymbolKeys).size !== analyzedSymbolKeys.length) return false;
    const priceSourceSymbols = new Set();
    for (const row of priceSources) {
      if (!isRecord(row)) return false;
      const symbol = stringOr(row.symbol, '').trim().toUpperCase();
      const source = stringOr(row.price_source, '').trim();
      if (!symbol || !source || priceSourceSymbols.has(symbol)) return false;
      priceSourceSymbols.add(symbol);
    }
    if (
      analyzedSymbolKeys.some((symbol) => !priceSourceSymbols.has(symbol))
      || hashes.priceSources !== momentumCanonicalRecordsSha256(priceSources)
      || hashes.dataSources !== momentumCanonicalRecordsSha256(sourceHealth)
    ) return false;
    const candidateSymbolsSha256 = momentumSha256Hex(
      momentumCanonicalKeyPartsJson(analyzedSymbols),
    );
    if (
      !LOWERCASE_SHA256.test(
        stringOr(payload.resultIdentity?.keyParts?.marketSnapshot?.candidateSymbolsSha256, '').trim(),
      )
      || payload.resultIdentity.keyParts.marketSnapshot.candidateSymbolsSha256
        !== candidateSymbolsSha256
    ) return false;
    return sourceHealth.every((row) => (
      isRecord(row)
      && Boolean(stringOr(row.source, '').trim())
      && Boolean(stringOr(row.status, '').trim())
    ));
  }

  function validMomentumFactorGridV5(payload) {
    const definitions = payload.factorDefinitions;
    const ranking = payload.factorRanking;
    if (
      !Array.isArray(definitions)
      || definitions.length !== MOMENTUM_V5_GRID.factorCount
      || !Array.isArray(ranking)
      || ranking.length !== MOMENTUM_V5_GRID.totalFactorRunCount
      || !validMomentumFactorAccountingV5(payload.factorAccounting)
    ) return false;

    const independent = new Set();
    const aliases = new Map();
    const factors = new Set();
    for (const definition of definitions) {
      if (!isRecord(definition)) return false;
      const factor = stringOr(definition.factor, '').trim();
      const aliasOf = stringOr(definition.compatibility_alias_of, '').trim();
      if (!factor || factors.has(factor)) return false;
      factors.add(factor);
      if (aliasOf) {
        if (definition.selection_eligible !== false) return false;
        aliases.set(factor, aliasOf);
      } else if (definition.selection_eligible === true) {
        independent.add(factor);
      } else {
        return false;
      }
    }
    if (
      independent.size !== MOMENTUM_V5_GRID.independentFactorCount
      || aliases.size !== MOMENTUM_V5_GRID.aliasFactorCount
      || [...aliases.values()].some((factor) => !independent.has(factor))
    ) return false;

    const rows = new Map();
    for (const row of ranking) {
      if (!isRecord(row)) return false;
      const factor = stringOr(row.factor, '').trim();
      if (
        !factors.has(factor)
        || rows.has(factor)
        || row.policy_id !== MOMENTUM_FIXED_WEIGHTING_POLICY
      ) return false;
      if (aliases.has(factor) && row.comparison_status !== 'duplicate_alias') return false;
      rows.set(factor, row);
    }
    const selected = ranking.filter((row) => row.selected === true);
    const meta = payload.meta;
    return rows.size === MOMENTUM_V5_GRID.factorCount
      && selected.length === 1
      && selected[0].factor === payload.bestFactor
      && selected[0].policy_id === payload.weightingPolicy
      && selected[0].rank === 1
      && selected[0].selection_eligible === true
      && isRecord(meta)
      && meta.factorCount === MOMENTUM_V5_GRID.factorCount
      && meta.independentFactorCount === MOMENTUM_V5_GRID.independentFactorCount
      && meta.aliasFactorCount === MOMENTUM_V5_GRID.aliasFactorCount
      && meta.portfolioCount === MOMENTUM_V5_GRID.factorCount
      && meta.factorRunCount === MOMENTUM_V5_GRID.totalFactorRunCount;
  }

  function validMomentumFactorGrid(payload) {
    const definitions = payload.factorDefinitions;
    const ranking = payload.factorPolicyRanking;
    if (
      !Array.isArray(definitions)
      || definitions.length !== MOMENTUM_CANONICAL_GRID.factorCount
      || !Array.isArray(ranking)
      || ranking.length !== MOMENTUM_CANONICAL_GRID.totalPairCount
      || !validMomentumGridAccounting(payload.gridAccounting)
    ) return false;

    const independent = new Set();
    const aliases = new Map();
    const factors = new Set();
    for (const definition of definitions) {
      if (!isRecord(definition)) return false;
      const factor = stringOr(definition.factor, '').trim();
      const aliasOf = stringOr(definition.compatibility_alias_of, '').trim();
      if (!factor || factors.has(factor)) return false;
      factors.add(factor);
      if (aliasOf) {
        if (definition.selection_eligible !== false) return false;
        aliases.set(factor, aliasOf);
      } else if (definition.selection_eligible === true) {
        independent.add(factor);
      } else {
        return false;
      }
    }
    if (
      independent.size !== MOMENTUM_CANONICAL_GRID.independentFactorCount
      || aliases.size !== MOMENTUM_CANONICAL_GRID.aliasFactorCount
      || [...aliases.values()].some((factor) => !independent.has(factor))
    ) return false;

    const policyIds = new Set(MOMENTUM_WEIGHTING_POLICIES);
    const pairs = new Set();
    let independentPairCount = 0;
    let aliasPairCount = 0;
    for (const row of ranking) {
      if (!isRecord(row)) return false;
      const factor = stringOr(row.factor, '').trim();
      const policyId = stringOr(row.policy_id, '').trim();
      const pair = `${factor}\u0000${policyId}`;
      if (!factors.has(factor) || !policyIds.has(policyId) || pairs.has(pair)) return false;
      pairs.add(pair);
      if (aliases.has(factor)) {
        if (row.comparison_status !== 'duplicate_alias') return false;
        aliasPairCount += 1;
      } else {
        independentPairCount += 1;
      }
    }
    if (
      independentPairCount !== MOMENTUM_CANONICAL_GRID.independentPairCount
      || aliasPairCount !== MOMENTUM_CANONICAL_GRID.aliasPairCount
    ) return false;
    for (const factor of factors) {
      for (const policyId of MOMENTUM_WEIGHTING_POLICIES) {
        if (!pairs.has(`${factor}\u0000${policyId}`)) return false;
      }
    }

    const meta = payload.meta;
    return isRecord(meta)
      && meta.factorCount === MOMENTUM_CANONICAL_GRID.factorCount
      && meta.independentFactorCount === MOMENTUM_CANONICAL_GRID.independentFactorCount
      && meta.aliasFactorCount === MOMENTUM_CANONICAL_GRID.aliasFactorCount
      && meta.policyCount === MOMENTUM_CANONICAL_GRID.policyCount
      && meta.policyFactorRunCount === MOMENTUM_CANONICAL_GRID.totalPairCount;
  }

  function momentumConcentration(allocation) {
    const weights = allocation.rows.map((row) => row.modelWeight);
    const investedWeight = weights.reduce((sum, weight) => sum + weight, 0);
    const normalized = investedWeight > 0
      ? weights.map((weight) => weight / investedWeight)
      : [];
    const riskySleeveHhi = normalized.reduce((sum, weight) => sum + weight * weight, 0);
    const ordered = weights.slice().sort((left, right) => right - left);
    return {
      investedWeight,
      cashWeight: allocation.cashWeight,
      riskySleeveHhi,
      effectiveNames: riskySleeveHhi > 0 ? 1 / riskySleeveHhi : 0,
      top1Weight: ordered.slice(0, 1).reduce((sum, weight) => sum + weight, 0),
      top5Weight: ordered.slice(0, 5).reduce((sum, weight) => sum + weight, 0),
      maxWeight: ordered[0] || 0,
    };
  }

  function expectedMomentumAbsoluteGuardrailProfile(payload) {
    const inputs = payload.researchInputs;
    const config = payload.config;
    if (
      !isRecord(inputs)
      || !['research-inputs-v1', 'research-inputs-v2'].includes(inputs.version)
      || !isRecord(config)
      || !['absolute-factor-policy-v1', 'absolute-factor-v2'].includes(
        config.absolute_guardrail_version,
      )
    ) return null;

    const rules = [];
    for (const spec of MOMENTUM_ABSOLUTE_GUARDRAIL_RULES) {
      const inputThreshold = inputs[spec.researchInput];
      const configThreshold = config[spec.config];
      if (
        !momentumFiniteNumber(inputThreshold)
        || !momentumFiniteNumber(configThreshold)
        || !momentumCloseNumber(inputThreshold, configThreshold)
      ) return null;
      rules.push({
        id: spec.id,
        metric: spec.metric,
        operator: spec.operator,
        threshold: inputThreshold * (spec.thresholdMultiplier || 1),
        unit: spec.unit,
      });
    }

    const extremeEventAction = stringOr(inputs.selectionExtremeEventAction, '').trim();
    const extremeEventPenaltyPoints = inputs.selectionExtremeEventPenaltyPoints;
    if (
      !['warn', 'penalize', 'exclude'].includes(extremeEventAction)
      || !momentumFiniteNumber(extremeEventPenaltyPoints)
      || config.selection_extreme_event_action !== extremeEventAction
      || !momentumCloseNumber(
        config.selection_extreme_event_penalty_points,
        extremeEventPenaltyPoints,
      )
    ) return null;

    return {
      id: config.absolute_guardrail_version,
      version: 1,
      policyNeutral: true,
      rules,
      requiredContracts: MOMENTUM_REQUIRED_GUARDRAIL_CONTRACTS,
      extremeEventAction,
      extremeEventPenaltyPoints,
    };
  }

  function validMomentumAbsoluteGuardrailProfile(payload) {
    const expected = expectedMomentumAbsoluteGuardrailProfile(payload);
    const actual = (payload.factorSelectionDecision ?? payload.selectionDecision)?.guardrailProfile;
    return Boolean(expected)
      && isRecord(actual)
      && momentumCanonicalKeyPartsJson(actual) === momentumCanonicalKeyPartsJson(expected);
  }

  function validMomentumConcentrationRows(payload) {
    const inputs = payload.researchInputs;
    const ranking = payload.factorRanking ?? payload.factorPolicyRanking;
    if (!isRecord(inputs) || !Array.isArray(ranking)) return false;
    const metricDomains = {
      min_target_effective_names: (value) => value >= 0,
      current_target_effective_names: (value) => value >= 0,
      max_target_hhi: (value) => value >= 0 && value <= 1,
      current_target_hhi: (value) => value >= 0 && value <= 1,
      max_target_weight: (value) => value >= 0 && value <= 1,
      current_target_max_weight: (value) => value >= 0 && value <= 1,
    };
    return ranking.every((row) => (
      isRecord(row)
      && Object.entries(metricDomains).every(([field, validDomain]) => (
        momentumFiniteNumber(row[field]) && validDomain(row[field])
      ))
      && MOMENTUM_CONCENTRATION_GUARDRAILS.every((rule) => {
        const value = row[rule.metric];
        const threshold = inputs[rule.researchInput];
        if (!momentumFiniteNumber(threshold)) return false;
        const expected = rule.operator === '>=' ? value >= threshold : value <= threshold;
        return row[rule.flag] === expected;
      })
    ));
  }

  function validMomentumSelectedConcentrationContract(payload) {
    const ranking = payload.factorRanking ?? payload.factorPolicyRanking;
    const selectedRows = asRecords(ranking).filter((row) => row.selected === true);
    if (selectedRows.length !== 1 || !isRecord(payload.config)) return false;
    const selected = selectedRows[0];
    if (
      selected.factor !== (payload.bestFactor ?? payload.selectedFactor)
      || selected.policy_id !== (payload.weightingPolicy ?? payload.selectedWeightingPolicy)
      || selected.comparison_status !== 'available'
      || selected.selection_status !== 'eligible'
      || selected.selection_eligible !== true
      || selected.standard_guardrail_pass !== true
      || selected.contribution_guardrail_pass !== true
      || selected.absolute_guardrail_pass !== true
      || !momentumFiniteNumber(selected.selection_score)
      || MOMENTUM_CONCENTRATION_GUARDRAILS.some((rule) => selected[rule.flag] !== true)
    ) return false;

    const target = payload.bestFactorPortfolio ?? payload.currentResearchTarget;
    const allocation = validateMomentumAllocation(
      target?.weights,
      target?.cashWeight,
      payload.config.max_weight,
    );
    if (!allocation || !isRecord(target?.concentration)) return false;
    const expectedConcentration = momentumConcentration(allocation);
    if (Object.entries(expectedConcentration).some(([field, expected]) => (
      !momentumCloseNumber(target.concentration[field], expected)
    ))) return false;

    const currentMetrics = {
      current_target_effective_names: target.concentration.effectiveNames,
      current_target_hhi: target.concentration.riskySleeveHhi,
      current_target_max_weight: target.concentration.maxWeight,
    };
    if (Object.entries(currentMetrics).some(([field, expected]) => (
      !momentumCloseNumber(selected[field], expected)
    ))) return false;

    return true;
  }

  function normalizeMomentumDataMode(value) {
    const mode = stringOr(value, '').trim().toLowerCase();
    return ['live_market', 'demo', 'local_file'].includes(mode) ? mode : '';
  }

  function momentumDataModeLabel(mode) {
    if (mode === 'live_market') return '실제 시장 데이터';
    if (mode === 'demo') return '합성 데모';
    if (mode === 'local_file') return '로컬 연구 데이터';
    return '데이터 모드 확인 필요';
  }

  function momentumEvidenceLabel(status) {
    if (status === 'same_sample_descriptive_actual_market') return '실제 시장 동일 표본 설명 순위';
    if (status === 'same_sample_descriptive') return '동일 표본 설명 순위';
    return status ? `근거 상태 ${status}` : '근거 상태 확인 필요';
  }

  function appendMomentumContractConflict(reasons, field, summaryValue, dashboardValue) {
    if (summaryValue && dashboardValue && summaryValue !== dashboardValue) {
      reasons.push(`${field}_mismatch:${summaryValue}!=${dashboardValue}`);
    }
  }

  function matchingMomentumContractValue(values) {
    const normalized = values.map((value) => stringOr(value, '').trim());
    if (!normalized.length || normalized.some((value) => !value)) return '';
    return new Set(normalized).size === 1 ? normalized[0] : '';
  }

  function canonicalMomentumIdentityValue(value) {
    if (Array.isArray(value)) return value.map(canonicalMomentumIdentityValue);
    if (!isRecord(value)) return value;
    return Object.keys(value).sort().reduce((result, key) => {
      result[key] = canonicalMomentumIdentityValue(value[key]);
      return result;
    }, {});
  }

  function momentumUtf8Bytes(value) {
    const bytes = [];
    for (let index = 0; index < value.length; index += 1) {
      let codePoint = value.charCodeAt(index);
      if (codePoint >= 0xd800 && codePoint <= 0xdbff && index + 1 < value.length) {
        const low = value.charCodeAt(index + 1);
        if (low >= 0xdc00 && low <= 0xdfff) {
          codePoint = 0x10000 + ((codePoint - 0xd800) << 10) + (low - 0xdc00);
          index += 1;
        }
      }
      if (codePoint < 0x80) {
        bytes.push(codePoint);
      } else if (codePoint < 0x800) {
        bytes.push(0xc0 | (codePoint >>> 6), 0x80 | (codePoint & 0x3f));
      } else if (codePoint < 0x10000) {
        bytes.push(
          0xe0 | (codePoint >>> 12),
          0x80 | ((codePoint >>> 6) & 0x3f),
          0x80 | (codePoint & 0x3f),
        );
      } else {
        bytes.push(
          0xf0 | (codePoint >>> 18),
          0x80 | ((codePoint >>> 12) & 0x3f),
          0x80 | ((codePoint >>> 6) & 0x3f),
          0x80 | (codePoint & 0x3f),
        );
      }
    }
    return bytes;
  }

  function momentumSha256Hex(value) {
    const constants = [
      0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
      0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
      0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
      0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
      0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
      0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
      0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
      0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
    ];
    const bytes = momentumUtf8Bytes(String(value));
    const bitLength = bytes.length * 8;
    bytes.push(0x80);
    while (bytes.length % 64 !== 56) bytes.push(0);
    const high = Math.floor(bitLength / 0x100000000);
    const low = bitLength >>> 0;
    for (let shift = 24; shift >= 0; shift -= 8) bytes.push((high >>> shift) & 0xff);
    for (let shift = 24; shift >= 0; shift -= 8) bytes.push((low >>> shift) & 0xff);

    const hash = [
      0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
      0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
    ];
    const words = new Uint32Array(64);
    const rotateRight = (word, bits) => (word >>> bits) | (word << (32 - bits));
    for (let offset = 0; offset < bytes.length; offset += 64) {
      for (let index = 0; index < 16; index += 1) {
        const position = offset + index * 4;
        words[index] = (
          (bytes[position] << 24)
          | (bytes[position + 1] << 16)
          | (bytes[position + 2] << 8)
          | bytes[position + 3]
        ) >>> 0;
      }
      for (let index = 16; index < 64; index += 1) {
        const left = words[index - 15];
        const right = words[index - 2];
        const sigma0 = rotateRight(left, 7) ^ rotateRight(left, 18) ^ (left >>> 3);
        const sigma1 = rotateRight(right, 17) ^ rotateRight(right, 19) ^ (right >>> 10);
        words[index] = (words[index - 16] + sigma0 + words[index - 7] + sigma1) >>> 0;
      }

      let [a, b, c, d, e, f, g, h] = hash;
      for (let index = 0; index < 64; index += 1) {
        const sum1 = rotateRight(e, 6) ^ rotateRight(e, 11) ^ rotateRight(e, 25);
        const choice = (e & f) ^ (~e & g);
        const temporary1 = (h + sum1 + choice + constants[index] + words[index]) >>> 0;
        const sum0 = rotateRight(a, 2) ^ rotateRight(a, 13) ^ rotateRight(a, 22);
        const majority = (a & b) ^ (a & c) ^ (b & c);
        const temporary2 = (sum0 + majority) >>> 0;
        h = g;
        g = f;
        f = e;
        e = (d + temporary1) >>> 0;
        d = c;
        c = b;
        b = a;
        a = (temporary1 + temporary2) >>> 0;
      }
      hash[0] = (hash[0] + a) >>> 0;
      hash[1] = (hash[1] + b) >>> 0;
      hash[2] = (hash[2] + c) >>> 0;
      hash[3] = (hash[3] + d) >>> 0;
      hash[4] = (hash[4] + e) >>> 0;
      hash[5] = (hash[5] + f) >>> 0;
      hash[6] = (hash[6] + g) >>> 0;
      hash[7] = (hash[7] + h) >>> 0;
    }
    return hash.map((word) => word.toString(16).padStart(8, '0')).join('');
  }

  function momentumCanonicalKeyPartsJson(keyParts) {
    return JSON.stringify(canonicalMomentumIdentityValue(keyParts));
  }

  function momentumCanonicalRecordsSha256(records) {
    if (!Array.isArray(records) || records.some((record) => !isRecord(record))) return '';
    return momentumSha256Hex(momentumCanonicalKeyPartsJson(records));
  }

  function momentumResultKeyForKeyParts(keyParts) {
    return momentumSha256Hex(momentumCanonicalKeyPartsJson(keyParts));
  }

  function validMomentumResultIdentity(payload) {
    const identity = payload?.resultIdentity;
    let canonicalKeyParts = null;
    try {
      canonicalKeyParts = JSON.parse(identity?.canonicalKeyPartsJson || '');
    } catch (_error) {
      return null;
    }
    if (
      !isRecord(identity)
      || identity.identityVersion !== MOMENTUM_RESULT_IDENTITY_VERSION
      || !LOWERCASE_SHA256.test(stringOr(identity.resultKey, '').trim())
      || !isRecord(identity.keyParts)
      || identity.keyParts.identityVersion !== MOMENTUM_RESULT_IDENTITY_VERSION
      || identity.keyParts.canonicalJsonVersion !== MOMENTUM_CANONICAL_JSON_VERSION
      || !isRecord(canonicalKeyParts)
      || JSON.stringify(canonicalMomentumIdentityValue(canonicalKeyParts))
        !== JSON.stringify(canonicalMomentumIdentityValue(identity.keyParts))
      || momentumCanonicalKeyPartsJson(identity.keyParts) !== identity.canonicalKeyPartsJson
      || momentumSha256Hex(identity.canonicalKeyPartsJson) !== identity.resultKey
    ) return null;
    if (
      Object.prototype.hasOwnProperty.call(payload, 'resultKey')
      && stringOr(payload.resultKey, '').trim() !== stringOr(identity.resultKey, '').trim()
    ) return null;
    return identity;
  }

  function matchingMomentumResultIdentity(summaryPayload, dashboardPayload) {
    const identities = [summaryPayload, dashboardPayload]
      .filter(Boolean)
      .map(validMomentumResultIdentity);
    if (!identities.length || identities.some((identity) => !identity)) return null;
    const first = JSON.stringify(canonicalMomentumIdentityValue(identities[0]));
    if (identities.some((identity) => JSON.stringify(canonicalMomentumIdentityValue(identity)) !== first)) {
      return null;
    }
    return identities[0];
  }

  function momentumV5CompatibilityPayload(payload) {
    if (!payload) return null;
    return {
      ...payload,
      schemaVersion: 4,
      selectedFactor: payload.bestFactor,
      selectedWeightingPolicy: payload.weightingPolicy,
      selectedReason: payload.bestFactorReason,
      selectionDecision: payload.factorSelectionDecision,
      gridAccounting: payload.factorAccounting,
      factorPolicyRanking: payload.factorRanking,
      currentResearchTarget: payload.bestFactorPortfolio,
      currentTransition: payload.bestFactorTransition,
    };
  }

  function parseMomentumV5(summaryPayload, dashboardPayload) {
    const parsed = parseMomentumV4(
      momentumV5CompatibilityPayload(summaryPayload),
      momentumV5CompatibilityPayload(dashboardPayload),
    );
    if (!parsed) return null;
    const source = dashboardPayload || summaryPayload;
    const allocationSource = dashboardPayload ? 'dashboard.bestFactorPortfolio.weights' : 'summary.weights';
    parsed.weightSource = allocationSource;
    parsed.weightingPolicyReason = source?.bestFactorReason || parsed.weightingPolicyReason;
    parsed.currentTransition = summaryPayload?.bestFactorTransition
      ?? dashboardPayload?.bestFactorTransition
      ?? null;
    parsed.entities = parsed.entities.map((entity) => ({
      ...entity,
      signals: ['Momentum schemaVersion 5 Python 최고 팩터 포트폴리오'],
    }));
    parsed.meta = {
      ...parsed.meta,
      schemaVersion: 5,
      bestFactor: parsed.factor,
      weightingPolicy: parsed.selectedWeightingPolicy,
      allocationMethod: source?.allocationMethod || null,
      statusLabel: `${parsed.dataModeLabel} · Momentum v5 Python 최고 팩터 포트폴리오`,
    };
    return parsed;
  }

  function parseMomentumV4(summaryPayload, dashboardPayload) {
    if (!summaryPayload && !dashboardPayload) return null;
    if (normalizeMomentumDataMode(summaryPayload?.dataMode) === 'live_market' && !dashboardPayload) {
      return null;
    }
    const resultIdentity = matchingMomentumResultIdentity(summaryPayload, dashboardPayload);
    if (!resultIdentity) return null;
    const summaryTarget = isRecord(summaryPayload?.currentResearchTarget)
      ? summaryPayload.currentResearchTarget
      : null;
    const dashboardTarget = isRecord(dashboardPayload?.currentResearchTarget)
      ? dashboardPayload.currentResearchTarget
      : null;
    if (
      summaryTarget
      && dashboardTarget
      && JSON.stringify(canonicalMomentumIdentityValue(summaryTarget))
        !== JSON.stringify(canonicalMomentumIdentityValue(dashboardTarget))
    ) return null;
    const currentTarget = dashboardTarget || summaryTarget;
    const factorSources = [];
    const policySources = [];
    const asOfSources = [];
    if (summaryPayload) {
      factorSources.push(summaryPayload.selectedFactor);
      policySources.push(summaryPayload.selectedWeightingPolicy);
      asOfSources.push(summaryPayload.dataAsOf);
    }
    if (dashboardPayload) {
      factorSources.push(dashboardPayload.selectedFactor, currentTarget?.factor);
      policySources.push(dashboardPayload.selectedWeightingPolicy, currentTarget?.weightingPolicyId);
      asOfSources.push(
        dashboardPayload.data?.asOf,
        currentTarget?.asOf,
        currentTarget?.signalDate,
      );
    }
    const factor = matchingMomentumContractValue(factorSources);
    const selectedWeightingPolicy = matchingMomentumContractValue(policySources);
    const dataAsOf = matchingMomentumContractValue(asOfSources);
    if (!factor || !selectedWeightingPolicy || !dataAsOf) return null;

    const summaryAllocation = summaryPayload
      ? validateMomentumAllocation(
        summaryPayload.weights,
        summaryPayload.cashWeight,
        summaryPayload.maxWeight,
      )
      : null;
    const dashboardAllocation = dashboardPayload
      ? validateMomentumAllocation(
        currentTarget?.weights,
        currentTarget?.cashWeight,
        dashboardPayload.config?.max_weight,
      )
      : null;
    if ((summaryPayload && !summaryAllocation) || (dashboardPayload && !dashboardAllocation)) return null;
    if (
      summaryAllocation
      && dashboardAllocation
      && !matchingMomentumAllocations(summaryAllocation, dashboardAllocation)
    ) return null;
    const allocation = dashboardAllocation || summaryAllocation;
    const rows = allocation?.rows || [];

    const summaryModeRaw = summaryPayload ? stringOr(summaryPayload.dataMode, '') : '';
    const dashboardModeRaw = dashboardPayload ? stringOr(dashboardPayload.data?.mode, '') : '';
    const summaryMode = normalizeMomentumDataMode(summaryModeRaw);
    const dashboardMode = normalizeMomentumDataMode(dashboardModeRaw);
    const degradedReasons = [];
    if ((summaryPayload && !summaryMode) || (dashboardPayload && !dashboardMode)) return null;
    appendMomentumContractConflict(degradedReasons, 'data_mode', summaryMode, dashboardMode);
    const dataMode = stringOr(summaryMode, dashboardMode);
    if (!dataMode) return null;

    const summarySourceLabel = summaryPayload ? stringOr(summaryPayload.sourceLabel, '') : '';
    const dashboardSourceLabel = dashboardPayload ? stringOr(dashboardPayload.data?.sourceLabel, '') : '';
    if (summaryPayload && !summarySourceLabel) degradedReasons.push('summary_source_label_missing');
    if (dashboardPayload && !dashboardSourceLabel) degradedReasons.push('dashboard_source_label_missing');
    appendMomentumContractConflict(degradedReasons, 'source_label', summarySourceLabel, dashboardSourceLabel);
    const sourceLabel = stringOr(summarySourceLabel, dashboardSourceLabel);
    if (!sourceLabel) return null;

    const summaryEvidenceStatus = summaryPayload ? stringOr(summaryPayload.evidenceStatus, '') : '';
    const dashboardEvidenceStatus = dashboardPayload ? stringOr(dashboardPayload.researchScope?.evidenceStatus, '') : '';
    if (summaryPayload && !summaryEvidenceStatus) degradedReasons.push('summary_evidence_status_missing');
    if (dashboardPayload && !dashboardEvidenceStatus) degradedReasons.push('dashboard_evidence_status_missing');
    appendMomentumContractConflict(degradedReasons, 'evidence_status', summaryEvidenceStatus, dashboardEvidenceStatus);
    const evidenceStatus = stringOr(summaryEvidenceStatus, dashboardEvidenceStatus);
    if (!evidenceStatus) return null;
    if (!['same_sample_descriptive', 'same_sample_descriptive_actual_market'].includes(evidenceStatus)) {
      degradedReasons.push(`evidence_status_unrecognized:${evidenceStatus}`);
    }

    const summaryPolicyReason = summaryPayload ? stringOr(summaryPayload.selectedReason, '') : '';
    const dashboardPolicyReason = dashboardPayload ? stringOr(dashboardPayload.selectedReason, '') : '';
    if ((summaryPayload && !summaryPolicyReason) || (dashboardPayload && !dashboardPolicyReason)) return null;
    appendMomentumContractConflict(
      degradedReasons,
      'weighting_policy_reason',
      summaryPolicyReason,
      dashboardPolicyReason,
    );
    const weightingPolicyReason = stringOr(summaryPolicyReason, dashboardPolicyReason);

    const ranking = asRecords(dashboardPayload?.factorPolicyRanking).find((row) => (
      row.factor === factor && row.policy_id === selectedWeightingPolicy
    )) || {};
    const compositeScore = finiteOrNull(summaryPayload?.compositeScore ?? ranking.composite_score);
    if (compositeScore === null) return null;
    const generatedAt = stringOr(summaryPayload?.generatedAt, dashboardPayload?.generatedAtUtc, '');
    const cashWeight = allocation.cashWeight;
    const maxWeight = allocation.maxWeight;
    const requestedCandidateCount = finiteOrNull(
      summaryPayload?.requestedCandidateCount
      ?? dashboardPayload?.data?.requestedCandidateCount,
    );
    const providerReturnedCandidateCount = finiteOrNull(
      summaryPayload?.providerReturnedCandidateCount
      ?? dashboardPayload?.data?.providerReturnedCandidateCount,
    );
    const universeSize = finiteOrNull(summaryPayload?.universeSize ?? dashboardPayload?.data?.inputSecurityCount);
    const eligibleSecurityCount = finiteOrNull(
      summaryPayload?.eligibleSecurityCount
      ?? dashboardPayload?.data?.latestEligibleSecurityCount
      ?? currentTarget?.eligibleSecurityCount,
    );
    const limitations = asArray(
      summaryPayload?.limitations
      ?? dashboardPayload?.researchScope?.limitations
      ?? dashboardPayload?.data?.notes,
    ).map(String).filter(Boolean);
    const dataModeLabel = momentumDataModeLabel(dataMode);
    const modeWarning = dataMode === 'demo'
      ? '합성 데모 결과이며 실제 시장 데이터나 투자 권고가 아닙니다.'
      : '';
    const warnings = [modeWarning, ...degradedReasons, ...limitations].filter(Boolean);
    const statusState = degradedReasons.length ? 'degraded' : (dataMode === 'demo' ? 'demo' : 'ok');
    const status = `${dataModeLabel} · ${sourceLabel} · ${momentumEvidenceLabel(evidenceStatus)} · Python 최고 팩터 ${factor} · 고정 비중 방법 ${selectedWeightingPolicy} · 종합 점수 ${formatNumber(compositeScore)} · 모델 ${formatInteger(rows.length)}개 · 현금 ${formatPercent(cashWeight)}${degradedReasons.length ? ` · 계약 경고 ${degradedReasons.join(', ')}` : ''}`;
    const entities = rows.map((row) => ({
      id: row.symbol,
      symbol: row.symbol,
      name: row.name,
      label: `${row.symbol} · rank ${row.rank}`,
      themes: ['Momentum', factor],
      metrics: {
        rank: row.rank,
        factor,
        dataMode,
        dataModeLabel,
        compositeScore,
        weightingPolicyId: selectedWeightingPolicy,
        cashWeight,
        signal: row.signal,
        modelWeight: row.modelWeight,
      },
      signals: ['Momentum schemaVersion 4 모델 포트폴리오'],
      warnings: warnings.slice(0, 2),
    }));
    return {
      factor,
      resultIdentity,
      resultKey: resultIdentity.resultKey,
      selectedWeightingPolicy,
      weightingPolicyReason,
      compositeScore,
      generatedAt,
      dataAsOf,
      dataMode,
      dataModeLabel,
      sourceLabel,
      evidenceStatus,
      outputLabel: '연구 모델 포트폴리오',
      status,
      cashWeight,
      maxWeight,
      concentration: summaryPayload?.concentration ?? currentTarget?.concentration ?? null,
      currentTransition: summaryPayload?.currentTransition ?? dashboardPayload?.currentTransition ?? null,
      weightSource: dashboardAllocation ? 'dashboard.currentResearchTarget.weights' : 'summary.weights',
      rows: rows.slice(0, 5),
      entities,
      meta: {
        schemaVersion: 4,
        resultIdentity,
        resultKey: resultIdentity.resultKey,
        selectedFactor: factor,
        selectedWeightingPolicy,
        weightingPolicyReason,
        compositeScore,
        requestedCandidateCount,
        providerReturnedCandidateCount,
        universeSize,
        eligibleSecurityCount,
        cashWeight,
        maxWeight,
        dataMode,
        dataModeLabel,
        sourceLabel,
        evidenceStatus,
        researchOnly: true,
        notInvestmentRecommendation: true,
        statusState,
        statusLabel: `${dataModeLabel} · Momentum v4 연구 모델 포트폴리오`,
        degradedReasons,
        limitations,
      },
    };
  }

  function momentumRowsFromModelWeights(weights) {
    return asRecords(weights)
      .slice()
      .sort((a, b) => numberOr(a.rank, 9999) - numberOr(b.rank, 9999))
      .map((row, index) => {
        return {
          rank: numberOr(row.rank, index + 1),
          symbol: stringOr(row.symbol, '-'),
          name: stringOr(row.name, row.symbol, '-'),
          signal: finiteOrNull(row.factorScore),
          modelWeight: finiteOrNull(row.weight),
        };
      })
      .filter((row) => row.symbol !== '-' && row.signal !== null && row.modelWeight !== null);
  }

  function validateMomentumAllocation(weights, cashWeightValue, maxWeightValue) {
    if (!Array.isArray(weights) || asRecords(weights).length !== weights.length) return null;
    const cashWeight = finiteOrNull(cashWeightValue);
    const maxWeight = finiteOrNull(maxWeightValue);
    if (
      cashWeight === null
      || cashWeight < 0
      || cashWeight > 1
      || maxWeight === null
      || maxWeight <= 0
      || maxWeight > 1
    ) return null;

    const rows = momentumRowsFromModelWeights(weights);
    if (rows.length !== weights.length) return null;
    const symbols = new Set();
    let totalWeight = cashWeight;
    for (const row of rows) {
      const symbolKey = row.symbol.trim().toUpperCase();
      if (
        !symbolKey
        || symbols.has(symbolKey)
        || row.modelWeight < 0
        || row.modelWeight > maxWeight + 1e-9
      ) return null;
      symbols.add(symbolKey);
      totalWeight += row.modelWeight;
    }
    if (Math.abs(totalWeight - 1) > 1e-8) return null;
    return { rows, cashWeight, maxWeight };
  }

  function matchingMomentumAllocations(summaryAllocation, dashboardAllocation) {
    const closeNumber = (left, right) => {
      const scale = Math.max(1, Math.abs(Number(left)), Math.abs(Number(right)));
      return Math.abs(Number(left) - Number(right)) <= 1e-9 * scale;
    };
    if (
      !closeNumber(summaryAllocation.cashWeight, dashboardAllocation.cashWeight)
      || !closeNumber(summaryAllocation.maxWeight, dashboardAllocation.maxWeight)
      || summaryAllocation.rows.length !== dashboardAllocation.rows.length
    ) return false;

    const dashboardBySymbol = new Map(dashboardAllocation.rows.map((row) => [
      row.symbol.trim().toUpperCase(),
      row,
    ]));
    return summaryAllocation.rows.every((row) => {
      const dashboardRow = dashboardBySymbol.get(row.symbol.trim().toUpperCase());
      return dashboardRow
        && row.rank === dashboardRow.rank
        && closeNumber(row.signal, dashboardRow.signal)
        && closeNumber(row.modelWeight, dashboardRow.modelWeight);
    });
  }

  function parseDram(pricesPayload, seriesPayload, statusPayload, summaryPayload) {
    const meta = isResearchSummary(summaryPayload, 'dram') ? summaryMeta(summaryPayload) : {};
    const entities = summaryEntities(summaryPayload);
    const observations = asRecords(pricesPayload?.observations);
    const manifestSeries = asRecords(seriesPayload?.series);
    const trendforceDailyKeys = new Set(manifestSeries.filter(isTrendforceDailySeries).map(dramObservationKey).filter(Boolean));
    const trendforceDailySeries = buildDramSeries(observations, manifestSeries, (observation) => isTrendforceDailyObservation(observation, trendforceDailyKeys));
    const fallbackSeries = trendforceDailySeries.length ? trendforceDailySeries : buildDramSeries(observations, manifestSeries, () => true);
    const selected = fallbackSeries.filter((item) => item.points.length >= 2).slice(0, 6);
    const series = selected.length ? selected : fallbackSeries.slice(0, 6);
    const trendforceDailyMode = trendforceDailySeries.length > 0;

    return {
      generatedAt: stringOr(pricesPayload?.generated_at, statusPayload?.generated_at, ''),
      observationCount: series.reduce((sum, item) => sum + item.points.length, 0) || observations.length || finiteOrNull(statusPayload?.observation_count),
      status: trendforceDailyMode
        ? appendDramSourceStatus(stringOr(meta.statusLabel, '라이브 공개 JSON 표시 중'), 'TrendForce daily saved prices')
        : stringOr(meta.statusLabel, '라이브 공개 JSON 표시 중'),
      series,
      entities,
      meta,
    };
  }

  function buildDramSeries(observations, manifestSeries, predicate) {
    const manifestByKey = new Map(asRecords(manifestSeries).map((item) => [dramObservationKey(item), item]).filter(([key]) => key));
    const groups = new Map();
    for (const observation of asRecords(observations)) {
      if (!predicate(observation)) continue;
      const key = dramObservationKey(observation) || stringOr(observation.product_name, observation.product_id, 'Unknown DRAM');
      const manifest = manifestByKey.get(key) || {};
      const name = stringOr(observation.product_name, manifest.product_name, observation.product_id, 'Unknown DRAM');
      const value = dramMetricValue(observation.values || {});
      const date = stringOr(observation.effective_date, observation.date, '');
      if (!isValidChartPoint(date, value)) continue;
      if (!groups.has(key)) {
        groups.set(key, {
          key,
          name,
          source: stringOr(observation.source, manifest.source, ''),
          cadence: stringOr(observation.cadence, asArray(manifest.cadences)[0], ''),
          representative: Boolean(manifest.representative),
          points: [],
        });
      }
      groups.get(key).points.push([date, value]);
    }

    return [...groups.values()]
      .map((item) => ({
        ...item,
        name: item.source === 'trendforce' && item.cadence === 'daily' ? `${item.name} · TrendForce daily` : item.name,
        points: item.points
          .sort((a, b) => a[0].localeCompare(b[0]))
          .filter((point, index, arr) => index === 0 || point[0] !== arr[index - 1][0]),
      }))
      .filter((item) => item.points.length > 0)
      .sort((a, b) => {
        const aTrend = a.source === 'trendforce' && a.cadence === 'daily';
        const bTrend = b.source === 'trendforce' && b.cadence === 'daily';
        if (aTrend !== bTrend) return aTrend ? -1 : 1;
        if (a.representative !== b.representative) return a.representative ? -1 : 1;
        return b.points.length - a.points.length || a.name.localeCompare(b.name);
      });
  }

  function dramObservationKey(item) {
    return stringOr(item?.product_id, item?.product_name, '').toLowerCase();
  }

  function isTrendforceDailySeries(item) {
    return String(item?.source || '').toLowerCase() === 'trendforce'
      && asArray(item?.cadences).map((value) => String(value).toLowerCase()).includes('daily');
  }

  function isTrendforceDailyObservation(observation, trendforceDailyKeys = new Set()) {
    const source = String(observation?.source || '').toLowerCase();
    const cadence = String(observation?.cadence || '').toLowerCase();
    const key = dramObservationKey(observation);
    return source === 'trendforce' && (cadence === 'daily' || trendforceDailyKeys.has(key));
  }

  function appendDramSourceStatus(status, sourceLabel) {
    return `${status} · ${sourceLabel}`;
  }

  function dramMetricValue(values) {
    const direct = finiteOrNull(values.average ?? values.session_average);
    if (direct !== null) return direct;
    const high = finiteOrNull(values.daily_high ?? values.high ?? values.session_high);
    const low = finiteOrNull(values.daily_low ?? values.low ?? values.session_low);
    if (high !== null && low !== null) return (high + low) / 2;
    return high ?? low ?? Number.NaN;
  }

  function parseBestFactor(payload) {
    if (isResearchSummary(payload, 'best')) {
      const meta = summaryMeta(payload);
      const entities = summaryEntities(payload);
      const rows = entities
        .sort((a, b) => numberOr(a.metrics.rank, 9999) - numberOr(b.metrics.rank, 9999))
        .map((entity, index) => ({
          rank: numberOr(entity.metrics.rank, index + 1),
          ticker: stringOr(entity.symbol, entity.name, '-'),
          score: finiteOrNull(entity.metrics.score),
          weight: finiteOrNull(entity.metrics.weight),
          date: stringOr(entity.metrics.rebalanceDate, meta.dataAsOf, ''),
          themes: entity.themes,
          warnings: entity.warnings,
        }));
      return {
        factor: stringOr(highlightValue(meta, 'factor'), FALLBACK_SNAPSHOT.best.factor),
        generatedAt: meta.generatedAt,
        dataEndDate: meta.dataAsOf,
        compositeScore: finiteOrNull(highlightValue(meta, 'composite')),
        status: stringOr(meta.statusLabel, '공통 summary contract 표시 중'),
        rows: rows.slice(0, 5),
        entities,
        meta,
      };
    }
    const summary = isRecord(payload?.summary) ? payload.summary : {};
    const bestRanking = asRecords(payload?.rankings).slice().sort((a, b) => numberOr(a.rank, 9999) - numberOr(b.rank, 9999))[0] || {};
    const factor = stringOr(summary.best_factor, bestRanking.factor, FALLBACK_SNAPSHOT.best.factor);
    const rows = asRecords(payload?.latest_holdings)
      .filter((row) => !factor || row.factor === factor)
      .slice()
      .sort((a, b) => numberOr(b.weight, -1) - numberOr(a.weight, -1))
      .map((row, index) => ({
        rank: index + 1,
        ticker: stringOr(row.ticker, row.symbol, '-'),
        score: finiteOrNull(row.score),
        weight: finiteOrNull(row.weight),
        date: stringOr(row.rebalance_date, row.price_date_used, summary.data_end_date, ''),
      }));

    return {
      factor,
      generatedAt: stringOr(payload?.generated_at, summary.fetched_at, ''),
      dataEndDate: stringOr(summary.data_end_date, payload?.metadata?.data_end_date, ''),
      compositeScore: finiteOrNull(summary.best_composite_score ?? bestRanking.composite_score),
      status: stringOr(summary.static_data_warning, '라이브 공개 JSON 표시 중'),
      rows: rows.slice(0, 5),
      meta: {},
    };
  }


  function parseEtfTracking(payload, summaryPayload, historySources = {}, historyLoadStatus = {}) {
    const meta = isResearchSummary(summaryPayload, 'etf') ? summaryMeta(summaryPayload) : {};
    const entities = summaryEntities(summaryPayload);
    const rows = asRecords(payload?.etfs).map((etf) => {
      const historyPayload = etfHistoryFor(etf, historySources);
      const rawHistory = asRecords(historyPayload?.history).length ? historyPayload.history : etf.history;
      const history = asRecords(rawHistory).map(normalizeEtfSnapshot).filter((snapshot) => snapshot.date).sort((a, b) => a.date.localeCompare(b.date));
      const latest = normalizeEtfSnapshot(etf.latest) || normalizeEtfSnapshot(historyPayload?.latest) || history.at(-1) || {};
      const top10 = latest.top10.slice(0, 10);
      const top = top10[0] || {};
      const metrics = isRecord(etf.metrics) ? etf.metrics : {};
      const latestSignals = asRecords(latest.signals);
      const signalCount = numberOr(metrics.signalCount, latestSignals.length);
      const entryExitCount = numberOr(metrics.entryExitSignalCount, latestSignals.filter((signal) => ['top10_entry', 'top10_exit'].includes(signal.type)).length);
      const top10Weight = top10.reduce((sum, holding) => sum + (finiteOrNull(holding.weight) || 0), 0);
      const chartHistory = history.length ? recentEtfHistory(history, latest.date, ETF_HISTORY_WINDOW_DAYS) : (latest.date ? [latest] : []);
      return {
        id: stringOr(etf.id, etf.code, etf.shortName, etf.name, ''),
        name: stringOr(etf.shortName, etf.name, 'ETF'),
        fullName: stringOr(etf.name, ''),
        code: stringOr(etf.code, ''),
        date: stringOr(latest.date, etf.availableEndDate, ''),
        topName: stringOr(top.name, '-'),
        topTicker: stringOr(top.ticker, top.codeRaw, ''),
        topWeight: finiteOrNull(top.weight),
        top10,
        top10Weight,
        chartSeries: buildEtfWeightSeries(chartHistory, top10),
        signalCount,
        entryExitCount,
        sourceStatus: stringOr(latest.sourceStatus, 'unknown'),
        sourceWarning: stringOr(latest.sourceWarning, ''),
        returnCoverage: finiteOrNull(metrics.returnCoverage ?? latest.analysisSummary?.returnCoverage),
      };
    }).filter((row) => row.name && row.date);

    return {
      generatedAt: stringOr(payload?.generatedAt, meta.generatedAt, ''),
      status: appendEtfHistoryStatus(stringOr(payload?.disclaimer, '라이브 공개 JSON 표시 중'), historyLoadStatus),
      historyWindowDays: ETF_HISTORY_WINDOW_DAYS,
      rows: rows.length ? rows : etfRowsFromSummaryEntities(entities, meta),
      entities,
      meta,
    };
  }

  async function enrichEtfTrackingSources(dataSources, fetchJson) {
    const manifestEtfs = asRecords(dataSources?.etfHistoryManifest?.etfs);
    if (!manifestEtfs.length) return { dataSources, fetchResults: {} };
    const fetchEntries = await Promise.all(manifestEtfs.map(async (item) => {
      const url = resolveEtfHistoryUrl(item.historyUrl);
      const key = stringOr(item.id, item.code, item.shortName, item.name, url);
      if (!url || !key) return [key, { ok: false, error: 'Invalid ETF history URL.', url }];
      return [key, await getEtfHistoryBestEffort(url, item, fetchJson)];
    }));
    const histories = {};
    const extraFetchResults = {};
    for (const [key, result] of fetchEntries) {
      extraFetchResults[`etfHistory:${key}`] = result;
      if (result?.ok) histories[key] = compactEtfHistoryPayload(result.data, ETF_HISTORY_WINDOW_DAYS);
    }
    const requested = fetchEntries.length;
    const loaded = Object.keys(histories).length;
    return {
      dataSources: {
        ...dataSources,
        etfHistories: histories,
        etfHistoryStatus: { requested, loaded, failed: Math.max(requested - loaded, 0) },
      },
      fetchResults: extraFetchResults,
    };
  }


  function etfHistoryEnrichmentFailure(dataSources, errorMessage) {
    const manifestEtfs = asRecords(dataSources?.etfHistoryManifest?.etfs);
    const requested = manifestEtfs.length;
    return {
      dataSources: {
        ...dataSources,
        etfHistories: {},
        etfHistoryStatus: { requested, loaded: 0, failed: requested || 1, error: stringOr(errorMessage, 'ETF history enrichment failed.') },
      },
      fetchResults: {
        etfHistoryEnrichment: { ok: false, error: stringOr(errorMessage, 'ETF history enrichment failed.') },
      },
    };
  }

  async function getEtfHistoryBestEffort(url, manifestItem, fetchJson) {
    const ranged = await getEtfHistoryTailBestEffort(url, manifestItem);
    if (ranged.ok) return ranged;
    return fetchJson(url, 20000);
  }

  async function getEtfHistoryTailBestEffort(url, manifestItem, timeoutMs = 12000) {
    if (typeof fetch !== 'function') return { ok: false, error: 'Fetch API unavailable for ranged ETF history.', url };
    const controller = new AbortController();
    const timerApi = typeof window !== 'undefined' && window.setTimeout ? window : globalThis;
    const timeout = timerApi.setTimeout(() => controller.abort(), timeoutMs);
    try {
      const response = await fetch(url, {
        signal: controller.signal,
        cache: 'no-store',
        headers: { Range: `bytes=-${ETF_HISTORY_TAIL_BYTES}` },
      });
      if (!response.ok && response.status !== 206) throw new Error(`HTTP ${response.status}`);
      const text = await response.text();
      const compact = compactEtfHistoryTailText(text, manifestItem, ETF_HISTORY_WINDOW_DAYS);
      if (!compact || !asRecords(compact.history).length) throw new Error('ETF history tail did not contain recent snapshots.');
      return {
        ok: true,
        data: compact,
        url,
        bytes: textByteLength(text),
        partial: response.status === 206,
      };
    } catch (error) {
      return { ok: false, error: error instanceof Error ? error.message : String(error), url };
    } finally {
      timerApi.clearTimeout(timeout);
    }
  }

  function resolveEtfHistoryUrl(historyUrl) {
    if (!historyUrl) return '';
    try {
      const url = new URL(String(historyUrl), 'https://sonchanggi.github.io/etf-tracking/');
      const validHost = url.protocol === 'https:' && url.hostname === 'sonchanggi.github.io';
      const validPath = /^\/etf-tracking\/data\/history\/[a-z0-9-]+\.json$/i.test(url.pathname);
      return validHost && validPath ? url.href : '';
    } catch {
      return '';
    }
  }

  function compactEtfHistoryPayload(payload, windowDays = 31) {
    const history = dedupeEtfSnapshots(asRecords(payload?.history).map(normalizeEtfSnapshot).filter((snapshot) => snapshot.date));
    const latest = normalizeEtfSnapshot(payload?.latest) || history.at(-1) || null;
    const endDate = stringOr(latest?.date, payload?.availableEndDate, history.at(-1)?.date, '');
    return {
      id: stringOr(payload?.id, ''),
      shortName: stringOr(payload?.shortName, payload?.name, ''),
      code: stringOr(payload?.code, ''),
      name: stringOr(payload?.name, ''),
      latest,
      history: recentEtfHistory(history, endDate, windowDays),
      historyCount: numberOr(payload?.historyCount, history.length),
      availableStartDate: stringOr(payload?.availableStartDate, history[0]?.date, ''),
      availableEndDate: stringOr(payload?.availableEndDate, history.at(-1)?.date, ''),
    };
  }

  function compactEtfHistoryTailText(text, manifestItem = {}, windowDays = 31) {
    try {
      return compactEtfHistoryPayload(JSON.parse(text), windowDays);
    } catch {
      // Ranged ETF history responses intentionally start mid-file; extract complete
      // snapshot objects rather than downloading multi-megabyte replay files.
    }
    const rawSnapshots = extractEtfSnapshotObjects(text);
    if (!rawSnapshots.length) return null;
    const history = dedupeEtfSnapshots(rawSnapshots.map(normalizeEtfSnapshot).filter((snapshot) => snapshot?.date));
    const latest = history.at(-1) || null;
    const endDate = stringOr(latest?.date, manifestItem?.availableEndDate, history.at(-1)?.date, '');
    return {
      id: stringOr(manifestItem?.id, ''),
      shortName: stringOr(manifestItem?.shortName, manifestItem?.name, ''),
      code: stringOr(manifestItem?.code, ''),
      name: stringOr(manifestItem?.name, ''),
      latest,
      history: recentEtfHistory(history, endDate, windowDays),
      historyCount: numberOr(manifestItem?.historyCount, history.length),
      availableStartDate: stringOr(manifestItem?.availableStartDate, history[0]?.date, ''),
      availableEndDate: stringOr(manifestItem?.availableEndDate, history.at(-1)?.date, ''),
    };
  }

  function extractEtfSnapshotObjects(text) {
    const snapshots = [];
    const matcher = /\{"date":"\d{4}-\d{2}-\d{2}"/g;
    let match;
    while ((match = matcher.exec(text))) {
      const lookahead = text.slice(match.index, match.index + 700);
      if (!/"holdings":\[/.test(lookahead)) continue;
      const objectText = extractBalancedJsonObject(text, match.index);
      if (!objectText) continue;
      try {
        const snapshot = JSON.parse(objectText);
        if (asRecords(snapshot.holdings).length || asRecords(snapshot.top10).length) snapshots.push(snapshot);
      } catch {
        // Ignore partial or nested objects from the ranged boundary.
      }
    }
    return snapshots;
  }

  function extractBalancedJsonObject(text, startIndex) {
    let depth = 0;
    let inString = false;
    let escaped = false;
    for (let index = startIndex; index < text.length; index += 1) {
      const char = text[index];
      if (inString) {
        if (escaped) {
          escaped = false;
        } else if (char === '\\') {
          escaped = true;
        } else if (char === '"') {
          inString = false;
        }
        continue;
      }
      if (char === '"') {
        inString = true;
      } else if (char === '{') {
        depth += 1;
      } else if (char === '}') {
        depth -= 1;
        if (depth === 0) return text.slice(startIndex, index + 1);
      }
    }
    return '';
  }

  function dedupeEtfSnapshots(history) {
    const byDate = new Map();
    for (const snapshot of asRecords(history)) {
      if (snapshot.date) byDate.set(snapshot.date, snapshot);
    }
    return [...byDate.values()].sort((a, b) => a.date.localeCompare(b.date));
  }

  function etfHistoryFor(etf, historySources = {}) {
    const keys = [etf?.id, etf?.code, etf?.shortName, etf?.name].map((value) => stringOr(value, ''));
    return keys.map((key) => historySources[key]).find(isRecord) || null;
  }

  function appendEtfHistoryStatus(status, historyLoadStatus = {}) {
    const requested = numberOr(historyLoadStatus?.requested, 0);
    if (!requested) return status;
    const loaded = numberOr(historyLoadStatus?.loaded, 0);
    if (loaded >= requested) return `${status} · 최근 1개월 history ${loaded}/${requested}개 로드`;
    if (loaded > 0) return `${status} · 최근 1개월 history 일부 로드(${loaded}/${requested})`;
    const error = stringOr(historyLoadStatus?.error, '상세 원인 없음');
    return `${status} · 최근 1개월 history 로드 실패(${requested}개 요청 · ${error})`;
  }

  function recentEtfHistory(history, endDate = '', windowDays = 31) {
    const rows = asRecords(history).filter((snapshot) => snapshot.date).sort((a, b) => a.date.localeCompare(b.date));
    if (!rows.length) return [];
    const end = Date.parse(endDate || rows.at(-1)?.date || '');
    if (!Number.isFinite(end)) return rows.slice(-31);
    const cutoff = end - (Math.max(windowDays, 1) - 1) * 24 * 60 * 60 * 1000;
    const recent = rows.filter((snapshot) => {
      const time = Date.parse(snapshot.date);
      return Number.isFinite(time) && time >= cutoff && time <= end;
    });
    return recent.length ? recent : rows.slice(-31);
  }

  function etfRowsFromSummaryEntities(entities, meta = {}) {
    const byEtf = new Map();
    asArray(entities).forEach((entity) => {
      const etfName = stringOr(entity.metrics?.etf, 'ETF');
      if (!byEtf.has(etfName)) {
        byEtf.set(etfName, {
          name: etfName,
          fullName: etfName,
          code: '',
          date: stringOr(entity.metrics?.date, meta.dataAsOf, ''),
          top10: [],
          signalCount: finiteOrNull(meta.coverage?.signalCount) || 0,
          entryExitCount: 0,
          sourceStatus: meta.statusState || 'summary',
          returnCoverage: finiteOrNull(entity.metrics?.returnCoverage),
        });
      }
      const row = byEtf.get(etfName);
      row.top10.push({
        rank: numberOr(entity.metrics?.rank, row.top10.length + 1),
        ticker: entity.symbol,
        codeRaw: entity.symbol,
        name: entity.name,
        weight: finiteOrNull(entity.metrics?.weight),
      });
    });
    return [...byEtf.values()].map((row) => {
      const top = row.top10[0] || {};
      return {
        ...row,
        topName: stringOr(top.name, '-'),
        topTicker: stringOr(top.ticker, top.codeRaw, ''),
        topWeight: finiteOrNull(top.weight),
        top10Weight: row.top10.reduce((sum, holding) => sum + numberOr(holding.weight, 0), 0),
        chartSeries: [],
      };
    });
  }

  function unwrapRegimePayload(document) {
    if (!isRecord(document)) throw new Error('Regime payload must be an object.');
    if (!Object.hasOwn(document, 'schema_version') && !Object.hasOwn(document, 'payload')) return document;
    if (!REGIME_CORE_VERSIONS.has(document.schema_version)) {
      throw new Error(`Unsupported Regime core version: ${document.schema_version || 'missing'}.`);
    }
    const payload = document.payload;
    if (!isRecord(payload) || payload.meta?.result_version !== 'weekly-regime-result-v5') {
      throw new Error('Regime core must contain a v5 payload.');
    }
    if (typeof document.generation_id !== 'string' || !document.generation_id.trim()
      || document.generation_id !== payload.meta.generation_id) {
      throw new Error('Regime core generation does not match its payload.');
    }
    if (typeof document.source_payload_sha256 !== 'string' || !/^[a-f0-9]{64}$/.test(document.source_payload_sha256)) {
      throw new Error('Regime core source payload SHA-256 is missing or invalid.');
    }
    return payload;
  }

  function regimeHistoryDescriptors(core) {
    unwrapRegimePayload(core);
    const descriptors = core.history_sidecars || [];
    if (!Array.isArray(descriptors)) throw new Error('Regime history manifest is invalid.');
    const paths = new Set();
    for (const item of descriptors) {
      if (!isRecord(item) || !/^regime-history-\d{3}\.json$/.test(item.path)
        || paths.has(item.path) || !LOWERCASE_SHA256.test(item.sha256 || '')
        || !Number.isInteger(item.row_count) || item.row_count < 1 || item.row_count > 104) throw new Error('Regime history descriptor is invalid.');
      requireRegimeDate(item.start, 'history.start'); requireRegimeDate(item.end, 'history.end');
      if (item.start > item.end) throw new Error('Regime history range is reversed.');
      paths.add(item.path);
    }
    const firstCurrent = core.payload?.weekly?.[0]?.date;
    if (descriptors.some((item, index) => (index > 0 && item.start <= descriptors[index - 1].end) || (firstCurrent && item.end >= firstCurrent))) throw new Error('Regime history ranges overlap.');
    return descriptors;
  }

  function validateRegimeHistory(history, core, descriptor) {
    if (!isRecord(history) || history.schema_version !== 'regime-dashboard-history/1'
      || history.generation_id !== core.generation_id || history.source_payload_sha256 !== core.source_payload_sha256
      || !Array.isArray(history.weekly) || history.weekly.length !== descriptor.row_count
      || history.weekly[0]?.date !== descriptor.start || history.weekly.at(-1)?.date !== descriptor.end
      || history.weekly.some((row, index) => !isRecord(row) || (index > 0 && row.date <= history.weekly[index - 1].date))) {
      throw new Error('Regime history identity or range mismatch.');
    }
    return history.weekly;
  }

  async function enrichRegimeSources(sources, fetchJson) {
    // Keep the existing summary usable when a separate history file fails.
    parseRegime(sources.summary);
    const core = sources.summary;
    const descriptors = regimeHistoryDescriptors(core);
    const entries = await Promise.all(descriptors.map(async (descriptor) => {
      const url = `https://sonchanggi.github.io/regime/data/${descriptor.path}`;
      const result = await fetchJson(url, 12000, descriptor.sha256);
      if (result.ok) {
        try { validateRegimeHistory(result.data, core, descriptor); }
        catch (error) { return [descriptor.path, { ...result, ok: false, error: error.message }]; }
      }
      return [descriptor.path, result];
    }));
    const failed = entries.find(([, result]) => !result.ok);
    return {
      dataSources: { ...sources, regimeHistory: Object.fromEntries(entries.map(([path, result]) => [path, result.ok ? result.data : null])),
        regimeHistoryError: failed ? `${failed[0]}: ${failed[1].error}` : '' },
      fetchResults: Object.fromEntries(entries),
    };
  }

  function parseRegimePanel(sources) {
    const summary = parseRegime(sources.summary);
    try {
      if (sources.regimeHistoryError) throw new Error(sources.regimeHistoryError);
      return { ...summary, trend: parseRegimeTrend(sources.summary, sources.regimeHistory) };
    } catch (error) {
      return { ...summary, trend: null, trendError: error.message };
    }
  }

  function parseRegimeTrend(core, history = {}) {
    const summary = parseRegime(core), payload = unwrapRegimePayload(core);
    if (['blocked', 'error'].includes(payload.meta.status)) throw new Error('Regime chart unavailable.');
    const descriptors = regimeHistoryDescriptors(core);
    const rows = descriptors.flatMap((item) => validateRegimeHistory(history[item.path], core, item)).concat(payload.weekly);
    const expectedCount = payload.model?.evidence_artifacts?.weekly_state_forecasts?.row_count;
    if (Number.isInteger(expectedCount) && rows.length !== expectedCount) throw new Error('Regime history coverage mismatch.');
    const seen = new Set(), isV5 = payload.meta.result_version === 'weekly-regime-result-v5';
    const parsed = rows.map((row, index) => {
      const date = requireRegimeDate(row.date, `history[${index}].date`);
      if (seen.has(date) || date > summary.dataAsOf) throw new Error('Regime history contains duplicate or future observations.');
      seen.add(date);
      const current = isV5 ? parseRegimeMembership(row.current, `history[${index}].current`) : parseRegimeEstimate(row.current, `history[${index}].current`);
      const forecast = parseRegimeEstimate(row.next_week, `history[${index}].next_week`);
      const nextDate = requireRegimeDate(row.next_week.date, `history[${index}].next_week.date`);
      if (Date.parse(nextDate) - Date.parse(date) !== 7 * 86400000) throw new Error('Regime history forecast horizon is not one week.');
      const entropy = row.next_week.entropy == null ? null : requireRegimeProbability(row.next_week.entropy, 'forecast.entropy');
      return { date, nextDate, currentState: current.state, memberships: current.values || current.probabilities,
        probabilities: forecast.probabilities, nextState: forecast.state, entropy };
    }).sort((a, b) => a.date.localeCompare(b.date));
    if (!parsed.length || parsed.at(-1).date !== summary.dataAsOf) throw new Error('Regime chart endpoint mismatch.');
    const byDate = new Map(parsed.map((row) => [row.date, row]));
    return { currentMeasureLabel: summary.currentMeasureLabel,
      rows: parsed.map((row) => ({ ...row, actualState: byDate.get(row.nextDate)?.currentState || null })) };
  }

  function parseRegime(document) {
    const payload = unwrapRegimePayload(document);
    if (!isRecord(payload)) throw new Error('Regime payload must be an object.');
    const meta = payload.meta;
    if (!isRecord(meta) || !['demo', 'live'].includes(meta.mode)) {
      throw new Error('Regime public payload must declare meta.mode=demo or live.');
    }
    if (!REGIME_RESULT_VERSIONS.has(meta.result_version)) {
      throw new Error(`Unsupported Regime result version: ${meta.result_version || 'missing'}.`);
    }
    const isV5 = meta.result_version === 'weekly-regime-result-v5';

    const sources = payload.sources;
    if (!Array.isArray(sources) || !sources.length || sources.some((source) => !isRecord(source))) {
      throw new Error('Regime public payload must contain sources.');
    }
    if (meta.mode === 'demo') {
      sources.forEach((source, index) => {
        if (typeof source.id !== 'string' || !source.id.startsWith('synthetic_')) {
          throw new Error(`Regime sources[${index}].id is not synthetic.`);
        }
        if (source.license_class !== 'synthetic_fixture') {
          throw new Error(`Regime sources[${index}].license_class is not synthetic_fixture.`);
        }
      });
    } else {
      const expectedLicenses = isV5 ? REGIME_V5_LIVE_SOURCE_LICENSES : REGIME_LIVE_SOURCE_LICENSES;
      const liveSources = new Map(sources.map((source) => [source.id, source]));
      if (liveSources.size !== sources.length
        || liveSources.size !== Object.keys(expectedLicenses).length) {
        throw new Error('Regime live-derived payload must contain the exact provider source set.');
      }
      Object.entries(expectedLicenses).forEach(([sourceId, expectedLicense]) => {
        if (liveSources.get(sourceId)?.license_class !== expectedLicense) {
          throw new Error(`Regime live source ${sourceId} has an invalid license_class.`);
        }
      });
    }

    if (!Array.isArray(payload.weekly) || !payload.weekly.length || payload.weekly.some((row) => !isRecord(row))) {
      throw new Error('Regime weekly results are missing.');
    }
    const datedWeeks = payload.weekly.map((row, index) => ({
      row,
      date: requireRegimeDate(row.date, `weekly[${index}].date`),
    })).sort((left, right) => left.date.localeCompare(right.date));
    const { row: latest, date } = datedWeeks.at(-1);
    const generatedAt = stringOr(meta.generated_at, '');
    if (!generatedAt || !Number.isFinite(Date.parse(generatedAt))) {
      throw new Error('Regime meta.generated_at is missing or invalid.');
    }
    const declaredDataAsOf = requireRegimeDatePrefix(meta.data_as_of, 'meta.data_as_of');
    if (declaredDataAsOf !== date) {
      throw new Error('Regime meta.data_as_of does not match the latest observation week.');
    }

    const current = isV5
      ? parseRegimeMembership(latest.current, 'weekly.latest.current')
      : parseRegimeEstimate(latest.current, 'weekly.latest.current');
    const nextWeek = parseRegimeEstimate(latest.next_week, 'weekly.latest.next_week');
    const nextDate = requireRegimeDate(latest.next_week?.date, 'weekly.latest.next_week.date');
    const horizonDate = (weeks) => new Date(Date.parse(`${date}T00:00:00Z`) + weeks * 7 * 86_400_000).toISOString().slice(0, 10);
    if (nextDate !== horizonDate(1)) throw new Error('Regime next-week date must be one week after the observation week.');

    const transitionRisk = {};
    for (const horizon of [1, 4, 13]) {
      const key = `${horizon}w`;
      const item = latest.transition_risk?.[key];
      if (!isRecord(item)) throw new Error(`Regime transition_risk.${key} is missing.`);
      transitionRisk[key] = {
        probability: requireRegimeProbability(item.probability, `transition_risk.${key}.probability`),
        targetEnd: requireRegimeDate(item.target_end, `transition_risk.${key}.target_end`),
      };
      if (transitionRisk[key].targetEnd !== horizonDate(horizon)) {
        throw new Error(`Regime ${key} transition target does not match its observation horizon.`);
      }
    }
    if (transitionRisk['1w'].targetEnd !== nextDate) {
      throw new Error('Regime 1w transition target does not match the next-week date.');
    }
    if (!(transitionRisk['1w'].probability <= transitionRisk['4w'].probability + 1e-8
      && transitionRisk['4w'].probability <= transitionRisk['13w'].probability + 1e-8)) {
      throw new Error('Regime transition risks must be monotone across 1w, 4w, and 13w.');
    }

    const transitionProbability = requireRegimeProbability(latest.transition_probability, 'transition_probability');
    const canonicalTransition = 1 - nextWeek.probabilities[current.state];
    if (Math.abs(transitionProbability - canonicalTransition) > 1e-6
      || Math.abs(transitionProbability - transitionRisk['1w'].probability) > 1e-6) {
      throw new Error('Regime 1w transition probability is internally inconsistent.');
    }

    const isLive = meta.mode === 'live';
    const liveStatus = ['ok', 'degraded', 'stale', 'blocked', 'error'].includes(meta.status)
      ? meta.status
      : 'degraded';
    const statusState = isLive ? liveStatus : 'demo';
    const statusLabel = isLive
      ? (liveStatus === 'ok' ? '정상' : '주의')
      : '합성 데모';
    const summary = {
      publicPayloadValid: true,
      generatedAt,
      dataAsOf: date,
      nextDate,
      resultVersion: meta.result_version,
      currentState: current.state,
      currentStateLabel: REGIME_STATE_LABELS[current.state],
      currentConfidence: current.confidence,
      currentMeasureLabel: isV5 ? '소속도' : '확률',
      nextState: nextWeek.state,
      nextStateLabel: REGIME_STATE_LABELS[nextWeek.state],
      nextConfidence: nextWeek.confidence,
      transitionRisk1w: transitionRisk['1w'].probability,
      transitionRisk4w: transitionRisk['4w'].probability,
      transitionRisk13w: transitionRisk['13w'].probability,
      status: statusLabel,
      rows: [],
      entities: [],
      meta: {
        statusState,
        statusLabel,
        dataModeLabel: isLive ? 'Live 파생 결과' : '합성 데모',
        dataAsOf: date,
        cadence: 'weekly',
        expectedFreshnessDays: PROJECT_EXPECTED_FRESHNESS_DAYS.regime,
        limitations: [],
        sourceCount: sources.length,
      },
    };
    summary.entities = [{
      id: 'us-market-regime',
      symbol: 'US Market',
      name: '미국 증시 국면',
      label: `미국 증시 · ${summary.currentStateLabel}`,
      sector: 'United States',
      sectorLabel: 'United States',
      themes: ['Regime', '미국 증시'],
      metrics: { ...summary },
      signals: [`현재 ${summary.currentStateLabel}`, `다음 주 ${summary.nextStateLabel}`],
      warnings: [],
      status: statusState,
    }];
    return summary;
  }

  function parseRegimeEstimate(value, context) {
    const result = parseRegimeDistribution(value, context, 'probabilities', 'confidence');
    return { state: result.state, probabilities: result.values, confidence: result.confidence };
  }

  function parseRegimeMembership(value, context) {
    if (!isRecord(value) || value.method !== 'risk_score_anchor_membership') {
      throw new Error(`${context} must declare risk_score_anchor_membership.`);
    }
    // The observed hysteresis state is authoritative, even when another membership is larger.
    return parseRegimeDistribution(value, context, 'memberships', 'primary_membership', false);
  }

  function parseRegimeDistribution(value, context, valuesKey, confidenceKey, requireDominantState = true) {
    if (!isRecord(value) || !isRecord(value[valuesKey])) {
      throw new Error(`${context} is missing ${valuesKey}.`);
    }
    const keys = Object.keys(value[valuesKey]);
    if (keys.length !== REGIME_STATES.length || REGIME_STATES.some((state) => !keys.includes(state))) {
      throw new Error(`${context} must contain the exact three Regime ${valuesKey} keys.`);
    }
    const values = Object.fromEntries(REGIME_STATES.map((state) => [
      state,
      requireRegimeProbability(value[valuesKey][state], `${context}.${valuesKey}.${state}`),
    ]));
    const total = Object.values(values).reduce((sum, probability) => sum + probability, 0);
    if (Math.abs(total - 1) > 1e-6) throw new Error(`${context} ${valuesKey} must sum to one.`);
    const state = value.state;
    if (!REGIME_STATES.includes(state)) throw new Error(`${context}.state is invalid.`);
    const confidence = requireRegimeProbability(value[confidenceKey], `${context}.${confidenceKey}`);
    const winningValue = Math.max(...Object.values(values));
    if (Math.abs(confidence - values[state]) > 1e-6
      || (requireDominantState && Math.abs(values[state] - winningValue) > 1e-6)) {
      throw new Error(`${context} state and ${confidenceKey} do not match its ${valuesKey}.`);
    }
    return { state, values, confidence };
  }

  function requireRegimeProbability(value, context) {
    if (typeof value !== 'number' || !Number.isFinite(value) || value < 0 || value > 1) {
      throw new Error(`${context} must be a finite probability.`);
    }
    return value;
  }

  function requireRegimeDate(value, context) {
    const parsed = typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)
      ? new Date(`${value}T00:00:00Z`)
      : null;
    if (!parsed || Number.isNaN(parsed.getTime()) || parsed.toISOString().slice(0, 10) !== value) {
      throw new Error(`${context} must be an ISO date.`);
    }
    return value;
  }

  function requireRegimeDatePrefix(value, context) {
    if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}/.test(value) || !Number.isFinite(Date.parse(value))) {
      throw new Error(`${context} must contain an ISO date.`);
    }
    return requireRegimeDate(value.slice(0, 10), context);
  }

  function parseFearPanel(sources) {
    const summary = parseFearAndGreed(sources.summary);
    if (summary.unavailable) return summary;
    let scatter;
    try {
      scatter = parseFearScatter(sources.dashboard, sources.summary);
    } catch (error) {
      return { ...summary, scatter: null, scatterError: error.message };
    }
    try {
      return { ...summary, scatter: { ...scatter, pricePoints: parseFearPrices(sources.history, sources.summary, scatter) } };
    } catch (error) {
      return { ...summary, scatter, priceError: error.message };
    }
  }

  function parseFearPrices(payload, summary, scatter) {
    const fail = (message) => { throw new Error(`Fear & Greed price: ${message}`); };
    const finite = (value) => typeof value === 'number' && Number.isFinite(value);
    if (!isRecord(payload) || payload.schemaVersion !== 1 || payload.fixture !== false
      || payload.methodologyVersion !== summary.methodologyVersion || payload.generatedAt !== summary.generatedAt
      || payload.dataAsOf !== summary.dataAsOf) fail('publication mismatch');
    const columns = payload.seriesColumns, rows = payload.seriesRows;
    const required = ['date', 'kospiClose', 'return1d', 'rawFlowTrillion'];
    if (payload.seriesEncoding !== 'columnar-v1' || payload.numericPrecisionDigits !== 8
      || !Array.isArray(columns) || new Set(columns).size !== columns.length
      || !required.every((key) => columns.includes(key)) || !Array.isArray(rows) || !rows.length) fail('history contract');
    const [dateIndex, closeIndex, returnIndex, flowIndex] = required.map((key) => columns.indexOf(key));
    const byDate = new Map();
    rows.forEach((row, index) => {
      const date = row?.[dateIndex];
      if (!Array.isArray(row) || row.length !== columns.length || typeof date !== 'string'
        || !/^\d{4}-\d{2}-\d{2}$/.test(date) || !Number.isFinite(Date.parse(date))
        || new Date(date).toISOString().slice(0, 10) !== date
        || (index && date <= rows[index - 1][dateIndex])) fail('invalid history dates');
      byDate.set(date, { row, previous: rows[index - 1] });
    });
    if (rows.at(-1)[dateIndex] !== summary.dataAsOf) fail('latest history date');
    return scatter.points.map((point) => {
      const match = byDate.get(point.date), row = match?.row, close = row?.[closeIndex];
      if (!finite(close) || close <= 0 || !finite(row[returnIndex]) || !finite(row[flowIndex])
        || Math.abs(row[returnIndex] - point.return1d) > 1e-8
        || Math.abs(row[flowIndex] - point.rawFlowTrillion) > 1e-8) fail('price observation mismatch');
      const previousClose = match.previous?.[closeIndex];
      if (!finite(previousClose) || previousClose <= 0
        || Math.abs(close / previousClose - 1 - point.return1d) > 1e-8) fail('close return mismatch');
      return { ...point, close };
    });
  }

  // Historical rolling states do not describe the current scatter's fitted regions.
  function fearPointState(scatter, row) {
    if (!scatter.boundaries) return null;
    let residual = row.rawFlowTrillion - scatter.alpha - scatter.beta * row.return1d;
    const b = scatter.boundaries;
    const boundary = Object.values(b).find((value) => Math.abs(residual - value) <= 5e-8);
    if (boundary !== undefined) residual = boundary;
    if (residual < b.extremeFearUpper) return 'extreme_fear';
    if (residual < b.fearUpper) return 'fear';
    if (residual < b.greedLower) return 'neutral';
    if (residual < b.extremeGreedLower) return 'greed';
    return 'extreme_greed';
  }

  const FEAR_POINT_LABELS = Object.freeze({ extreme_fear: '극단 공포', fear: '공포', neutral: '중립', greed: '탐욕', extreme_greed: '극단 탐욕' });

  function parseFearScatter(payload, summary) {
    const fail = (message) => { throw new Error(`Fear & Greed scatter: ${message}`); };
    const finite = (value) => typeof value === 'number' && Number.isFinite(value);
    const dateValid = (value) => typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)
      && Number.isFinite(Date.parse(value)) && new Date(value).toISOString().slice(0, 10) === value;
    if (!isRecord(payload) || payload.schemaVersion !== 1 || !isResearchSummary(summary, 'fearngreed')
      || !dateValid(payload.dataAsOf) || !Number.isFinite(Date.parse(payload.generatedAt))
      || !payload.methodologyVersion || payload.methodologyVersion !== summary.methodologyVersion
      || payload.dataAsOf !== summary.dataAsOf || payload.generatedAt !== summary.generatedAt
      || payload.status?.state !== summary.status?.state) fail('publication mismatch');
    if (!['ok', 'degraded', 'stale'].includes(payload.status?.state)) fail('unavailable');
    const meta = payload.scatterMetaByModel?.raw;
    const points = payload.scatterByModel?.raw;
    const fit = payload.regression?.raw;
    const model = payload.models?.raw;
    if (meta?.model !== 'raw' || meta.unit !== 'krw_trillion'
      || meta.roles?.training !== 'rolling_window' || meta.roles?.current !== 'out_of_sample_observation'
      || !Number.isInteger(meta.window) || meta.window < 8 || !Array.isArray(points)
      || fit?.model !== 'raw' || fit.fitMethod !== 'ols' || model?.model !== 'raw' || model.fitMethod !== 'ols'
      || model.state === 'unavailable' || !['alpha', 'beta', 'expected', 'observed', 'residual'].every((key) => finite(fit[key]) && finite(model[key]) && Math.abs(fit[key] - model[key]) < 5e-8)) fail('raw model contract');
    if (points.some((row, index) => !dateValid(row?.date) || !finite(row.return1d) || !finite(row.rawFlowTrillion)
      || !['training', 'current'].includes(row.role) || (index > 0 && row.date <= points[index - 1].date))) fail('invalid observations');
    const training = points.filter((row) => row.role === 'training');
    const currentRows = points.filter((row) => row.role === 'current');
    if (currentRows.length !== 1 || training.length < 8 || training.length > meta.window
      || meta.trainingCount !== training.length || meta.currentCount !== 1 || meta.pointCount !== points.length
      || fit.trainingCount !== training.length || model.trainingCount !== training.length) fail('observation counts');
    const current = currentRows[0];
    if (current !== points.at(-1) || current.date !== payload.dataAsOf
      || training.some((row) => row.date >= current.date)) fail('current observation date');
    const expected = fit.alpha + fit.beta * current.return1d;
    if (Math.abs(current.rawFlowTrillion - fit.observed) > 5e-8 || Math.abs(expected - fit.expected) > 5e-8
      || Math.abs(current.rawFlowTrillion - expected - fit.residual) > 5e-8) fail('current fit mismatch');
    let boundaries = null;
    if (meta.stateBoundaries) {
      const bounds = meta.stateBoundaries;
      const keys = ['extremeFearUpper', 'fearUpper', 'greedLower', 'extremeGreedLower'];
      const comparisons = {
        extremeFear: 'residual < extremeFearUpper', fear: 'extremeFearUpper <= residual < fearUpper',
        neutral: 'fearUpper <= residual < greedLower', greed: 'greedLower <= residual < extremeGreedLower',
        extremeGreed: 'residual >= extremeGreedLower',
      };
      if (Object.entries(comparisons).some(([key, value]) => bounds.comparators?.[key] !== value)) fail('boundary comparator mismatch');
      const cuts = keys.map((key) => bounds.percentileCuts?.[key]);
      const offsets = keys.map((key) => bounds.residualOffsets?.[key]);
      if (bounds.method !== 'empirical_cdf_transition_order_statistic' || bounds.fitScope !== 'current_fit_on_prior_window'
        || bounds.trainingCount !== training.length || training.length < 20
        || cuts.join(',') !== '5,20,80,95' || offsets.some((value, index) => !finite(value) || (index && value < offsets[index - 1]))) fail('residual boundary contract');
      const residuals = training.map((row) => row.rawFlowTrillion - fit.alpha - fit.beta * row.return1d).sort((a, b) => a - b);
      const indices = [Math.floor(.05 * training.length), Math.floor(.2 * training.length), Math.ceil(.8 * training.length) - 1, Math.ceil(.95 * training.length) - 1];
      if (offsets.some((value, index) => Math.abs(value - residuals[indices[index]]) > 5e-8)) fail('residual boundary mismatch');
      boundaries = { ...bounds.residualOffsets };
    }
    return { date: payload.dataAsOf, generatedAt: payload.generatedAt, points, current, trainingCount: training.length,
      alpha: fit.alpha, beta: fit.beta, boundaries, state: model.state, percentile: model.percentile };
  }

  function formatSignedFear(value, digits) {
    return `${value > 0 ? '+' : ''}${value.toLocaleString('ko-KR', { minimumFractionDigits: digits, maximumFractionDigits: digits })}`;
  }

  function fearScatterGeometry(scatter, width = 640) {
    const w = Math.max(300, width), h = width < 430 ? 300 : 285;
    const p = { l: 48, r: 18, t: 28, b: 45 };
    const xs = scatter.points.map((row) => row.return1d * 100);
    const xlow = Math.min(0, ...xs), xhigh = Math.max(0, ...xs);
    const xpad = Math.max(xhigh - xlow, .1) * .08;
    const xmin = xlow - xpad, xmax = xhigh + xpad;
    const predicted = (x) => scatter.alpha + scatter.beta * x / 100;
    const offsets = scatter.boundaries ? Object.values(scatter.boundaries) : [];
    const ys = [0, ...scatter.points.map((row) => row.rawFlowTrillion), predicted(xmin), predicted(xmax),
      ...offsets.flatMap((offset) => [predicted(xmin) + offset, predicted(xmax) + offset])];
    const ylow = Math.min(...ys), yhigh = Math.max(...ys), ypad = Math.max(yhigh - ylow, .1) * .06;
    const ymin = ylow - ypad, ymax = yhigh + ypad;
    const x = (value) => p.l + (value - xmin) / (xmax - xmin) * (w - p.l - p.r);
    const y = (value) => h - p.b - (value - ymin) / (ymax - ymin) * (h - p.t - p.b);
    const ticks = (min, max, count) => {
      const step = niceStep((max - min) / (count - 1), .01), result = [];
      for (let value = Math.ceil(min / step) * step; value <= max + step * .0001; value += step) result.push(roundTick(value));
      return result;
    };
    return { w, h, p, xmin, xmax, ymin, ymax, x, y, predicted,
      xTicks: ticks(xmin, xmax, 6), yTicks: ticks(ymin, ymax, 6),
      points: scatter.points.map((row) => ({ row, x: x(row.return1d * 100), y: y(row.rawFlowTrillion) })) };
  }

  function fearPriceGeometry(points, width = 640) {
    const w = Math.max(300, width), h = 190, p = { l: 48, r: 18, t: 12, b: 30 };
    const closes = points.map((row) => row.close);
    const low = Math.min(...closes), high = Math.max(...closes), pad = Math.max(high - low, high * .01) * .12;
    const ymin = low - pad, ymax = high + pad;
    const first = Date.parse(points[0].date), last = Date.parse(points.at(-1).date);
    const x = (date) => p.l + (Date.parse(date) - first) / Math.max(1, last - first) * (w - p.l - p.r);
    const y = (close) => h - p.b - (close - ymin) / (ymax - ymin) * (h - p.t - p.b);
    const step = niceStep((ymax - ymin) / 4, 1), yTicks = [];
    for (let value = Math.ceil(ymin / step) * step; value <= ymax; value += step) yTicks.push(roundTick(value));
    const tickCount = w < 430 ? 3 : 4;
    const dateTicks = Array.from({ length: tickCount }, (_, index) => points[Math.round(index * (points.length - 1) / (tickCount - 1))].date);
    return { w, h, p, x, y, yTicks, dateTicks, points: points.map((row) => ({ row, x: x(row.date), y: y(row.close) })) };
  }

  let fearScatterObserver;
  function renderFearScatter(scatter, project) {
    const target = $(panelSelector(project, 'chart'));
    if (!target) return;
    fearScatterObserver?.disconnect();
    if (!scatter) {
      target.innerHTML = '<p class="empty-state">차트 데이터를 불러올 수 없습니다.</p>';
      return;
    }
    let selected = scatter.points.length - 1, pinned = selected, previousWidth = 0;
    const states = scatter.points.map((row) => fearPointState(scatter, row));
    const draw = () => {
      const width = Math.max(300, Math.round(target.clientWidth || 640));
      if (width === previousWidth) return;
      previousWidth = width;
      const g = fearScatterGeometry(scatter, width), { w, h, p, x, y, predicted } = g;
      const price = scatter.pricePoints ? fearPriceGeometry(scatter.pricePoints, width) : null;
      const right = w - p.r, bottom = h - p.b;
      const line = (x1, y1, x2, y2, cls) => `<line class="${cls}" x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"/>`;
      const grid = g.xTicks.map((value) => `${line(x(value), p.t, x(value), bottom, 'scatter-grid')}<text x="${x(value)}" y="${bottom + 20}" text-anchor="middle">${value}</text>`).join('')
        + g.yTicks.map((value) => `${line(p.l, y(value), right, y(value), 'scatter-grid')}<text x="${p.l - 8}" y="${y(value) + 4}" text-anchor="end">${value}</text>`).join('');
      const band = (lower, upper, cls) => `<polygon class="${cls}" points="${p.l},${lower[0]} ${right},${lower[1]} ${right},${upper[1]} ${p.l},${upper[0]}"/>`;
      const boundaryY = (offset) => [y(predicted(g.xmin) + offset), y(predicted(g.xmax) + offset)];
      let zones = '';
      if (scatter.boundaries) {
        const b = scatter.boundaries, ef = boundaryY(b.extremeFearUpper), f = boundaryY(b.fearUpper), gr = boundaryY(b.greedLower), eg = boundaryY(b.extremeGreedLower);
        zones = band([bottom, bottom], ef, 'scatter-fear-extreme') + band(ef, f, 'scatter-fear')
          + band(gr, eg, 'scatter-greed') + band(eg, [p.t, p.t], 'scatter-greed-extreme');
      }
      const mark = ({ row, x: cx, y: cy }, index, chart) => {
        const state = states[index], current = row.role === 'current';
        const r = current ? 5 : state?.startsWith('extreme') ? 4 : chart === 'price' && (!state || state === 'neutral') ? 1.4 : 3;
        const attrs = `data-point="${index}" data-date="${row.date}" data-state="${state || 'unclassified'}" class="${chart}-observation fear-point ${state || ''}${current ? ' is-current' : ''}"`;
        const title = `<title>${escapeHtml(`${row.date} · ${FEAR_POINT_LABELS[state] || ''}${chart === 'price' ? ` · KOSPI ${row.close.toLocaleString('ko-KR', { maximumFractionDigits: 2 })}` : ` · 수익률 ${formatSignedFear(row.return1d * 100, 2)}% · 개인 ${formatSignedFear(row.rawFlowTrillion, 3)}조원`}`)}</title>`;
        return state?.includes('greed')
          ? `<path ${attrs} d="M${cx},${cy - r - 1}L${cx + r + 1},${cy}L${cx},${cy + r + 1}L${cx - r - 1},${cy}Z">${title}</path>`
          : `<circle ${attrs} cx="${cx}" cy="${cy}" r="${r}">${title}</circle>`;
      };
      const marks = g.points.map((point, index) => mark(point, index, 'scatter')).join('');
      const current = g.points.at(-1);
      const currentLabelX = current.x > w / 2 ? current.x - 11 : current.x + 11;
      const zoneLegend = scatter.boundaries ? '<div class="scatter-zones" aria-label="현재 회귀 기준 잔차 백분위 구간"><span class="fear-extreme">극단 공포 ≤5%</span><span class="fear">공포 5–20%</span><span>중립</span><span class="greed">탐욕 80–95%</span><span class="greed-extreme">극단 탐욕 ≥95%</span><small>현재 회귀 기준</small></div>' : '';
      const priceChart = price ? `<div class="fear-price-heading"><h4>가격 · KOSPI 종가</h4><span>지수포인트</span></div>
        <div class="scatter-frame fear-price-frame" tabindex="0" role="group" aria-label="KOSPI 종가와 공포·탐욕. 좌우 방향키로 두 그래프의 날짜 이동" aria-describedby="fear-scatter-readout">
          <svg viewBox="0 0 ${price.w} ${price.h}" role="img" aria-label="KOSPI 종가, 산점도와 같은 ${price.points.length}개 날짜">
            ${price.yTicks.map((value) => `${line(price.p.l, price.y(value), w - price.p.r, price.y(value), 'scatter-grid')}<text x="${price.p.l - 8}" y="${price.y(value) + 4}" text-anchor="end">${value.toLocaleString('ko-KR')}</text>`).join('')}
            ${price.dateTicks.map((date, index) => `<text x="${price.x(date)}" y="${price.h - 7}" text-anchor="${index === 0 ? 'start' : index === price.dateTicks.length - 1 ? 'end' : 'middle'}">${date.slice(0, 7).replace('-', '.')}</text>`).join('')}
            <path class="fear-price-line" d="${price.points.map((point, index) => `${index ? 'L' : 'M'}${point.x},${point.y}`).join('')}"/>
            ${price.points.map((point, index) => mark(point, index, 'price')).join('')}
            <line class="fear-price-cursor" y1="${price.p.t}" y2="${price.h - price.p.b}"/>
            <circle class="price-selected" r="7"/>
          </svg>
        </div>` : '<p class="empty-state fear-price-empty">KOSPI 종가 데이터를 불러올 수 없습니다.</p>';
      target.innerHTML = `<figure class="fear-scatter">
        <div class="scatter-legend"><span class="past">직전 ${scatter.trainingCount}거래일</span><span class="current">현재</span><span class="fit">OLS 회귀선</span></div>
        <div class="scatter-frame fear-scatter-frame" tabindex="0" role="group" aria-label="KOSPI 수익률과 개인 순매수 산점도. 좌우 방향키로 두 그래프의 날짜 이동" aria-describedby="fear-scatter-readout">
          <svg viewBox="0 0 ${w} ${h}" role="img" aria-label="KOSPI 1일 수익률 퍼센트와 개인 순매수대금 조원, ${scatter.points.length}개 관측점">
            <defs><clipPath id="fear-scatter-clip"><rect x="${p.l}" y="${p.t}" width="${right - p.l}" height="${bottom - p.t}"/></clipPath></defs>
            <g clip-path="url(#fear-scatter-clip)">${zones}</g>${grid}
            ${line(x(0), p.t, x(0), bottom, 'scatter-zero')}${line(p.l, y(0), right, y(0), 'scatter-zero')}
            <g clip-path="url(#fear-scatter-clip)">${line(p.l, y(predicted(g.xmin)), right, y(predicted(g.xmax)), 'scatter-fit')}${marks}
              <circle class="scatter-selected" r="8"/>
            </g>
            <text class="scatter-current-label" x="${currentLabelX}" y="${Math.max(p.t + 16, current.y - 13)}" text-anchor="${current.x > w / 2 ? 'end' : 'start'}">현재</text>
            <text class="scatter-axis-title" x="${p.l}" y="16">개인 순매수대금 (조원)</text>
            <text class="scatter-axis-title" x="${(p.l + right) / 2}" y="${h - 4}" text-anchor="middle">KOSPI 1일 수익률 (%)</text>
          </svg>
        </div>${zoneLegend}${priceChart}
        <figcaption class="scatter-readout" id="fear-scatter-readout" aria-live="polite"></figcaption>
      </figure>`;
      const readout = target.querySelector('.scatter-readout'), ring = target.querySelector('.scatter-selected');
      const priceRing = target.querySelector('.price-selected'), cursor = target.querySelector('.fear-price-cursor');
      const select = (index) => {
        selected = index;
        const point = g.points[index], row = point.row, state = states[index];
        ring.setAttribute('cx', point.x); ring.setAttribute('cy', point.y); ring.dataset.date = row.date;
        if (priceRing) {
          const match = price.points[index];
          priceRing.setAttribute('cx', match.x); priceRing.setAttribute('cy', match.y); priceRing.dataset.date = row.date;
          cursor.setAttribute('x1', match.x); cursor.setAttribute('x2', match.x);
        }
        const close = price?.points[index].row.close;
        readout.innerHTML = `<strong>${escapeHtml(row.date)}${row.role === 'current' ? ' · 현재' : ''}${state ? ` <em class="fear-state ${state}">${FEAR_POINT_LABELS[state]}</em>` : ''}</strong>${close !== undefined ? `<span>KOSPI <b>${close.toLocaleString('ko-KR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</b></span>` : ''}<span>수익률 <b>${escapeHtml(formatSignedFear(row.return1d * 100, 2))}%</b></span><span>개인 <b>${escapeHtml(formatSignedFear(row.rawFlowTrillion, 3))}조원</b></span>`;
      };
      const bind = (selector, geometry, isPrice) => {
        const frame = target.querySelector(selector);
        if (!frame) return;
        const svg = frame.querySelector('svg');
        const nearest = (event) => {
          const rect = svg.getBoundingClientRect(), px = (event.clientX - rect.left) * geometry.w / rect.width, py = (event.clientY - rect.top) * geometry.h / rect.height;
          if (px < geometry.p.l || px > geometry.w - geometry.p.r || py < geometry.p.t || py > geometry.h - geometry.p.b) return null;
          const hit = event.target.closest?.('[data-point]');
          if (hit) return Number(hit.dataset.point);
          let best = 0, distance = Infinity;
          geometry.points.forEach((point, index) => { const d = (px - point.x) ** 2 + (isPrice ? 0 : (py - point.y) ** 2); if (d < distance) { best = index; distance = d; } });
          return best;
        };
        svg.addEventListener('pointermove', (event) => { const index = nearest(event); if (event.pointerType !== 'touch' && index !== null) select(index); });
        svg.addEventListener('click', (event) => { const index = nearest(event); if (index !== null) { pinned = index; select(index); } });
        frame.addEventListener('pointerleave', () => select(pinned));
        frame.addEventListener('keydown', (event) => {
          const move = { ArrowLeft: Math.max(0, selected - 1), ArrowRight: Math.min(g.points.length - 1, selected + 1), Home: 0, End: g.points.length - 1, Escape: g.points.length - 1 };
          if (Object.hasOwn(move, event.key)) { event.preventDefault(); pinned = move[event.key]; select(pinned); }
        });
      };
      bind('.fear-scatter-frame', g, false);
      if (price) bind('.fear-price-frame', price, true);
      select(selected);
    };
    draw();
    if (typeof ResizeObserver !== 'undefined') { fearScatterObserver = new ResizeObserver(draw); fearScatterObserver.observe(target); }
  }

  function parseFearAndGreed(payload) {
    if (!isResearchSummary(payload, 'fearngreed')) return normalizeFearAndGreedUnavailable();
    const meta = summaryMeta(payload);
    const source = asRecords(payload.primaryEntities)[0];
    if (!source) return normalizeFearAndGreedUnavailable();
    const current = {
      id: stringOr(source.id, 'KOSPI'),
      name: stringOr(source.name, source.id, 'KOSPI'),
      signalState: stringOr(source.signalState, 'unavailable'),
      stateLabel: stringOr(payload.status?.label, source.signalState, '산출 불가'),
      sentimentPercentile: finiteOrNull(source.sentimentPercentile),
      residualZ: finiteOrNull(source.residualZ),
      rollingR2: finiteOrNull(source.rollingR2),
      return1d: finiteOrNull(source.return1d),
      flowShare: finiteOrNull(source.flowShare),
      disparity50: finiteOrNull(source.disparity50),
      position: stringOr(source.position, 'unavailable'),
      primaryProxy: stringOr(source.primaryProxy, '226490'),
      modelQuality: stringOr(source.modelQuality, 'unavailable'),
      modelConfidence: stringOr(source.modelConfidence, 'unavailable'),
      date: meta.dataAsOf,
    };
    const warnings = [
      ...meta.degradedReasons,
      ...asArray(meta.limitations),
    ].filter(Boolean);
    const entity = {
      id: current.id,
      symbol: 'KOSPI',
      name: current.name,
      label: current.name,
      sector: 'Korea',
      sectorLabel: 'Korea',
      themes: asArray(source.themes).length ? asArray(source.themes).map(String) : ['Sentiment', 'Flow'],
      metrics: { ...current },
      signals: [`연구 상태 ${current.stateLabel}`, `포지션 ${current.position}`],
      warnings,
      status: current.signalState,
    };
    return {
      generatedAt: meta.generatedAt,
      dataAsOf: meta.dataAsOf,
      status: stringOr(meta.statusLabel, current.stateLabel),
      current,
      rows: [current],
      entities: [entity],
      entityPresent: true,
      meta: {
        ...meta,
        statusState: stringOr(meta.statusState, 'unavailable'),
        statusLabel: stringOr(meta.statusLabel, current.stateLabel),
        expectedFreshnessDays: finiteOrNull(meta.expectedFreshnessDays),
      },
    };
  }

  function parseSoxPanel(sources) {
    const summary = parseSox(sources.summary);
    try {
      return { ...summary, quadrant: parseSoxQuadrant(sources.summary, sources.soxAnalysis) };
    } catch (error) {
      return { ...summary, quadrant: null, quadrantError: error.message };
    }
  }

  function parseSoxQuadrant(summary, analysis) {
    const fail = (message) => { throw new Error(`SOX quadrant: ${message}`); };
    if (!isResearchSummary(summary, 'sox') || summary.schemaVersion !== 1
      || !isRecord(analysis) || analysis.schemaVersion !== 1 || analysis.projectId !== 'sox'
      || analysis.index?.symbol !== 'SOX') fail('invalid source contract');
    if (!/^\d{4}-\d{2}-\d{2}$/.test(summary.dataAsOf || '') || !Number.isFinite(Date.parse(summary.generatedAt))
      || analysis.dataAsOf !== summary.dataAsOf || analysis.generatedAt !== summary.generatedAt
      || !['ok', 'degraded'].includes(analysis.status?.level) || analysis.status.level !== summary.status?.state) fail('publication mismatch');
    const count = summary.coverage?.entityCount, rawRows = analysis.constituents;
    if (!Number.isInteger(count) || count < 1 || !Array.isArray(rawRows) || rawRows.length !== count
      || analysis.index.constituentCount !== count) fail('constituent coverage mismatch');
    const tickers = new Set(), ranks = new Set();
    const optionalScore = (value) => {
      if (value === null) return null;
      if (soxScore(value) === null) fail('invalid score or weight');
      return value;
    };
    const rows = rawRows.map((row) => {
      if (!isRecord(row) || !/^[A-Z0-9.^-]{1,20}$/.test(row.ticker || '') || tickers.has(row.ticker)
        || !Number.isInteger(row.rank) || row.rank < 1 || row.rank > count || ranks.has(row.rank) || !isRecord(row.scores)) fail('invalid or duplicate constituent');
      tickers.add(row.ticker); ranks.add(row.rank);
      return { rank: row.rank, ticker: row.ticker, name: stringOr(row.name, row.ticker),
        priceMomentum: optionalScore(row.scores.priceMomentum), earningsMomentum: optionalScore(row.scores.earningsMomentum),
        score: optionalScore(row.scores.combined), weight: optionalScore(row.proxyWeight), status: stringOr(row.scores.label, ''),
      };
    }).sort((a, b) => a.rank - b.rank);
    const leaders = asRecords(summary.primaryEntities);
    if (leaders.length !== Math.min(5, count)) fail('leader coverage mismatch');
    for (const entity of leaders) {
      const row = rows.find((item) => item.ticker === entity.symbol), metrics = entity.metrics;
      if (!row || !isRecord(metrics) || row.rank !== metrics.rank || row.rank > Math.min(5, count)
        || row.score !== metrics.score || row.priceMomentum !== metrics.priceMomentum
        || row.earningsMomentum !== metrics.earningsMomentum || row.weight !== (Object.hasOwn(metrics, 'weight') ? metrics.weight : metrics.proxyWeight)) fail('summary and constituents differ');
    }
    if (new Set(leaders.map((row) => row.symbol)).size !== leaders.length) fail('duplicate leaders');
    return { rows, dataAsOf: analysis.dataAsOf, generatedAt: analysis.generatedAt, count,
      plottedCount: rows.filter((row) => row.priceMomentum !== null && row.earningsMomentum !== null).length };
  }

  function parseSox(payload) {
    if (isResearchSummary(payload, 'sox')) {
      const meta = summaryMeta(payload);
      const rows = summaryEntities(payload)
        .map((entity, index) => ({
          rank: numberOr(entity.metrics.rank, index + 1),
          ticker: stringOr(entity.symbol, entity.id, entity.label, entity.name, ''),
          name: stringOr(entity.name, entity.label, ''),
          score: finiteOrNull(entity.metrics.score),
          weight: finiteOrNull(entity.metrics.weight ?? entity.metrics.proxyWeight),
          priceMomentum: finiteOrNull(entity.metrics.priceMomentum),
          earningsMomentum: finiteOrNull(entity.metrics.earningsMomentum),
          status: stringOr(entity.status, entity.signals?.[0], meta.statusLabel, '확인 필요'),
          warnings: entity.warnings,
        }))
        .filter((row) => row.ticker)
        .sort((a, b) => numberOr(b.score, -999) - numberOr(a.score, -999));
      return {
        generatedAt: meta.generatedAt,
        dataAsOf: meta.dataAsOf,
        status: stringOr(meta.statusLabel, payload.status, 'SOX public summary'),
        rows: rows.slice(0, 5),
        allRows: rows,
        constituentCount: finiteOrNull(meta.coverage?.entityCount) || rows.length,
        topWeight: rows.reduce((best, row) => numberOr(row.weight, -1) > numberOr(best?.weight, -1) ? row : best, null),
        entities: summaryEntities(payload).map((entity) => ({
          ...entity,
          symbol: stringOr(entity.symbol, entity.id, entity.label),
          signals: entity.signals.length ? entity.signals : [stringOr(entity.status, 'SOX constituent')],
        })),
        meta: {
          ...meta,
          statusState: stringOr(meta.statusState, payload.status, 'ok'),
          cadence: stringOr(meta.cadence, 'manual'),
          limitations: meta.limitations.length ? meta.limitations : ['SOX 공식 무료 비중이 없을 때는 시가총액 정규화 proxy weight를 사용합니다.'],
        },
      };
    }
    return {
      generatedAt: stringOr(payload?.generatedAt, ''),
      dataAsOf: stringOr(payload?.dataAsOf, ''),
      status: 'SOX payload did not match the quant-research-summary contract.',
      rows: [],
      allRows: [],
      constituentCount: 0,
      topWeight: null,
      entities: [],
      meta: {},
    };
  }

  function normalizeEtfSnapshot(snapshot) {
    if (!isRecord(snapshot)) return null;
    return {
      date: stringOr(snapshot.date, snapshot.asOfDate, ''),
      sourceStatus: stringOr(snapshot.sourceStatus, ''),
      sourceWarning: stringOr(snapshot.sourceWarning, ''),
      holdings: asRecords(snapshot.holdings).map(normalizeEtfHolding),
      top10: asRecords(snapshot.top10).map(normalizeEtfHolding).sort((a, b) => numberOr(a.rank, 9999) - numberOr(b.rank, 9999)),
      signals: asRecords(snapshot.signals),
      analysisSummary: isRecord(snapshot.analysisSummary) ? snapshot.analysisSummary : {},
    };
  }

  function normalizeEtfHolding(row, index = 0) {
    const weight = coerceWeightFraction(row.weight, row.weightPercent);
    return {
      rank: numberOr(row.rank, index + 1),
      ticker: stringOr(row.ticker, ''),
      codeRaw: stringOr(row.codeRaw, row.code, ''),
      name: stringOr(row.name, row.ticker, row.codeRaw, row.code, '-'),
      weight,
    };
  }

  function buildEtfWeightSeries(history, latestTop10) {
    return asRecords(latestTop10).slice(0, 10).map((latest, index) => {
      const key = holdingKey(latest);
      const points = asRecords(history).map((snapshot) => {
        const universe = snapshot.holdings?.length ? snapshot.holdings : snapshot.top10;
        const holding = asRecords(universe).find((row) => holdingKey(row) === key);
        return { date: snapshot.date, value: finiteOrNull(holding?.weight) };
      });
      return {
        key,
        rank: numberOr(latest.rank, index + 1),
        label: stringOr(latest.ticker, latest.codeRaw, latest.name, key),
        points,
      };
    }).filter((item) => item.key && item.points.some((point) => Number.isFinite(point.value)));
  }

  function holdingKey(row) {
    return stringOr(row?.ticker, row?.codeRaw, row?.code, row?.name, '').toUpperCase();
  }

  function factorDisplayName(id) {
    if (id === 'winsorized_12m') return { name: '12개월 모멘텀', detail: '일 수익률 ±8% 제한' };
    const riskAdjusted = /^ramom_(\d+)d_skip_(\d+)d_vol_(\d+)d$/.exec(id || '');
    if (riskAdjusted) return { name: '변동성 조정 모멘텀', detail: `${riskAdjusted[1]}일 · 최근 ${riskAdjusted[2]}일 제외 · 변동성 ${riskAdjusted[3]}일` };
    return { name: id || '확인 불가', detail: '' };
  }

  function factorAllocation(summary, projectId) {
    const momentum = projectId === 'momentum';
    const rows = asRecords(summary.rows).slice(0, 5).map((row) => ({
      rank: row.rank, symbol: momentum ? row.symbol : row.ticker,
      name: row.name || '', value: momentum ? row.signal : row.score,
      weight: momentum ? row.modelWeight : row.weight,
      date: momentum ? summary.dataAsOf : row.date,
    }));
    const validWeight = (weight) => typeof weight === 'number' && Number.isFinite(weight) && weight >= 0 && weight <= 1;
    const total = rows.length && rows.every((row) => validWeight(row.weight)) ? rows.reduce((sum, row) => sum + row.weight, 0) : null;
    const dates = [...new Set(rows.map((row) => row.date).filter(Boolean))];
    return { rows, total: total !== null && total <= 1 + 1e-8 ? total : null,
      dateLabel: dates.length === 1 ? formatMaybeDate(dates[0]) : dates.length > 1 ? '종목별 상이' : '확인 불가' };
  }

  function factorWeightScale(allocations) {
    const weights = allocations.flatMap((allocation) => allocation.rows.map((row) => row.weight))
      .filter((weight) => typeof weight === 'number' && Number.isFinite(weight) && weight >= 0 && weight <= 1);
    return Math.max(.4, Math.ceil(Math.max(0, ...weights) * 10 - 1e-9) / 10);
  }

  const FACTOR_VIEWS = new Map();
  function renderFactorOverview(summary, project) {
    const target = $(panelSelector(project, 'metrics'));
    if (!target) return;
    const momentum = project.id === 'momentum', identity = factorDisplayName(summary.factor);
    const allocation = factorAllocation(summary, project.id);
    FACTOR_VIEWS.set(project.id, { allocation, project });
    const weightPolicy = momentum ? (summary.selectedWeightingPolicy === 'score_liquidity_rank' ? '점수 70% · 거래대금 30%' : summary.selectedWeightingPolicy || '확인 불가') : '';
    target.innerHTML = `<div class="factor-identity"><span>선택 팩터</span><strong>${escapeHtml(identity.name)}</strong>${identity.detail ? `<small>${escapeHtml(identity.detail)}</small>` : ''}</div>
      <div class="factor-stats">
        <div class="factor-concentration"><span>표시 ${allocation.rows.length || 5}종목 비중</span><strong>${allocation.total === null ? '—' : `${(allocation.total * 100).toFixed(2)}%`}</strong><div class="factor-total-track" role="img" aria-label="${allocation.total === null ? '비중 합계 확인 불가' : `전체 포트폴리오 중 표시 종목 비중 ${formatPercent(allocation.total)}`}" ${allocation.total === null ? 'hidden' : ''}><i style="width:${allocation.total === null ? 0 : Math.min(100, allocation.total * 100)}%"></i></div></div>
        <div class="factor-composite"><span>종합 점수 · ${momentum ? '0–100' : '0–1'}</span><strong>${escapeHtml(formatNumber(summary.compositeScore))}</strong></div>
      </div>
      <div class="factor-holdings-heading"><h5>${momentum ? '신호' : '비중'} 상위 ${allocation.rows.length || 5}종목</h5><span>${momentum ? '신호' : '보유'} 기준 ${escapeHtml(allocation.dateLabel)}</span></div>
      <div class="factor-allocation" id="${escapeAttribute(panelDomId(project, 'allocation'))}"></div>`;
    const sourceMeta = $(panelSelector(project, 'factor-meta'));
    if (sourceMeta) sourceMeta.innerHTML = [
      ['팩터 ID', summary.factor], ['종합 점수', formatNumber(summary.compositeScore)],
      ...(momentum ? [['비중 정책', weightPolicy]] : []),
      ['데이터 기준일', formatMaybeDate(momentum ? summary.dataAsOf : summary.dataEndDate)],
      ['업데이트', formatFreshness(summary.generatedAt)],
    ].map(([label, value]) => `<div><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value || '확인 불가')}</dd></div>`).join('');
    // Both panels share one weight scale, including when either source arrives first.
    const scale = factorWeightScale([...FACTOR_VIEWS.values()].map((view) => view.allocation));
    for (const view of FACTOR_VIEWS.values()) renderFactorAllocation(view.allocation, view.project, scale);
  }

  function renderFactorAllocation(allocation, project, scale) {
    const target = $(panelSelector(project, 'allocation'));
    if (!target) return;
    const momentum = project.id === 'momentum';
    if (!allocation.rows.length) { target.innerHTML = '<p class="empty-state">표시할 종목이 없습니다.</p>'; return; }
    const ticks = [0, scale / 2, scale].map((value) => `${Math.round(value * 100)}%`);
    target.innerHTML = `<div class="factor-columns" aria-hidden="true"><span>#</span><span>종목</span><span>모델 비중</span><span></span><span>${momentum ? '신호' : '팩터 점수'}</span></div>
      <div class="factor-axis" aria-hidden="true"><div>${ticks.map((value) => `<span>${value}</span>`).join('')}</div></div>
      <ol class="factor-holdings" aria-label="${momentum ? '모멘텀 신호' : '모델 비중'} 순위. 비중 막대 공통 범위 0에서 ${Math.round(scale * 100)}퍼센트">
      ${allocation.rows.map((row) => {
        const valid = typeof row.weight === 'number' && Number.isFinite(row.weight) && row.weight >= 0 && row.weight <= 1;
        const percentage = valid ? formatPercent(row.weight) : '—';
        return `<li data-symbol="${escapeAttribute(row.symbol)}">
          <span class="factor-rank">${escapeHtml(row.rank)}</span><strong class="factor-symbol" title="${escapeAttribute(row.name || row.symbol)}">${escapeHtml(row.symbol)}</strong>
          <div class="factor-bar-track" role="img" aria-label="모델 비중 ${percentage}" data-weight="${valid ? row.weight : ''}" data-scale="${scale}">${valid ? `<i style="width:${row.weight / scale * 100}%"></i>` : ''}</div>
          <strong class="factor-weight">${percentage}</strong><span class="factor-signal" aria-label="${momentum ? '신호' : '팩터 점수'} ${escapeAttribute(formatNumber(row.value))}">${escapeHtml(formatNumber(row.value))}</span>
        </li>`;
      }).join('')}</ol>`;
  }

  function renderMomentum(summary, mode, error, project) {
    renderFactorOverview(summary, project);
    renderRows(panelSelector(project, 'rows'), summary.rows, (row) => [
      row.rank,
      badge(row.symbol),
      formatNumber(row.signal),
      formatPercent(row.modelWeight),
    ], 4);
    const statusTone = mode === 'live' && summary.meta?.statusState !== 'ok' ? 'warning' : mode;
    const statusText = summary.unavailable
      ? `Momentum 데이터 사용 불가 · 보유 종목 0개 · 사유: ${error || summary.status}`
      : buildStatusText(mode, summary.generatedAt, error, summary.status, summaryDataAsOf(summary));
    setStatus(panelSelector(project, 'status'), statusText, summary.unavailable ? 'warning' : statusTone);
  }

  function renderDram(summary, mode, error, project) {
    renderMetricBadges(panelSelector(project, 'metrics'), [
      `제품 ${summary.series.length || 0}개`,
      `관측치 ${formatInteger(summary.observationCount)}`,
    ]);
    renderDramChart(panelSelector(project, 'chart'), summary.series);
    setStatus(panelSelector(project, 'status'), buildStatusText(mode, summary.generatedAt, error, summary.status, summaryDataAsOf(summary)), mode);
  }

  function renderBestFactor(summary, mode, error, project) {
    renderFactorOverview(summary, project);
    renderRows(panelSelector(project, 'rows'), summary.rows, (row) => [
      row.rank,
      badge(row.ticker),
      formatNumber(row.score),
      formatPercent(row.weight),
      formatMaybeDate(row.date),
    ], 5);
    setStatus(panelSelector(project, 'status'), buildStatusText(mode, summary.generatedAt, error, summary.status, summaryDataAsOf(summary)), mode);
  }


  function renderEtfTracking(summary, mode, error, project) {
    const metrics = $(panelSelector(project, 'metrics'));
    if (metrics) metrics.innerHTML = '<strong>최근 1개월 편입비중</strong><span>현재 TOP10 종목 · 공통 비중 축</span>';
    renderRows(panelSelector(project, 'rows'), summary.rows, (row) => [
      `${row.name}${row.code ? ` (${row.code})` : ''}`,
      formatMaybeDate(row.date),
      `${formatPercent(row.top10Weight)} · TOP1 ${row.topTicker ? `${row.topTicker} ` : ''}${formatPercent(row.topWeight)}`,
      `${row.signalCount}건 / 편입·편출 ${row.entryExitCount}건`,
      formatPercent(row.returnCoverage),
    ], 5);
    renderEtfDetailCards(panelSelector(project, 'details'), summary.rows);
    setStatus(panelSelector(project, 'status'), buildStatusText(mode, summary.generatedAt, error, summary.status, summaryDataAsOf(summary)), mode);
  }

  function windowedRegimeRows(trend, weeks = 52) {
    const rows = Array.isArray(trend?.rows) ? trend.rows : [];
    return weeks === 'all' ? rows.slice() : rows.slice(-([26, 52, 104].includes(Number(weeks)) ? Number(weeks) : 52));
  }

  function regimeTrendGeometry(rows, width = 580) {
    const w = Math.max(280, width), compact = w < 460, h = compact ? 384 : 410;
    const left = 40, right = w - (compact ? 62 : 112), panelHeight = compact ? 125 : 138;
    const observedTop = 26, forecastTop = observedTop + panelHeight + 44;
    const outcomeY = forecastTop + panelHeight + 26, dateY = h - 5;
    const day = 86400000, times = rows.map((row) => Date.parse(`${row.date}T00:00:00Z`));
    const span = times.length > 1 ? times.at(-1) - times[0] : 0;
    const xAt = (time) => span ? left + (time - times[0]) / span * (right - left) : (left + right) / 2;
    const x = (index) => xAt(times[index]), y = (value, top) => top + (1 - value) * panelHeight;
    const panels = [
      { key: 'observed', top: observedTop, field: 'memberships', state: 'currentState' },
      { key: 'forecast', top: forecastTop, field: 'probabilities', state: 'nextState' },
    ].map((panel) => {
      const bands = [];
      rows.forEach((row, index) => {
        const start = index ? (times[index] - times[index - 1] <= 7 * day ? (times[index] + times[index - 1]) / 2 : times[index] - 3.5 * day) : times[index];
        const end = index < rows.length - 1 ? (times[index + 1] - times[index] <= 7 * day ? (times[index] + times[index + 1]) / 2 : times[index] + 3.5 * day) : times[index];
        const band = { state: row[panel.state], left: rows.length === 1 ? left : xAt(start), right: rows.length === 1 ? right : xAt(end) };
        const previous = bands.at(-1);
        if (previous && previous.state === band.state && Math.abs(previous.right - band.left) < .01) previous.right = band.right;
        else bands.push(band);
      });
      const series = REGIME_STATES.map((state) => ({ state, points: rows.map((row, index) => ({ x: x(index), y: y(row[panel.field][state], panel.top), value: row[panel.field][state], index })) }));
      const endpoints = series.filter((item) => item.points.length).map((item) => ({ ...item.points.at(-1), state: item.state }))
        .map((point) => ({ ...point, labelY: Math.max(panel.top + 9, Math.min(panel.top + panelHeight - 9, point.y)) }))
        .sort((a, b) => a.labelY - b.labelY);
      for (let i = 1; i < endpoints.length; i += 1) endpoints[i].labelY = Math.max(endpoints[i].labelY, endpoints[i - 1].labelY + 18);
      if (endpoints.length && endpoints.at(-1).labelY > panel.top + panelHeight - 9) {
        endpoints.at(-1).labelY = panel.top + panelHeight - 9;
        for (let i = endpoints.length - 2; i >= 0; i -= 1) endpoints[i].labelY = Math.min(endpoints[i].labelY, endpoints[i + 1].labelY - 18);
      }
      return { ...panel, bands, series, endpoints };
    });
    const tickCount = Math.min(rows.length, Math.max(2, Math.floor((right - left) / 110) + 1));
    const tickIndices = [...new Set(Array.from({ length: tickCount }, (_, i) => tickCount === 1 ? 0 : Math.round(i / (tickCount - 1) * (rows.length - 1))))];
    return { w, h, compact, left, right, panelHeight, observedTop, forecastTop, outcomeY, dateY, times, x, y, panels, tickIndices };
  }

  let regimeTrendObserver;
  function renderRegimeTrend(trend, project) {
    const target = $(panelSelector(project, 'chart'));
    if (!target) return;
    regimeTrendObserver?.disconnect();
    if (!trend?.rows?.length) {
      target.innerHTML = '<p class="empty-state">차트 데이터를 불러올 수 없습니다.</p>';
      return;
    }
    const labels = { risk_on: 'Risk-on', transition: 'Transition', risk_off: 'Risk-off' };
    const percent = (value) => `${(value * 100).toFixed(1)}%`;
    const observedLabel = `관측 ${trend.currentMeasureLabel || '소속도'}`;
    const readoutId = `${project.id}-trend-readout`;
    let period = trend.rows.length >= 52 ? '52' : 'all', selected = 0, pinnedDate = trend.rows.at(-1).date, previousWidth = 0;
    target.innerHTML = `<figure class="regime-trend">
      <div class="regime-trend-toolbar"><span class="regime-trend-range"></span><label>분석 기간 <select class="regime-trend-window" aria-label="국면 추이 분석 기간">${[26, 52, 104, 'all'].map((n) => `<option value="${n}"${n !== 'all' && n > trend.rows.length ? ' disabled' : ''}>${n === 'all' ? '전체' : `${n}주`}</option>`).join('')}</select></label></div>
      <div class="regime-trend-legend">${REGIME_STATES.map((state) => `<span class="${state}"><i aria-hidden="true"></i>${labels[state]}</span>`).join('')}<small>배경 · 국면</small><small>● ◆ ▼ 실제 1주 후</small></div>
      <figcaption id="${escapeAttribute(readoutId)}" class="regime-trend-readout" aria-live="polite"></figcaption>
      <div class="regime-trend-frame" tabindex="0" role="group" aria-label="국면 추이. 좌우 방향키로 관측일 이동" aria-describedby="${escapeAttribute(readoutId)}"></div>
    </figure>`;
    const select = target.querySelector('.regime-trend-window'), frame = target.querySelector('.regime-trend-frame'), readout = target.querySelector('.regime-trend-readout');
    select.value = period;
    const draw = (force = false) => {
      const width = Math.max(280, Math.round(target.clientWidth || 580));
      if (!force && width === previousWidth) return;
      previousWidth = width;
      const rows = windowedRegimeRows(trend, period), g = regimeTrendGeometry(rows, width);
      if (!rows.some((row) => row.date === pinnedDate)) pinnedDate = rows.at(-1).date;
      selected = rows.findIndex((row) => row.date === pinnedDate);
      target.querySelector('.regime-trend-range').textContent = `${rows.length}주 · ${rows[0].date.slice(0, 7).replace('-', '.')}–${rows.at(-1).date.slice(0, 7).replace('-', '.')}`;
      const line = (x1, y1, x2, y2, cls) => `<line class="${cls}" x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"/>`;
      const panels = g.panels.map((panel) => {
        const title = panel.key === 'observed' ? observedLabel : '1주 예측확률';
        const bands = panel.bands.map((band) => `<rect class="regime-trend-band ${band.state}" data-panel="${panel.key}" data-state="${band.state}" x="${band.left}" y="${panel.top}" width="${band.right - band.left}" height="${g.panelHeight}"/>`).join('');
        const grid = [0, .25, .5, .75, 1].map((v) => `${line(g.left, g.y(v, panel.top), g.right, g.y(v, panel.top), 'regime-trend-grid')}<text x="${g.left - 7}" y="${g.y(v, panel.top) + 4}" text-anchor="end">${v * 100}%</text>`).join('');
        const curves = panel.series.map((series) => `<path class="regime-trend-line ${series.state} ${panel.key}" data-panel="${panel.key}" data-state="${series.state}" d="${series.points.map((p, index) => `${index && g.times[index] - g.times[index - 1] <= 7 * 86400000 ? 'L' : 'M'}${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(' ')}"/>`).join('');
        const ends = panel.endpoints.map((p) => `<path class="regime-trend-leader ${p.state}" d="M${p.x},${p.y} L${p.x + 6},${p.labelY} H${p.x + 10}"/><circle class="regime-trend-end ${p.state}" cx="${p.x}" cy="${p.y}" r="3"/><text class="regime-trend-end-label ${p.state}" x="${p.x + 14}" y="${p.labelY + 4}">${escapeHtml(`${g.compact ? '' : `${REGIME_STATE_LABELS[p.state].replaceAll(' ', '')} `}${percent(p.value)}`)}</text>`).join('');
        const focus = REGIME_STATES.map((state) => `<circle class="regime-trend-focus ${state}" data-panel="${panel.key}" data-state="${state}" r="3.5"/>`).join('');
        return `<text class="regime-trend-title" x="${g.left}" y="${panel.top - 11}">${escapeHtml(title)}</text>${bands}${grid}${curves}${ends}${focus}`;
      }).join('');
      const markerRadius = Math.min(3.5, (g.right - g.left) / Math.max(1, rows.length - 1) * .4);
      const outcomes = rows.map((row, i) => {
        const x = g.x(i), y = g.outcomeY, r = markerRadius, state = row.actualState, cls = `regime-trend-outcome ${state || 'pending'}`;
        const description = escapeHtml(`${row.date} → ${row.nextDate} · ${state ? labels[state] : row.nextDate > trend.rows.at(-1).date ? '결과 대기' : '결과 없음'}`);
        const title = `<title>${description}</title>`;
        if (state === 'transition') return `<path data-date="${row.date}" class="${cls}" d="M${x},${y - r} L${x + r},${y} L${x},${y + r} L${x - r},${y} Z">${title}</path>`;
        if (state === 'risk_off') return `<path data-date="${row.date}" class="${cls}" d="M${x - r},${y - r} L${x + r},${y - r} L${x},${y + r} Z">${title}</path>`;
        return `<circle data-date="${row.date}" class="${cls}" cx="${x}" cy="${y}" r="${r}">${title}</circle>`;
      }).join('');
      const dates = g.tickIndices.map((i) => `<text x="${g.x(i)}" y="${g.dateY}" text-anchor="${i === 0 ? 'start' : i === rows.length - 1 ? 'end' : 'middle'}">${rows.length <= 26 ? rows[i].date.slice(5).replace('-', '.') : rows[i].date.slice(0, 7).replace('-', '.')}</text>`).join('');
      frame.innerHTML = `<svg viewBox="0 0 ${g.w} ${g.h}" role="img" aria-label="${escapeAttribute(`${observedLabel}와 1주 예측확률, ${rows.length}주`)}">${panels}${line(g.left, g.outcomeY, g.right, g.outcomeY, 'regime-trend-grid')}<text class="regime-trend-outcome-title" x="${g.left}" y="${g.outcomeY - 10}">실제 t+1</text>${outcomes}${dates}${line(g.x(selected), g.observedTop, g.x(selected), g.outcomeY + 7, 'regime-trend-cursor')}</svg>`;
      const svg = frame.querySelector('svg'), cursor = frame.querySelector('.regime-trend-cursor');
      const show = (index) => {
        selected = index;
        const row = rows[index];
        cursor.setAttribute('x1', g.x(index)); cursor.setAttribute('x2', g.x(index));
        for (const point of frame.querySelectorAll('.regime-trend-focus')) {
          const panel = g.panels.find((item) => item.key === point.dataset.panel);
          point.setAttribute('cx', g.x(index)); point.setAttribute('cy', g.y(row[panel.field][point.dataset.state], panel.top));
        }
        for (const marker of frame.querySelectorAll('.regime-trend-outcome')) marker.classList.toggle('is-active', marker.dataset.date === row.date);
        const actual = row.actualState ? labels[row.actualState] : row.nextDate > trend.rows.at(-1).date ? '결과 대기' : '결과 없음';
        const vector = (values) => REGIME_STATES.map((state) => `<div class="${state}"><dt>${labels[state]}</dt><dd>${percent(values[state])}</dd></div>`).join('');
        readout.innerHTML = `<div class="regime-trend-date"><strong>${escapeHtml(formatMaybeDate(row.date))}</strong><span>→ ${escapeHtml(formatMaybeDate(row.nextDate))}</span></div><div class="regime-trend-vectors"><div><span>${escapeHtml(observedLabel)}</span><dl>${vector(row.memberships)}</dl></div><div><span>1주 예측확률</span><dl>${vector(row.probabilities)}</dl></div></div><div class="regime-trend-result"><span>예측 <b>${labels[row.nextState]}</b></span><span>실제 <b>${actual}</b></span><span>엔트로피 <b>${Number.isFinite(row.entropy) ? row.entropy.toFixed(3) : '—'}</b></span></div>`;
      };
      const nearest = (event) => {
        const rect = svg.getBoundingClientRect();
        if (!rect.width) return selected;
        const px = (event.clientX - rect.left) * g.w / rect.width;
        let closest = 0;
        rows.forEach((_, i) => { if (Math.abs(g.x(i) - px) < Math.abs(g.x(closest) - px)) closest = i; });
        return closest;
      };
      frame.onpointermove = (event) => { if (event.pointerType !== 'touch') show(nearest(event)); };
      frame.onclick = (event) => { const index = nearest(event); pinnedDate = rows[index].date; show(index); frame.focus({ preventScroll: true }); };
      frame.onpointerleave = () => show(rows.findIndex((row) => row.date === pinnedDate));
      frame.onkeydown = (event) => {
        const move = { ArrowLeft: Math.max(0, selected - 1), ArrowUp: Math.max(0, selected - 1), ArrowRight: Math.min(rows.length - 1, selected + 1), ArrowDown: Math.min(rows.length - 1, selected + 1), Home: 0, End: rows.length - 1, Escape: rows.length - 1 };
        if (Object.hasOwn(move, event.key)) { event.preventDefault(); pinnedDate = rows[move[event.key]].date; show(move[event.key]); }
      };
      show(selected);
    };
    select.addEventListener('change', () => { period = select.value; draw(true); });
    draw();
    if (typeof ResizeObserver !== 'undefined') { regimeTrendObserver = new ResizeObserver(() => draw()); regimeTrendObserver.observe(target); }
  }

  function renderRegime(summary, mode, error, project) {
    renderRegimeTrend(summary?.trend || null, project);
    setStatus(panelSelector(project, 'status'), buildStatusText(mode, summary.generatedAt, error, summary.status, summaryDataAsOf(summary)), mode);
  }

  function renderFearAndGreed(summary, mode, error, project) {
    renderFearScatter(summary.scatter || null, project);
    setStatus(panelSelector(project, 'status'), buildStatusText(mode, summary.generatedAt, error, summary.status, summaryDataAsOf(summary)), mode);
  }

  function renderSox(summary, mode, error, project) {
    const quadrant = summary.quadrant, metrics = $(panelSelector(project, 'metrics'));
    if (metrics) metrics.innerHTML = quadrant
      ? `<strong>${quadrant.plottedCount === quadrant.count ? `전체 ${quadrant.count}종목` : `표시 ${quadrant.plottedCount} / ${quadrant.count}종목`}</strong><span>상대점수 0–1 · 중앙선 0.5</span>`
      : '<strong>전체 종목 차트 확인 필요</strong>';
    renderSoxQuadrant(panelSelector(project, 'details'), quadrant);
    renderRows(panelSelector(project, 'rows'), asRecords(quadrant?.rows || summary.rows), (row) => [
      row.rank, badge(row.ticker), formatNumber(row.score), formatPercent(row.weight),
      `${formatNumber(row.priceMomentum)} / ${formatNumber(row.earningsMomentum)}`, row.status,
    ], 6);
    setStatus(panelSelector(project, 'status'), buildStatusText(mode, summary.generatedAt, error, summary.status, summaryDataAsOf(summary)), mode);
  }

  function soxScore(value) {
    return typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 1 ? value : null;
  }

  function soxQuadrantGeometry(rows, width = 1000, selectedTicker = '') {
    const w = Math.max(220, width), compact = w < 600, h = compact ? 360 : 480;
    const bounds = { left: 34, right: w - 22, top: 46, bottom: h - 42 };
    const x = (score) => bounds.left + score * (bounds.right - bounds.left);
    const y = (score) => bounds.bottom - score * (bounds.bottom - bounds.top);
    const points = asRecords(rows).filter((row) => soxScore(row.priceMomentum) !== null && soxScore(row.earningsMomentum) !== null)
      .map((row) => ({ ...row, x: x(row.priceMomentum), y: y(row.earningsMomentum) }));
    const priority = [...points].sort((a, b) => (b.ticker === selectedTicker) - (a.ticker === selectedTicker) || a.rank - b.rank);
    const labels = [];
    const overlaps = (a, b, gap = 4) => a.x < b.x + b.width + gap && a.x + a.width + gap > b.x && a.y < b.y + b.height + gap && a.y + a.height + gap > b.y;
    for (const point of priority) {
      if (compact && point.rank > 5 && point.ticker !== selectedTicker) continue;
      const labelWidth = point.ticker.length * (compact ? 6.8 : 8.2) + 20, labelHeight = compact ? 26 : 30;
      const candidates = [
        [12, -labelHeight / 2], [-labelWidth - 12, -labelHeight / 2], [-labelWidth / 2, -labelHeight - 12], [-labelWidth / 2, 12],
        [12, -labelHeight - 8], [-labelWidth - 12, -labelHeight - 8], [12, 8], [-labelWidth - 12, 8],
        [-labelWidth / 2, -labelHeight - 36], [-labelWidth / 2, 36], [30, -labelHeight / 2], [-labelWidth - 30, -labelHeight / 2],
      ].map(([dx, dy]) => ({ x: point.x + dx, y: point.y + dy, width: labelWidth, height: labelHeight }));
      const label = candidates.find((box) => box.x >= bounds.left && box.x + box.width <= bounds.right
        && box.y >= bounds.top - 20 && box.y + box.height <= bounds.bottom
        && !labels.some((existing) => overlaps(box, existing))
        && !points.some((other) => other.ticker !== point.ticker && overlaps(box, { x: other.x - 5, y: other.y - 5, width: 10, height: 10 }, 2)));
      if (label) labels.push({ ...label, ticker: point.ticker, rank: point.rank, anchorX: point.x, anchorY: point.y });
    }
    return { width: w, height: h, compact, bounds, points, labels, centerX: x(0.5), centerY: y(0.5) };
  }

  function renderSoxQuadrantChart(rows, width, selectedTicker, labelTicker = selectedTicker) {
    const g = soxQuadrantGeometry(rows, width, labelTicker), b = g.bounds;
    const grid = [0, 0.5, 1].map((score) => {
      const x = b.left + score * (b.right - b.left), y = b.bottom - score * (b.bottom - b.top);
      return `<text class="sox-axis-tick" x="${x}" y="${b.bottom + 20}" text-anchor="middle">${score}</text><text class="sox-axis-tick" x="${b.left - 12}" y="${y + 4}" text-anchor="end">${score}</text>`;
    }).join('');
    const points = [...g.points].sort((a, b) => (a.ticker === selectedTicker) - (b.ticker === selectedTicker)).map((point) => {
      const active = point.ticker === selectedTicker, leader = point.rank <= 5;
      return `<g class="sox-quadrant-point${leader ? ' is-leader' : ''}${active ? ' is-selected' : ''}" data-sox-ticker="${escapeAttribute(point.ticker)}" data-price="${point.priceMomentum}" data-earnings="${point.earningsMomentum}" transform="translate(${point.x} ${point.y})"><circle class="sox-point-hit" r="13"/><circle class="sox-point-halo" r="15"/><circle class="sox-point-dot" r="${active ? 7 : leader ? 6 : 4.5}"/></g>`;
    }).join('');
    const labels = g.labels.map((label) => {
      const active = label.ticker === selectedTicker, leader = label.rank <= 5;
      const endX = Math.max(label.x, Math.min(label.x + label.width, label.anchorX));
      const endY = Math.max(label.y, Math.min(label.y + label.height, label.anchorY));
      return `<g class="sox-ticker-label${leader ? ' is-leader' : ''}${active ? ' is-selected' : ''}" data-sox-ticker="${escapeAttribute(label.ticker)}"><line x1="${label.anchorX}" y1="${label.anchorY}" x2="${endX}" y2="${endY}"/><rect x="${label.x}" y="${label.y}" width="${label.width}" height="${label.height}" rx="13"/><text x="${label.x + label.width / 2}" y="${label.y + (g.compact ? 17 : 20)}" text-anchor="middle">${escapeHtml(label.ticker)}</text></g>`;
    }).join('');
    return `<svg class="sox-quadrant-svg" viewBox="0 0 ${g.width} ${g.height}" role="img" aria-label="가격과 실적 모멘텀 상대점수, ${g.points.length}종목">
      <rect class="sox-quadrant-surface" x="${b.left}" y="${b.top}" width="${b.right - b.left}" height="${b.bottom - b.top}" rx="8"/>
      <text class="sox-axis-title" x="${b.left}" y="20">실적 모멘텀 ↑</text><text class="sox-axis-title" x="${b.right}" y="${g.height - 2}" text-anchor="end">가격 모멘텀 →</text>
      <line class="sox-midline" x1="${g.centerX}" x2="${g.centerX}" y1="${b.top}" y2="${b.bottom}"/><line class="sox-midline" x1="${b.left}" x2="${b.right}" y1="${g.centerY}" y2="${g.centerY}"/>
      ${grid}${labels}${points}
    </svg>`;
  }

  function soxQuadrantReadout(row) {
    if (!row) return '선택할 종목이 없습니다.';
    return `<div class="sox-selection-name"><strong>${escapeHtml(row.ticker)}</strong><span>${escapeHtml(row.name)}</span><small>${escapeHtml(row.status)}</small></div><dl class="sox-selection-values">
      ${[['가격 점수', row.priceMomentum], ['실적 점수', row.earningsMomentum], ['종합 점수', row.score], ['Proxy 비중', row.weight]].map(([label, value], index) => `<div><dt>${label}</dt><dd>${escapeHtml(index === 3 ? formatPercent(value) : formatNumber(value))}</dd></div>`).join('')}</dl>`;
  }

  let soxQuadrantObserver;
  function renderSoxQuadrant(selector, quadrant) {
    const target = $(selector);
    if (!target) return;
    soxQuadrantObserver?.disconnect();
    if (!quadrant) {
      target.innerHTML = '<div class="sox-quadrant-empty" role="status">전체 구성종목 차트를 표시할 수 없습니다.</div>';
      return;
    }
    const rows = quadrant.rows, drawable = rows.filter((row) => row.priceMomentum !== null && row.earningsMomentum !== null);
    let pinnedTicker = drawable[0]?.ticker || rows[0]?.ticker || '', currentTicker = pinnedTicker, lastWidth = 0;
    target.innerHTML = `<div class="sox-quadrant-controls"><div class="sox-leaders" role="group" aria-label="종합 상위 5종목 선택"><span>종합 Top 5</span>${rows.slice(0, 5).map((row) => `<button class="sox-leader-button" type="button" data-sox-select="${escapeAttribute(row.ticker)}" aria-pressed="${row.ticker === pinnedTicker}">${escapeHtml(row.ticker)}</button>`).join('')}</div>
      <label class="sox-stock-control">종목 선택<select id="sox-stock-select" data-control-kind="display">${rows.map((row) => `<option value="${escapeAttribute(row.ticker)}"${row.ticker === pinnedTicker ? ' selected' : ''}>${row.rank}. ${escapeHtml(row.ticker)}</option>`).join('')}</select></label></div>
      <div class="sox-quadrant-readout" aria-live="polite">${soxQuadrantReadout(rows.find((row) => row.ticker === pinnedTicker))}</div>
      <div class="sox-quadrant-frame" tabindex="0" role="group" aria-label="SOX 가격·실적 사분면. 방향키로 종목을 선택합니다." aria-keyshortcuts="ArrowLeft ArrowRight ArrowUp ArrowDown Home End Escape"></div>`;
    const frame = target.querySelector('.sox-quadrant-frame'), readout = target.querySelector('.sox-quadrant-readout'), select = target.querySelector('#sox-stock-select');
    const draw = () => {
      const width = Math.max(220, Math.round(frame.clientWidth || 1000));
      lastWidth = width;
      frame.innerHTML = drawable.length ? renderSoxQuadrantChart(rows, width, currentTicker, pinnedTicker) : '<div class="sox-quadrant-empty">가격·실적 점수를 함께 가진 종목이 없습니다.</div>';
    };
    const choose = (ticker, pin = false) => {
      const row = rows.find((item) => item.ticker === ticker);
      if (!row) return;
      if (pin) pinnedTicker = ticker;
      currentTicker = ticker;
      readout.innerHTML = soxQuadrantReadout(row);
      frame.setAttribute('aria-label', `SOX 가격·실적 사분면. ${row.ticker} 가격 ${formatNumber(row.priceMomentum)}, 실적 ${formatNumber(row.earningsMomentum)}. 방향키로 종목 선택.`);
      select.value = pinnedTicker;
      target.querySelectorAll('[data-sox-select]').forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.soxSelect === pinnedTicker)));
      draw();
    };
    target.querySelectorAll('[data-sox-select]').forEach((button) => {
      button.addEventListener('click', () => choose(button.dataset.soxSelect, true));
      button.addEventListener('pointerenter', () => choose(button.dataset.soxSelect));
      button.addEventListener('pointerleave', () => choose(pinnedTicker));
      button.addEventListener('focus', () => choose(button.dataset.soxSelect));
      button.addEventListener('blur', () => choose(pinnedTicker));
    });
    select.addEventListener('change', () => choose(select.value, true));
    frame.addEventListener('pointermove', (event) => {
      const ticker = event.target.closest('[data-sox-ticker]')?.dataset.soxTicker;
      if (ticker && ticker !== currentTicker) choose(ticker);
    });
    frame.addEventListener('pointerleave', () => { if (currentTicker !== pinnedTicker) choose(pinnedTicker); });
    frame.addEventListener('click', (event) => {
      const ticker = event.target.closest('[data-sox-ticker]')?.dataset.soxTicker;
      if (ticker) choose(ticker, true);
    });
    frame.addEventListener('keydown', (event) => {
      const index = Math.max(0, rows.findIndex((row) => row.ticker === pinnedTicker));
      let next;
      if (['ArrowRight', 'ArrowDown'].includes(event.key)) next = rows[(index + 1) % rows.length];
      else if (['ArrowLeft', 'ArrowUp'].includes(event.key)) next = rows[(index + rows.length - 1) % rows.length];
      else if (['Home', 'Escape'].includes(event.key)) next = rows[0];
      else if (event.key === 'End') next = rows.at(-1);
      if (next) { event.preventDefault(); choose(next.ticker, true); }
    });
    draw();
    if (typeof ResizeObserver !== 'undefined') {
      soxQuadrantObserver = new ResizeObserver(() => { if (Math.abs(frame.clientWidth - lastWidth) >= 2) draw(); });
      soxQuadrantObserver.observe(frame);
    }
  }

  function etfComparisonDomain(rows) {
    const points = asRecords(rows).flatMap((row) => asRecords(row.chartSeries).flatMap((series) => asArray(series.points)));
    const dates = points.map((point) => Date.parse(point?.date ?? point?.[0])).filter(Number.isFinite);
    const values = points.map((point) => finiteOrNull(point?.value ?? point?.[1])).filter((value) => value !== null);
    return {
      minDate: dates.length ? Math.min(...dates) : null,
      maxDate: dates.length ? Math.max(...dates) : null,
      yTicks: buildNiceTicks(0, Math.max(0.04, ...values), 6, 0.01),
    };
  }

  let etfChartObserver;
  function renderEtfDetailCards(selector, rows) {
    const target = $(selector);
    if (!target) return;
    etfChartObserver?.disconnect();
    const records = asRecords(rows), domain = etfComparisonDomain(records);
    target.innerHTML = `<div class="etf-detail-grid">${records.map((row, index) => `
      <article class="etf-detail-card" data-etf-index="${index}">
        <header class="etf-card-heading"><h4>${escapeHtml(row.name)}</h4><p>${escapeHtml(row.code || '')} · ${escapeHtml(formatMaybeDate(row.date))}</p></header>
        <div class="etf-exposure"><span>TOP10 비중</span><strong>${escapeHtml(formatPercent(row.top10Weight))}</strong></div>
        <div class="etf-plot-heading"><span>편입비중 추이</span><div class="etf-series-control" role="group" aria-label="${escapeAttribute(row.name)} 표시 종목 수" data-control-kind="display"><button type="button" data-etf-limit="5" aria-pressed="true">Top 5</button><button type="button" data-etf-limit="10" aria-pressed="false">Top 10</button></div></div>
        <div class="etf-chart-slot">${renderEtfMiniChart(row, { width: 360, domain, limit: 5 })}</div>
        <details class="etf-holdings-details"><summary>TOP10 보유종목</summary><ol class="etf-top10-list" aria-label="${escapeAttribute(row.name)} 최신 TOP10 보유종목">${renderEtfTop10Items(row.top10)}</ol></details>
      </article>`).join('') || '<div class="skeleton-line">ETF 상세 요약을 표시할 데이터가 없습니다.</div>'}</div>`;
    const draws = new Map();
    target.querySelectorAll?.('.etf-detail-card').forEach((card, index) => {
      const slot = card.querySelector('.etf-chart-slot');
      let limit = 5, lastWidth = 0;
      const draw = (force = false) => {
        const width = Math.max(220, Math.round(slot.clientWidth || 360));
        if (!force && Math.abs(width - lastWidth) < 2) return;
        lastWidth = width;
        slot.innerHTML = renderEtfMiniChart(records[index], { width, domain, limit });
        bindChartKeyboardFrames(slot, { frameSelector: '.etf-mini-plot', seriesSelector: '.etf-mini-series', pointSelector: '.etf-data-point', readoutSelector: '.etf-chart-readout', navigationLabel: '날짜/종목', pointerPreview: true, legendSelector: '.etf-legend-button', guideSelector: '.etf-selection-guide', renderReadout: (point) => renderEtfReadout(point.dataset.seriesLabel, point.dataset.date, finiteOrNull(point.dataset.weight)) });
      };
      card.querySelectorAll('[data-etf-limit]').forEach((button) => button.addEventListener('click', () => {
        limit = Number(button.dataset.etfLimit);
        card.querySelectorAll('[data-etf-limit]').forEach((control) => control.setAttribute('aria-pressed', String(Number(control.dataset.etfLimit) === limit)));
        draw(true);
      }));
      draws.set(slot, draw);
      draw();
    });
    if (typeof ResizeObserver !== 'undefined') {
      etfChartObserver = new ResizeObserver((entries) => entries.forEach((entry) => draws.get(entry.target)?.()));
      draws.forEach((_, slot) => etfChartObserver.observe(slot));
    }
  }

  function renderEtfTop10Items(top10) {
    const holdings = asRecords(top10).slice(0, 10);
    if (!holdings.length) return '<li class="etf-top10-empty">표시할 TOP10 데이터가 없습니다.</li>';
    return holdings.map((holding, index) => {
      const identifier = stringOr(holding.ticker, holding.codeRaw, holding.name, '-');
      return `
        <li>
          <span class="etf-rank">${numberOr(holding.rank, index + 1)}</span>
          <strong>${escapeHtml(identifier)}</strong>
          <em>${escapeHtml(formatPercent(holding.weight))}</em>
          <small>${escapeHtml(holding.name)}</small>
        </li>
      `;
    }).join('');
  }

  function renderEtfMiniChart(row, options = {}) {
    const chartSeries = asRecords(row.chartSeries).slice(0, options.limit || 10)
      .map((item) => ({
        ...item,
        points: asArray(item.points)
          .map((point) => ({
            date: stringOr(point?.date, point?.[0], ''),
            value: finiteOrNull(point?.value ?? point?.[1]),
          }))
          .filter((point) => Number.isFinite(Date.parse(point.date))),
      }))
      .filter((item) => item.points.some((point) => Number.isFinite(point.value)));
    if (!chartSeries.length) return '<div class="etf-mini-empty">표시할 비중 그래프 데이터가 없습니다.</div>';

    const points = chartSeries.flatMap((item) => item.points);
    const dates = points.map((point) => Date.parse(point.date)).filter(Number.isFinite);
    const values = points.map((point) => point.value).filter(Number.isFinite);
    const minDate = options.domain?.minDate ?? Math.min(...dates);
    const maxDate = options.domain?.maxDate ?? Math.max(...dates);
    const minValue = Math.min(...values);
    const maxValue = Math.max(...values);
    const yTicks = options.domain?.yTicks || buildEtfPercentAxisTicks(minValue, maxValue, 5);
    const yMin = yTicks[0] ?? Math.max(0, minValue);
    const yMax = yTicks.at(-1) ?? Math.max(maxValue, yMin + 0.01);
    const width = options.width || 1120;
    const compact = width < 700;
    const height = compact ? 245 : 520;
    const margin = compact ? { top: 28, right: 12, bottom: 36, left: 38 } : { top: 52, right: 32, bottom: 68, left: 76 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;
    const x = (date) => margin.left + ((Date.parse(date) - minDate) / Math.max(maxDate - minDate, 1)) * innerWidth;
    const y = (value) => margin.top + (1 - ((value - yMin) / Math.max(yMax - yMin, 0.000001))) * innerHeight;
    const grid = yTicks.map((tick) => {
      const yy = y(tick);
      return `<g><line x1="${margin.left}" x2="${width - margin.right}" y1="${yy.toFixed(1)}" y2="${yy.toFixed(1)}" stroke="#d9e2f1"/><text x="${margin.left - 12}" y="${(yy + 5).toFixed(1)}" text-anchor="end" fill="#aab3c2" font-size="${compact ? 11 : 14}" font-weight="700">${escapeHtml(formatPercent(tick))}</text></g>`;
    }).join('');
    const paths = chartSeries.map((item, index) => {
      const color = COLORS[index % COLORS.length];
      const segments = splitChartPointSegments(item.points);
      const segmentPaths = segments.map((segment) => {
        const pathData = segment.map((point, pointIndex) => `${pointIndex ? 'L' : 'M'} ${x(point.date).toFixed(1)} ${y(point.value).toFixed(1)}`).join(' ');
        return `<path class="etf-mini-line" d="${pathData}" fill="none" stroke="${color}" stroke-width="${compact ? 2.2 : item.rank <= 3 ? 3.8 : 2.8}"${index >= 6 ? ' stroke-dasharray="5 3"' : ''} stroke-linecap="round" stroke-linejoin="round"/>`;
      }).join('');
      const pointMarks = item.points.filter((point) => Number.isFinite(point.value)).map((point, pointIndex) => {
        const pointX = x(point.date);
        const pointY = y(point.value);
        const valueText = formatPercent(point.value);
        const keyboardLabel = `${item.label} · ${formatMaybeDate(point.date)} · ${valueText}`;
        const labelWidth = Math.max(50, valueText.length * 8 + 16);
        const labelX = pointX > width - margin.right - 70 ? -labelWidth - 9 : 9;
        const labelY = pointY < margin.top + 36 ? 9 : -33;
        return `
          <g class="etf-data-point" transform="translate(${pointX.toFixed(1)} ${pointY.toFixed(1)})" data-series-index="${index}" data-point-index="${pointIndex}" data-date="${escapeAttribute(point.date)}" data-chart-x="${pointX.toFixed(1)}" data-keyboard-label="${escapeAttribute(keyboardLabel)}" data-series-label="${escapeAttribute(item.label)}" data-weight="${point.value}">
            <circle class="etf-point-hit" r="10" fill="transparent"/>
            <circle class="etf-mini-point" r="${compact ? 2.3 : item.rank <= 3 ? 4.7 : 4}" fill="${color}"/>
            <g class="etf-point-label" transform="translate(${labelX} ${labelY})" aria-hidden="true">
              <rect width="${labelWidth}" height="24" rx="5"/>
              <text x="${labelWidth / 2}" y="16" text-anchor="middle">${escapeHtml(valueText)}</text>
            </g>
          </g>
        `;
      }).join('');
      return `<g class="etf-mini-series series-color-${index % COLORS.length}" aria-label="${escapeAttribute(item.label)}">${segmentPaths}${pointMarks}</g>`;
    }).join('');
    const legend = chartSeries.map((item, index) => {
      const latest = item.points.at(-1);
      return `<button type="button" class="etf-legend-button" data-series-index="${index}" aria-pressed="false"><i class="legend-key" style="background:${COLORS[index % COLORS.length]}"></i><span>${escapeHtml(item.label)}</span><strong>${escapeHtml(formatPercent(latest?.value))}</strong></button>`;
    }).join('');
    const uniqueDates = [...new Set(points.map((point) => point.date))].sort((a, b) => Date.parse(a) - Date.parse(b));
    const xTickCount = Math.min(compact ? 3 : 6, uniqueDates.length);
    const xTickDates = xTickCount <= 1
      ? uniqueDates
      : [...new Set(Array.from({ length: xTickCount }, (_, index) => uniqueDates[Math.round((index * (uniqueDates.length - 1)) / (xTickCount - 1))]))];
    const xTicks = xTickDates.map((date, index) => {
      const anchor = index === 0 ? 'start' : index === xTickDates.length - 1 ? 'end' : 'middle';
      return `<text x="${x(date).toFixed(1)}" y="${height - 22}" text-anchor="${anchor}" fill="#9aa4b2" font-size="${compact ? 11 : 14}" font-weight="650">${escapeHtml(compact ? date.slice(5).replace('-', '.') : formatMaybeDate(date))}</text>`;
    }).join('');
    const initialSeries = chartSeries[0];
    const initialPoint = asArray(initialSeries?.points).filter((point) => Number.isFinite(point.value)).at(-1);
    const initialReadout = initialSeries && initialPoint
      ? renderEtfReadout(initialSeries.label, initialPoint.date, initialPoint.value)
      : '차트 값을 확인할 수 없습니다.';
    const frameLabel = `${row.name} 현재 상위 ${chartSeries.length}종목 편입비중 추이. 좌우 방향키로 날짜, 위아래 방향키로 종목을 탐색합니다.`;
    return `
      <div class="etf-mini-chart" data-y-min="${yMin}" data-y-max="${yMax}" data-date-start="${minDate}" data-date-end="${maxDate}">
        <div class="etf-chart-readout" aria-live="polite">${initialReadout}</div>
        <div class="etf-mini-plot" tabindex="0" role="group" aria-label="${escapeAttribute(frameLabel)}" data-base-label="${escapeAttribute(frameLabel)}">
          <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeAttribute(row.name)} 현재 상위 ${chartSeries.length}종목 편입비중 추이">
            <rect x="0" y="0" width="${width}" height="${height}" fill="transparent"/>
            <text x="${margin.left}" y="${compact ? 14 : 30}" fill="#d8dee8" font-size="${compact ? 11 : 16}" font-weight="600">최근 1개월 비중(%)</text>
            ${grid}
            <line x1="${margin.left}" x2="${width - margin.right}" y1="${height - margin.bottom}" y2="${height - margin.bottom}" stroke="#3b4556"/>
            ${xTicks}
            <line class="etf-selection-guide" x1="${margin.left}" x2="${margin.left}" y1="${margin.top}" y2="${height - margin.bottom}" hidden/>
            ${paths}
          </svg>
        </div>
        <div class="chart-legend etf-mini-legend">${legend}</div>
      </div>
    `;
  }

  function renderEtfReadout(label, date, weight) {
    return `<div class="etf-selected-asset"><strong>${escapeHtml(label)}</strong><time datetime="${escapeAttribute(date)}">${escapeHtml(formatMaybeDate(date))}</time></div><div class="etf-selected-weight"><span>편입비중</span><strong>${escapeHtml(formatPercent(weight))}</strong></div>`;
  }

  function bindChartKeyboardFrames(root, selectors) {
    if (!root?.querySelectorAll) return;
    const navigationLabel = stringOr(selectors.navigationLabel, '날짜/종목');
    root.querySelectorAll(selectors.frameSelector).forEach((frame) => {
      const seriesGroups = [...frame.querySelectorAll(selectors.seriesSelector)];
      if (!seriesGroups.length) return;
      const readout = frame.parentElement?.querySelector(selectors.readoutSelector);
      const initialReadout = readout?.innerHTML || '';
      const legendButtons = selectors.legendSelector
        ? [...(frame.parentElement?.querySelectorAll(selectors.legendSelector) || [])]
        : [];
      const selectionGuide = selectors.guideSelector ? frame.querySelector(selectors.guideSelector) : null;
      let seriesIndex = 0;
      let pointIndex = Math.max(seriesGroups[0].querySelectorAll(selectors.pointSelector).length - 1, 0);
      let pinnedSelection = null;

      const pointsForSeries = (index) => [...(seriesGroups[index]?.querySelectorAll(selectors.pointSelector) || [])];
      const closestPointIndex = (points, targetDate) => {
        const target = Date.parse(targetDate);
        if (!Number.isFinite(target)) return Math.max(points.length - 1, 0);
        return points.reduce((bestIndex, point, index) => {
          const distance = Math.abs(Date.parse(point.dataset.date) - target);
          const bestDistance = Math.abs(Date.parse(points[bestIndex]?.dataset.date) - target);
          return distance < bestDistance ? index : bestIndex;
        }, 0);
      };
      const updateLegendState = () => {
        legendButtons.forEach((button) => {
          button.setAttribute('aria-pressed', String(Number(button.dataset.seriesIndex) === pinnedSelection?.seriesIndex));
        });
      };
      const clearSelection = () => {
        seriesGroups.forEach((series) => series.classList.remove('is-keyboard-active'));
        frame.querySelectorAll(selectors.pointSelector).forEach((point) => point.classList.remove('is-keyboard-active'));
        seriesIndex = 0;
        pointIndex = Math.max(pointsForSeries(0).length - 1, 0);
        frame.classList.remove('is-keyboard-active');
        if (selectionGuide) selectionGuide.setAttribute('hidden', '');
        if (readout) readout.innerHTML = initialReadout;
        frame.setAttribute('aria-label', frame.dataset.baseLabel || '차트');
        updateLegendState();
      };
      const update = () => {
        seriesGroups.forEach((series) => series.classList.remove('is-keyboard-active'));
        frame.querySelectorAll(selectors.pointSelector).forEach((point) => point.classList.remove('is-keyboard-active'));
        const points = pointsForSeries(seriesIndex);
        if (!points.length) return;
        pointIndex = Math.max(0, Math.min(pointIndex, points.length - 1));
        const point = points[pointIndex];
        seriesGroups[seriesIndex].classList.add('is-keyboard-active');
        point.classList.add('is-keyboard-active');
        frame.classList.add('is-keyboard-active');
        const label = point.dataset.keyboardLabel || '선택값 확인 필요';
        if (readout) readout.innerHTML = selectors.renderReadout
          ? selectors.renderReadout(point)
          : `${escapeHtml(label)} <span>· 방향키: ${escapeHtml(navigationLabel)}</span>`;
        frame.setAttribute('aria-label', `${frame.dataset.baseLabel || '차트'} 현재 선택 ${label}`);
        const chartX = finiteOrNull(point.dataset.chartX);
        if (selectionGuide && chartX !== null) {
          selectionGuide.removeAttribute('hidden');
          selectionGuide.setAttribute('x1', chartX);
          selectionGuide.setAttribute('x2', chartX);
        }
        updateLegendState();
      };
      const pinCurrentSelection = () => {
        pinnedSelection = { seriesIndex, pointIndex };
        update();
      };
      const restorePinnedSelection = () => {
        if (!pinnedSelection) {
          clearSelection();
          return;
        }
        seriesIndex = pinnedSelection.seriesIndex;
        pointIndex = pinnedSelection.pointIndex;
        update();
      };
      const chartPointerX = (event) => {
        const svg = frame.querySelector('svg');
        if (!svg?.createSVGPoint || !svg.getScreenCTM) return null;
        const matrix = svg.getScreenCTM();
        if (!matrix) return null;
        try {
          const pointer = svg.createSVGPoint();
          pointer.x = event.clientX;
          pointer.y = event.clientY;
          return pointer.matrixTransform(matrix.inverse()).x;
        } catch {
          return null;
        }
      };
      const closestPointIndexByX = (points, targetX) => {
        if (!Number.isFinite(targetX)) return Math.max(points.length - 1, 0);
        return points.reduce((bestIndex, point, index) => {
          const distance = Math.abs(numberOr(point.dataset.chartX, targetX) - targetX);
          const bestDistance = Math.abs(numberOr(points[bestIndex]?.dataset.chartX, targetX) - targetX);
          return distance < bestDistance ? index : bestIndex;
        }, 0);
      };

      frame.addEventListener('focus', update);
      frame.addEventListener('keydown', (event) => {
        if (selectors.pointerPreview && event.key === 'Escape') {
          event.preventDefault();
          pinnedSelection = null;
          clearSelection();
          return;
        }
        const points = pointsForSeries(seriesIndex);
        if (!points.length) return;
        const currentDate = points[pointIndex]?.dataset.date || '';
        if (event.key === 'ArrowLeft') pointIndex = Math.max(0, pointIndex - 1);
        else if (event.key === 'ArrowRight') pointIndex = Math.min(points.length - 1, pointIndex + 1);
        else if (event.key === 'Home') pointIndex = 0;
        else if (event.key === 'End') pointIndex = points.length - 1;
        else if (event.key === 'ArrowUp' || event.key === 'ArrowDown') {
          const direction = event.key === 'ArrowUp' ? -1 : 1;
          seriesIndex = (seriesIndex + direction + seriesGroups.length) % seriesGroups.length;
          pointIndex = closestPointIndex(pointsForSeries(seriesIndex), currentDate);
        } else {
          return;
        }
        event.preventDefault();
        if (selectors.pointerPreview) pinCurrentSelection();
        else update();
      });

      if (!selectors.pointerPreview) return;

      frame.addEventListener('pointerleave', restorePinnedSelection);
      frame.addEventListener('blur', restorePinnedSelection);
      seriesGroups.forEach((series, nextSeriesIndex) => {
        const points = pointsForSeries(nextSeriesIndex);
        points.forEach((point, nextPointIndex) => {
          point.addEventListener('pointerenter', () => {
            seriesIndex = nextSeriesIndex;
            pointIndex = nextPointIndex;
            update();
          });
          point.addEventListener('click', (event) => {
            event.stopPropagation();
            seriesIndex = nextSeriesIndex;
            pointIndex = nextPointIndex;
            pinCurrentSelection();
          });
        });

        if (!selectors.hitSelector) return;
        const hitTarget = series.querySelector(selectors.hitSelector);
        if (!hitTarget) return;
        const previewAtPointer = (event, shouldPin = false) => {
          const chartX = chartPointerX(event);
          seriesIndex = nextSeriesIndex;
          pointIndex = closestPointIndexByX(points, chartX);
          if (shouldPin) pinCurrentSelection();
          else update();
        };
        hitTarget.addEventListener('pointermove', (event) => previewAtPointer(event));
        hitTarget.addEventListener('click', (event) => previewAtPointer(event, true));
      });

      legendButtons.forEach((button) => {
        const previewLegendSeries = () => {
          const nextSeriesIndex = Number(button.dataset.seriesIndex);
          if (!Number.isInteger(nextSeriesIndex) || !seriesGroups[nextSeriesIndex]) return;
          const currentDate = pinnedSelection
            ? pointsForSeries(pinnedSelection.seriesIndex)[pinnedSelection.pointIndex]?.dataset.date
            : pointsForSeries(seriesIndex)[pointIndex]?.dataset.date;
          seriesIndex = nextSeriesIndex;
          pointIndex = closestPointIndex(pointsForSeries(seriesIndex), currentDate);
          update();
        };
        button.addEventListener('pointerenter', previewLegendSeries);
        button.addEventListener('pointerleave', restorePinnedSelection);
        button.addEventListener('focus', previewLegendSeries);
        button.addEventListener('blur', restorePinnedSelection);
        button.addEventListener('click', () => {
          previewLegendSeries();
          pinCurrentSelection();
        });
      });
    });
  }

  function splitChartPointSegments(points) {
    const segments = [];
    let current = [];
    asArray(points).forEach((point) => {
      if (point && Number.isFinite(Date.parse(point.date)) && Number.isFinite(point.value)) {
        current.push(point);
      } else if (current.length) {
        segments.push(current);
        current = [];
      }
    });
    if (current.length) segments.push(current);
    return segments;
  }

  function renderMetricCards(selector, entries) {
    const target = $(selector);
    if (!target) return;
    target.replaceChildren(...entries.map(([label, value]) => {
      const item = document.createElement('div');
      item.className = 'metric-card';
      item.innerHTML = `<span>${escapeHtml(label)}</span><strong>${escapeHtml(value || '확인 불가')}</strong>`;
      return item;
    }));
  }

  function renderMetricBadges(selector, labels) {
    const target = $(selector);
    if (!target) return;
    target.replaceChildren(...labels.map((label) => {
      const item = document.createElement('span');
      item.className = 'badge';
      item.textContent = label;
      return item;
    }));
  }

  function renderRows(selector, rows, mapper, colspan) {
    const target = $(selector);
    if (!target) return;
    if (!rows.length) {
      target.innerHTML = `<tr><td colspan="${colspan}">표시할 데이터가 없습니다. 원본 페이지를 확인해주세요.</td></tr>`;
      return;
    }
    target.replaceChildren(...rows.map((row) => {
      const tr = document.createElement('tr');
      mapper(row).forEach((value) => {
        const td = document.createElement('td');
        if (value instanceof Node) td.appendChild(value);
        else td.textContent = value === null || value === undefined || value === '' ? '-' : String(value);
        tr.appendChild(td);
      });
      return tr;
    }));
  }

  function dramProductLabel(name) {
    const raw = String(name || '');
    const clean = raw.replace(/ · TrendForce daily$/, '');
    const match = clean.match(/^(DDR[345] \d+Gb)\s+\(?([\d.]+[GM]x\d+)\)?\s+(\d+(?:\/\d+)?|eTT)$/);
    return match ? { name: match[1], spec: `${match[3]} · ${match[2].replace('x', '×')}`, full: raw } : { name: clean, spec: '', full: raw };
  }

  function dramCompactName(name) {
    const label = dramProductLabel(name);
    return [label.name, label.spec].filter(Boolean).join(' · ');
  }

  let dramChartObserver;
  function renderDramChart(selector, series) {
    const target = $(selector);
    if (!target) return;
    const chartSeries = normalizeChartSeries(series);
    target.classList.add('dram-chart-collection');
    if (!chartSeries.length) {
      target.innerHTML = '<div class="skeleton-line">표시할 D램 가격 그래프 데이터가 없습니다.</div>';
      return;
    }

    const sourceBuckets = new Map();
    chartSeries.forEach((item) => {
      const source = stringOr(item.source, 'unknown');
      if (!sourceBuckets.has(source)) sourceBuckets.set(source, []);
      sourceBuckets.get(source).push(item);
    });
    const sourceEntries = [...sourceBuckets.entries()];
    dramChartObserver?.disconnect();
    let lastWidth = 0;
    const draw = () => {
      const width = Math.max(220, Math.min(1240, Math.round((target.clientWidth || 980) - 32)));
      if (Math.abs(width - lastWidth) < 2) return;
      lastWidth = width;
      const modes = [...target.querySelectorAll('.dram-source-card')].map((card) => card.dataset.dramScaleMode);
      target.innerHTML = `<div class="dram-source-grid">${sourceEntries.map(([source, sourceSeries], index) => renderDramSourceChart(source, sourceSeries, modes[index], width)).join('')}</div>`;
      const cards = [...target.querySelectorAll('.dram-source-card')];
      sourceEntries.forEach(([source, sourceSeries], index) => bindDramSourceCard(cards[index], source, sourceSeries, width));
    };
    draw();
    if (typeof ResizeObserver !== 'undefined') { dramChartObserver = new ResizeObserver(draw); dramChartObserver.observe(target); }
  }

  function bindDramSourceCard(card, source, chartSeries, width) {
    if (!card) return;
    bindChartKeyboardFrames(card, {
      frameSelector: '.dram-chart-frame',
      seriesSelector: '.dram-series',
      pointSelector: '.dram-data-point',
      readoutSelector: '.dram-chart-readout',
      navigationLabel: '날짜/제품',
      pointerPreview: true,
      hitSelector: '.dram-series-hit',
      legendSelector: '.dram-legend-button',
      guideSelector: '.dram-selection-guide',
    });
    card.querySelectorAll('[data-dram-scale]').forEach((button) => {
      button.addEventListener('click', () => {
        const nextMode = button.dataset.dramScale === 'indexed' ? 'indexed' : 'price';
        if (nextMode === card.dataset.dramScaleMode) return;
        const restoreFocus = document.activeElement === button;
        const template = document.createElement('template');
        template.innerHTML = renderDramSourceChart(source, chartSeries, nextMode, width).trim();
        const replacement = template.content.firstElementChild;
        if (!replacement) return;
        card.replaceWith(replacement);
        bindDramSourceCard(replacement, source, chartSeries, width);
        if (restoreFocus) {
          queueMicrotask(() => replacement.querySelector(`[data-dram-scale="${nextMode}"]`)?.focus({ preventScroll: true }));
        }
      });
    });
  }

  function renderDramSourceChart(source, chartSeries, scaleMode = 'price', chartWidth = 920) {
    const normalizedSeries = normalizeChartSeries(chartSeries);
    const canIndex = normalizedSeries.every((item) => Number(item.points[0]?.[1]) !== 0);
    const mode = scaleMode === 'indexed' && canIndex ? 'indexed' : 'price';
    const displaySeries = normalizedSeries.map((item) => {
      const baseline = Number(item.points[0][1]);
      return {
        ...item,
        points: item.points.map(([date, value]) => {
          const numericValue = Number(value);
          return {
            date,
            value: numericValue,
            plotValue: mode === 'indexed' ? (numericValue / baseline) * 100 : numericValue,
          };
        }),
      };
    });
    const points = displaySeries.flatMap((item) => item.points);
    const dates = points.map((point) => Date.parse(point.date)).filter(Number.isFinite);
    const values = points.map((point) => point.plotValue).filter(Number.isFinite);
    const minDate = Math.min(...dates);
    const maxDate = Math.max(...dates);
    const minValue = Math.min(...values);
    const maxValue = Math.max(...values);
    const yTicks = buildDramAxisTicks(minValue, maxValue, 6);
    const yMin = yTicks[0] ?? Math.floor(minValue);
    const yMax = yTicks.at(-1) ?? Math.ceil(maxValue);

    const width = Math.max(220, chartWidth);
    const compact = width < 600;
    const height = compact ? 280 : 330;
    const margin = { top: 28, right: compact ? 12 : 20, bottom: 40, left: compact ? 38 : 54 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;
    const x = (date) => margin.left + ((Date.parse(date) - minDate) / Math.max(maxDate - minDate, 1)) * innerWidth;
    const y = (value) => margin.top + (1 - ((value - yMin) / Math.max(yMax - yMin, 1))) * innerHeight;

    const grid = yTicks.map((tick) => {
      const yy = y(tick);
      return `<g><line x1="${margin.left}" x2="${width - margin.right}" y1="${yy}" y2="${yy}" stroke="#d9e2f1"/><text x="${margin.left - 12}" y="${yy + 4}" text-anchor="end" fill="#9aa4b2" font-size="12">${formatInteger(tick)}</text></g>`;
    }).join('');

    const allDates = [...new Set(points.map((point) => point.date))].sort();
    const tickCount = Math.min(allDates.length, Math.max(2, Math.floor(innerWidth / 150) + 1));
    const tickIndexes = [...new Set(Array.from({ length: tickCount }, (_, index) => Math.round((index / Math.max(tickCount - 1, 1)) * (allDates.length - 1))))];
    const xTicks = tickIndexes.map((dateIndex) => {
      const date = allDates[dateIndex];
      const anchor = dateIndex === 0 ? 'start' : dateIndex === allDates.length - 1 ? 'end' : 'middle';
      return `<text x="${x(date).toFixed(1)}" y="${height - 22}" text-anchor="${anchor}" fill="#9aa4b2" font-size="12">${escapeHtml(compact ? date.slice(5).replace('-', '.') : date)}</text>`;
    }).join('');

    const paths = displaySeries.map((item, index) => {
      const color = COLORS[index % COLORS.length];
      const dash = DRAM_DASHES[index % DRAM_DASHES.length];
      const pathData = item.points.map((point, pointIndex) => `${pointIndex === 0 ? 'M' : 'L'} ${x(point.date).toFixed(1)} ${y(point.plotValue).toFixed(1)}`).join(' ');
      const circles = item.points.map((point, pointIndex) => {
        const indexContext = mode === 'indexed' ? ` · 시작=100 지수 ${formatNumber(point.plotValue)}` : '';
        const keyboardLabel = `${dramCompactName(item.name)} · ${point.date} · ${formatNumber(point.value)} USD${indexContext}`;
        const pointX = x(point.date).toFixed(1);
        const pointY = y(point.plotValue).toFixed(1);
        return `<circle class="dram-data-point${pointIndex === item.points.length - 1 ? ' endpoint' : ''}" cx="${pointX}" cy="${pointY}" r="${pointIndex === item.points.length - 1 ? '4.2' : '3.3'}" fill="${color}" data-series-index="${index}" data-point-index="${pointIndex}" data-date="${escapeAttribute(point.date)}" data-chart-x="${pointX}" data-keyboard-label="${escapeAttribute(keyboardLabel)}"/>`;
      }).join('');
      const dashAttribute = dash ? ` stroke-dasharray="${dash}"` : '';
      return `<g class="dram-series series-color-${index % COLORS.length}" data-series-index="${index}" data-series-label="${escapeAttribute(item.name)}" style="--series-color:${color}"><path class="dram-series-hit" d="${pathData}" fill="none" stroke="transparent"/><path class="dram-series-line" d="${pathData}" fill="none" stroke="${color}"${dashAttribute}/>${circles}</g>`;
    }).join('');

    const legend = displaySeries.map((item, index) => {
      const dash = DRAM_DASHES[index % DRAM_DASHES.length];
      const dashAttribute = dash ? ` stroke-dasharray="${dash}"` : '';
      const label = dramProductLabel(item.name);
      const latest = item.points.at(-1);
      return `
      <button type="button" class="dram-legend-button" title="${escapeAttribute(item.name)}" data-series-index="${index}" aria-pressed="false" aria-label="${escapeAttribute(`${item.name} 계열 선택`)}">
        <svg viewBox="0 0 30 10" aria-hidden="true"><line x1="1" x2="29" y1="5" y2="5" stroke="${COLORS[index % COLORS.length]}" stroke-width="3"${dashAttribute}/></svg>
        <span class="dram-product-name"><strong>${escapeHtml(label.name)}</strong><small>${escapeHtml(label.spec)}</small></span><span class="dram-product-price">${escapeHtml(formatNumber(latest?.value))}<small>USD</small></span>
      </button>
    `;
    }).join('');

    const sourceName = dramSourceLabel(source);
    const firstDate = allDates[0] || '';
    const lastDate = allDates.at(-1) || '';
    const initialSeries = displaySeries[0];
    const initialPoint = initialSeries?.points.at(-1);
    const scaleContext = mode === 'indexed' ? ` · 시작=100 지수 ${formatNumber(initialPoint?.plotValue)}` : '';
    const initialReadout = initialSeries && initialPoint
      ? `${dramCompactName(initialSeries.name)} · ${initialPoint.date} · ${formatNumber(initialPoint.value)} USD${scaleContext}`
      : '차트 값을 확인할 수 없습니다.';
    const modeLabel = mode === 'indexed' ? '변화율 비교, 각 제품 첫 관측 100 기준' : '가격, USD';
    const frameLabel = `${sourceName} D램 일별 ${modeLabel}. 좌우 방향키로 날짜, 위아래 방향키로 제품을 탐색합니다.`;
    const sourceId = String(source || 'unknown').toLowerCase().replace(/[^a-z0-9_-]+/g, '-');
    const titleId = `dram-${sourceId}-${mode}-title`;
    const descId = `dram-${sourceId}-${mode}-desc`;
    return `<article class="dram-source-card" data-dram-source="${escapeAttribute(source)}" data-dram-scale-mode="${mode}">
      <div class="dram-source-heading">
        <div><h4>${escapeHtml(sourceName)}</h4><p>${escapeHtml(firstDate)} — ${escapeHtml(lastDate)}</p></div>
      </div>
      <div class="dram-chart-toolbar">
        <p class="chart-keyboard-readout dram-chart-readout" aria-live="polite">${escapeHtml(initialReadout)}</p>
        <div class="dram-scale-control" role="group" aria-label="D램 차트 표시 방식">
          <button type="button" data-dram-scale="price" aria-pressed="${mode === 'price'}">가격 (USD)</button>
          <button type="button" data-dram-scale="indexed" aria-pressed="${mode === 'indexed'}">첫 관측 = 100</button>
        </div>
      </div>
      <div class="chart-legend dram-legend" role="group" aria-label="D램 제품 계열 선택">${legend}</div>
      <div class="dram-chart-frame" tabindex="0" role="group" aria-label="${escapeAttribute(frameLabel)}" aria-keyshortcuts="ArrowLeft ArrowRight ArrowUp ArrowDown Home End Escape" data-base-label="${escapeAttribute(frameLabel)}">
        <svg viewBox="0 0 ${width} ${height}" role="img" aria-labelledby="${titleId} ${descId}">
          <title id="${titleId}">${escapeHtml(`${sourceName} D램 일별 ${modeLabel}`)}</title>
          <desc id="${descId}">${escapeHtml(`${firstDate}부터 ${lastDate}까지 ${displaySeries.length}개 제품, ${points.length}개 관측치를 비교합니다. 정확값은 차트 밖 선택값 영역에서 확인합니다.`)}</desc>
          <rect x="0" y="0" width="${width}" height="${height}" fill="transparent"/>
          <text x="${margin.left}" y="18" fill="#d8dee8" font-size="13" font-weight="700">${mode === 'indexed' ? '상대 변화 · 첫 관측=100' : '일별 가격 · USD'}</text>
          ${grid}
          <line x1="${margin.left}" x2="${width - margin.right}" y1="${height - margin.bottom}" y2="${height - margin.bottom}" stroke="#3b4556"/>
          <line x1="${margin.left}" x2="${margin.left}" y1="${margin.top}" y2="${height - margin.bottom}" stroke="#3b4556"/>
          ${xTicks}
          <line class="dram-selection-guide" x1="${margin.left}" x2="${margin.left}" y1="${margin.top}" y2="${height - margin.bottom}" hidden/>
          ${paths}
        </svg>
      </div>
    </article>`;
  }

  function dramSourceLabel(source) {
    const labels = { trendforce: 'TrendForce', memorymarket: 'MemoryMarket', dramexchange: 'DRAMeXchange' };
    return labels[String(source || '').toLowerCase()] || (source === 'unknown' ? 'Source not specified' : source);
  }

  function latestSeriesPoint(series) {
    return asArray(series)
      .flatMap((item) => asArray(item.points).map(([date, value]) => ({ name: item.name, date, value: Number(value) })))
      .filter((point) => point.date && Number.isFinite(point.value))
      .sort((a, b) => b.date.localeCompare(a.date))[0] || null;
  }

  function normalizeChartSeries(series) {
    return asArray(series)
      .map((item) => ({
        ...item,
        points: asArray(item.points).filter(([date, value]) => isValidChartPoint(date, value)),
      }))
      .filter((item) => item.points.length);
  }

  function isValidChartPoint(date, value) {
    return Boolean(date) && Number.isFinite(Date.parse(date)) && Number.isFinite(Number(value));
  }

  function setStatus(selector, text, mode) {
    const target = $(selector);
    if (!target) return;
    target.textContent = text;
    target.classList.toggle('warning', mode === 'fallback');
    target.classList.toggle('error', mode === 'error');
  }

  function buildStatusText(mode, generatedAt, error, sourceStatus, dataAsOf = '') {
    const freshness = dataAsOf
      ? `기준일 ${formatMaybeDate(dataAsOf)} · 업데이트 ${formatFreshness(generatedAt)}`
      : `업데이트 ${formatFreshness(generatedAt)}`;
    if (mode === 'live') return `라이브 공개 JSON 기준 · ${freshness} · ${sourceStatus || '정상'}`;
    return `공개 JSON을 읽지 못해 fallback 표시 중 · ${freshness} · 사유: ${error || sourceStatus || '스키마/네트워크 확인 필요'}`;
  }

  function normalizeMomentumFallback() {
    return momentumUnavailable(
      'Momentum 공개 JSON을 읽지 못해 보유 종목을 표시하지 않습니다.',
      'momentum_public_json_unavailable',
    );
  }

  function normalizeDramFallback() {
    return {
      generatedAt: FALLBACK_SNAPSHOT.dram.generatedAt,
      observationCount: FALLBACK_SNAPSHOT.dram.series.reduce((sum, item) => sum + item.points.length, 0),
      status: FALLBACK_SNAPSHOT.dram.status,
      series: FALLBACK_SNAPSHOT.dram.series,
    };
  }

  function normalizeBestFallback() {
    return { ...FALLBACK_SNAPSHOT.best };
  }

  function normalizeEtfFallback() {
    return {
      generatedAt: FALLBACK_SNAPSHOT.etf.generatedAt,
      status: FALLBACK_SNAPSHOT.etf.status,
      rows: FALLBACK_SNAPSHOT.etf.rows,
    };
  }

  function normalizeSoxFallback() {
    return {
      ...FALLBACK_SNAPSHOT.sox,
      rows: FALLBACK_SNAPSHOT.sox.rows,
      allRows: FALLBACK_SNAPSHOT.sox.rows,
      constituentCount: FALLBACK_SNAPSHOT.sox.rows.length,
      topWeight: FALLBACK_SNAPSHOT.sox.rows.reduce((best, row) => numberOr(row.weight, -1) > numberOr(best?.weight, -1) ? row : best, null),
      entities: FALLBACK_SNAPSHOT.sox.entities,
      meta: FALLBACK_SNAPSHOT.sox.meta,
    };
  }

  function normalizeFearAndGreedUnavailable() {
    return {
      unavailable: true,
      generatedAt: '',
      dataAsOf: '',
      status: 'Fear & Greed 공개 요약을 사용할 수 없습니다.',
      current: {},
      rows: [],
      entities: [],
      entityPresent: false,
      meta: {
        statusState: 'unavailable',
        statusLabel: 'unavailable',
        expectedFreshnessDays: null,
        limitations: ['마지막 시장 수치를 하드코딩된 값으로 대체하지 않습니다.'],
      },
    };
  }

  function normalizeRegimeUnavailable() {
    return {
      unavailable: true,
      publicPayloadValid: false,
      generatedAt: '',
      dataAsOf: '',
      nextDate: '',
      currentState: '',
      currentStateLabel: '',
      currentConfidence: null,
      nextState: '',
      nextStateLabel: '',
      nextConfidence: null,
      transitionRisk1w: null,
      transitionRisk4w: null,
      transitionRisk13w: null,
      status: 'Regime 공개 결과를 사용할 수 없습니다.',
      rows: [],
      entities: [],
      meta: {
        statusState: 'unavailable',
        statusLabel: 'unavailable',
        dataModeLabel: '사용 불가',
        cadence: 'weekly',
        expectedFreshnessDays: PROJECT_EXPECTED_FRESHNESS_DAYS.regime,
        limitations: [],
      },
    };
  }

  function renderResearchBriefing(records = []) {
    const target = $('#research-briefing');
    if (!target) return;
    const items = records.map((record) => {
      const item = briefingItemForRecord(record);
      return item ? { ...item, project: record.project, health: visibleHealthLabel(record), tone: healthTone(record) } : null;
    }).filter(Boolean);
    target.innerHTML = items.length ? items.map((item) => `
      <a class="briefing-item ${item.tone === 'ok' ? '' : 'warning'}" href="#${escapeAttribute(panelDomId(item.project, 'panel'))}">
        <span class="briefing-kicker">${escapeHtml(item.kicker)}<span class="briefing-state">${escapeHtml(item.health)}</span></span>
        <strong>${escapeHtml(item.title)}</strong>
      </a>
    `).join('') : '';

  }

  function briefingItemForRecord(record) {
    const summary = record.summary || {};
    if (record.project.id === 'fearngreed') {
      const current = summary.current || {};
      return {
        kicker: 'Fear & Greed · KOSPI',
        title: summary.scatter ? `KOSPI ${formatSignedFear(summary.scatter.current.return1d * 100, 2)}% · 개인 ${formatSignedFear(summary.scatter.current.rawFlowTrillion, 3)}조원` : '수익률 · 개인 순매수 차트 확인 필요',
        detail: `잔차 z ${formatNumber(current.residualZ)} · R² ${formatNumber(current.rollingR2)} · ${current.primaryProxy || '226490'} ${formatFearPosition(current.position)} · 기준일 ${formatMaybeDate(summary.dataAsOf)}`,
        tone: summary.meta?.statusState === 'ok' ? '' : 'warning',
      };
    }
    if (record.project.id === 'momentum') {
      const limit = firstLimitation(summary.meta || {});
      return {
        kicker: `Momentum · ${summary.dataModeLabel || '연구 데이터'}`,
        title: `${summary.factor || '-'} · 종합 ${formatNumber(summary.compositeScore)}`,
        detail: `${summary.sourceLabel || '소스 확인 필요'} · ${momentumEvidenceLabel(summary.evidenceStatus)} · 현금 ${formatPercent(summary.cashWeight)} · 기준일 ${formatMaybeDate(summary.dataAsOf)} · ${limit}`,
        tone: summary.meta?.statusState === 'ok' ? '' : 'warning',
      };
    }
    if (record.project.id === 'dram') {
      const latest = latestSeriesPoint(summary.series);
      const limit = firstLimitation(summary.meta || {});
      return {
        kicker: 'DRAM',
        title: latest ? `${dramCompactName(latest.name)} ${formatNumber(latest.value)} USD` : '대표 가격 확인 필요',
        detail: `관측치 ${formatInteger(summary.observationCount)}개 · ${limit}`,
        tone: summary.meta?.statusState === 'ok' ? '' : 'warning',
      };
    }
    if (record.project.id === 'best') {
      const limit = firstLimitation(summary.meta || {});
      return {
        kicker: 'Best Factor',
        title: `${summary.factor || '-'} · 점수 ${formatNumber(summary.compositeScore)}`,
        detail: `데이터 기준일 ${formatMaybeDate(summary.dataEndDate)} · ${limit}`,
      };
    }
    if (record.project.id === 'etf') {
      const latestDate = maxString(asRecords(summary.rows).map((row) => row.date));
      const signalTotal = asRecords(summary.rows).reduce((sum, row) => sum + numberOr(row.signalCount, 0), 0);
      return {
        kicker: 'ETF',
        title: `${summary.rows?.length || 0}개 ETF · ${signalTotal}개 신호`,
        detail: `최근 기준일 ${formatMaybeDate(latestDate)} · ${firstLimitation(summary.meta || {})}`,
      };
    }
    if (record.project.id === 'sox') {
      const topScore = asRecords(summary.rows)[0];
      const topWeight = summary.topWeight || asRecords(summary.rows).reduce((best, row) => numberOr(row.weight, -1) > numberOr(best?.weight, -1) ? row : best, null);
      return {
        kicker: 'SOX',
        title: topScore ? `${topScore.ticker} 종합 ${formatNumber(topScore.score)} · ${formatMaybeDate(summary.dataAsOf)}` : 'SOX 요약 확인 필요',
        detail: `${topWeight ? `최대 proxy ${topWeight.ticker} ${formatPercent(topWeight.weight)} · ` : ''}${firstLimitation(summary.meta || {})}`,
        tone: summary.meta?.statusState === 'ok' ? '' : 'warning',
      };
    }
    if (record.project.id === 'regime') {
      if (summary.unavailable || !summary.publicPayloadValid) {
        return {
          kicker: 'Regime',
          title: '공개 요약 확인 필요',
          detail: '공개 결과 계약을 확인할 수 없습니다.',
          tone: 'warning',
        };
      }
      return {
        kicker: `Regime · ${summary.meta?.dataModeLabel || '공개 결과'}`,
        title: `현재 ${summary.currentStateLabel} · ${summary.currentMeasureLabel} ${formatPercent(summary.currentConfidence)} · ${formatMaybeDate(summary.nextDate)} 예측 ${summary.nextStateLabel} · 확률 ${formatPercent(summary.nextConfidence)}`,
        detail: `이탈 1주 ${formatPercent(summary.transitionRisk1w)} · 4주 ${formatPercent(summary.transitionRisk4w)} · 13주 ${formatPercent(summary.transitionRisk13w)} · 기준일 ${formatMaybeDate(summary.dataAsOf)}`,
        tone: summary.meta?.statusState === 'ok' ? '' : 'warning',
      };
    }
    return null;
  }

  function renderHubStatus(records = [], total = getPanelProjects().length) {
    const coverageTarget = $('#hub-status-coverage');
    const dateTarget = $('#hub-status-date');
    const attentionTarget = $('#hub-status-attention');
    const operationsTarget = $('#operations-summary');
    const expected = Math.max(numberOr(total, 0), records.length);
    const loaded = records.length;
    const warningCount = records.filter((record) => healthTone(record) !== 'ok').length;
    const portfolio = portfolioFreshnessSummary(records);
    const isComplete = expected > 0 && loaded === expected;

    if (coverageTarget) {
      coverageTarget.textContent = `${loaded}/${expected} ${isComplete ? '확인 완료' : '확인 중'}`;
    }
    if (dateTarget) {
      dateTarget.textContent = portfolio
        ? portfolio.mixed
          ? `${formatMaybeDate(portfolio.oldest)}–${formatMaybeDate(portfolio.newest)}`
          : formatMaybeDate(portfolio.newest)
        : '확인 중';
    }
    if (attentionTarget) {
      attentionTarget.dataset.state = loaded ? (warningCount ? 'warning' : 'ok') : 'loading';
      attentionTarget.textContent = loaded
        ? warningCount
          ? `${warningCount}개`
          : '없음'
        : '확인 중';
    }
    if (operationsTarget) {
      operationsTarget.textContent = isComplete
        ? `${loaded}개 데이터 요약 · 주의 ${warningCount}개`
        : `${loaded}/${expected}개 데이터 요약 확인 중`;
    }
  }

  function renderDataHealth(records = []) {
    const target = $('#data-health');
    if (!target) return;
    const portfolio = portfolioFreshnessSummary(records);
    const portfolioRow = portfolio ? `
      <article class="health-item ${portfolio.mixed ? 'warn' : 'ok'}">
        <div>
          <strong>전체 기준일</strong>
          <span>${portfolio.mixed ? '혼합' : '일치'}</span>
        </div>
        <p>${escapeHtml(portfolio.label)}</p>
      </article>
    ` : '';
    const rows = records.map((record) => `
      <article class="health-item ${healthTone(record)}">
        <div>
          <strong>${escapeHtml(record.project.shortName)}</strong>
          <span>${escapeHtml(healthLabel(record))}</span>
        </div>
        <p>${escapeHtml(recordFreshnessText(record))}</p>
        <small>${escapeHtml(`${formatBytes(record.payloadBytes)} · ${record.sourceCount}개 JSON · ${record.summary?.meta?.cadence || 'cadence 확인 필요'} · freshness ${formatInteger(expectedFreshnessDays(record))}일${record.error || record.summary?.scatterError || record.summary?.priceError || record.summary?.trendError || record.summary?.quadrantError ? ` · ${record.error || record.summary.scatterError || record.summary.priceError || record.summary.trendError || record.summary.quadrantError}` : ''}`)}</small>
        <div class="source-links"><a href="${escapeAttribute(record.project.url)}">원본 페이지</a>${Object.entries(PANEL_ADAPTERS[record.project.panelAdapter]?.sourceUrls || {}).map(([key, url]) => `<a href="${escapeAttribute(url)}">${escapeHtml(key)} JSON</a>`).join('')}</div>
        ${safeAutomationUrl(record.summary?.meta?.automation?.workflowUrl) ? `<a class="health-link" href="${escapeAttribute(safeAutomationUrl(record.summary.meta.automation.workflowUrl))}" rel="noopener noreferrer">자동화/수동 실행</a>` : ''}
      </article>
    `).join('');
    target.innerHTML = portfolioRow || rows ? `${portfolioRow}${rows}` : '<div class="skeleton-line">데이터 상태를 표시할 수 없습니다.</div>';
  }

  function visibleHealthLabel(record) {
    if (record.summary?.scatterError || record.summary?.priceError || record.summary?.trendError || record.summary?.quadrantError) return '차트 확인 필요';
    if (record.summary?.unavailable || record.summary?.meta?.statusState === 'unavailable') return '산출 불가';
    if (!record.metadataMismatch && record.mode === 'live' && !isRecordStale(record)) {
      if (record.summary?.meta?.statusState === 'degraded') return '데이터 주의';
      if (record.summary?.meta?.statusState === 'ok') return '정상';
    }
    return healthLabel(record);
  }

  function renderPanelStatus(record) {
    const target = $(panelSelector(record.project, 'status'));
    if (!target) return;
    const summary = record.summary || {};
    const observedDate = stringOr(summary.meta?.minDataAsOf, summary.minDataAsOf, summaryDataAsOf(summary), record.dataAsOf, '');
    const dateLabel = observedDate ? `기준일 ${formatMaybeDate(observedDate)}` : `업데이트 ${formatFreshness(record.generatedAt || summary.generatedAt)}`;
    const dataMode = record.project.id === 'momentum' ? summary.dataModeLabel : '';
    target.textContent = [dateLabel, visibleHealthLabel(record), dataMode].filter(Boolean).join(' · ');
    target.classList.toggle('warning', healthTone(record) !== 'ok');
    target.classList.toggle('error', record.summary?.unavailable === true);
  }


  function portfolioFreshnessSummary(records = []) {
    const dated = records.map((record) => ({
      name: record?.project?.shortName || record?.project?.id || 'Project',
      date: recordFreshnessDate(record),
    })).filter((item) => item.date);
    if (!dated.length) return null;
    const dates = dated.map((item) => item.date).sort();
    const oldest = dates[0];
    const newest = dates.at(-1);
    const mixed = oldest !== newest;
    const label = mixed
      ? `혼합 기준일: ${formatMaybeDate(oldest)} ~ ${formatMaybeDate(newest)} · ${dated.map((item) => `${item.name} ${formatMaybeDate(item.date)}`).join(' / ')}`
      : `모든 패널 기준일 ${formatMaybeDate(newest)}로 정렬`;
    return { oldest, newest, mixed, label, records: dated };
  }

  function healthTone(record) {
    if (record.summary?.scatterError || record.summary?.priceError || record.summary?.trendError || record.summary?.quadrantError) return 'warn';
    if (record.metadataMismatch) return 'warn';
    if (record.mode !== 'live') return 'warn';
    if (isRecordStale(record)) return 'warn';
    if (['demo', 'degraded', 'stale', 'unavailable', 'ruin'].includes(record.summary?.meta?.statusState)) return 'warn';
    return 'ok';
  }

  function healthLabel(record) {
    if (record.summary?.scatterError || record.summary?.priceError || record.summary?.trendError || record.summary?.quadrantError) return '차트 확인 필요';
    const state = record.summary?.meta?.statusState;
    if (record.metadataMismatch) return '메타데이터 불일치';
    if (record.mode !== 'live') return '대체 데이터';
    if (isRecordStale(record)) return '갱신 지연';
    if (record.summary?.meta?.dataModeLabel) return record.summary.meta.dataModeLabel;
    if (state === 'ok') return '정상';
    if (state === 'published') return '게시 데이터';
    if (state === 'live_api') return '즉시조회';
    if (state === 'degraded') return '주의';
    if (state === 'stale') return '갱신 지연';
    if (state === 'unavailable') return '산출 불가';
    if (state === 'ruin') return '파산 경로';
    if (state) return state;
    return '실시간 공개본';
  }

  function isRecordStale(record) {
    const expectedDays = expectedFreshnessDays(record);
    const freshnessDate = Date.parse(recordFreshnessDate(record));
    if (expectedDays === null || !Number.isFinite(freshnessDate)) return false;
    const days = (Date.now() - freshnessDate) / (24 * 60 * 60 * 1000);
    return days > expectedDays;
  }

  function recordFreshnessDate(record) {
    const summary = isRecord(record?.summary) ? record.summary : {};
    return stringOr(
      summary.meta?.minDataAsOf,
      summary.minDataAsOf,
      summaryDataAsOf(summary),
      record?.dataAsOf,
      record?.generatedAt,
      summary.generatedAt,
      '',
    );
  }

  function summaryDataAsOf(summary) {
    if (!isRecord(summary)) return '';
    return stringOr(
      summary.meta?.dataAsOf,
      summary.dataAsOf,
      summary.dataEndDate,
      maxString(asRecords(summary.rows).map((row) => row.date)),
      ''
    );
  }

  function recordFreshnessText(record) {
    const minimum = stringOr(record?.summary?.meta?.minDataAsOf, record?.summary?.minDataAsOf, '');
    const maximum = stringOr(record?.summary?.meta?.maxDataAsOf, record?.summary?.maxDataAsOf, '');
    const dataAsOf = summaryDataAsOf(record?.summary) || record?.dataAsOf || '';
    const generatedAt = stringOr(record?.generatedAt, record?.summary?.generatedAt, '');
    if (minimum && maximum && minimum !== maximum) {
      return `자산별 기준일 ${formatMaybeDate(minimum)}–${formatMaybeDate(maximum)} · 업데이트 ${formatFreshness(generatedAt)}`;
    }
    if (dataAsOf) return `기준일 ${formatMaybeDate(dataAsOf)} · 업데이트 ${formatFreshness(generatedAt)}`;
    return `업데이트 ${formatFreshness(generatedAt)}`;
  }

  function expectedFreshnessDays(record) {
    return finiteOrNull(record?.summary?.meta?.expectedFreshnessDays)
      ?? finiteOrNull(PROJECT_EXPECTED_FRESHNESS_DAYS[record?.project?.id]);
  }

  function safeAutomationUrl(value) {
    if (!value) return '';
    try {
      const url = new URL(String(value), 'https://sonchanggi.github.io/');
      const host = url.hostname.toLowerCase();
      const githubSubdomain = host.endsWith('.github.com');
      if (url.protocol !== 'https:' || (!SAFE_AUTOMATION_HOSTS.has(host) && !githubSubdomain)) return '';
      return url.href;
    } catch {
      return '';
    }
  }

  function bindWatchlist(records = []) {
    renderWatchlistResults(records, parseWatchlistTokens($('#watchlist-input')?.value || ''));
    if (watchlistBound) return;
    const form = $('#watchlist-form');
    const input = $('#watchlist-input');
    if (!form || !input) return;
    form.addEventListener('submit', (event) => {
      event.preventDefault();
      renderWatchlistResults([...PANEL_RECORDS.values()], parseWatchlistTokens(input.value));
    });
    input.addEventListener('input', () => {
      renderWatchlistResults([...PANEL_RECORDS.values()], parseWatchlistTokens(input.value));
    });
    watchlistBound = true;
  }

  function parseWatchlistTokens(value) {
    return String(value || '')
      .split(/[,\s]+/u)
      .map((item) => item.trim().toUpperCase())
      .filter(Boolean)
      .slice(0, 12);
  }

  function renderWatchlistResults(records = [], tokens = []) {
    const target = $('#watchlist-results');
    if (!target) return;
    if (!tokens.length) {
      target.innerHTML = '<p class="muted">예: <button type="button" data-watch-token="NVDA">NVDA</button> <button type="button" data-watch-token="AMD">AMD</button> <button type="button" data-watch-token="DRAM">DRAM</button> <button type="button" data-watch-token="AI">AI</button></p>';
      target.querySelectorAll('[data-watch-token]').forEach((button) => {
        button.addEventListener('click', () => {
          const input = $('#watchlist-input');
          if (input) input.value = button.getAttribute('data-watch-token') || '';
          renderWatchlistResults([...PANEL_RECORDS.values()], parseWatchlistTokens(input?.value));
        });
      });
      return;
    }
    const matches = tokens.flatMap((token) => watchlistMatchesForToken(records, token));
    if (!matches.length) {
      target.innerHTML = `<p class="muted">${escapeHtml(tokens.join(', '))} · 검색 결과 없음</p>`;
      return;
    }
    target.innerHTML = matches.slice(0, 24).map((match) => `
      <article class="watch-match ${match.tone || ''}">
        <span>${escapeHtml(match.project)}</span>
        <strong>${escapeHtml(match.label)}</strong>
        <p>${escapeHtml(match.detail)}</p>
      </article>
    `).join('');
  }

  function watchlistMatchesForToken(records, token) {
    const matches = [];
    for (const record of records) {
      const project = record.project.shortName;
      const meta = record.summary?.meta || {};
      const genericEntities = asRecords(record.summary?.entities).length ? asRecords(record.summary.entities) : [];
      genericEntities.forEach((entity) => {
        const haystack = [
          entity.symbol,
          entity.name,
          entity.label,
          entity.sectorLabel,
          entity.sector,
          ...asArray(entity.themes),
          ...asArray(entity.signals),
        ].join(' ').toUpperCase();
        if (haystack.includes(token)) {
          matches.push({
            project,
            matchKey: summaryEntityIdentity(record.project.id, entity),
            label: entity.label || entity.symbol || entity.name,
            detail: entitySummaryLine(record.project.id, entity),
            limit: entity.warnings?.[0] || firstLimitation(meta),
            tone: meta.statusState === 'ok' ? '' : 'warning',
          });
        }
      });
      if (genericEntities.length) continue;
      if (record.project.id === 'momentum') {
        asRecords(record.summary.rows).forEach((row) => {
          if (String(row.symbol || '').toUpperCase().includes(token)) {
            matches.push({ project, matchKey: matchIdentity(record.project.id, row.symbol), label: `${row.symbol} · rank ${row.rank}`, detail: `${record.summary.dataModeLabel || '연구 데이터'}, Python 최고 팩터 ${record.summary.factor}, 고정 비중 방법 ${record.summary.selectedWeightingPolicy || '-'}, 현금 ${formatPercent(record.summary.cashWeight)}, 모멘텀 신호 ${formatNumber(row.signal)}, 모델 비중 ${formatPercent(row.modelWeight)}`, limit: firstLimitation(meta), tone: meta.statusState === 'ok' ? '' : 'warning' });
          }
        });
      } else if (record.project.id === 'best') {
        asRecords(record.summary.rows).forEach((row) => {
          if (String(row.ticker || '').toUpperCase().includes(token)) {
            matches.push({ project, matchKey: matchIdentity(record.project.id, row.ticker), label: `${row.ticker} · rank ${row.rank}`, detail: `팩터 ${record.summary.factor}, 비중 ${formatPercent(row.weight)}, 점수 ${formatNumber(row.score)}`, limit: firstLimitation(meta) });
          }
        });
      } else if (record.project.id === 'sox') {
        asRecords(record.summary.rows).forEach((row) => {
          const haystack = [row.ticker, row.name, row.status].join(' ').toUpperCase();
          if (haystack.includes(token)) {
            matches.push({ project, matchKey: matchIdentity(record.project.id, row.ticker), label: `${row.ticker} · rank ${row.rank}`, detail: `Proxy ${formatPercent(row.weight)} · 가격 ${formatNumber(row.priceMomentum)} / 실적 ${formatNumber(row.earningsMomentum)}`, limit: firstLimitation(meta), tone: meta.statusState === 'ok' ? '' : 'warning' });
          }
        });
      } else if (record.project.id === 'etf') {
        asRecords(record.summary.rows).forEach((etf) => {
          const etfText = [etf.name, etf.fullName, etf.code].join(' ').toUpperCase();
          asRecords(etf.top10).forEach((holding) => {
            const holdingText = [holding.ticker, holding.codeRaw, holding.name].join(' ').toUpperCase();
            if (etfText.includes(token) || holdingText.includes(token)) {
              matches.push({ project, matchKey: matchIdentity(record.project.id, holding.ticker || holding.codeRaw || holding.name), label: `${etf.name} · ${holding.ticker || holding.codeRaw || holding.name}`, detail: `TOP10 보유 비중 ${formatPercent(holding.weight)} · 기준일 ${formatMaybeDate(etf.date)}`, limit: firstLimitation(meta) });
            }
          });
        });
      } else if (record.project.id === 'dram' && ['DRAM', 'D램', 'MEMORY', '반도체'].includes(token)) {
        const latest = latestSeriesPoint(record.summary.series);
        matches.push({ project, matchKey: matchIdentity(record.project.id, 'DRAM'), label: 'DRAM 가격', detail: latest ? `${latest.name} ${formatNumber(latest.value)} USD · 메모리 업황 확인용` : '대표 가격 확인 필요', limit: firstLimitation(meta) });
      }
    }
    return dedupeMatches(matches);
  }

  function entitySummaryLine(projectId, entity) {
    const metrics = entity.metrics || {};
    const render = ENTITY_METRIC_RENDERERS[projectId];
    return render ? render(metrics) : asArray(entity.signals).join(' · ') || '공통 summary contract entity';
  }

  function dedupeMatches(matches) {
    const seen = new Set();
    return matches.filter((match) => {
      const key = match.matchKey || `${match.project}|${match.label}|${match.detail}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }

  function summaryEntityIdentity(projectId, entity) {
    const metrics = entity.metrics || {};
    if (entity.entityKey || entity.id) return matchIdentity(projectId, entity.entityKey || entity.id);
    if (projectId === 'etf') return matchIdentity(projectId, [entity.symbol || entity.label || entity.name, metrics.etf || entity.label].join('|'));
    return matchIdentity(projectId, entity.symbol || entity.label || entity.name);
  }

  function matchIdentity(projectId, value) {
    const normalized = String(value || '').trim().toUpperCase();
    return normalized ? `${projectId}|${normalized}` : '';
  }

  function formatBytes(value) {
    const bytes = finiteOrNull(value);
    if (!bytes || bytes <= 0) return '용량 확인 불가';
    if (bytes >= 1_000_000) return `${(bytes / 1_000_000).toLocaleString('ko-KR', { maximumFractionDigits: 1 })} MB`;
    if (bytes >= 1_000) return `${(bytes / 1_000).toLocaleString('ko-KR', { maximumFractionDigits: 0 })} KB`;
    return `${bytes.toLocaleString('ko-KR')} B`;
  }

  function textByteLength(text) {
    const value = String(text || '');
    return typeof TextEncoder === 'undefined' ? value.length : new TextEncoder().encode(value).length;
  }

  function coerceWeightFraction(weight, weightPercent) {
    const direct = finiteOrNull(weight);
    if (direct !== null) return direct;
    const percent = finiteOrNull(weightPercent);
    return percent === null ? null : percent / 100;
  }

  function badge(text) {
    const span = document.createElement('span');
    span.className = 'badge';
    span.textContent = text || '-';
    return span;
  }

  function formatFreshness(value) {
    if (!value) return '업데이트 시각 알 수 없음';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return `${date.toLocaleString('ko-KR', {
      timeZone: 'Asia/Seoul',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })} KST`;
  }

  function formatMaybeDate(value) {
    if (!value) return '-';
    const text = String(value);
    if (!/^\d{4}-\d{2}-\d{2}/.test(text)) return text;
    return text.slice(0, 10);
  }

  function formatPercent(value) {
    const num = finiteOrNull(value);
    if (num === null) return '-';
    return `${(num * 100).toLocaleString('ko-KR', { maximumFractionDigits: 2, minimumFractionDigits: 0 })}%`;
  }

  function formatNumber(value) {
    const num = finiteOrNull(value);
    if (num === null) return '-';
    return num.toLocaleString('ko-KR', { maximumFractionDigits: 4 });
  }

  function formatFearPosition(value) {
    const labels = {
      cash: '현금',
      long: '매수·보유',
      unavailable: '산출 불가',
    };
    return labels[value] || value || '확인 필요';
  }

  function formatInteger(value) {
    const num = finiteOrNull(value);
    if (num === null) return '-';
    return Math.round(num).toLocaleString('ko-KR');
  }

  function buildDramAxisTicks(min, max, count = 5) {
    if (!Number.isFinite(min) || !Number.isFinite(max) || count < 2) return [];
    const low = Math.floor(Math.min(min, max));
    const high = Math.ceil(Math.max(min, max));
    const pad = Math.max(1, Math.ceil((high - low) * 0.08));
    const domainMin = Math.max(0, low - pad);
    const domainMax = Math.max(high + pad, domainMin + 1);
    return buildNiceTicks(domainMin, domainMax, count, 1);
  }

  function buildEtfPercentAxisTicks(min, max, count = 5) {
    if (!Number.isFinite(min) || !Number.isFinite(max) || count < 2) return [];
    const low = Math.max(0, Math.min(min, max));
    const high = Math.max(low, Math.max(min, max));
    const observedSpan = high - low;
    const paddedSpan = Math.max(observedSpan * 1.36, 0.04);
    const midpoint = (low + high) / 2;
    let domainMin = Math.max(0, midpoint - paddedSpan / 2);
    let domainMax = domainMin + paddedSpan;
    if (domainMax < high) {
      domainMax = high;
      domainMin = Math.max(0, domainMax - paddedSpan);
    }
    return buildNiceTicks(domainMin, domainMax, count, 0.01);
  }

  function buildNiceTicks(min, max, count, minimumStep) {
    const span = Math.max(max - min, minimumStep);
    const step = niceStep(span / Math.max(count - 1, 1), minimumStep);
    const start = Math.max(0, Math.floor(min / step) * step);
    const end = Math.ceil(max / step) * step;
    const ticks = [];
    for (let tick = start; tick <= end + step / 2; tick += step) {
      ticks.push(roundTick(tick));
      if (ticks.length > count + 4) break;
    }
    return ticks.length >= 2 ? ticks : [roundTick(start), roundTick(start + step)];
  }

  function niceStep(rawStep, minimumStep) {
    if (!Number.isFinite(rawStep) || rawStep <= 0) return minimumStep;
    const magnitude = 10 ** Math.floor(Math.log10(rawStep));
    const residual = rawStep / magnitude;
    const niceResidual = residual <= 1 ? 1 : residual <= 2 ? 2 : residual <= 5 ? 5 : 10;
    return Math.max(minimumStep, niceResidual * magnitude);
  }

  function roundTick(value) {
    return Number(value.toFixed(10));
  }

  function asArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function asRecords(value) {
    return asArray(value).filter(isRecord);
  }

  function isRecord(value) {
    return value !== null && typeof value === 'object' && !Array.isArray(value);
  }

  function finiteOrNull(value) {
    if (value === null || value === undefined || value === '') return null;
    const num = Number(value);
    return Number.isFinite(num) ? num : null;
  }

  function numberOr(value, fallback) {
    const num = finiteOrNull(value);
    return num === null ? fallback : num;
  }

  function stringOr(...values) {
    for (const value of values) {
      if (value !== null && value !== undefined && String(value).trim() !== '') return String(value);
    }
    return '';
  }

  function maxString(values) {
    return values.filter(Boolean).sort().at(-1) || '';
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>"]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[char]));
  }

  function escapeAttribute(value) {
    return escapeHtml(value).replace(/'/g, '&#39;');
  }

  if (typeof globalThis !== 'undefined') {
    globalThis.__QUANT_DASHBOARD_TESTS__ = {
      parseMomentum,
      parseFearAndGreed,
      parseDram,
      parseBestFactor,
      parseEtfTracking,
      parseRegime,
      parseSox,
      renderSox,
      renderRegime,
      parseRegimePanel,
      parseRegimeTrend,
      enrichRegimeSources,
      validateRegimeHistory,
      renderRegimeTrend,
      windowedRegimeRows,
      regimeTrendGeometry,
      renderFearAndGreed,
      parseFearPanel,
      parseFearScatter,
      fearScatterGeometry,
      factorDisplayName,
      factorAllocation,
      factorWeightScale,
      parseFearPrices,
      fearPointState,
      fearPriceGeometry,
      renderFearScatter,
      parseNewsArchive,
      parseNewsBriefing,
      loadNewsSummary,
      getJsonBestEffort,
      renderPanelStatus,
      visibleHealthLabel,
      normalizeRegimeUnavailable,
      isMomentumSummaryV5,
      isMomentumDashboardV5,
      validMomentumFactorAccountingV5,
      validMomentumMarketSnapshotParity,
      validMomentumLiveProvenance,
      validMomentumFactorGridV5,
      validMomentumAbsoluteGuardrailProfile,
      validMomentumConcentrationRows,
      validMomentumSelectedConcentrationContract,
      isMomentumSummaryV4,
      isMomentumDashboardV4,
      validMomentumResultIdentity,
      matchingMomentumResultIdentity,
      momentumResultKeyForKeyParts,
      momentumCanonicalKeyPartsJson,
      momentumCanonicalRecordsSha256,
      momentumSha256Hex,
      buildDramSeries,
      isTrendforceDailyObservation,
      compactEtfHistoryPayload,
      compactEtfHistoryTailText,
      extractEtfSnapshotObjects,
      appendEtfHistoryStatus,
      etfHistoryEnrichmentFailure,
      enrichPanelSources,
      recentEtfHistory,
      resolveEtfHistoryUrl,
      buildEtfWeightSeries,
      renderEtfMiniChart,
      etfComparisonDomain,
      parseSoxPanel,
      parseSoxQuadrant,
      soxQuadrantGeometry,
      renderSoxQuadrantChart,
      soxScore,
      dramProductLabel,
      renderEtfDetailCards,
      renderResearchBriefing,
      briefingItemForRecord,
      renderHubStatus,
      renderDataHealth,
      healthTone,
      healthLabel,
      watchlistMatchesForToken,
      parseWatchlistTokens,
      resolveLoadState,
      loadProjectPanel,
      loadEtfPanel,
      parsePanelSafely,
      validateAdapterContract,
      isResearchSummary,
      summaryMeta,
      summaryEntities,
      entitySummaryLine,
      isRecordStale,
      expectedFreshnessDays,
      recordFreshnessDate,
      recordFreshnessText,
      portfolioFreshnessSummary,
      summaryDataAsOf,
      safeAutomationUrl,
      renderProjectNavigation,
      renderDashboardPanels,
      PROJECTS,
      NAVIGATION_PROJECTS,
      PANEL_ADAPTERS,
      normalizeChartSeries,
      isValidChartPoint,
      buildDramAxisTicks,
      renderDramSourceChart,
      buildEtfPercentAxisTicks,
      configuredSupabaseMetadata,
      getPublishedSnapshotMetadata,
      PLATFORM_PROJECT_IDS,
      PROJECT_EXPECTED_FRESHNESS_DAYS,
    };
  }
})();
