from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx2
import pytest
from fastapi.testclient import TestClient
from healthpick_api.chat import (
    ChatPipeline,
    ConversationTurn,
    EphemeralConversationStore,
)
from healthpick_api.chat.pipeline import (
    _log_safety_decision,
    _log_validation_failure,
    _repair_prompt,
    _system_prompt,
)
from healthpick_api.config import Settings
from healthpick_api.main import create_app
from healthpick_api.models import ChatFinalEvent, ChatRequest, SafetyResult
from healthpick_api.providers import (
    FailoverLLMProvider,
    LLMRequest,
    LLMResult,
    ProviderRequestError,
)
from healthpick_api.retrieval import KnowledgeIndex
from healthpick_api.safety import OutputSafetyValidator


def mock_settings() -> Settings:
    return Settings(
        app_env="test",
        web_origin="http://web.test",
        llm_mode="mock",
        llm_model="mock-healthpick-v1",
        embedding_mode="disabled",
        retrieval_mode="keyword",
        _env_file=None,
    )


def parse_sse(body: str) -> list[tuple[str, dict[str, Any]]]:
    events: list[tuple[str, dict[str, Any]]] = []
    for block in body.strip().split("\n\n"):
        lines = block.splitlines()
        event = next(line[7:] for line in lines if line.startswith("event: "))
        data = next(line[6:] for line in lines if line.startswith("data: "))
        events.append((event, json.loads(data)))
    return events


def request(client: TestClient, message: str, conversation_id: str = "sse-test"):
    return client.post(
        "/v1/chat/stream",
        json={"conversation_id": conversation_id, "message": message},
        headers={"X-Request-ID": "d0327ef1-f5a7-4442-b803-f946045d725b"},
    )


def test_mock_chat_sse_has_ordered_events_and_valid_final() -> None:
    with TestClient(create_app(mock_settings()), raise_server_exceptions=False) as client:
        response = request(client, "膳食纤维有什么营养作用？")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-cache, no-transform"
    assert response.headers["x-accel-buffering"] == "no"
    events = parse_sse(response.text)
    names = [name for name, _ in events]
    assert names[0] == "meta"
    assert "citation" in names
    assert "token" in names
    assert names[-1] == "final"

    final = ChatFinalEvent.model_validate(events[-1][1])
    assert final.request_id == "d0327ef1-f5a7-4442-b803-f946045d725b"
    assert final.model.mode == "mock"
    assert final.answer.startswith("[MOCK RESPONSE — NOT REAL MODEL OUTPUT]")
    assert final.citations
    assert f"【{final.citations[0].chunk_id}】" in final.answer
    assert {citation.source for citation in final.citations} <= {"A", "B"}
    assert final.retrieval_trace is not None
    assert final.retrieval_trace.evidence_gate == "passed"
    assert final.retrieval_trace.returned_chunks == len(final.retrieval_trace.selections)
    assert {item.chunk_id for item in final.retrieval_trace.selections} == {
        citation.chunk_id for citation in final.citations
    }
    assert set(final.retrieval_trace.allowed_sources) == {"A", "B"}


@pytest.mark.parametrize(
    ("message", "expected_route", "expected_sources"),
    [
        ("平台会员和企业服务有哪些？", "platform", {"C"}),
        ("膳食纤维有什么营养作用？", "nutrition", {"A", "B"}),
    ],
)
def test_sse_respects_public_route_and_source_boundary(
    message: str,
    expected_route: str,
    expected_sources: set[str],
) -> None:
    with TestClient(create_app(mock_settings()), raise_server_exceptions=False) as client:
        response = request(client, message)
    final = ChatFinalEvent.model_validate(parse_sse(response.text)[-1][1])
    assert final.route == expected_route
    assert {citation.source for citation in final.citations} <= expected_sources
    assert {citation.source for citation in final.citations}


def test_mixed_sse_returns_core_and_platform_citations() -> None:
    with TestClient(create_app(mock_settings()), raise_server_exceptions=False) as client:
        response = request(client, "平台会员能否获得低钠饮食建议？")
    final = ChatFinalEvent.model_validate(parse_sse(response.text)[-1][1])
    sources = {citation.source for citation in final.citations}
    assert final.route == "mixed"
    assert sources & {"A", "B"}
    assert "C" in sources


@pytest.mark.parametrize(
    ("message", "expected_goal", "expected_title"),
    [
        ("我想减重，三餐应该怎么搭配？", "fat_loss", "轻盈减脂方案"),
        ("我在健身，训练前后应该怎么吃？", "muscle_gain", "力量增肌方案"),
        ("我血糖有点高，应该怎样选择低 GI 食物？", "stable_glucose", "稳糖调理方案"),
    ],
)
def test_competition_intent_examples_return_structured_preview(
    message: str,
    expected_goal: str,
    expected_title: str,
) -> None:
    with TestClient(create_app(mock_settings()), raise_server_exceptions=False) as client:
        response = request(client, message)

    assert response.status_code == 200
    final = ChatFinalEvent.model_validate(parse_sse(response.text)[-1][1])
    preview = final.recommendation_preview
    assert preview is not None
    assert preview.selection_basis == "message"
    assert preview.selected_goal == expected_goal
    plan = preview.primary or preview.safe_alternative
    assert plan is not None
    assert expected_title in plan.title


def test_contraindication_preview_filters_foods_and_emits_exact_plan_notice() -> None:
    with TestClient(create_app(mock_settings()), raise_server_exceptions=False) as client:
        response = request(client, "我尿酸高，也想减重，应该怎么搭配？")

    assert response.status_code == 200
    final = ChatFinalEvent.model_validate(parse_sse(response.text)[-1][1])
    assert final.safety.risk_level == "S1"
    assert "high_purine" in final.safety.blocked_food_tags
    assert final.recommendation_preview is not None
    assert final.recommendation_preview.primary is None
    assert final.recommendation_preview.safe_alternative is not None
    assert "建议您在使用本方案前咨询专业医师或注册营养师" in final.answer


def test_out_of_scope_uses_deterministic_guard_without_citations() -> None:
    with TestClient(create_app(mock_settings()), raise_server_exceptions=False) as client:
        response = request(client, "如何修复汽车发动机？")
    events = parse_sse(response.text)
    final = ChatFinalEvent.model_validate(events[-1][1])
    assert final.route == "out_of_scope"
    assert final.model.provider == "healthpick_guard"
    assert final.citations == []
    assert final.retrieval_trace is None
    assert "citation" not in [name for name, _ in events]


def test_real_mode_without_credentials_fails_before_streaming() -> None:
    settings = Settings(
        app_env="test",
        llm_mode="real",
        llm_base_url=None,
        llm_api_key=None,
        llm_model=None,
        retrieval_mode="keyword",
        _env_file=None,
    )
    with TestClient(create_app(settings), raise_server_exceptions=False) as client:
        response = request(client, "膳食纤维有什么营养作用？")

    assert response.status_code == 503
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["code"] == "provider_not_configured"
    assert response.json()["retryable"] is False
    assert "answer" not in response.json()


class UncitedProvider:
    mode = "mock"
    provider_name = "invalid-test-provider"
    model_name = "invalid-test-model"

    def __init__(self) -> None:
        self.call_count = 0
        self.requests: list[LLMRequest] = []

    async def generate(self, request: LLMRequest) -> LLMResult:
        self.call_count += 1
        self.requests.append(request)
        return LLMResult(
            content="没有引用标记的模型回答",
            provider=self.provider_name,
            model=self.model_name,
            mode=self.mode,
            latency_ms=0,
        )

    async def aclose(self) -> None:
        return None


class SlowProvider:
    mode = "mock"
    provider_name = "slow-test-provider"
    model_name = "slow-test-model"

    async def generate(self, request: LLMRequest) -> LLMResult:
        await asyncio.sleep(0.2)
        return LLMResult(
            content="不应返回",
            provider=self.provider_name,
            model=self.model_name,
            mode=self.mode,
            latency_ms=200,
        )

    async def aclose(self) -> None:
        return None


class FailingProvider:
    mode = "real"

    def __init__(self, name: str, code: str) -> None:
        self.provider_name = name
        self.model_name = f"{name}-model"
        self.code = code

    async def generate(self, request: LLMRequest) -> LLMResult:
        raise ProviderRequestError("injected failure", retryable=True, code=self.code)

    async def aclose(self) -> None:
        return None


class CancellableProvider:
    mode = "real"
    provider_name = "cancellable-test-provider"
    model_name = "cancellable-test-model"

    def __init__(self) -> None:
        self.started = asyncio.Event()

    async def generate(self, request: LLMRequest) -> LLMResult:
        self.started.set()
        await asyncio.Event().wait()
        raise AssertionError("cancelled provider unexpectedly resumed")

    async def aclose(self) -> None:
        return None


def test_provider_timeout_is_distinct_retryable_and_not_persisted() -> None:
    conversations = EphemeralConversationStore()
    pipeline = ChatPipeline(
        provider=SlowProvider(),
        index=KnowledgeIndex.load_default(),
        conversations=conversations,
        generation_timeout_seconds=0.01,
    )
    with TestClient(
        create_app(mock_settings(), chat_pipeline=pipeline),
        raise_server_exceptions=False,
    ) as client:
        response = request(client, "膳食纤维有什么营养作用？", "timeout-test")

    assert response.status_code == 504
    assert response.json()["code"] == "provider_timeout"
    assert response.json()["retryable"] is True
    assert conversations._conversations.get("timeout-test", ()) == ()


def test_failover_exhaustion_is_stable_and_not_persisted() -> None:
    conversations = EphemeralConversationStore()
    provider = FailoverLLMProvider(
        FailingProvider("primary", "provider_timeout"),  # type: ignore[arg-type]
        FailingProvider("backup", "provider_upstream_unavailable"),  # type: ignore[arg-type]
    )
    pipeline = ChatPipeline(
        provider=provider,
        index=KnowledgeIndex.load_default(),
        conversations=conversations,
    )
    with TestClient(
        create_app(mock_settings(), chat_pipeline=pipeline),
        raise_server_exceptions=False,
    ) as client:
        response = request(client, "膳食纤维有什么营养作用？", "failover-exhausted")

    assert response.status_code == 503
    assert response.json()["code"] == "provider_failover_exhausted"
    assert response.json()["retryable"] is True
    assert conversations._conversations.get("failover-exhausted", ()) == ()


@pytest.mark.anyio
async def test_active_generation_can_be_cancelled_without_persisting() -> None:
    request_id = "88888888-8888-4888-8888-888888888888"
    conversations = EphemeralConversationStore()
    provider = CancellableProvider()
    pipeline = ChatPipeline(
        provider=provider,
        index=KnowledgeIndex.load_default(),
        conversations=conversations,
        generation_timeout_seconds=30,
    )
    app = create_app(mock_settings(), chat_pipeline=pipeline)
    transport = httpx2.ASGITransport(app=app)
    async with httpx2.AsyncClient(transport=transport, base_url="http://test") as client:
        chat_request = asyncio.create_task(
            client.post(
                "/v1/chat/stream",
                json={
                    "conversation_id": "cancelled-test",
                    "message": "膳食纤维有什么营养作用？",
                },
                headers={"X-Request-ID": request_id},
            )
        )
        await asyncio.wait_for(provider.started.wait(), timeout=1)
        cancelled = await client.post(f"/v1/chat/cancel/{request_id}")
        response = await asyncio.wait_for(chat_request, timeout=1)

    assert cancelled.status_code == 204
    assert response.status_code == 409
    assert response.json()["code"] == "generation_cancelled"
    assert response.json()["retryable"] is True
    assert conversations._conversations.get("cancelled-test", ()) == ()
    assert app.state.active_chat_tasks == {}


def test_uncited_provider_output_uses_validated_evidence_fallback() -> None:
    provider = UncitedProvider()
    pipeline = ChatPipeline(provider=provider, index=KnowledgeIndex.load_default())
    with TestClient(
        create_app(mock_settings(), chat_pipeline=pipeline),
        raise_server_exceptions=False,
    ) as client:
        response = request(client, "膳食纤维有什么营养作用？")

    assert response.status_code == 200
    final = ChatFinalEvent.model_validate(parse_sse(response.text)[-1][1])
    assert final.model.provider == "healthpick_guard"
    assert final.model.name == "deterministic_evidence_fallback"
    assert final.citations
    assert "没有引用标记的模型回答" not in final.answer
    assert "以下内容直接摘自本次检索资料" in final.answer
    assert "【" in final.answer
    assert provider.call_count == 2
    assert provider.requests[0].temperature == 0
    assert provider.requests[0].max_tokens == 500


def test_evidence_fallback_selects_the_query_relevant_numeric_clause() -> None:
    provider = UncitedProvider()
    pipeline = ChatPipeline(provider=provider, index=KnowledgeIndex.load_default())
    with TestClient(
        create_app(mock_settings(), chat_pipeline=pipeline),
        raise_server_exceptions=False,
    ) as client:
        response = request(client, "碳水化合物每克提供多少热量？", "numeric-fallback")

    assert response.status_code == 200
    final = ChatFinalEvent.model_validate(parse_sse(response.text)[-1][1])
    assert final.model.name == "deterministic_evidence_fallback"
    assert "每克提供4 千卡热量" in final.answer
    assert "【A-p01-c02】" in final.answer


class InvalidFallbackPipeline(ChatPipeline):
    def _build_evidence_fallback(self, **kwargs: object) -> str:
        del kwargs
        return "安全回退也没有引用"


def test_invalid_deterministic_fallback_still_fails_closed() -> None:
    provider = UncitedProvider()
    pipeline = InvalidFallbackPipeline(
        provider=provider,
        index=KnowledgeIndex.load_default(),
    )
    with TestClient(
        create_app(mock_settings(), chat_pipeline=pipeline),
        raise_server_exceptions=False,
    ) as client:
        response = request(client, "膳食纤维有什么营养作用？")

    assert response.status_code == 502
    assert response.json()["code"] == "evidence_validation_failed"
    assert "安全证据回退均未通过校验" in response.json()["message"]
    assert provider.call_count == 2


class RepairingProvider(UncitedProvider):
    async def generate(self, request: LLMRequest) -> LLMResult:
        self.call_count += 1
        self.requests.append(request)
        content = "没有引用标记的模型回答"
        if self.call_count == 2:
            assert "missing_inline_reference" in request.messages[-1].content
            content = "膳食纤维有助于促进肠道蠕动。【A-p01-c04】"
        return LLMResult(
            content=content,
            provider=self.provider_name,
            model=self.model_name,
            mode=self.mode,
            latency_ms=0,
        )


def test_pipeline_repairs_invalid_inline_reference_once() -> None:
    provider = RepairingProvider()
    pipeline = ChatPipeline(provider=provider, index=KnowledgeIndex.load_default())
    with TestClient(
        create_app(mock_settings(), chat_pipeline=pipeline),
        raise_server_exceptions=False,
    ) as client:
        response = request(client, "膳食纤维有什么营养作用？")

    assert response.status_code == 200
    final = ChatFinalEvent.model_validate(parse_sse(response.text)[-1][1])
    assert "【A-p01-c04】" in final.answer
    assert final.answer.endswith("不替代医疗诊断或治疗。")
    assert provider.call_count == 2


class SecondaryEvidenceProvider(UncitedProvider):
    async def generate(self, request: LLMRequest) -> LLMResult:
        self.call_count += 1
        self.requests.append(request)
        return LLMResult(
            content="燕麦属于全谷物。【A-p01-c02】",
            provider=self.provider_name,
            model=self.model_name,
            mode=self.mode,
            latency_ms=0,
        )


def test_pipeline_rejects_secondary_only_citation_and_uses_primary_evidence() -> None:
    provider = SecondaryEvidenceProvider()
    pipeline = ChatPipeline(provider=provider, index=KnowledgeIndex.load_default())
    with TestClient(
        create_app(mock_settings(), chat_pipeline=pipeline),
        raise_server_exceptions=False,
    ) as client:
        response = request(client, "燕麦的膳食纤维和GI如何？", "primary-evidence")

    assert response.status_code == 200
    final = ChatFinalEvent.model_validate(parse_sse(response.text)[-1][1])
    assert final.model.name == "deterministic_evidence_fallback"
    assert "【A-p03-c03】" in final.answer
    assert provider.call_count == 2


def test_blocked_food_safety_can_select_safe_non_primary_evidence() -> None:
    provider = UncitedProvider()
    pipeline = ChatPipeline(provider=provider, index=KnowledgeIndex.load_default())
    with TestClient(
        create_app(mock_settings(), chat_pipeline=pipeline),
        raise_server_exceptions=False,
    ) as client:
        response = request(client, "我鸡蛋过敏，早餐怎么吃？", "allergy-safe-evidence")

    assert response.status_code == 200
    final = ChatFinalEvent.model_validate(parse_sse(response.text)[-1][1])
    assert final.safety.blocked_food_tags == ["egg"]
    assert "鸡蛋" not in final.answer
    assert OutputSafetyValidator().validate(answer=final.answer, safety=final.safety).valid


def test_s2_evidence_fallback_keeps_professional_boundary() -> None:
    provider = UncitedProvider()
    pipeline = ChatPipeline(provider=provider, index=KnowledgeIndex.load_default())
    with TestClient(
        create_app(mock_settings(), chat_pipeline=pipeline),
        raise_server_exceptions=False,
    ) as client:
        response = client.post(
            "/v1/chat/stream",
            json={
                "conversation_id": "s2-fallback",
                "message": "膳食纤维有什么营养作用？",
                "profile_patch": {"conditions": ["kidney_disease"]},
            },
        )

    assert response.status_code == 200
    final = ChatFinalEvent.model_validate(parse_sse(response.text)[-1][1])
    assert final.safety.risk_level == "S2"
    assert final.model.name == "deterministic_evidence_fallback"
    assert "本建议仅供参考，不构成医疗建议，请咨询专业医师或注册营养师" in final.answer
    assert OutputSafetyValidator().validate(answer=final.answer, safety=final.safety).valid


@pytest.mark.anyio
async def test_deterministic_fallback_isolated_across_concurrent_requests() -> None:
    provider = UncitedProvider()
    pipeline = ChatPipeline(provider=provider, index=KnowledgeIndex.load_default())
    executions = await asyncio.gather(
        *(
            pipeline.run(
                ChatRequest(
                    conversation_id=f"fallback-concurrent-{index}",
                    message="膳食纤维有什么营养作用？",
                ),
                request_id=f"fallback-request-{index}",
            )
            for index in range(3)
        )
    )

    assert provider.call_count == 6
    assert {execution.final.request_id for execution in executions} == {
        "fallback-request-0",
        "fallback-request-1",
        "fallback-request-2",
    }
    assert all(
        execution.final.model.name == "deterministic_evidence_fallback" for execution in executions
    )
    assert all(execution.final.citations for execution in executions)


def test_system_prompt_freezes_exact_inline_reference_syntax() -> None:
    prompt = _system_prompt()
    assert "【A-p01-c04】" in prompt
    assert "禁止写成【Chunk-ID: A-p01-c04】" in prompt
    assert "逐字匹配" in prompt
    assert "一到三条短句" in prompt
    assert "句末标点前" in prompt


def test_repair_prompt_limits_ids_and_includes_error_codes() -> None:
    prompt = _repair_prompt(("missing_inline_reference",), ("A-p01-c04", "B-p01-c02"))
    assert "missing_inline_reference" in prompt
    assert "A-p01-c04, B-p01-c02" in prompt
    assert "不得使用列表外 ID" in prompt
    assert "一到三条短句" in prompt


def test_safety_and_validation_logs_exclude_raw_health_text(
    caplog: pytest.LogCaptureFixture,
) -> None:
    raw_answer = "敏感病史：正在服用某药且有家庭住址"
    safety = SafetyResult(
        risk_level="S2",
        matched_rules=["profile_kidney_disease"],
        required_notice="professional",
        response_mode="general_only",
        allow_personalized_targets=False,
    )
    with caplog.at_level("INFO", logger="healthpick.api.chat"):
        _log_safety_decision(request_id="privacy-log", safety=safety)
        _log_validation_failure(
            request_id="privacy-log",
            attempt=1,
            answer=raw_answer,
            error_codes=("forbidden_precise_target",),
            referenced_chunk_ids=("A-p01-c04",),
        )
    assert raw_answer not in caplog.text
    assert "家庭住址" not in caplog.text
    assert "profile_kidney_disease" in caplog.text
    assert "answer_sha256=" in caplog.text


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_ephemeral_conversation_store_is_bounded() -> None:
    store = EphemeralConversationStore(max_conversations=1, max_turns=2)
    for index in range(3):
        await store.append(
            "first",
            ConversationTurn(
                user_message=f"u{index}",
                assistant_message=f"a{index}",
                request_id=f"r{index}",
                route="nutrition",
            ),
        )
    assert [turn.request_id for turn in await store.history("first")] == ["r1", "r2"]

    await store.append(
        "second",
        ConversationTurn(
            user_message="u",
            assistant_message="a",
            request_id="r",
            route="platform",
        ),
    )
    assert await store.history("first") == ()
    assert len(await store.history("second")) == 1
