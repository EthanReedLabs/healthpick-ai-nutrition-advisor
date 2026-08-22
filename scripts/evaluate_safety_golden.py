from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from healthpick_api.evaluation import evaluate_golden_cases, load_golden_cases  # noqa: E402

DEFAULT_DATASET = ROOT / "tests" / "fixtures" / "phase04_safety_golden.jsonl"
DEFAULT_OUTPUT = ROOT / "docs" / "evidence" / "phase-04-p04-06-golden.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate the Phase 04 safety golden set")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    report = evaluate_golden_cases(load_golden_cases(args.dataset))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
