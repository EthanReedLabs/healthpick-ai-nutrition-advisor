from __future__ import annotations

from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from healthpick_api.config import Settings
from healthpick_api.main import create_app
from healthpick_api.profile import ProfilePatch
from healthpick_api.recommendation import PlanRule, RecommendationCatalog
from healthpick_api.recommendation.service import PLAN_USAGE_NOTICE, RecommendationService


def rule(rule_id: str, content: dict, *, source: str = "B") -> PlanRule:
    return PlanRule(
        rule_id=rule_id,
        title=rule_id,
        content=content,
        source_code=source,
        pages=(1,),
        section="test section",
        review_status="verified",
        unknown_glyph=False,
        has_second_person_review=True,
    )


def substitution_content() -> dict:
    return {
        "carbohydrate_about_80g_raw": [["糙米", "燕麦米", "黑米"]],
        "protein_100_120g": [["鸡胸肉", "火鸡胸肉", "去皮鸡腿肉"]],
        "vegetables_about_200g": [["西兰花", "花菜", "芦笋"]],
    }


def verified_service() -> RecommendationService:
    return RecommendationService(
        RecommendationCatalog(
            (
                rule(
                    "rule-A-fat_loss_guidance",
                    {
                        "energy_delta_kcal": [-500, -300],
                        "protein_g_per_kg": [1.2, 1.6],
                        "water_ml_per_day": [2000, 2500],
                        "eating_order": ["蔬菜", "蛋白质", "碳水"],
                    },
                    source="A",
                ),
                rule("rule-A-plate_211", {"plate": "211"}, source="A"),
                rule("rule-B-food_substitutions", substitution_content()),
                rule(
                    "rule-B-muscle_targets",
                    {
                        "protein_g_per_kg": [1.8, 2.2],
                        "carbohydrate_g_per_kg": [4, 6],
                        "energy_delta_kcal": [300, 500],
                    },
                ),
                rule("rule-B-muscle_timing", {"post_training": [30, 60]}),
                rule(
                    "rule-B-plate_321",
                    {"eating_order": ["蔬菜", "蛋白质", "碳水"]},
                ),
                rule("rule-B-gi_categories", {"low": {"value": 55}}),
            )
        )
    )


def test_live_catalog_releases_the_reviewed_core_rules_for_all_goals() -> None:
    service = RecommendationService.load_default()
    results = {
        goal: service.evaluate(ProfilePatch(age_band="adult_18_44", goal=goal))
        for goal in ("fat_loss", "muscle_gain", "stable_glucose")
    }
    assert all(result.status == "ready" for result in results.values())
    assert all(result.primary is not None for result in results.values())
    assert results["fat_loss"].primary is not None
    assert {item.rule_id for item in results["fat_loss"].primary.evidence} == {
        "rule-A-fat_loss_guidance",
        "rule-A-plate_211",
        "rule-B-food_substitutions",
    }


def test_missing_goal_and_ambiguous_age_fail_closed() -> None:
    service = verified_service()
    missing_goal = service.evaluate(ProfilePatch(age_band="adult_18_44"))
    ambiguous_age = service.evaluate(ProfilePatch(age_band="adult_45_64", goal="fat_loss"))
    assert missing_goal.blocked_reasons == ["missing_goal"]
    assert ambiguous_age.blocked_reasons == ["age_outside_or_ambiguous_plan_scope"]


def test_exact_45_is_ready_but_age_outside_verified_source_scope_is_blocked() -> None:
    service = verified_service()

    exact_45 = service.evaluate(ProfilePatch(age_band="adult_45_64", age_years=45, goal="fat_loss"))
    age_56 = service.evaluate(ProfilePatch(age_band="adult_45_64", age_years=56, goal="fat_loss"))

    assert exact_45.status == "ready"
    assert exact_45.primary is not None
    assert any("精确年龄 45 岁" in reason for reason in exact_45.primary.match_reasons)
    assert age_56.status == "blocked"
    assert age_56.blocked_reasons == ["age_outside_plan_scope"]


def test_medical_or_allergy_constraint_never_receives_personalized_targets() -> None:
    service = verified_service()
    allergy = service.evaluate(
        ProfilePatch(
            age_band="adult_18_44",
            goal="fat_loss",
            allergies=["shellfish"],
        )
    )
    kidney = service.evaluate(
        ProfilePatch(
            age_band="adult_18_44",
            goal="fat_loss",
            conditions=["kidney_disease"],
        )
    )
    exact_45_kidney = service.evaluate(
        ProfilePatch(
            age_band="adult_45_64",
            age_years=45,
            goal="fat_loss",
            conditions=["kidney_disease"],
        )
    )
    assert allergy.blocked_reasons == ["safety_s1_general_only"]
    assert kidney.blocked_reasons == ["safety_s2_general_only"]
    assert allergy.primary is None
    assert kidney.primary is None
    assert allergy.safe_alternative is not None
    assert kidney.safe_alternative is not None
    assert allergy.safe_alternative.blocked_food_tags == ["shellfish"]
    assert all(
        "kcal" not in target and "g/kg" not in target
        for target in allergy.safe_alternative.key_targets
    )
    assert allergy.professional_notice == PLAN_USAGE_NOTICE
    assert kidney.professional_notice == PLAN_USAGE_NOTICE
    assert exact_45_kidney.blocked_reasons == ["safety_s2_general_only"]
    assert exact_45_kidney.primary is None
    assert exact_45_kidney.safe_alternative is not None


def test_verified_fat_loss_rules_create_one_deterministic_primary_plan() -> None:
    result = verified_service().evaluate(
        ProfilePatch(
            age_band="adult_18_44",
            sex="female",
            activity_level="moderate",
            goal="fat_loss",
        )
    )
    assert result.status == "ready"
    assert result.generated_by == "deterministic_rules"
    assert result.alternate is None
    assert result.primary is not None
    assert result.primary.title == "轻盈减脂方案"
    assert result.primary.selection_score == 95
    assert len(result.primary.actions) == 3
    assert "每日能量缺口：300–500 kcal" in result.primary.key_targets
    assert "蛋白质范围：1.2–1.6 g/kg" in result.primary.key_targets
    assert {item.source for item in result.primary.evidence} == {"A", "B"}
    assert 1 <= len(result.primary.match_reasons) <= 2
    assert all(reason.endswith("。") for reason in result.primary.match_reasons)


@pytest.mark.parametrize(
    ("message", "expected_goal", "expected_title"),
    [
        ("我想减重，三餐应该怎么搭配？", "fat_loss", "轻盈减脂方案"),
        ("我在健身，训练前后应该怎么吃？", "muscle_gain", "力量增肌方案"),
        ("我血糖有点高，应该怎样选择低 GI 食物？", "stable_glucose", "稳糖调理方案"),
    ],
)
def test_message_intent_creates_non_persistent_preview(
    message: str,
    expected_goal: str,
    expected_title: str,
) -> None:
    service = verified_service()
    preview = service.preview_for_message(message)

    assert preview is not None
    assert preview.selection_basis == "message"
    assert preview.selected_goal == expected_goal
    assert preview.primary is not None or preview.safe_alternative is not None
    plan = preview.primary or preview.safe_alternative
    assert plan is not None
    assert expected_title in plan.title
    assert any("尚未写入健康档案" in reason for reason in plan.match_reasons)


def test_message_intent_with_allergy_returns_filtered_general_alternative() -> None:
    service = verified_service()
    preview = service.preview_for_message(
        "我对海鲜过敏，但我想减重，应该怎么搭配？",
        ProfilePatch(allergies=["shellfish"]),
    )

    assert preview is not None
    assert preview.status == "blocked"
    assert preview.primary is None
    assert preview.safe_alternative is not None
    assert preview.safe_alternative.blocked_food_tags == ["shellfish"]
    assert all("虾" not in item for item in preview.safe_alternative.substitutions)
    assert preview.professional_notice == PLAN_USAGE_NOTICE


def test_conflicting_message_goals_require_clarification_instead_of_guessing() -> None:
    assert verified_service().preview_for_message("我既想减脂又想增肌") is None


def test_verified_muscle_and_glucose_rules_create_goal_specific_targets() -> None:
    service = verified_service()
    muscle = service.evaluate(ProfilePatch(age_band="adult_18_44", goal="muscle_gain"))
    glucose = service.evaluate(ProfilePatch(age_band="adult_18_44", goal="stable_glucose"))
    assert muscle.primary is not None
    assert "蛋白质范围：1.8–2.2 g/kg" in muscle.primary.key_targets
    assert glucose.primary is not None
    assert "进餐顺序：蔬菜 → 蛋白质 → 碳水" in glucose.primary.key_targets


def test_unknown_glyph_or_missing_second_review_is_ineligible() -> None:
    unsafe_rule = rule(
        "rule-A-fat_loss_guidance",
        {
            "energy_delta_kcal": [-500, -300],
            "protein_g_per_kg": [1.2, 1.6],
            "water_ml_per_day": [2000, 2500],
            "eating_order": ["蔬菜", "蛋白质", "碳水"],
        },
        source="A",
    )
    unsafe_rule = replace(
        unsafe_rule,
        unknown_glyph=True,
        has_second_person_review=False,
    )
    service = RecommendationService(
        RecommendationCatalog(
            (
                unsafe_rule,
                rule("rule-A-plate_211", {"plate": "211"}, source="A"),
                rule("rule-B-food_substitutions", substitution_content()),
            )
        )
    )
    result = service.evaluate(ProfilePatch(age_band="adult_18_44", goal="fat_loss"))
    assert result.status == "blocked"
    assert result.blocked_rule_ids == ["rule-A-fat_loss_guidance"]


def test_recommendation_endpoint_returns_the_live_reviewed_candidate() -> None:
    app = create_app(Settings(app_env="test", llm_mode="mock", embedding_mode="disabled"))
    with TestClient(app) as client:
        response = client.post(
            "/v1/recommendations/evaluate",
            json={"age_band": "adult_18_44", "sex": "female", "goal": "fat_loss"},
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["primary"]["title"] == "轻盈减脂方案"
    assert payload["primary"]["key_targets"][0] == "每日能量缺口：300–500 kcal"
    assert payload["requires_second_person_review"] is False


def test_recommendation_endpoint_supports_verified_exact_age_45() -> None:
    app = create_app(Settings(app_env="test", llm_mode="mock", embedding_mode="disabled"))
    with TestClient(app) as client:
        response = client.post(
            "/v1/recommendations/evaluate",
            json={
                "age_band": "adult_45_64",
                "age_years": 45,
                "sex": "female",
                "goal": "fat_loss",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["primary"]["title"] == "轻盈减脂方案"
    assert any("精确年龄 45 岁" in reason for reason in payload["primary"]["match_reasons"])
