import io
import json
import sys
import tempfile
import unittest
import urllib.error
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

    def test_invalid_response_retry_preserves_usage_and_accepts_fenced_json(self):
        def response(content):
            return io.BytesIO(json.dumps({'model':'fixture/free','usage':{'prompt_tokens':5,'completion_tokens':2,'total_tokens':7,'cost':0},
                'choices':[{'finish_reason':'stop','message':{'content':content}}]}).encode())
        with tempfile.TemporaryDirectory() as directory, patch.dict('os.environ',{'OPENROUTER_API_KEY':'fixture-key'}):
            client=ModelClient(Path(directory),online=True)
            with patch('urllib.request.urlopen',side_effect=[response(''),response('```json\n{"ok":true}\n```')]),patch('time.sleep'):
                self.assertEqual(client.json('test','Return JSON',{}),{'ok':True})
            self.assertEqual(len(client.events),2)
            self.assertFalse(client.events[0]['response_valid'])
            self.assertTrue(client.events[1]['response_valid'])
            events=(Path(directory)/'model/usage_events.jsonl').read_text().splitlines()
            self.assertEqual(len(events),2)
            self.assertNotIn('fixture-key',''.join(events))

    def test_optional_reasoning_repair_keeps_zero_price_guards(self):
        error=urllib.error.HTTPError('https://openrouter.ai',400,'Bad request',{},
            io.BytesIO(b'{"error":{"message":"Reasoning is mandatory for this model"}}'))
        response=io.BytesIO(json.dumps({'model':'fixture:free','usage':{'cost':0},
            'choices':[{'finish_reason':'stop','message':{'content':'{"ok":true}'}}]}).encode())
        with tempfile.TemporaryDirectory() as directory,patch.dict('os.environ',{'OPENROUTER_API_KEY':'fixture-key'}):
            client=ModelClient(Path(directory),online=True)
            with patch('urllib.request.urlopen',side_effect=[error,response]) as call:
                self.assertEqual(client.json('test','JSON',{}),{'ok':True})
            repaired=json.loads(call.call_args_list[1].args[0].data)
            self.assertNotIn('reasoning',repaired)
            self.assertEqual(repaired['provider']['max_price'],{'prompt':0,'completion':0,'request':0,'image':0})
