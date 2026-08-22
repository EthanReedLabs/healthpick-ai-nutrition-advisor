"""Strict OpenAI-compatible embeddings transport."""

from __future__ import annotations

from math import isfinite
from time import perf_counter
from typing import Any

import httpx2

from healthpick_api.providers import ProviderProtocolError, ProviderRequestError

from .base import EmbeddingRequest, EmbeddingResult


class OpenAICompatibleEmbeddingProvider:
    def __init__(
        self,
        *,
        provider_name: str,
        base_url: str,
        api_key: str,
        model_name: str,
        dimensions: int,
        timeout_seconds: int,
        client: httpx2.AsyncClient | None = None,
    ) -> None:
        if dimensions <= 0:
            raise ValueError("dimensions must be positive")
        self.provider_name = provider_name
        self.model_name = model_name
        self.dimensions = dimensions
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

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        if not request.inputs or any(not item.strip() for item in request.inputs):
            raise ValueError("embedding inputs must contain non-empty text")

        started = perf_counter()
        headers = {"X-Request-ID": request.request_id} if request.request_id else None
        try:
            response = await self._client.post(
                "/embeddings",
                json={
                    "model": self.model_name,
                    "input": list(request.inputs),
                    "dimensions": self.dimensions,
                    "encoding_format": "float",
                },
                headers=headers,
            )
            response.raise_for_status()
        except httpx2.TimeoutException as exc:
            raise ProviderRequestError(
                "Embedding provider timed out", retryable=True, code="embedding_timeout"
            ) from exc
        except httpx2.HTTPStatusError as exc:
            status_code = exc.response.status_code
            raise ProviderRequestError(
                f"Embedding provider returned HTTP {status_code}",
                status_code=status_code,
                retryable=status_code == 429 or status_code >= 500,
                code=(
                    "embedding_rate_limited"
                    if status_code == 429
                    else (
                        "embedding_upstream_unavailable"
                        if status_code >= 500
                        else "embedding_rejected_request"
                    )
                ),
            ) from exc
        except httpx2.RequestError as exc:
            raise ProviderRequestError(
                "Embedding provider connection failed",
                retryable=True,
                code="embedding_connection_failed",
            ) from exc

        try:
            body: dict[str, Any] = response.json()
            raw_data = sorted(body["data"], key=lambda item: item["index"])
            if len(raw_data) != len(request.inputs):
                raise ValueError("embedding count mismatch")
            vectors = tuple(self._validate_vector(item["embedding"]) for item in raw_data)
            usage = body.get("usage") or {}
            prompt_tokens = usage.get("prompt_tokens")
            if prompt_tokens is not None and not isinstance(prompt_tokens, int):
                raise ValueError("invalid token count")
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderProtocolError("Embedding provider returned an invalid response") from exc

        return EmbeddingResult(
            vectors=vectors,
            provider=self.provider_name,
            model=self.model_name,
            dimensions=self.dimensions,
            latency_ms=round((perf_counter() - started) * 1000),
            prompt_tokens=prompt_tokens,
        )

    def _validate_vector(self, raw_vector: object) -> tuple[float, ...]:
        if not isinstance(raw_vector, list) or len(raw_vector) != self.dimensions:
            raise ValueError("embedding dimension mismatch")
        vector: list[float] = []
        for value in raw_vector:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError("embedding contains a non-number")
            number = float(value)
            if not isfinite(number):
                raise ValueError("embedding contains a non-finite number")
            vector.append(number)
        return tuple(vector)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
