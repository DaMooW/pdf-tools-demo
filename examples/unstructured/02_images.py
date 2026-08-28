"""Unstructured 示例 02：图片 —— 能力边界说明 + 可能时的真实提取。

重要结论（实测）：
* strategy="fast" （纯 pdfminer）不产出 Image 元素，也不提取图片文件；
* 提取 PDF 内嵌图片元素需要 strategy="hi_res"（需要 torch + unstructured-inference
  版面模型，Intel Mac 等平台装不了）；
* 对"图片文件本身"（PNG/JPG），unstructured 可配合 Tesseract OCR 识别其中文字。

本脚本自动探测本机能力：
  1) 若能安装 hi_res（有 torch）→ 直接按 extract_image_block_types 提取；
  2) 否则 → 输出明确的能力报告与替代方案（本仓库用 PyMuPDF 示例 02 提取图片）。

运行:  python examples/unstructured/02_images.py
"""

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # examples/
import _compat  # noqa: E402
_compat.install()

from common import *  # noqa: E402
from unstructured.partition.pdf import partition_pdf  # noqa: E402

ensure_data()
out_dir = OUTPUT_DIR / "unstructured" / "02_images"

section("Unstructured · 02 图片 —— 能力探测与提取")
print(f"PDF: {IMAGE_PDF}  ({IMAGE_PDF.name})")

has_torch = shutil.which("poppler") is not None or True  # poppler 只是 hi_res 渲染前置
# 探测 torch：能 import 说明该机器具备 hi_res 条件
try:
    import torch  # noqa: F401
    torch_ok = True
except ImportError:
    torch_ok = False

print("\n-- 本机能力检测 --")
print(f"  torch (hi_res 版面模型依赖):  {'✅ 可用' if torch_ok else '❌ 不可用（Intel Mac 无 wheel）'}")
print(f"  poppler (页面渲染):            {'✅ ' + shutil.which('poppler') if shutil.which('pdftoppm') else '❌ 未安装'}")
print(f"  tesseract (OCR):               {'✅ 已安装' if shutil.which('tesseract') else '❌ 未安装'}")

if torch_ok:
    print("\n-- hi_res 策略提取图片（本机支持）--")
    elements = partition_pdf(
        str(IMAGE_PDF),
        strategy="hi_res",
        extract_image_block_types=["Image"],
        extract_image_block_output_dir=str(out_dir),
    )
    from collections import Counter
    print(dict(Counter(e.category for e in elements)))
else:
    print("\n-- fast 策略下的实际情况 --")
    elements = partition_pdf(str(IMAGE_PDF), strategy="fast",
                             extract_image_block_types=["Image"],
                             extract_image_block_output_dir=str(out_dir))
    from collections import Counter
    cats = Counter(e.category for e in elements)
    print("  元素类型:", dict(cats))
    print(f"  Image 元素数量: {cats.get('Image', 0)}  "
          f"（fast 策略确实不产出 Image 元素，需要 hi_res 或 OCR 模型）")
    saved = [p for p in out_dir.rglob("*") if p.is_file()] if out_dir.is_dir() else []
    print(f"  图片文件: {len(saved)} 个")

print("""
结论与建议:
  • 图片"元素化"（Image 元素 + 保存图片文件）：需要 hi_res 策略（torch）。
  • 在不能装 torch 的环境：用 PyMuPDF 直接取出内嵌图片（见 examples/pymupdf/02_images.py），
    或用 LlamaParse 云端解析（见 examples/llamaparse/02_images.py，云端模型自动提取图片）。
""")

report = out_dir / "capability_report.txt"
report.parent.mkdir(parents=True, exist_ok=True)
report.write_text(
    f"unstructured image capability report\n"
    f"  torch_ok={torch_ok}\n  poppler={'yes' if shutil.which('pdftoppm') else 'no'}\n"
    f"  tesseract={'yes' if shutil.which('tesseract') else 'no'}\n", encoding="utf-8")
print(f"能力报告已保存: {report.relative_to(ROOT)}")
