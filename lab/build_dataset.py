#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""判断核数据集构建（本机实验脚本，目录已 gitignore——含题库答案标注，不进公开仓库）。

把历次解题的扫描候选 + 人工标注（真/假）导出为 dataset.jsonl：
    ~/.devtools/ctfsweep/judge/dataset.jsonl

数据来源三类：
  1) 已解题目的"答案命中"候选（label=1）
  2) 原始文件预过滤噪声候选（label=0，如 .dll 后缀拼贴 / GUID / 乱码区）
  3) 合成困难负样本（四类噪音族，数据增强）

用法: python3 lab/build_dataset.py [--print-extras]
"""
import json
import os
import random
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from ctfsweep.core import judge  # noqa: E402
from ctfsweep.core.capture import PCAP_MAGICS, PCAPNG_MAGIC  # noqa: E402
from ctfsweep.core.decode import fragments  # noqa: E402
from ctfsweep.core.scanner import scan_capture, scan_rawfile  # noqa: E402

D = os.path.expanduser('~/Downloads/1')
W = os.path.expanduser('~/Documents/Personal/WLAQ/WP/Wireshare数据包分析')

FILES = [
    (D + '/logs/Security.evtx', 'solar'),
    (D + '/logs/regedit.reg', 'solar'),
    (D + '/logs/Microsoft-Windows-Shell-ConnectedAccountState%4ActionCenter.evtx', 'solar'),
    (D + '/challenge.pcap', 'astrbot'),
    (D + '/一发入魂.pcap', 'yifa'),
    (D + '/FLAG 消失之谜.pcap', 'mystery'),
    (W + '/logs.pcapng/logs.pcapng', 'wlaq'),
    (W + '/flag.pacpng/flag.pcapng', 'wlaq'),
    (W + '/attack.pcapng/attack.pcapng', 'wlaq'),
]

# 正样本规则：候选文本包含任一子串 → 与最终答案直接相关
POS = {
    'solar': ['flag{sol', '{krjl424', '33arsierting}', 'zlmqu458xktq}', 'wq3453dalb'],
    'astrbot': ['flag{80892e26', '"username":"admin"', 'WEBUI_SK=Advanced_System_for_Text',
                '/AstrBot', 'helloworld.zip'],
    'yifa': ['flag{0018ee2b', 'hexdump -ve'],
    'mystery': ['flag{00af113d'],
    'wlaq': ['flag{Find You!}', 'flag{4de36e4c7f941590b0f8ae2a74051f8e}', 'flag{Manners maketh man}'],
}

# 显式负样本规则（可选，按子串）
NEG = {
    'solar': ['LogonUI.exe'],
}


def _row(group, fname, kind, score, val, label, note, data, finder=None):
    s = {'kind': kind, 'score': score, 'val': val, 'file_type': 'raw', 'finder': finder}
    if finder is None:
        s['data'] = data
    return {'v': 1, 'group': group, 'file': fname, 'kind': kind, 'score': score,
            'val': judge.normalize_val(val)[:200], 'label': label, 'note': note,
            'feats': judge.extract_features(s)}


def _label_of(group, val):
    for pat in POS.get(group, []):
        if pat in val:
            return 1, 'pos:%s' % pat
    for pat in NEG.get(group, []):
        if pat in val:
            return 0, 'neg:%s' % pat
    return None, ''


def prefilter_extras(data, found_vals, limit=80):
    """原始文件：用未过滤的片段探测，回收被规则剔除的噪音候选（负样本）。"""
    out, seen = [], set()
    compact = data.replace(b'\x00', b'')
    for blob in (compact, data):
        res = []
        fragments(blob, ['flag', 'ctf'], res, set(), '(prefilter)', strict_text=False)
        for sc, kind, _tok, val, _loc in res:
            if len(out) >= limit:
                break
            v = val if isinstance(val, str) else val.decode('utf-8', 'replace')
            if v in found_vals or v in seen:
                continue
            seen.add(v)
            out.append((sc, kind, v))
    return out


def synth_negatives():
    """合成困难负样本（四类噪音族，各 30 条，随机种子固定）。"""
    rnd = random.Random(20261011)
    hexc = '0123456789abcdef'
    out = []

    # 1) .dll / .exe 后缀拼贴
    for _i in range(30):
        name = rnd.choice(['dll', 'exe']) + ''.join(rnd.choice(hexc) for _ in range(2)) \
            + rnd.choice('abef') + rnd.choice(hexc)
        val = '%s}' % name
        data = ('C:\\Windows\\system32\\setup%s.%s' % (rnd.choice(['etw', 'svc', 'mgr', 'host']), name)).encode()
        out.append(_row('synth', 'synth', '片段(尾)', 0.55, val, 0, 'synth:dll-suffix', data))

    # 2) GUID / 纯 hex 花括号
    for _i in range(30):
        inner = ''.join(rnd.choice(hexc) for _ in range(rnd.randint(6, 16)))
        val = '{%s' % inner
        data = ('HKEY_CLASSES_ROOT\\CLSID\\{%sB3-98b5-11cf-bb82}' % inner[:4]).encode('utf-16-le')
        out.append(_row('synth', 'synth', '片段(前)', 0.60, val, 0, 'synth:guid', data))

    # 3) 乱码密集区（无空白）
    junkchars = 'abcdefghijklmnopqrstuvwxyz0123456789@~`^|&?*[]%$#!+=<>()'
    for _i in range(30):
        body = ''.join(rnd.choice(junkchars) for _ in range(110))
        inner = ''.join(rnd.choice('abcdefghijklmnopqrstuvwxyz0123456789') for _ in range(rnd.randint(4, 8)))
        val = '{%s' % inner
        pos = 40
        data = (body[:pos] + val + body[pos + len(val):]).encode()
        out.append(_row('synth', 'synth', '片段(前)', 0.60, val, 0, 'synth:gibberish', data))

    # 4) 词内误报（关键词上下文）
    for _i in range(30):
        word = rnd.choice(['FolderValueFlags', 'AppIDFlags', 'StorageProviderFlags',
                           'create_pdo_flag', 'msctf_31bf', 'ValueFlags'])
        val = '"%s"=dword:0000000%d' % (word, rnd.randint(0, 9))
        out.append(_row('synth', 'synth', '关键词', 0.45, val, 0, 'synth:word-internal',
                        val.encode('utf-16-le')))

    return out


def main():
    show_extras = '--print-extras' in sys.argv
    rows = []
    print('== 候选收集 ==')
    for path, group in FILES:
        if not os.path.exists(path):
            print('  [跳过] 文件不存在: %s' % path)
            continue
        data = open(path, 'rb').read()
        fname = os.path.basename(path)
        ispcap = data[:4] in PCAP_MAGICS or data[:4] == PCAPNG_MAGIC
        tmpd = None
        if ispcap:
            tmpd = tempfile.mkdtemp(prefix='judge-ds-')
            findings = scan_capture(data, ['flag', 'ctf'], True, 3,
                                    {'outdir': tmpd, 'stem': os.path.splitext(fname)[0]})
        else:
            findings = scan_rawfile(data, ['flag', 'ctf'], True, 3, 300)
        finder = judge.ContextFinder(data)
        found_vals = set()
        n_pos = n_neg = n_skip = 0
        for f in findings:
            score, kind, _tok, val, _loc = f
            v = val if isinstance(val, str) else val.decode('utf-8', 'replace')
            v = judge.normalize_val(v)
            found_vals.add(v)
            lab, note = _label_of(group, v)
            if lab is None:
                n_skip += 1
                continue
            rows.append(_row(group, fname, kind, score, v, lab, note, None, finder=finder))
            n_pos += (lab == 1)
            n_neg += (lab == 0)
        extras = []
        if not ispcap:
            extras = prefilter_extras(data, found_vals)
            for sc, kind, v in extras:
                if _label_of(group, v)[0] == 1:
                    continue                       # 疑似真片段不进负样本（保守）
                rows.append(_row(group, fname, kind, sc, v, 0, 'prefilter:noise', None, finder=finder))
                n_neg += 1
        if tmpd:
            shutil.rmtree(tmpd, ignore_errors=True)
        print('  [%s|%s] 正 %d / 负 %d / 未标注 %d（预过滤噪音 %d）'
              % (fname, group, n_pos, n_neg - len(extras), n_skip, len(extras)))
        if show_extras and extras:
            for sc, kind, v in extras[:40]:
                print('      - [%.2f %s] %s' % (sc, kind, v[:90]))

    syn = synth_negatives()
    rows.extend(syn)
    print('  [synth] 合成负样本 %d 条' % len(syn))

    # 去重（file + kind + val）
    dedup, seen = [], set()
    for r in rows:
        key = (r['file'], r['kind'], r['val'][:120])
        if key in seen:
            continue
        seen.add(key)
        dedup.append(r)
    rows = dedup

    n_pos = sum(1 for r in rows if r['label'] == 1)
    n_neg = len(rows) - n_pos
    out_path = judge.default_dataset_path()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')

    print('')
    print('== 数据集 ==')
    print('  总计: %d 条（正 %d / 负 %d）' % (len(rows), n_pos, n_neg))
    by_group = {}
    for r in rows:
        g = r['group']
        by_group.setdefault(g, [0, 0])
        by_group[g][0 if r['label'] == 1 else 1] += 1
    for g, (p, n) in by_group.items():
        print('  %-9s 正 %-3d / 负 %-3d' % (g, p, n))
    print('  写入: %s' % out_path)
    print('')
    print('下一步: ctfsweep train   （留一组评估 + 全量重训 + 保存模型）')


if __name__ == '__main__':
    main()
