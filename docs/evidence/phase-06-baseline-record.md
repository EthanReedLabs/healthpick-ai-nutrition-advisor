# Phase 06 退出验收记录

## 结论

Phase 06 以 `PASS WITH ACTION` 退出，允许进入 Phase 07。P06-01～P06-04 均为 `passed`，账号迁移、历史管理、运行透明度、检索 Trace 和用户数据权利已完成；最终提交仍为 `NOT_READY`。

## 任务验收

| 任务 | 结果 | 核心证据 |
|---|---:|---|
| P06-01 匿名身份账号与迁移 | PASS | `control/records/P06-01.yaml`、10 项专项、真实 PostgreSQL |
| P06-02 历史搜索改名删除 | PASS | `control/records/P06-02.yaml`、刷新恢复、桌面/移动浏览器 |
| P06-03 来源透明与检索 Trace | PASS | `control/records/P06-03.yaml`、动态透明接口、真实 Trace |
| P06-04 用户数据导出删除 | PASS | `control/records/P06-04.yaml`、同数据面 21 项 PostgreSQL、真实下载删除 |

## 退出门逐项判定

1. P06-01～P06-04 独立记录、实现、问题和验收证据齐全：PASS。
2. 匿名历史可原子接管账号，所有受保护接口集中校验归属，跨账号拒绝：PASS。
3. 历史搜索、改名、删除在桌面/移动共享服务端真值，刷新后恢复：PASS。
4. 当前模型、Embedding、检索、存储和 A/B/C 边界由运行配置动态公开；Trace 与最终引用 ID 完全一致：PASS。
5. 账号导出计数与永久删除覆盖 `users / auth_sessions / anonymous_sessions / conversations / conversation_turns`；秘密字段排除、静态知识保留：PASS。
6. Python 全仓 201/201、Web 27/27、Ruff、格式、TypeScript、ESLint、production build：PASS。
7. 真实本地栈 12:06 复验：LLM/Embedding real、PostgreSQL、营养/平台/越界三路径、Trace/evidence gate：PASS。
8. 控制面阶段内审：`structural_status=PASS`、`errors=0`；`final_readiness=NOT_READY` 符合当前阶段。

## 本阶段问题闭环

- 新增 ISSUE-049～056，全部 `resolved`；其中账号授权边界、公开路由枚举、启动配置漂移、用户 ID 类型边界均已增加自动或真实运行回归。
- ISSUE-054 形成项目级 `tools/start_local_api.ps1`，只设置子进程配置，不修改全局环境。
- 沉淀候选：个人数据的计数、导出与删除必须覆盖同一数据面，并以删除后归零和静态数据保留配对验收。

## 保留行动与影响

- `ACTION-05` / `ISSUE-005`：Render 区域、预算与七天可用性授权，仅阻断 Phase 08 公网与最终验收。
- `ACTION-06`：80 条结构化事实第二人复核，阻断最终知识准确性签署。
- `ACTION-08` / `ISSUE-048`：用户主动停止生成由 P07-05 关闭，当前仍阻断最终体验验收。
- `ISSUE-009`、`ISSUE-014`、`ISSUE-017` 为已知非最终阻断环境/工具兼容记录，本阶段门均有等价真实证据。

## Phase 07 进入条件

- P07-01 优先构建黄金、医疗安全、来源隔离、平台与多轮串库评测集，并冻结机器可判定字段。
- P07-02 必须运行真实模型评测并达到预先冻结阈值；不得在看到结果后降低阈值。
- P07-03 与 P07-05 可在评测执行期间推进主备故障演练和停止生成；P07-04 只展示真实评测产物。
- 每项继续写独立 record、问题与证据，P07-06 执行功能冻结。

## 最终总纲状态

本记录只签署 Phase 06。最终总纲仍由 P08-07 重新解析全部任务记录、开放问题、评测、公网、文档、演示、release tag 与七天可用性证据后签署。
