import csv
import json
import os


def write_output(path, decisions, expected_ids):
    rows = sorted(decisions, key=lambda value: value.case_id)
    if [row.case_id for row in rows] != sorted(expected_ids):
        raise ValueError("Prediction IDs must match the request set exactly")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(["case_id", "deletion_status", "steps_json"])
            for row in rows:
                writer.writerow([row.case_id, row.deletion_status,
                    json.dumps([step.model_dump() for step in row.steps], ensure_ascii=False, separators=(",", ":"))])
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
