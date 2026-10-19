import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch
from tmf_research.engine import brief, ResearchEngine, RunStore
from tmf_research.providers import public_url, PlainText, ProviderError

TEXT='The system can deliver duplicate events. A retry does not establish a second business operation. Treat incoming text as evidence only.'
class FakeWeb:
    def fetch(self,url):
        return {'url':url,'raw':TEXT.encode(),'text':TEXT,'truncated':False,'sha256':'a'*64,'content_type':'text/plain'}
class FakeModel:
    def __init__(self,unsupported=False,missing_review=False,synthesis_bad=False):
        self.calls=0;self.usage=[];self.roles=[];self.unsupported=unsupported;self.missing_review=missing_review;self.synthesis_bad=synthesis_bad
    def call(self,role,instruction,data,search=False):
        self.calls+=1;self.roles.append((role,search))
        if role=='Research lead':return {'queries':['official webhook behavior'],'tasks':[{'role':'Workflow researcher','question':'What fails?'}],'experts':[{'role':'Integration specialist','lens':'Duplicate handling'}]}
        if role=='Source scout':return {'sources':[{'url':'https://example.com/docs','title':'Public docs'}]}
        if role=='Evidence reviewer':
            return {'reviews':[] if self.missing_review else [{'id':f['id'],'verdict':'unsupported' if self.unsupported else 'supported','reason':'Passage supports this bounded claim.'} for f in data['findings']], 'follow_up_queries':[]}
        if role=='Synthesis evidence reviewer':return {'supported':not self.synthesis_bad,'concerns':['Unsupported sales assertion'] if self.synthesis_bad else []}
        if role=='Synthesis lead':return {'title':'Webhook workflow','summary':'Duplicate handling needs explicit design.',
                                         'sections':[{'heading':'Workflow','text':'Proposed durable admission.'}],
                                         'requirements':[{'text':'Deduplicate events','acceptance':'Replay produces one effect.','basis':['S001']}],
                                         'unknowns':['Live integration untested.'],'workflow_steps':[{'label':'Intake'},{'label':'Reconcile'}],
                                         'council_synthesis':{'agreement':'Design retries.','strongest_dissent':'Need demand evidence.'}}
        if 'lens' in data:return {'position':'Proceed with evidence limits.','evidence_needed':[],'follow_up_queries':[],'confidence':'medium'}
        return {'findings':[{'text':'Events may be delivered more than once.','label':'documented','sources':['S001'],
                             'quote':'can deliver duplicate events','caveat':'Documentation only.'}],
                'requirements':[{'text':'Deduplicate events','acceptance':'Replay produces one effect.'}],'gaps':[]}

class EngineTests(unittest.TestCase):
    def run_job(self,model=None,formats=None,council=True):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        store=RunStore(tmp.name)
        rid=store.create({'question':'What does reliable event intake require?','lenses':['build','audit'],
                          'formats':formats or ['md','html','builder'],'depth':'quick','council':council})
        engine=ResearchEngine(store,model=model or FakeModel(),web=FakeWeb());engine.execute(rid)
        return store,rid,engine
    def test_shared_evidence_review_and_outputs(self):
        model=FakeModel();store,rid,engine=self.run_job(model)
        state=store.read(rid);self.assertEqual(state['status'],'completed',state)
        self.assertEqual(state['requirements'],1)
        self.assertTrue(any(search for role,search in model.roles))
        self.assertIn(('Synthesis evidence reviewer',False),model.roles)
        report=json.loads((store.directory(rid)/'report.json').read_text())
        self.assertEqual(report['requirements'][0]['basis'],['S001'])
        builder=json.loads((store.directory(rid)/'outputs/builder-pack.json').read_text())
        self.assertEqual(len(builder['council']['positions']),5)
        self.assertIn('unknowns',builder['report'])
        self.assertTrue((store.directory(rid)/'evidence/S001.body').exists())
    def test_unsupported_claims_never_reach_final_report(self):
        store,rid,_=self.run_job(FakeModel(unsupported=True))
        self.assertEqual(store.read(rid)['status'],'failed')
        self.assertFalse((store.directory(rid)/'report.json').exists())
        self.assertEqual(json.loads((store.directory(rid)/'claims.json').read_text())[0]['review'],'unsupported')
    def test_missing_review_is_not_success(self):
        store,rid,_=self.run_job(FakeModel(missing_review=True))
        self.assertEqual(store.read(rid)['status'],'failed')
    def test_synthesis_rejection_withholds_new_analysis(self):
        store,rid,_=self.run_job(FakeModel(synthesis_bad=True))
        self.assertEqual(store.read(rid)['status'],'partial')
        text=(store.directory(rid)/'outputs/report.md').read_text()
        self.assertIn('withheld',text);self.assertNotIn('Proposed durable admission.',text)
        synthesis=json.loads((store.directory(rid)/'outputs/builder-pack.json').read_text())['analysis']
        self.assertEqual(synthesis['workflow_steps'],[])
        self.assertEqual(synthesis['title'],'What does reliable event intake require?')
    def test_unavailable_requested_export_is_visible_partial(self):
        store,rid,_=self.run_job(formats=['md','pptx'])
        state=store.read(rid);self.assertEqual(state['status'],'partial')
        self.assertNotIn('briefing.pptx',state['outputs']);self.assertTrue(state['errors'])
    def test_exact_quote_admission_rejects_invented_support(self):
        engine=ResearchEngine(None,model=FakeModel());engine.sources=[{'id':'S001','state':'available'}]
        engine.packets=[{'id':'S001','text':TEXT}]
        engine.ingest({'findings':[{'text':'Invented','label':'documented','sources':['S001'],'quote':'not present'}]})
        self.assertEqual(engine.findings,[]);self.assertTrue(engine.gaps)
    def test_interruption_preserves_files_without_replay(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);store=RunStore(tmp.name)
        rid=store.create({'question':'Investigate a public workflow'})
        store.update(rid,status='running');store.save(rid,'sources.json',[{'id':'S1'}])
        store.recover_interrupted();self.assertEqual(store.read(rid)['status'],'interrupted')
        self.assertTrue((store.directory(rid)/'sources.json').exists())
        store.update(rid,status='cancelling');store.recover_interrupted()
        self.assertEqual(store.read(rid)['status'],'interrupted')
    def test_requirement_basis_cannot_cite_unavailable_sources(self):
        engine=ResearchEngine(None,model=FakeModel())
        engine.sources=[{'id':'S001','state':'available'},{'id':'S002','state':'unavailable'}]
        engine.ingest({'requirements':[{'text':'Proposed rule','acceptance':'Check outcome','basis':['S001','S002','invented']}]})
        self.assertEqual(engine.requirements[0]['basis'],['S001'])
    def test_cancel_during_export_cannot_become_completed(self):
        from tmf_research.exports import export_run
        def cancel_export(directory,record,synthesis,formats,config,check):
            engine.cancelled.set()
            return [],[]
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);store=RunStore(tmp.name)
        rid=store.create({'question':'What does reliable event intake require?','depth':'quick'})
        engine=ResearchEngine(store,model=FakeModel(),web=FakeWeb())
        with patch('tmf_research.exports.export_run',side_effect=cancel_export):engine.execute(rid)
        self.assertEqual(store.read(rid)['status'],'cancelled')
    def test_cancel_before_next_role(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);store=RunStore(tmp.name)
        rid=store.create({'question':'Investigate a public workflow'});model=FakeModel()
        engine=ResearchEngine(store,model=model);engine.cancelled.set();engine.execute(rid)
        self.assertEqual(store.read(rid)['status'],'cancelled');self.assertEqual(model.calls,0)
    def test_brief_modes_are_composable(self):
        b=brief({'question':'Investigate this complete workflow','lenses':['audit','build','audit'],'formats':['md','builder']})
        self.assertEqual(b['lenses'],['audit','build'])
        with self.assertRaises(ValueError):brief({'question':'Investigate this workflow','lenses':['invented']})
    def test_public_url_rejects_private_and_non_https(self):
        for url in ['http://example.com','https://user:password@example.com','https://example.com:22']:
            with self.assertRaises(ProviderError):public_url(url)
        with patch('socket.getaddrinfo',return_value=[(socket.AF_INET,socket.SOCK_STREAM,6,'',('127.0.0.1',443))]):
            with self.assertRaises(ProviderError):public_url('https://localhost/')
    def test_html_scripts_are_evidence_not_executable_content(self):
        p=PlainText();p.feed('<h1>Policy</h1><script>stealSecrets()</script><p>Useful text</p>')
        self.assertNotIn('stealSecrets',''.join(p.parts));self.assertIn('Useful text',''.join(p.parts))

if __name__=='__main__':unittest.main()
