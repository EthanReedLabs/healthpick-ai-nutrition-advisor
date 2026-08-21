# Phase 02 详细实施计划：知识数据生产化处理

> 执行状态：2026-08-21 已完成文件级链路，结论 `PASS WITH ACTION`。详见[阶段验收记录](../evidence/phase-02-baseline-record.md)和[第二人复核清单](../evidence/phase-02-second-person-review-checklist.md)。

## 1. 阶段定义

| 项目 | 内容 |
|---|---|
| 时间窗口 | T+2～T+6 |
| 目标 | 把 A/B/C 三份固定 PDF 转换为可追溯、可校验、可导入的数据资产 |
| 输入 | `knowledge/raw/*.pdf`、`sources.yaml`、Phase 01 基线 |
| 输出 | 页 JSONL、Chunk JSONL、FoodFact、PlanRule、PlatformFact、Schema、migration、验证报告 |
| 降级状态 | Docker/Embedding 未就绪时完成文件级全链路，不伪报数据库/向量运行通过 |
| 下一阶段 | Phase 03：FastAPI + RAG + Next.js 最薄闭环 |

## 2. 不可违反的原则

1. `knowledge/raw/` 是只读真值，不覆盖、不重写；
2. 生产解析使用原生 PDF 文本层，OCR 只允许辅助人工核对，不能成为事实真值；
3. 每条数据保留 source、version、source_role、page、section、source hash 和 review status；
4. A/B 与 C 在数据层就分角色，不能等到 Prompt 再隔离；
5. 数字、单位、禁忌和方案边界必须人工复核，解析器不能自动标记 verified；
6. 原生文本、标准化文本和结构化事实分层保存，避免无法回溯；
7. 未观测到数据库或向量结果时，只记录 `not_run`，不写成 PASS。

## 3. 四小时时间盒

| 时间 | Task | 产物 | 退出条件 |
|---:|---|---|---|
| 00:00–00:30 | DATA-01 页级解析 | `pages/A|B|C.pages.jsonl` | A=5、B=8、C=5，hash 一致 |
| 00:30–01:05 | DATA-02 Chunk | `chunks/*.chunks.jsonl` | 每条引用字段完整，无跨页合并 |
| 01:05–02:15 | DATA-03 A/B 事实 | `food_facts.jsonl`、`plan_rules.jsonl` | 关键数字/单位/禁忌人工核对 |
| 02:15–02:35 | DATA-04 C 事实 | `platform_facts.jsonl` | 全部 role=auxiliary_platform |
| 02:35–03:20 | DATA-05 Schema/Migration | JSON Schema、SQL migration | 静态校验通过；历史 migration 不修改 |
| 03:20–03:50 | DATA-06 文件级 smoke | validation JSON/Markdown | 来源、页码、ID、forbidden-use 全通过 |
| 03:50–04:00 | 门禁与证据 | Phase 02 record | 明确 PASS/PASS WITH ACTION/BLOCKED |

## 4. DATA-01 页级解析

### 实现

- 项目依赖：PyMuPDF，版本由 `uv.lock` 固定；
- `scripts/ingest_knowledge.py` 在写输出前验证文件 hash 和页数；
- 每页保存 `raw_text`、`normalized_text` 和文本 block 坐标；
- 只清除已知水印行与多余空白，不擅自重排表格或补字；
- 输出 UTF-8 JSONL，按 source code 和 page 升序，重复执行结果稳定。

### 页记录最小字段

```text
schema_version, source_code, source_title, source_version, source_role,
source_sha256, page, page_count, extractor, raw_text, normalized_text,
blocks, quality, review_status
```

### 验收

- 输出记录数严格等于 18；
- 所有页 `normalized_text` 非空，否则标记人工检查；
- manifest hash/页数不符时程序非零退出且不写半成品；
- 解析警告进入报告，不能静默吞掉。

## 5. DATA-02 Chunk

### 规则

- 按页内标题/段落切分，绝不跨页；
- 目标 200～600 中文字符，短列表可独立成块；
- ID 为稳定的 `SOURCE-pNN-cNN`；
- Chunk 保存原页文本范围、section、content、用途和 review status；
- C 的 Chunk 固定 `allowed_routes=[platform]`，禁止 nutrition/recommendation；
- 表格相关 Chunk 标记 `contains_table=true`，数值回答仍优先查结构化事实。

### 验收

- chunk_id 唯一且重复执行不漂移；
- 每个 Chunk 能回指唯一页记录；
- A/B/C 的 route/role 约束符合 manifest；
- 不把“免责声明”与前一页方案合并。

## 6. DATA-03/04 结构化事实

### FoodFact

用于 A 中食材营养表和明确食材属性。字段至少包含食材名、别名、份量/基准、营养素、数值、单位、适用/禁忌标签、source/page 和人工复核状态。

### PlanRule

用于 A/B 中餐盘比例、减脂/增肌/稳糖目标、食谱、替换规则和特殊人群边界。每条 rule 必须声明 `rule_type`、适用条件、排除条件、证据页和安全级别。

### PlatformFact

用于 C 中套餐、价格、平台能力、合作和 API 计划。固定 `source_role=auxiliary_platform` 和 `allowed_routes=[platform]`，并显式记录 `forbidden_routes=[nutrition,recommendation,contraindication]`。

### 人工复核门

- `verified`：已对照原 PDF 页面核对数字、单位、语义和上下文；
- `review_required`：解析可见但尚未完成人工确认；
- `rejected`：错位、水印或无法确认，不进入生产导入。

生产导入默认只接收 `verified`。每条复核记录包含 reviewer、日期和证据说明；本项目由 Codex 初录，最终参赛者仍需对医疗/营养数字做第二人复核。

## 7. DATA-05 Schema 与 Migration

### JSON Schema

创建：

- `page.schema.json`
- `chunk.schema.json`
- `food-fact.schema.json`
- `plan-rule.schema.json`
- `platform-fact.schema.json`

Schema 固定枚举：`source_code=A|B|C`、`source_role=core_nutrition|auxiliary_platform`、`review_status=verified|review_required|rejected`。

### PostgreSQL migration

首条 migration 建立 documents、pages、chunks、food_facts、plan_rules、platform_facts 和 ingestion_runs。向量维度尚未确认时不猜测建列；后续在 Embedding manifest 确认后新增 migration。所有表保留 source/page/version/hash，C 的营养用途约束由 CHECK 和导入器双重限制。

## 8. DATA-06 文件级 smoke

`scripts/validate_knowledge.py` 至少检查：

- 文件 hash、页数、记录数、JSON 可解析；
- 必填字段、枚举、稳定 ID 和引用完整；
- A/B 只能是 core，C 只能是 auxiliary；
- C 的 forbidden routes 完整，C 事实不出现在 food/plan 文件；
- verified 数字有 page 和 review 记录；
- 空文本、重复 ID、越界页码、未知来源均为失败；
- 生成机器可读 JSON 和人类可读 Markdown 报告。

Embedding/数据库未运行不算失败，但报告必须显示 `NOT_RUN` 和对应 ACTION ID。

## 9. 退出门禁

| Gate | 条件 |
|---|---|
| G1 | 18 页全部解析且可回溯原 PDF |
| G2 | Chunk 不跨页，ID 唯一，来源字段完整 |
| G3 | A/B 结构化事实已完成至少一轮人工页级核对 |
| G4 | C 事实严格 auxiliary，营养用途为 0 |
| G5 | JSON Schema 和 migration 已生成并静态验证 |
| G6 | 文件级数据与隔离 smoke 全绿 |
| G7 | Docker/Embedding 未执行项如实标注并继承 ACTION |
| G8 | Phase 03 输入清单和失败边界明确 |

`PASS WITH ACTION` 允许 Docker/向量运行项未执行，但不允许来源 hash、页码、A/B/C 隔离或关键数字复核失败。
