#!/usr/bin/env bash
# ctfsweep 冒烟（macOS / Linux）：语法门 + 单元冒烟 + 启动器 + 安装/卸载循环 + 引导模式 + 自管理子命令
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

# 7.1 config：显示运行模式与配置信息
HOME="$_stage_home" "$_csw" config > "$_stage_home/.cfg.out" 2>&1 \
    || _fail "config 子命令失败（退出码非 0）"
case "$(cat "$_stage_home/.cfg.out")" in
    *"运行模式: 已安装"*"配置文件:"*) echo "config 子命令 OK" ;;
    *) _fail "config 输出异常：$(cat "$_stage_home/.cfg.out")" ;;
esac

# 7.2 update：与快照一致 → 已是最新
HOME="$_stage_home" CTFSWEEP_MIRROR="file://$_stage" "$_csw" update > "$_stage_home/.u1.out" 2>&1 \
    || _fail "update 失败（退出码非 0）"
case "$(cat "$_stage_home/.u1.out")" in
    *"已是最新"*) echo "update（已是最新）OK" ;;
    *) _fail "update 输出异常：$(cat "$_stage_home/.u1.out")" ;;
esac

# 7.3 update --check：只检查不改动
HOME="$_stage_home" CTFSWEEP_MIRROR="file://$_stage" "$_csw" update --check > "$_stage_home/.u2.out" 2>&1 \
    || _fail "update --check 失败（退出码非 0）"
case "$(cat "$_stage_home/.u2.out")" in
    *"已是最新"*) echo "update --check OK" ;;
    *) _fail "update --check 输出异常：$(cat "$_stage_home/.u2.out")" ;;
esac

# 7.4 篡改已安装文件 → update 应检测差异并修复，随后再跑一次应收敛为「已是最新」
_target="$_stage_home/.devtools/ctfsweep/lib/ctfsweep/core/utils.py"
printf '\n# tampered by smoke\n' >> "$_target"
HOME="$_stage_home" CTFSWEEP_MIRROR="file://$_stage" "$_csw" update > "$_stage_home/.u3.out" 2>&1 \
    || _fail "update（修复）失败（退出码非 0）"
case "$(cat "$_stage_home/.u3.out")" in
    *"更新完成"*) : ;;
    *) _fail "update（修复）输出异常：$(cat "$_stage_home/.u3.out")" ;;
esac
if "$PY" -c "import sys; sys.exit(0 if b'tampered by smoke' not in open(sys.argv[1],'rb').read() else 1)" "$_target"; then
    echo "update（检测差异并修复）OK"
else
    _fail "篡改未被修复"
fi
HOME="$_stage_home" CTFSWEEP_MIRROR="file://$_stage" "$_csw" update > "$_stage_home/.u4.out" 2>&1 \
    || _fail "update（收敛校验）失败（退出码非 0）"
case "$(cat "$_stage_home/.u4.out")" in
    *"已是最新"*) echo "update（修复后收敛）OK" ;;
    *) _fail "update（收敛校验）输出异常：$(cat "$_stage_home/.u4.out")" ;;
esac

# 7.5 uninstall -y：卸载（隔离 HOME）
HOME="$_stage_home" "$_csw" uninstall -y > "$_stage_home/.u5.out" 2>&1 \
    || _fail "uninstall 失败（退出码非 0）"
case "$(cat "$_stage_home/.u5.out")" in
    *"卸载完成"*) : ;;
    *) _fail "uninstall 输出异常：$(cat "$_stage_home/.u5.out")" ;;
esac
if [ ! -d "$_stage_home/.devtools/ctfsweep" ]; then
    echo "uninstall -y OK"
else
    _fail "卸载后安装目录仍存在"
fi

rm -rf "$_stage" "$_stage_home" "$_boot_root"

echo "smoke: 全部通过"
