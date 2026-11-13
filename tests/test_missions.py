import copy
import json
from pathlib import Path
import tempfile
import unittest
from tmf_research.engine import brief, ResearchEngine, RunStore
from tmf_research.missions import SCHEMA, COMPANY_SECTIONS, normalize, validate_output, permits
from test_engine import FakeModel, FakeWeb
from test_pre_build import FakeCrawlee, FailIfFetched


def section(label='documented'):
    return {'heading':'Synthetic evidence','text':'Events may be delivered more than once.',
            'finding_ids':['F001'],'label':label}


def specialty():
    return {'name':'Synthetic operations specialist','purpose':'Evaluate duplicate-event handling.',
            'responsibilities':['Evaluate supplied evidence.'],'procedures':['Check source version.'],
            'instructions':['Separate inference from documented behavior.'],
            'evaluation_criteria':['Cite each relevant finding.'],'required_capabilities':['research']}


def output(kind):
    company={'name':'Synthetic Example','domain':'example.com','finding_ids':['F001'],
             'sections':{name:section('proposed' if name in ('opportunities','consulting_questions','possible_services') else 'documented') for name in COMPANY_SECTIONS}}
    if kind in ('company','startup'):return {'companies':[company]}
    if kind=='leads':return {'leads':[{'company':'Synthetic Example','domain':'example.com','industry':'Synthetic operations',
        'opportunity':'Assess event handling.','potential_service':'Evidence-backed integration review.',
        'estimated_fit':'Unknown until a client confirms internal needs.','confidence':'low','finding_ids':['F001'],
        'assumptions':['Internal business need is not established.']}]}
    if kind=='market':return {'market':{'name':'Synthetic event systems','sections':[section()]}}
    if kind=='profession':return {'knowledge':{'profession':'Synthetic operations','domains':[section()], 'specialty':specialty()}}
    if kind=='person':return {'person':{'name':'Synthetic Public Author','documented_work':[section()],
        'communication_patterns':[section('inferred')],'generic_specialty':specialty()}}
    raise AssertionError(kind)


class MissionModel(FakeModel):
    def __init__(self,kind,invalid=False,reject=False):
        super().__init__();self.kind=kind;self.invalid=invalid;self.reject=reject;self.inputs=[]
    def call(self,role,instruction,data,search=False):
        self.inputs.append((role,data))
        if role=='Mission intelligence analyst':
            self.calls+=1;self.roles.append((role,search));result=output(self.kind)
            if self.invalid:result['leads'][0]['finding_ids']=['invented']
            return result
        if role=='Mission output evidence reviewer':
            self.calls+=1;self.roles.append((role,search));return {'supported':not self.reject,'concerns':['Synthetic rejection'] if self.reject else []}
        return super().call(role,instruction,data,search)


class MissionTests(unittest.TestCase):
    def request(self,kind='company',**extra):
        return {'question':'What does the synthetic evidence establish?', 'depth':'quick','formats':['md','builder'],'council':False,
                'mission':{'schema':SCHEMA,'type':kind,'target':'Synthetic Example','collection':'web',**extra}}
    def execute(self,kind,model=None,request=None,web=None,crawlee=None):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        store=RunStore(temp.name);rid=store.create(request or self.request(kind),request_id='synthetic-mission')
        model=model or MissionModel(kind)
        engine=ResearchEngine(store,model=model,web=web or FakeWeb(),crawlee=crawlee);engine.execute(rid)
        return store,rid,model

    def test_versioned_missions_preserve_old_request_identity_and_validate_fields(self):
        original=brief({'question':'What does the synthetic evidence establish?'})
        self.assertNotIn('mission',original)
        normalized=brief(self.request())
        self.assertEqual(normalized,brief(normalized))
        for change in ({'schema':'unknown'},{'type':'security'},{'token':'forbidden'}, {'budgets':{'calls':0}},
                       {'budgets':{'concurrency':True}},{'permitted_domains':['example.com/path']}):
            with self.subTest(change=change),self.assertRaises(ValueError):normalize({**self.request()['mission'],**change})
        self.assertEqual(normalize({'schema':SCHEMA,'type':'leads','target':'Industry and region'})['collection'],'plugins')

    def test_business_and_knowledge_outputs_run_through_existing_engine(self):
        for kind in ('company','startup','leads','market','profession','person'):
            with self.subTest(kind=kind):
                request=self.request(kind,**({'public_person':True} if kind=='person' else {}))
                store,rid,model=self.execute(kind,request=request)
                state=store.read(rid);self.assertEqual(state['status'],'partial' if kind in ('startup','leads') else 'completed',state)
                directory=store.directory(rid)
                value=json.loads((directory/'intelligence.json').read_text())
                self.assertEqual(value['mission_type'],kind)
                self.assertEqual(value['verification'],'model-reviewed')
                self.assertEqual(value['review_status'],'candidate')
                self.assertFalse(value['independent_verification'])
                self.assertEqual(value['evidence']['F001']['sources'][0]['url'],'https://example.com/docs')
                self.assertIn('intelligence.json',state['outputs'])
                receipt=json.loads((directory/'outputs/export-receipt.json').read_text())
                self.assertTrue(any(x['file']=='intelligence.json' for x in receipt['artifacts']))
                self.assertEqual(len(list(store.root.glob('*/state.json'))),1)
                self.assertIn(('Mission output evidence reviewer',False),model.roles)

    def test_invalid_or_unreviewed_intelligence_is_withheld_and_research_partial(self):
        for model in (MissionModel('leads',invalid=True),MissionModel('leads',reject=True)):
            store,rid,_=self.execute('leads',model)
            self.assertEqual(store.read(rid)['status'],'partial')
            self.assertFalse((store.directory(rid)/'intelligence.json').exists())
            self.assertTrue((store.directory(rid)/'report.json').exists())
            self.assertTrue(any('Mission output withheld' in e for e in store.read(rid)['errors']))

    def test_inference_cannot_be_promoted_to_documented_or_empty_citations(self):
        finding={'id':'F001','label':'inferred'}
        value=output('company')
        with self.assertRaises(ValueError):validate_output(normalize(self.request()['mission']),value,[finding],'a'*32,'2026-01-01T00:00:00Z')
        value['companies'][0]['finding_ids']=[]
        with self.assertRaises(ValueError):validate_output(normalize(self.request()['mission']),value,[],'a'*32,'2026-01-01T00:00:00Z')

    def test_duplicate_company_domains_merge_only_equivalent_evidence(self):
        value=output('leads');value['leads'].append(copy.deepcopy(value['leads'][0]))
        mission=normalize(self.request('leads')['mission']);findings=[{'id':'F001','label':'documented','text':'Synthetic company docs','sources':['S001']}]
        sources=[{'id':'S001','url':'https://example.com/docs','state':'available','retrieved_at':'2026-01-01T00:00:00Z'}]
        normalized=validate_output(mission,value,findings,'a'*32,'2026-01-01T00:00:00Z',sources=sources)
        self.assertEqual(len(normalized['leads']),1)
        value['leads'][1]['opportunity']='A conflicting invented need'
        with self.assertRaisesRegex(ValueError,'Conflicting duplicate'):validate_output(mission,value,findings,'a'*32,'2026-01-01T00:00:00Z',sources=sources)

    def test_private_person_consent_and_simulation_labels_are_explicit(self):
        mission={**self.request('person')['mission'],'public_person':False}
        with self.assertRaises(ValueError):normalize(mission)
        self.assertEqual(normalize({**mission,'consent':'Synthetic documented consent'})['public_person'],False)
        value=validate_output(normalize({**mission,'public_person':True}),output('person'),[{'id':'F001','label':'documented'}],'a'*32,'2026-01-01T00:00:00Z')
        self.assertIn('not the person',value['person']['simulation_label'])
        self.assertEqual(value['person']['private_thoughts'],'unknown')
        self.assertFalse(value['person']['generic_specialty']['grants_authority'])
        self.assertEqual(value['person']['generic_specialty']['hub_import_status'],'not-connected')

    def test_scope_filters_source_collection_and_redirects(self):
        mission=normalize(self.request(permitted_domains=['example.com'],excluded_domains=['private.example.com'])['mission'])
        self.assertTrue(permits(mission,'https://docs.example.com/reference'))
        self.assertFalse(permits(mission,'https://example.com.evil.test/reference'))
        self.assertFalse(permits(mission,'https://private.example.com/reference'))
        class Redirect(FakeWeb):
            def fetch(self,url):return {**super().fetch(url),'url':'https://outside.example/reference'}
        store,rid,_=self.execute('company',request=self.request(permitted_domains=['example.com']),web=Redirect())
        self.assertEqual(store.read(rid)['status'],'failed')
        self.assertFalse((store.directory(rid)/'evidence/S001.body').exists())

    def test_plugin_collection_is_reused_without_public_fallback(self):
        request=self.request('company',collection='plugins')
        store,rid,_=self.execute('company',request=request,web=FailIfFetched(),crawlee=FakeCrawlee())
        self.assertEqual(store.read(rid)['status'],'completed',store.read(rid))
        self.assertEqual(json.loads((store.directory(rid)/'sources.json').read_text())[0]['crawler'],'crawlee')

    def test_mission_budget_and_completion_criteria_survive_and_are_used(self):
        request=self.request('company',budgets={'calls':1,'sources':1,'concurrency':1,'rounds':0},completion_criteria=['Explicit synthetic criterion'])
        store,rid,model=self.execute('company',request=request)
        self.assertEqual(model.calls,1)
        self.assertEqual(store.read(rid)['status'],'failed')
        self.assertIn('Explicit synthetic criterion',json.loads((store.directory(rid)/'plan.json').read_text())['success_criteria'])

    def test_custom_council_runs_distinct_responsibilities_on_existing_loop(self):
        specialists=[{'name':'Synthetic market specialist','responsibilities':'Evaluate source-backed market claims.'},
                     {'name':'Synthetic systems specialist','responsibilities':'Evaluate integration failure evidence.'}]
        request=self.request('council',specialists=specialists);request['council']=True
        store,rid,model=self.execute('council',request=request,model=FakeModel())
        self.assertEqual(store.read(rid)['status'],'completed',store.read(rid))
        council=json.loads((store.directory(rid)/'council.json').read_text())
        self.assertEqual({p['role'] for p in council['positions']},{s['name'] for s in specialists})
        self.assertEqual(json.loads((store.directory(rid)/'intelligence.json').read_text())['configuration'],specialists)
        with self.assertRaises(ValueError):brief({**request,'council':False})

    def test_paused_controller_resumes_same_job_without_replaying_completed_calls(self):
        import threading,time
        entered=threading.Event();release=threading.Event()
        class BlockLead(FakeModel):
            def call(self,role,instruction,data,search=False):
                if role=='Research lead':entered.set();release.wait(2)
                return super().call(role,instruction,data,search)
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);store=RunStore(temp.name)
        rid=store.create({'question':'What does synthetic event handling establish?','depth':'quick','formats':['md'],'council':False})
        model=BlockLead();engine=ResearchEngine(store,model=model,web=FakeWeb())
        thread=threading.Thread(target=engine.execute,args=(rid,),daemon=True);thread.start()
        try:
            self.assertTrue(entered.wait(2));engine.pause_requested.set();store.update(rid,status='pausing');release.set()
            for _ in range(100):
                if store.read(rid)['status']=='paused':break
                time.sleep(.01)
            self.assertEqual(store.read(rid)['status'],'paused')
            self.assertEqual(model.calls,1)
            engine.pause_requested.clear();store.update(rid,status='running');thread.join(3)
            self.assertFalse(thread.is_alive());self.assertEqual(store.read(rid)['status'],'completed')
            self.assertEqual(sum(role=='Research lead' for role,_ in model.roles),1)
            self.assertEqual(len(list(store.root.iterdir())),1)
        finally:engine.cancelled.set();engine.pause_requested.clear();release.set();thread.join(2)

    def test_swarm_reserves_global_source_budget_and_cancels_owned_remote_jobs(self):
        request=self.request('company',collection='plugins',budgets={'sources':2})
        crawler=FakeCrawlee();store,rid,_=self.execute('company',request=request,crawlee=crawler)
        self.assertLessEqual(sum(args['max_pages'] for name,args in crawler.calls if name=='crawlee_start'),2)
        class CancelOnStart(FakeCrawlee):
            def call(self,name,args):
                if name=='crawlee_cancel':self.calls.append((name,args));return {'status':'cancelling'}
                result=super().call(name,args)
                if name=='crawlee_start':engine.cancelled.set()
                return result
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);store=RunStore(temp.name);rid=store.create(request)
        crawler=CancelOnStart();engine=ResearchEngine(store,model=MissionModel('company'),web=FailIfFetched(),crawlee=crawler);engine.execute(rid)
        self.assertEqual(store.read(rid)['status'],'cancelled')
        self.assertTrue(any(name=='crawlee_cancel' for name,_ in crawler.calls))
        self.assertTrue((store.directory(rid)/'acquisition.json').exists())

    def test_knowledge_reuse_reads_exact_canon_revision_and_fails_visibly_when_disconnected(self):
        from tmf_research.canon import CanonConnection
        from unittest.mock import patch
        request=self.request('general',knowledge_refs=[{'id':'cn-'+'a'*8+'-'+ 'a'*4+'-4aaa-8aaa-'+ 'a'*12,'revision':3}])
        source={'id':'known','revision':3,'title':'Prior synthetic knowledge','body':'The system can deliver duplicate events. '+('Synthetic evidence. '*10)}
        with patch.object(CanonConnection,'__init__',return_value=None),patch.object(CanonConnection,'read',return_value=source) as read:
            store,rid,_=self.execute('general',request=request,model=FakeModel())
        self.assertEqual(store.read(rid)['status'],'completed',store.read(rid))
        read.assert_called_once_with(request['mission']['knowledge_refs'][0]['id'],3)
        sources=json.loads((store.directory(rid)/'sources.json').read_text())
        self.assertEqual(sources[0]['kind'],'canon-knowledge')
        self.assertEqual(sources[0]['canon']['revision'],3)
        store,rid,model=self.execute('general',request=request,model=FakeModel())
        self.assertEqual(store.read(rid)['status'],'failed');self.assertEqual(model.calls,0)

    def test_unknown_required_company_sections_make_the_mission_partial(self):
        class MissingOverview(MissionModel):
            def call(self,role,instruction,data,search=False):
                value=super().call(role,instruction,data,search)
                if role=='Mission intelligence analyst':value['companies'][0]['sections']['overview']={'text':'Unknown from retrieved sources','label':'unknown','finding_ids':[]}
                return value
        store,rid,_=self.execute('company',model=MissingOverview('company'))
        self.assertEqual(store.read(rid)['status'],'partial')
        self.assertTrue((store.directory(rid)/'intelligence.json').exists())
        self.assertTrue(any('Mission section remains unknown' in e for e in store.read(rid)['errors']))

    def test_crawlee_tampered_text_never_becomes_evidence(self):
        class Tampered(FakeCrawlee):
            def call(self,name,args):
                value=super().call(name,args)
                if name=='crawlee_read':value['text']='A different untrusted source body. '*10
                return value
        from unittest.mock import patch
        from tmf_research.providers import ProviderError
        with patch('tmf_research.engine.ScraplingPlugin',side_effect=ProviderError('Synthetic unavailable fallback')):
            store,rid,_=self.execute('company',request=self.request('company',collection='plugins'),crawlee=Tampered(),web=FailIfFetched())
        self.assertEqual(store.read(rid)['status'],'failed')
        self.assertFalse((store.directory(rid)/'report.json').exists())

    def test_small_source_budget_still_acquires_initial_evidence_with_followups_enabled(self):
        store,rid,_=self.execute('general',request=self.request('general',budgets={'sources':1,'rounds':1}),model=FakeModel())
        self.assertEqual(store.read(rid)['status'],'completed',store.read(rid))
        self.assertEqual(len(json.loads((store.directory(rid)/'sources.json').read_text())),1)

    def test_documented_evidence_is_not_an_observed_claim(self):
        mission=normalize(self.request()['mission']);value=output('company')
        value['companies'][0]['sections']['overview']['label']='observed'
        with self.assertRaises(ValueError):validate_output(mission,value,[{'id':'F001','label':'documented'}],'a'*32,'2026-01-01T00:00:00Z')

    def test_scoped_https_redirect_is_refused_before_contacting_the_other_host(self):
        from tmf_research.providers import PublicWeb,ProviderError
        from unittest.mock import patch
        import socket
        calls=[]
        class Redirect:
            status=302
            def getheader(self,name,default=None):return 'https://outside.example/reference' if name=='Location' else default
        public=[(socket.AF_INET,socket.SOCK_STREAM,6,'',('93.184.216.34',443))]
        with patch('tmf_research.providers.public_url'),patch('socket.getaddrinfo',return_value=public),              patch('http.client.HTTPSConnection.request',side_effect=lambda *a,**k:calls.append('request')),              patch('http.client.HTTPSConnection.getresponse',return_value=Redirect()):
            with self.assertRaises(ProviderError):PublicWeb(permitted=lambda u:u.startswith('https://example.com/')).fetch('https://example.com/start')
        self.assertEqual(calls,['request'])

    def test_crawler_evidence_can_be_refined_without_recollecting_or_losing_hashes(self):
        request=self.request('company',collection='plugins')
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);store=RunStore(temp.name)
        parent=store.create(request)
        ResearchEngine(store,model=MissionModel('company'),web=FailIfFetched(),crawlee=FakeCrawlee()).execute(parent)
        rid=store.create(request)
        ResearchEngine(store,model=MissionModel('company'),web=FailIfFetched()).refine(rid,parent,'Make the synthetic briefing clearer')
        self.assertEqual(store.read(rid)['status'],'completed',store.read(rid))
        self.assertTrue((store.directory(rid)/'intelligence.json').exists())
        self.assertEqual((store.directory(parent)/'evidence/S001.body').read_bytes(),(store.directory(rid)/'evidence/S001.body').read_bytes())
