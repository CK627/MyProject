# -*- coding: utf-8 -*-
r"""体检 .bat 的编码契约（devtool 系列一致）。

三条，都有实测依据（Windows 10 19045，代码页 936 的 cmd）：

1. **不许有 UTF-8 BOM。** cmd 会把 BOM 当成命令的一部分，第一行直接报错
   （实测：`'?@echo' 不是内部或外部命令`），随后整段退化成逐行交互执行。
2. **必须 CRLF。** LF-only 的 .bat 会被碎片化解析（实测报 `'not' 不是内部或外部命令`）。
3. **含中文时，`chcp 65001` 必须出现在第一处非 ASCII 之前。** 它把控制台切到 UTF-8，
   之后 cmd 按 UTF-8 读行、控制台也按 UTF-8 渲染。

2026-10 实测：UTF-8 无 BOM + CRLF + chcp 65001 的 .bat，中文 REM / echo / if 块在
**直接调用与 call 两种方式下都正确显示**。此前"必须纯 ASCII"的契约，是基于一次
（很可能带 BOM 或用了 LF 的）失败推断出来的——那个结论过宽了。

⚠️ 用 Python 判非 ASCII 而不是 `grep -P '[\x80-\xFF]'`：BSD grep（macOS 自带）
   不支持 `-P` 与 `\xNN`，本地跑不出来；Python 到处都一样。
"""
import os
import sys

CHCP = b'chcp 65001'


def check(path):
    """返回问题列表（空 = 通过）。"""
    try:
        raw = open(path, 'rb').read()
    except OSError as e:
        return ['读不到: %s' % e]
    bad = []

    if raw.startswith(b'\xef\xbb\xbf'):
        bad.append('有 UTF-8 BOM（cmd 会把 BOM 当命令的一部分，第一行直接报错）')

    bare_lf = raw.replace(b'\r\n', b'').count(b'\n')
    if bare_lf:
        bad.append('含 %d 个裸 LF（必须 CRLF，否则 cmd 会碎片化解析）' % bare_lf)

    first_nonascii = None
    for i, b in enumerate(raw):
        if b > 0x7f:
            first_nonascii = i
            break
    if first_nonascii is not None:
        pos = raw.find(CHCP)
        if pos < 0:
            bad.append('含中文但没有 `chcp 65001`（控制台会按本地代码页渲染成乱码）')
        elif pos > first_nonascii:
            bad.append('`chcp 65001` 出现在第一处中文之后（要放在它之前才生效）')

    return bad


def main(argv):
    files = argv or [f for f in os.listdir('.') if f.endswith('.bat')]
    fails = 0
    for f in files:
        if not os.path.isfile(f):
            continue
        problems = check(f)
        if problems:
            fails += 1
            for p in problems:
                print('FAIL %s: %s' % (f, p))
        else:
            print('ok   %s' % f)
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
