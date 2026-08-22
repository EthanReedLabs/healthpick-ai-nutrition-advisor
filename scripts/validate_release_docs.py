"""Validate release documentation against the implemented data and release state."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "docs" / "evidence" / "phase-08-p08-03-doc-validation.json"
REQUIRED_TEXT = {
    "README.md": ["254", "docker compose up -d --build", "PRIVACY.md", "ACTION-05", "ACTION-06"],
    "docs/AI_USAGE.md": ["OpenAI Codex", "2026-08-21", "254", "ACTION-06"],
    "PRIVACY.md": [
        "localStorage",
        "PostgreSQL",
        "配置的模型 Provider",
        "不会按 `.env` 自动 30 天清理",
    ],
    "SECURITY.md": ["Known limitations", "localStorage", "ACTION-05"],
    "THIRD_PARTY_NOTICES.md": ["uv.lock", "package-lock.json", "not relicensed"],
    "LICENSE": ["MIT License", "Competition materials"],
}
FORBIDDEN_TEXT = ("AI 工具/provider/model：`待填写`", "Phase 05 尚未开始")
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
        if data_map.get("public_deployment_status") != "pending ACTION-05":
            errors.append("release data map must keep public deployment pending")
        checks.append(
            {
                "path": "docs/release-data-map.json",
                "data_paths": len(path_ids),
                "status": "PASS" if path_ids == REQUIRED_PATH_IDS else "FAIL",
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
