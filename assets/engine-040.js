document.documentElement.dataset.designEngine="0.4.4";
/* v0.4.4 interaction audit: retain native sorting and range handlers. */
(() => {
  const enhance = () => {
    document.querySelectorAll('.qr-readout').forEach(readout => { readout.hidden = /^표시 순서대로 구간 선택/.test(readout.textContent); });
    document.querySelectorAll('table').forEach(table => {
      table.setAttribute('data-quant-table', '');
      if (table.dataset.qeSearch) return;
      table.dataset.qeSearch = 'true';
      if(table.caption) table.caption.textContent=table.caption.textContent.replace(/ · 비중 내림차순$/, '');
      const bar = document.createElement('div'); bar.className = 'qe-table-tools';
      const input = document.createElement('input'); input.type = 'search'; input.placeholder = '표 검색';
      input.setAttribute('aria-label', (table.caption?.textContent || '표') + ' 검색');
      const count = document.createElement('output'); count.setAttribute('aria-live','polite');
      const reset = document.createElement('button'); reset.type = 'button'; reset.textContent = '초기화'; reset.hidden = true;
      const more = document.createElement('details'); const summary = document.createElement('summary'); summary.textContent = '표 도구';
      const csv = document.createElement('button'); csv.type = 'button'; csv.textContent = 'CSV 저장'; more.append(summary,csv);
      bar.append(input,reset,count,more); table.parentElement.before(bar);
      const filter = () => {
        const query = input.value.trim().toLocaleLowerCase(); const rows = Array.from(table.tBodies[0]?.rows || []);
        rows.forEach(row => {row.hidden = !!query && !row.textContent.toLocaleLowerCase().includes(query);});
        const label = rows.filter(row=>!row.hidden).length + ' / ' + rows.length;
        if(count.textContent!==label) count.textContent=label;
        reset.hidden=!query;
      };
      input.addEventListener('input',filter);
      reset.addEventListener('click',()=>{input.value='';filter();input.focus();});
      csv.addEventListener('click',()=>{
        const rows=[...Array.from(table.tHead?.rows||[]),...Array.from(table.tBodies[0]?.rows||[]).filter(row=>!row.hidden)];
        const data=rows.map(row=>Array.from(row.cells).map(cell=>'"'+cell.textContent.trim().replace(/[↕↑↓]/g,'').replace(/"/g,'""')+'"').join(',')).join('\r\n');
        const url=URL.createObjectURL(new Blob(['\ufeff'+data],{type:'text/csv;charset=utf-8'}));
        const link=document.createElement('a');link.href=url;link.download='table.csv';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
      });
      if(table.tBodies[0])new MutationObserver(filter).observe(table.tBodies[0],{childList:true});
      filter();
    });
  };
  const start=()=>{enhance();new MutationObserver(enhance).observe(document.body,{childList:true,subtree:true});};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
