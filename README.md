# HealthPick AI Smart Nutrition Advisor

第二届 OPC 软件与智能体开发赛道参赛项目的规划与实施仓库。

本项目采用代码优先路线：Next.js Web 前端、FastAPI 后端、PostgreSQL + pgvector 数据层，以及可替换的 LLM/Embedding Provider。目标不是只完成一个聊天演示，而是交付一个可部署、可追溯、可测试、具备安全边界和多轮记忆的 AI 智能膳食顾问。

## 当前阶段

当前仓库已完成：

- 赛题与三份资料归档；
- A/B 核心营养知识与 C 辅助平台资料的边界分析；
- 高分功能范围、技术架构、RAG、安全、评测、部署与 48 小时执行计划；
- 需求到功能、测试和提交证据的追踪设计；
- FastAPI/OpenAPI、Provider、A/B/C 检索、引用校验、SSE Chat API 与 Next.js 工作台的开发态动态闭环。

当前 Phase 04 已 READY，将继续实现健康档案、确定性推荐、禁忌硬过滤与医疗安全。后续仍以需求追踪矩阵和统一控制面为唯一范围/状态基线。

Phase 01 已于 2026-08-21 完成，退出结论为 `PASS WITH ACTION`。资料、范围、Owner、技术与环境基线均已冻结；Docker、真实 LLM/Embedding 配置、远端仓库和 Render 账号仍有 T+6/T+12 限时行动，详见[阶段验收记录](docs/evidence/phase-01-baseline-record.md)。

Phase 02 已完成文件级知识生产链路，退出结论为 `PASS WITH ACTION`：18 页、67 个 Chunk、80 条结构化事实、5 个 Schema、1 个 migration，文件与隔离校验通过，自动测试 11/11。80 条事实仍需参赛者第二人复核，6 个原始页面存在缺字符号；数据库与向量运行态尚未执行。详见[Phase 02 验收记录](docs/evidence/phase-02-baseline-record.md)与[第二人复核清单](docs/evidence/phase-02-second-person-review-checklist.md)。

Phase 03 已完成开发态最薄动态问答闭环，退出结论为 `PASS WITH ACTION`：API 50/50、Web 4/4，Ruff/ESLint/TypeScript/Next Build 均通过；浏览器实测营养问题只用 A/B、平台问题只用 C，引用可回查页码与章节。真实 LLM、向量模型和原文二人复核仍分别受 ACTION-02/03/06 阻断，详见[Phase 03 验收记录](docs/evidence/phase-03-baseline-record.md)。

项目统一控制面已启用，覆盖 Phase 01～08 的 55 个任务、行动项、问题日志、逐任务完成记录和 10 个最终验收门。当前结构审计为 `PASS`，最终就绪度为 `NOT_READY`；控制面会把所有未完成任务显式列为阻断，直至最终总纲验收。入口见[统一控制板](docs/governance/CONTROL_BOARD.md)。

## 文档导航

1. [主执行方案](docs/00-master-execution-plan.md)
2. [需求追踪矩阵](docs/01-requirements-traceability.md)
3. [系统架构](docs/02-architecture.md)
4. [知识库与 RAG](docs/03-rag-and-knowledge.md)
5. [医疗安全与隐私](docs/04-safety-privacy.md)
6. [评测与冲分策略](docs/05-evaluation-and-winning.md)
7. [48 小时排期](docs/06-48h-schedule.md)
8. [演示与提交清单](docs/07-demo-and-submission.md)
9. [AI 辅助使用披露](docs/AI_USAGE.md)
10. [已确认项目意图](docs/INTENT.md)
11. [技术选型决策](docs/decisions/ADR-001-technology-stack.md)
12. [开发与部署基线](docs/decisions/ADR-002-development-and-deployment-baseline.md)
13. [项目目录说明](PROJECT_STRUCTURE.md)
14. [统一控制面规则](docs/governance/README.md)
15. [实时统一控制板](docs/governance/CONTROL_BOARD.md)
16. [最终总纲验收](docs/governance/FINAL_ACCEPTANCE_MASTER.md)
17. [问题与解决日志](docs/governance/ISSUE_LOG.md)

## 分阶段执行手册

- [Phase 01：基线与范围冻结（T+0～2h）](docs/phases/phase-01-baseline-freeze.md)
- [Phase 02：知识数据生产化处理（T+2～6h）](docs/phases/phase-02-knowledge-ingestion.md)
- [Phase 02 READY 任务板](docs/phases/phase-02-ready-task-board.md)
- [Phase 02 验收记录](docs/evidence/phase-02-baseline-record.md)
- [Phase 02 第二人复核清单](docs/evidence/phase-02-second-person-review-checklist.md)
- [Phase 03：最薄动态问答闭环（T+6～12h）](docs/phases/phase-03-thin-slice.md)
- [Phase 03 验收记录](docs/evidence/phase-03-baseline-record.md)
- Phase 04～Phase 08 的详细手册按顺序编写，未完成前以 48 小时排期中的目标和退出条件为基线。

所有任务状态以 `control/project-control.yaml` 为唯一真值。每个任务关闭后必须新增独立完成记录并通过 `scripts/control_plane.py` 审计；阶段文档和 README 不得单独宣称完成。

## 资料边界

- 素材 A：营养基础、食材数据、特殊人群和禁忌；仅属于核心营养知识库。
- 素材 B：减脂、增肌、稳糖三套方案、食谱和替换规则；仅属于核心营养知识库。
- 素材 C：平台产品、价格、企业合作、API 和品牌资料；只回答平台类问题，不得作为营养推荐依据。

任何回答中的营养数字、方案结论、食材禁忌都必须来自 A/B 或确定性规则，且展示文档、章节和页码。C 中的会员价格、成功案例和平台能力不得进入膳食推荐上下文。

## 推荐实施顺序

1. 建立知识源清单、结构化事实表和隔离检索；
2. 完成动态 LLM 问答、引用校验和安全门；
3. 完成响应式聊天、健康档案与方案展示；
4. 完成历史持久化、用户系统和部署；
5. 使用黄金集、串库集、安全集和端到端测试生成提交证据；
6. 冻结功能，完成文档、演示视频和提交演练。

## 运行目标

最终交付必须同时支持：

- 公网 HTTPS 演示地址；
- Docker Compose 本地一键运行；
- `.env.example`，仓库中不包含真实密钥；
- 可重复执行的单元、接口、RAG 评测和浏览器端到端测试；
- 至少保留 7 天的演示可访问性。
