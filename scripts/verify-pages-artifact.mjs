import {readFileSync,readdirSync} from 'node:fs';
import {join,relative} from 'node:path';
import assert from 'node:assert/strict';
const root=process.argv[2]||'dist';
const walk=p=>readdirSync(p,{withFileTypes:true}).flatMap(e=>e.isDirectory()?walk(join(p,e.name)):[relative(root,join(p,e.name))]);
const expected=JSON.parse(readFileSync(new URL('./pages-artifact-files.json',import.meta.url),'utf8'));
assert.deepEqual(walk(root).sort(),expected.sort());
console.log(`Verified ${expected.length} allowlisted public assets.`);
