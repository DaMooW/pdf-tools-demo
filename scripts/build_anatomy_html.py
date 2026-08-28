#!/usr/bin/env python3
"""生成《PDF 内容流逐行解剖讲义》HTML。

材料来源（全部来自本仓库、真实可复现）：
  1. data/generated/sample_mixed_all.pdf 的内容流（doc.xref_stream 解码原文）
  2. PyMuPDF 视角：文本块坐标 / 词坐标 / 图片 / 表格 / 控件（真实运行结果）
  3. Unstructured fast 视角：36 个元素的分类结果（真实运行结果）
  4. LlamaParse 视角：API 用法与"预期输出示意"（需 key，云端运行）

产物：docs/pdf-content-stream-anatomy.html（纯 HTML+CSS，离线可打开）
运行：.venv/bin/python scripts/build_anatomy_html.py
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

import pymupdf

EX_DIR = Path(__file__).resolve().parent.parent / "examples"
sys.path.insert(0, str(EX_DIR))
sys.path.insert(0, str(EX_DIR / "unstructured"))

ROOT = Path(__file__).resolve().parent.parent
PDF_PATH = ROOT / "data" / "generated" / "sample_mixed_all.pdf"
OUT_PATH = ROOT / "docs" / "pdf-content-stream-anatomy.html"

# --------------------------------------------------------------------------
# 1. 读取内容流与页面对象信息
# --------------------------------------------------------------------------
doc = pymupdf.open(PDF_PATH)
page = doc[0]
PAGE_W, PAGE_H = page.rect.width, page.rect.height
stream = b"".join(doc.xref_stream(x) for x in page.get_contents()).decode("latin-1")
lines = stream.splitlines()

# span 索引：用于把内容流里的 TJ hex 串还原成可读文字
spans = [
    (s["bbox"], s["text"], s["origin"], s["font"], s["size"])
    for block in page.get_text("dict")["blocks"]
    if block.get("type") == 0
    for line in block["lines"]
    for s in line["spans"]
]
img_info = page.get_images(full=True)
img_xref = img_info[0][0]
img_obj = doc.xref_object(img_xref)
fonts = page.get_fonts()

# --------------------------------------------------------------------------
# 2. 内容流逐行分类 + 文字还原
# --------------------------------------------------------------------------
def decode_tj(line: str) -> str:
    """从 [<hex>]TJ 行还原显示文字：优先用 span 坐标匹配，失败则尝试 ascii。"""
    m_tm = re.match(r"^\d+(\.\d+)? \d+(\.\d+)? \d+(\.\d+)? \d+(\.\d+)? ([\d.]+) ([\d.]+) Tm$", line)
    try:
        # 取最近一次 Tm 的基线坐标（y 轴朝上 -> 转 PyMuPDF 的 y 朝下）
        ty = _last_tm[1]
        tx = _last_tm[0]
        py = PAGE_H - ty
        best, best_d = None, 8.0
        for (bbox, text, origin, font, size) in spans:
            d = abs(origin[1] - py)
            if d < best_d and abs(origin[0] - tx) < 60:
                best, best_d = text, d
        if best:
            return best
    except Exception:
        pass
    hexes = re.findall(r"<([0-9a-fA-F]+)>", line)
    try:
        raw = b"".join(bytes.fromhex(h) for h in hexes)
        return raw.decode("utf-16-be", errors="ignore") or raw.decode("ascii", errors="ignore")
    except Exception:
        return ""


_last_tm = (0.0, 0.0)

OP_LABELS = [
    (re.compile(r"^q$"), "q", "保存绘图状态入栈"),
    (re.compile(r"^Q$"), "Q", "弹栈，恢复之前的状态"),
    (re.compile(r"^BT$"), "BT", "开始文本块（文字输出的开关）"),
    (re.compile(r"^ET$"), "ET", "结束文本块"),
    (re.compile(r"^[-\d. ]+ Tm$"), "Tm", "设置文本矩阵（基线起点 x y）"),
    (re.compile(r"^/[^\s]+ [\d.]+ Tf$"), "Tf", "指定字体与字号"),
    (re.compile(r"^.* Tm .*Tf \[.*\]TJ$"), "TJ", "一行内：设文本矩阵 + 字体 + 显示文本（紧凑写法）"),
    (re.compile(r"^/[^\s]+ [\d.]+ Tf \[.*\]TJ$"), "TJ", "设置字体并显示文本（常见紧凑写法）"),
    (re.compile(r"^\[.*\]TJ$"), "TJ", "显示文本（数字=字间距微调）"),
    (re.compile(r"^\(.*\)Tj$"), "Tj", "显示文本（简单形式）"),
    (re.compile(r"^[-\d. ]+ cm$"), "cm", "变换矩阵（平移/缩放）"),
    (re.compile(r"^/[^\s]+ Do$"), "Do", "绘制图片资源"),
    (re.compile(r"^[-\d. ]+ re$"), "re", "画矩形路径"),
    (re.compile(r"^[\d.]+ w$"), "w", "设置线宽"),
    (re.compile(r"^h$"), "h", "闭合路径"),
    (re.compile(r"^S$"), "S", "描边"),
    (re.compile(r"^[\d. ]+ RG$"), "RG", "设置描边颜色"),
    (re.compile(r"^[\d. ]+ rg$"), "rg", "设置填充颜色"),
    (re.compile(r"^[-\d. ]+ m$"), "m", "移动到点"),
    (re.compile(r"^[-\d. ]+ l$"), "l", "画直线到点"),
]

ANNOTATIONS: dict[str, str] = {
    "q": "状态的快照：之后对线宽/颜色的修改都会在 Q 时被撤销（所以每个小元素都成对出现 q…Q）",
    "Q": "撤销本组 q 之后的所有状态修改",
    "BT": "文字写入器打开。PDF 规定：离开 BT/ET 之外写字符串是语法错误",
    "ET": "文字写入器关闭。这一组 q BT … ET Q 就是「一条文本」",
    "Tf": "/helv 19 Tf → 用 Helvetica 内置字体、19 号字。字体对象单独存在 /Resources 里",
    "Tm": "文本矩阵的 6 个数是 [a b c d e f]，最后两个 = 基线起点 x、y（PDF 坐标：原点在左下角，y 朝上）",
    "TJ": "方括号数组 = 多个字符串 + 数字。数字是字间距补偿（负数为贴近，正数为拉开），单位是 1/1000 字号",
    "cm": "拼装变换矩阵 [a b c d e f]：这里 240 0 0 137.1 60 327.4 = 缩放 240x137 后平移到 (60, 327.4)，即图片的显示位置",
    "Do": "把 /Resources 里的图片资源 /fzImg0 贴到当前变换的位置——这就是「图片」在 PDF 里的全部存在形式",
    "re": "矩形路径：x y w h。表格的每个单元格就是这样一个矩形（描边=画格子线）",
    "w": "线宽 0.8pt（表框线粗细）",
    "h": "把矩形路径闭合",
    "S": "沿路径描边——「画出一根线」就是它",
    "RG": "描边颜色 0.45 灰（格子的灰线颜色）",
}

def classify(line: str):
    if not line.strip():
        return None
    for pat, key, desc in OP_LABELS:
        if pat.match(line):
            return key, desc
    return "?", "其他指令"

def annotate_line(line: str, row_idx: int) -> tuple[str, str, str]:
    """返回 (类型key, 短说明, 长说明)"""
    if not line.strip():
        return "blank", "", ""
    cls = classify(line)
    if cls is None:
        return "blank", "", ""
    key = cls[0]
    if key in ("TJ", "Tj"):
        text = decode_tj(line)
        shown = text if text else "(无法还原,hex 为字形码)"
        return key, "显示文本", shown
    return key, ANNOTATIONS.get(key, cls[1]), ""

# 预扫描：给每行附上处理中需要的 Tm 上下文
restored_lines = []   # (整数行号, 原文, key, 短注, 长注)
_last_tm = (0.0, 0.0)
for i, line in enumerate(lines):
    # Tm 可能单独一行（标题）也可能与 Tf/TJ 同行（中文段），统一从整行提取
    m = re.search(r"([-\d.]+) ([-\d.]+) Tm", line)
    if m:
        _last_tm = (float(m.group(1)), float(m.group(2)))
    key, short, long_ = annotate_line(line, i)
    restored_lines.append((i + 1, line, key, short, long_))

# --------------------------------------------------------------------------
# 3. 收集三个库的"真实视图"
# --------------------------------------------------------------------------
# 3.1 PyMuPDF：文本块（带坐标）
blocks = []
for b in page.get_text("blocks"):
    x0, y0, x1, y1, text, *_ = b
    if text.strip():
        blocks.append((x0, y0, x1, y1, text.strip().replace("\n", " ")))

# 3.2 PyMuPDF：词级坐标（前 5 个词）
words = page.get_text("words")[:6]

# 3.3 表格
table_rows = page.find_tables().tables[0].extract()

# 3.4 控件
widgets = [
    (w.field_name, w.field_type_string, getattr(w, "field_value", ""),
     [round(v, 1) for v in w.rect]) for w in page.widgets() or []
]

# 3.5 Unstructured 元素（fast 策略）
els = []
try:
    import _compat  # noqa: F401  (Intel Mac 上让 fast 策略可用的兼容桩)
    _compat.install()
    from unstructured.partition.pdf import partition_pdf
    elements = partition_pdf(str(PDF_PATH), strategy="fast")
    els = [(e.category, e.metadata.page_number, (e.text or "")) for e in elements]
except Exception as exc:  # 防御：讲义不应因为环境问题而失效
    els = []
    print(f"unstructured 元素采集失败（讲义中该节会显示为空）: {exc}")

# --------------------------------------------------------------------------
# 4. 组装 HTML
# --------------------------------------------------------------------------
def esc(s: str) -> str:
    return html.escape(str(s), quote=False)

# 逐行渲染
stream_rows = []
color_map = {
    "q": "st", "Q": "st", "BT": "tx", "ET": "tx", "Tm": "tx", "Tf": "font",
    "TJ": "text", "Tj": "text", "cm": "img", "Do": "img2", "re": "draw",
    "w": "draw", "h": "draw", "S": "draw", "RG": "draw", "rg": "draw",
    "m": "draw", "l": "draw", "blank": "",
}
key_notes = {
    "TX01": "标题：一句话就是一行 BT/Tm/Tf/TJ —— 标题在 PDF 里**没有**任何标记，它只是“第 4 行 y=772 处、19 号字”的文本",
    "TX02": "正文：一样的指令重复多次。字体 10.5pt、灰色 (.25 .25 .25)——注意 PDF 里**没有“正文”这个名词**，这些都是“外观”",
    "CNL": "中文：字符串被编码成 Hex 紧凑形式 <...>，还原靠字体的 ToUnicode 表（这也是 TTC 字体容易翻车的地方）",
    "LIST": "列表项：**和普通文本完全没有区别**——bullet • 只是行首一个字。谁“认出”它是列表，谁就要多做语义工作",
    "IMG": "图片：一条 cm + 一条 Do，仅此而已。图片的像素数据在 /Resources 的图像对象里（DCTDecode = JPEG）",
    "TBL": "表格：每个单元格 = 一个灰色矩形 (re/w/h/RG/S) + 一串文字。101 行全是这个模式——表格是“画出来的文字”，PDF 没有表格对象",
    "FORM": "表单控件**不在内容流里**！它们挂在 /Annots 注释数组上（Widget 注解）。内容流只是“空表皮的文字”",
    "CAP": "题注：Figure 1. / Table 1. 在 PDF 里也只是普通文本，没有任何“题注对象”",
}

seg_start = 1  # 第一个非空段开始行号
seg_ids = {}

# 划分片段（按空行分段），并给关键段打标签
segments = []
cur = []
for lineno, line, key, short, long_ in restored_lines:
    if key == "blank":
        if cur:
            segments.append((seg_start, lineno - 1, cur))
            cur = []
    else:
        if not cur:
            seg_start = lineno
        cur.append((lineno, line, key, short, long_))
if cur:
    segments.append((seg_start, len(restored_lines), cur))

def seg_label(seg) -> str:
    texts = [long_ for (_, _, key, short, long_) in seg if key == "TJ" and long_]
    head = texts[0] if texts else ""
    if "A Sample Document" in head:
        return "标题行（txt）", "TX01"
    if "This PDF is generated" in head:
        return "引言（txt）", "TX02"
    if "中文段落" in head[0:6]:
        return "中文段落（txt）", "CNL"
    if head.startswith("Item"):
        return "列表项（txt）", "LIST"
    if any(k == "Do" for (_, _, k, *_ ) in seg):
        return "图片（img）", "IMG"
    if any(k == "re" for (_, _, k, *_ ) in seg):
        return "表格单元格（draw+txt）", "TBL"
    if "Section 2" in head or "Name:" in head or "Email:" in head or "Date:" in head or "City:" in head or "Subscribe" in head or "Agree" in head:
        return "表单标签（txt，控件在别处）", "FORM"
    if "Figure 1." in head or "Table 1." in head:
        return "题注（txt）", "CAP"
    return head[:40] or "空段", ""

seg_rows = []
for start, end, rows in segments:
    label, note_key = seg_label(rows)
    span = f"L{start}-{end}" if start != end else f"L{start}"
    rows_html = []
    for (lineno, line, key, short, long_) in rows:
        cls = color_map.get(key, "")
        if key == "TJ" and long_:
            note_html = esc(long_)
            note_cls = "showtext"
        elif key == "blank":
            note_html, note_cls = "", ""
        else:
            note_html, note_cls = "", ""
        rows_html.append(
            f'<div class="srow {cls}"><span class="ln">{lineno}</span>'
            f'<code>{esc(line) or "&nbsp;"}</code>'
            + (f'<span class="nt {note_cls}">{note_html}</span>' if note_html else "")
            + "</div>"
        )
    badge = f'<span class="keybadge">{note_key}</span>' if note_key else ""
    seg_rows.append(f"""
<div class="seg">
  <div class="segh">{badge}<b>{esc(label)}</b><span class="segspan">{span} · {len(rows)} 行</span></div>
  <div class="segbody">{''.join(rows_html)}</div>
</div>""")

# 重点行卡片（深度讲解）
key_cards = [
    ("重点 1 · 标题：一行文本的完整生命周期", "TX01",
     "<b>第 3-6 行</b>：`BT` 开块 → `Tm` 挪到 (60,772) → `/helv 19 Tf` 设字体 → `[&lt;hex&gt;]TJ` 写字 → `ET` 关块。<br>"
     "这就是 <b>PDF 里“一段文字”的全部</b>。三个库看到的是同一串指令：PyMuPDF 忠实还原（还带上 y=772 的坐标），"
     "Unstructured 发现它“很短、没有句号、字号 19pt 比别的都大” → 猜它是 <b>Title</b>；LlamaParse 则把整页视为图像，"
     "让大模型「认」出这是个 <b>标题</b>（顺便理解语义：这是一份文档的题目）。"),
    ("重点 2 · TJ 里的负数：字符间距（kerning）", "TX02",
     "`[&lt;B&gt;-50(...)...]TJ` 中的 `-50` 是字间距微调（单位=1/1000 字号），负值让字母「贴」在一起。"
     "<b>这说明 P 与 F 的间距并不相等</b>——所以“逐字符坐标”必须跟着 TJ 里的补偿数字算，"
     "这正是 PyMuPDF `get_text(\"words\")` 里每个词都有独立 bbox 的原因。"),
    ("重点 3 · 中文为什么是 &lt;hex&gt; 串", "CNL",
     "`&lt;20bc38163e4456...&gt;` 是紧凑的十六进制字符串，每个字符 2 字节。这里的字节<b>不是 Unicode</b>，"
     "而是<b>字体内的字形编号（GID）</b>：Arial Unicode 被「子集化」后嵌入（字体名带随机前缀），"
     "再靠字体里的 <b>ToUnicode CMap</b> 把 GID 映射回汉字。映射错了提取就乱码——"
     "本仓库生成样例时就踩过：PingFang.ttc 子集化后「落」字被映射成兼容字符 U+F934。"),
    ("重点 4 · 图片：cm + Do 就是全部", "IMG",
     "第 53-54 行：`240 0 0 137.1028 60 327.4486 cm` + `/fzImg0 Do`。之前 398 行的“程序”里，"
     "图片占 2 行。<b>像素数据</b>在 /Resources 的图像对象中（本页是 856×489 的 JPEG，`/Filter /DCTDecode`）。"
     "PyMuPDF 按 xref 解码成像素（能存出原始分辨率 PNG）；Unstructured fast 对图片<b>毫无感知</b>；"
     "LlamaParse 渲染整页后视觉识别图片内容（能读懂图「画了什么」）。"),
    ("重点 5 · 表格：20 个灰色矩形 + 文字（PDF 里没有“表”）", "TBL",
     "每个单元格都是 6 行固定套路：`re`（矩形框）+ `.8 w`（线宽）+ `h`（闭合）+ `.45 .45 .45 RG S`（描边灰线）"
     "然后一段文字。整张表 = <b>20 个矩形 + 20 条文本</b>，没有“表格对象”。"
     "所以：PyMuPDF 用几何法（find_tables 求线段交点）还原 5×4 行列；Unstructured fast 把 20 个格子的文字"
     "当成 20 个独立元素（还错把 Product 判成 Title）；LlamaParse 靠视觉模型认出「这是一张表」并重建单元格关系。"),
    ("重点 6 · 表单：控件根本不在内容流里", "FORM",
     "表单区的内容流里只有标签文字（Name: / Email: / …）。真正能输入的控件是挂在页对象 `/Annots` 数组上的"
     " <b>Widget 注释</b>：`/FT /Tx`（文本）、`/T (applicant_name)`（字段名）、`/V (Ada Lovelace)`（值）、`/DA`（样式）。"
     "所以只有读取注释树的库（PyMuPDF）才能「看到」控件并填写；Unstructured/LlamaParse 只是把表单文字结构化。"
     "本页 6 个控件：applicant_name / applicant_email / applicant_date / newsletter / survey_ok / city。"),
]

# PyMuPDF 视图区
blocks_html = "<br>".join(
    f"<code>({x0:.1f}, {y0:.1f}, {x1:.1f}, {y1:.1f})</code>  {esc(t[:46])}" for x0, y0, x1, y1, t in blocks
)
words_html = "<br>".join(
    f"<code>({w[0]:.1f}, {w[1]:.1f}, {w[2]:.1f}, {w[3]:.1f})</code>  <b>{esc(w[4])}</b>" for w in words
)
table_html = "<br>".join(" | ".join(esc(str(c)) for c in row) for row in table_rows)
widgets_html = "<br>".join(
    f"<b>{esc(name)}</b> — {esc(typ)}，值='{esc(val)}'，<code>{rect}</code>"
    for name, typ, val, rect in widgets
)
img_obj_short = re.sub(r"\s+", " ", img_obj)[:200]
fonts_html = "<br>".join(
    f"<code>#{f[0]}</code> {esc(f[1])} {esc(f[2])} <b>{esc(f[3])}</b>" for f in fonts
)

# Unstructured 视图区
el_color = {
    "Title": "c-title", "NarrativeText": "c-nar", "ListItem": "c-list",
    "UncategorizedText": "c-uncat", "Footer": "c-footer", "Header": "c-header",
}
els_html = "<br>".join(
    f'<span class="cat {el_color.get(cat, "")}">{esc(cat)}</span> {esc(text[:58])}'
    for cat, pno, text in els
)

# LlamaParse 示意
llama_example = """# A Sample Document: Text, Image, Table and Form

This PDF is generated by scripts/make_sample_pdfs.py to demonstrate extracting four kinds of elements...

## 中文段落：在实际项目中...

- Item 1: coordinates of each text span
- Item 2: table grid structure
- Item 3: image bounding boxes
- Item 4: form field widgets

![Figure 1](image_asset_1.jpg)

| Product     | Qty | Unit Price | Subtotal |
|-------------|-----|------------|----------|
| Desk Lamp   | 12  | $18.50     | $222.00  |
| Floor Lamp  | 5   | $59.00     | $295.00  |
| Total       | 25  | -          | $755.00  |

## Section 2. Fillable form
- Name: Ada Lovelace
- Email: ada@example.com ..."""

html_doc = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>PDF 内容流逐行解剖：文字·图片·表格·列表·表单 如何被三个库解析</title>
<style>
:root{--ink:#1f2430;--mut:#6b7280;--bg:#fafbfc;--card:#fff;--acc:#2563eb;
--code:#f6f8fa;--tx:#1d4ed8;--font:#7c3aed;--text:#0f766e;--draw:#b45309;
--img:#15803d;--img2:#166534;--st:#64748b;--cur:#fff7e6}
*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;color:var(--ink);background:var(--bg);line-height:1.75}
header{background:linear-gradient(120deg,#0f172a,#1e3a8a);color:#fff;padding:34px 40px}
header h1{margin:0 0 10px;font-size:26px}
header p{margin:4px 0;color:#cbd5e1;font-size:14px}
main{max-width:1080px;margin:24px auto;padding:0 20px 80px}
h2{font-size:21px;margin:48px 0 14px;border-left:5px solid var(--acc);padding-left:12px}
h3{font-size:16px;margin:22px 0 8px;color:#0f172a}
.card{background:var(--card);border:1px solid #e5e7eb;border-radius:10px;padding:18px 20px;margin:14px 0;box-shadow:0 1px 2px rgba(0,0,0,.04)}
code{background:#eef2f7;border-radius:4px;padding:1px 5px;font-size:13px;font-family:ui-monospace,Menlo,Consolas,monospace}
pre{background:#0f172a;color:#e2e8f0;border-radius:8px;padding:14px 16px;overflow-x:auto;font-size:12.5px;line-height:1.6;font-family:ui-monospace,Menlo,Consolas,monospace}
.muted{color:var(--mut);font-size:13px}
.ok{color:#15803d}.warn{color:#b45309}.err{color:#b91c1c}
/* 流逐行 */
.stream{border:1px solid #e5e7eb;border-radius:10px;overflow:hidden;background:#fff}
.seg{border-bottom:1px dashed #e5e7eb}
.seg:last-child{border-bottom:none}
.segh{background:#f8fafc;padding:6px 14px;font-size:13px;display:flex;gap:10px;align-items:center}
.segh b{color:#0f172a}
.segspan{color:var(--mut);font-size:12px}
.keybadge{background:var(--cur);color:#92400e;border:1px solid #f5d9a8;border-radius:4px;padding:0 6px;font-size:11px;font-weight:600}
.segbody{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px}
.srow{display:flex;gap:12px;padding:2px 14px;align-items:baseline}
.srow:hover{background:#f1f5f9}
.srow .ln{color:#9ca3af;min-width:34px;text-align:right;user-select:none}
.srow code{white-space:pre;color:inherit}
.srow .nt{color:var(--mut);white-space:pre-wrap;font-size:11.5px;font-family:-apple-system,"PingFang SC",sans-serif}
.srow .nt.showtext{color:#0f766e;font-weight:600}
.srow.tx code{color:var(--tx)} .srow.font code{color:var(--font)}
.srow.text code{color:var(--text)} .srow.draw code{color:var(--draw)}
.srow.img code{color:var(--img)} .srow.img2 code{color:var(--img2)}
.srow.st code{color:var(--st)}
/* 重点卡 */
.keycard{border-left:4px solid var(--acc)}
.keycard em{color:#92400e;font-style:normal;font-weight:600}
/* 分类色块 */
.cat{display:inline-block;border-radius:4px;padding:0 6px;font-size:11.5px;font-weight:600;margin-right:6px}
.c-title{background:#dbeafe;color:#1d4ed8}.c-nar{background:#f3e8ff;color:#7c3aed}
.c-list{background:#dcfce7;color:#15803d}.c-uncat{background:#f3f4f6;color:#6b7280}
.c-footer{background:#ffedd5;color:#c2410c}.c-header{background:#fef9c3;color:#a16207}
table{border-collapse:collapse;width:100%;margin:10px 0;font-size:13.5px}
th,td{border:1px solid #dbe0e6;padding:7px 10px;text-align:left}
th{background:#f1f5f9}
.two{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:800px){.two{grid-template-columns:1fr}}
.note{background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:10px 14px;font-size:13.5px;margin:10px 0}
</style>
</head>
<body>
<header>
<h1>PDF 内容流逐行解剖讲义</h1>
<p>对象：<code style="background:#1e293b;color:#93c5fd">data/generated/sample_mixed_all.pdf</code>
（page 0 · 595×842pt · 本节全部内容来自原文，逐行可复现）</p>
<p>三个库：PyMuPDF（对象树） · Unstructured fast（版面分组） · LlamaParse（云端语义重建）</p>
</header>
<main>

<h2>0. 这张 PDF 的"目录"：一页 = 五个世界</h2>
<div class="card">
<p>398 行的内容流里，元素分布如下（全部为实测）：</p>
<table>
<tr><th>元素</th><th>在 PDF 里的形式</th><th>行号范围</th><th>谁最擅长</th></tr>
<tr><td><b>文字</b>（标题/正文/中文）</td><td>BT/Tm/Tf/TJ 指令组</td><td>1-50</td><td>PyMuPDF（坐标）</td></tr>
<tr><td><b>图片</b></td><td>cm + Do 两行</td><td>52-55</td><td>PyMuPDF（像素）</td></tr>
<tr><td><b>表格</b></td><td>20×(re 矩形 + 文字)</td><td>65-183</td><td>PyMuPDF/LlamaParse</td></tr>
<tr><td><b>列表</b></td><td>就是普通文本行（• 只是个字符）</td><td>L31-L48</td><td>Unstructured（语义）</td></tr>
<tr><td><b>表单</b></td><td>不在内容流：/Annots 里的 Widget</td><td>L185 之后只有标签</td><td>PyMuPDF（唯一）</td></tr>
</table>
</div>

<h2>1. 对象图：六个对象是"文字/图片/控件"的真身</h2>
<div class="card">
<h3>页对象（#1）→ 内容流 + 资源 + 注释</h3>
<pre>&lt;&lt; /Type /Page /MediaBox [0 0 595 842]
   /Contents 12 0 R              ← "程序"（398 行内容流）在对象 12
   /Resources ...                ← 字体、图片 /fzImg0 的真身在这里
   /Annots [...]                 ← 6 个表单控件挂在这里！
   /Parent ... &gt;&gt;</pre>
<h3>图片对象（DCTDecode = 一张 JPEG 包在 PDF 里）</h3>
<pre>__IMGOBJ__</pre>
<h3>本页字体（9 个字体对象，多数字体被"子集化"嵌入）</h3>
<div>__FONTS__</div>
</div>

<h2>2. 内容流逐行解剖（全 398 行）</h2>
<p class="muted">颜色：<b style="color:#1d4ed8">蓝=文本指令</b> ·
<b style="color:#7c3aed">紫=字体</b> · <b style="color:#0f766e">绿=文本内容</b> ·
<b style="color:#b45309">橙=画线/矩形（表格）</b> · <b style="color:#15803d">深绿=图片</b> ·
<b style="color:#64748b">灰=状态</b>。<br>
每段下方有段落标签；绿色小字是程序根据坐标还原出的<b>显示文字</b>（由字体 ToUnicode 解出）。</p>
<div class="stream">__SEGMENTS__</div>

<h2>3. 六个重点：每一种元素如何"存在"、又如何被解析</h2>
__KEYCARDS__

<h2>4. 三个库逐元素实测对比（同一份 PDF）</h2>

<h3>4.1 PyMuPDF —— 忠实还原物理层</h3>
<div class="two">
<div class="card">
<h3>文本块（带坐标）</h3>
<div>__BLOCKS__</div>
<p class="muted">注意：PyMuPDF 用 y 轴<b>向下</b>的坐标，内容流是 y 轴<b>向上</b>（842-y）。</p>
<h3>词级坐标（前 6 个词）</h3>
<div>__WORDS__</div>
</div>
<div class="card">
<h3>图片</h3>
<p>856×489 像素 · 显示位置 <code>(60, 330.6)-(300, 467.7)</code>pt<br>
PyMuPDF 能把它解码回原始像素 PNG。<b>它永远不知道图"画了什么"</b>。</p>
<h3>表格（find_tables 还原行列）</h3>
<div>__TABLE__</div>
<h3>表单控件（读取 Widget 注释）</h3>
<div>__WIDGETS__</div>
<p class="muted">这就是"能填表"的原因：直接改对象 /V 值 + 重生成外观流。</p>
</div>
</div>

<h3>4.2 Unstructured fast —— 版面分组 + 规则分类（36 个元素）</h3>
<div class="card">
<div>__ELS__</div>
<br><p class="muted">✅ 4 个列表项被正确识别为 <span class="cat c-list">ListItem</span>；标题、正文、题注已分类。<br>
⚠️ <b>表格</b>：20 个表格字串成了 20 个独立元素（Product 被猜成 Title，- 被猜成 ListItem）——fast 策略<b>不产出 Table 元素</b>；<br>
⚠️ <b>图片</b>：只字未提（只有题注 Figure 1 成为 Title）；<br>
⚠️ <b>表单</b>：Name:/Email: 被分类成 Title，City: 因页面位置被误判成 Footer。<br>
这就是"语义分组"的边界：它靠<b>规则猜</b>，猜不出的（表格/图片）就只能退化成文本。</p>
</div>

<h3>4.3 LlamaParse —— 云端"读一遍"（需 API Key，此处为预期输出示意）</h3>
<div class="card">
<pre>__LLAMA__</pre>
<p class="muted">↑ 只是示意。真实调用：<code>LlamaParse(api_key=…, result_type="markdown")</code> → <code>get_json_result()</code>。
它把整页<b>渲染成图</b>再交给版面模型 + 大模型：<br>
✅ 标题层级（# 标题）✅ 列表 ✅ <b>表格被重建为 Markdown 表（单元格关系恢复了！）</b> ✅ 图片引用 <code>![Figure 1]</code> ✅ 表单文字也结构化<br>
⚠️ 代价：需要 key/网络/费用；<b>没有坐标、没有控件</b>——它关心"文档在说什么"，不关心"它物理上在哪"。</p>
</div>

<h2>5. 结论：同一个 PDF，三层眼睛</h2>
<div class="card">
<table>
<tr><th>元素</th><th>PDF 物理形态</th><th>PyMuPDF</th><th>Unstructured</th><th>LlamaParse</th></tr>
<tr><td>文字</td><td>Tj/TJ 指令 + 字体</td><td>✅ 原文+坐标+字体</td><td>✅ Title/正文/列表</td><td>✅ 篇章结构</td></tr>
<tr><td>图片</td><td>cm+Do → XObject</td><td>✅ 像素原图+位置</td><td>❌ fast 无感知</td><td>✅ 识别图内容</td></tr>
<tr><td>表格</td><td>矩形+文字的<b>堆叠</b></td><td>✅ 几何法行列</td><td>❌ 退化成文本</td><td>✅ 重建单元格</td></tr>
<tr><td>列表</td><td>普通文本（• 即字符）</td><td>❌ 只是行</td><td>✅ ListItem</td><td>✅ 列表语法</td></tr>
<tr><td>表单</td><td>Annots 的 Widget 对象</td><td>✅ 字段+值+可填写</td><td>❌ 只有标签文字</td><td>❌ 只有语义文字</td></tr>
</table>
<p class="muted">复现：<code>.venv/bin/python scripts/make_sample_pdfs.py</code> →
<code>.venv/bin/python examples/pymupdf/06_mixed_all.py</code> →
<code>.venv/bin/python examples/unstructured/06_mixed_all.py</code> →
<code>export LLAMA_CLOUD_API_KEY=… &amp;&amp; .venv/bin/python examples/llamaparse/06_mixed_all.py</code></p>
</div>

</main>
</body></html>"""

# 填充
html_doc = (html_doc
            .replace("__SEGMENTS__", "\n".join(seg_rows))
            .replace("__KEYCARDS__", "\n".join(
                f'<div class="card keycard"><h3>{esc(t)}</h3>{b}</div>' for t, k, b in key_cards))
            .replace("__BLOCKS__", blocks_html)
            .replace("__WORDS__", words_html)
            .replace("__TABLE__", table_html)
            .replace("__WIDGETS__", widgets_html)
            .replace("__ELS__", els_html)
            .replace("__LLAMA__", esc(llama_example))
            .replace("__IMGOBJ__", esc(img_obj_short))
            .replace("__FONTS__", fonts_html))

OUT_PATH.write_text(html_doc, encoding="utf-8")
print(f"已生成: {OUT_PATH}")
print(f"大小: {OUT_PATH.stat().st_size / 1024:.0f} KB | 内容流 {len(lines)} 行 | "
      f"文本块 {len(blocks)} | 元素 {len(els)}")
doc.close()
