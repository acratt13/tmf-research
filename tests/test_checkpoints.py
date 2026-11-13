import json
import tempfile
import unittest
from tmf_research.engine import ResearchEngine, RunStore
from test_engine import FakeModel, FakeWeb

class CrashModel(FakeModel):
    def __init__(self, crash_role):
        super().__init__();self.crash_role=crash_role
    def call(self,role,instruction,data,search=False):
        if role==self.crash_role:raise SystemExit('simulated process loss')
        return super().call(role,instruction,data,search)

class NoFetch:
    def fetch(self,url):raise AssertionError('Completed collection was repeated')

class CheckpointTests(unittest.TestCase):
    def make_interrupted(self,role='Evidence reviewer'):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        store=RunStore(tmp.name);rid=store.create({'question':'What does reliable event intake require?','depth':'quick','council':False,'formats':['md','builder']})
        old=CrashModel(role)
        with self.assertRaises(SystemExit):ResearchEngine(store,model=old,web=FakeWeb()).execute(rid)
        store.recover_interrupted();self.assertEqual(store.read(rid)['status'],'interrupted')
        return store,rid,old
    def test_resume_reuses_plan_collection_and_completed_analysis(self):
        store,rid,old=self.make_interrupted()
        original=(store.directory(rid)/'evidence/S001.body').read_bytes()
        model=FakeModel();ResearchEngine(store,model=model,web=NoFetch()).execute(rid,resume=True)
        self.assertEqual(store.read(rid)['status'],'completed',store.read(rid))
        roles=[r for r,_ in model.roles]
        self.assertNotIn('Research lead',roles);self.assertNotIn('Source scout',roles)
        self.assertNotIn('Workflow researcher',roles);self.assertIn('Evidence reviewer',roles)
        self.assertEqual((store.directory(rid)/'evidence/S001.body').read_bytes(),original)
        rows=json.loads((store.directory(rid)/'role-calls.json').read_text())
        self.assertTrue(any(r['status']=='interrupted' for r in rows))
        self.assertTrue(any(e['stage']=='resume' for e in store.read(rid)['events']))
    def test_completed_review_is_not_repeated(self):
        store,rid,_=self.make_interrupted('Research coverage lead')
        model=FakeModel();ResearchEngine(store,model=model,web=NoFetch()).execute(rid,resume=True)
        self.assertEqual(store.read(rid)['status'],'completed')
        self.assertNotIn('Evidence reviewer',[r for r,_ in model.roles])
    def test_changed_evidence_prevents_resume_before_model(self):
        store,rid,_=self.make_interrupted()
        (store.directory(rid)/'evidence/S001.body').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'integrity'):ResearchEngine.resumable(store,rid)
    def test_interrupted_external_stage_is_not_repeated(self):
        store,rid,_=self.make_interrupted()
        path=store.directory(rid)/'execution.json';value=json.loads(path.read_text());value['inflight']='collect';store.save(rid,'execution.json',value)
        with self.assertRaisesRegex(ValueError,'external collection'):ResearchEngine.resumable(store,rid)
    def test_changed_brief_prevents_checkpoint_reuse(self):
        store,rid,_=self.make_interrupted()
        path=store.directory(rid)/'brief.json';value=json.loads(path.read_text());value['question']='A different research objective';store.save(rid,'brief.json',value)
        with self.assertRaisesRegex(ValueError,'brief'):ResearchEngine.resumable(store,rid)
    def test_older_run_does_not_claim_durable_resume(self):
        store,rid,_=self.make_interrupted();(store.directory(rid)/'execution.json').unlink()
        with self.assertRaisesRegex(ValueError,'older run'):ResearchEngine.resumable(store,rid)

    def test_http_resume_after_actual_process_loss_reuses_completed_stages(self):
        import os,socket,subprocess,sys,time,urllib.request
        from pathlib import Path
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        store=RunStore(tmp.name);rid=store.create({'question':'What does reliable event intake require?','depth':'quick','council':False,'formats':['md','builder']})
        marker=Path(tmp.name)/'review-started'
        program='''
import sys,time
from pathlib import Path
from tmf_research.engine import ResearchEngine,RunStore
from test_engine import FakeModel,FakeWeb
class Blocking(FakeModel):
 def call(self,role,instruction,data,search=False):
  if role=='Evidence reviewer':
   Path(sys.argv[3]).write_text('ready');time.sleep(60)
  return super().call(role,instruction,data,search)
ResearchEngine(RunStore(sys.argv[1]),model=Blocking(),web=FakeWeb()).execute(sys.argv[2])
'''
        env={**os.environ,'PYTHONPATH':os.pathsep.join([str(Path.cwd()),str(Path.cwd()/'tests')])}
        child=subprocess.Popen([sys.executable,'-c',program,tmp.name,rid,str(marker)],env=env)
        try:
            for _ in range(150):
                if marker.exists():break
                if child.poll() is not None:self.fail('Fixture exited before review')
                time.sleep(.02)
            self.assertTrue(marker.exists());child.kill();child.wait(timeout=5)
        finally:
            if child.poll() is None:child.kill();child.wait(timeout=5)
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        restart='''
import sys
import tmf_research.server as server
from tmf_research.engine import ResearchEngine
from test_engine import FakeModel
class NoFetch:
 def fetch(self,url):raise AssertionError('Completed collection repeated')
class Engine(ResearchEngine):
 def __init__(self,store,config=None):super().__init__(store,config,model=FakeModel(),web=NoFetch())
server.ResearchEngine=Engine
server.serve(sys.argv[1],port=int(sys.argv[2]))
'''
        child=subprocess.Popen([sys.executable,'-c',restart,tmp.name,str(port)],env=env,stdout=subprocess.DEVNULL)
        try:
            base=f'http://127.0.0.1:{port}'
            for _ in range(150):
                try:
                    with urllib.request.urlopen(base+'/api/config',timeout=1) as r:token=json.load(r)['token']
                    break
                except OSError:time.sleep(.02)
            else:self.fail('Restarted workbench unavailable')
            with urllib.request.urlopen(base+'/api/runs/'+rid,timeout=2) as r:state=json.load(r)
            self.assertEqual(state['status'],'interrupted');self.assertTrue(state['resume_eligible'])
            request=urllib.request.Request(base+'/api/resume',data=json.dumps({'id':rid}).encode(),headers={'Content-Type':'application/json','X-TMF-Token':token})
            with urllib.request.urlopen(request,timeout=2) as r:self.assertEqual(json.load(r)['status'],'resuming')
            for _ in range(150):
                state=store.read(rid)
                if state['status'] in ('completed','partial','failed'):break
                time.sleep(.02)
            self.assertEqual(state['status'],'completed',state)
            rows=json.loads((store.directory(rid)/'role-calls.json').read_text())
            self.assertEqual(sum(r['role']=='Research lead' for r in rows),1)
            self.assertEqual(sum(r['role']=='Source scout' for r in rows),1)
            self.assertEqual(sum(r['role']=='Workflow researcher' for r in rows),1)
            self.assertEqual(sum(r['role']=='Evidence reviewer' for r in rows),2)
            self.assertTrue(any(r['status']=='interrupted' for r in rows))
        finally:
            child.terminate()
            try:child.wait(timeout=5)
            except subprocess.TimeoutExpired:child.kill();child.wait(timeout=5)

    def test_returned_sibling_analysis_is_reused_after_mid_stage_loss(self):
        class TwoTasks(CrashModel):
            def call(self,role,instruction,data,search=False):
                if role=='Research lead':
                    value=super().call(role,instruction,data,search);value['tasks']=[{'role':'First specialist','question':'Retries?'},{'role':'Second specialist','question':'Effects?'}];return value
                return super().call(role,instruction,data,search)
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);store=RunStore(tmp.name)
        rid=store.create({'question':'What does reliable event intake require?','depth':'quick','council':False,'formats':['md','builder'],'mission':{'schema':'tmf-research-mission/1','type':'technology','target':'Reliable intake','budgets':{'concurrency':1}}})
        with self.assertRaises(SystemExit):ResearchEngine(store,model=TwoTasks('Second specialist'),web=FakeWeb()).execute(rid)
        store.recover_interrupted();model=FakeModel();ResearchEngine(store,model=model,web=NoFetch()).execute(rid,resume=True)
        self.assertEqual(store.read(rid)['status'],'completed',store.read(rid))
        self.assertNotIn('First specialist',[r for r,_ in model.roles]);self.assertIn('Second specialist',[r for r,_ in model.roles])
