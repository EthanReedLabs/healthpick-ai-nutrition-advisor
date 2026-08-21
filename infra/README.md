# Infrastructure

- `docker/`：镜像和 Compose 相关配置；
- `migrations/`：数据库结构与版本迁移。

目标交付形态是公网 HTTPS 演示环境与 Docker Compose 本地复现并存。任何部署配置不得包含真实 Secret；生产迁移必须先在空库和已有数据副本上验证。

