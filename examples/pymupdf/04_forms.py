"""PyMuPDF 示例 04：读取与填充 PDF 表单（AcroForm 控件）。

特点：PyMuPDF 直接读取 PDF 内的表单控件（文本框/复选框/下拉框等），
列出字段名、类型、当前值；还能模仿用户"填写"表单并保存新文件。

运行:  python examples/pymupdf/04_forms.py
输入:  data/forms/fw9.pdf (IRS W-9, 23 个控件) / fw4.pdf (IRS W-4, 48 个控件)
输出:  outputs/pymupdf/04_forms/（表单字段清单 json + 填充后的副本 pdf）
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # examples/
from common import *  # noqa: E402
import pymupdf  # noqa: E402

ensure_data()
out_dir = OUTPUT_DIR / "pymupdf" / "04_forms"

section("PyMuPDF · 04 表单控件读取与填充 —— 真实 PDF 表单")

for form_path in FORM_PDFS:
    print(f"\n{'=' * 70}\n表单: {form_path.name}")
    doc = pymupdf.open(form_path)
    print(f"  是否为表单 PDF: {doc.is_form_pdf}")

    widgets = []
    for page in doc:
        for w in (page.widgets() or []):
            widgets.append({
                "page": page.number + 1,
                "name": w.field_name,
                "type": w.field_type_string,
                "value": getattr(w, "field_value", ""),
                "read_only": bool(getattr(w, "read_only", False)),
            })
    print(f"  控件总数: {len(widgets)}")
    print("  前 8 个字段：")
    for w in widgets[:8]:
        print(f"    第{w['page']}页  {w['name'][:38]:<38} {w['type']:<10} 值='{str(w['value'])[:18]}'")

    # 保存字段清单
    manifest = out_dir / f"fields_{form_path.stem}.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(widgets, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  字段清单已保存: {manifest.relative_to(ROOT)}")

    # ---- 模拟填表：复制一份，填几个字段，保存为新的 PDF ----
    print("\n  -- 模拟填表 --")
    filled = pymupdf.open(form_path)
    written = 0
    for page in filled:
        for w in (page.widgets() or []):
            if w.field_type_string == "Text" and not getattr(w, "read_only", False):
                if written == 0:
                    w.field_value = "DEMO USER"
                elif written == 1:
                    w.field_value = "100-00-0000"
                else:
                    break
                w.update()
                written += 1
            elif w.field_type_string == "CheckBox" and written < 1:
                continue
    filled_path = out_dir / f"filled_{form_path.stem}.pdf"
    filled.save(filled_path)
    filled.close()

    # 验证：填充后的值会出现在页面文本提取里
    check = pymupdf.open(filled_path)
    filled_text = check[0].get_text()
    check.close()
    print(f"  已填充 {written} 个文本字段 -> {filled_path.relative_to(ROOT)}")
    print(f"  验证（提取第 1 页文本含 DEMO USER）: {'DEMO USER' in filled_text}")
    doc.close()

print(f"\n完成。详见 outputs/pymupdf/04_forms/")
