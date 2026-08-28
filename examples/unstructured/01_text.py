"""Unstructured 示例 01：将 PDF 内容整理为结构化元素（标题/正文/列表）。

特点：unstructured 把 PDF 里的文本"分块"成带类型的元素：
Title / NarrativeText / ListItem / Header / Footer / Table ...
这正是"把内容整理成标题、正文、列表等结构化元素"的典型用法。

运行:  python examples/unstructured/01_text.py
输出:  outputs/unstructured/01_text/elements.tsv
"""

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # examples/
import _compat  # noqa: E402  (本机 Intel Mac 无法安装 torch，此为 fast 策略兼容桩)
_compat.install()

from common import *  # noqa: E402
from unstructured.partition.pdf import partition_pdf  # noqa: E402

ensure_data()
out_dir = OUTPUT_DIR / "unstructured" / "01_text"

section("Unstructured · 01 结构化元素提取 —— 纯文字论文")
print(f"PDF: {TEXT_PDF}  ({TEXT_PDF.name})")

# fast 策略：基于 pdfminer 的文本与版面分组，速度最快、无需模型
elements = partition_pdf(str(TEXT_PDF), strategy="fast")
print(f"共得到 {len(elements)} 个元素")

print("\n-- 元素类型统计 --")
for cat, n in Counter(e.category for e in elements).most_common():
    print(f"  {cat:<20} {n:4d}")

print("\n-- 标题 (Title) 示例 --")
shown = 0
for e in elements:
    if e.category == "Title" and len((e.text or "")) >= 20:
        print(f"  页{e.metadata.page_number}: {e.text[:70]}")
        shown += 1
        if shown >= 2:
            break

print("\n-- 正文 (NarrativeText) 示例 --")
shown = 0
for e in elements:
    if e.category == "NarrativeText":
        print(f"  页{e.metadata.page_number}: {e.text[:70]}")
        shown += 1
        if shown >= 3:
            break

print("\n-- 列表项 (ListItem) 示例 --")
shown = 0
for e in elements:
    if e.category == "ListItem":
        print(f"  页{e.metadata.page_number}: {e.text[:70]}")
        shown += 1
        if shown >= 3:
            break

# 保存全量元素清单（tab 分隔：类型 | 页 | 坐标 | 文本）
lines = ["category\tpage\ttext"]
for e in elements:
    txt = (e.text or "").replace("\t", " ").replace("\n", " ")
    lines.append(f"{e.category}\t{e.metadata.page_number}\t{txt}")
out_path = out_dir / "elements.tsv"
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text("\n".join(lines), encoding="utf-8")
print(f"\n全量元素清单已保存: {out_path.relative_to(ROOT)}")
