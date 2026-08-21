# ADR-001：代码优先全栈技术路线

- 状态：已接受
- 日期：2026-08-21
- 决策人：项目参赛者

## 背景

赛题既要求知识库问答、多轮记忆和动态 LLM，也要求可交互界面、工程稳定性、用户系统、历史持久化、公网部署和本地一键运行。纯无代码平台能快速完成基础聊天，但难以提供可审计的知识隔离、引用校验、自动评测、数据库迁移和双部署证据。

## 决策

采用以下可替换、可容器化的代码优先架构：

- Web：Next.js App Router + TypeScript + Tailwind CSS；
- API：Python FastAPI + Pydantic；
- 数据库：PostgreSQL + pgvector；
- 检索：元数据硬过滤 + 精确向量检索 + 关键词/字符相似度 + RRF；
- LLM：OpenAI-compatible Provider Adapter，不在业务代码中写死厂商或模型；
- Embedding：独立 Provider Adapter，向量维度写入 manifest 并与索引绑定；
- 鉴权：先匿名会话，进阶阶段增加邮箱账户与会话迁移；
- 测试：pytest、API contract tests、Playwright E2E、离线 RAG 评测；
- 部署：公网 HTTPS 主环境 + Docker Compose 本地兜底。

## 关键取舍

1. 资料规模只有三份 PDF，默认使用精确向量检索，不急于使用 HNSW。只有数据量和实测延迟证明需要时才增加近似索引。
2. 不采用“LLM 一步完成分类、检索、推荐和安全判断”的黑盒流程。路由、禁忌、安全和引用均有确定性门禁。
3. 食材营养表和方案目标进入结构化事实表；普通说明文字进入章节 Chunk。数值类答案优先查事实表。
4. Web 与 API 分离，但共享 OpenAPI 生成的类型，避免手写重复契约。
5. 优先部署一个稳定公网版本，同时保留容器化一键运行；不把比赛成败押在单一平台。

## 选型依据

- Next.js 官方支持 Node.js server、Docker 和多种平台部署方式，适合同时提供公网与本地方案。
- FastAPI 自动生成 OpenAPI，便于联调、测试与提交架构证据。
- pgvector 官方支持精确检索、HNSW/IVFFlat 和与 PostgreSQL 全文检索组合；本项目先选择小规模精确检索以保召回。
- PostgreSQL 同时承载用户、会话、消息、引用、评测运行和向量，减少 48 小时比赛中的运维面。

## 后果

优势：工程证据完整、可控、易测试、可迁移，能够覆盖全部进阶需求。

成本：需要同时维护 TypeScript 与 Python。通过 OpenAPI 类型生成、Docker Compose 和明确服务边界控制复杂度。

## 失败降级

- 主 LLM 不可用：切换兼容 Provider；若都不可用，返回可解释的服务繁忙提示，不使用硬编码伪装模型回答。
- Embedding 不可用：临时退化为关键词/字符相似度检索，健康高风险问题仍受安全门控制。
- 公网平台故障：使用本地 Docker Compose 和录制好的演示证据。

## 官方参考

- [Next.js App Router](https://nextjs.org/docs/app)
- [Next.js 部署方式](https://nextjs.org/docs/app/getting-started/deploying)
- [FastAPI 容器部署](https://fastapi.tiangolo.com/deployment/docker/)
- [pgvector 官方仓库](https://github.com/pgvector/pgvector)
- [PostgreSQL 全文检索控制](https://www.postgresql.org/docs/current/textsearch-controls.html)

