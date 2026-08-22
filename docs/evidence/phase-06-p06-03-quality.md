# P06-03 来源透明页、模型信息与检索 Trace 验收

结论：`PASS`。透明信息和 Trace 均由当前请求、当前运行配置动态生成，不使用会失真的静态展示文案。

## 实现与边界

- 新增非敏感 `GET /v1/transparency`，公开模型、Embedding、检索、会话存储、档案持久化、证据策略及 A/B/C 允许/禁止用途；不返回密钥、令牌或数据库连接串。
- 每个命中检索的最终 SSE 事件附带结构化 Trace：公开路由、允许来源、查询词、检索/排除/候选/拒绝/返回计数、所选 Chunk、分数和命中词。
- Trace 的所选 Chunk ID 必须与最终引用 ID 完全一致，且全部位于冻结来源边界；确定性越界保护不伪造 Trace。
- Web 展示当前真实模型摘要、透明度卡片及可展开 Trace；桌面和移动复用同一服务器真值。
- 增加 `tools/start_local_api.ps1`，只给项目子进程注入本地端口、模型、数据库和 CORS 配置，避免手工重启漂移；不修改全局环境。

## 自动与真实运行证据

- API 专项 28/28，见 `phase-06-p06-03-api-pytest.xml`。
- Web 组件 26/26，TypeScript、ESLint、Next.js production build 全部通过，见 `phase-06-p06-03-web-vitest.xml`。
- OpenAPI 已导出，Web 类型已重新生成。
- 真实本地栈通过：营养路由返回 A 来源 6 引用，平台路由返回 C 来源 6 引用，越界问题走确定性保护且 Trace 为 `null`；模型/Embedding 均为 real，见 `local-real-stack-runtime.json`。
- 真实浏览器的运行态展示、Trace、响应式和控制台门禁通过，见 `phase-06-p06-03-browser.md`。
- 新启动器在独立端口 8012 返回 `llm=real`、`embedding=real`、`retrieval=keyword` 和数据库 schema ready，随后测试进程已关闭。

## 实施中发现并解决

- ISSUE-053：内部路由值 `recommendation` 被直接序列化到公开 Trace，触发 Pydantic 校验 500；改用统一 `_public_route` 映射并增加回归断言。
- ISSUE-054：手工重启遗漏项目本地模型与 CORS 环境，先导致真实烟测 503，后导致浏览器 CORS；增加统一项目启动器，并用真实 smoke、独立端口和干净浏览器复验。

## 采用的工程经验

采用 Sulde `work-model/evidence-gate-contract`：透明度与 Trace 作为可机器校验的当前作用域证据，由运行配置和本次检索结果生成，避免静态成功文案被误当验收证据。
