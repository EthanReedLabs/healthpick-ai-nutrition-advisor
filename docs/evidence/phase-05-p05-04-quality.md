# P05-04 Compose、迁移与种子质量报告

## 结论

`P05-04` 达到全部计划门槛，可以关闭为 `passed`。本地全栈现在按 PostgreSQL 健康、迁移完成、种子完成、API 健康、Web 启动的硬依赖链复现；空库、已有库、重复启动和服务重启均通过真实验收。

## 实现边界

- `migrate_database.py` 按三位版本号执行 SQL，以 canonical LF 内容计算 SHA-256 并写入 `schema_migrations`；历史库仅在结构全部存在时登记 baseline，部分结构或校验和变化会拒绝启动。
- `seed_database.py` 在事务内验证 A/B/C 清单、源哈希和资料 C 路由隔离，执行 upsert 与陈旧行清理，并强制校验 3/18/67/31/37/12 的精确计数。
- Compose 不再使用只在空卷首次执行的 `/docker-entrypoint-initdb.d`；迁移和种子改为显式 one-shot 服务，失败时 API 不会启动。
- API/Web 使用非 root 用户、只读根文件系统和 `no-new-privileges`；Web 采用 Next standalone 生产产物。
- Compose 应用覆盖统一使用 `COMPOSE_*` 命名空间，避免部署 `.env` 污染本地 Ollama 模型和端点。

## 质量结果

| 检查 | 结果 | 证据 |
|---|---:|---|
| Compose 配置展开 | PASS | `docker compose config --quiet` |
| 生命周期专项测试 | 5/5 PASS | `tests/test_database_lifecycle.py` |
| Python 全量测试 | 193/193 PASS | `docs/evidence/phase-05-p05-04-pytest.xml` |
| Web 全量测试 | 18/18 PASS | `docs/evidence/phase-05-p05-04-web-vitest.xml` |
| Ruff / format | PASS / 138 files | 本次质量门输出 |
| ESLint / TypeScript / Next production build | PASS | 本次质量门输出 |
| 空库迁移与三次幂等 seed | PASS | `docs/evidence/phase-05-p05-04-compose.json` |
| 真实 Ollama 问答及 A/B 来源隔离 | PASS | `docs/evidence/phase-05-p05-04-compose.json` |
| PostgreSQL/API/Web 重启后数据保留 | PASS | `docs/evidence/phase-05-p05-04-compose.json` |
| API/Web 非 root、只读、健康 | PASS | 本次 `docker inspect` 输出 |

## 问题闭环

- `ISSUE-038`：旧 Compose 只有 PostgreSQL，迁移依赖首次空卷初始化且没有 seed/API/Web；已改为五服务有序编排。
- `ISSUE-039`：API 运行时导入的 `httpx2` 被放在 dev 依赖，生产镜像启动即退出；已移入运行依赖并更新锁文件。
- `ISSUE-040`：根 `.env` 的部署模型名覆盖 Compose 本地默认模型并导致 502；已改为 `COMPOSE_*` 隔离变量。
- `ISSUE-041`：生命周期 smoke 把导入成功状态误写为 `success`，造成假失败；已与数据库枚举 `passed` 对齐并重跑。

P05-04 无残余行动。隔离验收卷保留以便复核，测试服务在取证后停止；正常本地开发栈不受影响。

## 沉淀候选

1. 迁移校验和应基于统一行尾的 canonical bytes，并把已发布迁移视为不可变历史，避免 Windows/容器工作区产生假漂移。
2. 生产镜像必须用 `--no-dev` 构建并真实启动，才能发现“运行时依赖误放开发组”这类本机测试掩盖的问题。
3. Compose 会自动读取根 `.env`；本地编排和部署共享仓库时，应用覆盖变量应使用独立命名空间，避免模型、端点和安全模式被静默污染。
