# HealthPick API

```powershell
uv run uvicorn healthpick_api.main:app --app-dir apps/api --host 127.0.0.1 --port 8010 --reload
```

- Health: `http://127.0.0.1:8010/healthz`
- OpenAPI UI（非 production）：`http://127.0.0.1:8010/docs`
- Chat contract: `POST /v1/chat/stream`，成功时返回严格以 `final` 结束的 SSE；失败时统一返回带 `request_id`、`code`、`message`、`retryable` 的 JSON 错误体。
- Profile preview: `POST /v1/profile/assess`，只校验和规范化最小结构化档案；返回 BMI 系统估算但不持久化。

未提供 `.env` 时 API 仍可启动，但 health 会把真实 LLM 标为 `not_configured`。开发 Mock 必须显式设置 `LLM_MODE=mock`；production 配置禁止 Mock。

## 请求边界与超时

- `MAX_REQUEST_BODY_BYTES` 默认 32768；超限在业务校验前返回稳定 `413 request_body_too_large`。
- Chat 消息去除首尾空白后长度为 1～2000，标题为 1～80；列表 limit 为 1～100。
- `LLM_TIMEOUT_SECONDS` 默认 30 秒，并区分超时、连接失败、限流、上游不可用、请求拒绝和协议错误。
- `DATABASE_CONNECT_TIMEOUT_SECONDS` 默认 5 秒；`DATABASE_STATEMENT_TIMEOUT_MS` 默认 5000 毫秒。
- 生成或证据校验失败不会写入对话历史；相同 `X-Request-ID` 的安全重试由数据库幂等约束兜底。

运行 P05-02 专用 smoke：

```powershell
.\.venv\Scripts\python.exe -B scripts\smoke_phase05_error_contract.py
```

## 本地真实模型基线

Ollama 的 OpenAI-compatible 端点可用于无云端凭据的真实 smoke：

```powershell
$env:LLM_MODE="real"
$env:LLM_PROVIDER="ollama_local"
$env:LLM_BASE_URL="http://127.0.0.1:11434/v1"
$env:LLM_API_KEY="ollama-local-no-secret"
$env:LLM_MODEL="qwen2.5:3b-instruct"
$env:EMBEDDING_MODE="real"
$env:EMBEDDING_PROVIDER="ollama_local"
$env:EMBEDDING_BASE_URL="http://127.0.0.1:11434/v1"
$env:EMBEDDING_API_KEY="ollama-local-no-secret"
$env:EMBEDDING_MODEL="qwen3-embedding:0.6b"
$env:EMBEDDING_DIMENSIONS="1024"
.\.venv\Scripts\python.exe scripts\smoke_real_models.py
```

本地基线用于可复现验收；比赛公网模型仍通过相同 adapter 由 Secret 注入，不把密钥提交到仓库。

## 健康档案本地探针

API 和 Web 启动后运行：

```powershell
.\.venv\Scripts\python.exe -B scripts\smoke_profile.py
```

档案在 Phase 04 只用于匿名会话级评估和 Chat 请求上下文。持久化属于 Phase 05；档案风险分级与禁忌硬过滤属于 P04-03。
