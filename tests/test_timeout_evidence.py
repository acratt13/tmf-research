import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tmf_research.engine import ResearchEngine, RunStore
from tmf_research.processes import bounded_run
from tmf_research.processes import retained_diagnostic
from tmf_research.providers import CodexModel
from test_provider_protocol import FEATURES


class TimeoutEvidenceTests(unittest.TestCase):
    def test_overlapping_timeouts_keep_each_roles_evidence(self):
        from concurrent.futures import ThreadPoolExecutor
        class Model:
            def call(self, role, *args, **kwargs):
                raise subprocess.TimeoutExpired('fixture', 180, output=role.encode(), stderr=b'partial stderr')
        with tempfile.TemporaryDirectory() as root:
            store = RunStore(root)
            engine = ResearchEngine(store, model=Model())
            engine.model = Model()
            engine.run_id = store.create({'question': 'Retain each overlapping role timeout'})
            def run(role):
                with self.assertRaises(subprocess.TimeoutExpired): engine.call(role, 'fixture', {})
            with ThreadPoolExecutor(max_workers=3) as pool: list(pool.map(run, ['first', 'second', 'third']))
            roles = store.read(engine.run_id)['timed_out_roles']
            self.assertEqual({r['role'] for r in roles}, {'first', 'second', 'third'})
            for role in roles: self.assertEqual(role['partial']['stdout'], role['role'])

    def test_nested_credential_patterns_mask_tokens_but_keep_usage_counts(self):
        credentials = ['token', 'id_token', 'idToken', 'session_token', 'oauth_token', 'access_token',
                       'prefixSecretSuffix', 'MyPasswordHint', 'vendor_API_KEY_backup', 'vendorApiKey', 'api.key', 'api key', 'ProxyAUTHORIZATIONdata']
        value = {'outer': [{**{key: 'synthetic-credential-741' for key in credentials},
                            'elapsed_ms': 123, 'usage': {'input_tokens': 17, 'output_tokens': 8, 'token_count': 25}}]}
        clean = json.loads(retained_diagnostic(json.dumps(value)))['outer'][0]
        for key in credentials:
            self.assertEqual(clean[key], '[redacted]', key)
        self.assertEqual(clean['usage'], {'input_tokens': 17, 'output_tokens': 8, 'token_count': 25})
        self.assertEqual(clean['elapsed_ms'], 123)

    def test_diagnostics_redact_structured_credentials_and_remain_bounded(self):
        # SECRET-FIXTURE: synthetic sentinels, not real secrets.
        value = json.dumps({'type': 'item.completed', 'item': {'apiKey': 'synthetic-key-741',
                          'text': 'https://user:synthetic-pass-741@example.test/?token=synthetic-query-741',
                          'usage': {'input_tokens': 12}}})
        output = retained_diagnostic(value)
        for secret in ['synthetic-key-741', 'synthetic-pass-741', 'synthetic-query-741']:
            self.assertNotIn(secret, output)
        retained_diagnostic(r'{"text":"\ud800"}').encode('utf-8')
        self.assertIn('input_tokens', output)
        for partial in ['password="synthetic multi word', 'Authorization: Basic synthetic-basic-value', 'api_key=synthetic-query-value&other=detail']:
            self.assertNotIn('synthetic', retained_diagnostic(partial))
        self.assertIn('[partial diagnostic truncated]', retained_diagnostic('x'*17000))

    @unittest.skipUnless(shutil.which('node'), 'node is optional; required only for the browser renderer probe')
    def test_timeout_section_uses_text_nodes_and_names_the_evidence_boundary(self):
        # Execute the real rendering function with a tiny DOM; no layout claims.
        script = (Path(__file__).parents[1]/'tmf_research/web/app.js').read_text()
        function = script[script.index('function timedOutSection('):script.index('async function showResult(')]
        probe = '''
import assert from 'node:assert/strict';
const element=(tag,text)=>({tag,text,children:[],append(...children){this.children.push(...children)}});
''' + function + '''
const node=timedOutSection([{role:'Reviewer',elapsed_seconds:180,timeout_seconds:180,partial:{stdout:'<script>fixture</script>',stderr:'partial stderr'}}]);
assert.equal(node.tag,'section');
assert.match(node.children[0].text,/Timed-out roles/);
assert.match(node.children[1].text,/not accepted research/);
assert.equal(node.children[2].children[2].tag,'pre');
assert.equal(node.children[2].children[2].text,'<script>fixture</script>');
assert.equal(timedOutSection([]),null);
'''
        subprocess.run(['node', '--input-type=module', '-e', probe], check=True, capture_output=True)

    def test_process_timeout_carries_both_partial_streams(self):
        with self.assertRaises(subprocess.TimeoutExpired) as caught:
            bounded_run([sys.executable, '-c',
                         'import os,time;os.write(1,b"partial stdout");os.write(2,b"partial stderr");time.sleep(10)'],
                        timeout=.15)
        self.assertIn(b'partial stdout', caught.exception.output)
        self.assertIn(b'partial stderr', caught.exception.stderr)

    def test_real_role_timeout_survives_temp_cleanup_without_secrets(self):
        # SECRET-FIXTURE: synthetic sentinels only; never provider credentials.
        sentinels = ['synthetic-environment-value-741', 'synthetic-bearer-value-741', 'synthetic-query-value-741']
        with tempfile.TemporaryDirectory() as root:
            store = RunStore(root)
            run = store.create({'question': 'Why did this bounded fixture time out?', 'council': False})
            with patch('tmf_research.providers.subprocess.check_output', return_value=FEATURES):
                model = CodexModel(timeout=.15)
            def child(command, **kwargs):
                return bounded_run([sys.executable, '-c',
                    'import os,time;os.write(1,b\'{"type":"item.completed","item":{"text":"partial answer synthetic-environment-value-741"}}\\n\');'
                    'os.write(2,b"Authorization: Bearer synthetic-bearer-value-741\\nhttps://example.test/?api_key=synthetic-query-value-741");time.sleep(10)'],
                    timeout=kwargs['timeout'])
            with patch.dict(os.environ, {'FIXTURE_API_KEY': sentinels[0]}), patch('tmf_research.providers.bounded_run', side_effect=child):
                ResearchEngine(store, model=model).execute(run)
            state = store.read(run)
            self.assertEqual(state['status'], 'failed', 'partial diagnostics must not become successful research')
            self.assertIn('TimeoutExpired', ' '.join(state['errors']))
            roles = state['timed_out_roles']
            self.assertEqual(len(roles), 1)
            role = roles[0]
            self.assertEqual(role['role'], 'Research lead')
            self.assertEqual(role['status'], 'timed_out')
            self.assertEqual(role['timeout_seconds'], .15)
            self.assertGreaterEqual(role['elapsed_seconds'], .15)
            self.assertIn('partial answer', role['partial']['stdout'])
            self.assertIn('[redacted]', role['partial']['stderr'])
            retained = ''.join(p.read_text() for p in store.directory(run).glob('*.json'))
            for secret in sentinels:
                self.assertNotIn(secret, retained)
            self.assertEqual(json.loads((store.directory(run)/'role-calls.json').read_text())[0], role)
            self.assertEqual(state['outputs'], [])


if __name__ == '__main__':
    unittest.main()
