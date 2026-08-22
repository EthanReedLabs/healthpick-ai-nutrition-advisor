from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from healthpick_api.config import Settings
from healthpick_api.main import create_app
from healthpick_api.profile import ProfilePatch, assess_profile
from pydantic import ValidationError


def test_profile_normalizes_strings_and_deduplicates_tags() -> None:
    profile = ProfilePatch(
        age_band="adult_18_44",
        goal="fat_loss",
        allergies=["shellfish", "shellfish"],
        disliked_foods=[" 香菜 ", "香菜", "苦瓜"],
        conditions=["hypertension", "hypertension"],
    )
    assert profile.allergies == ["shellfish"]
    assert profile.disliked_foods == ["香菜", "苦瓜"]
    assert profile.conditions == ["hypertension"]


def test_profile_rejects_unknown_medical_flags_and_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ProfilePatch(conditions=["free_text_diagnosis"])
    with pytest.raises(ValidationError):
        ProfilePatch(full_name="private person")


@pytest.mark.parametrize(
    ("field", "value"),
    [("height_cm", 99), ("height_cm", 231), ("weight_kg", 24), ("weight_kg", 301)],
)
def test_profile_rejects_out_of_range_measurements(field: str, value: int) -> None:
    with pytest.raises(ValidationError):
        ProfilePatch(**{field: value})


def test_bmi_is_an_explicit_system_estimate_only_when_inputs_are_complete() -> None:
    complete = assess_profile(ProfilePatch(height_cm=170, weight_kg=65))
    incomplete = assess_profile(ProfilePatch(height_cm=170))
    assert complete.bmi is not None
    assert complete.bmi.value == 22.5
    assert complete.bmi.formula == "weight_kg / (height_m ** 2)"
    assert complete.bmi.label == "系统估算"
    assert incomplete.bmi is None


def test_profile_assessment_endpoint_is_ephemeral_and_normalized() -> None:
    app = create_app(Settings(app_env="test", llm_mode="mock", embedding_mode="disabled"))
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/v1/profile/assess",
            json={
                "age_band": "adult_18_44",
                "height_cm": 170,
                "weight_kg": 65,
                "goal": "stable_glucose",
                "allergies": ["shellfish", "shellfish"],
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert body["persistence"] == "ephemeral"
    assert body["profile"]["allergies"] == ["shellfish"]
    assert body["bmi"]["value"] == 22.5
    assert set(body["collected_fields"]) == {
        "age_band",
        "height_cm",
        "weight_kg",
        "goal",
        "allergies",
    }


def test_chat_rejects_invalid_profile_patch_with_stable_422() -> None:
    app = create_app(Settings(app_env="test", llm_mode="mock", embedding_mode="disabled"))
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/v1/chat/stream",
            json={
                "conversation_id": "invalid-profile",
                "message": "帮我搭配早餐",
                "profile_patch": {"height_cm": 99, "conditions": ["unknown"]},
            },
        )
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
