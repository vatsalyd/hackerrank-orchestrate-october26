"""Policy action is loaded from participant rules; treatments are contract operations."""
from dataclasses import dataclass

from .models import UnresolvedCase, instant


@dataclass(frozen=True)
class Treatment:
    compliant: bool
    verification: str
    finding: str = ""
    remediation: str = ""


class Policy:
    def __init__(self, rows):
        self.rules = {}
        for row in rows:
            if row["data_category"] in self.rules:
                raise ValueError("Ambiguous policy category")
            self.rules[row["data_category"]] = row

    def apply(self, observation, cutoff=None):
        category, state = observation.category, observation.state
        raw = observation.raw
        if cutoff:
            until = raw.get("retention_until", raw.get("retained_until"))
            if until and instant(until) <= instant(cutoff) and category in {"SECURITY_AUDIT_LOG", "LEGAL_HOLD_RECORD"}:
                raise UnresolvedCase("Retention condition expired; no replacement treatment is supplied")
        if category == "LEGAL_HOLD_RECORD" and raw.get("legal_hold_active") is False:
            raise UnresolvedCase("Legal hold is inactive; the conditional retention rule does not apply")
        if category == "SUPPORT_ATTACHMENT" and len(raw.get("subject_ids", [])) > 1:
            raise UnresolvedCase("Attachment ownership is shared; subject-only deletion rule does not apply")
        if category == "SUPPORT_MESSAGE" and raw.get("shared_context_required") is False:
            raise UnresolvedCase("Shared-context redaction condition does not apply")
        if category == "DATA_FLOW":
            return Treatment(state == "DISABLED", "VERIFY_DATA_FLOW_DISABLED",
                             "REPORT_ACTIVE_DATA_FLOW", "DISABLE_DATA_FLOW")
        if category == "BACKUP_ARCHIVE":
            if category not in self.rules:
                raise UnresolvedCase("Missing backup retention rule")
            if raw.get("restore_can_be_blocked") is False:
                raise UnresolvedCase("Backup restore cannot be blocked under the supplied conditional rule")
            recoverable=state=='PRESENT' and raw.get('recovery_archive_available') is True
            if state not in {"ACTIVE", "BLOCKED"} and not recoverable:
                raise UnresolvedCase("Backup existence does not establish restore permission")
            return Treatment(state == "BLOCKED", "VERIFY_RESTORE_BLOCKED", "REPORT_RESTORE_RISK", "BLOCK_RESTORE")
        rule = self.rules.get(category)
        if not rule:
            raise UnresolvedCase(f"No policy for category {category}")
        action = rule["required_action"]
        if action == "DELETE":
            return Treatment(state == "ABSENT", "VERIFY_RECORD_ABSENT", "REPORT_REMAINING_RECORD", "DELETE_RECORD")
        if action == "REDACT":
            if state == "ABSENT":
                raise UnresolvedCase(f"Required retained record is absent: {observation.resource_id}")
            return Treatment(state == "REDACTED", "VERIFY_RECORD_REDACTED", "REPORT_EXPOSED_PII", "REDACT_RECORD")
        if action == "ANONYMIZE":
            if state == "ABSENT":
                raise UnresolvedCase(f"Anonymization record unavailable: {observation.resource_id}")
            return Treatment(state == "ANONYMIZED", "VERIFY_RECORD_ANONYMIZED", "REPORT_EXPOSED_PII", "ANONYMIZE_RECORD")
        if action == "RETAIN":
            if state == "ABSENT":
                raise UnresolvedCase(f"Required retained record is absent: {observation.resource_id}")
            return Treatment(True, "VERIFY_RECORD_PRESENT")
        raise UnresolvedCase(f"Unsupported policy action: {action}")
