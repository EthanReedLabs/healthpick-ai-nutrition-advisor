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
DEFAULT_REVIEW_EVIDENCE = (
    ROOT / "docs" / "evidence" / "action-06-full-structured-fact-review.json"
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


def build_public_summary(
    source: dict[str, Any], *, source_sha256: str, review_evidence: dict[str, Any]
) -> dict[str, Any]:
    gates = source["gates"]
    if set(gates) != set(PUBLIC_METRICS):
        raise ValueError("release report gate set does not match the frozen public metric set")
    if source["automatic_status"] != "PASS" or any(
        gate["status"] != "PASS" for gate in gates.values()
    ):
        raise ValueError("only a fully passing automatic release report may be published")
    if source["cleanup_status"] != "PASS" or not source["first_attempt_preserved"]:
        raise ValueError("release report integrity checks are incomplete")
    disposition = review_evidence.get("disposition", {})
    if not (
        review_evidence.get("status") == "PASS"
        and review_evidence.get("action_status") == "CLOSED"
        and disposition == {"verified": 74, "rejected": 6, "review_required": 0}
    ):
        raise ValueError("ACTION-06 full review evidence is incomplete")
    reviewed_case_count = source.get("manual_review", {}).get("case_count", 0)

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
        "overall_status": "PASS",
        "cleanup_status": source["cleanup_status"],
        "gates_passed": sum(gate["status"] == "PASS" for gate in gates.values()),
        "gates_total": len(gates),
        "metrics": {key: source["metrics"][key] for key in PUBLIC_METRICS},
        "gates": {key: gates[key] for key in PUBLIC_METRICS},
        "manual_review": {
            "status": "PASS",
            "action": "ACTION-06 CLOSED",
            "case_count": reviewed_case_count,
        },
        "first_attempt_preserved": source["first_attempt_preserved"],
        "public_note": (
            "自动发布门 9/9 已通过；80 条结构化事实完成最终处置："
            "74 条通过、6 条因源文缺字驳回并保持隔离、0 条待复核。"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--review-evidence", type=Path, default=DEFAULT_REVIEW_EVIDENCE)
    args = parser.parse_args()
    source_path = args.source.resolve()
    output_path = args.output.resolve()
    review_path = args.review_evidence.resolve()
    source = json.loads(source_path.read_text(encoding="utf-8"))
    review_evidence = json.loads(review_path.read_text(encoding="utf-8"))
    public = build_public_summary(
        source, source_sha256=sha256(source_path), review_evidence=review_evidence
    )
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
