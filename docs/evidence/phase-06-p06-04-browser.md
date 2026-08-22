# P06-04 用户数据导出与删除浏览器验收

结论：`PASS`。

- 目标：Web `http://127.0.0.1:3100/`，API `http://127.0.0.1:8010/`；真实 PostgreSQL 与 real 模式本地栈。
- 真实注册测试账号后，账号窗口显示“导出我的数据”和“永久删除账号”两个独立入口。
- 导出触发浏览器真实下载 `healthpick-account-2026-08-22.json`；文件包含 `users=1`、`auth_sessions=1`、`anonymous_sessions=1`、`conversations=1`、`conversation_turns=0`、`total_records=4`，不含 `password_hash`、`token_hash` 或密码。
- 删除入口明确提示不可撤销及覆盖范围，要求再次输入密码；确认后账号窗口关闭、令牌清除并创建全新匿名会话，原账号不能再登录。
- 干净浏览器会话复查删除确认表单：控制台错误 `0`、警告 `0`；首次出现的密码表单用户名提示已通过隐藏 `autocomplete=username` 字段解决。

截图：

- `output/playwright/phase-06-p06-04-account-export-delete.png`
- `output/playwright/phase-06-p06-04-account-delete-confirm.png`
