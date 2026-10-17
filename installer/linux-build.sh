#!/bin/bash
# encoding: utf-8
# 构建 Linux 安装包（.tar.gz，通用格式）
#
# 用法:
#   ./installer/linux-build.sh           正式构建
#   ./installer/linux-build.sh --force   跳过校验
#
# 产物: dist/startupctl-<version>-linux.tar.gz
# 用户解压后进入目录运行 ./installer/install-from-source.sh install
#
# 与 ptool / jtool 的同名脚本同规矩：只装「可安装的那一 subset」，不带 tests/、
# 不带 dist/。区别在于本项目的载荷是 Python 包，而 ptool 是 shell 模块。

set -euo pipefail

TOOL="startupctl"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
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

# ------------------------------------------------------------------
# 组装 payload —— 必须与 installer/deploy.sh 的 preflight 清单逐项对齐，
# 少一项 deploy.sh 就会在安装时中止（它是先检查完再动手的）。
# ------------------------------------------------------------------
STAGE="$DIST/$TOOL-$VERSION"
rm -rf "$STAGE"
mkdir -p "$STAGE"/{bin,config,completions,installer}

cp -R "$REPO_DIR/$TOOL" "$STAGE/$TOOL"
find "$STAGE" \( -name '__pycache__' -o -name '.DS_Store' -o -name '*.pyc' \) \
    -exec rm -rf {} + 2>/dev/null || true

install -m 755 "$REPO_DIR/bin/$TOOL.sh"                        "$STAGE/bin/$TOOL.sh"
install -m 644 "$REPO_DIR/config/$TOOL.conf"                   "$STAGE/config/$TOOL.conf"
install -m 644 "$REPO_DIR/completions/$TOOL.zsh"               "$STAGE/completions/$TOOL.zsh"
install -m 644 "$REPO_DIR/completions/$TOOL.bash"              "$STAGE/completions/$TOOL.bash"
install -m 755 "$REPO_DIR/installer/install-from-source.sh"    "$STAGE/installer/install-from-source.sh"
install -m 755 "$REPO_DIR/installer/deploy.sh"                 "$STAGE/installer/deploy.sh"
install -m 755 "$REPO_DIR/installer/shell-setup.sh"            "$STAGE/installer/shell-setup.sh"
install -m 755 "$REPO_DIR/installer/uninstall.sh"              "$STAGE/installer/uninstall.sh"
install -m 644 "$REPO_DIR/VERSION"                             "$STAGE/VERSION"

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
用户级安装（无需 root）: STARTUPCTL_USER=1 ./installer/install-from-source.sh install

数据目录（永不自动删除）: ~/.devtools/$TOOL
  whitelist.json   白名单（安全产物）
  backups/         备份（restore 的唯一来源）
  scans/           扫描快照（纯缓存，clear 只清这里）
README_EOF

TARBALL="$DIST/$TOOL-$VERSION-linux.tar.gz"
rm -f "$TARBALL"
tar czf "$TARBALL" -C "$DIST" "$TOOL-$VERSION"
rm -rf "$STAGE"

echo "==> 已生成 $TARBALL"
ls -lh "$TARBALL" | awk '{print "    " $9 "  " $5}'
