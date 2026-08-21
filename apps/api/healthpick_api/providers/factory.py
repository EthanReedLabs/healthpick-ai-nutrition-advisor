"""Single construction point for runtime mode transparency."""

from __future__ import annotations

from healthpick_api.config import Settings

from .base import LLMProvider, ProviderConfigurationError
from .mock import MockLLMProvider
from .openai_compatible import OpenAICompatibleLLMProvider


def build_llm_provider(settings: Settings) -> LLMProvider:
    if settings.llm_mode == "mock":
        return MockLLMProvider(settings.llm_model or "mock-healthpick-v1")

    missing = [
        name
        for name, value in (
            ("LLM_BASE_URL", settings.llm_base_url),
            ("LLM_API_KEY", settings.llm_api_key),
            ("LLM_MODEL", settings.llm_model),
        )
        if value is None or (isinstance(value, str) and not value.strip())
    ]
    if missing:
        raise ProviderConfigurationError(f"Real LLM mode requires: {', '.join(missing)}")

    assert settings.llm_base_url is not None
    assert settings.llm_api_key is not None
    assert settings.llm_model is not None
    return OpenAICompatibleLLMProvider(
        provider_name=settings.llm_provider,
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key.get_secret_value(),
        model_name=settings.llm_model,
        timeout_seconds=settings.llm_timeout_seconds,
    )
