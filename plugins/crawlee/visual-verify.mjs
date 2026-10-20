#!/usr/bin/env node
import {readFile,writeFile} from 'node:fs/promises';
import {resolve,join,basename} from 'node:path';
import {sha256} from './visual-report.mjs';
const directory=resolve(process.argv[2]||'.');
const collection=JSON.parse(await readFile(join(directory,'collection.json'),'utf8'));
let artifacts=0,images=0;const ids=new Set();
for(const record of collection.records){
 if(!/^[a-z0-9][a-z0-9-]{0,99}$/.test(record.id)||ids.has(record.id))throw Error('Invalid or duplicate study id');
 ids.add(record.id);if(record.state!=='captured')continue;
 const dir=join(directory,record.id),saved=JSON.parse(await readFile(join(dir,'design.json'),'utf8'));
 if(saved.id!==record.id||saved.url!==record.url)throw Error('Study provenance mismatch');
 if(saved.measurements.desktop.components.length<2)throw Error('Empty anatomy');
 if(!saved.evidence.some(e=>e.path==='source.txt')||!saved.evidence.some(e=>e.path==='DESIGN.md'))throw Error('Missing source/handoff evidence');
 for(const evidence of saved.evidence){
  if(evidence.path!==basename(evidence.path))throw Error('Invalid artifact path');
  const data=await readFile(join(dir,evidence.path));
  if(data.length!==evidence.bytes||sha256(data)!==evidence.sha256)throw Error('Evidence mismatch: '+record.id+'/'+evidence.path);
  artifacts++;
  if(evidence.path.endsWith('.jpg')){if(data[0]!==255||data[1]!==216||data.at(-2)!==255||data.at(-1)!==217)throw Error('Invalid JPEG: '+evidence.path);images++;}
 }
}
const receipt={schema:'tmf-design-verification/v1',verified_at:new Date().toISOString(),captured:collection.records.filter(r=>r.state==='captured').length,unavailable:collection.records.filter(r=>r.state==='unavailable').length,artifacts,images,proof:'Saved artifact hashes and JPEG signatures checked; not visual, interaction or design approval.'};
await writeFile(join(directory,'verification.json'),JSON.stringify(receipt,null,2));console.log(JSON.stringify(receipt));
