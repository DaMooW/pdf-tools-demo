"""Unstructured 示例 03：表格 —— 能力边界说明 + 可能时的真实提取。

重要结论（实测）：
* fast 策略（pdfminer）把表格当作普通文本流，不产出 Table 元素；
* 表格结构元素（Table + 单元格/HTML 结构）需要 hi_res 策略 +
  table structure 模型（torch），Intel Mac 等平台装不了。

本脚本自动探测：有 torch → 直接提取 Table 元素（含 metadata.text_as_html）；
否则 → 展示表格在 fast 策略下"退化"成什么样子，并指出替代方案。

运行:  python examples/unstructured/03_tables.py
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
out_dir = OUTPUT_DIR / "unstructured" / "03_tables"

section("Unstructured · 03 表格 —— 能力探测与提取")
print(f"PDF: {TABLE_PDF}  ({TABLE_PDF.name})")

try:
    import torch  # noqa: F401
    torch_ok = True
except ImportError:
    torch_ok = False

if torch_ok:
    print("\n-- hi_res + 表格结构模型（本机支持）--")
    elements = partition_pdf(str(TABLE_PDF), strategy="hi_res",
                             infer_table_structure=True)
    cats = Counter(e.category for e in elements)
    print("  元素类型:", dict(cats))
    for e in elements:
        if e.category == "Table":
            html = e.metadata.text_as_html or ""
            print(f"\n  第一张表的 HTML 结构（前 300 字）:\n{html[:300]}")
            break
else:
    print("\n-- fast 策略下的实际情况（本机）--")
    elements = partition_pdf(str(TABLE_PDF), strategy="fast")
    cats = Counter(e.category for e in elements)
    print("  元素类型:", dict(cats))
    print(f"  Table 元素数量: {cats.get('Table', 0)}  "
          "（fast 策略不识别表格，表格内容被当作普通文本流）")
    print("""
  表格内容在 fast 策略中会变成连续文本，例如第 8 页（结果表所在页）的元素流：
""")
    shown = 0
    for e in elements:
        if e.metadata.page_number == 8 and (e.text or "").strip():
            print(f"  [{e.category}] {e.text.strip()[:64]}")
            shown += 1
            if shown >= 6:
                break

    # 保存 fast 视角的表格页文本（第 8 页是 SWE-bench 的结果表）
    page8_text = "\n".join(
        e.text for e in elements if e.metadata.page_number == 8
    )
    path = out_dir / "page8_fast_text.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(page8_text, encoding="utf-8")
    print(f"  第 8 页（含结果表）fast 文本已保存: {path.relative_to(ROOT)}")

print("""
结论与建议:
  • 表格结构化（Table 元素 + 单元格结构）：需要 hi_res / 表格结构模型（torch）。
  • 不依赖模型的替代方案：
      - PyMuPDF find_tables(): 基于网格线直接给出行列（见 examples/pymupdf/03_tables.py）
      - LlamaParse: 云端模型，直接返回 Markdown/HTML 表格（见 examples/llamaparse/03_tables.py）
""")
