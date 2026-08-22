# ECS 生产部署与回滚

目标环境：Alibaba Cloud Linux 3，公网入口 `https://106-14-13-139.sslip.io`，应用模型为北京地域阿里云百炼 `qwen3.7-plus`。

## 安全边界

- ECS 安全组只开放 `22/tcp`、`80/tcp`、`443/tcp` 和 `443/udp`；数据库、API、Web 的宿主端口只绑定 `127.0.0.1`。
- `/opt/healthpick/shared/production.env` 权限必须为 `0600`；禁止提交、打印或放入运行证据。
- 每次发布使用独立的 `releases/<commit>` 目录；`current` 只作为可回滚软链接。
- Caddy 自动申请与续期 TLS 证书，证书状态和公网健康检查是发布门的一部分。

## 安装基础环境

按阿里云 Alibaba Cloud Linux 3 官方流程安装 Docker CE、containerd、Buildx 与 Compose 插件，并启用 Docker 服务。该步骤只执行一次，执行前必须取得服务器软件和服务变更批准。

## 发布

1. 从已通过匿名克隆复验的 Release tag 生成归档，不从脏工作区复制。
2. 上传到 `/opt/healthpick/incoming/`，核对 SHA-256 后解压到新的 `releases/<commit>`。
3. 从 `infra/ecs.env.example` 生成服务器 `production.env`，替换随机数据库密码与百炼 Key，并设置 `chmod 600`。
4. 依次运行：

```bash
docker compose --env-file /opt/healthpick/shared/production.env \
  -f compose.yaml -f compose.production.yaml config --quiet
docker compose --env-file /opt/healthpick/shared/production.env \
  -f compose.yaml -f compose.production.yaml build
docker compose --env-file /opt/healthpick/shared/production.env \
  -f compose.yaml -f compose.production.yaml up -d --wait
```

5. 验收 HTTPS、API 健康、真实千问响应、迁移版本、seed 精确计数、容器健康、重启持久化与公开端口。

## 回滚

若新版本健康检查失败，不删除新目录或数据卷：把 `current` 软链接切回上一已知良好 release，使用同一 `production.env` 重新执行 `docker compose up -d --wait`。数据库迁移保持只增不改；若新版本引入不可向后兼容迁移，必须使用部署前数据库备份恢复，禁止人工修改迁移校验表。
