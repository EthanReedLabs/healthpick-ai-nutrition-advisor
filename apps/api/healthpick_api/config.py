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

    llm_mode: Literal["real", "mock"] = "real"
    llm_provider: str = "openai_compatible"
    llm_base_url: str | None = None
    llm_api_key: SecretStr | None = None
    llm_model: str | None = None
    llm_timeout_seconds: int = 30

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
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
