#!/usr/bin/env bash
# ctfsweep 冒烟（macOS / Linux）：语法门 + 单元冒烟 + 启动器 + 安装/卸载循环
set -euo pipefail
cd "$(dirname "$0")/.."

PY="${PYTHON:-python3}"

echo "== 1/5 语法门（compileall）=="
"$PY" -m compileall -q ctfsweep tests

echo "== 2/5 python 冒烟 =="
"$PY" tests/test_smoke.py

echo "== 3/5 shell 语法 =="
bash -n bin/ctfsweep
bash -n installer/install.sh
bash -n installer/uninstall.sh
bash -n installer/install-from-source.sh
if command -v zsh >/dev/null 2>&1; then
    zsh -n completions/ctfsweep.zsh
fi

echo "== 4/5 启动器 =="
./bin/ctfsweep --version

echo "== 5/5 安装/卸载循环（隔离 HOME）=="
_tmp_home="$(mktemp -d)"
_log="$_tmp_home/install.log"
if HOME="$_tmp_home" bash installer/install.sh > "$_log" 2>&1 \
   && HOME="$_tmp_home" "$_tmp_home/.devtools/ctfsweep/bin/ctfsweep" --version >/dev/null \
   && HOME="$_tmp_home" bash installer/uninstall.sh > "$_log" 2>&1 \
   && [ ! -d "$_tmp_home/.devtools/ctfsweep" ]; then
    echo "安装/卸载循环 OK"
else
    echo "安装/卸载循环失败，日志："
    cat "$_log" 2>/dev/null || true
    rm -rf "$_tmp_home"
    exit 1
fi
rm -rf "$_tmp_home"

echo "smoke: 全部通过"
