# P07-04 评测概览与透明度展示记录

## 结论

P07-04 以 `PASS` 完成。真实冻结评测报告经白名单脚本生成脱敏公开摘要，由版本化 API 合同供 Web 展示；自动门、人工复核和主备模型策略均明确区分。

## 数据链与防伪装

1. 源数据固定为 v1.1 attempt 3 不可覆盖报告。
2. `scripts/export_public_evaluation.py` 只允许九项冻结门全部通过、清理通过且首轮失败已保留的报告发布。
3. 公开摘要只保留数据集哈希、规模、指标、门限、人工复核状态与源报告哈希；删除本地 API 地址、Git 状态、内部路径和供应商秘密。
4. `/v1/evaluation/summary` 使用严格模型加载打包摘要，Docker 的 `COPY apps/api` 会携带该版本化文件。
5. Web 只从 API 读取分数；读取失败显示“不会使用演示占位分数”。

## 验证

| 验证项 | 结果 | 证据 |
|---|---:|---|
| API/OpenAPI/Provider 回归 | 29/29 PASS | `docs/evidence/phase-07-p07-04-api-pytest.xml` |
| Web 组件回归 | 27/27 PASS | `docs/evidence/phase-07-p07-04-web-vitest.xml` |
| TypeScript 类型检查 | PASS | `npm run typecheck` |
| ESLint | PASS | `npm run lint` |
| Ruff | PASS | P07-04 Python 文件 |
| 真实接口 | PASS | 9/9 自动门、整体 PASS_WITH_ACTION、人工 PENDING |
| 桌面浏览器 | PASS | `docs/evidence/phase-07-p07-04-browser.md` |
| 浏览器控制台 | PASS | 0 errors / 0 warnings |

## 问题闭环

- ISSUE-063：透明度卡最初直接展示内部枚举 `retryable_or_invalid_response`，长词换行且不利于评委理解；已改为“可重试故障 / 无效响应”并增加组件断言。
- 首次浏览器插件调用因宿主缺少 `sandboxPolicy` 元数据不可用，随后确认本机已有 Playwright 1.62.1，使用 `npx --no-install playwright cli` 完成同等验收；未安装依赖或修改全局配置。
- 静态检查首次发现一个未使用导入；已移除并把 Ruff、Pytest 分开执行，避免后续命令掩盖中间退出码。

## 沉淀候选

面向用户的评测概览必须由冻结报告生成并保留源哈希，自动门通过与人工签署状态必须并列展示；公开层应采用字段白名单，不能直接转发包含本地地址、Git 状态和内部路径的完整报告。
