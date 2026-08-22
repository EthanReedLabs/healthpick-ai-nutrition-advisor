from __future__ import annotations

import hashlib
import json
from pathlib import Path

from healthpick_api.evaluation import load_chunk_index, load_release_cases, validate_release_cases

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "evals" / "datasets" / "release-golden-v1.jsonl"
ERRATA = ROOT / "evals" / "datasets" / "release-golden-v1.1.jsonl"
BASE_MANIFEST = ROOT / "evals" / "golden" / "release-golden-v1.manifest.json"
ERRATA_MANIFEST = ROOT / "evals" / "golden" / "release-golden-v1.1.manifest.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_errata_preserves_v1_and_thresholds_and_validates() -> None:
    base_manifest = json.loads(BASE_MANIFEST.read_text(encoding="utf-8"))
    errata_manifest = json.loads(ERRATA_MANIFEST.read_text(encoding="utf-8"))
    assert b"\r\n" not in BASE.read_bytes()
    assert b"\r\n" not in ERRATA.read_bytes()
    assert BASE.read_bytes().endswith(b"\n")
    assert ERRATA.read_bytes().endswith(b"\n")
    assert digest(BASE) == base_manifest["dataset_sha256"]
    assert errata_manifest["base_dataset_sha256"] == base_manifest["dataset_sha256"]
    assert errata_manifest["thresholds_sha256"] == base_manifest["thresholds_sha256"]
    assert errata_manifest["thresholds_unchanged_from_v1"] is True
    assert errata_manifest["errata_count"] == 6

    cases = load_release_cases(ERRATA)
    chunks = load_chunk_index(
        sorted((ROOT / "knowledge" / "normalized" / "chunks").glob("*.chunks.jsonl"))
    )
    validation = validate_release_cases(cases, chunks)
    assert validation["status"] == "PASS"
    assert validation["case_count"] == 72
    assert validation["turn_count"] == 80


def test_errata_fixes_only_the_documented_case_turns() -> None:
    base = {case.case_id: case for case in load_release_cases(BASE)}
    errata = {case.case_id: case for case in load_release_cases(ERRATA)}
    changed: set[tuple[str, int]] = set()
    for case_id, base_case in base.items():
        for index, base_turn in enumerate(base_case.turns, 1):
            if base_turn.expected != errata[case_id].turns[index - 1].expected:
                changed.add((case_id, index))
    assert changed == {
        ("ANUT-12", 1),
        ("ANUT-14", 1),
        ("ROUTE-03", 1),
        ("ROUTE-10", 1),
        ("MULTI-04", 2),
        ("MULTI-05", 1),
    }
