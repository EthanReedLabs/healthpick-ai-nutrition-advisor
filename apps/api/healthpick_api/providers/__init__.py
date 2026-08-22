"""LLM provider boundary with explicit Real and Mock modes."""

from .base import (
    LLMMessage,
    LLMProvider,
    LLMRequest,
    LLMResult,
    ProviderConfigurationError,
    ProviderError,
    ProviderProtocolError,
    ProviderRequestError,
)
from .factory import build_llm_provider
from .failover import FailoverLLMProvider
from .mock import MockLLMProvider
from .openai_compatible import OpenAICompatibleLLMProvider

__all__ = [
    "LLMMessage",
    "LLMProvider",
    "LLMRequest",
    "LLMResult",
    "FailoverLLMProvider",
    "MockLLMProvider",
    "OpenAICompatibleLLMProvider",
    "ProviderConfigurationError",
    "ProviderError",
    "ProviderProtocolError",
    "ProviderRequestError",
    "build_llm_provider",
]
