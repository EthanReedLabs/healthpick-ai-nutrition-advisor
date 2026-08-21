"""Serialize an already validated final result as ordered SSE events."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from .pipeline import ChatExecution


async def stream_chat_events(execution: ChatExecution) -> AsyncIterator[str]:
    final = execution.final
    yield _event(
        "meta",
        {
            "request_id": final.request_id,
            "route": final.route,
            "model_mode": final.model.mode,
            "session_mode": execution.session_mode,
            "retrieval_mode": execution.trace.mode if execution.trace else "not_used",
        },
    )
    for citation in final.citations:
        yield _event("citation", citation.model_dump(mode="json"))
    for delta in _chunks(final.answer, size=48):
        yield _event("token", {"delta": delta})
        await asyncio.sleep(0)
    yield _event("final", final.model_dump(mode="json"))


def _event(name: str, payload: dict[str, object]) -> str:
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return f"event: {name}\ndata: {data}\n\n"


def _chunks(value: str, *, size: int) -> list[str]:
    return [value[index : index + size] for index in range(0, len(value), size)]
