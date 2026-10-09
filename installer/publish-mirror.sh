#!/bin/bash
# 把发布产物推到国内镜像服务器（httpd 已在跑，无需 VPN 可直连）
#
# 用法:
#   ./installer/publish-mirror.sh             上传 dist/ 里已有的产物
#   ./installer/publish-mirror.sh --force     跳过「工作区必须干净」检查
#   MIRROR_HOST=ck ./installer/publish-mirror.sh
#
# 镜像布局（install.sh / install.ps1 / update 都按这个布局读）:
#   <root>/<tool>/VERSION                       纯文本最新版本号
#   <root>/<tool>/install.sh                    一键安装脚本（macOS / Linux）
#   <root>/<tool>/install.ps1                   一键安装脚本（Windows）
#   <root>/<tool>/<version>/<asset>             该版本的发布产物
#   <root>/<tool>/<version>/<tool>-<version>-src.tar.gz   update 用的源码包
#
# 两个容易踩的点：
#   1. 源码包的顶层目录必须是 MyProject-<branch>，与 GitHub archive 一致 ——
#      update 里写死了 src="$tmp/MyProject-$branch"，名字对不上就取不到文件。
#   2. scp 成功不代表能下载：httpd 的目录权限没配对时是 403，退出码里看不出来，
#      所以脚本最后会真的 curl 一次。

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TOOL="$(basename "$REPO_DIR")"
DIST="$REPO_DIR/dist"

MIRROR_HOST="${MIRROR_HOST:-ck}"
MIRROR_ROOT="${MIRROR_ROOT:-/var/www/html/dist}"
MIRROR_URL="${MIRROR_URL:-http://101.132.165.98/dist}"

FORCE=0
[ "${1:-}" = "--force" ] && FORCE=1

VERSION="$(tr -d '[:space:]' < "$REPO_DIR/VERSION")"
[ -n "$VERSION" ] || { echo "错误: VERSION 文件为空" >&2; exit 1; }

cd "$REPO_DIR"
if [ "$FORCE" -eq 0 ] && [ -n "$(git status --porcelain)" ]; then
    echo "错误: 工作区不干净，请先提交（或用 --force 跳过）" >&2
    echo "      未提交的代码推上去，会让镜像与 tag 对不上" >&2
    exit 1
fi

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
REMOTE_DIR="$MIRROR_ROOT/$TOOL/$VERSION"

echo "==> 发布 $TOOL $VERSION -> $MIRROR_HOST:$REMOTE_DIR"

ssh "$MIRROR_HOST" "mkdir -p '$REMOTE_DIR'"

# update 用的源码包。用 git archive 而不是手工拷贝，保证与 GitHub archive 同源。
SRC_TARBALL="$DIST/$TOOL-$VERSION-src.tar.gz"
git archive --prefix="MyProject-$BRANCH/" -o "$SRC_TARBALL" HEAD
echo "==> 已生成源码包 $(basename "$SRC_TARBALL")"

# 三种平台的包不一定都在本机（dmg 在 mac 上打、exe 在 Windows 上打），缺哪个就
# 跳过哪个，但一定要说出来 —— 静默跳过会让镜像悄悄缺一个平台。
uploaded=0
missing=0
for asset in \
    "$TOOL-$VERSION.dmg" \
    "$TOOL-$VERSION-linux.tar.gz" \
    "$TOOL-setup-$VERSION.exe"
do
    if [ -f "$DIST/$asset" ]; then
        scp -q "$DIST/$asset" "$MIRROR_HOST:$REMOTE_DIR/$asset"
        echo "    + $asset"
        uploaded=$((uploaded + 1))
    else
        # 用 ${asset} 而不是 ${asset}：macOS 自带的 bash 3.2 会把紧跟其后的全角括号
        # 算进变量名（${asset}（ -> 变量名「asset（」），set -u 下直接退出。
        echo "    - 跳过 ${asset}（dist/ 里没有，本机未构建该平台）"
        missing=$((missing + 1))
    fi
done

scp -q "$SRC_TARBALL" "$MIRROR_HOST:$REMOTE_DIR/"
echo "    + $(basename "$SRC_TARBALL")"

# VERSION 与安装脚本放在镜像根：用户的一键安装命令直接 curl 它们。
# 同时发一份 VERSION.txt：httpd 对无扩展名的文件返回 application/octet-stream，
# PowerShell 的 Invoke-WebRequest 就把它当 byte[] 而不是字符串，install.ps1 里
# 再怎么 Trim 都拿不到版本号。带 .txt 后缀才是 text/plain。两者内容一致，
# curl 那侧（install.sh / update）读哪个都行。
printf '%s\n' "$VERSION" > "$DIST/VERSION.mirror"
scp -q "$DIST/VERSION.mirror" "$MIRROR_HOST:$MIRROR_ROOT/$TOOL/VERSION"
scp -q "$DIST/VERSION.mirror" "$MIRROR_HOST:$MIRROR_ROOT/$TOOL/VERSION.txt"
rm -f "$DIST/VERSION.mirror"
scp -q "$REPO_DIR/installer/install.sh"  "$MIRROR_HOST:$MIRROR_ROOT/$TOOL/install.sh"
scp -q "$REPO_DIR/installer/install.ps1" "$MIRROR_HOST:$MIRROR_ROOT/$TOOL/install.ps1"
echo "    + VERSION install.sh install.ps1"

# httpd 以 apache 用户读文件，root 建的目录默认权限可能挡住它
ssh "$MIRROR_HOST" "chmod -R a+rX '$MIRROR_ROOT/$TOOL'"

echo "==> 上传完成：${uploaded} 个平台包 + 源码包，跳过 ${missing} 个"

# 真下载一次：403/404 不会体现在 scp 的退出码里，只有 HTTP 能暴露
echo "==> 校验"
code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 10 "$MIRROR_URL/$TOOL/VERSION" || echo 000)"
echo "    VERSION    -> HTTP $code"
if [ "$code" != "200" ]; then
    echo "错误: 镜像自检失败（HTTP ${code}），检查 httpd 配置与目录权限" >&2
    exit 1
fi
echo "    $(curl -sS --max-time 10 "$MIRROR_URL/$TOOL/VERSION")"
echo "==> 一键安装（国内）:"
echo "    source <(curl -fsSL $MIRROR_URL/$TOOL/install.sh)"
