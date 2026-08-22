# P08-02 公网部署与 Compose 干净复现

## 结论

P08-02 以 `PASS` 完成。本地干净 Compose 复现通过；Alibaba Cloud ECS 已按用户确认的纯镜像边界加载四个镜像并以 `--no-build` 启动，迁移、seed、四个长驻容器和真实百炼 Token Plan `qwen3.7-plus` 演练均通过。公网 IP 已获得 Let’s Encrypt 短期受信证书，首页、健康检查、浏览器真实问答、引用隔离和 S3 急症停止链路全部通过。

## 干净环境结果

| 检查 | 结果 | 证据 |
|---|---:|---|
| Compose 配置展开 | PASS | `docker compose -p healthpick-p08-clean config --quiet` |
| 当前源码 production images 构建 | PASS | Python 3.13 API、Node 22/Next 16 Web |
| 新空卷 migration | 001–005 全部 applied | `docs/evidence/phase-08-p08-02-compose.json` |
| 新空卷 seed | 3/18/67/31/37/12 精确计数 | 同上 |
| 真实模型问答 | PASS，仅 A 引用 | 同上 |
| PostgreSQL/API/Web 重启 | PASS | 同上 |
| 会话、turn、request、回答、模型保持 | PASS | 同上 |
| API/Web 非 root、只读、健康 | PASS | `docs/evidence/phase-08-p08-02-container-security.json` |
| ECS 纯镜像交付与 `--no-build` 启动 | PASS | `docs/evidence/phase-08-p08-02-ecs-production.json` |
| 百炼 Token Plan `qwen3.7-plus` 真实演练 | PASS | 同上，三路由、S3、历史与清理通过 |
| 公网 HTTPS | PASS | `https://106.14.13.139` 首页与健康检查均为 200 |
| 公网浏览器真实链路 | PASS | `docs/evidence/phase-08-p08-02-ecs-public-browser.json` |

## 隔离参数

- Compose project：`healthpick-p08-clean`
- Web：`127.0.0.1:13120`
- API：`127.0.0.1:18120`
- PostgreSQL：`127.0.0.1:55449`
- 现有开发栈 3100/8010/54329 未被覆盖或删除。
- 隔离栈和卷暂时保留，便于最终核验；未执行破坏性清理。

## 问题与解决

- ISSUE-067：smoke 将迁移版本硬编码为 001–004，当前新库正确包含 005 时产生假失败。改为从合法 migration 文件生成期望版本，并增加断言；5 项生命周期测试通过。
- ISSUE-068：P08 专用证据路径仍写 Phase 05 evidence ID。增加 `--evidence-id` 参数，保持旧默认兼容，最终证据为 `PHASE-08-P08-02-CLEAN-COMPOSE`。
- ISSUE-073：服务器无法稳定从 Docker Hub 拉取 Caddy，且用户要求只接收镜像。改为可信本机构建/拉取、分应用与基础设施导出镜像归档、双端 SHA-256 校验、服务器 `docker load`，加载后删除传输归档；服务器源码文件计数为 0。
- ISSUE-074：Caddy 已监听 80/443，但 Let’s Encrypt 从公网执行 HTTP-01 与 TLS-ALPN-01 均连接超时。服务器 firewalld 未运行且 iptables INPUT 为 ACCEPT，根因定位到阿里云安全组未放行；用户放行 TCP 80/443 后证书签发与公网访问通过。
- ISSUE-075：`sk-sp-` Token Plan Key 错配到通用 DashScope 端点返回 401。对两个官方专属端点做不泄密探测后，Token Plan 端点以 `qwen3.7-plus` 返回 200；修正生产端点并仅重建 API 后，完整演练通过。
- ISSUE-076：临时 `sslip.io` 域名在阿里云中国大陆节点触发未备案拦截。改用 Let’s Encrypt 支持的公网 IP 短期证书，不依赖未备案域名，公网 HTTPS 恢复。
- ISSUE-077：部分不发送 SNI 的 IP 客户端握手时 Caddy 无法选择证书。设置全局 `default_sni {$PUBLIC_HOST}` 后，Windows curl、Python 和 Chromium 均通过受信 HTTPS。

## 公网验收

`https://106.14.13.139` 已通过受信 HTTPS 返回首页和 `/healthz`，健康响应为 `llm=real`。Chromium 中完成营养 A 类引用、平台 C 类引用和独立 S3 急症停止；所有 API 请求均使用公网 IP 同源，测试会话随后以 204 删除。短期 IP 证书续期与七天可用性责任转入 P08-06，不再阻断 P08-02。

## 沉淀候选

Compose 生命周期验收的期望迁移集合应来自仓库真值，而不是复制阶段时的硬编码列表；证据 ID 也应由运行参数决定，避免复用脚本时生成内容正确但归属错误的证据。
