"""Deterministic post-generation safety validation and notice enforcement."""

from __future__ import annotations

import re
from dataclasses import dataclass

from healthpick_api.models import SafetyResult

PROFESSIONAL_NOTICE_TERMS = (
    "咨询医生",
    "咨询医师",
    "咨询医生或注册营养师",
    "咨询专业人员",
    "医生或注册营养师",
    "医师或注册营养师",
    "医生或药师",
)
GENERAL_NOTICE_TERMS = ("仅供参考", "不替代医疗诊断", "不构成医疗诊断")
EMERGENCY_NOTICE_TERMS = ("急救电话", "前往急诊", "立即就医")

MEDICATION_DIRECTIVE = re.compile(
    r"(?:建议|应该|可以|需要|请).{0,8}(?:停药|换药|减药|加药|调整剂量|替代药物)"
)
DIAGNOSIS_DIRECTIVE = re.compile(r"(?:你|您).{0,4}(?:患有|得了|确诊为)|可以确诊|诊断为")
ABSOLUTE_TREATMENT_CLAIM = re.compile(r"治愈|根治|保证有效|一定能|百分之百")
PRECISE_TARGET = re.compile(
    r"\d+(?:\.\d+)?\s*(?:千卡|kcal|大卡|克|g|毫克|mg)(?:\s*/\s*(?:天|日|kg))?",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class OutputSafetyValidationResult:
    valid: bool
    error_codes: tuple[str, ...]


class OutputSafetyValidator:
    def validate(
        self,
        *,
        answer: str,
        safety: SafetyResult,
    ) -> OutputSafetyValidationResult:
        errors: list[str] = []
        without_references = re.sub(r"【[ABC]-p\d{2}-c\d{2}】", "", answer)

        if safety.required_notice == "professional" and not any(
            term in answer for term in PROFESSIONAL_NOTICE_TERMS
        ):
            errors.append("missing_professional_notice")
        if safety.required_notice == "general" and not any(
            term in answer for term in GENERAL_NOTICE_TERMS
        ):
            errors.append("missing_general_notice")
        if safety.required_notice == "emergency" and not any(
            term in answer for term in EMERGENCY_NOTICE_TERMS
        ):
            errors.append("missing_emergency_notice")

        if MEDICATION_DIRECTIVE.search(without_references):
            errors.append("forbidden_medication_directive")
        if DIAGNOSIS_DIRECTIVE.search(without_references):
            errors.append("forbidden_diagnosis")
        if ABSOLUTE_TREATMENT_CLAIM.search(without_references):
            errors.append("forbidden_absolute_treatment_claim")
        if not safety.allow_personalized_targets and PRECISE_TARGET.search(without_references):
            errors.append("forbidden_precise_target")

        unique_errors = tuple(dict.fromkeys(errors))
        return OutputSafetyValidationResult(
            valid=not unique_errors,
            error_codes=unique_errors,
        )


def ensure_required_notice(answer: str, safety: SafetyResult) -> str:
    """Append a deterministic notice so safety does not depend on model compliance."""
    normalized = answer.rstrip()
    if safety.required_notice == "emergency":
        notice = "紧急提示：请立即联系当地急救电话或尽快前往急诊。"
        if any(term in normalized for term in EMERGENCY_NOTICE_TERMS):
            return normalized
    elif safety.required_notice == "professional":
        notice = (
            "安全提示：以上仅为一般营养信息，不构成医疗诊断或治疗建议；"
            "请咨询医生或注册营养师后再做个体化调整。"
        )
        if any(term in normalized for term in PROFESSIONAL_NOTICE_TERMS) and any(
            term in normalized for term in GENERAL_NOTICE_TERMS
        ):
            return normalized
    else:
        notice = "提示：以上为一般营养信息，仅供参考，不替代医疗诊断或治疗。"
        if any(term in normalized for term in GENERAL_NOTICE_TERMS):
            return normalized
    return f"{normalized}\n\n{notice}"
