import argparse
import json
import sys
import io
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from audit.evaluation import CUSTOM_SCENARIOS, compare, write_evaluation_report


def main():
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Evaluate public sample predictions")
    parser.add_argument("predictions", type=Path)
    parser.add_argument("--reference", type=Path, default=root / "dataset/sample_output.csv")
    parser.add_argument("--report", type=Path, default=Path(__file__).with_name("evaluation_report.md"))
    args = parser.parse_args()
    metrics = compare(args.predictions, args.reference)
    suite=unittest.defaultTestLoader.discover(str(root/'code/tests'))
    tests=unittest.TextTestRunner(stream=io.StringIO(),verbosity=1).run(suite)
    if not tests.wasSuccessful():
        raise SystemExit("Independent tests failed; refusing to claim passing custom cases")
    write_evaluation_report(args.report, metrics, CUSTOM_SCENARIOS+f"\n\nVerified suite: {tests.testsRun} tests passed during this evaluation invocation.")
    args.report.with_suffix(".json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in metrics.items() if key != "details"}, indent=2))


if __name__ == "__main__":
    main()
