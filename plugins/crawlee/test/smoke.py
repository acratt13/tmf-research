"""Live SSH/MCP smoke test. Set CRAWLEE_CONFIG to your private connection JSON."""
import json
import os
from pathlib import Path
import select
import subprocess
import sys
import time

bridge = Path(__file__).resolve().parents[1] / 'mc-plugin' / 'bridge.mjs'
process = subprocess.Popen(['node', str(bridge)], stdin=subprocess.PIPE,
                           stdout=subprocess.PIPE, text=True, env=os.environ)
receipt = []

def call(name, arguments):
    process.stdin.write(json.dumps({'jsonrpc': '2.0', 'id': len(receipt)+1,
        'method': 'tools/call', 'params': {'name': name, 'arguments': arguments}})+'\n')
    process.stdin.flush()
    if not select.select([process.stdout], [], [], 25)[0]:
        raise RuntimeError('MCP response timeout')
    response = json.loads(process.stdout.readline())
    receipt.append({'tool': name, 'response': response})
    if 'error' in response:
        raise RuntimeError(response['error'])
    result = response['result']
    data = json.loads(result['content'][0]['text'])
    if result.get('isError'):
        raise RuntimeError(data)
    return data

try:
    call('crawlee_status', {})
    job = call('crawlee_start', {'urls': [sys.argv[1]], 'max_pages': 3,
        'topic': 'Documentation source pack', 'tags': ['documentation']})['id']
    for _ in range(65):
        time.sleep(2)
        state = call('crawlee_status', {'job_id': job})
        if state['status'] not in ('queued', 'running'):
            break
    assert state['status'] == 'completed', state
    assert 1 <= len(state['sources']) <= 3, state
    for source in state['sources']:
        passage = call('crawlee_read', {'job_id': job, 'source_id': source['id']})
        assert passage['text'] and passage['source']['text_sha256']
    packed = call('crawlee_pack', {'job_id': job})
    for format in ('json', 'md'):
        artifact = call('crawlee_pack_read', {'job_id': job, 'format': format})
        expected = next(a for a in packed['artifacts'] if a['name'] == artifact['name'])
        assert artifact['sha256'] == expected['sha256']
    cancelled = call('crawlee_start', {'urls': [sys.argv[1]], 'max_pages': 1})['id']
    call('crawlee_cancel', {'job_id': cancelled})
    for _ in range(10):
        time.sleep(1)
        state = call('crawlee_status', {'job_id': cancelled})
        if state['status'] == 'cancelled':
            break
    assert state['status'] == 'cancelled', state
finally:
    process.terminate()
    process.wait(timeout=5)
    print(json.dumps(receipt, indent=2))
