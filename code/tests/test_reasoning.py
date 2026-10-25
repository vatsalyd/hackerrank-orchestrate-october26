import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from audit.identity import IdentityResolver
from audit.intent import local_intent
from audit.intent import classify_hybrid_requests
from audit.intent import classify_requests
from audit.models import Observation
from audit.planner import build_decision
from audit.policy import Policy
from audit.timeline import reconstruct
from audit.timeline import EvidenceIndex


class ReasoningTest(unittest.TestCase):
    def test_identical_text_is_interpreted_once_and_mapped_to_each_case(self):
        requests=[SimpleNamespace(case_id='one',request_text='Please export my data.'),
                  SimpleNamespace(case_id='two',request_text='Please export my data.')]
        class FreeModel:
            def json(self,task,prompt,data,validator):
                self.count=len(data)
                result={'items':[{'id':data[0]['id'],'delete':False,'reason':'Export only'}]}
                validator(result)
                return result
        model=FreeModel()
        self.assertEqual(classify_requests(requests,model),{'one':False,'two':False})
        self.assertEqual(model.count,1)

    def test_hybrid_intent_uses_free_model_for_uncertain_or_multilingual_text(self):
        requests=[SimpleNamespace(case_id='english',request_text='Please delete my account.'),
            SimpleNamespace(case_id='spanish',request_text='No quiero eliminar mi cuenta.'),
            SimpleNamespace(case_id='export',request_text='Please export my data.')]
        with patch('audit.intent.classify_requests',return_value={'spanish':False}) as remote:
            result=classify_hybrid_requests(requests,object())
        self.assertEqual(result,{'english':True,'export':False,'spanish':False})
        self.assertEqual([row.case_id for row in remote.call_args.args[0]],['spanish'])

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

    def test_current_verification_cites_newer_direct_read_over_old_replica_snapshot(self):
        observations = [
            Observation('old_snapshot','2026-01-01T00:00:00Z','2026-01-01T00:00:00Z',
                'account_service','account_x','USER_PROFILE','ABSENT',scope='replica',strength=4),
            Observation('current_read','2026-02-01T00:00:00Z','2026-02-01T00:00:00Z',
                'account_service','account_x','USER_PROFILE','ABSENT',scope='primary',strength=3)]
        policy = Policy([dict(data_category='USER_PROFILE',required_action='DELETE',condition='Always')])
        result = build_decision('case_x',reconstruct(observations),policy)
        self.assertEqual(result.deletion_status,'COMPLETE')
        self.assertEqual(result.steps[0].evidence_id,'current_read')

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

    def test_available_recovery_archive_is_a_restore_risk_without_permission_claim(self):
        policy=Policy([dict(data_category='BACKUP_ARCHIVE',required_action='RETAIN',condition='Restore can be blocked')])
        obs=Observation('archive','2026-01-01T00:00:00Z','2026-01-01T00:00:00Z',
            'backup_service','backup_x','BACKUP_ARCHIVE','PRESENT',raw={'recovery_archive_available':True})
        treatment=policy.apply(obs)
        self.assertFalse(treatment.compliant)
        self.assertEqual(treatment.finding,'REPORT_RESTORE_RISK')
