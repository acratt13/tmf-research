"""Renderer diagnostics must gate publication, even when the engine exits zero."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from tmf_research.exports import export_run

class DiagramExportTests(unittest.TestCase):
    def test_missing_or_overflowing_diagnostics_withhold_files(self):
        record=json.loads(Path('examples/council-live/report.json').read_text())
        synthesis={'workflow_steps':[{'label':'Intake','detail':'Accept input.'},{'label':'Review','detail':'Confirm ownership.'}]}
        for bad in ('missing','overflow','warning'):
            with self.subTest(bad=bad), tempfile.TemporaryDirectory() as tmp:
                def renderer(cmd,**kwargs):
                    if '--version' in cmd:return SimpleNamespace(returncode=0,stdout='designcraft-cli 0.9.0',stderr='')
                    script=json.loads(Path(cmd[2]).read_text())
                    stories=[{'overset':False,'length':len(c['params']['text'].encode())} for c in script if c['command']=='frame.create' and 'text' in c['params']]
                    issues=[]
                    if bad=='missing':stories=[]
                    if bad=='overflow':stories[0]['overset']=True
                    if bad=='warning':issues=[{'severity':'warning'}]
                    for flag in ('--save','--export'):
                        for i,x in enumerate(cmd):
                            if x==flag:Path(cmd[i+1]).write_bytes(b'rendered')
                    result={'results':[{'stories':stories},{'issues':issues,'errors':0,'warnings':len(issues)}]}
                    return SimpleNamespace(returncode=0,stdout=json.dumps(result),stderr='')
                with patch('tmf_research.exports.bounded_run',side_effect=renderer):
                    outputs,errors=export_run(tmp,record,synthesis,['diagram'],{'craft':{'designcraft':'configured-cli'}})
                self.assertEqual(outputs,['export-receipt.json'])
                self.assertEqual(len(errors),1)
                self.assertEqual(json.loads((Path(tmp)/'outputs/export-receipt.json').read_text())['artifacts'],[])
