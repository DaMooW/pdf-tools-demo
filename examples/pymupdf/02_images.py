"""PyMuPDF 示例 02：提取 PDF 内嵌图片（含坐标、尺寸）。

特点：直接读取 PDF 中的 XObject 图片对象（真实像素位图），
可以按原始分辨率保存为 PNG/JPEG；还能列出图片在哪一页、什么位置。

运行:  python examples/pymupdf/02_images.py
输出:  outputs/pymupdf/02_images/（提取的图片 + 整页渲染图）
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # examples/
from common import *  # noqa: E402
import pymupdf  # noqa: E402

ensure_data()
out_dir = OUTPUT_DIR / "pymupdf" / "02_images"

section("PyMuPDF · 02 图片提取 —— 图片为主的论文")
print(f"PDF: {IMAGE_PDF}  ({IMAGE_PDF.name})")

doc = pymupdf.open(IMAGE_PDF)
print(f"页数: {doc.page_count}")

# ---- 1. 统计每页图片 ------------------------------------------------------
print("\n-- 每页图片数量 --")
total = 0
page_info = []
for page_num, page in enumerate(doc):
    imgs = page.get_images(full=True)
    total += len(imgs)
    page_info.append((page_num, len(imgs)))
    if len(imgs):
        print(f"  第 {page_num + 1:2d} 页: {len(imgs)} 张图")
print(f"共 {total} 张内嵌图片（含跨页重复引用）")

# ---- 2. 提取前 3 张图片 ----
print("\n-- 提取前 3 张图片 --")
pix_count = 0
for page_num, page in enumerate(doc):
    for xref, *_ in page.get_images(full=True):
        pix = pymupdf.Pixmap(doc, xref)
        if pix.n > 4:  # CMYK 等转成 RGB
            pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
        name = f"img_p{page_num + 1:02d}_xref{xref}.png"
        path = out_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        pix.save(path)
        rects = page.get_image_rects(xref)
        rect = rects[0] if rects else None
        print(f"  第 {page_num + 1} 页 xref={xref}  尺寸={pix.width}x{pix.height}  "
              f"显示位置={rect if rect else 'n/a'}")
        print(f"  已保存: {path.relative_to(ROOT)}")
        pix_count += 1
        if pix_count >= 3:
            break
    if pix_count >= 3:
        break

# ---- 3. 整页渲染（页面截图）---------------------------------------------
print("\n-- 整页渲染演示：把第 1 页渲染为 PNG --")
page = doc[0]
pix = page.get_pixmap(dpi=110)
path = out_dir / "render_page1.png"
pix.save(str(path))
print(f"  已保存: {path.relative_to(ROOT)}  尺寸={pix.width}x{pix.height}")

doc.close()
print(f"\n完成。图片与渲染图已保存到 outputs/pymupdf/02_images/")
