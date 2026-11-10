import test from 'node:test';
import assert from 'node:assert/strict';
import {validateSpec,CHART_KINDS} from '../engine/index.js';
import {charts,tables} from '../demo/fixtures.js';
test('every shipped demo fixture satisfies the actual core contract',()=>{assert.equal(charts.length,CHART_KINDS.length);for(const spec of [...charts,...tables])assert.doesNotThrow(()=>validateSpec(spec),spec.title);});
import {tableLab} from '../demo/fixtures.js';
test('table lab headline changes agree with the same row sparkline endpoints',()=>{for(const r of tableLab.rows){if(r.history.at(-1)===null)assert.equal(r.return,null);else assert.ok(Math.abs(r.return-(r.history.at(-1)/r.history[0]-1)*100)<1e-8);}});


test('research example links resolve to shipped routes and chart patterns',async()=>{
 const {readFile}=await import('node:fs/promises');
 const coverage=JSON.parse(await readFile(new URL('../research/coverage.json',import.meta.url),'utf8'));
 assert.equal(coverage.version,'0.4.2');assert.equal(coverage.items.length,14);
 for(const item of coverage.items){assert.ok(['overview','compose','foundations','tables','charts'].includes(item.route));if(item.pattern)assert.ok(charts.some(c=>c.kind===item.pattern));assert.ok(item.applied&&item.code&&item.url.startsWith('https://'));}
});
