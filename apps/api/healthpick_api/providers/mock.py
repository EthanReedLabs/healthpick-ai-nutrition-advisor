"""Deterministic development provider that is impossible to mistake for Real."""

from __future__ import annotations

import re

from .base import LLMRequest, LLMResult

EVIDENCE_ID = re.compile(r"\[EVIDENCE ([ABC]-p\d{2}-c\d{2})\]")


class MockLLMProvider:
    mode = "mock"
    provider_name = "healthpick_mock"

    def __init__(self, model_name: str = "mock-healthpick-v1") -> None:
        self.model_name = model_name

    async def generate(self, request: LLMRequest) -> LLMResult:
        user_messages = [item.content for item in request.messages if item.role == "user"]
        latest = user_messages[-1].strip() if user_messages else "(empty user message)"
        evidence_ids = EVIDENCE_ID.findall(latest)
        reference = f"【{evidence_ids[0]}】" if evidence_ids else ""
        return LLMResult(
            content=(
                "[MOCK RESPONSE — NOT REAL MODEL OUTPUT] "
                f"这是仅用于开发联调的确定性回答。{reference}"
            ),
            provider=self.provider_name,
            model=self.model_name,
            mode=self.mode,
            latency_ms=0,
            finish_reason="mock_complete",
            metadata={"disclosure": "mock_only"},
        )

    async def aclose(self) -> None:
        return None
