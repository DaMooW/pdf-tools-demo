"""LlamaParse 示例的公共辅助：API Key 解析 + 解析器创建。

LlamaParse 是 LlamaIndex 的云端 PDF 解析服务：
  - 需要 LLAMA_CLOUD_API_KEY（https://cloud.llamaindex.ai/ 注册获取）
  - 内容在云端解析，返回结构化 Markdown/JSON（标题、正文、表格、图片引用）

本仓库的示例在缺失 key 时会打印指引并跳过（不会报错中断）。
"""

import os
import sys
import warnings

# llama-parse 包已整体标注 deprecation（迁移到 llama-cloud 统一 SDK），
# 这里按消息精确过滤，避免示例输出里反复出现警告刷屏；README 有说明。
warnings.filterwarnings("ignore", message=".*llama-parse.*deprecated.*")


def resolve_api_key(argv=None) -> str:
    """按顺序解析 API key：命令行 --api-key <KEY> 或环境变量 LLAMA_CLOUD_API_KEY。"""
    argv = sys.argv[1:] if argv is None else argv
    for i, arg in enumerate(argv):
        if arg == "--api-key" and i + 1 < len(argv):
            return argv[i + 1]
    key = os.environ.get("LLAMA_CLOUD_API_KEY")
    if key:
        return key
    print("=" * 78)
    print("未找到 LlamaParse API Key，跳过本示例。")
    print("获取方式：https://cloud.llamaindex.ai/ 注册后复制 API Key")
    print("使用方法：")
    print("  1. 环境变量:  export LLAMA_CLOUD_API_KEY='<your-key>'")
    print("     再运行:    python examples/llamaparse/01_text.py")
    print("  2. 或命令行:  python examples/llamaparse/01_text.py --api-key <your-key>")
    print("（此跳过不影响 PyMuPDF / Unstructured 示例的运行。）")
    print("=" * 78)
    raise SystemExit(0)


def make_parser(result_type: str = "markdown"):
    """创建 LlamaParse 解析器；result_type: 'markdown' | 'json' | 'text'。"""
    from llama_parse import LlamaParse

    key = resolve_api_key()
    return LlamaParse(api_key=key, result_type=result_type, verbose=False)


def head(text: str, n: int = 700) -> str:
    """文本前 n 字符，用于打印摘要。"""
    return (text or "").strip()[:n]
