const test=require('node:test'), assert=require('node:assert/strict'), fs=require('node:fs'), path=require('node:path'), {spawnSync}=require('node:child_process');
const dir=path.resolve(__dirname,'../shared/design/contracts/1.0.0');
const {verifyHtml,CONTRACT}=require(path.join(dir,'verify-design.cjs'));
const base=CONTRACT.startupBase;
const pair=`<link rel="stylesheet" href="${base}factor.css" data-quant-first-paint-css><script src="${base}start.js" data-quant-design-project="factor"></script>`;
const app='<script src="app.js" defer></script>', nav=`<script src="${CONTRACT.navigationUrl}" defer></script>`;
const valid=`<!doctype html><html><head><script src="assets/theme.js"></script><link rel="stylesheet" href="app.css">${pair}${app}${nav}</head><body></body></html>`;
const cases=[['current',valid,true],['old pin',valid.replaceAll('1.2.0','1.1.0'),false],['duplicate startup',valid.replace(pair,pair+pair),false],['missing startup',valid.replace(pair,''),false],['async startup',valid.replace('data-quant-design-project="factor"','async data-quant-design-project="factor"'),false],['late native css',valid.replace(app,'<link rel="stylesheet" href="late.css">'+app),false],['early app',valid.replace(pair+app,app+pair),false],['duplicate navigation',valid.replace(nav,nav+nav),false],['app after nav',valid.replace(app+nav,nav+app),false],['direct engine',valid.replace(app,app+'<script defer src="quant-range.js"></script>'),true],['direct absolute engine',valid.replace(app,app+'<script defer src="/quant-range.js"></script>'),false],['head blocking app',valid.replace('src="app.js" defer','src="app.js"'),false],['wrong project',valid.replace('data-quant-design-project="factor"','data-quant-design-project="regime"'),false]];
// Relative standalone engine filenames must be rejected as well.
cases.find(c=>c[0]==='direct engine')[2]=false;
cases.push(['commented old loader',valid.replace('</head>','<!-- <script src="/shared/design/startup/1.0.0/start.js"></script> --></head>'),true]);
const react=valid.replace(nav,'').replace(pair, '<script type="module" async src="/_assets/framework-abc123.js"></script>'+pair);
cases.push(['framework before startup',react,true,'react'],['app module before startup',react.replace('framework-abc123.js','index-abc123.js'),false,'react']);
test('identical artifact contract in Node and Python, including rollback and startup races',()=>{
 const inputs=cases.map(([name,html,expected,navigation='static'])=>({name,html,expected,navigation}));
 const child=spawnSync('python3',['-B','-c',`import sys,json\nsys.path.insert(0,${JSON.stringify(dir)})\nfrom verify_design import verify_html\nrows=[]\nfor x in json.load(sys.stdin):\n try: verify_html(x['html'],'factor',x['navigation']); rows.append(True)\n except ValueError: rows.append(False)\nprint(json.dumps(rows))`],{input:JSON.stringify(inputs),encoding:'utf8'});
 assert.equal(child.status,0,child.stderr); const python=JSON.parse(child.stdout);
 for(const [i,c] of inputs.entries()){let accepted=true;try{verifyHtml(c.html,{project:'factor',navigation:c.navigation})}catch{accepted=false}assert.equal(accepted,c.expected,c.name);assert.equal(python[i],accepted,'Python parity: '+c.name)}
});

test('Hub refuses stale artifact bytes even when filenames and startup pin remain valid',()=>{
 const os=require('node:os'), root=path.resolve(__dirname,'..'), temp=fs.mkdtempSync(path.join(os.tmpdir(),'quant-artifact-'));
 try {
  const files=JSON.parse(fs.readFileSync(path.join(__dirname,'pages-artifact-files.json'),'utf8'));
  for(const name of files){const dest=path.join(temp,name);fs.mkdirSync(path.dirname(dest),{recursive:true});fs.copyFileSync(path.join(root,name),dest)}
  let result=spawnSync(process.execPath,[path.join(__dirname,'verify-pages-artifact.mjs'),temp],{encoding:'utf8'});assert.equal(result.status,0,result.stderr);
  const retired=path.join(temp,'shared/design/startup/1.1.0/start.js');fs.mkdirSync(path.dirname(retired),{recursive:true});fs.writeFileSync(retired,'/* retired */');
  result=spawnSync(process.execPath,[path.join(__dirname,'verify-pages-artifact.mjs'),temp],{encoding:'utf8'});assert.notEqual(result.status,0);
  fs.rmSync(path.dirname(retired),{recursive:true});
  fs.appendFileSync(path.join(temp,'shared/design/startup/1.2.0/start.js'),'\n/* stale generated output */');
  result=spawnSync(process.execPath,[path.join(__dirname,'verify-pages-artifact.mjs'),temp],{encoding:'utf8'});assert.notEqual(result.status,0);assert.match(result.stderr,/Artifact bytes differ from validated source/);
 }finally{fs.rmSync(temp,{recursive:true,force:true})}
});

test('all published stylesheet dependencies exist in the minimal artifact',()=>{
 const files=JSON.parse(fs.readFileSync(path.join(__dirname,'pages-artifact-files.json'),'utf8'));
 for(const name of files.filter(n=>n.endsWith('.css'))){
  const css=fs.readFileSync(path.join(__dirname,'..',name),'utf8');
  for(const match of css.matchAll(/url\(['"]?([^)'"\s]+)['"]?\)/g)){
   if(/^(?:data:|https?:|#)/.test(match[1]))continue;
   const dependency=path.posix.normalize(path.posix.join(path.posix.dirname(name),match[1]));
   assert(files.includes(dependency),`${name} requires unpublished ${dependency}`);
  }
 }
});
