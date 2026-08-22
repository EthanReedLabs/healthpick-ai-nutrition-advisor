"""Strict A/B plan-rule catalog with explicit review eligibility."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[4]


class RecommendationCatalogError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class PlanRule:
    rule_id: str
    title: str
    content: dict[str, Any]
    source_code: str
    pages: tuple[int, ...]
    section: str
    review_status: str
    unknown_glyph: bool
    has_second_person_review: bool

    @property
    def eligible(self) -> bool:
        return (
            self.source_code in {"A", "B"}
            and self.review_status == "verified"
            and not self.unknown_glyph
            and self.has_second_person_review
        )


class RecommendationCatalog:
    def __init__(self, rules: Iterable[PlanRule]) -> None:
        values = tuple(rules)
        ids = [rule.rule_id for rule in values]
        if len(ids) != len(set(ids)):
            raise RecommendationCatalogError("plan rule IDs must be unique")
        self.rules = values
        self.by_id = {rule.rule_id: rule for rule in values}

    @classmethod
    def load_default(cls, root: Path = PROJECT_ROOT) -> RecommendationCatalog:
        return cls.load_path(root / "knowledge" / "normalized" / "facts" / "plan_rules.jsonl")

    @classmethod
    def load_path(cls, path: Path) -> RecommendationCatalog:
        rules: list[PlanRule] = []
        with path.open("r", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, start=1):
                if not line.strip():
                    continue
                try:
                    raw = json.loads(line)
                    rules.append(_parse_rule(raw))
                except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                    raise RecommendationCatalogError(
                        f"invalid plan rule at {path}:{line_number}: {exc}"
                    ) from exc
        return cls(rules)

    def required(self, rule_ids: tuple[str, ...]) -> tuple[PlanRule, ...]:
        return tuple(self.by_id[rule_id] for rule_id in rule_ids if rule_id in self.by_id)

    def blocked_rule_ids(self, rule_ids: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(
            rule_id
            for rule_id in rule_ids
            if rule_id not in self.by_id or not self.by_id[rule_id].eligible
        )


def _parse_rule(raw: dict[str, Any]) -> PlanRule:
    source = _required_str(raw, "source_code")
    if source not in {"A", "B"}:
        raise ValueError("recommendation rules may only use source A or B")
    pages = raw["pages"]
    if (
        not isinstance(pages, list)
        or not pages
        or not all(isinstance(page, int) and page > 0 for page in pages)
    ):
        raise ValueError("pages must contain positive integers")
    content = raw["content"]
    if not isinstance(content, dict) or not content:
        raise ValueError("content must be a non-empty object")
    return PlanRule(
        rule_id=_required_str(raw, "rule_id"),
        title=_required_str(raw, "title"),
        content=content,
        source_code=source,
        pages=tuple(pages),
        section=_required_str(raw, "section"),
        review_status=_required_str(raw, "review_status"),
        unknown_glyph=bool(raw.get("unknown_glyph", False)),
        has_second_person_review=isinstance(raw.get("second_person_review"), dict),
    )


def _required_str(raw: dict[str, Any], key: str) -> str:
    value = raw[key]
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value
