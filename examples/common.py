"""共享工具：仓库内所有数据/输出路径 + 打印辅助。

所有示例脚本都通过本模块定位 PDF，不依赖运行时的当前目录，
因此从仓库根目录或 anywhere 运行都能工作。
"""

from pathlib import Path

# ---- 仓库根目录与数据目录 -------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
PAPERS_DIR = DATA_DIR / "papers"          # 本机"论文"目录复制来的 arXiv 论文
FORMS_DIR = DATA_DIR / "forms"            # 从网络下载的真实 PDF 表单
GENERATED_DIR = DATA_DIR / "generated"    # 由 scripts/make_sample_pdfs.py 生成的样例
OUTPUT_DIR = ROOT / "outputs"             # 运行产物（已 gitignore）

# ---- 六类测试文件的映射 ----------------------------------------------------
# 1. 纯文字（0 图、0 表）
TEXT_PDF = PAPERS_DIR / "2512.23631_BOAD.pdf"
# 2. 图片为主（46 张内嵌图）
IMAGE_PDF = PAPERS_DIR / "2607.26977_TREK.pdf"
# 3. 表格为主（26 张表）
TABLE_PDF = PAPERS_DIR / "2310.06770_SWE-bench.pdf"
# 4. 文字 + 图片混合（33 页、61 张图）
TEXT_IMAGE_PDF = PAPERS_DIR / "2608.05212_SearchAuditor.pdf"
# 5. 真实 PDF 表单（IRS W-9: 23 控件 / W-4: 48 控件）
FORM_PDFS = [FORMS_DIR / "fw9.pdf", FORMS_DIR / "fw4.pdf"]
# 6. 文字 + 图片 + 表格 + 表单四合一（生成样例）
MIXED_ALL_PDF = GENERATED_DIR / "sample_mixed_all.pdf"
# 附：全控件类型的表单（文本框/复选框/下拉框/多选框/日期）
WIDGET_PDF = GENERATED_DIR / "sample_widget_types.pdf"


def section(title: str) -> None:
    """打印醒目的章节标题。"""
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def save_text(path: Path, content: str) -> None:
    """把文本写入 outputs/ 下的文件（目录自动创建）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  已保存: {path.relative_to(ROOT)}")


def ensure_data() -> None:
    """检查测试数据是否齐全，缺失时给出生成/下载提示。"""
    needed = [
        TEXT_PDF, IMAGE_PDF, TABLE_PDF, TEXT_IMAGE_PDF,
        MIXED_ALL_PDF, WIDGET_PDF, *FORM_PDFS,
    ]
    missing = [p for p in needed if not p.exists()]
    if missing:
        print("缺少测试数据：")
        for p in missing:
            print(f"  - {p}")
        print("请先运行:  python scripts/make_sample_pdfs.py")
        print("          bash scripts/download_forms.sh")
        raise SystemExit(1)
