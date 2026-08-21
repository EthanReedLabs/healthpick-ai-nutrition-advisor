from __future__ import annotations

import pytest
from healthpick_api.evidence import CitationBuilder, EvidenceValidator
from healthpick_api.models import Citation
from healthpick_api.retrieval import KeywordRetriever, KnowledgeIndex
from healthpick_api.routing import QueryRouter


@pytest.fixture(scope="module")
def index() -> KnowledgeIndex:
    return KnowledgeIndex.load_default()


def bundle_for(query: str, index: KnowledgeIndex):
    decision = QueryRouter().route(query)
    result = KeywordRetriever(index).search(query, decision, limit=6)
    return decision, CitationBuilder(excerpt_chars=120).build(result)


def test_builder_produces_exact_traceable_excerpts(index: KnowledgeIndex) -> None:
    decision, bundle = bundle_for("膳食纤维有什么营养作用？", index)
    by_id = {chunk.chunk_id: chunk for chunk in index.chunks}

    assert decision.route == "nutrition"
    assert bundle.citations
    for citation in bundle.citations:
        chunk = by_id[citation.chunk_id]
        assert citation.excerpt in chunk.content
        assert len(citation.excerpt) <= 120
        assert citation.page == chunk.page
        assert citation.section == chunk.section


def test_context_blocks_have_hard_evidence_delimiters(index: KnowledgeIndex) -> None:
    _, bundle = bundle_for("平台会员有哪些权益？", index)
    assert bundle.context_blocks
    for citation, context in zip(bundle.citations, bundle.context_blocks, strict=True):
        assert f"[EVIDENCE {citation.chunk_id}]" in context
        assert f"[END EVIDENCE {citation.chunk_id}]" in context
        assert f"source={citation.source}; page={citation.page}" in context


def test_validator_accepts_real_citation_and_inline_reference(index: KnowledgeIndex) -> None:
    decision, bundle = bundle_for("膳食纤维有什么营养作用？", index)
    citation = bundle.citations[0]
    validation = EvidenceValidator(index).validate(
        answer=f"膳食纤维的说明见原文证据【{citation.chunk_id}】。",
        citations=(citation,),
        decision=decision,
    )
    assert validation.valid is True
    assert validation.referenced_chunk_ids == (citation.chunk_id,)


def test_validator_rejects_unknown_citation(index: KnowledgeIndex) -> None:
    decision = QueryRouter().route("营养饮食")
    fabricated = Citation(
        chunk_id="A-p99-c99",
        source="A",
        title="伪造来源",
        page=99,
        section="伪造章节",
        excerpt="伪造摘录",
    )
    validation = EvidenceValidator(index).validate(
        answer="伪造回答【A-p99-c99】",
        citations=(fabricated,),
        decision=decision,
    )
    assert validation.valid is False
    assert "unknown_citation" in validation.error_codes


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("page", 999, "citation_metadata_mismatch"),
        ("section", "不存在的章节", "citation_metadata_mismatch"),
        ("excerpt", "不存在于原文的摘录", "citation_excerpt_mismatch"),
    ],
)
def test_validator_rejects_tampered_citation(
    index: KnowledgeIndex,
    field: str,
    value: object,
    error: str,
) -> None:
    decision, bundle = bundle_for("营养饮食", index)
    original = bundle.citations[0]
    tampered = original.model_copy(update={field: value})
    validation = EvidenceValidator(index).validate(
        answer=f"回答【{original.chunk_id}】",
        citations=(tampered,),
        decision=decision,
    )
    assert error in validation.error_codes


def test_validator_rejects_platform_citation_for_nutrition(index: KnowledgeIndex) -> None:
    nutrition = QueryRouter().route("营养饮食")
    _, platform_bundle = bundle_for("平台会员", index)
    citation = platform_bundle.citations[0]
    validation = EvidenceValidator(index).validate(
        answer=f"越界回答【{citation.chunk_id}】",
        citations=(citation,),
        decision=nutrition,
    )
    assert "citation_route_violation" in validation.error_codes


def test_validator_rejects_inline_reference_not_returned(index: KnowledgeIndex) -> None:
    decision, bundle = bundle_for("膳食纤维营养", index)
    citation = bundle.citations[0]
    validation = EvidenceValidator(index).validate(
        answer=f"回答【{citation.chunk_id}】【A-p99-c99】",
        citations=(citation,),
        decision=decision,
    )
    assert "inline_reference_not_returned" in validation.error_codes


def test_validator_requires_inline_reference_for_supported_answer(index: KnowledgeIndex) -> None:
    decision, bundle = bundle_for("膳食纤维营养", index)
    validation = EvidenceValidator(index).validate(
        answer="没有引用标记的回答",
        citations=(bundle.citations[0],),
        decision=decision,
    )
    assert "missing_inline_reference" in validation.error_codes


def test_out_of_scope_refusal_is_valid_without_evidence(index: KnowledgeIndex) -> None:
    decision = QueryRouter().route("如何修复汽车发动机？")
    validation = EvidenceValidator(index).validate(
        answer="这个问题不在营养与平台说明范围内。",
        citations=(),
        decision=decision,
    )
    assert validation.valid is True


def test_duplicate_citations_are_rejected(index: KnowledgeIndex) -> None:
    decision, bundle = bundle_for("膳食纤维营养", index)
    citation = bundle.citations[0]
    validation = EvidenceValidator(index).validate(
        answer=f"回答【{citation.chunk_id}】",
        citations=(citation, citation),
        decision=decision,
    )
    assert "duplicate_citation" in validation.error_codes


def test_mixed_route_accepts_one_core_and_one_platform_citation(
    index: KnowledgeIndex,
) -> None:
    decision, bundle = bundle_for("平台会员能否获得低钠饮食建议？", index)
    core = next(item for item in bundle.citations if item.source in {"A", "B"})
    platform = next(item for item in bundle.citations if item.source == "C")
    validation = EvidenceValidator(index).validate(
        answer=f"营养证据【{core.chunk_id}】，平台证据【{platform.chunk_id}】。",
        citations=(core, platform),
        decision=decision,
    )
    assert validation.valid is True
