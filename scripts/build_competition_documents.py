"""Build the three competition delivery DOCX files from maintained Markdown sources.

Design preset: compact_reference_guide.
First-page pattern: editorial_cover (restrained technical-delivery variant).
Named overrides:
- CJK glyph fallback uses Microsoft YaHei while Latin text remains Calibri.
- The test matrix uses Letter landscape with 0.75-inch margins so six real data
  columns remain readable; every other preset token is preserved.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import qrcode
from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
DELIVERABLES = ROOT / "docs" / "deliverables"
WORD_DIR = DELIVERABLES / "word"
ASSET_DIR = DELIVERABLES / "assets"
PUBLIC_URL = "https://106.14.13.139/"

BLUE = "2E74B5"
DARK_BLUE = "1F4D78"
INK = "173B36"
GREEN = "0E8064"
PALE_GREEN = "EAF5F0"
LIGHT_BLUE = "E8EEF5"
LIGHT_GRAY = "F2F4F7"
MUTED = "667085"
WHITE = "FFFFFF"
BORDER = "CBD5E1"


@dataclass(frozen=True)
class DocSpec:
    source: Path
    output: Path
    title: str
    subtitle: str
    code: str
    landscape: bool = False


SPECS = (
    DocSpec(
        source=DELIVERABLES / "03-使用说明文档.md",
        output=WORD_DIR / "03-使用说明文档.docx",
        title="AI智能膳食顾问使用说明",
        subtitle="访问、操作、技术逻辑与安全边界",
        code="DELIVERABLE 03 · USER GUIDE",
    ),
    DocSpec(
        source=DELIVERABLES / "04-系统架构说明.md",
        output=WORD_DIR / "04-系统架构说明.docx",
        title="AI智能膳食顾问系统架构说明",
        subtitle="前后端、知识库、推荐、安全、多轮与部署",
        code="DELIVERABLE 04 · ARCHITECTURE",
    ),
    DocSpec(
        source=DELIVERABLES / "05-基础功能测试记录.md",
        output=WORD_DIR / "05-基础功能测试记录.docx",
        title="AI智能膳食顾问基础功能测试记录",
        subtitle="12 组可复核测试与当前发布质量门",
        code="DELIVERABLE 05 · TEST RECORD",
        landscape=True,
    ),
)


def set_run_font(
    run,
    *,
    latin: str = "Calibri",
    east_asia: str = "Microsoft YaHei",
    size: float | None = None,
    color: str | None = None,
    bold: bool | None = None,
    italic: bool | None = None,
) -> None:
    run.font.name = latin
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.rFonts
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.insert(0, rfonts)
    rfonts.set(qn("w:ascii"), latin)
    rfonts.set(qn("w:hAnsi"), latin)
    rfonts.set(qn("w:eastAsia"), east_asia)
    if size is not None:
        run.font.size = Pt(size)
    if color is not None:
        run.font.color.rgb = RGBColor.from_string(color)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic


def set_paragraph_tokens(paragraph, *, before: float, after: float, line: float) -> None:
    fmt = paragraph.paragraph_format
    fmt.space_before = Pt(before)
    fmt.space_after = Pt(after)
    fmt.line_spacing = line
    fmt.widow_control = True


def shade(element, fill: str) -> None:
    shd = element.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        element.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, *, top: int = 80, bottom: int = 80, start: int = 120, end: int = 120) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for edge, value in (("top", top), ("bottom", bottom), ("start", start), ("end", end)):
        node = tc_mar.find(qn(f"w:{edge}"))
        if node is None:
            node = OxmlElement(f"w:{edge}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_table_borders(table, color: str = BORDER, size: int = 6) -> None:
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.first_child_found_in("w:tblBorders")
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = borders.find(qn(f"w:{edge}"))
        if tag is None:
            tag = OxmlElement(f"w:{edge}")
            borders.append(tag)
        tag.set(qn("w:val"), "single")
        tag.set(qn("w:sz"), str(size))
        tag.set(qn("w:space"), "0")
        tag.set(qn("w:color"), color)


def set_repeat_table_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def set_table_geometry(table, widths_dxa: list[int], *, indent_dxa: int = 120) -> None:
    total = sum(widths_dxa)
    table.autofit = False
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    tbl_pr = table._tbl.tblPr

    tbl_w = tbl_pr.first_child_found_in("w:tblW")
    if tbl_w is None:
        tbl_w = OxmlElement("w:tblW")
        tbl_pr.append(tbl_w)
    tbl_w.set(qn("w:w"), str(total))
    tbl_w.set(qn("w:type"), "dxa")

    tbl_ind = tbl_pr.first_child_found_in("w:tblInd")
    if tbl_ind is None:
        tbl_ind = OxmlElement("w:tblInd")
        tbl_pr.append(tbl_ind)
    tbl_ind.set(qn("w:w"), str(indent_dxa))
    tbl_ind.set(qn("w:type"), "dxa")

    grid = table._tbl.tblGrid
    for child in list(grid):
        grid.remove(child)
    for width in widths_dxa:
        col = OxmlElement("w:gridCol")
        col.set(qn("w:w"), str(width))
        grid.append(col)

    for row in table.rows:
        for idx, cell in enumerate(row.cells):
            width = widths_dxa[min(idx, len(widths_dxa) - 1)]
            tc_pr = cell._tc.get_or_add_tcPr()
            tc_w = tc_pr.first_child_found_in("w:tcW")
            if tc_w is None:
                tc_w = OxmlElement("w:tcW")
                tc_pr.append(tc_w)
            tc_w.set(qn("w:w"), str(width))
            tc_w.set(qn("w:type"), "dxa")
            cell.width = Inches(width / 1440)


def add_page_field(paragraph) -> None:
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = "1"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend((begin, instr, separate, text, end))
    set_run_font(run, size=8.5, color=MUTED)


def add_hyperlink(paragraph, text: str, url: str) -> None:
    part = paragraph.part
    rel_id = part.relate_to(
        url,
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
        is_external=True,
    )
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), rel_id)
    new_run = OxmlElement("w:r")
    rpr = OxmlElement("w:rPr")
    color = OxmlElement("w:color")
    color.set(qn("w:val"), GREEN)
    underline = OxmlElement("w:u")
    underline.set(qn("w:val"), "single")
    rfonts = OxmlElement("w:rFonts")
    rfonts.set(qn("w:ascii"), "Calibri")
    rfonts.set(qn("w:hAnsi"), "Calibri")
    rfonts.set(qn("w:eastAsia"), "Microsoft YaHei")
    rpr.extend((rfonts, color, underline))
    new_run.append(rpr)
    node = OxmlElement("w:t")
    node.text = text
    new_run.append(node)
    hyperlink.append(new_run)
    paragraph._p.append(hyperlink)


def configure_styles(doc: Document) -> None:
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)
    normal.font.color.rgb = RGBColor.from_string("1F2937")
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.25

    heading_tokens = {
        "Heading 1": (16, BLUE, 18, 10),
        "Heading 2": (13, BLUE, 14, 7),
        "Heading 3": (12, DARK_BLUE, 10, 5),
    }
    for name, (size, color, before, after) in heading_tokens.items():
        style = doc.styles[name]
        style.font.name = "Calibri"
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor.from_string(color)
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True
        style.paragraph_format.line_spacing = 1.0

    for name in ("List Bullet", "List Number"):
        style = doc.styles[name]
        style.font.name = "Calibri"
        style.font.size = Pt(11)
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
        style.paragraph_format.left_indent = Inches(0.375)
        style.paragraph_format.first_line_indent = Inches(-0.188)
        style.paragraph_format.space_after = Pt(4)
        style.paragraph_format.line_spacing = 1.25

    caption = doc.styles["Caption"]
    caption.font.name = "Calibri"
    caption.font.size = Pt(9)
    caption.font.italic = False
    caption.font.color.rgb = RGBColor.from_string(MUTED)
    caption._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")


def configure_section(doc: Document, *, landscape: bool) -> int:
    section = doc.sections[0]
    if landscape:
        section.orientation = WD_ORIENT.LANDSCAPE
        section.page_width = Inches(11)
        section.page_height = Inches(8.5)
        margin = 0.75
    else:
        section.page_width = Inches(8.5)
        section.page_height = Inches(11)
        margin = 1.0
    section.top_margin = Inches(margin)
    section.right_margin = Inches(margin)
    section.bottom_margin = Inches(margin)
    section.left_margin = Inches(margin)
    section.header_distance = Inches(0.492)
    section.footer_distance = Inches(0.492)
    return int((section.page_width.inches - 2 * margin) * 1440)


def add_header_footer(doc: Document, spec: DocSpec, content_width_dxa: int) -> None:
    section = doc.sections[0]
    header = section.header
    p = header.paragraphs[0]
    p.text = ""
    set_paragraph_tokens(p, before=0, after=2, line=1.0)
    left = p.add_run("HEALTHPICK · AI SMART NUTRITION ADVISOR")
    set_run_font(left, size=8.2, color=GREEN, bold=True)
    p.add_run("    ")
    right = p.add_run(spec.code)
    set_run_font(right, size=8.2, color=MUTED)

    footer = section.footer
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    set_paragraph_tokens(fp, before=2, after=0, line=1.0)
    run = fp.add_run("赛事交付文档 · 第 ")
    set_run_font(run, size=8.5, color=MUTED)
    add_page_field(fp)
    run = fp.add_run(" 页")
    set_run_font(run, size=8.5, color=MUTED)


def add_title_block(doc: Document, spec: DocSpec, metadata: list[str], content_width_dxa: int) -> None:
    kicker = doc.add_paragraph()
    set_paragraph_tokens(kicker, before=12 if not spec.landscape else 4, after=8, line=1.0)
    kr = kicker.add_run(spec.code)
    set_run_font(kr, size=9.5, color=GREEN, bold=True)

    title = doc.add_paragraph()
    set_paragraph_tokens(title, before=0, after=5, line=1.0)
    title.paragraph_format.keep_with_next = True
    tr = title.add_run(spec.title)
    set_run_font(tr, size=25 if not spec.landscape else 22, color=INK, bold=True)

    subtitle = doc.add_paragraph()
    set_paragraph_tokens(subtitle, before=0, after=14 if not spec.landscape else 9, line=1.1)
    sr = subtitle.add_run(spec.subtitle)
    set_run_font(sr, size=12.5, color=MUTED)

    if metadata:
        table = doc.add_table(rows=1, cols=len(metadata))
        widths = distribute_widths(content_width_dxa, len(metadata), equal=True)
        set_table_geometry(table, widths, indent_dxa=120)
        set_table_borders(table, color="D7E4DE", size=4)
        for index, text in enumerate(metadata):
            cell = table.cell(0, index)
            shade(cell._tc.get_or_add_tcPr(), PALE_GREEN)
            set_cell_margins(cell, top=100, bottom=100, start=120, end=120)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            set_paragraph_tokens(p, before=0, after=0, line=1.1)
            r = p.add_run(text)
            set_run_font(r, size=9, color=INK, bold=True)
        spacer = doc.add_paragraph()
        set_paragraph_tokens(spacer, before=0, after=2, line=1.0)


def distribute_widths(total: int, columns: int, *, equal: bool = False) -> list[int]:
    if equal:
        base = total // columns
        widths = [base] * columns
        widths[-1] += total - sum(widths)
        return widths
    patterns = {
        2: [0.28, 0.72],
        3: [0.24, 0.56, 0.20],
        4: [0.12, 0.24, 0.49, 0.15],
        5: [0.07, 0.15, 0.24, 0.44, 0.10],
        6: [0.055, 0.12, 0.205, 0.22, 0.32, 0.08],
    }
    weights = patterns.get(columns, [1 / columns] * columns)
    widths = [int(total * value) for value in weights]
    widths[-1] += total - sum(widths)
    return widths


INLINE_RE = re.compile(r"(`[^`]+`|<https?://[^>]+>|\*\*[^*]+\*\*)")


def add_inline(paragraph, text: str, *, size: float | None = None) -> None:
    cursor = 0
    for match in INLINE_RE.finditer(text):
        if match.start() > cursor:
            run = paragraph.add_run(text[cursor : match.start()])
            set_run_font(run, size=size)
        token = match.group(0)
        if token.startswith("`"):
            run = paragraph.add_run(token[1:-1])
            set_run_font(run, latin="Consolas", east_asia="Microsoft YaHei", size=(size or 11) - 0.5, color=DARK_BLUE)
        elif token.startswith("<http"):
            url = token[1:-1]
            add_hyperlink(paragraph, url, url)
        else:
            run = paragraph.add_run(token[2:-2])
            set_run_font(run, size=size, bold=True)
        cursor = match.end()
    if cursor < len(text):
        run = paragraph.add_run(text[cursor:])
        set_run_font(run, size=size)


def parse_table(lines: list[str]) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in lines:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            continue
        rows.append(cells)
    return rows


def add_markdown_table(doc: Document, rows: list[list[str]], content_width_dxa: int) -> None:
    if not rows:
        return
    columns = max(len(row) for row in rows)
    normalized = [row + [""] * (columns - len(row)) for row in rows]
    table = doc.add_table(rows=len(normalized), cols=columns)
    widths = distribute_widths(content_width_dxa, columns)
    set_table_geometry(table, widths, indent_dxa=120)
    set_table_borders(table)
    set_repeat_table_header(table.rows[0])

    font_size = 9.1 if columns <= 3 else 8.4 if columns <= 5 else 8.0
    for r_idx, source_row in enumerate(normalized):
        for c_idx, text in enumerate(source_row):
            cell = table.cell(r_idx, c_idx)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_margins(cell, top=90, bottom=90, start=105, end=105)
            if r_idx == 0:
                shade(cell._tc.get_or_add_tcPr(), LIGHT_BLUE)
            elif r_idx % 2 == 0:
                shade(cell._tc.get_or_add_tcPr(), "F8FAFC")
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if c_idx in (0, columns - 1) else WD_ALIGN_PARAGRAPH.LEFT
            set_paragraph_tokens(p, before=0, after=0, line=1.15)
            add_inline(p, text, size=font_size)
            for run in p.runs:
                if r_idx == 0:
                    run.bold = True
                    run.font.color.rgb = RGBColor.from_string(DARK_BLUE)
    after = doc.add_paragraph()
    set_paragraph_tokens(after, before=0, after=2, line=1.0)


def add_figure(doc: Document, path: Path, *, width_inches: float, caption: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_paragraph_tokens(p, before=4, after=4, line=1.0)
    run = p.add_run()
    inline = run.add_picture(str(path), width=Inches(width_inches))
    doc_pr = inline._inline.docPr
    doc_pr.set("descr", caption)
    cp = doc.add_paragraph(style="Caption")
    cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_paragraph_tokens(cp, before=0, after=8, line=1.0)
    cp.add_run(caption)


def add_body_from_markdown(doc: Document, source: str, content_width_dxa: int, *, landscape: bool) -> None:
    lines = source.splitlines()
    first_h2 = next((idx for idx, line in enumerate(lines) if line.startswith("## ")), len(lines))
    lines = lines[first_h2:]
    i = 0
    paragraph_buffer: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph_buffer
        if not paragraph_buffer:
            return
        text = "".join(part.strip() for part in paragraph_buffer)
        p = doc.add_paragraph()
        set_paragraph_tokens(p, before=0, after=6, line=1.25)
        add_inline(p, text)
        paragraph_buffer = []

    while i < len(lines):
        line = lines[i].rstrip()
        if not line:
            flush_paragraph()
            i += 1
            continue
        if line.startswith("|"):
            flush_paragraph()
            table_lines: list[str] = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                table_lines.append(lines[i].rstrip())
                i += 1
            add_markdown_table(doc, parse_table(table_lines), content_width_dxa)
            continue
        if line == "[[QR:public-url]]":
            flush_paragraph()
            add_figure(doc, ASSET_DIR / "public-url-qr.png", width_inches=1.55, caption="扫码访问 HealthPick 公网演示入口")
            i += 1
            continue
        if line == "[[FIGURE:architecture]]":
            flush_paragraph()
            add_figure(
                doc,
                ASSET_DIR / "system-architecture.png",
                width_inches=8.8 if landscape else 6.25,
                caption="图 1  HealthPick 生产架构与证据安全工作流",
            )
            i += 1
            continue
        heading = re.match(r"^(#{2,4})\s+(.*)$", line)
        if heading:
            flush_paragraph()
            level = len(heading.group(1)) - 1
            p = doc.add_paragraph(style=f"Heading {min(level, 3)}")
            p.add_run(heading.group(2))
            i += 1
            continue
        if line.startswith("- "):
            flush_paragraph()
            p = doc.add_paragraph(style="List Bullet")
            add_inline(p, line[2:].strip())
            i += 1
            continue
        numbered = re.match(r"^\d+\.\s+(.*)$", line)
        if numbered:
            flush_paragraph()
            p = doc.add_paragraph(style="List Number")
            add_inline(p, numbered.group(1).strip())
            i += 1
            continue
        paragraph_buffer.append(line)
        i += 1
    flush_paragraph()


def load_font(size: int, *, bold: bool = False):
    candidates = [
        Path(r"C:\Windows\Fonts\msyhbd.ttc" if bold else r"C:\Windows\Fonts\msyh.ttc"),
        Path(r"C:\Windows\Fonts\simhei.ttf"),
        Path(r"C:\Windows\Fonts\arial.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def generate_qr() -> None:
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=4)
    qr.add_data(PUBLIC_URL)
    qr.make(fit=True)
    image = qr.make_image(fill_color="#0E8064", back_color="white").convert("RGB")
    image.save(ASSET_DIR / "public-url-qr.png")


def rounded_box(draw, xy, title: str, subtitle: str, *, fill: str, outline: str, title_color: str = "#173B36") -> None:
    draw.rounded_rectangle(xy, radius=22, fill=fill, outline=outline, width=3)
    x1, y1, x2, y2 = xy
    title_font = load_font(29, bold=True)
    body_font = load_font(20)
    tw = draw.textbbox((0, 0), title, font=title_font)[2]
    sw = draw.textbbox((0, 0), subtitle, font=body_font)[2]
    draw.text(((x1 + x2 - tw) / 2, y1 + 20), title, font=title_font, fill=title_color)
    draw.text(((x1 + x2 - sw) / 2, y1 + 64), subtitle, font=body_font, fill="#52616B")


def arrow(draw, start: tuple[int, int], end: tuple[int, int], *, color: str = "#6B8791", width: int = 4) -> None:
    draw.line((start, end), fill=color, width=width)
    ex, ey = end
    sx, sy = start
    if abs(ex - sx) > abs(ey - sy):
        direction = 1 if ex > sx else -1
        points = [(ex, ey), (ex - 14 * direction, ey - 8), (ex - 14 * direction, ey + 8)]
    else:
        direction = 1 if ey > sy else -1
        points = [(ex, ey), (ex - 8, ey - 14 * direction), (ex + 8, ey - 14 * direction)]
    draw.polygon(points, fill=color)


def generate_architecture_diagram() -> None:
    canvas = Image.new("RGB", (1600, 900), "#F8FBFA")
    draw = ImageDraw.Draw(canvas)
    title_font = load_font(34, bold=True)
    draw.text((60, 35), "公网交互层", font=title_font, fill="#173B36")
    rounded_box(draw, (60, 95, 360, 205), "浏览器", "桌面 · 平板 · 手机", fill="#FFFFFF", outline="#A9D8C5")
    rounded_box(draw, (510, 95, 810, 205), "Caddy", "HTTPS · 反向代理", fill="#EAF5F0", outline="#73B99C")
    rounded_box(draw, (960, 95, 1260, 205), "Next.js Web", "问答 · 档案 · 历史 · 引用", fill="#FFFFFF", outline="#A9D8C5")
    arrow(draw, (360, 150), (510, 150))
    arrow(draw, (810, 150), (960, 150))

    draw.text((60, 270), "后端证据与安全工作流", font=title_font, fill="#173B36")
    boxes = [
        ("输入/权限", "空长边界 · Session"),
        ("S0-S3 安全门", "禁忌过滤 · 必需提示"),
        ("来源路由", "A/B 营养 · C 平台"),
        ("Keyword 检索", "章节 · 页码 · Chunk"),
        ("百炼千问", "qwen3.7-plus · real"),
        ("输出后校验", "逐条引用 · 安全复核"),
    ]
    x_positions = [60, 310, 560, 810, 1060, 1310]
    for idx, ((title, subtitle), x) in enumerate(zip(boxes, x_positions)):
        rounded_box(draw, (x, 335, x + 210, 455), title, subtitle, fill="#FFFFFF" if idx % 2 == 0 else "#EAF5F0", outline="#83BFA7")
        if idx < len(boxes) - 1:
            arrow(draw, (x + 210, 395), (x_positions[idx + 1], 395))

    draw.text((60, 535), "只读知识与状态存储", font=title_font, fill="#173B36")
    rounded_box(draw, (60, 605, 410, 735), "A + B 核心知识", "营养事实 · 方案 · 禁忌 · 7 条规则", fill="#EDF5FF", outline="#8EB4D9")
    rounded_box(draw, (505, 605, 855, 735), "C 辅助平台资料", "会员 · 企业合作 · API 服务", fill="#FFF7E8", outline="#D9B871")
    rounded_box(draw, (950, 605, 1300, 735), "PostgreSQL", "会话 · 完整历史 · 账号", fill="#F1F3F8", outline="#AAB3C2")
    rounded_box(draw, (1360, 605, 1540, 735), "临时档案", "请求内使用\n不单独落库", fill="#FCEEEF", outline="#D9A0A5")
    arrow(draw, (235, 605), (650, 455))
    arrow(draw, (680, 605), (665, 455))
    arrow(draw, (1125, 605), (1415, 455))
    arrow(draw, (1450, 605), (415, 455), color="#A98787", width=3)

    note_font = load_font(22)
    draw.rounded_rectangle((60, 790, 1540, 855), radius=18, fill="#173B36")
    note = "确定性前门（权限/安全/来源）  +  受证据约束生成  +  确定性后门（引用/安全）  =  完整回答才写入历史"
    bbox = draw.textbbox((0, 0), note, font=note_font)
    draw.text(((1600 - (bbox[2] - bbox[0])) / 2, 809), note, font=note_font, fill="white")
    canvas.save(ASSET_DIR / "system-architecture.png", quality=95)


def extract_metadata(source: str) -> list[str]:
    lines = source.splitlines()[1:]
    values = []
    for line in lines:
        if line.startswith("## "):
            break
        clean = line.strip().rstrip("  ")
        if clean:
            clean = clean.replace("`", "")
            clean = re.sub(r"<(https?://[^>]+)>", r"\1", clean)
            values.append(clean)
    return values[:4]


def build_document(spec: DocSpec) -> None:
    source = spec.source.read_text(encoding="utf-8")
    doc = Document()
    configure_styles(doc)
    content_width_dxa = configure_section(doc, landscape=spec.landscape)
    add_header_footer(doc, spec, content_width_dxa)
    add_title_block(doc, spec, extract_metadata(source), content_width_dxa)
    add_body_from_markdown(doc, source, content_width_dxa, landscape=spec.landscape)
    doc.core_properties.title = spec.title
    doc.core_properties.subject = "第二届 OPC 软件与智能体开发赛道 · AI智能膳食顾问"
    doc.core_properties.author = "HealthPick 参赛团队（Codex 辅助生成，人工验收）"
    doc.core_properties.keywords = "HealthPick, AI智能膳食顾问, OPC, RAG, qwen3.7-plus"
    spec.output.parent.mkdir(parents=True, exist_ok=True)
    doc.save(spec.output)


def chinese_character_count(text: str) -> int:
    return len(re.findall(r"[\u3400-\u9fff]", text))


def validate_sources() -> dict[str, int]:
    usage = SPECS[0].source.read_text(encoding="utf-8")
    architecture = SPECS[1].source.read_text(encoding="utf-8")
    tests = SPECS[2].source.read_text(encoding="utf-8")
    core_match = re.search(r"## 6\. 技术选型与核心逻辑说明\n(.*?)(?=\n## 7\.)", usage, re.S)
    if core_match is None:
        raise RuntimeError("Missing technical selection and core logic section")
    metrics = {
        "usage_chinese_chars": chinese_character_count(usage),
        "usage_core_logic_chinese_chars": chinese_character_count(core_match.group(1)),
        "architecture_chinese_chars": chinese_character_count(architecture),
        "test_groups": len(re.findall(r"^\| T\d{2} \|", tests, re.M)),
    }
    if metrics["usage_chinese_chars"] < 500:
        raise RuntimeError("Usage guide is shorter than 500 Chinese characters")
    if metrics["usage_core_logic_chinese_chars"] < 200:
        raise RuntimeError("Core logic section is shorter than 200 Chinese characters")
    if metrics["architecture_chinese_chars"] < 300:
        raise RuntimeError("Architecture document is shorter than 300 Chinese characters")
    if metrics["test_groups"] < 5:
        raise RuntimeError("Fewer than 5 basic functional test groups")
    return metrics


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def main() -> None:
    WORD_DIR.mkdir(parents=True, exist_ok=True)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    metrics = validate_sources()
    generate_qr()
    generate_architecture_diagram()
    for spec in SPECS:
        build_document(spec)
    print("SOURCE_METRICS", metrics)
    for spec in SPECS:
        print(f"DOCX {spec.output.relative_to(ROOT)} {spec.output.stat().st_size} SHA256={sha256(spec.output)}")


if __name__ == "__main__":
    main()
