#!/usr/bin/env bash
# ctfsweep 卸载脚本（macOS / Linux）
# 移除 devtools 安装目录（系统级 + 用户级）、用户数据目录与 shell 配置块、旧版软链。
#
# 用法:
#   ./installer/uninstall.sh                    # 用户级一键清理（系统级目录需 sudo 才能删）
#   sudo ./installer/uninstall.sh               # 全部清理（含系统级）
#   sudo /Library/devtools/ctfsweep/uninstall   # 也可用安装目录内的副本
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
try_remove_dir() {
    local d="$1"
    [ -d "$d" ] || return 0
    [ "$(basename "$d")" = "ctfsweep" ] || { echo "跳过（路径不匹配）: $d"; return 0; }
    if rm -rf "$d" 2>/dev/null; then
        echo "已删除: $d"
        removed=1
    else
        echo "无权限删除: ${d}（请用 sudo 重跑本脚本）"
    fi
}
try_remove_dir "$USR_INSTALL"
try_remove_dir "$SYS_INSTALL"

if [ -L "$OLD_LINK" ]; then
    rm -f "$OLD_LINK"
    echo "已删除旧版软链: $OLD_LINK"
    removed=1
fi

strip_block() {
    local f="$1" tmp tmp2
    [ -f "$f" ] || return 0
    grep -q -e "completions/ctfsweep" -e "devtools/ctfsweep/bin" -e "^# ctfsweep$" -e "^alias ctf='ctfsweep'" "$f" 2>/dev/null || return 0
    tmp="$f.ctfsweep.tmp.$$"
    grep -v -e "completions/ctfsweep" -e "devtools/ctfsweep/bin" -e "^# ctfsweep$" -e "^alias ctf='ctfsweep'" "$f" > "$tmp" || true
    tmp2="$tmp.n"
    printf '%s\n' "$(cat "$tmp")" > "$tmp2"      # 规整尾部空行
    cat "$tmp2" > "$f"                            # 原地覆盖，保留原属主/权限
    rm -f "$tmp" "$tmp2"
    echo "已清理 shell 配置: $f"
}
strip_block "$REAL_HOME/.zshrc"
strip_block "$REAL_HOME/.bashrc"

if [ "$removed" = 0 ]; then
    echo "（未发现遗留的安装目录，也可能已清理过）"
fi
echo "卸载完成。"
