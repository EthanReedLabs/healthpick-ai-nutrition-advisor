"""Reject citations or inline references that cannot be traced to indexed evidence."""

from __future__ import annotations

import re
from dataclasses import dataclass

from healthpick_api.models import Citation
from healthpick_api.retrieval import ChunkRecord, KnowledgeIndex
from healthpick_api.routing import RouteDecision

INLINE_REFERENCE = re.compile(r"【([ABC]-p\d{2}-c\d{2})】")
REFERENCE_LIKE_TOKEN = re.compile(r"【[^】]*[ABC]-p\d{2}-c\d{2}[^】]*】")
CLAUSE_SPLIT = re.compile(r"(?<=[。！？!?；;])(?!【)|(?<=】)\s+(?=\S)|\n+")
MEASURE = re.compile(
    r"\d+(?:\.\d+)?(?:\s*[-–至]\s*\d+(?:\.\d+)?)?\s*"
    r"(?:千卡|kcal|大卡|克|g|毫克|mg|元|%|周|天)",
    re.IGNORECASE,
)
FACTUAL_MARKERS = (
    "有助于",
    "促进",
    "降低",
    "提供",
    "含有",
    "推荐",
    "每日",
    "每天",
    "每100",
    "作用",
    "包括",
    "比例",
    "价格",
    "会员",
    "适用于",
    "目标",
    "摄入",
    "热量",
    "蛋白质",
    "碳水",
    "脂肪",
    "GI",
)


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
        malformed_references = [
            token
            for token in REFERENCE_LIKE_TOKEN.findall(answer)
            if INLINE_REFERENCE.fullmatch(token) is None
        ]

        if len(citation_ids) != len(set(citation_ids)):
            errors.append("duplicate_citation")
        if decision.route != "out_of_scope" and not citations:
            errors.append("missing_citation")
        if decision.route != "out_of_scope" and not referenced_ids:
            errors.append("missing_inline_reference")
        if malformed_references:
            errors.append("invalid_inline_reference_format")

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
        if decision.route != "out_of_scope":
            errors.extend(_validate_claim_bindings(answer, by_id))

        unique_errors = tuple(dict.fromkeys(errors))
        return EvidenceValidationResult(
            valid=not unique_errors,
            error_codes=unique_errors,
            referenced_chunk_ids=referenced_ids,
        )


def _validate_claim_bindings(answer: str, by_id: dict[str, ChunkRecord]) -> list[str]:
    errors: list[str] = []
    for raw_clause in CLAUSE_SPLIT.split(answer):
        clause = raw_clause.strip()
        if not clause or not any(marker in clause for marker in FACTUAL_MARKERS):
            continue
        references = tuple(dict.fromkeys(INLINE_REFERENCE.findall(clause)))
        if not references:
            errors.append("uncited_factual_claim")
            continue
        evidence_texts = [by_id[chunk_id].content for chunk_id in references if chunk_id in by_id]
        if not evidence_texts:
            continue
        if not _has_text_anchor(clause, evidence_texts):
            errors.append("claim_evidence_anchor_mismatch")
        for measure in MEASURE.findall(INLINE_REFERENCE.sub("", clause)):
            normalized_measure = _compact(measure).casefold()
            if not any(normalized_measure in _compact(text).casefold() for text in evidence_texts):
                errors.append("numeric_claim_not_in_evidence")
    return errors


def _has_text_anchor(claim: str, evidence_texts: list[str]) -> bool:
    normalized_claim = _compact(INLINE_REFERENCE.sub("", claim)).casefold()
    for generic in (*FACTUAL_MARKERS, "规则见此处", "说明见原文", "原文证据"):
        normalized_claim = normalized_claim.replace(_compact(generic).casefold(), "")
    claim_anchors = {
        normalized_claim[index : index + 4]
        for index in range(max(0, len(normalized_claim) - 3))
        if len(normalized_claim[index : index + 4]) == 4
    }
    return any(
        anchor in _compact(evidence).casefold()
        for anchor in claim_anchors
        for evidence in evidence_texts
    )


def _compact(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff.%–-]", "", value)
