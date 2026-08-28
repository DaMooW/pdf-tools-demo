"""LlamaParse 示例 01：云端解析 → 结构化 Markdown。

特点：LlamaParse 用云端大模型重建文档语义，输出带标题层级、表格、
列表的 Markdown；对扫描件/复杂排版比本地工具更鲁棒（云端 OCR + 版面模型）。

运行:  python examples/llamaparse/01_text.py [--api-key <KEY>]
输入:  data/papers/2512.23631_BOAD.pdf（纯文字论文）
输出:  outputs/llamaparse/01_text/boad.md
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # examples/
from common import *  # noqa: E402
import _lp  # noqa: E402

ensure_data()
out_dir = OUTPUT_DIR / "llamaparse" / "01_text"

section("LlamaParse · 01 结构化 Markdown —— 纯文字论文")
print(f"PDF: {TEXT_PDF}  ({TEXT_PDF.name})")

parser = _lp.make_parser(result_type="markdown")
print("已连接 LlamaParse（云端解析中，可能需要几十秒……）")

json_result = parser.get_json_result(str(TEXT_PDF))
record = json_result[0]
markdown = record.get("markdown", "") or ""
print(f"解析完成：Markdown 共 {len(markdown):,} 字符")

print("\n-- Markdown 结构（前 600 字）--")
print(_lp.head(markdown, 600))

out_path = out_dir / "boad.md"
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(markdown, encoding="utf-8")
print(f"\nMarkdown 已保存: {out_path.relative_to(ROOT)}")
