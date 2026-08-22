"""Load the packaged, sanitized release evaluation summary."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from healthpick_api.models import EvaluationSummaryResponse

PUBLIC_SUMMARY_PATH = Path(__file__).with_name("release-summary-v1.1.json")


@lru_cache(maxsize=1)
def load_public_evaluation_summary() -> EvaluationSummaryResponse:
    return EvaluationSummaryResponse.model_validate_json(
        PUBLIC_SUMMARY_PATH.read_text(encoding="utf-8")
    )
