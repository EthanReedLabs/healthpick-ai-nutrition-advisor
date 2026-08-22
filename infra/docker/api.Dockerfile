# syntax=docker/dockerfile:1.7

FROM ghcr.io/astral-sh/uv:0.8.17 AS uv

FROM python:3.13-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:${PATH}"

WORKDIR /app

RUN groupadd --system healthpick \
    && useradd --system --gid healthpick --home-dir /nonexistent healthpick

COPY --from=uv /uv /uvx /bin/
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY apps/api ./apps/api
COPY scripts/migrate_database.py scripts/seed_database.py ./scripts/
COPY infra/migrations ./infra/migrations
COPY knowledge/manifests ./knowledge/manifests
COPY knowledge/normalized ./knowledge/normalized

USER healthpick

EXPOSE 8010

CMD ["uvicorn", "healthpick_api.main:app", "--app-dir", "apps/api", "--host", "0.0.0.0", "--port", "8010"]
