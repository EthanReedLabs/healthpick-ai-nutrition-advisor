# 问题与解决统一日志

> 真值来自 `control/project-control.yaml`。问题不删除；解决后保留原因、处理和证据。

## ISSUE-001 · OPEN

- 发现时间：2026-08-21T16:47:07+08:00
- 阶段/任务：PHASE-01 / P01-08, DATA-05, DATA-06
- 严重度：high；阻断最终验收：True
- 现象：本机没有 Docker 和 psql，数据库与 pgvector 无法运行验收。
- 原因：尚未确认
- 解决/缓解：已启用文件级降级路径，运行态仍待恢复。
- 行动：ACTION-01
- 证据：docs/evidence/phase-01-baseline-record.md, docs/evidence/phase-02-knowledge-validation.json

## ISSUE-002 · OPEN

- 发现时间：2026-08-21T16:47:07+08:00
- 阶段/任务：PHASE-01 / P01-08, P03-02, P03-07
- 严重度：high；阻断最终验收：True
- 现象：未配置真实 LLM provider/model/quota，无法证明动态模型闭环。
- 原因：尚未确认
- 解决/缓解：开发阶段允许 Mock adapter，最终必须执行脱敏真实 smoke。
- 行动：ACTION-02
- 证据：docs/evidence/phase-01-baseline-record.md

## ISSUE-003 · OPEN

- 发现时间：2026-08-21T16:47:07+08:00
- 阶段/任务：PHASE-01 / P01-08, DATA-05, P03-03, P03-07
- 严重度：high；阻断最终验收：True
- 现象：Embedding 模型和维度未知，不能建立可信生产向量索引。
- 原因：尚未确认
- 解决/缓解：先使用结构化事实与关键词检索，禁止猜测向量维度。
- 行动：ACTION-03
- 证据：docs/evidence/phase-02-knowledge-validation.json

## ISSUE-004 · OPEN

- 发现时间：2026-08-21T16:47:07+08:00
- 阶段/任务：PHASE-01 / P01-08, P08-05
- 严重度：high；阻断最终验收：True
- 现象：Git 仓库没有远端，无法完成匿名克隆和提交候选验收。
- 原因：尚未确认
- 解决/缓解：等待参赛者授权建立远端仓库。
- 行动：ACTION-04
- 证据：docs/evidence/phase-01-baseline-record.md

## ISSUE-005 · OPEN

- 发现时间：2026-08-21T16:47:07+08:00
- 阶段/任务：PHASE-01 / P01-08, P08-02, P08-06
- 严重度：high；阻断最终验收：True
- 现象：Render 账号、区域、预算和七天可用性尚未确认。
- 原因：尚未确认
- 解决/缓解：等待参赛者授权账号与可能产生费用的操作。
- 行动：ACTION-05
- 证据：docs/evidence/phase-01-baseline-record.md

## ISSUE-006 · MITIGATED

- 发现时间：2026-08-21T17:08:00+08:00
- 阶段/任务：PHASE-02 / DATA-01, DATA-03, P03-03, P03-04, P03-05, P03-07
- 严重度：high；阻断最终验收：True
- 现象：A-p02、A-p04、B-p01、B-p05、B-p07、B-p08 的原始 PDF 存在缺字符号，影响 8 个 Chunk。
- 原因：源文件渲染和文本层均缺字，不是解析器丢字。
- 解决/缓解：未猜测符号；受影响规则标记 unknown_glyph 和 review_required，并阻止生产放行。
- 行动：ACTION-07
- 证据：docs/evidence/phase-02-knowledge-validation.json, docs/evidence/phase-02-second-person-review-checklist.md

## ISSUE-007 · OPEN

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
