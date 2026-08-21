# Phase 01 Baseline Record

- Start：2026-08-21 16:47:07+08:00
- End：2026-08-21 16:50:46+08:00
- Execution mode：单人模式基线；Project Lead（参赛者）承担最终责任，职能 Owner 见 ownership baseline
- Repository：`D:/OPC_competition/healthpick-ai-nutrition-advisor`
- Branch：`main`
- Commit：`UNBORN`（新初始化仓库，尚未创建基线 commit）
- Host：Windows / China Standard Time (UTC+08:00)

## 1. 工具链实测

| Tool | Version/Result | Status |
|---|---|---|
| Git | `2.51.1.windows.1` | READY |
| Node.js | `22.20.0` | READY，已写 `.nvmrc` |
| npm | `10.9.3` | READY，Web 冻结为 npm + package-lock |
| Python | `3.13.5` | READY，已写 `.python-version` |
| uv | 可用，位于 Python 3.13 Scripts | READY，API 冻结为 uv + uv.lock |
| Docker | 命令不存在 | ACTION-01，T+12 前恢复 |
| psql | 命令不存在 | 由 Compose/Render CLI 路径承接 |
| Git `core.autocrlf` | `true` | 仓库由 `.gitattributes` 显式覆盖 |
| Git `core.eol` | 未设置 | 接受，由 `.gitattributes` 固定 |

## 2. 来源完整性

| Source | SHA-256 | Result |
|---|---|---|
| A | `44B9A8B1FFDDF08A6F6397563393CF1D786AB210036493DFD0F1DA5788BF4E18` | PASS |
| B | `65C5FF9E426CB49F92899106FE4E02FEA64C91F49880F51F8B517547C4A21BB3` | PASS |
| C | `015713384E28C91C4FA217FAA1F9B125DAFF166DFEDEA6BD67815258B2921DBC` | PASS |
| Competition DOCX | `7F8C6A81F5FB14ABD4AC20B6A9102C9F3CE8E5D250B907187FC82B80C2684499` | PASS |

实际 hash 全部存在于 `knowledge/manifests/sources.yaml`。A/B 为 `core_nutrition`；C 为 `auxiliary_platform`，且营养问答、推荐、食材事实和禁忌检查均列入 C 的禁止用途。

## 3. 外部资源就绪状态

| Resource | Primary | Fallback | Current result |
|---|---|---|---|
| LLM | OpenAI-compatible adapter，实际 provider/model 由 Secret 注入 | 第二 compatible provider；Mock 仅开发 | 未提供真实配置，ACTION-02，T+6 |
| Embedding | OpenAI-compatible adapter，model/dimensions 绑定 manifest | 先做结构化事实和关键词检索 | 未提供真实配置，ACTION-03，T+6 |
| Local DB | Docker Compose PostgreSQL + pgvector | Phase 02 先文件级 schema/smoke | Docker 缺失，ACTION-01，T+12 |
| Public deploy | Render Blueprint：Web/API/Postgres | 第二 Docker HTTPS 平台 + 本地录屏 | 账号/远端/预算未授权，ACTION-04/05，T+12 |

Render 路径只完成官方能力核验，未创建账号、未授权仓库、未购买资源、未部署。

## 4. 退出门禁

| Gate | Result | Evidence | Owner |
|---|---|---|---|
| G1 四份来源 hash 一致 | PASS | 本记录第 2 节、manifest | KNOWLEDGE |
| G2 A/B/C source_role 冻结 | PASS | `knowledge/manifests/sources.yaml` | KNOWLEDGE/API |
| G3 所有 P0 有 owner/test/evidence | PASS | `phase-01-ownership-baseline.md` + 追踪矩阵 | LEAD/QA_DOCS |
| G4 P1/P2 和非目标冻结 | PASS | ownership baseline、主执行方案 | LEAD |
| G5 技术主栈和最小契约冻结 | PASS | ADR-001、Phase 01 第 8 节 | LEAD/API/WEB |
| G6 工具链、lockfile、行尾规则确定 | PASS | ADR-002、`.nvmrc`、`.python-version`、`.gitattributes` | DEVOPS |
| G7 Secret 管理与 `.env` ignore 通过 | PASS | `.env` 不存在；check-ignore PASS；Secret token 命中 0 | DEVOPS/QA_DOCS |
| G8 主/备 provider 与部署路径明确 | PASS WITH ACTION | 本记录第 3 节、ADR-002 ACTION-01～05 | API/DEVOPS/LEAD |
| G9 Phase 02 任务全部 READY | PASS | `phase-02-ready-task-board.md` DATA-01～06 | LEAD |

## 5. 自动检查摘要

- README 本地断链：0
- manifest hash mismatch：0
- `sk-*` / Bearer 类真实 Token 命中：0
- 本地 `.env`：不存在
- `.env` ignore：通过（`.gitignore:2`）
- `.nvmrc`：`22.20.0`
- `.python-version`：`3.13.5`
- PowerShell 行尾：CRLF；源码默认：LF；PDF/DOCX：binary

## 6. 未决行动

| ID | Owner | Deadline | Completion evidence |
|---|---|---|---|
| ACTION-01 Docker/Compose/PostgreSQL/pgvector | DEVOPS/Lead | T+12 | `docker version`、Compose health、`SELECT extversion` |
| ACTION-02 LLM provider/model/quota smoke | API/Lead | T+6 | 脱敏状态码、model、latency、request ID |
| ACTION-03 Embedding model/dimensions/中文 smoke | API/Lead | T+6 | 脱敏结果与维度，更新 manifest |
| ACTION-04 远端 Git 仓库与最小权限 | DEVOPS/Lead | T+12 | remote URL 和匿名读取/构建检查 |
| ACTION-05 Render 区域、预算、7 天可用性 | DEVOPS/Lead | T+12 | 项目配置与健康检查，不记录 Secret |

上述动作涉及安装全局软件、账号/仓库授权或费用，执行前需要用户单独批准。

## 7. Decision

`PASS WITH ACTION`

Phase 02 的 DATA-01～05 可以立即开始；DATA-06 在 Docker/PostgreSQL 未恢复前只能执行文件级隔离 smoke。Phase 03 动态模型闭环在 ACTION-02/03 未完成前不得宣称已打通。

- Lead sign-off：Project Lead（参赛者，按“按计划进入第一阶段”授权执行）
- Execution record prepared by：Codex

