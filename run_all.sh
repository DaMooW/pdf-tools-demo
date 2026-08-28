#!/usr/bin/env bash
# 一键运行仓库内全部示例。
#   - LlamaParse 示例缺少 API Key 时会自动跳过（不影响其他示例）
#   - 任一示例失败不会中断整体流程
set -u
cd "$(dirname "$0")"

if [ -x .venv/bin/python ]; then
  PY=.venv/bin/python
elif command -v python3 >/dev/null; then
  PY=python3
else
  echo "未找到 Python，请先创建虚拟环境（见 README）" >&2
  exit 1
fi

echo "== 1/2 生成样例 PDF（data/generated/）=="
"$PY" scripts/make_sample_pdfs.py || { echo "生成样例失败"; exit 1; }

echo
echo "== 2/2 运行全部示例 =="
for d in pymupdf unstructured llamaparse; do
  for f in examples/$d/0*.py; do
    echo
    echo "########## $f"
    "$PY" "$f" || echo "!! 示例失败（不影响后续）: $f"
  done
done

echo
echo "全部示例运行完毕。产物在 outputs/ 目录。"
