import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from audit.native_artifacts import native_records


class NativeArtifactsTest(unittest.TestCase):
    def test_customer_page_does_not_make_related_support_a_primary_record(self):
        text='Customer Operations\nuser_42 account _123\nEmail\nperson@example.test\nSupport history\nsupport_987'
        rows=list(native_records(text))
        self.assertEqual([row['resource_id'] for row in rows],['account_123'])

    def test_multiple_exports_do_not_inherit_every_email(self):
        rows=list(native_records('Data exports\nReady\nexport_1\nexport_2\nfirst@example.test\nsecond@example.test'))
        self.assertEqual(len(rows),2)
        self.assertTrue(all(not row['identifiers'] for row in rows))

    def test_legal_register_preserves_literal_order_reference(self):
        rows=list(native_records('ORD-20261234 | user_7 | Dispute | Retain until 04 May 2033'))
        self.assertEqual(rows[0]['resource_id'],'ORD-20261234')
        self.assertEqual(rows[0]['category'],'LEGAL_HOLD_RECORD')
        self.assertIn('user_7',rows[0]['identifiers'])

    def test_backup_presence_does_not_claim_restore_permission(self):
        rows=list(native_records('Archives\nbackup_123\nAES-256\nHealthy'))
        self.assertEqual(rows[0]['state'],'PRESENT')
