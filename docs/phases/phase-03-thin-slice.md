# Phase 03 详细实施计划：最薄动态问答闭环

## 1. 阶段目标

| 项目 | 内容 |
|---|---|
| 时间窗口 | T+6～T+12 |
| 当前批次 | P03-01 FastAPI 基础 + P03-06 Web 骨架 |
| 最终目标 | 浏览器完成一次动态、带来源页码、A/B/C 硬隔离的问答 |
| 输入 | Phase 01 API 契约、Phase 02 页/Chunk/事实、中心控制面 |
| 退出门禁 | P03-01～08 均有代码、测试、真实运行证据和完成记录 |

## 2. 任务与依赖

```text
P03-01 API/OpenAPI ─┬→ P03-02 Provider ──────────┐
                    └→ P03-03 路由/检索 → P03-04 引用 ─→ P03-05 SSE API
P03-06 Web 骨架 ──────────────────────────────────────────┤
ACTION-02/03 ─────────────────────────────────────────────┘
                                                ↓
                                      P03-07 浏览器闭环
                                                ↓
                                      P03-08 阶段验收
```

P03-01 是共享契约短前置。完成后 P03-02、P03-03 与持续中的 P03-06 可以真正并行。

## 3. 并行文件冲突边界

| 任务 | 允许修改 | 禁止并行修改 |
|---|---|---|
| P03-01 | `apps/api/**`、根 `pyproject.toml/uv.lock`、API tests、OpenAPI 导出脚本 | `apps/web/**` |
| P03-02 | `apps/api/healthpick_api/providers/**`、provider tests | API 入口、公共响应模型由 P03-01/P03-05 维护 |
| P03-03 | `apps/api/healthpick_api/retrieval/**`、`routing/**`、检索 tests | Provider 和 Web 文件 |
| P03-06 | `apps/web/**` | API Python 文件、根 Python lockfile |
| LEAD 集成 | `control/**`、阶段记录、README、公共契约生成 | 其他执行者不得同时修改 |

共享配置、API 入口、OpenAPI 产物和控制面采用单写者。若任务需要触碰同一文件，先合并短前置再继续，不按不同 hunk 冒险并行。

## 4. P03-01 验收

- FastAPI 从 `apps/api` 可启动；
- `GET /healthz` 不调用数据库或模型，返回服务、版本、环境、request ID 和依赖状态；
- OpenAPI 包含稳定错误模型、Chat/Citation/Safety 共享模型，即使 Chat endpoint 后续才实现；
- CORS 只允许配置的 Web origin；
- 请求验证和未捕获异常使用统一错误契约，不泄露堆栈；
- Mock/Real 配置在状态中可识别，生产配置不得静默使用 Mock；
- pytest 有健康检查、CORS、request ID、OpenAPI 和错误契约证据。

## 5. P03-06 验收

- Next.js App Router + TypeScript + Tailwind；
- 375/768/1440 三档布局没有依赖固定宽度；
- 聊天主区、健康档案摘要、快捷问题、输入区、来源/安全占位组件齐全；
- 默认走 API，不用硬编码回复伪装模型；API 不可用时展示明确错误；
- 开发 fixture 必须显式标注且不能成为生产默认；
- 类型从 FastAPI OpenAPI 生成，不手写第二份跨端协议；
- lint、typecheck/build 和核心组件测试通过。

## 6. 模式透明度

- `LLM_MODE=real|mock` 必须显式；
- Mock 只用于测试和无密钥的开发，UI/health/trace 均显示 Mock；
- `APP_ENV=production` 且 `LLM_MODE=mock` 时启动失败；
- P03-07 的比赛闭环必须绑定 ACTION-02 的真实调用证据；
- Embedding 未就绪时检索模式明确为 keyword，不宣称 vector 已运行。

## 7. 阶段证据

每个任务产生：独立 `control/records/<TASK-ID>.yaml`、测试报告、构建日志或结构化 probe。阶段结束再生成 `docs/evidence/phase-03-baseline-record.md`，不会用开发说明替代运行证据。
