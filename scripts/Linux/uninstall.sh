#!/bin/bash
# jtool 卸载入口 (macOS)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

source "$PROJECT_DIR/module/common.sh"

do_uninstall
