"""Minimal OpenAI-compatible chat-completions transport."""

from __future__ import annotations

from time import perf_counter
from typing import Any

import httpx2

from .base import (
    LLMRequest,
    LLMResult,
    ProviderProtocolError,
    ProviderRequestError,
)


class OpenAICompatibleLLMProvider:
    mode = "real"

    def __init__(
        self,
        *,
        provider_name: str,
        base_url: str,
        api_key: str,
        model_name: str,
        timeout_seconds: int,
        client: httpx2.AsyncClient | None = None,
    ) -> None:
        self.provider_name = provider_name
        self.model_name = model_name
        self._owns_client = client is None
        self._client = client or httpx2.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "healthpick-api/0.1",
            },
            timeout=timeout_seconds,
            follow_redirects=False,
        )

    async def generate(self, request: LLMRequest) -> LLMResult:
        started = perf_counter()
        payload = {
            "model": self.model_name,
            "messages": [{"role": item.role, "content": item.content} for item in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": False,
        }
        headers = {"X-Request-ID": request.request_id} if request.request_id else None

        try:
            response = await self._client.post(
                "/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
        except httpx2.TimeoutException as exc:
            raise ProviderRequestError("LLM provider timed out", retryable=True) from exc
        except httpx2.HTTPStatusError as exc:
            status_code = exc.response.status_code
            raise ProviderRequestError(
                f"LLM provider returned HTTP {status_code}",
                status_code=status_code,
                retryable=status_code == 429 or status_code >= 500,
            ) from exc
        except httpx2.RequestError as exc:
            raise ProviderRequestError("LLM provider connection failed", retryable=True) from exc

        try:
            body: dict[str, Any] = response.json()
            choice = body["choices"][0]
            content = choice["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise ValueError("empty content")
            usage = body.get("usage") or {}
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ProviderProtocolError("LLM provider returned an invalid response") from exc

        return LLMResult(
            content=content.strip(),
            provider=self.provider_name,
            model=self.model_name,
            mode=self.mode,
            latency_ms=round((perf_counter() - started) * 1000),
            prompt_tokens=_optional_int(usage.get("prompt_tokens")),
            completion_tokens=_optional_int(usage.get("completion_tokens")),
            finish_reason=_optional_str(choice.get("finish_reason")),
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()


def _optional_int(value: object) -> int | None:
    return value if isinstance(value, int) else None


def _optional_str(value: object) -> str | None:
    return value if isinstance(value, str) else None
