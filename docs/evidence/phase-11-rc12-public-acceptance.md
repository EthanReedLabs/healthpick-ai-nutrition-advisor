# RC12 公网部署与视觉验收

结论：通过。提交 `8b0446e5e986126a8b002e2b88fdd7ff5e0ea6c8` 已构建为 `linux/amd64` Web 镜像 `healthpick-web:rc12-chat-feedback-20260823`，并以仅镜像、仅重建 Web 服务的方式部署至 <https://106.14.13.139/>。公网首页返回 200，Web、API 与 PostgreSQL 均健康，Caddy 正常运行，所有容器重启计数均为 0。API、数据库、Caddy 和百炼千问配置未重建或更改。

## 交互验收

使用真实浏览器发送两轮减脂问题。点击发送后 100 毫秒内观察到：输入框值为空；对话区恰好出现 1 个待处理用户气泡；“正在接收并安全校验回答”和“停止生成”均可见；输入框光标样式为 `default`。完整回答返回后，页面只保留一份正式用户消息，没有临时气泡重复；回答标注 `openai_compatible · qwen3.7-plus · real`，包含 S0 安全分级、“轻盈减脂方案”和资料 A/B 的页码引用。浏览器控制台记录为 0 个错误、0 个警告。

等待态截图见 `apps/web/output/playwright/rc12-public/rc12-public-pending.png`，最终态截图见 `apps/web/output/playwright/rc12-public/rc12-public-final.png`。机器可读的镜像摘要、服务状态、视觉断言和截图哈希见 `docs/evidence/phase-11-rc12-public-acceptance.json`。

## 清理与可恢复性

视觉验收产生的两轮测试对话已通过界面删除，PostgreSQL 中标题匹配 `RC12%` 的记录数为 0，浏览器会话已关闭。服务器 `/opt/healthpick/incoming` 中本轮上传 tar 已删除且目录恢复为空；该文件仍保留在本地不可变版本目录，可在需要时重新传输。服务器未上传项目源代码。
