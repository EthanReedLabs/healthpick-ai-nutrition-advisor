# RC9 公网预览部署记录

- 记录编号：`RC9-PREVIEW-DEPLOY-01`
- 完成时间：`2026-08-22T23:01:18+08:00`
- 公网地址：`https://106.14.13.139`
- 状态：`PASS / RUNNING`
- 发布性质：临时预览；未提交、未打正式标签、未推送

## 部署范围

仅替换 Web 容器为 `healthpick-web:rc9-preview-20260822`。API 继续运行 `healthpick-api:v0.1.0-rc8`，PostgreSQL、Caddy、知识库、数据、百炼千问配置和 HTTPS 均未修改或重启。服务器继续使用 RC8 的三个最小运行描述文件，未上传应用源码。

本地镜像归档：`output/deployment/healthpick-rc9-preview-20260822.tar`，大小 `188997120` 字节，SHA-256：`2B9729EDBCC7DEFB9F0F48CF75DF129B0500605410E0FB6E853378BFA5E46A26`。服务器复算一致后执行 `docker load`，成功切换后已删除服务器临时归档；本地归档保留。

## 关键不变量

- RC8 `current` 仍指向 `/opt/healthpick/releases/6e56b96f7d5ac4ffd306cdcedabfac7366034f44`。
- RC9 临时 API 标签与 RC8 API 的远端镜像 ID 相同：`sha256:87fd5fbc1cd239a545f761f117181353c0a23b7c7786803457ad068ac5de5714`。
- RC8 Web 镜像 ID 保留：`sha256:43676fbbf99510ff747d10521b30e7a98c076c2e82dbdf543663ab3456cf0b0d`。
- RC9 Web 镜像 ID：`sha256:92fc1d1ec3bcaf3aa0b4d37eb29f8de8271f186bd3f8116749c4c1d6fc539298`。
- 仅执行 `docker compose ... up -d --wait --no-build --no-deps web`；API、数据库和 Caddy 未重建。

## 公网验收

- 首页 HTTPS：`200`。
- `/healthz`：`status=ok`、`environment=production`、`llm=real`、`retrieval=keyword`、数据库已配置。
- 桌面端 `1440×1000`：欢迎卡、快捷问题、输入框和独立右侧资料栏首屏可见。
- 移动端 `375×812`：历史、新对话、档案、登录和在线状态横向排列；核心操作区无横向溢出。
- 真实问答：低钠问题经同请求编号超时恢复后成功；显示 `qwen3.7-plus · real`、S1 安全分级、高钠排除和 A/B 页码引用。
- 推荐引擎：缺少年龄段时正确阻断；补齐 `18–44 岁 + 减脂` 后生成“轻盈减脂”，规则匹配 `80` 分并展示已复核 A/B 依据。
- 浏览器控制台：`0 errors / 0 warnings`。
- 自动化测试对话已通过界面确认删除；隔离浏览器会话已清理。
- 最终容器：Web RC9 healthy，API RC8 healthy，PostgreSQL healthy，Caddy running。

## 发现与解决

1. 本机未记录服务器主机密钥，首次非交互 SSH 被严格校验拒绝。只读扫描主机 ED25519 公钥后写入项目级 `output/deployment/known_hosts.rc9`，未修改全局 `known_hosts`。
2. 专用登录公钥与用户批准的 `server-login-2026-08-22` 完全一致，但 OpenSSH 不会自动选择非默认私钥。所有连接显式使用 `id_ed25519_servers` 和 `IdentitiesOnly=yes`。
3. Windows 沙箱拒绝直接访问 Docker 进程。仅对已批准的镜像查询、构建、标记和导出命令使用受控提升权限，没有安装或修改全局软件。
4. 公网截图目录不存在导致第一次截图写入失败。只创建 `apps/web/output/playwright/rc9-public/` 后重试成功，页面未受影响。
5. Playwright `run-code` 首次使用了错误包装格式。读取帮助后改为 `async (page) => { ... }`；未重复错误命令，应用状态未受影响。
6. 真实模型首次请求超过客户端等待时间。界面没有伪造回答，并使用同一请求编号恢复；最终答案、安全门和引用全部通过。
7. 仅填写健康目标时推荐引擎因缺少年龄段正确阻断；补齐最小必要字段后正向推荐通过。

## 回滚

如果 RC9 Web 后续异常，在服务器执行以下命令即可只回滚 Web；不触碰 API、数据库、Caddy 或数据卷：

```bash
IMAGE_TAG=v0.1.0-rc8 docker compose -p healthpick-prod \
  --env-file /opt/healthpick/shared/production.env \
  --env-file /opt/healthpick/shared/bailian.env \
  -f /opt/healthpick/current/compose.yaml \
  -f /opt/healthpick/current/compose.production.yaml \
  up -d --wait --no-build --no-deps web
```

## 证据

- `apps/web/output/playwright/rc9-public/rc9-public-desktop-1440x1000.png`
- `apps/web/output/playwright/rc9-public/rc9-public-mobile-375x812.png`
- `apps/web/output/playwright/rc9-public/rc9-public-mobile-answer-375x812.png`
- `apps/web/output/playwright/rc9-public/rc9-public-mobile-recommendation-card.png`
- `output/deployment/healthpick-rc9-preview-20260822.tar`
