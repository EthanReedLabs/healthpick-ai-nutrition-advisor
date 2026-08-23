import subprocess
from pathlib import Path

from scripts.audit_git_history_security import audit


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def test_history_audit_finds_secret_removed_from_head_without_returning_value(
    tmp_path: Path,
) -> None:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.name", "Security Test")
    _git(tmp_path, "config", "user.email", "security@example.invalid")
    candidate = "sk-" + "c" * 32
    settings = tmp_path / "settings.json"
    settings.write_text('{"API_KEY": "' + candidate + '"}', encoding="utf-8")
    _git(tmp_path, "add", "settings.json")
    _git(tmp_path, "commit", "-m", "historical candidate")
    settings.write_text('{"API_KEY": "replace-with-local-secret"}', encoding="utf-8")
    _git(tmp_path, "add", "settings.json")
    _git(tmp_path, "commit", "-m", "replace with placeholder")

    report = audit(tmp_path)

    assert report["status"] == "FAIL"
    assert report["finding_count"] == 2
    assert {item["rule"] for item in report["findings"]} == {
        "openai_style_token",
        "secret_assignment",
    }
    assert candidate not in repr(report)
