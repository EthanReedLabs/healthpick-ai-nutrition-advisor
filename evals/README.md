# Evaluation

- `datasets/`：固定黄金集、串库集、安全集和多轮集；
- `golden/`：经人工确认的期望断言；
- `adversarial/`：注入、越权、无答案和异常输入；
- `reports/`：按 release ID 固化的机器可读与 Markdown 报告。

评测必须记录 commit、知识哈希、provider/model 和运行时间。报告目录是构建产物，不手工修改分数。

