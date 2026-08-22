"""Exercise account claim and authorization against a real PostgreSQL database."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from fastapi.testclient import TestClient  # noqa: E402
from healthpick_api.config import Settings  # noqa: E402
from healthpick_api.main import create_app  # noqa: E402
from psycopg import connect  # noqa: E402
from psycopg.rows import dict_row  # noqa: E402

DEFAULT_DATABASE_URL = "postgresql://healthpick:healthpick-local-only@127.0.0.1:54329/healthpick"


def run(database_url: str) -> dict[str, object]:
    suffix = uuid4().hex[:12]
    first_email = f"p06-first-{suffix}@example.test"
    second_email = f"p06-second-{suffix}@example.test"
    password = "p06-competition-password"
    user_ids: list[str] = []
    session_ids: list[str] = []
    checks: dict[str, bool] = {}

    app = create_app(
        Settings(
            app_env="test",
            web_origin="http://web.test",
            database_url=database_url,
            conversation_store_mode="postgres",
            llm_mode="mock",
            embedding_mode="disabled",
            retrieval_mode="keyword",
        )
    )

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            anonymous = client.post("/v1/sessions/anonymous")
            checks["anonymous_session_created"] = anonymous.status_code == 201
            session_id = anonymous.json()["session_id"]
            session_ids.append(session_id)

            conversation = client.post(
                "/v1/conversations",
                json={"session_id": session_id, "title": "P06 迁移前历史"},
            )
            checks["pre_claim_history_created"] = conversation.status_code == 201

            registered = client.post(
                "/v1/auth/register",
                json={
                    "email": first_email,
                    "password": password,
                    "anonymous_session_id": session_id,
                },
            )
            first = registered.json()
            checks["registration_succeeded"] = registered.status_code == 201
            checks["canonical_session_preserved"] = first.get("session_id") == session_id
            user_ids.append(first["user_id"])
            first_headers = {"Authorization": f"Bearer {first['access_token']}"}

            anonymous_read = client.get("/v1/conversations", params={"session_id": session_id})
            checks["claimed_history_requires_bearer"] = (
                anonymous_read.status_code == 401
                and anonymous_read.json().get("code") == "authentication_required"
            )

            authorized_read = client.get(
                "/v1/conversations",
                params={"session_id": session_id},
                headers=first_headers,
            )
            checks["claimed_history_preserved"] = (
                authorized_read.status_code == 200
                and authorized_read.json()["items"][0]["title"] == "P06 迁移前历史"
            )

            renamed = client.patch(
                f"/v1/conversations/{conversation.json()['conversation_id']}",
                json={"session_id": session_id, "title": "P06 已持久化新标题"},
                headers=first_headers,
            )
            checks["authorized_rename_succeeded"] = (
                renamed.status_code == 200 and renamed.json().get("title") == "P06 已持久化新标题"
            )

            second_anonymous = client.post("/v1/sessions/anonymous").json()
            second_session_id = second_anonymous["session_id"]
            session_ids.append(second_session_id)
            second_registered = client.post(
                "/v1/auth/register",
                json={
                    "email": second_email,
                    "password": password,
                    "anonymous_session_id": second_session_id,
                },
            ).json()
            user_ids.append(second_registered["user_id"])
            cross_read = client.get(
                "/v1/conversations",
                params={"session_id": session_id},
                headers={"Authorization": f"Bearer {second_registered['access_token']}"},
            )
            checks["cross_account_access_denied"] = (
                cross_read.status_code == 403
                and cross_read.json().get("code") == "session_access_denied"
            )

            logged_in = client.post(
                "/v1/auth/login", json={"email": first_email, "password": password}
            )
            checks["login_returns_canonical_session"] = (
                logged_in.status_code == 200 and logged_in.json().get("session_id") == session_id
            )
            login_headers = {"Authorization": f"Bearer {logged_in.json()['access_token']}"}

            exported = client.get("/v1/account/export", headers=login_headers)
            export_payload = exported.json()
            exported_text = exported.text.lower()
            inventory = export_payload.get("inventory", {})
            inventory_sum = sum(
                inventory.get(key, -1)
                for key in (
                    "users",
                    "auth_sessions",
                    "anonymous_sessions",
                    "conversations",
                    "conversation_turns",
                )
            )
            checks["account_export_covers_personal_tables"] = (
                exported.status_code == 200
                and inventory.get("users") == 1
                and inventory.get("anonymous_sessions") == 1
                and inventory.get("conversations") == 1
                and inventory.get("total_records") == inventory_sum
                and export_payload.get("conversations", [{}])[0].get("title")
                == "P06 已持久化新标题"
            )
            checks["account_export_excludes_secrets"] = (
                "password_hash" not in exported_text
                and "token_hash" not in exported_text
                and password not in exported_text
            )
            checks["account_export_excludes_static_knowledge"] = (
                "knowledge_chunks" in export_payload.get("excluded_static_data", [])
                and "knowledge_chunks" not in export_payload
            )

            logout = client.post("/v1/auth/logout", headers=first_headers)
            revoked = client.get("/v1/auth/me", headers=first_headers)
            checks["logout_revokes_presented_token"] = (
                logout.status_code == 204
                and revoked.status_code == 401
                and revoked.json().get("code") == "invalid_access_token"
            )

            with connect(database_url, row_factory=dict_row) as connection:
                row = connection.execute(
                    """
                    SELECT u.password_hash, s.user_id,
                           bool_and(length(a.token_hash) = 64) AS token_hashes_are_sha256
                    FROM users u
                    JOIN anonymous_sessions s ON s.user_id = u.id
                    JOIN auth_sessions a ON a.user_id = u.id
                    WHERE u.id = %s
                    GROUP BY u.password_hash, s.user_id
                    """,
                    (user_ids[0],),
                ).fetchone()
                checks["password_is_scrypt_hash_only"] = bool(
                    row
                    and str(row["password_hash"]).startswith("scrypt$")
                    and row["password_hash"] != password
                )
                checks["tokens_are_sha256_hashes_only"] = bool(
                    row and row["token_hashes_are_sha256"]
                )
                persisted_title = connection.execute(
                    "SELECT title FROM conversations WHERE id = %s",
                    (conversation.json()["conversation_id"],),
                ).fetchone()
                checks["rename_persisted_in_database"] = bool(
                    persisted_title and persisted_title["title"] == "P06 已持久化新标题"
                )

            wrong_delete = client.request(
                "DELETE",
                "/v1/account",
                headers=login_headers,
                json={"password": "wrong-delete-password"},
            )
            checks["account_delete_requires_password_reentry"] = (
                wrong_delete.status_code == 401
                and client.get("/v1/auth/me", headers=login_headers).status_code == 200
            )
            deleted = client.request(
                "DELETE",
                "/v1/account",
                headers=login_headers,
                json={"password": password},
            )
            checks["account_delete_succeeded"] = deleted.status_code == 204
            deleted_login = client.post(
                "/v1/auth/login", json={"email": first_email, "password": password}
            )
            checks["deleted_account_cannot_login"] = deleted_login.status_code == 401

            with connect(database_url, row_factory=dict_row) as connection:
                remaining = connection.execute(
                    """
                    SELECT
                      (SELECT count(*) FROM users WHERE id = %s) AS users,
                      (SELECT count(*) FROM auth_sessions WHERE user_id = %s) AS auth_sessions,
                      (SELECT count(*) FROM anonymous_sessions WHERE id = %s) AS sessions,
                      (SELECT count(*) FROM conversations WHERE session_id = %s) AS conversations,
                      (SELECT count(*) FROM conversation_turns
                         WHERE conversation_id = %s) AS turns,
                      (SELECT count(*) FROM knowledge_chunks) AS knowledge_chunks
                    """,
                    (
                        user_ids[0],
                        user_ids[0],
                        session_id,
                        session_id,
                        conversation.json()["conversation_id"],
                    ),
                ).fetchone()
                assert remaining is not None
                checks["account_delete_clears_same_personal_tables"] = all(
                    remaining[key] == 0
                    for key in ("users", "auth_sessions", "sessions", "conversations", "turns")
                )
                checks["account_delete_preserves_static_knowledge"] = (
                    remaining["knowledge_chunks"] > 0
                )

        return {
            "status": "PASS" if all(checks.values()) else "FAIL",
            "generated_at": datetime.now(UTC).isoformat(),
            "database_target": "127.0.0.1:54329/healthpick",
            "checks": checks,
            "check_count": len(checks),
        }
    finally:
        if user_ids or session_ids:
            with connect(database_url, autocommit=True) as connection:
                if user_ids:
                    connection.execute("DELETE FROM users WHERE id = ANY(%s)", (user_ids,))
                if session_ids:
                    connection.execute(
                        "DELETE FROM anonymous_sessions WHERE id = ANY(%s)",
                        (session_ids,),
                    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", default=DEFAULT_DATABASE_URL)
    args = parser.parse_args()
    result = run(args.database_url)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
