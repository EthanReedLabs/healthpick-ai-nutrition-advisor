# HealthPick API

```powershell
uv run uvicorn healthpick_api.main:app --app-dir apps/api --host 127.0.0.1 --port 8010 --reload
```

- Health: `http://127.0.0.1:8010/healthz`
- OpenAPI UI（非 production）：`http://127.0.0.1:8010/docs`
- Chat contract: `POST /v1/chat/stream`，在 P03-05 前明确返回 `chat_not_ready`，不会返回硬编码答案。

未提供 `.env` 时 API 仍可启动，但 health 会把真实 LLM 标为 `not_configured`。开发 Mock 必须显式设置 `LLM_MODE=mock`；production 配置禁止 Mock。
