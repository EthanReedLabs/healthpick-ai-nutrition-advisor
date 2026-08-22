"""Deterministic profile normalization and BMI preview."""

from __future__ import annotations

from .models import BmiEstimate, ProfileAssessment, ProfilePatch


def assess_profile(profile: ProfilePatch) -> ProfileAssessment:
    bmi = None
    if profile.height_cm is not None and profile.weight_kg is not None:
        height_m = profile.height_cm / 100
        bmi = BmiEstimate(
            value=round(profile.weight_kg / (height_m**2), 1),
            height_cm=profile.height_cm,
            weight_kg=profile.weight_kg,
        )
    collected_fields = [
        field for field, value in profile.model_dump().items() if value is not None and value != []
    ]
    return ProfileAssessment(
        profile=profile,
        bmi=bmi,
        collected_fields=collected_fields,
    )
