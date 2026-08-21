"""Compile human-curated YAML records into stable JSONL facts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "knowledge" / "normalized" / "curated"
OUTPUT = ROOT / "knowledge" / "normalized" / "facts"
MANIFEST = ROOT / "knowledge" / "manifests" / "sources.yaml"


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def route_policy(role: str) -> tuple[list[str], list[str]]:
    if role == "auxiliary_platform":
        return ["platform"], ["nutrition", "recommendation", "contraindication"]
    return ["nutrition", "recommendation", "contraindication"], ["platform"]


def common(source: dict[str, Any]) -> dict[str, Any]:
    allowed, forbidden = route_policy(source["source_role"])
    return {
        "schema_version": 1,
        "source_code": source["code"],
        "source_title": source["title"],
        "source_version": source["version"],
        "source_role": source["source_role"],
        "source_sha256": str(source["sha256"]).upper(),
        "allowed_routes": allowed,
        "forbidden_routes": forbidden,
    }


def review_info(
    dataset: dict[str, Any],
    source_code: str,
    pages: list[int],
    item: dict[str, Any],
) -> dict[str, Any]:
    status = item.get("review_status", dataset["review_status"])
    second_person_review = item.get("second_person_review")
    if status == "verified" and not second_person_review:
        item_id = item.get("id", "<unknown>")
        raise ValueError(
            f"{source_code}/{item_id}: verified requires second_person_review"
        )

    review = {
        "review_status": status,
        "first_pass_review": {
            "reviewer": dataset["first_pass_reviewer"],
            "date": dataset["first_pass_date"],
            "result": "passed_visual_parity",
            "evidence_images": [
                f"docs/evidence/phase-02-page-review/{source_code}-p{page:02d}.png"
                for page in pages
            ],
            "second_person_review_required": status != "verified",
        },
    }
    if second_person_review:
        review["second_person_review"] = second_person_review
    return review


def write_jsonl(name: str, records: list[dict[str, Any]]) -> Path:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / name
    temporary = path.with_suffix(".jsonl.tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    temporary.replace(path)
    return path


def main() -> int:
    manifest = load_yaml(MANIFEST)
    sources = {source["code"]: source for source in manifest["sources"]}

    foods = load_yaml(CURATED / "foods.yaml")
    food_records: list[dict[str, Any]] = []
    for item in foods["items"]:
        pages = [int(item["page"])]
        record = {
            **common(sources["A"]),
            "fact_id": f"food-A-{item['id']}",
            "food_name": item["name"],
            **{
                key: value
                for key, value in item.items()
                if key
                not in {"id", "name", "review_status", "second_person_review"}
            },
            **review_info(foods, "A", pages, item),
        }
        food_records.append(record)

    plans = load_yaml(CURATED / "plans.yaml")
    plan_records: list[dict[str, Any]] = []
    for item in plans["items"]:
        source_code = item["source"]
        pages = [int(page) for page in item["pages"]]
        record = {
            **common(sources[source_code]),
            "rule_id": f"rule-{source_code}-{item['id']}",
            **{
                key: value
                for key, value in item.items()
                if key
                not in {"id", "source", "review_status", "second_person_review"}
            },
            **review_info(plans, source_code, pages, item),
        }
        plan_records.append(record)

    platform = load_yaml(CURATED / "platform.yaml")
    platform_records: list[dict[str, Any]] = []
    for item in platform["items"]:
        pages = [int(page) for page in item["pages"]]
        record = {
            **common(sources["C"]),
            "fact_id": f"platform-C-{item['id']}",
            **{
                key: value
                for key, value in item.items()
                if key not in {"id", "review_status", "second_person_review"}
            },
            "claim_scope": "provided_whitepaper_only",
            **review_info(platform, "C", pages, item),
        }
        platform_records.append(record)

    outputs = (
        (write_jsonl("food_facts.jsonl", food_records), len(food_records)),
        (write_jsonl("plan_rules.jsonl", plan_records), len(plan_records)),
        (write_jsonl("platform_facts.jsonl", platform_records), len(platform_records)),
    )
    for path, count in outputs:
        print(f"{count} records -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
