#!/bin/bash
# ptool 安装入口 (macOS)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

source "$PROJECT_DIR/module/common.sh"

case "${1:-install}" in
    install) do_install "$PROJECT_DIR" ;;
    scan)    do_scan "$PROJECT_DIR/config/ptool.conf" ;;
    config)  do_config "$PROJECT_DIR/config/ptool.conf" ;;
    help)    echo "用法: common.sh [install|scan|config|help]" ;;
    *)       echo "未知命令: $1"; exit 1 ;;
esac
