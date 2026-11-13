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
        auth=cfg.get('auth','bearer')
        self.headers={}
        self.token=None
        if auth=='local-system':
            # Canon serviceIdentity.ts explicitly admits its loopback system owner;
            # MC's own tmf.canonSections uses this same API with author attribution.
            author=cfg.get('author')
            if not isinstance(author,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}',author):
                raise CanonUnavailable('Canon local-system connection needs its configured author')
            self.headers={'X-Canon-Actor':author}
        elif auth=='bearer':
            if not isinstance(token_name, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', token_name):
                raise CanonUnavailable('Canon connection unavailable: configure token_env by name')
            self.token = os.environ.get(token_name)
            if not self.token:
                raise CanonUnavailable('Canon connection unavailable: named authorization is missing')
            self.headers={'Authorization':'Bearer '+self.token}
        else:raise CanonUnavailable('Unsupported Canon connection authorization mode')
        self.base, self.scope = base.rstrip('/'), scope
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def request(self, path, payload=None, missing_ok=False):
        data = encoded(payload).encode() if payload is not None else None
        request = urllib.request.Request(self.base + path, data=data, headers={
            'Content-Type': 'application/json', **self.headers})
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
            if missing_ok and status==404:return None
            raise CanonUnavailable(f'Canon refused the request (HTTP {status}); retry after resolving the connection or revision conflict') from None
        except (OSError, ValueError, urllib.error.URLError):
            raise CanonUnavailable('Canon connection unavailable or response unreadable') from None

    def read(self, record_id, revision=None):
        if not isinstance(record_id,str) or not re.fullmatch(r'cn-[a-f0-9-]{36}',record_id):
            raise ValueError('Use a Canon record identity')
        if revision is not None and (type(revision) is not int or revision<1):raise ValueError('Use an exact positive Canon revision')
        value=self.request('/api/canon/organization/entries/'+record_id+(f'?revision={revision}' if revision else ''))
        entry=value.get('entry',{})
        fields=entry.get('fields',{})
        if (entry.get('id')!=record_id or (revision is not None and entry.get('revision')!=revision)
                or fields.get('source')!='tmf-research'
                or not str(fields.get('sourceId','')).startswith('tmf-research:v1:'+self.scope+':')):
            raise CanonUnavailable('Canon reference does not belong to this Research connection and namespace')
        return entry

    def company_record(self, host):
        from .missions import company_domain
        host=company_domain(host);found=[]
        # Reuse a legacy www identity as well; never manufacture a second identity
        # or merge two already-distinct reviewed entities by convention.
        for spelling in (host,'www.'+host):
            key='tmf-research:v1:'+self.scope+':company:'+digest(spelling)
            detail=self.request('/api/canon/organization/entries/'+stable_id(key),missing_ok=True)
            if detail is None:continue
            entry=detail.get('entry',{});fields=entry.get('fields',{})
            payload={}
            try:
                payload=json.loads(entry['body'])
                if not isinstance(payload,dict):raise ValueError('Identity is not an object')
                matches=company_domain(payload.get('domain'))==host
            except (ValueError,TypeError,KeyError):matches=False
            if (entry.get('id')!=stable_id(key) or fields.get('sourceId')!=key or fields.get('source')!='tmf-research'
                    or not isinstance(payload,dict) or payload.get('entity')!='company-identity' or not matches):
                raise CanonUnavailable('Stored company identity conflicts with this Research namespace or domain')
            found.append(detail)
        if len(found)>1:raise CanonUnavailable('Multiple existing company identities require review; none were merged or replaced')
        return found[0] if found else None

    def company_history(self, host, exclude_run=None, limit=3):
        from .missions import company_domain
        host=company_domain(host);detail=self.company_record(host)
        result={'status':'not-found','identity':None,'investigations':[],'truncated':False,
                'scope':'Up to 30 linked current entries; original revisions remain in Canon'}
        if detail is None:return result
        entry=detail['entry'];result.update(status='available',identity={'id':entry['id'],'revision':entry['revision']})
        links=list(dict.fromkeys(row.get('from') for row in detail.get('backlinks',[]) if isinstance(row,dict) and isinstance(row.get('from'),str)))
        result['truncated']=len(links)>30
        prefix='tmf-research:v1:'+self.scope+':'
        for record_id in links[:30]:
            if not re.fullmatch(r'cn-[a-f0-9-]{36}',record_id):continue
            value=self.request('/api/canon/organization/entries/'+record_id,missing_ok=True)
            if value is None:continue
            previous=value.get('entry',{});fields=previous.get('fields',{})
            if fields.get('source')!='tmf-research' or not str(fields.get('sourceId','')).startswith(prefix):continue
            if exclude_run and str(fields['sourceId']).startswith(prefix+'mission:'+exclude_run+':'):continue
            try:
                body=json.loads(previous['body']);item=body['intelligence']
                matches=company_domain(item['domain'])==host
            except (ValueError,TypeError,KeyError):continue
            if not matches or body.get('entity') not in ('company-investigation','lead'):continue
            result['investigations'].append({'reference':{'id':previous['id'],'revision':previous['revision']},
                'research_date':item.get('research_date'),'review_status':fields.get('reviewStatus'),'intelligence':item})
        result['investigations'].sort(key=lambda row:(row.get('research_date') or '',row['reference']['id']),reverse=True)
        result['truncated']=result['truncated'] or len(result['investigations'])>limit
        result['investigations']=result['investigations'][:limit]
        return result

    def put(self, key, title, payload, links):
        body = encoded(payload)
        fields = {'source': 'tmf-research', 'sourceId': key, 'sourceHash': digest(payload),
                  'status': 'draft', 'reviewStatus': 'candidate',
                  **({'profession':payload['profession']} if isinstance(payload.get('profession'),str) else {})}
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
        findings = [];finding_refs={}
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
            if finding.get('id'):finding_refs[finding['id']]=ref
            receipt['references'].append({'kind': 'finding', **ref})
            store.save(run_id, 'canon-publication.json', {**receipt, 'status': 'partial'})
        intelligence_path=store.directory(run_id)/'intelligence.json'
        intelligence_refs=[]
        if intelligence_path.exists():
            intelligence=json.loads(intelligence_path.read_text())
            def remember(kind,ref):
                receipt['references'].append({'kind':kind,**ref})
                store.save(run_id,'canon-publication.json',{**receipt,'status':'partial'})
            intelligence_refs=publish_intelligence(connection,prefix,mission_key,intelligence,finding_refs,remember,check)
        check()
        payload = {'entity': 'research-mission', 'run_id': run_id, 'research_status': state['status'],
                   'report_sha256': digest(report), 'report': report, 'source_revisions': sources,
                   'finding_revisions': findings, **({'intelligence_references':intelligence_refs} if intelligence_refs else {}), 'verification': 'candidate; no independent certification',
                   'output_references': [{'run_id': run_id, 'name': name} for name in state.get('outputs', [])]}
        links = [{'to': r['id'], 'kind': 'source'} for r in sources.values()]
        links += [{'to': r['id'], 'kind': 'related'} for r in findings+intelligence_refs]
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


def publish_intelligence(connection, prefix, mission_key, intelligence, finding_refs, remember, check):
    """Logical research entities use the existing Knowledge entries and typed links."""
    refs=[]
    def put(kind,key,title,payload,links):
        check()
        ref=connection.put(key,title,payload,links)
        remember(kind,ref);refs.append({'kind':kind,**ref})
        return ref
    def support(ids):
        if not isinstance(ids,list) or not ids or any(i not in finding_refs for i in ids):
            raise CanonUnavailable('Intelligence publication cites a missing retained finding')
        return [{'to':finding_refs[i]['id'],'kind':'supported-by'} for i in dict.fromkeys(ids)]
    def proposal(specialty,knowledge):
        value={**specialty,'status':'draft','grants_authority':False,'hub_import_status':'not-connected',
               'knowledge_references':knowledge}
        return put('specialty',prefix+'specialty:'+digest(value),'Draft expertise: '+value['name'],
                   {'entity':'specialty-definition','definition':value},
                   [{'to':r['id'],'kind':'learned-from'} for r in knowledge])
    kind=intelligence.get('mission_type')
    if intelligence.get('review_status')!='candidate' or intelligence.get('schema')!='tmf-research-intelligence/1':
        raise CanonUnavailable('Intelligence is not a retained candidate output')
    if kind=='council':
        config=intelligence.get('configuration',[])
        ref=put('council-configuration',prefix+'council:'+digest(config),'Draft research Council configuration',
                {'entity':'council-configuration','specialists':config,'status':'draft','deploys_agents':False},[])
        put('council-result',mission_key+':council:'+digest(intelligence),'Research Council candidate result',
            intelligence,[{'to':ref['id'],'kind':'source'}])
    else:
        if intelligence.get('verification')!='model-reviewed':
            raise CanonUnavailable('Intelligence publication requires its retained output review')
        for item in intelligence.get('companies',intelligence.get('leads',[])):
            existing=connection.company_record(item['domain'])
            if existing:
                entry=existing['entry'];identity={'id':entry['id'],'revision':entry['revision']}
                remember('company-identity',identity);refs.append({'kind':'company-identity',**identity})
            else:
                identity=put('company-identity',prefix+'company:'+digest(item['domain']),
                    'Company domain identity: '+item['domain'],
                    {'entity':'company-identity','domain':item['domain'],'verification':'domain-key only; identity association is candidate evidence'},[])
            key=mission_key+':'+('lead:' if kind=='leads' else 'company:')+digest(item['domain'])
            payload={'entity':'lead' if kind=='leads' else 'company-investigation','intelligence':item,
                     'run_id':intelligence['run_id'],'finding_revisions':{i:finding_refs[i] for i in item['finding_ids']}}
            links=[{'to':identity['id'],'kind':'related'}]+support(item['finding_ids'])
            links += [{'to':row['reference']['id'],'kind':'learned-from'} for row in item.get('continuity',{}).get('previous',[])]
            observation=put('company-observation',key+':snapshot:'+digest(payload),'Company observation: '+item['name'],
                {**payload,'entity':'company-observation'},links)
            put('lead' if kind=='leads' else 'company-investigation',key,'Research candidate: '+item['name'],
                payload,links+[{'to':observation['id'],'kind':'source'}])
        if 'knowledge' in intelligence:
            value=intelligence['knowledge'];profession=value['profession']
            domain_refs=[]
            for item in value['domains']:
                if item['label']=='unknown':continue
                record={'entity':'professional-knowledge','profession':profession,'knowledge':item,
                        'finding_revisions':{i:finding_refs[i] for i in item['finding_ids']}}
                ref=put('professional-knowledge',prefix+'knowledge:'+digest(record),
                    'Knowledge candidate: '+profession+' / '+item['heading'],record,support(item['finding_ids']))
                domain_refs.append(ref)
            if not domain_refs:raise CanonUnavailable('Professional knowledge has no sourced domain candidates')
            collection=put('knowledge-collection',prefix+'collection:'+digest({'profession':profession,'references':domain_refs}),
                'Knowledge collection candidate: '+profession,{'entity':'knowledge-collection','profession':profession,
                    'knowledge_references':domain_refs,'status':'draft'},[{'to':r['id'],'kind':'related'} for r in domain_refs])
            proposal(value['specialty'],[collection])
        if 'market' in intelligence:
            market=intelligence['market']
            ids=list(dict.fromkeys(i for s in market['sections'] for i in s['finding_ids']))
            put('market',mission_key+':market:'+digest(market),'Market candidate: '+market['name'],
                {'entity':'market-research','market':market},support(ids))
        if 'person' in intelligence:
            person=intelligence['person']
            ids=list(dict.fromkeys(i for s in person['documented_work']+person['communication_patterns'] for i in s['finding_ids']))
            profile=put('person-research',mission_key+':person:'+digest(person),'Simulation research draft: '+person['name'],
                {'entity':'person-research','profile':person,'status':'draft','creates_agent':False},support(ids))
            proposal(person['generic_specialty'],[profile])
    return refs


def attach_company_continuity(intelligence, config, error=lambda message:None, check=lambda:None):
    """Freeze exact prior revisions and literal description differences in this run.

    This is a comparison of evidence-backed research, never a claim that a
    company's operations changed merely because a model used different wording.
    """
    rows=intelligence.get('companies',intelligence.get('leads',[]))
    if not rows:return
    try:connection=CanonConnection(config)
    except CanonUnavailable as exc:
        for row in rows:row['continuity']={'status':'unavailable','reason':str(exc),'previous':[],'changes':[]}
        return
    for row in rows:
        check()
        try:
            history=connection.company_history(row['domain'],exclude_run=intelligence['run_id'])
            previous=history.pop('investigations')
            history['previous']=[{k:p[k] for k in ('reference','research_date','review_status')} for p in previous]
            history['changes']=[]
            history['comparison_scope']='Literal retained research descriptions; differences do not establish independently verified business changes'
            if previous:
                prior=previous[0]['intelligence']
                current_fields={**row.get('sections',{}),**row.get('startup_sections',{})}
                prior_fields={**prior.get('sections',{}),**prior.get('startup_sections',{})}
                if not current_fields:
                    current_fields={key:{'text':row[key],'label':'inferred'} for key in ('industry','opportunity','potential_service','estimated_fit')}
                    prior_fields={key:{'text':prior.get(key,''),'label':'inferred'} for key in current_fields}
                    for item,fields in ((row,current_fields),(prior,prior_fields)):
                        fields.update({key:item[key] for key in ('industry_evidence','location','opportunity_basis') if isinstance(item.get(key),dict)})
                        for key,fit in item.get('scope_fit',{}).items():
                            fields['scope_'+key]={'text':fit['status']+': '+fit['reason'],'label':fit['label']}
                for key,value in current_fields.items():
                    old=prior_fields.get(key)
                    label=value.get('label');status='unknown' if label=='unknown' else 'new' if old is None else (
                        'unchanged' if (old.get('label'),re.sub(r'\s+',' ',old.get('text','')).strip())==
                            (label,re.sub(r'\s+',' ',value['text']).strip()) else 'research-description-changed')
                    history['changes'].append({'field':key,'status':status,'previous_text':old.get('text') if old else None,
                        'previous_label':old.get('label') if old else None,'current_text':value['text'],'current_label':label,
                        'previous_reference':previous[0]['reference']})
            row['continuity']=history
        except CanonUnavailable as exc:
            row['continuity']={'status':'unavailable','reason':str(exc),'previous':[],'changes':[]}
            error('Company continuity unavailable: '+str(exc))


def operator_config(config=None, environment=None):
    """MC's existing per-plugin environment is operator-owned and survives updates."""
    env=os.environ if environment is None else environment
    result=dict(config or {})
    if 'canon' not in result and env.get('TMF_RESEARCH_CANON_URL'):
        result['canon']={'url':env['TMF_RESEARCH_CANON_URL'],
            'identity_scope':env.get('TMF_RESEARCH_CANON_SCOPE',''),
            'auth':env.get('TMF_RESEARCH_CANON_AUTH','bearer'),
            'author':env.get('TMF_RESEARCH_CANON_AUTHOR','tmf-research'),
            'token_env':env.get('TMF_RESEARCH_CANON_TOKEN_ENV','MC_CANON_TOKEN')}
    return result
