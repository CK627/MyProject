#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ctfsweep 特征化（golden）回归：把每个夹具的完整 stdout 与基线逐字节比对。

    python3 tests/test_golden.py            # 比对，不一致则打印首个差异并失败
    python3 tests/test_golden.py --record   # 重新录制基线（仅在确认改动符合预期时）

为什么需要它：`tests/test_smoke.py` 是约 60 条**子串**断言，看不见
并列项换序、重复打印、整块位移——而"并列项换序"正是扫描管线收敛
（新 Router/MetaJudge 与旧版 scanner 合并）最容易踩的坑。这里做逐字节护栏。

基线里只归一化**环境相关**的路径（工作目录、仓库目录），其余一字不改。
为了可复现，运行时固定三件事：
  * `TZ=UTC`——报告里的 HTTP 事务时间戳走 `time.localtime`，不定时区就不可复现；
  * `PYTHONHASHSEED=0`——`set` 迭代序会随哈希种子变（`get_summary` 里就有 `list(set(...))`）；
  * 固定的工作目录与全新的数据目录——留存区提示里的候选条数必须从头开始算。

注意：本脚本**不进 CI**（不同 Python 版本/平台的格式化细节可能有别），
它是重构期间手工跑的护栏，`bash tests/smoke.sh` 仍是 CI 的唯一门禁。
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import gen_fixtures  # noqa: E402

GOLDEN_DIR = os.path.join(HERE, 'golden')

# 固定（非 mkdtemp）工作区，比对结果才与本次运行的临时目录名无关
BASE = os.path.join(tempfile.gettempdir(), 'ctfsweep-golden')
WORK = os.path.join(BASE, 'work')        # 夹具所在
EXOUT = os.path.join(BASE, 'extout')     # --extract 落盘目标（在 WORK 之外，
                                         # 免得目录模式把上一次的雕刻产物也扫进去）
DATADIR = os.path.join(BASE, 'data')
MODELDIR = os.path.join(BASE, 'models')


def cases():
    """(用例名, argv)。argv 里的路径全部落在 BASE 内，便于统一归一化。"""
    def p(*parts):
        return os.path.join(WORK, *parts)

    return [
        ('t1.pcap', [p('t1.pcap')]),
        ('t2.pcapng', [p('t2.pcapng')]),
        ('t3.evtx', [p('t3.evtx')]),
        ('t4.pcap', [p('t4.pcap')]),
        ('t5-ad.pcap', [p('t5-ad.pcap')]),
        ('t6-hosts.pcap', [p('t6-hosts.pcap')]),
        ('t7-tls.pcap', [p('t7-tls.pcap')]),
        ('t8-b64.pcap', [p('t8-b64.pcap')]),
        ('t9-dns.pcap', [p('t9-dns.pcap')]),
        ('t10-ftp.pcap', [p('t10-ftp.pcap')]),
        ('t10-ftp.pcap+brief', [p('t10-ftp.pcap'), '-q']),
        ('t11-smtp.pcap', [p('t11-smtp.pcap')]),
        ('t12-web.pcap', [p('t12-web.pcap')]),
        ('t4.pcap+extract', [p('t4.pcap'), '--extract',
                             '--extract-dir', os.path.join(EXOUT, 't4')]),
        ('t7-tls.pcap+extract', [p('t7-tls.pcap'), '--extract',
                                 '--extract-dir', os.path.join(EXOUT, 't7')]),
        ('dir', [WORK]),
    ]


def normalize(text):
    """只抹掉环境相关的部分，其余原样保留。"""
    text = text.replace(BASE, '<TMP>').replace(ROOT, '<ROOT>')
    # -q/--brief 的缓存目录名带「完整路径的短哈希」（同名不同目录不互相覆盖），
    # 而 BASE 本身随 $TMPDIR 变 → 哈希也变。归一化掉哈希，否则基线不可复现。
    return re.sub(r'/[^/\s]+-[0-9a-f]{6}/', '/<名>-<哈希>/', text)


def run_case(argv):
    env = dict(os.environ)
    env['TZ'] = 'UTC'
    env['PYTHONHASHSEED'] = '0'
    env['CTFSWEEP_DATA_DIR'] = DATADIR
    env['CTFSWEEP_MODELS_DIR'] = MODELDIR
    proc = subprocess.run([sys.executable, '-B', '-m', 'ctfsweep'] + list(argv),
                          cwd=ROOT, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, env=env)
    return proc.returncode, normalize(proc.stdout.decode('utf-8', 'replace'))


def first_diff(exp, got):
    el, gl = exp.splitlines(), got.splitlines()
    for i in range(max(len(el), len(gl))):
        a = el[i] if i < len(el) else '<无此行>'
        b = gl[i] if i < len(gl) else '<无此行>'
        if a != b:
            return i + 1, a, b
    return None


def main():
    record = '--record' in sys.argv[1:]

    shutil.rmtree(BASE, ignore_errors=True)
    os.makedirs(WORK)
    gen_fixtures.generate(WORK)
    os.makedirs(DATADIR)
    os.makedirs(MODELDIR)
    if record:
        os.makedirs(GOLDEN_DIR, exist_ok=True)

    fails = []
    for name, argv in cases():
        path = os.path.join(GOLDEN_DIR, name + '.txt')
        rc, out = run_case(argv)
        if rc != 0:
            fails.append('%s：退出码 %d' % (name, rc))
            continue
        if record:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(out)
            print('  [录制] %s（%d 行）' % (name, len(out.splitlines())))
            continue
        if not os.path.isfile(path):
            fails.append('%s：缺少基线（先跑 --record）' % name)
            continue
        with open(path, encoding='utf-8') as f:
            expected = f.read()
        if expected == out:
            print('  [ok  ] %s' % name)
            continue
        diff = first_diff(expected, out)
        fails.append('%s：第 %d 行不一致\n      基线: %s\n      实际: %s'
                     % ((name,) + diff if diff else (name, 0, '?', '?')))
        print('  [FAIL] %s' % name)

    shutil.rmtree(BASE, ignore_errors=True)

    print()
    if record:
        print('基线已录制到 %s' % GOLDEN_DIR)
        return 0
    if fails:
        print('特征化比对失败 %d 项:' % len(fails))
        for m in fails:
            print('  - %s' % m)
        return 1
    print('特征化比对全部通过（逐字节一致）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
