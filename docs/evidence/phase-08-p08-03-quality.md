# P08-03 文档、AI 披露、许可证与隐私冻结

## 结论

P08-03 以 `PASS` 完成。README 已更新到 Phase 08 客观基线；AI 使用披露已填入实际工具、日期、模块、人工责任与验证方式；MIT 许可证、第三方/来源边界、面向用户隐私说明、安全边界和 6 条机器可读数据路径齐全。文档没有“待填写”或旧阶段误导文案。

## 验收结果

| 检查 | 结果 | 证据 |
|---|---:|---|
| README 运行/测试/状态/限制 | PASS | `README.md`（3531 字符） |
| AI 使用实际披露 | PASS | `docs/AI_USAGE.md` |
| 原创代码许可证 | PASS | `LICENSE` |
| 赛题资料与依赖权利边界 | PASS | `THIRD_PARTY_NOTICES.md` |
| 实际个人数据流与用户权利 | PASS | `PRIVACY.md` |
| 安全控制与已知限制 | PASS | `SECURITY.md` |
| 机器可读统一数据路径 | 6/6 PASS | `docs/release-data-map.json` |
| 自动文档防漂移门 | 7/7 PASS | `docs/evidence/phase-08-p08-03-doc-validation.json` |
| 文档后全仓密钥复扫 | 458 files / 0 findings | `docs/evidence/phase-08-p08-01-secret-scan.json` |

## 与实现一致的关键披露

- 账号保存规范化邮箱、scrypt 密码哈希、认证令牌哈希；明文密码和明文 token 不在服务端持久化。
- Web 当前把 30 天 bearer token 存在 `localStorage`，不是 HttpOnly Cookie；已披露风险和正式运营加固项。
- 健康档案为请求内临时状态，不单独落库；写进聊天正文的健康信息随对话持久化。
- 当前没有自动对话保留 worker；对话到用户删除、账号删除或运营方清理为止。
- 默认 Compose 使用本地 Ollama；改用远程 Provider 时，消息、证据和必要约束会发送给该 Provider。
- 公网部署、HTTPS/托管数据库 TLS、监测与七天可用性仍由 ACTION-05 管理。

## 问题与解决

- ISSUE-069：README 停在 Phase 04、AI_USAGE 含多处待填写、根目录缺许可证/隐私/安全入口，`.env.example` 还列出 Settings 未消费的 JWT/Cookie/Retention 变量。已以运行代码和迁移为真值重写文档，删除虚假配置承诺，增加机器数据路径与自动门。
- Ollama 的 `ollama-local` 兼容哑 key 被秘密赋值规则首轮误报；加入明确占位测试后，458 文件复扫零发现。

## Sulde 规则影响

采用“公开政策、代码、依赖与真实数据路径使用同一事实”的原则，但不套用移动商店特有结论。由于本项目存在账号、远程模型能力和服务端持久化，不能写成“数据不离设备”；外部账号绑定发布动作继续与实现阶段分离。

## 沉淀候选

发布文档冻结应把实现过度声明也视为失败：环境变量样例、隐私政策、UI、迁移和 Provider 数据流必须来自同一真值；未实现的 Cookie、保留任务或公网 TLS 只能写成限制/后续门，不能写成现状。
