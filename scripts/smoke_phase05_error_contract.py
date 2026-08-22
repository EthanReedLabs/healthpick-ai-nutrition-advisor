"""Runtime smoke for Phase 05 request boundaries, error classes, and timeouts."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import httpx2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from fastapi.testclient import TestClient  # noqa: E402
from healthpick_api.chat import (  # noqa: E402
    ChatPipeline,
    ConversationStoreError,
    EphemeralConversationStore,
    PostgresConversationStore,
)
from healthpick_api.config import Settings  # noqa: E402
from healthpick_api.main import create_app  # noqa: E402
from healthpick_api.providers import LLMRequest, LLMResult  # noqa: E402
from healthpick_api.retrieval import KnowledgeIndex  # noqa: E402

DEFAULT_DATABASE_URL = "postgresql://healthpick:healthpick-local-only@127.0.0.1:54329/healthpick"
REQUEST_ID = "a3f69d40-3ed2-44f2-8552-c59cdf47d22b"
DEFAULT_API_ORIGIN = "http://127.0.0.1:8010"


class SlowProvider:
    mode = "mock"
    provider_name = "phase05-timeout-smoke"
    model_name = "slow-provider"

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


def app_contract_smoke() -> dict[str, object]:
    settings = Settings(
        app_env="test",
        web_origin="http://web.test",
        llm_mode="mock",
        embedding_mode="disabled",
        retrieval_mode="keyword",
        conversation_store_mode="ephemeral",
        _env_file=None,
    )
    with TestClient(create_app(settings), raise_server_exceptions=False) as client:
        session_id = client.post("/v1/sessions/anonymous").json()["session_id"]
        whitespace = client.post(
            "/v1/chat/stream",
            json={"conversation_id": "demo", "message": " \n "},
            headers={"X-Request-ID": REQUEST_ID},
        )
        oversized = client.post(
            "/v1/chat/stream",
            json={"conversation_id": "demo", "message": "x" * 33_000},
            headers={"X-Request-ID": REQUEST_ID},
        )
        blank_title = client.post(
            "/v1/conversations",
            json={"session_id": session_id, "title": "   "},
        )
        invalid_limit = client.get(
            "/v1/conversations", params={"session_id": session_id, "limit": 101}
        )
        method_not_allowed = client.put("/healthz", json={})

    checks = {
        "whitespace_message_422": whitespace.status_code == 422
        and whitespace.json().get("code") == "validation_error",
        "oversized_body_413": oversized.status_code == 413
        and oversized.json().get("code") == "request_body_too_large",
        "request_id_round_trip": oversized.json().get("request_id") == REQUEST_ID
        and oversized.headers.get("X-Request-ID") == REQUEST_ID,
        "blank_title_422": blank_title.status_code == 422
        and blank_title.json().get("code") == "validation_error",
        "list_limit_422": invalid_limit.status_code == 422
        and invalid_limit.json().get("code") == "validation_error",
        "method_405_stable": method_not_allowed.status_code == 405
        and method_not_allowed.json().get("code") == "http_error",
        "no_stack_or_secret_leak": all(
            "traceback" not in response.text.lower()
            and "healthpick-local-only" not in response.text
            for response in (
                whitespace,
                oversized,
                blank_title,
                invalid_limit,
                method_not_allowed,
            )
        ),
    }
    return {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}


def provider_timeout_smoke() -> dict[str, object]:
    conversations = EphemeralConversationStore()
    pipeline = ChatPipeline(
        provider=SlowProvider(),
        index=KnowledgeIndex.load_default(),
        conversations=conversations,
        generation_timeout_seconds=0.01,
    )
    settings = Settings(
        app_env="test",
        llm_mode="mock",
        embedding_mode="disabled",
        retrieval_mode="keyword",
        _env_file=None,
    )
    with TestClient(
        create_app(settings, chat_pipeline=pipeline), raise_server_exceptions=False
    ) as client:
        response = client.post(
            "/v1/chat/stream",
            json={
                "conversation_id": "timeout-smoke",
                "message": "膳食纤维有什么营养作用？",
            },
            headers={"X-Request-ID": REQUEST_ID},
        )

    checks = {
        "provider_timeout_504": response.status_code == 504,
        "distinct_timeout_code": response.json().get("code") == "provider_timeout",
        "timeout_retryable": response.json().get("retryable") is True,
        "timeout_not_persisted": conversations._conversations.get("timeout-smoke", ()) == (),
    }
    return {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}


def live_api_smoke(api_origin: str) -> dict[str, object]:
    with httpx2.Client(timeout=15) as client:
        health = client.get(f"{api_origin}/healthz")
        whitespace = client.post(
            f"{api_origin}/v1/chat/stream",
            json={"conversation_id": "demo", "message": " \n "},
            headers={"X-Request-ID": REQUEST_ID},
        )
        oversized = client.post(
            f"{api_origin}/v1/chat/stream",
            json={"conversation_id": "demo", "message": "x" * 33_000},
            headers={"X-Request-ID": REQUEST_ID},
        )
    checks = {
        "live_health_ok": health.status_code == 200 and health.json().get("status") == "ok",
        "live_database_ready": health.json()
        .get("dependencies", {})
        .get("database", {})
        .get("status")
        == "configured",
        "live_whitespace_422": whitespace.status_code == 422
        and whitespace.json().get("code") == "validation_error",
        "live_oversized_413": oversized.status_code == 413
        and oversized.json().get("code") == "request_body_too_large",
        "live_request_id_round_trip": oversized.json().get("request_id") == REQUEST_ID
        and oversized.headers.get("X-Request-ID") == REQUEST_ID,
    }
    return {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}


async def database_timeout_smoke(database_url: str) -> dict[str, object]:
    store = PostgresConversationStore(database_url, statement_timeout_ms=100)

    def delayed_query() -> None:
        with store._connect() as connection:
            connection.execute("SELECT pg_sleep(0.2)")

    error: ConversationStoreError | None = None
    try:
        await store._run(delayed_query)
    except ConversationStoreError as caught:
        error = caught

    checks = {
        "statement_timeout_enforced": error is not None,
        "database_timeout_distinct": error is not None
        and error.code == "conversation_store_timeout",
        "database_timeout_retryable": error is not None and error.retryable,
    }
    return {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--evidence",
        default="docs/evidence/phase-05-p05-02-error-contract.json",
    )
    parser.add_argument("--api-origin", default=DEFAULT_API_ORIGIN)
    args = parser.parse_args()
    database_url = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
    sections = {
        "app_contract": app_contract_smoke(),
        "live_api": live_api_smoke(args.api_origin),
        "provider_timeout": provider_timeout_smoke(),
        "database_timeout": asyncio.run(database_timeout_smoke(database_url)),
    }
    status = "PASS" if all(item["status"] == "PASS" for item in sections.values()) else "FAIL"
    evidence = {
        "schema_version": 1,
        "evidence_id": "PHASE-05-P05-02-ERROR-CONTRACT",
        "captured_at": datetime.now().astimezone().isoformat(),
        "database_target": "127.0.0.1:54329/healthpick",
        "api_origin": args.api_origin,
        **sections,
        "status": status,
    }
    target = ROOT / args.evidence
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
