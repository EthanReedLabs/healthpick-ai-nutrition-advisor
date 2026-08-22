# ACTION-06 全量结构化事实复核记录

- 复核范围：`80` 条结构化事实（31 条食材、37 条方案规则、12 条平台事实）
- 复核方式：`Project Lead-authorized review / Codex-assisted`
- 页面范围：A 5 页、B 8 页、C 5 页，共 `18` 页
- 最终处置：`74 verified / 6 rejected / 0 review_required`
- ACTION-06：`CLOSED`

## 处置原则

逐页对照资料截图与结构化字段。可从页面可靠确认的字段标记为 `verified`；以下 6 条规则涉及源文不可恢复缺字，未猜测比较符或限定符，标记为 `rejected` 并继续从运行时隔离：

- `rule-A-glucose_control_guidance`
- `rule-B-fat_loss_eligibility`
- `rule-B-fat_loss_targets`
- `rule-B-muscle_eligibility`
- `rule-B-plan_selection`
- `rule-B-plan_faq`

驳回代表复核已经完成并形成明确处置，不代表问题被伪装修复。7 条确定性推荐核心规则集合保持不变，全部为 `verified`，上述 6 条驳回规则均不进入运行时推荐。

## 自动门禁

- 80 条记录均有最终处置和页图证据。
- 74 条通过记录不包含未解决缺字。
- 驳回集合精确等于 6 条缺字规则。
- `review_required=0`。
- 知识 Schema、来源隔离、数据库、向量索引、缺字排除和核心推荐规则门禁均为 `PASS`。

机器可读证据见 `docs/evidence/action-06-full-structured-fact-review.json` 与 `docs/evidence/phase-02-knowledge-validation.json`。
