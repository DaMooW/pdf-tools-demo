"""兼容桩（shim）：让 unstructured 的 fast 策略可以在没有 torch 的机器上使用。

背景
----
unstructured >= 0.16 的 `unstructured.partition.pdf` 会在**模块顶层**执行::

    from unstructured_inference.inference.layout import DocumentLayout

而 `unstructured-inference`（版面模型）依赖 torch / torchvision / detectron2，
在 Intel Mac（macOS x86_64）等平台上没有可用 wheel，无法安装。

其实 `strategy="fast"` 只使用 pdfminer 的文本与版面分组，**并不会调用**任何模型；
只有 `strategy="hi_res"` / `strategy="ocr_only"` 才会真正用到 unstructured-inference。

因此这里提供一个最小桩：预先往 ``sys.modules`` 里注册同名包与子模块，
属性访问一律返回一个惰性占位对象（``unittest.mock.MagicMock``），
让 import 语句通过；若未来真正调用了被桩住的类/函数（hi_res 路径），
会得到明确的报错而非静默错误结果。

在能安装 torch 的机器上，本桩不会被激活（检测到真实包时直接让位）。
"""

import importlib
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

# 需要被桩住的子模块；属性访问全部惰性返回占位对象
_STUB_MODULE_NAMES = [
    "unstructured_inference",
    "unstructured_inference.config",
    "unstructured_inference.constants",
    "unstructured_inference.logger",
    "unstructured_inference.inference",
    "unstructured_inference.inference.elements",
    "unstructured_inference.inference.layout",
    "unstructured_inference.inference.layoutmodel",
    "unstructured_inference.inference.layoutelement",
    "unstructured_inference.inference.ocr",
    "unstructured_inference.models",
    "unstructured_inference.models.base",
    "unstructured_inference.models.detectron2onnx",
    "unstructured_inference.models.yolox",
    "unstructured_inference.models.eval",
    "unstructured_inference.models.tables",
    "unstructured_inference.models.tables.table_structure",
]


def install() -> None:
    """环境准备：设置 NLTK 数据目录 + 注册桩包。"""
    _setup_nltk()
    for name in _STUB_MODULE_NAMES:
        if name in sys.modules:
            continue  # 已有真实模块（或更具体的桩），不覆盖
        try:
            importlib.import_module(name)
            continue  # 真实存在，无需桩
        except ImportError:
            pass

        module = types.ModuleType(name)
        # PEP 562：模块级 __getattr__，任何缺失属性都返回占位对象
        module.__getattr__ = lambda attr, _m=name: MagicMock(name=f"shim:{_m}.{attr}")
        sys.modules[name] = module


def _setup_nltk() -> None:
    """把仓库自带的 nltk 数据目录放进搜索路径，避免首次运行联网下载。"""
    repo_root = Path(__file__).resolve().parent.parent.parent
    nltk_dir = repo_root / "data" / "nltk_data"
    if nltk_dir.is_dir():
        import os
        os.environ.setdefault("NLTK_DATA", str(nltk_dir))
    # matplotlib 的字体缓存写入 outputs 目录（~/.matplotlib 可能不可写）
    os.environ.setdefault("MPLCONFIGDIR", str(repo_root / "outputs" / ".mplconfig"))


if __name__ == "__main__":
    install()
    print("shim installed for:", [n for n in _STUB_MODULE_NAMES if n in sys.modules])
