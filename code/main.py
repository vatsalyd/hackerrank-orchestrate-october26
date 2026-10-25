"""Run from any directory: python /path/to/repo/code/main.py inventory."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from audit.ingestion import Dataset
from audit.extraction import Extractor
from audit.llm import ModelClient
from audit.storage import write_evidence_index
from audit.engine import Auditor
from audit.export import write_output
from audit.intent import classify_requests,classify_hybrid_requests,local_intent
from audit.usage import write_usage_report
from audit.local_intent import classify_local


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Point-in-time deletion auditor")
    parser.add_argument("command", nargs="?", default="run", choices=["inventory", "extract", "run", "diagnose"])
    parser.add_argument("--dataset", type=Path, default=root / "dataset")
    parser.add_argument("--cache", type=Path, default=root / ".cache")
    parser.add_argument("--online", action="store_true", help="Allow explicitly free OpenRouter calls on cache misses")
    parser.add_argument("--provider", choices=["local","openrouter"], default="local")
    parser.add_argument("--model", default="openrouter/free")
    parser.add_argument("--max-cost", type=float, default=0.0, help="Must remain zero; paid models are disabled")
    parser.add_argument("--sample", action="store_true")
    parser.add_argument("--output", type=Path, default=root / "output.csv")
    parser.add_argument("--structured-only", action="store_true", help="Diagnosis only: skip PDF/images")
    parser.add_argument("--local-intent", action="store_true", help="Use conservative local language rules")
    parser.add_argument("--diagnostics-dir", type=Path, default=root / "evaluation_runs")
    parser.add_argument("--local-python", help="Python executable with optional local Transformers dependencies")
    parser.add_argument('--artifact-mode',choices=['native','hybrid','model'],default='hybrid',
                        help='Hybrid uses a free model only for ambiguous artifacts, with native fallback')
    parser.add_argument('--intent-mode',choices=['model','hybrid'],default='model',
                        help='Model interprets every distinct request text; hybrid keeps clear English local')
    args = parser.parse_args()
    dataset = Dataset(args.dataset)
    if args.command == "inventory":
        print(json.dumps(dataset.inventory(), indent=2))
    else:
        if args.structured_only and args.command != "diagnose":
            parser.error("--structured-only is allowed only for diagnosis, not submission generation")
        started = time.monotonic()
        model = ModelClient(args.cache, args.online, args.model, max_cost=args.max_cost)
        if args.online and args.provider != "openrouter":
            parser.error("--online requires --provider openrouter; paid providers are not supported")
        requests=dataset.requests(args.sample)
        intent_errors={}
        intents=None
        if args.command!='extract' and not args.local_intent:
            if args.provider=='local':
                intents,intent_errors=classify_local(requests,args.cache,model,args.local_python)
            else:
                intents=(classify_requests if args.intent_mode=='model' else classify_hybrid_requests)(requests,model)
        extraction = Extractor(dataset, model if args.provider == "openrouter" else None, args.cache,args.artifact_mode).extract(args.structured_only)
        write_evidence_index(args.cache / "evidence.sqlite3", extraction)
        summary = {"files": len(extraction.coverage), "observations": len(extraction.observations),
            "tables": len(extraction.tables), "zero_observation_files": [key for key, value in extraction.coverage.items() if not value],
            "skipped_files": extraction.skipped, "issues":extraction.issues, "model_events": model.events}
        (args.cache / "extraction_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(json.dumps({key: value for key, value in summary.items() if key != "model_events"}, indent=2))
        if args.command == "extract":
            return
        if not args.sample and len(requests) != 518:
            raise ValueError("Evaluation dataset must contain exactly 518 requests")
        auditor, decisions, diagnostics, failures = Auditor(dataset, extraction), [], {}, []
        for request in requests:
            try:
                if request.case_id in intent_errors:
                    raise ValueError(intent_errors[request.case_id])
                intent = local_intent(request.request_text) if intents is None else intents[request.case_id]
                decision, facts = auditor.audit(request, intent)
                decisions.append(decision)
                diagnostics[request.case_id] = {"decision": decision.model_dump(), **facts}
            except ValueError as exc:
                failures.append({"case_id":request.case_id,"error":str(exc)})
        diagnostic_dir = args.diagnostics_dir
        diagnostic_dir.mkdir(parents=True, exist_ok=True)
        suffix = "sample" if args.sample else "full"
        (diagnostic_dir / f"{suffix}_diagnostics.json").write_text(json.dumps(
            {"cases":diagnostics,"failures":failures,"skipped_files":extraction.skipped}, indent=2), encoding="utf-8")
        if args.command == "run" and not failures:
            write_output(args.output, decisions, [request.case_id for request in requests])
        usage_path = diagnostic_dir / f"{suffix}_usage_report.md" if args.command == "diagnose" or failures or args.sample else root / "code/evaluation/usage_report.md"
        write_usage_report(usage_path, model, len(requests), args.output, len(decisions), time.monotonic()-started)
        print(json.dumps({"resolved":len(decisions),"unresolved":len(failures),"failures":failures}, indent=2))
        if failures and args.command == "run":
            raise SystemExit("No output written: resolve the reported evidence/intent gaps first")


if __name__ == "__main__":
    main()
