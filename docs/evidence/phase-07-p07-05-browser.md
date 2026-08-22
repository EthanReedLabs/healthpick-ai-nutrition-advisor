# P07-05 停止生成与可访问性浏览器验收

- 时间：2026-08-22T14:08:33+08:00
- 环境：Real Ollama LLM、PostgreSQL、Keyword RAG
- 视口：1440×1000、375×812

## 结果

| 验收项 | 结果 |
|---|---:|
| 生成期间显示可操作的“停止生成”按钮 | PASS |
| 按钮语义为 `type=button`、可访问名称“停止生成本次回答” | PASS |
| 客户端终止正在读取的 chat fetch | PASS |
| 服务端取消接口返回 204 | PASS |
| 取消后等待仍无第二次用户请求 | PASS |
| 桌面 PostgreSQL 会话 turns=0 | PASS |
| 移动 PostgreSQL 会话 turns=0 | PASS |
| 输入内容保留且焦点恢复到输入框 | PASS |
| 375px `scrollWidth=viewportWidth=375` | PASS |
| 浏览器控制台 | 0 errors / 0 warnings |

桌面取消请求为 `4502df60-bf38-46f4-aca6-8f7dafba35df`，移动取消请求为 `c122eb29-b316-4898-b594-78935c72f1fe`；两者对应的新会话均为零轮次，详见 `phase-07-p07-05-cancellation.json`。

## 自动化工具假象

Playwright `locator.click()` 点击异步消失的停止按钮时会重试，并在按钮被“发送”按钮替换后误触发第二次提交。该行为有不同请求 ID，且只在 locator 自动重试路径出现。改用浏览器原生 DOM `button.click()` 后连续两次（桌面、移动）均只有一次 chat abort 和一次 cancel 204，等待后无重发；按钮实际 `type=button`。因此问题登记为 ISSUE-064 并在验收脚本口径中禁止使用会重定位的停止按钮点击。

## 截图

- `output/playwright/phase-07-p07-05-generating.png`
- `output/playwright/phase-07-p07-05-stopped.png`
- `output/playwright/phase-07-p07-05-stopped-mobile.png`
