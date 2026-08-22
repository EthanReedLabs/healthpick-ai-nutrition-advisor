# P07-01 完整黄金、安全与串库评测集验收

结论：`PASS WITH ACTION`。72 条固定评测集、80 轮对话、强类型契约、结构审计和发布阈值已在首次运行前冻结；53 条含事实/来源断言的用例继续等待 ACTION-06 第二人复核。

## 数据集覆盖

| 类别 | 用例数 |
|---|---:|
| A 基础营养事实 | 14 |
| B 方案与替换 | 14 |
| C 平台事实 | 8 |
| 路由与混合 | 10 |
| 多轮约束 | 8（16 轮） |
| 医疗安全 | 10 |
| 对抗与鲁棒性 | 8 |
| 合计 | 72 个用例 / 80 轮 |

## 机器门

- `ReleaseCase / ReleaseTurn / ReleaseExpectation` 使用 Pydantic `extra=forbid`，避免未知字段和不完整断言静默进入评测。
- A/B/C 允许来源和禁止来源必须无交集且完整分割；营养不得包含 C，平台只能使用 C，混合必须允许 A/B/C。
- 每个要求引用的 Chunk 必须存在、来源位于允许集合、`unknown_glyph_count=0`。
- 多轮类必须至少两轮并声明上下文策略；其余类别必须单轮。
- S2/S3 不允许 `normal`；HTTP 错误用例不得同时声称回答、路由或引用。
- 结构报告：`PASS`、72 cases、80 turns、0 errors；专项测试 2/2，Ruff 与 format 通过。

## 冻结与可追溯性

- 数据集：`evals/datasets/release-golden-v1.jsonl`，SHA-256 `ec60edc1fb4df35dd3dcc0a0929ef2a0d4ca7f569b1be5420ac71419e2c61b20`。
- 阈值：`evals/golden/release-gate-v1.json`，SHA-256 `b1c9b7a36e13a7a8e1fa28664a21ac3064ce505ccd2c090609dbcfce2a0041d7`。
- 来源清单 SHA-256：`718385efe40c60d276c9aa5f7f683ee8a3db175e20a93df9431fead0182edc27`。
- 阈值文件明确保留首次结果、重跑不覆盖、LLM judge 仅补充、安全/数字/来源使用确定性门且结果后不得降阈值。

## 实施中发现并解决

- ISSUE-057：生成器首跑被 `case_id` 长度契约拦截，短 ID `A-01` 不合规；改用稳定可读的 `ANUT/BPLAN/CPLAT-*` 前缀，随后 72 条全部通过。

## 保留行动

- ACTION-06：53 个含事实/来源断言的用例当前状态是 `second_person_required`。P07-02 可以运行自动来源、路由、安全和文本门，但最终“人工事实准确性”不得提前签署。

## 采用的工程经验

采用 Sulde `tech-docs/验证器输出必须为LLM设计`：生成器标准输出只给结论、cases/turns/errors 和详细报告路径，完整哈希、分类与错误数组写入 JSON 产物。
