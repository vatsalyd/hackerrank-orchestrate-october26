"""Run from any directory: python /path/to/repo/code/main.py inventory."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from audit.ingestion import Dataset
from audit.extraction import Extractor
from audit.llm import ModelClient
from audit.storage import write_evidence_index


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Point-in-time deletion auditor")
    parser.add_argument("command", choices=["inventory", "extract"])
    parser.add_argument("--dataset", type=Path, default=root / "dataset")
    parser.add_argument("--cache", type=Path, default=root / ".cache")
    parser.add_argument("--online", action="store_true", help="Allow paid model calls on cache misses")
    parser.add_argument("--model", default="deepseek-flash")
    args = parser.parse_args()
    dataset = Dataset(args.dataset)
    if args.command == "inventory":
        print(json.dumps(dataset.inventory(), indent=2))
    else:
        model = ModelClient(args.cache, args.online, args.model)
        extraction = Extractor(dataset, model).extract()
        write_evidence_index(args.cache / "evidence.sqlite3", extraction)
        summary = {"files": len(extraction.coverage), "observations": len(extraction.observations),
            "tables": len(extraction.tables), "zero_observation_files": [key for key, value in extraction.coverage.items() if not value],
            "model_events": model.events}
        (args.cache / "extraction_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(json.dumps({key: value for key, value in summary.items() if key != "model_events"}, indent=2))


if __name__ == "__main__":
    main()
