"""LlamaParse 示例 05：云端解析 → 图文混合文档。

特点：Markdown 输出会保留图片引用位置（![](...) 形式的 image 块），
标题层级、正文、列表都被重建，适合"论文精读/知识库入库"场景。

运行:  python examples/llamaparse/05_mixed_text_image.py [--api-key <KEY>]
输入:  data/papers/2608.05212_SearchAuditor.pdf（图文混排论文）
输出:  outputs/llamaparse/05_mixed_text_image/searchauditor.md
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # examples/
from common import *  # noqa: E402
import _lp  # noqa: E402

ensure_data()
out_dir = OUTPUT_DIR / "llamaparse" / "05_mixed_text_image"

section("LlamaParse · 05 图文混合 —— 语义重建")
print(f"PDF: {TEXT_IMAGE_PDF}  ({TEXT_IMAGE_PDF.name})")

parser = _lp.make_parser(result_type="markdown")
print("已连接 LlamaParse（云端解析中……）")

json_result = parser.get_json_result(str(TEXT_IMAGE_PDF))
markdown = json_result[0].get("markdown", "") or ""
print(f"解析完成：Markdown 共 {len(markdown):,} 字符")

print("\n-- 统计 --")
print(f"  标题行（# 开头）: {sum(1 for l in markdown.splitlines() if l.strip().startswith('#'))}")
print(f"  图片引用（![...]）: {markdown.count('![')}")
print(f"  表格（| 开头行）: {sum(1 for l in markdown.splitlines() if l.strip().startswith('|'))}")

print("\n-- Markdown 结构（前 600 字）--")
print(_lp.head(markdown, 600))

out_path = out_dir / "searchauditor.md"
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(markdown, encoding="utf-8")
print(f"\n已保存: {out_path.relative_to(ROOT)}")
