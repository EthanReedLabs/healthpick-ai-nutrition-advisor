"""Prove that source-level missing glyphs remain excluded from runtime retrieval."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from healthpick_api.retrieval import KnowledgeIndex  # noqa: E402

OUTPUT = ROOT / "docs" / "evidence" / "action-07-unknown-glyph-exclusion.json"


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def main() -> None:
    source_chunks = [
        record
        for code in ("A", "B", "C")
        for record in load_jsonl(
            ROOT / "knowledge" / "normalized" / "chunks" / f"{code}.chunks.jsonl"
        )
    ]
    ambiguous_chunk_ids = sorted(
        record["chunk_id"] for record in source_chunks if record.get("unknown_glyph_count", 0) > 0
    )
    index = KnowledgeIndex.load_default(ROOT)
    loaded_ids = {chunk.chunk_id for chunk in index.chunks}

    curated_plans = yaml.safe_load(
        (ROOT / "knowledge" / "normalized" / "curated" / "plans.yaml").read_text(encoding="utf-8")
    )
    ambiguous_rules = [item for item in curated_plans["items"] if item.get("unknown_glyph") is True]
    generated_rules = load_jsonl(ROOT / "knowledge" / "normalized" / "facts" / "plan_rules.jsonl")
    generated_ambiguous = [item for item in generated_rules if item.get("unknown_glyph")]

    checks = {
        "source_ambiguous_chunks_are_exactly_8": len(ambiguous_chunk_ids) == 8,
        "loader_reports_all_exclusions": sorted(index.excluded_unknown_glyph_ids)
        == ambiguous_chunk_ids,
        "no_ambiguous_chunk_is_loaded": not (loaded_ids & set(ambiguous_chunk_ids)),
        "curated_ambiguous_rules_are_exactly_6": len(ambiguous_rules) == 6,
        "generated_ambiguous_rules_are_exactly_6": len(generated_ambiguous) == 6,
        "all_ambiguous_rules_remain_review_required": all(
            item["review_status"] == "review_required" for item in generated_ambiguous
        ),
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    evidence = {
        "schema_version": 1,
        "evidence_id": "ACTION-07-UNKNOWN-GLYPH-EXCLUSION",
        "action_id": "ACTION-07",
        "scope": "knowledge/runtime-retrieval/structured-rules",
        "captured_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "resolution": "maintain_exclusion_until_corrected_source_is_available",
        "source_chunk_count": len(source_chunks),
        "runtime_loaded_chunk_count": len(index.chunks),
        "excluded_unknown_glyph_chunk_ids": ambiguous_chunk_ids,
        "excluded_unknown_glyph_rule_ids": sorted(item["rule_id"] for item in generated_ambiguous),
        "checks": checks,
        "status": status,
    }
    OUTPUT.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    if status != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
