# P05-02 输入边界、错误契约与超时质量报告

## 结论

`P05-02` 达到全部计划门槛，可以关闭为 `passed`。公共 API 具备稳定的请求体和字段边界；模型、Embedding 与数据库故障不再塌缩为同一错误；Web 只接受合法 SSE `final`，超时后可用同一客户端 request ID 安全重试。

## 实现边界

- 请求体最大 32768 bytes；Chat 消息去空白后 1～2000 字符，标题 1～80，列表 limit 1～100。
- 所有失败继续使用 `request_id`、`code`、`message`、`retryable`、可选 `details` 的错误体；413、405、422、500/502/503/504 均覆盖。
- 模型区分 timeout、connection、rate limit、upstream unavailable、rejected request 和 invalid response；Embedding 使用对应独立错误码。
- PostgreSQL 同时设置连接超时和语句超时，并区分 timeout、unavailable、database failure 与未分类内部错误。
- 只有完整通过安全和证据门禁的结果才会持久化；客户端 45 秒超时不会展示半成品，重试复用原始 `X-Request-ID`。
- 200 响应若不是 `text/event-stream` 或缺少有效 `final`，客户端按可判别协议错误失败，不把 JSON/HTML 当成功回答。

## 质量结果

| 检查 | 结果 | 证据 |
|---|---:|---|
| Python 全量测试 | 188/188 PASS | `docs/evidence/phase-05-p05-02-api-pytest.xml` |
| Web 全量测试 | 18/18 PASS | `docs/evidence/phase-05-p05-02-web-vitest.xml` |
| Ruff / format | PASS / 132 files | 本次质量门输出 |
| ESLint / TypeScript / Next build | PASS | 本次质量门输出 |
| 真实 API 413/422 与 request ID 往返 | PASS | `docs/evidence/phase-05-p05-02-error-contract.json` |
| 真实 PostgreSQL 100 ms statement timeout | PASS | `docs/evidence/phase-05-p05-02-error-contract.json` |
| 提供商 504 且超时不落历史 | PASS | `docs/evidence/phase-05-p05-02-error-contract.json` |
| 真实模型三路全栈 | PASS | `docs/evidence/local-real-stack-runtime.json` |
| 浏览器同 ID 重试 | PASS | `docs/evidence/phase-05-p05-02-browser.md` |
| 会话持久化回归 | PASS | `docs/evidence/phase-05-p05-01-postgres.json` |

## 问题闭环

- `ISSUE-035`：输入体无总上限且传输、超时、协议、业务错误分类不足；已按层分离并故障注入。
- `ISSUE-036`：前端信任错误响应 ID 会让重试 ID 漂移；已固定使用客户端原始 ID，单测与浏览器网络头验证通过。
- `ISSUE-037`：Phase 04 runtime smoke 仍使用旧字符串对话 ID，并强制真实模型路径；已统一改用规范会话 API，合法证据回退也纳入断言。

P05-02 无残余行动；更完整的移动端错误布局和空/加载状态继续由 P05-03 验收。

## 沉淀候选

1. 错误码必须按传输、超时、上游否定、协议和业务规则分层；一个兜底码会同时破坏重试策略与排障方向。
2. 幂等重试应绑定客户端首次生成的 request ID，不能把错误响应或代理返回的相关 ID 当成下一次幂等键。
3. API 从临时字符串 ID 升级为服务端规范 ID 后，所有 runtime smoke 都必须先走公开创建契约；只改产品前端会留下验收脚本断层。
