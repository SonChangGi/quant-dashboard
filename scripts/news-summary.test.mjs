import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = readFileSync('assets/app.js', 'utf8');
const reportDate = '2026-09-15';
const issue = (id, title) => ({ anchor: `issue-${id.repeat(16)}`, title, summary: [`${title}의 핵심 사실.`] });
const briefing = {
  schema_version: '1', publication: { visibility: 'public' }, synthetic: false,
  report_date: reportDate, generated_at: '2026-09-15T12:00:00Z', cutoff: '2026-09-15T07:00:00+09:00',
  mode: 'reconstruction', status: 'partial',
  issues: [issue('a', '첫 번째 이슈'), issue('b', '두 번째 이슈'), issue('c', '세 번째 이슈')],
  highlights: ['세 번째 이슈', '첫 번째 이슈'], notice: '운영 상세에만 남길 출처 설명',
};
const serialize = (payload) => JSON.stringify(payload) + '\n';
const sha = (text) => createHash('sha256').update(text).digest('hex');
const entry = {
  date: reportDate, report_url: `/news/daily/${reportDate}/index.html`,
  generated_at: briefing.generated_at, cutoff: briefing.cutoff, mode: briefing.mode, status: briefing.status,
  issue_count: 3, sha256: { json: sha(serialize(briefing)) },
};
const archive = { schema_version: 1, visibility: 'public', base_path: '/news/', latest_date: reportDate, entries: [entry] };

function setup(fetchImpl) {
  const targets = Object.fromEntries(['news-summary', 'news-status', 'news-report-link', 'news-health'].map((id) => [
    `#${id}`, { innerHTML: '', textContent: '', href: '', classList: { toggle() {} } },
  ]));
  const context = vm.createContext({
    console, URL, AbortController, fetch: fetchImpl,
    window: { setTimeout, clearTimeout },
    document: { addEventListener() {}, querySelector: (selector) => targets[selector] || null },
  });
  vm.runInContext(source, context);
  return { api: context.__QUANT_DASHBOARD_TESTS__, targets };
}
const bodyFor = (url) => url.endsWith('archive.json') ? serialize(archive) : serialize(briefing);
const responseFor = (body, status = 200) => new Response(body, { status });

test('archive follows its declared latest date, not array order', () => {
  const { api } = setup();
  const result = api.parseNewsArchive({ ...archive, entries: [{ ...entry, date: '2026-09-14' }, entry] });
  assert.equal(result.date, reportDate);
  assert.equal(result.jsonUrl, `https://sonchanggi.github.io/news/daily/${reportDate}/briefing.json`);
  assert.equal(api.parseNewsArchive({ ...archive, entries: [], latest_date: null }), null);
});

test('unsafe or ambiguous archive identity is rejected', () => {
  const { api } = setup();
  for (const report_url of ['https://evil.example/news/daily/2026-09-15/index.html', '/news/daily/2026-09-14/index.html', '/news/daily/2026-09-15/index.html?other=1', 'javascript:alert(1)']) {
    assert.throws(() => api.parseNewsArchive({ ...archive, entries: [{ ...entry, report_url }] }));
  }
  assert.throws(() => api.parseNewsArchive({ ...archive, entries: [entry, entry] }));
  assert.throws(() => api.parseNewsArchive({ ...archive, visibility: 'private' }));
  assert.throws(() => api.parseNewsArchive({ ...archive, entries: [{ ...entry, sha256: {} }] }));
  assert.throws(() => api.parseNewsArchive({ ...archive, entries: [] }));
});

test('summary uses the publisher highlight order and retains report anchors', () => {
  const { api } = setup();
  const parsed = api.parseNewsBriefing(api.parseNewsArchive(archive), briefing);
  assert.deepEqual(Array.from(parsed.headlines, (row) => row.title), briefing.highlights);
  assert.equal(parsed.headlines[0].summary, briefing.issues[2].summary[0]);
  assert.match(parsed.headlines[0].url, /#issue-cccccccccccccccc$/);
  assert.equal(parsed.issue_count, 3);
  assert.equal(parsed.mode, 'reconstruction');
  assert.equal(parsed.status, 'partial');
});

test('mixed dates, counts, private or synthetic inputs cannot become a News summary', () => {
  const { api } = setup();
  const selected = api.parseNewsArchive(archive);
  for (const change of [
    { schema_version: '2' }, { report_date: '2026-09-14' }, { generated_at: '2026-09-15T13:00:00Z' }, { status: 'ok' },
    { issues: briefing.issues.slice(0, 1) }, { publication: { visibility: 'private' } }, { synthetic: true },
    { highlights: ['unknown issue'] }, { issues: [briefing.issues[0], briefing.issues[0], briefing.issues[2]] },
  ]) assert.throws(() => api.parseNewsBriefing(selected, { ...briefing, ...change }));
});

test('expired evidence does not expose a stale summary sentence', () => {
  const { api } = setup();
  const payload = { ...briefing, issues: briefing.issues.map((row) => ({ ...row, evidence_expired: true })) };
  const parsed = api.parseNewsBriefing(api.parseNewsArchive(archive), payload);
  assert.equal(parsed.headlines[0].summary, '');
  assert.equal(parsed.headlines[0].title, briefing.highlights[0]);
});

test('transport verifies the exact published UTF-8 bytes including the final newline', async () => {
  const { api } = setup(async () => responseFor(serialize(briefing)));
  assert.equal((await api.getJsonBestEffort('https://example.test/data', 1000, entry.sha256.json)).ok, true);
  assert.equal((await api.getJsonBestEffort('https://example.test/data', 1000, sha(JSON.stringify(briefing)))).ok, false);
  assert.equal((await api.getJsonBestEffort('https://example.test/data')).ok, true, 'existing unsigned readers are unchanged');
});

test('loader reads archive then the signed briefing and renders only concise content', async () => {
  const urls = [];
  const { api, targets } = setup(async (url) => { urls.push(url); return responseFor(bodyFor(url)); });
  const state = await api.loadNewsSummary();
  assert.equal(state.state, 'ready');
  assert.equal(urls.length, 2);
  assert.match(urls[1], /2026-09-15\/briefing.json$/);
  assert.match(targets['#news-status'].textContent, /발행일 2026-09-15 · 3개 이슈 · 사후 재구성 · 부분 발행/);
  assert.ok(!targets['#news-summary'].innerHTML.includes(briefing.notice));
  assert.ok(!targets['#news-health'].innerHTML.includes(briefing.notice));
});

test('new errors or empty archives clear a previously rendered News summary', async () => {
  let mode = 'ready';
  const { api, targets } = setup(async (url) => {
    if (mode === 'error') throw new Error('offline');
    if (mode === 'empty') return responseFor(serialize({ ...archive, entries: [], latest_date: null }));
    return responseFor(bodyFor(url));
  });
  await api.loadNewsSummary();
  assert.ok(targets['#news-summary'].innerHTML.includes(briefing.highlights[0]));
  mode = 'error';
  assert.equal((await api.loadNewsSummary()).state, 'error');
  assert.equal(targets['#news-summary'].innerHTML, '');
  assert.equal(targets['#news-report-link'].href, 'https://sonchanggi.github.io/news/');
  mode = 'empty';
  assert.equal((await api.loadNewsSummary()).state, 'empty');
  assert.match(targets['#news-status'].textContent, /발행된 브리핑 없음/);
});

test('rendered titles and summary sentences are escaped', async () => {
  const title = '<img src=x onerror=alert(1)>';
  const payload = { ...briefing, issues: [{ ...issue('d', title), summary: ['<script>alert(1)</script>'] }], highlights: [title] };
  const index = { ...archive, entries: [{ ...entry, issue_count: 1, sha256: { json: sha(serialize(payload)) } }] };
  const { api, targets } = setup(async (url) => responseFor(serialize(url.endsWith('archive.json') ? index : payload)));
  assert.equal((await api.loadNewsSummary()).state, 'ready');
  assert.ok(!targets['#news-summary'].innerHTML.includes('<img'));
  assert.ok(!targets['#news-summary'].innerHTML.includes('<script>'));
  assert.ok(targets['#news-summary'].innerHTML.includes('&lt;img'));
});
