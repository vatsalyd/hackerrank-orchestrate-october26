"""Run from any directory: python /path/to/repo/code/main.py inventory."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from audit.ingestion import Dataset


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Point-in-time deletion auditor")
    parser.add_argument("command", choices=["inventory"])
    parser.add_argument("--dataset", type=Path, default=root / "dataset")
    args = parser.parse_args()
    dataset = Dataset(args.dataset)
    print(json.dumps(dataset.inventory(), indent=2))


if __name__ == "__main__":
    main()
