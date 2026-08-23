# 赛题交付文档索引

本目录提供《AI智能膳食顾问》赛题要求的三份正式交付文档。Markdown 为可维护源文件，`word/` 目录中的 DOCX 为提交版。

| 赛题要求 | Markdown 源文件 | Word 提交版 |
|---|---|---|
| 使用说明文档（不少于 500 字，技术选型与核心逻辑不少于 200 字） | `03-使用说明文档.md` | `word/03-使用说明文档.docx` |
| 系统架构说明（不少于 300 字） | `04-系统架构说明.md` | `word/04-系统架构说明.docx` |
| 基础功能测试记录（不少于 5 组） | `05-基础功能测试记录.md` | `word/05-基础功能测试记录.docx` |

生成命令：

```powershell
uv run --isolated --no-project --with python-docx --with "qrcode[pil]" python scripts/build_competition_documents.py
```

生成后优先使用 Documents 技能附带的 `render_docx.py` 渲染；若本机没有 LibreOffice/`soffice`，可使用 Microsoft Word 只读导出 PDF，再通过 `scripts/render_competition_docx_qa.py` 生成逐页 PNG。无论采用哪条路径，都必须完成全页视觉检查。渲染图片仅用于内部质量复核，不属于比赛提交物；本次检查结果见 `docs/evidence/phase-12-delivery-documents-validation.json`。
