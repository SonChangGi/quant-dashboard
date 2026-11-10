import test from 'node:test';
import assert from 'node:assert/strict';
import {sortRows, filterRows, toCSV} from '../engine/table.js';

const columns=[{key:'name',label:'종목',type:'text'},{key:'value',label:'값',type:'number'}];
const rows=Object.freeze([
  Object.freeze({id:'a',name:'MU',value:3}),Object.freeze({id:'b',name:'ADI',value:null}),
  Object.freeze({id:'c',name:'LSCC',value:-2}),Object.freeze({id:'d',name:'TXN',value:3}),
  Object.freeze({id:'e',name:'AMD',value:NaN}),Object.freeze({id:'f',name:'NVDA',value:0})
]);

test('numeric sorts preserve ties, leave null/NaN last in either direction and do not mutate input',()=>{
  assert.deepEqual(sortRows(rows,columns[1]).map(r=>r.id),['c','f','a','d','b','e']);
  assert.deepEqual(sortRows(rows,columns[1],'desc').map(r=>r.id),['a','d','f','c','b','e']);
  assert.deepEqual(rows.map(r=>r.id),['a','b','c','d','e','f']);
  assert.equal(sortRows(rows,columns[1])[0],rows[2]);
});
test('invalid numeric strings are not silently coerced into observations',()=>{
  const data=[{id:1,value:'1,000'},{id:2,value:0},{id:3,value:Infinity}];
  assert.deepEqual(sortRows(data,columns[1]).map(r=>r.id),[2,1,3]);
});
test('search is case insensitive, uses all query terms, and respects declared columns',()=>{
  const data=[{id:'secret',name:'Micron Technology',value:0},{id:'b',name:'Analog Devices',value:2}];
  assert.deepEqual(filterRows(data,' miCRon  tech ',columns),[data[0]]);
  assert.equal(filterRows(data,'secret',columns).length,0);
  assert.deepEqual(filterRows(data,'0',columns),[data[0]]);
  assert.equal(filterRows(rows,'missing',columns).length,0);
  assert.equal(filterRows(rows,'',columns).length,rows.length);
});
test('CSV preserves raw numbers, missing values, commas, quotes and multiline text',()=>{
  const csv=toCSV([{name:'A, "B"\nC',value:-1.234567},{name:'X',value:null}],columns);
  assert.equal(csv,'"종목","값"\r\n"A, ""B""\nC",-1.234567\r\n"X",""');
});
test('CSV neutralizes text formulas including whitespace prefixes but keeps numeric negatives',()=>{
  const data=['=1+1','+SUM(A1:A2)','-2+3','@SUM(A1:A2)','  =1','\t=1','\n@A'].map(name=>({name,value:-2}));
  const lines=toCSV(data,columns);
  for(const row of data)assert.ok(lines.includes('"\''+row.name+'",-2'));
  assert.equal(toCSV([{name:'safe',value:0}],columns),'"종목","값"\r\n"safe",0');
});
test('CSV protects column labels too and does not turn null into zero',()=>{
  assert.equal(toCSV([{x:NaN}],[{key:'x',label:'=DANGER'}]),'"\'=DANGER"\r\n""');
});
