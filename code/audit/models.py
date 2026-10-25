"""Typed boundaries and the submission's canonical operation order."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

OPERATIONS = {
    "FINDING": {
        "REPORT_REMAINING_RECORD": "PRESENT", "REPORT_EXPOSED_PII": "PRESENT",
        "REPORT_ACTIVE_DATA_FLOW": "ACTIVE", "REPORT_RESTORE_RISK": "ACTIVE",
    },
    "REMEDIATION": {
        "DISABLE_DATA_FLOW": "DISABLED", "BLOCK_RESTORE": "BLOCKED",
        "DELETE_RECORD": "ABSENT", "REDACT_RECORD": "REDACTED",
        "ANONYMIZE_RECORD": "ANONYMIZED",
    },
    "VERIFICATION": {
        "VERIFY_RECORD_ABSENT": "ABSENT", "VERIFY_RECORD_PRESENT": "PRESENT",
        "VERIFY_RECORD_REDACTED": "REDACTED", "VERIFY_RECORD_ANONYMIZED": "ANONYMIZED",
        "VERIFY_DATA_FLOW_DISABLED": "DISABLED", "VERIFY_RESTORE_BLOCKED": "BLOCKED",
    },
}
PHASE_ORDER = {phase: i for i, phase in enumerate(OPERATIONS)}
OP_ORDER = {op: i for operations in OPERATIONS.values() for i, op in enumerate(operations)}


def instant(value: str | datetime) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value
    if result.tzinfo is None:
        raise ValueError(f"Timestamp requires timezone: {value}")
    return result.astimezone(timezone.utc)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Request(StrictModel):
    case_id: str
    email: str
    requested_at: str
    reported_status: str
    reported_at: str
    audit_at: str
    request_text: str

    @model_validator(mode="after")
    def timestamps(self):
        for name in ("requested_at", "reported_at", "audit_at"):
            instant(getattr(self, name))
        return self


class Step(StrictModel):
    step_no: int = Field(ge=1)
    phase: Literal["FINDING", "REMEDIATION", "VERIFICATION"]
    system_id: str = Field(min_length=1)
    resource_id: str = Field(min_length=1)
    operation: str
    state: str
    evidence_id: str

    @model_validator(mode="after")
    def operation_state(self):
        if OPERATIONS[self.phase].get(self.operation) != self.state:
            raise ValueError(f"Invalid operation/state for {self.phase}: {self.operation}/{self.state}")
        return self

    def sort_key(self):
        return PHASE_ORDER[self.phase], OP_ORDER[self.operation], self.system_id, self.resource_id


class Decision(StrictModel):
    case_id: str
    deletion_status: Literal["COMPLETE", "INCOMPLETE", "NOT_APPLICABLE"]
    steps: list[Step]

    @model_validator(mode="after")
    def contract(self):
        if self.deletion_status == "NOT_APPLICABLE" and self.steps:
            raise ValueError("Non-deletion requests must have empty steps")
        if self.deletion_status != "NOT_APPLICABLE" and not self.steps:
            raise ValueError("Deletion decisions require evidence or a plan")
        if [s.step_no for s in self.steps] != list(range(1, len(self.steps) + 1)):
            raise ValueError("Step numbers must be consecutive")
        if self.steps != sorted(self.steps, key=lambda s: s.sort_key()):
            raise ValueError("Steps violate canonical ordering")
        for step in self.steps:
            if self.deletion_status == "COMPLETE" and step.phase != "VERIFICATION":
                raise ValueError("Complete decisions contain verification only")
            requires_evidence = self.deletion_status == "COMPLETE" or step.phase == "FINDING"
            if bool(step.evidence_id) != requires_evidence:
                raise ValueError("Invalid evidence citation for this phase/verdict")
        if self.deletion_status == "INCOMPLETE":
            if {s.phase for s in self.steps} != set(OPERATIONS):
                raise ValueError("Incomplete decisions need all three phases")
        return self


@dataclass(frozen=True)
class Observation:
    evidence_id: str
    captured_at: str
    observed_at: str
    system_id: str
    resource_id: str
    category: str
    state: str
    identifiers: frozenset[str] = frozenset()
    scope: str = ""
    location: str = ""
    raw: dict[str, Any] = field(default_factory=dict, compare=False)
    strength: int = 2

    def eligible(self, cutoff: str) -> bool:
        return max(instant(self.captured_at), instant(self.observed_at)) <= instant(cutoff)


class UnresolvedCase(ValueError):
    """Evidence coverage or interpretation is insufficient for a supported answer."""
