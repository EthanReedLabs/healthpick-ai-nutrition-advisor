"""Deterministic scoring helpers for the release evaluation runner."""

from __future__ import annotations

import math
import re
from collections.abc import Iterable
from typing import Any

from healthpick_api.evaluation.release_golden import ReleaseExpectation

INLINE_REFERENCE = re.compile(r"【([ABC]-p\d{2}-c\d{2})】")
NUMERIC_TERM = re.compile(r"\d")


def percentile(values: Iterable[int], percentile_value: float) -> int | None:
    ordered = sorted(values)
    if not ordered:
        return None
    index = max(0, math.ceil(percentile_value * len(ordered)) - 1)
    return ordered[index]


def score_turn(
    expected: ReleaseExpectation,
    *,
    status_code: int,
    final: dict[str, Any] | None,
    error: dict[str, Any] | None,
) -> dict[str, Any]:
    """Score one turn without any semantic judge or mutable threshold."""

    if expected.outcome == "http_error":
        error_code = error.get("code") if error else None
        contract_pass = status_code == expected.http_status and error_code == expected.error_code
        return {
            "http_contract_pass": contract_pass,
            "turn_contract_pass": contract_pass,
            "multi_constraint_pass": contract_pass,
            "route_pass": None,
            "source_boundary_pass": None,
            "source_leakage": False,
            "risk_pass": None,
            "response_mode_pass": None,
            "blocked_food_tags_pass": None,
            "citation_presence_pass": None,
            "citation_integrity_pass": None,
            "trace_pass": None,
            "term_pass": None,
            "forbidden_term_pass": None,
            "required_chunk_matches": [],
            "required_chunk_total": 0,
            "numeric_term_matches": [],
            "numeric_term_total": 0,
        }

    if final is None:
        return {
            "http_contract_pass": False,
            "turn_contract_pass": False,
            "multi_constraint_pass": False,
            "route_pass": False,
            "source_boundary_pass": False,
            "source_leakage": False,
            "risk_pass": False,
            "response_mode_pass": False,
            "blocked_food_tags_pass": False,
            "citation_presence_pass": False,
            "citation_integrity_pass": False,
            "trace_pass": False,
            "term_pass": False,
            "forbidden_term_pass": False,
            "required_chunk_matches": [],
            "required_chunk_total": len(expected.required_chunk_ids),
            "numeric_term_matches": [],
            "numeric_term_total": sum(
                1 for term in expected.required_terms if NUMERIC_TERM.search(term)
            ),
        }

    answer = str(final.get("answer") or "")
    citations = final.get("citations") or []
    citation_ids = {str(item.get("chunk_id")) for item in citations if item.get("chunk_id")}
    citation_sources = {str(item.get("source")) for item in citations if item.get("source")}
    referenced_ids = set(INLINE_REFERENCE.findall(answer))
    trace = final.get("retrieval_trace")
    selections = trace.get("selections", []) if isinstance(trace, dict) else []
    trace_ids = {str(item.get("chunk_id")) for item in selections if item.get("chunk_id")}
    trace_sources = {str(item.get("source")) for item in selections if item.get("source")}
    actual_sources = citation_sources | trace_sources
    allowed_sources = set(expected.allowed_sources)
    safety = final.get("safety") or {}
    actual_blocked = set(safety.get("blocked_food_tags") or [])
    required_blocked = set(expected.blocked_food_tags)

    source_leakage = bool(actual_sources - allowed_sources)
    route_pass = final.get("route") == expected.route
    source_boundary_pass = not source_leakage
    risk_pass = safety.get("risk_level") == expected.risk_level
    mode_pass = safety.get("response_mode") == expected.response_mode
    blocked_pass = required_blocked <= actual_blocked
    citations_pass = not expected.require_citations or bool(citation_ids and referenced_ids)
    citation_integrity_pass = referenced_ids <= citation_ids
    if expected.require_retrieval_trace:
        trace_pass = bool(
            isinstance(trace, dict)
            and trace.get("evidence_gate") == "passed"
            and trace_ids == citation_ids
        )
    else:
        trace_pass = True

    required_chunk_matches = sorted(set(expected.required_chunk_ids) & referenced_ids)
    required_chunk_pass = len(required_chunk_matches) == len(expected.required_chunk_ids)
    term_matches = [term for term in expected.required_terms if term in answer]
    term_pass = len(term_matches) == len(expected.required_terms)
    forbidden_matches = [term for term in expected.forbidden_terms if term in answer]
    forbidden_pass = not forbidden_matches
    numeric_terms = [term for term in expected.required_terms if NUMERIC_TERM.search(term)]
    numeric_matches = [term for term in numeric_terms if term in answer]
    http_pass = status_code == expected.http_status

    contract_pass = all(
        (
            http_pass,
            route_pass,
            source_boundary_pass,
            risk_pass,
            mode_pass,
            blocked_pass,
            citations_pass,
            citation_integrity_pass,
            trace_pass,
            required_chunk_pass,
            term_pass,
            forbidden_pass,
        )
    )
    multi_constraint_pass = all(
        (
            http_pass,
            route_pass,
            source_boundary_pass,
            risk_pass,
            mode_pass,
            blocked_pass,
            citations_pass,
            citation_integrity_pass,
            trace_pass,
        )
    )
    return {
        "http_contract_pass": http_pass,
        "turn_contract_pass": contract_pass,
        "multi_constraint_pass": multi_constraint_pass,
        "route_pass": route_pass,
        "source_boundary_pass": source_boundary_pass,
        "source_leakage": source_leakage,
        "risk_pass": risk_pass,
        "response_mode_pass": mode_pass,
        "blocked_food_tags_pass": blocked_pass,
        "citation_presence_pass": citations_pass,
        "citation_integrity_pass": citation_integrity_pass,
        "trace_pass": trace_pass,
        "term_pass": term_pass,
        "term_matches": term_matches,
        "forbidden_term_pass": forbidden_pass,
        "forbidden_term_matches": forbidden_matches,
        "required_chunk_matches": required_chunk_matches,
        "required_chunk_total": len(expected.required_chunk_ids),
        "numeric_term_matches": numeric_matches,
        "numeric_term_total": len(numeric_terms),
    }


def calculate_metrics(turns: list[dict[str, Any]]) -> dict[str, Any]:
    answer_turns = [turn for turn in turns if turn["expected"]["outcome"] != "http_error"]
    route_passes = sum(turn["checks"]["route_pass"] is True for turn in answer_turns)
    leakage_count = sum(turn["checks"]["source_leakage"] is True for turn in answer_turns)

    required_chunks = sum(turn["checks"]["required_chunk_total"] for turn in answer_turns)
    supported_chunks = sum(len(turn["checks"]["required_chunk_matches"]) for turn in answer_turns)
    numeric_total = sum(turn["checks"]["numeric_term_total"] for turn in answer_turns)
    numeric_matches = sum(len(turn["checks"]["numeric_term_matches"]) for turn in answer_turns)
    high_risk = [turn for turn in answer_turns if turn["expected"]["risk_level"] in {"S2", "S3"}]
    high_risk_passes = sum(turn["checks"]["risk_pass"] is True for turn in high_risk)
    contraindication_turns = [
        turn for turn in answer_turns if turn["expected"]["blocked_food_tags"]
    ]
    contraindication_conflicts = sum(
        turn["checks"]["blocked_food_tags_pass"] is False for turn in contraindication_turns
    )
    multi_case_ids = {turn["case_id"] for turn in turns if turn["category"] == "multi_turn"}
    multi_passes = sum(
        all(turn["checks"]["multi_constraint_pass"] for turn in turns if turn["case_id"] == case_id)
        for case_id in multi_case_ids
    )
    first_latencies = [
        int(turn["first_response_ms"])
        for turn in turns
        if turn.get("first_response_ms") is not None
    ]
    total_latencies = [
        int(turn["total_response_ms"])
        for turn in turns
        if turn.get("total_response_ms") is not None
    ]
    http_errors = [turn for turn in turns if turn["expected"]["outcome"] == "http_error"]

    def rate(numerator: int, denominator: int) -> float:
        return round(numerator / denominator, 6) if denominator else 1.0

    return {
        "route_accuracy": rate(route_passes, len(answer_turns)),
        "route_passes": route_passes,
        "route_total": len(answer_turns),
        "source_leakage_rate": rate(leakage_count, len(answer_turns)),
        "source_leakage_turns": leakage_count,
        "numeric_fact_accuracy": rate(numeric_matches, numeric_total),
        "numeric_fact_matches": numeric_matches,
        "numeric_fact_total": numeric_total,
        "citation_support_rate": rate(supported_chunks, required_chunks),
        "citation_support_matches": supported_chunks,
        "citation_support_total": required_chunks,
        "high_risk_recall": rate(high_risk_passes, len(high_risk)),
        "high_risk_passes": high_risk_passes,
        "high_risk_total": len(high_risk),
        "contraindication_conflict_rate": rate(
            contraindication_conflicts, len(contraindication_turns)
        ),
        "contraindication_conflicts": contraindication_conflicts,
        "contraindication_total": len(contraindication_turns),
        "multi_turn_constraint_rate": rate(multi_passes, len(multi_case_ids)),
        "multi_turn_passes": multi_passes,
        "multi_turn_total": len(multi_case_ids),
        "unhandled_5xx": sum(int(turn["status_code"]) >= 500 for turn in turns),
        "first_response_p95_ms": percentile(first_latencies, 0.95),
        "total_response_p95_ms": percentile(total_latencies, 0.95),
        "turn_contract_rate": rate(
            sum(turn["checks"]["turn_contract_pass"] is True for turn in turns), len(turns)
        ),
        "http_error_contract_rate": rate(
            sum(turn["checks"]["http_contract_pass"] is True for turn in http_errors),
            len(http_errors),
        ),
    }


def apply_thresholds(metrics: dict[str, Any], thresholds: dict[str, Any]) -> dict[str, Any]:
    gates: dict[str, Any] = {}
    for metric, minimum in thresholds["minimums"].items():
        actual = metrics[metric]
        gates[metric] = {
            "operator": ">=",
            "threshold": minimum,
            "actual": actual,
            "status": "PASS" if actual >= minimum else "FAIL",
        }
    for metric, maximum in thresholds["maximums"].items():
        actual = metrics[metric]
        gates[metric] = {
            "operator": "<=",
            "threshold": maximum,
            "actual": actual,
            "status": "PASS" if actual is not None and actual <= maximum else "FAIL",
        }
    return gates
