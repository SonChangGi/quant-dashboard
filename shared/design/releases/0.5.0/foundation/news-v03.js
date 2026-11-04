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

/* Weekly narrative navigation: presentation only, with native content ownership. */
(() => {
  'use strict';
  function enhanceWeekly() {
    if (document.body.dataset.qdProject !== 'news') return;
    const narrative = document.querySelector('.weekly-narrative');
    if (!narrative || narrative.dataset.nw4Reader) return;
    const stories = [...narrative.querySelectorAll('.narrative-story')].filter(story =>
      /^[A-Za-z0-9_-]+$/.test(story.id) && story.querySelector('h3'));
    const nativeNav = narrative.querySelector('.narrative-contents');
    if (!stories.length || !nativeNav) return;

    const aside = document.createElement('aside');
    aside.className = 'nw4-weekly-outline';
    aside.setAttribute('aria-label', '주간 이야기 탐색');
    const details = document.createElement('details');
    const summary = document.createElement('summary');
    summary.textContent = '이번 주 이야기';
    const count = document.createElement('span');
    count.className = 'nw4-outline-count';
    count.textContent = String(stories.length);
    summary.append(count);
    details.append(summary);
    const list = document.createElement('ol');
    const targets = [];
    const links = [];
    function linkTo(target, text, className) {
      const a = document.createElement('a');
      a.href = '#' + target.id;
      a.className = className;
      a.textContent = text;
      a.addEventListener('click', event => {
        const original = [...nativeNav.querySelectorAll('a')].find(link => link.hash === a.hash);
        if (original) {
          event.preventDefault();
          const reading = target.closest('.weekly-reading-details')
            || target.querySelector('.weekly-reading-details');
          if (reading && !reading.open) reading.querySelector('summary')?.click();
          original.click(); // Native archive/search/hash handlers remain authoritative.
        } else {
          const previous = target.getAttribute('tabindex');
          target.setAttribute('tabindex', '-1');
          target.focus({preventScroll: true});
          target.scrollIntoView({block: 'start', behavior: 'instant'});
          current();
          target.addEventListener('blur', () => previous === null
            ? target.removeAttribute('tabindex') : target.setAttribute('tabindex', previous), {once: true});
        }
        // Keep an explicit mobile disclosure usable while reading. Its state
        // is not saved and never changes the source article's reader state.
      });
      links.push(a);
      targets.push(target);
      return a;
    }
    stories.forEach(story => {
      const item = document.createElement('li');
      const heading = story.querySelector('h3').cloneNode(true);
      heading.querySelectorAll('.narrative-story-number').forEach(node => node.remove());
      const a = linkTo(story, heading.textContent.trim(), 'nw4-story-link');
      item.append(a);
      list.append(item);
    });
    details.append(list);
    const sections = document.createElement('nav');
    sections.className = 'nw4-outline-sections';
    sections.setAttribute('aria-label', '주간 브리핑 구간');
    [...nativeNav.querySelectorAll('a')].forEach(original => {
      if (!original.hash || original.hash === '#weekly-key-stories') return;
      const target = document.getElementById(original.hash.slice(1));
      if (target) sections.append(linkTo(target, original.textContent.trim(), 'nw4-section-link'));
    });
    details.append(sections);
    aside.append(details);
    narrative.prepend(aside);
    narrative.classList.add('nw4-weekly');
    narrative.dataset.nw4Reader = '1';

    const desktop = matchMedia('(min-width: 1180px)');
    const adapt = () => { details.open = desktop.matches; };
    adapt();
    if (desktop.addEventListener) desktop.addEventListener('change', adapt);
    let queued = false;
    const current = () => {
      queued = false;
      const rootStyle = getComputedStyle(document.documentElement);
      const offset = Math.max((parseFloat(rootStyle
        .getPropertyValue('--qd-header-height')) || 64) + 40,
      (parseFloat(rootStyle.scrollPaddingTop) || 0) + 24);
      // Heading elements inside a section have the same logical position as
      // their containing story/section. No URL or stored reading state changes.
      const positions = targets.map((target, index) => ({target, index,
        top: target.getBoundingClientRect().top})).filter(row => row.target.getClientRects().length);
      const past = positions.filter(row => row.top <= offset).sort((a, b) => b.top - a.top);
      const chosen = past[0] || positions.sort((a, b) => a.top - b.top)[0];
      links.forEach((link, index) => index === chosen?.index
        ? link.setAttribute('aria-current', 'location') : link.removeAttribute('aria-current'));
    };
    const queue = () => {if (!queued) {queued = true; requestAnimationFrame(current);}};
    window.addEventListener('scroll', queue, {passive: true});
    window.addEventListener('resize', queue, {passive: true});
    window.addEventListener('hashchange', queue);
    current();
  }
  if (window.__quantDesignV4?.state === 'ready') enhanceWeekly();
  else window.addEventListener('quant-design-ready', enhanceWeekly, {once: true});
})();
