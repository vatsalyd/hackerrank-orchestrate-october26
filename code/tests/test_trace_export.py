import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from export_trace import export_trace, redact


class TraceExportTest(unittest.TestCase):
    def test_long_unrelated_text_is_preserved_while_trailing_contact_is_redacted(self):
        prefix='X'*200000
        self.assertEqual(redact(prefix+' person@example.test'),prefix+' [REDACTED EMAIL]')

    def test_credentials_and_contacts_are_redacted_without_losing_record_structure(self):
        secret='sk-or-v1-'+'fictional'*8
        original={'type':'tool_result','timestamp':'2026-01-01T00:00:00Z',
                  'payload':{'text':f'{secret} person@example.test +1 202 555 0199','password':'sensitive'}}
        cleaned=redact(original,(secret,))
        self.assertEqual(cleaned['timestamp'],original['timestamp'])
        self.assertNotIn(secret,json.dumps(cleaned))
        self.assertNotIn('person@example.test',json.dumps(cleaned))
        self.assertNotIn('+1 202 555 0199',json.dumps(cleaned))
        self.assertEqual(cleaned['payload']['password'],'[REDACTED]')
        self.assertIn(secret,original['payload']['text'])

    def test_archive_excludes_unrelated_sessions_and_preserves_original_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory=Path(temporary)
            project=directory/'project'
            project.mkdir()
            sessions=directory/'sessions'
            sessions.mkdir()
            relevant=sessions/'rollout-project.jsonl'
            content=json.dumps({'type':'session_meta','payload':{'cwd':str(project)}})+'\n'
            content+=json.dumps({'type':'message','payload':{'text':'person@example.test'}})+'\n'
            relevant.write_text(content,encoding='utf-8')
            (sessions/'rollout-other.jsonl').write_text(json.dumps(
                {'type':'session_meta','payload':{'cwd':str(directory/'other')}})+'\n',encoding='utf-8')
            manifest=export_trace(project,sessions)
            self.assertEqual(manifest['session_count'],1)
            with zipfile.ZipFile(project/'agent-trace.zip') as archive:
                self.assertFalse(any('rollout-other' in name for name in archive.namelist()))
                records=[json.loads(line) for line in archive.read(
                    'agent-trace/codex/sessions/rollout-project.jsonl').decode().splitlines()]
                self.assertEqual(records[1]['payload']['text'],'[REDACTED EMAIL]')
            self.assertEqual(relevant.read_text(encoding='utf-8'),content)
