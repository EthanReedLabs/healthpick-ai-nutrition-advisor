# P03-06 Web 质量门禁记录

- 日期：2026-08-21
- Next.js：16.3.2；React：19.2.8；TypeScript：5.x；Tailwind：4.x
- `npm ls eslint`：PASS，依赖树统一为 ESLint 9.39.5
- `npm run lint`：PASS
- `npm run typecheck`：PASS
- `npm test`：PASS，1 个文件、4 个组件测试（含 SSE final 解析）
- `npm run build`：PASS，主页静态预渲染成功
- `npm audit --audit-level=high`：PASS，0 vulnerabilities
- OpenAPI 类型：由 `packages/shared/openapi/healthpick.openapi.json` 生成至 `apps/web/src/lib/api-schema.d.ts`
- 组件测试报告：`docs/evidence/phase-03-web-vitest.xml`

说明：Next 16.3.2 的 ESLint 插件链尚不接受 ESLint 10，因此固定兼容的 9.39.5。其 npm 弃用提示登记为 ISSUE-014，不影响当前构建，但必须在 Next 插件链支持后升级并复验。
