import test from 'node:test';import assert from 'node:assert/strict';import {JSDOM} from 'jsdom';
import {createEngine,validateSpec,metricChange,rebaseComparison,themes,contrastRatio} from '../engine/index.js';
import {resolveDesign,validateDesign} from '../engine/tokens.js';
import {charts,metrics,tableLab} from '../demo/fixtures.js';
test('metric deltas distinguish percentage points, relative percent, and lower-is-better',()=>{
 assert.equal(metricChange(metrics[1]).tone,'positive');assert.ok(Math.abs(metricChange(metrics[2]).value-3.3)<1e-10);assert.equal(metricChange(metrics[2]).unit,'%p');assert.equal(metricChange(metrics[0]).tone,'neutral');
 const zero={...metrics[0],comparison:{...metrics[0].comparison,value:0}};assert.equal(metricChange(zero).value,null);assert.throws(()=>validateSpec({...zero,comparison:{...zero.comparison,value:-1}}),/음수/);assert.equal(metricChange({...metrics[0],value:null}),null);
});
test('rebase uses one common starting observation, preserves gaps and never mutates sources',()=>{
 const before=JSON.stringify(charts[0]),output=rebaseComparison(charts[0],5);assert.equal(output.x.length,3);assert.ok(output.series.every(s=>s.data[0]===100));assert.ok(Math.abs(output.series[0].data.at(-1)-125/117*100)<1e-10);assert.equal(JSON.stringify(charts[0]),before);
 const gap=structuredClone(charts[0]);gap.series[0].data[6]=null;assert.equal(rebaseComparison(gap,5).series[0].data[1],null);gap.series[0].data[5]=0;assert.throws(()=>rebaseComparison(gap,5),/공통 시작일/);assert.throws(()=>rebaseComparison(charts[0],7),/두 관측/);
});
test('all shipped presets retain readable foreground and muted text on the card surface',()=>{
 for(const theme of ['light','dark'])for(const accent of ['cyan','blue','violet']){const t=resolveDesign(theme,themes[theme],validateDesign({accent}));assert.ok(contrastRatio(t.text,t.surface)>=4.5);assert.ok(contrastRatio(t.muted,t.surface)>=4.5);assert.ok(contrastRatio(t.accent,t.surface)>=4.5);}
});
test('design configuration rejects invalid changes atomically and is isolated per engine',()=>{
 const dom=new JSDOM('<div id="a"></div><div id="b"></div>');const a=dom.window.document.querySelector('#a'),b=dom.window.document.querySelector('#b');const e=createEngine(a),f=createEngine(b,{theme:'light'});const view=e.mount(a,metrics[0]);
 e.configure({density:'compact',accent:'violet',corners:'square'});assert.equal(a.style.getPropertyValue('--qe-card-inset'),'20px');assert.equal(b.style.getPropertyValue('--qe-card-inset'),'24px');assert.equal(view.getState().value,125);const before=e.getDesign();assert.throws(()=>e.configure({accent:'red'}));assert.deepEqual(e.getDesign(),before);e.setTheme('light');assert.equal(e.getDesign().accent,'violet');assert.equal(a.style.getPropertyValue('--qe-accent'),'#7351b7');e.destroy();f.destroy();dom.window.close();
});
test('metric gaps remain separate paths and tiny nonzero measurements are not rounded to zero',()=>{
 const dom=new JSDOM('<main></main>'),root=dom.window.document.querySelector('main'),e=createEngine(root);const m=e.mount(root,{...metrics[0],value:.000001,history:[1,null,2]});assert.match(root.querySelector('.qe-metric-value').textContent,/0.000001/);assert.equal((root.querySelector('path').getAttribute('d').match(/M/g)||[]).length,2);m.destroy();e.destroy();dom.window.close();
});
test('table paging and rank specs are checked at core boundary',()=>{assert.doesNotThrow(()=>validateSpec(tableLab));assert.throws(()=>validateSpec({...tableLab,pageSize:0}),/pageSize/);assert.throws(()=>validateSpec({...tableLab,rankBy:'name'}),/rankBy/);});
test('small table observations remain visibly nonzero and selection callback cannot mutate mounted evidence',()=>{
 const dom=new JSDOM('<main></main>'),root=dom.window.document.querySelector('main'),e=createEngine(root);const view=e.mount(root,{kind:'table',title:'정확값',columns:[{key:'name',label:'대상',type:'text'},{key:'n',label:'변화',type:'percent'}],rows:[{id:'a',name:'A',n:.0001}]},{onSelect:r=>r.n=99});
 assert.match(root.querySelector('tbody').textContent,/0.0001%/);root.querySelector('tr[data-qe-row]').click();e.setTheme('light');assert.match(root.querySelector('tbody').textContent,/0.0001%/);view.destroy();e.destroy();dom.window.close();
});
import {buildOption} from '../engine/charts.js';
test('treemap label text has readable contrast on actual nested fills and parent bands in both themes',()=>{
 for(const theme of Object.values(themes)){const option=buildOption(charts.find(s=>s.kind==='treemap'),theme);const visit=nodes=>{for(const node of nodes){assert.ok(contrastRatio(node.label.color,node.itemStyle.color)>=4.5);assert.ok(contrastRatio(node.upperLabel.color,node.itemStyle.borderColor)>=4.5);if(node.children)visit(node.children);}};visit(option.series[0].data);}
});
test('heatmap exact-value labels use contrast appropriate to the actual signed cell fill',()=>{
 for(const theme of Object.values(themes)){const o=buildOption(charts.find(s=>s.kind==='heatmap'),theme);for(const d of o.series[0].data)assert.ok(contrastRatio(d.label.color,d.itemStyle.color)>=4.5);assert.equal(o.series[0].data.length,7);}
});
