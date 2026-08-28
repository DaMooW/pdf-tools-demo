"""LlamaParse 示例 02：云端解析 → 图片与图像块。

特点：LlamaParse 的 JSON 模式会为文档中的图片生成 image 块，
get_images() 可以直接把图片下载到本地。

运行:  python examples/llamaparse/02_images.py [--api-key <KEY>]
输入:  data/papers/2607.26977_TREK.pdf（图片为主论文）
输出:  outputs/llamaparse/02_images/（下载的图片）
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # examples/
from common import *  # noqa: E402
import _lp  # noqa: E402

ensure_data()
out_dir = OUTPUT_DIR / "llamaparse" / "02_images"

section("LlamaParse · 02 图片提取 —— 图片为主论文")
print(f"PDF: {IMAGE_PDF}  ({IMAGE_PDF.name})")

parser = _lp.make_parser(result_type="json")
print("已连接 LlamaParse（云端解析中……）")

json_result = parser.get_json_result(str(IMAGE_PDF))
record = json_result[0]

# JSON 内容里统计图片块数量（结构因 result_type 而异，保守取交集）
image_blocks = 0
content = (record.get("json") or {}).get("content", [])
if content:
    image_blocks = sum(1 for blk in content if isinstance(blk, dict) and blk.get("type") == "image")
print(f"JSON 内容块中的图片块数量: {image_blocks}")

print("\n-- 下载图片 --")
try:
    images = parser.get_images(json_result, download_path=str(out_dir))
    print(f"已下载/返回图片条目: {len(images)}")
    for meta in images[:5]:
        print(f"   {str(meta)[:110]}")
except Exception as e:
    print(f"图片下载失败: {type(e).__name__}: {str(e)[:200]}")
    print("（部分设置下需 premium_mode=True 才会提取图片；也可参考 PyMuPDF 示例 02 本地提取）")
