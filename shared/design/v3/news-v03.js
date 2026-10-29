/* Local reading enhancement: retain the native article nodes and reader state. */
(() => {
  'use strict';
  if (!location.pathname.startsWith('/news/')) return;
  const library = document.querySelector('.library');
  const root = library || document.querySelector('main') || document.body;
  const selector = library ? '.card' : '.issue';
  let current = null;
  const dialog = document.createElement('dialog');
  dialog.className = 'nw3-reader';
  dialog.setAttribute('aria-label', '집중 읽기');
  const bar = document.createElement('div');
  bar.className = 'nw3-reader-bar';
  const label = document.createElement('span');
  label.textContent = '집중 읽기';
  const close = document.createElement('button');
  close.type = 'button';
  close.className = 'nw3-reader-close';
  close.textContent = '← 목록으로';
  bar.append(label, close);
  const content = document.createElement('div');
  content.className = 'nw3-reader-content';
  dialog.append(bar, content);
  root.append(dialog);

  function nativeControl(card) {
    return card.querySelector(library ? '.card-title' : '.issue-detail > summary');
  }
  function expanded(card) {
    return library ? card.classList.contains('open') : card.querySelector('.issue-detail').open;
  }
  function finish() {
    if (!current) return;
    const state = current;
    current = null;
    if (dialog.open) dialog.close();
    document.documentElement.classList.remove('nw3-reading');
    state.card.classList.remove('nw3-focused');
    if (state.placeholder.isConnected) {
      state.placeholder.replaceWith(state.card);
      if (!state.wasOpen && expanded(state.card)) nativeControl(state.card)?.click();
    } else {
      if (!state.wasOpen && expanded(state.card)) nativeControl(state.card)?.click();
      state.card.remove();
    }
    requestAnimationFrame(() => requestAnimationFrame(() => {
      window.scrollTo({top: state.scroll, behavior: 'instant'});
      const target = state.button.isConnected && !state.card.hidden ? state.button : document.querySelector(library ? '#query' : '#search');
      target?.focus({preventScroll:true});
    }));
  }
  function start(card, button) {
    if (current) return;
    const state = {card, button, wasOpen:expanded(card), scroll:window.scrollY, placeholder:document.createComment('news reader position')};
    current = state;
    if (!state.wasOpen) nativeControl(card)?.click();
    // Native daily reader first aligns the article. Move only after that frame.
    requestAnimationFrame(() => {
      if (current !== state || !card.isConnected) { if (current === state) finish(); return; }
      card.before(state.placeholder);
      content.append(card);
      card.classList.add('nw3-focused');
      document.documentElement.classList.add('nw3-reading');
      dialog.showModal();
      dialog.scrollTop = 0;
      close.focus({preventScroll:true});
    });
  }
  close.addEventListener('click', finish);
  dialog.addEventListener('cancel', event => {event.preventDefault(); finish();});
  dialog.addEventListener('close', () => {if (current) finish();});
  // Article backgrounds and titles normally collapse the native card. Keep them
  // readable in the dialog, while links, evidence details and save remain live.
  content.addEventListener('click', event => {
    const target = event.target;
    if (!(target instanceof Element)) return;
    if (target.closest('.card-title,.issue h3 a')) {event.preventDefault(); event.stopPropagation(); return;}
    if (!target.closest('a,button,input,select,textarea,label,summary,[role="button"]')) event.stopPropagation();
  }, true);
  function enhance() {
    root.querySelectorAll(selector).forEach(card => {
      if (card.querySelector('.nw3-read-button')) return;
      // Some archived editions contain the same provenance label twice in a row.
      // Only remove byte-identical neighboring labels from the rendered DOM.
      // Article bodies, source links and the stored edition stay untouched.
      card.querySelectorAll('.location').forEach(label => {
        let next = label.nextElementSibling;
        while (next?.matches('.location') && next.outerHTML === label.outerHTML) {
          const duplicate = next;
          next = duplicate.nextElementSibling;
          duplicate.remove();
        }
      });
      const button = document.createElement('button');
      button.className = 'nw3-read-button';
      button.type = 'button';
      button.textContent = '집중 읽기 ↗';
      button.setAttribute('aria-haspopup','dialog');
      button.setAttribute('aria-label', (card.querySelector('h3')?.textContent.trim() || '기사') + ' · 집중 읽기');
      button.addEventListener('click', event => {event.stopPropagation(); start(card, button);});
      card.append(button);
    });
  }
  enhance();
  const resultRoot = library ? document.getElementById('results') : root;
  if (resultRoot) new MutationObserver(() => {
    if (current && dialog.open && (!current.placeholder.isConnected || current.card.hidden)) finish();
    enhance();
  }).observe(resultRoot, {childList:true, subtree:true, attributes:true, attributeFilter:['hidden']});
})();
