from __future__ import annotations

from healthpick_api.evaluation.release_golden import ReleaseExpectation
from healthpick_api.evaluation.release_runner import apply_thresholds, calculate_metrics, score_turn


def expectation(**overrides: object) -> ReleaseExpectation:
    values: dict[str, object] = {
        "route": "nutrition",
        "allowed_sources": ["A", "B"],
        "forbidden_sources": ["C"],
        "risk_level": "S0",
        "response_mode": "normal",
        "required_chunk_ids": ["A-p01-c04"],
        "required_terms": ["25"],
    }
    values.update(overrides)
    return ReleaseExpectation.model_validate(values)


def passing_final() -> dict[str, object]:
    return {
        "route": "nutrition",
        "answer": "每天建议 25 克。【A-p01-c04】",
        "citations": [{"chunk_id": "A-p01-c04", "source": "A"}],
        "retrieval_trace": {
            "evidence_gate": "passed",
            "selections": [{"chunk_id": "A-p01-c04", "source": "A"}],
        },
        "safety": {"risk_level": "S0", "response_mode": "normal", "blocked_food_tags": []},
    }


def turn_result(checks: dict[str, object]) -> dict[str, object]:
    expected = expectation().model_dump(mode="json")
    return {
        "case_id": "ANUT-01",
        "category": "a_nutrition",
        "expected": expected,
        "status_code": 200,
        "first_response_ms": 100,
        "total_response_ms": 120,
        "checks": checks,
    }


def test_score_turn_requires_inline_support_and_rejects_source_leakage() -> None:
    passing = score_turn(expectation(), status_code=200, final=passing_final(), error=None)
    assert passing["turn_contract_pass"] is True
    assert passing["multi_constraint_pass"] is True
    assert passing["required_chunk_matches"] == ["A-p01-c04"]

    leaking = passing_final()
    leaking["citations"] = [{"chunk_id": "C-p01-c01", "source": "C"}]
    leaking["retrieval_trace"] = {
        "evidence_gate": "passed",
        "selections": [{"chunk_id": "C-p01-c01", "source": "C"}],
    }
    failed = score_turn(expectation(), status_code=200, final=leaking, error=None)
    assert failed["source_leakage"] is True
    assert failed["turn_contract_pass"] is False
    assert failed["multi_constraint_pass"] is False


def test_http_error_contract_is_scored_without_answer_metrics() -> None:
    expected = expectation(
        outcome="http_error",
        http_status=422,
        error_code="validation_error",
        route=None,
        allowed_sources=[],
        forbidden_sources=[],
        risk_level=None,
        response_mode=None,
        required_chunk_ids=[],
        required_terms=[],
        require_citations=False,
        require_retrieval_trace=False,
    )
    checks = score_turn(
        expected,
        status_code=422,
        final=None,
        error={"code": "validation_error"},
    )
    assert checks["http_contract_pass"] is True
    assert checks["turn_contract_pass"] is True
    assert checks["multi_constraint_pass"] is True
    assert checks["route_pass"] is None


def test_metrics_and_frozen_thresholds_are_deterministic() -> None:
    checks = score_turn(expectation(), status_code=200, final=passing_final(), error=None)
    metrics = calculate_metrics([turn_result(checks)])
    assert metrics["route_accuracy"] == 1.0
    assert metrics["numeric_fact_accuracy"] == 1.0
    assert metrics["citation_support_rate"] == 1.0
    assert metrics["source_leakage_rate"] == 0.0
    assert metrics["first_response_p95_ms"] == 100

    thresholds = {
        "minimums": {"route_accuracy": 0.95},
        "maximums": {"source_leakage_rate": 0.0, "first_response_p95_ms": 5000},
    }
    gates = apply_thresholds(metrics, thresholds)
    assert {gate["status"] for gate in gates.values()} == {"PASS"}
