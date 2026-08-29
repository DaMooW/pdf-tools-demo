#!/usr/bin/env python3
"""生成《PDF 四类元素 x 三个库 提取矩阵讲义》HTML。

spec: docs/spec/pdf-element-matrix-spec.md
产物: docs/pdf-element-matrix.html

数据（全部真实、可复现）：
  - 对象: data/generated/sample_mixed_all.pdf（make_sample_pdfs.py 一键生成）
  - 行1「PDF 原样」: 内容流/对象字典原码（按区域过滤）+ 该区域真实渲染图（base64 PNG）
  - 行2-4: PyMuPDF / Unstructured 现场运行结果；LlamaParse 为预期输出（需 API key，已标注）
"""

from __future__ import annotations

import base64
import re
import sys
from collections import Counter
from pathlib import Path

import pymupdf

EX_DIR = Path(__file__).resolve().parent.parent / "examples"
sys.path.insert(0, str(EX_DIR))
sys.path.insert(0, str(EX_DIR / "unstructured"))

ROOT = Path(__file__).resolve().parent.parent
PDF_PATH = ROOT / "data" / "generated" / "sample_mixed_all.pdf"
OUT_PATH = ROOT / "docs" / "pdf-element-matrix.html"

# --------------------------------------------------------------------------
# 0. 打开文档 & 区域定义（PyMuPDF 坐标：原点左上，y 向下）
# --------------------------------------------------------------------------
doc = pymupdf.open(PDF_PATH)
page = doc[0]
PW, PH = page.rect.width, page.rect.height

REGIONS = {
    "text":  ((40, 40, 500, 350), "文字", "标题 / 正文 / 中文段落 / 列表", "#1d4ed8"),
    "image": ((40, 352, 310, 555), "图片", "内嵌位图 + 题注", "#15803d"),
    "table": ((315, 352, 585, 555), "表格", "5x4 网格表 + 题注", "#b45309"),
    "form":  ((40, 560, 585, 842), "表单", "填写区（6 个 AcroForm 控件）+ 标签", "#7c3aed"),
}

# --------------------------------------------------------------------------
# 1. 区域渲染图（= 用阅读器/浏览器打开看到的样子）
# --------------------------------------------------------------------------
def render_region(rect) -> str:
    pix = page.get_pixmap(clip=pymupdf.Rect(*rect), dpi=140)
    return "data:image/png;base64," + base64.b64encode(pix.tobytes("png")).decode()


# --------------------------------------------------------------------------
# 2. 内容流分「组」，按区域过滤
# --------------------------------------------------------------------------
stream = b"".join(doc.xref_stream(x) for x in page.get_contents()).decode("latin-1")
groups = []
cur = []
for line in stream.splitlines():
    if line.strip():
        cur.append(line)
    else:
        if cur:
            groups.append(cur)
            cur = []
if cur:
    groups.append(cur)


def group_geometry(group):
    """返回 (类型名, 关键几何（PyMuPDF 坐标）, 说明)。"""
    for line in group:
        m = re.match(r"^([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+) cm$", line)
        if m:
            e, f = float(m.group(5)), float(m.group(6))
            return "img", (e, PH - f), "图片"
        m = re.match(r"^([-\d.]+) ([-\d.]+) ([\d.]+) ([\d.]+) re$", line)
        if m:
            x, y, w, h = (float(m.group(i)) for i in range(1, 5))
            return "table", (x, PH - y - h, x + w, PH - y), "表格单元"
        m = re.search(r"([-\d.]+) ([-\d.]+) Tm", line)
        if m:
            tx, ty = float(m.group(1)), float(m.group(2))
            return "text", (tx, PH - ty), "文本"
    return "?", (), ""


def inside(region, geom, pad=6.0) -> bool:
    x0, y0, x1, y1 = region
    if len(geom) == 2:
        px, py = geom
        return x0 - pad <= px <= x1 + pad and y0 - pad <= py <= y1 + pad
    px0, py0, px1, py1 = geom
    return not (px1 < x0 - pad or px0 > x1 + pad or py1 < y0 - pad or py0 > y1 + pad)


stream_src = {k: [] for k in REGIONS}
for group in groups:
    kind, geom, note = group_geometry(group)
    if geom == ():
        continue
    for key, (region, _, _, _) in REGIONS.items():
        if inside(region, geom):
            stream_src[key].extend(group)
            break


def esc(s: str) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def code_block(text: str, cap: int = 1400) -> str:
    text = text.rstrip()
    if not text:
        text = "（此元素原码见右侧说明）"
    if len(text) > cap:
        text = text[:cap] + " …"
    return "<pre class='src'>" + esc(text) + "</pre>"


# 表单原码 = Widget 注解对象字典（真实对象原文）
form_src_parts = []
seen = set()
for w in list(page.widgets() or []):
    key = w.field_name.split("[")[0]
    if key in seen:
        continue
    seen.add(key)
    form_src_parts.append("% " + w.field_type_string + " 字段: " + w.field_name + "\n"
                          + re.sub(r"\s+", " ", doc.xref_object(w.xref)))
    if len(seen) >= 2:
        break
form_src = "\n\n".join(form_src_parts)
stream_src["form"] = ["（控件不在内容流，实际源码是右侧的 Widget 注解对象）"]

# --------------------------------------------------------------------------
# 3. PyMuPDF 真实结果（按区域过滤/直接提取）
# --------------------------------------------------------------------------
pm = {}
blocks = []
for b in page.get_text("blocks"):
    x0, y0, x1, y1, txt, *_ = b
    if txt.strip() and inside(REGIONS["text"][0], (x0, y0, x1, y1)):
        blocks.append((round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1),
                       txt.strip().replace("\n", " ")))
pm["text"] = "\n".join(
    "bbox=({}, {}, {}, {})  {}".format(*b[:4], b[4][:40]) for b in blocks[:4]
) + "\n… 区域共 {} 个文本块".format(len(blocks))

img = page.get_images(full=True)[0]
ixref, _, _, iw, ih, *_ = img
irects = page.get_image_rects(ixref)
pm["image"] = (
    "xref={}  原始像素: {}x{}\n显示位置: {}\n\n"
    "Pixmap(doc, xref).save('fig.png') 即可得到原始分辨率的图片"
).format(ixref, iw, ih, irects[0] if irects else "n/a")

rows = page.find_tables().tables[0].extract()
pm["table"] = "\n".join(" | ".join(str(c or "") for c in row) for row in rows) + \
    "\n\n共 {} 行 x {} 列（含表头，find_tables 自动识别）".format(len(rows), len(rows[0]))

wlist = [(w.field_name.split("[")[0].split(".")[-1], w.field_type_string,
          getattr(w, "field_value", "")) for w in list(page.widgets() or [])]
pm["form"] = "\n".join("{:<14} {:<22} 值={!r}".format(t, n, v) for n, t, v in wlist) + \
    "\n\n填表: w.field_value='...'; w.update() → 另存新 PDF"

# --------------------------------------------------------------------------
# 4. Unstructured 真实结果（按元素 bbox 与区域求交过滤）
# --------------------------------------------------------------------------
els = []
try:
    import _compat  # noqa: F401
    _compat.install()
    from unstructured.partition.pdf import partition_pdf
    els = partition_pdf(str(PDF_PATH), strategy="fast")
except Exception as exc:
    print("unstructured 采集失败: {}".format(exc))

un = {}
for key, (region, _, _, _) in REGIONS.items():
    hits = []
    for e in els:
        c = e.metadata.coordinates
        if not c or not c.points:
            continue
        xs = [p[0] for p in c.points]
        ys = [p[1] for p in c.points]
        bbox = (min(xs), min(ys), max(xs), max(ys))
        if inside(region, bbox, pad=2):
            hits.append((e.category, e.text or ""))
    un[key] = hits

def un_view(key, limit=6):
    hits = un[key]
    if not hits:
        return "（该区域没匹配到任何元素）"
    body = "\n".join("[{}]  {}".format(cat, (txt or "").replace("\n", " ")[:38]) for cat, txt in hits[:limit])
    return body + "\n\n… 该区域共 {} 个文本类元素（无 Table / Image 元素）".format(len(hits))

# --------------------------------------------------------------------------
# 5. 每个库 x 每类元素：怎么提取 / 原理 / 结果
# --------------------------------------------------------------------------
CELLS = {}

CELLS["pymupdf"] = {
    "text": (
        'page.get_text("blocks")  /  get_text("words")',
        "解析内容流里的 Tj/TJ 指令，按字体度量算出字符位置，再经 ToUnicode CMap 转 Unicode；"
        "对象树级还原，无任何模型，所以文字 + 原生坐标都可获得",
        pm["text"],
    ),
    "image": (
        'page.get_images(full=True) → Pixmap(doc, xref).save(...)',
        "图片是 /Resources 里的 XObject 图像对象（JPEG/Flate 编码流）；PyMuPDF 按 xref 定位并解码像素，"
        "可提取到原始分辨率（本图 856x489 像素、显示 240x137pt）",
        pm["image"],
    ),
    "table": (
        'page.find_tables().tables[0].extract()',
        "PDF 没有表格对象，只有矩形/线段 + 文字；find_tables 做几何推理（求网格线交点）"
        "推断单元格，再按位置回填文字，得到行列结构",
        pm["table"],
    ),
    "form": (
        'list(page.widgets()) → w.field_name / field_type_string / field_value',
        "表单是页面 Annots 上的 Widget 注解对象（/T 名、/FT 类型、/V 值、/Rect 位置、/AP 外观）；"
        "读出来就是完整控件，改 /V + 重生成外观流即可「填表」",
        pm["form"],
    ),
}

CELLS["unstructured"] = {
    "text": (
        'partition_pdf(pdf, strategy="fast") → e.category / e.text / e.metadata.coordinates',
        "pdfminer 解析内容流并按边距聚块；再用规则启发式猜语义：短文本无句号→Title、"
        "bullet/数字前缀→ListItem、成句→NarrativeText、页面首尾→Header/Footer",
        un_view("text"),
    ),
    "image": (
        'strategy="hi_res" + extract_image_block_types=["Image"]（需 torch）',
        "fast 策略是纯文本分组，对位图完全无感知；hi_res 用版面模型（detectron2/YOLOX，需 torch）"
        "框出图片区域并导出——本机装不了 torch，所以 fast 之下只见题注",
        un_view("image"),
    ),
    "table": (
        'strategy="hi_res" + infer_table_structure=True（需 torch）',
        "同上：fast 无 Table 概念，把 20 个单元格当成 20 个散文本元素（还按启发式误判成 Title/ListItem）；"
        "hi_res 才用表格结构模型重建 Table 元素（text_as_html）",
        un_view("table"),
    ),
    "form": (
        '同 text：partition_pdf(strategy="fast")',
        "unstructured 只做文本层：把表单标签当普通文本分类，拿不到控件；"
        "且纯位置启发式会把页面中部的标签误判为 Title/Footer",
        un_view("form"),
    ),
}

LLAMA_EXPECTED = {
    "text": (
        'LlamaParse(api_key="…", result_type="markdown").get_json_result(pdf)[0]["markdown"]',
        "云端把整页渲染成图，用版面模型 + 大模型重建篇章结构（标题层级/段落/列表），并理解语义",
        "# A Sample Document: Text, Image, Table and Form\n\n"
        "This PDF is generated by scripts/make_sample_pdfs.py …\n\n"
        "## 中文段落：在实际项目中，PDF 可能同时包含多种语言\n\n"
        "- Item 1: coordinates of each text span\n- Item 4: form field widgets",
    ),
    "image": (
        'parser.get_json_result(pdf) → parser.get_images(result, download_path="img/")',
        "视觉模型识别图像区域并理解内容（能读出图里画了什么），图片以资产形式下载",
        "![Figure 1](image_asset_1.jpg)\n\n"
        "（云端还能给出图内容的文字描述 —— 这就是「读懂图」的能力）",
    ),
    "table": (
        'parser.get_json_result(pdf) → parser.get_tables(result, download_path="tbl/")',
        "表格结构模型/agentic 解析重建单元格关系，支持跨页合并，返回 Markdown/HTML",
        "| Product    | Qty | Unit Price | Subtotal |\n|------------|-----|------------|----------|\n"
        "| Desk Lamp  | 12  | $18.50     | $222.00  |\n| Floor Lamp | 5   | $59.00     | $295.00  |",
    ),
    "form": (
        '同 text：result_type="markdown" 解析',
        "把表单当作普通版面重建为可读文字（字段名 + 值），但拿不到控件与坐标",
        "## Section 2. Fillable form\n- Name: Ada Lovelace\n- Email: ada@example.com\n"
        "- Date: 2026-08-01  \n- City: Beijing",
    ),
}

# --------------------------------------------------------------------------
# 6. 组装 HTML
# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
# 6. 行1 渲染原理（面向计算机新手：怎么渲染出来的 + 术语表 + 乱码解释）
# --------------------------------------------------------------------------
PRINCIPLE = {
    "text": (
        [
            "把页面想成一块 595×842pt 的「画布」，内容流就是一张「作画指令单」，阅读器是照着指令单画画的小机器人。"
            "文字部分每次都是一套固定动作：q（保存状态）→ BT（进入「写字模式」）→ Tm（把笔尖挪到坐标）→ "
            "Tf（换字体和字号）→ TJ（写字）→ ET、Q（结束、定稿）。",
            "你看到的每个字，都是机器人按字体文件里存好的「字形」打出来的，位置由 Tm 的坐标决定——"
            "所以 PDF 里的文字既不是图片也不算纯文本，是「指令 + 字体」，这也是为什么能拿到每个字的精确坐标。",
            "「乱码」真相：TJ 行里 <412053...> 是十六进制编码的一串字节。英文部分直接就是字符编码（41=A）；"
            "中文部分是字体内部的「字形编号」（GID），要依靠嵌入字体附带的一张对照表（ToUnicode CMap）"
            "翻译回汉字。这张表不全或出错的 PDF，提取出来就是乱码。另一个坑是「子集化」：为了省空间，"
            "PDF 常把字体文件砍到只用到的几十个字形，字体名就被改成了 BNXTWZ+Nimbus... 这种带前缀的名字。",
        ],
        [
            ("q / Q", "把画笔状态存起来 / 恢复——保证每段文字的修改不影响其他部分"),
            ("BT / ET", "进入 / 退出「写字模式」（离开它写字符串是语法错误）"),
            ("Tm", "文本矩阵：6 个数字的快捷方式，最后两个是笔尖起点 x、y（坐标原点在左下角）"),
            ("Tf", "指定字体与字号（/helv 19 Tf = Helvetica 19 号）"),
            ("TJ", "写字；方括号里的负数（-50 等）是字距微调，单位 1/1000 字号"),
            ("<4120…>", "十六进制字节流：英文=ASCII；中文=字形编号 GID（靠 ToUnicode 表还原）"),
        ],
    ),
    "image": (
        [
            "图片部分只有两条指令：cm 把画布坐标系做「缩放 + 平移」（决定图片放哪、放多大），"
            "Do 把某个资源贴到当前坐标上——像把一张照片贴到墙上：先量好相框位置，再把照片按上去。",
            "照片的大文件本身不在这两条指令里，而是藏在 /Resources 目录下的一个「图像对象」"
            "（/Subtype /Image /Filter /DCTDecode，DCTDecode 就是 JPEG 解码器，/Width /Height 是像素尺寸）。"
            "阅读器执行 Do → 找到对象 → 解码像素 → 按 cm 的尺寸贴到页面上。",
        ],
        [
            ("cm", "变换矩阵 [a b c d e f]：a d=缩放，e f=平移（这里=缩放到 240×137pt 并移到 (60,327)）"),
            ("Do", "把 /Resources 里名为 fzImg0 的图片资源「贴上」当前坐标"),
            ("/Subtype /Image", "这是一个图像对象（XObject），存储像素数据"),
            ("/Filter /DCTDecode", "像素流是 JPEG 压缩的（DCTDecode=JPEG 解码器）"),
            ("/Width /Height", "原始像素尺寸：856×489（存原图靠它解出来）"),
        ],
    ),
    "table": (
        [
            "表格在 PDF 里没有「表格」这个对象——它就像自己画格子再往里写字：每一格先 re 画一个矩形路径，"
            "再用 .45 .45 .45 RG（灰色）+ S（描边）把矩形边框画成格子线，最后 BT…TJ 往格子里写字。",
            "整张表 = 20 个矩形 + 20 条文字，所以阅读器也只是「画框写字」，它根本不知道这是表格。"
            "「认出这是表、每行每列是什么」必须额外推理：PyMuPDF 用几何法（找网格线交叉点），"
            "Unstructured/LlamaParse 用模型（视觉认出「这是表格」）。",
        ],
        [
            ("re", "矩形路径：x y w h（本表每格 85×26pt 的框）"),
            ("w", "线宽（0.8pt：格子线的粗细）"),
            ("h", "把矩形路径闭合（首尾相连）"),
            ("RG", "描边颜色（0.45 0.45 0.45 = 灰色）"),
            ("S", "描边——「把线画出来」的指令，就是这一步才真正画出格子线"),
        ],
    ),
    "form": (
        [
            "表单和上面三种不一样：它不是画在内容流里，而是「贴在页面上的电子标签」——挂在页面对象"
            "的 /Annots（注释数组）里的 Widget 注解对象。可以类比成：页面是实体文件，控件是贴上的一张"
            "「可填写的透明贴纸」。",
            "阅读器的工作是：先按内容流画出页面（比如 Name: 这些标签文字），再依 /Rect 的位置叠加显示控件，"
            "并按 /AP（外观流）把框和字画出来；你输入文字时，值被写进 /V 字段。",
            "所以「提取表单」= 读这些注解对象（PyMuPDF 的 page.widgets()）；「填表」= 改写 /V 并重新生成外观流。",
        ],
        [
            ("/Type /Annot /Subtype /Widget", "这是一个「控件注释」对象——不是页面内容，是附加功能"),
            ("/FT /Tx", "字段类型：Tx=文本框（Ch=复选框，Btn=按钮）"),
            ("/T (applicant_name)", "字段名：程序靠它找到这个框"),
            ("/Rect [70 200 300 222]", "控件在页面上的位置和大小"),
            ("/V (Ada Lovelace)", "当前填写值——「填表」的本质就是改写这个值"),
            ("/AP …", "外观流：控件长什么样（框、底纹、字体）的绘制指令"),
        ],
    ),
}

CELLS["llamaparse"] = dict(LLAMA_EXPECTED)

CSS = """
:root{--ink:#1f2430;--mut:#6b7280;--bg:#f6f8fb;--card:#fff;--bd:#dbe0e6}
*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;color:var(--ink);background:var(--bg);line-height:1.7}
header{background:linear-gradient(120deg,#0f172a,#1e3a8a);color:#fff;padding:30px 36px}
header h1{margin:0 0 8px;font-size:24px}
header p{margin:3px 0;color:#cbd5e1;font-size:13.5px}
.wrap{max-width:1400px;margin:22px auto;padding:0 18px 80px}
.legend{display:flex;gap:18px;flex-wrap:wrap;font-size:13px;margin:14px 0;background:#fff;border:1px solid var(--bd);border-radius:10px;padding:10px 16px}
.legend b{color:#334155}
.scroll{overflow-x:auto;border:1px solid var(--bd);border-radius:12px;background:#fff;box-shadow:0 1px 3px rgba(0,0,0,.05)}
table{border-collapse:collapse;min-width:1320px;width:100%;font-size:13px}
th,td{border:1px solid var(--bd);padding:10px;vertical-align:top}
th{background:#f1f5f9;font-size:14px}
th .tag{display:inline-block;border-radius:6px;padding:2px 10px;color:#fff;font-size:13px;margin-bottom:4px}
.rowhead{background:#f8fafc;width:118px;font-weight:700;writing-mode:initial;text-align:left;vertical-align:top}
.rowhead .lib{font-size:13.5px}
.rowhead .none{color:var(--mut);font-weight:400;font-size:12px}
.cell{padding:2px}
img.snap{width:100%;max-width:210px;border:1px solid var(--bd);border-radius:6px;display:block;margin:6px 0}
pre.src{background:#0f172a;color:#dbe7f3;border-radius:8px;padding:10px 12px;font-size:11.5px;line-height:1.55;overflow-x:auto;max-width:330px;margin:6px 0;font-family:ui-monospace,Menlo,Consolas,monospace;white-space:pre}
pre.src.soft{background:#f6f8fa;color:#334155;border:1px solid var(--bd);max-height:220px;overflow-y:auto}
.lbl{font-size:12px;font-weight:700;color:#64748b;border-bottom:1px dashed #cbd5e1;margin:8px 0 2px;text-transform:uppercase;letter-spacing:.4px}
.hint{font-size:12px;color:#64748b}
.tiny{font-size:11.5px;color:#64748b;marggin-top:2px}
.prin{margin:4px 0}
.prin p{margin:4px 0 8px;font-size:12.5px;color:#334155}
table.gloss{border-collapse:collapse;width:100%;margin:4px 0 8px}
table.gloss td{border:1px solid #e5e7eb;padding:5px 7px;font-size:12px;background:#fff}
table.gloss td.tk{width:110px;word-break:break-all}
table.gloss code{background:#eef2f7;border-radius:3px;padding:0 4px;font-size:11.5px}
.warn{background:#fffbeb;border:1px solid #fde68a;border-radius:6px;padding:4px 8px;font-size:12px;margin:4px 0}
code{background:#eef2f7;border-radius:3px;padding:0 4px;font-size:12px;font-family:ui-monospace,Menlo,Consolas,monospace}
footer{margin-top:30px;font-size:12.5px;color:#64748b}
"""

def lib_cell_html(lib_key, type_key, color):
    how, prin, result = CELLS[lib_key][type_key]
    if lib_key == "llamaparse":
        warn = "<div class='warn'>⚠️ 预期输出（需 LLAMA_CLOUD_API_KEY + 网络，云端解析）</div>"
    else:
        warn = ""
    return (
        "<div class='cell'>" + warn
        + "<div class='lbl'>怎么提取</div><div>" + esc(how) + "</div>"
        + "<div class='lbl'>原理</div><div>" + esc(prin) + "</div>"
        + "<div class='lbl'>提取结果（真实输出）</div>"
        + "<pre class='src soft'>" + esc(result) + "</pre>"
        + "</div>"
    )

def row1_cell_html(type_key, color, name):
    region, label, desc, col = REGIONS[type_key]
    src_map = {
        "text": "\n".join(stream_src["text"][:40]),
        "image": "\n".join(stream_src["image"][:8]),
        "table": "\n".join(stream_src["table"][:9]) + "\n… （共 %d 行，其余为同样式重复）" % len(stream_src["table"]),
        "form": form_src,
    }
    note = {
        "text": "原码里没有标题/正文/列表的任何标记 —— 只有坐标、字体、字号",
        "image": "整张图在内容流只占 2 行；像素数据在图像对象里",
        "table": "20 个矩形 + 20 条文字 = 表格；PDF 没有「表格对象」",
        "form": "控件不在内容流，而是页面 Annots 上的 Widget 对象",
    }[type_key]
    paras, terms = PRINCIPLE[type_key]
    para_html = "".join("<p>" + esc(p) + "</p>" for p in paras)
    terms_html = "".join(
        "<tr><td class='tk'><code>" + esc(k) + "</code></td><td>" + esc(v) + "</td></tr>"
        for k, v in terms
    )
    return (
        "<div class='cell'>"
        + "<div class='lbl'>PDF 原码</div>"
        + code_block(src_map[type_key])
        + "<div class='hint'>" + note + "</div>"
        + "<div class='lbl'>怎么渲染出来的（新手版）</div>"
        + "<div class='prin'>" + para_html + "</div>"
        + "<table class='gloss'>" + terms_html + "</table>"
        + "<div class='lbl'>阅读器/浏览器打开的样子</div>"
        + "<img class='snap' src='" + render_region(region) + "' alt='" + esc(name) + " 区域渲染'>"
        + "</div>"
    )

head_cells = ""
for type_key, (region, name, desc, color) in REGIONS.items():
    head_cells += "<th><span class='tag' style='background:" + color + "'>" + name + "</span><br>" \
                  "<span class='hint'>" + esc(desc) + "</span></th>"

row1 = "<tr><td class='rowhead'>PDF 原样<br><span class='none'>原码 + 渲染效果</span></td>" \
       + "".join("<td>" + row1_cell_html(k, v[3], v[1]) + "</td>" for k, v in REGIONS.items()) + "</tr>"

ROWS = [("PyMuPDF", "pymupdf", "对象树级：快、准、本地，无模型"),
        ("Unstructured", "unstructured", "版面分组 + 规则启发式（本机 fast 策略）"),
        ("LlamaParse", "llamaparse", "云端大模型语义重建（需 API Key + 网络）")]

body_rows = ""
for title, key, sub in ROWS:
    cells = ""
    for type_key in REGIONS:
        color = REGIONS[type_key][3]
        cells += "<td>" + lib_cell_html(key, type_key, color) + "</td>"
    body_rows += "<tr><td class='rowhead'><div class='lib'>" + title + "</div>" \
                 "<div class='none'>" + esc(sub) + "</div></td>" + cells + "</tr>"

html_doc = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>PDF 四类元素 x 三个库：提取矩阵讲义</title>
<style>__CSS__</style>
</head>
<body>
<header>
<h1>PDF 四类元素 x 三个库 —— 提取矩阵</h1>
<p>对象：__PDF__（第 1 页；四类元素在同一页，坐标由生成脚本确定）</p>
<p>行 = 分析者（PDF 本身 / 三个库）；列 = 元素类型。PyMuPDF 与 Unstructured 的「提取结果」为真实运行输出，LlamaParse 行为预期输出（需 API Key）。</p>
</header>
<div class="wrap">
<div class="legend">
<span><b>行</b>：第 1 行 = PDF 原码 + 渲染效果；第 2-4 行 = 三个库的「怎么提取 / 原理 / 提取结果」</span>
<span><b>颜色</b>：<span style="color:#1d4ed8">■ 文字</span> <span style="color:#15803d">■ 图片</span> <span style="color:#b45309">■ 表格</span> <span style="color:#7c3aed">■ 表单</span></span>
</div>
<div class="scroll">
<table>
<tr><th style="width:118px">分析者 ↓ / 元素类型 →</th>__HEAD__</tr>
__ROW1____ROWS__
</table>
</div>
<footer>
复现：<code>.venv/bin/python scripts/make_sample_pdfs.py</code> →
<code>.venv/bin/python scripts/build_matrix_html.py</code>（LLamaParse 列内容需 key 后手动验证）<br>
生成脚本：scripts/build_matrix_html.py · 设计规格：docs/spec/pdf-element-matrix-spec.md
</footer>
</div>
</body>
</html>"""

html_doc = (html_doc
            .replace("__CSS__", CSS)
            .replace("__HEAD__", head_cells)
            .replace("__ROW1__", row1)
            .replace("__ROWS__", body_rows)
            .replace("__PDF__", esc(PDF_PATH.name)))

OUT_PATH.write_text(html_doc, encoding="utf-8")
print("已生成: {}".format(OUT_PATH))
print("大小: {:.0f} KB | 元素总数: {} | 流分组: {} | 文本块: {}".format(
    OUT_PATH.stat().st_size / 1024, len(els), len(groups), len(blocks)))
doc.close()
