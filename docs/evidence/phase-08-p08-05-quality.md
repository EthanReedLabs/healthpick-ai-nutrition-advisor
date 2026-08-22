# P08-05 Release 候选冻结与匿名克隆

## 结论

P08-05 以 `PASS` 完成。发布提交 `b8cd3f1ee243cbf5a83ba8019b44cb40f4152184` 已创建本地 annotated tag `v0.1.0-rc5`；匿名浅克隆的 HEAD、tag commit 和 tree 与候选完全一致，跟踪区干净。克隆内重新执行 Python/Web 测试、静态检查、类型检查、生产构建、文档校验、密钥扫描和控制面结构审计，全部通过。

## 冻结标识

- Commit：`b8cd3f1ee243cbf5a83ba8019b44cb40f4152184`
- Tag：`v0.1.0-rc5`
- Annotated tag object：`f00b7fa72305320aa9101677ea0eb11cb0766be1`
- Tree：`d4633fabcff5bd42037a45fee0aeb0d056e3c9df`
- 匿名克隆：`../healthpick-rc5-anonymous`

## 独立质量门

| 门 | 结果 |
|---|---:|
| Python | 260 PASS |
| Web Vitest | 30 PASS |
| Ruff / ESLint | PASS / PASS |
| TypeScript / Next production build | PASS / PASS |
| Release 文档校验 | 7 PASS，0 error |
| 仓库密钥扫描 | 504 files，0 finding |
| 控制面结构审计 | PASS，0 error |
| Git 跟踪区 | clean |

## ECS 提交映射

服务器 `current` 指向 `/opt/healthpick/releases/b8cd3f1ee243cbf5a83ba8019b44cb40f4152184`。该目录只含 `compose.yaml`、`compose.production.yaml`、`infra/caddy/Caddyfile` 三个运行描述文件；使用现有 rc5 镜像执行 `up -d --wait --no-build` 后全部容器健康，公网首页和健康检查均返回 200，模型模式为 real。

完整机器可读证据见 `docs/evidence/phase-08-p08-05-release-candidate.json`。
