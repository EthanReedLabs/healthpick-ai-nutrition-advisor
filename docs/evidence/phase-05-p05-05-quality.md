# P05-05 P0 追踪矩阵与全回归报告

## 结论

`P05-05` 以 `pass_with_action` 关闭。Phase 05 本地 P0 实现和回归全部为绿，34 个赛题 P0 均已关联实现、测试、证据和后续门；最终发布相关要求没有提前标绿。

## 最新回归结果

- Python：193/193 PASS；Ruff PASS；141 files formatted。
- Web：23/23 PASS；ESLint、TypeScript、Next production build PASS。
- PostgreSQL 17.11、pgvector 0.8.6、vector(1024)、HNSW：PASS。
- 真实 LLM `qwen2.5:3b-instruct` 与中文 Embedding `qwen3-embedding:0.6b`：PASS。
- 真实 Web/API/RAG：营养 A-only、平台 C-only、越界守卫：PASS。
- 档案、S0/S1/S2/S3、候选过滤、输出声明和逐结论门禁：PASS。
- 375/768/1440：无横向溢出，控制台 0 error / 0 warning。

## 问题与行动复核

- `ISSUE-007`：修复和后续验证早已完成但状态仍为 open；本轮纠正为 resolved。
- `ISSUE-047`：原主追踪矩阵只有计划态、没有实际状态和同 scope 证据；已增加 P05 实测快照和状态定义。
- `ISSUE-048`：ENG-03 缺用户主动停止生成；登记 `ACTION-08`，由 P07-05 完成，阻断最终验收但不阻断 Phase 05 本地退出。
- `ISSUE-009`：Windows 沙箱偶发拒绝创建 PowerShell 子进程，本轮复发；项目脚本经获批前缀完成同 scope 验证，仍为非最终阻断环境问题。
- `ISSUE-014`：ESLint 9 兼容固定，等待插件链支持 10；Lint/Build 全绿，非最终阻断。
- `ISSUE-017`：内置浏览器元数据问题仍在；Playwright 等价三视口验证全绿，非最终阻断。
- `ACTION-05`：Render 区域、预算、七天可用性仍需用户授权，留到 P08-02/06。
- `ACTION-06`：80 条事实第二人复核仍需独立人员，继续阻断最终知识签署。

## 沉淀候选

1. 需求追踪矩阵必须同时给出当前实测状态和后续门；只有“计划实现/计划证据”不能作为阶段门禁。
2. 最新 PASS 只能关闭同 scope 的旧失败，项目工具或其他视口的 PASS 不能互相覆盖。
3. 本地完成、公网部署和七天可用性应拆分判定，避免用 Compose 通过替代公开 URL 事实。
