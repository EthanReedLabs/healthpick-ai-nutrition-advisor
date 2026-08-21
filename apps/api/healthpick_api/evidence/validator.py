"""Reject citations or inline references that cannot be traced to indexed evidence."""

from __future__ import annotations

import re
from dataclasses import dataclass

from healthpick_api.models import Citation
from healthpick_api.retrieval import KnowledgeIndex
from healthpick_api.routing import RouteDecision

INLINE_REFERENCE = re.compile(r"【([ABC]-p\d{2}-c\d{2})】")


@dataclass(frozen=True, slots=True)
class EvidenceValidationResult:
    valid: bool
    error_codes: tuple[str, ...]
    referenced_chunk_ids: tuple[str, ...]


class EvidenceValidator:
    def __init__(self, index: KnowledgeIndex) -> None:
        self.index = index

    def validate(
        self,
        *,
        answer: str,
        citations: tuple[Citation, ...],
        decision: RouteDecision,
    ) -> EvidenceValidationResult:
        errors: list[str] = []
        citation_ids = [citation.chunk_id for citation in citations]
        referenced_ids = tuple(dict.fromkeys(INLINE_REFERENCE.findall(answer)))

        if len(citation_ids) != len(set(citation_ids)):
            errors.append("duplicate_citation")
        if decision.route != "out_of_scope" and not citations:
            errors.append("missing_citation")
        if decision.route != "out_of_scope" and not referenced_ids:
            errors.append("missing_inline_reference")

        by_id = {chunk.chunk_id: chunk for chunk in self.index.chunks}
        for citation in citations:
            chunk = by_id.get(citation.chunk_id)
            if chunk is None:
                errors.append("unknown_citation")
                continue
            if chunk.source_code not in decision.allowed_sources or not any(
                component in chunk.allowed_routes for component in decision.components
            ):
                errors.append("citation_route_violation")
            if (
                citation.source != chunk.source_code
                or citation.title != chunk.source_title
                or citation.page != chunk.page
                or citation.section != chunk.section
            ):
                errors.append("citation_metadata_mismatch")
            if not citation.excerpt or citation.excerpt not in chunk.content:
                errors.append("citation_excerpt_mismatch")

        if any(chunk_id not in set(citation_ids) for chunk_id in referenced_ids):
            errors.append("inline_reference_not_returned")
        if decision.route == "out_of_scope" and (citations or referenced_ids):
            errors.append("out_of_scope_has_evidence")

        unique_errors = tuple(dict.fromkeys(errors))
        return EvidenceValidationResult(
            valid=not unique_errors,
            error_codes=unique_errors,
            referenced_chunk_ids=referenced_ids,
        )
