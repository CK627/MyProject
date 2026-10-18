#!/usr/bin/env bash
# encoding: utf-8
# startupctl 清理脚本（macOS / Linux）
#
# 「uninstall」= 卸载安装副本 + 摘除 shell 接线：
#   · 用户级: 删除 ~/.devtools/startupctl/ 整个目录（含 data/guard.json）
#   · 系统级: 删除 /Library/devtools/startupctl（含 data/guard.json）
#   · 旧版软链 ~/.local/bin/startupctl 一并清理
#   · 摘除 .zshrc/.bashrc 里的 `# >>> startupctl >>>` 块（由 shell-setup.sh remove 负责）
#
# ★ 数据跟着项目走（用户的明确要求）：名单与模式住在**安装根下的 data/**，
#   所以卸载会把它们一起带走——删掉项目就不留无主文件。升级不在此列：
#   update 只替换功能项，data/ 原样保留。
#
# 用法:
#   ./installer/uninstall.sh          # 用户级清理（系统级目录需 sudo 才能删）
#   sudo ./installer/uninstall.sh     # 全部清理（含系统级）
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

case "$(uname -s)" in
    Darwin) SYS_INSTALL="/Library/devtools/startupctl" ;;
    *)      SYS_INSTALL="/usr/local/devtools/startupctl" ;;
esac

REAL_HOME="$HOME"
if [ "$(id -u)" = "0" ] && [ -n "${SUDO_USER:-}" ]; then
    REAL_HOME="$(eval echo "~${SUDO_USER}")"
fi
USR_INSTALL="$REAL_HOME/.devtools/startupctl"
OLD_LINK="$REAL_HOME/.local/bin/startupctl"

removed=0

# —— 先摘 shell 接线：必须赶在删除 shell-setup.sh 之前 ——
# （它也在这份删除清单里，删完再调就找不到脚本了）
if [ -f "$DIR/shell-setup.sh" ]; then
    bash "$DIR/shell-setup.sh" remove "$USR_INSTALL" || true
fi

# —— 用户级：整目录删除 ——
# 只认"看起来确实是本工具的安装根"的目录：有 VERSION 或 lib/startupctl。
# 不按路径无脑 rm -rf —— 那个路径是用户主目录下的固定位置，赌不起。
_rm_install() {
    local d="$1"
    [ -d "$d" ] || return 0
    if [ ! -e "$d/VERSION" ] && [ ! -d "$d/lib/startupctl" ]; then
        echo "跳过 ${d}（不像本工具的安装根：没有 VERSION / lib/startupctl）"
        return 0
    fi
    if rm -rf "$d" 2>/dev/null; then
        echo "已删除: $d"
        removed=1
    else
        echo "无权限删除: ${d}（请用 sudo 重跑本脚本）"
    fi
}

_rm_install "$USR_INSTALL"
_rm_install "$SYS_INSTALL"

# devtools 根（/Library/devtools、/usr/local/devtools）只在**空**时收掉：
# 里面还住着别的工具时 rmdir 失败，正合预期（与 ptool / jtool 同规）。
# ⚠️ 不要改成 rm -rf —— 那是同目录其他工具的安装根。
for _DIRNAME in "$(dirname "$SYS_INSTALL")" "$(dirname "$USR_INSTALL")"; do
    if [ -d "$_DIRNAME" ] && rmdir "$_DIRNAME" 2>/dev/null; then
        echo "（空目录已移除: ${_DIRNAME}）"
    fi
done

if [ -L "$OLD_LINK" ]; then
    rm -f "$OLD_LINK"
    echo "已删除旧版软链: $OLD_LINK"
    removed=1
fi

if [ "$removed" = 0 ]; then
    echo "（未发现遗留的安装残留，可能已清理过）"
fi
echo "清理完成。"
