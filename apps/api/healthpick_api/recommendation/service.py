"""Deterministic plan selection; the model never chooses candidate facts."""

from __future__ import annotations

from typing import Any

from healthpick_api.profile import ProfilePatch
from healthpick_api.safety import SafetyService

from .catalog import PlanRule, RecommendationCatalog
from .models import (
    RecommendationEvaluation,
    RecommendationEvidence,
    RecommendationOption,
)

GOAL_RULES: dict[str, tuple[str, ...]] = {
    "fat_loss": (
        "rule-A-fat_loss_guidance",
        "rule-A-plate_211",
        "rule-B-food_substitutions",
    ),
    "muscle_gain": (
        "rule-B-muscle_targets",
        "rule-B-muscle_timing",
        "rule-B-food_substitutions",
    ),
    "stable_glucose": (
        "rule-B-plate_321",
        "rule-B-gi_categories",
        "rule-B-food_substitutions",
    ),
}

PLAN_TITLES = {
    "fat_loss": "轻盈减脂",
    "muscle_gain": "力量增肌",
    "stable_glucose": "稳糖调理",
}

BLOCKED_TAG_TERMS: dict[str, tuple[str, ...]] = {
    "animal_product": ("鸡", "鱼", "虾", "肉", "蛋", "奶", "乳清", "酪蛋白"),
    "dairy": ("牛奶", "酸奶", "乳清", "酪蛋白", "乳制品"),
    "egg": ("鸡蛋", "蛋清", "蛋类"),
    "fish": ("鱼", "鳕鱼", "鲈鱼", "龙利鱼", "比目鱼"),
    "gluten": ("小麦", "全麦", "面包", "馒头"),
    "meat": ("鸡", "肉", "火鸡"),
    "peanut": ("花生",),
    "sesame": ("芝麻",),
    "shellfish": ("虾", "蟹", "蛤蜊", "鱿鱼"),
    "soy": ("豆腐", "大豆", "豆制品"),
    "tree_nut": ("坚果", "核桃"),
    "wheat": ("小麦", "全麦", "面包", "馒头"),
}


class RecommendationService:
    def __init__(
        self,
        catalog: RecommendationCatalog,
        *,
        safety: SafetyService | None = None,
    ) -> None:
        self.catalog = catalog
        self.safety = safety or SafetyService()

    @classmethod
    def load_default(cls) -> RecommendationService:
        return cls(RecommendationCatalog.load_default())

    def evaluate(self, profile: ProfilePatch) -> RecommendationEvaluation:
        if profile.goal is None:
            return _blocked("missing_goal")
        if profile.age_band != "adult_18_44":
            return _blocked("age_outside_or_ambiguous_plan_scope")

        safety = self.safety.assess("请评估结构化饮食方案", profile)
        if not safety.allow_personalized_targets:
            return _blocked(f"safety_{safety.risk_level.lower()}_general_only")

        required_rule_ids = GOAL_RULES[profile.goal]
        blocked_rule_ids = self.catalog.blocked_rule_ids(required_rule_ids)
        if blocked_rule_ids:
            return RecommendationEvaluation(
                status="blocked",
                blocked_reasons=["knowledge_second_person_review_required"],
                blocked_rule_ids=list(blocked_rule_ids),
                requires_second_person_review=True,
            )

        rules = self.catalog.required(required_rule_ids)
        return RecommendationEvaluation(
            status="ready",
            primary=_build_option(profile, safety.blocked_food_tags, rules),
        )


def _blocked(reason: str) -> RecommendationEvaluation:
    return RecommendationEvaluation(status="blocked", blocked_reasons=[reason])


def _build_option(
    profile: ProfilePatch,
    blocked_food_tags: list[str],
    rules: tuple[PlanRule, ...],
) -> RecommendationOption:
    by_id = {rule.rule_id: rule for rule in rules}
    goal = profile.goal
    assert goal is not None
    if goal == "fat_loss":
        targets = _fat_loss_targets(by_id["rule-A-fat_loss_guidance"].content)
        actions = (
            "每餐先按 2 份蔬菜、1 份蛋白质、1 份主食组织餐盘。",
            "从可用替换组中选择食材，保持同类替换并避开禁忌标签。",
            "每周记录执行感受；出现疾病、用药或不适时停止个体化调整并咨询专业人员。",
        )
    elif goal == "muscle_gain":
        content = by_id["rule-B-muscle_targets"].content
        targets = [
            f"蛋白质范围：{_range_text(content['protein_g_per_kg'])} g/kg",
            f"碳水范围：{_range_text(content['carbohydrate_g_per_kg'])} g/kg",
            f"能量增量：{_range_text(content['energy_delta_kcal'])} kcal",
        ]
        actions = (
            "训练前从已验证示例中选择一组碳水和蛋白质搭配。",
            "训练后在资料给出的时间窗内完成一餐或加餐。",
            "按周观察训练表现和体重趋势，不自行使用药物或极端增量。",
        )
    else:
        content = by_id["rule-B-plate_321"].content
        targets = [
            "餐盘比例：蔬菜 1/2、蛋白质 1/4、低 GI 主食 1/4",
            f"进餐顺序：{' → '.join(content['eating_order'])}",
            "优先选择资料列出的低 GI 主食。",
        ]
        actions = (
            "先确定半盘非淀粉类蔬菜，再安排蛋白质和低 GI 主食。",
            "按蔬菜、蛋白质、碳水的顺序进餐。",
            "记录餐后反应；确诊糖尿病或正在用药时由医生评估。",
        )

    substitutions = _substitutions(
        by_id["rule-B-food_substitutions"].content,
        blocked_food_tags,
    )
    reasons = [f"健康目标匹配：{PLAN_TITLES[goal]}"]
    if profile.activity_level:
        reasons.append(f"活动水平已纳入规则输入：{profile.activity_level}")
    return RecommendationOption(
        plan_id=f"plan-{goal}",
        title=PLAN_TITLES[goal],
        selection_score=min(
            100,
            80 + (10 if profile.activity_level else 0) + (5 if profile.sex else 0),
        ),
        match_reasons=reasons,
        key_targets=targets,
        actions=list(actions),
        substitutions=substitutions,
        evidence=[_evidence(rule) for rule in rules],
        blocked_food_tags=blocked_food_tags,
    )


def _fat_loss_targets(content: dict[str, Any]) -> list[str]:
    energy_delta = content["energy_delta_kcal"]
    energy_deficit = sorted(abs(value) for value in energy_delta)
    return [
        f"每日能量缺口：{_range_text(energy_deficit)} kcal",
        f"蛋白质范围：{_range_text(content['protein_g_per_kg'])} g/kg",
        f"每日饮水：{_range_text(content['water_ml_per_day'])} ml",
        f"进食顺序：{' → '.join(content['eating_order'])}",
    ]


def _substitutions(content: dict[str, Any], blocked_tags: list[str]) -> list[str]:
    results: list[str] = []
    for category in (
        "carbohydrate_about_80g_raw",
        "protein_100_120g",
        "vegetables_about_200g",
    ):
        groups = content.get(category, [])
        for group in groups:
            allowed = [item for item in group if not _blocked_item(item, blocked_tags)]
            if len(allowed) >= 2:
                results.append(" / ".join(allowed))
                break
    return results[:3]


def _blocked_item(item: str, blocked_tags: list[str]) -> bool:
    return any(term in item for tag in blocked_tags for term in BLOCKED_TAG_TERMS.get(tag, ()))


def _evidence(rule: PlanRule) -> RecommendationEvidence:
    return RecommendationEvidence(
        rule_id=rule.rule_id,
        source=rule.source_code,  # type: ignore[arg-type]
        title=rule.title,
        section=rule.section,
        pages=list(rule.pages),
    )


def _range_text(value: Any) -> str:
    if isinstance(value, list) and len(value) == 2:
        return f"{value[0]}–{value[1]}"
    raise ValueError("expected a two-item numeric range")
