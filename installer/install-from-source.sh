#!/usr/bin/env bash
# 兼容入口：安装 / 卸载已合并为 install.sh 与 uninstall.sh。
#
# 用法:
#   ./installer/install-from-source.sh install     # → installer/install.sh
#   ./installer/install-from-source.sh uninstall   # → installer/uninstall.sh
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
case "${1:-install}" in
    install)
        exec "$DIR/install.sh"
        ;;
    uninstall)
        exec "$DIR/uninstall.sh"
        ;;
    *)
        echo "用法: $0 [install|uninstall]" >&2
        exit 1
        ;;
esac
