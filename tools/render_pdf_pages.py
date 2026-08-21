"""Render selected source pages to PNG for human fact verification."""

from __future__ import annotations

import argparse
from pathlib import Path

import pymupdf
import yaml


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "knowledge" / "manifests" / "sources.yaml"
OUTPUT_DIR = ROOT / "docs" / "evidence" / "phase-02-page-review"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "selection",
        nargs="+",
        help="Page selection such as A:2 A:4 B:1.",
    )
    args = parser.parse_args()

    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    sources = {source["code"]: source for source in manifest["sources"]}
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for item in args.selection:
        code, page_text = item.upper().split(":", 1)
        source = sources[code]
        page_number = int(page_text)
        source_path = ROOT / source["file"]
        with pymupdf.open(source_path) as document:
            if not 1 <= page_number <= document.page_count:
                raise ValueError(f"{item}: page out of range")
            page = document[page_number - 1]
            pixmap = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
            output = OUTPUT_DIR / f"{code}-p{page_number:02d}.png"
            pixmap.save(output)
            print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

