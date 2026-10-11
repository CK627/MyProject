# -*- coding: utf-8 -*-
"""多层解码链（hex/base64）、花括号片段探测、内容"加壳"识别与拼接建议"""
import re

from .utils import (B64_RUN, BRACE_CORE, FLAG_RE, HEX_RUN, decode_score,
                    printable_ratio, try_b64, try_hex)


def decode_chain(blob, keywords, depth, out, seen):
    """对 blob 尝试 hex / base64 解码；命中关键词 / flag 结构 / 花括号结构则记录并递归"""
    if depth <= 0:
        return
    for name, fn, pat in (("hex", try_hex, HEX_RUN), ("base64", try_b64, B64_RUN)):
        for m in pat.finditer(blob):
            tok = m.group(0)
            dec = fn(tok)
            if not dec or len(dec) < 6 or printable_ratio(dec) < 0.8:
                continue
            low = dec.lower()
            has_kw = any(k.encode() in low for k in keywords)
            has_brace = b'{' in dec and b'}' in dec and BRACE_CORE.search(dec)
            if not (has_kw or has_brace or FLAG_RE.search(dec)):
                continue
            key = (name, dec[:100])
            if key in seen:
                continue
            seen.add(key)
            out.append((decode_score(dec, keywords), name, tok[:70], dec[:260]))
            decode_chain(dec, keywords, depth - 1, out, seen)


def fragments(blob, keywords, findings, seen, loc, strict_text=False):
    """花括号片段探测：分段 flag 题的核心线索（如 {krjl424 / zlmqu458xktq}）

    strict_text=True（原始文件：evtx / .reg / 任意文本）时启用噪音闸门，剔除二进制巧合：
      1) 纯 hex 片段 —— 注册表 GUID / 十六进制路径（如 {3050f3 / {5046ab8c…）
      2) 紧跟在 . \\ / 之后的「文件名后缀」拼贴（如 setupetw.dll55e3}）
      3) 周边 80 字节内无任何空白的密集 token 区（乱码数据里的巧合配对）
    """

    def text_like(st, en):
        ctx = blob[max(0, st - 30): en + 40]
        if not ctx:
            return False
        return sum(32 <= c < 127 or c in (9, 10, 13) for c in ctx) / len(ctx) > 0.6

    def noisy(st, en, inner):
        """严格模式噪音判定（True = 剔除）"""
        if len(inner) >= 6 and re.fullmatch(rb'[0-9a-f]+', inner):
            return True
        prev = blob[st - 1:st]
        if prev and prev in b'.\\/':
            return True
        ctx = blob[max(0, st - 40): en + 40]
        if sum(ctx.count(c) for c in (b' ', b'\t', b'\r', b'\n')) < 2:
            return True
        return False

    def skip(st, en, inner):
        return (not text_like(st, en)) or (strict_text and noisy(st, en, inner))

    for m in re.finditer(rb'(?i)(flag|ctf)[A-Za-z0-9_]{0,6}\{[A-Za-z0-9_\-\.{}]{2,90}', blob):
        if FLAG_RE.match(blob, m.start()):
            continue
        if skip(m.start(), m.end(), m.group(0).split(b'{', 1)[-1]):
            continue
        val = m.group(0)[:80]
        k = ('frag-open', val)
        if k not in seen:
            seen.add(k)
            findings.append((0.65, '片段(前)', b'', val, loc))
    for m in re.finditer(rb'(?<![A-Za-z0-9_]){([a-z0-9]{4,24})', blob):
        inner = m.group(1)
        nxt = blob[m.end(1):m.end(1) + 1]
        if nxt in (b'}', b'-'):
            continue
        if not (any(97 <= c <= 122 for c in inner) and any(48 <= c <= 57 for c in inner)):
            continue
        if skip(m.start(), m.end(), inner):
            continue
        val = m.group(0)[:80]
        k = ('frag-open', val)
        if k not in seen:
            seen.add(k)
            findings.append((0.60, '片段(前)', b'', val, loc))
    for m in re.finditer(rb'([a-z0-9]{6,24})\}', blob):
        st = m.start(1)
        back = blob[st - 1:st]
        inner = m.group(1)
        if back and (back.isalnum() or back in b'_-{}:'):
            continue
        if not (any(97 <= c <= 122 for c in inner) and any(48 <= c <= 57 for c in inner)):
            continue
        if skip(m.start(), m.end(), inner):
            continue
        val = m.group(0)[:80]
        k = ('frag-close', val)
        if k not in seen:
            seen.add(k)
            findings.append((0.55, '片段(尾)', b'', val, loc))


# ---------- 内容"加壳"识别（txt 本体不是 flag{} 格式时）与片段拼接建议 ----------
BODY_PATS = [
    (re.compile(rb'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'), 'UUID'),
    (re.compile(rb'^[0-9a-fA-F]{32}$'), '32位十六进制'),
    (re.compile(rb'^[0-9a-fA-F]{40}$'), '40位十六进制'),
    (re.compile(rb'^[A-Za-z0-9_\-]{6,64}$'), '字母数字串'),
]


def flagify(content):
    """内容疑似 flag 本体（缺 flag{} 外壳）时给出加壳建议，否则返回 None"""
    c = content.strip()
    if not c or len(c) > 120 or b'{' in c or b'}' in c:
        return None
    for pat, label in BODY_PATS:
        if pat.match(c):
            if label == '字母数字串':
                has_a = any(65 <= x <= 90 or 97 <= x <= 122 for x in c)
                has_d = any(48 <= x <= 57 for x in c)
                if not (has_a and has_d):
                    continue
            return 'flag{%s}   (内容为%s，疑似缺少 flag{} 外壳)' % (c.decode('utf-8', 'replace'), label)
    return None


def assemble_suggestion(frags):
    """对检出的花括号片段给出启发式拼接尝试（供人工确认）"""
    if len(frags) < 2:
        return None
    fl = list(frags)
    head = None
    for i, f in enumerate(fl):
        if re.match(r'(?i)(flag|ctf)[A-Za-z0-9_]{0,6}\{', f):
            head = f
            fl.pop(i)
            break
    if head is None:
        for i, f in enumerate(fl):
            if f.startswith('{'):
                head = 'flag' + f
                fl.pop(i)
                break
    tail = None
    for i in range(len(fl) - 1, -1, -1):
        if fl[i].endswith('}'):
            tail = fl[i]
            fl.pop(i)
            break
    if head is None and fl:
        head = 'flag{' + fl.pop(0)
    parts = [head or '']
    for f in fl:
        parts.append(f.strip('{}'))
    if tail:
        parts.append(tail)
    s = ''.join(parts)
    if head and not s.endswith('}'):
        s += '}'
    return s
