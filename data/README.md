# 测试数据来源与说明

本目录只存放示例"用到"的测试数据，全部可离线使用（LlamaParse 除外，它需要联网）。

```
data/
├── papers/      # 从本机"论文"目录复制的 arXiv 论文（用户个人学习用）
├── forms/       # 从互联网下载的真实 PDF 表单（美国政府公开文件）
├── generated/   # 由 scripts/make_sample_pdfs.py 生成的样例（一页含四类元素）
└── nltk_data/   # NLTK 语料资源（punkt_tab / averaged_perceptron_tagger_eng）
```

## data/papers/ —— 纯论文（来自本机 ~/Desktop/面试准备与论文相关/论文/）

| 文件 | 用途 | arXiv 页面 |
|---|---|---|
| 2512.23631_BOAD.pdf | 纯文字（0 图 0 表） | https://arxiv.org/abs/2512.23631 |
| 2607.26977_TREK.pdf | 图片为主（46 张内嵌图） | https://arxiv.org/abs/2607.26977 |
| 2310.06770_SWE-bench.pdf | 表格为主（26 张表） | https://arxiv.org/abs/2310.06770 |
| 2608.05212_SearchAuditor.pdf | 文字+图片混排（33 页 61 图） | https://arxiv.org/abs/2608.05212 |

版权说明：论文著作权归原作者，PDF 为本地学习用途的副本（原文件在论文目录中，
原始来源为 arXiv）。如需公开传播请以 arXiv 页面链接代替。

## data/forms/ —— 真实 PDF 表单（美国政府文件，公有领域）

| 文件 | 说明 | 来源 |
|---|---|---|
| fw9.pdf | IRS Form W-9（2024-03 版），6 页 23 个 AcroForm 控件 | https://www.irs.gov/pub/irs-pdf/fw9.pdf |
| fw4.pdf | IRS Form W-4（2025 版），5 页 48 个 AcroForm 控件 | https://www.irs.gov/pub/irs-pdf/fw4.pdf |

重新下载：`bash scripts/download_forms.sh`

## data/generated/ —— 合成样例（本仓库内生成，可复现）

| 文件 | 说明 |
|---|---|
| sample_mixed_all.pdf | 一页同时含：文字（含中文）、合成位图、5x4 网格表、6 个表单控件 |
| sample_widget_types.pdf | 全控件类型展示：文本/多行文本/复选框/下拉框/多选框/日期 |

重新生成：`python scripts/make_sample_pdfs.py`

为什么需要合成样例：真实文档极少在同一文件里同时包含"正文文字 + 内嵌图 +
结构化表格 + 可填写表单控件"四类元素（论文没有表单，表单没有大图表格），
因此用 PyMuPDF 合成一份确定性的综合样例，保证"四合一混合"示例稳定可运行。

## data/nltk_data/ —— NLTK 语料（由 nltk_data 包提供）

unstructured 的文本元素化使用 NLTK（分句/词性标注）。仓库内置了两份小资源
（punkt_tab 的 english 子集 + averaged_perceptron_tagger_eng），
避免首次运行联网下载；NLTK 数据随 nltk_data 发行版分发。
