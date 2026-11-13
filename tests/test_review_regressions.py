"""Review edge cases, using temporary runs and synthetic providers only."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tmf_research.engine import ResearchEngine, RunStore
from tmf_research.canon import CanonConnection, CanonUnavailable, publish_intelligence, stable_id
from tmf_research.missions import normalize, permits, validate_output, COMPANY_SECTIONS
from tmf_research.providers import ProviderError
from test_engine import FakeModel, FakeWeb
from test_scrapling_plugin import server as scrapling, FakeFetcher, FakeStealthy, PUBLIC, FakeScraplingPlugin

class ReviewRegressions(unittest.TestCase):
    def test_exact_legacy_scope_with_colons_never_matches_its_parent(self):
        for scope in ('workspace:private', 'workspace:mission:'+ 'a'*32, 'workspace:company'):
            entry={'id':stable_id(scope), 'revision':1, 'fields':{'source':'tmf-research',
                'sourceId':'tmf-research:v1:'+scope+':knowledge:'+ 'b'*64},
                'body':json.dumps({'entity':'professional-knowledge','profession':'Fixture'})}
            connection=object.__new__(CanonConnection);connection.request=lambda *a,**kw:{'entry':entry}
            connection.scope=scope
            self.assertEqual(connection.read(entry['id'],1),entry,'existing colon-scoped data remains readable')
            connection.scope='workspace'
            with self.assertRaises(CanonUnavailable):connection.read(entry['id'],1)

    def test_domain_root_dot_cannot_evade_either_exclusion_boundary(self):
        mission=normalize({'schema':'tmf-research-mission/1','type':'technology','target':'Fixture',
            'excluded_domains':['example.com']})
        for host in ('example.com','example.com.','sub.example.com.','EXAMPLE.COM.'):
            url='https://'+host+'/docs'
            self.assertFalse(permits(mission,url),host)
            fetcher=FakeFetcher();collector=scrapling.Collector(fetcher,FakeStealthy(),'fixture')
            with patch('socket.getaddrinfo',return_value=PUBLIC):
                with self.assertRaisesRegex(scrapling.Refused,'scope'):collector.fetch(url,excluded_domains=['example.com'])
            self.assertEqual(fetcher.calls,[],'refuse before DNS, robots or content fetch')
        allowed=normalize({'schema':'tmf-research-mission/1','type':'technology','target':'Fixture',
            'permitted_domains':['example.com']})
        self.assertTrue(permits(allowed,'https://example.com./docs'))
        with patch('socket.getaddrinfo',return_value=PUBLIC):
            result=scrapling.Collector(FakeFetcher(),FakeStealthy(),'fixture').fetch(
                'https://example.com./docs',permitted_domains=['example.com'])
        self.assertEqual(result['final_url'],'https://example.com./docs')

    def test_failed_crawlee_start_still_uses_scrapling(self):
        class NoStart:
            def call(self,*a,**kw):raise ProviderError('Synthetic start failure')
        with tempfile.TemporaryDirectory() as tmp:
            store=RunStore(tmp);rid=store.create({'question':'Read the official source site','depth':'quick','council':False})
            engine=ResearchEngine(store,crawlee=NoStart());engine.run_id=rid
            engine.request=json.loads((store.directory(rid)/'brief.json').read_text());plugins=[]
            engine.scrapling_factory=lambda:plugins.append(FakeScraplingPlugin()) or plugins[-1]
            engine.swarm([{'url':'https://blocked.example/docs'}],1)
            fetched=[args['url'] for p in plugins for name,args in p.calls if name=='scrapling_fetch']
            self.assertEqual(fetched,['https://blocked.example/docs'])
            self.assertEqual(engine.sources[0]['crawler'],'scrapling')
            self.assertEqual(engine.acquisition['jobs'][0]['status'],'not started')

    def test_recovery_preserves_scope_limits_and_reuses_returned_council_calls(self):
        class ScopeModel(FakeModel):
            def __init__(self,crash=False):super().__init__();self.crash=crash
            def call(self,role,instruction,data,search=False):
                if self.crash and role=='Full-stack specialist':raise SystemExit('Synthetic process loss')
                value=super().call(role,instruction,data,search)
                if role=='Research lead':value['scope_limits']=['No production observation']
                return value
        with tempfile.TemporaryDirectory() as tmp:
            store=RunStore(tmp);rid=store.create({'question':'Explain duplicate delivery','depth':'quick','council':True,
                'council_members':['design','fullstack'],'council_auto_experts':False,'formats':['md'],
                'mission':{'schema':'tmf-research-mission/1','type':'technology','target':'Retries','budgets':{'concurrency':1,'calls':24}}})
            with self.assertRaises(SystemExit):ResearchEngine(store,model=ScopeModel(True),web=FakeWeb()).execute(rid)
            store.recover_interrupted();model=ScopeModel();engine=ResearchEngine(store,model=model,web=FakeWeb());engine.execute(rid,resume=True)
            self.assertEqual(store.read(rid)['status'],'completed')
            self.assertNotIn('Design systems specialist',[r for r,_ in model.roles])
            self.assertIn('Full-stack specialist',[r for r,_ in model.roles])
            self.assertEqual(engine.gaps.count('Lead scope limit: No production observation'),1)

    def test_root_rea_integrity_is_checked_for_new_and_legacy_checkpoints(self):
        for legacy in (False,True):
            with self.subTest(legacy=legacy),tempfile.TemporaryDirectory() as tmp:
                store=RunStore(tmp);rid=store.create({'question':'Inspect the chosen source artifact','depth':'quick'})
                request=json.loads((store.directory(rid)/'brief.json').read_text())
                engine=ResearchEngine(store);engine.run_id=rid
                engine.execution={'schema':'tmf-research-execution/1','brief_sha256':hashlib.sha256(json.dumps(request,sort_keys=True).encode()).hexdigest(),
                    'completed':{},'snapshot':{},'evidence':{},'inflight':None}
                store.save(rid,'REA1.json',{'evidence_id':'fixture','normalized_result':{'summary':'original'}})
                file=store.directory(rid)/'REA1.json'
                engine.sources=[{'id':'REA1','artifact_sha256':hashlib.sha256(file.read_bytes()).hexdigest()}]
                engine.checkpoint('inspect',lambda:None);store.update(rid,status='interrupted')
                if legacy:
                    engine.execution.pop('artifacts',None);store.save(rid,'execution.json',engine.execution)
                self.assertIsNotNone(ResearchEngine.resumable(store,rid),'unchanged legacy evidence stays resumable')
                file.write_text('changed')
                with self.assertRaisesRegex(ValueError,'integrity'):ResearchEngine.resumable(store,rid)
                file.unlink()
                with self.assertRaisesRegex(ValueError,'integrity'):ResearchEngine.resumable(store,rid)

    def test_nested_only_company_citation_keeps_publication_support(self):
        findings=[{'id':fid,'text':'Official fixture description','label':'documented','sources':['S001']} for fid in ('F001','F002')]
        mission=normalize({'schema':'tmf-research-mission/1','type':'company','target':'Fixture'})
        sections={k:{'text':'Unknown','label':'unknown','finding_ids':[]} for k in COMPANY_SECTIONS}
        sections['overview']={'text':'Official fixture description','label':'documented','finding_ids':['F002']}
        value=validate_output(mission,{'companies':[{'name':'Fixture','domain':'example.com','finding_ids':['F001'],'sections':sections}]},
            findings,'a'*32,'2026-11-13T00:00:00Z',sources=[{'id':'S001','url':'https://example.com/'}])
        value['verification']='model-reviewed'
        class PublicationFixture:
            def __init__(self):self.rows=[]
            def company_record(self,host):return None
            def put(self,key,title,payload,links):self.rows.append({'payload':payload,'links':links});return {'id':stable_id(key),'revision':1}
        connection=PublicationFixture();refs={fid:{'id':stable_id(fid),'revision':1} for fid in ('F001','F002')}
        publish_intelligence(connection,'tmf-research:v1:fixture:','tmf-research:v1:fixture:mission:'+'a'*32,
            value,refs,lambda *a:None,lambda:None)
        row=next(r for r in connection.rows if r['payload'].get('entity')=='company-investigation')
        self.assertEqual(set(row['payload']['finding_revisions']),{'F001','F002'})
        self.assertEqual({link['to'] for link in row['links'] if link['kind']=='supported-by'},{r['id'] for r in refs.values()})

    def test_http_pause_at_publication_commit_can_resume_and_cancel(self):
        import threading
        import time
        import urllib.request
        import tmf_research.server as workbench
        for action in ('resume','cancel'):
            with self.subTest(action=action),tempfile.TemporaryDirectory() as tmp:
                entered=threading.Event();release=threading.Event();created=threading.Event();handles={}
                class BoundaryEngine(ResearchEngine):
                    def __init__(self,store,config):
                        super().__init__(store,config,model=FakeModel(),web=FakeWeb());handles['engine']=self
                    def check(self):
                        if (self.store.directory(self.run_id)/'usage.json').exists() and not entered.is_set():
                            entered.set();release.wait(3)
                        super().check()
                real_server=workbench.ThreadingHTTPServer
                def server(*args,**kw):
                    handles['server']=real_server(*args,**kw);created.set();return handles['server']
                with patch.object(workbench,'ResearchEngine',BoundaryEngine),patch.object(workbench,'ThreadingHTTPServer',server):
                    serving=threading.Thread(target=lambda:workbench.serve(tmp,port=0),daemon=True);serving.start()
                    self.assertTrue(created.wait(2));base='http://127.0.0.1:'+str(handles['server'].server_port)
                    def request(path,payload=None,timeout=1):
                        req=urllib.request.Request(base+path,data=json.dumps(payload).encode() if payload is not None else None,
                            headers={'Content-Type':'application/json','X-TMF-Token':handles.get('token','')})
                        with urllib.request.urlopen(req,timeout=timeout) as reply:return json.load(reply)
                    try:
                        handles['token']=request('/api/config')['token']
                        rid=request('/api/runs',{'question':'Explain duplicate delivery','depth':'quick','council':False,'formats':['md']})['id']
                        self.assertTrue(entered.wait(3))
                        outcome={}
                        def pause():
                            try:outcome['response']=request('/api/pause',{'id':rid})
                            except OSError as exc:outcome['error']=type(exc).__name__
                        pausing=threading.Thread(target=pause,daemon=True);pausing.start()
                        for _ in range(100):
                            if handles['engine'].pause_requested.is_set():break
                            time.sleep(.01)
                        self.assertTrue(handles['engine'].pause_requested.is_set());release.set();pausing.join(2)
                        self.assertEqual(outcome.get('response',{}).get('status'),'pausing',outcome)
                        self.assertIn(request('/api/'+action,{'id':rid})['status'],('running','cancelling'))
                        for _ in range(100):
                            state=request('/api/runs/'+rid)
                            if state['stage'] in ('done','cancelled'):break
                            time.sleep(.01)
                        self.assertEqual(state['status'],'completed' if action=='resume' else 'cancelled',state)
                    finally:
                        release.set()
                        if 'engine' in handles:handles['engine'].pause_requested.clear();handles['engine'].cancelled.set()
                        if 'pausing' in locals():pausing.join(2)
                        handles['server'].shutdown();serving.join(2);handles['server'].server_close()

    def test_ambiguous_legacy_key_collision_cannot_overwrite_another_scope(self):
        from tmf_research.canon import digest, encoded
        # The same v1 bytes could name a nested scope's root company identity,
        # or a parent scope's mission company observation. Existing data wins.
        key='tmf-research:v1:workspace:mission:'+ 'a'*32+':company:'+ 'b'*64
        original={'entity':'company-identity','domain':'example.com'}
        entry={'id':stable_id(key),'revision':1,'body':encoded(original),
            'fields':{'source':'tmf-research','sourceId':key,'sourceHash':digest(original),
                      'status':'draft','reviewStatus':'candidate'},'links':[]}
        writes=[];connection=object.__new__(CanonConnection);connection.scope='workspace'
        def request(path,payload):
            writes.append(payload)
            return entry
        connection.request=request
        with self.assertRaises(CanonUnavailable):
            connection.put(key,'Parent observation',{'entity':'company-investigation','intelligence':{'domain':'example.com'}},[])
        self.assertFalse(any('id' in call for call in writes),'no revision update to the colliding legacy identity')
        self.assertEqual(entry['body'],encoded(original))

    def test_legacy_rea_without_a_saved_digest_is_refused_without_rewriting_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=RunStore(tmp);rid=store.create({'question':'Inspect the retained source artifact','depth':'quick'})
            request=json.loads((store.directory(rid)/'brief.json').read_text())
            checkpoint={'schema':'tmf-research-execution/1','brief_sha256':hashlib.sha256(json.dumps(request,sort_keys=True).encode()).hexdigest(),
                'completed':{'inspect':{'result':None}},'snapshot':{'sources':[{'id':'REA1'}]},'evidence':{},'inflight':None}
            store.save(rid,'execution.json',checkpoint);store.save(rid,'REA1.json',{'evidence_id':'fixture'})
            store.update(rid,status='interrupted')
            before={p.name:p.read_bytes() for p in store.directory(rid).iterdir() if p.is_file()}
            with self.assertRaisesRegex(ValueError,'no integrity digest'):ResearchEngine.resumable(store,rid)
            after={p.name:p.read_bytes() for p in store.directory(rid).iterdir() if p.is_file()}
            self.assertEqual(after,before,'no migration, replacement digest or destructive recovery')
