# HealthPick AI Smart Nutrition Advisor

第二届 OPC 软件与智能体开发赛道参赛项目。HealthPick 不是普通聊天壳，而是一套可审计的健康领域 RAG 产品：Next.js Web、FastAPI API、PostgreSQL、真实 LLM Provider、A/B/C 知识硬隔离、逐条引用、医疗安全门、多轮历史、账号数据权利、自动评测和 Docker Compose 复现均已落地。

## 发布候选状态

截至 2026-08-22，Phase 01～07 已退出，Phase 08 正在执行。当前客观基线：

- Python 全仓 254 项、Web 30 项测试通过，Ruff、TypeScript、ESLint、Next.js production build 通过；
- 真实 Ollama + PostgreSQL 执行 72 cases / 80 turns，路由 100%、来源泄漏 0、数字准确率 100%、引用支持率 95.5882%、高风险召回 100%、多轮保持 100%、未处理 5xx 为 0、首字 P95 2814ms；
- 独立 Compose 新卷完成 001～005 migration、seed、真实问答、PostgreSQL/API/Web 重启和会话持久化；
- 438 个已跟踪及未跟踪提交候选文件密钥扫描为 0；JavaScript 和 32 个 Python 生产依赖已知漏洞为 0；
- 公网 Render 地址仍等待 `ACTION-05` 的区域、预算和七天在线责任授权；80 条结构化事实第二人复核 `ACTION-06` 仍开放。因此最终状态必须保持 `NOT_READY`，不能把本地通过写成最终提交完成。

实时状态以 [统一控制板](docs/governance/CONTROL_BOARD.md) 和 `control/project-control.yaml` 为唯一真值。

## 核心能力

- 营养与方案问题只检索资料 A/B；会员、企业服务和 API 问题只检索资料 C；混合问题拆分后分别检索。
- 回答展示文档、章节、页码、原文摘录和 Chunk ID；无证据时 fail closed。
- S0～S3 确定性风险分级覆盖过敏、糖尿病、肾病、痛风、高血压、孕哺、药物调整、进食障碍和紧急症状。
- PostgreSQL 保存匿名/账号会话和对话；支持搜索、改名、删除、账号导出和永久删除。
- 用户可主动停止生成；客户端与服务端使用同一 request ID 取消，半成品不落库。
- 公开透明页展示实际模型、Embedding、检索、存储、知识边界、故障切换策略及脱敏评测摘要。

## 15 分钟本地运行

前置条件：Docker Desktop、Docker Compose，以及宿主机可访问的 OpenAI-compatible 模型服务。默认 Compose 指向宿主 Ollama：

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

## 医疗边界

HealthPick 只提供资料范围内的一般膳食信息与计划辅助，不进行诊断，不替代医生或注册营养师，不建议停药、换药或调整治疗。胸痛、呼吸困难、严重过敏、意识丧失等紧急信号会中止普通生成并引导立即联系当地急救或线下医疗机构。
