"""Deterministic plan selection; the model never chooses candidate facts."""

from __future__ import annotations

from typing import Any

from healthpick_api.models import SafetyResult
from healthpick_api.profile import ProfilePatch
from healthpick_api.safety import SafetyService

from .catalog import PlanRule, RecommendationCatalog
from .intent import GoalInference, GoalName, infer_goal
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
    "fat_loss": "轻盈减脂方案",
    "muscle_gain": "力量增肌方案",
    "stable_glucose": "稳糖调理方案",
}

PLAN_MAX_AGE_YEARS = 55
PLAN_USAGE_NOTICE = "建议您在使用本方案前咨询专业医师或注册营养师"

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
    "high_purine": ("动物内脏", "浓肉汤", "沙丁鱼", "啤酒"),
    "high_sodium": ("腌制", "加工肉", "浓汤宝", "方便面调料"),
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
        if profile.age_band == "adult_45_64" and profile.age_years is None:
            return _blocked("age_outside_or_ambiguous_plan_scope")
        if profile.age_band == "adult_45_64" and profile.age_years <= PLAN_MAX_AGE_YEARS:
            pass
        elif profile.age_band != "adult_18_44":
            return _blocked("age_outside_plan_scope")

        required_rule_ids = GOAL_RULES[profile.goal]
        blocked_rule_ids = self.catalog.blocked_rule_ids(required_rule_ids)
        if blocked_rule_ids:
            return RecommendationEvaluation(
                status="blocked",
                selected_goal=profile.goal,
                blocked_reasons=["knowledge_second_person_review_required"],
                blocked_rule_ids=list(blocked_rule_ids),
                requires_second_person_review=True,
            )

        rules = self.catalog.required(required_rule_ids)
        safety = self.safety.assess("请评估结构化饮食方案", profile)
        if not safety.allow_personalized_targets:
            return RecommendationEvaluation(
                status="blocked",
                selected_goal=profile.goal,
                safe_alternative=_build_safe_alternative(
                    profile.goal,
                    safety.blocked_food_tags,
                    rules,
                    selection_basis="profile",
                ),
                professional_notice=PLAN_USAGE_NOTICE,
                blocked_reasons=[f"safety_{safety.risk_level.lower()}_general_only"],
            )

        return RecommendationEvaluation(
            status="ready",
            selected_goal=profile.goal,
            primary=_build_option(
                profile,
                safety.blocked_food_tags,
                rules,
                selection_basis="profile",
            ),
        )

    def preview_for_message(
        self,
        message: str,
        profile: ProfilePatch | None = None,
        *,
        safety: SafetyResult | None = None,
    ) -> RecommendationEvaluation | None:
        """Build a non-persistent candidate from one unambiguous user intent."""
        inference = infer_goal(message)
        if inference is None:
            return None
        assessed = safety or self.safety.assess(message, profile)
        if assessed.response_mode in {"refuse", "emergency_stop"}:
            return None

        required_rule_ids = GOAL_RULES[inference.goal]
        blocked_rule_ids = self.catalog.blocked_rule_ids(required_rule_ids)
        if blocked_rule_ids:
            return RecommendationEvaluation(
                status="blocked",
                selection_basis="message",
                selected_goal=inference.goal,
                blocked_reasons=["knowledge_second_person_review_required"],
                blocked_rule_ids=list(blocked_rule_ids),
                requires_second_person_review=True,
            )

        rules = self.catalog.required(required_rule_ids)
        if not assessed.allow_personalized_targets:
            return RecommendationEvaluation(
                status="blocked",
                selection_basis="message",
                selected_goal=inference.goal,
                safe_alternative=_build_safe_alternative(
                    inference.goal,
                    assessed.blocked_food_tags,
                    rules,
                    selection_basis="message",
                    inference=inference,
                ),
                professional_notice=PLAN_USAGE_NOTICE,
                blocked_reasons=[f"safety_{assessed.risk_level.lower()}_general_only"],
            )

        preview_profile = (profile or ProfilePatch()).model_copy(update={"goal": inference.goal})
        return RecommendationEvaluation(
            status="ready",
            selection_basis="message",
            selected_goal=inference.goal,
            primary=_build_option(
                preview_profile,
                assessed.blocked_food_tags,
                rules,
                selection_basis="message",
                inference=inference,
            ),
        )


def _blocked(reason: str) -> RecommendationEvaluation:
    return RecommendationEvaluation(status="blocked", blocked_reasons=[reason])


def _build_option(
    profile: ProfilePatch,
    blocked_food_tags: list[str],
    rules: tuple[PlanRule, ...],
    *,
    selection_basis: str,
    inference: GoalInference | None = None,
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
    reasons = _match_reasons(
        profile,
        goal,
        selection_basis=selection_basis,
        inference=inference,
    )
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


def _build_safe_alternative(
    goal: GoalName,
    blocked_food_tags: list[str],
    rules: tuple[PlanRule, ...],
    *,
    selection_basis: str,
    inference: GoalInference | None = None,
) -> RecommendationOption:
    by_id = {rule.rule_id: rule for rule in rules}
    substitutions = _substitutions(
        by_id["rule-B-food_substitutions"].content,
        blocked_food_tags,
    )
    if goal == "fat_loss":
        targets = [
            "采用 211 餐盘结构，优先安排蔬菜、蛋白质与主食的均衡组合。",
            "本卡不提供个体化热量或营养素数值目标。",
        ]
    elif goal == "muscle_gain":
        targets = [
            "训练前后采用资料中的碳水与蛋白质组合，具体摄入量由专业人员评估。",
            "本卡不提供个体化热量或营养素数值目标。",
        ]
    else:
        targets = [
            "采用控糖 321 餐盘与低 GI 优先原则。",
            "本卡不提供疾病个体化数值目标。",
        ]

    matched_text = _inference_text(inference)
    if selection_basis == "message":
        reasons = [
            f"根据本轮“{matched_text}”表达，系统识别出相应健康诉求并展示“{PLAN_TITLES[goal]}”的通用安全替换。",
            "当前疾病或过敏信息使个体化目标保持关闭，候选食材已经应用禁忌标签过滤且尚未写入健康档案。",
        ]
    else:
        reasons = [
            f"您的健康目标与“{PLAN_TITLES[goal]}”匹配，但医疗或过敏标签使个体化目标保持关闭。",
            "以下仅展示基于已复核 A/B 资料并经过禁忌过滤的通用替换，不构成个体化处方。",
        ]
    return RecommendationOption(
        plan_id=f"safe-plan-{goal}",
        title=f"{PLAN_TITLES[goal]} · 安全替换",
        selection_score=70,
        match_reasons=reasons,
        key_targets=targets,
        actions=[
            "从已验证的同类替换组选择食材，并避开页面标出的受限类别。",
            "核对配料表和交叉接触风险，不确定时暂停食用。",
            "如有疾病、用药或不适，由专业医师或注册营养师进一步评估。",
        ],
        substitutions=substitutions,
        evidence=[_evidence(rule) for rule in rules],
        blocked_food_tags=blocked_food_tags,
    )


def _match_reasons(
    profile: ProfilePatch,
    goal: GoalName,
    *,
    selection_basis: str,
    inference: GoalInference | None,
) -> list[str]:
    if selection_basis == "message":
        return [
            f"根据本轮“{_inference_text(inference)}”表达，系统识别为相应健康诉求，因此优先展示“{PLAN_TITLES[goal]}”通用预览。",
            "该候选尚未写入健康档案；补充年龄、活动水平和禁忌后可进行个体化规则评估。",
        ]

    reasons = [
        f"您的健康目标与“{PLAN_TITLES[goal]}”匹配，系统仅使用已复核的核心营养资料 A/B 生成该方案。"
    ]
    details: list[str] = []
    if profile.activity_level:
        details.append(f"活动水平 {profile.activity_level}")
    if profile.age_years is not None:
        details.append(f"精确年龄 {profile.age_years} 岁")
    if details:
        reasons.append(f"规则校验已纳入{'、'.join(details)}，用于确认方案适用范围与匹配度。")
    return reasons


def _inference_text(inference: GoalInference | None) -> str:
    if inference and inference.matched_terms:
        return inference.matched_terms[0]
    return "当前诉求"


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
