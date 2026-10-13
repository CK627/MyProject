#!/usr/bin/env bash
# ctfsweep 部署（devtools 布局的唯一实现，与 jtool / ptool 同规）
#
# 用法: deploy.sh <源码目录> <安装根>
#
# 被三处共用：installer/install-from-source.sh、ctfsweep update（用快照里的这份副本）、
# 冒烟测试。要改布局只改这里。
#
# 三条硬约定:
#   1. preflight 挡在删除之前。调用方是 set -e，先删后拷一旦源文件缺失就会中止，
#      留下「已删旧、未建新」的半安装残骸，shell 接线根本跑不到。
#   2. 永不 rm -rf <安装根>。用户级安装下安装根就是数据目录，还住着 judge/ cache/ 等
#      用户数据，项目硬契约是「永不自动删除，uninstall 也保留」；删除范围收窄到功能项。
#   3. 白名单拷贝，绝不 cp -R bin。那会把 Windows 启动器 ctfsweep.bat 带进 PATH，
#      命令名补全就会同时列出 ctfsweep 和 ctfsweep.bat —— 正是本布局要修的病。
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
for cand in "$SRC/bin/ctfsweep.sh" "$SRC/bin/ctfsweep"; do
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
    echo "缺少源文件: $SRC/bin/ctfsweep.sh（或 bin/ctfsweep）" >&2
    _missing=1
fi
_need "$SRC/ctfsweep/__main__.py"
_need "$SRC/VERSION"
_need "$SRC/config/ctfsweep.conf"
_need "$SRC/completions/ctfsweep.zsh"
_need "$SRC/completions/ctfsweep.bash"
_need "$SRC/installer/uninstall.sh"
# models/ 必须一起装：安装态下 judge.project_dir() 解析为 <安装根>/lib，
# 于是 models_dir() = <安装根>/lib/models；不装的话 --judge 会**静默**显示「未训练」。
_need "$SRC/models/model.ctfj"
_need "$SRC/models/train_config.json"
if [ "$_missing" -ne 0 ]; then
    echo "部署中止：源码不完整，未改动 $DEST" >&2
    exit 1
fi

mkdir -p "$DEST"
DEST="$(cd "$DEST" && pwd)"
echo "[ctfsweep] 部署 → $DEST"

# ---- 只删功能项（保留 judge/ cache/ auto_learn/ 等用户数据）----
for item in bin lib completions config VERSION uninstall deploy.sh shell-setup.sh; do
    rm -rf "$DEST/$item"
done

# ---- 白名单拷贝 ----
mkdir -p "$DEST/bin" "$DEST/lib" "$DEST/config" "$DEST/completions"
cp -R "$SRC/ctfsweep" "$DEST/lib/ctfsweep"
cp -R "$SRC/models" "$DEST/lib/models"
find "$DEST/lib" \( -name '__pycache__' -o -name '.DS_Store' \) -exec rm -rf {} + 2>/dev/null || true
cp "$SRC/VERSION" "$DEST/VERSION"
cp "$SRC/config/ctfsweep.conf" "$DEST/config/ctfsweep.conf"
cp "$SRC/completions/ctfsweep.zsh" "$SRC/completions/ctfsweep.bash" "$DEST/completions/"
cp "$SRC/installer/uninstall.sh" "$DEST/uninstall"
chmod +x "$DEST/uninstall"
for f in deploy.sh shell-setup.sh; do
    if [ -f "$SRC/installer/$f" ]; then
        cp "$SRC/installer/$f" "$DEST/$f"
        chmod +x "$DEST/$f"
    fi
done

# ---- 命令入口：真实脚本放 lib/，bin/ 里只放无后缀软链 ----
# bin/ 在 PATH 上，若把 ctfsweep.sh 也留在 bin/，补全就会同时列出 ctfsweep 和 ctfsweep.sh。
# $0 始终是 bin/ctfsweep，启动器据此推导目录，所以真实文件在 lib/ 不影响运行。
cp "$LAUNCHER" "$DEST/lib/ctfsweep.sh"
chmod +x "$DEST/lib/ctfsweep.sh"
ln -sf ../lib/ctfsweep.sh "$DEST/bin/ctfsweep"
# 清理旧布局残留，否则它仍在 PATH 上、仍会出现在补全里
rm -f "$DEST/bin/ctfsweep.sh"

echo "已部署: $DEST/bin/ctfsweep（→ ../lib/ctfsweep.sh；lib / models / config / completions 就位）"
