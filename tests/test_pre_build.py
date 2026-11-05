"""PRE-BUILD preset (Owner 2026-11-05, Canon cn-bdaf883f): Crawlee swarm ingress, quick depth, the Workstream Council,
and the workstream spec doc in chapters, returned as mc-pre-build/1."""
import hashlib
import json
import tempfile
import unittest
from tmf_research.engine import brief, ResearchEngine, RunStore, PRESETS
from tmf_research.providers import ProviderError
from test_engine import FakeModel, TEXT

DIGEST = hashlib.sha256(TEXT.encode()).hexdigest()
WORKSTREAM = {'id': 'ws-tmf-site', 'goal': 'TMF website v1: a fast marketing site', 'whoFor': 'The Owner: "make it pop"',
              'existing': ['Canon: the kit tokens are the look'], 'references': ['https://example.com/inspiration', 'Linear.app hero'],
              'constraints': ['Vite + React'], 'unknowns': ['Hosting']}
CHAPTERS = [('summary', 'Summary'), ('what-exists', 'What exists'), ('research', 'Research'), ('requirements', 'Requirements'),
            ('design', 'Design'), ('build-1', 'Build: hero and nav'), ('proof', 'Proof and Owner questions')]


class FakeCrawlee:
    def __init__(self, status='completed'):
        self.calls = []; self.status = status
    def call(self, name, args):
        self.calls.append((name, args))
        if name == 'crawlee_start': return {'id': f'job-{len(self.calls)}'}
        if name == 'crawlee_status':
            return {'status': self.status, 'sources': [{'id': 'S001', 'url': args['job_id'] + '.example', 'final_url': 'https://example.com/docs',
                                                        'title': 'Public docs', 'state': 'available', 'text_sha256': DIGEST}]}
        if name == 'crawlee_read': return {'source': {'text_sha256': DIGEST}, 'text': TEXT, 'end': len(TEXT), 'total_characters': len(TEXT)}
        if name == 'crawlee_pack': return {'artifacts': [{'name': 'pack.json', 'sha256': 'a' * 64}]}
        raise ProviderError('unexpected ' + name)


class PreBuildModel(FakeModel):
    def __init__(self, chapters=CHAPTERS, **kw):
        super().__init__(**kw); self.chapters = chapters
    def call(self, role, instruction, data, search=False):
        if role == 'Spec writer':
            self.calls += 1; self.roles.append((role, search))
            return {'title': 'TMF website v1', 'chapters': [{'id': cid, 'title': title, 'body': f'{title}: duplicate events are documented (S001).'}
                                                            for cid, title in self.chapters]}
        return super().call(role, instruction, data, search)


class FailIfFetched:
    def fetch(self, url): raise AssertionError('the pre-build preset never falls back to the public-web fetcher')


class PreBuildTests(unittest.TestCase):
    def run_job(self, model=None, crawlee=None, config=None, **extra):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        store = RunStore(tmp.name)
        rid = store.create({'question': 'What does the TMF website need before the builders build it?', 'preset': 'pre-build',
                            'workstream': WORKSTREAM, **extra}, request_id='ws-tmf-site:research')
        engine = ResearchEngine(store, config=config, model=model or PreBuildModel(), web=FailIfFetched(), crawlee=crawlee)
        engine.execute(rid)
        return store, rid, engine

    def test_the_preset_decides_depth_formats_and_the_workstream_council(self):
        request = brief({'question': 'What does the TMF website need before the builders build it?', 'preset': 'pre-build', 'workstream': WORKSTREAM,
                         'depth': 'deep', 'formats': ['pdf']})
        self.assertEqual([request['depth'], request['formats']], ['quick', ['builder', 'md']], 'the launcher passes the preset; the preset decides')
        self.assertEqual(request['council_members'], ['systems', 'fullstack', 'design', 'customer', 'challenger', 'canon'])
        self.assertEqual(request['urls'], ['https://example.com/inspiration'], 'only https references become crawl seeds')
        self.assertFalse(brief({**request, 'council': False})['council'], 'light or no Council: the brief may turn it off')
        for bad in [{'preset': 'deep-dive'}, {'workstream': None}, {'workstream': {'goal': ''}}, {'workstream': {**WORKSTREAM, 'tickets': ['T-1']}}]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                brief({'question': 'What does the TMF website need before the builders build it?', 'preset': 'pre-build', 'workstream': WORKSTREAM, **bad})
        self.assertNotIn('preset', brief({'question': 'What does reliable event intake require?'}), 'an ordinary brief is unchanged (same request hash)')

    def test_a_swarm_run_returns_the_spec_in_chapters_with_crawlee_provenance(self):
        crawlee = FakeCrawlee(); model = PreBuildModel()
        store, rid, _ = self.run_job(model, crawlee)
        state = store.read(rid); self.assertEqual(state['status'], 'completed', state)
        started = [args for name, args in crawlee.calls if name == 'crawlee_start']
        self.assertEqual([s['allowed_domains'] for s in started], [['example.com']], 'one bounded job per site')
        self.assertEqual(started[0]['max_pages'], 5)
        result = json.loads((store.directory(rid) / 'pre-build.json').read_text())
        self.assertEqual([result['schema'], result['preset']], ['mc-pre-build/1', 'pre-build'])
        self.assertEqual([c['id'] for c in result['spec']['chapters']], [cid for cid, _ in CHAPTERS])
        self.assertIn('## Build: hero and nav', result['spec']['markdown'])
        self.assertEqual(result['acquisition']['provider'], 'crawlee')
        self.assertEqual(result['acquisition']['sourceHashes'], [DIGEST])
        self.assertTrue(result['acquisition']['jobIds'] and result['acquisition']['packs'])
        self.assertEqual(result['sources'][0]['artifact_sha256'], DIGEST)
        self.assertIn('spec.md', state['outputs']); self.assertIn('builder-pack.json', state['outputs'])
        council = json.loads((store.directory(rid) / 'council.json').read_text())
        self.assertIn('Canon keeper', [p['role'] for p in council['positions']])
        self.assertNotIn('tickets', json.dumps(result['spec']).lower(), 'Research writes the doc; the builders cut the tickets')

    def test_no_crawlee_is_a_failed_run_with_the_reason_never_a_web_fallback(self):
        store, rid, _ = self.run_job(config={'crawlee': {}})
        state = store.read(rid)
        self.assertEqual(state['status'], 'failed')
        self.assertTrue(any('Crawlee is not configured' in e for e in state['errors']), state['errors'])
        self.assertFalse((store.directory(rid) / 'pre-build.json').exists())

    def test_a_spec_off_the_template_is_withheld_and_the_run_is_partial(self):
        store, rid, _ = self.run_job(PreBuildModel(chapters=CHAPTERS[:4] + CHAPTERS[-1:]), FakeCrawlee())
        state = store.read(rid)
        self.assertEqual(state['status'], 'partial')
        self.assertTrue(any('spec doc withheld' in e for e in state['errors']), state['errors'])
        self.assertIsNone(json.loads((store.directory(rid) / 'pre-build.json').read_text())['spec'])
        self.assertNotIn('spec.md', state['outputs'])

    def test_the_preset_budget_covers_the_six_member_council(self):
        self.assertGreaterEqual(PRESETS['pre-build']['limits']['calls'], 24)


if __name__ == '__main__':
    unittest.main()
