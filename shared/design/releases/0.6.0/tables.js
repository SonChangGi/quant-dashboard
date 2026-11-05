(()=>{'use strict';
function value(text){const s=text.trim().replaceAll(',','').replaceAll('−','-');if(!s||/^[—–-]$/.test(s))return null;const m=s.match(/^([-+]?(?:\d+(?:\.\d+)?|\.\d+))\s*(%p|pp|%|bps|bp|pt|USD|KRW|원|조원|억원|만원|천원|배|점)?$/);return m?Number(m[1])*({조원:1e12,억원:1e8,만원:1e4,천원:1e3}[m[2]]||1):s;}
if(typeof module!=='undefined')module.exports={value};if(typeof document==='undefined')return;
const collator=new Intl.Collator('ko',{numeric:true,sensitivity:'base'}),states=new WeakMap(),sortMemory=new Map();

function describeSort(table,state,headers){if(!table.closest('.observation-panel'))return;const p=table.closest('.observation-panel').querySelector('p:last-child');if(!p)return;const walk=document.createTreeWalker(p,NodeFilter.SHOW_TEXT);for(let n; (n=walk.nextNode());){const next=n.textContent.replace(/날짜 역순|(?:기준일|가격 종류|제품|카테고리|소스|가격) (?:오름차순|내림차순)/,headers[state.index].textContent.trim()+' '+(state.ascending?'오름차순':'내림차순'));if(next!==n.textContent)n.textContent=next;}}
function sort(table,state){const body=table.tBodies[0],headers=[...table.querySelectorAll('thead tr:last-child th')];if(!body||state.index==null)return;const rows=[...body.rows];if(rows.some(r=>r.cells.length!==headers.length))return;const mapped=rows.map((row,i)=>({row,i,v:value(row.cells[state.index].textContent)}));mapped.sort((a,b)=>a.v===null?b.v===null?a.i-b.i:1:b.v===null?-1:(typeof a.v==='number'&&typeof b.v==='number'?a.v-b.v:collator.compare(String(a.v),String(b.v)))*(state.ascending?1:-1)||a.i-b.i);if(mapped.some((x,i)=>x.row!==rows[i]))mapped.forEach(x=>body.append(x.row));for(const row of rows)for(const cell of row.cells)cell.toggleAttribute('data-qr-sorted',cell.cellIndex===state.index);describeSort(table,state,headers);}
function enhance(){
for(const table of document.querySelectorAll('table')){
for(const cell of table.querySelectorAll('tbody td'))cell.toggleAttribute('data-qr-number',typeof value(cell.textContent)==='number');
const headCells=[...table.querySelectorAll('thead tr:last-child th')],sample=[...(table.tBodies[0]?.rows||[])].slice(0,30);
headCells.forEach((th,i)=>{const cells=sample.map(r=>r.cells[i]).filter(Boolean);th.toggleAttribute('data-qr-number',cells.length>0&&cells.filter(c=>typeof value(c.textContent)==='number').length/cells.length>=.8)});
if(headCells.length>=4&&!table.querySelector('[rowspan],[colspan]'))table.dataset.qrCompare='true';
if(states.has(table)){sort(table,states.get(table));continue}
if(table.dataset.quantTable)continue;table.dataset.quantTable='ready';
if(!table.parentElement||table.closest('[role=dialog]'))continue;
const headers=[...table.querySelectorAll('thead tr:last-child th')],body=table.tBodies[0];
if(!body||!headers.length||table.querySelector('[aria-sort],th button,th a,th[colspan],td[rowspan]'))continue;
if(getComputedStyle(table.parentElement).overflowX==='visible'){const wrap=document.createElement('div');wrap.className='qr-table-scroll';wrap.tabIndex=0;wrap.setAttribute('role','region');wrap.setAttribute('aria-label',(table.caption?.textContent||'데이터 표')+' 스크롤');table.before(wrap);wrap.append(table)}
const key=location.pathname+'|'+[...document.querySelectorAll('table')].indexOf(table)+'|'+headers.map(h=>h.textContent.trim()).join('|');
const state=sortMemory.get(key)||{index:null,ascending:true};states.set(table,state);sortMemory.set(key,state);
headers.forEach((th,index)=>{const label=th.textContent.trim();if(!label)return;const button=document.createElement('button');button.className='qr-sort';button.type='button';button.textContent=label;button.setAttribute('aria-label',label+' 정렬');th.replaceChildren(button);if(state.index===index)th.setAttribute('aria-sort',state.ascending?'ascending':'descending');button.addEventListener('click',()=>{state.ascending=state.index===index?!state.ascending:true;state.index=index;headers.forEach(h=>h.removeAttribute('aria-sort'));th.setAttribute('aria-sort',state.ascending?'ascending':'descending');sort(table,state)})});sort(table,state);
}}
let pending=false;const schedule=()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;enhance()})};function start(){enhance();new MutationObserver(schedule).observe(document.body,{childList:true,subtree:true})}if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
