# rc6 核心推荐规则公网部署验收

- 发布：`v0.1.0-rc6` / `62de15c7d7d553b96b4984f425d4f78dba1a50b4`
- 公网入口：`https://106.14.13.139`
- 部署方式：仅上传 API/Web Docker 镜像和 3 个部署描述文件，未上传应用源码
- 容器：API、Web、PostgreSQL、Caddy 全部 healthy/running

## 验收结果

| 检查 | 结果 |
|---|---|
| HTTPS 健康检查及百炼千问真实模式 | PASS |
| 减脂、增肌、稳糖确定性方案 | 3/3 `ready` |
| 缺目标与过敏约束 | fail-closed |
| 真实 Chromium 方案卡 | PASS |
| 浏览器控制台 | 0 error / 0 warning |

公网减脂卡可见 300–500 kcal 每日缺口、1.2–1.6 g/kg 蛋白质、饮水、进食顺序、三步行动、替换组和 A/B 页码依据。核心 7 条已放行；其余 73 条仍隔离，ACTION-06 保持开放。

截图：`output/playwright/phase-08-rc6-public-reviewed-plan-1440x1000.png`
