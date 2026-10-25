import json
import hashlib
import os
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tmf_research.engine import ResearchEngine, RunStore


class RoleRetentionTests(unittest.TestCase):
    def engine(self, root, model):
        store = RunStore(root)
        engine = ResearchEngine(store, model=model)
        engine.model = model
        engine.run_id = store.create({'question': 'Retain exact coverage input and output'})
        engine.request = json.loads((store.directory(engine.run_id)/'brief.json').read_text())
        return engine

    def test_coverage_keeps_raw_queries_and_replays_the_later_exact_input(self):
        queries = ['Read the primary cancellation specification', 'Check paging applicability']
        raw = {'criteria': [{'index': 0, 'status': 'unanswered', 'finding_ids': [], 'reason': 'Evidence needed'}],
               'follow_up_queries': queries, 'extra': {'preserved': True}}
        class Model:
            def __init__(self): self.inputs = []
            def call(self, role, instruction, data, *, search=False):
                self.inputs.append(dict(role=role, instruction=instruction, data=data, search=search))
                saved = json.loads(self.path.read_text())
                assert saved[-1]['input'] == self.inputs[-1], 'input must be durable before dispatch'
                return json.loads(json.dumps(raw))
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, {}, clear=True):
            model = Model(); engine = self.engine(root, model)
            model.path = engine.store.directory(engine.run_id)/'role-calls.json'
            plan = {'success_criteria': ['Resolve the cancellation contract']}
            objections = engine.coverage(plan, [])
            analysis = {'summary': 'Retained analysis', 'text': 'é quote " '*4000}
            engine.coverage(plan, objections, analysis)
            path = engine.store.directory(engine.run_id)/'role-calls.json'
            rows = json.loads(path.read_text())
            self.assertEqual(rows[0]['output'], raw)
            self.assertEqual(rows[1]['input'], model.inputs[1])
            self.assertEqual(rows[1]['input']['data']['objections'], queries)
            self.assertFalse(rows[1]['input_redacted'])
            self.assertFalse(rows[0]['output_redacted'])
            self.assertEqual(model.call(**rows[1]['input']), raw, 'retained call is directly replayable')
            self.assertEqual(rows[1]['input_sha256'], hashlib.sha256(json.dumps(rows[1]['input'], ensure_ascii=False).encode()).hexdigest())
            normalized = json.loads((path.parent/'coverage-final.json').read_text())
            self.assertEqual(set(normalized), {'kind', 'criteria'})
            raw['follow_up_queries'].append('later mutation')
            analysis['summary'] = 'later mutation'
            engine.call('Another role', 'Persist again', {})
            saved = json.loads(path.read_text())
            self.assertEqual(saved[0]['output']['follow_up_queries'], queries[:-1])
            self.assertEqual(saved[1]['input']['data']['accepted_analysis']['summary'], 'Retained analysis')

    def test_failed_call_keeps_input_without_expanding_timeout_state(self):
        class Model:
            def call(self, *args, **kwargs):
                raise subprocess.TimeoutExpired('fixture', 180, output=b'partial', stderr=b'')
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, {}, clear=True):
            engine = self.engine(root, Model())
            with self.assertRaises(subprocess.TimeoutExpired): engine.call('Reviewer', 'Exact instruction', {'source': 'retained'})
            row = json.loads((engine.store.directory(engine.run_id)/'role-calls.json').read_text())[0]
            self.assertEqual(row['input']['data'], {'source': 'retained'})
            self.assertNotIn('output', row)
            state_row = engine.store.read(engine.run_id)['timed_out_roles'][0]
            self.assertNotIn('input', state_row)
            self.assertEqual(state_row['partial']['stdout'], 'partial')

    def test_retained_values_filter_credentials_and_mark_inexact_replays(self):
        # SECRET-FIXTURE: synthetic sentinel, never a real credential.
        class Model:
            def call(self, *args, **kwargs): return {'nested': {'session_token': 'synthetic-value'}, 'input_tokens': 123}
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, {}, clear=True):
            engine = self.engine(root, Model())
            answer = engine.call('Reviewer', 'Fixture', {'apiKey': 'synthetic-value'})
            self.assertEqual(answer['nested']['session_token'], 'synthetic-value', 'consumer value is unchanged')
            path = engine.store.directory(engine.run_id)/'role-calls.json'
            row = json.loads(path.read_text())[0]
            self.assertNotIn('synthetic-value', path.read_text())
            self.assertTrue(row['input_redacted']); self.assertTrue(row['output_redacted'])
            self.assertEqual(row['output']['input_tokens'], 123)

    def test_overlapping_calls_keep_independent_snapshots_before_consumers_mutate(self):
        from concurrent.futures import ThreadPoolExecutor
        class Model:
            def call(self, role, instruction, data, *, search=False): return {'role': role, 'values': [data['number']]}
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, {}, clear=True):
            engine = self.engine(root, Model())
            def run(number):
                data = {'number': number}
                answer = engine.call('Reviewer ' + str(number), 'Fixture', data)
                data['number'] = -1; answer['values'].clear()
            with ThreadPoolExecutor(max_workers=3) as pool: list(pool.map(run, range(9)))
            rows = json.loads((engine.store.directory(engine.run_id)/'role-calls.json').read_text())
            self.assertEqual(len(rows), 9)
            for row in rows:
                number = row['input']['data']['number']
                self.assertEqual(row['output'], {'role': 'Reviewer ' + str(number), 'values': [number]})
                self.assertEqual(row['status'], 'returned')
