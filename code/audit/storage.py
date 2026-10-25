import json
import sqlite3
from dataclasses import asdict


def write_evidence_index(path, extraction):
    """Rebuild derived facts, leaving all participant inputs untouched."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as db:
        db.execute("DROP TABLE IF EXISTS observations")
        db.execute("CREATE TABLE observations (evidence_id TEXT, system_id TEXT, resource_id TEXT, observed_at TEXT, payload TEXT)")
        for observation in extraction.observations:
            value = asdict(observation)
            value["identifiers"] = sorted(value["identifiers"])
            db.execute("INSERT INTO observations VALUES (?, ?, ?, ?, ?)", (observation.evidence_id,
                observation.system_id, observation.resource_id, observation.observed_at, json.dumps(value, ensure_ascii=False)))
        db.execute("CREATE INDEX resource_lookup ON observations(system_id, resource_id, observed_at)")
        db.execute("CREATE INDEX citation_lookup ON observations(evidence_id)")
