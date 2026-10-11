#!/usr/bin/env bash
# ctfsweep 冒烟（macOS / Linux）：语法门 + 单元冒烟 + 启动器 + 安装/卸载循环 + 引导模式
set -euo pipefail
cd "$(dirname "$0")/.."

PY="${PYTHON:-python3}"

echo "== 1/6 语法门（compileall）=="
"$PY" -m compileall -q ctfsweep tests

echo "== 2/6 python 冒烟 =="
"$PY" tests/test_smoke.py

echo "== 3/6 shell 语法 =="
bash -n bin/ctfsweep
bash -n installer/install.sh
bash -n installer/install-from-source.sh
bash -n installer/uninstall.sh
bash -n installer/publish-mirror.sh
if command -v zsh >/dev/null 2>&1; then
    zsh -n completions/ctfsweep.zsh
fi

echo "== 4/6 启动器 =="
./bin/ctfsweep --version

echo "== 5/6 安装/卸载循环（隔离 HOME；仓库内运行为本地源码模式）=="
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

echo "== 6/6 引导模式（离线模拟：file:// 镜像 + 独立脚本副本）=="
# 造一份源码快照当「镜像服务器目录」：用工作区当前文件（含未提交改动），
# 但只放安装所需的内容，顶层目录名与 GitHub archive 一致。
_stage="$(mktemp -d)"
_boot_root="$(mktemp -d)"
_boot="$_boot_root/boot"          # 只放 install.sh 的隔离目录 → 强制触发远程自举路径
_boot_home="$(mktemp -d)"
mkdir -p "$_stage/MyProject-CtfSweep" "$_boot"
cp -R ctfsweep bin config completions installer VERSION "$_stage/MyProject-CtfSweep/"
(cd "$_stage" && tar -czf ctfsweep-src.tar.gz MyProject-CtfSweep)
cp installer/install.sh "$_boot/install.sh"
_boot_log="$_boot_home/boot.log"
if (cd "$_boot" && HOME="$_boot_home" CTFSWEEP_MIRROR="file://$_stage" bash ./install.sh) > "$_boot_log" 2>&1 \
   && HOME="$_boot_home" "$_boot_home/.devtools/ctfsweep/bin/ctfsweep" --version >/dev/null; then
    echo "引导模式 OK"
else
    echo "引导模式失败，日志："
    cat "$_boot_log" 2>/dev/null || true
    rm -rf "$_stage" "$_boot_root" "$_boot_home"
    exit 1
fi
rm -rf "$_stage" "$_boot_root" "$_boot_home"

echo "smoke: 全部通过"
