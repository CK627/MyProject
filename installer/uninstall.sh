#!/usr/bin/env bash
# startupctl 清理脚本（macOS / Linux）
#
# 「uninstall」= 卸载安装副本 + 摘除 shell 接线：
#   · 用户级: 只删除 ~/.devtools/startupctl/ 下的功能文件（bin/ lib/ completions/
#     config/ VERSION uninstall deploy.sh shell-setup.sh），**保留数据目录**
#     （whitelist.json 白名单 + backups/ 备份 + scans/ 快照——永不自动删除）。
#     ⚠️ 这里比别处更要紧：backups/ 是用户唯一的后悔药，删了就没法 restore；
#        whitelist.json 是用户逐条确认过的允许清单。两者都只能由用户显式命令清除
#        （whitelist remove / backup prune），卸载绝不代劳。
#   · 系统级: 删除 /Library/devtools/startupctl（纯安装产物，无数据目录）；devtools 根
#     （/Library/devtools、/usr/local/devtools）只在**空**时收掉（同 ptool / jtool）；
#   · 旧版软链 ~/.local/bin/startupctl 一并清理；
#   · 摘除 .zshrc/.bashrc 里的 `# >>> startupctl >>>` 块（由 shell-setup.sh remove 负责）。
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

# —— 用户级: 只删功能残留, 保留数据目录（白名单 / 备份 / 快照） ——
# 白名单与备份**不在**这份清单里，这是刻意的：卸载不该带走用户的允许清单，
# 更不该带走唯一能 restore 的备份。
for item in bin lib completions config VERSION uninstall deploy.sh shell-setup.sh; do
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
    # 空壳（无数据）→ 直接移除；有数据（白名单/备份/快照）→ 保留
    if rmdir "$USR_INSTALL" 2>/dev/null; then
        echo "（空目录已移除: ${USR_INSTALL}）"
    else
        echo "数据目录保留: ${USR_INSTALL}/"
        echo "  内有白名单、备份与快照；卸载不代删（备份是 restore 的唯一来源）"
        echo "  需要清理请显式执行: startupctl backup prune / startupctl whitelist remove"
    fi
fi

# —— 系统级: 安装产物整体删除（无数据目录） ——
if [ -d "$SYS_INSTALL" ]; then
    if rm -rf "$SYS_INSTALL" 2>/dev/null; then
        echo "已删除系统级安装: $SYS_INSTALL"
        removed=1
    else
        echo "无权限删除: ${SYS_INSTALL}（请用 sudo 重跑本脚本）"
    fi
fi
# devtools 根（/Library/devtools、/usr/local/devtools）只在**空**时收掉：
# 里面还住着别的工具时 rmdir 失败，正合预期（与 ptool / jtool 同规）。
# ⚠️ 不要改成 rm -rf —— 那是同目录其他工具的安装根。
_DIRNAME="$(dirname "$SYS_INSTALL")"
if [ -d "$_DIRNAME" ] && rmdir "$_DIRNAME" 2>/dev/null; then
    echo "（空目录已移除: ${_DIRNAME}）"
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
