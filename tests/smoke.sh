#!/usr/bin/env bash
# ctfsweep 冒烟（macOS / Linux）：语法门 + 单元冒烟 + 启动器检查
set -euo pipefail
cd "$(dirname "$0")/.."

PY="${PYTHON:-python3}"

echo "== 1/4 语法门（compileall）=="
"$PY" -m compileall -q ctfsweep tests

echo "== 2/4 python 冒烟 =="
"$PY" tests/test_smoke.py

echo "== 3/4 shell 语法 =="
bash -n bin/ctfsweep
bash -n installer/install.sh
bash -n installer/install-from-source.sh
if command -v zsh >/dev/null 2>&1; then
    zsh -n completions/ctfsweep.zsh
fi

echo "== 4/4 启动器 =="
./bin/ctfsweep --version

echo "smoke: 全部通过"
