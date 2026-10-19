import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from tmf_research.engine import ResearchEngine,RunStore
from test_engine import FakeModel,FakeWeb

class ServerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=RunStore(self.temp.name)
        self.rid=self.store.create({'question':'What does reliable intake require?','depth':'quick','formats':['md','builder']})
        ResearchEngine(self.store,model=FakeModel(),web=FakeWeb()).execute(self.rid)
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));self.port=sock.getsockname()[1]
        self.base=f'http://127.0.0.1:{self.port}'
        self.process=subprocess.Popen([sys.executable,'-m','tmf_research','serve','--runs',self.temp.name,'--port',str(self.port)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        self.addCleanup(self.stop)
        for _ in range(100):
            try:
                self.token=self.request('/api/config')['token'];return
            except OSError:time.sleep(.03)
        self.fail('Workbench failed to start')
    def stop(self):
        self.process.terminate()
        try:self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=5)
    def request(self,path,payload=None,**headers):
        if payload is not None:
            headers={'Content-Type':'application/json','X-TMF-Token':getattr(self,'token',''),**headers}
        data=json.dumps(payload).encode() if payload is not None else None
        with urllib.request.urlopen(urllib.request.Request(self.base+path,data=data,headers=headers),timeout=3) as r:return json.load(r)
    def test_origin_token_and_terminal_cancel_guards(self):
        for headers in [{'Origin':'https://evil.example'},{'X-TMF-Token':'wrong'}]:
            with self.assertRaises(urllib.error.HTTPError) as caught:self.request('/api/brief',{'question':'Investigate this workflow'},**headers)
            self.assertEqual(caught.exception.code,403)
            caught.exception.close()
        with self.assertRaises(urllib.error.HTTPError) as caught:self.request('/api/cancel',{'id':self.rid})
        self.assertEqual(caught.exception.code,409)
        caught.exception.close()
        self.assertEqual(self.store.read(self.rid)['status'],'completed')
    def test_reexport_uses_accepted_revision_without_model_calls(self):
        before=(self.store.directory(self.rid)/'role-calls.json').read_bytes()
        self.request('/api/export',{'id':self.rid,'formats':['md','builder']})
        for _ in range(100):
            state=self.request('/api/runs/'+self.rid)
            if state['status'] not in ('running','queued'):break
            time.sleep(.03)
        self.assertEqual(state['status'],'completed',state)
        self.assertEqual((self.store.directory(self.rid)/'role-calls.json').read_bytes(),before)
        new=[n for n in state['outputs'] if n.startswith('e') and n.endswith('-builder-pack.json')]
        self.assertEqual(len(new),1)
        exported=json.loads((self.store.directory(self.rid)/'outputs'/new[0]).read_text())
        self.assertIn('council',exported);self.assertIn('claims',exported)
        result=self.request('/api/result/'+self.rid)
        self.assertEqual(result['report']['title'],'Webhook workflow')
    def test_resolved_export_failure_is_archived(self):
        self.store.update(self.rid,status='partial',errors=['Requested md export unavailable (RuntimeError); no successful export claimed'])
        self.request('/api/export',{'id':self.rid,'formats':['md']})
        for _ in range(100):
            state=self.request('/api/runs/'+self.rid)
            if state['status']!='running':break
            time.sleep(.03)
        self.assertEqual(state['status'],'completed',state)
        self.assertEqual(state['errors'],[])
        self.assertEqual(len(state['error_history']),1)
    def test_successful_reexport_does_not_upgrade_uncertain_research(self):
        claims=self.store.directory(self.rid)/'claims.json'
        data=json.loads(claims.read_text());data[0]['review']='uncertain';claims.write_text(json.dumps(data))
        self.store.update(self.rid,status='partial')
        self.request('/api/export',{'id':self.rid,'formats':['md']})
        for _ in range(100):
            state=self.request('/api/runs/'+self.rid)
            if state['status']!='running':break
            time.sleep(.03)
        self.assertEqual(state['status'],'partial')

if __name__=='__main__':unittest.main()
