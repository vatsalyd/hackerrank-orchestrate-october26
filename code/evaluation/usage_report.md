# Model usage report

Run time (UTC): 2026-10-25T17:46:17.376731+00:00. Requests: 518. Completed decisions: 518. Elapsed seconds: 9.33. Output: `output.csv`.

This report includes model results consumed by this run, including cached preprocessing used to produce its answers. Origin tokens/cost and calls are attributed once per unique response, including invalid responses retried during extraction. New model calls this run: 0. Returned cloud responses this run: 0. Attempted HTTP calls: 0. Cached derivations consumed: 12.

| Provider / response model | New calls | Origin calls attributed | Cached origin responses | Input tokens | Output tokens | Total tokens | Estimated attributable USD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| OpenRouter (free route) / cohere/north-mini-code:free | 0 | 3 | 3 | 4572 | 2475 | 7047 | $0.000000 |
| OpenRouter (free route) / nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free | 0 | 1 | 1 | 1842 | 1258 | 3100 | $0.000000 |
| OpenRouter (free route) / nvidia/nemotron-3.5-lightning:free | 0 | 2 | 2 | 3499 | 1851 | 5350 | $0.000000 |
| OpenRouter (free route) / nvidia/nemotron-3.5-super-vl:free | 0 | 3 | 3 | 5143 | 5591 | 10734 | $0.000000 |
| OpenRouter (free route) / poolside/laguna-s-2.1:free | 0 | 1 | 1 | 1735 | 938 | 2673 | $0.000000 |
| OpenRouter (free route) / poolside/laguna-xs-2.1:free | 0 | 1 | 1 | 1772 | 1003 | 2775 | $0.000000 |
| OpenRouter (free route) / recursive/flint-v1.0:free | 0 | 1 | 1 | 1669 | 3843 | 5512 | $0.000000 |
| OpenRouter (free route) / xingchen-agi/xing4.0-29b-a4b:free | 0 | 1 | 1 | 1764 | 1045 | 2809 | $0.000000 |
| Overall | 0 | 13 | 13 | 21996 | 18004 | 40000 | $0.000000 |

Total/average attributable tokens: 40000 / 77.22 per request. Estimated total/per-request cost: $0.000000 / $0.00000000.

Requested optional cloud route: `openrouter/free`. Cloud tokens are API-reported; local-model input tokens come from its tokenizer and generated output tokens are zero for embedding classification. Native OCR is not assigned invented LLM token counts. Only free routes are allowed. No coding-assistant tokens are included; this report describes the submitted pipeline run.

The optional cloud client rejects paid model IDs and nonzero budgets, sets zero maximum prices for prompt, completion, request and image routing, and never lists a paid fallback. [Free routing documentation](https://openrouter.ai/docs/guides/routing/model-variants/free). Local processing has no API charge. HTTP failures without reported usage cannot be assigned invented token counts; attempted calls and returned usage are reported separately.
