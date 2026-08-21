# Phase 02 READY 任务板：知识数据生产化处理

- 时间窗口：T+2～T+6
- 前置门禁：Phase 01 `PASS` 或 `PASS WITH ACTION`
- 本文是 Phase 01 的退出产物，不替代后续 Phase 02 详细实施手册。

| Task | Owner | 预计 | 依赖 | 目标文件 | 验收/证据 | 状态 |
|---|---|---:|---|---|---|---|
| DATA-01 页级解析 | KNOWLEDGE | 30m | manifest/hash PASS | `knowledge/normalized/pages/*.jsonl` | A=5、B=8、C=5 页；标题/页码抽检 | PASS |
| DATA-02 章节与 Chunk | KNOWLEDGE + API | 35m | DATA-01 | `knowledge/normalized/chunks/*.jsonl` | 每条有 source/version/role/page/section/chunk_id | PASS（67 chunks） |
| DATA-03 A/B 结构化事实 | KNOWLEDGE | 70m | DATA-01 | `food_facts.jsonl`、`plan_rules.jsonl` | 数字、单位、禁忌和方案边界逐条人工核对 | PASS WITH ACTION-06（68 条待第二人复核） |
| DATA-04 C 平台事实 | KNOWLEDGE | 20m | DATA-01 | `platform_facts.jsonl` | role 仅为 auxiliary；forbidden uses 完整 | PASS WITH ACTION-06（12 条待第二人复核） |
| DATA-05 Schema/Migration | API | 45m | DATA-02～04 | `knowledge/schemas/*`、`infra/migrations/*` | Schema 校验；空库迁移命令已定义 | PASS（静态）；运行态 ACTION-01 |
| DATA-06 导入与隔离 smoke | API + QA_DOCS | 30m | DATA-05；数据库可用则执行 | `scripts/ingest*`、`docs/evidence/phase-02-*` | A/B 营养可查、C 平台可查、C 不进推荐 | PASS（文件级）；DB/向量 ACTION-01/03 |

预留 10 分钟处理解析异常和签署 Phase 02 门禁。任务只允许写归一化产物，不得覆盖 `knowledge/raw/`。

Phase 02 执行结论为 `PASS WITH ACTION`，详见[阶段验收记录](../evidence/phase-02-baseline-record.md)和[第二人复核清单](../evidence/phase-02-second-person-review-checklist.md)。

## 依赖顺序

```text
DATA-01 → DATA-02 ─┬→ DATA-05 → DATA-06
        ├→ DATA-03 ┤
        └→ DATA-04 ┘
```

多人模式可在 DATA-01 后并行执行 DATA-02、DATA-03、DATA-04；单人严格按表格顺序执行。

## 阻塞规则

- LLM 不可用不阻塞 DATA-01～05；
- Embedding 维度未确认时不得创建生产向量列/索引，可先保留 schema 参数；
- Docker/PostgreSQL 不可用时 DATA-05 产出 migration 并做静态校验，DATA-06 执行文件级隔离 smoke，运行态验收转 ACTION-01；
- 任何关键数字无法从原 PDF 人工确认时标记 `REVIEW_REQUIRED`，禁止猜测填入。
