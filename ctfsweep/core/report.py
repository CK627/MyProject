# -*- coding: utf-8 -*-
"""置信度报告渲染（按分数排序、分级小标题换行、截断省略）"""
from .utils import level_of

LEVEL_TITLES = {
    '高': '高置信（可直接核验）',
    '中': '中置信（需人工确认）',
    '低': '低置信（线索参考）',
}


def report(findings, limit, min_score, pfunc=None):
    """按置信度分带渲染。

    `findings` 是 5 元组 `(score, kind, tok, val, loc)`——全项目的渲染 ABI，
    与 `judge.predict_finding` 同形；调用方若持 `Finding`，自行 `to_tuple()`。
    `val` 按 utf-8 解码，`tok` 按 **latin-1**（非 UTF-8 的 token 走 latin-1 才不丢字节）。
    """
    findings = [f for f in findings if f[0] >= min_score]
    findings.sort(key=lambda f: -f[0])
    cur = None
    for score, kind, tok, val, loc in findings[:limit]:
        lv = level_of(score)
        if lv != cur:
            cur = lv
            print('  【%s】' % LEVEL_TITLES.get(lv, lv))
        v = val if isinstance(val, str) else val.decode('utf-8', 'replace')
        v = ' '.join(v.split())
        t = tok if isinstance(tok, str) else tok.decode('latin-1', 'replace')
        prefix = '[%.2f %s]' % (score, lv)
        sfx = ''
        if pfunc is not None:
            try:
                sfx = '   p=%.2f' % pfunc((score, kind, tok, val, loc))
            except Exception:
                sfx = ''
        if kind == '明文flag':
            print('    %s 明文flag: %s   @%s%s' % (prefix, v, loc, sfx))
        elif kind == 'USB键盘输入':
            print('    %s USB键盘键入: %s   @%s%s' % (prefix, v[:230], loc, sfx))
        elif kind == 'DNS查询':
            print('    %s DNS查询: %s   @%s%s' % (prefix, v, loc, sfx))
        elif kind == 'JWT':
            print('    %s JWT令牌: %s   @%s%s' % (prefix, v[:230], loc, sfx))
        elif kind in ('Kerberos票据', 'NetNTLM', 'LDAP口令', '域账号'):
            print('    %s %s: %s   @%s%s' % (prefix, kind, v[:230], loc, sfx))
        elif kind in ('命令回显', '环境/配置', '短文本响应'):
            print('    %s %s: %s   @%s%s' % (prefix, kind, v[:230], loc, sfx))
        elif kind in ('hex', 'base64'):
            print('    %s %s解码: %s...  =>  %s   @%s%s' % (prefix, kind, t[:44], v[:160], loc, sfx))
        elif kind.startswith('片段'):
            print('    %s %s: %s   @%s%s' % (prefix, kind, v[:120], loc, sfx))
        elif kind == '关键词':
            print('    %s 关键词[%s]: ...%s...   @%s%s' % (prefix, t, v[:150], loc, sfx))
        else:
            # 其余具名 kind（FTP成功凭据 / FTP命令序列 / 系统版本 / Redis凭据 /
            # 交互会话记录 / 漏洞利用 …）直接以类型名渲染——它们的 tok 恒为空，
            # 旧回退分支会把它们套进 `关键词[tok]` 格式，印出 "关键词[]" 空标签。
            print('    %s %s: %s   @%s%s' % (prefix, kind, v[:230], loc, sfx))
    if len(findings) > limit:
        print('  ...（其余省略，共 %d 条候选）' % len(findings))
    if not findings:
        print('  (无命中)')
