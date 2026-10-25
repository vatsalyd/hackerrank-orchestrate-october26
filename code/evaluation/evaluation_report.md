# Evaluation report

Compared predictions or diagnostic decisions against the 32 public sample answers. Unresolved/missing predictions count as failures. Public samples were used during development, so these are development-set metrics, not hidden-test accuracy.

| Metric | Result |
| --- | ---: |
| Case deletion-status accuracy | 100.00% (32/32) |
| Exact step precision | 68.39% |
| Exact step recall | 68.39% |
| Positional field accuracy | 80.04% (1143/1428) |
| Exact ordered sequence accuracy | 18.75% (6/32) |

Exact steps compare all seven fields with multiplicity. Field accuracy compares seven fields at each array position, counting missing/extra positions as incorrect. Sequence accuracy requires identical ordered arrays. Case accuracy compares status alone.

## Independent evaluation cases

The CLI integration test creates three independent fictional requests and participant-style CSV/JSON evidence, runs from outside the repository, and checks the resulting CSV:

1. **Export only.** Input: "Please export my data." Expected: `NOT_APPLICABLE` and `[]`. Result: passed.
2. **Deletion complete with retained security evidence.** Input: an authorized deletion, direct profile `NOT_FOUND`, and an existing retained security record. Expected: `COMPLETE`, profile-absence verification, and retained-record verification. Result: passed.
3. **Remaining profile, shared support PII, active connector, and unsafe backup.** Expected: `INCOMPLETE`; disable the connector and block restore before deleting/redacting records; include matching future checks. Result: passed.

Additional behavioral tests cover historical email aliases, post-cutoff evidence, independent replica state, retained tombstones, expired retention, unrelated workflow timestamps, strict output fields, model caching, and paid-model rejection. These fixtures use only fictional `example.test` identities and do not copy public answer rows.

Verified suite: 38 tests passed during this evaluation invocation.

## Failures and improvements

Development fixes include normalizing six log layouts, joining identifiers through preceding trace lines, rejecting post-cutoff evidence, distinguishing direct reads from operation claims, and preserving separate replica scopes. Sample sequence mismatches: 26. A correct status can still have missing records, different evidence citations, or incorrect verification coverage.


## Field breakdown

| Field | Matching positions | Accuracy |
| --- | ---: | ---: |
| step_no | 182/204 | 89.22% |
| phase | 176/204 | 86.27% |
| system_id | 156/204 | 76.47% |
| resource_id | 135/204 | 66.18% |
| operation | 158/204 | 77.45% |
| state | 160/204 | 78.43% |
| evidence_id | 176/204 | 86.27% |
- case_01: 1 expected steps missing; 1 extra/different steps.
- case_02: 1 expected steps missing; 1 extra/different steps.
- case_03: 1 expected steps missing; 0 extra/different steps.
- case_04: 2 expected steps missing; 1 extra/different steps.
- case_06: 1 expected steps missing; 1 extra/different steps.
- case_07: 4 expected steps missing; 7 extra/different steps.
- case_08: 1 expected steps missing; 2 extra/different steps.
- case_09: 3 expected steps missing; 2 extra/different steps.
- case_10: 1 expected steps missing; 1 extra/different steps.
- case_12: 1 expected steps missing; 2 extra/different steps.
- case_15: 5 expected steps missing; 8 extra/different steps.
- case_17: 2 expected steps missing; 5 extra/different steps.
- case_18: 5 expected steps missing; 4 extra/different steps.
- case_20: 3 expected steps missing; 2 extra/different steps.
- case_21: 3 expected steps missing; 3 extra/different steps.
- case_22: 1 expected steps missing; 1 extra/different steps.
- case_23: 2 expected steps missing; 1 extra/different steps.
- case_24: 1 expected steps missing; 1 extra/different steps.
- case_25: 2 expected steps missing; 1 extra/different steps.
- case_26: 4 expected steps missing; 3 extra/different steps.
- case_27: 4 expected steps missing; 3 extra/different steps.
- case_28: 4 expected steps missing; 3 extra/different steps.
- case_29: 2 expected steps missing; 2 extra/different steps.
- case_30: 5 expected steps missing; 4 extra/different steps.
- case_31: 1 expected steps missing; 1 extra/different steps.
- case_32: 1 expected steps missing; 1 extra/different steps.

Full-dataset hidden accuracy is unavailable and is not inferred from valid CSV structure. See the usage report for the measured full run.

## Full run and coverage model

The completed run produced exactly 518 sorted prediction rows. All 375 distinct evaluation request texts were interpreted through free OpenRouter models in bounded batches; repeated text was classified once. The final serialization reused those cached interpretations and performed no new cloud request. The usage report attributes the original preprocessing responses and all reported tokens.

Negative profile checks use complete dedicated SQL snapshots or global assurance exports without filter, pagination, truncation, or partial-scope metadata. All positive profile rows must carry a usable subject identifier. This is a declared-namespace completeness assumption and requires review when adapting to other exporters. Missing matches in an arbitrary file or a filtered query do not establish absence.

When a deleted row's physical resource ID is unrecoverable, negative verification uses the supplied stable user reference as an indexed lookup target. Diagnostics mark these as `subject_lookup`; these references are never used to synthesize destructive record actions. The canonical public answers often use historical physical IDs, contributing to resource-ID and sequence mismatches.

An available subject-bearing archive in a live recovery manager with restore/drill context is treated as a potential restore path until blocked. This does not assert an unshown operator permission flag, and future restore events are excluded by the cutoff.

All 518 decisions pass schema, allowed-operation/state, citation-time, step-number, phase-order, and request-ID checks. This is validation of format and grounding rules, not a claim of hidden-test accuracy. The artifacts remain drafts while reference/sequence alignment is improved.
