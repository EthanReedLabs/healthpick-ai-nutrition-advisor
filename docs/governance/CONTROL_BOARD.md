# 项目统一控制板

> 本文件由 `scripts/control_plane.py` 从 `control/project-control.yaml` 生成；请勿手工修改状态。

- 结构校验：`PASS`
- 最终验收就绪度：`NOT_READY`
- 当前阶段：`PHASE-08`
- 最近审计：`2026-08-22T16:51:28.479483+08:00`

## 阶段

| Phase | 名称 | 状态 | 退出记录 |
|---|---|---|---|
| PHASE-01 | 基线与范围冻结 | `passed` | docs/evidence/phase-01-baseline-record.md |
| PHASE-02 | 知识数据生产化 | `pass_with_action` | docs/evidence/phase-02-baseline-record.md |
| PHASE-03 | 最薄动态问答闭环 | `pass_with_action` | docs/evidence/phase-03-baseline-record.md |
| PHASE-04 | 推荐与医疗安全 | `pass_with_action` | docs/evidence/phase-04-baseline-record.md |
| PHASE-05 | P0 完整与本地部署 | `pass_with_action` | docs/evidence/phase-05-baseline-record.md |
| PHASE-06 | P1 产品化能力 | `pass_with_action` | docs/evidence/phase-06-baseline-record.md |
| PHASE-07 | 评测冲分与功能冻结 | `pass_with_action` | docs/evidence/phase-07-baseline-record.md |
| PHASE-08 | 发布演示与最终验收 | `in_progress` | — |

## 当前可开始任务

- 无

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
| PHASE-01 | P01-08 | 执行 Phase 01 退出验收 | LEAD | `passed` | control/records/P01-08.yaml |
| PHASE-01 | P01-09 | 建立 Phase 02 READY 任务板 | LEAD | `passed` | control/records/P01-09.yaml |
| PHASE-02 | DATA-01 | 页级解析与视觉核对 | KNOWLEDGE | `passed` | control/records/DATA-01.yaml |
| PHASE-02 | DATA-02 | 生成稳定页内 Chunk | KNOWLEDGE/API | `passed` | control/records/DATA-02.yaml |
| PHASE-02 | DATA-03 | 生成 A/B 结构化事实 | KNOWLEDGE | `pass_with_action` | control/records/DATA-03.yaml |
| PHASE-02 | DATA-04 | 生成 C 平台事实并隔离 | KNOWLEDGE | `pass_with_action` | control/records/DATA-04.yaml |
| PHASE-02 | DATA-05 | 建立知识 Schema 与 migration | API | `passed` | control/records/DATA-05.yaml |
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
| PHASE-04 | P04-01 | 健康档案与约束模型 | API/WEB | `passed` | control/records/P04-01.yaml |
| PHASE-04 | P04-02 | 确定性推荐候选与方案解释 | API/KNOWLEDGE | `pass_with_action` | control/records/P04-02.yaml |
| PHASE-04 | P04-03 | 禁忌硬过滤与风险分级 | API/KNOWLEDGE | `passed` | control/records/P04-03.yaml |
| PHASE-04 | P04-04 | 输出校验拒答与免责声明 | API | `passed` | control/records/P04-04.yaml |
| PHASE-04 | P04-05 | 方案卡片与安全提示 UI | WEB | `pass_with_action` | control/records/P04-05.yaml |
| PHASE-04 | P04-06 | 推荐安全黄金集与 API 测试 | QA_DOCS | `passed` | control/records/P04-06.yaml |
| PHASE-04 | P04-07 | Phase 04 退出验收 | LEAD | `pass_with_action` | control/records/P04-07.yaml |
| PHASE-05 | P05-01 | 多轮记忆与会话持久化 CRUD | API/WEB | `passed` | control/records/P05-01.yaml |
| PHASE-05 | P05-02 | 输入边界统一错误与超时处理 | API/WEB | `passed` | control/records/P05-02.yaml |
| PHASE-05 | P05-03 | 三档响应式与交互状态完成 | WEB | `passed` | control/records/P05-03.yaml |
| PHASE-05 | P05-04 | Docker Compose 数据库迁移与 seed | DEVOPS/API | `passed` | control/records/P05-04.yaml |
| PHASE-05 | P05-05 | 全部 P0 追踪矩阵与回归闭环 | QA_DOCS | `pass_with_action` | control/records/P05-05.yaml |
| PHASE-05 | P05-06 | Phase 05 退出验收 | LEAD | `pass_with_action` | control/records/P05-06.yaml |
| PHASE-06 | P06-01 | 匿名身份账号与数据迁移 | API/WEB | `passed` | control/records/P06-01.yaml |
| PHASE-06 | P06-02 | 历史搜索重命名删除体验 | API/WEB | `passed` | control/records/P06-02.yaml |
| PHASE-06 | P06-03 | 来源透明页模型信息与检索 trace | API/WEB | `passed` | control/records/P06-03.yaml |
| PHASE-06 | P06-04 | 用户数据导出与删除 | API/WEB | `passed` | control/records/P06-04.yaml |
| PHASE-06 | P06-05 | Phase 06 退出验收 | LEAD | `pass_with_action` | control/records/P06-05.yaml |
| PHASE-07 | P07-01 | 构建完整黄金安全串库评测集 | QA_DOCS/KNOWLEDGE | `pass_with_action` | control/records/P07-01.yaml |
| PHASE-07 | P07-02 | 运行评测并达到冻结阈值 | QA_DOCS | `pass_with_action` | control/records/P07-02.yaml |
| PHASE-07 | P07-03 | 主备模型切换与故障演练 | API/DEVOPS | `passed` | control/records/P07-03.yaml |
| PHASE-07 | P07-04 | 评测概览与透明度展示 | WEB | `passed` | control/records/P07-04.yaml |
| PHASE-07 | P07-05 | 关键体验与可访问性打磨 | WEB/QA_DOCS | `passed` | control/records/P07-05.yaml |
| PHASE-07 | P07-06 | 功能冻结与 Phase 07 验收 | LEAD | `pass_with_action` | control/records/P07-06.yaml |
| PHASE-08 | P08-01 | 全回归性能安全与密钥扫描 | QA_DOCS/DEVOPS | `passed` | control/records/P08-01.yaml |
| PHASE-08 | P08-02 | 公网部署与 Compose 干净环境复现 | DEVOPS | `passed` | control/records/P08-02.yaml |
| PHASE-08 | P08-03 | 文档 AI 披露许可证与隐私冻结 | QA_DOCS/LEAD | `passed` | control/records/P08-03.yaml |
| PHASE-08 | P08-04 | 演示资产与双次连续演练 | LEAD/QA_DOCS | `pass_with_action` | control/records/P08-04.yaml |
| PHASE-08 | P08-05 | Release tag 匿名克隆与提交候选冻结 | DEVOPS/LEAD | `in_progress` | — |
| PHASE-08 | P08-06 | 公网七天可用性责任与监测 | DEVOPS/LEAD | `not_started` | — |
| PHASE-08 | P08-07 | 执行最终总纲验收并签署 | LEAD | `not_started` | — |

## 开放行动

| ID | 行动 | Owner | 截止 | 阻断 |
|---|---|---|---|---|
| ACTION-05 | ECS 七天可用性与短期 IP 证书续期监测 | DEVOPS/LEAD | Phase-08 最终验收前 | P08-06 |
| ACTION-06 | 80 条结构化事实第二人逐条复核 | KNOWLEDGE/LEAD | T+12 | DATA-03, DATA-04, DATA-06, P04-02, P04-05, P04-07 |

## 未关闭问题

| ID | 状态 | 严重度 | 现象 | 后续行动 |
|---|---|---|---|---|
| ISSUE-009 | `open` | low | Windows 沙箱偶发在创建 PowerShell 子进程前返回 CreateProcessAsUserW 拒绝访问，并行和后续串行调用均曾出现。 | — |
| ISSUE-014 | `open` | low | create-next-app 安装的 ESLint 9.39.5 输出版本已弃用提示。 | — |
| ISSUE-017 | `open` | low | 内置浏览器连接在页面操作前因宿主请求缺失 sandboxPolicy 元数据失败。 | — |

## 任务状态计数

- in_progress: 1
- not_started: 2
- pass_with_action: 18
- passed: 34

## 最终验收

当前共有 `72` 个机器判定阻断项。完整清单见 `docs/evidence/control-plane-validation.md`。

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
