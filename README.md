# Ghost Data Still Exists

Python deletion auditing at each request's `audit_at`, with grounded identity links, scoped evidence, policy decisions, and ordered remediation/verification.

Current stage: a runnable development pipeline and reviewable PR stack. The latest local diagnostic resolved 380/518 cases. Unsupported cases remain explicit; no final 518-row submission has been produced. Paid model inference is disabled.

## Setup

Python 3.12+; development uses Python 3.14.8.

```text
python -m venv .venv
```

Activate with `.venv\Scripts\Activate.ps1` on Windows or `source .venv/bin/activate` on macOS/Linux:

```text
python -m pip install -r requirements.txt
python code/main.py inventory
python -m unittest discover -s code/tests -v
```

## Local run

Native PDF text extraction uses pypdf. Image OCR uses Windows OCR automatically on Windows; install the Tesseract executable on other platforms.

Optional local semantic intent uses a small public model. Install its dependencies in the same Python environment and download weights once, without authentication or participant data:

```text
python -m pip install -r requirements-local.txt
python code/prepare_local_model.py
python code/main.py diagnose --sample
python code/main.py diagnose
```

Inference reads cached weights with network access disabled. `--local-python PATH` selects a different interpreter containing local model dependencies. Missing weights or uncertain intent produce explicit unresolved cases. Local inference has no API charge.

A lightweight diagnosis can skip visual evidence and semantic inference:

```text
python code/main.py diagnose --structured-only --local-intent --sample
```

Diagnostics go to `evaluation_runs/`; derived facts and content caches go to `.cache/`. Defaults resolve from the repository root, regardless of working directory.

## Optional free cloud processing

Only OpenRouter's `openrouter/free` route and explicit `:free` model IDs are accepted. Paid model IDs, nonzero budgets, paid credentials, and paid fallbacks are rejected. Every request sets zero maximum prompt, completion, per-request, and image prices.

Set `OPENROUTER_API_KEY` in the environment; never paste it into source or logs. The explicit flags below allow participant request text and evidence, including identifiers in PDFs/images, to be sent to OpenRouter and its free-model providers. Free quotas and model availability can limit a run; the agent does not upgrade to paid inference.

```text
python code/main.py diagnose --sample --provider openrouter --online
python code/main.py run --sample --provider openrouter --online --output evaluation_runs/sample_output.csv
python code/main.py run --provider openrouter --online
```

A repeated run can omit `--online` and use cached free-model results; cache misses fail. No DeepSeek credential is used. [Free-route guarantees](https://openrouter.ai/docs/guides/routing/model-variants/free).

## Output, evaluation, and submission

A successful full `run` writes root `output.csv` only when all 518 cases have supported decisions and valid ordered steps. Failures preserve any older output; do not mistake a pre-existing file for the latest run.

```text
python code/main.py run
python code/evaluation/main.py evaluation_runs/sample_diagnostics.json
python code/package.py
```

The evaluator accepts sample prediction CSV or sample diagnostic JSON. Unresolved cases count as failures. It reports status accuracy, exact step precision/recall, positional field accuracy, and exact sequence accuracy, and runs independent behavioral/CLI tests before claiming custom-case results. Sample answers never enter prediction code.

Evaluation Markdown lives under `code/evaluation/`. A successful full run writes the final usage report there; incomplete/sample runs put usage under `evaluation_runs/`. Reports distinguish new model calls, cached-origin usage, locally tokenized inputs, provider-reported output tokens, and zero API cost. Full hidden accuracy remains unavailable.

Packaging refuses missing/incomplete outputs or unfinished reports. The archive includes source/prompts, requirements, README, and evaluation Markdown; it excludes the dataset, environments, caches, raw data reports, credentials, transcripts, and nested archives. Submit `code.zip`, root `output.csv`, and root `log.txt` as `chat_transcript`. Original trace packaging is described in `agent_trace_instructions.md`.

## Investigation rules

- Match current and historical identifiers; names and nearby timestamps alone cannot link resources.
- Require both capture and observation times to satisfy the cutoff.
- Preserve replica scope; workflow success does not establish deletion.
- Apply conditional retention, redaction, anonymization, and tombstone rules.
- Stop unsafe flows/restores before changing dependent records.
- Keep unresolved identity, state, scope, or policy questions visible rather than fabricating evidence.

Design rationale: `docs/FOUNDATION.md`. Increment notes: `docs/prs/`.

Challenge and submission: https://www.hackerrank.com/contests/hackerrank-orchestrate-october26/challenges/ghost-data-still-exists

The challenge end time is not configured.
