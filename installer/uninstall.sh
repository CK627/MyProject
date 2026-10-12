#!/usr/bin/env bash
# ctfsweep 清理脚本（macOS / Linux）
#
# 源码直跑模式下，「uninstall」= 清理旧版安装残留：
#   · 用户级: 只删除 ~/.devtools/ctfsweep/ 下的功能文件（bin/ lib/ completions/
#     config/ VERSION uninstall），**保留用户数据**（judge/、auto_learn/ 等
#     数据集、模型与缓存——这些是解题标注积累，永不自动删除）；
#   · 系统级: 删除 /Library/devtools/ctfsweep（纯安装产物，无用户数据）；
#   · 旧版软链 ~/.local/bin/ctfsweep 一并清理；
#   · 不再改动 shell 配置文件（.zshrc/.bashrc）——如其中有旧路径引用，请手动检查。
#
# 用法:
#   ./installer/uninstall.sh          # 用户级清理（系统级目录需 sudo 才能删）
#   sudo ./installer/uninstall.sh     # 全部清理（含系统级）
set -euo pipefail

case "$(uname -s)" in
    Darwin) SYS_INSTALL="/Library/devtools/ctfsweep" ;;
    *)      SYS_INSTALL="/usr/local/devtools/ctfsweep" ;;
esac

REAL_HOME="$HOME"
if [ "$(id -u)" = "0" ] && [ -n "${SUDO_USER:-}" ]; then
    REAL_HOME="$(eval echo "~${SUDO_USER}")"
fi
USR_INSTALL="$REAL_HOME/.devtools/ctfsweep"
OLD_LINK="$REAL_HOME/.local/bin/ctfsweep"

removed=0

# —— 用户级: 只删功能残留, 保留数据目录（judge/ auto_learn/ 等） ——
for item in bin lib completions config VERSION uninstall; do
    p="$USR_INSTALL/$item"
    [ -e "$p" ] || continue
    if rm -rf "$p" 2>/dev/null; then
        echo "已删除功能残留: $p"
        removed=1
    else
        echo "无权限删除: ${p}（请检查权限）"
    fi
done
if [ -d "$USR_INSTALL" ]; then
    # 空壳（无用户数据）→ 直接移除；有数据（judge/ auto_learn/ 等）→ 保留
    if rmdir "$USR_INSTALL" 2>/dev/null; then
        echo "（空目录已移除: ${USR_INSTALL}）"
    else
        echo "用户数据保留: ${USR_INSTALL}/（judge/、auto_learn/ 等；如需彻底删除请手动处理）"
    fi
fi

# —— 系统级: 安装产物整体删除（无用户数据） ——
if [ -d "$SYS_INSTALL" ]; then
    if rm -rf "$SYS_INSTALL" 2>/dev/null; then
        echo "已删除系统级安装: $SYS_INSTALL"
        removed=1
    else
        echo "无权限删除: ${SYS_INSTALL}（请用 sudo 重跑本脚本）"
    fi
fi

if [ -L "$OLD_LINK" ]; then
    rm -f "$OLD_LINK"
    echo "已删除旧版软链: $OLD_LINK"
    removed=1
fi

if [ "$removed" = 0 ]; then
    echo "（未发现遗留的安装残留，可能已清理过）"
fi
echo "清理完成。"
