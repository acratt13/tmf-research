"""Optional integration against MC's shared shim, supplied by MC_CLI_SHIM."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import tomllib
import unittest
from tmf_research.client import PAGE_BYTES


@unittest.skipUnless(os.environ.get('MC_CLI_SHIM') and shutil.which('node'), 'set MC_CLI_SHIM to test the existing MC serializer')
class SharedWrapperTests(unittest.TestCase):
    def exchange(self, requests):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            command = folder / 'tmf-research'
            command.write_text('''#!/usr/bin/env python3
import sys
if '--help' in sys.argv:
    print('Commands:\\n  submit  Submit a brief\\n  status  Read state\\n  result  Read results\\n  cancel  Cancel work\\n  serve   Start a server\\n  run     Run synchronously')
else:
    from tmf_research.client import page
    from tmf_research.cli import dump
    print(dump(page({'payload': 'Quote " \\\\ Unicode 💡\\n' * 3000}, 'completed')), end='')
''')
            command.chmod(0o700)
            allow = folder / 'allow.json'
            shutil.copyfile(root / 'tmf_research/mc/allow.json', allow)
            env = {**os.environ, 'PYTHONPATH': str(root), 'PYTHONDONTWRITEBYTECODE': '1'}
            server = json.loads((root / 'tmf_research/mc/mcp-servers.json').read_text())['mcpServers'][0]
            self.assertEqual(server['command'], 'node')
            self.assertEqual(server['args'][-1], 'tmf-research')
            replacements = {'${plugin:.mc-cli-shim/cli-mcp-shim.mjs}': os.environ['MC_CLI_SHIM'],
                            '${data}/tmf-research-allow.json': str(allow), 'tmf-research': str(command)}
            argv = [server['command']] + [replacements.get(arg, arg) for arg in server['args']]
            result = subprocess.run(argv,
                                    input=''.join(json.dumps(r) + '\n' for r in requests), capture_output=True,
                                    text=True, timeout=10, check=True, env=env, cwd=folder)
            return [json.loads(line) for line in result.stdout.splitlines()]

    def test_annotations_match_the_real_console_tool_names(self):
        root = Path(__file__).resolve().parents[1]
        scripts = tomllib.loads((root / 'pyproject.toml').read_text())['project']['scripts']
        server = json.loads((root / 'tmf_research/mc/mcp-servers.json').read_text())['mcpServers'][0]
        self.assertEqual(scripts[server['args'][-1]], 'tmf_research.cli:main')
        self.assertEqual(server['name'], 'tmf-research')
        self.assertEqual(server['probe'], {'tool': 'tmf-research_status', 'arguments': {}})
        reply, = self.exchange([{'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'}])
        annotations = json.loads((root / 'tmf_research/mc/tool-annotations.json').read_text())['toolAnnotations']
        names = [t['name'] for t in reply['result']['tools']]
        self.assertEqual(names, ['tmf-research_' + op for op in ('submit', 'status', 'result', 'cancel')])
        self.assertEqual({name: annotations.get('mcp.tmf-research/' + name, {}).get('readOnlyHint') for name in names},
                         {name: name.endswith(('_status', '_result')) for name in names})

    def test_budget_uses_the_real_complete_mcp_result(self):
        reply, = self.exchange([{'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call',
                                 'params': {'name': 'tmf-research_result', 'arguments': {'args': []}}}])
        self.assertFalse(reply['result']['isError'])
        result_bytes = len(json.dumps(reply['result'], ensure_ascii=False, separators=(',', ':')).encode())
        self.assertLessEqual(result_bytes, PAGE_BYTES)
        text = reply['result']['content'][0]['text']
        page = json.loads(text.removesuffix('\n[exit 0]'))
        self.assertGreater(page['next_cursor'], 0)
