# 项目统一控制面使用规则

## 1. 唯一真值

`control/project-control.yaml` 是 Phase 01～08 的唯一任务状态真值。README、阶段计划、聊天记录和人工看板只能引用它，不得在其他文件建立一套相互独立的状态。

控制面管理六类对象：

1. 阶段：Phase 01～08 和阶段退出记录；
2. 任务：Owner、优先级、依赖、状态、证据和完成记录；
3. 行动：允许 `PASS WITH ACTION` 的限时残余工作；
4. 问题：发现时间、现象、原因、解决方式、证据和是否阻断最终验收；
5. 最终门禁：总纲验收必须逐项通过的 10 个 Gate；
6. Release：commit、tag、公网 URL、Compose probe 和最终签署。

可读视图由审计器生成：[统一控制板](CONTROL_BOARD.md)和[问题解决日志](ISSUE_LOG.md)。生成文件不是状态真值，不得手工修改。

## 2. 状态机

任务只允许按下列路径流转：

```text
not_started → ready → in_progress ─┬→ passed
                                  ├→ pass_with_action → in_progress → passed
                                  └→ blocked → in_progress
```

- `passed`：实现、测试、证据和任务记录均完整，不存在残余行动；
- `pass_with_action`：当前范围可以继续，但必须绑定仍开放的 ACTION；最终验收把它视为未完成；
- `blocked`：当前任务不能继续，必须绑定问题或外部依赖；
- `deferred`：只能用于经 Project Lead 批准的非必做任务，必做任务不得用它逃避验收；
- 禁止“基本完成”“应该可以”“代码写完”等模糊状态。

阶段状态由其任务状态自动推导，不应凭主观手工宣布。任何 `pass_with_action` 都会让阶段保持同名状态，直到残余行动关闭并重新运行证据。

## 3. 每个任务的执行闭环

### 开始前

1. 在注册表确认任务 ID、Owner、依赖、验收和证据路径；
2. 依赖未满足时不得把任务标记 `in_progress`，允许 Mock/降级时需在任务说明中明确范围；
3. 将任务改为 `in_progress`，记录真实开始时间。

### 执行中

1. 发现异常立即新增 `ISSUE-nnn`，先记录现象，不把猜测写成原因；
2. 问题若需要跨任务或外部处理，新增 `ACTION-nn` 并设置 Owner、截止点和阻断对象；
3. 解决后保留原失败，填写 root cause、resolution 和更晚的同范围成功证据；
4. 不删除失败记录，不用不同环境/配置的 PASS 覆盖本轮失败。

### 完成时

1. 从 `control/templates/task-record.yaml` 创建 `control/records/<TASK-ID>.yaml`；
2. 填写实际开始/完成时间、交付物、逐条验收、关联问题、残余行动；
3. `passed` 必须有至少一项客观证据且 residual_actions 为空；
4. 只能继续但仍有外部工作时使用 `pass_with_action`；
5. 更新中心注册表并运行控制面审计；
6. 阶段最后一个 Gate 关闭时，再生成阶段退出记录。

任务记录的 `review.status` 初始为 `pending_final_review`。最终总纲验收时 Project Lead 逐项查看证据后改为 `accepted`；这防止开发者自报完成直接变成最终签署。

## 4. 审计命令

日常结构与证据审计：

```powershell
.\.venv\Scripts\python.exe scripts\control_plane.py
```

它会生成：

- `docs/governance/CONTROL_BOARD.md`；
- `docs/governance/ISSUE_LOG.md`；
- `docs/evidence/control-plane-validation.json`；
- `docs/evidence/control-plane-validation.md`。

最终发布门禁：

```powershell
.\.venv\Scripts\python.exe scripts\control_plane.py --check-final
```

只要存在以下任一情况，最终命令必须非零退出：

- 任一 required 任务不是 `passed`；
- 任一任务记录尚未被 Project Lead 接受；
- 任一 ACTION 未关闭或豁免；
- 任一阻断最终验收的问题未解决；
- 任一 FINAL Gate 未通过；
- release commit/tag/URL/Compose probe/最终签署缺失；
- Schema、依赖、记录或证据路径校验失败。

## 5. 变更控制

- 新需求必须先新增 Task ID，再开始代码；
- 不得删除已有任务。取消任务使用 `deferred`，并记录替代项、原因、对 P0 的影响和 Project Lead 批准；
- 任务拆分时保留原 ID 作为父任务，新任务声明依赖；
- 交付物路径变化必须同步更新任务和完成记录；
- 证据失效、过期或 scope 改变时，任务应从 `passed` 退回 `in_progress`，重新产生证据；
- 最终功能冻结后只允许修复已登记的问题，不新增未经审批的功能。

## 6. 最终判定原则

状态字段只是判定结果，不是发布事实。最终验收必须回答：哪个 build/commit、哪个环境和配置、何时运行、由哪个证据证明了什么。回答不出来时判定为 `NOT_READY`，不得默认通过。

