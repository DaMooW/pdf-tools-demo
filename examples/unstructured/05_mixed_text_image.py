"""Unstructured 示例 05：文字 + 图片混合文档。

fast 策略不产出 Image 元素，但它会把图文混排页面中的"文字"整理成
Title / NarrativeText / ListItem，并保留页码 —— 这正是
"把内容整理成标题、正文、列表等结构化元素"的典型场景；
图片元素请参考示例 02（hi_res）或 PyMuPDF 示例 05。

运行:  python examples/unstructured/05_mixed_text_image.py
输入:  data/papers/2608.05212_SearchAuditor.pdf
"""

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # examples/
import _compat  # noqa: E402
_compat.install()

from common import *  # noqa: E402
from unstructured.partition.pdf import partition_pdf  # noqa: E402

ensure_data()
out_dir = OUTPUT_DIR / "unstructured" / "05_mixed_text_image"

section("Unstructured · 05 图文混合 —— 结构化元素视图")
print(f"PDF: {TEXT_IMAGE_PDF}  ({TEXT_IMAGE_PDF.name})")

elements = partition_pdf(str(TEXT_IMAGE_PDF), strategy="fast")
print(f"共 {len(elements)} 个元素")
print("\n-- 元素类型分布 --")
for cat, n in Counter(e.category for e in elements).most_common():
    print(f"  {cat:<18} {n:4d}")

print("\n-- 结构段示例：标题 / 正文 / 列表项 --")
shown = {"Title": 0, "NarrativeText": 0, "ListItem": 0}
for e in elements:
    if e.category in shown and shown[e.category] < 2:
        print(f"  [{e.category}] 页{e.metadata.page_number} | {e.text[:60]}")
        shown[e.category] += 1
    if all(v >= 2 for v in shown.values()):
        break

# 按页聚合结构化文本（图片在元素流中缺位，但文字结构完整）
page_dump = {}
for e in elements:
    page_dump.setdefault(e.metadata.page_number, []).append(f"{e.category}: {e.text}")
lines = [f"page {p}\n" + "\n".join(block) for p, block in sorted(page_dump.items())]
out_path = out_dir / "structured_pages.txt"
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text("\n\n".join(lines)[:200000], encoding="utf-8")
print(f"\n按页结构化文本已保存: {out_path.relative_to(ROOT)}")
