#!/usr/bin/env bash
# 重新下载真实表单到 data/forms/（美国政府文件，公有领域）
set -e
cd "$(dirname "$0")/.."
mkdir -p data/forms
curl -sL -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36" \
  -o data/forms/fw9.pdf https://www.irs.gov/pub/irs-pdf/fw9.pdf
curl -sL -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36" \
  -o data/forms/fw4.pdf https://www.irs.gov/pub/irs-pdf/fw4.pdf
ls -l data/forms/
