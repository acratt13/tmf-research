"""Bounded HTTP execution against synthetic Canon, never the live service."""
import copy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from tmf_research.canon import CanonConnection, CanonUnavailable, publish_candidates, publication_status, stable_id
from tmf_research.engine import RunStore


class CanonFixture:
    def __init__(self):
        self.entries = {}; self.history = []; self.fail_at = None; self.calls = 0
        self.guard = threading.Lock()
        self.blocked_call = None; self.entered = threading.Event(); self.release = threading.Event()
        fixture = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self):
                from urllib.parse import urlsplit,parse_qs
                path=urlsplit(self.path).path;identity=path.rsplit('/',1)[1]
                query=parse_qs(urlsplit(self.path).query)
                entry=fixture.entries.get(identity)
                if query.get('revision'):
                    entry=next((r for r in fixture.history if r['id']==identity and r['revision']==int(query['revision'][0])),None)
                if not entry:self.send_response(404);self.end_headers();return
                value=json.dumps({'entry':entry}).encode()
                self.send_response(200);self.send_header('Content-Length',str(len(value)));self.end_headers();self.wfile.write(value)
            def do_POST(self):
                with fixture.guard:
                    fixture.calls += 1
                    if fixture.calls == fixture.blocked_call:
                        fixture.entered.set(); fixture.release.wait(3)
                    status = 200
                    payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                    if self.path != '/api/canon/sections/knowledge/entries': status, value = 404, {}
                    elif self.headers.get('Authorization') != 'Bearer fixture-only': status, value = 401, {}
                    elif fixture.calls == fixture.fail_at: status, value = 503, {}
                    elif 'key' in payload:
                        identity = stable_id(payload['key'])
                        if identity in fixture.entries:
                            value = {**fixture.entries[identity], 'created': False}
                        else:
                            value = {k: payload[k] for k in ('title','body','fields','links','type')}
                            value.update(id=identity, revision=1)
                            fixture.entries[identity] = copy.deepcopy(value)
                            fixture.history.append(copy.deepcopy(value))
                            value = {**value, 'created': True}; status = 201
                    else:
                        prior = fixture.entries.get(payload['id'])
                        if not prior or prior['revision'] != payload['expectedRevision']: status, value = 409, {}
                        else:
                            value = {**prior, **{k: payload[k] for k in ('title','body','fields','links')}, 'revision':prior['revision']+1}
                            fixture.entries[value['id']] = copy.deepcopy(value)
                            fixture.history.append(copy.deepcopy(value))
                    data = json.dumps(value).encode()
                    self.send_response(status); self.send_header('Content-Length', str(len(data))); self.end_headers(); self.wfile.write(data)
        self.http = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True); self.thread.start()
        self.config = {'canon': {'url':f'http://127.0.0.1:{self.http.server_port}', 'identity_scope':'synthetic-workspace', 'token_env':'RESEARCH_TEST_TOKEN'}}
    def close(self):
        self.http.shutdown(); self.thread.join(2); self.http.server_close()


class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.store = RunStore(self.temp.name)
        self.fixture = CanonFixture(); self.addCleanup(self.fixture.close)
        self.env = patch.dict(os.environ, {'RESEARCH_TEST_TOKEN':'fixture-only'}); self.env.start(); self.addCleanup(self.env.stop)
        self.rid = self.store.create({'question':'What does the synthetic fixture establish?'},request_id='fixture-001')
        self.report = {'schema_version':1, 'title':'Synthetic fixture', 'question':'What does the synthetic fixture establish?',
                       'summary':'A bounded source-backed finding.', 'sources':[{'id':'S1', 'title':'Synthetic public source',
                       'url':'https://EXAMPLE.test:443/reference#section', 'state':'partial', 'retrieved_at':'2026-01-01T00:00:00Z',
                       'artifact_sha256':'a'*64, 'scope':'Synthetic passage only', 'limitations':'Incomplete synthetic source'}],
                       'findings':[{'label':'inferred','text':'The source suggests a bounded conclusion.', 'sources':['S1'],
                                    'caveat':'Partial evidence; inference only.'}], 'requirements':[], 'unknowns':['Independent verification absent.']}
        self.store.save(self.rid,'report.json',self.report)
        self.store.save(self.rid,'claims.json',[{**self.report['findings'][0], 'quote':'Synthetic passage', 'review':'supported', 'review_reason':'Bounded fixture check'}])
        self.store.update(self.rid,status='partial',outputs=['report.md'])

    def publish(self): return publish_candidates(self.store,self.rid,self.fixture.config)

    def test_http_publication_retains_evidence_and_repeat_has_no_effects(self):
        receipt = self.publish()
        self.assertEqual(receipt['status'],'published-candidate')
        self.assertEqual(receipt['research_status'],'partial')
        mission = self.fixture.entries[receipt['mission']['id']]
        payload = json.loads(mission['body'])
        self.assertEqual(payload['report'],self.report)
        self.assertEqual(payload['output_references'],[{'run_id':self.rid,'name':'report.md'}])
        finding = next(e for e in self.fixture.entries.values() if json.loads(e['body'])['entity']=='finding')
        content = json.loads(finding['body'])
        self.assertEqual(content['finding']['label'],'inferred')
        self.assertEqual(content['retained_reviews'][0]['quote'],'Synthetic passage')
        self.assertFalse(content['independent_verification'])
        source_ref = content['source_revisions'][0]
        source = self.fixture.entries[source_ref['id']]
        self.assertEqual(source_ref['revision'],source['revision'])
        self.assertEqual(json.loads(source['body'])['evidence'],self.report['sources'][0])
        self.assertEqual(finding['links'],[{'to':source['id'],'kind':'supported-by'}])
        before = copy.deepcopy(self.fixture.history)
        self.assertEqual(self.publish(),receipt)
        self.assertEqual(self.fixture.history,before)
        for entry in self.fixture.entries.values():
            self.assertEqual(entry['fields']['status'],'draft')
            self.assertEqual(entry['fields']['reviewStatus'],'candidate')
            self.assertNotIn('fixture-only',json.dumps(entry))

    def test_changed_report_uses_mission_revision_and_preserves_snapshots(self):
        first = self.publish(); count = len(self.fixture.history)
        self.report['summary'] = 'Updated bounded conclusion.'
        self.store.save(self.rid,'report.json',self.report)
        second = self.publish()
        self.assertEqual(second['mission']['id'],first['mission']['id'])
        self.assertEqual(second['mission']['revision'],2)
        self.assertNotEqual(second['snapshot']['id'],first['snapshot']['id'])
        self.assertIn(first['snapshot']['id'],self.fixture.entries)
        self.assertEqual(len(self.fixture.history),count+2)

    def test_same_source_new_mission_reuses_identity_retains_observations(self):
        first = self.publish()
        identities = {e['id'] for e in self.fixture.entries.values() if json.loads(e['body'])['entity']=='source-identity'}
        rid = self.store.create({'question':'A second synthetic investigation'})
        self.report['sources'][0]['url']='https://example.test/reference'
        self.report['sources'][0]['retrieved_at']='2026-01-02T00:00:00Z'
        self.store.save(rid,'report.json',self.report);self.store.update(rid,status='completed')
        second = publish_candidates(self.store,rid,self.fixture.config)
        self.assertEqual(second['status'],'published-candidate')
        self.assertEqual(identities,{e['id'] for e in self.fixture.entries.values() if json.loads(e['body'])['entity']=='source-identity'})
        old_source = next(r['id'] for r in first['references'] if r['kind']=='source')
        new_source = next(r['id'] for r in second['references'] if r['kind']=='source')
        self.assertNotEqual(old_source,new_source)

    def test_unavailable_partial_and_lost_response_retry(self):
        self.assertEqual(publication_status(self.store,self.rid,{} )['status'],'unavailable')
        self.assertEqual(publish_candidates(self.store,self.rid,{})['status'],'unavailable')
        self.fixture.fail_at=4
        partial=self.publish();self.assertEqual(partial['status'],'partial')
        self.assertNotIn('mission',partial)
        retained = set(self.fixture.entries)
        final=self.publish();self.assertEqual(final['status'],'published-candidate')
        self.assertTrue(retained.issubset(self.fixture.entries))
        # Retry after a lost response/receipt resolves keyed remote records, not a local ledger.
        (self.store.directory(self.rid)/'canon-publication.json').unlink()
        count=len(self.fixture.history)
        self.assertEqual(self.publish(),final);self.assertEqual(len(self.fixture.history),count)

    def test_reviewed_or_human_changed_candidate_is_not_overwritten(self):
        first=self.publish();mission=self.fixture.entries[first['mission']['id']]
        mission['fields']['reviewStatus']='approved'
        self.report['summary']='Changed research'
        self.store.save(self.rid,'report.json',self.report)
        self.assertEqual(self.publish()['status'],'partial')
        self.assertEqual(mission['revision'],1)
        mission['fields']['reviewStatus']='candidate';mission['body']='Human draft'
        self.assertEqual(self.publish()['status'],'partial')
        self.assertEqual(mission['body'],'Human draft')

    def test_missing_citations_rejected_before_remote_effects(self):
        self.report['findings'][0]['sources']=['absent']
        self.store.save(self.rid,'report.json',self.report)
        with self.assertRaises(ValueError):self.publish()
        self.assertEqual(self.fixture.calls,0)

    def test_connection_never_uses_research_selected_urls_or_redirects(self):
        for url in ('https://example.test','http://127.0.0.1:4325/path','http://user:pass@127.0.0.1:4325','http://127.0.0.1:4325#fragment'):
            with self.assertRaises(CanonUnavailable):CanonConnection({'canon':{**self.fixture.config['canon'],'url':url}})

    def test_cancellation_retains_partial_effects_and_safe_retry(self):
        calls=0
        def check():
            nonlocal calls
            calls+=1
            if calls==2:raise InterruptedError()
        result=publish_candidates(self.store,self.rid,self.fixture.config,check)
        self.assertEqual(result['status'],'partial')
        self.assertEqual(self.publish()['status'],'published-candidate')
        self.assertEqual(self.store.read(self.rid)['status'],'partial')

    def start_workbench(self, configured=True):
        import select
        import subprocess
        import sys
        config_path = Path(self.temp.name)/'config.json'
        config_path.write_text(json.dumps(self.fixture.config if configured else {}))
        process = subprocess.Popen([sys.executable,'-c',
                                    'import sys,json;from tmf_research.server import serve;serve(sys.argv[1],json.load(open(sys.argv[2])),0)',
                                    self.temp.name,str(config_path)], stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,text=True)
        def stop():
            process.terminate()
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired: process.kill();process.wait(timeout=3)
            process.stdout.close();process.stderr.close()
        self.addCleanup(stop)
        ready,_,_=select.select([process.stdout],[],[],5)
        self.assertTrue(ready,'Local workbench did not start')
        line=process.stdout.readline().strip()
        self.assertTrue(line, 'Workbench exited: '+process.stderr.read() if process.poll() is not None else 'Workbench returned no startup URL')
        return line.split()[-1]

    def test_workbench_http_and_original_result_cli_expose_publication(self):
        import contextlib
        import io
        import time
        from tmf_research.client import Workbench
        from tmf_research.cli import main
        base=self.start_workbench()
        with patch.dict(os.environ, {'TMF_RESEARCH_URL':base}):
            wb=Workbench()
            self.assertEqual(wb.request('/api/result/'+self.rid)['canon']['status'],'not-published')
            response=wb.request('/api/canon/publish',{'id':self.rid})
            self.assertEqual(response['status'],'publishing-candidates')
            for _ in range(100):
                state=wb.request('/api/runs/'+self.rid)
                if not state.get('canon_activity'):break
                time.sleep(.02)
            self.assertIsNone(state['canon_activity'])
            self.assertEqual(state['status'],'partial')
            result=wb.request('/api/result/'+self.rid)
            self.assertEqual(result['canon']['status'],'published-candidate')
            chunks=[];cursor=0;sha=None
            while True:
                out=io.StringIO()
                args=['result','--id',self.rid,'--cursor',str(cursor)]+(['--sha256',sha] if sha else [])
                with contextlib.redirect_stdout(out): self.assertEqual(main(args),0)
                page=json.loads(out.getvalue());chunks.append(page['text']);sha=page['sha256']
                if page['next_cursor'] is None:break
                cursor=page['next_cursor']
            whole=json.loads(''.join(chunks))
            self.assertEqual(whole['result']['canon']['mission'],result['canon']['mission'])
            self.assertEqual(whole['result']['report'],self.report)
            self.assertEqual(len(list(self.store.root.glob('*/state.json'))),1)

    def test_restart_clears_publication_activity_without_restarting_research(self):
        from tmf_research.canon import recover_publications
        self.store.update(self.rid,canon_activity='publishing')
        recover_publications(self.store)
        self.assertIsNone(self.store.read(self.rid)['canon_activity'])
        self.assertEqual(self.store.read(self.rid)['status'],'partial')
        self.assertEqual(publication_status(self.store,self.rid,self.fixture.config)['status'],'interrupted')
        self.assertEqual(self.fixture.calls,0)
        final=self.publish()
        self.store.update(self.rid,canon_activity='publishing')
        recover_publications(self.store)
        self.assertEqual(publication_status(self.store,self.rid,self.fixture.config),final)

    def test_revision_conflict_is_partial_and_keeps_original_mission(self):
        first=self.publish()
        self.report['summary']='A later report revision'
        self.store.save(self.rid,'report.json',self.report)
        original=CanonConnection.request
        def conflict(connection,path,payload=None):
            if payload and payload.get('id')==first['mission']['id']:
                raise CanonUnavailable('Canon refused publication (HTTP 409)')
            return original(connection,path,payload)
        with patch.object(CanonConnection,'request',conflict):
            self.assertEqual(self.publish()['status'],'partial')
        self.assertEqual(self.fixture.entries[first['mission']['id']]['revision'],1)
        self.assertEqual(self.publish()['mission']['revision'],2)

    def test_http_publication_busy_and_cancel_do_not_change_research_status(self):
        import time
        from tmf_research.client import Workbench, WorkbenchError
        base=self.start_workbench()
        self.fixture.blocked_call=1
        with patch.dict(os.environ,{'TMF_RESEARCH_URL':base}):
            wb=Workbench()
            wb.request('/api/canon/publish',{'id':self.rid})
            self.assertTrue(self.fixture.entered.wait(2))
            try:
                with self.assertRaises(WorkbenchError) as caught:
                    wb.request('/api/canon/publish',{'id':self.rid})
                self.assertEqual(caught.exception.status,409)
                self.assertEqual(wb.request('/api/cancel',{'id':self.rid})['status'],'cancelling-publication')
            finally:self.fixture.release.set()
            for _ in range(100):
                state=wb.request('/api/runs/'+self.rid)
                if not state.get('canon_activity'):break
                time.sleep(.02)
            self.assertEqual(state['status'],'partial')
            self.assertIsNone(state.get('canon_activity'))
            receipt=wb.request('/api/result/'+self.rid)['canon']
            self.assertEqual(receipt['status'],'partial')
            self.assertNotIn('mission',receipt)
            self.assertEqual(len(list(self.store.root.glob('*/state.json'))),1)

    def test_reviewed_unchanged_source_can_be_reused_without_demotion(self):
        self.publish()
        identities=[e for e in self.fixture.entries.values() if json.loads(e['body'])['entity']=='source-identity']
        identities[0]['fields'].update(status='current',reviewStatus='approved')
        rows=len(self.fixture.history)
        self.assertEqual(self.publish()['status'],'published-candidate')
        self.assertEqual(identities[0]['fields']['reviewStatus'],'approved')
        self.assertEqual(identities[0]['fields']['status'],'current')
        self.assertEqual(len(self.fixture.history),rows)

    def test_professional_publication_keeps_one_collection_and_shared_revision_refs(self):
        from tmf_research.missions import normalize, validate_output
        from test_missions import output
        self.report['findings'][0]['id']='F001'
        mission=normalize({'schema':'tmf-research-mission/1','type':'profession','target':'Synthetic operations'})
        raw=output('profession');raw['knowledge']['domains'][0]['label']='inferred'
        intelligence=validate_output(mission,raw,self.report['findings'],self.rid,'2026-01-01T00:00:00Z')
        intelligence['verification']='model-reviewed'
        self.store.save(self.rid,'report.json',self.report);self.store.save(self.rid,'intelligence.json',intelligence)
        first=self.publish();self.assertEqual(first['status'],'published-candidate',first)
        collections=[e for e in self.fixture.entries.values() if json.loads(e['body'])['entity']=='knowledge-collection']
        self.assertEqual(len(collections),1)
        roles=[e for e in self.fixture.entries.values() if json.loads(e['body'])['entity']=='specialty-definition']
        self.assertEqual(len(roles),1)
        definition=json.loads(roles[0]['body'])['definition']
        reference=definition['knowledge_references'][0]
        self.assertEqual(reference,{'id':collections[0]['id'],'revision':collections[0]['revision']})
        self.assertFalse(definition['grants_authority'])
        before=len(self.fixture.history)
        # Two callers retrieve the very same authoritative revision, without copying knowledge.
        for _ in range(2):
            entry=CanonConnection(self.fixture.config).read(reference['id'],reference['revision'])
            self.assertEqual(entry['id'],reference['id'])
        self.assertEqual(len(self.fixture.history),before)
        self.assertEqual(self.publish(),first)
        self.assertEqual(len(self.fixture.history),before)
        knowledge=[e for e in self.fixture.entries.values() if json.loads(e['body'])['entity']=='professional-knowledge']
        self.assertEqual(knowledge[0]['fields']['profession'],'Synthetic operations')

    def test_knowledge_reads_refuse_other_namespaces_and_stale_or_unknown_revisions(self):
        publication=self.publish();identity=publication['mission']['id']
        other={**self.fixture.config,'canon':{**self.fixture.config['canon'],'identity_scope':'another-workspace'}}
        with self.assertRaises(CanonUnavailable):CanonConnection(other).read(identity)
        with self.assertRaises(CanonUnavailable):CanonConnection(self.fixture.config).read(identity,99)
        self.assertEqual(CanonConnection(self.fixture.config).read(identity,1)['revision'],1)

    def test_local_system_mode_is_explicit_and_never_a_bearer_auth_fallback(self):
        from tmf_research.canon import operator_config
        configured={'canon':{'url':'http://127.0.0.1:4325','identity_scope':'synthetic-system','auth':'local-system','author':'synthetic-research'}}
        connection=CanonConnection(configured)
        self.assertEqual(connection.headers,{'X-Canon-Actor':'synthetic-research'})
        self.assertIsNone(connection.token)
        for settings in ({**configured['canon'],'url':'http://outside.example:4325'},
                         {**configured['canon'],'author':'untrusted/name'},
                         {**configured['canon'],'auth':'unknown'}):
            with self.assertRaises(CanonUnavailable):CanonConnection({'canon':settings})
        bearer={**configured['canon'],'auth':'bearer','token_env':'NO_SYNTHETIC_TOKEN_CONFIGURED'}
        with self.assertRaises(CanonUnavailable):CanonConnection({'canon':bearer})
        result=operator_config({}, {'TMF_RESEARCH_CANON_URL':'http://127.0.0.1:4325','TMF_RESEARCH_CANON_SCOPE':'synthetic-system','TMF_RESEARCH_CANON_AUTH':'local-system'})
        self.assertEqual(result['canon']['identity_scope'],'synthetic-system')
        self.assertEqual(result['canon']['auth'],'local-system')
        self.assertEqual(operator_config(configured,{'TMF_RESEARCH_CANON_URL':'http://127.0.0.1:9999'}),configured)
