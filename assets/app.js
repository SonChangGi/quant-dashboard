(() => {
  'use strict';

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
      shortName: 'DRAM',
      title: 'DRAM 가격 랩',
      description: 'DRAM 현물가, 고정가, 주간 현물 프록시를 모니터링하는 가격 대시보드입니다.',
      url: 'https://sonchanggi.github.io/dram-price/',
      accent: 'DR',
      panelAdapter: 'dram',
      panel: {
        eyebrow: 'DRAM Price',
        title: '대표 DRAM 가격 그래프',
        contentType: 'chart',
        metricLoading: 'DRAM 가격 데이터를 불러오는 중...',
        chartLabel: '대표 DRAM 가격 추이 그래프',
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
  ];

  const PANEL_ADAPTERS = {
    momentum: {
      sourceUrls: {
        momentum: 'https://sonchanggi.github.io/momentum-factor-lab/data/dashboard.json',
      },
      primarySourceKey: 'momentum',
      parse: (sources) => parseMomentum(sources.momentum),
      hasUsableData: (summary) => Boolean(summary?.rows?.length),
      fallback: normalizeMomentumFallback,
      render: renderMomentum,
      emptyReason: 'Momentum payload did not contain usable top rows.',
    },
    dram: {
      sourceUrls: {
        dramPrices: 'https://sonchanggi.github.io/dram-price/data/prices.json',
        dramSeries: 'https://sonchanggi.github.io/dram-price/data/series.json',
        dramStatus: 'https://sonchanggi.github.io/dram-price/data/status.json',
      },
      primarySourceKey: 'dramPrices',
      parse: (sources) => parseDram(sources.dramPrices, sources.dramSeries, sources.dramStatus),
      hasUsableData: (summary) => Boolean(summary?.series?.length),
      fallback: normalizeDramFallback,
      render: renderDram,
      emptyReason: 'DRAM payload did not contain usable dated price points.',
    },
    best: {
      sourceUrls: {
        best: 'https://sonchanggi.github.io/best-factor/data/latest-results.json',
      },
      primarySourceKey: 'best',
      parse: (sources) => parseBestFactor(sources.best),
      hasUsableData: (summary) => Boolean(summary?.rows?.length),
      fallback: normalizeBestFallback,
      render: renderBestFactor,
      emptyReason: 'Best Factor payload did not contain usable holdings.',
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
  };

  const COLORS = ['#2457d6', '#0f766e', '#e11d48', '#f97316', '#7c3aed', '#0891b2'];
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

  async function loadDashboardPanels() {
    return Promise.all(getPanelProjects().map((project) => loadProjectPanel(project)));
  }

  async function loadProjectPanel(projectOrId) {
    const project = typeof projectOrId === 'string' ? projectById(projectOrId) : projectOrId;
    const adapter = project ? PANEL_ADAPTERS[project.panelAdapter] : null;
    if (!project || !adapter) return;

    const entries = await Promise.all(Object.entries(adapter.sourceUrls).map(async ([sourceKey, url]) => [sourceKey, await getJsonBestEffort(url)]));
    const fetchResults = Object.fromEntries(entries);
    const dataSources = Object.fromEntries(entries.map(([sourceKey, result]) => [sourceKey, result.ok ? result.data : null]));
    const primaryResult = fetchResults[adapter.primarySourceKey] || { ok: false, error: 'Missing primary source.' };
    const parseResult = primaryResult.ok ? parsePanelSafely(adapter, dataSources) : { ok: false, data: null, error: primaryResult.error };
    const hasUsableData = parseResult.ok && adapter.hasUsableData(parseResult.data);
    const loadState = resolveLoadState(primaryResult, hasUsableData, parseResult.error || adapter.emptyReason);
    adapter.render(hasUsableData ? parseResult.data : adapter.fallback(), loadState.mode, loadState.error, project);
  }

  function parsePanelSafely(adapter, dataSources) {
    try {
      return { ok: true, data: adapter.parse(dataSources), error: null };
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      return { ok: false, data: null, error: `Payload parse failed: ${message}` };
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
      return { ok: true, data: await response.json(), url };
    } catch (error) {
      return { ok: false, error: error instanceof Error ? error.message : String(error), url };
    } finally {
      window.clearTimeout(timeout);
    }
  }

  function parseMomentum(payload) {
    const runs = Array.isArray(payload?.runs) ? payload.runs : [];
    const latestIndex = Number.isInteger(payload?.latest_run_index) ? payload.latest_run_index : runs.length - 1;
    const run = runs[latestIndex] || runs.at(-1) || payload || {};
    const summary = isRecord(run.summary) ? run.summary : {};
    const factor = stringOr(summary.selected_factor, latestFactorLeader(run)?.best_factor, FALLBACK_SNAPSHOT.momentum.factor);
    const latestRows = momentumRowsFromLatestOutput(run);
    const rows = latestRows.length ? latestRows : momentumRowsFromHoldings(run, factor);

    return {
      factor,
      generatedAt: stringOr(run.generated_at_utc, payload?.generated_at_utc, ''),
      dataAsOf: stringOr(summary.data_as_of, ''),
      outputLabel: stringOr(summary.recommendation_output_label, summary.recommendation_status, 'Research signal'),
      status: stringOr(summary.recommendation_output_label, '라이브 공개 JSON 표시 중'),
      rows: rows.slice(0, 5),
    };
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

  function momentumRowsFromHoldings(run, factor) {
    const holdings = asRecords(run.holdings).filter((row) => !factor || row.factor === factor);
    const latestDate = maxString(holdings.map((row) => row.date || row.weight_date));
    return holdings
      .filter((row) => !latestDate || row.date === latestDate || row.weight_date === latestDate)
      .sort((a, b) => numberOr(a.rank, 9999) - numberOr(b.rank, 9999))
      .map((row, index) => ({
        rank: numberOr(row.rank, index + 1),
        symbol: stringOr(row.symbol, row.ticker, '-'),
        signal: finiteOrNull(row.score),
        displayWeight: finiteOrNull(row.default_weight ?? row.weight),
        finalWeight: finiteOrNull(row.weight),
      }));
  }

  function latestFactorLeader(run) {
    const leaders = asArray(run.factor_leaders);
    const latestDate = maxString(leaders.map((row) => row.date));
    return leaders.find((row) => row.date === latestDate) || leaders.at(-1) || null;
  }

  function parseDram(pricesPayload, seriesPayload, statusPayload) {
    const observations = asRecords(pricesPayload?.observations);
    const representativeNames = new Set(
      asRecords(seriesPayload?.series)
        .filter((item) => item?.representative)
        .map((item) => item.product_name)
        .filter(Boolean)
    );
    const groups = new Map();
    for (const observation of observations) {
      const name = stringOr(observation.product_name, observation.product_id, 'Unknown DRAM');
      const value = dramMetricValue(observation.values || {});
      const date = stringOr(observation.effective_date, observation.date, '');
      if (!isValidChartPoint(date, value)) continue;
      if (!groups.has(name)) groups.set(name, { name, representative: representativeNames.has(name), points: [] });
      groups.get(name).points.push([date, value]);
    }

    const allSeries = [...groups.values()]
      .map((item) => ({
        ...item,
        points: item.points
          .sort((a, b) => a[0].localeCompare(b[0]))
          .filter((point, index, arr) => index === 0 || point[0] !== arr[index - 1][0]),
      }))
      .filter((item) => item.points.length > 0)
      .sort((a, b) => {
        if (a.representative !== b.representative) return a.representative ? -1 : 1;
        return b.points.length - a.points.length;
      });

    const chartSeries = allSeries.filter((item) => item.points.length >= 2).slice(0, 4);
    const selected = chartSeries.length ? chartSeries : allSeries.slice(0, 4);
    return {
      generatedAt: stringOr(pricesPayload?.generated_at, statusPayload?.generated_at, ''),
      observationCount: observations.length || finiteOrNull(statusPayload?.observation_count),
      status: '라이브 공개 JSON 표시 중',
      series: selected,
    };
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
    };
  }

  function renderMomentum(summary, mode, error, project) {
    renderMetricCards(panelSelector(project, 'metrics'), [
      ['선택/베스트 팩터', summary.factor],
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
    setStatus(panelSelector(project, 'status'), buildStatusText(mode, summary.generatedAt, error, summary.status), mode);
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
    setStatus(panelSelector(project, 'status'), buildStatusText(mode, summary.generatedAt, error, summary.status), mode);
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
    setStatus(panelSelector(project, 'status'), buildStatusText(mode, summary.generatedAt, error, summary.status), mode);
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
      target.innerHTML = '<div class="skeleton-line">표시할 DRAM 가격 그래프 데이터가 없습니다.</div>';
      return;
    }

    const points = chartSeries.flatMap((item) => item.points.map(([date, value]) => ({ date, value: Number(value) })));
    const dates = points.map((point) => Date.parse(point.date)).filter(Number.isFinite);
    const values = points.map((point) => point.value).filter(Number.isFinite);
    const minDate = Math.min(...dates);
    const maxDate = Math.max(...dates);
    const minValue = Math.min(...values);
    const maxValue = Math.max(...values);
    const yPad = Math.max((maxValue - minValue) * 0.1, 1);

    const width = 920;
    const height = 360;
    const margin = { top: 28, right: 34, bottom: 54, left: 72 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;
    const x = (date) => margin.left + ((Date.parse(date) - minDate) / Math.max(maxDate - minDate, 1)) * innerWidth;
    const y = (value) => margin.top + (1 - ((value - (minValue - yPad)) / Math.max((maxValue + yPad) - (minValue - yPad), 1))) * innerHeight;

    const yTicks = buildTicks(minValue - yPad, maxValue + yPad, 5);
    const xLabels = [minDate, maxDate].map((time) => formatMaybeDate(new Date(time).toISOString().slice(0, 10)));

    const grid = yTicks.map((tick) => {
      const yy = y(tick);
      return `<g><line x1="${margin.left}" x2="${width - margin.right}" y1="${yy}" y2="${yy}" stroke="#d9e2f1"/><text x="${margin.left - 12}" y="${yy + 4}" text-anchor="end" fill="#667085" font-size="12">${formatNumber(tick)}</text></g>`;
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
        <line x1="${margin.left}" x2="${width - margin.right}" y1="${height - margin.bottom}" y2="${height - margin.bottom}" stroke="#aab7cf"/>
        <line x1="${margin.left}" x2="${margin.left}" y1="${margin.top}" y2="${height - margin.bottom}" stroke="#aab7cf"/>
        <text x="${margin.left}" y="${height - 18}" fill="#667085" font-size="12">${escapeHtml(xLabels[0])}</text>
        <text x="${width - margin.right}" y="${height - 18}" text-anchor="end" fill="#667085" font-size="12">${escapeHtml(xLabels[1])}</text>
        <text x="${margin.left}" y="18" fill="#344054" font-size="13" font-weight="700">USD 기준 가격 추이</text>
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

  function buildStatusText(mode, generatedAt, error, sourceStatus) {
    const freshness = formatFreshness(generatedAt);
    if (mode === 'live') return `라이브 공개 JSON 기준 · 업데이트 ${freshness} · ${sourceStatus || '정상'}`;
    return `공개 JSON을 읽지 못해 fallback 표시 중 · 업데이트 ${freshness} · 사유: ${error || sourceStatus || '스키마/네트워크 확인 필요'}`;
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

  function buildTicks(min, max, count) {
    if (!Number.isFinite(min) || !Number.isFinite(max) || count < 2) return [];
    const step = (max - min) / (count - 1 || 1);
    return Array.from({ length: count }, (_, index) => min + step * index);
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
      resolveLoadState,
      loadProjectPanel,
      parsePanelSafely,
      renderProjectNavigation,
      renderDashboardPanels,
      PROJECTS,
      PANEL_ADAPTERS,
      normalizeChartSeries,
      isValidChartPoint,
    };
  }
})();
