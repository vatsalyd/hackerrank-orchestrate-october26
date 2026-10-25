import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from audit.artifact_grounding import ground_records
from audit.extraction import resource_kind


def record(resource,category='USER_PROFILE',state='IDENTIFIABLE'):
    return dict(resource_id=resource,category=category,state=state,system_id='Customer Portal',
                identifiers=['user_42'],fields={},observed_at='')


class ArtifactGroundingTest(unittest.TestCase):
    def test_user_reference_is_bound_to_visible_physical_record(self):
        rows,issues=ground_records([record('user_42')],
            'Customer details user_42 account _987 person@example.test',resource_kind,True)
        self.assertEqual(rows[0]['resource_id'],'account_987')
        self.assertEqual(rows[0]['system_id'],'account_service')
        self.assertEqual(rows[0]['state'],'PRESENT')

    def test_related_ticket_claim_is_removed(self):
        rows,issues=ground_records([record('account_987'),record('CS-111','SUPPORT_MESSAGE')],
            'Customer details account_987 person@example.test\nRelated support_111',resource_kind,True)
        self.assertEqual(len(rows),1)
        self.assertTrue(issues)

    def test_unseen_reference_is_not_guessed_from_subject_number(self):
        rows,issues=ground_records([record('account_42')],
            'Customer reference user_42',resource_kind,True)
        self.assertEqual(rows,[])
        self.assertTrue(issues)
