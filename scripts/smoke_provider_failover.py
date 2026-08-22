"""Inject primary and dual failures while using the real local model as backup."""

from __future__ import annotations

import asyncio
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from healthpick_api.config import Settings  # noqa: E402
from healthpick_api.providers import (  # noqa: E402
    LLMMessage,
    LLMRequest,
    ProviderRequestError,
    build_llm_provider,
)

OUTPUT = ROOT / "docs" / "evidence" / "phase-07-p07-03-failover.json"


def settings(*, fallback_url: str) -> Settings:
    return Settings(
        app_env="test",
        llm_mode="real",
        llm_provider="injected-primary",
        llm_base_url="http://127.0.0.1:1/v1",
        llm_api_key="injected-primary-key",
        llm_model="injected-primary-model",
        llm_timeout_seconds=1,
        llm_fallback_enabled=True,
        llm_fallback_provider="ollama-local-backup",
        llm_fallback_base_url=fallback_url,
        llm_fallback_api_key="ollama-local-only",
        llm_fallback_model="qwen2.5:3b-instruct",
        llm_fallback_timeout_seconds=30,
        _env_file=None,
    )


async def main() -> int:
    request = LLMRequest(
        messages=(LLMMessage(role="user", content="只回复：故障切换成功"),),
        request_id="p07-03-real-backup",
        temperature=0,
        max_tokens=32,
    )
    provider = build_llm_provider(settings(fallback_url="http://127.0.0.1:11434/v1"))
    result = await provider.generate(request)
    await provider.aclose()
    if result.metadata.get("failover") != "used" or result.mode != "real":
        raise RuntimeError("real backup failover was not disclosed")

    exhausted = build_llm_provider(settings(fallback_url="http://127.0.0.1:2/v1"))
    exhausted_code: str | None = None
    try:
        await exhausted.generate(request)
    except ProviderRequestError as exc:
        exhausted_code = exc.code
    finally:
        await exhausted.aclose()
    if exhausted_code != "provider_failover_exhausted":
        raise RuntimeError("dual failure did not use the stable exhausted code")

    evidence = {
        "schema_version": 1,
        "task_id": "P07-03",
        "captured_at": datetime.now().astimezone().isoformat(),
        "primary_failure": "injected_connection_failure",
        "backup": {
            "provider": result.provider,
            "model": result.model,
            "mode": result.mode,
            "failover": result.metadata["failover"],
            "primary_error_code": result.metadata["primary_error_code"],
            "answer_chars": len(result.content),
            "answer_sha256": hashlib.sha256(result.content.encode("utf-8")).hexdigest(),
        },
        "dual_failure": {
            "code": exhausted_code,
            "persisted": False,
        },
        "secrets_recorded": False,
        "status": "PASS",
    }
    OUTPUT.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        "FAILOVER RESULT: PASS "
        f"backup={result.provider}/{result.model} "
        f"dual_failure={exhausted_code} details={OUTPUT.relative_to(ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
