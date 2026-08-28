"""LlamaParse 示例 04：云端解析 → 表单文档的语义视图。

说明：LlamaParse 擅长把表单/扫描件重建为结构化 Markdown（识别标题、段落、
选项文字、签名行等版面），表单"控件"（AcroForm 字段）属于 PDF 底层结构，
应由 PyMuPDF 直接读写（见 examples/pymupdf/04_forms.py）。
两者互补：LlamaParse 给出"表单的语义内容"，PyMuPDF 给出"表单的控件字段"。

运行:  python examples/llamaparse/04_forms.py [--api-key <KEY>]
输入:  data/forms/fw9.pdf (IRS W-9)
输出:  outputs/llamaparse/04_forms/fw9.md
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # examples/
from common import *  # noqa: E402
import _lp  # noqa: E402

ensure_data()
form_path = FORM_PDFS[0]
out_dir = OUTPUT_DIR / "llamaparse" / "04_forms"

section("LlamaParse · 04 表单 —— 语义重建视图")
print(f"PDF: {form_path}  ({form_path.name})")

parser = _lp.make_parser(result_type="markdown")
print("已连接 LlamaParse（云端解析中……）")

json_result = parser.get_json_result(str(form_path))
markdown = json_result[0].get("markdown", "") or ""
print(f"解析完成：Markdown 共 {len(markdown):,} 字符")

print("\n-- 表单语义结构（前 700 字）--")
print(_lp.head(markdown, 700))

out_path = out_dir / "fw9.md"
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(markdown, encoding="utf-8")
print(f"\n已保存: {out_path.relative_to(ROOT)}")
print("""
补充：同一份 PDF 的控件级信息（字段名/类型/值）请看 examples/pymupdf/04_forms.py。
""")
