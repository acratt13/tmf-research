"""Research consumes Canon's real native-shelf route in scratch storage only."""
import hashlib
import io
import json
import os
from pathlib import Path
import select
import shutil
import subprocess
import unittest
import urllib.request
import zipfile
from unittest.mock import patch

import test_canon
from tmf_research.role_knowledge import KnowledgeShelf,collect_role_knowledge


@unittest.skipUnless(os.environ.get('KNOWLEDGE_TEST_DIST') and shutil.which('node'),
                     'set KNOWLEDGE_TEST_DIST to MC dist/src with the pinned read_knowledge contract')
class NativeKnowledgeContractTests(unittest.TestCase):
    setUp=test_canon.CandidateTests.setUp

    def test_actual_native_reader_material_is_usable_in_role_package_without_database_changes(self):
        script=r'''
import {pathToFileURL} from 'node:url';import {createServer} from 'node:http';
import {join} from 'node:path';import {writeFileSync,readFileSync,renameSync} from 'node:fs';import {createHash} from 'node:crypto';
const mod=p=>import(pathToFileURL(process.env.KNOWLEDGE_TEST_DIST+'/'+p).href);
const {KnowledgeStore}=await mod('memory/knowledgeStore.js');const {createMemoryRoutes}=await mod('memory/memoryRoutes.js');
const root=process.env.ROLE_CONTRACT_ROOT,file=join(root,'guide.md');
const text='# Guide\n\nThe system can deliver duplicate events. Use the documented plugin installation and verification workflow.\n\n'+
 ('Keep source identity and verify the running package before reporting success.\n\n'.repeat(100));
writeFileSync(file,text);const store=new KnowledgeStore(root);
const doc=store.put({title:'Guide',text,path:file,source_kind:'pack',lane:'builder'},'fixture').doc;store.close();
let opens=0;const route=createMemoryRoutes({dataDir:root,options:{operatorAuthorized:r=>!r.headers.authorization||r.headers.authorization==='Bearer fixture-only',episodeLane:id=>id==='agent-fixture'?'agent':'builder'},open:()=>{opens++;throw Error('writer opened');},openKnowledge:()=>{opens++;throw Error('knowledge writer opened');}});
const hash=()=>createHash('sha256').update(readFileSync(join(root,'memory/knowledge.db'))).digest('hex');const before=hash();
const server=createServer(async(req,res)=>{
 if(req.url==='/stats'){res.end(JSON.stringify({before,after:hash(),opens}));return;}
 if(req.url==='/fixture-change'){writeFileSync(file,'# Guide\n\nSource changed after selection.');res.end('{}');return;}
 if(req.url==='/fixture-remove'){renameSync(file,file+'.saved');res.end('{}');return;}
 const handled=await route(req,res,new URL(req.url,'http://fixture'));if(!handled){res.writeHead(404);res.end('{}');}
});server.listen(0,'127.0.0.1',()=>console.log(JSON.stringify({url:'http://127.0.0.1:'+server.address().port,doc_id:doc.id,content_hash:doc.content_hash})));
process.on('SIGTERM',()=>server.close(()=>process.exit(0)));
'''
        root=Path(self.temp.name)/'native-contract';root.mkdir()
        process=subprocess.Popen(['node','--input-type=module','-e',script],env={**os.environ,'ROLE_CONTRACT_ROOT':str(root)},
                                 stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        def close():
            process.terminate()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=3)
            process.stdout.close();process.stderr.close()
        self.addCleanup(close)
        ready,_,_=select.select([process.stdout],[],[],10);self.assertTrue(ready,'native contract did not start')
        line=process.stdout.readline();self.assertTrue(line,process.stderr.read() if process.poll() is not None else 'No contract URL')
        source=json.loads(line)
        config={'native_knowledge':{'url':source['url'],'actor':'bound-builder','token_env':'NATIVE_TEST_AUTH'}}
        selected={k:source[k] for k in ('doc_id','content_hash')};selected.update(chunk_indexes=[0],purpose='Install and verify plugin behavior')
        with patch.dict(os.environ,{'NATIVE_TEST_AUTH':'fixture-only'}):
            reader=KnowledgeShelf(config)
            page=reader.read({'id':source['doc_id'],'offset':0,'expected_hash':source['content_hash']})
            self.assertEqual(page['source_currentness']['state'],'current')
            self.assertTrue(page['chunk_refs'])
            local=KnowledgeShelf({'native_knowledge':{'url':source['url'],'actor':'bound-builder','auth':'local-operator'}})
            self.assertEqual(local.read({'id':source['doc_id'],'expected_hash':source['content_hash']})['content_hash'],source['content_hash'])
            material=collect_role_knowledge([selected],reader.read)
            self.assertEqual(material['status'],'complete',material)
            self.assertEqual(material['sources'][0]['chunks'][0]['id'],source['doc_id']+'@'+source['content_hash']+'#0')
            self.assertIn('documented plugin installation',material['sources'][0]['chunks'][0]['text'])
            # Build the ordinary plugin from its Canon role plus these actual native passages.
            from test_role_plugins import RolePluginTests
            RolePluginTests.profession(self);receipt=test_canon.CandidateTests.publish(self)
            from tmf_research.role_plugins import build_role_plugin
            from tmf_research.canon import CanonConnection
            data,_=build_role_plugin(CanonConnection(self.fixture.config),receipt['role_plugin']['source'],self.rid,native_knowledge=material)
            with zipfile.ZipFile(io.BytesIO(data)) as package:
                text=package.read('knowledge/role-knowledge.md').decode()
                self.assertIn('documented plugin installation',text)
                selection=json.loads(package.read('knowledge/selection.json'))
                self.assertEqual(selection['sources'][0]['content_hash'],source['content_hash'])
                self.assertEqual(json.loads(package.read('tmf-plugin.json'))['audience'],'builders')
                self.assertNotIn(str(root),data.decode('utf8',errors='ignore'))
                exported=root/'role-export';package.extractall(exported)
            imported_script=r'''
import {pathToFileURL} from 'node:url';import {readFileSync} from 'node:fs';import {join} from 'node:path';import assert from 'node:assert/strict';
const mod=p=>import(pathToFileURL(process.env.KNOWLEDGE_TEST_DIST+'/'+p).href);
const {importPluginFromDirectory}=await mod('link-sync/plugins/importPlugin.js');const {grantedPluginSkills}=await mod('plugins/grantedPluginSkills.js');
const root=process.env.ROLE_CONTRACT_ROOT,installed=await importPluginFromDirectory({source:join(root,'role-export'),pluginRoot:join(root,'plugins')});
assert.equal(installed.manifest.audience,'builders');const held=[{pluginId:installed.packageId,capabilities:[]}];let shared;
for(const id of ['builder-fixture-one','builder-fixture-two']){
 const cards=grantedPluginSkills(root,id,held);assert.equal(cards.length,2);
 const card=cards.find(c=>c.name.includes('-knowledge-kn-'));assert.ok(card);
 const body=readFileSync(card.path,'utf8');assert.ok(body.includes('documented plugin installation'));
 if(shared)assert.equal(card.path,shared);shared=card.path;
}
console.log('both builder fixtures consume captured native material through normal skill readers');
'''
            imported=subprocess.run(['node','--input-type=module','-e',imported_script],env={**os.environ,'ROLE_CONTRACT_ROOT':str(root)},capture_output=True,text=True,timeout=30)
            self.assertEqual(imported.returncode,0,imported.stderr)
            self.assertIn('both builder fixtures',imported.stdout)
            wrong={**selected,'content_hash':'0'*64}
            refused=collect_role_knowledge([wrong],reader.read)
            self.assertEqual(refused['sources'],[])
            self.assertEqual(refused['gaps'][0]['reason'],'indexed_revision_changed')
            denied=KnowledgeShelf({'native_knowledge':{**config['native_knowledge'],'actor':'agent-fixture'}})
            self.assertEqual(collect_role_knowledge([selected],denied.read)['sources'],[])
            with urllib.request.urlopen(source['url']+'/fixture-change',timeout=3):pass
            changed=collect_role_knowledge([selected],reader.read)
            self.assertEqual(changed['sources'],[]);self.assertEqual(changed['gaps'][0]['reason'],'changed')
            with urllib.request.urlopen(source['url']+'/fixture-remove',timeout=3):pass
            missing=collect_role_knowledge([selected],reader.read)
            self.assertEqual(missing['gaps'][0]['reason'],'missing')
        with urllib.request.urlopen(source['url']+'/stats',timeout=3) as response:stats=json.load(response)
        self.assertEqual(stats['before'],stats['after']);self.assertEqual(stats['opens'],0)
