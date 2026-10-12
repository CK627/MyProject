#!/usr/bin/env bash
# ctfsweep 冒烟（macOS / Linux）：语法门 + 单元冒烟 + 启动器 + 历史安装/清理循环 + 引导模式 + 自管理子命令
# （源码直跑模式下 install/update 已改为指引输出；本节测的是历史安装脚本仍可用 + 清理不伤数据）
set -euo pipefail
cd "$(dirname "$0")/.."

PY="${PYTHON:-python3}"

echo "== 1/7 语法门（compileall）=="
"$PY" -m compileall -q ctfsweep tests

echo "== 2/7 python 冒烟 =="
"$PY" tests/test_smoke.py

echo "== 3/7 shell 语法 =="
bash -n bin/ctfsweep
bash -n installer/install.sh
bash -n installer/install-from-source.sh
bash -n installer/uninstall.sh
bash -n installer/publish-mirror.sh
bash -n completions/ctfsweep.bash
if command -v zsh >/dev/null 2>&1; then
    zsh -n completions/ctfsweep.zsh
fi

echo "== 4/7 启动器 =="
./bin/ctfsweep --version

echo "== 5/7 安装/卸载循环（隔离 HOME；仓库内运行为本地源码模式）=="
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

echo "== 6/7 引导模式（离线模拟：file:// 镜像 + 独立脚本副本）=="
# 造一份源码快照当「镜像服务器目录」：用工作区当前文件（含未提交改动），
# 但只放安装所需的内容，顶层目录名与 GitHub archive 一致。
# 快照在 6/7、7/7 间共用（7/7 的 update 也从它下载）。
_stage="$(mktemp -d)"
_stage_home="$(mktemp -d)"
_boot_root="$(mktemp -d)"
_boot="$_boot_root/boot"          # 只放 install.sh 的隔离目录 → 强制触发远程自举路径
mkdir -p "$_stage/MyProject-CtfSweep" "$_boot"
cp -R ctfsweep bin config completions installer VERSION "$_stage/MyProject-CtfSweep/"
(cd "$_stage" && tar -czf ctfsweep-src.tar.gz MyProject-CtfSweep)
cp installer/install.sh "$_boot/install.sh"

_fail() {
    echo "$1"
    rm -rf "$_stage" "$_stage_home" "$_boot_root"
    exit 1
}

_boot_log="$_stage_home/boot.log"
if (cd "$_boot" && HOME="$_stage_home" CTFSWEEP_MIRROR="file://$_stage" bash ./install.sh) > "$_boot_log" 2>&1 \
   && HOME="$_stage_home" "$_stage_home/.devtools/ctfsweep/bin/ctfsweep" --version >/dev/null; then
    echo "引导模式 OK"
else
    echo "引导模式失败，日志："
    cat "$_boot_log" 2>/dev/null || true
    _fail "（见上方日志）"
fi

echo "== 7/7 自管理子命令（config / update / uninstall，离线）=="
_csw="$_stage_home/.devtools/ctfsweep/bin/ctfsweep"

# 7.1 config：显示运行模式与配置信息（旧版 devtools 安装布局）
HOME="$_stage_home" "$_csw" config > "$_stage_home/.cfg.out" 2>&1 \
    || _fail "config 子命令失败（退出码非 0）"
case "$(cat "$_stage_home/.cfg.out")" in
    *"运行模式: 旧版 devtools 安装"*"配置文件:"*) echo "config 子命令 OK" ;;
    *) _fail "config 输出异常：$(cat "$_stage_home/.cfg.out")" ;;
esac

# 7.2 update：源码直跑模式下输出更新指引（不再下载/修复）
HOME="$_stage_home" CTFSWEEP_MIRROR="file://$_stage" "$_csw" update > "$_stage_home/.u1.out" 2>&1 \
    || _fail "update 失败（退出码非 0）"
case "$(cat "$_stage_home/.u1.out")" in
    *"源码直跑"*) echo "update（指引输出）OK" ;;
    *) _fail "update 输出异常：$(cat "$_stage_home/.u1.out")" ;;
esac

# 7.3 update --check：兼容接受（同样输出指引）
HOME="$_stage_home" CTFSWEEP_MIRROR="file://$_stage" "$_csw" update --check > "$_stage_home/.u2.out" 2>&1 \
    || _fail "update --check 失败（退出码非 0）"
case "$(cat "$_stage_home/.u2.out")" in
    *"源码直跑"*) echo "update --check OK" ;;
    *) _fail "update --check 输出异常：$(cat "$_stage_home/.u2.out")" ;;
esac

# 7.4 uninstall -y：清理旧版安装残留
#（隔离 HOME 无用户数据 → 功能文件移除后空壳一并移除；真实环境有数据则保留数据目录）
HOME="$_stage_home" "$_csw" uninstall -y > "$_stage_home/.u5.out" 2>&1 \
    || _fail "uninstall 失败（退出码非 0）"
case "$(cat "$_stage_home/.u5.out")" in
    *"清理完成"*) : ;;
    *) _fail "uninstall 输出异常：$(cat "$_stage_home/.u5.out")" ;;
esac
if [ ! -d "$_stage_home/.devtools/ctfsweep" ]; then
    echo "uninstall -y OK（功能残留清理、空壳移除）"
else
    _fail "清理后安装目录仍存在"
fi

rm -rf "$_stage" "$_stage_home" "$_boot_root"

echo "smoke: 全部通过"
