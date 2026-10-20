import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from tmf_research.engine import brief, ResearchEngine, RunStore
from test_engine import FakeModel, FakeWeb


class DocumentsTests(unittest.TestCase):
    def setup_engine(self, raw=b'Local contract: agents work; builders ship.'):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        path=Path(tmp.name)/'contract.txt';path.write_bytes(raw)
        store=RunStore(Path(tmp.name)/'runs')
        rid=store.create({'question':'How should local contracts inform research?','depth':'quick','documents':['contract'],'formats':['md','html','builder']})
        engine=ResearchEngine(store,{'documents':{'contract':{'path':str(path),'sha256':hashlib.sha256(raw).hexdigest()}}},model=FakeModel(),web=FakeWeb())
        engine.run_id=rid
        return engine,store,rid,path

    def test_selected_bytes_are_retained_and_do_not_spend_web_budget(self):
        engine,store,rid,path=self.setup_engine();engine.documents(['contract'])
        source=engine.sources[0];self.assertEqual(source['kind'],'local-document')
        self.assertEqual((store.directory(rid)/'evidence/D001.body').read_bytes(),path.read_bytes())
        engine.fetch([{'url':'https://example.com'}],1)
        self.assertEqual(len(engine.sources),2)
        self.assertNotIn(str(path),json.dumps(source))

    def test_invalid_bytes_oversize_and_tampering_have_no_packet(self):
        for raw in (b'\xff',b'x'*200001):
            engine,store,rid,path=self.setup_engine(raw);engine.documents(['contract'])
            self.assertEqual(engine.sources[0]['state'],'unavailable');self.assertFalse(engine.packets)
        engine,store,rid,path=self.setup_engine();path.write_text('changed')
        engine.documents(['contract']);self.assertEqual(engine.sources[0]['state'],'unavailable')

    def test_unconfigured_paths_are_not_accepted(self):
        engine,_,_,_=self.setup_engine()
        with self.assertRaises(ValueError):engine.documents(['/etc/passwd'])
        with self.assertRaises(ValueError):brief({'question':'Investigate local contracts','documents':['/etc/passwd']})

    def test_revision_preserves_local_evidence_and_rejects_changed_bytes(self):
        engine,store,parent,path=self.setup_engine();engine.execute(parent)
        self.assertEqual(store.read(parent)['status'],'completed')
        source=next(s for s in engine.sources if s.get('kind')=='local-document')
        rid=store.create(json.loads((store.directory(parent)/'brief.json').read_text()))
        revised=ResearchEngine(store,model=FakeModel());revised.refine(rid,parent,'Explain the local contract')
        self.assertEqual(store.read(rid)['status'],'completed')
        retained=store.directory(parent)/'evidence'/(source['id']+'.body')
        self.assertEqual((store.directory(rid)/'evidence'/retained.name).read_bytes(),retained.read_bytes())
        self.assertEqual(next(s for s in revised.sources if s.get('kind')=='local-document'),source)
        retained.write_text('tampered');bad=store.create(brief({'question':'Investigate local contracts'}));model=FakeModel()
        ResearchEngine(store,model=model).refine(bad,parent,'Explain the contract')
        self.assertEqual(store.read(bad)['status'],'failed');self.assertEqual(model.calls,0)
