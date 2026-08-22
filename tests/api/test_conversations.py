from __future__ import annotations

import json
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from healthpick_api.config import Settings
from healthpick_api.main import create_app


def settings() -> Settings:
    return Settings(
        app_env="test",
        web_origin="http://web.test",
        llm_mode="mock",
        llm_model="mock-healthpick-v1",
        embedding_mode="disabled",
        retrieval_mode="keyword",
        conversation_store_mode="ephemeral",
        _env_file=None,
    )


def final_event(body: str) -> dict[str, object]:
    for block in body.strip().split("\n\n"):
        if "event: final" not in block:
            continue
        data = next(line[6:] for line in block.splitlines() if line.startswith("data: "))
        return json.loads(data)
    raise AssertionError("final event missing")


def test_server_owned_session_conversation_and_turn_crud() -> None:
    with TestClient(create_app(settings()), raise_server_exceptions=False) as client:
        session_response = client.post("/v1/sessions/anonymous")
        assert session_response.status_code == 201
        session_id = session_response.json()["session_id"]
        UUID(session_id)

        create_response = client.post(
            "/v1/conversations",
            json={"session_id": session_id, "title": "新对话"},
        )
        assert create_response.status_code == 201
        conversation_id = create_response.json()["conversation_id"]
        UUID(conversation_id)
        assert not conversation_id.startswith("web-")

        chat_response = client.post(
            "/v1/chat/stream",
            json={
                "session_id": session_id,
                "conversation_id": conversation_id,
                "message": "膳食纤维有什么营养作用？",
            },
            headers={"X-Request-ID": "d0327ef1-f5a7-4442-b803-f946045d725b"},
        )
        assert chat_response.status_code == 200
        chat_final = final_event(chat_response.text)
        UUID(str(chat_final["turn_id"]))

        detail_response = client.get(
            f"/v1/conversations/{conversation_id}", params={"session_id": session_id}
        )
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert detail["turn_count"] == 1
        assert detail["title"] == "膳食纤维有什么营养作用？"
        assert detail["turns"][0]["turn_id"] == chat_final["turn_id"]
        assert detail["turns"][0]["request_id"] == chat_final["request_id"]

        list_response = client.get("/v1/conversations", params={"session_id": session_id})
        assert list_response.status_code == 200
        assert list_response.json()["items"][0]["conversation_id"] == conversation_id

        rename_response = client.patch(
            f"/v1/conversations/{conversation_id}",
            json={"session_id": session_id, "title": "  高纤维饮食  "},
        )
        assert rename_response.status_code == 200
        assert rename_response.json()["title"] == "高纤维饮食"

        delete_response = client.delete(
            f"/v1/conversations/{conversation_id}", params={"session_id": session_id}
        )
        assert delete_response.status_code == 204
        missing_response = client.get(
            f"/v1/conversations/{conversation_id}", params={"session_id": session_id}
        )
        assert missing_response.status_code == 404
        assert missing_response.json()["code"] == "conversation_not_found"


def test_conversation_ownership_is_fail_closed() -> None:
    with TestClient(create_app(settings()), raise_server_exceptions=False) as client:
        owner_id = client.post("/v1/sessions/anonymous").json()["session_id"]
        attacker_id = client.post("/v1/sessions/anonymous").json()["session_id"]
        conversation_id = client.post(
            "/v1/conversations",
            json={"session_id": owner_id, "title": "owner"},
        ).json()["conversation_id"]

        for response in (
            client.get(
                f"/v1/conversations/{conversation_id}",
                params={"session_id": attacker_id},
            ),
            client.patch(
                f"/v1/conversations/{conversation_id}",
                json={"session_id": attacker_id, "title": "stolen"},
            ),
            client.delete(
                f"/v1/conversations/{conversation_id}",
                params={"session_id": attacker_id},
            ),
        ):
            assert response.status_code == 404
            assert response.json()["code"] == "conversation_not_found"


def test_persistent_mode_requires_session_id_on_chat() -> None:
    from healthpick_api.chat import ChatPipeline, PostgresConversationStore
    from healthpick_api.providers import MockLLMProvider
    from healthpick_api.retrieval import KnowledgeIndex

    pipeline = ChatPipeline(
        provider=MockLLMProvider(model_name="mock-healthpick-v1"),
        index=KnowledgeIndex.load_default(),
        conversations=PostgresConversationStore("postgresql://invalid.invalid/healthpick"),
    )
    with TestClient(
        create_app(settings(), chat_pipeline=pipeline), raise_server_exceptions=False
    ) as client:
        response = client.post(
            "/v1/chat/stream",
            json={"conversation_id": str(UUID(int=1)), "message": "膳食纤维有什么作用？"},
        )

    assert response.status_code == 422
    assert response.json()["code"] == "session_required"


@pytest.mark.anyio
async def test_postgres_timeout_is_not_collapsed_into_generic_unavailability() -> None:
    from healthpick_api.chat import ConversationStoreError, PostgresConversationStore
    from psycopg.errors import QueryCanceled

    store = PostgresConversationStore("postgresql://unused.invalid/healthpick")

    def timed_out() -> None:
        raise QueryCanceled("statement timeout")

    with pytest.raises(ConversationStoreError) as caught:
        await store._run(timed_out)

    assert caught.value.code == "conversation_store_timeout"
    assert caught.value.status_code == 503
    assert caught.value.retryable is True
