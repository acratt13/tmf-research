"""Short CLI requests to the existing workbench; it alone owns research execution."""
import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from urllib.parse import urlsplit
from .cli import dump

MAX_RESPONSE = 8 * 1024 * 1024
PAGE_BYTES = 2400


class WorkbenchError(ValueError):
    def __init__(self, reason, status=None):
        super().__init__(reason)
        self.status = status


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Workbench:
    def __init__(self):
        value = os.environ.get('TMF_RESEARCH_URL', 'http://127.0.0.1:8765')
        parsed = urlsplit(value)
        if (parsed.scheme != 'http' or parsed.hostname != '127.0.0.1' or not parsed.port
                or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('', '/')):
            raise ValueError('Configure a loopback workbench URL without credentials or a path')
        self.base = value.rstrip('/')
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        self.token = None

    def request(self, path, payload=None):
        headers = {'Origin': self.base}
        if payload is not None:
            self.token = self.request('/api/config').get('token')
            if not isinstance(self.token, str) or not self.token:
                raise WorkbenchError('Workbench authorization is unavailable')
            headers.update({'Content-Type': 'application/json', 'X-TMF-Token': self.token})
        data = json.dumps(payload).encode() if payload is not None else None
        try:
            response = self.opener.open(urllib.request.Request(self.base + path, data=data, headers=headers), timeout=5)
        except urllib.error.HTTPError as exc:
            response = exc
        except (OSError, urllib.error.URLError):
            raise WorkbenchError('Research workbench is not reachable') from None
        with response:
            raw = response.read(MAX_RESPONSE + 1)
            if len(raw) > MAX_RESPONSE:
                raise WorkbenchError('Workbench response exceeds the bounded read; original artifacts remain in Research')
            if self.token and path != '/api/config':
                raw = raw.replace(self.token.encode(), b'[redacted]')
            try: value = json.loads(raw)
            except (ValueError, UnicodeError): raise WorkbenchError('Workbench returned an unreadable response') from None
            if response.status >= 400:
                raise WorkbenchError(value.get('error', 'Workbench refused this request') if isinstance(value, dict) else 'Workbench refused this request', response.status)
            return value


def run_id(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-f0-9]{32}', value):
        raise ValueError('Use the saved research run id')
    return value


def page(value, status, cursor=0, expected_hash=None):
    """A document range, never a cut JSON envelope. The original remains with Research."""
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    digest = hashlib.sha256(text.encode()).hexdigest()
    if expected_hash and expected_hash != digest:
        raise WorkbenchError('Research result changed; read from cursor zero', 409)
    if not 0 <= cursor <= len(text): raise ValueError('Cursor is outside the result')
    def answer(end):
        return {'status': status, 'content_type': 'application/json', 'text': text[cursor:end],
                'cursor': cursor, 'next_cursor': end if end < len(text) else None, 'total_chars': len(text), 'sha256': digest}
    low, high = cursor, min(len(text), cursor + PAGE_BYTES)
    while low < high:
        end = (low + high + 1) // 2
        result = answer(end)
        # Include the existing shim's text wrapper and JSON escaping, not just document bytes.
        wire = {'isError': False, 'content': [{'type': 'text', 'text': dump(result) + '\n[exit 0]'}]}
        if len(json.dumps(wire, ensure_ascii=False).encode()) <= PAGE_BYTES: low = end
        else: high = end - 1
    if low == cursor and cursor < len(text): raise ValueError('Result metadata exceeds the page budget')
    return answer(low)


def execute(args):
    if getattr(args, 'cursor', 0) and not getattr(args, 'sha256', None):
        raise ValueError('Continue a result with its previous page hash')
    workbench = Workbench()
    if args.command == 'submit':
        request = json.loads(args.brief_json)
        if not isinstance(request, dict): raise ValueError('Research brief must be an object')
        if 'request_id' in request: raise ValueError('Supply the stable request id as --request-id')
        return workbench.request('/api/runs', {**request, 'request_id': args.request_id})
    if args.command == 'cancel':
        return workbench.request('/api/cancel', {'id': run_id(args.id)})
    if args.command == 'status':
        value = workbench.request('/api/runs/' + run_id(args.id)) if args.id else workbench.request('/api/runs')
        return page(value, value['status'] if args.id else 'available', args.cursor, args.sha256)
    state = workbench.request('/api/runs/' + run_id(args.id))
    result = {'state': state, 'artifacts': [{'name': name, 'url': f'{workbench.base}/outputs/{args.id}/{name}'} for name in state.get('outputs', [])]}
    if state['status'] in ('completed', 'partial'):
        try: result['result'] = workbench.request('/api/result/' + args.id)
        except WorkbenchError as exc:
            if exc.status != 404: raise
            result['unavailable'] = 'No retained report is available for this run'
    return page(result, state['status'], args.cursor, args.sha256)
