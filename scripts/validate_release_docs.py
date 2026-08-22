"""Validate release documentation against the implemented data and release state."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "docs" / "evidence" / "phase-09-rc10-05-doc-validation.json"
REQUIRED_TEXT = {
    "README.md": [
        "https://106.14.13.139",
        "qwen3.7-plus",
        "RETRIEVAL_MODE=keyword",
        "docker compose up -d --build",
        "PRIVACY.md",
        "ACTION-05",
        "ACTION-06",
    ],
    "docs/AI_USAGE.md": [
        "OpenAI Codex",
        "2026-08-21",
        "qwen3.7-plus",
        "RETRIEVAL_MODE=keyword",
        "EMBEDDING_MODE=disabled",
        "ACTION-06 已关闭",
    ],
    "docs/02-architecture.md": [
        "Next.js",
        "FastAPI",
        "PostgreSQL",
        "KeywordRetriever",
        "Prompt",
        "服务繁忙，请稍后重试",
    ],
    "docs/03-rag-and-knowledge.md": [
        "core_nutrition",
        "auxiliary_platform",
        "EMBEDDING_MODE=disabled",
        "qwen3.7-plus",
    ],
    "docs/08-basic-test-records.md": [
        "我想减重",
        "A/B/C 隔离",
        "45 岁边界",
        "多轮和历史",
        "输入与系统错误",
    ],
    "PRIVACY.md": [
        "localStorage",
        "PostgreSQL",
        "阿里云百炼",
        "不会按 `.env` 自动 30 天清理",
    ],
    "SECURITY.md": ["Known limitations", "localStorage", "seven days"],
    "THIRD_PARTY_NOTICES.md": [
        "uv.lock",
        "package-lock.json",
        "not relicensed",
        "Bailian",
    ],
    "LICENSE": ["MIT License", "Competition materials"],
}
FORBIDDEN_TEXT = (
    "AI 工具/provider/model：`待填写`",
    "Phase 05 尚未开始",
    "公网 Render 地址仍等待",
    "最终 NOT_READY",
    "公网部署尚未完成",
    "Public deployment is not yet active",
    "remain behind ACTION-05",
)
REQUIRED_PATH_IDS = {
    "browser_identity",
    "account",
    "conversation",
    "health_profile",
    "operational_logs",
    "knowledge_and_evaluation",
}


def validate(root: Path = ROOT) -> dict[str, object]:
    errors: list[str] = []
    checks: list[dict[str, object]] = []
    for relative, phrases in REQUIRED_TEXT.items():
        path = root / relative
        if not path.is_file():
            errors.append(f"missing file: {relative}")
            continue
        text = path.read_text(encoding="utf-8")
        missing = [phrase for phrase in phrases if phrase not in text]
        forbidden = [phrase for phrase in FORBIDDEN_TEXT if phrase in text]
        if missing:
            errors.append(f"{relative} missing: {', '.join(missing)}")
        if forbidden:
            errors.append(f"{relative} contains stale text: {', '.join(forbidden)}")
        checks.append(
            {
                "path": relative,
                "required_phrases": len(phrases),
                "status": "PASS" if not missing and not forbidden else "FAIL",
            }
        )

    length_requirements = {
        "README.md": 500,
        "docs/02-architecture.md": 300,
    }
    for relative, minimum in length_requirements.items():
        text = (root / relative).read_text(encoding="utf-8")
        if len(text) < minimum:
            errors.append(f"{relative} shorter than {minimum} characters")
        checks.append(
            {
                "path": relative,
                "characters": len(text),
                "minimum_characters": minimum,
                "status": "PASS" if len(text) >= minimum else "FAIL",
            }
        )

    basic_tests = (root / "docs" / "08-basic-test-records.md").read_text(encoding="utf-8")
    basic_test_groups = sum(
        1 for line in basic_tests.splitlines() if line.startswith("| ") and ". " in line
    )
    if basic_test_groups < 5:
        errors.append("basic test record contains fewer than five groups")
    checks.append(
        {
            "path": "docs/08-basic-test-records.md",
            "test_groups": basic_test_groups,
            "status": "PASS" if basic_test_groups >= 5 else "FAIL",
        }
    )

    data_map_path = root / "docs" / "release-data-map.json"
    if not data_map_path.is_file():
        errors.append("missing file: docs/release-data-map.json")
    else:
        data_map = json.loads(data_map_path.read_text(encoding="utf-8"))
        path_ids = {item["id"] for item in data_map.get("paths", [])}
        if path_ids != REQUIRED_PATH_IDS:
            errors.append("release data map path ids differ from frozen set")
        if data_map.get("automatic_personal_data_retention_worker") is not False:
            errors.append("release data map must disclose absent automatic retention worker")
        if data_map.get("public_deployment_status") != "deployed https://106.14.13.139":
            errors.append("release data map must disclose the current public deployment")
        runtime = data_map.get("production_runtime", {})
        expected_runtime = {
            "llm_model": "qwen3.7-plus",
            "retrieval_mode": "keyword",
            "embedding_mode": "disabled",
            "conversation_store": "postgres",
            "health_profile_persistence": "ephemeral",
        }
        if any(runtime.get(key) != value for key, value in expected_runtime.items()):
            errors.append("release data map production runtime differs from deployed contract")
        checks.append(
            {
                "path": "docs/release-data-map.json",
                "data_paths": len(path_ids),
                "status": "PASS" if path_ids == REQUIRED_PATH_IDS else "FAIL",
            }
        )

    availability_path = root / "docs" / "evidence" / "phase-09-rc10-05-availability.json"
    availability = json.loads(availability_path.read_text(encoding="utf-8"))
    availability_rule = availability.get("availability_rule", {})
    availability_ok = (
        availability.get("status") == "COMMITTED"
        and availability.get("public_url") == "https://106.14.13.139"
        and availability_rule.get("duration_after_actual_competition_submission") == "P7D"
        and availability_rule.get("absolute_not_before") == "2026-08-30T01:00:00+08:00"
        and availability_rule.get("shutdown_before_minimum") == "forbidden"
    )
    if not availability_ok:
        errors.append("seven-day availability commitment is incomplete")
    checks.append(
        {
            "path": "docs/evidence/phase-09-rc10-05-availability.json",
            "status": "PASS" if availability_ok else "FAIL",
        }
    )

    return {
        "schema_version": 1,
        "captured_at": datetime.now(UTC).astimezone().isoformat(),
        "checks": checks,
        "error_count": len(errors),
        "errors": errors,
        "status": "PASS" if not errors else "FAIL",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = validate()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
