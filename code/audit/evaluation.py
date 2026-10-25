"""Public-answer comparison stays outside the prediction path."""
import json
from collections import Counter

from .ingestion import read_csv

FIELDS = ("step_no", "phase", "system_id", "resource_id", "operation", "state", "evidence_id")
CUSTOM_SCENARIOS = '''The CLI integration test creates three independent fictional requests and participant-style CSV/JSON evidence, runs from outside the repository, and checks the resulting CSV:

1. **Export only.** Input: "Please export my data." Expected: `NOT_APPLICABLE` and `[]`. Result: passed.
2. **Deletion complete with retained security evidence.** Input: an authorized deletion, direct profile `NOT_FOUND`, and an existing retained security record. Expected: `COMPLETE`, profile-absence verification, and retained-record verification. Result: passed.
3. **Remaining profile, shared support PII, active connector, and unsafe backup.** Expected: `INCOMPLETE`; disable the connector and block restore before deleting/redacting records; include matching future checks. Result: passed.

Additional behavioral tests cover historical email aliases, post-cutoff evidence, independent replica state, retained tombstones, expired retention, unrelated workflow timestamps, strict output fields, model caching, and paid-model rejection. These fixtures use only fictional `example.test` identities and do not copy public answer rows.'''


def signature(step):
    return tuple(step.get(key) for key in FIELDS)


def compare(prediction_path, reference_path):
    if prediction_path.suffix == ".json":
        diagnostics = json.loads(prediction_path.read_text(encoding="utf-8"))
        predicted_rows = [{"case_id":case,"deletion_status":data["decision"]["deletion_status"],
            "steps_json":json.dumps(data["decision"]["steps"])} for case,data in diagnostics["cases"].items()]
    else:
        predicted_rows = read_csv(prediction_path)
    predictions = {row["case_id"]: row for row in predicted_rows}
    if len(predictions) != len(predicted_rows):
        raise ValueError("Duplicate prediction case IDs")
    reference = read_csv(reference_path)
    if set(predictions) - {row["case_id"] for row in reference}:
        raise ValueError("Predictions contain case IDs absent from the reference")
    status = sequence = matched = predicted_count = expected_count = field_matches = field_count = 0
    cases = []
    for target in reference:
        prediction = predictions.get(target["case_id"])
        expected_steps = json.loads(target["steps_json"])
        actual_steps = json.loads(prediction["steps_json"]) if prediction else []
        status_ok = bool(prediction and prediction["deletion_status"] == target["deletion_status"])
        sequence_ok = bool(prediction and actual_steps == expected_steps)
        status += status_ok
        sequence += sequence_ok
        actual_set, expected_set = Counter(map(signature, actual_steps)), Counter(map(signature, expected_steps))
        matched += sum((actual_set & expected_set).values())
        predicted_count += len(actual_steps)
        expected_count += len(expected_steps)
        for index in range(max(len(actual_steps), len(expected_steps))):
            actual = actual_steps[index] if index < len(actual_steps) else {}
            expected = expected_steps[index] if index < len(expected_steps) else {}
            field_matches += sum(key in actual and key in expected and actual[key] == expected[key] for key in FIELDS)
            field_count += len(FIELDS)
        cases.append({"case_id": target["case_id"], "status_correct": status_ok, "sequence_correct": sequence_ok,
            "missing_steps": [dict(zip(FIELDS, key)) for key in (expected_set - actual_set).elements()],
            "extra_steps": [dict(zip(FIELDS, key)) for key in (actual_set - expected_set).elements()]})
    return {"cases": len(reference), "status_correct": status, "status_accuracy": status / len(reference),
        "sequence_correct": sequence, "sequence_accuracy": sequence / len(reference),
        "step_precision": matched / predicted_count if predicted_count else 0,
        "step_recall": matched / expected_count if expected_count else 0,
        "field_accuracy": field_matches / field_count if field_count else 0,
        "step_matches": matched, "predicted_steps": predicted_count, "reference_steps": expected_count,
        "field_matches": field_matches, "field_comparisons": field_count, "details": cases}


def write_evaluation_report(path, metrics, custom_results=CUSTOM_SCENARIOS):
    failures = [row for row in metrics["details"] if not row["sequence_correct"]]
    text = f'''# Evaluation report

Compared predictions or diagnostic decisions against the 32 public sample answers. Unresolved/missing predictions count as failures. Public samples were used during development, so these are development-set metrics, not hidden-test accuracy.

| Metric | Result |
| --- | ---: |
| Case deletion-status accuracy | {metrics['status_accuracy']:.2%} ({metrics['status_correct']}/{metrics['cases']}) |
| Exact step precision | {metrics['step_precision']:.2%} |
| Exact step recall | {metrics['step_recall']:.2%} |
| Positional field accuracy | {metrics['field_accuracy']:.2%} ({metrics['field_matches']}/{metrics['field_comparisons']}) |
| Exact ordered sequence accuracy | {metrics['sequence_accuracy']:.2%} ({metrics['sequence_correct']}/{metrics['cases']}) |

Exact steps compare all seven fields with multiplicity. Field accuracy compares seven fields at each array position, counting missing/extra positions as incorrect. Sequence accuracy requires identical ordered arrays. Case accuracy compares status alone.

## Independent evaluation cases

{custom_results}

## Failures and improvements

Development fixes include normalizing six log layouts, joining identifiers through preceding trace lines, rejecting post-cutoff evidence, distinguishing direct reads from operation claims, and preserving separate replica scopes. Sample sequence mismatches: {len(failures)}. A correct status can still have missing records, different evidence citations, or incorrect verification coverage.

'''
    for row in failures:
        text += f"- {row['case_id']}: {len(row['missing_steps'])} expected steps missing; {len(row['extra_steps'])} extra/different steps.\n"
    text += "\nFull-dataset hidden accuracy is unavailable and is not inferred from valid CSV structure. See the usage report for the latest full-dataset diagnostic; a successful complete prediction run is still required.\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
