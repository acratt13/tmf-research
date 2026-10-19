import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from tmf_research.decisions import PerplexityDecider, run_trial, validate_answer
from tmf_research.providers import ProviderError

OPTIONS = {'supported': 'Explicit support', 'insufficient': 'Missing evidence', 'contradicted': 'Explicit contradiction'}
CASE = {'id': 'one', 'state': {'claim': 'A', 'source': 'A'}, 'instructions': 'Judge support',
        'options': OPTIONS, 'expected': 'supported'}


def response():
    return {'model': 'pplx-decider-flash-v1.2', 'answers': {'decision': {'choice': 'supported', 'probabilities': {
        'supported': .98, 'insufficient': .01, 'contradicted': .01}, 'confidence': .97}},
        'usage': {'input_tokens': 100, 'output_tokens': 1}}


class DecisionTests(unittest.TestCase):
    def test_invalid_distributions_fail(self):
        for value in (float('nan'), True, -1, 1.4):
            item = response(); item['answers']['decision']['probabilities']['supported'] = value
            with self.assertRaises(ValueError): validate_answer(item, OPTIONS)
        item = response(); item['answers']['decision']['choice'] = 'insufficient'
        with self.assertRaises(ValueError): validate_answer(item, OPTIONS)

    def test_missing_key_fails_before_network(self):
        with patch.dict('os.environ', {}, clear=True), self.assertRaises(ProviderError): PerplexityDecider()

    def test_unknown_answer_fields_are_not_retained(self):
        item = response(); item['answers']['decision']['unexpected_echo'] = 'untrusted extra field'
        self.assertNotIn('unexpected_echo', validate_answer(item, OPTIONS))

    def test_invalid_cases_fail_before_client_or_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/'trial'
            for cases in ([], [CASE, CASE], [{**CASE, 'expected': 'invented'}]):
                with self.assertRaises(ValueError): run_trial(cases, out, 'pplx-decider-v1.2')
                self.assertFalse(out.exists())

    def test_fixed_destination_no_labels_or_secret_in_receipt(self):
        calls = []
        class Reply:
            status = 200
            def read(self, n): return json.dumps(response()).encode()
        class Connection:
            def __init__(self, host, **kw): self.host = host
            def request(self, method, path, **kw): calls.append((self.host, method, path, kw))
            def getresponse(self): return Reply()
            def close(self): pass
        with patch.dict('os.environ', {'TRIAL_KEY': 'test-only-placeholder'}), patch('http.client.HTTPSConnection', Connection):
            model = PerplexityDecider(key_env='TRIAL_KEY')
            result = model.decide(CASE['state'], CASE['instructions'], OPTIONS)
        host, method, path, kw = calls[0]
        self.assertEqual((host, method, path), ('api.perplexity.ai', 'POST', '/v1/decisions'))
        self.assertNotIn('expected', json.loads(kw['body']))
        self.assertNotIn('test-only-placeholder', json.dumps(result))

    def test_error_body_is_not_read_or_echoed(self):
        class Connection:
            def __init__(self, *a, **kw): pass
            def request(self, *a, **kw): pass
            def getresponse(self): return type('Response', (), {'status': 401})()
            def close(self): pass
        with patch.dict('os.environ', {'TRIAL_KEY': 'test-placeholder'}), patch('http.client.HTTPSConnection', Connection):
            with self.assertRaisesRegex(ProviderError, 'HTTP 401'):
                PerplexityDecider(key_env='TRIAL_KEY').decide({}, 'Judge', OPTIONS)

    def test_trial_labels_remain_local_and_existing_outputs_protected(self):
        observed = []
        class Client:
            def decide(self, state, instructions, options):
                observed.append(state)
                return {'answer': response()['answers']['decision'], 'estimated_input_cost_usd': .000001}
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'trial'
            summary = run_trial([CASE], out, 'pplx-decider-flash-v1.2', client=Client())
            self.assertEqual(summary['correct'], 1)
            self.assertEqual(observed, [CASE['state']])
            with self.assertRaises(FileExistsError): run_trial([CASE], out, 'pplx-decider-flash-v1.2', client=Client())

    def test_unavailable_is_partial_not_false_success(self):
        class Client:
            def decide(self, *a): raise ProviderError('Do not retain raw provider text')
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'trial'
            summary = run_trial([CASE], out, 'pplx-decider-flash-v1.2', client=Client())
            self.assertEqual(summary['status'], 'partial')
            self.assertEqual(summary['answered'], 0)
            self.assertNotIn('raw provider text', (out/'results.json').read_text())

    def test_false_support_is_explicit(self):
        class Client:
            def decide(self, *a): return {'answer': response()['answers']['decision'], 'estimated_input_cost_usd': 0}
        with tempfile.TemporaryDirectory() as tmp:
            summary = run_trial([{**CASE, 'expected': 'insufficient'}], Path(tmp)/'trial', 'pplx-decider-v1.2', client=Client())
            self.assertEqual(summary['false_support'], 1)
            self.assertEqual(summary['high_confidence_errors'], 1)


if __name__ == '__main__': unittest.main()
