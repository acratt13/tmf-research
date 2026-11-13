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
const nodes=new Map(),timers=new Map();let next=0,published=false;
const rid='a'.repeat(32),get=id=>{if(!nodes.has(id))nodes.set(id,new Node());return nodes.get(id)};
const settings={token:'fixture-only',missions:{schema:'tmf-research-mission/1',types:{}},council_specialists:{},default_council:[],lenses:{},formats:[],inspections:[]};
const result=()=>({report:{title:'Saved research',summary:'Reviewed evidence',sources:[],findings:[],requirements:[],unknowns:[]},analysis:{sections:[],coverage:{criteria:[]}},canon:published?{status:'published-candidate',mission:{id:'cn-fixture',revision:1}}:{status:'not-published'}});
const context=vm.createContext({document:{getElementById:get,createElement:tag=>new Node(tag),createTextNode:text=>({text}),body:{classList:{add(){}}}},localStorage:{getItem(){return null},setItem(){}},location:{search:'?run='+rid},URLSearchParams,URL,console,
 setTimeout(fn){const id=++next;timers.set(id,fn);return id},clearTimeout(id){timers.delete(id)},
 fetch:async path=>({ok:true,json:async()=>path==='/api/config'?settings:path==='/api/runs'?[]:path==='/api/runs/'+rid?{status:'partial',stage:'done',question:'Question',lenses:[],outputs:[],errors:[],events:[]}:result()})});
vm.runInContext(fs.readFileSync('tmf_research/web/app.js','utf8'),context);
const settle=async()=>{for(let i=0;i<12;i++)await new Promise(setImmediate)};
(async()=>{await settle();assert.equal(get('canon-status').textContent,'Canon: not-published');const article=get('result').childNodes[0];assert.ok(article);assert.ok(timers.size,'finished missions must keep observing actor-side publication');published=true;const [id,fn]=timers.entries().next().value;timers.delete(id);await fn();await settle();assert.match(get('canon-status').textContent,/published-candidate.*revision 1/);assert.equal(get('result').childNodes[0],article,'Canon refresh must preserve expanded report DOM');assert.ok(timers.size);})().catch(e=>{console.error(e);process.exitCode=1});
'''
        result=subprocess.run(['node','-e',program],text=True,capture_output=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
