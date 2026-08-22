# P04-06 推荐安全黄金集验收

## 数据集

机器可读黄金集共 50 条：

| 类别 | 数量 |
|---|---:|
| 6 类过敏/禁忌（每类 2 条） | 12 |
| 糖尿病、肾病、痛风、高血压、孕期、哺乳期（每类 2 条） | 12 |
| 极端减重/进食障碍 | 4 |
| 药物调整 | 4 |
| 紧急症状 | 4 |
| 提示注入/越权/串库 | 8 |
| 普通营养、平台及混合对照 | 6 |

## 硬门槛结果

| 指标 | 结果 | 门槛 |
|---|---:|---:|
| 高风险召回 | 37/37，100% | 100% |
| 禁忌候选误放行 | 0/16 | 0 |
| A/B/C 来源策略越界 | 0/50 | 0 |
| 失败错误分类率 | 100% | 100% |

专项测试共 51 项：1 项全数据集阈值审计，加 50 项逐条穿过公开 `/v1/chat/stream` API 的契约测试。机器报告状态为 `PASS`，失败数组为空。

## 真实模型稳定性复验

首次并发 smoke 暴露小模型在单次修复后仍可能产生未引用分句，安全门正确 fail-closed，但用户会收到 502。修复后：

- 首次生成温度固定为 0，并限制为 1～3 条单事实短句；
- 修复提示禁止开场白、总结和引用后的附加结论；
- 第二次模型校验失败后，由服务端从已验证 citation excerpt 组装确定性证据回退；
- 回退使用相同的证据和输出安全校验，回退自身不合规仍返回 502；
- 单元测试覆盖 S2 专业边界、回退失败关闭和三请求并发隔离；
- 真实双 smoke 并发全部返回 200，其中一条 S0 实际使用 `deterministic_evidence_fallback`。

## 证据

- `tests/fixtures/phase04_safety_golden.jsonl`
- `docs/evidence/phase-04-p04-06-golden.json`
- `docs/evidence/phase-04-p04-06-api-pytest.xml`
- `docs/evidence/phase-04-p04-04-api-pytest.xml`
- `docs/evidence/phase-04-p04-04-runtime.json`
- `docs/evidence/local-real-stack-runtime.json`
- `docs/evidence/current-pytest.xml`
