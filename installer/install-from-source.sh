#!/bin/bash
# 从源码安装 / 卸载（macOS / Linux 通用）
#
# 用法:
#   ./installer/install-from-source.sh install     # 安装
#   ./installer/install-from-source.sh uninstall   # 卸载
#   ./installer/install-from-source.sh scan        # 扫描 Python 路径
#   ./installer/install-from-source.sh config      # 查看配置
#
# do_install / do_uninstall 内部用 uname 区分 macOS 和 Linux 的安装路径，
# 所以一个脚本即可覆盖两个平台，不必再各放一份几乎相同的 install.sh / uninstall.sh。

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TOOL="$(basename "$PROJECT_DIR")"
CONFIG="$PROJECT_DIR/config/$TOOL.conf"

source "$PROJECT_DIR/module/common.sh"

case "${1:-install}" in
    install)   do_install "$PROJECT_DIR" ;;
    uninstall) do_uninstall ;;
    scan)      do_scan "$CONFIG" ;;
    config)    do_config "$CONFIG" ;;
    help)      echo "用法: $0 [install|uninstall|scan|config|help]" ;;
    *)         echo "未知命令: $1"; exit 1 ;;
esac
