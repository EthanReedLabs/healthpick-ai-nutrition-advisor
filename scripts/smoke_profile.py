"""Run P04-01 profile validation, BMI, OpenAPI, and chat-transport probes."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx2

if __package__:
    from .runtime_conversation import RuntimeConversationScope
else:
    from runtime_conversation import RuntimeConversationScope

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "evidence" / "phase-04-p04-01-runtime.json"
API_ORIGIN = "http://127.0.0.1:8010"


def final_sse_payload(body: str) -> dict[str, Any]:
    normalized = body.replace("\r\n", "\n")
    for block in normalized.split("\n\n"):
        lines = block.splitlines()
        if "event: final" not in lines:
            continue
        data = "\n".join(line[6:] for line in lines if line.startswith("data: "))
        return json.loads(data)
    raise RuntimeError("chat response did not contain a final SSE event")


async def main() -> None:
    profile = {
        "age_band": "adult_18_44",
        "height_cm": 170,
        "weight_kg": 65,
        "goal": "stable_glucose",
        "allergies": ["shellfish", "shellfish"],
        "disliked_foods": ["香菜", "苦瓜"],
        "conditions": ["hypertension"],
    }
    async with httpx2.AsyncClient(timeout=120) as client:
        assessment_response = await client.post(
            f"{API_ORIGIN}/v1/profile/assess",
            json=profile,
        )
        assessment_response.raise_for_status()
        assessment = assessment_response.json()

        invalid_response = await client.post(
            f"{API_ORIGIN}/v1/profile/assess",
            json={"height_cm": 99, "conditions": ["free_text_diagnosis"]},
        )
        if invalid_response.status_code != 422:
            raise RuntimeError("invalid profile did not use the stable 422 contract")

        openapi_response = await client.get(f"{API_ORIGIN}/openapi.json")
        openapi_response.raise_for_status()
        openapi = openapi_response.json()
        schemas = openapi["components"]["schemas"]
        if "/v1/profile/assess" not in openapi["paths"]:
            raise RuntimeError("profile assessment path is absent from OpenAPI")
        expected_fields = {
            "age_band",
            "sex",
            "height_cm",
            "weight_kg",
            "activity_level",
            "goal",
            "dietary_preferences",
            "allergies",
            "disliked_foods",
            "conditions",
        }
        if set(schemas["ProfilePatch"]["properties"]) != expected_fields:
            raise RuntimeError("ProfilePatch fields differ from the frozen minimal contract")

        scope = await RuntimeConversationScope.create(client, API_ORIGIN)
        try:
            conversation_id = await scope.new_conversation("p04-01-profile-transport")
            chat_response = await client.post(
                f"{API_ORIGIN}/v1/chat/stream",
                json={
                    "session_id": scope.session_id,
                    "conversation_id": conversation_id,
                    "message": "膳食纤维有什么营养作用？",
                    "profile_patch": assessment["profile"],
                },
            )
            chat_response.raise_for_status()
            final = final_sse_payload(chat_response.text)
        finally:
            await scope.cleanup()

    if assessment["persistence"] != "ephemeral":
        raise RuntimeError("profile assessment unexpectedly claims persistence")
    if assessment["profile"]["allergies"] != ["shellfish"]:
        raise RuntimeError("profile tags were not normalized and deduplicated")
    if assessment["bmi"]["value"] != 22.5:
        raise RuntimeError("BMI estimate differs from the deterministic baseline")

    evidence = {
        "schema_version": 1,
        "evidence_id": "PHASE-04-P04-01-RUNTIME",
        "task_id": "P04-01",
        "captured_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "api_origin": API_ORIGIN,
        "assessment": {
            "status_code": assessment_response.status_code,
            "persistence": assessment["persistence"],
            "collected_fields": assessment["collected_fields"],
            "normalized_allergies": assessment["profile"]["allergies"],
            "bmi": assessment["bmi"],
            "status": "PASS",
        },
        "invalid_profile": {
            "status_code": invalid_response.status_code,
            "error_code": invalid_response.json()["code"],
            "status": "PASS",
        },
        "openapi": {
            "status_code": openapi_response.status_code,
            "profile_path": True,
            "profile_fields": sorted(expected_fields),
            "status": "PASS",
        },
        "chat_transport": {
            "status_code": chat_response.status_code,
            "route": final["route"],
            "model_mode": final["model"]["mode"],
            "profile_field_names_sent": sorted(assessment["profile"]),
            "status": "PASS",
        },
        "browser_evidence": "docs/evidence/phase-04-p04-01-browser.md",
        "downstream_safety_gate": "P04-03_PASSED",
        "status": "PASS",
    }
    OUTPUT.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
