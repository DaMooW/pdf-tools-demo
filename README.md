# PDF 解析三件套示例：PyMuPDF · Unstructured · LlamaParse

一个可直接运行的示例仓库：用 **PyMuPDF**、**Unstructured**、**LlamaParse**
三种思路处理同一批 PDF，覆盖 **文字**、**图片**、**表格**、**表单**、
**文字+图片混合**、**文字+图片+表格+表单混合** 六类场景。

一句话选型：

| 工具 | 特长 | 一句话说明 |
|---|---|---|
| **PyMuPDF** | 快、准、本地 | 直接把 PDF 里"已有"的文字、图片、坐标、表格、表单控件取出来，无需网络和模型 |
| **Unstructured** | 结构化 | 把内容整理成 Title / NarrativeText / ListItem / Table 等**带语义的元素** |
| **LlamaParse** | 语义最全 | 云端 LLM 重建文档，直接给你 Markdown / HTML 表格，扫描件也能处理 |

## 快速开始

```bash
# 1. 创建虚拟环境并安装依赖
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt        # Apple Silicon / Linux / Windows
# Intel Mac 请改用: .venv/bin/pip install -r requirements-macos-intel.txt \
#                   -c constraints-macos-intel.txt

# 2. 一键运行全部示例（约 2 分钟；LlamaParse 无 key 会自动跳过）
.venv/bin/python scripts/make_sample_pdfs.py    # 生成 data/generated/ 的两个样例
bash run_all.sh                                  # 或逐个运行 examples/**/*.py
```

运行产物（提取的图片、表格 csv、Markdown 等）统一写到 `outputs/`（已 gitignore）。

### LlamaParse（云端服务，需要 key）

```bash
export LLAMA_CLOUD_API_KEY='<你的key>'           # https://cloud.llamaindex.ai/
python examples/llamaparse/01_text.py            # 缺 key 时打印指引并跳过
# 也可以: python examples/llamaparse/01_text.py --api-key <KEY>
```

> 注：`llama-parse` 包已标记 deprecated（官方建议迁移到 `llama-cloud` 统一 SDK），
> 本仓库为教学用途仍使用其最稳定的 `get_json_result` / `get_images` / `get_tables` 接口，
> 迁移方式见 [llama-cloud-py](https://github.com/run-llama/llama-cloud-py)。

## 六类场景 × 三个工具

| 场景 | PyMuPDF | Unstructured | LlamaParse |
|---|---|---|---|
| ① 文字 | `01_text.py` 文字+块坐标+字体字号 | `01_text.py` Title/NarrativeText/ListItem | `01_text.py` 结构化 Markdown |
| ② 图片 | `02_images.py` 提取内嵌位图+位置 | `02_images.py` 能力探测（hi_res 才出 Image 元素） | `02_images.py` 云端提取图片 |
| ③ 表格 | `03_tables.py` find_tables 行列结构 | `03_tables.py` 能力探测（hi_res 才有 Table 元素） | `03_tables.py` HTML/Markdown 表格 |
| ④ 表单 | `04_forms.py` 读取/填写 AcroForm 控件 | `04_forms.py` 表单文字视图 | `04_forms.py` 表单语义重建 |
| ⑤ 文字+图片 | `05_mixed_text_image.py` | `05_mixed_text_image.py` | `05_mixed_text_image.py` |
| ⑥ 四合一 | `06_mixed_all.py` | `06_mixed_all.py` | `06_mixed_all.py` |

### 测试数据（全部在本仓库 data/ 下）

| 数据 | 来源 | 用途 |
|---|---|---|
| `data/papers/` 4 篇 arXiv 论文 | 本机"论文"目录复制的原 PDF | ①纯文字 ②图片 ③表格 ⑤图文混合 |
| `data/forms/` IRS W-9 / W-4 | 从 irs.gov 下载（真实表单，公有领域） | ④表单 |
| `data/generated/` | `scripts/make_sample_pdfs.py` 生成 | ⑥四合一（+ 全控件类型表单一页） |
| `data/nltk_data/` | NLTK 语料子集 | unstructured 元素化的本地依赖 |

完整出处与版权说明见 [`data/README.md`](data/README.md)。

## 三个工具怎么用（示例摘录）

### PyMuPDF —— 文字 + 坐标（最强）

```python
import pymupdf
doc = pymupdf.open("data/papers/2512.23631_BOAD.pdf")
page = doc[0]
text = page.get_text()                    # 文字
blocks = page.get_text("blocks")          # (x0,y0,x1,y1,text,...) 坐标块
tables = page.find_tables().tables        # 表格 → .extract() 行列
widgets = page.widgets()                  # 表单控件 → w.field_name / w.field_type_string
for xref, *_ in page.get_images(full=True):
    pymupdf.Pixmap(doc, xref).save("img.png")   # 提取内嵌图片
```

运行 `python examples/pymupdf/01_text.py` 可看到：页数/字数统计、带坐标的文本块、
span 级字体字号（如 `NimbusRomNo9L-Regu size=10.1`），并把全文存为 txt。

### Unstructured —— 结构化元素

```python
from unstructured.partition.pdf import partition_pdf
elements = partition_pdf("data/papers/2512.23631_BOAD.pdf", strategy="fast")
for e in elements:
    print(e.category, "|", e.metadata.page_number, "|", e.text[:60])
# Title 159 个 / NarrativeText 281 个 / ListItem 26 个 / Header / Footer
```

**重要边界（实测结论，示例 02/03 有自动探测与说明）**：

- `strategy="fast"`（pdfminer，本地无模型）：输出文本元素，**不产出** Table / Image 元素；
- `strategy="hi_res"`（版面模型，需要 torch + unstructured-inference）：才能给出
  Table 元素（含 `metadata.text_as_html`）和 Image 元素；
- Intel Mac（macOS x86_64）装不了新版 torch/llvmlite（无 wheel），
  本仓库因此内置了一个最小兼容桩 `examples/unstructured/_compat.py`：
  检测到真实包时自动让位，未安装时只保证 fast 策略可用，
  一旦调用被桩住的 hi_res 路径会得到明确报错而非错误结果。

### LlamaParse —— 云端语义重建

```python
from llama_parse import LlamaParse
parser = LlamaParse(api_key="...", result_type="markdown")
r = parser.get_json_result("data/papers/2608.05212_SearchAuditor.pdf")[0]
print(r["markdown"])                        # 标题层级 + 表格 + 图片引用
# JSON 模式 + parser.get_images(result, ...) / get_tables(result, ...) 可下载图片/表格
```

## 目录结构

```
pdf-tools-demo/
├── README.md / AGENTS.md / LICENSE
├── requirements.txt            # 主流平台依赖
├── requirements-macos-intel.txt# Intel Mac 依赖（+ constraints-macos-intel.txt）
├── run_all.sh                  # 一键运行全部示例
├── scripts/
│   ├── make_sample_pdfs.py     # 生成四合一/全控件样例 PDF
│   └── download_forms.sh       # 重新下载 IRS 表单
├── data/                       # 全部测试数据（说明见 data/README.md）
│   ├── papers/ forms/ generated/ nltk_data/
├── examples/
│   ├── common.py               # 数据路径与公共工具
│   ├── pymupdf/  01~06
│   ├── unstructured/ 01~06（+ _compat.py 兼容桩）
│   └── llamaparse/ 01~06（+ _lp.py key 解析）
└── outputs/                    # 运行产物（gitignore）
```

## Intel Mac 说明（macOS x86_64）

2025 年之后大量 Python 科学包只发布 arm64 的 macOS wheel。本仓库在本机
（macOS 14.6 + Intel i7-9750H）实测的可用组合：

- `unstructured` 固定 **0.18.9**：0.19+ 依赖 numba，而 llvmlite/numba 无 macOS x86_64 wheel；
- `pikepdf` 固定 **9.x**：10.x 的 x86_64 wheel 要求 macOS 15；
- `cryptography <43`：42.0.8 最后支持 macOS 14 x86_64；
- `opencv-python==4.13.0.92`、`pi-heif==1.4.0`（导入依赖，固定在最后提供 x86_64 wheel 的版本）。

主流平台直接 `pip install -r requirements.txt`，无需这些固定。

## 常见问题

- **Unstructured 示例为什么没输出 Table/Image 元素？**
  见上文"重要边界"；对应功能的完整示例在 `examples/pymupdf/03_tables.py`、
  `examples/llamaparse/03_tables.py` 与 `examples/pymupdf/02_images.py`。
- **想用 hi_res（torch）怎么做？** 在可安装 torch 的机器上：
  `pip install "unstructured[pdf]" "unstructured-inference"`，示例 02/03 会自动走 hi_res 分支。
- **为什么有合成样例 PDF？** 真实文档很难在同一文件包含全部四种元素，
  详见 `data/README.md`。
- **LlamaParse 提示 deprecated？** 是上游包状态，接口可用；迁移指引见上文链接。

## License

MIT（测试数据版权说明见 `data/README.md`）。
