const {test}=require('node:test');const assert=require('node:assert/strict');const {number}=require('../shared/design/releases/0.7.0/number.js');
const cases=[[475,'475'],[475.000,'475'],[12.5,'12.5'],[12.345,'12.35'],[-12.345,'-12.35'],[0.0001234,'0.00012'],[-0.0001234,'-0.00012'],[0.001234,'0.0012'],[0.009999,'0.01'],[0.01234,'0.01'],[1234567.891,'1,234,567.89'],[-0,'0'],[null,'—'],[NaN,'—'],[Infinity,'—'],['','—']];
for(const [value,expected]of cases)test(String(value)+' → '+expected,()=>assert.equal(number(value),expected));
test('displayed percent controls tiny precision',()=>{assert.equal(number(.000123,{style:'percent'}),'0.01%');assert.equal(number(.00000123,{style:'percent'}),'0.00012%');assert.equal(number(.123456,{style:'percent'}),'12.35%')});
test('old per-view precision cannot override shared policy',()=>{assert.equal(number(1.2345,{minimumFractionDigits:4,maximumFractionDigits:4}),'1.23');assert.equal(number(475,{minimumFractionDigits:2,maximumFractionDigits:2}),'475')});
test('currency and sign preserve semantics',()=>{assert.equal(number(12.345,{style:'currency',currency:'USD'}),'US$12.35');assert.equal(number(1.25,{signDisplay:'always'}),'+1.25')});
test('tiny observations survive beyond fixed decimal cutoffs',()=>assert.equal(number(0.0000000001234),'0.00000000012'));
