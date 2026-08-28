"""LlamaParse 示例 03：云端解析 → 表格（Markdown / HTML）。

特点：LlamaParse 用表格结构模型重建单元格关系，
结果可以直接转成 HTML / Markdown 表格，甚至 xlsx。

运行:  python examples/llamaparse/03_tables.py [--api-key <KEY>]
输入:  data/papers/2310.06770_SWE-bench.pdf（表格为主论文）
输出:  outputs/llamaparse/03_tables/（表格文件）
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # examples/
from common import *  # noqa: E402
import _lp  # noqa: E402

ensure_data()
out_dir = OUTPUT_DIR / "llamaparse" / "03_tables"

section("LlamaParse · 03 表格提取 —— 表格为主论文")
print(f"PDF: {TABLE_PDF}  ({TABLE_PDF.name})")

parser = _lp.make_parser(result_type="json")
print("已连接 LlamaParse（云端解析中……）")

json_result = parser.get_json_result(str(TABLE_PDF))
record = json_result[0]

# 统计表格块
n_tables = 0
content = (record.get("json") or {}).get("content", [])
if content:
    n_tables = sum(1 for blk in content if isinstance(blk, dict) and blk.get("type") == "table")
print(f"JSON 内容块中的表格块数量: {n_tables}")

print("\n-- 下载表格（HTML/Markdown 文件）--")
try:
    tables = parser.get_tables(json_result, download_path=str(out_dir))
    print(f"表格数量: {len(tables)}")
    for i, tbl in enumerate(tables[:3], start=1):
        print(f"\n  表格 {i}（前 300 字符）:")
        print(str(tbl)[:300].replace("\n", "\n    "))
except Exception as e:
    print(f"表格下载失败: {type(e).__name__}: {str(e)[:200]}")

# 保存 Markdown 版（如果 record 已带 markdown）
md = record.get("markdown")
if md:
    path = out_dir / "swe_bench.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(md, encoding="utf-8")
    print(f"\nMarkdown 全文已保存: {path.relative_to(ROOT)}")
