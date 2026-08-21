# Knowledge Assets

- `raw/`：只读归档的原始 A/B/C PDF；
- `manifests/`：来源角色、版本、哈希和使用边界；
- `normalized/`：解析后的页、章节、chunk 和人工复核事实；
- `schemas/`：chunk、FoodFact、PlanRule、PlatformFact 的 Schema；
- `prompts/`：版本化 Prompt，只组织检索证据，不承载硬编码答案。

生产导入不得直接使用 OCR 输出作为事实真值。所有表格数字、食材禁忌和方案边界必须对照原 PDF 人工复核。

