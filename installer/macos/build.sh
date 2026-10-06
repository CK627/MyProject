#!/bin/bash
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
# 说明: 安装包未签名。本机构建的包没有 quarantine 属性、可直接双击安装；
#       从网上下载的包会带 com.apple.quarantine，需要右键「打开」或
#       sudo installer -pkg ... -target /

set -euo pipefail

TOOL="ptool"
TOOL_UPPER="PTOOL"
IDENTIFIER="com.ck627.ptool"

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
# 组装 payload
# 注意: 不包含 config/ —— pkgbuild 的 BOM 是权威的，升级时会无条件覆盖
#       payload 里的每个文件，配置必须留给 postinstall 按需创建。
#       模板放在 share/ 下，随包刷新。
# ------------------------------------------------------------------
PKG_ROOT="$DIST/.pkgroot"
rm -rf "$PKG_ROOT"
mkdir -p "$PKG_ROOT"/{bin,lib,module,completions,share}

install -m 755 "$REPO_DIR/bin/$TOOL.sh"            "$PKG_ROOT/lib/$TOOL.sh"
install -m 644 "$REPO_DIR/module/common.sh"        "$PKG_ROOT/module/common.sh"
install -m 644 "$REPO_DIR/completions/$TOOL.zsh"   "$PKG_ROOT/completions/$TOOL.zsh"
install -m 644 "$REPO_DIR/completions/$TOOL.bash"  "$PKG_ROOT/completions/$TOOL.bash"
install -m 644 "$REPO_DIR/config/$TOOL.conf"       "$PKG_ROOT/share/$TOOL.conf.template"
install -m 644 "$REPO_DIR/VERSION"                 "$PKG_ROOT/VERSION"

# bin/ 里只放无后缀入口，且必须是相对软链接：
# 这样在 payload 内部和装到 / 之后解析结果一致
ln -s "../lib/$TOOL.sh" "$PKG_ROOT/bin/$TOOL"

# 清除扩展属性：源文件上可能带 com.apple.lastuseddate 之类，install 会一并复制，
# pkgbuild 则把它们编码成 ._* AppleDouble 文件塞进 payload（实测 VERSION 就会中招）
xattr -cr "$PKG_ROOT" 2>/dev/null || true
find "$PKG_ROOT" \( -name '.DS_Store' -o -name '._*' \) -delete 2>/dev/null || true

# ------------------------------------------------------------------
# 渲染脚本
# ------------------------------------------------------------------
render() {
    sed -e "s|@TOOL_UPPER@|$TOOL_UPPER|g" \
        -e "s|@TOOL@|$TOOL|g" \
        -e "s|@IDENTIFIER@|$IDENTIFIER|g" \
        -e "s|@VERSION@|$VERSION|g" "$1" > "$2"
}

SCRIPTS_DIR="$DIST/.pkgscripts"
rm -rf "$SCRIPTS_DIR"
mkdir -p "$SCRIPTS_DIR"
render "$SCRIPT_DIR/postinstall.in" "$SCRIPTS_DIR/postinstall"
chmod 755 "$SCRIPTS_DIR/postinstall"

render "$SCRIPT_DIR/uninstall.in" "$PKG_ROOT/uninstall"
chmod 755 "$PKG_ROOT/uninstall"

echo "==> payload 结构"
(cd "$PKG_ROOT" && find . -mindepth 1 | sort | sed 's|^\./|    |')
echo ""

# ------------------------------------------------------------------
# 构建 .pkg
# ------------------------------------------------------------------
# 第一步: 由 payload 生成 component package
COMPONENT="$DIST/.$TOOL-component.pkg"
rm -f "$COMPONENT"
pkgbuild --root "$PKG_ROOT" \
         --identifier "$IDENTIFIER" \
         --version "$VERSION" \
         --scripts "$SCRIPTS_DIR" \
         --install-location "/Library/devtools/$TOOL" \
         "$COMPONENT"

# 第二步: 包成 product archive。
# 裸的 component package 没有 Distribution 文件，Finder 双击时 Installer
# 渲染不出安装界面；productbuild 会把它包装成带 Distribution 的标准 .pkg。
PKG="$DIST/$TOOL-$VERSION.pkg"
rm -f "$PKG"
render "$SCRIPT_DIR/distribution.xml.in" "$DIST/.distribution.xml"
# component package 与 Distribution 里的 # 引用必须同名同目录，先摆好
COMPONENT_DIR="$DIST/.componentdir"
rm -rf "$COMPONENT_DIR"; mkdir -p "$COMPONENT_DIR"
cp "$COMPONENT" "$COMPONENT_DIR/$TOOL-$VERSION.pkg"

productbuild --distribution "$DIST/.distribution.xml" \
             --package-path "$COMPONENT_DIR" \
             "$PKG"

rm -rf "$COMPONENT" "$COMPONENT_DIR" "$DIST/.distribution.xml"

echo "==> 已生成 $PKG"

# ------------------------------------------------------------------
# 构建 .dmg（把 .pkg 和安装说明装进去）
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

3. 安装完成后重开终端，执行 $TOOL help 验证

安装位置：/Library/devtools/$TOOL
配置文件：/Library/devtools/$TOOL/config/$TOOL.conf

卸载：
    sudo /Library/devtools/$TOOL/uninstall

注意：安装程序会往 ~/.zshrc（或 ~/.bashrc）追加三行，用于把 $TOOL
      加进 PATH 并加载 Tab 补全。卸载脚本会自动清理这三行。
EOF

DMG="$DIST/$TOOL-$VERSION.dmg"
rm -f "$DMG"
hdiutil create -volname "$TOOL $VERSION" -srcfolder "$DMG_SRC" \
               -ov -format UDZO "$DMG" >/dev/null

echo "==> 已生成 $DMG"

# 清理中间产物
rm -rf "$PKG_ROOT" "$SCRIPTS_DIR" "$DMG_SRC"

echo ""
echo "==> 完成"
ls -lh "$PKG" "$DMG" | awk '{print "    " $9 "  " $5}'
