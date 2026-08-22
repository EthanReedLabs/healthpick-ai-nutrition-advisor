"""Validate knowledge artifacts, source isolation, and review readiness."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / "knowledge"
EVIDENCE = ROOT / "docs" / "evidence"
MANIFEST = KNOWLEDGE / "manifests" / "sources.yaml"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: {exc}") from exc
    return records


def sha256(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest.upper()


def load_json_if_present(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def validate_schema(
    records: list[dict[str, Any]], schema_path: Path, label: str, errors: list[str]
) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    for index, record in enumerate(records, start=1):
        for error in validator.iter_errors(record):
            location = ".".join(str(part) for part in error.absolute_path)
            errors.append(f"{label}[{index}] {location}: {error.message}")


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    sources = {source["code"]: source for source in manifest["sources"]}

    for code, source in sources.items():
        actual = sha256(ROOT / source["file"])
        require(actual == str(source["sha256"]).upper(), f"{code}: hash mismatch", errors)

    pages: list[dict[str, Any]] = []
    for path in sorted((KNOWLEDGE / "normalized" / "pages").glob("*.pages.jsonl")):
        pages.extend(load_jsonl(path))
    chunks: list[dict[str, Any]] = []
    for path in sorted((KNOWLEDGE / "normalized" / "chunks").glob("*.chunks.jsonl")):
        chunks.extend(load_jsonl(path))
    food_facts = load_jsonl(KNOWLEDGE / "normalized" / "facts" / "food_facts.jsonl")
    plan_rules = load_jsonl(KNOWLEDGE / "normalized" / "facts" / "plan_rules.jsonl")
    platform_facts = load_jsonl(KNOWLEDGE / "normalized" / "facts" / "platform_facts.jsonl")

    validate_schema(pages, KNOWLEDGE / "schemas" / "page.schema.json", "page", errors)
    validate_schema(chunks, KNOWLEDGE / "schemas" / "chunk.schema.json", "chunk", errors)
    validate_schema(food_facts, KNOWLEDGE / "schemas" / "food-fact.schema.json", "food", errors)
    validate_schema(plan_rules, KNOWLEDGE / "schemas" / "plan-rule.schema.json", "plan", errors)
    validate_schema(
        platform_facts,
        KNOWLEDGE / "schemas" / "platform-fact.schema.json",
        "platform",
        errors,
    )

    expected_pages = {code: int(source["pages"]) for code, source in sources.items()}
    actual_pages = Counter(page["source_code"] for page in pages)
    require(len(pages) == 18, f"expected 18 pages, found {len(pages)}", errors)
    require(dict(actual_pages) == expected_pages, f"page counts: {actual_pages}", errors)

    page_ids = [page["page_id"] for page in pages]
    require(len(page_ids) == len(set(page_ids)), "duplicate page_id", errors)
    pages_by_id = {page["page_id"]: page for page in pages}
    for page in pages:
        source = sources[page["source_code"]]
        require(page["page"] <= source["pages"], f"{page['page_id']}: page out of range", errors)
        require(
            page["source_role"] == source["source_role"],
            f"{page['page_id']}: role mismatch",
            errors,
        )
        require(
            page["source_sha256"] == str(source["sha256"]).upper(),
            f"{page['page_id']}: hash mismatch",
            errors,
        )
        require(bool(page["normalized_text"].strip()), f"{page['page_id']}: empty text", errors)

    chunk_ids = [chunk["chunk_id"] for chunk in chunks]
    require(len(chunk_ids) == len(set(chunk_ids)), "duplicate chunk_id", errors)
    for chunk in chunks:
        page = pages_by_id.get(chunk["page_id"])
        require(page is not None, f"{chunk['chunk_id']}: unknown page_id", errors)
        if page:
            require(
                chunk["source_code"] == page["source_code"],
                f"{chunk['chunk_id']}: source mismatch",
                errors,
            )
            require(
                chunk["page"] == page["page"], f"{chunk['chunk_id']}: cross-page mismatch", errors
            )
            require(
                chunk["source_role"] == page["source_role"],
                f"{chunk['chunk_id']}: role mismatch",
                errors,
            )
        if chunk["source_code"] == "C":
            require(
                chunk["allowed_routes"] == ["platform"],
                f"{chunk['chunk_id']}: C route leak",
                errors,
            )
            require(
                all(
                    route in chunk["forbidden_routes"]
                    for route in ("nutrition", "recommendation", "contraindication")
                ),
                f"{chunk['chunk_id']}: C forbidden route missing",
                errors,
            )
        else:
            require(
                "platform" not in chunk["allowed_routes"],
                f"{chunk['chunk_id']}: A/B platform leak",
                errors,
            )
        if chunk.get("unknown_glyph_count", 0) > 0:
            require(
                chunk["review_status"] != "verified",
                f"{chunk['chunk_id']}: unknown glyph marked verified",
                errors,
            )

    require(len(food_facts) == 31, f"expected 31 food facts, found {len(food_facts)}", errors)
    require(len(plan_rules) == 37, f"expected 37 plan rules, found {len(plan_rules)}", errors)
    require(
        len(platform_facts) == 12,
        f"expected 12 platform facts, found {len(platform_facts)}",
        errors,
    )

    all_fact_ids = [record["fact_id"] for record in food_facts + platform_facts]
    rule_ids = [record["rule_id"] for record in plan_rules]
    require(len(all_fact_ids) == len(set(all_fact_ids)), "duplicate fact_id", errors)
    require(len(rule_ids) == len(set(rule_ids)), "duplicate rule_id", errors)

    for fact in food_facts:
        require(
            fact["source_code"] == "A" and fact["source_role"] == "core_nutrition",
            f"{fact['fact_id']}: invalid food source",
            errors,
        )
        require(
            "platform" not in fact["allowed_routes"], f"{fact['fact_id']}: platform allowed", errors
        )
    for rule in plan_rules:
        require(
            rule["source_code"] in {"A", "B"} and rule["source_role"] == "core_nutrition",
            f"{rule['rule_id']}: invalid plan source",
            errors,
        )
        if rule.get("unknown_glyph"):
            require(
                rule["review_status"] != "verified",
                f"{rule['rule_id']}: ambiguous rule verified",
                errors,
            )
    for fact in platform_facts:
        require(
            fact["source_code"] == "C" and fact["source_role"] == "auxiliary_platform",
            f"{fact['fact_id']}: invalid platform source",
            errors,
        )
        require(
            fact["allowed_routes"] == ["platform"],
            f"{fact['fact_id']}: platform route invalid",
            errors,
        )

    for record in food_facts + plan_rules + platform_facts:
        record_id = record.get("fact_id", record.get("rule_id"))
        if record["review_status"] == "verified":
            second_review = record.get("second_person_review")
            require(
                isinstance(second_review, dict),
                f"{record_id}: verified without second-person review",
                errors,
            )
            if isinstance(second_review, dict):
                require(
                    all(second_review.get(field) for field in ("reviewer", "date", "notes")),
                    f"{record_id}: incomplete second-person review",
                    errors,
                )
            require(
                record["first_pass_review"].get("second_person_review_required") is False,
                f"{record_id}: verified but review flag remains open",
                errors,
            )
        else:
            require(
                record["first_pass_review"].get("second_person_review_required") is True,
                f"{record_id}: unverified record closed review flag",
                errors,
            )
        for evidence_path in record["first_pass_review"]["evidence_images"]:
            require(
                (ROOT / evidence_path).is_file(),
                f"missing review evidence: {evidence_path}",
                errors,
            )

    migration = (ROOT / "infra" / "migrations" / "001_knowledge_base.sql").read_text(
        encoding="utf-8"
    )
    require(migration.lstrip().startswith("BEGIN;"), "migration does not start with BEGIN", errors)
    require(migration.rstrip().endswith("COMMIT;"), "migration does not end with COMMIT", errors)
    require(
        migration.count("CREATE TABLE ") == 7, "migration must create 7 knowledge tables", errors
    )
    require(
        re.search(r"\bvector\s*\(\s*\d+", migration, flags=re.IGNORECASE) is None,
        "vector dimensions were guessed in migration 001",
        errors,
    )

    unknown_pages = sum(page["quality"].get("unknown_glyph_count", 0) > 0 for page in pages)
    unknown_chunks = sum(chunk.get("unknown_glyph_count", 0) > 0 for chunk in chunks)
    review_required = sum(
        record["review_status"] == "review_required"
        for record in food_facts + plan_rules + platform_facts
    )
    database_evidence = load_json_if_present(EVIDENCE / "action-01-database-runtime.json")
    model_evidence = load_json_if_present(EVIDENCE / "action-02-03-real-model-runtime.json")
    glyph_evidence = load_json_if_present(EVIDENCE / "action-07-unknown-glyph-exclusion.json")
    database_gate = (
        database_evidence.get("status") == "PASS"
        and database_evidence.get("vector_version")
        and database_evidence.get("embedding_column_type") == "vector(1024)"
        and database_evidence.get("embedding_index_present") is True
    )
    embedding_config = manifest.get("embedding", {})
    embedding_probe = model_evidence.get("embedding", {})
    embedding_gate = (
        model_evidence.get("status") == "PASS"
        and embedding_probe.get("status") == "PASS"
        and embedding_probe.get("model") == embedding_config.get("model")
        and embedding_probe.get("digest") == embedding_config.get("digest")
        and embedding_probe.get("dimensions") == embedding_config.get("dimensions")
        and database_gate
    )
    unknown_glyph_gate = glyph_evidence.get("status") == "PASS"
    warnings.extend(
        [
            (
                f"{unknown_pages} pages / {unknown_chunks} chunks contain source-level "
                "unknown glyphs; affected rules remain review_required."
            ),
            (
                f"{review_required} structured records require participant second-person "
                "review before production import."
            ),
            "Unknown-glyph runtime exclusion: "
            + ("PASS." if unknown_glyph_gate else "NOT_RUN (ACTION-07)."),
            "Database migration execution: "
            + ("PASS." if database_gate else "NOT_RUN (ACTION-01)."),
            "Embedding/vector build: " + ("PASS." if embedding_gate else "NOT_RUN (ACTION-03)."),
        ]
    )

    counts = {
        "pages": len(pages),
        "chunks": len(chunks),
        "food_facts": len(food_facts),
        "plan_rules": len(plan_rules),
        "platform_facts": len(platform_facts),
        "unknown_glyph_pages": unknown_pages,
        "unknown_glyph_chunks": unknown_chunks,
        "review_required_records": review_required,
    }
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "status": "PASS" if not errors else "FAIL",
        "counts": counts,
        "errors": errors,
        "warnings": warnings,
        "runtime_gates": {
            "file_validation": "PASS" if not errors else "FAIL",
            "database_migration": "PASS" if database_gate else "NOT_RUN",
            "embedding_index": "PASS" if embedding_gate else "NOT_RUN",
            "unknown_glyph_exclusion": "PASS" if unknown_glyph_gate else "NOT_RUN",
            "second_person_review": "REQUIRED",
        },
    }
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    json_path = EVIDENCE / "phase-02-knowledge-validation.json"
    md_path = EVIDENCE / "phase-02-knowledge-validation.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_lines = [
        "# Phase 02 Knowledge Validation",
        "",
        f"- Status: `{report['status']}`",
        f"- Generated: `{report['generated_at']}`",
        "",
        "## Counts",
        "",
        *[f"- {key}: {value}" for key, value in counts.items()],
        "",
        "## Runtime gates",
        "",
        *[f"- {key}: `{value}`" for key, value in report["runtime_gates"].items()],
        "",
        "## Errors",
        "",
        *(errors or ["- None"]),
        "",
        "## Warnings",
        "",
        *[f"- {warning}" for warning in warnings],
        "",
    ]
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
