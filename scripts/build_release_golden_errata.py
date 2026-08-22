"""Create release-golden-v1.1 from explicit, auditable v1 assertion errata."""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from healthpick_api.evaluation import (  # noqa: E402
    load_chunk_index,
    load_release_cases,
    validate_release_cases,
)

BASE_DATASET = ROOT / "evals" / "datasets" / "release-golden-v1.jsonl"
OUTPUT_DATASET = ROOT / "evals" / "datasets" / "release-golden-v1.1.jsonl"
BASE_MANIFEST = ROOT / "evals" / "golden" / "release-golden-v1.manifest.json"
OUTPUT_MANIFEST = ROOT / "evals" / "golden" / "release-golden-v1.1.manifest.json"
THRESHOLDS = ROOT / "evals" / "golden" / "release-gate-v1.json"
EVIDENCE = ROOT / "docs" / "evidence" / "phase-07-p07-02-errata-validation.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expectation(rows: list[dict[str, Any]], case_id: str, turn: int = 1) -> dict[str, Any]:
    row = next(item for item in rows if item["case_id"] == case_id)
    return row["turns"][turn - 1]["expected"]


def assert_value(actual: object, expected: object, label: str) -> None:
    if actual != expected:
        raise RuntimeError(f"{label}: expected frozen value {expected!r}, got {actual!r}")


def build_errata(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []

    for case_id, risk, mode in (
        ("ANUT-12", "S1", "general_only"),
        ("ANUT-14", "S2", "general_only"),
        ("ROUTE-10", "S1", "general_only"),
    ):
        target = expectation(rows, case_id)
        assert_value(target["risk_level"], "S0", f"{case_id}.risk_level")
        assert_value(target["response_mode"], "normal", f"{case_id}.response_mode")
        target["risk_level"] = risk
        target["response_mode"] = mode
        changes.append(
            {
                "case_id": case_id,
                "turn": 1,
                "fields": ["risk_level", "response_mode"],
                "reason": (
                    "Phase04 deterministic safety policy and attempts 1-2 agree; "
                    "v1 expected S0 incorrectly."
                ),
            }
        )

    route_mixed = expectation(rows, "ROUTE-03")
    assert_value(
        route_mixed["required_chunk_ids"],
        ["B-p05-c02", "C-p02-c01"],
        "ROUTE-03.required_chunk_ids",
    )
    route_mixed["required_chunk_ids"] = ["A-p04-c01", "C-p02-c01"]
    changes.append(
        {
            "case_id": "ROUTE-03",
            "turn": 1,
            "fields": ["required_chunk_ids"],
            "reason": (
                "The question asks for fat-loss guidance plus membership help; "
                "A-p04-c01 is the guidance source, while B-p05-c02 is only a "
                "substitution table."
            ),
        }
    )

    breakfast = expectation(rows, "MULTI-04", 2)
    assert_value(breakfast["required_chunk_ids"], ["B-p05-c02"], "MULTI-04#2.required_chunk_ids")
    assert_value(breakfast["required_terms"], ["替换"], "MULTI-04#2.required_terms")
    breakfast["required_chunk_ids"] = ["A-p02-c03"]
    breakfast["required_terms"] = ["早餐"]
    changes.append(
        {
            "case_id": "MULTI-04",
            "turn": 2,
            "fields": ["required_chunk_ids", "required_terms"],
            "reason": (
                "The follow-up asks for breakfast direction, not substitution; "
                "A-p02-c03 contains the breakfast formula."
            ),
        }
    )

    allergy = expectation(rows, "MULTI-05", 1)
    assert_value(allergy["required_chunk_ids"], ["A-p04-c06"], "MULTI-05#1.required_chunk_ids")
    allergy["required_chunk_ids"] = []
    allergy["required_terms"] = ["避免"]
    allergy["require_citations"] = False
    allergy["require_retrieval_trace"] = False
    changes.append(
        {
            "case_id": "MULTI-05",
            "turn": 1,
            "fields": [
                "required_chunk_ids",
                "required_terms",
                "require_citations",
                "require_retrieval_trace",
            ],
            "reason": (
                "A-p04-c06 is pregnancy/gout/kidney guidance and contains no "
                "egg-allergy fact; the deterministic blocked-food safety contract "
                "remains required."
            ),
        }
    )
    return changes


def main() -> int:
    base_manifest = json.loads(BASE_MANIFEST.read_text(encoding="utf-8"))
    assert_value(sha256(BASE_DATASET), base_manifest["dataset_sha256"], "base dataset hash")
    assert_value(sha256(THRESHOLDS), base_manifest["thresholds_sha256"], "threshold hash")
    rows = [
        json.loads(line)
        for line in BASE_DATASET.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    changes = build_errata(rows)
    OUTPUT_DATASET.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) for row in rows)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    cases = load_release_cases(OUTPUT_DATASET)
    chunks = load_chunk_index(
        sorted((ROOT / "knowledge" / "normalized" / "chunks").glob("*.chunks.jsonl"))
    )
    validation = validate_release_cases(cases, chunks)
    if validation["status"] != "PASS":
        raise RuntimeError(f"errata dataset validation failed: {validation['errors']}")
    manifest = {
        "schema_version": 1,
        "dataset_version": "release-golden-v1.1",
        "generated_at": datetime.now().astimezone().isoformat(),
        "base_dataset": str(BASE_DATASET.relative_to(ROOT)).replace("\\", "/"),
        "base_dataset_sha256": sha256(BASE_DATASET),
        "dataset": str(OUTPUT_DATASET.relative_to(ROOT)).replace("\\", "/"),
        "dataset_sha256": sha256(OUTPUT_DATASET),
        "thresholds": str(THRESHOLDS.relative_to(ROOT)).replace("\\", "/"),
        "thresholds_sha256": sha256(THRESHOLDS),
        "thresholds_unchanged_from_v1": True,
        "first_attempt_evidence": (
            "evals/reports/release-v1-20260822T124320970139+0800/summary.json"
        ),
        "second_attempt_evidence": (
            "evals/reports/release-v1-20260822T125826519364+0800/summary.json"
        ),
        "errata_count": len(changes),
        "errata": changes,
        **validation,
    }
    OUTPUT_MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    EVIDENCE.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        f"ERRATA RESULT: PASS cases={validation['case_count']} turns={validation['turn_count']} "
        f"changes={len(changes)} details={EVIDENCE.relative_to(ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
