#!/usr/bin/env bash
# encoding: utf-8
# startupctl 部署（devtools 布局的唯一实现，与 jtool / ptool 同规）
#
# 用法: deploy.sh <源码目录> <安装根>
#
# 被三处共用：installer/install-from-source.sh、startupctl update（用快照里的这份副本）、
# 冒烟测试。要改布局只改这里。
#
# 三条硬约定:
#   1. preflight 挡在删除之前。调用方是 set -e，先删后拷一旦源文件缺失就会中止，
#      留下「已删旧、未建新」的半安装残骸，shell 接线根本跑不到。
#   2. 永不 rm -rf <安装根>。用户级安装下安装根就是数据目录，还住着 whitelist.json
#      （用户逐条确认过的允许清单）与 backups/（唯一能 restore 的备份），项目硬契约是
#      「永不自动删除，uninstall 也保留」；删除范围收窄到功能项。
#   3. 白名单拷贝，绝不 cp -R bin。那会把 Windows 启动器 startupctl.bat 带进 PATH，
#      命令名补全就会同时列出 startupctl 和 startupctl.bat —— 正是本布局要修的病。
set -euo pipefail

SRC="${1:-}"
DEST="${2:-}"
if [ -z "$SRC" ] || [ -z "$DEST" ]; then
    echo "用法: $0 <源码目录> <安装根>" >&2
    exit 2
fi
[ -d "$SRC" ] || { echo "源码目录不存在: $SRC" >&2; exit 1; }
SRC="$(cd "$SRC" && pwd)"

# ---- 定位启动器（兼容重命名前后的两种名字）----
LAUNCHER=""
for cand in "$SRC/bin/startupctl.sh" "$SRC/bin/startupctl"; do
    if [ -f "$cand" ]; then
        LAUNCHER="$cand"
        break
    fi
done

# ---- preflight：源文件齐不齐（全部检查完再报，一次看全）----
_missing=0
_need() {
    if [ ! -e "$1" ]; then
        echo "缺少源文件: $1" >&2
        _missing=1
    fi
}
if [ -z "$LAUNCHER" ]; then
    echo "缺少源文件: $SRC/bin/startupctl.sh（或 bin/startupctl）" >&2
    _missing=1
fi
_need "$SRC/startupctl/__main__.py"
_need "$SRC/VERSION"
_need "$SRC/config/startupctl.conf"
_need "$SRC/completions/startupctl.zsh"
_need "$SRC/completions/startupctl.bash"
_need "$SRC/installer/uninstall.sh"
if [ "$_missing" -ne 0 ]; then
    echo "部署中止：源码不完整，未改动 $DEST" >&2
    exit 1
fi

mkdir -p "$DEST"
DEST="$(cd "$DEST" && pwd)"
echo "[startupctl] 部署 → $DEST"

# ---- 只删功能项（保留 whitelist.json / backups/ / scans/ 等数据）----
for item in bin lib completions config VERSION uninstall deploy.sh shell-setup.sh; do
    rm -rf "$DEST/$item"
done

# ---- 白名单拷贝 ----
mkdir -p "$DEST/bin" "$DEST/lib" "$DEST/config" "$DEST/completions"
cp -R "$SRC/startupctl" "$DEST/lib/startupctl"
find "$DEST/lib" \( -name '__pycache__' -o -name '.DS_Store' \) -exec rm -rf {} + 2>/dev/null || true
cp "$SRC/VERSION" "$DEST/VERSION"
cp "$SRC/config/startupctl.conf" "$DEST/config/startupctl.conf"
cp "$SRC/completions/startupctl.zsh" "$SRC/completions/startupctl.bash" "$DEST/completions/"
cp "$SRC/installer/uninstall.sh" "$DEST/uninstall"
chmod +x "$DEST/uninstall"
for f in deploy.sh shell-setup.sh; do
    if [ -f "$SRC/installer/$f" ]; then
        cp "$SRC/installer/$f" "$DEST/$f"
        chmod +x "$DEST/$f"
    fi
done

# ---- 命令入口：真实脚本放 lib/，bin/ 里只放无后缀软链 ----
# bin/ 在 PATH 上，若把 startupctl.sh 也留在 bin/，补全就会同时列出 startupctl 和 startupctl.sh。
# $0 始终是 bin/startupctl，启动器据此推导目录，所以真实文件在 lib/ 不影响运行。
cp "$LAUNCHER" "$DEST/lib/startupctl.sh"
chmod +x "$DEST/lib/startupctl.sh"
ln -sf ../lib/startupctl.sh "$DEST/bin/startupctl"
# 清理旧布局残留，否则它仍在 PATH 上、仍会出现在补全里
rm -f "$DEST/bin/startupctl.sh"

# ---- 权限归一（不能继承 umask）----
# ★ cp 跟着**调用方的 umask** 走。`sudo` 会把 umask 透传给子进程，所以只要
#   调用者的 shell 里设过 umask 077（实测踩到），装出来的就是 0600/0700：
#   普通用户连 bin/startupctl 都执行不了（permission denied）。
#   安装/更新必须显式摆正权限，不能指望调用环境。
chmod -R a+rX "$DEST"
chmod 755 "$DEST/lib/startupctl.sh" "$DEST/uninstall" 2>/dev/null || true

echo "已部署: $DEST/bin/startupctl（→ ../lib/startupctl.sh；lib / models / config / completions 就位）"
