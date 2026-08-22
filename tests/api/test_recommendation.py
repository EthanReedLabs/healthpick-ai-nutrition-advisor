from __future__ import annotations

from dataclasses import replace

from fastapi.testclient import TestClient
from healthpick_api.config import Settings
from healthpick_api.main import create_app
from healthpick_api.profile import ProfilePatch
from healthpick_api.recommendation import PlanRule, RecommendationCatalog
from healthpick_api.recommendation.service import RecommendationService


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
                    "rule-B-fat_loss_targets",
                    {
                        "cycle_weeks": [8, 12],
                        "female": {"energy_kcal": [1200, 1500], "protein_g": [60, 75]},
                        "male": {"energy_kcal": [1500, 1800], "protein_g": [75, 90]},
                    },
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


def test_live_catalog_blocks_every_unreviewed_rule_from_candidate_pool() -> None:
    result = RecommendationService.load_default().evaluate(
        ProfilePatch(
            age_band="adult_18_44",
            sex="female",
            goal="fat_loss",
        )
    )
    assert result.status == "blocked"
    assert result.primary is None
    assert result.requires_second_person_review is True
    assert result.blocked_reasons == ["knowledge_second_person_review_required"]
    assert set(result.blocked_rule_ids) == {
        "rule-B-fat_loss_targets",
        "rule-A-plate_211",
        "rule-B-food_substitutions",
    }


def test_missing_goal_and_ambiguous_age_fail_closed() -> None:
    service = verified_service()
    missing_goal = service.evaluate(ProfilePatch(age_band="adult_18_44"))
    ambiguous_age = service.evaluate(ProfilePatch(age_band="adult_45_64", goal="fat_loss"))
    assert missing_goal.blocked_reasons == ["missing_goal"]
    assert ambiguous_age.blocked_reasons == ["age_outside_or_ambiguous_plan_scope"]


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
    assert allergy.blocked_reasons == ["safety_s1_general_only"]
    assert kidney.blocked_reasons == ["safety_s2_general_only"]
    assert allergy.primary is None
    assert kidney.primary is None


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
    assert result.primary.title == "轻盈减脂"
    assert result.primary.selection_score == 95
    assert len(result.primary.actions) == 3
    assert "资料能量范围：1200–1500 kcal" in result.primary.key_targets
    assert {item.source for item in result.primary.evidence} == {"A", "B"}


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
        "rule-B-fat_loss_targets",
        {
            "cycle_weeks": [8, 12],
            "female": {"energy_kcal": [1200, 1500], "protein_g": [60, 75]},
            "male": {"energy_kcal": [1500, 1800], "protein_g": [75, 90]},
        },
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
    assert result.blocked_rule_ids == ["rule-B-fat_loss_targets"]


def test_recommendation_endpoint_reports_live_review_gate_without_fabrication() -> None:
    app = create_app(Settings(app_env="test", llm_mode="mock", embedding_mode="disabled"))
    with TestClient(app) as client:
        response = client.post(
            "/v1/recommendations/evaluate",
            json={"age_band": "adult_18_44", "sex": "female", "goal": "fat_loss"},
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "blocked"
    assert payload["primary"] is None
    assert payload["requires_second_person_review"] is True
