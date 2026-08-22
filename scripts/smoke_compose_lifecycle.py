"""Verify an isolated Compose stack before and after a service restart."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import httpx2
from psycopg import connect
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE = ROOT / "output" / "runtime" / "phase-05-p05-04-compose-state.json"
DEFAULT_EVIDENCE = ROOT / "docs" / "evidence" / "phase-05-p05-04-compose.json"
EXPECTED_MIGRATION_VERSIONS = sorted(
    path.name.split("_", 1)[0]
    for path in (ROOT / "infra" / "migrations").glob("[0-9][0-9][0-9]_*.sql")
)
EXPECTED_COUNTS = {
    "knowledge_documents": 3,
    "knowledge_pages": 18,
    "knowledge_chunks": 67,
    "food_facts": 31,
    "plan_rules": 37,
    "platform_facts": 12,
}


def parse_sse(body: str) -> list[tuple[str, dict[str, Any]]]:
    events: list[tuple[str, dict[str, Any]]] = []
    for block in body.replace("\r\n", "\n").strip().split("\n\n"):
        lines = block.splitlines()
        event = next((line[7:] for line in lines if line.startswith("event: ")), None)
        data = [line[6:] for line in lines if line.startswith("data: ")]
        if event is None or not data:
            raise RuntimeError("invalid SSE event block")
        events.append((event, json.loads("\n".join(data))))
    return events


def wait_for_url(client: httpx2.Client, url: str, marker: str | None = None) -> dict[str, Any]:
    deadline = time.monotonic() + 90
    last_error = "not attempted"
    while time.monotonic() < deadline:
        try:
            response = client.get(url)
            response.raise_for_status()
            if marker is not None and marker not in response.text:
                raise RuntimeError(f"response does not contain {marker!r}")
            return (
                response.json()
                if response.headers.get("content-type", "").startswith("application/json")
                else {"status_code": response.status_code, "marker": marker}
            )
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            time.sleep(2)
    raise RuntimeError(f"{url} did not become ready: {last_error}")


def database_snapshot(database_url: str) -> dict[str, Any]:
    with connect(database_url, row_factory=dict_row) as connection:
        counts = {
            table: int(
                connection.execute(f"SELECT count(*) AS count FROM {table}").fetchone()["count"]
            )
            for table in EXPECTED_COUNTS
        }
        migrations = connection.execute(
            """
            SELECT version, filename, sha256, execution
            FROM schema_migrations
            ORDER BY version
            """
        ).fetchall()
        successful_ingestion_runs = int(
            connection.execute(
                """
                SELECT count(*) AS count
                FROM knowledge_ingestion_runs
                WHERE status = 'passed'
                """
            ).fetchone()["count"]
        )

    if counts != EXPECTED_COUNTS:
        raise RuntimeError(f"seed counts differ: {counts}")
    if [row["version"] for row in migrations] != EXPECTED_MIGRATION_VERSIONS:
        raise RuntimeError("migration registry is incomplete")
    if any(row["execution"] != "applied" for row in migrations):
        raise RuntimeError("empty-stack migrations were not executed normally")
    if successful_ingestion_runs < 1:
        raise RuntimeError("no successful ingestion run found")

    return {
        "counts": counts,
        "migrations": [dict(row) for row in migrations],
        "successful_ingestion_runs": successful_ingestion_runs,
    }


def runtime_snapshot(
    client: httpx2.Client,
    *,
    api_origin: str,
    web_origin: str,
    database_url: str,
) -> dict[str, Any]:
    health = wait_for_url(client, f"{api_origin}/healthz")
    wait_for_url(client, web_origin, "HealthPick")
    if health.get("modes") != {
        "llm": "real",
        "embedding": "disabled",
        "retrieval": "keyword",
    }:
        raise RuntimeError(f"unexpected API modes: {health.get('modes')}")
    if health.get("dependencies", {}).get("database", {}).get("status") != "configured":
        raise RuntimeError("API database dependency is not configured")
    return {
        "api_health": health,
        "web": {"status_code": 200, "healthpick_marker": True},
        "database": database_snapshot(database_url),
    }


def create_persisted_turn(client: httpx2.Client, api_origin: str) -> dict[str, Any]:
    session_response = client.post(f"{api_origin}/v1/sessions/anonymous")
    session_response.raise_for_status()
    session_id = session_response.json()["session_id"]

    conversation_response = client.post(
        f"{api_origin}/v1/conversations",
        json={"session_id": session_id, "title": "P05-04 Compose 持久化验收"},
    )
    conversation_response.raise_for_status()
    conversation_id = conversation_response.json()["conversation_id"]

    chat_response = client.post(
        f"{api_origin}/v1/chat/stream",
        json={
            "session_id": session_id,
            "conversation_id": conversation_id,
            "message": "膳食纤维有什么营养作用？",
        },
    )
    chat_response.raise_for_status()
    events = parse_sse(chat_response.text)
    if not events or events[-1][0] != "final":
        raise RuntimeError("chat stream did not end with final")
    final = events[-1][1]
    sources = {citation["source"] for citation in final.get("citations", [])}
    if final.get("route") != "nutrition" or not sources or not sources.issubset({"A", "B"}):
        raise RuntimeError("nutrition response violated source routing")

    detail_response = client.get(
        f"{api_origin}/v1/conversations/{conversation_id}",
        params={"session_id": session_id},
    )
    detail_response.raise_for_status()
    detail = detail_response.json()
    if detail.get("turn_count") != 1 or len(detail.get("turns", [])) != 1:
        raise RuntimeError("conversation turn was not persisted")

    return {
        "session_id": session_id,
        "conversation_id": conversation_id,
        "turn_id": final["turn_id"],
        "request_id": final["request_id"],
        "route": final["route"],
        "citation_sources": sorted(sources),
        "answer_sha256": hashlib.sha256(final["answer"].encode()).hexdigest(),
    }


def verify_persisted_turn(
    client: httpx2.Client, api_origin: str, state: dict[str, Any]
) -> dict[str, Any]:
    created = state["created_turn"]
    response = client.get(
        f"{api_origin}/v1/conversations/{created['conversation_id']}",
        params={"session_id": created["session_id"]},
    )
    response.raise_for_status()
    detail = response.json()
    turns = detail.get("turns", [])
    if detail.get("turn_count") != 1 or len(turns) != 1:
        raise RuntimeError("persisted conversation was not restored after restart")
    turn = turns[0]
    if turn.get("turn_id") != created["turn_id"] or turn.get("request_id") != created["request_id"]:
        raise RuntimeError("persisted turn identity changed after restart")
    persisted_response = turn.get("response") or {}
    model = persisted_response.get("model") or {}
    if model.get("mode") != "real":
        raise RuntimeError("persisted response is not backed by a real model")
    if (
        hashlib.sha256(persisted_response.get("answer", "").encode()).hexdigest()
        != created["answer_sha256"]
    ):
        raise RuntimeError("persisted answer changed after restart")
    return {
        "conversation_id": created["conversation_id"],
        "turn_id": turn["turn_id"],
        "request_id": turn["request_id"],
        "turn_count": detail["turn_count"],
        "identity_preserved": True,
        "answer_preserved": True,
        "model": model,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run(
    stage: Literal["before", "after"],
    *,
    evidence_id: str,
    api_origin: str,
    web_origin: str,
    database_url: str,
    state_path: Path,
    evidence_path: Path,
) -> dict[str, Any]:
    with httpx2.Client(timeout=120) as client:
        snapshot = runtime_snapshot(
            client,
            api_origin=api_origin,
            web_origin=web_origin,
            database_url=database_url,
        )
        if stage == "before":
            report = {
                "schema_version": 1,
                "evidence_id": evidence_id,
                "captured_at": datetime.now(UTC).isoformat(),
                "origins": {"api": api_origin, "web": web_origin},
                "before_restart": snapshot,
                "created_turn": create_persisted_turn(client, api_origin),
                "status": "PRE_RESTART_PASS",
            }
            write_json(state_path, report)
            return report

        state = json.loads(state_path.read_text(encoding="utf-8"))
        report = {
            **state,
            "captured_at": datetime.now(UTC).isoformat(),
            "after_restart": snapshot,
            "persistence": verify_persisted_turn(client, api_origin, state),
            "status": "PASS",
        }
        write_json(evidence_path, report)
        return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("before", "after"))
    parser.add_argument("--evidence-id", default="PHASE-05-P05-04-COMPOSE")
    parser.add_argument("--api-origin", default="http://127.0.0.1:18110")
    parser.add_argument("--web-origin", default="http://127.0.0.1:13110")
    parser.add_argument(
        "--database-url",
        default="postgresql://healthpick:healthpick-p0504-verify@127.0.0.1:55439/healthpick",
    )
    parser.add_argument("--state-path", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--evidence-path", type=Path, default=DEFAULT_EVIDENCE)
    args = parser.parse_args()
    try:
        report = run(
            args.stage,
            evidence_id=args.evidence_id,
            api_origin=args.api_origin,
            web_origin=args.web_origin,
            database_url=args.database_url,
            state_path=args.state_path,
            evidence_path=args.evidence_path,
        )
    except Exception as exc:
        print(f"Compose lifecycle smoke failed: {type(exc).__name__}: {exc}")
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
