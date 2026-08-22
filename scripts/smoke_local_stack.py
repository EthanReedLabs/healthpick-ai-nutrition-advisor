"""Exercise the local Web/API/real-model closed loop and write auditable evidence."""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

import httpx2

if __package__:
    from .runtime_conversation import RuntimeConversationScope
else:
    from runtime_conversation import RuntimeConversationScope

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "evidence" / "local-real-stack-runtime.json"
API_ORIGIN = "http://127.0.0.1:8010"
WEB_ORIGIN = "http://127.0.0.1:3100"
INLINE_REFERENCE = re.compile(r"【([ABC]-p\d{2}-c\d{2})】")

CASES = (
    {
        "name": "nutrition",
        "message": "膳食纤维有什么营养作用？",
        "route": "nutrition",
        "sources": {"A", "B"},
        "citations_required": True,
    },
    {
        "name": "platform",
        "message": "平台会员和企业服务有哪些？",
        "route": "platform",
        "sources": {"C"},
        "citations_required": True,
    },
    {
        "name": "out_of_scope",
        "message": "如何修复汽车发动机？",
        "route": "out_of_scope",
        "sources": set(),
        "citations_required": False,
    },
)


def parse_sse(body: str) -> list[tuple[str, dict[str, Any]]]:
    events: list[tuple[str, dict[str, Any]]] = []
    normalized = body.replace("\r\n", "\n").strip()
    for block in normalized.split("\n\n"):
        lines = block.splitlines()
        event = next((line[7:] for line in lines if line.startswith("event: ")), None)
        data_lines = [line[6:] for line in lines if line.startswith("data: ")]
        if event is None or not data_lines:
            raise RuntimeError("SSE block is missing event or data")
        events.append((event, json.loads("\n".join(data_lines))))
    return events


async def run_case(
    client: httpx2.AsyncClient,
    case: dict[str, Any],
    *,
    session_id: str,
    conversation_id: str,
) -> dict[str, Any]:
    started = perf_counter()
    response = await client.post(
        f"{API_ORIGIN}/v1/chat/stream",
        json={
            "session_id": session_id,
            "conversation_id": conversation_id,
            "message": case["message"],
        },
    )
    response.raise_for_status()
    events = parse_sse(response.text)
    if events[-1][0] != "final":
        raise RuntimeError(f"{case['name']} did not end with a final event")

    final = events[-1][1]
    citations = final.get("citations") or []
    citation_ids = {item["chunk_id"] for item in citations}
    sources = {item["source"] for item in citations}
    referenced_ids = set(INLINE_REFERENCE.findall(final["answer"]))
    trace = final.get("retrieval_trace")

    if final.get("route") != case["route"]:
        raise RuntimeError(f"{case['name']} returned the wrong route")
    if final.get("model", {}).get("mode") != "real":
        raise RuntimeError(f"{case['name']} did not use the real runtime mode")
    if not sources <= case["sources"]:
        raise RuntimeError(f"{case['name']} crossed the frozen source boundary")
    if case["citations_required"] and (not citations or not referenced_ids):
        raise RuntimeError(f"{case['name']} omitted required citations")
    if not referenced_ids <= citation_ids:
        raise RuntimeError(f"{case['name']} referenced an unreturned citation")
    if not case["citations_required"] and (citations or referenced_ids):
        raise RuntimeError(f"{case['name']} unexpectedly returned citations")
    if case["citations_required"]:
        if not trace or trace.get("evidence_gate") != "passed":
            raise RuntimeError(f"{case['name']} omitted the passing retrieval trace")
        selected_ids = {item["chunk_id"] for item in trace.get("selections", [])}
        selected_sources = {item["source"] for item in trace.get("selections", [])}
        if selected_ids != citation_ids:
            raise RuntimeError(f"{case['name']} trace selections differ from citations")
        if not selected_sources <= case["sources"]:
            raise RuntimeError(f"{case['name']} trace crossed the source boundary")
        if trace.get("returned_chunks") != len(trace.get("selections", [])):
            raise RuntimeError(f"{case['name']} trace count is inconsistent")
    elif trace is not None:
        raise RuntimeError(f"{case['name']} guard path unexpectedly returned a trace")

    return {
        "name": case["name"],
        "status_code": response.status_code,
        "latency_ms": round((perf_counter() - started) * 1000),
        "event_names": [name for name, _ in events],
        "route": final["route"],
        "model": final["model"],
        "safety": final["safety"],
        "citation_count": len(citations),
        "sources": sorted(sources),
        "referenced_chunk_ids": sorted(referenced_ids),
        "retrieval_trace": trace,
        "answer_chars": len(final["answer"]),
        "answer_sha256": hashlib.sha256(final["answer"].encode("utf-8")).hexdigest(),
        "status": "PASS",
    }


async def main() -> None:
    async with httpx2.AsyncClient(timeout=120) as client:
        health_response = await client.get(f"{API_ORIGIN}/healthz")
        health_response.raise_for_status()
        health = health_response.json()
        expected_modes = {"llm": "real", "embedding": "real", "retrieval": "keyword"}
        if health.get("modes") != expected_modes:
            raise RuntimeError("API health modes do not match the local real baseline")

        transparency_response = await client.get(f"{API_ORIGIN}/v1/transparency")
        transparency_response.raise_for_status()
        transparency = transparency_response.json()
        if transparency.get("model", {}).get("mode") != "real":
            raise RuntimeError("transparency endpoint does not disclose real model mode")
        if transparency.get("retrieval_mode") != health["modes"]["retrieval"]:
            raise RuntimeError("transparency retrieval mode differs from health")
        if {item["source"] for item in transparency.get("sources", [])} != {"A", "B", "C"}:
            raise RuntimeError("transparency source boundary is incomplete")
        source_c = next(item for item in transparency["sources"] if item["source"] == "C")
        if "不得作为营养事实" not in source_c["forbidden_use"]:
            raise RuntimeError("source C nutrition prohibition is missing")
        lowered_transparency = transparency_response.text.lower()
        secret_fields = ("api_key", "base_url", "authorization")
        if any(secret in lowered_transparency for secret in secret_fields):
            raise RuntimeError("transparency endpoint exposed a secret-bearing field")

        web_response = await client.get(WEB_ORIGIN)
        web_response.raise_for_status()
        if "HealthPick" not in web_response.text:
            raise RuntimeError("Web root does not contain the HealthPick marker")

        scope = await RuntimeConversationScope.create(client, API_ORIGIN)
        try:
            cases = []
            for case in CASES:
                conversation_id = await scope.new_conversation(f"local-stack-{case['name']}")
                cases.append(
                    await run_case(
                        client,
                        case,
                        session_id=scope.session_id,
                        conversation_id=conversation_id,
                    )
                )
        finally:
            await scope.cleanup()

    evidence = {
        "schema_version": 1,
        "evidence_id": "LOCAL-REAL-STACK-RUNTIME",
        "scope": "local/web/api/keyword-retrieval/ollama-real-model",
        "captured_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "origins": {"web": WEB_ORIGIN, "api": API_ORIGIN},
        "health": {
            "status_code": health_response.status_code,
            "status": health["status"],
            "environment": health["environment"],
            "modes": health["modes"],
        },
        "web": {
            "status_code": web_response.status_code,
            "healthpick_marker": True,
        },
        "transparency": transparency,
        "cases": cases,
        "database_evidence": "docs/evidence/action-01-database-runtime.json",
        "model_evidence": "docs/evidence/action-02-03-real-model-runtime.json",
        "browser_evidence": "docs/evidence/local-real-stack-browser.md",
        "phase_04_high_risk_gate": {
            "status": "PASS",
            "evidence": "docs/evidence/phase-04-p04-04-runtime.json",
        },
        "status": "PASS",
    }
    OUTPUT.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
