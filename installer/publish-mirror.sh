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
#   <root>/startupctl/startupctl-src.tar.gz      源码快照（顶层目录 MyProject-<branch>，与 GitHub archive 一致）
#   <root>/startupctl/VERSION                    远端版本号（startupctl update 的第一步就是读它；
#                                              不发这一份，update 会直接 404 报「无法获取远端版本号」）
#   <root>/startupctl/VERSION.txt                同一份版本号，带扩展名——httpd 把无扩展名文件
#                                              当 application/octet-stream 发，PowerShell 的
#                                              Invoke-WebRequest 会拿到 byte[] 而不是字符串
#   <root>/startupctl/<ver>/                     每次发布的**版本化目录**（与 jtool/ptool 同规）
#       <tool>-<ver>-src.tar.gz                  该版本的源码快照
#       <tool>-setup-<ver>.exe                   Windows 安装包（Inno Setup）——没有就跳过并**明说**
#
# 版本化目录里的 exe 由 installer/windows/build-from-mac.sh 产出后再跑本脚本；
# 本脚本不负责编译，只负责发布（编译要一台 Windows 与 Inno Setup）。
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

# ★ 必须在本项目自己的仓库根上发布。
#   `git archive HEAD` 只认「当前仓库」，而本项目目前可能寄居在 MyProject 的
#   monorepo 工作树里（StartupItemManagement/ 在 main 上是 gitignored 的）。
#   那种情况下 HEAD 指向的是 **main**，打出来的快照会是整个作品集、而不是本项目，
#   而且自检（只验 HTTP 200 与 VERSION 一致）照样全绿——静默发错内容，最难发现。
TOPLEVEL="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [ "$TOPLEVEL" != "$REPO_DIR" ]; then
    echo "错误: 当前仓库顶层是 '${TOPLEVEL:-<不在 git 仓库里>}'，不是 $REPO_DIR" >&2
    echo "      在这里发布会把另一个仓库的树打成快照。" >&2
    echo "      请在本项目分支的独立克隆/工作树里执行，例如：" >&2
    echo "        git worktree add /tmp/$TOOL-wt $(basename "$REPO_DIR")" >&2
    exit 1
fi

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
# VERSION.txt 是同一份内容的带扩展名副本：httpd 对无扩展名文件发
# application/octet-stream，PowerShell 的 Invoke-WebRequest 会把它当 byte[]（ptool 踩过）
scp -q "$REPO_DIR/VERSION" "$MIRROR_HOST:$MIRROR_ROOT/$TOOL/VERSION.txt"
echo "    + VERSION ($(tr -d '\n' < "$REPO_DIR/VERSION")) + VERSION.txt"

# ---- 版本化目录：与 jtool / ptool 同规的「每次发布一个目录」----
VER="$(tr -d '[:space:]' < "$REPO_DIR/VERSION")"
ssh "$MIRROR_HOST" "mkdir -p '$MIRROR_ROOT/$TOOL/$VER'"
scp -q "$TMP/startupctl-src.tar.gz" "$MIRROR_HOST:$MIRROR_ROOT/$TOOL/$VER/${TOOL}-${VER}-src.tar.gz"
EXE="$REPO_DIR/dist/${TOOL}-setup-${VER}.exe"
if [ -f "$EXE" ]; then
    scp -q "$EXE" "$MIRROR_HOST:$MIRROR_ROOT/$TOOL/$VER/"
    echo "    + $VER/${TOOL}-${VER}-src.tar.gz ${TOOL}-setup-${VER}.exe"
else
    # 不静默跳过：缺 exe 是发布内容不完整，必须让人看见（与 ptool 的 publish-mirror 同规矩）
    echo "    + $VER/${TOOL}-${VER}-src.tar.gz"
    echo "    - 跳过 ${TOOL}-setup-${VER}.exe（dist/ 里没有；先跑 installer/windows/build-from-mac.sh）"
fi

# httpd 以 apache 用户读文件，root 建的目录默认权限可能挡住它
ssh "$MIRROR_HOST" "chmod -R a+rX '$MIRROR_ROOT/$TOOL'"

# 真下载一次：403/404 不会体现在 scp 的退出码里，只有 HTTP 能暴露
echo "==> 校验"
for f in install.sh install.ps1 startupctl-src.tar.gz VERSION VERSION.txt; do
    code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 10 "$MIRROR_URL/$TOOL/$f" || echo 000)"
    echo "    $f -> HTTP $code"
    if [ "$code" != "200" ]; then
        echo "错误: 镜像自检失败（HTTP ${code}），检查 httpd 配置与目录权限" >&2
        exit 1
    fi
done
# 版本化目录里的产物单独校验一遍（exe 有才验）
for f in "$VER/${TOOL}-${VER}-src.tar.gz" "$VER/${TOOL}-setup-${VER}.exe"; do
    [ -f "$REPO_DIR/dist/$(basename "$f")" ] || [ "${f##*/}" = "${TOOL}-setup-${VER}.exe" ] || continue
    if [ "${f##*/}" = "${TOOL}-setup-${VER}.exe" ] && [ ! -f "$EXE" ]; then continue; fi
    code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 10 "$MIRROR_URL/$TOOL/$f" || echo 000)"
    echo "    $f -> HTTP $code"
    if [ "$code" != "200" ]; then
        echo "错误: 镜像自检失败（HTTP ${code}）" >&2
        exit 1
    fi
done
echo "==> 一键安装（国内）:"
echo "    source <(curl -fsSL $MIRROR_URL/$TOOL/install.sh)"
echo "==> Windows 安装包:"
if [ -f "$EXE" ]; then
    echo "    $MIRROR_URL/$TOOL/$VER/${TOOL}-setup-${VER}.exe"
else
    echo "    （本次未发布 exe）"
fi
