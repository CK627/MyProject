#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ctfsweep 冒烟测试（纯标准库、免安装）：

    python3 tests/test_smoke.py

覆盖：
  * CLI：--version / --help / 无参数 / 路径不存在
  * VERSION 文件与包版本一致性
  * shell 脚本体检：$VAR 后不得紧跟全角字符（bash 变量名解析坑）
  * 补全体检：zsh 选项列表必须用 _describe -O（-t options 会被 prefix-needed 门禁挡掉，
    导致不敲 "-" 就补不出 --选项）
  * t1.pcap：明文 flag / hex 解码 / DNS base64 外带 / JWT / 环境变量回显 / --min-score 过滤
  * t2.pcapng：pcapng 封装 + -f/--file 参数
  * t3.evtx：UTF-16 明文 + 花括号片段 + 启发式拼接
  * t4.pcap --extract：文件雕刻 + zip 内容扫描 + 落盘
  * 目录模式
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import gen_fixtures  # noqa: E402
from ctfsweep import __version__  # noqa: E402

FAILS = []


def check(cond, msg):
    print('  [%s] %s' % ('ok  ' if cond else 'FAIL', msg))
    if not cond:
        FAILS.append(msg)


def run_cli(args):
    proc = subprocess.run(
        [sys.executable, '-B', '-m', 'ctfsweep'] + list(args),
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return proc.returncode, proc.stdout.decode('utf-8', 'replace')


def check_shell_scripts():
    """体检 shell 脚本：$VAR 后不得紧跟非 ASCII 字符（bash 会把全角字符并入变量名导致解析错误）"""
    pat = re.compile(r'\$[A-Za-z_][A-Za-z0-9_]*[^\x00-\x7f]')
    bad = []
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in ('.git', '__pycache__')]
        for f in sorted(files):
            if not (f.endswith('.sh') or f.endswith('.zsh') or f.endswith('.bash')
                    or f == 'ctfsweep'):
                continue
            p = os.path.join(root, f)
            for i, line in enumerate(open(p, encoding='utf-8', errors='replace'), 1):
                if pat.search(line):
                    bad.append('%s:%d' % (os.path.relpath(p, ROOT), i))
    check(not bad, 'shell 变量名体检（%s）' % (', '.join(bad) if bad else '全部通过'))


def check_completions():
    """补全静态体检（防回退）：

    zsh 的 _describe -t options 受 prefix-needed 样式约束，默认「光标不以 - 开头就不列出选项」；
    本项目要求「不敲 - 也能 TAB 出 --选项」，必须用 _describe -O（源码级绕过该门禁）。
    """
    zsh = open(os.path.join(ROOT, 'completions', 'ctfsweep.zsh'), encoding='utf-8').read()
    code = '\n'.join(l for l in zsh.splitlines() if not l.lstrip().startswith('#'))
    check('_describe -O' in code, 'zsh 补全：选项列表使用 _describe -O（不敲 - 也能列出）')
    check('_describe -t options' not in code, 'zsh 补全：未回退为 -t options（会被 prefix-needed 拦截）')
    check('--extract' in code and '--min-score' in code, 'zsh 补全：含主要选项')
    check('--check' in code, 'zsh 补全：update --check 在场')
    bash = open(os.path.join(ROOT, 'completions', 'ctfsweep.bash'), encoding='utf-8').read()
    check('--extract' in bash and '--check' in bash, 'bash 补全：含主要选项与 --check')


def main():
    tmp = tempfile.mkdtemp(prefix='ctfsweep-smoke-')
    try:
        print('== 生成测试样例 ==')
        names = gen_fixtures.generate(tmp)
        for n in names:
            print('  - %s' % n)

        print('== 基础 CLI ==')
        rc, out = run_cli(['--version'])
        check(rc == 0 and __version__ in out, '--version 输出版本号')
        with open(os.path.join(ROOT, 'VERSION'), encoding='utf-8') as f:
            check(f.read().strip() == __version__, 'VERSION 文件与包版本一致')
        rc, out = run_cli([])
        check(rc == 1 and '用法' in out, '无参数时打印帮助并返回 1')
        rc, out = run_cli(['--help'])
        check(rc == 0 and '置信度模型' in out, '--help 返回 0')
        check('update' in out and 'uninstall' in out, '--help 含管理子命令')
        rc, out = run_cli(['/no/such/file.pcap'])
        check(rc == 2, '路径不存在时返回 2')

        print('== shell 脚本体检 ==')
        check_shell_scripts()

        print('== 补全体检 ==')
        check_completions()

        print('== t1.pcap：多载体 flag ==')
        rc, out = run_cli([os.path.join(tmp, 't1.pcap')])
        check('flag{plain-smoke-ok}' in out, '明文 flag')
        check('flag{h3x-smoke-ok}' in out, 'hex 解码 flag')
        check('flag{dns-smoke-ok}' in out, 'DNS 子域名 base64 外带')
        check('"username":"admin"' in out, 'JWT payload 解码')
        check('WEBUI_SK=Advanced_System_for_Text' in out, '环境变量回显')
        rc, out = run_cli([os.path.join(tmp, 't1.pcap'), '--min-score', '0.9'])
        check('flag{plain-smoke-ok}' in out and 'WEBUI_SK' not in out, '--min-score 过滤低置信')

        print('== t2.pcapng ==')
        rc, out = run_cli([os.path.join(tmp, 't2.pcapng')])
        check('flag{pcapng-smoke-ok}' in out, 'pcapng 明文 flag')
        rc, out = run_cli(['-f', os.path.join(tmp, 't2.pcapng')])
        check(rc == 0 and 'flag{pcapng-smoke-ok}' in out, '-f/--file 等价位置参数')

        print('== t3.evtx ==')
        rc, out = run_cli([os.path.join(tmp, 't3.evtx')])
        check('flag{evtx-smoke-ok}' in out, 'evtx UTF-16 明文 flag')
        check('krjl424' in out and 'zlmqu458xktq}' in out, '花括号片段探测')
        check('flag{krjl424zlmqu458xktq}' in out, '启发式拼接建议')

        print('== t4.pcap --extract ==')
        exdir = os.path.join(tmp, 'extract')
        rc, out = run_cli([os.path.join(tmp, 't4.pcap'), '--extract', '--extract-dir', exdir])
        check('[提取]' in out, '提取提示')
        check('flag{zip-carve-ok}' in out, 'zip 内 flag 内容扫描')
        carved = os.listdir(exdir) if os.path.isdir(exdir) else []
        check(any(f.endswith('.zip') for f in carved), 'zip 文件已落盘')

        print('== 目录模式 ==')
        rc, out = run_cli([tmp])
        check(rc == 0, '目录扫描整体返回 0')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FAILS:
        print('冒烟失败 %d 项:' % len(FAILS))
        for m in FAILS:
            print('  - %s' % m)
        return 1
    print('冒烟全部通过')
    return 0


if __name__ == '__main__':
    sys.exit(main())
