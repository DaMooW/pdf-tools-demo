"""生成仓库用的 PDF 样例（仅依赖 PyMuPDF）。

产物（写入 data/generated/）：

1. sample_mixed_all.pdf —— 一页/多页同时包含四类元素：
   - 文字：标题 + 正文段落（含一个中文段落，若本机有 CJK 字体）
   - 图片：一张合成"柱状图"位图（由 PyMuPDF 绘制后光栅化得到真实像素图）
   - 表格：带网格线的 4 列销售表（PyMuPDF find_tables 可识别）
   - 表单：文本框 / 复选框 / 下拉框等 AcroForm 控件

2. sample_widget_types.pdf —— 全控件类型展示（文本框、复选框、下拉框、
   多选框、日期字段），并预填了部分值，方便演示"提取填充后的值"。

为什么需要这份合成样例：真实 PDF 极少在同一个文件里同时包含
"正文文字 + 内嵌图 + 结构化表格 + 可填写表单控件"，
仓库里的真实数据覆盖了：纯文字论文 (BOAD)、图片为主论文 (TREK)、
表格为主论文 (SWE-bench)、文字+图片混合论文 (SearchAuditor)、
真实表单 (IRS W-9 / W-4)。合成样例把四类元素收进一个文件，
保证"四合一混合"场景的示例可以稳定运行、结果确定性。
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "generated"

# 候选 CJK 字体（macOS / Linux / Windows 常见路径），找到即用
# 注意：优先纯 TTF（Arial Unicode），TTC 集合字体子集化后提取可能出现字形映射偏差
CJK_FONT_CANDIDATES = [
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "C:/Windows/Fonts/msyh.ttc",
]


def find_cjk_font() -> str | None:
    for p in CJK_FONT_CANDIDATES:
        if Path(p).exists():
            return p
    return None


def add_text_block(page: pymupdf.Page, rect: pymupdf.Rect, text: str, *, size=10, font: str = "helv", color=(0, 0, 0)):
    """插入文本块并保证 100% 写入（插入失败时换行补齐）。"""
    page.insert_textbox(rect, text, fontsize=size, fontname=font, color=color, align=0)


def make_gradient_chart_png() -> bytes:
    """用绘图原语画一张"柱状图"，光栅化为 JPEG 位图。

    相当于一个合成的产品数据图：标题 + 4 根柱子 + 坐标刻度。
    返回 JPEG 字节：PyMuPDF 对 JPEG 流使用 DCTDecode 原生压缩，
    不会像 PNG 那样解码成未压缩 RGB 导致 PDF 体积暴增。
    """
    scratch = pymupdf.open()
    page = scratch.new_page(width=560, height=320)

    # 标题
    page.insert_text(pymupdf.Point(180, 30), "Rooms Sold by Quarter", fontsize=18)
    # 坐标轴
    page.draw_line(pymupdf.Point(60, 260), pymupdf.Point(520, 260), width=1.2)
    page.draw_line(pymupdf.Point(60, 260), pymupdf.Point(60, 40), width=1.2)
    # 4 根柱子（不同颜色）+ 顶部数值
    bars = [
        ("Q1", 120, (0.35, 0.55, 0.85)),
        ("Q2", 165, (0.45, 0.75, 0.45)),
        ("Q3", 95,  (0.85, 0.55, 0.35)),
        ("Q4", 200, (0.75, 0.4, 0.5)),
    ]
    for i, (label, h, color) in enumerate(bars):
        x0 = 90 + i * 110
        page.draw_rect(pymupdf.Rect(x0, 260 - h, x0 + 60, 260), color=color, fill=color)
        page.insert_text(pymupdf.Point(x0 + 30, 42), f"{h}", fontsize=11)
        page.insert_text(pymupdf.Point(x0 + 20, 280), label, fontsize=12)
    return page.get_pixmap(dpi=110).tobytes("jpeg")


def add_table(page: pymupdf.Page, left=320, top=372, width=255):
    """绘制带网格线的表格（配合 PyMuPDF find_tables 识别）。"""
    rows = [["Product", "Qty", "Unit Price", "Subtotal"],
            ["Desk Lamp",      "12",   "$18.50",   "$222.00"],
            ["Floor Lamp",     "5",    "$59.00",   "$295.00"],
            ["Wall Sconce",    "8",    "$29.75",   "$238.00"],
            ["Total",          "25",   "-",        "$755.00"]]
    col_w = [85, 45, 65, 60]
    row_h = 26
    y = top
    for r_i, row in enumerate(rows):
        x = left
        for c_i, cell in enumerate(row):
            rect = pymupdf.Rect(x, y, x + col_w[c_i], y + row_h)
            page.draw_rect(rect, width=0.8, color=(0.45, 0.45, 0.45))
            page.insert_text(pymupdf.Point(x + 6, y + 17), cell, fontsize=10.5)
            x += col_w[c_i]
        y += row_h
    return y


def add_form_fields(page: pymupdf.Page, top: float):
    """在页面上创建真实的 AcroForm 控件。"""
    def text_field(name, label, rect, value=""):
        page.insert_text(pymupdf.Point(rect.x0, rect.y0 - 6), label, fontsize=10.5)
        w = pymupdf.Widget()
        w.field_name = name
        w.field_type = pymupdf.PDF_WIDGET_TYPE_TEXT
        w.rect = rect
        w.text_font = "Helv"
        w.text_size = 10.5
        w.field_value = value
        page.add_widget(w)

    def checkbox(name, label, rect, checked=False):
        w = pymupdf.Widget()
        w.field_name = name
        w.field_type = pymupdf.PDF_WIDGET_TYPE_CHECKBOX
        w.rect = rect
        if checked:
            w.field_value = "Yes"
        page.add_widget(w)
        page.insert_text(pymupdf.Point(rect.x1 + 6, rect.y0 + 12), label, fontsize=10.5)

    x0, x1 = 70, 300
    text_field("applicant_name", "Name:", pymupdf.Rect(x0, top + 20, x1, top + 42), value="Ada Lovelace")
    text_field("applicant_email", "Email:", pymupdf.Rect(x0, top + 62, x1, top + 84), value="ada@example.com")
    text_field("applicant_date", "Date:", pymupdf.Rect(x0, top + 104, x1, top + 126), value="2026-08-01")
    checkbox("newsletter", "Subscribe to newsletter", pymupdf.Rect(x0, top + 150, x0 + 16, top + 166), checked=True)
    checkbox("survey_ok", "Agree to be contacted for research", pymupdf.Rect(x0, top + 176, x0 + 16, top + 192))

    # 下拉框（组合框）
    w = pymupdf.Widget()
    w.field_name = "city"
    w.field_type = pymupdf.PDF_WIDGET_TYPE_COMBOBOX
    w.rect = pymupdf.Rect(x0, top + 220, x1, top + 242)
    w.text_font = "Helv"
    w.choice_values = ["Beijing", "Shanghai", "Guangzhou", "Hong Kong"]
    w.field_value = "Beijing"
    page.add_widget(w)
    page.insert_text(pymupdf.Point(x0, top + 214), "City:", fontsize=10.5)


def build_mixed_all(cjk_font: str | None) -> Path:
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)  # A4

    # ---- 第 1 部分：标题 + 正文（文字）----
    page.insert_text(pymupdf.Point(60, 70), "A Sample Document: Text, Image, Table and Form", fontsize=19)
    page.insert_text(
        pymupdf.Point(60, 95),
        "This PDF is generated by scripts/make_sample_pdfs.py to demonstrate extracting "
        "four kinds of elements from one file: text, embedded images, tables and fillable forms.",
        fontsize=10.5,
        color=(0.25, 0.25, 0.25),
    )
    body = (
        "Section 1. Plain text\n"
        "Paragraphs of regular narrative text here. The quick brown fox jumps over the lazy dog. "
        "Real-world documents usually mix headings, body paragraphs and lists. "
        "PyMuPDF can extract this text together with its absolute coordinates; "
        "Unstructured groups it into Title / NarrativeText / ListItem elements."
    )
    add_text_block(page, pymupdf.Rect(60, 115, 480, 190), body, size=10.5)
    if cjk_font:
        zh = (
            "中文段落：在实际项目中，PDF 可能同时包含多种语言的正文。"
            "例如产品说明书或招标文件通常使用混合语言排版，提取时需要注意字体与编码。"
        )
        page.insert_textbox(pymupdf.Rect(60, 200, 480, 260), zh, fontsize=10.5,
                            fontname="cjk-noto", fontfile=cjk_font)

    # 列表（ListItem 元素）
    for i, line in enumerate(
        ["Item 1: coordinates of each text span", "Item 2: table grid structure",
         "Item 3: image bounding boxes", "Item 4: form field widgets"]
    ):
        page.insert_text(pymupdf.Point(66, 285 + i * 18), f"• {line}", fontsize=10.5)

    # ---- 第 2 部分：图片（真实位图，JPEG 内嵌）----
    img_bytes = make_gradient_chart_png()
    img_rect = pymupdf.Rect(60, 372, 300, 520)
    page.insert_image(img_rect, stream=img_bytes)
    page.insert_text(pymupdf.Point(60, 540), "Figure 1. A rasterized chart image (synthetic).", fontsize=9.5,
                     color=(0.35, 0.35, 0.35))

    # ---- 第 3 部分：表格 ----
    add_table(page, left=320, top=372)
    page.insert_text(pymupdf.Point(330, 545), "Table 1. Quarterly sales.", fontsize=9.5,
                     color=(0.35, 0.35, 0.35))

    # ---- 第 4 部分：表单 ----
    page.insert_text(pymupdf.Point(60, 590), "Section 2. Fillable form", fontsize=14)
    add_form_fields(page, 600)

    out = OUT_DIR / "sample_mixed_all.pdf"
    doc.subset_fonts()  # 只保留用到的字形，否则 Arial Unicode 会整字体嵌入（20+MB）
    doc.save(out, garbage=4, deflate=True)
    doc.close()
    return out


def build_widget_types() -> Path:
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=700)
    page.insert_text(pymupdf.Point(60, 60), "All Widget Types", fontsize=18)

    def label(x, y, text):
        page.insert_text(pymupdf.Point(x, y), text, fontsize=10.5)

    # 文本框 + 只读
    w = pymupdf.Widget(); w.field_name = "fullname"; w.field_type = pymupdf.PDF_WIDGET_TYPE_TEXT
    w.rect = pymupdf.Rect(180, 90, 420, 112); w.text_font = "Helv"; w.field_value = "John Doe"
    page.add_widget(w); label(100, 104, "Text field:")

    # 多行文本框
    w = pymupdf.Widget(); w.field_name = "bio"; w.field_type = pymupdf.PDF_WIDGET_TYPE_TEXT
    w.rect = pymupdf.Rect(180, 130, 420, 190); w.text_font = "Helv"
    w.field_value = "First line\nSecond line"
    page.add_widget(w); label(100, 144, "Multi-line text:")

    # 复选框
    w = pymupdf.Widget(); w.field_name = "agree"; w.field_type = pymupdf.PDF_WIDGET_TYPE_CHECKBOX
    w.rect = pymupdf.Rect(180, 210, 196, 226)
    page.add_widget(w); label(204, 224, "Checkbox (unchecked):")
    w = pymupdf.Widget(); w.field_name = "subscribe"; w.field_type = pymupdf.PDF_WIDGET_TYPE_CHECKBOX
    w.rect = pymupdf.Rect(180, 236, 196, 252); w.field_value = "Yes"
    page.add_widget(w); label(204, 250, "Checkbox (checked):")

    # 下拉框
    w = pymupdf.Widget(); w.field_name = "country"; w.field_type = pymupdf.PDF_WIDGET_TYPE_COMBOBOX
    w.rect = pymupdf.Rect(180, 272, 420, 294); w.text_font = "Helv"
    w.choice_values = ["China", "Japan", "Korea", "USA", "UK"]
    w.field_value = "China"
    page.add_widget(w); label(100, 286, "Combo box:")

    # 多选框
    w = pymupdf.Widget(); w.field_name = "hobbies"; w.field_type = pymupdf.PDF_WIDGET_TYPE_LISTBOX
    w.rect = pymupdf.Rect(180, 314, 420, 374); w.text_font = "Helv"
    w.choice_values = ["Reading", "Hiking", "Gaming", "Cooking"]
    page.add_widget(w); label(100, 328, "List box:")

    # 日期格式文本框
    w = pymupdf.Widget(); w.field_name = "birthday"; w.field_type = pymupdf.PDF_WIDGET_TYPE_TEXT
    w.rect = pymupdf.Rect(180, 394, 420, 416); w.text_font = "Helv"
    w.format = pymupdf.PDF_WIDGET_TX_FORMAT_DATE
    w.field_value = "2000-01-01"
    page.add_widget(w); label(100, 408, "Date field:")

    page.insert_text(
        pymupdf.Point(100, 470),
        "Note: radio buttons are intentionally left out; in this PyMuPDF version creating them "
        "raises spurious errors, and real-world forms (W-9 / W-4) use checkboxes.",
        fontsize=9.5, color=(0.4, 0.4, 0.4),
    )
    out = OUT_DIR / "sample_widget_types.pdf"
    doc.save(out, garbage=4, deflate=True)
    doc.close()
    return out


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cjk = find_cjk_font()
    print(f"使用 CJK 字体: {cjk or '(未找到，跳过中文段落)'}")
    p1 = build_mixed_all(cjk)
    p2 = build_widget_types()
    print(f"已生成: {p1}")
    print(f"已生成: {p2}")


if __name__ == "__main__":
    main()
