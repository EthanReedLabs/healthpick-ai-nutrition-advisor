# Phase 02 Knowledge Ingestion Record

- Start：2026-08-21 16:58:24+08:00
- Phase completion：2026-08-21 17:24:17+08:00
- Repository：`D:/OPC_competition/healthpick-ai-nutrition-advisor`
- Execution mode：单人、代码优先、文件级降级路径
- Parser：PyMuPDF 1.28.2 native text（由 `uv.lock` 固定）
- Decision：`PASS WITH ACTION`

## 1. 交付摘要

| Artifact | Result | Evidence |
|---|---:|---|
| 页级记录 | 18（A=5、B=8、C=5） | `knowledge/normalized/pages/*.pages.jsonl` |
| 页内 Chunk | 67（A=21、B=26、C=20） | `knowledge/normalized/chunks/*.chunks.jsonl` |
| 食材事实 | 31 | `food_facts.jsonl` |
| 营养/方案规则 | 37 | `plan_rules.jsonl` |
| 平台事实 | 12 | `platform_facts.jsonl` |
| JSON Schema | 5 | `knowledge/schemas/` |
| PostgreSQL migration | 1，7 张知识表 | `infra/migrations/001_knowledge_base.sql` |
| 页面视觉证据 | 18 PNG | `docs/evidence/phase-02-page-review/` |
| 自动测试 | 11/11 PASS | `docs/evidence/phase-02-pytest.xml` |
| 文件/隔离校验 | PASS，errors=0 | `phase-02-knowledge-validation.md` |

## 2. 可复现数据指纹

| Output | SHA-256 |
|---|---|
| A pages | `4D46435EE01032B7F1346AF26776B3B6DE001E11A9113951D4213DBC4E357F77` |
| B pages | `D345C00159C736EC3DF74D6269879E5D526393FAAD421C70C7CE9CE3311CF7B5` |
| C pages | `7CF1F08DF530EA07CFB5A474F76EFF78005047A7F256064DD21D400A704A552C` |
| A chunks | `11F88F08D43E617E0B2EA8B7FDD67177373362011A5C529B700CF0C77BDB0C3D` |
| B chunks | `22D04ED08DACDF7912151DDA9C557054677D7783E16498943FE9A7B325297E7A` |
| C chunks | `C6E4FABFD336A59F31C87CC7E0745B3E76099FC8E4E535132EA992681A9FD2BE` |
| Food facts | `9ACC97D26AC0AF46F50BD9C4974283360D894026ABBBA4BD9AB2DBF87DF1292C` |
| Plan rules | `F43F52BC9FBA3EABDBC3C7B8B0EE3135444055B4A38C435EFA64EE56FAF38ADC` |
| Platform facts | `6BC43EF84DA82FD3F6D63AAA814E19C41C4562ACD06A97ED242BBA7B99F25C48` |

## 3. 质量与隔离结果

- 原始 PDF hash 与 Phase 01 manifest 一致，`knowledge/raw/` 未改写；
- 所有页有 raw/normalized text、block bbox、source version/hash 和页码；
- 所有 Chunk 均在单页内，ID 唯一且能回指页记录；
- C 的 20 个 Chunk 和 12 条事实仅允许 platform 路由，营养、推荐、禁忌用途全部禁止；
- A/B 数据没有 platform 路由，C 串入营养事实/方案规则的记录数为 0；
- migration 未猜测 Embedding 维度，向量列留待模型 manifest 确认后新增；
- 80 条结构化记录均有第一轮页面视觉证据，且保持 `review_required` 等待参赛者第二人复核。

## 4. 原始资料缺陷

视觉渲染和原生文本提取共同确认：A-p02、A-p04、B-p01、B-p05、B-p07、B-p08 共 6 页存在源文件缺字，影响 8 个 Chunk。受影响的比较符或符号没有被推断补写；对应规则保持 `unknown_glyph: true` 和 `review_required`。

详细位置与处理流程见 `phase-02-second-person-review-checklist.md`。

## 5. 退出门禁

| Gate | Result | Evidence/限制 |
|---|---|---|
| G1 18 页可回溯 | PASS | 页数、hash、非空文本和 18 张页面图均通过 |
| G2 Chunk 稳定且不跨页 | PASS | 67 个唯一 ID，page/source 引用校验通过 |
| G3 A/B 事实页级核对 | PASS WITH ACTION | Codex 第一轮视觉对照完成；参赛者第二人复核为 ACTION-06 |
| G4 C 严格 auxiliary | PASS | 允许营养用途 0，文件级隔离 smoke 通过 |
| G5 Schema/migration | PASS WITH ACTION | JSON Schema 和 SQL 静态通过；数据库运行态转 ACTION-01 |
| G6 文件级 smoke | PASS | validation errors=0，pytest 11/11 |
| G7 未运行项透明 | PASS | DB=`NOT_RUN`，Embedding=`NOT_RUN`，第二复核=`REQUIRED` |
| G8 Phase 03 输入明确 | PASS | 开发可使用 review-aware 数据；生产数值导入受 ACTION-06 阻断 |

## 6. 未决行动

| ID | Owner | Deadline | Completion evidence |
|---|---|---|---|
| ACTION-01 Docker/PostgreSQL/pgvector 运行态迁移与 smoke | DEVOPS/Lead | T+12 | Compose health、migration、隔离查询结果 |
| ACTION-03 Embedding model/dimensions/中文 smoke | API/Lead | T+6 | 模型名、维度、脱敏请求结果，新增向量 migration |
| ACTION-06 80 条事实第二人逐条复核 | KNOWLEDGE/Lead | T+12 | checklist 签署；verified 均有 reviewer/date/notes；全套校验通过 |
| ACTION-07 6 页源文件缺字处理 | Lead | T+18 | 修正版 PDF/赛题方书面确认及新 version/hash；否则永久排除受影响规则 |

ACTION-01/03 继承 Phase 01；ACTION-06/07 为 Phase 02 新增。生产导入和对外数值回答不得绕过 ACTION-06，缺字规则不得仅凭经验放行。

## 7. Decision

`PASS WITH ACTION`

Phase 03 可开始实现 API、检索路由、引用与 review-aware 安全门；开发态只能使用 `review_required` 数据做可追溯验证，不得把它作为已核准的生产营养结论。数据库/向量运行态和最终事实放行分别受 ACTION-01/03/06 约束。

- Lead sign-off：待参赛者完成 ACTION-06 后签署最终数据放行
- Execution record prepared by：Codex
