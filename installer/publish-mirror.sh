#!/bin/bash
# 把源码快照与一键安装脚本发布到国内镜像服务器（httpd 已在跑，无需 VPN 可直连）
#
# 用法:
#   ./installer/publish-mirror.sh             发布当前分支快照（要求工作区干净）
#   ./installer/publish-mirror.sh --force     跳过「工作区必须干净」检查
#   MIRROR_HOST=ck ./installer/publish-mirror.sh
#
# 镜像布局（installer/install.sh 引导模式 与 startupctl update 都按这个布局读）:
#   <root>/startupctl/install.sh                 一键安装脚本（macOS / Linux）
#   <root>/startupctl/install.ps1                一键安装脚本（Windows，irm … | iex）
#   <root>/startupctl/startupctl-src.tar.gz        源码快照（顶层目录 MyProject-<branch>，与 GitHub archive 一致）
#   <root>/startupctl/VERSION                    远端版本号（startupctl update 的第一步就是读它；
#                                              不发这一份，update 会直接 404 报「无法获取远端版本号」）
#
# ⚠️ 两份东西必须同版本发布：VERSION 先更新、tarball 后到，中间的窗口里 update 会读到
#    新版本号却下到旧快照 —— startupctl 侧有「快照 VERSION 必须等于远端 VERSION」的校验兜底，
#    不落盘。所以这里 VERSION **最后**发（见下方顺序）。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TOOL="startupctl"
MIRROR_HOST="${MIRROR_HOST:-ck}"
MIRROR_ROOT="${MIRROR_ROOT:-/var/www/html/dist}"
MIRROR_URL="${MIRROR_URL:-http://101.132.165.98/dist}"

FORCE=0
[ "${1:-}" = "--force" ] && FORCE=1

cd "$REPO_DIR"
if [ "$FORCE" -eq 0 ] && [ -n "$(git status --porcelain)" ]; then
    echo "错误: 工作区不干净，请先提交（或用 --force 跳过）" >&2
    echo "      未提交的代码发到镜像上，会与分支对不上" >&2
    exit 1
fi

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# 用 git archive 而不是手工拷贝，保证与 GitHub archive 同源（顶层目录名前缀一致）
git archive --prefix="MyProject-$BRANCH/" -o "$TMP/startupctl-src.tar.gz" HEAD

echo "==> 发布 ${TOOL}（分支 ${BRANCH}）-> $MIRROR_HOST:$MIRROR_ROOT/$TOOL"
ssh "$MIRROR_HOST" "mkdir -p '$MIRROR_ROOT/$TOOL'"
scp -q "$TMP/startupctl-src.tar.gz" "$MIRROR_HOST:$MIRROR_ROOT/$TOOL/"
scp -q "$REPO_DIR/installer/install.sh" "$MIRROR_HOST:$MIRROR_ROOT/$TOOL/install.sh"
scp -q "$REPO_DIR/installer/install.ps1" "$MIRROR_HOST:$MIRROR_ROOT/$TOOL/install.ps1"
echo "    + startupctl-src.tar.gz install.sh install.ps1"
# VERSION 最后发：它是 update 的入口信号，先发的话会有一段「版本号是新的、快照还是旧的」
# 窗口（startupctl 侧虽有校验兜底不落盘，但白跑一趟）
scp -q "$REPO_DIR/VERSION" "$MIRROR_HOST:$MIRROR_ROOT/$TOOL/VERSION"
echo "    + VERSION ($(tr -d '\n' < "$REPO_DIR/VERSION"))"

# httpd 以 apache 用户读文件，root 建的目录默认权限可能挡住它
ssh "$MIRROR_HOST" "chmod -R a+rX '$MIRROR_ROOT/$TOOL'"

# 真下载一次：403/404 不会体现在 scp 的退出码里，只有 HTTP 能暴露
echo "==> 校验"
for f in install.sh install.ps1 startupctl-src.tar.gz VERSION; do
    code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 10 "$MIRROR_URL/$TOOL/$f" || echo 000)"
    echo "    $f -> HTTP $code"
    if [ "$code" != "200" ]; then
        echo "错误: 镜像自检失败（HTTP ${code}），检查 httpd 配置与目录权限" >&2
        exit 1
    fi
done
echo "==> 一键安装（国内）:"
echo "    source <(curl -fsSL $MIRROR_URL/$TOOL/install.sh)"
