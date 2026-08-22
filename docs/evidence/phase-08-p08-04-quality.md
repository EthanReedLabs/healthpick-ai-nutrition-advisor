# P08-04 演示资产与双次连续演练

## 结论

P08-04 以 `PASS WITH ACTION` 完成。六分钟脚本、运行手册、评委问答和资产索引齐全；同一隔离 Compose 候选在不改配置的情况下连续完成 rehearsal-01/02。两次均通过营养/平台/混合来源边界、S3 安全会话、三轮历史、72/80 评测摘要和 ACTION-06 推荐复核门，并清理临时会话。

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

## 演示资产

- `docs/demo/DEMO_SCRIPT_6MIN.md`
- `docs/demo/DEMO_RUNBOOK.md`
- `docs/demo/JUDGE_QA.md`
- `docs/demo/ASSET_INDEX.md`
- P06/P07 真实桌面、移动、评测、停止生成和数据删除截图
- `scripts/run_demo_rehearsal.py`

## 问题与解决

- ISSUE-070：首轮演练误把 S3 设计理解为“完全不持久化”，并与正常三轮共用会话。实际产品会清空该会话生成上下文、保留一条 `context_eligible=false` 安全记录。演练改为独立安全会话并校验主会话三轮保持与安全轮不可进入生成上下文，连续两次通过。

## 保留行动

- ACTION-05：公网 URL 镜头、HTTPS 和提交时段可用性尚未演练。
- ACTION-06：推荐规则第二人复核未完成，演示只能展示诚实 review gate，不能展示伪造个性化方案。
- 最终视频文件和提交回执属于人工最终提交资产，当前索引明确标为尚未生成。

## 沉淀候选

医疗安全“不可进入生成上下文”和“是否保留可见审计记录”是两个不同契约；演示脚本必须与产品的历史语义一致，S3 应使用独立会话，避免安全动作意外清除正常演示上下文。
