# P08-02 公网部署与 Compose 干净复现

## 结论

P08-02 以 `PASS WITH ACTION` 完成。本地 Compose 使用独立项目 `healthpick-p08-clean`、新网络、新 PostgreSQL 卷和隔离端口，从当前冻结源码构建并完成迁移、seed、真实 Ollama 问答、三服务重启与同一会话持久化验收。公网 Render 仍需 `ACTION-05` 的区域、预算和七天可用性授权，未伪装完成。

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
| 公网 HTTPS | PENDING | `ACTION-05` / `ISSUE-005` |

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

## 公网阻断

Render 登录本身不是技术实现；需要用户明确区域、付费预算和七天在线责任授权。授权后才能配置生产 Secret、PostgreSQL、健康检查、HTTPS URL 和监测。当前没有公网 URL，因此 P08-04 只能先准备本地演示资产，P08-06/P08-07 不得签署。

## 沉淀候选

Compose 生命周期验收的期望迁移集合应来自仓库真值，而不是复制阶段时的硬编码列表；证据 ID 也应由运行参数决定，避免复用脚本时生成内容正确但归属错误的证据。
