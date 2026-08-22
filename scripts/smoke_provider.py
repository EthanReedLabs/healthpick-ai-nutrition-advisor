"""Produce auditable evidence for the explicit development Mock provider."""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from healthpick_api.config import Settings  # noqa: E402
from healthpick_api.providers import (  # noqa: E402
    LLMMessage,
    LLMRequest,
    build_llm_provider,
)

OUTPUT = ROOT / "docs" / "evidence" / "phase-03-provider-runtime.json"


async def main() -> None:
    settings = Settings(
        app_env="test",
        llm_mode="mock",
        llm_model="mock-healthpick-v1",
        _env_file=None,
    )
    provider = build_llm_provider(settings)
    result = await provider.generate(
        LLMRequest(
            messages=(LLMMessage(role="user", content="provider smoke"),),
            request_id="provider-smoke",
        )
    )
    await provider.aclose()

    assert result.mode == "mock"
    assert result.content.startswith("[MOCK RESPONSE — NOT REAL MODEL OUTPUT]")
    assert result.metadata.get("disclosure") == "mock_only"

    evidence = {
        "schema_version": 1,
        "task_id": "P03-02",
        "checked_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "configured_mode": settings.llm_mode,
        "provider": result.provider,
        "model": result.model,
        "result_mode": result.mode,
        "disclosure": result.metadata["disclosure"],
        "content_prefix": "[MOCK RESPONSE — NOT REAL MODEL OUTPUT]",
        "real_adapter": {
            "implemented": True,
            "external_call_executed": False,
            "external_call_action": "ACTION-02",
        },
        "result": "pass",
    }
    OUTPUT.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    asyncio.run(main())
