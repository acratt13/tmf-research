import https from 'node:https';
import robotsParser from 'robots-parser';
import {checkedURL, publicLookup, USER_AGENT} from './policy.mjs';
import {sha256} from './visual-report.mjs';

// Node supplies the validated DNS address to the socket, including for browser assets.
// Browser routing fulfills from these bounded responses instead of resolving twice.
export function publicResponse(url, domains, cap = 6000000) {
 const u = checkedURL(url, domains);
 return new Promise((resolve,reject) => {
  const req = https.get(u,{lookup:publicLookup,headers:{'user-agent':USER_AGENT,'accept-encoding':'identity'},timeout:20000},res => {
   const chunks=[]; let bytes=0;
   res.on('data',chunk=>{bytes+=chunk.length;if(bytes>cap)res.destroy(Error('Response exceeds byte limit'));else chunks.push(chunk)});
   res.on('error',reject);
   res.on('end',()=>resolve({status:res.statusCode,headers:res.headers,body:Buffer.concat(chunks)}));
  });
  req.on('timeout',()=>req.destroy(Error('Public request timeout')));req.on('error',reject);
 });
}
export function createPolicy(domains) {
 const cache=new Map();
 return async function allowed(url) {
  const u=checkedURL(url,domains),robotURL=new URL('/robots.txt',u).href;
  if(!cache.has(u.origin))cache.set(u.origin,(async()=>{
   const r=await publicResponse(robotURL,domains,250000);
   if(![200,404,410].includes(r.status))throw Error('Robots policy unavailable: '+r.status);
   const text=r.status===200?r.body.toString('utf8'):'';
   return {parser:robotsParser(robotURL,text),receipt:{url:robotURL,status:r.status,sha256:sha256(text)}};
  })());
  const rules=await cache.get(u.origin);
  if(rules.parser.isAllowed(u.href,USER_AGENT)===false)throw Error('Disallowed by robots policy');
  if((rules.parser.getCrawlDelay(USER_AGENT)||0)>3)throw Error('Robots delay exceeds three-second collection policy');
  return rules.receipt;
 };
}
