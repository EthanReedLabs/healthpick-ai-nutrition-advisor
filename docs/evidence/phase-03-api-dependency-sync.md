# Phase 03 API Dependency Sync

- Command: `uv sync`
- Result: `PASS`
- Python: `3.13.5`
- FastAPI: `0.141.1`
- Starlette: `1.6.0`
- Uvicorn: `0.52.4`
- Pydantic: `2.13.4`
- pydantic-settings: `2.15.0`
- TestClient transport: `httpx2 2.12.0`

## Observed issues

1. uv 无法在缓存与项目环境之间建立 hardlink，自动降级为完整文件复制；安装完成，影响仅为同步性能/磁盘复制方式，不影响包内容。
2. 首轮测试使用 `httpx 0.28.1` 时，Starlette 1.6.0 发出 TestClient 弃用警告。其包元数据和源码均要求/优先使用 `httpx2>=2.0.0`，因此开发依赖改为 `httpx2>=2,<3`。重锁后卸载 `httpx/httpcore`，安装 `httpx2/httpcore2`，同一 8 项测试无警告通过。

依赖均写入根 `uv.lock`，未安装或升级全局 Python 包。

