# P06-03 来源透明与检索 Trace 浏览器验收

结论：`PASS`。

- 目标：Web `http://127.0.0.1:3100/`，API `http://127.0.0.1:8010/`；真实本地模型与 PostgreSQL 运行。
- 透明度卡片来自 `GET /v1/transparency` 的当前运行配置，展示 `qwen2.5:3b-instruct`、`qwen3-embedding:0.6b / 1024`、`keyword`、`postgres`、档案临时保存及 A/B/C 使用边界。
- 真实提问“膳食纤维有什么营养作用？”后，回答显示 `custom · qwen2.5:3b-instruct · real`；展开 Trace 可见 6 个返回 Chunk、来源边界排除 20 个、Chunk ID、来源、分数和命中词。
- 新建干净浏览器会话复查：横向溢出 `0`，重复 DOM ID `0`，控制台错误 `0`、警告 `0`；仅有 2 条开发环境 INFO/LOG。
- 首次复查发现手工重启 API 遗漏 `WEB_ORIGIN`，导致浏览器出现 8 条 CORS 错误；恢复项目子进程配置并增加统一启动器后，干净会话复验为 0 错误。

截图：

- `output/playwright/phase-06-p06-03-real-retrieval-trace.png`
- `output/playwright/phase-06-p06-03-transparency-card.png`
