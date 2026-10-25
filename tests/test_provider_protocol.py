import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch
from tmf_research.providers import CodexModel,ProviderError

FEATURES='\n'.join(f'{name} stable true' for name in ['shell_tool','unified_exec','plugins','apps','hooks','multi_agent','skip_host_skill_discovery','code_mode_host'])
class ProviderProtocolTests(unittest.TestCase):
    def setup_model(self):
        return patch('tmf_research.providers.subprocess.check_output',return_value=FEATURES)
    def test_compatibility_uses_features_not_an_exact_version(self):
        with patch('tmf_research.providers.subprocess.check_output', return_value=FEATURES) as query:
            CodexModel()
        self.assertEqual(query.call_args.args[0], ['codex', 'features', 'list'])
        self.assertEqual(query.call_count, 1)
    def test_every_required_isolation_feature_must_be_present_and_current(self):
        required = ['shell_tool','unified_exec','plugins','apps','hooks','multi_agent','skip_host_skill_discovery']
        for name in required:
            for replacement in ['', f'{name} removed false', f'{name} deprecated false']:
                with self.subTest(feature=name, replacement=replacement):
                    listing = FEATURES.replace(f'{name} stable true', replacement)
                    with patch('tmf_research.providers.subprocess.check_output', return_value=listing):
                        with self.assertRaisesRegex(ProviderError, name): CodexModel()
    def run_adapter(self,types,search):
        commands=[]
        def child(cmd,**kwargs):
            commands.append(cmd)
            Path(cmd[cmd.index('-o')+1]).write_text(json.dumps({'payload_json':json.dumps({'sources':[]})}))
            events=[{'type':'item.completed','item':{'type':t}} for t in types]+[{'type':'turn.completed','usage':{'input_tokens':10,'output_tokens':2}}]
            return subprocess.CompletedProcess(cmd,0,'\n'.join(json.dumps(x) for x in events),'')
        with self.setup_model(),patch('tmf_research.providers.bounded_run',side_effect=child):
            model=CodexModel(max_calls=1);result=model.call('Test role','Return sources',{},search=search)
            with self.assertRaises(ProviderError):model.call('Second role','Return sources',{})
        return model,result,commands
    def test_live_search_requires_recorded_native_event(self):
        with self.assertRaises(ProviderError):self.run_adapter(['agent_message'],True)
    def test_unexpected_execution_is_rejected(self):
        with self.assertRaises(ProviderError):self.run_adapter(['command_execution','agent_message'],False)
    def test_search_cannot_run_inside_reviewer(self):
        with self.assertRaises(ProviderError):self.run_adapter(['web_search','agent_message'],False)
    def test_isolation_and_usage_contract(self):
        model,result,commands=self.run_adapter(['web_search','agent_message'],True)
        self.assertEqual(model.usage[0]['web_search_calls'],1)
        cmd=commands[0]
        for flag in ['--ignore-user-config','--ignore-rules','--ephemeral','--skip-git-repo-check','--output-schema']:self.assertIn(flag,cmd)
        for config in ['features.shell_tool=false','features.plugins=false','features.apps=false','features.hooks=false','features.multi_agent=false']:self.assertIn(config,cmd)
        self.assertIn('web_search="live"',cmd)
        self.assertEqual(cmd[-1],'-')

if __name__=='__main__':unittest.main()
