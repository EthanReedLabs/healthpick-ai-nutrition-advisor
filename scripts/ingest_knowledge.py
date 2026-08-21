"""Extract deterministic page-level records from the frozen PDF sources."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import pymupdf
import yaml


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "knowledge" / "manifests" / "sources.yaml"
OUTPUT_DIR = ROOT / "knowledge" / "normalized" / "pages"
KNOWN_WATERMARKS = {"Kimi 生成", "Kimi生成"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def normalize_text(text: str) -> tuple[str, int]:
    cleaned_lines: list[str] = []
    removed_watermarks = 0
    for raw_line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = re.sub(r"[ \t]+", " ", raw_line).strip()
        if line in KNOWN_WATERMARKS:
            removed_watermarks += 1
            continue
        if line:
            cleaned_lines.append(line)
    return "\n".join(cleaned_lines), removed_watermarks


def text_blocks(page: pymupdf.Page) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for x0, y0, x1, y1, text, block_no, block_type in page.get_text(
        "blocks", sort=True
    ):
        if block_type != 0:
            continue
        normalized, removed = normalize_text(text)
        if not normalized:
            continue
        blocks.append(
            {
                "block_no": int(block_no),
                "bbox": [round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)],
                "text": normalized,
                "watermarks_removed": removed,
            }
        )
    return blocks


def load_sources() -> list[dict[str, Any]]:
    manifest = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))
    return manifest["sources"]


def extract_source(source: dict[str, Any]) -> tuple[Path, int]:
    source_path = ROOT / source["file"]
    actual_hash = sha256(source_path)
    expected_hash = str(source["sha256"]).upper()
    if actual_hash != expected_hash:
        raise ValueError(
            f"{source['code']}: SHA-256 mismatch: {actual_hash} != {expected_hash}"
        )

    document = pymupdf.open(source_path)
    if document.page_count != int(source["pages"]):
        raise ValueError(
            f"{source['code']}: page count mismatch: "
            f"{document.page_count} != {source['pages']}"
        )

    records: list[dict[str, Any]] = []
    try:
        for page_index, page in enumerate(document):
            raw_text = page.get_text("text", sort=True).replace("\r\n", "\n")
            normalized, removed = normalize_text(raw_text)
            blocks = text_blocks(page)
            cjk_chars = len(re.findall(r"[\u3400-\u9fff]", normalized))
            spaced_cjk = len(
                re.findall(r"[\u3400-\u9fff]\s+[\u3400-\u9fff]", normalized)
            )
            unknown_glyphs = normalized.count("\uffff") + normalized.count("\ufffd")
            records.append(
                {
                    "schema_version": 1,
                    "page_id": f"{source['code']}-p{page_index + 1:02d}",
                    "source_code": source["code"],
                    "source_title": source["title"],
                    "source_version": source["version"],
                    "source_role": source["source_role"],
                    "source_sha256": actual_hash,
                    "page": page_index + 1,
                    "page_count": document.page_count,
                    "extractor": {"name": "PyMuPDF", "version": pymupdf.VersionBind},
                    "raw_text": raw_text,
                    "normalized_text": normalized,
                    "blocks": blocks,
                    "quality": {
                        "character_count": len(normalized),
                        "cjk_character_count": cjk_chars,
                        "spaced_cjk_pairs": spaced_cjk,
                        "unknown_glyph_count": unknown_glyphs,
                        "watermarks_removed": removed,
                        "empty": not bool(normalized),
                    },
                    "review_status": "review_required",
                }
            )
    finally:
        document.close()

    if any(record["quality"]["empty"] for record in records):
        raise ValueError(f"{source['code']}: one or more pages have no native text")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{source['code']}.pages.jsonl"
    temporary_path = output_path.with_suffix(".jsonl.tmp")
    with temporary_path.open("w", encoding="utf-8", newline="\n") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    temporary_path.replace(output_path)
    return output_path, len(records)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        default="all",
        choices=("all", "A", "B", "C"),
        help="Source code to extract.",
    )
    args = parser.parse_args()

    selected = [
        source
        for source in load_sources()
        if args.source == "all" or source["code"] == args.source
    ]
    try:
        for source in selected:
            output_path, page_count = extract_source(source)
            print(f"{source['code']}: {page_count} pages -> {output_path}")
    except (OSError, ValueError, pymupdf.FileDataError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
