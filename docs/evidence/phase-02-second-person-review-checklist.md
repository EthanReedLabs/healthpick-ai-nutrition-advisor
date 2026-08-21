# Phase 02 第二人复核清单

## 1. 目的与放行规则

本清单用于参赛者逐条核对 Phase 02 生成的 80 条结构化记录。Codex 已完成页面渲染与第一轮视觉对照，但营养数字、方案阈值、禁忌和平台声明在第二人复核前统一保持 `review_required`。

只有同时满足以下条件的单条记录才能改为 `verified`：

1. 对照对应 PDF 页面或 `docs/evidence/phase-02-page-review/` 中的页面图；
2. 核对名称、数字、小数、单位、份量基准、适用范围和上下文；
3. 确认 source、page/pages、section 与页面一致；
4. 在 curated YAML 的该条 item 中填写 `review_status: verified` 和完整 `second_person_review`；
5. 重新生成事实文件并通过全部知识校验和测试。

生产导入只接收 `verified`。`review_required` 和 `rejected` 均不得进入面向用户的数值回答或推荐规则。

## 2. 复核范围

| 数据集 | Curated 真值 | 生成产物 | 数量 | 页面证据 |
|---|---|---|---:|---|
| 食材事实 | `knowledge/normalized/curated/foods.yaml` | `food_facts.jsonl` | 31 | A-p02～A-p03 |
| 营养/方案规则 | `knowledge/normalized/curated/plans.yaml` | `plan_rules.jsonl` | 37 | A-p01～A-p05、B-p01～B-p08 |
| 平台事实 | `knowledge/normalized/curated/platform.yaml` | `platform_facts.jsonl` | 12 | C-p01～C-p05 |
| 合计 | 3 个 YAML | 3 个 JSONL | 80 | 18 张 PNG |

## 3. 原始 PDF 已确认的缺字

下列空缺同时存在于原 PDF 的可视渲染和文本层，并非解析器自行丢失。严禁根据语义猜测 `≥`、`≤`、`β` 或其他符号。

| Source/Page | 观察到的缺失 | 处理规则 |
|---|---|---|
| A-p02 | “胡萝卜素”前的符号缺失 | 不补写符号；只核对不受影响的表格项 |
| A-p04 | “200g 水果”前的比较符缺失 | 相关规则保持 `review_required` |
| B-p01 | BMI、腰围、蛋白质、膳食纤维等 8 处比较符缺失 | 所有受影响阈值保持 `review_required` |
| B-p05 | 每周力量训练次数前比较符缺失 | 相关规则保持 `review_required` |
| B-p07 | 方案选择映射中的 BMI 比较符缺失 | 相关规则保持 `review_required` |
| B-p08 | 每周代餐次数前比较符缺失 | 相关规则保持 `review_required` |

解除这些记录的阻塞需要取得修正版源文件或赛题方的书面确认，并更新 source version/hash；仅凭经验推断不能放行。

## 4. 单条记录操作模板

在对应 curated YAML 的 item 中增加：

```yaml
review_status: verified
second_person_review:
  reviewer: "参赛者真实姓名或团队标识"
  date: "2026-08-21"
  notes: "已对照 A-p03，名称、100g 基准、能量/蛋白质/脂肪/钙及适用标签一致。"
```

不要修改数据集顶层的 `review_status` 来批量放行。含 `unknown_glyph: true` 的规则不得设为 `verified`。

## 5. 每条复核断言

### FoodFact（31 条）

- 食材名称和分组正确；
- `basis.amount/unit/qualifier` 与表头一致；
- 四项营养素的字段、数字、小数位和单位均正确；
- 推荐标签属于原文表格，不扩写医学结论；
- page/section 指向正确。

### PlanRule（37 条）

- 规则标题和类型能表达原文，不扩大适用范围；
- 数值、比较关系、周期、餐次和单位完整；
- 适用条件、排除条件、禁忌和免责声明未被截断；
- 菜单每天/每餐未发生跨行错位；
- 缺字符号没有被猜测恢复。

### PlatformFact（12 条）

- 套餐、价格、服务、API、合作与联系信息逐字义核对；
- `claim_scope` 保持 `provided_whitepaper_only`；
- 不把平台白皮书中的案例或能力当作独立验证事实；
- `allowed_routes` 仅为 platform，三个营养用途仍禁止。

## 6. 重建与验收

```powershell
.\.venv\Scripts\python.exe scripts\build_structured_facts.py
.\.venv\Scripts\python.exe scripts\validate_knowledge.py
.\.venv\Scripts\pytest.exe -q --junitxml=docs/evidence/phase-02-pytest.xml
```

验收标准：脚本退出码均为 0；validation 为 `PASS`；`review_required_records` 按实际复核数量递减；任何 `verified` 记录都有完整第二人复核信息；含缺字规则仍未放行。

