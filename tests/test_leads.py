"""Lead qualification exercises the existing evidence, engine and export paths."""
import copy
import json
import tempfile
import unittest
from tmf_research.engine import ResearchEngine, RunStore
from tmf_research.missions import normalize, validate_output
from tmf_research.exports import business_lines
from test_missions import MissionModel, output
from test_engine import FakeWeb
from test_pre_build import FakeCrawlee

class LeadTests(unittest.TestCase):
    def setUp(self):
        self.mission=normalize({'schema':'tmf-research-mission/1','type':'leads','target':'Synthetic restaurant prospects',
            'industry':'Restaurants','geography':'Synthetic Harbor','collection':'web','budgets':{'sources':2,'concurrency':1,'rounds':0}})
        self.findings=[{'id':'F001','text':'Example describes its restaurant in Synthetic Harbor.','label':'documented','sources':['S001']},
                       {'id':'F002','text':'Example offers online reservation requests.','label':'documented','sources':['S001']}]
        self.sources=[{'id':'S001','url':'https://example.com/about','state':'available','retrieved_at':'2026-01-01T00:00:00Z'}]
    def row(self,host='example.com'):
        row=output('leads')['leads'][0];row.update(domain=host,industry='Restaurants',finding_ids=['F001','F002'])
        row['industry_evidence']={'text':'A restaurant.','label':'documented','finding_ids':['F001']}
        row['location']={'text':'In Synthetic Harbor.','label':'documented','finding_ids':['F001']}
        row['opportunity_basis']={'text':'Assess the documented reservation workflow; inefficiency is not established.','label':'inferred','finding_ids':['F002']}
        row['scope_fit']={key:{'status':'match','reason':'Official restaurant/location evidence matches the requested scope.','finding_ids':['F001']} for key in ('industry','geography')}
        return row
    def validate(self,rows):
        return validate_output(self.mission,{'leads':rows},self.findings,'a'*32,'2026-01-02T00:00:00Z',sources=self.sources)
    def test_source_supported_scope_is_not_verified_buying_intent(self):
        value=self.validate([self.row()]);lead=value['leads'][0]
        self.assertEqual(lead['qualification']['scope_status'],'supported')
        self.assertFalse(lead['qualification']['fit_verified'])
        self.assertEqual(lead['opportunity_basis']['label'],'inferred')
        self.assertEqual(value['lead_summary']['scope_supported'],1)
        self.assertEqual(lead['priority']['rank'],1)
    def test_requested_scope_or_inferred_location_cannot_establish_a_match(self):
        row=self.row();row['location']['label']='inferred'
        with self.assertRaisesRegex(ValueError,'scope.*factual'):self.validate([row])
        row=self.row();row['scope_fit']['geography']['finding_ids']=['invented']
        with self.assertRaises(ValueError):self.validate([row])
        row=self.row();del row['scope_fit']
        value=self.validate([row])['leads'][0]
        self.assertEqual(value['qualification']['scope_status'],'unresolved')
    def test_other_company_evidence_cannot_qualify_a_business(self):
        self.sources.append({'id':'S002','url':'https://different.test/about','state':'available'})
        self.findings.append({'id':'F003','text':'A different business is in Synthetic Harbor.','label':'documented','sources':['S002']})
        row=self.row();row['location']['finding_ids']=['F003'];row['scope_fit']['geography']['finding_ids']=['F003']
        with self.assertRaisesRegex(ValueError,'scope.*official'):self.validate([row])
    def test_opportunity_justification_cannot_be_promoted_to_fact(self):
        row=self.row();row['opportunity_basis']['label']='documented'
        with self.assertRaisesRegex(ValueError,'opportunity'):self.validate([row])
    def test_ranking_uses_scope_evidence_instead_of_model_confidence(self):
        known=self.row();known['confidence']='low'
        pending=self.row('pending.test');pending['confidence']='high';del pending['scope_fit']
        outside=self.row('outside.test');outside['scope_fit']['geography']['status']='mismatch'
        for number,host in enumerate(('pending.test','outside.test'),3):
            sid='S'+str(number).zfill(3);fid='F'+str(number).zfill(3)
            self.sources.append({'id':sid,'url':'https://'+host+'/about','state':'available'})
            self.findings.append({'id':fid,'text':'Synthetic business scope statement.','label':'documented','sources':[sid]})
            row=pending if host=='pending.test' else outside
            row['finding_ids']=[fid]
            for key in ('industry_evidence','location','opportunity_basis'):row[key]['finding_ids']=[fid]
            for fit in row.get('scope_fit',{}).values():fit['finding_ids']=[fid]
        value=self.validate([outside,pending,known]);self.assertEqual([x['domain'] for x in value['leads']],['example.com','pending.test','outside.test'])
        self.assertEqual([x['priority']['rank'] for x in value['leads']],[1,2,3])
        self.assertEqual(value['lead_summary']['outside_scope'],1)
        text='\n'.join(t for _,t in business_lines(value));self.assertIn('Research priority',text);self.assertIn('Scope fit',text)
        self.assertIn('not purchase likelihood',text)
    def test_no_matching_leads_has_an_explicit_retained_reason(self):
        value=validate_output(self.mission,{'leads':[],'limitations':['No retained business evidence supports the requested geographic market.']},self.findings,'a'*32,'2026-01-02T00:00:00Z',sources=self.sources)
        self.assertEqual(value['lead_summary']['scope_supported'],0);self.assertTrue(value['limitations'])
    def execute(self,collection='web',crawlee=None):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);store=RunStore(temp.name)
        class DiscoveryModel(MissionModel):
            def call(self,role,instruction,data,search=False):
                if role=='Source scout':return {'sources':[{'url':url,'access':'readable'} for url in
                    ('https://example.com/about','https://www.example.com/about#menu','https://example.com/pricing','https://second.test/about')]}
                return super().call(role,instruction,data,search)
        mission={**self.mission,'collection':collection};rid=store.create({'question':'Find synthetic restaurant prospects.', 'depth':'quick','formats':['md'],'council':False,'mission':mission})
        engine=ResearchEngine(store,model=DiscoveryModel('leads'),web=FakeWeb(),crawlee=crawlee);engine.execute(rid)
        return store,rid
    def test_small_source_budget_is_shared_between_businesses(self):
        store,rid=self.execute();sources=json.loads((store.directory(rid)/'sources.json').read_text())
        self.assertEqual([x['url'] for x in sources],['https://example.com/about','https://second.test/about'])
    def test_existing_crawler_page_budget_is_not_consumed_by_first_business(self):
        crawler=FakeCrawlee();self.execute('plugins',crawler)
        starts=[a for name,a in crawler.calls if name=='crawlee_start']
        self.assertEqual([x['allowed_domains'] for x in starts],[['example.com'],['second.test']])
        self.assertEqual([x['max_pages'] for x in starts],[1,1])
    def test_equivalent_business_rows_merge_distinct_source_citations(self):
        row=self.row();other=copy.deepcopy(row)
        self.sources.append({'id':'S003','url':'https://www.example.com/locations','state':'available','retrieved_at':'2026-01-02T00:00:00Z'})
        self.findings.append({**self.findings[0],'id':'F003','sources':['S003']})
        other['domain']='WWW.EXAMPLE.COM.';other['finding_ids']=['F003','F002']
        for key in ('industry_evidence','location'):other[key]['finding_ids']=['F003']
        for fit in other['scope_fit'].values():fit['finding_ids']=['F003']
        value=self.validate([row,other]);self.assertEqual(len(value['leads']),1)
        lead=value['leads'][0];self.assertEqual(lead['location']['finding_ids'],['F001','F003'])
        self.assertEqual(lead['scope_fit']['geography']['finding_ids'],['F001','F003'])
        self.assertEqual(set(lead['finding_ids']),{'F001','F002','F003'})
        self.assertEqual(len(lead['supporting_evidence']),3)
    def test_unrelated_or_inferred_opportunity_basis_is_not_actionable_evidence(self):
        self.sources.append({'id':'S002','url':'https://different.test/about','state':'available'})
        self.findings.append({'id':'F003','text':'A different business feature.','label':'documented','sources':['S002']})
        row=self.row();row['opportunity_basis']['finding_ids']=['F003']
        with self.assertRaisesRegex(ValueError,'opportunity basis.*official'):self.validate([row])
        self.findings[1]['label']='inferred';row=self.row()
        with self.assertRaisesRegex(ValueError,'opportunity basis.*factual'):self.validate([row])
    def test_omitted_requested_market_cannot_be_invented_by_the_model(self):
        self.mission.pop('geography')
        with self.assertRaisesRegex(ValueError,'explicit requested geography'):self.validate([self.row()])
    def test_empty_lead_output_remains_partial_with_visible_limitations(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);store=RunStore(temp.name)
        class NoMatches(MissionModel):
            def call(self,role,instruction,data,search=False):
                if role=='Mission intelligence analyst':return {'leads':[],'limitations':['No scoped business identities were retained.']}
                return super().call(role,instruction,data,search)
        rid=store.create({'question':'Find synthetic prospects.', 'depth':'quick','formats':['md','builder'],'council':False,'mission':self.mission})
        ResearchEngine(store,model=NoMatches('leads'),web=FakeWeb()).execute(rid)
        self.assertEqual(store.read(rid)['status'],'partial')
        value=json.loads((store.directory(rid)/'intelligence.json').read_text());self.assertEqual(value['leads'],[])
        self.assertIn('No scoped business identities were retained.',(store.directory(rid)/'outputs/report.md').read_text())
        self.assertTrue(any('No source-backed lead' in e for e in store.read(rid)['errors']))
    def test_later_collection_does_not_retrieve_a_retained_website_variant_again(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);store=RunStore(temp.name)
        rid=store.create({'question':'Find synthetic prospects.','mission':self.mission});engine=ResearchEngine(store,web=FakeWeb())
        engine.run_id=rid;engine.request=json.loads((store.directory(rid)/'brief.json').read_text())
        engine.sources=[{**self.sources[0],'url':'https://example.com/about'}]
        engine.fetch([{'url':'https://www.example.com/about#menu'},{'url':'https://second.test/about'}],2)
        self.assertEqual([s['url'] for s in engine.sources],['https://example.com/about','https://second.test/about'])
