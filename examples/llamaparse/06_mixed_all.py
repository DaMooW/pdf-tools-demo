"""LlamaParse 示例 06：云端解析 → 文字 + 图片 + 表格 + 表单四合一。

输入: data/generated/sample_mixed_all.pdf（生成样例，一页含四类元素）
演示: LlamaParse 如何把一份"混排 + 表格 + 表单"文档重建为
      Markdown（标题/正文/图片引用/表格），表单控件字段则由
      PyMuPDF 直接读取（见 examples/pymupdf/06_mixed_all.py）。

运行:  python examples/llamaparse/06_mixed_all.py [--api-key <KEY>]
输出:  outputs/llamaparse/06_mixed_all/mixed_all.md
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # examples/
from common import *  # noqa: E402
import _lp  # noqa: E402

ensure_data()
out_dir = OUTPUT_DIR / "llamaparse" / "06_mixed_all"

section("LlamaParse · 06 四合一综合演示 —— 语义重建")
print(f"PDF: {MIXED_ALL_PDF}  ({MIXED_ALL_PDF.name})")

parser = _lp.make_parser(result_type="markdown")
print("已连接 LlamaParse（云端解析中……）")

json_result = parser.get_json_result(str(MIXED_ALL_PDF))
markdown = json_result[0].get("markdown", "") or ""
print(f"解析完成：Markdown 共 {len(markdown):,} 字符")

print("\n-- 重建结果统计 --")
print(f"  标题: {sum(1 for l in markdown.splitlines() if l.strip().startswith('#'))}")
print(f"  图片引用: {markdown.count('![')}")
print(f"  表格行（| 开头）: {sum(1 for l in markdown.splitlines() if l.strip().startswith('|'))}")

print("\n-- Markdown 全文 --")
print(markdown)

out_path = out_dir / "mixed_all.md"
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(markdown, encoding="utf-8")
print(f"\n已保存: {out_path.relative_to(ROOT)}")
print("""
对照：同一份 PDF 的控件级信息由 PyMuPDF 直接读取（6 个 widget），
表格单元格由 PyMuPDF find_tables 得到 5x4 行列结构。
""")
