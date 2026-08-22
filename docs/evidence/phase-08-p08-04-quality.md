# P08-04 演示资产与双次连续演练

## 结论

P08-04 以 `PASS` 完成。六分钟脚本、运行手册、评委问答和资产索引齐全；原有同一隔离 Compose 候选连续完成 rehearsal-01/02，最终 RC8 又在公网完成真实千问、推荐、引用、恢复与 S3 演示。ACTION-05/06 均已关闭，最终录像和截图已经生成并固定哈希。

## 双次结果

| 检查 | Run 01 | Run 02 |
|---|---:|---:|
| Web/API/真实 LLM/PostgreSQL | PASS | PASS |
| 营养路由与 A/B 边界 | PASS | PASS |
| 平台路由与 C 边界 | PASS | PASS |
| 混合路由双域证据 | PASS | PASS |
| S3 紧急停止 | PASS | PASS |
| S3 不进入生成上下文 | PASS | PASS |
| 主演示会话三轮保持 | PASS | PASS |
| 公开评测 72/80、9/9 | PASS WITH ACTION | PASS WITH ACTION |
| 推荐第二人复核门 | ACTION-06 正确阻断 | ACTION-06 正确阻断 |
| 临时会话清理 | PASS | PASS |

最终 RC8 公网演练另见 `docs/evidence/phase-08-rc8-final-rehearsal.json`，其公开评测为 9/9 frozen gates `PASS`，事实处置为 74 verified / 6 rejected / 0 pending。

## 演示资产

- `docs/demo/DEMO_SCRIPT_6MIN.md`
- `docs/demo/DEMO_RUNBOOK.md`
- `docs/demo/JUDGE_QA.md`
- `docs/demo/ASSET_INDEX.md`
- P06/P07 真实桌面、移动、评测、停止生成和数据删除截图
- `scripts/run_demo_rehearsal.py`
- `output/playwright/final-rc8/healthpick-rc8-final-demo-6min.mp4`
- `output/playwright/final-rc8/healthpick-rc8-final-demo.webm`
- `docs/demo/assets/healthpick-rc8-final-s3.png`
- `docs/evidence/phase-08-rc8-final-demo.json`

## 问题与解决

- ISSUE-070：首轮演练误把 S3 设计理解为“完全不持久化”，并与正常三轮共用会话。实际产品会清空该会话生成上下文、保留一条 `context_eligible=false` 安全记录。演练改为独立安全会话并校验主会话三轮保持与安全轮不可进入生成上下文，连续两次通过。

## 最终资产说明

- 完整录像 8分17.84秒，保留全部实际等待与恢复过程。
- 六分钟提交版 5分55.64秒，仅做统一 1.4× 时间压缩，没有剪接、替换或 Mock。
- 比赛平台回执必须在实际外部提交后取得，当前不伪造。

## 沉淀候选

医疗安全“不可进入生成上下文”和“是否保留可见审计记录”是两个不同契约；演示脚本必须与产品的历史语义一致，S3 应使用独立会话，避免安全动作意外清除正常演示上下文。
