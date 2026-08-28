"""PyMuPDF 示例 06：文字 + 图片 + 表格 + 表单 四合一文档。

输入: data/generated/sample_mixed_all.pdf（scripts/make_sample_pdfs.py 生成，
      一个文件里同时包含四类元素 —— 真实世界很少见，故用合成样例保证示例确定性）
演示: 一份综合报告 —— 用 PyMuPDF 在一个文档里依次取出全部四类元素。

运行:  python examples/pymupdf/06_mixed_all.py
输出:  outputs/pymupdf/06_mixed_all/（提取的图片 + 表格 csv + 字段清单 json）
"""

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # examples/
from common import *  # noqa: E402
import pymupdf  # noqa: E402

ensure_data()
out_dir = OUTPUT_DIR / "pymupdf" / "06_mixed_all"

section("PyMuPDF · 06 四合一综合演示 —— 文字+图片+表格+表单")
print(f"PDF: {MIXED_ALL_PDF}  ({MIXED_ALL_PDF.name})")

doc = pymupdf.open(MIXED_ALL_PDF)
print(f"页数: {doc.page_count}")

for page_num, page in enumerate(doc):
    print(f"\n{'─' * 70}\n第 {page_num + 1} 页")
    text = page.get_text()
    imgs = page.get_images(full=True)
    tables = page.find_tables().tables
    widgets = list(page.widgets() or [])

    print(f"  [文字] {len(text.strip())} 字符")

    if imgs:
        print(f"  [图片] {len(imgs)} 张")
        for xref, *_ in imgs[:2]:
            pix = pymupdf.Pixmap(doc, xref)
            if pix.n > 4:
                pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
            path = out_dir / f"page{page_num + 1}_img{xref}.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            pix.save(path)
            print(f"     xref={xref}  {pix.width}x{pix.height}px -> {path.relative_to(ROOT)}")

    if tables:
        print(f"  [表格] {len(tables)} 张")
        for i, t in enumerate(tables[:2], start=1):
            rows = t.extract()
            print(f"    第 {i} 张表（{len(rows)} 行 x {len(rows[0])} 列）: {rows[0]}")
            if i == 1:
                csv_path = out_dir / f"page{page_num + 1}_table.csv"
                with csv_path.open("w", newline="", encoding="utf-8") as f:
                    csv.writer(f).writerows([[c or "" for c in r] for r in rows])
                print(f"     已保存: {csv_path.relative_to(ROOT)}")

    if widgets:
        print(f"  [表单] {len(widgets)} 个控件")
        for w in widgets[:8]:
            print(f"     {w.field_name:<18} {w.field_type_string:<10} 值='{getattr(w, 'field_value', '')}'")
        manifest = out_dir / f"page{page_num + 1}_widgets.json"
        manifest.write_text(json.dumps(
            [{"name": w.field_name, "type": w.field_type_string,
              "value": getattr(w, "field_value", "")} for w in widgets],
            ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"     清单已保存: {manifest.relative_to(ROOT)}")

print("\n-- 正文文字节选 --")
print(doc[0].get_text()[:400])

doc.close()
print(f"\n完成。四类元素全部提取，产物在 outputs/pymupdf/06_mixed_all/")
