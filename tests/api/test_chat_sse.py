from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient
from healthpick_api.chat import (
    ChatPipeline,
    ConversationTurn,
    EphemeralConversationStore,
)
from healthpick_api.config import Settings
from healthpick_api.main import create_app
from healthpick_api.models import ChatFinalEvent
from healthpick_api.providers import LLMRequest, LLMResult
from healthpick_api.retrieval import KnowledgeIndex


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


def test_out_of_scope_uses_deterministic_guard_without_citations() -> None:
    with TestClient(create_app(mock_settings()), raise_server_exceptions=False) as client:
        response = request(client, "如何修复汽车发动机？")
    events = parse_sse(response.text)
    final = ChatFinalEvent.model_validate(events[-1][1])
    assert final.route == "out_of_scope"
    assert final.model.provider == "healthpick_guard"
    assert final.citations == []
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

    async def generate(self, request: LLMRequest) -> LLMResult:
        del request
        return LLMResult(
            content="没有引用标记的模型回答",
            provider=self.provider_name,
            model=self.model_name,
            mode=self.mode,
            latency_ms=0,
        )

    async def aclose(self) -> None:
        return None


def test_uncited_provider_output_fails_closed_before_sse() -> None:
    pipeline = ChatPipeline(provider=UncitedProvider(), index=KnowledgeIndex.load_default())
    with TestClient(
        create_app(mock_settings(), chat_pipeline=pipeline),
        raise_server_exceptions=False,
    ) as client:
        response = request(client, "膳食纤维有什么营养作用？")

    assert response.status_code == 502
    assert response.json()["code"] == "evidence_validation_failed"
    assert "模型输出未通过证据完整性校验" in response.json()["message"]


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
