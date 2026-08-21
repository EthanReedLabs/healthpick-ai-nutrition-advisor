# P03-04 引用与证据校验质量门禁记录

- 日期：2026-08-21
- 引用专项测试：13/13 PASS
- API 全量回归：42/42 PASS，报告 `docs/evidence/phase-03-api-pytest.xml`
- Ruff check / format check：PASS，24 个 API/测试文件
- 实际检索—引用—验证 smoke：PASS，见 `phase-03-citation-runtime.json`

校验器采用 fail-closed：支持范围内的回答必须有引用和 `【Chunk-ID】` 内联标记；Chunk 必须存在于索引，source/title/page/section 必须一致，excerpt 必须是原文连续子串，且来源必须符合本次路由。伪造、篡改、重复、越界或未随响应返回的引用都会产生稳定错误码。

残余门禁：引用机制已通过，但部分源 Chunk 仍为 `review_required`；ACTION-06 完成二人复核前，相关内容不能作为最终发布证据放行。
