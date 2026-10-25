from collections import defaultdict
from datetime import datetime, timezone


def write_usage_report(path, client, requests, output_path, completed, elapsed):
    consumed = {}
    live = [event for event in client.events if not event["cache_hit"]]
    live_http = [event for event in live if event["provider"].startswith("OpenRouter")]
    for event in client.events:
        identity=event.get('event_id',event['key'])
        existing=consumed.get(identity)
        if existing is None or existing['cache_hit'] and not event['cache_hit']:
            consumed[identity]=event
    groups = defaultdict(lambda: {"calls":0,"origin_calls":0,"cached":0,"input":0,"output":0,"total":0,"cost":0.0})
    for event in consumed.values():
        totals = groups[(event["provider"], event["model"])]
        usage = event["usage"]
        prompt, completion = usage.get("prompt_tokens",0), usage.get("completion_tokens",0)
        calls = event.get("model_calls",1)
        totals["origin_calls"] += calls
        if event["cache_hit"]:
            totals["cached"] += 1
        else:
            totals["calls"] += calls
        totals["input"] += prompt
        totals["output"] += completion
        totals["total"] += usage.get("total_tokens",prompt+completion)
        totals["cost"] += usage.get("cost",0) or 0
    totals = {key:sum(group[key] for group in groups.values()) for key in ("calls","origin_calls","cached","input","output","total","cost")}
    text = f'''# Model usage report

Run time (UTC): {datetime.now(timezone.utc).isoformat()}. Requests: {requests}. Completed decisions: {completed}. Elapsed seconds: {elapsed:.2f}. Output: `{output_path.name}`.

This report includes model results consumed by this run, including cached preprocessing used to produce its answers. Origin tokens/cost and calls are attributed once per unique response, including invalid responses retried during extraction. New model calls this run: {sum(e.get('model_calls',1) for e in live)}. Returned cloud responses this run: {len(live_http)}. Attempted HTTP calls: {client.calls}. Cached derivations consumed: {len({e['key'] for e in client.events if e['cache_hit']})}.

| Provider / response model | New calls | Origin calls attributed | Cached origin responses | Input tokens | Output tokens | Total tokens | Estimated attributable USD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
'''
    for (provider, model), value in sorted(groups.items()):
        text += f"| {provider} / {model} | {value['calls']} | {value['origin_calls']} | {value['cached']} | {value['input']} | {value['output']} | {value['total']} | ${value['cost']:.6f} |\n"
    text += f"| Overall | {totals['calls']} | {totals['origin_calls']} | {totals['cached']} | {totals['input']} | {totals['output']} | {totals['total']} | ${totals['cost']:.6f} |\n"
    text += f'''
Total/average attributable tokens: {totals['total']} / {totals['total']/requests if requests else 0:.2f} per request. Estimated total/per-request cost: ${totals['cost']:.6f} / ${totals['cost']/requests if requests else 0:.8f}.

Requested optional cloud route: `{client.model}`. Cloud tokens are API-reported; local-model input tokens come from its tokenizer and generated output tokens are zero for embedding classification. Native OCR is not assigned invented LLM token counts. Only free routes are allowed. No coding-assistant tokens are included; this report describes the submitted pipeline run.

The optional cloud client rejects paid model IDs and nonzero budgets, sets zero maximum prices for prompt, completion, request and image routing, and never lists a paid fallback. [Free routing documentation](https://openrouter.ai/docs/guides/routing/model-variants/free). Local processing has no API charge. HTTP failures without reported usage cannot be assigned invented token counts; attempted calls and returned usage are reported separately.
'''
    if completed != requests:
        text += "\nThis is an incomplete development run; it did not produce a complete submission.\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
