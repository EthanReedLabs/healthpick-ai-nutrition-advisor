"""Rasterize Word-exported competition-deliverable PDFs for visual QA."""

from pathlib import Path

import pymupdf


ROOT = Path(__file__).resolve().parents[1]
QA_ROOT = ROOT / "output" / "docx-qa"


def main() -> None:
    for pdf_path in sorted(QA_ROOT.glob("*/*.pdf")):
        document = pymupdf.open(pdf_path)
        try:
            for page_number, page in enumerate(document, start=1):
                pixmap = page.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5), alpha=False)
                pixmap.save(pdf_path.parent / f"page-{page_number}.png")
            print(f"{pdf_path.parent.name}: {len(document)} pages")
        finally:
            document.close()


if __name__ == "__main__":
    main()
