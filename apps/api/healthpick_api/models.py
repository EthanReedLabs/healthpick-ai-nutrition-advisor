"""Public API contracts shared through generated OpenAPI."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ErrorResponse(StrictModel):
    request_id: str
    code: str
    message: str
    retryable: bool
    details: list[dict[str, Any]] | None = None


class ComponentStatus(StrictModel):
    status: Literal["configured", "mock", "not_configured", "not_checked", "disabled"]
    detail: str | None = None


class HealthResponse(StrictModel):
    status: Literal["ok"] = "ok"
    service: Literal["healthpick-api"] = "healthpick-api"
    version: str
    environment: Literal["development", "test", "production"]
    request_id: str
    modes: dict[str, str]
    dependencies: dict[str, ComponentStatus]


class ProfilePatch(StrictModel):
    goal: Literal["fat_loss", "muscle_gain", "stable_glucose"] | None = None
    allergies: list[str] = Field(default_factory=list, max_length=20)
    disliked_foods: list[str] = Field(default_factory=list, max_length=20)
    conditions: list[str] = Field(default_factory=list, max_length=20)


class ChatRequest(StrictModel):
    conversation_id: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=4000)
    profile_patch: ProfilePatch | None = None


class Citation(StrictModel):
    source: Literal["A", "B", "C"]
    title: str
    section: str
    page: int = Field(ge=1)
    chunk_id: str
    excerpt: str


class SafetyResult(StrictModel):
    risk_level: Literal["S0", "S1", "S2", "S3"]
    matched_rules: list[str] = Field(default_factory=list)
    required_notice: Literal["general", "professional", "emergency"]


class ModelInfo(StrictModel):
    provider: str
    name: str
    mode: Literal["real", "mock"]


class ChatFinalEvent(StrictModel):
    request_id: str
    answer: str
    route: Literal["nutrition", "platform", "mixed", "out_of_scope"]
    citations: list[Citation]
    safety: SafetyResult
    model: ModelInfo


class ChatStreamMetaEvent(StrictModel):
    request_id: str
    route: Literal["nutrition", "platform", "mixed", "out_of_scope"]
    model_mode: Literal["real", "mock"]
    session_mode: Literal["ephemeral"]
    retrieval_mode: str


class ChatTokenEvent(StrictModel):
    delta: str
