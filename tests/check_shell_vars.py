# -*- coding: utf-8 -*-
"""体检：shell 脚本里 `$VAR` 后面不得**直接**跟非 ASCII 字符。

为什么要有这条：`$VAR（` 这种写法里，shell 解析变量名时会把紧跟的多字节字符
一起看进去，行为随 locale/实现而变，轻则变量取空、重则脚本报错。项目里踩过。

⚠️ 为什么是 Python 而不是 `grep -E '[^\\x00-\\x7f]'`：
   **BSD grep（macOS 自带）根本不支持 `\\xNN` 转义**，那个模式会报
   `grep: invalid character range` 并以 rc=2 退出。而调用方写的是
   `if grep ...; then` —— 命令**出错**和"没匹配"都走 else 分支，
   于是这条检查会**永远报 ok**（实测：它在 startupctl 里从来没生效过，
   直到换到 CtfSweep 上才被发现）。检查器自己出错必须能被看见。

只扫 shell 文件（.sh/.bash/.zsh 以及 bin/ 下无扩展名的启动器）——
Python 源码里出现 `$VAR` 加中文是正常的（正则、字符串模板），不该被误报。
"""
import os
import re
import sys

PAT = re.compile(r'\$[A-Za-z_][A-Za-z0-9_]*[^\x00-\x7f]')


def is_shell_file(path, roots):
    base = os.path.basename(path)
    if base.endswith(('.sh', '.bash', '.zsh', '.ksh')):
        return True
    # bin/ 下的启动器没有扩展名（bin/ctfsweep、bin/startupctl）
    if '.' not in base:
        for r in roots:
            if os.path.basename(r) == 'bin' and path.startswith(r):
                return True
    return False


def main(argv):
    if not argv:
        print('用法: check_shell_vars.py <目录>...', file=sys.stderr)
        return 2
    bad = []
    for root in argv:
        if not os.path.isdir(root):
            continue
        for dp, dn, fn in os.walk(root):
            dn[:] = [d for d in dn if d not in ('__pycache__', '.git')]
            for f in sorted(fn):
                p = os.path.join(dp, f)
                if not is_shell_file(p, argv):
                    continue
                try:
                    with open(p, encoding='utf-8', errors='replace') as fh:
                        lines = fh.read().splitlines()
                except OSError:
                    continue
                for i, line in enumerate(lines, 1):
                    if PAT.search(line):
                        bad.append('%s:%d: %s' % (p, i, line.strip()[:78]))
    if bad:
        for b in bad:
            print(b)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
