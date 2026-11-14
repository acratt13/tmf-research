"""Research-to-role packages use published Canon revisions and normal MC skills."""
import io
import json
import os
import shutil
import zipfile
import unittest
import test_canon
from tmf_research.missions import normalize, validate_output
from test_missions import output

class RolePluginTests(unittest.TestCase):
    setUp = test_canon.CandidateTests.setUp
    publish = test_canon.CandidateTests.publish
    def profession(self):
        self.report['findings'][0]['id']='F001'
        mission=normalize({'schema':'tmf-research-mission/1','type':'profession','target':'Synthetic operations'})
        raw=output('profession');raw['knowledge']['domains'][0]['label']='inferred'
        value=validate_output(mission,raw,self.report['findings'],self.rid,'2026-01-01T00:00:00Z')
        value['verification']='model-reviewed'
        self.store.save(self.rid,'report.json',self.report);self.store.save(self.rid,'intelligence.json',value)

    def test_publishing_professional_knowledge_exposes_a_reusable_role_plugin(self):
        self.profession();receipt=self.publish()
        self.assertEqual(receipt['status'],'published-candidate',receipt)
        artifact=receipt.get('role_plugin')
        self.assertIsNotNone(artifact,'publication must produce a real role-plugin artifact')
        self.assertEqual(artifact['status'],'available')
        self.assertIn(artifact['file'],self.store.read(self.rid)['outputs'])
        data=(self.store.directory(self.rid)/'outputs'/artifact['file']).read_bytes()
        with zipfile.ZipFile(io.BytesIO(data)) as package:
            manifest=json.loads(package.read('tmf-plugin.json'))
            role=json.loads(package.read('role.json'))
            skill=package.read('skills/'+manifest['id']+'/SKILL.md').decode()
        self.assertEqual(manifest['audience'],'both')
        self.assertEqual(manifest['permissions'],[])
        self.assertNotIn('runtime',manifest)
        self.assertEqual(role['entity'],'specialty-definition')
        self.assertFalse(role['definition']['grants_authority'])
        self.assertEqual(role['provenance']['role'],artifact['source'])
        collection=next(r for r in receipt['references'] if r['kind']=='knowledge-collection')
        self.assertEqual(role['definition']['knowledge_references'],[{'id':collection['id'],'revision':collection['revision']}])
        self.assertIn(collection['id'],skill)
        self.assertIn('revision '+str(collection['revision']),skill)
        self.assertNotIn('Events may be delivered more than once.',data.decode('utf8',errors='ignore'))

    def test_retry_keeps_identical_package_and_canon_revisions(self):
        import copy
        self.profession();first=self.publish();before=copy.deepcopy(self.fixture.history)
        path=self.store.directory(self.rid)/'outputs'/first['role_plugin']['file']
        data=path.read_bytes()
        self.assertEqual(self.publish(),first)
        self.assertEqual(self.fixture.history,before)
        self.assertEqual(path.read_bytes(),data)
        self.assertEqual(self.store.read(self.rid)['outputs'].count(path.name),1)
        with zipfile.ZipFile(path) as package:
            self.assertTrue(all(row.external_attr >> 16 == 0o100644 for row in package.infolist()))
            knowledge=[json.loads(e['body'])['knowledge']['text'] for e in self.fixture.entries.values()
                       if json.loads(e['body'])['entity']=='professional-knowledge']
            self.assertTrue(knowledge)
            for name in package.namelist():
                for body in knowledge:self.assertNotIn(body,package.read(name).decode())

    def test_failed_artifact_retains_publication_and_retry_repairs_only_export(self):
        import copy,os
        from unittest.mock import patch
        self.profession()
        replace=os.replace
        def fail_archive(source,dest):
            if str(dest).endswith('.zip'):raise OSError('fixture-only')
            return replace(source,dest)
        with patch('tmf_research.role_plugins.os.replace',side_effect=fail_archive):
            first=self.publish()
        self.assertEqual(first['status'],'published-candidate')
        self.assertEqual(first['role_plugin']['status'],'unavailable')
        self.assertEqual(self.store.read(self.rid)['outputs'],['report.md'])
        self.assertFalse(list((self.store.directory(self.rid)/'outputs').iterdir()))
        before=copy.deepcopy(self.fixture.history)
        second=self.publish()
        self.assertEqual(second['role_plugin']['status'],'available')
        self.assertEqual(self.fixture.history,before)
        self.assertEqual(first['mission'],second['mission'])

    def test_missing_wrong_revision_kind_and_foreign_knowledge_refuse_package(self):
        from tmf_research.canon import CanonConnection,CanonUnavailable
        from tmf_research.role_plugins import build_role_plugin
        self.profession();receipt=self.publish();source=receipt['role_plugin']['source']
        collection=next(e for e in self.fixture.history if json.loads(e['body'])['entity']=='knowledge-collection')
        original=json.loads(collection['body'])
        bad=next(r for r in receipt['references'] if r['kind']=='finding')
        mutations=[{'id':bad['id'],'revision':bad['revision']},
                   {**original['knowledge_references'][0],'revision':999},
                   {'id':'cn-'+'0'*8+'-'+'0'*4+'-4000-8000-'+'0'*12,'revision':1}]
        connection=CanonConnection(self.fixture.config)
        for ref in mutations:
            collection['body']=json.dumps({**original,'knowledge_references':[ref]})
            with self.subTest(ref=ref),self.assertRaises((ValueError,CanonUnavailable)):
                build_role_plugin(connection,source,self.rid)
        collection['body']=json.dumps(original)
        key=collection['fields']['sourceId'];collection['fields']['sourceId']=key.replace('synthetic-workspace:','foreign-workspace:')
        with self.assertRaises(CanonUnavailable):build_role_plugin(connection,source,self.rid)

    def test_role_revision_keeps_package_identity_and_old_definition(self):
        import copy
        from tmf_research.canon import CanonConnection
        from tmf_research.role_plugins import build_role_plugin
        self.profession();receipt=self.publish();source=receipt['role_plugin']['source']
        old=copy.deepcopy(self.fixture.entries[source['id']]);new=copy.deepcopy(old)
        body=json.loads(new['body']);body['definition']['purpose']='Updated proposed professional purpose.'
        body['definition'].update(grants_authority=True,permissions=['admin'],agent_id='injected-worker')
        new.update(revision=2,body=json.dumps(body));self.fixture.entries[new['id']]=new;self.fixture.history.append(new)
        connection=CanonConnection(self.fixture.config)
        first,_=build_role_plugin(connection,source,self.rid)
        second,metadata=build_role_plugin(connection,{**source,'revision':2},self.rid)
        self.assertEqual(metadata['id'],receipt['role_plugin']['id'])
        self.assertEqual(metadata['version'],'0.1.2')
        self.assertNotEqual(first,second)
        with zipfile.ZipFile(io.BytesIO(second)) as package:
            role=json.loads(package.read('role.json'))
            self.assertFalse(role['definition']['grants_authority'])
            self.assertNotIn('permissions',role['definition']);self.assertNotIn('agent_id',role['definition'])
        self.assertEqual(connection.read(source['id'],1),old)

    @unittest.skipUnless(os.environ.get('CANON_TEST_DIST') and shutil.which('node'),
                         'set CANON_TEST_DIST for native MC importer and shared skill reader')
    def test_native_mc_import_shared_read_and_revision_replace_for_two_builder_fixtures(self):
        import os,subprocess,copy
        from pathlib import Path
        from tmf_research.canon import CanonConnection
        from tmf_research.role_plugins import build_role_plugin
        self.profession();receipt=self.publish();source=receipt['role_plugin']['source']
        one=self.store.directory(self.rid)/'package-one';two=self.store.directory(self.rid)/'package-two'
        with zipfile.ZipFile(self.store.directory(self.rid)/'outputs'/receipt['role_plugin']['file']) as package:package.extractall(one)
        new=copy.deepcopy(self.fixture.entries[source['id']]);body=json.loads(new['body'])
        body['definition']['purpose']='Updated fixture expertise.'
        new.update(revision=2,body=json.dumps(body));self.fixture.entries[new['id']]=new;self.fixture.history.append(new)
        data,_=build_role_plugin(CanonConnection(self.fixture.config),{**source,'revision':2},self.rid)
        with zipfile.ZipFile(io.BytesIO(data)) as package:package.extractall(two)
        before=copy.deepcopy(self.fixture.history)
        script=r'''
import {pathToFileURL} from 'node:url';
import {readFileSync,mkdirSync,writeFileSync} from 'node:fs';
import {join} from 'node:path';
import assert from 'node:assert/strict';
const mod=p=>import(pathToFileURL(process.env.CANON_TEST_DIST+'/'+p).href);
const {importPluginFromDirectory}=await mod('link-sync/plugins/importPlugin.js');
const {grantedPluginSkills}=await mod('plugins/grantedPluginSkills.js');
const root=process.env.ROLE_TEST_ROOT,dataDir=join(root,'mc-data');
const workers=['builder-one','builder-two'];
for(const id of workers){mkdirSync(join(dataDir,id),{recursive:true});writeFileSync(join(dataDir,id,'identity-history.json'),JSON.stringify({id,history:['existing-work']}));}
const snapshot=workers.map(id=>readFileSync(join(dataDir,id,'identity-history.json'),'utf8'));
const installed=await importPluginFromDirectory({source:join(root,'package-one'),pluginRoot:join(dataDir,'plugins')});
assert.equal(installed.manifest.audience,'both');assert.deepEqual(installed.manifest.permissions,[]);
const held=[{pluginId:installed.packageId,capabilities:[]}];
assert.deepEqual(grantedPluginSkills(dataDir,'unheld-worker',[]),[]);
let sharedPath;
for(const id of workers){
 const skills=grantedPluginSkills(dataDir,id,held);assert.equal(skills.length,1);
 if(sharedPath)assert.equal(skills[0].path,sharedPath);sharedPath=skills[0].path;
 const skill=readFileSync(sharedPath,'utf8'),role=JSON.parse(readFileSync(join(installed.installedAt,'role.json'),'utf8'));
 for(const ref of role.definition.knowledge_references){
  assert.ok(skill.includes(ref.id));
  const read=async r=>{const response=await fetch(process.env.ROLE_TEST_CANON+'/api/canon/organization/entries/'+r.id+'?revision='+r.revision);assert.equal(response.status,200);const {entry}=await response.json();assert.equal(entry.revision,r.revision);return JSON.parse(entry.body)};
  const collection=await read(ref);assert.equal(collection.entity,'knowledge-collection');
  for(const member of collection.knowledge_references)assert.equal((await read(member)).entity,'professional-knowledge');
 }
}
const updated=await importPluginFromDirectory({source:join(root,'package-two'),pluginRoot:join(dataDir,'plugins'),replace:true,expectedPackageId:installed.packageId});
assert.equal(updated.packageId,installed.packageId);assert.equal(updated.manifest.version,'0.1.2');
for(const [index,id] of workers.entries()){
 const skills=grantedPluginSkills(dataDir,id,held);assert.equal(skills.length,1);
 assert.ok(readFileSync(skills[0].path,'utf8').includes('Updated fixture expertise.'));
 assert.equal(readFileSync(join(dataDir,id,'identity-history.json'),'utf8'),snapshot[index]);
}
console.log('two builder fixtures: native import, shared skill read, exact knowledge retrieval, replace passed');
'''
        result=subprocess.run(['node','--input-type=module','-e',script],env={**os.environ,
            'ROLE_TEST_ROOT':str(self.store.directory(self.rid)),'ROLE_TEST_CANON':self.fixture.config['canon']['url'],
            'CHAT_BACKEND_DATA_DIR':str(Path(self.temp.name)/'isolated-native-data')},capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('replace passed',result.stdout)
        self.assertEqual(self.fixture.history,before,'two readers must not create knowledge copies')

    def test_published_role_download_uses_existing_output_route_and_retains_bytes(self):
        import socket,subprocess,sys,time,urllib.request
        self.profession();receipt=self.publish();artifact=receipt['role_plugin']
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        process=subprocess.Popen([sys.executable,'-B','-m','tmf_research','serve','--runs',self.temp.name,'--port',str(port)],
                                 stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        def stop():
            process.terminate()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=3)
        self.addCleanup(stop)
        url=f'http://127.0.0.1:{port}/outputs/{self.rid}/'+artifact['file']
        for _ in range(100):
            try:
                with urllib.request.urlopen(url,timeout=2) as response:
                    self.assertEqual(response.headers['Content-Type'],'application/zip')
                    self.assertIn('attachment',response.headers['Content-Disposition'])
                    self.assertEqual(response.read(),(self.store.directory(self.rid)/'outputs'/artifact['file']).read_bytes())
                break
            except OSError:time.sleep(.03)
        else:self.fail('Saved role download did not become available')
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/result/{self.rid}',timeout=2) as response:
            self.assertEqual(json.load(response)['canon']['role_plugin'],artifact)
