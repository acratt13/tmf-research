#!/usr/bin/env node
// Optional local browser collector. Does not change the deployed text worker or MC catalog.
import {PlaywrightCrawler,Configuration,log} from 'crawlee';
import {chromium} from 'playwright-core';
import {readFile,writeFile,mkdir,open,unlink,rename} from 'node:fs/promises';
import {resolve,join} from 'node:path';
import {randomUUID} from 'node:crypto';
import {createPolicy,publicResponse} from './visual-network.mjs';
import {validateManifest,sha256,designMarkdown,galleryHTML} from './visual-report.mjs';

const [manifestPath,outputPath,batchArg='5']=process.argv.slice(2);
if(!manifestPath||!outputPath)throw Error('Usage: node visual.mjs MANIFEST OUTPUT [BATCH_SIZE] (CHROME_PATH required)');
if(!process.env.CHROME_PATH)throw Error('Set CHROME_PATH to an installed Chromium executable');
const batch=Number(batchArg);
if(!Number.isInteger(batch)||batch<1||batch>20)throw Error('Batch size must be 1–20');
const manifest=validateManifest(JSON.parse(await readFile(manifestPath,'utf8'))),out=resolve(outputPath);
await mkdir(out,{recursive:true});
const lock=await open(join(out,'.collector.lock'),'wx').catch(()=>{throw Error('Collection locked; inspect existing collector before removing a stale lock')});
await lock.writeFile(JSON.stringify({pid:process.pid,started_at:new Date().toISOString()}));
// A batch owns its Crawlee counters. Collection.json owns cross-batch progress.
// Reusing one queue would make maxRequestsPerCrawl count earlier completed requests.
const config=new Configuration({storageClientOptions:{localDataDirectory:join(out,'crawl-storage',randomUUID())},purgeOnStart:false,persistStorage:true});
let crawler,records=[];
const checkpoint=async()=>{
 for(const [name,data] of [['collection.json',JSON.stringify({schema:'tmf-design-collection/v1',updated_at:new Date().toISOString(),target_count:manifest.target_count,records},null,2)],['index.html',galleryHTML(records)]]){
  await writeFile(join(out,name+'.tmp'),data);await rename(join(out,name+'.tmp'),join(out,name));
 }
};

// Runs inside the page. Record observations only: semantic labels remain review work.
function measure(selector) {
 const root=document.querySelector(selector);if(!root)throw Error('Component selector missing: '+selector);
 const candidates=[root,...root.querySelectorAll('*')].filter(el=>!['SCRIPT','STYLE','LINK','META'].includes(el.tagName));
 const components=[],colors=new Map();
 for(const el of candidates.slice(0,500)) {
  const b=el.getBoundingClientRect(),s=getComputedStyle(el);if(b.width<1||b.height<1||s.visibility==='hidden'||s.display==='none')continue;
  const styles={};for(const key of ['display','position','backgroundColor','color','borderColor','borderRadius','borderWidth','boxShadow','fontFamily','fontSize','fontWeight','lineHeight','letterSpacing','padding','gap','gridTemplateColumns','alignItems','justifyContent','transform','opacity','transitionDuration','transitionTimingFunction','animationName'])styles[key]=s[key];
  for(const key of ['backgroundColor','color','borderColor','fill','stroke']){const value=s[key];if(!value||['none','rgba(0, 0, 0, 0)','transparent'].includes(value))continue;const c=colors.get(value)||{value,count:0,properties:[]};c.count++;if(!c.properties.includes(key))c.properties.push(key);colors.set(value,c);}
  if(components.length<60)components.push({id:'C'+String(components.length+1).padStart(3,'0'),tag:el.tagName.toLowerCase(),role:el.getAttribute('role'),text:(el.childElementCount===0?el.textContent:'').trim().slice(0,160),bounds:{x:Math.round(b.x),y:Math.round(b.y+scrollY),width:Math.round(b.width),height:Math.round(b.height)},styles,attributes:{ariaLabel:el.getAttribute('aria-label'),expanded:el.getAttribute('aria-expanded'),tabindex:el.getAttribute('tabindex'),type:el.getAttribute('type')}});
 }
 const animations=document.getAnimations().filter(a=>root.contains(a.effect?.target)).slice(0,30).map(a=>({target:a.effect?.target?.tagName,timing:a.effect?.getTiming(),keyframes:a.effect?.getKeyframes().slice(0,10),playState:a.playState}));
 return {viewport:{width:innerWidth,height:innerHeight},components,palette:[...colors.values()].sort((a,b)=>b.count-a.count).slice(0,16),animations};
}

try {
 try{records=JSON.parse(await readFile(join(out,'collection.json'),'utf8')).records;}catch(e){if(e.code!=='ENOENT')throw e;}
 const successful=records.filter(r=>r.state==='captured').length,attempted=new Set(records.map(r=>r.id));
 const targets=manifest.targets.filter(t=>!attempted.has(t.id)).slice(0,Math.max(0,Math.min(batch,manifest.target_count-successful)));
 if(!targets.length){console.log(JSON.stringify({state:'no_pending_targets',captured:successful,target:manifest.target_count}));}
 else {
 log.setLevel(log.LEVELS.ERROR);
 crawler=new PlaywrightCrawler({
  launchContext:{launcher:chromium,launchOptions:{executablePath:process.env.CHROME_PATH,headless:true}},
  browserPoolOptions:{useFingerprints:false,maxOpenPagesPerBrowser:1,prePageCreateHooks:[async(_id,_controller,options)=>{if(options){options.serviceWorkers='block';options.acceptDownloads=false;}}]},
  maxConcurrency:1,maxRequestsPerCrawl:targets.length,maxRequestRetries:0,useSessionPool:false,
  sameDomainDelaySecs:3,maxRequestsPerMinute:12,navigationTimeoutSecs:35,requestHandlerTimeoutSecs:90,
  preNavigationHooks:[async({page,request},options)=>{
   const t=request.userData.target,allowed=createPolicy(t.allowed_domains),blocked=[];let requests=0,bytes=0;
   request.userData.robots=await allowed(t.url);
   request.userData.blocked=blocked;
   await page.routeWebSocket('**/*',socket=>socket.close());
   await page.setViewportSize({width:1440,height:900});
   await page.context().setExtraHTTPHeaders({'user-agent':'TMFCrawlee/0.1 (+https://github.com/acratt13/tmf-research)'});
   await page.route('**/*',async route=>{
    const r=route.request(),url=r.url();
    try{
     if(r.method()!=='GET'||++requests>160)throw Error('Method/request budget refused');
     await allowed(url);
     const response=await publicResponse(url,t.allowed_domains);
     if(response.status>=300&&response.status<400)throw Error('Redirect refused');
     bytes+=response.body.length;if(bytes>25000000)throw Error('Page transfer budget exceeded');
     const headers={};for(const [k,v]of Object.entries(response.headers))if(v!=null&&!['transfer-encoding','connection','content-length','set-cookie','content-encoding'].includes(k))headers[k]=Array.isArray(v)?v.join(', '):String(v);
     await route.fulfill({status:response.status,headers,body:response.body});
    }catch(e){if(blocked.length<40)blocked.push({url,reason:e.message});await route.abort().catch(()=>{});}
   });
   options.waitUntil='domcontentloaded';
  }],
  async requestHandler({page,request,response}){
   const t=request.userData.target,dir=join(out,t.id);await mkdir(dir,{recursive:true});
   if(!response||response.status()!==200)throw Error('Non-success navigation');
   const errors=[];page.on('pageerror',e=>{if(errors.length<10)errors.push(e.message.slice(0,300))});
   await page.waitForSelector(t.selector,{state:'visible',timeout:15000});
   // Require actual rendered content: an empty demo shell is not a captured reference.
   await page.waitForFunction(s=>{const r=document.querySelector(s);return r&&r.children.length>0},t.selector,{timeout:15000});
   await page.waitForTimeout(700);
   const desktop=await page.evaluate(measure,t.selector);
   if(desktop.components.length<2)throw Error('Insufficient rendered component anatomy');
   const files=[];
   async function screenshot(name){const path=join(dir,name);await page.screenshot({path,type:'jpeg',quality:82,fullPage:false,timeout:15000});files.push(name);}
   await screenshot('desktop.jpg');
   const start=Date.now();await page.waitForTimeout(350);await screenshot('frame-1.jpg');
   await page.waitForTimeout(650);await screenshot('frame-2.jpg');
   const motion={desktop:{animations:desktop.animations,sample_elapsed_ms:Date.now()-start,trigger:'Passive mount; no click or drag performed'},hover:null};
   if(t.hover_selector){const target=page.locator(t.hover_selector).first();await target.hover({timeout:3000});await page.waitForTimeout(300);motion.hover=await page.evaluate(measure,t.selector);await screenshot('hover.jpg');await page.mouse.move(0,0);}
   await page.setViewportSize({width:390,height:844});await page.waitForTimeout(250);const mobile=await page.evaluate(measure,t.selector);await screenshot('mobile.jpg');
   await page.emulateMedia({reducedMotion:'reduce'});await page.reload({waitUntil:'domcontentloaded'});await page.waitForSelector(t.selector,{timeout:15000});await page.waitForTimeout(700);const reduced=await page.evaluate(measure,t.selector);await screenshot('reduced-motion.jpg');
   const study={schema:'tmf-design-study/v1',...t,source_text:undefined,state:'captured',review_status:'captured_unreviewed',captured_at:new Date().toISOString(),final_url:page.url(),measurements:{desktop,mobile,reduced},motion,robots:request.userData.robots,blocked_requests:request.userData.blocked,page_errors:errors,license_status:t.license_status||'unverified',limitations:['Passive frames are not full interaction or timing tests.','No automatic MC ingestion or implementation approval.']};
   await writeFile(join(dir,'source.txt'),t.source_text||'Source not supplied.');files.push('source.txt');
   await writeFile(join(dir,'DESIGN.md'),designMarkdown(study));files.push('DESIGN.md');
   study.evidence=[];for(const name of files){const data=await readFile(join(dir,name));study.evidence.push({path:name,bytes:data.length,sha256:sha256(data)});}
   await writeFile(join(dir,'design.json'),JSON.stringify(study,null,2));
   records.push(study);await checkpoint();console.log(JSON.stringify({id:t.id,state:'captured',elements:desktop.components.length,palette:desktop.palette.length}));
  },
  async failedRequestHandler({request},error){records.push({id:request.userData.target.id,url:request.url,state:'unavailable',reason:error.message.slice(0,800),at:new Date().toISOString()});await checkpoint();},
 },config);
 let stopping=false;
 const stop=async()=>{if(stopping)return;stopping=true;await crawler.stop();};
 process.once('SIGTERM',stop);process.once('SIGINT',stop);
 try{await crawler.run(targets.map(target=>({url:target.url,userData:{target}})));}
 finally{process.removeListener('SIGTERM',stop);process.removeListener('SIGINT',stop);}
 }
 await checkpoint();
 console.log(JSON.stringify({state:'batch_finished',captured:records.filter(r=>r.state==='captured').length,unavailable:records.filter(r=>r.state==='unavailable').length,target:manifest.target_count}));
}finally {
 await crawler?.browserPool?.destroy().catch(()=>{});
 await config.getStorageClient().teardown?.();
 await config.getEventManager().close();
 // Browser-pool utilities can initialize the process-global event manager too.
 await Configuration.getGlobalConfig().getEventManager().close();
 await lock.close();await unlink(join(out,'.collector.lock'));
}
// This is a standalone CLI, not an imported service. All writes and browser cleanup
// are awaited above; exit after flushing output rather than retaining SDK timers.
await new Promise(done=>process.stdout.write('',done));
process.exit(0);
