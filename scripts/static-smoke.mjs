import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { extname, join, normalize } from 'node:path';

const root = process.cwd();
const types = new Map([
  ['.html', 'text/html; charset=utf-8'],
  ['.js', 'text/javascript; charset=utf-8'],
  ['.css', 'text/css; charset=utf-8'],
]);

const server = createServer(async (request, response) => {
  try {
    const pathname = new URL(request.url || '/', 'http://127.0.0.1').pathname;
    const relative = pathname === '/' ? 'index.html' : pathname.slice(1);
    const safePath = normalize(relative).replace(/^(\.\.(\/|\\|$))+/, '');
    const filePath = join(root, safePath);
    const body = await readFile(filePath);
    response.writeHead(200, { 'content-type': types.get(extname(filePath)) || 'application/octet-stream' });
    response.end(body);
  } catch {
    response.writeHead(404);
    response.end('not found');
  }
});

await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
const { port } = server.address();
try {
  const [html, app, css, sharedNav] = await Promise.all([
    fetch(`http://127.0.0.1:${port}/`).then((response) => response.text()),
    fetch(`http://127.0.0.1:${port}/assets/app.js`).then((response) => response.text()),
    fetch(`http://127.0.0.1:${port}/assets/styles.css`).then((response) => response.text()),
    fetch(`http://127.0.0.1:${port}/assets/shared-nav.css`).then((response) => response.text()),
  ]);
  if (!html.includes('퀀트 리서치 현황')) throw new Error('results-first page header missing');
  if (!app.includes('parseEtfTracking')) throw new Error('ETF Tracking parser missing');
  if (!app.includes('parseFearAndGreed') || !app.includes('Fear & Greed · 현재 연구 상태')) throw new Error('Fear & Greed parser/panel missing');
  if (!app.includes('parseSox') || !app.includes('SOX 구성종목 · Momentum Top 5')) throw new Error('SOX parser/panel missing');
  if (!app.includes('parseRegime') || !app.includes('현재 국면 · 다음 주 전망')) throw new Error('Regime public-result parser/panel missing');
  if (!app.includes('renderEtfDetailCards') || !app.includes('renderEtfMiniChart')) throw new Error('ETF Tracking detail card/chart renderer missing');
  if (!app.includes('momentumDashboard') || !app.includes('buildDramAxisTicks') || !app.includes('buildEtfPercentAxisTicks')) throw new Error('dashboard readability improvements missing');
  if (!app.includes('renderDramSourceChart') || !app.includes('data-dram-scale="indexed"') || app.includes('dram-value-layer')) throw new Error('DRAM chart collision fix missing');
  if (!html.includes('id="top-nav"')) throw new Error('dynamic top navigation mount missing');
  if (!html.includes('id="summary-grid"')) throw new Error('dynamic dashboard mount missing');
  if (!html.includes('id="research-briefing"') || !html.includes('id="data-health"')) throw new Error('research cockpit mounts missing');
  if (!html.includes('티커·테마 연결')) throw new Error('watchlist copy missing');
  if (!app.includes('PANEL_ADAPTERS')) throw new Error('panel adapter manifest missing');
  if (!app.includes('quant-research-summary') || !app.includes('summaryEntities')) throw new Error('summary contract support missing');
  if (!app.includes('renderDashboardPanels')) throw new Error('manifest-driven panel renderer missing');
  if (!css.includes('.panel')) throw new Error('panel CSS missing');
  if (!css.includes('.etf-detail-grid') || !css.includes('.etf-top10-list')) throw new Error('ETF detail CSS missing');
  if (!css.includes('.health-link')) throw new Error('automation health link CSS missing');
  if (!sharedNav.includes('position: fixed !important') || !sharedNav.includes('--quant-shared-nav-height: 101px')) throw new Error('fixed shared navigation CSS missing');
  console.log('PASS static server smoke served index.html, app/styles, and fixed shared navigation CSS');
} finally {
  await new Promise((resolve) => server.close(resolve));
}
