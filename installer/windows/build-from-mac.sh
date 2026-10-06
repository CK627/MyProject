#!/bin/bash
# 在 macOS 上驱动 Windows 安装包的构建
#
# 流程: 组装 staging → tar → scp 到目标机 → 远程用 Inno Setup 编译 → scp 取回
#
# 用法:
#   ./build-from-mac.sh             正式构建（校验工作区干净且已推送）
#   ./build-from-mac.sh --force     跳过校验（本地测试）
#
# 凭据（二选一，密码不会写进命令行，避免出现在 ps 输出里）:
#   export JTOOL_WIN_PASS='...'
#   或写入 ~/.jtool-win-pass（建议 chmod 600）

set -euo pipefail

TOOL="jtool"
APPID="D1340466-0476-46D6-8B97-5AB23FF83D77"

WIN_HOST="${JTOOL_WIN_HOST:-172.16.100.23}"
WIN_USER="${JTOOL_WIN_USER:-CK}"
PASS_FILE="${JTOOL_WIN_PASS_FILE:-$HOME/.jtool-win-pass}"
REMOTE_DIR="jtool-build"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
DIST="$REPO_DIR/dist"
STAGE="$DIST/.win-stage"
VERSION="$(tr -d '[:space:]' < "$REPO_DIR/VERSION")"
[ -n "$VERSION" ] || { echo "错误: VERSION 文件为空" >&2; exit 1; }

FORCE=0
[ "${1:-}" = "--force" ] && FORCE=1

echo "==> 构建 $TOOL $VERSION (Windows)"
echo "    目标: $WIN_USER@$WIN_HOST"

# ------------------------------------------------------------------
# 凭据
# ------------------------------------------------------------------
WIN_PASS="${JTOOL_WIN_PASS:-}"
if [ -z "$WIN_PASS" ] && [ -f "$PASS_FILE" ]; then
    WIN_PASS="$(cat "$PASS_FILE")"
fi
if [ -z "$WIN_PASS" ]; then
    echo "错误: 未提供 Windows 密码" >&2
    echo "      设置 JTOOL_WIN_PASS 环境变量，或写入 $PASS_FILE" >&2
    exit 1
fi

PASS_TMP="$(mktemp)"
chmod 600 "$PASS_TMP"
printf '%s' "$WIN_PASS" > "$PASS_TMP"
trap 'rm -f "$PASS_TMP"' EXIT

SSH_OPTS=(-o StrictHostKeyChecking=accept-new -o ConnectTimeout=20)
SSH=(sshpass -f "$PASS_TMP" ssh "${SSH_OPTS[@]}" "$WIN_USER@$WIN_HOST")
SCP=(sshpass -f "$PASS_TMP" scp "${SSH_OPTS[@]}")

# ------------------------------------------------------------------
# 校验
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
        exit 1
    fi
fi

# ------------------------------------------------------------------
# 组装 staging
#   src\config\<tool>.conf 里要带上版本号：Windows 的 :cmd_update 靠配置文件里的
#   <TOOL>_VERSION 判断本地版本，缺了它每次 update 都会误判为需要更新。
# ------------------------------------------------------------------
rm -rf "$STAGE"
mkdir -p "$STAGE/src/bin" "$STAGE/src/config" "$STAGE/src/module"

install -m 755 "$REPO_DIR/bin/$TOOL.bat"                     "$STAGE/src/bin/$TOOL.bat"
install -m 755 "$REPO_DIR/installer/windows/install.bat"       "$STAGE/src/module/install.bat"
install -m 644 "$REPO_DIR/VERSION"                           "$STAGE/src/VERSION"
install -m 644 "$REPO_DIR/config/$TOOL.conf"                 "$STAGE/src/config/$TOOL.conf"

TOOL_UPPER="$(echo "$TOOL" | tr 'a-z' 'A-Z')"

# 仓库里的 config 模板带的是 macOS/Linux 默认路径（如 /usr/local/bin），
# 直接发到 Windows 上会让 `jtool list` 找不到任何东西。这里换成 Windows 默认值，
# 安装后的 [Run] 扫描再用实际检测结果覆盖它。
case "$TOOL" in
    ptool) WIN_BASE='C:\' ;;
    jtool) WIN_BASE='C:\Program Files\Java' ;;
    *)     WIN_BASE='C:\' ;;
esac
WIN_BASE="$WIN_BASE" python3 - "$STAGE/src/config/$TOOL.conf" "$TOOL_UPPER" <<'PYEOF'
import os, sys
path, key = sys.argv[1], sys.argv[2] + "_BASE_DIR"
lines = open(path, encoding="utf-8").read().splitlines(True)
out = []
for ln in lines:
    out.append(f'{key}="{os.environ["WIN_BASE"]}"\n' if ln.startswith(key + "=") else ln)
open(path, "w", encoding="utf-8").writelines(out)
PYEOF

printf '%s_VERSION="%s"\n' "$TOOL_UPPER" "$VERSION" >> "$STAGE/src/config/$TOOL.conf"

# 渲染 .iss，并写入 UTF-8 BOM：
# Inno 在脚本文件没有 BOM 时按系统 ANSI 代码页读取，中文注释会被解码坏
printf '\xEF\xBB\xBF' > "$STAGE/$TOOL.iss"
sed -e "s|@TOOL@|$TOOL|g" \
    -e "s|@VERSION@|$VERSION|g" \
    -e "s|@APPID@|$APPID|g" \
    "$SCRIPT_DIR/$TOOL.iss.in" >> "$STAGE/$TOOL.iss"

# 行尾统一成 CRLF
for f in "$STAGE/$TOOL.iss" "$STAGE/src/bin/$TOOL.bat" \
         "$STAGE/src/module/install.bat" "$STAGE/src/config/$TOOL.conf"; do
    perl -pi -e 's/\r?\n/\r\n/' "$f"
done

# build-remote.bat 直接 scp 过去，不经过 staging，单独转一次行尾
perl -pe 's/\r?\n/\r\n/' "$SCRIPT_DIR/build-remote.bat" > "$DIST/.build-remote.bat.crlf"

echo "==> staging 内容"
(cd "$STAGE" && find . -type f | sort | sed 's|^\./|    |')
echo ""

# ------------------------------------------------------------------
# 目标机无法直连 GitHub 的 release CDN，安装器改由本机取好再传过去
# ------------------------------------------------------------------
INNO_VERSION="6.7.3"
INNO_URL="https://github.com/jrsoftware/issrc/releases/download/is-6_7_3/innosetup-${INNO_VERSION}.exe"
IS_CACHE="$DIST/.cache/innosetup-${INNO_VERSION}.exe"

if [ ! -f "$IS_CACHE" ]; then
    mkdir -p "$(dirname "$IS_CACHE")"
    echo "==> 下载 Inno Setup $INNO_VERSION"
    curl -L --fail --silent --show-error -o "$IS_CACHE.part" "$INNO_URL"
    # 校验确实是 PE 可执行文件而不是 HTML 跳转页
    if [ "$(head -c 2 "$IS_CACHE.part")" != "MZ" ]; then
        rm -f "$IS_CACHE.part"
        echo "错误: 下载到的不是可执行文件" >&2
        exit 1
    fi
    mv "$IS_CACHE.part" "$IS_CACHE"
fi

TARBALL="$DIST/.$TOOL-win-src.tar.gz"
rm -f "$TARBALL"
tar czf "$TARBALL" -C "$STAGE" .
echo "==> 已打包 $(basename "$TARBALL") ($(du -h "$TARBALL" | cut -f1))"

# ------------------------------------------------------------------
# 传输 + 远程编译
# ------------------------------------------------------------------
echo "==> 清理远程目录并上传..."
"${SSH[@]}" "if exist $REMOTE_DIR rmdir /s /q $REMOTE_DIR" >/dev/null 2>&1 || true
"${SSH[@]}" "mkdir $REMOTE_DIR" >/dev/null

"${SCP[@]}" "$TARBALL" "$WIN_USER@$WIN_HOST:$REMOTE_DIR/src.tar.gz"
# Inno Setup 在本机下载后传过去（目标机到 GitHub release CDN 的连接会被重置）
"${SCP[@]}" "$IS_CACHE" "$WIN_USER@$WIN_HOST:$REMOTE_DIR/innosetup.exe"
"${SCP[@]}" "$DIST/.build-remote.bat.crlf" "$WIN_USER@$WIN_HOST:$REMOTE_DIR/build-remote.bat"

echo "==> 远程解包并编译（首次会自动安装 Inno Setup，可能需要几分钟）..."
# 用批处理而不是 PowerShell -File：后者要 -ExecutionPolicy Bypass，等于关掉目标机的
# 脚本执行策略这一安全控制。cmd 无此概念，不需要降级任何设置。
"${SSH[@]}" "cd $REMOTE_DIR && tar -xzf src.tar.gz && build-remote.bat $TOOL"

echo "==> 取回产物..."
mkdir -p "$DIST"
"${SCP[@]}" "$WIN_USER@$WIN_HOST:$REMOTE_DIR/$TOOL-setup-$VERSION.exe" "$DIST/"

rm -f "$TARBALL" "$DIST/.build-remote.bat.crlf"
rm -rf "$STAGE"

echo ""
echo "==> 完成"
ls -lh "$DIST/$TOOL-setup-$VERSION.exe" | awk '{print "    " $9 "  " $5}'
