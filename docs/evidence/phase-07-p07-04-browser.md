# P07-04 浏览器验收

- 时间：2026-08-22T13:51:38+08:00
- 地址：`http://127.0.0.1:3100`
- 视口：1440 × 1000
- API：`http://127.0.0.1:8010`
- 运行模式：Real LLM、Real Embedding、Keyword Retrieval、PostgreSQL

## 结果

- 页面显示 `72` 用例、`80` 轮对话和 `9/9 自动门通过`。
- 页面显示路由 100%、引用支持 95.6%、高风险召回 100%、多轮约束 100%、来源泄漏 0%、首字 P95 2814 ms。
- 页面同时显示 `整体状态：待人工复核`、`ACTION-06 · 53 个事实用例` 和 `PASS_WITH_ACTION`，未把自动门通过解释为最终签署。
- `/v1/evaluation/summary`、`/v1/transparency`、`/healthz` 的稳定请求均为 HTTP 200；页面重载/React 开发期取消的旧请求显示 `ERR_ABORTED`，随后成功请求完成。
- 浏览器控制台 Errors=0、Warnings=0。
- 透明度卡显示真实模型、嵌入模型、存储模式、备用启用状态与中文切换策略，未显示 URL 或密钥。

## 截图

- `output/playwright/phase-07-p07-04-evaluation-card.png`
- `output/playwright/phase-07-p07-04-desktop.png`
