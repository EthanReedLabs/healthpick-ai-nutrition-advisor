# P05-03 三档真实浏览器验收

- 验收时间：2026-08-22 10:13～10:25（Asia/Shanghai）
- Web：`http://127.0.0.1:3100`
- API：`http://127.0.0.1:8010`
- 浏览器：Playwright CLI / Chromium，复用真实 PostgreSQL 与 Ollama 数据

## 验收结果

| 视口 | document / body scrollWidth | 关键布局 | 结果 |
|---|---:|---|---:|
| 375 × 812 | 375 / 375 | 移动顶栏保留历史、新对话、档案、Real 状态；历史为底部弹层 | PASS |
| 768 × 1024 | 768 / 768 | 左侧历史与主工作区并列，输入和引用卡正常换行 | PASS |
| 1440 × 1000 | 1440 / 1440 | 左侧历史、主工作区、右侧档案/资料边界三栏完整 | PASS |

## 交互与无障碍

1. 375px 点击“历史”后出现 `role=dialog` 的“最近对话”，当前项具有可访问名称和当前状态，删除操作有独立名称。
2. 弹层打开后“关闭最近对话”自动成为 active focus；按 `Escape` 后弹层消失。
3. `Shift+Enter` 后 textarea 实际值为 `键盘验收\n`，页面未进入 busy、未发送请求；随后清空测试内容。CLI 组合键命令自身超时，但只读 DOM 取证确认应用行为正确。
4. 三档分别扫描所有带 ID 的元素，重复 ID 均为 0。
5. 浏览器累计 15 条控制台信息中 Errors=0、Warnings=0。
6. 加载、会话失败恢复、删除当前对话后选中下一条由 5 个新增组件场景验证；真实超时和同 ID 重试沿用 `phase-05-p05-02-browser.md` 的端到端证据。

## 截图

- `output/playwright/phase-05-p05-03-mobile-history-375x812.png`
- `output/playwright/phase-05-p05-03-tablet-768x1024.png`
- `output/playwright/phase-05-p05-03-desktop-1440x1000.png`

本机 WSL1 不能启动技能附带的 Linux wrapper，本次按技能降级规则使用等价的原生 Windows `npx --package @playwright/cli playwright-cli`；没有安装或修改全局工具。
