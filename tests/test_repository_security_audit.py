from pathlib import Path

from scripts.audit_repository_security import scan_file


def test_secret_scan_never_returns_candidate_values(tmp_path: Path) -> None:
    candidate = "sk-" + "a" * 32
    path = tmp_path / "settings.json"
    path.write_text('{"API_KEY": "' + candidate + '"}', encoding="utf-8")

    findings, is_binary = scan_file(path, "settings.json")

    assert not is_binary
    assert [(item.path, item.line, item.rule) for item in findings] == [
        ("settings.json", 1, "openai_style_token"),
        ("settings.json", 1, "secret_assignment"),
    ]
    assert candidate not in repr(findings)


def test_secret_scan_allows_documented_placeholders(tmp_path: Path) -> None:
    path = tmp_path / ".env.example"
    path.write_text(
        "API_KEY=replace-with-local-secret\nDATABASE_URL=postgresql://u:replace-with-local-secret@db/x\n",
        encoding="utf-8",
    )

    findings, is_binary = scan_file(path, ".env.example")

    assert not is_binary
    assert findings == []


def test_secret_scan_allows_compose_environment_interpolation(tmp_path: Path) -> None:
    path = tmp_path / "compose.yaml"
    path.write_text("API_KEY: ${API_KEY:-local-placeholder}\n", encoding="utf-8")

    findings, is_binary = scan_file(path, "compose.yaml")

    assert not is_binary
    assert findings == []


def test_secret_scan_allows_ollama_compatibility_dummy_key(tmp_path: Path) -> None:
    path = tmp_path / ".env.example"
    path.write_text("COMPOSE_LLM_API_KEY=ollama-local\n", encoding="utf-8")

    findings, is_binary = scan_file(path, ".env.example")

    assert not is_binary
    assert findings == []


def test_secret_scan_rejects_environment_and_private_key_files(tmp_path: Path) -> None:
    environment = tmp_path / ".env.production"
    environment.write_text("SAFE=true\n", encoding="utf-8")
    private_key = tmp_path / "release.pem"
    private_key.write_text("placeholder certificate container", encoding="utf-8")

    environment_findings, _ = scan_file(environment, ".env.production")
    key_findings, _ = scan_file(private_key, "release.pem")

    assert [item.rule for item in environment_findings] == ["forbidden_environment_file"]
    assert [item.rule for item in key_findings] == ["private_key_container"]


def test_secret_scan_allows_loopback_script_default_but_not_evidence(tmp_path: Path) -> None:
    uri = "postgresql://user:" + "candidatecredential" + "@127.0.0.1:5432/db"
    path = tmp_path / "candidate.txt"
    path.write_text(uri, encoding="utf-8")

    script_findings, _ = scan_file(path, "scripts/local_smoke.py")
    evidence_findings, _ = scan_file(path, "docs/evidence/runtime.json")

    assert script_findings == []
    assert [item.rule for item in evidence_findings] == ["credential_in_uri"]
