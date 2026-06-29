(() => {
  'use strict';

  const SAFE_AUTOMATION_HOSTS = new Set(['github.com', 'www.github.com', 'sonchanggi.github.io']);

  const ENTITY_METRIC_RENDERERS = {
    valuation: (metrics) => `현재가 ${formatNumber(metrics.price)} · DCF ${formatNumber(metrics.dcfPerShare)} · 품질 ${metrics.qualityStatus || '확인 필요'}`,
    etf: (metrics) => `${metrics.etf || 'ETF'} TOP10 비중 ${formatPercent(metrics.weight)} · 기준일 ${formatMaybeDate(metrics.date)}`,
    best: (metrics) => `팩터 ${metrics.factor || '-'} · 비중 ${formatPercent(metrics.weight)} · 점수 ${formatNumber(metrics.score)}`,
    momentum: (metrics) => `팩터 ${metrics.factor || '-'} · 신호 ${formatNumber(metrics.signal)} · 최종 비중 ${formatPercent(metrics.finalWeight)}`,
    dram: (metrics) => `${metrics.kind || '가격'} · ${formatMaybeDate(metrics.date)} · ${metrics.source || 'source N/A'}`,
    sox: (metrics) => `SOX proxy ${formatPercent(metrics.weight)} · 가격 ${formatNumber(metrics.priceMomentum)} · 실적 ${formatNumber(metrics.earningsMomentum)}`,
    riskScore: (metrics) => `Top ${formatNumber(metrics.topRiskScore)}/5 · OH ${formatNumber(metrics.ohScore)}/5 · RF ${formatNumber(metrics.rfScore)}/5`,
  };

  const PROJECTS = [
    {
      id: 'momentum',
      shortName: 'Momentum',
      title: '모멘텀 팩터 랩',
      description: '기간별 최고 모멘텀 팩터와 상위 종목 신호를 비교하는 데일리 대시보드입니다.',
      url: 'https://sonchanggi.github.io/momentum-factor-lab/',
      accent: 'MF',
      panelAdapter: 'momentum',
      panel: {
        eyebrow: 'Momentum Factor',
        title: '베스트 모멘텀 팩터 · Top 5',
        contentType: 'table',
        metricLoading: '모멘텀 데이터를 불러오는 중...',
        table: {
          caption: '모멘텀 팩터 상위 5개 종목과 표시용 비중',
          columns: ['순위', '종목', '신호', '표시용 비중', '최종 비중'],
          loadingText: '데이터를 불러오는 중...',
        },
      },
    },
    {
      id: 'dram',
      shortName: 'D램',
      title: 'D램(DRAM) 가격 랩',
      description: 'D램(DRAM) 현물가, 고정가, 주간 현물 프록시를 모니터링하는 가격 대시보드입니다.',
      url: 'https://sonchanggi.github.io/dram-price/',
      accent: 'DR',
      panelAdapter: 'dram',
      panel: {
        eyebrow: 'DRAM Price',
        title: 'TrendForce 일별 D램 가격 그래프',
        contentType: 'chart',
        metricLoading: 'D램 가격 데이터를 불러오는 중...',
        chartLabel: 'TrendForce 일별 저장 D램(DRAM) 가격 추이 그래프',
      },
    },
    {
      id: 'best',
      shortName: 'Best Factor',
      title: 'Best Factor Lab',
      description: '미국 주식 팩터 랭킹, 성과 지표, 최신 편입 종목과 비중을 확인합니다.',
      url: 'https://sonchanggi.github.io/best-factor/',
      accent: 'BF',
      panelAdapter: 'best',
      panel: {
        eyebrow: 'Best Factor',
        title: '베스트 팩터 · Top 5',
        contentType: 'table',
        metricLoading: '베스트 팩터 데이터를 불러오는 중...',
        table: {
          caption: '베스트 팩터 상위 5개 종목과 투자 비중',
          columns: ['순위', '종목', '점수', '투자 비중', '기준일'],
          loadingText: '데이터를 불러오는 중...',
        },
      },
    },
    {
      id: 'etf',
      shortName: 'ETF Tracking',
      title: 'ETF TOP10 Tracking',
      description: '한국 상장 액티브 ETF 3종의 TOP10 편입 종목, 비중 변화, 편입·편출 신호를 추적합니다.',
      url: 'https://sonchanggi.github.io/etf-tracking/',
      accent: 'ETF',
      panelAdapter: 'etf',
      panel: {
        eyebrow: 'ETF Tracking',
        title: 'ETF별 TOP10 비중 · 미니 그래프',
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
      description: '필라델피아 반도체 지수 구성종목의 프록시 비중, 가격 모멘텀, 실적 모멘텀을 함께 비교합니다.',
      url: 'https://sonchanggi.github.io/sox/',
      accent: 'SX',
      panelAdapter: 'sox',
      panel: {
        eyebrow: 'SOX Semiconductor',
        title: 'SOX 구성종목 · Momentum Top 5',
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
      id: 'risk-score',
      shortName: 'Risk Score',
      title: 'SOX Top Risk Score',
      description: 'SOX 단기 고점 위험을 과열형 OH Score와 반등 실패형 RF Score, confirmation, 5D backtest로 분리 추적합니다.',
      url: 'https://sonchanggi.github.io/quant-dashboard/risk-score/',
      accent: 'RS',
      panelAdapter: 'riskScore',
      panel: {
        eyebrow: 'SOX Top Risk',
        title: 'SOX Top Risk · OH/RF/Confirmation',
        contentType: 'table',
        metricLoading: 'Risk Score 데이터를 불러오는 중...',
        table: {
          caption: 'SOX top-risk overlay latest score and backtest context',
          columns: ['구분', '현재값', '상태', '해석', '기준일'],
          loadingText: 'Risk Score 요약 데이터를 불러오는 중...',
        },
      },
    },
    {
      id: 'port',
      shortName: 'Port',
      title: '포트폴리오 비중 Cockpit',
      description: 'ETF·주식 보유 주수와 종가 통화(USD/KRW)를 입력해 최종 비중, ETF 기초 노출, 레버리지 포함/제외, 상관관계를 확인합니다.',
      url: 'https://sonchanggi.github.io/port/',
      accent: 'PT',
    },
    {
      id: 'valuation',
      shortName: 'Valuation',
      title: '기업 가치평가 Lab',
      description: '티커별 DCF 절대가치와 PER/PBR 상대가치의 근거, 진단, 한계를 함께 확인하는 가치평가 워크스페이스입니다.',
      url: 'https://sonchanggi.github.io/valuation/',
      accent: 'VAL',
      panelAdapter: 'valuation',
      panel: {
        eyebrow: 'Valuation',
        title: '기업 가치평가 · 근거 점검 Top 5',
        contentType: 'table',
        metricLoading: '가치평가 데이터를 불러오는 중...',
        table: {
          caption: 'DCF 기준 주당가치, 현재가 괴리, 데이터 품질을 함께 보는 점검 목록',
          columns: ['티커', '섹터/테마', '현재가', 'DCF 기준', '근거/한계'],
          loadingText: '가치평가 데이터를 불러오는 중...',
        },
      },
    },
  ];

  const SUMMARY_CONTRACT = { versionField: 'schemaVersion', expectedVersion: 1, requiredKeys: ['contract', 'projectId', 'status', 'primaryEntities'] };

  const PANEL_ADAPTERS = {
    momentum: {
      sourceUrls: {
        summary: 'https://sonchanggi.github.io/momentum-factor-lab/data/summary.json',
        momentumDashboard: 'https://sonchanggi.github.io/momentum-factor-lab/data/dashboard.json',
      },
      primarySourceKey: 'summary',
      contracts: { summary: SUMMARY_CONTRACT },
      parse: (sources) => parseMomentum(sources.summary, sources.momentumDashboard),
      hasUsableData: (summary) => Boolean(summary?.rows?.length || summary?.bestFactorUnavailable),
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
      },
      primarySourceKey: 'summary',
      contracts: { summary: SUMMARY_CONTRACT },
      parse: (sources) => parseSox(sources.summary),
      hasUsableData: (summary) => Boolean(summary?.rows?.length),
      fallback: normalizeSoxFallback,
      render: renderSox,
      emptyReason: 'SOX summary did not contain usable constituents.',
    },
    riskScore: {
      sourceUrls: {
        summary: 'https://sonchanggi.github.io/quant-dashboard/risk-score/data/risk-score/risk_score_summary.json',
      },
      primarySourceKey: 'summary',
      contracts: { summary: SUMMARY_CONTRACT },
      parse: (sources) => parseRiskScore(sources.summary),
      hasUsableData: (summary) => [summary?.current?.topRiskScore, summary?.current?.ohScore, summary?.current?.rfScore].every((value) => finiteOrNull(value) !== null),
      fallback: normalizeRiskScoreFallback,
      render: renderRiskScore,
      emptyReason: 'Risk Score summary did not contain usable current score metrics.',
    },
    valuation: {
      sourceUrls: {
        summary: 'https://sonchanggi.github.io/valuation/data/summary.json',
      },
      primarySourceKey: 'summary',
      contracts: { summary: SUMMARY_CONTRACT },
      parse: (sources) => parseValuation(sources.summary),
      hasUsableData: (summary) => Boolean(summary?.rows?.length),
      fallback: normalizeValuationFallback,
      render: renderValuation,
      emptyReason: 'Valuation summary did not contain usable ticker rows.',
    },
  };

  const FALLBACK_SNAPSHOT = {
    momentum: {
      generatedAt: '2026-06-10T05:23:40+00:00',
      dataAsOf: '2026-06-09',
      factor: 'mom_9_1',
      outputLabel: 'Research signals (not tradable)',
      status: '마지막 확인 스냅샷 표시 중',
      rows: [
        { rank: 1, symbol: 'VSCO', signal: 1.2158671697, displayWeight: 0.1, finalWeight: 0 },
        { rank: 2, symbol: 'ADEA', signal: 1.1635723083, displayWeight: 0.1, finalWeight: 0 },
        { rank: 3, symbol: 'GALDY', signal: 0.3169318663, displayWeight: 0.1, finalWeight: 0 },
        { rank: 4, symbol: 'IAC', signal: 0.2593969017, displayWeight: 0.1, finalWeight: 0 },
        { rank: 5, symbol: 'SHEL', signal: 0.2107772093, displayWeight: 0.1, finalWeight: 0 },
      ],
    },
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
    riskScore: {
      generatedAt: '2026-06-30T00:00:00Z',
      dataAsOf: '2026-06-26',
      status: '마지막 Risk Score 스냅샷 표시 중',
      current: {
        date: '2026-06-26', close: 13203.57, oneDayReturn: null, vixClose: null,
        ohScore: 0, rfScore: 5, topRiskScore: 5, confirmedTopRisk: true,
        regime: 'Rebound Failure', actionLabel: 'Confirmed Red', actionLevel: 'confirmed-red',
        actionText: '가격/변동성 기반 confirmation이 켜진 red overlay 상태입니다.',
      },
      rows: [
        { label: 'Top Risk Score', value: '5/5', status: 'Confirmed Red', interpretation: 'OH/RF 중 높은 점수', date: '2026-06-26' },
        { label: 'OH Score', value: '0/5', status: 'Normal', interpretation: '과열형 setup 비활성', date: '2026-06-26' },
        { label: 'RF Score', value: '5/5', status: 'Red Zone', interpretation: '반등 실패형 lower-high warning', date: '2026-06-26' },
        { label: 'Confirmation', value: 'ON', status: 'Confirmed', interpretation: '가격/VIX confirmation', date: '2026-06-26' },
      ],
      entities: [{ id: 'sox-top-risk', symbol: 'NASDAQSOX', label: 'SOX Top Risk Score', metrics: { topRiskScore: 5, ohScore: 0, rfScore: 5, confirmedTopRisk: true }, signals: ['Confirmed Red'] }],
      meta: {
        statusState: 'fallback', statusLabel: 'Risk Score fallback snapshot', cadence: 'daily-after-market-close', expectedFreshnessDays: 7,
        limitations: ['뉴스 기반 모델이 아니며 가격/변동성 기반 risk overlay입니다.'],
      },
    },
    valuation: {
      generatedAt: '2026-06-19T14:43:32Z',
      status: '마지막 확인 스냅샷 표시 중',
      tickerCount: 21,
      sectors: ['기술', '금융', '헬스케어'],
      methodologyCount: 0,
      contractVersion: 'fallback',
      rows: [
        { ticker: 'AAPL', name: 'Apple Inc.', sectorLabel: '기술', themeTags: ['Consumer Tech', 'Services'], price: 298.01, dcfPerShare: 104.6, qualityStatus: '충분' },
        { ticker: 'MSFT', name: 'Microsoft Corporation', sectorLabel: '기술', themeTags: ['Cloud', 'AI'], price: 379.4, dcfPerShare: 223.61, qualityStatus: '충분' },
        { ticker: 'NVDA', name: 'NVIDIA Corp', sectorLabel: '기술', themeTags: ['AI', 'Semiconductors'], price: 210.69, dcfPerShare: 58.4, qualityStatus: '일부 누락' },
      ],
    },
  };

  const COLORS = ['#7dd3fc', '#86efac', '#fb7185', '#fbbf24', '#c4b5fd', '#67e8f9'];
  const PANEL_RECORDS = new Map();
  const ETF_HISTORY_WINDOW_DAYS = 31;
  const ETF_HISTORY_TAIL_BYTES = 2_400_000;
  let watchlistBound = false;
  const $ = (selector) => document.querySelector(selector);

  if (typeof document !== 'undefined') {
    document.addEventListener('DOMContentLoaded', () => {
      renderProjectNavigation();
      renderDashboardPanels();
      loadDashboardPanels();
    });
  }

  function renderProjectNavigation() {
    const topNav = $('#top-nav');
    const heroActions = $('#hero-actions');
    const projectGrid = $('#project-grid');

    if (topNav) {
      topNav.replaceChildren(...PROJECTS.map((project) => createProjectLink(project, project.shortName)));
    }

    if (heroActions) {
      heroActions.replaceChildren(...PROJECTS.map((project) => createProjectLink(project, `${project.shortName} 열기`)));
    }

    if (projectGrid) {
      projectGrid.replaceChildren(...PROJECTS.map((project) => {
        const article = document.createElement('article');
        article.className = 'project-card';
        article.innerHTML = `
          <div class="project-icon" aria-hidden="true">${escapeHtml(project.accent)}</div>
          <h3>${escapeHtml(project.title)}</h3>
          <p>${escapeHtml(project.description)}</p>
          <a href="${escapeAttribute(project.url)}" aria-label="${escapeAttribute(project.title)} 원본 페이지 열기">원본 페이지 열기</a>
        `;
        return article;
      }));
    }
  }

  function createProjectLink(project, label) {
    const link = document.createElement('a');
    link.href = project.url;
    link.textContent = label;
    link.setAttribute('data-project-id', project.id);
    return link;
  }

  function renderDashboardPanels() {
    const summaryGrid = $('#summary-grid');
    if (!summaryGrid) return;
    summaryGrid.replaceChildren(...getPanelProjects().map(createPanelShell));
  }

  function createPanelShell(project) {
    const panel = project.panel || {};
    const article = document.createElement('article');
    article.className = 'panel panel-wide';
    article.id = panelDomId(project, 'panel');
    article.setAttribute('aria-labelledby', panelDomId(project, 'title'));

    const content = panel.contentType === 'chart' ? chartPanelMarkup(project) : tablePanelMarkup(project);
    article.innerHTML = `
      <div class="panel-header">
        <div>
          <p class="eyebrow">${escapeHtml(panel.eyebrow || project.shortName)}</p>
          <h3 id="${escapeAttribute(panelDomId(project, 'title'))}">${escapeHtml(panel.title || project.title)}</h3>
        </div>
        <a class="panel-link" href="${escapeAttribute(project.url)}">원본 열기</a>
      </div>
      ${content}
      <p class="status-line" id="${escapeAttribute(panelDomId(project, 'status'))}">업데이트 확인 중</p>
    `;
    return article;
  }

  function tablePanelMarkup(project) {
    const panel = project.panel || {};
    const table = panel.table || { columns: [], caption: '', loadingText: '데이터를 불러오는 중...' };
    const columns = table.columns.map((label) => `<th scope="col">${escapeHtml(label)}</th>`).join('');
    const colspan = Math.max(table.columns.length, 1);
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
      <div class="chart-card" id="${escapeAttribute(panelDomId(project, 'chart'))}" role="img" aria-label="${escapeAttribute(panel.chartLabel || `${project.title} 차트`)}"></div>
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

  async function loadValuationPanel() {
    return loadProjectPanel('valuation');
  }

  async function loadDashboardPanels() {
    const records = (await Promise.all(getPanelProjects().map((project) => loadProjectPanel(project)))).filter(Boolean);
    PANEL_RECORDS.clear();
    records.forEach((record) => PANEL_RECORDS.set(record.project.id, record));
    renderResearchBriefing(records);
    renderDataHealth(records);
    bindWatchlist(records);
    return records;
  }

  async function loadProjectPanel(projectOrId) {
    const project = typeof projectOrId === 'string' ? projectById(projectOrId) : projectOrId;
    const adapter = project ? PANEL_ADAPTERS[project.panelAdapter] : null;
    if (!project || !adapter) return;

    const entries = await Promise.all(Object.entries(adapter.sourceUrls).map(async ([sourceKey, url]) => [sourceKey, await getJsonBestEffort(url)]));
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
    adapter.render(summary, loadState.mode, loadState.error, project);
    return {
      project,
      adapterId: project.panelAdapter,
      summary,
      mode: loadState.mode,
      error: loadState.error,
      generatedAt: summary?.generatedAt || '',
      dataAsOf: summaryDataAsOf(summary),
      payloadBytes: Object.values(fetchResults).reduce((sum, result) => sum + numberOr(result.bytes, 0), 0),
      sourceCount: Object.keys(fetchResults).length,
    };
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

  async function getJsonBestEffort(url, timeoutMs = 8500) {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
    try {
      const response = await fetch(url, { signal: controller.signal, cache: 'no-store' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const text = await response.text();
      const headerBytes = finiteOrNull(response.headers.get('content-length'));
      const bytes = headerBytes ?? textByteLength(text);
      return { ok: true, data: JSON.parse(text), url, bytes };
    } catch (error) {
      return { ok: false, error: error instanceof Error ? error.message : String(error), url };
    } finally {
      window.clearTimeout(timeout);
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
    const summaryPayload = isResearchSummary(payload, 'momentum') ? payload : null;
    const detailExpected = arguments.length >= 2;
    const detailSummary = parseMomentumDashboard(detailPayload || (summaryPayload ? null : payload), summaryPayload);
    if (detailSummary?.rows?.length) return detailSummary;

    if (summaryPayload) {
      if (detailExpected) return momentumBestFactorUnavailable(summaryPayload, detailSummary);
      const meta = summaryMeta(summaryPayload);
      const baseRows = summaryEntities(summaryPayload)
        .sort((a, b) => numberOr(a.metrics.rank, 9999) - numberOr(b.metrics.rank, 9999))
        .map((entity, index) => ({
          rank: numberOr(entity.metrics.rank, index + 1),
          symbol: stringOr(entity.symbol, entity.name, '-'),
          signal: finiteOrNull(entity.metrics.signal ?? entity.metrics.score),
          displayWeight: finiteOrNull(entity.metrics.displayWeight),
          finalWeight: finiteOrNull(entity.metrics.finalWeight),
          themes: entity.themes,
          warnings: entity.warnings,
        }));
      const rows = deriveMomentumDisplayWeights(baseRows);
      const weightSource = momentumWeightSource(rows);
      return {
        factor: stringOr(highlightValue(meta, 'best factor'), highlightValue(meta, 'factor'), meta.coverage?.bestFactor, meta.coverage?.selectedFactor, FALLBACK_SNAPSHOT.momentum.factor),
        generatedAt: meta.generatedAt,
        dataAsOf: meta.dataAsOf,
        outputLabel: stringOr(highlightValue(meta, 'output'), meta.statusLabel, 'Research signal'),
        status: appendMomentumWeightStatus(stringOr(meta.statusLabel, '공통 summary contract 표시 중'), weightSource),
        weightSource,
        rows: rows.slice(0, 5),
        entities: summaryEntities(summaryPayload),
        meta,
      };
    }

    return detailSummary || parseMomentumDashboard(payload) || {
      factor: FALLBACK_SNAPSHOT.momentum.factor,
      generatedAt: '',
      dataAsOf: '',
      outputLabel: 'Research signal',
      status: 'Momentum payload did not contain usable run data.',
      weightSource: '원천 제공 비중',
      rows: [],
      meta: {},
    };
  }

  function momentumBestFactorUnavailable(summaryPayload, detailSummary = null) {
    const meta = summaryMeta(summaryPayload);
    const detailBestFactor = detailSummary?.meta?.bestFactor && detailSummary.meta.bestFactor !== detailSummary.meta.selectedFactor
      ? detailSummary.meta.bestFactor
      : '';
    const factor = stringOr(detailBestFactor, meta.coverage?.bestFactor, 'best factor 확인 필요');
    const status = detailSummary
      ? 'Momentum dashboard.json에서 best factor 보유 종목을 확인하지 못해 selected factor summary를 표시하지 않음'
      : 'Momentum dashboard.json 미수신으로 selected factor summary를 best factor로 표시하지 않음';
    return {
      factor,
      generatedAt: stringOr(detailSummary?.generatedAt, meta.generatedAt),
      dataAsOf: stringOr(detailSummary?.dataAsOf, meta.dataAsOf),
      outputLabel: 'Best factor detail unavailable',
      status,
      weightSource: 'best factor 상세 데이터 미수신',
      rows: [],
      entities: [],
      bestFactorUnavailable: true,
      meta: {
        ...meta,
        statusState: 'warning',
        bestFactorUnavailable: true,
        degradedReasons: [...asArray(meta.degradedReasons), 'momentum best-factor dashboard detail unavailable'],
      },
    };
  }

  function parseMomentumDashboard(payload, summaryPayload = null) {
    if (!isRecord(payload)) return null;
    const runs = Array.isArray(payload.runs) ? payload.runs : [];
    if (!runs.length && !isRecord(payload.summary) && !Array.isArray(payload.holdings)) return null;

    const latestIndex = Number.isInteger(payload.latest_run_index) ? payload.latest_run_index : runs.length - 1;
    const run = runs[latestIndex] || runs.at(-1) || payload || {};
    const summary = isRecord(run.summary) ? run.summary : {};
    const leader = latestFactorLeader(run);
    const bestFactor = stringOr(leader?.best_factor, summary.best_factor);
    const selectedFactor = stringOr(summary.selected_factor, leader?.selected_factor);
    const factor = stringOr(bestFactor, summaryPayload ? '' : selectedFactor, FALLBACK_SNAPSHOT.momentum.factor);
    const requiresBestHoldings = Boolean(summaryPayload && (!bestFactor || (selectedFactor && bestFactor !== selectedFactor)));
    const bestFactorRows = bestFactor ? momentumRowsFromHoldings(run, bestFactor, leader?.window) : [];
    const latestRows = momentumRowsFromLatestOutput(run);
    const sourceRows = bestFactorRows.length ? bestFactorRows : (requiresBestHoldings ? [] : latestRows);
    const rows = deriveMomentumDisplayWeights(sourceRows);
    const weightSource = momentumWeightSource(rows);
    const meta = summaryPayload ? summaryMeta(summaryPayload) : {};
    const bestFactorStatus = factor && selectedFactor && factor !== selectedFactor ? ` · best momentum factor 기준(${factor})` : '';

    return {
      factor,
      generatedAt: stringOr(run.generated_at_utc, payload.generated_at_utc, meta.generatedAt, ''),
      dataAsOf: stringOr(summary.data_as_of, leader?.date, meta.dataAsOf, ''),
      outputLabel: stringOr(summary.recommendation_output_label, summary.recommendation_status, meta.statusLabel, 'Research signal'),
      status: appendMomentumWeightStatus(`${stringOr(summary.recommendation_output_label, meta.statusLabel, '라이브 공개 JSON 표시 중')}${bestFactorStatus}`, weightSource),
      weightSource,
      rows: rows.slice(0, 5),
      entities: summaryEntities(summaryPayload),
      meta: { ...meta, bestFactor, selectedFactor, factorLeader: leader || null },
    };
  }

  function deriveMomentumDisplayWeights(rows) {
    const records = asRecords(rows);
    const displayNeedsFallback = !records.some((row) => numberOr(row.displayWeight, 0) > 0);
    const finalNeedsFallback = !records.some((row) => numberOr(row.finalWeight, 0) > 0);
    if (!displayNeedsFallback && !finalNeedsFallback) return records;

    const signalWeights = momentumSignalWeights(records);
    return records.map((row, index) => {
      const signalWeight = signalWeights[index];
      const displayWeight = displayNeedsFallback && signalWeight !== null ? signalWeight : finiteOrNull(row.displayWeight);
      const finalWeight = finalNeedsFallback && signalWeight !== null ? signalWeight : finiteOrNull(row.finalWeight);
      return {
        ...row,
        displayWeight,
        finalWeight,
        weightSource: (displayNeedsFallback || finalNeedsFallback) && signalWeight !== null ? 'signal_normalized' : 'source',
      };
    });
  }

  function momentumSignalWeights(rows) {
    const positives = asRecords(rows).map((row) => Math.max(numberOr(row.signal, 0), 0));
    const total = positives.reduce((sum, value) => sum + value, 0);
    if (total > 0) return positives.map((value) => value / total);
    const count = positives.length;
    return count ? positives.map(() => 1 / count) : [];
  }

  function momentumWeightSource(rows) {
    return asRecords(rows).some((row) => row.weightSource === 'signal_normalized')
      ? '리서치 신호 정규화 비중'
      : '원천 제공 비중';
  }

  function appendMomentumWeightStatus(status, weightSource) {
    if (weightSource !== '리서치 신호 정규화 비중') return status;
    return `${status} · 표시/최종 비중은 양수 신호 합계 기준 dashboard 정규화`;
  }

  function momentumRowsFromLatestOutput(run) {
    return asRecords(run.latest_output_rows)
      .slice()
      .sort((a, b) => numberOr(a.rank, 9999) - numberOr(b.rank, 9999))
      .map((row, index) => ({
        rank: numberOr(row.rank, index + 1),
        symbol: stringOr(row.symbol, row.ticker, '-'),
        signal: finiteOrNull(row.score),
        displayWeight: finiteOrNull(row.proposed_weight ?? row.default_weight ?? row.pre_cap_weight),
        finalWeight: finiteOrNull(row.weight),
      }));
  }

  function momentumRowsFromHoldings(run, factor, preferredWindow = '') {
    const factorHoldings = asRecords(run.holdings).filter((row) => !factor || row.factor === factor);
    const windowHoldings = preferredWindow
      ? factorHoldings.filter((row) => !row.window || row.window === preferredWindow)
      : factorHoldings;
    const holdings = windowHoldings.length ? windowHoldings : factorHoldings;
    const latestDate = maxString(holdings.map((row) => row.date || row.weight_date));
    return holdings
      .filter((row) => !latestDate || row.date === latestDate || row.weight_date === latestDate)
      .sort((a, b) => numberOr(a.rank, 9999) - numberOr(b.rank, 9999))
      .map((row, index) => ({
        rank: numberOr(row.rank, index + 1),
        symbol: stringOr(row.symbol, row.ticker, '-'),
        signal: finiteOrNull(row.score),
        displayWeight: finiteOrNull(row.default_weight ?? row.weight),
        finalWeight: finiteOrNull(row.weight ?? row.default_weight),
      }));
  }

  function latestFactorLeader(run) {
    const leaders = asRecords(run.factor_leaders);
    const latestDate = maxString(leaders.map((row) => row.date));
    return leaders.find((row) => row.date === latestDate) || leaders.at(-1) || null;
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

  function parseValuation(payload) {
    if (isResearchSummary(payload, 'valuation')) {
      const meta = summaryMeta(payload);
      const rows = summaryEntities(payload)
        .map((entity) => {
          const price = finiteOrNull(entity.metrics.price);
          const dcfPerShare = finiteOrNull(entity.metrics.dcfPerShare);
          const dcfGap = price && dcfPerShare !== null ? (dcfPerShare / price) - 1 : null;
          return {
            ticker: stringOr(entity.symbol, ''),
            name: stringOr(entity.name, ''),
            sectorLabel: stringOr(entity.sectorLabel, entity.sector, '분류 없음'),
            themeTags: entity.themes.slice(0, 4),
            price,
            currency: 'USD',
            priceAsOf: stringOr(entity.metrics.priceAsOf, ''),
            dcfPerShare,
            dcfGap,
            qualityStatus: stringOr(entity.metrics.qualityStatus, '확인 필요'),
            companyFile: stringOr(entity.detailPath, ''),
            warnings: entity.warnings,
          };
        })
        .filter((row) => row.ticker)
        .sort((a, b) => numberOr(b.dcfGap, -999) - numberOr(a.dcfGap, -999));
      const sectors = asArray(meta.coverage?.sectors).length
        ? asArray(meta.coverage.sectors).map(String)
        : [...new Set(rows.map((row) => row.sectorLabel).filter(Boolean))];
      return {
        generatedAt: meta.generatedAt,
        status: firstLimitation(meta),
        tickerCount: finiteOrNull(meta.coverage?.entityCount) || rows.length,
        sectors,
        methodologyCount: finiteOrNull(highlightValue(meta, '방법론')) || 0,
        contractVersion: stringOr(payload.schemaVersion, ''),
        rows: rows.slice(0, 5),
        allRows: rows,
        entities: summaryEntities(payload),
        meta,
      };
    }
    const rows = asRecords(payload?.tickers)
      .map((row) => {
        const price = finiteOrNull(row.price);
        const dcfPerShare = finiteOrNull(row.dcfPerShare);
        const dcfGap = price && dcfPerShare !== null ? (dcfPerShare / price) - 1 : null;
        const themes = asArray(row.themeTags).map(String).filter(Boolean).slice(0, 3);
        return {
          ticker: stringOr(row.ticker, ''),
          name: stringOr(row.name, ''),
          sectorLabel: stringOr(row.sectorLabel, row.sector, '분류 없음'),
          themeTags: themes,
          price,
          currency: stringOr(row.currency, 'USD'),
          priceAsOf: stringOr(row.priceAsOf, ''),
          dcfPerShare,
          dcfGap,
          qualityStatus: stringOr(row.qualityStatus, '확인 필요'),
          companyFile: stringOr(row.companyFile, ''),
        };
      })
      .filter((row) => row.ticker)
      .sort((a, b) => numberOr(b.dcfGap, -999) - numberOr(a.dcfGap, -999));
    const sectors = [...new Set(rows.map((row) => row.sectorLabel).filter(Boolean))];
    return {
      generatedAt: stringOr(payload?.generatedAt, ''),
      status: stringOr(payload?.modelPolicy?.decisionOwner, '모델은 정답이 아니라 가정 정리 도구입니다. 최종 판단은 사용자가 수행합니다.'),
      tickerCount: rows.length,
      sectors,
      methodologyCount: asArray(payload?.methodologyReferences).length,
      contractVersion: stringOr(payload?.schemaVersion, ''),
      rows: rows.slice(0, 5),
      allRows: rows,
      meta: {},
    };
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

  function parseRiskScore(payload) {
    if (isResearchSummary(payload, 'risk-score')) {
      const meta = summaryMeta(payload);
      const entity = summaryEntities(payload)[0] || {};
      const metrics = isRecord(entity.metrics) ? entity.metrics : {};
      const risk = isRecord(payload.riskScore) ? payload.riskScore : {};
      const current = {
        date: stringOr(risk.current?.date, payload.dataAsOf, meta.dataAsOf),
        close: finiteOrNull(risk.current?.close ?? metrics.latestClose),
        oneDayReturn: finiteOrNull(risk.current?.oneDayReturn ?? metrics.oneDayReturn),
        vixClose: finiteOrNull(risk.current?.vixClose ?? metrics.vixClose),
        ohScore: finiteOrNull(risk.current?.ohScore ?? metrics.ohScore),
        rfScore: finiteOrNull(risk.current?.rfScore ?? metrics.rfScore),
        topRiskScore: finiteOrNull(risk.current?.topRiskScore ?? metrics.topRiskScore),
        confirmedTopRisk: Boolean(risk.current?.confirmation ?? metrics.confirmedTopRisk),
        regime: stringOr(risk.current?.regime, metrics.regime, '확인 필요'),
        actionLabel: stringOr(risk.current?.actionLabel, payload.status, entity.status, '확인 필요'),
        actionLevel: stringOr(risk.current?.actionLevel, metrics.actionLevel, ''),
        actionText: stringOr(risk.current?.actionText, firstLimitation(meta), ''),
      };
      const rows = [
        { label: 'Top Risk Score', value: `${formatNumber(current.topRiskScore)}/5`, status: current.actionLabel, interpretation: 'max(OH Score, RF Score)', date: current.date },
        { label: 'OH Score', value: `${formatNumber(current.ohScore)}/5`, status: scoreStatus(current.ohScore), interpretation: '과열형 top model', date: current.date },
        { label: 'RF Score', value: `${formatNumber(current.rfScore)}/5`, status: scoreStatus(current.rfScore), interpretation: '반등 실패형 top model', date: current.date },
        { label: 'Confirmation', value: current.confirmedTopRisk ? 'ON' : 'OFF', status: current.confirmedTopRisk ? 'Confirmed' : 'Leading/Inactive', interpretation: '가격/VIX confirmation filter', date: current.date },
        { label: 'SOX close', value: formatNumber(current.close), status: `1D ${formatPercent(current.oneDayReturn)}`, interpretation: `VIX ${formatNumber(current.vixClose)}`, date: current.date },
      ];
      return {
        generatedAt: meta.generatedAt,
        dataAsOf: meta.dataAsOf,
        status: current.actionLabel,
        current,
        rows,
        entities: summaryEntities(payload),
        meta: {
          ...meta,
          statusState: stringOr(meta.statusState, 'ok'),
          statusLabel: current.actionLabel,
          cadence: stringOr(meta.cadence, payload.automation?.cadence, 'daily-after-market-close'),
          limitations: meta.limitations.length ? meta.limitations : ['뉴스 기반 모델이 아니며 가격/변동성 기반 risk overlay입니다.'],
          automation: isRecord(payload.automation) ? payload.automation : meta.automation,
        },
      };
    }
    return normalizeRiskScoreFallback();
  }

  function scoreStatus(score) {
    const value = finiteOrNull(score);
    if (value === null) return '확인 필요';
    if (value >= 5) return 'Red Zone';
    if (value >= 4) return 'High Risk';
    if (value >= 3) return 'Watch';
    return 'Normal';
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

  function renderMomentum(summary, mode, error, project) {
    renderMetricCards(panelSelector(project, 'metrics'), [
      ['베스트 모멘텀 팩터', summary.factor],
      ['데이터 기준일', formatMaybeDate(summary.dataAsOf)],
      ['추천/신호 상태', summary.outputLabel],
      ['업데이트', formatFreshness(summary.generatedAt)],
    ]);
    renderRows(panelSelector(project, 'rows'), summary.rows, (row) => [
      row.rank,
      badge(row.symbol),
      formatNumber(row.signal),
      formatPercent(row.displayWeight),
      formatPercent(row.finalWeight),
    ], 5);
    setStatus(panelSelector(project, 'status'), buildStatusText(mode, summary.generatedAt, error, summary.status, summaryDataAsOf(summary)), mode);
  }

  function renderDram(summary, mode, error, project) {
    const latestPoint = latestSeriesPoint(summary.series);
    renderMetricBadges(panelSelector(project, 'metrics'), [
      `제품 ${summary.series.length || 0}개`,
      `관측치 ${formatInteger(summary.observationCount)}`,
      `최근값 ${latestPoint ? `${latestPoint.name} ${formatNumber(latestPoint.value)} USD` : '확인 불가'}`,
      `업데이트 ${formatFreshness(summary.generatedAt)}`,
    ]);
    renderDramChart(panelSelector(project, 'chart'), summary.series);
    setStatus(panelSelector(project, 'status'), buildStatusText(mode, summary.generatedAt, error, summary.status, summaryDataAsOf(summary)), mode);
  }

  function renderBestFactor(summary, mode, error, project) {
    renderMetricCards(panelSelector(project, 'metrics'), [
      ['베스트 팩터', summary.factor],
      ['종합 점수', formatNumber(summary.compositeScore)],
      ['데이터 기준일', formatMaybeDate(summary.dataEndDate)],
      ['업데이트', formatFreshness(summary.generatedAt)],
    ]);
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
    const latestDate = maxString(summary.rows.map((row) => row.date));
    const signalTotal = summary.rows.reduce((sum, row) => sum + numberOr(row.signalCount, 0), 0);
    const avgCoverageRows = summary.rows.map((row) => finiteOrNull(row.returnCoverage)).filter((value) => value !== null);
    const avgCoverage = avgCoverageRows.length ? avgCoverageRows.reduce((sum, value) => sum + value, 0) / avgCoverageRows.length : null;
    const avgTop10WeightRows = summary.rows.map((row) => finiteOrNull(row.top10Weight)).filter((value) => value !== null);
    const avgTop10Weight = avgTop10WeightRows.length ? avgTop10WeightRows.reduce((sum, value) => sum + value, 0) / avgTop10WeightRows.length : null;
    renderMetricCards(panelSelector(project, 'metrics'), [
      ['추적 ETF', `${summary.rows.length || 0}개`],
      ['최근 기준일', formatMaybeDate(latestDate)],
      ['특별 신호', `${signalTotal.toLocaleString('ko-KR')}건`],
      ['평균 TOP10 비중', formatPercent(avgTop10Weight)],
      ['평균 종가 커버리지', formatPercent(avgCoverage)],
    ]);
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

  function renderValuation(summary, mode, error, project) {
    const calculableGapCount = asRecords(summary.allRows || summary.rows).filter((row) => finiteOrNull(row.dcfGap) !== null).length;
    renderMetricCards(panelSelector(project, 'metrics'), [
      ['분석 티커', `${formatInteger(summary.tickerCount || summary.rows.length)}개`],
      ['섹터', `${asArray(summary.sectors).slice(0, 3).join(' · ') || '확인 필요'}`],
      ['DCF 괴리 계산', `${formatInteger(calculableGapCount)}개`],
      ['방법론 참조', `${formatInteger(summary.methodologyCount || 0)}개`],
    ]);
    renderRows(panelSelector(project, 'rows'), summary.rows, (row) => [
      badge(row.ticker),
      `${row.sectorLabel}${row.themeTags?.length ? ` · ${row.themeTags.join(', ')}` : ''}`,
      `${formatNumber(row.price)} ${row.currency || 'USD'}`,
      `${formatNumber(row.dcfPerShare)} · 괴리 ${formatPercent(row.dcfGap)}`,
      `${row.qualityStatus} · 가격일 ${formatMaybeDate(row.priceAsOf)}`,
    ], 5);
    setStatus(panelSelector(project, 'status'), buildStatusText(mode, summary.generatedAt, error, summary.status, summaryDataAsOf(summary)), mode);
  }

  function renderSox(summary, mode, error, project) {
    const topScore = asRecords(summary.rows)[0];
    const topWeight = summary.topWeight || asRecords(summary.rows).reduce((best, row) => numberOr(row.weight, -1) > numberOr(best?.weight, -1) ? row : best, null);
    renderMetricCards(panelSelector(project, 'metrics'), [
      ['구성종목', `${formatInteger(summary.constituentCount || summary.allRows?.length || summary.rows?.length)}개`],
      ['기준일', formatMaybeDate(summary.dataAsOf)],
      ['종합 1위', topScore ? `${topScore.ticker} · ${formatNumber(topScore.score)}` : '확인 필요'],
      ['최대 proxy weight', topWeight ? `${topWeight.ticker} · ${formatPercent(topWeight.weight)}` : '확인 필요'],
    ]);
    renderRows(panelSelector(project, 'rows'), asRecords(summary.rows), (row) => [
      row.rank,
      badge(row.ticker),
      formatNumber(row.score),
      formatPercent(row.weight),
      `${formatNumber(row.priceMomentum)} / ${formatNumber(row.earningsMomentum)}`,
      row.status,
    ], 6);
    setStatus(panelSelector(project, 'status'), buildStatusText(mode, summary.generatedAt, error, summary.status, summaryDataAsOf(summary)), mode);
  }

  function renderRiskScore(summary, mode, error, project) {
    const current = summary.current || {};
    renderMetricCards(panelSelector(project, 'metrics'), [
      ['Top Risk', `${formatNumber(current.topRiskScore)}/5`],
      ['OH / RF', `${formatNumber(current.ohScore)}/5 · ${formatNumber(current.rfScore)}/5`],
      ['Confirmation', current.confirmedTopRisk ? 'ON' : 'OFF'],
      ['기준일', formatMaybeDate(current.date || summary.dataAsOf)],
    ]);
    renderRows(panelSelector(project, 'rows'), asRecords(summary.rows), (row) => [
      row.label,
      row.value,
      row.status,
      row.interpretation,
      formatMaybeDate(row.date),
    ], 5);
    setStatus(panelSelector(project, 'status'), buildStatusText(mode, summary.generatedAt, error, summary.status, summaryDataAsOf(summary)), mode);
  }

  function renderEtfDetailCards(selector, rows) {
    const target = $(selector);
    if (!target) return;
    const cards = asRecords(rows).map((row) => `
      <article class="etf-detail-card">
        <div class="etf-detail-head">
          <div>
            <strong>${escapeHtml(row.name)}</strong>
            <span>${escapeHtml(row.code || row.fullName || '')} · ${escapeHtml(formatMaybeDate(row.date))}</span>
          </div>
          <a href="https://sonchanggi.github.io/etf-tracking/" aria-label="${escapeAttribute(row.name)} ETF Tracking 원본 열기">상세</a>
        </div>
        ${renderEtfMiniChart(row)}
        <ol class="etf-top10-list" aria-label="${escapeAttribute(row.name)} 최신 TOP10 보유종목">
          ${renderEtfTop10Items(row.top10)}
        </ol>
      </article>
    `).join('');
    target.innerHTML = `
      <div class="etf-detail-heading">
        <div>
          <strong>ETF별 최신 TOP10과 최근 1개월 비중 변화</strong>
          <span>표는 최신 기준일, 미니 그래프는 현재 TOP10 종목의 최근 31일 저장 비중 히스토리를 표시합니다.</span>
        </div>
      </div>
      <div class="etf-detail-grid">${cards || '<div class="skeleton-line">ETF 상세 요약을 표시할 데이터가 없습니다.</div>'}</div>
    `;
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

  function renderEtfMiniChart(row) {
    const chartSeries = asRecords(row.chartSeries)
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
    const minDate = Math.min(...dates);
    const maxDate = Math.max(...dates);
    const minValue = Math.min(...values);
    const maxValue = Math.max(...values);
    const yTicks = buildEtfPercentAxisTicks(minValue, maxValue, 5);
    const yMin = yTicks[0] ?? Math.max(0, minValue);
    const yMax = yTicks.at(-1) ?? Math.max(maxValue, yMin + 0.01);
    const width = 680;
    const height = 240;
    const margin = { top: 34, right: 22, bottom: 38, left: 58 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;
    const x = (date) => margin.left + ((Date.parse(date) - minDate) / Math.max(maxDate - minDate, 1)) * innerWidth;
    const y = (value) => margin.top + (1 - ((value - yMin) / Math.max(yMax - yMin, 0.000001))) * innerHeight;
    const grid = yTicks.map((tick) => {
      const yy = y(tick);
      return `<g><line x1="${margin.left}" x2="${width - margin.right}" y1="${yy.toFixed(1)}" y2="${yy.toFixed(1)}" stroke="#d9e2f1"/><text x="${margin.left - 10}" y="${(yy + 4).toFixed(1)}" text-anchor="end" fill="#aab3c2" font-size="12" font-weight="700">${escapeHtml(formatPercent(tick))}</text></g>`;
    }).join('');
    const paths = chartSeries.map((item, index) => {
      const color = COLORS[index % COLORS.length];
      const segments = splitChartPointSegments(item.points);
      const segmentPaths = segments.map((segment) => {
        const pathData = segment.map((point, pointIndex) => `${pointIndex ? 'L' : 'M'} ${x(point.date).toFixed(1)} ${y(point.value).toFixed(1)}`).join(' ');
        return `<path d="${pathData}" fill="none" stroke="${color}" stroke-width="${item.rank <= 3 ? 3.4 : 2.4}" stroke-linecap="round" stroke-linejoin="round"/>`;
      }).join('');
      const last = item.points.filter((point) => Number.isFinite(point.value)).at(-1);
      const lastPoint = last ? `<circle cx="${x(last.date).toFixed(1)}" cy="${y(last.value).toFixed(1)}" r="${item.rank <= 3 ? 4.2 : 3.3}" fill="${color}"><title>${escapeHtml(item.label)} ${formatPercent(last.value)}</title></circle>` : '';
      return `${segmentPaths}${lastPoint}`;
    }).join('');
    const legend = chartSeries.slice(0, 5).map((item, index) => `<span><i class="legend-key" style="background:${COLORS[index % COLORS.length]}"></i>${escapeHtml(item.label)}</span>`).join('');
    const firstDate = new Date(minDate).toISOString().slice(0, 10);
    const lastDate = new Date(maxDate).toISOString().slice(0, 10);
    return `
      <div class="etf-mini-chart">
        <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeAttribute(row.name)} TOP10 비중 변화 미니 그래프">
          <rect x="0" y="0" width="${width}" height="${height}" fill="transparent"/>
          <text x="${margin.left}" y="18" fill="#d8dee8" font-size="13" font-weight="800">최근 1개월 비중(%)</text>
          ${grid}
          <line x1="${margin.left}" x2="${width - margin.right}" y1="${height - margin.bottom}" y2="${height - margin.bottom}" stroke="#3b4556"/>
          <text x="${margin.left}" y="${height - 12}" fill="#9aa4b2" font-size="11">${escapeHtml(formatMaybeDate(firstDate))}</text>
          <text x="${width - margin.right}" y="${height - 12}" text-anchor="end" fill="#9aa4b2" font-size="11">${escapeHtml(formatMaybeDate(lastDate))}</text>
          ${paths}
        </svg>
        <div class="chart-legend etf-mini-legend">${legend}</div>
      </div>
    `;
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

  function renderDramChart(selector, series) {
    const target = $(selector);
    if (!target) return;
    const chartSeries = normalizeChartSeries(series);
    if (!chartSeries.length) {
      target.innerHTML = '<div class="skeleton-line">표시할 D램 가격 그래프 데이터가 없습니다.</div>';
      return;
    }

    const points = chartSeries.flatMap((item) => item.points.map(([date, value]) => ({ date, value: Number(value) })));
    const dates = points.map((point) => Date.parse(point.date)).filter(Number.isFinite);
    const values = points.map((point) => point.value).filter(Number.isFinite);
    const minDate = Math.min(...dates);
    const maxDate = Math.max(...dates);
    const minValue = Math.min(...values);
    const maxValue = Math.max(...values);
    const yTicks = buildDramAxisTicks(minValue, maxValue, 5);
    const yMin = yTicks[0] ?? Math.floor(minValue);
    const yMax = yTicks.at(-1) ?? Math.ceil(maxValue);

    const width = 920;
    const height = 360;
    const margin = { top: 28, right: 34, bottom: 54, left: 72 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;
    const x = (date) => margin.left + ((Date.parse(date) - minDate) / Math.max(maxDate - minDate, 1)) * innerWidth;
    const y = (value) => margin.top + (1 - ((value - yMin) / Math.max(yMax - yMin, 1))) * innerHeight;

    const xLabels = [minDate, maxDate].map((time) => formatMaybeDate(new Date(time).toISOString().slice(0, 10)));

    const grid = yTicks.map((tick) => {
      const yy = y(tick);
      return `<g><line x1="${margin.left}" x2="${width - margin.right}" y1="${yy}" y2="${yy}" stroke="#d9e2f1"/><text x="${margin.left - 12}" y="${yy + 4}" text-anchor="end" fill="#9aa4b2" font-size="12">${formatInteger(tick)}</text></g>`;
    }).join('');

    const paths = chartSeries.map((item, index) => {
      const color = COLORS[index % COLORS.length];
      const validPoints = item.points.filter(([, value]) => Number.isFinite(Number(value)));
      const pathData = validPoints.map(([date, value], pointIndex) => `${pointIndex === 0 ? 'M' : 'L'} ${x(date).toFixed(1)} ${y(Number(value)).toFixed(1)}`).join(' ');
      const circles = validPoints.map(([date, value]) => `<circle cx="${x(date).toFixed(1)}" cy="${y(Number(value)).toFixed(1)}" r="3.5" fill="${color}"/>`).join('');
      return `<path d="${pathData}" fill="none" stroke="${color}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>${circles}`;
    }).join('');

    const legend = chartSeries.map((item, index) => `
      <span><i class="legend-key" style="background:${COLORS[index % COLORS.length]}"></i>${escapeHtml(item.name)}</span>
    `).join('');

    target.innerHTML = `
      <svg viewBox="0 0 ${width} ${height}" aria-hidden="true">
        <rect x="0" y="0" width="${width}" height="${height}" fill="transparent"/>
        ${grid}
        <line x1="${margin.left}" x2="${width - margin.right}" y1="${height - margin.bottom}" y2="${height - margin.bottom}" stroke="#3b4556"/>
        <line x1="${margin.left}" x2="${margin.left}" y1="${margin.top}" y2="${height - margin.bottom}" stroke="#3b4556"/>
        <text x="${margin.left}" y="${height - 18}" fill="#9aa4b2" font-size="12">${escapeHtml(xLabels[0])}</text>
        <text x="${width - margin.right}" y="${height - 18}" text-anchor="end" fill="#9aa4b2" font-size="12">${escapeHtml(xLabels[1])}</text>
        <text x="${margin.left}" y="18" fill="#d8dee8" font-size="13" font-weight="700">TrendForce daily · USD 기준 가격 추이</text>
        ${paths}
      </svg>
      <div class="chart-legend">${legend}</div>
    `;
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
    return { ...FALLBACK_SNAPSHOT.momentum };
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

  function normalizeRiskScoreFallback() {
    return {
      ...FALLBACK_SNAPSHOT.riskScore,
      current: { ...FALLBACK_SNAPSHOT.riskScore.current },
      rows: FALLBACK_SNAPSHOT.riskScore.rows,
      entities: FALLBACK_SNAPSHOT.riskScore.entities,
      meta: FALLBACK_SNAPSHOT.riskScore.meta,
    };
  }

  function normalizeValuationFallback() {
    return {
      generatedAt: FALLBACK_SNAPSHOT.valuation.generatedAt,
      status: FALLBACK_SNAPSHOT.valuation.status,
      tickerCount: FALLBACK_SNAPSHOT.valuation.tickerCount,
      sectors: FALLBACK_SNAPSHOT.valuation.sectors,
      methodologyCount: FALLBACK_SNAPSHOT.valuation.methodologyCount || 0,
      contractVersion: FALLBACK_SNAPSHOT.valuation.contractVersion || 'fallback',
      rows: FALLBACK_SNAPSHOT.valuation.rows,
      allRows: FALLBACK_SNAPSHOT.valuation.rows,
    };
  }

  function renderResearchBriefing(records = []) {
    const target = $('#research-briefing');
    if (!target) return;
    const items = records.map(briefingItemForRecord).filter(Boolean);
    target.innerHTML = items.length ? items.map((item) => `
      <article class="briefing-item ${item.tone || ''}">
        <span>${escapeHtml(item.kicker)}</span>
        <strong>${escapeHtml(item.title)}</strong>
        <p>${escapeHtml(item.detail)}</p>
      </article>
    `).join('') : '<div class="skeleton-line">표시할 브리핑 데이터가 없습니다.</div>';
  }

  function briefingItemForRecord(record) {
    const summary = record.summary || {};
    if (record.project.id === 'momentum') {
      const limit = firstLimitation(summary.meta || {});
      return {
        kicker: 'Momentum',
        title: `베스트 ${summary.factor || '-'} · ${formatMaybeDate(summary.dataAsOf)}`,
        detail: `${summary.outputLabel || 'Research signal'} — ${limit}`,
        tone: summary.meta?.statusState === 'ok' ? '' : 'warning',
      };
    }
    if (record.project.id === 'dram') {
      const latest = latestSeriesPoint(summary.series);
      const limit = firstLimitation(summary.meta || {});
      return {
        kicker: 'DRAM',
        title: latest ? `${latest.name} ${formatNumber(latest.value)} USD` : '대표 가격 확인 필요',
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
    if (record.project.id === 'risk-score') {
      const current = summary.current || {};
      return {
        kicker: 'Risk Score',
        title: `Top ${formatNumber(current.topRiskScore)}/5 · ${current.actionLabel || '확인 필요'}`,
        detail: `OH ${formatNumber(current.ohScore)}/5 · RF ${formatNumber(current.rfScore)}/5 · confirmation ${current.confirmedTopRisk ? 'ON' : 'OFF'} · ${firstLimitation(summary.meta || {})}`,
        tone: current.confirmedTopRisk || current.topRiskScore >= 4 ? 'warning' : '',
      };
    }
    if (record.project.id === 'valuation') {
      return {
        kicker: 'Valuation',
        title: `${formatInteger(summary.tickerCount)}개 기업 · ${asArray(summary.sectors).slice(0, 2).join('/') || '다중 섹터'}`,
        detail: firstLimitation(summary.meta || {}),
      };
    }
    return null;
  }

  function renderDataHealth(records = []) {
    const target = $('#data-health');
    if (!target) return;
    const portfolio = portfolioFreshnessSummary(records);
    const portfolioRow = portfolio ? `
      <article class="health-item ${portfolio.mixed ? 'warn' : 'ok'}">
        <div>
          <strong>Portfolio snapshot</strong>
          <span>${portfolio.mixed ? 'mixed freshness' : 'aligned'}</span>
        </div>
        <p>${escapeHtml(portfolio.label)}</p>
        <small>${escapeHtml('허브는 각 프로젝트의 public JSON을 독립적으로 읽습니다. 이 행은 서로 다른 기준일이 섞였는지 보여줍니다.')}</small>
      </article>
    ` : '';
    const rows = records.map((record) => `
      <article class="health-item ${healthTone(record)}">
        <div>
          <strong>${escapeHtml(record.project.shortName)}</strong>
          <span>${escapeHtml(healthLabel(record))}</span>
        </div>
        <p>${escapeHtml(recordFreshnessText(record))}</p>
        <small>${escapeHtml(`${formatBytes(record.payloadBytes)} · ${record.sourceCount}개 JSON · ${record.summary?.meta?.cadence || 'cadence 확인 필요'}${record.error ? ` · ${record.error}` : ''}`)}</small>
        ${safeAutomationUrl(record.summary?.meta?.automation?.workflowUrl) ? `<a class="health-link" href="${escapeAttribute(safeAutomationUrl(record.summary.meta.automation.workflowUrl))}" rel="noopener noreferrer">자동화/수동 실행</a>` : ''}
      </article>
    `).join('');
    target.innerHTML = portfolioRow || rows ? `${portfolioRow}${rows}` : '<div class="skeleton-line">데이터 상태를 표시할 수 없습니다.</div>';
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
    if (record.mode !== 'live') return 'warn';
    if (isRecordStale(record)) return 'warn';
    if (['degraded', 'stale'].includes(record.summary?.meta?.statusState)) return 'warn';
    return 'ok';
  }

  function healthLabel(record) {
    const state = record.summary?.meta?.statusState;
    if (record.mode !== 'live') return 'fallback';
    if (isRecordStale(record)) return 'stale';
    if (state) return state;
    return 'live';
  }

  function isRecordStale(record) {
    const expectedDays = finiteOrNull(record?.summary?.meta?.expectedFreshnessDays);
    const freshnessDate = Date.parse(recordFreshnessDate(record));
    if (expectedDays === null || !Number.isFinite(freshnessDate)) return false;
    const days = (Date.now() - freshnessDate) / (24 * 60 * 60 * 1000);
    return days > expectedDays;
  }

  function recordFreshnessDate(record) {
    const summary = isRecord(record?.summary) ? record.summary : {};
    return stringOr(summaryDataAsOf(summary), record?.dataAsOf, record?.generatedAt, summary.generatedAt, '');
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
    const dataAsOf = summaryDataAsOf(record?.summary) || record?.dataAsOf || '';
    const generatedAt = stringOr(record?.generatedAt, record?.summary?.generatedAt, '');
    if (dataAsOf) return `기준일 ${formatMaybeDate(dataAsOf)} · 업데이트 ${formatFreshness(generatedAt)}`;
    return `업데이트 ${formatFreshness(generatedAt)}`;
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
    renderWatchlistResults(records, []);
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
      target.innerHTML = `<p class="muted">${escapeHtml(tokens.join(', '))}와 직접 연결되는 공개 요약 신호가 없습니다. 원본 프로젝트에서 더 넓은 검색을 확인하세요.</p>`;
      return;
    }
    target.innerHTML = matches.slice(0, 24).map((match) => `
      <article class="watch-match ${match.tone || ''}">
        <span>${escapeHtml(match.project)}</span>
        <strong>${escapeHtml(match.label)}</strong>
        <p>${escapeHtml(match.detail)}</p>
        ${match.limit ? `<small>${escapeHtml(match.limit)}</small>` : ''}
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
      if (record.project.id === 'valuation') {
        asRecords(record.summary.allRows || record.summary.rows).forEach((row) => {
          const haystack = [row.ticker, row.name, row.sectorLabel, ...asArray(row.themeTags)].join(' ').toUpperCase();
          if (haystack.includes(token)) {
            matches.push({
              project,
              label: `${row.ticker} · ${row.sectorLabel}`,
              detail: `현재가 ${formatNumber(row.price)} ${row.currency || 'USD'}, DCF ${formatNumber(row.dcfPerShare)}, 품질 ${row.qualityStatus}`,
              limit: firstLimitation(meta),
            });
          }
        });
      } else if (record.project.id === 'momentum') {
        asRecords(record.summary.rows).forEach((row) => {
          if (String(row.symbol || '').toUpperCase().includes(token)) {
            matches.push({ project, matchKey: matchIdentity(record.project.id, row.symbol), label: `${row.symbol} · rank ${row.rank}`, detail: `모멘텀 신호 ${formatNumber(row.signal)}, 표시용 비중 ${formatPercent(row.displayWeight)}`, limit: firstLimitation(meta), tone: meta.statusState === 'ok' ? '' : 'warning' });
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
      parseDram,
      parseBestFactor,
      parseEtfTracking,
      parseValuation,
      parseSox,
      renderSox,
      parseRiskScore,
      renderRiskScore,
      deriveMomentumDisplayWeights,
      momentumSignalWeights,
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
      renderEtfDetailCards,
      renderResearchBriefing,
      renderDataHealth,
      watchlistMatchesForToken,
      parseWatchlistTokens,
      resolveLoadState,
      loadProjectPanel,
      loadEtfPanel,
      loadValuationPanel,
      parsePanelSafely,
      validateAdapterContract,
      isResearchSummary,
      summaryMeta,
      summaryEntities,
      entitySummaryLine,
      isRecordStale,
      recordFreshnessDate,
      recordFreshnessText,
      portfolioFreshnessSummary,
      summaryDataAsOf,
      safeAutomationUrl,
      renderProjectNavigation,
      renderDashboardPanels,
      PROJECTS,
      PANEL_ADAPTERS,
      normalizeChartSeries,
      isValidChartPoint,
      buildDramAxisTicks,
      buildEtfPercentAxisTicks,
    };
  }
})();
