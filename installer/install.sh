#!/usr/bin/env bash
# ctfsweep 安装脚本（macOS / Linux）—— devtools 布局（与 jtool / ptool 同规）
#
# 目录:
#   系统级（以 sudo / root 运行）: /Library/devtools/ctfsweep     (macOS)
#                                  /usr/local/devtools/ctfsweep  (Linux)
#   用户级（默认，无需 sudo）:      ~/.devtools/ctfsweep
#   用户数据目录（始终创建）:        ~/.devtools/ctfsweep/completions/（供 shell 配置 source）
#
# 用法:
#   ./installer/install.sh          # 用户级安装
#   sudo ./installer/install.sh     # 系统级安装（多用户共享）
#   （环境变量 CTFSWEEP_DEVROOT 可覆盖安装根目录，主要供测试）
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

case "${1:-}" in
    -h|--help)
        sed -n '2,12p' "$0"
        exit 0
        ;;
    "") ;;
    *)
        echo "未知参数: $1（可用 --help）" >&2
        exit 2
        ;;
esac

# ---- 真实用户目录（sudo 场景下用登录用户，而非 root）----
REAL_HOME="$HOME"
if [ "$(id -u)" = "0" ] && [ -n "${SUDO_USER:-}" ]; then
    REAL_HOME="$(eval echo "~${SUDO_USER}")"
fi

# ---- 选择安装层级 ----
if [ -n "${CTFSWEEP_DEVROOT:-}" ]; then
    DEVROOT="$CTFSWEEP_DEVROOT"
    TIER="自定义"
elif [ "$(id -u)" = "0" ]; then
    case "$(uname -s)" in
        Darwin) DEVROOT="/Library/devtools" ;;
        *)      DEVROOT="/usr/local/devtools" ;;
    esac
    TIER="系统级"
else
    DEVROOT="$REAL_HOME/.devtools"
    TIER="用户级"
fi
INSTALL="$DEVROOT/ctfsweep"
USER_DIR="$REAL_HOME/.devtools/ctfsweep"

[ "$(basename "$INSTALL")" = "ctfsweep" ] || { echo "安装路径异常: $INSTALL" >&2; exit 1; }

echo "[ctfsweep] ${TIER}安装 → $INSTALL"

# ---- 旧版迁移：清掉 ~/.local/bin/ctfsweep 软链（仅当指向本仓库）----
OLD_LINK="$REAL_HOME/.local/bin/ctfsweep"
if [ -L "$OLD_LINK" ]; then
    dest="$(readlink "$OLD_LINK")"
    case "$dest" in
        "$ROOT"/*)
            rm -f "$OLD_LINK"
            echo "已清理旧版软链: $OLD_LINK"
            ;;
    esac
fi

# ---- 部署文件（先清后建，保证干净）----
rm -rf "$INSTALL"
mkdir -p "$INSTALL/bin" "$INSTALL/lib" "$INSTALL/config" "$INSTALL/completions"
cp -R "$ROOT/ctfsweep" "$INSTALL/lib/ctfsweep"
find "$INSTALL/lib" \( -name '__pycache__' -o -name '.DS_Store' \) -exec rm -rf {} + 2>/dev/null || true
cp "$ROOT/bin/ctfsweep" "$INSTALL/bin/ctfsweep"
cp "$ROOT/VERSION" "$INSTALL/VERSION"
cp "$ROOT/config/ctfsweep.conf" "$INSTALL/config/ctfsweep.conf"
cp "$ROOT/completions/ctfsweep.zsh" "$ROOT/completions/ctfsweep.bash" "$INSTALL/completions/"
chmod +x "$INSTALL/bin/ctfsweep"
cp "$ROOT/installer/uninstall.sh" "$INSTALL/uninstall"
chmod +x "$INSTALL/uninstall"
echo "已部署: $INSTALL/bin/ctfsweep（lib / config / completions 就位）"

# ---- 用户数据目录：补全副本（shell 配置 source 这里）----
mkdir -p "$USER_DIR/completions"
cp "$ROOT/completions/ctfsweep.zsh" "$ROOT/completions/ctfsweep.bash" "$USER_DIR/completions/"

# ---- shell 接线：先剥离旧块，再写入新块（幂等）----
strip_block() {
    local f="$1" tmp tmp2
    [ -f "$f" ] || return 0
    grep -q -e "completions/ctfsweep" -e "devtools/ctfsweep/bin" -e "^# ctfsweep$" -e "^alias ctf='ctfsweep'" "$f" 2>/dev/null || return 0
    tmp="$f.ctfsweep.tmp.$$"
    grep -v -e "completions/ctfsweep" -e "devtools/ctfsweep/bin" -e "^# ctfsweep$" -e "^alias ctf='ctfsweep'" "$f" > "$tmp" || true
    tmp2="$tmp.n"
    printf '%s\n' "$(cat "$tmp")" > "$tmp2"      # 规整尾部空行（防止反复安装堆积）
    cat "$tmp2" > "$f"                            # 原地覆盖，保留原属主/权限（sudo 场景友好）
    rm -f "$tmp" "$tmp2"
}

# shell 目标：优先取登录用户的 shell（sudo 场景）
shell_name="$(basename "${SHELL:-}")"
if [ -n "${SUDO_USER:-}" ]; then
    if [ "$(uname -s)" = "Darwin" ]; then
        rs="$(dscl . -read "/Users/${SUDO_USER}" UserShell 2>/dev/null | awk '{print $2}')" || true
    else
        rs="$(getent passwd "$SUDO_USER" 2>/dev/null | cut -d: -f7)" || true
    fi
    [ -n "${rs:-}" ] && shell_name="$(basename "$rs")"
fi
case "$shell_name" in
    bash) RC="$REAL_HOME/.bashrc"; COMP_FILE="ctfsweep.bash" ;;
    *)    RC="$REAL_HOME/.zshrc";  COMP_FILE="ctfsweep.zsh" ;;
esac

strip_block "$REAL_HOME/.zshrc"
strip_block "$REAL_HOME/.bashrc"
if [ -f "$RC" ]; then
    {
        echo ""
        echo "# ctfsweep"
        echo "export PATH=\"$INSTALL/bin:\$PATH\""
        echo "alias ctf='ctfsweep'"
        echo "[ -f \"$USER_DIR/completions/$COMP_FILE\" ] && source \"$USER_DIR/completions/$COMP_FILE\""
    } >> "$RC"
    echo "已写入 shell 配置: ${RC}（重开终端或 source 后生效）"
else
    echo "提示: $RC 不存在，请手动把下面一行加入 shell 配置："
    echo "  export PATH=\"$INSTALL/bin:\$PATH\""
fi

# ---- sudo 场景：把用户数据目录交还登录用户 ----
if [ "$(id -u)" = "0" ] && [ -n "${SUDO_USER:-}" ]; then
    chown -R "$SUDO_USER" "$USER_DIR" 2>/dev/null || true
fi

echo "完成。重开终端后运行 'ctfsweep --help'（或短命令 'ctf --help'）开始使用。"
if [ "$(id -u)" != "0" ] && [ -z "${CTFSWEEP_DEVROOT:-}" ]; then
    echo "提示: 如需系统级安装（/Library/devtools，多用户共享），运行: sudo $0"
fi
