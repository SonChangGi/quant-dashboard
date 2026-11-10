import test from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
import {bindRangeDrag, rangeValues} from '../engine/drag.js';
import {navigateChartWindow, TOUCH_HOLD_MS} from '../engine/touch.js';

function fixture() {
  const dom = new JSDOM('<div><canvas></canvas></div>');
  const el = dom.window.document.querySelector('div');
  const canvas = el.querySelector('canvas');
  const ranges = [], inspections = [], views = [];
  let clears = 0, rawStarts = 0;
  el.getBoundingClientRect = () => ({left: 0, top: 0, width: 100, height: 100});
  canvas.addEventListener('touchstart', () => rawStarts++);
  const cleanup = bindRangeDrag(el, {
    hit: ([x,y], clamp) => clamp || x >= 0 && x <= 100 && y >= 0 && y <= 100 ? Math.round(x) : null,
    onRange: (...v) => ranges.push(v), onClear: () => clears++, onInspect: x => inspections.push(x),
    onNavigate: (...pair) => views.push(pair)
  });
  const emit = (name, props = {}, target = canvas) => {
    const event = new dom.window.Event(name, {bubbles: true, cancelable: true});
    Object.assign(event, {clientX: 20, clientY: 20, pointerId: 1, pointerType: 'mouse', button: 0, detail: 1, ...props});
    target.dispatchEvent(event);
    return event;
  };
  const touch = (type, touches, changedTouches = touches) => emit('touch' + type, {touches, changedTouches});
  return {el, emit, touch, ranges, views, inspections, cleanup, clears: () => clears, rawStarts: () => rawStarts};
}
const finger = (clientX, clientY = 20, identifier = 1) => ({clientX, clientY, identifier});

test('mouse drag reports before release and reverse endpoints remain available', () => {
  const f = fixture();
  f.emit('pointerdown', {clientX:80});
  f.emit('pointermove', {clientX:25});
  assert.deepEqual(f.ranges, [[80,25]]);
  f.emit('pointerup', {clientX:25});
  f.emit('click');
  assert.equal(f.clears(),0);
  f.cleanup();
});

test('tap produces one observation on release and suppresses the renderer duplicate', () => {
  const f = fixture();
  f.touch('start', [finger(20)]);
  assert.deepEqual(f.inspections, []);
  assert.equal(f.rawStarts(), 0);
  f.touch('move', [finger(24, 22)]);
  assert.deepEqual(f.inspections, []);
  f.touch('end', [], [finger(24, 22)]);
  assert.deepEqual(f.inspections, [20]);
  assert.equal(f.emit('click').defaultPrevented, true);
  assert.deepEqual(f.ranges, []);
  f.cleanup();
});

test('early horizontal movement keeps inspecting even after the hold threshold', t => {
  t.mock.timers.enable({apis: ['setTimeout']});
  const f = fixture();
  f.touch('start', [finger(20)]);
  f.touch('move', [finger(40)]);
  t.mock.timers.tick(TOUCH_HOLD_MS + 30);
  f.touch('move', [finger(80)]);
  f.touch('end', [], [finger(80)]);
  assert.deepEqual(f.inspections, [40,80]);
  assert.deepEqual(f.ranges, []);
  f.cleanup();
});

test('hold arms one anchor and compares only after movement', t => {
  t.mock.timers.enable({apis: ['setTimeout']});
  const f = fixture();
  f.touch('start', [finger(70)]);
  t.mock.timers.tick(TOUCH_HOLD_MS);
  assert.equal(f.el.dataset.quantGesture, 'armed');
  assert.deepEqual(f.ranges, []);
  f.touch('move', [finger(22)]);
  assert.deepEqual(f.ranges, [[70,22]]);
  assert.deepEqual(f.inspections, []);
  f.touch('end', [], [finger(22)]);
  assert.equal(f.el.dataset.quantGesture, undefined);
  assert.equal(f.clears(),0);
  f.cleanup();
});

test('vertical scroll, cancellation, and controls do not select', t => {
  t.mock.timers.enable({apis: ['setTimeout']});
  const f = fixture();
  f.touch('start', [finger(20)]);
  assert.equal(f.touch('move', [finger(22,65)]).defaultPrevented, false);
  t.mock.timers.tick(TOUCH_HOLD_MS);
  f.touch('cancel', [], [finger(22,65)]);
  assert.equal(f.clears(),0);
  assert.deepEqual(f.inspections,[]);
  assert.deepEqual(f.ranges,[]);
  const button=f.el.ownerDocument.createElement('button');
  f.el.append(button);
  f.emit('touchstart', {touches:[finger(20)]}, button);
  t.mock.timers.tick(TOUCH_HOLD_MS);
  assert.equal(f.el.dataset.quantGesture,undefined);
  f.cleanup();
});

test('pinch replaces a partial compare and cannot turn into a single-finger drag', t => {
  t.mock.timers.enable({apis: ['setTimeout']});
  const f = fixture();
  f.touch('start', [finger(20)]);
  t.mock.timers.tick(TOUCH_HOLD_MS);
  f.touch('move', [finger(40)]);
  f.touch('start', [finger(40), finger(60,20,2)]);
  f.touch('move', [finger(35), finger(75,20,2)]);
  f.touch('end', [finger(35)], [finger(75,20,2)]);
  f.touch('move', [finger(80)]);
  f.touch('end', [], [finger(80)]);
  assert.equal(f.clears(),1);
  assert.deepEqual(f.ranges, [[20,40]]);
  assert.deepEqual(f.views, [[{center:[50,20],distance:20},{center:[55,20],distance:40}]]);
  assert.deepEqual(f.inspections, []);
  const window=navigateChartWindow(0,100,...f.views[0],0,100);
  assert.ok(Math.abs(window.start-22.5)<1e-9);
  assert.equal(window.end,72.5);
  f.cleanup();
});

test('cleanup removes pending gestures and timer', t => {
  t.mock.timers.enable({apis: ['setTimeout']});
  const f=fixture();
  f.touch('start', [finger(20)]);
  f.cleanup();
  t.mock.timers.tick(TOUCH_HOLD_MS);
  assert.equal(f.el.dataset.quantGesture,undefined);
  f.touch('move',[finger(90)]);
  assert.deepEqual(f.ranges,[]);
});

test('range semantics cover percentage points, zero base, missing and hidden series',()=>{const spec={unit:'%',series:[{name:'return',data:[10,15]},{name:'price',measure:'relative',data:[0,10]},{name:'missing',data:[null,10]},{name:'hidden',data:[1,2]}]};const rows=rangeValues(spec,{startIndex:0,endIndex:1},{hidden:false});assert.equal(rows.length,3);assert.equal(rows[0].change,5);assert.equal(rows[0].unit,'%p');assert.equal(rows[1].change,null);assert.equal(rows[1].difference,10);assert.equal(rows[2].change,null);});
test('fan ranges keep observation and estimate distinct',()=>{const rows=rangeValues({kind:'fan',unit:'원',observed:[100,null],center:[100,110]},{startIndex:0,endIndex:1});assert.equal(rows[0].change,null);assert.ok(Math.abs(rows[1].change-10)<1e-10);});
