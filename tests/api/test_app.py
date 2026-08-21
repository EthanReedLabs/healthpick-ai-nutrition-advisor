from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from healthpick_api.config import Settings
from healthpick_api.main import create_app
from pydantic import ValidationError


@pytest.fixture
def client() -> TestClient:
    app = create_app(
        Settings(
            app_env="test",
            web_origin="http://web.test",
            llm_mode="mock",
            embedding_mode="disabled",
            retrieval_mode="keyword",
        )
    )
    return TestClient(app, raise_server_exceptions=False)


def test_health_is_live_without_external_dependencies(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "healthpick-api"
    assert body["dependencies"]["database"]["status"] == "not_checked"
    assert body["dependencies"]["llm"]["status"] == "mock"
    assert body["modes"] == {
        "llm": "mock",
        "embedding": "disabled",
        "retrieval": "keyword",
    }
    assert "api_key" not in response.text.lower()


def test_request_id_is_stable_and_exposed(client: TestClient) -> None:
    request_id = "d0327ef1-f5a7-4442-b803-f946045d725b"
    response = client.get("/healthz", headers={"X-Request-ID": request_id})
    assert response.headers["X-Request-ID"] == request_id
    assert response.json()["request_id"] == request_id
    UUID(response.json()["request_id"])


def test_invalid_request_id_is_replaced(client: TestClient) -> None:
    response = client.get("/healthz", headers={"X-Request-ID": "not-a-uuid"})
    UUID(response.headers["X-Request-ID"])
    assert response.headers["X-Request-ID"] != "not-a-uuid"


def test_cors_allows_only_configured_web_origin(client: TestClient) -> None:
    allowed = client.options(
        "/healthz",
        headers={
            "Origin": "http://web.test",
            "Access-Control-Request-Method": "GET",
        },
    )
    denied = client.options(
        "/healthz",
        headers={
            "Origin": "http://untrusted.test",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert allowed.headers["access-control-allow-origin"] == "http://web.test"
    assert "access-control-allow-origin" not in denied.headers


def test_openapi_contains_health_chat_and_shared_contracts(client: TestClient) -> None:
    document = client.get("/openapi.json").json()
    assert "/healthz" in document["paths"]
    assert "/v1/chat/stream" in document["paths"]
    schemas = document["components"]["schemas"]
    for name in (
        "ChatRequest",
        "ChatFinalEvent",
        "Citation",
        "SafetyResult",
        "ModelInfo",
        "ErrorResponse",
    ):
        assert name in schemas


def test_chat_mock_sse_is_explicitly_disclosed(client: TestClient) -> None:
    response = client.post(
        "/v1/chat/stream",
        json={"conversation_id": "demo", "message": "请给我一个减脂方案"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: final" in response.text
    assert "[MOCK RESPONSE — NOT REAL MODEL OUTPUT]" in response.text


def test_validation_and_404_use_stable_error_contract(client: TestClient) -> None:
    invalid = client.post("/v1/chat/stream", json={"conversation_id": "demo", "message": ""})
    missing = client.get("/does-not-exist")
    assert invalid.status_code == 422
    assert invalid.json()["code"] == "validation_error"
    assert invalid.json()["details"]
    assert missing.status_code == 404
    assert missing.json()["code"] == "not_found"
    for response in (invalid, missing):
        assert set(response.json()) >= {"request_id", "code", "message", "retryable"}


def test_production_cannot_start_with_mock_llm() -> None:
    with pytest.raises(ValidationError, match="LLM_MODE=mock is forbidden"):
        Settings(app_env="production", llm_mode="mock")
