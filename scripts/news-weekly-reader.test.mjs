import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';

const source = readFileSync(new URL('../shared/design/releases/0.5.0/foundation/news-v03.js', import.meta.url), 'utf8');
const marker = '/* Weekly narrative navigation: presentation only, with native content ownership. */';
const weekly = source.slice(source.indexOf(marker));

function run({project = 'news', ready = true, narrative = null} = {}) {
  const events = new Map();
  let queries = 0;
  const document = {body: {dataset: {qdProject: project}},
    querySelector() {queries++; return narrative;}};
  const window = {__quantDesignV4: {state: ready ? 'ready' : 'loading'},
    addEventListener(name, callback, options) {events.set(name, {callback, options});}};
  vm.runInNewContext(weekly, {window, document});
  return {events, document, window, queries: () => queries};
}

test('daily focus reader stays byte-identical before the separate weekly adapter', () => {
  const prefix = source.slice(0, source.indexOf(marker)).trimEnd() + '\n';
  assert.equal(createHash('sha256').update(prefix).digest('hex'),
    '2989892e2ddc5349aae58f3ef5c39368b0acd2ce0a4d095920faf1aabc02a725');
});
test('unrelated projects never inspect or change their content', () => {
  for (const project of ['factor', 'investment-journal', 'alpha-house', 'quant-dashboard']) {
    const r = run({project});
    assert.equal(r.queries(), 0);
  }
});
test('ordinary daily and legacy weekly pages need no narrative adapter', () => {
  assert.equal(run().queries(), 1);
});
test('an already enhanced narrative cannot acquire another outline or listeners', () => {
  const r = run({narrative: {dataset: {nw4Reader: '1'}}});
  assert.equal(r.events.size, 0);
});
test('native shell readiness is awaited exactly once', () => {
  const r = run({ready: false});
  assert.equal(r.queries(), 0);
  assert.equal(r.events.get('quant-design-ready').options.once, true);
  r.events.get('quant-design-ready').callback();
  assert.equal(r.queries(), 1);
});
test('missing or malformed story headings keep the native navigation', () => {
  let mutations = 0;
  run({narrative: {dataset: {}, querySelectorAll: () => [{id: '../unsafe', querySelector() {throw Error('unsafe id');}}],
    querySelector: () => ({}), prepend() {mutations++;}}});
  assert.equal(mutations, 0);
});
test('weekly controls are display-only and never fetch or persist user data', () => {
  assert(!/\bfetch\s*\(|XMLHttpRequest|localStorage|sessionStorage|innerHTML|replaceChildren/.test(weekly));
  assert(weekly.includes('original.click()'));
  assert(weekly.includes("target.setAttribute('tabindex', '-1')"));
  assert(weekly.includes("previous === null"));
});
