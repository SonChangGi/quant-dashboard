/* Reviewed exact copy only; no calculation, request, input or chart mutation. */
(() => {
  'use strict';
  const rules = {
    'dram-price': [
      ['.page-footer>span', 'DRAM Price Lab · 개인 리서치용 공개 데이터 모니터', 'DRAM Price Lab'],
    ],
    'sox': [
      ['#methodology .method-grid>article', '운영 상세 개인 리서치용이며 투자 조언이 아닙니다. 데이터는 지연되거나 일부 누락될 수 있습니다.', ''],
    ],
    'etf-tracking': [
      ['#research-notice', '연구용 정적 스냅샷 · 잔차 신호는 실제 운용사 주문 확정이나 투자·매매 조언이 아닙니다.', ''],
      ['#decomposition-detail>summary small', '전일 대비 비중 변화의 전체 분석 행', ''],
    ],
  };
  const normalize = value => value.replace(/\s+/g, ' ').trim();
  function refine(scope) {
    const project = document.documentElement.dataset.quantDesignProject;
    for (const [selector, before, after] of rules[project] || []) {
      const nodes = [...(scope.matches?.(selector) ? [scope] : []), ...scope.querySelectorAll(selector)];
      for (const node of nodes) {
        if (normalize(node.textContent) !== before) continue;
        if (after) node.textContent = after;
        else node.remove();
      }
    }
  }
  function start() {
    refine(document);
    new MutationObserver(records => {
      for (const record of records) for (const node of record.addedNodes) {
        if (node.nodeType === 1) refine(node);
      }
    }).observe(document.body, {childList:true, subtree:true});
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, {once:true});
  else start();
  addEventListener('quant-design-ready', () => refine(document), {once:true});
})();
