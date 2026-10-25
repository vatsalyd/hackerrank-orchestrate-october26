import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from audit.identity import IdentityResolver
from audit.intent import local_intent
from audit.models import Observation
from audit.planner import build_decision
from audit.policy import Policy
from audit.timeline import reconstruct
from audit.timeline import EvidenceIndex


class ReasoningTest(unittest.TestCase):
    def test_export_and_negation_do_not_authorize_deletion(self):
        self.assertFalse(local_intent('Do not delete my account. Please export my data.'))
        self.assertFalse(local_intent('Unsubscribe me from marketing emails.'))
        self.assertTrue(local_intent('Please finish deleting my account after yesterday\'s error.'))

    def test_historical_email_is_resolved_without_future_alias(self):
        dataset = SimpleNamespace(identities=[dict(user_id='user_x', email='current@example.test',
            phone='+123456789', email_hash='hash-x', updated_at='2026-01-01T00:00:00Z')], audits=[
            dict(user_id='user_x', field_name='email', old_value='old@example.test',
                new_value='current@example.test', event_time='2025-12-01T00:00:00Z'),
            dict(user_id='user_x', field_name='email', old_value='current@example.test',
                new_value='future@example.test', event_time='2026-03-01T00:00:00Z')])
        user, aliases = IdentityResolver(dataset).resolve('OLD@example.test', '2026-02-01T00:00:00Z')
        self.assertEqual(user, 'user_x')
        self.assertNotIn('future@example.test', aliases)

    def test_primary_absence_does_not_hide_present_replica(self):
        observations = [Observation('primary', '2026-01-01T00:00:00Z','2026-01-01T00:00:00Z',
            'account_service','account_x','USER_PROFILE','ABSENT',scope='primary'),
            Observation('replica', '2026-01-01T00:00:00Z','2026-01-01T00:00:00Z',
            'account_service','account_x','USER_PROFILE','PRESENT',scope='replica')]
        policy = Policy([dict(data_category='USER_PROFILE',required_action='DELETE',condition='Always')])
        result = build_decision('case_x', reconstruct(observations), policy)
        self.assertEqual(result.deletion_status, 'INCOMPLETE')
        self.assertEqual(result.steps[0].evidence_id, 'replica')
        self.assertEqual([s.operation for s in result.steps],
            ['REPORT_REMAINING_RECORD','DELETE_RECORD','VERIFY_RECORD_ABSENT'])

    def test_tombstone_retains_reference_while_flow_is_stopped(self):
        policy = Policy([dict(data_category='ACCOUNT_TOMBSTONE',required_action='REDACT',condition='Stable reference')])
        observations = [Observation('t', '2026-01-01T00:00:00Z','2026-01-01T00:00:00Z',
            'identity_service','tombstone_x','ACCOUNT_TOMBSTONE','REDACTED',raw={'subject_reference':'user_x'}),
            Observation('f', '2026-01-01T00:00:00Z','2026-01-01T00:00:00Z',
            'integration_service','data_flow_x','DATA_FLOW','ACTIVE')]
        result = build_decision('case_x', reconstruct(observations), policy)
        self.assertEqual(result.steps[0].operation, 'REPORT_ACTIVE_DATA_FLOW')
        self.assertEqual(result.steps[1].operation, 'DISABLE_DATA_FLOW')
        self.assertTrue(all(s.resource_id != 'tombstone_x' for s in result.steps if s.phase=='REMEDIATION'))

    def test_nearby_workflow_time_is_not_an_identity_link(self):
        dataset = SimpleNamespace(activities=[dict(activity_id='a',event_time='2026-01-01T00:00:00Z',
            source_system='deletion_worker',target_system='account_service',event_type='DELETE_RECORD',
            resource_id='account_unrelated',details='Operation reported complete')])
        extraction = SimpleNamespace(observations=[Observation('e','2026-01-01T00:00:00Z',
            '2026-01-01T00:00:00Z','account_service','account_unrelated','USER_PROFILE','ABSENT')],tables=[])
        obs, links = EvidenceIndex(dataset,extraction).retrieve(frozenset({'user_subject'}),'2026-02-01T00:00:00Z')
        self.assertEqual(obs,[])
        self.assertEqual(links,[])

    def test_expired_retention_is_not_treated_as_active(self):
        policy=Policy([dict(data_category='LEGAL_HOLD_RECORD',required_action='RETAIN',condition='Active hold')])
        obs=Observation('e','2026-01-01T00:00:00Z','2026-01-01T00:00:00Z',
            'legal_archive','legal_hold_x','LEGAL_HOLD_RECORD','PRESENT',raw={'retained_until':'2026-01-15T00:00:00Z'})
        with self.assertRaisesRegex(ValueError,'expired'):
            policy.apply(obs,'2026-02-01T00:00:00Z')
