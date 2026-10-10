#!/usr/bin/env bash
# ctfsweep 安装脚本（macOS / Linux）
# 1) 把 bin/ctfsweep 软链到 $PREFIX/bin（默认 ~/.local/bin）
# 2) 把补全 source 行写入当前 shell 的 rc（zsh: ~/.zshrc / bash: ~/.bashrc），幂等
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
            sed -n '2,10p' "$0"
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

# ---- 补全接线（幂等：已在 rc 中出现过则跳过）----
case "$(basename "${SHELL:-zsh}")" in
    bash)
        RC="$HOME/.bashrc"
        COMPLETION="$ROOT/completions/ctfsweep.bash"
        ;;
    *)
        RC="$HOME/.zshrc"
        COMPLETION="$ROOT/completions/ctfsweep.zsh"
        ;;
esac
if [ -f "$RC" ]; then
    if grep -q "completions/ctfsweep" "$RC" 2>/dev/null; then
        echo "shell 补全已配置过（${RC}），跳过。"
    else
        {
            echo ""
            echo "# ctfsweep"
            echo "alias ctf='ctfsweep'"
            echo "[ -f \"$COMPLETION\" ] && source \"$COMPLETION\""
        } >> "$RC"
        echo "已写入补全配置（含 ctf 短命令别名）: ${RC}（重开终端或 source \"${RC}\" 后生效）"
    fi
else
    echo "提示: $RC 不存在，跳过补全配置；可手动 source \"$COMPLETION\""
fi

case ":$PATH:" in
    *":$BIN:"*)
        echo "运行 'ctfsweep --help' 开始使用（输入 ctf<TAB> 可补全命令名）。"
        ;;
    *)
        echo "提示: $BIN 不在 PATH 中。把下面一行加入 shell 配置（${RC}）后重开终端："
        echo "  export PATH=\"$BIN:\$PATH\""
        ;;
esac
