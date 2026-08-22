"""Provider-neutral embedding adapters."""

from .base import EmbeddingProvider, EmbeddingRequest, EmbeddingResult
from .factory import build_embedding_provider
from .openai_compatible import OpenAICompatibleEmbeddingProvider

__all__ = [
    "EmbeddingProvider",
    "EmbeddingRequest",
    "EmbeddingResult",
    "OpenAICompatibleEmbeddingProvider",
    "build_embedding_provider",
]
