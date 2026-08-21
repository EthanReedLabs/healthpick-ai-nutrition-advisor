# Scripts

预留可重复执行的知识导入、数据库 seed、评测、smoke、文档门禁和发布检查脚本。脚本必须幂等或明确写出副作用，不把临时 OCR 文本当作生产知识源。

当前可用脚本：

- `ingest_knowledge.py`：校验来源并生成页级记录；
- `build_chunks.py`：生成稳定的页内 Chunk；
- `build_structured_facts.py`：从 curated YAML 生成带复核门禁的事实；
- `validate_knowledge.py`：知识完整性、Schema 和隔离校验；
- `control_plane.py`：验证中心任务台账并生成控制板、问题日志和最终验收阻断清单。

日常运行 `control_plane.py` 校验结构；最终发布使用 `control_plane.py --check-final`，存在任何必做任务、行动、阻断问题、未复核记录或 Release 字段缺失时非零退出。
