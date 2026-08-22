"""Apply ordered PostgreSQL migrations with canonical checksums and safe baselining."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from psycopg import Connection, connect
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = ROOT / "infra" / "migrations"
MIGRATION_NAME = re.compile(r"^(?P<version>\d{3})_[a-z0-9_]+\.sql$")
DEFAULT_DATABASE_URL = "postgresql://healthpick:healthpick-local-only@127.0.0.1:54329/healthpick"


@dataclass(frozen=True, slots=True)
class Migration:
    version: str
    filename: str
    path: Path
    sql: str
    sha256: str


def canonical_sql_bytes(raw: bytes) -> bytes:
    return raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def discover_migrations(directory: Path = MIGRATIONS_DIR) -> tuple[Migration, ...]:
    migrations: list[Migration] = []
    seen_versions: set[str] = set()
    for path in sorted(directory.glob("*.sql")):
        match = MIGRATION_NAME.fullmatch(path.name)
        if match is None:
            raise ValueError(f"invalid migration filename: {path.name}")
        version = match.group("version")
        if version in seen_versions:
            raise ValueError(f"duplicate migration version: {version}")
        seen_versions.add(version)
        canonical = canonical_sql_bytes(path.read_bytes())
        migrations.append(
            Migration(
                version=version,
                filename=path.name,
                path=path,
                sql=canonical.decode("utf-8"),
                sha256=hashlib.sha256(canonical).hexdigest(),
            )
        )
    if not migrations:
        raise ValueError("no migrations found")
    return tuple(migrations)


def ensure_migration_table(connection: Connection[dict[str, object]]) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version text PRIMARY KEY,
            filename text NOT NULL UNIQUE,
            sha256 char(64) NOT NULL CHECK (sha256 ~ '^[a-f0-9]{64}$'),
            execution text NOT NULL CHECK (execution IN ('applied', 'baselined')),
            applied_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )


def migration_effect_state(
    connection: Connection[dict[str, object]], version: str
) -> Literal["absent", "partial", "applied"]:
    checks: tuple[bool, ...]
    if version == "001":
        table_names = (
            "knowledge_documents",
            "knowledge_pages",
            "knowledge_chunks",
            "food_facts",
            "plan_rules",
            "platform_facts",
            "knowledge_ingestion_runs",
        )
        checks = tuple(
            bool(
                connection.execute(
                    "SELECT to_regclass(%s) IS NOT NULL AS present", (f"public.{name}",)
                ).fetchone()["present"]
            )
            for name in table_names
        )
    elif version == "002":
        row = connection.execute(
            "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') AS present"
        ).fetchone()
        checks = (bool(row["present"]),)
    elif version == "003":
        column = connection.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM pg_attribute a
                JOIN pg_class c ON c.oid = a.attrelid
                WHERE c.relname = 'knowledge_chunks'
                  AND a.attname = 'embedding'
                  AND format_type(a.atttypid, a.atttypmod) = 'vector(1024)'
            ) AS present
            """
        ).fetchone()
        index = connection.execute(
            "SELECT to_regclass("
            "'public.knowledge_chunks_embedding_hnsw_idx'"
            ") IS NOT NULL AS present"
        ).fetchone()
        checks = (bool(column["present"]), bool(index["present"]))
    elif version == "004":
        table_checks = tuple(
            bool(
                connection.execute(
                    "SELECT to_regclass(%s) IS NOT NULL AS present", (f"public.{name}",)
                ).fetchone()["present"]
            )
            for name in ("anonymous_sessions", "conversations", "conversation_turns")
        )
        response_payload = connection.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'conversation_turns'
                  AND column_name = 'response_payload'
            ) AS present
            """
        ).fetchone()
        checks = (*table_checks, bool(response_payload["present"]))
    else:
        return "absent"

    if all(checks):
        return "applied"
    if any(checks):
        return "partial"
    return "absent"


def apply_migrations(database_url: str) -> dict[str, object]:
    migrations = discover_migrations()
    results: list[dict[str, str]] = []
    with connect(database_url, autocommit=True, row_factory=dict_row) as connection:
        ensure_migration_table(connection)
        recorded = {
            str(row["version"]): row
            for row in connection.execute(
                "SELECT version, filename, sha256, execution FROM schema_migrations"
            ).fetchall()
        }
        for migration in migrations:
            existing = recorded.get(migration.version)
            if existing is not None:
                if (
                    existing["filename"] != migration.filename
                    or existing["sha256"] != migration.sha256
                ):
                    raise RuntimeError(
                        f"migration {migration.version} checksum or filename changed after apply"
                    )
                results.append(
                    {
                        "version": migration.version,
                        "filename": migration.filename,
                        "result": "already_applied",
                    }
                )
                continue

            effect_state = migration_effect_state(connection, migration.version)
            if effect_state == "partial":
                raise RuntimeError(
                    f"migration {migration.version} has partial effects; refusing unsafe baseline"
                )
            execution = "baselined" if effect_state == "applied" else "applied"
            if execution == "applied":
                try:
                    connection.execute(migration.sql)
                except Exception:
                    connection.rollback()
                    raise
            connection.execute(
                """
                INSERT INTO schema_migrations(version, filename, sha256, execution)
                VALUES (%s, %s, %s, %s)
                """,
                (migration.version, migration.filename, migration.sha256, execution),
            )
            results.append(
                {
                    "version": migration.version,
                    "filename": migration.filename,
                    "result": execution,
                }
            )

    return {
        "status": "PASS",
        "migration_count": len(migrations),
        "migrations": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--database-url", default=os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
    )
    args = parser.parse_args()
    try:
        report = apply_migrations(args.database_url)
    except Exception as exc:
        print(f"migration failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
