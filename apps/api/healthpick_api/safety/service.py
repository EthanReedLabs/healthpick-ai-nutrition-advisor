"""Deterministic pre-generation risk classification and candidate hard filtering."""

from __future__ import annotations

from dataclasses import dataclass

from healthpick_api.models import SafetyResult
from healthpick_api.profile import ProfilePatch

EMERGENCY_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("emergency_chest_pain", ("胸痛", "胸口压榨", "胸口剧痛")),
    ("emergency_breathing", ("呼吸困难", "喘不过气", "无法呼吸", "说不出话")),
    ("emergency_syncope", ("晕厥", "昏厥", "失去意识", "晕倒了")),
    ("emergency_severe_allergy", ("严重过敏", "喉咙肿", "舌头肿", "过敏性休克")),
    ("emergency_severe_hypoglycemia", ("低血糖昏迷", "低血糖抽搐", "低血糖意识不清")),
)

MESSAGE_S2_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("message_diabetes", ("糖尿病",)),
    ("message_kidney_disease", ("肾病", "肾功能不全", "透析")),
    ("message_cardiovascular", ("心血管疾病", "冠心病")),
    ("message_pregnancy", ("孕期", "怀孕", "孕妇")),
    ("message_breastfeeding", ("哺乳期", "母乳喂养")),
    ("message_minor", ("未成年人", "儿童减肥", "青少年减肥")),
    ("message_eating_disorder", ("进食障碍", "厌食症", "暴食症")),
)

MESSAGE_S1_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("message_allergy_or_intolerance", ("过敏", "不耐受")),
    ("message_gout", ("痛风", "高尿酸", "尿酸高", "尿酸偏高")),
    ("message_hypertension", ("高血压", "血压偏高", "血压有点高")),
    ("message_blood_glucose_concern", ("血糖偏高", "血糖有点高", "血糖高")),
    ("message_family_history", ("家族病史", "家族史")),
    ("message_gluten_restriction", ("乳糜泻", "麸质")),
)

MESSAGE_BLOCK_TAGS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("shellfish", ("海鲜过敏", "虾过敏", "蟹过敏", "甲壳类过敏")),
    ("fish", ("鱼过敏", "鱼类过敏")),
    ("dairy", ("牛奶过敏", "乳制品过敏", "乳糖不耐")),
    ("egg", ("鸡蛋过敏", "蛋类过敏")),
    ("peanut", ("花生过敏",)),
    ("tree_nut", ("坚果过敏",)),
    ("wheat", ("小麦过敏",)),
    ("soy", ("大豆过敏", "豆制品过敏")),
    ("sesame", ("芝麻过敏",)),
    ("gluten", ("乳糜泻", "麸质")),
    ("high_purine", ("痛风", "高尿酸", "尿酸高", "尿酸偏高")),
    ("high_sodium", ("高血压", "血压偏高", "血压有点高", "低钠")),
)

MEDICATION_TERMS = (
    "停药",
    "换药",
    "减药",
    "加药",
    "调整药物",
    "调整剂量",
    "改剂量",
    "替代药物",
)
EXTREME_WEIGHT_TERMS = ("催吐", "绝食", "一天不吃", "一周瘦十斤", "低于800千卡")
PRECISE_PRESCRIPTION_TERMS = (
    "制定处方",
    "精确处方",
    "高蛋白处方",
    "低蛋白处方",
    "精确热量",
    "热量目标",
    "蛋白质目标",
    "每天吃多少克",
)

S1_CONDITIONS = {
    "gout",
    "hypertension",
    "celiac_disease",
    "lactose_intolerance",
}
S2_CONDITIONS = {
    "diabetes",
    "kidney_disease",
    "cardiovascular_disease",
    "pregnancy",
    "breastfeeding",
    "eating_disorder_history",
}

ALLERGY_BLOCK_TAGS = {
    "eggs": "egg",
    "milk": "dairy",
    "peanuts": "peanut",
    "tree_nuts": "tree_nut",
    "wheat": "wheat",
    "soy": "soy",
    "fish": "fish",
    "shellfish": "shellfish",
    "sesame": "sesame",
}
CONDITION_BLOCK_TAGS = {
    "gout": "high_purine",
    "hypertension": "high_sodium",
    "celiac_disease": "gluten",
    "lactose_intolerance": "dairy",
}
PREFERENCE_BLOCK_TAGS = {
    "vegetarian": "meat",
    "vegan": "animal_product",
    "low_sodium": "high_sodium",
    "gluten_free": "gluten",
    "lactose_free": "dairy",
}


@dataclass(frozen=True, slots=True)
class FoodCandidate:
    candidate_id: str
    tags: frozenset[str]


@dataclass(frozen=True, slots=True)
class CandidateFilterResult:
    allowed: tuple[FoodCandidate, ...]
    rejected_ids: tuple[str, ...]


class SafetyService:
    def assess(self, message: str, profile: ProfilePatch | None = None) -> SafetyResult:
        normalized = message.casefold()
        matched_rules: list[str] = []

        for rule_id, terms in EMERGENCY_RULES:
            if _matches_any(normalized, terms):
                matched_rules.append(rule_id)
        if matched_rules:
            return SafetyResult(
                risk_level="S3",
                matched_rules=matched_rules,
                blocked_food_tags=_blocked_food_tags(profile),
                allow_personalized_targets=False,
                required_notice="emergency",
                response_mode="emergency_stop",
            )

        medication_request = _matches_any(normalized, MEDICATION_TERMS)
        extreme_weight_request = _matches_any(normalized, EXTREME_WEIGHT_TERMS)
        precise_prescription_request = _matches_any(normalized, PRECISE_PRESCRIPTION_TERMS)
        if medication_request:
            matched_rules.append("medication_adjustment_forbidden")
        if extreme_weight_request:
            matched_rules.append("extreme_weight_control_forbidden")
        if precise_prescription_request:
            matched_rules.append("precise_prescription_request")

        for rule_id, terms in MESSAGE_S2_RULES:
            if _matches_any(normalized, terms):
                matched_rules.append(rule_id)

        profile_conditions = set(profile.conditions if profile else [])
        profile_has_s2 = bool(profile_conditions & S2_CONDITIONS)
        profile_has_s1 = bool(profile_conditions & S1_CONDITIONS)
        if profile_has_s2:
            matched_rules.extend(
                f"profile_{condition}" for condition in sorted(profile_conditions & S2_CONDITIONS)
            )
        if profile and profile.age_band == "under_18":
            matched_rules.append("profile_minor")
            profile_has_s2 = True

        message_has_s2 = any(rule.startswith("message_") for rule in matched_rules)
        is_s2 = medication_request or extreme_weight_request or message_has_s2 or profile_has_s2
        message_s1_rules = [
            rule_id for rule_id, terms in MESSAGE_S1_RULES if _matches_any(normalized, terms)
        ]
        message_blocked_food_tags = _message_blocked_food_tags(normalized)
        blocked_food_tags = list(
            dict.fromkeys([*_blocked_food_tags(profile), *message_blocked_food_tags])
        )
        if is_s2:
            should_refuse = (
                medication_request
                or extreme_weight_request
                or (precise_prescription_request and (message_has_s2 or profile_has_s2))
            )
            return SafetyResult(
                risk_level="S2",
                matched_rules=list(dict.fromkeys(matched_rules)),
                blocked_food_tags=blocked_food_tags,
                allow_personalized_targets=False,
                required_notice="professional",
                response_mode="refuse" if should_refuse else "general_only",
            )

        has_s1 = bool(
            (profile and profile.allergies)
            or profile_has_s1
            or blocked_food_tags
            or message_s1_rules
        )
        if has_s1:
            matched_rules.extend(message_s1_rules)
            if profile and profile.allergies:
                matched_rules.extend(f"profile_allergy_{allergy}" for allergy in profile.allergies)
            matched_rules.extend(
                f"profile_{condition}" for condition in sorted(profile_conditions & S1_CONDITIONS)
            )
            return SafetyResult(
                risk_level="S1",
                matched_rules=list(dict.fromkeys(matched_rules)),
                blocked_food_tags=blocked_food_tags,
                allow_personalized_targets=False,
                required_notice="professional",
                response_mode="general_only",
            )

        return SafetyResult(
            risk_level="S0",
            matched_rules=["standard_nutrition_scope"],
            blocked_food_tags=[],
            allow_personalized_targets=True,
            required_notice="general",
            response_mode="normal",
        )

    def filter_candidates(
        self,
        candidates: tuple[FoodCandidate, ...],
        safety: SafetyResult,
    ) -> CandidateFilterResult:
        blocked = set(safety.blocked_food_tags)
        allowed: list[FoodCandidate] = []
        rejected_ids: list[str] = []
        for candidate in candidates:
            if blocked & candidate.tags:
                rejected_ids.append(candidate.candidate_id)
            else:
                allowed.append(candidate)
        return CandidateFilterResult(tuple(allowed), tuple(rejected_ids))


def _matches_any(message: str, terms: tuple[str, ...]) -> bool:
    return any(term.casefold() in message for term in terms)


def _blocked_food_tags(profile: ProfilePatch | None) -> list[str]:
    if profile is None:
        return []
    tags = [ALLERGY_BLOCK_TAGS[tag] for tag in profile.allergies]
    tags.extend(
        CONDITION_BLOCK_TAGS[condition]
        for condition in profile.conditions
        if condition in CONDITION_BLOCK_TAGS
    )
    tags.extend(
        PREFERENCE_BLOCK_TAGS[preference]
        for preference in profile.dietary_preferences
        if preference in PREFERENCE_BLOCK_TAGS
    )
    return list(dict.fromkeys(tags))


def _message_blocked_food_tags(message: str) -> list[str]:
    return [tag for tag, terms in MESSAGE_BLOCK_TAGS if _matches_any(message, terms)]
