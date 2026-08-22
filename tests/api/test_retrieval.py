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


def test_loads_only_unambiguous_chunks_with_expected_source_counts(
    index: KnowledgeIndex,
) -> None:
    assert len(index.chunks) == 59
    assert {source: len(chunks) for source, chunks in index.by_source.items()} == {
        "A": 19,
        "B": 20,
        "C": 20,
    }
    assert len(index.excluded_unknown_glyph_ids) == 8
    assert all(chunk.unknown_glyph_count == 0 for chunk in index.chunks)


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


@pytest.mark.parametrize(
    ("query", "expected_route"),
    [
        ("211餐盘法则怎么分配？", "nutrition"),
        ("西兰花适合怎样烹调？", "nutrition"),
        ("豆浆和鸡蛋能不能一起吃？", "nutrition"),
        ("菠菜和豆腐能同食吗？", "nutrition"),
        ("免费版包含哪些功能？", "platform"),
        ("标准版包含哪些服务？", "platform"),
        ("专业版增加了什么？", "platform"),
        ("企业健康管家面向什么企业？", "platform"),
        ("平台有哪些增值服务？", "platform"),
        ("API开放平台有哪些套餐？", "platform"),
        ("给我稳糖食谱并介绍企业健康服务", "mixed"),
        ("训练后怎么补充？", "recommendation"),
    ],
)
def test_router_covers_supported_natural_language_aliases(query: str, expected_route: str) -> None:
    assert QueryRouter().route(query).route == expected_route


@pytest.mark.parametrize(
    ("query", "expected_chunk_ids"),
    [
        ("我想减重", {"A-p04-c01"}),
        ("我在健身", {"A-p04-c02", "B-p06-c01"}),
        ("我血糖有点高", {"B-p06-c04", "B-p07-c03"}),
    ],
)
def test_competition_intent_examples_route_to_core_recommendation_evidence(
    retriever: KeywordRetriever,
    query: str,
    expected_chunk_ids: set[str],
) -> None:
    decision = QueryRouter().route(query)
    result = retriever.search(query, decision)

    assert decision.route == "recommendation"
    assert decision.allowed_sources == ("A", "B")
    assert expected_chunk_ids <= {hit.chunk.chunk_id for hit in result.hits}
    assert {hit.chunk.source_code for hit in result.hits} <= {"A", "B"}


def test_competition_intent_aliases_do_not_capture_unrelated_gym_membership() -> None:
    decision = QueryRouter().route("健身房会员卡怎么退款？")

    assert decision.route == "platform"
    assert decision.allowed_sources == ("C",)


@pytest.mark.parametrize(
    "query",
    ["明天北京会下雨吗？", "给我写一段Python爬虫", "如何修复汽车发动机？"],
)
def test_router_aliases_do_not_expand_unrelated_scope(query: str) -> None:
    decision = QueryRouter().route(query)
    assert decision.route == "out_of_scope"
    assert decision.allowed_sources == ()


def test_nutrition_retrieval_never_returns_platform_source(
    retriever: KeywordRetriever,
) -> None:
    decision = QueryRouter().route("膳食纤维有什么营养作用？")
    result = retriever.search("膳食纤维有什么营养作用？", decision)

    assert result.hits
    assert {hit.chunk.source_code for hit in result.hits} <= {"A", "B"}
    assert result.trace.rejected_by_source_boundary == 20
    assert result.trace.excluded_unknown_glyph_chunks == 8
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


@pytest.mark.parametrize(
    ("query", "expected_primary"),
    [
        ("蛋白质有什么营养作用？", "A-p01-c02"),
        ("燕麦的膳食纤维和GI如何？", "A-p03-c03"),
        ("西兰花适合怎样烹调？", "A-p03-c04"),
        ("减脂饮食有哪些核心原则？", "A-p04-c01"),
        ("会员能获得什么减脂饮食帮助？", "A-p04-c01"),
        ("高血压饮食需要注意什么？", "A-p04-c04"),
        ("糙米可以用什么同类食材替换？", "B-p05-c02"),
        ("训练后怎么补充？", "B-p06-c03"),
        ("HealthPick提供哪些核心服务？", "C-p01-c03"),
        ("标准版包含哪些服务？", "C-p02-c01"),
        ("专业版增加了什么？", "C-p02-c02"),
        ("企业健康管家面向什么企业？", "C-p02-c03"),
        ("平台有哪些增值服务？", "C-p03-c01"),
        ("平台如何说明数据安全与隐私？", "C-p03-c03"),
    ],
)
def test_curated_concept_hints_rank_primary_evidence_first(
    retriever: KeywordRetriever, query: str, expected_primary: str
) -> None:
    decision = QueryRouter().route(query)
    result = retriever.search(query, decision)
    assert result.hits[0].chunk.chunk_id == expected_primary
    assert any(term.startswith("hint:") for term in result.hits[0].matched_terms)


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


def test_loader_excludes_unknown_glyph_chunk(tmp_path: Path) -> None:
    ambiguous = {
        "chunk_id": "A-p01-c01",
        "source_code": "A",
        "source_role": "core_nutrition",
        "source_title": "ambiguous",
        "source_version": "V0",
        "page": 1,
        "section": "ambiguous",
        "content": "阈值符号缺失",
        "allowed_routes": ["nutrition"],
        "forbidden_routes": ["platform"],
        "review_status": "review_required",
        "unknown_glyph_count": 1,
    }
    path = tmp_path / "A.chunks.jsonl"
    path.write_text(json.dumps(ambiguous, ensure_ascii=False) + "\n", encoding="utf-8")

    loaded = KnowledgeIndex.load_paths([path])
    assert loaded.chunks == ()
    assert loaded.excluded_unknown_glyph_ids == ("A-p01-c01",)
