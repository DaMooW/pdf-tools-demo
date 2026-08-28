# AGENTS.md

给 AI 代理（Copilot、Claude Code、DeepSeek 等）的仓库导航说明。

## 这是什么仓库

PDF 处理三工具（PyMuPDF / Unstructured / LlamaParse）的**可运行示例集**，
覆盖六类场景：文字、图片、表格、表单、图文混合、四合一混合。
仓库以"教学示例"为定位：代码简短、注释中文、输出到 stdout + `outputs/`。

## 常用命令

```bash
bash run_all.sh                  # 运行全部示例（LlamaParse 无 key 自动跳过）
.venv/bin/python examples/pymupdf/01_text.py      # 单个示例
.venv/bin/python scripts/make_sample_pdfs.py      # 重新生成合成样例
# 环境安装（Intel Mac 用 -requirements-macos-intel.txt -c constraints-macos-intel.txt）
```

## 目录约定（改代码前必读）

| 位置 | 约定 |
|---|---|
| `examples/common.py` | 所有数据路径唯一来源（TEXT_PDF / IMAGE_PDF / …），新增数据先改这里 |
| `examples/<tool>/NN_*.py` | 一个场景一个文件，`01`=文字 `02`=图片 `03`=表格 `04`=表单 `05`=图文 `06`=四合一 |
| `examples/unstructured/_compat.py` | Intel Mac 的 torch 兼容桩（fast 策略专用），**不要删除**；在真实包存在时自动让位 |
| `examples/llamaparse/_lp.py` | API key 解析与 parser 创建；缺 key 时示例必须优雅跳过（exit 0） |
| `data/` | 全部测试数据进仓库；数据出处/许可证说明写 `data/README.md` |
| `data/generated/` | 只由 `scripts/make_sample_pdfs.py` 生成，不手改 |
| `scripts/` | 数据生成/下载脚本；提供重新生成入口 |
| `outputs/` | 运行产物，gitignore，不提交 |
| `.venv/` | 本地虚拟环境，gitignore |

## 修改与验证

1. 改完示例后必须实际运行验证：`.venv/bin/python examples/<tool>/NN_*.py`；
   新增场景请保持 01-06 的文件编号语义。
2. 三个工具对同一场景的输出口径保持一致（统计 + 节选 + 保存产物）。
3. 文档同步：功能矩阵写在 README；数据来源写 data/README.md；本文件保持更新。
4. 提交前检查：`git status` 不应包含 `outputs/`、`.venv/` 与任何密钥
   （LlamaParse key 只允许来自环境变量/命令行参数，严禁硬编码）。

## 已知环境事实（不要"顺手修复"成失效行为）

- 本机是 Intel Mac（macOS 14.6），`pymupdf` 用全局 3.14、项目 venv 用 3.12；
- Intel Mac 上 `unstructured` 只能用 fast 策略（0.18.9，见 requirements-macos-intel.txt）；
  装不了 torch → hi_res/表格结构模型不可用，示例 02/03 的"能力探测"输出是设计行为；
- Fast 策略无 Table/Image 元素是 upstream 行为，示例已如实展示并给出替代方案；
- `matplotlib` 首次导入会构建字体缓存（写到 outputs/.mplconfig，正常现象）。

## 给 LlamaParse 示例的注意

- 只能通过 `_lp.resolve_api_key()` 拿 key（env 或 `--api-key`）；
- 无 key 时打印指引并以 `raise SystemExit(0)` 结束，不能报错；
- 不要升级 llama-parse 主版本而不验证 get_json_result/get_images/get_tables 的返回结构。
