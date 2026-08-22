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
            llm_model="mock-v1",
            embedding_mode="disabled",
            retrieval_mode="keyword",
            _env_file=None,
        )
    )
    return TestClient(app, raise_server_exceptions=False)


def test_health_is_live_without_external_dependencies(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "healthpick-api"
    assert body["dependencies"]["database"]["status"] == "disabled"
    assert body["dependencies"]["database"]["detail"] == "ephemeral conversation mode"
    assert body["dependencies"]["llm"]["status"] == "mock"
    assert body["modes"] == {
        "llm": "mock",
        "embedding": "disabled",
        "retrieval": "keyword",
    }
    assert "api_key" not in response.text.lower()


def test_transparency_discloses_runtime_and_source_boundaries_without_secrets(
    client: TestClient,
) -> None:
    response = client.get("/v1/transparency")
    assert response.status_code == 200
    body = response.json()
    assert body["model"] == {
        "provider": "healthpick_mock",
        "name": "mock-v1",
        "mode": "mock",
    }
    assert body["failover"] == {
        "enabled": False,
        "policy": "retryable_or_invalid_response",
        "fallback": None,
    }
    assert body["embedding"]["mode"] == "disabled"
    assert body["retrieval_mode"] == "keyword"
    assert body["conversation_store"] == "ephemeral"
    assert body["profile_persistence"] == "ephemeral"
    assert {item["source"] for item in body["sources"]} == {"A", "B", "C"}
    source_c = next(item for item in body["sources"] if item["source"] == "C")
    assert "不得作为营养事实" in source_c["forbidden_use"]
    lowered = response.text.lower()
    assert "api_key" not in lowered
    assert "base_url" not in lowered
    assert "authorization" not in lowered


def test_evaluation_summary_is_frozen_and_secret_free(client: TestClient) -> None:
    response = client.get("/v1/evaluation/summary")
    assert response.status_code == 200
    body = response.json()
    assert body["automatic_status"] == "PASS"
    assert body["overall_status"] == "PASS"
    assert body["gates_passed"] == body["gates_total"] == 9
    assert body["case_count"] == 72
    assert body["turn_count"] == 80
    assert body["manual_review"] == {
        "status": "PASS",
        "action": "ACTION-06 CLOSED",
        "case_count": 53,
    }
    assert body["first_attempt_preserved"] is True
    lowered = response.text.lower()
    for forbidden in ("api_origin", "base_url", "api_key", "authorization", "git", "dirty"):
        assert forbidden not in lowered


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
    assert "/v1/chat/cancel/{request_id}" in document["paths"]
    assert "/v1/profile/assess" in document["paths"]
    assert "/v1/transparency" in document["paths"]
    assert "/v1/evaluation/summary" in document["paths"]
    schemas = document["components"]["schemas"]
    for name in (
        "ChatRequest",
        "ChatFinalEvent",
        "Citation",
        "SafetyResult",
        "ModelInfo",
        "ErrorResponse",
        "ProfilePatch",
        "ProfileAssessment",
        "BmiEstimate",
        "TransparencyResponse",
        "EvaluationSummaryResponse",
        "RetrievalTraceView",
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
    invalid = client.post("/v1/chat/stream", json={"conversation_id": "demo", "message": " \n "})
    missing = client.get("/does-not-exist")
    assert invalid.status_code == 422
    assert invalid.json()["code"] == "validation_error"
    assert invalid.json()["details"]
    assert missing.status_code == 404
    assert missing.json()["code"] == "not_found"
    for response in (invalid, missing):
        assert set(response.json()) >= {"request_id", "code", "message", "retryable"}


def test_request_body_limit_fails_before_validation_with_stable_413(
    client: TestClient,
) -> None:
    request_id = "a3f69d40-3ed2-44f2-8552-c59cdf47d22b"
    response = client.post(
        "/v1/chat/stream",
        json={"conversation_id": "demo", "message": "x" * 33_000},
        headers={"X-Request-ID": request_id},
    )
    assert response.status_code == 413
    assert response.json() == {
        "request_id": request_id,
        "code": "request_body_too_large",
        "message": "请求体超过允许大小。",
        "retryable": False,
        "details": None,
    }
    assert response.headers["X-Request-ID"] == request_id


def test_string_limits_trim_before_validation(client: TestClient) -> None:
    session = client.post("/v1/sessions/anonymous").json()["session_id"]
    blank_title = client.post("/v1/conversations", json={"session_id": session, "title": "   "})
    too_long_message = client.post(
        "/v1/chat/stream",
        json={"conversation_id": "demo", "message": "x" * 2001},
    )
    assert blank_title.status_code == 422
    assert blank_title.json()["code"] == "validation_error"
    assert too_long_message.status_code == 422
    assert too_long_message.json()["code"] == "validation_error"


def test_method_not_allowed_uses_stable_error_contract(client: TestClient) -> None:
    response = client.put("/healthz", json={})
    assert response.status_code == 405
    assert response.json()["code"] == "http_error"
    assert set(response.json()) >= {"request_id", "code", "message", "retryable"}


def test_production_cannot_start_with_mock_llm() -> None:
    with pytest.raises(ValidationError, match="LLM_MODE=mock is forbidden"):
        Settings(app_env="production", llm_mode="mock")
