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
const v2Briefing = {
  ...briefing, schema_version: '2', status: 'complete',
  run_id: 'b44575cb1bc00358b6aaa3b2', edition_phase: 'daily_final',
  reviewable_draft: true, normal_editorial_approval: false,
  issues: [...briefing.issues, issue('d', '네 번째 이슈'), issue('e', '다섯 번째 이슈')],
  highlights: ['다섯 번째 이슈', '세 번째 이슈', '첫 번째 이슈', '네 번째 이슈', '두 번째 이슈'],
};
const weeklyBriefing = {
  ...v2Briefing, report_date: '2026-10-18', generated_at: '2026-10-19T04:13:59Z',
  cutoff: '2026-10-19T10:53:04+09:00', edition_kind: 'weekend', edition_phase: 'sunday_weekly',
  period_id: 'weekend:2026-10-12',
  edition: { owner_date: '2026-10-18', recap_policy: 'published_mon_sat_v1', period_start: '2026-10-12', period_end: '2026-10-17' },
};

function publicationFor(payload, fields = {}) {
  const selected = {
    ...entry, date: payload.report_date, generated_at: payload.generated_at, cutoff: payload.cutoff,
    mode: payload.mode, status: payload.status, issue_count: payload.issues.length,
    run_id: payload.run_id, edition_phase: payload.edition_phase,
    sha256: { json: sha(serialize(payload)) }, ...fields,
  };
  return { ...archive, latest_date: selected.date, entries: [selected] };
}
const weeklyArchive = publicationFor(weeklyBriefing, {
  report_url: '/news/weekend/2026-10-12/index.html', edition_kind: 'weekend', period_id: weeklyBriefing.period_id,
  ...weeklyBriefing.edition,
});

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
    { schema_version: '3' }, { report_date: '2026-09-14' }, { generated_at: '2026-09-15T13:00:00Z' }, { status: 'ok' },
    { issues: briefing.issues.slice(0, 1) }, { publication: { visibility: 'private' } }, { synthetic: true },
    { highlights: ['unknown issue'] }, { issues: [briefing.issues[0], briefing.issues[0], briefing.issues[2]] },
  ]) assert.throws(() => api.parseNewsBriefing(selected, { ...briefing, ...change }));
});

test('v2 drafts retain publisher order, four headlines, and separate editorial approval', async () => {
  const index = publicationFor(v2Briefing);
  const { api, targets } = setup(async (url) => responseFor(serialize(url.endsWith('archive.json') ? index : v2Briefing)));
  const result = await api.loadNewsSummary();
  assert.equal(result.state, 'ready');
  assert.deepEqual(Array.from(result.summary.headlines, (row) => row.title), v2Briefing.highlights.slice(0, 4));
  assert.match(result.summary.headlines[0].url, /#issue-eeeeeeeeeeeeeeee$/);
  assert.equal(result.summary.status, 'complete');
  assert.equal(result.summary.mode, 'reconstruction');
  assert.equal(result.summary.reviewable_draft, true);
  assert.equal(result.summary.normal_editorial_approval, false);
  assert.equal(targets['#news-status'].textContent, `발행일 ${reportDate} · 5개 이슈`);
  assert.match(targets['#news-health'].innerHTML, /health-item warn/);
  assert.match(targets['#news-health'].innerHTML, /검토용 초안/);
  assert.ok(!targets['#news-summary'].innerHTML.includes('두 번째 이슈'), 'the fifth highlight stays outside the four-headline summary');
});

test('legacy and v2 publications without approval metadata do not imply editorial approval', () => {
  const { api } = setup();
  for (const schema_version of ['1', 1, '2', 2]) {
    const payload = { ...briefing, schema_version };
    const parsed = api.parseNewsBriefing(api.parseNewsArchive(publicationFor(payload)), payload);
    assert.equal(parsed.reviewable_draft, null);
    assert.equal(parsed.normal_editorial_approval, null);
    assert.deepEqual(Array.from(parsed.headlines, (row) => row.title), briefing.highlights);
  }
});

test('v2 preserves publication identity, privacy, and approval-type validation', () => {
  const { api } = setup();
  const selected = api.parseNewsArchive(publicationFor(v2Briefing));
  for (const change of [
    { schema_version: '3' }, { schema_version: ['2'] }, { report_date: '2026-09-14' },
    { generated_at: '2026-09-15T13:00:00Z' }, { cutoff: '2026-09-15T08:00:00+09:00' },
    { mode: 'live' }, { status: 'partial' }, { run_id: 'another-run' }, { edition_phase: 'saturday_daily' },
    { issues: v2Briefing.issues.slice(1) }, { publication: { visibility: 'private' } }, { synthetic: true },
    { highlights: ['unknown issue'] }, { reviewable_draft: 'true' }, { reviewable_draft: null },
    { normal_editorial_approval: 'false' }, { normal_editorial_approval: true },
  ]) assert.throws(() => api.parseNewsBriefing(selected, { ...v2Briefing, ...change }), JSON.stringify(change));
});

test('v2 hash mismatches clear the summary instead of accepting a new version unsigned', async () => {
  const index = publicationFor(v2Briefing);
  const { api, targets } = setup(async (url) => responseFor(serialize(url.endsWith('archive.json')
    ? index : { ...v2Briefing, notice: 'changed bytes' })));
  assert.equal((await api.loadNewsSummary()).state, 'error');
  assert.equal(targets['#news-summary'].innerHTML, '');
});

test('weekly v2 follows its canonical Monday route while keeping the owner date and source order', async () => {
  const urls = [];
  const { api, targets } = setup(async (url) => {
    urls.push(url);
    return responseFor(serialize(url.endsWith('archive.json') ? weeklyArchive : weeklyBriefing));
  });
  const result = await api.loadNewsSummary();
  assert.equal(result.state, 'ready');
  assert.equal(urls[1], 'https://sonchanggi.github.io/news/weekend/2026-10-12/briefing.json');
  assert.equal(result.summary.date, '2026-10-18');
  assert.equal(result.summary.period_id, 'weekend:2026-10-12');
  assert.deepEqual(Array.from(result.summary.headlines, (row) => row.title), weeklyBriefing.highlights.slice(0, 4));
  assert.equal(targets['#news-report-link'].href, 'https://sonchanggi.github.io/news/weekend/2026-10-12/index.html');
  assert.match(result.summary.headlines[0].url, /weekend\/2026-10-12\/index.html#issue-eeeeeeeeeeeeeeee$/);
});

test('weekly retries retain their original period instead of routing by the later report date', () => {
  const { api } = setup();
  const payload = { ...weeklyBriefing, report_date: '2026-10-19' };
  const index = { ...weeklyArchive, latest_date: payload.report_date,
    entries: [{ ...weeklyArchive.entries[0], date: payload.report_date }] };
  const parsed = api.parseNewsBriefing(api.parseNewsArchive(index), payload);
  assert.equal(parsed.date, '2026-10-19');
  assert.equal(parsed.owner_date, '2026-10-18');
  assert.equal(parsed.jsonUrl, 'https://sonchanggi.github.io/news/weekend/2026-10-12/briefing.json');
});

test('weekly route validation rejects invalid owners, periods, and unsafe publication URLs', () => {
  const { api } = setup();
  for (const change of [
    { owner_date: '2026-10-25' }, { owner_date: '2026-10-12' }, { owner_date: '2026-10-17' },
    { owner_date: '2026-02-30' }, { owner_date: '2026-10-18T00:00:00Z' },
    { period_id: 'weekend:2026-10-05' }, { period_id: 'weekend:2026-10-13' }, { run_id: '' },
    { recap_policy: 'unknown' }, { period_start: '2026-10-13' }, { period_end: '2026-10-18' },
    { report_url: '/news/weekend/2026-10-05/index.html' },
    { report_url: '/news/daily/2026-10-18/index.html' },
    { report_url: 'https://evil.example/news/weekend/2026-10-12/index.html' },
    { report_url: '/news/weekend/2026-10-12/index.html?other=1' },
    { report_url: '/news/weekend/2026-10-12/index.html#other' },
  ]) assert.throws(() => api.parseNewsArchive({ ...weeklyArchive, entries: [{ ...weeklyArchive.entries[0], ...change }] }), JSON.stringify(change));
});

test('weekly briefing cannot mix another period, owner, run, or recap into the selected publication', () => {
  const { api } = setup();
  const selected = api.parseNewsArchive(weeklyArchive);
  for (const change of [
    { period_id: 'weekend:2026-10-05' }, { edition_kind: 'daily' }, { run_id: 'other-run' },
    { edition_phase: 'daily_final' }, { edition: { ...weeklyBriefing.edition, owner_date: '2026-10-17' } },
    { edition: { ...weeklyBriefing.edition, period_start: '2026-10-05' } },
    { edition: { ...weeklyBriefing.edition, period_end: '2026-10-18' } },
    { edition: { ...weeklyBriefing.edition, recap_policy: 'unknown' } },
  ]) assert.throws(() => api.parseNewsBriefing(selected, { ...weeklyBriefing, ...change }), JSON.stringify(change));
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
  assert.equal(targets['#news-status'].textContent, '발행일 2026-09-15 · 3개 이슈');
  assert.doesNotMatch(targets['#news-health'].innerHTML, /사후 재구성|부분 발행/);
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
