# 问题与解决统一日志

> 真值来自 `control/project-control.yaml`。问题不删除；解决后保留原因、处理和证据。

## ISSUE-001 · RESOLVED

- 发现时间：2026-08-21T16:47:07+08:00
- 阶段/任务：PHASE-01 / P01-08, DATA-05, DATA-06
- 严重度：high；阻断最终验收：True
- 现象：本机没有 Docker 和 psql，数据库与 pgvector 无法运行验收。
- 原因：初始开发机未安装 Docker Desktop。
- 解决/缓解：安装 Docker Desktop 4.87.0；Compose 启动 PostgreSQL 17.11、pgcrypto 1.3、pgvector 0.8.6，并验证 vector(1024) 与 HNSW 索引。
- 行动：ACTION-01
- 证据：docs/evidence/phase-01-baseline-record.md, docs/evidence/phase-02-knowledge-validation.json, docs/evidence/action-01-database-runtime.json

## ISSUE-002 · RESOLVED

- 发现时间：2026-08-21T16:47:07+08:00
- 阶段/任务：PHASE-01 / P01-08, P03-02, P03-07
- 严重度：high；阻断最终验收：True
- 现象：未配置真实 LLM provider/model/quota，无法证明动态模型闭环。
- 原因：初始阶段没有已确认的真实供应商端点。
- 解决/缓解：使用本机 Ollama OpenAI-compatible 端点和 qwen2.5:3b-instruct 完成精确、非截断真实 smoke；云端比赛模型仍可经同一 adapter 替换。
- 行动：ACTION-02
- 证据：docs/evidence/phase-01-baseline-record.md, docs/evidence/action-02-03-real-model-runtime.json

## ISSUE-003 · RESOLVED

- 发现时间：2026-08-21T16:47:07+08:00
- 阶段/任务：PHASE-01 / P01-08, DATA-05, P03-03, P03-07
- 严重度：high；阻断最终验收：True
- 现象：Embedding 模型和维度未知，不能建立可信生产向量索引。
- 原因：初始阶段未冻结 Embedding 模型与维度。
- 解决/缓解：冻结 qwen3-embedding:0.6b、1024 维和 cosine；中文正负样本排序通过，并建立 vector(1024) 与 HNSW 索引。
- 行动：ACTION-03
- 证据：docs/evidence/phase-02-knowledge-validation.json, docs/evidence/action-02-03-real-model-runtime.json, docs/evidence/action-01-database-runtime.json

## ISSUE-004 · RESOLVED

- 发现时间：2026-08-21T16:47:07+08:00
- 阶段/任务：PHASE-01 / P01-08, P08-05
- 严重度：high；阻断最终验收：True
- 现象：Git 仓库没有远端，无法完成匿名克隆和提交候选验收。
- 原因：项目初始只有本地 Git 仓库。
- 解决/缓解：在 EthanReedLabs 下建立 PRIVATE GitHub 仓库，main 首推送成功且远端提交可读。
- 行动：ACTION-04
- 证据：docs/evidence/phase-01-baseline-record.md, docs/evidence/action-04-git-remote-runtime.json

## ISSUE-005 · RESOLVED

- 发现时间：2026-08-21T16:47:07+08:00
- 阶段/任务：PHASE-01 / P01-08, P08-02, P08-06
- 严重度：high；阻断最终验收：False
- 现象：Phase 01 时公网承载平台、区域、预算和七天可用性尚未确认。
- 原因：当时缺少已授权的公网运行环境。
- 解决/缓解：用户提供 Alibaba Cloud ECS 并批准纯镜像部署；公网 IP HTTPS 与真实千问链路已经通过，七天观测单独由 P08-06 管理。
- 行动：无
- 证据：docs/evidence/phase-01-baseline-record.md, docs/evidence/phase-08-p08-02-ecs-production.json

## ISSUE-006 · RESOLVED

- 发现时间：2026-08-21T17:08:00+08:00
- 阶段/任务：PHASE-02 / DATA-01, DATA-03, P03-03, P03-04, P03-05, P03-07
- 严重度：high；阻断最终验收：True
- 现象：A-p02、A-p04、B-p01、B-p05、B-p07、B-p08 的原始 PDF 存在缺字符号，影响 8 个 Chunk。
- 原因：源文件渲染和文本层均缺字，不是解析器丢字。
- 解决/缓解：未猜测符号；8 个受影响 Chunk 已从运行索引 fail-closed 排除，6 条规则完成复核后标记 rejected，修正版来源到达前持续排除。
- 行动：ACTION-07
- 证据：docs/evidence/phase-02-knowledge-validation.json, docs/evidence/phase-02-second-person-review-checklist.md, docs/evidence/action-07-unknown-glyph-exclusion.json

## ISSUE-007 · RESOLVED

- 发现时间：2026-08-21T17:13:00+08:00
- 阶段/任务：PHASE-02 / DATA-06, GOV-01, P03-02
- 严重度：low；阻断最终验收：False
- 现象：Windows 环境缺少 tzdata，ZoneInfo 生成报告时间失败。
- 原因：项目不应为固定中国时区依赖外部 IANA tzdata 包。
- 解决/缓解：改用 timezone(timedelta(hours=8)) 生成固定 UTC+08 时间，随后校验通过。
- 行动：无
- 证据：scripts/validate_knowledge.py, docs/evidence/phase-02-knowledge-validation.json

## ISSUE-008 · RESOLVED

- 发现时间：2026-08-21T17:14:00+08:00
- 阶段/任务：PHASE-02 / DATA-06
- 严重度：medium；阻断最终验收：False
- 现象：首轮业务校验出现 food name 字段映射错误和向量维度静态检查误报。
- 原因：生成字段使用 food_name；向量正则匹配到了非向量语境文本。
- 解决/缓解：校验器改为 food_name，并将向量检查锚定真实 vector(number) DDL；后续 errors=0。
- 行动：无
- 证据：scripts/validate_knowledge.py, docs/evidence/phase-02-knowledge-validation.json

## ISSUE-009 · OPEN

- 发现时间：2026-08-21T17:18:00+08:00
- 阶段/任务：PHASE-02 / DATA-06, GOV-01, P03-01, P03-06
- 严重度：low；阻断最终验收：False
- 现象：Windows 沙箱偶发在创建 PowerShell 子进程前返回 CreateProcessAsUserW 拒绝访问，并行和后续串行调用均曾出现。
- 原因：Windows 沙箱间歇性拒绝创建 PowerShell 子进程，精确的运行器根因尚未确认。
- 解决/缓解：Phase 02 通过串行重跑恢复；GOV-01 复发后改由获批的项目脚本前缀在沙箱外运行，同一脚本随后 structural_status=PASS、errors=0。环境问题保留为非最终阻断的开放记录。
- 行动：无
- 证据：docs/evidence/phase-02-knowledge-validation.json, docs/evidence/phase-02-pytest.xml, docs/evidence/control-plane-validation.json

## ISSUE-010 · RESOLVED

- 发现时间：2026-08-21T17:22:00+08:00
- 阶段/任务：PHASE-02 / DATA-06
- 严重度：low；阻断最终验收：False
- 现象：pytest.exe 收集测试时找不到根目录 scripts 模块。
- 原因：pytest 启动路径未显式加入仓库根目录。
- 解决/缓解：在 pyproject.toml 添加 pytest pythonpath=[\".\"]，随后 11/11 通过。
- 行动：无
- 证据：pyproject.toml, docs/evidence/phase-02-pytest.xml

## ISSUE-011 · RESOLVED

- 发现时间：2026-08-21T17:24:00+08:00
- 阶段/任务：PHASE-02 / DATA-06
- 严重度：low；阻断最终验收：False
- 现象：当前 PowerShell 中 rg 不可用，第一次密钥审计结果因此无效。
- 原因：rg 未安装或不在当前 shell PATH，未做全局环境修改。
- 解决/缓解：改用 Select-String 重新扫描，真实密钥文件命中为 0。
- 行动：无
- 证据：docs/evidence/phase-02-baseline-record.md

## ISSUE-012 · RESOLVED

- 发现时间：2026-08-21T18:31:00+08:00
- 阶段/任务：PHASE-03 / P03-01, P03-02
- 严重度：low；阻断最终验收：False
- 现象：uv sync 无法创建 hardlink，并警告将回退为完整复制。
- 原因：当前 uv 缓存与项目环境之间不支持所需 hardlink 操作。
- 解决/缓解：接受 uv 的完整复制回退；依赖安装成功、锁文件生成且 API 测试通过，无需修改全局环境。
- 行动：无
- 证据：docs/evidence/phase-03-api-dependency-sync.md, uv.lock, docs/evidence/phase-03-api-pytest.xml

## ISSUE-013 · RESOLVED

- 发现时间：2026-08-21T18:34:00+08:00
- 阶段/任务：PHASE-03 / P03-01
- 严重度：medium；阻断最终验收：False
- 现象：FastAPI TestClient 运行时提示基于 httpx 的通道已弃用，应安装 httpx2。
- 原因：Starlette 1.6.0 已迁移 TestClient 传输层；项目最初仍显式依赖旧 httpx。
- 解决/缓解：开发依赖替换为 httpx2>=2,<3，uv 重锁后同一 8 项测试无警告通过。
- 行动：无
- 证据：pyproject.toml, uv.lock, docs/evidence/phase-03-api-dependency-sync.md, docs/evidence/phase-03-api-pytest.xml

## ISSUE-014 · OPEN

- 发现时间：2026-08-21T18:42:00+08:00
- 阶段/任务：PHASE-03 / P03-06
- 严重度：low；阻断最终验收：False
- 现象：create-next-app 安装的 ESLint 9.39.5 输出版本已弃用提示。
- 原因：ESLint 10 已发布，但 Next 16.3.2 固定的 eslint-plugin-import、jsx-a11y 和 react peer 范围仍拒绝 ESLint 10。
- 解决/缓解：项目精确固定兼容的 ESLint 9.39.5；npm ls 依赖树、Lint 和 Build 均通过，待 Next 插件链支持 ESLint 10 后升级复验。
- 行动：无
- 证据：apps/web/package.json, apps/web/package-lock.json, docs/evidence/phase-03-web-quality.md

## ISSUE-015 · RESOLVED

- 发现时间：2026-08-21T18:55:17+08:00
- 阶段/任务：PHASE-03 / P03-06
- 严重度：low；阻断最终验收：False
- 现象：Vitest 首次运行时后续用例发现前一用例残留 DOM，并伴随 Vite 配置加载警告。
- 原因：测试装配未显式执行 cleanup，且 Web package 未声明 ESM。
- 解决/缓解：afterEach 显式 cleanup，并将 apps/web 声明为 type=module；同一 3 项测试无警告通过。
- 行动：无
- 证据：apps/web/src/components/chat-workspace.test.tsx, apps/web/package.json, docs/evidence/phase-03-web-vitest.xml

## ISSUE-016 · RESOLVED

- 发现时间：2026-08-21T18:58:27+08:00
- 阶段/任务：PHASE-03 / P03-01, P03-06
- 严重度：medium；阻断最终验收：False
- 现象：localhost:3000 和 8000 已被其他本机服务占用，首次预览触发错误页面及 CORS 拦截。
- 原因：localhost 在本机解析到已有 IPv6 监听者，且 8000 由系统 HTTP 服务监听；项目首版默认端口与既有服务冲突。
- 解决/缓解：项目开发契约统一为 127.0.0.1:3000 与 127.0.0.1:8010，更新配置、环境样例和启动文档；隔离预览无意外控制台错误通过。
- 行动：无
- 证据：.env.example, apps/api/healthpick_api/config.py, apps/api/README.md, apps/web/README.md, docs/evidence/phase-03-web-runtime.json

## ISSUE-017 · OPEN

- 发现时间：2026-08-21T18:57:00+08:00
- 阶段/任务：PHASE-03 / P03-06, P03-07
- 严重度：low；阻断最终验收：False
- 现象：内置浏览器连接在页面操作前因宿主请求缺失 sandboxPolicy 元数据失败。
- 原因：Codex 宿主与内置浏览器连接器的沙箱元数据不完整，非项目代码错误。
- 解决/缓解：按浏览器技能降级使用 playwright-cli 完成相同三视口、交互和截图验收；宿主连接问题保留为非最终阻断记录。
- 行动：无
- 证据：docs/evidence/phase-03-web-runtime.json, output/playwright/phase-03-desktop-1440x1000.png, output/playwright/phase-03-tablet-1024x900.png, output/playwright/phase-03-mobile-390x844.png

## ISSUE-018 · RESOLVED

- 发现时间：2026-08-21T19:09:00+08:00
- 阶段/任务：PHASE-03 / P03-02
- 严重度：low；阻断最终验收：False
- 现象：Provider 首轮异步测试未执行，且 Real 缺配置用例受本地环境变量污染。
- 原因：项目没有 pytest-asyncio；Settings 测试只禁用了 .env 文件，没有显式覆盖进程环境中的 LLM 字段。
- 解决/缓解：复用 FastAPI 已依赖的 AnyIO pytest 插件并固定 asyncio backend；缺配置用例显式清空三项 Real 参数，同一 8 项专项测试通过。
- 行动：无
- 证据：tests/api/test_providers.py, docs/evidence/phase-03-api-pytest.xml

## ISSUE-019 · RESOLVED

- 发现时间：2026-08-21T19:11:00+08:00
- 阶段/任务：PHASE-03 / P03-01, P03-02, P03-03
- 严重度：low；阻断最终验收：False
- 现象：计划中的 Python 风格门禁无法运行，因为 Ruff 未声明为项目依赖；安装后首次发现 4 个 lint 与 7 个 format 差异。
- 原因：Phase 01/02 仅配置 pytest，未把 Ruff 和规则写入可复现的开发依赖。
- 解决/缓解：项目锁定 Ruff 0.16.4，配置 E/F/I/UP/B 规则并机械修复既有格式；check、format check 和 16 项 API 回归均通过。
- 行动：无
- 证据：pyproject.toml, uv.lock, docs/evidence/phase-03-provider-quality.md, docs/evidence/phase-03-api-pytest.xml

## ISSUE-020 · RESOLVED

- 发现时间：2026-08-21T19:35:00+08:00
- 阶段/任务：PHASE-03 / P03-06, P03-07
- 严重度：medium；阻断最终验收：False
- 现象：Web 资料边界卡片误把 B 描述为平台说明、C 描述为补充资料，与实际 A/B 核心营养、C 平台专用策略相反。
- 原因：P03-06 视觉占位文案未逐项绑定 sources.yaml 的 source_role 和 allowed_uses。
- 解决/缓解：卡片改为 A 健康膳食指南、B 个性化饮食方案、C 平台服务白皮书，并明确 C 仅用于平台功能与规则；P03-07 浏览器快照重新核验。
- 行动：无
- 证据：knowledge/manifests/sources.yaml, apps/web/src/components/chat-workspace.tsx

## ISSUE-021 · RESOLVED

- 发现时间：2026-08-21T19:37:00+08:00
- 阶段/任务：PHASE-03 / P03-06, P03-07
- 严重度：medium；阻断最终验收：False
- 现象：动态回答截图中 A/B 引用卡整块被染成深绿或蓝色，正文对比度下降。
- 原因：资料边界徽章使用全局 source-a/source-b/source-c 背景选择器，与引用卡的来源类名冲突。
- 解决/缓解：背景色选择器限定为 sources-card 后代；引用卡恢复浅色背景，仅用左边线区分来源，并重新执行浏览器视觉验收。
- 行动：无
- 证据：apps/web/src/app/globals.css, output/playwright/phase-03-dynamic-mock-closed-loop.png

## ISSUE-022 · RESOLVED

- 发现时间：2026-08-21T19:47:30+08:00
- 阶段/任务：PHASE-03 / P03-08
- 严重度：medium；阻断最终验收：False
- 现象：Phase 03 退出查漏时 README 仍宣称核心应用代码尚未开始，与控制面和实际交付冲突。
- 原因：P03-01～07 完成后未同步更新仓库对外首页的当前阶段摘要。
- 解决/缓解：README 更新 Phase 03 交付、50/4 测试、浏览器隔离结果与 Phase 04 READY 状态，并链接 Phase 03 验收记录。
- 行动：无
- 证据：README.md, docs/evidence/phase-03-baseline-record.md, control/project-control.yaml

## ISSUE-023 · RESOLVED

- 发现时间：2026-08-21T20:53:00+08:00
- 阶段/任务：PHASE-03 / GOV-01
- 严重度：medium；阻断最终验收：False
- 现象：全量 pytest 中两条控制面测试仍断言已关闭的 ACTION-01 和已解决的 ISSUE-006，导致状态推进后回归失败。
- 原因：测试把瞬时任务 ID 和旧状态写死，而不是验证控制面的状态不变量。
- 解决/缓解：改为断言存在未完成任务、最终门保持关闭，并逐项校验所有开放且 blocks_final 的问题进入阻断清单。
- 行动：无
- 证据：tests/test_control_plane.py, docs/evidence/current-pytest.xml

## ISSUE-024 · RESOLVED

- 发现时间：2026-08-21T20:55:00+08:00
- 阶段/任务：PHASE-03 / P03-02, P03-03
- 严重度：medium；阻断最终验收：False
- 现象：README 规定的独立真实模型 smoke 命令报 ModuleNotFoundError，但 pytest 未暴露该问题。
- 原因：pytest 配置注入 apps/api 到 Python 路径，独立脚本没有自行定位 API 包。
- 解决/缓解：所有依赖 healthpick_api 的 smoke 脚本统一从仓库根注入 apps/api，并以 README 原命令真实复验。
- 行动：无
- 证据：scripts/smoke_real_models.py, scripts/smoke_provider.py, scripts/smoke_retrieval.py, docs/evidence/action-02-03-real-model-runtime.json

## ISSUE-025 · RESOLVED

- 发现时间：2026-08-21T20:58:00+08:00
- 阶段/任务：PHASE-03 / P03-05, P03-07, P04-04
- 严重度：high；阻断最终验收：False
- 现象：真实 LLM 的域内请求因缺少校验器认可的行内 Chunk 引用而全部返回 evidence_validation_failed 502，Mock 测试未暴露。
- 原因：提示词把引用格式描述为对应的【Chunk-ID】，模型输出了字面标签或省略引用；校验器只接受严格的【A-p01-c04】形式。
- 解决/缓解：冻结唯一引用正反例，首次校验失败时仅允许携带错误码和白名单 Chunk ID 受限重生成一次，第二次仍失败继续 fail-closed；日志记录分类错误和回答哈希。
- 行动：无
- 证据：apps/api/healthpick_api/chat/pipeline.py, tests/api/test_chat_sse.py, docs/evidence/local-real-stack-runtime.json, docs/evidence/local-real-stack-browser.md

## ISSUE-026 · RESOLVED

- 发现时间：2026-08-21T21:00:00+08:00
- 阶段/任务：PHASE-03 / P03-05
- 严重度：low；阻断最终验收：False
- 现象：引用修复重试首版补丁把辅助函数插入 _user_prompt 中部，专项测试出现 500。
- 原因：补丁上下文命中函数内部的空行，导致原函数尾部误落入日志辅助函数。
- 解决/缓解：恢复 _user_prompt 完整返回结构，将修复提示和日志函数移到函数边界外；24 项专项测试和 Ruff 随后通过。
- 行动：无
- 证据：apps/api/healthpick_api/chat/pipeline.py, tests/api/test_chat_sse.py, docs/evidence/current-pytest.xml

## ISSUE-027 · RESOLVED

- 发现时间：2026-08-21T21:03:00+08:00
- 阶段/任务：PHASE-03 / P03-06, P03-07
- 严重度：low；阻断最终验收：False
- 现象：本机 3000 端口被另一个 Next.js 项目占用，本项目不能按默认端口启动。
- 原因：其他工作区的 node 进程监听双栈 3000；不是 HealthPick 进程或代码故障。
- 解决/缓解：不终止其他项目；本次 Web 显式使用 3100，API CORS 同步绑定该 origin，真实浏览器闭环通过。
- 行动：无
- 证据：docs/evidence/local-real-stack-browser.md, output/playwright/local-real-platform-1440x1000.png

## ISSUE-028 · RESOLVED

- 发现时间：2026-08-21T21:14:00+08:00
- 阶段/任务：PHASE-04 / P04-01
- 严重度：low；阻断最终验收：False
- 现象：首次生成 Web API 类型时在 apps/web 目录调用根目录相对 Python 路径失败，但 npm 随后仍使用旧 OpenAPI 继续生成类型。
- 原因：两条命令使用不同工作目录契约，PowerShell 非终止错误未阻止后续命令。
- 解决/缓解：从仓库根重新导出 OpenAPI，再以 npm --prefix 生成类型，并显式检索 profile 路径、ProfileAssessment 和字段后才接受产物。
- 行动：无
- 证据：scripts/export_openapi.py, packages/shared/openapi/healthpick.openapi.json, apps/web/src/lib/api-schema.d.ts

## ISSUE-029 · RESOLVED

- 发现时间：2026-08-21T21:32:30+08:00
- 阶段/任务：PHASE-04 / P04-04, P04-06
- 严重度：high；阻断最终验收：False
- 现象：S2 general-only 真实模型回答未稳定附加专业咨询提示，且现有 EvidenceValidator 只验证引用存在/来源边界，尚未逐项拦截未受证据支持的结论。
- 原因：P04-03 已完成前置风险分级，但 P04-04 的输出安全校验、免责声明和安全降级模板尚未实现。
- 解决/缓解：服务端现已按风险等级确定性附加声明，逐分句校验引用、文字锚点和精确数值；模型单次修复后仍失败时只返回经相同门禁复验的确定性证据回退，回退自身失败才关闭输出；真实本地模型五条路径全部通过。
- 行动：无
- 证据：docs/evidence/phase-04-p04-04-design.md, docs/evidence/phase-04-p04-04-runtime.json, docs/evidence/phase-04-p04-04-api-pytest.xml

## ISSUE-030 · RESOLVED

- 发现时间：2026-08-21T21:45:40+08:00
- 阶段/任务：PHASE-04 / P04-03, P04-05
- 严重度：high；阻断最终验收：False
- 现象：真实浏览器中先触发 S3 紧急中止，再用同一页面询问普通膳食纤维问题，模型回答错误带入上一轮胸痛和呼吸困难内容。
- 原因：前端固定使用 web-demo-session 且新对话只清界面；后端把确定性 S3 安全结果写入最近四轮模型历史，混淆了界面、会话和单次生成生命周期。
- 解决/缓解：S3 发生时原子清空该会话，所有确定性安全拒答不写入生成历史；前端每次新对话生成独立 conversation_id；新增连续请求与换 ID 回归测试并用真实模型重放通过。
- 行动：无
- 证据：tests/api/test_safety.py, apps/api/healthpick_api/chat/conversation.py, apps/api/healthpick_api/chat/pipeline.py, apps/web/src/components/chat-workspace.test.tsx, docs/evidence/phase-04-p04-05-browser.md

## ISSUE-031 · RESOLVED

- 发现时间：2026-08-21T21:52:20+08:00
- 阶段/任务：PHASE-04 / P04-05
- 严重度：medium；阻断最终验收：False
- 现象：小于 1180px 时右侧档案区隐藏，平板和手机没有可靠健康档案入口；手机同时没有新对话入口。
- 原因：响应式 CSS 隐藏了两个侧栏，但关键操作只存在于侧栏。
- 解决/缓解：桌面状态区增加健康档案入口，移动顶栏增加新对话和档案按钮；375px 真实点击、对话框截图和前端测试通过。
- 行动：无
- 证据：apps/web/src/components/chat-workspace.tsx, apps/web/src/components/chat-workspace.test.tsx, output/playwright/phase-04-p04-05-profile-375x812.png, output/playwright/phase-04-p04-05-mobile-entry-375x812.png

## ISSUE-032 · RESOLVED

- 发现时间：2026-08-21T22:40:20+08:00
- 阶段/任务：PHASE-04 / P04-04, P04-06
- 严重度：high；阻断最终验收：False
- 现象：API 与 Ollama 健康时，真实模型在单次修复后仍产生未引用事实分句，顺序和并发 smoke 均返回 evidence_validation_failed 502。
- 原因：首次生成温度为 0.1 且提示允许长回答，小模型可能在已引用内容之外追加开场、总结或补充结论；原流程第二次失败只有 502，没有确定性可用性回退。
- 解决/缓解：首次生成固定温度 0 并限制为一至三条单事实短句；修复仍失败时从已验证 citation excerpt 确定性组装答案并用同一证据/输出门禁复验；回退自身失败仍关闭。真实双 smoke 并发全部 200，其中一条实际命中回退。
- 行动：无
- 证据：apps/api/healthpick_api/chat/pipeline.py, tests/api/test_chat_sse.py, docs/evidence/phase-04-p04-04-runtime.json, docs/evidence/local-real-stack-runtime.json, docs/evidence/phase-04-p04-06-quality.md

## ISSUE-033 · RESOLVED

- 发现时间：2026-08-21T23:31:00+08:00
- 阶段/任务：PHASE-05 / P05-01, P05-03
- 严重度：medium；阻断最终验收：False
- 现象：真实浏览器中新建对话后立即发送时，发送逻辑可能仍读取上一个对话 ID，把新问题写入旧对话。
- 原因：新对话创建只更新异步 React state，发送路径没有等待同一个服务端对话创建 Promise，也没有先清除旧 conversation 引用。
- 解决/缓解：把会话和对话创建纳入共享 bootstrap barrier，新建开始即清空旧引用，发送统一等待 barrier 后只使用服务端规范 ID；组件测试和真实浏览器立即发送通过。
- 行动：无
- 证据：apps/web/src/components/chat-workspace.tsx, apps/web/src/components/chat-workspace.test.tsx, docs/evidence/phase-05-p05-01-browser.md

## ISSUE-034 · RESOLVED

- 发现时间：2026-08-21T23:42:00+08:00
- 阶段/任务：PHASE-05 / P04-04, P04-06, P05-01
- 严重度：high；阻断最终验收：False
- 现象：真实模型产生组合引用 `【A-p03-c03; A-p03-c04】`，且引用位于句号后时，下一事实分句可能被错误视为已有引用。
- 原因：证据校验只提取合法单 ID，没有拒绝引用样式异常；分句规则还禁止在引用闭合后切分，导致前一引用覆盖后续事实。
- 解决/缓解：新增引用样式 token 校验并拒绝组合 ID；引用闭合后遇到新内容重新分句；提示词冻结为每条事实一个独立引用，新增两项回归测试并用真实模型重放通过。
- 行动：无
- 证据：apps/api/healthpick_api/evidence/validator.py, apps/api/healthpick_api/chat/pipeline.py, tests/api/test_evidence.py, docs/evidence/phase-05-p05-01-browser.md

## ISSUE-035 · RESOLVED

- 发现时间：2026-08-21T23:57:00+08:00
- 阶段/任务：PHASE-05 / P05-02
- 严重度：high；阻断最终验收：False
- 现象：公共 API 没有请求体总上限，空白消息可绕过最小长度；模型超时、连接失败、限流、上游拒绝和数据库故障的错误分类不够细。
- 原因：Phase 03 最薄闭环只冻结了统一错误外形，尚未实施 P0 输入资源边界与按真因分层的故障契约。
- 解决/缓解：增加 32 KiB 请求体门和去空白字段边界；模型、Embedding、PostgreSQL 分层错误码及超时；对 413/422/405/502/503/504 做故障注入和真实运行 smoke。
- 行动：无
- 证据：apps/api/healthpick_api/main.py, apps/api/healthpick_api/models.py, apps/api/healthpick_api/providers/openai_compatible.py, apps/api/healthpick_api/chat/conversation.py, docs/evidence/phase-05-p05-02-error-contract.json

## ISSUE-036 · RESOLVED

- 发现时间：2026-08-22T00:11:00+08:00
- 阶段/任务：PHASE-05 / P05-01, P05-02
- 严重度：high；阻断最终验收：False
- 现象：前端超时重试使用错误响应体中的 request_id；若网关或异常响应返回不同 ID，重试会失去数据库幂等键并可能重复落库。
- 原因：客户端把服务端相关 ID 同时当成自己的重试标识，没有保持首次请求头 ID 为单一权威值。
- 解决/缓解：sendChat 在请求开始生成客户端 UUID，错误解析无条件保留该原始 ID；UI 重试复用同一值。单测构造 ID 不匹配响应，浏览器请求 53/54 网络头均验证为同一 UUID。
- 行动：无
- 证据：apps/web/src/lib/api.ts, apps/web/src/lib/api.test.ts, apps/web/src/components/chat-workspace.test.tsx, docs/evidence/phase-05-p05-02-browser.md

## ISSUE-037 · RESOLVED

- 发现时间：2026-08-22T00:14:00+08:00
- 阶段/任务：PHASE-05 / P05-01, P05-02, P05-05
- 严重度：high；阻断最终验收：False
- 现象：smoke_local_stack.py 及三个 Phase 04 runtime smoke 在 PostgreSQL 模式返回 422，安全 smoke 还把合法确定性证据回退误判为提供者错误。
- 原因：产品契约升级为服务端规范会话 ID 后，旧 smoke 仍发送 Phase 03 固定字符串 ID；断言也未同步 ISSUE-032 已批准的证据回退路径。
- 解决/缓解：新增共享 RuntimeConversationScope，所有运行 smoke 先走公开匿名会话和对话创建接口并清理对话；安全 smoke 接受经门禁复验的 deterministic_evidence_fallback，同时保持 guard 名称约束。四组真实 runtime smoke 全部重跑通过。
- 行动：无
- 证据：scripts/runtime_conversation.py, scripts/smoke_local_stack.py, scripts/smoke_profile.py, scripts/smoke_safety.py, scripts/smoke_output_safety.py, docs/evidence/local-real-stack-runtime.json, docs/evidence/phase-04-p04-03-runtime.json

## ISSUE-038 · RESOLVED

- 发现时间：2026-08-22T00:24:00+08:00
- 阶段/任务：PHASE-05 / P05-04
- 严重度：high；阻断最终验收：False
- 现象：原 Compose 只有 PostgreSQL，迁移依赖空卷首次初始化目录，已有卷不会执行新增迁移，且没有知识 seed、API 或 Web 编排。
- 原因：Phase 02 只建立数据库开发基线，尚未实施 Phase 05 的可重复全栈交付链。
- 解决/缓解：新增显式 migrate/seed one-shot 服务和 API/Web 生产镜像，冻结五级健康依赖顺序；空库与旧卷重复启动均通过。
- 行动：无
- 证据：compose.yaml, scripts/migrate_database.py, scripts/seed_database.py, docs/evidence/phase-05-p05-04-compose.json

## ISSUE-039 · RESOLVED

- 发现时间：2026-08-22T09:34:00+08:00
- 阶段/任务：PHASE-05 / P05-04
- 严重度：high；阻断最终验收：False
- 现象：迁移和 seed 成功后 API 生产容器持续退出，日志为 ModuleNotFoundError httpx2，Web 被健康依赖链阻止。
- 原因：API 运行时依赖 httpx2 被放在 dev 组，本机完整开发环境掩盖了生产镜像缺包。
- 解决/缓解：将 httpx2 移入运行依赖并刷新锁文件；no-dev 生产镜像与全量回归通过。
- 行动：无
- 证据：pyproject.toml, uv.lock, infra/docker/api.Dockerfile, docs/evidence/phase-05-p05-04-quality.md

## ISSUE-040 · RESOLVED

- 发现时间：2026-08-22T09:46:00+08:00
- 阶段/任务：PHASE-05 / P05-04
- 严重度：high；阻断最终验收：False
- 现象：容器网络和 Ollama 模型目录正常，但真实 Chat 因实际模型被覆盖为未安装模型而返回 provider_rejected_request 502。
- 原因：Compose 自动读取根 .env，部署 LLM_MODEL 静默覆盖本地默认模型。
- 解决/缓解：Compose 应用覆盖统一使用 COMPOSE_* 命名空间；本地默认 Ollama 模型恢复并通过真实问答。
- 行动：无
- 证据：compose.yaml, infra/README.md, docs/evidence/phase-05-p05-04-compose.json

## ISSUE-041 · RESOLVED

- 发现时间：2026-08-22T09:43:00+08:00
- 阶段/任务：PHASE-05 / P05-04
- 严重度：low；阻断最终验收：False
- 现象：知识计数正确但生命周期 smoke 误报不存在成功导入记录。
- 原因：验收脚本查询 success，数据库成功枚举实际为 passed。
- 解决/缓解：查询与 schema 枚举对齐并重跑，三次成功幂等导入和重启 smoke 通过。
- 行动：无
- 证据：scripts/smoke_compose_lifecycle.py, docs/evidence/phase-05-p05-04-compose.json

## ISSUE-042 · RESOLVED

- 发现时间：2026-08-22T09:58:00+08:00
- 阶段/任务：PHASE-05 / P05-03
- 严重度：high；阻断最终验收：False
- 现象：375px 隐藏左侧栏后没有历史对话入口。
- 原因：P05-01 新增历史功能后，响应式关键入口盘点没有同步移动顶栏。
- 解决/缓解：增加移动历史按钮和可聚焦、可 Escape 关闭的底部弹层。
- 行动：无
- 证据：apps/web/src/components/chat-workspace.tsx, apps/web/src/app/globals.css, docs/evidence/phase-05-p05-03-browser.md

## ISSUE-043 · RESOLVED

- 发现时间：2026-08-22T10:02:00+08:00
- 阶段/任务：PHASE-05 / P05-03
- 严重度：high；阻断最终验收：False
- 现象：会话恢复读取删除失败与真正空状态和聊天错误混叠，且缺少对应恢复动作。
- 原因：会话生命周期与聊天生成共享过于粗糙的空和错误表示。
- 解决/缓解：拆分 session activity 和 recovery action，为各状态提供独立文案、ARIA 状态和重试动作。
- 行动：无
- 证据：apps/web/src/components/chat-workspace.tsx, apps/web/src/components/chat-workspace.test.tsx, docs/evidence/phase-05-p05-03-web-vitest.xml

## ISSUE-044 · RESOLVED

- 发现时间：2026-08-22T10:06:00+08:00
- 阶段/任务：PHASE-05 / P05-03
- 严重度：medium；阻断最终验收：False
- 现象：输入区声明 Enter 发送但 textarea 没有键盘提交处理。
- 原因：界面提示早于键盘契约实现，既有测试只覆盖按钮提交。
- 解决/缓解：实现 Enter 发送、Shift+Enter 换行和 IME 保护，并增加自动与真实浏览器验证。
- 行动：无
- 证据：apps/web/src/components/chat-workspace.tsx, apps/web/src/components/chat-workspace.test.tsx, docs/evidence/phase-05-p05-03-browser.md

## ISSUE-045 · RESOLVED

- 发现时间：2026-08-22T10:10:00+08:00
- 阶段/任务：PHASE-05 / P05-01, P05-03
- 严重度：high；阻断最终验收：False
- 现象：首版会话状态禁用策略阻止初始化期间立即发送，破坏已验收的 bootstrap 路径。
- 原因：会话切换交互锁被错误扩展到已受 bootstrap barrier 保护的提交入口。
- 解决/缓解：初始化期间允许提交并由 barrier 排队，只在回答生成时禁用提交。
- 行动：无
- 证据：apps/web/src/components/chat-workspace.tsx, apps/web/src/components/chat-workspace.test.tsx, docs/evidence/phase-05-p05-03-web-vitest.xml

## ISSUE-046 · RESOLVED

- 发现时间：2026-08-22T10:14:00+08:00
- 阶段/任务：PHASE-05 / P05-03
- 严重度：medium；阻断最终验收：False
- 现象：桌面和移动历史实例生成相同标题 DOM ID，aria-describedby 目标不唯一。
- 原因：共用列表用 conversation ID 直接生成元素 ID，没有组件实例身份。
- 解决/缓解：增加 desktop/mobile ID 前缀，三档浏览器扫描重复 ID 均为 0。
- 行动：无
- 证据：apps/web/src/components/chat-workspace.tsx, docs/evidence/phase-05-p05-03-browser.md

## ISSUE-047 · RESOLVED

- 发现时间：2026-08-22T10:36:00+08:00
- 阶段/任务：PHASE-05 / P05-05
- 严重度：high；阻断最终验收：False
- 现象：主需求追踪矩阵只有计划态，无法区分当前实测、部分完成和发布待办。
- 原因：早期矩阵用于方案设计，尚未绑定同 scope、带时序的真实证据。
- 解决/缓解：新增34个P0实测快照，逐项关联实现、最新证据和剩余门，并同步主矩阵状态口径。
- 行动：无
- 证据：docs/01-requirements-traceability.md, docs/evidence/phase-05-p05-05-p0-traceability.md

## ISSUE-048 · RESOLVED

- 发现时间：2026-08-22T10:37:00+08:00
- 阶段/任务：PHASE-05 / P05-05, P07-05
- 严重度：medium；阻断最终验收：False
- 现象：Web没有用户可操作的停止生成入口，ENG-03尚未完整满足。
- 原因：AbortController只用于请求超时和组件清理，没有暴露用户主动取消控制。
- 解决/缓解：P07-05完成Web主动停止、API活动任务取消、输入与焦点恢复，并在真实PostgreSQL桌面移动会话验证中断后零轮次。
- 行动：ACTION-08
- 证据：apps/api/healthpick_api/main.py, apps/web/src/components/chat-workspace.tsx, apps/web/src/lib/api.ts, docs/evidence/phase-07-p07-05-cancellation.json, docs/evidence/phase-07-p07-05-browser.md

## ISSUE-049 · RESOLVED

- 发现时间：2026-08-22T10:50:00+08:00
- 阶段/任务：PHASE-06 / P06-01
- 严重度：high；阻断最终验收：False
- 现象：在匿名会话表增加账号归属后，原历史和Chat接口若仍只校验会话UUID，会让已接管历史继续被匿名或其他账号访问。
- 原因：Phase05接口以匿名会话UUID作为边界，账号接管引入了新的授权边界但旧路由没有身份参数。
- 解决/缓解：为所有会话绑定的创建、列表、读取、重命名、删除和Chat入口增加集中归属授权；未登录访问已接管会话返回401，跨账号返回403。
- 行动：无
- 证据：apps/api/healthpick_api/main.py, tests/api/test_auth.py, docs/evidence/phase-06-p06-01-postgres.json

## ISSUE-050 · RESOLVED

- 发现时间：2026-08-22T10:54:00+08:00
- 阶段/任务：PHASE-06 / P06-01
- 严重度：medium；阻断最终验收：False
- 现象：新增005迁移后数据库生命周期测试仅因预期版本仍为001至004而失败。
- 原因：测试硬编码迁移版本列表，新增合法迁移时没有从实际迁移集派生预期。
- 解决/缓解：更新生命周期断言为001至005并重跑10项账号及迁移专项全部通过；后续P08考虑把版本预期改为目录发现结果。
- 行动：无
- 证据：tests/test_database_lifecycle.py, docs/evidence/phase-06-p06-01-pytest.xml

## ISSUE-051 · RESOLVED

- 发现时间：2026-08-22T11:00:00+08:00
- 阶段/任务：PHASE-06 / P06-01
- 严重度：low；阻断最终验收：False
- 现象：真实账号烟测第一次启动即报ModuleNotFoundError healthpick_api，尚未进入数据库逻辑。
- 原因：新脚本没有沿用仓库其他运行脚本将apps/api加入sys.path的入口约定。
- 解决/缓解：加入统一ROOT路径引导并通过Ruff，随后真实PostgreSQL 11项烟测全部通过且测试数据清理完成。
- 行动：无
- 证据：scripts/smoke_account_migration.py, docs/evidence/phase-06-p06-01-postgres.json

## ISSUE-052 · RESOLVED

- 发现时间：2026-08-22T11:07:00+08:00
- 阶段/任务：PHASE-06 / P06-02
- 严重度：medium；阻断最终验收：False
- 现象：后端已有重命名接口，但Web最近对话只提供选择和删除，历史增多后也没有搜索或空结果反馈。
- 原因：Phase05优先闭合持久化CRUD与移动历史入口，P1检索和改名交互按计划留在Phase06。
- 解决/缓解：新增桌面移动共享的标题搜索、匹配计数、清除和空结果；新增行内改名、独立失败重试，并以刷新恢复和PostgreSQL标题查询配对验收。
- 行动：无
- 证据：apps/web/src/components/chat-workspace.tsx, docs/evidence/phase-06-p06-02-quality.md, docs/evidence/phase-06-p06-02-browser.md, docs/evidence/phase-06-p06-01-postgres.json

## ISSUE-053 · RESOLVED

- 发现时间：2026-08-22T11:24:00+08:00
- 阶段/任务：PHASE-06 / P06-03
- 严重度：high；阻断最终验收：False
- 现象：检索成功后公开Chat事件触发Pydantic校验500，无法返回最终回答。
- 原因：内部路由recommendation被直接写入只接受nutrition、platform和out_of_scope的公开Trace枚举。
- 解决/缓解：Trace统一使用_public_route映射，并增加正常检索、来源边界和越界保护回归断言；28项API专项通过。
- 行动：无
- 证据：apps/api/healthpick_api/chat/pipeline.py, tests/api/test_chat_sse.py, docs/evidence/phase-06-p06-03-api-pytest.xml

## ISSUE-054 · RESOLVED

- 发现时间：2026-08-22T11:32:00+08:00
- 阶段/任务：PHASE-06 / P06-03
- 严重度：high；阻断最终验收：False
- 现象：手工重启本地API后先因模型配置漂移返回503，恢复模型后又因遗漏WEB_ORIGIN产生8条浏览器CORS错误。
- 原因：本地API依赖多项项目子进程环境，但此前重启命令未形成单一可复现入口。
- 解决/缓解：增加tools/start_local_api.ps1集中设置项目本地端口、模型、数据库和CORS；真实栈、独立8012健康检查及干净浏览器会话全部通过，未修改全局环境。
- 行动：无
- 证据：tools/start_local_api.ps1, docs/evidence/phase-06-p06-03-quality.md, docs/evidence/phase-06-p06-03-browser.md, docs/evidence/local-real-stack-runtime.json

## ISSUE-055 · RESOLVED

- 发现时间：2026-08-22T11:49:00+08:00
- 阶段/任务：PHASE-06 / P06-04
- 严重度：high；阻断最终验收：False
- 现象：注册令牌有效但首个账号导出专项用例返回401 invalid_access_token。
- 原因：API身份辅助函数返回UUID对象，Ephemeral存储按字符串用户ID比较，类型边界不一致导致同一用户未命中。
- 解决/缓解：账号导出和删除进入存储前统一转换规范UUID字符串；账号专项7项、API全量176项和真实PostgreSQL21项通过。
- 行动：无
- 证据：apps/api/healthpick_api/main.py, tests/api/test_auth.py, docs/evidence/phase-06-p06-04-api-pytest.xml, docs/evidence/phase-06-p06-04-postgres.json

## ISSUE-056 · RESOLVED

- 发现时间：2026-08-22T12:00:00+08:00
- 阶段/任务：PHASE-06 / P06-04
- 严重度：low；阻断最终验收：False
- 现象：真实浏览器提示删除确认密码表单缺少用户名字段，可能降低密码管理器识别和可访问性质量。
- 原因：危险操作二次验证表单只展示密码，未为浏览器提供当前账号的username语义。
- 解决/缓解：增加只供密码管理器识别的隐藏只读autocomplete=username邮箱字段；干净浏览器会话控制台错误0、警告0且提示消失。
- 行动：无
- 证据：apps/web/src/components/chat-workspace.tsx, docs/evidence/phase-06-p06-04-browser.md

## ISSUE-057 · RESOLVED

- 发现时间：2026-08-22T12:15:00+08:00
- 阶段/任务：PHASE-07 / P07-01
- 严重度：low；阻断最终验收：False
- 现象：72条评测集生成器首跑在写出数据前因case_id长度契约失败。
- 原因：A、B、C事实类最初使用A-01等四字符短ID，不满足ReleaseCase最小五字符和可读前缀约束。
- 解决/缓解：改用ANUT、BPLAN、CPLAT稳定前缀；重跑后72 cases、80 turns、errors=0，专项2项通过。
- 行动：无
- 证据：scripts/build_release_golden.py, docs/evidence/phase-07-p07-01-dataset-validation.json, docs/evidence/phase-07-p07-01-pytest.xml

## ISSUE-058 · RESOLVED

- 发现时间：2026-08-22T12:44:02+08:00
- 阶段/任务：PHASE-07 / P07-02
- 严重度：high；阻断最终验收：False
- 现象：v1首轮真实评测路由仅81.82%、数字事实50%、引用支持53.62%、多轮25%。
- 原因：确定性路由缺少常见自然语言别名，证据回退只摘首行，检索排序和模型引用未优先直接证据。
- 解决/缓解：增加路由正反fixture、查询相关句抽取、可审计概念提示和首要证据引用；v1.1 attempt3路由与数字100%、引用95.59%、多轮100%。
- 行动：无
- 证据：evals/reports/release-v1-20260822T124320970139+0800/summary.json, apps/api/healthpick_api/routing/router.py, apps/api/healthpick_api/retrieval/keyword.py, docs/evidence/phase-07-p07-02-quality.md

## ISSUE-059 · RESOLVED

- 发现时间：2026-08-22T12:47:00+08:00
- 阶段/任务：PHASE-07 / P07-02
- 严重度：high；阻断最终验收：False
- 现象：v1有高血压/孕期错误S0断言，并把替换表或孕期禁忌Chunk误用于早餐方向和鸡蛋过敏问题。
- 原因：首版数据集结构门只验证来源分区和Chunk存在性，未验证问题、风险策略和断言语义一致性。
- 解决/缓解：保留v1及失败报告，建立仅含6项显式勘误的v1.1；阈值哈希不变，测试保证只修改已登记case/turn。
- 行动：无
- 证据：evals/golden/release-golden-v1.1.manifest.json, scripts/build_release_golden_errata.py, docs/evidence/phase-07-p07-02-errata-validation.json

## ISSUE-060 · RESOLVED

- 发现时间：2026-08-22T13:02:00+08:00
- 阶段/任务：PHASE-07 / P07-02
- 严重度：medium；阻断最终验收：False
- 现象：相对路径运行v1.1时80轮完成后在汇总阶段ValueError，未生成报告。
- 原因：CLI相对Path再次执行relative_to(ROOT)，而默认路径一直为绝对Path，单元测试未覆盖两种入口。
- 解决/缓解：运行入口统一resolve四类路径；确认半成品报告0、临时账号0，并通过路径回归后重跑。
- 行动：无
- 证据：scripts/run_release_evaluation.py, docs/evidence/phase-07-p07-02-aborted-run.json, docs/evidence/phase-07-p07-02-runner-path-pytest.xml

## ISSUE-061 · RESOLVED

- 发现时间：2026-08-22T13:07:00+08:00
- 阶段/任务：PHASE-07 / P07-02
- 严重度：high；阻断最终验收：False
- 现象：首要证据强制引用与鸡蛋过敏硬过滤互相阻断，三个过敏用例返回evidence_validation_failed 502。
- 原因：首要Chunk包含被阻断食物，模型和回退既不能安全输出该候选，也不能改用安全次要证据。
- 解决/缓解：blocked food场景允许安全次要证据，确定性回退先排除含阻断食物的候选句；专项22项和v1.1 attempt2/3均零5xx零禁忌冲突。
- 行动：无
- 证据：apps/api/healthpick_api/chat/pipeline.py, tests/api/test_chat_sse.py, docs/evidence/phase-07-p07-02-safety-primary-pytest.xml, evals/reports/release-v1.1-20260822T132040911243+0800/summary.json

## ISSUE-062 · RESOLVED

- 发现时间：2026-08-22T13:38:00+08:00
- 阶段/任务：PHASE-07 / P07-03
- 严重度：medium；阻断最终验收：False
- 现象：启用备用模型时空字符串API密钥可通过配置构造，错误会延迟到首个真实请求。
- 原因：配置校验只识别None和普通字符串，未展开SecretStr后检查空白值。
- 解决/缓解：主备模型密钥均在边界处展开后执行空值校验，并增加空主密钥和空备用密钥回归测试。
- 行动：无
- 证据：apps/api/healthpick_api/config.py, apps/api/healthpick_api/providers/factory.py, tests/api/test_providers.py, docs/evidence/phase-07-p07-03-pytest.xml

## ISSUE-063 · RESOLVED

- 发现时间：2026-08-22T13:50:00+08:00
- 阶段/任务：PHASE-07 / P07-04
- 严重度：low；阻断最终验收：False
- 现象：透明度卡直接显示内部切换策略枚举，长词换行且不利于评委快速理解。
- 原因：Web把API稳定枚举值原样当作用户文案展示。
- 解决/缓解：保留API枚举作为机器合同，Web映射为可重试故障/无效响应中文说明并增加组件断言。
- 行动：无
- 证据：apps/web/src/components/chat-workspace.tsx, apps/web/src/components/chat-workspace.test.tsx, docs/evidence/phase-07-p07-04-web-vitest.xml

## ISSUE-064 · RESOLVED

- 发现时间：2026-08-22T14:02:00+08:00
- 阶段/任务：PHASE-07 / P07-05
- 严重度：low；阻断最终验收：False
- 现象：Playwright locator点击异步消失的停止按钮后重定位到发送按钮，制造第二次提交和落库假象。
- 原因：locator.click在元素被React异步替换时执行可操作性重试；后继发送按钮占据同一交互位置，但拥有新请求ID。
- 解决/缓解：核对实际按钮type=button，改用浏览器原生DOM click进行停止验收；桌面移动连续两次均只有cancel 204且PostgreSQL零轮次。
- 行动：无
- 证据：docs/evidence/phase-07-p07-05-browser.md, docs/evidence/phase-07-p07-05-cancellation.json, output/playwright/phase-07-p07-05-stopped-mobile.png

## ISSUE-065 · RESOLVED

- 发现时间：2026-08-22T14:24:19+08:00
- 阶段/任务：PHASE-08 / P08-01
- 严重度：medium；阻断最终验收：False
- 现象：首轮提交候选密钥扫描发现两份PostgreSQL证据和账号smoke生成端保存完整本地数据库URI。
- 原因：运行证据复用了连接字符串作为环境标识，没有把审计目标和连接凭据分离。
- 解决/缓解：证据和生成端只保留不含账号口令的database_target；扫描器覆盖跟踪与未跟踪候选且永不回显值，最终438文件零发现。
- 行动：无
- 证据：scripts/audit_repository_security.py, scripts/smoke_account_migration.py, docs/evidence/phase-08-p08-01-secret-scan.json, docs/evidence/phase-06-p06-01-postgres.json, docs/evidence/phase-06-p06-04-postgres.json

## ISSUE-066 · RESOLVED

- 发现时间：2026-08-22T14:31:00+08:00
- 阶段/任务：PHASE-08 / P08-01
- 严重度：low；阻断最终验收：False
- 现象：pip-audit不识别uv.lock为原生锁文件，安装式审计又因临时Python3.12与项目Python3.13 wheel哈希集合不同失败。
- 原因：审计工具锁文件支持和临时解释器平台与项目uv锁定语义不一致，不代表已确认的包篡改或漏洞。
- 解决/缓解：从uv.lock执行frozen no-dev导出，记录锁与导出哈希，使用不安装模式审计全部32个精确生产依赖，零已知漏洞。
- 行动：无
- 证据：docs/evidence/phase-08-p08-01-quality.md, docs/evidence/phase-08-p08-01-dependency-audit.json, docs/evidence/phase-08-p08-01-python-audit.json

## ISSUE-067 · RESOLVED

- 发现时间：2026-08-22T14:39:00+08:00
- 阶段/任务：PHASE-08 / P08-02
- 严重度：medium；阻断最终验收：False
- 现象：新空卷已正确登记001至005迁移，但Compose生命周期smoke报migration registry incomplete。
- 原因：Phase05脚本把期望版本硬编码为001至004，后续005账号迁移加入后断言未随仓库真值更新。
- 解决/缓解：从infra/migrations合法文件名动态生成期望版本，并在数据库生命周期测试中断言与discover_migrations一致；新卷和重启后均通过。
- 行动：无
- 证据：scripts/smoke_compose_lifecycle.py, tests/test_database_lifecycle.py, docs/evidence/phase-08-p08-02-compose.json

## ISSUE-068 · RESOLVED

- 发现时间：2026-08-22T14:41:14+08:00
- 阶段/任务：PHASE-08 / P08-02
- 严重度：low；阻断最终验收：False
- 现象：P08专用Compose证据路径仍写入PHASE-05-P05-04-COMPOSE标识，内容与归属不一致。
- 原因：可复用生命周期脚本把evidence_id硬编码为首次创建阶段。
- 解决/缓解：增加可选evidence-id参数并保留旧默认兼容，P08最终证据重生成为PHASE-08-P08-02-CLEAN-COMPOSE。
- 行动：无
- 证据：scripts/smoke_compose_lifecycle.py, docs/evidence/phase-08-p08-02-compose.json

## ISSUE-069 · RESOLVED

- 发现时间：2026-08-22T14:46:00+08:00
- 阶段/任务：PHASE-08 / P08-03
- 严重度：high；阻断最终验收：False
- 现象：README停留在Phase04，AI_USAGE含多处待填写，缺少许可证和面向用户隐私/安全入口，env样例暗示未实现的Cookie和自动保留能力。
- 原因：规划文档没有随账号、PostgreSQL、Provider和Phase08实现同步，配置样例保留了未来字段，形成实现与公开声明漂移。
- 解决/缓解：按迁移和运行代码重写发布文档，删除未消费配置，补MIT/第三方边界/隐私/安全/六条数据路径，并增加七项机器防漂移门和密钥复扫。
- 行动：无
- 证据：README.md, docs/AI_USAGE.md, LICENSE, PRIVACY.md, SECURITY.md, THIRD_PARTY_NOTICES.md, docs/release-data-map.json, scripts/validate_release_docs.py, docs/evidence/phase-08-p08-03-doc-validation.json

## ISSUE-070 · RESOLVED

- 发现时间：2026-08-22T14:56:30+08:00
- 阶段/任务：PHASE-08 / P08-04
- 严重度：medium；阻断最终验收：False
- 现象：首次自动演练认为S3应完全不持久化，并与正常三轮共用会话，因安全记录存在而失败。
- 原因：混淆不可进入后续模型上下文与不可见/不落库；实际S3会清空当前生成上下文并保留context_eligible=false安全记录。
- 解决/缓解：使用独立安全会话，分别断言主演示三轮保持、安全会话一条可见记录且不可进入生成上下文；连续两次演练通过。
- 行动：无
- 证据：scripts/run_demo_rehearsal.py, docs/demo/DEMO_SCRIPT_6MIN.md, docs/evidence/phase-08-p08-04-rehearsal-01.json, docs/evidence/phase-08-p08-04-rehearsal-02.json

## ISSUE-071 · RESOLVED

- 发现时间：2026-08-22T15:08:00+08:00
- 阶段/任务：PHASE-08 / P08-05
- 严重度：high；阻断最终验收：False
- 现象：RC1匿名克隆后黄金数据集哈希与manifest不一致，但源工作区校验通过。
- 原因：生成器按Windows默认写入CRLF，Git检出策略将跟踪文件规范化为LF，manifest记录了提交前工作树字节而非提交后字节。
- 解决/缓解：生成器固定newline为LF，回归断言禁止CRLF，重生v1和v1.1 manifest；历史评测报告保留原哈希以维持审计真实性。
- 行动：无
- 证据：scripts/build_release_golden.py, tests/test_release_golden_dataset.py, evals/golden/release-golden-v1.manifest.json, evals/golden/release-golden-v1.1.manifest.json

## ISSUE-072 · RESOLVED

- 发现时间：2026-08-22T15:20:00+08:00
- 阶段/任务：PHASE-08 / P08-05
- 严重度：high；阻断最终验收：False
- 现象：RC2匿名冷克隆执行npm run typecheck时缺少Next生成的LayoutProps，源工作区因已有.next缓存而误通过。
- 原因：typecheck脚本直接运行tsc，隐式依赖next dev或build预先生成路由类型。
- 解决/缓解：typecheck先执行next typegen再运行tsc；RC3与RC4匿名冷克隆在无.next缓存条件下通过类型检查和生产构建。
- 行动：无
- 证据：apps/web/package.json, control/project-control.yaml

## ISSUE-073 · RESOLVED

- 发现时间：2026-08-22T15:42:00+08:00
- 阶段/任务：PHASE-08 / P08-02, P08-05
- 严重度：medium；阻断最终验收：False
- 现象：ECS首次部署时Docker Hub拉取Caddy超时，且用户要求服务器只接受镜像、不得接收源码或构建上下文。
- 原因：服务器外网镜像仓库链路不稳定，源码构建也不符合已确认的交付边界。
- 解决/缓解：可信本机构建或拉取四镜像，按应用与基础设施分卷docker save，双端SHA-256一致后docker load；加载完成删除服务器归档并确认源码文件计数为0，启动强制--no-build。
- 行动：无
- 证据：docs/deployment/ecs-production.md, docs/evidence/phase-08-p08-02-ecs-production.json

## ISSUE-074 · RESOLVED

- 发现时间：2026-08-22T16:03:00+08:00
- 阶段/任务：PHASE-08 / P08-02, P08-06
- 严重度：high；阻断最终验收：False
- 现象：Caddy已监听公网80/443，但Let’s Encrypt HTTP-01和TLS-ALPN-01均从公网连接超时，HTTPS证书未签发。
- 原因：ECS系统firewalld未运行且iptables INPUT为ACCEPT，阻断点定位为阿里云安全组尚未放行TCP 80/443。
- 解决/缓解：用户在ECS安全组放行TCP 80和443后，Let’s Encrypt短期IP证书签发成功；公网首页、健康检查和Chromium真实链路全部通过。UDP 443仅用于HTTP/3。
- 行动：无
- 证据：docs/evidence/phase-08-p08-02-ecs-production.json, docs/evidence/phase-08-p08-02-ecs-public-browser.json

## ISSUE-075 · RESOLVED

- 发现时间：2026-08-22T16:06:00+08:00
- 阶段/任务：PHASE-08 / P08-02
- 严重度：high；阻断最终验收：False
- 现象：生产API首个真实问答返回provider_rejected_request，绕过应用直连通用DashScope端点得到401 invalid_api_key。
- 原因：用户密钥为sk-sp开头的Token Plan专属Key，却配置了按量付费通用DashScope Base URL；两类密钥和端点不可混用。
- 解决/缓解：不回显密钥地分别探测Token Plan与Coding Plan端点；前者以qwen3.7-plus返回200、后者401。生产改用北京Token Plan专属OpenAI兼容端点并仅重建API，三路由、S3、历史与清理演练全部通过。
- 行动：无
- 证据：infra/ecs.env.example, docs/deployment/ecs-production.md, docs/evidence/phase-08-p08-02-ecs-production.json

## ISSUE-076 · RESOLVED

- 发现时间：2026-08-22T16:24:00+08:00
- 阶段/任务：PHASE-08 / P08-02
- 严重度：high；阻断最终验收：False
- 现象：临时sslip.io域名在Alibaba Cloud中国大陆节点返回未备案拦截页，应用容器本身正常。
- 原因：中国大陆公网域名接入触发ICP备案校验，临时域名没有对应备案。
- 解决/缓解：改为Let’s Encrypt支持的公网IP短期证书，以https://106.14.13.139直接提供服务，不再依赖未备案域名。
- 行动：无
- 证据：infra/ecs.env.example, infra/caddy/Caddyfile, docs/evidence/phase-08-p08-02-ecs-production.json

## ISSUE-077 · RESOLVED

- 发现时间：2026-08-22T16:36:00+08:00
- 阶段/任务：PHASE-08 / P08-02
- 严重度：medium；阻断最终验收：False
- 现象：公网IP证书已签发，但不发送SNI的IP客户端握手时Caddy无法选择证书。
- 原因：IP字面量客户端不保证在ClientHello中发送SNI，Caddy缺少无SNI时的默认证书选择。
- 解决/缓解：在Caddy全局配置中设置default_sni为PUBLIC_HOST；Windows curl、Python和Chromium均通过受信HTTPS。
- 行动：无
- 证据：infra/caddy/Caddyfile, tests/test_production_deployment.py, docs/evidence/phase-08-p08-02-ecs-public-browser.json

## ISSUE-078 · RESOLVED

- 发现时间：2026-08-22T17:44:39+08:00
- 阶段/任务：PHASE-04 / P04-02, DATA-03
- 严重度：medium；阻断最终验收：False
- 现象：首版核心规则验证把规则所在整页的其他缺字符号也算作本规则缺字，导致5条逐字段核对无误的核心规则被误报。
- 原因：页面级OCR质量标志与规则级结构化字段风险混用；同页其他段落的缺字不代表已复核规则字段含缺字。
- 解决/缓解：放行门改为校验规则级unknown_glyph、完整授权复核记录和精确7条白名单；含未知符号的具体规则继续隔离。
- 行动：ACTION-06, ACTION-07
- 证据：scripts/validate_knowledge.py, docs/evidence/action-06-core-rule-review.json, docs/evidence/phase-02-knowledge-validation.json

## ISSUE-079 · RESOLVED

- 发现时间：2026-08-22T19:35:54+08:00
- 阶段/任务：PHASE-08 / DATA-06, P08-07
- 严重度：low；阻断最终验收：False
- 现象：ACTION-06 关闭后缺字隔离审计仍只接受旧状态 review_required，导致实际隔离正确但报告为 FAIL。
- 原因：审计状态断言没有随最终处置模型从待复核更新为驳回。
- 解决/缓解：门禁改为精确校验 6 条模糊规则全部为 rejected；8 个 Chunk 未加载、6 条规则驳回和专项回归全部 PASS。
- 行动：无
- 证据：scripts/audit_unknown_glyph_exclusion.py, docs/evidence/action-07-unknown-glyph-exclusion.json, tests/test_knowledge_artifacts.py

## ISSUE-080 · RESOLVED

- 发现时间：2026-08-22T19:44:40+08:00
- 阶段/任务：PHASE-08 / P08-02, P08-07
- 严重度：low；阻断最终验收：False
- 现象：rc7 首次切换前复制运行描述文件时按发布根目录寻找 Caddyfile，文件不存在而安全停止。
- 原因：Caddyfile 实际位于 infra/caddy/Caddyfile，部署命令使用了错误相对路径。
- 解决/缓解：切换前只读确认目录结构，按真实嵌套路径复制并校验恰好 3 个描述文件、源码文件为 0；rc7 和最终 rc8 均无构建健康切换。
- 行动：无
- 证据：docs/deployment/ecs-production.md, docs/evidence/phase-08-rc8-final-deployment.json

## ISSUE-081 · RESOLVED

- 发现时间：2026-08-22T20:32:00+08:00
- 阶段/任务：PHASE-08 / P08-05, P08-07
- 严重度：low；阻断最终验收：False
- 现象：禁用Git凭据助手后匿名查询远端RC8标签要求认证，不能把私有仓库复验写成匿名克隆。
- 原因：GitHub origin保持私有可见性，匿名访问不在当前授权范围。
- 解决/缓解：不擅自公开源码；改用现有授权凭据从远端RC8标签创建全新浅克隆，提交、tag、tree、锁定安装和全部质量门一致通过；提交时如需评委读源码须授予访问权或上传归档。
- 行动：无
- 证据：docs/evidence/phase-08-p08-05-release-candidate.json, docs/evidence/phase-08-p08-05-quality.md

## ISSUE-082 · RESOLVED

- 发现时间：2026-08-22T20:39:00+08:00
- 阶段/任务：PHASE-08 / P08-07
- 严重度：low；阻断最终验收：False
- 现象：最终公网健康探针首次请求非契约路径/health并返回404。
- 原因：健康路径记忆错误；Caddy与OpenAPI实际公开/healthz。
- 解决/缓解：只读核对Caddyfile和OpenAPI后改探/healthz，返回production、llm real和database schema ready；HTTPS根页及评测摘要同时通过。
- 行动：无
- 证据：infra/caddy/Caddyfile, packages/shared/openapi/healthpick.openapi.json, docs/evidence/final-public-probe.json

## ISSUE-083 · RESOLVED

- 发现时间：2026-08-23T08:31:00+08:00
- 阶段/任务：PHASE-10 / RC11-01
- 严重度：high；阻断最终验收：False
- 现象：三句赛题自然诉求能进入A/B聊天链路，但结构化方案卡仍依赖用户先手工选择健康档案目标。
- 原因：自然语言路由与档案推荐服务之间没有受控目标映射。
- 解决/缓解：新增单目标确定性推断，只形成带理由的未落档候选；同句多目标不猜测，档案仍由用户控制。
- 行动：无
- 证据：tests/api/test_recommendation.py, tests/api/test_chat_sse.py, docs/evidence/phase-10-rc11-local-gates.json

## ISSUE-084 · RESOLVED

- 发现时间：2026-08-23T08:34:00+08:00
- 阶段/任务：PHASE-10 / RC11-02
- 严重度：high；阻断最终验收：False
- 现象：赛题明确用例“我尿酸高”未命中高嘌呤过滤；血压偏高和未明确家族病史表达也不完整。
- 原因：路由、检索和安全词表只覆盖部分同义词及固定词序。
- 解决/缓解：同步补齐受控别名；家族病史只进入专业级一般信息和澄清边界，不推断具体疾病。
- 行动：无
- 证据：tests/api/test_retrieval.py, tests/api/test_safety.py

## ISSUE-085 · RESOLVED

- 发现时间：2026-08-23T08:37:00+08:00
- 阶段/任务：PHASE-10 / RC11-02, RC11-03
- 严重度：high；阻断最终验收：False
- 现象：疾病或过敏触发后结构化推荐直接阻断，没有展示过滤后的食材替换，也没有赛题指定的方案使用提示原句。
- 原因：推荐服务在加载规则和执行替换前提前返回安全阻断。
- 解决/缓解：保持primary为空、S1/S2个体化目标关闭；新增不含精确数值的safe_alternative，并在API回答和Web卡片强制显示指定提示。
- 行动：无
- 证据：tests/api/test_recommendation.py, tests/api/test_chat_sse.py, apps/web/src/components/chat-workspace.test.tsx

## ISSUE-086 · RESOLVED

- 发现时间：2026-08-23T08:51:00+08:00
- 阶段/任务：PHASE-10 / RC11-04
- 严重度：medium；阻断最终验收：False
- 现象：家族病史的受控免责声明片段已获得提示加分，但仍被另一普通关键词片段以小幅分差挤出首位。
- 原因：人工核验提示固定权重25不足以压过真实查询中的BM25累计分。
- 解决/缓解：提示权重提高到50，并用全部策划主证据的首位断言回归；A/B/C边界不变。
- 行动：无
- 证据：apps/api/healthpick_api/retrieval/keyword.py, tests/api/test_retrieval.py

## ISSUE-087 · RESOLVED

- 发现时间：2026-08-23T08:56:00+08:00
- 阶段/任务：PHASE-10 / RC11-04
- 严重度：low；阻断最终验收：False
- 现象：首版把“痛风/高尿酸”也升级为禁忌路由，导致冻结黄金集POP-GOUT-02路由不一致。
- 原因：为修“尿酸高”词序时扩大了不必要的既有路由范围。
- 解决/缓解：撤回痛风和高尿酸的路由变化，仅保留赛题缺失词序；SafetyService对两者的S1和高嘌呤过滤继续生效，全量测试恢复通过。
- 行动：无
- 证据：tests/fixtures/phase04_safety_golden.jsonl, tests/api/test_safety_golden.py

## ISSUE-088 · RESOLVED

- 发现时间：2026-08-23T09:20:00+08:00
- 阶段/任务：PHASE-10 / RC11-05
- 严重度：medium；阻断最终验收：False
- 现象：本地完整 Dockerfile 构建连续在 Docker Hub 的 Dockerfile frontend 和 Python 基础镜像元数据请求处 TLS handshake timeout。
- 原因：Docker Hub 外部链路不可用；Docker 引擎、GHCR 元数据和本地已验收 RC10 linux/amd64 镜像正常。
- 解决/缓解：本轮依赖文件未变，改从 RC10 API/Web 镜像增量覆盖当前 API 源码和本地生产 Web standalone 产物，显式固定 linux/amd64；完成镜像健康、功能 smoke、双端哈希和公网验收，未改代理/证书/Docker 全局配置。
- 行动：网络恢复后可按原 Dockerfile做可选完整重建，不阻断当前短期比赛运行。
- 证据：docs/evidence/phase-10-rc11-05-public-acceptance.json

## ISSUE-089 · RESOLVED

- 发现时间：2026-08-23T09:42:00+08:00
- 阶段/任务：PHASE-10 / RC11-05
- 严重度：low；阻断最终验收：False
- 现象：首次 RC11 API 镜像 smoke 启动即退出。
- 原因：smoke 命令误用不存在的 LLM_MODE=stub 和 CONVERSATION_STORE_MODE=memory；项目合法值为 mock 和 ephemeral，Pydantic 按设计启动前拒绝错误配置。
- 解决/缓解：不修改应用，改用合法的隔离 smoke 参数后健康检查与尿酸安全替换功能均通过；生产继续使用原有 real/postgres 配置。
- 行动：无
- 证据：docs/evidence/phase-10-rc11-05-public-acceptance.json
