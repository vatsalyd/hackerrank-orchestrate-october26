# Manual submission

Upload at https://www.hackerrank.com/contests/hackerrank-orchestrate-october26/challenges/ghost-data-still-exists

| Artifact at repository root | Purpose |
| --- | --- |
| `code.zip` | Runnable Python solution, prompts, requirements, README, and evaluation reports |
| `output.csv` | All 518 predictions, sorted by case ID |
| `log.txt` | Chat transcript required by AGENTS.md |
| `agent-trace.zip` | Sanitized structured Codex traces requested by agent_trace_instructions.md; includes a log copy |

Keep the files separate; do not put the dataset, credentials, or output CSV into `code.zip`. `submission_checksums.json` records SHA-256 hashes for local integrity checking and is not a required upload. Both required reports are present at `evaluation/evaluation_report.md` and `evaluation/usage_report.md` inside the code archive.

The prepared output has 3,034 steps: 355 INCOMPLETE, 153 COMPLETE, and 10 NOT_APPLICABLE cases. Public sample status accuracy is 32/32; exact step precision/recall is 72.11%/70.98%, field accuracy is 82.59%, and exact ordered sequence accuracy is 7/32. These are development-set results. Hidden accuracy is unavailable, and remaining identity-reference and namespace-coverage assumptions are documented in the evaluation report.

The final pipeline run attributes 40,000 reported tokens across 13 free-model responses consumed through 12 cached derivations. The final rerun makes zero new model calls; estimated API cost is $0. Coding-assistant usage is excluded from pipeline usage.

## Reproduce

Install `requirements.txt` in a Python 3.12+ environment. Windows supplies native OCR; other systems need the Tesseract executable. Configure `OPENROUTER_API_KEY` in the terminal environment, then run:

```text
python code/main.py run --provider openrouter --online --artifact-mode native --intent-mode model
python code/package.py
```

Only free routes are allowed; provider quotas can limit a fresh run. The supplied output is already generated and does not need regeneration before upload. A run with existing local caches can omit `--online`.

The trace archive is a live snapshot of complete JSONL records, with credentials and contact details redacted. To refresh after ending the coding session, run `python code/export_trace.py` from a terminal with relevant credential environment variables available. Original source traces and the append-only root log are preserved.

For the interview, review `docs/INTERVIEW.md`. Submit promptly using the link above; no official end time is configured in this checkout.
