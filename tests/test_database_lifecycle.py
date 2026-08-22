from __future__ import annotations

from pathlib import Path

import pytest

from scripts.migrate_database import canonical_sql_bytes, discover_migrations
from scripts.seed_database import load_seed_payload, validate_seed_payload
from scripts.smoke_compose_lifecycle import EXPECTED_MIGRATION_VERSIONS


def test_migration_checksum_input_is_stable_across_line_endings() -> None:
    assert canonical_sql_bytes(b"BEGIN;\r\nSELECT 1;\r\nCOMMIT;\r\n") == canonical_sql_bytes(
        b"BEGIN;\nSELECT 1;\nCOMMIT;\n"
    )


def test_migrations_are_unique_and_strictly_ordered() -> None:
    migrations = discover_migrations()
    versions = [item.version for item in migrations]
    assert versions == sorted(versions)
    assert versions == ["001", "002", "003", "004", "005"]
    assert EXPECTED_MIGRATION_VERSIONS == versions
    assert len({item.sha256 for item in migrations}) == len(migrations)


def test_invalid_migration_filename_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "01_bad.sql").write_text("SELECT 1;", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid migration filename"):
        discover_migrations(tmp_path)


def test_seed_payload_matches_frozen_counts_and_source_boundary() -> None:
    payload = load_seed_payload()
    assert len(payload["sources"]) == 3
    assert len(payload["pages"]) == 18
    assert len(payload["chunks"]) == 67
    assert len(payload["food_facts"]) == 31
    assert len(payload["plan_rules"]) == 37
    assert len(payload["platform_facts"]) == 12


def test_seed_validation_rejects_c_route_leakage() -> None:
    payload = load_seed_payload()
    c_chunk = next(item for item in payload["chunks"] if item["source_code"] == "C")
    c_chunk["allowed_routes"] = ["nutrition"]
    with pytest.raises(ValueError, match="platform-only boundary"):
        validate_seed_payload(payload)
