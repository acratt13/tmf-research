import contextlib
import io
import json
import tempfile
import unittest
from unittest.mock import patch
from tmf_research.cli import main
from tmf_research.engine import RunStore


class LifecycleTests(unittest.TestCase):
    def test_status_is_a_short_cli_operation(self):
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors), patch.dict('os.environ', {'TMF_RESEARCH_URL': 'http://127.0.0.1:1'}):
            try:
                code = main(['status'])
            except SystemExit as exc:
                code = exc.code
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(output.getvalue())['status'], 'unavailable')

    def test_stable_request_uses_the_same_saved_run_and_refuses_changed_input(self):
        with tempfile.TemporaryDirectory() as root:
            store = RunStore(root)
            request = {'question': 'What makes a durable research handoff?', 'council': False}
            first = store.create(request, request_id='fixture-request')
            before = sorted(p.name for p in store.root.iterdir())
            self.assertEqual(store.create(request, request_id='fixture-request'), first)
            self.assertEqual(sorted(p.name for p in store.root.iterdir()), before)
            with self.assertRaises(ValueError):
                store.create({**request, 'question': 'A different question for the same key'}, request_id='fixture-request')
            store.update(first, status='running')
            store.recover_interrupted()
            self.assertEqual(store.create(request, request_id='fixture-request'), first)
            self.assertEqual(store.read(first)['status'], 'interrupted')

    def test_provider_metadata_has_only_four_commands_and_truthful_read_only_hints(self):
        from importlib.resources import files
        root = files('tmf_research').joinpath('mc')
        self.assertEqual(json.loads(root.joinpath('allow.json').read_text())['allow'], ['submit', 'status', 'result', 'cancel'])
        hints = json.loads(root.joinpath('tool-annotations.json').read_text())['toolAnnotations']
        self.assertEqual({key.rsplit('_', 1)[1]: value['readOnlyHint'] for key, value in hints.items()}, {'submit': False, 'status': True, 'result': True, 'cancel': False})
        import tomllib
        from pathlib import Path
        server = json.loads(root.joinpath('mcp-servers.json').read_text())['mcpServers'][0]
        command = server['args'][-1]
        scripts = tomllib.loads((Path(__file__).resolve().parents[1] / 'pyproject.toml').read_text())['project']['scripts']
        self.assertEqual(scripts[command], 'tmf_research.cli:main')
        self.assertEqual(set(hints), {f"mcp.{server['name']}/{command}_{op}" for op in ('submit', 'status', 'result', 'cancel')})
        self.assertEqual(server['probe']['tool'], command + '_status')


class WorkbenchCliTests(unittest.TestCase):
    def setUp(self):
        import threading
        from http.server import ThreadingHTTPServer
        from tmf_research import server
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = RunStore(self.temp.name)
        self.engines = []
        ready = threading.Event()
        owner = self

        class FakeEngine:
            def __init__(self, store, config):
                self.store, self.cancelled = store, threading.Event()
                self.release = threading.Event()
                self.done = threading.Event()
                owner.engines.append(self)
            def execute(self, run_id):
                self.store.update(run_id, status='running', stage='fixture')
                self.release.wait()
                self.store.update(run_id, status='cancelled' if self.cancelled.is_set() else 'completed', stage='done')
                self.done.set()

        def create(address, handler):
            self.http = ThreadingHTTPServer(address, handler)
            ready.set()
            return self.http
        self.patch_engine = patch.object(server, 'ResearchEngine', FakeEngine)
        self.patch_server = patch.object(server, 'ThreadingHTTPServer', side_effect=create)
        self.patch_engine.start(); self.patch_server.start()
        self.addCleanup(self.patch_engine.stop); self.addCleanup(self.patch_server.stop)
        self.thread = threading.Thread(target=server.serve, args=(self.temp.name,), kwargs={'port': 0}, daemon=True)
        # The service startup URL is operational output, not a CLI tool result.
        self.thread.start()
        self.assertTrue(ready.wait(2))
        self.base = f'http://127.0.0.1:{self.http.server_port}'
        self.env = patch.dict('os.environ', {'TMF_RESEARCH_URL': self.base})
        self.env.start(); self.addCleanup(self.env.stop)
        self.addCleanup(self.stop)
        from tmf_research.client import Workbench
        Workbench().request('/api/config')

    def stop(self):
        for engine in self.engines:
            engine.cancelled.set(); engine.release.set()
        for engine in self.engines: self.assertTrue(engine.done.wait(2))
        self.http.shutdown(); self.thread.join(3)
        self.assertFalse(self.thread.is_alive())

    def cli(self, *args):
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            code = main(list(args))
        self.assertEqual(errors.getvalue(), '')
        return code, json.loads(output.getvalue()), output.getvalue()

    def test_submit_retry_busy_conflict_cancel_and_memory_only_token(self):
        from tmf_research.client import Workbench
        token = Workbench().request('/api/config')['token']
        brief = json.dumps({'question': 'What makes a durable research handoff?', 'depth': 'quick', 'council': False})
        code, first, output = self.cli('submit', '--request-id', 'shared-request', '--brief-json', brief)
        self.assertEqual(code, 0)
        self.assertFalse(token in output)
        code, again, _ = self.cli('submit', '--request-id', 'shared-request', '--brief-json', brief)
        self.assertEqual(code, 0); self.assertEqual(again['id'], first['id']); self.assertTrue(again['reused'])
        self.assertEqual(len(self.engines), 1)
        self.assertFalse(json.loads((self.store.directory(first['id']) / 'brief.json').read_text())['council'])
        code, busy, _ = self.cli('submit', '--request-id', 'different-request', '--brief-json', brief)
        self.assertEqual(code, 1); self.assertEqual(busy['http_status'], 409)
        changed = json.dumps({'question': 'A changed question with the same request id'})
        code, conflict, _ = self.cli('submit', '--request-id', 'shared-request', '--brief-json', changed)
        self.assertEqual(code, 1); self.assertEqual(conflict['http_status'], 409)
        self.assertEqual(len(list(self.store.root.iterdir())), 1)
        code, cancelled, _ = self.cli('cancel', '--id', first['id'])
        self.assertEqual(code, 0); self.assertEqual(cancelled['status'], 'cancelling')
        self.assertTrue(self.engines[0].cancelled.is_set())
        self.assertFalse(self.store.read(first['id'])['status'] == 'completed')
        for file in self.store.directory(first['id']).iterdir():
            self.assertFalse(token.encode() in file.read_bytes())

    def test_result_pages_are_valid_complete_and_budget_actual_pretty_cli_output(self):
        from tmf_research.client import PAGE_BYTES
        rid = self.store.create({'question': 'What result should be retained?'})
        self.store.save(rid, 'report.json', {'title': 'Fixture', 'findings': [{'text': 'Quotes " Unicode 💡\n' * 900}]})
        self.store.save(rid, 'published-analysis.json', {'summary': 'Accepted synthesis'})
        self.store.save(rid, 'synthesis.json', {'summary': 'REJECTED_DRAFT'})
        self.store.update(rid, status='partial', outputs=['report.md'], errors=['Coverage remains partial'])
        original = (self.store.directory(rid) / 'report.json').read_bytes()
        chunks, cursor, digest = [], 0, None
        while True:
            args = ['result', '--id', rid, '--cursor', str(cursor)] + (['--sha256', digest] if digest else [])
            code, response, raw = self.cli(*args)
            self.assertEqual(code, 0); self.assertEqual(response['status'], 'partial')
            wire = {'isError': False, 'content': [{'type': 'text', 'text': raw + '\n[exit 0]'}]}
            self.assertLessEqual(len(json.dumps(wire, ensure_ascii=False).encode()), PAGE_BYTES)
            self.assertFalse('REJECTED_DRAFT' in raw)
            chunks.append(response['text']); digest = response['sha256']
            if response['next_cursor'] is None: break
            self.assertGreater(response['next_cursor'], cursor); cursor = response['next_cursor']
        whole = json.loads(''.join(chunks))
        self.assertEqual(whole['result']['analysis']['summary'], 'Accepted synthesis')
        self.assertEqual(whole['result']['report']['findings'][0]['text'], 'Quotes " Unicode 💡\n' * 900)
        self.assertEqual(original, (self.store.directory(rid) / 'report.json').read_bytes())
        self.assertEqual(len(self.engines), 0)
        self.store.save(rid, 'published-analysis.json', {'summary': 'Changed accepted revision'})
        code, changed, _ = self.cli('result', '--id', rid, '--cursor', '1', '--sha256', digest)
        self.assertEqual(code, 1); self.assertEqual(changed['http_status'], 409)

    def test_interrupted_retry_never_starts_an_engine(self):
        request = {'question': 'Preserve evidence after an interrupted job'}
        rid = self.store.create(request, request_id='interrupted')
        self.store.update(rid, status='running'); self.store.recover_interrupted()
        code, response, _ = self.cli('submit', '--request-id', 'interrupted', '--brief-json', json.dumps(request))
        self.assertEqual(code, 0); self.assertEqual(response['id'], rid); self.assertEqual(response['status'], 'interrupted')
        self.assertEqual(len(self.engines), 0)

    def test_failed_result_pages_keep_timed_out_partial_output_without_a_report(self):
        from tmf_research.client import PAGE_BYTES
        rid = self.store.create({'question': 'Read a timed-out role without retrying it'})
        diagnostics = [{'role': 'Reviewer', 'status': 'timed_out', 'elapsed_seconds': 180.1,
                        'timeout_seconds': 180, 'partial': {'stdout': 'partial 💡 "reasoning" ' * 300, 'stderr': 'bounded diagnostic'}}]
        self.store.update(rid, status='failed', timed_out_roles=diagnostics)
        chunks, cursor, digest = [], 0, None
        while True:
            args = ['result', '--id', rid, '--cursor', str(cursor)] + (['--sha256', digest] if digest else [])
            code, page, raw = self.cli(*args)
            self.assertEqual(code, 0)
            self.assertEqual(page['status'], 'failed')
            wire = {'isError': False, 'content': [{'type': 'text', 'text': raw + '\n[exit 0]'}]}
            self.assertLessEqual(len(json.dumps(wire, ensure_ascii=False).encode()), PAGE_BYTES)
            chunks.append(page['text']); digest = page['sha256']
            if page['next_cursor'] is None: break
            self.assertGreater(page['next_cursor'], cursor); cursor = page['next_cursor']
        result = json.loads(''.join(chunks))
        self.assertEqual(result['timed_out_roles'], diagnostics)
        self.assertNotIn('result', result)
        self.assertEqual(self.engines, [])

    def test_simultaneous_retry_has_one_worker_and_one_retained_run(self):
        from concurrent.futures import ThreadPoolExecutor
        from tmf_research.client import Workbench
        payload = {'question': 'Can duplicate research submission start two workers?', 'request_id': 'concurrent'}
        with ThreadPoolExecutor(max_workers=8) as pool:
            replies = list(pool.map(lambda _: Workbench().request('/api/runs', payload), range(8)))
        self.assertEqual(len({reply['id'] for reply in replies}), 1)
        self.assertEqual(sum(reply.get('reused', False) for reply in replies), 7)
        self.assertEqual(len(self.engines), 1)
        self.assertEqual(len(list(self.store.root.iterdir())), 1)

    def test_failed_response_cannot_echo_the_private_workbench_token(self):
        import urllib.request
        token = 'synthetic-private-token-sentinel'
        class Response(io.BytesIO):
            def __init__(self, status, body):
                super().__init__(json.dumps(body).encode()); self.status = status
        with patch('urllib.request.build_opener') as factory:
            factory.return_value.open.side_effect = [Response(200, {'token': token}), Response(403, {'error': 'Refused ' + token})]
            code, body, raw = self.cli('cancel', '--id', 'a' * 32)
        self.assertEqual(code, 1); self.assertEqual(body['http_status'], 403)
        self.assertFalse(token in raw); self.assertIn('[redacted]', body['reason'])
