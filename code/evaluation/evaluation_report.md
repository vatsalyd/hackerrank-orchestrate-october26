# Evaluation report

Compared predictions or diagnostic decisions against the 32 public sample answers. Unresolved/missing predictions count as failures. Public samples were used during development, so these are development-set metrics, not hidden-test accuracy.

| Metric | Result |
| --- | ---: |
| Case deletion-status accuracy | 100.00% (32/32) |
| Exact step precision | 72.11% |
| Exact step recall | 70.98% |
| Positional field accuracy | 82.59% (1162/1407) |
| Exact ordered sequence accuracy | 21.88% (7/32) |

Exact steps compare all seven fields with multiplicity. Field accuracy compares seven fields at each array position, counting missing/extra positions as incorrect. Sequence accuracy requires identical ordered arrays. Case accuracy compares status alone.

## Independent evaluation cases

The CLI integration test creates three independent fictional requests and participant-style CSV/JSON evidence, runs from outside the repository, and checks the resulting CSV:

1. **Export only.** Input: "Please export my data." Expected: `NOT_APPLICABLE` and `[]`. Result: passed.
2. **Deletion complete with retained security evidence.** Input: an authorized deletion, direct profile `NOT_FOUND`, and an existing retained security record. Expected: `COMPLETE`, profile-absence verification, and retained-record verification. Result: passed.
3. **Remaining profile, shared support PII, active connector, and unsafe backup.** Expected: `INCOMPLETE`; disable the connector and block restore before deleting/redacting records; include matching future checks. Result: passed.

Additional behavioral tests cover historical email aliases, post-cutoff evidence, independent replica state, retained tombstones, expired retention, unrelated workflow timestamps, strict output fields, model caching, and paid-model rejection. These fixtures use only fictional `example.test` identities and do not copy public answer rows.

Verified suite: 45 tests passed during this evaluation invocation.

## Failures and improvements

Development fixes include normalizing six log layouts, joining identifiers through preceding trace lines, rejecting post-cutoff evidence, distinguishing direct reads from operation claims, preserving separate replica scopes, citing current reads, and binding screenshot identifiers to their own row or detail panel. Sample sequence mismatches: 25. A correct status can still have missing records, different evidence citations, or incorrect verification coverage.


## Field breakdown

| Field | Matching positions | Accuracy |
| --- | ---: | ---: |
| step_no | 182/201 | 90.55% |
| phase | 179/201 | 89.05% |
| system_id | 159/201 | 79.10% |
| resource_id | 139/201 | 69.15% |
| operation | 162/201 | 80.60% |
| state | 164/201 | 81.59% |
| evidence_id | 177/201 | 88.06% |

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

## Coverage model and remaining limitations

Final full-dataset counts, providers, model responses, tokens, and costs are recorded in the usage report. Public sample metrics do not establish hidden-test accuracy.

Negative profile checks use complete dedicated SQL snapshots or global assurance exports without filter, pagination, truncation, or partial-scope metadata. All positive profile rows must carry a usable subject identifier. This is a declared-namespace completeness assumption and requires review when adapting to other exporters. Missing matches in an arbitrary file or a filtered query do not establish absence.

When a deleted row's physical resource ID is unrecoverable, negative verification uses the supplied stable user reference as an indexed lookup target. Diagnostics mark these as `subject_lookup`; these references never synthesize destructive record actions. Canonical public answers can use historical physical IDs for which the solver has no grounded identity link, contributing to resource-ID and sequence mismatches.

An available subject-bearing archive in a live recovery manager with restore/drill context is treated as a potential restore path until blocked. This does not assert an unshown operator permission flag, and future restore events are excluded by the cutoff.

Screenshot identifiers are bound to table rows or selected detail panels using local OCR geometry. Activity history does not establish current ownership. Neither unbound native transcript text nor model-returned raw fields can override those subject bindings. Ambiguous flat transcripts remain unlinked until another eligible source supplies the connection.

A successful full run validates schema, allowed operations/states, citation times, step numbers, phase order, and request IDs. Format and grounding checks do not prove hidden accuracy. The artifacts remain drafts while reference and sequence alignment is improved.
