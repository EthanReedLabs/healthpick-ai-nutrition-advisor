"""Public API contracts shared through generated OpenAPI."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from healthpick_api.profile import BmiEstimate, ProfileAssessment, ProfilePatch
from healthpick_api.recommendation.models import (
    RecommendationEvaluation,
    RecommendationEvidence,
    RecommendationOption,
)

__all__ = [
    "BmiEstimate",
    "ProfileAssessment",
    "ProfilePatch",
    "RecommendationEvaluation",
    "RecommendationEvidence",
    "RecommendationOption",
]


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


class ChatRequest(StrictModel):
    conversation_id: str = Field(min_length=1, max_length=128)
    session_id: str | None = Field(default=None, min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=2000)
    profile_patch: ProfilePatch | None = None

    @field_validator("conversation_id", "session_id", "message", mode="before")
    @classmethod
    def strip_chat_strings(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("message")
    @classmethod
    def reject_nul_in_message(cls, value: str) -> str:
        if "\x00" in value:
            raise ValueError("message contains a forbidden NUL character")
        return value


class AnonymousSession(StrictModel):
    session_id: UUID
    created_at: datetime


class AuthRegisterRequest(StrictModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=10, max_length=128)
    anonymous_session_id: UUID

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        normalized = value.strip().lower()
        if normalized.count("@") != 1 or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("invalid email address")
        return normalized


class AuthLoginRequest(StrictModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=10, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        return AuthRegisterRequest.normalize_email(value)


class AccountDeleteRequest(StrictModel):
    password: str = Field(min_length=10, max_length=128)


class AuthUser(StrictModel):
    user_id: UUID
    email: str
    created_at: datetime


class AuthResponse(AuthUser):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_at: datetime
    session_id: UUID


class ConversationCreate(StrictModel):
    session_id: UUID
    title: str = Field(default="新对话", min_length=1, max_length=80)

    @field_validator("title", mode="before")
    @classmethod
    def strip_title(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class ConversationRename(StrictModel):
    session_id: UUID
    title: str = Field(min_length=1, max_length=80)

    @field_validator("title", mode="before")
    @classmethod
    def strip_title(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class ConversationSummary(StrictModel):
    conversation_id: UUID
    session_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
    turn_count: int = Field(ge=0)


class ConversationList(StrictModel):
    items: list[ConversationSummary]


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
    blocked_food_tags: list[str] = Field(default_factory=list)
    allow_personalized_targets: bool = True
    required_notice: Literal["general", "professional", "emergency"]
    response_mode: Literal["normal", "general_only", "refuse", "emergency_stop"] = "normal"


class ModelInfo(StrictModel):
    provider: str
    name: str
    mode: Literal["real", "mock"]


class RetrievalSelection(StrictModel):
    chunk_id: str
    source: Literal["A", "B", "C"]
    score: float = Field(ge=0)
    matched_terms: list[str] = Field(default_factory=list)


class RetrievalTraceView(StrictModel):
    mode: str
    route: Literal["nutrition", "platform", "mixed"]
    route_components: list[str]
    allowed_sources: list[Literal["A", "B", "C"]]
    query_terms: list[str]
    examined_chunks: int = Field(ge=0)
    excluded_unknown_glyph_chunks: int = Field(ge=0)
    eligible_chunks: int = Field(ge=0)
    rejected_by_source_boundary: int = Field(ge=0)
    returned_chunks: int = Field(ge=0)
    selections: list[RetrievalSelection]
    evidence_gate: Literal["passed"] = "passed"


class EmbeddingTransparency(StrictModel):
    provider: str
    name: str
    mode: Literal["real", "disabled"]
    dimensions: int | None = Field(default=None, ge=1)


class SourceBoundaryInfo(StrictModel):
    source: Literal["A", "B", "C"]
    title: str
    allowed_use: str
    forbidden_use: str


class ModelFailoverInfo(StrictModel):
    enabled: bool
    policy: Literal["retryable_or_invalid_response"] = "retryable_or_invalid_response"
    fallback: ModelInfo | None = None


class TransparencyResponse(StrictModel):
    version: str
    model: ModelInfo
    failover: ModelFailoverInfo
    embedding: EmbeddingTransparency
    retrieval_mode: Literal["keyword", "vector", "hybrid"]
    conversation_store: Literal["ephemeral", "postgres"]
    profile_persistence: Literal["ephemeral"] = "ephemeral"
    evidence_policy: str
    sources: list[SourceBoundaryInfo]


class EvaluationGate(StrictModel):
    operator: Literal[">=", "<="]
    threshold: float
    actual: float
    status: Literal["PASS", "FAIL"]


class EvaluationManualReview(StrictModel):
    status: Literal["PENDING", "PASS", "FAIL"]
    action: str
    case_count: int = Field(ge=0)


class EvaluationSummaryResponse(StrictModel):
    schema_version: Literal[1] = 1
    report_id: str
    source_report_sha256: str = Field(min_length=64, max_length=64)
    dataset_version: str
    dataset_sha256: str = Field(min_length=64, max_length=64)
    case_count: int = Field(ge=1)
    turn_count: int = Field(ge=1)
    completed_at: datetime
    automatic_status: Literal["PASS", "FAIL"]
    overall_status: Literal["PASS", "PASS_WITH_ACTION", "FAIL"]
    cleanup_status: Literal["PASS", "FAIL"]
    gates_passed: int = Field(ge=0)
    gates_total: int = Field(ge=1)
    metrics: dict[str, float | int]
    gates: dict[str, EvaluationGate]
    manual_review: EvaluationManualReview
    first_attempt_preserved: bool
    public_note: str


class ChatFinalEvent(StrictModel):
    request_id: str
    answer: str
    route: Literal["nutrition", "platform", "mixed", "out_of_scope"]
    citations: list[Citation]
    safety: SafetyResult
    model: ModelInfo
    retrieval_trace: RetrievalTraceView | None = None
    turn_id: UUID | None = None


class ConversationTurnView(StrictModel):
    turn_id: UUID
    request_id: str
    user_message: str
    assistant_message: str
    route: Literal["nutrition", "platform", "mixed", "out_of_scope"]
    created_at: datetime
    response: ChatFinalEvent | None = None


class ConversationDetail(ConversationSummary):
    turns: list[ConversationTurnView]


class AccountDataInventory(StrictModel):
    users: int = Field(ge=0)
    auth_sessions: int = Field(ge=0)
    anonymous_sessions: int = Field(ge=0)
    conversations: int = Field(ge=0)
    conversation_turns: int = Field(ge=0)
    total_records: int = Field(ge=0)


class AccountExportUser(StrictModel):
    user_id: UUID
    email: str
    created_at: datetime
    updated_at: datetime


class AccountExportAuthSession(StrictModel):
    auth_session_id: str
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None


class AccountExportSession(StrictModel):
    session_id: UUID
    created_at: datetime
    updated_at: datetime
    last_seen_at: datetime
    claimed_at: datetime | None = None


class AccountExportTurn(StrictModel):
    turn_id: UUID | None = None
    request_id: str
    user_message: str
    assistant_message: str
    route: Literal["nutrition", "platform", "mixed", "out_of_scope"]
    context_eligible: bool
    response_payload: dict[str, Any]
    created_at: datetime | None = None


class AccountExportConversation(StrictModel):
    conversation_id: UUID
    session_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
    turns: list[AccountExportTurn]


class AccountDataExport(StrictModel):
    export_version: Literal["1.0"] = "1.0"
    exported_at: datetime
    user: AccountExportUser
    inventory: AccountDataInventory
    auth_sessions: list[AccountExportAuthSession]
    sessions: list[AccountExportSession]
    conversations: list[AccountExportConversation]
    excluded_static_data: list[str]


class ChatStreamMetaEvent(StrictModel):
    request_id: str
    route: Literal["nutrition", "platform", "mixed", "out_of_scope"]
    model_mode: Literal["real", "mock"]
    session_mode: Literal["ephemeral", "postgres"]
    retrieval_mode: str


class ChatTokenEvent(StrictModel):
    delta: str


__all__ = [
    "BmiEstimate",
    "AnonymousSession",
    "ChatFinalEvent",
    "ChatRequest",
    "ChatStreamMetaEvent",
    "ChatTokenEvent",
    "Citation",
    "ComponentStatus",
    "ErrorResponse",
    "EvaluationGate",
    "EvaluationManualReview",
    "EvaluationSummaryResponse",
    "ConversationCreate",
    "ConversationDetail",
    "ConversationList",
    "ConversationRename",
    "ConversationSummary",
    "ConversationTurnView",
    "HealthResponse",
    "ModelInfo",
    "ModelFailoverInfo",
    "RetrievalSelection",
    "RetrievalTraceView",
    "EmbeddingTransparency",
    "SourceBoundaryInfo",
    "TransparencyResponse",
    "ProfileAssessment",
    "ProfilePatch",
    "SafetyResult",
]
