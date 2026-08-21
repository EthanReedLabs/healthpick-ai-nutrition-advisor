from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import yaml
import pytest

from scripts.build_structured_facts import review_info


ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / "knowledge"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def all_pages() -> list[dict]:
    records: list[dict] = []
    for path in sorted((KNOWLEDGE / "normalized" / "pages").glob("*.jsonl")):
        records.extend(read_jsonl(path))
    return records


def all_chunks() -> list[dict]:
    records: list[dict] = []
    for path in sorted((KNOWLEDGE / "normalized" / "chunks").glob("*.jsonl")):
        records.extend(read_jsonl(path))
    return records


def test_source_files_match_manifest_hashes() -> None:
    manifest = yaml.safe_load(
        (KNOWLEDGE / "manifests" / "sources.yaml").read_text(encoding="utf-8")
    )
    for source in manifest["sources"]:
        digest = hashlib.sha256((ROOT / source["file"]).read_bytes()).hexdigest().upper()
        assert digest == source["sha256"]


def test_page_counts_and_ids() -> None:
    pages = all_pages()
    assert Counter(page["source_code"] for page in pages) == {"A": 5, "B": 8, "C": 5}
    ids = [page["page_id"] for page in pages]
    assert len(ids) == len(set(ids)) == 18


def test_chunks_are_unique_and_page_bounded() -> None:
    pages = {page["page_id"]: page for page in all_pages()}
    chunks = all_chunks()
    ids = [chunk["chunk_id"] for chunk in chunks]
    assert len(ids) == len(set(ids))
    assert len(chunks) == 67
    for chunk in chunks:
        page = pages[chunk["page_id"]]
        assert chunk["source_code"] == page["source_code"]
        assert chunk["page"] == page["page"]


def test_platform_chunks_are_hard_isolated() -> None:
    c_chunks = [chunk for chunk in all_chunks() if chunk["source_code"] == "C"]
    assert c_chunks
    for chunk in c_chunks:
        assert chunk["source_role"] == "auxiliary_platform"
        assert chunk["allowed_routes"] == ["platform"]
        assert {"nutrition", "recommendation", "contraindication"}.issubset(
            chunk["forbidden_routes"]
        )


def test_nutrition_facts_never_use_source_c() -> None:
    facts_dir = KNOWLEDGE / "normalized" / "facts"
    nutrition_records = read_jsonl(facts_dir / "food_facts.jsonl") + read_jsonl(
        facts_dir / "plan_rules.jsonl"
    )
    assert nutrition_records
    assert all(record["source_code"] in {"A", "B"} for record in nutrition_records)
    assert all(record["source_role"] == "core_nutrition" for record in nutrition_records)


def test_platform_facts_are_platform_only() -> None:
    facts = read_jsonl(
        KNOWLEDGE / "normalized" / "facts" / "platform_facts.jsonl"
    )
    assert len(facts) == 12
    assert all(fact["source_code"] == "C" for fact in facts)
    assert all(fact["allowed_routes"] == ["platform"] for fact in facts)


def test_unknown_glyph_rules_cannot_be_verified() -> None:
    rules = read_jsonl(KNOWLEDGE / "normalized" / "facts" / "plan_rules.jsonl")
    ambiguous = [rule for rule in rules if rule.get("unknown_glyph")]
    assert ambiguous
    assert all(rule["review_status"] != "verified" for rule in ambiguous)


def test_review_evidence_images_exist() -> None:
    facts_dir = KNOWLEDGE / "normalized" / "facts"
    records = (
        read_jsonl(facts_dir / "food_facts.jsonl")
        + read_jsonl(facts_dir / "plan_rules.jsonl")
        + read_jsonl(facts_dir / "platform_facts.jsonl")
    )
    for record in records:
        assert record["first_pass_review"]["second_person_review_required"] is True
        for path in record["first_pass_review"]["evidence_images"]:
            assert (ROOT / path).is_file()


def test_verified_record_requires_second_person_review() -> None:
    dataset = {
        "review_status": "review_required",
        "first_pass_reviewer": "Codex",
        "first_pass_date": "2026-08-21",
    }
    with pytest.raises(ValueError, match="verified requires second_person_review"):
        review_info(dataset, "A", [3], {"id": "sample", "review_status": "verified"})


def test_completed_second_person_review_closes_review_gate() -> None:
    dataset = {
        "review_status": "review_required",
        "first_pass_reviewer": "Codex",
        "first_pass_date": "2026-08-21",
    }
    review = review_info(
        dataset,
        "A",
        [3],
        {
            "id": "sample",
            "review_status": "verified",
            "second_person_review": {
                "reviewer": "participant",
                "date": "2026-08-21",
                "notes": "checked against A-p03",
            },
        },
    )
    assert review["review_status"] == "verified"
    assert review["first_pass_review"]["second_person_review_required"] is False
    assert review["second_person_review"]["reviewer"] == "participant"


def test_migration_defers_vector_dimensions() -> None:
    migration = (ROOT / "infra" / "migrations" / "001_knowledge_base.sql").read_text(
        encoding="utf-8"
    )
    assert migration.count("CREATE TABLE ") == 7
    assert "CREATE EXTENSION IF NOT EXISTS pgcrypto" in migration
    assert "CREATE EXTENSION vector" not in migration
