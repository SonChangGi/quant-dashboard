/* Shared theme preference wins over a page's legacy light/system default. */
(()=>{
 'use strict';
 const root=document.documentElement;
 const valid=value=>value==='light'||value==='dark';
 function apply(){
  let saved;try{saved=localStorage.getItem('quant-research-theme')}catch{}
  const requested=new URLSearchParams(location.search).get('theme');
  const theme=valid(requested)?requested:valid(saved)?saved:'dark';
  root.dataset.theme=theme;
  root.dataset.density=root.dataset.quantDesignProject==='news'?'spacious':'compact';
  root.style.colorScheme=theme;
  try{localStorage.setItem('quant-research-theme',theme);if(root.dataset.quantDesignProject==='news')localStorage.setItem('research-news-theme',theme)}catch{}
  return theme;
 }
 window.QuantDesignTheme=Object.freeze({apply});
 apply();
})();
