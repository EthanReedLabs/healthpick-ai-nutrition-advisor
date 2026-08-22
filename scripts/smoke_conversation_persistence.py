"""Real PostgreSQL smoke for Phase 05 anonymous conversation persistence."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from fastapi.testclient import TestClient  # noqa: E402
from healthpick_api.chat import (  # noqa: E402
    ConversationStoreError,
    ConversationTurn,
    PostgresConversationStore,
)
from healthpick_api.config import Settings  # noqa: E402
from healthpick_api.main import create_app  # noqa: E402

DEFAULT_DATABASE_URL = "postgresql://healthpick:healthpick-local-only@127.0.0.1:54329/healthpick"


async def repository_smoke(database_url: str) -> dict[str, object]:
    store = PostgresConversationStore(database_url)
    owner = await store.create_session()
    attacker = await store.create_session()
    conversation = await store.create_conversation(owner.session_id)

    turns = [
        ConversationTurn(
            user_message=f"并发问题 {index}",
            assistant_message=f"并发回答 {index}",
            request_id=str(uuid4()),
            route="nutrition",
        )
        for index in range(5)
    ]
    persisted = await asyncio.gather(
        *(
            store.append(
                conversation.conversation_id,
                turn,
                session_id=owner.session_id,
            )
            for turn in turns
        )
    )
    replay = await store.append(
        conversation.conversation_id,
        turns[0],
        session_id=owner.session_id,
    )

    restarted_store = PostgresConversationStore(database_url)
    restored, restored_turns = await restarted_store.get_conversation(
        conversation.conversation_id, session_id=owner.session_id
    )

    ownership_code = None
    try:
        await restarted_store.get_conversation(
            conversation.conversation_id, session_id=attacker.session_id
        )
    except ConversationStoreError as exc:
        ownership_code = exc.code

    renamed = await restarted_store.rename_conversation(
        conversation.conversation_id,
        session_id=owner.session_id,
        title="并发持久化验收",
    )
    await restarted_store.clear(conversation.conversation_id, session_id=owner.session_id)
    context_after_clear = await restarted_store.history(
        conversation.conversation_id, session_id=owner.session_id
    )
    _, transcript_after_clear = await restarted_store.get_conversation(
        conversation.conversation_id, session_id=owner.session_id
    )
    await restarted_store.delete_conversation(
        conversation.conversation_id, session_id=owner.session_id
    )
    remaining = await restarted_store.list_conversations(owner.session_id)

    checks = {
        "canonical_ids": all(turn.turn_id for turn in persisted),
        "concurrent_turn_count": len(restored_turns) == 5,
        "idempotent_request_id": replay.turn_id == persisted[0].turn_id,
        "repository_reinstantiation_restored": restored.turn_count == 5,
        "ownership_fail_closed": ownership_code == "conversation_not_found",
        "rename_round_trip": renamed.title == "并发持久化验收",
        "safety_context_cleared": len(context_after_clear) == 0,
        "transcript_retained_after_context_clear": len(transcript_after_clear) == 5,
        "cascade_delete": len(remaining) == 0,
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "concurrent_turn_ids": [turn.turn_id for turn in persisted],
    }


def api_smoke(database_url: str) -> dict[str, object]:
    settings = Settings(
        app_env="test",
        web_origin="http://web.test",
        llm_mode="mock",
        llm_model="mock-healthpick-v1",
        embedding_mode="disabled",
        retrieval_mode="keyword",
        conversation_store_mode="postgres",
        database_url=database_url,
        _env_file=None,
    )
    with TestClient(create_app(settings), raise_server_exceptions=False) as client:
        health = client.get("/healthz")
        session = client.post("/v1/sessions/anonymous")
        session_id = session.json()["session_id"]
        conversation = client.post(
            "/v1/conversations",
            json={"session_id": session_id, "title": "新对话"},
        )
        conversation_id = conversation.json()["conversation_id"]
        chat = client.post(
            "/v1/chat/stream",
            json={
                "session_id": session_id,
                "conversation_id": conversation_id,
                "message": "膳食纤维有什么营养作用？",
            },
            headers={"X-Request-ID": str(uuid4())},
        )
        detail = client.get(
            f"/v1/conversations/{conversation_id}", params={"session_id": session_id}
        )
        deleted = client.delete(
            f"/v1/conversations/{conversation_id}", params={"session_id": session_id}
        )

    checks = {
        "health_database_configured": health.json()["dependencies"]["database"]["status"]
        == "configured",
        "session_created": session.status_code == 201,
        "conversation_created": conversation.status_code == 201,
        "chat_persisted": chat.status_code == 200 and detail.json().get("turn_count") == 1,
        "delete_completed": deleted.status_code == 204,
    }
    return {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--evidence",
        default="docs/evidence/phase-05-p05-01-postgres.json",
    )
    args = parser.parse_args()
    database_url = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
    repository = asyncio.run(repository_smoke(database_url))
    api = api_smoke(database_url)
    status = "PASS" if repository["status"] == api["status"] == "PASS" else "FAIL"
    evidence = {
        "schema_version": 1,
        "evidence_id": "PHASE-05-P05-01-POSTGRES",
        "captured_at": datetime.now().astimezone().isoformat(),
        "database_target": "127.0.0.1:54329/healthpick",
        "repository": repository,
        "api": api,
        "status": status,
    }
    target = ROOT / args.evidence
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
