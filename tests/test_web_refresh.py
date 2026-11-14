import shutil
import subprocess
import unittest

@unittest.skipUnless(shutil.which('node'),'Node is required for the existing browser script')
class WebRefreshTests(unittest.TestCase):
    def test_terminal_publication_refresh_keeps_the_open_report(self):
        program=r'''
const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict');
class Node {
 constructor(tag='div'){this.tag=tag;this.childNodes=[];this.value='';this.classList={add(){}};}
 append(...nodes){this.childNodes.push(...nodes)} prepend(...nodes){this.childNodes.unshift(...nodes)}
 replaceChildren(...nodes){this.childNodes=nodes} insertBefore(node,before){const i=this.childNodes.indexOf(before);this.childNodes.splice(i<0?this.childNodes.length:i,0,node)}
 setAttribute(){} addEventListener(){} querySelectorAll(){return []} scrollIntoView(){} focus(){}
}
const nodes=new Map(),timers=new Map();let next=0,published=false;const roleFile='role-plugin-'+'c'.repeat(64)+'.zip';
const rid='a'.repeat(32),get=id=>{if(!nodes.has(id))nodes.set(id,new Node());return nodes.get(id)};
const settings={token:'fixture-only',missions:{schema:'tmf-research-mission/1',types:{}},council_specialists:{},default_council:[],lenses:{},formats:[],inspections:[]};
const result=()=>({report:{title:'Saved research',summary:'Reviewed evidence',sources:[],findings:[],requirements:[],unknowns:[]},analysis:{sections:[],coverage:{criteria:[]}},canon:published?{status:'published-candidate',mission:{id:'cn-fixture',revision:1},role_plugin:{status:'available'}}:{status:'not-published'}});
const context=vm.createContext({document:{getElementById:get,createElement:tag=>new Node(tag),createTextNode:text=>({text}),body:{classList:{add(){}}}},localStorage:{getItem(){return null},setItem(){}},location:{search:'?run='+rid},URLSearchParams,URL,console,
 setTimeout(fn){const id=++next;timers.set(id,fn);return id},clearTimeout(id){timers.delete(id)},
 fetch:async path=>({ok:true,json:async()=>path==='/api/config'?settings:path==='/api/runs'?[]:path==='/api/runs/'+rid?{status:'partial',stage:'done',question:'Question',lenses:[],outputs:published?[roleFile]:[],errors:[],events:[]}:result()})});
vm.runInContext(fs.readFileSync('tmf_research/web/app.js','utf8'),context);
const settle=async()=>{for(let i=0;i<12;i++)await new Promise(setImmediate)};
(async()=>{await settle();assert.equal(get('canon-status').textContent,'Canon: not-published');const article=get('result').childNodes[0];assert.ok(article);assert.ok(timers.size,'finished missions must keep observing actor-side publication');published=true;const [id,fn]=timers.entries().next().value;timers.delete(id);await fn();await settle();assert.match(get('canon-status').textContent,/published-candidate.*revision 1/);assert.match(get('canon-status').textContent,/Role package: available/);assert.equal(get('outputs').childNodes[0].textContent,'Role plugin (.zip)');assert.ok(get('outputs').childNodes[0].href.endsWith(roleFile));assert.equal(get('result').childNodes[0],article,'Canon refresh must preserve expanded report DOM');assert.ok(timers.size);})().catch(e=>{console.error(e);process.exitCode=1});
'''
        result=subprocess.run(['node','-e',program],text=True,capture_output=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_new_selected_and_revised_runs_keep_their_url_across_reload(self):
        program=r'''
const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict');
class Node {
 constructor(tag='div'){this.tag=tag;this.childNodes=[];this.value='';this.classList={add(){}};}
 append(...nodes){this.childNodes.push(...nodes)} prepend(...nodes){this.childNodes.unshift(...nodes)} replaceChildren(...nodes){this.childNodes=nodes}
 insertBefore(node,before){const i=this.childNodes.indexOf(before);this.childNodes.splice(i<0?this.childNodes.length:i,0,node)}
 setAttribute(){} addEventListener(){} querySelectorAll(){return []} scrollIntoView(){} focus(){}
}
const original='a'.repeat(32),child='b'.repeat(32),script=fs.readFileSync('tmf_research/web/app.js','utf8');
const settings={token:'fixture',missions:{schema:'tmf-research-mission/1',types:{}},council_specialists:{},default_council:[],lenses:{},formats:[],inspections:[]};
const settle=async()=>{for(let i=0;i<12;i++)await new Promise(setImmediate)};
(async()=>{for(const action of ['history','refine','start']){
 let where=new URL('http://127.0.0.1/?run='+original+'&keep=1'),saved=null,reads=[];
 const storage={getItem(){return saved},setItem(k,v){saved=v}};
 function boot(){
  const nodes=new Map(),get=id=>{if(!nodes.has(id))nodes.set(id,new Node());return nodes.get(id)};
  const history={replaceState(a,b,url){where=new URL(url,where)}};
  const context=vm.createContext({document:{getElementById:get,createElement:tag=>new Node(tag),createTextNode:text=>({text}),body:{classList:{add(){}}}},localStorage:storage,
   location:{get href(){return where.href},get search(){return where.search}},window:{history},history,URLSearchParams,URL,console,setTimeout(){return 1},clearTimeout(){},
   fetch:async(path,options)=>({ok:true,json:async()=>{
    if(path==='/api/config')return settings;
    if(path==='/api/runs'&&options?.method!=='POST')return [{id:original,question:'Original',status:'partial'},{id:child,question:'Revision',parent_id:original,status:'partial'}];
    if(path==='/api/brief')return {question:'Question',lenses:[],depth:'quick',formats:[],council:false,context:'',privacy:''};
    if(path==='/api/refine'||(path==='/api/runs'&&options?.method==='POST'))return {id:child};
    if(path.startsWith('/api/runs/')){reads.push(path);return {status:'partial',stage:'done',question:'Question',lenses:[],outputs:['builder-pack.json'],errors:[],events:[]}}
    return {report:{title:'Saved',summary:'Evidence',sources:[],findings:[],requirements:[],unknowns:[]},analysis:{sections:[],coverage:{criteria:[]}},canon:{status:'not-published'}};
   }})});vm.runInContext(script,context);return get;
 }
 let get=boot();await settle();
 if(action==='history')get('history').childNodes.find(n=>n.textContent.includes('Revision')).onclick();
 if(action==='refine'){get('refine-feedback').value='Clarify';await get('refine').onclick()}
 if(action==='start'){await get('preview').onclick();await get('start').onclick()}
 await settle();assert.equal(where.searchParams.get('run'),child,action+' must preserve its selected run in the URL');
 assert.equal(where.searchParams.get('keep'),'1');reads=[];boot();await settle();
 assert.ok(reads.includes('/api/runs/'+child),action+' reload must read the selected run');assert.ok(!reads.includes('/api/runs/'+original));
}})().catch(e=>{console.error(e);process.exitCode=1});
'''
        result=subprocess.run(['node','-e',program],text=True,capture_output=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
