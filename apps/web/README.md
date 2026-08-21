# HealthPick Web

Next.js App Router + TypeScript + Tailwind 的营养问答工作台。

```powershell
# 先按 apps/api/README.md 在 127.0.0.1:8010 启动 API
Copy-Item .env.example .env.local
npm run dev -- --hostname 127.0.0.1 --port 3000
```

打开 `http://127.0.0.1:3000`。页面从 `/healthz` 读取当前 Real/Mock 模式，问答请求默认发送到 API；后端未就绪时显示稳定错误，不使用预置回复冒充模型结果。

质量门禁：

```powershell
npm run generate:types
npm run lint
npm run typecheck
npm test
npm run build
```

`src/lib/api-schema.d.ts` 必须从根目录 OpenAPI 生成，禁止手写第二份跨端协议。
