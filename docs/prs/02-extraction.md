Title: Extract evidence with provenance, scoped snapshots, and model accounting

Adds nested JSON, isolated SQLite snapshots, six log layouts with time-bounded trace joins, text records, and PDF/image interpretation. Every observation retains its citation, capture and observation times, scope, and source location. The model adapter caches by content and records provider/model/token usage without credentials.

Validation: six unit tests pass, including five log layouts and nested snapshot timestamps. All 94 participant evidence paths exist. Local structured extraction was exercised; cloud interpretation has not been exercised. A later PR replaces the initial model adapter with free-only routing and adds local OCR/intent.
