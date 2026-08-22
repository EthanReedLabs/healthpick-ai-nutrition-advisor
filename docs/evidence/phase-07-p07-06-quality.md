# P07-06 功能冻结质量记录

## 结论

P07-06 以 `PASS WITH ACTION` 完成，Phase 07 功能冻结并允许进入 Phase 08。249 项 Python、30 项 Web、Ruff、格式、TypeScript、ESLint、Next.js production build、OpenAPI 类型重生成和真实本地栈全部通过。`ACTION-05` 公网授权与 `ACTION-06` 第二人事实复核继续开放，因此最终总纲保持 `NOT_READY`。

## 冻结门

| 检查 | 结果 | 证据 |
|---|---:|---|
| Python 全仓测试 | 249/249 PASS | `docs/evidence/phase-07-p07-06-pytest.xml` |
| Web 全仓测试 | 30/30 PASS | `docs/evidence/phase-07-p07-06-web-vitest.xml` |
| Python 静态质量 | PASS | Ruff check；174 files format check |
| Web 静态质量 | PASS | TypeScript、ESLint |
| Web 生产构建 | PASS | Next.js 16.3.2 production build |
| 契约重生成无漂移 | PASS | OpenAPI `D36714...097B`；TypeScript `A672B2...BDB` |
| 真实本地闭环 | PASS | `docs/evidence/local-real-stack-runtime.json`（2026-08-22T14:16:49+08:00） |
| 冻结真实评测 | 9/9 PASS | `evals/reports/release-v1.1-20260822T132040911243+0800/summary.json` |

## 运行结论

- 当前 Web `127.0.0.1:3100`、API `127.0.0.1:8010`、PostgreSQL 和 Ollama 可用。
- 真实 LLM 为 `qwen2.5:3b-instruct`，Embedding 为 `qwen3-embedding:0.6b`，存储为 PostgreSQL。
- 营养路径只使用 A/B，平台路径只使用 C，越界路径不返回引用。
- 真实 72 cases / 80 turns 的九项冻结发布门全部通过；最终引用支持率 95.5882%，首字 P95 2814ms。
- 用户停止生成、主备切换、评测公开摘要和桌面/移动验收均已有独立任务记录。

## 本任务问题记录

未发现新的产品缺陷。验收过程中两次只读核对命令使用了不存在的猜测文件名，定位到真实的 `control/project-control.yaml`、`docs/governance/ISSUE_LOG.md` 和 `docs/evidence/phase-06-baseline-record.md` 后继续；未修改配置、未影响产品或证据。

## 保留行动

- `ACTION-05`：Render 区域、预算、公网部署与七天可用性需要用户授权，阻断 P08-02/P08-06。
- `ACTION-06`：结构化事实第二人逐条复核仍开放，阻断最终知识准确性签署。

## 沉淀候选

功能冻结不能只跑单测：应把后端、前端、生产构建、共享契约重生成、真实依赖闭环和不可覆盖的真实评测报告一起作为一组发布基线；外部授权和人工复核必须保留为显式行动，不能用阶段通过替代。
