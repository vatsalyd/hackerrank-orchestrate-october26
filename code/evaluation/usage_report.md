# NOT A FINAL SUBMISSION REPORT

This is the latest local full-dataset diagnostic, not a completed prediction run. All 94 evidence files were processed, producing 3035 observations. Decisions resolved: 380/518; unresolved: 138. No cloud inference call has run. A free OpenRouter key was approved but is not available in the execution environment.

Known gaps: grounded primary-profile absence, conservative intent abstention, missing resource links, and restore-permission ambiguity. Final-run totals must be refreshed after unsupported cases are resolved. The measured local usage below distinguishes cached origin work from new calls.

# Model usage report

Run time (UTC): 2026-10-25T13:17:53.810294+00:00. Requests: 518. Completed decisions: 380. Elapsed seconds: 7.71. Output: `output.csv`.

This report includes model results consumed by this run, including cached preprocessing used to produce its answers. Origin tokens/cost and calls are attributed once per unique result. New model calls this run: 0. Successful cloud responses this run: 0. Attempted HTTP calls: 0. Local cache reads: 1.

| Provider / response model | New calls | Origin calls attributed | Cached results | Input tokens | Output tokens | Total tokens | Estimated attributable USD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Local Transformers / sentence-transformers/all-MiniLM-L6-v2 | 0 | 4 | 1 | 3910 | 0 | 3910 | $0.000000 |
| Overall | 0 | 4 | 1 | 3910 | 0 | 3910 | $0.000000 |

Total/average attributable tokens: 3910 / 7.55 per request. Estimated total/per-request cost: $0.000000 / $0.00000000.

Requested optional cloud route: `openrouter/free`. Cloud tokens are API-reported; local-model input tokens come from its tokenizer and generated output tokens are zero for embedding classification. Native OCR is not assigned invented LLM token counts. Only free routes are allowed. No coding-assistant tokens are included; this report describes the submitted pipeline run.

The optional cloud client rejects paid model IDs and nonzero budgets, sets zero maximum prices for prompt, completion, request and image routing, and never lists a paid fallback. [Free routing documentation](https://openrouter.ai/docs/guides/routing/model-variants/free). Local processing has no API charge. HTTP failures without reported usage cannot be assigned invented token counts; attempted calls and returned usage are reported separately.

This is an incomplete development run; it did not produce a complete submission.
