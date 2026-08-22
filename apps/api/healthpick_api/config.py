"""Validated runtime configuration with explicit Mock/Real modes."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    app_env: Literal["development", "test", "production"] = "development"
    app_version: str = "0.1.0"
    web_origin: str = "http://127.0.0.1:3000"
    api_origin: str = "http://127.0.0.1:8010"
    log_level: str = "INFO"

    database_url: SecretStr | None = None
    conversation_store_mode: Literal["auto", "postgres", "ephemeral"] = "auto"
    database_connect_timeout_seconds: int = 5
    database_statement_timeout_ms: int = 5000
    max_request_body_bytes: int = 32768

    llm_mode: Literal["real", "mock"] = "real"
    llm_provider: str = "openai_compatible"
    llm_base_url: str | None = None
    llm_api_key: SecretStr | None = None
    llm_model: str | None = None
    llm_timeout_seconds: int = 30
    llm_fallback_enabled: bool = False
    llm_fallback_provider: str = "openai_compatible"
    llm_fallback_base_url: str | None = None
    llm_fallback_api_key: SecretStr | None = None
    llm_fallback_model: str | None = None
    llm_fallback_timeout_seconds: int = 30

    embedding_mode: Literal["real", "disabled"] = "disabled"
    embedding_provider: str = "openai_compatible"
    embedding_base_url: str | None = None
    embedding_api_key: SecretStr | None = None
    embedding_model: str | None = None
    embedding_dimensions: int | None = None

    retrieval_mode: Literal["keyword", "vector", "hybrid"] = "keyword"

    @model_validator(mode="after")
    def prevent_production_mock(self) -> Settings:
        if self.app_env == "production" and self.llm_mode == "mock":
            raise ValueError("LLM_MODE=mock is forbidden when APP_ENV=production")
        if self.app_env == "production" and self.resolved_conversation_store_mode != "postgres":
            raise ValueError("PostgreSQL conversation persistence is required in production")
        if self.database_connect_timeout_seconds < 1:
            raise ValueError("DATABASE_CONNECT_TIMEOUT_SECONDS must be positive")
        if self.database_statement_timeout_ms < 100:
            raise ValueError("DATABASE_STATEMENT_TIMEOUT_MS must be at least 100")
        if self.max_request_body_bytes < 1024:
            raise ValueError("MAX_REQUEST_BODY_BYTES must be at least 1024")
        if self.llm_fallback_timeout_seconds < 1:
            raise ValueError("LLM_FALLBACK_TIMEOUT_SECONDS must be positive")
        if self.llm_fallback_enabled:
            if self.llm_mode != "real":
                raise ValueError("LLM fallback requires LLM_MODE=real")
            missing = [
                name
                for name, value in (
                    ("LLM_FALLBACK_BASE_URL", self.llm_fallback_base_url),
                    (
                        "LLM_FALLBACK_API_KEY",
                        self.llm_fallback_api_key.get_secret_value()
                        if self.llm_fallback_api_key
                        else None,
                    ),
                    ("LLM_FALLBACK_MODEL", self.llm_fallback_model),
                )
                if value is None or (isinstance(value, str) and not value.strip())
            ]
            if missing:
                raise ValueError(f"Enabled LLM fallback requires: {', '.join(missing)}")
        return self

    @property
    def resolved_conversation_store_mode(self) -> Literal["postgres", "ephemeral"]:
        if self.conversation_store_mode == "auto":
            return "postgres" if self.database_url else "ephemeral"
        return self.conversation_store_mode


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
