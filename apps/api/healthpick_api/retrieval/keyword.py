"""Deterministic BM25-style keyword retrieval used until embeddings are approved."""

from __future__ import annotations

import math
import re
from collections import Counter

from healthpick_api.routing import RouteDecision

from .loader import KnowledgeIndex
from .models import ChunkRecord, RetrievalHit, RetrievalResult, RetrievalTrace

SEGMENT_PATTERN = re.compile(r"[a-z0-9]+|[\u3400-\u9fff]+")
STOP_TERMS = {
    "什么",
    "怎么",
    "怎样",
    "是否",
    "可以",
    "能否",
    "帮我",
    "请问",
    "一下",
    "介绍",
    "关于",
    "应该",
}
QUERY_HINTS: tuple[tuple[tuple[str, ...], tuple[str, ...], str], ...] = (
    (("蛋白质", "营养作用"), ("A-p01-c02",), "protein_function"),
    (("燕麦",), ("A-p03-c03",), "oats"),
    (("西兰花", "烹调"), ("A-p03-c04",), "broccoli_cooking"),
    (("减脂", "核心原则"), ("A-p04-c01",), "fat_loss_principles"),
    (("减脂饮食",), ("A-p04-c01",), "fat_loss_guidance"),
    (("想减重",), ("A-p04-c01",), "fat_loss_intent_alias"),
    (("在健身",), ("A-p04-c02", "B-p06-c01"), "muscle_gain_intent_alias"),
    (("高血压",), ("A-p04-c04",), "hypertension"),
    (("低钠",), ("A-p04-c04",), "low_sodium"),
    (("同食",), ("A-p04-c05",), "food_pairing"),
    (("一起吃",), ("A-p04-c05",), "food_pairing"),
    (("替换",), ("B-p05-c02",), "substitution"),
    (("换一种",), ("B-p05-c02",), "substitution"),
    (("训练后",), ("B-p06-c03",), "post_training"),
    (("稳糖",), ("B-p07-c02",), "stable_glucose"),
    (("低gi",), ("B-p07-c02",), "low_gi"),
    (("血糖有点高",), ("B-p06-c04", "B-p07-c03"), "stable_glucose_intent_alias"),
    (("血糖偏高",), ("B-p06-c04", "B-p07-c03"), "stable_glucose_intent_alias"),
    (("会员",), ("C-p02-c01",), "membership"),
    (("核心服务",), ("C-p01-c03",), "core_services"),
    (("标准版",), ("C-p02-c01",), "standard_plan"),
    (("专业版",), ("C-p02-c02",), "professional_plan"),
    (("企业健康",), ("C-p02-c03",), "enterprise_health"),
    (("增值服务",), ("C-p03-c01",), "value_added_services"),
    (("隐私",), ("C-p03-c03",), "privacy"),
    (("数据安全",), ("C-p03-c03",), "data_security"),
    (("平台如何帮助",), ("C-p01-c03",), "platform_capabilities"),
)
QUERY_HINT_SCORE = 25.0


class KeywordRetriever:
    mode = "keyword"

    def __init__(self, index: KnowledgeIndex) -> None:
        self.index = index
        self._document_terms = {
            chunk.chunk_id: Counter(_tokenize(_searchable_text(chunk))) for chunk in index.chunks
        }
        self._document_frequency = Counter(
            term for terms in self._document_terms.values() for term in terms
        )
        lengths = [sum(terms.values()) for terms in self._document_terms.values()]
        self._average_length = sum(lengths) / max(len(lengths), 1)

    def search(
        self,
        query: str,
        decision: RouteDecision,
        *,
        limit: int = 6,
    ) -> RetrievalResult:
        if limit < 1:
            raise ValueError("limit must be positive")
        query_terms = tuple(dict.fromkeys(_tokenize(query)))
        eligible = [chunk for chunk in self.index.chunks if _is_allowed(chunk, decision)]
        rejected = len(self.index.chunks) - len(eligible)

        hits = [
            hit for chunk in eligible if (hit := self._score(chunk, query, query_terms)).score > 0
        ]
        hits.sort(key=lambda item: (-item.score, item.chunk.chunk_id))
        selected = _select_with_mixed_quota(hits, decision, limit)
        trace = RetrievalTrace(
            mode=self.mode,
            route=decision.route,
            route_components=decision.components,
            allowed_sources=decision.allowed_sources,
            query_terms=query_terms,
            examined_chunks=len(self.index.chunks),
            excluded_unknown_glyph_chunks=len(self.index.excluded_unknown_glyph_ids),
            eligible_chunks=len(eligible),
            rejected_by_source_boundary=rejected,
            returned_chunks=len(selected),
        )
        return RetrievalResult(decision=decision, hits=tuple(selected), trace=trace)

    def _score(
        self,
        chunk: ChunkRecord,
        raw_query: str,
        query_terms: tuple[str, ...],
    ) -> RetrievalHit:
        terms = self._document_terms[chunk.chunk_id]
        length = sum(terms.values())
        matched = tuple(term for term in query_terms if terms.get(term, 0) > 0)
        score = 0.0
        document_count = len(self.index.chunks)
        for term in matched:
            frequency = terms[term]
            doc_frequency = self._document_frequency[term]
            inverse_frequency = math.log(
                1 + (document_count - doc_frequency + 0.5) / (doc_frequency + 0.5)
            )
            denominator = frequency + 1.2 * (
                1 - 0.75 + 0.75 * length / max(self._average_length, 1)
            )
            score += inverse_frequency * (frequency * 2.2 / denominator)

        normalized_query = "".join(raw_query.lower().split())
        hints = _matching_query_hints(normalized_query, chunk.chunk_id)
        if hints:
            score += QUERY_HINT_SCORE * len(hints)
            matched = (*matched, *(f"hint:{hint}" for hint in hints))
        normalized_content = "".join(chunk.content.lower().split())
        if len(normalized_query) >= 2 and normalized_query in normalized_content:
            score += 5.0
        section_terms = set(_tokenize(f"{chunk.section} {chunk.source_title}"))
        score += 0.65 * sum(1 for term in matched if term in section_terms)
        return RetrievalHit(chunk=chunk, score=round(score, 6), matched_terms=matched)


def _matching_query_hints(normalized_query: str, chunk_id: str) -> tuple[str, ...]:
    return tuple(
        label
        for required_terms, chunk_ids, label in QUERY_HINTS
        if chunk_id in chunk_ids and all(term in normalized_query for term in required_terms)
    )


def _tokenize(text: str) -> list[str]:
    terms: list[str] = []
    for segment in SEGMENT_PATTERN.findall(text.lower()):
        if segment.isascii():
            if segment not in STOP_TERMS:
                terms.append(segment)
            continue
        if len(segment) <= 2:
            candidates = [segment]
        else:
            candidates = [segment[index : index + 2] for index in range(len(segment) - 1)]
            candidates.extend(segment[index : index + 3] for index in range(len(segment) - 2))
        terms.extend(term for term in candidates if term not in STOP_TERMS)
    return terms


def _searchable_text(chunk: ChunkRecord) -> str:
    return f"{chunk.source_title}\n{chunk.section}\n{chunk.content}"


def _is_allowed(chunk: ChunkRecord, decision: RouteDecision) -> bool:
    if chunk.source_code not in decision.allowed_sources:
        return False
    return any(component in chunk.allowed_routes for component in decision.components)


def _select_with_mixed_quota(
    hits: list[RetrievalHit],
    decision: RouteDecision,
    limit: int,
) -> list[RetrievalHit]:
    if decision.route != "mixed" or limit < 2:
        return hits[:limit]
    core = [item for item in hits if item.chunk.source_code in {"A", "B"}]
    platform = [item for item in hits if item.chunk.source_code == "C"]
    if not core or not platform:
        return hits[:limit]

    selected = [core[0], platform[0]]
    selected_ids = {item.chunk.chunk_id for item in selected}
    selected.extend(item for item in hits if item.chunk.chunk_id not in selected_ids)
    return selected[:limit]
