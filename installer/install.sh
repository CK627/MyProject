#!/bin/bash
# ptool 一行安装脚本
#
# 用法:
#   curl -fsSL https://raw.githubusercontent.com/CK627/MyProject/ptool/installer/install.sh | bash
#
# macOS  : 下载最新 Release 的 .pkg 并安装（带安装器收据、可干净卸载）
# Linux  : 下载源码后运行 scripts/Linux/install.sh
# Windows: 请下载 Release 里的 .exe 安装

set -euo pipefail

TOOL="ptool"
OWNER="CK627"
REPO="MyProject"
BASE="https://github.com/$OWNER/$REPO"

info() { echo "==> $*"; }
die() { echo "错误: $*" >&2; exit 1; }

command -v curl >/dev/null 2>&1 || die "需要 curl，请先安装"

case "$(uname -s)" in
    Darwin)
        # 动态解析最新版本 tag（ptool-v2.2.0 -> 2.2.0）
        command -v git >/dev/null 2>&1 || die "需要 git 解析版本号（xcode-select --install）"
        info "解析最新版本..."
        VERSION=$(git ls-remote --tags "$BASE.git" "refs/tags/${TOOL}-v*" \
                  | grep -vF '^{}' \
                  | sed 's|.*refs/tags/||' | sort -V | tail -1)
        [ -n "$VERSION" ] || die "未找到 ${TOOL} 的版本 tag"
        VER="${VERSION#${TOOL}-v}"
        info "安装 ${TOOL} ${VER}"

        PKG="/tmp/${TOOL}-${VER}.pkg"
        URL="$BASE/releases/download/${VERSION}/${TOOL}-${VER}.pkg"
        info "下载 $URL"
        curl -fL --progress-bar "$URL" -o "$PKG"

        info "安装（需要管理员密码）..."
        sudo installer -pkg "$PKG" -target /
        rm -f "$PKG"

        info "完成。重开终端或执行: source ~/.zshrc"
        ;;
    Linux)
        info "下载源码并安装..."
        TMP=$(mktemp -d)
        trap 'rm -rf "$TMP"' EXIT
        curl -fsSL "$BASE/archive/refs/heads/${TOOL}.tar.gz" | tar xz -C "$TMP"
        (cd "$TMP/${REPO}-${TOOL}" && ./scripts/Linux/install.sh)
        info "完成。重开终端或执行: source ~/.bashrc"
        ;;
    *)
        die "不支持的系统。Windows 请下载安装包: $BASE/releases"
        ;;
esac
