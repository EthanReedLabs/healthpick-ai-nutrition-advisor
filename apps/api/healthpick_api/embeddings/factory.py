"""Single construction point for the production embedding adapter."""

from __future__ import annotations

from healthpick_api.config import Settings
from healthpick_api.providers import ProviderConfigurationError

from .base import EmbeddingProvider
from .openai_compatible import OpenAICompatibleEmbeddingProvider


def build_embedding_provider(settings: Settings) -> EmbeddingProvider:
    if settings.embedding_mode != "real":
        raise ProviderConfigurationError("Embedding provider is disabled")

    missing = [
        name
        for name, value in (
            ("EMBEDDING_BASE_URL", settings.embedding_base_url),
            ("EMBEDDING_API_KEY", settings.embedding_api_key),
            ("EMBEDDING_MODEL", settings.embedding_model),
            ("EMBEDDING_DIMENSIONS", settings.embedding_dimensions),
        )
        if value is None or (isinstance(value, str) and not value.strip())
    ]
    if missing:
        raise ProviderConfigurationError(f"Real embedding mode requires: {', '.join(missing)}")

    assert settings.embedding_base_url is not None
    assert settings.embedding_api_key is not None
    assert settings.embedding_model is not None
    assert settings.embedding_dimensions is not None
    return OpenAICompatibleEmbeddingProvider(
        provider_name=settings.embedding_provider,
        base_url=settings.embedding_base_url,
        api_key=settings.embedding_api_key.get_secret_value(),
        model_name=settings.embedding_model,
        dimensions=settings.embedding_dimensions,
        timeout_seconds=settings.llm_timeout_seconds,
    )
