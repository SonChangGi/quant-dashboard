/* Shared public navigation. Generated fallback is checked against menu.json. */
(function (root, factory) {
  'use strict';
  const api = factory(root);
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root && root.document) {
    root.QuantNavigationV1 = api;
    const begin = () => api.start();
    if (root.document.readyState === 'loading') root.document.addEventListener('DOMContentLoaded', begin, {once: true});
    else begin();
  }
})(typeof globalThis !== 'undefined' ? globalThis : this, function (root) {
  'use strict';
  const menuUrl = 'https://sonchanggi.github.io/quant-dashboard/shared/navigation/v1/menu.json';
  // BEGIN GENERATED FALLBACK
  const fallbackMenu = {"schemaVersion":"quant-navigation/v1","brand":{"id":"hub","label":"Quant Research Hub","url":"https://sonchanggi.github.io/quant-dashboard/"},"projects":[{"id":"factor","label":"Factor","url":"https://sonchanggi.github.io/factor/"},{"id":"dram","label":"DRAM","url":"https://sonchanggi.github.io/dram-price/"},{"id":"etf","label":"ETF","url":"https://sonchanggi.github.io/etf-tracking/"},{"id":"sox","label":"SOX","url":"https://sonchanggi.github.io/sox/"},{"id":"fear-greed","label":"Fear & Greed","url":"https://sonchanggi.github.io/fearNgreed/"},{"id":"regime","label":"Regime","url":"https://sonchanggi.github.io/regime/"},{"id":"news","label":"News","url":"https://sonchanggi.github.io/news/"},{"id":"observatory","label":"알파 하우스","url":"https://research-observatory-changgi.changgi-son.chatgpt.site/"}]};
  // END GENERATED FALLBACK
  const aliases = Object.freeze({momentum: 'factor', 'momentum-factor-lab': 'factor', fearngreed: 'fear-greed', fearNgreed: 'fear-greed', 'dram-price': 'dram', 'etf-tracking': 'etf'});
  const normalizeId = id => aliases[id] || id;
  const trustedOrigins = new Set(['https://sonchanggi.github.io', 'https://research-observatory-changgi.changgi-son.chatgpt.site']);
  function validateMenu(value) {
    if (!value || value.schemaVersion !== 'quant-navigation/v1' || !Array.isArray(value.projects) || !value.projects.length || value.projects.length > 30) throw new Error('Invalid navigation schema');
    const ids = new Set(), urls = new Set();
    function entry(row) {
      if (!row || typeof row.id !== 'string' || !/^[a-z][a-z0-9-]{0,39}$/.test(row.id) || row.id === 'best-factor' || typeof row.label !== 'string' || !row.label.trim() || row.label.length > 60 || /[<>\x00-\x1f]/.test(row.label) || typeof row.url !== 'string') throw new Error('Invalid navigation entry');
      const parsed = new URL(row.url);
      if (!trustedOrigins.has(parsed.origin) || parsed.username || parsed.password || parsed.search || parsed.hash || !parsed.pathname.endsWith('/') || parsed.pathname.includes('//') || /\/(best-factor)(\/|$)/.test(parsed.pathname)) throw new Error('Invalid navigation URL');
      if (ids.has(row.id) || urls.has(parsed.href)) throw new Error('Duplicate navigation entry');
      ids.add(row.id); urls.add(parsed.href);
      return Object.freeze({id: row.id, label: row.label, url: parsed.href});
    }
    const brand = entry(value.brand);
    if (brand.id !== 'hub' || brand.url !== 'https://sonchanggi.github.io/quant-dashboard/') throw new Error('Invalid navigation brand');
    const projects = value.projects.map(entry);
    return Object.freeze({schemaVersion: 'quant-navigation/v1', brand, projects: Object.freeze(projects)});
  }
  async function loadMenu(fetcher = root.fetch && root.fetch.bind(root), timeoutMs = 3000) {
    if (typeof fetcher !== 'function') throw new Error('Navigation unavailable');
    const controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
    let timer;
    const deadline = new Promise((_, reject) => { timer = setTimeout(() => { controller?.abort(); reject(new Error('Navigation timeout')); }, timeoutMs); });
    try {
      return await Promise.race([deadline, (async () => {
        const response = await fetcher(menuUrl, {cache: 'no-cache', credentials: 'omit', referrerPolicy: 'no-referrer', signal: controller?.signal});
        if (!response.ok) throw new Error('Navigation unavailable');
        const text = await response.text();
        if (text.length > 16384) throw new Error('Navigation response too large');
        return validateMenu(JSON.parse(text));
      })()]);
    } finally { clearTimeout(timer); }
  }
  function getLinks(menu, currentId) {
    if (typeof menu === "string") {currentId = menu; menu = activeMenu;}
    const current = normalizeId(currentId);
    return menu.projects.map(project => ({...project, current: project.id === current}));
  }
  function projectFor(nav, document) {
    const explicit = nav.dataset.quantProject || document.querySelector('script[data-quant-project]')?.dataset.quantProject;
    if (explicit) return normalizeId(explicit);
    const active = nav.querySelector('.quant-shared-nav__links [aria-current="page"]');
    if (active) {
      const href = new URL(active.getAttribute('href') || '', document.baseURI);
      return fallbackMenu.projects.find(row => row.url === href.href)?.id || (href.pathname.includes('momentum-factor-lab') ? 'factor' : '');
    }
    return fallbackMenu.projects.find(row => document.location.href.startsWith(row.url))?.id || (document.location.pathname.includes('momentum-factor-lab') ? 'factor' : 'hub');
  }
  function render(menu, nav, currentId, document = root.document) {
    if (!nav || nav.dataset.quantNavigationManaged === 'react') return false;
    const rail = nav.querySelector('.quant-shared-nav__links');
    if (!rail) return false;
    const links = getLinks(menu, currentId);
    const signature = JSON.stringify(links);
    const existing = Array.from(rail.querySelectorAll('a')).map(link => ({id: link.dataset.quantProjectId, label: link.textContent, url: link.href, current: link.getAttribute('aria-current') === 'page'}));
    if (JSON.stringify(existing) === signature) return false;
    const focusedId = document.activeElement?.dataset.quantProjectId;
    const fragment = document.createDocumentFragment();
    for (const project of links) {
      const link = document.createElement('a');
      link.className = 'quant-shared-nav__link' + (project.current ? ' is-active' : '');
      link.dataset.quantProjectId = project.id;
      if (normalizeId(currentId) === "etf") link.dataset.controlId = "project_navigation";
      link.href = project.url; link.textContent = project.label;
      link.rel = 'noopener noreferrer'; link.referrerPolicy = 'no-referrer';
      if (project.current) link.setAttribute('aria-current', 'page');
      fragment.append(link);
    }
    rail.replaceChildren(fragment);
    const brand = nav.querySelector('.quant-shared-nav__brand');
    if (brand) { brand.href = menu.brand.url; brand.textContent = menu.brand.label; if (normalizeId(currentId) === 'hub') brand.setAttribute('aria-current', 'page'); else brand.removeAttribute('aria-current'); }
    if (focusedId) rail.querySelector('[data-quant-project-id="' + focusedId + '"]')?.focus();
    const active = rail.querySelector('[aria-current="page"]');
    if (active && rail.scrollWidth > rail.clientWidth) rail.scrollLeft = Math.max(0, active.offsetLeft - rail.offsetLeft - (rail.clientWidth - active.offsetWidth) / 2);
    nav.dataset.quantNavigationVersion = menu.schemaVersion;
    return true;
  }
  let started = false, activeMenu = validateMenu(fallbackMenu), observer;
  function start(document = root.document) {
    if (started || !document) return;
    started = true;
    const apply = () => document.querySelectorAll('.quant-shared-nav:not([data-quant-navigation-managed="react"])').forEach(nav => render(activeMenu, nav, projectFor(nav, document), document));
    apply();
    if (typeof root.MutationObserver === 'function') {
      observer = new root.MutationObserver(records => {
        if (records.some(record => record.target.nodeType === 1 && record.target.closest?.('.quant-shared-nav__links') || Array.from(record.addedNodes).some(node => node.nodeType === 1 && (node.matches?.('.quant-shared-nav') || node.querySelector?.('.quant-shared-nav'))))) apply();
      });
      observer.observe(document.body, {childList: true, subtree: true});
    }
    void loadMenu().then(menu => {activeMenu = menu; apply(); document.dispatchEvent(new root.CustomEvent('quant-navigation-ready', {detail: menu}));}).catch(() => {/* Local fallback remains usable. */});
  }
  return Object.freeze({menuUrl, fallbackMenu: activeMenu, normalizeId, validateMenu, loadMenu, getLinks, render, start, getMenu: () => activeMenu});
});
