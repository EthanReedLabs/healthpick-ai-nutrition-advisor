"""Exercise the live deterministic recommendation gate without exposing profile details."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "evidence" / "phase-04-p04-02-runtime.json"


def post_json(origin: str, payload: dict[str, object]) -> dict[str, object]:
    request = Request(
        f"{origin.rstrip('/')}/v1/recommendations/evaluate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=10) as response:  # noqa: S310 - fixed local API origin
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    origin = os.getenv("API_ORIGIN", "http://127.0.0.1:8010")
    cases = {
        "live_review_gate": post_json(
            origin,
            {"age_band": "adult_18_44", "sex": "female", "goal": "fat_loss"},
        ),
        "missing_goal": post_json(origin, {"age_band": "adult_18_44"}),
        "ambiguous_age": post_json(
            origin,
            {"age_band": "adult_45_64", "goal": "fat_loss"},
        ),
        "allergy_general_only": post_json(
            origin,
            {
                "age_band": "adult_18_44",
                "goal": "fat_loss",
                "allergies": ["shellfish"],
            },
        ),
        "kidney_general_only": post_json(
            origin,
            {
                "age_band": "adult_18_44",
                "goal": "fat_loss",
                "conditions": ["kidney_disease"],
            },
        ),
    }
    assert cases["live_review_gate"]["status"] == "blocked"
    assert cases["live_review_gate"]["primary"] is None
    assert cases["live_review_gate"]["requires_second_person_review"] is True
    assert len(cases["live_review_gate"]["blocked_rule_ids"]) == 3
    assert cases["missing_goal"]["blocked_reasons"] == ["missing_goal"]
    assert cases["ambiguous_age"]["blocked_reasons"] == ["age_outside_or_ambiguous_plan_scope"]
    assert cases["allergy_general_only"]["blocked_reasons"] == ["safety_s1_general_only"]
    assert cases["kidney_general_only"]["blocked_reasons"] == ["safety_s2_general_only"]

    report = {
        "schema_version": 1,
        "task_id": "P04-02",
        "status": "PASS_WITH_ACTION",
        "recorded_at": datetime.now().astimezone().isoformat(),
        "api_origin": origin,
        "generated_by": "deterministic_rules",
        "checks": {
            name: {
                "status": value["status"],
                "blocked_reasons": value["blocked_reasons"],
                "blocked_rule_count": len(value["blocked_rule_ids"]),
                "primary_present": value["primary"] is not None,
            }
            for name, value in cases.items()
        },
        "residual_action": "ACTION-06",
    }
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
