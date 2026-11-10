import test from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
import {mountTable,filterNumericRows,columnExtent} from '../engine/table.js';
const columns=[{key:'name',label:'대상',type:'text'},{key:'value',label:'값',type:'number'},{key:'bar',label:'기여',type:'bar'},{key:'trend',label:'흐름',type:'sparkline'}];
const rows=Array.from({length:45},(_,i)=>({id:i,name:`대상 ${i}`,value:i-20,bar:i-20,trend:[i-20,null,i-19]}));
const spec={title:'검사',columns,rows,pageSize:10};
function setup(input=spec){const dom=new JSDOM('<main></main>',{url:'http://localhost'}),doc=dom.window.document;const table=mountTable(doc.querySelector('main'),input);return {dom,doc,table,close(){table.destroy();dom.window.close();}};}
function click(doc,text){const btn=[...doc.querySelectorAll('button')].find(e=>e.textContent===text);assert.ok(btn,`button ${text}`);btn.click();}
function input(doc,selector,value){const e=doc.querySelector(selector);e.value=value;e.dispatchEvent(new doc.defaultView.Event('input',{bubbles:true}));}
test('numeric range is inclusive, rejects non-finite/reversed bounds, and keeps null distinct from zero',()=>{
 assert.deepEqual(filterNumericRows([{n:null},{n:-1},{n:0},{n:1},{n:'0'}],'n',0,1),[{n:0},{n:1}]);
 assert.throws(()=>filterNumericRows([],'n',2,1),/최솟값/);assert.throws(()=>filterNumericRows([],'n',NaN,null),/유한/);
 assert.deepEqual(columnExtent([{v:[null,-1,4]},{v:[2,NaN,8]}],{key:'v',type:'sparkline'}),[-1,8]);
});
test('pagination bounds DOM rows, sorting and filtering reset to first page, and invalid range preserves applied rows',()=>{
 const e=setup();assert.equal(e.doc.querySelectorAll('tr[data-qe-row]').length,10);assert.equal(e.table.getState().filteredRowIds.length,45);
 click(e.doc,'다음');assert.equal(e.table.getState().pageIndex,1);assert.deepEqual(e.table.getState().pageRowIds,Array.from({length:10},(_,i)=>i+10));
 input(e.doc,'[aria-label="범위 최솟값"]','-2');input(e.doc,'[aria-label="범위 최댓값"]','2');click(e.doc,'범위 적용');
 assert.equal(e.table.getState().pageIndex,0);assert.deepEqual(e.table.getState().filteredRowIds,[18,19,20,21,22]);
 input(e.doc,'[aria-label="범위 최솟값"]','9');click(e.doc,'범위 적용');assert.deepEqual(e.table.getState().filteredRowIds,[18,19,20,21,22]);assert.match(e.doc.querySelector('.qe-table-range-error').textContent,/마지막 적용/);
 click(e.doc,'범위 해제');assert.equal(e.table.getState().filteredRowIds.length,45);assert.equal(e.doc.querySelector('.qe-table-range-error').textContent,'');
 e.table.update({...spec,rows:rows.slice(0,3)});assert.equal(e.doc.querySelector('.qe-table-pager').hidden,true);assert.equal(e.doc.querySelectorAll('tr[data-qe-row]').length,3);e.close();
});
test('all cells share full-column scales that survive search; signed bars anchor at zero; matrix retains raw text',()=>{
 const e=setup({...spec,variant:'matrix'});
 assert.equal(e.doc.querySelector('.qe-table-sparkline').dataset.domain,'-20,25');
 const negative=e.doc.querySelector('.qe-table-bar-track');assert.equal(negative.dataset.domain,'-20,24');assert.equal(negative.querySelector('.qe-negative').style.left,'0%');assert.ok(parseFloat(negative.querySelector('.qe-table-bar-zero').style.left)>0);
 const numeric=e.doc.querySelector('td.qe-heat-cell');assert.equal(numeric.textContent,'-20');assert.ok(Number(numeric.dataset.heat)<0);
 input(e.doc,'input[type=search]','대상 0');assert.equal(e.doc.querySelector('.qe-table-sparkline').dataset.domain,'-20,25');assert.equal(e.doc.querySelector('.qe-table-bar-track').dataset.domain,'-20,24');
 e.table.update({...spec,variant:'standard'});assert.equal(e.doc.querySelector('.qe-heat-cell'),null);e.close();
});
test('CSV exports all filtered and sorted rows, rather than only visible page',async()=>{
 const e=setup();let blob;e.dom.window.URL.createObjectURL=value=>{blob=value;return 'blob:test';};e.dom.window.URL.revokeObjectURL=()=>{};e.dom.window.HTMLAnchorElement.prototype.click=()=>{};
 click(e.doc,'다음');click(e.doc,'CSV 저장');let text=await blob.text();assert.equal(text.trim().split('\r\n').length,46);assert.ok(text.includes('"대상 44"'));
 input(e.doc,'[aria-label="범위 최솟값"]','0');input(e.doc,'[aria-label="범위 최댓값"]','15');click(e.doc,'범위 적용');click(e.doc,'다음');click(e.doc,'CSV 저장');text=await blob.text();assert.equal(text.trim().split('\r\n').length,17);assert.ok(!text.includes('"대상 0"'));e.close();
});
test('invalid page size is rejected without replacing visible rows or filter state',()=>{
 const e=setup();const before=e.doc.querySelector('main').innerHTML;
 assert.throws(()=>e.table.update({...spec,pageSize:0}),/pageSize/);assert.equal(e.doc.querySelector('main').innerHTML,before);e.close();
});
test('ranked table displays tied full-source ranks that do not change under filtering',()=>{
 const e=setup({...spec,variant:'ranked',rankBy:'value',rows:[{id:'a',name:'A',value:3},{id:'b',name:'B',value:3},{id:'c',name:'C',value:1},{id:'d',name:'D',value:null}]});
 assert.deepEqual([...e.doc.querySelectorAll('.qe-table-rank')].map(n=>n.textContent),['1','1','3','—']);
 input(e.doc,'input[type=search]','C');assert.equal(e.doc.querySelector('.qe-table-rank').textContent,'3');
 assert.throws(()=>e.table.update({...spec,rankBy:'name'}),/숫자/);e.close();
});

test('filters can be cleared while results remain, and Escape returns focus to the disclosure',()=>{
 const e=setup();input(e.doc,'input[type=search]','대상 1');
 const reset=e.doc.querySelector('.qe-reset-filters');assert.equal(reset.hidden,false);assert.ok(e.table.getState().filteredRowIds.length>0);
 reset.click();assert.equal(e.table.getState().query,'');assert.equal(e.table.getState().filteredRowIds.length,45);assert.equal(reset.hidden,true);
 const chooser=e.doc.querySelector('.qe-table-chooser');chooser.open=true;
 chooser.querySelector('input:not(:disabled)').dispatchEvent(new e.dom.window.KeyboardEvent('keydown',{key:'Escape',bubbles:true}));
 assert.equal(chooser.open,false);assert.equal(e.doc.activeElement,chooser.querySelector('summary'));e.close();
});
