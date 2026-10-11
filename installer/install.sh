#!/usr/bin/env bash
# ctfsweep 一键安装脚本（macOS / Linux）
#
# 一键安装（安装后自动刷新当前终端，无需手动 source）:
#   source <(curl -fsSL https://raw.githubusercontent.com/CK627/MyProject/CtfSweep/installer/install.sh)
#
# 传统用法（安装后需重开终端或手动 source）:
#   curl -fsSL https://raw.githubusercontent.com/CK627/MyProject/CtfSweep/installer/install.sh | bash
#
# 国内镜像（无需 VPN，同一份脚本，只是换个下载地址）:
#   source <(curl -fsSL http://101.132.165.98/dist/ctfsweep/install.sh)
#
# 在源码仓库内运行（自动识别，用本地源码安装）:
#   ./installer/install.sh          # 默认用户级 → ~/.devtools/ctfsweep
#   sudo ./installer/install.sh     # 系统级 → /Library/devtools/ctfsweep
#
# 说明:
#   · 本脚本设计为可被 source 加载：顶层不使用 exit（会关掉用户 shell），
#     安装逻辑全部在子 shell 里隔离；安装成功后由父 shell 刷新终端配置。
#     （子 shell 是独立命令 + 显式判退出码，不写成 `( ... ) && {...}`——
#     POSIX 规定 AND-OR 列表中非末位命令忽略 set -e，失败会被吞掉。）
#   · 不在源码目录里运行时（curl 管道 / 下载后的脚本），会先下载源码快照
#     （先镜像后 GitHub，全部失败才报错），再交给 install-from-source.sh 安装。
#   · 换源：CTFSWEEP_MIRROR=<url> 指定其他镜像；CTFSWEEP_MIRROR=none 强制只走 GitHub。

# ---- 顶层（对 source 安全）：定位自身，判断「仓库内运行」还是「远程自举」----
_ctfsweep_self=""
if [ -n "${BASH_VERSION:-}" ]; then
    _ctfsweep_self="${BASH_SOURCE[0]:-}"
elif [ -n "${ZSH_VERSION:-}" ]; then
    eval '_ctfsweep_self="${(%):-%x}"' 2>/dev/null || _ctfsweep_self=""
else
    _ctfsweep_self="${0:-}"
fi

_ctfsweep_src=""
if [ -n "$_ctfsweep_self" ] && [ -f "$_ctfsweep_self" ]; then
    _ctfsweep_dir="$(cd "$(dirname "$_ctfsweep_self")" 2>/dev/null && pwd)" || _ctfsweep_dir=""
    if [ -n "${_ctfsweep_dir:-}" ]; then
        _ctfsweep_parent="$(cd "$_ctfsweep_dir/.." 2>/dev/null && pwd)" || _ctfsweep_parent=""
        if [ -n "${_ctfsweep_parent:-}" ] \
           && [ -f "$_ctfsweep_parent/ctfsweep/__main__.py" ] \
           && [ -f "$_ctfsweep_parent/VERSION" ] \
           && [ -f "$_ctfsweep_parent/installer/install-from-source.sh" ]; then
            _ctfsweep_src="$_ctfsweep_parent"
        fi
    fi
fi

# 是否为 source 加载（决定结尾文案；curl|bash / 直接执行 时为 0）
# 注意：bash 下「BASH_SOURCE 为空」不是 sourced（那是 stdin 管道执行），
# 只有「BASH_SOURCE 非空且不等于 $0」才是被 source。
_ctfsweep_sourced=0
if [ -n "${BASH_VERSION:-}" ]; then
    if [ -n "${BASH_SOURCE[0]:-}" ] && [ "${BASH_SOURCE[0]}" != "${0:-}" ]; then
        _ctfsweep_sourced=1
    fi
elif [ -n "${ZSH_VERSION:-}" ]; then
    case "${ZSH_EVAL_CONTEXT:-}" in
        *file*) _ctfsweep_sourced=1 ;;
    esac
fi

_ctfsweep_rc=0
_ctfsweep_action=install

case "${1:-}" in
    ""|install) ;;
    -h|--help)
        _ctfsweep_action=help
        printf '%s\n' \
            "用法:" \
            "  一键安装（推荐）: source <(curl -fsSL https://raw.githubusercontent.com/CK627/MyProject/CtfSweep/installer/install.sh)" \
            "  国内镜像安装:     source <(curl -fsSL http://101.132.165.98/dist/ctfsweep/install.sh)" \
            "  传统安装:         curl -fsSL https://raw.githubusercontent.com/CK627/MyProject/CtfSweep/installer/install.sh | bash" \
            "  源码安装:         ./installer/install-from-source.sh install" \
            "  卸载:             ./installer/uninstall.sh"
        ;;
    *)
        _ctfsweep_action=bad
        _ctfsweep_rc=2
        printf '未知参数: %s（用 --help 查看用法）\n' "$1" >&2
        ;;
esac

if [ "$_ctfsweep_action" = "install" ]; then
    # ---- 安装（子 shell 隔离：失败只影响子 shell，不会打断用户的终端）----
    (
        set -euo pipefail

        err()  { echo "错误: $*" >&2; exit 1; }
        info() { echo "==> $*"; }

        SRCROOT="$_ctfsweep_src"
        _ctfsweep_boot=0
        TMPDIR_DL=""

        cleanup() {
            if [ -n "$TMPDIR_DL" ]; then rm -rf "$TMPDIR_DL" || true; fi
            return 0
        }
        trap cleanup EXIT

        if [ -z "$SRCROOT" ]; then
            _ctfsweep_boot=1
            # —— 远程自举：下载源码快照（镜像优先，回退 GitHub）——
            # 镜像在国内直连可达，raw.githubusercontent.com 不保证——把镜像放前面，
            # 「不开 VPN 也能装」才是真的，而不是「卡一阵后失败」。
            command -v curl >/dev/null 2>&1 || err "需要 curl，请先安装（或下载源码后在仓库内运行 ./installer/install.sh）"
            command -v tar  >/dev/null 2>&1 || err "需要 tar（系统自带）"

            MIRROR="${CTFSWEEP_MIRROR:-http://101.132.165.98/dist/ctfsweep}"
            GITHUB="https://github.com/CK627/MyProject/archive/refs/heads/CtfSweep.tar.gz"
            TMPDIR_DL="$(mktemp -d)" || err "无法创建临时目录"

            TGZ="$TMPDIR_DL/ctfsweep-src.tar.gz"
            got=0
            if [ "$MIRROR" != "none" ]; then
                info "下载源码快照（镜像）: $MIRROR/ctfsweep-src.tar.gz"
                if curl -fL --connect-timeout 6 --max-time 60 -o "$TGZ" "$MIRROR/ctfsweep-src.tar.gz" 2>/dev/null && [ -s "$TGZ" ]; then
                    got=1
                else
                    info "镜像不可用，回退 GitHub"
                fi
            fi
            if [ "$got" -eq 0 ]; then
                info "下载源码快照: $GITHUB"
                curl -fL --connect-timeout 10 --max-time 180 --progress-bar -o "$TGZ" "$GITHUB" \
                    || err "下载失败，请检查网络；国内网络可直接用镜像安装: source <(curl -fsSL http://101.132.165.98/dist/ctfsweep/install.sh)"
                [ -s "$TGZ" ] || err "下载到的文件是空的"
            fi

            mkdir -p "$TMPDIR_DL/src"
            tar -xzf "$TGZ" -C "$TMPDIR_DL/src" || err "解压失败"
            SRCROOT="$TMPDIR_DL/src"
            if [ ! -f "$SRCROOT/installer/install-from-source.sh" ]; then
                # GitHub archive / 镜像快照的顶层目录都是 MyProject-<分支>，探一层
                _sub="$(find "$SRCROOT" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | head -n 1)"
                if [ -n "${_sub:-}" ] && [ -f "$_sub/installer/install-from-source.sh" ]; then
                    SRCROOT="$_sub"
                fi
            fi
            [ -f "$SRCROOT/installer/install-from-source.sh" ] || err "源码快照结构异常（缺少 installer/install-from-source.sh）"
        else
            info "检测到源码仓库（${SRCROOT}），使用本地源码安装"
        fi

        CTFSWEEP_BOOTSTRAP="$_ctfsweep_boot" bash "$SRCROOT/installer/install-from-source.sh" install
    )
    _ctfsweep_rc=$?

    if [ "$_ctfsweep_rc" -eq 0 ]; then
        if [ "$_ctfsweep_sourced" = "1" ]; then
            # source 用法：刷新当前终端（脚本运行在用户 shell 里，source rc 即时生效；
            # curl|bash 用法下这段在子进程里，无副作用）
            if [ -n "${ZSH_VERSION:-}" ]; then
                source "$HOME/.zshrc" 2>/dev/null || true
            elif [ -n "${BASH_VERSION:-}" ]; then
                source "$HOME/.bashrc" 2>/dev/null || true
            fi
            echo "==> ctfsweep 安装完成，已刷新当前终端"
        else
            echo "==> ctfsweep 安装完成，请重开终端（或 source 对应配置文件）使配置生效"
        fi
    else
        echo "错误: ctfsweep 安装失败（退出码 ${_ctfsweep_rc}）" >&2
    fi
fi

# 清理中间变量（顶层留下的变量不该污染用户 shell）
unset _ctfsweep_self _ctfsweep_dir _ctfsweep_parent _ctfsweep_src _ctfsweep_sourced _ctfsweep_action 2>/dev/null || true

# 最后一条命令决定脚本退出码，让 `curl ... | bash` 等调用方也能拿到真实结果
[ "$_ctfsweep_rc" -eq 0 ]
