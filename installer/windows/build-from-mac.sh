#!/bin/bash
# 在 macOS 上驱动 Windows 安装包（.exe）的构建
#
# 流程: 组装 staging → tar → scp 到目标机 → 远程用 Inno Setup 编译 → scp 取回
#
# 用法:
#   ./installer/windows/build-from-mac.sh            正式构建（校验工作区干净且已推送）
#   ./installer/windows/build-from-mac.sh --force    跳过校验（本地测试）
#
# 目标机: STARTUPCTL_WIN_HOST（默认 ck-win，免密 SSH）
#
# 与 ptool 的同名脚本相比有两点不同，都是本项目形态决定的：
#   1. **用户级布局**：装到 {%USERPROFILE}\.devtools\startupctl、PATH 走 HKCU，
#      不提权。ptool 是机器级（HKLM + shims）。
#   2. **不强依赖本机下载 Inno Setup**：先从目标机探一次 ISCC，装了就直接用。
#      ptool 每次都在本机下 10MB 的 innosetup.exe 再传过去——而目标机通常早就装好了，
#      本机到 GitHub release CDN 又常常很慢（实测 120 秒只下到 6/10.5 MB）。
#      只有目标机确实没有 ISCC 时才走下载那条路。
set -euo pipefail

TOOL="startupctl"
APPID="7E3A9C41-5B62-4D18-9F03-2A8C6B1D4E70"

WIN_HOST="${STARTUPCTL_WIN_HOST:-ck-win}"
REMOTE_DIR="startupctl-build"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
DIST="$REPO_DIR/dist"
STAGE="$DIST/.win-stage"
VERSION="$(tr -d '[:space:]' < "$REPO_DIR/VERSION")"
[ -n "$VERSION" ] || { echo "错误: VERSION 文件为空" >&2; exit 1; }

FORCE=0
[ "${1:-}" = "--force" ] && FORCE=1

echo "==> 构建 $TOOL $VERSION (Windows)"
echo "    目标: $WIN_HOST"

SSH_OPTS=(-o StrictHostKeyChecking=accept-new -o ConnectTimeout=20)
if ! ssh -o BatchMode=yes "${SSH_OPTS[@]}" "$WIN_HOST" "exit 0" >/dev/null 2>&1; then
    echo "错误: 无法免密登录 $WIN_HOST" >&2
    echo "      配一次即可: ssh-copy-id $WIN_HOST" >&2
    exit 1
fi
SSH=(ssh "${SSH_OPTS[@]}" "$WIN_HOST")
SCP=(scp "${SSH_OPTS[@]}")

# ------------------------------------------------------------------
# 校验：发出去的必须是已提交、已推送的代码
# ------------------------------------------------------------------
cd "$REPO_DIR"
if [ "$FORCE" -eq 0 ]; then
    # 「工作区干净」只有在本项目自己的仓库根上才有意义。本项目可能寄居在
    # MyProject 的 monorepo 工作树里（StartupItemManagement/ 在 main 上被忽略），
    # 那时 `git status` 看到的是**别的项目的**未跟踪目录——检查会永远失败，
    # 而且报出来的东西与本次构建毫无关系。宁可明确拒绝，也不要让 --force 变成常态。
    TOPLEVEL="$(git rev-parse --show-toplevel 2>/dev/null || true)"
    # 比字符串会在 macOS 上误判：/tmp 是指向 /private/tmp 的软链，
    # git 给的是解析后的物理路径。两边都取 pwd -P 再比。
    REPO_REAL="$(cd "$REPO_DIR" && pwd -P)"
    TOP_REAL="$(cd "$TOPLEVEL" 2>/dev/null && pwd -P || true)"
    if [ "$TOP_REAL" != "$REPO_REAL" ]; then
        echo "错误: 当前仓库顶层是 '${TOPLEVEL:-<不在 git 仓库里>}'，不是 $REPO_DIR" >&2
        echo "      这里的工作区检查看的是别的项目，结果无意义。" >&2
        echo "      请在本项目分支的独立克隆/工作树里构建，或加 --force。" >&2
        exit 1
    fi
    if [ -n "$(git status --porcelain)" ]; then
        echo "错误: 工作区不干净，请先提交（或用 --force 跳过）" >&2
        git status --short >&2
        exit 1
    fi
fi

# ------------------------------------------------------------------
# 组装 staging —— **必须与 Python 侧 _PAYLOAD_WIN 逐项一致**
#   src\lib\<tool>\         Python 包
#   src\bin\<tool>.bat      启动器
#   src\config\<tool>.conf  配置
#   src\VERSION
# ------------------------------------------------------------------
rm -rf "$STAGE"
mkdir -p "$STAGE/src/bin" "$STAGE/src/config" "$STAGE/src/lib"

# 只拷包本体，不要 __pycache__ / .DS_Store（装到用户目录里全是垃圾）
cp -R "$REPO_DIR/$TOOL" "$STAGE/src/lib/$TOOL"
find "$STAGE/src/lib" \( -name '__pycache__' -o -name '.DS_Store' -o -name '*.pyc' \) \
    -exec rm -rf {} + 2>/dev/null || true

install -m 644 "$REPO_DIR/VERSION"               "$STAGE/src/VERSION"
install -m 644 "$REPO_DIR/config/$TOOL.conf"     "$STAGE/src/config/$TOOL.conf"

# 启动器从 **Python 侧那份常量** 生成，保证 exe 装的与 install.ps1 装的一字不差。
# 手抄一份到 staging 就是两个真相来源，迟早对不上（比如改了 PYTHONPATH 的拼法）。
PYTHONPATH="$REPO_DIR" python3 - "$STAGE/src/bin/$TOOL.bat" <<'PYEOF'
import sys
from startupctl.core.selfmgr import _WIN_LAUNCHER
with open(sys.argv[1], 'w', encoding='ascii', newline='') as fh:
    fh.write(_WIN_LAUNCHER)
PYEOF
[ -s "$STAGE/src/bin/$TOOL.bat" ] || { echo "错误: 启动器没生成出来" >&2; exit 1; }

# 渲染 .iss，并写入 UTF-8 BOM：
# Inno 在脚本文件没有 BOM 时按系统 ANSI 代码页读取，中文注释会被解码坏
printf '\xEF\xBB\xBF' > "$STAGE/$TOOL.iss"
sed -e "s|@TOOL@|$TOOL|g" -e "s|@VERSION@|$VERSION|g" -e "s|@APPID@|$APPID|g" \
    "$SCRIPT_DIR/$TOOL.iss.in" >> "$STAGE/$TOOL.iss"

# 行尾统一 CRLF（.iss 与 .bat 都是 Windows 侧读的）
for f in "$STAGE/$TOOL.iss" "$STAGE/src/bin/$TOOL.bat"; do
    perl -pi -e 's/\r?\n/\r\n/' "$f"
done
perl -pe 's/\r?\n/\r\n/' "$SCRIPT_DIR/build-remote.bat" > "$DIST/.build-remote.bat.crlf"

echo "==> staging 内容"
(cd "$STAGE" && find . -type f | sort | sed 's|^\./|    |')
echo ""

# ------------------------------------------------------------------
# Inno Setup：先问目标机有没有，没有才在本机下好传过去
# ------------------------------------------------------------------
NEED_INNO=0
if "${SSH[@]}" 'if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" (exit 0) else (exit 1)' >/dev/null 2>&1 \
   || "${SSH[@]}" 'if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" (exit 0) else (exit 1)' >/dev/null 2>&1; then
    echo "==> 目标机已有 Inno Setup，跳过下载"
else
    NEED_INNO=1
    echo "==> 目标机没有 Inno Setup，在本机下好再传过去"
fi

TARBALL="$DIST/.$TOOL-win-src.tar.gz"
rm -f "$TARBALL"
tar czf "$TARBALL" -C "$STAGE" .
echo "==> 已打包 $(basename "$TARBALL") ($(du -h "$TARBALL" | cut -f1))"

if [ "$NEED_INNO" -eq 1 ]; then
    INNO_VERSION="6.7.3"
    INNO_URL="https://github.com/jrsoftware/issrc/releases/download/is-6_7_3/innosetup-${INNO_VERSION}.exe"
    IS_CACHE="$DIST/.cache/innosetup-${INNO_VERSION}.exe"
    if [ ! -f "$IS_CACHE" ]; then
        mkdir -p "$(dirname "$IS_CACHE")"
        echo "==> 下载 Inno Setup ${INNO_VERSION}（可能要几分钟）"
        curl -L --fail --silent --show-error --retry 3 --max-time 900 \
             -o "$IS_CACHE.part" "$INNO_URL"
        # 校验确实是 PE 可执行文件而不是 HTML 跳转页
        if [ "$(head -c 2 "$IS_CACHE.part")" != "MZ" ]; then
            rm -f "$IS_CACHE.part"
            echo "错误: 下载到的不是可执行文件" >&2
            exit 1
        fi
        mv "$IS_CACHE.part" "$IS_CACHE"
    fi
fi

# ------------------------------------------------------------------
# 传输 + 远程编译
# ------------------------------------------------------------------
echo "==> 清理远程目录并上传..."
"${SSH[@]}" "if exist $REMOTE_DIR rmdir /s /q $REMOTE_DIR" >/dev/null 2>&1 || true
"${SSH[@]}" "mkdir $REMOTE_DIR" >/dev/null

"${SCP[@]}" "$TARBALL" "$WIN_HOST:$REMOTE_DIR/src.tar.gz"
"${SCP[@]}" "$DIST/.build-remote.bat.crlf" "$WIN_HOST:$REMOTE_DIR/build-remote.bat"
if [ "$NEED_INNO" -eq 1 ]; then
    "${SCP[@]}" "$IS_CACHE" "$WIN_HOST:$REMOTE_DIR/innosetup.exe"
fi

echo "==> 远程解包并编译..."
"${SSH[@]}" "cd $REMOTE_DIR && tar -xzf src.tar.gz && build-remote.bat $TOOL"

echo "==> 取回产物..."
mkdir -p "$DIST"
"${SCP[@]}" "$WIN_HOST:$REMOTE_DIR/$TOOL-setup-$VERSION.exe" "$DIST/"

rm -f "$TARBALL" "$DIST/.build-remote.bat.crlf"
rm -rf "$STAGE"

echo ""
echo "==> 完成"
ls -lh "$DIST/$TOOL-setup-$VERSION.exe" | awk '{print "    " $9 "  " $5}'
