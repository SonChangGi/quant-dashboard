import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const source = readFileSync('assets/theme.js', 'utf8');
const html = readFileSync('index.html', 'utf8');

assert.match(html, /assets\/theme\.js\?v=20260722-common-v1/, 'HTML cache-busts the common-design v1 theme runtime');

function createStorage(entries = {}) {
  const values = new Map(Object.entries(entries));
  return {
    getItem(key) {
      return values.has(key) ? values.get(key) : null;
    },
    setItem(key, value) {
      values.set(key, String(value));
    },
    removeItem(key) {
      values.delete(key);
    },
  };
}

function runTheme({ search = '', stored = {}, systemDark = false } = {}) {
  const storage = createStorage(stored);
  const listeners = new Map();
  const label = { textContent: '' };
  const button = {
    attributes: new Map(),
    setAttribute(name, value) {
      this.attributes.set(name, String(value));
    },
    querySelector(selector) {
      return selector === '.theme-toggle-text' ? label : null;
    },
    addEventListener(type, callback) {
      listeners.set(type, callback);
    },
  };
  const root = { dataset: { theme: 'light' }, style: {} };
  const document = {
    documentElement: root,
    readyState: 'complete',
    querySelector(selector) {
      return selector === '#theme-toggle' ? button : null;
    },
    addEventListener() {},
  };
  const window = {
    localStorage: storage,
    location: { search },
    matchMedia: () => ({ matches: systemDark }),
  };
  const context = vm.createContext({ document, URLSearchParams, window });
  vm.runInContext(source, context, { filename: 'assets/theme.js' });
  return { button, label, listeners, root, storage };
}

{
  const page = runTheme({
    search: '?theme=dark',
    stored: { 'quant-dashboard-theme': 'light' },
  });
  assert.equal(page.root.dataset.theme, 'dark', 'valid query theme takes precedence over persisted theme');
  assert.equal(page.storage.getItem('quant-research-theme'), 'light', 'query preview does not overwrite the persisted preference');
  assert.equal(page.storage.getItem('quant-dashboard-theme'), null, 'query preview still completes legacy-key migration');
}

for (const legacyKey of ['quant-dashboard-theme', 'quant-calm-theme', 'dram-price-theme']) {
  const page = runTheme({ stored: { [legacyKey]: 'dark' } });
  assert.equal(page.root.dataset.theme, 'dark', `${legacyKey} is read during migration`);
  assert.equal(page.storage.getItem('quant-research-theme'), 'dark', `${legacyKey} migrates to the canonical key`);
  assert.equal(page.storage.getItem(legacyKey), null, `${legacyKey} is removed after migration`);
}

{
  const page = runTheme({ systemDark: true });
  assert.equal(page.root.dataset.theme, 'dark', 'system dark preference is used without a query or stored preference');
  assert.equal(page.root.style.colorScheme, 'dark', 'browser color scheme follows the applied theme');
  assert.equal(page.button.attributes.get('aria-pressed'), 'true', 'theme toggle state follows the applied dark theme');
}

{
  const page = runTheme();
  assert.equal(page.root.dataset.theme, 'light', 'light is the default when query, storage, and system are light');
  page.listeners.get('click')();
  assert.equal(page.root.dataset.theme, 'dark', 'theme toggle changes the current page theme');
  assert.equal(page.storage.getItem('quant-research-theme'), 'dark', 'theme toggle persists only the canonical key');
  assert.equal(page.label.textContent, '라이트 모드', 'theme toggle label describes the next action');
}

console.log('PASS theme query, migration, system preference, fallback, and toggle persistence');
