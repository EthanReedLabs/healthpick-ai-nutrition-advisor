# P07-05 关键体验与可访问性打磨记录

## 结论

P07-05 以 `PASS` 完成，并关闭 ACTION-08 / ISSUE-048。用户可在真实生成期间主动停止；Web 与 API 使用同一 UUID 请求编号协同取消，管线任务在持久化前终止，桌面和移动端真实 PostgreSQL 均验证零轮次。

## 实现

- Web `sendChat` 接受外部 AbortSignal，明确区分用户取消、45 秒超时和连接失败。
- 生成期间发送按钮替换为带可访问名称的停止按钮，不靠颜色传达含义。
- Web 先停止本地读取，再调用幂等服务端取消接口；取消确认失败时使用“不确认”文案，不伪装成功。
- API 为每个请求编号登记独立异步任务；重复活动请求号返回 409，取消接口终止指定任务并最终清理注册表。
- ChatPipeline 只在完整回答通过证据/安全校验后写入，因此取消任务不会保存半成品。
- 停止后保留输入并恢复焦点，状态区通过 `role=status` 宣告结果；既有 `aria-live`、`aria-busy`、焦点轮廓和 reduced-motion 规则继续生效。

## 验证

| 验证项 | 结果 | 证据 |
|---|---:|---|
| API/SSE/取消专项 | 34/34 PASS | `docs/evidence/phase-07-p07-05-api-pytest.xml` |
| Web/API client/交互组件 | 30/30 PASS | `docs/evidence/phase-07-p07-05-web-vitest.xml` |
| Ruff / ESLint / TypeScript | PASS | P07-05 相关代码、`npm run lint/typecheck` |
| OpenAPI 与生成类型 | PASS | `packages/shared/openapi/healthpick.openapi.json`、`apps/web/src/lib/api-schema.d.ts` |
| 桌面/移动真实取消 | PASS | `docs/evidence/phase-07-p07-05-cancellation.json` |
| 浏览器可视与控制台 | PASS | `docs/evidence/phase-07-p07-05-browser.md` |

## 问题闭环

- ISSUE-048 / ACTION-08：原系统没有用户主动停止入口；现已完成端到端取消与不落库验收，正式关闭。
- ISSUE-064：Playwright locator 对异步替换按钮的重定位产生假重发；使用原生 DOM 点击建立真实用户事件证据，并把该限制写入浏览器验收记录。

## 沉淀候选

“停止生成”不能只做视觉隐藏：必须把客户端 AbortSignal、服务端活动任务注册、管线取消传播和持久化负断言连成一条可验证链。自动化点击异步替换的按钮时要防止 locator 重定位到后继按钮，否则会制造重复提交假象。
