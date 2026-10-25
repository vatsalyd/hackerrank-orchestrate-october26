from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

from .models import Request, instant


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError(f"Missing/duplicate CSV columns: {path.name}")
        rows = list(reader)
        if any(None in row or None in row.values() for row in rows):
            raise ValueError(f"Malformed CSV row: {path.name}")
        return rows


class Dataset:
    def __init__(self, path: Path):
        self.path = path.resolve()
        self.identities = read_csv(self.path / "user_identities.csv")
        self.audits = read_csv(self.path / "user_audit_log.csv")
        self.activities = read_csv(self.path / "system_activity.csv")
        self.rules = read_csv(self.path / "deletion_rules.csv")
        self.manifest = read_csv(self.path / "evidence_files.csv")
        self.files = {}
        for row in self.manifest:
            file_path = (self.path / row["file_path"]).resolve()
            if not file_path.is_relative_to(self.path / "evidence") or not file_path.is_file():
                raise ValueError(f"Invalid evidence path for {row['file_id']}")
            if row["file_id"] in self.files:
                raise ValueError("Duplicate evidence ID")
            instant(row["captured_at"])
            self.files[row["file_id"]] = file_path
        self.citation_times = {row["file_id"]: row["captured_at"] for row in self.manifest}
        for rows, key in ((self.activities, "activity_id"), (self.audits, "audit_id")):
            for row in rows:
                if row[key] in self.citation_times:
                    raise ValueError(f"Duplicate citation: {row[key]}")
                instant(row["event_time"])
                self.citation_times[row[key]] = row["event_time"]

    def requests(self, sample: bool = False) -> list[Request]:
        filename = "sample_deletion_requests.csv" if sample else "deletion_requests.csv"
        rows = [Request.model_validate(row) for row in read_csv(self.path / filename)]
        if len({row.case_id for row in rows}) != len(rows):
            raise ValueError("Duplicate case ID")
        return sorted(rows, key=lambda row: row.case_id)

    def inventory(self):
        return {
            "requests": len(self.requests()), "samples": len(self.requests(True)),
            "identities": len(self.identities), "identity_events": len(self.audits),
            "activities": len(self.activities), "rules": len(self.rules),
            "evidence_files": len(self.manifest),
            "formats": dict(sorted(Counter(p.suffix for p in self.files.values()).items())),
        }
