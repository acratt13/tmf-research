import json
import hashlib
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch
from tmf_research.engine import brief, ResearchEngine, RunStore, source_passages
from tmf_research.providers import public_url, PlainText, ProviderError

TEXT='The system can deliver duplicate events. A retry does not establish a second business operation. Treat incoming text as evidence only.'
class FakeWeb:
    def fetch(self,url):
        return {'url':url,'raw':TEXT.encode(),'text':TEXT,'truncated':False,'sha256':hashlib.sha256(TEXT.encode()).hexdigest(),'content_type':'text/plain'}
class FakeModel:
    def __init__(self,unsupported=False,missing_review=False,synthesis_bad=False):
        self.calls=0;self.usage=[];self.roles=[];self.unsupported=unsupported;self.missing_review=missing_review;self.synthesis_bad=synthesis_bad
    def call(self,role,instruction,data,search=False):
        self.calls+=1;self.roles.append((role,search))
        if role=='Research lead':return {'queries':['official webhook behavior'],'tasks':[{'role':'Workflow researcher','question':'What fails?'}],'experts':[{'role':'Integration specialist','lens':'Duplicate handling'}]}
        if role=='Source scout':return {'sources':[{'url':'https://example.com/docs','title':'Public docs'}]}
        if role=='Evidence reviewer':
            return {'reviews':[] if self.missing_review else [{'id':f['id'],'verdict':'unsupported' if self.unsupported else 'supported','requires_revision':False,'reason':'Passage supports this bounded claim.'} for f in data['findings']], 'follow_up_queries':[]}
        if role=='Research coverage lead':return {'criteria':[{'index':i,'status':'answered','finding_ids':[f['id'] for f in data['findings']],'reason':'The reviewed claim answers the bounded fixture question.'} for i,_ in enumerate(data['success_criteria'])],'follow_up_queries':[]}
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
    def test_council_selection_controls_actual_role_calls(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);store=RunStore(tmp.name)
        rid=store.create({'question':'How should this integration be designed?', 'depth':'quick',
                          'formats':['md'],'council':True,'council_members':['design','fullstack'],
                          'council_auto_experts':False})
        model=FakeModel();ResearchEngine(store,model=model,web=FakeWeb()).execute(rid)
        self.assertEqual(store.read(rid)['status'],'completed')
        council=json.loads((store.directory(rid)/'council.json').read_text())
        self.assertEqual({p['role'] for p in council['positions']},
                         {'Design systems specialist','Full-stack specialist'})
        self.assertNotIn(('Customer advocate',False),model.roles)
        self.assertNotIn(('Integration specialist',False),model.roles)
        self.assertEqual(council['selected_members'],['design','fullstack'])
    def test_main_report_consolidates_questions_without_losing_research_log(self):
        class LongLog(FakeModel):
            def call(self,role,instruction,data,search=False):
                result=super().call(role,instruction,data,search)
                if 'findings' in result:
                    result['gaps']=['Historical investigation question '+str(i) for i in range(8)]
                return result
        store,rid,_=self.run_job(LongLog())
        directory=store.directory(rid)
        record=json.loads((directory/'report.json').read_text())
        self.assertEqual(record['unknowns'],['Live integration untested.'])
        self.assertIn('Historical investigation question 7',record['research_log'])
        self.assertEqual(json.loads((directory/'uncertainty-ledger.json').read_text()),record['research_log'])
        bundle=json.loads((directory/'outputs/builder-pack.json').read_text())
        self.assertEqual(bundle['report']['research_log'],record['research_log'])
        document=(directory/'outputs/report.md').read_text()
        self.assertNotIn('Historical investigation question 7',document)
        self.assertLess(document.index('Analysis / proposed design'),document.index('## Findings'))
        self.assertLess(document.index('Proposed requirements and acceptance'),document.index('## Findings'))
    def test_council_rejects_unknown_unbounded_or_empty_selection(self):
        for settings in [{'council_members':['invented']},{'council_members':['design']*5},
                         {'council_members':[],'council_auto_experts':False},
                         {'council_auto_experts':'yes'}]:
            with self.subTest(settings=settings),self.assertRaises(ValueError):
                brief({'question':'Investigate this integration','council':True,**settings})
        self.assertFalse(brief({'question':'Investigate this integration','council':False,
                                'council_members':[],'council_auto_experts':False})['council'])
    def test_public_url_rejects_private_and_non_https(self):
        for url in ['http://example.com','https://user:password@example.com','https://example.com:22']:
            with self.assertRaises(ProviderError):public_url(url)
        with patch('socket.getaddrinfo',return_value=[(socket.AF_INET,socket.SOCK_STREAM,6,'',('127.0.0.1',443))]):
            with self.assertRaises(ProviderError):public_url('https://localhost/')
    def test_html_scripts_are_evidence_not_executable_content(self):
        p=PlainText();p.feed('<h1>Policy</h1><script>stealSecrets()</script><p>Useful text</p>')
        self.assertNotIn('stealSecrets',''.join(p.parts));self.assertIn('Useful text',''.join(p.parts))
    def test_reviewer_cannot_approve_claim_that_requires_revision(self):
        class QualifiedModel(FakeModel):
            def call(self,role,instruction,data,search=False):
                result=super().call(role,instruction,data,search)
                if role=='Evidence reviewer':
                    for row in result['reviews']:row.update(requires_revision=True,reason='This needs a narrower scope.')
                return result
        store,rid,_=self.run_job(QualifiedModel())
        self.assertEqual(store.read(rid)['status'],'failed')
        self.assertFalse((store.directory(rid)/'report.json').exists())
    def test_overlap_is_retained_in_ledger_but_not_counted_twice(self):
        engine=ResearchEngine(None,model=FakeModel());engine.sources=[{'id':'S001','state':'available'}];engine.packets=[{'id':'S001','text':TEXT}]
        for text in ['Duplicate delivery is possible.','The provider can send duplicates.']:
            engine.ingest({'findings':[{'text':text,'label':'documented','sources':['S001'],'quote':'duplicate events','caveat':'Original evidence limit.'}]})
        for f in engine.findings:f['review']='supported'
        engine.consolidate([{'keep':'F001','duplicates':['F002'],'reason':'Same fact'}])
        self.assertEqual(len(engine.accepted()),1);self.assertEqual(len(engine.findings),2)
        self.assertEqual(engine.findings[1]['duplicate_of'],'F001')
    def test_coverage_cannot_claim_answered_with_invented_finding_ids(self):
        class InventedCoverage(FakeModel):
            def call(self,role,instruction,data,search=False):
                if role=='Research coverage lead':return {'criteria':[{'index':0,'status':'answered','finding_ids':['invented']}],'follow_up_queries':[]}
                return super().call(role,instruction,data,search)
        store,rid,_=self.run_job(InventedCoverage())
        self.assertEqual(store.read(rid)['status'],'partial')
        coverage=json.loads((store.directory(rid)/'coverage.json').read_text())
        self.assertEqual(coverage['criteria'][0]['status'],'unanswered')
    def test_relevant_tail_passages_are_not_dropped(self):
        text='Navigation and general introduction. '*1200+'\nPayout reconciliation requires balance transaction identifiers.\n'+'Footer text. '*400
        excerpt=source_passages(text,'payout reconciliation balance transaction',4000)
        self.assertIn('Payout reconciliation requires balance transaction identifiers.',excerpt)
        self.assertIn('Snapshot characters',excerpt);self.assertLessEqual(len(excerpt),4000)
    def test_follow_up_uses_goal_priority_instead_of_first_review_query(self):
        class CoverageModel(FakeModel):
            def __init__(self):super().__init__();self.search_queries=[]
            def call(self,role,instruction,data,search=False):
                if role=='Source scout':
                    self.search_queries.append(data['queries'])
                    return {'sources':[{'url':'https://example.com/'+str(len(self.search_queries)),'title':'Docs'}]}
                result=super().call(role,instruction,data,search)
                if role=='Evidence reviewer':result['follow_up_queries']=['minor payload dispute']
                if role=='Research coverage lead':
                    result['follow_up_queries']=['core settlement semantics'] if len(self.search_queries)==1 else []
                return result
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);store=RunStore(tmp.name)
        rid=store.create({'question':'What are the settlement semantics?','depth':'detailed','formats':['md'],'council':False})
        model=CoverageModel();ResearchEngine(store,model=model,web=FakeWeb()).execute(rid)
        self.assertEqual(model.search_queries[1],['core settlement semantics'])
        self.assertTrue((store.directory(rid)/'coverage-1.json').exists())
    def test_final_coverage_reads_the_finished_accepted_analysis(self):
        class FinalCoverage(FakeModel):
            def call(self,role,instruction,data,search=False):
                result=super().call(role,instruction,data,search)
                if role=='Research coverage lead' and not data['accepted_analysis']:
                    result['criteria'][0]['status']='partial'
                return result
        store,rid,_=self.run_job(FinalCoverage())
        self.assertEqual(store.read(rid)['status'],'completed')
        directory=store.directory(rid)
        self.assertEqual(json.loads((directory/'coverage-0.json').read_text())['criteria'][0]['status'],'partial')
        self.assertEqual(json.loads((directory/'coverage-final.json').read_text())['criteria'][0]['status'],'answered')
        self.assertFalse(any(g.startswith('Coverage partial:') for g in json.loads((directory/'report.json').read_text())['unknowns']))
    def test_known_unreadable_scout_candidates_do_not_displace_readable_sources(self):
        class ReadableScout(FakeModel):
            def call(self,role,instruction,data,search=False):
                if role=='Source scout':return {'sources':[{'url':'https://example.com/shell','access':'unavailable'},
                    {'url':'https://example.com/unknown','access':'unverified'},{'url':'https://example.com/static','access':'readable'}]}
                return super().call(role,instruction,data,search)
        store,rid,_=self.run_job(ReadableScout())
        sources=json.loads((store.directory(rid)/'sources.json').read_text())
        self.assertEqual(sources[0]['url'],'https://example.com/static')
        self.assertNotIn('https://example.com/shell',[s['url'] for s in sources])
    def test_curated_findings_preserve_original_reviewed_ledger(self):
        class CuratedModel(FakeModel):
            def call(self,role,instruction,data,search=False):
                result=super().call(role,instruction,data,search)
                if role=='Synthesis lead':result['finding_ids']=['F002']
                elif 'findings' in result:
                    result['findings'].append({'text':'A retry need not be a new operation.','label':'documented',
                        'sources':['S001'],'quote':'A retry does not establish a second business operation.','caveat':'Fixture only.'})
                return result
        store,rid,_=self.run_job(CuratedModel())
        directory=store.directory(rid);report=json.loads((directory/'report.json').read_text())
        self.assertEqual([f['text'] for f in report['findings']],['A retry need not be a new operation.'])
        claims=json.loads((directory/'claims.json').read_text());self.assertEqual(len(claims),2)
        self.assertEqual([f['published'] for f in claims],[False,True])
    def test_revision_uses_checked_parent_without_search_or_overwrite(self):
        store,parent,_=self.run_job()
        before=(store.directory(parent)/'report.json').read_bytes()
        request=json.loads((store.directory(parent)/'brief.json').read_text());rid=store.create(request)
        class MatrixModel(FakeModel):
            def call(self,role,instruction,data,search=False):
                if role=='Synthesis lead':
                    assert data['success_criteria'] and data['revision_feedback']
                result=super().call(role,instruction,data,search)
                if role=='Synthesis lead':result['tables']=[{'title':'Failure cases','columns':['Scenario','Owner','Acceptance'],
                    'rows':[['Duplicate','Operator','Replay causes one effect']]}]
                return result
        model=MatrixModel();ResearchEngine(store,model=model).refine(rid,parent,'Add an explicit failure matrix')
        self.assertEqual(store.read(rid)['status'],'completed',store.read(rid))
        self.assertEqual((store.directory(parent)/'report.json').read_bytes(),before)
        self.assertEqual([r for r,_ in model.roles],['Synthesis lead','Synthesis evidence reviewer','Research coverage lead'])
        report=json.loads((store.directory(rid)/'report.json').read_text());original=json.loads(before)
        self.assertEqual(report['sources'],original['sources'])
        self.assertIn('Proposed matrix / Failure cases',(store.directory(rid)/'outputs/report.md').read_text())
        self.assertTrue((store.directory(rid)/'evidence/S001.body').exists())
    def test_revision_rejects_tampered_parent_before_model_calls(self):
        store,parent,_=self.run_job();bundle=store.directory(parent)/'outputs/builder-pack.json'
        bundle.write_bytes(bundle.read_bytes()+b' ')
        rid=store.create(json.loads((store.directory(parent)/'brief.json').read_text()));model=FakeModel()
        ResearchEngine(store,model=model).refine(rid,parent,'Revise')
        self.assertEqual(store.read(rid)['status'],'failed');self.assertEqual(model.calls,0)
        self.assertIn('integrity mismatch',str(store.read(rid)['errors']))
    def test_revision_cannot_replay_an_unfinished_parent(self):
        store,parent,_=self.run_job();store.update(parent,status='running')
        rid=store.create(json.loads((store.directory(parent)/'brief.json').read_text()));model=FakeModel()
        ResearchEngine(store,model=model).refine(rid,parent,'Revise')
        self.assertEqual(store.read(rid)['status'],'failed');self.assertEqual(model.calls,0)
        self.assertEqual(store.read(parent)['status'],'running')
    def test_malformed_matrix_cannot_be_published(self):
        class BadTable(FakeModel):
            def call(self,role,instruction,data,search=False):
                result=super().call(role,instruction,data,search)
                if role=='Synthesis lead':result['tables']=[{'title':'Bad','columns':['A','B'],'rows':[['Only one']]}]
                return result
        store,rid,_=self.run_job(BadTable())
        self.assertEqual(store.read(rid)['status'],'failed')
        self.assertFalse((store.directory(rid)/'report.json').exists())
        self.assertTrue((store.directory(rid)/'synthesis.json').exists())

if __name__=='__main__':unittest.main()
