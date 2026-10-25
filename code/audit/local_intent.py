"""Rule-first local intent with an optional cached embedding model for ambiguity."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from .intent import local_intent

# Participant-created semantic examples; no sample answers or case templates are read.
PROTOTYPES = [
    "Please permanently delete my account and erase my personal information.",
    "Close my account and remove the records linked to my old and current email addresses.",
    "My deletion failed. Finish removing the remaining copies of my personal data.",
    "Check that my requested deletion finished and that my profile and identifying data are gone.",
    "Remove my personal details from the search results and documents connected to my account.",
    "Please give me a copy or export of my information, keeping my account open.",
    "Correct my email address or delivery details. I want to keep using my account.",
    "Unsubscribe me from promotional marketing messages and newsletters.",
    "Do not delete my account. I do not authorize deletion of my personal information.",
    "Explain what deleting an account means and how your deletion policy works.",
]


def classify_local(requests, cache, usage, python=None, model="sentence-transformers/all-MiniLM-L6-v2"):
    results, failures, pending = {}, {}, []
    for request in requests:
        try:
            results[request.case_id] = local_intent(request.request_text)
        except ValueError:
            pending.append(request)
    if not pending:
        return results, failures
    payload = {"model":model, "prototypes":PROTOTYPES, "texts":[row.request_text for row in pending]}
    key = hashlib.sha256(json.dumps(["local-intent-v1",payload],sort_keys=True).encode()).hexdigest()
    path = cache / "local_intent" / (key + ".json")
    hit = path.exists()
    if hit:
        values = json.loads(path.read_text(encoding="utf-8"))
    else:
        command = [python or sys.executable, str(Path(__file__).with_name("local_intent_worker.py"))]
        try:
            run = subprocess.run(command,input=json.dumps(payload),capture_output=True,encoding="utf-8",timeout=180,check=True)
            # Some library versions emit loading notices to stdout before the JSON result.
            values = json.loads(run.stdout[run.stdout.find('{"scores"'):])
        except (subprocess.SubprocessError, ValueError):
            return results, {row.case_id:"Local intent model unavailable or failed; install optional local dependencies/model" for row in pending}
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(values),encoding="utf-8")
    if len(values["scores"]) != len(pending):
        return results,{row.case_id:"Local model returned incomplete intent scores" for row in pending}
    usage.events.append({"key":key,"task":"local-intent","cache_hit":hit,"provider":"Local Transformers",
        "model":model,"model_calls":values["model_calls"],"called_at":datetime.now(timezone.utc).isoformat(),
        "usage":{"prompt_tokens":values["input_tokens"],"completion_tokens":0,"total_tokens":values["input_tokens"],"cost":0}})
    for row, scores in zip(pending,values["scores"]):
        positive, negative = max(scores[:5]), max(scores[5:])
        if max(positive,negative) < 0.35 or abs(positive-negative) < 0.035:
            failures[row.case_id] = "Local semantic intent is ambiguous; explicit interpretation required"
        else:
            results[row.case_id] = positive > negative
    return results, failures
