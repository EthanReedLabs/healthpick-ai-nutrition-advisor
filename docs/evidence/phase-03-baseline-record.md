# Phase 03 最薄动态问答闭环退出记录

- Start：2026-08-21 18:29:35+08:00
- Phase completion：2026-08-21 19:44:00+08:00
- Repository：`D:/OPC_competition/healthpick-ai-nutrition-advisor`
- Execution mode：单人、代码优先、统一控制面
- Decision：`PASS WITH ACTION`

## 1. 交付摘要

| Artifact | Result | Evidence |
|---|---:|---|
| FastAPI/OpenAPI/稳定错误 | PASS | P03-01 record、OpenAPI JSON |
| LLM Provider Real/Mock 适配 | PASS | P03-02 record、8 项专项测试 |
| 67-Chunk A/B/C 路由检索 | PASS WITH ACTION | P03-03 record、实际检索 smoke |
| 引用生成与 fail-closed 校验 | PASS WITH ACTION | P03-04 record、篡改拒绝 smoke |
| 临时会话与 SSE Chat API | PASS WITH ACTION | P03-05 record、Uvicorn smoke |
| Next.js 三档工作台 | PASS | P03-06 record、3 张视口图 |
| 浏览器动态闭环 | PASS WITH ACTION | P03-07 record、营养与平台截图 |
| API 自动测试 | 50/50 PASS | `phase-03-api-pytest.xml` |
| Web 组件测试 | 4/4 PASS | `phase-03-web-vitest.xml` |
| Python/Web 静态与构建 | PASS | Ruff、ESLint、TypeScript、Next Build |
| Web 高危依赖审计 | 0 vulnerabilities | `npm audit --audit-level=high` |

## 2. 闭环与隔离结果

- 健康接口公开环境、LLM/Embedding/检索模式，不读取外部依赖；
- Mock 回答固定包含 `[MOCK RESPONSE — NOT REAL MODEL OUTPUT]`，UI 同时显示 `API 在线 · Mock` 和 `mock`；
- Real 缺少 base URL/key/model 时，在发送 SSE 头之前以稳定 JSON 503 fail-closed；
- nutrition/recommendation/contraindication 仅允许 A/B，platform 仅允许 C，mixed 同时保留核心与平台证据；
- 每条引用均回指真实 Chunk、source/title/page/section，excerpt 必须是原文连续子串；
- SSE 顺序为 meta → citation → token → final；模型无合法内联 Chunk 引用时以 502 阻止；
- Web 浏览器实测营养问题返回 A/B，平台问题返回 C-only，Chat POST=200，控制台无异常；
- 会话为进程内有界 ephemeral，未宣称已经持久化；
- 当前检索明确为 keyword，`embedding_claimed=false`。

## 3. 退出门禁

| Gate | Result | Evidence/限制 |
|---|---|---|
| G1 API/OpenAPI/统一错误 | PASS | 50 项 API 回归、Uvicorn health/OpenAPI smoke |
| G2 Provider 模式透明 | PASS | Mock runtime 与 Real 协议测试；production 禁止 Mock |
| G3 A/B/C 硬隔离 | PASS WITH ACTION | keyword 闭环通过；vector 待 ACTION-03 |
| G4 引用不可伪造 | PASS WITH ACTION | 正常/篡改双向 smoke；原文放行待 ACTION-06 |
| G5 SSE 与会话 | PASS | 事件顺序、错误前置、ephemeral 容量均测试 |
| G6 三档响应式 | PASS | 1440×1000、1024×900、390×844；手机无横向溢出 |
| G7 浏览器动态闭环 | PASS WITH ACTION | Mock 两类闭环通过；Real 调用待 ACTION-02 |
| G8 未运行项透明 | PASS | Real/vector/review 均在状态、记录和最终门禁中显式保留 |

## 4. 过程问题与修复

- 依赖链：Starlette 迁移到 httpx2；ESLint 10 与 Next 插件 peer 不兼容，精确固定 9.39.5；
- 测试装配：补 AnyIO 异步 backend、显式 DOM cleanup、ESM package 声明；
- 运行环境：避开本机 3000/8000 冲突，统一使用 `127.0.0.1:3000/8010`；
- 工具环境：Windows 沙箱和内置浏览器宿主问题均用可审计降级路径完成验证；
- UI 查错：纠正 A/B/C 角色文案，并修复来源徽章 CSS 污染引用卡背景；
- 状态文档：退出查漏时修正 README 仍宣称应用代码未开始的陈旧描述；
- 所有问题均写入 ISSUE-009、012～022，开放项不冒充已修复。

## 5. 未决行动

| ID | Owner | Completion evidence |
|---|---|---|
| ACTION-02 真实 LLM provider/model/quota smoke | API/Lead | 脱敏真实请求、模型名、时延、成功 final 事件与浏览器截图 |
| ACTION-03 Embedding model/dimensions/中文 smoke | API/Lead | 模型 manifest、维度、向量 migration、召回评测 |
| ACTION-06 原始事实与缺字二人复核 | KNOWLEDGE/Lead | checklist reviewer/date/notes 完整，全套校验通过 |

ACTION-02/03/06 未关闭前，P03-03/04/05/07/08 与 Phase 03 保持 `PASS WITH ACTION`；不得把 Mock、keyword 或 review_required 数据作为最终生产证据。

## 6. Decision

`PASS WITH ACTION`

Phase 04 可进入健康档案、推荐和医疗安全规则实现；Phase 03 的开发态可执行闭环已经完整，但最终竞赛放行仍受上述三项客观证据约束。

- Lead sign-off：待最终总纲验收统一复核
- Execution record prepared by：Codex
