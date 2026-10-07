#!/bin/bash
# ptool 一键安装脚本（macOS / Linux）
#
# 用法（安装后自动刷新当前终端，无需手动 source）:
#   source <(curl -fsSL https://raw.githubusercontent.com/CK627/MyProject/ptool/installer/install.sh)
#
# 传统用法（安装后需重开终端或手动 source）:
#   curl -fsSL https://raw.githubusercontent.com/CK627/MyProject/ptool/installer/install.sh | bash
#
# macOS : 下载最新 Release 的 .dmg，挂载后安装里面的 .pkg（带安装器收据）
# Linux : 下载源码后运行 installer/install-from-source.sh
# Windows: 请用 PowerShell 一键安装（install.ps1）
#
# 注意：本脚本设计为可被 source 加载，因此不能用顶层 exit（会退出用户 shell），
# 安装逻辑全部放在子 shell 里隔离，成功后由父 shell 执行 source 刷新环境。
#
# 子 shell 必须作为独立命令执行，绝不能写成 `( ... ) && { 成功提示 }`：
# POSIX 规定 AND-OR 列表中非末位命令忽略 set -e，而 bash/zsh 都照此实现，
# 于是子 shell 里的任何失败都不会中断，脚本会一路跑到底，最后照样打印
# 「安装完成」——下载 404、installer 失败全被吞掉，用户只看到「没有效果」。
# 现在改成独立执行 + 显式判退出码，失败时明确报错且不刷新终端。
#
# 挂载卷与下载产物的清理走 EXIT trap（见下方 cleanup），不再在每条失败分支里手写：
# 手写版必然漏掉 Ctrl-C 和 sudo 输密码时取消，结果卷留在 /Volumes、dmg 留在 /tmp。

(
    set -euo pipefail

    TOOL="ptool"
    OWNER="CK627"
    REPO="MyProject"
    BASE="https://github.com/$OWNER/$REPO"

    err() { echo "错误: $*" >&2; exit 1; }
    info() { echo "==> $*"; }

    command -v curl >/dev/null 2>&1 || err "需要 curl，请先安装"

    # 下载目录与挂载点先置空：cleanup 挂在 EXIT 上，每条退出路径都会跑它，
    # 包括「还没开始下载」「还没挂载」的那些，所以它必须能安全地什么都不做。
    TMPDIR_DL=""
    MNT=""
    DMG=""
    cleanup() {
        if [ -n "$MNT" ]; then hdiutil detach "$MNT" >/dev/null 2>&1 || true; fi
        if [ -n "$TMPDIR_DL" ]; then rm -rf "$TMPDIR_DL" || true; fi
        return 0
    }
    # 清理只在 EXIT 上挂一次，不在每条失败分支里手写。手写的版本必然漏掉 Ctrl-C
    # 和 sudo 输密码时取消：卷留在 /Volumes、dmg 留在 /tmp，用户看到的就是
    # 「装一次多一个卷」。err 退出、被中断、正常结束，三条路都会走到这里。
    # 只挂 EXIT，别把 INT/TERM 也列进来——那样 bash 跑完 handler 会继续往下执行
    # （实测 rc=0），该中断的地方反而中断不了。
    trap cleanup EXIT

    case "$(uname -s)" in
        Darwin)
            command -v git >/dev/null 2>&1 || err "需要 git 解析版本号（xcode-select --install）"
            # hdiutil 是 macOS 自带命令，缺失说明系统环境异常，早报比晚报好
            command -v hdiutil >/dev/null 2>&1 || err "需要 hdiutil（macOS 自带）"
            info "解析最新版本..."
            VERSION=$(git ls-remote --tags "$BASE.git" "refs/tags/${TOOL}-v*" \
                      | grep -vF '^{}' \
                      | sed 's|.*refs/tags/||' | sort -V | tail -1)
            [ -n "$VERSION" ] || err "未找到 ${TOOL} 的版本 tag"
            VER="${VERSION#${TOOL}-v}"
            info "安装 ${TOOL} ${VER}"

            # 发布产物是 .dmg，.pkg 打在 dmg 里，所以要先挂载再从挂载点安装。
            # 别再改回直接下载 .pkg：Release 里没有这个资产，只会拿到 404。
            #
            # 下载到 mktemp -d 出来的私有目录，而不是固定的 /tmp/<工具>-<版本>.dmg：
            # 固定名字在多人机器上可以被人抢先建成符号链接，curl -o 会顺着写穿到别处。
            TMPDIR_DL=$(mktemp -d)
            DMG="$TMPDIR_DL/${TOOL}-${VER}.dmg"
            URL="$BASE/releases/download/${VERSION}/${TOOL}-${VER}.dmg"
            info "下载 $URL"
            curl -fL --progress-bar "$URL" -o "$DMG" || err "下载失败：$URL"
            [ -s "$DMG" ] || err "下载到的文件是空的：$DMG"

            info "挂载安装包..."
            MNT=$(hdiutil attach -nobrowse -readonly "$DMG" \
                  | grep -o '/Volumes/.*' | head -1)
            [ -n "$MNT" ] || err "挂载失败：$DMG"

            [ -f "$MNT/${TOOL}-${VER}.pkg" ] || err "安装包里没有 ${TOOL}-${VER}.pkg"

            info "安装（需要管理员密码）..."
            sudo installer -pkg "$MNT/${TOOL}-${VER}.pkg" -target / \
                || err "安装失败（可能是密码错误，或安装包与当前系统不兼容）"
            # 卸卷、删 dmg 一步都不用写在这里——EXIT trap 兜底，成功路径也不例外。
            ;;
        Linux)
            info "下载源码并安装..."
            TMPDIR_DL=$(mktemp -d)
            curl -fsSL "$BASE/archive/refs/heads/${TOOL}.tar.gz" | tar xz -C "$TMPDIR_DL"
            (cd "$TMPDIR_DL/${REPO}-${TOOL}" && ./installer/install-from-source.sh)
            ;;
        *)
            err "不支持的系统。Windows 请用 PowerShell 一键安装"
            ;;
    esac
)

# 注意变量名不能叫 status：zsh 里 status 是与 $? 绑定的特殊变量。
_ptool_rc=$?
if [ "$_ptool_rc" -eq 0 ]; then
    # 安装成功：刷新当前 shell（source 用法下生效；curl|bash 用法下这里是子进程，无效）
    if [ -n "${ZSH_VERSION:-}" ]; then
        source ~/.zshrc 2>/dev/null
    elif [ -n "${BASH_VERSION:-}" ]; then
        source ~/.bashrc 2>/dev/null
    fi
    echo "==> ptool 安装完成，已刷新当前终端"
else
    echo "错误: ptool 安装失败（退出码 ${_ptool_rc}），未改动当前终端" >&2
fi
# 最后一条命令决定脚本退出码，让 `curl ... | bash` 或 set -e 的调用方也能拿到真实结果
[ "$_ptool_rc" -eq 0 ]
