"""The Scrapling collection plugin (plugins/scrapling) and Research's second crawler pass (Owner 2026-11-06: "add them both
as plugins"; "we make the research machine just run on plugins")."""
import hashlib
import importlib.util
import io
import json
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tmf_research.engine import ResearchEngine, RunStore
from tmf_research.providers import ProviderError
from test_engine import TEXT
from test_pre_build import FakeCrawlee, PreBuildModel, WORKSTREAM, FailIfFetched, DIGEST

spec = importlib.util.spec_from_file_location('scrapling_server', Path(__file__).resolve().parents[1] / 'plugins' / 'scrapling' / 'server.py')
server = importlib.util.module_from_spec(spec); spec.loader.exec_module(server)
PUBLIC = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.216.34', 443))]
PAGE = 'Collected page text. ' * 10


class Answer:
    def __init__(self, status, body='', url=None):
        self.status, self.body, self.url = status, body.encode(), url
    def get_all_text(self, ignore_tags=()): return self.body.decode()


class FakeFetcher:
    def __init__(self, robots=(404, ''), page=(200, PAGE)):
        self.robots, self.page, self.calls = robots, page, []
    def get(self, url, **kw):
        self.calls.append((url, kw))
        status, body = self.robots if url.endswith('/robots.txt') else self.page
        return Answer(status, body, url)


class FakeStealthy:
    def __init__(self): self.calls = []
    def fetch(self, url, **kw): self.calls.append(kw); return Answer(200, PAGE, url)


class ServerTests(unittest.TestCase):
    def collector(self, **kw):
        fetcher, stealthy = FakeFetcher(**kw), FakeStealthy()
        return server.Collector(fetcher, stealthy, 'fixture'), fetcher, stealthy

    @patch('socket.getaddrinfo', return_value=PUBLIC)
    def test_a_page_is_collected_with_its_hash_and_fetcher(self, _):
        c, fetcher, _s = self.collector()
        got = c.fetch('https://example.com/docs')
        self.assertEqual([got['fetcher'], got['text_sha256']], ['Fetcher', hashlib.sha256(PAGE.encode()).hexdigest()])
        self.assertEqual(fetcher.calls[0][0], 'https://example.com/robots.txt', 'robots.txt is read before the page')

    @patch('socket.getaddrinfo', return_value=PUBLIC)
    def test_robots_is_honoured_and_an_unreadable_policy_fails_closed(self, _):
        c, *_ = self.collector(robots=(200, 'User-agent: *\nDisallow: /'))
        with self.assertRaisesRegex(server.Refused, 'disallows'): c.fetch('https://example.com/docs')
        c, *_ = self.collector(robots=(503, ''))
        with self.assertRaisesRegex(server.Refused, 'fails closed'): c.fetch('https://example.com/docs')

    @patch('socket.getaddrinfo', return_value=PUBLIC)
    def test_a_refused_plain_fetch_uses_the_stealthy_fetcher_without_challenge_solving(self, _):
        c, _f, stealthy = self.collector(page=(403, ''))
        got = c.fetch('https://example.com/docs')
        self.assertEqual(got['fetcher'], 'StealthyFetcher')
        self.assertIs(stealthy.calls[0]['solve_cloudflare'], False)

    def test_only_public_https_is_collected(self):
        with patch('socket.getaddrinfo', return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('127.0.0.1', 443))]):
            with self.assertRaisesRegex(server.Refused, 'non-public'): server.public_url('https://localhost/x')
        with self.assertRaisesRegex(server.Refused, 'HTTPS'): server.public_url('http://example.com/x')

    def test_the_mcp_surface_lists_read_only_tools_and_reports_refusals_as_errors(self):
        c, *_ = self.collector(robots=(200, 'User-agent: *\nDisallow: /'))
        out = io.StringIO()
        lines = '\n'.join(json.dumps(m) for m in [{'id': 1, 'method': 'tools/list'},
                                                   {'id': 2, 'method': 'tools/call', 'params': {'name': 'scrapling_status', 'arguments': {}}},
                                                   {'id': 3, 'method': 'tools/call', 'params': {'name': 'scrapling_fetch', 'arguments': {'url': 'https://example.com/a'}}}])
        with patch('socket.getaddrinfo', return_value=PUBLIC): server.main(io.StringIO(lines + '\n'), out, lambda: c)
        replies = [json.loads(x) for x in out.getvalue().splitlines()]
        self.assertTrue(all(t['annotations']['readOnlyHint'] for t in replies[0]['result']['tools']))
        self.assertFalse(replies[1]['result']['isError'])
        self.assertTrue(replies[2]['result']['isError'])
        self.assertIn('disallows', replies[2]['result']['content'][0]['text'])


class ScopedCollectorTests(unittest.TestCase):
    @patch('socket.getaddrinfo',return_value=PUBLIC)
    def test_scoped_collection_does_not_follow_redirects_or_start_browser_fallback(self,_):
        fetcher=FakeFetcher();stealth=FakeStealthy();collector=server.Collector(fetcher,stealth,'fixture')
        collector.fetch('https://example.com/docs',permitted_domains=['example.com'])
        self.assertTrue(all(kwargs['follow_redirects'] is False for _,kwargs in fetcher.calls))
        self.assertEqual(stealth.calls,[])
        prior=len(fetcher.calls)
        with self.assertRaises(server.Refused):collector.fetch('https://outside.example/docs',permitted_domains=['example.com'])
        self.assertEqual(len(fetcher.calls),prior)
        blocked=server.Collector(FakeFetcher(page=(302,'')),stealth,'fixture')
        with self.assertRaisesRegex(server.Refused,'Scoped plain collection unavailable'):
            blocked.fetch('https://example.com/docs',permitted_domains=['example.com'])
        self.assertEqual(stealth.calls,[])


class BlockedSiteCrawlee(FakeCrawlee):
    """example.com collects; blocked.example cannot (its Crawlee job fails)."""
    def call(self, name, args):
        if name == 'crawlee_start':
            self.calls.append((name, args)); return {'id': 'job-' + args['allowed_domains'][0]}
        if name == 'crawlee_status' and args['job_id'] == 'job-blocked.example':
            self.calls.append((name, args)); return {'status': 'failed', 'reason': 'HTTP 403 from the site', 'sources': []}
        return super().call(name, args)


class FakeScraplingPlugin:
    def __init__(self, mode='ok'): self.mode, self.calls = mode, []
    def call(self, name, args):
        self.calls.append((name, args))
        if self.mode == 'down': raise ProviderError('The Scrapling plugin could not start (FileNotFoundError)')
        if name == 'scrapling_status': return {'available': True, 'version': '0.5.1'}
        text = TEXT + ' Blocked site text.'
        digest = 'f' * 64 if self.mode == 'tampered' else hashlib.sha256(text.encode()).hexdigest()
        return {'url': args['url'], 'final_url': args['url'], 'text': text, 'text_sha256': digest, 'fetcher': 'StealthyFetcher', 'retrieved_at': '2026-11-06T00:00:00Z'}
    def close(self): pass


class SwarmTests(unittest.TestCase):
    def run_job(self, mode='ok'):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        store = RunStore(tmp.name)
        rid = store.create({'question': 'What does the TMF website need before the builders build it?', 'preset': 'pre-build',
                            'workstream': {**WORKSTREAM, 'references': ['https://example.com/inspiration', 'https://blocked.example/pricing']}})
        engine = ResearchEngine(store, model=PreBuildModel(), web=FailIfFetched(), crawlee=BlockedSiteCrawlee())
        plugins = []
        engine.scrapling_factory = lambda: plugins.append(FakeScraplingPlugin(mode)) or plugins[-1]
        engine.execute(rid)
        return store, rid, plugins

    def test_scrapling_collects_only_the_site_crawlee_could_not_and_provenance_names_the_crawler(self):
        store, rid, plugins = self.run_job()
        result = json.loads((store.directory(rid) / 'pre-build.json').read_text())
        acquisition = result['acquisition']
        self.assertEqual(acquisition['crawlers'], ['crawlee', 'scrapling'])
        self.assertEqual(acquisition['scrapling']['sites'], ['blocked.example'])
        fetched = [args['url'] for p in plugins for name, args in p.calls if name == 'scrapling_fetch']
        self.assertEqual(fetched, ['https://blocked.example/pricing'], 'example.com was collected by Crawlee, so Scrapling never fetched it')
        by_crawler = {s['crawler']: s for s in result['sources'] if s.get('state') == 'available'}
        self.assertEqual(by_crawler['crawlee']['artifact_sha256'], DIGEST)
        self.assertEqual(by_crawler['scrapling']['fetcher'], 'StealthyFetcher')
        self.assertIn(by_crawler['scrapling']['artifact_sha256'], acquisition['sourceHashes'])

    def test_an_unavailable_plugin_is_said_by_name_and_a_tampered_text_is_never_evidence(self):
        store, rid, _ = self.run_job('down')
        self.assertTrue(any('Scrapling plugin unavailable' in e for e in store.read(rid)['errors']), store.read(rid)['errors'])
        self.assertIn('unavailable', json.loads((store.directory(rid) / 'pre-build.json').read_text())['acquisition']['scrapling'])
        store, rid, _ = self.run_job('tampered')
        sources = json.loads((store.directory(rid) / 'pre-build.json').read_text())['sources']
        self.assertEqual([s['state'] for s in sources if s.get('crawler') == 'scrapling'], ['unavailable'])


if __name__ == '__main__':
    unittest.main()
