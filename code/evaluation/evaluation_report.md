# Evaluation report

Compared predictions or diagnostic decisions against the 32 public sample answers. Unresolved/missing predictions count as failures. Public samples were used during development, so these are development-set metrics, not hidden-test accuracy.

| Metric | Result |
| --- | ---: |
| Case deletion-status accuracy | 65.62% (21/32) |
| Exact step precision | 66.67% |
| Exact step recall | 50.78% |
| Positional field accuracy | 59.19% (837/1414) |
| Exact ordered sequence accuracy | 15.62% (5/32) |

Exact steps compare all seven fields with multiplicity. Field accuracy compares seven fields at each array position, counting missing/extra positions as incorrect. Sequence accuracy requires identical ordered arrays. Case accuracy compares status alone.

## Independent evaluation cases

The CLI integration test creates three independent fictional requests and participant-style CSV/JSON evidence, runs from outside the repository, and checks the resulting CSV:

1. **Export only.** Input: "Please export my data." Expected: `NOT_APPLICABLE` and `[]`. Result: passed.
2. **Deletion complete with retained security evidence.** Input: an authorized deletion, direct profile `NOT_FOUND`, and an existing retained security record. Expected: `COMPLETE`, profile-absence verification, and retained-record verification. Result: passed.
3. **Remaining profile, shared support PII, active connector, and unsafe backup.** Expected: `INCOMPLETE`; disable the connector and block restore before deleting/redacting records; include matching future checks. Result: passed.

Additional behavioral tests cover historical email aliases, post-cutoff evidence, independent replica state, retained tombstones, expired retention, unrelated workflow timestamps, strict output fields, model caching, and paid-model rejection. These fixtures use only fictional `example.test` identities and do not copy public answer rows.

Verified suite: 22 tests passed during this evaluation invocation.

## Failures and improvements

Development fixes include normalizing six log layouts, joining identifiers through preceding trace lines, rejecting post-cutoff evidence, distinguishing direct reads from operation claims, and preserving separate replica scopes. Sample sequence mismatches: 27. A correct status can still have missing records, different evidence citations, or incorrect verification coverage.

- case_01: 1 expected steps missing; 0 extra/different steps.
- case_02: 1 expected steps missing; 0 extra/different steps.
- case_03: 2 expected steps missing; 1 extra/different steps.
- case_04: 2 expected steps missing; 0 extra/different steps.
- case_06: 2 expected steps missing; 1 extra/different steps.
- case_07: 4 expected steps missing; 6 extra/different steps.
- case_08: 2 expected steps missing; 2 extra/different steps.
- case_09: 5 expected steps missing; 0 extra/different steps.
- case_10: 2 expected steps missing; 1 extra/different steps.
- case_12: 1 expected steps missing; 2 extra/different steps.
- case_14: 5 expected steps missing; 0 extra/different steps.
- case_15: 5 expected steps missing; 8 extra/different steps.
- case_17: 2 expected steps missing; 5 extra/different steps.
- case_18: 6 expected steps missing; 4 extra/different steps.
- case_20: 4 expected steps missing; 2 extra/different steps.
- case_21: 3 expected steps missing; 0 extra/different steps.
- case_22: 4 expected steps missing; 3 extra/different steps.
- case_23: 4 expected steps missing; 2 extra/different steps.
- case_24: 1 expected steps missing; 1 extra/different steps.
- case_25: 3 expected steps missing; 0 extra/different steps.
- case_26: 6 expected steps missing; 0 extra/different steps.
- case_27: 6 expected steps missing; 0 extra/different steps.
- case_28: 6 expected steps missing; 0 extra/different steps.
- case_29: 6 expected steps missing; 5 extra/different steps.
- case_30: 6 expected steps missing; 4 extra/different steps.
- case_31: 3 expected steps missing; 0 extra/different steps.
- case_32: 3 expected steps missing; 2 extra/different steps.

Full-dataset hidden accuracy is unavailable and is not inferred from valid CSV structure. See the usage report for the latest full-dataset diagnostic; a successful complete prediction run is still required.

## Current full-dataset coverage

The local diagnostic processed all 94 evidence files and extracted 3000 observations. It resolved 375/518 requests and withheld 143 unsupported decisions. No completed submission is claimed.
