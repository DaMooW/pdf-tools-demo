"""Unstructured 示例 04：表单 —— 把表单 PDF 整理为文本元素。

说明：表单 PDF 里有"控件级别的元数据"（字段名、类型、是否必填等），
unstructured 是内容结构化工具，拿不到控件属性；它会把表单里的
标签文字、说明文字整理成 Title/NarrativeText/ListItem 等文本元素。
控件级的能力请看 PyMuPDF 示例 04（直接读写 AcroForm）与
LlamaParse 示例 04（云端解析表单版面）。

运行:  python examples/unstructured/04_forms.py
输入:  data/forms/fw9.pdf (IRS W-9)
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
form_path = FORM_PDFS[0]  # W-9
out_dir = OUTPUT_DIR / "unstructured" / "04_forms"

section("Unstructured · 04 表单 —— 结构化文本视图")
print(f"PDF: {form_path}  ({form_path.name})")

elements = partition_pdf(str(form_path), strategy="fast")
print(f"共 {len(elements)} 个元素")
print("\n-- 元素类型统计 --")
for cat, n in Counter(e.category for e in elements).most_common():
    print(f"  {cat:<18} {n:4d}")

print("\n-- 表单标题行（Header）示例 --")
shown = 0
for e in elements:
    if e.category == "Header":
        print(f"  {e.text[:70]}")
        shown += 1
        if shown >= 3:
            break

print("\n-- 字段说明文字（NarrativeText / ListItem）示例 --")
shown = 0
for e in elements:
    if e.category in ("NarrativeText", "ListItem"):
        print(f"  [{e.category}] {e.text[:60]}")
        shown += 1
        if shown >= 8:
            break

lines = ["category\tpage\ttext"]
for e in elements:
    lines.append(f"{e.category}\t{e.metadata.page_number}\t{(e.text or '').replace(chr(9), ' ')}")
out_path = out_dir / "fw9_elements.tsv"
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text("\n".join(lines), encoding="utf-8")
print(f"\n全量元素清单已保存: {out_path.relative_to(ROOT)}")

print("""
提示：unstructured 看到的是"表单里的文字"，不是"表单控件"。
字段名/类型/值等控件信息请用 PyMuPDF 示例 04（page.widgets()）读取。
""")
