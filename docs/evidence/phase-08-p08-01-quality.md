# P08-01 全回归、性能与安全审计

## 结论

P08-01 以 `PASS` 完成。254 项 Python、30 项 Web、Ruff、Phase 07 真实 72 用例 80 轮性能/安全门、438 个提交候选文件密钥扫描、JavaScript 和 Python 依赖漏洞审计全部通过。

## 验收结果

| 门 | 结果 | 证据 |
|---|---:|---|
| Python 全回归 | 254/254 PASS | `docs/evidence/phase-08-p08-01-pytest.xml` |
| Web 全回归 | 30/30 PASS | `docs/evidence/phase-08-p08-01-web-vitest.xml` |
| Python 静态质量 | PASS | Ruff 全仓检查 |
| 真实性能 | P95 2814ms PASS | `evals/reports/release-v1.1-20260822T132040911243+0800/summary.json` |
| 医疗/来源/异常安全 | 9/9 冻结门 PASS | 同上；高风险 100%、泄漏 0、禁忌冲突 0、5xx 0 |
| 提交候选密钥扫描 | 438 files / 0 findings | `docs/evidence/phase-08-p08-01-secret-scan.json` |
| JavaScript 漏洞审计 | 0 vulnerabilities | `npm audit --audit-level=high`；依赖汇总 JSON |
| Python 漏洞审计 | 32 dependencies / 0 vulnerabilities | `docs/evidence/phase-08-p08-01-python-audit.json` |

## 密钥审计边界

- 扫描 `git tracked + untracked non-ignored`，覆盖当前尚未提交的实现和证据，而非只扫描历史 commit。
- 检测私钥容器、私钥正文、AWS/GitHub/OpenAI/Slack token、数据库 URI 凭据和 secret/password/token 赋值。
- 输出只含文件、行号与规则，永不回显候选值；二进制文件检查位置与文件类型。
- 明确允许 `.env.example` 占位、Compose 环境插值和 scripts/tools 中的 loopback 开发默认连接；证据和其他目录仍不允许完整连接凭据。

## 问题与解决

- ISSUE-065：首轮扫描发现两份 PostgreSQL 证据及账号 smoke 生成端保留完整本地 URI。证据改为 `database_target`，生成端同步修复，最终 438 文件零发现。
- ISSUE-066：pip-audit 不把 `uv.lock` 识别为其原生 lock，安装式审计又用 CPython 3.12 选择了项目 Python 3.13 哈希集合之外的 wheel。改为 `uv export --frozen --no-dev` 得到完整精确 pin，再用不安装模式审计全部 32 个生产依赖，零漏洞。
- Ruff 曾提示缓存文件写入拒绝访问，属于既有 ISSUE-009；静态检查本身通过，未重复调查宿主环境。

## 沉淀候选

秘密扫描必须覆盖即将提交的未跟踪文件，并默认禁止把完整连接 URI写入验收证据；审计工具与锁文件格式不兼容时，应从原锁无更新导出精确全依赖集合，记录哈希后执行不安装漏洞查询，不能把“无法解析”误写成“零漏洞”。
