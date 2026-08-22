# 最终总纲验收

## 1. 使用时机

Phase 08 的实现、部署、文档和演示资产完成后执行。它不是阶段总结，而是对中心注册表、逐任务记录、真实运行证据和 Release 候选的反向审计。

最终验收对象必须冻结为同一个 scope：

- release commit 和 tag；
- Web/API 构建版本；
- 数据库 migration 版本；
- A/B/C source hash 和知识产物版本；
- LLM/Embedding provider、model 和配置；
- 公网环境与本地 Compose 环境；
- 测试、截图、视频和文档对应的构建。

任一证据来自不同 commit、不同配置或过期环境，都不能覆盖当前候选版失败。

## 2. 十个最终门禁

| Gate | 验收内容 | 必须提供的客观证据 | 失败条件 |
|---|---|---|---|
| FINAL-01 | 注册范围内全部任务关闭 | 控制面 JSON；required task 全为 passed | 存在 TODO/READY/DOING/BLOCKED/PASS WITH ACTION |
| FINAL-02 | 所有完成记录已复核 | 每个 `control/records/*.yaml` 为 accepted | 缺记录、缺审阅人或仍 pending |
| FINAL-03 | P0/P1 需求无遗漏 | 追踪矩阵逐项代码、测试、证据链接 | 任一必做需求缺 owner/实现/测试/证据 |
| FINAL-04 | 知识与医疗安全 | 黄金集、串库集、引用、禁忌和免责声明报告 | C 串入推荐、编造数字、高风险漏提示 |
| FINAL-05 | 工程质量与隐私 | lint/typecheck/unit/API/RAG/E2E/安全/Secret 报告 | 未处理失败、真实密钥、跨用户越权 |
| FINAL-06 | 双部署可复现 | 公网 HTTPS probe；干净环境 Compose 录屏/日志 | URL 不可用或 15 分钟无法复现 |
| FINAL-07 | 文档和演示完整 | README、架构、测试、AI 披露、视频、截图 | 字数/内容不足或演示不是实际系统 |
| FINAL-08 | Release 一致性 | commit、tag、构建 hash、远端干净克隆日志（公开仓库匿名、私有仓库只读授权） | 证据不是同一 release scope |
| FINAL-09 | 七天可用性 | 到期时间、Owner、监测与故障预案 | 无责任人、资源将在要求前失效 |
| FINAL-10 | 最终签署 | Project Lead 签字、时间、无开放阻断 | 任一前置 Gate 未通过 |

## 3. 最终执行顺序

1. 功能冻结并创建 release candidate；
2. 从干净环境检出候选 commit；
3. 执行依赖安装、migration、seed、构建和全测试；
4. 在本地 Compose 与公网分别执行同一套 10 条核心场景；
5. 运行 Secret、权限、输入边界、知识串库和安全回归；
6. 复核全部任务记录和已解决问题的后续成功证据；
7. 逐项填写 FINAL-01～10 的证据；
8. 写入 release commit/tag/URL/Compose probe；
9. 运行 `scripts/control_plane.py --check-final`；
10. 机器结果 READY 后，Project Lead 才能签署 FINAL-10。

## 4. 总纲签署模板

```text
Release commit:
Release tag:
Public URL:
Compose probe evidence:
Knowledge manifest hash:
Full test report:
Open required tasks: 0
Open actions: 0
Open final-blocking issues: 0
Pending task-record reviews: 0
Final gates passed: 10/10
Decision: ACCEPTED / REJECTED
Project Lead:
Signed at:
Notes:
```

最终结果只能是 `ACCEPTED` 或 `REJECTED`。若证据不足，控制面保持 `NOT_READY`，等价于不能验收，不使用“有条件接受”绕过未完成任务。
