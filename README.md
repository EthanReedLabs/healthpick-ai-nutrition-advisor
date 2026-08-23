# HealthPick AI Smart Nutrition Advisor

第二届 OPC 软件与智能体开发赛道参赛项目。HealthPick 不是普通聊天壳，而是一套可审计的健康领域 RAG 产品：Next.js Web、FastAPI API、PostgreSQL、真实 LLM Provider、A/B/C 知识硬隔离、逐条引用、医疗安全门、多轮历史、账号数据权利、自动评测和 Docker Compose 复现均已落地。

## 公网访问与当前状态

公开演示入口：**<https://106.14.13.139>**。浏览器直接访问即可，不需要安装软件。当前生产环境部署在阿里云 ECS，使用受信 HTTPS 公网 IP 证书；Web、API 和 PostgreSQL 均有健康检查及 `unless-stopped` 重启策略，Caddy 数据卷持久化并自动续期证书。生产回答由阿里云百炼北京地域 Token Plan 的 `qwen3.7-plus` 动态生成，页面会如实展示模型来源；检索为可审计的 `keyword` 模式，Embedding 当前明确为 `disabled`。

Phase 01～08 的工程与发布验收已完成，`ACTION-05`、`ACTION-06` 等遗留动作已关闭：80 条结构化事实最终处置为 74 条通过、6 条含缺字符号规则驳回、0 条待复核；推荐引擎只使用其中 7 条已复核核心规则。本轮补充赛题说明收口由 [Phase 09 执行计划](docs/phases/phase-09-rubric-closure.md) 和 `control/records/RC10-CONTROL.yaml` 单独追踪，不改写此前验收记录。

## 如何使用

1. 打开公网入口，首页会显示欢迎语、三个快捷问题、健康档案入口、对话区和来源透明度。
2. 直接输入“我想减重”“我在健身”或“我血糖有点高”，系统会识别减脂、增肌或稳糖倾向，只从资料 A/B 检索匹配依据并给出带文档、章节、页码和 Chunk ID 的回答。
3. 需要规则方案时点击“编辑健康档案”，选择目标、年龄段、活动水平、过敏原和安全标签。45–64 岁用户需填写精确年龄；45 岁在资料适用范围内可生成方案，年龄冲突、资料范围外或高风险条件会被安全阻断。
4. 询问会员、企业合作或 API 服务时，系统只使用资料 C；平台资料不会进入营养推荐。登录或注册后可跨设备保存、搜索、改名和删除对话，也可导出或永久删除账号数据。
5. 输入为空、超过 2000 字或系统异常时会显示明确提示；生成期间可主动停止。模型超时可使用同一请求编号重试，不会保存半成品。

疾病、用药、孕哺、严重过敏或其他高风险问题只提供一般信息并触发专业提示。**本建议仅供参考，不构成医疗建议，请咨询专业医师或注册营养师。** 胸痛、呼吸困难、意识异常等紧急情况应立即联系当地急救或前往急诊。

## 技术选型与核心逻辑

前端采用 Next.js、React 和 TypeScript，以响应式页面承载问答、档案、方案卡、引用、历史和透明度；后端采用 FastAPI、Pydantic 与 Python，把输入校验、权限、意图路由、安全分级、检索、真实模型调用、证据校验和持久化组织成单一路径。PostgreSQL 保存匿名/账号会话与对话历史，健康档案只随请求临时使用。知识资料在离线阶段按页解析为带来源角色、章节、页码和哈希的 Chunk，并生成经过复核的结构化方案规则；运行时先由确定性路由决定允许来源，再在允许分区内执行关键词评分和受控别名提示，不能让模型自行决定是否忽略资料 C。模型只接收本轮允许的证据，回答必须逐条带合法 Chunk 引用；引用或医疗安全后校验失败时会修复一次，仍失败则使用可验证的证据回退或拒答。该设计选择可解释的关键词检索而非未启用的向量检索，适合三份小规模、数字和禁忌敏感的赛题资料，也便于证明来源隔离和零编造边界。

## 核心能力

- 营养与方案问题只检索资料 A/B；会员、企业服务和 API 问题只检索资料 C；混合问题拆分后分别检索。
- 回答展示文档、章节、页码、原文摘录和 Chunk ID；无证据时 fail closed。
- S0～S3 确定性风险分级覆盖过敏、糖尿病、肾病、痛风、高血压、孕哺、药物调整、进食障碍和紧急症状。
- PostgreSQL 保存匿名/账号会话和对话；支持搜索、改名、删除、账号导出和永久删除。
- 用户可主动停止生成；客户端与服务端使用同一 request ID 取消，半成品不落库。
- 公开透明页展示实际模型、Embedding、检索、存储、知识边界、故障切换策略及脱敏评测摘要。

## 15 分钟本地运行

前置条件：Docker Desktop、Docker Compose，以及宿主机可访问的 OpenAI-compatible 模型服务。仓库默认 Compose 复现配置指向宿主 Ollama；这只是本地替代方案，不代表公网生产模型：

```powershell
ollama pull qwen2.5:3b-instruct
Copy-Item .env.example .env
docker compose up -d --build
```

macOS/Linux 将第二行改为 `cp .env.example .env`。默认入口：

- Web：<http://127.0.0.1:3000>
- API 健康：<http://127.0.0.1:8010/healthz>
- OpenAPI：<http://127.0.0.1:8010/openapi.json>

`.env.example` 只有占位值。使用远程 Provider 时，必须在本机 `.env` 或部署平台 Secret 中设置真实值；`.env` 已被 Git 忽略。生产环境禁止 `LLM_MODE=mock`，并强制 PostgreSQL 会话存储。

如需复现公网同类配置，可把 `COMPOSE_LLM_BASE_URL`、`COMPOSE_LLM_MODEL` 和 `COMPOSE_LLM_API_KEY` 改为自己的百炼 OpenAI-compatible 端点、`qwen3.7-plus` 和 Secret；真实密钥不得提交。`EMBEDDING_MODE=disabled` 与 `RETRIEVAL_MODE=keyword` 是当前已验证组合。

停止服务：

```powershell
docker compose down
```

如需删除本地数据库卷，需由操作者明确执行 `docker compose down --volumes`；该动作会删除本地数据，不属于普通停止流程。

## 开发与质量门

Python：

```powershell
uv sync --frozen
.\.venv\Scripts\pytest.exe
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\python.exe -B scripts\control_plane.py
```

Web：

```powershell
cd apps\web
npm ci
npm test
npm run typecheck
npm run lint
npm run build
```

提交候选密钥扫描：

```powershell
.\.venv\Scripts\python.exe -B scripts\audit_repository_security.py
```

最终发布使用 `scripts/control_plane.py --check-final`；任何必做任务、行动、阻断问题、未复核记录或 Release 字段缺失都会返回非零退出码。

## 资料与许可证边界

- A《2026秋季健康膳食指南》：营养事实、风险与禁忌依据。
- B《2026秋季个性化饮食方案》：食谱、方案目标和同类替换依据。
- C《HealthPick平台服务白皮书》：平台功能、会员、合作和服务规则，不得用于营养或医疗结论。

本团队原创代码和原创文档按 [MIT License](LICENSE) 提供。赛题题面、资料 A/B/C、商标、截图中的第三方内容及依赖不因本许可证获得再许可，详见 [第三方与来源声明](THIRD_PARTY_NOTICES.md)。

## 隐私、安全与 AI 披露

- [面向用户的隐私说明](PRIVACY.md)
- [安全边界与漏洞报告](SECURITY.md)
- [医疗安全与隐私设计](docs/04-safety-privacy.md)
- [AI 辅助开发使用披露](docs/AI_USAGE.md)
- [机器可读数据路径](docs/release-data-map.json)

健康档案当前为请求内临时数据，不写入 PostgreSQL；对话会持久化。注册账号只保存规范化邮箱、密码哈希和令牌哈希。Web 当前把 bearer token 存在浏览器 `localStorage`，其风险和删除路径已在隐私/安全文档中明确披露。

## 文档导航

1. [主执行方案](docs/00-master-execution-plan.md)
2. [需求追踪矩阵](docs/01-requirements-traceability.md)
3. [系统架构](docs/02-architecture.md)
4. [知识库与 RAG](docs/03-rag-and-knowledge.md)
5. [医疗安全与隐私](docs/04-safety-privacy.md)
6. [评测与冲分策略](docs/05-evaluation-and-winning.md)
7. [48 小时排期](docs/06-48h-schedule.md)
8. [演示与提交清单](docs/07-demo-and-submission.md)
9. [AI 使用披露](docs/AI_USAGE.md)
10. [系统架构决策](docs/decisions/ADR-001-technology-stack.md)
11. [控制面规则](docs/governance/README.md)
12. [问题与解决日志](docs/governance/ISSUE_LOG.md)
13. [最终总纲验收](docs/governance/FINAL_ACCEPTANCE_MASTER.md)
14. [基础功能测试记录](docs/08-basic-test-records.md)
15. [公网七天可用性承诺](docs/evidence/phase-09-rc10-05-availability.md)
16. [赛题正式交付文档（Word）](docs/deliverables/README.md)
17. [公开仓库安全与漏洞报告](SECURITY.md)

## 公开仓库与密钥

本仓库不提交真实 API Key、数据库密码、私钥、访问令牌或部署凭据。`.env.example` 与 `infra/ecs.env.example` 仅提供变量名和占位符；真实值必须放在 Git 已忽略的本地环境文件或服务器环境中。CI 会同时扫描当前提交候选和全部可达 Git 历史，报告只包含位置与规则名，不回显候选值。

## 医疗边界

HealthPick 只提供资料范围内的一般膳食信息与计划辅助，不进行诊断，不替代医生或注册营养师，不建议停药、换药或调整治疗。胸痛、呼吸困难、严重过敏、意识丧失等紧急信号会中止普通生成并引导立即联系当地急救或线下医疗机构。
