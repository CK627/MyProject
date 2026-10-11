#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ctfsweep 冒烟测试（纯标准库、免安装）：

    python3 tests/test_smoke.py

覆盖：
  * CLI：--version / --help / 无参数 / 路径不存在
  * VERSION 文件与包版本一致性
  * shell 脚本体检：$VAR 后不得紧跟全角字符（bash 变量名解析坑）
  * 补全体检：选项列表经 compadd -l -d 添加并合并显示同义短/长选项（"-f --file"）；
    不得回退为 _describe -t options（prefix-needed 门禁会拦截，不敲 "-" 就补不出选项）
  * t1.pcap：明文 flag / hex 解码 / DNS base64 外带 / JWT / 环境变量回显 / --min-score 过滤
  * t2.pcapng：pcapng 封装 + -f/--file 参数
  * t3.evtx：UTF-16 明文 + 花括号片段 + 启发式拼接 + 噪音闸门（dll 后缀 / GUID / 乱码区剔除）
  * t4.pcap --extract：文件雕刻 + zip 内容扫描 + 落盘
  * 判断核（judge）：微型数据集训练与分离、train 子命令（留一组评估）、--judge 打分与无模型兜底
  * t5-ad.pcap：AD 域协议（Kerberos 票据 / NetNTLM 响应 / LDAP 明文绑定 / SPN）
  * 目录模式
"""
import json
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
from ctfsweep.core import judge  # noqa: E402

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

    选项列表经 compadd -l -d 添加：手写显示串、同义短/长选项合并为一行（如 "-f --file"）。
    不得回退为 _describe -t options —— 其 prefix-needed 门禁会在光标不以 - 开头时不列出
    选项（即历史上「不敲 - 就看不到 --选项」的根因）。
    """
    zsh = open(os.path.join(ROOT, 'completions', 'ctfsweep.zsh'), encoding='utf-8').read()
    code = '\n'.join(l for l in zsh.splitlines() if not l.lstrip().startswith('#'))
    check('compadd -l -d' in code, 'zsh 补全：选项经 compadd -l -d 添加（一屏一行显示串）')
    check('_describe -t options' not in code, 'zsh 补全：未回退为 -t options（会被 prefix-needed 拦截）')
    check('-f --file' in code and '-k --keywords' in code, 'zsh 补全：配对选项以 "-f --file" 合并显示')
    check('-F --folder' in code and '--folder:' in code, 'zsh 补全：含 -F --folder（指定文件夹）')
    check('--extract' in code and '--min-score' in code, 'zsh 补全：含主要选项')
    check('--check' in code, 'zsh 补全：update --check 在场')
    check('train' in code and '--judge' in code, 'zsh 补全：含 train 子命令与 --judge')
    bash = open(os.path.join(ROOT, 'completions', 'ctfsweep.bash'), encoding='utf-8').read()
    check('--extract' in bash and '--check' in bash and '--folder' in bash, 'bash 补全：含主要选项与 --check')
    check('train' in bash and '--judge' in bash, 'bash 补全：含 train 与 --judge')


def _judge_samples():
    """微型数据集：正=真片段语境（空格/正常词），负=dll 后缀拼贴（二进制噪音）"""
    return [
        {'kind': '片段(前)', 'score': 0.6, 'val': '{krjl424', 'file_type': 'raw',
         'data': b'"cmd.exe /c echo {krjl424" /f', 'label': 1, 'group': 'g1', 'file': 'g1'},
        {'kind': '片段(前)', 'score': 0.6, 'val': '{wtq998', 'file_type': 'raw',
         'data': b'echo {wtq998 more', 'label': 1, 'group': 'g1', 'file': 'g1'},
        {'kind': '片段(尾)', 'score': 0.55, 'val': 'zlmqu458xktq}', 'file_type': 'raw',
         'data': b'Service Key: zlmqu458xktq}\r\n', 'label': 1, 'group': 'g1', 'file': 'g1'},
        {'kind': '片段(尾)', 'score': 0.55, 'val': 'q3dalb773}', 'file_type': 'raw',
         'data': b'echo q3dalb773} here', 'label': 1, 'group': 'g1', 'file': 'g1'},
        {'kind': '片段(前)', 'score': 0.6, 'val': '{yq5511', 'file_type': 'raw',
         'data': b'add user {yq5511 now', 'label': 1, 'group': 'g1', 'file': 'g1'},
        {'kind': '片段(尾)', 'score': 0.55, 'val': 'dll55e3}', 'file_type': 'raw',
         'data': b'C:\\Windows\\system32\\setupetw.dll55e3}JK', 'label': 0, 'group': 'g2', 'file': 'g2'},
        {'kind': '片段(尾)', 'score': 0.55, 'val': 'dllb39e}', 'file_type': 'raw',
         'data': b'C:\\Windows\\system32\\setupetw.dllb39e}XK', 'label': 0, 'group': 'g2', 'file': 'g2'},
        {'kind': '片段(尾)', 'score': 0.55, 'val': 'exe6ce1}', 'file_type': 'raw',
         'data': b'C:\\Windows\\system32\\OpenWith.exe6ce1}\xa6', 'label': 0, 'group': 'g2', 'file': 'g2'},
        {'kind': '片段(尾)', 'score': 0.55, 'val': 'dll984b}', 'file_type': 'raw',
         'data': b'C:\\Windows\\System32\\RstrtMgr.dll984b}\x0e', 'label': 0, 'group': 'g2', 'file': 'g2'},
        {'kind': '片段(尾)', 'score': 0.55, 'val': 'dllff1c}', 'file_type': 'raw',
         'data': b'C:\\Windows\\system32\\shwebsvc.dllff1c}\xf4', 'label': 0, 'group': 'g2', 'file': 'g2'},
    ]


def check_judge(tmp):
    """判断核：机制训练、CLI train、--judge 打分、无模型兜底"""
    samples = _judge_samples()
    rows = []
    for s in samples:
        rows.append({'v': 1, 'group': s['group'], 'file': s['file'], 'kind': s['kind'],
                     'score': s['score'], 'val': judge.normalize_val(s['val']),
                     'label': s['label'], 'note': 'smoke',
                     'feats': judge.extract_features(s)})

    # 1) 机制：微型训练能分离正负
    net = judge.JudgeNet(seed=1)
    X, y = judge.rows_to_xy(rows)
    net.train(X, y)
    p_pos = net.predict(judge.extract_features(samples[0]))
    p_neg = net.predict(judge.extract_features(samples[5]))
    check(p_pos > 0.5 > p_neg, '微型训练：正负分离（p 正 %.2f > 0.5 > 负 %.2f）' % (p_pos, p_neg))

    # 2) CLI train：留一组评估 + 保存
    ds = os.path.join(tmp, 'judge_ds.jsonl')
    mdl = os.path.join(tmp, 'judge_model.json')
    with open(ds, 'w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    rc, out = run_cli(['train', '--data', ds, '--model-out', mdl, '--epochs', '150'])
    check(rc == 0 and os.path.isfile(mdl), 'train 子命令：训练并保存模型')
    check('留一组评估' in out and 'AUC' in out, 'train 输出留一组评估信息')

    # 3) --judge：扫描输出 p 分与重点候选
    os.environ['CTFSWEEP_JUDGE_MODEL'] = mdl
    try:
        rc, out = run_cli([os.path.join(tmp, 't3.evtx'), '--judge'])
    finally:
        os.environ.pop('CTFSWEEP_JUDGE_MODEL', None)
    check(rc == 0 and '已加载模型' in out, '--judge：显示模型加载信息')
    check('p=' in out, '--judge：扫描结果带 p 分')
    check('【判断核·重点候选】' in out, '--judge：重点候选区块')

    # 4) 无模型兜底：提示但扫描照常
    os.environ['CTFSWEEP_JUDGE_MODEL'] = os.path.join(tmp, 'no_such_model.json')
    try:
        rc, out = run_cli([os.path.join(tmp, 't2.pcapng'), '--judge'])
    finally:
        os.environ.pop('CTFSWEEP_JUDGE_MODEL', None)
    check('未找到模型' in out and 'flag{pcapng-smoke-ok}' in out,
          '--judge 无模型：提示并正常扫描')


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
        check('update' in out and 'train' in out, '--help 含管理子命令（含 train）')
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
        check('dll55e3' not in out, '噪音闸门：文件名后缀拼贴（.dll55e3}）已剔除')
        check('3050f3' not in out, '噪音闸门：GUID 花括号（{3050f3）已剔除')
        check('v8ozb' not in out, '噪音闸门：密集乱码 token（{v8ozb）已剔除')
        check('FolderValueFlags' not in out, '噪音闸门：词内误报（FolderValueFlags）已剔除')
        check('create_pdo_flag' not in out, '噪音闸门：标识符内部（create_pdo_flag）已剔除')
        check('msctf' not in out, '噪音闸门：标识符内部（msctf_）已剔除')
        check('【中置信（需人工确认）】' in out, '报告分级：中置信小标题（换行分区）')
        check('【扫描统计】' in out and '高置信（可直接核验）：' in out, '统计：换行分区输出')
        check('统计: 高置信' not in out, '旧版单行统计已移除')
        check('片段池（按文件标注来源）' in out and '←' in out, '全局片段池：按行标注来源')

        print('== t4.pcap --extract ==')
        exdir = os.path.join(tmp, 'extract')
        rc, out = run_cli([os.path.join(tmp, 't4.pcap'), '--extract', '--extract-dir', exdir])
        check('[提取]' in out, '提取提示')
        check('flag{zip-carve-ok}' in out, 'zip 内 flag 内容扫描')
        carved = os.listdir(exdir) if os.path.isdir(exdir) else []
        check(any(f.endswith('.zip') for f in carved), 'zip 文件已落盘')

        print('== t5-ad.pcap：AD / 域协议 ==')
        rc, out = run_cli([os.path.join(tmp, 't5-ad.pcap')])
        check('【AD / 域渗透线索】' in out, 'AD 线索区块出现')
        check('域: CORP.LOCAL' in out, 'Kerberos 域名解析（CORP.LOCAL）')
        check('$krb5asrep$23$svc_sql@CORP.LOCAL:' in out, 'AS-REP Roasting 哈希（-m 18200 格式）')
        check('RC4-HMAC' in out and '可离线爆破' in out, 'RC4 票据标注可爆破')
        check('NetNTLMv2' in out and 'kanna.seto::corp:' in out, 'NetNTLMv2 响应（-m 5600 格式）')
        check('P@ssw0rd-AD-2026' in out, 'LDAP 明文绑定口令')
        check('MSSQLSvc/dc01.corp.local' in out, 'SPN（Kerberoasting 目标）')

        print('== 判断核（judge）==')
        check_judge(tmp)

        print('== 目录模式 ==')
        rc, out = run_cli([tmp])
        check(rc == 0, '目录扫描整体返回 0')
        rc, out = run_cli(['-F', tmp])
        check(rc == 0, '-F 指定文件夹')
        rc, out = run_cli(['--folder', tmp])
        check(rc == 0, '--folder 长选项等价')
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
