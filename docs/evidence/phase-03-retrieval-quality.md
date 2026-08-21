# P03-03 路由与检索质量门禁记录

- 日期：2026-08-21
- 实际语料：A=21、B=26、C=20，共 67 个 Chunk
- 路由/检索专项测试：13/13 PASS
- API 全量回归：29/29 PASS，报告 `docs/evidence/phase-03-api-pytest.xml`
- Ruff check / format check：PASS，20 个 API/测试文件
- 实际知识文件 smoke：PASS，见 `phase-03-retrieval-runtime.json`

已验证的硬边界：

- nutrition/recommendation/contraindication 只能使用 A/B；
- platform 只能使用 C；
- mixed 至少保留一条 A/B 和一条 C（存在相关命中时）；
- out_of_scope 不返回证据；
- 每次检索 trace 都记录允许来源、检查数、隔离拒绝数、命中数和模式；
- 当前模式明确为 `keyword`，`embedding_claimed=false`，不会猜测未确认的向量维度。

残余门禁：ACTION-03 确认真实 embedding manifest 后才能增加 vector/hybrid；ACTION-06 完成缺字符号与结构化事实复核后才能最终放行相关证据。
