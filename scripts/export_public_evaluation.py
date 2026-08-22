"""Export a strict, secret-free public view of one immutable release report."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = (
    ROOT / "evals" / "reports" / "release-v1.1-20260822T132040911243+0800" / "summary.json"
)
DEFAULT_OUTPUT = (
    ROOT / "apps" / "api" / "healthpick_api" / "evaluation" / "release-summary-v1.1.json"
)

PUBLIC_METRICS = (
    "route_accuracy",
    "source_leakage_rate",
    "numeric_fact_accuracy",
    "citation_support_rate",
    "high_risk_recall",
    "contraindication_conflict_rate",
    "multi_turn_constraint_rate",
    "unhandled_5xx",
    "first_response_p95_ms",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_public_summary(source: dict[str, Any], *, source_sha256: str) -> dict[str, Any]:
    gates = source["gates"]
    if set(gates) != set(PUBLIC_METRICS):
        raise ValueError("release report gate set does not match the frozen public metric set")
    if source["automatic_status"] != "PASS" or any(
        gate["status"] != "PASS" for gate in gates.values()
    ):
        raise ValueError("only a fully passing automatic release report may be published")
    if source["cleanup_status"] != "PASS" or not source["first_attempt_preserved"]:
        raise ValueError("release report integrity checks are incomplete")

    return {
        "schema_version": 1,
        "report_id": source["run_id"],
        "source_report_sha256": source_sha256,
        "dataset_version": source["dataset"]["version"],
        "dataset_sha256": source["dataset"]["sha256"],
        "case_count": source["dataset"]["case_count"],
        "turn_count": source["dataset"]["turn_count"],
        "completed_at": source["completed_at"],
        "automatic_status": source["automatic_status"],
        "overall_status": source["overall_status"],
        "cleanup_status": source["cleanup_status"],
        "gates_passed": sum(gate["status"] == "PASS" for gate in gates.values()),
        "gates_total": len(gates),
        "metrics": {key: source["metrics"][key] for key in PUBLIC_METRICS},
        "gates": {key: gates[key] for key in PUBLIC_METRICS},
        "manual_review": source["manual_review"],
        "first_attempt_preserved": source["first_attempt_preserved"],
        "public_note": (
            "自动发布门已通过；知识事实的第二人复核仍按 ACTION-06 独立跟踪，"
            "完成前整体状态保持 PASS_WITH_ACTION。"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    source_path = args.source.resolve()
    output_path = args.output.resolve()
    source = json.loads(source_path.read_text(encoding="utf-8"))
    public = build_public_summary(source, source_sha256=sha256(source_path))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(public, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"PUBLIC EVALUATION: {public['gates_passed']}/{public['gates_total']} gates "
        f"-> {output_path.relative_to(ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
