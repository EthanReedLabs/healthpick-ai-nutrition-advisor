"""Strict JSONL loader that validates the A/B core and C platform boundary."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from .models import ChunkRecord

CORE_ROUTES = {"nutrition", "recommendation", "contraindication"}
PLATFORM_ROUTE = "platform"
PROJECT_ROOT = Path(__file__).resolve().parents[4]


class ChunkPolicyError(ValueError):
    pass


class KnowledgeIndex:
    def __init__(self, chunks: Iterable[ChunkRecord]) -> None:
        values = tuple(chunks)
        ids = [item.chunk_id for item in values]
        if len(ids) != len(set(ids)):
            raise ChunkPolicyError("Chunk IDs must be globally unique")
        self.chunks = values
        self.by_source = {
            source: tuple(item for item in values if item.source_code == source)
            for source in ("A", "B", "C")
        }

    @classmethod
    def load_default(cls, root: Path = PROJECT_ROOT) -> KnowledgeIndex:
        chunk_root = root / "knowledge" / "normalized" / "chunks"
        return cls.load_paths([chunk_root / f"{source}.chunks.jsonl" for source in ("A", "B", "C")])

    @classmethod
    def load_paths(cls, paths: Iterable[Path]) -> KnowledgeIndex:
        records: list[ChunkRecord] = []
        for path in paths:
            expected_source = path.name.split(".", maxsplit=1)[0]
            with path.open("r", encoding="utf-8") as stream:
                for line_number, line in enumerate(stream, start=1):
                    if not line.strip():
                        continue
                    try:
                        raw = json.loads(line)
                        chunk = _parse_chunk(raw)
                    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                        raise ChunkPolicyError(
                            f"Invalid chunk at {path}:{line_number}: {exc}"
                        ) from exc
                    if chunk.source_code != expected_source:
                        raise ChunkPolicyError(
                            f"{chunk.chunk_id}: source {chunk.source_code} "
                            f"does not match file {expected_source}"
                        )
                    _validate_source_policy(chunk)
                    records.append(chunk)
        return cls(records)


def _parse_chunk(raw: dict[str, object]) -> ChunkRecord:
    return ChunkRecord(
        chunk_id=_required_str(raw, "chunk_id"),
        source_code=_required_str(raw, "source_code"),
        source_role=_required_str(raw, "source_role"),
        source_title=_required_str(raw, "source_title"),
        source_version=_required_str(raw, "source_version"),
        page=_required_int(raw, "page"),
        section=_required_str(raw, "section"),
        content=_required_str(raw, "content"),
        allowed_routes=_string_tuple(raw, "allowed_routes"),
        forbidden_routes=_string_tuple(raw, "forbidden_routes"),
        review_status=_required_str(raw, "review_status"),
    )


def _validate_source_policy(chunk: ChunkRecord) -> None:
    allowed = set(chunk.allowed_routes)
    forbidden = set(chunk.forbidden_routes)
    if allowed & forbidden:
        raise ChunkPolicyError(f"{chunk.chunk_id}: route cannot be both allowed and forbidden")
    if chunk.source_code in {"A", "B"}:
        if PLATFORM_ROUTE in allowed or not allowed <= CORE_ROUTES:
            raise ChunkPolicyError(f"{chunk.chunk_id}: A/B chunk crosses into platform route")
        if PLATFORM_ROUTE not in forbidden:
            raise ChunkPolicyError(f"{chunk.chunk_id}: A/B chunk must forbid platform route")
    elif chunk.source_code == "C":
        if allowed != {PLATFORM_ROUTE} or not CORE_ROUTES <= forbidden:
            raise ChunkPolicyError(f"{chunk.chunk_id}: C chunk violates platform-only policy")
    else:
        raise ChunkPolicyError(f"{chunk.chunk_id}: unknown source {chunk.source_code}")


def _required_str(raw: dict[str, object], key: str) -> str:
    value = raw[key]
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _required_int(raw: dict[str, object], key: str) -> int:
    value = raw[key]
    if not isinstance(value, int) or value < 1:
        raise ValueError(f"{key} must be a positive integer")
    return value


def _string_tuple(raw: dict[str, object], key: str) -> tuple[str, ...]:
    value = raw[key]
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{key} must be a string array")
    return tuple(value)
