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
  const [html, app, css] = await Promise.all([
    fetch(`http://127.0.0.1:${port}/`).then((response) => response.text()),
    fetch(`http://127.0.0.1:${port}/assets/app.js`).then((response) => response.text()),
    fetch(`http://127.0.0.1:${port}/assets/styles.css`).then((response) => response.text()),
  ]);
  if (!html.includes('투자 리서치 프로젝트 통합 대시보드')) throw new Error('index hero missing');
  if (!app.includes('parseEtfTracking')) throw new Error('ETF Tracking parser missing');
  if (!app.includes('renderEtfDetailCards') || !app.includes('renderEtfMiniChart')) throw new Error('ETF Tracking detail card/chart renderer missing');
  if (!html.includes('id="top-nav"')) throw new Error('dynamic top navigation mount missing');
  if (!html.includes('id="summary-grid"')) throw new Error('dynamic dashboard mount missing');
  if (!app.includes('PANEL_ADAPTERS')) throw new Error('panel adapter manifest missing');
  if (!app.includes('renderDashboardPanels')) throw new Error('manifest-driven panel renderer missing');
  if (!css.includes('.panel')) throw new Error('panel CSS missing');
  if (!css.includes('.etf-detail-grid') || !css.includes('.etf-top10-list')) throw new Error('ETF detail CSS missing');
  console.log('PASS static server smoke served index.html, assets/app.js, and assets/styles.css');
} finally {
  await new Promise((resolve) => server.close(resolve));
}
