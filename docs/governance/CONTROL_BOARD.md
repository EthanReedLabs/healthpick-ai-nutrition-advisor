# 项目统一控制板

> 本文件由 `scripts/control_plane.py` 从 `control/project-control.yaml` 生成；请勿手工修改状态。

- 结构校验：`PASS`
- 最终验收就绪度：`NOT_READY`
- 当前阶段：`PHASE-04`
- 最近审计：`2026-08-21T19:48:05.935699+08:00`

## 阶段

| Phase | 名称 | 状态 | 退出记录 |
|---|---|---|---|
| PHASE-01 | 基线与范围冻结 | `pass_with_action` | docs/evidence/phase-01-baseline-record.md |
| PHASE-02 | 知识数据生产化 | `pass_with_action` | docs/evidence/phase-02-baseline-record.md |
| PHASE-03 | 最薄动态问答闭环 | `pass_with_action` | docs/evidence/phase-03-baseline-record.md |
| PHASE-04 | 推荐与医疗安全 | `ready` | — |
| PHASE-05 | P0 完整与本地部署 | `not_started` | — |
| PHASE-06 | P1 产品化能力 | `not_started` | — |
| PHASE-07 | 评测冲分与功能冻结 | `not_started` | — |
| PHASE-08 | 发布演示与最终验收 | `not_started` | — |

## 当前可开始任务

- `P04-01` 健康档案与约束模型（Owner: API/WEB）

## 全部任务

| Phase | Task | 任务 | Owner | 状态 | 完成记录 |
|---|---|---|---|---|---|
| PHASE-01 | P01-01 | 冻结需求范围与追踪矩阵 | LEAD | `passed` | control/records/P01-01.yaml |
| PHASE-01 | P01-02 | 冻结技术与部署决策 | LEAD/API | `passed` | control/records/P01-02.yaml |
| PHASE-01 | P01-03 | 建立来源与角色基线 | KNOWLEDGE | `passed` | control/records/P01-03.yaml |
| PHASE-01 | P01-04 | 建立环境变量契约 | DEVOPS/API | `passed` | control/records/P01-04.yaml |
| PHASE-01 | P01-05 | 建立仓库与行尾策略 | DEVOPS | `passed` | control/records/P01-05.yaml |
| PHASE-01 | P01-06 | 冻结最小 API 契约 | WEB/API | `passed` | control/records/P01-06.yaml |
| PHASE-01 | P01-07 | 冻结风险触发器与降级路径 | LEAD | `passed` | control/records/P01-07.yaml |
| PHASE-01 | P01-08 | 执行 Phase 01 退出验收 | LEAD | `pass_with_action` | control/records/P01-08.yaml |
| PHASE-01 | P01-09 | 建立 Phase 02 READY 任务板 | LEAD | `passed` | control/records/P01-09.yaml |
| PHASE-02 | DATA-01 | 页级解析与视觉核对 | KNOWLEDGE | `passed` | control/records/DATA-01.yaml |
| PHASE-02 | DATA-02 | 生成稳定页内 Chunk | KNOWLEDGE/API | `passed` | control/records/DATA-02.yaml |
| PHASE-02 | DATA-03 | 生成 A/B 结构化事实 | KNOWLEDGE | `pass_with_action` | control/records/DATA-03.yaml |
| PHASE-02 | DATA-04 | 生成 C 平台事实并隔离 | KNOWLEDGE | `pass_with_action` | control/records/DATA-04.yaml |
| PHASE-02 | DATA-05 | 建立知识 Schema 与 migration | API | `pass_with_action` | control/records/DATA-05.yaml |
| PHASE-02 | DATA-06 | 执行导入与隔离 smoke | API/QA_DOCS | `pass_with_action` | control/records/DATA-06.yaml |
| PHASE-03 | GOV-01 | 建立统一任务控制面与最终验收门禁 | LEAD/QA_DOCS | `passed` | control/records/GOV-01.yaml |
| PHASE-03 | P03-01 | FastAPI 骨架健康检查与 OpenAPI | API | `passed` | control/records/P03-01.yaml |
| PHASE-03 | P03-02 | LLM Provider 适配与真实或 Mock 调用 | API | `passed` | control/records/P03-02.yaml |
| PHASE-03 | P03-03 | A/B/C 路由与检索适配 | API/KNOWLEDGE | `pass_with_action` | control/records/P03-03.yaml |
| PHASE-03 | P03-04 | 引用生成与证据校验 | API | `pass_with_action` | control/records/P03-04.yaml |
| PHASE-03 | P03-05 | 会话与 SSE Chat API | API | `pass_with_action` | control/records/P03-05.yaml |
| PHASE-03 | P03-06 | Next.js 聊天与引用界面骨架 | WEB | `passed` | control/records/P03-06.yaml |
| PHASE-03 | P03-07 | 浏览器动态问答最薄闭环 | WEB/API/QA_DOCS | `pass_with_action` | control/records/P03-07.yaml |
| PHASE-03 | P03-08 | Phase 03 退出验收 | LEAD | `pass_with_action` | control/records/P03-08.yaml |
| PHASE-04 | P04-01 | 健康档案与约束模型 | API/WEB | `ready` | — |
| PHASE-04 | P04-02 | 确定性推荐候选与方案解释 | API/KNOWLEDGE | `not_started` | — |
| PHASE-04 | P04-03 | 禁忌硬过滤与风险分级 | API/KNOWLEDGE | `not_started` | — |
| PHASE-04 | P04-04 | 输出校验拒答与免责声明 | API | `not_started` | — |
| PHASE-04 | P04-05 | 方案卡片与安全提示 UI | WEB | `not_started` | — |
| PHASE-04 | P04-06 | 推荐安全黄金集与 API 测试 | QA_DOCS | `not_started` | — |
| PHASE-04 | P04-07 | Phase 04 退出验收 | LEAD | `not_started` | — |
| PHASE-05 | P05-01 | 多轮记忆与会话持久化 CRUD | API/WEB | `not_started` | — |
| PHASE-05 | P05-02 | 输入边界统一错误与超时处理 | API/WEB | `not_started` | — |
| PHASE-05 | P05-03 | 三档响应式与交互状态完成 | WEB | `not_started` | — |
| PHASE-05 | P05-04 | Docker Compose 数据库迁移与 seed | DEVOPS/API | `not_started` | — |
| PHASE-05 | P05-05 | 全部 P0 追踪矩阵与回归闭环 | QA_DOCS | `not_started` | — |
| PHASE-05 | P05-06 | Phase 05 退出验收 | LEAD | `not_started` | — |
| PHASE-06 | P06-01 | 匿名身份账号与数据迁移 | API/WEB | `not_started` | — |
| PHASE-06 | P06-02 | 历史搜索重命名删除体验 | API/WEB | `not_started` | — |
| PHASE-06 | P06-03 | 来源透明页模型信息与检索 trace | API/WEB | `not_started` | — |
| PHASE-06 | P06-04 | 用户数据导出与删除 | API/WEB | `not_started` | — |
| PHASE-06 | P06-05 | Phase 06 退出验收 | LEAD | `not_started` | — |
| PHASE-07 | P07-01 | 构建完整黄金安全串库评测集 | QA_DOCS/KNOWLEDGE | `not_started` | — |
| PHASE-07 | P07-02 | 运行评测并达到冻结阈值 | QA_DOCS | `not_started` | — |
| PHASE-07 | P07-03 | 主备模型切换与故障演练 | API/DEVOPS | `not_started` | — |
| PHASE-07 | P07-04 | 评测概览与透明度展示 | WEB | `not_started` | — |
| PHASE-07 | P07-05 | 关键体验与可访问性打磨 | WEB/QA_DOCS | `not_started` | — |
| PHASE-07 | P07-06 | 功能冻结与 Phase 07 验收 | LEAD | `not_started` | — |
| PHASE-08 | P08-01 | 全回归性能安全与密钥扫描 | QA_DOCS/DEVOPS | `not_started` | — |
| PHASE-08 | P08-02 | 公网部署与 Compose 干净环境复现 | DEVOPS | `not_started` | — |
| PHASE-08 | P08-03 | 文档 AI 披露许可证与隐私冻结 | QA_DOCS/LEAD | `not_started` | — |
| PHASE-08 | P08-04 | 演示资产与双次连续演练 | LEAD/QA_DOCS | `not_started` | — |
| PHASE-08 | P08-05 | Release tag 匿名克隆与提交候选冻结 | DEVOPS/LEAD | `not_started` | — |
| PHASE-08 | P08-06 | 公网七天可用性责任与监测 | DEVOPS/LEAD | `not_started` | — |
| PHASE-08 | P08-07 | 执行最终总纲验收并签署 | LEAD | `not_started` | — |

## 开放行动

| ID | 行动 | Owner | 截止 | 阻断 |
|---|---|---|---|---|
| ACTION-01 | Docker/PostgreSQL/pgvector 运行态恢复 | DEVOPS/LEAD | T+12 | DATA-05, DATA-06, P05-04, P08-02 |
| ACTION-02 | LLM provider/model/quota smoke | API/LEAD | T+6 | P03-02, P03-07 |
| ACTION-03 | Embedding model/dimensions/中文 smoke | API/LEAD | T+6 | DATA-05, DATA-06, P03-03 |
| ACTION-04 | 建立远端 Git 仓库及最小权限 | DEVOPS/LEAD | T+12 | P08-02, P08-05 |
| ACTION-05 | Render 区域预算与七天可用性确认 | DEVOPS/LEAD | T+12 | P08-02, P08-06 |
| ACTION-06 | 80 条结构化事实第二人逐条复核 | KNOWLEDGE/LEAD | T+12 | DATA-03, DATA-04, DATA-06, P04-02 |
| ACTION-07 | 取得缺字符号修正版来源或维持排除 | LEAD | T+18 | DATA-03, P04-02 |

## 未关闭问题

| ID | 状态 | 严重度 | 现象 | 后续行动 |
|---|---|---|---|---|
| ISSUE-001 | `open` | high | 本机没有 Docker 和 psql，数据库与 pgvector 无法运行验收。 | ACTION-01 |
| ISSUE-002 | `open` | high | 未配置真实 LLM provider/model/quota，无法证明动态模型闭环。 | ACTION-02 |
| ISSUE-003 | `open` | high | Embedding 模型和维度未知，不能建立可信生产向量索引。 | ACTION-03 |
| ISSUE-004 | `open` | high | Git 仓库没有远端，无法完成匿名克隆和提交候选验收。 | ACTION-04 |
| ISSUE-005 | `open` | high | Render 账号、区域、预算和七天可用性尚未确认。 | ACTION-05 |
| ISSUE-006 | `mitigated` | high | A-p02、A-p04、B-p01、B-p05、B-p07、B-p08 的原始 PDF 存在缺字符号，影响 8 个 Chunk。 | ACTION-07 |
| ISSUE-007 | `open` | low | Windows 环境缺少 tzdata，ZoneInfo 生成报告时间失败。 | — |
| ISSUE-009 | `open` | low | Windows 沙箱偶发在创建 PowerShell 子进程前返回 CreateProcessAsUserW 拒绝访问，并行和后续串行调用均曾出现。 | — |
| ISSUE-014 | `open` | low | create-next-app 安装的 ESLint 9.39.5 输出版本已弃用提示。 | — |
| ISSUE-017 | `open` | low | 内置浏览器连接在页面操作前因宿主请求缺失 sandboxPolicy 元数据失败。 | — |

## 任务状态计数

- not_started: 30
- pass_with_action: 10
- passed: 14
- ready: 1

## 最终验收

当前共有 `93` 个机器判定阻断项。完整清单见 `docs/evidence/control-plane-validation.md`。

| Gate | 验收项 | 状态 |
|---|---|---|
| FINAL-01 | 注册范围内全部任务关闭且无 PASS WITH ACTION | `not_started` |
| FINAL-02 | 全部任务完成记录已复核接受 | `not_started` |
| FINAL-03 | P0/P1 需求追踪与客观证据完整 | `not_started` |
| FINAL-04 | 知识准确引用隔离与医疗安全全绿 | `not_started` |
| FINAL-05 | 自动测试回归性能安全和隐私全绿 | `not_started` |
| FINAL-06 | 公网 HTTPS 与 Compose 干净环境复现通过 | `not_started` |
| FINAL-07 | 文档 AI 披露演示和提交资产齐全 | `not_started` |
| FINAL-08 | Release commit/tag/hash/匿名克隆一致 | `not_started` |
| FINAL-09 | 七天可用性责任和监测已确认 | `not_started` |
| FINAL-10 | Project Lead 最终签署且不存在开放阻断 | `not_started` |
