import assert from 'node:assert/strict';
import {readFileSync,readdirSync,mkdirSync,mkdtempSync,copyFileSync,existsSync,renameSync,rmSync,lstatSync} from 'node:fs';
import {dirname,join,resolve,relative} from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
const source=fileURLToPath(new URL('../',import.meta.url));
const destination=resolve(process.argv[2]||join(source,'dist'));
assert(!source.startsWith(destination+'/')&&destination!==resolve(source),'Output must not contain the source checkout');
const files=JSON.parse(readFileSync(new URL('./pages-artifact-files.json',import.meta.url),'utf8'));
const walk=(root,base=root)=>readdirSync(root,{withFileTypes:true}).flatMap(e=>{
 const path=join(root,e.name);assert(!e.isSymbolicLink(),'Unexpected artifact symlink');
 return e.isDirectory()?walk(path,base):[relative(base,path)];
});
if(existsSync(destination)){
 assert(!lstatSync(destination).isSymbolicLink(),'Output must not be a symlink');
 assert.deepEqual(walk(destination).sort(),[...files].sort(),'Refuse to replace an output containing unexpected files');
}
mkdirSync(dirname(destination),{recursive:true});
const stage=mkdtempSync(join(dirname(destination),'.quant-pages-'));
try {
 for(const name of files){const out=join(stage,name);mkdirSync(dirname(out),{recursive:true});copyFileSync(join(source,name),out)}
 execFileSync(process.execPath,[fileURLToPath(new URL('./verify-pages-artifact.mjs',import.meta.url)),stage],{stdio:'inherit'});
 if(existsSync(destination))rmSync(destination,{recursive:true});
 renameSync(stage,destination);
 console.log(`Built current public artifact: ${destination}`);
}finally{if(existsSync(stage))rmSync(stage,{recursive:true})}
