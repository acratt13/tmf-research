"""Observed execution metadata must reach factual review without becoming business claims."""
import json
import tempfile
import unittest
from tmf_research.engine import ResearchEngine, RunStore
from test_missions import MissionModel
from test_engine import FakeWeb

class AuditedMissionModel(MissionModel):
    def call(self,role,instruction,data,search=False):
        value=super().call(role,instruction,data,search)
        self.usage.append({'call':self.calls,'role':role,'web_search_calls':2 if search else 0,'usage':{}})
        return value

class ExecutionContextTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.store=RunStore(self.temp.name)
    def run_job(self,model=None):
        model=model or AuditedMissionModel('company')
        rid=self.store.create({'question':'Investigate the synthetic business evidence.','depth':'quick','formats':['md','builder'],'council':False,
            'mission':{'schema':'tmf-research-mission/1','type':'company','target':'Synthetic example','collection':'web','budgets':{'concurrency':1,'rounds':0,'calls':16}}})
        engine=ResearchEngine(self.store,model=model,web=FakeWeb());engine.execute(rid)
        return rid,model,engine
    def test_synthesis_coverage_and_output_review_receive_measured_provenance(self):
        rid,model,engine=self.run_job()
        for role in ('Research coverage lead','Synthesis lead','Synthesis evidence reviewer','Mission intelligence analyst','Mission output evidence reviewer'):
            data=next(data for name,data in model.inputs if name==role)
            receipt=data['execution_evidence']
            self.assertEqual(receipt['discovery']['native_web_search_calls_observed'],2)
            self.assertTrue(receipt['discovery']['provider_usage_complete'])
            self.assertEqual(receipt['sources'][0]['retrieved_at'],engine.sources[0]['retrieved_at'])
            self.assertEqual(receipt['analysis_concurrency'],1)
            self.assertLessEqual(receipt['model_calls_attempted_so_far'],receipt['model_call_limit'])
        review=next(data for role,data in model.inputs if role=='Mission output evidence reviewer')
        self.assertEqual(review['canon_continuity']['example.com']['status'],'unavailable')
        snapshots=[data['execution_evidence'] for role,data in model.inputs if role in ('Synthesis lead','Synthesis evidence reviewer','Mission intelligence analyst','Mission output evidence reviewer')]
        self.assertTrue(all(value==snapshots[0] for value in snapshots),'publish-stage receipt must be stable for exact call replay')
        saved=json.loads((self.store.directory(rid)/'outputs/builder-pack.json').read_text())
        self.assertEqual(saved['execution_evidence'],snapshots[0])
    def test_missing_provider_usage_is_unknown_not_zero_native_search(self):
        _,model,_=self.run_job(MissionModel('company'))
        data=next(data for role,data in model.inputs if role=='Synthesis lead')
        self.assertIsNone(data['execution_evidence']['discovery']['native_web_search_calls_observed'])
        self.assertFalse(data['execution_evidence']['discovery']['provider_usage_complete'])
    def test_retained_evidence_revision_keeps_original_search_receipt_without_new_search(self):
        rid,_,_=self.run_job();model=AuditedMissionModel('company')
        child=self.store.create(json.loads((self.store.directory(rid)/'brief.json').read_text()))
        ResearchEngine(self.store,model=model,web=FakeWeb()).refine(child,rid,'Clarify proposals and preserve the original observed provenance.')
        self.assertIn(self.store.read(child)['status'],('completed','partial'),self.store.read(child))
        self.assertFalse(any(search for _,search in model.roles))
        receipt=next(data for role,data in model.inputs if role=='Synthesis lead')['execution_evidence']
        self.assertEqual(receipt['origin']['run_id'],rid)
        self.assertEqual(receipt['origin']['discovery']['native_web_search_calls_observed'],2)
        self.assertEqual(receipt['discovery']['native_web_search_calls_observed'],None)
    def test_legacy_parent_provenance_is_read_without_recollecting_or_rewriting_parent(self):
        import hashlib
        rid,_,_=self.run_job();root=self.store.directory(rid)
        pack=root/'outputs/builder-pack.json';bundle=json.loads(pack.read_text());bundle.pop('execution_evidence')
        pack.write_text(json.dumps(bundle));receipt=root/'outputs/export-receipt.json';value=json.loads(receipt.read_text())
        for row in value['artifacts']:
            if row['file']=='builder-pack.json':row['sha256']=hashlib.sha256(pack.read_bytes()).hexdigest()
        receipt.write_text(json.dumps(value));original=pack.read_bytes()
        model=AuditedMissionModel('company');child=self.store.create(json.loads((root/'brief.json').read_text()))
        ResearchEngine(self.store,model=model,web=FakeWeb()).refine(child,rid,'Reconcile the retained discovery and source provenance.')
        self.assertIn(self.store.read(child)['status'],('completed','partial'),self.store.read(child))
        context=next(data for role,data in model.inputs if role=='Synthesis lead')['execution_evidence']
        self.assertEqual(context['origin']['discovery']['native_web_search_calls_observed'],2)
        self.assertIn('legacy',context['origin']['receipt_basis'])
        self.assertEqual(pack.read_bytes(),original)
        self.assertFalse(any(search for _,search in model.roles))
    def test_publish_receipt_preserves_exact_returned_call_replay(self):
        _,model,engine=self.run_job();saved=next(row for row in engine.role_calls if row['role']=='Synthesis lead')
        context=engine.execution_context('publication')
        model.usage.append({'role':'later call','web_search_calls':4})
        self.assertEqual(engine.execution_context('publication'),context)
        engine.replaying=True;before=model.calls
        task=saved['input']['instruction'].split(' Controller execution_evidence')[0]
        result=engine.call('Synthesis lead',task,saved['input']['data'])
        self.assertEqual(result,saved['output']);self.assertEqual(model.calls,before)
