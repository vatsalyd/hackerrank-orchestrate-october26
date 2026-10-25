import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from audit.extraction import TableSnapshot
from audit.extraction import Extractor
from audit.timeline import EvidenceIndex,reconstruct
from audit.planner import build_decision
from audit.policy import Policy

TIME='2026-01-01T00:00:00Z'


class SubjectLookupTest(unittest.TestCase):
    def index(self,identifiers=frozenset({'user_other'}),queryable=True,captured=TIME):
        table=TableSnapshot('snapshot',captured,TIME,'account_service','USER_PROFILE','customer_profiles',
            frozenset({'account_unrelated'}),identifiers,queryable)
        return EvidenceIndex(SimpleNamespace(activities=[]),SimpleNamespace(observations=[],tables=[table]))

    def test_complete_snapshot_supports_negative_lookup_without_inventing_physical_id(self):
        facts,_=self.index().retrieve(frozenset({'user_subject'}),'2026-02-01T00:00:00Z',subject_reference='user_subject')
        self.assertEqual(facts[0].resource_id,'user_subject')
        self.assertEqual(facts[0].raw['binding_kind'],'subject_lookup')
        policy=Policy([dict(data_category='USER_PROFILE',required_action='DELETE',condition='Always')])
        result=build_decision('case',reconstruct(facts),policy)
        self.assertEqual(result.deletion_status,'COMPLETE')
        self.assertEqual([step.operation for step in result.steps],['VERIFY_RECORD_ABSENT'])

    def test_partial_or_anonymous_snapshot_does_not_prove_absence(self):
        facts,_=self.index(queryable=False).retrieve(frozenset({'user_subject'}),
            '2026-02-01T00:00:00Z',subject_reference='user_subject')
        self.assertEqual(facts,[])

    def test_matching_subject_or_future_capture_prevents_negative_proof(self):
        for index in (self.index(frozenset({'user_subject'})),self.index(captured='2026-03-01T00:00:00Z')):
            facts,_=index.retrieve(frozenset({'user_subject'}),'2026-02-01T00:00:00Z',subject_reference='user_subject')
            self.assertEqual(facts,[])

    def test_global_gateway_export_query_excludes_partial_and_unattributed_reads(self):
        value={'region':'global','source':'assurance_gateway','exported_at':TIME,
               'service_exports':{'account_service':{'profile_lookups':[
                   {'resource_id':'account_other','observed_at':TIME,'status_code':200,
                    'profile':{'customer_reference':'user_other','email':'other@example.test'}},
                   {'resource_id':'account_gone','observed_at':TIME,'status_code':404,'profile':None}]}}}
        extractor=Extractor(SimpleNamespace())
        extractor.json_file(value,{'file_id':'gateway','captured_at':TIME})
        self.assertTrue(extractor.tables[0].supports_subject_query)
        value['service_exports']['account_service']['filters']={'region':'subset'}
        extractor=Extractor(SimpleNamespace())
        extractor.json_file(value,{'file_id':'gateway','captured_at':TIME})
        self.assertEqual(extractor.tables,[])
