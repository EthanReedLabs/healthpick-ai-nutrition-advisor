from __future__ import annotations

from fastapi.testclient import TestClient
from healthpick_api.config import Settings
from healthpick_api.main import create_app


def _client() -> TestClient:
    return TestClient(
        create_app(
            Settings(
                app_env="test",
                web_origin="http://web.test",
                llm_mode="mock",
                embedding_mode="disabled",
                retrieval_mode="keyword",
            )
        ),
        raise_server_exceptions=False,
    )


def _anonymous_with_conversation(client: TestClient) -> tuple[str, str]:
    session_id = client.post("/v1/sessions/anonymous").json()["session_id"]
    conversation = client.post(
        "/v1/conversations",
        json={"session_id": session_id, "title": "迁移前历史"},
    )
    assert conversation.status_code == 201
    return session_id, conversation.json()["conversation_id"]


def test_registration_claims_anonymous_history_and_requires_bearer_afterward() -> None:
    client = _client()
    session_id, conversation_id = _anonymous_with_conversation(client)

    registered = client.post(
        "/v1/auth/register",
        json={
            "email": " Person@Example.COM ",
            "password": "correct horse battery staple",
            "anonymous_session_id": session_id,
        },
    )
    assert registered.status_code == 201
    body = registered.json()
    assert body["email"] == "person@example.com"
    assert body["session_id"] == session_id
    assert body["token_type"] == "bearer"
    assert body["access_token"]

    anonymous_read = client.get(
        f"/v1/conversations/{conversation_id}", params={"session_id": session_id}
    )
    assert anonymous_read.status_code == 401
    assert anonymous_read.json()["code"] == "authentication_required"

    headers = {"Authorization": f"Bearer {body['access_token']}"}
    migrated = client.get("/v1/conversations", params={"session_id": session_id}, headers=headers)
    assert migrated.status_code == 200
    assert migrated.json()["items"][0]["title"] == "迁移前历史"
    assert client.get("/v1/auth/me", headers=headers).json()["email"] == "person@example.com"


def test_login_returns_canonical_claimed_session_and_rejects_wrong_password() -> None:
    client = _client()
    session_id, _ = _anonymous_with_conversation(client)
    password = "ten-characters-minimum"
    registered = client.post(
        "/v1/auth/register",
        json={
            "email": "member@example.com",
            "password": password,
            "anonymous_session_id": session_id,
        },
    )
    assert registered.status_code == 201

    wrong = client.post(
        "/v1/auth/login",
        json={"email": "member@example.com", "password": "wrong-password-value"},
    )
    assert wrong.status_code == 401
    assert wrong.json()["code"] == "invalid_credentials"

    login = client.post(
        "/v1/auth/login",
        json={"email": " MEMBER@example.com ", "password": password},
    )
    assert login.status_code == 200
    assert login.json()["session_id"] == session_id
    assert login.json()["access_token"] != registered.json()["access_token"]


def test_claim_conflicts_and_cross_account_access_are_fail_closed() -> None:
    client = _client()
    first_session, _ = _anonymous_with_conversation(client)
    first = client.post(
        "/v1/auth/register",
        json={
            "email": "first@example.com",
            "password": "first-password-value",
            "anonymous_session_id": first_session,
        },
    )
    assert first.status_code == 201

    second_session, _ = _anonymous_with_conversation(client)
    second = client.post(
        "/v1/auth/register",
        json={
            "email": "second@example.com",
            "password": "second-password-value",
            "anonymous_session_id": second_session,
        },
    )
    assert second.status_code == 201

    duplicate_email = client.post(
        "/v1/auth/register",
        json={
            "email": "first@example.com",
            "password": "another-password-value",
            "anonymous_session_id": second_session,
        },
    )
    assert duplicate_email.status_code == 409

    denied = client.get(
        "/v1/conversations",
        params={"session_id": first_session},
        headers={"Authorization": f"Bearer {second.json()['access_token']}"},
    )
    assert denied.status_code == 403
    assert denied.json()["code"] == "session_access_denied"


def test_logout_revokes_only_the_presented_token() -> None:
    client = _client()
    session_id, _ = _anonymous_with_conversation(client)
    result = client.post(
        "/v1/auth/register",
        json={
            "email": "logout@example.com",
            "password": "logout-password-value",
            "anonymous_session_id": session_id,
        },
    ).json()
    headers = {"Authorization": f"Bearer {result['access_token']}"}

    assert client.post("/v1/auth/logout", headers=headers).status_code == 204
    expired = client.get("/v1/auth/me", headers=headers)
    assert expired.status_code == 401
    assert expired.json()["code"] == "invalid_access_token"


def test_auth_validation_and_cors_authorization_header() -> None:
    client = _client()
    invalid = client.post(
        "/v1/auth/register",
        json={"email": "not-an-email", "password": "short", "anonymous_session_id": "bad"},
    )
    assert invalid.status_code == 422
    assert invalid.json()["code"] == "validation_error"

    preflight = client.options(
        "/v1/auth/me",
        headers={
            "Origin": "http://web.test",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization",
        },
    )
    assert preflight.status_code == 200
    assert "authorization" in preflight.headers["access-control-allow-headers"].lower()


def test_account_export_and_delete_cover_the_same_personal_data_surface() -> None:
    client = _client()
    session_id, conversation_id = _anonymous_with_conversation(client)
    password = "privacy-delete-password"
    registered = client.post(
        "/v1/auth/register",
        json={
            "email": "privacy@example.com",
            "password": password,
            "anonymous_session_id": session_id,
        },
    ).json()
    headers = {"Authorization": f"Bearer {registered['access_token']}"}

    exported = client.get("/v1/account/export", headers=headers)
    assert exported.status_code == 200
    payload = exported.json()
    assert payload["user"]["email"] == "privacy@example.com"
    assert payload["inventory"] == {
        "users": 1,
        "auth_sessions": 1,
        "anonymous_sessions": 1,
        "conversations": 1,
        "conversation_turns": 0,
        "total_records": 4,
    }
    assert payload["conversations"][0]["conversation_id"] == conversation_id
    serialized = exported.text.lower()
    assert "password_hash" not in serialized
    assert "token_hash" not in serialized
    assert password not in serialized
    assert "knowledge_chunks" in payload["excluded_static_data"]

    wrong_password = client.request(
        "DELETE", "/v1/account", headers=headers, json={"password": "wrong-password-value"}
    )
    assert wrong_password.status_code == 401
    assert client.get("/v1/auth/me", headers=headers).status_code == 200

    deleted = client.request("DELETE", "/v1/account", headers=headers, json={"password": password})
    assert deleted.status_code == 204
    assert client.get("/v1/auth/me", headers=headers).status_code == 401
    assert (
        client.post(
            "/v1/auth/login", json={"email": "privacy@example.com", "password": password}
        ).status_code
        == 401
    )
    removed_session = client.post(
        "/v1/conversations", json={"session_id": session_id, "title": "不应恢复"}
    )
    assert removed_session.status_code == 404


def test_account_privacy_endpoints_require_authentication() -> None:
    client = _client()
    assert client.get("/v1/account/export").status_code == 401
    assert (
        client.request(
            "DELETE", "/v1/account", json={"password": "ten-characters-minimum"}
        ).status_code
        == 401
    )
