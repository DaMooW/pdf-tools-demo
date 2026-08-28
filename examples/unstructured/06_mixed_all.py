"""Unstructured 示例 06：文字 + 图片 + 表格 + 表单 四合一文档。

输入: data/generated/sample_mixed_all.pdf（合成样例：一个文件里同时包含四类元素）
演示: unstructured 从这份综合文档里能结构化出什么、不能结构化什么
     （表格/表单控件需要 hi_res 模型，见示例 03/04 的说明）。

运行:  python examples/unstructured/06_mixed_all.py
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
out_dir = OUTPUT_DIR / "unstructured" / "06_mixed_all"

section("Unstructured · 06 四合一综合演示 —— 结构化元素")
print(f"PDF: {MIXED_ALL_PDF}  ({MIXED_ALL_PDF.name})")

elements = partition_pdf(str(MIXED_ALL_PDF), strategy="fast")
print(f"共 {len(elements)} 个元素")

print("\n-- 元素类型分布 --")
for cat, n in Counter(e.category for e in elements).most_common():
    print(f"  {cat:<18} {n:4d}")

print("\n-- 全部元素（fast 视角，含页码与文本）--")
for i, e in enumerate(elements, start=1):
    txt = (e.text or "").replace("\n", " ")[:66]
    print(f"  {i:3d}. 页{e.metadata.page_number} [{e.category:<18}] {txt}")

lines = ["category\tpage\ttext"] + [
    f"{e.category}\t{e.metadata.page_number}\t{(e.text or '').replace(chr(9), ' ')}"
    for e in elements
]
out_path = out_dir / "elements.tsv"
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text("\n".join(lines), encoding="utf-8")
print(f"\n元素清单已保存: {out_path.relative_to(ROOT)}")

print("""
对照（同样是这份 PDF）：
  * 表格单元格 -> PyMuPDF 示例 06（find_tables 得到 5x4 行列）或 LlamaParse 示例 06
  * 表单控件 -> PyMuPDF 示例 06（6 个 widget：姓名/邮箱/日期/复选框/城市下拉框）
  * 图片     -> PyMuPDF 示例 06（提取内嵌位图）或 LlamaParse 示例 06
""")
