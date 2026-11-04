/* Exact UI copy edits only; never inspect article prose, financial output or failure messages. */
(() => {
  'use strict';
  const rules = {
    'investment-journal': [
      ['.section-head p','비교하고 싶은 지수를 선택하세요. 모두 해제하면 내 수익률만 표시합니다.',''],
      ['.auth-story-bottom','나만의 계정 · 기기 간 동기화 · 원본은 기기에서 분석',''],
      ['.demo-strip > span','가상 데이터 체험 중 · 실제 보유·시세가 아닙니다','예시 데이터'],
      ['.footer > span','시연용 가상 데이터','']
    ]
  };
  function apply() {
    const project = document.body?.dataset.qdProject;
    for (const [selector, before, after] of rules[project] || []) {
      for (const node of document.querySelectorAll(selector)) {
        if (node.textContent.trim() !== before || node.children.length) {
          if (!after) delete node.dataset.qdRedundantCopy;
          continue;
        }
        // Keep the React-owned node in place. Only this reviewed literal is changed.
        if (after) node.textContent = after;
        else node.dataset.qdRedundantCopy = 'true';
      }
    }
  }
  let scheduled = false;
  const observer = new MutationObserver(() => {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => {scheduled = false;apply();});
  });
  if (document.body) {apply();observer.observe(document.body,{subtree:true,childList:true,characterData:true});}
  else document.addEventListener('DOMContentLoaded',()=>{apply();observer.observe(document.body,{subtree:true,childList:true,characterData:true});},{once:true});
})();
