# ECS 生产部署与回滚

目标环境：Alibaba Cloud Linux 3，公网入口 `https://106.14.13.139`，应用模型为北京地域阿里云百炼 Token Plan `qwen3.7-plus`。服务器执行纯镜像部署，不接收应用源码，也不执行镜像构建。

## 安全边界

- ECS 入方向只向公网开放 `80/tcp`、`443/tcp`；`22/tcp` 仅允许可信管理 IP，`443/udp` 仅在需要 HTTP/3 时开放。数据库、API、Web 的宿主端口只绑定 `127.0.0.1`。
- 出方向至少允许 DNS（`53/udp`/`53/tcp`）和 `443/tcp`，供百炼调用与 ACME 续期使用；不得为方便调试而开放全部入方向。
- `/opt/healthpick/shared/production.env` 权限必须为 `0600`；禁止提交、打印或放入运行证据。
- 百炼密钥独立保存在 `/opt/healthpick/shared/bailian.env`，权限必须为 `0600`。`sk-sp-` Token Plan Key 必须使用 `https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1`，不得与通用 DashScope 或 Coding Plan 端点混用。
- 每次发布使用独立的 `releases/<commit>` 目录；`current` 只作为可回滚软链接。
- Caddy 自动申请与续期 TLS 证书，证书状态和公网健康检查是发布门的一部分。
- 中国内地 ECS 会阻断未备案域名的 Web 访问；本项目不再使用 `sslip.io`，而是使用 Let’s Encrypt `shortlived` profile 为公网 IP 申请约六天有效期的受信证书。Caddy 数据卷必须持久化并持续监测续期。
- 服务器只接收经哈希核验的镜像归档，以及 `compose.yaml`、`compose.production.yaml`、`Caddyfile` 等最小运行描述文件；禁止上传仓库归档或 Docker build context。

## 安装基础环境

按阿里云 Alibaba Cloud Linux 3 官方流程安装 Docker CE、containerd、Buildx 与 Compose 插件，并启用 Docker 服务。该步骤只执行一次，执行前必须取得服务器软件和服务变更批准。

## 发布

1. 在可信构建机从已通过匿名克隆复验的 Release tag 构建 API/Web 镜像；基础镜像也在构建机拉取并固定版本。
2. 使用 `docker save` 导出应用镜像和基础镜像归档，记录每个归档的 SHA-256；上传到 `/opt/healthpick/incoming/` 后在服务器复算并比对。
3. 服务器执行 `docker load`，确认 API、Web、PostgreSQL/pgvector、Caddy 四个镜像均存在；加载完成后删除服务器上的传输归档。
4. 只上传最小运行描述文件到新的 `releases/<commit>`；检查目录中不存在 `.py`、`.ts`、`.tsx`、`package.json`、`pyproject.toml` 等应用源码。
5. 从 `infra/ecs.env.example` 生成服务器 `production.env`，在服务器端生成随机数据库密码；百炼 Key 单独写入 `bailian.env`，两个文件均设置 `chmod 600`。
6. 依次运行，两个环境文件的后者只提供密钥；所有启动命令强制 `--no-build`：

```bash
docker compose -p healthpick-prod \
  --env-file /opt/healthpick/shared/production.env \
  --env-file /opt/healthpick/shared/bailian.env \
  -f compose.yaml -f compose.production.yaml config --quiet
docker compose -p healthpick-prod \
  --env-file /opt/healthpick/shared/production.env \
  --env-file /opt/healthpick/shared/bailian.env \
  -f compose.yaml -f compose.production.yaml \
  up -d --wait --no-build
```

7. 验收 HTTPS、API 健康、真实千问响应、迁移版本、seed 精确计数、容器健康、重启持久化与公开端口；发布证据只记录密钥类型和端点类别，不记录密钥值。

## 回滚

若新版本健康检查失败，不删除新目录或数据卷：把 `current` 软链接切回上一已知良好 release，使用同一组环境文件重新执行 `docker compose up -d --wait --no-build`。数据库迁移保持只增不改；若新版本引入不可向后兼容迁移，必须使用部署前数据库备份恢复，禁止人工修改迁移校验表。
