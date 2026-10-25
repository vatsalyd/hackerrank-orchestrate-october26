Title: Finalize submission artifacts and sanitized agent traces

Freezes the tested audit behavior, adds manual-upload and interview notes, and exports checkout-specific Codex JSONL traces with credential/contact redaction. The trace archive is separate from the source package and preserves original trace files. Evaluation limitations remain explicit.

Validation: all 518 rows and citation cutoffs pass, and 48 tests pass, including long-transcript redaction and exclusion of unrelated sessions. Public status/field/sequence results remain 32/32, 82.59%, and 7/32. The ZIP includes both required evaluation report paths and excludes datasets, caches, credentials, transcripts, and nested archives. Three checkout-specific Codex sessions are exported separately; final artifact hashes are recorded. No paid inference or additional cloud model calls were used.
