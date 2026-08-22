# Infrastructure

- `docker/`：镜像和 Compose 相关配置；
- `migrations/`：数据库结构与版本迁移。

目标交付形态是公网 HTTPS 演示环境与 Docker Compose 本地复现并存。任何部署配置不得包含真实 Secret；生产迁移必须先在空库和已有数据副本上验证。

## 本地全栈

仓库根目录的 `compose.yaml` 固定使用 PostgreSQL 17 与 pgvector 0.8.6，并按以下顺序启动：

`PostgreSQL healthy -> migrate completed -> seed completed -> API healthy -> Web`

默认宿主端口为 PostgreSQL `54329`、API `8010`、Web `3000`。默认真实模型端点是宿主机 Ollama `http://127.0.0.1:11434`，模型为 `qwen2.5:3b-instruct`。

```powershell
$env:POSTGRES_DB="healthpick"
$env:POSTGRES_USER="healthpick"
$env:POSTGRES_PASSWORD="仅供本机的随机密码"
$env:COMPOSE_PUBLIC_API_ORIGIN="http://127.0.0.1:8010"
docker compose up -d --build
.\tools\smoke_db.ps1
```

Compose 的应用覆盖变量统一使用 `COMPOSE_*` 前缀（例如 `COMPOSE_LLM_MODEL`、`COMPOSE_LLM_BASE_URL`），避免部署用 `.env` 中的同名变量污染本地容器。PostgreSQL 连接变量仍使用 `POSTGRES_*`。

迁移器每次启动都会按文件名顺序核对 canonical SHA-256：空库执行迁移，结构完整的历史库只登记安全基线，部分结构会拒绝启动。已经进入发布基线的迁移只允许新增，不允许修改；文本迁移由 `.gitattributes` 固定为 LF，校验和同时兼容 CRLF/LF 工作区。

种子器在单事务内验证 A/B/C 清单与源文件哈希，执行 upsert 和陈旧数据清理，并强制校验精确行数及资料 C 路由隔离。迁移或种子失败时 API 不会启动。
