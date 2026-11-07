import {createRequire} from 'node:module';
const {verifyHtml}=createRequire(import.meta.url)('../shared/design/contracts/1.0.0/verify-design.cjs');
import {readFileSync,readdirSync} from 'node:fs';
import {join,relative} from 'node:path';
import assert from 'node:assert/strict';
const root=process.argv[2]||'dist';
const walk=p=>readdirSync(p,{withFileTypes:true}).flatMap(e=>e.isDirectory()?walk(join(p,e.name)):[relative(root,join(p,e.name))]);
const expected=JSON.parse(readFileSync(new URL('./pages-artifact-files.json',import.meta.url),'utf8'));
assert.deepEqual(walk(root).sort(),expected.sort());
console.log(`Verified ${expected.length} allowlisted public assets.`);

verifyHtml(readFileSync(join(root,'index.html'),'utf8'),{project:'quant-dashboard'});
for (const name of expected) {
  assert(readFileSync(join(root,name)).equals(readFileSync(new URL('../'+name,import.meta.url))),
    `Artifact bytes differ from validated source: ${name}`);
}
