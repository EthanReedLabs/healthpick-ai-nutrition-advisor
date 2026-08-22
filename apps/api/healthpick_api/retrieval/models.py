from __future__ import annotations

from dataclasses import dataclass

from healthpick_api.routing import RouteDecision, RouteName


@dataclass(frozen=True, slots=True)
class ChunkRecord:
    chunk_id: str
    source_code: str
    source_role: str
    source_title: str
    source_version: str
    page: int
    section: str
    content: str
    allowed_routes: tuple[str, ...]
    forbidden_routes: tuple[str, ...]
    review_status: str
    unknown_glyph_count: int = 0


@dataclass(frozen=True, slots=True)
class RetrievalHit:
    chunk: ChunkRecord
    score: float
    matched_terms: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RetrievalTrace:
    mode: str
    route: RouteName
    route_components: tuple[str, ...]
    allowed_sources: tuple[str, ...]
    query_terms: tuple[str, ...]
    examined_chunks: int
    excluded_unknown_glyph_chunks: int
    eligible_chunks: int
    rejected_by_source_boundary: int
    returned_chunks: int


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    decision: RouteDecision
    hits: tuple[RetrievalHit, ...]
    trace: RetrievalTrace
