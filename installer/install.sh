#!/usr/bin/env bash
# ctfsweep 安装脚本（macOS / Linux）
# 把 bin/ctfsweep 软链到 $PREFIX/bin（默认 ~/.local/bin），不改动其他任何文件。
#
# 用法:
#   ./installer/install.sh                      # 安装到 ~/.local
#   ./installer/install.sh --prefix /usr/local  # 安装到指定前缀
#   PREFIX=/usr/local ./installer/install.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PREFIX="${PREFIX:-$HOME/.local}"

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
        -h|--help)
            sed -n '2,9p' "$0"
            exit 0
            ;;
        *)
            echo "未知参数: $1（可用 --prefix DIR）" >&2
            exit 2
            ;;
    esac
done

BIN="$PREFIX/bin"
mkdir -p "$BIN"
chmod +x "$ROOT/bin/ctfsweep"
ln -sf "$ROOT/bin/ctfsweep" "$BIN/ctfsweep"
echo "已安装: $BIN/ctfsweep -> $ROOT/bin/ctfsweep"

case ":$PATH:" in
    *":$BIN:"*)
        echo "运行 'ctfsweep --help' 开始使用。"
        ;;
    *)
        echo "提示: $BIN 不在 PATH 中。把下面一行加入 shell 配置（~/.zshrc 或 ~/.bashrc）后重开终端："
        echo "  export PATH=\"$BIN:\$PATH\""
        ;;
esac
