"""Portable expertise through MC's existing skill-plugin import boundary.

Canon remains the knowledge origin. Packages carry a draft definition and exact
references, never worker identity, executable code, permissions or knowledge bodies.
"""
import hashlib
import io
import json
import os
import re
import tempfile
import zipfile

from .missions import text, texts
from . import __version__


def reference(value):
    if (not isinstance(value, dict) or not isinstance(value.get('id'), str)
            or not re.fullmatch(r'cn-[a-f0-9-]{36}', value['id'])
            or type(value.get('revision')) is not int or value['revision'] < 1):
        raise ValueError('Role knowledge needs exact Canon identities and revisions')
    return {'id': value['id'], 'revision': value['revision']}


def build_role_plugin(connection, source, run_id, check=lambda: None):
    """Read through the configured Canon connection; return deterministic bytes."""
    source = reference(source)
    def read(ref, entity):
        check()
        entry = connection.read(ref['id'], ref['revision'])
        body = json.loads(entry['body'])
        if not isinstance(body, dict) or body.get('entity') != entity:
            raise ValueError('Role references an incompatible Canon knowledge kind')
        return body
    body = read(source, 'specialty-definition')
    raw = body.get('definition')
    if not isinstance(raw, dict):
        raise ValueError('Role definition is missing')
    definition = {key: text(raw.get(key), key, limit, True)
                  for key, limit in (('name', 200), ('purpose', 3000))}
    for key in ('responsibilities', 'procedures', 'instructions', 'evaluation_criteria', 'required_capabilities'):
        definition[key] = texts(raw.get(key, []), key)
    if any(not definition[key] for key in ('responsibilities', 'instructions', 'evaluation_criteria')):
        raise ValueError('Role needs responsibilities, instructions and evaluation criteria')
    definition['required_capabilities'] = list(dict.fromkeys(definition['required_capabilities'] +
        ['mcp.tmf-research/tmf-research_knowledge']))
    refs = raw.get('knowledge_references')
    if not isinstance(refs, list) or not 1 <= len(refs) <= 12:
        raise ValueError('Role needs one to twelve Canon knowledge collections')
    refs = [reference(ref) for ref in refs]
    validated = []
    for ref in refs:
        collection = read(ref, 'knowledge-collection')
        members = collection.get('knowledge_references')
        if not isinstance(members, list) or not 1 <= len(members) <= 40:
            raise ValueError('Role knowledge collection is empty or exceeds the bounded read')
        for member in members:
            member = reference(member)
            if member not in validated:
                read(member, 'professional-knowledge')
                validated.append(member)
    definition.update(status='draft', grants_authority=False, hub_import_status='not-connected',
                      knowledge_references=refs)
    plugin_id = 'research-role-' + source['id'][3:]
    version = '0.1.' + str(source['revision'])
    role = {'entity': 'specialty-definition', 'definition': definition,
            'provenance': {'role': source, 'knowledge': validated, 'source_run_id': run_id,
                           'generator': 'tmf-research', 'generator_version': __version__, 'package_version': version}}
    manifest = {'id': plugin_id, 'name': definition['name'], 'version': version,
                'description': definition['purpose'], 'provider': 'tmf-research',
                'audience': 'both', 'skills': 'skills', 'licence': 'UNLICENSED',
                'provides': [{'id': 'skill.' + plugin_id, 'kind': 'skill', 'description': definition['purpose']}],
                'permissions': [], 'secretRefs': []}
    # JSON-quoted YAML values prevent role text from adding frontmatter metadata.
    skill = '\n'.join(['---', 'name: ' + json.dumps(plugin_id),
                       'description: ' + json.dumps(definition['purpose'], ensure_ascii=False), '---', '',
                       '# ' + definition['name'], '',
                       'Draft professional expertise; candidate research is not an approved operating rule.',
                       'This package grants no authority. Worker identity, history and permissions remain with MC.',
                       'Required capabilities below are requests, not grants. Use the current authorized toolbelt.', '',
                       'Source role: ' + source['id'] + ' revision ' + str(source['revision']), '',
                       '## Canon knowledge', '',
                       'Read these exact revisions using mcp.tmf-research/tmf-research_knowledge (id and revision).',
                       'Read the collection, then its relevant professional-knowledge references. Preserve source labels,',
                       'evidence, dates and uncertainty. If unavailable, report the missing knowledge; do not invent it.', '',
                       *['- ' + ref['id'] + ' revision ' + str(ref['revision']) for ref in refs], '',
                       '## Purpose', '', definition['purpose'], ''])
    for key in ('responsibilities', 'procedures', 'instructions', 'evaluation_criteria', 'required_capabilities'):
        skill += '\n## ' + key.replace('_', ' ').capitalize() + '\n\n'
        skill += '\n'.join('- ' + item for item in definition[key]) + '\n'
    encode = lambda value: (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()
    files = {'tmf-plugin.json': encode(manifest), 'role.json': encode(role),
             'skills/' + plugin_id + '/SKILL.md': skill.encode()}
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_STORED) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    data = output.getvalue()
    sha = hashlib.sha256(data).hexdigest()
    return data, {'status': 'available', 'file': 'role-plugin-' + sha + '.zip',
                  'id': plugin_id, 'version': version, 'source': source, 'sha256': sha}


def export_role_plugin(store, run_id, connection, source, check=lambda: None):
    data, receipt = build_role_plugin(connection, source, run_id, check)
    directory = store.directory(run_id) / 'outputs'
    directory.mkdir(exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=directory, prefix='.role-plugin-', delete=False) as output:
            temporary = output.name
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        check()
        with store.lock:
            os.replace(temporary, directory / receipt['file'])
            outputs = store.read(run_id).get('outputs', [])
            store.update(run_id, outputs=list(dict.fromkeys(outputs + [receipt['file']])))
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)
    return receipt
