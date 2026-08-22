"""Run privacy-safe real LLM and Chinese embedding probes against local Ollama."""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from healthpick_api.config import Settings  # noqa: E402
from healthpick_api.embeddings import (  # noqa: E402
    EmbeddingRequest,
    build_embedding_provider,
)
from healthpick_api.providers import (  # noqa: E402
    LLMMessage,
    LLMRequest,
    build_llm_provider,
)

OUTPUT = ROOT / "docs" / "evidence" / "action-02-03-real-model-runtime.json"
BASE_URL = "http://127.0.0.1:11434/v1"
LLM_MODEL = "qwen2.5:3b-instruct"
EMBEDDING_MODEL = "qwen3-embedding:0.6b"
EMBEDDING_DIMENSIONS = 1024


def cosine(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    numerator = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    return numerator / (left_norm * right_norm)


async def model_digests() -> dict[str, str]:
    async with httpx2.AsyncClient(timeout=10) as client:
        response = await client.get("http://127.0.0.1:11434/api/tags")
        response.raise_for_status()
    models = response.json().get("models", [])
    return {
        item["name"]: item["digest"]
        for item in models
        if isinstance(item, dict)
        and isinstance(item.get("name"), str)
        and isinstance(item.get("digest"), str)
    }


async def main() -> None:
    settings = Settings(
        app_env="test",
        llm_mode="real",
        llm_provider="ollama_local",
        llm_base_url=BASE_URL,
        llm_api_key="ollama-local-no-secret",
        llm_model=LLM_MODEL,
        llm_timeout_seconds=120,
        embedding_mode="real",
        embedding_provider="ollama_local",
        embedding_base_url=BASE_URL,
        embedding_api_key="ollama-local-no-secret",
        embedding_model=EMBEDDING_MODEL,
        embedding_dimensions=EMBEDDING_DIMENSIONS,
        _env_file=None,
    )

    llm = build_llm_provider(settings)
    embedding = build_embedding_provider(settings)
    try:
        llm_result = await llm.generate(
            LLMRequest(
                messages=(
                    LLMMessage(
                        role="system",
                        content="立即返回用户指定的精确字符串，不要解释。",
                    ),
                    LLMMessage(
                        role="user",
                        content="只回复：HEALTHPICK_REAL_SMOKE",
                    ),
                ),
                temperature=0,
                max_tokens=64,
                request_id="action-02-real-smoke",
                reasoning_effort="none",
            )
        )
        embedding_result = await embedding.embed(
            EmbeddingRequest(
                inputs=(
                    "高血压人群应该如何控制钠摄入？",
                    "高血压饮食通常需要限制食盐和含钠调味品。",
                    "平台会员套餐包含哪些服务和价格？",
                ),
                request_id="action-03-chinese-smoke",
            )
        )
    finally:
        await llm.aclose()
        await embedding.aclose()

    if llm_result.mode != "real" or not llm_result.content.strip():
        raise RuntimeError("real LLM probe returned no usable content")
    if llm_result.content.strip() != "HEALTHPICK_REAL_SMOKE":
        raise RuntimeError("real LLM probe did not return the expected marker")
    if llm_result.finish_reason == "length":
        raise RuntimeError("real LLM probe was truncated")
    if embedding_result.dimensions != EMBEDDING_DIMENSIONS:
        raise RuntimeError("embedding dimensions do not match the frozen manifest")

    positive_similarity = cosine(embedding_result.vectors[0], embedding_result.vectors[1])
    negative_similarity = cosine(embedding_result.vectors[0], embedding_result.vectors[2])
    if positive_similarity <= negative_similarity:
        raise RuntimeError("Chinese semantic smoke did not rank the positive text first")

    digests = await model_digests()
    for model in (LLM_MODEL, EMBEDDING_MODEL):
        if model not in digests:
            raise RuntimeError(f"model digest missing for {model}")

    evidence = {
        "schema_version": 1,
        "evidence_id": "ACTION-02-03-REAL-MODELS",
        "action_ids": ["ACTION-02", "ACTION-03"],
        "scope": "ollama-local/openai-compatible/chinese",
        "captured_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "runtime": {
            "provider": "ollama_local",
            "base_url": BASE_URL,
            "quota": "local hardware; no remote token quota",
        },
        "llm": {
            "model": llm_result.model,
            "digest": digests[LLM_MODEL],
            "mode": llm_result.mode,
            "latency_ms": llm_result.latency_ms,
            "prompt_tokens": llm_result.prompt_tokens,
            "completion_tokens": llm_result.completion_tokens,
            "finish_reason": llm_result.finish_reason,
            "output_chars": len(llm_result.content),
            "output_sha256": hashlib.sha256(llm_result.content.encode()).hexdigest(),
            "status": "PASS",
        },
        "embedding": {
            "model": embedding_result.model,
            "digest": digests[EMBEDDING_MODEL],
            "dimensions": embedding_result.dimensions,
            "input_count": len(embedding_result.vectors),
            "latency_ms": embedding_result.latency_ms,
            "positive_similarity": round(positive_similarity, 6),
            "negative_similarity": round(negative_similarity, 6),
            "ranking_margin": round(positive_similarity - negative_similarity, 6),
            "status": "PASS",
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
