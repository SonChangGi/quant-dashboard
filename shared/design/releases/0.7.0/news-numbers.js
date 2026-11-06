/* Financial numbers in editorial text only; stored articles and dates stay intact. */
(()=>{'use strict';
const money=/(?<![\w.])([+-]?(?:\d{1,3}(?:,\d{3})+|\d+)\.\d+)(?=\s*(?:%p|%|(?:호주|홍콩|캐나다|미국)?달러|원|유로|파운드|엔|배럴|배|포인트|bp|bps)(?![A-Za-z]))/g;
function formatText(text){return text.replace(money,n=>window.QuantFormat.number(Number(n.replaceAll(',','')),{useGrouping:n.includes(',')}));}
function update(){for(const el of document.querySelectorAll('.issue,.weekly-spotlight,article.card')){const walk=document.createTreeWalker(el,NodeFilter.SHOW_TEXT);for(let n;(n=walk.nextNode());){if(n.parentElement.closest('script,style,code,pre'))continue;const next=formatText(n.textContent);if(next!==n.textContent)n.textContent=next}}}
function start(){update();let pending=false;new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;update()})}).observe(document.body,{childList:true,subtree:true})}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
