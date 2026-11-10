import assert from 'node:assert/strict';
import test from 'node:test';
import {JSDOM} from 'jsdom';
import '../engine/range.js';

const {createRangeReadout, placeInside, signedChange, zeroBasedAxis} = globalThis.QuantRangeReadout;

test('few visible series stay next to the band; a dense selection remains readable below the plot', () => {
  const dom = new JSDOM('<section><div id="plot"></div><output hidden></output><button>해제</button></section>');
  const {document} = dom.window;
  const plot = document.querySelector('#plot'), output = document.querySelector('output');
  const readout = createRangeReadout(plot, output);
  Object.defineProperties(output, {offsetWidth: {value: 211}, offsetHeight: {value: 74}});
  const geometry = {bounds: {left: 41, top: 18, width: 244, height: 245}, band: [49, 117]};
  const items = [{name: '월별 선택', change: '−10.4%p'}, {name: 'SPY', change: '+68.29%p'}];
  readout.show({start:'2022-08-02', end:'2024-07-16', items}, geometry);
  assert.equal(output.dataset.quantRangeOutput, 'inline');
  assert.equal(output.parentNode.parentNode, plot);
  assert.ok(parseFloat(output.style.left) + output.offsetWidth < 286);
  readout.show({start:'2022-08-02', end:'2024-07-16', items:[...items, {name:'세 번째 계열', change:'—', detail:'관측 없음'}]}, geometry);
  assert.equal(output.dataset.quantRangeOutput, 'below');
  assert.equal(plot.nextElementSibling, output);
  assert.deepEqual([...output.querySelectorAll('.qs-range-value')].map(el=>el.textContent), ['−10.4%p', '+68.29%p', '—']);
  assert.equal(output.querySelectorAll('[role="status"]').length, 0);
  readout.clear();
  assert.equal(output.hidden, true);
  assert.equal(plot.nextElementSibling, output);
  readout.destroy();
  assert.equal(plot.childElementCount, 0);
});

test('prefer the empty side of a range and avoid the selected endpoint at the top edge', () => {
  const bounds = {left: 40, top: 20, width: 700, height: 220}, size = {width: 220, height: 70};
  assert.deepEqual(placeInside(bounds, size, [70,230]), {left:514,top:26});
  assert.deepEqual(placeInside(bounds, size, [70,230], [[705,55]]), {left:514,top:164});
  assert.equal(placeInside(bounds,size,[900,1000]),null);
});

test('a common zero baseline uses only visible fund holdings, with room for the observed maximum', () => {
  assert.deepEqual(zeroBasedAxis([8.4, 5.7, 10.1, null]), {min:0,max:12,interval:2});
  const all = zeroBasedAxis([8.4, 5.7, 10.1, 13.1, null]);
  assert.ok(all.max > 13.1 && all.max <= 15 && all.max/all.interval <= 6);
  assert.equal(signedChange(.00307,'%p'), '+0.0031%p');
  assert.equal(signedChange(0,'%p'), '0%p');
  assert.equal(signedChange(null,'%p'), '—');
});
