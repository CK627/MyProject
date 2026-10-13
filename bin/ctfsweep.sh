#!/usr/bin/env bash
# ctfsweep 启动器（macOS / Linux）
# 解析软链接定位自身目录，再交给 python3 执行（-c 引导，避免 cwd 遮蔽安装版）。
# 本文件是**素材**，不进 PATH：安装时被复制成 <安装根>/lib/ctfsweep.sh，
# 由 <安装根>/bin/ctfsweep（无后缀软链）指过来。bin/ 在 PATH 上，若把 .sh 也
# 放在那里，命令名补全就会同时列出 ctfsweep 和 ctfsweep.sh（Windows 的 .bat 同理）。
# 兼容两种布局：
#   仓库检出   <root>/bin/ctfsweep.sh + <root>/ctfsweep/     → PYTHONPATH=<root>
#   devtools   <root>/bin/ctfsweep（软链）→ <root>/lib/ctfsweep.sh
#              + <root>/lib/ctfsweep/                        → PYTHONPATH=<root>/lib
set -euo pipefail

src="${BASH_SOURCE[0]}"
while [ -L "$src" ]; do
    dir="$(cd "$(dirname "$src")" && pwd)"
    src="$(readlink "$src")"
    [[ "$src" != /* ]] && src="$dir/$src"
done
root="$(cd "$(dirname "$src")/.." && pwd)"

if [ -d "$root/lib/ctfsweep" ]; then
    pyroot="$root/lib"
else
    pyroot="$root"
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "ctfsweep: 未找到 python3（需要 Python 3.8+）" >&2
    exit 127
fi

# 用 -c 而不是 -m：-m / -c 都会把 cwd 放进 sys.path[0]，在源码目录里调用
# 安装版时，cwd 里的 ctfsweep/ 包会把 PYTHONPATH 指向的安装版遮蔽掉。
# 这里先把 cwd 从 sys.path 移除，保证「装的是哪份就跑哪份」。
exec env PYTHONPATH="$pyroot${PYTHONPATH:+:$PYTHONPATH}" python3 -B -c '
import sys
if sys.path and sys.path[0] in ("", "."):
    del sys.path[0]
from ctfsweep.cli import main
sys.exit(main())' "$@"
