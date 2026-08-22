"""Minimal, structured health-profile contracts without free-text medical history."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

AgeBand = Literal["under_18", "adult_18_44", "adult_45_64", "older_65_plus"]
Sex = Literal["female", "male", "prefer_not_to_say"]
ActivityLevel = Literal["sedentary", "light", "moderate", "high"]
Goal = Literal["fat_loss", "muscle_gain", "stable_glucose"]
DietaryPreference = Literal[
    "vegetarian",
    "vegan",
    "low_sodium",
    "gluten_free",
    "lactose_free",
]
AllergenTag = Literal[
    "eggs",
    "milk",
    "peanuts",
    "tree_nuts",
    "wheat",
    "soy",
    "fish",
    "shellfish",
    "sesame",
]
MedicalFlag = Literal[
    "diabetes",
    "kidney_disease",
    "gout",
    "hypertension",
    "cardiovascular_disease",
    "pregnancy",
    "breastfeeding",
    "celiac_disease",
    "lactose_intolerance",
    "eating_disorder_history",
]
ShortFoodName = Annotated[str, Field(min_length=1, max_length=40)]


class ProfileModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ProfilePatch(ProfileModel):
    age_band: AgeBand | None = None
    sex: Sex | None = None
    height_cm: float | None = Field(default=None, ge=100, le=230)
    weight_kg: float | None = Field(default=None, ge=25, le=300)
    activity_level: ActivityLevel | None = None
    goal: Goal | None = None
    dietary_preferences: list[DietaryPreference] = Field(default_factory=list, max_length=10)
    allergies: list[AllergenTag] = Field(default_factory=list, max_length=20)
    disliked_foods: list[ShortFoodName] = Field(default_factory=list, max_length=20)
    conditions: list[MedicalFlag] = Field(default_factory=list, max_length=20)

    @field_validator(
        "dietary_preferences",
        "allergies",
        "disliked_foods",
        "conditions",
    )
    @classmethod
    def deduplicate_tags(cls, values: list[str]) -> list[str]:
        return list(dict.fromkeys(values))


class BmiEstimate(ProfileModel):
    value: float = Field(gt=0)
    height_cm: float
    weight_kg: float
    formula: Literal["weight_kg / (height_m ** 2)"] = "weight_kg / (height_m ** 2)"
    label: Literal["系统估算"] = "系统估算"


class ProfileAssessment(ProfileModel):
    profile: ProfilePatch
    bmi: BmiEstimate | None
    persistence: Literal["ephemeral"] = "ephemeral"
    collected_fields: list[str]
