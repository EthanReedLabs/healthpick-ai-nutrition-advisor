"""Scan the submission candidate for accidentally committed secrets.

The report intentionally contains only rule identifiers and locations. It never
copies a candidate value into console output or evidence files.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "docs" / "evidence" / "phase-08-p08-01-secret-scan.json"

FORBIDDEN_SUFFIXES = {".key", ".p12", ".pfx", ".pem"}
ASSIGNMENT_SUFFIXES = {".cfg", ".env", ".ini", ".json", ".properties", ".toml", ".yaml", ".yml"}
PLACEHOLDER_MARKERS = (
    "***",
    "$",
    "${",
    "{{",
    "<",
    "changeme",
    "dummy",
    "example",
    "fake",
    "local-secret",
    "mock",
    "ollama-local",
    "placeholder",
    "redacted",
    "replace-with",
    "secretstr",
    "test-secret",
)

TEXT_RULES = (
    ("private_key_material", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("aws_access_key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("github_token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}\b")),
    ("github_fine_grained_token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{40,}\b")),
    ("openai_style_token", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
)
ASSIGNMENT = re.compile(
    r"(?im)^\s*\{?\s*[\"']?(?:[A-Z0-9_]*(?:API_KEY|SECRET|PASSWORD|TOKEN|DSN))\b"
    r"[\"']?\s*[=:]\s*[\"']?([^\s\"'\r\n,#{}]+)"
)
URI_CREDENTIAL = re.compile(
    r"(?i)\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://"
    r"([^/\s:@]+):([^@\s/]+)@([^:/\s]+)"
)


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    rule: str


def _candidate_files(root: Path) -> list[Path]:
    command = ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"]
    result = subprocess.run(command, cwd=root, check=True, capture_output=True)
    paths = []
    for raw_path in result.stdout.split(b"\0"):
        if not raw_path:
            continue
        path = root / raw_path.decode("utf-8", errors="strict")
        if path.is_file():
            paths.append(path)
    return sorted(paths)


def _is_placeholder(value: str) -> bool:
    normalized = value.strip().strip("\"'").lower()
    if normalized in {"", "false", "none", "null", "true"}:
        return True
    return any(marker in normalized for marker in PLACEHOLDER_MARKERS)


def _line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def scan_file(path: Path, relative_path: str) -> tuple[list[Finding], bool]:
    findings: list[Finding] = []
    name = path.name.lower()
    if name == ".env" or (name.startswith(".env.") and name != ".env.example"):
        findings.append(Finding(relative_path, 1, "forbidden_environment_file"))
    if path.suffix.lower() in FORBIDDEN_SUFFIXES:
        findings.append(Finding(relative_path, 1, "private_key_container"))

    raw = path.read_bytes()
    if b"\0" in raw[:8192]:
        return findings, True
    text = raw.decode("utf-8", errors="replace")

    for rule, pattern in TEXT_RULES:
        for match in pattern.finditer(text):
            findings.append(Finding(relative_path, _line_number(text, match.start()), rule))

    for match in URI_CREDENTIAL.finditer(text):
        password = match.group(2)
        host = match.group(3).lower()
        local_development_source = host in {"127.0.0.1", "localhost"} and relative_path.startswith(
            ("scripts/", "tools/")
        )
        if not _is_placeholder(password) and not local_development_source:
            findings.append(
                Finding(relative_path, _line_number(text, match.start()), "credential_in_uri")
            )

    if path.suffix.lower() in ASSIGNMENT_SUFFIXES or name.startswith(".env"):
        for match in ASSIGNMENT.finditer(text):
            if not _is_placeholder(match.group(1)):
                findings.append(
                    Finding(relative_path, _line_number(text, match.start()), "secret_assignment")
                )
    return findings, False


def audit(root: Path) -> dict[str, object]:
    findings: list[Finding] = []
    binary_files = 0
    candidates = _candidate_files(root)
    for path in candidates:
        relative_path = path.relative_to(root).as_posix()
        file_findings, is_binary = scan_file(path, relative_path)
        findings.extend(file_findings)
        binary_files += int(is_binary)
    return {
        "schema_version": 1,
        "captured_at": datetime.now(UTC).astimezone().isoformat(),
        "scope": "git tracked and untracked non-ignored submission candidates",
        "scanned_files": len(candidates),
        "binary_files_location_checked": binary_files,
        "finding_count": len(findings),
        "findings": [asdict(finding) for finding in findings],
        "redaction_policy": "candidate values are never emitted",
        "status": "PASS" if not findings else "FAIL",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    root = args.root.resolve()
    report = audit(root)
    output = args.output if args.output.is_absolute() else root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
