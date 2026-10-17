#!/bin/bash
# encoding: utf-8
# 构建 macOS 安装包（.pkg + .dmg）
#
# 用法:
#   ./build.sh            正式构建，要求工作区干净且 HEAD 已推送
#   ./build.sh --force    跳过上面两项校验（仅供本地测试）
#
# 产物:
#   dist/<tool>-<version>.pkg
#   dist/<tool>-<version>.dmg
#
# 与 ptool / jtool 的打包形态一致（/Library/devtools/<tool>、.dmg 内含 .pkg
# 与安装说明、未签名）。区别只有一处，而且是刻意的：
#
#   **载荷是「源码树」而不是「装好的树」。** 安装布局的唯一实现是
#   installer/deploy.sh（安装、更新、冒烟三处共用同一份），如果这里直接
#   拼一份装好的目录，布局就有了第二个真相来源，迟早对不上。所以 pkg 把
#   源码树落到 /Library/devtools/<tool>-<version>/，postinstall 调 deploy.sh
#   部署到 /Library/devtools/<tool>，然后删掉暂存树。

set -euo pipefail

TOOL="ctfsweep"
IDENTIFIER="com.ck627.ctfsweep"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
DIST="$REPO_DIR/dist"

FORCE=0
[ "${1:-}" = "--force" ] && FORCE=1

VERSION="$(tr -d '[:space:]' < "$REPO_DIR/VERSION")"
[ -n "$VERSION" ] || { echo "错误: VERSION 文件为空" >&2; exit 1; }

echo "==> 构建 $TOOL $VERSION (macOS)"
echo "    仓库: $REPO_DIR"
echo ""

# ------------------------------------------------------------------
# 前置校验
# ------------------------------------------------------------------
cd "$REPO_DIR"
if [ "$FORCE" -eq 0 ]; then
    if [ -n "$(git status --porcelain)" ]; then
        echo "错误: 工作区不干净，请先提交（或用 --force 跳过）" >&2
        git status --short >&2
        exit 1
    fi
    LOCAL_SHA="$(git rev-parse HEAD)"
    REMOTE_SHA="$(git rev-parse "origin/$TOOL" 2>/dev/null || true)"
    if [ -n "$REMOTE_SHA" ] && [ "$LOCAL_SHA" != "$REMOTE_SHA" ]; then
        echo "错误: HEAD (${LOCAL_SHA:0:7}) 与 origin/$TOOL (${REMOTE_SHA:0:7}) 不一致" >&2
        echo "      发布前请先 push（或用 --force 跳过）" >&2
        exit 1
    fi
fi

# ------------------------------------------------------------------
# 组装 payload：源码树，落在 /Library/devtools/<tool>-<version>/
# 清单与 installer/deploy.sh 的 preflight 逐项对齐。
# ------------------------------------------------------------------
PKG_ROOT="$DIST/.pkgroot"
rm -rf "$PKG_ROOT"
STAGE="$PKG_ROOT/$TOOL-$VERSION"
mkdir -p "$STAGE"/{bin,config,completions,installer}

cp -R "$REPO_DIR/$TOOL"    "$STAGE/$TOOL"
cp -R "$REPO_DIR/models"   "$STAGE/models"
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

# 清除扩展属性：install 会把 com.apple.* 一并复制，pkgbuild 则把它们编码成
# ._* AppleDouble 文件塞进 payload（ptool 的 VERSION 就中过招）
xattr -cr "$PKG_ROOT" 2>/dev/null || true
find "$PKG_ROOT" \( -name '.DS_Store' -o -name '._*' \) -delete 2>/dev/null || true

# ------------------------------------------------------------------
# 渲染脚本
# ------------------------------------------------------------------
render() {
    sed -e "s|@TOOL@|$TOOL|g" \
        -e "s|@IDENTIFIER@|$IDENTIFIER|g" \
        -e "s|@VERSION@|$VERSION|g" "$1" > "$2"
}

SCRIPTS_DIR="$DIST/.pkgscripts"
rm -rf "$SCRIPTS_DIR"
mkdir -p "$SCRIPTS_DIR"
render "$SCRIPT_DIR/postinstall.in" "$SCRIPTS_DIR/postinstall"
chmod 755 "$SCRIPTS_DIR/postinstall"

echo "==> payload 结构"
(cd "$PKG_ROOT" && find . -mindepth 1 -maxdepth 3 | sort | sed 's|^\./|    |')
echo ""

# ------------------------------------------------------------------
# 构建 .pkg
# ------------------------------------------------------------------
# --ownership recommended：把 payload 统一记成 root:wheel。
# 默认（preserve）会记下构建者的 uid/gid —— 于是 /Library/devtools 下的文件
# 属于某个普通用户，任何人都能改，系统级安装的意义就没了。ptool 早期没有加
# 这个参数，已一并修正。
COMPONENT="$DIST/.$TOOL-component.pkg"
rm -f "$COMPONENT"
pkgbuild --root "$PKG_ROOT" \
         --identifier "$IDENTIFIER" \
         --version "$VERSION" \
         --scripts "$SCRIPTS_DIR" \
         --install-location "/Library/devtools" \
         --ownership recommended \
         "$COMPONENT"

# 裸的 component package 没有 Distribution 文件，Finder 双击时 Installer
# 渲染不出安装界面；productbuild 会把它包装成带 Distribution 的标准 .pkg。
PKG="$DIST/$TOOL-$VERSION.pkg"
rm -f "$PKG"
render "$SCRIPT_DIR/distribution.xml.in" "$DIST/.distribution.xml"
COMPONENT_DIR="$DIST/.componentdir"
rm -rf "$COMPONENT_DIR"; mkdir -p "$COMPONENT_DIR"
cp "$COMPONENT" "$COMPONENT_DIR/$TOOL-$VERSION.pkg"

productbuild --distribution "$DIST/.distribution.xml" \
             --package-path "$COMPONENT_DIR" \
             "$PKG"

rm -rf "$COMPONENT" "$COMPONENT_DIR" "$DIST/.distribution.xml"

echo "==> 已生成 $PKG"

# ------------------------------------------------------------------
# 构建 .dmg
# ------------------------------------------------------------------
DMG_SRC="$DIST/.dmg-src"
rm -rf "$DMG_SRC"
mkdir -p "$DMG_SRC"
cp "$PKG" "$DMG_SRC/"

cat > "$DMG_SRC/安装说明.txt" <<EOF
$TOOL $VERSION — macOS 安装说明

1. 双击 $TOOL-$VERSION.pkg 开始安装

2. 如果提示「无法打开，因为 Apple 无法检查其是否包含恶意软件」
   —— 这是未签名安装包的正常提示，二选一：
     a) 右键点 .pkg → 打开 → 在弹窗里再点「打开」
     b) 打开「终端」执行：
        sudo installer -pkg "$TOOL-$VERSION.pkg" -target /

3. 安装完成后重开终端，执行 $TOOL --help 验证

安装位置：/Library/devtools/$TOOL
配置文件：/Library/devtools/$TOOL/config/$TOOL.conf
扫描缓存：~/.devtools/$TOOL/cache/（永不自动删除）

卸载：
    sudo /Library/devtools/$TOOL/uninstall

注意：安装程序会往 ~/.zshrc（或 ~/.bashrc）追加成对标记的配置块，
      用于把 $TOOL 加进 PATH；卸载脚本会自动清理。
EOF

DMG="$DIST/$TOOL-$VERSION.dmg"
rm -f "$DMG"
hdiutil create -volname "$TOOL $VERSION" -srcfolder "$DMG_SRC" \
               -ov -format UDZO "$DMG" >/dev/null

echo "==> 已生成 $DMG"

# 清理中间产物；pkg 已打进 dmg，不再单独发布
rm -rf "$PKG_ROOT" "$SCRIPTS_DIR" "$DMG_SRC" "$PKG"

echo ""
echo "==> 完成"
ls -lh "$DMG" | awk '{print "    " $9 "  " $5}'
