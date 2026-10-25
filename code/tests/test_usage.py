import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from audit.usage import write_usage_report


class UsageTest(unittest.TestCase):
    def test_retries_count_and_later_cache_hit_does_not_erase_live_usage(self):
        def event(identity,tokens,hit=False):
            return dict(event_id=identity,key='same-job',cache_hit=hit,provider='OpenRouter (free route)',
                model='fixture:free',usage={'prompt_tokens':tokens,'completion_tokens':0,'total_tokens':tokens,'cost':0})
        client=SimpleNamespace(events=[event('attempt-one',10),event('attempt-two',20),event('attempt-two',20,True)],
                               calls=2,model='openrouter/free',max_cost=0)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'usage.md'
            write_usage_report(path,client,1,Path('output.csv'),1,1)
            text=path.read_text()
        self.assertIn('| Overall | 2 | 2 | 0 | 30 | 0 | 30 | $0.000000 |',text)
