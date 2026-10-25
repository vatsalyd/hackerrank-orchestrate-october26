import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from audit.models import Decision, Observation, Step
from audit.validation import validate_citations


def step(**changes):
    return Step.model_validate(dict(step_no=1, phase="VERIFICATION", system_id="accounts",
        resource_id="profile-x", operation="VERIFY_RECORD_ABSENT", state="ABSENT",
        evidence_id="capture-x", **changes))


class ContractsTest(unittest.TestCase):
    def test_non_deletion_has_no_steps(self):
        with self.assertRaises(ValueError):
            Decision(case_id="x", deletion_status="NOT_APPLICABLE", steps=[step()])

    def test_operation_cannot_claim_wrong_state(self):
        payload = step().model_dump()
        payload["state"] = "PRESENT"
        with self.assertRaises(ValueError):
            Step.model_validate(payload)

    def test_future_capture_cannot_prove_earlier_state(self):
        observation = Observation("capture-x", "2026-02-03T00:00:00Z", "2026-01-01T00:00:00Z",
                                  "accounts", "profile-x", "USER_PROFILE", "ABSENT")
        self.assertFalse(observation.eligible("2026-02-01T00:00:00Z"))
        decision = Decision(case_id="x", deletion_status="COMPLETE", steps=[step()])
        with self.assertRaises(ValueError):
            validate_citations(decision, "2026-02-01T00:00:00Z", {"capture-x": observation.captured_at})

    def test_exact_step_fields(self):
        payload = step().model_dump()
        payload["explanation"] = "unpermitted extra field"
        with self.assertRaises(ValueError):
            Step.model_validate(payload)


if __name__ == "__main__":
    unittest.main()
