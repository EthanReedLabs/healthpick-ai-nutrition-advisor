# 项目目录说明

```text
healthpick-ai-nutrition-advisor/
├─ apps/
│  ├─ web/                   # Next.js 响应式 Web、聊天、方案、历史、管理页
│  └─ api/                   # FastAPI、RAG、规则引擎、用户与会话 API
├─ packages/
│  └─ shared/                # OpenAPI 生成类型、共享枚举和契约
├─ knowledge/
│  ├─ raw/                   # 原始 PDF，只读真值，不直接编辑
│  ├─ normalized/            # 章节文本、表格 JSON/CSV、别名和规则
│  ├─ manifests/             # 来源、版本、哈希、许可和处理状态
│  ├─ schemas/               # Chunk、Citation、FoodFact、PlanRule schema
│  └─ prompts/               # 系统提示、路由、生成、校验提示
├─ evals/
│  ├─ datasets/              # 路由、问答、边界输入和多轮用例
│  ├─ golden/                # 人工确认的期望答案与引用
│  ├─ adversarial/           # 串库、提示注入、医疗越界和无关输入
│  └─ reports/               # 每次评测的 JSON/Markdown 报告
├─ infra/
│  ├─ docker/                # Web/API 镜像与 Compose 支撑文件
│  └─ migrations/            # PostgreSQL/pgvector 迁移
├─ scripts/                  # ingest、seed、eval、dev、smoke、backup
├─ control/                  # Phase 01..08 中心任务、行动、问题、记录与 Schema
├─ tools/                    # 本地分析辅助工具，不进入生产运行路径
├─ docs/
│  ├─ source/                # 原始赛题说明
│  ├─ decisions/             # ADR 技术决策
│  ├─ phases/                # Phase 01..08 独立实施手册
│  ├─ evidence/              # 截图、测试记录、演示证据
│  ├─ governance/            # 自动生成控制板、问题日志与最终验收总纲
│  └─ 00..07                 # 主方案和专项方案
├─ .github/workflows/        # lint、test、build、eval 门禁
├─ .gitignore                # 密钥、构建、缓存和报告忽略规则
├─ .env.example              # 环境变量清单，无真实值
├─ docker-compose.yml        # 实现阶段创建，可一键启动全栈
└─ README.md
```

## 管理规则

1. `knowledge/raw` 中的原始文件不可覆盖；变更资料时新增版本并更新 manifest。
2. 任何从 PDF 提取的表格必须进入 `normalized` 并完成人工复核，不能直接相信 OCR。
3. A/B 与 C 使用不同 `source_role`，检索前先做硬过滤，不依赖提示词隔离。
4. 评测数据不得与运行时会话数据混放。
5. `docs/evidence` 只保存可交付证据；临时截图和调试日志不进入此目录。
6. 所有敏感配置只通过环境变量注入，真实 `.env` 必须被 Git 忽略。
7. 任何新功能都必须先在需求追踪矩阵中拥有需求 ID、验收方法和证据位置。
8. `AI_USAGE.md` 必须随实现过程持续更新，提交前由人工签字复核。
9. `control/project-control.yaml` 是唯一任务状态真值；任何任务完成都必须有 `control/records/<TASK-ID>.yaml` 和客观证据。
10. 最终提交前必须运行 `scripts/control_plane.py --check-final`，未返回 READY 不得签署验收。
