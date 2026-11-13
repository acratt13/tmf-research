"""Candidate-only publication through Canon's existing keyed section entry door.

No knowledge store or credential discovery lives here. The operator supplies the
connection; research content can never select a destination or authorization.
"""
import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from urllib.parse import urlsplit, urlunsplit

from .cli import validate
from .client import NoRedirect


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def digest(value):
    return hashlib.sha256(encoded(value).encode()).hexdigest()


def stable_id(key):
    """Canon db/canonDb.ts stableId, not a new identity algorithm."""
    h = hashlib.sha256(key.encode()).hexdigest()
    return f'cn-{h[:8]}-{h[8:12]}-4{h[13:16]}-8{h[17:20]}-{h[20:32]}'


class CanonUnavailable(ValueError):
    pass


class CanonConnection:
    def __init__(self, config):
        cfg = config.get('canon') or {}
        base = cfg.get('url', '')
        try:
            url = urlsplit(base)
            valid = (url.scheme == 'http' and url.hostname == '127.0.0.1' and url.port
                     and not url.username and not url.password and not url.query
                     and not url.fragment and url.path in ('', '/'))
        except ValueError:
            valid = False
        scope = cfg.get('identity_scope')
        token_name = cfg.get('token_env', '')
        if not valid or not isinstance(scope, str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}', scope):
            raise CanonUnavailable('Canon connection unavailable: configure loopback URL and stable identity_scope')
        if not isinstance(token_name, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', token_name):
            raise CanonUnavailable('Canon connection unavailable: configure token_env by name')
        self.token = os.environ.get(token_name)
        if not self.token:
            raise CanonUnavailable('Canon connection unavailable: named authorization is missing')
        self.base, self.scope = base.rstrip('/'), scope
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def request(self, path, payload=None):
        data = encoded(payload).encode() if payload is not None else None
        request = urllib.request.Request(self.base + path, data=data, headers={
            'Content-Type': 'application/json', 'Authorization': 'Bearer ' + self.token})
        try:
            with self.opener.open(request, timeout=5) as response:
                raw = response.read(8 * 1024 * 1024 + 1)
                if len(raw) > 8 * 1024 * 1024:
                    raise CanonUnavailable('Canon response exceeds the bounded read')
                return json.loads(raw)
        except urllib.error.HTTPError as exc:
            # Never echo a server response that may contain credentials or source text.
            status = exc.code
            exc.close()
            raise CanonUnavailable(f'Canon refused publication (HTTP {status}); retry after resolving the connection or revision conflict') from None
        except (OSError, ValueError, urllib.error.URLError):
            raise CanonUnavailable('Canon connection unavailable or response unreadable') from None

    def put(self, key, title, payload, links):
        body = encoded(payload)
        fields = {'source': 'tmf-research', 'sourceId': key, 'sourceHash': digest(payload),
                  'status': 'draft', 'reviewStatus': 'candidate'}
        entry = self.request('/api/canon/sections/knowledge/entries', {
            'key': key, 'type': 'knowledge', 'title': title, 'body': body, 'fields': fields, 'links': links})
        if (entry.get('id') != stable_id(key) or entry.get('fields', {}).get('sourceId') != key
                or not isinstance(entry.get('revision'), int)):
            raise CanonUnavailable('Canon identity receipt did not match the candidate')
        prior = entry['fields']
        unchanged = (entry.get('body') == body and prior.get('sourceHash') == digest(payload)
                     and all(x in entry.get('links', []) for x in links))
        # Accepted knowledge may be cited again; it must never be demoted or edited.
        if unchanged and prior.get('source') == 'tmf-research':
            return {'id': entry['id'], 'revision': entry['revision']}
        if prior.get('source') != 'tmf-research' or prior.get('status') != 'draft' or prior.get('reviewStatus') != 'candidate':
            raise CanonUnavailable('Canon candidate has been reviewed or changed; publication will not overwrite it')
        if entry.get('body') != body or not all(x in entry.get('links', []) for x in links):
            # Retain human edits: even a still-draft entry is not ours to replace blindly.
            try:
                owned = digest(json.loads(entry['body'])) == prior.get('sourceHash')
            except (ValueError, KeyError, TypeError):
                owned = False
            if not owned:
                raise CanonUnavailable('Canon candidate content changed outside Research; review is required')
            entry = self.request('/api/canon/sections/knowledge/entries', {
                'id': entry['id'], 'expectedRevision': entry['revision'], 'title': title,
                'body': body, 'fields': {**prior, **fields},
                'links': list({(x['to'], x['kind']): x for x in entry.get('links', []) + links}.values())})
        if (entry.get('id') != stable_id(key) or not isinstance(entry.get('revision'), int)
                or entry.get('body') != body or entry.get('fields', {}).get('sourceHash') != digest(payload)
                or not all(x in entry.get('links', []) for x in links)):
            raise CanonUnavailable('Canon did not retain the requested candidate revision')
        return {'id': entry['id'], 'revision': entry['revision']}


def source_identity(source):
    if source.get('url'):
        url = urlsplit(source['url'])
        host = url.hostname.lower()
        port = url.port
        netloc = ('[' + host + ']') if ':' in host else host
        if port and (url.scheme, port) not in (('https', 443), ('http', 80)):
            netloc += ':' + str(port)
        return 'url:' + urlunsplit((url.scheme.lower(), netloc, url.path or '/', url.query, ''))
    if source.get('artifact_sha256'):
        return 'artifact:' + source['artifact_sha256']
    # Unidentified sources remain mission-local rather than guessing entity equivalence.
    return None


def publication_status(store, run_id, config):
    path = store.directory(run_id) / 'canon-publication.json'
    if path.exists():
        return json.loads(path.read_text())
    try:
        CanonConnection(config)
        return {'status': 'not-published', 'review_status': 'candidate'}
    except CanonUnavailable as exc:
        return {'status': 'unavailable', 'reason': str(exc)}


def publish_candidates(store, run_id, config, check=lambda: None):
    """Retry-safe effects; receipts are diagnostic run artifacts, never authority."""
    state = store.read(run_id)
    if state['status'] not in ('completed', 'partial'):
        raise ValueError('Only a finished retained report can be published')
    report = validate(json.loads((store.directory(run_id) / 'report.json').read_text()))
    claims_file = store.directory(run_id) / 'claims.json'
    claims = json.loads(claims_file.read_text()) if claims_file.exists() else []
    receipt = {'status': 'unavailable', 'review_status': 'candidate', 'run_id': run_id,
               'report_sha256': digest(report), 'research_status': state['status'], 'references': []}
    try:
        connection = CanonConnection(config)
        prefix = 'tmf-research:v1:' + connection.scope + ':'
        mission_key = prefix + 'mission:' + run_id
        sources = {}
        for source in report['sources']:
            check()
            identity = source_identity(source) or 'mission:' + run_id + ':source:' + source['id']
            key = prefix + 'source:' + hashlib.sha256(identity.encode()).hexdigest()
            # Observation snapshots are immutable-by-key; different missions retain their own evidence.
            observation = {'entity': 'source', 'identity': identity, 'evidence': source,
                           'verification': 'source-state-only; not independent factual verification'}
            identity_ref = connection.put(key, 'Research source identity: ' + identity,
                                          {'entity': 'source-identity', 'identity': identity, 'verification': 'identity-only'}, [])
            receipt['references'].append({'kind': 'source-identity', **identity_ref})
            store.save(run_id, 'canon-publication.json', {**receipt, 'status': 'partial'})
            ref = connection.put(key + ':' + digest(observation), 'Research source candidate: ' + source['title'], observation, [{'to': identity_ref['id'], 'kind': 'source'}])
            sources[source['id']] = ref
            receipt['references'].append({'kind': 'source', 'local_id': source['id'], 'identity': identity_ref, **ref})
            store.save(run_id, 'canon-publication.json', {**receipt, 'status': 'partial'})
        findings = []
        for finding in report['findings']:
            check()
            refs = [{'local_id': sid, **sources[sid]} for sid in finding.get('sources', [])]
            reviews = [c for c in claims if c.get('text') == finding['text'] and c.get('label') == finding['label']
                       and c.get('sources') == finding.get('sources', []) and c.get('published') is not False
                       and c.get('review') in ('supported', 'proposal')]
            payload = {'entity': 'finding', 'finding': finding, 'source_revisions': refs,
                       'retained_reviews': reviews, 'verification': 'model-reviewed' if reviews else 'unreviewed',
                       'independent_verification': False}
            key = mission_key + ':finding:' + digest(payload)
            ref = connection.put(key, 'Research finding candidate: ' + finding['text'][:160], payload,
                                 [{'to': r['id'], 'kind': 'supported-by'} for r in refs])
            findings.append(ref)
            receipt['references'].append({'kind': 'finding', **ref})
            store.save(run_id, 'canon-publication.json', {**receipt, 'status': 'partial'})
        check()
        payload = {'entity': 'research-mission', 'run_id': run_id, 'research_status': state['status'],
                   'report_sha256': digest(report), 'report': report, 'source_revisions': sources,
                   'finding_revisions': findings, 'verification': 'candidate; no independent certification',
                   'output_references': [{'run_id': run_id, 'name': name} for name in state.get('outputs', [])]}
        links = [{'to': r['id'], 'kind': 'source'} for r in sources.values()]
        links += [{'to': r['id'], 'kind': 'related'} for r in findings]
        # Preserve an immutable report snapshot as well as the mission's revisioned head.
        snapshot = connection.put(mission_key + ':report:' + digest(payload), 'Research report candidate: ' + report['title'], payload, links)
        mission = connection.put(mission_key, 'Research mission candidate: ' + report['title'], payload,
                                 links + [{'to': snapshot['id'], 'kind': 'source'}])
        receipt.update(status='published-candidate', mission=mission, snapshot=snapshot)
    except CanonUnavailable as exc:
        receipt.update(status='partial' if receipt['references'] else 'unavailable', reason=str(exc))
    except InterruptedError:
        receipt.update(status='partial' if receipt['references'] else 'cancelled', reason='Publication interrupted; retry reuses keyed identities')
    store.save(run_id, 'canon-publication.json', receipt)
    return receipt


def recover_publications(store):
    """A process exit stops publication, never restarts research or repeats writes."""
    for file in store.root.glob('*/state.json'):
        try:
            state = json.loads(file.read_text())
            if state.get('canon_activity') != 'publishing':
                continue
            path = file.parent / 'canon-publication.json'
            receipt = json.loads(path.read_text()) if path.exists() else {}
            if receipt.get('status') != 'published-candidate':
                store.save(state['id'], 'canon-publication.json', {**receipt,
                    'status': 'partial' if receipt.get('references') else 'interrupted',
                    'reason': 'Process restarted during publication; retry reuses keyed identities'})
            store.update(state['id'], canon_activity=None)
        except (ValueError, KeyError, OSError):
            continue
