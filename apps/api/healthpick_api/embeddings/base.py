"""Embedding contracts shared by local and hosted OpenAI-compatible providers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class EmbeddingRequest:
    inputs: tuple[str, ...]
    request_id: str | None = None


@dataclass(frozen=True, slots=True)
class EmbeddingResult:
    vectors: tuple[tuple[float, ...], ...]
    provider: str
    model: str
    dimensions: int
    latency_ms: int
    prompt_tokens: int | None = None


class EmbeddingProvider(Protocol):
    provider_name: str
    model_name: str
    dimensions: int

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult: ...

    async def aclose(self) -> None: ...
