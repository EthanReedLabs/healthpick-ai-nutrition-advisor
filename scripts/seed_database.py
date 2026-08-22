"""Idempotently seed validated A/B/C knowledge artifacts into PostgreSQL."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml
from psycopg import connect
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / "knowledge"
MANIFEST_PATH = KNOWLEDGE / "manifests" / "sources.yaml"
DEFAULT_DATABASE_URL = "postgresql://healthpick:healthpick-local-only@127.0.0.1:54329/healthpick"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def json_safe(value: object) -> object:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def load_seed_payload() -> dict[str, Any]:
    manifest_raw = MANIFEST_PATH.read_text(encoding="utf-8")
    manifest = yaml.safe_load(manifest_raw)
    sources = manifest["sources"]
    pages = [
        record
        for path in sorted((KNOWLEDGE / "normalized" / "pages").glob("*.pages.jsonl"))
        for record in load_jsonl(path)
    ]
    chunks = [
        record
        for path in sorted((KNOWLEDGE / "normalized" / "chunks").glob("*.chunks.jsonl"))
        for record in load_jsonl(path)
    ]
    food_facts = load_jsonl(KNOWLEDGE / "normalized" / "facts" / "food_facts.jsonl")
    plan_rules = load_jsonl(KNOWLEDGE / "normalized" / "facts" / "plan_rules.jsonl")
    platform_facts = load_jsonl(KNOWLEDGE / "normalized" / "facts" / "platform_facts.jsonl")
    payload = {
        "manifest": json_safe(manifest),
        "manifest_sha256": hashlib.sha256(manifest_raw.encode("utf-8")).hexdigest().upper(),
        "sources": sources,
        "pages": pages,
        "chunks": chunks,
        "food_facts": food_facts,
        "plan_rules": plan_rules,
        "platform_facts": platform_facts,
    }
    validate_seed_payload(payload)
    return payload


def validate_seed_payload(payload: dict[str, Any]) -> None:
    sources = {item["code"]: item for item in payload["sources"]}
    if set(sources) != {"A", "B", "C"}:
        raise ValueError("seed manifest must contain exactly sources A, B, and C")
    for collection in ("pages", "chunks", "food_facts", "plan_rules", "platform_facts"):
        for record in payload[collection]:
            source = sources.get(record["source_code"])
            if source is None or record["source_sha256"] != source["sha256"]:
                raise ValueError(f"{collection}: source identity mismatch")
    for chunk in payload["chunks"]:
        routes = chunk["allowed_routes"]
        if chunk["source_code"] == "C":
            if routes != ["platform"] or "nutrition" not in chunk["forbidden_routes"]:
                raise ValueError("source C chunk crossed the platform-only boundary")
        elif "platform" in routes:
            raise ValueError("source A/B chunk crossed into the platform route")
    for fact in payload["platform_facts"]:
        if fact["source_code"] != "C" or fact["allowed_routes"] != ["platform"]:
            raise ValueError("platform fact is not C-only")


def _prune(connection, table: str, id_column: str, ids: list[str]) -> None:  # type: ignore[no-untyped-def]
    if not ids:
        raise ValueError(f"refusing to prune {table} from an empty seed collection")
    connection.execute(
        f"DELETE FROM {table} WHERE NOT ({id_column} = ANY(%s))",  # noqa: S608
        (ids,),
    )


def seed_database(database_url: str) -> dict[str, Any]:
    payload = load_seed_payload()
    expected = {
        "knowledge_documents": len(payload["sources"]),
        "knowledge_pages": len(payload["pages"]),
        "knowledge_chunks": len(payload["chunks"]),
        "food_facts": len(payload["food_facts"]),
        "plan_rules": len(payload["plan_rules"]),
        "platform_facts": len(payload["platform_facts"]),
    }
    with connect(database_url, autocommit=True, row_factory=dict_row) as connection:
        run = connection.execute(
            """
            INSERT INTO knowledge_ingestion_runs(status, source_manifest_sha256, extractor)
            VALUES ('running', %s, %s) RETURNING id
            """,
            (
                payload["manifest_sha256"],
                Jsonb({"name": "seed_database.py", "schema_version": 1}),
            ),
        ).fetchone()
        run_id = run["id"]
        try:
            with connection.transaction():
                for source in payload["sources"]:
                    connection.execute(
                        """
                        INSERT INTO knowledge_documents
                            (id, title, version, source_role, sha256, page_count, manifest)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            title = EXCLUDED.title,
                            version = EXCLUDED.version,
                            source_role = EXCLUDED.source_role,
                            sha256 = EXCLUDED.sha256,
                            page_count = EXCLUDED.page_count,
                            manifest = EXCLUDED.manifest
                        """,
                        (
                            source["code"],
                            source["title"],
                            source["version"],
                            source["source_role"],
                            source["sha256"],
                            source["pages"],
                            Jsonb(json_safe(source)),
                        ),
                    )
                for page in payload["pages"]:
                    connection.execute(
                        """
                        INSERT INTO knowledge_pages
                            (id, document_id, page_number, raw_text, normalized_text,
                             blocks, quality, review_status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            document_id = EXCLUDED.document_id,
                            page_number = EXCLUDED.page_number,
                            raw_text = EXCLUDED.raw_text,
                            normalized_text = EXCLUDED.normalized_text,
                            blocks = EXCLUDED.blocks,
                            quality = EXCLUDED.quality,
                            review_status = EXCLUDED.review_status
                        """,
                        (
                            page["page_id"],
                            page["source_code"],
                            page["page"],
                            page["raw_text"],
                            page["normalized_text"],
                            Jsonb(page["blocks"]),
                            Jsonb(page["quality"]),
                            page["review_status"],
                        ),
                    )
                for chunk in payload["chunks"]:
                    connection.execute(
                        """
                        INSERT INTO knowledge_chunks
                            (id, page_id, document_id, source_role, page_number, section,
                             content, allowed_routes, forbidden_routes, contains_table,
                             unknown_glyph_count, review_status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            page_id = EXCLUDED.page_id,
                            document_id = EXCLUDED.document_id,
                            source_role = EXCLUDED.source_role,
                            page_number = EXCLUDED.page_number,
                            section = EXCLUDED.section,
                            embedding = CASE
                                WHEN knowledge_chunks.content IS DISTINCT FROM EXCLUDED.content
                                THEN NULL ELSE knowledge_chunks.embedding END,
                            embedding_model = CASE
                                WHEN knowledge_chunks.content IS DISTINCT FROM EXCLUDED.content
                                THEN NULL ELSE knowledge_chunks.embedding_model END,
                            embedding_created_at = CASE
                                WHEN knowledge_chunks.content IS DISTINCT FROM EXCLUDED.content
                                THEN NULL ELSE knowledge_chunks.embedding_created_at END,
                            content = EXCLUDED.content,
                            allowed_routes = EXCLUDED.allowed_routes,
                            forbidden_routes = EXCLUDED.forbidden_routes,
                            contains_table = EXCLUDED.contains_table,
                            unknown_glyph_count = EXCLUDED.unknown_glyph_count,
                            review_status = EXCLUDED.review_status
                        """,
                        (
                            chunk["chunk_id"],
                            chunk["page_id"],
                            chunk["source_code"],
                            chunk["source_role"],
                            chunk["page"],
                            chunk["section"],
                            chunk["content"],
                            chunk["allowed_routes"],
                            chunk["forbidden_routes"],
                            chunk["contains_table"],
                            chunk["unknown_glyph_count"],
                            chunk["review_status"],
                        ),
                    )
                for fact in payload["food_facts"]:
                    attributes = {
                        "recommended_for": fact.get("recommended_for", []),
                        "allowed_routes": fact["allowed_routes"],
                        "forbidden_routes": fact["forbidden_routes"],
                        "first_pass_review": fact.get("first_pass_review"),
                    }
                    connection.execute(
                        """
                        INSERT INTO food_facts
                            (id, document_id, page_number, section, food_name, category,
                             basis, nutrients, attributes, review_status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            document_id = EXCLUDED.document_id,
                            page_number = EXCLUDED.page_number,
                            section = EXCLUDED.section,
                            food_name = EXCLUDED.food_name,
                            category = EXCLUDED.category,
                            basis = EXCLUDED.basis,
                            nutrients = EXCLUDED.nutrients,
                            attributes = EXCLUDED.attributes,
                            review_status = EXCLUDED.review_status
                        """,
                        (
                            fact["fact_id"],
                            fact["source_code"],
                            fact["page"],
                            fact["section"],
                            fact["food_name"],
                            fact["category"],
                            Jsonb(fact["basis"]),
                            Jsonb(fact["nutrients"]),
                            Jsonb(attributes),
                            fact["review_status"],
                        ),
                    )
                for rule in payload["plan_rules"]:
                    connection.execute(
                        """
                        INSERT INTO plan_rules
                            (id, document_id, page_numbers, section, rule_type, title,
                             content, unknown_glyph, review_status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            document_id = EXCLUDED.document_id,
                            page_numbers = EXCLUDED.page_numbers,
                            section = EXCLUDED.section,
                            rule_type = EXCLUDED.rule_type,
                            title = EXCLUDED.title,
                            content = EXCLUDED.content,
                            unknown_glyph = EXCLUDED.unknown_glyph,
                            review_status = EXCLUDED.review_status
                        """,
                        (
                            rule["rule_id"],
                            rule["source_code"],
                            rule["pages"],
                            rule["section"],
                            rule["rule_type"],
                            rule["title"],
                            Jsonb(rule["content"]),
                            bool(rule.get("unknown_glyph")),
                            rule["review_status"],
                        ),
                    )
                for fact in payload["platform_facts"]:
                    connection.execute(
                        """
                        INSERT INTO platform_facts
                            (id, document_id, page_numbers, section, fact_type, title,
                             value, claim_scope, allowed_routes, forbidden_routes, review_status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            document_id = EXCLUDED.document_id,
                            page_numbers = EXCLUDED.page_numbers,
                            section = EXCLUDED.section,
                            fact_type = EXCLUDED.fact_type,
                            title = EXCLUDED.title,
                            value = EXCLUDED.value,
                            claim_scope = EXCLUDED.claim_scope,
                            allowed_routes = EXCLUDED.allowed_routes,
                            forbidden_routes = EXCLUDED.forbidden_routes,
                            review_status = EXCLUDED.review_status
                        """,
                        (
                            fact["fact_id"],
                            fact["source_code"],
                            fact["pages"],
                            fact["section"],
                            fact["fact_type"],
                            fact["title"],
                            Jsonb(fact["value"]),
                            fact["claim_scope"],
                            fact["allowed_routes"],
                            fact["forbidden_routes"],
                            fact["review_status"],
                        ),
                    )

                _prune(
                    connection, "food_facts", "id", [x["fact_id"] for x in payload["food_facts"]]
                )
                _prune(
                    connection, "plan_rules", "id", [x["rule_id"] for x in payload["plan_rules"]]
                )
                _prune(
                    connection,
                    "platform_facts",
                    "id",
                    [x["fact_id"] for x in payload["platform_facts"]],
                )
                _prune(
                    connection, "knowledge_chunks", "id", [x["chunk_id"] for x in payload["chunks"]]
                )
                _prune(
                    connection, "knowledge_pages", "id", [x["page_id"] for x in payload["pages"]]
                )

                actual = {
                    table: int(
                        connection.execute(f"SELECT count(*) AS count FROM {table}").fetchone()[  # noqa: S608
                            "count"
                        ]
                    )
                    for table in expected
                }
                isolation_violations = int(
                    connection.execute(
                        """
                        SELECT count(*) AS count FROM knowledge_chunks
                        WHERE (document_id = 'C' AND allowed_routes <> ARRAY['platform']::text[])
                           OR (document_id IN ('A', 'B') AND 'platform' = ANY(allowed_routes))
                        """
                    ).fetchone()["count"]
                )
                if actual != expected or isolation_violations:
                    raise RuntimeError("seed counts or source isolation failed")
            connection.execute(
                """
                UPDATE knowledge_ingestion_runs
                SET status = 'passed', finished_at = now(), metrics = %s
                WHERE id = %s
                """,
                (Jsonb({"counts": actual, "isolation_violations": isolation_violations}), run_id),
            )
        except Exception as exc:
            connection.execute(
                """
                UPDATE knowledge_ingestion_runs
                SET status = 'failed', finished_at = now(), error_summary = %s
                WHERE id = %s
                """,
                (type(exc).__name__, run_id),
            )
            raise

    return {
        "status": "PASS",
        "manifest_sha256": payload["manifest_sha256"],
        "counts": actual,
        "source_isolation_violations": isolation_violations,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--database-url", default=os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
    )
    args = parser.parse_args()
    try:
        report = seed_database(args.database_url)
    except Exception as exc:
        print(f"seed failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
