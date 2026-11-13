"""TMF Council: durable, bounded, evidence-first research orchestration."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import shutil
import threading
import time
from urllib.parse import urlsplit
import uuid

from .cli import dump, validate, REA_OPERATIONS
from .missions import normalize as mission_input, permits, output_instruction, validate_output
from .providers import CodexModel, Crawlee, PublicWeb, ProviderError, ScraplingPlugin
from .processes import bounded_run, retained_diagnostic

LENSES = {
    'understand': 'Explain the system and its complete workflow.',
    'compare': 'Compare credible alternatives against explicit criteria; disclose missing data.',
    'build': 'Identify records, interfaces, hidden rules, failures and acceptance requirements.',
    'audit': 'Identify evidenced gaps, impact and remediation; do not invent an audit of an untested system.',
    'offer': 'Assess buyer evidence, scope, costs, support and commercial unknowns; do not invent demand or prices.',
}
FORMATS = ('md', 'html', 'pdf', 'docx', 'xlsx', 'pptx', 'diagram', 'builder')
DEPTHS = {'quick': {'sources': 4, 'rounds': 0, 'calls': 16},
          'detailed': {'sources': 8, 'rounds': 1, 'calls': 24},
          'deep': {'sources': 12, 'rounds': 2, 'calls': 32}}
PRESETS = {'tmf-service-blueprint': {'lenses': list(LENSES), 'depth': 'deep',
                                    'formats': ['md', 'html', 'pdf', 'docx', 'xlsx', 'pptx', 'diagram', 'builder'], 'council': True},
           # PRE-BUILD (Owner 2026-11-05, Canon cn-bdaf883f): research for a builders' workstream before it is built. A fast
           # parallel Crawlee swarm, quick depth, the Workstream Council, REA only for a teardown the brief asks for, and the
           # workstream's spec doc in chapters. A launcher passes the preset only; what it means lives here.
           'pre-build': {'lenses': ['build', 'understand'], 'depth': 'quick', 'formats': ['builder', 'md'], 'council': True,
                         'council_members': ['systems', 'fullstack', 'design', 'customer', 'challenger', 'canon'],
                         'council_auto_experts': True, 'limits': {'sources': 20, 'calls': 30}}}
PRE_BUILD_SCHEMA = 'mc-pre-build/1'
# The workstream doc's chapters (cn-bdaf883f "DOC OUT"): industry PRD + technical design; chapters = epics, never tickets.
SPEC_CHAPTERS = [('summary', 'Summary: goal, done, out of scope'), ('what-exists', 'What exists (sourced)'),
                 ('research', 'Research (sourced: references, how others do it, teardowns)'),
                 ('requirements', 'Requirements: user stories + acceptance criteria'), ('design', 'Design')]
WORKSTREAM_TEXT = {'id': 128, 'ticket': 128, 'goal': 3000, 'whoFor': 1000}
WORKSTREAM_LISTS = ('existing', 'references', 'constraints', 'unknowns')
COUNCIL = [
    ('Customer advocate', 'Challenge buyer need, usefulness, adoption and evidence of demand.'),
    ('Delivery architect', 'Challenge data models, integrations, edge cases and acceptance feasibility.'),
    ('Operations economist', 'Challenge ongoing ownership, support burden, cost assumptions and economics.'),
    ('Assumptions challenger', 'Seek counterexamples, simpler alternatives and missing evidence.'),
]
COUNCIL_SPECIALISTS = {
    'customer': COUNCIL[0],
    'systems': COUNCIL[1],
    'business': COUNCIL[2],
    'challenger': COUNCIL[3],
    'fullstack': ('Full-stack specialist', 'Challenge implementation seams, data contracts, tests and recovery behavior.'),
    'design': ('Design systems specialist', 'Challenge tokens, component consistency, tool interoperability, live collaboration and accessibility.'),
    'growth': ('Marketing and SEO specialist', 'Challenge positioning, discoverability, distribution and measurable acquisition evidence.'),
    'canon': ('Canon keeper', 'Check every proposal against what already exists and what the Owner decided (the brief\'s workstream.existing). '
              'Name each rebuild of something that exists and each contradiction of a decision, quoting the line it contradicts.'),
}
DEFAULT_COUNCIL = ['customer', 'systems', 'business', 'challenger']


def council_roles(request, experts):
    selected = [COUNCIL_SPECIALISTS[key] for key in request['council_members']]
    selected += [(s['name'], s['responsibilities']) for s in request.get('mission', {}).get('specialists', [])]
    if request['council_auto_experts']:
        selected += [(str(x.get('role', 'Domain specialist'))[:80],
                      str(x.get('lens', 'Subject-specific gaps'))[:300])
                     for x in experts[:2] if isinstance(x, dict)]
    return list(dict.fromkeys(selected))


def timestamp(): return datetime.now(timezone.utc).isoformat()


def source_passages(text, query, budget=16000):
    """Select located windows across a snapshot instead of dropping its tail."""
    if len(text) <= budget: return text
    ignored={'what','must','with','from','that','this','which','their','should','include','using','into','before','after','does','research','service','proposed'}
    terms={w for w in re.findall(r'[a-z]{4,}',query.lower()) if w not in ignored}
    windows=[(i,text[i:i+1400]) for i in range(0,len(text),1200)]
    ranked=sorted(windows,key=lambda row:(-sum(t in row[1].lower() for t in terms),row[0]))
    selected={0:windows[0][1]};used=len(windows[0][1])+80
    for offset,window in ranked:
        if offset in selected: continue
        if used+len(window)+80>budget: continue
        selected[offset]=window;used+=len(window)+80
    return '\n\n'.join(f'[Snapshot characters {offset}:{offset+len(window)}]\n{window}' for offset,window in sorted(selected.items()))


def workstream(value):
    """A builders' workstream brief (cn-bdaf883f BRIEF IN): text fields and short lists, bounded."""
    if not isinstance(value, dict): raise ValueError('The pre-build preset needs a workstream object')
    out = {}
    for key, limit in WORKSTREAM_TEXT.items():
        item = value.get(key, '')
        if not isinstance(item, str) or len(item) > limit: raise ValueError(f'workstream.{key} must be text of at most {limit} characters')
        if item.strip(): out[key] = item.strip()
    if 'goal' not in out: raise ValueError('workstream.goal is required')
    for key in WORKSTREAM_LISTS:
        items = value.get(key, [])
        if not isinstance(items, list) or len(items) > 40 or any(not isinstance(x, str) or len(x) > 2000 for x in items):
            raise ValueError(f'workstream.{key} must be at most 40 texts of at most 2000 characters')
        out[key] = [x.strip() for x in items if x.strip()]
    unknown = set(value) - set(WORKSTREAM_TEXT) - set(WORKSTREAM_LISTS)
    if unknown: raise ValueError('Unknown workstream fields: ' + ', '.join(sorted(unknown)))
    return out


def brief(value):
    if not isinstance(value, dict): raise ValueError('Research brief must be an object')
    mission = mission_input(value.get('mission'))
    preset = value.get('preset')
    if preset is not None:
        if preset != 'pre-build': raise ValueError('Unknown research preset')
        # the preset decides depth, lenses, formats and Council; a brief may still turn the Council off (light or none)
        fixed = {k: v for k, v in PRESETS['pre-build'].items() if k != 'limits'}
        value = {**value, **fixed, 'council': value.get('council', True), 'workstream': workstream(value.get('workstream'))}
        references = [x for x in value['workstream']['references'] if re.fullmatch(r'https://\S{1,1990}', x)]
        value['urls'] = list(dict.fromkeys(list(value.get('urls', [])) + references))[:12]
    question = value.get('question', ('Research '+mission['type']+': '+mission['target']) if mission else '')
    if not isinstance(question,str):raise ValueError('Research question must be text')
    question=question.strip()
    if not 10 <= len(question) <= 3000: raise ValueError('Describe a research question in 10–3000 characters')
    lenses=value.get('lenses',['understand']);formats=value.get('formats',['md','html'])
    if not isinstance(lenses,list) or any(not isinstance(x,str) for x in lenses):raise ValueError('Research lenses must be an array')
    if not isinstance(formats,list) or any(not isinstance(x,str) for x in formats):raise ValueError('Output formats must be an array')
    lenses = list(dict.fromkeys(lenses))
    formats = list(dict.fromkeys(formats))
    depth = value.get('depth', 'detailed')
    if not lenses or any(x not in LENSES for x in lenses): raise ValueError('Choose one or more known research lenses')
    if not formats or any(x not in FORMATS for x in formats): raise ValueError('Choose one or more supported output formats')
    if depth not in DEPTHS: raise ValueError('Unknown research depth')
    context = value.get('context', '')
    urls = value.get('urls', [])
    if not isinstance(context, str) or len(context) > 6000: raise ValueError('Context must be text of at most 6000 characters')
    if not isinstance(urls, list) or len(urls) > 12 or any(not isinstance(u, str) or len(u) > 2000 for u in urls):
        raise ValueError('Supply at most 12 source URLs')
    inspections = value.get('inspections', [])
    if not isinstance(inspections, list) or any(not isinstance(x, str) for x in inspections): raise ValueError('Invalid inspection selection')
    documents = value.get('documents', [])
    if not isinstance(documents, list) or len(documents)>12 or any(not isinstance(x,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',x) for x in documents):
        raise ValueError('Select at most 12 configured document names')
    if mission and mission['type']=='council' and value.get('council') is False:raise ValueError('A Council mission must run its Council')
    if not isinstance(value.get('council',True),bool):raise ValueError('Challenge round must be true or false')
    members = value.get('council_members', [] if mission and mission['specialists'] else DEFAULT_COUNCIL)
    if (not isinstance(members, list) or len(members) > 6
            or any(not isinstance(x, str) or x not in COUNCIL_SPECIALISTS for x in members)):
        raise ValueError('Select up to six known Council specialists')
    auto_experts = value.get('council_auto_experts', not bool(mission and mission['specialists']))
    if not isinstance(auto_experts, bool):raise ValueError('Automatic domain specialists must be true or false')
    if value.get('council', True) and not members and not auto_experts and not (mission and mission['specialists']):
        raise ValueError('Choose a Council specialist or enable automatic domain specialists')
    return dict(question=question, context=context, lenses=lenses, formats=formats, depth=depth,
                council_members=list(dict.fromkeys(members)), council_auto_experts=auto_experts,
                council=bool(value.get('council', True)), urls=list(dict.fromkeys(urls)), inspections=inspections, documents=list(dict.fromkeys(documents)),
                **({'preset': preset, 'workstream': value['workstream']} if preset else {}),
                **({'mission':mission} if mission else {}),
                privacy='Your question, context, retrieved public passages, selected local documents and excerpts from selected local REA artifacts are sent to the model provider. Select only material you intend to share. Local run records remain on this machine.')


class RequestConflict(ValueError):
    """A saved request must never be replayed with a different brief."""


class RunStore:
    def __init__(self, root):
        self.root = Path(root).resolve(); self.root.mkdir(parents=True, exist_ok=True); self.lock = threading.RLock()
    def directory(self, run_id):
        if not re.fullmatch(r'[a-f0-9]{32}', run_id): raise ValueError('Invalid run ID')
        return self.root / run_id
    def save(self, run_id, name, data):
        if not re.fullmatch(r'[A-Za-z0-9_-]+\.json', name): raise ValueError('Invalid record name')
        with self.lock:
            directory = self.directory(run_id); directory.mkdir(exist_ok=True)
            target = directory / name; tmp = directory / ('.' + name + '.tmp')
            with tmp.open('w') as f:
                f.write(dump(data)); f.flush(); os.fsync(f.fileno())
            tmp.replace(target)
    def read(self, run_id): return json.loads((self.directory(run_id) / 'state.json').read_text())
    def request_identity(self, request, request_id):
        if not isinstance(request_id, str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}', request_id):
            raise ValueError('Use a stable request id of 1–128 letters, digits or ._:-')
        digest = hashlib.sha256(json.dumps(brief(request), sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        run_id = hashlib.sha256(('research-request-v1:' + request_id).encode()).hexdigest()[:32]
        return run_id, digest
    def existing_request(self, request, request_id):
        if request_id is None: return None
        run_id, digest = self.request_identity(request, request_id)
        if not self.directory(run_id).exists(): return None
        try: state = self.read(run_id)
        except (OSError, ValueError): raise RequestConflict('Saved request is incomplete; no new job was started')
        if state.get('request_hash') != digest:
            raise RequestConflict('Request id already belongs to a different brief')
        return state
    def create(self, request, request_id=None):
        request = brief(request)
        with self.lock:
            prior = self.existing_request(request, request_id)
            if prior: return prior['id']
            run_id, digest = self.request_identity(request, request_id) if request_id is not None else (uuid.uuid4().hex, None)
            self.directory(run_id).mkdir()
            self.save(run_id, 'brief.json', request)
            self.save(run_id, 'state.json', {'id': run_id, 'status': 'queued', 'stage': 'queued', 'started_at': timestamp(), 'events': [], 'outputs': [], 'errors': [],
                                           **({'request_id': request_id, 'request_hash': digest} if request_id is not None else {})})
            return run_id
    def update(self, run_id, **fields):
        with self.lock:
            state = self.read(run_id); state.update(fields); self.save(run_id, 'state.json', state)
    def event(self, run_id, stage, text):
        with self.lock:
            state = self.read(run_id); state['stage'] = stage
            state['events'].append({'at': timestamp(), 'stage': stage, 'text': text})
            self.save(run_id, 'state.json', state)
    def recover_interrupted(self):
        for file in self.root.glob('*/state.json'):
            try:
                state = json.loads(file.read_text())
                if state['status'] in ('queued', 'running', 'reviewing', 'cancelling', 'pausing', 'paused'):
                    self.update(state['id'], status='interrupted', stage='interrupted',
                                errors=state.get('errors', []) + ['Process restarted. Evidence retained; no automatic replay. Eligible runs can resume from saved checkpoints.'])
            except (ValueError, KeyError, OSError): continue


def retain_role_value(entry, key, value):
    raw = json.dumps(value, ensure_ascii=False)
    saved = json.loads(retained_diagnostic(json.dumps(value), limit=None))
    entry[key] = saved
    entry[key + '_sha256'] = hashlib.sha256(raw.encode()).hexdigest()
    entry[key + '_redacted'] = json.dumps(saved, ensure_ascii=False) != raw


class ResearchEngine:
    def __init__(self, store, config=None, model=None, web=None, crawlee=None):
        from .canon import operator_config
        self.store, self.config, self.model_override = store, operator_config(config), model
        self.web = web or PublicWeb(permitted=lambda url:permits(self.request.get("mission"),url)); self.crawlee_override = crawlee; self.acquisition = None; self.scrapling_factory = None
        self.cancelled = threading.Event();self.pause_requested=threading.Event()
        self.errors = []; self.sources = []; self.packets = []; self.findings = []; self.requirements = []
        self.gaps = []; self.reviewed = {}; self.serial = 0; self.round = 0
        self.role_calls=[];self.role_lock=threading.Lock()
        self.call_limit=None;self.concurrency=3;self.request={};self.execution=None;self.replaying=False;self.provider_usage=[];self.provider_session=uuid.uuid4().hex
    SNAPSHOT_FIELDS = ('errors','sources','packets','findings','requirements','gaps','reviewed','serial','round','acquisition','coverage_result')
    def checkpoint(self, key, action):
        """One durable execution record in the existing run directory, not a scheduler."""
        if self.execution is None:return action()
        saved=self.execution['completed'].get(key)
        if saved is not None:return saved['result']
        self.execution['inflight']=key
        self.store.save(self.run_id,'execution.json',self.execution)
        result=action()
        self.execution['completed'][key]={'result':result}
        self.execution['snapshot']={name:getattr(self,name) for name in self.SNAPSHOT_FIELDS if hasattr(self,name)}
        evidence=self.store.directory(self.run_id)/'evidence'
        self.execution['evidence']={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in evidence.glob('*') if f.is_file()}
        self.execution['inflight']=None
        self.store.save(self.run_id,'execution.json',self.execution)
        return result
    @staticmethod
    def resumable(store, run_id):
        """Validate before dispatch; incomplete external operations are never replayed."""
        if store.read(run_id)['status']!='interrupted':raise ValueError('Only an interrupted saved mission can restart from checkpoints')
        path=store.directory(run_id)/'execution.json'
        if not path.exists():raise ValueError('This older run has no durable execution checkpoint')
        value=json.loads(path.read_text())
        request=json.loads((store.directory(run_id)/'brief.json').read_text())
        digest=hashlib.sha256(json.dumps(request,sort_keys=True).encode()).hexdigest()
        if value.get('schema')!='tmf-research-execution/1' or value.get('brief_sha256')!=digest:
            raise ValueError('Saved mission checkpoint does not match its brief')
        key=value.get('inflight') or ''
        if key in ('collect','inspect','documents','publish') or key.startswith('collect:'):
            raise ValueError('The external collection, inspection or export stage was interrupted; its retained evidence needs recovery before it can resume')
        for name,digest in value.get('evidence',{}).items():
            if not re.fullmatch(r'[A-Za-z0-9_.-]+',name):raise ValueError('Invalid checkpoint evidence reference')
            file=store.directory(run_id)/'evidence'/name
            if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest()!=digest:
                raise ValueError('Retained checkpoint evidence integrity mismatch')
        return value
    def check(self):
        if self.cancelled.is_set(): raise InterruptedError('Research cancelled')
        while self.pause_requested.is_set():
            with self.role_lock:
                running=any(r.get('status')=='running' for r in self.role_calls)
            status='pausing' if running else 'paused'
            if self.store.read(self.run_id)['status']!=status:self.store.update(self.run_id,status=status)
            if self.cancelled.wait(.1):raise InterruptedError('Research cancelled')
    def call(self, role, task, data, search=False):
        self.check()
        mission=self.request.get('mission')
        if mission and mission['type'] in ('company','startup','leads'):
            # Planning and coverage must see the same output contract as the writer.
            data={**data,'mission_output_contract':output_instruction(mission)}
        if isinstance(data,dict) and isinstance(data.get('evidence'),list):
            # Keep later rounds bounded as the source ledger grows.
            packets=data['evidence'];per_source=min(16000,100000//max(1,len(packets)))
            query=json.dumps({'brief':data.get('brief',{}),'task':data.get('task',{})},ensure_ascii=False)
            data={**data,'evidence':[{**p,'text':source_passages(p['text'],query,per_source)} for p in packets]}
        request_sha256=hashlib.sha256(json.dumps(dict(role=role,instruction=task,data=data,search=search),sort_keys=True).encode()).hexdigest()
        if self.replaying:
            with self.role_lock:
                prior=next((r for r in self.role_calls if r.get('request_sha256')==request_sha256 and r.get('status')=='returned'),None)
                if prior:
                    if prior.get('output_redacted') or 'output' not in prior:raise ProviderError('A redacted retained model result cannot be replayed as exact evidence')
                    raw=json.dumps(prior['output'],ensure_ascii=False)
                    if hashlib.sha256(raw.encode()).hexdigest()!=prior['output_sha256']:raise ProviderError('Retained model result integrity mismatch')
                    return json.loads(raw)
        entry={'request_sha256':request_sha256,'id':uuid.uuid4().hex,'role':role,'started_at':timestamp(),'status':'running','search_enabled':search}
        retain_role_value(entry, 'input', dict(role=role, instruction=task, data=data, search=search))
        started = time.monotonic()
        with self.role_lock:
            if self.call_limit is not None and len(self.role_calls)>=self.call_limit: raise ProviderError('Mission model-call budget exhausted; retained results were not replayed')
            self.role_calls.append(entry);self.store.save(self.run_id,'role-calls.json',self.role_calls)
        try:
            result = self.model.call(role, task, data, search=search)
            with self.role_lock:
                retain_role_value(entry, 'output', result)
                entry.update(status='returned',finished_at=timestamp())
        except subprocess.TimeoutExpired as exc:
            with self.role_lock:
                entry.update(status='timed_out', finished_at=timestamp(), error=type(exc).__name__, timeout_seconds=exc.timeout,
                             partial={'stdout': retained_diagnostic(exc.output), 'stderr': retained_diagnostic(exc.stderr)})
            raise
        except Exception as exc:
            with self.role_lock:
                entry.update(status='failed',finished_at=timestamp(),error=type(exc).__name__)
            raise
        finally:
            with self.role_lock:
                entry['elapsed_seconds'] = round(time.monotonic() - started, 3)
                self.store.save(self.run_id,'role-calls.json',self.role_calls)
                self.store.save(self.run_id,'provider-usage.json',self.provider_usage+[{'session':self.provider_session,**row} for row in getattr(self.model,'usage',[])])
                timed_out = [{k: v for k, v in r.items() if k not in ('input', 'input_sha256', 'input_redacted')}
                             for r in self.role_calls if r['status'] == 'timed_out']
                if timed_out: self.store.update(self.run_id, timed_out_roles=timed_out)
        self.check()
        return result
    def event(self, stage, text): self.store.event(self.run_id, stage, text)
    def error(self, message):
        self.errors.append(message); self.store.update(self.run_id, errors=self.errors)
    def search(self, queries):
        self.event('search', 'Source scout is searching for primary sources; search results are leads only.')
        result = self.call('Source scout', 'Use native web search for these bounded queries. Prefer official primary sources. '
                           'Return {"sources":[{"url":"https://...","title":"...","access":"readable|unverified|unavailable"}],"limitations":["..."]}. '
                           'At most 8 relevant sources. Order for breadth: interleave the distinct questions and vendors; '
                           'do not spend the shortlist on one subtopic. Prefer directly readable official documentation or '
                           'official Markdown/static equivalents when a previous URL failed. If the reference is an application shell, '
                           'seek official SDK documentation, schemas or examples, labeling their version/scope limits. '
                           'Mark pages you opened but could not read as unavailable; do not displace readable sources with known shells. '
                           'Search snippets are leads, not evidence.',
                           {'queries': queries,'brief':self.request,'unavailable_urls':[s['url'] for s in self.sources if s['state']=='unavailable' and s.get('url')]}, search=True)
        self.store.save(self.run_id, f'search-{self.round}.json', result)
        candidates = result.get('sources', [])
        if not isinstance(candidates, list): raise ProviderError('Invalid source-scout response')
        usable=[x for x in candidates[:8] if isinstance(x, dict) and isinstance(x.get('url'), str) and x.get('access')!='unavailable']
        return sorted(usable,key=lambda x:x.get('access')!='readable')
    def fetch(self, candidates, limit):
        seen = {s.get('url') for s in self.sources}
        for candidate in candidates:
            self.check()
            if len([s for s in self.sources if s.get('url')]) >= limit: break
            url = candidate['url']
            if not permits(self.request.get('mission'),url):
                self.gaps.append('Source excluded by mission scope: '+url);continue
            if url in seen: continue
            seen.add(url); sid = f'S{len(self.sources)+1:03}'
            self.event('fetch', f'Retrieving and retaining source {sid}.')
            source = {'id': sid, 'title': str(candidate.get('title') or url)[:200], 'url': url,
                      'retrieved_at': timestamp(), 'scope': 'Selected public web page, text extracted from retained bytes.',
                      'limitations': 'No authenticated vendor operation or runtime behavior tested.'}
            try:
                result = self.web.fetch(url)
                if not permits(self.request.get('mission'),result['url']):raise ProviderError('Redirect left the permitted mission scope')
                if len(result['text'].strip()) < 100: raise ProviderError('Page has too little readable content')
                source.update(state='partial' if result['truncated'] else 'available', artifact_sha256=result['sha256'])
                source.update(requested_url=url,final_url=result['url'],content_type=result['content_type'],
                              charset=result.get('charset','utf-8'),extraction='Retained response bytes → decoded text → inert HTML extraction; analyst context is bounded.')
                if result['truncated']: source['limitations'] += ' Snapshot truncated at transport size budget.'
                directory = self.store.directory(self.run_id) / 'evidence'; directory.mkdir(exist_ok=True)
                (directory / (sid + '.body')).write_bytes(result['raw'])
                (directory / (sid + '.txt')).write_text(result['text'])
                self.packets.append({'id': sid, 'title': source['title'], 'url': url,
                                     'text': result['text'], 'state': source['state']})
            except (OSError, ValueError, ProviderError) as exc:
                source.update(state='unavailable', limitations=f'Fetch failed ({type(exc).__name__}); no claim support.')
                self.error(f'{sid}: source unavailable; see source register')
            self.sources.append(source)
        self.store.save(self.run_id, 'sources.json', self.sources)
    def swarm(self, candidates, limit, deadline=240):
        """PRE-BUILD INGRESS: a parallel Crawlee swarm on the installed remote worker. One bounded job per site (the worker
        runs two at once and queues up to eight), polled to a terminal state, each source read back hash-checked and packed.
        Never a silent fallback to the public-web fetcher: no Crawlee means no pre-build evidence."""
        # the operator's config, else CRAWLEE_CONFIG (the variable the bridge itself reads; MC's install sets it on the workbench)
        crawlee = self.crawlee_override or Crawlee((self.config.get('crawlee') or {}).get('connection') or os.environ.get('CRAWLEE_CONFIG'))
        self.acquisition = self.acquisition or {'provider': 'crawlee', 'crawlers': ['crawlee'], 'jobIds': [], 'sourceHashes': [], 'jobs': [], 'packs': []}
        job_site, collected = {}, set();states={};round_jobs=[]
        prior_urls={s.get('url') for s in self.sources}|{s.get('requested_url') for s in self.sources}
        sites = {}
        for candidate in candidates:
            url = candidate.get('url') if isinstance(candidate, dict) else None
            host = urlsplit(url).hostname if isinstance(url, str) and url.startswith('https://') else None
            if host and url not in prior_urls and permits(self.request.get('mission'),url) and len(sites.setdefault(host, [])) < 5 and url not in sites[host]: sites[host].append(url)
        topic = (self.request.get('workstream') or {}).get('goal') or self.request['question']
        tags = ['pre-build'] + ([self.request['workstream']['id']] if self.request.get('workstream', {}).get('id') else [])
        try:
            remaining=max(0,limit-len([s for s in self.sources if s.get('url')]))
            for host, urls in list(sites.items())[:8]:
                self.check()
                if not remaining:break
                pages=min(5,remaining);remaining-=pages
                try:
                    job = crawlee.call('crawlee_start', {'urls': urls[:pages], 'allowed_domains': [host], 'max_pages': pages, 'max_depth': 1,
                                                         'topic': topic[:200], 'tags': [t[:60] for t in tags]})
                    self.acquisition['jobIds'].append(job['id']);round_jobs.append(job['id']); job_site[job['id']] = host
                    self.store.save(self.run_id,'acquisition.json',self.acquisition)
                except (ProviderError, KeyError, TypeError) as exc:
                    self.acquisition['jobs'].append({'site': host, 'status': 'not started', 'reason': str(exc)[:300]}); self.error(f'Crawlee job for {host} not started')
            self.event('swarm', f'Crawlee swarm: {len(round_jobs)} job(s) across {len(sites)} site(s).')
            pending, end = list(round_jobs), time.monotonic() + deadline
            states = {}
            while pending and time.monotonic() < end:
                self.check()
                for job_id in list(pending):
                    state = crawlee.call('crawlee_status', {'job_id': job_id})
                    if state.get('status') not in ('queued', 'running', 'cancelling'): states[job_id] = state; pending.remove(job_id)
                if pending: time.sleep(2)
            for job_id in pending:
                self.error(f'Crawlee job {job_id} still running at the deadline; cancelled, its sources not used')
                try: crawlee.call('crawlee_cancel', {'job_id': job_id})
                except ProviderError: pass
                self.acquisition['jobs'].append({'id': job_id, 'status': 'timed out'})
            directory = self.store.directory(self.run_id) / 'evidence'; directory.mkdir(exist_ok=True)
            for job_id, state in states.items():
                self.acquisition['jobs'].append({'id': job_id, 'status': state.get('status'), **({'reason': str(state['reason'])[:300]} if state.get('reason') else {})})
                for item in state.get('sources', []):
                    if len([x for x in self.sources if x.get('url')]) >= limit: break
                    sid = f'S{len(self.sources)+1:03}'
                    source = {'id': sid, 'title': str(item.get('title') or item.get('url'))[:200], 'url': item.get('final_url') or item.get('url'),
                              'crawler': 'crawlee', 'retrieved_at': item.get('retrieved_at') or timestamp(), 'scope': f'Crawlee swarm job {job_id}, source {item.get("id")}.',
                              'limitations': 'Collected by the remote Crawlee worker; untrusted reference text. No runtime behavior tested.'}
                    if item.get('state') != 'available' or not item.get('id'):
                        source.update(state='unavailable', limitations=f'Crawlee could not collect it ({str(item.get("reason", "unavailable"))[:200]}); no claim support.')
                    else:
                        try:
                            read = crawlee.call('crawlee_read', {'job_id': job_id, 'source_id': item['id'], 'limit': 20000})
                            text, digest = str(read.get('text', '')), str(read.get('source', {}).get('text_sha256', ''))
                            if len(text.strip()) < 100: raise ProviderError('Source has too little readable content')
                            partial = read.get('end', len(text)) < read.get('total_characters', len(text))
                            retained_hash=hashlib.sha256(text.encode()).hexdigest()
                            if not partial and retained_hash != digest:raise ProviderError('Crawlee text does not match its source hash')
                            if not permits(self.request.get('mission'),source['url']):raise ProviderError('Crawler result left mission scope')
                            source['upstream_text_sha256']=digest
                            digest=retained_hash
                            source.update(state='partial' if partial else 'available', artifact_sha256=digest, crawlee={'job': job_id, 'source': item['id']})
                            if partial: source['limitations'] += ' Read the first 20000 characters of the saved text.'
                            (directory / (sid + '.txt')).write_text(text)
                            (directory / (sid + '.body')).write_bytes(text.encode())
                            self.packets.append({'id': sid, 'title': source['title'], 'url': source['url'], 'text': text, 'state': source['state']})
                            self.acquisition['sourceHashes'].append(digest); collected.add(job_site.get(job_id))
                        except (ProviderError, KeyError, TypeError, ValueError) as exc:
                            source.update(state='unavailable', limitations=f'Crawlee read failed ({type(exc).__name__}); no claim support.')
                    self.sources.append(source)
                if state.get('status') in ('completed', 'partial', 'failed') and state.get('sources'):
                    try: self.acquisition['packs'].append({'job': job_id, 'artifacts': crawlee.call('crawlee_pack', {'job_id': job_id}).get('artifacts', [])})
                    except ProviderError as exc: self.error(f'Crawlee pack for {job_id} unavailable ({str(exc)[:120]})')
            # THE SCRAPLING PLUGIN for what Crawlee could not collect (blocked, changed layout, timed out): named, never quiet
            blocked = [host for host in dict.fromkeys(job_site.values()) if host not in collected]
            if blocked: self.scrapling_pass({host: sites[host] for host in blocked}, limit, directory)
        finally:
            if self.cancelled.is_set():
                for job_id in round_jobs:
                    if states.get(job_id,{}).get('status') in ('completed','partial','failed','cancelled'):continue
                    try:
                        crawlee.call('crawlee_cancel',{'job_id':job_id})
                        self.acquisition['jobs'].append({'id':job_id,'status':'cancel-requested'})
                    except ProviderError:
                        self.acquisition['jobs'].append({'id':job_id,'status':'cancellation-unconfirmed'})
            if not self.crawlee_override: crawlee.close()
            self.store.save(self.run_id, 'sources.json', self.sources)
            self.store.save(self.run_id, 'acquisition.json', self.acquisition)
    def scrapling_pass(self, sites, limit, directory):
        """The Scrapling plugin (plugins/scrapling) collects the sites the Crawlee worker could not. Three plugin processes in
        parallel, each source hash-checked into the same evidence review; an unavailable plugin is said once, by name."""
        self.event('swarm', f'Scrapling plugin: collecting {len(sites)} site(s) the Crawlee worker could not ({", ".join(sites)}).')
        record = {'sites': list(sites), 'fetched': 0, 'failed': 0}; self.acquisition['scrapling'] = record
        remaining=max(0,limit-len([s for s in self.sources if s.get('url')]))
        if not remaining:return
        make = self.scrapling_factory or (lambda: ScraplingPlugin(**((self.config.get('crawlers') or {}).get('scrapling') or {})))
        probe = make()
        try: record['version'] = probe.call('scrapling_status', {}).get('version')
        except ProviderError as exc:
            record['unavailable'] = str(exc)[:300]; self.error(f'Scrapling plugin unavailable for {len(sites)} site(s): {str(exc)[:160]}')
            probe.close(); return
        if 'scrapling' not in self.acquisition['crawlers']: self.acquisition['crawlers'].append('scrapling')
        urls = [u for host_urls in sites.values() for u in host_urls[:3]][:remaining]
        clients = [probe] + [make() for _ in range(min(2, max(0, len(urls) - 1)))]
        results = {}
        try:
            with ThreadPoolExecutor(max_workers=len(clients)) as pool:
                chunks = [urls[i::len(clients)] for i in range(len(clients))]
                def run(client, chunk):
                    for url in chunk:
                        try:
                            mission=self.request.get('mission') or {}
                            scope={key:mission[key] for key in ('permitted_domains','excluded_domains') if mission.get(key)}
                            results[url] = client.call('scrapling_fetch', {'url': url, **scope})
                        except ProviderError as exc: results[url] = exc
                for future in as_completed([pool.submit(run, c, ch) for c, ch in zip(clients, chunks)]): future.result()
        finally:
            for client in clients: client.close()
        for url in urls:
            self.check()
            if len([x for x in self.sources if x.get('url')]) >= limit: break
            got, sid = results.get(url, ProviderError('not collected')), f'S{len(self.sources)+1:03}'
            source = {'id': sid, 'title': url[:200], 'url': url, 'crawler': 'scrapling', 'retrieved_at': timestamp(),
                      'scope': 'Scrapling plugin, for a site the Crawlee worker could not collect.',
                      'limitations': 'Untrusted reference text collected by the Scrapling plugin. No runtime behavior tested.'}
            text = got.get('text', '') if isinstance(got, dict) else ''
            if isinstance(got,dict) and not permits(self.request.get('mission'),got.get('final_url') or url):got=ProviderError('Scrapling result left mission scope')
            if isinstance(got, Exception) or len(text.strip())<100 or hashlib.sha256(text.encode()).hexdigest() != got.get('text_sha256'):
                reason = str(got)[:200] if isinstance(got, Exception) else 'text does not match its hash'
                source.update(state='unavailable', limitations=f'Scrapling could not collect it ({reason}); no claim support.'); record['failed'] += 1
            else:
                source.update(state='available', url=got.get('final_url') or url, requested_url=url, artifact_sha256=got['text_sha256'],
                              fetcher=got.get('fetcher'), retrieved_at=got.get('retrieved_at') or source['retrieved_at'])
                (directory / (sid + '.txt')).write_text(text)
                (directory / (sid + '.body')).write_bytes(text.encode())
                self.packets.append({'id': sid, 'title': source['title'], 'url': source['url'], 'text': text, 'state': 'available'})
                self.acquisition['sourceHashes'].append(got['text_sha256']); record['fetched'] += 1
            self.sources.append(source)
    def spec_doc(self, synthesis, accepted, requirements, unknowns):
        """The workstream's spec doc in chapters (cn-bdaf883f DOC OUT); the builders review it, Jev reads it, then they cut tickets."""
        self.event('spec', 'Spec writer is writing the workstream doc in chapters from reviewed findings.')
        template = [{'id': cid, 'title': title} for cid, title in SPEC_CHAPTERS] + [
            {'id': 'build-1', 'title': 'Build chapter 1..n: scope, files, acceptance criteria, risks (one per epic, no tickets)'},
            {'id': 'proof', 'title': 'Proof + only the questions that need the Owner'}]
        doc = self.call('Spec writer', 'Write the workstream spec doc in chapters, from reviewed findings only. '
                        'Return {"title":"...","chapters":[{"id":"...","title":"...","body":"markdown"}]}. Use exactly the chapter ids of the template, '
                        'in its order, with one or more build-N chapters (build-1, build-2, ...) before proof. Cite source IDs (S001) for every factual claim; '
                        'a claim without a source is written as UNKNOWN. Keep unknowns visible. Requirements are user stories with acceptance criteria. '
                        'Do not cut tickets. Respect workstream.constraints and what workstream.existing says already exists: never propose rebuilding it.',
                        {'brief': self.request, 'template': template, 'findings': accepted, 'requirements': requirements, 'unknowns': unknowns,
                         'synthesis': {k: synthesis.get(k) for k in ('title', 'summary', 'sections', 'council_synthesis')}})
        chapters, sources = doc.get('chapters'), {x['id'] for x in self.sources if x['state'] != 'unavailable'}
        ids = [c.get('id') for c in chapters] if isinstance(chapters, list) and all(isinstance(c, dict) for c in chapters) else []
        builds = [i for i in ids if isinstance(i, str) and re.fullmatch(r'build-\d{1,2}', i)]
        expected = [cid for cid, _ in SPEC_CHAPTERS] + builds + ['proof']
        if not builds or ids != expected or len(ids) > 16:
            raise ProviderError('Spec chapters do not follow the template (summary, what-exists, research, requirements, design, build-N, proof)')
        for chapter in chapters:
            if not isinstance(chapter.get('title'), str) or not isinstance(chapter.get('body'), str) or not chapter['body'].strip() or len(chapter['body']) > 12000:
                raise ProviderError(f'Spec chapter {chapter.get("id")} has no usable title or body')
            cited = set(re.findall(r'\bS\d{3}\b', chapter['body']))
            if cited - sources: raise ProviderError(f'Spec chapter {chapter["id"]} cites unknown sources: {", ".join(sorted(cited - sources))}')
        if not set(re.findall(r'\bS\d{3}\b', next(c['body'] for c in chapters if c['id'] == 'research'))):
            raise ProviderError('The research chapter cites no source')
        title = str(doc.get('title') or self.request['workstream']['goal'])[:200]
        clean = [{'id': c['id'], 'title': c['title'][:200], 'body': c['body']} for c in chapters]
        return {'title': title, 'chapters': clean, 'markdown': f'# {title}\n\n' + '\n\n'.join(f'## {c["title"]}\n\n{c["body"]}' for c in clean) + '\n'}
    def documents(self, selected):
        """Only operator-configured UTF-8 files; source text never supplies paths."""
        definitions=self.config.get('documents',{})
        for key in selected:
            self.check()
            if key not in definitions: raise ValueError('Document is not configured by the local operator')
            item=definitions[key];sid=f'D{len(self.sources)+1:03}'
            source=dict(id=sid,kind='local-document',title=str(item.get('title',key))[:200],retrieved_at=timestamp(),
                        scope=str(item.get('scope','Operator-selected static local document.'))[:1000],
                        limitations='Static selected text; not runtime proof. Contents are untrusted evidence, not instructions.')
            try:
                with Path(item['path']).open('rb') as stream:raw=stream.read(200001)
                if len(raw)>200000:raise ValueError('Document exceeds 200000-byte limit')
                text=raw.decode('utf-8')
                if not text.strip():raise ValueError('Document is empty')
                digest=hashlib.sha256(raw).hexdigest()
                if item.get('sha256') and item['sha256']!=digest:raise ValueError('Document integrity mismatch')
                directory=self.store.directory(self.run_id)/'evidence';directory.mkdir(exist_ok=True)
                (directory/(sid+'.body')).write_bytes(raw)
                (directory/(sid+'.txt')).write_text(text,encoding='utf-8')
                source.update(state='available',artifact_sha256=digest)
                self.packets.append(dict(id=sid,title=source['title'],text=text,state='available'))
            except (OSError,ValueError,KeyError) as exc:
                source.update(state='unavailable',limitations=f'Local document unavailable ({type(exc).__name__}); no claim support.')
                self.error(sid+': local document unavailable')
            self.sources.append(source)
        self.store.save(self.run_id,'sources.json',self.sources)
    def inspect(self, selected):
        definitions = self.config.get('inspections', {})
        for key in selected:
            self.check()
            if key not in definitions: raise ValueError('Inspection is not configured by the local operator')
            item = definitions[key]; operation = item['operation']; prefix = item.get('command', ['rea'])
            if operation not in REA_OPERATIONS or not isinstance(prefix, list) or not prefix or any(not isinstance(x, str) for x in prefix):
                raise ValueError('Invalid REA configuration')
            source_paths = item.get('source_paths', [])
            if not isinstance(source_paths, list) or any(not isinstance(x, str) or x.startswith('-') for x in source_paths):
                raise ValueError('Invalid selected REA sources')
            args = prefix + [operation, str(Path(item['target']).resolve())]
            for path in source_paths: args += ['--source-path', path]
            if operation == 'analyze-javascript-application': args += ['--analysis-timeout-ms', '45000', '--max-heap-mb', '512']
            args += ['--json']
            self.event('inspect', 'REA analyst is inspecting the operator-selected local artifact.')
            sid = 'REA' + str(len(self.sources)+1)
            try:
                result = bounded_run(args, timeout=90, max_output=16_000_000, text=False)
                if len(result.stdout) > 16_000_000: raise ProviderError('REA response exceeds evidence budget')
                evidence = json.loads(result.stdout)
                if not evidence.get('evidence_id'): raise ProviderError('No REA evidence envelope')
                self.store.save(self.run_id, sid + '.json', evidence)
                digest = hashlib.sha256((self.store.directory(self.run_id)/(sid+'.json')).read_bytes()).hexdigest()
                self.sources.append(dict(id=sid, title=item.get('title', key), state='partial', retrieved_at=timestamp(),
                                         artifact_sha256=digest, evidence_id=evidence['evidence_id'],
                                         scope='Selected static local artifact inspection.', limitations='Static selected-source evidence, not runtime proof. ' + ' | '.join(map(str,evidence.get('limitations', [])))))
                normalized = evidence.get('normalized_result', {})
                # Retain full original envelope; analysts receive only bounded data, not local paths.
                def redact(value):
                    if isinstance(value,dict):
                        return {k:('[redacted]' if re.search(r'local_path|input_path|password|secret|authorization|api_key|access_token',k,re.I) else redact(v)) for k,v in value.items()}
                    if isinstance(value,list):return [redact(x) for x in value]
                    if isinstance(value,str):return re.sub(r'(?:/Users/|/home/|[A-Z]:\\Users\\)[^\s"\']+', '[local-path]', value)
                    return value
                packet = {'id': sid, 'title': item.get('title', key), 'state': 'partial',
                          'text': json.dumps(redact({'summary': normalized.get('summary'), 'statistics': normalized.get('statistics'),
                                                     'graph': normalized.get('graph'), 'limitations': evidence.get('limitations')}))[:16000]}
                self.packets.append(packet)
                if result.returncode: self.error('REA returned a nonzero exit; evidence remains partial')
            except (OSError, ValueError, subprocess.SubprocessError) as exc:
                self.error(f'REA inspection unavailable ({type(exc).__name__})')
        self.store.save(self.run_id, 'sources.json', self.sources)
    def investigate(self, tasks):
        self.event('investigate', 'Specialists are independently reading bounded source passages.')
        instruction = ('Answer your assigned investigation using only the supplied evidence. Return '
                       '{"findings":[{"text":"...","label":"documented|observed|inferred|proposed",'
                       '"sources":["S001"],"quote":"short exact source passage, at most 25 words","caveat":"..."}],'
                       '"requirements":[{"text":"...","acceptance":"...","basis":["source IDs"]}],'
                       '"gaps":["..."]}. At most 5 findings and 5 requirements. Static code inspection is not runtime proof. '
                       'No external factual finding without a supplied source and exact supporting quote. Proposals need no quote. '
                       'Each finding must make ONE independently checkable assertion supported by its quote and nearby context. '
                       'Do not bundle several fields, lifecycle rules, exceptions and design implications into one factual claim. '
                       'Separate documented source behavior from proposed TMF controls or inferred business conclusions. '
                       'Quote only one short passage per finding; do not copy whole paragraphs.')
        results = []
        with ThreadPoolExecutor(max_workers=self.concurrency) as pool:
            futures = {pool.submit(self.call, t.get('role', 'Research specialist'), instruction,
                                    {'brief': self.request, 'task': t, 'evidence': self.packets}): t for t in tasks[:3]}
            for future in as_completed(futures):
                task = futures[future]
                try:
                    result = future.result(); results.append({'role': task.get('role'), 'result': result})
                    self.ingest(result)
                except (ProviderError, ValueError, OSError, subprocess.SubprocessError) as exc:
                    self.error(f"Specialist {task.get('role')}: {type(exc).__name__}")
        self.store.save(self.run_id, f'investigation-{self.round}.json', results)
    def ingest(self, result):
        known = {s['id']: s for s in self.sources}
        packets = {p['id']: p for p in self.packets}
        for item in result.get('findings', [])[:5]:
            if not isinstance(item, dict) or not isinstance(item.get('text'), str): continue
            if any(f['text'] == item['text'] for f in self.findings): continue
            label = item.get('label'); refs = item.get('sources', [])
            if label not in ('documented', 'observed', 'inferred', 'proposed') or not isinstance(refs,list): continue
            if any(x not in known or known[x]['state']=='unavailable' for x in refs): continue
            quote = item.get('quote', '')
            # Exact quote presence is an admission check, not an entailment verdict.
            if label != 'proposed' and (not refs or not isinstance(quote,str) or not quote.strip() or
                                       len(quote.split())>25 or not any(quote in packets[x]['text'] for x in refs if x in packets)):
                self.gaps.append('Rejected finding lacks an exact bounded supporting passage: ' + item['text'][:200]); continue
            self.serial += 1
            self.findings.append(dict(id=f'F{self.serial:03}', text=item['text'][:2500], label=label, sources=refs,
                                      quote=quote, caveat=str(item.get('caveat') or 'Evidence is bounded to the retrieved source and inspection context.'), review='pending'))
        for item in result.get('requirements', [])[:5]:
            if isinstance(item,dict) and isinstance(item.get('text'),str) and isinstance(item.get('acceptance'),str):
                refs=item.get('basis',[])
                refs=refs if isinstance(refs,list) else []
                self.requirements.append({'text':item['text'][:2500], 'acceptance':item['acceptance'][:2500],
                                          'basis':[sid for sid in refs if isinstance(sid,str) and sid in known and known[sid]['state']!='unavailable']})
        self.gaps.extend(str(x)[:700] for x in result.get('gaps',[])[:8])
    def review(self):
        pending = [f for f in self.findings if f['review']=='pending']
        if not pending: return
        self.event('review', 'Evidence reviewer is checking claims against original passage context.')
        contexts = []
        for finding in pending:
            for sid in finding['sources']:
                packet = next((p for p in self.packets if p['id']==sid),None)
                if packet:
                    quote = finding['quote']; pos = packet['text'].find(quote)
                    contexts.append({'finding':finding['id'],'source':sid,'text':packet['text'][max(0,pos-1000):pos+len(quote)+2000]})
        result = self.call('Evidence reviewer', 'Independently check each supplied finding against original passage context. '
                           'Return {"reviews":[{"id":"F001","verdict":"supported|unsupported|uncertain|proposal",'
                           '"reason":"...","requires_revision":false}],"duplicate_groups":[{"keep":"F001","duplicates":["F002"],"reason":"..."}],"follow_up_queries":["..."]}. '
                           'A matching quote does not guarantee entailment. Reject overreach, wrong scope, stale versions or runtime claims from static facts. '
                           'Judge the entire exact claim and label, not just its useful core. If any qualification or change is needed, '
                           'set requires_revision=true and verdict=uncertain; your reason is not a correction to the published claim. '
                           'Group only semantically equivalent accepted claims; keep the most complete supported wording. Do not merge distinct facts. '
                           'Proposed designs are proposals, never verified facts. No majority vote can establish truth.',
                           {'findings':pending,'previously_reviewed':[f for f in self.findings if f['review'] in ('supported','proposal')],'source_contexts':contexts})
        self.store.save(self.run_id, f'review-{self.round}.json', result)
        by_id = {x.get('id'):x for x in result.get('reviews',[]) if isinstance(x,dict)}
        for finding in pending:
            decision = by_id.get(finding['id'], {})
            verdict = decision.get('verdict', 'uncertain')
            if verdict not in ('supported','unsupported','uncertain','proposal'): verdict='uncertain'
            if verdict=='supported' and decision.get('requires_revision') is not False: verdict='uncertain'
            if finding['label']=='proposed': verdict='proposal'
            elif verdict=='proposal': verdict='uncertain'
            finding['review']=verdict; finding['review_reason']=str(decision.get('reason','Reviewer returned no decision'))
        self.consolidate(result.get('duplicate_groups',[]))
        self.gaps.extend('Review gap: '+f['text'] for f in pending if f['review'] in ('unsupported','uncertain'))
        return result.get('follow_up_queries', [])[:2]
    def consolidate(self, groups):
        by_id={f['id']:f for f in self.findings}
        for group in groups if isinstance(groups,list) else []:
            if not isinstance(group,dict): continue
            keep=by_id.get(group.get('keep'))
            if not keep or keep['review'] not in ('supported','proposal') or keep.get('duplicate_of'): continue
            for fid in group.get('duplicates',[]) if isinstance(group.get('duplicates'),list) else []:
                other=by_id.get(fid)
                if not other or other is keep or other.get('duplicate_of') or other['review']!=keep['review'] or other['label']!=keep['label']: continue
                if any(f.get('duplicate_of')==other['id'] for f in self.findings): continue
                if other['label']!='proposed' and not set(other['sources']) & set(keep['sources']): continue
                other['duplicate_of']=keep['id'];other['consolidation_reason']=str(group.get('reason','Equivalent reviewed claim'))
    def accepted(self):
        return [f for f in self.findings if f['review'] in ('supported','proposal') and not f.get('duplicate_of')]
    def coverage(self, plan, queries, analysis=None):
        self.event('coverage','Research lead is checking the original goals and prioritizing missing evidence.')
        council=self.store.directory(self.run_id)/'council.json'
        result=self.call('Research coverage lead',
            'Assess coverage of EVERY supplied success criterion, preserving its index. Return '
            '{"criteria":[{"index":0,"status":"answered|partial|unanswered","finding_ids":["F001"],"reason":"..."}],'
            '"follow_up_queries":["..."]}. At most 3 prioritized, concrete public-documentation queries. '
            'A proposed requirement to research something is NOT an answer. General controls do not establish domain semantics. '
            'Prioritize missing evidence central to the user decision over narrow disputes or repeated facts. '
            'Customer interviews and private runtime tests cannot be resolved by web search; keep them explicit, '
            'but pursue answerable official documentation questions. Use failed URLs to seek readable official alternatives. '
            'Coverage is a model assessment, not factual certification. Do not mark answered without reviewed finding IDs.',
            {'brief':self.request,'success_criteria':plan['success_criteria'],'findings':self.accepted(),
             'council':json.loads(council.read_text()) if council.exists() else None,
             'objections':queries,'sources':self.sources,'requirements':self.requirements,'accepted_analysis':analysis})
        rows={}
        for row in result.get('criteria',[]) if isinstance(result.get('criteria'),list) else []:
            if isinstance(row,dict) and type(row.get('index')) is int: rows[row['index']]=row
        accepted_ids={f['id'] for f in self.accepted()};criteria=[]
        for i,question in enumerate(plan['success_criteria']):
            row=rows.get(i,{});refs=[fid for fid in row.get('finding_ids',[]) if isinstance(fid,str) and fid in accepted_ids] if isinstance(row.get('finding_ids'),list) else []
            state=row.get('status','unanswered')
            if state not in ('answered','partial','unanswered') or (state=='answered' and not refs): state='unanswered'
            criteria.append({'index':i,'question':question,'status':state,'finding_ids':refs,'reason':str(row.get('reason','No coverage decision returned'))[:1200]})
        self.coverage_result={'kind':'Model-assessed question coverage, not certification','criteria':criteria}
        self.store.save(self.run_id,'coverage-final.json' if analysis is not None else f'coverage-{self.round}.json',self.coverage_result)
        self.store.save(self.run_id,'coverage.json',self.coverage_result)
        queries=result.get('follow_up_queries',[])
        return [q[:500] for q in queries if isinstance(q,str) and q.strip()][:3] if isinstance(queries,list) else []
    def council(self, experts):
        roles = council_roles(self.request, experts)
        self.event('council', 'Council specialists: ' + (', '.join(role for role, _ in roles) or 'none selected by the lead'))
        data = {'brief':self.request,'findings':[f for f in self.findings if f['review'] in ('supported','proposal')],
                'requirements':self.requirements,'unknowns':self.gaps[:20]}
        task = ('Critique the research from your assigned lens; do not perform an implementation or certify anything. '
                'Return {"position":"...","reason":"...","underweighted_risk":"...","alternative":"...",'
                '"evidence_needed":["..."],"follow_up_queries":["..."],"confidence":"low|medium|high"}. '
                'Keep under 200 words. These are simulated advisory perspectives, not real experts or factual evidence. '
                'Challenge unsupported claims and identify one consequential omission. Confidence is subjective, not a probability of correctness.')
        positions=[]
        with ThreadPoolExecutor(max_workers=self.concurrency) as pool:
            futures={pool.submit(self.call,role,task,dict(data,lens=lens)):role for role,lens in roles}
            for future in as_completed(futures):
                role=futures[future]
                try: positions.append({'role':role,**future.result()})
                except (ProviderError,ValueError,OSError,subprocess.SubprocessError) as exc:
                    positions.append({'role':role,'status':'unavailable','reason':type(exc).__name__});self.error('Council perspective unavailable: '+role)
        self.store.save(self.run_id,'council.json',{'kind':'TMF Council; same-provider simulated perspectives',
                        'selected_members':self.request['council_members'],
                        'automatic_domain_specialists':self.request['council_auto_experts'], 'positions':positions})
        self.gaps.extend('Council evidence request: '+str(gap)[:500] for p in positions for gap in p.get('evidence_needed',[])[:2])
        return list(dict.fromkeys(str(q) for p in positions for q in p.get('follow_up_queries',[])[:1]))[:2]
    def knowledge(self, references):
        if not references:return
        from .canon import CanonConnection, CanonUnavailable
        try:
            connection=CanonConnection(self.config)
            for reference in references:
                self.check();entry=connection.read(reference['id'],reference['revision'])
                text=entry['body'];sid=f'S{len(self.sources)+1:03}'
                digest=hashlib.sha256(text.encode()).hexdigest()
                directory=self.store.directory(self.run_id)/'evidence';directory.mkdir(exist_ok=True)
                (directory/(sid+'.body')).write_bytes(text.encode());(directory/(sid+'.txt')).write_text(text)
                source={'id':sid,'title':entry['title'],'kind':'canon-knowledge','state':'available',
                    'canon':reference,'retrieved_at':timestamp(),'artifact_sha256':digest,
                    'scope':f'Canon {reference["id"]} revision {reference["revision"]}',
                    'limitations':'Retained Research knowledge; its original evidence/review limits remain. A candidate is not approved guidance.'}
                self.sources.append(source);self.packets.append({'id':sid,'title':entry['title'],'text':text,'state':'available'})
                self.store.save(self.run_id,'sources.json',self.sources)
        except CanonUnavailable as exc:raise ProviderError(str(exc)) from None

    def execute(self, run_id, resume=False):
        self.run_id=run_id; self.request=json.loads((self.store.directory(run_id)/'brief.json').read_text())
        limits={**DEPTHS[self.request['depth']], **(PRESETS.get(self.request.get('preset'), {}).get('limits') or {})}
        mission=self.request.get('mission')
        if mission:
            if mission['type'] not in ('general','technology','council'):limits['calls']+=2
            limits.update(mission['budgets'])
            self.concurrency=limits.get('concurrency',3)
        self.call_limit=limits['calls']
        try:
            if resume:
                self.execution=self.resumable(self.store,run_id);self.replaying=True
                for name,value in self.execution.get('snapshot',{}).items():
                    if name in self.SNAPSHOT_FIELDS:setattr(self,name,value)
                path=self.store.directory(run_id)/'role-calls.json'
                self.role_calls=json.loads(path.read_text()) if path.exists() else []
                usage_path=self.store.directory(run_id)/'provider-usage.json'
                self.provider_usage=json.loads(usage_path.read_text()) if usage_path.exists() else []
                for row in self.role_calls:
                    if row['status']=='running':row.update(status='interrupted',finished_at=timestamp())
                self.store.save(run_id,'role-calls.json',self.role_calls)
                self.event('resume','Resuming the saved controller checkpoint. Completed stages and matching retained model results are reused; incomplete model calls consume the existing budget and may be retried.')
            else:
                self.execution={'schema':'tmf-research-execution/1','brief_sha256':hashlib.sha256(json.dumps(self.request,sort_keys=True).encode()).hexdigest(),'completed':{},'snapshot':{},'evidence':{},'inflight':None}
                self.store.save(run_id,'execution.json',self.execution)
            self.model=self.model_override or CodexModel(self.config.get('codex','codex'), max_calls=limits['calls'])
            self.store.update(run_id,status='running')
            if mission:self.checkpoint('knowledge',lambda:self.knowledge(mission['knowledge_refs']))
            self.event('plan','Research lead is decomposing the selected lenses into bounded investigations.')
            plan=self.checkpoint('plan',lambda:self.call('Research lead', 'Plan the investigation. Return {"queries":["..."],'
                           '"tasks":[{"role":"...","question":"..."}],"experts":[{"role":"...","lens":"..."}],'
                           '"success_criteria":["..."],"scope_limits":["..."]}. At most 3 queries, 3 tasks and 2 domain experts. '
                           'Cover every selected lens in the three tasks. First map the relevant scope and relationships, '
                           'then allocate complementary investigations. Broad requests need the shared foundation before narrow examples; '
                           'focused requests should stay focused. Adapt to supplied context rather than assuming one organization or domain. '
                           'Experts are functional perspectives, not invented credentials.',
                           {'brief':self.request,'lenses':{x:LENSES[x] for x in self.request['lenses']},**({'evidence':self.packets} if self.packets else {})}))
            criteria=plan.get('success_criteria',[])
            plan['success_criteria']=[str(c)[:1000] for c in criteria[:8] if isinstance(c,str) and c.strip()] if isinstance(criteria,list) else []
            if not plan['success_criteria']: plan['success_criteria']=[self.request['question']]
            if mission:plan['success_criteria']=list(dict.fromkeys(plan['success_criteria']+mission['completion_criteria']))
            self.store.save(run_id,'plan.json',plan)
            self.gaps.extend('Lead scope limit: '+str(x)[:500] for x in plan.get('scope_limits',[])[:8])
            tasks=plan.get('tasks',[])
            if not isinstance(tasks,list) or not tasks or any(not isinstance(t,dict) for t in tasks): raise ProviderError('Lead returned no valid investigation tasks')
            candidates=self.checkpoint('search:0',lambda:self.search(plan.get('queries',[])[:3]))
            seed=[{'url':u,'title':u} for u in self.request['urls']]
            # Reserve two web slots for material follow-up in non-quick runs.
            if self.request.get('preset') == 'pre-build' or (mission and mission['collection']=='plugins'): self.checkpoint('collect',lambda:self.swarm(seed+candidates, limits['sources']))
            else: self.checkpoint('collect',lambda:self.fetch(seed+candidates, limits['sources']-(min(2,max(0,limits['sources']-1)) if limits['rounds'] else 0)))
            self.checkpoint('inspect',lambda:self.inspect(self.request['inspections']))
            self.checkpoint('documents',lambda:self.documents(self.request.get('documents',[])))
            if not self.packets: raise ProviderError('No readable evidence acquired; research cannot proceed')
            self.checkpoint('investigate:0',lambda:self.investigate(tasks))
            follow=self.checkpoint('review:0',self.review) or []
            positions_queries=self.checkpoint('council',lambda:self.council(plan.get('experts',[]))) if self.request['council'] else []
            queries=self.checkpoint('coverage:0',lambda:self.coverage(plan,follow+positions_queries))
            for n in range(limits['rounds']):
                if not queries: break
                self.round=n+1
                self.event('follow-up','Lead is investigating material objections before final synthesis.')
                before=self.checkpoint(f'before:{n+1}',lambda:len(self.packets))
                follow_sources=self.checkpoint(f'search:{n+1}',lambda:self.search(queries))
                if mission and mission['collection']=='plugins':self.checkpoint(f'collect:{n+1}',lambda:self.swarm(follow_sources,limits['sources']))
                else:self.checkpoint(f'collect:{n+1}',lambda:self.fetch(follow_sources,limits['sources']))
                if len(self.packets)==before:
                    self.gaps.append('Follow-up acquired no new readable evidence within the source budget.'); break
                self.checkpoint(f'investigate:{n+1}',lambda:self.investigate([{'role':'Follow-up investigator','question':'Resolve these objections: '+'; '.join(queries)}]))
                review_queries=self.checkpoint(f'review:{n+1}',self.review) or []
                queries=self.checkpoint(f'coverage:{n+1}',lambda:self.coverage(plan,review_queries))
            accepted=self.accepted()
            self.gaps.extend('Coverage '+c['status']+': '+c['question']+' — '+c['reason'] for c in self.coverage_result['criteria'] if c['status']!='answered')
            self.gaps.extend('Unresolved follow-up query: '+str(q) for q in queries)
            self.store.save(run_id,'claims.json',self.findings)
            if not accepted: raise ProviderError('No findings survived evidence review')
            self.checkpoint('publish',lambda:self.publish(plan,accepted,limits,queries))
        except InterruptedError:
            self.store.update(run_id,status='cancelled',stage='cancelled',finished_at=timestamp(),errors=self.errors)
        except Exception as exc:
            detail=(' '+str(exc)[:200]) if isinstance(exc,ProviderError) else ''
            self.error(f'Research stopped ({type(exc).__name__}).{detail} Retained evidence remains available locally')
            self.store.update(run_id,status='failed',stage='failed',finished_at=timestamp(),errors=self.errors)

    def refine(self, run_id, parent_id, feedback):
        """New synthesis from a hash-checked parent bundle; no source acquisition."""
        self.run_id=run_id
        try:
            parent=self.store.directory(parent_id);directory=self.store.directory(run_id)
            if parent==directory or self.store.read(parent_id)['status'] not in ('completed','partial'):
                raise ProviderError('Revision requires a finished parent investigation')
            if not isinstance(feedback,str) or not 1<=len(feedback)<=3000: raise ProviderError('Provide bounded revision feedback')
            receipt=json.loads((parent/'outputs/export-receipt.json').read_text())
            artifact=next((a for a in receipt['artifacts'] if a['file']=='builder-pack.json'),None)
            raw=(parent/'outputs/builder-pack.json').read_bytes()
            if not artifact or hashlib.sha256(raw).hexdigest()!=artifact['sha256']: raise ProviderError('Parent builder bundle integrity mismatch')
            bundle=json.loads(raw);record=validate(bundle['report'])
            report_hash=hashlib.sha256(dump(record).encode()).hexdigest()
            if report_hash!=receipt['record_sha256']: raise ProviderError('Parent report integrity mismatch')
            self.request=json.loads((directory/'brief.json').read_text());self.feedback=feedback
            self.sources=record['sources'];self.findings=bundle['claims'];self.requirements=record['requirements']
            self.gaps=[g for g in record.get('research_log',record['unknowns']) if not g.startswith('Coverage ')]
            self.coverage_result=bundle['analysis'].get('coverage',{'criteria':[]})
            plan=bundle['plan'];plan.setdefault('success_criteria',[record['question']])
            for key in ('plan','claims','council'):
                if key in bundle:self.store.save(run_id,key+'.json',bundle[key])
            self.store.save(run_id,'sources.json',self.sources)
            evidence=directory/'evidence';evidence.mkdir()
            for source in self.sources:
                if source['state']=='unavailable':continue
                retained_text=source.get('url') or source.get('kind') in ('local-document','canon-knowledge')
                original=parent/'evidence'/(source['id']+'.body') if retained_text else parent/(source['id']+'.json')
                if hashlib.sha256(original.read_bytes()).hexdigest()!=source['artifact_sha256']: raise ProviderError('Parent source integrity mismatch')
                shutil.copyfile(original,evidence/original.name if retained_text else directory/original.name)
                if retained_text:shutil.copyfile(parent/'evidence'/(source['id']+'.txt'),evidence/(source['id']+'.txt'))
            self.store.save(run_id,'revision.json',{'parent_id':parent_id,'parent_report_sha256':report_hash,'feedback':feedback,
                'scope':'Retained-evidence synthesis revision; original retrieval times preserved; no source acquisition or automatic replay'})
            self.errors=['Retained source '+s['id']+' is unavailable' for s in self.sources if s['state']=='unavailable']
            limits={'sources':0,'rounds':0,'calls':4+(2 if self.request.get('mission',{}).get('type') not in (None,'general','technology','council') else 0)}
            self.model=self.model_override or CodexModel(self.config.get('codex','codex'),max_calls=limits['calls'])
            self.store.update(run_id,status='running',parent_id=parent_id)
            self.publish(plan,self.accepted(),limits,[])
        except InterruptedError:
            self.store.update(run_id,status='cancelled',stage='cancelled',errors=self.errors)
        except Exception as exc:
            detail=str(exc)[:200] if isinstance(exc,ProviderError) else type(exc).__name__
            self.store.update(run_id,status='failed',stage='failed',errors=['Revision stopped: '+detail])

    def mission_output(self, record, accepted):
        mission=self.request['mission']
        if mission['type'] in ('general','technology'):return
        if mission['type']=='council':
            council=self.store.directory(self.run_id)/'council.json'
            if not council.exists():
                self.error('Council mission produced no Council record');return
            self.store.save(self.run_id,'intelligence.json',{'schema':'tmf-research-intelligence/1',
                'run_id':self.run_id,'mission_type':'council','review_status':'candidate',
                'independent_verification':False,'verification':'simulated-perspectives',
                'configuration':mission['specialists'],'council':json.loads(council.read_text())})
            return
        try:
            self.event('intelligence','Organizing mission outputs against the reviewed evidence.')
            raw=self.call('Mission intelligence analyst',output_instruction(mission),
                          {'mission':mission,'findings':accepted,'unknowns':record['unknowns'],
                           **({'source_register':record['sources']} if mission['type'] in ('company','startup','leads') else {})})
            self.store.save(self.run_id,'intelligence-draft.json',raw)
            output=validate_output(mission,raw,accepted,self.run_id,timestamp(),sources=record['sources'])
            from .canon import attach_company_continuity
            attach_company_continuity(output,self.config,self.error,self.check)
            review=self.call('Mission output evidence reviewer',
                'Check every company identity, factual claim, inference, recommendation and specialty instruction against the supplied findings. '
                'Return {"supported":true,"concerns":["..."]}. Refuse unsupported identity associations, invented company problems, '
                'unfounded professional procedures, missing jurisdiction/date caveats, inferred private thoughts, claims of person identity/endorsement, '
                'or promoted uncertain evidence. For leads, requested geography/industry is not evidence of a company location or qualification; unsupported matches stay unknown. A citation resolving is not entailment. Confidence is not verification. '
                'Specialties are draft expertise only, never permissions or deployed agents. This is model review, not independent certification.',
                {'mission':mission,'output':output,'reviewed_findings':accepted,
                 **({'source_register':record['sources']} if mission['type'] in ('company','startup','leads') else {})})
            self.store.save(self.run_id,'intelligence-review.json',review)
            if review.get('supported') is not True:raise ProviderError('Mission output evidence review withheld the proposed output')
            output['verification']='model-reviewed'
            def unknowns(value):
                if isinstance(value,dict):
                    if value.get('label')=='unknown':self.error('Mission section remains unknown: '+str(value.get('heading') or value.get('text'))[:160])
                    for child in value.values():unknowns(child)
                elif isinstance(value,list):
                    for child in value:unknowns(child)
            unknowns(output)
            source_map={s['id']:s for s in record['sources']}
            output['evidence']={f['id']:{'finding':f,'sources':[source_map[sid] for sid in f['sources']]} for f in accepted}
            self.store.save(self.run_id,'intelligence.json',output)
        except (ProviderError,ValueError,KeyError,TypeError) as exc:
            self.error('Mission output withheld: '+str(exc)[:200])

    def publish(self, plan, accepted, limits, queries):
        run_id=self.run_id
        self.event('synthesize','Writer is assembling the blueprint from reviewed findings and explicit unknowns.')
        council_file=self.store.directory(run_id)/'council.json'
        synthesis=self.call('Synthesis lead', 'Using only reviewed findings, write a useful research result. '
                            'Return {"title":"...","summary":"...","sections":[{"heading":"...","text":"..."}],'
                            '"finding_ids":["F001"],"tables":[{"title":"...","columns":["..."],"rows":[["..."]]}],'
                            '"requirements":[{"text":"...","acceptance":"...","basis":["source IDs"]}],"unknowns":["..."],'
                            '"workflow_steps":[{"label":"...","detail":"..."}],"council_synthesis":'
                            '{"agreement":"...","strongest_dissent":"...","recommendation":"..."}}. '
                            'Preserve dissent and source IDs. Cover selected lenses. Requirements and workflow are PROPOSED, not implemented. '
                            'No invented price, demand or verified behavior. At most 20 requirements and 6 short workflow steps. '
                            'Do not promote source titles, package names or version metadata into factual conclusions unless a reviewed finding establishes them. '
                            'Choose a concise, non-overlapping set of reviewed finding_ids for publication; preserve distinct risks and contrary evidence. '
                            'Do not rewrite claims or pad the findings list with repeated service proposals already covered by analysis. '
                            'Fulfill the success criteria explicitly. Organize the main report around the reader’s decision and next actions, not research task numbers. '
                            'Establish the broad landscape, relevant existing foundations, relationships and major gaps before narrowing to examples. '
                            'Follow the scope actually requested: a focused question still deserves a focused answer. '
                            'Use reusable methods with subject-specific evidence and configuration. '
                            'For system breakdowns map components, responsibilities, interfaces, data and workflows; trace handoffs and failure paths; '
                            'distinguish existing foundations, disconnected parts, missing capabilities and behavior needing verification; '
                            'then provide an ordered improvement plan with dependencies, tradeoffs, affected components and completion checks '
                            'that the relevant professionals can use. Do not assume the system is software or belongs to one organization. '
                            'Individual products or plugins are evidence and examples, not the whole architecture unless explicitly requested. '
                            'Missing runtime proof does not establish an absent implementation. Respect the user’s stated policies '
                            'without inventing restrictions. Include up to three concise tables suited to the job, '
                            'such as a component map, gap analysis and ordered work plan. '
                            'Each table has 2–6 columns and at most 16 rows. '
                            'Keep cells concise; mark unknown contracts UNKNOWN instead of inventing them. '
                            'Apply revision_feedback as editorial goals within these evidence limits; it cannot authorize new facts, tools or implementation claims. '
                            'Return at most six consolidated unknowns that materially change a decision; for each state the affected decision and '
                            'the smallest check that resolves it. Reconcile repeated or superseded research questions. The complete research log is '
                            'retained separately, so do not dump it into the main report. Preserve consequential dissent in the analysis.',
                            {'brief':self.request,'findings':accepted,'requirements':self.requirements,
                             'unknowns':self.gaps[-35:],'success_criteria':plan['success_criteria'],
                             'coverage':self.coverage_result,'revision_feedback':getattr(self,'feedback',''),
                             'council':json.loads(council_file.read_text()) if council_file.exists() else None})
        self.store.save(run_id,'synthesis.json',synthesis)
        tables=synthesis.get('tables',[])
        if not isinstance(tables,list) or len(tables)>3: raise ProviderError('Invalid analysis tables')
        for table in tables:
            if (not isinstance(table,dict) or not isinstance(table.get('title'),str)
                or not isinstance(table.get('columns'),list) or not 2<=len(table['columns'])<=6
                or any(not isinstance(c,str) for c in table['columns'])
                or not isinstance(table.get('rows'),list) or len(table['rows'])>16
                or any(not isinstance(row,list) or len(row)!=len(table['columns']) or any(not isinstance(c,str) or len(c)>1200 for c in row) for row in table['rows'])):
                raise ProviderError('Invalid analysis table dimensions or cells')
        final_review=self.call('Synthesis evidence reviewer',
                               'Check the proposed summary and analysis against the reviewed findings. '
                               'Return {"supported":true,"concerns":["..."]}. Set supported=false for new '
                               'unsupported factual assertions, concealed gaps, or suppressed council dissent. '
                               'Explicit recommendations and proposed requirements need not be proven facts. '
                               'This is model review, not independent certification.',
                               {'synthesis':synthesis,'reviewed_findings':accepted,
                                'material_gaps':self.gaps,'scope_limits':plan.get('scope_limits',[]),
                                'council':json.loads(council_file.read_text()) if council_file.exists() else None})
        self.store.save(run_id,'synthesis-review.json',final_review)
        if final_review.get('supported') is not True:
            self.error('Synthesis support review did not pass; draft retained and unsupported analysis withheld')
            self.gaps.extend(str(x) for x in final_review.get('concerns',[])[:8])
            synthesis={'title':self.request['question'],
                       'summary':'Reviewed findings are available below. The proposed narrative did not pass source-support review and has been withheld.',
                       'sections':[], 'council_synthesis':{},'requirements':self.requirements,
                       'workflow_steps':[],'unknowns':[]}
        else:
            chosen=synthesis.get('finding_ids')
            if isinstance(chosen,list) and chosen and all(isinstance(fid,str) and fid in {f['id'] for f in accepted} for fid in chosen):
                accepted=[f for f in accepted if f['id'] in chosen]
        self.coverage(plan,queries,analysis=synthesis)
        synthesis['coverage']=self.coverage_result
        self.gaps=[g for g in self.gaps if not g.startswith('Coverage ')]
        self.gaps.extend('Coverage '+c['status']+': '+c['question']+' — '+c['reason'] for c in self.coverage_result['criteria'] if c['status']!='answered')
        for finding in self.findings: finding['published']=finding['id'] in {f['id'] for f in accepted}
        self.store.save(run_id,'claims.json',self.findings)
        req=synthesis.get('requirements',self.requirements)
        if not isinstance(req,list): raise ProviderError('Invalid synthesis requirements')
        source_ids={s['id'] for s in self.sources if s['state']!='unavailable'}
        requirements=[dict(id=f'R{i:03}',text=x['text'],acceptance=x['acceptance'],
                           basis=[sid for sid in x.get('basis',[]) if isinstance(sid,str) and sid in source_ids]) for i,x in enumerate(req[:20],1)
                      if isinstance(x,dict) and isinstance(x.get('text'),str) and isinstance(x.get('acceptance'),str)]
        research_log=list(dict.fromkeys(self.gaps + [str(x) for x in synthesis.get('unknowns',[])] + [
            'Source selection, model review and advisory perspectives can be wrong. No independently verified human review or service implementation is established.',
            'Models share a provider; role separation is not provider diversity. Source snapshots and source contexts are bounded.',
        ]))
        # Keep the complete provenance trail without presenting historical questions as current decisions.
        self.store.save(run_id,'uncertainty-ledger.json',research_log)
        unknowns=list(dict.fromkeys(str(x) for x in synthesis.get('unknowns',[]) if isinstance(x,str) and x.strip()))[:6]
        if not unknowns:
            unknowns=['No consolidated decision questions were published. Inspect the retained research log before treating this result as complete.']
        record=dict(schema_version=1,title=str(synthesis.get('title') or self.request['question']),question=self.request['question'],
                    summary=str(synthesis.get('summary') or 'Partial research result'),sources=self.sources,
                    findings=[{**{k:f[k] for k in ('id','text','label','sources','quote','review','review_reason') if k in f},
                               'caveat':' '.join(dict.fromkeys([f['caveat']]+[d['caveat'] for d in self.findings if d.get('duplicate_of')==f['id']]))} for f in accepted],
                    requirements=requirements,unknowns=unknowns,research_log=research_log,
                    **({'mission':self.request['mission']} if self.request.get('mission') else {}))
        validate(record);self.store.save(run_id,'report.json',record)
        if self.request.get('mission'):self.mission_output(record,accepted)
        self.check()
        spec=None
        if self.request.get('preset')=='pre-build':
            try: spec=self.spec_doc(synthesis,accepted,requirements,unknowns)
            except (ProviderError,ValueError,KeyError,TypeError) as exc: self.error(f'Workstream spec doc withheld: {str(exc)[:200]}')
        from .exports import export_run
        outputs, export_errors=export_run(self.store.directory(run_id),record,synthesis,self.request['formats'],self.config,self.check)
        self.errors.extend(export_errors)
        if self.request.get('preset')=='pre-build':
            if spec:
                (self.store.directory(run_id)/'outputs').mkdir(exist_ok=True)
                (self.store.directory(run_id)/'outputs'/'spec.md').write_text(spec['markdown']);outputs=list(outputs)+['spec.md']
            acquired=bool(self.acquisition and self.acquisition['provider']=='crawlee' and self.acquisition['sourceHashes'])
            if not acquired: self.error('No crawler-collected (Crawlee or Scrapling plugin) source backs this result')
            self.store.save(run_id,'pre-build.json',{'schema':PRE_BUILD_SCHEMA,'preset':'pre-build','spec':spec,
                'sources':[{k:x[k] for k in ('id','title','url','state','artifact_sha256','crawler','fetcher') if k in x} for x in self.sources],
                'unknowns':unknowns,'artifacts':list(outputs),'acquisition':self.acquisition or {'provider':'unavailable','jobIds':[],'sourceHashes':[]}})
        partial=bool(self.errors or (self.request.get('preset')=='pre-build' and not spec) or any(f['review'] in ('unsupported','uncertain') for f in self.findings) or not requirements or any(c['status']!='answered' for c in self.coverage_result['criteria']))
        usage=self.provider_usage+[{'session':self.provider_session,**row} for row in getattr(self.model,'usage',[])]
        self.store.save(run_id,'usage.json',{'calls':len(self.role_calls),'session_calls':getattr(self.model,'calls',None),'roles':usage,
                                           'provider_usage_complete':len(usage)==len(self.role_calls),
                                           'limits':limits,'dollar_cost':'unavailable; subscription usage and native-search costs are not a hard monetary budget'})
        with self.store.lock:
            self.check()
            self.store.update(run_id,status='partial' if partial else 'completed',stage='done',finished_at=timestamp(),
                              outputs=outputs,errors=self.errors,findings=len(accepted),requirements=len(requirements))
