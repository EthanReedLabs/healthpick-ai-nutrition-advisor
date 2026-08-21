# Phase 01 P0 Owner 基线

- 冻结日期：2026-08-21
- 执行模式：暂按单人参赛模式；若后续确认多人，仅替换角色负责人，不改变需求范围和验收。
- 最终 Accountable：Project Lead（参赛者）

## 角色

| 角色 ID | 职责 |
|---|---|
| LEAD | 范围、技术裁决、发布门禁和最终提交 |
| KNOWLEDGE | 原始资料、结构化事实、manifest、引用与知识隔离 |
| API | FastAPI、RAG、Provider、推荐、安全、用户和会话后端 |
| WEB | Next.js、交互、响应式、历史和透明度页面 |
| QA_DOCS | 黄金集、自动测试、文档、证据和演示脚本 |
| DEVOPS | Git、CI、数据库、Secret、公网和 Compose 部署 |

单人模式下，Project Lead 同时承担上述六个角色；角色 ID 用来保持任务边界清晰。

## P0 Owner 映射

| 需求 ID | Responsible | Accountable | 测试/证据责任 |
|---|---|---|---|
| KB-01～KB-02 | KNOWLEDGE + API | LEAD | QA_DOCS |
| KB-03～KB-06 | KNOWLEDGE + API | LEAD | QA_DOCS，必须含数字、引用和串库报告 |
| MEM-01～MEM-03 | API + WEB | LEAD | QA_DOCS，多轮与 CRUD E2E |
| REC-01～REC-05 | API + KNOWLEDGE | LEAD | QA_DOCS，推荐及安全黄金集 |
| ENG-01～ENG-05 | WEB + API + DEVOPS | LEAD | QA_DOCS，三档视口和异常输入 |
| DOC-01～DOC-04 | QA_DOCS | LEAD | LEAD 复核字数、内容和真实报告 |
| LLM-01 | API | LEAD | QA_DOCS，动态调用 trace 与代码扫描 |
| DEP-02～DEP-03 | DEVOPS | LEAD | QA_DOCS，干净环境复现和 Secret scan |
| CON-01～CON-08 | LEAD + 对应角色 | LEAD | QA_DOCS，追踪矩阵和提交清单 |

## P1/P2 冻结

- P1 仅在 T+24 且 P0 验收通过后进入：响应式增强、账号、持久化历史、公网部署增强、透明 trace、数据导出/删除和主备模型。
- P2 仅在 T+30 且核心评测全绿后进入：评测概览页、下载式方案摘要等。
- 图片识别、智能硬件、支付、复杂知识图谱和自动联网营养搜索不进入本次 48 小时范围。

新增需求必须由 LEAD 记录：提出时间、需求 ID、替代的既有任务、P0 风险和接受/拒绝结论。

