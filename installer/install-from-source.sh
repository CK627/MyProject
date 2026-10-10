#!/usr/bin/env bash
# 从源码安装 / 卸载 ctfsweep（macOS / Linux）
#
# 用法:
#   ./installer/install-from-source.sh install   [--prefix DIR]
#   ./installer/install-from-source.sh uninstall [--prefix DIR]
#
# 卸载只会移除"指向本仓库"的软链接，不会触碰其他文件。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PREFIX="${PREFIX:-$HOME/.local}"

usage() {
    sed -n '2,7p' "$0"
    exit 1
}

[ $# -ge 1 ] || usage
ACTION="$1"
shift
while [ $# -gt 0 ]; do
    case "$1" in
        --prefix)
            PREFIX="$2"
            shift 2
            ;;
        --prefix=*)
            PREFIX="${1#*=}"
            shift
            ;;
        *)
            echo "未知参数: $1" >&2
            exit 2
            ;;
    esac
done
TARGET="$PREFIX/bin/ctfsweep"

install_it() {
    mkdir -p "$PREFIX/bin"
    chmod +x "$ROOT/bin/ctfsweep"
    ln -sf "$ROOT/bin/ctfsweep" "$TARGET"
    echo "已安装: $TARGET -> $ROOT/bin/ctfsweep"
    echo "可选——shell 补全："
    echo "  bash: 将 completions/ctfsweep.bash 放入 /etc/bash_completion.d/（或 source 它）"
    echo "  zsh : 将 completions/ctfsweep.zsh 所在目录加入 fpath 后重开终端"
    case ":$PATH:" in
        *":$PREFIX/bin:"*) ;;
        *) echo "提示: $PREFIX/bin 不在 PATH 中，请把 'export PATH=\"$PREFIX/bin:\$PATH\"' 加入 shell 配置。" ;;
    esac
}

uninstall_it() {
    if [ -L "$TARGET" ]; then
        dest="$(readlink "$TARGET")"
        case "$dest" in
            "$ROOT"/*)
                rm -f "$TARGET"
                echo "已卸载: 移除 $TARGET"
                ;;
            *)
                echo "跳过: $TARGET 指向其他位置（$dest），未删除。"
                ;;
        esac
    elif [ -e "$TARGET" ]; then
        echo "跳过: $TARGET 不是本仓库创建的软链接，未删除。"
    else
        echo "无需卸载: $TARGET 不存在。"
    fi
}

case "$ACTION" in
    install)
        install_it
        ;;
    uninstall)
        uninstall_it
        ;;
    *)
        usage
        ;;
esac
