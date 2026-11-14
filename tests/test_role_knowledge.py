"""Role artifacts carry bounded native-shelf excerpts, not another database."""
import hashlib
import io
import json
import unittest
import zipfile

import test_role_plugins
from tmf_research.canon import CanonConnection
from tmf_research.role_plugins import build_role_plugin


class NativeRoleKnowledgeTests(unittest.TestCase):
    setUp = test_role_plugins.RolePluginTests.setUp
    publish = test_role_plugins.RolePluginTests.publish
    profession = test_role_plugins.RolePluginTests.profession

    def test_role_package_includes_selected_native_knowledge_with_exact_provenance(self):
        self.profession();published=self.publish()
        native={'status':'complete','sources':[{
            'doc_id':'kn-0123456789ab','content_hash':'a'*64,'title':'Synthetic plugin workflow',
            'source_kind':'folder','updated_at':'2026-01-01T00:00:00Z',
            'lane':'shared','source_currentness':{'state':'current'},
            'purpose':'Install and verify a plugin',
            'chunks':[{'index':2,'id':'kn-0123456789ab@'+'a'*64+'#2','content_hash':hashlib.sha256(b'Use the normal plugin installation path.').hexdigest(),'text':'Use the normal plugin installation path.',
                       'headings':['Installation'],'start':0,'end':40}]}], 'gaps':[]}
        data,receipt=build_role_plugin(CanonConnection(self.fixture.config),published['role_plugin']['source'],
                                       self.rid,native_knowledge=native)
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            selection=json.loads(archive.read('knowledge/selection.json'))
            role=json.loads(archive.read('role.json'));manifest=json.loads(archive.read('tmf-plugin.json'))
            skill=archive.read('skills/'+manifest['id']+'/SKILL.md').decode()
            body=archive.read('knowledge/role-knowledge.md').decode()
        self.assertEqual(selection,native)
        self.assertIn('Use the normal plugin installation path.',body)
        self.assertIn('kn-0123456789ab',body)
        self.assertIn('knowledge/role-knowledge.md',skill)
        self.assertEqual(role['provenance']['native_knowledge'][0]['content_hash'],'a'*64)
        self.assertEqual(manifest['audience'],'both')
        self.assertFalse(role['definition']['grants_authority'])
        self.assertIn('read_knowledge',role['definition']['required_capabilities'])
        self.assertEqual(receipt['native_knowledge']['sources'],1)
        with zipfile.ZipFile(io.BytesIO(data)) as package:
            cards=[name for name in package.namelist() if name.startswith('skills/') and name.endswith('/SKILL.md')]
            self.assertEqual(len(cards),2)
            selected_card=next(name for name in cards if '-knowledge-kn-' in name)
            self.assertIn('Use the normal plugin installation path.',package.read(selected_card).decode())
            self.assertIn('read_skill',skill)


    def test_selection_resolves_pinned_chunk_pages_and_reports_missing_or_stale(self):
        import hashlib
        from tmf_research.role_knowledge import collect_role_knowledge
        content='Use the normal plugin installation path.'
        pin={'doc_id':'kn-0123456789ab','content_hash':'a'*64,'chunk_indexes':[0],
             'purpose':'Install plugins using the documented interface'}
        calls=[]
        def read(args):
            calls.append(args)
            offset=args.get('offset',0);text=content[offset:offset+16]
            return {'doc_id':pin['doc_id'],'content_hash':pin['content_hash'],'title':'Synthetic plugin guide',
                'source_kind':'pack','lane':'shared','actor':None,'updated_at':'2026-01-01T00:00:00Z',
                'source_currentness':{'state':'current'},'text':text,'offset':offset,
                'next_offset':offset+len(text) if offset+len(text)<len(content) else None,'chars':len(content),
                'chunk_refs':[{'id':pin['doc_id']+'@'+pin['content_hash']+'#0','index':0,
                    'content_hash':hashlib.sha256(content.encode()).hexdigest(),'headings':['Installation'],
                    'start':offset,'end':offset+len(text)}]}
        result=collect_role_knowledge([pin],read)
        self.assertEqual(result['status'],'complete')
        self.assertEqual(result['sources'][0]['chunks'][0]['text'],content)
        self.assertTrue(all(c['expected_hash']==pin['content_hash'] for c in calls))
        self.assertEqual([c['offset'] for c in calls],[0,16,32])
        def changed(args):return {**read(args),'source_currentness':{'state':'changed'}}
        unavailable=collect_role_knowledge([pin],changed)
        self.assertEqual(unavailable['sources'],[])
        self.assertEqual(unavailable['gaps'][0]['reason'],'changed')
        self.assertEqual(unavailable['gaps'][0]['research_query'],pin['purpose'])

    def test_builder_only_material_cannot_be_broadened_or_private_material_packaged(self):
        import copy
        from tmf_research.role_knowledge import package_knowledge
        source={'doc_id':'kn-0123456789ab','content_hash':'a'*64,'title':'Synthetic guide',
            'source_kind':'pack','updated_at':'2026-01-01T00:00:00Z','lane':'builder',
            'source_currentness':{'state':'current'},'purpose':'Build a plugin',
            'chunks':[{'index':0,'id':'kn-0123456789ab@'+'a'*64+'#0',
                       'content_hash':hashlib.sha256(b'Procedure').hexdigest(),
                       'text':'Procedure','start':0,'end':9,'headings':['Procedure']}]}
        selected={'status':'complete','sources':[source],'gaps':[]}
        self.assertEqual(package_knowledge(selected)[2],'builders')
        private=copy.deepcopy(selected);private['sources'][0]['actor']='worker-private'
        with self.assertRaisesRegex(ValueError,'private'):package_knowledge(private)
        shared=copy.deepcopy(selected);shared['sources'][0].update(actor='source-author',lane='shared',source_currentness={'state':'indexed_only'})
        self.assertEqual(package_knowledge(shared)[2],'both')
        self.assertEqual(package_knowledge(shared)[1][0]['author'],'source-author')
        mixed=copy.deepcopy(selected);agent=copy.deepcopy(source);agent.update(lane='agent',doc_id='kn-123456789abc')
        mixed['sources'].append(agent)
        with self.assertRaisesRegex(ValueError,'combine'):package_knowledge(mixed)

    def test_utf16_pages_preserve_non_bmp_text_and_detect_corrupt_chunk(self):
        from tmf_research.role_knowledge import collect_role_knowledge
        content='A 🧪 source-backed procedure.';raw=content.encode('utf-16-le')
        selected={'doc_id':'kn-0123456789ab','content_hash':'a'*64,'chunk_indexes':[0],'purpose':'Test safe source paging'}
        def read(args):
            offset=args['offset'];part=raw[offset*2:(offset+3)*2];end=offset+len(part)//2
            return {'doc_id':selected['doc_id'],'content_hash':selected['content_hash'],'title':'Unicode procedure',
                'source_kind':'actor','actor':'author','lane':'shared','updated_at':'2026-01-01T00:00:00Z',
                'source_currentness':{'state':'indexed_only'},'offset':offset,'text':part.decode('utf-16-le','surrogatepass'),
                'next_offset':end if end<len(raw)//2 else None,'chars':len(raw)//2,
                'chunk_refs':[{'id':selected['doc_id']+'@'+selected['content_hash']+'#0','index':0,
                    'content_hash':hashlib.sha256(content.encode()).hexdigest(),'start':offset,'end':end,'headings':[]}]}
        result=collect_role_knowledge([selected],read)
        self.assertEqual(result['sources'][0]['chunks'][0]['text'],content)
        def corrupt(args):
            page=read(args);page['chunk_refs'][0]['content_hash']='b'*64;return page
        result=collect_role_knowledge([selected],corrupt)
        self.assertEqual(result['sources'],[])
        self.assertEqual(result['gaps'][0]['reason'],'incomplete_chunk')

    def test_selection_rejects_unpinned_and_command_or_actor_configuration(self):
        from tmf_research.missions import normalize
        good={'doc_id':'kn-0123456789ab','content_hash':'a'*64,'chunk_indexes':[0],'purpose':'Install plugins'}
        mission={'schema':'tmf-research-mission/1','type':'profession','target':'Plugin specialist','role_knowledge':[good]}
        self.assertEqual(normalize(mission)['role_knowledge'],[good])
        for bad in ({**good,'actor':'other-worker'},{**good,'command':['execute']},{**good,'content_hash':''},
                    {**good,'chunk_indexes':[0,0]}):
            with self.subTest(bad=bad),self.assertRaises(ValueError):normalize({**mission,'role_knowledge':[bad]})
        with self.assertRaises(ValueError):normalize({**mission,'type':'company'})

    def test_profession_consumes_native_knowledge_then_exports_selected_material_and_hashes(self):
        from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
        import os,threading
        from unittest.mock import patch
        from urllib.parse import urlsplit,parse_qs
        from tmf_research.engine import ResearchEngine
        from test_missions import MissionModel
        from test_engine import FakeWeb
        content='The system can deliver duplicate events.\nUse the normal plugin installation path.'
        selected={'doc_id':'kn-0123456789ab','content_hash':'a'*64,'chunk_indexes':[0],
                  'purpose':'Evaluate documented plugin installation and event handling'}
        calls=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                query=parse_qs(urlsplit(self.path).query);calls.append(query)
                if self.headers.get('Authorization')!='Bearer fixture-only':self.send_response(403);self.end_headers();return
                page={'status':'ok','doc_id':selected['doc_id'],'content_hash':selected['content_hash'],
                    'title':'Synthetic plugin workflow','lane':'builder','actor':None,'source_kind':'pack',
                    'updated_at':'2026-01-01T00:00:00Z','source_currentness':{'state':'current'},'text':content,
                    'offset':0,'next_offset':None,'chars':len(content),'chunk_refs':[{
                        'id':selected['doc_id']+'@'+selected['content_hash']+'#0','index':0,
                        'content_hash':hashlib.sha256(content.encode()).hexdigest(),'start':0,'end':len(content),'headings':['Procedure']}]}
                data=json.dumps(page).encode();self.send_response(200);self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
        http=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
        def close():http.shutdown();thread.join(2);http.server_close()
        self.addCleanup(close)
        config={**self.fixture.config,'native_knowledge':{'url':f'http://127.0.0.1:{http.server_port}',
                                                        'actor':'bound-builder','token_env':'ROLE_TEST_AUTH'}}
        with patch.dict(os.environ,{'ROLE_TEST_AUTH':'fixture-only'}):
            rid=self.store.create({'question':'What does documented plugin installation require?','depth':'quick','formats':['md','builder'],
                'council':False,'mission':{'schema':'tmf-research-mission/1','type':'profession','target':'Plugin specialist',
                                         'role_knowledge':[selected],'budgets':{'sources':1}}})
            model=MissionModel('profession');ResearchEngine(self.store,config,model=model,web=FakeWeb()).execute(rid)
        state=self.store.read(rid);self.assertIn(state['status'],('completed','partial'),state)
        sources=json.loads((self.store.directory(rid)/'sources.json').read_text())
        self.assertEqual(len(sources),1,'native evidence consumes the source budget')
        self.assertNotIn(('Source scout',True),model.roles,'a full native source budget must not start an external search')
        source=sources[0]
        self.assertEqual(source['kind'],'native-knowledge')
        self.assertEqual(source['native_knowledge']['content_hash'],selected['content_hash'])
        lead=next(data for role,data in model.inputs if role=='Research lead')
        self.assertIn('normal plugin installation',lead['evidence'][0]['text'])
        self.assertEqual(calls[0]['actor'],['bound-builder'])
        self.assertEqual(calls[0]['expected_hash'],[selected['content_hash']])
        from tmf_research.canon import publish_candidates
        receipt=publish_candidates(self.store,rid,config)
        self.assertEqual(receipt['role_plugin']['native_knowledge'],{'status':'complete','sources':1,'gaps':0},receipt)
        archive=self.store.directory(rid)/'outputs'/receipt['role_plugin']['file']
        with zipfile.ZipFile(archive) as package:
            self.assertIn('normal plugin installation',package.read('knowledge/role-knowledge.md').decode())
            self.assertEqual(json.loads(package.read('tmf-plugin.json'))['audience'],'builders')
        # Refinement retains the same captured knowledge without rereading native sources.
        child=self.store.create(json.loads((self.store.directory(rid)/'brief.json').read_text()))
        ResearchEngine(self.store,config,model=MissionModel('profession'),web=FakeWeb()).refine(child,rid,'Clarify the existing procedure without acquiring sources.')
        self.assertIn(self.store.read(child)['status'],('completed','partial'))
        child_receipt=publish_candidates(self.store,child,config)
        self.assertEqual(child_receipt['role_plugin']['native_knowledge']['sources'],1,child_receipt)
        self.assertEqual(len(calls),1,'revision must not reacquire native knowledge')
        # The captured selection is controller evidence, checked before packaging.
        path=self.store.directory(rid)/'evidence/role-knowledge.json';path.write_text('{}')
        damaged=publish_candidates(self.store,rid,config)
        self.assertEqual(damaged['status'],'published-candidate')
        self.assertEqual(damaged['role_plugin']['status'],'unavailable')

    def test_missing_native_connection_stays_partial_and_feeds_scoped_gathering_gaps(self):
        from tmf_research.engine import ResearchEngine
        from tmf_research.canon import publish_candidates
        from test_missions import MissionModel
        from test_engine import FakeWeb
        selected={'doc_id':'kn-0123456789ab','content_hash':'a'*64,'chunk_indexes':[0],
                  'purpose':'Find documented plugin installation procedures'}
        request={'question':'What does plugin installation require?','depth':'quick','formats':['md'],'council':False,
                 'mission':{'schema':'tmf-research-mission/1','type':'profession','target':'Plugin specialist',
                            'permitted_domains':['example.com'],'role_knowledge':[selected]}}
        rid=self.store.create(request);model=MissionModel('profession')
        ResearchEngine(self.store,self.fixture.config,model=model,web=FakeWeb()).execute(rid)
        self.assertEqual(self.store.read(rid)['status'],'partial')
        lead=next(data for role,data in model.inputs if role=='Research lead')
        self.assertIn('Find documented plugin installation procedures',lead['knowledge_gaps'][0])
        receipt=publish_candidates(self.store,rid,self.fixture.config)
        self.assertEqual(receipt['role_plugin']['native_knowledge'],{'status':'partial','sources':0,'gaps':1})
        with zipfile.ZipFile(self.store.directory(rid)/'outputs'/receipt['role_plugin']['file']) as package:
            selection=json.loads(package.read('knowledge/selection.json'))
            self.assertEqual(selection['sources'],[])
            self.assertEqual(selection['gaps'][0]['reason'],'connection_unavailable')
            self.assertIn('Missing or unavailable knowledge',package.read('knowledge/role-knowledge.md').decode())

    def test_long_unicode_native_passage_remains_readable_through_skill_body_budget(self):
        self.profession();published=self.publish()
        content='🧪 documented procedure. '*600
        native={'status':'complete','sources':[{'doc_id':'kn-0123456789ab','content_hash':'a'*64,
            'title':'Synthetic long procedure','source_kind':'actor','updated_at':'2026-01-01T00:00:00Z',
            'lane':'shared','actor':'author','source_currentness':{'state':'indexed_only'},'purpose':'Apply documented procedures',
            'chunks':[{'index':0,'id':'kn-0123456789ab@'+'a'*64+'#0','content_hash':hashlib.sha256(content.encode()).hexdigest(),
                       'start':0,'end':len(content.encode('utf-16-le'))//2,'text':content,'headings':[]}]}],'gaps':[]}
        data,_=build_role_plugin(CanonConnection(self.fixture.config),published['role_plugin']['source'],self.rid,native_knowledge=native)
        with zipfile.ZipFile(io.BytesIO(data)) as package:
            cards=[package.read(name) for name in package.namelist() if '/SKILL.md' in name and '-knowledge-kn-' in name]
            self.assertGreater(len(cards),1)
            self.assertTrue(all(len(body)<16000 for body in cards))
            self.assertEqual(''.join(body.decode().split('Selected for: Apply documented procedures\n\n',1)[1].removesuffix('\n') for body in cards),content)
