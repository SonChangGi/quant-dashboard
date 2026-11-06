const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
test('editorial display rounds financial decimals while preserving dates, versions and URLs',()=>{
 const texts=['금리 4.00%, 0.50%포인트, 12.345달러, 0.0001234원, 9.50호주달러','2026.11.06 · v0.6.0 · https://example.com/12.345 · ABC12.345원'];
 const nodes=texts.map(textContent=>({textContent,parentElement:{closest:()=>null}}));
 const document={readyState:'complete',body:{},querySelectorAll:()=>[{}],createTreeWalker(){let i=0;return {nextNode:()=>nodes[i++]}}};
 vm.runInNewContext(fs.readFileSync(__dirname+'/../shared/design/releases/0.7.0/news-numbers.js','utf8'),{window:{QuantFormat:require('../shared/design/releases/0.7.0/number.js')},document,NodeFilter:{SHOW_TEXT:4},MutationObserver:class{observe(){}}});
 assert.equal(nodes[0].textContent,'금리 4%, 0.5%포인트, 12.35달러, 0.00012원, 9.5호주달러');
 assert.equal(nodes[1].textContent,texts[1]);
});
