from __future__ import annotations

import json
from pathlib import Path

import pytest
from healthpick_api.retrieval import ChunkPolicyError, KeywordRetriever, KnowledgeIndex
from healthpick_api.routing import QueryRouter


@pytest.fixture(scope="module")
def index() -> KnowledgeIndex:
    return KnowledgeIndex.load_default()


@pytest.fixture(scope="module")
def retriever(index: KnowledgeIndex) -> KeywordRetriever:
    return KeywordRetriever(index)


def test_loads_all_normalized_chunks_with_expected_source_counts(index: KnowledgeIndex) -> None:
    assert len(index.chunks) == 67
    assert {source: len(chunks) for source, chunks in index.by_source.items()} == {
        "A": 21,
        "B": 26,
        "C": 20,
    }


@pytest.mark.parametrize(
    ("query", "expected_route", "expected_sources"),
    [
        ("膳食纤维有什么营养作用？", "nutrition", ("A", "B")),
        ("帮我搭配一份增肌早餐食谱", "recommendation", ("A", "B")),
        ("肾病人群有哪些饮食禁忌？", "contraindication", ("A", "B")),
        ("平台会员和企业服务有哪些？", "platform", ("C",)),
        ("平台会员能否获得低钠饮食建议？", "mixed", ("A", "B", "C")),
        ("如何修复汽车发动机？", "out_of_scope", ()),
    ],
)
def test_router_is_deterministic_and_exposes_source_policy(
    query: str,
    expected_route: str,
    expected_sources: tuple[str, ...],
) -> None:
    decision = QueryRouter().route(query)
    assert decision.route == expected_route
    assert decision.allowed_sources == expected_sources
    assert decision.reason_codes


def test_nutrition_retrieval_never_returns_platform_source(
    retriever: KeywordRetriever,
) -> None:
    decision = QueryRouter().route("膳食纤维有什么营养作用？")
    result = retriever.search("膳食纤维有什么营养作用？", decision)

    assert result.hits
    assert {hit.chunk.source_code for hit in result.hits} <= {"A", "B"}
    assert result.trace.rejected_by_source_boundary == 20
    assert all("nutrition" in hit.chunk.allowed_routes for hit in result.hits)


def test_platform_retrieval_is_c_only(retriever: KeywordRetriever) -> None:
    query = "平台会员和企业服务有哪些？"
    result = retriever.search(query, QueryRouter().route(query))

    assert result.hits
    assert {hit.chunk.source_code for hit in result.hits} == {"C"}
    assert result.trace.eligible_chunks == 20
    assert all(hit.chunk.allowed_routes == ("platform",) for hit in result.hits)


def test_mixed_route_reserves_core_and_platform_evidence(
    retriever: KeywordRetriever,
) -> None:
    query = "平台会员能否获得低钠饮食建议？"
    result = retriever.search(query, QueryRouter().route(query), limit=6)
    sources = {hit.chunk.source_code for hit in result.hits}

    assert sources & {"A", "B"}
    assert "C" in sources
    assert result.trace.route_components[-1] == "platform"


def test_out_of_scope_route_returns_no_evidence(retriever: KeywordRetriever) -> None:
    query = "如何修复汽车发动机？"
    result = retriever.search(query, QueryRouter().route(query))
    assert result.hits == ()
    assert result.trace.eligible_chunks == 0
    assert result.trace.returned_chunks == 0


def test_keyword_ranking_is_stable_and_auditable(retriever: KeywordRetriever) -> None:
    query = "低GI碳水和膳食纤维"
    decision = QueryRouter().route(query)
    first = retriever.search(query, decision)
    second = retriever.search(query, decision)

    assert [hit.chunk.chunk_id for hit in first.hits] == [hit.chunk.chunk_id for hit in second.hits]
    assert first.hits[0].score > 0
    assert first.hits[0].matched_terms
    assert first.hits[0].chunk.page >= 1
    assert first.hits[0].chunk.section


def test_loader_rejects_c_chunk_that_claims_nutrition_route(tmp_path: Path) -> None:
    invalid = {
        "chunk_id": "C-p01-c01",
        "source_code": "C",
        "source_role": "auxiliary_platform",
        "source_title": "invalid",
        "source_version": "V0",
        "page": 1,
        "section": "invalid",
        "content": "invalid",
        "allowed_routes": ["nutrition"],
        "forbidden_routes": ["platform"],
        "review_status": "review_required",
    }
    path = tmp_path / "C.chunks.jsonl"
    path.write_text(json.dumps(invalid, ensure_ascii=False) + "\n", encoding="utf-8")

    with pytest.raises(ChunkPolicyError, match="platform-only"):
        KnowledgeIndex.load_paths([path])
