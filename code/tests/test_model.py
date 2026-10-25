import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from audit.llm import ModelClient


class ModelTest(unittest.TestCase):
    def test_cache_reuses_result_and_retains_accounting(self):
        response = {'model':'fixture/model:free','usage':{'prompt_tokens':10,'completion_tokens':5,'total_tokens':15,'cost':0},
            'choices':[{'finish_reason':'stop','message':{'content':'{"value": true}'}}]}
        with tempfile.TemporaryDirectory() as directory:
            client=ModelClient(Path(directory),online=True)
            with patch.dict('os.environ',{'OPENROUTER_API_KEY':'fixture-key'}), patch('urllib.request.urlopen',
                    return_value=io.BytesIO(json.dumps(response).encode())) as call:
                self.assertEqual(client.json('test','Return JSON',{'a':1}),{'value':True})
                self.assertEqual(client.json('test','Return JSON',{'a':1}),{'value':True})
                self.assertEqual(call.call_count,1)
                request=call.call_args.args[0]
                body=json.loads(request.data)
                self.assertEqual(request.full_url,'https://openrouter.ai/api/v1/chat/completions')
                self.assertEqual(body['model'],'openrouter/free')
                self.assertNotIn('models',body)
                self.assertEqual(body['provider']['max_price'],{'prompt':0,'completion':0,'request':0,'image':0})
            self.assertFalse(client.events[0]['cache_hit'])
            self.assertTrue(client.events[1]['cache_hit'])
            self.assertEqual(client.events[1]['usage']['total_tokens'],15)
            self.assertNotIn('fixture-key',''.join(p.read_text() for p in Path(directory).rglob('*.json')))

    def test_paid_models_and_nonzero_budget_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError,'Paid models'):
                ModelClient(Path(directory),online=True,model='provider/paid-model')
            with self.assertRaisesRegex(ValueError,'Paid spending'):
                ModelClient(Path(directory),online=True,max_cost=1)

    def test_paid_credential_is_never_used_as_fallback(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict('os.environ',{'DEEPSEEK_API_KEY':'unused-fixture'},clear=True):
            client=ModelClient(Path(directory),online=True)
            with patch('urllib.request.urlopen') as network:
                with self.assertRaisesRegex(ValueError,'OPENROUTER_API_KEY'):
                    client.json('test','Return JSON',{})
                network.assert_not_called()
