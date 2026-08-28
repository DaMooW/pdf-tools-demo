"""PyMuPDF 示例 01：快速提取 PDF 中已有的文字（含坐标）。

特点：PyMuPDF 以"页"和"块/行/词"为单位直接读取 PDF 内部的文字内容，
不需要 OCR、不需要外部分析模型，速度最快；同时返回每个文字块的精确坐标。

运行:  python examples/pymupdf/01_text.py
输出:  outputs/pymupdf/01_text/boad_full_text.txt
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # examples/
from common import *  # noqa: E402
import pymupdf  # noqa: E402

ensure_data()
out_dir = OUTPUT_DIR / "pymupdf" / "01_text"

section("PyMuPDF · 01 文字提取 —— 纯文字论文")
print(f"PDF: {TEXT_PDF}  ({TEXT_PDF.name})")

doc = pymupdf.open(TEXT_PDF)
print(f"页数: {doc.page_count}")

# ---- 1. 按页提取纯文本 ----------------------------------------------------
full_text = []
for page in doc:
    full_text.append(page.get_text())
text = "\n\n".join(full_text)
print(f"总字符数: {len(text):,}  总词数: {len(text.split()):,}")

save_path = out_dir / "boad_full_text.txt"
save_text(save_path, text)

print("\n-- 第 1 页正文前 500 字 --")
print(doc[0].get_text()[:500])

# ---- 2. 文字 + 坐标（PyMuPDF 的强项）--------------------------------------
print("\n-- 第 1 页前 5 个文字块及其坐标 (x0, y0, x1, y1) --")
for block in doc[0].get_text("blocks")[:5]:
    x0, y0, x1, y1, snippet, *_ = block
    snippet = snippet.replace("\n", " ")[:48]
    print(f"  bbox=({x0:6.1f},{y0:6.1f},{x1:6.1f},{y1:6.1f})  {snippet}")

# ---- 3. 更细的粒度：span 级（字体、字号）----------------------------------
print("\n-- 第 2 页 span 级信息（字体/字号/红色高亮等）--")
shown = 0
for block in doc[1].get_text("dict")["blocks"]:
    if block.get("type") != 0:  # 只处理文本块
        continue
    for line in block["lines"]:
        for span in line["spans"]:
            if span["text"].strip():
                print(f"  font={span['font']:<20} size={span['size']:.1f}  {span['text'][:40]}")
                shown += 1
                if shown >= 5:
                    break
        if shown >= 5:
            break
    if shown >= 5:
        break

# ---- 4. 提取公式/引用等也可以按行抽取 ------------------------------------
print("\n-- 第 3 页按行抽取示例 --")
for i, line in enumerate(doc[2].get_text().splitlines()[:8]):
    print(f"  {line.strip()[:60]}")

doc.close()
print(f"\n完成。全文已保存到 {save_path.relative_to(ROOT)}")
