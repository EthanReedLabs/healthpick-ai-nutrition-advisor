# P05-05 P0 需求追踪与回归快照

## 判定口径

- `PASS_CURRENT`：当前实现、自动测试和同 scope 运行证据齐全；发布冻结时仍需复跑。
- `PARTIAL_MAPPED`：本地部分已通过，剩余发布、人工或体验门已绑定控制面任务/行动。
- `OPEN_MAPPED`：尚未实施，但有明确任务、负责人和最终阻断关系。
- 本表是 `docs/01-requirements-traceability.md` 在 2026-08-22 10:34 的实测快照；控制面仍是唯一任务状态真值。

## 基础功能 P0

| ID | 状态 | 实现/任务 | 最新测试与运行证据 | 剩余门 |
|---|---|---|---|---|
| KB-01 | PASS_CURRENT | DATA-01～06；A/B=`core_nutrition` | `phase-02-knowledge-validation.json`、`local-real-stack-runtime.json` | 发布复跑 |
| KB-02 | PASS_CURRENT | DATA-04/06；C=`auxiliary_platform` | 平台真实问答 sources=`C` | 发布复跑 |
| KB-03 | PARTIAL_MAPPED | 结构化事实 + P04-06 自动 golden | `phase-04-p04-06-golden.json`、193/193 | ACTION-06 第二人复核；P07-01/02 完整评测 |
| KB-04 | PASS_CURRENT | P03-04 引用对象与逐结论门禁 | `phase-03-citation-runtime.json`、P05 三档截图 | 发布复跑 |
| KB-05 | PASS_CURRENT | P03-04/P04-04 fail-closed 与确定性回退 | `phase-04-p04-04-runtime.json` 10:34 PASS | P07 对抗集扩展 |
| KB-06 | PASS_CURRENT | P03-03 数据库硬过滤与路由隔离 | 营养 sources=`A`、平台 sources=`C` | P07 串库集扩展 |
| MEM-01 | PASS_CURRENT | P04-01/05 + P05-01 档案和消息上下文 | `phase-05-p05-01-postgres.json`、安全 smoke | 发布复跑 |
| MEM-02 | PASS_CURRENT | P05-01 服务端多轮持久化 | P05-01 API/Web/浏览器证据 | P07 多轮集扩展 |
| MEM-03 | PASS_CURRENT | P05-01 CRUD；P05-03 UI 列表/切换/删除 | `phase-05-p05-03-browser.md`、23/23 | P06-02 搜索/重命名体验增强 |
| REC-01 | PASS_CURRENT | P04-02 确定性候选和解释 | `phase-04-p04-02-runtime.json` | P07 完整评测 |
| REC-02 | PASS_CURRENT | P04-02 来源约束，P04-03 硬过滤 | P04 runtime/golden | 发布复跑 |
| REC-03 | PASS_CURRENT | 主/备推荐结构与方案卡 | P04-02 API、P04-05 浏览器 | 发布复跑 |
| REC-04 | PASS_CURRENT | P04-03 禁忌规则与候选过滤 | 10:34 S0/S1/S2/S3 smoke | P07 完整安全集 |
| REC-05 | PASS_CURRENT | P04-04 风险级免责声明 | 10:34 output safety smoke | 发布复跑 |
| ENG-01 | PARTIAL_MAPPED | 本地 Compose P05-04 PASS | `phase-05-p05-04-compose.json`、DB 10:33 PASS | P08-02 公网 HTTPS；P08-06 七天可用 |
| ENG-02 | PASS_CURRENT | P03-06/P04-05/P05-03 响应式界面 | 375/768/1440、0 overflow | 发布复跑 |
| ENG-03 | PARTIAL_MAPPED | 加载/成功/清空已完成 | P05-03 23/23、浏览器状态证据 | ACTION-08 / P07-05 增加用户主动停止 |
| ENG-04 | PASS_CURRENT | P05-02 统一错误和动作级恢复 | 504 同请求 ID 重试、错误契约 | 发布复跑 |
| ENG-05 | PASS_CURRENT | P05-02 请求边界/超时/中断 | P05-02 API/Web 与 193/193 | 发布复跑 |
| DOC-01 | PASS_CURRENT | `README.md` 3721 字符 | 只读字符检查 | P08-03 最终冻结 |
| DOC-02 | PASS_CURRENT | `docs/02-architecture.md` + ADR | 文件 >200 字 | P08-03 最终冻结 |
| DOC-03 | PASS_CURRENT | 架构/RAG/异常/Prompt 文档 | `02-architecture.md`、`03-rag-and-knowledge.md` | P08-03 最终冻结 |
| DOC-04 | PASS_CURRENT | 自动与运行报告远超 5 组 | Python 193/193、Web 23/23、6 类 runtime | P08-01 最终回归 |

## 工程与提交 P0

| ID | 状态 | 实现/任务 | 最新测试与运行证据 | 剩余门 |
|---|---|---|---|---|
| LLM-01 | PASS_CURRENT | Provider adapter + RAG + 输出门禁 | 10:33 真实 `qwen2.5:3b-instruct`，动态哈希 | P07-03 主备演练 |
| DEP-02 | PASS_CURRENT | P05-04 五服务 Compose/migrate/seed | 空库、幂等 seed、重启保留 PASS | P08-02 匿名干净环境复现 |
| DEP-03 | PARTIAL_MAPPED | P01-04 `.env.example`、Compose 命名空间 | 配置校验与生产构建 PASS | P08-01 正式 secret scan |
| CON-01 | PASS_CURRENT | 主计划、任务控制面与阶段记录 | Phase 01～05 时间戳和任务记录 | 最终总纲复核 |
| CON-02 | PARTIAL_MAPPED | Git remote ACTION-04 已关闭 | `action-04-git-remote-runtime.json` | P08-05 release tag/匿名克隆 |
| CON-03 | PASS_CURRENT | 自研 UI、RAG、规则、评测和部署 | 代码、架构、测试链 | 最终提交复核 |
| CON-04 | PASS_CURRENT | `docs/AI_USAGE.md` | 文件 2674 字节、模块披露 | P08-03 最终更新 |
| CON-05 | PASS_CURRENT | manifest/source_role/串库测试 | Phase 02 验证 + 10:33 real smoke | P07-02 冻结阈值 |
| CON-06 | PASS_CURRENT | 风险级统一免责声明 | 10:34 五路径 output safety PASS | P08-01 复跑 |
| CON-07 | PARTIAL_MAPPED | env 注入、gitignore、日志脱敏 | P05 配置与测试 PASS | P08-01 正式密钥扫描 |
| CON-08 | OPEN_MAPPED | P08-06 七天可用性责任与监测 | 尚无公网时间序列证据 | ISSUE-005/ACTION-05/P08-02/06 |

## 汇总与门禁

- P0 总数：34。
- `PASS_CURRENT`：27。
- `PARTIAL_MAPPED`：6（KB-03、ENG-01、ENG-03、DEP-03、CON-02、CON-07）。
- `OPEN_MAPPED`：1（CON-08）。
- 未解释空项：0。
- Phase 05 本地 P0：达到退出条件。
- 最终提交：仍为 `NOT_READY`；ACTION-05、ACTION-06、ACTION-08 和 Phase 06～08 任务不得被本表覆盖。

## 本轮最新回归

| 检查 | 结果 | 时间/证据 |
|---|---:|---|
| Python 全量 | 193/193 PASS | `phase-05-p05-05-pytest.xml` |
| Ruff / format | PASS / 141 files | 2026-08-22 10:32 |
| Web 全量 | 23/23 PASS | `phase-05-p05-05-web-vitest.xml` |
| ESLint / TypeScript / production build | PASS | 2026-08-22 10:32 |
| PostgreSQL/pgvector | PASS | `phase-05-p05-05-database-runtime.json` 10:33 |
| 真实 LLM/Embedding | PASS | `action-02-03-real-model-runtime.json` 10:33 |
| 真实 Web/API/RAG | PASS | `local-real-stack-runtime.json` 10:33 |
| 档案/风险/输出安全 | PASS | P04 三份 runtime 10:34 |
| 三视口/控制台 | PASS | `phase-05-p05-03-browser.md` |
