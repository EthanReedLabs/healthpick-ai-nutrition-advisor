"""Deterministic health-goal inference for recommendation previews."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

GoalName = Literal["fat_loss", "muscle_gain", "stable_glucose"]

GOAL_INTENT_TERMS: dict[GoalName, tuple[str, ...]] = {
    "fat_loss": ("想减重", "我要减重", "减脂", "减肥", "瘦身", "塑形"),
    "muscle_gain": ("在健身", "想增肌", "增肌", "增加肌肉", "肌肉量"),
    "stable_glucose": (
        "血糖有点高",
        "血糖偏高",
        "血糖高",
        "糖尿病前期",
        "糖尿病",
        "稳糖",
        "控糖",
        "家族糖尿病史",
        "糖尿病家族史",
    ),
}


@dataclass(frozen=True, slots=True)
class GoalInference:
    goal: GoalName
    matched_terms: tuple[str, ...]


def infer_goal(message: str) -> GoalInference | None:
    """Return one unambiguous goal; conflicting goals require user clarification."""
    normalized = "".join(message.casefold().split())
    matches = {
        goal: tuple(term for term in terms if term in normalized)
        for goal, terms in GOAL_INTENT_TERMS.items()
    }
    matched_goals = [goal for goal, terms in matches.items() if terms]
    if len(matched_goals) != 1:
        return None
    goal = matched_goals[0]
    return GoalInference(goal=goal, matched_terms=matches[goal])
