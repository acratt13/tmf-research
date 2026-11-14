"""Optional acceptance using MC's real compiled Canon writer in scratch storage."""
import json
import os
from pathlib import Path
import select
import shutil
import subprocess
import tempfile
import unittest
import urllib.request

from tmf_research.canon import publish_candidates
from tmf_research.engine import RunStore


@unittest.skipUnless(os.environ.get('CANON_TEST_DIST') and shutil.which('node'),
                     'set CANON_TEST_DIST to MC backend dist/src for the real Canon contract')
class NativeCanonContractTests(unittest.TestCase):
    def test_real_keyed_section_writer_reuses_ids_and_preserves_revisions(self):
        with tempfile.TemporaryDirectory() as scratch:
            root=Path(scratch)
            script=r'''
import {pathToFileURL} from 'node:url';
import {createServer} from 'node:http';
const mod = p => import(pathToFileURL(process.env.CANON_TEST_DIST+'/'+p).href);
const {CanonDb} = await mod('canon/db/canonDb.js');
const {writeSectionEntry,registerDeclaredSections} = await mod('canon/sections.js');
const {KNOWLEDGE_CANON_SECTION} = await mod('team-knowledge/canonSection.js');
const db = new CanonDb(process.env.CHAT_BACKEND_DATA_DIR);
registerDeclaredSections(db,[{canonSections:[KNOWLEDGE_CANON_SECTION]}]);
db.ensureSection('knowledge','Knowledge',['knowledge']);
const server=createServer(async(req,res)=>{
 let code=200,value;
 if(req.method==='POST' && req.url==='/api/canon/sections/knowledge/entries'){
  let raw='';for await(const chunk of req)raw+=chunk;
  const answer=writeSectionEntry(db,{actor:'synthetic-research-proof',operator:req.headers.authorization==='Bearer fixture-only'},'knowledge',JSON.parse(raw));
  code=answer.status;value=answer.body;
 }else if(req.url.startsWith('/api/canon/organization/entries/')){
  const url=new URL(req.url,'http://fixture');const id=url.pathname.split('/').pop();
  const entry=url.searchParams.has('revision')?db.history(id).find(e=>e.revision===Number(url.searchParams.get('revision'))):db.current(id);
  code=entry?200:404;value={entry,backlinks:db.linksTo(id)};
 }else if(req.url==='/stats'){
  value={rows:Number(db.db.prepare('select count(*) as n from canon_entries').get().n)};
 }else if(req.url.startsWith('/entry/')){
  value=db.current(req.url.slice(7));
 }else{code=404;value={error:'Fixture route unavailable'};}
 res.writeHead(code,{'content-type':'application/json'});res.end(JSON.stringify(value));
});
server.listen(0,'127.0.0.1',()=>console.log('http://127.0.0.1:'+server.address().port));
process.on('SIGTERM',()=>server.close(()=>{db.db.close();process.exit(0)}));
'''
            env={**os.environ,'CHAT_BACKEND_DATA_DIR':str(root/'canon-data'),
                 'HERMES_HOME':str(root/'hermes'), 'BMC_HOME':str(root/'bmc')}
            process=subprocess.Popen(['node','--input-type=module','-e',script],env=env,
                                     stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            try:
                ready,_,_=select.select([process.stdout],[],[],10)
                self.assertTrue(ready,'Native Canon fixture did not start')
                base=process.stdout.readline().strip()
                self.assertTrue(base,process.stderr.read() if process.poll() is not None else 'No fixture URL')
                def read(path):
                    with urllib.request.urlopen(base+path,timeout=3) as response:return json.load(response)
                config={'canon':{'url':base,'identity_scope':'native-synthetic-proof','token_env':'RESEARCH_TEST_TOKEN'}}
                store=RunStore(root/'runs')
                rid=store.create({'question':'What can the synthetic payment fixture establish?'},request_id='native-proof')
                report=json.loads((Path(__file__).resolve().parents[1]/'examples/report.json').read_text())
                store.save(rid,'report.json',report);store.update(rid,status='partial',outputs=['report.md'])
                from unittest.mock import patch
                with patch.dict(os.environ,{'RESEARCH_TEST_TOKEN':'fixture-only'}):
                    first=publish_candidates(store,rid,config)
                    self.assertEqual(first['status'],'published-candidate',first)
                    rows=read('/stats')['rows']
                    self.assertEqual(publish_candidates(store,rid,config),first)
                    self.assertEqual(read('/stats')['rows'],rows)
                    mission=read('/entry/'+first['mission']['id'])
                    self.assertEqual(json.loads(mission['body'])['report'],report)
                    self.assertEqual(mission['fields']['status'],'draft')
                    report['summary']='A revised synthetic candidate summary.'
                    store.save(rid,'report.json',report)
                    second=publish_candidates(store,rid,config)
                    self.assertEqual(second['status'],'published-candidate',second)
                    self.assertEqual(second['mission']['id'],first['mission']['id'])
                    self.assertEqual(second['mission']['revision'],2)
                    self.assertEqual(read('/stats')['rows'],rows+2)
                    self.assertNotEqual(second['snapshot']['id'],first['snapshot']['id'])
                    original=read('/entry/'+first['snapshot']['id'])
                    self.assertNotEqual(json.loads(original['body'])['report']['summary'],report['summary'])
                    # The real native graph/writer also preserves one company identity
                    # across independently created research runs and exact prior refs.
                    from tmf_research.engine import ResearchEngine
                    from test_missions import MissionModel
                    from test_engine import FakeWeb
                    company_request={'question':'What does this synthetic company establish?','depth':'quick','formats':['md','builder'],'council':False,
                        'mission':{'schema':'tmf-research-mission/1','type':'company','target':'Synthetic Example','collection':'web'}}
                    one=store.create(company_request,request_id='native-company-one')
                    ResearchEngine(store,config,model=MissionModel('company'),web=FakeWeb()).execute(one)
                    first_company=publish_candidates(store,one,config);self.assertEqual(first_company['status'],'published-candidate',first_company)
                    two=store.create(company_request,request_id='native-company-two')
                    ResearchEngine(store,config,model=MissionModel('company'),web=FakeWeb()).execute(two)
                    second_company=publish_candidates(store,two,config);self.assertEqual(second_company['status'],'published-candidate',second_company)
                    first_identity=next(x for x in first_company['references'] if x['kind']=='company-identity')
                    second_identity=next(x for x in second_company['references'] if x['kind']=='company-identity')
                    self.assertEqual(first_identity,second_identity)
                    intelligence=json.loads((store.directory(two)/'intelligence.json').read_text())
                    prior=intelligence['companies'][0]['continuity']['previous']
                    self.assertEqual(len(prior),1)
                    head=next(x for x in first_company['references'] if x['kind']=='company-investigation')
                    self.assertEqual(prior[0]['reference'],{'id':head['id'],'revision':1})
                    before=read('/stats')['rows'];self.assertEqual(publish_candidates(store,two,config),second_company)
                    self.assertEqual(read('/stats')['rows'],before)

                    # Professional roles use the same native Canon entries and
                    # exact revisions; exporting/retrying creates no new store.
                    profession=store.create({'question':'What does the synthetic profession establish?',
                        'depth':'quick','formats':['md'],'council':False,
                        'mission':{'schema':'tmf-research-mission/1','type':'profession',
                                   'target':'Synthetic operations','collection':'web'}},request_id='native-role')
                    ResearchEngine(store,config,model=MissionModel('profession'),web=FakeWeb()).execute(profession)
                    role_receipt=publish_candidates(store,profession,config)
                    self.assertEqual(role_receipt['status'],'published-candidate',role_receipt)
                    self.assertEqual(role_receipt['role_plugin']['status'],'available',role_receipt)
                    count=read('/stats')['rows']
                    self.assertEqual(publish_candidates(store,profession,config),role_receipt)
                    self.assertEqual(read('/stats')['rows'],count)
                    import zipfile
                    with zipfile.ZipFile(store.directory(profession)/'outputs'/role_receipt['role_plugin']['file']) as package:
                        role=json.loads(package.read('role.json'))
                    from tmf_research.canon import CanonConnection
                    connection=CanonConnection(config)
                    for ref in role['definition']['knowledge_references']:
                        collection=json.loads(connection.read(ref['id'],ref['revision'])['body'])
                        self.assertEqual(collection['entity'],'knowledge-collection')
                        for member in collection['knowledge_references']:
                            knowledge=json.loads(connection.read(member['id'],member['revision'])['body'])
                            self.assertEqual(knowledge['entity'],'professional-knowledge')

            finally:
                process.terminate()
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=3)
                process.stdout.close();process.stderr.close()
