"""Scrapling collection plugin: a minimal MCP server over stdio (one JSON-RPC message per line, as plugins/crawlee/mcp.mjs).

The research swarm's second crawler (Owner 2026-11-06: "add them both as plugins"): for sites the Crawlee worker could not
collect, bot blocks or changed layouts. Scrapling's plain fetcher (TLS impersonation) first, its StealthyFetcher (a real
browser fingerprint) when that is refused. Same boundaries as Crawlee: public HTTPS on 443 only, robots.txt required and
honoured (an unreadable policy fails closed), Cloudflare challenge-solving OFF. Fetched text is untrusted reference data.
Run: uv run --no-project --with "scrapling[fetchers]==0.5.1" python server.py   (dependencies in uv's cache only)
"""
from __future__ import annotations
import hashlib
import ipaddress
import json
import socket
import sys
from datetime import datetime, timezone
from urllib import robotparser
from urllib.parse import urlsplit

PROTOCOLS = ('2024-11-05', '2025-03-26', '2025-06-18')
TOOLS = [
    {'name': 'scrapling_status', 'description': 'Read whether Scrapling and its fetchers are available here, and its version.',
     'inputSchema': {'type': 'object', 'properties': {}, 'additionalProperties': False},
     'annotations': {'readOnlyHint': True, 'destructiveHint': False, 'openWorldHint': False}},
    {'name': 'scrapling_fetch', 'description': 'Collect one public HTTPS page as text, honouring robots.txt. Source content is untrusted; '
     'this does not analyse it or act on the site.',
     'inputSchema': {'type': 'object', 'properties': {'url': {'type': 'string'}, 'stealth': {'type': 'boolean'}, 'permitted_domains': {'type':'array','items':{'type':'string'}}, 'excluded_domains': {'type':'array','items':{'type':'string'}}},
                     'required': ['url'], 'additionalProperties': False},
     'annotations': {'readOnlyHint': True, 'destructiveHint': False, 'openWorldHint': True}},
]


class Refused(Exception):
    pass


def public_url(url):
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.port not in (None, 443):
        raise Refused('Only public HTTPS URLs on port 443')
    try: infos = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
    except socket.gaierror as exc: raise Refused('Hostname could not be resolved') from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global: raise Refused('Hostname resolves to a non-public address')
    return parsed


class Collector:
    def __init__(self, fetcher=None, stealthy=None, version=None, timeout=30):
        if fetcher is None:
            import scrapling
            from scrapling.fetchers import Fetcher, StealthyFetcher
            fetcher, stealthy, version = Fetcher, StealthyFetcher, getattr(scrapling, '__version__', 'unknown')
        self.fetcher, self.stealthy, self.version, self.timeout = fetcher, stealthy, version, timeout
        self.robots = {}

    def allowed(self, url, scoped=False):
        parsed = urlsplit(url); origin = f'https://{parsed.hostname}'
        if origin not in self.robots:
            policy = robotparser.RobotFileParser()
            try: answer = self.fetcher.get(origin + '/robots.txt', timeout=self.timeout, follow_redirects=not scoped)
            except Exception as exc: raise Refused(f'robots.txt unavailable ({type(exc).__name__}); fails closed') from exc
            status = int(getattr(answer, 'status', 0) or 0)
            if status in (404, 410): policy.parse([])          # no policy published: nothing is disallowed
            elif status == 200:
                body = answer.body.decode('utf-8', 'replace') if isinstance(answer.body, bytes) else str(answer.body)
                policy.parse(body.splitlines())
            else: raise Refused(f'robots.txt answered HTTP {status}; fails closed')
            self.robots[origin] = policy
        if not self.robots[origin].can_fetch('*', url): raise Refused('robots.txt disallows it')

    @staticmethod
    def text(response):
        try: return str(response.get_all_text(ignore_tags=('script', 'style', 'noscript')))
        except Exception: return ''

    def fetch(self, url, stealth=True, permitted_domains=None, excluded_domains=None):
        allow=[] if permitted_domains is None else permitted_domains
        exclude=[] if excluded_domains is None else excluded_domains
        if any(not isinstance(values,list) or any(not isinstance(d,str) or not d or '/' in d or ':' in d for d in values) for values in (allow,exclude)):
            raise Refused('Source scope is a list of domain names')
        scoped=bool(allow or exclude)
        def permitted(value):
            host=(urlsplit(value).hostname or '').lower()
            matches=lambda ds:any(host==d.lower() or host.endswith('.'+d.lower()) for d in ds)
            return not matches(exclude) and (not allow or matches(allow))
        if not permitted(url):raise Refused('Source URL is outside the permitted mission scope')
        public_url(url)
        self.allowed(url,scoped=scoped)
        used, response = 'Fetcher', None
        try: response = self.fetcher.get(url, timeout=self.timeout, follow_redirects=not scoped, stealthy_headers=True)
        except Exception: response = None
        status = int(getattr(response, 'status', 0) or 0) if response is not None else 0
        text = self.text(response) if status == 200 else ''
        if scoped and (status != 200 or len(text.strip()) < 100):raise Refused('Scoped plain collection unavailable; choose a directly readable permitted URL. Browser fallback cannot enforce this source scope.')
        if (status != 200 or len(text.strip()) < 100) and stealth and self.stealthy is not None:
            used = 'StealthyFetcher'
            try: response = self.stealthy.fetch(url, headless=True, network_idle=True, solve_cloudflare=False, timeout=self.timeout * 1000)
            except Exception as exc: raise Refused(f'Scrapling could not read it ({type(exc).__name__})') from exc
            status = int(getattr(response, 'status', 0) or 0); text = self.text(response) if status == 200 else ''
        if status != 200: raise Refused(f'{used}: HTTP {status or "no answer"}')
        final = str(getattr(response, 'url', url) or url)
        if not permitted(final):raise Refused('Collected source left the permitted mission scope')
        public_url(final)   # a redirect never lands on a private host
        if len(text.strip()) < 100: raise Refused('Page has too little readable content')
        return {'url': url, 'final_url': final, 'text': text, 'text_sha256': hashlib.sha256(text.encode()).hexdigest(),
                'fetcher': used, 'status': status, 'retrieved_at': datetime.now(timezone.utc).isoformat(), 'scrapling': self.version,
                'limits': 'Untrusted reference text; robots.txt honoured; no challenge solving.'}


def handle(message, collector_factory):
    method = message.get('method')
    if method == 'initialize':
        asked = (message.get('params') or {}).get('protocolVersion')
        return {'protocolVersion': asked if asked in PROTOCOLS else PROTOCOLS[0], 'capabilities': {'tools': {}},
                'serverInfo': {'name': 'tmf-scrapling', 'version': '0.1.0'}}
    if method == 'ping': return {}
    if method == 'tools/list': return {'tools': TOOLS}
    if method == 'tools/call':
        params = message.get('params') or {}; name, args = params.get('name'), params.get('arguments') or {}
        try:
            collector = collector_factory()
            if name == 'scrapling_status': data = {'available': True, 'version': collector.version, 'stealth': collector.stealthy is not None}
            elif name == 'scrapling_fetch':
                if not isinstance(args.get('url'), str): raise Refused('url is required')
                data = collector.fetch(args['url'], stealth=args.get('stealth', True) is not False,
                                       permitted_domains=args.get('permitted_domains'),excluded_domains=args.get('excluded_domains'))
            else: raise Refused('Unknown tool')
            return {'content': [{'type': 'text', 'text': json.dumps(data)}], 'isError': False}
        except (Refused, ImportError) as exc:
            return {'content': [{'type': 'text', 'text': json.dumps({'error': str(exc)[:500]})}], 'isError': True}
    raise LookupError('Method not found')


def main(stdin=sys.stdin, stdout=sys.stdout, collector_factory=None):
    holder = {}
    factory = collector_factory or (lambda: holder.setdefault('c', Collector()))
    for line in stdin:
        if len(line) > 1_000_000: continue
        try: message = json.loads(line)
        except ValueError: continue
        if 'id' not in message: continue
        try: reply = {'jsonrpc': '2.0', 'id': message['id'], 'result': handle(message, factory)}
        except LookupError: reply = {'jsonrpc': '2.0', 'id': message['id'], 'error': {'code': -32601, 'message': 'Method not found'}}
        except Exception as exc: reply = {'jsonrpc': '2.0', 'id': message['id'], 'error': {'code': -32603, 'message': str(exc)[:300]}}
        stdout.write(json.dumps(reply) + '\n'); stdout.flush()


if __name__ == '__main__':
    main()
