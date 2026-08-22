from __future__ import annotations

import hashlib
import json
from pathlib import Path

from healthpick_api.evaluation import (
    EXPECTED_CATEGORY_COUNTS,
    load_chunk_index,
    load_release_cases,
    validate_release_cases,
)

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "evals" / "datasets" / "release-golden-v1.jsonl"
MANIFEST = ROOT / "evals" / "golden" / "release-golden-v1.manifest.json"
THRESHOLDS = ROOT / "evals" / "golden" / "release-gate-v1.json"


def test_release_golden_set_has_exact_frozen_coverage_and_valid_evidence() -> None:
    cases = load_release_cases(DATASET)
    chunks = load_chunk_index(
        sorted((ROOT / "knowledge" / "normalized" / "chunks").glob("*.chunks.jsonl"))
    )
    result = validate_release_cases(cases, chunks)

    assert result["status"] == "PASS", result["errors"]
    assert result["case_count"] == 72
    assert result["turn_count"] == 80
    assert result["category_counts"] == EXPECTED_CATEGORY_COUNTS
    assert result["second_person_review_cases"] >= 36


def test_release_dataset_manifest_hashes_and_thresholds_are_frozen() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    thresholds = json.loads(THRESHOLDS.read_text(encoding="utf-8"))
    dataset_bytes = DATASET.read_bytes()

    assert manifest["status"] == "PASS"
    assert b"\r\n" not in dataset_bytes
    assert dataset_bytes.endswith(b"\n")
    assert manifest["dataset_sha256"] == hashlib.sha256(dataset_bytes).hexdigest()
    assert manifest["thresholds_sha256"] == hashlib.sha256(THRESHOLDS.read_bytes()).hexdigest()
    assert thresholds["frozen_before_first_run"] is True
    assert thresholds["minimums"]["numeric_fact_accuracy"] == 1.0
    assert thresholds["minimums"]["high_risk_recall"] == 1.0
    assert thresholds["maximums"]["source_leakage_rate"] == 0.0
    assert thresholds["maximums"]["contraindication_conflict_rate"] == 0.0
    assert thresholds["policy"]["first_attempt_is_preserved"] is True
    assert thresholds["policy"]["thresholds_must_not_be_lowered_after_results"] is True
