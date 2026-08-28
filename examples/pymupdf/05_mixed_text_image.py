"""PyMuPDF 示例 05：文字 + 图片混合文档。

场景：一篇典型的论文页面 —— 正文文字与配图混排。
演示：逐页统计文字/图片，找出"图文同页"的页面，
再把该页的文字、图片、坐标一起导出。

运行:  python examples/pymupdf/05_mixed_text_image.py
输入:  data/papers/2608.05212_SearchAuditor.pdf
输出:  outputs/pymupdf/05_mixed_text_image/
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # examples/
from common import *  # noqa: E402
import pymupdf  # noqa: E402

ensure_data()
out_dir = OUTPUT_DIR / "pymupdf" / "05_mixed_text_image"

section("PyMuPDF · 05 文字 + 图片混合 —— 图文混排论文")
print(f"PDF: {TEXT_IMAGE_PDF}  ({TEXT_IMAGE_PDF.name})")

doc = pymupdf.open(TEXT_IMAGE_PDF)
print(f"页数: {doc.page_count}")

# ---- 1. 逐页统计：文字量 + 图片数 ----------------------------------------
print("\n-- 逐页文字量/图片数 --")
pages = []
for page_num, page in enumerate(doc):
    text_chars = len(page.get_text().strip())
    n_imgs = len(page.get_images(full=True))
    pages.append((page_num, text_chars, n_imgs))
    if page_num < 6 or n_imgs > 0:
        print(f"  第 {page_num + 1:2d} 页: 文字 {text_chars:5d} 字符, 图片 {n_imgs} 张")

# ---- 2. 找出"文字最密 + 图片最多"的页面 ----------------------------------
best = max(pages, key=lambda t: (t[2], t[1]))
print(f"\n图文最丰富的页面: 第 {best[0] + 1} 页（{best[1]} 字符, {best[2]} 张图）")

# ---- 3. 混合抽取：该页全部文字（带坐标）+ 全部图片 ------------------------
print("\n-- 该页文字块与坐标（节选）--")
page = doc[best[0]]
for block in page.get_text("blocks")[:4]:
    x0, y0, x1, y1, snippet, *_ = block
    print(f"  bbox=({x0:6.1f},{y0:6.1f},{x1:6.1f},{y1:6.1f})  {snippet.replace(chr(10), ' ')[:45]}")

print("-- 该页图片信息与提取 --")
os_pics = []
for xref, *_ in page.get_images(full=True):
    pix = pymupdf.Pixmap(doc, xref)
    if pix.n > 4:
        pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
    rects = page.get_image_rects(xref)
    rect = rects[0] if rects else None
    name = f"mixed_p{best[0] + 1}_xref{xref}.png"
    path = out_dir / name
    path.parent.mkdir(parents=True, exist_ok=True)
    pix.save(path)
    print(f"  xref={xref}  {pix.width}x{pix.height}px  显示位置={rect}")
    print(f"  已保存: {path.relative_to(ROOT)}")

# ---- 4. 保存该页文字 + 图文对照 json -------------------------------------
json_payload = {
    "page": best[0] + 1,
    "text_blocks": [{"bbox": b[:4], "text": b[4]} for b in page.get_text("blocks")],
}
import json  # noqa: E402
meta_path = out_dir / "page_blocks.json"
meta_path.write_text(json.dumps(json_payload, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"  对照数据已保存: {meta_path.relative_to(ROOT)}")

doc.close()
print(f"\n完成。图文信息已保存到 outputs/pymupdf/05_mixed_text_image/")
