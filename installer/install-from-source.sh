#!/usr/bin/env bash
# ctfsweep 从源码安装 / 卸载（macOS / Linux）—— devtools 布局（与 jtool / ptool 同规）
#
# 用法:
#   ./installer/install-from-source.sh install          # 安装（默认系统级，与 jtool / ptool 一致）
#   ./installer/install-from-source.sh uninstall        # 卸载（等价于 installer/uninstall.sh）
#   ./installer/install-from-source.sh print-install-dir  # 只打印解析出的安装根，不落盘
#
# 目录:
#   系统级（默认）: /Library/devtools/ctfsweep     (macOS)
#                   /usr/local/devtools/ctfsweep  (Linux)
#   用户级（CTFSWEEP_USER=1，无需密码）: ~/.devtools/ctfsweep
#   扫描缓存目录（扫描时惰性创建，永不删除）: ~/.devtools/ctfsweep/cache/
#
# 层级选择（与 jtool / ptool 一致：一键安装直接装系统级，脚本内提示管理员密码）:
#   · 默认            → 系统级；需要写 /Library 时用 sudo 执行落盘（会提示输密码）
#   · CTFSWEEP_USER=1 → 用户级 ~/.devtools/ctfsweep（不弹密码；CI / 多环境隔离用）
#   · CTFSWEEP_DEVROOT=<dir> → 显式指定 devtools 根（优先级最高，测试用）
#
# 说明:
#   · 这里是本地的真实安装逻辑；一键安装脚本 installer/install.sh 在远程自举
#     （下载源码快照）后，调用的同样是本脚本。
#   · 布局的实现在 installer/deploy.sh（唯一一份），shell 接线在 installer/shell-setup.sh；
#     本脚本只负责选层级、迁移旧软链、调这两个。
#   · 落盘提权走 run_priv()：目标可写就直接跑，否则 sudo —— 与 ctfsweep update 的
#     _run_root 同口径。shell 接线（shell-setup.sh）**不走 sudo**：sudo 之后 HOME 变成
#     root 的，rc 就写错地方了（shell-setup.sh 自己认 SUDO_USER 决定写谁家的 rc）。
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

case "${1:-install}" in
    install|print-install-dir) ;;
    uninstall)
        exec "$DIR/uninstall.sh"
        ;;
    -h|--help)
        printf '%s\n' \
            "用法:" \
            "  $0 install            # 安装（默认系统级；CTFSWEEP_USER=1 走用户级）" \
            "  $0 uninstall          # 卸载" \
            "  $0 print-install-dir  # 只打印解析出的安装根，不落盘"
        exit 0
        ;;
    *)
        echo "未知参数: ${1}（可用 --help）" >&2
        exit 2
        ;;
esac

ROOT="$(cd "$DIR/.." && pwd)"

# ---- 真实用户目录（sudo 场景下用登录用户，而非 root）----
REAL_HOME="$HOME"
if [ "$(id -u)" = "0" ] && [ -n "${SUDO_USER:-}" ]; then
    REAL_HOME="$(eval echo "~${SUDO_USER}")"
fi

# ---- 选择安装层级（默认系统级 = jtool / ptool 的样子）----
if [ -n "${CTFSWEEP_DEVROOT:-}" ]; then
    DEVROOT="$CTFSWEEP_DEVROOT"
    TIER="自定义"
elif [ "${CTFSWEEP_USER:-0}" = "1" ]; then
    DEVROOT="$REAL_HOME/.devtools"
    TIER="用户级"
else
    case "$(uname -s)" in
        Darwin) DEVROOT="/Library/devtools" ;;
        *)      DEVROOT="/usr/local/devtools" ;;
    esac
    TIER="系统级"
fi
INSTALL="$DEVROOT/ctfsweep"
USER_DIR="$REAL_HOME/.devtools/ctfsweep"

[ "$(basename "$INSTALL")" = "ctfsweep" ] || { echo "安装路径异常: $INSTALL" >&2; exit 1; }
if [ "$(basename "$DEVROOT")" = "." ] || [ "$DEVROOT" = "/" ]; then
    echo "拒绝安装到 ${DEVROOT}（devtools 根目录名异常）" >&2
    exit 1
fi

# 只问不装：冒烟据此断言默认层级，用户也能先看清装到哪
if [ "${1:-install}" = "print-install-dir" ]; then
    printf '%s\n' "$INSTALL"
    exit 0
fi

echo "[ctfsweep] ${TIER}安装 → $INSTALL"

# ---- 落盘提权：目标可写就直接跑，否则 sudo（与 selfmgr._run_root 同口径）----
run_priv() {
    if [ "$(id -u)" = "0" ]; then
        "$@"
    elif [ -w "$DEVROOT" ] || { [ ! -e "$DEVROOT" ] && [ -w "$(dirname "$DEVROOT")" ]; }; then
        "$@"
    else
        command -v sudo >/dev/null 2>&1 \
            || { echo "无写权限且找不到 sudo: ${DEVROOT}（可改用 CTFSWEEP_USER=1 装到用户级）" >&2; exit 1; }
        # 非交互环境（CI / curl | bash 且无 tty）下 sudo 只会抛 "a terminal is required"，
        # 与其让用户对着一句 sudo 报错猜，不如直接给出可用出口
        if [ ! -t 0 ] && ! sudo -n true 2>/dev/null; then
            echo "安装到 ${INSTALL} 需要管理员权限，但当前没有终端可以输入密码。" >&2
            echo "  改用用户级安装（无需密码）: CTFSWEEP_USER=1 <同样的安装命令>" >&2
            exit 1
        fi
        echo "  安装到 $INSTALL 需要管理员权限，可能提示输入密码。"
        sudo "$@"
    fi
}

# ---- 旧版迁移：清掉 ~/.local/bin/ctfsweep 软链（仅当指向本仓库）----
OLD_LINK="$REAL_HOME/.local/bin/ctfsweep"
if [ -L "$OLD_LINK" ]; then
    dest="$(readlink "$OLD_LINK")"
    case "$dest" in
        "$ROOT"/*)
            rm -f "$OLD_LINK"
            echo "已清理旧版软链: $OLD_LINK"
            ;;
    esac
fi

# ---- 部署文件（布局实现在 deploy.sh，唯一一份；先 preflight 再删，只删功能项）----
run_priv bash "$ROOT/installer/deploy.sh" "$ROOT" "$INSTALL"

# ---- shell 接线（成对标记块，幂等；rc 不存在时创建）----
bash "$ROOT/installer/shell-setup.sh" install "$INSTALL"

# ---- sudo 场景：把扫描缓存目录交还登录用户（扫描时才创建，这里只处理已存在的）----
if [ "$(id -u)" = "0" ] && [ -n "${SUDO_USER:-}" ] && [ -d "$USER_DIR" ]; then
    chown -R "$SUDO_USER" "$USER_DIR" 2>/dev/null || true
fi

# 「要不要重开终端」不在这里下结论：shell-setup.sh 上一行已按 rc 改没改如实报了
# （首次安装通常是「已写入…重开终端或 source 后生效」，重复安装则是「接线一致」）。
echo "完成。运行 'ctfsweep --help' 开始使用。"
# 提示反方向：现在是系统级默认，要装用户级才需要额外一个环境变量。
# 引导 / 更新模式（从临时快照安装：install.sh 自举、ctfsweep update）不提示——
# 那时 $0 指向临时快照，打出来是个马上就消失的路径
if [ "$TIER" = "系统级" ] && [ "${CTFSWEEP_BOOTSTRAP:-0}" != "1" ]; then
    echo "提示: 只想给当前用户装（无需密码，~/.devtools/ctfsweep）: CTFSWEEP_USER=1 $0"
fi
