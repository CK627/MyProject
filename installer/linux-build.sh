#!/bin/bash
# 构建 Linux 安装包（.tar.gz，通用格式）
#
# 用法:
#   ./installer/linux-build.sh           正式构建
#   ./installer/linux-build.sh --force   跳过校验
#
# 产物: dist/<tool>-<version>-linux.tar.gz
# 用户解压后进入目录运行 ./installer/install-from-source.sh install

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TOOL="$(basename "$REPO_DIR")"
DIST="$REPO_DIR/dist"

FORCE=0
[ "${1:-}" = "--force" ] && FORCE=1

VERSION="$(tr -d '[:space:]' < "$REPO_DIR/VERSION")"
[ -n "$VERSION" ] || { echo "错误: VERSION 文件为空" >&2; exit 1; }

echo "==> 构建 $TOOL $VERSION (Linux)"

cd "$REPO_DIR"
if [ "$FORCE" -eq 0 ] && [ -n "$(git status --porcelain)" ]; then
    echo "错误: 工作区不干净，请先提交（或用 --force 跳过）" >&2
    exit 1
fi

# 组装 payload
STAGE="$DIST/$TOOL-$VERSION"
rm -rf "$STAGE"
mkdir -p "$STAGE"/{bin,module,config,completions,installer}

install -m 755 "$REPO_DIR/bin/$TOOL.sh"                     "$STAGE/bin/$TOOL.sh"
install -m 644 "$REPO_DIR/module/common.sh"                 "$STAGE/module/common.sh"
install -m 644 "$REPO_DIR/config/$TOOL.conf"                "$STAGE/config/$TOOL.conf"
install -m 644 "$REPO_DIR/completions/$TOOL.zsh"            "$STAGE/completions/$TOOL.zsh"
install -m 644 "$REPO_DIR/completions/$TOOL.bash"           "$STAGE/completions/$TOOL.bash"
install -m 755 "$REPO_DIR/installer/install-from-source.sh" "$STAGE/installer/install-from-source.sh"
install -m 644 "$REPO_DIR/VERSION"                          "$STAGE/VERSION"

cat > "$STAGE/README.txt" <<README_EOF
$TOOL $VERSION — Linux 安装说明

1. 解压:
   tar xzf $TOOL-$VERSION-linux.tar.gz
2. 进入目录:
   cd $TOOL-$VERSION
3. 安装:
   ./installer/install-from-source.sh install
4. 安装完成后重开终端，或执行:
   source ~/.bashrc

卸载:
   ./installer/install-from-source.sh uninstall

安装位置: /usr/local/devtools/$TOOL
配置文件: /usr/local/devtools/$TOOL/config/$TOOL.conf
README_EOF

TARBALL="$DIST/$TOOL-$VERSION-linux.tar.gz"
rm -f "$TARBALL"
tar czf "$TARBALL" -C "$DIST" "$TOOL-$VERSION"
rm -rf "$STAGE"

echo "==> 已生成 $TARBALL"
ls -lh "$TARBALL" | awk '{print "    " $9 "  " $5}'
