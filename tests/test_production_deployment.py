from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_yaml(path: str) -> dict[str, object]:
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))


def test_base_compose_supports_loopback_bind_overrides() -> None:
    compose = load_yaml("compose.yaml")
    services = compose["services"]

    assert services["postgres"]["ports"] == [
        "${POSTGRES_BIND_ADDRESS:-0.0.0.0}:${POSTGRES_PORT:-54329}:5432"
    ]
    assert services["api"]["ports"] == [
        "${API_BIND_ADDRESS:-0.0.0.0}:${API_PORT:-8010}:8010"
    ]
    assert services["web"]["ports"] == [
        "${WEB_BIND_ADDRESS:-0.0.0.0}:${WEB_PORT:-3000}:3000"
    ]


def test_production_overlay_exposes_only_caddy_publicly() -> None:
    production = load_yaml("compose.production.yaml")
    caddy = production["services"]["caddy"]

    assert caddy["image"] == "caddy:2.11.4-alpine"
    assert caddy["ports"] == ["80:80", "443:443", "443:443/udp"]
    assert caddy["security_opt"] == ["no-new-privileges:true"]
    assert caddy["restart"] == "unless-stopped"

    env_text = (ROOT / "infra" / "ecs.env.example").read_text(encoding="utf-8")
    assert "POSTGRES_BIND_ADDRESS=127.0.0.1" in env_text
    assert "API_BIND_ADDRESS=127.0.0.1" in env_text
    assert "WEB_BIND_ADDRESS=127.0.0.1" in env_text
    assert "COMPOSE_LLM_MODE=real" in env_text
    assert "COMPOSE_LLM_MODEL=qwen3.7-plus" in env_text
    assert "PUBLIC_HOST=106.14.13.139" in env_text
    assert "COMPOSE_PUBLIC_API_ORIGIN=https://106.14.13.139" in env_text
    assert (
        "COMPOSE_LLM_BASE_URL=https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
        in env_text
    )
    assert "replace-with-token-plan-bailian-secret" in env_text


def test_ecs_runbook_requires_image_only_no_build_deployment() -> None:
    runbook = (ROOT / "docs" / "deployment" / "ecs-production.md").read_text(
        encoding="utf-8"
    )

    assert "不接收应用源码" in runbook
    assert "docker load" in runbook
    assert "--no-build" in runbook
    assert "compose.production.yaml build" not in runbook


def test_caddy_routes_api_and_web_through_one_https_origin() -> None:
    caddyfile = (ROOT / "infra" / "caddy" / "Caddyfile").read_text(encoding="utf-8")

    assert "{$PUBLIC_HOST}" in caddyfile
    assert "default_sni {$PUBLIC_HOST}" in caddyfile
    assert "issuer acme https://acme-v02.api.letsencrypt.org/directory" in caddyfile
    assert "profile shortlived" in caddyfile
    assert "@api path /v1/* /healthz /openapi.json /docs* /redoc*" in caddyfile
    assert "reverse_proxy api:8010" in caddyfile
    assert "reverse_proxy web:3000" in caddyfile
    assert "X-Content-Type-Options" in caddyfile
    assert "Permissions-Policy" in caddyfile
