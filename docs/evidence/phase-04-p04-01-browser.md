# P04-01 健康档案浏览器验收

- 验收日期：2026-08-21（Asia/Shanghai）
- Web：`http://127.0.0.1:3100`
- API：`http://127.0.0.1:8010`
- 页面状态：`API 在线 · Real`

## 交互结果

1. 打开“编辑健康档案”后，目标、年龄段、性别、活动水平、身高体重、饮食偏好、过敏原、医疗安全标签和不喜欢食材均可键盘访问。
2. 保存稳糖、18–44 岁、170 cm、65 kg、甲壳类海鲜过敏、高血压、香菜/苦瓜后，`POST /v1/profile/assess` 返回 200。
3. 摘要区展示服务端规范化值与 `BMI 22.5 · 系统估算`，同时展示公式 `weight_kg / (height_m ** 2)`。
4. 随后的 `POST /v1/chat/stream` 返回 200；浏览器请求体包含上述 `profile_patch`，没有姓名或自由文本疾病详情。
5. 浏览器控制台 0 error、0 warning。

## 证据

- 截图：`output/playwright/phase-04-p04-01-profile-1440x1000.png`
- 机器探针：`docs/evidence/phase-04-p04-01-runtime.json`
- OpenAPI：`packages/shared/openapi/healthpick.openapi.json`

## 尚未覆盖

P04-01 只负责档案建模、校验和传输。根据档案把风险从 S0 升级为 S1/S2、执行禁忌硬过滤和拒答属于 P04-03/P04-04，本记录不将其标记为通过。
