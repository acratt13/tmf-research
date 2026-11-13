import copy
import json
import os
import tempfile
import unittest
from unittest.mock import patch
from tmf_research.engine import ResearchEngine, RunStore
from tmf_research.missions import normalize, validate_output
from tmf_research.canon import CanonConnection, publish_candidates
from test_canon import CanonFixture
from test_engine import FakeWeb
from test_missions import MissionModel, output

class BusinessTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.store=RunStore(self.tmp.name)
        self.fixture=CanonFixture();self.addCleanup(self.fixture.close)
        env=patch.dict(os.environ,{'RESEARCH_TEST_TOKEN':'fixture-only'});env.start();self.addCleanup(env.stop)
        self.findings=[{'id':'F001','text':'Synthetic company publishes its event documentation.','label':'documented','sources':['S001']}]
        self.sources=[{'id':'S001','url':'https://www.example.com/about','state':'available','retrieved_at':'2026-01-01T00:00:00Z'}]
    def mission(self,kind='company'):
        return normalize({'schema':'tmf-research-mission/1','type':kind,'target':'Synthetic company','collection':'web'})
    def validate(self,kind='company',raw=None):
        return validate_output(self.mission(kind),raw or output(kind),self.findings,'a'*32,'2026-01-02T00:00:00Z',sources=self.sources)
    def run_company(self,request_id):
        rid=self.store.create({'question':'What does the synthetic company evidence establish?','depth':'quick','formats':['md','builder'],'council':False,'mission':self.mission()},request_id=request_id)
        ResearchEngine(self.store,self.fixture.config,model=MissionModel('company'),web=FakeWeb()).execute(rid)
        self.assertIn(self.store.read(rid)['status'],('completed','partial'))
        return rid
    def publish(self,rid):
        result=publish_candidates(self.store,rid,self.fixture.config);self.assertEqual(result['status'],'published-candidate',result);return result
    def test_company_identity_requires_its_own_sourced_domain(self):
        raw=output('company');raw['companies'][0]['domain']='unrelated.test'
        with self.assertRaisesRegex(ValueError,'company domain'):self.validate(raw=raw)
    def test_website_host_variants_share_one_company_key_and_keep_evidence_dates(self):
        raw=output('company');raw['companies'][0]['domain']='WWW.EXAMPLE.COM.'
        value=self.validate(raw=raw)['companies'][0]
        self.assertEqual(value['domain'],'example.com')
        self.assertEqual(value['identity_evidence'][0]['source_id'],'S001')
        self.assertEqual(value['supporting_evidence'][0]['sources'][0]['retrieved_at'],'2026-01-01T00:00:00Z')
        self.assertFalse(value['identity_independently_verified'])
    def test_lead_source_facts_are_separate_from_opportunity_and_assumptions(self):
        row=self.validate('leads')['leads'][0]
        self.assertEqual(row['label'],'inferred');self.assertIsNone(row['last_verification'])
        self.assertEqual(row['supporting_evidence'][0]['text'],self.findings[0]['text'])
        self.assertEqual(row['supporting_evidence'][0]['label'],'documented')
        self.assertTrue(row['assumptions']);self.assertEqual(row['review_status'],'candidate')
        self.assertEqual(row['location']['label'],'unknown');self.assertEqual(row['industry_evidence']['label'],'unknown')
    def test_startup_output_has_explicit_unknown_funding_and_leadership(self):
        value=self.validate('startup')['companies'][0]
        self.assertIn('founders_and_leadership',value['startup_sections'])
        self.assertIn('funding',value['startup_sections'])
        self.assertEqual(value['startup_sections']['funding']['label'],'unknown')
    def test_repeat_company_investigation_reuses_identity_and_compares_prior_revision(self):
        first=self.run_company('company-one');published=self.publish(first)
        second=self.run_company('company-two');r=self.publish(second)
        identities=[e for e in self.fixture.entries.values() if json.loads(e['body'])['entity']=='company-identity']
        self.assertEqual(len(identities),1)
        intelligence=json.loads((self.store.directory(second)/'intelligence.json').read_text())
        prior=intelligence['companies'][0]['continuity']['previous']
        self.assertEqual(len(prior),1)
        first_ref=next(x for x in published['references'] if x['kind']=='company-investigation')
        self.assertEqual(prior[0]['reference'],{'id':first_ref['id'],'revision':first_ref['revision']})
        before=len(self.fixture.history);self.assertEqual(self.publish(second),r);self.assertEqual(len(self.fixture.history),before)
    def test_same_run_company_update_uses_revisions_and_retains_original_snapshot(self):
        rid=self.run_company('company-update');first=self.publish(rid)
        head=next(x for x in first['references'] if x['kind']=='company-investigation')
        path=self.store.directory(rid)/'intelligence.json';value=json.loads(path.read_text())
        value['companies'][0]['sections']['consulting_questions']['text']='A revised proposed question for client confirmation.'
        self.store.save(rid,'intelligence.json',value);second=self.publish(rid)
        changed=next(x for x in second['references'] if x['kind']=='company-investigation')
        self.assertEqual(changed['id'],head['id']);self.assertEqual(changed['revision'],head['revision']+1)
        self.assertEqual(CanonConnection(self.fixture.config).read(head['id'],1)['revision'],1)
        snapshots=[x for x in self.fixture.entries.values() if json.loads(x['body'])['entity']=='company-observation']
        self.assertEqual(len(snapshots),2)
    def test_reviewed_company_identity_and_investigation_are_not_overwritten(self):
        rid=self.run_company('company-reviewed');first=self.publish(rid)
        for ref in first['references']:
            if ref['kind'] in ('company-identity','company-investigation'):
                self.fixture.entries[ref['id']]['fields'].update(status='current',reviewStatus='approved')
        second=self.run_company('company-followup');self.publish(second)
        head=next(x for x in first['references'] if x['kind']=='company-investigation')
        self.assertEqual(self.fixture.entries[head['id']]['revision'],1)
        self.assertEqual(self.fixture.entries[head['id']]['fields']['reviewStatus'],'approved')

    def test_section_citations_are_retained_even_when_summary_cites_another_finding(self):
        self.findings.append({'id':'F002','text':'A second reviewed public claim.','label':'documented','sources':['S001']})
        raw=output('company');raw['companies'][0]['sections']['products_and_business_model']['finding_ids']=['F002']
        value=self.validate(raw=raw)['companies'][0]
        self.assertIn('F002',value['finding_ids'])
        self.assertIn('F002',[x['finding_id'] for x in value['supporting_evidence']])
    def test_recommendations_cannot_be_promoted_to_company_facts(self):
        raw=output('company');raw['companies'][0]['sections']['possible_services']['label']='documented'
        with self.assertRaisesRegex(ValueError,'recommendations'):self.validate(raw=raw)
    def test_domain_matching_rejects_parent_suffix_guess_and_inferred_identity(self):
        for host in ('com.example.com','co.uk','unrelated.test'):
            raw=output('company');raw['companies'][0]['domain']=host
            with self.subTest(host=host),self.assertRaisesRegex(ValueError,'company domain'):self.validate(raw=raw)
        self.findings[0]['label']='inferred'
        with self.assertRaisesRegex(ValueError,'company domain'):self.validate('leads')
    def test_missing_canon_is_visible_without_fabricating_continuity(self):
        rid=self.store.create({'question':'What does the synthetic evidence establish?','depth':'quick','formats':['md'],'council':False,'mission':self.mission()})
        ResearchEngine(self.store,model=MissionModel('company'),web=FakeWeb()).execute(rid)
        row=json.loads((self.store.directory(rid)/'intelligence.json').read_text())['companies'][0]
        self.assertEqual(row['continuity']['status'],'unavailable');self.assertEqual(row['continuity']['previous'],[])
    def test_legacy_www_identity_is_reused_and_ambiguous_pair_is_not_merged(self):
        from tmf_research.canon import digest
        connection=CanonConnection(self.fixture.config);prefix='tmf-research:v1:'+connection.scope+':'
        legacy=connection.put(prefix+'company:'+digest('www.example.com'),'Legacy company identity',
            {'entity':'company-identity','domain':'www.example.com','verification':'candidate'},[])
        self.fixture.entries[legacy['id']]['fields'].update(status='current',reviewStatus='approved')
        rid=self.run_company('legacy-company');receipt=self.publish(rid)
        ref=next(r for r in receipt['references'] if r['kind']=='company-identity')
        self.assertEqual(ref['id'],legacy['id']);self.assertEqual(self.fixture.entries[legacy['id']]['revision'],1)
        canonical=connection.put(prefix+'company:'+digest('example.com'),'A distinct existing identity',
            {'entity':'company-identity','domain':'example.com','verification':'candidate'},[])
        from tmf_research.canon import CanonUnavailable
        with self.assertRaisesRegex(CanonUnavailable,'Multiple existing'):connection.company_history('example.com')
        self.assertEqual(self.fixture.entries[legacy['id']]['revision'],1);self.assertEqual(self.fixture.entries[canonical['id']]['revision'],1)
    def test_same_run_reviewed_content_is_not_overwritten(self):
        rid=self.run_company('reviewed-company');first=self.publish(rid)
        ref=next(x for x in first['references'] if x['kind']=='company-investigation')
        entry=self.fixture.entries[ref['id']];before=copy.deepcopy(entry);entry['fields'].update(status='current',reviewStatus='approved')
        value=json.loads((self.store.directory(rid)/'intelligence.json').read_text());value['companies'][0]['sections']['overview']['text']='Changed research wording'
        self.store.save(rid,'intelligence.json',value)
        result=publish_candidates(self.store,rid,self.fixture.config)
        self.assertEqual(result['status'],'partial');self.assertEqual(entry['body'],before['body']);self.assertEqual(entry['revision'],1)
    def test_company_history_does_not_import_a_foreign_namespace_backlink(self):
        rid=self.run_company('history-owned');first=self.publish(rid)
        identity=next(x for x in first['references'] if x['kind']=='company-identity')
        foreign={**self.fixture.config,'canon':{**self.fixture.config['canon'],'identity_scope':'another-customer'}}
        conn=CanonConnection(foreign)
        conn.put('tmf-research:v1:another-customer:foreign','Private other customer observation',
            {'entity':'company-investigation','intelligence':{'domain':'example.com','research_date':'2099-01-01','name':'Private marker'}},[{'to':identity['id'],'kind':'related'}])
        history=CanonConnection(self.fixture.config).company_history('example.com')
        self.assertEqual(len(history['investigations']),1)
        self.assertNotIn('Private marker',json.dumps(history))

    def test_company_lookup_uses_existing_paged_knowledge_cli_without_new_records(self):
        import contextlib,io
        from test_canon import CandidateTests
        from tmf_research.cli import main
        rid=self.run_company('company-lookup');receipt=self.publish(rid)
        self.temp=self.tmp;base=CandidateTests.start_workbench(self)
        before=len(self.fixture.history)
        with patch.dict(os.environ,{'TMF_RESEARCH_URL':base}):
            args=['knowledge','--company','WWW.EXAMPLE.COM.'];chunks=[];cursor=None;digest=None
            for _ in range(100):
                stream=io.StringIO()
                with contextlib.redirect_stdout(stream):
                    code=main(args+(['--cursor',str(cursor),'--sha256',digest] if cursor is not None else []))
                self.assertEqual(code,0)
                page=json.loads(stream.getvalue());chunks.append(page['text']);cursor=page['next_cursor'];digest=page['sha256']
                if cursor is None:break
            else:self.fail('Bounded history did not finish paging')
            value=json.loads(''.join(chunks));identity=next(x for x in receipt['references'] if x['kind']=='company-identity')
            self.assertEqual(value['identity'],{'id':identity['id'],'revision':identity['revision']})
            self.assertEqual(len(value['investigations']),1)
            stream=io.StringIO()
            with contextlib.redirect_stdout(stream):self.assertEqual(main(['knowledge','--company','missing.test']),0)
            self.assertEqual(json.loads(json.loads(stream.getvalue())['text'])['status'],'not-found')
        self.assertEqual(len(self.fixture.history),before)

    def test_business_exports_include_sections_evidence_and_prior_revision_comparison(self):
        first=self.run_company('export-first');self.publish(first)
        second=self.run_company('export-second');root=self.store.directory(second)
        md=(root/'outputs/report.md').read_text()
        self.assertIn('Company consultation briefing',md);self.assertIn('products and business model',md)
        self.assertIn(r'\[PROPOSED\]',md);self.assertIn('Supporting reviewed findings',md)
        self.assertIn('Previous investigations and comparison',md);self.assertIn('revision 1',md)
        bundle=json.loads((root/'outputs/builder-pack.json').read_text())
        self.assertEqual(bundle['intelligence']['companies'][0]['domain'],'example.com')
        self.assertEqual(bundle['intelligence']['companies'][0]['continuity']['previous'][0]['reference']['revision'],1)


    def test_intelligence_writer_and_reviewer_receive_retained_official_source_register(self):
        rid=self.store.create({'question':'What does the company evidence establish?','depth':'quick','formats':['md'],'council':False,'mission':self.mission()})
        model=MissionModel('company');ResearchEngine(self.store,self.fixture.config,model=model,web=FakeWeb()).execute(rid)
        for role in ('Mission intelligence analyst','Mission output evidence reviewer'):
            data=next(data for name,data in model.inputs if name==role)
            self.assertEqual(data['source_register'][0]['url'],'https://example.com/docs')
            self.assertTrue(data['source_register'][0]['artifact_sha256'])

    def test_company_domain_normalization_is_idempotent_and_rejects_invalid_dns(self):
        from tmf_research.missions import company_domain
        for host in ('example.com','WWW.EXAMPLE.COM.','www.www.example.com','xn--bcher-kva.example'):
            value=company_domain(host);self.assertEqual(company_domain(value),value)
        for host in ('example..com','example.com..','-bad.example','good.example/path','user:secret@example.com'):
            with self.subTest(host=host),self.assertRaises(ValueError):company_domain(host)


    def test_requested_market_scope_does_not_become_company_location_evidence(self):
        mission=normalize({'schema':'tmf-research-mission/1','type':'leads','target':'Synthetic region','industry':'Synthetic operations','geography':'Synthetic northwest'})
        row=validate_output(mission,output('leads'),self.findings,'a'*32,'2026-01-02T00:00:00Z',sources=self.sources)['leads'][0]
        self.assertEqual(row['qualification']['geographic_scope'],'Synthetic northwest')
        self.assertEqual(row['location']['label'],'unknown');self.assertEqual(row['location']['finding_ids'],[])
        self.assertFalse(row['qualification']['fit_verified'])
