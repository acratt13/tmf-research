"""Bounded role artifacts over native knowledge references; no database or refresh owner."""
import hashlib
import json
import re


class KnowledgeShelfError(ValueError):
    def __init__(self, reason):
        self.reason=reason
        super().__init__('Native knowledge unavailable: '+reason)


def skill_passages(text):
    """Keep on-demand source skill bodies within the ordinary reader's budget."""
    parts=[];part=[];size=0
    for char in text:
        amount=len(char.encode())
        if size+amount>6000:
            parts.append(''.join(part));part=[];size=0
        part.append(char);size+=amount
    if part:parts.append(''.join(part))
    return parts


def package_knowledge(selection):
    """Render an already resolved, pinned selection into a portable role artifact."""
    if (not isinstance(selection, dict) or not isinstance(selection.get('sources'), list)
            or len(selection['sources']) > 12 or not isinstance(selection.get('gaps'), list)
            or len(selection['gaps']) > 40
            or selection.get('status') != ('partial' if selection['gaps'] else 'complete')):
        raise ValueError('Role knowledge needs a bounded source selection and explicit gaps')
    audience = {'builders', 'agents'}
    provenance = []
    lines = ['# Selected role knowledge', '',
             'Captured excerpts from the existing knowledge database. This artifact is not a new knowledge store.',
             'Source currentness below describes assembly time; check the pinned source before new work.', '']
    used = 0
    for source in selection['sources']:
        if (not isinstance(source, dict) or not re.fullmatch(r'kn-[a-f0-9]{12}', str(source.get('doc_id', '')))
                or not re.fullmatch(r'[a-f0-9]{64}', str(source.get('content_hash', '')))
                or (source.get('actor') and source.get('lane') != 'shared') or source.get('lane') not in ('shared', 'builder', 'agent')
                or not isinstance(source.get('source_currentness'), dict)
                or source['source_currentness'].get('state') not in ('current', 'indexed_only')
                or not isinstance(source.get('chunks'), list) or not 1 <= len(source['chunks']) <= 8):
            raise ValueError('Role knowledge source is unpinned, stale, private or incompatible')
        if source['lane'] != 'shared':
            audience &= {'builders' if source['lane'] == 'builder' else 'agents'}
        if not audience:
            raise ValueError('Role knowledge cannot combine builder-only and agent-only content')
        metadata = {key: source[key] for key in ('doc_id', 'content_hash', 'title', 'source_kind',
                                                'updated_at', 'lane', 'source_currentness', 'purpose')}
        if source.get('actor'):metadata['author']=source['actor']
        metadata['chunks'] = []
        lines += ['## ' + str(source['title']), '',
                  source['doc_id'] + ' · content hash ' + source['content_hash'],
                  'Selected for: ' + str(source['purpose']),
                  'Currentness at assembly: ' + source['source_currentness']['state'], '']
        seen = set()
        for chunk in source['chunks']:
            if (not isinstance(chunk, dict) or not isinstance(chunk.get('text'), str) or not chunk['text'].strip()
                    or any(type(chunk.get(key)) is not int or chunk[key] < 0 for key in ('index', 'start', 'end'))
                    or chunk['end']-chunk['start'] != len(chunk['text'].encode('utf-16-le'))//2
                    or (seen and chunk['index'] <= max(seen))):
                raise ValueError('Role knowledge needs distinct ordered chunk references and text')
            seen.add(chunk['index']);used += len(chunk['text'])
            if used > 48000:
                raise ValueError('Selected role knowledge exceeds the package passage budget')
            pin = {key: chunk[key] for key in ('index', 'start', 'end')}
            if (chunk.get('id')!=source['doc_id']+'@'+source['content_hash']+'#'+str(chunk['index'])
                    or not re.fullmatch(r'[a-f0-9]{64}',str(chunk.get('content_hash','')))
                    or hashlib.sha256(chunk['text'].encode()).hexdigest()!=chunk['content_hash']):
                raise ValueError('Role knowledge chunk integrity mismatch')
            pin.update(id=chunk['id'], content_hash=chunk['content_hash'])
            pin['sha256'] = hashlib.sha256(chunk['text'].encode()).hexdigest()
            metadata['chunks'].append(pin)
            lines += ['Chunk ' + str(chunk['index']) + ' · ' + pin['sha256'], '', chunk['text'], '']
        provenance.append(metadata)
    if selection['gaps']:
        lines += ['# Missing or unavailable knowledge', '',
                  'These gaps require scoped evidence gathering or source repair; no crawl was started by packaging.', '']
        for gap in selection['gaps']:
            lines += [json.dumps(gap, ensure_ascii=False, sort_keys=True), '']
    return {'knowledge/selection.json': (json.dumps(selection, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode(),
            'knowledge/role-knowledge.md': '\n'.join(lines).encode()}, provenance, 'both' if len(audience) == 2 else next(iter(audience))


def selections(value):
    """User-selected native pins; source text never chooses a connection or actor."""
    if not isinstance(value, list) or len(value) > 12:
        raise ValueError('Select at most twelve native knowledge documents')
    result=[]
    for row in value:
        if (not isinstance(row, dict) or set(row) != {'doc_id','content_hash','chunk_indexes','purpose'}
                or not re.fullmatch(r'kn-[a-f0-9]{12}', str(row.get('doc_id','')))
                or not re.fullmatch(r'[a-f0-9]{64}', str(row.get('content_hash','')))
                or not isinstance(row['purpose'], str) or not row['purpose'].strip() or len(row['purpose']) > 1000
                or not isinstance(row['chunk_indexes'], list) or not 1 <= len(row['chunk_indexes']) <= 8
                or any(type(i) is not int or not 0 <= i <= 100000 for i in row['chunk_indexes'])
                or len(set(row['chunk_indexes'])) != len(row['chunk_indexes'])):
            raise ValueError('Native knowledge selections need document/hash pins, distinct chunk indexes and role purpose')
        if any(prior['doc_id'] == row['doc_id'] for prior in result):
            raise ValueError('Select each native knowledge document once')
        result.append({**row,'chunk_indexes':sorted(row['chunk_indexes'])})
    return result


def collect_role_knowledge(requested, read_knowledge, check=lambda: None):
    """Consume Canon's additive read_knowledge contract, preserving exact chunk pins.

    The supplied reader owns actor binding and retrieval; this function only
    selects bounded passages. No search, refresh, file read or crawl happens here.
    Native ranges use JavaScript UTF-16 offsets, including across page boundaries.
    """
    sources=[];gaps=[];used=0
    for selected in selections(requested):
        check();offset=0;pieces={};metadata=None;reason=None
        try:
            for _ in range(128):
                check()
                page=read_knowledge({'id':selected['doc_id'],'expected_hash':selected['content_hash'],'offset':offset})
                if (not isinstance(page,dict) or page.get('doc_id') != selected['doc_id']
                        or page.get('content_hash') != selected['content_hash']):
                    reason='missing_or_changed';break
                state=(page.get('source_currentness') or {}).get('state')
                if state not in ('current','indexed_only'):
                    reason=state if state in ('changed','missing','unverified') else 'currentness_unavailable';break
                if page.get('lane') not in ('shared','builder','agent') or (page.get('actor') and page['lane']!='shared'):
                    reason='restricted';break
                facts={key:page.get(key) for key in ('doc_id','content_hash','title','source_kind','updated_at',
                                                     'lane','actor','source_currentness')}
                if any(not isinstance(facts[key],str) or not facts[key] for key in ('title','source_kind','updated_at')):
                    reason='incomplete_reference';break
                if metadata is not None and metadata != facts:
                    reason='changed_during_read';break
                metadata=facts
                raw=page.get('text');refs=page.get('chunk_refs')
                if not isinstance(raw,str) or not isinstance(refs,list) or page.get('offset')!=offset:
                    reason='incomplete_reference';break
                wire=raw.encode('utf-16-le','surrogatepass');end=offset+len(wire)//2
                beyond=False
                for ref in refs:
                    if (not isinstance(ref,dict) or any(type(ref.get(k)) is not int for k in ('index','start','end'))
                            or not offset<=ref['start']<ref['end']<=end
                            or ref.get('id') != selected['doc_id']+'@'+selected['content_hash']+'#'+str(ref['index'])
                            or not re.fullmatch(r'[a-f0-9]{64}',str(ref.get('content_hash','')))):
                        raise ValueError('Incomplete native chunk reference')
                    index=ref['index'];beyond=beyond or index>max(selected['chunk_indexes'])
                    if index not in selected['chunk_indexes']:continue
                    part=wire[(ref['start']-offset)*2:(ref['end']-offset)*2]
                    prior=pieces.get(index)
                    if prior:
                        if prior['end']!=ref['start'] or prior['content_hash']!=ref['content_hash']:
                            raise ValueError('Native chunk changed between pages')
                        prior['wire']+=part;prior['end']=ref['end']
                    else:pieces[index]={**ref,'wire':part}
                if sum(len(p['wire'])//2 for p in pieces.values())+used>48000:
                    reason='passage_budget_exceeded';break
                next_offset=page.get('next_offset')
                if next_offset is None or beyond:break
                if type(next_offset) is not int or next_offset!=end or next_offset<=offset or next_offset>1024000:
                    reason='read_budget_or_pagination';break
                offset=next_offset
            else:reason='read_budget_exceeded'
            if not reason:
                if set(pieces)!=set(selected['chunk_indexes']):reason='missing_chunks'
                else:
                    chunks=[]
                    for index in selected['chunk_indexes']:
                        part=pieces[index];content=part.pop('wire').decode('utf-16-le')
                        if hashlib.sha256(content.encode()).hexdigest()!=part['content_hash']:
                            reason='incomplete_chunk';break
                        chunks.append({**part,'text':content})
                    if not reason:
                        source={**metadata,'purpose':selected['purpose'],'chunks':chunks}
                        used+=sum(len(p['text']) for p in chunks);sources.append(source)
        except InterruptedError:raise
        except KnowledgeShelfError as error:reason=error.reason
        except (OSError,ValueError,TypeError,KeyError,RuntimeError):reason='source_unavailable'
        if reason:
            gaps.append({'doc_id':selected['doc_id'],'content_hash':selected['content_hash'],
                         'reason':reason,'research_query':selected['purpose']})
    return {'status':'partial' if gaps else 'complete','sources':sources,'gaps':gaps}


class KnowledgeShelf:
    """Configured caller of the existing governed HTTP read, never a DB opener.

    Connection/actor/authorization are operator configuration, not mission data.
    No fallback to a raw file, another actor or an older unpinned API is allowed.
    """
    def __init__(self, config):
        import os
        import urllib.request
        from urllib.parse import urlsplit
        from .client import NoRedirect
        cfg=config.get('native_knowledge') or {};base=cfg.get('url','')
        try:
            parsed=urlsplit(base)
            valid=(parsed.scheme=='http' and parsed.hostname=='127.0.0.1' and parsed.port
                   and not parsed.username and not parsed.password and not parsed.query
                   and not parsed.fragment and parsed.path in ('','/'))
        except ValueError:valid=False
        self.actor=cfg.get('actor','');token_env=cfg.get('token_env','')
        if (not valid or not isinstance(self.actor,str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}',self.actor)
                or cfg.get('auth','bearer') not in ('bearer','local-operator')):
            raise ValueError('Configure the existing native knowledge connection, actor and authorization by name')
        self.headers={}
        if cfg.get('auth','bearer')=='bearer':
            if not isinstance(token_env,str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',token_env):
                raise ValueError('Configure native knowledge authorization by name')
            token=os.environ.get(token_env)
            if not token:raise ValueError('Native knowledge authorization unavailable')
            self.headers={'Authorization':'Bearer '+token}
        self.base=base.rstrip('/')
        self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())

    def read(self, args):
        import urllib.error
        import urllib.request
        from urllib.parse import urlencode
        query=urlencode({**args,'actor':self.actor})
        request=urllib.request.Request(self.base+'/api/memory/knowledge/doc?'+query,
                                       headers=self.headers)
        try:
            with self.opener.open(request,timeout=5) as response:
                raw=response.read(256000)
                if len(raw)>=256000:raise ValueError('Native knowledge response exceeds bounded page')
                value=json.loads(raw)
        except urllib.error.HTTPError as error:
            status=error.code
            try:body=json.loads(error.read(4096))
            except (OSError,ValueError):body={}
            finally:error.close()
            if not isinstance(body,dict):body={}
            reason=({'knowledge_revision_changed':'indexed_revision_changed',
                     'knowledge_index_incomplete':'index_incomplete'}.get(body.get('reason'),'source_unavailable')
                    if status==409 else 'restricted_or_missing' if status==404
                    else 'access_unavailable' if status in (401,403) else 'source_unavailable')
            raise KnowledgeShelfError(reason) from None
        except (OSError,ValueError):raise ValueError('Native knowledge source unavailable; no fallback used') from None
        if not isinstance(value,dict) or value.get('status')!='ok':
            raise ValueError('Native knowledge source refused')
        return value


def resolve_role_knowledge(requested, config, check=lambda: None):
    requested=selections(requested)
    try:reader=KnowledgeShelf(config).read
    except ValueError:
        return {'status':'partial','sources':[],'gaps':[
            {'doc_id':r['doc_id'],'content_hash':r['content_hash'],'reason':'connection_unavailable',
             'research_query':r['purpose']} for r in requested]}
    return collect_role_knowledge(requested,reader,check)


def retained_selection(store,run_id):
    """Read the controller's captured selection, never bless edited current bytes."""
    directory=store.directory(run_id);path=directory/'evidence/role-knowledge.json'
    execution=directory/'execution.json';revision=directory/'revision.json'
    expected=(json.loads(execution.read_text()).get('evidence',{}).get('role-knowledge.json') if execution.exists()
              else json.loads(revision.read_text()).get('native_knowledge_sha256') if revision.exists() else None)
    if not path.is_file() or not expected or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
        raise ValueError('Native knowledge selection integrity mismatch')
    return json.loads(path.read_text())
