"""Provider-neutral, one-hop LLM failover with an auditable result marker."""

from __future__ import annotations

from dataclasses import replace

from .base import (
    LLMProvider,
    LLMRequest,
    LLMResult,
    ProviderError,
    ProviderProtocolError,
    ProviderRequestError,
)


class FailoverLLMProvider:
    def __init__(self, primary: LLMProvider, fallback: LLMProvider) -> None:
        if primary.mode != "real" or fallback.mode != "real":
            raise ValueError("failover providers must both use real mode")
        self.primary = primary
        self.fallback = fallback
        self.mode = primary.mode
        self.provider_name = primary.provider_name
        self.model_name = primary.model_name

    async def generate(self, request: LLMRequest) -> LLMResult:
        primary_error_code: str | None = None
        try:
            return await self.primary.generate(request)
        except ProviderError as primary_error:
            if not _can_fail_over(primary_error):
                raise
            primary_error_code = primary_error.code
        try:
            result = await self.fallback.generate(request)
        except ProviderError as fallback_error:
            raise ProviderRequestError(
                "Primary and fallback LLM providers failed",
                retryable=getattr(fallback_error, "retryable", False),
                code="provider_failover_exhausted",
            ) from fallback_error
        return replace(
            result,
            metadata={
                **result.metadata,
                "failover": "used",
                "primary_provider": self.primary.provider_name,
                "primary_model": self.primary.model_name,
                "primary_error_code": primary_error_code or "provider_error",
            },
        )

    async def aclose(self) -> None:
        try:
            await self.primary.aclose()
        finally:
            await self.fallback.aclose()


def _can_fail_over(error: ProviderError) -> bool:
    return isinstance(error, ProviderProtocolError) or (
        isinstance(error, ProviderRequestError) and error.retryable
    )
