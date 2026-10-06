#!/bin/bash
# ptool 一键安装脚本（macOS / Linux）
#
# 用法（安装后自动刷新当前终端，无需手动 source）:
#   source <(curl -fsSL https://raw.githubusercontent.com/CK627/MyProject/ptool/installer/install.sh)
#
# 传统用法（安装后需重开终端或手动 source）:
#   curl -fsSL https://raw.githubusercontent.com/CK627/MyProject/ptool/installer/install.sh | bash
#
# macOS : 下载最新 Release 的 .pkg 并安装（带安装器收据）
# Linux : 下载源码后运行 installer/install-from-source.sh
# Windows: 请用 PowerShell 一键安装（install.ps1）
#
# 注意：本脚本设计为可被 source 加载，因此不能用顶层 exit（会退出用户 shell），
# 安装逻辑全部放在子 shell 里隔离，成功后由父 shell 执行 source 刷新环境。

(
    set -euo pipefail

    TOOL="ptool"
    OWNER="CK627"
    REPO="MyProject"
    BASE="https://github.com/$OWNER/$REPO"

    err() { echo "错误: $*" >&2; exit 1; }
    info() { echo "==> $*"; }

    command -v curl >/dev/null 2>&1 || err "需要 curl，请先安装"

    case "$(uname -s)" in
        Darwin)
            command -v git >/dev/null 2>&1 || err "需要 git 解析版本号（xcode-select --install）"
            info "解析最新版本..."
            VERSION=$(git ls-remote --tags "$BASE.git" "refs/tags/${TOOL}-v*" \
                      | grep -vF '^{}' \
                      | sed 's|.*refs/tags/||' | sort -V | tail -1)
            [ -n "$VERSION" ] || err "未找到 ${TOOL} 的版本 tag"
            VER="${VERSION#${TOOL}-v}"
            info "安装 ${TOOL} ${VER}"

            PKG="/tmp/${TOOL}-${VER}.pkg"
            URL="$BASE/releases/download/${VERSION}/${TOOL}-${VER}.pkg"
            info "下载 $URL"
            curl -fL --progress-bar "$URL" -o "$PKG"

            info "安装（需要管理员密码）..."
            sudo installer -pkg "$PKG" -target /
            rm -f "$PKG"
            ;;
        Linux)
            info "下载源码并安装..."
            TMP=$(mktemp -d)
            trap 'rm -rf "$TMP"' EXIT
            curl -fsSL "$BASE/archive/refs/heads/${TOOL}.tar.gz" | tar xz -C "$TMP"
            (cd "$TMP/${REPO}-${TOOL}" && ./installer/install-from-source.sh)
            ;;
        *)
            err "不支持的系统。Windows 请用 PowerShell 一键安装"
            ;;
    esac
) && {
    # 安装成功：刷新当前 shell（source 用法下生效；curl|bash 用法下这里是子进程，无效）
    if [ -n "${ZSH_VERSION:-}" ]; then
        source ~/.zshrc 2>/dev/null
    elif [ -n "${BASH_VERSION:-}" ]; then
        source ~/.bashrc 2>/dev/null
    fi
    echo "==> ${TOOL} 安装完成，已刷新当前终端"
}
