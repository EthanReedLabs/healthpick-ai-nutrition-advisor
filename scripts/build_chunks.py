"""Build stable, page-bounded chunks from extracted page block records."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PAGE_DIR = ROOT / "knowledge" / "normalized" / "pages"
OUTPUT_DIR = ROOT / "knowledge" / "normalized" / "chunks"
TARGET_CHARS = 480

HEADING_PATTERNS = (
    re.compile(r"^第[一二三四五六七八九十]+章"),
    re.compile(r"^\d+\.\d+\s*"),
    re.compile(r"^【[^】]+】"),
    re.compile(r"^周[一二三四五六日]食谱"),
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def is_heading(text: str) -> bool:
    first_line = text.splitlines()[0].strip()
    return len(first_line) <= 60 and any(pattern.match(first_line) for pattern in HEADING_PATTERNS)


def route_policy(source_role: str) -> tuple[list[str], list[str]]:
    if source_role == "auxiliary_platform":
        return ["platform"], ["nutrition", "recommendation", "contraindication"]
    return ["nutrition", "recommendation", "contraindication"], ["platform"]


def flush_chunk(
    chunks: list[dict[str, Any]],
    page: dict[str, Any],
    section: str,
    texts: list[str],
    block_numbers: list[int],
) -> None:
    content = "\n".join(texts).strip()
    if not content:
        return
    chunk_number = len(chunks) + 1
    allowed, forbidden = route_policy(page["source_role"])
    chunks.append(
        {
            "schema_version": 1,
            "chunk_id": (f"{page['source_code']}-p{page['page']:02d}-c{chunk_number:02d}"),
            "page_id": page["page_id"],
            "source_code": page["source_code"],
            "source_title": page["source_title"],
            "source_version": page["source_version"],
            "source_role": page["source_role"],
            "source_sha256": page["source_sha256"],
            "page": page["page"],
            "section": section,
            "content": content,
            "block_numbers": block_numbers,
            "allowed_routes": allowed,
            "forbidden_routes": forbidden,
            "contains_table": bool(
                re.search(
                    r"食材\s+热量|营养素\s+.*目标|套餐\s+月调用量|服务项\s+内容\s+价格|企业规模\s+年费",
                    content,
                )
            ),
            "unknown_glyph_count": content.count("\uffff") + content.count("\ufffd"),
            "review_status": "review_required",
        }
    )


def build_source(page_path: Path) -> tuple[Path, int]:
    pages = read_jsonl(page_path)
    source_code = pages[0]["source_code"]
    source_chunks: list[dict[str, Any]] = []
    inherited_section = "文档首页"

    for page in pages:
        page_chunks: list[dict[str, Any]] = []
        current_section = inherited_section
        texts: list[str] = []
        block_numbers: list[int] = []
        current_length = 0

        for block in page["blocks"]:
            text = block["text"].strip()
            if is_heading(text):
                flush_chunk(page_chunks, page, current_section, texts, block_numbers)
                texts = []
                block_numbers = []
                current_length = 0
                current_section = text.splitlines()[0].strip()
                inherited_section = current_section

            if texts and current_length + len(text) + 1 > TARGET_CHARS:
                flush_chunk(page_chunks, page, current_section, texts, block_numbers)
                texts = []
                block_numbers = []
                current_length = 0

            texts.append(text)
            block_numbers.append(block["block_no"])
            current_length += len(text) + 1

        flush_chunk(page_chunks, page, current_section, texts, block_numbers)

        # Chapter/section title-only blocks carry no retrievable fact. The
        # section value is retained on the following semantic chunk.
        page_chunks = [
            chunk
            for chunk in page_chunks
            if not (
                chunk["content"].strip() == chunk["section"].strip()
                and is_heading(chunk["content"].strip())
            )
        ]

        # IDs are page-local so inserting a page never renumbers other pages.
        for index, chunk in enumerate(page_chunks, start=1):
            chunk["chunk_id"] = f"{source_code}-p{page['page']:02d}-c{index:02d}"
        source_chunks.extend(page_chunks)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output = OUTPUT_DIR / f"{source_code}.chunks.jsonl"
    temporary = output.with_suffix(".jsonl.tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        for chunk in source_chunks:
            stream.write(json.dumps(chunk, ensure_ascii=False, sort_keys=True) + "\n")
    temporary.replace(output)
    return output, len(source_chunks)


def main() -> int:
    total = 0
    for page_path in sorted(PAGE_DIR.glob("*.pages.jsonl")):
        output, count = build_source(page_path)
        total += count
        print(f"{page_path.name}: {count} chunks -> {output}")
    print(f"total: {total} chunks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
