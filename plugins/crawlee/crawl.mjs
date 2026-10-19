import {CheerioCrawler,Configuration,GotScrapingHttpClient,log} from 'crawlee';
import {limitedStream} from './limited-stream.mjs';
import robotsParser from 'robots-parser';
import https from 'node:https';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {join} from 'node:path';
import {createHash} from 'node:crypto';
import {checkedURL,publicLookup,USER_AGENT} from './policy.mjs';
const directory=process.argv[2],request=JSON.parse(await readFile(join(directory,'request.json'),'utf8'));
const hash=data=>createHash('sha256').update(data).digest('hex');
const records=[],robots=new Map();let id=0;
log.setLevel(log.LEVELS.ERROR);
function robotRules(url){
 const u=new URL('/robots.txt',url);
 return new Promise((resolve,reject)=>{
  const req=https.get(u,{lookup:publicLookup,headers:{'user-agent':USER_AGENT},timeout:15000},res=>{
   if(res.statusCode===404||res.statusCode===410){res.resume();return resolve({text:'',status:res.statusCode,url:u.href})}
   if(res.statusCode!==200){res.resume();return reject(Error('Robots policy unavailable: HTTP '+res.statusCode))}
   const chunks=[];let size=0;
   res.on('data',chunk=>{size+=chunk.length;if(size>250000){res.destroy();reject(Error('Robots policy exceeds limit'))}else chunks.push(chunk)});
   res.on('error',reject);res.on('end',()=>resolve({text:Buffer.concat(chunks).toString('utf8'),status:200,url:u.href}));
  });req.on('timeout',()=>req.destroy(Error('Robots policy timeout')));req.on('error',reject);
 });
}
async function allowed(url){
 const u=checkedURL(url,request.allowed_domains);
 if(!robots.has(u.origin))robots.set(u.origin,robotRules(u));
 const rules=await robots.get(u.origin),parser=robotsParser(rules.url,rules.text);
 if(parser.isAllowed(u.href,USER_AGENT)===false)throw Error('Disallowed by robots policy');
 // A delay larger than this run's allowance is refused, not ignored.
 const delay=parser.getCrawlDelay(USER_AGENT);
 if(delay&&delay>2)throw Error('Robots crawl-delay exceeds configured two-second policy; narrower configuration required');
 return rules;
}
await mkdir(join(directory,'evidence'),{recursive:true});
const configuration=new Configuration({storageDir:join(directory,'crawl-storage'),persistStorage:true,purgeOnStart:false});
class BoundedHttpClient extends GotScrapingHttpClient {
 async stream(...args){const result=await super.stream(...args);result.stream=limitedStream(result.stream,request.limits.page_bytes);return result;}
}
const crawler=new CheerioCrawler({
 httpClient:new BoundedHttpClient(),
 maxConcurrency:1,maxRequestsPerCrawl:request.max_pages,maxCrawlDepth:request.max_depth,maxRequestRetries:1,
 useSessionPool:false,sameDomainDelaySecs:2,maxRequestsPerMinute:20,
 requestHandlerTimeoutSecs:20,navigationTimeoutSecs:15,
 preNavigationHooks:[async({request:r},options)=>{
  await allowed(r.url);options.dnsLookup=publicLookup;options.dnsCache=false;options.followRedirect=false;
  options.headers={...options.headers,'user-agent':USER_AGENT};
 }],
 async requestHandler({request:r,response,body,$,enqueueLinks}){
  if(response.statusCode>=300)throw Error('Non-success HTTP '+response.statusCode+'; redirects are not followed');
  const retained=Buffer.isBuffer(body)?body:Buffer.from(body,'utf8');
  if(retained.length>request.limits.page_bytes)throw Error('Page exceeds retained-body limit');
  const title=$('title').text().trim();$('script,style,noscript,nav,footer,header').remove();
  const chosen=$('main').length?$('main'):$('article').length?$('article'):$('body');
  const text=chosen.text().replace(/[ \t]+/g,' ').replace(/\n\s*\n/g,'\n\n').trim();
  if(text.length<80)throw Error('Insufficient readable HTML content; rendering or another parser may be required');
  const sourceId='S'+String(++id).padStart(3,'0');
  await writeFile(join(directory,'evidence',sourceId+'.html'),retained);
  await writeFile(join(directory,'evidence',sourceId+'.txt'),text);
  const policy=await allowed(r.url);
  records.push({id:sourceId,url:r.url,final_url:r.loadedUrl??r.url,title,retrieved_at:new Date().toISOString(),state:'available',http_status:response.statusCode,content_type:response.headers['content-type'],body_sha256:hash(retained),text_sha256:hash(text),characters:text.length,extraction:'Crawlee Cheerio HTML text; retained body may be decoded/decompressed, not raw wire bytes',robots:{url:policy.url,status:policy.status,sha256:hash(policy.text)},limitations:['Public static HTML collection; not factual verification, browser rendering or complete site coverage.']});
  await writeFile(join(directory,'sources.json'),JSON.stringify(records,null,2));
  await enqueueLinks({limit:100,transformRequestFunction:options=>{try{options.url=checkedURL(options.url,request.allowed_domains).href;return options}catch{return false}}});
 },
 async failedRequestHandler({request:r},error){records.push({url:r.url,state:'unavailable',reason:String(error.message).slice(0,500),attempts:r.retryCount+1});await writeFile(join(directory,'sources.json'),JSON.stringify(records,null,2));},
},configuration);
try{await crawler.run(request.urls);await writeFile(join(directory,'sources.json'),JSON.stringify(records,null,2));}
finally{await configuration.getStorageClient().teardown?.();}
