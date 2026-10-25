import sys
import unittest
import tempfile
import json
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from audit.extraction import Extractor


class ExtractionTest(unittest.TestCase):
    def test_log_formats_preserve_same_fact(self):
        examples = [
            '2026-01-01T00:00:00Z level=INFO service=account_service resource_id=account_x event=profile_lookup_completed rows=0',
            '2026-01-01T00:00:00Z [INFO] [account_service] [tr-x] profile_lookup_completed: resource_id="account_x" rows="0"',
            '2026-01-01T00:00:00Z | INFO | account_service | tr-x | profile_lookup_completed | resource_id="account_x" rows="0"',
            '2026-01-01T00:00:00Z {"service":"account_service","event":"profile_lookup_completed","resource_id":"account_x","rows":"0"}',
            '2026-01-01T00:00:00Z requestId=tr-x function=account_service message="event=\\"profile_lookup_completed\\" resource_id=\\"account_x\\" rows=\\"0\\""',
        ]
        for line in examples:
            with self.subTest(line=line):
                fields = Extractor.parse_log(line)
                self.assertEqual(fields["resource_id"], "account_x")
                self.assertEqual(fields["rows"], "0")
                self.assertEqual(fields["event"], "profile_lookup_completed")

    def test_json_nested_snapshot_uses_observation_and_manifest_times(self):
        extractor = Extractor(SimpleNamespace())
        manifest = {"file_id":"e", "captured_at":"2026-02-01T00:00:00Z"}
        extractor.json_file({"snapshots":[{"captured_at":"2026-01-01T00:00:00Z",
            "collection":"customer_analytics_reports", "records":[{"resource_id":"analytics_x",
                "email":None, "user_id":None, "phone":None, "email_hash":None}]}]}, manifest)
        obs = extractor.observations[0]
        self.assertEqual(obs.state, "ANONYMIZED")
        self.assertEqual(obs.observed_at, "2026-01-01T00:00:00Z")
        self.assertFalse(obs.eligible("2026-01-15T00:00:00Z"))

    def test_sql_json_wrapper_retains_its_real_category(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'snapshot.sql'
            payload=json.dumps({'resource_id':'analytics_x','user_id':None,'email':None,'phone':None,'email_hash':None})
            path.write_text("CREATE TABLE customer_data_primary(resource_id TEXT,origin_system TEXT,collection_name TEXT,record_json TEXT);"
                + "INSERT INTO customer_data_primary VALUES('analytics_x','analytics_platform','customer_analytics_reports','"+payload+"');",encoding='utf-8')
            extractor=Extractor(SimpleNamespace())
            extractor.sql_file(path,{'file_id':'e','captured_at':'2026-01-01T00:00:00Z'})
            self.assertEqual(extractor.observations[0].category,'ANALYTICS_PROFILE')
            self.assertEqual(extractor.observations[0].state,'ANONYMIZED')

    def test_sql_integer_flags_preserve_flow_and_restore_state(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'snapshot.sql'
            path.write_text("CREATE TABLE connector_subscriptions(resource_id TEXT,enabled INTEGER);"
                "INSERT INTO connector_subscriptions VALUES('data_flow_x',1);"
                "CREATE TABLE backup_restore_entries(resource_id TEXT,restore_allowed INTEGER);"
                "INSERT INTO backup_restore_entries VALUES('backup_x',0);",encoding='utf-8')
            extractor=Extractor(SimpleNamespace())
            extractor.sql_file(path,{'file_id':'e','captured_at':'2026-01-01T00:00:00Z'})
            self.assertEqual([(o.category,o.state) for o in extractor.observations],
                [('DATA_FLOW','ACTIVE'),('BACKUP_ARCHIVE','BLOCKED')])
