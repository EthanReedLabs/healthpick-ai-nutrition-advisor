"""Provider-neutral contracts; no SDK-specific objects cross this boundary."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol


@dataclass(frozen=True, slots=True)
class LLMMessage:
    role: Literal["system", "user", "assistant"]
    content: str


@dataclass(frozen=True, slots=True)
class LLMRequest:
    messages: tuple[LLMMessage, ...]
    temperature: float = 0.1
    max_tokens: int = 1200
    request_id: str | None = None


@dataclass(frozen=True, slots=True)
class LLMResult:
    content: str
    provider: str
    model: str
    mode: Literal["real", "mock"]
    latency_ms: int
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    finish_reason: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)


class ProviderError(RuntimeError):
    """Base error safe for API-layer normalization."""

    code = "provider_error"
    retryable = False

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ProviderConfigurationError(ProviderError):
    code = "provider_not_configured"


class ProviderRequestError(ProviderError):
    code = "provider_request_failed"

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retryable: bool = True,
    ) -> None:
        super().__init__(message, status_code=status_code)
        self.retryable = retryable


class ProviderProtocolError(ProviderError):
    code = "provider_invalid_response"


class LLMProvider(Protocol):
    mode: Literal["real", "mock"]
    provider_name: str
    model_name: str

    async def generate(self, request: LLMRequest) -> LLMResult: ...

    async def aclose(self) -> None: ...
