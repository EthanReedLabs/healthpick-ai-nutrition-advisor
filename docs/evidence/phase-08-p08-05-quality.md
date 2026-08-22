# P08-05 RC8 Release 候选冻结与远端干净克隆

## 结论

P08-05 以 `PASS` 完成。应用提交 `6e56b96f7d5ac4ffd306cdcedabfac7366034f44` 的 annotated tag `v0.1.0-rc8` 已推送远端；从该远端标签新建的授权浅克隆，其 HEAD、tag commit 和 tree 与候选完全一致。克隆内重新执行 Python/Web 测试、静态检查、类型检查、生产构建、文档校验、密钥扫描、知识校验和控制面结构审计，全部通过。

## 冻结标识

- 应用 Commit：`6e56b96f7d5ac4ffd306cdcedabfac7366034f44`
- Tag：`v0.1.0-rc8`
- Annotated tag object：`ee2c6c5fee5e4ed4ad78af4977e04295ed4e4ffa`
- Tree：`cc45e0163bdb489cec1476efe084fc805d8cf9ae`
- 远端证据分支 Commit：`bb67e9c7cb2535a65546e824638c43f29c1a5d78`
- 干净克隆：`../healthpick-rc8-clean-20260822-2028`

## 独立质量门

| 门 | 结果 |
|---|---:|
| Python | 261 PASS |
| Web Vitest | 30 PASS |
| Ruff / ESLint | PASS / PASS |
| TypeScript / Next production build | PASS / PASS |
| Release 文档校验 | 7 PASS，0 error |
| 仓库密钥扫描 | 520 files，0 finding |
| 控制面结构审计 | PASS，0 error |
| Git 检出时跟踪区 | clean |
| RC8 tag/commit/tree | 远端与克隆一致 |

## ECS 提交映射

服务器 `current` 指向 `/opt/healthpick/releases/6e56b96f7d5ac4ffd306cdcedabfac7366034f44`。该目录只含 `compose.yaml`、`compose.production.yaml`、`infra/caddy/Caddyfile` 三个运行描述文件；使用 rc8 镜像执行 `up -d --wait --no-build` 后全部容器健康，公网首页和健康检查均返回 200，模型为真实 `qwen3.7-plus`。纯镜像归档 SHA-256 为 `5FBBF5BC1F89F1F0785C3D21C59ABA21D951F2D5D81351D4385A8498F59B3D51`。

## 私有仓库边界

禁用 Git 凭据助手后的只读远端查询返回认证必需，证明仓库当前为私有；没有擅自改为公开。最终复现采用现有授权凭据进行远端干净克隆。若比赛平台要求评委直接读取源码，参赛者需在实际提交时授予仓库访问权或上传源码归档；这不影响 RC8 commit/tag/tree 的一致性结论。

完整机器可读证据见 `docs/evidence/phase-08-p08-05-release-candidate.json`。
