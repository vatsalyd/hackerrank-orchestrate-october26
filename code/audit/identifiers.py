"""Conservative search forms; keep original source values in observations."""
import re
import unicodedata

EMAIL = re.compile(r"[\w.!#$%&'*+/=?^`{|}~-]+@[\w.-]+\.[A-Za-z]{2,}", re.UNICODE)
USER = re.compile(r"\buser_[A-Za-z0-9]+\b")
RESOURCE = re.compile(r"\b(?:account|search|analytics|support|export|marketing|cache|email_delivery|audit_record|legal_hold|backup|data_flow|tombstone|object)_[A-Za-z0-9]+\b")


def normalize(value):
    text = unicodedata.normalize("NFKC", str(value)).strip().casefold()
    if text.startswith("+") and len(re.sub(r"\D", "", text)) >= 7:
        return "+" + re.sub(r"\D", "", text)
    return text


def identifiers(value) -> frozenset[str]:
    found = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"resource_id", "ticket_id", "order_reference", "integrity_seal"}:
                continue
            found.update(identifiers(item))
            if item and key in {"phone", "email_hash", "subject_reference", "subject_selector", "lookup_value",
                                "lookup_key", "subject_key", "match_key", "scan_key", "correlation_key"}:
                found.add(normalize(item))
    elif isinstance(value, list):
        for item in value:
            found.update(identifiers(item))
    elif isinstance(value, str):
        found.update(normalize(match.group()) for pattern in (EMAIL, USER) for match in pattern.finditer(value))
    return frozenset(found)
