"""Typed contract and structural gates for the 72-case release golden set."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

SourceCode = Literal["A", "B", "C"]
Category = Literal[
    "a_nutrition",
    "b_plan_substitution",
    "c_platform",
    "routing_mixed",
    "multi_turn",
    "medical_safety",
    "adversarial_robustness",
]

EXPECTED_CATEGORY_COUNTS: dict[str, int] = {
    "a_nutrition": 14,
    "b_plan_substitution": 14,
    "c_platform": 8,
    "routing_mixed": 10,
    "multi_turn": 8,
    "medical_safety": 10,
    "adversarial_robustness": 8,
}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ReleaseExpectation(StrictModel):
    outcome: Literal["answer", "guard", "http_error"] = "answer"
    http_status: int = Field(default=200, ge=200, le=599)
    error_code: str | None = None
    route: Literal["nutrition", "platform", "mixed", "out_of_scope"] | None = None
    allowed_sources: list[SourceCode] = Field(default_factory=list)
    forbidden_sources: list[SourceCode] = Field(default_factory=list)
    risk_level: Literal["S0", "S1", "S2", "S3"] | None = None
    response_mode: Literal["normal", "general_only", "refuse", "emergency_stop"] | None = None
    blocked_food_tags: list[str] = Field(default_factory=list)
    required_chunk_ids: list[str] = Field(default_factory=list)
    required_terms: list[str] = Field(default_factory=list)
    forbidden_terms: list[str] = Field(default_factory=list)
    require_citations: bool = True
    require_retrieval_trace: bool = True


class ReleaseTurn(StrictModel):
    message: str
    profile_patch: dict[str, Any] | None = None
    expected: ReleaseExpectation


class ReleaseCase(StrictModel):
    case_id: str = Field(min_length=5)
    category: Category
    weight: int = Field(default=1, ge=1, le=5)
    context_policy: Literal["single", "same_conversation", "isolated_conversations"] = "single"
    assertion_review: Literal["second_person_required", "not_applicable"]
    turns: list[ReleaseTurn] = Field(min_length=1, max_length=4)
    notes: str


def load_release_cases(path: Path) -> tuple[ReleaseCase, ...]:
    cases: list[ReleaseCase] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw_line.strip():
            continue
        try:
            cases.append(ReleaseCase.model_validate_json(raw_line))
        except ValueError as exc:
            raise ValueError(f"invalid release case at line {line_number}: {exc}") from exc
    return tuple(cases)


def load_chunk_index(paths: list[Path]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for path in paths:
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            if not raw_line.strip():
                continue
            row = json.loads(raw_line)
            index[str(row["chunk_id"])] = row
    return index


def validate_release_cases(
    cases: tuple[ReleaseCase, ...], chunk_index: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    errors: list[str] = []
    ids = [case.case_id for case in cases]
    if len(ids) != len(set(ids)):
        errors.append("duplicate_case_id")
    counts = Counter(case.category for case in cases)
    if dict(counts) != EXPECTED_CATEGORY_COUNTS:
        errors.append("category_counts_mismatch")
    if len(cases) != 72:
        errors.append("total_cases_must_equal_72")

    turn_count = 0
    second_person_cases = 0
    for case in cases:
        turn_count += len(case.turns)
        if case.category == "multi_turn":
            if len(case.turns) < 2 or case.context_policy == "single":
                errors.append(f"{case.case_id}:multi_turn_contract")
        elif len(case.turns) != 1 or case.context_policy != "single":
            errors.append(f"{case.case_id}:single_turn_contract")
        if case.assertion_review == "second_person_required":
            second_person_cases += 1

        for turn_index, turn in enumerate(case.turns, 1):
            expected = turn.expected
            label = f"{case.case_id}:turn-{turn_index}"
            allowed = set(expected.allowed_sources)
            forbidden = set(expected.forbidden_sources)
            if expected.outcome == "http_error":
                if expected.http_status < 400 or not expected.error_code:
                    errors.append(f"{label}:http_error_contract")
                if expected.route or allowed or expected.required_chunk_ids:
                    errors.append(f"{label}:http_error_must_not_claim_answer")
                continue
            if allowed & forbidden or allowed | forbidden != {"A", "B", "C"}:
                errors.append(f"{label}:source_partition")
            if (
                expected.route is None
                or expected.risk_level is None
                or expected.response_mode is None
            ):
                errors.append(f"{label}:missing_answer_contract")
            if expected.route == "platform" and allowed != {"C"}:
                errors.append(f"{label}:platform_boundary")
            if expected.route == "nutrition" and "C" in allowed:
                errors.append(f"{label}:nutrition_boundary")
            if expected.route == "mixed" and allowed != {"A", "B", "C"}:
                errors.append(f"{label}:mixed_boundary")
            if expected.route == "out_of_scope" and allowed:
                errors.append(f"{label}:out_of_scope_boundary")
            if expected.risk_level in {"S2", "S3"} and expected.response_mode == "normal":
                errors.append(f"{label}:high_risk_normal_response")
            for chunk_id in expected.required_chunk_ids:
                chunk = chunk_index.get(chunk_id)
                if chunk is None:
                    errors.append(f"{label}:unknown_chunk:{chunk_id}")
                    continue
                if int(chunk.get("unknown_glyph_count", 0)) > 0:
                    errors.append(f"{label}:unknown_glyph_chunk:{chunk_id}")
                if chunk.get("source_code") not in allowed:
                    errors.append(f"{label}:chunk_outside_source_boundary:{chunk_id}")

    return {
        "status": "PASS" if not errors else "FAIL",
        "case_count": len(cases),
        "turn_count": turn_count,
        "category_counts": dict(sorted(counts.items())),
        "second_person_review_cases": second_person_cases,
        "errors": errors,
    }
