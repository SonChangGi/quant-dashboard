import './range.js';
import {rangeValues} from './drag.js?v=043';
import {buildOption,mountChart,CHART_KINDS} from './charts.js?v=044';
import {mountTable} from './table.js?v=043';
import {validateMetric,mountMetric} from './metrics.js?v=043';
import {designDefaults,validateDesign,resolveDesign} from './tokens.js?v=043';
export {metricChange} from './metrics.js?v=043';
export {designDefaults,designPresets} from './tokens.js?v=043';
export const themes = Object.freeze({dark:{bg:'#101521',surface:'#171e2d',raised:'#222d42',text:'#edf2fb',muted:'#a8b5cc',border:'#394961',grid:'#2b3850',accent:'#78d9e1',positive:'#83dfb3',negative:'#ffa6b4',palette:['#78d9e1','#edc782','#b6aaff','#f6a4ce','#a6d697','#90baff']},light:{bg:'#f2f5fa',surface:'#ffffff',raised:'#e9eff7',text:'#18253a',muted:'#526480',border:'#c8d3e3',grid:'#dde5f0',accent:'#006970',positive:'#166b48',negative:'#a53349',palette:['#006970','#8a5b11','#5d48a9','#96386e','#426b2e','#2558a3']}});
export {CHART_KINDS};
export function validateSpec(spec) {
  if (!spec || typeof spec.title !== 'string' || !spec.title.trim()) throw new TypeError('title이 필요합니다.');
  if(spec.kind==='metric'){validateMetric(spec);return spec;}
  if (spec.kind === 'status') {
    if (!['loading','empty','error'].includes(spec.state)) throw new TypeError('status state가 필요합니다.');
    return spec;
  }
  if (spec.kind === 'table') {
    if (!Array.isArray(spec.columns) || !spec.columns.length || !Array.isArray(spec.rows)) throw new TypeError('columns와 rows가 필요합니다.');
    const types = ['text','number','percent','sparkline','bar'];
    for (const column of spec.columns) {
      if (!column || typeof column.key !== 'string' || !column.key.trim()) throw new TypeError('열 key는 비어 있지 않은 문자열이어야 합니다.');
      if (typeof column.label !== 'string' || !column.label.trim()) throw new TypeError('열 label이 필요합니다.');
      if (!types.includes(column.type)) throw new TypeError('지원하지 않는 열 type입니다.');
    }
    if (spec.rows.some(row => !row || !['string','number'].includes(typeof row.id) ||
      (typeof row.id === 'number' ? !Number.isFinite(row.id) : !row.id.trim())) ||
      new Set(spec.rows.map(row => String(row.id))).size !== spec.rows.length) throw new TypeError('행 id는 비어 있지 않고 고유해야 합니다.');
    if (new Set(spec.columns.map(column => column.key)).size !== spec.columns.length) throw new TypeError('열 key는 고유해야 합니다.');
    if (spec.variant != null && !['standard','matrix','ranked','grouped'].includes(spec.variant)) throw new TypeError('지원하지 않는 table variant입니다.');
    if(spec.pageSize!=null&&(!Number.isInteger(spec.pageSize)||spec.pageSize<1||spec.pageSize>500))throw new TypeError('pageSize는 1~500 정수입니다.');
    if(spec.rankBy!=null&&!spec.columns.some(c=>c.key===spec.rankBy&&['number','percent','bar'].includes(c.type)))throw new TypeError('rankBy는 숫자 열이어야 합니다.');
    if(spec.rankDirection!=null&&!['asc','desc'].includes(spec.rankDirection))throw new TypeError('rankDirection은 asc/desc입니다.');
  } else {
    buildOption(spec); // Structural and numeric checks precede arithmetic validation.
    if (spec.kind === 'waterfall' && spec.verifyTotals) {
      let total = spec.initial ?? 0;
      for (const [index, row] of spec.rows.entries()) {
        if (row.type === 'total') {
          // An opening total can define the starting balance when initial is absent.
          if ((index > 0 || spec.initial !== undefined) && Math.abs(total - row.value) > 1e-8)
            throw new TypeError('waterfall 합계가 기여도 합과 다릅니다.');
          total = row.value;
        } else total += row.value;
      }
    }
  }
  return spec;
}

export function createEngine(root, {theme = 'dark', echarts = globalThis.echarts, design = designDefaults} = {}) {
  if (!root?.ownerDocument || root.nodeType !== 1) throw new TypeError('root DOM element가 필요합니다.');
  let currentTheme, disposed = false, currentDesign=validateDesign(design), resolvedTokens;
  const handles = new Set(), doc = root.ownerDocument;
  function ensureAlive() { if (disposed) throw new Error('destroy된 engine입니다.'); }
  function setTheme(value) {
    ensureAlive();
    if (!Object.hasOwn(themes, value)) throw new TypeError('dark 또는 light 테마를 선택하세요.');
    currentTheme = value; root.dataset.qeTheme = value; resolvedTokens=resolveDesign(value,themes[value],currentDesign);
    for (const [key, token] of Object.entries(resolvedTokens)) if (key !== 'palette') root.style.setProperty('--qe-' + key, token);
    for (const handle of handles) handle.renderer.setTheme(handle.kind === 'table' ? value : resolvedTokens);
  }
  setTheme(theme);
  function mount(host, input, {onSelect, onRange, onRetry, onLegendChange} = {}) {
    ensureAlive();
    if (host?.nodeType !== 1 || !root.contains(host)) throw new TypeError('host는 engine root 내부 요소여야 합니다.');
    let spec = structuredClone(input), dead = false, renderer, rangePresenter, syncChart=()=>{}, paintRange=()=>{};
    validateSpec(spec);
    const frame = doc.createElement('section'); frame.className = 'qe-frame';frame.setAttribute('data-quant-card','');
    frame.dataset.kind=spec.kind;const header = doc.createElement('header'); header.className = 'qe-frame-header';
    const title = doc.createElement('h2'), desc = doc.createElement('p'), meta = doc.createElement('small');
    header.append(title, desc, meta);
    const body = doc.createElement('div'); body.className = 'qe-chart-body';
    const controls = doc.createElement('div'); controls.className = 'qe-controls';
    const readout = doc.createElement('output'); readout.className = 'qe-readout';readout.dataset.quantChartReadout=''; readout.setAttribute('aria-live', 'polite');
    frame.append(header, controls, body, readout);
    const entry = {kind: spec.kind, get renderer() { return renderer; }, destroy};
    function paint() {
      title.textContent = spec.title; desc.textContent = spec.description || '';
      meta.textContent = [spec.dataState==='simulated'?'합성 예제':spec.dataState==='forecast'?'예측':spec.dataState==='observed'?'관측':null,spec.asOf?`기준 ${spec.asOf}`:null,spec.source || (spec.kind==='status'?'':'출처 미지정'), spec.unit && `단위 ${spec.unit}`].filter(Boolean).join(' · ');
    }
    function select(event) {
      readout.replaceChildren();
      const format=value=>value==null?'미제공':typeof value==='number'?new Intl.NumberFormat('ko-KR',value!==0&&Math.abs(value)<.01?{maximumSignificantDigits:3}:{maximumFractionDigits:2}).format(value):String(value);
      if(event?.series){const date=doc.createElement('strong');date.textContent=event.x??'';readout.append(date);for(const series of event.series){const item=doc.createElement('span');item.textContent=`${series.name} ${format(series.value)}`;readout.append(item);}}
      else readout.textContent=!event?'':`선택: ${event.name??event.id??''}`;
      onSelect?.(event == null ? null : structuredClone(event));syncChart();
    }
    function destroy() {
      if (dead) return;
      dead = true;
      try { rangePresenter?.destroy(); renderer?.destroy(); } finally { frame.remove(); handles.delete(entry); }
    }
    host.append(frame); // ECharts requires the host to participate in layout.
    try {
      if(spec.kind==='metric'){renderer=mountMetric(body,spec);}
      else if (spec.kind === 'status') {
        body.className = 'qe-status';
        let status = spec;
        const statusPaint = () => {
          body.replaceChildren(); body.setAttribute('role', status.state === 'error' ? 'alert' : 'status');
          body.setAttribute('aria-busy', String(status.state === 'loading'));
          body.append(doc.createTextNode(status.state === 'loading' ? '자료를 불러오고 있습니다.' : status.state === 'empty' ? '조건에 맞는 자료가 없습니다.' : '자료를 표시하지 못했습니다.'));
          if (status.state === 'error' && onRetry) {
            const retry = doc.createElement('button'); retry.type = 'button'; retry.textContent = '다시 시도'; retry.onclick = onRetry; body.append(retry);
          }
        };
        statusPaint();
        renderer = {update(next) { status = next; statusPaint(); }, setTheme() {}, destroy() {}, getState: () => ({state: status.state})};
      } else if (spec.kind === 'table') {
        body.className = 'qe-table-body'; renderer = mountTable(body, spec, {onSelect: select});
        renderer.setTheme(currentTheme);
      } else {
        const rangeOutput=doc.createElement('output');rangeOutput.className='qe-range-readout';rangeOutput.dataset.quantChartReadout='';rangeOutput.setAttribute('aria-live','polite');rangeOutput.hidden=true;frame.append(rangeOutput);
        renderer = mountChart(body, spec, {echarts, tokens: resolvedTokens, rangeReadout:()=>rangeOutput, onSelect: select, onRange:value=>{paintRange(value);onRange?.(value);}, onLegendChange, onStateChange:()=>syncChart()});
        const presentation=globalThis.QuantRangeReadout;
        rangePresenter=presentation.createRangeReadout(body,rangeOutput);
        const reset=doc.createElement('button');reset.type='button';reset.dataset.quantResetView='';reset.textContent='전체 기간';reset.hidden=true;
        reset.onclick=()=>{renderer.resetZoom();body.focus();};controls.append(reset);
        body.after(controls);
        const rangeClear=doc.createElement('button');rangeClear.type='button';rangeClear.textContent='구간 해제';rangeClear.hidden=true;controls.append(rangeClear);rangeClear.onclick=()=>{renderer.setRange(null,null);body.focus();};
        const format=v=>v==null?'미제공':new Intl.NumberFormat('ko-KR',{maximumFractionDigits:2}).format(v);
        paintRange=value=>{
          readout.hidden=!!value;
          if(!value){rangePresenter.clear();return;}
          const active=renderer?.getState().legend;
          const items=rangeValues(spec,value,active).map(row=>{
            const i=spec.series?.findIndex(s=>s.name===row.name)??-1;
            const color=i<0?undefined:spec.series[i].color||resolvedTokens.palette[i%resolvedTokens.palette.length];
            return {name:row.name,change:row.change===null?(row.difference===null?'—':'Δ '+presentation.signedChange(row.difference,spec.unit||'')):presentation.signedChange(row.change,row.unit),
              detail:format(row.start)+' → '+format(row.end)+(row.change===null&&row.difference!==null?' · 상대 변화율 미제공':''),color};
          });
          rangePresenter.show({start:value.start,end:value.end,items,dense:spec.kind==='small-multiples'},renderer?.rangeGeometry());
        };
        syncChart=()=>{if(!renderer)return;const state=renderer.getState();reset.hidden=!(state.zoom&&(state.zoom.start>.01||state.zoom.end<99.99));rangeClear.hidden=!state.range;paintRange(state.range);};syncChart();
        const details = doc.createElement('details'); details.className = 'qe-data';
        const summary = doc.createElement('summary'); summary.textContent = '데이터 표 · 원자료';
        const pre = doc.createElement('pre'); pre.textContent = JSON.stringify(spec, null, 2);
        const raw = doc.createElement('div'); raw.className = 'qe-raw-table'; fillDataTable(raw, spec, doc);
        const source=doc.createElement('details');source.className='qe-spec-source';const sourceTitle=doc.createElement('summary');sourceTitle.textContent='구현용 JSON 보기';source.append(sourceTitle,pre);details.append(summary,raw,source); frame.append(details);
      }
      paint(); handles.add(entry);
    } catch (error) {
      // A chart can throw after init but before returning its renderer handle.
      try { if (renderer) renderer.destroy(); else echarts?.getInstanceByDom?.(body)?.dispose(); }
      finally { dead = true; frame.remove(); }
      throw error;
    }
    return {
      update(next) {
        ensureAlive(); if (dead) throw new Error('destroy된 mount입니다.');
        const candidate = structuredClone(next); validateSpec(candidate);
        if (candidate.kind !== spec.kind) throw new TypeError('kind 변경은 새 mount를 사용하세요.');
        renderer.update(candidate); spec = candidate; paint();syncChart();
        const pre = frame.querySelector('pre'); if (pre) pre.textContent = JSON.stringify(spec, null, 2);
        const raw = frame.querySelector('.qe-raw-table'); if (raw) fillDataTable(raw, spec, doc);
      },
      getState: () => renderer.getState(), destroy, renderer, element: frame
    };
  }
  return {
    mount, setTheme, getTheme: () => currentTheme,
    configure(next){ensureAlive();const checked=validateDesign({...currentDesign,...next});currentDesign=checked;setTheme(currentTheme);return {...currentDesign};},
    getDesign:()=>({...currentDesign}),
    destroy() {
      if (disposed) return;
      disposed = true;
      for (const handle of [...handles]) handle.destroy();
      // Only mounted frames are owned; caller content and host elements remain.
    }
  };
}

function fillDataTable(host,spec,doc){
 let headers,rows;
 if(spec.kind==='fan'){headers=['시점','관측','중앙값',...spec.intervals.flatMap(b=>[`${b.level*100}% 하한`,`${b.level*100}% 상한`])];rows=spec.x.map((x,i)=>[x,spec.observed[i],spec.center[i],...spec.intervals.flatMap(b=>[b.low[i],b.high[i]])]);}
 else if(spec.kind==='treemap'){headers=['경로','값'];rows=[];const walk=(nodes,path)=>nodes.forEach(n=>{const name=[...path,n.name];if(n.children)walk(n.children,name);else rows.push([name.join(' / '),n.value]);});walk(spec.nodes,[]);}
 else if(spec.series&&spec.x){headers=['시점',...spec.series.map(s=>s.name)];rows=spec.x.map((x,i)=>[x,...spec.series.map(s=>s.data[i])]);}
 else if(spec.rows){headers=Object.keys(spec.rows[0]||{});rows=spec.rows.map(r=>headers.map(k=>r[k]));}
 else if(spec.bins){headers=['하한','상한','건수'];rows=spec.bins.map(b=>[b.start,b.end,b.count]);}
 else if(spec.points){headers=['대상','x','y','그룹'];rows=spec.points.map(p=>[p.name,p.x,p.y,p.group]);}
 else if(spec.kind==='heatmap'){headers=['x','y','값'];rows=spec.values.map(([x,y,v])=>[spec.x[x],spec.y[y],v]);}
 else {headers=['날짜','값'];rows=spec.values||[];}
 const table=doc.createElement('table'),head=doc.createElement('thead'),hr=doc.createElement('tr'),body=doc.createElement('tbody');
 headers.forEach(h=>{const th=doc.createElement('th');th.scope='col';th.textContent=h;hr.append(th);});head.append(hr);
 rows.forEach(r=>{const tr=doc.createElement('tr');r.forEach((v,i)=>{const cell=doc.createElement(i===0?'th':'td');if(i===0)cell.scope='row';cell.textContent=v==null?'미제공':Array.isArray(v)?v.map(x=>x??'미제공').join(' / '):String(v);tr.append(cell);});body.append(tr);});table.append(head,body);host.replaceChildren(table);
}
export {rebaseComparison} from './compare.js?v=043';
export {contrastRatio} from './tokens.js?v=043';
