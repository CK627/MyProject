#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ctfsweep 冒烟测试（纯标准库、免安装）：

    python3 tests/test_smoke.py

覆盖：
  * CLI：--version / --help / 无参数 / 路径不存在
  * VERSION 文件与包版本一致性
  * t1.pcap：明文 flag / hex 解码 / DNS base64 外带 / JWT / 环境变量回显 / --min-score 过滤
  * t2.pcapng：pcapng 封装
  * t3.evtx：UTF-16 明文 + 花括号片段 + 启发式拼接
  * t4.pcap --extract：文件雕刻 + zip 内容扫描 + 落盘
  * 目录模式
"""
import os
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
        rc, out = run_cli(['/no/such/file.pcap'])
        check(rc == 2, '路径不存在时返回 2')

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
