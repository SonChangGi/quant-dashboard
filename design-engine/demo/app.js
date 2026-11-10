document.documentElement.dataset.theme='dark';
import {createEngine,themes,contrastRatio,rebaseComparison} from '../engine/index.js?v=042';
import {charts,tables,principles,metrics,tableLab,chartCategories} from './fixtures.js?v=042';
import {renderResearch} from './research-view.js?v=042';
const root=document.querySelector('#app'),content=document.querySelector('#content');
const engine=createEngine(root);let mounts=new Set(),revision=0,cleanup=()=>{};
const el=(tag,cls,text)=>{const n=document.createElement(tag);n.className=cls||'';if(text!==undefined)n.textContent=text;return n;};
function mount(host,spec,events){const box=el('div');host.append(box);const view=engine.mount(box,spec,events);const dispose=view.destroy;view.destroy=()=>{dispose();mounts.delete(view);};mounts.add(view);return view;}
function head(kicker,title,description){content.append(el('p','eyebrow',kicker),el('h1','',title),el('p','intro',description));}
function grid(cls='grid'){const g=el('div',cls);content.append(g);return g;}
function section(title,description){const h=el('div','section-head');h.append(el('h2','',title),el('span','',description));content.append(h);}
function button(text,fn){const b=el('button','',text);b.type='button';b.onclick=fn;return b;}
function overview(){
 head('Quant / Interface lab · 0.4.2','비교가 되는 화면을 만듭니다.','한눈에 보는 요약에서 숫자의 근거까지. 개인 연구 페이지를 위한 시각 언어와 작동하는 공통 엔진입니다.');
 const actions=el('div','hero-actions');for(const [href,text] of [['#compose','비교 워크스페이스 열기 →'],['#charts','17종 차트 살펴보기'],['#research','새 리서치와 적용 근거']]){const a=el('a','',text);a.href=href;actions.append(a);}content.append(actions);
 const kpis=grid('metric-grid overview-metrics');metrics.forEach(s=>mount(kpis,s));
 section('같은 기준으로 읽기','합성 예제 · 시작값 100 · 동일한 8개 관측');
 const g=grid('showcase-grid');mount(g,charts[0]);const note=el('aside','decision-note');note.append(el('span','mini-label','비교의 조건'),el('h2','','성과보다 먼저, 비교 기준'),el('p','','기간을 바꾸면 차트·요약 카드·표가 함께 갱신됩니다. 기준 계열도 같은 화면에서 선택하고 확인합니다.'));
 const dl=el('dl','contract-list');for(const [k,v]of [['기준','공통 시작 관측 = 100'],['빈 값','0으로 바꾸지 않음'],['조작','선택과 확대를 구분'],['출처','합성 / 관측 / 예측 구분']]){dl.append(el('dt','',k),el('dd','',v));}note.append(dl);const link=el('a','','직접 비교해 보기 ↗');link.href='#compose';note.append(link);g.append(note);
 section('표현의 범위를 넓히기','예측 범위 · 목표 대비 실적 · 계층별 구성');const examples=grid();[14,15,16].forEach(i=>mount(examples,charts[i]));
 section('하나의 엔진에서 바뀌는 것','토큰 → 카드 → 차트 → 표');const p=el('div','principles');principles.forEach(([num,title,description])=>{const c=el('article','principle');c.append(el('small','',num),el('h3','',title),el('p','',description));p.append(c);});content.append(p);
}
function chartLibrary(){
 head('차트 라이브러리','질문에 맞는 시각화를 고릅니다.','추세·분포·관계·구성·불확실성, 17가지 패턴.');
 const bar=el('div','filterbar'),search=el('input');search.type='search';search.placeholder='차트 이름·종류 검색';search.setAttribute('aria-label','차트 검색');search.value=new URLSearchParams(location.search).get('pattern')||'';bar.append(search);content.append(bar);
 const categories=el('div','filter-chips');let selected='전체';const buttons=[];
 ['전체',...new Set(Object.values(chartCategories))].forEach(c=>{const b=button(c,()=>{selected=c;draw();});buttons.push([c,b]);categories.append(b);});content.append(categories);
 const count=el('p','result-count');count.setAttribute('role','status');content.append(count);const g=grid('grid chart-grid');
 const draw=()=>{mounts.forEach(m=>m.destroy());mounts=new Set();g.replaceChildren();buttons.forEach(([c,b])=>{b.classList.toggle('active',selected===c);b.setAttribute('aria-pressed',String(selected===c));});const found=charts.filter(s=>(selected==='전체'||chartCategories[s.kind]===selected)&&(s.title+s.kind+s.description).toLowerCase().includes(search.value.toLowerCase()));count.textContent=`${found.length} / ${charts.length}개 패턴`;for(const spec of found){const v=mount(g,spec);const badge=el('span','pattern-label',`${chartCategories[spec.kind]} / ${spec.kind}`);v.element.querySelector('header').prepend(badge);}if(!found.length){const empty=el('div','panel');empty.append(el('p','','일치하는 패턴이 없습니다.'),button('검색 초기화',()=>{selected='전체';search.value='';draw();}));g.append(empty);}};
 search.oninput=draw;draw();
}
function tableLibrary(){
 head('데이터 표','정확한 숫자와 패턴을 함께 읽습니다.','필요한 행을 찾고, 같은 척도로 비교합니다.');
 mount(content,tableLab);section('읽는 목적에 따른 구성','비교 · 전체 순위 · 그룹 · 부호 행렬');const g=grid();tables.forEach(s=>mount(g,s).element.parentElement.classList.add('wide'));
}
function composition(){
 head('비교 워크스페이스','같은 기준에서 비교합니다.','');
 const bar=el('div','workspace-controls'),periodLabel=el('label','','표시 기간'),period=el('select');period.setAttribute('aria-label','비교 기간');
 for(const [v,t]of [[0,'전체 · 01–08월'],[2,'최근 6개 관측 · 03–08월'],[5,'최근 3개 관측 · 06–08월']]){const o=el('option','',t);o.value=v;period.append(o);}periodLabel.append(period);bar.append(periodLabel);
 const choices=el('fieldset','series-choices');choices.append(el('legend','','비교 계열'));
 const selected=new Set(charts[0].series.map(s=>s.name)),checkboxes=[];
 charts[0].series.forEach(s=>{const label=el('label'),input=el('input');input.type='checkbox';input.checked=true;input.onchange=()=>{input.checked?selected.add(s.name):selected.delete(s.name);line.renderer.setLegend(s.name,input.checked);paintSummary();};checkboxes.push([s.name,input]);label.append(input,document.createTextNode(s.name));choices.append(label);});bar.append(choices);content.append(bar);
 const status=el('div','notice');status.hidden=true;status.setAttribute('role','status');content.append(status);
 const cards=grid('metric-grid summary-strip'),lineHost=el('div'),tableHost=el('div');content.append(lineHost,tableHost);tableHost.style.marginTop='22px';let summaries=[],line,spec,range=null;
 function rangeSummary(){status.hidden=!range;if(!range)return;const changes=spec.series.filter(s=>selected.has(s.name)).map(s=>{const a=s.data[range.startIndex],b=s.data[range.endIndex];const n=a!==null&&b!==null&&a>0?(b/a-1)*100:null;return `${s.name} ${n===null?'미제공':(n>0?'+':'')+n.toFixed(2)+'%'}`;});status.textContent=`선택 구간 ${range.start}–${range.end} · ${changes.join(' / ')}`;}
 function paintSummary(){
  summaries.forEach(v=>v.destroy());summaries=[];cards.replaceChildren();tableHost.replaceChildren();
  checkboxes.forEach(([name,input])=>{input.checked=selected.has(name);input.disabled=selected.size===1&&input.checked;});
  const rows=spec.series.filter(s=>selected.has(s.name)).map(s=>({id:s.id||s.name,name:s.name,end:s.data.at(-1),return:s.data.at(-1)===null?null:s.data.at(-1)-100,history:s.data}));
  const best=rows.filter(r=>r.return!==null).sort((a,b)=>b.return-a.return)[0];
  for(const card of [{kind:'metric',title:'선택 계열',value:rows.length,unit:'개',precision:0,source:'현재 선택'},{kind:'metric',title:'공통 관측 구간',value:spec.x.length,unit:'개',precision:0,source:`${spec.x[0]}–${spec.x.at(-1)}`},{kind:'metric',title:best?`최대 기간 변화 · ${best.name}`:'기간 변화',value:best?.return??null,unit:'%',precision:2,source:'합성 예제'}])summaries.push(mount(cards,card));
  summaries.push(mount(tableHost,{...tables[0],title:'같은 구간의 정확한 값',description:'기간 변화 = 종료 기준값 − 100',rows,columns:[{key:'name',label:'계열',type:'text'},{key:'end',label:'종료 기준값',type:'number'},{key:'return',label:'기간 변화',type:'percent'},{key:'history',label:'공통 척도 추이',type:'sparkline'}]},{onSelect:()=>line.renderer.select(spec.x.length-1)}));rangeSummary();
 }
 function update(){
  line?.destroy();lineHost.replaceChildren();range=null;status.hidden=true;
  const rebased=rebaseComparison(charts[0],+period.value);spec={...rebased,unit:'지수',brush:true,title:'기준값 100에서 시작하는 비교',description:`${rebased.x[0]}–${rebased.x.at(-1)} · 시작값 100`,series:rebased.series.map(s=>({...s,visible:selected.has(s.name)}))};
  line=mount(lineHost,spec,{onLegendChange:visible=>{const names=spec.series.filter(s=>visible[s.name]!==false).map(s=>s.name);if(!names.length){const keep=[...selected][0];line.renderer.setLegend(keep,true);return;}selected.clear();names.forEach(n=>selected.add(n));paintSummary();},onRange:value=>{range=value;rangeSummary();}});paintSummary();
 }
 period.onchange=update;update();
}

function studio(){
 head('스펙 스튜디오','수정하고, 검증하고, 재사용합니다.','JSON으로 편집하는 예제');
 const specs=[...charts,...metrics],bar=el('div','filterbar'),select=el('select');select.setAttribute('aria-label','편집할 예제');specs.forEach((s,i)=>{const o=el('option','',s.kind+' · '+s.title);o.value=i;select.append(o);});bar.append(select);content.append(bar);
 const g=grid(),panel=el('div','panel'),host=el('div');g.append(panel,host);const editor=el('textarea','editor');editor.setAttribute('aria-label','JSON spec');editor.spellcheck=false;const message=el('p');message.setAttribute('role','status');let view;
 const apply=button('스펙 적용',()=>{try{view.update(JSON.parse(editor.value));message.className='';message.textContent='적용 완료';}catch(e){message.className='error';message.textContent=e.message+' 마지막 정상 결과를 유지합니다.';}});
 const reset=()=>{view?.destroy();host.replaceChildren();editor.value=JSON.stringify(specs[+select.value],null,2);view=mount(host,specs[+select.value]);message.textContent='';};const restore=button('예제 복원',()=>{reset();restore.hidden=true;});restore.hidden=true;editor.oninput=()=>{restore.hidden=editor.value===JSON.stringify(specs[+select.value],null,2);};panel.append(editor,apply,restore,message);select.onchange=()=>{reset();restore.hidden=true;};reset();
}
function foundations(){
 head('토큰과 카드','취향은 조절하고, 의미는 유지합니다.','강조색·간격·모서리를 조절해 보세요.');
 const controls=el('div','token-controls');const current=engine.getDesign();const names={density:'정보 밀도',corners:'모서리',accent:'강조색'};const labels={comfortable:'여유롭게',compact:'촘촘하게',soft:'부드럽게',square:'각지게',cyan:'청록',blue:'파랑',violet:'보라'};
 for(const [key,values]of Object.entries({density:['comfortable','compact'],corners:['soft','square'],accent:['cyan','blue','violet']})){const label=el('label','',names[key]),select=el('select');select.setAttribute('aria-label',names[key]);for(const v of values){const o=el('option','',labels[v]);o.value=v;o.selected=current[key]===v;select.append(o);}select.onchange=()=>{engine.configure({[key]:select.value});refresh();};label.append(select);controls.append(label);}const resetDesign=button('기본값 복원',()=>{engine.configure({density:'comfortable',corners:'soft',accent:'cyan'});controls.querySelectorAll('select').forEach((s,i)=>s.value=['comfortable','soft','cyan'][i]);refresh();});controls.append(resetDesign);content.append(controls);
 const preview=grid('metric-grid');metrics.forEach(s=>mount(preview,s));
 const tokenPanel=el('div','panel');tokenPanel.style.marginTop='24px';tokenPanel.append(el('h2','','현재 디자인 계약'));const swatches=el('div','swatches'),contrast=el('p'),code=el('pre','code');const tokenDetails=el('details','token-details');tokenDetails.append(el('summary','','설정·대비'),contrast,code);tokenPanel.append(swatches,tokenDetails);const exportButton=button('설정 JSON 저장',()=>{const blob=new Blob([JSON.stringify({version:'0.4.2',theme:engine.getTheme(),design:engine.getDesign()},null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=el('a');a.href=url;a.download='quant-design.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});tokenDetails.append(exportButton);content.append(tokenPanel);
 function refresh(){const design=engine.getDesign();resetDesign.hidden=design.density==='comfortable'&&design.corners==='soft'&&design.accent==='cyan';const styles=getComputedStyle(root);swatches.replaceChildren();['bg','surface','raised','text','muted','accent','positive','negative'].forEach(t=>{const wrap=el('div'),swatch=el('div','swatch');swatch.style.background=`var(--qe-${t})`;wrap.append(swatch,el('small','',t));swatches.append(wrap);});const fg=styles.getPropertyValue('--qe-text').trim(),bg=styles.getPropertyValue('--qe-surface').trim(),muted=styles.getPropertyValue('--qe-muted').trim();contrast.textContent=`표면 대비 · 본문 ${contrastRatio(fg,bg).toFixed(2)}:1 / 보조 ${contrastRatio(muted,bg).toFixed(2)}:1 · 일반 텍스트 AA 기준 4.5:1`;code.textContent=JSON.stringify({theme:engine.getTheme(),design:engine.getDesign()},null,2);}
 refresh();content.addEventListener('qe-theme-change',refresh);cleanup=()=>content.removeEventListener('qe-theme-change',refresh);
 section('비교 방향을 명시하는 카드','숫자의 증가 ≠ 항상 좋은 변화');const examples=grid('metric-grid');[ {...metrics[1],title:'비용 감소는 개선',value:142,comparison:{value:180,label:'이전 대비 · 작을수록 좋음',mode:'absolute',desirable:'lower'}},{...metrics[1],title:'값의 증가는 중립',value:220,comparison:{value:180,label:'이전 대비 · 판단하지 않음',mode:'absolute',desirable:'neutral'}},{...metrics[0],title:'기준값이 0인 변화율',value:12,comparison:{value:0,label:'0 대비',mode:'relative',desirable:'neutral'},history:[]}].forEach(s=>mount(examples,s));
 section('긴 제목과 종목 카드','같은 여백 · 같은 숫자 정렬');const spacing=grid('metric-grid');[{...metrics[0],title:'SOX · 반도체 종목 종합 평가',value:86,unit:'점',history:[],comparison:undefined},{...metrics[1],title:'MU · Micron Technology',value:72,unit:'점',history:[],comparison:undefined},{...metrics[2],title:'LSCC · Lattice Semiconductor',value:null,unit:'점',history:[],comparison:undefined}].forEach(s=>mount(spacing,s));
 section('화면 문구','짧게, 한 번만');const copy=el('p','intro','결과와 동작을 먼저 보여줍니다. 반복 설명과 상투적인 제약·한계 문구는 삭제하고, 필요한 기준은 해당 값 곁에 한 번만 표시합니다.');content.append(copy);
 section('상태도 하나의 계약','로딩 · 빈 결과 · 복구 가능한 오류');const g=grid();mount(g,{kind:'status',state:'loading',title:'로딩'});mount(g,{kind:'status',state:'empty',title:'빈 결과'});let retryView;retryView=mount(g,{kind:'status',state:'error',title:'오류와 재시도'},{onRetry:()=>{retryView.update({kind:'status',state:'loading',title:'다시 확인 중'});setTimeout(()=>{try{retryView.update({kind:'status',state:'empty',title:'확인 완료',description:'합성 상태 예제 · 요청 완료 후 빈 결과'});}catch{}},600);}});
}
async function render(){const rev=++revision;cleanup();cleanup=()=>{};mounts.forEach(m=>m.destroy());mounts=new Set();content.replaceChildren();const route=location.hash.slice(1)||'overview';document.querySelectorAll('nav a').forEach(a=>{a.classList.toggle('active',a.hash==='#'+route);if(a.hash==='#'+route)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');});document.querySelector('#breadcrumb').textContent=document.querySelector('nav a.active')?.childNodes[0].textContent||'시작하기';try{if(route==='overview')overview();else if(route==='charts')chartLibrary();else if(route==='tables')tableLibrary();else if(route==='compose')composition();else if(route==='studio')studio();else if(route==='foundations')foundations();else if(route==='research')await renderResearch(content,{el,head,grid,isCurrent:()=>rev===revision});else location.hash='overview';}catch(error){content.append(el('p','error','화면을 구성하지 못했습니다: '+error.message));}}
document.querySelector('#theme').onclick=()=>{const next=engine.getTheme()==='dark'?'light':'dark';document.documentElement.dataset.theme=next;engine.setTheme(next);document.querySelector('#theme').textContent=next==='dark'?'라이트 모드':'다크 모드';content.dispatchEvent(new Event('qe-theme-change'));};
window.addEventListener('hashchange',()=>{window.scrollTo(0,0);render();});render();
