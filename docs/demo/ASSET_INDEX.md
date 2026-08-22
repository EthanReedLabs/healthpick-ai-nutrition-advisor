# 演示资产索引

## 最终候选

- 公网地址：`https://106.14.13.139`
- Release：`v0.1.0-rc8` / `6e56b96f7d5ac4ffd306cdcedabfac7366034f44`
- 六分钟提交版：`output/playwright/final-rc8/healthpick-rc8-final-demo-6min.mp4`（5:55.64，1.4× 等速压缩，无剪接、无替换、无 Mock）
- 完整证据版：`output/playwright/final-rc8/healthpick-rc8-final-demo.webm`（8:17.84，Playwright 原始录制）
- 最终 S3 截图：`docs/demo/assets/healthpick-rc8-final-s3.png`
- 资产哈希与覆盖场景：`docs/evidence/phase-08-rc8-final-demo.json`

## 脚本与操作

- 六分钟脚本：`docs/demo/DEMO_SCRIPT_6MIN.md`
- 运行手册：`docs/demo/DEMO_RUNBOOK.md`
- 评委问答：`docs/demo/JUDGE_QA.md`
- 自动演练：`scripts/run_demo_rehearsal.py`

## 产品截图

- 评测卡：`output/playwright/phase-07-p07-04-evaluation-card.png`
- 桌面总览：`output/playwright/phase-07-p07-04-desktop.png`
- 生成中停止按钮：`output/playwright/phase-07-p07-05-generating.png`
- 停止后桌面：`output/playwright/phase-07-p07-05-stopped.png`
- 停止后移动：`output/playwright/phase-07-p07-05-stopped-mobile.png`
- 历史搜索桌面/移动：`output/playwright/phase-06-p06-02-history-search-1440x1000.png`、`output/playwright/phase-06-p06-02-history-search-375x812.png`
- 账号导出删除：`output/playwright/phase-06-p06-04-account-export-delete.png`
- RC8 最终 S3 急症阻断：`docs/demo/assets/healthpick-rc8-final-s3.png`

## 机器证据

- RC8 真实评测：`evals/reports/release-v1-20260822T200205387257+0800/summary.json`（9/9 frozen gates PASS）
- 事实全量复核：`docs/evidence/action-06-full-structured-fact-review.json`（74 verified / 6 rejected / 0 pending）
- RC8 公网部署：`docs/evidence/phase-08-rc8-final-deployment.json`
- RC8 公网演练：`docs/evidence/phase-08-rc8-final-rehearsal.json`
- RC8 最终录像：`docs/evidence/phase-08-rc8-final-demo.json`
- Compose：`docs/evidence/phase-08-p08-02-compose.json`
- 密钥/依赖：`docs/evidence/phase-08-p08-01-quality.md`
- 双次演练：`docs/evidence/phase-08-p08-04-rehearsal-01.json`、`phase-08-p08-04-rehearsal-02.json`

## 外部提交边界

- 公网截图、最终录屏和仓库内提交资产已经生成。
- 比赛平台上传与回执只能在实际提交后取得；当前不伪造回执，也不把未授权的外部提交通道当作项目验收阻断。
