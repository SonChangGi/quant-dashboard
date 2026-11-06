/* Shared presentation: exact UI copy mappings; no article/data-wide text rewriting. */
(() => {
  'use strict';
  if (window.__quantUICopy) return;
  const percentPoint = text => location.pathname.startsWith('/etf-tracking/') ? text.replace(/([+−-]?\d+(?:\.\d+)?)pp\b/g, '$1%p') : text;
  const rules = [
    { id: 'news-topic-order', selector: '.reader-topic-options > p', from: '선택한 주제를 먼저 표시합니다. 모든 이슈는 그대로 볼 수 있습니다.', to: '선택한 주제 우선 표시' },
    { id: 'news-local-storage', selector: '.reader-local-note', from: '보기 설정과 저장 상태는 이 브라우저에 보관됩니다.', to: '이 브라우저에 저장' },
    { id: 'news-empty', selector: '#no-results', from: '검색 결과가 없습니다.', to: '검색 결과 없음' },
    { id: 'news-filter-empty', selector: '#no-results', from: '조건에 맞는 이슈가 없습니다. 검색어나 필터를 바꿔보세요.', to: '조건에 맞는 이슈 없음' },
    { id: 'journal-privacy', selector: '.performance-hidden, .quant-private', from: '금액 가리기 사용 중 · 상단 눈 아이콘으로 표시할 수 있습니다.', to: '금액 숨김' },
    { id: 'journal-stale-result', selector: '.quant-stale', from: '조회 기간·계좌·원자료·가정 거래·비용 중 일부가 바뀌었습니다. 이전 결과를 참고용으로 표시하며, 다시 실행해야 내보낼 수 있습니다.', to: '입력 변경됨 · 이전 결과 · 다시 계산 후 내보내기' },
    { id: 'journal-symbol-empty', selector: '.muted.small-text', from: '검색 결과가 없습니다. 티커를 확인하거나 아래에 직접 입력하세요.', to: '검색 결과 없음 · 직접 입력' },
    { id: 'journal-table-empty', selector: '.tracking-table .table-empty', from: '검색 결과가 없습니다.', to: '검색 결과 없음' },
    { id: 'etf-percentage-point-unit', selector: '#chart-selection-summary small, .chart-summary-item small, #top10-rows td, #decomposition-rows td, #etf-signal-tables .weight-move-cell span, #etf-signal-tables .price-residual-cell strong, #etf-signal-tables .price-residual-cell span, #etf-signal-tables select[data-signal-filter="magnitude"] option', transform: percentPoint },
    { id: 'etf-chart-heading', selector: '#chart-title', from: 'TOP10 비중 변화 그래프', to: '종목별 비중' },
    { id: 'etf-observation-detail', selector: '.signal-card > p', transform: text => /^\d{4}-\d{2}-\d{2} · 매수·매도 추정 없음 · [−+\-\d.,]+% → [−+\-\d.,]+%$/.test(text) ? text.replace(' · 매수·매도 추정 없음', '') : text },
  ];
  const selector = rules.map(rule => rule.selector).join(', ');
  const applied = {};
  function update(element) {
    // Preserve React-owned node identity and never replace controls or nested content.
    if (element.childElementCount || element.childNodes.length !== 1 || element.firstChild.nodeType !== 3) return;
    const before = element.firstChild.nodeValue;
    const text = before.trim();
    for (const rule of rules) {
      if (!element.matches(rule.selector)) continue;
      const after = rule.transform ? rule.transform(text) : text === rule.from ? rule.to : text;
      if (after !== text) {
        element.firstChild.nodeValue = before.replace(text, after);
        applied[rule.id] = (applied[rule.id] || 0) + 1;
        return;
      }
    }
  }
  function scan(root) {
    if (root.nodeType !== 1) return;
    if (root.matches(selector)) update(root);
    root.querySelectorAll(selector).forEach(update);
  }
  function start() {
    scan(document.body);
    const pending = new Set();
    let queued = false;
    const observer = new MutationObserver(records => {
      for (const record of records) {
        if (record.type === 'characterData') pending.add(record.target.parentElement);
        else {
          pending.add(record.target);
          for (const node of record.addedNodes) if (node.nodeType === 1) pending.add(node);
        }
      }
      if (!queued) {
        queued = true;
        queueMicrotask(() => { queued = false; for (const node of pending) if (node?.isConnected) scan(node); pending.clear(); });
      }
    });
    observer.observe(document.body, { subtree: true, childList: true, characterData: true });
    window.__quantUICopy = { version: '1.0.0-local', applied, disconnect: () => observer.disconnect() };
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true });
  else start();
})();
