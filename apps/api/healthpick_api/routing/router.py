"""Conservative query router; routing is deterministic and auditable."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

RouteName = Literal[
    "nutrition",
    "recommendation",
    "contraindication",
    "platform",
    "mixed",
    "out_of_scope",
]
AtomicRoute = Literal["nutrition", "recommendation", "contraindication", "platform"]

CORE_SOURCES = ("A", "B")
PLATFORM_SOURCES = ("C",)

PLATFORM_TERMS = (
    "平台",
    "会员",
    "订阅",
    "退款",
    "企业服务",
    "白皮书",
    "api",
    "healthpick",
    "健康优选",
    "数据隐私",
    "客服",
    "免费版",
    "标准版",
    "专业版",
    "企业健康",
    "增值服务",
    "开放平台",
)
CONTRAINDICATION_TERMS = (
    "禁忌",
    "过敏",
    "不能吃",
    "不宜",
    "慎用",
    "肾病",
    "糖尿病",
    "高血压",
    "心血管",
    "孕期",
    "哺乳期",
    "疾病",
    "药物",
)
RECOMMENDATION_TERMS = (
    "推荐",
    "方案",
    "食谱",
    "搭配",
    "一日三餐",
    "早餐",
    "午餐",
    "晚餐",
    "减脂",
    "想减重",
    "增肌",
    "在健身",
    "稳糖",
    "控糖",
    "血糖偏高",
    "血糖有点高",
    "替换",
    "计划",
    "训练前",
    "训练后",
)
NUTRITION_TERMS = (
    "营养",
    "饮食",
    "膳食",
    "蛋白质",
    "碳水",
    "脂肪",
    "纤维",
    "热量",
    "千卡",
    "维生素",
    "矿物质",
    "低钠",
    "盐",
    "食物",
    "食材",
    "gi",
    "餐盘",
    "烹调",
    "烹饪",
    "一起吃",
    "同食",
)


@dataclass(frozen=True, slots=True)
class RouteDecision:
    route: RouteName
    components: tuple[AtomicRoute, ...]
    allowed_sources: tuple[str, ...]
    reason_codes: tuple[str, ...]


class QueryRouter:
    def route(self, query: str) -> RouteDecision:
        normalized = " ".join(query.lower().split())
        platform_hits = _matches(normalized, PLATFORM_TERMS)
        core_hits = {
            "contraindication": _matches(normalized, CONTRAINDICATION_TERMS),
            "recommendation": _matches(normalized, RECOMMENDATION_TERMS),
            "nutrition": _matches(normalized, NUTRITION_TERMS),
        }
        primary_core = next(
            (
                name
                for name in ("contraindication", "recommendation", "nutrition")
                if core_hits[name]
            ),
            None,
        )

        if platform_hits and primary_core:
            component = _as_atomic(primary_core)
            return RouteDecision(
                route="mixed",
                components=(component, "platform"),
                allowed_sources=(*CORE_SOURCES, *PLATFORM_SOURCES),
                reason_codes=(
                    f"core:{primary_core}:{','.join(core_hits[primary_core])}",
                    f"platform:{','.join(platform_hits)}",
                ),
            )
        if platform_hits:
            return RouteDecision(
                route="platform",
                components=("platform",),
                allowed_sources=PLATFORM_SOURCES,
                reason_codes=(f"platform:{','.join(platform_hits)}",),
            )
        if primary_core:
            component = _as_atomic(primary_core)
            return RouteDecision(
                route=component,
                components=(component,),
                allowed_sources=CORE_SOURCES,
                reason_codes=(f"core:{primary_core}:{','.join(core_hits[primary_core])}",),
            )
        return RouteDecision(
            route="out_of_scope",
            components=(),
            allowed_sources=(),
            reason_codes=("no_supported_intent",),
        )


def _matches(query: str, terms: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(term for term in terms if term in query)


def _as_atomic(value: str) -> AtomicRoute:
    if value not in {"nutrition", "recommendation", "contraindication", "platform"}:
        raise ValueError(f"Unsupported atomic route: {value}")
    return value  # type: ignore[return-value]
