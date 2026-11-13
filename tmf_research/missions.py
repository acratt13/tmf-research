"""Versioned mission configuration and evidence-bound domain outputs.

The existing ResearchEngine executes every mission. These are inputs and output
contracts, not another runtime, scheduler, knowledge store or permissions model.
"""
import re
from urllib.parse import urlsplit

SCHEMA = 'tmf-research-mission/1'
TYPES = {
    'general': {'name': 'General research', 'purpose': 'Investigate a scoped question', 'outputs': ['report']},
    'technology': {'name': 'Technology research', 'purpose': 'Investigate software, APIs and integration evidence', 'outputs': ['report']},
    'company': {'name': 'Company intelligence', 'purpose': 'Prepare a sourced pre-consultation briefing', 'outputs': ['companies']},
    'startup': {'name': 'Startup intelligence', 'purpose': 'Investigate public company, founder and funding evidence', 'outputs': ['companies']},
    'leads': {'name': 'Lead discovery', 'purpose': 'Find deduplicated evidence-backed opportunities, without outreach', 'outputs': ['leads']},
    'market': {'name': 'Market research', 'purpose': 'Compare a scoped market and its alternatives', 'outputs': ['market']},
    'profession': {'name': 'Professional expertise', 'purpose': 'Organize sourced expertise and a draft specialty definition', 'outputs': ['knowledge']},
    'person': {'name': 'Public-person research', 'purpose': 'Document professional work and clearly labeled interpretations', 'outputs': ['person']},
    'council': {'name': 'Council research', 'purpose': 'Run distinct specialist perspectives through the existing Council', 'outputs': ['council']},
}
COMPANY_SECTIONS = ('overview', 'products_and_business_model', 'market', 'competitors', 'digital_presence',
                    'developments', 'potential_problems', 'opportunities', 'consulting_questions', 'possible_services', 'unknowns')
KNOWLEDGE_DOMAINS = ('foundations', 'terminology', 'procedures', 'decisions', 'standards', 'workflows', 'tools', 'examples', 'failure_patterns')


def text(value, name, limit=3000, required=False):
    if not isinstance(value, str) or len(value) > limit or (required and not value.strip()):
        raise ValueError(f'{name} must be {"nonempty " if required else ""}text of at most {limit} characters')
    return value.strip()


def texts(value, name, limit=40):
    if not isinstance(value, list) or len(value) > limit:
        raise ValueError(f'{name} must be a list of at most {limit} texts')
    return list(dict.fromkeys(text(x, name, required=True) for x in value))


def domain(value):
    value = text(value, 'company domain', 253, True).lower()
    parsed = urlsplit('https://' + value)
    if (parsed.hostname != value or parsed.username or parsed.password or parsed.port
            or not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?', value) or '.' not in value):
        raise ValueError('Use a company domain without a URL path or credentials')
    return value


def normalize(value):
    if value is None: return None
    if not isinstance(value, dict) or value.get('schema') != SCHEMA or value.get('type') not in TYPES:
        raise ValueError('Use a supported versioned research mission; security assessment is not implemented')
    allowed = {'schema', 'type', 'target', 'scope', 'permitted_domains', 'excluded_domains', 'collection', 'budgets',
               'verification', 'completion_criteria', 'specialists', 'profession', 'public_person', 'consent', 'knowledge_refs'}
    if set(value) - allowed: raise ValueError('Unknown mission fields: ' + ', '.join(sorted(set(value) - allowed)))
    result = {'schema': SCHEMA, 'type': value['type'], 'target':text(value.get('target', ''), 'mission target', required=True),
              'scope':text(value.get('scope', ''), 'mission scope'),
              'permitted_domains':[domain(x) for x in texts(value.get('permitted_domains', []), 'permitted domains')],
              'excluded_domains':[domain(x) for x in texts(value.get('excluded_domains', []), 'excluded domains')],
              'verification':texts(value.get('verification', []), 'verification requirements'),
              'completion_criteria':texts(value.get('completion_criteria', []), 'completion criteria'),
              'profession':text(value.get('profession', ''), 'profession', 200)}
    collection = value.get('collection', 'plugins' if value['type'] in ('company', 'startup', 'leads', 'market') else 'web')
    if collection not in ('web', 'plugins'): raise ValueError('Select web or plugins collection')
    result['collection'] = collection
    budgets = value.get('budgets', {})
    if not isinstance(budgets, dict) or set(budgets) - {'sources', 'calls', 'rounds', 'concurrency'}:
        raise ValueError('Unknown mission resource budget')
    for key, amount in budgets.items():
        if type(amount) is not int or amount < (0 if key == 'rounds' else 1): raise ValueError('Budgets must be explicit nonnegative counts; sources/calls/concurrency must be positive')
    result['budgets'] = dict(budgets)
    specialists = value.get('specialists', [])
    if not isinstance(specialists, list) or len(specialists) > 6:
        raise ValueError('Use at most six configured Council specialists')
    result['specialists'] = []
    for specialist in specialists:
        if not isinstance(specialist, dict) or set(specialist) - {'name', 'responsibilities'}:
            raise ValueError('A specialist supplies name and responsibilities, not permissions or executable configuration')
        result['specialists'].append({'name':text(specialist.get('name'), 'specialist name', 80, True),
                                     'responsibilities':text(specialist.get('responsibilities'), 'specialist responsibilities', 1000, True)})
    if (len({s['name'].casefold() for s in result['specialists']}) != len(result['specialists'])
            or len({s['responsibilities'].casefold() for s in result['specialists']}) != len(result['specialists'])):
        raise ValueError('Council specialists need distinct names and responsibilities')
    if value['type'] == 'council' and len(result['specialists']) < 2:
        raise ValueError('A custom council needs at least two distinct specialist responsibilities')
    references=value.get('knowledge_refs',[])
    if not isinstance(references,list) or len(references)>12:raise ValueError('Select at most twelve Canon knowledge revisions')
    result['knowledge_refs']=[]
    for reference in references:
        if (not isinstance(reference,dict) or set(reference)!={'id','revision'}
                or not isinstance(reference.get('id'),str) or not re.fullmatch(r'cn-[a-f0-9-]{36}',reference['id'])
                or type(reference.get('revision')) is not int or reference['revision']<1):
            raise ValueError('Knowledge references require an exact Canon id and positive revision')
        if reference not in result['knowledge_refs']:result['knowledge_refs'].append(dict(reference))
    if value['type'] == 'person':
        public = value.get('public_person')
        if not isinstance(public, bool): raise ValueError('State whether the subject is a public person')
        consent = text(value.get('consent', ''), 'person research consent', 1000)
        if not public and not consent: raise ValueError('Private-person simulation research requires documented consent')
        result.update(public_person=public, consent=consent)
    return result


def catalog():
    return {'schema': SCHEMA, 'types': TYPES, 'input_fields': ['target', 'scope', 'permitted_domains', 'excluded_domains',
            'collection', 'budgets', 'verification', 'completion_criteria', 'specialists', 'profession', 'public_person', 'consent', 'knowledge_refs'],
            'tools': ['submit', 'status', 'result', 'cancel', 'publish', 'missions', 'pause', 'resume', 'knowledge'],
            'authority': 'All generated knowledge and specialty definitions remain candidates; no agent creation, role deployment, recurring missions or security assessment',
            'canvas': {'app':'tmf-research', 'query':{'run':'saved run id'}},
            'limitations': ['Model review is not independent factual certification', 'Hub role-socket import and distributed runtime acceptance are not established']}


def permits(mission, url):
    if not mission: return True
    try: host = urlsplit(url).hostname
    except ValueError: return False
    if not host: return False
    host = host.lower()
    matches = lambda ds: any(host == d or host.endswith('.' + d) for d in ds)
    return not matches(mission['excluded_domains']) and (not mission['permitted_domains'] or matches(mission['permitted_domains']))


def output_instruction(mission):
    kind = mission['type']
    common = ('Use only the supplied reviewed findings. Every nonempty factual section needs finding_ids from those findings. '
              'Missing information stays unknown, never guessed. Recommendations are inferred or proposed. '
              'Return JSON only. Do not create agents, permissions, outreach, approved knowledge or deployment receipts. ')
    if kind in ('company', 'startup'):
        return common + 'Return {"companies":[{"name":"...","domain":"example.test","finding_ids":["F001"],"sections":{' + ','.join('"'+s+'":{"text":"...","finding_ids":["F001"],"label":"documented|inferred|proposed|unknown"}' for s in COMPANY_SECTIONS) + '}}]}. Funding and traction claims must preserve dates and public-announcement scope.'
    if kind == 'leads':
        return common + 'Return {"leads":[{"company":"...","domain":"example.test","industry":"...","opportunity":"...","potential_service":"...","estimated_fit":"...","confidence":"low|medium|high","finding_ids":["F001"],"assumptions":["..."]}]}. Explain why the opportunity may fit; a proposed problem is an inference, not a confirmed internal fact.'
    if kind == 'market':
        return common + 'Return {"market":{"name":"...","sections":[{"heading":"...","text":"...","finding_ids":["F001"],"label":"documented|inferred|proposed|unknown"}]}}. Cover categories, competitors, pricing, business models, customer needs, trends, applicable regulation and alternatives; missing evidence remains unknown.'
    if kind == 'profession':
        return common + 'Return {"knowledge":{"profession":"...","domains":[{"heading":"...","text":"...","finding_ids":["F001"],"label":"documented|inferred|proposed|unknown"}],"specialty":{"name":"...","purpose":"...","responsibilities":["..."],"procedures":["..."],"instructions":["..."],"evaluation_criteria":["..."],"required_capabilities":["..."]}}}. Cover foundations, terminology, procedures, decision frameworks, standards, workflows, tools, examples and failure patterns. Specialty is an expertise proposal, never an authority role or agent identity.'
    if kind == 'person':
        return common + 'Return {"person":{"name":"...","documented_work":[{"heading":"...","text":"...","finding_ids":["F001"],"label":"documented|inferred|proposed|unknown"}],"communication_patterns":[{"heading":"...","text":"...","finding_ids":["F001"],"label":"inferred|unknown"}],"generic_specialty":{"name":"...","purpose":"...","responsibilities":["..."],"procedures":["..."],"instructions":["..."],"evaluation_criteria":["..."],"required_capabilities":["..."]}}}. This is a documented professional simulation draft; do not infer private thoughts, motives or psychological facts. No voice cloning or claims of identity/endorsement.'
    return common


def validate_output(mission, raw, findings, run_id, at):
    if not isinstance(raw, dict): raise ValueError('Mission output must be an object')
    known = {f['id']:f for f in findings}
    def refs(value):
        if not isinstance(value, list) or not value or any(not isinstance(i,str) or i not in known for i in value):
            raise ValueError('Mission output must cite reviewed finding identities')
        return list(dict.fromkeys(value))
    def section(value):
        if not isinstance(value,dict): raise ValueError('Mission section must be an object')
        label = value.get('label')
        if label not in ('documented','observed','inferred','proposed','unknown'): raise ValueError('Mission section needs an evidence label')
        reference = refs(value.get('finding_ids')) if label != 'unknown' else []
        if label in ('documented','observed') and any(known[i]['label'] not in ('documented','observed') for i in reference):
            raise ValueError('Inferences or proposals cannot be promoted into factual mission sections')
        if label=='observed' and any(known[i]['label']!='observed' for i in reference):
            raise ValueError('Documented findings cannot be promoted into observed execution')
        return {'heading':text(value.get('heading',''), 'section heading', 200), 'text':text(value.get('text'), 'section text', required=True),
                'label':label,'finding_ids':reference}
    def sections(values):
        if not isinstance(values,list) or not values: raise ValueError('Mission output needs sourced sections')
        return [section(s) for s in values]
    def specialty(value):
        if not isinstance(value,dict): raise ValueError('Missing draft specialty definition')
        if any(not value.get(key) for key in ('responsibilities','instructions','evaluation_criteria')):
            raise ValueError('A draft specialty needs responsibilities, instructions and evaluation criteria')
        return {'name':text(value.get('name'),'specialty name',200,True),'purpose':text(value.get('purpose'),'specialty purpose',required=True),
                **{k:texts(value.get(k,[]),k) for k in ('responsibilities','procedures','instructions','evaluation_criteria','required_capabilities')},
                'status':'draft','grants_authority':False,'hub_import_status':'not-connected', 'knowledge_references':[]}
    result={'schema':'tmf-research-intelligence/1','mission_type':mission['type'],'run_id':run_id,'created_at':at,
            'review_status':'candidate','verification':'unreviewed','independent_verification':False}
    kind=mission['type']
    if kind in ('company','startup','leads'):
        collection='leads' if kind=='leads' else 'companies'; rows=raw.get(collection)
        if not isinstance(rows,list) or not rows: raise ValueError('No sourced company/lead output was produced')
        entries={}
        for row in rows:
            if not isinstance(row,dict): raise ValueError('Intelligence entry must be an object')
            host=domain(row.get('domain')); reference=refs(row.get('finding_ids'))
            item={'id':'company:'+host,'company_id':'company:'+host,'domain':host,
                  'name':text(row.get('company' if kind=='leads' else 'name'),'company name',200,True),
                  'finding_ids':reference,'research_date':at,'last_verification':None,'review_status':'candidate'}
            if kind=='leads':
                confidence=row.get('confidence')
                if confidence not in ('low','medium','high'): raise ValueError('Lead confidence must be low, medium or high')
                item.update(id='lead:'+host,label='inferred',confidence=confidence,
                            **{k:text(row.get(k),k,required=True) for k in ('industry','opportunity','potential_service','estimated_fit')},
                            assumptions=texts(row.get('assumptions',[]),'lead assumptions'))
            else:
                source_sections=row.get('sections')
                if not isinstance(source_sections,dict) or set(source_sections)!=set(COMPANY_SECTIONS):
                    raise ValueError('Company briefing must include every consultation section, marking gaps unknown')
                item['sections']={key:section(value) for key,value in source_sections.items()}
            if host in entries:
                prior=entries[host]
                if {k:v for k,v in prior.items() if k!='finding_ids'} != {k:v for k,v in item.items() if k!='finding_ids'}:
                    raise ValueError('Conflicting duplicate company/lead identities require review')
                prior['finding_ids']=list(dict.fromkeys(prior['finding_ids']+reference))
            else:entries[host]=item
        result[collection]=list(entries.values())
    elif kind=='market':
        market=raw.get('market',{})
        result['market']={'name':text(market.get('name'),'market name',200,True),'sections':sections(market.get('sections'))}
    elif kind=='profession':
        value=raw.get('knowledge',{})
        result['knowledge']={'profession':text(value.get('profession'),'profession',200,True),
                             'domains':sections(value.get('domains')),'specialty':specialty(value.get('specialty'))}
    elif kind=='person':
        value=raw.get('person',{})
        result['person']={'name':text(value.get('name'),'person name',200,True),'simulation_label':'Research-grounded AI simulation draft; not the person and no endorsement',
                          'private_thoughts':'unknown','documented_work':sections(value.get('documented_work')),
                          'communication_patterns':sections(value.get('communication_patterns')),
                          'generic_specialty':specialty(value.get('generic_specialty'))}
        if any(s['label'] not in ('inferred','unknown') for s in result['person']['communication_patterns']):
            raise ValueError('Communication interpretation must remain labeled inference')
    return result
