# -*- coding: utf-8 -*-
"""置信度报告渲染（按分数排序、分级前缀、截断省略）"""
from .utils import level_of


def report(findings, limit, min_score):
    findings = [f for f in findings if f[0] >= min_score]
    findings.sort(key=lambda f: -f[0])
    for score, kind, tok, val, loc in findings[:limit]:
        v = val if isinstance(val, str) else val.decode('utf-8', 'replace')
        v = ' '.join(v.split())
        t = tok if isinstance(tok, str) else tok.decode('latin-1', 'replace')
        prefix = '[%.2f %s]' % (score, level_of(score))
        if kind == '明文flag':
            print('  %s 明文flag: %s   @%s' % (prefix, v, loc))
        elif kind == 'DNS查询':
            print('  %s DNS查询: %s   @%s' % (prefix, v, loc))
        elif kind == 'JWT':
            print('  %s JWT令牌: %s   @%s' % (prefix, v[:230], loc))
        elif kind in ('命令回显', '环境/配置', '短文本响应'):
            print('  %s %s: %s   @%s' % (prefix, kind, v[:230], loc))
        elif kind in ('hex', 'base64'):
            print('  %s %s解码: %s...  =>  %s   @%s' % (prefix, kind, t[:44], v[:160], loc))
        elif kind.startswith('片段'):
            print('  %s %s: %s   @%s' % (prefix, kind, v[:120], loc))
        else:
            print('  %s 关键词[%s]: ...%s...   @%s' % (prefix, t, v[:150], loc))
    if len(findings) > limit:
        print('  ...（其余省略，共 %d 条候选）' % len(findings))
    if not findings:
        print('  (无命中)')
