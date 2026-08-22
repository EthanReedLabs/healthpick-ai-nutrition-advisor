# P07-03 主备模型切换与故障演练记录

## 结论

P07-03 以 `PASS` 完成。主模型只在连接、超时、限流、上游不可用或成功响应协议无效时切换一次备用模型；不可重试的请求拒绝不切换。主备同时失败统一返回 `provider_failover_exhausted`，失败请求不写入会话。

## 实现范围

- `FailoverLLMProvider` 封装主备适配器，业务与对话管线不包含供应商专属分支。
- 主备模型分别配置 provider、base URL、密钥、模型名和超时；默认关闭，开启时执行完整启动校验。
- `/v1/transparency` 只披露非敏感的启用状态、策略和备用模型标识，不返回 URL 或密钥。
- 备用成功结果带 `failover=used` 和主模型失败码，供日志与演练取证；不会把失败结果或半成品写入对话。
- 主备均失败时隐藏上游错误正文，以稳定、可重试的统一错误契约返回。

## 验证结果

| 验证项 | 结果 | 证据 |
|---|---:|---|
| Ruff 静态检查 | PASS | P07-03 相关 Python 文件 |
| Provider、API、SSE 回归 | 48/48 PASS | `docs/evidence/phase-07-p07-03-pytest.xml` |
| 注入主模型连接失败并切换真实 Ollama | PASS | `docs/evidence/phase-07-p07-03-failover.json` |
| 注入主备双故障并统一错误码 | PASS | `docs/evidence/phase-07-p07-03-failover.json` |
| 双故障不持久化会话 | PASS | `tests/api/test_chat_sse.py`、JUnit 证据 |
| 不可重试请求不切换 | PASS | `tests/api/test_providers.py` |
| 主备资源均关闭 | PASS | `tests/api/test_providers.py` |

真实备用模型为本机 `ollama-local-backup/qwen2.5:3b-instruct`。取证文件只保存回答长度与 SHA-256，不保存回答正文、URL 或密钥。

## 问题闭环

- ISSUE-062：启用备用模型时空字符串密钥最初可通过配置构造，只会在首个请求时失败；已收紧主、备密钥空值校验并增加两条回归测试。
- 故障演练初稿中的“不持久化”只有适配器层推断；已补充主备双故障经 API/ChatPipeline 到会话存储的端到端断言。

## 沉淀候选

主备模型切换应保持在供应商适配器边界，并把可切换错误集合做成明确白名单；失败或超时的生成结果不得进入会话存储。故障演练证据既要覆盖真实备用服务，也要覆盖双故障错误契约和持久化负断言。
