# ADR-002：开发环境与部署基线

- 状态：已接受（含限时行动项）
- 日期：2026-08-21
- 阶段：Phase 01
- 决策人：Project Lead（参赛者）

## 决策

1. 项目使用独立 Git 仓库，默认分支为 `main`；Phase 01 初始化时尚无 commit。
2. Web 使用 Node.js `22.20.0`、npm `10.9.3` 和唯一 `package-lock.json`。
3. API 使用 Python `3.13.5`、uv 和唯一 `uv.lock`。若依赖解析证明确实不支持 Python 3.13，允许通过新 ADR 降到 Python 3.12，不得无记录地切换。
4. 源码、YAML、JSON、SQL 和 migration 统一 LF；PowerShell/Batch 使用 CRLF。历史 migration 一旦进入 release 只增不改。
5. 本地目标为 Docker Compose；当前机器未安装 Docker，Phase 02 先执行与运行时无关的数据规范化，Docker 必须在 T+12 前恢复。
6. 公网主路径选择 Render Blueprint：Next.js Web Service、FastAPI Web Service、Render PostgreSQL/pgvector。同一区域优先使用数据库 internal URL。
7. 公网备选为另一支持 Docker 的 HTTPS 平台；现场运行兜底为本地 Docker Compose 和预录演示。未获得用户授权前，不创建外部账号、不购买资源、不部署。
8. LLM 与 Embedding 通过 OpenAI-compatible adapter 接入；实际 provider、model、dimensions 和密钥必须在 T+6 前由项目负责人写入本地 Secret，不进入仓库。
9. Mock provider 只用于开发契约测试，禁止在比赛演示中伪装为动态模型；Embedding 暂不可用时可先构建结构化事实与关键词索引，但不能取消来源过滤和引用。

## 实测环境

| 项目 | Phase 01 实测值 | 状态 |
|---|---|---|
| OS/时区 | Windows / China Standard Time (UTC+08:00) | READY |
| Git | 2.51.1.windows.1 | READY |
| Node.js | 22.20.0 | READY |
| npm | 10.9.3 | READY |
| Python | 3.13.5 | READY |
| uv | Python 3.13 Scripts 中可用 | READY |
| Docker | 未找到命令 | ACTION-01 |
| psql | 未找到命令 | 可由 Compose/Render CLI 替代，ACTION-01 |
| Git `core.autocrlf` | `true` | 由 `.gitattributes` 覆盖仓库规则 |
| Git `core.eol` | 未设置 | 接受，由 `.gitattributes` 固定 |

## 限时行动项

| ID | 行动 | Owner | 截止时间 | 失败降级 |
|---|---|---|---|---|
| ACTION-01 | 安装/启用 Docker Desktop 并验证 Compose/PostgreSQL/pgvector | DEVOPS（单人模式为 Lead） | T+12 | Phase 02 仅产出数据文件；不得删除 Compose 交付项 |
| ACTION-02 | 提供可用 LLM provider、model、配额和 Secret，完成脱敏 smoke | API/Lead | T+6 | Mock 仅供开发；T+6 仍失败则切第二兼容 provider |
| ACTION-03 | 提供 Embedding model、dimensions 和 Secret，完成中文 smoke | API/Lead | T+6 | Phase 02 暂用关键词检索，维度未定前不建生产向量索引 |
| ACTION-04 | 建立远端 Git 仓库并授予 Render 只需的访问权限 | DEVOPS/Lead | T+12 | 本地继续开发，T+12 后仍未完成则标记发布阻塞 |
| ACTION-05 | 创建 Render 项目，确认区域、预算/套餐和 7 天可用性 | DEVOPS/Lead | T+12 | 切换备选 Docker 平台；不得等到 T+36 首次部署 |

涉及安装全局软件、创建外部账号、授权仓库或产生费用时，必须单独向用户说明影响并获得明确批准。

## 依据

- Render 官方的[多服务架构文档](https://render.com/docs/multi-service-architecture)覆盖 Next.js、FastAPI 与托管 PostgreSQL 的组合。
- Render 官方的[PostgreSQL 扩展清单](https://render.com/docs/postgresql-extensions)明确支持 `pgvector`，启用语句为 `CREATE EXTENSION vector;`。
- Render 官方[首次部署说明](https://render.com/docs/your-first-deploy)说明 Web Service 可获得 HTTPS 子域名，但免费 Web Service 可能休眠；最终演示前需根据预算选择稳定套餐或进行冷启动预检。

## 后果

优点是公网主环境可以用一份 Blueprint 管理，减少 48 小时内跨平台配置；本地仍能用 Compose 复现。代价是 Render 账号、套餐和仓库授权需要用户参与，Docker 缺失必须在 T+12 前处理。所有限时行动都不改变 A/B/C 隔离、安全门和引用校验。

