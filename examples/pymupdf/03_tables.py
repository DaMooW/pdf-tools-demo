"""PyMuPDF 示例 03：识别并提取表格（无需三方模型，直接基于网格线/文本）。

特点：page.find_tables() 基于页面上的矢量线条（或文本对齐）识别表格，
返回表格的结构化数据（行 x 列），不依赖网络与机器学习模型。

运行:  python examples/pymupdf/03_tables.py
输出:  outputs/pymupdf/03_tables/（前 5 张表格的 csv + 全部表结构 json）
"""

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # examples/
from common import *  # noqa: E402
import pymupdf  # noqa: E402

ensure_data()
out_dir = OUTPUT_DIR / "pymupdf" / "03_tables"

section("PyMuPDF · 03 表格识别与提取 —— 表格为主的论文")
print(f"PDF: {TABLE_PDF}  ({TABLE_PDF.name})")

doc = pymupdf.open(TABLE_PDF)
print(f"页数: {doc.page_count}")

# ---- 1. 全文档扫描表格 ----------------------------------------------------
all_tables = []
for page_num, page in enumerate(doc):
    try:
        found = page.find_tables().tables
    except Exception:
        continue
    for t in found:
        rows = t.extract()
        all_tables.append({
            "page": page_num + 1,
            "bbox": [round(v, 1) for v in t.bbox],
            "rows": rows,
        })
        if len(all_tables) <= 5:
            print(f"\n-- 第 {page_num + 1} 页发现表格 (左上角 {tuple(round(v) for v in t.bbox[:2])}) --")
            for row in rows[:3]:
                print("   " + " | ".join(str(c or "")[:24] for c in row))
            if len(rows) > 3:
                print(f"   ... 共 {len(rows)} 行")

print(f"\n全文档共识别到 {len(all_tables)} 张表格")

# ---- 2. 保存前 5 张表格为 CSV -------------------------------------------
for i, tbl in enumerate(all_tables[:5], start=1):
    path = out_dir / f"table_{i:02d}_page{tbl['page']}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows([[c or "" for c in row] for row in tbl["rows"]])
    print(f"  已保存: {path.relative_to(ROOT)}")

# ---- 3. 全部表格结构存为 JSON -------------------------------------------
json_path = out_dir / "all_tables.json"
json_path.parent.mkdir(parents=True, exist_ok=True)
json_path.write_text(json.dumps(all_tables, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"  已保存: {json_path.relative_to(ROOT)}")

# ---- 4. 也可以只提取某个页面区域内的表格 ---------------------------------
print("\n-- 附录：也可以按区域提取（第 1 页全页范围示例）--")
page = doc[0]
tables = page.find_tables()  # 支持 clip= 参数限定区域
print(f"  第 1 页发现 {len(tables.tables)} 张表格")

doc.close()
print(f"\n完成。表格已保存到 outputs/pymupdf/03_tables/")
