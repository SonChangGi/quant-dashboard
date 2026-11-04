import assert from 'node:assert/strict';
import {readFileSync, readdirSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {join, relative} from 'node:path';
const root=new URL('../shared/design/releases/0.5.0/',import.meta.url);
const manifest=JSON.parse(readFileSync(new URL('manifest.json',root),'utf8'));
assert.equal(manifest.version,'0.5.0');assert.equal(manifest.foundation,'0.4.0');
const walk=p=>readdirSync(p,{withFileTypes:true}).flatMap(e=>e.isDirectory()?walk(join(p,e.name)):[join(p,e.name)]);
const files=walk(root.pathname).map(p=>relative(root.pathname,p)).filter(p=>p!=='manifest.json').sort();
assert.deepEqual(files,Object.keys(manifest.files).sort());
for(const name of files){
 const bytes=readFileSync(new URL(name,root));assert.equal(createHash('sha256').update(bytes).digest('hex'),manifest.files[name],name);
 if(name.startsWith('foundation/'))assert.deepEqual(bytes,readFileSync(new URL('../shared/design/v3/'+name.slice(11),import.meta.url)),name+' foundation drift');
 if(/\.(css|js)$/.test(name))assert(!/QuantPreview|127\.0\.0\.1|localhost|design=baseline|quant-preview-/.test(bytes.toString()),name+' preview contamination');
}
console.log(`Verified immutable release ${manifest.version}: ${files.length} asset hashes and unchanged foundation.`);
