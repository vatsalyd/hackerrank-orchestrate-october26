"""Local OCR and conservative extraction from literal business references."""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
from pathlib import Path

from .identifiers import identifiers


def artifact_text(path: Path, cache: Path):
    key = hashlib.sha256(b"native-ocr-v1" + path.read_bytes()).hexdigest()
    destination = cache / "ocr" / (key + ".txt")
    if destination.exists():
        return destination.read_text(encoding="utf-8")
    if path.suffix == ".pdf":
        from pypdf import PdfReader
        text = "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
    elif os.name == "nt":
        result = subprocess.run(["powershell", "-NoProfile", "-File", str(Path(__file__).with_name("windows_ocr.ps1")),
            "-ImagePath", str(path.resolve())], capture_output=True, encoding="utf-8", timeout=40, check=True)
        text = result.stdout
    elif shutil.which("tesseract"):
        result = subprocess.run(["tesseract", str(path), "stdout"], capture_output=True, encoding="utf-8", timeout=40, check=True)
        text = result.stdout
    else:
        raise ValueError("Install Tesseract for local image OCR, or select an explicitly free model provider")
    if not text.strip():
        raise ValueError("Artifact has no extractable text; scanned PDFs require OCR")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")
    return text


def native_records(text: str):
    """Never infer internal IDs from user numbers or artifact filenames."""
    # Whitespace repair preserves a literal visible prefix and number (account _5762).
    clean = re.sub(r"\b(account|analytics|search|support|export|marketing|backup|data_flow|audit_record)\s*_\s*(\d+)\b", r"\1_\2", text)
    clean = re.sub(r"\buser[ _](\d+)\b", r"user_\1", clean)
    lower = clean.casefold()
    kinds = [
        ("audit_record", "SECURITY_AUDIT_LOG", "security_service", "PRESENT"),
        ("marketing", "MARKETING_PROFILE", "marketing_platform", "PRESENT"),
        ("data_flow", "DATA_FLOW", "integration_service", "ACTIVE" if "continuous" in lower and "delivered" in lower else "UNKNOWN"),
        ("analytics", "ANALYTICS_PROFILE", "analytics_platform", "IDENTIFIABLE" if "@" in clean else "UNKNOWN"),
        ("account", "USER_PROFILE", "account_service", "PRESENT"),
        ("search", "SEARCH_INDEX_ENTRY", "search_service", "PRESENT" if re.search(r"\b[1-9]\d* hits\b",lower) else "UNKNOWN"),
        ("export", "USER_EXPORT", "export_service", "PRESENT" if "ready" in lower else "UNKNOWN"),
        ("backup", "BACKUP_ARCHIVE", "backup_service", "PRESENT"),
        ("support", "SUPPORT_ATTACHMENT" if "attachment" in lower or "correction request" in lower else "SUPPORT_MESSAGE",
         "support_platform", "PRESENT" if "attachment" in lower or "correction request" in lower else "IDENTIFIABLE"),
    ]
    selected = None
    for prefix, category, system, state in kinds:
        refs = list(dict.fromkeys(re.findall(r"\b" + prefix + r"_\d+\b", clean)))
        if refs:
            selected = refs, category, system, state
            break
    if selected:
        refs, category, system, state = selected
        for ref in refs:
            # Multiple table rows need row-level identity evidence. Catalog links can bind
            # their literal resource IDs later; do not assign every visible email to every row.
            ids = identifiers(clean) if len(refs) == 1 else frozenset()
            yield dict(resource_id=ref, category=category, system_id=system, state=state,
                       identifiers=ids, fields={"visible_text": clean})
        return
    if "retain until" in lower:
        for line in clean.splitlines():
            ref = re.search(r"\bORD-\d+\b", line)
            if ref and identifiers(line):
                yield dict(resource_id=ref.group(), category="LEGAL_HOLD_RECORD", system_id="legal_archive",
                           state="PRESENT", identifiers=identifiers(line), fields={"register_entry":line})
    elif "customer reference" in lower and "retained reference" in lower:
        refs = list(dict.fromkeys(re.findall(r"\buser_\d+\b",clean)))
        if len(refs) == 1:
            yield dict(resource_id=refs[0], category="ACCOUNT_TOMBSTONE", system_id="identity_service",
                       state="REDACTED", identifiers=frozenset(refs), fields={"subject_reference":refs[0]})
    elif "statement" in lower:
        refs = list(dict.fromkeys(re.findall(r"\bNST-\d{4}-\d{4}-\d+\b",clean)))
        for ref in refs:
            yield dict(resource_id=ref, category="USER_EXPORT", system_id="export_service", state="PRESENT",
                       identifiers=identifiers(clean), fields={"statement_reference":ref})
    elif "support-attachments" in lower:
        # The selected object is a literal filename; ownership must come from a catalog link.
        refs = list(dict.fromkeys(re.findall(r"\bdelivery_confirmation_\d+\.pdf\b",clean)))
        for ref in refs:
            yield dict(resource_id=ref, category="SUPPORT_ATTACHMENT", system_id="object_storage", state="PRESENT",
                       identifiers=frozenset(), fields={"file_name":ref})
