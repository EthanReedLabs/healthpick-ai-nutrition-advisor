# 第一阶段详细实施计划：基线与范围冻结

## 1. 阶段定义

| 项目 | 内容 |
|---|---|
| 阶段编号 | Phase 01 |
| 时间窗口 | T+0:00～T+2:00 |
| 阶段目标 | 在写业务代码前冻结“做什么、用什么、谁负责、如何验收、失败如何降级” |
| 主负责人 | 项目负责人 / Tech Lead |
| 参与者 | Web、API/RAG、知识/评测、DevOps；单人参赛时由本人按顺序执行 |
| 前置输入 | 赛题 DOCX、A/B/C 三份 PDF、主执行方案、需求追踪矩阵、ADR-001 |
| 下一阶段 | Phase 02：知识数据生产化处理（T+2～6h） |

本阶段不是讨论会，也不是开始堆功能。它要产出一个可以签字的冻结包，使后续每项代码都能追溯到需求 ID、验收断言和证据位置。两小时结束时，即使个别外部资源仍未到位，也必须已经确定 owner、截止点和可执行的备用路径。

## 2. 成功标准

阶段结束必须同时满足：

1. A/B/C 和赛题 DOCX 哈希复核通过，来源角色不可被代码或 Prompt 覆盖；
2. 所有 P0 需求都有 owner、实现位置、验收方法和证据路径；
3. P1/P2 边界冻结，新增需求只能通过变更记录进入；
4. 技术主栈、最小 API/数据契约和真正需要可替换的轴心已经确定；
5. 开发工具链、包管理器、行尾策略和迁移不可变规则已记录；
6. LLM、Embedding、数据库和部署环境至少各有主路径与降级路径；
7. `.env.example` 完整、真实密钥未入库、日志不得输出密钥；
8. Phase 02 的任务卡已到 `READY`，执行者无需再次讨论范围即可开工。

任何一项缺少可复核证据，都不能标记为 `PASS`。

## 3. 本阶段不做什么

- 不解析生产知识 Chunk，不手抄 PDF 表格；
- 不开发聊天 UI、推荐算法或账号系统；
- 不因为“以后可能用”引入消息队列、缓存集群、微服务或复杂索引；
- 不测试真实健康结论，也不把 OCR 文本当作知识真值；
- 不在群聊、截图、提交记录或日志中粘贴 API Key；
- 不修改已归档的 A/B/C 原始文件。

## 4. 冻结包产物

| 编号 | 产物 | 路径/记录位置 | Owner | 验收 |
|---|---|---|---|---|
| P01-01 | 范围基线 | `docs/01-requirements-traceability.md` | Lead | P0 无空 owner/测试/证据 |
| P01-02 | 技术决策 | `docs/decisions/ADR-001-technology-stack.md` | API/Lead | 状态为 Accepted，无未决主栈 |
| P01-03 | 来源基线 | `knowledge/manifests/sources.yaml` | Knowledge | 文件、角色、版本、页数、哈希完整 |
| P01-04 | 环境契约 | `.env.example` | DevOps/API | 主/备 provider 和安全配置字段齐全 |
| P01-05 | 仓库策略 | `.gitignore`、待创建 `.gitattributes` | DevOps | `.env` 被忽略，行尾规则明确 |
| P01-06 | 最小接口契约 | 本文第 8 节，Phase 03 前固化为 OpenAPI | Web/API | 请求、响应、错误和流式事件一致 |
| P01-07 | 风险与降级表 | 本文第 11 节 | Lead | 每个阻塞有触发条件和决策人 |
| P01-08 | 阶段验收记录 | `docs/evidence/phase-01-baseline-record.md` | Lead | 所有门禁有实际值、时间和签字 |
| P01-09 | 下一阶段任务卡 | 任务看板或验收记录中的 Phase 02 区域 | Knowledge/API | 每项均满足 Ready 定义 |

`phase-01-baseline-record.md` 在真正开始计时时创建，不能预先伪造 PASS；模板见本文第 13 节。

## 5. 两小时执行时间表

| 时间 | 任务 | 执行人 | 输出 | 硬停止点 |
|---:|---|---|---|---|
| 00:00–00:10 | 建立计时、参与人、仓库和证据记录 | Lead | 启动记录、当前 commit/branch | 10 分钟必须进入资料核验 |
| 00:10–00:25 | 复核四份原始资料、hash、A/B/C 角色 | Knowledge + Lead | 来源核验 PASS/FAIL | hash 不同立即停止并找正确原件 |
| 00:25–00:50 | 逐行复核 P0，分配 owner、测试和证据 | 全员 | P0 基线 | 未能在 25 分钟内决定的项由 Lead 裁决 |
| 00:50–01:05 | 冻结 P1/P2、非目标和降级顺序 | Lead + Product | 范围冻结记录 | P2 不得占用 0–24h 主链路 |
| 01:05–01:25 | 冻结架构轴心、最小接口和数据枚举 | Web + API | 契约 v0 | 不讨论非核心抽象 |
| 01:25–01:40 | 盘点工具链、包管理、行尾和 Secret | DevOps | 环境矩阵 | 不在此阶段临时升级全局工具 |
| 01:40–01:50 | 验证外部资源和主/备路径 | API + DevOps | provider/deploy readiness | 失败必须选择降级，不无限排查 |
| 01:50–01:58 | 建立 Phase 02 任务卡、依赖和并行关系 | Lead | READY backlog | 每项包含输入、输出、验收 |
| 01:58–02:00 | 执行退出门禁并签字 | Lead | PASS 或 BLOCKED | 只有 Lead 可宣布进入 Phase 02 |

## 6. 步骤一：启动和仓库基线（00:00–00:10）

### 操作

1. 从项目根目录启动计时，记录实际开始时间、参赛者、机器和网络环境。
2. 确认 Git 仓库边界，不要把整个 Downloads 或上级私人目录纳入仓库。
3. 记录当前分支、commit 和工作区状态；存在用户已有改动时先标注归属，不覆盖。
4. 确认主分支保护策略：短分支开发、PR/自审后合并，T+36 后禁止功能性大合并。
5. 若尚未初始化代码仓库，才执行 `git init`；已有仓库不得重复初始化。

### 只读检查命令（PowerShell）

```powershell
Set-Location D:\OPC_competition\healthpick-ai-nutrition-advisor
git rev-parse --show-toplevel
git branch --show-current
git rev-parse --short HEAD
git status --short
```

如果仓库还没有首个 commit，记录 `UNBORN`，不得用虚构 hash 代替。

### 产出

- `phase_start_at`、人员/角色、repo root、branch、commit；
- 当前未提交文件清单及归属；
- 主分支和短分支命名规则。

## 7. 步骤二：资料与知识边界核验（00:10–00:25）

### 操作

1. 对四份原件重新计算 SHA-256，与 manifest 比较；
2. 人工打开首页/标题页，复核文件没有因重命名而对错；
3. 再确认边界：A/B=`core_nutrition`，C=`auxiliary_platform`；
4. 明确 C 的禁止用途包括营养问答、方案推荐、食材事实和禁忌检查；
5. 记录原件只读，后续解析结果只能进入 `knowledge/normalized/`。

### 检查命令

```powershell
Get-FileHash knowledge\raw\A-2026-fall-healthy-diet-guide.pdf -Algorithm SHA256
Get-FileHash knowledge\raw\B-personalized-diet-plan.pdf -Algorithm SHA256
Get-FileHash knowledge\raw\C-healthpick-service-whitepaper.pdf -Algorithm SHA256
Get-FileHash docs\source\competition-brief.docx -Algorithm SHA256
Get-Content -Raw knowledge\manifests\sources.yaml
```

### 失败处理

- hash 不一致：标记 `BLOCKED-SOURCE`，停止知识处理，回到用户提供的原件重新复制并新增版本记录；
- 文件能打开但标题/版本不符：不得只改 manifest 迎合文件；先确认正确来源；
- 资料边界有争议：采用更严格边界，C 仍不得进入营养检索。

## 8. 步骤三：P0 范围与最小契约冻结（00:25–01:25）

### 8.1 P0 必保范围

下列能力不得因时间不足被删除：

- A/B/C 知识挂载、准确问答、引用和 0 串库；
- 动态 LLM、推荐 1–2 个方案、禁忌识别与专业提示；
- 多轮约束记忆、会话管理和错误反馈；
- 响应式 Web、公开 HTTPS、Docker Compose 本地复现；
- 文档、测试、AI 使用披露和真实 Secret 保护。

负责人逐行检查 `docs/01-requirements-traceability.md`。每个 P0 补齐以下字段：

```text
Requirement ID / Owner / Implementation path / Test ID / Evidence path / Deadline
```

P1 只在 T+24 后进入，P2 只在 T+30 且所有 P0 回归全绿后进入。新增功能必须说明它替代哪个既有任务以及对 P0 的影响。

### 8.2 变化轴心冻结

只对以下确定会变且替换成本高的部分定义 adapter：

| 轴心 | 灵活度 | 冻结决定 |
|---|---|---|
| LLM provider/model | A | `LLMProvider` 协议，支持主/备实现和 Mock |
| Embedding provider/model/dimensions | A | 独立 adapter；维度写入 manifest 并绑定索引版本 |
| 部署目标 | B | 公网主环境 + Docker Compose 兜底，业务代码不感知平台 |
| PostgreSQL、FastAPI、Next.js | C | 比赛版本直接锁定，不做无收益的多数据库/多框架抽象 |
| A/B/C 来源角色 | C/规则 | 枚举和后端硬过滤，不允许运行时任意改写 |

### 8.3 最小 API 契约 v0

Phase 01 只冻结跨团队边界；Phase 03 用 FastAPI OpenAPI 生成正式契约。

| API | 用途 | 最小要求 |
|---|---|---|
| `GET /healthz` | 部署健康检查 | 不访问模型；返回 API/DB 状态和版本 |
| `POST /v1/conversations` | 新建匿名会话 | 返回 conversation ID，不要求注册 |
| `POST /v1/chat/stream` | 动态 RAG 问答 | SSE；请求包含 conversation ID/message/profile patch |
| `GET /v1/conversations/{id}` | 恢复历史 | 权限检查，返回消息和引用 |
| `DELETE /v1/conversations/{id}` | 删除会话 | 幂等、权限检查 |
| `GET /v1/sources/{source}/{page}` | 引用定位 | 只访问 manifest 白名单来源 |

`chat/stream` 的最终事件至少包含：

```json
{
  "request_id": "uuid",
  "answer": "string",
  "route": "nutrition|platform|mixed|out_of_scope",
  "citations": [
    {
      "source": "A|B|C",
      "title": "string",
      "section": "string",
      "page": 1,
      "chunk_id": "string",
      "excerpt": "string"
    }
  ],
  "safety": {
    "risk_level": "S0|S1|S2|S3",
    "matched_rules": [],
    "required_notice": "general|professional|emergency"
  },
  "model": {"provider": "string", "name": "string"}
}
```

错误契约统一包含 `request_id`、稳定错误码、用户可读消息和 `retryable`，不得把堆栈或 provider 原始错误返回前端。

## 9. 步骤四：工具链与环境冻结（01:25–01:40）

### 操作

1. 记录 Git、Node、包管理器、Python、Python 包管理器和 Docker 的实际版本；
2. Web 只选一个包管理器并提交唯一 lockfile；API 同理；
3. 选择 Next.js 支持的 Node LTS，写入 `.nvmrc`；Python 版本写入 `.python-version`；
4. 在根目录创建 `.gitattributes`，统一源码和 migration 的 LF；历史 migration 发布后只增不改；
5. 对 Windows 开发与 Linux/容器部署执行同一套 lint/test/build 命令；
6. 复核 `.gitignore` 和 `.env.example`，真实 `.env` 不提交。

### 版本采集命令

```powershell
git --version
node --version
npm --version
python --version
docker version
git check-ignore .env
```

版本不可用时只记录事实并选择团队已有的稳定安装路径。本阶段不得为了追最新版本而升级全局工具；任何安装行为单独评估时间与影响。

### 行尾与迁移规则

建议的 `.gitattributes` 基线：

```gitattributes
* text=auto eol=lf
*.ps1 text eol=crlf
*.pdf binary
*.docx binary
```

数据库 migration 一经进入 release 即不可改原文件；需要变更只新增 migration。CI 后续校验历史 migration hash，避免 Windows/WSL/Linux 行尾差异在最后部署时才暴露。

## 10. 步骤五：外部资源就绪检查（01:40–01:50）

| 资源 | 主路径要确认 | 备用路径 | 证据 |
|---|---|---|---|
| LLM | Base URL、model、配额、流式、超时 | 第二兼容 provider 或 Mock 用于开发 | 脱敏 smoke 结果 |
| Embedding | model、dimensions、中文表现、配额 | 关键词/字符检索暂代，不能取消引用 | 脱敏 smoke 结果 |
| PostgreSQL | 本地 Compose 可创建 extension | 托管 PostgreSQL/反向备用 | 连接与 extension 记录 |
| 公网部署 | 账号、区域、HTTPS、环境变量 | 第二平台或本地演示 | 项目/服务名，不记 Secret |
| 域名/URL | 默认平台 HTTPS URL | 平台备用 URL | 可访问性 owner 与截止点 |

检查只验证最小连通性，不做长时间模型选型。日志中只记录状态码、延迟、模型名和 request ID，禁止记录 Authorization header。

决策时限：主资源在 10 分钟内不能通过最小 smoke，就立即启用备用路径并登记 `owner + 最晚恢复时间`，不得吞掉 Phase 02 时间。

## 11. 风险、触发器与降级

| 风险 | 触发条件 | 当场动作 | 不允许的做法 |
|---|---|---|---|
| 范围膨胀 | P0 尚未分配却提出新增功能 | 放入 P2 backlog，T+30 再评估 | “顺手做一下” |
| Provider 不可用 | 连通/配额 smoke 失败 | 切备用或 Mock，保留 adapter 契约 | 把答案硬编码成模型输出 |
| Embedding 未就绪 | 维度/接口未知 | Phase 02 先结构化事实和关键词索引 | 猜测维度创建生产索引 |
| Docker 不可用 | `docker version` 失败 | 记录 owner；本机 native 开发，T+12 前恢复 Compose | 删除本地一键运行要求 |
| 部署账号缺失 | 无项目/权限/Secret 管理 | 指派 DevOps 在 T+12 前完成，保留第二平台 | 等到 T+36 才首次部署 |
| 资料 hash 不符 | 任一原件不匹配 | 停止导入，确认正确版本 | 修改 manifest 迎合错误文件 |
| Windows/Linux 漂移 | 行尾或构建版本不一致 | 锁 `.gitattributes`、lockfile 和容器构建 | 修改已发布 migration checksum |
| 真实密钥入库 | status/diff 出现 Key | 立即移除并轮换泄露 Key，记录事件 | 只删除 Git 当前文件但不轮换 |

## 12. Phase 02 的 Ready 定义

进入下一阶段前，以下任务必须已经建卡：

| 任务 ID | 任务 | 输入 | 输出 | 验收 |
|---|---|---|---|---|
| DATA-01 | PDF 页级解析 | A/B/C 原件 + manifest | page JSON | 页数与原件一致 |
| DATA-02 | 章节与 chunk | page JSON + schema | chunk JSONL | source_role/page 完整 |
| DATA-03 | 结构化事实 | A/B 表格/方案 | FoodFact/PlanRule | 关键数字人工复核 |
| DATA-04 | 平台事实 | C 文档 | PlatformFact | 禁止营养用途 |
| DATA-05 | 数据库 schema/migration | 数据契约 | migration | 空库可重复执行 |
| DATA-06 | 导入与隔离 smoke | 全部上项 | 检索记录 | A/B/C 硬过滤通过 |

每张卡必须有 owner、预计时长、依赖、目标文件、测试 ID 和证据路径；只写“处理知识库”不算 Ready。

## 13. 退出门禁与记录模板

在 `docs/evidence/phase-01-baseline-record.md` 写入实际结果：

```markdown
# Phase 01 Baseline Record

- Start / End:
- Participants and roles:
- Repo / Branch / Commit:
- Host / toolchain versions:

| Gate | Result | Evidence | Owner |
|---|---|---|---|
| G1 四份来源 hash 一致 | PASS/FAIL | command output/path | |
| G2 A/B/C source_role 冻结 | PASS/FAIL | manifest | |
| G3 所有 P0 有 owner/test/evidence | PASS/FAIL | traceability matrix | |
| G4 P1/P2 和非目标冻结 | PASS/FAIL | scope record | |
| G5 技术主栈和最小契约冻结 | PASS/FAIL | ADR/phase plan | |
| G6 工具链、lockfile、行尾规则确定 | PASS/FAIL | versions/files | |
| G7 Secret 管理与 .env ignore 通过 | PASS/FAIL | scan/check-ignore | |
| G8 主/备 provider 与部署路径明确 | PASS/FAIL | redacted smoke | |
| G9 Phase 02 任务全部 READY | PASS/FAIL | task IDs | |

Decision: PASS / BLOCKED
Blockers and deadline:
Lead sign-off:
```

### 判定规则

- `PASS`：G1～G9 全部通过，立即进入 Phase 02；
- `BLOCKED`：G1/G2/G3/G5/G7 任一失败，不得开始知识生产；
- `PASS WITH ACTION` 仅允许用于外部资源暂不可用，且已启用不改变核心契约的备用路径、明确 owner 和不晚于 T+12 的截止时间；
- 不允许使用“基本完成”“应该可以”等模糊状态。

## 14. 单人模式压缩执行

单人仍保留全部门禁，只压缩会议动作：

1. 15 分钟核验资料和仓库；
2. 30 分钟冻结 P0/P1/P2；
3. 25 分钟冻结契约与变化轴心；
4. 20 分钟记录工具链、行尾和 Secret；
5. 15 分钟验证外部资源；
6. 10 分钟建立 Phase 02 任务卡；
7. 5 分钟签署退出记录。

若两小时仍无法完成，优先删减 P2，而不是跳过来源、安全、Secret 或部署基线。

## 15. 本阶段对得分的直接贡献

- 用追踪矩阵防止漏掉基础评分项；
- 用 A/B/C 角色冻结和 hash 提供知识隔离证据；
- 用最小 API/错误契约减少前后端返工，保证 12 小时端到端闭环；
- 用 provider 和部署双路径降低现场不可用风险；
- 用行尾、lockfile、migration 不可变和 Secret 规则提升可复现与工程质量；
- 用明确退出门禁，让后续报告中的“完成”都有可验证证据。

