"""Public, deterministic recommendation contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RecommendationModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RecommendationEvidence(RecommendationModel):
    rule_id: str
    source: Literal["A", "B"]
    title: str
    section: str
    pages: list[int]
    review_status: Literal["verified"] = "verified"


class RecommendationOption(RecommendationModel):
    plan_id: str
    title: str
    selection_score: int = Field(ge=0, le=100)
    match_reasons: list[str] = Field(min_length=1, max_length=4)
    key_targets: list[str] = Field(min_length=1, max_length=5)
    actions: list[str] = Field(min_length=3, max_length=3)
    substitutions: list[str] = Field(default_factory=list, max_length=5)
    evidence: list[RecommendationEvidence] = Field(min_length=1)
    blocked_food_tags: list[str] = Field(default_factory=list)


class RecommendationEvaluation(RecommendationModel):
    status: Literal["ready", "blocked"]
    generated_by: Literal["deterministic_rules"] = "deterministic_rules"
    selection_basis: Literal["profile", "message"] = "profile"
    selected_goal: Literal["fat_loss", "muscle_gain", "stable_glucose"] | None = None
    primary: RecommendationOption | None = None
    alternate: RecommendationOption | None = None
    safe_alternative: RecommendationOption | None = None
    professional_notice: str | None = None
    blocked_reasons: list[str] = Field(default_factory=list)
    blocked_rule_ids: list[str] = Field(default_factory=list)
    requires_second_person_review: bool = False
