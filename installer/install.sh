#!/bin/bash
# jtool 一键安装脚本（macOS / Linux）
#
# 用法（安装后自动刷新当前终端，无需手动 source）:
#   source <(curl -fsSL https://raw.githubusercontent.com/CK627/MyProject/jtool/installer/install.sh)
#
# 传统用法（安装后需重开终端或手动 source）:
#   curl -fsSL https://raw.githubusercontent.com/CK627/MyProject/jtool/installer/install.sh | bash
#
# 国内镜像（无需 VPN，同一份脚本，只是换个下载地址）:
#   source <(curl -fsSL http://101.132.165.98/dist/jtool/install.sh)
#
# macOS : 下载最新 Release 的 .dmg，挂载后安装里面的 .pkg（带安装器收据）
# Linux : 下载最新 Release 的 <tool>-<ver>-linux.tar.gz，运行其中的 install-from-source.sh
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

    TOOL="jtool"
    OWNER="CK627"
    REPO="MyProject"
    BASE="https://github.com/$OWNER/$REPO"

    # 安装源：默认先走国内镜像，拿不到再回退 GitHub Release。
    #   · 这台镜像机在国内直连可达，raw.githubusercontent.com / api.github.com 则不保证；
    #     把镜像放在前面，「不开 VPN 也能装」才是真的，而不是「卡 30 秒后失败」。
    #   · 覆盖方式：JTOOL_MIRROR=<url> 换镜像地址，JTOOL_MIRROR=none 强制只走 GitHub。
    MIRROR="${JTOOL_MIRROR:-http://101.132.165.98/dist/jtool}"

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

    # ---------------------------------------------------------------
    # 版本解析（两平台共用）
    #   · 发布 tag 是 annotated：ls-remote 会多打印 refs/tags/x^{}，必须用
    #     grep -vF '^{}' 去掉，否则会选中 jtool-v2.2.15^{} 拼出错误 URL
    #   · 排序用 sort -t. -k1,1n -k2,2n -k3,3n，不用 sort -V：-V 在旧系统上
    #     不一定有（bin/jtool.sh 里就有同样的可用性判断）
    #   · 没有 git 时回退 GitHub API：Linux 侧原本不要求装 git
    # ---------------------------------------------------------------
    resolve_latest() {
        # 镜像优先：它就是一个纯文本 VERSION，一次 GET 就够，比 ls-remote / API 都快。
        # 超时必须短——国内访问 GitHub 常见的不是「连不上」而是「连上后一直挂着」，
        # 没有 --max-time 就会把整个安装卡死在第一步，看起来像脚本坏了。
        if [ "$MIRROR" != "none" ]; then
            local mv
            mv=$(curl -fsSL --connect-timeout 6 --max-time 15 "$MIRROR/VERSION" 2>/dev/null | tr -d '[:space:]')
            if [ -n "$mv" ]; then printf '%s\n' "$mv"; return 0; fi
        fi
        if command -v git >/dev/null 2>&1; then
            git ls-remote --tags "$BASE.git" "refs/tags/${TOOL}-v*" \
                | grep -vF '^{}' \
                | sed "s|.*refs/tags/${TOOL}-v||" \
                | sort -t. -k1,1n -k2,2n -k3,3n | tail -1
        else
            curl -fsSL "https://api.github.com/repos/$OWNER/$REPO/releases?per_page=100" \
                | grep -oE "\"tag_name\"[[:space:]]*:[[:space:]]*\"${TOOL}-v[0-9.]+\"" \
                | sed -E "s/.*\"${TOOL}-v([0-9.]+)\"/\1/" \
                | sort -t. -k1,1n -k2,2n -k3,3n | tail -1
        fi
    }

    # 下载发布资产：先镜像，再 GitHub Release。
    # 镜像按 <base>/<version>/<asset> 布局，与 release 里的资产同名，所以调用方只
    # 传文件名和版本号，不用关心当前走的是哪条路。
    fetch_asset() {
        # $1 资产文件名  $2 版本号  $3 输出路径
        local asset="$1" ver="$2" out="$3"
        rm -f "$out" 2>/dev/null || true
        if [ "$MIRROR" != "none" ]; then
            local murl="$MIRROR/$ver/$asset"
            info "下载 $murl"
            # 大文件（dmg / tar.gz）不能套短 --max-time，否则 20 秒就被掐断；
            # 这里只给连接阶段设超时，传输阶段交给 curl 自己跑。
            if curl -fL --connect-timeout 6 --progress-bar "$murl" -o "$out" 2>/dev/null \
               && [ -s "$out" ]; then
                return 0
            fi
            info "镜像上没有该版本，回退 GitHub Release"
        fi
        local gurl="$BASE/releases/download/${TOOL}-v${ver}/${asset}"
        info "下载 $gurl"
        curl -fL --progress-bar "$gurl" -o "$out"
    }

    case "$(uname -s)" in
        Darwin)
            # hdiutil 是 macOS 自带命令，缺失说明系统环境异常，早报比晚报好
            command -v hdiutil >/dev/null 2>&1 || err "需要 hdiutil（macOS 自带）"
            info "解析最新版本..."
            VER="$(resolve_latest)" || err "无法解析最新版本，请检查网络"
            [ -n "$VER" ] || err "未找到 ${TOOL} 的版本 tag"
            info "安装 ${TOOL} ${VER}"

            # 发布产物是 .dmg，.pkg 打在 dmg 里，所以要先挂载再从挂载点安装。
            # 别再改回直接下载 .pkg：Release 里没有这个资产，只会拿到 404。
            #
            # 下载到 mktemp -d 出来的私有目录，而不是固定的 /tmp/<工具>-<版本>.dmg：
            # 固定名字在多人机器上可以被人抢先建成符号链接，curl -o 会顺着写穿到别处。
            TMPDIR_DL=$(mktemp -d)
            DMG="$TMPDIR_DL/${TOOL}-${VER}.dmg"
            fetch_asset "${TOOL}-${VER}.dmg" "$VER" "$DMG" || err "下载失败：${TOOL}-${VER}.dmg"
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
            # 与 macOS 对齐：取 release 里已打包好的产物，而不是分支 HEAD。
            # 分支 HEAD 是「未发布代码」，写进配置的版本号也随之漂移；release
            # 资产（installer/linux-build.sh 产出、随 tag 上传）才是用户要装的东西。
            info "解析最新版本..."
            VER="$(resolve_latest)" || err "无法解析最新版本，请检查网络"
            [ -n "$VER" ] || err "未找到 ${TOOL} 的发布版本"
            ASSET="${TOOL}-${VER}-linux.tar.gz"
            TMPDIR_DL=$(mktemp -d)
            fetch_asset "$ASSET" "$VER" "$TMPDIR_DL/$ASSET" || err "下载失败：$ASSET"
            [ -s "$TMPDIR_DL/$ASSET" ] || err "下载到的文件是空的：$ASSET"
            tar -xzf "$TMPDIR_DL/$ASSET" -C "$TMPDIR_DL" || err "解压失败：$ASSET"
            info "安装（需要管理员密码）..."
            (cd "$TMPDIR_DL/${TOOL}-${VER}" && ./installer/install-from-source.sh install) \
                || err "安装失败"
            ;;
        *)
            err "不支持的系统。Windows 请用 PowerShell 一键安装"
            ;;
    esac
)

# 注意变量名不能叫 status：zsh 里 status 是与 $? 绑定的特殊变量。
_jtool_rc=$?
if [ "$_jtool_rc" -eq 0 ]; then
    # 安装成功：刷新当前 shell（source 用法下生效；curl|bash 用法下这里是子进程，无效）
    if [ -n "${ZSH_VERSION:-}" ]; then
        source ~/.zshrc 2>/dev/null
    elif [ -n "${BASH_VERSION:-}" ]; then
        source ~/.bashrc 2>/dev/null
    fi
    echo "==> jtool 安装完成，已刷新当前终端"
else
    echo "错误: jtool 安装失败（退出码 ${_jtool_rc}），未改动当前终端" >&2
fi
# 最后一条命令决定脚本退出码，让 `curl ... | bash` 或 set -e 的调用方也能拿到真实结果
[ "$_jtool_rc" -eq 0 ]
